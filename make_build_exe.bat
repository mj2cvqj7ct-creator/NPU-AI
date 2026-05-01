@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  NPU Audio Enhancer - Build Tool EXE Creator
echo ============================================================
echo.
echo This creates a standalone EXE that builds the app + installer.
echo The EXE will be copied to: C:\Users\look5\Desktop\
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
    python -m venv venv
)
call venv\Scripts\activate.bat

:: Install PyInstaller
pip install "pyinstaller>=6.0" >nul 2>&1

:: Build the build tool EXE
echo Building NPU_Build_Installer.exe...
pyinstaller build_all.spec --noconfirm

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

:: Copy to Desktop
set "DESKTOP=C:\Users\look5\Desktop"
if exist "%DESKTOP%" (
    copy /Y "%EXE_PATH%" "%DESKTOP%\NPU_Build_Installer.exe" >nul
    echo [OK] Copied to: %DESKTOP%\NPU_Build_Installer.exe
) else (
    echo [WARNING] Desktop path not found: %DESKTOP%
    echo          EXE is at: %EXE_PATH%
)

echo.
echo ============================================================
echo  Done!
echo ============================================================
echo.
echo  EXE: %DESKTOP%\NPU_Build_Installer.exe
echo.
echo  Usage: Double-click NPU_Build_Installer.exe on your Desktop
echo         to build the app and create the installer.
echo.
echo  NOTE: The EXE must be run from the project directory,
echo        or copy the entire project folder alongside it.
echo.

pause
