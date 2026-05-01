"""
Main Application Window.

Assembles all UI components into a modern, tabbed layout with
real-time visualizations and comprehensive audio control panels.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QFont
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

from src.ui.styles import DARK_THEME
from src.ui.widgets.controls import (
    DepthControlPanel,
    EnhancerControlPanel,
    MasterControlBar,
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

        self.setWindowTitle("NPU Audio Enhancer - Snapdragon X")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        self.setStyleSheet(DARK_THEME)
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        self._setup_timers()
        self._connect_signals()

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

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self._create_visualization_panel()
        splitter.addWidget(left_panel)

        right_panel = self._create_control_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([700, 500])
        main_layout.addWidget(splitter, 1)

    def _create_header(self) -> QWidget:
        """Create the application header."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 8, 16, 8)

        title = QLabel("NPU Audio Enhancer")
        title_font = QFont("Segoe UI", 20, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #6C5CE7; letter-spacing: 1px;")

        subtitle = QLabel("Snapdragon X NPU  |  Real-time AI Audio Processing")
        subtitle.setObjectName("statusLabel")

        npu_status = QLabel("NPU: Initializing...")
        npu_status.setObjectName("valueLabel")
        self._npu_status_label = npu_status

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(npu_status)

        return header

    def _create_visualization_panel(self) -> QWidget:
        """Create the left panel with audio visualizations."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        viz_label = QLabel("Audio Analysis")
        viz_label.setObjectName("sectionTitle")
        layout.addWidget(viz_label)

        self._spectrum = SpectrumVisualizer()
        layout.addWidget(self._spectrum)

        self._waveform = WaveformVisualizer()
        layout.addWidget(self._waveform)

        stems_label = QLabel("Source Separation")
        stems_label.setObjectName("sectionTitle")
        layout.addWidget(stems_label)

        self._stem_meters = StemLevelMeters()
        layout.addWidget(self._stem_meters)

        stats_row = QHBoxLayout()
        self._latency_label = QLabel("Latency: -- ms")
        self._latency_label.setObjectName("valueLabel")
        self._cpu_label = QLabel("CPU: --%")
        self._cpu_label.setObjectName("valueLabel")
        self._buffer_label = QLabel("Buffer: OK")
        self._buffer_label.setObjectName("valueLabel")
        stats_row.addWidget(self._latency_label)
        stats_row.addWidget(self._cpu_label)
        stats_row.addWidget(self._buffer_label)
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
        tabs.addTab(dac_tab, "DAC")

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
            self._npu_status_label.setStyleSheet("color: #00B894;")
        elif provider != "None":
            self._npu_status_label.setText(f"NPU: {provider}")
            self._npu_status_label.setStyleSheet("color: #FDCB6E;")
        else:
            self._npu_status_label.setText("NPU: DSP Mode")
            self._npu_status_label.setStyleSheet("color: #8B949E;")

        dac_status = self._app.dac_controller.get_status_info()
        self._dac_panel.update_status(dac_status)

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
            "<h2>NPU Audio Enhancer v1.0</h2>"
            "<p>ARM64 Snapdragon X NPU-accelerated real-time audio enhancement</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>WASAPI Loopback audio capture</li>"
            "<li>AI source separation (Vocals/Drums/Bass/Other)</li>"
            "<li>Spatial audio & holographic soundstage</li>"
            "<li>SABAJ A20D XMOS USB DAC integration</li>"
            "<li>Deep learning music recommendations</li>"
            "</ul>"
            "<p>Powered by ONNX Runtime + DirectML</p>",
        )

    def update_npu_status(self, info: dict) -> None:
        """Update NPU status display from app controller."""
        if info.get("is_npu"):
            self._npu_status_label.setText("NPU: Active")
            self._npu_status_label.setStyleSheet("color: #00B894;")
        else:
            self._npu_status_label.setText(f"NPU: {info.get('provider', 'N/A')}")

    def closeEvent(self, event) -> None:
        if self._app:
            self._app.shutdown()
        event.accept()
