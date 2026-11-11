"""Small helpers shared by the layer 1 and layer 3 tests."""
import re

import pytest

from conftest import REV, STEPS   # noqa: F401  (REV: None on the working tree; a git revision when the live page is tested)
from test_states import LANDED

HEX = re.compile(r'\b[0-9a-f]{10,}(?:-\d+)?\b')   # an internal picture or search id, as the server makes them


def ident(i):
    """The test's id in the run's output: the inventory row (C-3.5-07) or the requirement, edge case or fault (R01, E01, U01, X1, N1)."""
    return pytest.mark.parametrize('_id', [i])


def only_post(put, n=1):
    """The page sent exactly n requests; returns the last one."""
    put.wait_posts(n)
    assert len(put.posts) == n, f'expected {n} request(s) to the server, the page sent {len(put.posts)}: {put.posts}'
    return put.posts[-1]


def no_post(put, why=''):
    put.page.wait_for_timeout(150)
    assert not put.posts, f'no request should be sent{why}; the page sent {put.posts}'


def clean(put):
    assert not put.js_errors, f'the page script threw: {put.js_errors}'
    assert not put.unstubbed, f'the page asked for something unknown: {put.unstubbed}'


def panel(put):
    """The text of the right picture panel; '' when it is not on the page."""
    return put.text('#panel')


def card(put, unit):
    """The centre card of one element or shot (Playwright locator)."""
    return put.page.locator(f'#s-{put.active_tab()} [data-unit="{unit}"]')


def rail(put, unit):
    """The left-list card of one element, shot or gap."""
    return put.page.locator(f'#rcards .rcard[data-unit-card="{unit}"]')


def round_of(put):
    return put.payload['round']['elements']


def to_judge(put):
    """The elements of step 2 that ask for an answer today: not ignored, not taken from the footage."""
    return [e for e, r in round_of(put).items() if not r.get('ignored') and not r.get('from_footage')]


def kind_of(put, eid):
    return next(e['kind'] for e in put.payload['elements'] if e['id'] == eid)


def set_of(put, eid):
    by = {r['id']: r for r in put.payload['references']}
    return [i for i in round_of(put)[eid].get('set') or [] if by.get(i, {}).get('status') not in ('rejected', None)]


def show(put, unit):
    """Bring a card into view as the operator does: by its card in the left list, when the centre shows another card only."""
    c = card(put, unit)
    if (not c.count() or not c.first.is_visible()) and rail(put, unit).count():
        rail(put, unit).first.click()
        put.page.wait_for_timeout(80)


def golden(put, eid, k=0):
    """Choose the starting picture of a thing's set: today's tick, or the labelled control of the contract."""
    show(put, eid)
    put.page.locator(f'[data-golden^="{eid}:"]').nth(k).click()


def verdict(put, eid, v, words=''):
    show(put, eid)
    put.page.locator(f'input[name="v-{eid}"][value="{v}"]').check()
    if words:
        put.page.locator(f'[id="w-{eid}"]').fill(words)


def answer_all(put, quote='Pass one.'):
    """Step 2, as the operator: Yes with the first picture for every thing, Yes for every person. Returns what was answered."""
    said = {}
    for eid in to_judge(put):
        if not set_of(put, eid):
            verdict(put, eid, 'no')
            said[eid] = {'verdict': 'no', 'words': '', 'golden': ''}
            continue
        thing = kind_of(put, eid) != 'person'
        if thing:
            golden(put, eid)
        verdict(put, eid, 'yes')
        said[eid] = {'verdict': 'yes', 'words': '', 'golden': set_of(put, eid)[0] if thing else ''}
    if quote:
        put.page.fill('#words', quote)
    return said


def press_done(put, action='round-sets'):
    """Done, and Finish when the page asks first (step 1 asks today; step 2 asks once R15 is built: its Finish is inside #done-confirm)."""
    n = len(put.posts)
    put.page.locator(f'button[data-a="{action}"]').first.click()
    put.page.wait_for_timeout(150)
    if len(put.posts) == n:
        fin = put.page.locator(f'#done-confirm button[data-a="{action}"], #action button[data-a="{action}"]')
        if fin.count() and fin.first.is_enabled():
            fin.first.click()
    put.wait_posts(n + 1)


def last_of(put, action):
    """The last request of one action, or None."""
    hits = [b for b in put.posts if b.get('action') == action]
    return hits[-1] if hits else None


def counts_wrong(put):
    """R6: the header equals the tabs added up; on every tab the tab's number, the cards with the waiting mark and "Waiting for me (N)" agree."""
    header, tabs, wrong = put.header_count(), put.tab_counts(), []
    if header != sum(tabs.values()):
        wrong.append(f'the header says {header} waiting, the tabs add up to {sum(tabs.values())}')
    for tab in STEPS:
        put.open_tab(tab)
        marked, chip = sum(c['waiting'] for c in put.cards()), put.waiting_chip()
        if not (tabs[tab] == marked == chip):
            wrong.append(f'{tab}: the tab says {tabs[tab]} waiting, {marked} cards carry the waiting mark, the filter says "Waiting for me ({chip})"')
    return wrong


def next_waiting_wrong(put):
    """R9: every press of Next waiting opens or outlines something with a live control in it, and never prints a red line."""
    waiting, wrong = put.payload.get('waiting') or [], []
    for k in range(put.header_count()):
        put.clear_bar()
        put.click('#wnext')
        put.page.wait_for_timeout(80)
        label = waiting[k]['label'] if k < len(waiting) else f'item {k + 1}'
        landed = put.page.evaluate(LANDED)
        if put.red_line():
            wrong.append(f'"{label}": red line "{put.red_line()}"')
        elif not landed['opened'] or not landed['controls']:
            wrong.append(f'"{label}": nothing to act on was opened')
    return wrong


def opened(put):
    """What the right panel holds: its pictures, its take, its buttons."""
    return put.page.evaluate("""() => ({pictures: [...document.querySelectorAll('#panel img[data-view]')].map(i => i.dataset.view).sort(),
        take: ((document.querySelector('#panel video') || {}).src || '').split('/').pop(), buttons: [...document.querySelectorAll('#panel button[data-a]')].map(b => b.dataset.a).sort()})""")


def app_text(put):
    return put.page.inner_text('#app')


def stored(answers):
    """A patch for the data: the stored answers of step 2 as the contract carries them (round.elements[id].answer)."""
    def patch(payload):
        for eid, a in answers.items():
            payload['round']['elements'][eid]['answer'] = {'verdict': a.get('verdict'), 'golden': a.get('golden'), 'words': a.get('words', '')}
    return patch
