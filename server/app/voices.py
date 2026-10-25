"""Voices beyond one run (design/52 A, B): compact catalog rows, the account line, the register of favourites, release and
restore of library copies, the usage directory, and a run's voice page state (shortlist, pick, narrations, final).
The pure parts take plain dicts; the database and storage parts are below them."""
import json
from datetime import datetime, timezone

from psycopg.types.json import Json

from . import elevenlabs, jobs
from . import voice_direction as VD
from .errors import Problem

DESCRIPTION_CHARS = 160
PAGE_CONTRACT = 'vw2-voice-page-v2'
TRYOUT_MAX, NARRATE_MAX = 6, 3   # design/54
STEPS = ('browse', 'try', 'narrations', 'final')   # design/55: four steps


# ---------- pure ----------

def _day(value):
    return value.date().isoformat() if isinstance(value, datetime) else str(value)[:10]


def aggregate(job_rows, output_rows):
    """The usage directory from ready jobs and accepted voice outputs: per voice, where it was auditioned, narrated and final."""
    out = {}

    def entry(voice_id, name):
        return out.setdefault(voice_id, {'name': name, 'narrations': 0, 'auditions': 0, 'final_in': [], 'narrated_in': [], 'auditioned_in': [], 'last_used': ''})

    def place(row):
        return {'code': row.get('code'), 'title': row.get('title') or '', 'client': row.get('client') or '', 'date': _day(row['created_at'])}

    for j in job_rows:
        req = j.get('request') or {}
        if j.get('status') != 'ready' or not req.get('voice_id'):
            continue
        e = entry(req['voice_id'], req.get('name') or '')
        kind = 'narrations' if req.get('kind') == 'narration' else 'auditions'
        e[kind] += 1
        e['narrated_in' if kind == 'narrations' else 'auditioned_in'].append(place(j))
        e['last_used'] = max(e['last_used'], _day(j['created_at']))
    for o in output_rows:
        s = o.get('summary') or {}
        if not s.get('voice_id'):
            continue
        e = entry(s['voice_id'], s.get('name') or '')
        e['final_in'].append(place(o))
        e['last_used'] = max(e['last_used'], _day(o['created_at']))
    return out


def release_refusal(row):
    if not row:
        return 'not in the register'
    if row.get('source') == 'custom':
        return 'custom voices are never deleted here'
    if row.get('favourite'):
        return f"favourite since {_day(row.get('favourite_at'))}, by {row.get('favourite_by') or 'someone'}; unmark it first"
    return None


def new_page_state():
    return {'contract': PAGE_CONTRACT, 'shortlist': [], 'excerpt': None, 'pick': None, 'narrations': [], 'final': None, 'step': 'browse', 'tried': []}


def set_step(state, step):
    if step not in STEPS:
        raise Problem(422, 'STEP', 'step must be one of ' + ', '.join(STEPS))
    state['step'] = step


def sub_request_id(request_id, i):
    """One idempotency id per voice of a multi-voice action, as a UUID (the column's type): derived from the action's id, so a retry maps to the same jobs."""
    import uuid
    try:
        base = uuid.UUID(str(request_id))
    except ValueError:
        base = uuid.uuid5(uuid.NAMESPACE_URL, str(request_id))
    return str(uuid.uuid5(base, str(i)))


def check_cap(voice_ids, cap, what):
    names = {6: 'six', 3: 'three'}
    if not voice_ids:
        raise Problem(422, 'VOICES', f'Pick at least one voice for the {what}.')
    if len(voice_ids) > cap:
        raise Problem(422, 'VOICES', f'At most {names.get(cap, cap)} voices per {what}; {len(voice_ids)} given.')
    if len(set(voice_ids)) != len(voice_ids):
        raise Problem(422, 'VOICES', 'The same voice is listed twice.')


def add_narration(state, narration):
    same = [n for n in state['narrations'] if n['voice_id'] == narration['voice_id']]
    state['narrations'].append({**narration, 'number': len(same) + 1})


