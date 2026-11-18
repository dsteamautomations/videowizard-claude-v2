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


@pytest.fixture(autouse=True)
def _v2_round(monkeypatch, _older_round_tests):   # conftest: a module not named test_design211* posts an older round; these post the round of today
    monkeypatch.setattr(VS, 'ROUND_V', 2)
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
    assert said == '3 things need your answer:\n- The mason\n- The roof deck\n- Family room\nThen choose whether the other 17 sets are made. Then say done here.'   # the critic's point 3
    assert not re.search(r'\bpictures?\b|\blines?\b', said)
    assert P.sets_say([line('set:MASON', name='The mason')]) == '1 thing needs your answer:\n- The mason\nThen say done here.'
    assert P.sets_say([line('sets:rest', covers=['a', 'b'])]) == 'Choose whether the other 2 sets are made. Then say done here.'        # only the other sets
    assert P.sets_say([line('set:M', 'recorded'), line('set:K', kept='Approve all 3', name='K')]) == 'Nothing needs your answer on this page now.'   # nothing to answer
    assert 'Say to the operator `say`, exactly as it is, then the link' in P.HOW and 'no count' in P.HOW and 'Open this page, answer each line' not in P.HOW


def test_b1_the_sets_page_carries_its_message_and_every_page_one(monkeypatch):
    p = Film(monkeypatch, '2').page()
    assert p['say'] == P.sets_say(p['lines']) and p['say'].startswith('3 things need your answer:\n- ')
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

LIST, REASON = ['TILE', 'TROWEL', 'FAN', 'BRICK'], 'The roof tiles, the trowel left on the wall, the fan and the bricks of the street.'


def listed(s, ids=None, reason=REASON):
    """design/216b: Claude's list of the street's things on the round's row."""
    s['round']['elements']['STREET']['things'] = {'ids': list(LIST if ids is None else ids), 'reason': reason, 'at': F.NOW}
    return s


def street_plan():
    plan = F.plan()
    shots = plan['gaps'][0]['scenes'][0]['shots']
    shots[0]['element_ids'] = ['STREET', 'DOG', 'TROWEL', 'TILE', 'MASON', 'FAN']
    shots.append(F._shot('G1-S1-SH3', 'image', 'MS', ['STREET', 'TILE', 'BRICK']))
    return plan


def test_b4_a_places_things_most_shared_first_with_their_approved_references():
    plan, s = street_plan(), listed(ready('making', street_plan()))
    things = RS.place_things(plan, s, el('STREET', plan))
    assert [t['id'] for t, _ in things] == LIST   # design/216b: Claude's list, in Claude's order (before: the things its shots share, most shared first)
    refs = dict((t['id'], r) for t, r in things)
    assert refs['TROWEL'] == 'f-trowel-side'                                     # its golden picture
    assert all(r is None or s['references'][r]['status'] == 'approved' for r in refs.values())


def test_b4_the_request_gives_the_references_as_input_pictures_and_the_rest_in_words(monkeypatch):
    plan, s = street_plan(), listed(ready('making', street_plan()))
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
    plan, s = street_plan(), listed(ready('making', street_plan()))
    monkeypatch.setattr(VS, 'GEMINI_KIND_CAPS', {**VS.GEMINI_KIND_CAPS, 'object': 1})   # room for one picture only
    monkeypatch.setattr(RS, 'inputs_of', lambda session, element: ([], set()))
    req = RS.set_request(plan, RUN, s, el('STREET', plan), s['round']['elements']['STREET'])
    things = RS.place_things(plan, s, el('STREET', plan))
    first = next(t for t, r in things if r)
    assert [i['view'] for i in req['inputs']] == [first['name']]                 # the most shared with a reference
    rest = [t['name'] for t, r in things if t is not first]
    assert all(n in req['prompt'].split("from their descriptions: ")[1] for n in rest)   # the rest in words


