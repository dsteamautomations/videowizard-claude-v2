"""design/222, the page checks: step 7, "AI video" (`layout.kind === 'takes'`), `plugin/pages/decisions.html` drawn in a headless browser from a
local copy with the frozen round (`d222_takes_round.json`) and the stand-in database of design/217 (no product server). Every take's video is the
short webm the browser records itself. Every label is read from the round file: the page holds none of its own. The fit: at page areas of
1536 x 510 and 1900 x 830 the player (at least 150 px high), the check line, the buttons and the two links are in view with no scrolling of the
main area. Skipped where Playwright or its browser is not installed. Set VW_SHOTS to a folder to keep screenshots."""
import copy
import json
import re
from pathlib import Path

import pytest

pytest.importorskip('playwright.sync_api')

import base64

from test_design212_browser_pure import PAGE, SIZES, answers, browser, picture, shot   # noqa: F401 (`browser` is the fixture)
from test_design217_browser_pure import BLOB, HOST, LARGE, STUB, big_picture, inside, saved, webm

ROUND = json.loads((Path(__file__).with_name('d222_takes_round.json')).read_text(encoding='utf-8'))
W = ROUND['layout']['words']['takes']
L = {l['line']: l for l in ROUND['lines']}
TWO, ONE, DONE = L['l01'], L['l02'], L['l03']   # two takes (take 2 failed, take 1 rejected), one take passed, answered earlier
AMOUNT = re.compile(r'[₹$€£]\s?\d|\b\d[\d,.]*\s?(USD|INR|EUR|dollars?|rupees?|cents?)\b', re.I)   # no amount of money anywhere ("paid" and "price" are the round's words)


def doc(change=None):
    d = copy.deepcopy(ROUND)
    d['at'] = 'now'
    if change:
        change({l['line']: l for l in d['lines']}, d)
    return d


def page(browser, d=None, size='fit-large', scheme='light'):
    """The page file as a document of its own at the test origin, drawn with one round; every take's `zoom/<code>` links the webm."""
    d = d or doc()
    pg = browser.new_page(viewport=SIZES[size], color_scheme=scheme)
    pg.errors = []
    pg.on('console', lambda m: pg.errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: pg.errors.append(str(e)))
    zoom = {p['code']: LARGE for l in d['lines'] for p in l.get('pics') or []}
    zoom.update({t['video']['code']: BLOB for l in d['lines'] for t in l.get('takes') or [] if t['video'].get('code')})
    html = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            f"<script>window.__round = {json.dumps(d).replace('</', '<\\/')}; window.__zoom = {json.dumps(zoom)}; window.__nopic = [];"
            f"window.__pic = 'data:image/png;base64,{base64.b64encode(picture()).decode()}';{STUB}</script>" + PAGE.read_text(encoding='utf-8') + '</body></html>')
    clip = webm(browser)

    def route(r):
        u = r.request.url
        if u == HOST:
            return r.fulfill(status=200, content_type='text/html', body=html)
        if u == HOST + BLOB[1:]:   # with byte ranges, so that the player can seek in it
            m = re.match(r'bytes=(\d+)-(\d*)', r.request.headers.get('range', ''))
            if not m:
                return r.fulfill(status=200, content_type='video/webm', body=clip, headers={'Accept-Ranges': 'bytes'})
            a, z = int(m.group(1)), int(m.group(2) or len(clip) - 1)
            return r.fulfill(status=206, content_type='video/webm', body=clip[a:z + 1],
                             headers={'Accept-Ranges': 'bytes', 'Content-Range': f'bytes {a}-{z}/{len(clip)}'})
        if u == HOST + LARGE[1:]:
            return r.fulfill(status=200, content_type='image/png', body=big_picture())
        return r.fulfill(status=200, content_type='text/css', body='')
    pg.route('**/*', route)
    pg.goto(HOST)
    try:
        pg.wait_for_selector('#smain .swrap', state='attached', timeout=10000)
    except Exception:
        raise AssertionError(f'the page did not draw: {pg.errors}')
    return pg


def go(pg, l):
    pg.locator(f'#srail .srow[data-line="{l["line"]}"]').click()
    pg.wait_for_function('n => (document.querySelector("#smain .sname") || {}).textContent === n', arg=l['name'])


