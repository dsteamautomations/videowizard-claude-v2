"""SK, 23 Nov 2026 (VW-25, plan of action Phase 4): the rules behind the review page's trim in seconds, its scene balance and its "Other clips",
as pure functions. The page and the chat command reach them through the same server functions in stage.py (one flow, two front ends)."""
import math
import re
from fractions import Fraction

SECONDS = re.compile(r'^\s*start\s*:\s*([+-]?\d+(?:\.\d+)?)\s*s?\s*,\s*end\s*:\s*([+-]?\d+(?:\.\d+)?)\s*s?\s*$')


def parse_edit(edit):
    """'in:±frames,out:±frames' (source frames) → {'in': n, 'out': n}."""
    out = {'in': 0, 'out': 0}
    for part in str(edit).split(','):
        k, _, v = part.strip().partition(':')
        if k in out:
            out[k] = int(v)
    return out


def _fps(row):
    return Fraction(str(row['source_fps']))


def seconds_edit(edit, row):
    """'start:0.5,end:1' (seconds: start later by, end earlier by; a minus value lengthens) → the same trim in the clip's own frames,
    'in:25,out:-50'. None when the edit is not in seconds (the older way, in source frames, kept until the next release)."""
    m = SECONDS.match(str(edit or ''))
    if not m:
        return None
    return f'in:{round(Fraction(m.group(1)) * _fps(row))},out:{-round(Fraction(m.group(2)) * _fps(row))}'


def edit_text(edit, row):
    """A recorded trim in plain words, for the page and the chat."""
    e, fps = parse_edit(edit), _fps(row)
    parts = ([f"starts {abs(float(e['in'] / fps)):.1f} s {'later' if e['in'] > 0 else 'earlier'}"] if e['in'] else []) + \
            ([f"ends {abs(float(e['out'] / fps)):.1f} s {'later' if e['out'] > 0 else 'earlier'}"] if e['out'] else [])
    return ', '.join(parts) or 'no change'


# SK, 25 Nov 2026 (VW-25 issue 3b, requirement R3b): a footage shot may be shorter than its piece's hold when it carries `short`, one of
# these six reasons (the words are what the operator reads on the card).
SHORT = {'list_item': 'one item of a list', 'thing': 'a thing, not an action', 'kinds': 'kinds of one thing side by side', 'repeated_action': 'a repeated action',
         'recap': 'a recap or a run of pictures', 'b_roll': 'B-roll under words with no specific claim'}
SHORT_S = 1               # the lowest length of a short shot, in seconds (D1b)
ALONE_S = Fraction(3, 2)  # a short shot under this stands only in a run (D1c) ...
RUN = 3                   # ... of this many shots in a row that each carry `short`
WIDE = ('WS', 'EWS')


def limits(row, short=None, held=False):
    """The one rule for the length of a footage shot. The options check, Trim, the trim form and Other clips all read it: (the lowest length
    in the clip's own frames, the action that stays whole as (first frame, end frame) or None, the camera move that ends that action early or
    None).
    - No `short`: the piece's hold, and its main action whole. Two exceptions: a still frame held at the end (`held`) has no lowest length;
      the action is complete where a reported camera move starts inside it.
    - With `short` (one of SHORT): 1.0 s in place of the hold, rounded up to whole frames of the clip; the main action need not be whole,
      except for a repeated action.
    Older way retired: four copies of this rule (validator._piece, stage._trim, room and fit_piece here), which did not agree: Trim and the
    trim form knew neither exception, Other clips not the camera move, and the check and Trim read the hold as a binary fraction."""
    least = 1 if held else max(1, math.ceil((SHORT_S if short else Fraction(str(row.get('min_hold_s') or 0))) * _fps(row)))
    peak = row.get('action_peak')
    if not peak or (short and short != 'repeated_action'):
        return least, None, None
    move = min((m for m in row.get('camera_moves') or [] if peak['in_frame'] < m['start_frame'] < peak['out_frame']), key=lambda m: m['start_frame'], default=None)
    return least, (peak['in_frame'], move['start_frame'] if move else peak['out_frame']), move


