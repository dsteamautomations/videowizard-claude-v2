"""VW-25 issue 13 (25 Nov 2026): an answer on a reference set that is ready is recorded at once. It is never refused, and never held back,
because another set is being made, waits for the assistant's look, or waits for its request to be written again. Each set is judged by its
own state (`visuals_stage._set_wait`); the round's state (`ref_sets.state`) only says whose turn it is and closes the round.

The round of these tests has one set in each state (`mixed`): MASON and STREET are ready, T_LAY waits for its rewrite, BRICK is back and not
looked at, TILE is being made. The real `visuals_stage`, `ref_sets`, `chat_flow` and `page_flow` run, on the film of design/211
(test_design211_together_pure). Every row of the note's table and each failure mode has its test. Without a database."""
import inspect
import json

import pytest

from app import chat_flow as CF, main, page_flow as P, ref_sets as RS, visuals_stage as VS
import d211_fixture as F
from test_design211_together_pure import PLAN_KEY, SESSION, USER, ans, approve, at_step_1, outside, png   # noqa: F401 (outside: what is outside the five modules, on every test)

WAIT = {'TILE': ('making', 'Roof tile'), 'BRICK': ('looking', 'Brick'), 'T_LAY': ('rewrite', 'Laying a brick')}


@pytest.fixture(autouse=True)
def _v2_round(monkeypatch, _older_round_tests):   # conftest: a module not named test_design211* posts an older round; these post the round of today
    monkeypatch.setattr(VS, 'ROUND_V', 2)


def put(film, s):
    film.store.files[SESSION] = json.dumps(s).encode('utf-8')


def back(film, *only):
    """The image worker brings back the sets of `only`; the other sets are still being made."""
    s = film.session()
    hold = [r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['status'] == 'generating' and r['element_id'] not in only]
    for rid in hold:
        s['references'][rid]['status'] = 'held by the test'
    put(film, s)
    film.back()
    s = film.session()
    for rid in hold:
        s['references'][rid]['status'] = 'generating'
    put(film, s)


def mixed(state='making'):
    """A round with one set in each state: MASON and STREET ready (made and looked at), T_LAY waiting for its rewrite, BRICK back and not looked
    at, TILE being made. `state='looking'`: TILE is back too and not looked at, so the round reads 'looking' (VW-25, 25 Nov, 05:32 UTC)."""
    film, _ = at_step_1()
    l = film.lines()
    film.record(ans(l['ref:TROWEL'], 'use'), ans(l['ref:FAN'], 'ignore'), ans(l['ref:BRICK'], 'set'), ans(l['ref:TILE'], 'set'), ans(l['refs:proposals'], 'accept_all'))
    film.back()
    film.set_looks()
    l = film.lines()
    film.record(ans(l['set:T_LAY'], 'correct', 'Show the hand pressing the brick down.'), ans(l['sets:rest'], 'rest'))
    back(film, *(('BRICK',) if state == 'making' else ('BRICK', 'TILE')))
    assert film.state() == state
    return film


def sets(film, verdicts, partial=True, quote='Sets done'):
    return film.do(lambda: VS.round_sets(film.store, USER, film.run, film.outputs, verdicts, quote, conn=film.conn, partial=partial, each=partial))


def flush(film):
    return film.do(lambda: CF.flush_sets(film.conn, film.store, USER, film.run, film.outputs, 'Answered on the page'))


def store_answer(film, eid, verdict='yes', words=''):
    """One answer stored and not recorded (`set_answer`), as it stands when the server stops between the two halves of an answer."""
    golden = film.row(eid)['set'] if verdict == 'yes' else None
    return film.do(lambda: VS.set_answer(film.store, USER, film.run, film.outputs, eid, verdict, golden, words))


def yes(film, eid):
    return {'verdict': 'yes', 'golden': film.row(eid)['set']}


def approved(film, eid):
    s = film.session()
    return [r['approval']['at'] for r in VS._set_rows(s, eid, s['round']['elements'][eid]['set'], ('approved',))]