def playing(pg):
    pg.wait_for_function("(() => { const v = document.querySelector('#pvideo'); return v && v.readyState >= 2; })()")


def bar(pg):
    return [' '.join(t.split()) for t in pg.locator('#pbar button').all_text_contents()]


def btn(l, choice):
    return next(b for b in l['buttons'] if b['choice'] == choice)


def foot(pg):
    return ' '.join(pg.locator('#sfoot > *').all_text_contents())


def clean(pg):
    text = pg.locator('body').inner_text()
    assert not AMOUNT.search(text), AMOUNT.search(text).group(0)
    assert pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not pg.errors, pg.errors


def still_main(pg):
    return pg.evaluate("(() => { const m = document.querySelector('#smain'); return m.scrollHeight <= m.clientHeight + 1 && m.scrollWidth <= m.clientWidth + 1; })()")


# ---------- the list ----------

def test_the_list_names_and_dots_only_in_three_groups(browser):
    coming = [{'name': 'Brick kiln at dusk', 'kind_words': 'An AI video take', 'state': 'failed', 'note': 'It could not be made.'}]
    pg = page(browser, doc(lambda l, d: d['layout'].update(coming=coming)))
    assert pg.locator('#sets').is_visible() and pg.locator('#wrap').is_hidden() and pg.locator('#things').is_hidden()
    assert pg.locator('#sstep').text_content() == ROUND['step'] and pg.locator('#shelp').text_content() == W['help']
    assert pg.locator('#srail h2').all_text_contents() == [W['todo'], W['answered_head']]
    todo = pg.locator('#srail ul').nth(0).locator('.srow')
    assert todo.evaluate_all('rs => rs.map(r => [r.querySelector(".sdot").textContent, r.querySelector(".snm").textContent])') == [['1', TWO['name']], ['2', ONE['name']]]
    assert todo.nth(0).get_attribute('title') == W['state_open'] and todo.nth(0).get_attribute('aria-label') == TWO['name'] + ': ' + W['state_open']
    done = pg.locator('#srail ul').nth(1).locator('.srow')
    assert done.count() == 1 and done.locator('.snm').text_content() == DONE['name'] and done.locator('.sdot').text_content() == '✓'
    assert done.get_attribute('title') == W['done']['select'] and 'done' in done.get_attribute('class')
    # no film time, no take count, no kind under the name
    assert pg.locator('#srail .pkw, #srail .sst').count() == 0 and not re.search(r'\d:\d\d', pg.locator('#srail').inner_text())
    fold = pg.locator('#srail [data-fold="coming"]')
    assert fold.locator('span').text_content() == W['coming'] and fold.text_content().endswith('1')
    fold.click()
    assert pg.locator('#pcoming li').evaluate_all('r => r.map(x => x.firstChild.textContent)') == ['Brick kiln at dusk'] and 'It could not be made.' in pg.locator('#pcoming').text_content()
    assert foot(pg) == W['foot'].replace('{n}', '0').replace('{m}', '2') + ' ' + W['foot_wait']
    assert pg.locator('#smain .sname').text_content() == TWO['name']   # the first that needs an answer opens
    clean(pg)
    pg.close()


# ---------- the take, its tabs, its check ----------

def test_the_newest_take_is_open_and_the_tabs_switch(browser):
    pg = page(browser)
    playing(pg)
    tabs = pg.locator('#ptabs [role="tab"]')
    assert tabs.all_text_contents() == [t['tab'] for t in TWO['takes']] and tabs.nth(1).get_attribute('aria-selected') == 'true'
    v = pg.evaluate("(() => { const v = document.querySelector('#pvideo'); return [v.loop, v.muted, v.controls, v.src.endsWith('" + BLOB + "'), v.getAttribute('aria-label')]; })()")
    assert v == [True, True, True, True, TWO['takes'][1]['video']['label']]
    assert bar(pg) == [b['label'] for b in TWO['buttons'] if b['take'] == 2] and pg.locator('#pwas').count() == 0
    tabs.nth(0).click()
    assert tabs.nth(0).get_attribute('aria-selected') == 'true' and pg.locator('#pvideo').get_attribute('aria-label') == TWO['takes'][0]['video']['label']
    assert pg.locator('#pwas').text_content() == TWO['takes'][0]['rejected'] and pg.locator('#pcheck').text_content() == TWO['takes'][0]['check']['head']
    assert bar(pg) == ['Use take 1 after all']
    tabs.nth(1).click()
    assert tabs.nth(1).get_attribute('aria-selected') == 'true' and len(bar(pg)) == 2
    go(pg, ONE)
    assert pg.locator('#ptabs').count() == 0   # one take: no tabs
    pg.close()


