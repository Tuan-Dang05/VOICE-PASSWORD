import math

import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AuthenticationAttempt, User, VoicePassword
from ..schemas import AttemptOut, StatsOut

router = APIRouter(tags=["monitoring"])


@router.get("/auth-attempts", response_model=list[AttemptOut])
def list_attempts(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    granted: bool | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        select(AuthenticationAttempt, VoicePassword.name)
        .join(VoicePassword)
        .where(VoicePassword.user_id == user.id)
        .order_by(AuthenticationAttempt.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if granted is not None:
        query = query.where(AuthenticationAttempt.granted == granted)
    rows = db.execute(query).all()
    return [
        AttemptOut(
            id=attempt.id,
            voice_password_id=attempt.voice_password_id,
            voice_password_name=name,
            granted=attempt.granted,
            score=attempt.score,
            speaker_score=attempt.speaker_score,
            threshold=attempt.threshold,
            dtw_score=attempt.dtw_score,
            dtw_threshold=attempt.dtw_threshold,
            processing_ms=attempt.processing_ms,
            reason=attempt.reason,
            created_at=attempt.created_at,
        )
        for attempt, name in rows
    ]


@router.get("/stats", response_model=StatsOut)
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempts = db.scalars(
        select(AuthenticationAttempt)
        .join(VoicePassword)
        .where(VoicePassword.user_id == user.id)
    ).all()
    total = len(attempts)
    granted_count = sum(item.granted for item in attempts)
    latencies = [item.processing_ms for item in attempts]

    labeled = [item for item in attempts if item.ground_truth in {"genuine", "impostor"}]
    impostors = [item for item in labeled if item.ground_truth == "impostor"]
    genuine = [item for item in labeled if item.ground_truth == "genuine"]
    far = sum(item.granted for item in impostors) / len(impostors) if impostors else None
    frr = sum(not item.granted for item in genuine) / len(genuine) if genuine else None

    return StatsOut(
        total_attempts=total,
        granted=granted_count,
        denied=total - granted_count,
        success_rate=round(granted_count / total, 4) if total else 0,
        average_processing_ms=round(float(np.mean(latencies)), 2) if latencies else 0,
        p95_processing_ms=round(float(np.percentile(latencies, 95)), 2) if latencies else 0,
        far=round(far, 4) if far is not None else None,
        frr=round(frr, 4) if frr is not None else None,
    )
