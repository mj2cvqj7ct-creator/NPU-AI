"""
Main Application Window (v3 - Modern & Refined).

Premium dark-themed interface with glassmorphism styling,
real-time spectral visualizations, and comprehensive
audio processing controls.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.presets import EffectPreset, PresetManager
from src.settings import SettingsManager
from src.ui.styles import DARK_THEME
from src.ui.tray import SystemTrayManager
from src.ui.widgets.controls import (
    DepthControlPanel,
    EnhancerControlPanel,
    MasterControlBar,
    PresetSelector,
    SeparationControlPanel,
    SpatialControlPanel,
)
from src.ui.widgets.dac_panel import DACControlPanel
from src.ui.widgets.recommender_panel import RecommenderPanel
from src.ui.widgets.visualizer import (
    SpectrumVisualizer,
    StemLevelMeters,
    WaveformVisualizer,
)

if TYPE_CHECKING:
    from src.app import AudioEnhancerApp

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with modern dark theme UI."""

    def __init__(self, app_controller: AudioEnhancerApp | None = None):
        super().__init__()
        self._app = app_controller
        self._preset_manager = PresetManager()
        self._settings_mgr = SettingsManager()

        self.setWindowTitle("NPU Audio Enhancer - Snapdragon X Elite")
        self.setMinimumSize(1200, 800)
        self.resize(1500, 950)

        self.setStyleSheet(DARK_THEME)
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        self._setup_timers()
        self._connect_signals()
        self._setup_shortcuts()
        self._restore_settings()
        self._tray = SystemTrayManager(self)

    def _setup_ui(self) -> None:
        """Build the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        header = self._create_header()
        main_layout.addWidget(header)

        self._master_bar = MasterControlBar()
        main_layout.addWidget(self._master_bar)

        self._preset_selector = PresetSelector(self._preset_manager)
        main_layout.addWidget(self._preset_selector)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self._create_visualization_panel()
        splitter.addWidget(left_panel)

        right_panel = self._create_control_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([700, 500])
        main_layout.addWidget(splitter, 1)

    def _create_header(self) -> QWidget:
        """Create the application header with branding."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)

        title = QLabel("NPU Audio Enhancer")
        title.setObjectName("headerTitle")
        title_font = QFont("Segoe UI", 22, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #A29BFE; letter-spacing: 1.5px;")

        subtitle = QLabel(
            "Snapdragon X Elite NPU  |  Real-time AI Processing  |  "
            "Spotify / Apple Music / YouTube Music"
        )
        subtitle.setObjectName("statusLabel")

        npu_status = QLabel("NPU: Initializing...")
        npu_status.setObjectName("npuBadge")
        self._npu_status_label = npu_status

        dac_badge = QLabel("DAC: Detecting...")
        dac_badge.setObjectName("statusLabel")
        self._dac_badge = dac_badge

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(dac_badge)
        layout.addSpacing(10)
        layout.addWidget(npu_status)

        return header

    def _create_visualization_panel(self) -> QWidget:
        """Create the left panel with audio visualizations."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        viz_label = QLabel("Audio Analysis")
        viz_label.setObjectName("sectionTitle")
        layout.addWidget(viz_label)

        self._spectrum = SpectrumVisualizer()
        self._spectrum.setMinimumHeight(200)
        layout.addWidget(self._spectrum)

        self._waveform = WaveformVisualizer()
        self._waveform.setMinimumHeight(120)
        layout.addWidget(self._waveform)

        stems_label = QLabel("Source Separation")
        stems_label.setObjectName("sectionTitle")
        layout.addWidget(stems_label)

        self._stem_meters = StemLevelMeters()
        layout.addWidget(self._stem_meters)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        self._latency_label = QLabel("Latency: -- ms")
        self._latency_label.setObjectName("valueLabel")
        self._cpu_label = QLabel("CPU: --%")
        self._cpu_label.setObjectName("valueLabel")
        self._buffer_label = QLabel("Buffer: OK")
        self._buffer_label.setObjectName("valueLabel")
        self._npu_load_label = QLabel("NPU: --")
        self._npu_load_label.setObjectName("valueLabel")
        stats_row.addWidget(self._latency_label)
        stats_row.addWidget(self._cpu_label)
        stats_row.addWidget(self._buffer_label)
        stats_row.addWidget(self._npu_load_label)
        layout.addLayout(stats_row)

        layout.addStretch()
        return panel

    def _create_control_panel(self) -> QWidget:
        """Create the right panel with tabbed controls."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        tabs = QTabWidget()
        self._tabs = tabs

        effects_tab = self._create_effects_tab()
        tabs.addTab(effects_tab, "Effects")

        dac_tab = self._create_dac_tab()
        tabs.addTab(dac_tab, "SABAJ DAC")

        rec_tab = self._create_recommender_tab()
        tabs.addTab(rec_tab, "AI Recommend")

        layout.addWidget(tabs)
        return panel

    def _create_effects_tab(self) -> QWidget:
        """Create the effects control tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        self._spatial_panel = SpatialControlPanel()
        self._separation_panel = SeparationControlPanel()
        self._enhancer_panel = EnhancerControlPanel()
        self._depth_panel = DepthControlPanel()

        layout.addWidget(self._spatial_panel)
        layout.addWidget(self._separation_panel)
        layout.addWidget(self._enhancer_panel)
        layout.addWidget(self._depth_panel)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _create_dac_tab(self) -> QWidget:
        """Create the DAC control tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)

        self._dac_panel = DACControlPanel()
        layout.addWidget(self._dac_panel)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _create_recommender_tab(self) -> QWidget:
        """Create the recommendation engine tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)

        self._recommender_panel = RecommenderPanel()
        layout.addWidget(self._recommender_panel)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _setup_menu(self) -> None:
        """Setup application menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("View")
        self._always_on_top = QAction("Always on Top", self)
        self._always_on_top.setCheckable(True)
        self._always_on_top.triggered.connect(self._toggle_always_on_top)
        view_menu.addAction(self._always_on_top)

        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_status_bar(self) -> None:
        """Setup status bar."""
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready - Connect audio source to begin processing")

    def _setup_timers(self) -> None:
        """Setup UI update timers."""
        self._viz_timer = QTimer(self)
        self._viz_timer.timeout.connect(self._update_visualizations)
        self._viz_timer.start(33)  # ~30fps

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(500)

    def _connect_signals(self) -> None:
        """Connect UI signals to application controller."""
        if not self._app:
            return

        self._master_bar.play_toggled.connect(self._on_play_toggled)
        self._master_bar.bypass_toggled.connect(self._on_bypass_toggled)
        self._master_bar.volume_changed.connect(self._on_volume_changed)

        self._spatial_panel.params_changed.connect(self._on_spatial_changed)
        self._separation_panel.params_changed.connect(self._on_separation_changed)
        self._enhancer_panel.params_changed.connect(self._on_enhancer_changed)
        self._depth_panel.params_changed.connect(self._on_depth_changed)

        self._dac_panel.optimize_requested.connect(self._on_optimize_dac)
        self._dac_panel.config_changed.connect(self._on_dac_config_changed)

        self._recommender_panel.track_liked.connect(self._on_track_liked)
        self._recommender_panel.track_skipped.connect(self._on_track_skipped)

        self._preset_selector.preset_selected.connect(self._on_preset_selected)
        self._preset_selector.save_requested.connect(self._on_preset_save)
        self._preset_selector.delete_requested.connect(self._on_preset_delete)

    @pyqtSlot(bool)
    def _on_play_toggled(self, playing: bool) -> None:
        if self._app:
            if playing:
                self._app.start_processing()
                self._master_bar.set_status("Processing...")
                self.statusBar().showMessage("Audio processing active")
            else:
                self._app.stop_processing()
                self._master_bar.set_status("Stopped")
                self.statusBar().showMessage("Audio processing stopped")

    @pyqtSlot(bool)
    def _on_bypass_toggled(self, bypassed: bool) -> None:
        if self._app:
            self._app.processor.bypass = bypassed

    @pyqtSlot(float)
    def _on_volume_changed(self, volume: float) -> None:
        if self._app:
            self._app.processor.master_gain = volume

    @pyqtSlot(dict)
    def _on_spatial_changed(self, params: dict) -> None:
        if self._app:
            spatial = self._app.processor.spatial
            spatial.enabled = params.pop("enabled", True)
            spatial.update_parameters(**params)

    @pyqtSlot(dict)
    def _on_separation_changed(self, params: dict) -> None:
        if self._app:
            sep = self._app.processor.separator
            sep.config.enabled = params.get("enabled", True)
            sep.config.vocal_boost = params.get("vocal_boost", 0.3)
            sep.config.instrument_clarity = params.get("instrument_clarity", 0.5)
            sep.config.bass_enhance = params.get("bass_enhance", 0.2)
            sep.config.drum_punch = params.get("drum_punch", 0.2)
            sep.config.wiener_iterations = int(params.get("wiener_iterations", 3))

    @pyqtSlot(dict)
    def _on_enhancer_changed(self, params: dict) -> None:
        if self._app:
            self._app.processor.enhancer.update_parameters(**{
                k: v for k, v in params.items() if k != "enabled"
            })
            self._app.processor.enhancer.enabled = params.get("enabled", True)

    @pyqtSlot(dict)
    def _on_depth_changed(self, params: dict) -> None:
        if self._app:
            depth = self._app.processor.depth
            depth.enabled = params.pop("enabled", True)
            depth.update_parameters(**params)

    @pyqtSlot()
    def _on_optimize_dac(self) -> None:
        if self._app:
            settings = self._app.dac_controller.optimize_for_npu()
            self._dac_panel.show_optimization_result(settings)

    @pyqtSlot(dict)
    def _on_dac_config_changed(self, config: dict) -> None:
        if self._app:
            self._app.dac_controller.set_buffer_size(config.get("buffer_size_ms", 10))
            self._app.dac_controller.set_latency(config.get("latency_ms", 5))

    @pyqtSlot()
    def _on_track_liked(self) -> None:
        if self._app:
            self._app.on_track_liked()

    @pyqtSlot()
    def _on_track_skipped(self) -> None:
        if self._app:
            self._app.on_track_skipped()

    @pyqtSlot(str)
    def _on_preset_selected(self, name: str) -> None:
        preset = self._preset_manager.apply_preset(name)
        if not preset:
            return
        params = asdict(preset)
        self._spatial_panel.set_params(params)
        self._separation_panel.set_params(params)
        self._enhancer_panel.set_params(params)
        self._depth_panel.set_params(params)
        # Push to backend
        self._on_spatial_changed(self._spatial_panel.get_params())
        self._on_separation_changed(self._separation_panel.get_params())
        self._on_enhancer_changed(self._enhancer_panel.get_params())
        self._on_depth_changed(self._depth_panel.get_params())
        self.statusBar().showMessage(f"Preset loaded: {name}")

    @pyqtSlot(str)
    def _on_preset_save(self, name: str) -> None:
        preset = EffectPreset(name=name)
        sp = self._spatial_panel.get_params()
        preset.spatial_enabled = sp.get("enabled", True)
        preset.soundstage_width = sp.get("soundstage_width", 0.7)
        preset.depth = sp.get("depth", 0.5)
        preset.height = sp.get("height", 0.3)
        preset.holographic_intensity = sp.get("holographic_intensity", 0.6)
        preset.crossfeed_level = sp.get("crossfeed_level", 0.3)
        preset.center_focus = sp.get("center_focus", 0.5)
        preset.stereo_enhance = sp.get("stereo_enhance", 0.4)
        preset.immersion = sp.get("immersion", 0.5)
        preset.diffusion = sp.get("diffusion", 0.3)
        sep = self._separation_panel.get_params()
        preset.separation_enabled = sep.get("enabled", True)
        preset.vocal_boost = sep.get("vocal_boost", 0.3)
        preset.instrument_clarity = sep.get("instrument_clarity", 0.5)
        preset.bass_enhance = sep.get("bass_enhance", 0.2)
        preset.drum_punch = sep.get("drum_punch", 0.2)
        preset.wiener_iterations = int(sep.get("wiener_iterations", 3))
        enh = self._enhancer_panel.get_params()
        preset.enhancer_enabled = enh.get("enabled", True)
        preset.warmth = enh.get("warmth", 0.3)
        preset.clarity = enh.get("clarity", 0.5)
        preset.presence = enh.get("presence", 0.4)
        preset.air = enh.get("air", 0.3)
        preset.bass_boost = enh.get("bass_boost", 0.2)
        preset.exciter = enh.get("exciter", 0.2)
        preset.transient_shape = enh.get("transient_shape", 0.0)
        preset.psychoacoustic_bass = enh.get("psychoacoustic_bass", 0.3)
        preset.multiband_compression = enh.get("multiband_compression", 0.3)
        preset.stereo_width = enh.get("stereo_width", 0.0)
        preset.loudness_target = enh.get("loudness_target", -14.0)
        dep = self._depth_panel.get_params()
        preset.depth_enabled = dep.get("enabled", True)
        preset.depth_amount = dep.get("depth_amount", 0.5)
        preset.room_size = dep.get("room_size", 0.4)
        preset.damping = dep.get("damping", 0.5)
        preset.damp_lo = dep.get("damp_lo", 0.3)
        preset.depth_diffusion = dep.get("diffusion", 0.7)
        preset.modulation_depth = dep.get("modulation_depth", 0.3)
        preset.pre_delay_ms = dep.get("pre_delay_ms", 15.0)
        preset.early_reflection_mix = dep.get("early_reflection_mix", 0.3)
        preset.late_reverb_mix = dep.get("late_reverb_mix", 0.2)
        self._preset_manager.save_preset(preset)
        self._preset_selector.refresh()
        self.statusBar().showMessage(f"Preset saved: {name}")

    @pyqtSlot(str)
    def _on_preset_delete(self, name: str) -> None:
        if self._preset_manager.delete_preset(name):
            self._preset_selector.refresh()
            self.statusBar().showMessage(f"Preset deleted: {name}")

    def _setup_shortcuts(self) -> None:
        """Configure keyboard shortcuts."""
        # Space - toggle play/stop
        sc_play = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        sc_play.activated.connect(lambda: self._master_bar._play_btn.toggle())

        # B - toggle bypass
        sc_bypass = QShortcut(QKeySequence(Qt.Key.Key_B), self)
        sc_bypass.activated.connect(lambda: self._master_bar._bypass_btn.toggle())

        # Ctrl+S - save current as preset
        sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_save.activated.connect(lambda: self._preset_selector._on_save_clicked())

        # 1-3 - switch effect tabs
        for i in range(3):
            sc = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            sc.activated.connect(lambda idx=i: self._tabs.setCurrentIndex(idx))

        # A - toggle A/B comparison mode
        sc_ab = QShortcut(QKeySequence(Qt.Key.Key_A), self)
        sc_ab.activated.connect(self._toggle_ab_mode)

        # Ctrl+Up / Ctrl+Down - volume adjust
        sc_vol_up = QShortcut(QKeySequence("Ctrl+Up"), self)
        sc_vol_up.activated.connect(
            lambda: setattr(
                self._master_bar._volume,
                "value",
                min(2.0, self._master_bar._volume.value + 0.05),
            ),
        )
        sc_vol_down = QShortcut(QKeySequence("Ctrl+Down"), self)
        sc_vol_down.activated.connect(
            lambda: setattr(
                self._master_bar._volume,
                "value",
                max(0.0, self._master_bar._volume.value - 0.05),
            ),
        )

    def _toggle_ab_mode(self) -> None:
        """Toggle A/B comparison mode with crossfade."""
        if not self._app:
            return
        proc = self._app.processor
        proc.ab_mode = not proc.ab_mode
        state = "ON" if proc.ab_mode else "OFF"
        self.statusBar().showMessage(f"A/B Comparison: {state}")

    def _update_visualizations(self) -> None:
        """Update audio visualizations from processing data."""
        if not self._app or not self._master_bar.is_playing:
            return

        viz_data = self._app.get_visualization_data()
        if viz_data:
            if viz_data.get("spectrum"):
                self._spectrum.update_spectrum(viz_data["spectrum"])
            if viz_data.get("waveform"):
                self._waveform.update_waveform(viz_data["waveform"])
            if viz_data.get("stem_levels"):
                self._stem_meters.update_levels(viz_data["stem_levels"])

    def _update_stats(self) -> None:
        """Update processing statistics display."""
        if not self._app:
            return

        stats = self._app.processor.stats
        self._latency_label.setText(f"Latency: {stats.processing_time_ms:.1f} ms")

        try:
            import psutil

            cpu = psutil.cpu_percent(interval=None)
            self._cpu_label.setText(f"CPU: {cpu:.0f}%")
        except ImportError:
            pass

        npu_info = self._app.npu_engine.get_device_info()
        provider = npu_info.get("provider", "N/A")
        if npu_info.get("is_npu"):
            self._npu_status_label.setText(f"NPU: Active ({provider})")
            self._npu_status_label.setStyleSheet(
                "color: #00B894; border-color: #00B894;"
            )
        elif provider != "None":
            self._npu_status_label.setText(f"NPU: {provider}")
            self._npu_status_label.setStyleSheet(
                "color: #FDCB6E; border-color: #FDCB6E;"
            )
        else:
            self._npu_status_label.setText("NPU: DSP Mode")
            self._npu_status_label.setStyleSheet(
                "color: #8B949E; border-color: #8B949E;"
            )

        # NPU processing time
        npu_ms = npu_info.get("avg_inference_ms", 0)
        self._npu_load_label.setText(f"NPU: {npu_ms:.1f}ms")

        dac_status = self._app.dac_controller.get_status_info()
        self._dac_panel.update_status(dac_status)

        # DAC badge
        dac_name = dac_status.get("device_name", "N/A")
        dac_st = dac_status.get("status", "disconnected")
        if dac_st in ("connected", "streaming"):
            self._dac_badge.setText(f"DAC: {dac_name}")
            self._dac_badge.setStyleSheet("color: #00B894;")
        else:
            self._dac_badge.setText("DAC: Not Connected")
            self._dac_badge.setStyleSheet("color: #8B949E;")

        profile = self._app.recommender.preference_profile
        self._recommender_panel.update_preferences(profile)

    def _toggle_always_on_top(self, checked: bool) -> None:
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def _show_about(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "About NPU Audio Enhancer",
            "<h2>NPU Audio Enhancer v3.2.0</h2>"
            "<p>ARM64 Snapdragon X Elite NPU-accelerated real-time audio enhancement</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Phase-aware source separation with Wiener filtering & HPSS</li>"
            "<li>512-tap HRTF with pinna notch & concha resonance modeling</li>"
            "<li>6-band holographic soundstage with allpass diffusion</li>"
            "<li>12-line FDN reverb with modulated delay lines</li>"
            "<li>Tape saturation harmonic exciter with transient shaping</li>"
            "<li>SABAJ A20D ES9038PRO DAC with triple-buffer NPU streaming</li>"
            "<li>Adam-optimized deep learning recommendations</li>"
            "<li>8 built-in presets with user-defined preset management</li>"
            "<li>A/B comparison with smooth crossfade bypass</li>"
            "<li>System tray integration with playback controls</li>"
            "<li>Persistent settings (window state, last preset, volume)</li>"
            "<li>64 unit tests covering all core modules</li>"
            "<li>Spotify / Apple Music / YouTube Music support</li>"
            "</ul>"
            "<p><b>Shortcuts:</b> Space=Play/Stop, B=Bypass, A=A/B Compare, "
            "Ctrl+S=Save Preset, Ctrl+1-3=Tabs, Ctrl+Up/Down=Volume</p>"
            "<p>Powered by ONNX Runtime + DirectML on Snapdragon X NPU</p>",
        )

    def update_npu_status(self, info: dict) -> None:
        """Update NPU status display from app controller."""
        if info.get("is_npu"):
            self._npu_status_label.setText("NPU: Active")
            self._npu_status_label.setStyleSheet(
                "color: #00B894; border-color: #00B894;"
            )
        else:
            self._npu_status_label.setText(
                f"NPU: {info.get('provider', 'N/A')}"
            )

    def _restore_settings(self) -> None:
        """Restore saved window state and settings."""
        s = self._settings_mgr.settings
        if s.window_maximized:
            self.showMaximized()
        else:
            self.setGeometry(s.window_x, s.window_y, s.window_width, s.window_height)
        self._tabs.setCurrentIndex(s.active_tab)
        if s.always_on_top:
            self._always_on_top.setChecked(True)
            self._toggle_always_on_top(True)
        if s.last_preset != "Default":
            preset = self._preset_manager.get_preset(s.last_preset)
            if preset:
                self._preset_selector._combo.setCurrentText(s.last_preset)

    def _save_settings(self) -> None:
        """Save current window state and settings."""
        s = self._settings_mgr.settings
        s.window_maximized = self.isMaximized()
        if not s.window_maximized:
            geo = self.geometry()
            s.window_x = geo.x()
            s.window_y = geo.y()
            s.window_width = geo.width()
            s.window_height = geo.height()
        s.last_preset = self._preset_manager.current_name
        s.active_tab = self._tabs.currentIndex()
        s.always_on_top = self._always_on_top.isChecked()
        if self._app:
            s.master_volume = self._app.processor.master_gain
            s.bypass_enabled = self._app.processor.bypass
        self._settings_mgr.save()

    def closeEvent(self, event) -> None:
        self._save_settings()
        if self._app:
            self._app.shutdown()
        event.accept()
