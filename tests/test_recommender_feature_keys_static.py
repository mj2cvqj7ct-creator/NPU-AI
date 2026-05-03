"""Ensure RecommenderPanel preference bar keys match engine FEATURE_NAMES (no Qt)."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


def _feature_rows_keys_from_source() -> set[str]:
    root = Path(__file__).resolve().parent.parent
    path = root / "src" / "ui" / "widgets" / "recommender_panel.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "feature_rows":
                    elts = node.value
                    if not isinstance(elts, ast.List):
                        continue
                    keys: set[str] = set()
                    for elt in elts.elts:
                        if isinstance(elt, ast.Tuple) and len(elt.elts) >= 1:
                            k = elt.elts[0]
                            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                keys.add(k.value)
                    if keys:
                        return keys
    raise AssertionError("feature_rows not found in recommender_panel.py")


class TestRecommenderFeatureKeysStatic(unittest.TestCase):
    def test_keys_subset_of_engine_features(self) -> None:
        from src.recommender.engine import FEATURE_NAMES

        keys = _feature_rows_keys_from_source()
        for k in keys:
            self.assertIn(k, FEATURE_NAMES, msg=f"unknown bar key: {k}")


if __name__ == "__main__":
    unittest.main()
