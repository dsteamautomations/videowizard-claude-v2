"""design/211, the review of 17 Nov 2026 (three critics): the request and its checks fit every category of film; what the operator is told
is true; the "what next" sentences; money and limits. One test or more per finding, named by its label (C1 … M6). The film is the shared
fixture's, walked with the real modules (the harness of `test_design211_together_pure`). Without a database."""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app import chat_flow as CF, page_flow as P, ref_find as RF, ref_sets as RS, visuals_stage as VS
import d211_fixture as F
from test_design211_together_pure import Film, RUN, USER, a_look, ans, approve, at_step_1, chat, outside, round_file, says, searched   # noqa: F401 (`outside`: ffmpeg and the prices stood in)

PERFUME = {'id': 'BOTTLE', 'name': 'The perfume bottle', 'kind': 'object', 'identity': 'exact', 'requirements': 'The product of the advertisement.', 'required_views': [], 'size': [],
           'description': 'A square clear glass bottle with a gold cap; the label reads "NOOR" in thin black capitals.'}
SOFTWARE = {'id': 'P_SAVE', 'name': 'Saving the file', 'kind': 'process', 'identity': 'representative', 'requirements': 'The progress bar fills and the tick appears.', 'required_views': [], 'size': [],
            'description': 'On the screen a blue progress bar fills from left to right, then a green tick replaces it.'}
RISING = {'id': 'P_RISE', 'name': 'Dough rising', 'kind': 'process', 'identity': 'representative', 'requirements': 'The dough doubles in the bowl.', 'required_views': [], 'size': [],
          'description': 'A ball of pale dough in a steel bowl swells until it domes above the rim.'}
WATER = {'id': 'WATER', 'name': 'Clean water', 'kind': 'material', 'identity': 'representative', 'requirements': 'It stands a finger deep on the slab.', 'required_views': [], 'size': [], 'description': 'Clear water.'}
PAN = {'id': 'PAN', 'name': 'Round metal pan', 'kind': 'object', 'identity': 'exact', 'requirements': 'The pan the workers carry.', 'required_views': ['side', 'tipped, pouring'], 'size': [],
       'description': 'A round, shallow, dull grey steel pan with a rolled rim, dented and crusted with dried cement.'}


def film_plan(*more, look=None):
    """The fixture's plan with more things, each named by one made shot of a scene of its own."""
    plan = F.plan()
    for n, e in enumerate(more, 1):
        plan['elements'].append(copy.deepcopy(e))
        plan['gaps'].append({'gap_id': f'X{n}', 'scenes': [{'id': f'X{n}-S1', 'location_time': 'a studio table, soft window light, afternoon', 'outfit': {},
                                                             'shots': [{'id': f'X{n}-S1-SH1', 'visual_type': 'image', 'size': 'CU', 'element_ids': [e['id']], 'message': 'm'}]}]})
    if look is not None:
        plan['foundation']['appearance'] = look
    return plan


def ask(element, row=None, session=None, plan=None, look=None):
    plan = plan or film_plan(element, look=look)
    s = session or F.specs_approved(F.session('making'), plan, VS.spec_digest)
    return RS.set_request(plan, RUN, s, next(e for e in plan['elements'] if e['id'] == element['id']), row or {'prompt': ''})


def checks(r):
    return {l['check']: l['pass_when'] for l in r['lines']}


def el(eid):
    return next(e for e in F.plan()['elements'] if e['id'] == eid)


# ---------- GROUP 1: the request and its checks ----------

@pytest.mark.parametrize('thing', [SOFTWARE, RISING])
def test_C1_a_way_of_working_with_no_hands_is_not_asked_for_hands_or_a_tool(thing):
    r = ask(thing)
    said = r['prompt'] + ' ' + ' '.join(v['ask'] + ' ' + v['name'] for v in r['views'])
    assert not re.search(r'the hands and|the tool meeting|the hands and forearms doing it', said)
    assert 'allowed where the description names them, never required' in r['prompt'] and 'the action or the change' in r['views'][0]['ask']
    line = checks(r)['the action is shown']
    assert line.startswith('the action or the change is shown') and 'not required' in line and 'no face' in line and 'the hands and the tool doing it' not in line
    assert 'no person' not in checks(r)   # hands stay allowed for a way of working that has them


def test_C2_lettering_the_description_names_is_allowed_in_the_request_and_in_the_check():
    r = ask(PERFUME)
    assert "maker's stamps" not in r['prompt'] and 'except what the description names' in r['prompt'] and RS.FINISH in r['prompt']
    assert checks(r)['no text'].endswith('except lettering the description names')
    assert 'except lettering the description names' in RS.PERSON_SET


