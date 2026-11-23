"""SK, 23 Nov 2026 (VW-25, plan of action Phase 4). On the review page the operator could not change a clip ("Find footage" was a dead end and a new
proposal cleared every answer), and a trim was typed in frames with a wrong hint and checked only when the master was built.
- Other clips: every shot and an all-AI scene list the server's ranked pieces; "Use this" records the swap as that row's answer. No other answer changes.
- Trim in seconds, checked when it is recorded, with what the shot can lose and gain; a scene out of balance is named, with the shots that can take the time.
- One flow, two front ends: the page and `vw master decide` call the same server function.
Older way kept until the next release: a trim in source frames ("in:±frames,out:±frames")."""
import json
from pathlib import Path

import pytest

from app.errors import Problem
from app.stage2 import review as R, stage as S
from test_design127_review_pure import USER, answer_all, decide, plan, saved, session_store
from test_review_page import FakeConn, RUN

SERVER = Path(__file__).resolve().parents[1]


def package_of(store):
    return json.loads(store.files['p'])


def put_package(store, pk):
    store.files['p'] = json.dumps(pk).encode('utf-8')


ROW = {'in_frame': 100, 'out_frame': 600, 'source_fps': '50', 'min_hold_s': 2.0, 'action_peak': {'in_frame': 300, 'out_frame': 350}}


# ---------- trim in seconds ----------

def test_seconds_become_the_clips_own_frames():
    assert R.seconds_edit('start:0.5,end:1', ROW) == 'in:25,out:-50'                     # start later by 0.5 s, end earlier by 1 s, at 50 frames a second
    assert R.seconds_edit('start:-0.3, end:0', {**ROW, 'source_fps': '25'}) == 'in:-8,out:0'   # a minus value lengthens; rounded to a whole frame
    assert R.seconds_edit('in:5,out:-5', ROW) is None                                     # the older way, in frames: passed through as it is
    assert R.edit_text('in:25,out:-50', ROW) == 'starts 0.5 s later, ends 1.0 s earlier' and R.edit_text('in:-25,out:0', ROW) == 'starts 0.5 s earlier'
    assert R.edit_text('in:0,out:0', ROW) == 'no change'


def test_the_card_says_what_a_shot_can_lose_and_gain():
    r = R.room(200, 450, ROW)                                                             # a 5 s shot; hold 2 s; main action 300-350; window 100-600
    assert (r['start_earlier'], r['start_later'], r['end_earlier'], r['end_later'], r['lose']) == (100, 100, 100, 150, 150)
    assert R.room_text(200, 450, ROW) == ('This shot: 5.0 s. It can lose up to 3.0 s (start up to 2.0 s later, end up to 2.0 s earlier). '
                                          'It can grow by up to 5.0 s (start up to 2.0 s earlier, end up to 3.0 s later).')
    tight = {**ROW, 'in_frame': 200, 'out_frame': 300, 'action_peak': None}
    assert R.room_text(200, 300, tight) == 'This shot: 2.0 s. It cannot get shorter. It cannot grow.'


def test_a_trim_is_checked_when_it_is_recorded_not_at_the_master():
    store = session_store()                                                               # shots of 75 frames at 25 a second; window 0-200; hold 1 s
    with pytest.raises(Problem, match=r'shorter than its hold 1.0 s.*This shot: 3.0 s. It can lose up to 2.0 s'):
        decide(store, '1.2', 'TRIM', 'start:1.5,end:1')
    with pytest.raises(Problem, match=r'outside its usable window.*It can grow by up to 5.0 s'):
        decide(store, '1.2', 'TRIM', 'start:-1,end:0')                                    # it starts at the first usable frame: it cannot start earlier
    assert '1.2' not in saved(store)['decisions']                                         # nothing recorded
    decide(store, '1.2', 'TRIM', 'start:0.2,end:-0.2')
    d = saved(store)['decisions']['1.2']
    assert (d['edit'], d['edit_text']) == ('in:5,out:5', 'starts 0.2 s later, ends 0.2 s later')
    view = S.slides_view(store, RUN)
    assert next(s for s in view['slides'] if s['slide'] == '1.2')['answer']['edit_text'] == 'starts 0.2 s later, ends 0.2 s later' and view['balance'] == []


