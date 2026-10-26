"""design/101: the surroundings move in every take. A scene's ambient line (M1), its warning (M2), the take's sentence (M3), the take check's line (M4),
the start image's sentence in the packet (M5), the procedure and the page (M6); no re-acceptance: the line never changes a gap's or a take's fingerprint."""
import json
import types
from fractions import Fraction
from pathlib import Path

from app import image_check as IC, visual_contract as VC, visuals_stage as VS
from app.video_providers import motion_text
from test_design91_b1_pure import Video, subject
from test_visuals_stage_pure import RUN, USER, FakeConn, accepted, gap_digest, plan_doc, ref, saved, session, shot, store_with
from test_visuals_pure import GAPS, plan, shot as pshot

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
LINE = 'palm fronds sway in a light breeze; fine dust drifts in the light; two workers on the far scaffolding pass bricks'


def kinds(doc):
    return {(w.get('scene_id'), w['kind']) for w in VC.validate_plan(doc, GAPS, Fraction(25))[1]}


# ---------- M1, M2 ----------

def test_a_scene_takes_an_ambient_line_and_an_old_plan_stays_valid_without_it():
    out, _ = VC.validate_plan(plan([pshot('IM1', 0, 100, 'image'), pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')]), GAPS, Fraction(25))
    assert 'ambient' not in out['gaps'][0]['scenes'][0]   # absent stays absent
    doc = plan([pshot('IM1', 0, 100, 'image'), pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    doc['gaps'][0]['scenes'][0]['ambient'] = LINE
    out, _ = VC.validate_plan(doc, GAPS, Fraction(25))
    assert out['gaps'][0]['scenes'][0]['ambient'] == LINE


def test_a_scene_with_a_video_shot_and_no_ambient_line_warns_and_a_still_scene_does_not():
    doc = plan([pshot('IM1', 0, 100, 'image'), pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    assert ('SC1', 'ambient_missing') in kinds(doc)
    doc['gaps'][0]['scenes'][0]['ambient'] = 'still: nothing else moves'
    assert ('SC1', 'ambient_missing') not in kinds(doc)
    stills = plan([pshot('IM1', 0, 500, 'image'), pshot('IM2', 500, 1000, 'image')])
    assert ('SC1', 'ambient_missing') not in kinds(stills)


# ---------- no re-acceptance: the line changes no fingerprint ----------

def take_store(ambient=None):
    vs = shot('VS1', 900, 1150, 'video', subjects=[subject((900, 1000, 3), (1000, 1150, 3), landmark='L2')])
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [vs])
    if ambient is not None:
        doc['gaps'][1]['scenes'][0]['ambient'] = ambient
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', 'approved')},
                   bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}})
    store = store_with(sess, doc)
    store.files['run-1/visuals/references/R1.png'] = b'start'
    store.files['run-1/visuals/references/R2.png'] = b'end'
    return store, doc


def test_an_ambient_line_changes_neither_the_gaps_digest_nor_a_takes_preparation_digest():
    _, plain = take_store()
    _, lined = take_store(LINE)
    assert gap_digest(plain, plain['gaps'][1]) == gap_digest(lined, lined['gaps'][1])
    assert VS.packet(take_store()[0], RUN, [], 'VS1')['preparation_digest'] == VS.packet(take_store(LINE)[0], RUN, [], 'VS1')['preparation_digest']


# ---------- M5 ----------

def test_the_packet_tells_the_writer_to_put_what_moves_in_the_start_image():
    ctx = VS.packet(take_store(LINE)[0], RUN, [], 'VS1')['preparation']['context']
    assert ctx['ambient']['line'] == LINE and 'Put in the frame what the scene\'s ambient line says moves' in ctx['ambient']['instruction']
    assert VS.packet(take_store()[0], RUN, [], 'VS1')['preparation']['context']['ambient']['line'] == ''


# ---------- M3 ----------

def snapshot(**over):
    return {'motion_prompt': 'He lays two bricks on the top course.', 'subject_reconciliation': {'E1': 'the mason'}, 'continuity_notes': 'the wall stays',
            'duration_seconds': 5, 'end_image': {'key': 'k'}, **over}


def test_the_take_text_carries_the_ambient_sentence_once_after_the_motion_and_is_unchanged_without_it():
    text = motion_text(snapshot(ambient=LINE))
    sentence = 'Throughout the shot the surroundings stay alive: ' + LINE + '.'
    assert text.count(sentence) == 1 and text.index('He lays two bricks') < text.index(sentence) < text.index('Subject reconciliation')
    assert motion_text(snapshot()) == motion_text(snapshot(ambient=''))
    assert 'surroundings' not in motion_text(snapshot())


def test_a_prepared_take_carries_the_scenes_ambient_line(monkeypatch):
    monkeypatch.setattr(VS, '_gemini_transport', lambda: None)
    store, _ = take_store(LINE)
    body = {'shot_id': 'VS1', 'motion_prompt': 'he lays two bricks on the top course', 'subject_reconciliation': {'E1': 'the mason'}, 'start_image': 'R1', 'end_image': 'R2',
            'continuity_notes': 'the wall and the light stay'}
    VS.prepare_take(store, USER, RUN, [], body)
    record = json.loads(store.files[saved(store)['preparations']['VS1']['key']])
    assert record['ambient'] == LINE and 'the surroundings stay alive: ' + LINE in record['effective_prompt']
    store, _ = take_store()
    VS.prepare_take(store, USER, RUN, [], body)
    assert 'ambient' not in json.loads(store.files[saved(store)['preparations']['VS1']['key']])


# ---------- M4 ----------

def test_the_take_check_asks_whether_the_surroundings_move_only_when_the_take_has_a_line(monkeypatch, tmp_path):
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: 'k')))
    video_path = tmp_path / 'output.mp4'
    video_path.write_bytes(b'mp4')
    rec = IC.run_take_check({'motion_prompt': 'm', 'ambient': LINE}, video_path, 'a' * 64, Video)
    asked = json.dumps(Video.payload)
    assert '6. surroundings move' in asked and LINE in asked and [l['check'] for l in rec['lines']][-1] == 'surroundings move'
    assert IC.AMBIENT_LINE['weight'] == 'must'
    rec = IC.run_take_check({'motion_prompt': 'm'}, video_path, 'a' * 64, Video)
    assert '6. ' not in json.dumps(Video.payload) and len(rec['lines']) == 5


# ---------- M6 ----------

def test_the_procedure_names_the_field():
    doc = json.loads((ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8'))
    assert 'ambient' in json.dumps(doc) and 'what moves around the action' in json.dumps(doc)


def test_the_page_shows_what_moves_around_a_video_shot():
    store, doc = take_store(LINE)
    view = VS.page_view(FakeConn([]), store, RUN, [], 'VW-9')
    shots = {s['shot_id']: s for g in view['gaps'] for s in g['shots']}
    assert shots['VS1']['ambient'] == LINE and not shots['IM1'].get('ambient')
    assert "'Moves around it: '+esc(s.ambient)" in PAGE


# ---------- SK, 26 Oct: the take's remarks fold, as a picture's check does (design/97 K1) ----------

def test_the_take_check_and_the_review_notes_fold_to_one_line():
    fn = PAGE[PAGE.index('function takeCheck(c){'):PAGE.index('function checklist(')]
    assert "<details class=\"chkd\"><summary" in fn and "'Take check: '+ok+' passed'" in fn
    assert 'function reviewsOf(k)' in fn and "' earlier</summary>'" in fn
    assert 'reviewsOf(k)' in PAGE[PAGE.index("s.takes.map(k=>'<tr data-take="):]
