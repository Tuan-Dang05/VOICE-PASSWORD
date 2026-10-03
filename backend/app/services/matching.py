from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist


def normalized_dtw(left: np.ndarray, right: np.ndarray) -> float:
    if left.ndim != 2 or right.ndim != 2 or left.shape[1] != right.shape[1]:
        raise ValueError("Hai ma trận MFCC phải có dạng T x K và cùng số hệ số")
    if left.shape[0] == 0 or right.shape[0] == 0:
        raise ValueError("Chuỗi MFCC không được rỗng")

    distances = cdist(left.astype(np.float64), right.astype(np.float64), metric="euclidean")
    rows, cols = distances.shape
    costs = np.full((rows + 1, cols + 1), np.inf, dtype=np.float64)
    lengths = np.zeros((rows + 1, cols + 1), dtype=np.int32)
    costs[0, 0] = 0.0

    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            candidates = ((costs[i - 1, j], i - 1, j), (costs[i, j - 1], i, j - 1), (costs[i - 1, j - 1], i - 1, j - 1))
            best_cost, prev_i, prev_j = min(candidates, key=lambda item: item[0])
            costs[i, j] = distances[i - 1, j - 1] + best_cost
            lengths[i, j] = lengths[prev_i, prev_j] + 1

    return float(costs[rows, cols] / max(int(lengths[rows, cols]), 1))


def subsequence_dtw(command: np.ndarray, utterance: np.ndarray) -> float:
    """Lowest normalized DTW cost for a complete command inside an utterance."""
    if command.ndim != 2 or utterance.ndim != 2 or command.shape[1] != utterance.shape[1]:
        raise ValueError("MFCC lệnh và câu nói phải có cùng số hệ số")
    if command.shape[0] < 2 or utterance.shape[0] < 2:
        raise ValueError("MFCC quá ngắn")
    distances = cdist(command.astype(np.float64), utterance.astype(np.float64), metric="euclidean")
    rows, cols = distances.shape
    previous = np.zeros(cols + 1, dtype=np.float64)  # free starting position
    previous_lengths = np.zeros(cols + 1, dtype=np.int32)
    for i in range(1, rows + 1):
        current = np.full(cols + 1, np.inf, dtype=np.float64)
        current_lengths = np.zeros(cols + 1, dtype=np.int32)
        for j in range(1, cols + 1):
            best_cost = previous[j - 1]
            length = previous_lengths[j - 1]
            if previous[j] < best_cost:
                best_cost = previous[j]
                length = previous_lengths[j]
            if current[j - 1] < best_cost:
                best_cost = current[j - 1]
                length = current_lengths[j - 1]
            current[j] = best_cost + distances[i - 1, j - 1]
            current_lengths[j] = length + 1
        previous, previous_lengths = current, current_lengths
    valid = previous_lengths[1:] > 0
    return float(np.min(previous[1:][valid] / previous_lengths[1:][valid]))


def command_dtw_threshold(left: np.ndarray, right: np.ndarray) -> float:
    genuine_distance = max(subsequence_dtw(left, right), subsequence_dtw(right, left))
    # Demo margin from two genuine reads; validation with other speakers is still required.
    return round(float(np.clip(genuine_distance + 0.75, 2.7, 5.0)), 4)


def aggregate_template_scores(probe: np.ndarray, templates: list[np.ndarray]) -> tuple[float, list[float]]:
    if not templates:
        raise ValueError("Không có template để so khớp")
    scores = sorted(normalized_dtw(probe, template) for template in templates)
    take = min(2, len(scores))
    return float(np.mean(scores[:take])), scores


def calibrate_from_enrollment(templates: list[np.ndarray], fallback_threshold: float) -> tuple[float, list[float]]:
    if len(templates) < 3:
        raise ValueError("Cần ít nhất 3 template để hiệu chỉnh")
    scores = [
        normalized_dtw(templates[i], templates[j])
        for i in range(len(templates))
        for j in range(i + 1, len(templates))
    ]
    median = float(np.median(scores))
    mad = float(np.median(np.abs(np.asarray(scores) - median)))
    robust_upper = median + 3.0 * 1.4826 * mad + 0.15
    threshold = min(fallback_threshold, max(median + 0.15, robust_upper))
    return round(threshold, 4), [round(value, 4) for value in scores]


def select_threshold(genuine_scores: list[float], impostor_scores: list[float], max_far: float = 0.05) -> dict:
    if not genuine_scores or not impostor_scores:
        raise ValueError("Cần cả score genuine và impostor")
    candidates = sorted(set(genuine_scores + impostor_scores))
    best: dict | None = None
    for threshold in candidates:
        frr = sum(score > threshold for score in genuine_scores) / len(genuine_scores)
        far = sum(score <= threshold for score in impostor_scores) / len(impostor_scores)
        balanced_accuracy = ((1 - frr) + (1 - far)) / 2
        candidate = {"threshold": threshold, "far": far, "frr": frr, "balanced_accuracy": balanced_accuracy}
        if far <= max_far and (best is None or balanced_accuracy > best["balanced_accuracy"]):
            best = candidate
    if best is None:
        best = min(
            (
                {
                    "threshold": threshold,
                    "far": sum(score <= threshold for score in impostor_scores) / len(impostor_scores),
                    "frr": sum(score > threshold for score in genuine_scores) / len(genuine_scores),
                    "balanced_accuracy": (
                        2
                        - sum(score > threshold for score in genuine_scores) / len(genuine_scores)
                        - sum(score <= threshold for score in impostor_scores) / len(impostor_scores)
                    )
                    / 2,
                }
                for threshold in candidates
            ),
            key=lambda item: (item["far"], -item["balanced_accuracy"]),
        )
    return {key: round(float(value), 4) for key, value in best.items()}

