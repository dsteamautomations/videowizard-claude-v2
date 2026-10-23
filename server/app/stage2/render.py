"""FFmpeg renders for stage 2: the options review film (slates + option events + each beat's narration window + A2 nat sound)
and the master film (events rippled from zero + the continuous narration + A2). Codec spec per design/17: H.264 High, yuv420p, BT.709 tags,
AAC 48 kHz stereo, faststart. Segments are cached by digest so a revise re-renders only what changed."""
import hashlib
import json
import math
import re
import subprocess
from fractions import Fraction
from pathlib import Path

from ..config import settings
from ..errors import Problem
from . import SLATE_FRAMES

A2_PEAK_DBFS = -27.0          # blueprint A2 band −24 to −30 dBFS peak
A1_TARGET_LUFS = -16.0
FADE_FRAMES = 4


def ffmpeg():
    return settings().FFMPEG_EXECUTABLE


def ffprobe():
    return settings().FFPROBE_EXECUTABLE


def run(args, timeout=1800):
    try:
        return subprocess.run(args, check=True, capture_output=True, timeout=timeout)
    except subprocess.CalledProcessError as exc:
        raise Problem(502, 'RENDER', 'ffmpeg failed: ' + exc.stderr.decode(errors='replace')[-600:])
    except (OSError, subprocess.SubprocessError) as exc:
        raise Problem(502, 'RENDER', f'ffmpeg could not run ({exc.__class__.__name__}).')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def duration_of(path):
    out = subprocess.run([ffprobe(), '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)], capture_output=True, check=True, timeout=60).stdout
    return float(json.loads(out)['format']['duration'])


def _font(size):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def slate_png(lines, width, height, path):
    """A black slide. A first line that starts "#NN | ..." shows the number large on its own line (16 Oct: SK missed the small one)."""
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    size = max(12, height // 22)
    rows = [''.join(c if ord(c) < 127 else '?' for c in line) for line in lines]
    m = SLATE_HEAD.match(rows[0]) if rows else None
    head = None
    if m:
        head, rows = m.group(1), [m.group(2)] + rows[1:]
    y = height // 2 - int(((size * 3.2) if head else 0) + size * 0.8 * len(rows))
    if head:
        draw.text((width // 16, y), head, fill=(255, 190, 60), font=_font(size * 2))
        y += int(size * 3.2)
    for text in rows:
        draw.text((width // 16, y), text, fill=(240, 240, 240), font=_font(size))
        y += int(size * 1.6)
    img.save(path, format='PNG')


def label_png(text, height, path):
    """The small corner label on review-film footage, e.g. "#08" or "#11 DECISION"."""
    from PIL import Image, ImageDraw
    size = max(12, height // 20)
    font = _font(size)
    text = ''.join(c if ord(c) < 127 else '?' for c in text)
    w = int(draw_width(text, font)) + size
    img = Image.new('RGBA', (w, int(size * 1.6)), (0, 0, 0, 170))
    ImageDraw.Draw(img).text((size // 2, int(size * 0.25)), text, fill=(255, 190, 60), font=font)
    img.save(path, format='PNG')
    return path


def draw_width(text, font):
    try:
        return font.getlength(text)
    except AttributeError:
        return len(text) * font.size * 0.6


WATCHED_SIZE = {'review': (1280, 720), 'master': (1280, 720)}   # design/43 7.1, design/44 8.3: films watched once and never delivered are made at the size the operator watches
SLATE_HEAD = re.compile(r'^(#\d+[A-Z]*)\s*\|\s*(.*)$')             # "#2 | ..." or "#2B | ...": the label shows large on its own line


DELIVERED = ('master', 'assembly')       # films with the whole narration under them; the assembly film is the delivered one
PEAK_CEILING_DB = -3.0                   # blueprint: −3 dBTP ceiling on the mix (design/46 11.6)
A1_TOLERANCE_LU = 1.5
MOTION_SHARE = 0.05   # design/89 B2 (SK, 23 Oct): a still or a graphic moves 5 % across its shot


def motion_vf(motion, n, W, H, fps, per_frame):
    """zoompan for one move over n frames: push in or out by MOTION_SHARE, or a pan across the margin a 5 % zoom leaves."""
    m = max(int(n) - 1, 1)
    z = 1 + MOTION_SHARE
    zoom = {'push_in': f'1+{MOTION_SHARE}*on/{m}', 'push_out': f'{z}-{MOTION_SHARE}*on/{m}'}.get(motion, f'{z}')
    x = {'pan_left': f'(iw-iw/zoom)*(1-on/{m})', 'pan_right': f'(iw-iw/zoom)*on/{m}'}.get(motion, 'iw/2-(iw/zoom/2)')
    return f"zoompan=z='{zoom}':x='{x}':y='ih/2-(ih/zoom/2)':d={1 if per_frame else int(n)}:s={W}x{H}:fps={fps}"


class Renderer:
    def __init__(self, work, timeline, fast=False, cache=None):
        self.work = Path(work)
        self.cache = Path(cache) if cache else self.work / 'cache'   # design/46 11.7: master and assembly pieces live in a per-run cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.tl = timeline
        self.fast = fast   # review films: a fast preset, the pieces are never delivered
        self.W, self.H, self.fps = int(timeline['width']), int(timeline['height']), Fraction(str(timeline['fps']))

    # ---------- picture ----------

    def video_args(self):
        preset, crf = ('veryfast', '23') if self.fast else ('medium', '18')
        return ['-c:v', 'libx264', '-profile:v', 'high', '-preset', preset, '-crf', crf, '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-r', str(self.fps), '-an']

    def slate(self, lines, frames=SLATE_FRAMES):
        key = digest({'slate': lines, 'tl': self.tl, 'frames': frames})
        out = self.cache / f'slate-{key[:16]}.mp4'
        if not out.exists():
            png = self.cache / f'slate-{key[:16]}.png'
            slate_png(lines, self.W, self.H, png)
            run([ffmpeg(), '-y', '-v', 'error', '-loop', '1', '-framerate', str(self.fps), '-i', str(png), '-frames:v', str(frames), *self.video_args(), str(out)])
        return out

    def still(self, png_path, sha, n_tl, motion='none'):
        """A still asset held for n_tl frames, contain-padded to the timeline; with a motion it moves 5 % (design/89 B2), drawn from a 4× canvas so it does not judder."""
        key = digest({'still': sha, 'n': n_tl, 'tl': self.tl, **({'motion': motion} if motion != 'none' else {})})
        out = self.cache / f'still-{key[:16]}.mp4'
        if not out.exists() and motion != 'none':
            W4, H4 = 4 * self.W, 4 * self.H
            run([ffmpeg(), '-y', '-v', 'error', '-i', str(png_path), '-vf', f'scale={W4}:{H4}:force_original_aspect_ratio=decrease,pad={W4}:{H4}:(ow-iw)/2:(oh-ih)/2,setsar=1,'
                 + motion_vf(motion, n_tl, self.W, self.H, self.fps, False) + ',format=yuv420p', '-frames:v', str(n_tl), *self.video_args(), str(out)])
        if not out.exists():
            run([ffmpeg(), '-y', '-v', 'error', '-loop', '1', '-framerate', str(self.fps), '-i', str(png_path), '-frames:v', str(n_tl),
                 '-vf', f'scale={self.W}:{self.H}:force_original_aspect_ratio=decrease,pad={self.W}:{self.H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p', *self.video_args(), str(out)])
        return out

    def sequence(self, states, dissolve, n_tl, motion='none'):
        """design/65 B8: a graphic sequence; design/89 B2: with a motion, one continuous push across the whole build (never restarting per state)."""
        flat = self._sequence(states, dissolve, n_tl)
        if motion == 'none':
            return flat
        out = self.cache / f"seqm-{digest({'flat': flat.name, 'n': int(n_tl), 'motion': motion, 'tl': self.tl})[:16]}.mp4"
        if not out.exists():
            run([ffmpeg(), '-y', '-v', 'error', '-i', str(flat), '-vf', f'scale={2 * self.W}:{2 * self.H},setsar=1,' + motion_vf(motion, n_tl, self.W, self.H, self.fps, True) + ',format=yuv420p',
                 '-frames:v', str(int(n_tl)), *self.video_args(), str(out)])
        return out

    def _sequence(self, states, dissolve, n_tl):
        """The states one after another with their dissolves, exactly n_tl frames, contain-padded to the timeline."""
        key = digest({'seq': [(sha, int(h)) for _, sha, h in states], 'd': int(dissolve), 'n': int(n_tl), 'tl': self.tl, 'motion': 'none'})
        out = self.cache / f'seq-{key[:16]}.mp4'
        if out.exists():
            return out
        fit = f'scale={self.W}:{self.H}:force_original_aspect_ratio=decrease,pad={self.W}:{self.H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p,setsar=1'
        if len(states) == 1 or dissolve <= 0:   # no join to make: the states one after another
            pieces = [self.still(p, sha, int(h)) for p, sha, h in states]
            return self.concat(pieces, out) if len(pieces) > 1 else pieces[0]
        args, filters, last = [], [], len(states) - 1
        for i, (png, sha, hold) in enumerate(states):
            frames = int(hold) + (int(dissolve) if i < last else 0)   # each state but the last also covers the dissolve into the next
            args += ['-loop', '1', '-framerate', str(self.fps), '-t', f'{frames / float(self.fps):.6f}', '-i', str(png)]
            filters.append(f'[{i}:v]{fit}[v{i}]')
        chain, offset = '[v0]', 0.0
        for i in range(1, len(states)):
            offset += int(states[i - 1][2]) / float(self.fps)   # the dissolve starts when the previous state's hold ends
            label = f'[x{i}]' if i < last else '[out]'
            filters.append(f'{chain}[v{i}]xfade=transition=fade:duration={int(dissolve) / float(self.fps):.6f}:offset={offset:.6f}{label}')
            chain = label
        run([ffmpeg(), '-y', '-v', 'error', *args, '-filter_complex', ';'.join(filters), '-map', '[out]', '-frames:v', str(int(n_tl)), *self.video_args(), str(out)])
        return out

    def stabilized(self, seg):
        """vidstab two-pass on one segment only (design/16): the 1.08 zoom is applied here and counted by the assembly stage."""
        out = seg.with_name(seg.stem + '-stab.mp4')
        if out.exists():
            return out
        trf = seg.with_suffix('.trf')
        run([ffmpeg(), '-y', '-v', 'error', '-i', str(seg), '-vf', f'vidstabdetect=shakiness=5:accuracy=15:result={trf.as_posix()}', '-f', 'null', '-'])
        run([ffmpeg(), '-y', '-v', 'error', '-i', str(seg), '-vf', f'vidstabtransform=input={trf.as_posix()}:zoom=8:smoothing=15:crop=black,unsharp=5:5:0.8:3:3:0.4', *self.video_args(), str(out)])
        return out

    def segment(self, src_path, src_sha, src_fps, ev, n_tl, crop_rect=None, rotation_deg=0.0, hdr=False, label=None):
        """One picture event: source frames [in,out) at src_fps → exactly n_tl timeline frames. hold_last_frame pads with the last frame.
        label: a corner caption burned in (review film only, so the operator knows which numbered slide is playing)."""
        key = digest({'src': src_sha, 'in': ev['source_in_frame'], 'out': ev['source_out_frame'], 'n': n_tl, 'crop': crop_rect, 'rot': rotation_deg, 'hold': bool(ev.get('hold_last_frame')), 'tl': self.tl, 'hdr': hdr,
                      **({'label': label} if label else {})})
        out = self.cache / f'seg-{key[:16]}.mp4'
        if out.exists():
            return out
        src_fps = Fraction(str(src_fps))
        start = Fraction(ev['source_in_frame']) / src_fps
        n_src = ev['source_out_frame'] - ev['source_in_frame']
        filters = []
        if crop_rect:
            x, y, w, h = crop_rect
            filters.append(f'crop=iw*{w}:ih*{h}:iw*{x}:ih*{y}')
        if rotation_deg:
            filters.append(f'rotate={math.radians(rotation_deg)}:c=black')
        if hdr:
            filters.append('zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable,zscale=t=bt709:m=bt709:r=tv,format=yuv420p')
        filters += [f'scale={self.W}:{self.H}:force_original_aspect_ratio=decrease', f'pad={self.W}:{self.H}:(ow-iw)/2:(oh-ih)/2', f'fps={self.fps}']
        if ev.get('hold_last_frame'):
            filters.append(f'tpad=stop_mode=clone:stop_duration={float(n_tl / self.fps) + 1}')
        if label:
            png = label_png(label, self.H, self.cache / f'label-{key[:16]}.png')
            margin = max(8, self.H // 30)
            run([ffmpeg(), '-y', '-v', 'error', '-ss', f'{float(start):.6f}', '-i', str(src_path), '-i', str(png), '-t', f'{float(Fraction(n_src) / src_fps) + 0.5:.6f}',
                 '-filter_complex', f"[0:v]{','.join(filters)}[b];[b][1:v]overlay={margin}:{margin}[o]", '-map', '[o]', '-frames:v', str(n_tl), *self.video_args(), str(out)])
            return out
        run([ffmpeg(), '-y', '-v', 'error', '-ss', f'{float(start):.6f}', '-i', str(src_path), '-t', f'{float(Fraction(n_src) / src_fps) + 0.5:.6f}',
             '-vf', ','.join(filters), '-frames:v', str(n_tl), *self.video_args(), str(out)])
        return out

    def dissolve_pair(self, a, n_a, b, n_b, d):
        """design/71 P4: a cross-fade of d frames from piece a (n_a frames, its last d being the spare tail) into piece b (n_b frames):
        exactly n_a + n_b - d frames, so the timeline length is unchanged."""
        key = digest({'xf': [Path(a).name, Path(b).name], 'na': int(n_a), 'nb': int(n_b), 'd': int(d), 'tl': self.tl})
        out = self.cache / f'xf-{key[:16]}.mp4'
        if out.exists():
            return out
        run([ffmpeg(), '-y', '-v', 'error', '-i', str(a), '-i', str(b), '-filter_complex',
             f'[0:v][1:v]xfade=transition=fade:duration={int(d) / float(self.fps):.6f}:offset={(int(n_a) - int(d)) / float(self.fps):.6f},format=yuv420p[out]',
             '-map', '[out]', '-frames:v', str(int(n_a) + int(n_b) - int(d)), *self.video_args(), str(out)])
        return out

    def concat(self, parts, out):
        lst = out.with_suffix('.txt')
        lst.write_text(''.join(f"file '{Path(p).as_posix()}'\n" for p in parts), encoding='utf-8')
        run([ffmpeg(), '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(out)])
        return out

    # ---------- audio ----------

    def narration_window(self, narration, start_s, end_s, out):
        run([ffmpeg(), '-y', '-v', 'error', '-ss', f'{start_s:.6f}', '-t', f'{max(0.0, end_s - start_s):.6f}', '-i', str(narration), '-ar', '48000', '-ac', '2', str(out)])
        return out

    def silence(self, seconds, out):
        run([ffmpeg(), '-y', '-v', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', f'{seconds:.6f}', str(out)])
        return out

    def peak_dbfs(self, path):
        r = subprocess.run([ffmpeg(), '-i', str(path), '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, timeout=600)
        m = re.search(r'max_volume: (-?[0-9.]+) dB', r.stderr.decode(errors='replace'))
        return float(m.group(1)) if m else None

    def loudness(self, path):
        r = subprocess.run([ffmpeg(), '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, timeout=600)
        txt = r.stderr.decode(errors='replace')
        i = re.findall(r'I:\s+(-?[0-9.]+) LUFS', txt)
        tp = re.findall(r'Peak:\s+(-?[0-9.]+) dBFS', txt)
        return {'integrated_lufs': float(i[-1]) if i else None, 'true_peak_dbfs': float(tp[-1]) if tp else None}

    def a2_piece(self, src_path, src_fps, iv, timeline_at_s, out):
        """One nat-sound interval: cut, 4-frame fades, gain to −27 dBFS peak, placed at timeline_at_s. Returns the piece path or None (silent source)."""
        src_fps = Fraction(str(src_fps))
        start, end = float(Fraction(iv['in_frame']) / src_fps), float(Fraction(iv['out_frame']) / src_fps)
        raw = out.with_name(out.stem + '.raw.wav')
        r = subprocess.run([ffmpeg(), '-y', '-v', 'error', '-ss', f'{start:.6f}', '-t', f'{end - start:.6f}', '-i', str(src_path), '-vn', '-ar', '48000', '-ac', '2', str(raw)], capture_output=True)
        if r.returncode != 0 or not raw.exists():
            return None
        peak = self.peak_dbfs(raw)
        gain = (A2_PEAK_DBFS - peak) if peak is not None else 0.0
        fade = float(FADE_FRAMES / self.fps)
        run([ffmpeg(), '-y', '-v', 'error', '-i', str(raw), '-af', f'volume={gain:.2f}dB,afade=t=in:st=0:d={fade:.4f},afade=t=out:st={max(0.0, end - start - fade):.4f}:d={fade:.4f},adelay={int(timeline_at_s * 1000)}|{int(timeline_at_s * 1000)}', str(out)])
        return out

    def mix(self, a1, pieces, length_s, out, limit=False):
        """A1 plus the A2 pieces; limit=True (design/46 11.6) holds the sample peak at −3 dBFS on a delivered film."""
        inputs = [a1] + [p for p in pieces if p]
        args = [ffmpeg(), '-y', '-v', 'error']
        for p in inputs:
            args += ['-i', str(p)]
        limiter = f'alimiter=limit={10 ** (PEAK_CEILING_DB / 20):.4f}:attack=5:release=50:level=false'
        if len(inputs) == 1:
            run(args + (['-af', limiter] if limit else []) + ['-t', f'{length_s:.6f}', '-ar', '48000', '-ac', '2', str(out)])
        else:
            run(args + ['-filter_complex', f'amix=inputs={len(inputs)}:duration=first:normalize=0' + (',' + limiter if limit else ''), '-t', f'{length_s:.6f}', '-ar', '48000', '-ac', '2', str(out)])
        return out

    def mux(self, picture, audio, out):
        run([ffmpeg(), '-y', '-v', 'error', '-i', str(picture), '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
             '-movflags', '+faststart', '-shortest', str(out)])
        return out


def a1_gain(renderer, narration):
    """design/17 C2: A1 is measured; one gain change only when more than 1 LU from −16, recorded; never re-encoded otherwise."""
    lo = renderer.loudness(narration)
    i = lo.get('integrated_lufs')
    gain = 0.0 if i is None or abs(i - A1_TARGET_LUFS) <= 1.0 else A1_TARGET_LUFS - i
    return gain, lo


def timeline_narration(r, narration, pieces, total_frames, out):
    """design/19 A6: the narration laid on the timeline: each piece cut from the recording at whole frames (sample-exact, PCM),
    silence inserted between pieces where a pause was approved, padded to the timeline length. Words are never altered."""
    fps = r.fps
    parts = []
    cursor = 0
    for j, p in enumerate(pieces):
        if p['timeline_start_frame'] > cursor:
            parts.append(r.silence(float(Fraction(p['timeline_start_frame'] - cursor) / fps), r.work / f'a1-pause-{j}.wav'))
        seg = r.work / f'a1-piece-{j}.wav'
        a, b = Fraction(p['source_start_frame']) / fps, Fraction(p['source_end_frame']) / fps
        run([ffmpeg(), '-y', '-v', 'error', '-i', str(narration), '-af', f'atrim=start={float(a):.6f}:end={float(b):.6f},asetpts=N/SR/TB', '-ar', '48000', '-ac', '2', str(seg)])
        parts.append(seg)
        cursor = p['timeline_start_frame'] + (p['source_end_frame'] - p['source_start_frame'])
    lst = r.work / 'a1-timeline.txt'
    lst.write_text(''.join(f"file '{Path(x).as_posix()}'\n" for x in parts), encoding='utf-8')
    run([ffmpeg(), '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-af', 'apad', '-t', f'{float(Fraction(total_frames) / fps):.6f}', '-ar', '48000', '-ac', '2', str(out)])
    return out


def render_film(kind, plan, sources, narration, work, timeline, narration_plan=None, cache=None):
    """plan: {'items': [...]} where each item is {'kind': 'slate', 'lines': [...]} or
    {'kind': 'event', 'sub_clip_id', 'clip': {'id','name','sha256','fps','rotation_deg','hdr'}, 'source_in_frame', 'source_out_frame', 'timeline_frames', 'crop_rect', 'hold_last_frame',
     'a2': [{'in_frame','out_frame'}]} and, for the review film, {'kind': 'narration', 'start_s', 'end_s'} markers before each option; the master uses the whole narration.
    sources: {clip_id: Path}. Returns the film path and a record.
    Review and master films (design/43 7.1, design/44 8.3) are rendered on a 1280x720 timeline with a fast preset from the first piece,
    no copy pass; the review film also skips the loudness pass, the master keeps it (its sound is the first cut's)."""
    if kind in WATCHED_SIZE:
        timeline = {**timeline, 'width': WATCHED_SIZE[kind][0], 'height': WATCHED_SIZE[kind][1]}
    r = Renderer(work, timeline, fast=kind in WATCHED_SIZE, cache=cache)
    parts, a2_pieces, a1_parts, normalised, looks = [], [], [], [], []
    recording = narration
    if narration_plan and narration_plan.get('pieces'):
        narration = timeline_narration(r, recording, narration_plan['pieces'], narration_plan['total_frames'], r.work / 'narration-timeline.wav')
    cursor = Fraction(0)
    silence_before = Fraction(0)
    carry = None   # design/71 P4: (plain piece, piece with its spare tail, its frames, dissolve frames) waiting for the next take to cross-fade into
    for i, item in enumerate(plan['items']):
        if carry and item['kind'] != 'event':   # nothing to fade into: the plain piece, a cut
            parts.append(carry[0])
            carry = None
        if item['kind'] == 'slate':
            n = int(item.get('frames') or SLATE_FRAMES)
            parts.append(r.slate(item['lines'], n))
            silence_before += Fraction(n) / r.fps
            cursor += Fraction(n) / r.fps
        elif item['kind'] == 'card':   # design/21: a blank inside an option, captioned; the narration window already covers it
            n = int(item['frames'])
            parts.append(r.slate(item['lines'], n))
            cursor += Fraction(n) / r.fps
        elif item['kind'] == 'narration':
            if silence_before:
                a1_parts.append(r.silence(float(silence_before), r.work / f'a1-sil-{i}.wav'))
                silence_before = Fraction(0)
            a1_parts.append(r.narration_window(narration, item['start_s'], item['end_s'], r.work / f'a1-{i}.wav'))
        elif item['kind'] == 'still':
            seg = r.still(sources[item['file']['sha256']], item['file']['sha256'], item['timeline_frames'], item.get('motion') or 'none')
            parts.append(seg)
            looks.append((item.get('label') or 'still', float(cursor), seg, item['timeline_frames'], bool(item.get('graphic'))))
            normalised.append((item, seg))
            cursor += Fraction(item['timeline_frames']) / r.fps
            continue
        elif item['kind'] == 'sequence':   # design/65 B8: a graphic sequence of stills
            seg = r.sequence([(sources[st['file']['sha256']], st['file']['sha256'], st['hold_frames']) for st in item['states']], item.get('dissolve_frames') or 0,
                             item['timeline_frames'], item.get('motion') or 'none')
            parts.append(seg)
            looks.append((item.get('label') or 'sequence', float(cursor), seg, item['timeline_frames'], True))
            normalised.append((item, seg))
            cursor += Fraction(item['timeline_frames']) / r.fps
            continue
        else:
            clip = item['clip']
            seg = r.segment(sources[clip['id']], clip['sha256'], clip['fps'], item, item['timeline_frames'], item.get('crop_rect'), clip.get('rotation_deg') or 0.0, bool(clip.get('hdr')),
                            item.get('label'))
            if item.get('stabilize'):
                seg = r.stabilized(seg)
            looks.append((item.get('label') or item.get('sub_clip_id') or clip['id'], float(cursor), seg, int(item['timeline_frames']), False))
            if item.get('normalised_key'):
                normalised.append((item, seg))   # the delivered piece is the plain take, whatever the join
            n, d = int(item['timeline_frames']), int(item.get('dissolve_into_next') or 0)
            extended, n_ext = None, n + d
            if d > 0:   # design/71 P4: this take also rendered with its spare tail, to fade into the next
                tail = int(Fraction(d) * Fraction(str(clip['fps'])) / r.fps)   # the tail in source frames
                ext = {**item, 'source_out_frame': item['source_out_frame'] + tail}
                extended = r.segment(sources[clip['id']], clip['sha256'], clip['fps'], ext, n_ext, item.get('crop_rect'), clip.get('rotation_deg') or 0.0, bool(clip.get('hdr')))
            if carry:   # the previous take fades into this one over its spare tail
                seg = r.dissolve_pair(carry[1], carry[2], seg, n, carry[3])
                if extended is not None:   # three or more in a row: the join so far, with this take's tail
                    extended, n_ext = r.dissolve_pair(carry[1], carry[2], extended, n_ext, carry[3]), carry[2] + n_ext - carry[3]
                carry = None
            if d > 0:
                carry = (seg, extended, n_ext, d)
            else:
                parts.append(seg)
            for j, iv in enumerate(item.get('a2') or []):
                src_fps = Fraction(str(clip['fps']))
                at = cursor + (Fraction(iv['in_frame'] - item['source_in_frame']) / src_fps)
                a2_pieces.append(r.a2_piece(sources[clip['id']], clip['fps'], iv, float(at), r.work / f'a2-{i}-{j}.wav'))
            cursor += Fraction(item['timeline_frames']) / r.fps
    if carry:
        parts.append(carry[0])
    picture = r.concat(parts, r.work / f'{kind}-picture.mp4')
    look_alike = None
    if kind == 'assembly':   # design/89 H6: before the operator watches, the pieces that look alike, whatever their source
        try:
            from .. import lookalike
            look_alike = lookalike.pairs([{'label': lab, 'at_s': at, 'graphic': g, 'hashes': lookalike.video_hashes(seg, n, g, ffmpeg())} for lab, at, seg, n, g in looks])
        except Exception as exc:   # the check never fails a render
            look_alike = {'error': f'{exc.__class__.__name__}: {str(exc)[:200]}'}
    length_s = float(cursor)
    gain, a1_measured = a1_gain(r, recording)
    if kind in DELIVERED:   # the whole narration, one measured gain (design/46 11.1: the assembly film too, never the small size)
        a1 = r.work / 'a1.wav'
        run([ffmpeg(), '-y', '-v', 'error', '-i', str(narration), '-af', f'volume={gain:.2f}dB,apad', '-t', f'{length_s:.6f}', '-ar', '48000', '-ac', '2', str(a1)])
    else:
        if silence_before:
            a1_parts.append(r.silence(float(silence_before), r.work / 'a1-sil-end.wav'))
        a1 = r.work / 'a1.wav'
        lst = r.work / 'a1.txt'
        lst.write_text(''.join(f"file '{Path(p).as_posix()}'\n" for p in a1_parts), encoding='utf-8')
        run([ffmpeg(), '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-af', f'volume={gain:.2f}dB,apad', '-t', f'{length_s:.6f}', '-ar', '48000', '-ac', '2', str(a1)])
    mixed = r.mix(a1, a2_pieces, length_s, r.work / f'{kind}-mix.wav', limit=kind in DELIVERED)
    film = r.mux(picture, mixed, r.work / f'{kind}.mp4')
    codec = 'h264 high yuv420p bt709 / aac 48k stereo'
    if kind in WATCHED_SIZE:   # before design/43: a 1080p render then a 720p copy, 16 min on VW-3's third review round
        codec = f'h264 high yuv420p bt709 {r.W}x{r.H} veryfast crf 23 / aac 48k stereo ({kind}, made at this size)'
    master_loudness = r.loudness(film) if kind != 'review' else None
    check = None
    if kind in DELIVERED and master_loudness:   # design/46 11.6: the numbers against the targets
        i, tp = master_loudness.get('integrated_lufs'), master_loudness.get('true_peak_dbfs')
        check = {'integrated_lufs': i, 'true_peak_dbfs': tp, 'peak_ceiling_dbtp': int(PEAK_CEILING_DB), 'peak_inside': tp is not None and tp <= PEAK_CEILING_DB + 0.2,
                 'integrated_target_lufs': int(A1_TARGET_LUFS), 'integrated_inside': i is not None and abs(i - A1_TARGET_LUFS) <= A1_TOLERANCE_LU}
    return film, {'duration_s': round(duration_of(film), 3), 'frames': int(cursor * r.fps), 'a1_gain_db': round(gain, 2), 'a1_measured': a1_measured,
                  'a2_pieces': sum(1 for p in a2_pieces if p), 'mix': master_loudness, 'loudness_check': check, 'codec': codec,
                  'normalised_segments': [(it.get('normalised_key'), str(seg)) for it, seg in normalised if it.get('normalised_key')],
                  **({'look_alike': look_alike} if look_alike is not None else {})}
