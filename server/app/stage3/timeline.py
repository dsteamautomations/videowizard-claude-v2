"""design/107: the edit as a timeline file (FCPXML 1.9) any editor can import into Resolve, free or Studio, with our own reader for the checks;
the same cuts as an EDL; and Relink-list.csv, one line per camera file, for relinking to the full-quality originals.

The FCPXML holds no picture: every cut says "this file, from this frame to this frame, at this place in the film". Paths are folder-relative
(`file://./Media/...`); the plugin rewrites the base with the computer's real path (with_base) after the download."""
import csv
import io
import xml.etree.ElementTree as ET
from fractions import Fraction
from urllib.parse import quote, unquote

REL = 'file://./'
REFERENCE = 'REFERENCE – approved film'


def _t(frac):
    """A time as FCPXML writes it: whole seconds as '3s', else 'num/dens'."""
    frac = Fraction(frac)
    return f'{frac.numerator}s' if frac.denominator == 1 else f'{frac.numerator}/{frac.denominator}s'


def _frac(text):
    return Fraction(text.rstrip('s'))


def _url(path):
    return REL + quote(path, safe='/')


def _path(src):
    src = unquote(src)
    return src[len(REL):] if src.startswith(REL) else src[len('file://'):] if src.startswith('file://') else src


def fcpxml(code, tl, events, narration_pieces, finishing, sfx_cues, film_frames):
    """design/107 §5. events: delivery.resolve_events rows (file, kind, source/record frames, source_fps, zoom, pan, tilt, rotation, colour group, marker, a2).
    One gap the length of the film is the primary story; every cut, the voiceover (lane -1), the nat sound (lane -2) and the switched-off reference track
    (lane 2) connect to it, so every offset is a film time."""
    fps = Fraction(str(tl['fps']))
    root = ET.Element('fcpxml', version='1.9')
    res = ET.SubElement(root, 'resources')
    formats = {}

    def fmt(rate):
        rate = Fraction(str(rate))
        if rate not in formats:
            fid = f'r{len(formats) + 1}'
            ET.SubElement(res, 'format', id=fid, name=f"FFVideoFormat{tl['height']}p{float(rate):g}", frameDuration=_t(1 / rate), width=str(tl['width']), height=str(tl['height']))
            formats[rate] = fid
        return formats[rate]
    main = fmt(fps)
    assets = {}

    def asset(path, kind, rate, frames_=None):
        if path not in assets:
            aid = f'a{len(assets) + 1}'
            rate = Fraction(str(rate))
            dur = Fraction(frames_) / rate if frames_ else None
            a = ET.SubElement(res, 'asset', id=aid, name=path.rsplit('/', 1)[-1], start='0s', duration=_t(dur) if dur else '0s',
                              hasVideo='1' if kind in ('camera', 'movie', 'still', 'reference') else '0', hasAudio='1' if kind in ('camera', 'movie', 'reference', 'audio') else '0')
            if kind != 'audio':
                a.set('format', fmt(rate))
            ET.SubElement(a, 'media-rep', kind='original-media', src=_url(path))
            assets[path] = (aid, a)
        return assets[path][0]
    lib = ET.SubElement(root, 'library')
    event = ET.SubElement(lib, 'event', name=code)
    project = ET.SubElement(event, 'project', name=code)
    seq = ET.SubElement(project, 'sequence', format=main, duration=_t(Fraction(film_frames) / fps), tcStart='0s', tcFormat='NDF')
    spine = ET.SubElement(seq, 'spine')
    gap = ET.SubElement(spine, 'gap', name='Film', offset='0s', start='0s', duration=_t(Fraction(film_frames) / fps))
    by_cut = {}
    for e in events:
        src_fps = Fraction(str(e.get('source_fps') or fps))
        frames_ = e.get('source_frames') or (e['source_out_frame'] if e.get('kind') != 'still' else e['source_out_frame'])
        aid = asset(e['file'], e.get('kind', 'camera'), src_fps, frames_)
        rec_in, rec_out = Fraction(e['record_in_frame']) / fps, Fraction(e['record_out_frame']) / fps
        clip = ET.SubElement(gap, 'asset-clip', ref=aid, lane='1', offset=_t(rec_in), name=e['marker']['name'], start=_t(Fraction(e['source_in_frame']) / src_fps),
                             duration=_t(rec_out - rec_in), format=fmt(src_fps), enabled='1')
        by_cut[e['marker']['name']] = e
        z, pan, tilt, rot = float(e.get('zoom') or 1.0), float(e.get('pan') or 0.0), float(e.get('tilt') or 0.0), float(e.get('rotation') or 0.0)
        if z != 1.0 or pan or tilt or rot:
            ET.SubElement(clip, 'adjust-transform', scale=f'{z:g} {z:g}', position=f'{pan:g} {tilt:g}', rotation=f'{rot:g}')
        note = e['marker'].get('note') or ''
        if e.get('color_group'):
            note += f"; colour group {e['color_group']}"
        ET.SubElement(clip, 'marker', start=_t(Fraction(e['source_in_frame']) / src_fps), duration=_t(1 / fps), value=e['marker']['name'], note=note)
        for iv in e.get('a2') or []:   # the nat sound of this cut, in its place
            at = rec_in + Fraction(iv['in_frame'] - e['source_in_frame']) / src_fps
            ET.SubElement(gap, 'asset-clip', ref=aid, lane='-2', offset=_t(at), name=f"{e['marker']['name']} nat sound", start=_t(Fraction(iv['in_frame']) / src_fps),
                          duration=_t(Fraction(iv['out_frame'] - iv['in_frame']) / src_fps), role='effects.nat-sound', enabled='1')
    for p in narration_pieces or []:
        aid = asset(p.get('file') or 'Media/Voiceover/narration.mp3', 'audio', fps, p['source_out_frame'])
        ET.SubElement(gap, 'asset-clip', ref=aid, lane='-1', offset=_t(Fraction(p['record_in_frame']) / fps), name='Voiceover', start=_t(Fraction(p['source_in_frame']) / fps),
                      duration=_t(Fraction(p['source_out_frame'] - p['source_in_frame']) / fps), role='dialogue.voiceover', enabled='1')
    ref = asset('Approved-film.mp4', 'reference', fps, film_frames)
    ET.SubElement(gap, 'asset-clip', ref=ref, lane='2', offset='0s', name=REFERENCE, start='0s', duration=_t(Fraction(film_frames) / fps), format=main, enabled='0')
    for item in finishing or []:
        ET.SubElement(gap, 'marker', start=_t(Fraction(int(item.get('timeline_in_frame') or 0)) / fps), duration=_t(1 / fps), value=str(item.get('item') or '')[:200], note='finishing')
    for c in sfx_cues or []:
        e = by_cut.get(c.get('sub_clip_id'))
        at = Fraction(e['record_in_frame']) / fps if e else Fraction(0)
        ET.SubElement(gap, 'marker', start=_t(at), duration=_t(1 / fps), value=f"SFX {c.get('sfx_type') or ''}".strip(),
                      note=(f"{c.get('description') or ''}" + (f" (clip time {c['start_tc']})" if c.get('start_tc') else '')).strip())
    ET.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + ET.tostring(root, encoding='unicode')


