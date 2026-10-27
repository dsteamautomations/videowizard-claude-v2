"""Code review of 27 Oct 2026, group A: the pictures and takes path. A fix keeps its parent's role (visuals 1); an end needs a start (visuals 2);
an approval never discards a pending correction (visuals 3); the chat status shows corrections (visuals 4); the camera-move check matches only a
camera that moves (checks 1); a still ambient line asks for no movement (checks 2); the page keeps what the operator typed across a redraw (page 1);
a broken picture falls back to the full file (page 2)."""
import json
import types
from pathlib import Path

import pytest

from app import image_check as IC, visuals_stage as VS, web
from app.errors import Problem
from app.video_providers import motion_text
from test_design101_pure import snapshot
from test_design106_pure import END, approvable, revise_start, start_store
from test_design106d_pure import spec_store
from test_design91_b1_pure import Video
from test_visuals_stage_pure import RUN, USER, FakeConn, FakeStore, g, ref, saved

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
FAILED = {'check': 'cavity', 'pass_when': 'the cavity shows', 'weight': 'must'}


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


# ---------- visuals 1: a fix of a start is a start ----------

def test_a_fix_keeps_the_role_and_the_end_prompt_of_the_picture_it_fixes():
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    ref = saved(approvable(store, rid))['references'][rid]
    body = IC.fix_body(ref, FAILED)
    assert body['role'] == 'start' and body['end_prompt'] == ref['pending_end']['prompt'] == END['prompt'] and body['end_answer'] == END
    fix = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    row = saved(store)['references'][fix['reference_id']]
    assert row['role'] == 'start' and row['fix_of'] == rid and row['pending_end']['prompt'] == END['prompt']
    assert VS._picture_word(store, saved(store), row) == 'start image'
    assert 'role' not in IC.fix_body({**ref, 'kind': 'state', 'role': None}, FAILED)   # a state has no role


# ---------- visuals 2: an end always follows its start ----------

def test_an_end_without_a_start_parent_is_refused():
    store = start_store()
    s = saved(store)
    s['references']['S1'] = {**ref('S1', 'approved'), 'kind': 'sheet'}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    with pytest.raises(Problem, match='An end image is made from its start'):
        g(lambda: revise_start(store, role='end', parents=['S1'], prompt='Image 1 is the start; the labourer at the edge.', end_prompt=None, end_answer=None))


# ---------- visuals 3: an approval never discards a correction that waits ----------

def test_approving_a_spec_with_a_pending_correction_is_refused_until_the_spec_changes():
    store = spec_store()
    VS.correct_spec(store, USER, RUN, [], 'DG1', 'the cavity is 50 mm, not unknown')
    with pytest.raises(Problem, match='waits for the assistant'):
        g(lambda: VS.approve_spec(store, USER, RUN, [], 'DG1', ''))
    out = VS.approve_specs(store, USER, RUN, [], '')
    assert out['approved'] == [] and out['waiting'] == ['DG1']
    s = saved(store)
    assert s['spec_corrections']['DG1']['words'] == 'the cavity is 50 mm, not unknown' and 'DG1' not in s.get('spec_approvals', {})
    assert not [w for w in VS.waiting(s, VS.current_plan(store, s), 'VW-9', []) if w.get('item') == 'specs']   # nothing for the operator: the assistant's turn
    s['spec_corrections']['DG1']['digest'] = 'an older spec'   # the assistant revised the spec
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    assert [r['shot_id'] for r in VS.approve_specs(store, USER, RUN, [], '')['approved']] == ['DG1']
    assert 'DG1' not in saved(store).get('spec_corrections', {})


# ---------- visuals 4: the chat path sees a correction ----------

def test_the_status_carries_the_pending_corrections():
    store = spec_store()
    assert VS.status(FakeConn([]), store, RUN, [], repair=False)['spec_corrections'] == {}
    VS.correct_spec(store, USER, RUN, [], 'DG1', 'the cavity is 50 mm')
    st = VS.status(FakeConn([]), store, RUN, [], repair=False)
    assert st['spec_corrections'] == {'DG1': 'the cavity is 50 mm'}
    assert 'spec_corrections' in (ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8')


# ---------- checks 1: only a camera that moves is a camera move ----------

def test_the_camera_move_check_ignores_things_that_move_near_the_word_camera():
    for text in ('Same camera as Image 1, the worker has moved the brick to the wall.', 'Camera at eye level, the worker moves the trowel.',
                 'The camera holds on the pan of mortar.', 'Camera unchanged, a truck on the track behind.', 'The same framing, camera and light; the mason has moved on.'):
        assert VS.camera_move(text) is None, text
    for text, hit in (('The camera pans left to the house.', 'camera pans'), ('The camera slowly pushes in.', 'camera slowly pushes'), ('Camera tracks him along the wall.', 'Camera tracks'),
                      ('The camera moves right.', 'camera moves'), ('A slow push in on the wall.', 'push in'), ('Then a pan left across the yard.', 'pan left')):
        assert VS.camera_move(text) == hit, text


# ---------- checks 2: a still ambient line asks for nothing to move ----------

def test_a_still_ambient_line_adds_no_motion_sentence_and_no_must_line(monkeypatch, tmp_path):
    assert motion_text(snapshot(ambient='still: nothing else moves')) == motion_text(snapshot())
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: 'k')))
    video_path = tmp_path / 'output.mp4'
    video_path.write_bytes(b'mp4')
    rec = IC.run_take_check({'motion_prompt': 'm', 'ambient': 'Still: nothing else moves.'}, video_path, 'a' * 64, Video)
    assert len(rec['lines']) == 6 and 'ambient line' not in json.dumps(Video.payload)


# ---------- page 1: what the operator typed survives a redraw ----------

def test_the_page_keeps_typed_notes_and_corrections_across_a_redraw():
    assert "document.querySelectorAll('textarea.keep').forEach(t=>typed[t.id]=t.value)" in PAGE
    assert 'id="ref-note" class="pnote keep"' in PAGE and 'id="sp-c-\'+id+\'" class="words keep"' in PAGE
    assert "Object.entries(typed).forEach(([id,v])=>{const t=$(id);if(t&&v)t.value=v;})" in PAGE


# ---------- page 2: a broken picture falls back to the full file ----------

def test_a_picture_pillow_cannot_read_is_served_the_usual_way_not_a_500():
    class Store(FakeStore):
        def signed_download(self, key):
            return 'https://files.example/' + key
    store = Store()
    key = 'run-1/visuals/references/K9.png'
    store.files[key] = b'not a png'
    resp = web.thumb_response(store, 'run-1', key, None)
    assert resp.status_code == 307 and key + '.thumb.jpg' not in store.files
