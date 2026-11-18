"""design/214 (SK, 18 Nov 2026): Claude checks the sets of a v2 round; the Gemini check is taken out of this step.

The picture model still makes the pictures. No model checks a set of a v2 round: the server builds each picture's check list (the lines
it built for the model's check: `image_check.lines_of`, one source), gives it with the sets to look at, and the look answers every line
of every picture. One result is shown, "Claude's check". Every other use of the model check is untouched. Without a database."""
import copy
import json
from pathlib import Path

import pytest

from app import chat_flow as CF, image_check as IC, page_flow as P, ref_sets as RS, visual_workers as VW, visuals_stage as VS
from app.config import Settings
import d211_fixture as F
from test_design211b_round_pure import RUN, USER, at_two, back, done, film, judge, look, looks, post, put, refused, saved, state   # noqa: F401
from test_design211b_sets_pure import Lock, el, finder, ready, request, store_of   # noqa: F401 (finder: the stand-in for part A, on every test)
from test_design211c_kit_pure import Film

REPO = Path(__file__).resolve().parents[2]
ALL = lambda p: [{'id': l['id'], 'pass': True, 'seen': 'As the drawing shows.' if l.get('say') else ''} for l in p['lines']]


@pytest.fixture(autouse=True)
def round_of_today(monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', 2)   # conftest gives every module not named test_design211* the older round; these tests post a round of today


def boom(*a, **k):
    raise AssertionError('the model check was called')


def finalize(monkeypatch, s, rid='s-street-1', extra=2, width=2752, height=1536, **request_more):
    """A picture job comes back: finalize_image on the session `s`. Returns (store, job, result, due)."""
    store = store_of(s)
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW.jobs, 'finish', lambda *a, **k: None)
    monkeypatch.setattr(VW.jobs, 'record_file', lambda *a, **k: None)
    job = {'id': s['references'][rid]['job_id'], 'run_id': RUN['id'], 'request': {'reference': {'id': rid}, **request_more}}
    result = {'key': f"{RUN['id']}/visuals/references/{rid}.png", 'sha256': 'a', 'bytes': 9, 'width': width, 'height': height, 'notes': 'n', 'sources': [],
              'extra': [{'key': f"{RUN['id']}/visuals/references/{rid}-{n}.png", 'sha256': str(n), 'bytes': 9, 'width': width, 'height': height} for n in range(2, 2 + extra)]}
    return store, job, result, VW.finalize_image(Lock(), job, 'retained', result, None, {'provider': 'gemini', 'pictures': 1 + extra}, None)


def making():
    s = F.session('making')
    s['references']['s-street-1']['server_checklist'] = request('STREET')['lines']
    return s


# ---------- 1. no model check for a set of a v2 round; the code checks stay ----------

def test_a_set_of_a_v2_round_is_not_checked_by_a_model_and_keeps_its_code_checks(monkeypatch):
    monkeypatch.setattr(IC, 'run_check', boom)
    monkeypatch.setattr(IC, '_model_check', boom)
    views = RS.views_for(el('STREET'), F.plan())
    store, job, result, due = finalize(monkeypatch, making(), views=[v['ask'] for v in views], view_names=[v['name'] for v in views])
    refs = saved(store)['references']
    three = [refs[r] for r in ('s-street-1', 's-street-1-2', 's-street-1-3')]
    assert not due and not any('check_pending' in r for r in three)                    # nothing is due: the worker never calls check_image for it
    assert all(list(r['check']) == ['code'] and [(c['check'], c['pass']) for c in r['check']['code']] == [('size', True)] for r in three)
    assert all(r['server_checklist'] and r['status'] == 'candidate' for r in three)    # the check list is still built and kept, for the look
    store, job, result, due = finalize(monkeypatch, making(), width=1536, height=2752)
    wrong = saved(store)['references']['s-street-1-2']
    assert not due and wrong['check']['code'][0]['pass'] is False and RS.check_summary(saved(store), wrong) == {'state': 'fail', 'failed': [{'check': 'size', 'seen': '1536x2752'}], 'error': None}


