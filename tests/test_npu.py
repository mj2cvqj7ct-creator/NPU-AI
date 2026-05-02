"""Tests for the NPU inference engine."""

from __future__ import annotations

from src.npu.engine import ExecutionProvider, NPUConfig, NPUEngine


class TestNPUConfig:
    def test_defaults(self):
        cfg = NPUConfig()
        assert cfg.preferred_provider == ExecutionProvider.NPU_DIRECTML
        assert cfg.model_dir == "models"
        assert cfg.num_threads == 4
        assert cfg.optimization_level == 99

    def test_custom_config(self):
        cfg = NPUConfig(device_id=1, memory_limit_mb=4096)
        assert cfg.device_id == 1
        assert cfg.memory_limit_mb == 4096


class TestNPUEngine:
    def test_init_without_onnx(self):
        engine = NPUEngine()
        # On Linux without DirectML, should gracefully handle
        info = engine.get_device_info()
        assert "runtime" in info
        assert "provider" in info

    def test_provider_name(self):
        engine = NPUEngine()
        name = engine.provider_name
        assert isinstance(name, str)

    def test_load_nonexistent_model(self):
        engine = NPUEngine()
        result = engine.load_model("test", "nonexistent.onnx")
        assert result is False

    def test_infer_unloaded_model(self):
        engine = NPUEngine()
        result = engine.infer("unloaded", __import__("numpy").zeros((1, 10)))
        assert result is None

    def test_unload_model(self):
        engine = NPUEngine()
        engine.unload_model("nonexistent")  # Should not raise

    def test_shutdown(self):
        engine = NPUEngine()
        engine.shutdown()  # Should not raise

    def test_device_info_structure(self):
        engine = NPUEngine()
        info = engine.get_device_info()
        assert "runtime" in info
        assert "provider" in info
        assert "is_npu" in info
        assert "models_loaded" in info
        assert "model_names" in info
        assert "init_time_ms" in info
        assert "model_stats" in info
