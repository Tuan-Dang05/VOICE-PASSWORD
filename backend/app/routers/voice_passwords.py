from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..database import get_db
from ..deps import get_algorithm_config, get_current_user
from ..models import AuthenticationAttempt, User, VoicePassword, VoiceTemplate
from ..schemas import EnrollmentResponse, FinalizeResponse, VerifyResponse, VoicePasswordCreate, VoicePasswordOut
from ..services.audio import AudioValidationError, process_audio, save_upload
from ..services.simple_voice import (
    PROFILE_VERSION, SAMPLE_COUNT, calibrate_phrase, calibrate_speaker,
    load_speaker_template, load_template, match_phrase,
)
from ..services.speaker_command import extract_embedding, speaker_score

router = APIRouter(prefix="/voice-passwords", tags=["voice-passwords"])
logger = logging.getLogger(__name__)


def _serialize_write(db: Session):
    # Serialize concurrent enrollment/verification writes on the local SQLite demo.
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))


def _get_owned(db: Session, voice_password_id: int, user_id: int) -> VoicePassword:
    item = db.scalar(
        select(VoicePassword)
        .options(selectinload(VoicePassword.templates), selectinload(VoicePassword.command_templates))
        .where(VoicePassword.id == voice_password_id, VoicePassword.user_id == user_id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy mật khẩu giọng nói")
    return item


def _to_out(item: VoicePassword) -> VoicePasswordOut:
    legacy = item.config_version != PROFILE_VERSION
    return VoicePasswordOut.model_validate(item).model_copy(update={
        "template_count": len(item.templates),
        "command_template_count": len(item.command_templates),
        "is_active": item.is_active and not legacy,
        "requires_reenrollment": legacy,
    })


def _require_simple(item: VoicePassword):
    if item.config_version != PROFILE_VERSION:
        raise HTTPException(status_code=409, detail="Mẫu cũ chưa có đặc trưng người nói. Hãy tạo mật khẩu mới và đọc cùng một câu 3 lần.")


@router.get("", response_model=list[VoicePasswordOut])
def list_voice_passwords(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(VoicePassword)
        .options(selectinload(VoicePassword.templates), selectinload(VoicePassword.command_templates))
        .where(VoicePassword.user_id == user.id)
        .order_by(VoicePassword.created_at.desc())
    ).all()
    return [_to_out(item) for item in items]


@router.post("", response_model=VoicePasswordOut, status_code=201)
def create_voice_password(payload: VoicePasswordCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    name, phrase = payload.name.strip(), " ".join(payload.phrase.split())
    if not name or not phrase or not any(char.isalnum() for char in phrase):
        raise HTTPException(status_code=422, detail="Hãy nhập tên và câu mật khẩu bạn sẽ đọc")
    item = VoicePassword(user_id=user.id, name=name, phrase=phrase, config_version=PROFILE_VERSION)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.get("/{voice_password_id}", response_model=VoicePasswordOut)
def get_voice_password(voice_password_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _to_out(_get_owned(db, voice_password_id, user.id))


@router.delete("/{voice_password_id}", status_code=204)
def delete_voice_password(voice_password_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = _get_owned(db, voice_password_id, user.id)
    paths = [Path(sample.feature_path) for sample in (*item.templates, *item.command_templates)]
    db.delete(item)
    db.commit()
    for path in paths:
        path.unlink(missing_ok=True)


def _extract_upload(file: UploadFile, db: Session):
    config = get_algorithm_config(db)
    settings = get_settings()
    raw_path = None
    try:
        raw_path = save_upload(file.file.read(settings.max_upload_bytes + 1), file.filename)
        return process_audio(raw_path, config, simple_mode=True), config
    finally:
        if raw_path:
            raw_path.unlink(missing_ok=True)


@router.post("/{voice_password_id}/enroll", response_model=EnrollmentResponse)
def enroll(
    voice_password_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _serialize_write(db)
    item = _get_owned(db, voice_password_id, user.id)
    _require_simple(item)
    if item.is_active or len(item.templates) >= SAMPLE_COUNT:
        raise HTTPException(status_code=409, detail="Đã đủ 3 mẫu. Bạn có thể sang Két sắt để mở bằng giọng nói.")
    try:
        processed, _ = _extract_upload(file, db)
    except AudioValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)}) from exc
    try:
        speaker_embedding = extract_embedding(processed.samples)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Chưa có mô hình nhận dạng người nói. Chạy scripts/prepare_voice_models.py") from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Không tạo được đặc trưng người nói: {exc}") from exc

    feature_path = get_settings().template_dir / f"phrase{item.id}_{uuid.uuid4().hex}.npz"
    count = len(item.templates) + 1
    try:
        np.savez_compressed(feature_path, mfcc=processed.features, speaker_embedding=speaker_embedding)
        template = VoiceTemplate(
            voice_password_id=item.id, feature_path=str(feature_path),
            duration_seconds=processed.duration_seconds,
            quality={**processed.quality, "algorithm": PROFILE_VERSION},
        )
        db.add(template)
        if count == SAMPLE_COUNT:
            arrays = [load_template(sample.feature_path) for sample in item.templates] + [processed.features]
            item.threshold, _ = calibrate_phrase(arrays)
            speakers = [load_speaker_template(sample.feature_path) for sample in item.templates] + [speaker_embedding]
            item.speaker_threshold, _ = calibrate_speaker(speakers)
            item.is_active = True
            item.failed_attempts = 0
            item.locked_until = None
        db.commit()
        db.refresh(template)
    except ValueError as exc:
        db.rollback()
        feature_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        feature_path.unlink(missing_ok=True)
        raise

    return EnrollmentResponse(
        template_id=template.id, sample_count=count, required_count=SAMPLE_COUNT,
        ready_to_finalize=count == SAMPLE_COUNT, duration_seconds=round(processed.duration_seconds, 3),
        quality=processed.quality, is_active=item.is_active, threshold=item.threshold,
        speaker_threshold=item.speaker_threshold,
    )


@router.post("/{voice_password_id}/finalize", response_model=FinalizeResponse)
def finalize(voice_password_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = _get_owned(db, voice_password_id, user.id)
    _require_simple(item)
    if len(item.templates) != SAMPLE_COUNT:
        raise HTTPException(status_code=409, detail="Cần đọc cùng một câu đủ 3 lần")
    threshold, scores = calibrate_phrase([load_template(sample.feature_path) for sample in item.templates])
    speaker_threshold, _ = calibrate_speaker([load_speaker_template(sample.feature_path) for sample in item.templates])
    # Compatibility endpoint; enrollment already activates the third sample.
    if not item.is_active:
        item.threshold, item.speaker_threshold, item.is_active = threshold, speaker_threshold, True
        db.commit()
    return FinalizeResponse(voice_password_id=item.id, threshold=item.threshold, template_count=SAMPLE_COUNT, pairwise_scores=scores, speaker_threshold=item.speaker_threshold)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@router.post("/{voice_password_id}/verify", response_model=VerifyResponse)
def verify(
    voice_password_id: int,
    file: UploadFile = File(...),
    ground_truth: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    _serialize_write(db)
    item = _get_owned(db, voice_password_id, user.id)
    _require_simple(item)
    config = get_algorithm_config(db)
    now = datetime.now(timezone.utc)
    locked_until = _as_utc(item.locked_until)
    if locked_until and locked_until > now:
        raise HTTPException(status_code=429, detail={
            "message": "Bạn đã thử sai nhiều lần. Hãy đợi hết thời gian khóa tạm.",
            "code": "locked_out", "locked_until": locked_until.isoformat(),
        })
    if not item.is_active or item.threshold is None or item.speaker_threshold is None or len(item.templates) != SAMPLE_COUNT:
        raise HTTPException(status_code=409, detail="Hãy đọc cùng câu mật khẩu đủ 3 lần trước khi xác thực")

    score = None
    identity_score = None
    granted = False
    reason, message = "processing_error", "Không xử lý được bản ghi. Hãy thử lại."
    try:
        processed, _ = _extract_upload(file, db)
        score, _ = match_phrase(processed.features, [load_template(sample.feature_path) for sample in item.templates])
        if score <= item.threshold:
            identity_score = speaker_score(
                extract_embedding(processed.samples),
                [load_speaker_template(sample.feature_path) for sample in item.templates],
            )
        granted = score <= item.threshold and identity_score is not None and identity_score >= item.speaker_threshold
        reason = "matched" if granted else ("score_above_threshold" if score > item.threshold else "speaker_mismatch")
        message = (
            "Câu nói và người nói đều khớp. Két đang mở." if granted
            else f'Hãy đọc lại đúng câu “{item.phrase}”, với nhịp nói và khoảng cách micro như lúc đăng ký.'
            if reason == "score_above_threshold" else "Câu nói khớp nhưng đặc trưng người nói không đạt ngưỡng. Két vẫn khóa."
        )
    except AudioValidationError as exc:
        reason, message = exc.code, str(exc)
    except FileNotFoundError:
        logger.exception("Speaker model or enrolled sample missing")
        reason, message = "model_unavailable", "Thiếu mô hình hoặc mẫu giọng đã lưu. Két vẫn khóa; hãy kiểm tra backend/data/models."
    except Exception:
        logger.exception("MFCC/DTW verification failed")

    if granted:
        item.failed_attempts = 0
        item.locked_until = None
    elif reason in {"score_above_threshold", "speaker_mismatch"}:
        item.failed_attempts += 1
        if item.failed_attempts >= config.max_failed_attempts:
            item.failed_attempts = 0
            item.locked_until = datetime.now(timezone.utc) + timedelta(seconds=config.lockout_seconds)
            reason = "locked_out"
            message = f"Đã thử sai {config.max_failed_attempts} lần. Hãy đợi {config.lockout_seconds} giây."

    elapsed = round((time.perf_counter() - started) * 1000, 2)
    db.add(AuthenticationAttempt(
        voice_password_id=item.id, granted=granted, score=score, threshold=item.threshold,
        speaker_score=identity_score,
        dtw_score=score, dtw_threshold=item.threshold, processing_ms=elapsed, reason=reason,
        ground_truth=ground_truth if ground_truth in {"genuine", "impostor"} else None,
    ))
    db.commit()
    return VerifyResponse(
        granted=granted, score=round(score, 4) if score is not None else None,
        threshold=item.threshold, processing_ms=elapsed, reason=reason, message=message,
        auto_lock_seconds=config.auto_lock_seconds, lockout_until=_as_utc(item.locked_until),
        dtw_score=round(score, 4) if score is not None else None, dtw_threshold=item.threshold,
        dtw_matched=score <= item.threshold if score is not None else None,
        speaker_score=round(identity_score, 4) if identity_score is not None else None,
        speaker_threshold=item.speaker_threshold,
        speaker_matched=identity_score >= item.speaker_threshold if identity_score is not None else None,
    )