def waits(eid):
    return VS.SET_WAITS[WAIT[eid][0]].format(name=WAIT[eid][1])


def remade(film, eid='STREET'):
    """The thing's set made again with no answer of the operator: its words in the plan changed and the assistant had it made again
    (`vw visuals round --make`). The pictures before are rejected; the new set is being made."""
    doc = json.loads(film.store.files[PLAN_KEY])
    next(e for e in doc['document']['elements'] if e['id'] == eid)['description'] = 'A wide paved street between low houses.'
    film.store.files[PLAN_KEY] = json.dumps(doc).encode('utf-8')
    assert film.do(lambda: VS.set_make(film.conn, film.store, USER, film.run, film.outputs, eid, quote='the plan changed'))['queued'] is True


def logged(film):
    return [p[8] for sql, p in film.conn.sql if 'vw2_log' in sql]   # the words of each log line


# ---------- row 1: every answer on a ready set is recorded, whatever the other sets wait for ----------

@pytest.mark.parametrize('state', ['making', 'looking'])
def test_the_answers_on_ready_sets_are_recorded_at_once_and_the_round_stays_open_for_the_others(state):
    film = mixed(state)
    l = film.lines()
    out = film.record(ans(l['set:MASON'], 'yes'), ans(l['set:STREET'], approve(l['set:STREET'])))
    assert sorted(out['recorded']) == ['set:MASON', 'set:STREET'] and out['kept'] == [] and out['refused'] == [] and out['stale'] == []
    s = film.session()
    rows = s['round']['elements']
    assert rows['MASON']['verdict'] == rows['STREET']['verdict'] == 'yes' and 'answer' not in rows['MASON'] and 'answer' not in rows['STREET']
    assert approved(film, 'MASON') and approved(film, 'STREET') and s['golden']['STREET'] == rows['STREET']['set'] and s['golden']['MASON'] == rows['MASON']['set']
    assert film.state() == state and s['round']['pass'] != 'complete'                # the round stays open for the sets that are not ready
    now = {x['key']: x for x in out['page']['lines']}
    assert now['set:MASON']['state'] == now['set:STREET']['state'] == 'recorded' and 'kept' not in now['set:MASON']
    assert 'sets still being made are back' not in json.dumps(out)                  # the older sentence of a kept answer is not said


# ---------- expected 3: a set that is not ready is not offered; it says what it waits for ----------

def test_a_set_that_is_not_ready_shows_what_it_waits_for_and_has_no_answer_buttons():
    film = mixed()
    l = film.lines()
    assert [(l[k]['state'], l[k]['note']) for k in ('set:TILE', 'set:BRICK', 'set:T_LAY')] == [
        ('making', CF.WORDS['making']), ('making', CF.WORDS['looking']), ('making', CF.WORDS['rewriting'])]
    assert all('buttons' not in l[k] and 'item' not in l[k] and 'own' not in l[k] for k in ('set:TILE', 'set:BRICK', 'set:T_LAY'))
    assert all(l[k]['state'] == 'open' and l[k]['buttons'] and l[k]['item'] for k in ('set:MASON', 'set:STREET'))
    assert [i['_eid'] for i in film.do(lambda: CF._round_items(CF._ctx(film.conn, film.store, USER, film.run, film.outputs), every=True))] == ['MASON', 'STREET']   # the chat asks the same two


# ---------- expected 1, 2 and 4, row 2: each set by its own state ----------

def test_each_set_is_judged_by_its_own_state():
    film = mixed()
    s = film.session()
    wait = lambda eid: VS._set_wait(s, eid, s['round']['elements'][eid])
    assert [wait(e) for e in ('MASON', 'STREET', 'TILE', 'BRICK', 'T_LAY')] == [None, None, 'making', 'looking', 'rewrite']
    assert RS.state(s, s['round']) == 'making'                                       # the round's state is kept, for the status line and for closing the round


