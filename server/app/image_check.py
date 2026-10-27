"""design/86 K2: the check before the operator sees a picture.

A retained candidate is read against its own answer form's checklist by Gemini Flash (the analysis stage's transport), one pass or fail with a
sentence per line, plus three fixed questions: readable text, a face that matches a footage frame, anything in the frame the prompt did not ask for.
The code checks size, aspect and parent. A failed must line marks the picture; a fix round (an edit of the candidate with the one change the
failed line asks for) is made only on request (design/96 X1: `visuals_stage.request_fix`). The check never blocks: a transport error leaves the candidate a candidate with the error on it. The operator may approve a picture
the check failed."""
import base64
import subprocess
import json
import re
import uuid
from io import BytesIO

from PIL import Image, ImageFilter, ImageStat

from .config import settings

CHECK_MODEL = 'gemini-3.8-flash'
FIXED = [{'check': 'readable text', 'pass_when': 'no readable text anywhere in the frame unless the prompt asked for exact text', 'weight': 'must'},
         {'check': 'a real face', 'pass_when': 'no face that matches a person in the footage frames sent as references', 'weight': 'must'},
         {'check': 'nothing extra', 'pass_when': 'nothing in the frame that the prompt did not ask for (a second person, a vehicle, a sign, a logo)', 'weight': 'should'}]
SCENE_FIXED = [   # design/91 N7: for scene pictures, not graphics; should lines, so they never start a fix round alone
    {'check': 'plausible setting', 'pass_when': 'the setting and its scale are plausible for what is shown: the location, the size of the spaces against a person, the ground', 'weight': 'should'},
    {'check': 'practitioner', 'pass_when': 'people handle tools and materials as a practitioner would (nothing set down on fresh work, the right tool for the task)', 'weight': 'should'},
    {'check': 'wear', 'pass_when': 'materials show their real age and wear (uneven colour, chipped and worn edges, irregular joints, dust where work happens); '
                                   'clothes on people doing dirty work are soiled; skin shows texture', 'weight': 'should'}]   # design/104 C2
SCHEMA = {'type': 'object', 'properties': {'lines': {'type': 'array', 'items': {'type': 'object', 'properties': {'n': {'type': 'integer'}, 'pass': {'type': 'boolean'}, 'seen': {'type': 'string'}},
                                                                                'required': ['n', 'pass', 'seen']}}},
          'required': ['lines']}


TAKE_LINES = [   # design/91 N3: the fixed questions every take is read against
    {'check': 'appear or vanish', 'pass_when': 'nothing appears or vanishes without a visible cause (a hand placing it, a person carrying it in or out)', 'weight': 'must'},
    {'check': 'same tools, clothes, faces', 'pass_when': 'every tool, piece of clothing and face stays the same from the first frame to the last', 'weight': 'must'},
    {'check': 'no repeat without its precondition', 'pass_when': 'no action is repeated without what it needs (pouring again from a pan already emptied)', 'weight': 'must'},
    {'check': 'no change of shape or size', 'pass_when': 'no object changes shape or size (a window, a wall, a tool)', 'weight': 'must'},
    {'check': 'planned end', 'pass_when': 'the clip ends in the state the plan below describes', 'weight': 'must'},
    {'check': 'frozen person', 'pass_when': 'no person stands frozen while others move', 'weight': 'should'}]   # design/104 C4
