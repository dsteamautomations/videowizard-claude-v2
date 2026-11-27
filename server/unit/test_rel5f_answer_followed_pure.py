"""Release 1 of 27 Nov 2026, phase 1, part F, rules 1 to 4 (SK approved, question 11): the operator's answer to the assistant's own question
(`vw visuals ask`) is followed. Before: the answer was recorded and "work goes on from this answer", with nothing checked (VW-25: "Still with
push-in" answered for S11-2 and S15-4, both made as AI video). Now the answer holds the shot until a plan change names it (`--answers`), or
the answer is the choice the assistant marked, when asking, as the one that keeps the item as it is. Each test failed first. Without a database."""
import pytest

from app import chat_flow as CF, visuals_stage as V
from app.errors import Problem
from test_design106_pure import revise_start, start_store
from test_rel3_plan_cards_pure import change, doc, film
from test_visuals_stage_pure import RUN, USER, FakeConn, g, saved

Q, CHOICES = 'A still with a push-in, or a trial AI video?', ['Still with push-in', 'Trial AI video']


def asked(store, item='VS1', words='Still with push-in', keeps=None):
    V.ask(store, USER, RUN, [], item, Q, CHOICES, keeps=keeps)
    return V.answer(store, USER, RUN, [], item, words)


def record(sess, item, **over):
    sess.setdefault('answered', []).append({'item': item, 'question': Q, 'choices': CHOICES, 'by': 'u1', 'answer': 'Still with push-in',
                                            'answered_by': 'u1', 'answered_at': '2026-11-27T10:00:00+00:00', 'holds': [item], **over})
    return sess['answered'][-1]


# ---------- rule 1: the answer holds the shot ----------

def test_an_order_for_the_shot_is_refused_with_the_question_and_the_answer():
    store = start_store()
    out = asked(store)
    assert 'goes on from this answer' not in out['next'] and '--answers VS1' in out['next'] and saved(store)['answered'][-1]['holds'] == ['VS1']
    for order in (lambda: revise_start(store, role='start'), lambda: V.bind(store, USER, RUN, [], 'VS1', {}, {}, '')):
        with pytest.raises(Problem) as e:
            g(order)
        words = str(e.value.message)
        assert Q in words and '"Still with push-in"' in words and '--answers VS1' in words and 'VS1' in words


def test_own_words_hold_the_shot_too_and_another_shot_is_not_held():
    store = start_store()
    asked(store, words='Make it a slow push-in on the lamp only')
    with pytest.raises(Problem, match='is not applied yet'):
        g(lambda: revise_start(store, role='start'))
    V._no_question(saved(store), 'VS2', 'K9')                               # nothing else is held


def test_a_question_on_a_thing_holds_every_shot_that_shows_it():
    store, sess, d = film(change(doc(), lambda s, _: (s['D2'].update(element_ids=['E2']), s['D1'].update(element_ids=['E2']))))
    assert V._holds(store, sess, 'E2') == ['E2', 'D1', 'D2']
    record(sess, 'E2', holds=['E2', 'D1', 'D2'])
    for sid in ('D1', 'D2'):
        with pytest.raises(ValueError, match='is not applied yet'):
            V._no_question(sess, sid)
    V._no_question(sess, 'P1')


def test_a_question_on_a_picture_holds_the_shot_it_was_made_for():
    store = start_store()
    assert V._holds(store, saved(store), 'K1') == ['K1', 'VS1']


def test_a_question_the_server_raised_itself_holds_nothing_after_its_answer():
    sess = {'answered': [{'item': 'VS1', 'question': 'Two start images for VS1: which one?', 'choices': ['K1', 'K2'], 'fork': 'slot', 'answer': 'K1'}]}
    V._no_question(sess, 'VS1')
    assert V.unapplied(sess) == []


# ---------- rule 2: the two ways to close it ----------

def test_the_choice_marked_as_keeping_the_item_closes_it_and_nothing_else_does():
    store = start_store()
    with pytest.raises(Problem, match='one of the choices'):
        g(lambda: V.ask(store, USER, RUN, [], 'VS1', Q, CHOICES, keeps='Leave it'))
    out = asked(store, words='Trial AI video', keeps='Trial AI video')
    assert saved(store)['answered'][-1]['applied'] == 'no change needed' and 'no change' in out['next']
    assert revise_start(store, role='start')['reference_id']                 # the work goes on
    store = start_store()
    asked(store, words='Still with push-in', keeps='Trial AI video')         # the other choice
    assert 'applied' not in saved(store)['answered'][-1]
    store = start_store()
    asked(store, words='trial ai video, but shorter', keeps='Trial AI video')   # own words are never closed this way
    assert 'applied' not in saved(store)['answered'][-1]


