@echo off
setlocal EnableExtensions
chcp 65001 >nul
title NPU Audio Enhancer - デスクトップに EXE を作成

echo ============================================================
echo  NPU オーディオエンハンサー - ローカル EXE ビルド
echo ============================================================
echo.
echo  このリポジトリのルートでダブルクリックしてください。
echo  完了後、デスクトップにフォルダ「NPU_Audio_Enhancer」ができ、
echo  その中の NPU_Audio_Enhancer.exe を起動します。
echo.
echo  別のフォルダ名にしたい場合（例: 日本語フォルダ名）:
echo    set NPU_AE_DESKTOP_DIR=NPUオーディオ作成アプリ
echo    build_desktop.bat
echo.
echo ============================================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Python が見つかりません。Python 3.12 をインストールしてください。
    pause
    exit /b 1
)

python scripts\build_app.py
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" (
    echo [エラー] ビルドが失敗しました ^(終了コード %RC%^)
    pause
    exit /b %RC%
)

echo.
echo 完了しました。デスクトップの NPU_Audio_Enhancer を開いてください。
pause
exit /b 0
