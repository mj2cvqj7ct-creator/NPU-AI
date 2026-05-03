"""
Audio Effect Control Widgets.

Provides styled slider controls, toggle buttons, and parameter panels
for all audio processing effects with modern layout and responsive design.
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
        self._label.setMinimumWidth(100)
        self._label.setMaximumWidth(130)

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
        super().__init__("空間オーディオとホログラフィック", parent)

        layout = QVBoxLayout(self)

        self._enable = QCheckBox("空間処理を有効にする")
        self._enable.setChecked(True)
        self._enable.toggled.connect(self._emit_params)

        self._width = EffectSlider("サウンドステージ", 0, 1.5, 0.7)
        self._depth = EffectSlider("奥行き", 0, 1.0, 0.5)
        self._height = EffectSlider("高さ", 0, 1.0, 0.3)
        self._holographic = EffectSlider("ホログラフィック", 0, 1.0, 0.6)
        self._crossfeed = EffectSlider("クロスフィード", 0, 1.0, 0.3)
        self._center = EffectSlider("センター定位", 0, 1.0, 0.5)
        self._stereo = EffectSlider("ステレオ拡張", 0, 1.0, 0.4)
        self._immersion = EffectSlider("没入感", 0, 1.0, 0.5)

        sliders = [
            self._width, self._depth, self._height, self._holographic,
            self._crossfeed, self._center, self._stereo, self._immersion,
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
        }


class SeparationControlPanel(QGroupBox):
    """Control panel for source separation settings."""

    params_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("ソース分離", parent)

        layout = QVBoxLayout(self)

        self._enable = QCheckBox("ソース分離を有効にする")
        self._enable.setChecked(True)
        self._enable.toggled.connect(self._emit_params)

        self._vocal_boost = EffectSlider("ボーカル強調", 0, 1.0, 0.3)
        self._instrument = EffectSlider("楽器の明瞭さ", 0, 1.0, 0.5)
        self._bass = EffectSlider("ベース強調", 0, 1.0, 0.2)
        self._drums = EffectSlider("ドラムのパンチ", 0, 1.0, 0.2)

        for slider in [self._vocal_boost, self._instrument, self._bass, self._drums]:
            slider.value_changed.connect(lambda _: self._emit_params())

        layout.addWidget(self._enable)
        layout.addWidget(self._vocal_boost)
        layout.addWidget(self._instrument)
        layout.addWidget(self._bass)
        layout.addWidget(self._drums)

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_params(self) -> dict[str, object]:
        return {
            "enabled": self._enable.isChecked(),
            "vocal_boost": self._vocal_boost.value,
            "instrument_clarity": self._instrument.value,
            "bass_enhance": self._bass.value,
            "drum_punch": self._drums.value,
        }


class EnhancerControlPanel(QGroupBox):
    """Control panel for audio quality enhancement."""

    params_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("オーディオ強化", parent)

        layout = QVBoxLayout(self)

        self._enable = QCheckBox("強化を有効にする")
        self._enable.setChecked(True)
        self._enable.toggled.connect(self._emit_params)

        self._npu_blend = EffectSlider("AI スペクトル（NPU）", 0, 1.0, 0.35)

        self._warmth = EffectSlider("ウォームさ", 0, 1.0, 0.3)
        self._clarity = EffectSlider("明瞭さ", 0, 1.0, 0.5)
        self._presence = EffectSlider("存在感", 0, 1.0, 0.4)
        self._air = EffectSlider("エア感", 0, 1.0, 0.3)
        self._bass_boost = EffectSlider("ベースブースト", 0, 1.0, 0.2)
        self._exciter = EffectSlider("ハーモニックエキサイター", 0, 1.0, 0.2)
        self._stereo_width = EffectSlider("ステレオ幅", -0.5, 1.0, 0.0)

        sliders = [
            self._npu_blend,
            self._warmth, self._clarity, self._presence, self._air,
            self._bass_boost, self._exciter, self._stereo_width,
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
            "npu_blend": self._npu_blend.value,
            "warmth": self._warmth.value,
            "clarity": self._clarity.value,
            "presence": self._presence.value,
            "air": self._air.value,
            "bass_boost": self._bass_boost.value,
            "exciter": self._exciter.value,
            "stereo_width": self._stereo_width.value,
        }


class NoiseReducerControlPanel(QGroupBox):
    """NPU-driven spectral noise attenuation (noise_reduction ONNX)."""

    params_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("AI ノイズ低減（NPU）", parent)

        layout = QVBoxLayout(self)

        self._enable = QCheckBox("有効にする")
        self._enable.setChecked(False)
        self._enable.toggled.connect(self._emit_params)

        self._amount = EffectSlider("減衰量", 0, 1.0, 0.25)

        self._amount.value_changed.connect(lambda _: self._emit_params())

        layout.addWidget(self._enable)
        layout.addWidget(self._amount)

    def _emit_params(self) -> None:
        self.params_changed.emit(self.get_params())

    def get_params(self) -> dict[str, object]:
        return {
            "enabled": self._enable.isChecked(),
            "npu_blend": self._amount.value,
        }


class DepthControlPanel(QGroupBox):
    """Control panel for depth and soundstage processing."""

    params_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("奥行きとサウンドステージ", parent)

        layout = QVBoxLayout(self)

        self._enable = QCheckBox("奥行き処理を有効にする")
        self._enable.setChecked(True)
        self._enable.toggled.connect(self._emit_params)

        self._depth = EffectSlider("奥行き量", 0, 1.0, 0.5)
        self._room = EffectSlider("ルームサイズ", 0, 1.0, 0.4)
        self._damping = EffectSlider("減衰（ダンピング）", 0, 1.0, 0.5)
        self._pre_delay = EffectSlider("プリディレイ", 0, 50.0, 15.0, " ms", 0)
        self._early_ref = EffectSlider("初期反射", 0, 1.0, 0.3)
        self._late_rev = EffectSlider("後期リバーブ", 0, 1.0, 0.2)

        sliders = [
            self._depth, self._room, self._damping,
            self._pre_delay, self._early_ref, self._late_rev,
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
            "pre_delay_ms": self._pre_delay.value,
            "early_reflection_mix": self._early_ref.value,
            "late_reverb_mix": self._late_rev.value,
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

        self._play_btn = QPushButton("開始")
        self._play_btn.setObjectName("primaryButton")
        self._play_btn.setCheckable(True)
        self._play_btn.setMinimumWidth(100)
        self._play_btn.toggled.connect(self._on_play_toggled)

        self._bypass_btn = QPushButton("バイパス")
        self._bypass_btn.setCheckable(True)
        self._bypass_btn.toggled.connect(self.bypass_toggled.emit)

        self._volume = EffectSlider("マスター", 0, 2.0, 1.0, "", 2)
        self._volume.value_changed.connect(self.volume_changed.emit)

        self._status = QLabel("準備完了")
        self._status.setObjectName("statusLabel")

        layout.addWidget(self._play_btn)
        layout.addWidget(self._bypass_btn)
        layout.addWidget(self._volume, 1)
        layout.addWidget(self._status)

    def _on_play_toggled(self, checked: bool) -> None:
        self._play_btn.setText("停止" if checked else "開始")
        self.play_toggled.emit(checked)

    @property
    def is_playing(self) -> bool:
        return self._play_btn.isChecked()

    def set_status(self, text: str) -> None:
        self._status.setText(text)
