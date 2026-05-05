"""
NPU Audio Enhancer - Main Entry Point.

Launches the PyQt6 application with NPU-accelerated real-time audio processing
for Spotify, Apple Music, and YouTube Music on ARM64 Snapdragon X.
"""

from __future__ import annotations

import contextlib
import logging
import os
import sys
from pathlib import Path


def _log_dir() -> Path:
    """Return a writable directory for the application log file.

    When running as a PyInstaller-frozen EXE, ``os.getcwd()`` may be
    ``C:\\Windows\\System32`` (if the user launched via a Start Menu
    shortcut), which is not writable. Prefer ``%LOCALAPPDATA%`` on
    Windows so the log is reliably created and easy for the user to
    locate.
    """
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            target = Path(local_appdata) / "NPU-Audio-Enhancer"
            try:
                target.mkdir(parents=True, exist_ok=True)
                return target
            except OSError:
                pass
    return Path(os.getcwd())


def setup_logging() -> Path:
    """Configure application logging and return the log file path."""
    log_path = _log_dir() / "npu_audio_enhancer.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(log_path), encoding="utf-8"),
        ],
    )
    return log_path


def main() -> int:
    """Application entry point."""
    log_path = setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting NPU Audio Enhancer v1.0")
    logger.info("Log file: %s", log_path)

    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        logger.error(
            "PyQt6 is required. Install with: pip install PyQt6>=6.6.0"
        )
        return 1

    with contextlib.suppress(Exception):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough,
        )

    app = QApplication(sys.argv)
    app.setApplicationName("NPU オーディオエンハンサー")
    app.setOrganizationName("NPU-AI")
    app.setApplicationVersion("1.0.0")

    font = QFont()
    if sys.platform == "win32":
        font.setFamilies(["Yu Gothic UI", "Meiryo UI", "Segoe UI", "sans-serif"])
    else:
        font.setFamilies(["Segoe UI", "Noto Sans CJK JP", "sans-serif"])
    font.setPointSize(10)
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

    return int(app.exec())


if __name__ == "__main__":
    sys.exit(main())
