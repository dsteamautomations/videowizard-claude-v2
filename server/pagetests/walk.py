"""Walk the visuals page by hand: a small local server with the application's real server functions behind the buttons.

    "$TEMP/vw2venv/Scripts/python.exe" pagetests/walk.py --port 8765      (from server/), then open http://127.0.0.1:8765/

No real server, database, network or cost. Each scenario is a film held in memory, built as build_states.py builds its states.
Real: the page (visuals.html, base.html, style.css), and web.py's own visuals_data and _visuals_act (so its table of actions, the
visuals_stage functions behind it, core.load_run's open-defect gate, auth.current_user). They are called as they are; only what
they reach for is swapped here: the database connection (the unit tests' FakeConn, answering a few more questions), the storage
(FakeStore) and core.next_for (the run is always at the visuals stage).
Imitated: the worker (a queued set comes back about 3 s later, as build_states.sets_back writes it), the pictures (made here with
their name on them), sign-in (one button, no password), the prices (fixed, as in the unit tests).
"""
import argparse
import colorsys
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from functools import lru_cache
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ap = argparse.ArgumentParser()
ap.add_argument('--port', type=int, default=8765)
PORT = ap.parse_args().port
sys.argv = sys.argv[:1]   # build_states reads the command line when it is imported

import build_states as B   # noqa: E402  (puts server/ and server/unit on the path; fixes the prices)
from PIL import Image, ImageDraw, ImageFont   # noqa: E402
from app import auth, core, storage as storage_mod, web   # noqa: E402
from app.errors import Problem   # noqa: E402

VS, S, R, USER, NEW = B.VS, B.S, B.R, B.USER, B.NEW
REFS = B.REPO.parent / 'videobuilder-v4' / 'phase2' / 'refs'   # the real film's reference pictures, when this PC has them
TOKEN = 'walk'
RUN = {**NEW, 'film': {**NEW['film'], 'category': {'value': 'documentary-explainer'}}}   # a real film has its category recorded; a take's preparation reads it
BRIEF = [{'stage': 'brief', 'unit': None, 'summary': {'production': {'industry': 'other'}, 'audience': 'general'}}]   # and the brief's industry and audience
LOCK = threading.RLock()   # one request (or one turn of the worker) at a time
FILMS, NOW = {}, []        # the scenarios' films; NOW[0]: the film of the request being answered
WORKER_S = 3.0


# ---------- what the real functions reach for ----------

class Conn(B.Conn):
    """build_states' connection, answering what web.py, core and auth also ask a database."""
    film = None

    def execute(self, sql, params=()):
        f, one, many = self.film, None, None
        if 'insert into vw2_jobs' in sql and len(params) == 5:   # a picture or a set is queued: the row the spend counts and the worker finishes
            one = super().execute(sql, params).fetchone()
            self.jobs.append({'id': one['id'], 'unit': params[1], 'run_id': params[0], 'provider': params[4], 'status': 'queued', 'request': getattr(params[2], 'obj', params[2]), 'error': None, 'cost': None, 'result': None})
        elif 'from vw2_sessions' in sql:
            one = {'user_id': USER['id'], 'user_name': USER['name'], 'role': 'Admin', 'kind': 'browser', 'token_hash': params[0]} if params[0] == auth._hash(TOKEN) else None
        elif 'from vw2_runs' in sql:
            one = f.run
        elif 'from vw2_defects' in sql:
            many = [{'id': d} for d in f.defects]
        elif 'from vw2_stage_outputs' in sql:
            many = f.outputs
        elif 'advisory' in sql:
            one = {'got': True}
        elif 'from vw2_jobs where id=%s and run_id' in sql:   # one take, to select or reject
            one = next((j for j in self.jobs if j['id'] == params[0]), None)
        else:
            return super().execute(sql, params)
        return type('R', (), {'fetchone': lambda _: one, 'fetchall': lambda _: many or []})()


@contextmanager
def connect():
    yield NOW[0].conn


web.db_connect = auth.connect = connect
storage_mod.storage = lambda: NOW[0].store
core.next_for = lambda conn, run: {'stage': 'visuals', 'open_defects': core.open_defects(conn, run['id'])}