def test_a_scene_out_of_balance_is_named_with_the_shots_that_can_take_the_time():
    store = session_store()
    answer_all(store, **{'1.2': ('TRIM', 'start:0,end:0.4')})                             # Scene 1 is now 10 frames (0.4 s) short
    out = S.slides_view(store, RUN)['balance']
    assert len(out) == 1 and out[0]['scene'] == 1 and out[0]['text'] == 'Scene 1 is 0.4 s short after the trim.'
    assert out[0]['takers'] == [{'slide': '1.2', 'title': 'Scene 1 · Shot 2', 'edit': 'in:0,out:0'}, {'slide': '1.3', 'title': 'Scene 1 · Shot 3', 'edit': 'in:0,out:10'}]
    with pytest.raises(Problem, match='240 frames'):
        S.build_master(FakeConn({}), store, USER, RUN)                                    # the master's check stays as the last safety net
    decide(store, '1.3', 'TRIM', out[0]['takers'][1]['edit'])                             # "Give 0.4 s to Shot 3"
    assert S.slides_view(store, RUN)['balance'] == []
    S.build_master(FakeConn({}), store, USER, RUN)
    assert sum(e['timeline_frames'] for e in plan(store)['events'] if e['beat_id'] == 'BEAT_01') == 250
    long = session_store()
    answer_all(long, **{'1.2': ('TRIM', 'start:0,end:-0.4')})
    assert S.slides_view(long, RUN)['balance'][0]['text'] == 'Scene 1 is 0.4 s long after the trim.'


# ---------- other clips and the swap ----------

def test_a_piece_is_fitted_to_the_shots_length_or_the_reason_is_said():
    assert R.fit_piece(ROW, 100, 25) == (225, 425, 100)                                   # 4 s of a 50-a-second clip: 200 frames, the main action in the middle
    assert R.fit_piece({**ROW, 'action_peak': None}, 100, 25) == (100, 300, 100)
    assert R.fit_piece(ROW, 300, 25) == 'it has 10.0 s of usable picture; the shot needs 12.0 s'
    assert R.fit_piece(ROW, 300, 25, partial=True) == (100, 600, 250)                     # an all-AI scene: the piece takes what it has, AI keeps the rest
    assert R.fit_piece(ROW, 25, 25) == 'it needs 2.0 s on screen to be understood; the shot has 1.0 s'
    assert R.fit_piece({**ROW, 'min_hold_s': 0.5, 'action_peak': {'in_frame': 200, 'out_frame': 400}}, 50, 25) == 'its main action takes 4.0 s; the shot has 2.0 s'
    assert R.fit_piece({**ROW, 'source_fps': '30'}, 101, 25) == "its frame rate (30 a second) does not divide this shot's length evenly"


def test_other_clips_are_the_ranked_pieces_with_what_each_needs_to_be_used():
    store = session_store()
    out = S.others(store, RUN, '1.3')
    assert out['slide'] == '1.3' and out['title'] == 'Scene 1 · Shot 3' and out['seconds'] == 3.0
    assert out['pieces'] == [] and out['empty'] == 'No other clip fits this scene.'   # the small film's pieces fit no scene
    assert S.others(store, RUN, '2.1')['empty'] == 'No clip fits this scene. Keep AI.'
    pk = package_of(store)
    pk['sub_clips'][4].update(fit_kinds={'BEAT_01': 'chapter'}, eligibility='ELIGIBLE_AS_IS', grade='A', what='A mason lays bricks.', process_stage='Laying')
    pk['sub_clips'][0].update(fit_kinds={'BEAT_01': 'chapter'}, eligibility='ELIGIBLE_AS_IS', grade='B')
    put_package(store, pk)
    got = S.others(store, RUN, '1.3')['pieces']
    assert [(p['sub_clip_id'], p['kind'], p['in_cut'], p['can']) for p in got] == [('c5:S', 'chapter', False, True), ('c1:S', 'chapter', True, False)]
    assert got[0]['chapter'] == 'Laying' and got[0]['grade'] == 'A' and got[0]['media']['key'] == 'run-1/media/C5.MP4' and got[1]['why'] == 'already in the cut'


