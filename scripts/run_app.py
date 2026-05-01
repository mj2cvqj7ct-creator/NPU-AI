"""NPU Audio Enhancer - Quick Run (replaces run.bat)."""

from __future__ import annotations

import os
import sys

from scripts.common import (
    APP_NAME,
    get_project_dir,
    get_venv_executables,
    print_header,
    run_cmd,
)


def main() -> int:
    print_header(f"{APP_NAME} - Run")

    project_dir = get_project_dir()
    os.chdir(project_dir)

    os.makedirs(os.path.join(project_dir, "models"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "data", "recommender"), exist_ok=True)

    _venv_dir, _pip_exe, python_exe = get_venv_executables(project_dir)

    if not os.path.isfile(python_exe):
        print("[ERROR] Virtual environment not found.")
        print("        Run NPU_Setup.exe first.")
        input("Press Enter to exit...")
        return 1

    print("Starting NPU Audio Enhancer...")
    rc = run_cmd([python_exe, "-m", "src.main"])
    return rc


if __name__ == "__main__":
    sys.exit(main())
