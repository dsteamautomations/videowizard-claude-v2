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


def room(a, z, row):
    """How far each end of a footage shot (source frames a to z) may move, in source frames, and the most it may lose: inside its usable
    window, keeping its main action whole and never shorter than its hold."""
    spare = max(0, (z - a) - max(1, math.ceil(Fraction(str(row.get('min_hold_s') or 0)) * _fps(row))))
    peak = row.get('action_peak')
    later = max(0, min(spare, peak['in_frame'] - a if peak else spare))
    sooner = max(0, min(spare, z - peak['out_frame'] if peak else spare))
    return {'start_earlier': max(0, a - row['in_frame']), 'start_later': later, 'end_earlier': sooner, 'end_later': max(0, row['out_frame'] - z), 'lose': min(spare, later + sooner)}


def room_text(a, z, row):
    """What the trim form and a refused trim say: the shot's length, what it can lose and what it can gain, in seconds (rounded down)."""
    r, fps = room(a, z, row), _fps(row)
    s = lambda n: f'{math.floor(n / fps * 10) / 10:.1f}'
    grow = r['start_earlier'] + r['end_later']
    return (f"This shot: {s(z - a)} s. "
            + (f"It can lose up to {s(r['lose'])} s (start up to {s(r['start_later'])} s later, end up to {s(r['end_earlier'])} s earlier). " if r['lose'] else 'It cannot get shorter. ')
            + (f"It can grow by up to {s(grow)} s (start up to {s(r['start_earlier'])} s earlier, end up to {s(r['end_later'])} s later)." if grow else 'It cannot grow.'))


def fit_piece(row, frames, tl_fps, partial=False):
    """Where a piece sits in a shot of `frames` timeline frames: (source in, source out, timeline frames), around its main action; or the
    reason it cannot be used there, in plain words. partial (an all-AI scene): a piece shorter than the scene takes what it has."""
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
    if need / fps < Fraction(str(row.get('min_hold_s') or 0)) or need < 1:
        return f"it needs {row.get('min_hold_s')} s on screen to be understood; the shot has {sec(need)}"
    a, peak = row['in_frame'], row.get('action_peak')
    if peak:
        action = peak['out_frame'] - peak['in_frame']
        if action > need:
            return f'its main action takes {sec(action)}; the shot has {sec(need)}'
        a = max(row['in_frame'], min(peak['in_frame'] - (need - action) // 2, row['out_frame'] - need))
    return a, a + need, frames


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
            open_.append((s, e, a, z, row))
        off = total - targets[o['beat_id']]
        if not off:
            continue
        takers = []
        for s, e, a, z, row in open_:
            n = abs(off) * _fps(row) / tl
            if n.denominator != 1:
                continue
            n, r = int(n), room(a, z, row)
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
