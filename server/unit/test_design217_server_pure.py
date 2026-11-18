"""design/217 (SK, 18 Nov 2026): step 6 "Pictures and drawn graphics" on the page, and Claude's check of its pictures (server side).

Built from the approved release (design/_work/step6-release-requirements-18-nov.md: C1-C7, F1-F6, R1-R4, D1-D8) and the contract with its
fixture (design/217-contract.md, server/unit/d217_pictures_round.json). Without a database: the session is held in memory."""
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app import chat_flow as CF, image_check as IC, library as L, page_flow as PF, pictures as P, visual_workers as VW, visuals_stage as V

HERE = Path(__file__).resolve().parent
FIXTURE = json.loads((HERE / 'd217_pictures_round.json').read_text(encoding='utf-8'))
RUN, USER = {'id': 'run-1', 'code': 'VW-99'}, {'id': 'u1', 'name': 'Op'}
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


def shot(sid, kind='still', states=0, title='The housing site'):
    return {'id': sid, 'title': title, 'visual_type': kind, 'narration': 'Across the state, housing schemes use the bond.', 'start_frame': 3260, 'end_frame': 3375,
            **({'states': [{'what_appears': f'part {n}', 'hold_s': 1.0, 'words': f'words {n}'} for n in range(1, states + 1)]} if states else {}),
            'subjects': [{'element_id': 'WORKER', 'role': 'background'}]}


def plan(*shots):
    return {'foundation': {'graphic_style': {'palette': 'cream, terracotta, charcoal'}}, 'elements': [{'id': 'WORKER', 'kind': 'person', 'name': 'Kiln worker'}],
            'gaps': [{'gap_id': '8', 'title': 'Homes that last', 'scenes': [{'id': 'sc1', 'shots': list(shots)}]}]}


def ref(rid, kind='keyframe', shot_id='S1', status='candidate', sha='a' * 64, **more):
    return {'id': rid, 'kind': kind, 'shot_id': shot_id, 'status': status, 'sha256': sha, 'key': f'run-1/visuals/references/{rid}.png', 'element_id': 'WORKER', 'element_kind': 'person',
            'name': rid, 'generation': {'prompt': 'A still of the housing site.', 'parents': []}, 'width': 2752, 'height': 1536,
            'check': {'code': [{'check': 'size', 'pass_when': 'the picture is 16:9', 'weight': 'must', 'pass': True, 'seen': '2752x1536'}]}, **more}


def session(*refs, v=2):
    return {'round': {'v': v, 'kept': True, 'pass': 'complete', 'elements': {}}, 'references': {r['id']: r for r in refs}, 'accepted': {}, 'choice_selections': {},
            'source': {'fps': 25}, 'questions': {}, 'reviews': {}, 'selections': {}, 'current': 'p1'}


@pytest.fixture
def held(monkeypatch):
    """A session and a plan held in memory for the server functions."""
    box = {}

    def use(s, p):
        box.update(s=s, p=p)
        monkeypatch.setattr(V, 'session_of', lambda *a, **k: box['s'])
        monkeypatch.setattr(V, 'save_session', lambda store, run, s_: box.update(s=s_))
        monkeypatch.setattr(V, 'current_plan', lambda *a, **k: box['p'])
        monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
        monkeypatch.setattr(P, '_big', lambda store, s_, rid: f'big/{rid}')
        return box
    return use


def all_pass(listed, say='As the picture shows.'):
    return [{'id': l['id'], 'pass': True, 'seen': say if l.get('say') else ''} for l in listed]


# ---------- C1: which pictures Claude checks; the worker calls no model ----------

def test_c1_a_still_a_step_the_style_sheet_and_a_component_of_a_v2_film_are_claudes_and_nothing_else_is():
    s, p = session(), plan(shot('S1'), shot('V1', 'video'))
    assert all(P.claude_checks(s, ref('x', k), p) for k in ('keyframe', 'state', 'style', 'component'))
    assert not P.claude_checks(s, ref('x', 'keyframe', 'V1'), p)                         # an AI video's start image: step 7, untouched (C7)
    assert not P.claude_checks(s, ref('x', 'keyframe', role='start'), p)
    assert not P.claude_checks(s, ref('x', 'sheet', set='x'), p) and not P.claude_checks(s, ref('x', 'frame'), p)   # sets (design/214) and footage
    assert not P.claude_checks(session(v=1), ref('x'), p)                                  # an older film keeps the check of before


