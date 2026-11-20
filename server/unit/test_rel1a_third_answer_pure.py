"""Release 1, section A (SK, 20 Nov 2026), rows A3, A4, A5: three answers per check line, everywhere Claude checks.

A line of a check list is answered Passed, Failed, or "does not apply here" (`"pass": "na"`) with one sentence saying why: in the look of a
picture of step 6 (`pictures`), of a set (`ref_sets`), of an AI video take (`takes`), and in the verdict on a drawn graphic's rules
(`visuals_stage.motion_verdict`, with `why`). Without its reason it is refused with the way to fix it. It is recorded once: not a problem, not
counted as passed, kept in the stored look, given to the page and the chat as a list of its own ("N lines did not apply"); a picture where every
line does not apply is "not checked, judge by eye", never "Passed". A look recorded before this release (true and false only) reads as before.
Without a database."""
import pytest

from app import chat_flow as CF, guide_worker as GW, pictures as P, ref_sets as RS, takes as T, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import motion_store, project
from test_design214_pure import RUN as SRUN, USER as SUSER, back, done, film, post, sent_for, state
from test_design214_pure import saved as set_saved
from test_design217_server_pure import NOW, RUN, USER, all_pass, held, plan, ref, session, shot   # noqa: F401 (held: the fixture)
from test_design221_p2_pure import EVEN, LEAVES, SOLID, upload, verdict
from test_design222_takes_pure import SHA, guide, job, rec
from test_design222_takes_pure import plan as take_plan, session as take_session, shot as take_shot
from test_visuals_stage_pure import g, saved

WHY = 'A close view of one object: the room is not in the frame.'


