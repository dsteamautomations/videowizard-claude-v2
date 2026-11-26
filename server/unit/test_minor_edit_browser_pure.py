"""Minor corrections as an edit (SK, 25 Nov 2026), the page checks: the marking control of the sets screen on `plugin/pages/decisions.html`,
drawn in a headless browser from a local copy with the round the server builds (`d213_sets_round.json`) and the stand-in for the page's
database and file store of design/212's page checks (no product server, no network, no model). "Mark the place" under the picture and the side
bar's "Minor corrections" open the picture large, in place; one row of tools (Rectangle chosen first, Paint with its brush size, Undo, Redo,
Clear marks); a mark is drawn with the mouse and with a finger, three at most on a picture, each numbered in the list beside the words box;
what the correction does well and poorly stands beside the box; the tick is on and absent on a set of one picture; "Minor corrections" and
"Make again" stand side by side with one line each. What is saved: the words, the marks per picture as fractions of the picture, the tick.
The operator's own picture is marked and corrected the same way. A round of an older server (no `mark`) keeps the words box: that is
`test_design216_browser_pure.test_the_words_box_and_its_tick`. Skipped where Playwright or its browser is not installed."""
import copy

import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import answers, browser   # noqa: F401 (`browser` is the fixture)
from test_design216_browser_pure import btn, go, made
from test_vw25_own_browser_pure import SETS, file, own, show

W = SETS['layout']['words']['sets']['mark']
L = {l['name']: l for l in SETS['lines'] if l.get('name')}
SET, ONE, MASON = L['Thing Site_Deck'], L['The street (one picture)'], L['Thing Mason']
FIX, AGAIN = btn(SET, 'fix'), btn(SET, 'again')
WORDS = 'Take the bucket out.'


def ready(pg):
    """The picture has shown, the canvas lies over it and the two answers can be clicked."""
    pg.wait_for_function("""() => { const c = document.querySelector('#smcv'), b = document.querySelector('#sfixsend'), i = document.querySelector('#smwrap img');
        if (!c || !b || b.disabled || !i || !i.complete) return false; const r = c.getBoundingClientRect(); return r.width > 50 && r.height > 50 && Math.abs(c.width - r.width) < 2; }""")


def marking(pg, l=SET):
    go(pg, l)
    pg.locator('#smarkopen').click()
    ready(pg)


def drag(pg, a, b, steps=4):
    ready(pg)
    pg.locator('#smcv').scroll_into_view_if_needed()
    box = pg.locator('#smcv').bounding_box()
    at = lambda p: (box['x'] + p[0] * box['width'], box['y'] + p[1] * box['height'])
    pg.mouse.move(*at(a))
    pg.mouse.down()
    pg.mouse.move(*at(b), steps=steps)
    pg.mouse.up()


def listed(pg):
    return [' '.join(t.split()) for t in pg.locator('#smlist li').all_text_contents()]


def send(pg, words=WORDS):
    pg.locator('#sfix').fill(words)
    pg.locator('#sfixsend').click()


def near(got, want):
    return len(got) == len(want) and all(abs(g - w) < 0.02 for g, w in zip(got, want))


