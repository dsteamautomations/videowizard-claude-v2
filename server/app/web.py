"""Server-rendered pages: login, connect approve, my runs, run view, defects. Pages never write run state."""
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import auth, connect, core
from .config import settings
from .db import connect as db_connect
from .errors import Problem

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / 'templates'))
COOKIE = 'vw2_session'


def page_user(vw2_session: str | None = Cookie(default=None)):
    if not vw2_session:
        return None
    try:
        return auth.current_user('Bearer ' + vw2_session)
    except Problem:
        return None


def render(request, name, status=200, **ctx):
    return templates.TemplateResponse(request, name, ctx, status_code=status)


def login_redirect(request):
    return RedirectResponse('/login?next=' + request.url.path, status_code=303)


@router.get('/login', response_class=HTMLResponse)
def login_page(request: Request, next: str = '/runs'):
    return render(request, 'login.html', next=next, message=None)


@router.post('/login')
def login_submit(request: Request, username: str = Form(), password: str = Form(), next: str = Form(default='/runs')):
    try:
        result = auth.sign_in(username, password, 'browser')
    except Problem as exc:
        return render(request, 'login.html', status=exc.status, next=next, message=exc.message)
    response = RedirectResponse(next if next.startswith('/') else '/runs', status_code=303)
    response.set_cookie(COOKIE, result['token'], httponly=True, samesite='strict', secure=settings().APP_ORIGIN.startswith('https'),
                        max_age=settings().SESSION_HOURS * 3600)
    return response


@router.post('/logout')
def logout(vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if user:
        auth.sign_out(user)
    response = RedirectResponse('/login', status_code=303)
    response.delete_cookie(COOKIE)
    return response


@router.get('/connect/{connection_id}', response_class=HTMLResponse)
def connect_page(request: Request, connection_id: UUID, vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        try:
            row = connect.load(conn, connection_id)
        except Problem as exc:
            return render(request, 'connect.html', status=exc.status, user=user, code=None, message=exc.message, connected=False)
    return render(request, 'connect.html', user=user, code=row['code'], message=None, connected=bool(row['approved_at']))


@router.post('/connect/{connection_id}', response_class=HTMLResponse)
def connect_approve(request: Request, connection_id: UUID, code: str = Form(), vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        try:
            connect.approve(conn, user, connection_id, code)
        except Problem as exc:
            return render(request, 'connect.html', status=exc.status, user=user, code=None, message=exc.message, connected=False)
    return render(request, 'connect.html', user=user, code=None, message='Connected. You can go back to the operator chat.', connected=True)


@router.get('/runs', response_class=HTMLResponse)
def runs_page(request: Request, vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        runs = core.list_runs(conn, user)
    return render(request, 'runs.html', user=user, runs=runs)


@router.get('/runs/{code}', response_class=HTMLResponse)
def run_page(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        row = conn.execute('select id from vw2_runs where code = %s', (code,)).fetchone()
        if not row:
            raise Problem(404, 'NOT_FOUND', 'Run not found.')
        run = core.load_run(conn, user, row['id'])
        stages = core.stage_table(run['procedure_version'])
        outputs = conn.execute('select * from vw2_stage_outputs where run_id=%s order by created_at', (run['id'],)).fetchall()
        nxt = core.next_for(conn, run)
    by_stage = {s['name']: [o for o in outputs if o['stage'] == s['name']] for s in stages}
    return render(request, 'run.html', user=user, run=run, stages=stages, by_stage=by_stage, next=nxt)


@router.get('/defects', response_class=HTMLResponse)
def defects_page(request: Request, vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    if not core.is_admin(user):
        raise Problem(404, 'NOT_FOUND', 'Page not found.')
    with db_connect() as conn:
        defects = conn.execute('''select d.*, r.code from vw2_defects d join vw2_runs r on r.id = d.run_id
                                  order by d.status, d.created_at desc limit 200''').fetchall()
    return render(request, 'defects.html', user=user, defects=defects)
