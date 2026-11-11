"""Layer 2 of the approved test plan (videobuilder-v4/phase2/ui/requirements-and-test-plan.md, section 7): every screen state renders and
tells the truth. One test per check, run on every state under data/<VW_PAGE_DATA>/.

The assertions are the approved requirements (R6, R9, R10, E16, section 4), not today's behaviour: a failure here is a fault of the page.
"""
import re

import pytest

from conftest import LABEL, SIZES, STEPS, states

STATES = states()
each_state = pytest.mark.parametrize('state', STATES)

# What was opened by a link or by Next waiting, and whether the operator can act on it: a highlighted item or the open picture panel, with a live control in it.
LANDED = '''() => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const panel = document.getElementById('panel');
  const scope = [...document.querySelectorAll('.hl')].filter(vis).concat(panel && vis(panel) ? [panel] : []);
  const controls = scope.flatMap(s => [...s.querySelectorAll('button[data-a], input, textarea, select, [data-golden], [data-tick], #p-save')]).filter(e => vis(e) && !e.disabled);
  return {opened: scope.length, controls: controls.length};
}'''

PICTURES = '''async () => {
  const imgs = [...document.querySelectorAll('#app img')];
  await Promise.all(imgs.map(i => { i.loading = 'eager'; return i.decode().catch(() => {}); }));
  return imgs.filter(i => getComputedStyle(i).display !== 'none' && !(i.complete && i.naturalWidth > 0)).map(i => i.getAttribute('src') || '(no address)');
}'''

LAYOUT = '''() => {
  const W = document.documentElement.clientWidth, out = [];
  const inScroller = e => { for (let p = e.parentElement; p; p = p.parentElement) { if (/(auto|scroll)/.test(getComputedStyle(p).overflowX) && p.scrollWidth > p.clientWidth) return true; } return false; };
  for (const e of document.querySelectorAll('button, a, input, select, textarea, [data-golden], [data-tick]')) {
    const r = e.getBoundingClientRect();
    if (!r.width || !r.height || getComputedStyle(e).visibility === 'hidden') continue;
    const name = (e.innerText || e.id || e.name || e.tagName).trim().slice(0, 40);
    if ((r.right > W + 1 || r.left < -1) && !inScroller(e)) out.push(name + ' at ' + Math.round(r.left) + '-' + Math.round(r.right) + ' px');
    for (let p = e.parentElement; p; p = p.parentElement) {   // cut off by a box that hides what does not fit
      const q = p.getBoundingClientRect();
      if (/(hidden|clip)/.test(getComputedStyle(p).overflowX) && (r.right > q.right + 1 || r.left < q.left - 1)) { out.push(name + ' is cut off by its box'); break; }
    }
  }
  return {width: W, pageWidth: document.documentElement.scrollWidth, outside: out};
}'''


@each_state
def test_loads_without_script_or_console_errors(open_page, state):
    put = open_page(state)
    for tab in STEPS:   # every tab of the page is drawn once with this state's data
        put.open_tab(tab)
    put.open_tab(put.state['tab'])
    put.screenshot(f'{LABEL}--{state}')
    assert not put.js_errors, f'the page script threw: {put.js_errors}'
    assert not put.console_errors, f'the browser console shows errors: {put.console_errors}'
    assert not put.unstubbed, f'the page asked for something the harness does not know: {put.unstubbed}'
    if put.state.get('pictures') != 'missing':
        assert not put.failed_requests, f'requests failed: {put.failed_requests}'


@each_state
def test_nothing_is_blank(open_page, state):
    put = open_page(state)
    own = put.state['tab']
    assert put.page.inner_text('#line').strip(), 'the header line is empty'
    blank = []
    for tab in STEPS:
        put.open_tab(tab)
        if not put.section_text(tab):
            blank.append(tab)
        if tab == own:
            shown = put.page.locator(f'#s-{tab} .card, #s-{tab} table tr, #s-{tab} .empty, #s-{tab} .turn').count()
            assert shown, f'the {tab} tab shows neither a card nor a line saying what comes next'
            assert put.page.inner_text('#rcards').strip(), f'the left list of the {tab} tab is empty'
    assert not blank, f'blank tabs: {blank}'
    junk = re.findall(r'undefined|NaN|\[object Object\]', put.page.inner_text('#app'))
    assert not junk, f'the page prints {sorted(set(junk))} where a value should be'