def test_an_answer_for_a_set_that_is_not_ready_is_named_with_what_it_waits_for_and_the_ready_one_is_recorded():
    film = mixed()
    before = film.session()
    out = sets(film, {'STREET': yes(film, 'STREET'), 'TILE': {'verdict': 'no'}, 'BRICK': yes(film, 'BRICK'), 'T_LAY': {'verdict': 'correct', 'words': 'Another word.'}})
    assert out['approved'] == ['STREET'] and out['waiting'] == {e: waits(e) for e in ('TILE', 'BRICK', 'T_LAY')} and 'refused' not in out
    assert out['unanswered'] == ['MASON'] and out['pass'] == 'making'
    s = film.session()
    for eid in ('TILE', 'BRICK', 'T_LAY'):                                           # nothing of a set that is not ready was changed
        assert s['round']['elements'][eid] == before['round']['elements'][eid]
        assert [r for r in s['references'].values() if r.get('element_id') == eid] == [r for r in before['references'].values() if r.get('element_id') == eid]
    assert all(name in waits(e) for e, (_, name) in WAIT.items()) and 'being made' in waits('TILE') and 'looking' in waits('BRICK') and 'recorded' in waits('T_LAY')   # each names its thing and what it waits for


def test_a_send_that_names_only_sets_that_are_not_ready_records_nothing_and_says_why():
    film = mixed()
    out = sets(film, {'TILE': {'verdict': 'no'}})                                    # the page and the chat: never an error for a set's wait
    assert out['approved'] == [] and out['waiting'] == {'TILE': waits('TILE')} and film.state() == 'making'
    sets(film, {'MASON': yes(film, 'MASON'), 'STREET': yes(film, 'STREET')})
    assert film.refused(lambda: VS.round_sets(film.store, USER, film.run, film.outputs, {'BRICK': {'verdict': 'no'}}, 'No', conn=film.conn)) == waits('BRICK')   # the chat tool: refused by name
    assert film.refused(lambda: VS.set_answer(film.store, USER, film.run, film.outputs, 'T_LAY', 'no', None, '')) == VS.SET_WAITS['rewrite'].format(name='T_LAY')
    assert film.refused(lambda: VS.set_answer(film.store, USER, film.run, film.outputs, 'TILE', 'no', None, '')) == 'TILE: its set is being made: there is nothing to answer yet.'
    assert film.refused(lambda: VS.set_answer(film.store, USER, film.run, film.outputs, 'BRICK', 'no', None, '')) == RS.SET_NO_LOOK.format(eid='BRICK')


def test_the_sentence_of_the_round_level_gate_is_retired():
    text = inspect.getsource(VS) + inspect.getsource(CF) + inspect.getsource(P) + inspect.getsource(RS)
    assert 'No reference round is waiting for its sets' not in text and 'Done is offered when' not in text
    assert 'sets still being made are back' not in text and not hasattr(P, 'SETS_KEPT')
    film, _ = at_step_1()                                                           # a round that is not at its sets refuses in the sentence `set_answer` has
    assert film.refused(lambda: VS.round_sets(film.store, USER, film.run, film.outputs, {'MASON': {'verdict': 'yes'}}, 'Yes', conn=film.conn, partial=True)) == VS.NOT_AT_SETS
    assert film.refused(lambda: VS.set_answer(film.store, USER, film.run, film.outputs, 'MASON', 'yes', None, '')) == VS.NOT_AT_SETS


def test_an_answer_stored_on_a_set_that_is_with_the_assistant_again_stays_stored_and_is_recorded_without_the_operator():
    film = mixed()
    store_answer(film, 'STREET')
    s = film.session()
    look = s['round']['elements']['STREET'].pop('set_look')                          # the set is with the assistant again: its look is not recorded
    put(film, s)
    out = flush(film)
    assert out['waiting'] == {'STREET': VS.SET_WAITS['looking'].format(name='The street')} and out['approved'] == []
    assert film.row('STREET')['answer']['verdict'] == 'yes' and not approved(film, 'STREET')
    assert film.next()['item']['id'].startswith('set:MASON:')                        # and no other card is stopped by it
    s = film.session()
    s['round']['elements']['STREET']['set_look'] = look
    put(film, s)
    film.page()                                                                      # the next call of either front end records it
    assert film.row('STREET')['verdict'] == 'yes' and 'answer' not in film.row('STREET') and approved(film, 'STREET')


