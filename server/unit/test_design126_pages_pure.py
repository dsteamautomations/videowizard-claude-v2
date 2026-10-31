"""design/126 U1-U7, the users' page issues: both pages' scripts parse, the page items are on the pages, and a picture saved on its own
(U3) adds to the earlier saves of its search instead of replacing them."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app import visuals_stage as VS
from test_design121_pure import round_store, searched, web  # noqa: F401  (web is a fixture)
from test_visuals_stage_pure import RUN, USER, saved

TEMPLATES = Path(__file__).resolve().parents[1] / 'app' / 'templates'
REVIEW = (TEMPLATES / 'review.html').read_text(encoding='utf-8')
VISUALS = (TEMPLATES / 'visuals.html').read_text(encoding='utf-8')


@pytest.mark.parametrize('page', ['review.html', 'visuals.html'])
def test_the_page_script_parses(page):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is not installed here')
    html = (TEMPLATES / page).read_text(encoding='utf-8')
    script = re.search(r'<script>\s*(\(function\(\)\{.*?\}\)\(\);)\s*</script>', html, re.S).group(1)
    assert '{{' not in script and '{%' not in script and '{#' not in script, 'Jinja would rewrite the script'
    out = subprocess.run([node, '-e', 'new Function(require("fs").readFileSync(0, "utf8"))'], input=script, capture_output=True, text=True, encoding='utf-8')
    assert out.returncode == 0, out.stderr


def test_u1_the_review_list_follows_the_film_but_not_while_typing():
    assert "if(el&&!typing)el.scrollIntoView({block:'nearest'})" in REVIEW and 'typing=' in REVIEW and "$('slides').contains(ae)" in REVIEW


def test_u2_to_u7_are_on_the_visuals_page():
    for needle in ('.v2 .pclose{', 'position:sticky;top:0;background:var(--card)', 'overflow-x:hidden',                     # U2
                   'id="p-save"', 'The note is saved with the picture.', 'function savePick', "action:'pick',search_id:sid,picks:[{n:p.n",  # U3
                   'data-sview=', 'function openSearchViewer', 'img[data-sview]{cursor:zoom-in}',                            # U4
                   'two to twelve words', 'n>=2&&n<=12',                                                                    # U5
                   'function supplyBox', 'selPic.supply', 'data-a="supply-open"', 'roundOpen()&&can?supplyBox(s.element_id)',  # U6
                   'function usedIn', '<b>Used in</b>', 'usedIn(eid)', 'usedIn(e.id)'):                                     # U7
        assert needle in VISUALS, needle
    assert 'two to six' not in VISUALS.lower() and '.length>6' not in VISUALS


def test_u3_a_picture_saved_on_its_own_keeps_the_earlier_saves_of_its_search(web):  # noqa: F811
    store = round_store()
    searched(store, 'E1')
    sid = saved(store)['round']['elements']['E1']['search_ids'][0]
    VS.pick(store, USER, RUN, [], sid, [{'n': 1, 'note': 'keep the bond'}], '')
    VS.pick(store, USER, RUN, [], sid, [{'n': 3}], '')
    VS.pick(store, USER, RUN, [], sid, [{'n': 1, 'note': 'keep the bond'}], '')      # saved twice: listed once
    s = saved(store)['searches'][sid]
    assert s['picked'] == [1, 3]
    webs = {r['source']['n']: r for r in saved(store)['references'].values() if r['kind'] == 'web' and r['source']['search_id'] == sid}
    assert sorted(webs) == [1, 3] and all(r['status'] == 'approved' for r in webs.values())
    assert webs[1]['source']['note'] == 'keep the bond'
    assert saved(store)['round']['elements']['E1']['search_ids'][0] == sid
