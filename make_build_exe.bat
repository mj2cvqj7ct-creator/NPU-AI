@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  NPU Audio Enhancer - Build Tool EXE Creator
echo ============================================================
echo.
echo This creates a standalone EXE that builds the app + installer.
echo The EXE will be copied to your Desktop.
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

:: Create Desktop shortcut (sets working directory to project root)
set "DESKTOP=%USERPROFILE%\Desktop"
set "PROJECT_DIR=%CD%"
set "DEST_PATH="

if exist "%DESKTOP%" (
    :: Create a shortcut using PowerShell so working directory is set
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%DESKTOP%\NPU Build Installer.lnk'); $sc.TargetPath = '%PROJECT_DIR%\%EXE_PATH%'; $sc.WorkingDirectory = '%PROJECT_DIR%'; $sc.IconLocation = '%PROJECT_DIR%\resources\icons\app.ico'; $sc.Description = 'Build NPU Audio Enhancer installer'; $sc.Save()" >nul 2>&1
    if !errorlevel! equ 0 (
        set "DEST_PATH=%DESKTOP%\NPU Build Installer.lnk"
        echo [OK] Desktop shortcut created: !DEST_PATH!
    ) else (
        :: Fallback: copy EXE directly
        copy /Y "%EXE_PATH%" "%DESKTOP%\NPU_Build_Installer.exe" >nul
        set "DEST_PATH=%DESKTOP%\NPU_Build_Installer.exe"
        echo [OK] Copied to: !DEST_PATH!
        echo [NOTE] Run from project directory or use --project-dir flag
    )
)

echo.
echo ============================================================
echo  Done!
echo ============================================================
echo.
if defined DEST_PATH (
    echo  Desktop: !DEST_PATH!
) else (
    echo  EXE: %EXE_PATH%
)
echo.
echo  Usage: Double-click the shortcut on your Desktop.
echo         The build tool will automatically find the project.
echo.

pause
