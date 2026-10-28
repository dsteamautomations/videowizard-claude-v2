"""design/119 set E. Rule 7: a thing whose fact or size cites the footage is identity exact with an approved frame before any picture of it (the plan
warns, the References step refuses). Rule 8: a height word in a layout is a must line and a prompt sentence; a thing with an approved frame and an
unknown size is measured before its first picture. Rule 9: a passer-by is never a named element (the plan warns)."""
import json
from fractions import Fraction

import pytest

from app import visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design106_pure import revise_start
from test_design111_f11_pure import golden_store, image, put
from test_visuals_pure import GAPS, plan, shot as pshot
from test_visuals_stage_pure import accepted, g, ref, saved


def kinds(d):
    return {(w.get('shot_id') or w.get('element_id'), w.get('kind')) for w in VC.validate_plan(d, GAPS, Fraction(25))[1]}


def two_videos():
    return plan([pshot('VS1', 0, 500, 'video'), pshot('VS2', 500, 1000, 'video')])


def test_the_plan_warns_when_a_things_fact_or_size_cites_the_footage_and_it_is_not_exact():
    d = two_videos()
    d['elements'].append({'id': 'PL', 'name': 'Plinth top', 'kind': 'object', 'identity': 'representative', 'requirements': 'a flat plinth top',
                          'size': [{'part': 'plinth', 'measure': 'height', 'value': None, 'unit': 'mm', 'source': 'Footage frame f9c75 shows the broom on it', 'status': 'unknown', 'tried': 'not measured yet'}]})
    assert ('PL', 'footage_identity') in kinds(d)
    d['elements'][-1]['identity'] = 'exact'
    assert ('PL', 'footage_identity') not in kinds(d)
    d['elements'][-1].update(identity='representative', size=[{'part': 'plinth', 'measure': 'height', 'value': 450, 'unit': 'mm', 'source': 'COSTFORD manual', 'status': 'confirmed'}])
    assert ('PL', 'footage_identity') not in kinds(d)   # a standard, not the footage
    d['visual_facts'] = [{'id': 'F_PL', 'about': 'PL', 'looks': 'swept and wetted', 'how': 'broom', 'source': 'broom observed in footage f9c75', 'status': 'observed'}]
    assert ('PL', 'footage_identity') in kinds(d)   # the fact cites it


def test_the_plan_warns_when_a_person_element_is_a_passer_by():
    d = two_videos()
    d['elements'].append({'id': 'PB', 'name': 'Passer-by', 'kind': 'person', 'identity': 'representative', 'requirements': 'a man walking by in the background'})
    assert ('PB', 'passer_by') in kinds(d)
    d['elements'][-1]['requirements'] = 'the mason who lays the wall'
    assert ('PB', 'passer_by') not in kinds(d)


def cited_store(with_frame, value=450):
    store = golden_store(with_frame=with_frame)
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    e2 = next(e for e in doc['elements'] if e['id'] == 'E2')
    e2['size'] = [{'part': 'course', 'measure': 'height', 'value': value, 'unit': 'mm', 'source': 'footage frame F2, read against a brick', 'status': 'measured' if value else 'unknown', 'tried': 'measure not run'}]
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    return store


def test_a_picture_of_a_footage_cited_thing_needs_its_approved_frame():
    with pytest.raises(Problem, match='E2.*cites the footage.*approve a footage frame of E2'):
        g(lambda: image(cited_store(with_frame=False)))
    out = image(cited_store(with_frame=True), parents=['S2', 'F2'], prompt='Image 1 is the sheet of the wall. Image 2 is the footage frame: take its brick. The wall in its yard.')
    assert out['reference_id']


def test_a_thing_with_a_frame_and_an_unknown_size_is_measured_before_its_first_picture():
    with pytest.raises(Problem, match='E2 has a size still unknown \\(course height\\) and an approved footage frame F2: measure it first'):
        g(lambda: image(cited_store(with_frame=True, value=None), parents=['S2', 'F2'], prompt='Image 1 is the sheet of the wall. Image 2 is the footage frame: take its brick. The wall.'))
    out = image(cited_store(with_frame=True, value=None), kind='sheet', name='sheet2', parents=['F2'], prompt='Image 1 is the footage frame: take the wall.', request_id='q-sheet')   # the sheet comes before the measure
    assert out['reference_id']


def test_height_words_in_a_layout_become_a_line_and_a_sentence():
    assert VS.height_lines({'layout': 'A plinth top runs across the frame at knee height; a bucket of water stands at its left end.'}) == \
        [{'check': 'plinth top at knee height', 'weight': 'must', 'pass_when': "the plinth top reaches a standing person's knee and no higher; the rest of the person is above it, feet on the same ground"}]
    assert [l['check'] for l in VS.height_lines({'layout': 'A waist-high rat-trap wall runs across; the mason stands behind it.'})] == ['rat-trap wall at waist height']
    assert VS.height_lines({'layout': 'A man of medium height sweeps the yard.'}) == [] and VS.height_lines({}) == []
    assert VS.height_sentence({'layout': 'A plinth top runs across the frame at knee height.'}) == "Heights: the plinth top reaches a standing person's knee and no higher; the rest of the person is above it, feet on the same ground."
    store = golden_store(with_frame=False)
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    doc['gaps'][1]['scenes'][0]['layout'] = 'A plinth top runs across the frame at knee height; the stack behind it.'
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    s['accepted'] = accepted(doc)   # the layout changed the gap's digest: accept it again, as the operator would
    s['bindings']['VS1']['gap_digest'] = s['accepted']['G2']['digest']
    put(store, s)
    out = image(store, shot_id='VS1', request_id='q-height')   # a picture of E2 (an object) for shot VS1: the scene's lines apply (a graphic's picture gets none)
    r = saved(store)['references'][out['reference_id']]
    assert 'plinth top at knee height' in [l['check'] for l in r['server_checklist']] and "Heights: the plinth top reaches a standing person's knee" in r['generation']['prompt']
