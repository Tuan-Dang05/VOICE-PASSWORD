"""Text-independent speaker embeddings plus Vietnamese command transcription."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import numpy as np

from ..config import get_settings

SPEAKER_MODEL_NAME = "3dspeaker_speech_eres2net_sv_en_voxceleb_16k.onnx"
PROFILE_VERSION = "speaker-command-v1"
MIN_SPEAKER_SIMILARITY = 0.65  # Demo starting point; calibrate with impostor validation recordings.
def normalized_words(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).casefold().replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    return re.findall(r"[a-z0-9]+", text)


def contains_command(transcript: str, command: str) -> bool:
    words, wanted = normalized_words(transcript), normalized_words(command)
    return bool(wanted) and any(words[i:i + len(wanted)] == wanted for i in range(len(words) - len(wanted) + 1))


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    a, b = np.asarray(left, dtype=np.float32).reshape(-1), np.asarray(right, dtype=np.float32).reshape(-1)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Embedding người nói không hợp lệ")
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    if norm < 1e-8:
        raise ValueError("Embedding người nói rỗng")
    return float(np.dot(a, b) / norm)


def speaker_score(probe: np.ndarray, templates: list[np.ndarray]) -> float:
    if len(templates) < 3:
        raise ValueError("Cần 3 phiên ghi âm")
    return float(np.mean(sorted((cosine_similarity(probe, sample) for sample in templates), reverse=True)[:2]))


def enrollment_threshold(templates: list[np.ndarray], threshold: float = MIN_SPEAKER_SIMILARITY) -> tuple[float, list[float]]:
    if len(templates) != 3:
        raise ValueError("Cần đúng 3 phiên ghi âm")
    pairwise = [cosine_similarity(templates[i], templates[j]) for i, j in ((0, 1), (0, 2), (1, 2))]
    return threshold, [round(value, 4) for value in pairwise]


def select_similarity_threshold(genuine: list[float], impostor: list[float], max_far: float = 0.05) -> dict:
    if not genuine or not impostor:
        raise ValueError("Cần score của cả người thật và người khác")
    candidates = sorted(set(genuine + impostor))
    evaluated = []
    for threshold in candidates:
        far = sum(score >= threshold for score in impostor) / len(impostor)
        frr = sum(score < threshold for score in genuine) / len(genuine)
        evaluated.append({"threshold": threshold, "far": far, "frr": frr,
                          "balanced_accuracy": 1 - (far + frr) / 2})
    valid = [item for item in evaluated if item["far"] <= max_far]
    pool = valid or evaluated
    best = max(pool, key=lambda item: (item["balanced_accuracy"], -item["far"]))
    return {key: round(float(value), 4) for key, value in best.items()}


@lru_cache(maxsize=1)
def _extractor():
    import sherpa_onnx
    path = get_settings().model_dir / SPEAKER_MODEL_NAME
    if not path.is_file():
        raise FileNotFoundError(f"Chưa có mô hình nhận dạng người nói: {path}. Chạy scripts/prepare_voice_models.py")
    config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(path), num_threads=2, provider="cpu")
    if not config.validate():
        raise RuntimeError("Mô hình nhận dạng người nói không hợp lệ")
    return sherpa_onnx.SpeakerEmbeddingExtractor(config)


def extract_embedding(samples: np.ndarray) -> np.ndarray:
    extractor = _extractor()
    stream = extractor.create_stream()
    stream.accept_waveform(sample_rate=16000, waveform=np.ascontiguousarray(samples, dtype=np.float32))
    stream.input_finished()
    if not extractor.is_ready(stream):
        raise ValueError("Audio chưa đủ để nhận dạng người nói")
    embedding = np.asarray(extractor.compute(stream), dtype=np.float32)
    if embedding.ndim != 1 or not np.isfinite(embedding).all() or np.linalg.norm(embedding) < 1e-8:
        raise ValueError("Không thể trích xuất đặc trưng người nói")
    return embedding / np.linalg.norm(embedding)


@lru_cache(maxsize=1)
def _asr():
    from faster_whisper import WhisperModel
    path = get_settings().model_dir / "whisper-base"
    if not (path / "model.bin").is_file():
        raise FileNotFoundError(f"Chưa có mô hình nhận dạng tiếng Việt: {path}. Chạy scripts/prepare_voice_models.py")
    return WhisperModel(str(path), device="cpu", compute_type="int8", cpu_threads=4)


def transcribe_vietnamese(samples: np.ndarray) -> str:
    segments, _ = _asr().transcribe(samples, language="vi", beam_size=3, vad_filter=False, condition_on_previous_text=False)
    return " ".join(segment.text.strip() for segment in segments).strip()
