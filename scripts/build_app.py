"""NPU Audio Enhancer - Build EXE (replaces build.bat)."""

from __future__ import annotations

import os
import shutil
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

    # Step 2: Install dependencies (Windows EXE: slim set matches CI / PyInstaller)
    print_step(2, total, "Installing dependencies...")
    run_cmd([pip_exe, "install", "--upgrade", "pip"], check=False)
    req_file = "requirements.txt"
    if sys.platform == "win32" and os.path.isfile("requirements-windows-build.txt"):
        req_file = "requirements-windows-build.txt"
        print(f"[INFO] Using {req_file} (no torch; same set as GitHub Windows build)")
    rc = run_cmd([pip_exe, "install", "-r", req_file])
    if rc != 0:
        print("[ERROR] Failed to install dependencies")
        pause_exit(1)
    print("[OK] Dependencies installed")

    # Step 3: ONNX Runtime (no-op if already in requirements file)
    print_step(3, total, "Ensuring ONNX Runtime DirectML...")
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

    bundle_dir = os.path.join(project_dir, "dist", "NPU_Audio_Enhancer")
    exe_path = os.path.join(bundle_dir, "NPU_Audio_Enhancer.exe")
    if not os.path.isfile(exe_path):
        print(f"[ERROR] EXE not found at: {exe_path}")
        pause_exit(1)

    # PyInstaller one-folder: copy the entire bundle (DLLs next to the EXE).
    desktop = get_desktop_path()
    dest_name = os.environ.get("NPU_AE_DESKTOP_DIR", "NPU_Audio_Enhancer")
    output_dir = os.path.join(desktop, dest_name)
    try:
        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)
        shutil.copytree(bundle_dir, output_dir)
        dest_exe = os.path.join(output_dir, "NPU_Audio_Enhancer.exe")
        print(f"[OK] App folder copied to: {output_dir}")
        print(f"[OK] Run: {dest_exe}")
    except Exception as e:
        print(f"[WARNING] Could not copy bundle to desktop: {e}")
        print(f"[INFO] Run from build output: {exe_path}")

    print_header("Build Complete!")
    print(f"  Desktop folder: {output_dir}")
    print(f"  Build output:   {bundle_dir}")
    pause_exit(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
