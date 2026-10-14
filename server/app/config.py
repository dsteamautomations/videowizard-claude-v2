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
    DEFAULT_PROCEDURE_VERSION: str = '1'
    MAX_BODY_BYTES: int = 256 * 1024            # guard against blobs in the database; files go to storage
    MAX_QUOTE_CHARS: int = 2048
    APP_ORIGIN: str = 'http://localhost:8002'  # where operators open /connect and /runs
    CONNECT_MINUTES: int = 10
    SERVER_VERSION: str = '0.2.0'
    PLUGIN_MIN_VERSION: str = '0.1.0'


@lru_cache
def settings():
    return Settings()
