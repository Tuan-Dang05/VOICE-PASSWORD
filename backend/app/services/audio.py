from __future__ import annotations

import subprocess
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

from ..config import get_settings
from ..models import AlgorithmConfig


class AudioValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class ProcessedAudio:
    features: np.ndarray | None
    duration_seconds: float
    quality: dict
    samples: np.ndarray | None = None


def _decode_to_wav(input_path: Path, output_path: Path, sample_rate: int) -> None:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=15)
    except FileNotFoundError as exc:
        raise AudioValidationError("decoder_unavailable", "Không tìm thấy FFmpeg trên máy chủ") from exc
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise AudioValidationError("invalid_audio", "Không thể giải mã tệp âm thanh") from exc


def _read_pcm16_wav(path: Path) -> tuple[np.ndarray, int]:
    try:
        with wave.open(str(path), "rb") as wav:
            sample_rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
            channels = wav.getnchannels()
            width = wav.getsampwidth()
    except (wave.Error, EOFError) as exc:
        raise AudioValidationError("invalid_audio", "Tệp WAV không hợp lệ") from exc
    if channels != 1 or width != 2:
        raise AudioValidationError("invalid_audio", "Audio sau chuyển đổi không phải PCM mono 16-bit")
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    return samples, sample_rate


def command_mfcc(samples: np.ndarray, config: AlgorithmConfig) -> np.ndarray:
    """Frame-wise MFCC shape used for phrase spotting with subsequence DTW."""
    n_fft = round(config.sample_rate * config.frame_ms / 1000)
    hop_length = round(config.sample_rate * config.hop_ms / 1000)
    mfcc = librosa.feature.mfcc(
        y=np.asarray(samples, dtype=np.float32), sr=config.sample_rate,
        n_mfcc=config.n_mfcc, n_fft=n_fft, win_length=n_fft,
        hop_length=hop_length, window="hann", center=False,
    ).T.astype(np.float32)
    if mfcc.shape[0] < 2 or mfcc.shape[1] < 2:
        raise AudioValidationError("no_speech", "Không đủ MFCC để so khớp cụm lệnh")
    # Drop energy coefficient, then normalize each coefficient across the clip.
    # This preserves time-varying spectral detail for DTW while reducing gain drift.
    spectral = mfcc[:, 1:]
    mean = spectral.mean(axis=0, keepdims=True)
    std = spectral.std(axis=0, keepdims=True)
    return np.ascontiguousarray((spectral - mean) / np.maximum(std, 1e-6))


def process_audio(input_path: Path, config: AlgorithmConfig, *, speaker_mode: bool = False, enrollment: bool = False, simple_mode: bool = False) -> ProcessedAudio:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    wav_path = settings.upload_dir / f"{uuid.uuid4().hex}.wav"
    try:
        _decode_to_wav(input_path, wav_path, config.sample_rate)
        samples, sample_rate = _read_pcm16_wav(wav_path)
    finally:
        wav_path.unlink(missing_ok=True)

    if samples.size == 0:
        raise AudioValidationError("empty_audio", "Không tìm thấy dữ liệu âm thanh")

    duration = samples.size / sample_rate
    minimum = 6.0 if speaker_mode and enrollment else config.min_duration_seconds
    maximum = 20.0 if speaker_mode and enrollment else (8.0 if speaker_mode else config.max_duration_seconds)
    if simple_mode:
        minimum, maximum = 1.0, 8.0
    if duration < minimum:
        raise AudioValidationError("too_short", f"Bản ghi phải dài ít nhất {minimum:.1f} giây")
    if duration > maximum:
        raise AudioValidationError("too_long", f"Bản ghi không được dài quá {maximum:.1f} giây")

    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    clipping_ratio = float(np.mean(np.abs(samples) >= 0.99))
    if rms < config.min_rms:
        raise AudioValidationError("too_quiet", "Âm thanh quá nhỏ hoặc không có giọng nói")
    if clipping_ratio > 0.05:
        raise AudioValidationError("clipping", "Âm thanh bị vỡ tiếng; hãy giảm âm lượng hoặc lùi xa microphone")

    trimmed, _ = librosa.effects.trim(samples, top_db=30, frame_length=400, hop_length=160)
    trimmed_duration = trimmed.size / sample_rate
    if trimmed_duration < (0.3 if simple_mode else 0.6):
        raise AudioValidationError("no_speech", "Không phát hiện đủ giọng nói trong bản ghi")

    trimmed = trimmed / max(float(np.max(np.abs(trimmed))), 1e-8) * 0.98
    quality = {
        "rms": round(rms, 5),
        "peak": round(peak, 5),
        "clipping_ratio": round(clipping_ratio, 5),
        "trimmed_duration_seconds": round(trimmed_duration, 3),
    }
    if speaker_mode and not simple_mode:
        if enrollment and trimmed_duration < 5.0:
            raise AudioValidationError("too_short", "Cần ít nhất 5 giây có giọng nói rõ ràng")
        return ProcessedAudio(features=None, duration_seconds=duration, quality=quality, samples=np.ascontiguousarray(trimmed, dtype=np.float32))
    n_fft = round(sample_rate * config.frame_ms / 1000)
    hop_length = round(sample_rate * config.hop_ms / 1000)
    mfcc = librosa.feature.mfcc(
        y=trimmed,
        sr=sample_rate,
        n_mfcc=config.n_mfcc,
        n_fft=n_fft,
        win_length=n_fft,
        hop_length=hop_length,
        window="hann",
        center=False,
    ).T.astype(np.float32)
    if mfcc.shape[0] < 2:
        raise AudioValidationError("no_speech", "Không đủ frame để trích xuất MFCC")
    mean = mfcc.mean(axis=0, keepdims=True)
    std = mfcc.std(axis=0, keepdims=True)
    features = (mfcc - mean) / np.maximum(std, 1e-6)

    quality.update({
        "trimmed_duration_seconds": round(trimmed_duration, 3),
        "frames": int(features.shape[0]),
        "coefficients": int(features.shape[1]),
    })
    return ProcessedAudio(
        features=features, duration_seconds=duration, quality=quality,
        samples=np.ascontiguousarray(trimmed, dtype=np.float32) if simple_mode else None,
    )


def save_upload(data: bytes, original_name: str | None) -> Path:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if not data:
        raise AudioValidationError("empty_audio", "Tệp âm thanh rỗng")
    if len(data) > settings.max_upload_bytes:
        raise AudioValidationError("file_too_large", "Tệp âm thanh vượt quá 10 MB")
    suffix = Path(original_name or "recording.webm").suffix.lower() or ".webm"
    if suffix not in {".wav", ".webm", ".ogg", ".mp3", ".m4a", ".mp4"}:
        suffix = ".bin"
    path = settings.upload_dir / f"{uuid.uuid4().hex}{suffix}"
    path.write_bytes(data)
    return path