def test_c1_finalize_image_stores_the_code_checks_and_ready_at_and_no_model_ever_runs(monkeypatch):
    s = session(ref('r1', status='generating', sha=None, job_id='j1', server_checklist=[{'check': 'word', 'pass_when': 'the word reads', 'weight': 'must'}]))
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
    due = VW.finalize_image(Lock(), job, 'retained', result, None, {}, None)
    r = json.loads(store['run-1/visuals/session.json'])['references']['r1']
    assert due and 'check_pending' not in r and r['ready_at'] and [c['check'] for c in r['check']['code']] == ['size']
    monkeypatch.setattr(VW, '_measure', lambda *a: 'measured')
    assert VW.check_image(job, result) == 'measured'                                       # the program's measurements only (C4)


# ---------- the list per kind (contract 5.3) ----------

def test_lines_per_kind_style_step_still_figures_and_a_remade_picture():
    st1 = ref('st1', 'state', 'G1')
    st2 = ref('st2', 'state', 'G1', generation={'prompt': 'p', 'parents': [{'id': 'st1'}]})
    old = ref('old', status='approved', shot_id='S0')
    still = ref('k1', 'keyframe', 'S1')
    fix = ref('k2', 'keyframe', 'S1', fix_of='k1', fix_for='word')
    k1 = {**still, 'server_checklist': [{'check': 'word', 'pass_when': 'the word reads', 'weight': 'must'}]}
    s = session(st1, st2, {**old, 'shot_id': 'S1b'}, k1, fix, ref('sty', 'style', None, element_id='_STYLE', element_kind='style'))
    p = plan(shot('S1'), shot('S1b'), shot('G1', 'animation', states=2, title='Fewer bricks'))
    sty = [l['check'] for l in P.lines(s, p, s['references']['sty'])]
    assert {'the palette', 'sample labels readable', 'no scene', 'readable text'} <= set(sty) and 'wear' not in sty   # the style sheet gets a list too (F5)
    assert 'step 2 adds its part' in [l['check'] for l in P.lines(s, p, st2)] and 'step 1 adds its part' not in [l['check'] for l in P.lines(s, p, st1)]
    assert 'no background figure repeated' in [l['check'] for l in P.lines(s, p, k1)]       # C5: the second call's question, before the answer
    remade = [l['check'] for l in P.lines(s, p, fix)]
    assert {'word', 'the line it was made for', 'nothing else changed'} <= set(remade)    # the original's whole list, never a smaller one
    a, b = P.lines(s, p, k1), P.lines(s, p, k1)
    assert [l['id'] for l in a] == [l['id'] for l in b] and len({l['id'] for l in a}) == len(a)
    assert 'light and colour' not in [l['check'] for l in a]                               # D2: the light is measured, not a line of Claude's


# ---------- C2: the looks, the refusals, not checked ----------

def test_c2_looks_due_lists_each_waiting_picture_with_its_lines_and_stamps_the_ones_the_model_held(held):
    box = held(session(ref('k1', check_pending=True), ref('k2', 'keyframe', 'S2', look={'sha256': 'a' * 64, 'lines': []})), plan(shot('S1'), shot('S2')))
    out = P.looks_due(None, RUN, [])
    assert [x['ref'] for x in out['pictures']] == ['k1'] and out['pictures'][0]['sha10'] == 'a' * 10 and out['pictures'][0]['lines'] and out['how'] == P.LOOK_HOW
    assert 'check_pending' not in box['s']['references']['k1'] and box['s']['references']['k1']['ready_at']   # given to Claude's check at the deploy


