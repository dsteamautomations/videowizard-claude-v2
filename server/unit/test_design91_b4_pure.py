"""design/91 batch 4: N12 a build that builds, N13 labels, N15 every shot fills the frame, N16 transitions chosen (SK: 8-frame dissolve at graphics)."""
import json
import shutil
import subprocess
from fractions import Fraction
from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from app import visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from app.stage3 import assembly as A
from test_batch89_pure import MEDIA, clip_session
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, g, plan_doc, ref, saved, session, shot, store_with
from test_visuals_pure import GAPS, plan, shot as pshot, states

FFMPEG = shutil.which('ffmpeg') and shutil.which('ffprobe')


def kinds(doc):
    return {(w.get('shot_id'), w['kind']) for w in VC.validate_plan(doc, GAPS, Fraction(25))[1]}


# ---------- N16 in the plan ----------

def test_a_chosen_transition_needs_its_reason_and_transition_out_is_for_a_gaps_last_shot():
    im = {**pshot('IM1', 0, 100, 'image'), 'transition_in': 'dissolve'}
    rest = [pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')]
    with pytest.raises(ValueError, match='reason'):
        VC.validate_plan(plan([im] + rest), GAPS, Fraction(25))
    VC.validate_plan(plan([{**im, 'transition_reason': 'the wall dissolves into its section'}] + rest), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='last shot'):
        VC.validate_plan(plan([{**pshot('IM1', 0, 100, 'image'), 'transition_out': 'cut', 'transition_reason': 'x'}] + rest), GAPS, Fraction(25))
    VC.validate_plan(plan([pshot('IM1', 0, 100, 'image'), pshot('VS1', 100, 500, 'video'), {**pshot('VS2', 500, 1000, 'video'), 'transition_out': 'match', 'transition_reason': 'same arch'}]),
                     GAPS, Fraction(25))
    out, _ = VC.validate_plan(plan([pshot('IM1', 0, 100, 'image')] + rest), GAPS, Fraction(25))
    assert 'transition_in' not in out['gaps'][0]['scenes'][0]['shots'][0]   # absent stays absent


# ---------- N12 ----------

def test_a_build_with_fewer_states_than_claims_warns():
    an = {**pshot('AN1', 0, 250, 'animation'), 'states': states(5, 5), 'claims': ['one storey', 'two storeys', 'three storeys']}
    assert ('AN1', 'build_short') in kinds(plan([an, pshot('VS1', 250, 500, 'video'), pshot('VS2', 500, 1000, 'video')]))
    assert ('AN1', 'build_short') not in kinds(plan([{**an, 'end_frame': 300, 'states': states(4, 4, 4)}, pshot('VS1', 300, 500, 'video'), pshot('VS2', 500, 1000, 'video')]))


def drawing(*boxes):
    img = Image.new('RGB', (160, 90), 'white')
    d = ImageDraw.Draw(img)
    for b in boxes:
        d.rectangle(b, outline='black', width=3)   # an outline: a filled box is flat inside its content and has no fingerprint
    out = BytesIO()
    img.save(out, 'PNG')
    return out.getvalue()


def sequence_store(second):
    doc = plan_doc([shot('AN1', 0, 500, 'animation', states=[{'what_appears': 'section', 'hold_s': 10}, {'what_appears': 'cavities', 'hold_s': 10}])],
                   [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', parents=['R1'])})
    store = store_with(sess, doc)
    store.files['run-1/visuals/references/R1.png'] = drawing((10, 10, 150, 80))
    store.files['run-1/visuals/references/R2.png'] = second
    return store


def test_a_state_that_adds_nothing_visible_is_refused():
    """N12: the same fingerprint as the state before."""
    with pytest.raises(Problem, match='state 2'):
        g(lambda: VS.sequence(sequence_store(drawing((10, 10, 150, 80))), USER, RUN, [], 'AN1', ['R1', 'R2'], 'yes'))
    out = VS.sequence(sequence_store(drawing((10, 10, 150, 80), (20, 20, 40, 70), (100, 20, 140, 70))), USER, RUN, [], 'AN1', ['R1', 'R2'], 'yes')
    assert out['states'] == 2


# ---------- N13 ----------

def test_a_graphics_labels_are_must_lines_with_the_size_and_a_sign_in_place_of_words_warns(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc = plan_doc([shot('DG1', 0, 100, 'diagram', narration='Fewer bricks.', depicts='a rat-trap wall', claims_left_out=[{'claim': 'x', 'reason': 'y'}]), shot('IM1', 100, 500, 'image')],
                   [shot('VS1', 900, 1150, 'video', subjects=[])])
    store = store_with(session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc)), doc)
    prompt = 'A wall section labelled "25% fewer bricks", "↓ 25%" and "110".'
    answer = {'status': 'ready', 'prompt': prompt, 'checklist': [{'check': 'look', 'pass_when': 'flat', 'weight': 'must'}], 'exact_text': ['25% fewer bricks', '↓ 25%', '110']}
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'l1', 'element_id': 'E1', 'name': 'wall', 'kind': 'isolated', 'subject': 'wall', 'prompt': prompt, 'answer': answer})
    lines = {l['check']: l for l in saved(store)['references'][out['reference_id']]['server_checklist']}
    assert lines['label: 25% fewer bricks']['weight'] == 'must' and 'leader line' in lines['label: 25% fewer bricks']['pass_when'] and '4 %' in lines['label: 25% fewer bricks']['pass_when']
    assert lines['label size']['weight'] == 'should' and '6 %' in lines['label size']['pass_when']
    w = ' | '.join(out['warnings'])
    assert '↓ 25%' in w and 'words' in w and "'110'" in w and 'unit' in w


