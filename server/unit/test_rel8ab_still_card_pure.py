"""Release 1 of 27 Nov 2026, phase 4, parts A (rules 3 to 6) and B (SK: one approving button).

A: the card of the picture that starts an AI video shot shows that picture alone and asks what it shows; a picture whose check failed is made
again once by itself. B: its approving button reads "Approve and shoot (about ₹N)" and is the operator's word for the paid take, which the
server orders when the take's words and the layout video both exist; a typed "not yet" approves the picture only. Without a database."""
import pytest

from app import chat_flow as CF, guide as G, pictures as P, takes as T, visuals_stage as V
from app.errors import Problem
from test_design151_refs_pure import NEW
from test_design222_takes_pure import NOW, RUN, USER as OP, guide, held, job, plan, session, shot, states   # noqa: F401 (held: the fixture)
from test_guide_route_pure import STILL_WORDS, refused, still_made, take_film   # noqa: F401 (take_film: the fixture)
from test_rel3b_critic_pure import item, still_to_answer, videos, with_a_still
from test_rel4_first_frame_pure import TAKE_WORDS, back
from test_visuals_stage_pure import USER, saved

FAILED = {'sha256': 's' * 64, 'lines': [{'id': '1', 'check': 'on the layout', 'pass': False, 'seen': 'The mason is missing.'}]}
PASSED = {'sha256': 's' * 64, 'lines': []}
SAID = 'Yes, that is the kiln.'


def pure(s, p, monkeypatch, rows=()):
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run, sid=None: [j for j in rows if sid in (None, j['unit'])])
    return CF._guide_items({'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': OP, 'outputs': [], 'conn': None})


def one(still='candidate', look=PASSED, **more):
    s, p = session(), plan(shot('S1', title='Mason'))
    s['guides']['S1'] = guide(still=still, prompt=False, **more)
    if look:
        s['guides']['S1']['stills'][0]['check_look'] = look
    return s, p


# ---------- A: what the card shows ----------

def test_the_card_shows_the_picture_alone_with_the_new_question_the_price_and_no_word_of_the_layout(take_film):
    store, conn = with_a_still(take_film)
    card = CF.next_item(conn, store, USER, NEW, [])['item']
    assert [x['name'] for x in card['show']] == ['VS1-still.png']                                    # one picture: no overlay, no layout frame
    assert card['ask'] == 'Is it what the shot should show?' and 'this picture starts the shot' in card['message']
    assert [b['label'] for b in card['buttons']] == ['Approve and shoot (about ₹30)', 'Reject'] and card['buttons'][0]['description'] == 'The picture is right; its take is made (paid)'
    assert [b['choice'] for b in card['other_choices']] == ['later']
    assert 'The take is 10 s and costs about ₹30. It is made on your approval, as soon as its words are written.' in card['message']
    shown = ' '.join([card['message'], card['ask']] + [b['label'] + b['description'] for b in card['buttons']]).lower()
    assert not any(w in shown for w in ('outline', 'overlay', 'guide'))
    assert 'never a rejection: record it as `--choice later`' in card['how'] and '`--choice reject` with their words as `--notes`' in card['how']


def test_the_warnings_before_paying_are_on_the_pictures_card(held, monkeypatch):
    s, p = one(checks=[{'check': 'untried', 'message': 'This kind of shot has not been tried here.', 'before_take': True}])
    held(s, p)
    card = pure(s, p, monkeypatch)[0]
    assert 'Before you pay: This kind of shot has not been tried here.' in card['text'] and card['question'].endswith(': this picture starts the shot. Is it what the shot should show?')


# ---------- A, rule 6: one remake by itself ----------

def test_a_picture_whose_check_failed_is_named_for_one_remake_and_no_card_is_shown(held, monkeypatch):
    s, p = one(look=FAILED)
    held(s, p)
    assert pure(s, p, monkeypatch) == [] and states(s, p, []) == [('S1', 'being checked by Claude')]
    line = P.starts_failed(s, p)
    assert len(line) == 1 and "did not pass Claude's check: on the layout: The mason is missing. Make it again once now, without asking the operator" in line[0] and line[0] in P.waits_words(s, p)
    s['still_retries'] = {'S1': {'of': 'st0', 'by': 'st1'}}                                          # the remake failed too: it goes to the operator with the finding
    card = pure(s, p, monkeypatch)[0]
    assert P.starts_failed(s, p) == [] and 'on the layout: The mason is missing.' in card['text'] and not card['buttons'][0].get('needs_words')   # Approve works with one click


