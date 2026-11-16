"""design/207 package A (SK, 16 Nov 2026): the plan check after the review of the visuals rules. A1 one fault per shot and the later checks
collected; A2 clothes and time; A3 a real, named person; A4 materials; A5 the size claim; A6 people; A7 circling; A8 drawings; A9 framing;
A10 a look; A11 living extras; A12 the same set-up; A13 any kind of AI video; A14 the kinds other parts raise; A15 generic wording."""
import copy
from fractions import Fraction
from pathlib import Path

import pytest

from app import visual_contract as VC
from test_batch89b_pure import SPEC
from test_design111_f10_pure import BRICK
from test_design111_f19_pure import base as drawing
from test_design124_b_pure import base, held, person, scene, vs1
from test_design148_pure import two_gaps
from test_design149_pure import two_scenes
from test_visuals_pure import GAPS, plan, shot as pshot

SOURCE = (Path(__file__).resolve().parents[1] / 'app' / 'visual_contract.py').read_text(encoding='utf-8')
SIGNS = [{'what': 'a worn step', 'landmark_id': 'L1'}, {'what': 'a coat on the hook', 'landmark_id': 'L1'}]
BAD = {'states': [{'what_appears': 's', 'hold_s': 4}]}   # states on a still: one fault of that shot


@pytest.fixture
def long_shots(monkeypatch):   # the borrowed plans hold 16 to 20 s video shots and test other rules (as conftest.LONG_SHOT_FIXTURES)
    real = VC._default_generator
    monkeypatch.setattr(VC, '_default_generator', lambda: {**real(), 'max_seconds': 60})


def check(d, gaps=GAPS, **kw):
    return VC.validate_plan(d, gaps, Fraction(25), **kw)


def kinds(d, gaps=GAPS):
    return {(w.get('shot_id') or w.get('scene_id') or w.get('element_id') or w.get('gap_id'), w['kind']) for w in check(d, gaps)[1]}


def refused(d, gaps=GAPS):
    with pytest.raises(ValueError) as e:
        check(d, gaps)
    return e.value


def pic(sid, a, b, **over):
    return {**pshot(sid, a, b, 'image'), **over}


def element(eid, kind, **over):
    return {'id': eid, 'name': eid.title(), 'kind': kind, 'identity': 'representative', 'requirements': f'the {eid.lower()} of the film', **over}


def scenes_of(d, *shot_lists):
    """The plan's one gap as one scene per list of shots."""
    first = d['gaps'][0]['scenes'][0]
    d['gaps'][0]['scenes'] = [{**copy.deepcopy(first), 'id': f'SC{n}', 'shots': shots} for n, shots in enumerate(shot_lists, 1)]
    return d


def with_person(d, place=False):
    """E1 becomes a person; with place, a place element ROOM with its signs of use is added."""
    d['elements'][0].update(kind='person', name='Guide', description='a tall woman of about thirty, short black hair')
    for sc in d['gaps'][0]['scenes']:
        sc['outfit'] = {'E1': 'a green coat'}
    if place:
        d['elements'].append(element('ROOM', 'place', signs_of_use=SIGNS))
    return d


# ---------- A1: one fault per shot, and the later checks in the same answer ----------

def test_a_scene_with_faults_in_three_shots_reports_three_faults_in_one_answer():
    e = refused(plan([pic('I1', 0, 300, **BAD), pic('I2', 300, 600, **BAD), pic('I3', 600, 1000, **BAD)]))
    assert str(e).startswith('3 things to fix:\n1. ') and len(e.errors) == 3
    assert [m.split('(shot ')[1][:2] for m in e.errors] == ['I1', 'I2', 'I3']


