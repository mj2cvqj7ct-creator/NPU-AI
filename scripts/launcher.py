"""NPU Audio Enhancer - Unified Launcher (replaces all BAT files).

Double-click this EXE to see a menu of all available actions.
"""

from __future__ import annotations

import os
import sys

if not getattr(sys, "frozen", False):
    _scripts_dir = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_scripts_dir)
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

from scripts.common import APP_NAME, APP_VERSION, print_header


def main() -> int:
    print_header(f"{APP_NAME} v{APP_VERSION} - Launcher")
    print("  Select an action:\n")
    print("  [1] Setup       - First-time environment setup")
    print("  [2] Run          - Start the application")
    print("  [3] Build EXE    - Build standalone application EXE")
    print("  [4] Build All    - Build EXE + create installer")
    print("  [5] Installer    - Create installer (after Build EXE)")
    print("  [0] Exit")
    print()

    choice = input("  Enter choice (0-5): ").strip()

    if choice == "1":
        from scripts.setup_app import main as setup_main
        return setup_main()
    elif choice == "2":
        from scripts.run_app import main as run_main
        return run_main()
    elif choice == "3":
        from scripts.build_app import main as build_main
        return build_main()
    elif choice == "4":
        from scripts.build_all_exe import main as build_all_main
        return build_all_main()
    elif choice == "5":
        from scripts.build_installer import main as installer_main
        return installer_main()
    elif choice == "0":
        return 0
    else:
        print(f"\n  [ERROR] Invalid choice: {choice}")
        input("Press Enter to exit...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