def test_a_passed_check_says_only_check_passed(browser):
    pg = page(browser)
    go(pg, ONE)
    c = pg.locator('#pcheck')
    assert c.text_content() == ONE['takes'][0]['check']['head'] == 'Check passed' and c.get_attribute('data-state') == 'pass' and 'bad' not in c.get_attribute('class')
    assert pg.locator('#pcheck button').count() == 1 and pg.locator('#pcheckb').get_attribute('aria-expanded') == 'false'   # release 1, B3: the line is a button; who checked is one click away
    assert pg.locator('#plinks button').all_text_contents() == [W['film'], W['details']]   # the fixture's line has your footage before it
    go(pg, TWO)
    assert pg.locator('#plinks button').all_text_contents() == [W['film'], W['details']] if any(p['role'] in ('before', 'after') for p in TWO['pics']) else [W['details']]   # no picture before or after: no "See it in the film"
    pg.close()


def test_a_failed_check_shows_the_first_fault_go_to_and_see_all(browser):
    pg = page(browser)
    playing(pg)
    k = TWO['takes'][1]['check']
    c = pg.locator('#pcheck')
    assert c.get_attribute('data-state') == 'fail' and 'bad' in c.get_attribute('class')
    assert ' '.join(c.text_content().split()) == f"{k['head']} {k['faults'][0]['text']}"      # release 1, B3: one closed line (a round of 0.118.0 has no short line: "Check:" and its first fault)
    assert pg.locator('#pcheck li').count() == 0 and k['faults'][1]['text'] not in c.text_content()
    pg.locator('#pcheckb').click()                                                        # one click opens the rest: every fault, each with its "Go to"
    assert pg.locator('#pfaults li').count() == 2 and k['faults'][1]['text'] in c.text_content()
    c.locator('[data-seek]').first.click()
    pg.wait_for_function("(() => { const v = document.querySelector('#pvideo'); return v.paused && Math.abs(v.currentTime - Math.min(1.5, v.duration)) < 0.05; })()")   # the stand-in clip is about 1.45 s: the time stops at its end
    pg.locator('#pdetails').click()                                                       # Details still lists them
    assert pg.locator('#ksheet').is_visible() and pg.locator('#dfaults li').count() == 2
    pg.close()


def test_a_check_neither_passed_nor_failed_is_neutral(browser):
    def change(l, d):
        l['l02']['takes'][0]['check'].update(state='not_checked', head='Not checked')
    pg = page(browser, doc(change))
    go(pg, ONE)
    c = pg.locator('#pcheck')
    assert c.text_content() == 'Not checked' and 'doubt' in c.get_attribute('class')
    pg.close()


def test_short_take_is_one_line(browser):
    pg = page(browser, doc(lambda l, d: l['l02']['takes'][0].update(short='The take is 4.0 s; its place in the film is 5.6 s.')))
    go(pg, ONE)
    assert pg.locator('#pshort').text_content() == 'The take is 4.0 s; its place in the film is 5.6 s.'
    go(pg, TWO)
    assert pg.locator('#pshort').count() == 0
    pg.close()


# ---------- the answers ----------

def test_select_on_a_passed_take_writes_select(browser):
    pg = page(browser)
    go(pg, ONE)
    assert 'primary' in pg.locator('#pbar [data-choice="select"]').get_attribute('class') and 'danger' in pg.locator('#pbar [data-choice="reject"]').get_attribute('class')
    pg.locator('#pbar [data-choice="select"]').click()
    got = saved(pg, 'l02', 'select')
    assert set(got) == {'key', 'item', 'choice', 'notes', 'at'} and got['notes'] == '' and got['key'] == ONE['key'] and got['item'] == ONE['item']
    assert pg.locator('#sanswer').text_content().startswith(btn(ONE, 'select')['say']) and W['against'] not in pg.locator('#sanswer').text_content()
    row = pg.locator('#srail .srow[data-line="l02"]')
    assert row.locator('.sdot').text_content() == '✓' and row.get_attribute('title') == W['done']['select']
    pg.locator('#sundo').click()                                                          # Undo deletes it
    pg.wait_for_function('() => !window.__answers.l02')
    assert pg.locator('#sanswer').count() == 0 and row.locator('.sdot').text_content() == '2'
    pg.close()