def test_a_broken_shot_leaves_the_next_shot_checked_on_its_own():
    e = refused(plan([pic('I1', 0, 300, **BAD), pic('I2', 300, 1000)]))
    assert e.errors == ['states belong to an animation shot (shot I1 is a image).']   # the gap's length check is skipped, the next shot is clean
    e = refused(plan([pic('I1', 0, 300), pic('I2', 350, 600), pic('I3', 600, 1000)]))   # I2 leaves 50 frames uncovered; I3 follows I2 and is not blamed for it
    assert e.errors == ['Shots must cover their gap in order, without overlaps or missing frames.']
    e = refused(plan([pic('I1', 0, 300, **BAD), pic('I2', 300, 1000, return_of='I1', differs_by='closer')]))   # a return to a broken shot is no second fault
    assert len(e.errors) == 1


def test_the_later_checks_come_in_the_same_answer_each_recorded():
    d = plan([pic('I1', 0, 300, **BAD), pic('I2', 300, 600, return_of='NOPE', differs_by='closer'), pic('I3', 600, 1000, return_of='I2')])
    d['elements'] += [element('ROOM', 'place'), element('YARD', 'place', signs_of_use=[SIGNS[0], {'what': 'a bucket', 'landmark_id': 'L9'}])]
    for s in d['gaps'][0]['scenes'][0]['shots']:
        s['element_ids'] = ['E1', 'ROOM', 'YARD']
    e = refused(d)
    text = str(e)
    assert text.startswith('5 things to fix:')
    for part in ('shot I1 is a image', 'ROOM is a place the film shows: give signs_of_use', 'YARD: L9 is not a landmark of a scene that shows YARD',
                 'shot I2: return_of names an earlier shot of this plan (NOPE is not one)', 'shot I3 returns to I2: say what differs'):
        assert part in text
    d['gaps'][0]['scenes'][0]['shots'][0].pop('states')   # the later checks alone: still all of them together
    assert len(refused(d).errors) == 4


def test_a_broken_scene_head_does_not_blame_the_places_signs_of_use():
    d = with_person(plan([pic('I1', 0, 1000, element_ids=['E1', 'ROOM'])]), place=True)
    d['gaps'][0]['scenes'][0]['outfit'] = {}
    assert refused(d).errors == ['scene SC1 shows E1: give outfit[E1], the garment colours of this scene.']


# ---------- A2: clothes change when the time changes ----------

def test_a_change_of_clothes_asks_what_changed_in_time(long_shots):
    text = str(refused(two_scenes('a green shirt, a white lungi')))
    assert ('changes the colours of E1 (a faded blue shirt, a white lungi -> a green shirt, a white lungi): give time_jump: what changed in time '
            "(later the same day, another day, another season, years later), from the script or from the scene's own time, or keep the colours.") in text
    for words in ('later the same day', 'another season', 'ten years later'):
        check(two_scenes('a green shirt, a white lungi', time_jump=words))


# ---------- A3: a real, named person may be pictured ----------

def test_a_real_named_person_is_no_longer_held_to_footage():
    d = base()
    d['elements'][0]['speaker'] = True
    out, _ = check(d)   # an AI video shot and a still of them
    assert out['elements'][0]['speaker'] is True
    d['elements'][1]['speaker'] = True   # the trowel
    assert 'element TROWEL: speaker marks a real, named person; TROWEL is a object.' in str(refused(d))


# ---------- A4: a material laid in units, and one that is not ----------

def material_doc(el):
    d = plan([pic('IM1', 0, 500), pic('IM2', 500, 1000)])
    d['elements'].append(copy.deepcopy(el))
    d['gaps'][0]['scenes'][0]['shots'][0]['element_ids'] = ['E1', el['id']]
    return d


