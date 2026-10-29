"""design/124 A3 decisions 5 and 9, A4 decisions 2 and 5, and the A4 "fix now" texts in the server's own voice.
Decision 5: a person's sheet is made from words; a footage frame or web picture of a person is never a parent of any picture (a supplied one is).
Decision 9: an end image is made only from an approved start (the server makes it from end_prompt once the start is approved).
A4 decision 5: Gemini Omni only (3-10 s); an older Kling/Seedance choice is still read, but no new take is prepared on it.
A4 decision 2: takes are locked off unless the shot's camera_move names its one move; no guidance asks for handheld movement."""
import json
from fractions import Fraction

import pytest

from app import image_check as IC, video_generators as VG, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design101_pure import take_store
from test_design102_pure import shot_, side
from test_design106_pure import start_store
from test_design111_f11_pure import REGION, golden_store, image, put
from test_design119_d_pure import sheet_store
from test_visuals_stage_pure import RUN, USER, FakeConn, accepted, g, ref, saved
from test_visuals_pure import GAPS, plan, shot as pshot

KLING = 'kling-video/v3.0/std/image-to-video'


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def doc_of(store):
    return json.loads(store.files['run-1/visuals/plan-v1.json'])['document']


def set_doc(store, doc):
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    s['accepted'] = accepted(doc)
    if 'VS1' in s['bindings']:
        s['bindings']['VS1']['gap_digest'] = s['accepted']['G2']['digest']
    put(store, s)


def person_store():
    """sheet_store plus E4, a person, with an approved footage frame F4, a web pick W4 and the operator's own picture U4."""
    store = sheet_store()
    doc = doc_of(store)
    doc['elements'].append({'id': 'E4', 'name': 'The mason', 'kind': 'person', 'identity': 'representative', 'requirements': 'a mason', 'required_views': ['front', 'side']})
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    for rid, kind in (('F4', 'frame'), ('W4', 'web'), ('U4', 'supplied')):
        s['references'][rid] = {**ref(rid, 'approved'), 'kind': kind, 'element_id': 'E4'}
    put(store, s)
    return store


# ---------- decision 5: a person's sheet from words ----------

def test_a_persons_sheet_is_due_from_the_description_with_no_picture_parents():
    store = person_store()
    due = {d['element_id']: d['next'] for d in VS.status(FakeConn([]), store, RUN, [], repair=False)['sheet_due']}
    assert '--parents' not in due['E4'] and "from the person's description" in due['E4'] and 'no picture parents' in due['E4']
    assert '--parents W3,U3' in due['E3']   # a thing keeps its pictures as parents


def test_a_footage_frame_or_web_picture_of_a_person_is_refused_as_a_parent_by_name_and_a_supplied_one_is_not():
    store = person_store()
    for rid, word in (('F4', 'footage frame'), ('W4', 'web picture')):
        with pytest.raises(Problem, match=f'{rid} is a {word} of The mason \\(E4\\), a person') as exc:
            g(lambda: image(store, element_id='E4', kind='sheet', name='sheet-E4', subject='the mason', parents=[rid], prompt='Image 1 is the mason: take his build.'))
        assert "description" in exc.value.message
    with pytest.raises(Problem, match='F4 is a footage frame of The mason'):   # a parent of any picture, not only the person's own
        g(lambda: image(store, element_id='E3', kind='sheet', name='sheet-E3', subject='the broom', parents=['W3', 'F4'],
                        prompt='Image 1 is the broom: take its form. Image 2 is the mason: take the hand.'))
    assert image(store, element_id='E4', kind='sheet', name='sheet-E4', subject='the mason', parents=['U4'], prompt="Image 1 is the operator's own picture of the mason: take his build.")['reference_id']
    assert image(store, element_id='E4', kind='sheet', name='sheet-E4w', subject='the mason', parents=[], prompt='The mason: wiry, about fifty, a faded blue shirt.', request_id='q-words')['op'] == 'generate'


# ---------- decision 9: the end after the start's approval ----------

def test_an_end_from_a_candidate_start_is_refused_naming_end_prompt_and_an_approved_start_still_makes_one():
    store = start_store()
    s = saved(store)
    s['references']['K9'] = {**ref('K9', 'candidate'), 'kind': 'keyframe', 'shot_id': 'VS1', 'role': 'start'}
    put(store, s)
    body = {'request_id': 'q-end', 'element_id': 'E1', 'name': 'keyframe-end-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer',
            'prompt': 'Image 1 is the start; the labourer at the edge.', 'parents': ['K9'], 'role': 'end', 'region': REGION}
    with pytest.raises(Problem, match='K9 is a start image still waiting for approval') as exc:
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], body))
    assert 'end_prompt' in exc.value.message and 'design/' not in exc.value.message
    assert VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'parents': ['K1']})['op'] == 'edit'


