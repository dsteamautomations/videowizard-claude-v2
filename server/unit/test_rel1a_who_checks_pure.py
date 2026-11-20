"""Release 1, section A (SK, 20 Nov 2026), rows A1, A2, A6: Claude's look is the only picture check of steps 6 and 7, and the words name who checked.

A1: on a film whose reference round is of the new kind no picture of steps 6 and 7 goes to the model check: a start or end picture that
belongs to a still shot is checked by Claude's look against the still's own list (every keyframe carries the role `start` or `end`, so until
this release every still went to the model); step 7's still (the start picture of an AI video shot) is checked by Claude's look against a
list of its own, and its card waits for the look as a picture of step 6 does. A picture the model checked before this release keeps that
result. A2: such a picture's heading, its small line and its question name the model; one picture never shows two names. A6: a failed line
is a warning the operator may approve against. Without a database."""
import copy
import json
from datetime import timedelta

import pytest

from app import chat_flow as CF, image_check as IC, pictures as P, takes as T, visual_workers as VW, visuals_stage as V
from test_design217_server_pure import NOW, RUN, USER, all_pass, held, plan, ref, session, shot   # noqa: F401 (held: the fixture)
from test_design222_takes_pure import guide
from test_design222_takes_pure import plan as take_plan, session as take_session, shot as take_shot

WORD = [{'check': 'word', 'pass_when': 'the word reads', 'weight': 'must'}]
MODEL = {'model': 'gemini-3.8-flash', 'code': [], 'must_failed': [], 'lines': [{'check': 'the people', 'weight': 'must', 'pass': False, 'seen': 'three workers'},
                                                                              {'check': 'the place', 'weight': 'must', 'pass': True, 'seen': 'a tiled roof'}]}


# ---------- A1: which pictures Claude checks ----------

def test_a_start_or_end_picture_of_a_still_shot_and_every_other_keyframe_of_a_v2_film_is_claudes():
    s, p = session(), plan(shot('S1'), shot('V1', 'video'))
    for more in ({'role': 'start'}, {'role': 'end'}, {'role': 'start', 'pending_end': {'prompt': 'Image 1 is the start.'}}, {}):
        assert P.claude_checks(s, ref('x', **more), p), more
    assert P.claude_checks(s, ref('x', 'keyframe', 'V1', role='start'), p)                 # no picture of step 6 or 7 is left to the model
    assert all(P.claude_checks(s, ref('x', k), p) for k in ('state', 'style', 'component'))
    assert not P.claude_checks(s, ref('x', 'sheet', set='x'), p) and not P.claude_checks(s, ref('x', 'frame'), p)   # a set has its own look (design/214); footage is untouched
    assert not P.claude_checks(session(v=1), ref('x', role='start'), p)                    # a film of the older round keeps the check of before


def test_the_worker_calls_no_model_for_a_start_picture_and_it_waits_for_claudes_look(monkeypatch):
    s = session(ref('r1', status='generating', sha=None, job_id='j1', role='start', server_checklist=WORD))
    s['references']['r1'].pop('check')
    store = {'run-1/visuals/session.json': json.dumps(s).encode()}

    class Store:
        get = staticmethod(lambda k: store[k])
        put = staticmethod(lambda k, data, t: store.__setitem__(k, data))
    monkeypatch.setattr(VW, 'storage', lambda: Store)
    monkeypatch.setattr(VW.jobs, 'finish', lambda *a, **k: None)
    monkeypatch.setattr(VW.jobs, 'record_file', lambda *a, **k: None)
    monkeypatch.setattr(IC, 'run_check', lambda *a, **k: pytest.fail('a model was called'))
    monkeypatch.setattr(IC, '_model_check', lambda *a, **k: pytest.fail('a model was called'))
    monkeypatch.setattr(V, 'current_plan', lambda *a, **k: plan(shot('S1')))

    class Lock:
        execute = staticmethod(lambda *a, **k: None)
    job = {'id': 'j1', 'run_id': 'run-1', 'request': {'reference': {'id': 'r1'}}}
    result = {'key': 'run-1/visuals/references/r1.png', 'sha256': 'b' * 64, 'bytes': 9, 'width': 2752, 'height': 1536}
    assert VW.finalize_image(Lock(), job, 'retained', result, None, {}, None)
    r = json.loads(store['run-1/visuals/session.json'])['references']['r1']
    assert 'check_pending' not in r and r['ready_at'] and 'model' not in r['check'] and [c['check'] for c in r['check']['code']] == ['size']
    monkeypatch.setattr(VW, '_measure', lambda *a: 'measured')
    assert VW.check_image(job, result) == 'measured'                                       # the program's measurements only, as advice


