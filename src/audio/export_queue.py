"""
Export Queue Module.

Manages batch export of processed audio files with progress
tracking and background processing.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable

import numpy as np

from src.audio.file_io import AudioFileIO

if TYPE_CHECKING:
    from src.audio.processor import AudioProcessor

logger = logging.getLogger(__name__)


class ExportStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExportJob:
    """Single export job in the queue."""

    input_path: str
    output_path: str
    bit_depth: int = 24
    sample_rate: int = 48000
    status: ExportStatus = ExportStatus.PENDING
    progress: float = 0.0
    error_message: str = ""

    @property
    def filename(self) -> str:
        return os.path.basename(self.output_path)


class ExportQueue:
    """Background batch export processor."""

    def __init__(self, processor: AudioProcessor | None = None) -> None:
        self._processor = processor
        self._jobs: list[ExportJob] = []
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._on_progress: Callable[[int, float], None] | None = None
        self._on_complete: Callable[[int, bool], None] | None = None

    @property
    def jobs(self) -> list[ExportJob]:
        with self._lock:
            return list(self._jobs)

    @property
    def is_processing(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def add_job(
        self,
        input_path: str,
        output_path: str,
        bit_depth: int = 24,
        sample_rate: int = 48000,
    ) -> int:
        """Add an export job. Returns job index."""
        job = ExportJob(
            input_path=input_path,
            output_path=output_path,
            bit_depth=bit_depth,
            sample_rate=sample_rate,
        )
        with self._lock:
            self._jobs.append(job)
            return len(self._jobs) - 1

    def remove_job(self, index: int) -> None:
        """Remove a pending job by index."""
        with self._lock:
            if 0 <= index < len(self._jobs):
                if self._jobs[index].status == ExportStatus.PENDING:
                    self._jobs.pop(index)

    def start(self) -> None:
        """Start processing the queue in background."""
        if self.is_processing:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """Cancel processing."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None

    def clear_completed(self) -> None:
        """Remove completed and failed jobs from queue."""
        with self._lock:
            self._jobs = [
                j
                for j in self._jobs
                if j.status not in (ExportStatus.COMPLETED, ExportStatus.FAILED)
            ]

    def _process_queue(self) -> None:
        """Process all pending jobs sequentially."""
        for i, job in enumerate(self._jobs):
            if self._stop_event.is_set():
                job.status = ExportStatus.CANCELLED
                continue

            if job.status != ExportStatus.PENDING:
                continue

            job.status = ExportStatus.PROCESSING
            success = self._process_single(i, job)
            job.status = (
                ExportStatus.COMPLETED if success else ExportStatus.FAILED
            )

            if self._on_complete:
                self._on_complete(i, success)

    def _process_single(self, index: int, job: ExportJob) -> bool:
        """Process a single export job."""
        try:
            result = AudioFileIO.import_audio(
                job.input_path,
                target_sample_rate=job.sample_rate,
            )
            if result is None:
                job.error_message = "Failed to import source file"
                return False

            audio, sr = result
            job.progress = 0.3

            if self._on_progress:
                self._on_progress(index, 0.3)

            # Process through DSP pipeline
            if self._processor:
                chunk_size = 4096
                processed = np.zeros_like(audio)
                total = audio.shape[0]
                for start in range(0, total, chunk_size):
                    if self._stop_event.is_set():
                        return False
                    end = min(start + chunk_size, total)
                    chunk = audio[start:end]
                    processed[start:end] = self._processor.process(chunk)
                    job.progress = 0.3 + 0.5 * (end / total)
                    if self._on_progress:
                        self._on_progress(index, job.progress)
                audio = processed

            job.progress = 0.8
            if self._on_progress:
                self._on_progress(index, 0.8)

            ok = AudioFileIO.export_audio(
                audio,
                job.output_path,
                sample_rate=sr,
                bit_depth=job.bit_depth,
            )
            if not ok:
                job.error_message = "Failed to write output file"
                return False

            job.progress = 1.0
            if self._on_progress:
                self._on_progress(index, 1.0)

            logger.info("Exported: %s", job.filename)
            return True

        except Exception as e:
            job.error_message = str(e)
            logger.error("Export failed for %s: %s", job.filename, e)
            return False

    @property
    def pending_count(self) -> int:
        with self._lock:
            return sum(
                1 for j in self._jobs if j.status == ExportStatus.PENDING
            )

    @property
    def completed_count(self) -> int:
        with self._lock:
            return sum(
                1 for j in self._jobs if j.status == ExportStatus.COMPLETED
            )
