# Download Windows EXE zip from GitHub Releases into repo root and extract (Cursor workspace).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
python (Join-Path $Root "scripts\fetch_windows_release_zip.py") --extract @args