def test_C3_the_order_of_authority_is_said_once_and_the_check_carries_the_operators_words():
    plan = F.plan()
    s = F.specs_approved(F.session('making'), plan, VS.spec_digest)
    r = RS.set_request(plan, RUN, s, el('TROWEL'), {'prompt': 'The blade is narrow.', 'operator_words': ['An earlier word.', 'The handle is red, not brown.']})
    order = "(1) the operator's words; (2) the words added by the film's writer; (3) the film's own footage picture; (4) the description from the film's plan; (5) real photographs from the web"
    assert r['prompt'].count(RS.AUTHORITY.format(order=order)) == 1 and 'the photographs win' not in r['prompt'] and 'this wins' not in r['prompt']
    line = checks(r)['matches the description']
    assert line.startswith("it agrees with these, the earlier winning where two differ: the operator's words: The handle is red, not brown; the words added by the film's writer: The blade is narrow; the description of the plan: ")
    assert 'A pointed steel blade, a reddish-brown handle.' in line and 'An earlier word.' not in line
    assert "where the operator's words or the words added by the film's writer say otherwise, they win" in checks(r)['matches the footage picture']
    web = ask(PERFUME)   # no operator, no writer, no film picture: the plan, then the web
    assert RS.AUTHORITY.format(order="(1) the description from the film's plan; (2) real photographs from the web") in web['prompt'] and 'the photographs win' not in web['prompt']
    assert checks(web)['matches the description'] == 'it agrees with the description of the plan: ' + PERFUME['description']


def test_S11_between_the_drawing_and_the_footage_picture_the_request_says_which_wins_for_what():
    plan = F.plan()
    s = F.specs_approved(F.session('making'), plan, VS.spec_digest)
    s['references']['drawing-TILE-iso-eeeeeeee'] = {'id': 'drawing-TILE-iso-eeeeeeee', 'kind': 'drawing', 'element_id': 'TILE', 'status': 'approved', 'key': 'k', 'sha256': 'f' * 64, 'view': 'iso'}
    r = RS.set_request(plan, RUN, s, el('TILE'), {'prompt': ''})
    assert {i['role'] for i in r['inputs']} == {'footage', 'drawing'}
    assert "the film's own pictures (the approved drawing for shape and size; the film's footage picture for look, colour and wear)" in r['prompt']
    assert 'its shape and size come from the approved drawing' in r['prompt'] and 'its exact form, colour, material and wear.\n' not in r['prompt'].split('The subject:')[1]
    assert 'its shape and size follow the approved drawing' in checks(r)['matches the footage picture']


def test_C6_a_persons_sheet_names_no_place():
    r = ask(el('MASON'), plan=F.plan())
    assert 'Where the film shows them' not in r['prompt'] and 'the sandy street' not in r['prompt'] and r['parts']['place'] == '' and 'plain neutral ground' in r['prompt']
    assert '(MASON)' not in r['prompt'] and 'MASON' not in r['prompt']   # no code name either


def test_S7_a_material_has_its_own_views():
    r = ask(WATER)
    assert [v['name'] for v in r['views']] == ['a surface of it, filling the frame', 'as the film uses it', 'very close: what it is made of'] == RS.view_names(WATER)
    assert 'how it is made' not in ' '.join(v['ask'] for v in r['views']) and RS.MAY_SHOW['material'] in r['prompt'] and RS.MAY_SHOW['material'] != RS.MAY_SHOW['object']


def test_S8_only_the_looks_sentences_for_a_photograph_are_placed_and_the_setting_wins_for_light():
    look = 'Handheld, natural colours, soft daylight. Drawn diagrams follow the graphic style. Titles are set in a plain sans-serif.'
    r = ask(PERFUME, look=look)
    assert 'Drawn diagrams' not in r['prompt'] and 'Titles are set' not in r['prompt'] and r['parts']['look'] == 'Handheld, natural colours, soft daylight'
    assert RS.LOOK_LINE.format(look='Handheld, natural colours, soft daylight') in r['prompt'] and 'For light, the place and time of the setting win.' in RS.LOOK_LINE
    assert ask(PERFUME, look='Diagrams are drawn flat.')['parts']['look'] == 'as the footage'


def test_S9_a_weak_frame_is_shown_whole_and_uncovered_and_keeps_the_described_wear():
    assert 'show the thing whole and uncovered' in RS.FRAME_WEAK_LINE and 'the wear the description names' in RS.FRAME_WEAK_LINE and 'clean' not in RS.FRAME_WEAK_LINE


@pytest.mark.parametrize('views, names', [
    (['side', 'tipped, pouring'], ['side', 'tipped, pouring', 'the detail that shows how it is made']),
    (['side'], ['side', 'as the film uses it', 'the detail that shows how it is made']),
    ([], ['whole and at rest', 'as the film uses it', 'the detail that shows how it is made']),
    (['side', 'held close'], ['side', 'held close', 'whole and at rest']),            # every default has its like: still three
    (['a stacked pair'], ['a stacked pair', 'whole and at rest', 'as the film uses it'])])
def test_S10_a_default_view_the_plan_already_shows_is_left_out_and_there_are_always_three(views, names):
    got = RS.view_names({**PAN, 'required_views': views})
    assert got == names and len(set(got)) == 3


