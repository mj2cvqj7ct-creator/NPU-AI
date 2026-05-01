"""
NPU Audio Enhancer - One-Click Build & Installer EXE.

This script automates the entire build pipeline:
  1. Setup Python virtual environment
  2. Install dependencies
  3. Build application EXE with PyInstaller
  4. Create Windows installer with Inno Setup
  5. Copy installer to user's Desktop

Can be compiled to a standalone EXE with PyInstaller:
  pyinstaller build_all.py --onefile --name "NPU_Build_Installer" --console
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

# --- Configuration ---
APP_NAME = "NPU Audio Enhancer"
APP_VERSION = "1.0.0"
INSTALLER_FILENAME = f"NPU_Audio_Enhancer_Setup_{APP_VERSION}.exe"
DESKTOP_PATH = r"C:\Users\look5\Desktop"


def print_header(title: str) -> None:
    line = "=" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n")


def print_step(step: int, total: int, msg: str) -> None:
    print(f"[Step {step}/{total}] {msg}")


def find_python() -> str:
    """Find Python executable."""
    for candidate in ["python", "python3", "py -3"]:
        try:
            result = subprocess.run(
                candidate.split(),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return candidate.split()[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return "python"


def find_inno_setup() -> str | None:
    """Find Inno Setup compiler (ISCC.exe)."""
    candidates = [
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Inno Setup 6", "ISCC.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path

    if shutil.which("ISCC.exe"):
        return "ISCC.exe"

    return None


def run_cmd(cmd: str | list[str], cwd: str | None = None, check: bool = True) -> int:
    """Run a command and stream output."""
    if isinstance(cmd, str):
        cmd_list = cmd.split()
    else:
        cmd_list = cmd

    try:
        result = subprocess.run(
            cmd_list,
            cwd=cwd,
            timeout=600,
        )
        if check and result.returncode != 0:
            print(f"[ERROR] Command failed with exit code {result.returncode}")
            return result.returncode
        return result.returncode
    except FileNotFoundError:
        print(f"[ERROR] Command not found: {cmd_list[0]}")
        return 1
    except subprocess.TimeoutExpired:
        print("[ERROR] Command timed out")
        return 1


def get_project_dir() -> str:
    """Get the project root directory."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    print_header(f"{APP_NAME} - Full Build & Installer")

    project_dir = get_project_dir()
    os.chdir(project_dir)
    print(f"Project directory: {project_dir}")

    total_steps = 5

    # --- Step 1: Virtual Environment ---
    print_step(1, total_steps, "Setting up virtual environment...")
    venv_dir = os.path.join(project_dir, "venv")
    if not os.path.isdir(venv_dir):
        rc = run_cmd([sys.executable, "-m", "venv", "venv"])
        if rc != 0:
            print("[ERROR] Failed to create virtual environment")
            input("Press Enter to exit...")
            return 1

    if sys.platform == "win32":
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        python_exe = os.path.join(venv_dir, "bin", "python")

    print("[OK] Virtual environment ready")

    # --- Step 2: Install Dependencies ---
    print_step(2, total_steps, "Installing dependencies...")
    run_cmd([pip_exe, "install", "--upgrade", "pip"], check=False)
    rc = run_cmd([pip_exe, "install", "-r", "requirements.txt"])
    if rc != 0:
        print("[ERROR] Failed to install dependencies")
        input("Press Enter to exit...")
        return 1

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
        input("Press Enter to exit...")
        return 1

    exe_path = os.path.join(project_dir, "dist", "NPU_Audio_Enhancer", "NPU_Audio_Enhancer.exe")
    if not os.path.isfile(exe_path):
        print(f"[ERROR] EXE not found at: {exe_path}")
        input("Press Enter to exit...")
        return 1

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
        input("Press Enter to exit...")
        return 0

    print(f"[OK] Inno Setup found: {iscc}")
    os.makedirs(installer_output_dir, exist_ok=True)

    iss_path = os.path.join(project_dir, "installer", "setup.iss")
    rc = run_cmd([iscc, iss_path])
    if rc != 0:
        print("[ERROR] Installer build failed")
        input("Press Enter to exit...")
        return 1

    print(f"[OK] Installer built: {installer_path}")

    # --- Step 5: Copy to Desktop ---
    print_step(5, total_steps, f"Copying installer to {DESKTOP_PATH}...")

    desktop_dest = os.path.join(DESKTOP_PATH, INSTALLER_FILENAME)
    try:
        if os.path.isdir(DESKTOP_PATH):
            shutil.copy2(installer_path, desktop_dest)
            print(f"[OK] Installer copied to: {desktop_dest}")
        else:
            print(f"[WARNING] Desktop path not found: {DESKTOP_PATH}")
            alt_desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if os.path.isdir(alt_desktop):
                alt_dest = os.path.join(alt_desktop, INSTALLER_FILENAME)
                shutil.copy2(installer_path, alt_dest)
                print(f"[OK] Installer copied to: {alt_dest}")
            else:
                print(f"[INFO] Installer available at: {installer_path}")
    except Exception as e:
        print(f"[WARNING] Could not copy to desktop: {e}")
        print(f"[INFO] Installer available at: {installer_path}")

    # --- Done ---
    print_header("Build Complete!")
    print("  Application EXE: dist\\NPU_Audio_Enhancer\\NPU_Audio_Enhancer.exe")
    print(f"  Installer:       {installer_path}")
    if os.path.isfile(desktop_dest):
        print(f"  Desktop copy:    {desktop_dest}")
    print()
    print("  Double-click the installer to install on your PC.")
    print()
    input("Press Enter to exit...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
