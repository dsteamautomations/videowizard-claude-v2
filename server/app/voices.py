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
PAGE_CONTRACT = 'vw2-voice-page-v1'
SHORTLIST_MAX = 6


# ---------- pure ----------

def compact(raw, register, usage, account_ids):
    """One catalog row the assistant and the page can read: identity, labels, a short description, the preview link and what we know."""
    labels = raw.get('labels') or {}
    desc = (raw.get('description') or '').strip()
    if len(desc) > DESCRIPTION_CHARS:
        desc = desc[:DESCRIPTION_CHARS].rstrip() + '…'
    reg = register.get(raw['voice_id']) or {}
    use = usage.get(raw['voice_id']) or {}
    sharing = raw.get('sharing') or {}
    owner = raw.get('public_owner_id') or sharing.get('public_owner_id')
    row = {'voice_id': raw['voice_id'], 'name': raw.get('name') or '', 'accent': labels.get('accent') or '', 'gender': labels.get('gender') or '', 'age': labels.get('age') or '',
           'use_case': labels.get('use_case') or '', 'descriptive': labels.get('descriptive') or '', 'description': desc, 'preview_url': raw.get('preview_url') or '',
           'scope': raw.get('scope') or '', 'category': raw.get('category') or '', 'on_account': raw['voice_id'] in account_ids,
           'favourite': bool(reg.get('favourite')), 'note': reg.get('note') or '', 'narrations': use.get('narrations') or 0, 'auditions': use.get('auditions') or 0,
           'last_used': use.get('last_used') or ''}
    if owner:
        row['library'] = {'public_owner_id': owner, 'original_voice_id': sharing.get('original_voice_id') or raw['voice_id']}
    return row


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
    return {'contract': PAGE_CONTRACT, 'shortlist': [], 'excerpt': None, 'pick': None, 'narrations': [], 'final': None}


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


def account(provider):
    d = provider.request('GET', '/v1/user/subscription').json()
    keys = ('tier', 'voice_limit', 'voice_slots_used', 'voice_add_edit_counter', 'max_voice_add_edits', 'character_count', 'character_limit', 'next_character_count_reset_unix')
    return {k: d.get(k) for k in keys}


def account_ids(provider):
    ids, cursor, seen = set(), '', set()
    while True:
        data = provider.request('GET', '/v2/voices', params={'page_size': 100, **({'next_page_token': cursor} if cursor else {})}).json()
        ids.update(v['voice_id'] for v in data.get('voices', []))
        cursor = data.get('next_page_token') if data.get('has_more') else None
        if not cursor or cursor in seen:
            return ids
        seen.add(cursor)


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


def catalog(conn, provider, q):
    """Compact rows with the register, the usage and the account mark; favourites first in the 'favourites' scope."""
    usage = history(conn)
    if q.get('scope') == 'favourites':
        reg = {k: v for k, v in register_rows(conn).items() if v.get('favourite')}
        acc = account_ids(provider)
        rows = []
        for vid, r in reg.items():
            try:
                raw = provider.voice(vid)
            except Problem:
                raw = {'voice_id': vid, 'name': r['name'], 'labels': {}, 'description': ''}
            row = compact({**raw, 'scope': 'favourites'}, reg, usage, acc)
            row['missing'] = vid not in acc
            rows.append(row)
        return {'voices': rows, 'has_more': False, 'next_page_token': None, 'scope': 'favourites'}
    found = elevenlabs.discover(provider, q)
    reg = register_rows(conn, [v['voice_id'] for v in found['voices']])
    acc = {v['voice_id'] for v in found['voices']} if q.get('scope') == 'account' else account_ids(provider)
    found['voices'] = sorted((compact(v, reg, usage, acc) for v in found['voices']), key=lambda r: not r['favourite'])
    return found


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
    doc = {'contract': 'vw2-voice-direction-v1', 'kind_of_film': body.get('kind_of_film') or '', 'options': body.get('options') or {}, 'registers': body.get('registers') or {},
           'chosen': chosen, 'register': register, 'base': items, 'digest': digest, 'approved_by': user['name'], 'at': datetime.now(timezone.utc).isoformat(),
           'quote': body.get('quote') or '', 'tweaks': (direction_of(store, run) or {}).get('tweaks') or {}}
    state = page_state(store, run)
    previous = direction_of(store, run)
    if previous and previous.get('digest') != digest and state['narrations']:
        mark_direction_change(state, digest)
        save_doc(store, run, 'page.json', state)
    save_doc(store, run, 'direction.json', doc)
    return {'chosen': chosen, 'digest': digest, 'items': len(items), 'register': register}


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


