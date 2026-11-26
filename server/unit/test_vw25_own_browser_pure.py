"""VW-25 issues 10 and 11, the page checks: "Use my own picture" on `plugin/pages/decisions.html`, drawn in a headless browser from a local
copy with the round the server builds (step 1 from the shared fixture, step 2 from `d213_sets_round.json`) and the stand-in for the page's
database and file store of design/212's page checks (no product server, no network). Issue 10: add three (one by one and several at once),
the fourth refused, the same file taken once, remove one, a reload keeps them, all removed is unanswered; one that fails to upload is named
with "Try again" and the others stay; a wrong type and a file over 15 MB are refused by name; a person keeps one photo; an answer in the
older shape (one object) is a list of one. Issue 11: the words box stops at 300 characters and shows the count; words alone are not an
answer; the words travel with the pictures as the answer's `notes`. Skipped where Playwright or its browser is not installed."""
import base64
import copy
import io
import json
from pathlib import Path

import pytest
from PIL import Image

pytest.importorskip('playwright.sync_api')

from test_design211c_kit_pure import Film
from test_design212_browser_pure import PAGE, SIZES, STUB, answers, browser, doc, gone, picture, thing   # noqa: F401 (`browser` is the fixture)
from test_design216_browser_pure import go

# the kit's stand-in, with: answers that were saved before (a reload), a file store that gives every file its own id and fails for a file named fail-… until healed
MINE = STUB.replace('window.__answers = {};', 'window.__answers = window.__seed || {};').replace(
    "const assets = {upload: async f => ({id: 'a'.repeat(32), url: window.__pic, contentType: f.type, sizeBytes: f.size})};",
    "let n = 0; const assets = {upload: async f => { if (/^fail/.test(f.name) && !window.__heal) throw new Error('offline'); n += 1; "
    "return {id: ('0' + n).slice(-2).repeat(16), url: window.__pic, contentType: f.type, sizeBytes: f.size}; }};")
assert 'window.__seed' in MINE and 'window.__heal' in MINE
SETS = json.loads(Path(__file__).with_name('d213_sets_round.json').read_text(encoding='utf-8'))
MOST, ONE = 'Three pictures at most. Remove one first.', 'One photo of a person at most. Remove one first.'


def show(browser, round_doc, seed=None, wait='#tmain .thead'):
    pg = browser.new_page(viewport=SIZES['1366'])
    pg.errors = []
    pg.on('console', lambda m: pg.errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: pg.errors.append(str(e)))
    pg.route('**/*', lambda route: route.fulfill(status=200, content_type='text/css', body='') if route.request.url.startswith('http') else route.continue_())
    data = json.dumps(round_doc).replace('</', '<\\/')
    pg.set_content('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
                   f"<script>window.__round = {data}; window.__seed = {json.dumps(seed or {})}; window.__pic = 'data:image/png;base64,{base64.b64encode(picture()).decode()}';{MINE}</script>"
                   + PAGE.read_text(encoding='utf-8') + '</body></html>')
    pg.wait_for_selector(wait, state='attached')
    return pg


def file(name, colour='white', kind='image/png'):
    out = io.BytesIO()
    Image.new('RGB', (40 + len(name), 30), colour).save(out, 'PNG')
    return {'name': name, 'mimeType': kind, 'buffer': out.getvalue()}


def line_of(round_doc, name):
    return next(l['line'] for l in round_doc['lines'] if l.get('name') == name)


def own(pg, line, n):
    """The line's own answer once it holds `n` pictures."""
    pg.wait_for_function('([l, n]) => { const a = window.__answers[l]; return !!a && a.choice === "own" && [].concat(a.own).length === n; }', arg=[line, n])
    return answers(pg)[line]


def names(a):
    return [p['name'] for p in a['own']]


def says(pg, text, box='#tpanel'):
    pg.wait_for_function('([b, t]) => (document.querySelector(b) || {textContent: ""}).textContent.includes(t)', arg=[box, text])


def step_1(monkeypatch):
    return doc(Film(monkeypatch).page())


def open_own(pg, name='Brick'):
    thing(pg, name)
    pg.locator('#tmain [data-act="own"]').click()
    return pg.locator('#tpanel input[type=file]')


