"""design/95: Release 1's review fixes (F1-F10)."""
from pathlib import Path

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design94_r1_pure import build, film, held, image, pic, refs   # noqa: F401  (cheap: the autouse price fixture)
from test_design94_r1_pure import cheap   # noqa: F401
from test_visuals_stage_pure import FakeConn, RUN, USER, g, saved, store_with

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


# ---------- F1: a fix stands in for its original; F2: pictures made from a rejected one leave the order ----------

def test_a_fix_stands_in_for_its_original_and_rejecting_it_brings_the_original_back():
    fix = pic('BF', 'AN1', kind='state', parents=['B'], fix_of='B', name='state-TITLE-b-fix')
    doc, sess = film(references=refs(*build(fix)))
    store = store_with(sess, doc)
    VS.sequence(store, USER, RUN, [], 'AN1', [], 'Yes, the build.')
    assert [st['reference_id'] for st in saved(store)['assets']['AN1']['states']] == ['A', 'BF', 'C']
    doc, sess = film(references=refs(*build({**fix, 'status': 'rejected'})))
    store = store_with(sess, doc)
    VS.sequence(store, USER, RUN, [], 'AN1', [], 'Yes, the build.')
    assert [st['reference_id'] for st in saved(store)['assets']['AN1']['states']] == ['A', 'B', 'C']


def test_pictures_made_from_a_rejected_state_leave_the_order():
    a, b, c = build()
    doc, sess = film(references=refs({**a, 'status': 'rejected'}, pic('A2', 'AN1', name='keyframe-TITLE-a2'), b, c))
    with pytest.raises(Problem, match=r'AN1 plans 3 states; its pictures make 1: keyframe-TITLE-a2\.'):
        g(lambda: VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', [], 'yes'))


# ---------- F3: a filled still shot still shows a new picture made for it ----------

def test_the_page_view_names_the_picture_in_the_shot():
    doc, sess = film(references=refs(pic('K1', 'DG1', 'approved'), pic('K2', 'DG1')), assets={'DG1': held('K1')})
    view = VS.page_view(FakeConn([]), store_with(sess, doc), RUN, [], 'VW-9')
    shot = next(s for gap in view['gaps'] for s in gap['shots'] if s['shot_id'] == 'DG1')
    assert shot['asset']['reference_id'] == 'K1'


def test_the_page_shows_new_pictures_for_a_filled_shot_and_says_where_an_approval_went():
    assert 'A new picture for this shot · approving replaces the one in the shot' in PAGE and 'j.next' in PAGE
    assert 'Remove the sequence to rebuild it' in PAGE


# ---------- F4, F10: the video box counts its own pictures; an empty title is left out ----------

def test_a_video_shot_counts_only_its_own_pictures_and_an_empty_title_is_left_out():
    assert PAGE.count("ownPic(r,s)") >= 2 and "const ownPic=(r,s)=>r.shot_id===s.shot_id||(!r.shot_id&&s.element_ids.includes(r.element_id));" in PAGE
    assert "(shotTitle(r.shot_id)?' · '+esc(shotTitle(r.shot_id)):'')" in PAGE


# ---------- F5: the plugin's version on every call ----------

def test_an_old_or_silent_plugin_is_refused_on_every_api_call_except_meta_auth_and_connect():
    from app.main import plugin_refusal
    assert 'update it and restart Claude Code' in plugin_refusal('/api/runs', None, '0.40.0')
    assert '(0.39.0)' in plugin_refusal('/api/runs/x/visuals/still', '0.39.0', '0.40.0')
    assert plugin_refusal('/api/runs', '0.40.0', '0.40.0') is None and plugin_refusal('/api/runs', '0.41.2', '0.40.0') is None
    for path in ('/api/meta', '/api/auth/me', '/api/connect', '/api/connect/abc/approve', '/runs/VW-7/visuals', '/runs/VW-7/visuals/act'):
        assert plugin_refusal(path, None, '0.40.0') is None, path


def test_the_minimum_is_this_releases_plugin():
    from app.config import Settings
    import json
    plugin = json.loads((Path(__file__).resolve().parents[2] / 'plugin' / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))
    v = lambda t: tuple(int(x) for x in t.split('.'))
    assert v('0.40.0') <= v(Settings.model_fields['PLUGIN_MIN_VERSION'].default) <= v(plugin['version'])   # design/98: raised only when the procedure needs the new plugin


# ---------- F6, F7, F9 ----------

def test_h5_names_the_shot_suggests_a_return_and_how_to_take_it_out():
    doc, sess = film(references=refs(pic('K1', 'DG1', 'approved')), assets={'DG1': held('K1')})
    with pytest.raises(Problem, match=r'already in DG1\. Two shots never show the same picture: compose another \(a reimagined shot, return_of, for a return\), '
                                      r'or take it out there first: `vw visuals unplace --shot DG1`'):
        g(lambda: VS.still_from_reference(store_with(sess, doc), USER, RUN, [], 'DG2', 'K1', 'yes', move='move it'))


def test_a_picture_naming_another_shot_than_its_parents_is_warned():
    doc, sess = film(references=refs(pic('K1', 'DG1', status='approved')))
    out = image(store_with(sess, doc), parents=['K1'], prompt='Image 1 is the start; the cavities now show.', shot_id='DG2')
    assert any('made from K1, which was made for DG1; this picture is listed and checked under DG2' in w for w in out['warnings'])


def test_approving_the_same_picture_twice_keeps_it_in_its_shot():
    doc, sess = film(references=refs(pic('K1', 'DG1')))
    store = store_with(sess, doc)
    VS.approve_reference(store, USER, RUN, [], 'K1', 'sha-K1', 'yes')
    out = VS.approve_reference(store, USER, RUN, [], 'K1', 'sha-K1', 'yes, again')
    assert out['placed'] == 'DG1' and 'replaced' not in out and saved(store)['assets']['DG1']['reference_id'] == 'K1'