def test_make_another_writes_again_with_the_words_and_shows_its_note(browser):
    pg = page(browser)
    go(pg, ONE)
    b = btn(ONE, 'again')
    pg.locator('#pbar [data-choice="again"]').click()
    assert pg.locator('#spanel label').text_content() == b['hint'] and pg.locator('#pnote').text_content() == b['note']
    pg.locator('#sfixsend').click()
    assert pg.locator('#smsg').text_content() == b['need'] and answers(pg) == {}
    pg.locator('#sfix').fill('He lays the brick slower.')
    pg.locator('#sfixsend').click()
    got = saved(pg, 'l02', 'again')
    assert got['notes'] == 'He lays the brick slower.' and b['say'].replace('{words}', got['notes']) in pg.locator('#sanswer').text_content()
    row = pg.locator('#srail .srow[data-line="l02"]')
    assert row.locator('.sdot').text_content() == '↻' and row.get_attribute('title') == W['done']['again']
    pg.close()


def test_reject_on_the_two_take_line_says_no_further_take(browser):
    pg = page(browser)
    b = btn(TWO, 'reject')
    pg.locator('#pbar [data-choice="reject"]').click()
    assert pg.locator('#pnote').text_content() == b['note'] and pg.locator('#sfix').input_value() == b['prefill']
    pg.keyboard.press('Escape')
    assert pg.locator('#spanel').count() == 0
    pg.locator('#pbar [data-choice="reject"]').click()
    pg.locator('#sfixsend').click()                                                       # the prefill is sent as it is
    got = saved(pg, 'l01', 'reject')
    assert got['notes'] == b['prefill']
    assert pg.locator('#srail .srow[data-line="l01"] .sdot').text_content() == '×'
    pg.close()


def test_use_take_1_after_all_asks_once_and_writes_old_1(browser):
    pg = page(browser)
    b = btn(TWO, 'old:1')
    pg.locator('#ptabs [data-take="1"]').click()
    pg.locator('#pbar [data-choice="old:1"]').click()
    assert pg.locator('#spanel label').text_content() == b['sure']['ask'] and pg.locator('#ssure').text_content() == b['sure']['go'] and pg.locator('#sback').text_content() == b['sure']['back']
    assert answers(pg) == {} and pg.evaluate('document.activeElement.id') == 'sback'
    pg.locator('#sback').click()
    assert pg.locator('#spanel').count() == 0 and answers(pg) == {}
    pg.locator('#pbar [data-choice="old:1"]').click()
    pg.locator('#ssure').click()
    got = saved(pg, 'l01', 'old:1')
    assert got['notes'] == '' and set(got) == {'key', 'item', 'choice', 'notes', 'at'}
    assert pg.locator('#sanswer').text_content().startswith(b['say']) and W['against'] not in pg.locator('#sanswer').text_content()   # take 1 passed its check
    pg.close()


def test_a_line_answered_earlier_has_no_buttons_and_says_its_answer(browser):
    pg = page(browser)
    go(pg, DONE)
    assert pg.locator('#pbar').count() == 0 and pg.locator('#smain .sbtn').count() == 0 and pg.locator('#sundo').count() == 0
    text = pg.locator('#sanswer').text_content()
    assert DONE['answer']['say'] in text and W['change_in_chat'] in text and W['against'] not in text
    assert pg.locator('#pcheck').text_content() == 'Check passed' and pg.locator('#plinks button').all_text_contents() == [W['details']]
    assert foot(pg).startswith(W['foot'].replace('{n}', '0').replace('{m}', '2'))   # not counted
    pg.close()
    pg = page(browser, doc(lambda l, d: l['l03']['answer'].update(against=True)))
    go(pg, DONE)
    assert W['against'] in pg.locator('#sanswer').text_content()
    assert pg.locator('#srail .srow[data-line="l03"] .sdot').text_content() == '!'
    pg.close()


# ---------- the two sheets ----------

