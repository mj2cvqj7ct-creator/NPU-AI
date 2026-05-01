"""NPU Audio Enhancer - Unified Build Script.

Single script that handles everything:
  1. Creates Python virtual environment
  2. Installs all dependencies
  3. Tries multiple build tools (PyInstaller, cx_Freeze, Nuitka)
  4. Builds the application EXE
  5. Copies output to Desktop\\NPU-AI-main

Usage:
  python build.py          (full build)
  python build.py --run    (setup + run without building EXE)
  python build.py --setup  (setup only, no build)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

# ── Configuration ──────────────────────────────────────────────────

APP_NAME = "NPU Audio Enhancer"
APP_VERSION = "1.0.0"
EXE_NAME = "NPU_Audio_Enhancer"
ENTRY_POINT = os.path.join("src", "main.py")
OUTPUT_FOLDER = "NPU-AI-main"

HIDDEN_IMPORTS = [
    "PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
    "numpy", "scipy", "scipy.signal", "scipy.fft", "scipy.spatial",
    "sounddevice", "onnxruntime", "librosa", "sklearn",
    "psutil", "comtypes", "pycaw", "pycaw.pycaw", "yaml",
]

EXCLUDES = ["matplotlib", "tkinter", "test", "unittest"]

# Build tools to try in order of preference
BUILD_TOOLS = [
    "pyinstaller",
    "cx_freeze",
    "nuitka",
]


# ── Utilities ──────────────────────────────────────────────────────

def print_header(title: str) -> None:
    line = "=" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n")


def print_step(step: int, total: int, msg: str) -> None:
    print(f"  [{step}/{total}] {msg}")


def run(cmd: list[str], cwd: str | None = None,
        check: bool = True, capture: bool = False,
        timeout: int | None = 600) -> subprocess.CompletedProcess[str]:
    """Run a command, stream output unless capturing."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, timeout=timeout,
            capture_output=capture, text=capture,
        )
        if check and result.returncode != 0:
            tool = os.path.basename(cmd[0])
            print(f"  [ERROR] {tool} exited with code {result.returncode}")
        return result
    except FileNotFoundError:
        print(f"  [ERROR] Command not found: {cmd[0]}")
        return subprocess.CompletedProcess(cmd, 127)
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] Command timed out after {timeout}s")
        return subprocess.CompletedProcess(cmd, 1)


def get_desktop_path() -> str:
    """Get user's Desktop path (Windows shell API with fallback)."""
    if sys.platform == "win32":
        try:
            import ctypes.wintypes
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(  # type: ignore[union-attr]
                None, 0x0010, None, 0, buf,
            )
            if buf.value:
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def venv_path(*parts: str) -> str:
    """Build a path inside the venv."""
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    return os.path.join("venv", scripts, *parts)


def pip_exe() -> str:
    ext = ".exe" if sys.platform == "win32" else ""
    return venv_path(f"pip{ext}")


def python_exe() -> str:
    ext = ".exe" if sys.platform == "win32" else ""
    return venv_path(f"python{ext}")


# ── Step 1: Virtual Environment ───────────────────────────────────

def setup_venv() -> bool:
    """Create virtual environment if it doesn't exist."""
    if os.path.isdir("venv") and os.path.isfile(python_exe()):
        print("  [OK] Virtual environment already exists")
        return True

    print("  Creating virtual environment...")
    result = run([sys.executable, "-m", "venv", "venv"])
    if result.returncode != 0:
        print("  [ERROR] Failed to create virtual environment")
        return False

    if not os.path.isfile(pip_exe()):
        print(f"  [ERROR] pip not found at: {pip_exe()}")
        return False

    print("  [OK] Virtual environment created")
    return True


# ── Step 2: Install Dependencies ──────────────────────────────────

def install_deps() -> bool:
    """Install project dependencies into venv."""
    pip = pip_exe()

    print("  Upgrading pip...")
    run([pip, "install", "--upgrade", "pip"], check=False)

    print("  Installing requirements.txt...")
    result = run([pip, "install", "-r", "requirements.txt"])
    if result.returncode != 0:
        print("  [ERROR] Failed to install requirements")
        return False

    # ARM64-specific ONNX Runtime
    print("  Installing ONNX Runtime DirectML (ARM64)...")
    run([pip, "install", "onnxruntime-directml"], check=False)

    print("  [OK] Dependencies installed")
    return True


# ── Step 3: Setup Resources ──────────────────────────────────────

def setup_resources() -> None:
    """Create required directories and generate models."""
    os.makedirs("models", exist_ok=True)
    os.makedirs(os.path.join("data", "recommender"), exist_ok=True)
    os.makedirs(os.path.join("resources", "icons"), exist_ok=True)

    # Generate ONNX models if needed
    py = python_exe()
    run(
        [py, "-c",
         "from src.npu.models import create_all_models; "
         "create_all_models('models')"],
        check=False,
    )
    print("  [OK] Resources ready")


# ── Step 4: Build EXE ─────────────────────────────────────────────