def test_water_passes_and_a_material_with_unit_sizes_is_still_checked():
    water = element('WATER', 'material', requirements='clear water, filling the trough to the brim')
    assert ('WATER', 'material_bare') not in kinds(material_doc(water))   # no unit sizes asked
    sized = {**water, 'size': [{'part': 'trough', 'measure': 'depth', 'value': 30, 'unit': 'cm', 'source': 'the client', 'status': 'confirmed'}]}
    check(material_doc(sized))   # "its sizes live in its material_spec" applies only when there is a spec
    check(material_doc(BRICK))
    bad = copy.deepcopy(BRICK)
    bad['material_spec']['proportions'] = []
    assert 'material spec of BRICK: give the proportions that matter.' in str(refused(material_doc(bad)))
    bad = copy.deepcopy(BRICK)
    bad['material_spec']['dimensions'] = []
    assert 'material spec of BRICK: give the unit sizes' in str(refused(material_doc(bad)))
    bad = {**copy.deepcopy(BRICK), 'size': sized['size']}
    assert 'element BRICK: its sizes live in its material_spec, not in size.' in str(refused(material_doc(bad)))


def test_a_material_that_says_nothing_beyond_its_name_is_noted_to_the_assistant():
    for words in ('Water', ' water. '):
        d = material_doc(element('WATER', 'material', requirements=words))
        w = next(w for w in check(d)[1] if w['kind'] == 'material_bare')
        assert w['element_id'] == 'WATER' and w['message'] == ('element WATER is a material with no unit sizes: say how much of it is used or how much of the surface it covers '
                                                               '(requirements), or give its unit sizes (material_spec) if it is laid in repeating units')
    assert 'material_bare' in VC.WARNING_TECHNICAL
    assert ('BRICK', 'material_bare') not in kinds(material_doc({**BRICK, 'requirements': 'Red brick'}))   # it has its spec


# ---------- A5: a size claim is read against a person first ----------

def size_doc():
    d = with_person(plan([pic('IM1', 0, 500, claims=['the case is small'], evidence='beside the chair', element_ids=['CASE', 'CHAIR'], size='MS'), pic('IM2', 500, 1000)]))
    d['elements'] += [element('CASE', 'object'), element('CHAIR', 'object')]
    return d


def test_the_size_refusals_name_the_order_a_person_first():
    order = 'a person in frame first; with no person, a thing whose size is generally fixed (a door, a chair, a hand tool)'
    d = size_doc()
    sh = d['gaps'][0]['scenes'][0]['shots'][0]
    assert f'shot IM1: its claim is about size (small): give the subject a size value and name compare_to: {order}.' in str(refused(d))
    d['elements'][1]['size'] = [{'part': 'case', 'measure': 'length', 'value': 40, 'unit': 'cm', 'source': 'the maker', 'status': 'confirmed'}]
    assert f'shot IM1: size is the message: name compare_to, what the size of CASE is read against: {order}.' in str(refused(d))
    sh['compare_to'] = 'CASE'
    assert f'shot IM1: compare_to names an element in frame other than the subject (CASE is not): {order}.' in str(refused(d))
    sh['compare_to'] = 'CHAIR'
    assert ('IM1', 'compare_not_person') not in kinds(d)   # no person in the shot: a thing of fixed size


def test_a_comparison_that_passes_over_a_person_in_the_shot_is_noted():
    d = size_doc()
    d['elements'][1]['size'] = [{'part': 'case', 'measure': 'length', 'value': 40, 'unit': 'cm', 'source': 'the maker', 'status': 'confirmed'}]
    sh = d['gaps'][0]['scenes'][0]['shots'][0]
    sh.update(element_ids=['CASE', 'CHAIR', 'E1'], compare_to='CHAIR')
    w = next(w for w in check(d)[1] if w['kind'] == 'compare_not_person')
    assert w['shot_id'] == 'IM1' and w['message'] == 'shot IM1: size is the message and a person is in the shot (E1): read the size against the person (compare_to E1), not against CHAIR'
    sh['compare_to'] = 'E1'
    assert ('IM1', 'compare_not_person') not in kinds(d)
    assert 'compare_not_person' in VC.WARNING_TECHNICAL


# ---------- A6: people ----------

