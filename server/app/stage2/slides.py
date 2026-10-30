"""design/21, design/127: the review film's rows and its item sequence, by scene and shot (scheme 3).

A scene is a header (no answer): "Scene 1", its title, its total time, its shots. Every event of the scene's cut is a shot, numbered in play order
(1.1, 1.2): a footage shot (direct or B-roll) is answered KEEP, REJECT or TRIM; an AI shot inside a scene needs nothing; the one AI shot of an
all-AI scene is answered Keep AI (KEEP) or Find footage (REJECT). An alternative belongs to a footage shot (1.2A1: the same words, the same
length) and opens only when its shot is rejected. A doubtful shot carries a note {kind, question}, shown with it. In the film, a card comes
only before a scene and before an alternative; footage carries a strip with its label and the words spoken; an AI shot is a card with its words."""
import textwrap
import unicodedata

NOTE_KINDS = ('reuse', 'check_by_eye', 'poor_quality', 'join', 'other')
WRAP = 58   # characters per line at the card font size
COLOURS = ('#1D9E75', '#7F77DD', '#D85A30', '#378ADD', '#BA7517', '#D4537E', '#639922', '#5F5E5A')   # one per scene, in turn


def ascii_text(text):
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')


def wrap(text, width=WRAP):
    return textwrap.wrap(ascii_text(text), width) or ['']


def _frames(ev):
    return ev.get('timeline_frames', ev.get('_timeline_frames', 0))


def clip_name(row, cards):
    card = cards.get(row['clip_id']) or {}
    return ascii_text((card.get('descriptive_name') or row['clip_name']).replace('_', ' '))


def scene_colour(n):
    return COLOURS[(n - 1) % len(COLOURS)]


def spoken(words, a, z):
    """The narration words whose start falls inside [a, z) timeline frames."""
    return ' '.join(str(w['text']) for w in words if a <= w['start_frame'] < z)


def said_lines(said, most=6):
    """The words on a card: wrapped, at most six lines (a long AI scene's words would run off the card), the last cut with "..."."""
    lines = wrap(f'"{said}"') if said else []
    return lines if len(lines) <= most else lines[:most - 1] + [lines[most - 1][:WRAP - 3] + '...']


def _seconds(frames, fps):
    return f'{frames / fps:.1f} s'


def slides(doc, pk, fps):
    beats = {b['beat_id']: (i + 1, b) for i, b in enumerate(pk['beats'])}
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    cards = {c['clip_id']: c for c in pk.get('cards') or []}
    words = (pk.get('narration') or {}).get('words') or []
    out = []
    for o in doc['options']:
        n, b = beats[o['beat_id']]
        title = ascii_text(b.get('title') or b['beat_id'])
        events = o.get('events') or []
        frames = sum(_frames(ev) for ev in events)
        ai = sum(1 for ev in events if ev.get('blank'))
        footage = len(events) - ai
        ai_only = not footage
        base = {'number': n, 'scheme': 3, 'beat_id': o['beat_id'], 'option_number': o['option_number'], 'colour': scene_colour(n), 'scene': f'Scene {n}: {title}'}
        out.append({**base, 'no': str(n), 'type': 'scene', 'title': f'Scene {n}', 'frames': frames, 'shots': footage, 'ai_shots': ai,
                    'hint': 'the scene; its shots below are answered one by one',
                    'lines': [f'Scene {n}', title, f'Total time: {_seconds(frames, fps)}',
                              f'Shots: {len(events)} ' + ('(made with AI)' if ai_only else f'({ai} made with AI, {footage} footage)' if ai else '(footage)')]})
        at = b['timeline_start_frame']
        for i, ev in enumerate(events, 1):
            k = _frames(ev)
            said = ascii_text(spoken(words, at, at + k))
            label, name = f'{n}.{i}', f'Scene {n} · Shot {i}'
            common = {**base, 'event_index': i - 1, 'frames': k, 'at_frame': at, 'words': said}
            at += k
            if ev.get('blank'):
                out.append({**common, 'no': label, 'type': 'ai', 'title': name, 'intent': ev.get('intent', ''),
                            **({'ai_only': True, 'hint': 'the whole scene made with AI; Keep AI leaves it to AI, Find footage sends it back to look for footage'}
                               if ai_only else {'hint': 'made with AI later; nothing to answer'}),
                            'lines': [f'{name} · made with AI', f'Time: {_seconds(k, fps)}'] + said_lines(said)
                            + wrap('For AI: ' + str(ev.get('intent', '')))})
                continue
            row = rows.get(ev.get('sub_clip_id')) or {'clip_id': '', 'clip_name': ev.get('sub_clip_id', '')}
            b_roll = ev.get('match') == 'b_roll'
            what = clip_name(row, cards)
            out.append({**common, 'no': label, 'type': 'shot', 'title': name, 'clip': what, 'b_roll': b_roll,
                        'note': ev.get('note') if isinstance(ev.get('note'), dict) else None,
                        'hint': ('B-roll: fine to reject. ' if b_roll else '') + 'Keep uses it, Reject leaves an AI stretch in its place, Trim shortens or shifts it',
                        'lines': [name + (' · B-roll' if b_roll else ''), what, f'Time: {_seconds(k, fps)}'] + said_lines(said)})
            for m, alt in enumerate(ev.get('alternatives') or [], 1):
                arow = rows.get(alt.get('sub_clip_id')) or {'clip_id': '', 'clip_name': alt.get('sub_clip_id', '')}
                aname = f'{name} · Alternative {m}'
                out.append({**common, 'no': f'{label}A{m}', 'type': 'alternative', 'title': aname, 'of': label, 'alt_index': m - 1, 'clip': clip_name(arow, cards),
                            'b_roll': alt.get('match') == 'b_roll', 'hint': f'another clip for Shot {i}; open when Shot {i} is rejected; keep at most one',
                            'lines': [aname, clip_name(arow, cards), f'Time: {_seconds(k, fps)}', f'Words: the same as Shot {i}']})
    return out


