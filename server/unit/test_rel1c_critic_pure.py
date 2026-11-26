"""Release 1, the critic's points on the eight commits of `rel1` (20 Nov 2026), each with a test that failed first. Without a database.
Until 25 Nov 2026 a passed layout waited for the operator's Yes on its drawing's card before its still; retired (A1): the check's pass opens the still."""
import json
from datetime import timedelta
from pathlib import Path

import pytest

from app import chat_flow as CF, guide as G, page_flow as PF, pictures as P, ref_sets, takes as T, visuals_stage as V
from test_design217_server_pure import held as held6, plan as plan6, ref, session as session6, shot as shot6   # noqa: F401 (held6: the fixture)
from test_design222_takes_pure import NOW, RUN, USER as OP, guide, held, job, look, plan, rec, session, shot, states   # noqa: F401 (held: the fixture)
from test_guide_route_pure import take_film   # noqa: F401 (the fixture)

ROOT = Path(__file__).resolve().parents[2]


def ctx_of(s, p):
    return {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': OP, 'outputs': [], 'conn': None}


def cards(s, p, monkeypatch, rows=()):
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run, sid=None: [j for j in rows if sid in (None, j['unit'])])
    return [':'.join(i['id'].split(':')[:2]) for i in CF._guide_items(ctx_of(s, p))]


# ---------- point 1: a still ordered with a look reference (design/200: `look` is a picture's id, a string) ----------

def test_1_a_still_ordered_with_a_look_reference_does_not_break_step_7_and_keeps_its_reference(held, monkeypatch):
    s, p = session(), plan(shot('S1', title='Mason'))
    s['guides']['S1'] = guide(still='candidate', prompt=False)
    s['guides']['S1']['stills'][0]['look'] = 'R9'                                              # as `guide.request_still` writes it: the picture whose look is kept
    held(s, p)
    assert states(s, p, []) == [('S1', 'being checked by Claude')] and cards(s, p, monkeypatch) == []
    assert "1 picture(s) wait for Claude's check" in P.waits_words(s, p)
    row = P.looks_due(None, RUN, [], [])['pictures'][0]
    done = P.record_looks(None, OP, RUN, [], [{'ref': 'st1', 'sha10': 's' * 10, 'lines': [{'id': l['id'], 'pass': True, 'seen': 'As the picture shows.'} for l in row['lines']]}], 'helper')
    st = s['guides']['S1']['stills'][0]
    assert done['recorded'] == ['st1'] and st['look'] == 'R9' and st['check_look']['who'] == 'helper'   # Claude's look has its own field; the reference is untouched
    assert cards(s, p, monkeypatch) == ['still:S1'] and states(s, p, []) == [('S1', 'waiting for you in the chat')]
    assert T.starts(s, p, []) == '' or 'S1' not in T.starts(s, p, []).split('the checkers of the stills')[-1]


# ---------- point 3: a candidate still of a shot that is no AI video shot any more holds nobody ----------

def test_3_a_plan_revision_that_turns_a_shot_with_a_candidate_still_into_another_kind_does_not_hold_the_words_to_shoot(held, monkeypatch):
    for kind in ('still', 'drawn', 'footage'):
        s, p = session(), plan(shot('S1', kind, end=100), shot('S2', start=100, end=200), shot('S3', start=200, end=300))
        s['guides'] = {'S1': guide(still='candidate', prompt=False), 'S2': guide(), 'S3': guide()}   # S1's still was made while S1 was an AI video shot: nobody is asked to look at it now
        held(s, p)
        assert P.starts_due(s, p) == [] and cards(s, p, monkeypatch) == ['shoot:S2', 'shoot:S3'], kind   # no card for S1, and the others' words come
    s['guides']['S1'] = guide(still='candidate', prompt=False)
    s['guides']['S1']['stills'][0].pop('sha256')                                                # a still that can never be listed for a look is not waited for either
    p = plan(shot('S1', end=100), shot('S2', start=100, end=200))
    held(s, p)
    assert cards(s, p, monkeypatch) == ['still:S1', 'shoot:S2'] and states(s, p, [])[0] == ('S1', 'waiting for you in the chat')


