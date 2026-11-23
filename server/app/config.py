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
    SERVER_VERSION: str = '0.126.0'
    GEMINI_IMAGE_MODEL: str = 'gemini-3-pro-image'   # design/120: Nano Banana Pro as Google's docs name it; SK's exact id goes in server/.env (VW2_GEMINI_IMAGE_MODEL)
    GEMINI_IMAGE_SIZE: str = '2K'                     # design/120: 1K, 2K or 4K (uppercase K)
    GEMINI_IMAGE_USD: float = 0.134                   # design/120: Google's price per 1K/2K picture, 28 Oct 2026
    GEMINI_IMAGE_USD_4K: float = 0.24
    GEMINI_IMAGE_INPUT_USD: float = 0.0011             # per input picture (560 tokens)
    DRAWN_FIX_MODEL: str = 'gemini-3.8-flash'   # design/117 answer 3: Flash first; the Pro model is this one line
    PLUGIN_MIN_VERSION: str = '0.108.0'   # release 0.126.0 / 0.108.0 (23 Nov 2026), films with no camera footage: the tool sends the run with every request for instructions and records the footage answer at intake; an older tool would be served a footage film's steps on a film with none. Before: release 0.125.0 / 0.107.0 (23 Nov 2026), the VW-25 set: the brief's served text now carries `{library_chapters}`, which an older tool leaves unfilled, and the served text names `vw master others` and a trim in seconds, which an older tool lacks; before: release 0.122.0 / 0.106.0 (22 Nov 2026), design/223: the new take process: a correction's route is sent with `vw guide corrections` and `vw guide correct`, which an older tool lacks, and an older tool still names the retired `vw-take-look` helper and `vw guide cause`; the page draws a version beside the video it was made from; before: release 0.121.0 / 0.105.0 (20 Nov 2026): layout B (the layout video flat with thin outlines, a purple back mark; the checker's helper text names them); before: release 0.120.0 / 0.104.0 (20 Nov 2026): releases 1 to 4 (the served text now names `vw motion render --wait`, `vw visuals propose --answers` and `vw defect --shot`, which an older tool lacks; 0.119.0 / 0.103.0 was never deployed): Claude's check with judgement (a line answered "na"), one click, the closed check box, step 7's order (a look with "na" is refused by an older server, and an older tool lacks the helper texts); before: release 0.118.0 / 0.102.0 (20 Nov 2026): step 7 on the page, the step 6 fix set, the page fixes: the page's link is given by `vw visuals page --shown` once the round is read back from the page (`after_round`), the loading note (`loading_write`), a publish to another link refused (`--new-page`), the takes of step 7 answered on the page: an older tool prints the link before the round is on the page. Before that, 0.101.0: design/221 (19 Nov 2026): the redo of step 6: `vw motion parts` (the shared parts), `vw motion upload --still` (the still end-frame), the closed page of step 6 (`closed`, the line of counts) and the finished drawing shown once (`show`), which an older tool does not know; before: 0.100.0, design/218 (18 Nov 2026): `vw font --sample` (the picture before the font question); before: design/217 (18 Nov 2026): step 6 on the page (an older page cannot draw the `pictures` layout) and Claude's check of its pictures (`vw visuals pictures --looks`, the `vw-picture-look` helper, rules.md sent with `vw motion upload`); `vw visuals fix` retired. Before: 0.98.0, design/216b (18 Nov 2026): `vw visuals round --things`, Claude's list of the things shown in each place, which the server now asks for before a place is made. Before: 0.97.0, design/216 (18 Nov 2026): the sets screen as on SK's trial (its words from the server under `layout.words.sets`), the page's `say` posted unchanged, the pictures announced before they are fetched (`vw visuals page --fetch`); an older page cannot draw the screen and an older tool passes no `say`. Before: 0.96.0, design/215 (18 Nov 2026): the references page renders the words the server sends and sends the new answer "correct_all"; an older page would show the older words and its own labels. Before: 0.95.0, design/214 (18 Nov 2026): Claude checks the sets: a look at a set must answer every line of each picture's check list, which only the new helper file and instructions tell the looker to send; an older tool's look carries no line answers and would be refused; before: 0.94.0, design/213 (17 Nov 2026): step 2 of the references in its new layout: the round carries `layout` of kind `sets` and each set its case and its buttons, which only the new page file draws and sends; a look at a set with notes must carry `chose` and `aside`, and a look at a person's frame `face`, which only the new helper files and tool send; before: 0.93.0 design/212 (17 Nov 2026): step 1 of the references in its new layout: the round carries `layout`, which the new tool writes into the round file, and each thing carries its case and its buttons (`use`, `set`, `fix`), which only the new page file draws and sends; before: 0.92.0 design/211 (17 Nov 2026): the references step rebuilt: a new round needs the new tool's commands (`vw visuals digest`, `trial`, `look`, `round --looks`, `--rest`, `--rewrite`), the new page file (the proposals, the groups, a picture answered on its own, the check and the notes) and the two helpers (`vw-reference-finder`, `vw-set-look`); before: 0.91.0 design/210 (16 Nov 2026): the reference drawings and the reference round are answered on the page with pictures, which the new tool sends and the new page file draws; before: 0.90.0 design/209 (16 Nov 2026): the drawings and the materials are approved on the page, whose file must draw them, and the join after a proposal needs the new tool; before: 0.89.0 design/207 (16 Nov 2026): the helper's checklist, the guide skill (any kind of shot, a thing on a path) and the commands `vw visuals likeness` and `vw visuals cap` are in the plugin; an older tool still asks for the retired reuse approval; before: 0.88.0 design/206 (16 Nov 2026): the plan is answered on the page, whose file must draw a gap's table; an older tool's page shows the gaps without their shots; before: 0.87.0 design/205 (15 Nov 2026): the Direction alone first and the motion style on the page: an older tool's own line after a draft sends the assistant to the card; before: 0.86.0 design/204 (15 Nov 2026): the treatment is answered on a Claude artifact page, which needs `vw visuals page`; design/200 (14 Nov 2026): a thing's drawing set and the shot's drawing are sent and approved with the new tool; design/192 and 194 (14 Nov 2026): the intake's --category, vw last, vw next inside the voice stage and the page ticket, which an older tool does not know; before: 0.84.0 design/193 (14 Nov 2026): the pieces files carry each piece's own lines, which an older tool does not write; before: design/190 (13 Nov 2026): the treatment and the plan come on a card an older tool cannot show; before: design/188 (SK, 12 Nov 2026): the visuals decisions are taken in the chat with `vw visuals next` and `decide`; an older tool has neither. 0.81.0 design/186 (SK, 12 Nov 2026): the motion skill asks for a finish and `vw motion finish` takes it away; an older skill knows neither. 0.80.0 design/181, integration steps B to D (SK, 12 Nov 2026): an AI video shot is made with `vw guide`; an older tool has only the retired take commands. 0.79.0 design/180, integration step A (SK, 12 Nov 2026): a hand-in says how the file was made (`--made`); an older tool sends none and would be refused. 0.78.0 design/179 (SK, 12 Nov 2026): the motion skill reads the brief's Motion style, `vw motion-style`; an older skill would contradict the brief. 0.70.0 design/142 (SK, 2 Nov 2026: "YES change"): vw category, shape, colours, font, log and the second look's stills; design/95 F5; 0.66.0 design/130 (vw motion, the motion helpers, the guard's motion skill); 0.65.1 design/129 I (the guard only in the operator folder, the second look's record, downloads run again); 0.65.0 the design/126 build (ST2, ME1, VI1, OP1, U1-U7); G2 (SK, 31 Oct 2026, after defect 36): an older tool is told to update; 0.64.2 `vw visuals plan` (defect 37); 0.64.3 crops in image files (defect 38); 0.64.4 the sweep fixes W1-W13
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
    VISUALS_PRICE_VIDEO_360P_INR_PER_S: float = 2.97   # design/223 (SK, 22 Nov 2026: "the price by size"): one second of a 360p take, a third of the 720p second (about a third of its video tokens); corrected from the provider's own token count of the first real 360p take
    VISUALS_USD_INR: float = 88.0
    VISUALS_STILL_SHARE: float = 0.10              # design/202: warn when still pictures pass this share of the film (VW-21's 13.5 % would have warned); SK's figure
    VISUALS_CAP_INR_PER_MIN: float = 750.0         # design/207 (SK, 16 Nov 2026): a new film's cost limit follows its length, this much a minute of film
    VISUALS_CAP_FLOOR_INR: float = 1500.0          # design/207: the lowest limit a film gets, however short
    VISUALS_CAP_INR: float = 5000.0                # the older figure, kept for a film begun before design/207 whose session holds no limit; the owner sets another figure for one film with `vw visuals cap`
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
    GUIDE_VIDEO_LOOK: str = 'flat'      # layout B (SK, 20 Nov 2026): the layout video and the check frames in Workbench, flat colours, thin black outlines; 'eevee' renders them as before


@lru_cache
def settings():
    return Settings()
