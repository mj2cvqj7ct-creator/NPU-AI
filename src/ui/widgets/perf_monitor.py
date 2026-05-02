"""
NPU Performance Monitor Widget.

Displays real-time processing time graph, NPU utilization,
and benchmark results for audio pipeline performance analysis.
"""

from __future__ import annotations

from collections import deque

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProcessingTimeGraph(QWidget):
    """Real-time processing time line chart."""

    def __init__(
        self, history_length: int = 120, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(100)
        self._history: deque[float] = deque(maxlen=history_length)
        self._max_ms = 10.0
        self._target_ms = 5.0

    def push_value(self, ms: float) -> None:
        """Add a processing time measurement."""
        self._history.append(ms)
        if ms > self._max_ms * 0.9:
            self._max_ms = max(self._max_ms, ms * 1.2)
        self.update()

    def set_target(self, ms: float) -> None:
        self._target_ms = ms

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 30

        painter.fillRect(self.rect(), QColor(10, 14, 20))

        if not self._history:
            painter.setPen(QColor(139, 148, 158))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter,
                "Waiting for data..."
            )
            painter.end()
            return

        plot_w = w - margin - 5
        plot_h = h - 10

        # Target line
        target_y = h - 5 - (self._target_ms / self._max_ms) * plot_h
        painter.setPen(
            QPen(QColor(255, 159, 67, 120), 1, Qt.PenStyle.DashLine)
        )
        painter.drawLine(margin, int(target_y), w - 5, int(target_y))

        # Build path
        path = QPainterPath()
        n = len(self._history)
        for i, val in enumerate(self._history):
            x = margin + (i / max(1, n - 1)) * plot_w
            y = h - 5 - (val / self._max_ms) * plot_h
            y = max(5, min(h - 5, y))
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        # Fill gradient
        fill = QPainterPath(path)
        fill.lineTo(margin + plot_w, h - 5)
        fill.lineTo(margin, h - 5)
        fill.closeSubpath()
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, QColor(0, 184, 148, 80))
        gradient.setColorAt(1.0, QColor(0, 184, 148, 10))
        painter.fillPath(fill, gradient)

        # Line
        painter.setPen(QPen(QColor(0, 206, 201), 2))
        painter.drawPath(path)

        # Scale labels
        painter.setPen(QColor(139, 148, 158))
        font = painter.font()
        font.setPointSize(7)
        painter.setFont(font)
        painter.drawText(2, 12, f"{self._max_ms:.0f}ms")
        painter.drawText(2, h - 2, "0ms")

        # Current value
        if self._history:
            cur = self._history[-1]
            color = QColor(0, 184, 148) if cur < self._target_ms else QColor(253, 121, 168)
            painter.setPen(color)
            painter.drawText(w - 50, 12, f"{cur:.1f}ms")

        painter.end()


class PerfMonitor(QWidget):
    """NPU benchmark and performance monitoring panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._frame_count = 0
        self._total_ms = 0.0

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Processing time graph
        graph_group = QGroupBox("PROCESSING TIME")
        graph_layout = QVBoxLayout(graph_group)
        self._graph = ProcessingTimeGraph()
        graph_layout.addWidget(self._graph)
        layout.addWidget(graph_group)

        # Stats row
        stats_group = QGroupBox("PERFORMANCE STATS")
        stats_layout = QVBoxLayout(stats_group)

        row1 = QHBoxLayout()
        self._avg_label = QLabel("Avg: -- ms")
        self._avg_label.setStyleSheet("color: #00CEC9;")
        row1.addWidget(self._avg_label)
        self._peak_label = QLabel("Peak: -- ms")
        self._peak_label.setStyleSheet("color: #FD7978;")
        row1.addWidget(self._peak_label)
        self._fps_label = QLabel("FPS: --")
        self._fps_label.setStyleSheet("color: #FECA57;")
        row1.addWidget(self._fps_label)
        stats_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self._frames_label = QLabel("Frames: 0")
        self._frames_label.setStyleSheet("color: #8B949E;")
        row2.addWidget(self._frames_label)
        self._npu_label = QLabel("NPU: --")
        self._npu_label.setStyleSheet("color: #A29BFE;")
        row2.addWidget(self._npu_label)
        self._budget_label = QLabel("Budget: --")
        self._budget_label.setStyleSheet("color: #55EFC4;")
        row2.addWidget(self._budget_label)
        stats_layout.addLayout(row2)

        layout.addWidget(stats_group)

        # Benchmark button
        self._bench_btn = QPushButton("Run Benchmark")
        self._bench_btn.setStyleSheet(
            "QPushButton { background-color: #6C5CE7; padding: 8px; }"
        )
        layout.addWidget(self._bench_btn)

        layout.addStretch()

    def update_stats(
        self,
        processing_ms: float,
        frames_processed: int,
        npu_active: bool = False,
        buffer_ms: float = 10.0,
    ) -> None:
        """Update performance display."""
        self._graph.push_value(processing_ms)
        self._frame_count += 1
        self._total_ms += processing_ms

        avg = self._total_ms / self._frame_count
        self._avg_label.setText(f"Avg: {avg:.2f} ms")
        self._peak_label.setText(f"Peak: {processing_ms:.2f} ms")
        self._frames_label.setText(f"Frames: {frames_processed}")
        self._npu_label.setText(f"NPU: {'Active' if npu_active else 'Off'}")

        budget_pct = (processing_ms / buffer_ms) * 100 if buffer_ms > 0 else 0
        self._budget_label.setText(f"Budget: {budget_pct:.0f}%")

        if self._frame_count > 0:
            chunk_dur_ms = buffer_ms
            if chunk_dur_ms > 0:
                fps = 1000.0 / chunk_dur_ms
                self._fps_label.setText(f"FPS: {fps:.0f}")

    def reset(self) -> None:
        """Reset all counters."""
        self._frame_count = 0
        self._total_ms = 0.0
        self._graph._history.clear()
        self._avg_label.setText("Avg: -- ms")
        self._peak_label.setText("Peak: -- ms")
        self._fps_label.setText("FPS: --")
        self._frames_label.setText("Frames: 0")
