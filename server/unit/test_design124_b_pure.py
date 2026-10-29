"""design/124 Phase B (design/124-b-film-types.md): the server side of the approved film-type fixes and SK's decisions (a) and (c).
Each test names its item. Every rule keeps firing where it is right; only the misfire is cut."""
import copy
import json
from fractions import Fraction

import pytest

from app import visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design110_f456_pure import doc_with, rich
from test_design91_b1_pure import video
from test_design124_a3a4_pure import person_store
from test_design111_f11_pure import image
from test_visuals_pure import GAPS, plan, shot as pshot, states
from test_visuals_stage_pure import RUN, USER, TREATMENT, g, saved, session, store_with


def check(d, **kw):
    return VC.validate_plan(d, GAPS, Fraction(25), **kw)


def kinds(d, **kw):
    return {(w.get('shot_id') or w.get('scene_id') or w.get('element_id') or w.get('gap_id'), w['kind']) for w in check(d, **kw)[1]}


def base():
    """A 10 s video shot of the mason (E1, a person) with a grazing cow, then a still of him."""
    return doc_with(rich('VS1', 0, 250), pshot('IM1', 250, 1000, 'image'))


def vs1(d):
    return d['gaps'][0]['scenes'][0]['shots'][0]


def scene(d):
    return d['gaps'][0]['scenes'][0]


def person(pid, **over):
    return {'id': pid, 'name': pid, 'kind': 'person', 'identity': 'representative', 'requirements': 'a worker', 'description': 'a wiry man of about thirty', **over}


def held(eid, role='background'):
    st = {'position': {'landmark_id': 'L1', 'relation': 'behind', 'amount': 3, 'unit': 'paces'}, 'facing': 'left', 'pose': 'bent', 'holding': [], 'progress': 'mixing'}
    return {'element_id': eid, 'role': role, 'screen_position': 'back', 'behaviour': 'holds', 'hold_reason': 'works on', 'start': st, 'end': copy.deepcopy(st)}


def test_the_base_plan_is_valid():
    check(base())


# ---------- item 1: a footage shot ----------

def test_a_footage_shot_skips_the_rules_made_for_generated_pictures():
    d = plan([pshot('FT1', 0, 400, 'footage'), pshot('FT2', 400, 1000, 'footage')])   # 16 s and 24 s of real footage, longer than Omni makes
    out, warns = check(d)
    found = {(w.get('shot_id') or w.get('scene_id'), w['kind']) for w in warns}
    for k in ('still_long', 'camera_reason_missing', 'short_route'):
        assert ('FT1', k) not in found and ('FT2', k) not in found
    assert ('SC1', 'light_missing') not in found and ('SC1', 'activity_missing') not in found
    r = VC.routes(out, 25)
    assert r['footage'] == 2 and r['seconds']['footage'] == 40.0 and r['images_estimated'] == 0 and r['seconds']['video'] == 0
    assert VC.route_of({'visual_type': 'footage'}) == 'footage'
    assert [x['route'] for x in VS.split_of(out['gaps'][0]['scenes'][0]['shots'], 25.0)] == ['footage']
    with pytest.raises(ValueError, match='motion'):   # the still's motion rules are not skipped for a picture that is one: an image keeps them
        check(plan([{**pshot('IM1', 0, 1000, 'image'), 'motion': 'none'}]))


def test_a_footage_shot_takes_a_clip_or_a_footage_frame_and_never_a_take():
    VS._route_gate({'id': 'FT1', 'visual_type': 'footage'}, 'still')
    with pytest.raises(ValueError, match='FT1 is a footage shot'):
        VS._route_gate({'id': 'FT1', 'visual_type': 'footage'}, 'video')


# ---------- decision (a), item 2: a busy scene ----------

