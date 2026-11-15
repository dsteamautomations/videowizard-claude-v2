"""design/202, the defects an independent review found in the first build (15 Nov 2026): stills lost or invented when a shot has no seconds; the
still warning stating a share that is not above its limit; a reason that is not text; a shot route outside the five ways; "asked" lost on a second
send; the gap's own why hidden; an older draft filled with "not given"; the card's header; the preparation text; the wording script's removal."""
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from app import chat_flow as CF, visuals_stage as VS
from test_design126_a_pure import USER, run, treat, vw12
from test_design202_pure import reasoned, treat_with_film

ROOT = Path(__file__).resolve().parents[1]
R = run('gemini')


def gap_only(doc, idx, **changes):
    doc['gaps'][idx].pop('shots', None)
    doc['gaps'][idx].update(changes)
    return doc


def rows_of(store, key):
    s = VS.session_of(store, R, [])
    line = next(i for i in CF._treatment_items({'session': s, 'store': store, 'user': USER, 'run': R, 'outputs': []})[0] if i['_key'] == key)
    return dict(line['_card']['r'])


# ---------- moving and still ----------

def test_a_shot_without_numeric_seconds_does_not_lose_the_other_shots_stills():
    doc = reasoned(vw12())
    del doc['gaps'][1]['shots'][0]['seconds']   # the video shot has no seconds; the still of 5.56 s still counts
    t = treat(doc)[0]['totals']
    assert t['still_seconds'] == 5.56 and t['unsplit_seconds'] == 4.0


def test_a_gap_of_several_ways_with_no_shots_is_counted_as_neither_still_nor_moving():
    doc = gap_only(reasoned(vw12()), 2, routes=['still', 'video'], seconds=30.0, fits_why='a', way_why='b')
    t = treat(doc)[0]['totals']
    assert t['still_seconds'] == 5.56 and t['unsplit_seconds'] == 30.0
    one = treat(gap_only(reasoned(vw12()), 2, routes=['still'], seconds=3.0, images=1, fits_why='a', way_why='b'))[0]['totals']
    assert one['still_seconds'] == 8.56 and 'unsplit_seconds' not in one


def test_the_still_warning_states_a_share_that_is_above_its_limit():
    doc = reasoned(vw12())
    doc['gaps'][1]['shots'][2]['seconds'], doc['gaps'][1]['seconds'] = 20.1, 4.0 + 23.92 + 20.1   # 10.05 % of 200 s
    w = [x for x in treat_with_film(doc, 5000)['warnings'] if x['kind'] == 'stills_many']
    assert len(w) == 1 and '10.1 %' in w[0]['message'] and 'above 10 %' in w[0]['message']
    doc['gaps'][1]['shots'][2]['seconds'], doc['gaps'][1]['seconds'] = 20.02, 4.0 + 23.92 + 20.02   # 10.01 %: over the limit, however it rounds
    w = [x for x in treat_with_film(doc, 5000)['warnings'] if x['kind'] == 'stills_many']
    assert len(w) == 1 and '10.1 %' in w[0]['message']   # shown rounded up, never as the limit itself


# ---------- the two reasons ----------

@pytest.mark.parametrize('bad', [['a', 'b'], {'x': 1}, 5, True, ' ' * 301])
def test_a_reason_that_is_not_text_or_is_only_spaces_counts_as_not_given(bad):
    doc = reasoned(vw12())
    doc['gaps'][0]['shots'][0]['fits_why'] = bad
    out, store = treat(doc)
    assert out['reasons_missing'] == ['gap BEAT_01-B1, shot BEAT_01-B1-1: say fits_why (why the picture fits the words).']
    assert rows_of(store, 'BEAT_01-B1')['Shot 1 · why it fits the words'] == 'not given'


def test_a_shot_route_outside_the_five_ways_is_refused():
    doc = reasoned(vw12())
    doc['gaps'][0]['shots'][0]['route'] = 'Video'
    with pytest.raises(ValueError) as e:
        treat(doc)
    assert 'BEAT_01-B1-1' in str(e.value) and 'footage, still' in str(e.value)


# ---------- a line changed as the operator asked ----------