# ---------- point 4: the line of what can start now is complete, and never names what the server would refuse ----------

def test_4_every_group_of_what_can_start_is_named_exactly_when_its_gate_lets_it_through(take_film):
    from test_design151_refs_pure import NEW
    from test_guide_route_pure import TAKE_WORDS, frames_back, passed, refused, scene, still_made
    from test_visuals_stage_pure import USER, saved
    store, conn = take_film
    s = saved(store)
    s['round'] = {'v': 2, 'kept': True, 'pass': 'complete', 'elements': {}}
    V.save_session(store, NEW, s)

    def said():
        s_ = saved(store)
        return T.starts(s_, V.current_plan(store, s_), [])
    assert said() == 'Start now, together in one message: the writers of the scene descriptions of VS1 (1).'
    scene(store, conn)
    sha = saved(store)['guides']['VS1']['sha256']
    assert said() == '' and 'The check frames are not ready yet' in refused(lambda: G.verdict(conn, store, USER, NEW, [], 'VS1', sha, True, [{'look': 'x', 'pass': True}]))
    frames_back(store, conn)
    assert said() == 'Start now, together in one message: ' + GUIDE_CHECK.format(ids='VS1', n=1) + '.'   # release 1 (20 Nov 2026): the checker first; no layout card before its verdict (test_rel1d_layout_check_pure.py)
    passed(store, conn)                                                                          # the real gate takes the verdict
    assert said() == '' and 'The first frame of the layout is not rendered yet' in refused(lambda: still_made(store, conn))   # being rendered: no still can be ordered, and none is named
    s = saved(store)
    g = s['guides']['VS1']
    G.apply_result(s, {'id': g['render']['job_id'], 'request': {'kind': 'guide-render', 'shot_id': 'VS1', 'sha256': g['sha256']}}, 'ready',
                   {'guide_key': 'g.mp4', 'sha256': 'sha-guide', 'bytes': 9, 'frame1_key': 'f1.png', 'frame1_sha256': 'sha-f1', 'render_seconds': 600}, None)
    V.save_session(store, NEW, s)
    # the check passed and the first frame is there: named at once (until 25 Nov 2026: only after the operator's Yes on the layout drawing's card; retired, A1)
    assert said() == 'Start now, together in one message: the stills of VS1 (1), each ordered with `vw guide still --shot S --file still.json`.'
    assert saved(store)['guides']['VS1']['drawing']['status'] == 'proposed'
    sid = still_made(store, conn)                                                                # the real gate takes the order
    assert said() == 'Start now, together in one message: the checkers of the stills of VS1 (1).'   # a still exists: not ordered twice; its checker is what starts
    G.approve_still(conn, store, USER, NEW, [], 'VS1', sid, 'sha-still', 'Yes.')
    assert said() == "Start now, together in one message: the writers of the take's words of VS1 (1) (`vw guide prompt --shot S --file take.txt`)."
    G.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS)
    assert said() == ''


# ---------- the start line on the live film's state (VW-24 on 0.118.0, 20 Nov 2026): 19 guides with their check frames, no verdict, no still ----------

GUIDE_CHECK = ('the checkers of the guides of {ids} ({n}) (a fresh `vw-guide-check` helper each: its guide is rendered, and its still can be ordered, only after its check passes)')


