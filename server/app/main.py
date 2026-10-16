"""VideoWizard v2 server. Routes are thin: auth, body checks, one transaction, delegate to core."""
import json
from typing import Any, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import analysis_jobs, auth, connect, core, elevenlabs, files, jobs, planning_stage, visuals_stage, web, worker
from .stage2 import stage as stage2
from .stage3 import assembly as stage3, delivery as deliv
from .stage3 import assembly as stage3, delivery as deliv
from .stage3 import assembly as stage3, delivery as deliv
from .storage import storage
from .config import settings
from .db import connect as db_connect, migrate
from .errors import Problem


class Response(JSONResponse):
    def render(self, content):
        return json.dumps(core.jsonable(content)).encode()


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_app):
    if settings().DATABASE_URL:
        migrate()
    yield


app = FastAPI(title='VideoWizard v2', default_response_class=Response, lifespan=lifespan)
app.mount('/static', StaticFiles(directory=str(Path(__file__).resolve().parent / 'static')), name='static')
app.include_router(web.router)
app.include_router(files.router)


@app.exception_handler(Problem)
def problem(request, exc: Problem):
    return Response({'code': exc.code, 'message': exc.message, **exc.extra}, status_code=exc.status)


def db():
    with db_connect() as conn:
        yield conn


DB = Depends(db)
User = auth.User


def size_guard(request: Request):
    if int(request.headers.get('content-length') or 0) > settings().MAX_BODY_BYTES:
        raise Problem(413, 'BODY_TOO_LARGE', 'Store large content as a file; the database keeps only hashes and a short summary.')


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Login(Strict):
    username: str
    password: str
    kind: Literal['browser', 'executor'] = 'browser'


class Write(Strict):
    request_id: UUID


class NewRun(Write):
    client: str = Field(min_length=1, max_length=200)
    title: str = ''
    procedure_version: str | None = None


class FileRef(Strict):
    name: str
    key: str
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    bytes: int = Field(ge=0)
    receipt: bool = False
    location: Literal['local', 'storage'] = 'local'


class Sign(Write):
    stage: str
    name: str


class Receipt(Write):
    key: str
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    bytes: int = Field(ge=0)


class Job(Write):
    stage: str
    provider: Literal['elevenlabs']
    request: dict[str, Any]


class Resolve(Write):
    note: str | None = None


class AnalysisPolicy(Write):
    camera_audio: Literal['allowed', 'excluded'] | None = None
    show_speaker_video: bool | None = None
    waived_risk_flags: list[str] | None = None
    note: str = ''


class AnalysisStart(Write):
    camera_audio: Literal['allowed', 'excluded']
    understand_audio: bool = True
    film_type: str = ''
    exclude: list[str] = []
    again: bool = False


class Note(Write):
    note: str | None = None


class PlanningPrepare(Write):
    fps: int = Field(ge=1, le=120)
    resolution: list[int] = Field(min_length=2, max_length=2)
    source_audio_in_output: Literal['none', 'ambient', 'speech', 'both'] = 'none'
    visible_speaking: Literal['allow', 'avoid'] = 'avoid'
    film_type: str = ''


class PlanningScenes(Write):
    scenes: list[dict[str, Any]]
    quote: str = Field(min_length=1)


class PlanningPlan(Write):
    plan: dict[str, Any]
    quote: str | None = None


class PlanningAnswer(Write):
    question_id: str
    answer: str | None = None
    quote: str | None = None
    check: dict[str, Any] | None = None


class PlanningFrames(Write):
    question_id: str
    source_id: str
    times: list[float]


class PlanningInspect(Write):
    question_ids: list[str]


class PlanningReview(Write):
    response_digest: str
    fields: list[dict[str, Any]]
    excluded_observation_ids: list[str] = []


class PlanningFinalize(Write):
    assessment: dict[str, Any]
    quote: str = Field(min_length=1)


class VisualPlan(Write):
    plan: dict[str, Any]


class VisualSelect(Write):
    choices: dict[str, str]


class VisualAccept(Write):
    gap_ids: list[str]
    quote: str = Field(min_length=1)


class ReferenceAdd(Write):
    element_id: str
    name: str
    kind: Literal['frame', 'supplied', 'web']
    subject: str
    content_base64: str = ''
    source_media_id: str | None = None
    requested_s: float | None = None
    source_url: str = ''
    selection_reply: str = ''


class ImageGenerate(Write):
    element_id: str
    name: str
    kind: Literal['isolated', 'sheet', 'keyframe']
    subject: str
    prompt: str = Field(min_length=1, max_length=8000)
    parents: list[str] = []
    model: str | None = None
    size: str | None = None
    quality: str | None = None


class ReferenceApprove(Write):
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    quote: str = Field(min_length=1)


class BindBody(Write):
    shot_id: str
    references: dict[str, list[str]]
    subject_selectors: dict[str, dict[str, str]] = {}
    quote: str = Field(min_length=1)


class GeneratorBody(Write):
    shot_id: str
    provider: str
    model: str


