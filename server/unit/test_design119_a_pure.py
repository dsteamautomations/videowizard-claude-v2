"""design/119 set A. Rule 5: a reference goes in only when its thing is in the shot (the style, a person in frame and the start chain excepted).
Rule 6: every element's known sizes are written into the prompt as numbers beside its name. Rule 3: a reference of another thing, sent for its look,
gets an exclusion line built from its own stored Details sentence."""
import json

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design106_pure import revise_start
from test_design111_f11_pure import golden_store, put
from test_visuals_stage_pure import g, ref, saved


def store_with_extras():
    store = golden_store(with_frame=False)   # E2 without its footage frame, so the L41 parent rule stays out of these tests
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    doc['elements'].append({'id': 'E3', 'name': 'Bicycle', 'kind': 'object', 'identity': 'representative', 'requirements': 'a black roadster'})
    doc['elements'][0]['size'] = [{'part': 'block', 'measure': 'length', 'value': 290, 'unit': 'mm', 'source': 'maker sheet', 'status': 'confirmed'},
                                  {'part': 'block', 'measure': 'height', 'value': None, 'unit': 'mm', 'source': '', 'status': 'unknown', 'tried': 'nothing shows it'}]
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    s['references']['P3'] = {**ref('P3', 'approved'), 'kind': 'isolated', 'element_id': 'E3'}
    s['references']['ST1'] = {**ref('ST1', 'approved'), 'kind': 'style', 'element_id': VS.STYLE}
    s['references']['L2'] = {**ref('L2', 'approved'), 'kind': 'isolated', 'element_id': 'E2',
                             'generation': {'op': 'edit', 'parents': [], 'prompt': 'Asset: the yard. Layout: the wall across the frame. Details: a parked bicycle and a clay water pot at the edge of the lane, '
                                                                                     'a white kolam on the swept ground; deep focus, sharp, 28mm feel, natural colour. Constraints: no people, no readable text.'}}
    put(store, s)
    return store


def three(third, line):
    return {'role': 'start', 'parents': ['K1', 'R1', third], 'prompt': "Image 1 is the old start; the labourer at the stack, the lane behind. Image 2 is the labourer's sheet: take identity from it, nothing else. " + line}


def test_a_reference_of_a_thing_not_in_the_shot_is_refused_by_name_and_the_style_is_not():
    store = store_with_extras()
    with pytest.raises(Problem, match='P3 is a picture of E3 \\(Bicycle\\), which is not in shot VS1'):
        g(lambda: revise_start(store, **three('P3', 'Image 3 is the bicycle: take its shape.')))
    out = revise_start(store, **three('ST1', 'Image 3 is the style: take its palette.'))
    assert out['reference_id']


def test_known_sizes_are_written_into_the_prompt_beside_the_thing_and_an_unknown_one_is_not():
    store = store_with_extras()
    out = revise_start(store, role='start')
    prompt = saved(store)['references'][out['reference_id']]['generation']['prompt']
    assert 'Sizes: Wall section: block length 290 mm' in prompt and 'height' not in prompt.split('Sizes:')[1].split('\n')[0]
    assert VS.size_sentence({'name': 'Broom', 'size': [{'part': 'broom', 'measure': 'length', 'value': 600, 'unit': 'mm'}, {'part': 'head', 'measure': 'width', 'value': 0.2, 'unit': 'm'}]}) == 'Broom: broom length 600 mm, head width 0.2 m'
    assert VS.size_sentence({'name': 'Peg', 'size': [{'part': 'peg', 'measure': 'length', 'value': None}]}) == ''


def test_a_look_reference_of_another_thing_gets_an_exclusion_line_from_its_own_details():
    store = store_with_extras()
    out = revise_start(store, **three('L2', "Image 3 is the wall's picture: take its light and air, nothing else."))
    prompt = saved(store)['references'][out['reference_id']]['generation']['prompt']
    assert 'Image 3 also shows a parked bicycle, a clay water pot at the edge of the lane, a white kolam on the swept ground: show none of them' in prompt
    assert '28mm' not in prompt.split('Image 3 also shows')[1].split('\n')[0]   # camera notes are not things
    r = saved(store)['references']['L2']
    assert VS.also_shows(r, own=['bicycle']) == ['a clay water pot at the edge of the lane', 'a white kolam on the swept ground']   # the shot's own things stay allowed
    assert VS.also_shows({**r, 'generation': {'prompt': 'no details block here'}}, own=[]) == [] and VS.also_shows({'kind': 'frame'}, own=[]) == []