def install_build_tool(tool: str) -> bool:
    """Install a build tool into the venv."""
    pip = pip_exe()
    packages = {
        "pyinstaller": ["pyinstaller>=6.0"],
        "cx_freeze": ["cx_Freeze>=7.0"],
        "nuitka": ["nuitka", "ordered-set"],
    }
    pkgs = packages.get(tool, [])
    if not pkgs:
        return False

    print(f"  Installing {tool}...")
    result = run([pip, "install"] + pkgs, check=False)
    return result.returncode == 0


def build_with_pyinstaller() -> tuple[str, str] | None:
    """Build EXE using PyInstaller. Returns (exe_path, dist_dir) or None."""
    pyinstaller = venv_path("pyinstaller.exe" if sys.platform == "win32"
                            else "pyinstaller")

    if not os.path.isfile(pyinstaller):
        pyinstaller = venv_path("pyinstaller")
        if not os.path.isfile(pyinstaller):
            print("  [SKIP] pyinstaller executable not found")
            return None

    # Use existing build.spec if available
    if os.path.isfile("build.spec"):
        print("  Using build.spec...")
        result = run([pyinstaller, "build.spec", "--clean", "--noconfirm"])
        dist_dir = os.path.join("dist", EXE_NAME)
        exe_path = os.path.join(dist_dir, f"{EXE_NAME}.exe")
    else:
        # Build with command line args
        cmd = [
            pyinstaller, ENTRY_POINT,
            "--name", EXE_NAME,
            "--noconfirm", "--clean",
            "--windowed",
        ]
        for imp in HIDDEN_IMPORTS:
            cmd.extend(["--hidden-import", imp])
        for exc in EXCLUDES:
            cmd.extend(["--exclude-module", exc])
        if os.path.isdir("resources"):
            cmd.extend(["--add-data", "resources;resources"])
        icon = os.path.join("resources", "icons", "app.ico")
        if os.path.isfile(icon):
            cmd.extend(["--icon", icon])

        result = run(cmd)
        dist_dir = os.path.join("dist", EXE_NAME)
        exe_path = os.path.join(dist_dir, f"{EXE_NAME}.exe")

    if result.returncode == 0 and os.path.isfile(exe_path):
        return exe_path, dist_dir

    # Also check onefile output
    onefile = os.path.join("dist", f"{EXE_NAME}.exe")
    if os.path.isfile(onefile):
        return onefile, ""

    return None


def build_with_cx_freeze() -> tuple[str, str] | None:
    """Build EXE using cx_Freeze. Returns (exe_path, dist_dir) or None."""
    py = python_exe()

    # Create a temporary cx_Freeze setup script
    setup_content = f'''
import sys
from cx_Freeze import setup, Executable

build_options = {{
    "packages": {HIDDEN_IMPORTS!r},
    "excludes": {EXCLUDES!r},
    "include_files": (
        [("resources", "resources")]
        if __import__("os").path.isdir("resources") else []
    ),
}}

setup(
    name="{APP_NAME}",
    version="{APP_VERSION}",
    description="{APP_NAME} - NPU-Accelerated Audio",
    options={{"build_exe": build_options}},
    executables=[
        Executable(
            "{ENTRY_POINT.replace(chr(92), '/')}",
            base="Win32GUI" if sys.platform == "win32" else None,
            target_name="{EXE_NAME}.exe",
            icon=(
                "resources/icons/app.ico"
                if __import__("os").path.isfile("resources/icons/app.ico")
                else None
            ),
        )
    ],
)
'''
    setup_file = "_cx_setup.py"
    try:
        with open(setup_file, "w", encoding="utf-8") as f:
            f.write(setup_content)

        result = run([py, setup_file, "build"])
        if result.returncode != 0:
            return None

        # cx_Freeze outputs to build/exe.*
        build_dir = "build"
        if os.path.isdir(build_dir):
            for d in os.listdir(build_dir):
                if d.startswith("exe"):
                    dist_dir = os.path.join(build_dir, d)
                    exe_path = os.path.join(dist_dir, f"{EXE_NAME}.exe")
                    if os.path.isfile(exe_path):
                        return exe_path, dist_dir
        return None
    finally:
        if os.path.isfile(setup_file):
            os.remove(setup_file)


def build_with_nuitka() -> tuple[str, str] | None:
    """Build EXE using Nuitka. Returns (exe_path, dist_dir) or None."""
    py = python_exe()

    cmd = [
        py, "-m", "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        f"--output-filename={EXE_NAME}.exe",
        "--enable-plugin=pyqt6",
    ]
    if os.path.isdir("resources"):
        cmd.append("--include-data-dir=resources=resources")
    icon = os.path.join("resources", "icons", "app.ico")
    if os.path.isfile(icon):
        cmd.extend(["--windows-icon-from-ico", icon])
    cmd.append(ENTRY_POINT)

    result = run(cmd)
    if result.returncode != 0:
        return None

    # Nuitka outputs to *.dist/
    dist_dir = f"{os.path.splitext(os.path.basename(ENTRY_POINT))[0]}.dist"
    exe_path = os.path.join(dist_dir, f"{EXE_NAME}.exe")
    if os.path.isfile(exe_path):
        return exe_path, dist_dir
    return None


