@echo off
setlocal
title MBOX Viewer - Build & Publish Release Package
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
set /p PUBLISH="Do you want to automatically publish this release to GitHub? (y/n): "
if /i "%PUBLISH%"=="y" (
    echo.
    python publish_release.py
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to publish release to GitHub.
        pause
        exit /b 1
    )
)

echo.
pause
