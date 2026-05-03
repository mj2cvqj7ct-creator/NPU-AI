"""
ONNX Model Definitions and Generators.

Creates lightweight ONNX models for audio processing tasks that can
run on the Snapdragon X NPU via DirectML.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TypedDict

import numpy as np

logger = logging.getLogger(__name__)


def default_model_dir() -> str:
    """Directory for ONNX weights: beside the frozen EXE, else repo ./models."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "models")
    return str(Path(__file__).resolve().parents[2] / "models")


class _ModelRegistryEntry(TypedDict):
    description: str
    input_shape: list[int]
    output_shape: list[int]


MODEL_REGISTRY: dict[str, _ModelRegistryEntry] = {
    "source_separation": {
        "description": "Vocal/instrument source separation",
        "input_shape": [1, 1, 2049],
        "output_shape": [1, 4, 2049],
    },
    "audio_enhance": {
        "description": "AI-based audio quality enhancement",
        "input_shape": [1, 1, 2049],
        "output_shape": [1, 1, 2049],
    },
    "noise_reduction": {
        "description": "Intelligent noise gate and reduction",
        "input_shape": [1, 1, 2049],
        "output_shape": [1, 1, 2049],
    },
    "recommender": {
        "description": "Music feature extraction for recommendations",
        "input_shape": [1, 128],
        "output_shape": [1, 64],
    },
}


def create_dummy_onnx_model(
    model_name: str,
    input_shape: list[int],
    output_shape: list[int],
    output_dir: str = "models",
) -> str | None:
    """Create a placeholder ONNX model for testing.

    In production, these would be replaced with trained models.
    """
    try:
        import onnx
        from onnx import TensorProto, helper

        os.makedirs(output_dir, exist_ok=True)

        input_tensor = helper.make_tensor_value_info("input", TensorProto.FLOAT, input_shape)
        output_tensor = helper.make_tensor_value_info("output", TensorProto.FLOAT, output_shape)

        input_size = 1
        for d in input_shape:
            input_size *= d

        output_size = 1
        for d in output_shape:
            output_size *= d

        # Zero weights → matmul is zero → sigmoid(0)=0.5: neutral spectral masks /
        # curves until replaced with trained checkpoints (avoids random junk when
        # exercising NPU/DirectML on placeholder graphs).
        weights = np.zeros((input_size, output_size), dtype=np.float32)
        weight_init = helper.make_tensor(
            "weights", TensorProto.FLOAT, [input_size, output_size], weights.flatten()
        )

        reshape_input_shape = np.array([input_shape[0], input_size], dtype=np.int64)
        reshape_input_init = helper.make_tensor(
            "reshape_input_shape", TensorProto.INT64, [2], reshape_input_shape
        )

        reshape_output_shape = np.array(output_shape, dtype=np.int64)
        reshape_output_init = helper.make_tensor(
            "reshape_output_shape", TensorProto.INT64, [len(output_shape)], reshape_output_shape
        )

        nodes = [
            helper.make_node("Reshape", ["input", "reshape_input_shape"], ["flat_input"]),
            helper.make_node("MatMul", ["flat_input", "weights"], ["matmul_out"]),
            helper.make_node("Sigmoid", ["matmul_out"], ["sigmoid_out"]),
            helper.make_node("Reshape", ["sigmoid_out", "reshape_output_shape"], ["output"]),
        ]

        graph = helper.make_graph(
            nodes,
            model_name,
            [input_tensor],
            [output_tensor],
            initializer=[weight_init, reshape_input_init, reshape_output_init],
        )

        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
        model.ir_version = 8

        model_path = os.path.join(output_dir, f"{model_name}.onnx")
        onnx.save(model, model_path)
        logger.info("Created ONNX model: %s", model_path)
        return model_path

    except ImportError:
        logger.info("ONNX not available; model creation skipped for '%s'", model_name)
        return None
    except Exception as e:
        logger.error("Failed to create model '%s': %s", model_name, e)
        return None


def create_all_models(model_dir: str = "models") -> dict[str, str]:
    """Create all ONNX models in the given directory."""
    os.makedirs(model_dir, exist_ok=True)
    created = {}
    for name, spec in MODEL_REGISTRY.items():
        path = create_dummy_onnx_model(
            name, spec["input_shape"], spec["output_shape"], model_dir
        )
        if path:
            created[name] = path
    return created


def ensure_models_exist(model_dir: str = "models") -> dict[str, str]:
    """Ensure all required ONNX models exist, creating placeholders if needed."""
    existing = {}
    for name, spec in MODEL_REGISTRY.items():
        model_path = os.path.join(model_dir, f"{name}.onnx")
        if os.path.exists(model_path):
            existing[name] = model_path
        else:
            path = create_dummy_onnx_model(
                name, spec["input_shape"], spec["output_shape"], model_dir
            )
            if path:
                existing[name] = path
    return existing