def test_the_marking_control_opens_in_place_with_its_tools(browser):
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')
    go(pg, SET)
    assert pg.locator('#smarkopen').text_content() == W['open'] and pg.locator('#smark').count() == 0
    pg.locator('#smarkopen').click()
    ready(pg)
    assert [' '.join(t.split()) for t in pg.locator('#smark .smtools button').all_text_contents()] == [W['rect'], W['paint'], W['undo'], W['redo'], W['clear'], W['close']]
    assert pg.locator('#smrect').get_attribute('aria-pressed') == 'true' and pg.locator('#smpaint').get_attribute('aria-pressed') == 'false'   # the rectangle first
    assert pg.locator('#smbrush').is_disabled() and all(pg.locator(i).is_disabled() for i in ('#smundo', '#smredo', '#smclear'))
    assert pg.locator('#smtold').text_content() == W['told'] and 'It does well' in W['told'] and 'It does poorly' in W['told']
    assert pg.locator('#severy').is_checked() and pg.locator('label[for=severy]').text_content() == FIX['every']['label'] and listed(pg) == [W['none']]
    assert pg.evaluate("getComputedStyle(document.querySelector('#smcv')).touchAction") == 'none'      # a finger draws, the page does not scroll under it
    told, box = pg.locator('#smtold').bounding_box(), pg.locator('#sfix').bounding_box()
    assert told['x'] > box['x'] + box['width'] - 2 and abs(told['y'] - box['y']) < 60                    # beside the words box
    both = pg.locator('#smark .smdo > div')
    assert [' '.join(t.split()) for t in both.all_text_contents()] == [FIX['label'] + W['fix_line'], AGAIN['label'] + W['again_line']]
    a, b = both.nth(0).bounding_box(), both.nth(1).bounding_box()
    assert abs(a['y'] - b['y']) < 2 and a['x'] + a['width'] <= b['x'] + 1                                # side by side
    pg.keyboard.press('Escape')                                                                          # closed: the set as it was
    pg.wait_for_selector('#smark', state='detached')
    assert pg.locator('#smarkopen').count() == 1
    pg.locator('#smain [data-act="fix"]').click()                                                        # the side bar's button opens the same view
    ready(pg)
    pg.locator('#smclose').click()
    assert pg.locator('#smark').count() == 0 and answers(pg) == {} and not pg.errors, pg.errors
    pg.close()


def test_a_rectangle_three_at_most_undo_redo_and_clear(browser):
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')
    marking(pg)
    drag(pg, (0.1, 0.1), (0.3, 0.3))
    assert listed(pg) == ['1: a rectangle Remove']
    drag(pg, (0.5, 0.5), (0.5, 0.5))                                                                     # a click with no drag is no mark
    assert listed(pg) == ['1: a rectangle Remove']
    drag(pg, (0.4, 0.1), (0.6, 0.3))
    drag(pg, (0.7, 0.6), (0.9, 0.9))
    assert len(listed(pg)) == 3 and pg.locator('#smsg').is_hidden()
    drag(pg, (0.1, 0.6), (0.3, 0.9))                                                                     # the fourth is refused, in words
    assert len(listed(pg)) == 3 and pg.locator('#smsg').text_content() == W['most']
    pg.locator('#smundo').click()
    assert len(listed(pg)) == 2 and not pg.locator('#smredo').is_disabled()
    pg.locator('#smredo').click()
    assert len(listed(pg)) == 3 and pg.locator('#smredo').is_disabled()
    pg.locator('#smlist li button').first.click()                                                        # one taken away by its number; the others count again from 1
    assert listed(pg) == ['1: a rectangle Remove', '2: a rectangle Remove']
    pg.locator('#smclear').click()
    assert listed(pg) == [W['none']] and pg.locator('#smclear').is_disabled()
    pg.locator('#smundo').click()                                                                        # clearing is a step too
    assert len(listed(pg)) == 2 and not pg.errors, pg.errors
    pg.close()


def test_paint_its_brush_size_and_a_finger(browser):
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')
    marking(pg)
    pg.locator('#smpaint').click()
    ready(pg)
    assert pg.locator('#smpaint').get_attribute('aria-pressed') == 'true' and not pg.locator('#smbrush').is_disabled()
    pg.evaluate("() => { const b = document.querySelector('#smbrush'); b.value = '10'; b.dispatchEvent(new Event('input', {bubbles: true})); }")
    drag(pg, (0.2, 0.2), (0.6, 0.5), steps=8)
    assert listed(pg) == ['1: painted Remove']
    pg.locator('#smrect').click()
    ready(pg)
    pg.evaluate("""() => { const c = document.querySelector('#smcv'), r = c.getBoundingClientRect();   // a finger: the same pointer events, of the kind "touch"
        const ev = (t, x, y) => c.dispatchEvent(new PointerEvent(t, {pointerType: 'touch', pointerId: 7, isPrimary: true, bubbles: true, cancelable: true, clientX: r.left + x * r.width, clientY: r.top + y * r.height}));
        ev('pointerdown', .2, .6); ev('pointermove', .3, .7); ev('pointermove', .4, .8); ev('pointerup', .4, .8); }""")
    pg.wait_for_function("document.querySelectorAll('#smlist li').length === 2")
    assert listed(pg) == ['1: painted Remove', '2: a rectangle Remove']
    send(pg)
    got = answers(pg)[SET['line']]
    stroke, rect = got['marks'][made(SET)[0]['ref']]
    assert stroke['s'] == 0.1 and len(stroke['p']) >= 4 and len(stroke['p']) % 2 == 0 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in stroke['p'])   # flat: the page's database takes no list of lists
    assert near(stroke['p'][:2], [0.2, 0.2]) and near(stroke['p'][-2:], [0.6, 0.5]) and near(rect['r'], [0.2, 0.6, 0.2, 0.2]) and not pg.errors, pg.errors
    pg.close()


