"""design/216 (SK, 18 Nov 2026), the server's part: the words of the sets screen (A3-A13) sent on the lines and with the layout; the message
posted with the page's link (B1) and the sentence said before its pictures are fetched (B2); a set held by a rule that no longer applies (B3);
a place's request with the film's own things that stand in it, their references within the picture model's limits, things made before places
(B4); two people alike in plain words (B5); no "left out" left in the assistant's sentences and the older rounds' labels (B6). Without a database."""
import copy
import json
import re
from pathlib import Path

import pytest

from app import chat_flow as CF, page_flow as P, ref_sets as RS, visuals_stage as VS
import d211_fixture as F
from test_design211b_sets_pure import RUN, el, finder, ready   # noqa: F401 (`finder` is the fixture)
from test_design211c_kit_pure import Film

W = CF.WORDS
REPO = Path(__file__).resolve().parents[2]


# ---------- the words of the screen (A3-A13): on the line, the same for the chat ----------

def test_a_set_of_three_one_answer_for_the_whole_set(monkeypatch):
    film = Film(monkeypatch, '2')
    lines = film.lines()
    t, m = lines['set:T_LAY'], lines['set:MASON']
    made = [p for p in t['pics'] if not p.get('ref_only')]
    assert t['answer_head'] == 'Your answer for the whole set (pictures A, B and C)' and t['answer_note'] == 'One answer covers all 3 pictures. You do not answer them one by one.'
    assert t['strip_head'] == 'The set: 3 pictures, answered together'
    assert [b['label'] for b in t['buttons']] == ['Make all 3 again', 'Approve all 3', 'Minor corrections']
    assert [b['label'] for b in m['buttons']] == ['Approve all 3', 'Minor corrections', 'Make all 3 again']
    chat = next(i for i in film.items() if i['_key'] == 'set:MASON')
    assert [b['label'] for b in chat['buttons']][0] == 'Approve all 3' and 'Make all 3 again' in [b['label'] for b in chat['buttons']]   # one flow, two front ends
    assert [(p['name'], p['set_cap'], p['main_label']) for p in made] == [('Picture A', 'The set: picture A', 'Make A the main picture'), ('Picture B', 'The set: picture B', 'Make B the main picture'),
                                                                          ('Picture C', 'The set: picture C', 'Make C the main picture')]
    assert [p['faults'] for p in made] == [[], ['A tool lying still; no hand.'], []] and made[0]['check_head'] == "Claude's check of picture A:" and made[0]['check_none'] == 'no fault found.'
    assert made[1]['say'] == 'All 3 pictures approved as one set. Later pictures start from picture B.' and not any('main_label' in p for p in m['pics'])   # a person is always A
    assert t['sure'] == {'ask': "Claude's check found 1 fault in this set. Approve it all the same?", 'text': 'Picture B shows no hand at work. Every later picture of it would copy this.',
                         'go': 'Approve the set all the same', 'back': 'Go back'} and 'sure' not in m   # A6: only against "make again"
    assert t['rec']['head'] == 'Claude recommends: make it again' and m['rec']['head'] == 'Claude recommends: use this set'
    fix = next(b for b in t['buttons'] if b['act'] == 'fix')
    assert fix['all']['say'] == W['say_fix_all'] and m['own']['label'] == 'Use my own picture instead'
    assert ["Why Claude suggests this" not in [d[0] for d in t['details']]] and [d[0] for d in t['details']][0] == "What Claude's check found"   # A9


def test_a_picture_claude_could_not_check_is_never_said_to_have_no_fault(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: s['references']['s-mason-1-3']['look'].update(not_checked='The file could not be opened.', verdict=None, lines=None) or s['references']['s-mason-1-3']['look'].pop('lines'))
    made = [p for p in film.lines()['set:MASON']['pics'] if not p.get('ref_only')]
    assert made[2]['check_head'] == '' and made[2]['check_none'] == 'Claude could not check this picture.' and made[0]['check_none'] == 'no fault found.'


def test_a_make_again_with_no_fault_counted_and_a_rec_with_one_sentence():
    assert CF._first('One. Two three.') == 'One.' and CF.rec_of('Make it again', 'remake', 'One. Two.')['more'] == 'Two.' and CF._and(['A', 'B', 'C']) == 'A, B and C'
    assert W['sure_ask_none'] == 'Claude recommends making this set again. Approve it all the same?'


def test_the_screen_words_come_with_the_layout(monkeypatch):
    p = Film(monkeypatch, '2').page()
    s = p['layout']['words']['sets']
    assert s is CF.SETS_PAGE or s == CF.SETS_PAGE
    assert s['foot'] == '{n} of {m} answered.' and s['foot_wait'] == 'When all are answered, say done in the chat. Nothing is made before that.'   # A11
    assert s['end_note'] == 'Go back to the chat and say done. This is what will happen then:'   # A13
    rest = next(l for l in p['lines'] if l['key'] == 'sets:rest')
    assert rest['name'] == 'The other 2 sets' and [b['label'] for b in rest['buttons']] == ['Make the other 2', 'Make only some of them']   # A10, A12: one label everywhere
    assert rest['buttons'][0]['big'] == rest['buttons'][0]['label'] and 'Make them' not in json.dumps(p) and W['wait_head'] == 'Not made yet. It is made with the other sets when you choose to make them.'