def still(s):
    r = s['references']['s-street-1']
    r.update(kind='keyframe', shot_id='G1-S1-SH1')
    [r.pop(k) for k in ('set', 'set_n')]


def start(s):
    still(s)
    s['references']['s-street-1']['role'] = 'start'


def sheet_alone(s):
    s.pop('round')


CASES = {'a still of a shot': (still, 0), 'the start picture of a video shot': (start, 0), 'a set of an older round': (lambda s: s['round'].pop('v'), 2),
         "a person's sheet with no round": (sheet_alone, 2)}


@pytest.mark.parametrize('case', list(CASES))
def test_every_other_picture_is_still_checked_by_the_model(monkeypatch, case):
    change, extra = CASES[case]
    s = making()
    change(s)
    store, job, result, due = finalize(monkeypatch, s, extra=extra)
    refs = saved(store)['references']
    ids = ['s-street-1'] + [f's-street-1-{n}' for n in range(2, 2 + extra)]
    assert due is True and all(refs[r]['check_pending'] is True and 'check' not in refs[r] for r in ids)
    seen = []
    monkeypatch.setattr(IC, 'run_check', lambda st, session, ref, res, transport: seen.append(ref['id']) or {'code': [], 'lines': [], 'must_failed': [], 'model': IC.CHECK_MODEL})
    monkeypatch.setattr(VW, 'connect', lambda: Lock())
    VW.check_image(job, result)
    assert seen == ids and all(saved(store)['references'][r]['check']['model'] == 'gemini-3.8-flash' for r in ids)


def test_takes_drawn_graphics_and_the_lines_of_other_pictures_are_as_before():
    worker = (REPO / 'server' / 'app' / 'visual_workers.py').read_text(encoding='utf-8')
    assert 'image_check.run_take_check(snapshot' in worker and 'image_check.drawn_sheet_check(sheet' in worker and 'image_check.run_check(store, session' in worker
    assert IC.CHECK_MODEL == 'gemini-3.8-flash' and 'image_check.check_lines(store, session, row' in (REPO / 'server' / 'app' / 'visuals_stage.py').read_text(encoding='utf-8')
    s = F.older_session()   # a set of an older round: its stored model result is read as before
    assert RS.check_summary(s, 's-street-1') == {'state': 'fail', 'failed': [{'check': 'size', 'seen': '2752x1536'}], 'error': None}
    assert RS.looks_due(store_of(s), RUN, []) == {'sets': [], 'then': None}


# ---------- 2. the check list goes to the looker; the look answers every line ----------

def test_the_sets_to_look_at_carry_each_pictures_check_list_with_stable_ids():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    out = RS.looks_due(store, RUN, [])
    s = saved(store)
    assert [x['element_id'] for x in out['sets']] == ['MASON', 'STREET', 'T_LAY'] and out == RS.looks_due(store, RUN, [])      # the same ids at every listing
    for x in out['sets']:
        for p in x['pictures']:
            ref = s['references'][p['ref']]
            assert 'check' not in p and [(l['check'], l['pass_when']) for l in p['lines']] == [(l['check'], l['pass_when']) for l in IC.lines_of(ref)]   # one source
            assert len({l['id'] for l in p['lines']}) == len(p['lines']) and all(set(l) == {'id', 'check', 'pass_when'} for l in p['lines'])
    lay, street, mason = out['sets'][2]['pictures'], out['sets'][1]['pictures'], out['sets'][0]['pictures']
    names = lambda p: [l['check'] for l in p['lines']]
    assert len(lay) == 3 and names(lay[0])[0] == 'the view' and IC.SAME_THING not in names(lay[0]) and IC.SAME_THING in names(lay[1]) and IC.SAME_THING in names(lay[2])
    assert {'matches the description', 'one thing only', 'no text', 'the action is shown'} <= set(names(lay[1]))
    asked = [l['check'] for l in s['references'][out['sets'][1]['set']]['server_checklist']]
    assert IC.SAME_THING not in asked and 'the place is the subject' in asked and 'the place is the subject' in names(street[0])      # a place of one picture: no line compares it with picture A
    assert 'one person' in ' '.join(names(mason[0])).lower() or len(names(mason[0])) > 3
    how = json.dumps(out['how'])
    assert 'Gemini' not in how and "program's check" not in how and 'not_checked' in how and '`lines`' in how and 'never from the request or the notes' in how
    assert "every line of every picture's check list" in RS.SETS_LOOK and out['then'] == RS.SETS_LOOK