def test_more_than_three_background_people_are_a_crowd():
    d = base()
    d['elements'] += [person(f'P{n}') for n in range(1, 5)]
    im = d['gaps'][0]['scenes'][0]['shots'][1]
    im['element_ids'] = ['E1', 'P1', 'P2', 'P3']
    im['subjects'] = [held('P1'), held('P2'), held('P3')]
    scene(d)['outfit'].update({f'P{n}': 'grey vest' for n in range(1, 5)})
    check(d)   # three named workers
    im['element_ids'].append('P4')
    im['subjects'].append(held('P4'))
    with pytest.raises(ValueError, match='4 background people .* a crowd: .*ambient.* groups'):
        check(d)


def test_a_crowd_is_one_varied_group_with_a_few_traits_and_life_missing_accepts_it():
    d = base()
    scene(d)['activity_level'] = 'busy'
    vs1(d)['subjects'] = vs1(d)['subjects'][:1]   # the mason alone, the cow gone
    vs1(d)['element_ids'] = ['E1', 'TROWEL', 'BRICK']
    assert ('SC1', 'life_missing') in kinds(d)
    scene(d)['ambient'] = 'workers mixing and carrying in the background'
    vs1(d)['groups'].append({'kind': 'workers', 'count': 20, 'mode': 'varied', 'items': ['a red cap']})
    with pytest.raises(ValueError, match='a few traits'):
        check(d)
    vs1(d)['groups'][-1]['items'] = ['a red cap', 'a towel on the shoulder', 'a head pan']
    assert ('SC1', 'life_missing') not in kinds(d)
    lines = VS.group_lines(d, vs1(d))
    assert lines[-1] == '20 workers, varied, the traits in turn: a red cap; a towel on the shoulder; a head pan.'
    rule = {l['check']: l for l in VS.group_rule_lines(d, vs1(d))}
    assert 'a red cap' in rule['group alike: workers']['pass_when'] and rule['group count: workers']['pass_when'].startswith('about 20 workers')
    del scene(d)['ambient']
    assert ('SC1', 'life_missing') in kinds(d)   # the group alone is not the crowd; the ambient line is half of it


def test_passer_by_does_not_fire_on_an_element_with_beats():
    d = base()
    d['elements'][0]['requirements'] = 'a mason laying bricks in the background'
    d['elements'].append(person('P9', requirements='a man walking by'))
    found = kinds(d)
    assert ('E1', 'passer_by') not in found and ('P9', 'passer_by') in found


# ---------- item 3: a living thing that holds ----------

def test_a_living_thing_that_holds_keeps_its_place_when_its_small_life_is_named():
    d = base()
    cow = vs1(d)['subjects'][1]
    cow['end']['position'] = copy.deepcopy(cow['start']['position'])
    with pytest.raises(ValueError, match='stands still'):
        check(d)
    cow['hold_reason'] = 'it lies chewing; its tail and ears flick'
    check(d)
    cow['start']['pose'] = cow['end']['pose'] = 'standing'
    scene(d)['activity_level'] = 'busy'
    with pytest.raises(ValueError, match='stands still'):   # a standing figure in a busy scene keeps the body-length move
        check(d)


# ---------- item 4: a place staged clean ----------

def test_a_place_staged_clean_needs_no_signs_of_use_and_gets_the_clean_line():
    d = base()
    d['elements'].append({'id': 'FLAT', 'name': 'The new flat', 'kind': 'place', 'identity': 'exact', 'requirements': 'the handed-over flat'})
    d['gaps'][0]['scenes'][0]['shots'][1]['element_ids'].append('FLAT')
    with pytest.raises(ValueError, match='FLAT is a place the film shows: give signs_of_use'):
        check(d)
    d['elements'][-1]['staged_clean'] = 'the film shows the flat at handover, spotless'
    out, _ = check(d)
    assert out['elements'][-1]['staged_clean'].startswith('the film shows')
    assert VS.place_line(out, 'FLAT', out['gaps'][0]['scenes'][0]['shots'][1])['pass_when'].startswith('clean and unused, as planned')
    assert VS.place_line(out, 'E1', vs1(out)) is None
    d['elements'][-1].pop('staged_clean')
    d['elements'][-1]['signs_of_use'] = [{'what': 'a bucket', 'landmark_id': 'L1'}, {'what': 'a broom', 'landmark_id': 'L1'}]
    out, _ = check(d)
    assert VS.place_line(out, 'FLAT', out['gaps'][0]['scenes'][0]['shots'][1]) == VS.OCCUPIED
    assert 'staged_clean' not in out['elements'][-1]   # absent stays absent


