"""design/217, the critic's review (18 Nov 2026) of e545154..a3ab2c6: five faults, one wording fault and the video copy's size, each with its test.
Without a database: the session is held in memory (the server tests' pieces)."""
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import chat_flow as CF, page_flow as PF, pictures as P, visuals_stage as V
from test_design217_server_pure import RUN, USER, all_pass, held, plan, ref, session, shot   # noqa: F401 (`held` is a fixture)

NOW = datetime.now(timezone.utc)
OLDER = {'lines': [{'check': 'the people', 'pass': False, 'weight': 'must', 'seen': 'three workers'}], 'must_failed': [{'check': 'the people'}], 'model': 'gemini-3.8-flash'}


# ---------- 1: the 30 minutes count from when Claude was first asked ----------

def test_1_a_paused_film_is_not_offered_as_not_checked_and_asking_stamps_asked_at_once(held):
    box = held(session(ref('k1', ready_at=(NOW - timedelta(days=1)).isoformat())), plan(shot('S1')))
    r = box['s']['references']['k1']
    assert not P.offered(box['s'], r, box['p'])                        # made a day ago, the laptop closed: still waits for Claude
    out = P.looks_due(None, RUN, [])
    first = box['s']['references']['k1']['asked_at']
    assert [x['ref'] for x in out['pictures']] == ['k1'] and first and not P.offered(box['s'], box['s']['references']['k1'], box['p'])
    assert P.waits_words(box['s'], box['p']) == P.LOOKS_DUE.format(n=1) and box['s']['references']['k1']['asked_at'] == first   # asked once: the first time counts
    s2 = session(ref('k2', shot_id='S1'))
    assert P.waits_words(s2, plan(shot('S1'))) and s2['references']['k2']['asked_at']     # `next` and `status` ask too


# ---------- 2: pictures the model checked before the deploy stay offered ----------

