"""Guard: desktop helpers must not use ctypes windll / SHGetFolderPath (CI/analyzer safe)."""

from __future__ import annotations

import unittest
from pathlib import Path

_FORBIDDEN = (
    "SHGetFolderPath",
    "CSIDL_DESKTOP",
    "ctypes.windll",
)


class TestNoCtypesDesktopShell(unittest.TestCase):
    _WATCHED = (
        Path("scripts/common.py"),
        Path("build_all.py"),
        Path("make_all_exe.py"),
    )

    def test_watched_files_avoid_shell_desktop_api(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for rel in self._WATCHED:
            path = root / rel
            self.assertTrue(path.is_file(), msg=f"missing {rel}")
            text = path.read_text(encoding="utf-8")
            for needle in _FORBIDDEN:
                self.assertNotIn(
                    needle,
                    text,
                    msg=f"{rel} must not contain {needle!r} (use expanduser Desktop only)",
                )


if __name__ == "__main__":
    unittest.main()
