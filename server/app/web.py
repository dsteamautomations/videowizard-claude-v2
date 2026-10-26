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
templates.env.globals['version'] = settings().SERVER_VERSION   # cache-busts the stylesheet on every release (the browser kept an old style.css on 20 Oct)
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
    brief = next((o for o in by_stage.get('brief', []) if not o.get('stale')), None)   # design/50: how much the directory held, as the brief saw it
    directory_fields = len((brief.get('summary') or {}).get('client_card') or {}) if brief else None
    return render(request, 'run.html', user=user, run=run, stages=stages, by_stage=by_stage, next=nxt, directory_fields=directory_fields)


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


@router.get('/voices', response_class=HTMLResponse)
def voices_directory(request: Request, vw2_session: str | None = Cookie(default=None)):
    """The voices directory (design/52 M): favourites and where every voice was used. No provider call."""
    from . import voices
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        history, register = voices.history(conn), voices.register_rows(conn)
    return render(request, 'voices.html', user=user, history=history, register=register)


@router.get('/runs/{code}/voices')
def run_voices_redirect(code: str):
    """The first voices page (design/52) is gone; its links land on the end-to-end page (design/55)."""
    return RedirectResponse(f'/runs/{code}/voices2', status_code=307)


# ---------- design/54: the Voices page end to end (/runs/<code>/voices2), served as data for the page's own JavaScript ----------