def sent_back_and_rewritten(key='BEAT_02-B2'):
    first, store = treat(reasoned(vw12()))
    VS.treatment(store, USER, R, [], None, 'make it move', send_back=[key], notes='show a person')
    second = reasoned(vw12())
    second['gaps'][2]['picture'] = 'a mason points at the cavity'
    VS.treatment(store, USER, R, [], second, '')
    return store, second


def test_asked_survives_a_second_send_and_the_changes_are_against_what_the_operator_saw():
    store, second = sent_back_and_rewritten()
    third = deepcopy(second)
    third['gaps'][2]['shots'][0]['way_why'] = 'A real clip shows it.'   # the assistant sends again before the operator has seen the line
    VS.treatment(store, USER, R, [], third, '')
    line = VS.session_of(store, R, [])['treatment_draft']['lines']['BEAT_02-B2']
    assert line['state'] == 'to_accept' and line['asked'] is True
    assert any('picture' in c and 'a mason points at the cavity' in c for c in line['changes']) and any('way_why' in c for c in line['changes'])


def test_asked_is_cleared_once_the_operator_accepts():
    store, _ = sent_back_and_rewritten()
    VS.treatment(store, USER, R, [], None, 'yes', accept=['BEAT_02-B2'])
    line = VS.session_of(store, R, [])['treatment_draft']['lines']['BEAT_02-B2']
    assert line['state'] == 'accepted' and 'asked' not in line and 'was' not in line


def test_the_direction_sent_back_and_sent_twice_shows_what_the_operator_saw_before():
    first, store = treat(reasoned(vw12()))
    VS.treatment(store, USER, R, [], None, 'x', send_back=['direction'], notes='another view')
    VS.treatment(store, USER, R, [], {**reasoned(vw12()), 'direction': 'told from the family'}, '')
    VS.treatment(store, USER, R, [], {**reasoned(vw12()), 'direction': 'told from the family who will live there'}, '')
    line = VS.session_of(store, R, [])['treatment_draft']['lines']['direction']
    assert line['asked'] is True and line['changes'] == ['Before: "a documentary explainer told from the site"']


# ---------- how the operator is asked ----------

def test_the_gaps_own_why_is_still_shown_and_an_older_draft_is_not_filled_with_not_given():
    doc = vw12()
    doc['gaps'][1]['why'] = 'the graphics run is long because the saving needs three steps'
    out, store = treat(doc)
    new = rows_of(store, 'BEAT_05-B1')
    assert new['Why'].startswith('the graphics run is long') and new['Shot 1 · why it fits the words'] == 'not given'
    s = VS.session_of(store, R, [])
    s['treatment_draft'].pop('reasons_missing')   # a draft saved before design/202
    VS.save_session(store, R, s)
    old = rows_of(store, 'BEAT_05-B1')
    assert old['Why'].startswith('the graphics run is long') and 'Shot 1 · why it fits the words' not in old and old['Shot 1'] == 'AI video, 4 s'


def test_a_shot_route_that_is_not_text_does_not_break_the_question():
    rows = CF._shot_rows({'shots': [{'route': 5, 'seconds': 3}, {'route': ['video'], 'seconds': '4'}]}, True)
    assert rows[0] == ('Shot 1', '3 s') and rows[4] == ('Shot 2', '')


def test_the_card_names_a_line_changed_as_asked_in_its_header_too():
    html = (ROOT / 'app' / 'chat_card.html').read_text(encoding='utf-8')
    assert "e.a?'Changed as you asked':e.c?'Changed since you last saw it':''" in html


# ---------- the instruction text and its script ----------

def test_the_preparation_no_longer_tells_the_assistant_to_read_the_scripts_notes_first():
    prep = next(p['text'] for s in json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals'
                for p in s['parts'] if p['name'] == 'preparation')
    assert 'Read prompt.md and gaps.json first' in prep and 'and intended-visuals.json first' not in prep


def test_the_wording_script_stops_when_a_sentence_it_removes_was_reworded():
    code = ("import sys; sys.path.insert(0, 'scripts'); import d202_wording_v3 as d; "
            "d.replace('Treat the visual notes (reworded) as a requirement. ', d.PAIRS['treatment'][1:2], 'treatment')")
    r = subprocess.run([sys.executable, '-c', code], cwd=ROOT.parent, capture_output=True, text=True)
    assert r.returncode != 0 and 'not applied' in (r.stdout + r.stderr)
