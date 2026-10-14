"""VideoWizard v2 server. Routes are thin: auth, body checks, one transaction, delegate to core."""
import json
from typing import Any, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from . import auth, core
from .config import settings
from .db import connect, migrate
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


@app.exception_handler(Problem)
def problem(request, exc: Problem):
    return Response({'code': exc.code, 'message': exc.message, **exc.extra}, status_code=exc.status)


def db():
    with connect() as conn:
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


@app.get('/health')
def health():
    return {'ok': True}