def mark_direction_change(state, new_digest):
    for n in state['narrations']:
        if n.get('direction_digest') != new_digest:
            n['made_before_direction_change'] = True


def final_body(job, source_script, beats, quote, direction, recorded_from='page'):
    """The voice stage output from a kept narration, the same shape the plugin records in chat."""
    req, res = job['request'], job['result']
    if req.get('source_script') != source_script:
        raise Problem(409, 'SCRIPT_CHANGED', 'The narration was generated for a different script version. Narrate again.')
    voice = {'job_id': str(job['id']), 'voice_id': req['voice_id'], 'name': req.get('name'), 'model_id': req.get('model_id'), 'settings': req.get('settings'),
             'duration_s': res.get('duration_s'), 'source_script': req.get('source_script'), 'beats': beats, 'direction_digest': req.get('direction_digest'),
             'tweaks': req.get('tweaks') or []}
    files = [{'name': 'narration.mp3', 'key': res['audio_key'], 'sha256': res['sha256'], 'bytes': res['bytes'], 'location': 'storage', 'receipt': True},
             {'name': 'timing.json', 'key': res['timing_key'], 'sha256': res['timing_sha256'], 'bytes': res['timing_bytes'], 'location': 'storage', 'receipt': True}]
    summary = {**voice, 'cost': job.get('cost'), 'content_digest': source_script, 'direction': direction, 'recorded_from': recorded_from,
               'recorded_at': datetime.now(timezone.utc).isoformat()}
    return {'stage': 'voice', 'unit': None, 'files': files, 'summary': summary, 'accepted_quote': quote}


BREATHING_PAUSE_S = 0.8


def beat_rows(script, timing):
    """Measured narration per beat from the word timing (the plugin's voice_record does the same in chat)."""
    words = timing.get('words') or []
    rows = []
    for b in script.get('beats') or []:
        own = [w for w in words if w['passage_id'] == b['passage_id']]
        if not own:
            raise Problem(409, 'TIMING', f"Narration timing has no words for {b['beat_id']}; narrate the accepted script again.")
        measured = round(own[-1]['end_s'] - own[0]['start_s'], 3)
        rows.append({'beat_id': b['beat_id'], 'passage_id': b['passage_id'], 'start_s': own[0]['start_s'], 'end_s': own[-1]['end_s'], 'measured_vo_duration_s': measured,
                     'breathing_pause_s': BREATHING_PAUSE_S, 'target_beat_duration_s': round(measured + BREATHING_PAUSE_S, 3), 'words': len(own)})
    return rows


# ---------- live search of the provider's library (design/55) ----------

SORTS = ('trending', 'created_date', 'usage_character_count_1y', 'cloned_by_count')
SEARCH_PAGE, SEARCH_CACHE_S = 100, 120
_SEARCH = {}


def search_params(q):
    """The provider's query for one search: 100 a page, the operator's filters, trending unless asked otherwise."""
    p = {'page_size': SEARCH_PAGE, 'page': int(q.get('page') or 0)}
    for ours, theirs in (('language', 'language'), ('accent', 'accent'), ('gender', 'gender'), ('age', 'age'), ('use_case', 'use_cases'), ('search', 'search'), ('category', 'category')):
        v = (q.get(ours) or '').strip()
        if v:
            p[theirs] = v
    p['sort'] = q.get('sort') if q.get('sort') in SORTS else 'trending'
    return p


def _row_from_shared(v):
    desc = (v.get('description') or '').strip()
    return {'voice_id': v['voice_id'], 'name': v.get('name') or '', 'accent': v.get('accent') or '', 'gender': v.get('gender') or '', 'age': v.get('age') or '',
            'use_case': v.get('use_case') or '', 'descriptive': v.get('descriptive') or '', 'language': v.get('language') or '',
            'description': desc[:DESCRIPTION_CHARS].rstrip() + ('…' if len(desc) > DESCRIPTION_CHARS else ''), 'preview_url': v.get('preview_url') or '',
            'category': v.get('category') or '', 'on_account': bool(v.get('is_added_by_user')), 'popularity': v.get('cloned_by_count') or 0,
            'library': {'public_owner_id': v.get('public_owner_id'), 'original_voice_id': v['voice_id']} if v.get('public_owner_id') else None}