def sent_for(store, eid='T_LAY'):
    sent = looks(store)
    return sent, next(x for x in sent if x['element_id'] == eid)


FAULTS = {
    'a line left out': lambda pic, l: (pic['lines'].remove(l), RS.LOOK_LINE_OPEN)[1],
    'pass is not true or false': lambda pic, l: (l.update({'pass': 'yes'}), RS.LOOK_LINE_OPEN)[1],
    'an unknown line': lambda pic, l: (pic['lines'].append({'id': 'feedbeef', 'pass': True}), RS.LOOK_LINE_UNKNOWN)[1],
    'a fail with no words': lambda pic, l: (l.update({'pass': False, 'seen': ' '}), RS.LOOK_LINE_WORDS)[1],
    'words too long': lambda pic, l: (l.update({'pass': False, 'seen': 'x' * 301}), RS.LOOK_LINE_WORDS)[1],
    'no answers at all, as an older tool sends': lambda pic, l: (pic.pop('lines'), RS.LOOK_LINE_OPEN)[1],
}


@pytest.mark.parametrize('fault', list(FAULTS))
def test_a_look_that_does_not_answer_every_line_is_refused_by_name_and_not_half_recorded(fault):
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    due = next(x for x in RS.looks_due(store, RUN, [])['sets'] if x['element_id'] == 'T_LAY')['pictures'][1]
    sent, mine = sent_for(store)
    pic = mine['pictures'][1]
    line = pic['lines'][2]
    listed = due['lines'][0 if fault.startswith('no answers') else 2]
    constant = FAULTS[fault](pic, line)
    out = RS.round_looks(store, USER, RUN, [], sent, 'helper')
    said = out['refused']['T_LAY']
    assert said == constant.format(eid='T_LAY', pic='the result just after', check=listed['check'], id='feedbeef' if fault == 'an unknown line' else listed['id'], max=300)
    assert 'the result just after' in said and '--looks' in said and 'again' in said                    # the picture, and how to send it again
    assert out['recorded'] == ['MASON', 'STREET'] and out['left'] == ['T_LAY'] and out['then'] == RS.SETS_LOOK
    s = saved(store)
    assert 'set_look' not in s['round']['elements']['T_LAY'] and not any(r.get('look') for r in s['references'].values() if r.get('element_id') == 'T_LAY' and r.get('kind') == 'sheet')
    assert state(store) == 'looking'


def test_a_fail_keeps_its_sentence_and_the_look_is_recorded_line_by_line():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    sent, mine = sent_for(store)
    bad = mine['pictures'][1]['lines'][0]
    bad.update({'pass': False, 'seen': ' A tool lying still;\n no hand. '})
    out = RS.round_looks(store, USER, RUN, [], sent, 'helper')
    assert out['recorded'] == ['MASON', 'STREET', 'T_LAY'] and out['refused'] == {} and state(store) == 2
    s = saved(store)
    pic = s['references'][mine['pictures'][1]['ref']]
    assert pic['look']['lines'][0] == {'id': bad['id'], 'check': 'the view', 'pass': False, 'seen': 'A tool lying still; no hand.'}
    assert [l['id'] for l in pic['look']['lines']] == [l['id'] for l in RS.check_lines(pic)] and 'pass_when' not in pic['look']['lines'][0]
    assert RS.check_summary(s, pic) == {'state': 'fail', 'failed': [{'check': 'the view', 'seen': 'A tool lying still; no hand.'}], 'error': None}
    assert RS.check_summary(s, mine['pictures'][0]['ref']) == {'state': 'pass', 'failed': [], 'error': None}
    again = RS.round_looks(store, USER, RUN, [], sent, 'helper')                       # the same look sent twice: recorded again, nothing else changes
    after = saved(store)
    assert again['recorded'] == out['recorded'] and again['refused'] == {} and state(store) == 2
    strip = lambda x: {k: strip(v) for k, v in x.items() if k != 'at'} if isinstance(x, dict) else [strip(v) for v in x] if isinstance(x, list) else x
    assert strip(after['references']) == strip(s['references']) and strip(after['round']) == strip(s['round'])


