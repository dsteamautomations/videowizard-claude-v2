"""Accurate images (design/194): a thing's drawing set on the server.

A helper sends one description of a thing (app/draw3d.py: facts, pieces in real units, views). It is checked, drawn into picture files (the
operator's labelled sheet and the image model's plain copy of every view) and kept with the film under session['drawings'][element_id].
The operator approves it by its exact content before any paid picture uses it; a changed description must be approved again.
Every step is a server function that the page and the chat tool both call. Nothing here costs money: no job is queued and no provider is called.
"""
import hashlib
import io
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

from . import draw3d, drawn
from . import visuals_stage as VS
from .errors import Problem
from .planning.digest import digest
from .visual_contract import need

SCALE = 2                                   # picture pixels per sheet unit
FONT = {'h': 16, 'e': 13, 't': 13, 'd': 12}  # the sheet's text sizes, in sheet units
MOST_SHEETS = 2                             # sheets of one thing sent to an image model in one request (design/194: Gemini takes six object pictures)
ANGLED = ('through the camera', 'three-quarter')


def now():
    return datetime.now(timezone.utc).isoformat()


def png(ops):
    """A sheet's drawing instructions as a PNG file."""
    w, h = (int(round(v * SCALE)) for v in ops['size'])
    px = lambda pts: [(x * SCALE, y * SCALE) for x, y in pts]
    layer = Image.new('RGB', (w, h), 'white')
    pen = ImageDraw.Draw(layer)
    for pts, fill in ops['polys']:
        pen.polygon(px(pts), fill=fill, outline=draw3d.INK)
    im = layer
    if ops['clip']:
        x, y, cw, ch = (int(round(v * SCALE)) for v in ops['clip'])
        im = Image.new('RGB', (w, h), 'white')
        im.paste(layer.crop((x, y, x + cw, y + ch)), (x, y))
    pen = ImageDraw.Draw(im)
    if ops['frame']:
        x, y, fw, fh = (v * SCALE for v in ops['frame'])
        pen.rectangle((x, y, x + fw, y + fh), outline='#111111', width=3)
    for pts, _ in ops['lines']:
        pen.line(px(pts), fill='#444444', width=1)
    for x, y in ops['dots']:
        pen.ellipse((x * SCALE - 4, y * SCALE - 4, x * SCALE + 4, y * SCALE + 4), fill='#555555')
    if ops['texts']:
        path = str(drawn.font_file())
        fonts = {cls: ImageFont.truetype(path, size * SCALE) for cls, size in FONT.items()}
        for cls, x, y, text, anchor in ops['texts']:
            f = fonts[cls]
            x0 = x * SCALE - (pen.textlength(text, font=f) / 2 if anchor == 'middle' else 0)
            pen.text((x0, y * SCALE), text, font=f, fill='#111111' if cls == 'h' else '#222222', anchor='ls')
    out = io.BytesIO()
    im.save(out, 'PNG')
    return out.getvalue()


def _element(store, session, element_id):
    plan = VS.guarded(lambda: VS.current_plan(store, session))
    el = next((e for e in (plan or {}).get('elements') or [] if e['id'] == element_id), None)
    need(el is not None, f'{element_id} is not an element of the plan.')
    need(el.get('kind') != 'person', f"{el.get('name') or element_id} is a person: a drawing places and poses a person in a shot, it is never a person's reference.")
    return el


def _fact_line(f, with_source=False):
    line = f"{f['what']}: {f.get('value', '')}{(' ' + str(f['unit'])) if f.get('unit') else ''}".strip().rstrip(':')
    return f"{line} ({f['source']})" if with_source and f.get('source') else line


def _drop_sheets(session, element_id):
    """The sheets of a thing's earlier drawing set stop being references: only the approved, current set is ever sent."""
    for rid in [rid for rid, r in session['references'].items() if r.get('kind') == 'drawing' and r.get('element_id') == element_id]:
        del session['references'][rid]


