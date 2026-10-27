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
    SERVER_VERSION: str = '0.55.0'
    PLUGIN_MIN_VERSION: str = '0.42.0'   # design/95 F5; design/97: the procedure gives the links `vw visuals status` prints from 0.42.0
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
    APIFY_TOKEN: SecretStr = SecretStr('')         # design/73 R3: Google Images through Apify; SK's account
    ANALYSIS_DEADLINE_SECONDS: int = 1800
    FFPROBE_EXECUTABLE: str = 'ffprobe'
    # design/65 B7: the visuals cap. No job records a money amount (tokens, characters, seconds only), so the ledger is computed from these prices in INR.
    # The defaults are the builder's estimates (21 Oct 2026); SK sets the real figures in server/.env (VW2_VISUALS_PRICE_IMAGE_INR, VW2_VISUALS_PRICE_VIDEO_INR_PER_S).
    VISUALS_PRICE_IMAGE_INR: float = 4.0           # a picture whose job has no tokens; with tokens the ledger uses OpenAI's rates (design/82 U2; measured ₹3 to ₹5 on 22 Oct)
    VISUALS_PRICE_VIDEO_INR_PER_S: float = 8.9     # one second of a generated take: Omni 1.1 Flash, 5,792 tokens a second at $17.50/M
    VISUALS_USD_INR: float = 88.0
    VISUALS_CAP_INR: float = 5000.0                # per film, unless the operator raises it with their words (SK, 21 Oct 2026, design/66)
    FFMPEG_EXECUTABLE: str = 'ffmpeg'


@lru_cache
def settings():
    return Settings()
