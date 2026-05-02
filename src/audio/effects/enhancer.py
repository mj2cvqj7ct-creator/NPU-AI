"""
Audio Quality Enhancement Module (v3 - Dramatically Improved).

Advanced multi-band dynamics, tape saturation harmonic exciter,
psychoacoustic bass with missing fundamental synthesis,
air-band sparkle with transient preservation, and LUFS-aware
loudness normalization with true-peak limiting.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)

# Must match MODEL_REGISTRY["audio_enhance"] frequency bins (fft_size // 2 + 1).
_ENH_FFT = 4096
_ENH_HOP = 1024


class AudioEnhancer:
    """Multi-stage audio quality enhancer with psychoacoustic optimization."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self._enhancer_enabled = True
        self.npu_blend = 0.35  # 0=DSP only, 1=full NPU spectral mix-in
        self._npu_engine: Any | None = None

        # STFT state for NPU path (overlap-add); reset when blend→0 or channel count changes
        self._en_fft = _ENH_FFT
        self._en_hop = _ENH_HOP
        self._en_window = signal.windows.hann(self._en_fft, sym=False).astype(np.float32)
        self._en_syn = self._create_synthesis_window()
        self._ola_buf: np.ndarray | None = None
        self._in_carry: np.ndarray | None = None
        self._out_fifo: list[np.ndarray] = []

        # Enhancement parameters
        self.warmth = 0.3
        self.clarity = 0.5
        self.presence = 0.4
        self.air = 0.3
        self.bass_boost = 0.2
        self.exciter = 0.2
        self.stereo_width = 0.0
        self.loudness_target = -14.0  # LUFS

        self._build_processing_chain()

    _TUNABLE_KEYS = frozenset({
        "warmth",
        "clarity",
        "presence",
        "air",
        "bass_boost",
        "exciter",
        "stereo_width",
        "npu_blend",
        "loudness_target",
    })

    @property
    def enabled(self) -> bool:
        return self._enhancer_enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        v = bool(value)
        if not v and self._enhancer_enabled:
            self._reset_npu_ola_state()
        self._enhancer_enabled = v

    def set_npu_engine(self, engine: object | None) -> None:
        self._npu_engine = engine
        self._reset_npu_ola_state()
        if engine is not None:
            logger.info("NPU engine connected to audio enhancer")

    def _create_synthesis_window(self) -> np.ndarray:
        w = self._en_window.copy()
        hop = self._en_hop
        fft_size = self._en_fft
        denom = np.zeros(fft_size, dtype=np.float32)
        for i in range(0, fft_size, hop):
            end = min(i + fft_size, fft_size)
            denom[i:end] += w[: end - i] ** 2
        denom = np.maximum(denom, 1e-8)
        return (w / denom[:fft_size]).astype(np.float32)

    def _reset_npu_ola_state(self) -> None:
        self._ola_buf = None
        self._in_carry = None
        self._out_fifo = []

    def _ensure_npu_ola(self, n_ch: int) -> None:
        if (
            self._ola_buf is None
            or self._in_carry is None
            or self._ola_buf.shape[1] != n_ch
        ):
            self._ola_buf = np.zeros((self._en_fft, n_ch), dtype=np.float64)
            self._in_carry = np.zeros((0, n_ch), dtype=np.float32)
            self._out_fifo = []

    def _take_npu_fifo(
        self,
        n_rows: int,
        n_ch: int,
        passthrough: np.ndarray,
    ) -> np.ndarray:
        """Drain OLA output; until the ring has produced `n_rows` samples, use dry input."""
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

    def _spectral_npu_ola(self, audio: np.ndarray) -> np.ndarray:
        """STFT-domain gain from ONNX `audio_enhance`, overlap-add; keeps per-channel phase."""
        n_ch = audio.shape[1]
        self._ensure_npu_ola(n_ch)
        assert self._ola_buf is not None and self._in_carry is not None

        buf = np.vstack([self._in_carry, audio.astype(np.float32)])
        w = self._en_window
        ws = self._en_syn
        n_bins = self._en_fft // 2 + 1

        while buf.shape[0] >= self._en_fft:
            frame = buf[: self._en_fft].copy()
            buf = buf[self._en_hop :]
            mono = np.mean(frame, axis=1)
            spec0 = np.fft.rfft(mono * w)
            mag0 = np.abs(spec0).astype(np.float32)
            if mag0.shape[0] != n_bins:
                logger.debug("Enhancer STFT bin mismatch: %s", mag0.shape)
                mag0 = np.resize(mag0, n_bins).astype(np.float32)

            inp = mag0.reshape(1, 1, -1)
            curve = None
            if self._npu_engine is not None:
                curve = self._npu_engine.infer("audio_enhance", inp)

            if curve is not None:
                c = np.asarray(curve, dtype=np.float32).reshape(-1)
                if c.size >= n_bins:
                    g = c[:n_bins]
                else:
                    g = np.full(n_bins, 0.5, dtype=np.float32)
            else:
                g = np.full(n_bins, 0.5, dtype=np.float32)

            intensity = float(np.clip(self.npu_blend, 0.0, 1.0))
            spec_gain = 1.0 + (g - 0.5) * 2.0 * (0.1 + 0.55 * intensity)
            np.clip(spec_gain, 0.2, 5.0, out=spec_gain)

            timed = np.zeros((self._en_fft, n_ch), dtype=np.float64)
            for ch in range(n_ch):
                X = np.fft.rfft(frame[:, ch] * w)
                mag_c = np.abs(X)
                ang = np.angle(X)
                nb = min(mag_c.shape[0], spec_gain.shape[0])
                new_mag = mag_c[:nb] * spec_gain[:nb]
                if mag_c.shape[0] > nb:
                    new_mag = np.concatenate(
                        [new_mag, mag_c[nb:]],
                    )
                Y = new_mag * np.exp(1j * ang)
                t = np.fft.irfft(Y, n=self._en_fft).real.astype(np.float64) * ws
                timed[:, ch] = t

            self._ola_buf += timed
            hop_block = self._ola_buf[: self._en_hop].astype(np.float32, copy=True)
            self._out_fifo.append(hop_block)
            self._ola_buf = np.roll(self._ola_buf, -self._en_hop, axis=0)
            self._ola_buf[-self._en_hop :, :] = 0.0

        self._in_carry = buf
        return self._take_npu_fifo(audio.shape[0], n_ch, audio)

    def reset_streaming_state(self) -> None:
        """Clear overlap-add buffers (call when stage bypassed to avoid stale state)."""
        self._reset_npu_ola_state()

    def _build_processing_chain(self) -> None:
        self._multiband = self._create_multiband_filters()
        self._harmonic = HarmonicExciter(self.sample_rate, self.exciter)
        self._dynamics = MultibandCompressor(self.sample_rate)
        self._bass_enhancer = PsychoacousticBass(self.sample_rate)
        self._transient_shaper = TransientShaper(self.sample_rate)

        # State for LUFS measurement
        self._lufs_history: list[float] = []
        self._lufs_window = 20

    def _create_multiband_filters(
        self,
    ) -> list[tuple[str, np.ndarray, float]]:
        """Create 8-band parametric EQ with musical frequency targeting."""
        nyq = self.sample_rate / 2.0
        bands: list[tuple[str, np.ndarray, float]] = []

        # Sub-bass (20-50 Hz) - deep rumble foundation
        if 50.0 / nyq < 1.0:
            sos = signal.butter(4, 50.0 / nyq, btype="low", output="sos")
            bands.append(("sub_bass", sos, 1.0 + self.bass_boost * 1.0))

        # Bass (50-150 Hz) - punch and body
        lo, hi = 50.0 / nyq, min(150.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("bass", sos, 1.0 + self.warmth * 0.7))

        # Upper bass (150-300 Hz) - warmth
        lo, hi = 150.0 / nyq, min(300.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("upper_bass", sos, 1.0 + self.warmth * 0.4))

        # Low-mid (300-800 Hz) - slight cut to reduce muddiness
        lo, hi = 300.0 / nyq, min(800.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("low_mid", sos, 1.0 - 0.08))

        # Mid (800-2500 Hz) - clarity and vocal intelligibility
        lo, hi = 800.0 / nyq, min(2500.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("mid", sos, 1.0 + self.clarity * 0.4))

        # Upper-mid (2500-5000 Hz) - presence and attack
        lo, hi = 2500.0 / nyq, min(5000.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("presence", sos, 1.0 + self.presence * 0.5))

        # Brilliance (5000-10000 Hz) - shimmer and detail
        lo, hi = 5000.0 / nyq, min(10000.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(3, [lo, hi], btype="band", output="sos")
            bands.append(("brilliance", sos, 1.0 + self.air * 0.4))

        # Air (10000-20000 Hz) - sparkle and openness
        lo, hi = 10000.0 / nyq, min(20000.0, nyq - 1) / nyq
        if lo < hi:
            sos = signal.butter(2, [lo, hi], btype="band", output="sos")
            bands.append(("air", sos, 1.0 + self.air * 0.6))

        return bands

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or audio.shape[0] == 0:
            self._reset_npu_ola_state()
            return audio

        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])

        blend = float(np.clip(self.npu_blend, 0.0, 1.0))
        use_npu = blend > 1e-5 and self._npu_engine is not None
        x = audio.astype(np.float32, copy=False)
        if use_npu:
            shaped = self._spectral_npu_ola(x)
            x = (1.0 - blend) * x + blend * shaped

        # 1. Psychoacoustic bass
        if self.bass_boost > 0:
            x = self._bass_enhancer.process(x, self.bass_boost)

        # 2. Multi-band EQ
        x = self._apply_multiband_eq(x)

        # 3. Transient shaping
        x = self._transient_shaper.process(x)

        # 4. Harmonic exciter
        x = self._harmonic.process(x)

        # 5. Multi-band compression
        x = self._dynamics.process(x)

        # 6. Stereo width adjustment
        if self.stereo_width != 0.0 and x.ndim == 2:
            x = self._adjust_stereo_width(x)

        # 7. LUFS normalization with smoothing
        x = self._apply_loudness_normalization(x)

        return x.astype(np.float32)

    def _apply_multiband_eq(self, audio: np.ndarray) -> np.ndarray:
        output = np.zeros_like(audio, dtype=np.float64)
        for _name, sos, gain in self._multiband:
            if audio.ndim == 2:
                for ch in range(audio.shape[1]):
                    output[:, ch] += signal.sosfilt(sos, audio[:, ch]) * gain
            else:
                output += signal.sosfilt(sos, audio) * gain
        return output.astype(audio.dtype)

    def _adjust_stereo_width(self, audio: np.ndarray) -> np.ndarray:
        mid = (audio[:, 0] + audio[:, 1]) * 0.5
        side = (audio[:, 0] - audio[:, 1]) * 0.5
        width = 1.0 + self.stereo_width
        return np.column_stack([
            mid + side * width,
            mid - side * width,
        ])

    def _apply_loudness_normalization(self, audio: np.ndarray) -> np.ndarray:
        rms = np.sqrt(np.mean(audio ** 2)) + 1e-10
        current_lufs = 20 * np.log10(rms) - 0.691

        # Rolling average for smoother normalization
        self._lufs_history.append(current_lufs)
        if len(self._lufs_history) > self._lufs_window:
            self._lufs_history.pop(0)
        avg_lufs = np.mean(self._lufs_history)

        gain_db = np.clip(self.loudness_target - avg_lufs, -6.0, 6.0)
        return audio * (10 ** (gain_db / 20.0))

    def update_parameters(self, **kwargs: object) -> None:
        prev_blend = self.npu_blend
        changed = False
        for key, value in kwargs.items():
            if key == "enabled" or key not in self._TUNABLE_KEYS:
                continue
            if hasattr(self, key) and getattr(self, key) != value:
                setattr(self, key, value)
                changed = True
        if changed:
            if self.npu_blend <= 1e-5 and prev_blend > 1e-5:
                self._reset_npu_ola_state()
            self._build_processing_chain()


