"""Unit tests for NPU engine data structures (no ORT session required)."""

from __future__ import annotations

import unittest


class TestModelInfo(unittest.TestCase):
    def test_avg_infer_ms_zero_until_calls(self) -> None:
        from src.npu.engine import ModelInfo

        m = ModelInfo(name="x", path="/tmp/x.onnx")
        self.assertEqual(m.avg_infer_ms, 0.0)

    def test_avg_infer_ms_tracks_totals(self) -> None:
        from src.npu.engine import ModelInfo

        m = ModelInfo(name="x", path="/tmp/x.onnx")
        m.infer_count = 4
        m.total_infer_ms = 10.0
        self.assertAlmostEqual(m.avg_infer_ms, 2.5)


if __name__ == "__main__":
    unittest.main()