def test_use_this_records_the_swap_as_the_rows_answer_and_changes_no_other_answer():
    store = session_store()
    pk = package_of(store)
    pk['sub_clips'][4].update(fit_kinds={'BEAT_01': 'chapter', 'BEAT_02': 'chapter'}, eligibility='ELIGIBLE_AS_IS', grade='A')
    put_package(store, pk)
    answer_all(store)
    before = saved(store)['decisions']
    out = S.decide(FakeConn({}), store, USER, RUN, '1.3', 'SWAP', '', None, 'c5:S')
    after = saved(store)['decisions']
    assert out['action'] == 'SWAP' and {k: v for k, v in after.items() if k != '1.3'} == {k: v for k, v in before.items() if k != '1.3'}
    assert after['1.3']['swap'] == {'sub_clip_id': 'c5:S', 'source_in_frame': 0, 'source_out_frame': 75, 'timeline_frames': 75, 'crop': 'full', 'match': 'b_roll', 'clip': 'C5.MP4'}
    S.build_master(FakeConn({}), store, USER, RUN)
    events = plan(store)['events']
    assert [e.get('sub_clip_id') for e in events][:3] == [None, 'c1:S', 'c5:S'] and events[2]['swapped_from'] == 'c2:S'
    with pytest.raises(Problem, match='already in the cut'):
        S.decide(FakeConn({}), store, USER, RUN, '3.1', 'SWAP', '', None, 'c1:S')
    with pytest.raises(Problem, match='SWAP needs the piece'):
        S.decide(FakeConn({}), store, USER, RUN, '3.1', 'SWAP', '', None, None)
    with pytest.raises(Problem, match='is not a piece of this film'):
        S.decide(FakeConn({}), store, USER, RUN, '3.1', 'SWAP', '', None, 'nope')


def test_find_footage_on_an_all_ai_scene_takes_a_piece_and_ai_keeps_the_rest():
    store = session_store()
    pk = package_of(store)
    pk['sub_clips'][4].update(fit_kinds={'BEAT_02': 'chapter'}, eligibility='ELIGIBLE_AS_IS', grade='A', out_frame=60)   # 2.4 s of picture for a 4 s scene
    put_package(store, pk)
    answer_all(store)
    S.decide(FakeConn({}), store, USER, RUN, '2.1', 'SWAP', '', None, 'c5:S')
    S.build_master(FakeConn({}), store, USER, RUN)
    scene = [(e['kind'], e.get('sub_clip_id'), e['timeline_frames']) for e in plan(store)['events'] if e['beat_id'] == 'BEAT_02']
    assert scene == [('event', 'c5:S', 60), ('gap', None, 40)]


def test_both_front_ends_reach_the_same_function():
    web = (SERVER / 'app' / 'web.py').read_text(encoding='utf-8')
    assert "if action == 'others':" in web and "stage2.others(store, run, body.get('slide'))" in web and "body.get('sub_clip_id') or None)" in web
    main = (SERVER / 'app' / 'main.py').read_text(encoding='utf-8')
    assert 'body.edit, body.sub_clip_id)' in main and "stage2.others(storage(), run, slide)" in main
    vw = (SERVER.parent / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "'sub_clip_id': a.sub" in vw and "base + '/others'" in vw
