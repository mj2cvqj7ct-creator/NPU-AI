@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  NPU Audio Enhancer - Installer Builder
echo ============================================
echo.

:: Check if PyInstaller dist exists
if not exist "..\dist\NPU_Audio_Enhancer\NPU_Audio_Enhancer.exe" (
    echo [ERROR] PyInstaller build not found.
    echo         Run build.bat first to create the application.
    echo.
    echo         cd ..
    echo         build.bat
    echo.
    pause
    exit /b 1
)

:: Find Inno Setup
set "ISCC="

:: Check common install locations
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)

:: Check PATH
if "%ISCC%"=="" (
    where ISCC.exe >nul 2>&1
    if !errorlevel! equ 0 (
        set "ISCC=ISCC.exe"
    )
)

:: If not found, offer to download
if "%ISCC%"=="" (
    echo [WARNING] Inno Setup 6 not found.
    echo.
    echo Please install Inno Setup 6 from:
    echo   https://jrsoftware.org/isdl.php
    echo.
    echo Or install via winget:
    echo   winget install JRSoftware.InnoSetup
    echo.
    choice /C YN /M "Open download page now?"
    if !errorlevel! equ 1 (
        start https://jrsoftware.org/isdl.php
    )
    pause
    exit /b 1
)

echo [OK] Inno Setup found: %ISCC%
echo.

:: Create output directory
if not exist "output" mkdir output

:: Build installer
echo Building installer...
echo.
"%ISCC%" setup.iss

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installer build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Installer built successfully!
echo ============================================
echo.
echo Output: installer\output\NPU_Audio_Enhancer_Setup_3.0.0.exe
echo.

pause
