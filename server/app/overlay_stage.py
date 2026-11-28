"""Text overlays, the step (requirements version 3 of 28 Nov 2026, parts A and B). It sits at the end of visuals, before the editor's package.
The record of the step, the one start card (kinds and look, defaults ticked), the client's look kept for their next film, and the gate the package
waits behind. The operator decides; the application refuses only what it cannot make."""
from datetime import datetime, timezone
from fractions import Fraction

from . import film as F
from . import overlays as O
from .errors import Problem
from .stage2 import stage as S2

KINDS = {'callout': 'a short phrase the viewer should take away', 'number': 'a figure with its unit and a short label', 'list': 'three or more items, each appearing as it is said',
         'title': 'the name of a section as it begins', 'name': 'a person\'s name and role'}
CARD_WORDS = {'dark': 'a dark see-through card, white text (the default)', 'cream': 'a solid cream card, dark text', 'bare': 'no card: the text alone, with a soft shadow',
              'bar': 'no card: the text with a bar in the film\'s accent colour beside it'}
MOTION_WORDS = {'wipe': 'the card opens from one side and the lines follow (the default)', 'fade': 'it fades in', 'rise': 'it rises a little as it fades in',
                'slide': 'it slides in from the side it sits on', 'cut': 'it is simply there, no movement'}
ANSWERS = (('defaults', 'Accept the defaults'), ('change', 'Change'), ('none', 'No overlays in this film'))


def key(run, name):
    return f"{run['id']}/visuals/overlays/{name}"


def session_of(store, run):
    k = key(run, 'session.json')
    try:
        return S2.load_json(store, k)
    except Problem:
        if store.exists(k):
            raise   # a failed read is not a missing record: starting a new one would drop the operator's answers
    return {'contract': 'vw2-overlays-session-v1', 'start': None, 'proposed': False, 'rows': []}


def save_session(store, run, session):
    session['updated_at'] = datetime.now(timezone.utc).isoformat()
    S2.save_json(store, key(run, 'session.json'), session)
    return session


def _kept_key(client_id):
    return f'clients/{client_id}/overlay-look.json'


def kept_look(store, client_id):
    """The look this client chose on their last film with overlays: {'run', 'kinds', 'look'}; None when there is none."""
    if not client_id or not store.exists(_kept_key(client_id)):
        return None
    return S2.load_json(store, _kept_key(client_id))


def _usable(kept, film):
    """The kept kinds and look as this film can use them: a font the film's scripts do not fit gives way to the film's own."""
    look = dict((kept or {}).get('look') or {})
    if look.get('font') and not F._holds(look['font'], film.get('scripts') or ['latin']):
        look.pop('font')
    return list((kept or {}).get('kinds') or O.KINDS), look


def start_card(film, kept=None):
    """The one card at the start of the step. Everything on it is a suggestion; the operator's word replaces any of it."""
    kinds, look = _usable(kept, film)
    return {'kinds': [{'id': k, 'what': KINDS[k]} for k in O.KINDS],
            'cards': [{'id': c, 'what': CARD_WORDS[c], 'sample': f'overlay-samples/{c}.jpg'} for c in O.CARDS],
            'own_card': 'Or your own: send a reference picture of a card from an earlier film; it is matched as far as the settings go (ground colour, see-through, text colour, corner, border).',
            'motions': [{'id': m, 'what': MOTION_WORDS[m]} for m in O.MOTIONS],
            'fonts': [n for n in F.font_set() if F._holds(n, film.get('scripts') or ['latin'])],
            'font_note': 'Only the fonts of the application can be used; a font from outside it cannot. The film\'s own font is the default.',
            'sizes': list(O.SIZES), 'weights': list(O.WEIGHTS),
            'defaults': {'kinds': kinds, 'look': {**{k: O.LOOK[k] for k in O.LOOK_KEYS}, 'font': film.get('font'), **look}},
            'kept_from': (kept or {}).get('run'),
            'answers': [{'id': a, 'label': label} for a, label in ANSWERS]}


