"""VW-25 issues 7, 8 and 9 (SK, 25 Nov 2026), the page check: `plugin/pages/decisions.html` in a headless browser from a local copy, fed the
page document the server builds (no product server). A gap line of the treatment shows the words under the gap and its time in the film, open
and accepted; the Direction shows none. A drawing's line shows, above its parts, where it sits in the film, the words under it and what it
shows, under the drawing's name with its code. Narration is shown as text, never as markup. Skipped where Playwright or its browser is not
installed."""
import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import browser   # noqa: F401 (`browser` is the fixture)
from test_design209_pure import drawing, page
from test_fixset5_browser_pure import live
from test_vw25_visuals_words_pure import entry, quiet, spec_film, timed, treatment   # noqa: F401 (`quiet` is a fixture)

PAIRS = "[...document.querySelectorAll('#list .item')].map(b => ({title: b.querySelector('h2').textContent, pairs: [...b.querySelectorAll('dl.kv dt')].map(dt => [dt.textContent, dt.nextElementSibling.textContent])}))"


def test_a_gap_line_shows_the_words_and_the_time_open_and_accepted_and_the_direction_none(browser):
    gaps = {'G1': timed(0, 100, 'first <b>words</b> & more'), 'G2': timed(100, 150, '')}
    store, conn = treatment([entry('G1'), entry('G2')], gaps, accepted=('G1',))
    pg = live(browser, page(store, conn))
    blocks = pg.evaluate(PAIRS)
    by = {b['title'].split('. ', 1)[1]: b['pairs'] for b in blocks}
    assert by['Gap G1'][:2] == [['The words', 'first <b>words</b> & more'], ['In the film', '0:00.0 to 0:04.0 (4.0 s)']]   # accepted: still readable; as text
    assert by['Gap G2'][:2] == [['The words', 'none (no narration under this gap)'], ['In the film', '0:04.0 to 0:06.0 (2.0 s)']]
    assert not any(k in ('The words', 'In the film') for k, _ in by['The direction of the film'])
    assert pg.locator('#list b').count() == 0 and not pg.errors


def test_a_drawings_line_shows_where_it_sits_the_words_and_what_it_shows_above_its_parts(browser):
    store, conn = spec_film([drawing(depicts_note=None)], change=lambda plan: plan['gaps'][0]['scenes'][0]['shots'][0].update(depicts='the box and its lid'))
    d = page(store, conn)
    pg = live(browser, d)
    block = pg.evaluate(PAIRS)[0]
    assert block['title'].endswith('Shot G1-S1 (G1-S1)')                                   # the name, its code last
    assert block['pairs'][:2] == [['Voiceover', 'words'], ['Shows', 'the box and its lid']]
    body = pg.locator('#list .item .body').first.inner_text()
    where = d['lines'][0]['rows'][0][1]
    assert where.startswith('In the film at') and where in body
    assert body.index(where) < body.index('Voiceover') < body.index('Shows') < body.index(d['lines'][0]['ask'])   # above the parts and the question
    assert not pg.errors
