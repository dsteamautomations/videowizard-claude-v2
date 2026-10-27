"""design/111 F14 and F15. F14: every tool in a holding or props list and every technique verb in the beats is an element (kind object, or the new kind
technique), so it joins the single reference round; a plan missing one is refused with the ids to add. F15: when a shot's claim or descriptor is about
size, amount or scale, the subject element carries a size value and the shot names a thing in frame to compare with; the server writes the line and
the "real size" check becomes a must on that picture."""
import copy
from fractions import Fraction

import pytest

from app import visual_contract as VC, visuals_stage as VS
from test_design110_f456_pure import doc_with, rich
from test_visuals_pure import GAPS, shot as pshot


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


# ---------- F14 ----------

def test_a_technique_in_the_beats_must_be_an_element_and_a_technique_element_joins_the_round():
    sh = rich()
    sh['subjects'][0]['beats'][0].update(action='points the joints of the course', done='pointed the joints of the course')
    d = doc_with(sh, pshot('VS2', 500, 1000, 'video'))
    with pytest.raises(ValueError, match="technique 'pointing' .* is not an element"):
        check(d)
    d['elements'].append({'id': 'POINTING', 'name': 'Pointing', 'kind': 'technique', 'identity': 'representative', 'requirements': 'the joint struck flush with a pointing trowel'})
    out, _ = check(d)
    assert out['elements'][-1]['kind'] == 'technique'
    assert VS.technique_words('points the joints, then plasters the face') == ['pointing', 'plastering']
    assert VS.technique_words('lays one brick') == []


def test_the_derived_elements_are_listed_for_the_planner():
    sh = rich()
    sh['subjects'][0]['beats'][0].update(action='planes the edge of the plank', done='planed the edge of the plank')
    d = doc_with(sh)
    assert VS.needed_elements(d) == [{'id': 'PLANING', 'kind': 'technique', 'from': 'VS1 B1: planes the edge of the plank'}]
    d['elements'].append({'id': 'PLANING', 'name': 'Planing', 'kind': 'technique', 'identity': 'representative', 'requirements': 'a hand plane along the grain'})
    assert VS.needed_elements(d) == []


# ---------- F15 ----------

def test_a_size_claim_needs_a_number_and_a_comparison_and_the_server_writes_the_line():
    sh = rich()
    sh['claims'] = ['the carrier is small']
    d = doc_with(sh, pshot('VS2', 500, 1000, 'video'))
    with pytest.raises(ValueError, match='is about size .* give the subject a size value and name compare_to'):
        check(d)
    d['elements'][0]['size'] = [{'part': 'deck', 'measure': 'length', 'value': 2, 'unit': 'm', 'source': 'the maker', 'status': 'confirmed'}]
    with pytest.raises(ValueError, match='compare_to'):
        check(d)
    d['gaps'][0]['scenes'][0]['shots'][0]['compare_to'] = 'NOPE'
    with pytest.raises(ValueError, match='compare_to names an element in frame'):
        check(d)
    d['gaps'][0]['scenes'][0]['shots'][0]['compare_to'] = 'BRICK'
    check(d)
    scene, sh = d['gaps'][0]['scenes'][0], d['gaps'][0]['scenes'][0]['shots'][0]
    assert VS.size_line(d, sh) == 'Size is the point: Mason, deck length 2 m, against the Red brick beside it; the sizes read true against each other and the place.'
    lines = VS.picture_rule_lines(d, scene, sh, 'start')
    assert any(l['check'] == 'size is the point' and l['weight'] == 'must' and 'deck length 2 m' in l['pass_when'] for l in lines)
    assert 'Size is the point' in VS.composed_block(d, scene, sh, 'start')
    plain = doc_with(rich())
    assert VS.size_line(plain, plain['gaps'][0]['scenes'][0]['shots'][0]) == ''   # no size word: no line