def test_the_gate_that_waits_for_a_guides_check_and_the_line_for_a_shot_whose_frames_are_ready(take_film):
    """Read in the code and proved on the gates: 0.118.0 records a guide's verdict (`guides[shot].verdicts`), the guide is rendered only when a fresh
    checker's verdict passes (`guide.verdict` queues the render), and no still can be ordered before the render (`guide.request_still`). So for a shot
    whose guide has no verdict, the checker is what starts; "order the stills" would be refused. Release 1 (20 Nov 2026, design/35 row 281): the
    checker is named as soon as the check frames are ready (until then: the layout card first, the checker only after the operator's Yes).
    Until 25 Nov 2026 the layout card came after the verdict passed; retired (A1): no card, the old Yes is refused by name."""
    from test_design151_refs_pure import NEW
    from test_guide_route_pure import OTHER, frames_back, refused, scene, still_made
    from test_visuals_stage_pure import USER, saved
    store, conn = take_film
    s = saved(store)
    s['round'] = {'v': 2, 'kept': True, 'pass': 'complete', 'elements': {}}
    V.save_session(store, NEW, s)
    said = lambda: T.starts(saved(store), V.current_plan(store, saved(store)), [])
    scene(store, conn)
    sha = frames_back(store, conn)
    states = lambda: [(i['id'], i['state']) for i in T.expected(saved(store), V.current_plan(store, saved(store)), [])]
    assert said() == 'Start now, together in one message: ' + GUIDE_CHECK.format(ids='VS1', n=1) + '.' and states() == [('VS1', 'being checked by Claude')]
    assert refused(lambda: G.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, True, 'Yes.')) == G.DRAWING_RETIRED   # the older way's Yes on a layout: refused by name, before the check too
    assert 'The first frame of the layout is not rendered yet: it is rendered, before the video, after a fresh checker passes the check frames' in refused(lambda: still_made(store, conn))   # the gate: no still yet (release 4; until then: "The guide is not rendered yet")
    assert saved(store)['guides']['VS1'].get('render') is None
    G.verdict(conn, store, OTHER, NEW, [], 'VS1', sha, True, [{'look': 'everyone reads as a person', 'pass': True}])
    assert saved(store)['guides']['VS1']['render']['status'] == 'queued' and said() == ''       # the verdict is what queues the render; the checker is not named again
    assert states() == [('VS1', 'being made')]                                                   # its first frame is being made: no layout card waits for the operator
    assert CF._layout_items({'session': saved(store), 'plan': V.current_plan(store, saved(store)), 'run': NEW, 'store': store, 'user': USER, 'outputs': [], 'conn': conn}) == []


def test_the_start_line_for_a_film_shaped_like_the_live_one(held):
    ids = [f'S{n:02d}' for n in range(1, 20)]
    s, p = session(), plan(*[shot(sid, start=100 * n, end=100 * n + 100) for n, sid in enumerate(ids)])
    live = lambda drawing: {'sha256': 'g' * 64, 'key': 'k', 'seconds': 6, 'frames': {'job_id': 'f', 'status': 'ready', 'frames': [], 'strip_key': 'strip'}, 'verdicts': [], 'rounds_before': 0,
                            'drawing': {'status': drawing, 'sha256': 'g' * 64}, 'stills': [], 'takes': [], 'checks': []}
    s['guides'] = {sid: live('proposed' if sid in ('S18', 'S19') else 'approved') for sid in ids}   # 17 layouts approved by the operator under the older way, 2 never answered; no verdict, no render, no still
    held(s, p)
    assert T.status_line(T.expected(s, p, [], NOW)) == 'AI video: 19 being checked by Claude.'    # release 1 (20 Nov 2026): no card before the check, so S18 and S19 are with their checkers too
    assert T.starts(s, p, []) == 'Start now, together in one message: ' + GUIDE_CHECK.format(ids=', '.join(ids), n=19) + '.'
    for sid in ids[:5]:                                                                          # five checks passed and their guides rendered: their stills can be ordered
        s['guides'][sid].update(verdicts=[{'sha256': 'g' * 64, 'pass': True}], render={'job_id': 'r', 'status': 'ready', 'frame1_key': 'f1.png'})
    s['guides']['S06'].update(verdicts=[{'sha256': 'g' * 64, 'pass': True}], render={'job_id': 'r', 'status': 'queued'})   # being rendered: nothing to start for it
    assert T.starts(s, p, []) == ('Start now, together in one message: ' + GUIDE_CHECK.format(ids=', '.join(ids[6:]), n=13)
                                  + '; the stills of S01, S02, S03, S04, S05 (5), each ordered with `vw guide still --shot S --file still.json`.')
    s['guides']['S19'].update(verdicts=[{'sha256': 'g' * 64, 'pass': True}], render={'job_id': 'r', 'status': 'ready', 'frame1_key': 'f1.png'})   # a layout nobody approved: its pass is enough (A1)
    assert T.starts(s, p, []) == ('Start now, together in one message: ' + GUIDE_CHECK.format(ids=', '.join(ids[6:18]), n=12)
                                  + '; the stills of S01, S02, S03, S04, S05, S19 (6), each ordered with `vw guide still --shot S --file still.json`.')