def background(n):
    d = base()
    d['elements'] += [person(f'P{i}') for i in range(1, n + 1)]
    im = scene(d)['shots'][1]
    im['element_ids'] = ['E1'] + [f'P{i}' for i in range(1, n + 1)]
    im['subjects'] = [held(f'P{i}') for i in range(1, n + 1)]
    scene(d)['outfit'].update({f'P{i}': f'vest number {i}' for i in range(1, n + 1)})
    return d


def test_ten_named_background_people_are_taken_and_eleven_refused():
    assert VC.NAMED_BACKGROUND_MAX == 10 and not hasattr(VC, 'CROWD')
    check(background(10))
    text = str(refused(background(11)))
    assert ('scene SC1 names 11 background people (P1, P10, P11, P2, P3, P4, P5, P6, P7, P8, P9): up to 10 background people are named, each with their own description; '
            'beyond 10, each further person is described one by one in a groups entry with mode different (one trait per head).') in text
    assert 'crowd' not in text


def test_the_varied_way_is_retired_by_name_on_every_kind_of_shot():
    for sh in (lambda d: vs1(d), lambda d: scene(d)['shots'][1]):
        d = base()
        sh(d).setdefault('groups', []).append({'kind': 'people', 'count': 12, 'mode': 'varied', 'items': ['a red cap', 'a grey scarf']})
        text = str(refused(d))
        assert 'groups mode `varied` is retired: describe the people one by one with mode different, one trait each in items.' in text
        sh(d)['groups'][-1].update(mode='different', count=2)
        check(d)


def test_five_people_in_a_moving_shot_warn_the_operator_and_are_not_refused():
    d = base()
    mason = next(s for s in vs1(d)['subjects'] if s['element_id'] == 'E1')
    for n in range(4):
        d['elements'].append(person(f'W{n}'))
        vs1(d)['subjects'].append({**copy.deepcopy(mason), 'element_id': f'W{n}', 'role': 'secondary', 'beats': [], 'behaviour': 'holds', 'hold_reason': 'watches', 'end': copy.deepcopy(mason['start'])})
        vs1(d)['element_ids'].append(f'W{n}')
        scene(d)['outfit'][f'W{n}'] = f'shirt number {n}'
    w = next(w for w in check(d)[1] if w['kind'] == 'people_many')
    assert w['shot_id'] == 'VS1' and w['message'] == 'shot VS1 has 5 people; an AI video shot with more than 4 often needs a second take: the operator is told; take people out of the shot if it does not need them'
    assert VC.WARNING_PLAIN['people_many'] == 'This moving shot has more than four people; expect a second take.'
    vs1(d)['subjects'].pop()
    assert ('VS1', 'people_many') not in kinds(d)   # four


def test_several_of_a_kind_in_a_camera_still_need_their_groups_entry():
    d = plan([pic('IM1', 0, 500, framing='three people at the counter'), pic('IM2', 500, 1000, framing='no people yet, the counter alone')])
    text = str(refused(d))
    assert 'shot IM1 shows several people (more than one in frame): give groups an entry for it' in text and 'IM2' not in text
    sh = d['gaps'][0]['scenes'][0]['shots'][0]
    sh['groups'] = [{'kind': 'people', 'count': 3, 'mode': 'different', 'items': ['a red cap', 'a grey scarf']}]
    assert 'the people are 3 and different: give one trait each in items' in str(refused(d))
    sh['groups'][0]['items'].append('a walking stick')
    check(d)
    d = plan([{**pshot('DG1', 0, 500, 'diagram'), 'framing': 'three people as icons'}, pic('IM2', 500, 1000)])
    assert 'groups' not in ' '.join(getattr(_try(d), 'errors', []))   # a graphic is not asked


def _try(d):
    try:
        return check(d)
    except ValueError as e:
        return e


