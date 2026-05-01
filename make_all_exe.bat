@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  NPU Audio Enhancer - Build All EXEs
echo ============================================================
echo.
echo  This will build all tools into standalone EXEs:
echo    NPU_Setup.exe          - First-time setup
echo    NPU_Run.exe            - Run the application
echo    NPU_Build.exe          - Build application EXE
echo    NPU_Build_Installer.exe - Build EXE + installer
echo    NPU_Installer_Only.exe - Build installer only
echo    NPU_Launcher.exe       - Unified launcher menu
echo.
echo  All EXEs will be copied to your Desktop.
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

:: Run the build script
python make_all_exe.py

pause