def answer(store, run, session, body, film):
    """The operator's answer to the start card, recorded. Returns the faults ([] when recorded): only what cannot be made."""
    said = body.get('answer')
    if said not in dict(ANSWERS):
        return [f"the answer {said!r} is not one of: {', '.join(dict(ANSWERS))}"]
    kinds, look = [], {}
    if said == 'defaults':
        kinds, look = _usable(kept_look(store, run.get('client_id')), film)
    elif said == 'change':
        look = body.get('look') if body.get('look') is not None else {}
        problems = O.check({'look': look, 'overlays': []}, film)['problems']
        if problems:
            return problems[:1]
        kinds = body.get('kinds') if body.get('kinds') is not None else list(O.KINDS)
        if not isinstance(kinds, list) or not kinds:
            return ['no kind of overlay is chosen. Choose one or more kinds, or answer "No overlays in this film"']
        bad = [k for k in kinds if k not in O.KINDS]
        if bad:
            return [f"the kind {bad[0]!r} is not one the application has. The kinds are: {', '.join(O.KINDS)}"]
    before = session.get('start')
    if before and before['answer'] != 'none' and said != 'none' and O.look_of(before['look'], film) != O.look_of(look, film):
        for row in session.get('rows') or []:   # a changed look changes every picture: each overlay is asked again
            if row['state'] != 'removed':
                row.update(state='proposed', clip=None)
    session['start'] = {'answer': said, 'kinds': kinds, 'look': look, 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    if said != 'none' and run.get('client_id'):
        S2.save_json(store, _kept_key(run['client_id']), {'run': run['code'], 'kinds': kinds, 'look': look})
    return []


def open_points(session):
    """What the editor's package still waits for; [] when the step is settled."""
    start = session.get('start')
    if not start:
        return ['the start card of the overlays is not answered (`vw overlays start`)']
    if start['answer'] == 'none':
        return []
    if not session.get('proposed'):
        return ['no overlay list is proposed yet (`vw overlays propose`)']
    return [f"{r['id']} is not approved or removed" if r['state'] == 'proposed' else f"{r['id']} has no clip yet"
            for r in session.get('rows') or [] if r['state'] == 'proposed' or (r['state'] == 'approved' and not r.get('clip'))]


def gate(session):
    points = open_points(session)
    if points:
        raise Problem(409, 'NOT_ALLOWED', f"The editor's package waits for the text overlays: {'; '.join(points)}.")


# ---------- the list (parts C and D): proposed by the assistant, decided by the operator ----------

def film_of(events, words, fps, frames, font, scripts):
    """The film as overlays.check reads it, from the package's events and the narration's words: one cut per shot (the states of one shot are one cut)."""
    cuts = []
    for i, e in enumerate(events, 1):
        name = (e.get('marker') or {}).get('name') or f'cut {i}'
        if cuts and cuts[-1]['name'] == name and cuts[-1]['end_frame'] == e['record_in_frame']:
            cuts[-1]['end_frame'] = e['record_out_frame']
        else:
            cuts.append({'name': name, 'start_frame': e['record_in_frame'], 'end_frame': e['record_out_frame']})
    return {'fps': fps, 'frames': frames, 'cuts': cuts, 'words': [{'start_frame': w['start_frame'], 'text': w.get('text')} for w in words], 'font': font, 'scripts': sorted(scripts or ['latin'])}


def _fresh_row(rid, given, row):
    return {'id': rid, 'state': 'proposed', 'given': given, 'row': row, 'still': None, 'clip': None}


def propose(store, run, session, doc, film):
    """The assistant's list, recorded when the application can make all of it. An overlay written exactly as before keeps its number, its approval and
    its clip; the others are new and wait for the operator. Returns {'problems', 'to_draw'}."""
    start = session.get('start')
    if not start:
        return {'problems': ['the start card of the overlays is not answered yet: show it and record the answer first (`vw overlays start`)'], 'to_draw': []}
    if start['answer'] == 'none':
        return {'problems': ['the operator answered "No overlays in this film". To add overlays, ask them and record a new answer on the start card (`vw overlays start`)'], 'to_draw': []}
    if not isinstance(doc, dict) or 'look' in doc:
        return {'problems': ['the list holds "overlays" only: {"overlays": [ … ]}. The film\'s look is the start card\'s answer (`vw overlays start --answer change`)'], 'to_draw': []}
    out = O.check({'look': start['look'], 'overlays': doc.get('overlays')}, film)
    if out['problems']:
        return {'problems': out['problems'], 'to_draw': []}
    old = list(session.get('rows') or [])
    n = max([int(r['id'][1:]) for r in old] or [0])
    rows, new = [], []
    for given, row in zip(doc['overlays'], out['rows']):
        same = next((r for r in old if r['given'] == given and r['row'] == row), None)
        if same:
            old.remove(same)
            rows.append(same)
        else:
            n += 1
            rows.append(_fresh_row(f'O{n:02d}', given, row))
            new.append(rows[-1]['id'])
    session.update(rows=rows, proposed=True)
    save_session(store, run, session)
    return {'problems': [], 'to_draw': new}


def decide(store, run, session, rid, what, film, given=None):
    """The operator's word on one overlay: approve, remove, or change (the changed overlay, written whole). Returns {'problems', 'to_draw'}."""
    r = next((x for x in session.get('rows') or [] if x['id'] == rid), None)
    if not r:
        return {'problems': [f"{rid} is not an overlay of this film. They are: {', '.join(x['id'] for x in session.get('rows') or []) or 'none yet'}"], 'to_draw': []}
    if what not in ('approve', 'remove', 'change'):
        return {'problems': [f'the decision {what!r} is not one of: approve, remove, change'], 'to_draw': []}
    draw = []
    if what == 'change':
        if not isinstance(given, dict):
            return {'problems': [f'{rid}: write the changed overlay whole, as a row of the list'], 'to_draw': []}
        out = O.check({'look': session['start']['look'], 'overlays': [given]}, film)
        if out['problems']:
            return {'problems': [f"{rid}: {out['problems'][0].replace('row 1: ', '', 1)}"], 'to_draw': []}
        r.update(_fresh_row(rid, given, out['rows'][0]))
        draw = [rid]
    else:
        r['state'] = 'approved' if what == 'approve' else 'removed'
        if what == 'remove':
            r['clip'] = None
    save_session(store, run, session)
    return {'problems': [], 'to_draw': draw}


def approve_all(store, run, session):
    """"Approve all as shown": every overlay still waiting is approved. Returns their numbers."""
    ids = [r['id'] for r in session.get('rows') or [] if r['state'] == 'proposed']
    for r in session.get('rows') or []:
        if r['id'] in ids:
            r['state'] = 'approved'
    save_session(store, run, session)
    return ids


def listing(session, film):
    """The list as the operator reads it: one line of facts per overlay, no judgment."""
    fps = film['fps']
    out = []
    for r in session.get('rows') or []:
        row = r['row']
        cut = O._cut_at(film['cuts'], row['start_frame'])
        out.append({'id': r['id'], 'state': r['state'], 'kind': row['kind'], 'lines': row['lines'], 'shot': cut['name'] if cut else None,
                    'start_s': round(row['start_frame'] / fps, 2), 'end_s': round(row['end_frame'] / fps, 2), 'place': row['place'], 'motion': row['motion'],
                    'facts': row.get('facts') or [], 'why': row.get('why'), 'still': (r.get('still') or {}).get('key'), 'clip': bool(r.get('clip'))})
    return out


# ---------- the stills and the clips: requests for the worker, results into the record ----------

ACCENT = '#F0A46E'   # the application's own accent, when the film's colours name none


def accent_of(words):
    """The film's accent: the first colour the operator named in the film's colours (#rrggbb or a colour word), else the application's own."""
    import re
    from PIL import ImageColor
    for tok in re.findall(r'#[0-9A-Fa-f]{6}\b|[A-Za-z]+', str(words or '')):
        try:
            return '#%02X%02X%02X' % ImageColor.getrgb(tok)[:3]
        except ValueError:
            continue
    return ACCENT


def base_of(events, keys, frame):
    """The shot's own picture under an overlay's still: the file of the cut at `frame` and the second of it to take. `keys`: package name to storage key.
    None when no file of that cut is on the server (the still is then shown on a plain ground)."""
    e = next((e for e in events if e['record_in_frame'] <= frame < e['record_out_frame']), None)
    if not e or e.get('file') not in keys:
        return None
    picture = e.get('kind') == 'still'
    return {'key': keys[e['file']], 'picture': picture,
            'at_s': 0 if picture else round((e['source_in_frame'] + frame - e['record_in_frame']) / float(Fraction(str(e.get('source_fps') or 25))), 3)}


def _digest(row, page):
    return S2.digest({'row': row, 'page': page})


def requests(run, session, ids, what, page, events=(), keys=None):
    """One request per overlay for the worker: its still picture (on the shot's own frame) or its transparent clip."""
    from . import overlay_template as T
    out = []
    for r in session.get('rows') or []:
        if r['id'] not in ids:
            continue
        d = _digest(r['row'], page)
        q = {'kind': f'overlay-{what}', 'overlay': r['id'], 'row': r['row'], 'page': page, 'digest': d, 'out_key': key(run, f"{r['id']}-{d[:12]}.{'jpg' if what == 'still' else 'mov'}")}
        if what == 'still':
            q['base'] = base_of(events, keys or {}, r['row']['start_frame'] + int(round(T.still_at(r['row'], page['fps']) * page['fps'])))
        out.append(q)
    return out


def stills_due(session):
    return [r['id'] for r in session.get('rows') or [] if r['state'] == 'proposed' and not r.get('still')]


def clips_due(session):
    return [r['id'] for r in session.get('rows') or [] if r['state'] == 'approved' and not r.get('clip')]


def _jobs_of(r, page, jobs, kind):
    d = _digest(r['row'], page)
    return [j for j in jobs if (j.get('request') or {}).get('overlay') == r['id'] and j['request'].get('kind') == kind and j['request'].get('digest') == d]


def collect(session, page, jobs):
    """The worker's results taken into the record: a result counts only for the overlay as it is written now. True when anything changed."""
    changed = False
    for r in session.get('rows') or []:
        for field, kind in (('still', 'overlay-still'), ('clip', 'overlay-clip')):
            mine = _jobs_of(r, page, jobs, kind)
            ready = next((j for j in reversed(mine) if j['status'] == 'ready'), None)
            failed = next((j for j in reversed(mine) if j['status'] == 'failed'), None)
            if ready and not r.get(field):
                r[field] = {k: v for k, v in ready['result'].items() if k in ('key', 'bytes', 'sha256', 'frames') and (field == 'clip' or k == 'key')}
                r.pop('failed', None)
                changed = True
            elif failed and not ready and not r.get(field) and r.get('failed') != failed.get('error'):
                r['failed'] = failed.get('error')
                changed = True
    return changed


def waiting(session, page, jobs):
    """The overlays the worker is still busy with."""
    return [r['id'] for r in session.get('rows') or []
            if any(j['status'] in ('queued', 'running', 'storage_pending') for kind in ('overlay-still', 'overlay-clip') for j in _jobs_of(r, page, jobs, kind))]


# ---------- the film and the worker, read from the run (the part that needs the run's outputs and the database) ----------

def context(store, run, outputs):
    """(film, page, events, keys) of a run whose visuals are all recorded: what the list is checked against and what the worker draws on."""
    from .stage3 import delivery as D, early as E
    master_o, media_o = S2._output(outputs, 'master'), S2._output(outputs, 'media')
    plan, _ = S2._file(store, master_o, f"master-v{master_o['summary']['version']}.json")
    missing = E.gaps_missing(plan, outputs)
    if missing:
        raise Problem(409, 'NOT_ALLOWED', f"The text overlays come after the visuals: {', '.join(missing)} {'has' if len(missing) == 1 else 'have'} no recorded visuals yet (`vw visuals record --gap G`).")
    s2 = S2.session_of(store, run)
    pk = S2._package(store, s2)
    clips = D.all_clips(media_o, s2.get('package'))
    events, ai_files = E.events_of(plan, pk, outputs, clips)
    keys = {D.layout('ai', f['name']): f['key'] for f in ai_files}
    keys.update({D.layout('original', c['name']): S2.clip_key(run, c) for c in clips.values()})
    tl = pk['timeline']
    film = film_of(events, (pk.get('narration') or {}).get('words') or [], tl['fps'], plan['duration_frames'], F.font(run), F.font_scripts(run))
    return film, {'fps': tl['fps'], 'width': tl['width'], 'height': tl['height'], 'accent': accent_of(F.colours(run)), 'scripts': film['scripts']}, events, keys


def jobs_of(conn, run):
    return conn.execute("select id, status, request, result, error from vw2_jobs where run_id=%s and provider='motion' and request->>'kind' like 'overlay-%%' order by created_at",
                        (run['id'],)).fetchall()


def queue(conn, store, run, reqs, jobs):
    """The requests handed to the worker, one job each; a request already queued, running or made for the overlay as it is written now is not asked twice."""
    from psycopg.types.json import Jsonb
    asked = []
    for q in reqs:
        if any(j['request'].get('overlay') == q['overlay'] and j['request'].get('kind') == q['kind'] and j['request'].get('digest') == q['digest'] and j['status'] != 'failed' for j in jobs):
            continue
        k = key(run, f"requests/{q['overlay']}-{q['kind']}-{q['digest'][:12]}.json")
        S2.save_json(store, k, q)
        conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,'motion',%s, gen_random_uuid())",
                     (run['id'], q['overlay'], Jsonb({'kind': q['kind'], 'request_key': k, 'overlay': q['overlay'], 'digest': q['digest']})))
        asked.append(q['overlay'])
    return asked


