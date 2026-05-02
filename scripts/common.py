"""Shared utilities for NPU Audio Enhancer build scripts."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

APP_NAME = "NPU Audio Enhancer"
APP_VERSION = "3.6.0"
INSTALLER_FILENAME = f"NPU_Audio_Enhancer_Setup_{APP_VERSION}.exe"

# Default output directory for built EXEs on target machine
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "NPU-AI-main")

_PROJECT_SENTINELS = ("requirements.txt", "build.spec", "pyproject.toml")


def get_desktop_path() -> str:
    """Get the user's Desktop path, using Windows shell API if available."""
    if sys.platform == "win32":
        try:
            import ctypes.wintypes

            CSIDL_DESKTOPDIRECTORY = 0x0010
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(  # type: ignore[union-attr]
                None, CSIDL_DESKTOPDIRECTORY, None, 0, buf,
            )
            if buf.value:
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def print_header(title: str) -> None:
    line = "=" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n")


def print_step(step: int, total: int, msg: str) -> None:
    print(f"[Step {step}/{total}] {msg}")


def find_python() -> str:
    """Find a system Python 3 executable path."""
    candidates = [("python",), ("python3",), ("py", "-3")]
    for cmd in candidates:
        try:
            result = subprocess.run(
                list(cmd) + ["--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                resolve = subprocess.run(
                    list(cmd) + ["-c", "import sys; print(sys.executable)"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if resolve.returncode == 0 and resolve.stdout.strip():
                    return resolve.stdout.strip()
                found = shutil.which(cmd[0])
                if found:
                    return found
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return "python"


def find_inno_setup() -> str | None:
    """Find Inno Setup compiler (ISCC.exe)."""
    candidates = [
        os.path.join(
            os.environ.get("ProgramFiles(x86)", ""), "Inno Setup 6", "ISCC.exe",
        ),
        os.path.join(
            os.environ.get("ProgramFiles", ""), "Inno Setup 6", "ISCC.exe",
        ),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    if shutil.which("ISCC.exe"):
        return "ISCC.exe"
    return None


def run_cmd(
    cmd: str | list[str],
    cwd: str | None = None,
    check: bool = True,
) -> int:
    """Run a command and stream output."""
    cmd_list = cmd.split() if isinstance(cmd, str) else cmd
    try:
        result = subprocess.run(cmd_list, cwd=cwd, timeout=600)
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


def is_project_root(path: str) -> bool:
    """Check if a directory contains project sentinel files."""
    if not os.path.isdir(path):
        return False
    return any(os.path.isfile(os.path.join(path, s)) for s in _PROJECT_SENTINELS)


def get_project_dir() -> str:
    """Get the project root directory.

    Handles both script and frozen EXE modes. When frozen, searches for
    sentinel files to find the real project root.
    """
    if not getattr(sys, "frozen", False):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    exe_dir = os.path.dirname(sys.executable)
    if is_project_root(exe_dir):
        return exe_dir

    cwd = os.getcwd()
    if is_project_root(cwd):
        return cwd

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.startswith("--project-dir="):
            candidate = arg.split("=", 1)[1]
            if is_project_root(candidate):
                return candidate
        elif arg == "--project-dir" and i < len(sys.argv) - 1:
            candidate = sys.argv[i + 1]
            if is_project_root(candidate):
                return candidate

    print("[WARNING] Project directory not found at EXE location.")
    print("          Please enter the path to the NPU-AI project folder,")
    print("          or drag-and-drop the folder here:")
    print()
    user_path = input("Project path: ").strip().strip('"')
    if user_path and is_project_root(user_path):
        return user_path

    print(f"[ERROR] '{user_path}' is not a valid project directory.")
    print(f"        Expected to find: {', '.join(_PROJECT_SENTINELS)}")
    input("Press Enter to exit...")
    sys.exit(1)


def get_venv_executables(project_dir: str) -> tuple[str, str, str]:
    """Return (venv_dir, pip_exe, python_exe) paths for the project."""
    venv_dir = os.path.join(project_dir, "venv")
    if sys.platform == "win32":
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        python_exe = os.path.join(venv_dir, "bin", "python")
    return venv_dir, pip_exe, python_exe


def ensure_venv(project_dir: str) -> tuple[str, str, str]:
    """Ensure virtual environment exists, create if not. Returns paths."""
    venv_dir, pip_exe, python_exe = get_venv_executables(project_dir)
    if not os.path.isdir(venv_dir):
        if getattr(sys, "frozen", False):
            python_cmd = find_python()
            print(f"[INFO] Using system Python: {python_cmd}")
        else:
            python_cmd = sys.executable
        rc = run_cmd([python_cmd, "-m", "venv", "venv"])
        if rc != 0:
            print("[ERROR] Failed to create virtual environment")
            input("Press Enter to exit...")
            sys.exit(1)
    return venv_dir, pip_exe, python_exe


def pause_exit(code: int = 0) -> None:
    """Pause for user input then exit."""
    input("Press Enter to exit...")
    sys.exit(code)