class PrepareTake(Write):
    shot_id: str
    start_image: str
    end_image: str | None = None
    motion_prompt: str = Field(min_length=1, max_length=16000)
    subject_reconciliation: dict[str, str]
    continuity_notes: str = ''
    duration_seconds: int | None = None
    aspect_ratio: Literal['16:9', '9:16'] = '16:9'
    resolution: Literal['720p', '1080p'] | None = None


class ShotBody(Write):
    shot_id: str


class TakeReview(Write):
    job_id: UUID
    decision: Literal['accepted', 'rejected']
    notes: str = Field(min_length=1)
    timing_notes: str = ''
    quote: str = Field(min_length=1)


class TakeSelect(Write):
    job_id: UUID
    quote: str = Field(min_length=1)


class AssetBody(Write):
    shot_id: str
    key: str
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    bytes: int = Field(ge=1)
    kind: Literal['movie', 'still']
    quote: str = Field(min_length=1)


class GapBody(Write):
    gap_id: str
    quote: str = Field(min_length=1)


class Quote(Write):
    quote: str = Field(min_length=1)


class OptionsDoc(Write):
    document: dict[str, Any]


class ScenesBody(Write):
    document: dict[str, Any]
    quote: str = ''   # the stage refuses an empty one with a readable message


class FramesBody(Write):
    sub_clip_id: str
    edge: Literal['in', 'out'] = 'in'


class RenderBody(Write):
    film: Literal['review', 'master']


class DecideBody(Write):
    slide: int | None = None
    option_number: int | None = None   # before design/21; the same as the slide number when a version has no decision or blank slides
    action: Literal['KEEP', 'REJECT', 'KEEP_WITH_EDIT', 'DROP']
    note: str = ''
    edit: str | None = None


class RuleBody(Write):
    rule: str = Field(min_length=1, max_length=2000)


class ChooseBody(Write):
    shot_id: str
    offset_frames: int = 0
    end_policy: Literal['trim', 'hold_last'] = 'trim'
    accept_as_is: bool = False


class StabBody(Write):
    sub_clip_id: str
    choice: Literal['leave', 'ffmpeg']


class ReviewBody(Write):
    decision: Literal['accepted', 'changes', 'rejected']
    notes: str = ''
    frame_notes: list[dict[str, Any]] = []
    quote: str = Field(min_length=1)


class ReserveBody(Write):
    machine: str = Field(min_length=1)
    authorization: str = ''


class MarkBody(Write):
    machine: str = Field(min_length=1)
    state: Literal['dispatched', 'reported', 'closed']
    report: dict[str, Any] | None = None
    note: str = ''


class ChooseBody(Write):
    shot_id: str
    offset_frames: int = 0
    end_policy: Literal['trim', 'hold_last'] = 'trim'
    accept_as_is: bool = False


class StabBody(Write):
    sub_clip_id: str
    choice: Literal['leave', 'ffmpeg']


class ReviewBody(Write):
    decision: Literal['accepted', 'changes', 'rejected']
    notes: str = ''
    frame_notes: list[dict[str, Any]] = []
    quote: str = Field(min_length=1)


class ReserveBody(Write):
    machine: str = Field(min_length=1)
    authorization: str = ''


class MarkBody(Write):
    machine: str = Field(min_length=1)
    state: Literal['dispatched', 'reported', 'closed']
    report: dict[str, Any] | None = None
    note: str = ''


class ChooseBody(Write):
    shot_id: str
    offset_frames: int = 0
    end_policy: Literal['trim', 'hold_last'] = 'trim'
    accept_as_is: bool = False


class StabBody(Write):
    sub_clip_id: str
    choice: Literal['leave', 'ffmpeg']


class ReviewBody(Write):
    decision: Literal['accepted', 'changes', 'rejected']
    notes: str = ''
    frame_notes: list[dict[str, Any]] = []
    quote: str = Field(min_length=1)


class ReserveBody(Write):
    machine: str = Field(min_length=1)
    authorization: str = ''


class MarkBody(Write):
    machine: str = Field(min_length=1)
    state: Literal['dispatched', 'reported', 'closed']
    report: dict[str, Any] | None = None
    note: str = ''


class LibraryAdd(Strict):
    public_owner_id: str
    voice_id: str


class Output(Write):
    stage: str
    unit: str | None = None
    files: list[FileRef] = []
    summary: dict[str, Any] = {}
    accepted_quote: str | None = None


class Revise(Write):
    stage: str
    unit: str | None = None
    confirm_quote: str | None = None


class Decide(Write):
    stage: str
    unit: str | None = None
    decision: Literal['retry', 'revise', 'defect', 'stop']
    note: str | None = None


class Adopt(Write):
    version: str


class Claim(Write):
    machine: str = Field(min_length=1, max_length=120)


class ConnectBegin(Strict):
    request_id: UUID
    token_hash: str = Field(pattern=r'^[0-9a-f]{64}$')


class ConnectApprove(Strict):
    code: str = Field(min_length=9, max_length=9)


class Defect(Write):
    stage: str | None = None
    error: str
    log_excerpt: str | None = None


def body_dict(model):
    d = model.model_dump(mode='json')
    d['request_id'] = str(model.request_id)
    return d


# ---------- auth ----------