def test_c2_record_refuses_a_skipped_an_unknown_and_a_silent_fail_and_records_the_others(held):
    box = held(session(ref('k1'), ref('k2', shot_id='S2'), ref('k3', shot_id='S3'), ref('k4', shot_id='S4'), ref('k5', shot_id='S5')),
               plan(*(shot(f'S{n}', title=f'Shot {n}') for n in range(1, 6))))
    lines = lambda rid: P.lines(box['s'], box['p'], box['s']['references'][rid])
    sent = [{'ref': 'k1', 'sha10': 'a' * 10, 'lines': all_pass(lines('k1'))[1:]},
            {'ref': 'k2', 'sha10': 'a' * 10, 'lines': all_pass(lines('k2')) + [{'id': 'zzzzzzzz', 'pass': True}]},
            {'ref': 'k3', 'sha10': 'a' * 10, 'lines': [{**l, 'pass': False} if n == 0 else l for n, l in enumerate(all_pass(lines('k3')))]},
            {'ref': 'k4', 'sha10': 'a' * 10, 'lines': [{**l, 'pass': False, 'seen': 'Three workers, not two.'} if n == 0 else l for n, l in enumerate(all_pass(lines('k4')))]},
            {'ref': 'k5', 'sha10': 'b' * 10, 'lines': all_pass(lines('k5'))}]
    out = P.record_looks(None, USER, RUN, [], sent, 'helper')
    assert out['recorded'] == ['k4']
    assert out['refused']['k1'].startswith('Shot 1: the line') and 'has no answer' in out['refused']['k1']
    assert 'zzzzzzzz is not a line of this picture now' in out['refused']['k2']
    assert 'needs one plain sentence' in out['refused']['k3']
    assert out['refused']['k5'] == P.PIC_LOOK_GONE.format(name='Shot 5')               # its content changed: nothing recorded
    look = box['s']['references']['k4']['look']
    assert look['who'] == 'helper' and look['sha256'] == 'a' * 64 and look['lines'][0]['pass'] is False and set(out['left']) == {'k1', 'k2', 'k3', 'k5'}
    assert not any('look' in box['s']['references'][r] for r in ('k1', 'k2', 'k3', 'k5'))   # a helper that stops half-way: the rest stay due, never passed


def test_c2_not_checked_only_without_lines_and_it_reads_not_checked(held):
    box = held(session(ref('k1'), ref('k2', shot_id='S2')), plan(shot('S1'), shot('S2')))
    l1 = P.lines(box['s'], box['p'], box['s']['references']['k1'])
    out = P.record_looks(None, USER, RUN, [], [{'ref': 'k1', 'sha10': 'a' * 10, 'not_checked': 'The file did not open.'},
                                                {'ref': 'k2', 'sha10': 'a' * 10, 'not_checked': 'x', 'lines': all_pass(l1)}], 'assistant')
    assert out['recorded'] == ['k1'] and '`not_checked` is only for a picture that could not be opened' in out['refused']['k2']
    v = P.check_view(box['s'], box['s']['references']['k1'], box['p'])
    assert v['state'] == 'not_checked' and v['head'] == 'Not checked: Claude could not open the picture. Judge it by eye.'


def test_d4_a_component_is_approved_by_a_clean_look_and_never_asked(held):
    box = held(session(ref('c1', 'component', None)), plan(shot('S1')))
    want = P.lines(box['s'], box['p'], box['s']['references']['c1'])
    P.record_looks(None, USER, RUN, [], [{'ref': 'c1', 'sha10': 'a' * 10, 'lines': all_pass(want)}], 'assistant')
    assert box['s']['references']['c1']['status'] == 'approved' and box['s']['references']['c1']['approval']['quote'] == P.COMPONENT_APPROVED


# ---------- C3, F6: offered only with the look, else after the time-out as not checked ----------

def test_c3_a_picture_waits_for_its_look_then_is_offered_after_the_time_out_as_not_checked():
    s, p = session(ref('k1', ready_at=(NOW - timedelta(hours=12)).isoformat())), plan(shot('S1'))
    r = s['references']['k1']
    assert not P.offered(s, r, p, NOW) and not P.late(r, NOW)                               # the critic's review (1): a film paused overnight: made long ago, never asked
    r['asked_at'] = NOW.isoformat()                                                         # the time-out counts from when Claude was first asked
    assert not P.offered(s, r, p, NOW + timedelta(minutes=29))
    assert P.offered(s, r, p, NOW + timedelta(minutes=P.PICTURE_LOOK_MINUTES))
    v = P.check_view(s, r, p, NOW + timedelta(minutes=31))
    assert v['state'] == 'not_checked' and v['head'] == "Not checked: Claude's check did not come within 30 minutes. Judge it by eye." == FIXTURE['lines'][7]['check']['head']
    r['look'] = {'sha256': 'a' * 64, 'lines': [{'id': 'x', 'check': 'the people', 'pass': False, 'seen': 'three distant workers are visible, not two'}]}
    assert P.offered(s, r, p, NOW)                                                          # a look that arrives later replaces "not checked"
    r['sha256'] = 'c' * 64
    assert not P.offered(s, r, p, NOW)                                                      # a look of another content is not its look
    assert P.offered(session(ref('k1', check_pending=True), v=1), ref('k9'), p)             # an older film: as before