LIGHT_KEPT = {'check': 'light kept', 'pass_when': "the light keeps the direction and brightness the plan's light line gives, from the first frame to the last", 'weight': 'must'}   # design/104 C5
TOOL_KEPT = {'check': 'tool kept', 'pass_when': 'every held tool keeps its identity (shape, size, colour, handle) from the first frame to the last and ends where the tool line says; it never changes into another thing or vanishes without a cause', 'weight': 'must'}   # design/110 F5
HEADING_KEPT = {'check': 'heading kept', 'pass_when': 'each travelling subject keeps the heading its line gives (front toward its landmark, the same side to the camera) and never flips or reverses, unless its change is a turn', 'weight': 'must'}   # design/110 F6
PERSON_KEPT = {'check': 'person kept', 'pass_when': 'each person keeps the build, age, skin, hair and the garment colours the person line gives, from the first frame to the last', 'weight': 'must'}   # design/111 F16
BACKGROUND_KEPT = {'check': 'background kept', 'pass_when': 'the three fixed things the background line names stay in the same place, size and light from the first frame to the last', 'weight': 'must'}   # design/111 F8
AMBIENT_LINE = {'check': 'surroundings move', 'pass_when': "what the plan's ambient line names moves visibly through the shot; nothing that should move is frozen", 'weight': 'must'}   # design/101 M4


CAMERA_STEADY = {'check': 'camera steady', 'pass_when': 'the framing does not move, drift, zoom or slide from the first frame to the last; only the subjects move', 'weight': 'must'}   # design/112 S4


def take_lines_for(snapshot):
    """The fixed take lines plus those the snapshot earns (design/101 M4, design/104 C5, design/110 F5, F6, design/111 F8, F16, design/112 S4)."""
    return (TAKE_LINES + ([AMBIENT_LINE] if ambient_moves(snapshot) else []) + ([LIGHT_KEPT] if snapshot.get('light') else [])
            + ([TOOL_KEPT] if snapshot.get('tool_lines') else []) + ([HEADING_KEPT] if snapshot.get('heading_lines') else []) + ([BACKGROUND_KEPT] if snapshot.get('fixed_line') else [])
            + ([PERSON_KEPT] if snapshot.get('person_lines') else []) + ([CAMERA_STEADY] if 'camera_move' in snapshot and not (snapshot.get('camera_move') or '').strip() else []))


ALIGN_SHIFT, ALIGN_SCALE, ALIGN_W, ALIGN_H = 0.01, 0.01, 256, 144   # design/112 S3: about 1 % of the frame; starting values, the first film tunes them


