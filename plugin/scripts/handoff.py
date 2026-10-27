"""design/107 slice 2: handing the film to the editor, on the operator's computer (Windows or Mac).

Step B the Resolve check, Step D the count and cross-check of the downloaded edit, Step E the timeline written with this computer's paths,
Step F the free route's words, Step G the zip. Python 3.9: the operator's laptops run it."""
import hashlib
import platform
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
    assets = {a.get('id'): _path(a.find('media-rep').get('src')) for a in root.findall('./resources/asset')}
    cuts = []
    for c in root.iter('asset-clip'):
        rec_in = Fraction(c.get('offset').rstrip('s')) * fps
        cuts.append({'file': assets[c.get('ref')], 'lane': int(c.get('lane') or 0), 'record_in': int(round(rec_in)), 'record_out': int(round(rec_in + Fraction(c.get('duration').rstrip('s')) * fps))})
    seq = root.find('.//sequence')
    return cuts, int(round(Fraction(seq.get('duration').rstrip('s')) * fps)) if seq is not None else 0


def cross_check(edit_dir, manifest):
    """design/107 Step D: every manifest file present with its size and fingerprint, the voiceover byte-identical, every cut pointing at a present file,
    the timeline's length and cut count equal to the approved film's."""
    edit_dir = Path(edit_dir)
    problems, present = [], 0
    rows = manifest.get('files') or []
    for f in rows:
        p = edit_dir / f['name']
        if not p.exists():
            problems.append(f"{f['name']}: missing")
            continue
        present += 1
        if f.get('bytes') is not None and p.stat().st_size != f['bytes']:
            problems.append(f"{f['name']}: {p.stat().st_size} bytes, the manifest says {f['bytes']}")
        elif f.get('sha256') and sha256_of(p) != f['sha256']:
            problems.append(f"{f['name']}: the fingerprint differs from the manifest's" + (' (the voiceover is not the approved one)' if f['name'].endswith('narration.mp3') else ''))
    out = {'present': f'{present} of {len(rows)} files', 'cuts': 0, 'timeline_frames': 0, 'problems': problems}
    tl = edit_dir / (manifest.get('timeline_file') or f"Timeline/{manifest.get('run')}.fcpxml")
    if not tl.exists():
        problems.append(f'{tl.name}: the timeline file is missing')
        out['ok'] = False
        return out
    cuts, frames = read_timeline(tl.read_bytes().decode('utf-8'), (manifest.get('timeline') or {}).get('fps') or 25)
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