def report(conn, store, run, session, film, page):
    """The step as the operator's side reads it: the list, what the worker is busy with, what the package still waits for. The worker's results are taken in first."""
    jobs = jobs_of(conn, run)
    if collect(session, page, jobs):
        save_session(store, run, session)
    return {'start': session.get('start'), 'overlays': listing(session, film), 'failed': {r['id']: r['failed'] for r in session.get('rows') or [] if r.get('failed')},
            'busy': waiting(session, page, jobs), 'open': open_points(session)}


def after(conn, store, run, session, film, page, events, keys, draw=()):
    """After a proposal or a decision: the stills of the overlays to draw are asked; once no overlay waits for the operator, the clips of the approved ones, in one go."""
    jobs = jobs_of(conn, run)
    queue(conn, store, run, requests(run, session, list(draw), 'still', page, events, keys), jobs)
    if session.get('proposed') and not any(r['state'] == 'proposed' for r in session.get('rows') or []):
        queue(conn, store, run, requests(run, session, clips_due(session), 'clip', page), jobs)
    return report(conn, store, run, session, film, page)


# ---------- the editor's package (part G) ----------

def package_rows(session):
    """The approved overlays with their clips, as the package carries them: the file under Media/Overlays/, the film frames, and a track each:
    an overlay that begins while another still shows goes on the next track."""
    rows, ends = [], []
    for r in sorted((r for r in session.get('rows') or [] if r['state'] == 'approved' and r.get('clip')), key=lambda r: (r['row']['start_frame'], r['id'])):
        row, clip = r['row'], r['clip']
        track = next((i for i, end in enumerate(ends) if end <= row['start_frame']), len(ends))
        ends[track:track + 1] = [row['end_frame']]
        card = next((name for name, c in O.CARDS.items() if c == row['card']), 'own')
        place = row['place'] if isinstance(row['place'], str) else f"x {row['place']['x']:g} %, y {row['place']['y']:g} %"
        rows.append({'id': r['id'], 'file': f"Media/Overlays/{r['id']}.mov", 'key': clip['key'], 'sha256': clip.get('sha256'), 'bytes': clip.get('bytes'), 'frames': row['end_frame'] - row['start_frame'],
                     'record_in_frame': row['start_frame'], 'record_out_frame': row['end_frame'], 'track': track + 1, 'kind': row['kind'],
                     'text': (f"{row['heading']}: " if row.get('heading') else '') + ' / '.join(row['lines']), 'card': card, 'motion': row['motion'], 'place': place})
    return rows


def overlays_csv(rows, fps):
    import csv
    import io
    from .stage3.early import tc
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    w.writerow(['overlay', 'file', 'kind', 'text', 'in_tc', 'out_tc', 'in_s', 'out_s', 'track', 'card', 'motion', 'place'])
    for r in rows:
        w.writerow([r['id'], r['file'], r['kind'], r['text'], tc(r['record_in_frame'], fps), tc(r['record_out_frame'], fps), f"{r['record_in_frame'] / float(fps):g}",
                    f"{r['record_out_frame'] / float(fps):g}", f"Overlays {r['track']}", r['card'], r['motion'], r['place']])
    return out.getvalue()