def short_why(a, z, row, short, match=None):
    """What the server can see against cutting source frames a to z short, in plain words, or None: a wide shot, a cut into a reported camera
    move, B-roll as the reason on a piece that is not placed as B-roll. (What is in the picture, the first time a thing is shown, a heavy crop
    and a pause in the narration it cannot see: the instruction and the operator's eye.)"""
    if row.get('effective_shot_size') in WIDE:
        return 'a wide shot is not cut short'
    move = next((m for m in row.get('camera_moves') or [] if a < m['end_frame'] and m['start_frame'] < z), None)
    if move:
        return f"a short shot does not cut into a camera move (the reported {move['kind']} at {move['start_frame']}-{move['end_frame']})"
    if short == 'b_roll' and match != 'b_roll':
        return 'it is cut short as B-roll, and this piece is not placed as B-roll'
    return None


def judge(a, z, row, short=None, held=False, match=None):
    """Which limits judge a shot cut at source frames a to z. `short` is a permission, used only by a cut that needs it: a cut that meets its
    piece's own hold and main action is judged by them, whatever it carries. Returns least, action and move (limits), `short` (the reason in
    use, None when the piece's own limits judge the cut), `why` (short_why: the cut may not be short) and `alone` (a short shot under 1.5 s:
    the proposal's check wants it in a run; never a still frame held at the end, whose frames are not its time on screen)."""
    least, action, move = limits(row, None, held)
    used = None
    if isinstance(short, str) and short in SHORT and (z - a < least or (action and not (a <= action[0] and action[1] <= z))):
        used, (least, action, move) = short, limits(row, short, held)
    return {'least': least, 'action': action, 'move': move, 'short': used, 'why': short_why(a, z, row, short, match) if used else None,
            'alone': bool(used) and not held and z - a < math.ceil(ALONE_S * _fps(row))}


def short_text(a, z, row, short, held, seconds):
    """The card's line for a shot that is cut short, "Short shot, 1.4 s: one item of a list", or None: no `short`, or the cut meets its
    piece's own hold and main action."""
    used = judge(a, z, row, short, held)['short']
    return f'Short shot, {seconds:.1f} s: {SHORT[used]}' if used else None


def room(a, z, row, short=None, held=False, match=None):
    """How far each end of a footage shot (source frames a to z) may move, in source frames, and the most it may lose: inside its usable
    window and inside its limits (limits: the piece's own, or those of a short shot when the shot carries `short` and may be cut short)."""
    least, action, _ = limits(row, short if isinstance(short, str) and short in SHORT and not short_why(a, z, row, short, match) else None, held)
    spare = max(0, (z - a) - least)
    later = max(0, min(spare, action[0] - a if action else spare))
    sooner = max(0, min(spare, z - action[1] if action else spare))
    return {'start_earlier': max(0, a - row['in_frame']), 'start_later': later, 'end_earlier': sooner, 'end_later': max(0, row['out_frame'] - z), 'lose': min(spare, later + sooner)}


def room_text(a, z, row, short=None, held=False, match=None):
    """What the trim form and a refused trim say: the shot's length, what it can lose and what it can gain, in seconds (rounded down)."""
    r, fps = room(a, z, row, short, held, match), _fps(row)
    s = lambda n: f'{math.floor(n / fps * 10) / 10:.1f}'
    grow = r['start_earlier'] + r['end_later']
    return (f"This shot: {s(z - a)} s. "
            + (f"It can lose up to {s(r['lose'])} s (start up to {s(r['start_later'])} s later, end up to {s(r['end_earlier'])} s earlier). " if r['lose'] else 'It cannot get shorter. ')
            + (f"It can grow by up to {s(grow)} s (start up to {s(r['start_earlier'])} s earlier, end up to {s(r['end_later'])} s later)." if grow else 'It cannot grow.'))