def set_drawing(conn, store, user, run, outputs, element_id, description):
    """A helper's drawing set of a thing: its shape is checked in plain words, every view is drawn and stored, and it waits for the operator."""
    session = VS.session_of(store, run, outputs)
    el = _element(store, session, element_id)
    wrong = draw3d.problems(description)
    need(not wrong, 'The drawing set cannot be drawn: ' + ' '.join(wrong[:6]) + (f' (and {len(wrong) - 6} more)' if len(wrong) > 6 else ''))
    need(description.get('level') != 'shot', "A thing's drawing set is at the engineered, composition or form level; \"shot\" is for a shot's own drawing.")
    sha = digest(description)
    rows = session.setdefault('drawings', {})
    old = rows.get(element_id) or {}
    if old.get('sha256') == sha:
        return {'element_id': element_id, 'sha256': sha, 'unchanged': True, 'status': old['status'], 'next': 'This drawing set is already stored; nothing was drawn again.'}
    k = VS.key(run, f'drawings/{sha}/set.json')
    VS.save_json(store, k, description)
    views = []
    for s in draw3d.render(description):
        row = {'id': s['view'], 'name': s['name'], 'kind': s['kind'], 'width': s['width'], 'height': s['height']}
        for which, ops in (('labelled', s['labelled_ops']), ('plain', s['plain_ops'])):
            data = png(ops)
            key = VS.key(run, f"drawings/{sha}/{s['view']}{'-plain' if which == 'plain' else ''}.png")
            store.put(key, data, 'image/png')
            row[f'{which}_key'], row[f'{which}_sha256'] = key, hashlib.sha256(data).hexdigest()
        views.append(row)
    facts = description.get('facts') or []
    _drop_sheets(session, element_id)
    rows[element_id] = {'sha256': sha, 'key': k, 'level': description['level'], 'name': description.get('name') or el.get('name') or element_id, 'unit': description['unit'],
                        'views': views, 'facts': [{k2: f[k2] for k2 in ('what', 'value', 'unit', 'source', 'assumed') if k2 in f} for f in facts],
                        'sourced': [_fact_line(f, True) for f in facts if not f.get('assumed')], 'assumed': [_fact_line(f) for f in facts if f.get('assumed')],
                        'status': 'proposed', 'by': user['id'], 'by_name': user.get('name') or '', 'at': now()}
    VS.save_session(store, run, session)
    slot = ((session.get('round') or {}).get('elements') or {}).get(element_id) or {}
    late = ('Its footage picture was already taken as its reference, so no set will be made with these drawings on this round: say so to the operator. ' if slot.get('from_footage') else
            'Its set was already made without these drawings: once they are approved, the operator answers that set No or Correct it on step 2 and it is made again with them. ' if slot.get('set') else '')
    return {'element_id': element_id, 'sha256': sha, 'status': 'proposed', **({'late': late.strip()} if late else {}), 'views': [{'id': v['id'], 'name': v['name'], 'kind': v['kind']} for v in views],
            'assumed': rows[element_id]['assumed'],
            'next': late + f"The drawings are made (free). The operator looks at them in the chat (`vw visuals next`) and approves or corrects them; "
                           f"or `vw drawing show --element {element_id}`, then `vw drawing approve --element {element_id} --sha {sha} --quote \"<the operator's words>\"`."}


