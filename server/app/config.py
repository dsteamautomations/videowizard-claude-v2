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
    DEFAULT_PROCEDURE_VERSION: str = '3'  # clip-log-v1 analysis; version 1 keeps the v1 evidence contract
    MAX_BODY_BYTES: int = 256 * 1024            # guard against blobs in the database; files go to storage
    PLAN_MAX_BODY_BYTES: int = 4 * 1024 * 1024   # defect 41: a visual plan is stored as a file, never in the database; VW-12's is about 280 KB
    MAX_QUOTE_CHARS: int = 2048
    APP_ORIGIN: str = 'http://localhost:8002'  # where operators open /connect and /runs
    CONNECT_MINUTES: int = 10
    SERVER_VERSION: str = '0.97.0'
    GEMINI_IMAGE_MODEL: str = 'gemini-3-pro-image'   # design/120: Nano Banana Pro as Google's docs name it; SK's exact id goes in server/.env (VW2_GEMINI_IMAGE_MODEL)
    GEMINI_IMAGE_SIZE: str = '2K'                     # design/120: 1K, 2K or 4K (uppercase K)
    GEMINI_IMAGE_USD: float = 0.134                   # design/120: Google's price per 1K/2K picture, 28 Oct 2026
    GEMINI_IMAGE_USD_4K: float = 0.24
    GEMINI_IMAGE_INPUT_USD: float = 0.0011             # per input picture (560 tokens)
    DRAWN_FIX_MODEL: str = 'gemini-3.8-flash'   # design/117 answer 3: Flash first; the Pro model is this one line
    PLUGIN_MIN_VERSION: str = '0.83.0'   # design/190 (13 Nov 2026): the treatment and the plan come on a card an older tool cannot show; before: design/188 (SK, 12 Nov 2026): the visuals decisions are taken in the chat with `vw visuals next` and `decide`; an older tool has neither. 0.81.0 design/186 (SK, 12 Nov 2026): the motion skill asks for a finish and `vw motion finish` takes it away; an older skill knows neither. 0.80.0 design/181, integration steps B to D (SK, 12 Nov 2026): an AI video shot is made with `vw guide`; an older tool has only the retired take commands. 0.79.0 design/180, integration step A (SK, 12 Nov 2026): a hand-in says how the file was made (`--made`); an older tool sends none and would be refused. 0.78.0 design/179 (SK, 12 Nov 2026): the motion skill reads the brief's Motion style, `vw motion-style`; an older skill would contradict the brief. 0.70.0 design/142 (SK, 2 Nov 2026: "YES change"): vw category, shape, colours, font, log and the second look's stills; design/95 F5; 0.66.0 design/130 (vw motion, the motion helpers, the guard's motion skill); 0.65.1 design/129 I (the guard only in the operator folder, the second look's record, downloads run again); 0.65.0 the design/126 build (ST2, ME1, VI1, OP1, U1-U7); G2 (SK, 31 Oct 2026, after defect 36): an older tool is told to update; 0.64.2 `vw visuals plan` (defect 37); 0.64.3 crops in image files (defect 38); 0.64.4 the sweep fixes W1-W13
    # storage: Supabase bucket in production; a local folder when STORAGE_LOCAL_DIR is set (tests, local dev)
    STORAGE_SUPABASE_URL: str = ''
    STORAGE_SUPABASE_SERVICE_KEY: SecretStr = SecretStr('')
    STORAGE_BUCKET: str = ''
    STORAGE_LOCAL_DIR: str = ''
    MEDIA_MAX_BYTES: int = 200 * 1024 * 1024
    ELEVENLABS_API_KEY: SecretStr = SecretStr('')
    GEMINI_API_KEY: SecretStr = SecretStr('')
    OPENAI_API_KEY: SecretStr = SecretStr('')
    GEMINI_API_KEYS: SecretStr = SecretStr('')   # design/114: more keys, comma-separated, used in turn after the single one
    OPENAI_API_KEYS: SecretStr = SecretStr('')
    WORKERS: int = 5  # one process per concurrent job; must be at least ANALYSIS_CAP plus room for voice, images, takes and renders
    ANALYSIS_CAP: int = 5  # concurrent Gemini analysis calls across all runs; 15 on the live VM since 18 Oct 2026 (design/35 row 29: 10 and 20 at once tested clean)
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
    # design/130: the HyperFrames motion route, installed on the VM in phase 0 (pinned CLI, its own HOME with the pinned Chrome, a pinned GSAP)
    MOTION_CLI: str = '/opt/vw2/hyperframes/node_modules/.bin/hyperframes'
    MOTION_HOME: str = '/opt/vw2/hyperframes/home'
    MOTION_GSAP: str = '/opt/vw2/hyperframes/node_modules/gsap/dist/gsap.min.js'
    MOTION_VERSION: str = '0.8.226'
    MOTION_TIMEOUT: int = 600   # seconds for one check, snapshot or render
    MOTION_CAP: int = 2         # drawn and motion jobs running at once across the workers (phase 0: under 1 GB each)
    # integration steps B to D (SK, 12 Nov 2026): the Blender guide. Installed on the VM on 12 Nov; software graphics, no graphics chip.
    BLENDER_BIN: str = '/opt/vw2/blender/blender-5.2.3-linux-x64/blender'
    GUIDE_TIMEOUT: int = 900            # seconds for one Blender call (a chunk of frames)
    GUIDE_CHUNK: int = 30               # frames a call; the job's claim is renewed between calls (about 4 s a frame on the VM)
    GUIDE_FRAME1_SAMPLES: int = 16      # the first frame again at full quality: the still is made from it and needs true shadows


@lru_cache
def settings():
    return Settings()