# ---------- item 5: ordinary words are no technique ----------

def test_a_gesture_or_a_noun_is_no_technique_and_the_working_verb_still_is():
    for words in ('the engineer points at the crack', 'points to the gate', 'picks up the drill', 'adjusts his tie', 'dips the brush in paint', 'wipes a polish off'):
        assert VC.technique_words(words) == [], words
    assert VC.technique_words('points the joint with a trowel') == ['pointing']
    assert VC.technique_words('drills a hole, then paints the frame') == ['drilling', 'painting']


# ---------- item 6: size words ----------

def test_size_words_skip_graphics_and_drop_light_less_fewer_short():
    d = plan([{**pshot('IM1', 0, 100, 'image'), 'descriptors': ['a light, airy room', 'a short walk']}, pshot('IM2', 100, 1000, 'image')])
    check(d)
    d['gaps'][0]['scenes'][0]['shots'][0]['descriptors'] = ['a smaller block']
    with pytest.raises(ValueError, match='about size'):
        check(d)
    dg = plan([{**pshot('DG1', 0, 100, 'diagram'), 'claims': ['a much bigger saving'], 'depicts': 'two piles'}, pshot('IM2', 100, 1000, 'image')])
    check(dg)


# ---------- item 7: a title or text card is no unbuilt graphic ----------

def test_a_title_or_text_card_held_long_is_not_graphic_unbuilt():
    for kind, warned in (('text', False), ('title', False), ('diagram', True)):
        d = plan([{**pshot('DG1', 0, 150, 'diagram'), 'graphic_kind': kind}, pshot('IM2', 150, 1000, 'image')])
        assert (('DG1', 'graphic_unbuilt') in kinds(d)) is warned, kind


# ---------- item 8: close means a close shot ----------

def test_the_close_refusal_reads_the_size_and_the_subjects_facts():
    d = plan([{**pshot('IM1', 0, 100, 'image'), 'framing': 'wide, the gate closed'}, pshot('IM2', 100, 1000, 'image')])
    d['visual_facts'] = [{'id': 'F1', 'about': 'E1', 'looks': 'how it is pressed', 'status': 'unknown'}]
    check(d)
    d['gaps'][0]['scenes'][0]['shots'][0]['size'] = 'CU'
    with pytest.raises(ValueError, match='close on what fact F1'):
        check(d)
    d['elements'].append({'id': 'E2', 'name': 'Shed', 'kind': 'object', 'identity': 'representative', 'requirements': 'a shed'})
    sh = d['gaps'][0]['scenes'][0]['shots'][0]
    sh['element_ids'] = ['E2', 'E1']   # E2 the subject, E1 in the background
    sh['subjects'] = [{'element_id': 'E2', 'role': 'primary', 'screen_position': 'centre', 'behaviour': 'holds', 'hold_reason': 'a shed',
                       'start': {'position': {'landmark_id': 'L1', 'relation': 'at'}, 'facing': 'front', 'pose': 'stands', 'progress': 'built'},
                       'end': {'position': {'landmark_id': 'L1', 'relation': 'at'}, 'facing': 'front', 'pose': 'stands', 'progress': 'built'}}]
    check(d)


# ---------- item 9: "no workers" ----------

def test_a_negated_group_word_needs_no_group():
    d = base()
    vs1(d)['framing'] = 'empty site at dawn, no workers yet, before the labourers arrive'
    check(d)
    vs1(d)['framing'] = 'wide, three workers behind the wall'
    with pytest.raises(ValueError, match='several workers'):
        check(d)


# ---------- items 10 and the end_state dead weight ----------

