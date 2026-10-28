"""design/115: the editor's package once every shot is placed, before the server's assembly (H1). The events come from the master plan (the camera
cuts) and the recorded gaps (the selected takes, stills, drawings, sequences and clip stretches), the files are the raw ones the run holds, and the
timeline, the cut list (H5) and the captions (H3) are written from them. The server's own assembly stays the proof copy; nothing here renders."""
import csv
import io
from fractions import Fraction

from .delivery import layout, resolve_events


def gaps_missing(plan, outputs):
    """The gaps of the master plan that have no recorded visuals output yet: the bundle is refused while any remains (SK's answer 1)."""
    recorded = {o['unit'] for o in outputs if o['stage'] == 'visuals' and o['unit']}
    return [g['shot_id'] for g in plan.get('gaps') or [] if g['shot_id'] not in recorded]


def _frames(seconds, fps):
    return int(round(Fraction(str(seconds)) * Fraction(str(fps))))


def events_of(plan, pk, outputs, clips):
    """The resolve events of the early package and the AI files it carries: the master's camera events through resolve_events as they are
    (no stabilisation: no assembly choice exists yet), then one row per placed shot of every gap in placement order.
    Returns (events, ai_files) with ai_files = [{'name', 'key', 'sha256', 'bytes'}] under Media/AI."""
    fps = Fraction(str(pk['timeline']['fps']))
    by_gap = {o['unit']: o for o in outputs if o['stage'] == 'visuals' and o['unit']}
    events, ai_files, seen = [], [], set()
    camera = {e['timeline_in_frame']: e for e in plan['events'] if e['kind'] == 'event'}
    cam_rows = {e['sub_clip_id']: r for e, r in zip(camera.values(), resolve_events({'events': list(camera.values())}, pk, plan, clips))}
    for ev in plan['events']:
        if ev['kind'] == 'event':
            events.append(cam_rows[ev['sub_clip_id']])
            continue
        gid = ev.get('gap_id') or ev['beat_id']
        vo = by_gap.get(gid)
        if not vo:
            continue
        files = {f['name']: f for f in vo['files']}
        for shot in sorted(vo['summary']['shots'], key=lambda s: s['placement']['start_frame']):
            sid, pl = shot['shot_id'], shot['placement']
            rec_in, rec_out = pl['start_frame'], pl['end_frame']
            n = rec_out - rec_in
            media = shot.get('media') or {}
            if shot.get('source') == 'clip':   # design/89 B3: a stretch of an original, cut from the camera file itself
                c = media['clip']
                src_fps = Fraction(str(c.get('fps') or fps))
                src_in = _frames(media['in_s'], src_fps)
                events.append({'file': layout('original', c['name']), 'kind': 'camera', 'clip_id': c['id'], 'source_in_frame': src_in, 'source_out_frame': src_in + int(Fraction(n) * src_fps / fps),
                               'record_in_frame': rec_in, 'record_out_frame': rec_out, 'source_fps': str(src_fps), 'zoom': 1.0, 'pan': 0.0, 'tilt': 0.0, 'rotation': 0.0, 'color_group': None,
                               'marker': {'name': sid, 'note': 'a stretch of the original, chosen at visuals', 'colour': 'Blue'}, 'a2': [], 'stabilized': False,
                               'source_frames': int(round(float(c.get('duration_s') or 0) * float(src_fps))) or None, 'crop_rect': media.get('crop_rect')})
                continue
            if shot.get('kind') == 'sequence':   # design/65 B8: one still per state, each held its frames; the build in order
                cursor = rec_in
                for st in media.get('states') or []:
                    f = files.get(st['name'])
                    hold = int(st.get('hold_frames') or 0)
                    if f and f['name'] not in seen:
                        ai_files.append({k: f[k] for k in ('name', 'key', 'sha256', 'bytes')})
                        seen.add(f['name'])
                    events.append({'file': layout('ai', st['name']), 'kind': 'still', 'source_in_frame': 0, 'source_out_frame': hold, 'record_in_frame': cursor, 'record_out_frame': cursor + hold,
                                   'source_fps': str(fps), 'zoom': 1.0, 'pan': 0.0, 'tilt': 0.0, 'rotation': 0.0, 'color_group': None,
                                   'marker': {'name': sid, 'note': f"state of {sid}; planned move {media.get('motion') or 'none'}", 'colour': 'Green'}, 'a2': [], 'stabilized': False, 'source_frames': hold})
                    cursor += hold
                continue
            name = f'{sid}.mp4' if shot.get('source') == 'take' else f"{sid}-asset{'.mp4' if shot.get('kind') == 'movie' else '.png'}"
            f = files.get(name)
            if f and f['name'] not in seen:
                ai_files.append({k: f[k] for k in ('name', 'key', 'sha256', 'bytes')})
                seen.add(f['name'])
            still = name.endswith('.png')
            avail = _frames(media['duration_s'], fps) if media.get('duration_s') else n
            events.append({'file': layout('ai', name), 'kind': 'still' if still else 'movie', 'source_in_frame': 0, 'source_out_frame': n if still else min(n, avail),
                           'record_in_frame': rec_in, 'record_out_frame': rec_out, 'source_fps': str(fps), 'zoom': 1.0, 'pan': 0.0, 'tilt': 0.0, 'rotation': 0.0, 'color_group': None,
                           'marker': {'name': sid, 'note': ('AI take' if shot.get('source') == 'take' else 'picture') + (f"; planned move {media.get('motion')}" if still and media.get('motion') else '')
                                      + ('; shorter than its slot: hold the last frame' if not still and avail < n else ''), 'colour': 'Green'},
                           'a2': [], 'stabilized': False, 'source_frames': n if still else avail})
    return events, ai_files