def test_c3_waiting_lists_a_still_only_with_its_look(held, monkeypatch):
    s = session(ref('k1', ready_at=datetime.now(timezone.utc).isoformat(), asked_at=datetime.now(timezone.utc).isoformat()))
    p = plan(shot('S1'))
    held(s, p)
    monkeypatch.setattr(V, 'route_of', lambda sh: 'still')
    assert V.waiting(s, p, 'VW-99', []) == []
    s['references']['k1']['look'] = {'sha256': 'a' * 64, 'lines': []}
    assert [w['item'] for w in V.waiting(s, p, 'VW-99', [])] == ['k1']


# ---------- F1, D2: the check from the look and the program's lines ----------

def test_f1_the_check_is_claudes_look_with_the_program_lines_as_advice():
    r = ref('k1', look={'sha256': 'a' * 64, 'lines': [{'id': '1', 'check': 'the people', 'pass': False, 'seen': 'three distant workers are visible, not two'},
                                                       {'id': '2', 'check': 'readable text', 'pass': True, 'seen': 'none'}]},
            checklist=[{'check': 'never read'}])
    r['check']['code'].append({'check': 'light and colour', 'pass': False, 'seen': 'brighter by 0.26 than the footage beside it (6 frames)', 'advice': True})
    v = P.check_view(session(r), r, plan(shot('S1')))
    assert v['state'] == 'fail' and v['head'] == "Claude's check found 1 problem: the people: three distant workers are visible, not two."
    assert v['by'] == 'Claude looked at the picture against its list of 2 lines.' and v['passed'] == ['readable text: none.']
    assert v['advice'] == ["Size: 2752x1536, the film's shape.", 'Light and colour: brighter by 0.26 than the footage beside it (6 frames).']   # advice, not a fault (D2)
    item_text = P.chat_text({'check': v})
    assert v['head'] in item_text and 'never read' not in item_text                         # the chat says the same, never `ref.checklist`


# ---------- the lines of the step: words and shape as the fixture ----------

def _paged(line):
    out = dict(line)
    out['pics'] = [{**PF.pic(x['_key'], x['label'], x.get('_mark')), **{k: v for k, v in x.items() if k not in ('_key', 'label', '_mark')}} for x in line['pics']]
    for x in out['pics']:
        x.pop('_key', None), x.pop('_mark', None)
    if 'video' in out:
        out['video'] = {k: v for k, v in out['video'].items() if not k.startswith('_')}
    return out


def fixture_line(kind):
    return next(l for l in FIXTURE['lines'] if l['kind'] == kind)


def test_a_still_line_has_the_fixture_fields_words_and_buttons(monkeypatch):
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    r = ref('k1', look={'sha256': 'a' * 64, 'lines': [{'id': '1', 'check': 'the start state', 'pass': False, 'seen': "the pan is on the ground"}]})
    s, p = session(r, ref('k0', status='rejected', rejection={'notes': 'make a new picture', 'at': '1'})), plan(shot('S1'))
    line = _paged(P.picture_line(None, s, p, r))
    want = fixture_line('still')
    assert set(line) | {'line', 'key', 'item', 'state'} == set(want)
    assert [(b['label'], b['choice'], b['act']) for b in line['buttons']] == [(b['label'], b['choice'], b['act']) for b in want['buttons']]
    assert line['buttons'][0]['say'] == 'Approved and placed in the film at 2:10.4.' and line['buttons'][0]['sure']['go'] == 'Use it all the same'
    assert line['buttons'][1]['say'] == 'Rejected. Claude asks for a second picture.' and line['buttons'][2]['prefill'] == "the start state: the pan is on the ground."   # D3
    assert line['where'] == 'In the film at 2:10.4 to 2:15.0 (4.6 s) · Gap 8, Homes that last' and line['try'] == 'Try 2'
    assert [x['role'] for x in line['pics']] == ['main', 'earlier'] and line['pics'][1]['why'] == 'You said: make a new picture'
    assert set(line['check']) == set(want['check'])
    assert not any('₹' in json.dumps(line, ensure_ascii=False) or 'INR' in json.dumps(line) for _ in [0])   # D1