def test_a_picture_that_could_not_be_opened_is_not_checked_and_the_set_can_still_be_approved():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    sent, mine = sent_for(store)
    first, second = mine['pictures'][0]['ref'], mine['pictures'][1]['ref']
    mine['pictures'][1] = {'ref': second, 'not_checked': ' The file would not open. '}   # no verdict, no words, no lines
    mine.update(recommend='doubt', golden=None)
    out = RS.round_looks(store, USER, RUN, [], sent, 'helper')
    assert out['recorded'] == ['MASON', 'STREET', 'T_LAY'] and state(store) == 2
    s = saved(store)
    look_ = s['references'][second]['look']
    assert look_ == {'who': 'helper', 'at': look_['at'], 'view': 'the result just after', 'verdict': None, 'seen': '', 'trial': None, 'ref': second, 'not_checked': 'The file would not open.'}
    assert RS.check_summary(s, second) == {'state': 'none', 'failed': [], 'error': 'The file would not open.'} and RS.looked(s, 'T_LAY', s['round']['elements']['T_LAY'])
    assert VS.set_answer(store, USER, RUN, [], 'T_LAY', 'yes', golden=first)['stored'] is True     # it never blocks
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    sent, mine = sent_for(store)
    mine['pictures'][1] = {'ref': mine['pictures'][1]['ref'], 'not_checked': 'x' * 301}
    assert RS.round_looks(store, USER, RUN, [], sent, 'helper')['refused'] == {'T_LAY': RS.LOOK_SEEN.format(eid='T_LAY', max=300)}


def test_not_checked_beside_a_verdict_or_lines_is_refused_and_nothing_of_the_set_is_recorded():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    sent, mine = sent_for(store)
    mine['pictures'][1]['not_checked'] = 'no'          # a checked picture, the template's field filled all the same
    out = RS.round_looks(store, USER, RUN, [], sent, 'helper')
    assert list(out['refused']) == ['T_LAY'] and 'not_checked' in out['refused']['T_LAY'] and 'T_LAY' not in out['recorded']
    assert not saved(store)['references'][mine['pictures'][1]['ref']].get('look')


# ---------- 3. what the operator sees: one result, Claude's check ----------

def test_the_operator_sees_claudes_check_passed_faults_or_not_checked_on_the_page_and_in_the_chat(monkeypatch):
    film_ = Film(monkeypatch, '2')
    film_.change(lambda s: (s['references']['s-t_lay-1-3']['look'].pop('lines'), s['references']['s-t_lay-1-3']['look'].update(not_checked='It came back empty.', verdict=None, seen='')))
    lines = film_.lines()
    lay, mason = lines['set:T_LAY'], lines['set:MASON']
    assert mason['check'] == {'state': 'pass', 'by': "Claude's check passed: no fault found.", 'chip': "Claude's check passed", 'lines': []}
    assert lay['check'] == {'state': 'fail', 'by': "Claude's check found:", 'chip': "Claude's check found 1 fault",
                            'lines': ['Picture B: A tool lying still; no hand.', 'Picture C was not checked: It came back empty.']}
    made = [p for p in lay['pics'] if not p.get('ref_only')]
    assert [bool(p.get('flag')) for p in made] == [False, True, False] and lay['buttons']                # the amber dot on the picture a failed line names; nothing is blocked
    assert ["What Claude's check found", lay['check']['lines']] in lay['details']
    text = next(i for i in film_.items() if i['_key'] == 'set:T_LAY')['text']
    assert "Claude's check found:\nPicture B: A tool lying still; no hand.\nPicture C was not checked: It came back empty." in text   # the chat says the same
    whole = json.dumps(film_.page()) + json.dumps([i['text'] for i in film_.items()])
    assert 'Gemini' not in whole and "program's check" not in whole and 'gemini' not in whole
    assert not [w for w in CF.WORDS.values() if isinstance(w, str) and ("program's check" in w or 'Gemini' in w)]
    drawn = (Path(__file__).with_name('d213_sets_round.json')).read_text(encoding='utf-8')     # the round the page's browser tests draw: the chip and its lines as written here
    assert "Claude's check found 1 fault" in drawn and "Claude's check found:" in drawn and "program's check" not in drawn