def test_no_end_state_warning_and_changes_missing_only_when_a_subject_acts():
    d = base()
    assert not any(k == 'end_state' for _, k in kinds(d))
    acts = plan([video('VS1', 0, 200, [(0, 100, 3), (100, 200, 3)]), pshot('IM2', 200, 1000, 'image')])
    assert ('VS1', 'changes_missing') in kinds(acts)
    amb = plan([{**pshot('VS1', 0, 100, 'video'), 'purpose': 'steam rises because the kiln breathes'}, pshot('IM2', 100, 1000, 'image')])
    assert ('VS1', 'changes_missing') not in kinds(amb)


# ---------- item 11: the footage beside the gap is the wider view ----------

def test_a_close_insert_that_continues_the_footage_place_is_not_warned_for_size():
    d = plan([{**pshot('IM1', 0, 100, 'image'), 'size': 'CU'}, {**pshot('IM2', 100, 1000, 'image'), 'size': 'MS'}])
    assert {('IM1', 'size_open'), ('IM1', 'size_close_first')} <= kinds(d)
    d['gaps'][0]['scenes'][0]['continues_footage'] = True
    found = kinds(d)
    assert ('IM1', 'size_open') not in found and ('IM1', 'size_close_first') not in found
    out, _ = check(plan([pshot('IM1', 0, 1000, 'image')]))
    assert 'continues_footage' not in out['gaps'][0]['scenes'][0]   # absent stays absent


# ---------- item 13: no footage, no footage advice ----------

def test_a_film_with_no_footage_is_not_told_to_use_a_frame_from_the_footage():
    d = plan([{**pshot('VS1', 0, 250, 'video'), 'purpose': 'because it moves'}, {**pshot('VS2', 250, 500, 'video'), 'purpose': 'because it moves'}, pshot('IM1', 500, 1000, 'image')])
    msg = lambda **kw: next(w['message'] for w in check(d, **kw)[1] if w['kind'] == 'ai_run')
    assert 'footage' in msg() and 'footage' not in msg(footage=False)
    gd = plan([{**pshot('DG1', 0, 100, 'diagram'), 'depicts': 'a'}, {**pshot('DG2', 100, 1000, 'diagram'), 'depicts': 'b'}])
    allg = lambda **kw: next(w['message'] for w in check(gd, **kw)[1] if w['kind'] == 'all_graphics')
    assert 'footage' in allg() and 'footage' not in allg(footage=False)


# ---------- item 14: the treatment's seconds per route ----------

