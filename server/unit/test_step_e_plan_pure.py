"""Integration step E, the plan check for an AI video shot: the guide take's limits (3 to 15 s; a short cut of 1 s or more on screen), one still per
shot, at most four people, no circling camera, a transfer as its own close shot ending in the hand. The older tests of the changed rules are
updated in place and marked 'integration step E'."""
import copy
from fractions import Fraction

import pytest

from app import visual_contract as VC, video_generators as VG
from test_design124_b_pure import base, check, vs1
from test_visuals_pure import GAPS, plan, shot


def refused(d):
    with pytest.raises(ValueError) as e:
        check(d)
    return str(e.value)


def test_the_plan_reads_the_take_limits_from_the_one_place_they_are_stated():
    assert VC._default_generator() is VG.GUIDE and (VG.GUIDE['min_seconds'], VG.GUIDE['max_seconds']) == (3, 15)
    assert VC.VIDEO_MIN_ON_SCREEN_S == 1 and VC.take_seconds(1.9) == 3 and VC.take_seconds(14.2) == 15


def test_every_ai_video_shot_counts_one_still_whatever_its_end_state():
    doc = plan([shot('VS1', 0, 250, 'video'), shot('VS2', 250, 500, 'video'), shot('VS3', 500, 1000, 'video')])
    plain = VC.routes(doc)['images_estimated']
    for s in doc['gaps'][0]['scenes'][0]['shots']:
        s['end_state_exact'] = True
    assert VC.routes(doc)['images_estimated'] == plain   # no end picture, no start shared with the shot before


def test_a_camera_that_circles_a_person_is_refused_and_a_pan_is_not():
    d = base()
    vs1(d)['camera_move'] = 'a slow orbit around the mason'
    assert 'a camera that circles a person is not made' in refused(d)
    vs1(d)['camera_move'] = 'it turns slowly to the left to follow her'
    check(d)


def test_more_than_four_people_in_one_ai_video_shot_is_refused():
    d = base()
    person = next(e for e in d['elements'] if e.get('kind') == 'person')
    mason = next(s for s in vs1(d)['subjects'] if s['element_id'] == person['id'])
    for n in range(4):
        d['elements'].append({**copy.deepcopy(person), 'id': f'W{n}', 'name': f'Worker {n}'})
        vs1(d)['subjects'].append({**copy.deepcopy(mason), 'element_id': f'W{n}', 'role': 'secondary'})
        vs1(d)['element_ids'].append(f'W{n}')
        for sc in [sc for g in d['gaps'] for sc in g.get('scenes') or []]:
            if sc.get('outfit') is not None:
                sc['outfit'][f'W{n}'] = sc['outfit'].get(person['id'], 'a grey cotton shirt')
    said = refused(d)
    assert 'has 5 people; an AI video shot holds at most 4' in said and 'a crowd is not yet available' in said


def test_a_transfer_is_its_own_close_shot_and_ends_in_the_hand():
    d = base()
    vs1(d)['recipe'] = 'transfer_close'
    vs1(d)['size'] = 'WS'
    assert 'a transfer (a pour, a pick-up, a hand-over) is its own close shot' in refused(d)
    vs1(d)['size'] = 'CU'
    if any(p['end']['where'] == 'set_down' for p in vs1(d)['props']):
        assert 'a transfer ends before the set-down' in refused(d)
    for p in vs1(d)['props']:
        p['end'] = {'where': 'in_hand'}
    assert 'transfer' not in ' '.join(e for e in _errors(d))


def _errors(d):
    try:
        check(d)
        return []
    except ValueError as e:
        return [str(e)]


def test_a_kind_of_shot_with_no_recipe_cannot_be_named_in_the_plan():
    d = base()
    vs1(d)['recipe'] = 'crowd_crossing'
    with pytest.raises(Exception):
        check(d)
    vs1(d)['recipe'] = 'walker'
    check(d)


# ---------- the treatment's cost, and the instructions ----------

def test_the_takes_likely_to_be_made_again_are_shown_beside_the_estimate():
    from app import visuals_stage as VS
    assert VS.RERUN_SHARE == 0.3 and VS.rerun_allowance(40, {'video_inr_per_s': 8.0}) == 96.0 and VS.rerun_allowance(0, {'video_inr_per_s': 8.0}) == 0.0
    import inspect
    assert "'rerun_allowance_inr': rerun_allowance(video_seconds, pr)" in inspect.getsource(VS.treatment)


def test_the_instructions_say_fifteen_seconds_the_guide_and_no_longer_teach_the_older_take():
    import json
    from pathlib import Path
    st = next(s for s in json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
    text = ' '.join([st['prompt'], *st['steps'], *(p['text'] for p in st['parts'])])
    assert 'A take is 3 to 15 seconds' in text and 'AI video 1 to 15 s on screen' in text and 'every take is an edit of a guide, 3 to 15 s' in text and '(the 15 s limit and' in text
    assert '`vw:guide` skill' in text and '`vw guide shoot --shot S --quote' in text and 'vw guide cause' in text and 'one still per AI video shot' in text
    for gone in ('3 to 10 s', '2 to 10 s', 'makes 3 to 10 seconds', 'vw visuals prepare-take --shot S --start', 'vw visuals take --shots all', 'never a start image before the packet', 'clip-from-frame'):
        assert gone not in text, gone
    assert 'not yet available as AI video' in text and 'two rejected takes from one camera' in text