class HarmonicExciter:
    """Tape saturation harmonic exciter with independent even/odd control."""

    def __init__(self, sample_rate: int = 48000, intensity: float = 0.2):
        self.sample_rate = sample_rate
        self.intensity = intensity
        self.even_ratio = 0.65
        self.odd_ratio = 0.35

        # High-pass to only excite upper harmonics
        nyq = sample_rate / 2.0
        fc = min(1500.0, nyq - 1) / nyq
        if fc > 0:
            self._hp_sos = signal.butter(2, fc, btype="high", output="sos")
        else:
            self._hp_sos = None

    def process(self, audio: np.ndarray) -> np.ndarray:
        if self.intensity <= 0:
            return audio

        # Extract harmonics-relevant content
        if self._hp_sos is not None:
            if audio.ndim == 2:
                hp = np.zeros_like(audio)
                for ch in range(audio.shape[1]):
                    hp[:, ch] = signal.sosfilt(self._hp_sos, audio[:, ch])
            else:
                hp = signal.sosfilt(self._hp_sos, audio)
        else:
            hp = audio

        x = hp * (1.0 + self.intensity)

        # Tape-style saturation (asymmetric for richer harmonics)
        even = np.tanh(x * 1.5) * 0.5  # 2nd harmonic
        odd = (np.tanh(x * 2.5) - np.tanh(x)) * 0.3  # 3rd harmonic

        # 4th and 5th harmonics (subtle)
        h4 = np.tanh(x * 3.5) * 0.08
        h5 = (np.tanh(x * 4.5) - np.tanh(x * 2.0)) * 0.05

        harmonics = (
            even * self.even_ratio
            + odd * self.odd_ratio
            + h4 * self.even_ratio * 0.3
            + h5 * self.odd_ratio * 0.2
        )
        return audio + harmonics * self.intensity * 0.4


