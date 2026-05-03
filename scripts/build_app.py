"""NPU Audio Enhancer - Build EXE (replaces build.bat)."""

from __future__ import annotations

import os
import sys

if not getattr(sys, "frozen", False):
    _scripts_dir = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_scripts_dir)
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

from scripts.common import (
    APP_NAME,
    ensure_venv,
    get_desktop_path,
    get_project_dir,
    pause_exit,
    print_header,
    print_step,
    run_cmd,
)


def main() -> int:
    print_header(f"{APP_NAME} - Build EXE")
    print("  Target: Windows ARM64 (Snapdragon X)")
    print()

    project_dir = get_project_dir()
    os.chdir(project_dir)
    print(f"Project directory: {project_dir}")

    total = 5

    # Step 1: Virtual environment
    print_step(1, total, "Creating virtual environment...")
    venv_dir, pip_exe, python_exe = ensure_venv(project_dir)
    print("[OK] Virtual environment ready")

    # Step 2: Install dependencies
    print_step(2, total, "Installing dependencies...")
    run_cmd([pip_exe, "install", "--upgrade", "pip"], check=False)
    rc = run_cmd([pip_exe, "install", "-r", "requirements.txt"])
    if rc != 0:
        print("[ERROR] Failed to install dependencies")
        pause_exit(1)
    print("[OK] Dependencies installed")

    # Step 3: ONNX Runtime
    print_step(3, total, "Installing ONNX Runtime DirectML for ARM64...")
    run_cmd([pip_exe, "install", "onnxruntime-directml"], check=False)

    # Step 4: Setup resources
    print_step(4, total, "Setting up resources...")
    os.makedirs("models", exist_ok=True)
    os.makedirs(os.path.join("data", "recommender"), exist_ok=True)

    run_cmd(
        [python_exe, "-c",
         "from src.npu.models import create_all_models; create_all_models('models')"],
        check=False,
    )
    print("[OK] Resources ready")

    # Step 5: Build EXE
    print_step(5, total, "Building EXE with PyInstaller...")
    run_cmd([pip_exe, "install", "pyinstaller>=6.0"], check=False)

    pyinstaller_exe = os.path.join(
        venv_dir,
        "Scripts" if sys.platform == "win32" else "bin",
        "pyinstaller",
    )
    if not os.path.isfile(pyinstaller_exe) and not os.path.isfile(pyinstaller_exe + ".exe"):
        pyinstaller_exe = "pyinstaller"

    rc = run_cmd([pyinstaller_exe, "build.spec", "--clean", "--noconfirm"])
    if rc != 0:
        print("[ERROR] PyInstaller build failed")
        pause_exit(1)

    exe_path = os.path.join("dist", "NPU_Audio_Enhancer", "NPU_Audio_Enhancer.exe")
    if not os.path.isfile(exe_path):
        print(f"[ERROR] EXE not found at: {exe_path}")
        pause_exit(1)

    # Copy to Desktop\NPU-AI-main
    import shutil

    desktop = get_desktop_path()
    output_dir = os.path.join(desktop, "NPU-AI-main")
    os.makedirs(output_dir, exist_ok=True)
    try:
        dest_exe = os.path.join(output_dir, "NPU_Audio_Enhancer.exe")
        shutil.copy2(exe_path, dest_exe)
        print(f"[OK] EXE copied to: {dest_exe}")
    except Exception as e:
        print(f"[WARNING] Could not copy to desktop: {e}")
        print(f"[INFO] EXE available at: {exe_path}")

    print_header("Build Complete!")
    print(f"  Output: {output_dir}")
    print(f"  EXE:   {exe_path}")
    pause_exit(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
