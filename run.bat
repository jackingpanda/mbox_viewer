@echo off
setlocal
title MBOX Viewer

cd /d "%~dp0"

:: 1. Verifikasi Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak terdeteksi di PATH sistem.
    echo Silakan install Python 3.10+ dari https://www.python.org/
    echo dan pastikan opsi "Add python.exe to PATH" dicentang saat instalasi.
    echo.
    pause
    exit /b 1
)

:: 2. Verifikasi PySide6
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Menginstall dependencies dari requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Gagal memasang dependensi PySide6.
        echo.
        pause
        exit /b 1
    )
)

:: 3. Luncurkan GUI MBOX Viewer langsung (tanpa prompt menu CMD)
echo Membuka MBOX Viewer...
if "%~1" neq "" (
    python main.py %*
) else (
    python main.py
)

if errorlevel 1 (
    echo.
    echo [ERROR] Terjadi error saat menjalankan aplikasi (Kode exit: %ERRORLEVEL%).
    pause
)
