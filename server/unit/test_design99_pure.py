"""design/99: the visuals page, full control: one click needs no typed words; Reject with an optional reason; search and picks say what is saved."""
import inspect
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app import visuals_stage as VS
from app.errors import Problem
from test_design94_r1_pure import build, cheap, film, held, pic, refs   # noqa: F401  (cheap: the autouse price fixture)
from test_visuals_stage_pure import RUN, g, saved, store_with

USER = {'id': 'u1', 'name': 'SK'}
PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def test_a_click_records_who_and_when_and_words_are_kept_when_given():
    assert VS.said('', 'Approved', USER) == 'Approved by SK' and VS.said('  ', 'Removed', USER) == 'Removed by SK'
    assert VS.said('Yes, that one.', 'Approved', USER) == 'Yes, that one.'


def test_approving_a_picture_a_sequence_and_placing_or_removing_need_no_words():
    doc, sess = film(references=refs(pic('K1', 'DG1'), *build()))
    store = store_with(sess, doc)
    out = VS.approve_reference(store, USER, RUN, [], 'K1', 'sha-K1', '')
    assert out['placed'] == 'DG1' and saved(store)['references']['K1']['approval']['quote'] == 'Approved by SK'
    VS.sequence(store, USER, RUN, [], 'AN1', [], '')
    assert saved(store)['assets']['AN1']['quote'] == 'Approved by SK'
    VS.unplace(store, USER, RUN, [], 'DG1', '')
    assert saved(store)['unplaced'][-1]['quote'] == 'Removed by SK'
    VS.still_from_reference(store, USER, RUN, [], 'DG1', 'K1', '')
    assert saved(store)['assets']['DG1']['quote'] == 'Placed by SK'


def test_a_reject_needs_no_reason_and_a_reason_given_after_is_added():
    doc, sess = film(references=refs(pic('K1', 'DG1')))
    store = store_with(sess, doc)
    VS.reject_reference(store, USER, RUN, [], 'K1', '', '')
    row = saved(store)['references']['K1']
    assert row['status'] == 'rejected' and row['rejection']['notes'] == '' and row['rejection']['quote'] == 'Rejected by SK'
    out = VS.reject_reference(store, USER, RUN, [], 'K1', 'text wrong; framing', '')
    assert saved(store)['references']['K1']['rejection']['notes'] == 'text wrong; framing' and out['next'].startswith('Rejected')
    with pytest.raises(Problem, match='not a candidate or approved'):
        g(lambda: VS.reject_reference(store, USER, RUN, [], 'K1', '', ''))   # a second reject without a reason changes nothing


def test_the_search_and_the_pick_need_no_words():
    doc, sess = film()
    plan = VS.current_plan(store_with(sess, doc), sess)
    out = VS._search_into(sess, USER, RUN, plan, 'E1', 'rat trap wall', '', results=[{'n': 1, 'image_url': 'https://x/1.png', 'title': 'a wall'}])
    assert sess['searches'][out['search_id']]['quote'] == 'Searched by SK'
    buf = BytesIO()
    Image.new('RGB', (64, 64), 'red').save(buf, 'PNG')
    store = store_with(sess, doc)
    got = VS._pick_into(store, sess, USER, RUN, plan, out['search_id'], [{'n': 1}], '', fetched={(out['search_id'], 1): (buf.getvalue(), (64, 64), 'image')})
    assert got['references'] and sess['searches'][out['search_id']]['picked'] == [1]


def test_the_round_needs_no_words_and_the_page_wide_steps_still_do():
    for fn in (VS.round_done, VS.round_picks, VS.select_take, VS.review_take):
        assert 'words are required' not in inspect.getsource(fn) and 'reply is required' not in inspect.getsource(fn), fn.__name__
    for fn, needle in ((VS.correct_footage, 'words are required'), (VS.revise_gap, 'reply is required'), (VS.approve_reuse, 'words approving the reuse are required')):
        assert needle in inspect.getsource(fn), fn.__name__


def test_the_api_takes_a_click_without_words():
    from app import main as M
    for model, extra in ((M.ReferenceApprove, {'sha256': '0' * 64}), (M.StillBody, {'shot_id': 'S', 'reference_id': 'R'}), (M.SequenceBody, {'shot_id': 'S'}),
                         (M.ReferenceReject, {}), (M.SearchBody, {'element_id': 'E1', 'keywords': 'a wall'}), (M.PickBody, {'search_id': 's', 'picks': [{'n': 1}]}),
                         (M.RoundDone, {'verdicts': {}}), (M.RoundPicks, {'picks': {}}), (M.TakeSelect, {'job_id': '00000000-0000-0000-0000-000000000001'}),
                         (M.UnplaceBody, {'shot_id': 'S'})):
        assert model(request_id='00000000-0000-0000-0000-000000000002', **extra).quote == '', model.__name__
    with pytest.raises(Exception):
        M.ReuseApprove(request_id='00000000-0000-0000-0000-000000000002', shot_id='S')   # a reuse keeps the operator's words (design/89 H7)


# ---------- the page ----------

@pytest.mark.parametrize('needle', [
    'id="p-close"', "title=\"Close (Esc)\"",                       # C1: the panel's × and Esc
    "selPic?'<div class=\"split\"><div>'",                         # C1: no panel column when nothing is open
    'What was wrong? (optional)', 'wrong subject', 'not like the footage', 'data-rchip',   # C3
    'ticked · not saved', ' ticked · not saved yet', "'Save '+", 'Saved ✓', 'beforeunload',   # C5
    ' pictures found for ',                                        # C4
    "'saving…'",                                                   # C7
])
def test_the_page_carries_each_design_99_piece(needle):
    assert needle in PAGE, needle


def test_the_panel_asks_no_words_for_a_click():
    assert 'placeholder="your words for this picture"' not in PAGE and "Your words for this picture go in the box above the button." not in PAGE
    assert "Your yes to the web search goes in the box at the foot." not in PAGE and 'your yes at the foot' not in PAGE