def test_S10_a_view_in_use_may_show_the_hand_and_the_material_the_description_names():
    r = ask({**PAN, 'required_views': []})
    assert 'the thing alone' not in r['prompt'] and 'the hand that holds it and the material it works on may be shown where the description names them' in r['prompt']
    assert 'the material the thing works on' in checks(r)['no person']


def test_the_request_holds_no_code_name_and_no_doubled_full_stop():
    street = {**el('STREET'), 'requirements': 'Landmarks: near_house_wall (the half-built brick wall of the nearest house), road (the sandy road running away from the camera).'}
    pan = {**PAN, 'requirements': 'The pan the workers carry and tip in the footage (clips C0084, C0085, C0087).'}
    assert 'What it must meet: The pan the workers carry and tip in the footage.' in ask(pan)['prompt'] and 'C0084' not in ask(pan)['prompt']
    pour = {**SOFTWARE, 'requirements': 'The pan is tipped away from the body, as in clips C0084 and C0087.'}
    assert 'as in the footage.' in ask(pour)['prompt'] and 'C0084' not in ask(pour)['prompt']
    plan = F.plan()
    plan['elements'] = [street if e['id'] == 'STREET' else e for e in plan['elements']]
    for r in (ask(street, plan=plan), ask(PERFUME), ask(SOFTWARE), ask(el('MASON'), plan=F.plan()), ask(el('T_LAY'), plan=F.plan()), ask(el('BRICK'), plan=F.plan())):
        assert '(documentary' not in r['prompt'] and not re.search(r'(?<!\.)\.\.(?!\.)', r['prompt']) and not re.search(r'\b[a-z]+_[a-z_]+\b', r['prompt']), r['prompt']
        assert not re.search(r'\((?:%s)\)' % '|'.join(F.THINGS), r['prompt'])
    assert 'What it must meet: Landmarks: the half-built brick wall of the nearest house; the sandy road running away from the camera.' in ask(street, plan=plan)['prompt']


# ---------- GROUP 2: what the operator is told ----------

def money(n):
    return f'₹{n * VS.image_price_inr(RUN, provider="gemini") * VS.SET_MAX:,.0f}'


def step1_done(film, **answers):
    """Step 1 recorded on the page: the fixture's answers (TROWEL used from footage, FAN left out, BRICK and TILE a set), the routine things accepted."""
    lines = film.lines()
    given = {'TROWEL': 'use', 'FAN': 'ignore', 'BRICK': 'set', 'TILE': 'set', **answers}   # design/212: the buttons of step 1 (Approve, Leave out, Make a set)
    return film.record(*[ans(lines['ref:' + e], c) for e, c in given.items()], ans(lines['refs:proposals'], 'accept_all'))


def at_step_2(film=None, **answers):
    film = film or at_step_1()[0]
    step1_done(film, **answers)
    film.back()
    film.set_looks()
    return film


def put_session(film, s):
    film.store.files[[k for k in film.store.files if k.endswith('session.json')][0]] = json.dumps(s).encode('utf-8')


def test_C4_the_proposals_say_how_many_sets_are_made_first_and_that_the_rest_are_asked_after():
    """design/212 (SK, 17 Nov 2026): the same truth about the sets, with no price in the sentence or on the button."""
    film, _ = at_step_1()
    lines = film.lines()
    assert lines['refs:proposals']['buttons'][0]['label'] == 'Accept all 2'                         # the routine things; the person not in the footage is not among them
    film.record(ans(lines['ref:TROWEL'], 'set'), ans(lines['ref:BRICK'], 'set'))                  # two more sets asked for on other lines
    line = film.lines()['refs:proposals']
    assert 'The first 3 sets are made to check the method' in line['text'] and 'at most 3 times' in line['text']
    assert '₹' not in line['text'] and 'paid' not in line['text'] and line['buttons'][0]['label'] == 'Accept all 2'
    item = film.next()['item']
    assert item['id'] == 'round1:all' and item['text'] == line['text'] and item['buttons'][0]['label'] == line['buttons'][0]['label']   # the same words in the chat


def rest_with_a_person():
    """The first go is three things; the second go holds a person and a thing."""
    film = Film()
    searched(film)
    film.post(round_file(film, MASON={'first': False}, BRICK={'first': True}))
    return at_step_2(film)


