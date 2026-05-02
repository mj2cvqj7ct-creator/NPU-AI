"""Tests for export queue module."""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from src.audio.export_queue import ExportJob, ExportQueue, ExportStatus
from src.audio.file_io import AudioFileIO


class TestExportJob:
    def test_defaults(self):
        job = ExportJob(input_path="/in.wav", output_path="/out.wav")
        assert job.status == ExportStatus.PENDING
        assert job.progress == 0.0
        assert job.filename == "out.wav"


class TestExportQueue:
    @pytest.fixture()
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture()
    def sample_wav(self, temp_dir):
        audio = np.random.randn(48000, 2).astype(np.float32) * 0.3
        path = os.path.join(temp_dir, "input.wav")
        AudioFileIO.export_audio(audio, path, sample_rate=48000, bit_depth=16)
        return path

    def test_add_job(self):
        q = ExportQueue()
        idx = q.add_job("/in.wav", "/out.wav")
        assert idx == 0
        assert q.pending_count == 1

    def test_remove_pending_job(self):
        q = ExportQueue()
        q.add_job("/in.wav", "/out.wav")
        q.remove_job(0)
        assert q.pending_count == 0

    def test_is_processing_default(self):
        q = ExportQueue()
        assert q.is_processing is False

    def test_process_single_file(self, temp_dir, sample_wav):
        q = ExportQueue()
        out = os.path.join(temp_dir, "output.wav")
        q.add_job(sample_wav, out)
        q.start()
        q._thread.join(timeout=10)
        assert q.completed_count == 1
        assert os.path.exists(out)

    def test_clear_completed(self, temp_dir, sample_wav):
        q = ExportQueue()
        out = os.path.join(temp_dir, "output2.wav")
        q.add_job(sample_wav, out)
        q.start()
        q._thread.join(timeout=10)
        q.clear_completed()
        assert len(q.jobs) == 0

    def test_cancel(self):
        q = ExportQueue()
        q.add_job("/in.wav", "/out.wav")
        q.cancel()
        assert q.is_processing is False

    def test_multiple_jobs(self, temp_dir, sample_wav):
        q = ExportQueue()
        out1 = os.path.join(temp_dir, "o1.wav")
        out2 = os.path.join(temp_dir, "o2.wav")
        q.add_job(sample_wav, out1)
        q.add_job(sample_wav, out2)
        q.start()
        q._thread.join(timeout=15)
        assert q.completed_count == 2
