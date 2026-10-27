"""design/111 F17: several of a kind in frame are a group, same or different, said in the plan; the server writes the layout line and two must lines;
when a picture with background figures is approved, one Gemini question compares its figures with the approved pictures of the same scene."""
import copy
import json
import types
from fractions import Fraction

import pytest

from app import visual_contract as VC, visuals_stage as VS
from test_design106_pure import approvable, start_store
from test_design110_f456_pure import doc_with, rich
from test_visuals_pure import GAPS, shot as pshot
from test_visuals_stage_pure import RUN, USER, FakeConn, saved


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def test_several_of_a_kind_need_a_group_entry_same_with_a_reason_or_different_with_a_trait_each():
    sh = rich()
    d = doc_with(sh, pshot('VS2', 500, 1000, 'video'))
    sh = d['gaps'][0]['scenes'][0]['shots'][0]
    sh['groups'] = []
    with pytest.raises(ValueError, match="shot VS1 shows several BRICK .* give groups"):
        check(d)
    sh['groups'] = [{'kind': 'BRICK', 'count': 4, 'mode': 'same', 'reason': ''}]
    with pytest.raises(ValueError, match='BRICK are all alike: give the reason'):
        check(d)
    sh['groups'] = [{'kind': 'BRICK', 'count': 4, 'mode': 'same', 'reason': 'one kiln batch'}]
    check(d)
    sh['framing'] = 'wide, three workers behind the wall'
    with pytest.raises(ValueError, match="shot VS1 shows several workers .* give groups"):
        check(d)
    sh['groups'].append({'kind': 'workers', 'count': 3, 'mode': 'different', 'items': ['a tall one in a red cap']})
    with pytest.raises(ValueError, match='workers are 3 and different: give one trait each'):
        check(d)
    sh['groups'][-1]['items'] += ['a stooped one with a towel on the shoulder', 'a young one carrying a pan']
    check(d)


def test_the_server_writes_the_group_lines_and_the_two_must_lines():
    d = doc_with(rich())
    scene, sh = d['gaps'][0]['scenes'][0], d['gaps'][0]['scenes'][0]['shots'][0]
    sh['groups'] = [{'kind': 'BRICK', 'count': 4, 'mode': 'same', 'reason': 'one kiln batch'},
                    {'kind': 'workers', 'count': 3, 'mode': 'different', 'items': ['a tall one in a red cap', 'a stooped one with a towel', 'a young one with a pan']}]
    lines = VS.group_lines(d, sh)
    assert lines == ['Every Red brick: all alike (one kiln batch).', '3 workers: no two alike: a tall one in a red cap; a stooped one with a towel; a young one with a pan.']
    assert all(l in VS.composed_block(d, scene, sh, 'start') and l in VS.composed_block(d, scene, sh, 'end') for l in lines)
    by = {l['check']: l for l in VS.picture_rule_lines(d, scene, sh, 'start')}
    assert 'group count: Red brick' not in by   # the inventory counts an element; the count line is for a group of no element
    assert by['group alike: Red brick']['weight'] == 'must' and 'all alike' in by['group alike: Red brick']['pass_when']
    assert by['group count: workers']['pass_when'].startswith('exactly 3 workers') and 'no two alike' in by['group alike: workers']['pass_when'] and 'red cap' in by['group alike: workers']['pass_when']
    assert VS.group_lines(d, {**sh, 'groups': []}) == []


def test_background_figures_are_compared_with_the_approved_pictures_of_the_scene_at_approval(monkeypatch):
    d = doc_with(rich())
    scene, sh = d['gaps'][0]['scenes'][0], d['gaps'][0]['scenes'][0]['shots'][0]
    assert VS._has_figures(d, sh) is True   # the cow in the background
    assert VS._has_figures(d, {**sh, 'subjects': sh['subjects'][:1]}) is False

    class Transport:
        calls = []

        def __init__(self, key, model, **kw):
            Transport.model = model

        def generate(self, payload):
            Transport.calls.append(payload)
            return {'body': {'repeated': True, 'detail': 'the cow at the right is the same animal as in Picture 1'}, 'raw': ''}
    monkeypatch.setattr(VS, '_gemini_transport', lambda: Transport)
    real = VS.settings()

    class Settings:
        GEMINI_API_KEY = types.SimpleNamespace(get_secret_value=lambda: 'k')

        def __getattr__(self, name):
            return getattr(real, name)
    monkeypatch.setattr(VS, 'settings', lambda: Settings())
    store = start_store()
    s = saved(store)
    s['references']['K1'].update(key='run-1/visuals/references/K1.png')
    s['references']['K0'] = {**s['references']['K1'], 'id': 'K0', 'name': 'K0', 'shot_id': 'VS1', 'key': 'run-1/visuals/references/K0.png', 'status': 'rejected'}   # rejected: not compared
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    store.files['run-1/visuals/references/K1.png'] = b'png1'
    store.files['run-1/visuals/references/K0.png'] = b'png0'
    row = {'id': 'N1', 'kind': 'keyframe', 'shot_id': 'VS1', 'key': 'run-1/visuals/references/N1.png'}
    store.files['run-1/visuals/references/N1.png'] = b'pngN'
    rec = VS.figure_repeat(store, saved(store), row, {'shots': [{'id': 'VS1'}]})
    assert rec['against'] == ['K1'] and rec['repeated'] is True and 'same animal' in rec['detail'] and Transport.model == VS.image_check.CHECK_MODEL
    texts = ' '.join(p.get('text', '') for p in Transport.calls[0]['contents'][0]['parts'])
    assert 'Picture 1 (K1)' in texts and 'The new picture' in texts and 'background and secondary figures' in texts
    assert VS.figure_repeat(store, saved(store), row, {'shots': [{'id': 'VS9'}]}) is None   # nothing approved in that scene: no call
    # the approval wires it: the record lands on the row and status lists the repeat
    called = []
    monkeypatch.setattr(VS, '_has_figures', lambda plan, shot: True)
    monkeypatch.setattr(VS, 'figure_repeat', lambda store_, session_, row_, scene_: called.append(row_['id']) or {'against': ['K1'], 'repeated': True, 'detail': 'the same cow'})
    rid = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'r11', 'element_id': 'E1', 'name': 'end-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer',
                                                                'prompt': 'Image 1 is the start; the labourer at the edge.', 'parents': ['K1']})['reference_id']   # an end: no second start
    VS.approve_reference(approvable(store, rid), USER, RUN, [], rid, 'a' * 64, '', FakeConn([]))
    assert called == [rid] and saved(store)['references'][rid]['figure_check']['repeated'] is True
    assert VS.status(FakeConn([]), store, RUN, [], repair=False)['figure_repeats'] == [{'reference_id': rid, 'shot_id': 'VS1', 'detail': 'the same cow'}]