def test_C5_leave_these_out_never_covers_a_person_and_names_the_shots_that_lose_a_reference():
    film = rest_with_a_person()
    assert film.session()['round']['rest'] == ['MASON', 'TILE']
    line = film.lines()['sets:rest']
    said = chat(film, 'sets:rest')   # design/213: the page line has its parts and short labels; the chat says the same as one text
    assert [b['choice'] for b in line['buttons']] == ['rest', 'rest_out'] and [b['label'] for b in line['buttons']] == ['Make them', 'Do not make this set'] and line['buttons'][1]['loss']['button'] == 'Do not make this set; make the other 1'   # design/213 review: the words pressed say all the click does
    assert [b['label'] for b in said['buttons']] == ['Make the other 2 sets', 'Do not make this set; make the other 1']
    assert 'The mason: a person shown in a made picture always gets a set' in said['text'] and line['buttons'][1]['loss']['people'] == 'This person always gets a set: The mason. Not making the others also has their set made, on the same word, when you say done in the chat.'
    assert line['cost'] == 'Without this set, these shots are made with no reference: Roof tile: shot 2 of gap 3.'
    assert film.record(ans(line, 'rest_out'))['refused'][0]['message'] == CF.WORDS['rest_first'] and not film.row('TILE').get('ignored')   # design/213 review: not while a first set is unjudged
    judged = [ans(l, next((p['choice'] for p in l['pics'] if p.get('choice')), 'yes')) for l in film.lines().values() if l.get('case') == 'judge']
    assert film.record(ans(line, 'rest_out'), *judged)['refused'] == []                                                                  # judged in the same visit: taken after them
    assert film.row('TILE')['ignored'] and not film.row('MASON').get('ignored')
    # design/213: the person, who always gets a set, is made on the same word (before: the line stayed, with "Make the other set" alone)
    assert film.ordered()[-1] == 'MASON' and film.session()['round']['rest'] == [] and 'sets:rest' not in film.lines()


def test_S12_the_comment_hint_is_true_for_every_answer_of_the_line():
    """design/212: step 1 has no comment box: the words come with "Minor corrections". The hint stands where a box is still shown (a thing back at step 2)."""
    film, _ = at_step_1()
    trowel = film.lines()['ref:TROWEL']
    assert {b['choice'] for b in trowel['buttons']} >= {'use', 'set', 'fix'} and 'comment_hint' not in trowel and 'comment' not in trowel
    assert 'when a set is made; with any other answer they are not used' in CF.WORDS['hint'] and 'They go into the request of its set' not in CF.WORDS['hint']


def test_S13_step_2_names_no_money_and_the_chat_says_the_same_words():
    """design/212 (SK, 17 Nov 2026): no cost on the page's references steps. Before (design/211 review, S13): step 2 said what the plan's shots still need."""
    film = at_step_2()
    page = film.page()
    rest = next(l for l in page['lines'] if l['key'] == 'sets:rest')
    assert '₹' not in page['summary'] and '₹' not in json.dumps(page['lines']) and 'still need' not in json.dumps(rest) and 'text' not in rest   # design/213: the page line carries its parts
    out = film.next()
    while out['item'] and not out['item']['id'].startswith('rest:'):
        out = film.decide(out['item']['id'], out['item']['buttons'][0]['choice'], 'this one')
    assert out['item']['text'].endswith('\n' + rest['cost']) and '₹' not in out['item']['text'] and 'still need' not in out['item']['text']   # the same words in the chat


def test_S14_a_set_made_again_shows_the_set_before_in_the_chat_too():
    film = at_step_2()
    film.record(ans(film.lines()['set:T_LAY'], 'correct', 'Show the hand pressing the brick down.'))
    film.rewrite([{'element_id': 'T_LAY', 'prompt': 'The right hand presses the wet brick into the mortar bed.'}])
    film.back()
    film.set_looks()
    line = film.lines()['set:T_LAY']
    item = next(i for i in CF._round_items(CF._ctx(film.conn, film.store, USER, film.run, film.outputs), every=True) if i['_key'] == 'set:T_LAY')
    assert len(line['earlier']) == 3 and len([s for s in item['show'] if '-before-' in s['name']]) == 3
    assert CF.WORDS['earlier'].format(labels='Before: A, Before: B, Before: C') in item['text'] and 'The set before is shown too' in CF.WORDS['earlier']


def test_S15_the_check_is_told_in_plain_words_an_errored_check_is_not_checked_and_no_id_is_shown():
    film = at_step_2()
    s = film.session()
    first = s['round']['elements']['STREET']['set']
    s['references'][first]['check'] = {'code': [{'check': 'size', 'weight': 'must', 'pass': False, 'seen': '1024x1024'}, {'check': 'parent', 'weight': 'must', 'pass': False, 'seen': 'abc12345, def67890'}],
                                       'lines': [], 'must_failed': [{'check': 'size', 'weight': 'must', 'pass': False, 'seen': '1024x1024'}], 'model': 'm', 'error': 'TimeoutError: no answer'}
    put_session(film, s)
    line = film.lines()['set:STREET']
    # design/214: the code checks stay; a model's error stored before is no longer read (Claude's look answered the picture's lines)
    assert line['check']['state'] == 'fail' and line['check']['lines'] == ['Picture A is not the size asked for.', 'Picture A was made from a picture that is not approved.']
    assert '1024' not in json.dumps(line['check']) and 'abc12345' not in json.dumps(line) and 'TimeoutError' not in json.dumps(line)
    lay = film.lines()['set:T_LAY']
    assert lay['check']['state'] == 'pass' and lay['check']['lines'] == []


