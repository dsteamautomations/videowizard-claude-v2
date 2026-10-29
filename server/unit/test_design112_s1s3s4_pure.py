"""design/112 S1, S4, S3. S1: a take is made from the start image alone unless the shot says its final state must be exact (end_state_exact);
the plan check warns when a shot with a change list is left start-only. S4: the motion text always states the camera, locked off unless the shot
names a move, and the take check asks for it. S3: when a pair is used, the end's alignment with the start is measured in code (numpy phase
correlation, a small scale search); a shifted or zoomed pair is refused with the figure."""
import json
from fractions import Fraction
from io import BytesIO

import numpy as np
import pytest
from PIL import Image, ImageDraw

from app import image_check as IC, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from app.video_providers import motion_text
from test_visuals_pure import GAPS, plan, shot as pshot
from test_visuals_stage_pure import RUN, USER, accepted, g, gap_digest, plan_doc, ref, saved, session, shot, store_with


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


# ---------- S1 ----------

def test_a_shot_with_changes_and_no_exact_end_is_warned_and_the_estimate_counts_a_start_only():
    d = plan([pshot('V1', 0, 250, 'video'), pshot('V2', 250, 500, 'video'), pshot('V3', 500, 750, 'video'), pshot('IM1', 750, 1000, 'image')])
    out, warnings = check(d)
    assert ('V1', 'end_state') not in {(w.get('shot_id'), w.get('kind')) for w in warnings}   # no change list: nothing to be exact about
    assert VC.routes(out)['images_estimated'] == 3 + 1   # three starts, one still
    d['gaps'][0]['scenes'][0]['shots'][0]['end_state_exact'] = True
    assert VC.routes(check(d)[0])['images_estimated'] == 2 + 0 + 1 + 1   # V1 start and end; V2 starts on V1's end; V3 its own start; the still
    sh = d['gaps'][0]['scenes'][0]['shots'][1]
    sh['changes'] = [{'what': 'the brick is down', 'beat_id': sh['subjects'][0]['beats'][0]['id']}] if sh.get('subjects') and sh['subjects'][0].get('beats') else []
    if sh['changes']:
        _, warnings = check(d)
        w = next(w for w in warnings if w.get('shot_id') == 'V2' and w.get('kind') == 'end_state')
        assert 'start image alone' in w['message'] and 'end_state_exact' in w['message']


def prepared(exact, end=True):
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [{**shot('VS1', 900, 1150, 'video', subjects=[]), 'end_state_exact': exact}])
    plan_, gap = doc, doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', 'approved')},
                   bindings={'VS1': {'gap_digest': gap_digest(plan_, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}, 'packet_read_at': 't'}})
    store = store_with(sess, doc)
    body = {'shot_id': 'VS1', 'motion_prompt': 'water poured along the top', 'subject_reconciliation': {}, 'start_image': 'R1', 'continuity_notes': 'the wall and the yard light stay',
            **({'end_image': 'R2'} if end else {})}
    return store, body


def test_a_take_from_the_start_alone_is_accepted_unless_the_shot_needs_an_exact_end():
    store, body = prepared(exact=False, end=False)
    out = VS.prepare_take(store, USER, RUN, [], body)
    rec = json.loads(store.files[saved(store)['preparations']['VS1']['key']])
    assert 'end_image' not in rec and rec['start_image']['reference_id'] == 'R1' and saved(store)['preparations']['VS1']['end_image'] is None
    assert rec['effective_prompt'].startswith('[# Sources <FIRST_FRAME>@Image1]') and 'Camera: locked off on a tripod' in rec['effective_prompt']   # S4
    assert rec['camera_move'] == ''
    store, body = prepared(exact=True, end=False)
    with pytest.raises(Problem, match='final state must be exact \\(end_state_exact\\)'):
        g(lambda: VS.prepare_take(store, USER, RUN, [], body))


# ---------- S4 ----------

def test_the_camera_is_always_stated_and_the_take_check_asks_for_it():
    snap = {'motion_prompt': 'm', 'subject_reconciliation': {}, 'duration_seconds': 5, 'end_image': None}
    assert 'Camera:' not in motion_text(snap)   # a take prepared before design/112: nothing added
    assert 'Camera: locked off on a tripod; the frame does not move, drift, zoom or slide.' in motion_text({**snap, 'camera_move': ''})
    assert 'Camera: a slow push in toward the sill; nothing else about the frame changes.' in motion_text({**snap, 'camera_move': 'a slow push in toward the sill'})
    assert IC.CAMERA_STEADY['weight'] == 'must' and IC.take_lines_for({'camera_move': ''})[-1] is IC.CAMERA_STEADY
    assert IC.CAMERA_STEADY not in IC.take_lines_for({'camera_move': 'a pan'}) and IC.CAMERA_STEADY not in IC.take_lines_for({})


# ---------- S3 ----------

def texture(seed=1, size=(1536, 864)):
    rng = np.random.default_rng(seed)
    a = rng.integers(0, 255, (size[1] // 8, size[0] // 8), dtype=np.uint8)
    return Image.fromarray(a).resize(size, Image.NEAREST).convert('RGB')


def png(im):
    b = BytesIO()
    im.save(b, 'PNG')
    return b.getvalue()


def test_a_shifted_or_zoomed_pair_is_refused_with_the_figure_and_an_aligned_pair_passes():
    start = texture()
    same = start.copy()
    ImageDraw.Draw(same).rectangle((600, 300, 760, 420), fill=(200, 40, 40))   # the action area changed, the frame not
    rec = IC.pair_alignment(png(start), png(same))
    assert rec['pass'] is True and rec['shift_pct'] <= 1.0 and abs(rec['scale'] - 1) <= 0.01 and rec['weight'] == 'must'
    shifted = Image.new('RGB', start.size)
    shifted.paste(start, (31, 0))   # 2 % of the width to the right
    rec = IC.pair_alignment(png(start), png(shifted))
    assert rec['pass'] is False and 1.5 <= rec['shift_pct'] <= 2.5 and 'shift' in rec['seen']
    w, h = start.size
    zoomed = start.resize((round(w * 1.03), round(h * 1.03))).crop((round(w * 0.015), round(h * 0.015), round(w * 0.015) + w, round(h * 0.015) + h))
    rec = IC.pair_alignment(png(start), png(zoomed))
    assert rec['pass'] is False and rec['scale'] >= 1.02 and 'scale' in rec['seen']


def test_prepare_take_measures_the_pair_and_refuses_a_shifted_end():
    store, body = prepared(exact=True, end=True)
    start = texture()
    shifted = Image.new('RGB', start.size)
    shifted.paste(start, (31, 0))
    store.files['run-1/visuals/references/R1.png'] = png(start)
    store.files['run-1/visuals/references/R2.png'] = png(shifted)
    with pytest.raises(Problem, match='not aligned with the start') as exc:
        g(lambda: VS.prepare_take(store, USER, RUN, [], body))
    assert 'shift 2.' in exc.value.message and 'design/' not in exc.value.message
    store.files['run-1/visuals/references/R2.png'] = png(start)
    VS.prepare_take(store, USER, RUN, [], body)
    assert saved(store)['preparations']['VS1']['alignment']['pass'] is True
    store2, body2 = prepared(exact=True, end=True)   # pictures the store cannot read: the take goes on, the measurement is reported missing
    out = VS.prepare_take(store2, USER, RUN, [], body2)
    assert any('alignment' in w for w in out.get('warnings') or [])
