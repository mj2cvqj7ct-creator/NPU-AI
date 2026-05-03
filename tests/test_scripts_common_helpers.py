"""Tests for scripts/common helpers: is_project_root, get_venv_executables, run_cmd."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import scripts.common as common


class TestIsProjectRoot(unittest.TestCase):
    def test_false_for_non_directory(self) -> None:
        self.assertFalse(common.is_project_root("/nonexistent/path/xyz"))

    def test_false_when_no_sentinels(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(common.is_project_root(d))

    def test_true_when_pyproject_present(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "pyproject.toml")
            with open(marker, "w", encoding="utf-8") as f:
                f.write("")
            self.assertTrue(common.is_project_root(d))


class TestGetVenvExecutables(unittest.TestCase):
    def test_paths_use_platform_layout(self) -> None:
        vdir, pip_e, py_e = common.get_venv_executables("/proj")
        self.assertTrue(vdir.endswith(os.path.join("proj", "venv")))
        if common.sys.platform == "win32":
            self.assertIn("Scripts", pip_e)
            self.assertTrue(pip_e.endswith("pip.exe"))
            self.assertTrue(py_e.endswith("python.exe"))
        else:
            self.assertIn("bin", pip_e)
            self.assertTrue(pip_e.endswith("pip"))
            self.assertTrue(py_e.endswith("python"))


class TestRunCmd(unittest.TestCase):
    def test_invokes_subprocess_with_cwd(self) -> None:
        proc = MagicMock()
        proc.returncode = 0

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(common.subprocess, "run", return_value=proc) as run_mock,
        ):
            rc = common.run_cmd(
                [sys.executable, "-c", "raise SystemExit(0)"],
                cwd=tmp,
                check=True,
            )

        self.assertEqual(rc, 0)
        run_mock.assert_called_once()
        args, kwargs = run_mock.call_args
        self.assertEqual(list(args[0])[:2], [sys.executable, "-c"])
        self.assertEqual(kwargs.get("cwd"), tmp)
        self.assertFalse(kwargs.get("check", True))

    def test_file_not_found_returns_one(self) -> None:
        with (
            patch.object(
                common.subprocess,
                "run",
                side_effect=FileNotFoundError(),
            ),
            patch("builtins.print"),
        ):
            rc = common.run_cmd(["/nonexistent/binary_xyz"], check=True)
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
