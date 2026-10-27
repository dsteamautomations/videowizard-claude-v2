"""Defect 28 (VW-7): the client's-own check reads only the picture's own shot; an end image that cannot be made leaves the start approved and says why;
the page approves one state of an unfinished sequence, and names a video shot's pictures start or end."""
from pathlib import Path

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, gap_digest, g, plan_doc, ref, saved, session, shot, store_with

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
END = {'status': 'ready', 'prompt': 'Image 1 is the start; the labourer now at the edge of the site.', 'checklist': [{'check': 'end', 'pass_when': 'at the edge', 'weight': 'must'}], 'exact_text': []}


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def two_shots():
    """E1 in VS1 alone, and in VS2 beside the client's own wall, whose footage frame is approved (VW-7: LABOURER in B01_S1, and beside RTB_WALL elsewhere)."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1000, 'video', subjects=[]), shot('VS2', 1000, 1150, 'video', subjects=[], element_ids=['E1', 'WALL'])])
    doc['elements'].append({'id': 'WALL', 'name': "The client's rat-trap wall", 'kind': 'object', 'identity': 'exact', 'requirements': 'courses of equal height'})
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'S1': {**ref('S1', 'approved'), 'kind': 'sheet'}, 'F1': {**ref('F1', 'approved'), 'kind': 'frame', 'element_id': 'WALL'}},
                   bindings={sid: {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'S1', 'sha256': 'sha-S1'}]}, 'packet_read_at': 't'} for sid in ('VS1', 'VS2')})
    return doc, sess


def start_body(sid='VS1', **over):
    return {'request_id': 'r1', 'element_id': 'E1', 'name': 'keyframe-start-' + sid, 'kind': 'keyframe', 'shot_id': sid, 'subject': 'the labourer', 'prompt': 'Image 1 is the sheet: take identity. The labourer walks the lane',   # design/111 F21
            'parents': ['S1'], 'end_region': {'left': 0.1, 'top': 0.2, 'width': 0.5, 'height': 0.5}, **over}   # design/112 S2: the end's region with the start


def test_the_clients_own_check_reads_only_the_pictures_own_shot():
    doc, sess = two_shots()
    out = VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], start_body())   # VS1 shows no client material
    assert out['op'] == 'edit'
    with pytest.raises(Problem, match="WALL is the client's own"):   # VS2 does: the check still holds there
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], start_body('VS2')))


def approved_start(doc, sess, end_prompt):
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], start_body(end_prompt=end_prompt, end_answer={**END, 'prompt': end_prompt}))
    s2 = saved(store)
    s2['references'][out['reference_id']].update(status='candidate', sha256='a' * 64, width=1536, height=864, key=f"run-1/visuals/references/{out['reference_id']}.png", bytes=9)
    return store_with(s2, doc), out['reference_id']


def test_approving_a_start_makes_its_end_although_the_element_is_beside_client_material_in_another_shot():
    """VW-7: approving B01_S1's start was refused for RTB_WALL, a wall in other LABOURER shots."""
    doc, sess = two_shots()
    store, sid = approved_start(doc, sess, END['prompt'])
    conn = FakeConn([])
    row = VS.approve_reference(store, USER, RUN, [], sid, 'a' * 64, '', conn)
    assert row['status'] == 'approved' and row['end_reference_id'] and len(conn.inserted) == 1
    assert saved(store)['references'][row['end_reference_id']]['shot_id'] == 'VS1'


def test_an_end_that_cannot_be_made_leaves_the_start_approved_and_says_why_and_approving_again_retries():
    doc, sess = two_shots()
    store, sid = approved_start(doc, sess, 'Image 1 is the start; a slow push in on the labourer.')   # the end moves the camera: refused when it is made
    row = VS.approve_reference(store, USER, RUN, [], sid, 'a' * 64, '', FakeConn([]))
    assert row['status'] == 'approved' and not row.get('end_reference_id')
    assert 'the end image was not made' in row['next'] and 'moves the camera' in row['next']
    s = saved(store)
    assert s['references'][sid]['status'] == 'approved' and not s['references'][sid].get('end_queued') and s['references'][sid]['pending_end']
    s['references'][sid]['pending_end'] = {'prompt': END['prompt'], 'answer': END, 'region': {'left': 0.1, 'top': 0.2, 'width': 0.5, 'height': 0.5}}   # the assistant writes the end again (with its region, design/112 S2); approving the start again makes it
    conn = FakeConn([])
    row = VS.approve_reference(store_with(s, doc), USER, RUN, [], sid, 'a' * 64, '', conn)
    assert row['end_reference_id'] and len(conn.inserted) == 1


def test_the_page_approves_one_state_of_an_unfinished_sequence():
    """VW-7 B03B_S3: state 1 of 2 had no Approve; state 2 is made from the approved state 1."""
    i = PAGE.index("sh.route==='graphic_sequence'&&['keyframe','state'].includes(r.kind)")
    block = PAGE[i:PAGE.index("sh.route==='video'&&r.kind==='keyframe'", i)]
    assert "'Approve state '+idx" in block and "r.status==='candidate'" in block


def test_the_page_names_a_video_shots_pictures_start_or_end():
    """VW-7 B01_S1: two start candidates side by side read as a start and an end."""
    i = PAGE.index("sh.route==='video'&&r.kind==='keyframe'")
    assert 'picWord(x)' in PAGE[i:i + 600]
    assert "The start and end images:" not in PAGE and 'picWord(r)' in PAGE[PAGE.index('function renderTakes'):]
    assert 'click a picture to see it large, approve or reject it' in PAGE
