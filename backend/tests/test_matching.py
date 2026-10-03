import numpy as np
import pytest

from app.services.matching import aggregate_template_scores, command_dtw_threshold, normalized_dtw, select_threshold, subsequence_dtw


def test_identical_sequences_have_zero_distance():
    sequence = np.array([[0.0, 1.0], [1.0, 0.5], [2.0, -1.0]], dtype=np.float32)
    assert normalized_dtw(sequence, sequence) == 0.0


def test_dtw_is_symmetric():
    left = np.array([[0.0], [1.0], [2.0]], dtype=np.float32)
    right = np.array([[0.0], [0.7], [1.4], [2.0]], dtype=np.float32)
    assert normalized_dtw(left, right) == pytest.approx(normalized_dtw(right, left))


def test_aggregation_uses_two_best_templates():
    probe = np.array([[0.0], [1.0]], dtype=np.float32)
    templates = [probe.copy(), probe + 0.2, probe + 10]
    score, scores = aggregate_template_scores(probe, templates)
    assert score == pytest.approx((scores[0] + scores[1]) / 2)
    assert scores[2] > scores[1]


def test_threshold_calibration_respects_far_constraint():
    result = select_threshold([0.8, 0.9, 1.0], [2.0, 2.2, 2.5], max_far=0.05)
    assert result["far"] == 0
    assert result["frr"] == 0
    assert 1.0 <= result["threshold"] < 2.0


def test_subsequence_dtw_finds_command_inside_longer_utterance():
    command = np.array([[0.0], [1.0], [2.0]], dtype=np.float32)
    sentence = np.array([[9.0], [9.0], [0.0], [1.0], [2.0], [8.0]], dtype=np.float32)
    assert subsequence_dtw(command, sentence) == 0.0
    assert subsequence_dtw(command, np.array([[5.0], [5.0], [5.0]], dtype=np.float32)) > 1.0
    assert 2.7 <= command_dtw_threshold(command, command) <= 5.0