def test_b4_a_thing_with_no_reference_or_no_reference_needed_is_in_words_and_the_place_says_it_waits():
    plan, s = street_plan(), listed(ready('making', street_plan()))
    s['round']['elements']['FAN'] = {**s['round']['elements'].get('FAN', {}), 'ignored': True}
    for r in list(s['references'].values()):
        if r.get('element_id') == 'TILE':
            r['status'] = 'candidate'
    s['drawings'] = {}
    assert RS.thing_ref(s, 'FAN') is None and RS.thing_ref(s, 'TILE') is None
    said = RS.place_waiting(plan, s, 'STREET')
    assert said == 'It will be made again after the sets of Roof tile and Brick are approved, so that it shows the real things.'   # the fan needs no reference: not named
    s['round']['elements']['BRICK']['ignored'] = True
    assert RS.place_waiting(plan, s, 'STREET') == 'It will be made again after the set of Roof tile is approved, so that it shows the real Roof tile.'
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


# ---------- the critic's points 1 and 2: a place waits for its things' sets ----------

def held_film(fail=()):
    """The fixture's round on a plan where the street shows the roof tile and the brick (both made in the round), the trowel (taken from its
    footage at step 1) and the fan (no reference needed)."""
    from test_design211b_round_pure import back, done, film, look, post, rows
    store, conn = film(plan=street_plan())
    post(store, conn, rows(STREET={'things': LIST, 'things_reason': REASON}))   # Claude's list, with the street's proposal
    done(store, conn)
    back(store, fail=fail)
    look(store)
    return store, conn


def test_point1_a_place_is_held_until_its_things_sets_are_approved_and_then_made_by_itself():
    from test_design211b_round_pure import back, jobs, judge, look, yes
    from test_design211b_older_pure import saved
    store, conn = held_film()
    rd = saved(store)['round']
    assert rd['elements']['STREET'].get('held') and set(rd['elements']['STREET']['held']) <= {'TILE', 'BRICK'} and 'STREET' not in jobs(conn)   # not ordered
    assert 'TROWEL' not in rd['elements']['STREET']['held'] and 'FAN' not in rd['elements']['STREET']['held']                      # a footage reference, no reference needed: no hold
    s = saved(store)
    assert RS.state(s, s['round']) != 'complete'                                                                                   # a held place is not judged yet
    for _ in range(3):   # judge what is back, make the others, until the things are approved
        s = saved(store)
        if s['round'].get('rest') and RS.state(s, s['round']) == 2:
            VS.guarded(lambda: RS.round_rest(conn, store, F.USER if hasattr(F, 'USER') else {'id': 'u1'}, RUN, [], 'make the others'))
            back(store)
            look(store)
        s = saved(store)
        due = {e: yes(store, e) for e, r in s['round']['elements'].items() if r.get('set') and VS._set_rows(s, e, r['set'], ('candidate',)) and e != 'STREET'}
        if due:
            judge(store, conn, due)
    assert 'STREET' in jobs(conn) and not saved(store)['round']['elements']['STREET'].get('held')                                   # ordered in the same call as the last approval
    street = jobs(conn)['STREET']
    assert any(p['id'] == saved(store)['golden'].get('TILE') for p in street['parents'])                                            # with the tile's approved reference


def test_point1_a_thing_set_aside_releases_the_place_with_that_thing_in_words():
    from test_design211b_older_pure import saved
    from test_design211b_round_pure import jobs, judge, yes
    store, conn = held_film(fail=('BRICK',))   # the brick's set failed: the operator goes on without a reference for it
    rd = saved(store)['round']
    never = ['BRICK']
    made = [e for e in rd['elements']['STREET']['held'] if e not in never]
    assert 'BRICK' in rd['elements']['STREET']['held']   # the tile has an approved drawing: it holds nothing
    if made:
        judge(store, conn, {e: yes(store, e) for e in made})
    assert 'STREET' not in jobs(conn)                                                       # still held: a thing waits
    for eid in never:   # the operator goes on without a reference for it
        VS.set_aside(store, {'id': 'u1'}, RUN, [], eid, 'Go on without a reference')
    assert RS.release(conn, store, {'id': 'u1'}, RUN, []) == ['STREET']
    names = [next(e['name'] for e in street_plan()['elements'] if e['id'] == x) for x in never]
    assert all(n in jobs(conn)['STREET']['prompt'].split('from their descriptions: ')[1] for n in names)   # made with that thing in words


