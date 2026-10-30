"""design/21: the review film's numbered slides and its item sequence.

Labels (design/125 O2, O3; scheme 2): a slide's number is its scene's number (Scene 5 is #5); a second version of a scene is "#5-2",
"second choice"; the blanks and decision slides inside a cut take its number and a letter in event order (#5A, #5-2A). Slides stored
before design/125 (no scheme) keep their running numbers and "BACKUP for #N". Slide types: option (a scene's first cut), backup (its
second choice), decision (a placement that needs the operator's keep/drop: B-roll, reuse, check by eye, poor quality, an unsure join),
blank (a stretch left for AI video or animation). An AI-only scene (P13) is an option made of one blank: its own slide, no inner blank.
Option, backup and decision slides are silent; a blank is a captioned card under the continuing narration."""
import textwrap
import unicodedata

DECISION_KINDS = ('b_roll', 'reuse', 'check_by_eye', 'poor_quality', 'join', 'other')
WRAP = 58   # characters per line at the slide font size


def ascii_text(text):
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')


def wrap(text, width=WRAP):
    return textwrap.wrap(ascii_text(text), width) or ['']


def _frames(ev):
    return ev.get('timeline_frames', ev.get('_timeline_frames', 0))


def letter(n):
    """1 → A, 26 → Z, 27 → AA."""
    out = ''
    while n > 0:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def clip_name(row, cards):
    card = cards.get(row['clip_id']) or {}
    return ascii_text((card.get('descriptive_name') or row['clip_name']).replace('_', ' '))


def slides(doc, pk, fps):
    """design/125 O1–O3, O8: every slide carries scheme 2 and a hint; a scene slide counts its sure shots (footage without a decision); when
    every footage piece is a decision and the scene has no second choice, its parts decide it (parts_decide)."""
    beats = {b['beat_id']: (i + 1, b) for i, b in enumerate(pk['beats'])}
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    cards = {c['clip_id']: c for c in pk.get('cards') or []}
    versions = {}
    for o in doc['options']:
        versions[o['beat_id']] = versions.get(o['beat_id'], 0) + 1
    out, first, seen = [], {}, {}
    for o in doc['options']:
        n, b = beats[o['beat_id']]
        label = ascii_text(f"Scene {n}: {b.get('title') or b['beat_id']}")
        events = o.get('events') or []
        frames = sum(_frames(ev) for ev in events)
        shots = sum(1 for ev in events if not ev.get('blank'))
        sure = sum(1 for ev in events if not ev.get('blank') and not ev.get('decision'))
        seen[o['beat_id']] = seen.get(o['beat_id'], 0) + 1
        no = str(n) if seen[o['beat_id']] == 1 else f"{n}-{seen[o['beat_id']]}"
        backup_for = first.get(o['beat_id'])
        ai_only = not shots
        parts_decide = bool(shots) and not sure and versions[o['beat_id']] == 1
        head = (f"#{no} | {label} | " + ('second choice | ' if backup_for else '') + ('made with AI | ' if ai_only else '') + f"{frames / fps:.1f} s"
                + ('' if ai_only else f" | {shots} shot{'s' if shots != 1 else ''}"))
        clips = [f"blank {_frames(ev) / fps:.1f} s" if ev.get('blank') else f"{clip_name(rows[ev['sub_clip_id']], cards)} ({_frames(ev) / fps:.1f} s)"
                 for ev in events if ev.get('blank') or ev.get('sub_clip_id') in rows]
        body = ['For AI video or animation'] + wrap(' '.join(str(ev.get('intent') or '') for ev in events)) if ai_only else wrap('Clips: ' + ' + '.join(clips))
        if backup_for:
            hint = f"another way to cut scene {n}; keep only one of {backup_for} and {no}"
        elif ai_only:
            hint = 'the whole scene made with AI; Keep leaves it to AI, Reject sends it back to look for footage'
        elif parts_decide:
            hint = 'decided by its parts below; here only a trim (Trim a shot)'
        else:
            hint = 'the whole scene as cut; Keep uses it, Reject makes this scene with AI, Trim a shot changes one shot'
        top = {'no': no, 'number': n, 'scheme': 2, 'type': 'backup' if backup_for else 'option', 'option_number': o['option_number'], 'beat_id': o['beat_id'], 'scene': label,
               'frames': frames, 'shots': shots, 'sure_shots': sure, 'backup_for': backup_for, 'hint': hint, 'background': 'blue' if backup_for else 'black',
               **({'ai_only': True} if ai_only else {}), **({'parts_decide': True} if parts_decide else {}), 'lines': [head] + body}
        out.append(top)
        first.setdefault(o['beat_id'], no)
        if ai_only:
            continue
        inner, labels = 0, []
        for i, ev in enumerate(events):
            if ev.get('blank'):
                inner += 1
                lab = f'{no}{letter(inner)}'
                out.append({'no': lab, 'number': n, 'scheme': 2, 'type': 'blank', 'option_number': o['option_number'], 'beat_id': o['beat_id'], 'event_index': i, 'frames': _frames(ev),
                            'intent': ev.get('intent', ''), 'hint': 'made with AI later; nothing to answer',
                            'lines': [f"#{lab} | BLANK | {label} | {_frames(ev) / fps:.1f} s", 'For AI video or animation'] + wrap(ev.get('intent', ''))})
            elif ev.get('decision'):
                inner += 1
                lab = f'{no}{letter(inner)}'
                labels.append(lab)
                d = ev['decision']
                name = clip_name(rows[ev['sub_clip_id']], cards) if ev.get('sub_clip_id') in rows else ev.get('sub_clip_id', '')
                out.append({'no': lab, 'number': n, 'scheme': 2, 'type': 'decision', 'option_number': o['option_number'], 'beat_id': o['beat_id'], 'event_index': i, 'frames': _frames(ev),
                            'kind': d.get('kind'), 'question': d.get('question', ''), 'hint': 'one doubtful piece; Keep uses it, Drop leaves an AI stretch in its place',
                            'lines': [f"#{lab} | DECISION | {label}"] + wrap(d.get('question', '')) + [ascii_text(f"Keep or drop: {name} ({_frames(ev) / fps:.1f} s)")]})
        if parts_decide:
            top['parts'] = labels   # O1: the decisions that decide this scene, named in its refusal
    return out


