"""design/202 (SK, 15 Nov 2026): the treatment step. Each shot's two reasons (why the picture fits the words, why it is made this way); the
moving and still seconds and the still warning; the Direction asked by its name; a line changed as the operator asked says so; the script's
visual notes are no longer handed to the planner; the instruction text."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app import chat_flow as CF, visuals_stage as VS
from app.config import settings
from test_design126_a_pure import USER, VW12_GAPS, entry, run, session, store_with, treat, vw12

ROOT = Path(__file__).resolve().parents[1]
TREATMENT = next(p['text'] for s in json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals'
                 for p in s['parts'] if p['name'] == 'treatment')


def reasoned(doc):
    for e in doc['gaps']:
        for sh in e['shots']:
            sh.update(fits_why='It shows what the sentence says.', way_why='No clip shows it; one action, close.')
    return doc


# ---------- the two reasons ----------

def test_a_shot_without_its_reasons_is_named_and_the_draft_is_still_taken():
    out, _ = treat(vw12())
    missing = out['reasons_missing']
    assert out['draft'] is True and 'BEAT_01-B1-1' in missing[0] and 'fits_why' in missing[0] and 'way_why' in missing[0]
    assert len(missing) == sum(len(e['shots']) for e in vw12()['gaps'])


def test_a_shot_with_both_reasons_is_not_named():
    out, _ = treat(reasoned(vw12()))
    assert out['reasons_missing'] == []


def test_one_reason_alone_names_the_other():
    doc = reasoned(vw12())
    del doc['gaps'][0]['shots'][0]['way_why']
    out, _ = treat(doc)
    assert out['reasons_missing'] == ['gap BEAT_01-B1, shot BEAT_01-B1-1: say way_why (why it is made this way).']


def test_a_gap_with_one_way_and_no_shots_carries_the_reasons_on_its_line():
    doc = reasoned(vw12())
    e = doc['gaps'][2]
    e.pop('shots')
    out, _ = treat(doc)
    assert out['reasons_missing'] == ['gap BEAT_02-B2: say fits_why (why the picture fits the words) and way_why (why it is made this way).']
    e.update(fits_why='A comparison.', way_why='It must be read exactly.')
    assert treat(doc)[0]['reasons_missing'] == []


def test_a_reason_longer_than_300_characters_is_refused():
    doc = reasoned(vw12())
    doc['gaps'][0]['shots'][0]['fits_why'] = 'x' * 301
    with pytest.raises(ValueError) as e:   # the API turns it into a refusal in plain words, as every other field out of form
        treat(doc)
    assert 'BEAT_01-B1-1' in str(e.value) and '300' in str(e.value)


def test_a_changed_reason_changes_the_lines_digest():
    a, b = reasoned(vw12()), reasoned(vw12())
    b['gaps'][0]['shots'][0]['way_why'] = 'A real clip shows it.'
    assert VS.digest(a['gaps'][0]) != VS.digest(b['gaps'][0])


# ---------- moving and still ----------

def film(frames):
    return [{'stage': 'first_cut', 'unit': None, 'summary': {'duration_frames': frames}}]


def treat_with_film(doc, frames):
    store = store_with(session(source={'from': 'first_cut', 'fps': '25', 'resolution': '1920x1080', 'plan_digest': 'pd', 'gaps': VW12_GAPS}))
    return VS.treatment(store, USER, run('gemini'), film(frames), deepcopy(doc), '')


def stills_doc(still_s):
    doc = reasoned(vw12())
    doc['gaps'][2] = {**entry('BEAT_02-B2', [('still', 4.0)] * int(still_s // 4), images=int(still_s // 4))}
    return reasoned(doc)


def test_the_totals_say_how_much_moves_and_how_much_is_still():
    out = treat_with_film(reasoned(vw12()), 5000)   # a film of 200 s; one still of 5.56 s
    t = out['totals']
    assert t['still_seconds'] == 5.56 and t['still_share'] == round(5.56 / 200, 3)
    assert t['moving_seconds'] == round(sum(s for e in vw12()['gaps'] for _, s in [(x['route'], x['seconds']) for x in e['shots']]) - 5.56, 2)


def test_stills_above_the_limit_warn_once_and_at_the_limit_do_not():
    limit = settings().VISUALS_STILL_SHARE
    over = treat_with_film(stills_doc(24.0), 5000)    # 24 s + 5.56 s of 200 s = 14.8 %
    w = [x for x in over['warnings'] if x['kind'] == 'stills_many']
    assert limit == 0.10 and len(w) == 1 and '14.8 %' in w[0]['message'] and 'above 10 %' in w[0]['message']
    at = reasoned(vw12())
    at['gaps'][1]['shots'][2]['seconds'], at['gaps'][1]['seconds'] = 20.0, 4.0 + 23.92 + 20.0   # 20 s of 200 s: exactly the limit
    assert not [x for x in treat_with_film(at, 5000)['warnings'] if x['kind'] == 'stills_many']


def test_without_a_film_length_the_share_is_left_out():
    out, _ = treat(reasoned(vw12()))
    assert 'still_share' not in out['totals'] and out['totals']['still_seconds'] == 5.56


# ---------- a line changed as the operator asked ----------

def test_a_line_sent_back_and_rewritten_comes_back_marked_as_asked_with_what_changed():
    first, store = treat(reasoned(vw12()))
    VS.treatment(store, USER, run('gemini'), [], None, 'make it move', send_back=['BEAT_02-B2'], notes='show a person')
    doc = reasoned(vw12())
    doc['gaps'][2]['picture'] = 'a mason points at the cavity'
    out = VS.treatment(store, USER, run('gemini'), [], doc, '')
    line = VS.session_of(store, run('gemini'), [])['treatment_draft']['lines']['BEAT_02-B2']
    assert out['lines']['BEAT_02-B2'] == 'to_accept' and line['asked'] is True and line['changed'] is True
    assert any('picture' in c and 'a mason points at the cavity' in c for c in line['changes'])


def test_a_line_sent_back_and_sent_again_unchanged_stays_sent_back():
    first, store = treat(reasoned(vw12()))
    VS.treatment(store, USER, run('gemini'), [], None, 'make it move', send_back=['BEAT_02-B2'], notes='show a person')
    out = VS.treatment(store, USER, run('gemini'), [], reasoned(vw12()), '')
    assert out['lines']['BEAT_02-B2'] == 'sent_back'


# ---------- how the operator is asked ----------

def items_of(doc):
    out, store = treat(doc)
    s = VS.session_of(store, run('gemini'), [])
    return CF._treatment_items({'session': s, 'store': store, 'user': USER, 'run': run('gemini'), 'outputs': []})[0]


def test_the_direction_is_asked_by_its_name():
    first = items_of(reasoned(vw12()))[0]
    assert CF._split(first['question']) == ('The direction of the film', 'Do you accept the direction of the film?')
    assert 'what the viewer should understand by the end' in first['text'] and 'a documentary explainer told from the site' in first['text']


def test_a_gap_line_shows_each_shots_picture_way_and_two_reasons():
    doc = reasoned(vw12())
    doc['gaps'][1]['shots'][0]['picture'] = 'a mason lays a brick'
    line = next(i for i in items_of(doc) if i['_key'] == 'BEAT_05-B1')
    rows = dict(line['_card']['r'])
    assert rows['Shot 1'] == 'AI video, 4 s' and rows['Shot 1 · the viewer sees'] == 'a mason lays a brick'
    assert rows['Shot 1 · why it fits the words'] == 'It shows what the sentence says.' and rows['Shot 1 · why this way'].startswith('No clip shows it')
    assert 'Shot 3 · why this way' in rows and 'Do you accept this line?' in line['question']


def test_a_missing_reason_is_shown_as_not_given():
    line = next(i for i in items_of(vw12()) if i['_key'] == 'BEAT_05-B1')
    assert dict(line['_card']['r'])['Shot 1 · why it fits the words'] == 'not given'


def test_a_line_changed_as_asked_says_so():
    assert CF._changed_text(['picture: "p" → "q"'], asked=True).startswith('**Changed as you asked:**')
    assert CF._changed_text(['picture: "p" → "q"']).startswith('**What changed:**')


# ---------- the script's visual notes; the instruction text ----------

def test_the_instructions_use_the_narration_alone():
    assert 'intended visuals' not in TREATMENT and "the script's visual notes are not used" in TREATMENT
    assert 'the mason laying bricks' not in TREATMENT


def test_the_instructions_put_action_first_and_ask_for_the_two_reasons():
    for words in ('who is doing what', 'real footage that shows it; else AI video; else a still', '`fits_why`', '`way_why`', 'not from a noun in it',
                  'a symbol only when it reads at a glance', 'three words or fewer'):
        assert words in TREATMENT, words