@app.post('/api/auth/login')
def login(body: Login):
    return Response(auth.sign_in(body.username, body.password, body.kind))


@app.post('/api/auth/logout')
def logout(user=User):
    auth.sign_out(user)
    return {'ok': True}


@app.get('/api/auth/me')
def me(user=User):
    return Response({k: user[k] for k in ('id', 'name', 'role', 'kind')})


# ---------- runs ----------

@app.post('/api/runs', status_code=201)
def create_run(body: NewRun, user=User, conn=DB):
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (201, dict(core.create_run(conn, user, body.title, body.client, body.procedure_version))))
    return Response(resp, status_code=status)


@app.get('/api/clients')
def clients(search: str = '', user=User):
    term = search.strip().lower()
    return Response([r for r in auth.client_directory() if not term or term in r['client_name'].lower()][:50])


@app.get('/api/runs')
def list_runs(user=User, conn=DB):
    return Response(core.list_runs(conn, user))


@app.get('/api/runs/{run_id}')
def get_run(run_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    return Response({**run, 'outputs': core.current_outputs(conn, run_id), 'attempts': list(core.attempts_for(conn, run_id).values()), 'next': core.next_for(conn, run)})


@app.get('/api/runs/{run_id}/next')
def get_next(run_id: UUID, user=User, conn=DB):
    return Response(core.next_for(conn, core.load_run(conn, user, run_id)))


@app.get('/api/runs/{run_id}/stages/{stage}')
def view_stage(run_id: UUID, stage: str, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    core._stage(core.stage_table(run['procedure_version']), stage)
    rows = conn.execute('select * from vw2_stage_outputs where run_id=%s and stage=%s order by created_at', (run_id, stage)).fetchall()
    return Response({'stage': stage, 'outputs': rows})


@app.post('/api/runs/{run_id}/output', status_code=201, dependencies=[Depends(size_guard)])
def post_output(run_id: UUID, body: Output, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (201, dict(core.output(conn, user, run, body_dict(body)))))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/revise')
def post_revise(run_id: UUID, body: Revise, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, core.revise(conn, user, run, body.stage, body.unit, body.confirm_quote)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/decide')
def post_decide(run_id: UUID, body: Decide, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, core.decide(conn, user, run, body.stage, body.unit, body.decision, body.note)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/adopt')
def post_adopt(run_id: UUID, body: Adopt, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, dict(core.adopt(conn, user, run, body.version))))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/close')
def post_close(run_id: UUID, body: Write, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, _close_with_retention(conn, user, run)))
    return Response(resp, status_code=status)


def _close_with_retention(conn, user, run):
    outputs = core.current_outputs(conn, run['id'])
    closed = dict(core.close(conn, user, run))
    closed['retention'] = deliv.retention(conn, storage(), run, outputs)
    return closed


@app.post('/api/runs/{run_id}/defects', status_code=201)
def post_defect(run_id: UUID, body: Defect, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (201, core.file_defect(conn, user, run, body.stage, body.error, body.log_excerpt)))
    return Response(resp, status_code=status)


# ---------- files ----------

@app.post('/api/runs/{run_id}/files/sign')
def post_sign(run_id: UUID, body: Sign, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    return Response(files.sign(conn, user, run, body.stage, body.name))


@app.post('/api/runs/{run_id}/files/receipt')
def post_receipt(run_id: UUID, body: Receipt, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    return Response(files.receipt(conn, user, run, body.key, body.sha256, body.bytes))


# ---------- voice catalog (read-only provider access; no run needed) ----------

@app.get('/api/voice/catalog')
def voice_catalog(user=User, scope: str = 'account', search: str = '', cursor: str = '', language: str = '', accent: str = '',
                  gender: str = '', age: str = '', use_cases: str = '', high_quality: bool = False):
    q = {'scope': scope, 'search': search[:200], 'cursor': cursor[:1000], 'language': language[:30], 'accent': accent[:80], 'gender': gender, 'age': age,
         'use_cases': [u for u in use_cases.split(',') if u in elevenlabs.USE_CASES], 'high_quality': high_quality}
    return Response(elevenlabs.discover(elevenlabs.ElevenLabs(), q))


@app.get('/api/voice/models')
def voice_models(user=User):
    return Response({'models': elevenlabs.ElevenLabs().models(), 'default_model': elevenlabs.DEFAULT_MODEL, 'default_settings': elevenlabs.DEFAULT_SETTINGS})


@app.get('/api/voice/preview/{voice_id}')
def voice_preview(voice_id: str, user=User):
    voice = elevenlabs.ElevenLabs().voice(voice_id)
    url = voice.get('preview_url') or ''
    if not url.startswith('https://'):
        raise Problem(404, 'NO_PREVIEW', 'No catalog preview is available for this voice.')
    return Response({'voice_id': voice_id, 'name': voice['name'], 'url': url})


@app.post('/api/voice/library-add')
def voice_library_add(body: LibraryAdd, user=User):
    return Response(elevenlabs.add_library_voice(elevenlabs.ElevenLabs(), body.public_owner_id, body.voice_id))


# ---------- jobs ----------

@app.post('/api/runs/{run_id}/jobs', status_code=201)
def post_job(run_id: UUID, body: Job, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)
    nxt = core.next_for(conn, run)
    if nxt['stage'] != body.stage:
        raise Problem(409, 'NOT_ALLOWED', f"The next step is {nxt['stage']!r}, not {body.stage!r}.", next=nxt)
    outputs = core.current_outputs(conn, run['id'])
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (201, dict(jobs.submit_voice(conn, user, run, outputs, body.request, body.request_id))))
    return Response(resp, status_code=status)


@app.get('/api/runs/{run_id}/jobs')
def list_jobs(run_id: UUID, user=User, conn=DB, stage: str | None = None):
    run = core.load_run(conn, user, run_id)
    sql = 'select id, stage, unit, provider, status, request, result, error, cost, attempt, created_at, updated_at from vw2_jobs where run_id=%s'
    rows = conn.execute(sql + (' and stage=%s' if stage else '') + ' order by created_at', (run['id'], stage) if stage else (run['id'],)).fetchall()
    for r in rows:
        r['request'] = {k: v for k, v in r['request'].items() if k != 'text'}
    return Response(rows)


@app.get('/api/runs/{run_id}/jobs/{job_id}')
def get_job(run_id: UUID, job_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    row = conn.execute('select * from vw2_jobs where id=%s and run_id=%s', (job_id, run['id'])).fetchone()
    if not row:
        raise Problem(404, 'NOT_FOUND', 'Job not found.')
    return Response(row)


@app.post('/api/runs/{run_id}/jobs/{job_id}/recover')
def recover_job(run_id: UUID, job_id: UUID, body: Write, user=User, conn=DB):
    """Reconcile a submission_unknown voice job from provider history; never synthesizes."""
    run = core.load_run(conn, user, run_id, lock=True)
    row = conn.execute('select * from vw2_jobs where id=%s and run_id=%s', (job_id, run['id'])).fetchone()
    journaled = row and row['status'] == 'failed' and any((worker.SPOOL / f"{job_id}{suffix}").is_file() for suffix in ('.response.json', '.mp3'))
    if journaled:
        # The paid response is retained on this server: re-process it (e.g. after a validation rule change). No synthesis.
        message = 'Re-processing the retained response; no new synthesis.'
    elif not row or row['status'] != 'submission_unknown':
        raise Problem(409, 'NOT_ALLOWED', 'Only a job with an unknown provider outcome, or a failed job whose response is retained, can be recovered.')
    else:
        worker.recover_voice(row)
        message = 'Recovered from provider history; the worker will store it.'
    conn.execute("update vw2_jobs set status='storage_pending', lease_until=null, error=null, updated_at=now() where id=%s", (job_id,))
    return Response({'id': str(job_id), 'status': 'storage_pending', 'message': message})


@app.post('/api/runs/{run_id}/jobs/{job_id}/resolve')
def resolve_job(run_id: UUID, job_id: UUID, body: Resolve, user=User, conn=DB):
    """Set aside a job whose outcome is unknown after the operator checked the provider account; lets a new job start."""
    run = core.load_run(conn, user, run_id, lock=True)
    row = conn.execute('select * from vw2_jobs where id=%s and run_id=%s', (job_id, run['id'])).fetchone()
    if not row or row['status'] not in ('submission_unknown', 'storage_pending'):
        raise Problem(409, 'NOT_ALLOWED', 'Only an unresolved job can be set aside.')
    conn.execute("update vw2_jobs set status='failed', error=%s, lease_until=null, updated_at=now() where id=%s", ('Set aside by operator: ' + (body.note or ''), job_id))
    return Response({'id': str(job_id), 'status': 'failed'})


# ---------- analysis ----------

def _analysis_run(conn, user, run_id, stage_check=True):
    run = core.load_run(conn, user, run_id, lock=True)
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    if stage_check:
        nxt = core.next_for(conn, run)
        if nxt['stage'] != 'analysis':
            raise Problem(409, 'NOT_ALLOWED', f"The next step is {nxt['stage']!r}, not 'analysis'.", next=nxt)
    return run


@app.post('/api/runs/{run_id}/analysis/start', status_code=201)
def analysis_start(run_id: UUID, body: AnalysisStart, user=User, conn=DB):
    run = _analysis_run(conn, user, run_id)
    outputs = core.current_outputs(conn, run['id'])
    policy = {'camera_audio': body.camera_audio, 'understand_audio': body.understand_audio, 'film_type': body.film_type, 'exclude': body.exclude}
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (201, analysis_jobs.start(conn, user, run, outputs, policy, body.again)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/analysis/policy', status_code=201)
def analysis_policy(run_id: UUID, body: AnalysisPolicy, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    outputs = core.current_outputs(conn, run['id'])
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (201, analysis_jobs.repolicy(conn, user, run, outputs, {'camera_audio': body.camera_audio, 'show_speaker_video': body.show_speaker_video, 'waived_risk_flags': body.waived_risk_flags, 'note': body.note})))
    return Response(resp, status_code=status)


@app.get('/api/runs/{run_id}/analysis')
def analysis_status(run_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    return Response(analysis_jobs.status(conn, run, core.current_outputs(conn, run['id'])))


@app.post('/api/runs/{run_id}/analysis/{unit}/{action}')
def analysis_control(run_id: UUID, unit: str, action: Literal['retry', 'recover', 'resolve', 'exclude'], body: Note, user=User, conn=DB):
    run = _analysis_run(conn, user, run_id)
    fn = {'retry': lambda: analysis_jobs.retry(conn, user, run, unit, body.note), 'recover': lambda: analysis_jobs.recover(conn, user, run, unit),
          'resolve': lambda: analysis_jobs.resolve(conn, user, run, unit, body.note), 'exclude': lambda: dict(analysis_jobs.exclude(conn, user, run, unit, body.note))}[action]
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, fn()))
    return Response(resp, status_code=status)


@app.post('/api/jobs/{job_id}/release')
def job_release(job_id: UUID, body: Write, user=User, conn=DB):
    if not core.is_admin(user):
        raise Problem(404, 'NOT_FOUND', 'Not found.')
    analysis_jobs.release(conn, job_id)
    return Response({'id': str(job_id), 'released': True})


# ---------- planning ----------

def _planning_run(conn, user, run_id):
    run = core.load_run(conn, user, run_id, lock=True)
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    nxt = core.next_for(conn, run)
    if nxt['stage'] != 'planning':
        raise Problem(409, 'NOT_ALLOWED', f"The next step is {nxt['stage']!r}, not 'planning'.", next=nxt)
    return run


@app.get('/api/runs/{run_id}/planning')
def planning_status(run_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)   # it saves the session (ticket 9)
    return Response(planning_stage.status(conn, storage(), run))


@app.get('/api/runs/{run_id}/planning/review-input')
def planning_review_input(run_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    return Response(planning_stage.review_input(conn, storage(), run))


@app.get('/api/runs/{run_id}/planning/handoff')
def planning_handoff(run_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    out = next((o for o in core.current_outputs(conn, run['id']) if o['stage'] == 'planning'), None)
    if not out:
        raise Problem(409, 'EXECUTION_NOT_READY', 'Planning is not finalized.')
    ref = next(f for f in out['files'] if f['name'] == 'handoff.json')
    return Response(planning_stage.load_json(storage(), ref['key']))


@app.post('/api/runs/{run_id}/planning/prepare')
def planning_prepare(run_id: UUID, body: PlanningPrepare, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    outputs = core.current_outputs(conn, run['id'])
    settings_ = {'fps': body.fps, 'resolution': body.resolution, 'source_audio_in_output': body.source_audio_in_output, 'visible_speaking': body.visible_speaking, 'film_type': body.film_type}
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, planning_stage.prepare(conn, storage(), user, run, outputs, settings_)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/planning/scenes')
def planning_scenes(run_id: UUID, body: PlanningScenes, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, planning_stage.set_scenes(conn, storage(), user, run, body.scenes, body.quote)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/planning/check', dependencies=[Depends(size_guard)])
def planning_check(run_id: UUID, body: PlanningPlan, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    return Response(planning_stage.check(storage(), run, body.plan))


@app.post('/api/runs/{run_id}/planning/draft', dependencies=[Depends(size_guard)])
def planning_draft(run_id: UUID, body: PlanningPlan, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, planning_stage.draft(conn, storage(), user, run, body.plan, body.quote)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/planning/revise', dependencies=[Depends(size_guard)])
def planning_revise(run_id: UUID, body: PlanningPlan, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, planning_stage.revise(conn, storage(), user, run, body.plan, body.quote)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/planning/answer')
def planning_answer(run_id: UUID, body: PlanningAnswer, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    if body.check is not None:
        fn = lambda: (200, planning_stage.answer_mechanical(storage(), user, run, body.question_id, body.check))
    else:
        if not (body.answer or '').strip() or not (body.quote or '').strip():
            raise Problem(422, 'PLANNING_CONTRACT', 'A user answer needs answer and the operator reply as quote.')
        fn = lambda: (200, planning_stage.answer_user(storage(), user, run, body.question_id, body.answer, body.quote))
    status, resp = core.with_receipt(conn, user, body_dict(body), fn)
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/planning/frames')
def planning_frames(run_id: UUID, body: PlanningFrames, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, planning_stage.extract_frames(storage(), user, run, body.question_id, body.source_id, body.times)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/planning/inspect', status_code=201)
def planning_inspect(run_id: UUID, body: PlanningInspect, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (201, planning_stage.inspect(conn, storage(), user, run, body.question_ids)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/planning/review')
def planning_review(run_id: UUID, body: PlanningReview, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    doc = {'response_digest': body.response_digest, 'fields': body.fields, 'excluded_observation_ids': body.excluded_observation_ids}
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, planning_stage.review_answers(conn, storage(), user, run, doc)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/planning/ledger')
def planning_ledger(run_id: UUID, body: Write, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, planning_stage.ledger(conn, storage(), user, run)))
    return Response(resp, status_code=status)


@app.post('/api/runs/{run_id}/planning/finalize', status_code=201)
def planning_finalize(run_id: UUID, body: PlanningFinalize, user=User, conn=DB):
    run = _planning_run(conn, user, run_id)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (201, planning_stage.finalize(conn, storage(), user, run, body.assessment, body.quote)))
    return Response(resp, status_code=status)


# ---------- visuals ----------

def _visuals_run(conn, user, run_id):
    run = core.load_run(conn, user, run_id, lock=True)
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    nxt = core.next_for(conn, run)
    if nxt['stage'] != 'visuals':
        raise Problem(409, 'NOT_ALLOWED', f"The next step is {nxt['stage']!r}, not 'visuals'.", next=nxt)
    return run, core.current_outputs(conn, run['id'])


def _visuals_call(conn, user, run_id, body, fn, status=200):
    run, outputs = _visuals_run(conn, user, run_id)
    st, resp = core.with_receipt(conn, user, body_dict(body), lambda: (status, visuals_stage.guarded(lambda: fn(run, outputs))))
    return Response(resp, status_code=st)


@app.get('/api/runs/{run_id}/visuals')
def visuals_status(run_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)   # ticket 9: it may repair and save the session
    return Response(visuals_stage.status(conn, storage(), run, core.current_outputs(conn, run['id'])))


@app.get('/api/runs/{run_id}/visuals/shots/{shot_id}/packet')
def visuals_packet(run_id: UUID, shot_id: str, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    return Response(visuals_stage.packet(storage(), run, core.current_outputs(conn, run['id']), shot_id))


@app.post('/api/runs/{run_id}/visuals/prepare')
def visuals_prepare(run_id: UUID, body: Write, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.prepare(conn, storage(), user, run, outputs))


@app.post('/api/runs/{run_id}/visuals/check', dependencies=[Depends(size_guard)])
def visuals_check(run_id: UUID, body: VisualPlan, user=User, conn=DB):
    run, outputs = _visuals_run(conn, user, run_id)
    return Response(visuals_stage.check(storage(), run, outputs, body.plan))


@app.post('/api/runs/{run_id}/visuals/propose', dependencies=[Depends(size_guard)])
def visuals_propose(run_id: UUID, body: VisualPlan, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.propose(conn, storage(), user, run, outputs, body.plan))


@app.post('/api/runs/{run_id}/visuals/select')
def visuals_select(run_id: UUID, body: VisualSelect, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.select_choice(storage(), user, run, outputs, body.choices))


@app.post('/api/runs/{run_id}/visuals/accept')
def visuals_accept(run_id: UUID, body: VisualAccept, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.accept(storage(), user, run, outputs, body.gap_ids, body.quote))


@app.post('/api/runs/{run_id}/visuals/references', status_code=201)
def visuals_reference(run_id: UUID, body: ReferenceAdd, user=User, conn=DB):
    import base64 as b64
    content = b64.b64decode(body.content_base64) if body.content_base64 else b''
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.add_reference(conn, storage(), user, run, outputs, body_dict(body), content), 201)


@app.post('/api/runs/{run_id}/visuals/images', status_code=201)
def visuals_image(run_id: UUID, body: ImageGenerate, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.generate_image(conn, storage(), user, run, outputs, body_dict(body)), 201)


@app.post('/api/runs/{run_id}/visuals/references/{ref_id}/approve')
def visuals_approve(run_id: UUID, ref_id: str, body: ReferenceApprove, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.approve_reference(storage(), user, run, outputs, ref_id, body.sha256, body.quote))


@app.post('/api/runs/{run_id}/visuals/bind')
def visuals_bind(run_id: UUID, body: BindBody, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.bind(storage(), user, run, outputs, body.shot_id, body.references, body.subject_selectors, body.quote))


@app.post('/api/runs/{run_id}/visuals/generator')
def visuals_generator(run_id: UUID, body: GeneratorBody, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.select_generator(storage(), user, run, outputs, body.shot_id, body.provider, body.model))


@app.post('/api/runs/{run_id}/visuals/prepare-take')
def visuals_prepare_take(run_id: UUID, body: PrepareTake, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.prepare_take(storage(), user, run, outputs, body_dict(body)))


@app.post('/api/runs/{run_id}/visuals/take', status_code=201)
def visuals_take(run_id: UUID, body: ShotBody, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.submit_take(conn, storage(), user, run, outputs, body.shot_id), 201)


@app.post('/api/runs/{run_id}/visuals/review')
def visuals_review(run_id: UUID, body: TakeReview, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.review_take(conn, storage(), user, run, outputs, body.job_id, body.decision, body.notes, body.timing_notes, body.quote))


@app.post('/api/runs/{run_id}/visuals/select-take')
def visuals_select_take(run_id: UUID, body: TakeSelect, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.select_take(conn, storage(), user, run, outputs, body.job_id, body.quote))


@app.post('/api/runs/{run_id}/visuals/asset')
def visuals_asset(run_id: UUID, body: AssetBody, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.add_asset(conn, storage(), user, run, outputs, body.shot_id, body.key, body.sha256, body.bytes, body.kind, body.quote))


@app.post('/api/runs/{run_id}/visuals/record', status_code=201)
def visuals_record(run_id: UUID, body: GapBody, user=User, conn=DB):
    return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.record_gap(conn, storage(), user, run, outputs, body.gap_id, body.quote), 201)


# ---------- stage 2: options / master / first cut ----------

def _stage_run(conn, user, run_id, stage):
    run = core.load_run(conn, user, run_id, lock=True)
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    nxt = core.next_for(conn, run)
    if nxt['stage'] != stage:
        raise Problem(409, 'NOT_ALLOWED', f"The next step is {nxt['stage']!r}, not {stage!r}.", next=nxt)
    return run, core.current_outputs(conn, run['id'])


def _s2(conn, user, run_id, stage, body, fn, status=200):
    run, outputs = _stage_run(conn, user, run_id, stage)
    st, resp = core.with_receipt(conn, user, body_dict(body), lambda: (status, fn(run, outputs)))
    return Response(resp, status_code=st)


@app.post('/api/runs/{run_id}/options/prepare')
def options_prepare(run_id: UUID, body: Write, user=User, conn=DB):
    return _s2(conn, user, run_id, 'options', body, lambda run, outputs: stage2.prepare(conn, storage(), user, run, outputs))


@app.get('/api/runs/{run_id}/options/coverage')
def options_coverage(run_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    return Response(stage2.coverage(storage(), run))


@app.post('/api/runs/{run_id}/options/scenes', dependencies=[Depends(size_guard)])
def options_scenes(run_id: UUID, body: ScenesBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'options', body, lambda run, outputs: stage2.set_scenes(conn, storage(), user, run, outputs, body.document, body.quote))


@app.post('/api/runs/{run_id}/options/check', dependencies=[Depends(size_guard)])
def options_check(run_id: UUID, body: OptionsDoc, user=User, conn=DB):
    run, _ = _stage_run(conn, user, run_id, 'options')
    return Response(stage2.check(storage(), run, body.document))


@app.post('/api/runs/{run_id}/options/propose', dependencies=[Depends(size_guard)])
def options_propose(run_id: UUID, body: OptionsDoc, user=User, conn=DB):
    return _s2(conn, user, run_id, 'options', body, lambda run, outputs: stage2.propose(conn, storage(), user, run, body.document))


@app.post('/api/runs/{run_id}/options/frames')
def options_frames(run_id: UUID, body: FramesBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'options', body, lambda run, outputs: stage2.frames(storage(), user, run, body.sub_clip_id, body.edge))


@app.post('/api/runs/{run_id}/options/inspect', status_code=201)
def options_inspect(run_id: UUID, body: FramesBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'options', body, lambda run, outputs: stage2.inspect(conn, storage(), user, run, body.sub_clip_id, body.edge), 201)


@app.post('/api/runs/{run_id}/stage2/render', status_code=201)
def stage2_render(run_id: UUID, body: RenderBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'options' if body.film == 'review' else 'master', body, lambda run, outputs: stage2.render(conn, storage(), user, run, body.film), 201)


@app.get('/api/runs/{run_id}/stage2')
def stage2_status(run_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)   # it saves the session (ticket 9)
    return Response(stage2.status(conn, storage(), run))


@app.get('/api/runs/{run_id}/options/{option_number}')
def options_show(run_id: UUID, option_number: int, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    return Response(stage2.show(storage(), run, option_number))


@app.get('/api/runs/{run_id}/options/log/{unit}')
def options_log(run_id: UUID, unit: str, user=User, conn=DB):
    run = core.load_run(conn, user, run_id)
    return Response(stage2.log_key(storage(), run, core.current_outputs(conn, run['id']), unit))


@app.post('/api/runs/{run_id}/options/record', status_code=201)
def options_record(run_id: UUID, body: Quote, user=User, conn=DB):
    return _s2(conn, user, run_id, 'options', body, lambda run, outputs: stage2.record_options(conn, storage(), user, run, body.quote), 201)


@app.post('/api/runs/{run_id}/master/decide')
def master_decide(run_id: UUID, body: DecideBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'master', body, lambda run, outputs: stage2.decide(storage(), user, run, body.slide if body.slide is not None else body.option_number, body.action, body.note, body.edit))


@app.post('/api/runs/{run_id}/master/rule')
def master_rule(run_id: UUID, body: RuleBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'master', body, lambda run, outputs: stage2.add_rule(storage(), user, run, body.rule))


@app.post('/api/runs/{run_id}/master/build')
def master_build(run_id: UUID, body: Write, user=User, conn=DB):
    return _s2(conn, user, run_id, 'master', body, lambda run, outputs: stage2.build_master(conn, storage(), user, run))


@app.post('/api/runs/{run_id}/master/record', status_code=201)
def master_record(run_id: UUID, body: Quote, user=User, conn=DB):
    return _s2(conn, user, run_id, 'master', body, lambda run, outputs: stage2.record_master(conn, storage(), user, run, body.quote), 201)


@app.post('/api/runs/{run_id}/first-cut/record', status_code=201)
def first_cut_record(run_id: UUID, body: Quote, user=User, conn=DB):
    return _s2(conn, user, run_id, 'first_cut', body, lambda run, outputs: stage2.record_first_cut(conn, storage(), user, run, outputs, body.quote), 201)


# ---------- stage 3: assembly / delivery ----------

@app.post('/api/runs/{run_id}/assembly/prepare')
def assembly_prepare(run_id: UUID, body: Write, user=User, conn=DB):
    return _s2(conn, user, run_id, 'assembly', body, lambda run, outputs: stage3.prepare(conn, storage(), user, run, outputs))


@app.post('/api/runs/{run_id}/assembly/choose')
def assembly_choose(run_id: UUID, body: ChooseBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'assembly', body, lambda run, outputs: stage3.choose(storage(), user, run, body.shot_id, body.offset_frames, body.end_policy, body.accept_as_is))


@app.post('/api/runs/{run_id}/assembly/stabilize')
def assembly_stabilize(run_id: UUID, body: StabBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'assembly', body, lambda run, outputs: stage3.stabilize(storage(), user, run, body.sub_clip_id, body.choice))


@app.post('/api/runs/{run_id}/assembly/build')
def assembly_build(run_id: UUID, body: Write, user=User, conn=DB):
    return _s2(conn, user, run_id, 'assembly', body, lambda run, outputs: stage3.build(conn, storage(), user, run, outputs))


@app.post('/api/runs/{run_id}/assembly/render', status_code=201)
def assembly_render(run_id: UUID, body: Write, user=User, conn=DB):
    return _s2(conn, user, run_id, 'assembly', body, lambda run, outputs: stage3.render(conn, storage(), user, run), 201)


@app.get('/api/runs/{run_id}/stage3')
def stage3_status(run_id: UUID, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)   # it saves the session (ticket 9)
    return Response(stage3.status(conn, storage(), run))


@app.post('/api/runs/{run_id}/assembly/review')
def assembly_review(run_id: UUID, body: ReviewBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'assembly', body, lambda run, outputs: stage3.review(conn, storage(), user, run, body.decision, body.notes, body.frame_notes, body.quote))


@app.post('/api/runs/{run_id}/assembly/record', status_code=201)
def assembly_record(run_id: UUID, body: Quote, user=User, conn=DB):
    return _s2(conn, user, run_id, 'assembly', body, lambda run, outputs: stage3.record(conn, storage(), user, run, body.quote), 201)


@app.post('/api/runs/{run_id}/delivery/bundle', status_code=201)
def delivery_bundle(run_id: UUID, body: Write, user=User, conn=DB):
    return _s2(conn, user, run_id, 'delivery', body, lambda run, outputs: deliv.bundle(conn, storage(), user, run, outputs), 201)


@app.post('/api/runs/{run_id}/delivery/resolve/reserve')
def delivery_reserve(run_id: UUID, body: ReserveBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'delivery', body, lambda run, outputs: deliv.resolve_reserve(storage(), user, run, body.machine, body.authorization))


@app.post('/api/runs/{run_id}/delivery/resolve/mark')
def delivery_mark(run_id: UUID, body: MarkBody, user=User, conn=DB):
    return _s2(conn, user, run_id, 'delivery', body, lambda run, outputs: deliv.resolve_mark(storage(), user, run, body.state, body.machine, body.report, body.note))


@app.post('/api/runs/{run_id}/delivery/final', status_code=201)
def delivery_final(run_id: UUID, body: Quote, user=User, conn=DB):
    return _s2(conn, user, run_id, 'delivery', body, lambda run, outputs: deliv.final(conn, storage(), user, run, outputs, body.quote), 201)


@app.get('/health')
def health():
    return {'ok': True}


@app.get('/api/procedures/{version}/{stage}')
def procedure(version: str, stage: str, user=User):
    """Procedure text for the executor only: it is never written to disk by the plugin and never shown in the UI."""
    if user['kind'] != 'executor':
        raise Problem(403, 'EXECUTOR_ONLY', 'Procedures are available to the operator tool only.')
    stages = core.stage_table(version)
    if stages is None:
        raise Problem(404, 'VERSION_UNKNOWN', f'Procedure version {version!r} is not published.')
    st = core._stage(stages, stage)
    return Response({k: st.get(k) for k in ('name', 'prompt', 'steps', 'output_shape', 'output_file', 'needs_acceptance', 'paid', 'per_unit', 'cap')})


@app.get('/api/meta')
def meta():
    return Response({'server_version': settings().SERVER_VERSION, 'plugin_min_version': settings().PLUGIN_MIN_VERSION, 'app_origin': settings().APP_ORIGIN})


# ---------- connect flow ----------

@app.post('/api/connect', status_code=201)
def connect_begin(body: ConnectBegin, conn=DB):
    return Response(connect.begin(conn, body.request_id, body.token_hash), status_code=201)


@app.get('/api/connect/{connection_id}')
def connect_status(connection_id: UUID, conn=DB):
    return Response(connect.status(conn, connection_id))


@app.post('/api/connect/{connection_id}/approve')
def connect_approve(connection_id: UUID, body: ConnectApprove, user=User, conn=DB):
    return Response(connect.approve(conn, user, connection_id, body.code))


@app.post('/api/runs/{run_id}/claim')
def post_claim(run_id: UUID, body: Claim, user=User, conn=DB):
    run = core.load_run(conn, user, run_id, lock=True)
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, dict(core.claim(conn, user, run, body.machine))))
    return Response(resp, status_code=status)
