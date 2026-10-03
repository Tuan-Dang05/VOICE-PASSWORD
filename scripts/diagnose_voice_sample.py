"""Read-only MFCC/DTW and speaker diagnosis for an audio sample.

Run from repository root:
  backend/.venv/Scripts/python scripts/diagnose_voice_sample.py audio.mp3 --profile-id 2
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models import AlgorithmConfig
from app.services.audio import process_audio
from app.services.simple_voice import PROFILE_VERSION, load_speaker_template, load_template, match_phrase


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--profile-id", type=int, required=True)
    parser.add_argument("--database", type=Path, default=ROOT / "backend" / "data" / "voice_password.db")
    args = parser.parse_args()
    audio = args.audio.resolve()
    database = args.database.resolve()
    if not audio.is_file() or not database.is_file():
        parser.error("Không tìm thấy file audio hoặc database")
    with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True) as db:
        has_speaker_column = any(column[1] == "speaker_threshold" for column in db.execute("PRAGMA table_info(voice_passwords)"))
        profile = db.execute(
            "SELECT phrase, config_version, threshold" + (", speaker_threshold" if has_speaker_column else "") + " FROM voice_passwords WHERE id = ?", (args.profile_id,)
        ).fetchone()
        if not profile or profile[1] not in {PROFILE_VERSION, "mfcc-dtw-simple-v1"}:
            parser.error("Không tìm thấy hồ sơ MFCC + DTW với ID này")
        paths = [Path(row[0]) for row in db.execute(
            "SELECT feature_path FROM voice_templates WHERE voice_password_id = ? ORDER BY id", (args.profile_id,)
        )]
        row = db.execute(
            "SELECT sample_rate, n_mfcc, frame_ms, hop_ms, min_rms FROM algorithm_configs WHERE id = 1"
        ).fetchone()
    if len(paths) != 3:
        parser.error("Hồ sơ chưa có đủ 3 mẫu")
    config = AlgorithmConfig(
        sample_rate=row[0], n_mfcc=row[1], frame_ms=row[2], hop_ms=row[3], min_rms=row[4],
        min_duration_seconds=1, max_duration_seconds=8,
    )
    # App settings use backend/data relative to the backend working directory.
    import os
    os.chdir(ROOT / "backend")
    result = process_audio(audio, config, simple_mode=True)
    score, individual = match_phrase(result.features, [load_template(str(path)) for path in paths])
    diagnosis = {
        "profile_id": args.profile_id,
        "phrase": profile[0],
        "profile_version": profile[1],
        "sample_duration_seconds": round(result.duration_seconds, 3),
        "sample_quality": result.quality,
        "template_distances": [round(value, 4) for value in individual],
        "final_distance": round(score, 4),
        "dtw_threshold": profile[2],
        "dtw_matched": score <= profile[2],
    }
    if profile[1] == PROFILE_VERSION and len(profile) > 3 and profile[3] is not None:
        from app.services.speaker_command import extract_embedding, speaker_score
        identity = speaker_score(extract_embedding(result.samples), [load_speaker_template(str(path)) for path in paths])
        diagnosis.update({
            "speaker_similarity": round(identity, 4),
            "speaker_threshold": profile[3],
            "speaker_matched": identity >= profile[3],
            "would_open": score <= profile[2] and identity >= profile[3],
        })
    else:
        diagnosis["would_open"] = False
        diagnosis["note"] = "Hồ sơ cũ thiếu đặc trưng người nói; cần thu lại 3 mẫu để dùng bản hiện tại."
    print(json.dumps(diagnosis, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
