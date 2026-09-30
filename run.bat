@echo off
setlocal
title MBOX Viewer

cd /d "%~dp0"

:: 1. Verify Python Installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo and ensure "Add python.exe to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Verify PySide6 and dependencies
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install required dependencies.
        echo.
        pause
        exit /b 1
    )
)

:: 3. Launch MBOX Viewer GUI
echo Launching MBOX Viewer...
if "%~1" neq "" (
    python main.py %*
) else (
    python main.py
)

if errorlevel 1 (
    echo.
    echo [ERROR] An error occurred while running the application (Exit code: %ERRORLEVEL%).
    pause
)
