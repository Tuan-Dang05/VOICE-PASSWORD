import math
import wave
from pathlib import Path

import numpy as np

from app.models import AlgorithmConfig
from app.services.audio import AudioValidationError, process_audio


def algorithm_config():
    return AlgorithmConfig(
        sample_rate=16000, n_mfcc=13, frame_ms=25, hop_ms=10,
        default_threshold=4.5, auto_lock_seconds=8, max_failed_attempts=5,
        lockout_seconds=60, min_duration_seconds=1.0,
        max_duration_seconds=5.0, min_rms=0.01,
    )


def write_signal(path: Path, amplitude: float, seconds: float = 2.0):
    sample_rate = 16000
    time = np.arange(int(sample_rate * seconds)) / sample_rate
    envelope = 0.55 + 0.45 * np.sin(2 * math.pi * 3 * time) ** 2
    signal = amplitude * envelope * (np.sin(2 * math.pi * 180 * time) + 0.35 * np.sin(2 * math.pi * 520 * time))
    pcm = np.clip(signal * 32767, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(sample_rate); output.writeframes(pcm.tobytes())


def test_audio_pipeline_extracts_mfcc(tmp_path):
    path = tmp_path / "voice.wav"
    write_signal(path, 0.25)
    result = process_audio(path, algorithm_config())
    assert result.features.ndim == 2
    assert result.features.shape[1] == 13
    assert 1.9 <= result.duration_seconds <= 2.1
    assert abs(float(result.features.mean())) < 1e-4


def test_quiet_audio_is_rejected(tmp_path):
    path = tmp_path / "quiet.wav"
    write_signal(path, 0.0001)
    try:
        process_audio(path, algorithm_config())
        raise AssertionError("quiet audio should have failed")
    except AudioValidationError as error:
        assert error.code == "too_quiet"