# ---------- B1, B2: what the assistant says ----------

def line(key, state='open', **more):
    return {'key': key, 'state': state, 'title': key, **more}


def test_b1_the_message_with_the_link_names_what_needs_an_answer():
    lines = [line('sets:rest', covers=['a'] * 17), line('set:MASON', name='The mason'), line('set:DECK', name='The roof deck'), line('set:ROOM', name='Family room'), line('set:X', 'recorded', name='Y')]
    said = P.sets_say(lines)
    assert said == '3 things need your answer: the mason, the roof deck and the Family room. Then choose whether the other 17 sets are made. Then say done here.'
    assert not re.search(r'\bpictures?\b|\blines?\b', said)
    assert P.sets_say([line('set:MASON', name='The mason')]) == '1 thing needs your answer: the mason. Then say done here.'
    assert P.sets_say([line('sets:rest', covers=['a', 'b'])]) == 'Choose whether the other 2 sets are made. Then say done here.'        # only the other sets
    assert P.sets_say([line('set:M', 'recorded'), line('set:K', kept='Approve all 3', name='K')]) == 'Nothing needs your answer on this page now.'   # nothing to answer
    assert 'Say to the operator `say`, exactly as it is, then the link' in P.HOW and 'no count' in P.HOW and 'Open this page, answer each line' not in P.HOW


def test_b1_the_sets_page_carries_its_message_and_every_page_one(monkeypatch):
    p = Film(monkeypatch, '2').page()
    assert p['say'] == P.sets_say(p['lines']) and p['say'].startswith('3 things need your answer: ')
    assert P.CF.WORDS['say_page'] == 'Open this page, answer each line, then tell me you are done:'


