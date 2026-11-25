"""Issue 15 (VW-25, hotfix, SK 25 Nov 2026): a shared part that names its drawings (data-shots) is asked from those drawings only, also when it
draws a thing of the plan.

Seen on VW-25: the plan named one thing ("Filler slab cross-section") on every slab drawing, also on the two that show a conventional solid slab;
the parts file named the right drawings on the filler slab's part; the server read the plan alone, asked the two for the filler slab's part and
wrote it into their briefs as "the view this drawing shows". No upload could pass. The older way (a thing's part asked from every drawing that
names the thing, whatever the part's own list) is retired. A part that names no drawing is as before. Without a database."""
import pytest

from app import visuals_stage as VS
from app.errors import Problem
from step6_shape import build, load, parts_svg, upload
from test_design221_p1_pure import NEW
from test_fixset4_pure import alone
from test_rel2f_pure import other_view

BASE = '<symbol id="part-base" viewBox="0 0 200 100" data-element="E3"'   # the fixture's Base: one part, of no view; the plan names it on D3 and D4


def named(shots):
    """The film with the Base's part naming these drawings; D4 is a drawing of its own."""
    return other_view(alone(load(parts=False)), parts_svg().replace(BASE, BASE + f' data-shots="{shots}"'))


def test_a_drawing_the_things_part_does_not_name_is_not_asked_for_it():
    store = named('D3')   # as on VW-25: the plan names the thing on D4 too; its part names D3 alone
    brief = build(store, 'D4')['brief']
    assert 'part-base' not in brief and 'No part of' not in brief   # neither listed, nor "draw it yourself": the part's own list says D4 does not show it
    assert upload(store, 'D4', 'part-rod-grid', still=True)['sha256']   # was refused: "D4 shows Base but does not use its shared part: place part-base"


def test_the_drawing_the_part_names_is_asked_for_it_as_before():
    store = named('D4')
    assert 'part-base: Base' in build(store, 'D4')['brief']
    assert 'part-base' not in VS.motion_brief(store, NEW, [], 'D3')['brief']   # D3 shows the thing by the plan, and the part does not name it
    with pytest.raises(Problem, match='D4 shows Base but does not use its shared part: place part-base'):
        upload(store, 'D4', 'part-rod-grid', still=True)
    assert upload(store, 'D4', 'part-rod-grid', 'part-base', still=True)['sha256']


def test_the_three_lists_of_a_shots_parts():
    session = {'motion_parts_approved': {'parts': [
        {'id': 'part-a', 'element': 'E1', 'view': 'cutaway', 'shots': ['D2']},   # a thing's part, another drawing's
        {'id': 'part-b', 'element': 'E1', 'view': 'plan'},                         # the same thing in another view, names no drawing
        {'id': 'part-c', 'element': 'E2', 'view': '', 'shots': ['D2']},
        {'id': 'part-d', 'element': '', 'view': ''},                               # no thing, no drawing named: every drawing's
        {'id': 'part-e', 'element': 'E9', 'view': '', 'shots': ['D1']}]}}          # a thing D1 does not name, on a part that names D1
    d1 = {'id': 'D1', 'element_ids': ['E1', 'E2'], 'drawing_spec': {'view': 'cutaway'}}
    assert [p['id'] for p in VS.shot_parts(session, d1)] == ['part-b', 'part-d', 'part-e']
    assert VS.fit_parts(session, d1) == {'E1': []}   # E1 is left with a part of another view only: the brief's "draw it yourself" line, as release 2 F5; E2 has no part for D1: nothing is said
    assert VS.view_parts(session, d1) == {}
    d2 = {**d1, 'id': 'D2'}
    assert VS.fit_parts(session, d2) == {'E1': ['part-a'], 'E2': ['part-c']} and VS.view_parts(session, d2) == {'E1': ['part-a']}
    assert [p['id'] for p in VS.shot_parts(session, d2)] == ['part-a', 'part-b', 'part-c', 'part-d']