def _row_from_account(v):
    labels = v.get('labels') or {}
    sharing = v.get('sharing') or {}
    desc = (v.get('description') or '').strip()
    return {'voice_id': v['voice_id'], 'name': v.get('name') or '', 'accent': labels.get('accent') or '', 'gender': labels.get('gender') or '', 'age': labels.get('age') or '',
            'use_case': labels.get('use_case') or '', 'descriptive': labels.get('descriptive') or '', 'language': labels.get('language') or '',
            'description': desc[:DESCRIPTION_CHARS].rstrip() + ('…' if len(desc) > DESCRIPTION_CHARS else ''), 'preview_url': v.get('preview_url') or '',
            'category': v.get('category') or '', 'on_account': True, 'popularity': 0,
            'library': {'public_owner_id': sharing['public_owner_id'], 'original_voice_id': sharing.get('original_voice_id') or v['voice_id']} if sharing.get('public_owner_id') else None}


def _decorate(conn, rows):
    reg = register_rows(conn, [r['voice_id'] for r in rows]) if rows else {}
    usage = history(conn)
    for r in rows:
        f, u = reg.get(r['voice_id']) or {}, usage.get(r['voice_id']) or {}
        r.update(favourite=bool(f.get('favourite')), note=f.get('note') or '', narrations=u.get('narrations') or 0, auditions=u.get('auditions') or 0, last_used=u.get('last_used') or '')
    remember_many(conn, [r for r in rows if r.get('library')])   # defect 16: the identity an audition needs, one statement for the page
    return rows


def _label_match(r, q):
    return all(not q.get(k) or (r.get(k) or '').lower() == q[k].lower() for k in ('language', 'accent', 'gender', 'age', 'use_case')) and \
        (not q.get('search') or q['search'].lower() in f"{r.get('name', '')} {r.get('description', '')} {r.get('descriptive', '')}".lower())


_MINE = {'at': 0.0, 'rows': None}


def my_voices(provider):
    """Every voice on the account, as rows (one or two pages of 100); cached a minute, the page polls every ten seconds."""
    import time
    if _MINE['rows'] is not None and time.time() - _MINE['at'] < 60:
        return _MINE['rows']
    rows, cursor, seen = [], '', set()
    while True:
        data = provider.request('GET', '/v2/voices', params={'page_size': 100, **({'next_page_token': cursor} if cursor else {})}).json()
        rows.extend(_row_from_account(v) for v in data.get('voices', []))
        cursor = data.get('next_page_token') if data.get('has_more') else None
        if not cursor or cursor in seen:
            _MINE.update(at=time.time(), rows=rows)
            return rows
        seen.add(cursor)