# ---------- 4. sets made and checked by the model before this release ----------

def test_a_set_checked_by_the_model_before_and_not_looked_at_gets_its_list_and_its_model_result_is_no_longer_shown():
    s = F.session('looking')    # as VW-24's two sets stand: the model's results stored, one with a fault, no look recorded
    assert s['references']['s-t_lay-1-2']['check']['must_failed'] and RS.check_summary(s, 's-t_lay-1-2') == {'state': 'none', 'failed': [], 'error': None}
    store = store_of(s)
    out = RS.looks_due(store, RUN, [])
    assert [x['element_id'] for x in out['sets']] == ['MASON', 'STREET', 'T_LAY'] and all(p['lines'] and 'check' not in p for x in out['sets'] for p in x['pictures'])
    sent = [{'element_id': x['element_id'], 'set': x['set'], 'recommend': 'use', 'golden': None if x['element_id'] == 'MASON' else x['pictures'][0]['ref'], 'reason': 'All agree with the plan.',
             'chose': 'The most common variant.', 'aside': 'Nothing of the request.',
             'pictures': [{'ref': p['ref'], 'view': p['view'], 'verdict': 'pass', 'seen': 'As asked.', 'lines': ALL(p)} for p in x['pictures']]} for x in out['sets']]
    assert RS.round_looks(store, USER, RUN, [], sent, 'assistant')['recorded'] == ['MASON', 'STREET', 'T_LAY']
    after = saved(store)
    assert RS.state(after, after['round']) == 2 and RS.check_summary(after, 's-t_lay-1-2') == {'state': 'pass', 'failed': [], 'error': None}
    kept = after['references']['s-t_lay-1-2']['check']
    assert kept['model'] == 'gemini-3.8-flash' and kept['must_failed'][0]['seen'] == 'A tool lying still; no hand.'            # the model's result stays in the record


def test_a_look_of_before_stands_for_a_set_already_judged_and_is_due_again_for_one_that_is_not():
    s = F.session('2')
    for r in s['references'].values():
        if r.get('kind') == 'sheet':
            r['look'].pop('lines')          # looks recorded before this release: no line answers
    rows = s['round']['elements']
    rows['MASON']['answer'] = {'verdict': 'yes', 'golden': None, 'words': '', 'set': rows['MASON']['set'], 'by': 'u1', 'at': F.NOW}   # the operator already judged MASON's set
    assert RS.looked(s, 'MASON', rows['MASON']) and not RS.looked(s, 'STREET', rows['STREET']) and not RS.looked(s, 'T_LAY', rows['T_LAY'])
    assert RS.state(s, s['round']) == 'looking' and RS.then_of(s) == RS.SETS_LOOK
    store = store_of(s)
    assert [x['element_id'] for x in RS.looks_due(store, RUN, [])['sets']] == ['STREET', 'T_LAY']
    assert refused(lambda: VS.set_answer(store, USER, RUN, [], 'STREET', 'yes', golden='s-street-1')) == RS.SET_NO_LOOK.format(eid='STREET')
    rows['MASON']['answer']['set'] = 's-mason-0'                                    # an answer to an earlier set of the thing does not count
    assert not RS.looked(s, 'MASON', rows['MASON'])
    done_ = F.session('complete')
    for r in done_['references'].values():
        if r.get('kind') == 'sheet' and r.get('look'):
            r['look'].pop('lines', None)
    assert RS.state(done_, done_['round']) == 'complete' and RS.looks_due(store_of(done_), RUN, [])['sets'] == []     # approved sets: nothing is asked again


