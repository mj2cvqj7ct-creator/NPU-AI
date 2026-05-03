"""Build all BAT replacements into standalone EXEs.

Usage: python make_all_exe.py
Creates EXEs in dist/ and copies them to Desktop.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

# EXE definitions: (script_path, exe_name, description)
EXE_TARGETS = [
    ("scripts/setup_app.py", "NPU_Setup", "First-time setup"),
    ("scripts/run_app.py", "NPU_Run", "Run the application"),
    ("scripts/build_app.py", "NPU_Build", "Build application EXE"),
    ("scripts/build_all_exe.py", "NPU_Build_Installer", "Build EXE + installer"),
    ("scripts/build_installer.py", "NPU_Installer_Only", "Build installer only"),
    ("scripts/launcher.py", "NPU_Launcher", "Unified launcher menu"),
]


def get_desktop_path() -> str:
    """User Desktop: ~/Desktop (same as scripts.common.get_desktop_path)."""
    return os.path.join(os.path.expanduser("~"), "Desktop")


def main() -> int:
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    print()
    print("=" * 60)
    print("  NPU Audio Enhancer - Build All EXEs")
    print("=" * 60)
    print()

    # Ensure venv and PyInstaller
    venv_dir = os.path.join(project_dir, "venv")
    if not os.path.isdir(venv_dir):
        print("[Step 0] Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)

    if sys.platform == "win32":
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
        pyinstaller_exe = os.path.join(venv_dir, "Scripts", "pyinstaller.exe")
    else:
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        pyinstaller_exe = os.path.join(venv_dir, "bin", "pyinstaller")

    print("[Step 0] Installing PyInstaller...")
    subprocess.run([pip_exe, "install", "pyinstaller>=6.0"], capture_output=True)

    if not os.path.isfile(pyinstaller_exe):
        pyinstaller_exe = "pyinstaller"

    # Icon path
    icon_path = os.path.join(project_dir, "resources", "icons", "app.ico")
    icon_arg = f"--icon={icon_path}" if os.path.isfile(icon_path) else ""

    # Build each EXE
    dist_dir = os.path.join(project_dir, "dist")
    built_exes: list[str] = []
    failed: list[str] = []

    for i, (script, name, desc) in enumerate(EXE_TARGETS, 1):
        print(f"\n[{i}/{len(EXE_TARGETS)}] Building {name}.exe ({desc})...")

        cmd = [
            pyinstaller_exe,
            script,
            "--onefile",
            f"--name={name}",
            "--console",
            "--noconfirm",
            f"--paths={project_dir}",
            "--hidden-import=scripts.common",
        ]
        if icon_arg:
            cmd.append(icon_arg)

        # Add hidden imports for launcher
        if name == "NPU_Launcher":
            for _, _, _ in EXE_TARGETS:
                pass
            cmd.extend([
                "--hidden-import=scripts.setup_app",
                "--hidden-import=scripts.run_app",
                "--hidden-import=scripts.build_app",
                "--hidden-import=scripts.build_all_exe",
                "--hidden-import=scripts.build_installer",
            ])

        result = subprocess.run(cmd)
        exe_path = os.path.join(dist_dir, f"{name}.exe")

        if result.returncode == 0 and os.path.isfile(exe_path):
            print(f"  [OK] {name}.exe built successfully")
            built_exes.append(exe_path)
        else:
            print(f"  [ERROR] Failed to build {name}.exe")
            failed.append(name)

    # Copy to Desktop\NPU-AI-main
    desktop = get_desktop_path()
    output_dir = os.path.join(desktop, "NPU-AI-main")
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n[Copy] Copying EXEs to {output_dir}...")

    if os.path.isdir(output_dir):
        for exe_path in built_exes:
            dest = os.path.join(output_dir, os.path.basename(exe_path))
            try:
                shutil.copy2(exe_path, dest)
                print(f"  [OK] {os.path.basename(exe_path)} -> {output_dir}")
            except Exception as e:
                print(f"  [WARNING] Could not copy {os.path.basename(exe_path)}: {e}")
    else:
        print(f"  [WARNING] Output path not found: {output_dir}")

    # Summary
    print()
    print("=" * 60)
    print("  Build Complete!")
    print("=" * 60)
    print()
    print(f"  Built: {len(built_exes)}/{len(EXE_TARGETS)} EXEs")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    print()
    print(f"  Output: {output_dir}")
    print()
    print("  EXEs:")
    for exe_path in built_exes:
        name = os.path.basename(exe_path).replace(".exe", "")
        desc = next((d for _, n, d in EXE_TARGETS if n == name), "")
        print(f"    {os.path.basename(exe_path):30s} - {desc}")
    print()
    print("  Start with: NPU_Launcher.exe (menu) or NPU_Setup.exe (first time)")
    print()
    input("Press Enter to exit...")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