# ---------- N15 ----------

def test_a_source_fills_the_frame_when_the_enlargement_is_within_the_cap_else_keeps_bars():
    from app.stage2 import render as R
    fill, _ = R.fit(2048, 858, 1920, 1080)   # 2.39:1 drone: 1.34x to fill
    assert fill and 'increase' in R.fit_filters(2048, 858, 1920, 1080)[0][0]
    fill, _ = R.fit(1080, 1920, 1920, 1080)   # a portrait phone clip: 3.16x
    assert not fill
    assert R.fit(1920, 1080, 1920, 1080)[0]   # the same shape: nothing to crop


@pytest.mark.skipif(not FFMPEG, reason='ffmpeg not installed')
def test_the_renderer_crops_a_wide_clip_to_fill_and_reports_a_portrait_clip_that_keeps_bars(tmp_path):
    from app.stage2 import render as R

    def clip(name, size):
        p = tmp_path / name
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'color=c=red:s={size}:r=25:d=1', '-pix_fmt', 'yuv420p', str(p)], check=True, capture_output=True)
        return p

    def corner(path):
        out = tmp_path / 'f.png'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(path), '-frames:v', '1', str(out)], check=True, capture_output=True)
        return Image.open(out).convert('RGB').getpixel((1, 1))

    r = R.Renderer(tmp_path / 'w', {'width': 160, 'height': 90, 'fps': 25})
    ev = {'source_in_frame': 0, 'source_out_frame': 10, 'hold_last_frame': False}
    wide = r.segment(clip('wide.mp4', '240x100'), 'w1', '25', ev, 10, label=None)
    assert corner(wide)[0] > 150 and not r.padded   # red to the corner: no bars
    tall = r.segment(clip('tall.mp4', '90x160'), 't1', '25', ev, 10, label=None, name='VS7')
    assert corner(tall)[0] < 40 and r.padded == ['VS7']


def test_a_clip_stretch_that_would_keep_bars_warns():
    doc, sess = clip_session()
    store = store_with(sess, doc)
    media = json.loads(json.dumps(MEDIA))
    media['summary']['clips'][0].update(width=1080, height=1920)
    out = VS.fill_clip(store, USER, RUN, [media], 'VS1', 'c1', 4.0, 'This stretch, yes.')
    assert any('bars' in w and '--crop' in w for w in out['warnings'])
    out = VS.fill_clip(store, USER, RUN, [media], 'VS1', 'c1', 4.0, 'This stretch, yes.', crop=[0.0, 0.3, 1.0, 0.32])
    assert not [w for w in out.get('warnings') or [] if 'bars' in w]


def test_the_frame_size_is_read_as_a_list_as_real_runs_store_it():
    """Defect 26 (VW-9): the visuals session stores the film's size as [1920, 1080] (from the master's summary); the bars check read only '1920x1080'."""
    doc, sess = clip_session()
    sess['source']['resolution'] = [1920, 1080]
    store = store_with(sess, doc)
    media = json.loads(json.dumps(MEDIA))
    media['summary']['clips'][0].update(width=1080, height=1920)
    out = VS.fill_clip(store, USER, RUN, [media], 'VS1', 'c1', 4.0, 'This stretch, yes.')
    assert any('1920x1080 frame' in w for w in out['warnings'])


# ---------- N16 in assembly ----------

def ev_(kind, sid, media=None, transition=None):
    e = {'kind': kind, 'shot_id': sid, 'sub_clip_id': sid, 'dissolve_into_next': 0}
    if kind == 'fill':
        e.update(media=media or {'kind': 'movie'}, transition=transition or {})
    return e


