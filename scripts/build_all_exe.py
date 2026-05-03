"""NPU Audio Enhancer - Full Build & Installer (replaces make_installer.bat / build_all.py)."""

from __future__ import annotations

import os
import shutil
import sys

# `python scripts/...py` puts `scripts/` first on sys.path; repo root must precede it.
if not getattr(sys, "frozen", False):
    _scripts_dir = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_scripts_dir)
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

from scripts.common import (
    APP_NAME,
    INSTALLER_FILENAME,
    ensure_venv,
    find_inno_setup,
    get_desktop_path,
    get_project_dir,
    pause_exit,
    print_header,
    print_step,
    run_cmd,
)


def main() -> int:
    print_header(f"{APP_NAME} - Full Build & Installer")

    project_dir = get_project_dir()
    os.chdir(project_dir)
    print(f"Project directory: {project_dir}")

    total_steps = 5

    # --- Step 1: Virtual Environment ---
    print_step(1, total_steps, "Setting up virtual environment...")
    venv_dir, pip_exe, python_exe = ensure_venv(project_dir)
    print("[OK] Virtual environment ready")

    # --- Step 2: Install Dependencies ---
    print_step(2, total_steps, "Installing dependencies...")
    run_cmd([pip_exe, "install", "--upgrade", "pip"], check=False)
    rc = run_cmd([pip_exe, "install", "-r", "requirements.txt"])
    if rc != 0:
        print("[ERROR] Failed to install dependencies")
        pause_exit(1)
    run_cmd([pip_exe, "install", "pyinstaller>=6.0"], check=False)
    print("[OK] Dependencies installed")

    # --- Step 3: Build EXE with PyInstaller ---
    print_step(3, total_steps, "Building application with PyInstaller...")

    os.makedirs("models", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    run_cmd(
        [python_exe, "-c",
         "from src.npu.models import create_all_models; create_all_models('models')"],
        check=False,
    )

    pyinstaller_exe = os.path.join(
        venv_dir,
        "Scripts" if sys.platform == "win32" else "bin",
        "pyinstaller",
    )
    if not os.path.isfile(pyinstaller_exe) and not os.path.isfile(pyinstaller_exe + ".exe"):
        pyinstaller_exe = "pyinstaller"

    rc = run_cmd([pyinstaller_exe, "build.spec", "--noconfirm"])
    if rc != 0:
        print("[ERROR] PyInstaller build failed")
        pause_exit(1)

    exe_path = os.path.join(project_dir, "dist", "NPU_Audio_Enhancer", "NPU_Audio_Enhancer.exe")
    if not os.path.isfile(exe_path):
        print(f"[ERROR] EXE not found at: {exe_path}")
        pause_exit(1)
    print(f"[OK] Application built: {exe_path}")

    # --- Step 4: Build Installer with Inno Setup ---
    print_step(4, total_steps, "Building Windows installer...")

    iscc = find_inno_setup()
    installer_output_dir = os.path.join(project_dir, "installer", "output")
    installer_path = os.path.join(installer_output_dir, INSTALLER_FILENAME)

    if iscc is None:
        print("[WARNING] Inno Setup 6 not found.")
        print("         Install with: winget install JRSoftware.InnoSetup")
        print("         Skipping installer creation.")
        print()
        print(f"[OK] EXE available at: {exe_path}")
        pause_exit(0)

    print(f"[OK] Inno Setup found: {iscc}")
    os.makedirs(installer_output_dir, exist_ok=True)

    iss_path = os.path.join(project_dir, "installer", "setup.iss")
    rc = run_cmd([iscc, iss_path])
    if rc != 0:
        print("[ERROR] Installer build failed")
        pause_exit(1)
    print(f"[OK] Installer built: {installer_path}")

    # --- Step 5: Copy to Desktop\NPU-AI-main ---
    desktop_path = get_desktop_path()
    output_dir = os.path.join(desktop_path, "NPU-AI-main")
    os.makedirs(output_dir, exist_ok=True)
    print_step(5, total_steps, f"Copying installer to {output_dir}...")

    desktop_dest = os.path.join(output_dir, INSTALLER_FILENAME)
    try:
        if os.path.isdir(output_dir):
            shutil.copy2(installer_path, desktop_dest)
            print(f"[OK] Installer copied to: {desktop_dest}")
        else:
            desktop_dest = ""
            print(f"[WARNING] Output path not found: {output_dir}")
            print(f"[INFO] Installer available at: {installer_path}")
    except Exception as e:
        desktop_dest = ""
        print(f"[WARNING] Could not copy: {e}")
        print(f"[INFO] Installer available at: {installer_path}")

    # --- Done ---
    print_header("Build Complete!")
    print(f"  Output directory: {output_dir}")
    print("  Application EXE: dist\\NPU_Audio_Enhancer\\NPU_Audio_Enhancer.exe")
    print(f"  Installer:       {installer_path}")
    if desktop_dest and os.path.isfile(desktop_dest):
        print(f"  Desktop copy:    {desktop_dest}")
    print()
    print("  Double-click the installer to install on your PC.")
    pause_exit(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