def test_point1_make_it_on_a_held_place_answers_that_it_waits(monkeypatch):
    plan = street_plan()
    s = listed(ready('2', plan))
    words = RS.place_waiting(plan, s, 'STREET', again=False)
    assert words.startswith('It will be made after the sets of ') and words.endswith('approved, so that it shows the real things.') or words.startswith('It will be made after the set of ')


def test_point2_the_line_says_when_it_is_made_again_and_never_answer_that_first():
    plan, s = street_plan(), listed(ready('making', street_plan()))
    s['round']['elements']['BRICK']['ignored'] = True
    for r in s['references'].values():
        if r.get('element_id') == 'TILE':
            r['status'] = 'candidate'
    s['drawings'] = {}
    assert RS.place_waiting(plan, s, 'STREET') == 'It will be made again after the set of Roof tile is approved, so that it shows the real Roof tile.'
    assert RS.place_waiting(plan, s, 'STREET', again=False) == 'It will be made after the set of Roof tile is approved, so that it shows the real Roof tile.'
    assert 'answer that first' not in json.dumps(W) and W['held'].format(names='Roof tile') == 'Waits for Roof tile: it is made when their sets are approved.'


def test_point2_a_rewrite_of_a_held_place_is_stored_and_not_made():
    from test_design211b_older_pure import saved
    store, conn = held_film()
    s = saved(store)
    s['round']['elements']['STREET'].pop('held')
    s['round']['elements']['STREET']['rewrite_due'] = {'words': 'The tiles in pairs.', 'set': None, 'at': 'now'}
    from test_design211b_round_pure import jobs, put
    put(store, s)
    VS.guarded(lambda: RS.round_rewrite(conn, store, {'id': 'u1'}, RUN, [], [{'element_id': 'STREET', 'prompt': 'The roof tiles laid in pairs in each bay.'}]))
    row = saved(store)['round']['elements']['STREET']
    assert row['prompt'] == 'The roof tiles laid in pairs in each bay.' and row.get('held') and 'STREET' not in jobs(conn)   # the paid make waits for the things


def test_point1_the_other_sets_say_how_many_now_and_what_waits(monkeypatch):
    from test_design213_layout_pure import vw24
    film, things = vw24(monkeypatch)
    monkeypatch.setattr(RS, 'pending_things', lambda plan, session, eid: [{'id': 'TILE', 'name': 'Thing Tile'}] if eid in ('SITE_BELOW', 'LANE') else [])
    rest = next(l for l in film.page()['lines'] if l['key'] == 'sets:rest')
    assert rest['buttons'][0]['say'] == '15 sets are made now. Thing Site_Below and Thing Lane wait for Thing Tile: made when their sets are approved.'


# ---------- the critic's point 3: one name per line, the plan's names as they are ----------

def test_point3_the_message_lists_one_name_per_line():
    lines = [line('sets:rest', covers=['a'] * 17), line('set:DECK', name='The representative filler slab roof, from above'), line('set:R', name='Revathi')]
    assert P.sets_say(lines) == '2 things need your answer:\n- The representative filler slab roof, from above\n- Revathi\nThen choose whether the other 17 sets are made. Then say done here.'
    assert not hasattr(CF, 'the')


# ---------- design/216b: Claude names a place's things; the server enforces the list ----------

def no_list_film():
    """The fixture's round, the street's proposal sent with no list of its things."""
    from test_design211b_round_pure import done, film, post, rows
    store, conn = film(plan=street_plan())
    post(store, conn, [{k: v for k, v in r.items() if k not in ('things', 'things_reason')} for r in rows()])
    done(store, conn)
    return store, conn


def test_216b_a_place_with_no_list_is_not_ordered_and_claude_is_asked():
    from test_design211b_older_pure import saved
    from test_design211b_round_pure import jobs
    store, conn = no_list_film()
    row = saved(store)['round']['elements']['STREET']
    assert row.get('things_due') is True and 'STREET' not in jobs(conn) and 'held' not in row       # never ordered on a guess
    said = RS.things_due_words(saved(store))
    assert said.startswith("Name the film's own things shown in 1 place(s) before it is made: STREET.") and '`vw visuals round --things`' in said
    assert RS.then_of(saved(store)) == said
    asked = RS.things_asked(store, RUN, [])
    street = asked['places'][0]
    assert street['element_id'] == 'STREET' and street['description'] and street['shots'] and street['things'] is None
    assert {c['id'] for c in asked['candidates']} == {e['id'] for e in street_plan()['elements'] if e['kind'] in ('object', 'material')}   # what Claude reads
    out = VS.guarded(lambda: RS.round_things(conn, store, {'id': 'u1'}, RUN, [], [{'element_id': 'STREET', 'things': [], 'reason': 'Nothing of the film stays in the street.'}]))
    assert out['recorded'] == ['STREET'] and out['queued'] == ['STREET'] and 'STREET' in jobs(conn)                    # an empty list: made at once, nothing named
    assert "The film's own things in this place" not in jobs(conn)['STREET']['prompt'] and not saved(store)['round']['elements']['STREET'].get('things_due')


