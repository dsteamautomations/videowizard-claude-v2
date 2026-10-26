"""design/102, Release 4 (course batch B): the take's motion line (B3), the packet's guidance per shot (B1, B2, B4, B8, B10, B13), the procedure's
sentences (B5, B6, B7, B8, B9, B11); none of it changes a prepared take's fingerprint."""
import json
from pathlib import Path

from app import visuals_stage as VS
from app.video_providers import motion_text
from test_design101_pure import snapshot, take_store
from test_visuals_stage_pure import RUN

ROOT = Path(__file__).resolve().parents[1]
B3 = 'Natural, unhurried motion; no sudden, exaggerated or floating movement.'


def steps():
    doc = json.loads((ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8'))
    return next(s for s in doc['stages'] if s['name'] == 'visuals')['steps']


# ---------- B3 ----------

def test_every_new_take_asks_for_natural_unhurried_motion_once():
    text = motion_text(snapshot())
    assert text.count(B3) == 1 and text.index('He lays two bricks') < text.index(B3) < text.index('Subject reconciliation')
    assert motion_text(snapshot(ambient='leaves sway')).count(B3) == 1


# ---------- the packet's guidance ----------

def shot_(framing='medium', visual_type='video', camera='static'):
    return {'id': 'S1', 'framing': framing, 'visual_type': visual_type, 'camera': camera}


def side(support):
    return {'clip_id': 'c', 'support': support}


def test_a_wide_or_medium_shot_gets_layers_acting_traces_and_framing():
    lines = VS.shot_guidance(shot_('wide establishing'), {})
    text = ' '.join(lines)
    for words in ('a foreground, a midground and a background', 'carry the action in the hands, shoulders and posture', 'Work leaves traces', 'Thirds by default'):
        assert words in text
    assert not any('handheld' in l or 'steady' in l for l in lines)   # the neighbours' support is not known


def test_a_close_up_gets_no_layers_line_and_a_graphic_gets_nothing():
    assert not any('midground' in l for l in VS.shot_guidance(shot_('close-up on the hands'), {}))
    assert VS.shot_guidance(shot_(visual_type='animation'), {}) == [] and VS.shot_guidance(shot_(visual_type='diagram'), {}) == []


def test_the_camera_follows_the_clips_beside_the_gap():
    hand = ' '.join(VS.shot_guidance(shot_(), {'before': side('handheld'), 'after': side('tripod')}))
    assert 'slight handheld micro-movement' in hand
    steady = ' '.join(VS.shot_guidance(shot_(), {'before': side('tripod'), 'after': None}))
    assert 'keep the camera steady' in steady and 'handheld' not in steady
    assert not any('camera steady' in l or 'micro-movement' in l for l in VS.shot_guidance(shot_(), {'before': side('unknown'), 'after': {'clip_id': 'x'}}))
    assert not any('micro-movement' in l for l in VS.shot_guidance(shot_(visual_type='image'), {'before': side('handheld')}))   # a still does not move


def test_the_packet_carries_the_guidance_and_its_fingerprint_does_not_change(monkeypatch):
    store, _ = take_store()
    out = VS.packet(store, RUN, [], 'VS1')
    assert any('midground' in l for l in out['preparation']['context']['guidance'])
    monkeypatch.setattr(VS, 'shot_guidance', lambda shot, nb: [])
    assert VS.packet(take_store()[0], RUN, [], 'VS1')['preparation_digest'] == out['preparation_digest']


# ---------- the procedure ----------

def test_the_procedure_steps_carry_their_sentences():
    s = steps()
    assert 'strongest picture of the film' in s[1]                                          # B11, the treatment
    assert 'never what the setting forbids' in s[2] and 'Work leaves traces' in s[2]          # B9, B8, the plan
    assert 'different colour families' in s[3] and 'sharpest frame' in s[3]                  # B5, B7, the references
    assert 'say why each reference is bound' in s[4]                                         # B6, the pictures and takes