class Film:
    def __init__(self, name):
        store, conn, *rest = SCENARIOS[name][2]()
        conn.__class__, conn.film = Conn, self
        self.store, self.conn, self.outputs, self.seen = store, conn, rest[0] if rest else [], {}
        self.defects = [45] if name == 'held-run' else []
        self.run = {**RUN, 'code': name, 'title': SCENARIOS[name][0], 'status': 'open', 'owner_id': USER['id'], 'client_id': None}


def worker():
    """The image worker, imitated: a set that was queued comes back WORKER_S seconds after the last one was queued, as build_states.sets_back writes it."""
    while True:
        time.sleep(0.5)
        with LOCK:
            for f in FILMS.values():
                making = [r['id'] for r in S.saved(f.store)['references'].values() if r.get('kind') == 'sheet' and r.get('status') == 'generating']
                for rid in making:
                    f.seen.setdefault(rid, time.time())
                if making and time.time() - max(f.seen[r] for r in making) >= WORKER_S:
                    B.sets_back(f.store)
                    for j in f.conn.jobs:
                        if j['unit'] in making:
                            j['status'] = 'retained'


# ---------- the films ----------

def person(pid, name, description):
    return {**R.MASON, 'id': pid, 'name': name, 'requirements': f'{name.lower()}, as the film shows them', 'description': description}


def thing(tid, name, kind, **over):
    return {**R.KILN, 'id': tid, 'name': name, 'kind': kind, 'requirements': f'{name.lower()}, as the film shows it', **over}


BRICK = {**B.BRICK, 'id': 'brick_red_clay', 'name': 'Red clay brick'}
PEOPLE = [person('family_father', 'The father', 'a man of about forty-five, tall and lean, brown skin, short black hair greying at the temples, a trimmed moustache, a pale blue shirt and grey trousers'),
          person('family_mother', 'The mother', 'a woman of about forty, medium build, brown skin, long black hair in a single plait, a green cotton sari with a yellow border'),
          person('family_daughter', 'The daughter', 'a girl of about ten, slim, brown skin, two short plaits with red ribbons, a white school blouse and a navy pinafore'),
          person('neighbour', 'The neighbour', 'a man of about sixty, stout, dark skin, bald with a white beard, a white vest and a checked lungi'),
          person('lab_technician', 'The lab technician', 'a woman of about thirty, slight, fair skin, hair tied in a bun, clear safety glasses, a white lab coat over a maroon kurta'),
          person('worker_curing', 'The curing worker', 'a man of about twenty-five, muscular, very dark skin, curly hair under an orange cap, a faded red T-shirt and khaki shorts')]
PLACES = [thing('family_home', 'The family home', 'place'), thing('materials_lab', 'The materials lab', 'place')]
THINGS = [thing('compression_machine', 'The compression machine', 'object'), thing('water_hose', 'The water hose', 'object'), BRICK]
FAMILY = PEOPLE + PLACES + THINGS


def frame(fid, eid):
    return {**S.ref(fid, 'candidate'), 'kind': 'frame', 'element_id': eid, 'width': 1920, 'height': 1080}


def rows_of(els, frames=()):
    by = {}
    for fid, eid in frames:
        by.setdefault(eid, []).append(fid)
    return [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}] + [{'element_id': e['id'], 'prompt': f"{e['name']}: what the film must show", **({'frames': by[e['id']]} if e['id'] in by else {})} for e in els]


def round1(els, spec=True, frames=(), **kw):
    """A round at step 1 (build_states.step1, for elements of any name): the film, the footage pictures, the brick's spec approved or not, the round posted."""
    _, store, conn = B.film(els=tuple(els), **kw)
    B.edit(store, lambda s: s['references'].update({fid: frame(fid, eid) for fid, eid in frames}))
    if spec and BRICK in els:
        VS.approve_spec(store, USER, NEW, [], 'element:brick_red_clay', '')
    VS.round_start(store, USER, NEW, [], rows_of(els, frames), conn=conn)
    return store, conn


def round2(els=FAMILY, **kw):
    """Step 2 with every set back (build_states.step2)."""
    store, conn = round1(els, **kw)
    VS.round_done(store, USER, NEW, [], B.APPROVE(rows_of(els)), 'Yes, the frame.', conn=conn)
    return store, conn, B.sets_back(store)


