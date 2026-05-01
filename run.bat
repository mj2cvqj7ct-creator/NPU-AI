@echo off
cd /d "%~dp0"

echo Starting NPU Audio Enhancer...

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11+ not found.
    echo         Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Run via unified build script (setup + run, no EXE build)
python build.py --run

pause