def _scaled(im, scale=1.0):
    if scale != 1.0:
        w2, h2 = max(2, round(ALIGN_W * scale)), max(2, round(ALIGN_H * scale))
        scaled = im.resize((w2, h2), Image.BILINEAR)
        canvas = Image.new('L', (ALIGN_W, ALIGN_H), int(ImageStat.Stat(im).mean[0]))
        canvas.paste(scaled, ((ALIGN_W - w2) // 2, (ALIGN_H - h2) // 2))
        im = canvas.crop((0, 0, ALIGN_W, ALIGN_H))
    return im


def _grey(png, scale=1.0):
    return _scaled(Image.open(BytesIO(png)).convert('L').resize((ALIGN_W, ALIGN_H), Image.BILINEAR), scale)


def pair_alignment(start_png, end_png):
    """design/112 S3: the end registered against the start in code: translation by phase correlation on grey copies, scale by a small search
    (the end resized about its centre and the best peak kept). A must line with the measured shift and scale; no model call."""
    import numpy as np
    m = _match(_fft(np.asarray(_grey(start_png), dtype=float)), lambda z: _grey(end_png, z))
    dx, dy, scale, shift = m['dx'], m['dy'], m['scale'], m['shift']   # the scale: the end as a zoom of the start
    ok = shift <= ALIGN_SHIFT and abs(scale - 1) <= ALIGN_SCALE
    return {'check': 'pair aligned', 'pass_when': 'the end frames the start: no shift, zoom or slide of the background', 'weight': 'must', 'pass': ok,
            'seen': f'shift {shift * 100:.1f} % of the frame ({dx:+d}, {dy:+d} px at {ALIGN_W} wide), scale {scale:.3f}' + ('' if ok else ': the pair would glide'),
            'shift_pct': round(shift * 100, 2), 'scale': scale}


def _fft(a):
    import numpy as np
    return np.fft.fft2((a - a.mean()) * np.outer(np.hanning(ALIGN_H), np.hanning(ALIGN_W)))


def _match(fa, grey_fn):
    """The best shift and scale of a picture against a prepared one: translation by phase correlation, scale by a small search (the best peak kept)."""
    import numpy as np
    best = None
    for z in np.arange(0.95, 1.0501, 0.005):   # ponytail: a brute-force scale search, 21 FFTs on 256x144; no rotation
        b = np.asarray(grey_fn(float(z)), dtype=float)
        cross = fa * np.conj(_fft(b))
        r = np.fft.ifft2(cross / (np.abs(cross) + 1e-9)).real
        dy, dx = np.unravel_index(int(np.argmax(r)), r.shape)
        dy, dx = (dy - ALIGN_H if dy > ALIGN_H / 2 else dy), (dx - ALIGN_W if dx > ALIGN_W / 2 else dx)
        if best is None or r.max() > best[0]:
            best = (float(r.max()), int(dx), int(dy), float(z))
    _, dx, dy, z = best
    return {'dx': dx, 'dy': dy, 'scale': round(1 / z, 3), 'shift': (dx * dx + dy * dy) ** 0.5 / ALIGN_W}


DRIFT_MAX = 0.02   # design/112 S5: 2 % of the frame width, or 2 % of zoom, across a take; a starting value


def _frames(video_path, per_second=2, limit=12):
    """Up to twelve small grey frames of a take, two a second, straight from ffmpeg."""
    out = subprocess.run([settings().FFMPEG_EXECUTABLE, '-v', 'error', '-i', str(video_path), '-vf', f'fps={per_second},scale={ALIGN_W}:{ALIGN_H}', '-frames:v', str(limit),
                          '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True, check=True, timeout=120).stdout
    size = ALIGN_W * ALIGN_H
    return [Image.frombytes('L', (ALIGN_W, ALIGN_H), out[i * size:(i + 1) * size]) for i in range(len(out) // size)]


def take_drift(video_path, snapshot, frames=None):
    """design/112 S5: every later frame registered against the first; the worst shift and zoom. A must line for a locked-off camera (the take fails
    over DRIFT_MAX); measured and reported, not judged, when the shot names a camera move or the take was prepared before design/112. Code only."""
    import numpy as np
    frames = _frames(video_path) if frames is None else frames
    if len(frames) < 2:
        return None
    fa = _fft(np.asarray(frames[0], dtype=float))
    shift, zoom = 0.0, 0.0
    for fr in frames[1:]:
        m = _match(fa, lambda z, im=fr: _scaled(im, z))
        shift, zoom = max(shift, m['shift']), max(zoom, abs(m['scale'] - 1))
    locked = 'camera_move' in snapshot and not (snapshot.get('camera_move') or '').strip()
    ok = shift <= DRIFT_MAX and zoom <= DRIFT_MAX
    return {'check': 'camera drift', 'weight': 'must' if locked else 'should', 'pass': ok if locked else None,
            'pass_when': 'the frame holds still across the take: no drift, zoom or slide of the whole picture',
            'seen': f'drift up to {shift * 100:.1f} % of the frame, zoom up to {zoom * 100:.1f} %, over {len(frames)} frames'
                    + ('' if locked else ' (a camera move is planned, or the take is from before design/112: reported, not judged)'),
            'at_s': None, 'drift_pct': round(shift * 100, 2), 'zoom_pct': round(zoom * 100, 2)}


def ambient_moves(snapshot):
    """design/101 M1 allows `still: nothing else moves`; such a line asks for no movement and gets no must line."""
    line = str(snapshot.get('ambient') or '').strip()
    return line if line and not re.match(r'still\b', line, re.I) else ''


TAKE_SCHEMA = {'type': 'object', 'properties': {'lines': {'type': 'array', 'items': {'type': 'object', 'properties': {'n': {'type': 'integer'}, 'pass': {'type': 'boolean'}, 'seen': {'type': 'string'},
                                                                                     'at_s': {'type': 'number'}}, 'required': ['n', 'pass', 'seen']}}}, 'required': ['lines']}


def run_take_check(snapshot, video_path, sha256, transport_factory):
    """design/91 N3 and design/112 S5: the drift measured in code, then the take read by Gemini Flash against the fixed questions; the drift line joins the record either way. Never raises."""
    try:
        drift = take_drift(video_path, snapshot)
    except Exception as exc:   # ffmpeg missing, a short clip: the take is never held back by its measurement
        drift, drift_error = None, f'{exc.__class__.__name__}: {str(exc)[:200]}'
    record = _model_take_check(snapshot, video_path, sha256, transport_factory)
    if drift:
        record['lines'] = list(record.get('lines') or []) + [drift]
        if drift['pass'] is False and drift['weight'] == 'must':
            record['must_failed'] = list(record.get('must_failed') or []) + [drift]
    elif 'drift_error' in dir():
        record['drift_error'] = drift_error
    return record


def _model_take_check(snapshot, video_path, sha256, transport_factory):
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
                         (['What must move around the action (the ambient line): ' + str(snapshot['ambient'])[:1000]] if ambient_moves(snapshot) else []) +
                         (['The light (the light line): ' + str(snapshot['light'])[:1000]] if snapshot.get('light') else []) +
                         [str(l)[:600] for l in (snapshot.get('tool_lines') or []) + (snapshot.get('heading_lines') or []) + (snapshot.get('gaze_lines') or [])
                          + ([snapshot['fixed_line']] if snapshot.get('fixed_line') else []) + (snapshot.get('person_lines') or [])
                          + (['The camera: ' + ((snapshot.get('camera_move') or '').strip() or 'locked off, no move')] if 'camera_move' in snapshot else [])])   # design/110 F5, F6; design/111 F7, F8, F16; design/112 S4
        take_lines = take_lines_for(snapshot)
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


def drawn_lines_check(first_png, last_png, lines, prompt, transport_factory):
    """design/113 E3 (SK's answer 3): one Gemini Flash read of a drawing's first and last frame against its claims, relationships and labels. Never raises."""
    record = {'lines': [], 'must_failed': [], 'model': CHECK_MODEL}
    if not lines:
        return record
    try:
        key = settings().GEMINI_API_KEY.get_secret_value().strip()
        if not key:
            record['error'] = 'no Gemini key on the server'
            return record
        transport = transport_factory(key, CHECK_MODEL, terminal_deadline_seconds=180, initial_soft_wait_seconds=30, on_update=lambda e: None, capture_answer_deltas=False)
        received = transport.generate(build(last_png, [('first frame', first_png)], lines, 'A drawn graphic rendered by the server from a plan; Reference 1 is its first frame, the candidate its last. ' + str(prompt or '')))
        body = received.get('body')
        if not isinstance(body, dict):
            body = json.loads(received.get('raw') or '{}')
        got = read(body, lines)
        record.update(lines=got['lines'], must_failed=got['must_failed'])
    except Exception as exc:   # the check never blocks a drawing
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
    None for a graphic, a sheet, or a film without footage frames. Code, not a model: free; a must line since design/111 F18."""
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
    return {'check': 'light and colour', 'pass_when': 'the light, colour and saturation match the footage beside it', 'weight': 'must', 'pass': not jumps, 'seen': seen}   # design/111 F18: a must (SK, 27 Oct), the jumps untuned


DETAIL_MIN, DETAIL_FRAMES = 0.6, 3   # design/104 C3; ponytail: the handover's 40 % smoother, untuned; tune it from the ratios the line reports


def _detail(png):
    return ImageStat.Stat(Image.open(BytesIO(png)).convert('L').resize((768, 432)).filter(ImageFilter.FIND_EDGES)).mean[0]


def detail_line(store, session, ref, png):
    """design/104 C3: the picture's fine detail (edge energy) against the footage frames beside its gap, as N9 does for the light; code, not a model,
    and a should line. None for a graphic, a sheet, or fewer than three footage frames."""
    if ref.get('element_kind') in ('graphic', 'style') or ref.get('kind') not in ('keyframe', 'isolated'):
        return None
    frames = [r for r in session.get('references', {}).values() if r.get('kind') == 'frame' and r.get('status') == 'approved' and r.get('key')]
    beside = {c for c in ((session.get('gap_neighbours') or {}).get(ref.get('gap_id')) or {}).values() if c}
    near = [r for r in frames if (r.get('source') or {}).get('media_id') in beside]
    frames = near if len(near) >= DETAIL_FRAMES else frames
    values = []
    for r in frames[:6]:
        try:
            values.append(_detail(store.get(r['key'])))
        except Exception:
            continue
    if len(values) < DETAIL_FRAMES or not sum(values):
        return None
    ratio = _detail(png) / (sum(values) / len(values))
    return {'check': 'fine detail', 'pass_when': 'the picture has about the fine detail of the footage beside it, not much smoother', 'weight': 'should',
            'pass': ratio >= DETAIL_MIN, 'seen': f'{ratio:.2f} of the fine detail of the footage beside it ({len(values)} frames)'}


def run_check(store, session, ref, result, transport_factory):
    """The whole check for one retained candidate, Gemini's lines and then the measured light (design/91 N9); returns the check record. Never raises."""
    try:
        png = store.get(result['key'])   # review 27 Oct: read once, used by the model check, the light line and the detail line
    except Exception:
        png = None
    record = _model_check(store, session, ref, result, transport_factory, png)
    try:
        light = light_line(store, session, ref, png)
    except Exception:
        light = None
    if light:
        record['lines'] = list(record.get('lines') or []) + [light]
        if light.get('pass') is False:   # design/111 F18: a failed light line fails the picture
            record['must_failed'] = list(record.get('must_failed') or []) + [light]
    try:
        detail = detail_line(store, session, ref, png)   # design/104 C3
    except Exception:
        detail = None
    if detail:
        record['lines'] = list(record.get('lines') or []) + [detail]
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


def check_lines(store, session, ref, lines, transport_factory):
    """design/110 F3: a few lines asked of a stored picture outside its check (a start made before this release, at approval). Never raises;
    with no key or no answer the lines come back undecided, never passed."""
    return _model_check(store, session, ref, {'key': ref['key'], 'width': ref.get('width'), 'height': ref.get('height')}, transport_factory, lines=lines)


def _model_check(store, session, ref, result, transport_factory, png=None, lines=None):
    """Gemini's part of the check: the lines and the code checks. Never raises."""
    parents = [session['references'].get(p.get('id')) or {} for p in (ref.get('generation') or {}).get('parents') or []]
    lines = lines or lines_of(ref)
    record = {'code': code_checks(ref, result, parents), 'lines': [], 'must_failed': [], 'model': CHECK_MODEL}
    try:
        key = settings().GEMINI_API_KEY.get_secret_value().strip()
        if not key:
            record['error'] = 'no Gemini key on the server'
            return record
        pngs = [(('scene' if p.get('kind') == 'frame' else p.get('kind') or 'reference'), store.get(p['key'])) for p in parents if p.get('key')]
        transport = transport_factory(key, CHECK_MODEL, terminal_deadline_seconds=180, initial_soft_wait_seconds=30, on_update=lambda e: None, capture_answer_deltas=False)
        received = transport.generate(build(png if png is not None else store.get(result['key']), pngs, lines, (ref.get('generation') or {}).get('prompt')))
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
            **({'role': ref['role']} if ref.get('role') else {}),   # review 27 Oct: a fix of a start is a start, with the same end to make
            **({'end_prompt': ref['pending_end']['prompt'], 'end_answer': ref['pending_end'].get('answer')} if ref.get('pending_end') else {}),
            'answer': {**(ref.get('answer') or {}), 'prompt': prompt, 'base_image_id': ref['id'], 'single_change': failed['pass_when']} if ref.get('answer') else None}
