from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    app_name: str = "Oral Narrative Preservation System"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    allowed_origins: str = "*"

    storage_dir: str = "./storage"
    max_upload_size_mb: int = 500

    database_url: str = ""
    use_sqlite: bool = False
    sqlite_path: str = "./data/oral_narratives.db"

    redis_url: str = ""

    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_language: str = "en"
    whisper_compute_type: str = "int8"

    deepface_backend: str = "opencv"
    deepface_enforce_detection: bool = False

    log_level: str = "INFO"
    log_format: str = "console"

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    enable_gpu: bool = False

    enable_facial_analysis: bool = True
    enable_audio_analysis: bool = True
    enable_transcription: bool = True
    enable_multimodal_fusion: bool = True
    enable_faiss_indexing: bool = True

    async_processing: bool = True

    lightweight_mode: bool = False

    @property
    def cors_origins(self) -> List[str]:
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
