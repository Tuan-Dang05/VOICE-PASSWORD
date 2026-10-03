"""Fixed-phrase Voice Password: MFCC templates and normalized full-sequence DTW."""
import numpy as np

from .matching import normalized_dtw

PROFILE_VERSION = "mfcc-dtw-speaker-v1"
SAMPLE_COUNT = 3
MIN_SPEAKER_SIMILARITY = 0.60


def validate_features(features: np.ndarray) -> np.ndarray:
    result = np.asarray(features, dtype=np.float32)
    if result.ndim != 2 or result.shape[0] < 2 or result.shape[1] < 2 or not np.isfinite(result).all():
        raise ValueError("Mẫu MFCC không hợp lệ; hãy thu lại")
    return result


def load_template(path: str) -> np.ndarray:
    with np.load(path, allow_pickle=False) as archive:
        return validate_features(archive["mfcc"])


def load_speaker_template(path: str) -> np.ndarray:
    with np.load(path, allow_pickle=False) as archive:
        result = np.asarray(archive["speaker_embedding"], dtype=np.float32)
    if result.ndim != 1 or result.size < 2 or not np.isfinite(result).all():
        raise ValueError("Mẫu người nói không hợp lệ")
    return result


def calibrate_speaker(templates: list[np.ndarray]) -> tuple[float, list[float]]:
    from .speaker_command import cosine_similarity

    if len(templates) != SAMPLE_COUNT:
        raise ValueError("Cần đúng 3 mẫu người nói")
    scores = [cosine_similarity(templates[i], templates[j]) for i in range(3) for j in range(i + 1, 3)]
    if min(scores) < 0.5:
        raise ValueError("Ba mẫu giọng chưa đồng nhất. Hãy thu lại lần này bằng cùng người và cùng micro")
    # Short-phrase embeddings vary more than paragraph embeddings. A fixed floor
    # avoids setting a threshold so low that the same phrase in another voice passes.
    threshold = float(np.clip(min(scores) - 0.12, MIN_SPEAKER_SIMILARITY, 0.75))
    return round(threshold, 4), [round(score, 4) for score in scores]


def match_phrase(probe: np.ndarray, templates: list[np.ndarray]) -> tuple[float, list[float]]:
    probe = validate_features(probe)
    if len(templates) != SAMPLE_COUNT:
        raise ValueError("Cần đủ 3 mẫu câu mật khẩu")
    scores = sorted(normalized_dtw(probe, validate_features(template)) for template in templates)
    return float(np.mean(scores[:2])), scores


def calibrate_phrase(templates: list[np.ndarray]) -> tuple[float, list[float]]:
    if len(templates) != SAMPLE_COUNT:
        raise ValueError("Cần đúng 3 mẫu câu mật khẩu")
    arrays = [validate_features(sample) for sample in templates]
    matrix = np.zeros((SAMPLE_COUNT, SAMPLE_COUNT))
    pairwise = []
    for i in range(SAMPLE_COUNT):
        for j in range(i + 1, SAMPLE_COUNT):
            matrix[i, j] = matrix[j, i] = normalized_dtw(arrays[i], arrays[j])
            pairwise.append(float(matrix[i, j]))
    # Evaluate each enrollment sample against the other two, without self matches.
    genuine_scores = matrix.sum(axis=1) / 2
    # Small enrollment-only margin for a demo, not a claimed FAR-calibrated threshold.
    threshold = float(np.clip(max(genuine_scores) * 1.20 + 0.25, 2.0, 4.0))
    return round(threshold, 4), [round(value, 4) for value in pairwise]
