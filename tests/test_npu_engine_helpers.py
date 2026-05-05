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


class TestExecutionProviderClassification(unittest.TestCase):
    """Both QNN (Snapdragon NPU) and DirectML must count as `is_npu_active`.

    These tests don't load real ORT sessions; they construct an NPUEngine
    and override `_active_provider` to simulate the runtime selection.
    """

    def _new_engine(self) -> object:
        from src.npu.engine import NPUEngine

        # NPUEngine.__init__ tolerates onnxruntime being unavailable.
        return NPUEngine()

    def test_qnn_provider_reports_npu_active(self) -> None:
        from src.npu.engine import ExecutionProvider

        engine = self._new_engine()
        engine._active_provider = ExecutionProvider.NPU_QNN  # type: ignore[attr-defined]
        self.assertTrue(engine.is_npu_active)  # type: ignore[attr-defined]

    def test_directml_provider_reports_npu_active(self) -> None:
        from src.npu.engine import ExecutionProvider

        engine = self._new_engine()
        engine._active_provider = ExecutionProvider.NPU_DIRECTML  # type: ignore[attr-defined]
        self.assertTrue(engine.is_npu_active)  # type: ignore[attr-defined]

    def test_cpu_provider_reports_npu_inactive(self) -> None:
        from src.npu.engine import ExecutionProvider

        engine = self._new_engine()
        engine._active_provider = ExecutionProvider.CPU  # type: ignore[attr-defined]
        self.assertFalse(engine.is_npu_active)  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