def verdict(conn, store, user, run, outputs, element_id, sha256, approved, quote, notes=''):
    """The operator's verdict on a drawing set, by its exact content: approved with their words, or a correction in words."""
    session = VS.session_of(store, run, outputs)
    row = (session.get('drawings') or {}).get(element_id)
    need(row is not None, f'{element_id} has no drawing set yet: `vw drawing set --element {element_id} --file <its description>.json`.')
    need(row['sha256'] == sha256, 'The drawing set changed since it was looked at; look at the current drawings (`vw drawing show`).')
    need(str(quote or '').strip(), "A verdict carries the operator's own words.")
    notes = str(notes or '').strip()
    need(approved or notes, 'A correction says what is wrong, in the operator\'s words.')
    row['status'] = 'approved' if approved else 'rejected'
    _drop_sheets(session, element_id)
    if approved:   # each plain sheet becomes an approved reference of the film (kind 'drawing'), so it can be a parent of a picture request
        for v in row['views']:
            rid = f"drawing-{element_id}-{v['id']}-{row['sha256'][:8]}"
            session['references'][rid] = {'id': rid, 'kind': 'drawing', 'element_id': element_id, 'status': 'approved', 'key': v['plain_key'], 'sha256': v['plain_sha256'],
                                          'width': v['width'], 'height': v['height'], 'name': f"{row['name']}: {v['name']}", 'view': v['id'], 'view_kind': v['kind'],
                                          'drawing_sha256': row['sha256'], 'approval': {'by': user['id'], 'at': now(), 'quote': str(quote).strip()[:500]}}
    row['verdict'] = {'approved': bool(approved), 'quote': str(quote).strip()[:500], 'notes': notes[:2000], 'by': user['id'], 'by_name': user.get('name') or '', 'at': now()}
    VS.save_session(store, run, session)
    return {'element_id': element_id, 'status': row['status'],
            'next': 'The drawings are approved; they go with the requests for this thing\'s pictures.' if approved else
                    'The thing is drawn again with the correction (one thing at a time) and uploaded: `vw drawing set`.'}


def approved_sheets(session, element_id, most=MOST_SHEETS):
    """The plain sheets of a thing's approved drawing set that go to an image model: the angled view first, then the flat views in their order; `most` at most."""
    row = (session.get('drawings') or {}).get(element_id)
    if not row or row.get('status') != 'approved':
        return []
    views = sorted(row['views'], key=lambda v: v['kind'] not in ANGLED)      # a stable sort: angled views first, the rest as given
    return [{'id': f"drawing-{element_id}-{v['id']}-{row['sha256'][:8]}", 'view': v['id'], 'key': v['plain_key'], 'sha256': v['plain_sha256']} for v in views[:most]]


def words(store, session, element_id, first=1, most=MOST_SHEETS):
    """How to read the sheets that `approved_sheets` sends, as Image `first` onward: the paragraph for the prompt."""
    row = session['drawings'][element_id]
    return draw3d.how_to_read(VS.load_json(store, row['key']), [s['view'] for s in approved_sheets(session, element_id, most)], first)


def must_be_true(session, element_id):
    """The facts of a thing's approved drawing set, one plain line each: for the prompt's must-be-true list and for the check's lines."""
    row = (session.get('drawings') or {}).get(element_id)
    return [_fact_line(f) for f in row['facts']] if row and row.get('status') == 'approved' else []


def view(session, element_id):
    row = (session.get('drawings') or {}).get(element_id)
    need(row is not None, f'{element_id} has no drawing set yet.')
    return {'element_id': element_id, **{k: row.get(k) for k in ('sha256', 'status', 'level', 'name', 'sourced', 'assumed', 'verdict', 'at', 'by_name')},
            'views': [{'id': v['id'], 'name': v['name'], 'kind': v['kind']} for v in row['views']],
            'files': [v['id'] for v in row['views']] + [v['id'] + '-plain' for v in row['views']]}


def status(store, run, outputs, element_id):
    return view(VS.session_of(store, run, outputs), element_id)


def file(store, run, outputs, element_id, name):
    """One sheet as a picture file: '<view>' is the operator's labelled sheet, '<view>-plain' the image model's copy."""
    session = VS.session_of(store, run, outputs)
    row = (session.get('drawings') or {}).get(element_id)
    need(row is not None, f'{element_id} has no drawing set yet.')
    plain = name.endswith('-plain')
    v = next((v for v in row['views'] if v['id'] == (name[:-6] if plain else name)), None)
    if v is None:
        raise Problem(404, 'NOT_FOUND', f'{element_id} has no sheet called {name}.')
    import base64
    return {'name': name, 'file': f'{name}.png', 'mime': 'image/png', 'base64': base64.b64encode(store.get(v['plain_key' if plain else 'labelled_key'])).decode()}