def test_S16_N2_the_looks_listing_carries_the_judging_points_and_the_shape_of_the_file():
    film, _ = at_step_1()
    step1_done(film)
    film.back()
    how = film.due()['how']
    assert how == RS.LOOK_HOW and len(how['judge']) == 6 and any('approved drawing' in p and 'footage picture' in p for p in how['judge']) and any("the plan's description" in p for p in how['judge'])
    row = how['file']['sets'][0]
    assert set(row) == {'element_id', 'set', 'recommend', 'golden', 'reason', 'chose', 'aside', 'pictures'} and set(row['pictures'][0]) == {'ref', 'view', 'verdict', 'seen', 'lines', 'not_checked'} and '--looks' in how['send']
    assert '`how`' in RS.SETS_LOOK and 'its group name' in RS.SETS_LOOK and 'its group name' in RF.FIND_START
    helper = (Path(__file__).resolve().parents[2] / 'plugin' / 'agents' / 'vw-set-look.md').read_text(encoding='utf-8')
    assert '`how`' in helper and 'approved drawing' in helper and 'Each picture shows the view its turn asked for' not in helper   # one source: the server's


def test_what_the_operator_reads_at_step_1_says_the_unread_clips_once_and_holds_no_code_name():
    film, _ = at_step_1()
    page = film.page()
    said = 'Not searched for any thing, because they have no analysis: C003.mp4.'
    assert said in page['summary'] and 'no analysis' not in json.dumps(page['lines'])
    first = film.next()['item']
    assert first['summary'] == said + ' 1 person not in your footage gets a set from the description without being asked: The mason.' and said not in first['text']   # design/212: said once too
    assert not any('A size is not known' in w for l in page['lines'] for w in l.get('warnings') or [])
    lines = {l['key']: l for l in page['lines']}
    assert lines['ref:T_LAY']['title'] == 'Laying a brick (a way of working)' and lines['ref:T_LAY']['group'] == CF.STEP1_GROUPS[0]
    assert 'the closest is a close-up (shot 2 of gap 2).' in lines['ref:TROWEL']['used'] and not re.search(r'G\d-S\d-SH\d', json.dumps(page['lines']))
    assert lines['ref:TROWEL']['cost'] == 'These shots are then made with no reference of it: shot 1 of gap 2, shot 2 of gap 2.'
    film.decide(first['id'], 'each', 'ask me each one')
    nxt = film.next()['item']
    film.decide(nxt['id'], nxt['buttons'][0]['choice'], 'yes')
    assert 'summary' not in film.next()['item']   # said once: only while nothing is answered


# ---------- GROUP 3: the "what next" sentences ----------

def test_N4_while_the_sets_of_a_v2_round_are_made_the_page_says_wait_then_look():
    film, _ = at_step_1()
    out = step1_done(film)
    assert film.state() == 'making'
    assert film.page()['then'] == RS.SETS_MAKING and '`vw visuals round --looks`' in RS.SETS_MAKING and 'the operator judges the sets there' not in RS.SETS_MAKING
    assert says(RS.SETS_MAKING, 'vw visuals status', 'vw visuals round --looks') and P.SETS_WAIT not in json.dumps(out)


def test_N1_the_status_of_a_v2_round_has_one_sentence_for_each_state():
    film, _ = at_step_1()
    assert RS.status_of(film.session()) == RS.ROUND_STEP1
    step1_done(film)
    assert RS.status_of(film.session()) == RS.SETS_MAKING
    film.back()
    assert RS.status_of(film.session()) == RS.SETS_LOOK
    film.set_looks()
    assert RS.status_of(film.session()) == RS.SETS_PAGE
    film.record(ans(film.lines()['set:T_LAY'], 'no'))
    assert RS.status_of(film.session()) == RS.rewrite_due(film.session())
    for sentence in (RS.ROUND_STEP1, RS.SETS_MAKING, RS.ROUND_DONE):
        says(sentence)


def test_N5_the_digest_on_an_older_round_says_it_is_an_older_round():
    from test_design211b_older_pure import older
    film = Film(session=F.specs_approved(older('step1'), F.plan(), VS.spec_digest))
    assert film.do(lambda: RF.digest_answer(film.store, film.run, film.outputs))['then'] == RF.OLDER_ROUND


def test_N6_N9_with_the_plan_accepted_and_no_round_the_chat_says_what_comes_next():
    film = Film()
    out = film.next()
    assert out['item'] is None and out['then'] == RF.FIND_START
    searched(film)
    assert VS.round_due(film.session(), film.plan) == RF.LOOK_ALL == film.next()['then']   # nothing is left to search: the round file, not the search again