# ---------- row 3: the set was remade after the operator answered ----------

def test_an_answer_given_on_the_page_for_the_pictures_before_is_refused_by_name_with_the_reason():
    film = mixed()
    old = film.lines()['set:STREET']                                                 # the page the operator has open
    remade(film)
    said = VS.SET_REMADE.format(name='The street')
    out = film.record(ans(old, approve(old)), ans(film.lines()['set:MASON'], 'yes'))
    assert out['refused'] == [{'key': 'set:STREET', 'message': said}] and out['recorded'] == ['set:MASON'] and out['stale'] == []
    assert out['then'].startswith(P.ROUND_REFUSED) and 'The street' in said and 'made again' in said and 'answer' in said
    assert film.row('STREET')['verdict'] != 'yes' and 'STREET' not in film.session()['golden'] and 'answer' not in film.row('STREET')
    back(film, 'STREET')
    film.set_looks()
    new = film.lines()['set:STREET']                                                 # the new set is answered as any other
    assert new['item'] != old['item'] and film.record(ans(new, approve(new)))['recorded'] == ['set:STREET']


def test_an_answer_given_in_the_chat_for_the_pictures_before_is_refused_with_the_same_sentence():
    film = mixed()
    item = film.lines()['set:STREET']['item']
    remade(film)
    assert film.refused(lambda: CF.answer(film.conn, film.store, USER, film.run, film.outputs, item, 'yes', 'Yes')) == VS.SET_REMADE.format(name='The street')
    assert film.next()['item']['id'].startswith('set:MASON:')                        # the chat goes on with the next card


def test_a_stored_answer_of_the_pictures_before_is_dropped_and_the_operator_is_told_which_set_to_look_at_again():
    film = mixed()
    store_answer(film, 'STREET')                                                     # stored and not recorded (the server stopped); then the set was made again
    remade(film)
    back(film, 'STREET')
    film.set_looks()
    said = VS.SET_REMADE.format(name='The street')
    out = sets(film, {'MASON': yes(film, 'MASON')})                                  # whichever call comes next: the answer of the pictures before is never recorded
    assert out['approved'] == ['MASON'] and 'STREET' in out['unanswered'] and 'refused' not in out and not approved(film, 'STREET')
    line = film.lines()['set:STREET']                                                # the set's own line says which set to look at again, and why: on the page
    assert line['state'] == 'open' and line['refused'] == said and 'kept' not in line and line['buttons']
    card = next(i for i in film.do(lambda: CF._round_items(CF._ctx(film.conn, film.store, USER, film.run, film.outputs), every=True)) if i['_eid'] == 'STREET')
    assert card['text'].startswith(said)                                             # and on the chat's card
    out = film.record(ans(line, approve(line)))                                      # the new answer is recorded; the sentence is gone with the answer of before
    assert out['recorded'] == ['set:STREET'] and 'answer' not in film.row('STREET') and approved(film, 'STREET')
    assert 'refused' not in {x['key']: x for x in out['page']['lines']}['set:STREET']


# ---------- row 4: "Correct it" on one set while others are approved ----------

def test_a_correction_of_one_set_leaves_the_approvals_standing_and_only_that_set_is_made_again():
    film = mixed()
    l = film.lines()
    out = film.record(ans(l['set:MASON'], 'yes'), ans(l['set:STREET'], 'correct', 'The street is wider.'))
    assert sorted(out['recorded']) == ['set:MASON', 'set:STREET'] and out['refused'] == []
    at, n = approved(film, 'MASON'), len(film.ordered())
    assert at and film.row('STREET')['rewrite_due']['words'] == 'The street is wider.' and len(film.ordered()) == n   # nothing is ordered before the rewrite
    film.rewrite([{'element_id': 'STREET', 'prompt': 'A wider street, as the operator says.'}])
    assert film.ordered()[n:] == ['STREET'] and approved(film, 'MASON') == at and film.row('MASON')['verdict'] == 'yes'


