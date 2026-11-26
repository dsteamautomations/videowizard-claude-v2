"""VW-25 issue 12 (25 Nov 2026): the request of a reference set no longer hands the image model the thing's name as a title line. On VW-25
two sets came back with the person's name printed in them. That the title line caused it is a guess, not proven: these tests pin the request's
words only; the paid check that would prove it is not run here.

The real `ref_sets.set_request` runs on the film of design/211 (the harness of test_design211b_sets_pure). Every row of the note's table and
its failure mode has its test. Without a database."""
import copy
import inspect
import re

import pytest

from app import ref_sets as RS, visuals_stage as VS
import d211_fixture as F
from test_design211b_sets_pure import RUN, USER, FakeConn, el, finder, ready, request, store_of   # noqa: F401 (finder: part A's stand-ins, on every test)

THINGS = ('TROWEL', 'FAN', 'BRICK', 'STREET', 'T_LAY', 'TILE')   # an object from footage, an object from the web, a material, a place, a way of working, an object with its drawing
WHAT = {'TROWEL': 'an object', 'FAN': 'an object', 'BRICK': 'a material', 'STREET': 'a place', 'T_LAY': 'a way of working', 'TILE': 'an object'}


@pytest.fixture(autouse=True)
def _v2_round(monkeypatch, _older_round_tests):   # conftest: a module not named test_design211* posts an older round; these read the round of today
    monkeypatch.setattr(VS, 'ROUND_V', 2)


def with_person(description='A stocky young man, curly black hair.', name='Mason B', **more):
    """The fixture's plan with a second person; they must be told apart."""
    plan = F.plan()
    plan['elements'].append({'id': 'MASON_B', 'name': name, 'kind': 'person', 'identity': 'representative', 'description': description, 'requirements': 'Carries the bricks.', **more})
    return plan


def changed(eid, **fields):
    plan = F.plan()
    el(eid, plan).update(fields)
    return plan


def captioned(eid, seen='The name is printed under the figure.'):
    """The fixture's session at step 2 where the assistant's look found a caption in picture 2 of the thing's set."""
    s = ready('2')
    sid = s['round']['elements'][eid]['set']
    next(l for l in s['references'][f'{sid}-2']['look']['lines'] if l['check'] == 'no text').update({'pass': False, 'seen': seen})
    return s


def title_lines(prompt, name):
    """The lines of a request that hand the name over as a title: a line that is the name, or that opens with a label and the name."""
    return [l for l in prompt.splitlines() if l.strip().rstrip('.') == name or re.match(rf'\s*(Reference set of|Character sheet of|The subject:|Subject:|Title:|Name:)\s*{re.escape(name)}\b', l)]


# ---------- expected 1: a person's request has no name at all ----------

def test_a_persons_request_opens_with_what_the_picture_is_and_holds_no_name():
    r = request('MASON')
    assert r['prompt'].split('\n')[0] == RS.PERSON_OPENING and 'three' in RS.PERSON_OPENING.lower() and 'one person' in RS.PERSON_OPENING and '{' not in RS.PERSON_OPENING
    assert 'The mason' not in r['prompt'] and 'MASON' not in r['prompt'] and title_lines(r['prompt'], 'The mason') == []
    assert 'Reference set of' not in r['prompt'] and 'a person in this film' not in r['prompt']                       # the older opening line is retired
    assert 'Who they are: Lays the bricks. Works with his right hand.' in r['prompt'] and 'Fixed look: A lean man in his forties, short grey hair, a moustache.' in r['prompt']
    assert r['parts']['subject'] == 'The mason'                                                                      # the record and the page still know whose set it is


def test_the_operators_corrections_of_a_person_are_carried_without_the_name():
    s = ready()
    s['thing_corrections'] = {'MASON': [{'words': 'His shirt is blue.', 'set': None, 'by': 'u1', 'at': F.NOW}], 'STREET': [{'words': 'No cars.', 'set': None, 'by': 'u1', 'at': F.NOW}]}
    r = request('MASON', session=s)
    assert RS.CORRECTIONS_ONE.format(name='this person', words='His shirt is blue.') in r['prompt'] and 'The mason' not in r['prompt']
    assert RS.CORRECTIONS_ONE.format(name='The street', words='No cars.') in request('STREET', session=s)['prompt']       # a thing's corrections name the thing, as before


