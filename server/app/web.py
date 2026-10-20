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
    outputs = [dict(o) for o in outputs]
    _add_timing(run, outputs)
    by_stage = {s['name']: [o for o in outputs if o['stage'] == s['name']] for s in stages}
    return render(request, 'run.html', user=user, run=run, stages=stages, by_stage=by_stage, next=nxt)


def _add_timing(run, outputs):
    """Per output (design/34 1.19): minutes from the previous acceptance (or the run's creation) to the proposal, and from the
    proposal to this acceptance, when the summary carries prepared_at. Unparseable values leave the fields empty."""
    from datetime import datetime
    previous = run['created_at']
    for o in outputs:  # already ordered by created_at
        o['to_proposal_min'] = o['to_approval_min'] = None
        prepared = (o.get('summary') or {}).get('prepared_at')
        try:
            when = datetime.fromisoformat(str(prepared).replace('Z', '+00:00')) if prepared else None
        except ValueError:
            when = None
        if when is not None and when.tzinfo is not None:
            o['to_proposal_min'] = round((when - previous).total_seconds() / 60, 1)
            o['to_approval_min'] = round((o['created_at'] - when).total_seconds() / 60, 1)
        if not o.get('stale'):
            previous = o['created_at']


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


# ---------- the Voices page and directory (design/52 B, C) ----------

def _run_by_code(conn, user, code):
    row = conn.execute('select id from vw2_runs where code = %s', (code,)).fetchone()
    if not row:
        raise Problem(404, 'NOT_FOUND', 'Run not found.')
    return core.load_run(conn, user, row['id'])


def _voices_context(conn, user, run, request):
    from . import elevenlabs, voices
    from .storage import storage
    provider = elevenlabs.ElevenLabs()
    qp = request.query_params
    q = {'scope': qp.get('scope') or 'library', 'search': (qp.get('search') or '')[:200], 'cursor': (qp.get('cursor') or '')[:1000], 'language': (qp.get('language') or '')[:30],
         'accent': (qp.get('accent') or '')[:80], 'gender': qp.get('gender') or '', 'age': qp.get('age') or '',
         'use_cases': [u for u in (qp.get('use_case') or '').split(',') if u in elevenlabs.USE_CASES], 'high_quality': False}
    ctx = {'q': q, 'message': qp.get('message') or '', 'error': qp.get('error') or '', 'use_cases': elevenlabs.USE_CASES}
    try:
        ctx['account'] = voices.account(provider)
    except Problem as exc:
        ctx['account'] = {'error': exc.message}
    try:
        ctx['catalog'] = voices.catalog(conn, provider, q) if (qp.get('browse') or not run) else None
    except Problem as exc:
        ctx['catalog'], ctx['error'] = None, exc.message
    if run:
        store = storage()
        outputs = core.current_outputs(conn, run['id'])
        state = voices.page_state(store, run)
        direction = voices.direction_of(store, run)
        job_rows = conn.execute("select id, status, request, result, error, created_at from vw2_jobs where run_id=%s and stage='voice' order by created_at", (run['id'],)).fetchall()
        by_id = {str(j['id']): j for j in job_rows}
        auditions = [{**j, 'request': {k: v for k, v in j['request'].items() if k != 'text'}} for j in job_rows if j['request'].get('kind') == 'audition']
        for n in state['narrations']:
            n['job'] = by_id.get(n['job_id'])
        try:
            script, _ = voices.script_text(store, outputs)
            passages = sorted({r['passage_id'] for r in __import__('app.voice_direction', fromlist=['sentences_of']).sentences_of(script['spoken_text'])})
            characters = len(script['spoken_text'])
        except Problem:
            passages, characters = [], 0
        ctx.update(state=state, direction=direction, auditions=auditions, passages=passages, characters=characters, next=core.next_for(conn, run))
    else:
        ctx['history'] = voices.history(conn)
        ctx['register'] = voices.register_rows(conn)
    return ctx


