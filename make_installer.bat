@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ============================================================
echo  NPU Audio Enhancer - Full Build ^& Installer
echo ============================================================
echo.
echo This script will:
echo   1. Set up Python virtual environment
echo   2. Install dependencies
echo   3. Build EXE with PyInstaller
echo   4. Create Windows installer with Inno Setup
echo.
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.11+
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Step 1: Virtual environment
echo [Step 1/4] Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
)

:: Step 2: Install dependencies using full path
echo [Step 2/4] Installing dependencies...
venv\Scripts\pip.exe install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt
venv\Scripts\pip.exe install "pyinstaller>=6.0"

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.
echo.

:: Step 3: Build EXE
echo [Step 3/4] Building application with PyInstaller...

:: Create required directories
if not exist "models" mkdir models
if not exist "data" mkdir data
if not exist "resources\icons" mkdir resources\icons

:: Generate dummy ONNX models if not present
venv\Scripts\python.exe -c "from src.npu.models import create_all_models; create_all_models('models')" 2>nul

:: Run PyInstaller
venv\Scripts\pyinstaller.exe build.spec --noconfirm

if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

if not exist "dist\NPU_Audio_Enhancer\NPU_Audio_Enhancer.exe" (
    echo [ERROR] EXE not found after build.
    pause
    exit /b 1
)

echo [OK] Application built: dist\NPU_Audio_Enhancer\
echo.

:: Step 4: Build installer
echo [Step 4/4] Building Windows installer...

:: Find Inno Setup
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" (
    where ISCC.exe >nul 2>&1
    if !errorlevel! equ 0 set "ISCC=ISCC.exe"
)

if "%ISCC%"=="" (
    echo [WARNING] Inno Setup 6 not found. Skipping installer creation.
    echo          Install Inno Setup from: https://jrsoftware.org/isdl.php
    echo          Or run: winget install JRSoftware.InnoSetup
    echo.
    echo          After installing, run: installer\build_installer.bat
    echo.
    echo ============================================================
    echo  Build complete (EXE only, no installer)
    echo ============================================================
    echo.
    echo  EXE: dist\NPU_Audio_Enhancer\NPU_Audio_Enhancer.exe
    echo.
    pause
    exit /b 0
)

echo [OK] Inno Setup found: %ISCC%
cd installer
if not exist "output" mkdir output
"%ISCC%" setup.iss

if %errorlevel% neq 0 (
    echo [ERROR] Installer build failed.
    cd ..
    pause
    exit /b 1
)
cd ..

:: Copy installer to Desktop\NPU-AI-main
set "DESKTOP=%USERPROFILE%\Desktop"
set "OUTPUT_DIR=%DESKTOP%\NPU-AI-main"
set "INSTALLER_FILE=NPU_Audio_Enhancer_Setup_1.0.0.exe"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if exist "%OUTPUT_DIR%" (
    if exist "installer\output\%INSTALLER_FILE%" (
        copy /Y "installer\output\%INSTALLER_FILE%" "%OUTPUT_DIR%\%INSTALLER_FILE%" >nul 2>&1
        echo [OK] Installer copied to %OUTPUT_DIR%
    ) else (
        echo [WARNING] Installer not found at installer\output\%INSTALLER_FILE%
    )
)

echo.
echo ============================================================
echo  Build complete!
echo ============================================================
echo.
echo  Output:    %OUTPUT_DIR%
echo  EXE:       dist\NPU_Audio_Enhancer\NPU_Audio_Enhancer.exe
echo  Installer: installer\output\%INSTALLER_FILE%
echo.
echo  The installer includes:
echo    - Desktop shortcut
echo    - Start menu entry
echo    - Optional auto-start
echo    - Uninstaller
echo.

pause
