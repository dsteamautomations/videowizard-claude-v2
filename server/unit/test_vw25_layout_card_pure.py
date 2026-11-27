"""A1 (SK, 25 Nov 2026: "Yes, checker decides"; requirements approved 26 Nov): the operator's layout drawing card is retired. When the fresh
checker passes a layout the shot goes on to its still at once: no card is made, the still's gate is "this scene's check passed" (or the
operator took a held layout as it is), and what the retired card showed of the layout ("Changed from the plan", the notes) is on the still's
card. The operator is asked about a layout only when it failed its check three times in a row, as before. A correction recorded before this
change keeps its shot "to change". The old approval and correction are refused by name. Each test failed first. Without a database."""
import json
from pathlib import Path

import pytest

from app import chat_flow as CF, guide as G, pictures as P, takes as T, visuals_stage as V
from test_design151_refs_pure import NEW
from test_guide_route_pure import OTHER, STILL_WORDS, frames_back, refused, scene, spec10, still_made, take_film   # noqa: F401 (take_film: the fixture)
from test_rel1d_layout_check_pure import SCENES, START, STILLS, changed, film, rendered, said, state, verdict
from test_visuals_stage_pure import USER, saved

ROOT = Path(__file__).resolve().parents[2]
RETIRED = ('The operator\'s approval of a layout drawing is retired (25 Nov 2026): the checker decides. '
           'A fault in the layout is said on the still\'s card.')
CAN_ORDER = 'first frame ready: the still can be ordered'


def ctx(store, conn):
    s = saved(store)
    return {'session': s, 'plan': V.current_plan(store, s), 'run': NEW, 'store': store, 'user': USER, 'outputs': [], 'conn': conn}


def layout_cards(store, conn):
    return CF._layout_items(ctx(store, conn))


def still_card(store, conn):
    (card,) = [i for i in CF._guide_items(ctx(store, conn)) if i['kind'] == 'still']
    return card


def passed(store, conn, spec=None):
    scene(store, conn, spec)
    sha = frames_back(store, conn)
    return sha, verdict(store, conn, sha, True)


def order(store, conn, **kw):
    return G.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}], **kw)


# ---------- a pass: no card, the still at once ----------

def test_a_pass_makes_no_card_and_the_still_can_be_ordered(take_film):
    store, conn = film(take_film)
    sha, out = passed(store, conn)
    assert layout_cards(store, conn) == [] and state(store) == ['being made']                      # the first frame is being made; nobody is asked
    assert 'their Yes' not in out['next'] and 'vw visuals next' not in out['next'] and 'then the still' in out['next']
    rendered(store)
    assert layout_cards(store, conn) == [] and state(store) == [CAN_ORDER] and said(store) == START + STILLS.format(ids='VS1', n=1) + '.'
    assert saved(store)['guides']['VS1']['drawing']['status'] == 'proposed'                         # nobody approved it: the check's pass is the approval
    still_made(store, conn)                                                                         # ordered, with no word of the operator