@router.get('/voices', response_class=HTMLResponse)
def voices_directory(request: Request, vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        ctx = _voices_context(conn, user, None, request)
    return render(request, 'voices.html', user=user, run=None, **ctx)


@router.get('/runs/{code}/voices', response_class=HTMLResponse)
def run_voices(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        run = _run_by_code(conn, user, code)
        ctx = _voices_context(conn, user, run, request)
    return render(request, 'voices.html', user=user, run=run, **ctx)


@router.get('/runs/{code}/audio/{key:path}')
def run_audio(request: Request, code: str, key: str, vw2_session: str | None = Cookie(default=None)):
    """A kept audition or narration, played on the page: a redirect to the storage link (cookie sign-in, the run's own keys only)."""
    from .storage import storage
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        run = _run_by_code(conn, user, code)
    store = storage()
    if not key.startswith(f"{run['id']}/") or not store.exists(key):
        raise Problem(404, 'FILE_MISSING', 'No such file on this run.')
    return RedirectResponse(store.signed_download(key), status_code=307)


def _back(request, code, message='', error=''):
    from urllib.parse import urlencode
    base = f'/runs/{code}/voices' if code else '/voices'
    keep = {k: v for k, v in request.query_params.items() if k in ('scope', 'search', 'cursor', 'language', 'accent', 'gender', 'age', 'use_case', 'browse')}
    params = {**keep, **({'message': message} if message else {}), **({'error': error} if error else {})}
    return RedirectResponse(base + ('?' + urlencode(params) if params else ''), status_code=303)


@router.post('/voices/{action}')
@router.post('/runs/{code}/voices/{action}')
async def voices_action(request: Request, action: str, code: str | None = None, vw2_session: str | None = Cookie(default=None)):
    """One form post per button. Every paid button names its cost on the page; nothing runs without a click."""
    import uuid
    from . import elevenlabs, voices
    from .storage import storage
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    form = await request.form()
    provider = elevenlabs.ElevenLabs()
    rid = str(uuid.uuid4())
    try:
        with db_connect() as conn:
            if action == 'favourite':
                row = voices.set_favourite(conn, provider, user, form['voice_id'], form.get('on') == '1', form.get('note') or '')
                return _back(request, code, f"{row['name']}: {'favourite' if row['favourite'] else 'no longer a favourite'}")
            if action == 'release':
                voices.release(conn, provider, user, form['voice_id'])
                return _back(request, code, 'released from the account')
            if action == 'restore':
                v = voices.restore(conn, provider, user, form['voice_id'])
                return _back(request, code, f"{v['name']} saved to the account again")
            if not code:
                raise Problem(404, 'NOT_FOUND', 'Page not found.')
            run = core.load_run(conn, user, _run_by_code(conn, user, code)['id'], lock=True)
            outputs = core.current_outputs(conn, run['id'])
            store = storage()
            if action == 'shortlist':
                import json as _json
                chosen = [_json.loads(v) for v in form.getlist('voice')][:voices.SHORTLIST_MAX]
                state = voices.page_state(store, run)
                state['shortlist'] = [{'voice_id': v['voice_id'], 'name': v.get('name') or '', 'library': v.get('library')} for v in chosen]
                voices.save_doc(store, run, 'page.json', state)
                return _back(request, code, f'{len(chosen)} on the shortlist')
            if action == 'excerpt':
                state = voices.page_state(store, run)
                state['excerpt'] = (form.get('text') or '').strip()[:3000] or None
                voices.save_doc(store, run, 'page.json', state)
                return _back(request, code, 'excerpt set')
            if action == 'audition':
                rows = voices.audition_shortlist(conn, store, user, run, outputs, rid)
                return _back(request, code, f'{len(rows)} auditions submitted; refresh in a minute')
            if action == 'pick':
                state = voices.page_state(store, run)
                state['pick'] = {'voice_id': form['voice_id'], 'name': form.get('name') or '', 'by': user['name'], 'at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
                voices.save_doc(store, run, 'page.json', state)
                return _back(request, code, f"picked {state['pick']['name'] or form['voice_id']} (provisional)")
            if action == 'narrate':
                import json as _json
                tweaks = _json.loads(form.get('tweaks') or '[]')
                row = voices.narrate(conn, store, user, run, outputs, form['voice_id'], rid, 'page', tweaks if tweaks else None)
                return _back(request, code, f"full narration submitted with {row['request'].get('name')}; refresh in a few minutes")
            if action == 'direction-audition':
                row = voices.direction_audition(conn, store, user, run, outputs, form['voice_id'], form['passage_id'], rid)
                return _back(request, code, f"one passage with its tags submitted in {row['request'].get('name')}")
            if action == 'final':
                voices.finalise(conn, store, user, run, outputs, form['job_id'], form.get('quote') or '', 'page')
                return _back(request, code, 'this narration is now the final one; the run moves to media')
            raise Problem(404, 'NOT_FOUND', 'Page not found.')
    except Problem as exc:
        return _back(request, code, error=exc.message)