def test_its_list_is_the_stills_own_list_and_it_is_due_listed_and_recorded_like_any_still(held):
    start = ref('k1', role='start', server_checklist=WORD, pending_end={'prompt': 'Image 1 is the start.'})
    plain = ref('k1', server_checklist=WORD)
    box = held(session(start), plan(shot('S1')))
    checks = lambda r: [(l['check'], l['pass_when']) for l in P.lines(box['s'], box['p'], r)]
    assert checks(start) == checks(plain) and 'word' in [c for c, _ in checks(start)]
    out = P.looks_due(None, RUN, [])
    assert [x['ref'] for x in out['pictures']] == ['k1'] and out['pictures'][0]['kind'] == 'keyframe'
    assert not P.offered(box['s'], box['s']['references']['k1'], box['p'], NOW)             # not shown before its look
    done = P.record_looks(None, USER, RUN, [], [{'ref': 'k1', 'sha10': 'a' * 10, 'lines': all_pass(out['pictures'][0]['lines'])}], 'helper')
    assert done['recorded'] == ['k1'] and P.offered(box['s'], box['s']['references']['k1'], box['p'], NOW)
    v = P.check_view(box['s'], box['s']['references']['k1'], box['p'], NOW)
    assert v['head'] == "Claude's check found nothing wrong" and v['by'].startswith('Claude looked at the picture')


# ---------- a picture the model checked before this release; A2: who is named ----------

def test_a_picture_gemini_checked_before_this_release_keeps_that_result_and_is_named_as_geminis(held):
    old = ref('k1', role='start', check=copy.deepcopy(MODEL))
    box = held(session(old), plan(shot('S1')))
    s, p = box['s'], box['p']
    assert P.older(old) and P.offered(s, old, p, NOW) and P.due(s, p) == [] and P.looks_due(None, RUN, [])['pictures'] == []   # never given to Claude, never held
    v = P.check_view(s, old, p, NOW)
    assert v['state'] == 'fail' and v['head'] == 'An earlier check by Gemini 3.8 Flash found 1 problem: the people: three workers.'
    assert v['by'] == 'Gemini 3.8 Flash read the picture against its list of 2 lines.' and v['faults'] == ['the people: three workers.']
    line = P.picture_line(None, s, p, old, now=NOW)
    yes = line['buttons'][0]
    assert 'sure' not in yes and yes['against'] is True                                    # release 1, B1: one click; no second question
    assert yes['needs_words'] is False and yes['act'] == 'approve'                         # A6: a failed line is a warning: the operator may approve against it
    said = json.dumps([line['check'], yes]) + P.chat_text(line)
    assert 'Claude' not in said and said.count('Gemini 3.8 Flash') >= 3                      # one picture never shows two names, on the page or in the chat
    old['check']['lines'][0]['pass'] = True
    assert P.check_view(s, old, p, NOW)['head'] == 'An earlier check by Gemini 3.8 Flash found nothing wrong'


def test_a_picture_claude_checked_names_claude_in_the_heading_the_small_line_and_the_question(held):
    r = ref('k1', role='start', look={'who': 'helper', 'at': NOW.isoformat(), 'sha256': 'a' * 64, 'lines': [{'id': 'x', 'check': 'the people', 'pass': False, 'seen': 'three workers'}]})
    box = held(session(r), plan(shot('S1')))
    line = P.picture_line(None, box['s'], box['p'], r, now=NOW)
    said = json.dumps([line['check'], line['buttons'][0]])
    assert line['check']['head'].startswith("Claude's check found 1 problem") and line['check']['by'].startswith('Claude looked') and 'Gemini' not in said   # release 1, B1: the question (the second box) is retired


def test_the_steps_of_a_graphic_checked_by_the_model_before_name_the_model_and_a_mixed_graphic_names_neither_alone(held):
    g1, g2 = ref('g1', 'state', 'G1', check=copy.deepcopy(MODEL)), ref('g2', 'state', 'G1', sha='b' * 64, check=copy.deepcopy(MODEL), generation={'prompt': 'p', 'parents': [{'id': 'g1'}]})
    box = held(session(g1, g2), plan(shot('G1', 'graphic_sequence', states=2)))
    line = P.steps_line(None, box['s'], box['p'], 'G1', [g1, g2], now=NOW)
    assert line['check']['head'].startswith('An earlier check by Gemini 3.8 Flash found 2 problems: step 1: the people')
    assert 'sure' not in line['buttons'][0] and line['check']['short'] == '2 warnings: step 1, the people'   # release 1, B1, B3
    assert 'Claude' not in json.dumps([line['check'], line['buttons'][0], [x.get('check_head') for x in line['pics']]]) and 'Gemini 3.8 Flash' in line['check']['by']
    g2.pop('check')
    g2.update(ready_at=NOW.isoformat(), look={'who': 'helper', 'at': NOW.isoformat(), 'sha256': 'b' * 64, 'lines': [{'id': 'x', 'check': 'the place', 'pass': False, 'seen': 'a flat roof'}]})
    line = P.steps_line(None, box['s'], box['p'], 'G1', [g1, g2], now=NOW)
    assert line['check']['head'].startswith('The checks found 2 problems') and 'sure' not in line['buttons'][0]
    heads = [x.get('check_head') for x in line['pics'] if x.get('check_head')]
    assert heads == ["Gemini 3.8 Flash's check of step 1:", "Claude's check of step 2:"]     # each step names who checked it
    assert 'Step 1: Gemini 3.8 Flash read' in line['check']['by'] and 'Step 2: Claude looked' in line['check']['by']


