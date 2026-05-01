"""
Main Application Controller.

Orchestrates all components: audio capture, DSP processing, NPU engine,
DAC output, and recommendation engine into a unified real-time pipeline.
"""

from __future__ import annotations

import logging
import threading
import time

import numpy as np

from src.audio.capture import WASAPICapture
from src.audio.output import AudioOutput, OutputConfig
from src.audio.processor import AudioProcessor
from src.dac.xmos_controller import XMOSController
from src.npu.engine import NPUEngine
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

        self._npu_engine = NPUEngine()
        self._processor = AudioProcessor()
        self._capture = WASAPICapture()
        self._dac_controller = XMOSController()

        output_config = OutputConfig(
            device_name=(
                self._dac_controller.info.name
                if self._dac_controller.is_connected
                else None
            ),
            sample_rate=48000,
            channels=2,
            buffer_size_ms=10,
            exclusive_mode=True,
        )
        self._output = AudioOutput(output_config)
        self._recommender = RecommendationEngine()

        self._processing_thread: threading.Thread | None = None
        self._is_running = False
        self._latest_audio: np.ndarray | None = None
        self._latest_viz_data: dict | None = None
        self._lock = threading.Lock()

        self._connect_components()
        logger.info("NPU Audio Enhancer initialized")

    def _connect_components(self) -> None:
        """Wire up components together."""
        self._processor.set_npu_engine(self._npu_engine)
        self._recommender.set_npu_engine(self._npu_engine)

        if self._dac_controller.is_connected:
            settings = self._dac_controller.optimize_for_npu()
            logger.info("DAC optimized for NPU: %s", settings)

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

    def start_processing(self) -> None:
        """Start the real-time audio processing pipeline."""
        if self._is_running:
            return

        self._is_running = True

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

        logger.info("Audio processing pipeline stopped")

    def _processing_loop(self) -> None:
        """Main real-time processing loop."""
        frame_count = 0
        recommend_interval = 500  # Analyze for recommendations every N frames

        while self._is_running:
            audio = self._capture.get_audio(timeout=0.05)
            if audio is None:
                continue

            try:
                processed = self._processor.process(audio)

                self._output.write(processed)

                # Report processing time to DAC for adaptive buffer optimization
                proc_ms = self._processor.stats.processing_time_ms
                self._dac_controller.report_npu_processing_time(proc_ms)

                with self._lock:
                    self._latest_audio = processed
                    self._latest_viz_data = self._processor.get_visualization_data(processed)

                frame_count += 1
                if frame_count % recommend_interval == 0:
                    self._update_recommendations(audio)

            except Exception as e:
                logger.error("Processing error: %s", e)
                time.sleep(0.001)

    def _update_recommendations(self, audio: np.ndarray) -> None:
        """Update recommendation engine with current audio features."""
        try:
            features = self._recommender.analyze_audio(audio)
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
            features = self._recommender.analyze_audio(audio)
            self._recommender.update_preferences(features, liked=True)

    def on_track_skipped(self) -> None:
        """Handle user skipping/disliking the current track."""
        with self._lock:
            audio = self._latest_audio

        if audio is not None:
            features = self._recommender.analyze_audio(audio)
            self._recommender.update_preferences(features, liked=False)

    def shutdown(self) -> None:
        """Shutdown all components gracefully."""
        logger.info("Shutting down NPU Audio Enhancer...")
        self.stop_processing()
        self._npu_engine.shutdown()
        logger.info("NPU Audio Enhancer shut down")