def test_a_named_passer_by_is_no_longer_warned_and_old_answers_still_load():
    d = plan([pic('IM1', 0, 1000, warning_answers=[{'kind': 'passer_by', 'answer': 'answered before design/207'}])])
    d['elements'].append(person('PB', requirements='a man walking by in the background'))
    assert 'passer_by' not in {k for _, k in kinds(d)} and 'passer_by' in VC.WARNING_TECHNICAL and not hasattr(VC, 'PASSER_BY')


# ---------- A7: a circling camera is planned like any other move ----------

def test_a_circling_camera_is_not_refused():
    d = base()
    vs1(d)['camera_move'] = 'a slow orbit around the mason'
    check(d)
    assert not hasattr(VC, 'CIRCLING')


# ---------- A8: drawings ----------

def test_a_missing_view_is_a_note_to_the_assistant(long_shots):
    for spec in ({**SPEC, 'view': '', 'view_reason': ''}, {**SPEC, 'view': 'plan', 'view_reason': ''}):
        w = next(w for w in check(drawing(spec, depicts='the lid'))[1] if w['kind'] == 'view_missing')
        assert w['shot_id'] == 'DG1' and w['message'] == 'shot DG1: give view (cutaway, plan, side or elevation) and view_reason: which view shows what the drawing is for'
    assert ('DG1', 'view_missing') not in kinds(drawing({**SPEC, 'view': '', 'view_reason': ''}))   # a section defaults to cutaway
    assert ('DG1', 'view_missing') not in kinds(drawing(SPEC, depicts='the lid')) and 'view_missing' in VC.WARNING_TECHNICAL


def test_illustrative_no_longer_needs_four_sources_tried(long_shots):
    said = lambda d: ' | '.join(w['message'] for w in check(d)[1] if w['kind'] == 'spec_unresearched')
    two = {**SPEC['dimensions'][1], 'tried': 'not in the client brochure; no footage frame shows it'}
    assert said(drawing({**SPEC, 'dimensions': [SPEC['dimensions'][0], two]})) == ''
    VC.spec_research_needs('shot DG1', VC.DrawingSpec.model_validate({**SPEC, 'dimensions': [SPEC['dimensions'][0], two]}))   # the approval's check, the same
    assert not hasattr(VC, 'FOUR_SOURCES')
    assert 'shot DG1: a size is unknown: set illustrative true; the drawing then carries "not to scale" and shows no figure for that size.' in said(
        drawing({**SPEC, 'illustrative': False}))
    assert said(drawing({**SPEC, 'dimensions': [SPEC['dimensions'][0]]})) == ''   # the review of design/207: "not to scale" with every size known is taken (was: "nothing is unknown: drop illustrative")
    assert 'record the sources tried' in said(drawing({**SPEC, 'dimensions': [SPEC['dimensions'][0], {**two, 'tried': ''}]}))   # an unknown size still says what was tried


def test_a_drawing_with_an_unknown_size_still_carries_not_to_scale_and_a_stated_figure_is_never_unknown(long_shots):
    assert 'a size is unknown, so the drawing is labelled "illustrative, not to scale"' in str(refused(drawing({**SPEC, 'label': 'the wall'})))
    assert "the narration states 50 mm: the spec's cavity width is confirmed from the script, not unknown" in str(refused(drawing(SPEC, narration='The gap is 50 mm wide.')))


# ---------- A9: framing notes go to the assistant, and the scene before is remembered ----------

def test_the_three_framing_warnings_are_technical():
    for kind in ('size_open', 'size_repeat', 'size_close_first'):
        assert kind in VC.WARNING_TECHNICAL and kind not in VC.WARNING_PLAIN


def framing_doc():
    d = with_person(plan([]), place=True)
    wide = pic('IM1', 0, 300, size='WS', element_ids=['E1', 'ROOM'])
    close = pic('IM2', 300, 600, size='CU', element_ids=['E1', 'ROOM'])
    return d, wide, close