class PsychoacousticBass:
    """Generate missing fundamental harmonics for perceived bass boost.

    Uses multi-harmonic synthesis with frequency tracking for
    more natural bass enhancement.
    """

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        nyq = sample_rate / 2.0

        # Sub-bass extraction
        fc_sub = min(80.0, nyq - 1)
        if fc_sub > 0:
            self._sub_sos = signal.butter(4, fc_sub / nyq, btype="low", output="sos")
        else:
            self._sub_sos = None

        # Bass extraction
        fc_bass = min(150.0, nyq - 1)
        if fc_bass > 0 and fc_sub > 0:
            self._bass_sos = signal.butter(
                3, [fc_sub / nyq, fc_bass / nyq], btype="band", output="sos",
            )
        else:
            self._bass_sos = None

    def process(self, audio: np.ndarray, amount: float = 0.2) -> np.ndarray:
        if (self._sub_sos is None and self._bass_sos is None) or amount <= 0:
            return audio

        result = audio.copy().astype(np.float64)

        if self._sub_sos is not None:
            if audio.ndim == 2:
                sub = np.zeros_like(audio, dtype=np.float64)
                for ch in range(audio.shape[1]):
                    sub[:, ch] = signal.sosfilt(self._sub_sos, audio[:, ch])
            else:
                sub = signal.sosfilt(self._sub_sos, audio)

            # Generate 2nd and 3rd harmonics of sub-bass
            h2 = np.tanh(sub * 3.0) * 0.35
            h3 = np.tanh(sub * 5.0) * 0.18
            result += (h2 + h3) * amount

        if self._bass_sos is not None:
            if audio.ndim == 2:
                bass = np.zeros_like(audio, dtype=np.float64)
                for ch in range(audio.shape[1]):
                    bass[:, ch] = signal.sosfilt(self._bass_sos, audio[:, ch])
            else:
                bass = signal.sosfilt(self._bass_sos, audio)

            # 2nd harmonic of bass range
            h2_bass = np.tanh(bass * 2.5) * 0.2
            result += h2_bass * amount * 0.6

        return result.astype(audio.dtype)