def test_a_plan_change_that_names_the_answer_and_alters_the_shot_releases_it():
    store, sess, d = film()
    q = record(sess, 'D2')
    V.new_version(store, RUN, sess, change(d, lambda s, _: s['D2'].update(purpose='a still with a slow push-in')), USER, [], answers='D2')
    assert q['plan_version'] == 2 and V.unapplied(sess) == []
    V._no_question(sess, 'D2')


def test_a_plan_change_that_names_the_answer_and_leaves_the_shot_as_it_was_is_refused():
    store, sess, d = film()
    q = record(sess, 'D2')
    with pytest.raises(ValueError, match='does not change D2'):
        V.new_version(store, RUN, sess, change(d, lambda s, _: s['D1'].update(purpose='another shot')), USER, [], answers='D2')
    assert len(sess['versions']) == 1 and 'plan_version' not in q            # nothing stored, the answer still waits


def test_a_plan_change_without_the_answers_name_leaves_the_shot_held():
    store, sess, d = film()
    record(sess, 'D2')
    V.new_version(store, RUN, sess, change(d, lambda s, _: s['D2'].update(purpose='changed, the answer not named')), USER, [])
    assert [r['item'] for r in V.unapplied(sess)] == ['D2']


def test_two_answers_on_one_shot_are_closed_each_on_its_own():
    store, sess, d = film(change(doc(), lambda s, _: s['D2'].update(element_ids=['E2'])))
    record(sess, 'D2'), record(sess, 'E2', holds=['E2', 'D2'])
    V.new_version(store, RUN, sess, change(d, lambda s, _: s['D2'].update(purpose='the closing card')), USER, [], answers='D2')
    assert [r['item'] for r in V.unapplied(sess)] == ['E2']
    with pytest.raises(ValueError, match='is not applied yet'):
        V._no_question(sess, 'D2')                                           # held until both are closed


def test_the_shot_leaving_the_plan_closes_its_answer():
    store, sess, d = film()
    q = record(sess, 'D2')
    new = change(d, lambda s, new: new['gaps'][1]['scenes'][0]['shots'].__setitem__(0, {**s['D2'], 'id': 'D9'}))
    V.new_version(store, RUN, sess, new, USER, [])
    assert q['applied'] == 'left the plan in version 2' and V.unapplied(sess) == []


def test_asking_again_replaces_the_answer_and_the_newest_counts():
    store = start_store()
    asked(store)
    V.ask(store, USER, RUN, [], 'VS1', 'Still or video, once more?', CHOICES, keeps='Trial AI video')
    assert saved(store)['answered'][-1]['applied'] == 'asked again'
    V.answer(store, USER, RUN, [], 'VS1', 'Trial AI video')
    assert V.unapplied(saved(store)) == [] and revise_start(store, role='start')['reference_id']


# ---------- rule 3: it is said until it is closed ----------

def test_the_status_and_the_next_step_line_name_each_answer_not_applied(monkeypatch):
    store = start_store()
    asked(store)
    line = V.unapplied_line(saved(store))
    assert 'VS1' in line and Q in line and '"Still with push-in"' in line and '--answers VS1' in line
    assert V.status(FakeConn([]), store, RUN, [], repair=False)['answers_due'] == line
    monkeypatch.setattr(CF, '_next_item', lambda *a, **k: {'item': None, 'then': 'Nothing waits.'})
    assert CF.next_item(FakeConn([]), store, USER, RUN, [])['then'].startswith(line)
    store = start_store()
    assert V.unapplied_line(saved(store)) == '' and 'answers_due' not in V.status(FakeConn([]), store, RUN, [], repair=False)


# ---------- rule 4: the gap is not recorded ----------

def test_a_gap_with_an_answer_not_applied_is_not_recorded():
    store = start_store()
    asked(store)
    gid = V.locate(store, saved(store), 'VS1')[1]['gap_id']
    with pytest.raises(Problem, match='is not applied yet'):
        g(lambda: V.record_gap(FakeConn([]), store, USER, RUN, [], gid, 'Record it'))