# ---------- row 5: two sends at the same moment ----------

def test_the_second_of_two_sends_sees_what_the_first_recorded():
    film = mixed()
    line = film.lines()['set:MASON']
    assert film.next()['item']['id'] == line['item']                                 # the page and the chat hold the same card
    film.record(ans(line, 'yes'))
    at = approved(film, 'MASON')
    assert film.refused(lambda: CF.answer(film.conn, film.store, USER, film.run, film.outputs, line['item'], 'yes', 'Yes')) == VS.SET_RECORDED.format(name='The mason')
    assert approved(film, 'MASON') == at
    for door in (main.visuals_page_record, main.visuals_chat_answer):                 # both doors take the run's lock (`_visuals_run`, lock=True): one after the other
        assert '_visuals_call(' in inspect.getsource(door)
    assert 'lock=True' in inspect.getsource(main._visuals_run) and '_visuals_run(' in inspect.getsource(main._visuals_call)


# ---------- row 6: the same answer sent twice ----------

def test_the_same_answer_sent_twice_is_recorded_once_and_the_second_is_answered_already_recorded():
    film = mixed()
    l = film.lines()
    film.record(ans(l['set:MASON'], 'yes'), ans(l['set:STREET'], 'correct', 'The street is wider.'))
    at, words = approved(film, 'MASON'), film.row('STREET')['operator_words']
    out = film.record(ans(l['set:MASON'], 'yes'), ans(l['set:STREET'], 'correct', 'The street is wider.'))   # the page sends the same answers again
    assert sorted(out['recorded']) == ['set:MASON', 'set:STREET'] and out['refused'] == [] and out['stale'] == [] and out['kept'] == []
    assert approved(film, 'MASON') == at and film.row('STREET')['operator_words'] == words == ['The street is wider.']
    assert sorted(logged(film)[-2:]) == [VS.SET_RECORDED.format(name='The mason'), VS.SET_RECORDED.format(name='The street')]   # what each was answered, in the log
    assert out['tell'] in logged(film)[-2:] and out['then'].startswith(out['tell'])  # and the assistant is told so, in the answer of the send
    film.rewrite([{'element_id': 'STREET', 'prompt': 'A wider street, as the operator says.'}])
    out = film.record(ans(l['set:STREET'], 'correct', 'The street is wider.'))      # and once more after the set was ordered again: its answer was recorded, it is not "for the pictures before"
    assert out['recorded'] == ['set:STREET'] and out['refused'] == [] and film.row('STREET')['operator_words'] == words
    out = sets(film, {'MASON': yes(film, 'MASON')})                                  # the same through the function both front ends call
    assert out['already'] == ['MASON'] and out['approved'] == [] and approved(film, 'MASON') == at


# ---------- row 7: at the spend cap ----------

def test_at_the_spend_cap_a_yes_is_recorded_and_a_remake_is_held_with_its_reason():
    film = mixed()
    s = film.session()
    s['cap_inr'] = 1.0
    put(film, s)
    l, n = film.lines(), len(film.ordered())
    out = film.record(ans(l['set:MASON'], 'yes'), ans(l['set:STREET'], 'no'))
    assert out['recorded'] == ['set:MASON'] and [r['key'] for r in out['refused']] == ['set:STREET'] and out['refused'][0]['message'].startswith(RS.LIMIT_PLAIN) and approved(film, 'MASON')
    street = film.row('STREET')
    assert street['answer']['verdict'] == 'no' and 'rewrite_due' not in street and len(film.ordered()) == n and VS._set_rows(film.session(), 'STREET', street['set'])   # held: stored, nothing rejected, nothing ordered
    now = {x['key']: x for x in out['page']['lines']}['set:STREET']
    assert now['state'] == 'open' and now['refused'] == out['refused'][0]['message'] and now['kept_note'] == P.SETS_HELD


# ---------- row 8: the operator's own picture ----------