def test_N7_the_rewrite_sentence_names_the_things_and_the_operators_words():
    film = at_step_2()
    lines = film.lines()
    out = film.record(ans(lines['set:T_LAY'], 'correct', 'Show the hand pressing the brick down.'), ans(lines['set:MASON'], 'no'), ans(lines['set:STREET'], lines['set:STREET']['buttons'][0]['choice']),
                      ans(lines['sets:rest'], 'rest_out'))
    said = RS.rewrite_due(film.session())
    assert said.startswith('2 set(s) wait for your rewrite: MASON (no words: from the check and your look); T_LAY ("Show the hand pressing the brick down."). For each,')
    assert out['then'].endswith(said) and VS.round_due(film.session(), film.plan) == said and says(said, 'vw visuals round --rewrite')


def test_N8_step_1_recorded_with_nothing_ordered_says_what_was_not_ordered_and_why(monkeypatch):
    film, _ = at_step_1()

    def refused(*a, **k):
        raise ValueError('The picture service is not set up on this server.')
    monkeypatch.setattr(VS, 'generate_image', refused)
    verdicts = {e: {'verdict': 'ignore' if e == 'FAN' else 'approve'} for e in F.THINGS}
    then = film.do(lambda: VS.round_done(film.store, USER, film.run, film.outputs, verdicts, 'make them', conn=film.conn))['then']   # what `vw visuals round --verdicts` prints
    assert 'Step 1 is recorded. No set was ordered.' in then and "2 more wait for the operator's word." in then and 'The first 0 sets' not in then
    assert 'Not ordered: MASON: The picture service is not set up on this server.; STREET: ' in then and says(then, 'vw visuals page')


def test_N8_step_1_recorded_with_no_set_asked_for_says_so_and_what_comes_next():
    plan = F.plan()
    for gap in plan['gaps']:   # the mason is seen in his own footage only: no picture is made of him, so he may be left out
        for sc in gap['scenes']:
            for sh in sc['shots']:
                sh['element_ids'] = [e for e in sh['element_ids'] if e != 'MASON'] if sh['visual_type'] != 'footage' else sh['element_ids']
    film = Film(plan=plan)
    searched(film)
    film.post(round_file(film))
    out = film.do(lambda: VS.round_done(film.store, USER, film.run, film.outputs, {e: {'verdict': 'ignore'} for e in F.THINGS}, 'leave them all', conn=film.conn))
    assert out['then'] == RS.STEP1_NO_SET + ' ' + P.ROUND_NEXT and out['pass'] == 'complete' and film.ordered() == []


def test_N10_a_finder_replaces_a_frame_it_kept_by_sending_its_look_again_without_keep():
    film = Film()
    t = film.trial(('TROWEL', 'C001', 30.2), ('TROWEL', 'C001', 6.4))
    a, b = (x['id'] for x in t['trials'])
    film.look({'element': 'TROWEL', 'clips': ['C001'], 'note': 'n', 'looks': [a_look(a, 'side', keep=True)]})
    kept = film.session()['found']['TROWEL']['kept']
    out = film.look({'element': 'TROWEL', 'clips': ['C001'], 'note': 'n', 'looks': [a_look(a, 'side'), a_look(b, 'side', keep=True)]})
    assert out['refused'] == {} and len(out['kept']['TROWEL']) == 1 and out['kept']['TROWEL'] != kept and kept[0] not in film.session()['references']
    assert [f['view'] for f in RF.frames_of(film.session(), 'TROWEL')] == ['side']


def test_a_paid_step_of_a_v2_round_sent_by_the_tool_needs_the_operators_words():
    from test_design211b_older_pure import older
    film, _ = at_step_1()
    assert film.refused(lambda: VS.round_word(film.store, film.run, film.outputs, '  ')) == RS.WORD_NEEDED
    assert VS.round_word(film.store, film.run, film.outputs, 'yes, make them') is None
    old = Film(session=F.specs_approved(older('step1'), F.plan(), VS.spec_digest))
    assert VS.round_word(old.store, old.run, old.outputs, '') is None   # an older round: as before
    main = (Path(__file__).resolve().parents[1] / 'app' / 'main.py').read_text(encoding='utf-8')
    assert main.count('visuals_stage.round_word(storage(), run, outputs, body.quote)') == 2   # the doors of `round --verdicts` and `round --sets`


# ---------- GROUP 4: money and limits ----------

def made_three_times(film):
    """T_LAY made three times (each returned its pictures); the third set is with the operator."""
    film.record(ans(film.lines()['set:T_LAY'], 'no'))
    for n in (2, 3):
        film.rewrite([{'element_id': 'T_LAY', 'prompt': f'The hand presses the brick, try {n}.'}])
        film.back()
        film.set_looks()
        if n == 2:
            film.record(ans(film.lines()['set:T_LAY'], 'correct', 'Not yet.'))
    return film