def test_the_parent_check_line_passes_only_on_approved_parents_a_fix_and_a_state_excepted():
    line = lambda ref_, parents: next(l for l in IC.code_checks(ref_, {}, parents) if l['check'] == 'parent')['pass']
    assert line({'kind': 'keyframe'}, [{'id': 'K1', 'status': 'candidate', 'kind': 'keyframe'}]) is False
    assert line({'kind': 'keyframe'}, [{'id': 'K1', 'status': 'approved', 'kind': 'keyframe'}]) is True
    assert line({'kind': 'keyframe', 'fix_of': 'K1'}, [{'id': 'K1', 'status': 'candidate', 'kind': 'keyframe'}]) is True
    assert line({'kind': 'state'}, [{'id': 'T1', 'status': 'candidate', 'kind': 'state'}]) is True


def test_a_fix_of_a_start_carries_its_end_region():
    body = IC.fix_body({'id': 'K1', 'element_id': 'E1', 'name': 'k', 'kind': 'keyframe', 'role': 'start', 'pending_end': {'prompt': 'Image 1 is the start.', 'region': REGION}},
                       {'check': 'x', 'pass_when': 'y'})
    assert body['end_region'] == REGION


def test_a_start_approved_says_end_next_only_when_the_shot_has_an_exact_end():
    store = start_store()
    s = saved(store)
    assert VS._approved_next(store, s, s['references']['K1']) == 'Approved: the take for VS1 is the next step.'
    doc = doc_of(store)
    doc['gaps'][1]['scenes'][0]['shots'][0]['end_state_exact'] = True
    set_doc(store, doc)
    s = saved(store)
    nxt = VS._approved_next(store, s, s['references']['K1'])
    assert 'end image' in nxt and 'K1' in nxt


def test_the_prepare_take_refusal_for_an_exact_end_names_end_prompt():
    store, doc = take_store()
    doc['gaps'][1]['scenes'][0]['shots'][0]['end_state_exact'] = True
    set_doc(store, doc)
    body = {'shot_id': 'VS1', 'motion_prompt': 'he lays two bricks', 'subject_reconciliation': {'E1': 'the mason'}, 'start_image': 'R1', 'continuity_notes': 'the wall stays'}
    with pytest.raises(Problem, match='final state must be exact') as exc:
        g(lambda: VS.prepare_take(store, USER, RUN, [], body))
    assert 'end_prompt' in exc.value.message and 'approve both' not in exc.value.message


# ---------- A4 decision 5: Gemini Omni only ----------

def test_the_catalogue_offers_omni_only_and_another_generator_is_refused():
    assert [(o['provider'], o['model'], o['max_seconds']) for o in VG.catalog()['options']] == [('google', VG.OMNI, 10)]
    store, _ = take_store()
    with pytest.raises(Problem, match='every take is Gemini Omni, 3–10 s; split the shot'):
        g(lambda: VS.select_generator(store, USER, RUN, [], 'VS1', 'higgsfield', KLING))
    assert VS.select_generator(store, USER, RUN, [], 'VS1', 'google', VG.OMNI)['model'] == VG.OMNI


def test_a_shot_that_chose_kling_is_still_read_but_takes_no_new_take(monkeypatch):
    monkeypatch.setattr(VS, '_gemini_transport', lambda: None)
    store, _ = take_store()
    s = saved(store)
    s['generator_choices']['VS1'] = {'provider': 'higgsfield', 'model': KLING, 'plan_digest': 'd1'}
    put(store, s)
    assert VS.packet(store, RUN, [], 'VS1')['preparation']['provider'] == {'provider': 'higgsfield', 'model': KLING}   # read as it was: its prepared takes stay current
    body = {'shot_id': 'VS1', 'motion_prompt': 'he lays two bricks', 'subject_reconciliation': {'E1': 'the mason'}, 'start_image': 'R1', 'continuity_notes': 'the wall stays'}
    with pytest.raises(Problem, match='every take is Gemini Omni'):
        g(lambda: VS.prepare_take(store, USER, RUN, [], body))
    s = saved(store)
    s['generator_choices'] = {}
    put(store, s)
    assert VS.prepare_take(store, USER, RUN, [], body)['provider']['model'] == VG.OMNI


def test_the_plan_check_refuses_a_video_shot_longer_than_omni_makes():
    with pytest.raises(ValueError, match='split it'):
        VC.validate_plan(plan([pshot('V1', 0, 300, 'video'), pshot('IM1', 300, 1000, 'image')]), GAPS, Fraction(25))   # 12 s
    VC.validate_plan(plan([pshot('V1', 0, 250, 'video'), pshot('IM1', 250, 1000, 'image')]), GAPS, Fraction(25))   # 10 s: allowed


# ---------- A4 decision 2: steady takes ----------

def test_the_guidance_never_asks_for_handheld_movement():
    hand = ' '.join(VS.shot_guidance(shot_(), {'before': side('handheld'), 'after': side('tripod')}))
    assert 'micro-movement' not in hand and 'locked off' in hand and 'camera_move' in hand


# ---------- A4 fix-now texts ----------