def tc(frames, fps):
    fps = Fraction(str(fps))
    whole = int(Fraction(frames) / fps)
    f = int(frames - whole * fps)
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    return f'{h:02d}:{m:02d}:{s:02d}:{f:02d}'


def cut_list_csv(events, fps):
    """design/115 H5: one row per cut, in the editor's terms: the file, the source in and out, the film in and out, in seconds and timecode."""
    fps_ = Fraction(str(fps))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['cut', 'kind', 'file', 'source in (s)', 'source in (tc)', 'source out (s)', 'source out (tc)', 'film in (s)', 'film in (tc)', 'film out (s)', 'film out (tc)', 'zoom', 'note'])
    for i, e in enumerate(events, 1):
        sf = Fraction(str(e.get('source_fps') or fps_))
        s_in, s_out = Fraction(e['source_in_frame']) / sf, Fraction(e['source_out_frame']) / sf
        r_in, r_out = Fraction(e['record_in_frame']) / fps_, Fraction(e['record_out_frame']) / fps_
        w.writerow([i, e.get('kind', 'camera'), e['file'], f'{float(s_in):.3f}', tc(e['source_in_frame'], sf), f'{float(s_out):.3f}', tc(e['source_out_frame'], sf),
                    f'{float(r_in):.3f}', tc(e['record_in_frame'], fps_), f'{float(r_out):.3f}', tc(e['record_out_frame'], fps_), f"{float(e.get('zoom') or 1.0):g}",
                    (e.get('marker') or {}).get('note') or ''])
    return buf.getvalue()


LINE_CHARS, LINES = 42, 2   # design/115 H3: a cue is at most two lines of 42 characters


def _wrap(text):
    words, lines, cur = text.split(), [], ''
    for w in words:
        if cur and len(cur) + 1 + len(w) > LINE_CHARS:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    return lines


def cues(sentences, words, fps):
    """One cue per sentence, broken at the recorded pauses when a sentence runs over two lines: the words of the sentence are grouped so that
    each group fits, splitting at the largest gap between words. Returns [{'start_frame', 'end_frame', 'text'}]."""
    out = []
    for s in sentences or []:
        mine = [w for w in words or [] if s['start_frame'] <= w['start_frame'] < s['end_frame']]
        if len(_wrap(s['text'].strip())) <= LINES or len(mine) < 2:
            out.append({'start_frame': s['start_frame'], 'end_frame': s['end_frame'], 'text': '\n'.join(_wrap(s['text'].strip())[:LINES]) or s['text'].strip()})
            continue
        groups, cur = [], [mine[0]]
        for w in mine[1:]:
            text = ' '.join(x['text'] for x in cur + [w])
            if len(_wrap(text)) > LINES:
                groups.append(cur)
                cur = [w]
            else:
                cur.append(w)
        groups.append(cur)
        for i, g in enumerate(groups):
            end = groups[i + 1][0]['start_frame'] if i + 1 < len(groups) else s['end_frame']
            out.append({'start_frame': g[0]['start_frame'], 'end_frame': end, 'text': '\n'.join(_wrap(' '.join(x['text'] for x in g))[:LINES])})
    return out


def srt(cues_, fps):
    from .delivery import srt_time
    fps_ = float(Fraction(str(fps)))
    lines = []
    for i, c in enumerate(cues_, 1):
        lines += [str(i), f"{srt_time(c['start_frame'] / fps_)} --> {srt_time(c['end_frame'] / fps_)}", c['text'], '']
    return '\n'.join(lines) + '\n'


def open_edit_text(code):
    return (f"# {code}: the editor's package (made once every shot was placed, before the server's assembly)\n\n"
            "What is here: `Timeline/` (the FCPXML timeline, an EDL, `Cut-list.csv`, the captions `.srt`), `Media/AI/` (every AI take, picture and drawing, the only copies),\n"
            "`Media/Voiceover/` (the final narration), `Relink-list.csv` (every camera file the film uses, with its length, frame rate, timecode and fingerprint), `manifest.json`.\n"
            "The camera files themselves are not in this folder: you hold the originals. The timeline names them by their file names, and every cut carries its source in and out.\n\n"
            "## Open it in DaVinci Resolve Studio\n\n"
            "1. `vw delivery open --originals \"<the folder with the camera originals>\"` imports the timeline into a project named after the run and links the camera cuts to the originals in one step; "
            "or, by hand: File > Import > Timeline, pick `Timeline/" + code + ".fcpxml`; then in the Media Pool select the camera clips, right-click, Relink, and pick the originals' folder.\n"
            "2. Captions: File > Import > Subtitle, pick `Timeline/" + code + ".srt`; it lands on a subtitle track, one cue per sentence.\n"
            "3. `Cut-list.csv` is the same timeline as a table: one row per cut, source and film in and out in seconds and timecode, and a note per AI picture with its planned move (push in or pan), which the server would have applied; apply it or not as you judge.\n"
            "4. AI takes are 720p: Super Scale 2x before the final render. A still shorter than its slot is held on its last frame.\n\n"
            "Nothing is applied for you beyond the cuts: grade, sound, VFX and the end card are yours.\n")
