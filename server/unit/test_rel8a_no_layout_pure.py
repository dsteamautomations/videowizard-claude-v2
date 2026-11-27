"""Release 1 of 27 Nov 2026, phase 4, part A (SK: "the operator never approves a Blender layout, in this step or any other").

After the third failed check in a row the server takes the layout as it is, by itself, and records that as its own decision with the
checker's finding. No layout card is left. Without a database."""
import pytest

from app import chat_flow as CF, guide as G, visuals_stage as V
from app.errors import Problem
from test_design151_refs_pure import NEW
from test_guide_route_pure import take_film   # noqa: F401 (the fixture)
from test_rel1d_layout_check_pure import cards, film, state
from test_rel2c_critic_pure import round_
from test_visuals_stage_pure import USER, g, saved


def three(take_film):
    store, conn = film(take_film)
    for n in range(3):
        out = round_(store, conn, n)
    return store, conn, out


def test_the_third_failed_check_goes_on_by_the_servers_decision_with_no_card(take_film):
    store, conn, out = three(take_film)
    assert out['next'].startswith('Round 3 failed, the third check in a row: the layout goes on as it is, by the server; the operator is not asked about a layout.')
    assert out['next'].endswith('Still open on the layout: nothing floats')
    guide = saved(store)['guides']['VS1']
    assert G.checked(guide) and not G.held(guide) and not G.rebuild(guide) and (guide.get('render') or {}).get('job_id')   # rendered as after "Use this layout as it is"
    assert guide['accepted']['by'] == 'server' and guide['accepted']['finding'] == 'nothing floats (the brush, above the board)' and guide['drawing']['verdict']['against_check'] is True
    assert cards(store, conn) == [] and 'waiting for you in the chat' not in state(store)


def test_two_failed_checks_still_ask_for_a_new_scene(take_film):
    store, conn = film(take_film)
    for n in range(2):
        out = round_(store, conn, n)
    assert out['next'] == 'Change the scene (one thing at a time) and upload it again: `vw guide scene`.' and not G.checked(saved(store)['guides']['VS1'])


def test_an_answer_to_the_retired_card_is_refused_by_name(take_film):
    store, conn, _ = three(take_film)
    with pytest.raises((Problem, ValueError), match='The card of a layout that failed its check three times is retired'):
        g(lambda: CF.answer(conn, store, USER, NEW, [], 'layout-held:VS1:abc', 'use', quote='Use this layout as it is'))
