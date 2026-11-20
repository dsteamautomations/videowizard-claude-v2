"""Fix set, part 2 (SK, 20 Nov 2026), the page checks: `plugin/pages/decisions.html` in a headless browser from a local copy, with a stand-in
for the page's database whose newest round can change while the page is open (no product server).

(a) with no round at all the page says "Nothing to decide yet"; while a step is being loaded (the loading note is the newest document of
`rounds`) it says, in the server's words, that the pictures are being loaded and that the page fills itself, and it does fill itself when the
round arrives; (e) after twice the minutes stated it says to ask the assistant; (f) the round's count ("10 of 10 …") and what was answered
earlier are shown. The fit: at page areas of 1536 x 510 and 1900 x 830, light and dark, nothing scrolls the page. Skipped where Playwright or
its browser is not installed."""
import base64
import json
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import PAGE, SIZES, browser, picture   # noqa: F401 (`browser` is the fixture)
from test_design217_browser_pure import HOST, ROUND, STUB, doc, inside, page
from test_design222_browser_pure import doc as takes_doc, page as takes_page, still_main

ONCE = "onSnapshot(f){ f({docs: [{data: () => window.__round}]}); return () => {}; }"
LIVE = "onSnapshot(f){ window.__fire = () => f({docs: window.__round ? [{data: () => window.__round}] : []}); window.__fire(); return () => {}; }"
assert STUB.count(ONCE) == 1
NOTE = 'The pictures of this step are being loaded: 19 lines, about 2 minutes. This page fills itself: there is no need to reload it.'
LATE = 'This is taking longer than expected: ask the assistant in the chat.'
FITS = [('fit-small', 'light'), ('fit-small', 'dark'), ('fit-large', 'light'), ('fit-large', 'dark')]


def loading(ago_s=0, minutes=2):
    """The loading note as the tool writes it, handed out `ago_s` seconds ago."""
    at = datetime.now(timezone.utc) - timedelta(seconds=ago_s)
    return {'round': 'loading-x', 'at': at.isoformat(), 'run': 'VW-99', 'step': 'Pictures and drawn graphics', 'open': False, 'summary': '', 'note': NOTE, 'lines': [],
            'loading': {'minutes': minutes, 'expected': 19, 'late': LATE}}


def live(browser, d, size='fit-large', scheme='light'):
    """The page with the database's newest round `d` (None: no round at all); `window.__fire()` gives it the round again after a change."""
    pg = browser.new_page(viewport=SIZES[size], color_scheme=scheme)
    pg.errors = []
    pg.on('console', lambda m: pg.errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: pg.errors.append(str(e)))
    html = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            f"<script>window.__round = {json.dumps(d).replace('</', '<\\/')}; window.__zoom = {{}}; window.__nopic = [];"
            f"window.__pic = 'data:image/png;base64,{base64.b64encode(picture()).decode()}';{STUB.replace(ONCE, LIVE)}</script>" + PAGE.read_text(encoding='utf-8') + '</body></html>')
    pg.route('**/*', lambda r: r.fulfill(status=200, content_type='text/html', body=html) if r.request.url == HOST else r.fulfill(status=200, content_type='text/css', body=''))
    pg.goto(HOST)
    pg.wait_for_function("document.querySelector('#msg').textContent !== 'Loading…' || !!document.querySelector('#loading')")
    return pg


def no_scroll(pg):
    return pg.evaluate('document.documentElement.scrollHeight <= window.innerHeight + 1 && document.documentElement.scrollWidth <= window.innerWidth')


def test_a_page_with_no_step_at_all_says_nothing_to_decide_yet(browser):
    pg = live(browser, None)
    assert pg.locator('#list .state').text_content() == 'Nothing to decide yet. The assistant writes the lines here when a step is ready.'
    assert pg.locator('#loading').count() == 0 and not pg.errors


@pytest.mark.parametrize('size,scheme', FITS)
def test_while_a_step_is_loaded_the_page_says_so_and_never_nothing_to_decide(browser, size, scheme):
    pg = live(browser, loading(), size, scheme)
    assert pg.locator('#loading').text_content() == NOTE and pg.locator('#loading').is_visible() and pg.locator('#loadinglate').count() == 0
    body = pg.locator('body').inner_text()
    assert 'Nothing to decide' not in body and 'Pictures and drawn graphics: your decisions' in body and 'VW-99' in body
    assert pg.locator('#wrap').is_visible() and pg.locator('#sets').is_hidden() and pg.locator('#things').is_hidden()
    assert no_scroll(pg) and not pg.errors
    inside(pg, '#loading')


