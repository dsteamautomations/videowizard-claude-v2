"""design/97, Release 3: the visuals page from the operator's seat (design/93 P, R, V, W, K, A2, A4, A5, L4, G3; O4)."""
from pathlib import Path

import pytest

from app import visuals_stage as VS
from test_design94_r1_pure import cheap, build, film, held, pic, refs   # noqa: F401  (cheap: the autouse price fixture)
from test_visuals_stage_pure import FakeConn, RUN, USER, saved, store_with
from test_batch89b_pure import SPEC

APP = Path(__file__).resolve().parents[1] / 'app' / 'templates'
PAGE = (APP / 'visuals.html').read_text(encoding='utf-8')
REVIEW = (APP / 'review.html').read_text(encoding='utf-8')


def take(job_id, shot, status='ready'):
    return {'id': job_id, 'unit': shot, 'run_id': 'run-1', 'provider': 'video', 'status': status, 'request': {'duration_seconds': 6}, 'error': None, 'cost': None,
            'result': {'key': f'run-1/visuals/takes/{job_id}.mp4', 'sha256': 's', 'evidence': {'duration_seconds': 6.0, 'timing_matches_placement': True}}}


# ---------- W1, W3, W4: what waits for the operator, with labels and links ----------

def test_waiting_lists_each_item_for_the_operator_in_film_order_with_its_label_and_link():
    doc, sess = film(references=refs(pic('K1', 'DG2', check={'lines': [], 'must_failed': []}), pic('S1', status='candidate', kind='sheet'),
                                     pic('M1', 'DG1', check_pending=True), *build()),   # M1 is being checked: not waiting yet
                     reuse_pending={'DG1': {'clip_id': 'c1'}})
    items = VS.waiting(sess, VS.current_plan(store_with(sess, doc), sess), 'VW-9', [take('j1', 'VS1'), take('j2', 'VS1', 'running')])
    labels = [i['label'] for i in items]
    assert labels[0] == 'Reference sheet · E1'
    assert 'Reuse · DG1' in labels and 'Graphics · AN1 · 3 states' in labels and 'Still · DG2' in labels and 'Drawing specs · 1 to approve' in labels and 'Take · VS1' in labels
    assert labels.index('Reuse · DG1') < labels.index('Graphics · AN1 · 3 states') < labels.index('Still · DG2') < labels.index('Take · VS1')   # film order
    by = {i['label']: i for i in items}
    assert by['Still · DG2']['link'] == '/runs/VW-9/visuals#pictures/DG2/K1' and by['Take · VS1']['link'] == '/runs/VW-9/visuals#takes/VS1/j1'
    assert by['Reference sheet · E1']['link'] == '/runs/VW-9/visuals#references/E1/S1' and by['Still · DG2']['step'] == 'pictures'
    assert not any('M1' in i['link'] for i in items) and sum(1 for i in items if i['label'].startswith('Take')) == 1


def test_a_sequence_waits_only_once_every_state_is_made():
    doc, sess = film(references=refs(*build()[:2]))
    assert not any(i['label'].startswith('Graphics') for i in VS.waiting(sess, VS.current_plan(store_with(sess, doc), sess), 'VW-9', []))


def test_the_page_view_and_status_carry_the_waiting_list():
    doc, sess = film(references=refs(pic('K1', 'DG1', check={'lines': [], 'must_failed': []})))
    store = store_with(sess, doc)
    assert [i['label'] for i in VS.page_view(FakeConn([]), store, RUN, [], 'VW-9')['waiting']] == ['Still · DG1', 'Drawing specs · 1 to approve']   # DG2's spec is not approved
    assert VS.status(FakeConn([]), store, RUN, [])['waiting'][0]['link'] == '/runs/VW-9/visuals#pictures/DG1/K1'


# ---------- A4: after each verdict, what happens next, with the film time ----------

def test_each_verdict_says_what_happens_next_with_the_film_time():
    doc, sess = film(references=refs(pic('K1', 'DG1'), pic('K2', 'DG1'), pic('V1', 'VS1'), *build()))
    store = store_with(sess, doc)
    assert VS.approve_reference(store, USER, RUN, [], 'K1', 'sha-K1', 'yes')['next'] == 'Approved: in the film at 0:00–0:10 (DG1).'
    assert VS.approve_reference(store, USER, RUN, [], 'K2', 'sha-K2', 'yes')['next'] == 'Approved: in the film at 0:00–0:10 (DG1); it replaces K1, which stays approved.'
    assert VS.reject_reference(store, USER, RUN, [], 'V1', 'too dark', 'too dark')['next'] == 'Rejected: the assistant makes a new start image with your note.'
    assert VS.sequence(store, USER, RUN, [], 'AN1', [], 'yes')['next'] == 'Sequence approved: in the film at 0:10–0:20 (AN1).'
    assert VS.unplace(store, USER, RUN, [], 'DG1', 'out')['next'] == 'Taken out of DG1: it stays approved.'


def test_the_film_time_reads_minutes_and_seconds():
    assert VS.film_time({'source': {'fps': '25'}}, {'start_frame': 1500, 'end_frame': 1625}) == '1:00–1:05'


# ---------- G3: the split per gap ----------

def test_each_gap_carries_its_split_by_route_on_the_page_and_in_check():
    doc, sess = film()
    view = VS.page_view(FakeConn([]), store_with(sess, doc), RUN, [], 'VW-9')
    g1 = next(g for g in view['gaps'] if g['gap_id'] == 'G1')
    assert g1['split'] == [{'route': 'graphics', 'seconds': 20.0, 'shots': 2}]
    g2 = next(g for g in view['gaps'] if g['gap_id'] == 'G2')
    assert g2['split'] == [{'route': 'graphics', 'seconds': 4.0, 'shots': 1}, {'route': 'AI video', 'seconds': 6.0, 'shots': 1}]
    assert VS.split_of([{'visual_type': 'image', 'start_frame': 0, 'end_frame': 50}], 25) == [{'route': 'still (moving)', 'seconds': 2.0, 'shots': 1}]   # design/112 K3


# ---------- the page (P, V, K, R, W, A2, A5, L4) and the review page (O4) ----------

@pytest.mark.parametrize('needle', [
    "$('s-pictures').innerHTML=split(", "$('s-takes').innerHTML=split(",   # P1, P2: the shared panel on the Pictures and Takes steps
    'class="act"', '@media (max-width:600px)',                             # P3: the words and buttons pinned on a phone
    'id="viewer"', "ev.key==='Escape'", "'wheel'", 'vw-in', 'vw-out',       # V1, V3: the viewer with zoom, pan, arrows and the panel
    'grid-template-columns:minmax(0,1fr) minmax(360px,45%)',               # V2: a wider panel
    '<details class="chkd">', ' passed',                                   # K1: the check in one line
    'sources (', 'show all (',                                             # R1, R2
    "location.hash", "hashchange", 'waiting for you', 'Next waiting', ' waiting for your verdict',   # W1, W3
    "'Reject state '",                                                     # A2: one Reject naming the step
    "'Approved · in the film at '",                                        # A5
    'highlightNamed',                                                      # L4
    "j.next",                                                              # A4
    "g.split",                                                             # G3
])
def test_the_page_carries_each_release_3_piece(needle):
    assert needle in PAGE, needle


def test_the_review_page_explains_its_buttons():
    assert ('Keep: use it. Reject: not this one (a reason is optional). Trim a shot: use it with a shot trimmed. A blue mark is a second choice: keep only one cut '
            'of a scene. Drop: leave the decision out.') in REVIEW   # design/98 R1; design/125 O1, O8