def test_prepare_says_treatment_first():
    src = open(VS.__file__, encoding='utf-8').read()
    assert "'next': 'write out/visual-plan.json then `vw visuals check`'" not in src and 'settle the treatment with the operator and record it (`vw visuals treatment`), then write the plan' in src


def test_the_readable_text_line_allows_the_labels_a_sheet_a_spec_or_a_style_carries():
    text = next(l for l in IC.FIXED if l['check'] == 'readable text')['pass_when']
    assert 'label' in text and 'sheet' in text and 'spec' in text and 'style' in text


def test_a_sheet_takes_no_scene_lines_and_no_world_line():
    assert not [l for l in IC.lines_of({'kind': 'sheet', 'element_kind': 'object'}) if l['check'] == 'plausible setting']
    assert [l for l in IC.lines_of({'kind': 'isolated', 'element_kind': 'object'}) if l['check'] == 'plausible setting']
    store = sheet_store()
    out = image(store, element_id='E3', kind='sheet', name='sheet-E3', subject='the broom', parents=['W3', 'U3'], shot_id='VS1',
                prompt='Image 1 is the web picture of the broom: take its form. Image 2 is the supplied picture: take its binding.')
    assert "the film's world" not in [l['check'] for l in saved(store)['references'][out['reference_id']]['server_checklist']]


def test_a_sheet_approved_names_the_golden_picture_next_for_a_thing_and_a_reference_rejected_by_kind():
    store = person_store()
    s = saved(store)
    s['references']['S3'] = {**ref('S3', 'approved'), 'kind': 'sheet', 'element_id': 'E3'}
    s['references']['S4'] = {**ref('S4', 'approved'), 'kind': 'sheet', 'element_id': 'E4'}
    put(store, s)
    assert 'golden picture of E3' in VS._approved_next(store, s, s['references']['S3'])
    assert 'golden' not in VS._approved_next(store, s, s['references']['S4'])
    web = VS.reject_reference(store, USER, RUN, [], 'W3', 'wrong broom', 'Not this one.')['next']
    assert "operator's words" in web and 'assistant makes' not in web
    start = VS.reject_reference(start_store(), USER, RUN, [], 'K1', 'too dark', 'too dark')['next']
    assert start == 'Rejected: the assistant makes a new start image with your note.'


def test_the_region_refusal_names_the_start_only_shot_for_an_end():
    with pytest.raises(ValueError) as exc:
        VS.check_region({'left': 0, 'top': 0, 'width': 0.9, 'height': 0.9})
    assert 'start-only' in str(exc.value) and 'design/' not in str(exc.value)


def test_the_stack_clause_only_where_a_stack_is_named_and_nothing_is_put_on_it():
    scene = {'landmarks': [{'id': 'L1', 'description': 'the table'}, {'id': 'L2', 'description': 'the brick stack'}]}
    d = {'elements': [{'id': 'B', 'name': 'Red brick'}]}
    on_table = {'subjects': [{'element_id': 'E1', 'start': {'objects': [{'element_id': 'B', 'count': 2, 'place': {'landmark_id': 'L1', 'relation': 'on'}}]}}]}
    assert 'stack' not in VS.inventory_line(d, scene, on_table, 'start')
    by_stack = {'subjects': [{'element_id': 'E1', 'start': {'objects': [{'element_id': 'B', 'count': 2, 'place': {'landmark_id': 'L2', 'relation': 'beside'}}]}}]}
    assert VS.inventory_line(d, scene, by_stack, 'start').endswith('nothing rests on top of the stack.')
    onto = {'subjects': [{'element_id': 'E1', 'start': {'objects': [{'element_id': 'B', 'count': 2, 'place': {'landmark_id': 'L2', 'relation': 'beside'}}]},
                          'end': {'objects': [{'element_id': 'B', 'count': 2, 'place': {'landmark_id': 'L2', 'relation': 'on top of'}}]}}]}
    assert 'nothing rests on top' not in VS.inventory_line(d, scene, onto, 'start')


def test_bind_advice_skips_the_texture_frame_once_the_golden_picture_exists():
    store = golden_store()
    s = saved(store)
    doc = doc_of(store)
    shot = doc['gaps'][1]['scenes'][0]['shots'][0]
    assert any(a['element_id'] == 'E2' for a in VS.bind_advice(doc, s, shot))
    s.setdefault('golden', {})['E2'] = 'G2'
    assert not any(a['element_id'] == 'E2' and a['use'] == 'texture' for a in VS.bind_advice(doc, s, shot))


def test_the_cutaway_reason_is_not_about_walls():
    assert VS.spec_view({'depicts': 'a section of the slab'}) == ('cutaway', 'a section is shown cut through')


def test_the_not_this_prompt_and_the_code_keep_twelve_lines():
    src = open(VS.__file__, encoding='utf-8').read()
    assert 'twelve lines at most' in src and 'eight lines at most' not in src and "_dedupe_lines(body.get('lines') or [])[:12]" in src
