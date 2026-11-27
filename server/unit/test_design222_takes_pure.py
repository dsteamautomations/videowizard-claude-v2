"""design/222 (SK, 19 Nov 2026): step 7, AI video, on the decisions page. The finished takes are judged on the page, all together, once every take
is made and checked; Claude checks each take from frames (Gemini 3.8 Flash no longer watches it); "Make another" on the page is the operator's
word for one more take; the words spoken during the shot are sent with their seconds. Without a database."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app import chat_flow as CF, guide as G, guide_worker as GW, page_flow as PF, pictures as P, takes as T, visuals_stage as V
from test_visuals_stage_pure import CURRENT   # release 1 of 27 Nov 2026, part B: a hand-built job is of the plan in force

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
            'request': {'kind': 'take', 'request_key': f'run-1/visuals/takes/{jid}.request.json', 'duration_seconds': 6, 'shot_print': CURRENT, **req},
            'result': {'key': f'run-1/visuals/takes/{jid}.mp4', 'sha256': sha, 'bytes': 1, 'evidence': {'duration_seconds': 6.04, 'timing_matches_placement': True}} if status == 'ready' else {}}


def rec(look=None, jump=None, blocked=None, frames=13, **more):
    """A take's record as the worker leaves it. design/223: only its frames every half second and the sheet: nothing is measured on a take, nothing
    is set aside and Claude gives no look (`look`, `jump` and `blocked` are taken and ignored, for the tests written before it)."""
    return {'guide': True, 'frames': [{'at_s': n * 0.5, 'key': f'f/{n}.jpg'} for n in range(frames)], 'sheet_key': 'f/sheet.jpg' if frames else None, **more}


def look(fail=(), sha=SHA, **more):
    """design/223: a take has no look."""
    return None


def guide(sha='g' * 64, drawing='approved', still='approved', prompt=True, takes=(), **more):
    return {'sha256': sha, 'key': 'k', 'seconds': 6, 'drawing': {'status': drawing, 'sha256': sha}, 'verdicts': [{'sha256': sha, 'pass': True}], 'render': {'status': 'ready', 'guide_key': 'g.mp4', 'frame1_key': 'f1.png', 'sha256': 'r'},
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


# ---------- the page's line of a take ----------

def line_of(s, p, rows, **k):
    g, sh = p['gaps'][0], p['gaps'][0]['scenes'][0]['shots'][0]
    return T.line(None, s, p, g, sh, 1, len(g['scenes'][0]['shots']), rows, now=NOW, **k)


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


# ---------- the answers ----------

@pytest.fixture
def calls(monkeypatch):
    seen = []
    monkeypatch.setattr(V, 'review_take', lambda conn, store, user, run, outputs, jid, decision, notes, timing, quote: seen.append(('review', jid, decision, notes)) or {})
    monkeypatch.setattr(V, 'select_take', lambda conn, store, user, run, outputs, jid, quote, notes='', timing='', in_s=None: seen.append(('select', jid, notes)) or {'next': 'Take selected.'})
    return seen


# ---------- the round of the page, open and closed; the answers through the page ----------


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


# ---------- the served text, the old ways, the plugin ----------

ROOT = HERE.parents[1]


def test_the_old_ways_are_in_the_decision_log():
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    for n, words in ((226, 'Gemini 3.8 Flash'), (227, 'one by one'), (228, 'Shoot card'), (229, 'the join'), (230, 'start picture'), (231, '24/1')):
        row = next((l for l in log.splitlines() if l.startswith(f'| {n} |')), '')
        assert words in row and ('**Retired' in row or '**Kept' in row), n