@pytest.fixture(autouse=True)
def round_of_today(monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', 2)   # conftest gives the older round to every module not named test_design211*


def listed(s, p):
    return P.looks_due(None, RUN, [])['pictures'][0]


def answers(row, **said):
    """Every line passed, but the lines named by their check in `said`: {check: (pass, seen)}."""
    return [{'id': l['id'], 'pass': said.get(l['check'], (True, ''))[0], 'seen': said.get(l['check'], (True, 'As shown.' if l.get('say') else ''))[1]} for l in row['lines']]


# ---------- a picture of step 6 ----------

def test_a_line_that_does_not_apply_needs_its_reason_and_is_recorded_once_neither_a_problem_nor_passed(held):
    s, p = session(ref('r1')), plan(shot('S1'))
    held(s, p)
    row = listed(s, p)
    send = lambda why: P.record_looks(None, USER, RUN, [], [{'ref': 'r1', 'sha10': 'a' * 10, 'lines': answers(row, wear=(VS.NA, why))}], 'helper')
    out = send('  ')
    assert out['recorded'] == [] and out['refused']['r1'] == P.PIC_LOOK_NA.format(name='The housing site', check='wear', id=next(l['id'] for l in row['lines'] if l['check'] == 'wear'), max=300)
    assert 'why' in out['refused']['r1'] and 'pass or fail' in out['refused']['r1'] and '--looks' in out['refused']['r1']   # the way to fix it
    assert not s['references']['r1'].get('look')
    out = send(WHY)
    assert out['recorded'] == ['r1'] and out['refused'] == {} and out['left'] == []                 # recorded once: nothing is asked again
    look = s['references']['r1']['look']
    assert [l for l in look['lines'] if l['check'] == 'wear'] == [{'id': next(l['id'] for l in row['lines'] if l['check'] == 'wear'), 'check': 'wear', 'pass': 'na', 'seen': WHY}]
    assert P.due(s, p) == [] and P.offered(s, s['references']['r1'], p, NOW)
    v = P.check_view(s, s['references']['r1'], p, NOW)
    assert v['state'] == 'pass' and v['head'] == P.W['pass'] and v['faults'] == []
    assert not [x for x in v['passed'] if x.startswith('wear')] and len(v['passed']) == len(row['lines']) - 1   # not counted as passed either
    assert v['na'] == {'head': '1 line did not apply', 'lines': [f'wear: {WHY}']}
    line = P.picture_line(None, s, p, s['references']['r1'], now=NOW)
    assert 'sure' not in line['buttons'][0] and '1 line did not apply' in P.chat_text(line)        # no "use it all the same?"; the chat says the list too


def test_a_failed_line_stays_a_problem_beside_lines_that_do_not_apply_and_the_count_leaves_them_out(held):
    s, p = session(ref('r1')), plan(shot('S1'))
    held(s, p)
    row = listed(s, p)
    P.record_looks(None, USER, RUN, [], [{'ref': 'r1', 'sha10': 'a' * 10, 'lines': answers(row, wear=(VS.NA, WHY), practitioner=(VS.NA, WHY), **{'nothing extra': (False, 'A second cart stands at the left.')})}], 'helper')
    v = P.check_view(s, s['references']['r1'], p, NOW)
    assert v['state'] == 'fail' and v['head'] == "Claude's check found 1 problem: nothing extra: A second cart stands at the left."
    assert v['na']['head'] == '2 lines did not apply' and len(v['na']['lines']) == 2


def test_a_picture_where_every_line_does_not_apply_is_not_checked_never_passed(held):
    s, p = session(ref('r1')), plan(shot('S1'))
    held(s, p)
    row = listed(s, p)
    P.record_looks(None, USER, RUN, [], [{'ref': 'r1', 'sha10': 'a' * 10, 'lines': [{'id': l['id'], 'pass': 'na', 'seen': WHY} for l in row['lines']]}], 'helper')
    v = P.check_view(s, s['references']['r1'], p, NOW)
    assert v['state'] == 'not_checked' and v['head'] == P.W['all_na'] == 'Not checked: every line of its list was answered "does not apply". Judge it by eye.'
    assert v['passed'] == [] and v['faults'] == [] and v['na']['head'] == f"{len(row['lines'])} lines did not apply"


def test_a_component_whose_every_line_does_not_apply_is_not_approved_by_the_check(held):
    s, p = session(ref('c1', 'component', None)), plan(shot('S1'))
    held(s, p)
    row = listed(s, p)
    P.record_looks(None, USER, RUN, [], [{'ref': 'c1', 'sha10': 'a' * 10, 'lines': [{'id': l['id'], 'pass': 'na', 'seen': WHY} for l in row['lines']]}], 'helper')
    assert s['references']['c1']['status'] == 'candidate' and 'every line' in ' '.join(P.components_failed(s, p))   # said, never silent, never approved unchecked


def test_a_step_says_its_lines_that_did_not_apply_under_its_number(held):
    s = session(ref('g1', 'state', 'G1'), ref('g2', 'state', 'G1', sha='b' * 64, generation={'prompt': 'p', 'parents': [{'id': 'g1'}]}))
    p = plan(shot('G1', 'graphic_sequence', states=2))
    held(s, p)
    for row in P.looks_due(None, RUN, [])['pictures']:
        P.record_looks(None, USER, RUN, [], [{'ref': row['ref'], 'sha10': row['sha10'], 'lines': answers(row, **({'nothing extra': (VS.NA, WHY)} if row['ref'] == 'g2' else {}))}], 'helper')
    v = P.steps_view(None, s, [s['references']['g1'], s['references']['g2']], p, NOW)
    assert v['state'] == 'pass' and v['na'] == {'head': '1 line did not apply', 'lines': [f'Step 2: nothing extra: {WHY}']}


def test_a_look_recorded_before_this_release_reads_as_before(held):
    r = ref('r1', look={'who': 'helper', 'at': NOW.isoformat(), 'sha256': 'a' * 64, 'lines': [{'id': 'x1', 'check': 'the people', 'pass': True, 'seen': ''},
                                                                                           {'id': 'x2', 'check': 'the place', 'pass': False, 'seen': 'A flat roof, not tiles.'}]})
    s, p = session(r), plan(shot('S1'))
    v = P.check_view(s, r, p, NOW)
    assert v['state'] == 'fail' and v['faults'] == ['the place: A flat roof, not tiles.'] and v['passed'] == ['the people: the people.'] and 'na' not in v


# ---------- an AI video take ----------

def take_film(held_):
    s, p = take_session(), take_plan(take_shot('S1'))
    s['guides'].update(S1=guide())
    s['take_checks'].update(j1=rec())
    held_(s, p)
    return s, p, [job('j1')]


def test_a_takes_line_that_does_not_apply_is_no_fault_no_pass_and_never_a_fail_on_the_scorecard(held):
    s, p, rows = take_film(held)
    want = T.look_lines()
    na = lambda why: [{'id': l['id'], 'pass': 'na' if l['check'] == 'people' else True, 'seen': why if l['check'] == 'people' else ''} for l in want]
    said = T.record(s, p, rows, {'ref': 'j1', 'sha10': SHA[:10], 'lines': na('')}, 'helper')
    assert said == P.PIC_LOOK_NA.format(name='Housing at work', check='people', id=want[0]['id'], max=300) and not s['take_checks']['j1'].get('look')
    assert T.record(s, p, rows, {'ref': 'j1', 'sha10': SHA[:10], 'lines': na('No person is in this shot.')}, 'helper') is None
    r = s['take_checks']['j1']
    assert r['look']['lines'][0]['pass'] == 'na' and [x['state'] for x in r['scorecard'] if x['line'] == 'people'] == ['Does not apply']
    assert not [x for x in r['scorecard'] if x['state'] in ('Fail', 'Not sure')] and r['not_read'] is False
    v = T.check_view(s, rows[0], NOW)
    assert v['state'] == 'pass' and v['head'] == 'Check passed' and v['faults'] == [] and len(v['passed']) == 8 and not [x for x in v['passed'] if x.startswith('People')]
    assert v['na'] == {'head': '1 line did not apply', 'lines': ['People: No person is in this shot.']}
    assert T.due(s, p, rows) == []                                                                     # recorded once


def test_a_take_whose_every_line_does_not_apply_is_not_checked_and_a_take_looked_at_before_reads_as_before(held):
    s, p, rows = take_film(held)
    assert T.record(s, p, rows, {'ref': 'j1', 'sha10': SHA[:10], 'lines': [{'id': l['id'], 'pass': 'na', 'seen': 'Nothing of it is in the frames.'} for l in T.look_lines()]}, 'helper') is None
    v = T.check_view(s, rows[0], NOW)
    assert v['state'] == 'not_checked' and v['head'] == T.W['all_na'] and 'Judge it by eye' in v['head'] and v['na']['head'] == '5 lines did not apply'
    from test_design222_takes_pure import look
    s['take_checks'].update(j1=rec(look=look(fail=('objects',))))                                      # the format of before: true and false only
    v = T.check_view(s, rows[0], NOW)
    assert v['state'] == 'fail' and len(v['faults']) == 1 and len(v['passed']) == 8 and 'na' not in v


def test_the_scorecard_of_before_is_unchanged():
    lines = [{'check': n, 'pass': True, 'seen': ''} for n in GW.SCORECARD[3:]]
    rows, _ = GW.scorecard([], {'lines': lines})
    assert [r['state'] for r in rows[2:]] == ['Pass'] * 5


# ---------- a picture of a reference set ----------

def sets():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    return store


def test_a_sets_line_that_does_not_apply_needs_its_reason_and_is_listed_apart():
    store = sets()
    sent, mine = sent_for(store)
    pic = mine['pictures'][1]
    pic['lines'][2].update({'pass': 'na', 'seen': ''})
    out = RS.round_looks(store, SUSER, SRUN, [], sent, 'helper')
    assert 'T_LAY' in out['refused'] and out['refused']['T_LAY'].startswith('T_LAY: the result just after: the line') and 'does not apply' in out['refused']['T_LAY'] and '--looks' in out['refused']['T_LAY']
    pic['lines'][2].update({'seen': WHY})
    out = RS.round_looks(store, SUSER, SRUN, [], sent, 'helper')
    assert out['refused'] == {} and state(store) == 2
    s = set_saved(store)
    stored = s['references'][pic['ref']]['look']['lines'][2]
    assert stored['pass'] == 'na' and stored['seen'] == WHY
    assert RS.check_summary(s, pic['ref']) == {'state': 'pass', 'failed': [], 'error': None, 'na': [{'check': stored['check'], 'seen': WHY}]}
    assert RS.check_summary(s, mine['pictures'][0]['ref']) == {'state': 'pass', 'failed': [], 'error': None}   # no such line: the shape of before


def test_a_set_picture_whose_every_line_does_not_apply_is_not_checked():
    store = sets()
    sent, mine = sent_for(store)
    pic = mine['pictures'][1]
    for l in pic['lines']:
        l.update({'pass': 'na', 'seen': WHY})
    assert RS.round_looks(store, SUSER, SRUN, [], sent, 'helper')['refused'] == {}
    out = RS.check_summary(set_saved(store), pic['ref'])
    assert out['state'] == 'none' and out['failed'] == [] and out['error'] == RS.ALL_NA and len(out['na']) == len(pic['lines'])


def test_the_sets_line_on_the_page_and_in_the_chat_lists_them_apart(monkeypatch):
    from test_design211c_kit_pure import Film
    film_ = Film(monkeypatch, '2')
    film_.change(lambda s: s['references']['s-mason-1']['look']['lines'][0].update({'pass': 'na', 'seen': WHY}))
    check = film_.lines()['set:MASON']['check']
    assert check['state'] == 'pass' and check['lines'] == [] and check['na']['head'] == '1 line did not apply' and check['na']['lines'][0].endswith(WHY)
    assert '1 line did not apply' in next(i for i in film_.items() if i['_key'] == 'set:MASON')['text']


# ---------- a drawn graphic's rules ----------

def na(rule, why=WHY):
    return {'rule': rule, 'pass': 'na', **({'why': why} if why else {})}


def test_a_rule_that_does_not_apply_needs_its_reason_and_is_a_note_never_a_failed_must():
    store = motion_store()
    sha = upload(store)
    with pytest.raises(Problem) as e:
        g(lambda: verdict(store, sha, {EVEN: True, LEAVES: True}, extra=[na(SOLID, '')]))
    assert str(e.value) == VS.MOTION_RULE_NA.format(shot='MO1', rule=SOLID) and '`why`' in str(e.value) and 'pass or fail' in str(e.value)
    assert not saved(store).get('motion_checks')
    out = verdict(store, sha, {EVEN: True, LEAVES: True}, extra=[na(SOLID)])
    assert out['failed'] == [] and out['not_seen'] == [] and out['na'] == [{'rule': SOLID, 'why': WHY}] and out['next'].startswith('Passed, 0 notes')   # a must: a note, the drawing is not held
    assert '1 did not apply' in out['log']                                                         # kept in the run's log
    rec_ = saved(store)['motion_checks']['MO1'][-1]
    assert [(r['pass'], r.get('why')) for r in rec_['rules'] if r['rule'] == SOLID] == [('na', WHY)] and VS.open_rules(rec_) == [] and VS.held_rules(rec_) == []
    assert saved(store)['motion_bound']['MO1'] == sha


def test_it_is_recorded_once_no_frame_is_asked_for_it_and_a_later_round_does_not_ask_it_again():
    store = motion_store()
    sha = upload(store)
    first = verdict(store, sha, {EVEN: True, LEAVES: False}, extra=[na(SOLID)])
    assert first['failed'] == [LEAVES] and 'not seen' not in first['next'] and 'snapshot' not in first['next']
    sha2 = upload(store, project(**{'style.css': 'body { margin: 0; }'}))
    assert SOLID not in ' '.join(VS.round_rules(saved(store), 'MO1', sha2) or [])                    # the round's list does not ask it again
    out = verdict(store, sha2, {LEAVES: True}, rnd=2)                                                # left out: it keeps its answer, as a rule that passed does
    rec_ = saved(store)['motion_checks']['MO1'][-1]
    assert out['failed'] == [] and [(r['pass'], r.get('carried')) for r in rec_['rules'] if r['rule'] == SOLID] == [('na', True)] and out['na'] == [{'rule': SOLID, 'why': WHY}]


def test_a_rule_judged_in_an_earlier_round_is_not_cleared_by_does_not_apply():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {SOLID: False, EVEN: True, LEAVES: True})
    sha2 = upload(store, project(**{'style.css': 'body { margin: 0; }'}))
    with pytest.raises(Problem) as e:
        g(lambda: verdict(store, sha2, {}, rnd=2, extra=[na(SOLID)]))
    assert str(e.value) == VS.MOTION_RULE_NA_JUDGED.format(shot='MO1', rule=SOLID, was='failed') and 'pass or fail' in str(e.value)
    assert len(saved(store)['motion_checks']['MO1']) == 1                                           # nothing recorded