# ---------- point 5: "does not apply" never clears a line that already failed, and never approves a component by itself ----------

def test_5a_a_remade_picture_cannot_answer_na_on_the_line_it_was_made_for_or_on_a_line_its_original_failed(held6):
    orig = ref('k0', status='rejected', server_checklist=[{'check': 'the tool', 'pass_when': 'a trowel in the right hand', 'weight': 'must'}],
               look={'sha256': 'a' * 64, 'lines': [{'id': 'x', 'check': 'the tool', 'pass': False, 'seen': 'A hammer.'}]})
    new = ref('k1', sha='b' * 64, fix_of='k0', fix_for='the tool', server_checklist=[{'check': 'the tool', 'pass_when': 'a trowel in the right hand', 'weight': 'must'}])
    box = held6(session6(orig, new), plan6(shot6('S1')))
    want = P.lines(box['s'], box['p'], new)
    send = lambda na: P.record_looks(None, OP, RUN, [], [{'ref': 'k1', 'sha10': 'b' * 10, 'lines': [
        {'id': l['id'], 'pass': 'na' if l['check'] in na else True, 'seen': 'Not in this view.' if l['check'] in na else 'As the picture shows.'} for l in want]}], 'helper')
    for check in ('the tool', 'the line it was made for'):
        out = send({check})
        assert out['recorded'] == [] and f'the line "{check}"' in out['refused']['k1'] and 'answer it pass or fail, not "na"' in out['refused']['k1'] and 'send the file again' in out['refused']['k1'], check
    assert send({'nothing extra'})['recorded'] == ['k1']                                          # a line that never failed may still not apply


def test_5b_a_component_with_a_line_that_does_not_apply_is_not_approved_by_the_check_alone_and_is_said(held6):
    c = ref('c1', 'component', None)
    box = held6(session6(c), plan6(shot6('D1', 'drawn')))
    want = P.lines(box['s'], box['p'], c)
    rows = [{'id': l['id'], 'pass': True, 'seen': 'As the picture shows.'} for l in want]
    rows[0].update({'pass': 'na', 'seen': 'A part with no surface in view.'})
    P.record_looks(None, OP, RUN, [], [{'ref': 'c1', 'sha10': 'a' * 10, 'lines': rows}], 'helper')
    assert box['s']['references']['c1']['status'] == 'candidate'                                  # not approved with nobody seeing it
    said = P.components_failed(box['s'], box['p'])
    assert len(said) == 1 and 'does not apply' in said[0] and want[0]['check'] in said[0] and P._component_state([box['s']['references']['c1']]) == 'redo'
    box['s']['references']['c1'].pop('look')
    P.record_looks(None, OP, RUN, [], [{'ref': 'c1', 'sha10': 'a' * 10, 'lines': [{'id': l['id'], 'pass': True, 'seen': 'As the picture shows.'} for l in want]}], 'helper')
    assert box['s']['references']['c1']['status'] == 'approved'                                   # every line judged and passed: approved, as before


# ---------- point 6: step 7's still is asked who and what is in it, and gets the stills it was made from ----------

def test_6_the_stills_list_asks_who_and_what_is_in_it_and_an_approved_still_it_was_made_from_is_sent_as_a_parent(held):
    s, p = session(), plan(shot('S1', end=100, title='Mason'), shot('S2', start=100, end=200, title='Wall'))
    s['guides'] = {'S1': guide(), 'S2': guide(still='candidate', prompt=False)}
    s['guides']['S1']['stills'][0].update(id='first', key='run-1/first.png')                     # the scene's first approved still
    s['guides']['S2']['stills'][0]['inputs'] = [{'id': 'first', 'job': 'the place: copy the wall and the light'}, {'id': 'gone', 'job': 'x'}]
    held(s, p)
    row = P.looks_due(None, RUN, [], [])['pictures'][0]
    who = next(l for l in row['lines'] if l['check'] == 'who and what')
    assert who['say'] is True and 'sent as `parent`' in who['pass_when'] and row['lines'][1] == who   # right after the layout line
    assert [(i['role'], i['key']) for i in row['inputs']] == [('overlay', 'o.jpg'), ('layout', 'f1.png'), ('parent', 'run-1/first.png')]