def review_items(doc, pk, sl, event_items, fps):
    """The review film: each scene's card, then its narration and pictures. Footage carries its strip (label, words, B-roll, colour); an AI
    shot is a card under the continuing narration; after a shot with alternatives, each alternative has its card and the shot's narration again.
    Every item names its row (`slide`) for the page's cues."""
    beats = {b['beat_id']: b for b in pk['beats']}
    by_key = {(s['option_number'], s['type'], s.get('event_index'), s.get('alt_index')): s for s in sl}
    items = []

    def strip(s):
        return {'label': s['title'], 'words': s.get('words', ''), 'b_roll': bool(s.get('b_roll')), 'colour': s['colour']}

    for o in doc['options']:
        head = by_key[(o['option_number'], 'scene', None, None)]
        items.append({'kind': 'slate', 'lines': head['lines'], 'colour': head['colour'], 'slide': head['no']})
        seg_start = cursor = beats[o['beat_id']]['timeline_start_frame']
        pending = []
        for i, ev in enumerate(o['events']):
            n = _frames(ev)
            cursor += n
            if ev.get('blank'):
                s = by_key[(o['option_number'], 'ai', i, None)]
                pending.append({'kind': 'card', 'frames': n, 'lines': s['lines'], 'colour': s['colour'], 'slide': s['no']})
                continue
            s = by_key[(o['option_number'], 'shot', i, None)]
            pending += [{**it, 'strip': strip(s), 'slide': s['no']} for it in event_items([ev])]
            if ev.get('alternatives'):   # the shot's words, then each alternative with its card and the same words again
                items += [{'kind': 'narration', 'start_s': seg_start / fps, 'end_s': cursor / fps}] + pending
                pending, seg_start = [], cursor
                for m, alt in enumerate(ev['alternatives']):
                    a = by_key[(o['option_number'], 'alternative', i, m)]
                    items += [{'kind': 'slate', 'lines': a['lines'], 'colour': a['colour'], 'slide': a['no']},
                              {'kind': 'narration', 'start_s': (cursor - n) / fps, 'end_s': cursor / fps}]
                    items += [{**it, 'strip': strip(a), 'slide': a['no']} for it in event_items([{**alt, 'timeline_frames': n}])]
        if cursor > seg_start:
            items += [{'kind': 'narration', 'start_s': seg_start / fps, 'end_s': cursor / fps}] + pending
    return items


def scene_summary(doc, pk, fps):
    """Per scene: seconds of real footage, of B-roll and of AI, and the shots carrying a note (the scene's cut)."""
    out = []
    by_beat = {o['beat_id']: o for o in doc['options']}
    for i, b in enumerate(pk['beats'], 1):
        o = by_beat.get(b['beat_id'])
        if not o:
            out.append({'scene': i, 'beat_id': b['beat_id'], 'title': b.get('title'), 'real_s': 0.0, 'b_roll_s': 0.0, 'blank_s': round(b['target_beat_frames'] / fps, 2),
                        'notes': 0, 'note': 'no option'})
            continue
        evs = o['events']
        secs = lambda pick: round(sum(_frames(ev) for ev in evs if pick(ev)) / fps, 2)
        out.append({'scene': i, 'beat_id': b['beat_id'], 'title': b.get('title'), 'real_s': secs(lambda e: not e.get('blank') and e.get('match') != 'b_roll'),
                    'b_roll_s': secs(lambda e: e.get('match') == 'b_roll'), 'blank_s': secs(lambda e: e.get('blank')),
                    'notes': sum(1 for ev in evs if ev.get('note')), 'alternatives': sum(len(ev.get('alternatives') or []) for ev in evs)})
    return out
