from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    voice_passwords: Mapped[list[VoicePassword]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class VoicePassword(Base):
    __tablename__ = "voice_passwords"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    phrase: Mapped[str] = mapped_column(String(255))
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    speaker_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    config_version: Mapped[str] = mapped_column(String(30), default="mfcc13-v1")
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(back_populates="voice_passwords")
    templates: Mapped[list[VoiceTemplate]] = relationship(back_populates="voice_password", cascade="all, delete-orphan")
    command_templates: Mapped[list[VoiceCommandTemplate]] = relationship(back_populates="voice_password", cascade="all, delete-orphan")
    attempts: Mapped[list[AuthenticationAttempt]] = relationship(back_populates="voice_password", cascade="all, delete-orphan")


class VoiceTemplate(Base):
    __tablename__ = "voice_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    voice_password_id: Mapped[int] = mapped_column(ForeignKey("voice_passwords.id", ondelete="CASCADE"), index=True)
    feature_path: Mapped[str] = mapped_column(String(500), unique=True)
    duration_seconds: Mapped[float] = mapped_column(Float)
    quality: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    voice_password: Mapped[VoicePassword] = relationship(back_populates="templates")


class VoiceCommandTemplate(Base):
    __tablename__ = "voice_command_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    voice_password_id: Mapped[int] = mapped_column(ForeignKey("voice_passwords.id", ondelete="CASCADE"), index=True)
    feature_path: Mapped[str] = mapped_column(String(500), unique=True)
    speaker_score: Mapped[float] = mapped_column(Float)
    dtw_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    voice_password: Mapped[VoicePassword] = relationship(back_populates="command_templates")


class AuthenticationAttempt(Base):
    __tablename__ = "authentication_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    voice_password_id: Mapped[int] = mapped_column(ForeignKey("voice_passwords.id", ondelete="CASCADE"), index=True)
    granted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    speaker_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    dtw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dtw_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_ms: Mapped[float] = mapped_column(Float, default=0)
    reason: Mapped[str] = mapped_column(String(80), default="unknown")
    ground_truth: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    voice_password: Mapped[VoicePassword] = relationship(back_populates="attempts")


class AlgorithmConfig(Base):
    __tablename__ = "algorithm_configs"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    sample_rate: Mapped[int] = mapped_column(Integer, default=16000)
    n_mfcc: Mapped[int] = mapped_column(Integer, default=13)
    frame_ms: Mapped[float] = mapped_column(Float, default=25)
    hop_ms: Mapped[float] = mapped_column(Float, default=10)
    default_threshold: Mapped[float] = mapped_column(Float, default=0.65)
    auto_lock_seconds: Mapped[int] = mapped_column(Integer, default=8)
    max_failed_attempts: Mapped[int] = mapped_column(Integer, default=5)
    lockout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    min_duration_seconds: Mapped[float] = mapped_column(Float, default=1.0)
    max_duration_seconds: Mapped[float] = mapped_column(Float, default=5.0)
    min_rms: Mapped[float] = mapped_column(Float, default=0.01)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
