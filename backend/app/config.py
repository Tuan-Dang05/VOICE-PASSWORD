from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Voice Password API"
    database_url: str = "sqlite:///./data/voice_password.db"
    secret_key: str = "local-demo-secret-change-me"
    access_token_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    data_dir: Path = Path("data")
    model_dir: Path = Path("data/models")
    max_upload_bytes: int = 10 * 1024 * 1024
    speaker_model_url: str = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_eres2net_sv_en_voxceleb_16k.onnx"
    asr_model: str = "base"

    model_config = SettingsConfigDict(env_file="../.env", env_prefix="VOICE_", extra="ignore")

    @property
    def template_dir(self) -> Path:
        return self.data_dir / "templates"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
