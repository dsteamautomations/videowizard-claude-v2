"""design/112 S2 and S5. S2: every end image is an edit inside one region of its start (F11's mask and composite-back), so nothing outside the
action area moves; an end without a region is refused naming the change to cover; a start written with an end prompt and no end region is warned.
S5: every retained take is measured for drift in code (frame-to-frame registration against the first frame); a locked-off take that drifts or zooms
over 2 % fails the 'camera drift' must line with the figure; a take with a planned camera move is reported, not judged."""
import shutil
import subprocess
import types
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from app import image_check as IC, visuals_stage as VS
from app.errors import Problem
from test_design106_pure import approvable, revise_start, start_store
from test_design111_f11_pure import REGION, put
from test_design112_s1s3s4_pure import texture
from test_visuals_stage_pure import RUN, USER, FakeConn, g, saved


# ---------- S2 ----------

def test_an_end_without_a_region_is_refused_naming_the_change_and_a_start_without_an_end_region_is_warned():
    store = start_store()
    out = revise_start(store, role='start', end_region=None)
    assert any('--end-region' in w for w in out.get('warnings') or [])   # the end written with it will be refused without a region
    rid = out['reference_id']
    s = saved(approvable(store, rid))
    s['references'][rid]['status'] = 'approved'
    put(store, s)
    body = {'request_id': 'q-e', 'element_id': 'E1', 'name': 'keyframe-end-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer', 'prompt': 'Image 1 is the start; the labourer at the edge.',
            'parents': [rid], 'role': 'end'}
    with pytest.raises(Problem, match='An end image is an edit inside one region of its start: give --region') as exc:
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], body))
    assert '--region' in exc.value.message and 'start-only' in exc.value.message
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'region': REGION})
    assert saved(store)['references'][out['reference_id']]['generation']['region'] == REGION
    assert not any('--end-region' in w for w in revise_start(store, role='start', request_id='q-s-ok').get('warnings') or [])   # the shared fixture gives one


# ---------- S5 ----------

def frames_drifting(n=10, total_shift=0.03, zoom=1.0):
    base = texture(size=(512, 288))
    out = []
    for i in range(n):
        dx = round(512 * total_shift * i / (n - 1))
        f = Image.new('RGB', base.size)
        f.paste(base, (dx, 0))
        if zoom != 1.0 and i == n - 1:
            w, h = f.size
            f = f.resize((round(w * zoom), round(h * zoom))).crop((round(w * (zoom - 1) / 2), round(h * (zoom - 1) / 2), round(w * (zoom - 1) / 2) + w, round(h * (zoom - 1) / 2) + h))
        out.append(f.convert('L').resize((IC.ALIGN_W, IC.ALIGN_H)))
    return out


def frames_steady(n=10):
    base = texture(size=(512, 288))
    out = []
    for i in range(n):
        f = base.copy()
        ImageDraw.Draw(f).rectangle((100 + 20 * i, 120, 160 + 20 * i, 170), fill=(200, 40, 40))   # a subject moves; the frame does not
        out.append(f.convert('L').resize((IC.ALIGN_W, IC.ALIGN_H)))
    return out


def test_a_locked_off_take_that_drifts_fails_with_the_figure_a_steady_one_passes_a_planned_move_is_reported_only():
    d = IC.take_drift(None, {'camera_move': ''}, frames=frames_drifting())
    assert d['check'] == 'camera drift' and d['weight'] == 'must' and d['pass'] is False and 2.5 <= d['drift_pct'] <= 3.6 and 'drift up to' in d['seen']
    d = IC.take_drift(None, {'camera_move': ''}, frames=frames_drifting(total_shift=0.0, zoom=1.04))
    assert d['pass'] is False and d['zoom_pct'] >= 3.0
    d = IC.take_drift(None, {'camera_move': ''}, frames=frames_steady())
    assert d['pass'] is True and d['drift_pct'] <= 1.0
    d = IC.take_drift(None, {'camera_move': 'a slow push in'}, frames=frames_drifting())
    assert d['pass'] is None and d['weight'] == 'should' and 'planned' in d['seen']
    d = IC.take_drift(None, {}, frames=frames_drifting())   # a take prepared before design/112: measured, not judged
    assert d['pass'] is None
    assert IC.take_drift(None, {'camera_move': ''}, frames=frames_steady(1)) is None


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg is not on this machine')
def test_the_frames_are_read_from_the_video_with_ffmpeg(tmp_path):
    for i, f in enumerate(frames_drifting(n=10)):
        f.convert('RGB').resize((512, 288)).save(tmp_path / f'f{i:03d}.png')
    video = tmp_path / 'take.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '5', '-i', str(tmp_path / 'f%03d.png'), '-pix_fmt', 'yuv420p', str(video)], check=True, timeout=120)
    frames = IC._frames(video)
    assert 2 <= len(frames) <= 12 and frames[0].size == (IC.ALIGN_W, IC.ALIGN_H)
    d = IC.take_drift(video, {'camera_move': ''})
    assert d['pass'] is False and d['drift_pct'] >= 2.0


def test_the_take_check_carries_the_drift_line_even_when_gemini_cannot_run(monkeypatch):
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: '')))
    monkeypatch.setattr(IC, '_frames', lambda path: frames_drifting())
    rec = IC.run_take_check({'motion_prompt': 'm', 'camera_move': ''}, Path('no-such.mp4'), 'a' * 64, None)
    assert rec['error'] == 'no Gemini key on the server' and rec['lines'][-1]['check'] == 'camera drift' and rec['must_failed'] == [rec['lines'][-1]]
    monkeypatch.setattr(IC, '_frames', lambda path: (_ for _ in ()).throw(OSError('no ffmpeg')))
    rec = IC.run_take_check({'motion_prompt': 'm', 'camera_move': ''}, Path('no-such.mp4'), 'a' * 64, None)
    assert rec['lines'] == [] and 'drift_error' in rec   # the take is never held back by its measurement