def test_before_the_pass_no_still_also_for_a_masked_repair(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    frames_back(store, conn)
    assert 'first frame of the layout is not rendered yet' in refused(lambda: order(store, conn))   # no pass: no first frame
    s = saved(store)
    s['guides']['VS1']['render'] = {'frame1_key': 'f1.png', 'frame1_sha256': 'sha-f1'}             # a first frame kept from somewhere, and still no pass
    s['guides']['VS1']['stills'] = [{'id': 'ST1', 'key': 'st.png', 'sha256': 'sha-st', 'status': 'approved', 'guide_sha256': 'an earlier scene'}]
    V.save_session(store, NEW, s)
    for no in (refused(lambda: order(store, conn)),
               refused(lambda: order(store, conn, repair_of='ST1', region={'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2}))):
        assert 'The layout of VS1 is not checked yet' in no and 'vw-guide-check' in no and 'operator' not in no
    assert state(store) == ['being checked by Claude'] and said(store).startswith(START + 'the checkers of the guides of VS1')
    nxt = G.status(conn, store, NEW, [], 'VS1')['next']
    assert 'vw-guide-check' in nxt and 'Yes' not in nxt


def test_a_failed_check_orders_no_still_and_the_rebuilt_layout_goes_on_at_its_pass_with_no_card(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    verdict(store, conn, frames_back(store, conn), False)
    assert layout_cards(store, conn) == [] and state(store) == ['being redone'] and said(store) == START + SCENES.format(ids='VS1', n=1) + '.'
    sha2, out = passed(store, conn, changed())
    rendered(store)
    assert layout_cards(store, conn) == [] and state(store) == [CAN_ORDER]                          # no card "this drawing replaces an earlier one" either
    assert not hasattr(G, 'REDRAWN')
    still_made(store, conn)


# ---------- the film in work at the deploy ----------

def test_a_correction_recorded_before_the_change_keeps_the_shot_to_change(take_film):
    store, conn = film(take_film)
    sha, _ = passed(store, conn)
    rendered(store)
    s = saved(store)
    s['guides']['VS1']['drawing'].update(status='rejected', verdict={'approved': False, 'quote': 'No.', 'notes': 'the mother faces the wrong way'})   # as the older server recorded it
    V.save_session(store, NEW, s)
    assert state(store) == ['being redone'] and said(store) == START + SCENES.format(ids='VS1', n=1) + '.' and layout_cards(store, conn) == []
    no = refused(lambda: order(store, conn))
    assert 'The operator corrected the layout of VS1 (the mother faces the wrong way)' in no and '`vw guide scene' in no
    assert 'the mother faces the wrong way' in G.status(conn, store, NEW, [], 'VS1')['next']
    passed(store, conn, changed())                                                                  # the scene is rebuilt and checked
    rendered(store)
    assert state(store) == [CAN_ORDER] and layout_cards(store, conn) == []                          # and goes on without a card
    still_made(store, conn)


def test_a_layout_approved_before_the_change_goes_on_as_before(take_film):
    store, conn = film(take_film)
    passed(store, conn)
    rendered(store)
    s = saved(store)
    s['guides']['VS1']['drawing'].update(status='approved', verdict={'approved': True, 'quote': 'Yes.'})
    V.save_session(store, NEW, s)
    assert state(store) == [CAN_ORDER] and layout_cards(store, conn) == []
    still_made(store, conn)


def test_an_answer_to_a_layout_card_shown_before_the_change_is_refused_by_name(take_film, monkeypatch):
    store, conn = film(take_film)
    sha, _ = passed(store, conn)
    monkeypatch.setattr(CF, '_ctx', lambda *a, **k: (_ for _ in ()).throw(AssertionError('refused before anything is read')))
    for choice in ('yes', 'correct'):
        assert refused(lambda: CF.answer(conn, store, USER, NEW, [], f'shot-drawing:VS1:{sha[:10]}', choice, 'Yes.', 'her arm')) == RETIRED + ' Run `vw visuals next`.'
    assert saved(store)['guides']['VS1']['drawing']['status'] == 'proposed'


def test_the_old_approval_and_the_old_correction_are_refused_by_name(take_film):
    store, conn = film(take_film)
    sha, _ = passed(store, conn)
    before = json.dumps(saved(store)['guides'], sort_keys=True)
    assert refused(lambda: G.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, True, 'Yes.')) == RETIRED
    assert refused(lambda: G.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, False, 'No.', 'her arm')) == RETIRED
    assert json.dumps(saved(store)['guides'], sort_keys=True) == before                             # nothing is recorded
    assert not hasattr(G, 'NOT_APPROVED')


# ---------- the held layout: as before ----------

# Retired with release 1 of 27 Nov 2026, phase 4 part A (SK: the operator never approves a layout): test_a_layout_that_failed_three_times_is_still_put_to_the_operator_and_use_it_lets_the_still_be_ordered
# (the held-layout card is gone; the server goes on by itself: unit/test_rel8a_no_layout_pure.py)


# ---------- what the operator still sees of the layout: on the still's card ----------

def test_the_stills_card_carries_what_the_layout_changed_from_the_plan_and_its_notes(take_film, monkeypatch):
    store, conn = film(take_film)
    monkeypatch.setattr(P, 'start_offered', lambda *a, **k: True)
    spec = spec10()
    spec['changed_from_plan'] = ['The mason stands at the left of the kiln, facing right.', 'The mother is left out: she is not in this moment.']
    passed(store, conn, spec)
    rendered(store)
    s = saved(store)
    s['guides']['VS1']['drawing']['notes'] = ['The kiln is drawn as a box: it has no drawing set.']
    V.save_session(store, NEW, s)
    still_made(store, conn)
    text = still_card(store, conn)['text']
    assert text.endswith('Changed from the plan to make the shot possible:\n- The mason stands at the left of the kiln, facing right.\n'
                         '- The mother is left out: she is not in this moment.\nNotes:\n- The kiln is drawn as a box: it has no drawing set.')
    assert G.layout_lines(saved(store)['guides']['VS1'])[0] == 'Changed from the plan to make the shot possible:'


def test_a_layout_that_changed_nothing_and_has_no_notes_leaves_the_stills_card_as_it_was(take_film, monkeypatch):
    store, conn = film(take_film)
    monkeypatch.setattr(P, 'start_offered', lambda *a, **k: True)
    passed(store, conn)
    rendered(store)
    s = saved(store)
    s['guides']['VS1']['drawing'].update(notes=[], changes=[])
    V.save_session(store, NEW, s)
    still_made(store, conn)
    card = still_card(store, conn)
    assert 'Changed from the plan' not in card['text'] and 'Notes:' not in card['text'] and G.layout_lines(saved(store)['guides']['VS1']) == []
    assert [b['label'] for b in card['buttons']] == ['Approve', 'Reject']
    s = saved(store)
    s['guides']['VS1']['drawing'].update(sha256='an earlier scene', changes=['An old line.'])       # a drawing of another scene says nothing of this one
    assert G.layout_lines(s['guides']['VS1']) == []


# ---------- the words ----------

def test_the_status_and_the_next_step_lines_say_the_new_way(take_film):
    store, conn = film(take_film)
    out = scene(store, conn)
    assert 'After the check passes the still is ordered' in out['next'] and 'approve' not in out['next']
    sha = frames_back(store, conn)
    assert 'its guide is rendered, and its still can be ordered, only after its check passes' in said(store) and 'shown to the operator' not in said(store)
    verdict(store, conn, sha, True)
    again = refused(lambda: verdict(store, conn, sha, True))                                        # one verdict for each scene: what comes next is said the new way
    assert 'Its first frame is made, then its still is ordered' in again and 'operator' not in again
    rendered(store)
    nxt = G.status(conn, store, NEW, [], 'VS1')['next']
    assert nxt.startswith('First frame ready: the still can be ordered') and 'Yes' not in nxt and "operator's answer" not in nxt


@pytest.mark.parametrize('name', ['procedures/v3.json'])
def test_the_instruction_no_longer_says_no_still_before_their_yes(name):
    text = (ROOT / 'server' / name).read_text(encoding='utf-8')
    for gone in ('no still before their Yes', 'asks the operator whether the shot is laid out right', 'before any layout card is shown', 'or several layout drawings of AI video shots'):
        assert gone not in text, gone
    assert 'after the check passes, order the still' in text
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert 'no still before their Yes' in retired
