"""design/100: saved picks arrive approved (S1, S2); the panel's buttons always in view, its details folded (S3, S4)."""
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app import visuals_stage as VS
from test_design94_r1_pure import cheap, film   # noqa: F401  (cheap: the autouse price fixture)
from test_visuals_stage_pure import FakeConn, RUN, store_with

USER = {'id': 'u1', 'name': 'SK'}
PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def png():
    buf = BytesIO()
    Image.new('RGB', (64, 64), 'red').save(buf, 'PNG')
    return buf.getvalue()


def picked(quote='', used='image'):
    doc, sess = film()
    store = store_with(sess, doc)
    plan = VS.current_plan(store, sess)
    sid = VS._search_into(sess, USER, RUN, plan, 'E1', 'rat trap wall', 'yes', results=[{'n': 1, 'image_url': 'https://x/1.png', 'title': 'a wall'}])['search_id']
    out = VS._pick_into(store, sess, USER, RUN, plan, sid, [{'n': 1, 'note': 'the bond'}], quote, fetched={(sid, 1): (png(), (64, 64), used)})
    return store, sess, out['references'][0]


def test_a_saved_pick_arrives_approved_with_its_hash():
    store, sess, row = picked()
    assert row['status'] == 'approved' and row['approval']['quote'] == 'Approved when saved by SK' and row['approval']['sha256'] == row['sha256'] and row['approval']['by'] == 'u1'
    store, sess, row = picked('These two, the side from the second.')
    assert row['approval']['quote'] == 'These two, the side from the second.'


def test_a_saved_pick_can_still_be_rejected_and_says_when_it_came_from_a_thumbnail():
    store, sess, row = picked(used='thumbnail')
    VS.save_session(store, RUN, sess)
    out = VS.reject_reference(store, USER, RUN, [], row['id'], 'not the picture I ticked', '')
    assert out['status'] == 'rejected'
    view = {r['id']: r for r in VS.page_view(FakeConn([]), store, RUN, [], 'VW-9')['references']}
    assert view[row['id']]['from_thumbnail'] is True


@pytest.mark.parametrize('needle', [
    'max-height:calc(100vh - 210px)', 'overflow:auto',             # S3: the panel fits the window and scrolls inside
    '.v2 .panel .act{position:sticky;bottom:0',                    # S3: the buttons pinned to its bottom
    '.v2 .panel img{max-height:50vh',                              # S3: the picture at most half the window
    '<details class="pdet"><summary>Details</summary>',            # S4: the rest folded
    'saved from the thumbnail: check it',                          # S2
])
def test_the_page_keeps_the_panels_buttons_in_view(needle):
    assert needle in PAGE, needle