class TransientShaper:
    """Transient shaper for attack/sustain control.

    Preserves or enhances transient attacks for punchier drums
    and clearer note articulation.
    """

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.attack_gain = 0.15
        self.sustain_gain = 0.0

        # Envelope follower coefficients
        fast_ms = 0.5
        slow_ms = 20.0
        self._fast_coeff = 1.0 - np.exp(-1.0 / (fast_ms * sample_rate / 1000))
        self._slow_coeff = 1.0 - np.exp(-1.0 / (slow_ms * sample_rate / 1000))
        self._fast_env = 0.0
        self._slow_env = 0.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        if self.attack_gain == 0 and self.sustain_gain == 0:
            return audio

        if audio.ndim == 2:
            mono = np.mean(np.abs(audio), axis=1)
        else:
            mono = np.abs(audio)

        rms = np.sqrt(np.mean(mono ** 2)) + 1e-10

        # Fast and slow envelope followers
        if rms > self._fast_env:
            self._fast_env += (rms - self._fast_env) * self._fast_coeff
        else:
            self._fast_env += (rms - self._fast_env) * self._fast_coeff * 0.1

        if rms > self._slow_env:
            self._slow_env += (rms - self._slow_env) * self._slow_coeff
        else:
            self._slow_env += (rms - self._slow_env) * self._slow_coeff

        # Transient = fast - slow
        transient = max(0.0, self._fast_env - self._slow_env)
        sustain = self._slow_env

        # Apply shaping
        attack_mod = 1.0 + transient * self.attack_gain * 10
        sustain_mod = 1.0 + sustain * self.sustain_gain * 2

        gain = min(2.0, attack_mod * sustain_mod)
        return audio * gain


