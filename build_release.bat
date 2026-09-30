@echo off
setlocal
title MBOX Viewer - Build Release Package
cd /d "%~dp0"

echo ========================================================
echo   MBOX Viewer - Build Portable Release (.exe & .zip)
echo ========================================================
echo.
python build_release.py
if errorlevel 1 (
    echo.
    echo [ERROR] An error occurred while building the release package.
    pause
    exit /b 1
)

echo.
echo Build complete! The release ZIP is ready to be uploaded to GitHub Releases.
pause