def test_M1_no_fourth_make_whatever_way_the_order_comes():
    film = made_three_times(at_step_2())
    assert RS.makes(film.session(), 'T_LAY', film.row('T_LAY')) == 3
    film.record(ans(film.lines()['set:T_LAY'], 'aside', 'None is right.'))
    before = len(film.ordered())
    queued, errors = film.do(lambda: VS._queue_sets(film.conn, film.store, USER, film.run, film.outputs, ['T_LAY']))   # the one place every order passes
    assert queued == [] and errors == {'T_LAY': RS.MAKES_LIMIT.format(eid='T_LAY', max=3)} and len(film.ordered()) == before
    film.do(lambda: VS.set_aside(film.store, USER, film.run, film.outputs, 'T_LAY', back=True))   # brought back: its line offers no paid button
    line = film.lines()['set:T_LAY']
    assert 'make' not in [b['choice'] for b in line['buttons']] and CF.WORDS['made_max_unmade'].format(n=3) == line['head']   # design/213: the line's `head` (before: in its `text`)
    assert film.record(ans(line, 'make'))['refused'] and len(film.ordered()) == before and film.row('T_LAY')['round'] == 3


def test_M2_a_make_that_returned_no_picture_is_not_counted():
    film, _ = at_step_1()
    step1_done(film)
    film.back(fail=('T_LAY',))
    film.set_looks()
    for n in (2, 3, 4):   # the provider fails again and again: the operator may still ask
        line = film.lines()['set:T_LAY']
        assert [b['choice'] for b in line['buttons']] == ['make', 'aside'] and RS.makes(film.session(), 'T_LAY', film.row('T_LAY')) == 0
        assert film.record(ans(line, 'make'))['refused'] == [] and film.row('T_LAY')['round'] == n
        film.back(fail=('T_LAY',) if n < 4 else ())
        film.set_looks()
    lay = film.lines()['set:T_LAY']
    assert RS.makes(film.session(), 'T_LAY', film.row('T_LAY')) == 1 and RS.set_facts(film.session(), film.plan, 'T_LAY', film.row('T_LAY'))['makes_left'] == 2
    assert any(b['choice'] == 'no' for b in lay['buttons'])


def test_M3_accept_the_proposals_does_not_cover_a_frame_that_became_weak():
    film = Film()
    t = film.trial(('TROWEL', 'C001', 30.2), ('TROWEL', 'C001', 6.4), ('TILE', 'C002', 9.0), ('FAN', 'C001', 35.0))
    tid = {(x['elements'][0], x['at_s']): x['id'] for x in t['trials']}
    film.look({'element': 'TROWEL', 'clips': ['C001'], 'note': 'n', 'looks': [a_look(tid['TROWEL', 30.2], 'side', keep=True), a_look(tid['TROWEL', 6.4], 'side', 'weak', 'Half covered by mortar.')]},
              {'element': 'TILE', 'clips': ['C002'], 'note': 'n', 'looks': [a_look(tid['TILE', 9.0], 'underside', keep=True)]}, {'element': 'FAN', 'clips': ['C001', 'C002'], 'note': 'n'},
              {'element': 'MASON', 'clips': ['C001'], 'note': 'n'}, {'element': 'STREET', 'clips': ['C001', 'C002'], 'note': 'n'}, {'element': 'T_LAY', 'clips': ['C001'], 'note': 'n'},
              {'element': 'BRICK', 'clips': ['C001'], 'note': 'n'})
    film.post(round_file(film, TROWEL={'doubt': False}))
    trowel = film.lines()['ref:TROWEL']
    assert trowel['group'] == CF.STEP1_GROUPS[0] and not film.row('TROWEL')['doubt']                       # one good frame: routine, covered by the proposals
    film.record(ans(trowel, 'pics', pics={trowel['pics'][0]['choice'][4:]: 'not'}))              # "Not this picture": the weak frame takes its place
    lines = film.lines()
    assert lines['ref:TROWEL']['pics'][0]['weak'] and lines['ref:TROWEL']['group'] == CF.STEP1_GROUPS[1] and 'ref:TROWEL' not in lines['refs:proposals']['covers']
    film.record(ans(lines['refs:proposals'], 'accept_all'))
    assert 'TROWEL' not in (film.session().get('chat_round') or {}) and film.state() == 1 and not film.row('TROWEL').get('from_footage')


