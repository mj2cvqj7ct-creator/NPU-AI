@echo off
cd /d "%~dp0"
REM ============================================================
REM NPU Audio Enhancer - Windows ARM64 Build Script
REM Requires: Python 3.11+, pip
REM ============================================================

echo.
echo ===================================
echo  NPU Audio Enhancer Build Script
echo  Target: Windows ARM64 (Snapdragon X)
echo ===================================
echo.

REM Check Python version
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment
echo [1/5] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
)

REM Install dependencies using full path
echo [2/5] Installing dependencies...
venv\Scripts\pip.exe install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt

REM Install ARM64-specific ONNX Runtime with DirectML
echo [3/5] Installing ONNX Runtime DirectML for ARM64...
venv\Scripts\pip.exe install onnxruntime-directml

REM Create models directory
echo [4/5] Setting up resources...
if not exist "models" mkdir models
if not exist "data\recommender" mkdir data\recommender

REM Build EXE
echo [5/5] Building EXE with PyInstaller...
venv\Scripts\pip.exe install "pyinstaller>=6.0"
venv\Scripts\pyinstaller.exe build.spec --clean --noconfirm

echo.
echo ===================================
echo  Build Complete!
echo  Output: dist\NPU_Audio_Enhancer\
echo  Run:    dist\NPU_Audio_Enhancer\NPU_Audio_Enhancer.exe
echo ===================================
echo.
pause