def test_an_own_picture_answer_is_recorded_when_its_line_is_ready_whatever_the_other_sets_wait_for():
    film = mixed('looking')
    s = film.session()
    s['references']['own-1'] = {'id': 'own-1', 'kind': 'supplied', 'element_id': 'STREET', 'status': 'approved', 'key': f"{film.run['id']}/visuals/references/own-1.png", 'sha256': 'o' * 64, 'created_at': F.NOW}
    put(film, s)
    film.store.files[s['references']['own-1']['key']] = png()
    line = film.lines()['set:STREET']
    out = film.record({**ans(line, 'own'), 'own_ref': 'own-1'})
    assert out['recorded'] == ['set:STREET'] and out['refused'] == [] and out['kept'] == []
    assert film.session()['golden']['STREET'] == 'own-1' and film.row('STREET')['verdict'] == 'yes' and film.state() == 'looking'


# ---------- failure mode 1: the server stops between two answers of one send ----------

def test_answers_not_yet_recorded_when_the_server_stopped_are_recorded_on_the_next_call():
    film = mixed('looking')
    store_answer(film, 'MASON')                                                      # stored, and the server stopped before it recorded them
    store_answer(film, 'STREET')
    assert not approved(film, 'MASON') and not approved(film, 'STREET')
    film.next()                                                                      # the next call, of either front end: nothing is lost, and the operator is not asked again
    assert approved(film, 'MASON') and approved(film, 'STREET') and 'answer' not in film.row('MASON') and 'answer' not in film.row('STREET')


def test_a_send_given_again_after_the_server_stopped_records_what_was_left_and_nothing_twice():
    film = mixed()
    l = film.lines()
    film.record(ans(l['set:MASON'], 'yes'))                                          # the first answer of the send was recorded; then the server stopped
    at = approved(film, 'MASON')
    out = film.record(ans(l['set:MASON'], 'yes'), ans(l['set:STREET'], approve(l['set:STREET'])))   # the page's answer record is sent again, whole
    assert sorted(out['recorded']) == ['set:MASON', 'set:STREET'] and out['refused'] == [] and out['stale'] == []
    assert approved(film, 'MASON') == at and approved(film, 'STREET')


# ---------- failure mode 2: one answer of a send is refused for a real reason ----------

def test_one_answer_refused_for_a_real_reason_does_not_stop_the_others_and_names_its_line():
    film = mixed()
    l = film.lines()
    out = film.record(ans(l['set:STREET'], 'correct', ''), ans(l['set:MASON'], 'yes'))   # a missing word
    assert out['recorded'] == ['set:MASON'] and [r['key'] for r in out['refused']] == ['set:STREET'] and out['refused'][0]['message'] == 'Say what should change in this line, in your own words.'
    assert {x['key']: x for x in out['page']['lines']}['set:STREET']['refused'] == out['refused'][0]['message']


def test_a_stored_answer_the_server_refuses_never_stops_the_answers_of_other_sets():
    film = mixed()
    s = film.session()
    s['round']['elements']['MASON']['made']['photo'] = 'a-photo-given-then'            # the set was made from the person's photo; the permission is no longer recorded
    put(film, s)
    l = film.lines()
    out = film.record(ans(l['set:MASON'], 'yes'), ans(l['set:STREET'], approve(l['set:STREET'])))
    assert out['recorded'] == ['set:STREET'] and [r['key'] for r in out['refused']] == ['set:MASON'] and out['refused'][0]['message'].startswith('MASON: this set was made from the person')
    assert approved(film, 'STREET') and not approved(film, 'MASON') and film.row('MASON')['answer']['verdict'] == 'yes'
    out = flush(film)                                                                # the refused answer stays stored; no later call fails for it
    assert out['refused']['MASON'].startswith('MASON: this set was made from the person') and out['approved'] == []
    assert film.next()['needed'] is False and film.page()['step'] == P.SETS_STEP
    with pytest.raises(ValueError, match='MASON: this set was made from the person'):   # the chat tool sends every set at once: one fault refuses the send, as before
        VS.round_sets(film.store, USER, film.run, film.outputs, {'MASON': {'verdict': 'yes'}}, 'Yes', conn=film.conn)


