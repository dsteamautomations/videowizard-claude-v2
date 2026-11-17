"""design/210, the wording review (16 Nov 2026), the server's side: after a step of the page, the assistant is sent to what really comes
next. F1: after the plan, and after the drawings and materials, the references come on the page (never `vw visuals next`), and the chat does
not ask a footage picture that step 1 of the round asks. C3: a round this answer already hands over is not asked for again. F2: Done on
step 1 of a round that makes sets is not undone. F6, F10: the reference drawings and a drawing's parts and sizes are approved on the page.
Without a database: the harnesses of test_design209_pure.py, test_design210_pure.py and test_design210b_pure.py."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
from app import chat_flow as CF, page_flow as P, visuals_stage as VS   # noqa: E402
from app.errors import Problem   # noqa: E402
from test_design151_refs_pure import OLD   # noqa: E402
from test_design209_pure import PANEL, dim, drawing, plan_with   # noqa: E402
from test_design210_pure import put_set   # noqa: E402
from test_design210b_pure import A, NEW, USER, ans, at_sets, back, film, page, record, saved, step1   # noqa: E402

APP = Path(__file__).resolve().parents[1] / 'app'
KEPT = {**H.RUN, 'film': NEW['film']}   # the harness film as a new one: its references are made as sets
GAPS_DONE, SPECS_DONE, DRAWN = 'Every gap of the plan is accepted. ', 'Every drawing and material is approved. ', 'Every reference drawing is approved. '


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})
    monkeypatch.setattr(VS, 'not_this', lambda *a, **k: {})
    P._MADE.clear()


def proposed(plan):
    """A plan proposed on the harness film, no gap accepted yet."""
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    H.propose(store, plan)
    return store, conn


def done(store, conn, run, choice):
    """Every open line of the page answered with `choice`, then done."""
    return P.page_record(conn, store, H.USER, run, {}, [ans(l, choice) for l in P.page(conn, store, H.USER, run, {})['lines'] if l['state'] == 'open'])


def put(store, session):
    store.files['run-1/visuals/session.json'] = json.dumps(session).encode('utf-8')


# ---------- F1: what comes after the plan, and after the drawings and materials ----------

def test_after_the_last_gap_with_no_spec_the_assistant_is_sent_to_the_references_not_to_the_chat():
    store, conn = proposed(plan_with([None, None]))
    r = done(store, conn, KEPT, 'accept')
    assert r['open'] == 0 and r['page']['step'] == 'Plan' and r['then'] == GAPS_DONE + P.REFS_START
    assert '`vw visuals next`' not in r['then'] and '`vw visuals digest`' in r['then'] and '`vw visuals look`' in r['then']   # design/211: the footage is searched first (was: the round file, then the page)


def test_after_the_last_drawing_or_material_the_assistant_is_sent_to_the_references_not_to_the_chat():
    store, conn = proposed(plan_with([drawing([dim('box', 'length', 600)])], PANEL))
    r = done(store, conn, KEPT, 'accept')
    assert r['page']['step'] == P.SPEC_STEP and r['open'] > 0 and 'still wait for the operator on the page' in r['then']   # the plan done: the drawings and materials are in this answer
    r = done(store, conn, KEPT, 'yes')
    assert r['open'] == 0 and r['then'] == SPECS_DONE + P.REFS_START and '`vw visuals next`' not in r['then']


def test_a_film_whose_references_are_not_made_as_sets_goes_on_in_the_chat_as_before():
    store, conn = proposed(plan_with([None, None]))
    assert done(store, conn, H.RUN, 'accept')['then'] == P.PLAN_NEXT and '`vw visuals next`' in P.PLAN_NEXT
    store, conn = proposed(plan_with([drawing([dim('box', 'length', 600)])], PANEL))
    done(store, conn, H.RUN, 'accept')
    assert done(store, conn, H.RUN, 'yes')['then'] == P.SPEC_NEXT and '`vw visuals next`' in P.SPEC_NEXT


def test_after_the_plan_the_reference_drawings_that_wait_are_handed_over_on_the_page():
    store, conn = proposed(plan_with([None, None]))
    put_set(store)
    r = done(store, conn, KEPT, 'accept')
    assert r['page']['step'] == P.DRAW_STEP and r['open'] == 1 and 'still wait for the operator on the page' in r['then'] and '`vw visuals next`' not in r['then']


def reopened():
    """A film whose round is started, with gap G1 of its plan to accept again: the page is at the plan."""
    store, conn = film()
    s = saved(store)
    s['accepted'].pop('G1')
    put(store, s)
    return store, conn


def test_after_the_plan_a_round_already_started_is_handed_over_and_no_second_page_call_is_asked_for():
    store, conn = reopened()
    p = page(store, conn)
    assert p['step'] == 'Plan'
    r = record(store, conn, [ans(l, 'accept') for l in p['lines'] if l['state'] == 'open'])
    assert r['page']['step'] == A and r['open'] == 3 and r['then'] == GAPS_DONE + P.REFS_HERE
    assert 'run `vw visuals page`' not in r['then'] and '`vw visuals next`' not in r['then']


def test_one_function_gives_the_next_step_of_the_page():
    store, conn = film(begin=False)
    ctx = CF._ctx(conn, store, USER, NEW, [])
    quiet_page = {'step': 'Plan', 'lines': [{'state': 'recorded'}]}
    assert P._after(ctx, quiet_page, 'Lead. ', 'END') == 'Lead. ' + P.REFS_START                      # the round is due
    assert P._after(ctx, {'step': 'Plan', 'lines': [{'state': 'with_assistant'}]}, 'Lead. ', 'END') == 'END'   # a line is back with the assistant: not yet
    store, conn = film()
    ctx = CF._ctx(conn, store, USER, NEW, [])
    assert P._after(ctx, quiet_page, 'Lead. ', 'END') == 'Lead. ' + P.REFS_GO                         # the round exists and this answer did not hand it over
    assert P._after(ctx, {'step': A, 'lines': []}, 'Lead. ', 'END') == 'Lead. ' + P.REFS_HERE         # it did
    store, conn = at_sets()
    r = record(store, conn, [ans(l, 'yes' if l['key'] == 'set:P1' else l['pics'][0]['choice']) for l in page(store, conn)['lines']])
    assert saved(store)['round']['pass'] == 'complete'
    assert P._after(CF._ctx(conn, store, USER, NEW, []), quiet_page, 'Lead. ', 'END') == 'END'          # the round is over: nothing of the page is left
    store, conn = film(begin=False)
    assert P._after(CF._ctx(conn, store, USER, OLD, []), quiet_page, 'Lead. ', 'END') == 'END'          # an older film: its references are not made as sets


# ---------- F1: the chat does not ask a footage picture before the round ----------

def test_before_the_round_the_chat_does_not_ask_a_footage_picture_and_says_where_it_is_answered():
    store, conn = film(begin=False)
    assert [w['kind'] for w in VS.waiting(saved(store), VS.current_plan(store, saved(store)), 'VW-20', [])] == ['picture to answer']   # the frame waits, as the status says
    got = CF.next_item(conn, store, USER, NEW, [])
    assert got['item'] is None and got['needed'] is False and got['how'].startswith(CF.FRAMES_ON_PAGE)
    assert '`vw visuals round --file out/reference-round.json`' in CF.FRAMES_ON_PAGE and '`vw visuals page`' in CF.FRAMES_ON_PAGE


def test_once_the_round_is_sent_the_chat_asks_the_thing_with_its_footage_picture_where_the_page_cannot_be_shown():
    store, conn = film()
    got = CF.next_item(conn, store, USER, NEW, [])
    assert got['item']['id'] == 'round1:E1' and CF.FRAMES_ON_PAGE not in got['item']['how']


def test_an_older_films_footage_picture_is_asked_in_the_chat_as_before():
    store, conn = film(begin=False)
    got = CF.next_item(conn, store, USER, OLD, [])
    assert got['item']['id'].startswith('picture:F1:')


def test_with_no_footage_picture_waiting_the_chat_says_nothing_about_the_references_step():
    store, conn = film(frames=(), begin=False)
    got = CF.next_item(conn, store, USER, NEW, [])
    assert got['item'] is None and CF.FRAMES_ON_PAGE not in got['how']


# ---------- C3: a round the answer hands over is not asked for again ----------

def test_after_the_last_reference_drawing_the_round_in_the_answer_is_written_and_no_second_page_call_is_asked_for():
    store, conn = film()
    s = saved(store)
    s['drawings'] = {'E2': {'status': 'proposed', 'sha256': 'b' * 64, 'name': 'Clamp kiln', 'views': [], 'facts': [], 'assumed': []}}
    put(store, s)
    r = record(store, conn, [ans(page(store, conn)['lines'][0], 'yes')])
    assert r['page']['step'] == A and r['page']['open'] is True and len(r['page']['lines']) == 3   # the References round is in this answer
    assert r['then'] == DRAWN + P.REFS_HERE and 'run `vw visuals page`' not in r['then'] and 'write' in P.REFS_HERE and 'link' in P.REFS_HERE
    assert 'run `vw visuals page`' in P.REFS_GO   # said only when the round was not handed over


# ---------- F2: Done on step 1 of a round that makes sets is not undone ----------

@pytest.mark.parametrize('state', ['making', 'back', 'complete'])
def test_done_on_step_one_is_not_undone_once_the_sets_are_ordered_and_the_refusal_says_what_to_do(state):
    store, conn = film()
    step1(store, conn)
    if state != 'making':
        back(store)
    if state == 'complete':
        record(store, conn, [ans(l, 'yes' if l['key'] == 'set:P1' else l['pics'][0]['choice']) for l in page(store, conn)['lines']])
    before = saved(store)
    with pytest.raises((Problem, ValueError)) as exc:
        VS.round_undo(store, USER, NEW, [], 'undo it')
    said = str(getattr(exc.value, 'message', '') or exc.value)
    assert 'cannot be undone' in said and 'paid' in said and '`vw visuals page`' in said and 'pass 1' not in said
    assert saved(store) == before   # nothing changed


def test_undo_before_done_on_such_a_round_says_there_is_nothing_to_undo():
    store, conn = film()
    with pytest.raises((Problem, ValueError), match='Nothing to undo'):
        VS.round_undo(store, USER, NEW, [], 'undo it')


# ---------- F6, F10: three texts of the server send the operator to the page ----------

def test_done_on_step_one_with_a_drawing_set_open_sends_the_operator_to_the_page():
    store, conn = film()
    s = saved(store)
    s['drawings'] = {'E2': {'status': 'proposed', 'sha256': 'b' * 64, 'name': 'Clamp kiln', 'views': [], 'facts': [], 'assumed': []}}
    put(store, s)
    with pytest.raises((Problem, ValueError)) as exc:
        VS.round_done(store, USER, NEW, [], {e: {'verdict': 'approve'} for e in ('E1', 'E2', 'P1')}, 'done', conn=conn)
    said = str(getattr(exc.value, 'message', '') or exc.value)
    assert 'on the page (`vw visuals page`); in the chat (`vw visuals next`) only where the page cannot be shown' in said


def test_the_wording_scripts_old_sentences_are_retired():   # design/211: its new sentences were replaced in turn (scripts/d211a, d211b, d211c), so applying it again is no longer tested here; `c1_split_v3.py --check` holds the chain
    root = APP.parents[1]
    st = next(s for s in json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
    sys.path.insert(0, str(root / 'scripts'))
    import d210c_wording_v3 as W
    retired = json.loads((root / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    text = json.dumps(st, ensure_ascii=False)
    assert W.RETIRED and all(old in retired and old not in text for old in W.RETIRED)
    cmd = (root / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert all(old not in cmd or old in new for old, new in W.COMMANDS)


def test_no_text_of_the_server_sends_a_page_step_to_the_chat():
    stage, drawings = (APP / 'visuals_stage.py').read_text(encoding='utf-8'), (APP / 'drawings.py').read_text(encoding='utf-8')
    assert 'approves it in the chat, in its turn' not in stage   # a drawing's parts and sizes: the page
    assert stage.count('is not approved, or changed since: the operator approves the drawings and the materials on the page (`vw visuals page`)') == 3
    assert 'looks at them in the chat' not in drawings
    assert 'on the page (`vw visuals page`); in the chat (`vw visuals next`) only where the page cannot be shown' in drawings
    for text in (P.PLAN_NEXT, P.SPEC_NEXT, P.DRAW_NEXT, P.REFS_START, P.REFS_GO, P.REFS_HERE, CF.FRAMES_ON_PAGE, VS.NO_UNDO):
        assert not any(w in text.lower() for w in ('building', 'construction', 'brick', 'documentary'))   # nothing tied to one kind of film