def review_items(doc, pk, sl, event_items, fps):
    """The review film: each option's slide, then its narration and pictures; a decision slide splits the narration so the
    words stay with their pictures; a blank is a card the narration runs under (an AI-only scene's one blank shows its scene slide's lines).
    design/125 O8: a second choice's slide card carries its blue background."""
    beats = {b['beat_id']: b for b in pk['beats']}
    head = {s['option_number']: s for s in sl if s['type'] in ('option', 'backup')}
    inner = {(s['option_number'], s['event_index']): s for s in sl if s['type'] in ('blank', 'decision')}
    items = []
    for o in doc['options']:
        b = beats[o['beat_id']]
        top = head[o['option_number']]
        items.append({'kind': 'slate', 'lines': top['lines'], **({'background': top['background']} if top.get('background', 'black') != 'black' else {})})
        seg_start = cursor = b['timeline_start_frame']
        pending = []
        for i, ev in enumerate(o['events']):
            s = inner.get((o['option_number'], i))
            if s and s['type'] == 'decision':
                if cursor > seg_start:
                    items += [{'kind': 'narration', 'start_s': seg_start / fps, 'end_s': cursor / fps}] + pending
                pending, seg_start = [], cursor
                items.append({'kind': 'slate', 'lines': s['lines']})
            if ev.get('blank'):
                pending.append({'kind': 'card', 'frames': _frames(ev), 'lines': s['lines'] if s else top['lines']})
            else:
                label = f"#{s['no']} DECISION" if s and s['type'] == 'decision' else f"#{head[o['option_number']]['no']}"
                pending += [{**it, 'label': label} for it in event_items([ev])]
            cursor += _frames(ev)
        items += [{'kind': 'narration', 'start_s': seg_start / fps, 'end_s': cursor / fps}] + pending
    return items


def scene_summary(doc, pk, fps):
    """Per scene: seconds of real footage, seconds of blanks, decisions waiting (first option of each scene)."""
    out = []
    by_beat = {}
    for o in doc['options']:
        by_beat.setdefault(o['beat_id'], o)
    for i, b in enumerate(pk['beats'], 1):
        o = by_beat.get(b['beat_id'])
        total = b['target_beat_frames']
        if not o:
            out.append({'scene': i, 'beat_id': b['beat_id'], 'title': b.get('title'), 'real_s': 0.0, 'blank_s': round(total / fps, 2), 'decisions': 0,
                        'note': 'no option'})
            continue
        real = sum(_frames(ev) for ev in o['events'] if not ev.get('blank') and not ev.get('decision'))
        dec = [ev for ev in o['events'] if ev.get('decision')]
        out.append({'scene': i, 'beat_id': b['beat_id'], 'title': b.get('title'), 'real_s': round(real / fps, 2),
                    'blank_s': round(sum(_frames(ev) for ev in o['events'] if ev.get('blank')) / fps, 2),
                    'decision_s': round(sum(_frames(ev) for ev in dec) / fps, 2), 'decisions': len(dec)})
    return out