def test_a_graphic_dissolves_in_and_out_eight_frames_and_everything_else_cuts():
    events = [ev_('event', 'f1'), ev_('fill', 'DG1', {'kind': 'still', 'graphic': True}), ev_('fill', 'VS1'), ev_('fill', 'AN1', {'kind': 'sequence'}), ev_('event', 'f2'),
              ev_('fill', 'IM1', {'kind': 'still', 'graphic': False}), ev_('event', 'f3')]
    A.transitions(events)
    assert [e['dissolve_into_next'] for e in events] == [8, 8, 8, 8, 0, 0, 0]
    events = [ev_('event', 'f1'), ev_('fill', 'IM1', {'kind': 'still', 'graphic': False}, {'in': 'dissolve', 'reason': 'a change of time'}),
              ev_('fill', 'DG1', {'kind': 'still', 'graphic': True}, {'in': 'cut', 'reason': 'a match on the arch', 'out': 'match'}), ev_('event', 'f2')]
    A.transitions(events)
    assert [e['dissolve_into_next'] for e in events] == [8, 0, 0, 0]   # chosen: a dissolve in; a cut in; a match out (rendered as a cut)


@pytest.mark.skipif(not FFMPEG, reason='ffmpeg not installed')
def test_a_still_dissolves_into_the_footage_after_it_and_the_film_keeps_its_length(tmp_path):
    from app.stage2 import render as R
    narration = tmp_path / 'n.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', '2', str(narration)], check=True, capture_output=True)
    clip = tmp_path / 'c.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=64x48:r=25:d=2', '-pix_fmt', 'yuv420p', str(clip)], check=True, capture_output=True)
    still = tmp_path / 's.png'
    Image.new('RGB', (64, 48), 'white').save(still)
    plan_ = {'items': [{'kind': 'still', 'file': {'sha256': 's1'}, 'timeline_frames': 25, 'motion': 'none', 'graphic': True, 'dissolve_into_next': 8, 'label': 'DG1'},
                       {'kind': 'event', 'sub_clip_id': 'f1', 'clip': {'id': 'f1', 'name': 'c.mp4', 'sha256': 'f1', 'fps': '25', 'rotation_deg': 0.0, 'hdr': False},
                        'source_in_frame': 0, 'source_out_frame': 25, 'timeline_frames': 25, 'crop_rect': None, 'hold_last_frame': False, 'a2': []}]}
    film, record = R.render_film('assembly', plan_, {'s1': still, 'f1': clip}, narration, tmp_path / 'w', {'width': 64, 'height': 48, 'fps': 25})
    out = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', str(film)],
                         capture_output=True, text=True, check=True).stdout
    assert int(out.strip()) == 50 and record['frames'] == 50


@pytest.mark.skipif(not FFMPEG, reason='ffmpeg not installed')
def test_assembly_reports_a_planned_state_that_does_not_appear(tmp_path):
    """N12: a frame from the middle of each state's hold against the state's picture."""
    from app.stage2 import render as R
    a, b = tmp_path / 'a.png', tmp_path / 'b.png'
    a.write_bytes(drawing((10, 10, 150, 80)))
    b.write_bytes(drawing((10, 10, 150, 80), (20, 20, 40, 70), (100, 20, 140, 70)))
    r = R.Renderer(tmp_path / 'w', {'width': 160, 'height': 90, 'fps': 25})
    seg = r.sequence([(a, 'a', 25), (b, 'b', 25)], 0, 50)
    assert R.states_missing(seg, [(a, 25), (b, 25)], 25) == []
    seg_one = r.sequence([(a, 'a', 50)], 0, 50)
    assert R.states_missing(seg_one, [(a, 25), (b, 25)], 25) == [2]


def test_record_gap_carries_a_shots_chosen_transition_to_assembly(monkeypatch):
    doc, sess = clip_session()
    doc['gaps'][1]['scenes'][0]['shots'][0].update(transition_in='dissolve', transition_reason='a change of time')
    sess['accepted'] = accepted(doc)
    store = store_with(sess, doc)
    VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'c1', 4.0, 'This stretch, yes.')
    rec = []
    monkeypatch.setattr(VS.core, 'output', lambda conn, user, run, body: (rec.append(body) or {'id': 'o1'}))
    VS.record_gap(FakeConn(), store_with(saved(store), doc), USER, RUN, [MEDIA], 'G2', 'record')
    assert rec[0]['summary']['shots'][0]['transition'] == {'in': 'dissolve', 'out': '', 'reason': 'a change of time'}
