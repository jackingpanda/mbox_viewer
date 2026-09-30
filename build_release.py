"""
build_release.py
Automated release packager for MBOX Viewer.
Builds standalone portable executable using PyInstaller and packages it into a release ZIP archive.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

from utils.constants import APP_NAME, APP_VERSION

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
APP_DIR = os.path.join(DIST_DIR, "MBOX_Viewer")
ZIP_NAME = f"MBOX_Viewer_v{APP_VERSION}_Windows_x64.zip"
ZIP_PATH = os.path.join(DIST_DIR, ZIP_NAME)


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("=" * 65)
    print(f"  Building Release Package: {APP_NAME} v{APP_VERSION}")
    print("=" * 65)

    # 1. Check PyInstaller
    try:
        import PyInstaller
        print(f"[✓] PyInstaller detected: v{PyInstaller.__version__}")
    except ImportError:
        print("[!] PyInstaller not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Clean previous build artifacts
    print("[*] Cleaning previous build outputs...")
    for d in (BUILD_DIR, APP_DIR):
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    # 3. Configure PyInstaller command
    sep = ";" if sys.platform == "win32" else ":"
    icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name=MBOX_Viewer",
        f"--icon={icon_path}",
        f"--add-data=assets{sep}assets",
        f"--add-data=gui/styles{sep}gui/styles",
        "main.py",
    ]

    print("[*] Executing PyInstaller build...")
    res = subprocess.run(cmd, cwd=BASE_DIR)
    if res.returncode != 0:
        print(f"[X] Build failed with exit code {res.returncode}")
        sys.exit(res.returncode)

    # 4. Copy documentation to release folder
    print("[*] Copying documentation to package...")
    for doc in ("README.md", "LICENSE", "CHANGELOG.md"):
        src = os.path.join(BASE_DIR, doc)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(APP_DIR, doc))

    # 5. Compress to ZIP archive
    print(f"[*] Packaging into ZIP archive: {ZIP_NAME}...")
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, _, files in os.walk(APP_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, DIST_DIR)
                zf.write(abs_path, rel_path)

    # 6. Summary metrics
    zip_size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    sha256 = compute_sha256(ZIP_PATH)

    print("=" * 65)
    print("  RELEASE BUILD SUCCESSFUL! 🎉")
    print("=" * 65)
    print(f"  • Archive File : {ZIP_PATH}")
    print(f"  • Archive Size : {zip_size_mb:.2f} MB")
    print(f"  • SHA-256 Hash : {sha256}")
    print("=" * 65)
    print("Next Steps:")
    print("1. Go to: https://github.com/jackingpanda/mbox_viewer/releases/tag/v" + APP_VERSION)
    print("2. Click 'Edit release' (or 'Draft a new release').")
    print(f"3. Drag and drop '{ZIP_NAME}' into the release assets.")
    print("4. Click 'Publish release'!")
    print("=" * 65)


if __name__ == "__main__":
    main()
