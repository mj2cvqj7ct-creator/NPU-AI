@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ============================================================
echo  NPU Audio Enhancer - Build Tool EXE Creator
echo ============================================================
echo.
echo This creates a standalone EXE that builds the app + installer.
echo The EXE will be copied to Desktop\NPU-AI-main.
echo.
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

:: Setup venv if needed
if not exist "venv" (
    echo [Step 1] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

:: Install PyInstaller using full path
echo [Step 2] Installing PyInstaller...
venv\Scripts\pip.exe install "pyinstaller>=6.0"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install PyInstaller
    pause
    exit /b 1
)

:: Build the build tool EXE
echo [Step 3] Building NPU_Build_Installer.exe...
venv\Scripts\pyinstaller.exe build_all.spec --noconfirm

if %errorlevel% neq 0 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

set "EXE_PATH=dist\NPU_Build_Installer.exe"
if not exist "%EXE_PATH%" (
    echo [ERROR] EXE not found at %EXE_PATH%
    pause
    exit /b 1
)

echo [OK] Build tool created: %EXE_PATH%

:: Copy to Desktop\NPU-AI-main
set "DESKTOP=%USERPROFILE%\Desktop"
set "OUTPUT_DIR=%DESKTOP%\NPU-AI-main"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

set "DEST_PATH="
if exist "%OUTPUT_DIR%" (
    copy /Y "%EXE_PATH%" "%OUTPUT_DIR%\NPU_Build_Installer.exe" >nul
    set "DEST_PATH=%OUTPUT_DIR%\NPU_Build_Installer.exe"
    echo [OK] Copied to: !DEST_PATH!
)

echo.
echo ============================================================
echo  Done!
echo ============================================================
echo.
if defined DEST_PATH (
    echo  Output: !DEST_PATH!
) else (
    echo  EXE: %EXE_PATH%
)
echo.
echo  Usage: Double-click NPU_Build_Installer.exe in Desktop\NPU-AI-main
echo.

pause
