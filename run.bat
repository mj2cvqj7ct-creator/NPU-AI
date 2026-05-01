@echo off
cd /d "%~dp0"
REM ============================================================
REM NPU Audio Enhancer - Quick Run Script
REM Run directly without building EXE
REM ============================================================

echo Starting NPU Audio Enhancer...

REM Activate venv if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Create required directories
if not exist "models" mkdir models
if not exist "data\recommender" mkdir data\recommender

REM Run the application
python -m src.main

pause