def test_the_style_line_and_the_page_words_are_the_fixture_words(monkeypatch):
    r = ref('sty', 'style', None, element_id='_STYLE', element_kind='style', look={'sha256': 'a' * 64, 'lines': []})
    line = _paged(P.picture_line(None, session(r), plan(), r, style=True))
    want = fixture_line('style')
    assert set(line) | {'line', 'key', 'item', 'state'} == set(want)
    assert [(b['label'], b['say']) for b in line['buttons']] == [(b['label'], b['say']) for b in want['buttons']] and line['sub'] == want['sub']
    assert P.PAGE == FIXTURE['layout']['words']['pictures'] and P.W['help'] == FIXTURE['layout']['help'] and 'made' not in FIXTURE['layout'] and 'made' not in P.W
    assert [P.W[c['state']] for c in FIXTURE['layout']['coming']] == [c['note'] for c in FIXTURE['layout']['coming']]


def test_f2_r3_a_steps_line_has_one_correct_per_step_and_two_alike_is_advice_and_asked_once(monkeypatch):
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    monkeypatch.setattr(P, 'alike_steps', lambda store, chain: [(2, 3)])
    a = ref('a', 'state', 'G1', look={'sha256': 'a' * 64, 'lines': []})
    b = ref('b', 'state', 'G1', generation={'parents': [{'id': 'a'}]}, look={'sha256': 'a' * 64, 'lines': []})
    c = ref('c', 'state', 'G1', generation={'parents': [{'id': 'b'}]}, look={'sha256': 'a' * 64, 'lines': [{'id': '1', 'check': 'exact text', 'pass': False, 'seen': "it reads 'enviromental'"}]})
    s, p = session(a, b, c), plan(shot('G1', 'animation', states=3, title='Fewer bricks'))
    line = _paged(P.steps_line(None, s, p, 'G1', [a, b, c]))
    want = fixture_line('steps')
    assert set(line) | {'line', 'key', 'item', 'state'} == set(want)
    assert [b_['choice'] for b_ in line['buttons']] == ['yes', 'correct:1', 'correct:2', 'correct:3']
    assert [b_['say'] for b_ in line['buttons'][1:3]] == [x['say'] for x in want['buttons'][1:3]] and line['buttons'][3]['say'] == want['buttons'][3]['say']
    assert line['check']['advice'][0] == 'Steps 2 and 3 look almost the same: the change between them is small.'
    assert line['buttons'][0]['sure']['ask'] == "Claude's check found 1 problem in step 3, and steps 2 and 3 look almost the same. Use all 3 steps all the same?"
    assert line['check']['faults'] == ["Step 3: exact text: it reads 'enviromental'."] and line['buttons'][3]['prefill'] == "exact text: it reads 'enviromental'."


def test_f2_correct_step_one_rejects_it_and_every_later_step(monkeypatch, held):
    a = ref('a', 'state', 'G1', look={'sha256': 'a' * 64, 'lines': []})
    b = ref('b', 'state', 'G1', generation={'parents': [{'id': 'a'}]}, look={'sha256': 'a' * 64, 'lines': []})
    box = held(session(a, b), plan(shot('G1', 'animation', states=2, title='Fewer bricks')))
    done = []
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run: [])
    monkeypatch.setattr(V, 'waiting', lambda *a_, **k: [{'kind': 'graphics to approve', 'group': 'G1', 'item': 'b', 'label': 'g', 'step': 'pictures'}])
    monkeypatch.setattr(V, '_set_budget', lambda *a_: None)
    monkeypatch.setattr(V, 'visuals_spend', lambda *a_: 0)
    monkeypatch.setattr(P, 'alike_steps', lambda store, chain: [])
    def reject(store, user, run, outputs, rid, notes, quote):
        done.append((rid, notes, quote))
        box['s']['references'][rid].update(status='rejected', rejection={'notes': notes, 'quote': quote})
        return {}
    monkeypatch.setattr(V, 'reject_reference', reject)
    ctx = {'session': box['s'], 'plan': box['p'], 'run': RUN, 'store': None, 'user': USER, 'outputs': [], 'conn': None}
    item = CF._waiting_items(ctx)[0]
    assert [x['choice'] for x in item['buttons'] + item.get('other_choices', [])] == ['yes', 'correct:1', 'correct:2']
    item['_run']('correct:1', 'Correct 1', 'Two icons, not three.')
    assert done == [('a', 'Two icons, not three.', 'Correct 1'), ('b', '', 'No')]                # the critic's review (4): a later step carries no reason: nothing reaches the library
    assert box['s']['references']['b']['rejection']['cause'] == P.W['later_step'] and P._why(box['s']['references']['b']) == P.W['later_step']


