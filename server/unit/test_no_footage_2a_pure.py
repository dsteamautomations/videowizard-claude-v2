"""SK, 23 Nov 2026 (no-footage release 2a): the look of a film with no camera footage, in words. Such a film is always shown two Directions,
each with its look (colours, contrast, light, texture), one look for each period the script speaks of. The look of the Direction the operator
takes is the film's look: the light line of every picture and the "as the footage" fallbacks read it, a scene reading the look of its period.
A film with footage is unchanged: no look is asked, kept or read."""
import json
from pathlib import Path

import pytest

from app import chat_flow as CF, core, ref_sets, visual_contract as VC, visuals_stage as VS

SERVER = Path(__file__).resolve().parents[1]
VISUALS = next(s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
PARTS = {'idea': 'A brick is only as good as its week of curing.', 'purpose': 'Site engineers; they should ask for cured bricks.', 'viewpoint': 'The mason who lays them.',
         'feel': 'Plain and unhurried.', 'shape': 'Press, cure, lay.', 'pictures': 'Scenes carry the work; one diagram carries the strength.'}
OTHER = {**PARTS, 'idea': 'The wall remembers how its bricks were made.', 'viewpoint': 'The owner of the house, ten years on.', 'answers_brief': 'It shows the result.', 'risk': 'Less of the process.'}
LOOK = [{'period': '', 'look': 'Muted earth colours, soft overcast light, low contrast, fine grain.'}]
LOOK2 = [{'period': '', 'look': 'Warm evening light, deep shadows, rich brick red.'}]
USER = {'id': 'u1', 'name': 'Asha'}


def doc(**more):
    return {'direction_parts': dict(PARTS), 'direction_answers_brief': 'It shows the process.', 'direction_risk': 'Slow.', 'direction_look': LOOK,
            'direction_alternative': {**OTHER, 'look': LOOK2}, **more}


def test_a_film_with_footage_is_asked_for_no_look_and_keeps_none():
    out = VS.direction_fields(doc())
    assert 'direction_look' not in out and 'look' not in out['direction_alternative']
    plain = {'direction_parts': dict(PARTS)}
    assert VS.direction_fields(plain) == VS.direction_fields(plain, none=False) and 'direction_alternative' not in VS.direction_fields(plain)


def test_a_film_with_no_footage_keeps_the_look_of_both_directions():
    out = VS.direction_fields(doc(), none=True)
    assert out['direction_look'] == LOOK and out['direction_alternative']['look'] == LOOK2


@pytest.mark.parametrize('change, said', [
    ({'direction_look': None}, 'direction_look'), ({'direction_look': []}, 'direction_look'), ({'direction_look': 'muted'}, 'direction_look'),
    ({'direction_look': [{'period': '', 'look': ''}]}, 'look'), ({'direction_look': [{'period': '', 'look': 'x' * 401}]}, '400'),
    ({'direction_look': [{'period': '', 'look': 'a'}, {'period': '', 'look': 'b'}]}, 'period'),   # two looks, so each names its period
    ({'direction_look': [{'period': '1950s', 'look': 'a'}, {'period': '1950S', 'look': 'b'}]}, 'twice'),
    ({'direction_alternative': {**OTHER}}, 'second direction'),   # the second has no look
    ({'direction_alternative': {**OTHER, 'look': [{'period': '1950s', 'look': 'a'}, {'period': 'today', 'look': 'b'}]}}, 'same periods')])
def test_a_look_that_cannot_be_read_is_refused_in_one_sentence(change, said):
    with pytest.raises(ValueError) as e:
        VS.direction_fields(doc(**change), none=True)
    assert said in str(e.value)


def test_two_periods_are_two_looks_on_both_directions():
    two = [{'period': '1950s', 'look': 'Faded colour, soft lenses.'}, {'period': 'today', 'look': 'Clean daylight, true colour.'}]
    out = VS.direction_fields(doc(direction_look=two, direction_alternative={**OTHER, 'look': [{'period': 'Today', 'look': 'Cool light.'}, {'period': '1950s', 'look': 'Sepia.'}]}), none=True)
    assert [x['period'] for x in out['direction_look']] == ['1950s', 'today']


def test_a_second_direction_is_due_until_one_is_taken():
    first = VS.direction_fields(doc(), none=True)
    alone = {k: v for k, v in first.items() if k != 'direction_alternative'}
    assert VS.second_due({}, alone) and not VS.second_due({}, first)
    taken = {'treatment_draft': {**alone, 'lines': {'direction': {'state': 'accepted', 'digest': VS._line_digests(alone)['direction']}}}}
    assert not VS.second_due(taken, alone)   # sent again unchanged with the gap lines: the choice is made
    assert VS.second_due(taken, {**alone, 'direction': alone['direction'] + ' More.'})   # a new Direction is shown with a second again
    assert not VS.second_due({'treatment': alone}, alone)   # recorded


def session_with(look, **more):
    return {'treatment': {'direction': 'x', 'direction_look': look}, 'footage_measured': {'per_clip': {}}, 'first_cut_events': [], 'references': {}, **more}


def test_the_look_changes_the_line_the_operator_answers():
    first = VS.direction_fields(doc(), none=True)
    other = VS.direction_fields(doc(direction_look=[{'period': '', 'look': 'High contrast, hard noon light.'}]), none=True)
    assert VS._line_digests(first)['direction'] != VS._line_digests(other)['direction']
    plain = VS.direction_fields({'direction_parts': dict(PARTS)})
    assert VS._line_digests(plain)['direction'] == VS.digest(' '.join(plain['direction'].split()))   # a film with footage: as before


def test_taking_the_second_direction_takes_its_look(monkeypatch):
    first = VS.direction_fields(doc(), none=True)
    session = {'treatment_draft': {'gaps': [], 'direction_only': True, **first, 'lines': {'direction': {'digest': VS._line_digests(first)['direction'], 'state': 'to_accept'}}}}
    monkeypatch.setattr(VS, 'save_session', lambda *a, **k: None)
    VS._treatment_lines(None, USER, {'id': 'r'}, session, ['direction'], [], '', 'the second one', use_second=True)
    assert session['treatment_draft']['direction_look'] == LOOK2 and 'direction_alternative' not in session['treatment_draft']
    session = {'treatment_draft': {'gaps': [], 'direction_only': True, **first, 'lines': {'direction': {'digest': VS._line_digests(first)['direction'], 'state': 'to_accept'}}}}
    VS._treatment_lines(None, USER, {'id': 'r'}, session, ['direction'], [], '', 'the first', use_second=False)
    assert session['treatment_draft']['direction_look'] == LOOK


def test_the_light_line_of_a_picture_reads_the_look():
    s = session_with(LOOK)
    line = VS.real_light_line(None, s)
    assert LOOK[0]['look'].rstrip('.') in line and 'No studio light, no glow, no added saturation' in line and 'footage' not in line
    assert VS.real_light_line(None, s, {'light': 'one window, soft'}) == line   # a scene's own light keeps the film's look
    two = session_with([{'period': '1950s', 'look': 'Faded colour.'}, {'period': 'today', 'look': 'Clean daylight.'}])
    assert 'Faded colour' in VS.real_light_line(None, two, {'period': '1950S'}) and 'Clean daylight' in VS.real_light_line(None, two, {'period': 'today'})
    assert 'Faded colour' in VS.real_light_line(None, two, {}) and 'Faded colour' in VS.real_light_line(None, two, {'period': 'unknown'})   # no period named: the first


def test_a_film_with_no_clip_and_no_look_yet_still_gets_the_plain_rule():
    s = {'footage_measured': {'per_clip': {}}, 'first_cut_events': [], 'references': {}, 'footage': {'summary': {}}}
    assert VS.real_light_line(None, s) == 'No studio light, no glow, no added saturation.'


def test_a_film_with_footage_reads_its_footage_as_before():
    s = {'footage_measured': {'per_clip': {'c1': {}}}, 'first_cut_events': [], 'references': {}, 'footage': {'summary': {'look': 'natural', 'camera': 'phone'}}}
    line = VS.real_light_line(None, s)
    assert line.startswith('Real light, as the footage has it: natural look') and line.endswith('the same light and colour as the footage beside it.')
    assert VS.real_light_line(None, {'footage_measured': {'per_clip': {'c1': {}}}, 'first_cut_events': [], 'references': {}, 'footage': {'summary': {}}}) == ''
    assert VS._place_look({'gaps': []})[1] == 'as the footage' and VS._place_look({'gaps': []}, s)[1] == 'as the footage'
    assert ref_sets._look({}) == 'as the footage' and ref_sets._look({}, session=s) == 'as the footage'


def test_the_fallbacks_read_the_look_where_the_plan_gives_none():
    s = session_with(LOOK)
    assert VS._place_look({'gaps': []}, s)[1] == LOOK[0]['look'].rstrip('.') and ref_sets._look({}, session=s) == LOOK[0]['look'].rstrip('.')
    plan = {'foundation': {'appearance': 'Soft daylight.'}, 'gaps': []}
    assert VS._place_look(plan, s)[1] == 'Soft daylight.' and ref_sets._look(plan, session=s) == 'Soft daylight'   # the plan's own words win


def test_a_scene_may_name_its_period():
    assert 'period' in VC.Scene.model_fields and VC.Scene.model_fields['period'].default == ''


def test_both_fronts_show_the_look_of_each_direction():
    rows = dict(CF._direction_rows(VS.direction_fields(doc(), none=True), []))
    assert rows['First · The look'] == LOOK[0]['look'] and rows['Second · The look'] == LOOK2[0]['look']
    two = [{'period': '1950s', 'look': 'Faded.'}, {'period': 'today', 'look': 'Clean.'}]
    taken = {k: v for k, v in VS.direction_fields(doc(direction_look=two, direction_alternative={**OTHER, 'look': two}), none=True).items() if k != 'direction_alternative'}
    rows = dict(CF._direction_rows(taken, []))
    assert rows['The look · 1950s'] == 'Faded.' and rows['The look · today'] == 'Clean.'
    assert not [k for k, _ in CF._direction_rows(VS.direction_fields(doc()), []) if 'look' in k.lower()]   # a film with footage


def test_the_treatment_instructions_ask_such_a_film_for_two_directions_and_their_looks():
    none, own = core.for_footage(VISUALS, 'none'), core.for_footage(VISUALS, 'own')
    part = lambda st: next(p['text'] for p in st['parts'] if p['name'] == 'treatment')
    assert '`direction_look`' in part(none) and 'always two' in part(none) and 'period' in part(none)
    assert '`direction_look`' not in json.dumps(own)
