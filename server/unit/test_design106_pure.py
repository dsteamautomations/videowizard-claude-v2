"""design/106 T1-T6 (VW-7, 26 Oct): a picture's role is said, not guessed (T1, T2); approving a start always makes its end (T2);
the server never places a take its words reject (T3); a camera that stays still is not a camera move (T6)."""
import json
from pathlib import Path

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design101_pure import take_store
from test_visuals_stage_pure import RUN, USER, FakeConn, g, ref, saved

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
END = {'status': 'ready', 'prompt': 'Image 1 is the start; the labourer now at the edge of the site.', 'checklist': [{'check': 'end', 'pass_when': 'at the edge', 'weight': 'must'}], 'exact_text': []}


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def start_store():
    """VS1 bound and its packet read, with an approved start K1 to revise."""
    store, _ = take_store()
    s = saved(store)
    s['bindings']['VS1']['packet_read_at'] = 't'
    s['references']['K1'] = {**ref('K1', 'approved'), 'kind': 'keyframe', 'shot_id': 'VS1'}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    return store


def revise_start(store, **over):
    body = {'request_id': 'r9', 'element_id': 'E1', 'name': 'keyframe-start-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer',
            'prompt': 'Image 1 is the old start; the labourer at the stack, the lane behind.', 'parents': ['K1', 'R1'], 'end_prompt': END['prompt'], 'end_answer': END, **over}
    return VS.generate_image(FakeConn([]), store, USER, RUN, [], body)


# ---------- T1, T2: the role is said ----------

def test_a_start_made_from_an_old_start_is_a_start_when_its_role_says_so():
    store = start_store()
    out = revise_start(store, role='start')
    row = saved(store)['references'][out['reference_id']]
    assert row['role'] == 'start' and row['pending_end']['prompt'] == END['prompt']
    with pytest.raises(Problem, match='An end prompt goes with a start keyframe'):   # without the role, a keyframe parent still means an end
        g(lambda: revise_start(start_store(), request_id='r10'))


def test_a_keyframe_records_its_role_and_the_page_reads_it():
    store = start_store()
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'r11', 'element_id': 'E1', 'name': 'end-VS1', 'kind': 'keyframe', 'shot_id': 'VS1',
                                                                'subject': 'the labourer', 'prompt': 'Image 1 is the start; the labourer at the edge.', 'parents': ['K1']})
    assert saved(store)['references'][out['reference_id']]['role'] == 'end'
    view = VS.page_view(FakeConn([]), store, RUN, [], 'VW-9')
    assert {r['id']: r.get('role') for r in view['references']}[out['reference_id']] == 'end'
    assert "r.role?r.role+' image'" in PAGE and "if(r.role)return r.role==='start'" in PAGE
    assert "live.filter(r=>picWord(r)===role+' image').pop()" in PAGE and "' earlier picture'" in PAGE   # T1: the latest start and end in view, the rest folded


# ---------- T2: approving a start always makes its end, and says so ----------

def approvable(store, rid):
    s = saved(store)
    s['references'][rid].update(status='candidate', sha256='a' * 64, width=1536, height=864, key=f'run-1/visuals/references/{rid}.png', bytes=9)
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    return store


def test_approving_a_revised_start_queues_its_end_and_names_the_job():
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    conn = FakeConn([])
    row = VS.approve_reference(approvable(store, rid), USER, RUN, [], rid, 'a' * 64, '', conn)
    assert row['end_reference_id'] and row['end_job_id'] == 'job-1' and len(conn.inserted) == 1
    assert 'end image queued' in row['next'] and 'job-1' in row['next'] and 'take' not in row['next']


def test_a_start_approved_without_an_end_prompt_never_names_the_take_as_next():
    store = start_store()
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'r12', 'element_id': 'E1', 'name': 'keyframe-start-VS1', 'kind': 'keyframe', 'shot_id': 'VS1',
                                                                'subject': 'the labourer', 'prompt': 'Image 1 is the old start; the labourer at the stack.', 'parents': ['K1'], 'role': 'start'})
    row = VS.approve_reference(approvable(store, out['reference_id']), USER, RUN, [], out['reference_id'], 'a' * 64, '', FakeConn([]))
    assert 'take' not in row['next'] and 'end image' in row['next']


# ---------- T3: the server never places a take its words reject ----------

def test_select_refuses_when_the_words_say_reject():
    store = start_store()
    with pytest.raises(Problem, match='vw visuals review --job'):
        g(lambda: VS.select_take(FakeConn([]), store, USER, RUN, [], 'j1', 'Reject this take: the bricks fall', notes=''))
    with pytest.raises(Problem, match='vw visuals review --job'):
        g(lambda: VS.select_take(FakeConn([]), store, USER, RUN, [], 'j1', '', notes='rejected: a cut at 2 s'))


# ---------- T6: a camera that stays still is not a camera move ----------

def test_the_camera_move_check_lets_a_still_camera_pass():
    for text in ('Image 1 is the start. The camera did not move; he sets the brick.', 'The camera stays still while he walks.', 'Locked off camera, he walks on.',
                 'No camera move: he walks to the house.', "The camera doesn't move at all.", 'A locked-off camera; the dust drifts.'):
        assert VS.camera_move(text) is None, text
    assert VS.camera_move('The camera pans left to the house.') == 'camera pans'
    assert VS.camera_move('A slow push in on the wall.') == 'push in'