def test_what_is_saved_words_marks_and_the_tick(browser):
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')
    marking(pg)
    drag(pg, (0.1, 0.1), (0.3, 0.3))
    pg.locator('#sfixsend').click()                                                                      # a mark and no words: refused
    assert pg.locator('#smsg').text_content() == W['need'] and answers(pg) == {}
    pg.locator('#smclear').click()
    pg.locator('#severy').uncheck()
    send(pg)                                                                                             # words, no mark and no tick: which picture?
    assert pg.locator('#smsg').text_content() == W['one'] and answers(pg) == {}
    assert pg.locator('#sfix').input_value() == WORDS and not pg.locator('#severy').is_checked()         # a refusal keeps what was written
    drag(pg, (0.1, 0.1), (0.3, 0.3))
    send(pg)
    got = answers(pg)[SET['line']]
    assert got['choice'] == FIX['choice'] == 'correct' and got['notes'] == WORDS and got['every'] is False and list(got['marks']) == [made(SET)[0]['ref']]
    assert near(got['marks'][made(SET)[0]['ref']][0]['r'], [0.1, 0.1, 0.2, 0.2]) and FIX['say'].replace('{words}', WORDS) in pg.locator('#sanswer').text_content()
    seed = answers(pg)
    pg.close()
    pg = show(browser, copy.deepcopy(SETS), seed=seed, wait='#smain .swrap')                             # a reload: the saved answer's marks are shown again
    marking(pg)
    assert listed(pg) == ['1: a rectangle Remove'] and not pg.locator('#severy').is_checked() and not pg.errors, pg.errors   # and the tick as it was saved
    pg.close()
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')                                        # words alone, the tick on: every picture, no mark
    marking(pg)
    send(pg)
    got = answers(pg)[SET['line']]
    assert got['choice'] == 'correct' and got['notes'] == WORDS and got['every'] is True and 'marks' not in got and not pg.errors, pg.errors
    pg.close()


def test_marks_on_several_pictures_and_the_tick_for_every_later_picture(browser):
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')
    marking(pg)
    first, second = made(SET)[0], made(SET)[1]
    drag(pg, (0.1, 0.1), (0.3, 0.3))
    pg.locator('#sall').check()                                                                          # design/215's tick stays: the words for every later picture of the thing
    pg.locator(f'#smset .sth[data-code="{second["code"]}"]').click()                                    # the next picture of the set, marked on its own
    ready(pg)
    assert listed(pg) == [W['none']]
    drag(pg, (0.2, 0.2), (0.4, 0.4))
    drag(pg, (0.6, 0.6), (0.8, 0.8))
    counts = [t.text_content() for t in pg.locator('#smset .sth em').all()]
    assert counts == [W['count'].replace('{n}', '1'), W['count'].replace('{n}', '2')]
    assert pg.locator('#sall').is_checked() and pg.locator('#severy').is_checked()                       # a tick made before the marks is still there after them
    send(pg)
    got = answers(pg)[SET['line']]
    assert got['choice'] == FIX['all']['choice'] and got['every'] is True and {k: len(v) for k, v in got['marks'].items()} == {first['ref']: 1, second['ref']: 2}
    assert not pg.errors, pg.errors
    pg.close()


def test_a_set_of_one_picture_has_no_tick(browser):
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')
    assert 'every' not in btn(ONE, 'fix')
    marking(pg, ONE)
    assert pg.locator('#severy').count() == 0 and pg.locator('#smset').count() == 0 and pg.locator('#sall').count() == 1
    send(pg)
    got = answers(pg)[ONE['line']]
    assert got['choice'] == 'correct' and got['notes'] == WORDS and 'marks' not in got and not pg.errors, pg.errors
    pg.close()


