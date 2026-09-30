@echo off
setlocal
title MBOX Viewer Launcher

cd /d "%~dp0"

:: 1. Verifikasi Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python tidak terdeteksi di PATH sistem.
    echo Silakan install Python 3.10+ dari https://www.python.org/
    echo dan pastikan opsi "Add python.exe to PATH" dicentang.
    echo.
    pause
    exit /b 1
)

:: 2. Verifikasi PySide6
python -c "import PySide6" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Dependensi PySide6 belum terpasang.
    echo Sedang menginstall dependencies dari requirements.txt...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Gagal memasang dependensi PySide6.
        echo.
        pause
        exit /b 1
    )
)

:: 3. Luncurkan GUI MBOX Viewer langsung (tanpa menu prompt CMD)
:: Jika ada file yang di-drag-and-drop ke run.bat atau melalui CLI argumen
if "%~1" neq "" (
    where pythonw >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        start "" pythonw main.py %*
    ) else (
        start "" python main.py %*
    )
    exit /b 0
)

:: Luncurkan GUI MBOX Viewer langsung ke Welcome Screen interaktif
where pythonw >nul 2>&1
if %ERRORLEVEL% equ 0 (
    start "" pythonw main.py
) else (
    start "" python main.py
)
exit /b 0