def test_the_page_lists_the_rules_that_did_not_apply_apart_and_does_not_count_them_as_held():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {EVEN: True, LEAVES: True}, extra=[na(SOLID)])
    orig, VS.load_json = VS.load_json, (lambda store_, k: {'sha256': sha})
    try:
        v = P.fact_view(saved(store), store, {'unit': 'MO1', 'request': {'request_key': 'k'}}, 'MO1')
    finally:
        VS.load_json = orig
    assert v['state'] == 'pass' and v['head'] == 'Fact check: passed. All 2 rules held, after 0 redo rounds.' and v['faults'] == []
    assert v['na'] == {'head': '1 line did not apply', 'lines': [f"{SOLID.rstrip('.')}: {WHY}"]} and len(v['passed']) == 2


def test_a_drawing_whose_every_rule_does_not_apply_is_not_fact_checked():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {}, extra=[na(SOLID), na(EVEN), na(LEAVES)])
    orig, VS.load_json = VS.load_json, (lambda store_, k: {'sha256': sha})
    try:
        v = P.fact_view(saved(store), store, {'unit': 'MO1', 'request': {'request_key': 'k'}}, 'MO1')
    finally:
        VS.load_json = orig
    assert v['state'] == 'not_checked' and v['head'] == P.W['all_na_rules'] and 'Judge it by eye' in v['head'] and v['na']['head'] == '3 lines did not apply'


