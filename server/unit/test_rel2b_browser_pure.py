"""Release 2, B2 (SK, 20 Nov 2026, answer 4), the page's left list: `plugin/pages/decisions.html` in a headless browser with the frozen
rounds of step 5 (reference sets), step 6 (pictures and drawn graphics) and step 7 (takes).

The name of a row keeps the full width of the row. A state is shown by the small badge only, in the place of the number: the number while
unanswered, the tick once answered or selected, "!" once approved against the check. No state word stands beside the name ("Selected",
"Against the check", "Approved" and the rest are gone from the row); the badge (or its row) carries the words as its title and aria-label;
the item's own view on the right still says them.
The fit: page areas of 1536 x 510 and 1900 x 830, light and dark: every name's box is the row's inner width less the badge; a long name
wraps on no more lines than it needs at that width; no scroll of the page.
Skipped where Playwright or its browser is not installed."""
import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import answers, browser   # noqa: F401 (`browser` is the fixture)
import test_design216_browser_pure as B5
import test_design217_browser_pure as B6
import test_design222_browser_pure as B7
from test_rel1b_browser_pure import now6, now7

LONG = 'Compression zone, tension zone and the idle concrete between them, seen from below the slab'
SIZES = ['fit-small', 'fit-large']
SCHEMES = ['light', 'dark']

ROWS = """(() => { const c = document.createElement('canvas').getContext('2d');
  return [...document.querySelectorAll('#srail .srow')].filter(r => r.querySelector('.sdot')).map(r => {
    const n = r.querySelector('.snm'), d = r.querySelector('.sdot'), s = getComputedStyle(r), ns = getComputedStyle(n), first = n.firstChild;
    const inner = r.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
    c.font = ns.font;
    const range = document.createRange(); range.selectNodeContents(first);
    return {line: r.dataset.line, name: first.textContent, badge: d.textContent, words: d.title || r.title, label: d.getAttribute('aria-label') || r.getAttribute('aria-label'),
            beside: [...r.children].filter(e => e !== n && e !== d).map(e => e.textContent), state: r.querySelectorAll('.sst').length,
            width: n.getBoundingClientRect().width, room: inner - d.getBoundingClientRect().width - parseFloat(s.columnGap || 0),
            lines: Math.round(range.getBoundingClientRect().height / parseFloat(ns.lineHeight)), needs: Math.ceil(c.measureText(first.textContent).width / n.getBoundingClientRect().width)};
  }); })()"""


def rows(pg):
    return {r['line'] or r['name']: r for r in pg.evaluate(ROWS)}


def fits(pg, where):
    """Every row with a badge: the name on the full width, no state word beside it, a long name on no more lines than it needs; no page scroll."""
    got = rows(pg)
    assert got, where
    bad = []
    for r in got.values():
        checks = {'a state word beside the name': r['state'] == 0 and r['beside'] == [],                     # nothing in the row but the badge and the name
                  'a squeezed name': r['width'] >= r['room'] - 1,                                            # the row's inner width less the badge
                  'more lines than it needs': r['lines'] <= r['needs'] + 1,                                  # one more at most: a line breaks at a word
                  'no state words on the badge': bool(r['words']) and r['words'] in (r['label'] or '')}      # for a pointer and a screen reader
        bad += [(what, r['name'], round(r['width']), round(r['room']), r['beside']) for what, ok in checks.items() if not ok]
    assert not bad, (where, bad)
    assert pg.evaluate('(() => { const d = document.documentElement; return d.scrollHeight <= innerHeight + 1 && d.scrollWidth <= innerWidth; })()'), where
    return got


def long6(lines, d):
    now6(lines, d)
    lines['l04']['name'] = LONG


# ---------- step 6: pictures and drawn graphics ----------

