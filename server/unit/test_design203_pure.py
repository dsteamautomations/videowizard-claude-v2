"""design/203 (SK, 15 Nov 2026): the Direction in six labelled parts, each within its length, the idea in one sentence; an older paragraph still
taken; what changed named by part; the brief shown beside it; "Show me a different direction": a second Direction kept beside the first."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app import chat_flow as CF, visuals_stage as VS
from test_design126_a_pure import USER, run, treat, vw12
from test_design202_pure import reasoned

ROOT = Path(__file__).resolve().parents[1]
R = run('gemini')
TREATMENT = next(p['text'] for s in json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals'
                 for p in s['parts'] if p['name'] == 'treatment')
PARTS = {'idea': 'Fewer bricks, and a better wall.',
         'purpose': 'Builders and home owners. They should come away believing rat-trap bond is a sound choice.',
         'viewpoint': 'Told from beside the mason.',
         'feel': 'Calm and sure: steady pictures, real work, no hype.',
         'shape': 'The housing problem; the method; what it gives; the proof it is strong; what it saves the land.',
         'pictures': 'Real footage shows the method. Short scenes of one person doing one thing show what the footage lacks. No still held as wallpaper.'}
SECOND = {**PARTS, 'idea': 'A cooler home for less.', 'viewpoint': 'Told from the family who will live in the house.',
          'answers_brief': 'It speaks to home owners first.', 'risk': 'The method gets less screen time.'}
BRIEF = [{'stage': 'brief', 'unit': None, 'summary': {'purpose': 'Explain rat-trap bond', 'audience': 'Builders and home owners', 'tone': 'Calm, factual'}}]


def doc(parts=PARTS, **more):
    d = reasoned(vw12())
    d.pop('direction')
    return {**d, 'direction_parts': deepcopy(parts), **more}


def draft_of(store):
    return VS.session_of(store, R, [])['treatment_draft']


def direction_item(store, outputs=()):
    s = VS.session_of(store, R, [])
    return CF._treatment_items({'session': s, 'store': store, 'user': USER, 'run': R, 'outputs': list(outputs)})[0][0]


# ---------- the six parts ----------

def test_the_direction_is_built_from_the_six_parts_in_order_under_their_headings():
    out, store = treat(doc())
    text = draft_of(store)['direction']
    assert out['direction_missing'] == [] and draft_of(store)['direction_parts'] == PARTS
    assert text.startswith('The idea: Fewer bricks, and a better wall.\nWho it is for and what it must do: Builders')
    assert [line.split(':')[0] for line in text.split('\n')] == [h for _, h, _ in VS.DIRECTION_PARTS]


def test_a_part_not_given_is_named_and_the_draft_is_still_taken():
    parts = {k: v for k, v in PARTS.items() if k != 'feel'}
    parts['shape'] = '   '
    out, store = treat(doc(parts))
    assert out['draft'] is True and out['direction_missing'] == ['How it should feel', 'How the film moves']
    assert 'How it should feel' not in draft_of(store)['direction']


def test_a_part_over_its_limit_is_refused_and_at_its_limit_is_taken():
    with pytest.raises(ValueError) as e:
        treat(doc({**PARTS, 'viewpoint': 'x' * 201}))
    assert 'Whose story' in str(e.value) and '200' in str(e.value)
    assert treat(doc({**PARTS, 'viewpoint': 'x' * 200}))[0]['direction_missing'] == []


def test_the_idea_is_one_sentence():
    with pytest.raises(ValueError) as e:
        treat(doc({**PARTS, 'idea': 'Fewer bricks. A better wall.'}))
    assert 'The idea is one sentence' in str(e.value)
    assert treat(doc({**PARTS, 'idea': 'Fewer bricks; a better wall: cooler, cheaper'}))[0]['direction_missing'] == []


def test_a_part_that_is_not_text_counts_as_not_given():
    out, _ = treat(doc({**PARTS, 'feel': ['calm']}))
    assert out['direction_missing'] == ['How it should feel']


def test_an_older_paragraph_is_still_taken_with_its_flag():
    out, store = treat(reasoned(vw12()))
    assert out['direction_missing'] == ['The Direction is not in its six parts.'] and 'direction_parts' not in draft_of(store)
    assert draft_of(store)['direction'] == 'a documentary explainer told from the site'


def test_when_both_are_sent_the_parts_win():
    out, store = treat({**doc(), 'direction': 'an old paragraph'})
    assert draft_of(store)['direction'].startswith('The idea: ')


def test_no_direction_at_all_is_refused_as_before():
    d = reasoned(vw12())
    d.pop('direction')
    with pytest.raises(ValueError):
        treat(d)
    with pytest.raises(ValueError):
        treat(doc({}))


# ---------- what changed, by part ----------

def test_a_direction_changed_in_one_part_names_that_part_alone():
    first, store = treat(doc())
    VS.treatment(store, USER, R, [], None, 'x', send_back=['direction'], notes='tell it from the family')
    VS.treatment(store, USER, R, [], doc({**PARTS, 'viewpoint': 'Told from the family.'}), '')
    line = draft_of(store)['lines']['direction']
    assert line['asked'] is True and line['changes'] == ['Whose story: "Told from beside the mason." → "Told from the family."']


def test_a_paragraph_replaced_by_parts_still_says_what_it_was_before():
    first, store = treat(reasoned(vw12()))
    VS.treatment(store, USER, R, [], None, 'x', send_back=['direction'], notes='in parts please')
    VS.treatment(store, USER, R, [], doc(), '')
    assert draft_of(store)['lines']['direction']['changes'] == ['Before: "a documentary explainer told from the site"']


# ---------- how it is shown and asked ----------

def test_the_direction_is_shown_as_six_rows_with_the_brief_above_and_three_buttons():
    out, store = treat(doc({k: v for k, v in PARTS.items() if k != 'feel'}))
    item = direction_item(store, BRIEF)
    rows = dict(item['_card']['r'])
    assert list(rows)[:3] == ['From the brief · purpose', 'From the brief · audience', 'From the brief · tone'] and rows['From the brief · tone'] == 'Calm, factual'
    assert rows['The idea'] == PARTS['idea'] and rows['How it should feel'] == 'not given' and rows['Whose story'] == PARTS['viewpoint']
    assert [b['choice'] for b in item['buttons']] == ['accept', 'change', 'different'] and item['buttons'][2]['label'] == 'Show me a different direction'
    assert CF._split(item['question'])[1] == 'Do you accept the direction of the film?' and 'what the viewer should understand by the end' in item['text']


def test_a_brief_with_nothing_recorded_says_so_and_no_brief_leaves_the_rows_out():
    out, store = treat(doc())
    some = dict(direction_item(store, [{'stage': 'brief', 'unit': None, 'summary': {'purpose': 'Explain rat-trap bond'}}])['_card']['r'])
    assert some['From the brief · audience'] == 'not recorded' and some['From the brief · purpose'] == 'Explain rat-trap bond'
    assert not [k for k in dict(direction_item(store)['_card']['r']) if k.startswith('From the brief')]


def test_an_older_paragraph_is_shown_as_its_text_with_the_three_buttons():
    out, store = treat(reasoned(vw12()))
    item = direction_item(store)
    assert 't' in item['_card'] and 'a documentary explainer told from the site' in item['text'] and [b['choice'] for b in item['buttons']] == ['accept', 'change', 'different']


# ---------- a different direction ----------

def asked_for_another(first=None):
    out, store = treat(first or doc())
    direction_item(store)['_run']('different', 'Show me a different direction', '')
    return store


def test_asking_for_a_different_direction_sends_it_back_with_fixed_words():
    store = asked_for_another()
    line = draft_of(store)['lines']['direction']
    assert line['state'] == 'sent_back' and line['note'] == VS.DIFFERENT_DIRECTION and line['different'] is True


def test_the_answer_tells_the_assistant_to_write_a_second_direction_that_differs_in_kind():
    out, store = treat(doc())
    said = direction_item(store)['_run']('different', 'Show me a different direction', '')
    assert 'second Direction' in said['tell'] and 'viewpoint or approach' in said['tell']


def test_the_second_direction_is_kept_beside_the_first_and_both_are_shown():
    store = asked_for_another()
    out = VS.treatment(store, USER, R, [], doc(direction_alternative=SECOND, direction_answers_brief='It speaks to builders.', direction_risk='Home owners may feel left out.'), '')
    d = draft_of(store)
    assert out['lines']['direction'] == 'to_accept' and d['direction_parts'] == PARTS and d['direction_alternative']['parts']['viewpoint'] == SECOND['viewpoint']
    item = direction_item(store, BRIEF)
    rows = dict(item['_card']['r'])
    assert rows['First · Whose story'] == PARTS['viewpoint'] and rows['Second · Whose story'] == SECOND['viewpoint']
    assert rows['First · how it answers the brief'] == 'It speaks to builders.' and rows['Second · what it risks'] == 'The method gets less screen time.'
    assert [(b['choice'], b['label']) for b in item['buttons']] == [('accept', 'Use the first'), ('accept_second', 'Use the second'), ('change', 'Change this'),
                                                                    ('different', 'Show me a different direction')]


def test_a_second_direction_identical_to_the_first_is_refused():
    store = asked_for_another()
    with pytest.raises(ValueError) as e:
        VS.treatment(store, USER, R, [], doc(direction_alternative={**PARTS, 'answers_brief': 'a', 'risk': 'b'}), '')
    assert 'same as the first' in str(e.value)


def test_the_second_direction_without_its_two_lines_names_them():
    store = asked_for_another()
    out = VS.treatment(store, USER, R, [], doc(direction_alternative={k: v for k, v in SECOND.items() if k not in ('answers_brief', 'risk')}), '')
    assert 'The second direction: how it answers the brief' in out['direction_missing'] and 'The second direction: what it risks' in out['direction_missing']


def test_asking_again_replaces_the_second_and_keeps_the_first():
    store = asked_for_another()
    VS.treatment(store, USER, R, [], doc(direction_alternative=SECOND), '')
    direction_item(store)['_run']('different', 'Show me a different direction', '')
    third = {**SECOND, 'viewpoint': 'Told from the land the bricks come from.'}
    VS.treatment(store, USER, R, [], doc(direction_alternative=third), '')
    d = draft_of(store)
    assert d['direction_parts'] == PARTS and d['direction_alternative']['parts']['viewpoint'] == third['viewpoint'] and d['lines']['direction']['state'] == 'to_accept'


def test_using_the_first_drops_the_second_and_leaves_the_gap_lines_as_they_are():
    store = asked_for_another()
    VS.treatment(store, USER, R, [], doc(direction_alternative=SECOND), '')
    direction_item(store)['_run']('accept', 'Use the first', '')
    d = draft_of(store)
    assert 'direction_alternative' not in d and d['lines']['direction']['state'] == 'accepted' and d['direction_parts'] == PARTS
    assert d['lines']['direction']['digest'] == VS._line_digests(d)['direction'] and d['lines']['BEAT_02-B2']['state'] == 'to_accept'


def test_using_the_second_makes_it_the_direction_and_sends_every_gap_line_back():
    store = asked_for_another()
    VS.treatment(store, USER, R, [], doc(direction_alternative=SECOND), '')
    direction_item(store)['_run']('accept_second', 'Use the second', '')
    d = draft_of(store)
    assert 'direction_alternative' not in d and d['direction_parts']['viewpoint'] == SECOND['viewpoint'] and d['direction'].startswith('The idea: A cooler home for less.')
    assert d['lines']['direction']['state'] == 'accepted' and d['lines']['direction']['digest'] == VS._line_digests(d)['direction']
    assert all(v['state'] == 'sent_back' for k, v in d['lines'].items() if k != 'direction') and 'the direction you chose' in d['lines']['BEAT_02-B2']['note']
    again = doc({k: v for k, v in SECOND.items() if k not in ('answers_brief', 'risk')})   # the assistant sends the gaps again under the chosen direction
    again['gaps'][2]['picture'] = 'the family at the wall'
    out = VS.treatment(store, USER, R, [], again, '')
    assert out['lines']['direction'] == 'accepted' and out['lines']['BEAT_02-B2'] == 'to_accept'


# ---------- the instructions ----------

def test_the_instructions_ask_for_the_six_parts_and_a_second_direction_that_differs_in_kind():
    for words in ('`direction_parts`', 'in one sentence', 'One viewpoint', 'what the film will not do', '`direction_alternative`', 'differs in viewpoint or approach',
                  'how it answers the brief and what it risks'):
        assert words in TREATMENT, words
