"""Release 1 of 27 Nov 2026, phase 2, part B (SK approved; the place's set: "Without"): signs of use only where the shot's words ask for it.

Seen on VW-25: the same bucket, shovel, wire and pan in every picture of the site, and the pictures the operator cleaned failed their check.
The server added two of the place's signs to every still's prompt and two must lines to its check ("both visible", "nothing showroom-clean
or empty"), on a correction too. Now the server adds none: a shot's own words are its prompt. A place's reference set is made without
them. A plan is no longer refused for a place without signs. Each test failed first. Without a database."""
import inspect
import json
from pathlib import Path

from app import ref_sets as RS, visuals_stage as VS
from test_design111_f18_pure import SIGNS, YARD
from test_design124_b_pure import base, check as plan_check
from test_design110_f456_pure import doc_with, rich
from test_design211b_sets_pure import request
from test_visuals_pure import shot as pshot


def yard_plan(**more):
    d = doc_with(rich(), pshot('VS2', 500, 1000, 'video'))
    d['elements'].append({**YARD, **more})
    d['gaps'][0]['scenes'][0]['shots'][0]['element_ids'].append('YARD')
    return d


def test_a_plan_is_accepted_for_a_place_with_no_signs_and_one_with_signs_still_loads():
    for signs in (None, [{'what': 'a bucket', 'landmark_id': 'L1'}], [{'what': 'a bucket', 'landmark_id': 'L1'}, {'what': 'a broom', 'landmark_id': 'L1'}]):
        d = base()
        d['elements'].append({'id': 'FLAT', 'name': 'The new flat', 'kind': 'place', 'identity': 'exact', 'requirements': 'the handed-over flat', **({'signs_of_use': signs} if signs else {})})
        d['gaps'][0]['scenes'][0]['shots'][1]['element_ids'].append('FLAT')
        plan_check(d)                                              # was: "give signs_of_use, two or more"


def test_the_server_adds_no_signs_and_no_occupied_line_to_a_picture():
    assert not hasattr(VS, 'signs_lines') and not hasattr(VS, 'OCCUPIED')
    src = inspect.getsource(VS.generate_image)
    assert 'signs of use' not in src.lower() and 'both visible' not in src
    d = yard_plan(signs_of_use=SIGNS)
    assert VS.place_line(d, 'YARD', d['gaps'][0]['scenes'][0]['shots'][0]) is None   # no must line "nothing showroom-clean or empty": a cleaned picture passes


def test_a_place_staged_clean_keeps_its_own_line():
    d = yard_plan(staged_clean='shown at the handover')
    assert VS.place_line(d, 'YARD', d['gaps'][0]['scenes'][0]['shots'][0])['pass_when'].startswith('clean and unused, as planned')


def test_a_places_reference_set_is_made_without_signs():
    r = request('STREET')
    assert r['parts']['signs'] == [] and 'Signs of use' not in r['prompt']


def test_the_instruction_no_longer_asks_for_two_signs():
    st = next(s for s in json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
    text = ' '.join([st['prompt'], *(p['text'] for p in st['parts'])])
    assert 'signs_of_use' not in text and 'two signs of use' not in text
    assert 'write them in the shot that should show them' in text