def search(conn, provider, q):
    """One search of the library, the account or the favourites with the operator's filters: 100 rows a page, compact, joined with the register and the usage;
    cached two minutes per query so paging through the 100 is instant."""
    import json as _json
    import time
    tab = q.get('tab') or 'explore'
    key = _json.dumps({**q, 'tab': tab}, sort_keys=True, default=str)
    hit = _SEARCH.get(key)
    if hit and time.time() - hit['at'] < SEARCH_CACHE_S:
        return hit['out']
    if tab == 'explore':
        data = provider.request('GET', '/v1/shared-voices', params=search_params(q)).json()
        rows = [_row_from_shared(v) for v in data.get('voices', [])]
        out = {'voices': _decorate(conn, rows), 'total': data.get('total_count') or len(rows), 'has_more': bool(data.get('has_more')), 'page': int(q.get('page') or 0), 'tab': tab}
    elif tab == 'mine':
        rows = [r for r in my_voices(provider) if _label_match(r, q)]
        out = {'voices': _decorate(conn, rows), 'total': len(rows), 'has_more': False, 'page': 0, 'tab': tab}
    else:
        reg = {k: v for k, v in register_rows(conn).items() if v.get('favourite')}
        mine = {r['voice_id']: r for r in my_voices(provider)}
        rows = []
        for vid, f in reg.items():
            if vid in mine:
                rows.append(mine[vid])
            else:
                rows.append({'voice_id': vid, 'name': f.get('name') or vid, 'accent': '', 'gender': '', 'age': '', 'use_case': '', 'descriptive': '', 'language': '', 'description': '',
                             'preview_url': '', 'category': '', 'on_account': False, 'popularity': 0, 'missing': True,
                             'library': {'public_owner_id': f['public_owner_id'], 'original_voice_id': f.get('original_voice_id') or vid} if f.get('public_owner_id') else None})
        rows = [r for r in rows if _label_match(r, q)]
        out = {'voices': _decorate(conn, rows), 'total': len(rows), 'has_more': False, 'page': 0, 'tab': tab}
    _SEARCH[key] = {'at': time.time(), 'out': out}
    if len(_SEARCH) > 200:
        _SEARCH.pop(next(iter(_SEARCH)))
    return out


def known_voices(last_voice, favourites, mine):
    """design/55: voices the operator already knows, narratable without a tryout: last film's narrator, the favourites, the account's voices."""
    out, seen = [], set()
    for row, why in ([(last_voice, 'last film')] if last_voice else []) + [(f, 'favourite') for f in favourites or [] if not f.get('missing')] + [(m, 'in my voices') for m in mine or []]:
        if row and row.get('voice_id') and row['voice_id'] not in seen:
            seen.add(row['voice_id'])
            out.append({'voice_id': row['voice_id'], 'name': row.get('name') or row['voice_id'], 'why': why, 'preview_url': row.get('preview_url') or ''})
    return out


# ---------- the register and the account (database + provider) ----------

def register_rows(conn, voice_ids=None):
    sql = 'select * from vw2_voices' + (' where voice_id = any(%s)' if voice_ids is not None else '')
    rows = conn.execute(sql, (list(voice_ids),) if voice_ids is not None else ()).fetchall()
    return {r['voice_id']: dict(r) for r in rows}


def remember(conn, voice, source=None):
    """A register row the first time a voice is auditioned, narrated, favourited or released. Never downgrades a library identity."""
    lib = voice.get('library_identity') or voice.get('library') or {}
    source = source or ('library' if lib else 'custom')
    conn.execute('''insert into vw2_voices(voice_id, name, source, public_owner_id, original_voice_id) values (%s,%s,%s,%s,%s)
                    on conflict (voice_id) do update set name = excluded.name, public_owner_id = coalesce(vw2_voices.public_owner_id, excluded.public_owner_id),
                    original_voice_id = coalesce(vw2_voices.original_voice_id, excluded.original_voice_id), updated_at = now()''',
                 (voice['voice_id'], voice.get('name') or '', source, lib.get('public_owner_id'), lib.get('original_voice_id')))


def remember_many(conn, rows):
    """The register rows of listed library voices in one batched statement (a search lists up to 100)."""
    if not rows:
        return
    with conn.cursor() as cur:
        cur.executemany('''insert into vw2_voices(voice_id, name, source, public_owner_id, original_voice_id) values (%(voice_id)s, %(name)s, 'library', %(owner)s, %(orig)s)
                           on conflict (voice_id) do update set name = excluded.name, public_owner_id = coalesce(vw2_voices.public_owner_id, excluded.public_owner_id),
                           original_voice_id = coalesce(vw2_voices.original_voice_id, excluded.original_voice_id), updated_at = now()''',
                        [{'voice_id': r['voice_id'], 'name': r.get('name') or '', 'owner': r['library'].get('public_owner_id'), 'orig': r['library'].get('original_voice_id')} for r in rows])


