"""VideoWizard v2 server. Routes are thin: auth, body checks, one transaction, delegate to core."""
import json
from typing import Any, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import auth, connect, core, elevenlabs, files, jobs, web, worker
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
    title: str = ''
    client: str | None = None
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
    status, resp = core.with_receipt(conn, user, body_dict(body), lambda: (200, dict(core.close(conn, user, run))))
    return Response(resp, status_code=status)


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
    if not row or row['status'] != 'submission_unknown':
        raise Problem(409, 'NOT_ALLOWED', 'Only a job with an unknown provider outcome can be recovered.')
    worker.recover_voice(row)
    conn.execute("update vw2_jobs set status='storage_pending', lease_until=null, error=null, updated_at=now() where id=%s", (job_id,))
    return Response({'id': str(job_id), 'status': 'storage_pending', 'message': 'Recovered from provider history; the worker will store it.'})


@app.post('/api/runs/{run_id}/jobs/{job_id}/resolve')
def resolve_job(run_id: UUID, job_id: UUID, body: Resolve, user=User, conn=DB):
    """Set aside a job whose outcome is unknown after the operator checked the provider account; lets a new job start."""
    run = core.load_run(conn, user, run_id, lock=True)
    row = conn.execute('select * from vw2_jobs where id=%s and run_id=%s', (job_id, run['id'])).fetchone()
    if not row or row['status'] not in ('submission_unknown', 'storage_pending'):
        raise Problem(409, 'NOT_ALLOWED', 'Only an unresolved job can be set aside.')
    conn.execute("update vw2_jobs set status='failed', error=%s, lease_until=null, updated_at=now() where id=%s", ('Set aside by operator: ' + (body.note or ''), job_id))
    return Response({'id': str(job_id), 'status': 'failed'})


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
