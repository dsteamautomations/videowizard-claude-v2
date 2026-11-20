"""Release 1, section A (A5): the page as it is published today (`plugin/pages/decisions.html`, not changed by this part of the release) draws
a round whose check blocks carry the new field `na` (the lines that did not apply) and `who`: it ignores them, shows the check line as before
and raises no error. The page's own fold "N lines did not apply" is another part of the release. Skipped where Playwright is not installed."""
import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import browser   # noqa: F401 (the fixture)
import test_design217_browser_pure as B6
import test_design222_browser_pure as B7

NA = {'head': '2 lines did not apply', 'lines': ['wear: A drawn graphic has no worn surface.', 'practitioner: No person is in this view.']}


def test_step_6_draws_a_check_that_carries_the_lines_that_did_not_apply(browser):
    def change(lines, d):
        for l in lines.values():
            if l.get('check'):
                l['check'].update(na=NA, who='model')
    pg = B6.page(browser, B6.doc(change))
    for l in (B6.BUILDING, B6.KILN, B6.STEPS, B6.WALL):
        B6.go(pg, l)
        assert l['check']['head'] in pg.locator('#smain').text_content() and pg.locator('#pbar button').count() >= 2
    assert pg.errors == []
    pg.close()


def test_step_7_draws_a_take_whose_check_carries_them(browser):
    def change(lines, d):
        for l in lines.values():
            for t in l.get('takes') or []:
                t['check'].update(na=NA)
    pg = B7.page(browser, B7.doc(change))
    B7.go(pg, B7.ONE)
    c = pg.locator('#pcheck')
    assert c.text_content() == 'Check passed' and c.get_attribute('data-state') == 'pass'
    B7.go(pg, B7.TWO)
    assert pg.locator('#pcheck').get_attribute('data-state') == 'fail' and pg.errors == []
    pg.close()
