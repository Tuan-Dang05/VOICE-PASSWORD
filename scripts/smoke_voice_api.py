"""Check the simple MFCC + DTW API using a real WAV file in a temporary database.

Run: backend/.venv/Scripts/python scripts/smoke_voice_api.py phrase.wav --phrase "Mở két an toàn"
The same WAV is reused for all three enrollment samples. This checks wiring only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sample", type=Path)
    parser.add_argument("--phrase", default="Mở két an toàn")
    parser.add_argument("--probe", type=Path)
    args = parser.parse_args()
    sample = args.sample.resolve()
    probe = args.probe.resolve() if args.probe else sample
    if not sample.is_file() or not probe.is_file():
        parser.error("Sample or probe audio file not found")

    backend = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend))
    with tempfile.TemporaryDirectory(prefix="voice-vault-smoke-") as root:
        work = Path(root)
        os.environ["VOICE_DATABASE_URL"] = f"sqlite:///{(work / 'smoke.db').as_posix()}"
        os.environ["VOICE_DATA_DIR"] = str(work / "data")
        os.environ["VOICE_MODEL_DIR"] = str(backend / "data" / "models")
        os.environ["VOICE_SECRET_KEY"] = "smoke-test-only-secret"

        from fastapi.testclient import TestClient
        from app.database import engine
        from app.main import app

        try:
            with TestClient(app) as client:
                response = client.post("/api/auth/register", json={"username": "smoke_user", "password": "smoke-password-123"})
                response.raise_for_status()
                headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
                response = client.post("/api/voice-passwords", json={"name": "Smoke test", "phrase": args.phrase}, headers=headers)
                response.raise_for_status()
                voice_id = response.json()["id"]
                audio = sample.read_bytes()
                for index in range(3):
                    response = client.post(
                        f"/api/voice-passwords/{voice_id}/enroll",
                        files={"file": (sample.name, audio, "audio/wav")}, headers=headers,
                    )
                    response.raise_for_status()
                    print(f"Enrollment {index + 1}/3: active={response.json()['is_active']}", flush=True)
                response = client.post(
                    f"/api/voice-passwords/{voice_id}/verify",
                    files={"file": (probe.name, probe.read_bytes(), "audio/wav")}, headers=headers,
                )
                response.raise_for_status()
                print(json.dumps(response.json(), ensure_ascii=True, indent=2))
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
