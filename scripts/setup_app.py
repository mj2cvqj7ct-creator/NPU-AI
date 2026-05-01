"""NPU Audio Enhancer - First-time Setup (replaces setup.bat)."""

from __future__ import annotations

import os
import sys

from scripts.common import (
    APP_NAME,
    ensure_venv,
    get_project_dir,
    pause_exit,
    print_header,
    print_step,
    run_cmd,
)


def main() -> int:
    print_header(f"{APP_NAME} - Setup")
    print("  For Windows ARM64 (Snapdragon X)")
    print()

    project_dir = get_project_dir()
    os.chdir(project_dir)
    print(f"Project directory: {project_dir}")

    total = 4

    # Step 1: Virtual environment
    print_step(1, total, "Creating virtual environment...")
    venv_dir, pip_exe, python_exe = ensure_venv(project_dir)
    print("[OK] Virtual environment ready")

    # Step 2: Install dependencies
    print_step(2, total, "Installing dependencies...")
    run_cmd([pip_exe, "install", "--upgrade", "pip", "setuptools", "wheel"], check=False)
    rc = run_cmd([pip_exe, "install", "-r", "requirements.txt"])
    if rc != 0:
        print("[ERROR] Failed to install dependencies")
        pause_exit(1)
    print("[OK] Dependencies installed")

    # Step 3: Audio driver info
    print_step(3, total, "Setting up audio drivers...")
    print("  NOTE: Install SABAJ A20D XMOS USB DAC driver from:")
    print("    https://www.sabaj.com/pages/download")

    # Step 4: Create directories
    print_step(4, total, "Creating data directories...")
    os.makedirs(os.path.join(project_dir, "models"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "data", "recommender"), exist_ok=True)
    print("[OK] Directories created")

    print_header("Setup Complete!")
    print("  To run the app:      Double-click NPU_Run.exe")
    print("  To build installer:  Double-click NPU_Build_Installer.exe")
    print()
    print("  IMPORTANT: Install SABAJ A20D XMOS driver for USB DAC.")
    pause_exit(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
