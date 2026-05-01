"""
Spatial Audio & Holographic Sound Processing.

Advanced HRTF-based 3D positioning, cross-feed, stereo width expansion,
and holographic ambience for immersive soundstage reproduction.
Optimized for real-time processing on ARM64 NPU.
"""

from __future__ import annotations

import numpy as np
from scipy import signal


class SpatialProcessor:
    """HRTF-based spatial audio with holographic soundstage expansion."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.enabled = True

        # Spatial parameters
        self.soundstage_width = 0.7
        self.depth = 0.5
        self.height = 0.3
        self.holographic_intensity = 0.6
        self.crossfeed_level = 0.3
        self.center_focus = 0.5
        self.stereo_enhance = 0.4
        self.immersion = 0.5

        # Internal state
        self._hrtf_l: np.ndarray = np.zeros(0, dtype=np.float32)
        self._hrtf_r: np.ndarray = np.zeros(0, dtype=np.float32)
        self._crossfeed_sos: np.ndarray | None = None
        self._holographic_bands: list[tuple[np.ndarray, float]] = []
        self._height_sos: np.ndarray | None = None
        self._zi_crossfeed_l = None
        self._zi_crossfeed_r = None
        self._zi_height: list | None = None
        self._zi_holo: list[list | None] = []
        self._overlap_l = np.zeros(0, dtype=np.float32)
        self._overlap_r = np.zeros(0, dtype=np.float32)

        self._build_filters()

    def update_parameters(self, **kwargs: float) -> None:
        """Update spatial parameters and rebuild filters."""
        changed = False
        for key, value in kwargs.items():
            if hasattr(self, key) and getattr(self, key) != value:
                setattr(self, key, value)
                changed = True
        if changed:
            self._build_filters()

    # ------------------------------------------------------------------
    # Filter generation
    # ------------------------------------------------------------------

    def _build_filters(self) -> None:
        self._build_hrtf()
        self._build_crossfeed()
        self._build_holographic()
        self._build_height_filter()

    def _build_hrtf(self) -> None:
        """Approximate HRTF for left/right ear with ITD + ILD + pinna cues."""
        fir_len = 256
        t = np.arange(fir_len, dtype=np.float64) / self.sample_rate

        # Inter-aural time difference scaled by soundstage width
        itd_s = 0.00065 * self.soundstage_width
        itd_samples = int(itd_s * self.sample_rate)

        # Build ipsilateral (near-ear) impulse
        ipsi = np.zeros(fir_len, dtype=np.float64)
        ipsi[0] = 1.0
        # Pinna notch around 8-10 kHz
        pinna_f = 9000.0
        pinna_decay = np.exp(-np.arange(fir_len, dtype=np.float64) * pinna_f / self.sample_rate)
        ipsi += pinna_decay * np.sin(2 * np.pi * pinna_f * t) * -0.08

        # Contralateral (far-ear) with head shadow
        contra = np.zeros(fir_len, dtype=np.float64)
        delay_idx = min(itd_samples, fir_len - 1)
        contra[delay_idx] = 0.75 * (1.0 - 0.2 * self.soundstage_width)
        # Low-pass for head shadow
        shadow_fc = max(1200.0, 2500.0 - 1000.0 * self.soundstage_width)
        nyq = self.sample_rate / 2.0
        if shadow_fc < nyq:
            sos = signal.butter(2, shadow_fc / nyq, btype="low", output="sos")
            contra = signal.sosfilt(sos, contra)

        # Normalize
        ipsi_peak = np.max(np.abs(ipsi))
        if ipsi_peak > 0:
            ipsi /= ipsi_peak
        contra_peak = np.max(np.abs(contra))
        if contra_peak > 0:
            contra /= contra_peak
            contra *= 0.6

        self._hrtf_l = ipsi.astype(np.float32)
        self._hrtf_r = contra.astype(np.float32)
        self._overlap_l = np.zeros(fir_len - 1, dtype=np.float32)
        self._overlap_r = np.zeros(fir_len - 1, dtype=np.float32)

    def _build_crossfeed(self) -> None:
        """Natural speaker-like crossfeed (Bauer-inspired)."""
        fc = 650.0 + 100.0 * self.crossfeed_level
        nyq = self.sample_rate / 2.0
        if fc >= nyq:
            fc = nyq * 0.9
        self._crossfeed_sos = signal.butter(1, fc / nyq, btype="low", output="sos")
        self._zi_crossfeed_l = signal.sosfilt_zi(self._crossfeed_sos) * 0
        self._zi_crossfeed_r = signal.sosfilt_zi(self._crossfeed_sos) * 0

    def _build_holographic(self) -> None:
        """Multi-band holographic ambience extraction filters."""
        nyq = self.sample_rate / 2.0
        band_defs = [
            (150, 600, 0.35),
            (600, 2500, 0.55),
            (2500, 7000, 0.75),
            (7000, min(14000, nyq - 1), 0.45),
        ]
        self._holographic_bands = []
        self._zi_holo = []
        for lo, hi, gain in band_defs:
            if lo >= nyq or hi >= nyq:
                continue
            sos = signal.butter(3, [lo / nyq, hi / nyq], btype="band", output="sos")
            self._holographic_bands.append((sos, gain * self.holographic_intensity))
            self._zi_holo.append(None)

    def _build_height_filter(self) -> None:
        """Subtle high-shelf boost to simulate elevated source (height cue)."""
        nyq = self.sample_rate / 2.0
        fc = min(6000.0, nyq - 1)
        if fc <= 0:
            self._height_sos = None
            return
        self._height_sos = signal.butter(1, fc / nyq, btype="high", output="sos")
        self._zi_height = [signal.sosfilt_zi(self._height_sos) * 0 for _ in range(2)]

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Apply full spatial processing chain."""
        if not self.enabled or audio.shape[0] == 0:
            return audio

        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])

        left = audio[:, 0].astype(np.float64)
        right = audio[:, 1].astype(np.float64)

        # 1. Mid-side decomposition
        mid = (left + right) * 0.5
        side = (left - right) * 0.5

        # 2. Center focus - keep vocals/center content tight
        focus = 0.5 + self.center_focus * 0.5
        mid_out = mid * focus
        side_out = side * (1.0 + self.stereo_enhance * 0.8)

        # 3. HRTF convolution (overlap-add)
        mid_out, side_out = self._apply_hrtf(mid_out, side_out)

        # 4. Holographic ambience from side channel
        if self.holographic_intensity > 0:
            holo_l, holo_r = self._apply_holographic(side)
            mid_out = mid_out + holo_l
            side_out = side_out + holo_r

        # 5. Height cue
        if self.height > 0 and self._height_sos is not None:
            mid_out = self._apply_height(mid_out, 0)
            side_out = self._apply_height(side_out, 1)

        # 6. Reconstruct L/R
        out_l = mid_out + side_out
        out_r = mid_out - side_out

        # 7. Crossfeed
        if self.crossfeed_level > 0:
            out_l, out_r = self._apply_crossfeed(out_l, out_r)

        # 8. Immersion blend with original
        blend = self.immersion
        out_l = left * (1.0 - blend) + out_l * blend
        out_r = right * (1.0 - blend) + out_r * blend

        output = np.column_stack([out_l, out_r]).astype(np.float32)
        return output

    def _apply_hrtf(
        self, mid: np.ndarray, side: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Overlap-add HRTF convolution."""
        n = len(mid)
        fir_len = len(self._hrtf_l)

        conv_l = np.convolve(mid, self._hrtf_l)[:n + fir_len - 1]
        conv_r = np.convolve(side, self._hrtf_r)[:n + fir_len - 1]

        # Add previous overlap
        overlap_n = len(self._overlap_l)
        add_n = min(overlap_n, n)
        conv_l[:add_n] += self._overlap_l[:add_n]
        conv_r[:add_n] += self._overlap_r[:add_n]

        # Save new overlap
        self._overlap_l = conv_l[n:].astype(np.float32)
        self._overlap_r = conv_r[n:].astype(np.float32)

        return conv_l[:n], conv_r[:n]

    def _apply_holographic(
        self, side: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Extract ambience and create decorrelated holographic field."""
        holo_l = np.zeros(len(side), dtype=np.float64)
        holo_r = np.zeros(len(side), dtype=np.float64)

        for i, (sos, gain) in enumerate(self._holographic_bands):
            zi = self._zi_holo[i]
            if zi is None:
                zi = signal.sosfilt_zi(sos) * 0
            band, zi_out = signal.sosfilt(sos, side, zi=zi)
            self._zi_holo[i] = zi_out

            # Decorrelate left/right with phase offset
            shift = int((i + 1) * 0.003 * self.sample_rate)
            holo_l += band * gain
            shifted = np.roll(band, shift)
            shifted[:shift] = 0
            holo_r += shifted * gain * 0.9

        return holo_l, holo_r

    def _apply_crossfeed(
        self, left: np.ndarray, right: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Apply crossfeed for natural speaker-like presentation."""
        level = self.crossfeed_level * 0.35

        r_to_l, self._zi_crossfeed_l = signal.sosfilt(
            self._crossfeed_sos, right, zi=self._zi_crossfeed_l,
        )
        l_to_r, self._zi_crossfeed_r = signal.sosfilt(
            self._crossfeed_sos, left, zi=self._zi_crossfeed_r,
        )

        out_l = left * (1.0 - level * 0.5) + r_to_l * level
        out_r = right * (1.0 - level * 0.5) + l_to_r * level
        return out_l, out_r

    def _apply_height(self, data: np.ndarray, ch_idx: int) -> np.ndarray:
        """Apply height cue via high-shelf boost."""
        filtered, zi = signal.sosfilt(
            self._height_sos, data, zi=self._zi_height[ch_idx],
        )
        self._zi_height[ch_idx] = zi
        return data + filtered * self.height * 0.15