# ---------- A1: step 7's still, the start picture of an AI video shot ----------

def seven(held_, monkeypatch, **still):
    s, p = take_session(), take_plan(take_shot('S1', title='Mason'))
    s['guides'].update(S1=guide(still='candidate', prompt=False))
    s['guides']['S1']['stills'][0].update(still)
    s['drawings'] = {}
    held_(s, p)
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run, sid=None: [])
    monkeypatch.setattr(P, '_big', lambda store, s_, rid: f'big/{rid}')
    return s, p, {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': USER, 'outputs': {}, 'conn': None}


def test_step_7s_still_is_listed_for_claudes_look_with_a_list_of_its_own_and_its_card_waits_for_the_look(held, monkeypatch):
    s, p, ctx = seven(held, monkeypatch)
    assert P.waits_words(s, p) == P.LOOKS_DUE.format(n=1)                                   # the duty is said
    out = P.looks_due(None, RUN, [], [])
    row = out['pictures'][0]
    assert (row['ref'], row['kind'], row['name'], row['shot_id'], row['sha10'], row['key']) == ('st1', 'start', 'Mason', 'S1', 's' * 10, 'run-1/still.png')
    assert [(i['role'], i['key']) for i in row['inputs']] == [('overlay', 'o.jpg'), ('layout', 'f1.png')]
    checks = [l['check'] for l in row['lines']]
    assert checks[0] == 'on the layout' and {'readable text', 'a real face', 'nothing extra'} <= set(checks) and len({l['id'] for l in row['lines']}) == len(checks)
    assert 'red outlines' in row['lines'][0]['pass_when'] and out['then'].startswith('Look at each picture against its lines')
    assert s['guides']['S1']['stills'][0]['asked_at']
    assert CF._guide_items(ctx) == [] and [(i['id'], i['state']) for i in T.expected(s, p, [], NOW)] == [('S1', 'being checked by Claude')]   # no card before the look
    bad = [{'id': l['id'], 'pass': l['check'] != 'on the layout', 'seen': ('As the parents show.' if l.get('say') else '') if l['check'] != 'on the layout' else 'The mason stands a step left of his outline.'} for l in row['lines']]
    assert P.record_looks(None, USER, RUN, [], [{'ref': 'st1', 'sha10': 'x' * 10, 'lines': bad}], 'helper')['refused']['st1'] == P.PIC_LOOK_GONE.format(name='Mason')
    done = P.record_looks(None, USER, RUN, [], [{'ref': 'st1', 'sha10': 's' * 10, 'lines': bad}], 'helper')
    assert done['recorded'] == ['st1'] and done['left'] == [] and s['guides']['S1']['stills'][0]['check_look']['who'] == 'helper'
    item = CF._guide_items(ctx)[0]
    assert item['kind'] == 'still' and item['text'] == '- 1 warning: on the layout\n- on the layout: The mason stands a step left of his outline.'   # release 1, B3: the short line, the warning in full
    assert [b['choice'] for b in item['buttons']] == ['approve', 'reject'] and not item['buttons'][0].get('needs_words')   # a warning: the operator may approve against it
    assert [(i['id'], i['state']) for i in T.expected(s, p, [], NOW)] == [('S1', 'waiting for you in the chat')] and P.looks_due(None, RUN, [], [])['pictures'] == []


def test_a_still_whose_look_never_comes_is_offered_after_thirty_minutes_as_not_checked(held, monkeypatch):
    s, p, ctx = seven(held, monkeypatch)
    P.looks_due(None, RUN, [], [])
    s['guides']['S1']['stills'][0]['asked_at'] = NOW.isoformat()                            # Claude was asked then
    monkeypatch.setattr(P, '_now', lambda: NOW + timedelta(minutes=31))
    item = CF._guide_items(ctx)[0]
    assert "Not checked: Claude's check did not come within 30 minutes. Judge it by eye." in item['text'] and len(P.starts_due(s, p)) == 1   # a look that still comes replaces it


def test_a_still_approved_before_this_release_is_not_checked_again_and_an_older_film_has_no_such_check(held, monkeypatch):
    s, p, ctx = seven(held, monkeypatch, status='approved')
    assert P.starts_due(s, p) == [] and P.looks_due(None, RUN, [], [])['pictures'] == []
    s2, p2, ctx2 = seven(held, monkeypatch)
    s2['round']['v'] = 1
    assert P.starts_due(s2, p2) == [] and [i['kind'] for i in CF._guide_items(ctx2)] == ['still']   # as before: the card at once, no look