# ---------- expected 2: the same for every other kind ----------

@pytest.mark.parametrize('eid', THINGS)
def test_the_request_of_every_other_kind_has_no_title_line_with_the_name(eid):
    thing, r = el(eid), request(eid)
    name = thing['name']
    assert title_lines(r['prompt'], name) == [] and f'The subject: {name}' not in r['prompt'] and 'Reference set of' not in r['prompt']
    assert f'The subject: {WHAT[eid]} in this film.' in r['prompt']                                                   # what the picture is of, with no name
    assert name not in r['prompt'].split('\n\n')[0]                                                                  # nor in the opening
    assert f"Its description, from the film's plan: {name}. {thing['description']}" in r['prompt']                    # the name is the noun the description leans on: it opens that sentence
    assert r['parts']['subject'] == name


# ---------- row 1: two people who must be told apart ----------

def test_the_not_this_person_lines_carry_the_description_and_no_name():
    plan = with_person()
    r = request('MASON', plan=plan)
    assert RS.NOT_PERSON.format(description='A stocky young man, curly black hair') in r['prompt'] and 'Mason B' not in r['prompt'] and 'MASON_B' not in r['prompt']
    assert 'This person is not Mason B' not in r['prompt'] and '{' not in RS.NOT_PERSON.format(description='x')
    other = RS.set_request(plan, RUN, ready(plan=plan), el('MASON_B', plan), {})
    assert RS.NOT_PERSON.format(description='A lean man in his forties, short grey hair, a moustache') in other['prompt'] and 'The mason' not in other['prompt'] and 'Mason B' not in other['prompt']
    assert other['prompt'].split('\n')[0] == RS.PERSON_OPENING


def test_another_person_with_no_description_gives_no_line_and_no_name():
    r = request('MASON', plan=with_person(description=''))
    assert 'This person is not' not in r['prompt'] and 'Mason B' not in r['prompt']                                   # a name alone tells the image model nothing of how the other person looks


# ---------- row 2: a name that is the only description ----------

def test_a_thing_whose_name_is_its_only_description_keeps_the_name_in_the_description_sentence():
    r = request('FAN', plan=changed('FAN', description=''))
    assert "Its description, from the film's plan: Wall fan regulator" in r['prompt'] and title_lines(r['prompt'], 'Wall fan regulator') == []
    assert 'The subject: an object in this film.' in r['prompt'] and 'What it must meet: On the wall of the family room.' in r['prompt']


def test_a_person_whose_name_is_the_only_description_keeps_it_in_the_description_sentence():
    r = request('MASON', plan=changed('MASON', description='', requirements=''))
    assert 'Who they are: The mason' in r['prompt'] and r['prompt'].split('\n')[0] == RS.PERSON_OPENING and title_lines(r['prompt'], 'The mason') == []
    r = request('MASON', plan=changed('MASON', description=''))                                                      # their requirements describe them: no name
    assert 'The mason' not in r['prompt'] and 'Who they are: Lays the bricks.' in r['prompt']


# ---------- expected 3: the "no text" sentence, once and plain ----------

@pytest.mark.parametrize('eid', ('MASON',) + THINGS)
def test_the_no_text_sentence_is_said_once_as_a_plain_sentence(eid):
    prompt = request(eid)['prompt']
    said = [x for x in re.split(r'(?<=[.;])\s+|\n', prompt) if re.search(r'\bno text\b', x, re.I)]
    assert len(said) == 1 and len(re.findall(r'\bno text\b', prompt, re.I)) == 1 and prompt.lower().count('caption') == 1 and 'caption' in said[0]
    assert re.search(r'except (lettering|what) the description names', said[0])                                       # lettering the plan asks for stays allowed
    assert len(said[0].split()) <= 30                                                                                # one plain sentence, no long list of what is not wanted


def test_a_place_of_one_picture_says_it_once_too():
    s = ready()
    s['round']['place_one'] = True
    prompt = request('STREET', session=s)['prompt']
    assert RS.ONE_LINE in prompt and len(re.findall(r'\bno text\b', prompt, re.I)) == 1 and prompt.lower().count('caption') == 1


# ---------- row 3, expected 4 and 5: wanted lettering; the check stays ----------

