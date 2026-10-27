"""design/107 slice 2: handing the film to the editor, on the operator's computer (Windows or Mac).

Step B the Resolve check, Step D the count and cross-check of the downloaded edit, Step E the timeline written with this computer's paths,
Step F the free route's words, Step G the zip. Python 3.9: the operator's laptops run it."""
import hashlib
import platform
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote, unquote

REL = 'file://./'
GB = 1024 ** 3


# ---------- Step B: is Resolve here, which one, and is there room ----------

def _windows_entries():
    """(DisplayName, DisplayVersion) of every installed program, from the registry; [] when it cannot be read."""
    out = []
    try:
        import winreg
    except ImportError:
        return out
    roots = [(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'), (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
             (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall')]
    for root, path in roots:
        try:
            with winreg.OpenKey(root, path) as k:
                for i in range(winreg.QueryInfoKey(k)[0]):
                    try:
                        with winreg.OpenKey(k, winreg.EnumKey(k, i)) as sub:
                            name = winreg.QueryValueEx(sub, 'DisplayName')[0]
                            try:
                                version = winreg.QueryValueEx(sub, 'DisplayVersion')[0]
                            except OSError:
                                version = ''
                            out.append((str(name), str(version)))
                    except OSError:
                        continue
        except OSError:
            continue
    return out


def _mac_plist():
    p = Path('/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Info.plist')
    if not p.exists():
        return None
    import plistlib
    with p.open('rb') as f:
        return plistlib.load(f)


def _short(version):
    parts = [p for p in str(version or '').split('.') if p.isdigit()]
    return '.'.join(parts[:3]) if parts else None


def find_resolve(system=None, entries=None, plist=None):
    """{'found', 'version', 'edition'}: edition is 'studio' or 'free'. Windows reads the installed programs; Mac the app's Info.plist."""
    system = system or platform.system()
    none = {'found': False, 'version': None, 'edition': None}
    if system == 'Windows':
        entries = _windows_entries() if entries is None else entries
        hits = [(n, v) for n, v in entries if 'davinci resolve' in n.lower()]
        if not hits:
            return none
        name, version = sorted(hits, key=lambda x: 'studio' in x[0].lower(), reverse=True)[0]   # Studio wins when both are listed
        return {'found': True, 'version': _short(version), 'edition': 'studio' if 'studio' in name.lower() else 'free'}
    if system == 'Darwin':
        plist = _mac_plist() if plist is None else plist
        if not plist:
            return none
        label = (str(plist.get('CFBundleName') or '') + ' ' + str(plist.get('CFBundleIdentifier') or '')).lower()
        return {'found': True, 'version': _short(plist.get('CFBundleShortVersionString')), 'edition': 'studio' if 'studio' in label else 'free'}
    return none


def present_bytes(folder):
    folder = Path(folder)
    return sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()) if folder.exists() else 0


def needed_bytes(bundle_bytes, edit_dir):
    """review 27 Oct: a second download needs only what is not in the edit folder yet."""
    return max(0, int(bundle_bytes or 0) - present_bytes(edit_dir))


def free_bytes(folder):
    folder = Path(folder)
    while not folder.exists() and folder.parent != folder:
        folder = folder.parent
    return shutil.disk_usage(str(folder)).free


def check_words(resolve, needed, free):
    """The answer in plain words (design/107 Step B)."""
    if not resolve.get('found'):
        return 'Resolve not found. Install it, then press the button again.'
    head = f"Resolve {resolve.get('version') or ''} {'Studio' if resolve.get('edition') == 'studio' else '(free)'} found.".replace('  ', ' ')
    sizes = f'{needed / GB:.1f} GB needed, {free / GB:.0f} GB free.'
    if needed > free:
        return f'{head} Not enough disk space: {sizes[:-1]}. Free some space, then press the button again.'
    if resolve.get('edition') == 'free':
        return f'{head} The edit will open by one import step, shown at the end. {sizes}'
    return f'{head} {sizes}'


# ---------- Step D: count and cross-check ----------

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _path(src):
    src = unquote(src)
    return src[len(REL):] if src.startswith(REL) else src[len('file://'):] if src.startswith('file://') else src


def read_timeline(text, fps):
    """The timeline file's connected clips: file, lane, record in/out at the film's rate (kept the same as the server's reader, design/107 slice 1)."""
    fps = Fraction(str(fps))
    root = ET.fromstring(text)
    rates = {f.get('id'): 1 / Fraction(f.get('frameDuration').rstrip('s')) for f in root.findall('./resources/format')}
    assets = {a.get('id'): (_path(a.find('media-rep').get('src')), rates.get(a.get('format'), fps)) for a in root.findall('./resources/asset')}
    cuts = []
    for c in root.iter('asset-clip'):
        path, rate = assets[c.get('ref')]
        rec_in, start = Fraction(c.get('offset').rstrip('s')) * fps, Fraction(c.get('start').rstrip('s'))
        cuts.append({'file': path, 'lane': int(c.get('lane') or 0), 'record_in': int(round(rec_in)), 'record_out': int(round(rec_in + Fraction(c.get('duration').rstrip('s')) * fps)),
                     'source_in': int(round(start * rate)), 'source_out': int(round((start + Fraction(c.get('duration').rstrip('s'))) * rate))})
    seq = root.find('.//sequence')
    return cuts, int(round(Fraction(seq.get('duration').rstrip('s')) * fps)) if seq is not None else 0


def cross_check(edit_dir, manifest):
    """design/107 Step D: every manifest file present with its size and fingerprint, the voiceover byte-identical, every cut pointing at a present file,
    the timeline's length and cut count equal to the approved film's."""
    edit_dir = Path(edit_dir)
    problems, present = [], 0
    rows = manifest.get('files') or []
    tl = edit_dir / (manifest.get('timeline_file') or f"Timeline/{manifest.get('run')}.fcpxml")
    portable = tl.with_name(tl.name.replace('.fcpxml', '.portable.fcpxml'))
    src = portable if portable.exists() else tl   # review 27 Oct: once `download` wrote this computer's paths, the portable copy is what the manifest describes
    for f in rows:
        p = src if edit_dir / f['name'] == tl else edit_dir / f['name']
        if not p.exists():
            problems.append(f"{f['name']}: missing")
            continue
        present += 1
        if f.get('bytes') is not None and p.stat().st_size != f['bytes']:
            problems.append(f"{f['name']}: {p.stat().st_size} bytes, the manifest says {f['bytes']}")
        elif f.get('sha256') and sha256_of(p) != f['sha256']:
            problems.append(f"{f['name']}: the fingerprint differs from the manifest's" + (' (the voiceover is not the approved one)' if f['name'].endswith('narration.mp3') else ''))
    out = {'present': f'{present} of {len(rows)} files', 'cuts': 0, 'timeline_frames': 0, 'problems': problems}
    if not src.exists():
        problems.append(f'{tl.name}: the timeline file is missing')
        out['ok'] = False
        return out
    cuts, frames = read_timeline(src.read_bytes().decode('utf-8'), (manifest.get('timeline') or {}).get('fps') or 25)
    video = [c for c in cuts if c['lane'] == 1]
    out['cuts'], out['timeline_frames'] = len(video), frames
    for i, c in enumerate(video, 1):
        if not (edit_dir / c['file']).exists():
            problems.append(f"cut {i}: {c['file']} is not in the folder")
    want = manifest.get('film_frames')
    if want is not None and frames != want:
        problems.append(f'the timeline is {frames} frames long; the approved film is {want}' + (f" (the first cut that differs: cut {next((i for i, c in enumerate(video, 1) if c['record_out'] > want), len(video))})" if video else ''))
    if manifest.get('cuts') is not None and len(video) != manifest['cuts']:
        problems.append(f"the timeline has {len(video)} cuts; the plan has {manifest['cuts']}")
    out['ok'] = not problems
    return out


# ---------- Step E: this computer's paths ----------

def with_base(text, folder):
    base = str(folder).replace('\\', '/').rstrip('/')
    if base.startswith('//'):   # review 27 Oct: a network share keeps its host: file://nas/share/...
        return text.replace(REL, 'file://' + quote(base[2:], safe='/:') + '/')
    if not base.startswith('/'):
        base = '/' + base
    return text.replace(REL, 'file://' + quote(base, safe='/:') + '/')


def write_timeline_for(edit_dir, manifest, base=None):
    """The portable file kept beside it as VW-n.portable.fcpxml; VW-n.fcpxml gets this computer's absolute paths."""
    edit_dir = Path(edit_dir)
    tl = edit_dir / (manifest.get('timeline_file') or f"Timeline/{manifest.get('run')}.fcpxml")
    portable = tl.with_name(tl.name.replace('.fcpxml', '.portable.fcpxml'))
    text = tl.read_bytes().decode('utf-8')
    if REL in text:
        portable.write_bytes(text.encode('utf-8'))
    else:
        text = portable.read_bytes().decode('utf-8')
    tl.write_bytes(with_base(text, base or str(edit_dir.resolve())).encode('utf-8'))   # bytes: no line-ending change on Windows
    return str(tl)


# ---------- Step F (free Resolve) and Step G ----------

def free_route_text(code):
    return (f"Free Resolve: three steps. 1. Open DaVinci Resolve and make a new project. 2. File > Import > Timeline, and pick Timeline/{code}.fcpxml in runs/{code}/edit/. "
            f"3. Play the start, the middle and the end next to Approved-film.mp4 (also in that folder) and confirm they match. Then `vw delivery confirm --quote \"<the operator's words>\"`.")


def zip_edit(edit_dir, code):
    edit_dir = Path(edit_dir)
    out = edit_dir.parent / f'{code}-edit.zip'
    files = sorted(p for p in edit_dir.rglob('*') if p.is_file())
    files.sort(key=lambda p: p.name != 'OPEN-EDIT.md')   # OPEN-EDIT on top
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, f'{code}-edit/{p.relative_to(edit_dir).as_posix()}')
    return out


# ---------- design/107 §6: the relink check ----------

COPY_ENDINGS = ('_proxy', '_lowres', '_compressed', '_copy', '-1', '(1)', '_1')


def tc_seconds(tc, fps):
    """'14:23:10:05' at fps -> seconds (a Fraction); '' -> 0."""
    if not tc:
        return Fraction(0)
    parts = re.split(r'[:;]', tc.strip())
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        raise ValueError(f'timecode {tc!r} is not hh:mm:ss:ff')   # review 27 Oct: a refusal, not a traceback
    h, m, s, ff = (int(x) for x in parts)
    return Fraction(h * 3600 + m * 60 + s) + Fraction(ff) / Fraction(str(fps))


def _norm_stem(name):
    stem = name.rsplit('.', 1)[0].lower()
    changed = True
    while changed:
        changed = False
        for e in COPY_ENDINGS:
            if stem.endswith(e) and len(stem) > len(e):
                stem, changed = stem[:-len(e)], True
    return stem


def same_rate(a, b):
    """29.970 in the CSV is 30000/1001 from ffprobe: rates agree to three decimals (review 27 Oct)."""
    return abs(float(Fraction(str(a))) - float(Fraction(str(b)))) < 0.002


def probe_original(path):
    """An original read with the media stage's probe: frames, fps, start timecode, width, height."""
    import stages_av
    meta = stages_av.probe(Path(path))
    rate = Fraction(str(meta.get('fps') or 25))
    return {'frames': int(round(float(meta.get('duration_s') or 0) * float(rate))), 'fps': str(rate), 'start_timecode': meta.get('start_timecode') or '', 'width': meta.get('width'), 'height': meta.get('height')}


def grab_frame(src, at_s, out):
    """One frame of the original at at_s, as a PNG for the editor (ffmpeg); None when ffmpeg cannot."""
    import subprocess
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{float(at_s):.3f}', '-i', str(src), '-frames:v', '1', str(out)], check=True, capture_output=True, timeout=60)
        return out
    except (OSError, subprocess.SubprocessError):
        return None


def relink_check(edit_dir, code, rows, originals_dir, probe=None, grab=None):
    """Each camera file against the originals folder: match, renamed (extension or a copy ending), timecode (a corrected timeline is written), by_hand (trimmed or
    another frame rate: its cuts listed with the time inside the copy and a frame grab), ask (two originals fit: nothing written), missing."""
    probe, grab = probe or probe_original, grab or grab_frame
    edit_dir, originals_dir = Path(edit_dir), Path(originals_dir)
    portable = edit_dir / 'Timeline' / f'{code}.portable.fcpxml'
    text = portable.read_bytes().decode('utf-8')
    cuts = [c for c in read_timeline(text, 25)[0] if c['lane'] == 1]
    by_file = {}
    for i, c in enumerate(cuts, 1):
        by_file.setdefault(c['file'].rsplit('/', 1)[-1].lower(), []).append((i, c))
    files = [p for p in originals_dir.rglob('*') if p.is_file()]
    lines, checklist, relink, asking = [], [], {}, False
    for row in rows:
        name, fps = row['name'], Fraction(str(row.get('fps') or 25))
        frames = int(float(row.get('frames') or 0))
        mine = by_file.get(name.lower(), [])
        exact = [p for p in files if p.name.lower() == name.lower()]
        cands = exact or [p for p in files if _norm_stem(p.name) == _norm_stem(name)]
        line = {'copy': name, 'cuts': [i for i, _ in mine]}
        if not cands:
            lines.append({**line, 'outcome': 'missing', 'line': f'{name}: no original with this name. Look for a renamed file. Cuts: {", ".join(str(i) for i, _ in mine) or "none"}.'})
            continue
        probed = {p: probe(p) for p in cands}
        agree = lambda p: probed[p]['frames'] == frames and same_rate(probed[p]['fps'], fps) and (not row.get('start_timecode') or probed[p]['start_timecode'] == row['start_timecode'])
        confirmed = [p for p in cands if agree(p)]
        if len(cands) > 1 and len(confirmed) != 1:
            asking = True
            lines.append({**line, 'outcome': 'ask', 'candidates': [p.name for p in cands], 'line': f"{name}: {len(cands)} originals fit this name ({', '.join(p.name for p in cands)}); pick one. Nothing is written until then."})
            continue
        p = confirmed[0] if confirmed else cands[0]
        o = probed[p]
        if o['frames'] != frames or not same_rate(o['fps'], fps):
            diff = o['frames'] - frames
            why = (f"the copy is {abs(diff)} frames {'shorter' if diff > 0 else 'longer'} than the original" if same_rate(o['fps'], fps)
                   else f"the frame rate differs: the copy {float(fps):g}, the original {float(Fraction(str(o['fps']))):g}")
            grabs = []
            for i, c in mine:
                at = float(Fraction(c['source_in']) / fps)
                out = f'Timeline/grabs/{name}-cut{i}.png'
                grab(p, at, edit_dir / out)
                grabs.append({'cut': i, 'at_s': at, 'grab': out})
            lines.append({**line, 'outcome': 'by_hand', 'original': p.name, 'cuts': grabs, 'line': f'{name}: {why}. This clip must be lined up by hand (cuts listed below).'})
            checklist.append(f"{name} → {p.name}: {why}; line up cut{'s' if len(grabs) != 1 else ''} {', '.join(str(g['cut']) for g in grabs)} by hand ({'; '.join(f'{g[chr(97)+chr(116)+chr(95)+chr(115)]:.1f} s' for g in grabs)} into the copy; grab in Timeline/grabs/)".replace("f'{g[chr(97)+chr(116)+chr(95)+chr(115)]:.1f} s'", ''))
            continue
        offset = tc_seconds(o['start_timecode'], fps) - tc_seconds(row.get('start_timecode'), fps)
        if offset:
            lines.append({**line, 'outcome': 'timecode', 'original': p.name, 'line': f"{name}: the copy has {'no timecode' if not row.get('start_timecode') else 'timecode ' + row['start_timecode']}; the original starts at {o['start_timecode']}. A corrected timeline is written."})
            relink[name.lower()] = (p, offset)
        elif p.name != name:
            lines.append({**line, 'outcome': 'renamed', 'original': p.name, 'line': f'copy {name} = original {p.name} (length, frame rate, timecode agree). The relinked timeline points at it.'})
            relink[name.lower()] = (p, Fraction(0))
        else:
            lines.append({**line, 'outcome': 'match', 'original': p.name, 'line': f'{name}: name, length, frame rate and timecode match. Relinks as is.'})
    relinked = None
    if relink and not asking:
        relinked = edit_dir / 'Timeline' / f'{code}-relinked.fcpxml'
        relinked.write_bytes(_relinked(text, relink).encode('utf-8'))
    return {'lines': lines, 'checklist': checklist, 'relinked': str(relinked) if relinked else None}


def _relinked(text, relink):
    """The portable timeline with each relinked asset pointing at the original's real path and its cuts moved by the timecode offset."""
    root = ET.fromstring(text)
    shift = {}
    for a in root.findall('./resources/asset'):
        rep = a.find('media-rep')
        name = _path(rep.get('src')).rsplit('/', 1)[-1].lower()
        if name in relink:
            p, offset = relink[name]
            base = str(p.resolve()).replace('\\', '/')
            rep.set('src', 'file://' + quote(base if base.startswith('/') else '/' + base, safe='/:'))
            a.set('start', f'{offset.numerator}/{offset.denominator}s' if offset.denominator != 1 else f'{offset.numerator}s')
            shift[a.get('id')] = offset
    for c in root.iter('asset-clip'):
        off = shift.get(c.get('ref'))
        if off:
            start = Fraction(c.get('start').rstrip('s')) + off
            c.set('start', f'{start.numerator}/{start.denominator}s' if start.denominator != 1 else f'{start.numerator}s')
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + ET.tostring(root, encoding='unicode')


def compare(cuts, events, narration_pieces):
    """The readback against the plan, cut by cut (design/17 A47, 0 frames); [] when they agree. The same rule as the server's differences()."""
    out = []
    plan = [(1, [c for c in cuts if c['lane'] == 1], [{'file': e['file'], 'record_in': e['record_in_frame'], 'record_out': e['record_out_frame'], 'source_in': e['source_in_frame'], 'source_out': e['source_out_frame']} for e in events]),
            (-1, [c for c in cuts if c['lane'] == -1], [{'file': p.get('file') or 'Media/Voiceover/narration.mp3', 'record_in': p['record_in_frame'], 'record_out': p['record_in_frame'] + p['source_out_frame'] - p['source_in_frame'],
                                                         'source_in': p['source_in_frame'], 'source_out': p['source_out_frame']} for p in narration_pieces or []])]
    for lane, got, want in plan:
        for i, (g, w) in enumerate(zip(got, want), 1):
            for k in ('file', 'record_in', 'record_out', 'source_in', 'source_out'):
                if (not g['file'].replace('\\', '/').endswith(w['file'])) if k == 'file' else g.get(k) != w[k]:
                    out.append({'cut': i if lane == 1 else f'voiceover {i}', 'file': w['file'], 'field': k, 'timeline': g.get(k), 'plan': w[k]})
        if len(got) != len(want):
            out.append({'cut': None, 'file': 'voiceover' if lane == -1 else 'video', 'field': 'count', 'timeline': len(got), 'plan': len(want)})
    return out