def step1():
    return round1([*PEOPLE[:3], *THINGS], spec=False, frames=[('F2', 'compression_machine'), ('F3', 'water_hose')])


def step2():
    return round2()[:2]


def not_made():
    wall = thing('yard_wall', 'The yard wall', 'object', size=[{'part': 'wall', 'measure': 'height', 'value': None, 'unit': 'mm', 'source': '', 'status': 'unknown', 'tried': 'not in the client material'}])
    store, conn, s = round2([*PEOPLE[:2], PLACES[0], THINGS[0], BRICK, wall], spec=False)   # the brick's spec is not approved: its set is refused at Done
    # the wall: a footage picture of it is approved after its first set, then the set is refused (No); the server will not make it again before its height is measured
    B.edit(store, lambda x: x['references'].update(F9={**frame('F9', 'yard_wall'), 'status': 'approved'}))
    VS.round_sets(store, USER, NEW, [], {'yard_wall': {'verdict': 'no', 'words': 'the wall is too low'}}, 'Again.', conn=conn, partial=True)
    return store, conn


def second_pass():
    store, conn, s = round2()
    B.yes_all(store, conn, s, family_father={'verdict': 'no', 'words': 'too young'}, water_hose={'verdict': 'correct', 'words': 'a green hose, not a yellow one'})
    B.sets_back(store)
    return store, conn


def complete():
    store, conn, s = round2()
    B.yes_all(store, conn, s)
    return store, conn


def takes():
    g1 = [S.shot('DR1', 0, 500, 'drawn', element_ids=['E1'], depicts='the plinth in section')]
    g2 = [S.shot('VS1', 900, 1025, 'video', element_ids=['E1']), S.shot('VS2', 1025, 1150, 'video', element_ids=['E1'], subjects=[])]
    _, store, conn = B.complete(g1=g1, g2=g2)
    conn.files = {'run-1/uploads/wall-pour.mp4': {'key': 'run-1/uploads/wall-pour.mp4', 'sha256': 'sha-movie', 'bytes': 1000}}
    VS.add_asset(conn, store, USER, NEW, [], 'VS1', 'run-1/uploads/wall-pour.mp4', 'sha-movie', 1000, 'movie', 'My own shot of the pour.')
    B.edit(store, lambda s: (s['references'].update(K1=B.keyframe('K1', 'VS2', 'approved', role='start')), s['references']['F1'].update(element_kind='object')))
    # the ready take's preparation record, written by the real functions (bind, prepare_take); its job row as submit_take writes it: Select and Reject run the real select_take
    VS.bind(store, USER, RUN, BRIEF, 'VS2', {'E1': ['F1']}, {})
    VS.prepare_take(store, USER, RUN, BRIEF, {'shot_id': 'VS2', 'motion_prompt': 'water is poured along the top of the wall', 'subject_reconciliation': {}, 'start_image': 'K1',
                                              'continuity_notes': 'the wall and the yard light stay'})
    prep = S.saved(store)['preparations']['VS2']
    made = json.loads(store.get(prep['key']))
    # the drawing's record, as render_drawn writes it, with the fields select_take reads (its scene, font and cues need an uploaded SVG: not imitated)
    drawn = {'kind': 'drawn', 'shot_id': 'DR1', 'plan_digest': VS.digest(VS.current_plan(store, S.saved(store)))}
    dkey = VS.key(RUN, f'takes/{VS.digest(drawn)}.drawn.json')
    VS.save_json(store, dkey, drawn)
    B.edit(store, lambda s: s['preparations'].update(DR1={'preparation_id': VS.digest(drawn), 'key': dkey, 'drawn': True}))
    result = lambda jid, s, **more: {'key': f'run-1/visuals/takes/{jid}.mp4', 'sha256': 's-' + jid, 'bytes': 1000, 'evidence': {'duration_seconds': s, 'timing_matches_placement': True}, **more}
    conn.jobs += [B.take('job-take-1', 'VS2', request={'kind': 'take', 'preparation_id': prep['preparation_id'], 'request_key': prep['key'], 'provider': made['provider'], 'model': made['model'], 'duration_seconds': made['duration_seconds']},
                         result=result('job-take-1', 5.0)),
                  B.take('job-draw-1', 'DR1', provider='drawn', request={'kind': 'drawn', 'request_key': dkey, 'preparation_id': VS.digest(drawn), 'shot_id': 'DR1', 'frames': 500, 'duration_seconds': 20.0},
                         result=result('job-draw-1', 20.0, sheet_key='run-1/visuals/takes/job-draw-1.sheet.png'))]
    return store, conn, BRIEF