@pytest.mark.parametrize('case', ['not checked', 'the operator sent one back', 'passed'])
def test_no_remake_when_the_check_could_not_run_passed_or_the_operator_already_corrected(held, monkeypatch, case):
    s, p = one(look={'sha256': 's' * 64, 'not_checked': True, 'lines': []} if case == 'not checked' else PASSED if case == 'passed' else FAILED)
    if case == 'the operator sent one back':
        s['guides']['S1']['stills'].insert(0, {'id': 'st0', 'status': 'rejected', 'guide_sha256': 'g' * 64, 'rejection': {'by': 'u1', 'notes': 'The wall is too low.'}})
    held(s, p)
    assert P.starts_failed(s, p) == [] and [i['kind'] for i in pure(s, p, monkeypatch)] == ['still']


def failing(store):
    s = saved(store)
    s['guides']['VS1']['stills'][-1]['check_look'] = {**FAILED, 'sha256': 'sha-still'}
    V.save_session(store, NEW, s)


def test_the_remake_is_counted_when_it_is_ordered_and_the_first_picture_stays_as_the_earlier_try(take_film):
    store, conn = with_a_still(take_film)
    failing(store)
    assert CF.next_item(conn, store, USER, NEW, []).get('item') is None                               # nothing is shown
    new = G.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}])['still_id']
    s = saved(store)
    first = s['guides']['VS1']['stills'][0]
    assert s['still_retries']['VS1']['of'] == first['id'] and s['still_retries']['VS1']['by'] == new and s['still_retries']['VS1']['lines'] == 'on the layout: The mason is missing.'
    assert first['status'] == 'rejected' and first['rejection']['by'] == 'server' and "Claude's check failed" in first['rejection']['notes']


def test_no_remake_at_the_cost_limit_the_first_picture_goes_to_the_operator(take_film, monkeypatch):
    store, conn = with_a_still(take_film)
    failing(store)
    monkeypatch.setattr(V, 'check_cap', lambda *a, **k: (_ for _ in ()).throw(Problem(409, 'COST_CAP', 'The cost limit of the run is reached.')))
    assert refused(lambda: G.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}])) == 'The cost limit of the run is reached.'
    s = saved(store)
    assert s['still_retries']['VS1']['gave_up'] == 'The cost limit of the run is reached.' and len(s['guides']['VS1']['stills']) == 1
    assert item(store, conn, 'still:VS1')                                                             # shown with the check's finding


# ---------- B: one button ----------

def test_approve_and_shoot_approves_the_picture_and_orders_one_take_with_the_operators_words(take_film):
    store, conn = still_to_answer(take_film)
    out = CF.answer(conn, store, USER, NEW, [], item(store, conn, 'still:VS1'), 'approve', SAID)
    g = saved(store)['guides']['VS1']
    assert g['stills'][0]['status'] == 'approved' and g['stills'][0]['approval']['shoot'] is True and len(videos(conn)) == 1
    assert SAID in g['takes'][0]['quote'] and out['then'].startswith('The picture is approved and its take is being made.')
    CF.next_item(conn, store, USER, NEW, [])
    assert len(videos(conn)) == 1 and not any(i['kind'] == 'shoot' for i in CF._guide_items(CF._ctx(conn, store, USER, NEW, [])))   # once; no Shoot card