@pytest.mark.parametrize('things,word', [(['MASON'], 'MASON'), (['NOPE'], 'NOPE'), (['STREET'], 'STREET'), (['T_LAY'], 'T_LAY'), (['DOG'], 'DOG')])
def test_216b_a_person_an_unknown_id_or_not_a_thing_is_refused_by_name(things, word):
    from test_design211b_older_pure import saved
    store, conn = no_list_film()
    with pytest.raises(VS.Problem) as e:
        VS.guarded(lambda: RS.round_things(conn, store, {'id': 'u1'}, RUN, [], [{'element_id': 'STREET', 'things': things, 'reason': 'Why.'}]))
    assert e.value.message == RS.THINGS_NOT_THING.format(eid='STREET', word=word) and 'things' not in saved(store)['round']['elements']['STREET']   # nothing stored
    assert RS.things_fault(street_plan(), 'TILE', [], 'Why.') == RS.THINGS_NOT_PLACE.format(eid='TILE')
    assert RS.things_fault(street_plan(), 'STREET', ['TILE'], '') == RS.THINGS_REASON.format(eid='STREET', max=RS.REASON_CHARS)
    assert RS.things_fault(street_plan(), 'STREET', 'TILE', 'Why.') == RS.THINGS_SHAPE.format(eid='STREET')


def test_216b_the_list_given_with_the_proposal_is_kept_and_checked():
    from test_design211b_older_pure import saved
    from test_design211b_round_pure import film, post, refused, rows
    store, conn = film(plan=street_plan())
    post(store, conn, rows(STREET={'things': ['TILE', 'BRICK'], 'things_reason': 'The roof tiles and the bricks.'}))
    assert saved(store)['round']['elements']['STREET']['things']['ids'] == ['TILE', 'BRICK']
    store, conn = film(plan=street_plan())
    assert RS.THINGS_NOT_THING.format(eid='STREET', word='MASON') in refused(lambda: VS.round_start(store, {'id': 'u1'}, RUN, [], rows(STREET={'things': ['MASON'], 'things_reason': 'x'}), conn=conn))


def test_216b_no_reference_needed_a_removed_thing_two_places_and_a_new_list():
    plan, s = street_plan(), listed(ready('making', street_plan()), ['TILE', 'BRICK', 'FAN'])
    s['round']['elements']['FAN']['ignored'] = True                                                         # "No reference needed": named in words, holds nothing
    for r in s['references'].values():
        if r.get('element_id') == 'TILE':
            r['status'] = 'candidate'
    s['drawings'] = {}
    assert [t['id'] for t in RS.pending_things(plan, s, 'STREET')] == ['TILE', 'BRICK']
    req = RS.set_request(plan, RUN, s, el('STREET', plan), s['round']['elements']['STREET'])
    assert 'Wall fan regulator' in req['prompt'].split('from their descriptions: ')[1]
    gone = copy.deepcopy(plan)
    gone['elements'] = [e for e in gone['elements'] if e['id'] != 'TILE']                                  # a plan revision removed the tile: dropped, not blocking
    assert [t['id'] for t in RS.pending_things(gone, s, 'STREET')] == ['BRICK']
    two = copy.deepcopy(plan)
    two['elements'].append({**el('STREET', plan), 'id': 'YARD', 'name': 'The yard'})                       # two places listing the same thing
    s['round']['elements']['YARD'] = {**s['round']['elements']['STREET'], 'things': {'ids': ['TILE'], 'reason': 'Its tiled shed.', 'at': F.NOW}}
    assert [t['id'] for t in RS.pending_things(two, s, 'YARD')] == ['TILE'] and 'TILE' in [t['id'] for t in RS.pending_things(two, s, 'STREET')]
    listed(s, ['BRICK'])                                                                                     # the list changed between two makes: the next make uses it
    assert [t['id'] for t, _ in RS.place_things(plan, s, el('STREET', plan))] == ['BRICK']
    req = RS.set_request(plan, RUN, s, el('STREET', plan), s['round']['elements']['STREET'])
    assert 'Roof tile' not in req['prompt'].split('from their descriptions: ')[-1]