def test_words_that_cannot_be_kept_for_every_picture_refuse_that_answer_alone(monkeypatch):
    film = mixed()

    def check(words, placed=True):
        if 'forbidden' in words:
            raise ValueError('a word that cannot be sent')
    monkeypatch.setattr(VS.library, 'check_prompt', check)
    out = sets(film, {'STREET': {'verdict': 'correct', 'words': 'a forbidden word', 'all': True}, 'MASON': yes(film, 'MASON')})
    assert out['approved'] == ['MASON'] and out['refused'] == {'STREET': 'STREET: these words cannot be kept for every picture: a word that cannot be sent'}
    assert 'rewrite_due' not in film.row('STREET') and VS._set_rows(film.session(), 'STREET', film.row('STREET')['set']) and film.row('STREET')['operator_words'] == []   # nothing of it was recorded


# ---------- expected 5: when the round closes ----------

def test_the_round_closes_only_when_no_set_waits_and_every_set_has_its_answer():
    film = mixed('looking')
    l = film.lines()
    out = film.record(ans(l['set:MASON'], 'yes'), ans(l['set:STREET'], approve(l['set:STREET'])))   # every set that can be answered is answered
    assert film.session()['round']['pass'] != 'complete' and film.state() == 'looking' and out['then'].startswith(RS.SETS_LOOK)
    film.set_looks()
    assert film.state() == 'rewrite' and film.session()['round']['pass'] != 'complete'
    film.rewrite([{'element_id': 'T_LAY', 'prompt': 'The right hand presses the wet brick into the mortar bed.'}])
    l = film.lines()
    out = film.record(ans(l['set:BRICK'], approve(l['set:BRICK'])), ans(l['set:TILE'], approve(l['set:TILE'])))
    assert sorted(out['recorded']) == ['set:BRICK', 'set:TILE'] and film.state() == 'making' and film.session()['round']['pass'] == 'making'   # T_LAY is being made again
    film.back()
    film.set_looks()
    lay = film.lines()['set:T_LAY']
    out = film.record(ans(lay, approve(lay)))
    assert film.state() == 'complete' and film.session()['round']['pass'] == 'complete' and P.ROUND_NEXT in out['then']


# ---------- expected 6: the chat path, through the same function ----------

@pytest.mark.parametrize('state', ['making', 'looking'])
def test_an_answer_in_the_chat_is_recorded_at_once_too(state):
    film = mixed(state)
    item = film.next()['item']
    assert item['id'].startswith('set:MASON:')
    out = film.decide(item['id'], 'yes', 'Yes, use it')
    assert film.row('MASON')['verdict'] == 'yes' and approved(film, 'MASON') and 'answer' not in film.row('MASON') and out['pass'] == state
    assert 'kept' not in out['then'] and out['item']['id'].startswith('set:STREET:')    # no "your answer is kept"; the next card follows
    out = film.decide(out['item']['id'], out['item']['buttons'][0]['choice'], 'This one')
    assert film.row('STREET')['verdict'] == 'yes' and out['item'] is None and film.state() == state


def test_no_other_card_of_the_chat_is_refused_because_of_a_reference_set():
    film = mixed('looking')                                                          # VW-25, 25 Nov, 04:48 UTC: an answer on a layout was refused with the round's sentence
    store_answer(film, 'MASON')
    out = film.next()                                                                # `next_item` records what is stored and never fails for a set
    assert approved(film, 'MASON') and out['item']['id'].startswith('set:STREET:')
    assert '(ValueError, V.Problem)' in inspect.getsource(CF._next_item)
    # both front ends reach the sets through `round_sets` alone: the page answers through the chat item's own function
    assert 'V.round_sets(' in inspect.getsource(CF.flush_sets) and 'flush_sets(' in inspect.getsource(CF._record_set) and '_record_set(' in inspect.getsource(CF._round_v2)
    assert 'round_sets' not in inspect.getsource(P) and "item['_run'](" in inspect.getsource(P._round_answer)