def test_no_set_reaches_the_operator_on_a_look_without_its_line_answers(monkeypatch):
    film_ = Film(monkeypatch, '2')
    film_.change(lambda s: [r['look'].pop('lines') for r in s['references'].values() if r.get('set') == 's-street-1'])
    street, mason = film_.lines()['set:STREET'], film_.lines()['set:MASON']
    assert (street['case'], street['head']) == ('wait', 'Claude is looking at it.') and 'check' not in street and not street.get('pics') and mason['case'] == 'judge' and mason['pics']


# ---------- the edge cases ----------

def test_a_set_with_fewer_than_three_pictures_and_a_place_of_one_are_answered_as_they_came():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store, pictures=2)
    due = {x['element_id']: x for x in RS.looks_due(store, RUN, [])['sets']}
    assert [len(due[e]['pictures']) for e in ('MASON', 'STREET', 'T_LAY')] == [2, 2, 2] and all(p['lines'] for e in due for p in due[e]['pictures'])
    assert look(store)['recorded'] == ['MASON', 'STREET', 'T_LAY'] and state(store) == 2
    s = saved(store)
    assert all('lines' in r['look'] for r in s['references'].values() if r.get('kind') == 'sheet' and r.get('status') == 'candidate')
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store, pictures=1)                                                                          # one picture each, as a place of today's round has
    due = RS.looks_due(store, RUN, [])['sets']
    assert all(len(x['pictures']) == 1 and IC.SAME_THING not in [l['check'] for l in x['pictures'][0]['lines']] for x in due)
    assert look(store)['recorded'] == ['MASON', 'STREET', 'T_LAY'] and state(store) == 2


def many(monkeypatch, facts=14):
    """The fixture's film with TILE's set made from its approved drawing, which holds `facts` facts; and the sets of BRICK and FAN made too: six sets back at once."""
    s = ready('looking')
    s['drawings']['TILE']['facts'] = [{'what': f'part {n} of the tile, measured along its longer side from lug to lug', 'value': 100 + n, 'unit': 'mm', 'source': 'the client'} for n in range(1, facts + 1)]
    plan = F.plan()
    rows, rd = s['round']['elements'], s['round']
    rows['FAN'].update(verdict='approve', ignored=False)
    for eid in ('BRICK', 'TILE', 'FAN'):
        req = RS.set_request(plan, RUN, s, el(eid, plan), rows[eid])
        monkeypatch.setitem(F.VIEWS, eid, [v['name'] for v in req['views']])
        sid, new = F._set(eid, el(eid, plan)['kind'], checks=False, looks=False)
        for n, r in enumerate(new.values()):
            r.update(server_checklist=req['lines'], ask=req['views'][n]['ask'])
        s['references'].update(new)
        rows[eid].update(set=sid, round=1, made={'at': F.NOW, 'specs': {}, 'photo': None, 'fp': 'fp'}, parts=req['parts'])
    rd.update(rest=[], go=2)
    return s, plan


