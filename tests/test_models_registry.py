"""ONNX placeholder model helpers (runs when onnx is installed in CI/dev)."""

from __future__ import annotations

import os
import tempfile
import unittest

import numpy as np


class TestModelRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from src.npu import models as npu_models
        except ImportError as e:
            raise unittest.SkipTest(str(e)) from e
        cls.npu_models = npu_models

    def test_registry_covers_requirements(self) -> None:
        names = set(self.npu_models.MODEL_REGISTRY.keys())
        self.assertEqual(
            names,
            {"source_separation", "audio_enhance", "noise_reduction", "recommender"},
        )

    def test_ensure_models_exist_writes_files(self) -> None:
        try:
            import onnx  # noqa: F401
        except ImportError:
            self.skipTest("onnx not installed")
        with tempfile.TemporaryDirectory() as tmp:
            existing = self.npu_models.ensure_models_exist(tmp)
            self.assertEqual(set(existing.keys()), set(self.npu_models.MODEL_REGISTRY.keys()))
            for name, path in existing.items():
                self.assertTrue(os.path.isfile(path), msg=f"missing {name}")
                size = os.path.getsize(path)
                self.assertGreater(size, 0, msg=f"empty {name}")

    def test_placeholder_graph_is_neutral(self) -> None:
        """Zero MatMul weights → sigmoid(0)=0.5 for typical placeholder runtimes."""
        try:
            import onnx
            from onnx import TensorProto, helper
        except ImportError:
            self.skipTest("onnx not installed")
        try:
            import onnxruntime as ort
        except ImportError:
            self.skipTest("onnxruntime not installed")

        spec = self.npu_models.MODEL_REGISTRY["audio_enhance"]
        in_shape = list(spec["input_shape"])
        out_shape = list(spec["output_shape"])
        input_size = int(np.prod(in_shape))
        output_size = int(np.prod(out_shape))

        in_info = helper.make_tensor_value_info("input", TensorProto.FLOAT, in_shape)
        out_info = helper.make_tensor_value_info("output", TensorProto.FLOAT, out_shape)
        w = np.zeros((input_size, output_size), dtype=np.float32)
        w_init = helper.make_tensor(
            "weights", TensorProto.FLOAT, [input_size, output_size], w.flatten(),
        )
        ri = np.array([in_shape[0], input_size], dtype=np.int64)
        ri_init = helper.make_tensor("reshape_input_shape", TensorProto.INT64, [2], ri)
        ro = np.array(out_shape, dtype=np.int64)
        ro_init = helper.make_tensor(
            "reshape_output_shape", TensorProto.INT64, [len(out_shape)], ro,
        )
        nodes = [
            helper.make_node("Reshape", ["input", "reshape_input_shape"], ["flat_input"]),
            helper.make_node("MatMul", ["flat_input", "weights"], ["matmul_out"]),
            helper.make_node("Sigmoid", ["matmul_out"], ["sigmoid_out"]),
            helper.make_node("Reshape", ["sigmoid_out", "reshape_output_shape"], ["output"]),
        ]
        graph = helper.make_graph(
            nodes,
            "test_neutral",
            [in_info],
            [out_info],
            initializer=[w_init, ri_init, ro_init],
        )
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])

        with tempfile.NamedTemporaryFile(suffix=".onnx", delete=False) as f:
            path = f.name
        try:
            onnx.save(model, path)
            sess = ort.InferenceSession(
                path, providers=["CPUExecutionProvider"],
            )
            x = np.random.randn(*in_shape).astype(np.float32)
            y = sess.run(None, {"input": x})[0]
            np.testing.assert_allclose(y, 0.5, rtol=0, atol=1e-5)
        finally:
            if os.path.isfile(path):
                os.unlink(path)


if __name__ == "__main__":
    unittest.main()
