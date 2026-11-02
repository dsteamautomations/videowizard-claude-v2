"""design/142 R5 (SK, 2 Nov 2026, design/140 Q4): the look of each clip, measured by the server: about five frames, averaged for brightness, warmth (red
against blue, read only where the frame has light) and colour strength; clips within LOOK_DISTANCE of a group are that group; log footage is grouped only
with log. Measured in the analysis worker, which already holds the clip; a clip analysed before has no look and never trips R10."""
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

FRAMES = 5
LOOK_DISTANCE = 0.35   # design/142 R5, set on VW-16's 50 clips (2 Nov 2026): one yard, one day, furthest pair 0.34 apart; a night-time look (0.6 away) still splits


def look_of(paths):
    """{'brightness', 'warmth', 'strength'} in 0..1 (warmth -1..1) from pictures; None when no picture can be read."""
    values = []
    for p in paths:
        try:
            rgb = np.asarray(Image.open(p).convert('RGB').resize((96, 54)), dtype=float) / 255.0
        except (OSError, ValueError):
            continue
        light = rgb.mean(axis=2)
        lit = light > 0.15
        r, b = rgb[..., 0], rgb[..., 2]
        warmth = float((r[lit] - b[lit]).mean()) if lit.any() else 0.0
        mx, mn = rgb.max(axis=2), rgb.min(axis=2)
        strength = float(np.where(mx > 0, (mx - mn) / np.where(mx > 0, mx, 1), 0).mean())
        values.append((float(light.mean()), warmth, strength))
    if not values:
        return None
    return {k: round(sum(v[i] for v in values) / len(values), 4) for i, k in enumerate(('brightness', 'warmth', 'strength'))}


def measure(video, duration_s, folder, ffmpeg='ffmpeg', log=False):
    """FRAMES pictures spread over the clip, then their look; a frame that cannot be taken is skipped."""
    folder, paths = Path(folder), []
    duration = float(duration_s or 0)
    for i in range(FRAMES):
        at = duration * (i + 0.5) / FRAMES if duration > 0 else 0
        out = folder / f'look-{i}.png'
        try:
            subprocess.run([ffmpeg, '-y', '-v', 'error', '-ss', f'{at:.3f}', '-i', str(video), '-frames:v', '1', '-vf', 'scale=96:-1', str(out)], check=True, capture_output=True, timeout=60)
            paths.append(out)
        except (subprocess.SubprocessError, OSError):
            continue
    found = look_of(paths)
    return {**found, 'log': bool(log)} if found else None


def _distance(a, b):
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in ('brightness', 'warmth', 'strength')))


def groups(looks):
    """{clip_id: look or None} -> {clip_id: group name or None}: each clip joins the first group (of its own kind, log or not) within LOOK_DISTANCE."""
    out, made = {}, []
    for cid in sorted(looks):
        look = looks[cid]
        if not look:
            out[cid] = None
            continue
        home = next((g for g in made if g['log'] == bool(look.get('log')) and _distance(g['look'], look) <= LOOK_DISTANCE), None)
        if not home:
            home = {'name': f"LOOK_{len(made) + 1}{'_LOG' if look.get('log') else ''}", 'look': look, 'log': bool(look.get('log'))}
            made.append(home)
        out[cid] = home['name']
    return out
