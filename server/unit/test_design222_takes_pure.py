"""design/222 (SK, 19 Nov 2026): step 7, AI video, on the decisions page. The finished takes are judged on the page, all together, once every take
is made and checked; Claude checks each take from frames (Gemini 3.8 Flash no longer watches it); "Make another" on the page is the operator's
word for one more take; the words spoken during the shot are sent with their seconds. Without a database."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app import chat_flow as CF, guide as G, guide_worker as GW, page_flow as PF, pictures as P, takes as T, visuals_stage as V

HERE = Path(__file__).resolve().parent
FIXTURE = json.loads((HERE / 'd222_takes_round.json').read_text(encoding='utf-8'))
RUN, USER = {'id': 'run-1', 'code': 'VW-99'}, {'id': 'u1', 'name': 'Op'}
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
SHA = 'a' * 64


def shot(sid, kind='video', start=0, end=129, title='', words='As the demand grows'):
    return {'id': sid, **({'title': title} if title else {}), 'visual_type': kind, 'narration': words, 'start_frame': start, 'end_frame': end}


def plan(*shots, title='Housing at work'):
    return {'elements': [], 'gaps': [{'gap_id': 'G1', 'title': title, 'scenes': [{'id': 'sc1', 'shots': list(shots)}]}]}


def job(jid, sid='S1', status='ready', sha=SHA, at='2026-11-19T10:00:00+00:00', **req):
    return {'id': jid, 'run_id': 'run-1', 'unit': sid, 'provider': 'video', 'status': status, 'updated_at': at, 'created_at': at,
            'request': {'kind': 'take', 'request_key': f'run-1/visuals/takes/{jid}.request.json', 'duration_seconds': 6, **req},
            'result': {'key': f'run-1/visuals/takes/{jid}.mp4', 'sha256': sha, 'bytes': 1, 'evidence': {'duration_seconds': 6.04, 'timing_matches_placement': True}} if status == 'ready' else {}}


def rec(look=None, jump=None, blocked=None, frames=13, **more):
    """A take's check record as the worker leaves it: the measured lines, the frames every half second and the sheet; `look` is Claude's."""
    code = [{'check': 'real footage', 'weight': 'must', 'pass': True, 'seen': 'the clip differs from its guide by 31.0 % on 6 frames'},
            {'check': 'as long as the guide', 'weight': 'must', 'pass': True, 'seen': 'the clip is 6.0 s, the guide 6.0 s'},
            {'check': 'first frame matches the still', 'weight': 'must', 'pass': True, 'seen': 'shifted 0.4 % of the width, zoom 0.2 %'},
            {'check': 'one continuous shot', 'weight': 'must', 'pass': jump is None, 'seen': 'no jump to another view' if jump is None else f'the picture jumps to another view at {jump} s',
             **({'at_s': jump} if jump is not None else {})}]
    return {'guide': True, 'code_lines': code, 'blocked': blocked, 'frames': [{'at_s': n * 0.5, 'key': f'f/{n}.jpg'} for n in range(frames)], 'sheet_key': 'f/sheet.jpg' if frames else None,
            'not_read': look is None, **({'look': look} if look else {}), **more}


def look(fail=(), sha=SHA, **more):
    return {'who': 'helper', 'at': NOW.isoformat(), 'sha256': sha,
            'lines': [{'id': l['id'], 'check': l['check'], 'pass': l['check'] not in fail, 'seen': 'The broom is gone at 3.5 s.' if l['check'] in fail else '', **({'at_s': 3.5} if l['check'] in fail else {})}
                      for l in T.look_lines()], **more}


def guide(sha='g' * 64, drawing='approved', still='approved', prompt=True, takes=(), **more):
    return {'sha256': sha, 'key': 'k', 'seconds': 6, 'drawing': {'status': drawing, 'sha256': sha}, 'render': {'status': 'ready', 'guide_key': 'g.mp4', 'frame1_key': 'f1.png', 'sha256': 'r'},
            'stills': [{'id': 'st1', 'status': still, 'guide_sha256': sha, 'key': 'run-1/still.png', 'sha256': 's' * 64, 'overlay_key': 'o.jpg'}] if still else [],
            **({'take_prompt': {'prompt': 'ONE action only: he lays the brick.', 'at': 't'}} if prompt else {}),
            'takes': [{'job_id': j, 'camera': 'cam1'} for j in takes], 'checks': [], **more}


def session(**more):
    s = {'round': {'v': 2, 'kept': True, 'pass': 'complete', 'elements': {}}, 'references': {}, 'accepted': {}, 'choice_selections': {}, 'questions': {}, 'reviews': {}, 'selections': {},
         'assets': {}, 'current': 'p1', 'guides': {}, 'take_checks': {}, 'preparations': {},
         'source': {'fps': 25, 'gaps': {'G1': {'timing': {'words': [{'text': w, 'start_frame': 2 + 10 * i, 'end_frame': 8 + 10 * i} for i, w in enumerate('As the demand grows, homes rise.'.split())]}}}}}
    s.update(more)
    return s


@pytest.fixture
def held(monkeypatch):
    box = {}

    def use(s, p):
        box.update(s=s, p=p)
        monkeypatch.setattr(V, 'session_of', lambda *a, **k: box['s'])
        monkeypatch.setattr(V, 'save_session', lambda store, run, s_: box.update(s=s_))
        monkeypatch.setattr(V, 'current_plan', lambda *a, **k: box['p'])
        monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
        monkeypatch.setattr(V, 'load_json', lambda store, key: {'kind': 'guide', 'placement': {'exact_seconds': 5.16}})
        return box
    return use


def states(s, p, rows, now=NOW):
    return [(i['id'], i['state']) for i in T.expected(s, p, rows, now)]


# ---------- what step 7 must make, each shot's state, the line of counts, when the page opens ----------

def test_a_film_with_no_ai_video_has_no_step_7(held):
    p = plan(shot('S1', 'still'))
    held(session(), p)
    assert T.expected(session(), p, []) == [] and T.status_line([]) == '' and T.complete([])


@pytest.mark.parametrize('change, rows, state', [
    (lambda s: None, [], 'not started'),
    (lambda s: s['guides'].update(S1=guide(drawing='proposed', still=None, prompt=False)), [], 'waiting for you in the chat'),        # the layout drawing's card
    (lambda s: (s['guides'].update(S1=guide(still='candidate', prompt=False)), s['guides']['S1']['stills'][0].update(look={'sha256': 's' * 64, 'lines': []})), [], 'waiting for you in the chat'),   # the still's card, once Claude looked at it (release 1, A1)
    (lambda s: s['guides'].update(S1=guide()), [], 'waiting for you in the chat'),                                                  # the word to make the take
    (lambda s: s['guides'].update(S1=guide(still=None, prompt=False)), [], 'being made'),
    (lambda s: s['guides'].update(S1=guide()), [job('j1', status='running')], 'being made'),
    (lambda s: (s['guides'].update(S1=guide()), s['take_checks'].update(j1=rec())), [job('j1')], 'being checked by Claude'),
    (lambda s: (s['guides'].update(S1=guide()), s['take_checks'].update(j1=rec(look=look()))), [job('j1')], 'made and checked'),
    (lambda s: (s['guides'].update(S1=guide()), s['take_checks'].update(j1=rec(blocked='the guide came back unedited'))), [job('j1')], 'waiting for you in the chat'),
    (lambda s: s['guides'].update(S1=guide()), [job('j1', status='failed')], 'could not be made'),
    (lambda s: s['guides'].update(S1=guide(still='candidate', prompt=False)), [], 'being checked by Claude'),                      # release 1, A1: the still waits for Claude's look; then its card
    (lambda s: (s['guides'].update(S1=guide()), s['selections'].update(S1={'job_id': 'j1'})), [job('j1')], 'answered'),
    (lambda s: (s['guides'].update(S1=guide()), s['take_checks'].update(j1=rec(look=look())), s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'x'}])), [job('j1')], 'waiting for you in the chat'),
    (lambda s: (s['guides'].update(S1=guide(again={'job_id': 'j1', 'words': 'x'})), s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'x'}])), [job('j1')], 'being redone'),
    (lambda s: (s['guides'].update(S1=guide()), s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'x'}])), [job('j1'), job('j2', status='queued')], 'being redone'),
    (lambda s: (s['guides'].update(S1=guide()), s['take_checks'].update(j1=rec(look=look()))), [job('j1', plan_digest='another plan')], 'must be made again (the plan changed)'),
])
def test_each_ai_video_shot_reads_its_state(held, change, rows, state):
    s, p = session(), plan(shot('S1'), shot('S2', 'still', 129, 200))
    change(s)
    held(s, p)
    assert states(s, p, rows) == [('S1', state)]


def test_the_line_of_counts_and_the_page_opens_only_when_every_take_is_made_and_checked(held):
    s, p = session(), plan(shot('S1'), shot('S2', start=129, end=260), shot('S3', start=260, end=400))
    s['guides'].update(S1=guide(), S2=guide(), S3=guide())
    s['take_checks'].update(j1=rec(look=look()), j2=rec())
    held(s, p)
    rows = [job('j1'), job('j2', 'S2'), job('j3', 'S3', status='running')]
    items = T.expected(s, p, rows, NOW)
    assert T.status_line(items) == 'AI video: 1 made and checked, 1 being checked by Claude, 1 being made.' and not T.complete(items)
    s['take_checks'].update(j2=rec(look=look()), j3=rec(look=look()))
    assert T.complete(T.expected(s, p, [job('j1'), job('j2', 'S2'), job('j3', 'S3')], NOW))
    assert T.complete(T.expected(s, p, [job('j1'), job('j2', 'S2'), job('j3', 'S3', status='failed')], NOW))   # a take that could not be made never keeps the page closed


def test_a_take_is_not_offered_before_its_check_and_after_30_minutes_it_is_offered_as_not_checked(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide())
    held(s, p)
    j = job('j1', at='2026-11-19T11:50:00+00:00')
    assert not T.offered(s, j, NOW)                                   # the worker has not written the check yet: the gap of a take shown with no check lines
    assert T.offered(s, j, NOW + timedelta(minutes=25))               # ... never held for ever: 30 minutes after the take was made
    s['take_checks']['j1'] = rec()
    assert not T.offered(s, j, NOW) and T.asked(s, p, [j], NOW) and s['take_checks']['j1']['asked_at']
    assert not T.offered(s, j, NOW + timedelta(minutes=29)) and T.offered(s, j, NOW + timedelta(minutes=30))
    assert T.check_view(s, j, NOW + timedelta(minutes=30))['state'] == 'not_checked' and '30 minutes' in T.check_view(s, j, NOW + timedelta(minutes=30))['head']
    s['take_checks']['j1'] = rec(frames=0)                            # its frames could not be made: offered at once, as not checked
    assert T.offered(s, j, NOW) and T.check_view(s, j, NOW)['state'] == 'not_checked' and T.due(s, p, [j]) == []


def test_waiting_holds_a_ready_ai_video_take_until_all_are_made_and_checked(held, monkeypatch):
    s, p = session(), plan(shot('S1'), shot('S2', start=129, end=260))
    s['guides'].update(S1=guide(), S2=guide())
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    monkeypatch.setattr(V, 'item_link', lambda *a: '')
    rows = [job('j1'), job('j2', 'S2', status='running')]
    kinds = lambda rows_, **k: [w['kind'] for w in V.waiting(s, p, 'VW-99', rows_, **k)]
    assert kinds(rows) == [] and kinds(rows, gate=False) == ['take to select']          # one by one in the chat is retired; an answer on the page that opened is taken
    s['take_checks'].update(j2=rec(look=look()))
    assert kinds([job('j1'), job('j2', 'S2')]) == ['take to select', 'take to select']


# ---------- Claude's check of a take, from frames ----------

def test_the_lines_claude_judges_are_the_five_of_a_guide_take_and_gemini_is_never_called(monkeypatch):
    assert [l['check'] for l in T.look_lines()] == ['people', 'the action', 'objects', 'bodies and contact', 'the place and the light']
    from app import image_check as IC, visual_workers as VW
    monkeypatch.setattr(IC, '_model_take_check', lambda *a, **k: pytest.fail('Gemini does not watch a take made from a guide'))
    monkeypatch.setattr(IC, 'take_drift', lambda path, snap: {'check': 'camera drift', 'pass': None, 'weight': 'should', 'seen': 'drift up to 1.0 %'})
    out = VW.take_reading({'kind': 'guide'}, 'x.mp4', SHA, None)
    assert out['model'] is None and [l['check'] for l in out['lines']] == ['camera drift']


def test_the_takes_due_are_listed_with_their_frames_the_sheet_the_still_and_the_lines(held):
    s, p = session(), plan(shot('S1'), shot('S2', start=129, end=260))
    s['guides'].update(S1=guide(), S2=guide())
    s['take_checks'].update(j1=rec(), j2=rec(blocked='the guide came back unedited'))
    held(s, p)
    rows = T.listed(s, p, [job('j1'), job('j2', 'S2')])
    assert [r['ref'] for r in rows] == ['j1'] and rows[0]['kind'] == 'take' and rows[0]['sha10'] == SHA[:10] and rows[0]['key'] == 'f/sheet.jpg'   # a clip set aside is never given to the check
    assert [i['role'] for i in rows[0]['inputs']] == ['frame'] * 13 + ['still'] and rows[0]['inputs'][3]['at_s'] == 1.5 and rows[0]['inputs'][-1]['key'] == 'run-1/still.png'
    assert len(rows[0]['lines']) == 5 and rows[0]['seconds'] == 6.04 and 'ONE action only' in rows[0]['request']


def test_a_look_is_recorded_line_by_line_and_a_skipped_line_or_an_older_take_is_refused_by_name(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide())
    s['take_checks'].update(j1=rec())
    held(s, p)
    rows, want = [job('j1')], T.look_lines()
    full = [{'id': l['id'], 'pass': True, 'seen': ''} for l in want]
    assert 'has no answer' in T.record(s, p, rows, {'ref': 'j1', 'sha10': SHA[:10], 'lines': full[:-1]}, 'helper')
    assert 'needs one plain sentence' in T.record(s, p, rows, {'ref': 'j1', 'sha10': SHA[:10], 'lines': full[:-1] + [{'id': want[-1]['id'], 'pass': False, 'seen': ''}]}, 'helper')
    assert 'not a take waiting for its check' in T.record(s, p, rows, {'ref': 'j1', 'sha10': 'b' * 10, 'lines': full}, 'helper')
    assert not s['take_checks']['j1'].get('look')
    bad = full[:2] + [{'id': want[2]['id'], 'pass': False, 'seen': 'The broom is in his hand at 3.0 s and gone at 3.5 s.', 'at_s': 3.5}] + full[3:]
    assert T.record(s, p, rows, {'ref': 'j1', 'sha10': SHA[:10], 'lines': bad}, 'helper') is None
    r = s['take_checks']['j1']
    assert r['look']['who'] == 'helper' and r['not_read'] is False and [x['state'] for x in r['scorecard'] if x['line'] == 'objects'] == ['Fail']
    assert [x['line'] for x in r['scorecard']] == ['real footage and length', 'first frame', 'one continuous shot', 'people', 'the action', 'objects', 'bodies and contact', 'the place and the light']
    v = T.check_view(s, rows[0], NOW)
    assert v['state'] == 'fail' and v['head'] == 'Check:' and v['faults'] == [{'text': 'Objects: The broom is in his hand at 3.0 s and gone at 3.5 s.', 'at_s': 3.5}]
    assert v['by'].startswith('Claude looked at 13 frames of this take') and v['not_judged'] == 'Not judged: how things move between the frames. Play the take.' and len(v['passed']) == 8
    assert T.due(s, p, rows) == []


def test_a_passed_check_says_check_passed_and_a_measured_jump_is_a_fault_with_its_second(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide())
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    assert T.check_view(s, job('j1'), NOW)['head'] == 'Check passed' and T.check_view(s, job('j1'), NOW)['state'] == 'pass'
    s['take_checks'].update(j1=rec(look=look(), jump=1.1))
    v = T.check_view(s, job('j1'), NOW)
    assert v['state'] == 'fail' and v['faults'][0] == {'text': 'One continuous shot: the picture jumps to another view at 1.1 s. Measured by the server.', 'at_s': 1.1}


def test_the_frame_rate_24_over_1_is_read_as_24_and_a_jump_between_two_frames_fails_the_measured_line():
    assert GW.frame_rate('24/1') == 24.0 and GW.frame_rate('30000/1001') == pytest.approx(29.97, abs=0.01) and GW.frame_rate(None) == 24.0 and GW.frame_rate(25) == 25.0
    assert GW.continuous_line([]) == {'check': 'one continuous shot', 'weight': 'must', 'pass': True, 'pass_when': 'the clip is one shot from its first frame to its last: the picture never jumps to another view',
                                      'seen': 'no jump to another view'}
    line = GW.continuous_line([1.083, 4.04])
    assert line['pass'] is False and line['at_s'] == 1.1 and line['seen'] == 'the picture jumps to another view at 1.1 s and at 4.0 s'
    assert GW.blocked_by([line]) is None                                # marked on its line; the take is not set aside


# ---------- the page's line of a take ----------

def line_of(s, p, rows, **k):
    g, sh = p['gaps'][0], p['gaps'][0]['scenes'][0]['shots'][0]
    return T.line(None, s, p, g, sh, 1, len(g['scenes'][0]['shots']), rows, now=NOW, **k)


def test_a_take_line_has_the_fixtures_fields_and_no_amount_of_money(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    line, fx = line_of(s, p, [job('j1')]), FIXTURE['lines'][1]
    assert set(line) | {'line', 'key', 'item', 'state'} == set(fx) and set(line['takes'][0]) == set(fx['takes'][0]) and set(line['takes'][0]['check']) - {'short'} == set(fx['takes'][0]['check'])   # release 1, B3: the short line is new; the fixture is a round of 0.118.0
    assert [b['choice'] for b in line['buttons']] == ['select', 'again', 'reject'] == [b['choice'] for b in fx['buttons']]
    assert [b['label'] for b in line['buttons']] == ['Select', 'Make another', 'Reject'] and not line['buttons'][0]['needs_words']
    assert line['name'] == 'Housing at work' and line['where'] == 'In the film at 0:00.0 to 0:05.2 (5.2 s) · Housing at work'      # a shot with no title: the gap's title, never the id
    assert line['takes'][0]['short'] == '' and line['takes'][0]['in_s'] == 0.44                                             # the place sits in the middle of a guide take: (6.04 - 5.16) / 2
    assert '₹' not in json.dumps(line, ensure_ascii=False) and 'rupee' not in json.dumps(line).lower()
    assert '₹' not in json.dumps(T.PAGE, ensure_ascii=False) + json.dumps({k: v for k, v in T.W.items() if k not in ('ordered', 'order_log')}, ensure_ascii=False)   # the amount is said in the chat only


def test_a_shot_with_no_title_in_a_gap_of_several_is_named_by_the_gap_and_its_number(held):
    p = plan(shot('S1'), shot('S2', start=129, end=260, title='Mason pointing'))
    assert [T.name_of(g, sh, n, of) for g, sh, n, of in [(p['gaps'][0], sh, n, 2) for n, sh in enumerate(p['gaps'][0]['scenes'][0]['shots'], 1)]] == ['Housing at work, shot 1', 'Mason pointing']


def test_the_words_in_time_are_the_shots_words_with_seconds_from_its_start(held):
    s, p = session(), plan(shot('S1', end=40), shot('S2', start=40, end=260))
    held(s, p)
    g = p['gaps'][0]
    c1, c2 = T.caption(s, g, g['scenes'][0]['shots'][0]), T.caption(s, g, g['scenes'][0]['shots'][1])
    assert [w['t'] for w in c1['words']] == ['As', 'the', 'demand', 'grows,'] and c1['words'][0] == {'t': 'As', 's': 0.08, 'e': 0.32} and c1['pre'] == '' and c1['post'] == 'homes rise.'
    assert [w['t'] for w in c2['words']] == ['homes', 'rise.'] and c2['words'][0]['s'] == 0.08 and c2['pre'] == 'As the demand grows,' and c2['post'] == ''   # the rest of the sentence, greyed
    s['source']['gaps']['G1']['timing']['words'] = []
    assert T.caption(s, g, g['scenes'][0]['shots'][0]) is None                                                           # no words, or no times: the plain line


def test_selecting_against_a_failed_or_missing_check_is_one_click_with_no_typed_reason(held):   # release 1, B1 (SK, 20 Nov 2026): D6's typed reason is retired (design/35 row 276)
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(look=look(fail=('objects',))))
    held(s, p)
    b = line_of(s, p, [job('j1')])['buttons']
    assert not b[0]['needs_words'] and b[0]['hint'] == '' and b[0]['against'] is True
    assert b[1]['prefill'] == b[2]['prefill'] == 'Objects: The broom is gone at 3.5 s.' and b[1]['note'] == T.W['again_paid'] and b[2]['note'] == ''
    s['take_checks'].update(j1=rec(frames=0))
    assert not line_of(s, p, [job('j1')])['buttons'][0]['needs_words'] and line_of(s, p, [job('j1')])['buttons'][0]['against'] is True


def test_two_takes_of_a_shot_are_one_line_and_no_further_take_is_offered(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1', 'j2']))
    s['take_checks'].update(j1=rec(look=look()), j2=rec(look=look(fail=('people',))))
    s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'The helper looks at the camera.'}])
    held(s, p)
    line = line_of(s, p, [job('j1'), job('j2')])
    assert [(t['n'], t['tab'], t['rejected']) for t in line['takes']] == [(1, 'Take 1, rejected', 'Rejected. You said: The helper looks at the camera.'), (2, 'Take 2', '')]
    assert [(b['choice'], b['take']) for b in line['buttons']] == [('select', 2), ('reject', 2), ('old:1', 1)]                 # no "Make another": two were made from this camera
    assert line['buttons'][1]['note'] == T.W['no_more'] and line['buttons'][2]['sure'] == {'ask': 'You rejected take 1 earlier. Use it in the film after all?', 'go': 'Use take 1 after all', 'back': 'Go back'}
    s['take_checks'].update(j1=rec(look=look(fail=('objects',))))
    old = line_of(s, p, [job('j1'), job('j2')])['buttons'][2]
    assert not old['needs_words'] and old['sure']['ask'] == 'You rejected take 1 earlier, and its check did not pass. Use it in the film after all?'   # release 1, B1: asked once, no typed reason


def test_make_another_is_absent_when_the_cost_limit_would_be_passed(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    line = line_of(s, p, [job('j1')], left_inr=10.0, price_inr_per_s=20.0)
    assert [b['choice'] for b in line['buttons']] == ['select', 'reject'] and line['buttons'][1]['note'] == T.W['no_more_cap'] and '₹' not in line['buttons'][1]['note']


# ---------- the answers ----------

@pytest.fixture
def calls(monkeypatch):
    seen = []
    monkeypatch.setattr(V, 'review_take', lambda conn, store, user, run, outputs, jid, decision, notes, timing, quote: seen.append(('review', jid, decision, notes)) or {})
    monkeypatch.setattr(V, 'select_take', lambda conn, store, user, run, outputs, jid, quote, notes='', timing='', in_s=None: seen.append(('select', jid, notes)) or {'next': 'Take selected.'})
    return seen


def test_select_reject_and_use_the_earlier_take_call_the_chats_own_functions(held, calls):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1', 'j2']))
    s['take_checks'].update(j1=rec(look=look()), j2=rec(look=look(fail=('people',))))
    s['reviews'].update(j1=[{'decision': 'rejected', 'notes': ''}])
    held(s, p)
    rows = [job('j1'), job('j2')]
    T.answer(None, None, USER, RUN, {}, 'S1', rows, 'select', 'Select', 'His face is turned away; it reads fine.')
    assert calls == [('select', 'j2', 'His face is turned away; it reads fine.')]
    del calls[:]
    T.answer(None, None, USER, RUN, {}, 'S1', rows, 'reject', 'Reject', 'A second helper appears.')
    assert calls == [('review', 'j2', 'rejected', 'A second helper appears.')] and 'again' not in s['guides']['S1']
    del calls[:]
    T.answer(None, None, USER, RUN, {}, 'S1', rows, 'old:1', 'Use take 1 after all', '')
    assert calls == [('review', 'j1', 'accepted', ''), ('select', 'j1', '')]   # the earlier take is selected; the newer one gets no review (the second critic's point 4)
    with pytest.raises(ValueError):
        T.answer(None, None, USER, RUN, {}, 'S1', rows, 'old:7', 'x', '')


def test_make_another_rejects_the_take_and_keeps_the_operators_word_for_one_more(held, calls):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(look=look(fail=('objects',))))
    held(s, p)
    T.answer(None, None, USER, RUN, {}, 'S1', [job('j1')], 'again', 'Make another', 'He lays the broom on the sand.')
    assert calls == [('review', 'j1', 'rejected', 'He lays the broom on the sand.')]
    a = s['guides']['S1']['again']
    assert a['job_id'] == 'j1' and a['words'] == 'He lays the broom on the sand.' and a['by'] == 'u1' and not a.get('sent')
    s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'x'}])
    due = T.again_due(s, p, [job('j1')])
    assert 'the operator ordered another take on the page' in due and '`vw guide cause --shot S1' in due and '`vw guide shoot --shot S1`' in due and 'He lays the broom on the sand.' in due
    assert T.ordered(s, p, 20.0) == '1 new take is ordered: 6 s, about ₹120.'                                    # said in the chat after done, not asked
    with pytest.raises(ValueError):                                                                           # two were made from this camera: no third
        s['guides']['S1'] = guide(takes=['j0', 'j1'])
        s['reviews'].update(j0=[{'decision': 'rejected', 'notes': 'x'}], j1=[])
        T.answer(None, None, USER, RUN, {}, 'S1', [job('j0'), job('j1')], 'again', 'Make another', 'x y z')


def test_the_shoot_card_is_not_asked_again_once_make_another_gave_the_word(held, monkeypatch):
    s, p = session(), plan(shot('S1', title='Mason'))
    s['guides'].update(S1=guide(takes=['j1'], again={'job_id': 'j1', 'words': 'He lays the broom down.', 'by': 'u1'}))
    s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'x'}])
    held(s, p)
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run, sid=None: [job('j1')])
    monkeypatch.setattr(V, 'prices', lambda: {'video_inr_per_s': 20.0, 'image_inr': 4.0, 'usd_inr': 88.0})
    ctx = {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': USER, 'outputs': {}, 'conn': None}
    assert [i['kind'] for i in CF._guide_items(ctx)] == []
    del s['guides']['S1']['again']
    assert [i['kind'] for i in CF._guide_items(ctx)] == ['shoot']                                             # the first take, and a take after a plain Reject, keep their card


def test_a_cause_of_the_models_own_limit_drops_the_order(held, monkeypatch):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1'], again={'job_id': 'j1', 'words': 'x'}))
    s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'x'}])
    held(s, p)
    monkeypatch.setattr(G.generations, 'add', lambda *a, **k: None)
    out = G.set_cause(None, None, USER, RUN, {}, 'S1', 'model', 'It cannot hold the broom.', 'cut the shot')
    assert out['next'] == G.LADDER and 'again' not in s['guides']['S1']


# ---------- the round of the page, open and closed; the answers through the page ----------

def test_the_closed_page_says_the_counts_and_the_open_page_is_the_fixtures_shape(held, monkeypatch):
    s, p = session(), plan(shot('S1'))
    held(s, p)
    seven = [{'kind': 'take', 'id': 'S1', 'name': 'Housing at work', 'state': 'being made'}]
    closed = PF._takes_page({'session': s}, {'round': 'r1'}, None, seven)
    assert closed['step'] == FIXTURE['step'] == 'AI video' and closed['closed'] and not closed['open'] and closed['lines'] == [] and closed['say'] == 'AI video: 1 being made.'
    assert closed['note'] == 'The page opens when every take is made and checked.' and 'do not publish' in closed['how']
    lines = [{'key': 'pic:take:j1', 'item': 'take:j1', 'state': 'open', 'kind': 'take', 'name': 'Housing at work', 'takes': [{'check': {'passed': ['x' * 9000]}, 'details': [['How', ['y' * 9000]]]}], 'pics': [], 'buttons': [], 'details': []}]
    page = PF._takes_page({'session': {'page_refused': {'pic:take:j1': 'No.'}}}, {'round': 'r1'}, lines, [])
    assert page['layout']['kind'] == 'takes' and set(page['layout']) == set(FIXTURE['layout']) and set(page['layout']['words']['takes']) == set(FIXTURE['layout']['words']['takes'])
    assert page['lines'][0]['line'] == 'l01' and page['lines'][0]['refused'] == 'No.' and page['open'] and page['say'] == '1 take needs your answer:\n- Housing at work\nThen say done here.'
    big = [dict(lines[0], key=f'pic:take:{n}', takes=[{'check': {'passed': ['x' * 9000]}, 'details': [['How', ['y' * 9000]]]}]) for n in range(30)]
    cut = PF._takes_page({'session': {}}, {}, big, [])
    assert len(cut['lines']) == 30 and len(json.dumps(cut['lines'])) <= PF.ROUND_BYTES and cut['lines'][0]['takes'][0]['details']   # 30 shots: the details go first, never a line


def test_the_step_after_the_pictures_is_ai_video_and_step_6_keeps_its_own_lines(monkeypatch):
    s = session()
    p = plan(shot('S1'))
    ctx = {'session': s, 'plan': p, 'conn': None, 'run': RUN, 'store': None}
    monkeypatch.setattr(PF, '_spec_lines', lambda c: [])
    monkeypatch.setattr(CF, '_plan_items', lambda c: ([], []))
    monkeypatch.setattr(PF, '_drawing_lines', lambda c: [])
    monkeypatch.setattr(V, '_round_pass', lambda s_, rd: 'complete')
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run: [])
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    take = {'id': 'take:j1', '_line': {'kind': 'take', 'name': 'X', 'pics': [], 'takes': [], 'buttons': [], 'details': []}}
    still = {'id': 'picture:k1:aaaa', '_line': {'kind': 'still', 'name': 'Y', 'pics': [], 'buttons': [], 'details': []}}
    monkeypatch.setattr(CF, '_waiting_items', lambda c: [still, take])
    monkeypatch.setattr(T, 'recorded', lambda c: [])
    assert [l['key'] for l in PF._pictures_lines(ctx)] == ['pic:picture:k1:aaaa'] and [l['key'] for l in PF._takes_lines(ctx)] == ['pic:take:j1']
    assert PF._plan_step(ctx)[0] == 'pictures'                                             # a line of step 6 still waits: step 6 first
    monkeypatch.setattr(CF, '_waiting_items', lambda c: [take])
    step, (lines, seven) = PF._plan_step(ctx)
    assert step == 'takes' and lines is None and [i['state'] for i in seven] == ['not started']   # nothing made yet: the page is closed
    monkeypatch.setattr(T, 'complete', lambda items: True)
    assert [l['key'] for l in PF._plan_step(ctx)[1][0]] == ['pic:take:j1']
    monkeypatch.setattr(T, 'expected', lambda *a, **k: [])
    assert PF._plan_step(ctx)[0] == 'pictures'                                             # a film with no AI video: step 7 does not exist


def test_a_takes_video_copy_is_sent_for_every_take_of_a_line(monkeypatch):
    monkeypatch.setattr(PF, 'video_copy', lambda store, key, mark='': key + '.page.mp4')
    page = PF._with_videos(None, {'lines': [{'takes': [{'video': {'_key': 'a.mp4', '_mark': 'm1', 'code': '', 'label': 'Take 1', 'none': ''}}, {'video': {'_key': 'b.mp4', '_mark': 'm2', 'code': '', 'label': 'Take 2', 'none': ''}}]}]})
    codes = [t['video']['code'] for t in page['lines'][0]['takes']]
    assert all(c.startswith('v') and len(c) == 13 for c in codes) and codes[0] != codes[1] and [v['key'] for v in page['videos']] == ['a.mp4.page.mp4', 'b.mp4.page.mp4']


def test_the_words_of_the_page_come_from_the_server_and_the_old_ways_are_named():
    assert T.PAGE['done'] == {'select': 'Selected', 'reject': 'Rejected', 'again': 'Another ordered'} and T.PAGE['seek'] == 'Go to {s} s' and T.PAGE['check_pass'] == 'Check passed'
    assert T.PAGE['film'] == 'See it in the film' and T.PAGE['details'] == 'Details' and T.PAGE['change_in_chat'] == 'To change this answer, say so in the chat.'
    assert T.PAGE == FIXTURE['layout']['words']['takes']
    assert 'Gemini' not in json.dumps(T.W) and T.W['page_later'] == 'The page opens when every take is made and checked.'


# ---------- the served text, the old ways, the plugin ----------

ROOT = HERE.parents[1]


def test_the_served_text_says_the_new_order_and_the_replaced_sentences_are_retired():
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d222_wording_v3 as D
    import rel1a_wording as REL1A   # release 1, section A: step 7's still and the answer "na" come inside this script's sentences on a take's check
    v3 = json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    import rel1b_wording as REL1B   # release 1, B1 and D: "Select" loses its typed reason inside this script's sentence, and sentences are added after its two
    st = REL1A.before(REL1B.before(next(s for s in v3['stages'] if s['name'] == 'visuals')))
    later = next(p for p in st['parts'] if p['name'] == 'later')['text']
    assert D.CHECK_NEW in later and D.SHOOT_NEW in later and 'Gemini reads every ready take' not in later
    old = next(p for p in D.before(st)['parts'] if p['name'] == 'later')['text']
    assert D.CHECK_OLD in old and D.CHECK_NEW not in old and D.SHOOT_NEW not in old
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert all(s in retired for s in D.RETIRED) and not any(s in json.dumps(st, ensure_ascii=False) for s in D.RETIRED)
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('d221f(prompt, parts)') < split.index('d222(prompt, parts)')
    assert '₹' not in D.CHECK_NEW and 'vw-take-look' in D.CHECK_NEW and 'AI video: 11 made and checked, 4 being made.' in D.CHECK_NEW


def test_the_plugin_has_the_take_helper_and_says_where_step_7_is_answered():
    helper = (ROOT / 'plugin' / 'agents' / 'vw-take-look.md').read_text(encoding='utf-8')
    assert 'name: vw-take-look' in helper and 'model: opus' in helper and 'vw visuals pictures --looks' in helper and 'cannot play' in helper and 'at_s' in helper
    cmd = (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'the AI video and the recording are asked in the chat, one at a time' not in cmd
    assert 'the finished AI video takes are answered on the page' in cmd and 'vw-take-look' in cmd
    skill = (ROOT / 'plugin' / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'the take arrives with its scorecard; select or reject as for any take' not in skill and 'on the page' in skill and 'Make another' in skill
    tool = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "'quote': a.quote or ''" in tool and 'A take is paid for on the operator\'s word: `vw guide shoot --shot S --quote' not in tool   # the word given on the page ("Make another") needs no --quote: the server decides


def test_the_old_ways_are_in_the_decision_log():
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    for n, words in ((226, 'Gemini 3.8 Flash'), (227, 'one by one'), (228, 'Shoot card'), (229, 'the join'), (230, 'start picture'), (231, '24/1')):
        row = next((l for l in log.splitlines() if l.startswith(f'| {n} |')), '')
        assert words in row and ('**Retired' in row or '**Kept' in row), n


def test_a_take_with_no_word_at_all_is_refused_and_the_pages_word_stands_in_for_the_quote():
    with pytest.raises(ValueError, match="paid for on the operator's word"):
        G.word_for(guide(), '  ')
    assert G.word_for(guide(), 'Yes, shoot it.') == (None, 'Yes, shoot it.')
    order = {'job_id': 'j1', 'words': 'He lays the broom down.'}
    assert G.word_for(guide(again=order), '') == (order, 'Make another: He lays the broom down.')
    with pytest.raises(ValueError):                                     # the word is used once: the next take needs a new one
        G.word_for(guide(again={**order, 'sent': 'j2'}), '')
