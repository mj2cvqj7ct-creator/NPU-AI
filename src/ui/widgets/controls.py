"""
Audio Effect Control Widgets (v3 - Enhanced).

Provides styled slider controls, toggle buttons, and parameter panels
for all audio processing effects including new v3 controls for
transient shaping, psychoacoustic bass, multiband compression,
LUFS normalization, and allpass diffusion.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class EffectSlider(QWidget):
    """Labeled slider with value display for effect parameters."""

    value_changed = pyqtSignal(float)

    def __init__(
        self,
        label: str,
        min_val: float = 0.0,
        max_val: float = 1.0,
        default: float = 0.5,
        suffix: str = "",
        decimals: int = 2,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._suffix = suffix
        self._decimals = decimals

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._label = QLabel(label)
        self._label.setMinimumWidth(110)
        self._label.setMaximumWidth(140)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(self._to_slider(default))
        self._slider.valueChanged.connect(self._on_slider_changed)

        self._value_label = QLabel()
        self._value_label.setObjectName("valueLabel")
        self._value_label.setMinimumWidth(60)
        self._value_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self._update_value_display(default)

        layout.addWidget(self._label)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._value_label)

    def _to_slider(self, value: float) -> int:
        return int((value - self._min) / (self._max - self._min) * 1000)

    def _from_slider(self, slider_val: int) -> float:
        return self._min + (slider_val / 1000.0) * (self._max - self._min)

    def _on_slider_changed(self, slider_val: int) -> None:
        value = self._from_slider(slider_val)
        self._update_value_display(value)
        self.value_changed.emit(value)

    def _update_value_display(self, value: float) -> None:
        text = f"{value:.{self._decimals}f}{self._suffix}"
        self._value_label.setText(text)

    @property
    def value(self) -> float:
        return self._from_slider(self._slider.value())

    @value.setter
    def value(self, val: float) -> None:
        self._slider.setValue(self._to_slider(val))


class SpatialControlPanel(QGroupBox):
    """Control panel for spatial audio and holographic processing."""

    params_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Spatial Audio & Holographic", parent)

        layout = QVBoxLayout(self)

        self._enable = QCheckBox("Enable Spatial Processing")
        self._enable.setChecked(True)
        self._enable.toggled.connect(self._emit_params)

        self._width = EffectSlider("Soundstage", 0, 1.5, 0.7)
        self._depth = EffectSlider("Depth", 0, 1.0, 0.5)
        self._height = EffectSlider("Height", 0, 1.0, 0.3)
        self._holographic = EffectSlider("Holographic", 0, 1.0, 0.6)
        self._crossfeed = EffectSlider("Crossfeed", 0, 1.0, 0.3)
        self._center = EffectSlider("Center Focus", 0, 1.0, 0.5)
        self._stereo = EffectSlider("Stereo Enhance", 0, 1.0, 0.4)
        self._immersion = EffectSlider("Immersion", 0, 1.0, 0.5)
        self._diffusion = EffectSlider("Allpass Diffusion", 0, 1.0, 0.3)

        sliders = [
            self._width, self._depth, self._height, self._holographic,
            self._crossfeed, self._center, self._stereo, self._immersion,
            self._diffusion,
        ]
        for slider in sliders:
            slider.value_changed.connect(lambda _: self._emit_params())

        layout.addWidget(self._enable)
        for slider in sliders:
            layout.addWidget(slider)

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_params(self) -> dict[str, object]:
        return {
            "enabled": self._enable.isChecked(),
            "soundstage_width": self._width.value,
            "depth": self._depth.value,
            "height": self._height.value,
            "holographic_intensity": self._holographic.value,
            "crossfeed_level": self._crossfeed.value,
            "center_focus": self._center.value,
            "stereo_enhance": self._stereo.value,
            "immersion": self._immersion.value,
            "diffusion": self._diffusion.value,
        }


class SeparationControlPanel(QGroupBox):
    """Control panel for source separation settings."""

    params_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Source Separation", parent)

        layout = QVBoxLayout(self)

        self._enable = QCheckBox("Enable Source Separation")
        self._enable.setChecked(True)
        self._enable.toggled.connect(self._emit_params)

        self._vocal_boost = EffectSlider("Vocal Boost", 0, 1.0, 0.3)
        self._instrument = EffectSlider("Instrument Clarity", 0, 1.0, 0.5)
        self._bass = EffectSlider("Bass Enhance", 0, 1.0, 0.2)
        self._drums = EffectSlider("Drum Punch", 0, 1.0, 0.2)
        self._wiener = EffectSlider("Wiener Iterations", 1, 5, 3, "", 0)

        for slider in [
            self._vocal_boost, self._instrument,
            self._bass, self._drums, self._wiener,
        ]:
            slider.value_changed.connect(lambda _: self._emit_params())

        layout.addWidget(self._enable)
        layout.addWidget(self._vocal_boost)
        layout.addWidget(self._instrument)
        layout.addWidget(self._bass)
        layout.addWidget(self._drums)
        layout.addWidget(self._wiener)

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_params(self) -> dict[str, object]:
        return {
            "enabled": self._enable.isChecked(),
            "vocal_boost": self._vocal_boost.value,
            "instrument_clarity": self._instrument.value,
            "bass_enhance": self._bass.value,
            "drum_punch": self._drums.value,
            "wiener_iterations": int(self._wiener.value),
        }


class EnhancerControlPanel(QGroupBox):
    """Control panel for audio quality enhancement (v3)."""

    params_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Audio Enhancement", parent)

        layout = QVBoxLayout(self)

        self._enable = QCheckBox("Enable Enhancement")
        self._enable.setChecked(True)
        self._enable.toggled.connect(self._emit_params)

        self._warmth = EffectSlider("Warmth", 0, 1.0, 0.3)
        self._clarity = EffectSlider("Clarity", 0, 1.0, 0.5)
        self._presence = EffectSlider("Presence", 0, 1.0, 0.4)
        self._air = EffectSlider("Air", 0, 1.0, 0.3)
        self._bass_boost = EffectSlider("Bass Boost", 0, 1.0, 0.2)
        self._exciter = EffectSlider("Harmonic Exciter", 0, 1.0, 0.2)
        self._transient = EffectSlider("Transient Shape", -1.0, 1.0, 0.0)
        self._psych_bass = EffectSlider("Psycho Bass", 0, 1.0, 0.3)
        self._compression = EffectSlider("Multiband Comp", 0, 1.0, 0.3)
        self._stereo_width = EffectSlider("Stereo Width", -0.5, 1.0, 0.0)
        self._lufs_target = EffectSlider("LUFS Target", -24, -6, -14, " LUFS", 0)

        sliders = [
            self._warmth, self._clarity, self._presence, self._air,
            self._bass_boost, self._exciter, self._transient,
            self._psych_bass, self._compression, self._stereo_width,
            self._lufs_target,
        ]
        for slider in sliders:
            slider.value_changed.connect(lambda _: self._emit_params())

        layout.addWidget(self._enable)
        for slider in sliders:
            layout.addWidget(slider)

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_params(self) -> dict[str, object]:
        return {
            "enabled": self._enable.isChecked(),
            "warmth": self._warmth.value,
            "clarity": self._clarity.value,
            "presence": self._presence.value,
            "air": self._air.value,
            "bass_boost": self._bass_boost.value,
            "exciter": self._exciter.value,
            "transient_shape": self._transient.value,
            "psychoacoustic_bass": self._psych_bass.value,
            "multiband_compression": self._compression.value,
            "stereo_width": self._stereo_width.value,
            "lufs_target": self._lufs_target.value,
        }


class DepthControlPanel(QGroupBox):
    """Control panel for depth and soundstage processing (v3)."""

    params_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Depth & Soundstage", parent)

        layout = QVBoxLayout(self)

        self._enable = QCheckBox("Enable Depth Processing")
        self._enable.setChecked(True)
        self._enable.toggled.connect(self._emit_params)

        self._depth = EffectSlider("Depth Amount", 0, 1.0, 0.5)
        self._room = EffectSlider("Room Size", 0, 1.0, 0.4)
        self._damping = EffectSlider("HF Damping", 0, 1.0, 0.5)
        self._damp_lo = EffectSlider("LF Damping", 0, 1.0, 0.3)
        self._pre_delay = EffectSlider("Pre-delay", 0, 50.0, 15.0, " ms", 0)
        self._early_ref = EffectSlider("Early Reflections", 0, 1.0, 0.3)
        self._late_rev = EffectSlider("Late Reverb", 0, 1.0, 0.2)
        self._diffusion = EffectSlider("Diffusion", 0, 1.0, 0.7)
        self._modulation = EffectSlider("Mod Depth", 0, 1.0, 0.3)

        sliders = [
            self._depth, self._room, self._damping, self._damp_lo,
            self._pre_delay, self._early_ref, self._late_rev,
            self._diffusion, self._modulation,
        ]
        for slider in sliders:
            slider.value_changed.connect(lambda _: self._emit_params())

        layout.addWidget(self._enable)
        for slider in sliders:
            layout.addWidget(slider)

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_params(self) -> dict[str, object]:
        return {
            "enabled": self._enable.isChecked(),
            "depth_amount": self._depth.value,
            "room_size": self._room.value,
            "damping": self._damping.value,
            "damp_lo": self._damp_lo.value,
            "pre_delay_ms": self._pre_delay.value,
            "early_reflection_mix": self._early_ref.value,
            "late_reverb_mix": self._late_rev.value,
            "diffusion": self._diffusion.value,
            "modulation_depth": self._modulation.value,
        }


class MasterControlBar(QWidget):
    """Master control bar with play/stop, bypass, and volume."""

    bypass_toggled = pyqtSignal(bool)
    volume_changed = pyqtSignal(float)
    play_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._play_btn = QPushButton("Start")
        self._play_btn.setObjectName("primaryButton")
        self._play_btn.setCheckable(True)
        self._play_btn.setMinimumWidth(120)
        self._play_btn.toggled.connect(self._on_play_toggled)

        self._bypass_btn = QPushButton("Bypass")
        self._bypass_btn.setCheckable(True)
        self._bypass_btn.toggled.connect(self.bypass_toggled.emit)

        self._volume = EffectSlider("Master", 0, 2.0, 1.0, "", 2)
        self._volume.value_changed.connect(self.volume_changed.emit)

        self._status = QLabel("Ready")
        self._status.setObjectName("statusLabel")

        layout.addWidget(self._play_btn)
        layout.addWidget(self._bypass_btn)
        layout.addWidget(self._volume, 1)
        layout.addWidget(self._status)

    def _on_play_toggled(self, checked: bool) -> None:
        self._play_btn.setText("Stop" if checked else "Start")
        self.play_toggled.emit(checked)

    @property
    def is_playing(self) -> bool:
        return self._play_btn.isChecked()

    def set_status(self, text: str) -> None:
        self._status.setText(text)