def read_fcpxml(text, fps):
    """Our reader: every connected clip as (file, lane, record in/out at the timeline's fps, source in/out at the file's own fps)."""
    fps = Fraction(str(fps))
    root = ET.fromstring(text)
    rates = {f.get('id'): 1 / _frac(f.get('frameDuration')) for f in root.findall('./resources/format')}
    assets = {a.get('id'): (_path(a.find('media-rep').get('src')), rates.get(a.get('format'), fps)) for a in root.findall('./resources/asset')}
    out = []
    for c in root.iter('asset-clip'):
        path, rate = assets[c.get('ref')]
        rec_in = _frac(c.get('offset')) * fps
        out.append({'file': path, 'lane': int(c.get('lane') or 0), 'name': c.get('name'), 'enabled': c.get('enabled', '1') == '1',
                    'record_in': int(round(rec_in)), 'record_out': int(round(rec_in + _frac(c.get('duration')) * fps)),
                    'source_in': int(round(_frac(c.get('start')) * rate)), 'source_out': int(round((_frac(c.get('start')) + _frac(c.get('duration'))) * rate))})
    return out


def timeline_frames(cuts):
    return max((c['record_out'] for c in cuts if c['lane'] == 1), default=0)


def differences(cuts, events, narration_pieces):
    """The timeline against the plan, cut by cut (design/17 A47: tolerance 0 frames); [] when they agree."""
    out = []
    pairs = [(1, [c for c in cuts if c['lane'] == 1], [{'file': e['file'], 'record_in': e['record_in_frame'], 'record_out': e['record_out_frame'], 'source_in': e['source_in_frame'], 'source_out': e['source_out_frame']} for e in events]),
             (-1, [c for c in cuts if c['lane'] == -1], [{'file': p.get('file') or 'Media/Voiceover/narration.mp3', 'record_in': p['record_in_frame'], 'record_out': p['record_in_frame'] + p['source_out_frame'] - p['source_in_frame'],
                                                           'source_in': p['source_in_frame'], 'source_out': p['source_out_frame']} for p in narration_pieces or []])]
    for lane, got, want in pairs:
        for i, (g, w) in enumerate(zip(got, want), 1):
            for k in ('file', 'record_in', 'record_out', 'source_in', 'source_out'):
                if (g[k] != w[k]) if k != 'file' else not g['file'].endswith(w['file']):
                    out.append({'cut': i if lane == 1 else f'voiceover {i}', 'file': w['file'], 'field': k, 'timeline': g[k], 'plan': w[k]})
        if len(got) != len(want):
            out.append({'cut': None, 'file': 'voiceover' if lane == -1 else 'video', 'field': 'count', 'timeline': len(got), 'plan': len(want)})
    return out


