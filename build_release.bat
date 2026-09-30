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
    echo [ERROR] Terjadi kesalahan saat mem-build release package.
    pause
    exit /b 1
)

echo.
echo Selesai! File ZIP siap diupload ke GitHub Releases.
pause