def test_a_place_shown_wide_in_the_scene_just_before_needs_no_new_opener():
    d, wide, close = framing_doc()
    found = kinds(scenes_of(d, [wide], [close], [pic('IM3', 600, 1000, size='MS', element_ids=['E1', 'ROOM'])]))
    assert ('IM2', 'size_open') not in found and ('IM2', 'size_close_first') not in found
    d, wide, close = framing_doc()   # the scene before did not show the place: the scene two back does not count
    between = pic('IM4', 300, 400, size='WS', element_ids=['TABLE'])
    d['elements'].append(element('TABLE', 'object'))
    found = kinds(scenes_of(d, [wide], [between], [{**close, 'start_frame': 400, 'end_frame': 1000}]))
    assert {('IM2', 'size_open'), ('IM2', 'size_close_first')} <= found
    d, wide, close = framing_doc()   # the scene before showed the person wide in another place: the new place still opens wide, the close-up is fine
    d['elements'].append(element('HALL', 'place', signs_of_use=SIGNS))
    wide['element_ids'] = ['E1', 'HALL']
    found = kinds(scenes_of(d, [wide], [{**close, 'end_frame': 1000}]))
    assert ('IM2', 'size_open') in found and ('IM2', 'size_close_first') not in found
    d, wide, close = framing_doc()   # the scene before showed the place only medium: the opener is still asked
    wide['size'] = 'MS'
    found = kinds(scenes_of(d, [wide], [{**close, 'end_frame': 1000}]))
    assert ('IM1', 'size_open') in found and ('IM2', 'size_open') in found and ('IM2', 'size_close_first') not in found


def test_the_gap_before_is_remembered_in_film_order():
    d, wide, close = framing_doc()
    wide.update(end_frame=1000)
    later = {**close, 'start_frame': 1000, 'end_frame': 2000}
    doc, gaps = two_gaps([wide], [later])
    doc['elements'], doc['gaps'][0]['scenes'][0]['outfit'], doc['gaps'][1]['scenes'][0]['outfit'] = d['elements'], {'E1': 'a green coat'}, {'E1': 'a green coat'}
    found = kinds(doc, gaps)
    assert ('IM2', 'size_open') not in found and ('IM2', 'size_close_first') not in found
    doc['gaps'].reverse()   # the plan lists the later gap first: film order decides, not the list
    found = kinds(doc, gaps)
    assert ('IM2', 'size_open') not in found and ('IM2', 'size_close_first') not in found


# ---------- A10: a look or an expression is framed close ----------

def look_doc(size):
    d = base()
    m = vs1(d)['subjects'][0]
    for state in (m['end'], m['beats'][0]['end'], m['beats'][1]['start'], m['beats'][1]['end']):
        state['objects'] = copy.deepcopy(m['start']['objects'])   # nothing moves: the look is the only change
    vs1(d).update(changes=[{'what': 'E1 looks up at the window', 'beat_id': 'B2'}, {'what': 'a slow smile', 'beat_id': 'B2'}], size=size, fixed=[] if size in VC.CLOSE_SIZES else ['L1'])
    return d


def test_a_shot_about_a_look_framed_wide_is_noted_and_the_dead_warning_is_gone():
    w = next(w for w in check(look_doc('MS'))[1] if w['kind'] == 'look_wide')
    assert w['shot_id'] == 'VS1' and w['message'] == 'shot VS1: this shot is about a look or an expression: frame it MCU or closer with the face in frame'
    for size in VC.CLOSE_SIZES:
        assert ('VS1', 'look_wide') not in kinds(look_doc(size))
    d = look_doc('MS')
    vs1(d)['changes'].append({'what': 'the trowel set down on the course', 'beat_id': 'B2'})   # not only a look
    assert ('VS1', 'look_wide') not in kinds(d) and ('VS1', 'look_wide') not in kinds(base())
    assert "'kind': 'look_only'" not in SOURCE and 'look_only' in VC.WARNING_TECHNICAL and 'look_wide' in VC.WARNING_TECHNICAL
    assert 'look_only' not in VC.WARNING_PLAIN


