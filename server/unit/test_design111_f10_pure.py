"""design/111 F10: a repeating material has one measured spec on the element (unit sizes with sources, how it is laid, the joint, the pattern rule,
the proportions), made like the drawing spec, approved once on the References step, pasted word for word by the server into every prompt that shows
the material; relative size words are refused in the writer's prompt; the check measures the unit ratio and the pattern as a must line."""
import copy
import json
from fractions import Fraction
from pathlib import Path

import pytest

from app import library as L, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design106_pure import revise_start, start_store
from test_visuals_pure import GAPS, plan, shot as pshot
from test_visuals_stage_pure import RUN, USER, FakeConn, accepted, g, saved

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
BRICK_SPEC = {'dimensions': [{'part': 'brick', 'measure': 'length', 'value': 190, 'unit': 'mm', 'source': 'the client brief p.2', 'status': 'confirmed'},
                             {'part': 'brick', 'measure': 'width', 'value': 90, 'unit': 'mm', 'source': 'the client brief p.2', 'status': 'confirmed'},
                             {'part': 'brick', 'measure': 'height', 'value': 90, 'unit': 'mm', 'source': 'the client brief p.2', 'status': 'confirmed'},
                             {'part': 'joint', 'measure': 'thickness', 'value': 10, 'unit': 'mm', 'source': 'measured on C0120 at 12 s', 'status': 'measured'}],
              'laid': 'on edge, header ends to the camera', 'joint': '10 mm mortar joints', 'pattern': 'one long face alternating with one header per course; courses offset by half a header',
              'proportions': ['long face a little more than twice as wide as tall', 'header end a square'], 'relationships': [], 'label': ''}
BRICK = {'id': 'BRICK', 'name': 'Red brick', 'kind': 'material', 'identity': 'exact', 'requirements': 'the client\'s fired red brick', 'material_spec': BRICK_SPEC}


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def doc_with(element=BRICK):
    d = plan([pshot('IM1', 0, 500, 'image'), pshot('VS2', 500, 1000, 'video')])
    d['elements'].append(copy.deepcopy(element))
    d['gaps'][0]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'BRICK']
    return d


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


# ---------- the schema and the plan check ----------

def test_a_repeating_material_needs_its_spec_with_sourced_sizes_a_laying_a_pattern_and_proportions():
    out, _ = check(doc_with())
    assert out['elements'][1]['material_spec']['laid'] == 'on edge, header ends to the camera' and out['elements'][1]['material_spec']['not_this'] == []
    with pytest.raises(ValueError, match='BRICK is a repeating material: give its material_spec'):
        check(doc_with({**BRICK, 'material_spec': None}))
    with pytest.raises(ValueError, match='repeating material: give its material_spec'):
        check(doc_with({**BRICK, 'kind': 'object', 'repeating': True, 'material_spec': None}))
    bad = copy.deepcopy(BRICK)
    bad['material_spec']['dimensions'][0].pop('source')
    with pytest.raises(ValueError, match='material spec of BRICK: brick length is confirmed: give its source'):
        check(doc_with(bad))
    bad = copy.deepcopy(BRICK)
    bad['material_spec']['proportions'] = []
    with pytest.raises(ValueError, match='proportions'):
        check(doc_with(bad))
    bad = copy.deepcopy(BRICK)
    bad['size'] = [{'part': 'brick', 'measure': 'length', 'value': 190, 'unit': 'mm', 'status': 'confirmed', 'source': 'x'}]
    with pytest.raises(ValueError, match='sizes live in its material_spec'):
        check(doc_with(bad))
    plain = {**BRICK, 'kind': 'object', 'material_spec': None}
    check(doc_with(plain))   # an object that does not repeat needs none


# ---------- the sentence, the ratio and the lines ----------

def test_the_server_writes_the_spec_sentence_and_the_measured_must_line():
    s = VS.material_sentence(BRICK)
    assert s == ('Material spec, Red brick: brick length 190 mm, brick width 90 mm, brick height 90 mm, joint thickness 10 mm; laid on edge, header ends to the camera; joints 10 mm mortar joints; '
                 'pattern: one long face alternating with one header per course; courses offset by half a header; proportions: long face a little more than twice as wide as tall; header end a square.')
    assert VS.material_ratio(BRICK_SPEC) == '2.1 : 1'
    lines = VS.material_lines(BRICK)
    assert lines == [{'check': 'material: Red brick', 'weight': 'must',
                      'pass_when': 'measured on three units, the long face is 2.1 : 1 (length to height) and the units are laid on edge, header ends to the camera; across three courses the pattern is: '
                                   'one long face alternating with one header per course; courses offset by half a header; joints 10 mm mortar joints'}]
    assert VS.material_ratio({'dimensions': [{'part': 'tile', 'measure': 'length', 'value': 300, 'unit': 'mm', 'status': 'confirmed', 'source': 's'}]}) == ''