def event(conn, voice_id, what, user, note=''):
    conn.execute('insert into vw2_voice_events(voice_id, event, by_id, by_name, note) values (%s,%s,%s,%s,%s)', (voice_id, what, user['id'], user['name'], note or ''))


def set_favourite(conn, provider, user, voice_id, on, note=''):
    rows = register_rows(conn, [voice_id])
    if voice_id not in rows:
        remember(conn, provider.voice(voice_id))
    if on:
        conn.execute('update vw2_voices set favourite = true, favourite_by = %s, favourite_at = now(), note = %s, updated_at = now() where voice_id = %s', (user['name'], note or '', voice_id))
    else:
        conn.execute('update vw2_voices set favourite = false, updated_at = now() where voice_id = %s', (voice_id,))
    event(conn, voice_id, 'favourite' if on else 'unfavourite', user, note)
    return register_rows(conn, [voice_id])[voice_id]


def ensure_on_account(conn, provider, voice_id):
    """Defect 16 (VW-6): a voice the operator chose is checked with the provider; a library voice not yet on the account is saved there
    from its remembered identity (no custom slot used), on both front ends. Returns (voice, saved_now)."""
    try:
        return provider.voice(voice_id), False
    except Problem as exc:
        if 'voice_not_found' not in (exc.message or ''):
            raise
    row = register_rows(conn, [voice_id]).get(voice_id) or {}
    if not row.get('public_owner_id'):   # design/56 L11: the refusal names the exact command
        how = (f'Run `vw voice catalog --search "{row["name"]}"` (the tool remembers the library voices it lists), then submit again.' if row.get('name') else
               f'The tool has never listed {voice_id}: run `vw voice catalog` with filters that show it, or `vw voice add-library --owner <id> --voice <id>`.')
        raise Problem(409, 'VOICE_NOT_ON_ACCOUNT', f'{voice_id} is not on the ElevenLabs account and the tool knows no library identity for it. {how}')
    voice = elevenlabs.add_library_voice(provider, row['public_owner_id'], row.get('original_voice_id') or voice_id)
    remember(conn, voice, 'library')
    return voice, True


def preview_link(conn, provider, voice_id):
    """The sample link of a voice on the account; a library voice carries its link in every search row, so the page never needs this for one."""
    return provider.voice(voice_id).get('preview_url') or ''


_ACCOUNT = {'at': 0.0, 'row': None}


def account(provider):
    """The plan's slots, operations and characters; cached a minute (the page polls every ten seconds)."""
    import time
    if _ACCOUNT['row'] is not None and time.time() - _ACCOUNT['at'] < 60:
        return _ACCOUNT['row']
    d = provider.request('GET', '/v1/user/subscription').json()
    keys = ('tier', 'voice_limit', 'voice_slots_used', 'voice_add_edit_counter', 'max_voice_add_edits', 'character_count', 'character_limit', 'next_character_count_reset_unix')
    _ACCOUNT.update(at=time.time(), row={k: d.get(k) for k in keys})
    return _ACCOUNT['row']


def release(conn, provider, user, voice_id):
    rows = register_rows(conn, [voice_id])
    reason = release_refusal(rows.get(voice_id))
    if reason:
        raise Problem(409, 'RELEASE_REFUSED', f'Release refused: {reason}.')
    provider.request('DELETE', '/v1/voices/' + elevenlabs.identifier(voice_id))
    event(conn, voice_id, 'release', user)
    return {'voice_id': voice_id, 'released': True}


