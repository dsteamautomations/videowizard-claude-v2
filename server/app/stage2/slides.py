"""design/21: the review film's numbered slides and its item sequence.

Every slide carries one running number in film order; the operator answers by number. Slide types:
option (a scene's first edit), backup (an alternative edit of the same scene), decision (a placement that needs the
operator's keep/drop: B-roll, reuse, check by eye, poor quality, an unsure join), blank (a stretch left for AI video or
animation). Option, backup and decision slides are silent; a blank is a captioned card under the continuing narration."""
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


def clip_name(row, cards):
    card = cards.get(row['clip_id']) or {}
    return ascii_text((card.get('descriptive_name') or row['clip_name']).replace('_', ' '))


def slides(doc, pk, fps):
    beats = {b['beat_id']: (i + 1, b) for i, b in enumerate(pk['beats'])}
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    cards = {c['clip_id']: c for c in pk.get('cards') or []}
    out, first = [], {}
    for o in doc['options']:
        n, b = beats[o['beat_id']]
        label = ascii_text(f"Scene {n}: {b.get('title') or b['beat_id']}")
        events = o.get('events') or []
        frames = sum(_frames(ev) for ev in events)
        shots = sum(1 for ev in events if not ev.get('blank'))
        no = len(out) + 1
        backup_for = first.get(o['beat_id'])
        head = f"#{no:02d} | {label} | " + (f"BACKUP for #{backup_for:02d} | " if backup_for else '') + f"{frames / fps:.1f} s | {shots} shot{'s' if shots != 1 else ''}"
        parts = [f"blank {_frames(ev) / fps:.1f} s" if ev.get('blank') else f"{clip_name(rows[ev['sub_clip_id']], cards)} ({_frames(ev) / fps:.1f} s)"
                 for ev in events if ev.get('blank') or ev.get('sub_clip_id') in rows]
        out.append({'no': no, 'type': 'backup' if backup_for else 'option', 'option_number': o['option_number'], 'beat_id': o['beat_id'], 'scene': label,
                    'frames': frames, 'shots': shots, 'backup_for': backup_for, 'lines': [head] + wrap('Clips: ' + ' + '.join(parts))})
        first.setdefault(o['beat_id'], no)
        for i, ev in enumerate(events):
            if ev.get('blank'):
                no = len(out) + 1
                out.append({'no': no, 'type': 'blank', 'option_number': o['option_number'], 'beat_id': o['beat_id'], 'event_index': i, 'frames': _frames(ev),
                            'intent': ev.get('intent', ''), 'lines': [f"#{no:02d} | BLANK | {label} | {_frames(ev) / fps:.1f} s", 'For AI video or animation'] + wrap(ev.get('intent', ''))})
            elif ev.get('decision'):
                no = len(out) + 1
                d = ev['decision']
                name = clip_name(rows[ev['sub_clip_id']], cards) if ev.get('sub_clip_id') in rows else ev.get('sub_clip_id', '')
                out.append({'no': no, 'type': 'decision', 'option_number': o['option_number'], 'beat_id': o['beat_id'], 'event_index': i, 'frames': _frames(ev),
                            'kind': d.get('kind'), 'question': d.get('question', ''),
                            'lines': [f"#{no:02d} | DECISION | {label}"] + wrap(d.get('question', '')) + [ascii_text(f"Keep or drop: {name} ({_frames(ev) / fps:.1f} s)")]})
    return out


def review_items(doc, pk, sl, event_items, fps):
    """The review film: each option's slide, then its narration and pictures; a decision slide splits the narration so the
    words stay with their pictures; a blank is a card the narration runs under."""
    beats = {b['beat_id']: b for b in pk['beats']}
    head = {s['option_number']: s for s in sl if s['type'] in ('option', 'backup')}
    inner = {(s['option_number'], s['event_index']): s for s in sl if s['type'] in ('blank', 'decision')}
    items = []
    for o in doc['options']:
        b = beats[o['beat_id']]
        items.append({'kind': 'slate', 'lines': head[o['option_number']]['lines']})
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
                pending.append({'kind': 'card', 'frames': _frames(ev), 'lines': s['lines'] if s else ['BLANK']})
            else:
                label = f"#{s['no']:02d} DECISION" if s and s['type'] == 'decision' else f"#{head[o['option_number']]['no']:02d}"
                pending += [{**it, 'label': label} for it in event_items([ev])]
            cursor += _frames(ev)
        items += [{'kind': 'narration', 'start_s': seg_start / fps, 'end_s': cursor / fps}] + pending
    return items


def scene_summary(doc, pk, fps):
    """Per scene: seconds of real footage, seconds of blanks, decisions waiting (first option of each scene; declared gaps are all blank)."""
    out = []
    gaps = {g['beat_id'] for g in doc.get('gaps') or []}
    by_beat = {}
    for o in doc['options']:
        by_beat.setdefault(o['beat_id'], o)
    for i, b in enumerate(pk['beats'], 1):
        o = by_beat.get(b['beat_id'])
        total = b['target_beat_frames']
        if not o:
            out.append({'scene': i, 'beat_id': b['beat_id'], 'title': b.get('title'), 'real_s': 0.0, 'blank_s': round(total / fps, 2), 'decisions': 0,
                        'note': 'declared blank' if b['beat_id'] in gaps else 'no option'})
            continue
        real = sum(_frames(ev) for ev in o['events'] if not ev.get('blank') and not ev.get('decision'))
        dec = [ev for ev in o['events'] if ev.get('decision')]
        out.append({'scene': i, 'beat_id': b['beat_id'], 'title': b.get('title'), 'real_s': round(real / fps, 2),
                    'blank_s': round(sum(_frames(ev) for ev in o['events'] if ev.get('blank')) / fps, 2),
                    'decision_s': round(sum(_frames(ev) for ev in dec) / fps, 2), 'decisions': len(dec)})
    return out