# ---------- point 7: a made picture of kind `isolated` is Claude's too ----------

def test_7_an_isolated_picture_made_for_a_still_shot_is_checked_by_claudes_look_with_a_stills_list(held6, monkeypatch):
    from app import visual_workers as VW
    iso, key = ref('i1', 'isolated'), ref('k1', 'keyframe')
    box = held6(session6(iso), plan6(shot6('S1')))
    s, p = box['s'], box['p']
    assert P.claude_checks(s, iso, p) and VW._claude_checks(None, s, iso)                         # the worker's own question: no model is called for it
    assert [(l['check'], l['pass_when']) for l in P.lines(s, p, iso)] == [(l['check'], l['pass_when']) for l in P.lines(session6(key), p, key)]   # a still's list
    assert [x['ref'] for x in P.looks_due(None, RUN, [])['pictures']] == ['i1'] and not P.offered(s, iso, p, NOW)
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run, sid=None: [])
    assert [(i['id'], i['state']) for i in P.expected(s, p, []) if i['kind'] == 'still'] == [('S1', 'being checked by Claude')]   # counted as the still of its shot
    assert not P.claude_checks(s, ref('f1', 'frame'), p) and not P.claude_checks(s, ref('sh', 'sheet', set='x'), p)   # footage pictures and sets stay out


# ---------- point 10: what the served text says is what happens ----------


def test_10a_the_held_drawings_card_selects_with_one_click(monkeypatch):
    calls = []
    monkeypatch.setattr(V, 'session_of', lambda *a, **k: {'motion_held': {}})
    monkeypatch.setattr(V, 'held_drawing', lambda s, shot: {'sha256': 'p', 'round': 3})
    monkeypatch.setattr(V, 'select_take', lambda *a: calls.append(a[5:8]) or {})
    monkeypatch.setattr(V, 'save_session', lambda *a: None)
    assert V.held_answer(None, None, OP, RUN, [], 'D1', 'j9', 'select', 'Select it anyway')['recorded'] and calls == [('j9', 'Select it anyway', P.W['against_note'])]
    V.held_answer(None, None, OP, RUN, [], 'D1', 'j9', 'select', 'Select', 'It reads right.')
    assert calls[-1] == ('j9', 'Select', 'It reads right.')                                      # a reason given is kept as it is


def test_10b_10a_the_served_text_says_one_thing():
    stage = next(st for st in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if st['name'] == 'visuals')
    text = stage['prompt'] + ' '.join(pt['text'] for pt in stage['parts'])
    for gone in ('select it anyway with their reason', '`select` needs `--notes` saying why it is taken', 'Nothing of step 7 is asked one by one'):
        assert gone not in text, gone
    assert 'No finished take is asked one by one' in text and 'select it anyway (one click, recorded as selected against the check)' in text
    assert '`select` takes it all the same and records that it went against the check' in text
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert 'select it anyway with their reason' in retired and 'Nothing of step 7 is asked one by one' in retired


def test_10c_a_person_of_the_footage_is_asked_about_before_the_stills_of_their_shots_are_ordered(held6, monkeypatch):
    box = held6(session6(), plan6(shot6('S1'), {**shot6('S2'), 'subjects': []}))                 # S1 shows the kiln worker (a person); S2 shows nobody
    s, p = box['s'], box['p']
    monkeypatch.setattr(ref_sets, 'footage_person', lambda s_, p_, eid: {'state': 'ask' if not s_.get('likeness') else 'permitted'})
    said = P.faces_to_ask(s, p)
    assert len(said) == 1 and 'Kiln worker (WORKER)' in said[0] and 'ask the operator once' in said[0]   # no picture is made yet: asked now
    assert said[0] in P.waits_words(s, p)                                                        # with the step's first next-step line
    items = [{'kind': 'still', 'id': 'S1', 'state': P.STATE['none']}, {'kind': 'still', 'id': 'S2', 'state': P.STATE['none']}]
    assert '(S2)' in P.stills_due(items, P.ask_shots(s, p)) and 'S1' not in P.stills_due(items, P.ask_shots(s, p))   # S1's still waits for the answer; S2's does not
    s['likeness'] = {'WORKER': {'quote': 'Yes.'}}
    assert P.faces_to_ask(s, p) == [] and 'S1, S2' in P.stills_due(items, P.ask_shots(s, p))


