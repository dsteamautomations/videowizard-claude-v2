"""design/112 K1-K4: short gaps are moving stills first. K1: a video or graphic-build shot under 4 s with no visible action is warned unless its
purpose says why it is not a moving still. K2: a still that carries text moves only by push_in. K3: the route counts tell moving and frozen stills
apart. K4: a still that carries text is contained with no crop and never panned; the renderer refuses a pan on it as a backstop."""
import shutil
from fractions import Fraction
from io import BytesIO

import pytest
from PIL import Image

from app import visual_contract as VC, visuals_stage as VS
from app.stage2 import render as R
from test_visuals_pure import GAPS, plan, shot as pshot


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def kinds(d):
    return {(w.get('shot_id'), w.get('kind')) for w in check(d)[1]}


# ---------- K1 ----------

def test_a_short_video_or_build_without_action_is_warned_unless_the_purpose_says_why():
    d = plan([{**pshot('V1', 0, 75, 'video'), 'subjects': []}, pshot('IM1', 75, 1000, 'image')])   # 3 s of AI video, no acting beat
    assert ('V1', 'short_route') in kinds(d)
    w = next(w for w in check(d)[1] if w.get('kind') == 'short_route')
    assert 'moving still' in w['message'] and 'warning_answers' in w['message']   # design/124 Change 7
    d['gaps'][0]['scenes'][0]['shots'][0]['purpose'] = 'the water must be seen running, because a still cannot show the flow'
    assert ('V1', 'short_route') not in kinds(d)
    # a graphic build is never under 4 s (a state holds 3 s at least), so K1 is about AI video
    d = plan([pshot('IM1', 0, 75, 'image'), pshot('IM2', 75, 1000, 'image')])   # a moving still: the default, no warning
    assert ('IM1', 'short_route') not in kinds(d)


# ---------- K2 ----------

def test_a_still_that_carries_text_moves_by_push_in_only():
    d = plan([{**pshot('IM1', 0, 500, 'image'), 'carries_text': True, 'motion': 'pan_left'}, pshot('VS1', 500, 1000, 'video')])
    with pytest.raises(ValueError, match='IM1 carries text .* push_in'):
        check(d)
    d['gaps'][0]['scenes'][0]['shots'][0]['motion'] = 'push_in'
    out, _ = check(d)
    assert out['gaps'][0]['scenes'][0]['shots'][0]['carries_text'] is True
    d = plan([{**pshot('IM1', 0, 500, 'image'), 'motion': 'pan_left'}, pshot('VS1', 500, 1000, 'video')])   # a photograph without words may pan
    check(d)


# ---------- K3 ----------

def test_moving_and_frozen_stills_are_counted_apart():
    d = plan([pshot('IM1', 0, 300, 'image'), {**pshot('IM2', 300, 600, 'image'), 'motion': 'none', 'motion_reason': 'a document'}, pshot('VS1', 600, 1000, 'video')])
    r = VC.routes(check(d)[0])
    assert r['still'] == 2 and r['still_moving'] == 1 and r['still_frozen'] == 1
    rows = VS.split_of(d['gaps'][0]['scenes'][0]['shots'], 25)
    assert [x['route'] for x in rows] == ['AI video', 'still (moving)', 'still (frozen)'] and rows[1]['seconds'] == 12.0 and rows[2]['shots'] == 1


# ---------- K4 ----------

def test_the_handover_marks_a_still_with_text_and_the_renderer_contains_it_and_refuses_a_pan(tmp_path):
    assert VS._still_text({'carries_text': True, 'visual_type': 'image'}, {}) is True
    assert VS._still_text({'visual_type': 'diagram'}, {}) is True
    assert VS._still_text({'visual_type': 'image'}, {'answer': {'exact_text': [{'text': 'NARDEP', 'place': 'L1', 'size_pct': 8}]}}) is True
    assert VS._still_text({'visual_type': 'image'}, {'answer': {'exact_text': []}}) is False
    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg is not on this machine')
    r = R.Renderer(tmp_path, {'width': 320, 'height': 180, 'fps': '25'})
    img = Image.new('RGB', (400, 180), (240, 240, 240))   # a little wider than the frame: a photograph is cropped to fill (within the 1.35 cap)
    p = tmp_path / 'wide.png'
    img.save(p)
    with pytest.raises(ValueError, match='carries text: no pan'):
        r.still(p, 'sha-t', 10, 'pan_left', graphic=False, text=True)
    out = r.still(p, 'sha-t', 10, 'push_in', graphic=False, text=True)
    assert out.exists()
    plain = r.still(p, 'sha-t', 10, 'push_in', graphic=False)
    assert out != plain   # contained with bars, not cropped to fill as the photograph would be