def test_three_pictures_the_fourth_refused_one_removed_and_a_reload_keeps_them(monkeypatch, browser):
    rd = step_1(monkeypatch)
    line = line_of(rd, 'Brick')
    pg = show(browser, rd)
    pick = open_own(pg)
    assert pick.get_attribute('multiple') is not None and 'Up to three pictures of this thing' in pg.locator('#tpanel').text_content()   # said before the upload
    pick.set_input_files(file('front.png'))                                    # one
    assert names(own(pg, line, 1)) == ['front.png']
    pg.locator('#tpanel input[type=file]').set_input_files([file('side.png', 'blue'), file('top.jpg', 'red', 'image/jpeg')])   # several at once
    a = own(pg, line, 3)
    assert names(a) == ['front.png', 'side.png', 'top.jpg'] and len({p['id'] for p in a['own']}) == 3 and all(p['url'] and p['size'] for p in a['own'])
    assert pg.locator('#tpanel .ownlist li').count() == 3 and pg.locator('#tpanel .ownlist img.ownpic').count() == 3      # each shown small, with its name
    assert [t.strip() for t in pg.locator('#tpanel .ownlist li span').all_text_contents()] == ['front.png', 'side.png', 'top.jpg']
    assert pg.locator('#tanswer img.ownpic').count() == 3 and 'front.png, side.png, top.jpg' in pg.locator('#tanswer').text_content()
    pg.locator('#tpanel input[type=file]').set_input_files(file('fourth.png', 'green'))                                  # the fourth
    says(pg, MOST)
    assert len(answers(pg)[line]['own']) == 3
    pg.locator('#tpanel .ownlist li', has_text='side.png').locator('button').click()                                     # remove one, before "done"
    assert names(own(pg, line, 2)) == ['front.png', 'top.jpg']
    pg.locator('#tpanel input[type=file]').set_input_files(file('front.png'))                                            # the same file again: taken once
    says(pg, 'front.png is here already: it is taken once.')
    assert names(answers(pg)[line]) == ['front.png', 'top.jpg']
    seed = answers(pg)
    pg.close()
    pg = show(browser, rd, seed=seed)                                          # the page reloaded before "done": the pictures are still listed
    open_own(pg)
    assert [t.strip() for t in pg.locator('#tpanel .ownlist li span').all_text_contents()] == ['front.png', 'top.jpg'] and pg.locator('#tanswer img.ownpic').count() == 2
    pg.locator('#tpanel input[type=file]').set_input_files(file('late.webp', 'yellow', 'image/webp'))
    assert names(own(pg, line, 3)) == ['front.png', 'top.jpg', 'late.webp']
    for _ in range(3):                                                         # all removed: the line is unanswered again
        pg.locator('#tpanel .ownlist li button').first.click()
        pg.wait_for_timeout(50)
    gone(pg, line)
    assert pg.locator('#tanswer').count() == 0 and pg.locator('#tpanel .ownlist').count() == 0 and not pg.errors, pg.errors
    pg.close()


def test_one_picture_that_fails_to_upload_is_named_with_try_again_and_the_other_two_stay(monkeypatch, browser):
    rd = step_1(monkeypatch)
    line = line_of(rd, 'Brick')
    pg = show(browser, rd)
    open_own(pg).set_input_files([file('front.png'), file('fail-side.png', 'blue'), file('top.png', 'red')])
    assert names(own(pg, line, 2)) == ['front.png', 'top.png']
    says(pg, 'The picture could not be added: fail-side.png. The other pictures stay.')
    again = pg.locator('#tpanel button', has_text='Try again')
    assert again.count() == 1
    pg.evaluate('window.__heal = true')
    again.click()
    assert names(own(pg, line, 3)) == ['front.png', 'top.png', 'fail-side.png']
    assert pg.locator('#tpanel button', has_text='Try again').count() == 0 and 'could not be added' not in pg.locator('#tpanel').text_content() and not pg.errors, pg.errors
    pg.close()


def test_a_wrong_type_and_a_file_over_15_mb_are_refused_by_name_and_the_others_stay(monkeypatch, browser):
    rd = step_1(monkeypatch)
    line = line_of(rd, 'Brick')
    pg = show(browser, rd)
    huge = {'name': 'huge.png', 'mimeType': 'image/png', 'buffer': b'x' * (15 * 1024 * 1024 + 1)}
    open_own(pg).set_input_files([file('notes.gif', 'blue', 'image/gif'), file('front.png'), huge])
    assert names(own(pg, line, 1)) == ['front.png']
    says(pg, 'notes.gif is not a PNG, JPEG or WebP picture')
    says(pg, 'huge.png: This picture is larger than 15 MB')
    assert not pg.errors, pg.errors
    pg.close()


