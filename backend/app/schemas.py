from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class VoicePasswordCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phrase: str = Field(min_length=2, max_length=255)


class VoicePasswordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phrase: str
    threshold: float | None
    speaker_threshold: float | None = None
    is_active: bool
    failed_attempts: int
    locked_until: datetime | None
    created_at: datetime
    template_count: int = 0
    command_template_count: int = 0
    requires_reenrollment: bool = False


class EnrollmentResponse(BaseModel):
    template_id: int
    sample_count: int
    required_count: int = 3
    ready_to_finalize: bool
    duration_seconds: float
    quality: dict
    is_active: bool = False
    threshold: float | None = None
    speaker_threshold: float | None = None


class FinalizeResponse(BaseModel):
    voice_password_id: int
    threshold: float
    template_count: int
    pairwise_scores: list[float]
    speaker_threshold: float | None = None


class VerifyResponse(BaseModel):
    granted: bool
    score: float | None
    threshold: float | None
    processing_ms: float
    reason: str
    auto_lock_seconds: int
    lockout_until: datetime | None = None
    transcript: str | None = None
    command_matched: bool | None = None
    speaker_matched: bool | None = None
    speaker_score: float | None = None
    speaker_threshold: float | None = None
    dtw_score: float | None = None
    dtw_threshold: float | None = None
    dtw_matched: bool | None = None
    message: str | None = None


class CalibrationResponse(BaseModel):
    accepted: bool
    score: float
    previous_threshold: float
    threshold: float
    transcript: str
    command_matched: bool
    reason: str
    command_samples: int
    command_ready: bool
    dtw_threshold: float | None = None


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voice_password_id: int
    voice_password_name: str
    granted: bool
    score: float | None
    speaker_score: float | None = None
    threshold: float | None
    dtw_score: float | None
    dtw_threshold: float | None
    processing_ms: float
    reason: str
    created_at: datetime


class StatsOut(BaseModel):
    total_attempts: int
    granted: int
    denied: int
    success_rate: float
    average_processing_ms: float
    p95_processing_ms: float
    far: float | None
    frr: float | None


class AlgorithmConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sample_rate: int
    n_mfcc: int
    frame_ms: float
    hop_ms: float
    default_threshold: float
    auto_lock_seconds: int
    max_failed_attempts: int
    lockout_seconds: int
    min_duration_seconds: float
    max_duration_seconds: float
    min_rms: float


class AlgorithmConfigUpdate(BaseModel):
    # Retained for existing clients; simple mode calibrates a threshold per profile.
    default_threshold: float | None = Field(default=None, ge=0.4, le=5)
    auto_lock_seconds: int = Field(ge=3, le=60)
    max_failed_attempts: int = Field(ge=1, le=20)
    lockout_seconds: int = Field(ge=10, le=3600)
    min_rms: float = Field(gt=0, lt=1)