def restore(conn, provider, user, voice_id):
    row = register_rows(conn, [voice_id]).get(voice_id)
    if not row or not row.get('public_owner_id'):
        raise Problem(409, 'RESTORE_REFUSED', 'This voice has no stored library identity; it cannot be saved again from here.')
    try:
        voice = elevenlabs.add_library_voice(provider, row['public_owner_id'], row['original_voice_id'] or voice_id)
    except Problem as exc:
        if exc.code == 'LIBRARY_VOICE_UNAVAILABLE':
            raise Problem(409, 'WITHDRAWN', 'This voice was withdrawn from the library; it is unrecoverable.') from None
        raise
    event(conn, voice_id, 'restore', user)
    if voice['voice_id'] != voice_id:   # the account copy got a new id: carry the favourite mark over
        conn.execute('''insert into vw2_voices(voice_id, name, source, public_owner_id, original_voice_id, favourite, favourite_by, favourite_at, note)
                        select %s, name, source, public_owner_id, original_voice_id, favourite, favourite_by, favourite_at, note from vw2_voices where voice_id = %s
                        on conflict (voice_id) do nothing''', (voice['voice_id'], voice_id))
    return voice


def history(conn, voice_id=None):
    where = ' and j.request->>%s = %s' if voice_id else ''
    jobs_sql = f'''select j.request, j.status, j.created_at, r.code, r.title, r.client from vw2_jobs j join vw2_runs r on r.id = j.run_id
                   where j.stage = 'voice'{where} order by j.created_at'''
    outs_sql = f'''select o.summary, o.created_at, r.code, r.title, r.client from vw2_stage_outputs o join vw2_runs r on r.id = o.run_id
                   where o.stage = 'voice' and o.unit is null and not o.stale{' and o.summary->>%s = %s' if voice_id else ''} order by o.created_at'''
    params = ('voice_id', voice_id) if voice_id else ()
    return aggregate(conn.execute(jobs_sql, params).fetchall(), conn.execute(outs_sql, params).fetchall())


# ---------- a run's voice page state and direction (storage) ----------

def _key(run, name):
    return f"{run['id']}/voice/{name}"


def load_doc(store, run, name, default):
    key = _key(run, name)
    if not store.exists(key):
        return default() if callable(default) else default
    try:
        return json.loads(store.get(key).decode('utf-8'))
    except ValueError:
        raise Problem(502, 'STORAGE', f'{name} could not be read.') from None


def save_doc(store, run, name, doc):
    store.put(_key(run, name), json.dumps(doc, ensure_ascii=False, indent=1).encode('utf-8'), 'application/json')


def page_state(store, run):
    return load_doc(store, run, 'page.json', new_page_state)


def direction_of(store, run):
    return load_doc(store, run, 'direction.json', None)


def script_text(store, outputs):
    script_o = next((o for o in outputs if o['stage'] == 'script' and o['unit'] is None), None)
    if not script_o:
        raise Problem(409, 'NOT_ALLOWED', 'Voice needs an accepted script first.')
    ref = next((f for f in (script_o['files'] or []) if f.get('name') == 'script.json' and f.get('key')), None)
    if not ref:
        raise Problem(409, 'NOT_ALLOWED', 'The accepted script is not in storage; re-record the script.')
    doc = json.loads(store.get(ref['key']).decode('utf-8'))
    return doc, script_o