def test_see_it_in_the_film_and_details_open_over_the_page_and_close(browser):
    pg = page(browser)
    t = TWO['takes'][1]
    pg.locator('#pfilm').click()
    sheet = pg.locator('#ksheet')
    assert sheet.is_visible() and pg.locator('#kclose').text_content() == W['close']
    caps = [' '.join(x.split()) for x in sheet.locator('figcaption').all_text_contents()]
    after = next(p for p in TWO['pics'] if p['role'] == 'after')
    assert caps == [f"{W['this_take']}. Take 2", f"{W['after']}. {after['label']}"]   # no picture before this shot: this take, then after
    assert sheet.locator('figure').nth(0).get_attribute('data-code') == next(p['code'] for p in TWO['pics'] if p['role'] == 'frame' and p['take'] == 2)
    assert W['compare_only'] in sheet.text_content() and sheet.locator('button').count() == 1   # only Close
    pg.keyboard.press('Escape')
    assert pg.locator('#ksheet').count() == 0 and pg.locator('#kover').is_hidden()
    pg.locator('#pdetails').click()
    sheet = pg.locator('#ksheet')
    text = sheet.text_content()
    assert pg.locator('#dfaults li').count() == 2 and sheet.locator('[data-seek]').count() == 2
    assert t['check']['by'] in text and t['check']['not_judged'] in text
    assert W['d_passed'].replace('{n}', str(len(t['check']['passed']))) in text and all(x in text for x in t['check']['passed'])
    assert all(d[0] in text and all(x in text for x in d[1]) for d in t['details']) and W['d_still'] in text and W['d_check'] in text
    assert sheet.locator('button:not([data-seek])').count() == 1                          # no answer button inside
    pg.locator('#kclose').click()
    assert pg.locator('#ksheet').count() == 0
    pg.locator('#pdetails').click()
    pg.locator('#ksheet [data-seek]').first.click()                                       # Go to closes the sheet and moves the player
    assert pg.locator('#ksheet').count() == 0
    pg.close()


# ---------- the words in time ----------

def test_the_caption_marks_the_word_for_the_players_time(browser):
    pg = page(browser)
    go(pg, ONE)
    playing(pg)
    c, k = ONE['caption'], ONE['takes'][0]
    assert pg.locator('#pwords').get_attribute('aria-label') == W['words_label']
    assert pg.locator('#pwords .w').all_text_contents() == [w['t'] for w in c['words']]   # whole words
    def at(s):
        return pg.evaluate("""async s => { const v = document.querySelector('#pvideo'); v.pause(); v.currentTime = s;
          await new Promise(r => v.addEventListener('seeked', r, {once: true})); await new Promise(r => setTimeout(r, 50));
          return [...document.querySelectorAll('#pwords .w.now')].map(e => e.textContent); }""", s)
    assert at(k['in_s'] + c['words'][2]['s'] + 0.05) == [c['words'][2]['t']]            # "are": a word's time is in_s + its second
    assert at(k['in_s'] + c['words'][1]['s'] + 0.05) == [c['words'][1]['t']]            # dragged back
    assert at(k['in_s'] - 0.2) == []                                                       # before in_s nothing is marked
    # after the last word nothing is marked (the stand-in clip is 1.5 s long: its time is read through a stand-in clock)
    last = pg.evaluate("""s => { const v = document.querySelector('#pvideo'); v.pause(); Object.defineProperty(v, 'currentTime', {get: () => s, configurable: true});
      v.dispatchEvent(new Event('timeupdate')); return [...document.querySelectorAll('#pwords .w.now')].length; }""", k['in_s'] + c['words'][-1]['e'] + 1)
    assert last == 0
    assert pg.evaluate("(() => { const p = document.querySelector('#pwords'); return Math.round(p.getBoundingClientRect().height / parseFloat(getComputedStyle(p).lineHeight)); })()") <= 2
    pg.close()


def test_pre_and_post_are_greyed_and_never_marked(browser):
    pg = page(browser)
    playing(pg)
    ctx = pg.locator('#pwords .ctx')
    assert ctx.count() == 1 and ctx.text_content().strip() == TWO['caption']['post'] and ctx.locator('.w').count() == 0
    pg.close()