def test_a_mixed_gap_counts_its_seconds_per_route_from_its_shots(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    t = copy.deepcopy(TREATMENT)
    t['gaps'][1].update(routes=['footage', 'video', 'graphic_sequence'], seconds=30, images=1, activity_level='lively',
                        shots=[{'id': 'a', 'route': 'footage', 'seconds': 16}, {'id': 'b', 'route': 'video', 'seconds': 6}, {'id': 'c', 'route': 'graphic_sequence', 'seconds': 8}])
    store = store_with(session())
    VS.treatment(store, USER, RUN, [], t, 'Yes.')
    rec = saved(store)['treatment']
    assert rec['totals']['seconds'] == {'graphic_sequence': 28.0, 'footage': 16.0, 'video': 6.0}
    assert rec['estimate_inr'] == (3 + 1) * 20.0 + 6 * 8.0
    t['gaps'][1].pop('shots')   # no seconds per shot: today's sum, the first route
    store = store_with(session())
    VS.treatment(store, USER, RUN, [], t, 'Yes.')
    assert saved(store)['treatment']['totals']['seconds'] == {'graphic_sequence': 20.0, 'footage': 30.0}


# ---------- item 16: fixed landmarks in a close shot ----------

def test_a_close_shot_names_only_the_landmarks_in_frame():
    d = base()
    scene(d)['landmarks'] += [{'id': 'L2', 'description': 'the gate'}, {'id': 'L3', 'description': 'the stack'}]
    vs1(d)['fixed'] = ['L1']
    with pytest.raises(ValueError, match='three fixed things'):
        check(d)
    vs1(d)['size'] = 'ECU'
    check(d)
    vs1(d)['fixed'] = []
    check(d)
    vs1(d)['fixed'] = ['L1', 'L1']
    with pytest.raises(ValueError, match='fixed'):
        check(d)


# ---------- item 17: a look into the lens ----------

def test_a_gaze_at_the_camera_is_accepted():
    d = base()
    sh = vs1(d)
    sh['face_in_frame'] = True
    m = sh['subjects'][0]
    for stt in [m['start'], m['end']] + [x for b in m['beats'] for x in (b['start'], b['end'])]:
        stt['gaze'] = {'target': 'camera', 'head_turn': 'straight to the lens', 'mouth': 'closed smile'}
    check(d)
    m['start']['gaze']['target'] = m['beats'][0]['start']['gaze']['target'] = 'the sky'
    with pytest.raises(ValueError, match='gaze target'):
        check(d)


# ---------- item 19: an idea graphic needs no drawing spec ----------

def test_spec_missing_only_for_a_real_object_or_a_figure():
    d = plan([{**pshot('DG1', 0, 100, 'diagram'), 'depicts': 'heat leaving a house'}, pshot('IM2', 100, 1000, 'image')])
    assert ('DG1', 'spec_missing') in kinds(d)   # E1 is an object: a drawing of it needs its spec
    d['elements'][0]['kind'] = 'process'
    assert ('DG1', 'spec_missing') not in kinds(d)


# ---------- item 20: "on top of that" is no process ----------

def test_carries_over_only_where_a_subject_acts():
    d = plan([{**pshot('IM1', 0, 100, 'image'), 'narration': 'On top of that, the cost falls.'}, {**pshot('IM2', 100, 1000, 'image'), 'narration': 'Once, this was farmland.'}])
    found = kinds(d)
    assert ('IM1', 'carries_over_missing') not in found and ('IM2', 'carries_over_missing') not in found
    d = base()
    d['gaps'][0]['scenes'][0]['shots'][1]['narration'] = 'Then he sets the next course.'   # after an acting shot
    assert ('IM1', 'carries_over_missing') in kinds(d)


# ---------- item 21: "frame" is not footage ----------

def test_a_door_frame_is_not_the_footage():
    d = plan([pshot('IM1', 0, 1000, 'image')])
    d['elements'][0]['size'] = [{'part': 'door', 'measure': 'height', 'value': 2100, 'unit': 'mm', 'source': 'maker sheet, door frame 2100 mm', 'status': 'confirmed'}]
    assert ('E1', 'footage_identity') not in kinds(d)
    d['elements'][0]['size'][0]['source'] = 'clip 3 at 0:12'
    assert ('E1', 'footage_identity') in kinds(d)


# ---------- dead weight: the 30 s cap and the treatment's activity level ----------

def test_the_thirty_second_cap_is_gone():
    assert not hasattr(VC, 'MAX_GENERATED_SHOT_S')


# ---------- decision (c): a real speaker is never an AI picture ----------

def test_a_real_speaker_is_never_an_ai_still_or_take():
    d = base()
    d['elements'][0]['speaker'] = True
    with pytest.raises(ValueError, match='E1 is a real person speaking to camera: .*footage'):
        check(d)
    d = plan([pshot('FT1', 0, 1000, 'footage')])
    d['elements'][0].update(kind='person', description='the client, about sixty', speaker=True)
    d['gaps'][0]['scenes'][0]['outfit'] = {'E1': 'white shirt'}
    out, _ = check(d)
    assert out['elements'][0]['speaker'] is True
    d['elements'][0]['kind'] = 'object'
    with pytest.raises(ValueError, match='speaker'):
        check(d)
    out, _ = check(plan([pshot('IM1', 0, 1000, 'image')]))
    assert 'speaker' not in out['elements'][0]   # absent stays absent


def test_no_ai_picture_of_a_real_speaker_is_made():
    store = person_store()
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    next(e for e in doc['elements'] if e['id'] == 'E4')['speaker'] = True
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    with pytest.raises(Problem, match='real person speaking to camera'):
        g(lambda: image(store, element_id='E4', kind='sheet', name='sheet-E4', subject='the client', parents=[], prompt='The client: about sixty, a white shirt.'))