def test_216b_a_place_set_aside_while_it_waits_for_its_list_is_never_made():
    from test_design211b_older_pure import saved
    from test_design211b_round_pure import jobs, put
    store, conn = no_list_film()
    s = saved(store)
    s['round']['elements']['STREET']['ignored'] = True           # the operator: do not make this set
    put(store, s)
    assert RS.things_asked(store, RUN, [])['places'] == []
    out = VS.guarded(lambda: RS.round_things(conn, store, {'id': 'u1'}, RUN, [], [{'element_id': 'STREET', 'things': [], 'reason': 'Nothing stays.'}]))
    assert out['queued'] == [] and 'STREET' not in jobs(conn)


def test_216b_a_place_that_has_its_list_is_ordered_once_though_it_was_still_marked_as_waiting():
    from test_design211b_older_pure import saved
    from test_design211b_round_pure import put, req
    store, conn = no_list_film()
    s = saved(store)
    s['round']['elements']['STREET']['things'] = {'ids': [], 'reason': 'Nothing stays.'}   # the list came with the round file, the mark stayed
    put(store, s)
    VS._queue_sets(conn, store, {'id': 'u1'}, RUN, [], ['STREET'])                         # the operator: make it
    assert not saved(store)['round']['elements']['STREET'].get('things_due')
    out = VS.guarded(lambda: RS.round_things(conn, store, {'id': 'u1'}, RUN, [], [{'element_id': 'STREET', 'things': [], 'reason': 'Nothing stays.'}]))
    assert out['queued'] == [] and [req(p)['reference']['element_id'] for p in conn.inserted].count('STREET') == 1


def test_216b_a_hold_of_0113_waits_for_claudes_list_and_a_made_place_is_untouched():
    from test_design211b_older_pure import saved
    from test_design211b_round_pure import jobs, put
    store, conn = no_list_film()
    s = saved(store)
    row = s['round']['elements']['STREET']
    row.pop('things_due')
    row['held'] = ['SHUTTER_OIL', 'BRICK']                                                                   # as 0.113.0 left it: held on the shared-shots guess
    put(store, s)
    before = json.dumps({k: v for k, v in saved(store)['round']['elements'].items() if k != 'STREET'}, sort_keys=True)
    assert RS.release(conn, store, {'id': 'u1'}, RUN, []) == [] and 'STREET' not in jobs(conn)             # not ordered on the guess
    row = saved(store)['round']['elements']['STREET']
    assert 'held' not in row and row['things_due'] is True                                                  # it waits for Claude's list instead
    assert json.dumps({k: v for k, v in saved(store)['round']['elements'].items() if k != 'STREET'}, sort_keys=True) == before   # a place made or ordered is left alone
    VS.guarded(lambda: RS.round_things(conn, store, {'id': 'u1'}, RUN, [], [{'element_id': 'STREET', 'things': [], 'reason': 'Nothing stays.'}]))
    from test_design211b_round_pure import req
    assert [req(p)['reference']['element_id'] for p in conn.inserted].count('STREET') == 1   # ordered once
    assert RS.release(conn, store, {'id': 'u1'}, RUN, []) == []                                              # never twice


def test_216b_the_place_line_shows_claudes_list_under_details(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: listed(s, ['TILE'], 'The tiled roof over the street.'))
    street = film.lines()['set:STREET']
    assert ["The film's things shown in this place", ['Roof tile.', 'The tiled roof over the street.']] in street['details']
    film.change(lambda s: listed(s, [], 'Nothing of the film stays in the street.'))
    assert ["The film's things shown in this place", ['none.', 'Nothing of the film stays in the street.']] in film.lines()['set:STREET']['details']