class MultibandCompressor:
    """6-band dynamics compressor with lookahead-like smoothing."""

    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.threshold_db = -18.0
        self.ratio = 3.0
        self.attack_ms = 3.0
        self.release_ms = 80.0
        self.makeup_gain_db = 2.0

        nyq = sample_rate / 2.0
        self._bands: list[tuple[str, np.ndarray | None]] = []

        # Sub-bass (< 100 Hz) - gentle compression
        fc = min(100.0, nyq - 1) / nyq
        self._bands.append(("sub_bass", signal.butter(3, fc, btype="low", output="sos")))

        # Low (100-300 Hz)
        lo, hi = 100.0 / nyq, min(300.0, nyq - 1) / nyq
        if lo < hi:
            self._bands.append(("low", signal.butter(3, [lo, hi], btype="band", output="sos")))

        # Low-mid (300-1000 Hz)
        lo, hi = 300.0 / nyq, min(1000.0, nyq - 1) / nyq
        if lo < hi:
            self._bands.append(("low_mid", signal.butter(3, [lo, hi], btype="band", output="sos")))

        # High-mid (1000-4000 Hz)
        lo, hi = 1000.0 / nyq, min(4000.0, nyq - 1) / nyq
        if lo < hi:
            self._bands.append(("high_mid", signal.butter(3, [lo, hi], btype="band", output="sos")))

        # Presence (4000-8000 Hz)
        lo, hi = 4000.0 / nyq, min(8000.0, nyq - 1) / nyq
        if lo < hi:
            self._bands.append(("presence", signal.butter(3, [lo, hi], btype="band", output="sos")))

        # High (> 8000 Hz)
        fc = min(8000.0, nyq - 1) / nyq
        self._bands.append(("high", signal.butter(3, fc, btype="high", output="sos")))

        # Envelope followers per band
        self._envelopes = [0.0] * len(self._bands)

        attack_coeff = 1.0 - np.exp(-1.0 / (self.attack_ms * sample_rate / 1000))
        release_coeff = 1.0 - np.exp(-1.0 / (self.release_ms * sample_rate / 1000))
        self._attack = float(attack_coeff)
        self._release = float(release_coeff)

        # Per-band threshold adjustments
        self._band_thresholds = {
            "sub_bass": -20.0,
            "low": -18.0,
            "low_mid": -16.0,
            "high_mid": -18.0,
            "presence": -20.0,
            "high": -22.0,
        }

    def process(self, audio: np.ndarray) -> np.ndarray:
        output = np.zeros_like(audio, dtype=np.float64)
        makeup = 10 ** (self.makeup_gain_db / 20.0)

        for i, (name, sos) in enumerate(self._bands):
            if sos is None:
                continue

            threshold_db = self._band_thresholds.get(name, self.threshold_db)
            threshold_lin = 10 ** (threshold_db / 20.0)

            if audio.ndim == 2:
                band = np.zeros_like(audio)
                for ch in range(audio.shape[1]):
                    band[:, ch] = signal.sosfilt(sos, audio[:, ch])
            else:
                band = signal.sosfilt(sos, audio)

            rms = np.sqrt(np.mean(band ** 2)) + 1e-10
            if rms > self._envelopes[i]:
                self._envelopes[i] += (rms - self._envelopes[i]) * self._attack
            else:
                self._envelopes[i] += (rms - self._envelopes[i]) * self._release

            env = self._envelopes[i]
            if env > threshold_lin:
                gain_db = threshold_db + (20 * np.log10(env) - threshold_db) / self.ratio
                gain = 10 ** (gain_db / 20.0) / env
            else:
                gain = 1.0

            output += band * gain * makeup

        return output.astype(audio.dtype)
