"""The sweep of 31 Oct 2026 (design/126 W3-W6, W12): a fix starts from its candidate whatever its kind, a fix's answer is checked without
its exact texts (the server adds them after), a drawn shot is pointed at `vw visuals draw` and never takes a take, and the end image's
next line names its element."""
import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design111_f11_pure import golden_store, image, put
from test_visuals_stage_pure import ref, saved

ANSWER = {'status': 'ready', 'prompt': 'Image 1 is the sheet of the wall. The wall in its yard.',
          'checklist': [{'check': 'the wall', 'weight': 'must', 'pass_when': 'the wall'}],
          'exact_text': [{'text': 'RAT TRAP BOND', 'place': {'region': 'top centre'}, 'size_pct': 6}]}


def candidate_store():
    store = golden_store()
    s = saved(store)
    s['references']['C2'] = {**ref('C2', 'candidate'), 'kind': 'isolated', 'element_id': 'E2'}
    put(store, s)
    return store


def test_a_fix_of_an_isolated_candidate_is_made_from_it():   # W4
    store = candidate_store()
    out = image(store, parents=['C2'], fix_of='C2', prompt='Image 1 is the picture to fix: keep everything; make the wall straight.')
    assert saved(store)['references'][out['reference_id']]['generation']['parents'][0]['id'] == 'C2'


def test_a_candidate_that_is_not_the_one_fixed_is_still_refused():   # W4: nothing else loosened
    store = candidate_store()
    with pytest.raises((Problem, ValueError), match='approved references'):
        image(store, parents=['C2'], prompt='Image 1 is the sheet of the wall. The wall in its yard.')


def test_a_fix_with_an_answer_holding_exact_text_is_accepted():   # W5
    store = candidate_store()
    fix_prompt = 'Image 1 is the picture to fix: keep everything; make the wall straight.'
    image(store, parents=['C2'], fix_of='C2', prompt=fix_prompt, answer={**ANSWER, 'prompt': fix_prompt})


def test_a_drawn_shot_is_pointed_at_draw():   # W6
    with pytest.raises((Problem, ValueError), match='vw visuals draw'):
        VS._route_gate({'id': 'D1', 'visual_type': 'drawn'}, 'still')


def test_a_drawn_shot_never_takes_a_take(monkeypatch):   # W3
    monkeypatch.setattr(VS, 'session_of', lambda store, run, outputs: {'preparations': {'D1': {'drawn': True, 'key': 'k'}}})
    with pytest.raises((Problem, ValueError), match='rendered with `vw visuals draw --shot D1`'):
        VS.submit_take(None, None, {'id': 'u'}, {'id': 'r'}, [], 'D1')


def test_the_end_images_next_line_names_its_element():   # W12
    src = open(VS.__file__, encoding='utf-8').read()
    assert "`vw visuals image --element {row.get('element_id')} --kind keyframe --role end --parents {row['id']}" in src