@pytest.mark.parametrize('last', ['the words', 'the video'])
def test_the_take_is_ordered_whichever_comes_last_the_words_or_the_video(take_film, last):
    store, conn = with_a_still(take_film)
    if last == 'the words':
        back(store, 'guide-render')
    out = CF.answer(conn, store, USER, NEW, [], item(store, conn, 'still:VS1'), 'approve', SAID)
    assert videos(conn) == [] and out['then'].startswith(G.SHOOT_ON_APPROVAL.format(shot='VS1'))
    G.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS)
    if last == 'the video':
        CF.next_item(conn, store, USER, NEW, [])
        assert videos(conn) == [] and 'auto_shoot' not in saved(store)['guides']['VS1']               # nothing is tried, and nothing counts as refused, before the video is there
        back(store, 'guide-render')
    CF.next_item(conn, store, USER, NEW, [])
    assert len(videos(conn)) == 1 and SAID in saved(store)['guides']['VS1']['takes'][0]['quote']
    CF.next_item(conn, store, USER, NEW, [])
    assert len(videos(conn)) == 1


def due(store):
    s = saved(store)
    return T.render_due(s, V.current_plan(store, s))


def test_a_typed_not_yet_approves_the_picture_only_and_the_take_waits_for_the_operators_word(take_film):
    store, conn = still_to_answer(take_film)
    out = CF.answer(conn, store, USER, NEW, [], item(store, conn, 'still:VS1'), 'later', 'The picture is fine, but not yet.')
    g = saved(store)['guides']['VS1']
    assert g['stills'][0]['status'] == 'approved' and 'shoot' not in g['stills'][0]['approval'] and out['then'].startswith(G.SHOOT_LATER.format(shot='VS1'))
    assert CF.next_item(conn, store, USER, NEW, []).get('item') is None and videos(conn) == []         # no card, no take
    assert G.shoot_state(saved(store), 'VS1') == ('later', '') and due(store).endswith('its picture is approved and everything for its take is ready, but its take is not ordered: the operator has not given the word for it. '
                                                                                         'On their word: `vw guide shoot --shot VS1 --quote "…"`.')
    assert G.shoot_state({**saved(store), 'questions': {'VS1': {'question': 'Which hand?'}}}, 'VS1') is None   # an open question on the shot: nothing ordered, nothing recorded as refused
    G.shoot(conn, store, USER, NEW, [], 'VS1', 'Now make it.')
    assert len(videos(conn)) == 1 and G.shoot_state(saved(store), 'VS1') is None and due(store) == ''


def test_a_refused_order_keeps_the_approval_is_said_in_the_next_step_line_and_is_not_tried_again(take_film, monkeypatch):
    store, conn = still_to_answer(take_film)
    sid, calls = item(store, conn, 'still:VS1'), []

    def cap(*a, **k):
        calls.append(1)
        raise Problem(409, 'COST_CAP', 'The cost limit of the run is reached.')
    monkeypatch.setattr(V, 'check_cap', cap)
    out = CF.answer(conn, store, USER, NEW, [], sid, 'approve', SAID)
    g = saved(store)['guides']['VS1']
    assert g['stills'][0]['status'] == 'approved' and videos(conn) == [] and g['auto_shoot']['refused'] == 'The cost limit of the run is reached.'
    assert out['answered'] == sid and 'VS1): its take was not ordered: The cost limit of the run is reached. When that is settled' in due(store)
    CF.next_item(conn, store, USER, NEW, [])
    assert len(calls) == 1                                                                             # once for this state of the shot
    monkeypatch.undo()
    G.shoot(conn, store, USER, NEW, [], 'VS1', 'The limit is raised: make it.')
    assert len(videos(conn)) == 1 and due(store) == ''


def test_a_rejected_picture_orders_nothing(take_film):
    store, conn = still_to_answer(take_film)
    CF.answer(conn, store, USER, NEW, [], item(store, conn, 'still:VS1'), 'reject', '', 'The kiln is on the wrong side.')
    assert saved(store)['guides']['VS1']['stills'][0]['status'] == 'rejected' and videos(conn) == [] and G.shoot_state(saved(store), 'VS1') is None


def test_send_it_again_after_a_failure_at_the_provider_stays_a_card(held, monkeypatch):
    s, p = session(), plan(shot('S1', title='Mason'))
    s['guides']['S1'] = guide(takes=['j1'])
    held(s, p)
    card = pure(s, p, monkeypatch, [job('j1', 'S1', status='failed')])[0]
    assert card['kind'] == 'shoot' and [b['label'] for b in card['buttons']] == ['Send it again', 'Not yet'] and [x['name'] for x in card['show']] == ['S1-still.png']