def test_wanted_lettering_is_still_asked_and_the_check_does_not_fail_it():
    words = 'A grey paper cement bag with the brand name ACC printed in red on its face.'
    r = request('FAN', plan=changed('FAN', name='Cement bag', description=words))
    assert f"Its description, from the film's plan: Cement bag. {words}" in r['prompt'] and 'except what the description names' in r['prompt']
    line = next(l for l in r['lines'] if l['check'] == 'no text')
    assert line['weight'] == 'must' and line['pass_when'] == 'no caption, number, label, logo or watermark anywhere in the picture, except lettering the description names'
    assert words.rstrip('.') in next(l for l in r['lines'] if l['check'] == 'matches the description')['pass_when']       # the check reads the lettering as part of the description
    person = request('MASON', plan=changed('MASON', description='A lean man in a blue shirt with the word SITE on its back.'))
    assert 'the word SITE on its back' in person['prompt'] and 'except lettering the description names' in person['prompt']
    assert [l['check'] for l in person['lines']].count('no text') == 1                                                # the safety net stays, for every kind
    assert all([l['check'] for l in request(eid)['lines']].count('no text') == 1 for eid in THINGS)


# ---------- the failure mode: the model still prints a caption ----------

@pytest.mark.parametrize('eid', ('MASON', 'STREET', 'T_LAY'))
def test_a_remake_after_a_caption_adds_one_line_that_names_the_fault(eid):
    s = captioned(eid)
    assert RS.check_summary(s, s['round']['elements'][eid]['set'] + '-2')['failed'][0]['check'] == 'no text'        # the look failed the set, as today
    prompt = request(eid, session=s)['prompt']
    assert prompt.count(RS.CAPTION_AGAIN) == 1 and RS.CAPTION_AGAIN in prompt.split('\n') and 'caption' in RS.CAPTION_AGAIN and 'none is wanted' in RS.CAPTION_AGAIN.lower()
    assert len(re.findall(r'\bno text\b', prompt, re.I)) == 1                                                        # the line names the fault; the rule is not said a second time
    assert RS.CAPTION_AGAIN not in request(eid, session=ready('2'))['prompt']                                         # a set with no such fault: no line
    assert RS.CAPTION_AGAIN not in request(eid, session=s, row={**s['round']['elements'][eid], 'set': None})['prompt']   # a first make: no line


def test_another_fault_of_the_last_set_adds_no_caption_line_and_wanted_lettering_stays_allowed():
    s = ready('2')
    next(l for l in s['references']['s-street-1-2']['look']['lines'] if l['check'] == 'the view').update({'pass': False, 'seen': 'Not the view asked.'})
    assert RS.CAPTION_AGAIN not in request('STREET', session=s)['prompt']
    plan = changed('STREET', description='A sandy street with a shop sign that reads TEA in white letters.')
    prompt = request('STREET', plan=plan, session=captioned('STREET'))['prompt']
    assert RS.CAPTION_AGAIN in prompt and 'a shop sign that reads TEA' in prompt and 'except what the description names' in prompt   # the line speaks of an added caption only
    assert 'lettering' not in RS.CAPTION_AGAIN and 'text' not in RS.CAPTION_AGAIN.lower()


# ---------- row 4: a set made before this change ----------

def test_a_set_made_before_the_change_is_left_as_it_is():
    s, plan = ready('2'), F.plan()
    for eid in ('MASON', 'STREET', 'T_LAY'):
        row = s['round']['elements'][eid]
        row.setdefault('made', {})['fp'] = RS.fp(plan, s, el(eid))                                                   # made from the plan as it is; its stored request has the older words
        assert s['references'][row['set']]['generation']['prompt'] == f'the request of {eid}, make 1'
        assert RS.set_facts(s, plan, eid, row)['changed'] is False                                                    # nothing marks it as changed: it is not offered to be made again
    assert 'set_request' not in inspect.getsource(RS.fp) and 'prompt' not in inspect.getsource(RS.fp)                 # what a set was made from is the plan's words, never the request's wording
    store = store_of(copy.deepcopy(s))
    with pytest.raises(ValueError, match='STREET has its set: judge it'):                                            # and the server makes none of them again by itself
        VS.set_make(FakeConn([]), store, USER, RUN, [], 'STREET', quote='Make it again')


# ---------- what is known and what is a guess ----------

def test_the_code_says_the_cause_is_a_guess():
    text = inspect.getsource(RS)
    assert 'VW-25 issue 12' in text and 'a guess, not proven' in text