# ---------- F3, C6: the drawn graphic ----------

def _job(sha='p' * 64):
    return {'id': 'j9', 'unit': 'D1', 'provider': 'drawn', 'status': 'ready', 'request': {'kind': 'motion', 'request_key': 'k'},
            'result': {'key': 'v.mp4', 'sha_256': 'x', 'sheet_key': 'sheet.jpg', 'evidence': {'timing_matches_placement': True, 'exact_seconds': 4.04}, 'finish': ['grain', 'vignette']}}


def test_f3_c6_a_drawn_line_reads_the_fact_check_of_its_project_and_is_held_without_one(monkeypatch):
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    monkeypatch.setattr(V, 'load_json', lambda store, k: {'sha256': 'p' * 64})
    s, p = session(), plan(shot('D1', 'drawn', title='The wall builds itself'))
    line = _paged(P.drawn_line(None, s, p, _job(), {}, ['grain', 'vignette'], True))
    want = fixture_line('drawn')
    assert set(line) | {'line', 'key', 'item', 'state'} == set(want)
    assert line['check']['head'] == 'Not fact-checked yet.' and line['held'] == 'It has no fact check yet: to select it all the same, say why.' and line['buttons'][0]['needs_words']
    assert line['finish'] == 'Added by the server: a film grain and a soft darkening of the corners.' and line['buttons'][2]['choice'] == 'plain'
    s['motion_projects'] = {'p' * 64: {'rules': [{'id': P.rule_id(f'rule {n}'), 'rule': f'rule {n}'} for n in range(53)]}}
    s['motion_checks'] = {'D1': [{'sha256': 'p' * 64, 'round': 3, 'rules': [{'rule': f'rule {n}', 'pass': n > 1} for n in range(53)], 'stranger': ['0 s: a slab.']},
                                 {'sha256': 'other', 'round': 1, 'rules': []}]}
    v = P.drawn_line(None, s, p, _job(), {}, [], True)['check']
    assert v['head'] == 'Fact check: not passed. 2 of 53 rules are still open after 2 redo rounds:' and v['faults'] == ['rule 0', 'rule 1'] and v['show'] == 'all'
    assert v['by'] == 'A Claude checker that never saw the build judged 53 rules on snapshots of the video.' and v['advice'] == ['0 s: a slab.']


def test_f3_a_clean_drawing_is_selected_with_no_note_the_operator_did_not_give(monkeypatch, held):
    box = held(session(), plan(shot('D1', 'drawn', title='The wall')))
    box['s']['motion_checks'] = {'D1': [{'sha256': 'p' * 64, 'round': 1, 'rules': [{'rule': 'r', 'pass': True}]}]}
    monkeypatch.setattr(V, 'load_json', lambda store, k: {'sha256': 'p' * 64})
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run: [_job()])
    monkeypatch.setattr(V, 'waiting', lambda *a_, **k: [{'kind': 'take to select', 'group': 'D1', 'item': 'j9', 'label': 't', 'step': 'takes'}])
    monkeypatch.setattr(V, '_set_budget', lambda *a_: None)
    monkeypatch.setattr(V, 'visuals_spend', lambda *a_: 0)
    calls = []
    monkeypatch.setattr(V, 'review_take', lambda *a_: calls.append(('review',) + a_[6:9]))
    monkeypatch.setattr(V, 'select_take', lambda *a_: calls.append(('select',) + a_[7:9]))
    ctx = {'session': box['s'], 'plan': box['p'], 'run': RUN, 'store': None, 'user': USER, 'outputs': [], 'conn': None}
    item = CF._waiting_items(ctx)[0]
    assert item['_line']['held'] == '' and not item['buttons'][0].get('needs_words')
    item['_run']('select', 'Select: use it in the film', '')
    assert calls == [('review', 'accepted', '', ''), ('select', '', '')]