@pytest.mark.parametrize('scheme', SCHEMES)
@pytest.mark.parametrize('size', SIZES)
def test_step_6_a_name_keeps_the_rows_width_and_the_badge_alone_says_the_state(browser, size, scheme):
    pg = B6.page(browser, B6.doc(long6), size=size, scheme=scheme)
    W = B6.W
    got = fits(pg, 'nothing answered')
    assert got['l04']['badge'] == '4' and got['l04']['words'] == W['todo'] and got['l04']['name'] == LONG   # the number while unanswered
    B6.go(pg, B6.BUILDING)
    pg.locator('#pbar [data-choice="yes"]').click()                                                          # a still that passed
    B6.saved(pg, 'l03', 'yes')
    B6.go(pg, dict(B6.KILN, name=LONG))
    pg.locator('#pbar [data-choice="yes"]').click()                                                          # a still with warnings: one click, against the check
    B6.saved(pg, 'l04', 'yes')
    B6.go(pg, B6.WALL)
    pg.locator('#pbar [data-choice="select"]').click()                                                       # a drawn graphic whose check did not pass
    B6.saved(pg, 'l07', 'select')
    B6.go(pg, B6.CAVITIES)
    pg.locator('#pbar [data-choice="select"]').click()                                                       # a drawn graphic that passed: "Selected" squeezed the name
    B6.saved(pg, 'l06', 'select')
    got = fits(pg, 'four answered')
    assert [got[k]['badge'] for k in ('l03', 'l04', 'l06', 'l07')] == ['✓', '!', '✓', '!']
    yes = W['done'][B6.btn(B6.BUILDING, 'yes')['act']]
    assert got['l03']['words'] == yes and got['l06']['words'] == W['done']['select'] and got['l04']['words'] == got['l07']['words'] == W['against']
    rail = pg.locator('#srail > ul:first-of-type').inner_text()
    assert W['against'] not in rail and W['done']['select'] not in rail and yes not in rail                  # no state word in the list
    B6.go(pg, dict(B6.KILN, name=LONG))
    assert '(' + W['against'] + ')' in pg.locator('#sanswer').text_content()                                 # the words stay in the item's own view
    assert got['l04']['lines'] > 1 and pg.errors == []                                                       # the long name wrapped, on the full width
    pg.close()


def test_step_6_undo_puts_the_number_back(browser):
    pg = B6.page(browser, B6.doc(now6))
    B6.go(pg, B6.KILN)
    pg.locator('#pbar [data-choice="yes"]').click()
    B6.saved(pg, 'l04', 'yes')
    B6.go(pg, B6.KILN)
    pg.locator('#sundo').click()
    pg.wait_for_function('() => !window.__answers.l04')
    r = rows(pg)['l04']
    assert r['badge'] == '4' and r['words'] == B6.W['todo'] and pg.errors == []
    pg.close()


# ---------- step 5: reference sets ----------

@pytest.mark.parametrize('scheme', SCHEMES)
@pytest.mark.parametrize('size', SIZES)
def test_step_5_a_set_approved_against_the_advice_shows_the_mark_and_no_words(browser, size, scheme):
    pg = B5.page(browser, size=size, scheme=scheme)
    W = B5.W
    fits(pg, 'nothing answered')
    B5.go(pg, B5.MASON)
    pg.locator('#smain [data-act="approve"]').click()                                                        # with the advice
    pg.wait_for_function('l => !!window.__answers[l]', arg=B5.MASON['line'])
    B5.go(pg, B5.DECK)
    pg.locator('#smain [data-act="approve"]').click()
    pg.locator('#ssure').click()                                                                             # against the advice, asked once
    pg.wait_for_function('l => !!window.__answers[l]', arg=B5.DECK['line'])
    got = fits(pg, 'two answered')
    mason, deck = got[B5.MASON['line']], got[B5.DECK['line']]
    assert (mason['badge'], mason['words']) == ('✓', W['done']['approve']) and (deck['badge'], deck['words']) == ('!', W['against'])
    rail = pg.locator('#srail > ul:first-of-type').inner_text()
    assert W['against'] not in rail and W['done']['approve'] not in rail and pg.errors == []
    pg.close()


# ---------- step 7: takes (the list was built this way; pinned here) ----------

@pytest.mark.parametrize('scheme', SCHEMES)
@pytest.mark.parametrize('size', SIZES)
def test_step_7_the_same_list(browser, size, scheme):
    pg = B7.page(browser, B7.doc(now7), size=size, scheme=scheme)
    W = B7.W
    fits(pg, 'nothing answered')
    B7.go(pg, B7.TWO)
    pg.locator('#pbar [data-choice="select"]').click()                                                       # take 2 failed its check: against it
    B7.saved(pg, 'l01', 'select')
    B7.go(pg, B7.ONE)
    pg.locator('#pbar [data-choice="select"]').click()
    B7.saved(pg, 'l02', 'select')
    got = fits(pg, 'two answered')
    assert (got['l01']['badge'], got['l01']['words']) == ('!', W['against']) and (got['l02']['badge'], got['l02']['words']) == ('✓', W['done']['select'])
    assert pg.errors == []
    pg.close()
