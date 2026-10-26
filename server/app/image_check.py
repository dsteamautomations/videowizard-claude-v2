"""design/86 K2: the check before the operator sees a picture.

A retained candidate is read against its own answer form's checklist by Gemini Flash (the analysis stage's transport), one pass or fail with a
sentence per line, plus three fixed questions: readable text, a face that matches a footage frame, anything in the frame the prompt did not ask for.
The code checks size, aspect and parent. A failed must line marks the picture; a fix round (an edit of the candidate with the one change the
failed line asks for) is made only on request (design/96 X1: `visuals_stage.request_fix`). The check never blocks: a transport error leaves the candidate a candidate with the error on it. The operator may approve a picture
the check failed."""
import base64
import json
import uuid
from io import BytesIO

from PIL import Image, ImageStat

from .config import settings

CHECK_MODEL = 'gemini-3.8-flash'
FIXED = [{'check': 'readable text', 'pass_when': 'no readable text anywhere in the frame unless the prompt asked for exact text', 'weight': 'must'},
         {'check': 'a real face', 'pass_when': 'no face that matches a person in the footage frames sent as references', 'weight': 'must'},
         {'check': 'nothing extra', 'pass_when': 'nothing in the frame that the prompt did not ask for (a second person, a vehicle, a sign, a logo)', 'weight': 'should'}]
SCENE_FIXED = [   # design/91 N7: for scene pictures, not graphics; should lines, so they never start a fix round alone
    {'check': 'plausible setting', 'pass_when': 'the setting and its scale are plausible for what is shown: the location, the size of the spaces against a person, the ground', 'weight': 'should'},
    {'check': 'practitioner', 'pass_when': 'people handle tools and materials as a practitioner would (nothing set down on fresh work, the right tool for the task)', 'weight': 'should'}]
SCHEMA = {'type': 'object', 'properties': {'lines': {'type': 'array', 'items': {'type': 'object', 'properties': {'n': {'type': 'integer'}, 'pass': {'type': 'boolean'}, 'seen': {'type': 'string'}},
                                                                                'required': ['n', 'pass', 'seen']}}},
          'required': ['lines']}


TAKE_LINES = [   # design/91 N3: the fixed questions every take is read against
    {'check': 'appear or vanish', 'pass_when': 'nothing appears or vanishes without a visible cause (a hand placing it, a person carrying it in or out)', 'weight': 'must'},
    {'check': 'same tools, clothes, faces', 'pass_when': 'every tool, piece of clothing and face stays the same from the first frame to the last', 'weight': 'must'},
    {'check': 'no repeat without its precondition', 'pass_when': 'no action is repeated without what it needs (pouring again from a pan already emptied)', 'weight': 'must'},
    {'check': 'no change of shape or size', 'pass_when': 'no object changes shape or size (a window, a wall, a tool)', 'weight': 'must'},
    {'check': 'planned end', 'pass_when': 'the clip ends in the state the plan below describes', 'weight': 'must'}]
AMBIENT_LINE = {'check': 'surroundings move', 'pass_when': "what the plan's ambient line names moves visibly through the shot; nothing that should move is frozen", 'weight': 'must'}   # design/101 M4
TAKE_SCHEMA = {'type': 'object', 'properties': {'lines': {'type': 'array', 'items': {'type': 'object', 'properties': {'n': {'type': 'integer'}, 'pass': {'type': 'boolean'}, 'seen': {'type': 'string'},
                                                                                     'at_s': {'type': 'number'}}, 'required': ['n', 'pass', 'seen']}}}, 'required': ['lines']}


