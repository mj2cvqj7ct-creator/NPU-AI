"""NPU Audio Enhancer - Build Installer Only (replaces installer/build_installer.bat)."""

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
    INSTALLER_FILENAME,
    find_inno_setup,
    get_project_dir,
    pause_exit,
    print_header,
    run_cmd,
)


def main() -> int:
    print_header(f"{APP_NAME} - Installer Builder")

    project_dir = get_project_dir()
    os.chdir(project_dir)

    # Check if app EXE exists
    app_exe = os.path.join("dist", "NPU_Audio_Enhancer", "NPU_Audio_Enhancer.exe")
    if not os.path.isfile(app_exe):
        print("[ERROR] PyInstaller build not found.")
        print("        Run NPU_Build.exe first to build the application.")
        pause_exit(1)

    # Find Inno Setup
    iscc = find_inno_setup()
    if iscc is None:
        print("[WARNING] Inno Setup 6 not found.")
        print()
        print("  Install from: https://jrsoftware.org/isdl.php")
        print("  Or run: winget install JRSoftware.InnoSetup")
        pause_exit(1)

    print(f"[OK] Inno Setup found: {iscc}")

    # Build installer
    installer_dir = os.path.join(project_dir, "installer")
    output_dir = os.path.join(installer_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    iss_path = os.path.join(installer_dir, "setup.iss")
    rc = run_cmd([iscc, iss_path])
    if rc != 0:
        print("[ERROR] Installer build failed.")
        pause_exit(1)

    installer_path = os.path.join(output_dir, INSTALLER_FILENAME)
    print_header("Installer Built!")
    print(f"  Output: {installer_path}")
    pause_exit(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
