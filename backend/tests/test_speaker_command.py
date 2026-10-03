import numpy as np
import pytest

from app.services.speaker_command import contains_command, cosine_similarity, enrollment_threshold, speaker_score, select_similarity_threshold


@pytest.mark.parametrize(("transcript", "command", "expected"), [
    ("Mở két cho tôi nhé", "Mở két", True),
    ("Hãy MỞ KÉT!", "mở két", True),
    ("mo ket cho toi", "Mở két", True),
    ("Tôi mở két-sắt", "Mở két", True),
    ("Tôi mở kétô", "Mở két", False),
    ("Mở cửa, sau đó két", "Mở két", False),
    ("", "Mở két", False),
])
def test_command_requires_contiguous_words(transcript, command, expected):
    assert contains_command(transcript, command) is expected


def test_speaker_score_prefers_two_best_of_three_sessions():
    probe = np.array([1.0, 0.0], dtype=np.float32)
    templates = [probe, np.array([0.9, 0.1]), np.array([0.0, 1.0])]
    threshold, similarities = enrollment_threshold(templates)
    assert threshold == 0.65
    assert len(similarities) == 3
    assert speaker_score(probe, templates) > threshold
    assert speaker_score(np.array([-1.0, 0.0]), templates) < threshold
    with pytest.raises(ValueError):
        cosine_similarity(probe, np.array([0.0, 0.0]))


def test_similarity_threshold_prioritizes_low_false_accept_rate():
    result = select_similarity_threshold([0.71, 0.75, 0.8], [0.33, 0.45, 0.6])
    assert result["far"] == 0
    assert result["frr"] == 0
    assert 0.6 < result["threshold"] <= 0.71
