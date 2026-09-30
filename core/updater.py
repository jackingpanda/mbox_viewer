"""
core/updater.py
In-app update checker, GitHub Releases API integration, and in-place installer.
"""

from dataclasses import dataclass
import json
import logging
import os
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from typing import Optional, Tuple

from utils.constants import APP_NAME, APP_VERSION, GITHUB_RELEASES_URL, GITHUB_REPO

log = logging.getLogger(__name__)


@dataclass
class ReleaseInfo:
    """Metadata representing a GitHub release."""
    tag_name: str
    version_str: str
    title: str
    changelog: str
    html_url: str
    published_at: str
    zip_asset_url: Optional[str] = None
    zip_asset_name: Optional[str] = None
    zip_asset_size: int = 0

    @property
    def display_size(self) -> str:
        """Format asset size into human-readable string."""
        if not self.zip_asset_size or self.zip_asset_size <= 0:
            return "Unknown size"
        sz = float(self.zip_asset_size)
        for unit in ["B", "KB", "MB", "GB"]:
            if sz < 1024.0:
                return f"{sz:.1f} {unit}"
            sz /= 1024.0
        return f"{sz:.1f} TB"


def parse_version(version_str: str) -> Tuple[int, ...]:
    """
    Parse a semantic version string (e.g. 'v1.3.0', '1.4.1', 'v2.0.0-beta')
    into a comparable integer tuple, e.g. (1, 3, 0).
    """
    if not version_str:
        return (0, 0, 0)
    numbers = re.findall(r"\d+", version_str.strip())
    if not numbers:
        return (0, 0, 0)
    return tuple(int(n) for n in numbers)


def is_newer_version(current_ver: str, remote_ver: str) -> bool:
    """
    Check if remote_ver is strictly newer than current_ver.
    """
    c_parts = list(parse_version(current_ver))
    r_parts = list(parse_version(remote_ver))

    # Pad with zeros to equal length for safe comparison
    max_len = max(len(c_parts), len(r_parts), 3)
    c_parts.extend([0] * (max_len - len(c_parts)))
    r_parts.extend([0] * (max_len - len(r_parts)))

    return tuple(r_parts) > tuple(c_parts)


def fetch_latest_release(repo: str = GITHUB_REPO, timeout: int = 10) -> ReleaseInfo:
    """
    Fetch the latest release information from GitHub Releases API.
    Raises urllib.error.URLError, ValueError, or TimeoutError on failure.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"MBOX-Viewer/{APP_VERSION} (Windows)",
    }

    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError(f"No releases found for repository '{repo}'.") from exc
        if exc.code == 403:
            raise ValueError("GitHub API rate limit exceeded. Please try again later.") from exc
        raise ValueError(f"GitHub API error (HTTP {exc.code}): {exc.reason}") from exc
    except Exception as exc:
        raise ValueError(f"Failed to connect to update server: {exc}") from exc

    tag_name = data.get("tag_name", "").strip()
    version_str = tag_name.lstrip("vV")
    title = data.get("name") or f"Release {tag_name}"
    changelog = data.get("body") or "No changelog notes provided."
    html_url = data.get("html_url", f"https://github.com/{repo}/releases")
    published_at = data.get("published_at", "")[:10]

    # Find the zip asset (prefer Windows x64 zip)
    assets = data.get("assets", [])
    zip_url = None
    zip_name = None
    zip_size = 0

    # 1. Look for explicit Windows zip asset
    for asset in assets:
        aname = asset.get("name", "")
        if aname.lower().endswith(".zip") and ("win" in aname.lower() or "x64" in aname.lower()):
            zip_url = asset.get("browser_download_url")
            zip_name = aname
            zip_size = int(asset.get("size", 0))
            break

    # 2. Fallback to any zip asset
    if not zip_url:
        for asset in assets:
            aname = asset.get("name", "")
            if aname.lower().endswith(".zip"):
                zip_url = asset.get("browser_download_url")
                zip_name = aname
                zip_size = int(asset.get("size", 0))
                break

    return ReleaseInfo(
        tag_name=tag_name,
        version_str=version_str,
        title=title,
        changelog=changelog,
        html_url=html_url,
        published_at=published_at,
        zip_asset_url=zip_url,
        zip_asset_name=zip_name,
        zip_asset_size=zip_size,
    )


def get_app_target_info() -> Tuple[str, str, bool]:
    """
    Resolve the current running application location.
    Returns:
        (target_dir, executable_or_script_path, is_frozen)
    """
    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        exe_path = sys.executable
        target_dir = os.path.dirname(exe_path)
    else:
        # Running from source: root of project
        target_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        exe_path = sys.executable  # python.exe or run.bat

    return target_dir, exe_path, is_frozen


def extract_and_locate_staged_app(zip_path: str, staging_dir: str) -> str:
    """
    Extract downloaded ZIP archive into staging_dir.
    Returns the specific folder inside staging_dir that contains the application payload
    (handles nested root directory like MBOX_Viewer/ inside ZIP).
    """
    os.makedirs(staging_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(staging_dir)

    # Check if there is a single subdirectory (like MBOX_Viewer/) containing the app files
    entries = [os.path.join(staging_dir, e) for e in os.listdir(staging_dir)]
    dirs = [e for e in entries if os.path.isdir(e)]
    files = [e for e in entries if os.path.isfile(e)]

    if len(dirs) == 1 and not files:
        # Archive was packaged with a root folder, use that folder as source
        return dirs[0]

    return staging_dir


def create_in_place_updater_script(
    staging_source_dir: str,
    target_dir: str,
    exe_path: str,
    parent_pid: int,
) -> str:
    """
    Generate the Windows batch updater script to execute in-place replacement
    after the running process exits, release file locks, copy files, and relaunch.
    """
    temp_dir = tempfile.gettempdir()
    bat_path = os.path.join(temp_dir, "mbox_update_apply.bat")

    is_frozen = getattr(sys, "frozen", False)
    relaunch_cmd = f'start "" "{exe_path}"' if is_frozen else f'start "" "{exe_path}" main.py'

    bat_content = f"""@echo off
setlocal enabledelayedexpansion
title MBOX Viewer In-Place Updater

set "PID={parent_pid}"
set "STAGING={staging_source_dir}"
set "TARGET={target_dir}"

:: 1. Wait for parent MBOX Viewer process to terminate
:wait_loop
tasklist /fi "PID eq %PID%" 2>nul | find "%PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

:: 2. Brief grace period to ensure Windows OS file handles are completely unlocked
timeout /t 1 /nobreak >nul

:: 3. Robocopy new files into existing directory (in-place replacement)
robocopy "%STAGING%" "%TARGET%" /E /IS /IT /NP /R:5 /W:1 >nul

:: 4. Relaunch newly updated MBOX Viewer
{relaunch_cmd}

:: 5. Cleanup temporary staging directory
rmdir /s /q "%STAGING%" 2>nul

:: 6. Self-delete this batch script
(goto) 2>nul & del "%~f0"
"""

    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)

    return bat_path


def launch_in_place_updater(bat_path: str) -> None:
    """
    Launch the batch updater as a detached process and exit this application immediately.
    """
    DETACHED_FLAGS = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [bat_path],
        creationflags=DETACHED_FLAGS,
        close_fds=True,
        shell=True,
    )