def test_a_thing_with_fourteen_drawn_facts_stays_within_the_limits_of_the_look_file_and_of_the_page(monkeypatch):
    s, plan = many(monkeypatch)
    store = store_of(s, plan)
    out = RS.looks_due(store, RUN, [])
    tile = next(x for x in out['sets'] if x['element_id'] == 'TILE')
    drawn = [[l for l in p['lines'] if l.get('say')] for p in tile['pictures']]
    assert [len(d) for d in drawn] == [14, 14, 14] and all(l['check'].startswith('drawn fact: part ') and 'as the approved drawings do' in l['pass_when'] for d in drawn for l in d)
    assert any(i['role'] == 'drawing' for i in tile['inputs'])                                      # the drawing sheet comes with the set: a drawn fact is checked against it
    row = lambda x, lines: {'element_id': x['element_id'], 'set': x['set'], 'recommend': 'remake', 'golden': None, 'reason': 'r' * 300, 'chose': 'c' * 300, 'aside': 'a' * 300,
                            'pictures': [{'ref': p['ref'], 'view': p['view'], 'verdict': 'fail', 'seen': 's' * 300, 'lines': lines(p)} for p in x['pictures']]}
    worst = lambda p: [{'id': l['id'], 'pass': False, 'seen': 'w' * 300} for l in p['lines']]
    # the worst look file of a helper's group: five sets as large as this one, every line failed with the longest sentence. The route sets no size of its own
    # (80 sets a file); the measure here is the size the server allows a body it keeps in the database
    body = json.dumps({'by': 'helper', 'sets': [row(tile, worst)] * 5, 'request_id': 'x' * 36}).encode('utf-8')
    assert len(body) < Settings.model_fields['MAX_BODY_BYTES'].default, len(body)
    quiet = lambda p: [{**a, 'seen': ''} if not next(l for l in p['lines'] if l['id'] == a['id']).get('say') else a for a in ALL(p)]
    sent = row(tile, quiet)
    sent['pictures'][0]['lines'] = [{**a, 'seen': ''} for a in sent['pictures'][0]['lines']]         # a pass of a drawn fact with no words
    said = RS.round_looks(store, USER, RUN, [], [sent], 'helper')['refused']['TILE']
    first = drawn[0][0]
    assert said == RS.LOOK_LINE_WORDS.format(eid='TILE', pic=tile['pictures'][0]['view'], check=first['check'], id=first['id'], max=300) and 'a pass of a fact of the drawing' in said
    everything = [row(x, worst) for x in out['sets']]
    assert RS.round_looks(store, USER, RUN, [], everything, 'helper')['recorded'] == [x['element_id'] for x in out['sets']]
    after = saved(store)
    assert len(RS.check_summary(after, tile['pictures'][0]['ref'])['failed']) == len(tile['pictures'][0]['lines'])
    page = Film(monkeypatch, state='2', session=after, plan=plan).page()                            # the page's round: one document of its database
    assert len(json.dumps(page['lines'], ensure_ascii=False).encode('utf-8')) <= P.ROUND_BYTES
    line = next(l for l in page['lines'] if l['key'] == 'set:TILE')
    assert line['check']['state'] == 'fail' and len(line['check']['lines']) == sum(len(p['lines']) for p in tile['pictures']) and line['check']['lines'][0] == 'Picture A: ' + 'w' * 300


def test_more_than_five_sets_are_answered_by_groups_each_with_its_own_lists(monkeypatch):
    s, plan = many(monkeypatch, facts=2)
    store = store_of(s, plan)
    out = RS.looks_due(store, RUN, [])
    assert len(out['sets']) == 6 and 'With more than 5 sets start `vw-set-look` helpers' in out['then'] and all(p['lines'] for x in out['sets'] for p in x['pictures'])
    row = lambda x: {'element_id': x['element_id'], 'set': x['set'], 'recommend': 'doubt', 'golden': None, 'reason': 'Looked.', 'chose': 'One variant.', 'aside': 'Nothing.',
                     'pictures': [{'ref': p['ref'], 'view': p['view'], 'verdict': 'pass', 'seen': 'As asked.', 'lines': ALL(p)} for p in x['pictures']]}
    one = RS.round_looks(store, USER, RUN, [], [row(x) for x in out['sets'][:3]], 'helper')          # one helper's group
    assert len(one['recorded']) == 3 and len(one['left']) == 3 and one['then'] == RS.SETS_LOOK
    two = RS.round_looks(store, USER, RUN, [], [row(x) for x in out['sets'][3:]], 'helper')
    assert len(two['recorded']) == 3 and two['left'] == [] and RS.state(saved(store), saved(store)['round']) == 2


