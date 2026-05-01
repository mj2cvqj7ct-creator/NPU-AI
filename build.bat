@echo off
cd /d "%~dp0"

echo.
echo ============================================================
echo  NPU Audio Enhancer - Unified Build
echo  Target: Windows ARM64 (Snapdragon X)
echo ============================================================
echo.
echo  This script will:
echo    1. Create virtual environment
echo    2. Install all dependencies
echo    3. Try PyInstaller / cx_Freeze / Nuitka
echo    4. Build EXE
echo    5. Copy to Desktop\NPU-AI-main
echo.
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11+ not found.
    echo         Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Run unified build script
python build.py %*

pause