def test_no_caption_shows_the_plain_words_and_nothing_when_both_are_empty(browser):
    pg = page(browser, doc(lambda l, d: (l['l02'].update(caption=None), l['l03'].update(caption=None, words=''))))
    go(pg, ONE)
    assert pg.locator('#pwords').text_content() == ONE['words'] and pg.locator('#pwords .w').count() == 0
    go(pg, DONE)
    assert pg.locator('#pwords').count() == 0
    pg.close()


# ---------- the end ----------


def test_the_end_card_says_what_happens_to_a_take_rejected_with_no_new_one(browser):
    pg = page(browser)
    pg.locator('#pbar [data-choice="reject"]').click()
    pg.locator('#sfix').fill('A second helper appears.')
    pg.locator('#sfixsend').click()
    saved(pg, 'l01', 'reject')
    go(pg, ONE)
    pg.locator('#pbar [data-choice="select"]').click()
    saved(pg, 'l02', 'select')
    pg.wait_for_selector('#send li')
    items = [' '.join(x.split()) for x in pg.locator('#send li').all_text_contents()]
    assert items[0] == f"{TWO['name']}: " + btn(TWO, 'reject')['end'].replace('{words}', 'A second helper appears.') and '.".' not in items[0]
    assert pg.locator('#ereject').text_content() == W['end_reject'] and pg.locator('#eagain').count() == 0
    clean(pg)
    pg.close()


def test_answers_still_needed_and_the_help(browser):
    pg = page(browser)
    pg.keyboard.press('ArrowRight')
    assert pg.locator('#smain .sname').text_content() == ONE['name']
    pg.locator('#shelp').click()
    text = pg.locator('#smain').inner_text()
    assert all(p in text for p in ROUND['layout']['help']) and W['keys'] in text
    pg.locator('#shelpclose').click()
    pg.close()


# ---------- the fit ----------

@pytest.mark.parametrize('size', ['fit-small', 'fit-large'])
@pytest.mark.parametrize('view', ['two-takes', 'tab-1', 'one-take', 'answered-earlier', 'words-box'])
def test_it_fits_with_no_scrolling(browser, size, view):
    pg = page(browser, size=size)
    if view == 'tab-1':
        pg.locator('#ptabs [data-take="1"]').click()
    if view in ('one-take', 'words-box'):
        go(pg, ONE)
    if view == 'answered-earlier':
        go(pg, DONE)
    if view == 'words-box':
        pg.locator('#pbar [data-choice="again"]').click()
    playing(pg)
    need = ['#smain .sname', '#sbig', '#pcheck', '#plinks button'] + (['#pbar button'] if view != 'answered-earlier' else ['#sanswer'])
    if view == 'words-box':
        need = ['#smain .sname', '#sbig', '#pbar button', '#spanel textarea']
    for sel in need:
        for i in range(pg.locator(sel).count()):
            inside(pg, f'{sel} >> nth={i}')
    assert still_main(pg)
    assert pg.locator('#sbig').bounding_box()['height'] >= 150, pg.locator('#sbig').bounding_box()
    shot(pg, f'd222-{size}-{view}')
    clean(pg)
    pg.close()


@pytest.mark.parametrize('size', ['fit-small', 'fit-large'])
def test_the_sheets_and_the_end_card_fit(browser, size):
    pg = page(browser, size=size)
    for link in ('#pfilm', '#pdetails'):
        pg.locator(link).click()
        inside(pg, '#ksheet')
        inside(pg, '#kclose')
        pg.keyboard.press('Escape')
    pg.close()


# ---------- the page holds no words of its own ----------

def test_the_page_file_holds_no_words_for_this_layout():
    src = PAGE.read_text(encoding='utf-8')
    start = src.index('// ---------- design/222')
    block = src[start:src.index('function sEnd(', start)]
    code = re.sub(r'(^|\s)//.*$', '', block, flags=re.M)
    literals = re.findall(r"'((?:[^'\\\n]|\\.)*)'", code)
    classes = set(re.findall(r'\.([a-z][\w-]*)', src[:src.index('</style>')]))
    words = [s for s in literals if re.search(r'[A-Z]', s) or (' ' in s.strip() and re.search(r'[a-z]{2}', s) and any(t not in classes for t in s.split()))]
    assert not words, words   # a literal of two words or more is a list of classes; any other is a word of its own
    assert 'film' in literals and 'pvbox kbad' in literals   # the scan sees this block's literals


