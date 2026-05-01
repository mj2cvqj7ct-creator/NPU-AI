@echo off
cd /d "%~dp0"
REM ============================================================
REM NPU Audio Enhancer - First-time Setup Script
REM ============================================================

echo.
echo ===================================
echo  NPU Audio Enhancer Setup
echo  For Windows ARM64 (Snapdragon X)
echo ===================================
echo.

REM Check Python
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.11+ is required
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment
echo [1/4] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
)

REM Install core dependencies using full path
echo [2/4] Installing dependencies...
venv\Scripts\pip.exe install --upgrade pip setuptools wheel
venv\Scripts\pip.exe install -r requirements.txt

REM Install XMOS USB DAC driver support
echo [3/4] Setting up audio drivers...
echo NOTE: Install SABAJ A20D XMOS USB DAC driver from:
echo   https://www.sabaj.com/pages/download
echo.

REM Create directories
echo [4/4] Creating data directories...
if not exist "models" mkdir models
if not exist "data\recommender" mkdir data\recommender

echo.
echo ===================================
echo  Setup Complete!
echo.
echo  To run: run.bat
echo  To build EXE: build.bat
echo.
echo  IMPORTANT: Install SABAJ A20D XMOS driver
echo  for USB DAC integration.
echo ===================================
echo.
pause
