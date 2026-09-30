@echo off
setlocal
title MBOX Viewer Launcher

cd /d "%~dp0"

echo ====================================================
echo               MBOX Viewer Launcher
echo ====================================================

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
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Gagal memasang dependensi PySide6.
        echo.
        pause
        exit /b 1
    )
    echo [OK] Dependensi berhasil dipasang.
    echo.
)

:: 3. Path default Gmail Takeout
set "DEFAULT_MBOX=D:\secret\M\gmail\Takeout\Mail\All mail Including Spam and Trash.mbox"

:: 4. Jika ada file yang di-drag-and-drop atau dijadikan argumen CLI
if "%~1" neq "" goto :LAUNCH_ARG

:: 5. Jika file default Takeout tidak ada, langsung buka aplikasi kosong
if not exist "%DEFAULT_MBOX%" goto :LAUNCH_BLANK

:: 6. Menu interaktif: Menunggu input pengguna tanpa batas waktu (tanpa auto-timeout)
echo Ditemukan file Gmail Takeout (8.76 GB):
echo "%DEFAULT_MBOX%"
echo.
echo [1] Buka file Gmail Takeout langsung
echo [2] Buka MBOX Viewer kosong (Pilih file manual di dalam aplikasi)
echo.

set "CHOICE="
set /p "CHOICE=Masukkan pilihan Anda (1 atau 2, tekan Enter untuk [1]): "
if "%CHOICE%"=="" set "CHOICE=1"

if "%CHOICE%"=="2" goto :LAUNCH_BLANK
goto :LAUNCH_TAKEOUT

:LAUNCH_ARG
echo.
echo Membuka file dari argumen: "%~1"
python main.py %*
goto :FINISH

:LAUNCH_TAKEOUT
echo.
echo Membuka MBOX Viewer dengan file Gmail Takeout...
python main.py "%DEFAULT_MBOX%"
goto :FINISH

:LAUNCH_BLANK
echo.
echo Membuka MBOX Viewer kosong...
python main.py
goto :FINISH

:FINISH
if %ERRORLEVEL% neq 0 (
    echo.
    echo [INFO] Aplikasi ditutup dengan kode exit: %ERRORLEVEL%
)
endlocal
exit /b 0