def test_an_answer_to_a_set_made_again_or_not_due_is_refused_and_a_changed_list_is_refused_by_name():
    store, conn = at_two()
    s = saved(store)
    old_set = s['round']['elements']['T_LAY']['set']
    stale = {'element_id': 'T_LAY', 'set': old_set, 'recommend': 'use', 'golden': old_set, 'reason': 'Fine.', 'chose': 'c', 'aside': 'a',
             'pictures': [{'ref': r['id'], 'view': r['view'], 'verdict': 'pass', 'seen': 'ok', 'lines': [{'id': l['id'], 'pass': True, 'seen': ''} for l in RS.check_lines(r)]}
                          for r in s['references'].values() if r.get('set') == old_set]}
    judge(store, conn, {'T_LAY': {'verdict': 'no'}, 'STREET': {'verdict': 'yes', 'golden': s['round']['elements']['STREET']['set']}})
    VS.guarded(lambda: RS.round_rewrite(conn, store, USER, RUN, [], [{'element_id': 'T_LAY', 'prompt': 'The right hand presses the wet brick into the mortar bed.'}]))
    back(store)
    now = saved(store)
    new_set = now['round']['elements']['T_LAY']['set']
    assert new_set != old_set and state(store) == 'looking'
    due = RS.looks_due(store, RUN, [])['sets']
    assert [x['element_id'] for x in due] == ['T_LAY'] and due[0]['set'] == new_set and all(p['lines'] for p in due[0]['pictures'])           # the new pictures get their list
    out = RS.round_looks(store, USER, RUN, [], [stale], 'helper')                                    # an answer to the old set's lines: stale
    assert out['refused'] == {'T_LAY': RS.LOOK_SET_UNKNOWN.format(eid='T_LAY', set=old_set)} and out['recorded'] == []
    street = now['round']['elements']['STREET']['set']                                               # a set already approved is not due
    out = RS.round_looks(store, USER, RUN, [], [{**stale, 'element_id': 'STREET', 'set': street}], 'helper')
    assert out['refused'] == {'STREET': RS.LOOK_SET_UNKNOWN.format(eid='STREET', set=street)}
    sent = looks(store)                                                                              # the list changes between the listing and the look
    for r in now['references'].values():
        if r.get('set') == new_set:
            r['server_checklist'] = [{**l, 'pass_when': l['pass_when'] + ', in daylight'} if l['check'] == 'matches the description' else l for l in r['server_checklist']]
    put(store, now)
    out = RS.round_looks(store, USER, RUN, [], sent, 'helper')
    gone = next(l['id'] for l in due[0]['pictures'][0]['lines'] if l['check'] == 'matches the description')
    assert out['refused'] == {'T_LAY': RS.LOOK_LINE_UNKNOWN.format(eid='T_LAY', pic=due[0]['pictures'][0]['view'], id=gone)} and '`vw visuals round --looks`' in out['refused']['T_LAY']
    after = saved(store)
    assert 'look' not in after['references'][new_set] and (after['round']['elements']['T_LAY'].get('set_look') or {}).get('set') != new_set and state(store) == 'looking'
    assert look(store)['recorded'] == ['T_LAY'] and state(store) in (2, 'complete')                # listed again and answered: recorded


# ---------- 6 and 7. the instructions, the helper, the versions ----------

def test_the_instructions_and_the_helper_say_that_the_look_checks_and_no_text_says_the_program_or_gemini_does():
    doc = json.loads((REPO / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    visuals = next(st for st in doc['stages'] if st['name'] == 'visuals')
    part = next(p['text'] for p in visuals['parts'] if p['name'] == 'picture-search')
    helper = (REPO / 'plugin' / 'agents' / 'vw-set-look.md').read_text(encoding='utf-8')
    command = (REPO / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for text in (part, helper):
        assert "the program's check" not in text and 'never from the request or the notes' in text and 'not_checked' in text
        assert 'against the drawing sheet' in text and 'never pass a line you did not look at' in text.lower()
    assert "your check, your look and your two lines on the image model's notes" in part and 'your check and your look' in part and 'your check judges by them' in part
    assert 'answer every line' in command
    retired = json.loads((REPO / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    for gone in ("the program's check, your look and your two lines", "and the result of the program's check", 'from their words, the check and your look'):
        assert gone in retired and gone not in part and gone not in helper
    split = (REPO / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert 'from d214_wording_v3 import apply as d214' in split and split.index('d213(prompt, parts)') < split.index('d214(prompt, parts)')


def test_the_versions_of_this_release():
    assert Settings.model_fields['SERVER_VERSION'].default == '0.113.0' and Settings.model_fields['PLUGIN_MIN_VERSION'].default == '0.97.0'   # design/216; design/215: 0.112.0 / 0.96.0
    assert json.loads((REPO / 'plugin' / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))['version'] == '0.97.0'