def record_direction(store, run, outputs, body, user):
    """The base list for this run: the chosen option applied to the accepted script; 'none' is an empty list. A change after
    narrations exist marks them."""
    script, _ = script_text(store, outputs)
    chosen = body.get('chosen')
    if chosen not in ('best_fit', 'experimental', 'none'):
        raise Problem(422, 'DIRECTION', 'chosen must be best_fit, experimental or none.')
    items = [] if chosen == 'none' else list(body.get('items') or [])
    register = '' if chosen == 'none' else (body.get('register') or '')
    if chosen != 'none':
        problems = VD.validate({'register': register, 'items': items}, script['spoken_text'])
        if problems:
            raise Problem(422, 'DIRECTION', 'The direction list was refused: ' + '; '.join(problems[:6]), problems=problems)
    digest = VD.digest(items, register)
    passages = body.get('test_passages') or []   # design/54 B: three test passages proposed by the assistant, one chosen by the operator
    problems = VD.validate_passages(passages, script['spoken_text'])
    if problems:
        raise Problem(422, 'DIRECTION', 'The test passages were refused: ' + '; '.join(problems[:4]), problems=problems)
    choice = body.get('passage')
    if passages and not (isinstance(choice, int) and 1 <= choice <= len(passages)):
        raise Problem(422, 'DIRECTION', f'passage must be 1 to {len(passages)}: the test passage the operator chose.')
    chosen_passage = None
    if passages:
        pp = passages[choice - 1]
        chosen_passage = {'n': choice, **pp, 'words': pp['last_word'] - pp['first_word'] + 1, 'text': VD.passage_text(script['spoken_text'], pp['first_word'], pp['last_word'])}
    doc = {'contract': 'vw2-voice-direction-v2', 'kind_of_film': body.get('kind_of_film') or '', 'options': body.get('options') or {}, 'registers': body.get('registers') or {},
           'chosen': chosen, 'register': register, 'base': items, 'digest': digest, 'approved_by': user['name'], 'at': datetime.now(timezone.utc).isoformat(),
           'quote': body.get('quote') or '', 'tweaks': (direction_of(store, run) or {}).get('tweaks') or {},
           'test_passages': passages, 'passage': chosen_passage, 'sentences': len(VD.sentences_of(script['spoken_text']))}
    state = page_state(store, run)
    previous = direction_of(store, run)
    if previous and previous.get('digest') != digest and state['narrations']:
        mark_direction_change(state, digest)
        save_doc(store, run, 'page.json', state)
    save_doc(store, run, 'direction.json', doc)
    return {'chosen': chosen, 'digest': digest, 'items': len(items), 'register': register, 'passage': choice if passages else None, 'sentences': doc['sentences']}


def set_tweaks(store, run, outputs, voice_id, tweaks):
    doc = direction_of(store, run)
    if not doc:
        raise Problem(409, 'NOT_ALLOWED', 'Record the direction first (vw voice direct record).')
    script, _ = script_text(store, outputs)
    problems = VD.validate({'register': doc.get('register') or '[measured]', 'items': tweaks}, script['spoken_text'])
    if problems:
        raise Problem(422, 'DIRECTION', 'The tweaks were refused: ' + '; '.join(problems[:6]), problems=problems)
    doc.setdefault('tweaks', {})[voice_id] = [{'passage_id': t['passage_id'], 'sentence': t['sentence'], 'tag': t['tag']} for t in tweaks]
    save_doc(store, run, 'direction.json', doc)
    return {'voice_id': voice_id, 'tweaks': len(tweaks)}


def direction_for(store, run, voice_id):
    """What a narration of this run in this voice is directed with: the base list and that voice's tweaks; None when no direction is recorded."""
    doc = direction_of(store, run)
    if not doc or doc.get('chosen') == 'none':
        return None
    return {'register': doc.get('register') or '', 'items': doc.get('base') or [], 'tweaks': (doc.get('tweaks') or {}).get(voice_id) or [], 'digest': doc.get('digest')}


def narrate(conn, store, user, run, outputs, voice_id, request_id, by='page', tweaks=None):
    """A full narration in one voice with the run's direction; every narration is kept on the page state."""
    if tweaks is not None:
        set_tweaks(store, run, outputs, voice_id, tweaks)
    script, _ = script_text(store, outputs)
    row = jobs.submit_voice(conn, user, run, outputs, {'kind': 'narration', 'voice_id': voice_id, 'text': script['spoken_text']}, request_id, store=store)
    state = page_state(store, run)
    add_narration(state, {'job_id': str(row['id']), 'voice_id': row['request']['voice_id'], 'name': row['request'].get('name'), 'model_id': row['request'].get('model_id'),
                          'settings': row['request'].get('settings'), 'direction_digest': row['request'].get('direction_digest'), 'tweaks': row['request'].get('tweaks') or [],
                          'by': user['name'], 'at': datetime.now(timezone.utc).isoformat(), 'from': by})
    save_doc(store, run, 'page.json', state)
    return row