def with_base(text, folder):
    """design/107 Step E: the folder-relative paths become this computer's (Windows drive letters and Mac paths, spaces and other scripts encoded)."""
    base = str(folder).replace('\\', '/').rstrip('/')
    if not base.startswith('/'):
        base = '/' + base
    return text.replace(REL, 'file://' + quote(base, safe='/:') + '/')


# ---------- the EDL ----------

def tc(frames, fps):
    fps = Fraction(str(fps))
    total = Fraction(frames) / fps
    whole = int(total)
    ff = int((total - whole) * fps)
    return f'{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d}:{ff:02d}'


def edl(code, tl, events):
    """CMX 3600: the same cuts as a plain list, source and record timecodes at the timeline's rate."""
    fps = Fraction(str(tl['fps']))
    lines = [f'TITLE: {code}', 'FCM: NON-DROP FRAME', '']
    for n, e in enumerate(events, 1):
        src_fps = Fraction(str(e.get('source_fps') or fps))
        s_in, s_out = Fraction(e['source_in_frame']) / src_fps * fps, Fraction(e['source_out_frame']) / src_fps * fps   # source time at the timeline's rate
        lines.append(f"{n:03d}  AX       V     C        {tc(s_in, fps)} {tc(s_out, fps)} {tc(e['record_in_frame'], fps)} {tc(e['record_out_frame'], fps)}")
        lines.append(f"* FROM CLIP NAME: {e['file'].rsplit('/', 1)[-1]}")
        lines.append('')
    return '\n'.join(lines)


# ---------- Relink-list.csv ----------

RELINK_COLUMNS = ['name', 'stem', 'extension', 'frames', 'fps', 'width', 'height', 'duration_s', 'start_timecode', 'reel', 'original_name', 'sha256', 'bytes', 'cuts']


def _rate(text):
    r = Fraction(str(text or 25))
    return str(r.numerator) if r.denominator == 1 else f'{float(r):.3f}'


def relink_csv(clips, used_ids, cuts_per_clip):
    """design/107 §6: one line per camera file the film uses, with what Resolve matches on and what the relink check compares."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=RELINK_COLUMNS, lineterminator='\n')
    w.writeheader()
    for c in clips:
        if c['id'] not in used_ids:
            continue
        name = c['name']
        stem, dot, ext = name.rpartition('.')
        rate = Fraction(str(c.get('fps') or 25))
        w.writerow({'name': name, 'stem': stem if dot else name, 'extension': ('.' + ext) if dot else '', 'frames': int(round(float(c.get('duration_s') or 0) * float(rate))),
                    'fps': _rate(rate), 'width': c.get('width') or '', 'height': c.get('height') or '', 'duration_s': c.get('duration_s') or '',
                    'start_timecode': c.get('start_timecode') or '', 'reel': c.get('reel') or '', 'original_name': c.get('original_name') or '',
                    'sha256': c.get('sha256') or '', 'bytes': c.get('bytes') or '', 'cuts': cuts_per_clip.get(c['id'], 0)})
    return buf.getvalue()