def run_take_check(snapshot, video_path, sha256, transport_factory):
    """design/91 N3: a ready take read by Gemini Flash against the fixed questions, the plan beside them; the lines with the second each is decided. Never raises."""
    record = {'lines': [], 'must_failed': [], 'model': CHECK_MODEL}
    try:
        key = settings().GEMINI_API_KEY.get_secret_value().strip()
        if not key:
            record['error'] = 'no Gemini key on the server'
            return record
        transport = transport_factory(key, CHECK_MODEL, terminal_deadline_seconds=300, initial_soft_wait_seconds=60, on_update=lambda e: None, capture_answer_deltas=False)
        uploaded = transport.upload(video_path, 'video/mp4', sha256)
        plan = '\n'.join(['The motion asked for: ' + str(snapshot.get('motion_prompt') or '')[:2000]] +
                         [f"Planned change, {c['at_s'][0]}–{c['at_s'][1]} s: {c['what']}" for c in snapshot.get('changes') or []] +
                         (['What stays unchanged: ' + str(snapshot['continuity_notes'])[:1000]] if snapshot.get('continuity_notes') else []) +
                         (['What must move around the action (the ambient line): ' + str(snapshot['ambient'])[:1000]] if snapshot.get('ambient') else []))
        take_lines = TAKE_LINES + ([AMBIENT_LINE] if snapshot.get('ambient') else [])   # design/101 M4
        asks = '\n'.join(f"{n}. {c['check']}: passes when {c['pass_when']}" for n, c in enumerate(take_lines, 1))
        received = transport.generate({'contents': [{'role': 'user', 'parts': [{'fileData': {'fileUri': uploaded['uri'], 'mimeType': uploaded['mimeType']}}, {'text':
            'You check a generated video clip, looking only at what is visible. The plan it was made from:\n' + plan +
            '\n\nFor each numbered line answer pass true or false, say in one sentence what you see that decides it, and give the second (at_s) where it happens. Be literal.\n' + asks}]}],
            'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': TAKE_SCHEMA, 'thinkingConfig': {'thinkingLevel': 'LOW'}, 'maxOutputTokens': 4096}})
        body = received.get('body')
        if not isinstance(body, dict):
            body = json.loads(received.get('raw') or '{}')
        got = read(body, take_lines)
        at = {int(l.get('n')): l.get('at_s') for l in body.get('lines') or [] if isinstance(l, dict) and l.get('n') is not None}
        lines = [{**l, 'at_s': at.get(n) if isinstance(at.get(n), (int, float)) else None} for n, l in enumerate(got['lines'], 1)]
        record.update(lines=lines, must_failed=[l for l in lines if l['weight'] == 'must' and l['pass'] is False])
    except Exception as exc:   # the check never blocks a take
        record['error'] = f'{exc.__class__.__name__}: {str(exc)[:200]}'
    return record


def lines_of(ref):
    """The server's must lines (design/89 C1, D5: the claims and the spec's relationships), the checklist the writer gave this picture, then the three fixed lines."""
    own = list(ref.get('server_checklist') or []) + [c for c in ((ref.get('answer') or {}).get('checklist') or []) if isinstance(c, dict) and c.get('check')]
    return own + FIXED + ([] if ref.get('element_kind') in ('graphic', 'style') else SCENE_FIXED)