def test_c6_the_verdict_answers_every_rule_of_the_project(held, monkeypatch):
    box = held(session(), plan(shot('D1', 'drawn')))
    rules = '# Rules\n1. The only text is "Fewer bricks".\n- Bricks are all the same size.\n'
    held_rules = P.rules_of(rules)
    assert [r['rule'] for r in held_rules] == ['The only text is "Fewer bricks".', 'Bricks are all the same size.']
    box['s']['motion_projects'] = {'p' * 64: {'rules': held_rules}}
    monkeypatch.setattr(V, '_motion_run', lambda run: None)
    monkeypatch.setattr(V, 'locate', lambda store, s_, sid: (None, None, None, {'id': sid}))
    body = lambda rs: {'shot_id': 'D1', 'sha256': 'p' * 64, 'rules': rs}
    with pytest.raises(Exception) as e:
        V.motion_verdict(None, USER, RUN, [], body([{'rule': 'The only text is "Fewer bricks".', 'pass': True}]))
    assert 'leaves 1 rule(s) of the project without an answer' in str(e.value)
    with pytest.raises(Exception) as e:
        V.motion_verdict(None, USER, RUN, [], body([{'rule': r['rule'], 'pass': True} for r in held_rules] + [{'rule': 'Another rule.', 'pass': True}]))
    assert 'is not a rule of this project' in str(e.value)
    with pytest.raises(Exception) as e:
        V.motion_verdict(None, USER, RUN, [], body([{'rule': held_rules[0]['rule'], 'pass': True}, {'rule': held_rules[1]['rule'], 'pass': False}]))
    assert 'says nothing of what was seen' in str(e.value)
    out = V.motion_verdict(None, USER, RUN, [], body([{'rule': held_rules[0]['rule'], 'pass': True}, {'rule': held_rules[1]['rule'], 'pass': False, 'where': 'At 4 s one brick is longer.'}]))
    assert out['failed'] == [held_rules[1]['rule']]
    box['s']['motion_projects'] = {'p' * 64: {}}                                                        # a project uploaded before: the older way, kept until those films close
    assert V.motion_verdict(None, USER, RUN, [], body([{'rule': 'any', 'pass': True}]))['failed'] == []


# ---------- F4, D7, D3, D5, R1, R2, R4 ----------

def test_f4_a_bare_no_stores_no_reason_and_nothing_joins_the_library(held, monkeypatch):
    box = held(session(ref('k1')), plan(shot('S1')))
    box['s']['not_this'] = {'WORKER': {'lines': [], 'from': {}}}
    monkeypatch.setattr(V, '_keep_library', lambda *a: pytest.fail('the library was written'))
    monkeypatch.setattr(V, '_rejected_next', lambda *a: '')
    monkeypatch.setattr(V, 'said', lambda q, w, u: q or w)
    for quote in ('No', 'No, make another'):
        box['s']['references']['k1'].update(status='candidate')
        box['s']['references']['k1'].pop('rejection', None)
        V.reject_reference(None, USER, RUN, [], 'k1', '', quote)
        assert box['s']['references']['k1']['rejection']['notes'] == '' and box['s']['not_this']['WORKER']['lines'] == []


def test_d3_the_fix_round_is_retired():
    with pytest.raises(Exception) as e:
        V.request_fix(None, None, USER, RUN, [], 'k1')
    assert 'The fix round is retired' in str(e.value)


def test_d5_the_style_sheet_only_with_a_graphic_in_steps():
    assert not V._has_steps(plan(shot('D1', 'drawn'))) and V._has_steps(plan(shot('G1', 'animation', states=2)))


def test_r1_the_server_writes_no_fix_prompt_for_the_pixel_rule_to_refuse_and_r2_centred_as_the_hero_is_not_a_place(monkeypatch):
    monkeypatch.setattr(V, 'generate_image', lambda *a, **k: pytest.fail('a server-written fix request was made'))
    with pytest.raises(Exception):
        V.request_fix(None, None, USER, RUN, [], 'k1')   # R1: "Change only: the picture is 1536x1024" is never written now (D3)
    with pytest.raises(ValueError):
        L.check_prompt('A picture of 1536 x 1024.')     # the rule itself stands for what the assistant writes
    L.check_prompt('The bottle stands in the centre of the frame as the hero.')
    with pytest.raises(ValueError):
        L.check_prompt('The worker stands in the centre.')