def direction_audition(conn, store, user, run, outputs, voice_id, passage_id, request_id):
    """One passage with its tags in one voice: a paid audition, no timing."""
    direction = direction_for(store, run, voice_id)
    if not direction:
        raise Problem(409, 'NOT_ALLOWED', 'No direction is recorded for this run; audition without tags with vw voice audition.')
    script, _ = script_text(store, outputs)
    rows = [r for r in VD.sentences_of(script['spoken_text']) if r['passage_id'] == passage_id]
    if not rows:
        raise Problem(422, 'DIRECTION', f'{passage_id} is not a passage of the accepted script.')
    start, end = rows[0]['start'], rows[-1]['end']
    tagged, _ = VD.apply(script['spoken_text'], direction['items'], direction['register'], direction['tweaks'])
    items = [i for i in direction['items'] if i['passage_id'] == passage_id]
    piece, _ = VD.apply(script['spoken_text'][start:end], [{**i, 'passage_id': 'P001'} for i in items], direction['register'],
                        [{**t, 'passage_id': 'P001'} for t in direction['tweaks'] if t['passage_id'] == passage_id])
    return jobs.submit_voice(conn, user, run, outputs, {'kind': 'audition', 'voice_id': voice_id, 'text': piece, 'directed': True}, request_id, store=store)


def audition_shortlist(conn, store, user, run, outputs, request_id):
    """The shortlist's auditions on the run's excerpt: a library voice is saved to the account first (no custom slot), then one paid job each."""
    state = page_state(store, run)
    if not state['shortlist']:
        raise Problem(409, 'NOT_ALLOWED', 'Shortlist one to six voices first.')
    script, _ = script_text(store, outputs)
    excerpt = state.get('excerpt') or excerpt_default(script['spoken_text'])
    provider = elevenlabs.ElevenLabs()
    on_account = account_ids(provider)
    rows = []
    for i, entry in enumerate(state['shortlist']):
        voice_id, lib = entry['voice_id'], entry.get('library')
        if voice_id not in on_account and lib:
            saved = elevenlabs.add_library_voice(provider, lib['public_owner_id'], lib['original_voice_id'])
            voice_id = saved['voice_id']
            entry['voice_id'] = voice_id
            remember(conn, saved, 'library')
        rows.append(jobs.submit_voice(conn, user, run, outputs, {'kind': 'audition', 'voice_id': voice_id, 'text': excerpt}, f'{request_id}-{i}', store=store))
        remember(conn, {'voice_id': voice_id, 'name': rows[-1]['request'].get('name'), 'library': lib}, 'library' if lib else 'custom')
    state['excerpt'] = excerpt
    save_doc(store, run, 'page.json', state)
    return rows


def excerpt_default(text):
    """The first passage of 45 to 70 words, or the first passage, for the shortlist's auditions."""
    best = None
    from .narration_pieces import paragraph_spans
    for s, e in paragraph_spans(text):
        n = len(text[s:e].split())
        if best is None:
            best = text[s:e]
        if 45 <= n <= 70:
            return text[s:e]
    return best or text[:300]


def finalise(conn, store, user, run, outputs, job_id, quote, recorded_from='page'):
    """The record: a kept narration becomes the voice stage output, with the operator's words."""
    from . import core
    if not (quote or '').strip():
        raise Problem(422, 'ACCEPTANCE_REQUIRED', "The operator's words are required to make a narration final.")
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
    return {'pick': state.get('pick'), 'narrations': len(state['narrations']), 'final': bool(state.get('final')), 'direction': (direction or {}).get('chosen') or None}
