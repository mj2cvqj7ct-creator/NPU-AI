"""
NPU Inference Engine.

Manages ONNX Runtime sessions with DirectML execution provider
for Qualcomm Snapdragon X NPU acceleration. Supports automatic
fallback NPU -> GPU -> CPU, model lifecycle management, and
real-time performance monitoring.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class ExecutionProvider(Enum):
    NPU_DIRECTML = "DmlExecutionProvider"
    CPU = "CPUExecutionProvider"
    CUDA = "CUDAExecutionProvider"


@dataclass
class NPUConfig:
    preferred_provider: ExecutionProvider = ExecutionProvider.NPU_DIRECTML
    model_dir: str = "models"
    device_id: int = 0
    num_threads: int = 4
    enable_profiling: bool = False
    memory_limit_mb: int = 2048
    optimization_level: int = 99  # ORT_ENABLE_ALL


@dataclass
class ModelInfo:
    name: str
    path: str
    input_shapes: dict[str, list[int]] = field(default_factory=dict)
    output_names: list[str] = field(default_factory=list)
    loaded: bool = False
    infer_count: int = 0
    total_infer_ms: float = 0.0

    @property
    def avg_infer_ms(self) -> float:
        if self.infer_count == 0:
            return 0.0
        return self.total_infer_ms / self.infer_count


class NPUEngine:
    """ONNX Runtime-based NPU inference engine for Snapdragon X.

    Supports DirectML for NPU/GPU acceleration with automatic fallback to CPU.
    Manages multiple models for different audio processing tasks:
      - source_separation: Real-time stem separation masks
      - recommender: Audio feature embedding extraction
      - enhancement: Learned spectral enhancement curves
    """

    def __init__(self, config: NPUConfig | None = None):
        self.config = config or NPUConfig()
        self._sessions: dict[str, Any] = {}
        self._models: dict[str, ModelInfo] = {}
        self._active_provider: ExecutionProvider | None = None
        self._ort: Any = None
        self._init_time_ms = 0.0

        self._initialize_runtime()

    def _initialize_runtime(self) -> None:
        """Initialize ONNX Runtime with best available execution provider."""
        t0 = time.perf_counter()
        try:
            import onnxruntime as ort

            self._ort = ort

            available = ort.get_available_providers()
            logger.info("Available ONNX Runtime providers: %s", available)

            provider_priority = [
                ExecutionProvider.NPU_DIRECTML,
                ExecutionProvider.CUDA,
                ExecutionProvider.CPU,
            ]

            for provider in provider_priority:
                if provider.value in available:
                    self._active_provider = provider
                    logger.info("Selected execution provider: %s", provider.value)
                    break

            if self._active_provider is None:
                self._active_provider = ExecutionProvider.CPU
                logger.warning("No accelerated provider found, using CPU")

        except ImportError:
            logger.warning(
                "ONNX Runtime not available. NPU acceleration disabled. "
                "Install onnxruntime-directml for Snapdragon X NPU support.",
            )
            self._active_provider = None

        self._init_time_ms = (time.perf_counter() - t0) * 1000

    @property
    def is_available(self) -> bool:
        return self._ort is not None and self._active_provider is not None

    @property
    def provider_name(self) -> str:
        if self._active_provider:
            return self._active_provider.value
        return "None"

    @property
    def is_npu_active(self) -> bool:
        return self._active_provider == ExecutionProvider.NPU_DIRECTML

    def is_model_loaded(self, name: str) -> bool:
        return name in self._sessions

    def load_model(self, name: str, model_path: str) -> bool:
        """Load an ONNX model for inference."""
        if not self.is_available:
            logger.warning("Cannot load model '%s': runtime not available", name)
            return False

        try:
            full_path = model_path
            if not os.path.isabs(model_path):
                full_path = os.path.join(self.config.model_dir, model_path)

            if not os.path.exists(full_path):
                logger.info("Model file not found: %s (will use DSP fallback)", full_path)
                return False

            sess_options = self._ort.SessionOptions()
            sess_options.graph_optimization_level = (
                self._ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )
            sess_options.intra_op_num_threads = self.config.num_threads
            sess_options.execution_mode = self._ort.ExecutionMode.ORT_PARALLEL

            if self.config.enable_profiling:
                sess_options.enable_profiling = True

            providers = [self._active_provider.value]
            if self._active_provider != ExecutionProvider.CPU:
                providers.append(ExecutionProvider.CPU.value)

            provider_options: list[dict[str, Any]] = []
            if self._active_provider == ExecutionProvider.NPU_DIRECTML:
                provider_options.append({"device_id": self.config.device_id})
                if ExecutionProvider.CPU.value in providers:
                    provider_options.append({})

            session = self._ort.InferenceSession(
                full_path,
                sess_options=sess_options,
                providers=providers,
                provider_options=provider_options if provider_options else None,
            )

            input_shapes: dict[str, list[int]] = {}
            for inp in session.get_inputs():
                input_shapes[inp.name] = inp.shape

            output_names = [out.name for out in session.get_outputs()]

            self._sessions[name] = session
            self._models[name] = ModelInfo(
                name=name,
                path=full_path,
                input_shapes=input_shapes,
                output_names=output_names,
                loaded=True,
            )

            logger.info("Model '%s' loaded successfully via %s", name, self.provider_name)
            return True

        except Exception as e:
            logger.error("Failed to load model '%s': %s", name, e)
            return False

    def infer(self, model_name: str, input_data: np.ndarray) -> np.ndarray | None:
        """Run inference on a loaded model."""
        if model_name not in self._sessions:
            return None

        session = self._sessions[model_name]
        model_info = self._models[model_name]

        try:
            t0 = time.perf_counter()

            input_name = list(model_info.input_shapes.keys())[0]
            feed = {input_name: input_data.astype(np.float32)}

            results = session.run(model_info.output_names, feed)

            elapsed = (time.perf_counter() - t0) * 1000
            model_info.infer_count += 1
            model_info.total_infer_ms += elapsed

            return results[0] if len(results) == 1 else np.array(results)

        except Exception as e:
            logger.error("Inference error for model '%s': %s", model_name, e)
            return None

    def get_device_info(self) -> dict[str, Any]:
        """Get NPU/device information."""
        info: dict[str, Any] = {
            "runtime": "ONNX Runtime" if self._ort else "Not available",
            "provider": self.provider_name,
            "is_npu": self.is_npu_active,
            "models_loaded": len(self._sessions),
            "model_names": list(self._models.keys()),
            "init_time_ms": round(self._init_time_ms, 1),
        }

        if self._ort:
            info["ort_version"] = self._ort.__version__
            info["available_providers"] = self._ort.get_available_providers()

        model_stats = {}
        total_infer_ms = 0.0
        total_infer_count = 0
        for name, mi in self._models.items():
            model_stats[name] = {
                "infer_count": mi.infer_count,
                "avg_ms": round(mi.avg_infer_ms, 2),
            }
            total_infer_ms += mi.total_infer_ms
            total_infer_count += mi.infer_count
        info["model_stats"] = model_stats
        if total_infer_count > 0:
            info["avg_inference_ms"] = round(
                total_infer_ms / total_infer_count, 3,
            )
        else:
            info["avg_inference_ms"] = 0.0

        return info

    def unload_model(self, name: str) -> None:
        """Unload a model and free resources."""
        if name in self._sessions:
            del self._sessions[name]
        if name in self._models:
            self._models[name].loaded = False
            del self._models[name]
        logger.info("Model '%s' unloaded", name)

    def shutdown(self) -> None:
        """Shutdown the NPU engine and release all resources."""
        for name in list(self._sessions.keys()):
            self.unload_model(name)
        logger.info("NPU engine shut down")

    def load_default_models(self) -> None:
        """Ensure placeholder ONNX files exist and load all registry models."""
        from src.npu.models import MODEL_REGISTRY, ensure_models_exist

        ensure_models_exist(self.config.model_dir)
        for name in MODEL_REGISTRY:
            self.load_model(name, f"{name}.onnx")