def specs():
    # build_states' drawing spec without its unknown size, so Approve can be pressed (with it the server refuses: a size is unknown)
    g1 = [S.shot('IM1', 0, 160, 'image', element_ids=['E1'], drawing_spec={**B.copy.deepcopy(B.DSPEC), 'dimensions': B.DSPEC['dimensions'][:1]}), S.shot('IM2', 160, 330, 'image', element_ids=['E1']), S.shot('IM3', 330, 500, 'image', element_ids=['E1'])]
    _, store, conn = B.complete(g1=g1)
    B.edit(store, lambda s: s['references'].update(K2=B.keyframe('K2', 'IM2'), K3=B.keyframe('K3', 'IM3')))
    VS.approve_reference(store, USER, NEW, [], 'K3', 'sha-K3', 'Yes.', conn=conn)
    return store, conn


def large():
    return B.STATES['cross-large-round-58-elements'][2]()[:2]


SCENARIOS = {   # name: (title, what to try, builder)
    'round-step1': ('Reference round, step 1', 'Answer the three footage pictures (use or ignore), approve the brick\'s material spec (or leave it and see what will not be made), then press Done. The sets are "being made" for about 3 seconds, then step 2 opens.', step1),
    'round-step2': ('Reference round, step 2: every set is back', 'Choose the starting picture of each thing, answer Yes / No / Correct it with words, leave the page and come back (the answers stay), press Done and read what it asks before it records.', step2),
    'round-step2-not-made': ('Step 2 with two sets that were not made', 'Read the reason on the brick and on the yard wall. The brick: approve its material spec, then "Make it now". The wall waits for a size the assistant measures; nothing on the page settles it (and nothing here does), so it offers no "Make it now": set it aside, then bring it back.', not_made),
    'round-second-pass': ('Step 2, second pass', 'Some sets were approved by the first Done; the father and the water hose were made again and wait for an answer.', second_pass),
    'round-complete': ('The round finished', 'Nothing waits; look at what was approved.', complete),
    'takes-supplied': ('Takes: a supplied file, a take to select, a drawn shot', 'Open Takes: one shot is filled with a file you supplied, one take is ready and one shot is drawn: Select or Reject each, then change your mind (a rejected one can be selected, a selected one rejected).', takes),
    'pictures-specs': ('Pictures: a drawing spec, a candidate, an approved picture', 'Open Pictures: approve or correct the drawing spec waiting on its shot, approve or reject the candidate picture.', specs),
    'large-round': ('A large round: 58 elements at step 2', 'Scroll, filter "Waiting for me", press Next waiting, answer a few and press Done.', large),
    'held-run': ('A run held by an open defect', 'Every button that writes is refused with the defect\'s message; reading still works.', step2),
}


# ---------- pictures ----------

def font(px):
    try:
        return ImageFont.truetype('arial.ttf', px)
    except OSError:
        return ImageFont.load_default(px)