def test_the_words_box_stops_at_300_shows_the_count_and_words_alone_are_not_an_answer(monkeypatch, browser):
    rd = step_1(monkeypatch)
    line = line_of(rd, 'Brick')
    pg = show(browser, rd)
    pick = open_own(pg)
    box = pg.locator('#tpanel textarea')
    assert box.get_attribute('maxlength') == '300' and pg.locator('#tpanel .count').text_content() == '0 of 300 characters'
    box.fill('x' * 340)                                                        # more than fits, as a paste would give
    assert len(box.input_value()) == 300 and pg.locator('#tpanel .count').text_content() == '300 of 300 characters'
    pg.locator('#tpanel button', has_text='Save my words').click()             # a comment only, no picture
    says(pg, 'Words alone are not an answer here: add the picture too, or choose another answer.')
    assert line not in answers(pg)
    box = pg.locator('#tpanel textarea')
    box.fill('The brick is hand made, with a rough face.')
    pick = pg.locator('#tpanel input[type=file]')
    pick.set_input_files([file('front.png'), file('side.png', 'blue')])       # two pictures, one comment for the line
    a = own(pg, line, 2)
    assert a['notes'] == 'The brick is hand made, with a rough face.' and 'Your words: “The brick is hand made, with a rough face.”' in pg.locator('#tanswer').text_content()
    box = pg.locator('#tpanel textarea')
    assert box.input_value() == 'The brick is hand made, with a rough face.'
    box.fill('The brick is wire cut.')                                         # changed after the pictures: said as not saved until it is
    says(pg, 'Your words are not saved yet')
    pg.locator('#tpanel button', has_text='Save my words').click()
    pg.wait_for_function('l => window.__answers[l].notes === "The brick is wire cut."', arg=line)
    assert names(answers(pg)[line]) == ['front.png', 'side.png'] and 'not saved yet' not in pg.locator('#tpanel').text_content()
    seed = answers(pg)
    pg.close()
    pg = show(browser, rd, seed=seed)                                          # a reload keeps the words too
    open_own(pg)
    assert pg.locator('#tpanel textarea').input_value() == 'The brick is wire cut.' and not pg.errors, pg.errors
    pg.close()


def test_a_real_person_keeps_one_photo_and_the_box_says_so(monkeypatch, browser):
    rd = step_1(monkeypatch)
    line = line_of(rd, 'The mason')
    pg = show(browser, rd)
    pick = open_own(pg, 'The mason')
    assert pick.get_attribute('multiple') is None and 'One photo of this person' in pg.locator('#tpanel').text_content() and 'three' not in pg.locator('#tpanel').text_content().lower()
    pick.set_input_files(file('him.png'))                                      # the words of permission first, as before
    says(pg, "Write first that you have this person's permission")
    assert line not in answers(pg)
    pg.locator('#tpanel input[type=text]').fill('He agreed that we use his photo.')
    pg.locator('#tpanel textarea').fill('He wears the cap low.')
    pg.locator('#tpanel input[type=file]').set_input_files(file('him.png'))
    a = own(pg, line, 1)
    assert a['permission'] == 'He agreed that we use his photo.' and a['notes'] == 'He wears the cap low.' and names(a) == ['him.png']
    pg.locator('#tpanel input[type=file]').set_input_files(file('him-2.png', 'blue'))
    says(pg, ONE)
    assert names(answers(pg)[line]) == ['him.png'] and answers(pg)[line]['permission'] == 'He agreed that we use his photo.' and not pg.errors, pg.errors
    pg.close()


def test_an_answer_in_the_older_shape_is_read_as_a_list_of_one(monkeypatch, browser):
    rd = step_1(monkeypatch)
    line, item = line_of(rd, 'Brick'), next(l for l in rd['lines'] if l.get('name') == 'Brick')
    older = {line: {'key': item['key'], 'item': item['item'], 'choice': 'own', 'notes': '', 'at': 'x', 'permission': '',
                    'own': {'id': 'a' * 32, 'url': 'data:image/png;base64,' + base64.b64encode(picture()).decode(), 'name': 'mine.png', 'type': 'image/png', 'size': 5}}}
    pg = show(browser, rd, seed=older)
    open_own(pg)
    assert [t.strip() for t in pg.locator('#tpanel .ownlist li span').all_text_contents()] == ['mine.png'] and pg.locator('#tanswer img.ownpic').count() == 1
    assert 'My own picture: mine.png.' in pg.locator('#tanswer').text_content()
    pg.locator('#tpanel input[type=file]').set_input_files(file('second.png', 'blue'))
    a = own(pg, line, 2)
    assert isinstance(a['own'], list) and names(a) == ['mine.png', 'second.png'] and not pg.errors, pg.errors
    pg.close()


def test_the_sets_screen_takes_up_to_three_with_the_words_too(browser):
    rd = copy.deepcopy(SETS)
    l = next(x for x in rd['lines'] if x['state'] == 'open' and x.get('own') and not x['own']['person'] and x.get('pics'))
    assert l['own']['max'] == 3 and rd['layout']['words']['own']['most'] == MOST
    pg = show(browser, rd, wait='#smain .swrap')
    go(pg, l)
    pg.locator('#smain [data-act="own"]').click()
    assert pg.locator('#spanel textarea').get_attribute('maxlength') == '300' and 'Up to three pictures of this thing' in pg.locator('#spanel').text_content()
    pg.locator('#spanel textarea').fill('The real one is narrower.')
    pg.locator('#spanel input[type=file]').set_input_files([file('a.png'), file('b.png', 'blue'), file('c.png', 'red'), file('d.png', 'green')])
    a = own(pg, l['line'], 3)
    says(pg, MOST, '#spanel')
    assert names(a) == ['a.png', 'b.png', 'c.png'] and a['notes'] == 'The real one is narrower.' and a['item'] == l['item']
    assert pg.locator('#sanswer img.ownpic').count() == 3 and pg.locator('#spanel .ownlist li').count() == 3 and not pg.errors, pg.errors
    pg.close()
