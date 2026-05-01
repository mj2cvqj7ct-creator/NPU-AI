@echo off
cd /d "%~dp0"
REM ============================================================
REM NPU Audio Enhancer - Quick Run Script
REM Run directly without building EXE
REM ============================================================

echo Starting NPU Audio Enhancer...

REM Create required directories
if not exist "models" mkdir models
if not exist "data\recommender" mkdir data\recommender

REM Run the application using full venv path
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m src.main
) else (
    echo [WARNING] Virtual environment not found. Running setup first...
    python -m venv venv
    venv\Scripts\pip.exe install -r requirements.txt
    venv\Scripts\python.exe -m src.main
)

pause