BUILD_FUNCTIONS = {
    "pyinstaller": build_with_pyinstaller,
    "cx_freeze": build_with_cx_freeze,
    "nuitka": build_with_nuitka,
}


def build_exe() -> tuple[str, str] | None:
    """Try each build tool until one succeeds.

    Returns (exe_path, dist_dir) or None.
    dist_dir is the directory containing the EXE and its dependencies.
    Empty string means single-file EXE (no dependencies to copy).
    """
    for tool in BUILD_TOOLS:
        print(f"\n  --- Trying {tool} ---")
        if not install_build_tool(tool):
            print(f"  [SKIP] Failed to install {tool}")
            continue

        build_fn = BUILD_FUNCTIONS.get(tool)
        if not build_fn:
            continue

        try:
            result = build_fn()
            if result:
                exe_path, dist_dir = result
                print(f"  [OK] Build succeeded with {tool}: {exe_path}")
                return exe_path, dist_dir
            print(f"  [FAIL] {tool} did not produce an EXE")
        except Exception as e:
            print(f"  [FAIL] {tool} error: {e}")

    return None


# ── Step 5: Copy to Desktop ───────────────────────────────────────

def copy_to_desktop(exe_path: str, dist_dir: str) -> str:
    """Copy built EXE (and its folder) to Desktop\\NPU-AI-main.

    Args:
        exe_path: Path to the built EXE.
        dist_dir: Directory containing EXE and its dependencies.
                  Empty string means single-file EXE.
    """
    desktop = get_desktop_path()
    output_dir = os.path.join(desktop, OUTPUT_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    exe_name = os.path.basename(exe_path)

    # Directory-mode build: copy entire dist folder
    if dist_dir and os.path.isdir(dist_dir):
        dest_dir = os.path.join(output_dir, EXE_NAME)
        if os.path.isdir(dest_dir):
            shutil.rmtree(dest_dir)
        shutil.copytree(dist_dir, dest_dir)
        final_exe = os.path.join(dest_dir, exe_name)
        print(f"  [OK] App folder copied to: {dest_dir}")
    else:
        # Single-file mode: just copy the EXE
        final_exe = os.path.join(output_dir, exe_name)
        shutil.copy2(exe_path, final_exe)
        print(f"  [OK] EXE copied to: {final_exe}")

    return final_exe


# ── Main ──────────────────────────────────────────────────────────

def main() -> int:
    # Ensure we're in the project directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    mode = "full"
    if "--run" in sys.argv:
        mode = "run"
    elif "--setup" in sys.argv:
        mode = "setup"

    print_header(f"{APP_NAME} v{APP_VERSION} - Unified Build")
    print(f"  Mode: {mode}")
    print(f"  Platform: {sys.platform}")
    print(f"  Python: {sys.version}")
    print(f"  Project: {script_dir}")
    print()

    total = 5 if mode == "full" else (3 if mode == "run" else 2)

    # Step 1: Virtual environment
    print_step(1, total, "Setting up virtual environment...")
    if not setup_venv():
        print("\n  [FATAL] Cannot continue without virtual environment.")
        input("\n  Press Enter to exit...")
        return 1

    # Step 2: Install dependencies
    print_step(2, total, "Installing dependencies...")
    if not install_deps():
        print("\n  [FATAL] Cannot continue without dependencies.")
        input("\n  Press Enter to exit...")
        return 1

    if mode == "setup":
        setup_resources()
        print_header("Setup Complete!")
        print("  Run the app:  python build.py --run")
        print("  Build EXE:    python build.py")
        input("\n  Press Enter to exit...")
        return 0

    # Step 3: Setup resources
    print_step(3, total, "Setting up resources...")
    setup_resources()

    if mode == "run":
        print_header("Starting Application...")
        py = python_exe()
        result = run([py, "-m", "src.main"], timeout=None)
        return result.returncode

    # Step 4: Build EXE
    print_step(4, total, "Building EXE (trying multiple tools)...")
    build_result = build_exe()

    if not build_result:
        print("\n  [FATAL] All build tools failed.")
        print("  Please ensure Python 3.11+ is installed correctly.")
        print("  You can still run the app with: python build.py --run")
        input("\n  Press Enter to exit...")
        return 1

    exe_path, dist_dir = build_result

    # Step 5: Copy to Desktop
    print_step(5, total, "Copying to Desktop...")
    final_exe = copy_to_desktop(exe_path, dist_dir)

    # Summary
    desktop = get_desktop_path()
    output_dir = os.path.join(desktop, OUTPUT_FOLDER)
    print_header("Build Complete!")
    print(f"  Output:  {output_dir}")
    print(f"  EXE:     {final_exe}")
    print()
    print(f"  Run the app: double-click {EXE_NAME}.exe")
    print("  Or run directly: python build.py --run")
    print()
    input("  Press Enter to exit...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