# ---------- A11: living extras ----------

def extras_doc(*shot_lists):
    d = plan([])
    d['elements'] += [element('DOG', 'animal', name='Street dog'), element('CAT', 'animal', name='Grey cat')]
    return scenes_of(d, *shot_lists)


def test_the_same_living_extra_in_two_shots_in_a_row_of_different_scenes_is_noted():
    dog = lambda sid, a, b: pic(sid, a, b, element_ids=['E1', 'DOG'])
    d = extras_doc([pic('IM1', 0, 200), dog('IM2', 200, 400)], [dog('IM3', 400, 700), dog('IM4', 700, 1000)])
    found = [w for w in check(d)[1] if w['kind'] == 'extra_repeated']
    assert [w['shot_id'] for w in found] == ['IM3']   # IM4 carries on inside its own scene
    assert found[0]['message'] == 'shot IM3 shows DOG again straight after IM2, in another scene: a living extra is not in two shots in a row unless it carries on from the shot before; take it out of one, or say why it stays'
    d = extras_doc([dog('IM2', 0, 400)], [pic('IM3', 400, 700)], [dog('IM4', 700, 1000)])
    assert 'extra_repeated' not in {k for _, k in kinds(d)}   # a shot without it lies between
    assert 'extra_repeated' in VC.WARNING_TECHNICAL


def test_several_kinds_of_animal_in_one_shot_are_noted():
    d = extras_doc([pic('IM1', 0, 500, element_ids=['E1', 'DOG', 'CAT']), pic('IM2', 500, 1000, element_ids=['E1', 'DOG'])])
    found = [w for w in check(d)[1] if w['kind'] == 'animals_many']
    assert [w['shot_id'] for w in found] == ['IM1']
    assert found[0]['message'] == 'shot IM1 names more than one kind of animal (Grey cat, Street dog): one shot carries one kind of animal'
    d['elements'].append(element('DOG2', 'animal', name='Street dog'))
    d['gaps'][0]['scenes'][0]['shots'][1]['element_ids'] = ['E1', 'DOG', 'DOG2']
    assert [w['shot_id'] for w in check(d)[1] if w['kind'] == 'animals_many'] == ['IM1']   # two of one kind
    assert 'animals_many' in VC.WARNING_TECHNICAL


# ---------- A12: the same set-up twice ----------

def setup_doc(**later):
    d = with_person(plan([]), place=True)
    d['elements'].append(element('HALL', 'place', signs_of_use=SIGNS))
    one = pic('IM1', 0, 300, size='WS', element_ids=['E1', 'ROOM'])
    two = pic('IM2', 300, 600, size='MS', element_ids=['E1', 'ROOM'])
    three = pic('IM3', 600, 1000, **{'size': 'WS', 'element_ids': ['E1', 'ROOM'], **later})
    return scenes_of(d, [one, two], [three])


def test_the_same_person_place_clothes_and_size_again_is_noted_unless_it_says_what_differs():
    w = next(w for w in check(setup_doc())[1] if w['kind'] == 'same_setup')
    assert w['shot_id'] == 'IM3' and w['message'] == ('shot IM3 shows E1 at ROOM in the same clothes and at the same size (WS) as IM1: change the angle, the distance or the moment '
                                                      'and say what differs (differs_by), or name the return (return_of)')
    assert [k for _, k in kinds(setup_doc())].count('same_setup') == 1   # IM2 is another size
    for later in ({'differs_by': 'from the doorway, an hour on'}, {'return_of': 'IM1', 'differs_by': 'closer'}, {'size': 'MWS'}, {'element_ids': ['E1', 'HALL']}, {'element_ids': ['ROOM']}):
        assert ('IM3', 'same_setup') not in kinds(setup_doc(**later))
    d = setup_doc()
    d['gaps'][0]['scenes'][1].update(outfit={'E1': 'a red coat'}, time_jump='the next day')
    assert ('IM3', 'same_setup') not in kinds(d)   # other clothes
    d = setup_doc()
    d['gaps'][0]['scenes'][1]['shots'][0].update(visual_type='footage')
    assert ('IM3', 'same_setup') not in kinds(d)   # footage is what was filmed
    assert 'same_setup' in VC.WARNING_TECHNICAL and 'ponytail:' in SOURCE.split("'kind': 'same_setup'")[0][-1500:]


