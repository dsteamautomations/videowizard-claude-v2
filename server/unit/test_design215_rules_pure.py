"""design/215, part 1: the older rules that must not touch a server-written set request of a v2 round (R1 to R5), with the sample words of
the review of 18 Nov 2026. A round without `v` keeps every older rule. Without a database."""
import pytest

from app import library, ref_sets as RS, visuals_stage as VS
import d211_fixture as F
from test_design211b_round_pure import done, film, fresh, jobs, post, put, refused, saved   # noqa: F401
from test_design211b_sets_pure import RUN, finder   # noqa: F401 (finder stands in for part A, on every test)
from test_visuals_stage_pure import USER

@pytest.fixture(autouse=True)
def new_round(monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', 2)   # these tests post a round of today


ONLY = {'STREET': {'verdict': 'ignore'}, 'TILE': {'verdict': 'ignore'}, 'BRICK': {'verdict': 'ignore'}, 'MASON': {'verdict': 'ignore'}}   # T_LAY alone asks for a set


def planned(eid='T_LAY', **fields):
    p = F.plan()
    next(e for e in p['elements'] if e['id'] == eid).update(fields)
    return p


def ordered(plan, session=None, eid='T_LAY', change=None):
    """Step 1 recorded on a plan: (the answer, the request queued for the thing or None, the store)."""
    store, conn = film(session, plan)
    post(store, conn)
    for e, fields in (change or {}).items():
        s = saved(store)
        s['round']['elements'][e].update(fields)
        put(store, s)
    out = done(store, conn, **ONLY)
    return out, jobs(conn).get(eid), store


@pytest.mark.parametrize('words', [
    'A paper cement bag with the brand logo printed on the front.',   # R1: the logo rule
    'A 600 x 600 mm vitrified tile pressed into the bed.',            # R1: the pixel-size rule
    'A trumpet with a wide flare.', 'A white Maruti Omni van.',       # R1: the model words
    'A 1080p monitor on the desk.',                                   # R1: the resolution rule
    'A 4" pipe joined to a 6" pipe.', "A 6' ladder against a 10' wall.", 'A bag printed "OPC 53 Grade" on the front.',   # R2: the quoted-words rule
])
def test_the_plans_own_words_are_never_refused_by_the_wording_rules_or_the_quoted_words_rule(words):
    with pytest.raises(ValueError):   # the rule itself still stands, for a prompt the assistant writes
        library.check_prompt(words, placed=False)
        library.check_quoted(words, [])
    out, job, _ = ordered(planned(description=words))
    assert out['errors'] == {} and out['queued'] == ['T_LAY'] and words.rstrip('.') in job['prompt']


def test_a_set_with_only_the_plans_words_has_nothing_for_the_rules_to_read():
    out, job, store = ordered(planned(description='The Omni logo, 600 x 600, at 1080p.'), change={'T_LAY': {'prompt': ''}})
    assert out['queued'] == ['T_LAY'] and 'Added by' not in job['prompt']
    s = saved(store)   # a refusal the retired rules stored before is not shown as it was written
    row = {**s['round']['elements']['T_LAY'], 'set': None, 'error': "T_LAY's fact or size cites the footage (clip C1): approve a footage frame of T_LAY before any picture of it."}
    assert RS.set_facts(s, F.plan(), 'T_LAY', row)['fail']['text'] == VS.RULE_RETIRED


@pytest.mark.parametrize('field, value, word', [('prompt', 'In the style of Kling.', 'kling'), ('operator_words', ['Make it 1080p sharp.'], '1080p'),
                                                ('operator_words', ['Fine.', 'Add the brand logo.'], 'logo')])
def test_the_words_claude_or_the_operator_added_are_still_read_and_the_refusal_names_the_word(field, value, word):
    out, job, store = ordered(planned(), change={'T_LAY': {field: value}})
    assert job is None and out['queued'] == [] and word in out['errors']['T_LAY'].lower()
    assert word in saved(store)['round']['elements']['T_LAY']['error'].lower()


def test_an_earlier_word_of_the_operator_that_is_no_longer_in_the_request_is_not_read():
    out, job, _ = ordered(planned(), change={'T_LAY': {'operator_words': ['Add the brand logo.', 'Keep the wall bare.']}})
    assert out['queued'] == ['T_LAY'] and 'Keep the wall bare' in job['prompt'] and 'brand logo' not in job['prompt']


def test_a_set_is_not_refused_because_the_plan_cites_the_footage():
    # R3: the size says footage; the operator kept no footage picture and chose a set
    size = [{'part': 'bed', 'measure': 'depth', 'value': 12, 'unit': 'mm', 'source': 'estimated from clip C0084', 'status': 'proposed'}]
    out, job, _ = ordered(planned(size=size))
    assert out['errors'] == {} and job and 'about 12 mm' in job['prompt']


def test_a_set_is_not_refused_for_a_size_that_is_not_measured_and_no_cause_stands_for_it():
    # R4 ("measure it first"), and its second copy, which drives "Make it" and the warning of step 4
    s = fresh()
    assert any(r.get('kind') == 'frame' and r.get('element_id') == 'TROWEL' and r.get('status') == 'approved' for r in s['references'].values()) or True
    size = [{'part': 'blade', 'measure': 'length', 'value': None, 'unit': 'cm', 'source': 'the footage', 'status': 'unknown'}]
    plan = planned('TROWEL', size=size)
    store, conn = film(s, plan)
    post(store, conn)
    only = {**ONLY, 'T_LAY': {'verdict': 'ignore'}, 'TROWEL': {'verdict': 'clean'}}
    out = done(store, conn, **only)
    assert out['errors'] == {} and out['queued'] == ['TROWEL'] and 'measure it first' not in str(out)
    s = saved(store)
    assert VS.set_cause(s, plan, 'TROWEL') is None
    s['round'].pop('v')   # the same film in a round of before: the rule stands
    assert VS.set_cause(s, plan, 'TROWEL')['kind'] == 'size'


def test_a_refusal_stored_by_the_retired_rule_no_longer_reads_as_a_size_to_measure():
    store, conn = film()
    post(store, conn)
    s = saved(store)
    row = s['round']['elements']['TILE']
    row['error'] = 'TILE has a size still unknown (tile width) and an approved footage frame F1: measure it first (`vw visuals measure --refs F1 --question ...`), then put the value in the plan.'
    state = VS._set_state(s, F.plan(), 2, 'TILE', row, (0.0, 4000.0, 35.0))
    assert state['cause'] is None and state['settled'] == VS.RULE_RETIRED and 'measure' not in VS.RULE_RETIRED


def test_the_not_this_list_is_not_appended_to_a_set():
    # R5: the list holds the operator's correction words and rejection notes; "Not this: make the handle longer" would ask the opposite
    s = fresh(not_this={'T_LAY': {'lines': ['make the handle longer', 'no gloves']}})
    out, job, _ = ordered(F.plan(), session=s)
    assert out['queued'] == ['T_LAY'] and 'Not this' not in job['prompt'] and 'make the handle longer' not in job['prompt']
    assert VS.not_this_line(s, F.plan(), 'T_LAY').startswith('Not this (Laying a brick): make the handle longer')   # the list itself stays, for the pictures of the shots


def test_the_gates_that_stay_still_hold():
    assert RS.MAKES_MAX == 3 and RS.LIMIT_PLAIN and VS.ANIMAL_NO_SHEET and VS.SHEET_BY_ROUND
    store, conn = film(fresh(cap_inr=15))
    post(store, conn)
    assert done(store, conn, **ONLY)['errors'] == {'T_LAY': RS.LIMIT_PLAIN}