# ---------- point 9: a permission recorded while a look is out does not refuse that look ----------

def test_9_the_real_face_line_keeps_its_id_when_a_persons_permission_is_recorded(held6):
    box = held6(session6(ref('k1')), plan6(shot6('S1')))
    before = P.lines(box['s'], box['p'], box['s']['references']['k1'])
    answers = [{'id': l['id'], 'pass': True, 'seen': 'As the picture shows.'} for l in before]       # the helper's file, written from the list as it was
    box['s']['likeness'] = {'WORKER': {'quote': 'Yes, show him.'}}                                # the operator's permission, recorded meanwhile
    after = P.lines(box['s'], box['p'], box['s']['references']['k1'])
    face = lambda rows: next(l for l in rows if l['check'] == 'a real face')
    assert face(before)['pass_when'] != face(after)['pass_when'] and face(before)['id'] == face(after)['id']   # the words name him now; the id stands
    out = P.record_looks(None, OP, RUN, [], [{'ref': 'k1', 'sha10': 'a' * 10, 'lines': answers}], 'helper')
    assert out['recorded'] == ['k1'] and out['refused'] == {}


# ---------- point 2: an answer to an older view of the check is stale, for every item that is one click ----------

FAILED = {'sha256': 'a' * 64, 'lines': [{'id': '1', 'check': 'a real face', 'pass': False, 'seen': 'The face matches a bystander.'}]}
PASSED = {'sha256': 'a' * 64, 'lines': [{'id': '1', 'check': 'a real face', 'pass': True, 'seen': ''}]}


def six(box, monkeypatch, waiting, rows=()):
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run, sid=None: list(rows))
    monkeypatch.setattr(V, 'waiting', lambda *a_, **k: waiting)
    monkeypatch.setattr(V, '_set_budget', lambda *a_: None)
    monkeypatch.setattr(V, 'visuals_spend', lambda *a_: 0)
    monkeypatch.setattr(V, 'approve_reference', lambda *a_: {})
    monkeypatch.setattr(V, 'sequence', lambda *a_: {})
    monkeypatch.setattr(V, 'review_take', lambda *a_: {})
    monkeypatch.setattr(V, 'select_take', lambda *a_: {})
    monkeypatch.setattr(V, 'motion_brief', lambda *a_, **k: {'lines': {}})
    monkeypatch.setattr(V, 'stale_brief', lambda *a_, **k: [])
    monkeypatch.setattr(CF, '_decided', lambda *a_: None)
    return {'session': box['s'], 'plan': box['p'], 'run': RUN, 'store': None, 'user': OP, 'outputs': [], 'conn': object()}


def test_2_a_step_6_still_shown_not_checked_whose_failing_look_arrives_before_the_answer_is_asked_again(monkeypatch, held6):
    late = (P._now() - timedelta(minutes=40)).isoformat()
    box = held6(session6(ref('k1', ready_at=late, asked_at=late)), plan6(shot6('S1')))
    ctx = six(box, monkeypatch, [{'kind': 'picture to answer', 'group': 'S1', 'item': 'k1', 'label': 'p', 'step': 'pictures'}])
    shown = CF._waiting_items(ctx)[0]
    assert shown['_line']['check']['state'] == 'not_checked' and shown['id'].startswith('picture:k1:aaaaaaaaaa:')
    box['s']['references']['k1']['look'] = FAILED                                              # the late look, with a warning the operator never saw
    assert PF._pictures_answer(ctx, {'item': shown['id']}, 'yes', '') is None                 # stale: nothing recorded against a warning not in view
    again = CF._waiting_items(ctx)[0]
    assert again['id'] != shown['id'] and PF._pictures_answer(ctx, {'item': again['id']}, 'yes', '')[0] == 'Yes, put it in the film'
    assert PF._counted(box['s'], {'lines': [{'item': again['id'], 'name': 'x'}], 'layout': {}}, [{'id': 'S1', 'name': 'x', 'state': 'made and checked'}], '{n} of {m}', ())['layout']['count'] == '1 of 1'   # the id is still read


