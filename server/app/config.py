from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='VW2_', env_file=Path(__file__).resolve().parents[1] / '.env', extra='ignore')
    DATABASE_URL: str = ''                      # direct Postgres connection string (Supabase pooler or local)
    SHARED_SUPABASE_URL: str = ''               # employee directory (same as v1)
    SHARED_SUPABASE_SERVICE_KEY: SecretStr = SecretStr('')
    APP_ID: str = ''
    SESSION_HOURS: int = 168
    DEFAULT_PROCEDURE_VERSION: str = '2'  # clip-log-v1 analysis; version 1 keeps the v1 evidence contract
    MAX_BODY_BYTES: int = 256 * 1024            # guard against blobs in the database; files go to storage
    MAX_QUOTE_CHARS: int = 2048
    APP_ORIGIN: str = 'http://localhost:8002'  # where operators open /connect and /runs
    CONNECT_MINUTES: int = 10
    SERVER_VERSION: str = '0.19.6'
    PLUGIN_MIN_VERSION: str = '0.1.0'
    # storage: Supabase bucket in production; a local folder when STORAGE_LOCAL_DIR is set (tests, local dev)
    STORAGE_SUPABASE_URL: str = ''
    STORAGE_SUPABASE_SERVICE_KEY: SecretStr = SecretStr('')
    STORAGE_BUCKET: str = ''
    STORAGE_LOCAL_DIR: str = ''
    MEDIA_MAX_BYTES: int = 200 * 1024 * 1024
    ELEVENLABS_API_KEY: SecretStr = SecretStr('')
    GEMINI_API_KEY: SecretStr = SecretStr('')
    OPENAI_API_KEY: SecretStr = SecretStr('')
    WORKERS: int = 5  # one process per concurrent job; must be at least ANALYSIS_CAP plus room for voice, images, takes and renders
    ANALYSIS_CAP: int = 5  # concurrent Gemini analysis calls across all runs; 15 on the live VM since 18 Oct 2026 (design/35 row 29: 10 and 20 at once tested clean)
    HF_API_KEY: SecretStr = SecretStr('')
    ANALYSIS_DEADLINE_SECONDS: int = 1800
    FFPROBE_EXECUTABLE: str = 'ffprobe'
    FFMPEG_EXECUTABLE: str = 'ffmpeg'


@lru_cache
def settings():
    return Settings()