def tryout(conn, store, user, run, outputs, voice_ids, request_id):
    """design/54 step 2: up to six voices read the chosen test passage with the direction's register and tags; a library voice is saved to the account by the submission."""
    check_cap(voice_ids, TRYOUT_MAX, 'tryout')
    doc = direction_of(store, run)
    if not doc or not doc.get('passage'):
        raise Problem(409, 'NOT_ALLOWED', 'Ask the assistant for the direction and the test passage first (vw voice direct); the tryout reads that passage.')
    script, _ = script_text(store, outputs)
    pp = doc['passage']
    state = page_state(store, run)
    rows = []
    for i, vid in enumerate(voice_ids):
        tweaks = (doc.get('tweaks') or {}).get(vid) or []
        text = VD.directed_passage(script['spoken_text'], doc.get('base') or [], doc.get('register') or '', pp['first_word'], pp['last_word'], tweaks) if doc.get('chosen') != 'none' else pp['text']
        row = jobs.submit_voice(conn, user, run, outputs, {'kind': 'audition', 'voice_id': vid, 'text': text, 'directed': doc.get('chosen') != 'none', 'passage': pp['n']}, sub_request_id(request_id, i), store=store)
        rows.append(row)
        state['tried'] = [t for t in state['tried'] if t['voice_id'] != row['request']['voice_id']] + \
            [{'voice_id': row['request']['voice_id'], 'asked_as': vid, 'name': row['request'].get('name'), 'job_id': str(row['id']), 'at': datetime.now(timezone.utc).isoformat()}]
    state['step'] = 'try'
    save_doc(store, run, 'page.json', state)
    return rows


def narrate_many(conn, store, user, run, outputs, voice_ids, request_id, by='page'):
    """design/54 step 3: up to three voices read the whole script with the direction; every narration is kept."""
    check_cap(voice_ids, NARRATE_MAX, 'narration')
    rows = [narrate(conn, store, user, run, outputs, vid, sub_request_id(request_id, i), by) for i, vid in enumerate(voice_ids)]
    state = page_state(store, run)
    state['step'] = 'narrations'
    save_doc(store, run, 'page.json', state)
    return rows


def finalise(conn, store, user, run, outputs, job_id, quote, recorded_from='page'):
    """The record: a kept narration becomes the voice stage output; the click is the operator's choice (design/98 W1), their words kept when given."""
    from . import core
    quote = str(quote or '').strip() or f"Made final on the voices page by {user.get('name') or user.get('id')}"
    job = conn.execute('select * from vw2_jobs where id=%s and run_id=%s', (job_id, run['id'])).fetchone()
    if not job or job['request'].get('kind') != 'narration':
        raise Problem(404, 'NOT_FOUND', 'No such narration on this run.')
    if job['status'] != 'ready':
        raise Problem(409, 'NOT_READY', f"This narration is {job['status']}.")
    script, script_o = script_text(store, outputs)
    timing = json.loads(store.get(job['result']['timing_key']).decode('utf-8'))
    direction = direction_of(store, run) or {}
    body = final_body(dict(job), script_o['summary']['content_digest'], beat_rows(script, timing), quote.strip(),
                      {'chosen': direction.get('chosen') or 'none', 'digest': direction.get('digest')}, recorded_from)
    out = core.output(conn, user, run, body)
    state = page_state(store, run)
    state['final'] = {'job_id': str(job['id']), 'voice_id': job['request']['voice_id'], 'name': job['request'].get('name'), 'by': user['name'], 'at': datetime.now(timezone.utc).isoformat()}
    save_doc(store, run, 'page.json', state)
    return out


def page_summary(store, run):
    state = page_state(store, run)
    direction = direction_of(store, run)
    return {'pick': state.get('pick'), 'narrations': len(state['narrations']), 'final': bool(state.get('final')), 'direction': (direction or {}).get('chosen') or None,
            'passage': ((direction or {}).get('passage') or {}).get('n'), 'step': state.get('step') or 'browse', 'tried': len(state.get('tried') or [])}