def test_the_prompt_check_refuses_relative_size_words_for_a_material():
    for bad in ('A wall of short bricks.', 'Long bricks in running bond.', 'The bricks are about 2:1.', 'Roughly square headers.', 'A standard brick wall.', 'Typical red bricks, approximately square.'):
        with pytest.raises(ValueError, match='relative'):
            L.check_material_prompt(bad)
    for ok in ('The long face a little more than twice as wide as tall.', 'A long wall of bricks 190 mm long.', 'Bricks on edge, header ends to the camera.'):
        L.check_material_prompt(ok)


# ---------- approval, once, on the References step ----------

def material_store():
    store = start_store()
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    doc['elements'].append(copy.deepcopy(BRICK))
    doc['gaps'][1]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'BRICK']
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    s['accepted'] = accepted(doc)
    s['bindings']['VS1']['gap_digest'] = s['accepted']['G2']['digest']
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    return store


def test_the_material_spec_is_approved_once_corrected_through_rule_0_and_shown_everywhere():
    store = material_store()
    st = VS.status(FakeConn([]), store, RUN, [], repair=False)
    assert st['material_specs'] == {'BRICK': {'approved': False, 'correction': None}}
    assert any(w['label'] == 'Material specs · 1 to approve' and w['step'] == 'references' for w in st['waiting'])
    view = VS.page_view(FakeConn([]), store, RUN, [], 'VW-9', False)
    el = next(e for e in view['elements'] if e['id'] == 'BRICK')
    assert el['material_spec']['approved'] is False and el['material_spec']['table'][0]['size'] == '190 mm' and el['material_spec']['sentence'].startswith('Material spec, Red brick')
    VS.correct_spec(store, USER, RUN, [], 'element:BRICK', 'the joint is 12 mm on this site')
    with pytest.raises(Problem, match='waits for the assistant'):
        g(lambda: VS.approve_spec(store, USER, RUN, [], 'element:BRICK', ''))
    assert VS.approve_specs(store, USER, RUN, [], '')['waiting'] == ['element:BRICK']
    s = saved(store)
    s['spec_corrections']['element:BRICK']['digest'] = 'older'
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    out = VS.approve_spec(store, USER, RUN, [], 'element:BRICK', '')
    assert out['element_id'] == 'BRICK' and saved(store)['spec_approvals']['element:BRICK']['digest'] == VS.spec_digest(BRICK_SPEC)
    st = VS.status(FakeConn([]), store, RUN, [], repair=False)
    assert st['material_specs']['BRICK']['approved'] is True and not any('Material specs' in w['label'] for w in st['waiting'])
    assert VS.approve_specs(store, USER, RUN, [], '')['approved'] == []
    with pytest.raises(Problem, match='no material spec'):
        g(lambda: VS.approve_spec(store, USER, RUN, [], 'element:E1', ''))


# ---------- every picture that shows the material carries the sentence; none before the approval ----------

def test_no_picture_of_the_material_before_its_spec_is_approved_then_the_sentence_rides_with_every_prompt(monkeypatch):
    class Down:
        def __init__(self, *a, **k):
            pass

        def generate(self, payload):
            raise RuntimeError('no network in a unit test')
    monkeypatch.setattr(VS, '_gemini_transport', lambda: Down)   # F12's list cannot be built here: the approval stands without it
    store = material_store()
    with pytest.raises(Problem, match='material spec of BRICK is not approved'):
        g(lambda: revise_start(store, role='start'))
    VS.approve_spec(store, USER, RUN, [], 'element:BRICK', '')
    rid = revise_start(store, role='start')['reference_id']
    row = saved(store)['references'][rid]
    assert row['generation']['prompt'].count('Material spec, Red brick:') == 1 and [l['check'] for l in row['server_checklist'] if l['check'].startswith('material')] == ['material: Red brick']
    with pytest.raises(Problem, match='relative'):
        g(lambda: revise_start(store, role='start', request_id='r-short', prompt='Image 1 is the old start; short bricks on the course.'))
    sheet = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'r-sheet', 'element_id': 'BRICK', 'name': 'sheet-BRICK', 'kind': 'sheet', 'subject': 'the brick',
                                                                   'prompt': 'Image 1 is the footage frame; one reference sheet of the brick.', 'parents': ['R1']})
    assert 'Material spec, Red brick:' in saved(store)['references'][sheet['reference_id']]['generation']['prompt']


def test_the_page_and_the_tool_know_the_material_spec():
    assert 'data-a="approve-spec" data-shot="element:' in PAGE and 'Approve the material spec' in PAGE and "id=\"sp-c-element:'+esc(e.id)+'\"" in PAGE
    proc = (ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8')
    assert 'material_spec' in proc and 'vw visuals spec --element' in proc
