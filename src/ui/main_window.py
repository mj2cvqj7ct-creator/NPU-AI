"""
Main Application Window (v3 - Modern & Refined).

Premium dark-themed interface with glassmorphism styling,
real-time spectral visualizations, and comprehensive
audio processing controls.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QAction, QCloseEvent, QFont
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

from src.audio.capture import invalidate_default_render_endpoint_cache
from src.audio.device_notify import NotificationHandle, start_render_endpoint_notifier
from src.ui.styles import DARK_THEME
from src.ui.widgets.controls import (
    DepthControlPanel,
    EnhancerControlPanel,
    MasterControlBar,
    NoiseReducerControlPanel,
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

        self.setWindowTitle("NPU オーディオエンハンサー — Snapdragon X Elite")
        self.setMinimumSize(1200, 800)
        self.resize(1500, 950)

        self.setStyleSheet(DARK_THEME)
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        self._setup_timers()
        self._connect_signals()
        self._mm_notify: NotificationHandle | None = None
        self._mm_pending_reasons: set[str] = set()
        self._mm_debounce_timer = QTimer(self)
        self._mm_debounce_timer.setSingleShot(True)
        self._mm_debounce_timer.setInterval(350)
        self._mm_debounce_timer.timeout.connect(self._flush_mm_resync)
        self._rate_defer_timer = QTimer(self)
        self._rate_defer_timer.setSingleShot(True)
        self._rate_defer_timer.setInterval(150)
        self._rate_defer_timer.timeout.connect(self._update_pipeline_rate_labels)
        self._stats_ticks = 0
        self._start_mm_notification()
        QTimer.singleShot(0, self._on_startup_idle_probe)

    def _status_message(self, message: str, timeout: int = 0) -> None:
        bar = self.statusBar()
        if bar is not None:
            bar.showMessage(message, timeout)

    @pyqtSlot()
    def _on_startup_idle_probe(self) -> None:
        """Prime Pipeline/Rates from Windows default mix before first Start."""
        if not self._app or self._master_bar.is_playing:
            return
        self._app.refresh_loopback_probe_idle()
        self._update_pipeline_rate_labels()

    def _start_mm_notification(self) -> None:
        """Register MMDevice endpoint notifications (Windows)."""

        def schedule(reason: str) -> None:
            QTimer.singleShot(0, lambda r=reason: self._arm_mm_debounce(r))

        self._mm_notify = start_render_endpoint_notifier(schedule)

    def _arm_mm_debounce(self, reason: str) -> None:
        invalidate_default_render_endpoint_cache()
        self._mm_pending_reasons.add(reason)
        self._mm_debounce_timer.stop()
        self._mm_debounce_timer.start()

    @pyqtSlot()
    def _flush_mm_resync(self) -> None:
        reasons = self._mm_pending_reasons.copy()
        self._mm_pending_reasons.clear()
        invalidate_default_render_endpoint_cache()
        if self._app:
            self._app.dac_controller.refresh_detection()
        if not self._app:
            return
        changed = False
        if self._master_bar.is_playing:
            changed = self._app.sync_render_endpoint_if_changed()
            if changed:
                label = ", ".join(sorted(reasons)) if reasons else "device"
                self._status_message(
                    f"オーディオデバイスを更新しました（{label}）— キャプチャを再同期しました",
                    5000,
                )
                self._refresh_rates_after_capture_restart()
            else:
                self._update_pipeline_rate_labels()
        else:
            self._update_pipeline_rate_labels()

    def _update_pipeline_rate_labels(self) -> None:
        """Refresh loopback vs output in analysis row and DAC Pipeline line."""
        if not self._app:
            return
        ri = self._app.pipeline_rate_info()
        self._dac_panel.update_pipeline_rates(ri)
        lb = int(ri["loopback_hz"])
        out = int(ri["output_hz"])
        if self._master_bar.is_playing:
            if ri["resampling"]:
                self._rate_label.setText(f"レート: {lb}→{out} Hz")
                self._rate_label.setStyleSheet("color: #FDCB6E;")
            else:
                self._rate_label.setText(f"レート: {lb} Hz")
                self._rate_label.setStyleSheet("color: #55EFC4;")
        else:
            if ri["resampling"]:
                self._rate_label.setText(f"レート: {lb}→{out}（待機）")
                self._rate_label.setStyleSheet("color: #8B949E;")
            else:
                self._rate_label.setText(f"レート: {lb} Hz（待機）")
                self._rate_label.setStyleSheet("color: #8B949E;")

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
        """Create the application header with branding."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)

        title = QLabel("NPU オーディオエンハンサー")
        title.setObjectName("headerTitle")
        title_font = self.font()
        title_font.setPointSize(22)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #A29BFE; letter-spacing: 1.5px;")

        subtitle = QLabel(
            "Snapdragon X Elite NPU  |  リアルタイム AI 処理  |  "
            "Spotify / Apple Music / YouTube Music"
        )
        subtitle.setObjectName("statusLabel")

        npu_status = QLabel("NPU: …")
        npu_status.setObjectName("npuBadge")
        self._npu_status_label = npu_status

        dac_badge = QLabel("出力: …")
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

        viz_label = QLabel("オーディオ解析")
        viz_label.setObjectName("sectionTitle")
        layout.addWidget(viz_label)

        self._spectrum = SpectrumVisualizer()
        self._spectrum.setMinimumHeight(200)
        layout.addWidget(self._spectrum)

        self._waveform = WaveformVisualizer()
        self._waveform.setMinimumHeight(120)
        layout.addWidget(self._waveform)

        stems_label = QLabel("ソース分離")
        stems_label.setObjectName("sectionTitle")
        layout.addWidget(stems_label)

        self._stem_meters = StemLevelMeters()
        layout.addWidget(self._stem_meters)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        self._latency_label = QLabel("遅延: -- ms")
        self._latency_label.setObjectName("valueLabel")
        self._cpu_label = QLabel("CPU: -- %")
        self._cpu_label.setObjectName("valueLabel")
        self._buffer_label = QLabel("バッファ: OK")
        self._buffer_label.setObjectName("valueLabel")
        self._rate_label = QLabel("レート: —")
        self._rate_label.setObjectName("valueLabel")
        self._rate_label.setToolTip(
            "ループバックのキャプチャレートと DAC／出力のサンプルレートです。"
            "矢印（→）はパイプライン内のポリフェーズリサンプルを表します。"
            "待機中は、Windows の既定再生ミックスを約 1.5 秒キャッシュで表示します。",
        )
        self._npu_load_label = QLabel("NPU: --")
        self._npu_load_label.setObjectName("valueLabel")
        stats_row.addWidget(self._latency_label)
        stats_row.addWidget(self._cpu_label)
        stats_row.addWidget(self._buffer_label)
        stats_row.addWidget(self._rate_label)
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
        tabs.addTab(effects_tab, "エフェクト")

        dac_tab = self._create_dac_tab()
        tabs.addTab(dac_tab, "SABAJ DAC")

        rec_tab = self._create_recommender_tab()
        tabs.addTab(rec_tab, "AI おすすめ")

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
        self._noise_panel = NoiseReducerControlPanel()
        self._enhancer_panel = EnhancerControlPanel()
        self._depth_panel = DepthControlPanel()

        layout.addWidget(self._spatial_panel)
        layout.addWidget(self._separation_panel)
        layout.addWidget(self._noise_panel)
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
        assert menu_bar is not None

        file_menu = menu_bar.addMenu("ファイル")
        assert file_menu is not None
        exit_action = QAction("終了", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("表示")
        assert view_menu is not None
        self._always_on_top = QAction("常に手前に表示", self)
        self._always_on_top.setCheckable(True)
        self._always_on_top.triggered.connect(self._toggle_always_on_top)
        view_menu.addAction(self._always_on_top)

        help_menu = menu_bar.addMenu("ヘルプ")
        assert help_menu is not None
        about_action = QAction("バージョン情報", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        audio_menu = menu_bar.addMenu("オーディオ")
        assert audio_menu is not None
        resync_action = QAction("ループバックを再同期…", self)
        resync_action.setShortcut("Ctrl+Shift+R")
        resync_action.setStatusTip(
            "Windows のミックスを再取得します。処理中はキャプチャを再起動し、"
            "停止中はパイプライン／レート表示のみ更新します。",
        )
        resync_action.triggered.connect(self._on_resync_loopback)
        audio_menu.addAction(resync_action)

    def _setup_status_bar(self) -> None:
        """Setup status bar."""
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("準備完了 — 音楽を再生して「開始」を押してください")

    def _setup_timers(self) -> None:
        """Setup UI update timers."""
        self._viz_timer = QTimer(self)
        self._viz_timer.timeout.connect(self._update_visualizations)
        self._viz_timer.start(33)  # ~30fps

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(500)

        self._endpoint_timer = QTimer(self)
        self._endpoint_timer.timeout.connect(self._check_render_endpoint)
        self._endpoint_timer.start(5000)

    def _connect_signals(self) -> None:
        """Connect UI signals to application controller."""
        if not self._app:
            return

        self._master_bar.play_toggled.connect(self._on_play_toggled)
        self._master_bar.bypass_toggled.connect(self._on_bypass_toggled)
        self._master_bar.volume_changed.connect(self._on_volume_changed)

        self._spatial_panel.params_changed.connect(self._on_spatial_changed)
        self._separation_panel.params_changed.connect(self._on_separation_changed)
        self._noise_panel.params_changed.connect(self._on_noise_reducer_changed)
        self._enhancer_panel.params_changed.connect(self._on_enhancer_changed)
        self._depth_panel.params_changed.connect(self._on_depth_changed)

        self._dac_panel.optimize_requested.connect(self._on_optimize_dac)
        self._dac_panel.config_changed.connect(self._on_dac_config_changed)
        self._dac_panel.loopback_resync_requested.connect(self._on_resync_loopback)

        self._recommender_panel.track_liked.connect(self._on_track_liked)
        self._recommender_panel.track_skipped.connect(self._on_track_skipped)

        self._sync_processor_stage_flags()

    def _sync_processor_stage_flags(self) -> None:
        """Align pipeline stage enables with current panel state (startup / consistency)."""
        if not self._app:
            return
        proc = self._app.processor
        proc.config.enable_separation = bool(
            self._separation_panel.get_params().get("enabled", True),
        )
        proc.config.enable_enhancement = bool(
            self._enhancer_panel.get_params().get("enabled", True),
        )
        proc.config.enable_noise_reduction = bool(
            self._noise_panel.get_params().get("enabled", False),
        )
        proc.config.enable_spatial = bool(
            self._spatial_panel.get_params().get("enabled", True),
        )
        proc.config.enable_depth = bool(
            self._depth_panel.get_params().get("enabled", True),
        )

    def _schedule_deferred_rate_refresh(self) -> None:
        """Re-run rate labels after WASAPI mix rate is set (single-shot, cancellable)."""
        self._rate_defer_timer.stop()
        self._rate_defer_timer.start()

    def _refresh_rates_after_capture_restart(self) -> None:
        """After capture stop/start, refresh labels now and once mix rate is set."""
        self._update_pipeline_rate_labels()
        if self._master_bar.is_playing:
            self._schedule_deferred_rate_refresh()

    @pyqtSlot(bool)
    def _on_play_toggled(self, playing: bool) -> None:
        if self._app:
            if playing:
                self._app.start_processing()
                self._master_bar.set_status("処理中…")
                self._status_message("オーディオ処理を開始しました")
                self._refresh_rates_after_capture_restart()
            else:
                self._rate_defer_timer.stop()
                self._app.stop_processing()
                self._master_bar.set_status("停止")
                self._status_message("オーディオ処理を停止しました")
                self._update_pipeline_rate_labels()

    @pyqtSlot()
    def _on_resync_loopback(self) -> None:
        if not self._app:
            return
        if not self._master_bar.is_playing:
            self._app.refresh_loopback_probe_idle()
            self._update_pipeline_rate_labels()
            self._status_message(
                "ループバックを再取得しました（待機）— パイプライン／レートを更新しました",
                4000,
            )
            return
        self._app.force_resync_loopback_capture()
        self._status_message(
            "ループバックを手動で再同期しました",
            4000,
        )
        self._refresh_rates_after_capture_restart()

    @pyqtSlot(bool)
    def _on_bypass_toggled(self, bypassed: bool) -> None:
        if self._app:
            self._app.processor.bypass = bypassed

    @pyqtSlot(float)
    def _on_volume_changed(self, volume: float) -> None:
        if self._app:
            self._app.processor.master_gain = volume

    @pyqtSlot(dict)
    def _on_spatial_changed(self, params: dict[str, Any]) -> None:
        if self._app:
            p = dict(params)
            self._app.processor.config.enable_spatial = p.get("enabled", True)
            spatial = self._app.processor.spatial
            spatial.enabled = p.pop("enabled", True)
            spatial.update_parameters(**p)

    @pyqtSlot(dict)
    def _on_separation_changed(self, params: dict[str, Any]) -> None:
        if self._app:
            self._app.processor.config.enable_separation = params.get("enabled", True)
            sep = self._app.processor.separator
            sep.config.enabled = params.get("enabled", True)
            sep.config.vocal_boost = params.get("vocal_boost", 0.3)
            sep.config.instrument_clarity = params.get("instrument_clarity", 0.5)
            sep.config.bass_enhance = params.get("bass_enhance", 0.2)
            sep.config.drum_punch = params.get("drum_punch", 0.2)

    @pyqtSlot(dict)
    def _on_depth_changed(self, params: dict[str, Any]) -> None:
        if self._app:
            p = dict(params)
            self._app.processor.config.enable_depth = p.get("enabled", True)
            depth = self._app.processor.depth
            depth.enabled = p.pop("enabled", True)
            depth.update_parameters(**p)

    @pyqtSlot(dict)
    def _on_noise_reducer_changed(self, params: dict[str, Any]) -> None:
        if self._app:
            self._app.processor.config.enable_noise_reduction = params.get(
                "enabled", False,
            )
            nr = self._app.processor.noise_reducer
            nr.enabled = params.get("enabled", False)
            nr.update_parameters(**{
                k: v for k, v in params.items() if k != "enabled"
            })

    @pyqtSlot(dict)
    def _on_enhancer_changed(self, params: dict[str, Any]) -> None:
        if self._app:
            self._app.processor.config.enable_enhancement = params.get(
                "enabled", True,
            )
            self._app.processor.enhancer.update_parameters(**{
                k: v for k, v in params.items() if k != "enabled"
            })
            self._app.processor.enhancer.enabled = params.get("enabled", True)

    @pyqtSlot()
    def _on_optimize_dac(self) -> None:
        if self._app:
            settings = self._app.dac_controller.optimize_for_npu()
            self._dac_panel.show_optimization_result(settings)
            self._app.apply_dac_settings_from_ui(self._dac_panel.get_config())
            self._refresh_rates_after_capture_restart()

    @pyqtSlot(dict)
    def _on_dac_config_changed(self, config: dict[str, Any]) -> None:
        if self._app:
            self._app.apply_dac_settings_from_ui(config)
            self._refresh_rates_after_capture_restart()

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

    def _check_render_endpoint(self) -> None:
        if not self._app or not self._master_bar.is_playing:
            return
        if self._app.sync_render_endpoint_if_changed():
            self._status_message(
                "既定の再生デバイスまたは形式が変わりました — キャプチャを再同期しました",
                4000,
            )
            self._refresh_rates_after_capture_restart()

    def _update_stats(self) -> None:
        """Update processing statistics display."""
        self._stats_ticks += 1
        if not self._app:
            self._npu_status_label.setText("NPU: エンジン未初期化")
            self._npu_status_label.setStyleSheet(
                "color: #E17055; border-color: #E17055;",
            )
            self._dac_badge.setText("DAC: —")
            self._dac_badge.setStyleSheet("color: #8B949E;")
            return

        if self._stats_ticks % 10 == 0:
            self._app.dac_controller.refresh_detection()

        try:
            stats = self._app.processor.stats
            self._latency_label.setText(f"遅延: {stats.processing_time_ms:.1f} ms")

            try:
                import psutil

                cpu = psutil.cpu_percent(interval=None)
                self._cpu_label.setText(f"CPU: {cpu:.0f}%")
            except ImportError:
                pass

            npu_info = self._app.npu_engine.get_device_info()
            provider = npu_info.get("provider", "N/A")
            if npu_info.get("is_npu"):
                self._npu_status_label.setText(f"NPU: 有効（{provider}）")
                self._npu_status_label.setStyleSheet(
                    "color: #00B894; border-color: #00B894;",
                )
            elif provider != "None":
                self._npu_status_label.setText(f"NPU: {provider}")
                self._npu_status_label.setStyleSheet(
                    "color: #FDCB6E; border-color: #FDCB6E;",
                )
            else:
                self._npu_status_label.setText("NPU: DSP モード（ONNX なし）")
                self._npu_status_label.setStyleSheet(
                    "color: #8B949E; border-color: #8B949E;",
                )

            npu_infer_ms = float(npu_info.get("avg_inference_ms", 0.0))
            if npu_infer_ms > 0:
                self._npu_load_label.setText(f"推論: 平均 {npu_infer_ms:.2f} ms")
            else:
                self._npu_load_label.setText("推論: —")

            lines = [
                f"プロバイダ: {provider}",
                f"読み込んだモデル数: {npu_info.get('models_loaded', 0)}",
            ]
            mstats = npu_info.get("model_stats") or {}
            for name in sorted(mstats.keys()):
                row = mstats[name]
                cnt = int(row.get("infer_count", 0))
                avg = float(row.get("avg_ms", 0.0))
                if cnt > 0:
                    lines.append(f"{name}: {cnt} 回、平均 {avg:.2f} ms")
                else:
                    lines.append(f"{name}: —")
            self._npu_load_label.setToolTip("\n".join(lines))
            self._npu_status_label.setToolTip(
                "AI エフェクト用の ONNX Runtime 実行プロバイダです。"
                "「推論」にマウスを載せるとモデル別の統計が表示されます。",
            )

            dac_status = self._app.dac_controller.get_status_info()
            self._dac_panel.update_status(dac_status)

            out_stats = self._app.output_stats
            out_u = int(out_stats.get("underrun_count", 0))
            qsz = int(out_stats.get("queue_size", 0))
            buf_warn = out_u > 0 or qsz > 48
            self._buffer_label.setText(
                f"バッファ: {'注意' if buf_warn else 'OK'}（q={qsz}）",
            )
            if buf_warn:
                self._buffer_label.setStyleSheet("color: #FDCB6E;")
            else:
                self._buffer_label.setStyleSheet("color: #8B949E;")

            self._update_pipeline_rate_labels()

            dac_name = dac_status.get("device_name", "N/A")
            dac_st = dac_status.get("status", "disconnected")
            if dac_st in ("connected", "streaming"):
                self._dac_badge.setText(f"出力: {dac_name}")
                self._dac_badge.setStyleSheet("color: #00B894;")
            else:
                self._dac_badge.setText("出力: 未検出")
                self._dac_badge.setStyleSheet("color: #8B949E;")

            profile = self._app.recommender.preference_profile
            self._recommender_panel.update_preferences(profile)
        except Exception:
            logger.exception("Stats UI update failed; partial refresh next tick")
            self._npu_status_label.setText("NPU: 表示エラー（ログ参照）")
            self._npu_status_label.setStyleSheet(
                "color: #E17055; border-color: #E17055;",
            )

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
            "NPU オーディオエンハンサーについて",
            "<h2>NPU オーディオエンハンサー v3.0</h2>"
            "<p>ARM64 Snapdragon X Elite の NPU でリアルタイムに音質を強化します。</p>"
            "<p>主な機能:</p>"
            "<ul>"
            "<li>位相を考慮したソース分離（Wiener フィルタ・HPSS）</li>"
            "<li>512 タップ HRTF（耳介ノッチ・外耳道共鳴モデル）</li>"
            "<li>6 バンドのホログラフィックサウンドステージ（オールパス拡散）</li>"
            "<li>12 ライン FDN リバーブ（変調ディレイ）</li>"
            "<li>テープ風飽和ハーモニックエキサイターとトランジェント整形</li>"
            "<li>SABAJ A20D ES9038PRO DAC とトリプルバッファ NPU ストリーミング</li>"
            "<li>Adam 風の深層学習おすすめ</li>"
            "<li>Spotify / Apple Music / YouTube Music 向け</li>"
            "</ul>"
            "<p>ONNX Runtime + DirectML（Snapdragon X NPU）を利用します。</p>",
        )

    def update_npu_status(self, info: dict[str, Any]) -> None:
        """Update NPU status display from app controller."""
        prov = info.get("provider", "N/A")
        if info.get("is_npu"):
            self._npu_status_label.setText(f"NPU: 有効（{prov}）")
            self._npu_status_label.setStyleSheet(
                "color: #00B894; border-color: #00B894;",
            )
        elif prov != "None":
            self._npu_status_label.setText(f"NPU: {prov}")
            self._npu_status_label.setStyleSheet(
                "color: #FDCB6E; border-color: #FDCB6E;",
            )
        else:
            self._npu_status_label.setText("NPU: DSP モード（ONNX なし）")
            self._npu_status_label.setStyleSheet(
                "color: #8B949E; border-color: #8B949E;",
            )

    def closeEvent(self, event: QCloseEvent | None) -> None:
        if event is None:
            return
        self._mm_debounce_timer.stop()
        self._rate_defer_timer.stop()
        self._mm_pending_reasons.clear()
        if self._mm_notify is not None:
            self._mm_notify.close()
            self._mm_notify = None
        if self._app:
            self._app.shutdown()
        event.accept()