def test_2_a_picture_checked_by_the_model_before_the_deploy_is_offered_with_that_check_and_its_chat_item_still_answers(held, monkeypatch):
    old = ref('k1', check=OLDER)
    box = held(session(old, ref('k2', shot_id='S2', check_pending=True)), plan(shot('S1'), shot('S2')))
    s, p = box['s'], box['p']
    assert P.older(old) and P.offered(s, old, p) and [r['id'] for r in P.due(s, p)] == ['k2']   # only the one still waiting for the model goes to Claude
    assert P.stamp(s, p) and 'ready_at' not in s['references']['k1'] and s['references']['k2']['ready_at']
    v = P.check_view(s, old, p)
    assert v['state'] == 'fail' and v['by'] == P.W['by_older'].format(n=1) and v['faults'] == ['the people: three workers.']
    monkeypatch.setattr(V, 'route_of', lambda sh: 'still')
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run: [])
    monkeypatch.setattr(V, '_set_budget', lambda *a: None)
    monkeypatch.setattr(V, 'visuals_spend', lambda *a: 0)
    got = []
    monkeypatch.setattr(V, 'approve_reference', lambda store, user, run, outputs, rid, sha, quote, conn=None: got.append(rid) or {})
    ctx = {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': USER, 'outputs': [], 'conn': None}
    item = next(i for i in CF._waiting_items(ctx) if i['id'] == f"picture:k1:{'a' * 10}")   # the id handed out in the chat before the deploy
    item['_run']('yes', 'Yes', '')
    assert got == ['k1']


# ---------- 3: the step-7 parent question reads Claude's failed lines ----------

def test_3_a_parent_approved_against_claudes_check_still_raises_the_parent_question():
    look = {'sha256': 'a' * 64, 'lines': [{'id': '1', 'check': 'the people', 'pass': False, 'seen': 'three distant workers, not two'}]}
    p = ref('k1', status='approved', look=look)
    assert V.parent_failed(session(p), p) == ['the people: three distant workers, not two.']
    assert V.parent_failed(session(ref('k2', status='approved', look={**look, 'lines': []})), ref('k2', status='approved', look={**look, 'lines': []})) == []
    o = ref('k3', status='approved', check=OLDER)
    assert V.parent_failed(session(o), o) == ['the people'] and V.parent_failed(session(o, v=1), ref('k4', status='approved', check=OLDER)) == ['the people']


# ---------- 5: a failed component is said plainly, never silent ----------

def test_5_a_failed_component_is_named_with_its_lines_and_advice_never_decides(held):
    c1 = ref('c1', 'component', None, element_id='BRICK')
    c2 = ref('c2', 'component', None, element_id='MORTAR')
    c2['check']['code'].append({'check': 'transparency', 'pass': False, 'seen': 'the background is 2% opaque', 'advice': True})
    box = held(session(c1, c2), plan(shot('S1')))
    want = lambda rid: P.lines(box['s'], box['p'], box['s']['references'][rid])
    first = want('c1')[0]
    bad = [{**l, 'pass': False, 'seen': 'a shadow falls outside its edge'} if l['id'] == first['id'] else l for l in all_pass(want('c1'))]
    out = P.record_looks(None, USER, RUN, [], [{'ref': 'c1', 'sha10': 'a' * 10, 'lines': bad}, {'ref': 'c2', 'sha10': 'a' * 10, 'lines': all_pass(want('c2'))}], 'assistant')
    refs = box['s']['references']
    assert refs['c1']['status'] == 'candidate' and refs['c2']['status'] == 'approved'           # the advice line (transparency) did not hold c2 back
    said = P.W['comp_failed'].format(name='c1', ref='c1', lines=f"{first['check']}: a shadow falls outside its edge.", element='BRICK')
    assert said in out['then'] and said in P.waits_words(box['s'], box['p'])                    # in the look's answer and in what `next` and `status` say
    refs['c1']['look'] = {**refs['c1']['look'], 'lines': [], 'not_checked': 'the file did not open'}
    assert P.W['comp_unopened'].format(why='the file did not open') in P.waits_words(box['s'], box['p'])


# ---------- 6: the wording; the chat's question as the page says it ----------

def test_6_no_free_in_the_render_sentence_and_the_chat_question_has_no_amount(held, monkeypatch):
    text = Path(V.__file__).read_text(encoding='utf-8')
    assert 'frames on the server, free:' not in text and 'frames on the server: HyperFrames' in text
    box = held(session(ref('k1')), plan(shot('S1')))
    box['s']['questions'] = {'k1': {'question': 'Make a new picture (about ₹4.2) or use this one?', 'choices': ['make a new picture (₹4.2)', 'use this one'], 'fork': 'not_yet'}}
    monkeypatch.setattr(V, 'route_of', lambda sh: 'still')
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run: [])
    monkeypatch.setattr(V, '_set_budget', lambda *a: None)
    monkeypatch.setattr(V, 'visuals_spend', lambda *a: 0)
    ctx = {'session': box['s'], 'plan': box['p'], 'run': RUN, 'store': None, 'user': USER, 'outputs': [], 'conn': None}
    item = next(i for i in CF._waiting_items(ctx) if i['kind'] == 'question')
    assert '₹' not in item['question'] + str(item['buttons']) + item['text'] and [b['label'] for b in item['buttons']] == [b['label'] for b in item['_line']['buttons']]
    got = []
    monkeypatch.setattr(V, 'answer', lambda store, user, run, outputs, it, words: got.append(words) or {})
    item['_run']('c1', 'Make a new picture', '')
    assert got == ['make a new picture (₹4.2)']                                                  # the server still records the choice as it asked it


# ---------- the video copy over the page's file limit: the frames, with the sentence ----------

def test_a_video_copy_over_the_page_limit_shows_the_frames_with_its_sentence(monkeypatch):
    class Store(dict):
        get = lambda self, k: b'mp4'
        put = lambda self, k, d, t: self.__setitem__(k, d)
        exists = lambda self, k: k in self

    def ffmpeg(cmd, **k):
        Path(cmd[-1]).write_bytes(b'\0' * (V.OWN_PICTURE_MAX + 1))
    monkeypatch.setattr(subprocess, 'run', ffmpeg)
    store = Store()
    page = PF._with_videos(store, {'lines': [{'kind': 'drawn', 'video': {'_key': 'run-1/takes/big.mp4', '_mark': 'x', 'code': '', 'label': 'l', 'none': ''}}]})
    assert page['lines'][0]['video']['code'] == '' and page['lines'][0]['video']['none'] == P.W['video_none'] and 'videos' not in page and not store