@lru_cache(maxsize=None)
def picture(lines, seed, real, small):
    """(bytes, type) of a picture that says what it is: a coloured PNG card with the words in large letters, or the real reference picture with a tag (a JPEG: quick to make)."""
    if real:
        img = Image.open(real).convert('RGB')
        d, f = ImageDraw.Draw(img), font(max(24, img.width // 16))
        box = d.textbbox((20, 20), lines[-1], font=f)
        d.rectangle((box[0] - 14, box[1] - 14, box[2] + 14, box[3] + 14), fill=(255, 255, 255))
        d.text((20, 20), lines[-1], font=f, fill=(0, 0, 0))
    else:
        hue = int(hashlib.md5(seed.encode()).hexdigest()[:4], 16) / 65535
        img = Image.new('RGB', (1280, 720), tuple(round(c * 255) for c in colorsys.hls_to_rgb(hue, 0.78, 0.6)))
        d = ImageDraw.Draw(img)
        for k, line in enumerate(lines):
            f = font(96 if len(line) < 20 else 64 if len(line) < 32 else 40)
            d.text((640, 360 + (k - (len(lines) - 1) / 2) * 130), line, font=f, fill=(20, 20, 20), anchor='mm')
    if small and img.width > web.THUMB_WIDTH:
        img = img.resize((web.THUMB_WIDTH, round(img.height * web.THUMB_WIDTH / img.width)))
    buf = io.BytesIO()
    img.save(buf, 'JPEG' if real else 'PNG')
    return buf.getvalue(), 'image/jpeg' if real else 'image/png'


def picture_of(film, key):
    """What picture() needs to draw the picture stored under this key: its words, its colour, the real file when there is one."""
    s = S.saved(film.store)
    names = {e['id']: e['name'] for e in json.loads(film.store.get(s['versions'][-1]['file']['key']))['document']['elements']} if s.get('versions') else {}
    r = next((r for r in s['references'].values() if r.get('key') == key), None)
    if not r:
        return (Path(key).name,), key, None
    eid = r.get('element_id') or ''
    if r.get('kind') == 'sheet':
        real = REFS / f'{eid}.png'
        return (names.get(eid, eid), f"picture {r.get('set_n') or 1}"), eid, str(real) if real.is_file() else None
    if r.get('kind') == 'frame':
        return (names.get(eid, eid), 'footage picture'), eid + '-footage', None
    return (f"picture for shot {r['shot_id']}" if r.get('shot_id') else names.get(eid, eid), r['id']), key, None


@lru_cache(maxsize=None)
def clip():
    """A few seconds of test film for every take, when ffmpeg is on this PC; else an empty file, as in the page tests."""
    if not shutil.which('ffmpeg'):
        return b''
    out = Path(tempfile.mkdtemp(prefix='vw2-walk-')) / 'take.mp4'
    done = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=640x360:rate=25', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-y', str(out)], capture_output=True)
    return out.read_bytes() if done.returncode == 0 else b''


# ---------- the pages of the walk itself ----------

def shell(title, body):
    return f'<!doctype html><meta charset="utf-8"><title>{title}</title><style>body{{font:16px/1.5 system-ui,sans-serif;max-width:900px;margin:2em auto;padding:0 1em}}li{{margin:.9em 0}}small{{color:#555}}button{{font:inherit;padding:.4em 1em}}</style><h1>{title}</h1>{body}'


