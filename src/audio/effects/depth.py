"""
Depth & Soundstage Processing Module.

Creates convincing front-to-back depth and 3D soundstage through
frequency-dependent distance attenuation, early reflections,
Schroeder/FDN reverb, and psychoacoustic distance cues.
Optimized for real-time ARM64 NPU processing.
"""

from __future__ import annotations

import numpy as np
from scipy import signal


class DepthProcessor:
    """Creates depth and 3D soundstage through psychoacoustic processing."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True

        # Parameters
        self.depth_amount = 0.5
        self.room_size = 0.4
        self.damping = 0.5
        self.diffusion = 0.7
        self.pre_delay_ms = 15.0
        self.early_reflection_mix = 0.3
        self.late_reverb_mix = 0.2

        self._reverb = FDNReverb(sample_rate)
        self._early_reflections = EarlyReflections(sample_rate)
        self._distance_sos: np.ndarray | None = None
        self._zi_dist: list = []

        self._build_filters()

    def update_parameters(self, **kwargs: float) -> None:
        changed = False
        for key, value in kwargs.items():
            if hasattr(self, key) and getattr(self, key) != value:
                setattr(self, key, value)
                changed = True
        if changed:
            self._build_filters()

    def _build_filters(self) -> None:
        nyq = self.sample_rate / 2.0
        cutoff = min(6000.0 + (1.0 - self.depth_amount) * 10000.0, nyq - 1)
        self._distance_sos = signal.butter(
            3, cutoff / nyq, btype="low", output="sos",
        )
        self._zi_dist = [signal.sosfilt_zi(self._distance_sos) * 0 for _ in range(2)]

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or audio.shape[0] == 0:
            return audio

        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])

        dry = audio.copy()

        # 1. Distance filter (HF attenuation)
        wet = self._apply_distance(audio)

        # 2. Pre-delay
        pre_samples = int(self.pre_delay_ms * self.sample_rate / 1000)
        if 0 < pre_samples < len(wet):
            delayed = np.zeros_like(wet)
            delayed[pre_samples:] = wet[:-pre_samples]
            wet = delayed

        # 3. Early reflections
        er = self._early_reflections.process(wet, self.room_size)

        # 4. Late reverb (FDN)
        reverb = self._reverb.process(wet, self.room_size, self.damping)

        # 5. Mix
        mix_er = self.early_reflection_mix * self.depth_amount
        mix_rev = self.late_reverb_mix * self.depth_amount
        dry_gain = 1.0 - (mix_er + mix_rev) * 0.5

        output = dry * dry_gain + er * mix_er + reverb * mix_rev
        return output.astype(np.float32)

    def _apply_distance(self, audio: np.ndarray) -> np.ndarray:
        out = np.zeros_like(audio, dtype=np.float64)
        for ch in range(audio.shape[1]):
            filtered, zi = signal.sosfilt(
                self._distance_sos, audio[:, ch], zi=self._zi_dist[ch],
            )
            self._zi_dist[ch] = zi
            out[:, ch] = filtered
        return out


class EarlyReflections:
    """Generates early reflection pattern for realistic room simulation."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate

        # Reflection delay/gain pairs (ms, gain, pan L/R)
        self._reflections = [
            (4.8, 0.70, 0.3),
            (7.2, 0.58, -0.4),
            (11.5, 0.48, 0.6),
            (16.3, 0.38, -0.2),
            (22.1, 0.30, 0.5),
            (29.7, 0.24, -0.6),
            (38.4, 0.18, 0.1),
            (47.2, 0.14, -0.3),
        ]

    def process(self, audio: np.ndarray, room_size: float = 0.5) -> np.ndarray:
        n = audio.shape[0]
        output = np.zeros_like(audio, dtype=np.float64)

        for delay_ms, gain, pan in self._reflections:
            delay = int(delay_ms * (0.5 + room_size) * self.sample_rate / 1000)
            if delay >= n:
                continue
            g = gain * (0.3 + room_size * 0.7)
            l_gain = g * (0.5 + pan * 0.5)
            r_gain = g * (0.5 - pan * 0.5)
            output[delay:, 0] += audio[:-delay or n, 0] * l_gain
            output[delay:, 1] += audio[:-delay or n, 1] * r_gain

        return output


class FDNReverb:
    """Feedback Delay Network reverberator with Hadamard mixing matrix.

    More diffuse and natural than Schroeder parallel-comb architecture.
    """

    _DELAY_TIMES_MS = [29.7, 37.1, 41.1, 43.7, 47.3, 53.1, 59.3, 67.9]

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        n_lines = len(self._DELAY_TIMES_MS)

        self._delays = [
            int(d * sample_rate / 1000) for d in self._DELAY_TIMES_MS
        ]
        max_d = max(self._delays) + 1
        self._buffers = [np.zeros(max_d, dtype=np.float64) for _ in range(n_lines)]
        self._indices = [0] * n_lines
        self._lp_state = [0.0] * n_lines

        # Hadamard-like mixing matrix (orthogonal, N=8)
        self._mix = self._hadamard(n_lines) / np.sqrt(n_lines)

    @staticmethod
    def _hadamard(n: int) -> np.ndarray:
        """Generate a Hadamard matrix of size n (must be power of 2)."""
        h = np.array([[1.0]])
        while h.shape[0] < n:
            h = np.block([[h, h], [h, -h]])
        return h[:n, :n]

    def process(
        self,
        audio: np.ndarray,
        room_size: float = 0.5,
        damping: float = 0.5,
    ) -> np.ndarray:
        if audio.ndim == 2:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio.copy()

        n = len(mono)
        n_lines = len(self._delays)
        feedback = 0.65 + room_size * 0.30
        damp = damping * 0.5

        out = np.zeros(n, dtype=np.float64)

        for s in range(n):
            # Read delay lines
            taps = np.zeros(n_lines, dtype=np.float64)
            for i, delay in enumerate(self._delays):
                taps[i] = self._buffers[i][self._indices[i] % delay]

            out[s] = np.mean(taps)

            # Mix through Hadamard matrix
            mixed = self._mix @ taps

            # Write back with input, feedback, and damping
            for i, delay in enumerate(self._delays):
                lp = mixed[i] * (1.0 - damp) + self._lp_state[i] * damp
                self._lp_state[i] = lp
                self._buffers[i][self._indices[i] % delay] = mono[s] + lp * feedback
                self._indices[i] += 1

        if audio.ndim == 2:
            # Stereo decorrelation via slight phase offset
            offset = int(0.0012 * self.sample_rate)
            right = np.roll(out, offset)
            right[:offset] = 0
            return np.column_stack([out, right]).astype(np.float32)

        return out.astype(np.float32)