def test_b2_the_sentence_before_the_pictures(monkeypatch):
    p = Film(monkeypatch, '2').page()
    n = len(p['pictures'])
    assert n and p['preparing'] == f"Preparing {n} pictures for the page, about {max(1, -(-n * P.PREPARE_SECONDS // 60))} minute{'' if max(1, -(-n * P.PREPARE_SECONDS // 60)) == 1 else 's'}."
    assert W['preparing'].format(pictures=CF._n(44, 'picture'), minutes=CF._n(3, 'minute')) == 'Preparing 44 pictures for the page, about 3 minutes.'
    assert -(-44 * P.PREPARE_SECONDS // 60) == 3   # VW-24: about two to three minutes (finding 16)


# ---------- B3: held by a rule that no longer applies ----------

def test_b3_a_set_held_by_a_retired_rule_says_the_plain_sentence_and_offers_make_it(monkeypatch):
    film = Film(monkeypatch, '2')
    old = "The prompt places something at 'middle' with no landmark and measured distance ('the woven mat in the middle of the floor;'): say the landmark and how far from it."
    film.change(lambda s: ([r.update(status='failed') for r in s['references'].values() if r.get('set') == 's-street-1'], s.update(page_refused={'set:STREET': 'STREET: its set was not made: ' + old})))
    film.fails['STREET'] = {'cause': 'other', 'model': None, 'text': VS.RULE_RETIRED}   # ref_sets.set_facts says so for a retired rule
    s = film.lines()['set:STREET']
    assert s['head'] == VS.RULE_RETIRED and 'why' not in s and [b['label'] for b in s['buttons']] == ['Make it', 'Go on without a reference'] and 'refused' not in s
    assert VS.rule_retired({'round': {'v': 2}}, old) and VS.rule_retired({'round': {'v': 2}}, "'as before' says nothing a picture can show") and not VS.rule_retired({'round': {'v': 2}}, 'Google refused the request.')
    assert not VS.rule_retired({'round': {}}, old)   # an older round keeps its refusal


# ---------- B4: a place's own things ----------

def street_plan():
    plan = F.plan()
    shots = plan['gaps'][0]['scenes'][0]['shots']
    shots[0]['element_ids'] = ['STREET', 'DOG', 'TROWEL', 'TILE', 'MASON', 'FAN']
    shots.append(F._shot('G1-S1-SH3', 'image', 'MS', ['STREET', 'TILE', 'BRICK']))
    return plan


def test_b4_a_places_things_most_shared_first_with_their_approved_references():
    plan, s = street_plan(), ready('making', street_plan())
    things = RS.place_things(plan, s, el('STREET', plan))
    assert [t['id'] for t, _ in things] == ['TILE', 'TROWEL', 'FAN', 'BRICK']   # objects and materials only (no person, no animal), most shared first, then the plan's order
    refs = dict((t['id'], r) for t, r in things)
    assert refs['TROWEL'] == 'f-trowel-side'                                     # its golden picture
    assert all(r is None or s['references'][r]['status'] == 'approved' for r in refs.values())


def test_b4_the_request_gives_the_references_as_input_pictures_and_the_rest_in_words(monkeypatch):
    plan, s = street_plan(), ready('making', street_plan())
    things = RS.place_things(plan, s, el('STREET', plan))
    with_ref = [t for t, r in things if r]
    req = RS.set_request(plan, RUN, s, el('STREET', plan), s['round']['elements']['STREET'])
    own = [i for i in req['inputs'] if i['role'] != 'thing']
    mine = [i for i in req['inputs'] if i['role'] == 'thing']
    assert [i['view'] for i in mine] == [t['name'] for t in with_ref] and len(req['inputs']) <= min(VS.GEMINI_MAX_INPUTS, VS.GEMINI_KIND_CAPS['object'])
    for k, i in enumerate(mine, len(own) + 1):
        assert f"Image {k} is the approved reference of {i['view']}, one of the film's own things in this place" in req['prompt']
    said = [t['name'] for t, r in things if not r]
    if said:
        assert "The film's own things in this place, from their descriptions: " in req['prompt'] and all(n in req['prompt'] for n in said)
    assert any(l['check'] == "the film's own things in it match their references" for l in req['lines'])   # the check list says the same


def test_b4_the_limit_is_kept_before_the_call(monkeypatch):
    plan, s = street_plan(), ready('making', street_plan())
    monkeypatch.setattr(VS, 'GEMINI_KIND_CAPS', {**VS.GEMINI_KIND_CAPS, 'object': 1})   # room for one picture only
    monkeypatch.setattr(RS, 'inputs_of', lambda session, element: ([], set()))
    req = RS.set_request(plan, RUN, s, el('STREET', plan), s['round']['elements']['STREET'])
    things = RS.place_things(plan, s, el('STREET', plan))
    first = next(t for t, r in things if r)
    assert [i['view'] for i in req['inputs']] == [first['name']]                 # the most shared with a reference
    rest = [t['name'] for t, r in things if t is not first]
    assert all(n in req['prompt'].split("from their descriptions: ")[1] for n in rest)   # the rest in words


def test_b4_a_thing_with_no_reference_or_no_reference_needed_is_in_words_and_the_place_says_it_waits():
    plan, s = street_plan(), ready('making', street_plan())
    s['round']['elements']['FAN'] = {**s['round']['elements'].get('FAN', {}), 'ignored': True}
    for r in list(s['references'].values()):
        if r.get('element_id') == 'TILE':
            r['status'] = 'candidate'
    s['drawings'] = {}
    assert RS.thing_ref(s, 'FAN') is None and RS.thing_ref(s, 'TILE') is None
    said = RS.place_waiting(plan, s, 'STREET')
    assert said == 'This place shows the Roof tile and the Brick, whose sets are not approved yet: answer those first, or it is made from words.'   # the fan needs no reference: not named
    s['round']['elements']['BRICK']['ignored'] = True
    assert RS.place_waiting(plan, s, 'STREET') == 'This place shows the Roof tile, whose set is not approved yet: answer that first, or it is made from words.'
    assert RS.place_waiting(plan, s, 'TROWEL') == ''


def test_b4_things_are_ordered_before_places(monkeypatch):
    plan = street_plan()
    got = []
    monkeypatch.setattr(VS, '_queue_sets', lambda conn, store, user, run, outputs, eids: (got.extend(eids) or [], {}))
    monkeypatch.setattr(VS, 'session_of', lambda store, run, outputs: {'round': {}})
    monkeypatch.setattr(VS, 'current_plan', lambda store, session: plan)
    RS._order(None, None, None, RUN, [], ['STREET', 'MASON', 'TILE', 'BRICK'])
    assert got == ['MASON', 'TILE', 'BRICK', 'STREET']


# ---------- B5, B6 ----------

def test_b5_two_people_alike_in_plain_words():
    plan = F.plan()
    plan['elements'] += [{'id': 'P3', 'name': 'The first neighbour', 'kind': 'person', 'description': 'A man of about 40.'}, {'id': 'P4', 'name': 'The second neighbour', 'kind': 'person', 'description': 'A man of about 40.'}]
    plan['elements'] = [e for e in plan['elements'] if e['kind'] != 'person' or e['id'] in ('P3', 'P4')]
    with pytest.raises(ValueError, match='These two people read alike, The first neighbour and The second neighbour: add what tells them apart.'):
        VS.distinct_people(plan)


def test_b6_no_left_out_in_the_sentences_and_labels_and_the_flag():
    said = RS.MERGE_NONE + RS.BACK_ASKED + json.dumps(CF.WORDS) + json.dumps(CF.SETS_PAGE)
    assert not re.search(r'\bleft out\b|Leave it out|Leave out', said)
    src = (REPO / 'server' / 'app' / 'chat_flow.py').read_text(encoding='utf-8')
    assert "_button('Leave it out'" not in src and "'Leave it out', 'ignore', 'none'" not in src
    vw = (REPO / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "'--every-picture'" in vw and "{'all': True}" in vw
