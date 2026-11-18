"""design/215, change 5: the operator's corrections of a thing. Kept per thing in the session (`thing_corrections`), never in the plan's
description; carried by the server into every later request of that thing (a later set, a still, a start picture) and shown on its line. A
correction about one view stays on its set unless the operator ticks "This applies to every picture of this thing" (off by default). Two that
contradict are both kept in order, the later marked as the one in force. A plan revision keeps them by the thing's id; a thing the plan no
longer names takes its corrections with it. Without a database."""
import inspect

import pytest

from app import chat_flow as CF, page_flow as PF, ref_find, ref_sets as RS, visuals_stage as VS
import d211_fixture as F
from test_design211b_round_pure import at_two, back, done, film, fresh, jobs, judge, look, post, put, refused, saved   # noqa: F401
from test_design211b_sets_pure import RUN, el, finder   # noqa: F401 (finder stands in for part A, on every test)
from test_visuals_stage_pure import USER

DARK, LONG, SHORT = 'The side view is too dark.', 'Make the handle longer.', 'Make the handle shorter after all.'


@pytest.fixture(autouse=True)
def new_round(monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', 2)


def corrected(words, tick, store=None, conn=None, eid='T_LAY'):
    """A set judged "Minor corrections" with the words; `tick`: "applies to every picture of this thing"."""
    if store is None:
        store, conn = at_two()
    out = judge(store, conn, {eid: {'verdict': 'correct', 'words': words, **({'all': True} if tick else {})}})
    assert out['rewrite'] == [eid]
    return store, conn


def test_ticked_words_that_break_a_wording_rule_are_refused_when_given_and_nothing_is_kept():
    store, conn = at_two()
    with pytest.raises(Exception) as exc:
        VS.guarded(lambda: judge(store, conn, {'T_LAY': {'verdict': 'correct', 'words': 'Show the brand logo on the bag.', 'all': True}}))
    assert 'cannot be kept for every picture' in str(getattr(exc.value, 'message', exc.value))
    assert not saved(store).get('thing_corrections')


def test_a_correction_about_one_view_stays_on_its_set():
    store, conn = corrected(DARK, tick=False)
    s = saved(store)
    assert 'thing_corrections' not in s and s['round']['elements']['T_LAY']['operator_words'][-1] == DARK   # the next make of this set has the words, as before
    assert RS.corrections_of(s, F.plan(), 'T_LAY') == [] and RS.corrections_line(s, F.plan(), 'T_LAY') == ''


def test_a_ticked_correction_is_kept_for_the_thing_and_the_plan_is_not_touched():
    plan = F.plan()
    before = (ref_find.fingerprint(el('T_LAY')), el('T_LAY')['description'])
    store, conn = corrected(LONG, tick=True)
    s = saved(store)
    kept = s['thing_corrections']['T_LAY']
    assert [c['words'] for c in kept] == [LONG] and kept[0]['by'] == USER['id'] and kept[0]['at'] and kept[0]['set']
    assert (ref_find.fingerprint(el('T_LAY')), el('T_LAY')['description']) == before and plan == F.plan()   # no plan version, digest or fingerprint moves
    assert RS.corrections_of(s, plan, 'T_LAY') == [LONG]
    assert RS.corrections_line(s, plan, 'T_LAY') == "The operator's corrections of Laying a brick: Make the handle longer."


def test_two_corrections_that_contradict_are_both_kept_and_the_later_is_in_force():
    store, conn = corrected(LONG, tick=True)
    s = saved(store)
    s['thing_corrections']['T_LAY'].append({'words': SHORT, 'at': 'later', 'by': USER['id'], 'set': 'x'})
    assert RS.corrections_of(s, F.plan(), 'T_LAY') == [LONG, SHORT]
    assert RS.corrections_line(s, F.plan(), 'T_LAY') == ("The operator's corrections of Laying a brick, in the order given; where two disagree the later one wins: "
                                                           '(1) Make the handle longer; (2) Make the handle shorter after all.')
    assert RS.corrections_shown(s, F.plan(), 'T_LAY') == [LONG, SHORT + ' (the later one: in force where the two disagree)']
    assert RS.corrections_shown({'thing_corrections': {'T_LAY': s['thing_corrections']['T_LAY'][:1]}}, F.plan(), 'T_LAY') == [LONG]


def test_a_later_set_of_the_thing_carries_the_corrections_above_everything_else():
    store, conn = corrected(LONG, tick=True)
    s = saved(store)
    row = s['round']['elements']['T_LAY']
    req = RS.set_request(F.plan(), RUN, s, el('T_LAY'), row)
    assert req['prompt'].count(LONG.rstrip('.')) == 1 and "The operator's words: Make the handle longer." in req['prompt']   # the set just corrected: said once
    row['operator_words'].append(DARK)   # a later correction of one view of that set: both are in the request
    req = RS.set_request(F.plan(), RUN, s, el('T_LAY'), row)
    assert "The operator's corrections of Laying a brick: Make the handle longer." in req['prompt'] and "The operator's words: The side view is too dark." in req['prompt']
    assert req['parts']['corrections'] == [LONG] and req['parts']['operator'] == DARK and "(1) the operator's words" in req['prompt']
    assert any(LONG.rstrip('.') in l['pass_when'] and DARK.rstrip('.') in l['pass_when'] for l in req['lines'])   # the check judges by both
    row['operator_words'] = []   # a set of the thing made later with no words of its own still carries the thing's corrections, with the operator's rank
    req = RS.set_request(F.plan(), RUN, s, el('T_LAY'), row)
    assert "The operator's corrections of Laying a brick: Make the handle longer." in req['prompt'] and "(1) the operator's words" in req['prompt']


def test_stills_and_start_pictures_of_the_thing_carry_them_and_a_fix_or_a_set_does_not_get_the_line_twice():
    store, conn = corrected(LONG, tick=True)
    s = saved(store)
    line = "The operator's corrections of Laying a brick: Make the handle longer."
    out = VS.with_corrections(s, F.plan(), 'A brick is lowered.', ['T_LAY', 'BRICK', 'T_LAY'])
    assert out.startswith('A brick is lowered.') and out.count(line) == 1
    assert VS.with_corrections(s, F.plan(), 'A brick is lowered.', ['BRICK']) == 'A brick is lowered.'
    src = inspect.getsource(VS.generate_image)
    gate = src.split("with_corrections(session, plan, body['prompt']")[0].splitlines()[-2]   # a set's request places them itself; a fix is one change
    assert 'v2row is None' in gate and "not body.get('fix_of')" in gate


def test_a_plan_revision_keeps_them_by_the_things_id_and_a_removed_thing_takes_them_with_it():
    store, conn = corrected(LONG, tick=True)
    s = saved(store)
    plan = F.plan()
    next(e for e in plan['elements'] if e['id'] == 'T_LAY').update(description='A new description from the revised plan.', name='Brick laying')
    assert RS.corrections_of(s, plan, 'T_LAY') == [LONG] and 'Brick laying' in RS.corrections_line(s, plan, 'T_LAY')
    plan['elements'] = [e for e in plan['elements'] if e['id'] != 'T_LAY']
    assert RS.corrections_of(s, plan, 'T_LAY') == [] and VS.with_corrections(s, plan, 'x', ['T_LAY']) == 'x'


def test_the_answer_kept_before_done_holds_the_tick_and_done_records_it_once():
    store, conn = at_two()
    VS.guarded(lambda: VS.set_answer(store, USER, RUN, [], 'T_LAY', 'correct', None, LONG, all=True))
    assert saved(store)['round']['elements']['T_LAY']['answer']['all'] is True and 'thing_corrections' not in saved(store)   # nothing half stored
    VS.guarded(lambda: VS.set_answer(store, USER, RUN, [], 'T_LAY', 'correct', None, LONG))   # unticked again before done
    assert not saved(store)['round']['elements']['T_LAY']['answer'].get('all')
    VS.guarded(lambda: VS.set_answer(store, USER, RUN, [], 'T_LAY', 'correct', None, LONG, all=True))
    CF.flush_sets(conn, store, USER, RUN, [], 'done')   # "done": the stored answers, as both front ends record them
    assert [c['words'] for c in saved(store)['thing_corrections']['T_LAY']] == [LONG]


def test_a_correction_that_is_held_is_not_stored():
    store, conn = at_two()
    s = saved(store)
    s['cap_inr'] = 1   # the limit holds the remake: the answer waits, and so does its correction
    put(store, s)
    out = judge(store, conn, {'T_LAY': {'verdict': 'correct', 'words': LONG, 'all': True}})
    assert out['held'] == {'T_LAY': RS.LIMIT_PLAIN} and 'thing_corrections' not in saved(store) and saved(store)['round']['elements']['T_LAY']['answer']['all'] is True


def test_both_front_ends_offer_the_tick_and_show_the_corrections_on_the_things_line():
    store, conn = at_two()
    ctx = lambda: CF._ctx(conn, store, USER, RUN, [])
    item = next(i for i in CF._round_items(ctx(), every=True) if i['id'].startswith('set:T_LAY'))
    fix = next(b for b in item['_line']['buttons'] if b['act'] == 'fix')
    assert fix['all'] == {'label': 'This applies to every picture of this thing', 'choice': 'correct_all', 'say': CF.WORDS['say_fix_all']} and fix['choice'] == 'correct'
    chat = {b['choice']: b for b in item['buttons'] + list(item.get('other_choices') or [])}
    assert chat['correct_all']['label'] == 'Correct every picture of it' and chat['correct_all']['needs_words'] is True
    assert 'corrections' not in item['_line']
    item['_run']('correct_all', 'Correct every picture of it', LONG)
    assert [c['words'] for c in saved(store)['thing_corrections']['T_LAY']] == [LONG] and saved(store)['round']['elements']['T_LAY']['rewrite_due']['words'] == LONG
    s = saved(store)
    s['thing_corrections'] = {'TROWEL': [{'words': LONG, 'at': 'a', 'by': 'u', 'set': 'x'}, {'words': SHORT, 'at': 'b', 'by': 'u', 'set': 'y'}]}
    put(store, s)
    shown = [LONG, SHORT + ' (the later one: in force where the two disagree)']
    lines = {i['_eid']: i for i in CF._round_items(ctx(), every=True) if i.get('_eid')}
    s['thing_corrections']['MASON'] = s['thing_corrections']['TROWEL']
    put(store, s)
    mason = next(i for i in CF._round_items(ctx(), every=True) if i.get('_eid') == 'MASON')['_line']   # a set to judge: its line shows them, on the page and in the chat
    assert mason['corrections'] == shown and "The operator's corrections: " + LONG in CF._told(mason)
    assert PF._details({'corrections': shown})[0] == ["The operator's corrections", shown]
