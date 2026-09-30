"""
publish_release.py
Automated GitHub Release publisher for MBOX Viewer.
Uses Git Credential Manager to authenticate and publish release notes + assets to GitHub.
"""

import hashlib
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

from utils.constants import APP_NAME, APP_VERSION, GITHUB_REPO


def get_github_token() -> str:
    """Retrieve GitHub Personal Access Token from Git Credential Manager."""
    try:
        p = subprocess.Popen(
            ["git", "credential", "fill"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out, _ = p.communicate("protocol=https\nhost=github.com\n\n")
        for line in out.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as exc:
        print(f"[!] Error querying git credential: {exc}")
    return ""


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def extract_changelog_for_version(version: str) -> str:
    """Extract release notes for specific version from CHANGELOG.md."""
    changelog_path = os.path.join(os.path.dirname(__file__), "CHANGELOG.md")
    if not os.path.exists(changelog_path):
        return f"Release {version}"

    with open(changelog_path, "r", encoding="utf-8") as f:
        content = f.read()

    header = f"## [{version}]"
    if header not in content:
        return f"Release {version}"

    part = content.split(header, 1)[1]
    if "\n## [" in part:
        part = part.split("\n## [", 1)[0]

    return part.strip()


def main():
    print("=" * 65)
    print(f"  Publishing Release: {APP_NAME} v{APP_VERSION} to GitHub")
    print(f"  Repository: {GITHUB_REPO}")
    print("=" * 65)

    token = get_github_token()
    if not token:
        print("[X] ERROR: GitHub token could not be retrieved from git credentials.")
        sys.exit(1)

    tag_name = f"v{APP_VERSION}"
    release_title = f"{APP_NAME} {tag_name} — In-App Updater, Storage Analyzer & Portable Standalone Build"
    zip_filename = f"MBOX_Viewer_v{APP_VERSION}_Windows_x64.zip"
    zip_path = os.path.join(os.path.dirname(__file__), "dist", zip_filename)

    if not os.path.exists(zip_path):
        print(f"[X] ERROR: Release asset not found at {zip_path}")
        print("    Please run 'python build_release.py' first.")
        sys.exit(1)

    file_size = os.path.getsize(zip_path)
    file_size_mb = file_size / (1024 * 1024)
    sha256 = compute_sha256(zip_path)

    notes = extract_changelog_for_version(APP_VERSION)
    full_body = (
        f"### 📦 Standalone Portable Release for Windows x64\n\n"
        f"- **File:** `{zip_filename}`\n"
        f"- **Size:** {file_size_mb:.2f} MB\n"
        f"- **SHA-256:** `{sha256}`\n\n"
        f"---\n\n"
        f"{notes}\n"
    )

    ctx = ssl.create_default_context()
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"MBOX-Viewer-Publisher/{APP_VERSION}",
    }

    # 1. Check if release already exists
    print(f"[*] Checking release status for tag '{tag_name}'...")
    get_rel_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{tag_name}"
    req = urllib.request.Request(get_rel_url, headers=headers)
    release_data = None
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            release_data = json.loads(resp.read().decode("utf-8"))
            print(f"[✓] Release found (ID: {release_data['id']})")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print("[*] Release does not exist yet. Will create new release.")
        else:
            print(f"[X] GitHub API error: {exc}")
            sys.exit(1)

    # 2. Create or Update Release
    if release_data:
        release_id = release_data["id"]
        print(f"[*] Updating existing release details...")
        patch_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/{release_id}"
        patch_payload = json.dumps({
            "name": release_title,
            "body": full_body,
            "draft": False,
            "prerelease": False,
        }).encode("utf-8")
        req = urllib.request.Request(patch_url, data=patch_payload, headers=headers, method="PATCH")
        with urllib.request.urlopen(req, context=ctx) as resp:
            release_data = json.loads(resp.read().decode("utf-8"))
            print("[✓] Release metadata updated successfully.")
    else:
        print(f"[*] Creating new GitHub release for tag '{tag_name}'...")
        post_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
        post_payload = json.dumps({
            "tag_name": tag_name,
            "name": release_title,
            "body": full_body,
            "draft": False,
            "prerelease": False,
        }).encode("utf-8")
        req = urllib.request.Request(post_url, data=post_payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx) as resp:
            release_data = json.loads(resp.read().decode("utf-8"))
            print(f"[✓] Created release (ID: {release_data['id']})")

    release_id = release_data["id"]

    # 3. Check existing assets in release and remove duplicates
    existing_assets = release_data.get("assets", [])
    for a in existing_assets:
        if a.get("name") == zip_filename:
            asset_id = a.get("id")
            print(f"[*] Removing existing outdated asset '{zip_filename}' (Asset ID: {asset_id})...")
            del_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/assets/{asset_id}"
            req = urllib.request.Request(del_url, headers=headers, method="DELETE")
            with urllib.request.urlopen(req, context=ctx) as resp:
                print("[✓] Existing asset deleted successfully.")

    # 4. Upload new release asset
    print(f"[*] Uploading release asset '{zip_filename}' ({file_size_mb:.2f} MB)...")
    upload_url = f"https://uploads.github.com/repos/{GITHUB_REPO}/releases/{release_id}/assets?name={zip_filename}"
    upload_headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/zip",
        "Content-Length": str(file_size),
        "User-Agent": f"MBOX-Viewer-Publisher/{APP_VERSION}",
    }

    start_time = time.time()
    with open(zip_path, "rb") as f:
        file_bytes = f.read()

    req = urllib.request.Request(upload_url, data=file_bytes, headers=upload_headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            uploaded_asset = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - start_time
            print(f"[✓] Asset upload successful in {elapsed:.1f}s!")
            print(f"    • Download URL: {uploaded_asset.get('browser_download_url')}")
            print(f"    • Asset Size  : {uploaded_asset.get('size')} bytes")
    except urllib.error.HTTPError as exc:
        print(f"[X] Upload failed (HTTP {exc.code}): {exc.read().decode('utf-8')}")
        sys.exit(1)

    print("=" * 65)
    print("  GITHUB RELEASE PUBLISHED SUCCESSFULLY! 🚀")
    print("=" * 65)
    print(f"  • Release URL: {release_data.get('html_url')}")
    print(f"  • Tag Name   : {tag_name}")
    print(f"  • Asset Name : {zip_filename}")
    print(f"  • SHA-256    : {sha256}")
    print("=" * 65)


if __name__ == "__main__":
    main()
