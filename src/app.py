"""
Main Application Controller.

Orchestrates all components: audio capture, DSP processing, NPU engine,
DAC output, and recommendation engine into a unified real-time pipeline.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from math import gcd

import numpy as np
from scipy import signal

from src.audio.capture import (
    WASAPICapture,
    probe_default_render_endpoint_state,
    probe_default_render_mix_sample_rate,
)
from src.audio.output import AudioOutput, OutputConfig
from src.audio.processor import AudioProcessor
from src.dac.xmos_controller import XMOSController
from src.npu.engine import NPUEngine, NPUConfig
from src.recommender.engine import RecommendationEngine

logger = logging.getLogger(__name__)


class AudioEnhancerApp:
    """Main application controller coordinating all subsystems.

    Pipeline:
        Audio Source → WASAPI Capture → NPU-accelerated DSP → DAC Output
                                              ↕
                                    Recommendation Engine
    """

    def __init__(self):
        logger.info("Initializing NPU Audio Enhancer...")

        from src.npu.models import default_model_dir

        model_dir = default_model_dir()
        os.makedirs(model_dir, exist_ok=True)
        self._npu_engine = NPUEngine(NPUConfig(model_dir=model_dir))
        self._npu_engine.load_default_models()
        self._processor = AudioProcessor()
        self._capture = WASAPICapture()
        self._dac_controller = XMOSController()

        self._output = AudioOutput(self._build_output_config())
        self._recommender = RecommendationEngine()

        self._processing_thread: threading.Thread | None = None
        self._is_running = False
        self._latest_audio: np.ndarray | None = None
        self._latest_viz_data: dict | None = None
        self._lock = threading.Lock()
        self._last_output_underrun_count = 0
        self._render_signature: str | None = None
        self._endpoint_sync_lock = threading.Lock()

        self._connect_components()
        logger.info("NPU Audio Enhancer initialized")

    def _connect_components(self) -> None:
        """Wire up components together."""
        self._processor.set_npu_engine(self._npu_engine)
        self._recommender.set_npu_engine(self._npu_engine)

        if self._dac_controller.is_connected:
            settings = self._dac_controller.optimize_for_npu()
            logger.info("DAC optimized for NPU: %s", settings)
        self._sync_output_from_dac()
        self._sync_pipeline_sample_rates()
        self._sync_render_signature()

    def _render_sig_from_state(
        self, st: tuple[str, int, int, int],
    ) -> str:
        dev_id, rate, ch, bits = st
        return f"{dev_id}|{rate}|{ch}|{bits}"

    def _sync_render_signature(self) -> None:
        """Snapshot default render endpoint for change detection."""
        st = probe_default_render_endpoint_state()
        if st:
            self._render_signature = self._render_sig_from_state(st)

    def sync_render_endpoint_if_changed(self) -> bool:
        """If default playback device or mix format changed, resync capture.

        Call from UI timer while processing. Returns True if capture restarted.
        """
        with self._endpoint_sync_lock:
            st = probe_default_render_endpoint_state()
            if st is None:
                return False
            sig = self._render_sig_from_state(st)
            if sig == self._render_signature:
                return False
            logger.info(
                "Default render endpoint or mix format changed; restarting capture",
            )
            self._render_signature = sig
            self._sync_pipeline_sample_rates()
            if self._capture.is_capturing:
                self._capture.stop()
                self._capture.start()
            return True

    def force_resync_loopback_capture(self) -> None:
        """Refresh default-render snapshot, pipeline timing, and restart capture.

        Use when Windows mix format changes without updating device id (rare)
        or after external driver tweaks.
        """
        with self._endpoint_sync_lock:
            st = probe_default_render_endpoint_state()
            if st:
                self._render_signature = self._render_sig_from_state(st)
            else:
                self._render_signature = None
            self._sync_pipeline_sample_rates()
            if self._capture.is_capturing:
                self._capture.stop()
                self._capture.start()

    def _sync_pipeline_sample_rates(self) -> None:
        """Align capture buffer and DSP sample rate with DAC output."""
        out_sr = self._dac_controller.config.sample_rate.value
        self._processor.set_sample_rate(out_sr)
        mix_sr = probe_default_render_mix_sample_rate()
        cap_sr = mix_sr if mix_sr else out_sr
        buf_ms = self._dac_controller.config.buffer_size_ms
        self._capture.config.format.sample_rate = cap_sr
        self._capture.config.buffer_size_ms = buf_ms
        if mix_sr and mix_sr != out_sr:
            logger.info(
                "Capture at %d Hz, output/DSP at %d Hz (polyphase resample)",
                cap_sr,
                out_sr,
            )

    def _build_output_config(self) -> OutputConfig:
        c = self._dac_controller.config
        return OutputConfig(
            device_name=(
                self._dac_controller.info.name
                if self._dac_controller.is_connected
                else None
            ),
            sample_rate=c.sample_rate.value,
            channels=2,
            bit_depth=c.bit_depth.value,
            buffer_size_ms=c.buffer_size_ms,
            exclusive_mode=c.exclusive_mode,
        )

    def _sync_output_from_dac(self) -> None:
        """Apply XMOS/DAC buffer and device settings to the playback stream."""
        self._output.apply_config(self._build_output_config())

    def apply_dac_settings_from_ui(self, ui: dict) -> None:
        """Apply DAC panel values (rates, buffers, exclusive) and sync output."""
        from src.dac.xmos_controller import (
            BitDepth,
            DACConfig,
            DACFilter,
            SampleRate,
        )

        sr_val = int(ui.get("sample_rate", 48000))
        sample_rate = next(
            (s for s in SampleRate if s.value == sr_val),
            SampleRate.SR_48000,
        )
        bd_val = int(ui.get("bit_depth", 32))
        bit_depth = next(
            (b for b in BitDepth if b.value == bd_val),
            BitDepth.BIT_32,
        )
        filt_raw = ui.get("dac_filter", DACFilter.SLOW_MINIMUM.value)
        dac_filter = next(
            (f for f in DACFilter if f.value == filt_raw),
            DACFilter.SLOW_MINIMUM,
        )
        self._dac_controller.configure(
            DACConfig(
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                buffer_size_ms=int(ui.get("buffer_size_ms", 10)),
                latency_ms=int(ui.get("latency_ms", 5)),
                exclusive_mode=bool(ui.get("exclusive_mode", True)),
                triple_buffer=bool(ui.get("triple_buffer", True)),
                dac_filter=dac_filter,
            ),
        )
        self._sync_output_from_dac()
        self._sync_pipeline_sample_rates()
        if self._capture.is_capturing:
            self._capture.stop()
            self._capture.start()

    @staticmethod
    def _resample_audio(
        audio: np.ndarray, src_sr: int, dst_sr: int,
    ) -> np.ndarray:
        if src_sr == dst_sr or audio.shape[0] == 0:
            return audio
        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])
        g = gcd(int(src_sr), int(dst_sr))
        up = dst_sr // g
        down = src_sr // g
        n_out = max(1, int(round(audio.shape[0] * dst_sr / src_sr)))
        out = np.zeros((n_out, audio.shape[1]), dtype=np.float64)
        for ch in range(audio.shape[1]):
            out[:, ch] = signal.resample_poly(
                audio[:, ch].astype(np.float64), up, down,
            )[:n_out]
        return out.astype(np.float32)

    @property
    def processor(self) -> AudioProcessor:
        return self._processor

    @property
    def npu_engine(self) -> NPUEngine:
        return self._npu_engine

    @property
    def dac_controller(self) -> XMOSController:
        return self._dac_controller

    @property
    def recommender(self) -> RecommendationEngine:
        return self._recommender

    @property
    def output_stats(self) -> dict:
        return self._output.stats

    def start_processing(self) -> None:
        """Start the real-time audio processing pipeline."""
        if self._is_running:
            return

        self._is_running = True
        self._last_output_underrun_count = self._output.stats.get(
            "underrun_count", 0,
        )

        self._sync_pipeline_sample_rates()
        self._sync_render_signature()
        self._capture.start()
        self._output.start()

        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
            name="AudioProcessing",
        )
        self._processing_thread.start()

        logger.info("Audio processing pipeline started")

    def stop_processing(self) -> None:
        """Stop the audio processing pipeline."""
        self._is_running = False

        if self._processing_thread:
            self._processing_thread.join(timeout=2.0)
            self._processing_thread = None

        self._capture.stop()
        self._output.stop()
        self._last_output_underrun_count = 0

        logger.info("Audio processing pipeline stopped")

    def _processing_loop(self) -> None:
        """Main real-time processing loop."""
        frame_count = 0
        recommend_interval = 500

        last_out_sr = -1

        while self._is_running:
            audio = self._capture.get_audio(timeout=0.05)
            if audio is None:
                continue

            try:
                out_sr = self._dac_controller.config.sample_rate.value
                if out_sr != last_out_sr:
                    self._processor.set_sample_rate(out_sr)
                    last_out_sr = out_sr

                cap_sr = self._capture.effective_sample_rate
                if cap_sr != out_sr:
                    audio = self._resample_audio(audio, cap_sr, out_sr)

                processed = self._processor.process(audio)

                self._output.write(processed)

                proc_ms = self._processor.stats.processing_time_ms
                self._dac_controller.report_npu_processing_time(proc_ms)

                out_stats = self._output.stats
                u = int(out_stats.get("underrun_count", 0))
                if u > self._last_output_underrun_count:
                    for _ in range(u - self._last_output_underrun_count):
                        self._dac_controller.report_buffer_underrun()
                    self._last_output_underrun_count = u

                with self._lock:
                    self._latest_audio = processed
                    self._latest_viz_data = self._processor.get_visualization_data(
                        processed,
                    )

                frame_count += 1
                if frame_count % recommend_interval == 0:
                    self._update_recommendations(audio)

            except Exception as e:
                logger.error("Processing error: %s", e)
                time.sleep(0.001)

    def _update_recommendations(self, audio: np.ndarray) -> None:
        """Update recommendation engine with current audio features."""
        try:
            sr = self._dac_controller.config.sample_rate.value
            features = self._recommender.analyze_audio(audio, sample_rate=sr)
            self._recommender.update_preferences(features, liked=True)
        except Exception as e:
            logger.debug("Recommendation update error: %s", e)

    def get_visualization_data(self) -> dict | None:
        """Get latest visualization data for the UI."""
        with self._lock:
            return self._latest_viz_data

    def on_track_liked(self) -> None:
        """Handle user liking the current track."""
        with self._lock:
            audio = self._latest_audio

        if audio is not None:
            sr = self._dac_controller.config.sample_rate.value
            features = self._recommender.analyze_audio(audio, sample_rate=sr)
            self._recommender.update_preferences(features, liked=True)

    def on_track_skipped(self) -> None:
        """Handle user skipping/disliking the current track."""
        with self._lock:
            audio = self._latest_audio

        if audio is not None:
            sr = self._dac_controller.config.sample_rate.value
            features = self._recommender.analyze_audio(audio, sample_rate=sr)
            self._recommender.update_preferences(features, liked=False)

    def shutdown(self) -> None:
        """Shutdown all components gracefully."""
        logger.info("Shutting down NPU Audio Enhancer...")
        self.stop_processing()
        self._npu_engine.shutdown()
        logger.info("NPU Audio Enhancer shut down")