def build(candidate_png, parents, lines, prompt):
    """The Gemini request: the parents first (named by their tag), the candidate last, then the questions."""
    parts = []
    for i, (tag, png) in enumerate(parents, 1):
        parts += [{'text': f'Reference {i} ({tag}).'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(png).decode()}}]
    parts += [{'text': 'The candidate picture.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(candidate_png).decode()}}]
    asks = '\n'.join(f"{n}. {c['check']}: passes when {c['pass_when']}" for n, c in enumerate(lines, 1))
    parts.append({'text': 'You check a generated picture against the list below, looking only at what is visible. The prompt it was made from, for context only:\n' + str(prompt or '')[:3000] +
                          '\n\nFor each numbered line answer pass true or false and say in one sentence what you see that decides it. Be literal; do not infer intent.\n' + asks})
    return {'contents': [{'role': 'user', 'parts': parts}],
            'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': SCHEMA, 'thinkingConfig': {'thinkingLevel': 'LOW'}, 'maxOutputTokens': 4096}}


def read(body, lines):
    """The model's answer against the lines: the lines with pass and seen, and the must lines that failed."""
    by_n = {int(l.get('n')): l for l in (body or {}).get('lines') or [] if isinstance(l, dict) and l.get('n') is not None}
    out = []
    for n, c in enumerate(lines, 1):
        a = by_n.get(n) or {}
        out.append({'check': c['check'], 'pass_when': c['pass_when'], 'weight': c.get('weight') or 'should', 'pass': bool(a.get('pass')) if a else None, 'seen': str(a.get('seen') or '')[:300]})
    return {'lines': out, 'must_failed': [l for l in out if l['weight'] == 'must' and l['pass'] is False], 'model': CHECK_MODEL}


def code_checks(ref, result, parents):
    """What code can check without a model: the size against the request, the parent chain."""
    out = []
    want = (ref.get('generation') or {}).get('size')
    got = f"{result.get('width')}x{result.get('height')}" if result.get('width') and result.get('height') else None
    out.append({'check': 'size', 'pass_when': f'the picture is {want}', 'weight': 'must', 'pass': (got == want) if want and got else None, 'seen': got or ''})
    if parents:
        out.append({'check': 'parent', 'pass_when': 'made from its approved parent', 'weight': 'must', 'pass': all(p.get('status') in ('approved', 'candidate') for p in parents), 'seen': ', '.join(p.get('id', '')[:8] for p in parents)})
    return out


LIGHT_JUMP = {'brightness': 0.15, 'saturation': 0.15, 'warmth': 0.08}   # design/91 N9; ponytail: fixed jumps on 0..1 means, tune them against real films


def _light(png):
    img = Image.open(BytesIO(png)).convert('RGB').resize((64, 36))
    r, _, b = ImageStat.Stat(img).mean
    return {'brightness': ImageStat.Stat(img.convert('L')).mean[0] / 255, 'saturation': ImageStat.Stat(img.convert('HSV')).mean[1] / 255, 'warmth': (r - b) / 255}


def light_line(store, session, ref, png):
    """design/91 N9: a picture in the film against the approved footage frames beside its gap (else all of the film's): brightness, saturation and warmth.
    None for a graphic, a sheet, or a film without footage frames. Code, not a model: free, and a should line, so it never starts a fix round."""
    if ref.get('element_kind') in ('graphic', 'style') or ref.get('kind') not in ('keyframe', 'isolated'):
        return None
    frames = [r for r in session.get('references', {}).values() if r.get('kind') == 'frame' and r.get('status') == 'approved' and r.get('key')]
    beside = {c for c in ((session.get('gap_neighbours') or {}).get(ref.get('gap_id')) or {}).values() if c}
    frames = [r for r in frames if (r.get('source') or {}).get('media_id') in beside] or frames
    stats = []
    for r in frames[:6]:
        try:
            stats.append(_light(store.get(r['key'])))
        except Exception:
            continue
    if not stats:
        return None
    footage = {k: sum(s[k] for s in stats) / len(stats) for k in LIGHT_JUMP}
    mine = _light(png)
    words = {'brightness': ('brighter', 'darker'), 'saturation': ('more saturated', 'less saturated'), 'warmth': ('warmer', 'cooler')}
    jumps = [f"{words[k][0] if mine[k] > footage[k] else words[k][1]} by {abs(mine[k] - footage[k]):.2f}" for k in LIGHT_JUMP if abs(mine[k] - footage[k]) >= LIGHT_JUMP[k]]
    seen = (', '.join(jumps) + ' than' if jumps else 'close to') + f" the footage beside it ({len(stats)} frame{'s' if len(stats) > 1 else ''})"
    return {'check': 'light and colour', 'pass_when': 'the light, colour and saturation match the footage beside it', 'weight': 'should', 'pass': not jumps, 'seen': seen}


def run_check(store, session, ref, result, transport_factory):
    """The whole check for one retained candidate, Gemini's lines and then the measured light (design/91 N9); returns the check record. Never raises."""
    record = _model_check(store, session, ref, result, transport_factory)
    try:
        light = light_line(store, session, ref, store.get(result['key']))
    except Exception:
        light = None
    if light:
        record['lines'] = list(record.get('lines') or []) + [light]
    return compact(record, ref)


def compact(record, ref):
    """design/92: a check line, and a failed must line, is stored without the pass condition its picture's checklist already holds (the session
    kept small: on VW-7 about 90 of 654 KB); a line no checklist holds (the light) keeps its own. expand() puts them back for the page and the fix round."""
    known = {c['check']: c.get('pass_when') for c in lines_of(ref)}
    short = lambda rows: [{k: v for k, v in l.items() if not (k == 'pass_when' and known.get(l.get('check')) == v)} for l in rows or []]
    return {**record, 'lines': short(record.get('lines')), 'must_failed': short(record.get('must_failed'))}


def expand(record, ref):
    """The stored check with each line's pass condition back, for the page."""
    known = {c['check']: c.get('pass_when') for c in lines_of(ref)}
    full = lambda rows: [{**l, 'pass_when': l.get('pass_when') or known.get(l.get('check')) or ''} for l in rows or []]
    return {**record, 'lines': full(record.get('lines')), 'must_failed': full(record.get('must_failed'))}


def _model_check(store, session, ref, result, transport_factory):
    """Gemini's part of the check: the lines and the code checks. Never raises."""
    parents = [session['references'].get(p.get('id')) or {} for p in (ref.get('generation') or {}).get('parents') or []]
    lines = lines_of(ref)
    record = {'code': code_checks(ref, result, parents), 'lines': [], 'must_failed': [], 'model': CHECK_MODEL}
    try:
        key = settings().GEMINI_API_KEY.get_secret_value().strip()
        if not key:
            record['error'] = 'no Gemini key on the server'
            return record
        pngs = [(('scene' if p.get('kind') == 'frame' else p.get('kind') or 'reference'), store.get(p['key'])) for p in parents if p.get('key')]
        transport = transport_factory(key, CHECK_MODEL, terminal_deadline_seconds=180, initial_soft_wait_seconds=30, on_update=lambda e: None, capture_answer_deltas=False)
        received = transport.generate(build(store.get(result['key']), pngs, lines, (ref.get('generation') or {}).get('prompt')))
        body = received.get('body')
        if not isinstance(body, dict):
            body = json.loads(received.get('raw') or '{}')
        got = read(body, lines)
        record.update(lines=got['lines'], must_failed=got['must_failed'] + [c for c in record['code'] if c['pass'] is False])
    except Exception as exc:   # the check never blocks a picture
        record['error'] = f'{exc.__class__.__name__}: {str(exc)[:200]}'
    return record


def fix_body(ref, failed):
    """design/86 K2: one fix round, one change, from the failed line's pass condition, in the library's fix-round form."""
    prompt = ('Mode: edit. Image 1 is the picture to fix; images 2 onward are its references: take identity from them, nothing else.\n'
              f"Change only: {failed['pass_when'].rstrip('.')}.\n"
              'Keep exactly as in Image 1: everything else, the framing, the light, every other subject and object where it is.\n'
              'Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.')
    return {'request_id': str(uuid.uuid4()), 'element_id': ref['element_id'], 'name': ref['name'] + '-fix', 'kind': ref['kind'], 'subject': ref.get('subject') or '',
            'prompt': prompt, 'parents': [ref['id']], 'fix_of': ref['id'], 'shot_id': ref.get('shot_id'),   # design/94 R1.1: listed under its original's shot
            'answer': {**(ref.get('answer') or {}), 'prompt': prompt, 'base_image_id': ref['id'], 'single_change': failed['pass_when']} if ref.get('answer') else None}
