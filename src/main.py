"""
NPU Audio Enhancer - Main Entry Point.

Launches the PyQt6 application with NPU-accelerated real-time audio processing
for Spotify, Apple Music, and YouTube Music on ARM64 Snapdragon X.
"""

from __future__ import annotations

import logging
import sys


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("npu_audio_enhancer.log", encoding="utf-8"),
        ],
    )


def main() -> int:
    """Application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting NPU Audio Enhancer v3.2.0")

    try:
        from PyQt6.QtGui import QFont
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        logger.error(
            "PyQt6 is required. Install with: pip install PyQt6>=6.6.0"
        )
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("NPU Audio Enhancer")
    app.setOrganizationName("NPU-AI")
    app.setApplicationVersion("3.2.0")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    logger.info("Initializing audio processing engine...")

    try:
        from src.app import AudioEnhancerApp

        app_controller = AudioEnhancerApp()
    except Exception as e:
        logger.error("Failed to initialize audio engine: %s", e)
        app_controller = None

    from src.ui.main_window import MainWindow

    window = MainWindow(app_controller)

    if app_controller:
        npu_info = app_controller.npu_engine.get_device_info()
        window.update_npu_status(npu_info)
        logger.info("NPU Status: %s", npu_info)

    if "--minimized" in sys.argv:
        window.showMinimized()
        logger.info("Application started minimized (auto-start)")
    else:
        window.show()
    logger.info("Application window ready")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