# ---------- the guard, where the checker reads it (A4): the server cannot see the picture ----------

def test_the_served_look_instructions_say_the_third_answer_and_its_guard_with_two_neutral_examples():
    for how in (' '.join(P.LOOK_HOW['judge']), ' '.join(P.TAKE_LOOK_HOW['judge']), ' '.join(RS.LOOK_HOW['judge'])):
        assert VS.NA_HOW in how
    assert '"pass": "na"' in VS.NA_HOW and 'only when this view cannot show' in VS.NA_HOW and 'or the line is about another thing' in VS.NA_HOW and 'Never for something that is in view' in VS.NA_HOW
    assert VS.NA_HOW.count(';') >= 1 and 'for example' in VS.NA_HOW                                 # two examples
    for word in ('brick', 'ceiling', 'kiln', 'mason', 'tumbler', 'documentary'):                    # generic: every category of video
        assert word not in VS.NA_HOW.lower()
    assert 'na' in str(P.LOOK_HOW['file']) and 'na' in str(RS.LOOK_HOW['file']) and '"na"' in P.TAKE_LOOK_HOW['file']
    assert 'true, false or "na"' in P.PIC_LOOK_OPEN and 'true, false or "na"' in RS.LOOK_LINE_OPEN
    assert CF.WORDS   # the chat's words module loads with these