@each_state
def test_counts_agree(open_page, state):
    """R6: the header, each tab and the cards marked as waiting count the same things."""
    put = open_page(state)
    header, tabs, wrong = put.header_count(), put.tab_counts(), []
    if header != sum(tabs.values()):
        wrong.append(f'the header says {header} waiting, the tabs add up to {sum(tabs.values())} {dict((k, v) for k, v in tabs.items() if v)}')
    for tab in STEPS:
        put.open_tab(tab)
        marked, chip = sum(c['waiting'] for c in put.cards()), put.waiting_chip()
        if not (tabs[tab] == marked == chip):
            wrong.append(f'{tab}: the tab says {tabs[tab]} waiting, {marked} cards carry the waiting mark, the filter says "Waiting for me ({chip})"')
    assert not wrong, '; '.join(wrong)


@each_state
def test_next_waiting_lands_on_something_actionable(open_page, state):
    """R9: Next waiting always lands on something the operator can act on, and never prints "no longer waiting"."""
    put = open_page(state)
    n = put.header_count()
    waiting = put.payload.get('waiting') or []
    if not n:
        assert not waiting, f'the data holds {len(waiting)} waiting items but the header offers no Next waiting'
        return
    wrong = []
    for k in range(n):
        put.clear_bar()
        put.click('#wnext')
        put.page.wait_for_timeout(80)
        label = waiting[k]['label'] if k < len(waiting) else f'item {k + 1}'
        landed = put.page.evaluate(LANDED)
        if put.red_line():
            wrong.append(f'"{label}": red line "{put.red_line()}"')
        elif not landed['opened']:
            wrong.append(f'"{label}": nothing was opened or outlined')
        elif not landed['controls']:
            wrong.append(f'"{label}": what opened has no control to act with')
    assert not wrong, 'Next waiting: ' + '; '.join(wrong)


@each_state
def test_every_inside_link_opens_something(open_page, state):
    """R10: every link the tool gives the operator opens the thing it names."""
    put = open_page(state)
    if put.header_count():
        put.click('#wcount')   # the waiting list, with its links
    dead = []
    for label, h in put.links():
        step = h.split('/')[0]
        put.go_hash(h)
        landed = put.page.evaluate(LANDED)
        if put.red_line():
            dead.append(f'"{label}" (#{h}): red line "{put.red_line()}"')
        elif put.active_tab() != step:
            dead.append(f'"{label}" (#{h}): the {step} tab did not open')
        elif '/' in h and not landed['opened']:
            dead.append(f'"{label}" (#{h}): nothing was opened or outlined')
    assert not dead, 'dead links: ' + '; '.join(dead)


@each_state
def test_every_picture_loads_or_shows_a_placeholder(open_page, state):
    """E16: a picture whose file is missing shows a plain placeholder, never a broken picture."""
    put = open_page(state)
    broken = {}
    for tab in STEPS:
        put.open_tab(tab)
        bad = put.page.evaluate(PICTURES)
        if bad:
            broken[tab] = f'{len(bad)} broken, the first: {bad[0]}'
    assert not broken, f'pictures neither loaded nor replaced by a placeholder: {broken}'


@each_state
@pytest.mark.parametrize('size', list(SIZES))
def test_layout_holds(open_page, state, size):
    """Section 4: the page works at the widths SK uses; no control off the screen, no sideways scrollbar."""
    put = open_page(state, size=size)
    got = put.page.evaluate(LAYOUT)
    assert got['pageWidth'] <= got['width'], f'at {size} the page is {got["pageWidth"]} px wide in a {got["width"]} px window: it scrolls sideways'
    assert not got['outside'], f'at {size} controls are outside the window: {got["outside"][:5]}'