def fit_piece(row, frames, tl_fps, partial=False, short=None, match=None):
    """Where a piece sits in a shot of `frames` timeline frames: (source in, source out, timeline frames), around its main action; or the
    reason it cannot be used there, in plain words. partial (an all-AI scene): a piece shorter than the scene takes what it has.
    short: the shot's `short` (the piece the operator puts on a short shot takes it); match: how the piece would be placed (direct, b_roll or
    library). The piece's own limits are tried first, so `short` only adds pieces."""
    fps, tl = _fps(row), Fraction(str(tl_fps))
    sec = lambda n: f'{float(n / fps):.1f} s'
    have = row['out_frame'] - row['in_frame']
    if partial and have * tl / fps < frames:
        frames = math.floor(have * tl / fps)
    need = frames * fps / tl
    if need.denominator != 1:
        return f"its frame rate ({float(fps):g} a second) does not divide this shot's length evenly"
    need = int(need)
    if have < need:
        return f'it has {sec(have)} of usable picture; the shot needs {sec(need)}'
    peak = row.get('action_peak')

    def place(short):
        least, action, _ = limits(row, short)
        if need < least:
            return f'a short shot needs {SHORT_S:.1f} s on screen; the shot has {sec(need)}' if short else f"it needs {row.get('min_hold_s')} s on screen to be understood; the shot has {sec(need)}"
        if action and action[1] - action[0] > need:
            return f'its main action takes {sec(action[1] - action[0])}; the shot has {sec(need)}'
        around = action or ((peak['in_frame'], peak['out_frame']) if peak else None)   # a short shot of a thing: the middle of its main action
        return max(row['in_frame'], min(around[0] - (need - (around[1] - around[0])) // 2, row['out_frame'] - need)) if around else row['in_frame']

    a = place(None)
    if isinstance(a, str) and isinstance(short, str) and short in SHORT and not partial:
        said, a = a, place(short)
        # ponytail: one placement is tried; a piece whose steady part lies elsewhere is refused. Slide the cut along the piece if operators miss such pieces.
        why = None if isinstance(a, str) else short_why(a, a + need, row, short, match)
        a = f'{said}; {why}' if why else a
    return a if isinstance(a, str) else (a, a + need, frames)


def balance(options, decisions, sl, rows, targets, tl_fps):
    """The scenes whose shots no longer add up to the scene's length after the trims: each with how much it is short or long, and every
    shot of the scene that can take the difference, with the trim that does it (ready to record)."""
    tl = Fraction(str(tl_fps))
    shot = {(s['option_number'], s['event_index']): s for s in sl if s['type'] == 'shot'}
    out = []
    for o in options:
        total, open_ = 0, []
        for i, ev in enumerate(o['events']):
            s = shot.get((o['option_number'], i))
            d = (decisions.get(str(s['no'])) if s else None) or {}
            if not s or ev.get('blank') or d.get('action') in ('REJECT', 'SWAP') or ev.get('sub_clip_id') not in rows:
                total += ev['timeline_frames']
                continue
            row = rows[ev['sub_clip_id']]
            e = parse_edit(d['edit']) if d.get('action') == 'TRIM' else {'in': 0, 'out': 0}
            a, z = ev['source_in_frame'] + e['in'], ev['source_out_frame'] + e['out']
            total += ev['timeline_frames'] if not (e['in'] or e['out']) else int(round((z - a) * tl / _fps(row)))
            open_.append((s, e, a, z, row, ev))
        off = total - targets[o['beat_id']]
        if not off:
            continue
        takers = []
        for s, e, a, z, row, ev in open_:
            n = abs(off) * _fps(row) / tl
            if n.denominator != 1:
                continue
            n, r = int(n), room(a, z, row, ev.get('short'), bool(ev.get('hold_last_frame')), ev.get('match'))
            if off < 0 and r['end_later'] + r['start_earlier'] >= n:     # the scene is short: this shot grows, at its end first
                end = min(n, r['end_later'])
                new = (e['in'] - (n - end), e['out'] + end)
            elif off > 0 and r['lose'] >= n:                              # the scene is long: this shot gives, at its end first
                end = min(n, r['end_earlier'])
                new = (e['in'] + (n - end), e['out'] - end)
            else:
                continue
            takers.append({'slide': str(s['no']), 'title': s['title'], 'edit': f'in:{new[0]},out:{new[1]}'})
        number = next(s['number'] for s in sl if s['option_number'] == o['option_number'])
        seconds = f'{abs(off) / float(tl):.1f}'
        out.append({'scene': number, 'beat_id': o['beat_id'], 'seconds': seconds, 'short': off < 0,
                    'text': f"Scene {number} is {seconds} s {'short' if off < 0 else 'long'} after the trim.", 'takers': takers})
    return out