def test_every_text_on_the_screen_comes_from_the_round(browser):
    raw = json.dumps(ROUND, ensure_ascii=False)
    temps = [re.compile('^' + re.escape(s).replace(r'\{words\}', '.+').replace(r'\{n\}', r'\d+').replace(r'\{m\}', r'\d+').replace(r'\{s\}', r'[\d.]+') + '$')
             for s in [*W.values(), *[b['say'] for l in ROUND['lines'] for b in l['buttons']]] if isinstance(s, str) and '{' in s]
    pg = page(browser)
    seen = []
    for view in ('a', 'film', 'details', 'one', 'done', 'help'):
        if view == 'film':
            pg.locator('#pfilm').click()
        if view == 'details':
            pg.keyboard.press('Escape')
            pg.locator('#pdetails').click()
        if view == 'one':
            pg.keyboard.press('Escape')
            go(pg, ONE)
            pg.locator('#pbar [data-choice="again"]').click()
        if view == 'done':
            go(pg, DONE)
        if view == 'help':
            pg.locator('#shelp').click()
        seen += pg.evaluate("""() => { const out = [], w = document.createTreeWalker(document.querySelector('#sets'), NodeFilter.SHOW_TEXT);
          while (w.nextNode()) { const t = w.currentNode.textContent.trim(); if (/[A-Za-z]{2}/.test(t) && w.currentNode.parentElement.offsetParent !== null) out.push(t); } return out; }""")
    known = lambda t: json.dumps(t, ensure_ascii=False)[1:-1] in raw or any(r.match(t) for r in temps)
    odd = sorted({t for t in seen if not known(t) and not known(t.strip(' :().')) and not all(known(x) for x in t.split(' · '))
                  and not re.fullmatch(r'[.:·()\s]*', t.replace(ROUND['step'], ''))})
    assert not odd, odd
    pg.close()


# ---------- the second critic's points 8 and 7 (E3, F1, F6; E36) ----------

def test_a_take_with_no_page_video_shows_its_frames_and_its_buttons_stay(browser):
    said = 'The take cannot be played here: these are its frames, in order.'

    def none(lines, d):
        lines['l02']['takes'][0]['video'].update(code='', none=said)
    pg = page(browser, doc(none))
    go(pg, ONE)
    pg.wait_for_selector('#sbig img')                                     # the sheet of its frames stands in the player's place
    assert pg.locator('#sbig video').count() == 0 and pg.locator('#pnone').text_content() == said
    assert pg.locator('#pbar button').count() == 3 and pg.locator('#pbar button:disabled').count() == 0
    assert not pg.errors
    pg.close()


def test_a_long_caption_keeps_the_word_being_spoken_in_view_in_two_lines(browser):
    def long(lines, d):
        lines['l02']['caption'] = {'pre': '', 'post': '', 'words': [{'t': f'word{i}', 's': round(i * 0.02, 2), 'e': round(i * 0.02 + 0.01, 2)} for i in range(160)]}
    pg = page(browser, doc(long), size='fit-small')
    go(pg, ONE)
    playing(pg)
    k = ONE['takes'][0]

    def at(s):
        return pg.evaluate("""s => { const v = document.querySelector('#pvideo'), p = document.querySelector('#pwords'); v.pause();
          Object.defineProperty(v, 'currentTime', {get: () => s, configurable: true}); v.dispatchEvent(new Event('timeupdate'));
          const m = p.querySelector('.w.now'), a = p.getBoundingClientRect(), b = m && m.getBoundingClientRect();
          return {word: m && m.textContent, inside: !!b && b.top >= a.top - 1 && b.bottom <= a.bottom + 1, lines: Math.round(a.height / parseFloat(getComputedStyle(p).lineHeight))}; }""", s)
    late = at(k['in_s'] + 150 * 0.02 + 0.005)
    assert late == {'word': 'word150', 'inside': True, 'lines': 2}        # far beyond two lines of text: the caption followed the word
    early = at(k['in_s'] + 2 * 0.02 + 0.005)
    assert early == {'word': 'word2', 'inside': True, 'lines': 2}         # and back
    fits = pg.evaluate("(() => { const m = document.querySelector('#smain'); return m.scrollHeight <= m.clientHeight + 1; })()")
    assert fits and not pg.errors
    pg.close()
