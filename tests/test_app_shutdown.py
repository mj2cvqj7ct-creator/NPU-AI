"""AudioEnhancerApp.shutdown resilience."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class TestAppShutdown(unittest.TestCase):
    def test_shutdown_suppresses_npu_engine_shutdown_errors(self) -> None:
        """Closing the app must not fail if ONNX unload raises."""
        mock_npu = MagicMock()
        mock_npu.load_default_models = MagicMock()
        mock_npu.shutdown.side_effect = RuntimeError("simulated ORT unload failure")

        with patch("src.app.NPUEngine", return_value=mock_npu):
            from src.app import AudioEnhancerApp

            app = AudioEnhancerApp()
            try:
                app.shutdown()
            except RuntimeError:
                self.fail("shutdown should swallow NPU engine shutdown errors")

        mock_npu.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()