def test_r4_no_sentence_sends_the_operator_to_the_takes_step():
    text = Path(V.__file__).read_text(encoding='utf-8')
    for old in ('see it on the Takes step.\'}', 'show on the Takes step;', 'a new take on the Takes step, in under a minute; select it there.'):
        assert old not in text.split('def render_motion')[1].split('SUBJECT_RULES')[0]


# ---------- the round, the say, the record ----------

def test_say_is_the_fixture_sentence():
    lines = [{'name': l['name']} for l in FIXTURE['lines']]
    assert P.say(lines, FIXTURE['layout']['coming']) == FIXTURE['say']
    assert P.say([], []) == 'Nothing waits for you on the page now.'
    assert PF.ROUND_NEXT == 'The reference round is complete. Go on with `vw visuals next`: it gives the next decision.'


def test_the_step_is_pictures_once_the_v2_round_is_complete_and_an_item_waits(monkeypatch):
    s = session()
    ctx = {'session': s, 'plan': plan(), 'conn': None, 'run': RUN}
    monkeypatch.setattr(PF, '_spec_lines', lambda c: [])
    monkeypatch.setattr(CF, '_plan_items', lambda c: ([], []))
    monkeypatch.setattr(PF, '_drawing_lines', lambda c: [])
    monkeypatch.setattr(V, '_round_pass', lambda s_, rd: 'complete')
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run: [])
    monkeypatch.setattr(P, 'coming', lambda *a: [])
    monkeypatch.setattr(PF, '_pictures_lines', lambda c: [{'key': 'pic:x', 'name': 'X', 'details': []}])
    assert PF._plan_step(ctx)[0] == 'pictures'
    monkeypatch.setattr(PF, '_pictures_lines', lambda c: [])
    assert PF._plan_step(ctx)[0] == 'plan'
    s['round']['v'] = 1
    monkeypatch.setattr(PF, '_pictures_lines', lambda c: pytest.fail('an older round is asked in the chat'))
    assert PF._plan_step(ctx)[0] == 'plan'


def test_the_page_round_and_an_answer_recorded_stale_or_refused(monkeypatch):
    line = {'kind': 'still', 'name': 'The housing site', 'buttons': [{'label': 'Yes, put it in the film', 'choice': 'yes', 'needs_words': False},
                                                                    {'label': 'Correct it', 'choice': 'correct', 'needs_words': True}], 'pics': [], 'details': [['How', ['x']]]}
    ran = []
    item = {'id': 'picture:k1:aaaaaaaaaa', 'kind': 'picture', '_line': line, '_run': lambda c, q, w: ran.append((c, q, w)) or {}}
    monkeypatch.setattr(CF, '_waiting_items', lambda ctx: [item])
    page = PF._pictures_page({'session': {'page_refused': {'pic:picture:k1:aaaaaaaaaa': 'No.'}}}, {'round': 'r1'}, PF._pictures_lines({}), [])
    assert page['layout']['kind'] == 'pictures' and page['lines'][0]['line'] == 'l01' and page['lines'][0]['key'] == 'pic:picture:k1:aaaaaaaaaa' and page['lines'][0]['refused'] == 'No.'
    assert page['step'] == FIXTURE['step'] and page['say'] == '1 thing needs your answer:\n- The housing site\nThen say done here.'
    assert PF._pictures_answer({}, {'item': 'picture:k1:other'}, 'yes', '') is None                        # stale: the picture changed
    with pytest.raises(Exception):
        PF._pictures_answer({}, {'item': item['id']}, 'correct', '')                                      # words needed
    with pytest.raises(Exception):
        PF._pictures_answer({}, {'item': item['id']}, 'maybe', '')
    assert PF._pictures_answer({}, {'item': item['id']}, 'correct', 'Two workers.')[0] == 'Correct it: Two workers.' and ran == [('correct', 'Correct it', 'Two workers.')]


def test_a_round_over_the_document_size_loses_details_never_a_line():
    lines = [{'key': f'pic:{n}', 'name': str(n), 'details': [['How it was asked for', ['x' * 30000]]]} for n in range(10)]
    page = PF._pictures_page({'session': {}}, {}, lines, [])
    assert len(page['lines']) == 10 and len(json.dumps(page['lines'])) <= PF.ROUND_BYTES and page['lines'][0]['details']
