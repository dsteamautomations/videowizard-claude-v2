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
    m = re.match(r'^(#\d+)\s*\|\s*(.*)$', rows[0]) if rows else None
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


class Renderer:
    def __init__(self, work, timeline):
        self.work = Path(work)
        self.cache = self.work / 'cache'
        self.cache.mkdir(parents=True, exist_ok=True)
        self.tl = timeline
        self.W, self.H, self.fps = int(timeline['width']), int(timeline['height']), Fraction(str(timeline['fps']))

    # ---------- picture ----------

    def video_args(self):
        return ['-c:v', 'libx264', '-profile:v', 'high', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-r', str(self.fps), '-an']

    def slate(self, lines, frames=SLATE_FRAMES):
        key = digest({'slate': lines, 'tl': self.tl, 'frames': frames})
        out = self.cache / f'slate-{key[:16]}.mp4'
        if not out.exists():
            png = self.cache / f'slate-{key[:16]}.png'
            slate_png(lines, self.W, self.H, png)
            run([ffmpeg(), '-y', '-v', 'error', '-loop', '1', '-framerate', str(self.fps), '-i', str(png), '-frames:v', str(frames), *self.video_args(), str(out)])
        return out

    def still(self, png_path, sha, n_tl):
        """A still asset held for n_tl frames, contain-padded to the timeline."""
        key = digest({'still': sha, 'n': n_tl, 'tl': self.tl})
        out = self.cache / f'still-{key[:16]}.mp4'
        if not out.exists():
            run([ffmpeg(), '-y', '-v', 'error', '-loop', '1', '-framerate', str(self.fps), '-i', str(png_path), '-frames:v', str(n_tl),
                 '-vf', f'scale={self.W}:{self.H}:force_original_aspect_ratio=decrease,pad={self.W}:{self.H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p', *self.video_args(), str(out)])
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

    def mix(self, a1, pieces, length_s, out):
        inputs = [a1] + [p for p in pieces if p]
        args = [ffmpeg(), '-y', '-v', 'error']
        for p in inputs:
            args += ['-i', str(p)]
        if len(inputs) == 1:
            run(args + ['-t', f'{length_s:.6f}', '-ar', '48000', '-ac', '2', str(out)])
        else:
            run(args + ['-filter_complex', f'amix=inputs={len(inputs)}:duration=first:normalize=0', '-t', f'{length_s:.6f}', '-ar', '48000', '-ac', '2', str(out)])
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


def review_proxy(film, out, fps):
    run([ffmpeg(), '-y', '-v', 'error', '-i', str(film), '-vf', 'scale=1280:720:flags=bicubic', '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'fast', '-crf', '28',
         '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-r', str(fps),
         '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', str(out)])
    return out


def render_film(kind, plan, sources, narration, work, timeline, narration_plan=None):
    """plan: {'items': [...]} where each item is {'kind': 'slate', 'lines': [...]} or
    {'kind': 'event', 'sub_clip_id', 'clip': {'id','name','sha256','fps','rotation_deg','hdr'}, 'source_in_frame', 'source_out_frame', 'timeline_frames', 'crop_rect', 'hold_last_frame',
     'a2': [{'in_frame','out_frame'}]} and, for the review film, {'kind': 'narration', 'start_s', 'end_s'} markers before each option; the master uses the whole narration.
    sources: {clip_id: Path}. Returns the film path and a record."""
    r = Renderer(work, timeline)
    parts, a2_pieces, a1_parts, normalised = [], [], [], []
    recording = narration
    if narration_plan and narration_plan.get('pieces'):
        narration = timeline_narration(r, recording, narration_plan['pieces'], narration_plan['total_frames'], r.work / 'narration-timeline.wav')
    cursor = Fraction(0)
    silence_before = Fraction(0)
    for i, item in enumerate(plan['items']):
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
            seg = r.still(sources[item['file']['sha256']], item['file']['sha256'], item['timeline_frames'])
            parts.append(seg)
            normalised.append((item, seg))
            cursor += Fraction(item['timeline_frames']) / r.fps
            continue
        else:
            clip = item['clip']
            seg = r.segment(sources[clip['id']], clip['sha256'], clip['fps'], item, item['timeline_frames'], item.get('crop_rect'), clip.get('rotation_deg') or 0.0, bool(clip.get('hdr')),
                            item.get('label'))
            if item.get('stabilize'):
                seg = r.stabilized(seg)
            parts.append(seg)
            if item.get('normalised_key'):
                normalised.append((item, seg))
            for j, iv in enumerate(item.get('a2') or []):
                src_fps = Fraction(str(clip['fps']))
                at = cursor + (Fraction(iv['in_frame'] - item['source_in_frame']) / src_fps)
                a2_pieces.append(r.a2_piece(sources[clip['id']], clip['fps'], iv, float(at), r.work / f'a2-{i}-{j}.wav'))
            cursor += Fraction(item['timeline_frames']) / r.fps
    picture = r.concat(parts, r.work / f'{kind}-picture.mp4')
    length_s = float(cursor)
    gain, a1_measured = a1_gain(r, recording)
    if kind == 'master':
        a1 = r.work / 'a1.wav'
        run([ffmpeg(), '-y', '-v', 'error', '-i', str(narration), '-af', f'volume={gain:.2f}dB,apad', '-t', f'{length_s:.6f}', '-ar', '48000', '-ac', '2', str(a1)])
    else:
        if silence_before:
            a1_parts.append(r.silence(float(silence_before), r.work / 'a1-sil-end.wav'))
        a1 = r.work / 'a1.wav'
        lst = r.work / 'a1.txt'
        lst.write_text(''.join(f"file '{Path(p).as_posix()}'\n" for p in a1_parts), encoding='utf-8')
        run([ffmpeg(), '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-af', f'volume={gain:.2f}dB,apad', '-t', f'{length_s:.6f}', '-ar', '48000', '-ac', '2', str(a1)])
    mixed = r.mix(a1, a2_pieces, length_s, r.work / f'{kind}-mix.wav')
    film = r.mux(picture, mixed, r.work / f'{kind}.mp4')
    codec = 'h264 high yuv420p bt709 / aac 48k stereo'
    if kind == 'review':   # 15 Oct 2026: the full-quality review film was 513 MB and could not be uploaded; it is only for choosing options
        film = review_proxy(film, r.work / 'review-720p.mp4', r.fps)
        codec = 'h264 high yuv420p bt709 1280x720 crf 28 / aac 48k stereo (review copy)'
    master_loudness = r.loudness(film)
    return film, {'duration_s': round(duration_of(film), 3), 'frames': int(cursor * r.fps), 'a1_gain_db': round(gain, 2), 'a1_measured': a1_measured,
                  'a2_pieces': sum(1 for p in a2_pieces if p), 'mix': master_loudness, 'codec': codec,
                  'normalised_segments': [(it.get('normalised_key'), str(seg)) for it, seg in normalised if it.get('normalised_key')]}