def test_make_again_takes_the_operators_comment(browser):
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')
    marking(pg)
    drag(pg, (0.1, 0.1), (0.3, 0.3))
    pg.locator('#sfix').fill('The deck is too wide.')
    pg.locator('#smagain').click()                                                                       # beside "Minor corrections": a new set, the words go with it, no mark
    got = answers(pg)[SET['line']]
    assert got['choice'] == AGAIN['choice'] == 'no' and got['notes'] == 'The deck is too wide.' and 'marks' not in got
    pg.close()
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')                                        # the side bar's "Make again": the comment box, optional
    go(pg, SET)
    pg.locator('#smain [data-act="again"]').click()
    assert pg.locator('#sagainw').get_attribute('placeholder') == AGAIN['comment']
    pg.locator('#sagainw').fill('Make it narrower.')
    pg.locator('#sagain').click()
    assert answers(pg)[SET['line']]['notes'] == 'Make it narrower.' and answers(pg)[SET['line']]['choice'] == 'no' and not pg.errors, pg.errors
    pg.close()


def test_the_operators_own_picture_is_marked_and_corrected(browser):
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')
    go(pg, SET)
    pg.locator('#smain [data-act="own"]').click()
    pg.locator('#spanel input[type=file]').set_input_files([file('a.png'), file('b.png', 'blue')])
    mine = own(pg, SET['line'], 2)['own']
    pg.wait_for_selector('#spanel [data-own]')
    assert [t.strip() for t in pg.locator('#spanel [data-own]').all_text_contents()] == [W['own'], W['own']]
    pg.locator(f'#spanel [data-own="{mine[1]["id"]}"]').click()                                         # the second of their two pictures
    ready(pg)
    assert pg.locator('#smagain').count() == 0 and pg.locator('#sall').count() == 0 and pg.locator('#severy').is_checked()
    drag(pg, (0.5, 0.2), (0.9, 0.6))
    send(pg, 'Take the pole out.')
    got = answers(pg)[SET['line']]
    assert got['choice'] == 'own' and got['fix'] is True and got['notes'] == 'Take the pole out.' and got['every'] is True and [p['id'] for p in got['own']] == [p['id'] for p in mine]
    assert list(got['marks']) == [mine[1]['id']] and near(got['marks'][mine[1]['id']][0]['r'], [0.5, 0.2, 0.4, 0.4])
    assert FIX['say'].replace('{words}', 'Take the pole out.') in pg.locator('#sanswer').text_content() and not pg.errors, pg.errors   # the answer reads as a correction
    pg.close()


def test_a_persons_own_photo_is_never_corrected(browser):
    assert MASON['own']['person']
    pg = show(browser, copy.deepcopy(SETS), wait='#smain .swrap')
    go(pg, MASON)
    pg.locator('#smain [data-act="own"]').click()
    pg.locator('#spanel input[type=text]').fill('He agreed that we use his photo.')
    pg.locator('#spanel input[type=file]').set_input_files(file('him.png'))
    own(pg, MASON['line'], 1)
    pg.wait_for_selector('#spanel .ownlist li')
    assert pg.locator('#spanel [data-own]').count() == 0 and pg.locator('#smarkopen').count() == 1 and not pg.errors, pg.errors   # the set's own pictures of the person can be
    pg.close()


def test_a_correction_that_was_not_made_is_said_on_its_set_and_a_narrow_window_holds(browser):
    rd = copy.deepcopy(SETS)
    note = 'The correction could not be made: the picture model gave no picture back. The set is as it was.'
    next(l for l in rd['lines'] if l['line'] == SET['line'])['edit_note'] = note
    pg = show(browser, rd, wait='#smain .swrap')
    go(pg, SET)
    assert pg.locator('#seditnote').text_content() == note
    pg.set_viewport_size({'width': 800, 'height': 900})
    pg.locator('#smarkopen').click()
    ready(pg)
    told, box = pg.locator('#smtold').bounding_box(), pg.locator('#sfix').bounding_box()
    assert told['y'] > box['y'] + box['height'] and pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')   # under the box, nothing off the side
    drag(pg, (0.1, 0.1), (0.3, 0.3))
    assert listed(pg) == ['1: a rectangle Remove'] and not pg.errors, pg.errors
    pg.close()