def test_M5_a_round_file_sent_again_reopens_only_what_is_new_or_changed_in_the_plan():
    film = at_step_2(BRICK='ignore', TILE='ignore')
    lines = film.lines()
    film.record(ans(lines['set:MASON'], 'yes'), ans(lines['set:STREET'], approve(lines['set:STREET'])), ans(lines['set:T_LAY'], approve(lines['set:T_LAY'])))   # design/213: the page sends the picture chosen
    assert film.state() == 'complete'
    out = film.post(round_file(film, FAN={'rec': 'set', 'reason': 'It is seen closer now.'}))   # the same plan: nothing comes back, the round stays complete
    assert out['reopened'] == [] and out['then'] == RS.MERGE_NONE and film.state() == 'complete' and film.row('FAN')['ignored'] and says(out, 'vw visuals round --back')
    plan = copy.deepcopy(film.plan)
    next(e for e in plan['elements'] if e['id'] == 'FAN')['description'] = 'A square cream dial on a brown plate.'
    plan['elements'].append(copy.deepcopy(PERFUME))
    film.plan = plan
    film.store.files[[k for k in film.store.files if k.endswith('plan-v1.json')][0]] = json.dumps({'document': plan}).encode('utf-8')
    film.look({'element': 'FAN', 'clips': ['C001'], 'note': 'Searched again.'}, {'element': 'BOTTLE', 'clips': ['C001'], 'note': 'Not in the footage.'})
    out = film.post(round_file(film) + [{'element_id': 'BOTTLE', 'rec': 'set', 'reason': 'The product.'}])
    assert out['reopened'] == ['FAN', 'BOTTLE'] and out['then'] == RS.MERGE_ASK.format(n=2) and film.state() == 2 and film.row('BRICK')['ignored'] and not film.row('BRICK').get('reopened')
    lines = film.lines()
    assert CF.WORDS['reopen_changed'] == lines['set:FAN']['head'] and CF.WORDS['reopen_new'] == lines['set:BOTTLE']['head'] and CF.WORDS['reopen_changed'] in chat(film, 'set:FAN')['text'] and 'set:BRICK' not in lines
    out = film.do(lambda: VS.set_aside(film.store, USER, film.run, film.outputs, 'BRICK', back=True))   # the operator asks for it by name
    assert film.row('BRICK')['reopened'] == 'asked' and CF.WORDS['reopen_left'] == film.lines()['set:BRICK']['head'] and says(out, 'vw visuals page')


def test_M6_a_set_of_a_v2_round_is_never_made_by_the_image_command():
    film, _ = at_step_1()
    body = {'element_id': 'STREET', 'kind': 'sheet', 'name': 'set-STREET', 'subject': 'The street', 'prompt': 'A street.', 'parents': [], 'request_id': 'r-1'}
    assert film.refused(lambda: VS.generate_image(film.conn, film.store, USER, film.run, film.outputs, body)) == VS.SHEET_BY_ROUND.format(eid='STREET')
    assert film.ordered() == [] and says(VS.SHEET_BY_ROUND, 'vw visuals page', 'vw visuals round --file')


# ---------- the instructions say what the program does (the wording script of the review) ----------

ROOT = Path(__file__).resolve().parents[2]


def visuals_text():
    d = json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    return st, next(p['text'] for p in st['parts'] if p['name'] == 'picture-search')


def test_N3_the_step_list_names_the_rebuilt_way_and_the_older_sentences_are_retired():
    st, text = visuals_text()
    step = next(s for s in st['steps'] if s.startswith('The picture search'))
    assert '`vw visuals digest`' in step and '`vw visuals round --looks`' in step and 'each row a proposal' in step and '`vw visuals frame --file`' not in step and '`vw visuals elements`' not in step
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    agents = ' '.join(p.read_text(encoding='utf-8') for p in (ROOT / 'plugin' / 'agents').glob('*.md'))
    everything = json.dumps(json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8')), ensure_ascii=False) + agents
    for gone in ('`vw visuals elements`; `vw visuals frame --file`; out/reference-round.json', 'and the tool meeting the material (hands and forearms, no face)',
                 'in one click that shows the total price', 'the server adds the kept preamble', 'each thing gets the footage picture or Ignore this', 'judges them all in one shot'):
        assert gone in retired and gone not in everything, gone


def test_the_instruction_the_request_and_the_check_agree_after_the_review():
    _st, text = visuals_text()
    assert 'a way of working as the action or the change at its key moment, its result, and close on where it happens (hands and a tool allowed where the description names them, never required; no face)' in text
    assert [v['name'] for v in RS.WAY] == ['the action at its key moment', 'the result just after', 'close on where it happens'] and 'never required' in RS.MAY_SHOW['technique']
    assert 'a material as a surface, as the film uses it, and very close' in text and 'lettering only where the description names it' in text
    assert "the operator's words, your added words, the film's own pictures (the approved drawing for shape and size, the footage picture for look, colour and wear), the plan's description, then web photographs" in text
    assert 'a make that returned no picture not counted' in text and 'says how many sets are made first and that the others are asked after' in text   # design/212: no price
    assert 'brings back only a thing that is new in the plan or whose entry in the plan changed' in text and '`vw visuals round --back E`' in text and 'A set is never made with `vw visuals image --kind sheet`' in text
    assert "each given a group name, its thing ids, the run folder's path and the tool's command line" in text and 'its `how` gives the points to judge by' in text
    cmd = (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'its `how` gives the points to judge by and the shape of the file' in cmd and 'a make that returned no picture not counted' in cmd and '`vw visuals round --back <element>`' in cmd
