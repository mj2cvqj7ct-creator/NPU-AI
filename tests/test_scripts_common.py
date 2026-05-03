"""Regression tests for scripts/common.py (no frozen EXE)."""

from __future__ import annotations

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import scripts.common as common


def _patch_frozen_sys(argv: list[str], tmp: str) -> SimpleNamespace:
    """Minimal sys stand-in for get_project_dir() frozen-mode tests."""
    return SimpleNamespace(
        argv=argv,
        frozen=True,
        executable=os.path.join(tmp, "fake_launcher.exe"),
    )


class TestGetProjectDir(unittest.TestCase):
    def test_project_dir_equal_form(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "pyproject.toml")
            with open(marker, "w", encoding="utf-8") as f:
                f.write("[project]\n")
            fake_argv = ["launcher.exe", f"--project-dir={tmp}", "--other"]
            with patch.object(
                common,
                "sys",
                _patch_frozen_sys(fake_argv, tmp),
            ):
                self.assertEqual(common.get_project_dir(), tmp)

    def test_project_dir_space_form(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "pyproject.toml")
            with open(marker, "w", encoding="utf-8") as f:
                f.write("[project]\n")
            fake_argv = ["launcher.exe", "--project-dir", tmp]
            with patch.object(
                common,
                "sys",
                _patch_frozen_sys(fake_argv, tmp),
            ):
                self.assertEqual(common.get_project_dir(), tmp)


class TestEnsureVenv(unittest.TestCase):
    def test_creates_venv_in_project_dir(self) -> None:
        """venv must be created under project_dir, not CWD."""
        with tempfile.TemporaryDirectory() as proj:
            marker = os.path.join(proj, "pyproject.toml")
            with open(marker, "w", encoding="utf-8") as f:
                f.write("[project]\n")
            calls: list[tuple[list[str], str | None]] = []

            def fake_run_cmd(
                cmd: str | list[str],
                cwd: str | None = None,
                check: bool = True,
            ) -> int:
                cmd_list = cmd if isinstance(cmd, list) else cmd.split()
                calls.append((cmd_list, cwd))
                return 0

            with patch.object(common, "run_cmd", side_effect=fake_run_cmd):
                venv_dir, _pip, _py = common.ensure_venv(proj)

            self.assertTrue(venv_dir.endswith(os.path.join("venv")))
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1], proj)
            self.assertIn("-m", calls[0][0])
            self.assertIn("venv", calls[0][0])


if __name__ == "__main__":
    unittest.main()