# ---------- A13: any kind of AI video ----------

def test_another_kind_of_moving_shot_is_taken_with_one_plain_warning():
    d = base()
    vs1(d)['recipe'] = 'other'
    more = copy.deepcopy(d)
    extra = {**pshot('VS9', 250, 500, 'video'), 'recipe': 'other'}
    more['gaps'][0]['scenes'][0]['shots'] = [vs1(more), extra, pic('IM1', 500, 1000)]
    for doc, ids in ((d, 'VS1'), (more, 'VS1, VS9')):
        found = [w for w in check(doc)[1] if w['kind'] == 'video_untried']
        assert len(found) == 1 and found[0]['shot_id'] == 'VS1'
        assert found[0]['message'] == f'{ids}: this kind of moving shot has not been tried here; the first take is a trial and may need a second; the operator is told'
    assert VC.WARNING_PLAIN['video_untried'] == 'This kind of moving shot has not been tried here; the first take is a trial and may need a second.'
    assert 'video_untried' not in {k for _, k in kinds(base())}
    vs1(d)['recipe'] = 'drive_by'
    assert 'recipe' in str(refused(d))


# ---------- A14: the kinds other parts of the server raise ----------

def test_the_new_plain_kinds_are_told_to_the_operator_and_accepted_as_answers():
    plain = {'still_more_than_agreed': 'This gap has more still picture than you accepted in the treatment.',
             'text_card': "This is a card of words; this kind of film carries no words on the picture beyond a diagram's labels.",
             'stand_in_real': 'This person is real and named, but the picture will be a made-up stand-in.',
             'stills_many': 'Still pictures take up a large part of the film.'}
    for kind, sentence in plain.items():
        assert VC.WARNING_PLAIN[kind] == sentence
    assert 'look_alike' in VC.WARNING_TECHNICAL and 'look_alike' not in VC.WARNING_PLAIN
    assert not set(VC.WARNING_PLAIN) & set(VC.WARNING_TECHNICAL)
    answers = [{'kind': k, 'answer': 'answered'} for k in list(plain) + ['look_alike', 'look_only', 'video_untried', 'people_many', 'material_bare', 'compare_not_person',
                                                                         'view_missing', 'look_wide', 'extra_repeated', 'animals_many', 'same_setup']]
    out, _ = check(plan([pic('IM1', 0, 1000, warning_answers=answers)]))
    w = VC.answer_warnings(out, [{'shot_id': 'IM1', 'kind': 'text_card', 'message': 'm'}])[0]
    assert w['answered'] and w['answer'] == 'answered'
    with pytest.raises(ValueError, match="'crowd_note', which is no kind of warning"):
        check(plan([pic('IM1', 0, 1000, warning_answers=[{'kind': 'crowd_note', 'answer': 'x'}])]))


# ---------- A15: the messages fit every kind of film ----------

def test_the_checker_messages_carry_no_building_site_examples():
    for old in ('a brick about 3 : 1.5 : 1', 'unit: bricks, paces', '("set the third brick on edge beside the second")', 'named workers with beats', 'a worker with a beat is named',
                'and the working equipment', 'a crowd'):
        assert old not in '\n'.join(l.split('   # ')[0] for l in SOURCE.splitlines()), old   # the code and its messages; a comment may still tell the history
