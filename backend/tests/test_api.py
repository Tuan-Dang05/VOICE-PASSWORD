import io
import math
import wave

import numpy as np
import app.routers.voice_passwords as voice_router

from app.database import SessionLocal
from app.models import User, VoicePassword


def voice_wav(frequency: float = 180, seconds: float = 1.7) -> bytes:
    sample_rate = 16000
    time = np.arange(int(sample_rate * seconds)) / sample_rate
    envelope = 0.55 + 0.45 * np.sin(2 * math.pi * 3 * time) ** 2
    signal = 0.24 * envelope * (
        np.sin(2 * math.pi * frequency * time)
        + 0.3 * np.sin(2 * math.pi * frequency * 2.7 * time)
    )
    pcm = np.clip(signal * 32767, -32768, 32767).astype("<i2")
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return output.getvalue()


def register(client, username: str) -> dict:
    response = client.post("/api/auth/register", json={
        "username": username, "password": "strong-pass-123",
    })
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create(client, headers: dict) -> int:
    response = client.post(
        "/api/voice-passwords",
        json={"name": "Két demo", "phrase": "Mở két an toàn"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["template_count"] == 0
    return response.json()["id"]


def upload(client, headers: dict, voice_id: int, route: str, data: bytes):
    return client.post(
        f"/api/voice-passwords/{voice_id}/{route}",
        files={"file": ("recording.wav", data, "audio/wav")},
        headers=headers,
    )


def test_auth_and_owner_isolation(client):
    assert client.get("/api/voice-passwords").status_code == 401
    alice = register(client, "voice_alice")
    bob = register(client, "voice_bob")
    voice_id = create(client, alice)
    assert client.get(f"/api/voice-passwords/{voice_id}", headers=bob).status_code == 404
    assert upload(client, bob, voice_id, "verify", voice_wav()).status_code == 404
    login = client.post("/api/auth/login", json={
        "username": "voice_alice", "password": "strong-pass-123",
    })
    assert login.status_code == 200


def test_three_reads_activate_and_verify_without_extra_steps(client, monkeypatch):
    monkeypatch.setattr(voice_router, "extract_embedding", lambda samples: np.array([1.0, 0.0], dtype=np.float32))
    headers = register(client, "voice_mfcc_user")
    voice_id = create(client, headers)
    assert upload(client, headers, voice_id, "verify", voice_wav()).status_code == 409
    for count in range(1, 4):
        enrolled = upload(client, headers, voice_id, "enroll", voice_wav())
        assert enrolled.status_code == 200, enrolled.text
        result = enrolled.json()
        assert result["sample_count"] == count
        assert result["is_active"] is (count == 3)
    assert result["threshold"] is not None
    listed = client.get("/api/voice-passwords", headers=headers).json()
    profile = next(item for item in listed if item["id"] == voice_id)
    assert profile["is_active"] is True
    assert profile["template_count"] == 3
    assert profile["speaker_threshold"] is not None
    assert profile["command_template_count"] == 0
    assert upload(client, headers, voice_id, "enroll", voice_wav()).status_code == 409

    verified = upload(client, headers, voice_id, "verify", voice_wav())
    assert verified.status_code == 200, verified.text
    assert verified.json()["granted"] is True
    assert verified.json()["reason"] == "matched"
    assert verified.json()["dtw_score"] <= verified.json()["dtw_threshold"]
    assert verified.json()["score"] == verified.json()["dtw_score"]
    assert verified.json()["speaker_matched"] is True
    assert verified.json()["speaker_score"] >= verified.json()["speaker_threshold"]
    assert verified.json()["transcript"] is None
    attempts = client.get("/api/auth-attempts", headers=headers).json()
    assert attempts[0]["dtw_score"] == verified.json()["score"]


def test_invalid_audio_fails_closed_without_lockout(client, monkeypatch):
    monkeypatch.setattr(voice_router, "extract_embedding", lambda samples: np.array([1.0, 0.0], dtype=np.float32))
    headers = register(client, "voice_bad_audio")
    voice_id = create(client, headers)
    invalid = upload(client, headers, voice_id, "enroll", b"")
    assert invalid.status_code == 422
    for _ in range(3):
        assert upload(client, headers, voice_id, "enroll", voice_wav()).status_code == 200
    for _ in range(7):
        denied = upload(client, headers, voice_id, "verify", b"")
        assert denied.status_code == 200
        assert denied.json()["granted"] is False
        assert denied.json()["reason"] == "empty_audio"
    assert client.get(f"/api/voice-passwords/{voice_id}", headers=headers).json()["locked_until"] is None


def test_wrong_phrase_denied_and_five_mismatches_lock_temporarily(client, monkeypatch):
    monkeypatch.setattr(voice_router, "extract_embedding", lambda samples: np.array([1.0, 0.0], dtype=np.float32))
    headers = register(client, "voice_wrong_phrase")
    voice_id = create(client, headers)
    for _ in range(3):
        assert upload(client, headers, voice_id, "enroll", voice_wav(180)).status_code == 200
    for count in range(5):
        response = upload(client, headers, voice_id, "verify", voice_wav(620))
        assert response.status_code == 200
        assert response.json()["granted"] is False
        assert response.json()["reason"] == ("locked_out" if count == 4 else "score_above_threshold")
    assert upload(client, headers, voice_id, "verify", voice_wav(180)).status_code == 429


def test_previous_speaker_profile_kept_but_requires_new_three_read_enrollment(client):
    headers = register(client, "voice_legacy_user")
    with SessionLocal() as db:
        user = db.query(User).filter_by(username="voice_legacy_user").one()
        old = VoicePassword(user_id=user.id, name="Mẫu đoạn văn cũ", phrase="Mở két",
                            config_version="speaker-command-v1", is_active=True, threshold=0.65)
        db.add(old)
        db.commit()
        voice_id = old.id
    listed = client.get("/api/voice-passwords", headers=headers).json()
    profile = next(item for item in listed if item["id"] == voice_id)
    assert profile["requires_reenrollment"] is True
    assert profile["is_active"] is False
    assert upload(client, headers, voice_id, "verify", voice_wav()).status_code == 409


def test_same_phrase_from_another_speaker_cannot_open(client, monkeypatch):
    headers = register(client, "voice_other_speaker")
    voice_id = create(client, headers)
    monkeypatch.setattr(voice_router, "extract_embedding", lambda samples: np.array([1.0, 0.0], dtype=np.float32))
    for _ in range(3):
        assert upload(client, headers, voice_id, "enroll", voice_wav()).status_code == 200
    monkeypatch.setattr(voice_router, "extract_embedding", lambda samples: np.array([0.0, 1.0], dtype=np.float32))
    response = upload(client, headers, voice_id, "verify", voice_wav())
    assert response.status_code == 200
    assert response.json()["dtw_matched"] is True
    assert response.json()["speaker_matched"] is False
    assert response.json()["granted"] is False
    assert response.json()["reason"] == "speaker_mismatch"


def test_missing_speaker_model_does_not_save_an_enrollment_sample(client, monkeypatch):
    headers = register(client, "voice_missing_model")
    voice_id = create(client, headers)
    monkeypatch.setattr(voice_router, "extract_embedding", lambda samples: (_ for _ in ()).throw(FileNotFoundError("model missing")))
    response = upload(client, headers, voice_id, "enroll", voice_wav())
    assert response.status_code == 503
    item = client.get(f"/api/voice-passwords/{voice_id}", headers=headers).json()
    assert item["template_count"] == 0


def test_third_sample_from_different_speaker_is_not_accepted(client, monkeypatch):
    headers = register(client, "voice_mixed_enrollment")
    voice_id = create(client, headers)
    monkeypatch.setattr(voice_router, "extract_embedding", lambda samples: np.array([1.0, 0.0], dtype=np.float32))
    for _ in range(2):
        assert upload(client, headers, voice_id, "enroll", voice_wav()).status_code == 200
    monkeypatch.setattr(voice_router, "extract_embedding", lambda samples: np.array([0.0, 1.0], dtype=np.float32))
    rejected = upload(client, headers, voice_id, "enroll", voice_wav())
    assert rejected.status_code == 422
    profile = client.get(f"/api/voice-passwords/{voice_id}", headers=headers).json()
    assert profile["template_count"] == 2
    assert profile["is_active"] is False