def test_2_an_id_of_a_round_written_before_the_mark_is_taken_only_while_the_check_has_no_warning(monkeypatch, held6):
    box = held6(session6(ref('k1', look=PASSED)), plan6(shot6('S1')))
    ctx = six(box, monkeypatch, [{'kind': 'picture to answer', 'group': 'S1', 'item': 'k1', 'label': 'p', 'step': 'pictures'}])
    old = 'picture:k1:' + 'a' * 10                                                             # as the 0.118.0 server wrote it
    assert PF._pictures_answer(ctx, {'item': old}, 'yes', '')[0] == 'Yes, put it in the film'  # nothing to hide: taken
    box['s']['references']['k1']['look'] = FAILED
    assert PF._pictures_answer(ctx, {'item': old}, 'yes', '') is None                         # a warning now: asked again, with it in view


def _drawn():
    return {'id': 'j9', 'unit': 'D1', 'provider': 'drawn', 'status': 'ready', 'request': {'kind': 'motion', 'request_key': 'k'},
            'result': {'key': 'v.mp4', 'sheet_key': 'sheet.jpg', 'evidence': {'timing_matches_placement': True, 'exact_seconds': 4.04}}}


def test_2_a_drawing_that_became_held_after_the_page_was_drawn_is_asked_again(monkeypatch, held6):
    box = held6(session6(), plan6(shot6('D1', 'drawn', title='The wall')))
    box['s']['motion_checks'] = {'D1': [{'sha256': 'p' * 64, 'round': 1, 'rules': [{'rule': 'r', 'pass': True}]}]}
    monkeypatch.setattr(V, 'load_json', lambda store, k: {'sha256': 'p' * 64})
    ctx = six(box, monkeypatch, [{'kind': 'take to select', 'group': 'D1', 'item': 'j9', 'label': 't', 'step': 'takes'}], [_drawn()])
    shown = CF._waiting_items(ctx)[0]
    assert shown['_line']['held'] == '' and shown['id'].startswith('take:j9:')
    box['s']['motion_checks']['D1'].append({'sha256': 'p' * 64, 'round': 2, 'rules': [{'rule': 'r', 'pass': False}]})   # a later verdict fails a must: the drawing is held now
    assert PF._pictures_answer(ctx, {'item': shown['id']}, 'select', '') is None and PF._pictures_answer(ctx, {'item': 'take:j9'}, 'select', '') is None
    again = CF._waiting_items(ctx)[0]
    assert again['_line']['held'] and PF._pictures_answer(ctx, {'item': again['id']}, 'select', '')[0].startswith('Select')


def test_2_a_step_7_still_shown_not_checked_whose_failing_look_arrives_gets_a_new_card(held, monkeypatch):
    s, p = session(), plan(shot('S1', title='Mason'))
    s['guides']['S1'] = guide(still='candidate', prompt=False)
    s['guides']['S1']['stills'][0]['asked_at'] = (P._now() - timedelta(minutes=40)).isoformat()
    held(s, p)
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run, sid=None: [])
    shown = CF._guide_items(ctx_of(s, p))[0]
    assert 'Not checked' in shown['text']
    s['guides']['S1']['stills'][0]['check_look'] = {'sha256': 's' * 64, 'lines': [{'id': '1', 'check': 'on the layout', 'pass': False, 'seen': 'A step left of the outline.'}]}
    again = CF._guide_items(ctx_of(s, p))[0]
    assert again['id'] != shown['id'] and again['id'].startswith('still:S1:st1:') and '1 warning: on the layout' in again['text']   # the chat's answer to the older card finds no such item
