"""
NPU-accelerated spectral noise attenuation (noise_reduction ONNX).

Uses the same STFT layout as MODEL_REGISTRY["noise_reduction"] (2049 bins):
mono magnitude in, estimated noise/speech mask from ONNX, overlap-add
with per-bin attenuation and light temporal smoothing.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)

_NR_FFT = 4096
_NR_HOP = 1024


class NPUNoiseReducer:
    """Spectral denoise gate driven by `noise_reduction` ONNX model."""

    def __init__(self, sample_rate: int = 48000) -> None:
        self.sample_rate = sample_rate
        self.enabled = False
        self.npu_blend = 0.25
        self._mask_smooth = 0.35  # EMA alpha for inter-frame mask smoothing
        self._npu_engine: Any | None = None

        self._nr_fft = _NR_FFT
        self._nr_hop = _NR_HOP
        self._nr_window = signal.windows.hann(self._nr_fft, sym=False).astype(
            np.float32,
        )
        self._nr_syn = self._create_synthesis_window()
        self._ola_buf: np.ndarray | None = None
        self._in_carry: np.ndarray | None = None
        self._out_fifo: list[np.ndarray] = []
        self._mask_ema: np.ndarray | None = None

    def set_npu_engine(self, engine: object | None) -> None:
        self._npu_engine = engine
        self._reset_state()
        if engine is not None:
            logger.info("NPU engine connected to noise reducer")

    def _create_synthesis_window(self) -> np.ndarray:
        w = self._nr_window.copy()
        hop = self._nr_hop
        fft_size = self._nr_fft
        denom = np.zeros(fft_size, dtype=np.float32)
        for i in range(0, fft_size, hop):
            end = min(i + fft_size, fft_size)
            denom[i:end] += w[: end - i] ** 2
        denom = np.maximum(denom, 1e-8)
        return (w / denom[:fft_size]).astype(np.float32)

    def _reset_state(self) -> None:
        self._ola_buf = None
        self._in_carry = None
        self._out_fifo = []
        self._mask_ema = None

    def reset_streaming_state(self) -> None:
        """Clear OLA state when the stage is bypassed at the pipeline level."""
        self._reset_state()

    def update_parameters(self, **kwargs: float) -> None:
        prev = self.npu_blend
        skip = frozenset({"enabled"})
        for key, value in kwargs.items():
            if key in skip or key.startswith("_"):
                continue
            if hasattr(self, key):
                setattr(self, key, value)
        if self.npu_blend <= 1e-5 and prev > 1e-5:
            self._reset_state()

    def _ensure_ola(self, n_ch: int) -> None:
        if (
            self._ola_buf is None
            or self._in_carry is None
            or self._ola_buf.shape[1] != n_ch
        ):
            self._ola_buf = np.zeros((self._nr_fft, n_ch), dtype=np.float64)
            self._in_carry = np.zeros((0, n_ch), dtype=np.float32)
            self._out_fifo = []
            self._mask_ema = None

    def _take_fifo(
        self,
        n_rows: int,
        n_ch: int,
        passthrough: np.ndarray,
    ) -> np.ndarray:
        out = np.zeros((n_rows, n_ch), dtype=np.float32)
        filled = 0
        while filled < n_rows and self._out_fifo:
            block = self._out_fifo[0]
            take = min(n_rows - filled, block.shape[0])
            out[filled : filled + take] = block[:take].astype(np.float32, copy=False)
            if take >= block.shape[0]:
                self._out_fifo.pop(0)
            else:
                self._out_fifo[0] = block[take:]
            filled += take
        if filled < n_rows:
            out[filled:] = passthrough[filled:].astype(np.float32, copy=False)
        return out

    def _spectral_ola(self, audio: np.ndarray) -> np.ndarray:
        n_ch = audio.shape[1]
        self._ensure_ola(n_ch)
        assert self._ola_buf is not None and self._in_carry is not None

        buf = np.vstack([self._in_carry, audio.astype(np.float32)])
        w = self._nr_window
        ws = self._nr_syn
        n_bins = self._nr_fft // 2 + 1
        blend = float(np.clip(self.npu_blend, 0.0, 1.0))
        alpha = float(np.clip(self._mask_smooth, 0.05, 0.95))

        while buf.shape[0] >= self._nr_fft:
            frame = buf[: self._nr_fft].copy()
            buf = buf[self._nr_hop :]
            mono = np.mean(frame, axis=1)
            spec0 = np.fft.rfft(mono * w)
            mag0 = np.abs(spec0).astype(np.float32)
            if mag0.shape[0] != n_bins:
                logger.debug("Noise reducer STFT bin mismatch: %s", mag0.shape)
                mag0 = np.resize(mag0, n_bins).astype(np.float32)

            inp = mag0.reshape(1, 1, -1)
            curve = None
            if self._npu_engine is not None:
                curve = self._npu_engine.infer("noise_reduction", inp)

            if curve is not None:
                c = np.asarray(curve, dtype=np.float32).reshape(-1)
                if c.size >= n_bins:
                    noise_mask = np.clip(c[:n_bins], 0.0, 1.0)
                else:
                    noise_mask = None
            else:
                noise_mask = None

            if noise_mask is None:
                atten = np.ones(n_bins, dtype=np.float32)
            else:
                if self._mask_ema is None or self._mask_ema.shape != noise_mask.shape:
                    self._mask_ema = noise_mask.copy()
                else:
                    self._mask_ema = (1.0 - alpha) * self._mask_ema + alpha * noise_mask

                m = self._mask_ema
                # High mask = attenuate (treat model output as noise confidence).
                atten = 1.0 - blend * (0.08 + 0.92 * m)
                np.clip(atten, 0.04, 1.0, out=atten)

            timed = np.zeros((self._nr_fft, n_ch), dtype=np.float64)
            for ch in range(n_ch):
                X = np.fft.rfft(frame[:, ch] * w)
                mag_c = np.abs(X)
                ang = np.angle(X)
                nb = min(mag_c.shape[0], atten.shape[0])
                new_mag = mag_c[:nb] * atten[:nb]
                if mag_c.shape[0] > nb:
                    new_mag = np.concatenate([new_mag, mag_c[nb:]])
                Y = new_mag * np.exp(1j * ang)
                t = np.fft.irfft(Y, n=self._nr_fft).real.astype(np.float64) * ws
                timed[:, ch] = t

            self._ola_buf += timed
            hop_block = self._ola_buf[: self._nr_hop].astype(np.float32, copy=True)
            self._out_fifo.append(hop_block)
            self._ola_buf = np.roll(self._ola_buf, -self._nr_hop, axis=0)
            self._ola_buf[-self._nr_hop :, :] = 0.0

        self._in_carry = buf
        return self._take_fifo(audio.shape[0], n_ch, audio)

    def process(self, audio: np.ndarray) -> np.ndarray:
        if (
            not self.enabled
            or audio.shape[0] == 0
            or self.npu_blend <= 1e-6
            or self._npu_engine is None
        ):
            return audio

        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])

        x = audio.astype(np.float32, copy=False)
        return self._spectral_ola(x)
