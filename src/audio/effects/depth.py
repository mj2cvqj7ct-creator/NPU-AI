"""
Depth & Soundstage Processing Module.

Creates a convincing sense of front-to-back depth and three-dimensional
soundstage through frequency-dependent delay, reverb, and psychoacoustic cues.
"""

from __future__ import annotations

import numpy as np
from scipy import signal


class DepthProcessor:
    """Creates depth and 3D soundstage through psychoacoustic processing."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True

        self.depth_amount = 0.5
        self.room_size = 0.4
        self.damping = 0.5
        self.diffusion = 0.7
        self.pre_delay_ms = 15.0

        self._reverb = SchroederReverb(sample_rate)
        self._distance_filter = self._create_distance_filter()

    def _create_distance_filter(self) -> np.ndarray:
        """Create frequency-dependent distance simulation filter.

        Higher frequencies attenuate more with distance (air absorption).
        """
        nyq = self.sample_rate / 2.0
        cutoff = min(8000 + (1.0 - self.depth_amount) * 8000, nyq - 1)
        sos = signal.butter(2, cutoff / nyq, btype="low", output="sos")
        return sos

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply depth processing chain."""
        if not self.enabled or audio.shape[0] == 0:
            return audio

        dry = audio.copy()
        wet = self._apply_distance_filter(audio)

        pre_delay_samples = int(self.pre_delay_ms * self.sample_rate / 1000)
        if pre_delay_samples > 0 and pre_delay_samples < len(wet):
            delayed = np.zeros_like(wet)
            delayed[pre_delay_samples:] = wet[:-pre_delay_samples]
            wet = delayed

        reverb = self._reverb.process(wet, self.room_size, self.damping)

        mix = self.depth_amount * 0.4
        output = dry * (1.0 - mix) + reverb * mix

        return output.astype(np.float32)

    def _apply_distance_filter(self, audio: np.ndarray) -> np.ndarray:
        """Apply frequency-dependent distance attenuation."""
        output = np.zeros_like(audio)
        if audio.ndim == 2:
            for ch in range(audio.shape[1]):
                output[:, ch] = signal.sosfilt(self._distance_filter, audio[:, ch])
        else:
            output = signal.sosfilt(self._distance_filter, audio)
        return output


class SchroederReverb:
    """Schroeder reverberator with parallel comb filters and series allpass filters."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate

        self._comb_delays = [
            int(d * sample_rate / 1000)
            for d in [29.7, 37.1, 41.1, 43.7, 47.3, 53.1]
        ]
        self._allpass_delays = [
            int(d * sample_rate / 1000) for d in [5.0, 1.7, 3.3]
        ]

        max_delay = max(self._comb_delays + self._allpass_delays) + 1
        self._comb_buffers = [
            np.zeros(max_delay, dtype=np.float32) for _ in self._comb_delays
        ]
        self._allpass_buffers = [
            np.zeros(max_delay, dtype=np.float32) for _ in self._allpass_delays
        ]
        self._comb_indices = [0] * len(self._comb_delays)
        self._allpass_indices = [0] * len(self._allpass_delays)

    def process(
        self, audio: np.ndarray, room_size: float = 0.5, damping: float = 0.5
    ) -> np.ndarray:
        """Apply Schroeder reverb to audio."""
        if audio.ndim == 2:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio.copy()

        feedback = 0.7 + room_size * 0.28
        damp = damping * 0.4

        comb_sum = np.zeros_like(mono)
        for i, delay in enumerate(self._comb_delays):
            comb_out = self._process_comb(mono, i, delay, feedback, damp)
            comb_sum += comb_out

        comb_sum /= len(self._comb_delays)

        output = comb_sum
        for i, delay in enumerate(self._allpass_delays):
            output = self._process_allpass(output, i, delay, 0.5)

        if audio.ndim == 2:
            phase_offset = int(self.sample_rate * 0.001)
            right = np.roll(output, phase_offset)
            return np.column_stack([output, right]).astype(np.float32)

        return output.astype(np.float32)

    def _process_comb(
        self,
        audio: np.ndarray,
        index: int,
        delay: int,
        feedback: float,
        damp: float,
    ) -> np.ndarray:
        """Process through a single comb filter."""
        output = np.zeros_like(audio)
        buf = self._comb_buffers[index]
        idx = self._comb_indices[index]
        prev = 0.0

        for i in range(len(audio)):
            delayed = buf[idx % delay]
            filtered = delayed * (1.0 - damp) + prev * damp
            prev = filtered
            buf[idx % delay] = audio[i] + filtered * feedback
            output[i] = delayed
            idx += 1

        self._comb_indices[index] = idx
        return output

    def _process_allpass(
        self, audio: np.ndarray, index: int, delay: int, gain: float
    ) -> np.ndarray:
        """Process through a single allpass filter."""
        output = np.zeros_like(audio)
        buf = self._allpass_buffers[index]
        idx = self._allpass_indices[index]

        for i in range(len(audio)):
            delayed = buf[idx % delay]
            buf[idx % delay] = audio[i] + delayed * gain
            output[i] = delayed - audio[i] * gain
            idx += 1

        self._allpass_indices[index] = idx
        return output