def index():
    items = ''.join(f'<li><a href="/runs/{n}/visuals"><b>{t}</b></a> &nbsp; <small><a href="/reset/{n}">start this one again</a></small><br>{what}</li>' for n, (t, what, _) in SCENARIOS.items())
    return shell('Walk the visuals page', f'''<p>Each line opens the real page on a small film held in this PC's memory. The buttons run the application's real server functions; nothing reaches the real server, and nothing costs money.</p>
<ul>{items}</ul>
<p><a href="/reset-all">Start every one again</a> &nbsp;·&nbsp; <a href="/signout">Sign out</a> (to see the page send you to sign in, and bring you back)</p>
<p><small>Imitated here: the worker (a set comes back about 3 seconds after it is asked for), the pictures (cards with their name on them; the real reference pictures where this PC has them), sign-in (one button), the prices (₹20 a picture, and each set counts as one picture in the spend). The page reads its data again every 60 seconds, as on the real server.</small></p>''')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def out(self, status, body=b'', ctype='text/html; charset=utf-8', **headers):
        body = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        for k, v in {'Content-Type': ctype, 'Content-Length': str(len(body)), 'Cache-Control': 'no-store', **{k.replace('_', '-'): v for k, v in headers.items()}}.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def real(self, fn):
        """One of web.py's own functions; a refusal is answered as main.py answers a Problem."""
        try:
            r = fn()
            return self.out(r.status_code, r.body, 'application/json')
        except Problem as exc:
            return self.out(exc.status, json.dumps(core.jsonable({'code': exc.code, 'message': exc.message, **exc.extra})), 'application/json')
        except Exception as exc:   # something the walk does not imitate (a provider, a table of the database)
            return self.out(500, json.dumps({'code': 'WALK', 'message': f'Not imitated on the walk server: {type(exc).__name__}: {exc}'}), 'application/json')

    def do_GET(self):
        with LOCK:
            draw = self.route()
        if draw:   # a picture is drawn after the lock is given back, so the buttons never wait for it
            self.out(200, *draw())

    do_POST = do_GET

    def route(self):
        url = urlsplit(self.path)
        parts = [unquote(p) for p in url.path.strip('/').split('/')]
        cookie = SimpleCookie(self.headers.get('Cookie', '')).get('vw2_session')
        token = cookie.value if cookie else None
        sign = f'vw2_session={TOKEN}; Path=/; HttpOnly; SameSite=Strict'
        post = self.command == 'POST'
        body = self.rfile.read(int(self.headers.get('Content-Length') or 0)) if post else b''
        if parts in ([''], ['runs']):
            return self.out(200, index(), Set_Cookie=sign)
        if parts == ['static', 'style.css']:
            return self.out(200, (B.SERVER / 'app' / 'static' / 'style.css').read_bytes(), 'text/css')
        if parts == ['login']:
            nxt = (parse_qs(body.decode()) if post else parse_qs(url.query)).get('next', ['/'])[0]
            nxt = nxt if nxt.startswith('/') and not nxt.startswith('//') else '/'
            if post:
                return self.out(303, Location=nxt, Set_Cookie=sign)
            return self.out(200, shell('Sign in', f'<p>You are signed out. On the real server this is the page with your name and password; here one button signs you in.</p><form method="post" action="/login"><input type="hidden" name="next" value="{nxt.replace(chr(34), "&quot;")}"><button>Sign in as SK</button></form>'))
        if parts == ['signout']:
            return self.out(200, shell('Signed out', '<p>Go back to a page you had open and press a button, or wait for it to read its data: it sends you to sign in and brings you back to the same card.</p><p><a href="/">Back to the list</a> (this signs you in again)</p>'), Set_Cookie='vw2_session=; Path=/; Max-Age=0')
        if parts == ['reset-all'] or (parts[0] == 'reset' and parts[1:2] and parts[1] in SCENARIOS):
            for n in (SCENARIOS if parts == ['reset-all'] else parts[1:2]):
                FILMS[n] = Film(n)
            return self.out(303, Location='/')
        film = FILMS.get(parts[1]) if parts[0] == 'runs' and len(parts) > 2 else None
        if not film:
            return self.out(404, shell('Not on the walk server', '<p>This page is not part of the walk. <a href="/">Back to the list</a></p>'))
        NOW[:] = [film]
        name, rest = parts[1], parts[2:]
        if rest == ['visuals', 'data'] and not post:
            return self.real(lambda: web.visuals_data(None, name, token))
        if rest == ['visuals', 'act'] and post:
            return self.real(lambda: web._visuals_act(name, token, json.loads(body or b'{}')))
        if not token:   # web.py login_redirect
            return self.out(303, Location='/login?next=' + url.path)
        if rest == ['visuals']:   # rendered as the page tests render it, with web.py's own template environment (its `version` too)
            return self.out(200, web.templates.env.get_template('visuals.html').render(run={'code': name}, user={'name': USER['name'], 'role': 'Admin'}, request=None))
        if rest[0] in ('file', 'thumb') and rest[1:]:
            key = '/'.join(rest[1:])
            if key.endswith('.mp4'):
                return self.out(200, clip(), 'video/mp4')
            if key in film.store.files:   # a picture the operator uploaded on the page: the stored file itself
                return self.out(200, film.store.files[key], 'image/png')
            what = picture_of(film, key)
            return lambda: picture(*what, rest[0] == 'thumb')
        return self.out(404, 'Not found.', 'text/plain')


if __name__ == '__main__':
    for n in SCENARIOS:
        FILMS[n] = Film(n)
    threading.Thread(target=worker, daemon=True).start()
    print(f'Walk the visuals page: http://127.0.0.1:{PORT}/   (Ctrl+C stops it)', flush=True)
    try:
        ThreadingHTTPServer.request_queue_size = 128   # a page asks for all its pictures at once; the default of 5 refuses some
        ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