@router.get('/runs/{code}/voices2', response_class=HTMLResponse)
def voices2_page(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        run = _run_by_code(conn, user, code)
    return render(request, 'voices2.html', user=user, run=run)


def _voices2_state(conn, user, run):
    from . import core, elevenlabs, voices
    from .storage import storage
    store = storage()
    outputs = core.current_outputs(conn, run['id'])
    state = voices.page_state(store, run)
    direction = voices.direction_of(store, run)
    job_rows = conn.execute("select id, status, request, result, error, created_at from vw2_jobs where run_id=%s and stage='voice' order by created_at", (run['id'],)).fetchall()
    jobs_ = [{'id': str(j['id']), 'status': j['status'], 'kind': j['request'].get('kind'), 'voice_id': j['request'].get('voice_id'), 'name': j['request'].get('name'),
              'directed': bool(j['request'].get('directed')), 'passage': j['request'].get('passage'), 'saved_from_library': bool(j['request'].get('saved_from_library')),
              'audio_key': (j['result'] or {}).get('audio_key'), 'duration_s': (j['result'] or {}).get('duration_s'), 'error': j['error'], 'created_at': j['created_at'].isoformat()}
             for j in job_rows]
    try:
        script, _ = voices.script_text(store, outputs)
        from . import voice_direction as VD
        directed = VD.apply(script['spoken_text'], (direction or {}).get('base') or [], (direction or {}).get('register') or '')[0] if direction and direction.get('chosen') != 'none' else script['spoken_text']
        sentences = [{'passage_id': r['passage_id'], 'sentence': r['sentence'], 'text': r['text']} for r in VD.sentences_of(script['spoken_text'])]
        characters = len(script['spoken_text'])
    except Problem:
        directed, sentences, characters = '', [], 0
    try:
        account = voices.account(elevenlabs.ElevenLabs())
    except Problem as exc:
        account = {'error': exc.message}
    nxt = core.next_for(conn, run)
    last_voice = core.last_voice(conn, run.get('client_id')) if run.get('client_id') else None
    try:   # design/55: known voices, narratable without a tryout
        provider = elevenlabs.ElevenLabs()
        mine = voices.my_voices(provider)
        favs = voices.search(conn, provider, {'tab': 'favourites'})['voices']
        known = voices.known_voices(last_voice, favs, mine)
    except Problem:
        known = voices.known_voices(last_voice, [], [])
    return {'run': {'code': run['code'], 'title': run.get('title'), 'client': run.get('client'), 'stage': nxt.get('stage')}, 'state': state, 'direction': direction, 'jobs': jobs_,
            'directed_script': directed, 'sentences': sentences, 'characters': characters, 'account': account, 'last_voice': last_voice, 'known': known}


# ---------- design/62: the review page (watch the film, decide by button); the audio route voices2 plays from (lost in the 0.20.0 cleanup) ----------

def _stored_file(request, code, key, vw2_session):
    """A file of this run, served to the signed-in page by a redirect to the storage link (byte ranges work there, so the player seeks)."""
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


@router.get('/runs/{code}/audio/{key:path}')
def run_audio(request: Request, code: str, key: str, vw2_session: str | None = Cookie(default=None)):
    return _stored_file(request, code, key, vw2_session)


@router.get('/runs/{code}/film/{key:path}')
def run_film(request: Request, code: str, key: str, vw2_session: str | None = Cookie(default=None)):
    return _stored_file(request, code, key, vw2_session)


@router.get('/runs/{code}/file/{key:path}')
def run_file(request: Request, code: str, key: str, vw2_session: str | None = Cookie(default=None)):
    return _stored_file(request, code, key, vw2_session)   # design/65: reference images, states and takes on the visuals page


@router.get('/runs/{code}/visuals', response_class=HTMLResponse)
def visuals_page(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        run = _run_by_code(conn, user, code)
    return render(request, 'visuals.html', user=user, run=run)


def _visuals_payload(conn, store, run, repair=True):
    from . import visuals_stage
    nxt = core.next_for(conn, run)
    return {'run': {'code': run['code'], 'title': run['title'], 'status': run['status'], 'stage': nxt.get('stage'), 'open_defects': nxt.get('open_defects') or []},
            **visuals_stage.page_view(conn, store, run, core.current_outputs(conn, run['id']), run['code'], repair)}


@router.get('/runs/{code}/visuals/data')
def visuals_data(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    from fastapi.responses import JSONResponse
    from .storage import storage
    user = page_user(vw2_session)
    if not user:
        raise Problem(401, 'SIGN_IN', 'Sign in first.')
    with db_connect() as conn:
        run = core.load_run(conn, user, _run_by_code(conn, user, code)['id'])   # design/92: a read never waits for the lock nor stops on an open defect
        payload = _visuals_payload(conn, storage(), run, core.try_lock(conn, run['id']))   # the view may repair the session (ticket 9) when the run is free
    return JSONResponse(core.jsonable(payload))


@router.post('/runs/{code}/visuals/act')
async def visuals_act(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    """design/92: the body is read here; the work, which blocks (database, storage, providers), runs on a worker thread so the one server
    process keeps answering every other request meanwhile."""
    from starlette.concurrency import run_in_threadpool
    body = await request.json()
    return await run_in_threadpool(_visuals_act, code, vw2_session, body)


def _visuals_act(code, vw2_session, body):
    """One JSON post per button. Every action calls the server function the vw tool calls (design/65 §8), behind the visuals stage gate."""
    from fastapi.responses import JSONResponse
    from . import visuals_stage as V
    from .storage import storage
    user = page_user(vw2_session)
    if not user:
        raise Problem(401, 'SIGN_IN', 'Sign in first.')
    action = body.get('action')
    quote = str(body.get('quote') or '')
    found = None
    if action == 'round-done':   # design/92 (L59): the round's searches run before the run's lock
        with db_connect() as conn:
            r0 = core.load_run(conn, user, _run_by_code(conn, user, code)['id'])
            found = V.round_searches(storage(), r0, core.current_outputs(conn, r0['id']), dict(body.get('verdicts') or {}))
    with db_connect() as conn:
        run = _run_at(conn, user, code, 'visuals')
        store = storage()
        outputs = core.current_outputs(conn, run['id'])
        calls = {
            'treatment': lambda: V.treatment(store, user, run, outputs, None, quote),
            'select': lambda: V.select_choice(store, user, run, outputs, {body['gap_id']: body['choice_id']}),
            'accept': lambda: V.accept(store, user, run, outputs, list(body.get('gap_ids') or ['all']), quote),
            'revise': lambda: V.revise_gap(store, user, run, outputs, body['gap_id'], str(body.get('notes') or ''), quote),   # design/76
            'search': lambda: V.search(store, user, run, outputs, body['element_id'], str(body.get('keywords') or ''), quote),   # design/73
            'pick': lambda: V.pick(store, user, run, outputs, body['search_id'], list(body.get('picks') or []), quote),
            'nothing-fits': lambda: V.nothing_fits(store, user, run, outputs, body['search_id'], str(body.get('reason') or '')),
            'round-done': lambda: V.round_done(store, user, run, outputs, dict(body.get('verdicts') or {}), quote, found=found),   # design/79; design/92
            'round-picks': lambda: V.round_picks(store, user, run, outputs, dict(body.get('picks') or {}), quote),
            'approve': lambda: V.approve_reference(store, user, run, outputs, body['reference_id'], body['sha256'], quote, conn),
            'footage': lambda: V.correct_footage(store, user, run, outputs, {k: body.get(k) for k in ('camera', 'support', 'look')}, quote),   # design/88 F4
            'sequence': lambda: V.sequence(store, user, run, outputs, body['shot_id'], list(body.get('reference_ids') or []), quote),
            'still': lambda: V.still_from_reference(store, user, run, outputs, body['shot_id'], body['reference_id'], quote, {'reason': body.get('reuse'), 'considered': body.get('considered')}, body.get('crop'), body.get('move')),
            'unplace': lambda: V.unplace(store, user, run, outputs, body['shot_id'], quote),   # design/94 R1.8
            'fix': lambda: V.request_fix(conn, store, user, run, outputs, body['reference_id']),   # design/96 X1: the click is the request
            'clip': lambda: V.fill_clip(store, user, run, outputs, body['shot_id'], body['clip_id'], float(body.get('in_s') or 0), quote,
                                        {'reason': body.get('reuse'), 'considered': body.get('considered')}, body.get('crop')),   # design/89 B3, finding 7
            'approve-reuse': lambda: V.approve_reuse(store, user, run, outputs, body['shot_id'], quote),   # design/89 H7
            'approve-spec': lambda: V.approve_spec(store, user, run, outputs, body['shot_id'], quote),   # design/89 D4
            'approve-specs': lambda: V.approve_specs(store, user, run, outputs, quote),   # design/106 D5
            'correct-spec': lambda: V.correct_spec(store, user, run, outputs, body['shot_id'], body.get('words')),   # design/106 D4
            'measure': lambda: V.measure(store, user, run, outputs, list(body.get('reference_ids') or []), str(body.get('question') or '')),   # design/89 D2
            'select-take': lambda: V.select_take(conn, store, user, run, outputs, body['job_id'], quote, str(body.get('notes') or 'approved on the visuals page'), str(body.get('timing_notes') or '')),
            'reject-take': lambda: V.review_take(conn, store, user, run, outputs, body['job_id'], 'rejected', str(body.get('notes') or ''), '', quote),
            'reject': lambda: V.reject_reference(store, user, run, outputs, body['reference_id'], str(body.get('notes') or ''), quote),   # design/74 L7
            'record': lambda: V.record_gaps(conn, store, user, run, outputs, list(body.get('gap_ids') or ['all']), quote),
        }
        if action not in calls:
            raise Problem(404, 'NOT_FOUND', 'No such action.')
        out = V.guarded(calls[action])
        out = out if isinstance(out, dict) else {'done': True}
        return JSONResponse(core.jsonable({**{k: v for k, v in out.items() if k != 'view'}, 'view': _visuals_payload(conn, store, run)}))


@router.get('/runs/{code}/review', response_class=HTMLResponse)
def review_page(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    user = page_user(vw2_session)
    if not user:
        return login_redirect(request)
    with db_connect() as conn:
        run = _run_by_code(conn, user, code)
    return render(request, 'review.html', user=user, run=run)


@router.get('/runs/{code}/review/data')
def review_data(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    from fastapi.responses import JSONResponse
    from .stage2 import stage as stage2
    from .storage import storage
    user = page_user(vw2_session)
    if not user:
        raise Problem(401, 'SIGN_IN', 'Sign in first.')
    with db_connect() as conn:
        run = _run_by_code(conn, user, code)
        payload = _review_payload(conn, storage(), run)
    return JSONResponse(core.jsonable(payload))


def _review_payload(conn, store, run):
    from .stage2 import stage as stage2
    nxt = core.next_for(conn, run)
    return {'run': {'code': run['code'], 'title': run['title'], 'status': run['status'], 'stage': nxt.get('stage'), 'open_defects': nxt.get('open_defects') or []},
            **stage2.review_view(conn, store, run)}


def _run_at(conn, user, code, stage):
    """The run, locked, when its next step is `stage`: the same gate the API applies (main._stage_run), so the page can never act at the wrong stage."""
    run = core.load_run(conn, user, _run_by_code(conn, user, code)['id'], lock=True)
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    nxt = core.next_for(conn, run)
    if nxt['stage'] not in (stage if isinstance(stage, tuple) else (stage,)):   # design/98: a slide answer is taken at options or master
        raise Problem(409, 'NOT_ALLOWED', f"The run is at {nxt['stage']!r}, not {stage!r}; reload the page.")
    return run


@router.post('/runs/{code}/review/act')
async def review_act(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    """design/92: the body is read here; the work, which blocks (database, storage, providers), runs on a worker thread so the one server
    process keeps answering every other request meanwhile."""
    from starlette.concurrency import run_in_threadpool
    body = await request.json()
    return await run_in_threadpool(_review_act, code, vw2_session, body)


def _review_act(code, vw2_session, body):
    """One JSON post per button: {action: 'record', quote} at the options stage; {action: 'decide', slide, decision, note, edit} at the master stage.
    Each calls the server function the vw tool calls (`vw options record`, `vw master decide`)."""
    from fastapi.responses import JSONResponse
    from .stage2 import stage as stage2
    from .storage import storage
    user = page_user(vw2_session)
    if not user:
        raise Problem(401, 'SIGN_IN', 'Sign in first.')
    action = body.get('action')
    with db_connect() as conn:
        if action == 'record':
            quote = str(body.get('quote') or '').strip()
            if not quote:
                raise Problem(422, 'ACCEPTANCE_REQUIRED', "The operator's words are required to approve the options.")
            run = _run_at(conn, user, code, 'options')
            store = storage()
            out = stage2.record_options(conn, store, user, run, quote)
            return JSONResponse(core.jsonable({'recorded': True, 'version': out['version'], 'view': _review_payload(conn, store, run)}))
        if action == 'decide':
            run = _run_at(conn, user, code, ('options', 'master'))   # design/98: the first answer approves the options
            store = storage()
            out = stage2.decide(conn, store, user, run, body.get('slide'), str(body.get('decision') or ''), str(body.get('note') or ''), body.get('edit') or None)
            return JSONResponse(core.jsonable({**out, 'view': _review_payload(conn, store, run)}))   # design/63 addendum: one round trip per click
    raise Problem(404, 'NOT_FOUND', 'No such action.')


@router.get('/runs/{code}/voices2/data')
def voices2_data(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    from fastapi.responses import JSONResponse
    from . import core
    user = page_user(vw2_session)
    if not user:
        raise Problem(401, 'SIGN_IN', 'Sign in first.')
    with db_connect() as conn:
        run = _run_by_code(conn, user, code)
        return JSONResponse(core.jsonable(_voices2_state(conn, user, run)))


@router.get('/voices2/search')
def voices2_search(request: Request, vw2_session: str | None = Cookie(default=None)):
    from fastapi.responses import JSONResponse
    from . import elevenlabs, voices
    user = page_user(vw2_session)
    if not user:
        raise Problem(401, 'SIGN_IN', 'Sign in first.')
    qp = request.query_params
    q = {'tab': qp.get('tab') if qp.get('tab') in ('explore', 'mine', 'favourites') else 'explore', 'search': (qp.get('search') or '')[:200], 'language': (qp.get('language') or '')[:30],
         'accent': (qp.get('accent') or '')[:80], 'gender': (qp.get('gender') or '')[:20], 'age': (qp.get('age') or '')[:20],
         'use_case': qp.get('use_case') if qp.get('use_case') in elevenlabs.USE_CASES else '', 'category': qp.get('category') if qp.get('category') in ('professional', 'famous', 'high_quality') else '',
         'sort': qp.get('sort') or 'trending', 'page': max(0, min(int(qp.get('page') or 0), 500))}
    with db_connect() as conn:
        return JSONResponse(voices.search(conn, elevenlabs.ElevenLabs(), q))


@router.post('/runs/{code}/voices2/act')
async def voices2_act(request: Request, code: str, vw2_session: str | None = Cookie(default=None)):
    """design/92: the body is read here; the work, which blocks (database, storage, providers), runs on a worker thread so the one server
    process keeps answering every other request meanwhile."""
    from starlette.concurrency import run_in_threadpool
    body = await request.json()
    return await run_in_threadpool(_voices2_act, code, vw2_session, body)


def _voices2_act(code, vw2_session, body):
    """One JSON post per button: {action, ...}. Every action calls the same server function the vw tool calls."""
    import uuid
    from fastapi.responses import JSONResponse
    from . import core, elevenlabs, voices
    from .storage import storage
    user = page_user(vw2_session)
    if not user:
        raise Problem(401, 'SIGN_IN', 'Sign in first.')
    action = body.get('action')
    rid = str(uuid.uuid4())
    provider = elevenlabs.ElevenLabs()
    with db_connect() as conn:
        if action == 'favourite':
            row = voices.set_favourite(conn, provider, user, body['voice_id'], bool(body.get('on', True)), body.get('note') or '')
            voices._SEARCH.clear()
            return JSONResponse({'voice_id': row['voice_id'], 'favourite': row['favourite']})
        if action == 'save':
            lib = body.get('library') or {}
            v = elevenlabs.add_library_voice(provider, lib['public_owner_id'], lib['original_voice_id'])
            voices.remember(conn, v, 'library')
            voices._SEARCH.clear()
            voices._MINE['rows'] = None
            return JSONResponse({'voice_id': v['voice_id'], 'name': v.get('name')})
        if action == 'preview':
            return JSONResponse({'url': voices.preview_link(conn, provider, body['voice_id'])})
        run = core.load_run(conn, user, _run_by_code(conn, user, code)['id'], lock=True)
        outputs = core.current_outputs(conn, run['id'])
        store = storage()
        if action == 'step':
            state = voices.page_state(store, run)
            voices.set_step(state, body['step'])
            voices.save_doc(store, run, 'page.json', state)
            return JSONResponse({'step': state['step']})
        if action == 'tryout':
            rows = voices.tryout(conn, store, user, run, outputs, list(body.get('voice_ids') or []), rid)
            return JSONResponse({'jobs': [str(r['id']) for r in rows], 'saved': [r['request'].get('name') for r in rows if r['request'].get('saved_from_library')]})
        if action == 'narrate':
            rows = voices.narrate_many(conn, store, user, run, outputs, list(body.get('voice_ids') or []), rid, 'page')
            return JSONResponse({'jobs': [str(r['id']) for r in rows]})
        if action == 'tweaks':
            return JSONResponse(voices.set_tweaks(store, run, outputs, body['voice_id'], list(body.get('tweaks') or [])))
        if action == 'narrate-again':
            row = voices.narrate(conn, store, user, run, outputs, body['voice_id'], rid, 'page', list(body.get('tweaks') or []) or None)
            return JSONResponse({'job': str(row['id'])})
        if action == 'final':
            out = voices.finalise(conn, store, user, run, outputs, body['job_id'], body.get('quote') or '', 'page')
            return JSONResponse({'recorded': True, 'next': (out.get('next') or {}).get('stage')})
        raise Problem(404, 'NOT_FOUND', 'No such action.')