def test_the_page_fills_itself_when_the_round_arrives_and_goes_back_to_loading_for_the_next_load(browser):
    pg = live(browser, loading())
    pg.evaluate(f"window.__round = {json.dumps(doc())}; window.__fire()")
    pg.wait_for_selector('#smain .swrap', state='attached', timeout=10000)
    assert pg.locator('#sets').is_visible() and pg.locator('#wrap').is_hidden() and pg.locator('#srail .srow').count() == len(ROUND['lines'])
    pg.evaluate(f"window.__round = {json.dumps(loading())}; window.__fire()")   # a newer loading note: the next round's pictures are being sent
    pg.wait_for_selector('#loading', state='visible')
    assert pg.locator('#sets').is_hidden() and pg.locator('#loading').text_content() == NOTE and not pg.errors


def test_a_load_older_than_twice_the_minutes_stated_says_to_ask_the_assistant(browser):
    pg = live(browser, loading(ago_s=5 * 60))   # 2 minutes stated: late after 4
    assert pg.locator('#loadinglate').text_content() == LATE and pg.locator('#msg').text_content() == LATE and pg.locator('#loading').text_content() == NOTE
    assert no_scroll(pg) and not pg.errors


def test_the_loading_notes_timer_never_redraws_the_round_that_arrived(browser):
    pg = live(browser, loading(ago_s=4 * 60 - 2))   # the late sentence is due in two seconds
    pg.evaluate(f"window.__round = {json.dumps(doc())}; window.__fire()")
    pg.wait_for_selector('#smain .swrap', state='attached', timeout=10000)
    pg.evaluate("document.querySelector('#smain .swrap').dataset.mark = 'kept'")
    pg.wait_for_timeout(3500)
    assert pg.evaluate("(document.querySelector('#smain .swrap') || {dataset: {}}).dataset.mark") == 'kept'   # nothing was drawn again: a box being typed in keeps its text


def test_the_late_sentence_appears_by_itself_when_the_time_is_reached(browser):
    pg = live(browser, loading(ago_s=4 * 60 - 2))   # two seconds before twice the minutes
    assert pg.locator('#loadinglate').count() == 0
    pg.wait_for_selector('#loadinglate', state='visible', timeout=8000)
    assert pg.locator('#loadinglate').text_content() == LATE


@pytest.mark.parametrize('size,scheme', FITS)
def test_the_round_shows_how_many_are_on_the_page_and_what_was_answered_earlier(browser, size, scheme):
    earlier = [{'name': 'The yard at dawn', 'kind_words': 'A still', 'state': 'answered', 'note': 'Answered earlier, in the chat.'}]
    pg = page(browser, doc(lambda l, d: d['layout'].update(recorded=earlier)), size, scheme=scheme)
    assert pg.locator('#scount').text_content() == ROUND['layout']['count'] == '10 of 10 pictures and drawn graphics are on this page.'
    fold = pg.locator('#srail .sfold[data-fold="recorded"]')
    assert ' '.join(fold.inner_text().split()) == 'Answered earlier 1' and pg.locator('#precorded').count() == 0
    fold.click()
    assert ' '.join(pg.locator('#precorded li').inner_text().split()) == 'The yard at dawn A still · Answered earlier, in the chat.'
    assert pg.locator('#srail .sfold[data-fold="coming"]').count() == 1   # what could not be made keeps its own row
    assert still_main(pg) and pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth') and not pg.errors
    inside(pg, '#sfoot')


def test_a_round_of_before_has_no_count_and_the_takes_round_shows_its_own(browser):
    pg = page(browser, doc(lambda l, d: d['layout'].pop('count')))
    assert pg.locator('#scount').count() == 0 and pg.locator('#srail .sfold[data-fold="recorded"]').count() == 0 and not pg.errors
    said = '3 of 3 AI video shots are on this page.'
    pg = takes_page(browser, takes_doc(lambda l, d: d['layout'].update(count=said)), 'fit-small')
    assert pg.locator('#scount').text_content() == said and still_main(pg) and not pg.errors
