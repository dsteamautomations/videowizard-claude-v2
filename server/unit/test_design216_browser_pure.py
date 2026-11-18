"""design/216, the page checks: step 5 of the references ("the sets") as on the trial SK corrected, `plugin/pages/decisions.html` drawn in a
headless browser from a local copy with VW-24's round of 18 Nov (`d216_sets_round.json`, text only, in the shape the 0.113.0 server sends) and
with the round the server builds from the shared fixture (`d213_sets_round.json`, every case), and the stand-in for the page's database of
design/212's page checks (no product server, no network). Every label is read from the round file: the page holds none of its own.
Skipped where Playwright or its browser is not installed. Set VW_SHOTS to a folder to keep screenshots."""
import copy
import json
import re
from pathlib import Path

import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import SIZES, answers, browser, shot, show   # noqa: F401 (`browser` is the fixture)

VW24 = json.loads((Path(__file__).with_name('d216_sets_round.json')).read_text(encoding='utf-8'))
EVERY = json.loads((Path(__file__).with_name('d213_sets_round.json')).read_text(encoding='utf-8'))
SIZES.setdefault('800', {'width': 800, 'height': 900})
W = VW24['layout']['words']['sets']
COST = re.compile(r'\b(price|priced|paid|free|cost|costs)\b|₹', re.I)


def by(doc):
    return {l['key']: l for l in doc['lines']}


L = by(VW24)
DECK, MASON, ROOM, REST = L['set:SITE_DECK'], L['set:MASON'], L['set:ROOM'], L['sets:rest']
TODO = [l for l in VW24['lines'] if l['state'] == 'open' and l['key'] != 'sets:rest']


def made(l):
    return [p for p in l['pics'] if not p.get('ref_only')]


def btn(l, act):
    return next(b for b in l['buttons'] if b['act'] == act)


def doc(base=VW24, change=None):
    d = copy.deepcopy(base)
    if change:
        change(by(d), d)
    return d


def page(browser, d=None, size='1366', scheme='light'):
    return show(browser, d or doc(), size, scheme, wait='#smain .swrap')


def go(pg, l):
    pg.locator('#srail .srow', has=pg.locator('.snm', has_text=re.compile('^' + re.escape(l.get('name') or l['title']) + '$'))).first.click()
    pg.wait_for_function('n => (document.querySelector("#smain .sname") || {}).textContent === n', arg=l.get('name') or l['title'])
    if l['state'] == 'open' and l.get('pics'):
        pg.wait_for_function("![...document.querySelectorAll('#smain .sbar button')].some(b => b.disabled)")   # its pictures have shown


def bar(pg):
    return [' '.join(t.split()) for t in pg.locator('#smain .sbar button').all_text_contents()]


def rail(pg):
    return [' '.join(t.split()) for t in pg.locator('#srail > ul:first-of-type .srow').all_text_contents()]


def foot(pg):
    return ' '.join(pg.locator('#sfoot > *').all_text_contents())


def clean(pg):
    text = pg.locator('body').inner_text()
    assert not COST.search(text), COST.search(text).group(0)
    assert pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not pg.errors, pg.errors


@pytest.mark.parametrize('size,scheme', [('1366', 'light'), ('1920', 'dark')])
def test_the_screen_as_on_the_trial(browser, size, scheme):
    pg = page(browser, size=size, scheme=scheme)
    # A10, A11: only what needs an answer, numbered, the other sets as the last row; one count, at the bottom; "settled earlier" folded
    assert pg.locator('#sets').is_visible() and pg.locator('#things').is_hidden() and pg.locator('#wrap').is_hidden()
    assert rail(pg) == [f'{n}{l.get("name") or l["title"]}' for n, l in enumerate(TODO + [REST], 1)] and REST['name'] == 'The other 17 sets'
    assert pg.locator('#srail [data-fold="settled"] span').text_content() == W['settled'] and pg.locator('#srail [data-fold="settled"]').text_content().endswith('14') and pg.locator('#srail .squiet').count() == 0
    assert foot(pg) == '0 of 4 answered. ' + W['foot_wait']
    assert pg.locator('#sstep').text_content() == VW24['step'] and pg.locator('#shelp').text_content() == W['help']
    # A15: no chips, no "4 of 34", no auto-advance, no "Next to judge", no keys, no box of the waiting sets, no radio under a picture
    assert pg.locator('#sets .tchip, #sets [type=checkbox], #sets .tpick, #sets [role=radio], #sets .tprop').count() == 0
    assert not re.search(r'\b\d+ of 34\b|Auto-advance|Next to judge|\bKeys\b', pg.locator('#sets').inner_text())
    # A14: Inter 14 px for the text, Space Grotesk 20 px for the thing's name
    first = TODO[0]
    assert pg.locator('#smain .sname').text_content() == first['name']
    font = pg.evaluate("[getComputedStyle(document.querySelector('#sets')).fontSize, getComputedStyle(document.querySelector('#sets')).fontFamily, getComputedStyle(document.querySelector('#smain .sname')).fontSize, getComputedStyle(document.querySelector('#smain .sname')).fontFamily]")
    assert font[0] == '14px' and font[1].startswith('Inter') and font[2] == '20px' and font[3].startswith('"Space Grotesk"')
    shot(pg, f'd216-{size}-{scheme}')
    clean(pg)
    pg.close()


def test_one_set_one_large_picture_one_answer(browser):
    pg = page(browser)
    go(pg, DECK)
    m = made(DECK)
    # A1: one large picture, the small ones in a row below it, the answer beside it
    assert pg.locator('#sbig figure').count() == 1 and pg.locator('#sset .sth').count() == 3 and pg.locator('#sfootage .sth').count() == 3
    big, strip, side = (pg.locator(s).bounding_box() for s in ('#sbig', '#sset', '.sside'))
    assert strip['y'] >= big['y'] + big['height'] - 1 and side['x'] >= big['x'] + big['width'] - 1
    assert ' '.join(pg.locator('#smain .sbigcap').text_content().split()).startswith(f"{m[0]['name']} · {m[0]['view']}") and pg.locator('#smain .spill').text_content() == W['main']
    # A3: one answer for the whole set
    assert pg.locator('#sansh').text_content() == DECK['answer_head'] == 'Your answer for the whole set (pictures A, B and C)'
    assert DECK['answer_note'].startswith('One answer covers all 3 pictures') and pg.locator('#smain .soneset').text_content() == DECK['answer_note']
    assert bar(pg) == ['Make all 3 again ' + W['suggested'], 'Approve all 3', 'Minor corrections'] and pg.locator('#smain .sbar .primary').count() == 1
    # A4: what belongs to picture A is under it; the answer column speaks of the set only
    assert pg.locator('#sthis b').first.text_content() == m[0]['check_head'] and pg.locator('#sthis li').all_text_contents() == m[0]['faults']
    pg.locator('#sset .sth').nth(1).click()
    assert pg.locator('#sthis li').all_text_contents() == m[1]['faults'] and len(m[1]['faults']) == 2
    assert 'Picture B' not in pg.locator('.sside').inner_text()
    # A5: Claude's recommendation, one coloured line with the first sentence; "more" opens the rest
    rec = pg.locator('#srec')
    assert rec.locator('b').text_content() == DECK['rec']['head'] == 'Claude recommends: make it again' and DECK['rec']['first'] in rec.text_content() and DECK['rec']['more'] not in rec.text_content()
    assert 'bad' in rec.get_attribute('class')
    pg.locator('#smore').click()
    assert DECK['rec']['more'] in pg.locator('#srec').text_content()
    # B4: the place says what it waits for
    assert pg.locator('#swaits').text_content() == DECK['things_wait'] == 'This place shows the Mangalore clay roof tile, whose set is not approved yet: answer that first, or it is made from words.'
    # A9: the details, folded, in the server's rows
    titles = [d[0] for d in DECK['details']]
    assert pg.locator('.smore .sacc > button span:first-child').all_text_contents() == titles and pg.locator('.smore .sbody').count() == 0
    pg.locator('.smore [data-acc="d0"]').click()
    assert pg.locator('.smore .sbody li').all_text_contents() == DECK['check']['lines']
    # A8: "Use my own picture instead", a link under the buttons
    own = pg.locator('.sside [data-act="own"]')
    assert own.text_content() == DECK['own']['label'] == 'Use my own picture instead' and own.bounding_box()['y'] > pg.locator('#smain .sbar').bounding_box()['y']
    own.click()
    assert pg.locator('#spanel input[type=file]').count() == 1
    clean(pg)
    pg.close()


def test_the_footage_is_shown_beside_the_set_never_in_its_place(browser):
    pg = page(browser)
    go(pg, DECK)
    foot = [p for p in DECK['pics'] if p.get('ref_only')]
    pg.locator('#sfootage .sth').nth(2).click()                                                              # A2: a footage picture clicked
    caps = pg.locator('#sbig figcaption').all_text_contents()
    assert pg.locator('#sbig figure').count() == 2 and caps == [made(DECK)[0]['set_cap'], foot[2]['cmp_cap']] == ['The set: picture A', 'Your footage, to compare: its fixed things']
    pg.locator('#scompare').click()                                                                          # stop comparing
    assert pg.locator('#sbig figure').count() == 1
    pg.locator('#sset .sth').nth(1).click()
    pg.locator('#scompare').click()                                                                          # by default the footage picture in the same position
    assert pg.locator('#sbig figcaption').all_text_contents() == ['The set: picture B', foot[1]['cmp_cap']]
    pg.close()


def test_the_footage_compare_with_more_or_fewer_footage_pictures(browser):
    one = doc(change=lambda l, d: l['set:SITE_DECK'].update(pics=[p for p in l['set:SITE_DECK']['pics'] if not p.get('ref_only')][:0] + [p for p in l['set:SITE_DECK']['pics'] if p.get('ref_only')][:1] + made(l['set:SITE_DECK'])))
    pg = page(browser, one)
    go(pg, DECK)
    pg.locator('#sset .sth').nth(2).click()
    pg.locator('#scompare').click()                                                                          # fewer footage pictures than set pictures: the last
    assert pg.locator('#sbig figcaption').all_text_contents() == ['The set: picture C', 'Your footage, to compare: the whole place']
    pg.close()


def test_approving_against_advice_asks_once_and_undo_takes_the_mark_away(browser):
    pg = page(browser)
    go(pg, DECK)
    a = made(DECK)
    pg.locator('#smain [data-act="approve"]').click()                                                        # A6
    assert pg.locator('#spanel label').text_content() == DECK['sure']['ask'] == "Claude's check found 4 faults in this set. Approve it all the same?"
    assert answers(pg) == {}
    pg.locator('#sback').click()
    assert pg.locator('#spanel').count() == 0 and answers(pg) == {}
    pg.locator('#sset .sth').nth(1).click()                                                                  # A7: B made the main picture
    pg.locator('#smainpick').click()
    assert pg.locator('#smain .spill').count() == 1 and pg.locator('#sthis #smainpick').count() == 0
    pg.locator('#smain [data-act="approve"]').click()
    pg.locator('#ssure').click()
    got = answers(pg)[DECK['line']]
    assert got['choice'] == a[1]['choice'] and got['key'] == DECK['key'] and got['item'] == DECK['item']   # the contract: the same answer as before
    row = pg.locator('#srail .srow', has=pg.locator('.snm', has_text=DECK['name']))
    assert 'against' in row.get_attribute('class') and row.locator('.sst').text_content() == W['against']
    text = pg.locator('#sanswer').text_content()
    assert a[1]['say'] in text and W['against_say'] in text and a[1]['say'] == 'All 3 pictures approved as one set. Later pictures start from picture B.'
    pg.locator('#sundo').click()
    pg.wait_for_function('() => Object.keys(window.__answers).length === 0')
    assert 'against' not in (row.get_attribute('class') or '') and row.locator('.sst').count() == 0
    pg.close()


def test_a_person_one_answer_no_main_link_no_footage_and_the_count(browser):
    pg = page(browser)
    go(pg, MASON)
    assert pg.locator('#sfootage').count() == 0 and pg.locator('#scompare').count() == 0                       # a set with no footage picture: no compare
    pg.locator('#sset .sth').nth(1).click()
    assert pg.locator('#smainpick').count() == 0                                                             # a person is always A
    assert bar(pg) == ['Approve all 3 ' + W['suggested'], 'Minor corrections', 'Make all 3 again']
    assert pg.locator('#sthis').text_content().strip() == made(MASON)[1]['check_head'] + ' ' + made(MASON)[1]['check_none'] == "Claude's check of picture B: no fault found."
    pg.locator('#smain [data-act="approve"]').click()                                                        # with the advice: no question
    assert answers(pg)[MASON['line']]['choice'] == 'yes'
    row = pg.locator('#srail .srow', has=pg.locator('.snm', has_text=MASON['name']))
    assert 'done' in row.get_attribute('class') and row.locator('.sst').text_content() == W['done']['approve'] and row.locator('.sdot').text_content() == '✓'
    assert foot(pg).startswith('1 of 4 answered.')                                                           # A11
    pg.wait_for_function('n => document.querySelector("#smain .sname").textContent !== n', arg=MASON['name'])   # the next that needs an answer opens
    pg.close()


def test_the_words_box_and_its_tick(browser):
    pg = page(browser)
    go(pg, MASON)
    fix = btn(MASON, 'fix')
    pg.locator('#smain [data-act="fix"]').click()
    pg.locator('#sfixsend').click()
    assert pg.locator('#smsg').text_content() == W['fix_need'] and answers(pg) == {}
    pg.locator('#sfix').fill('Make the sleeves longer.')
    pg.locator('#sall').check()
    pg.locator('#sfixsend').click()
    got = answers(pg)[MASON['line']]
    assert got['choice'] == fix['all']['choice'] and got['notes'] == 'Make the sleeves longer.' and fix['all']['say'].replace('{words}', 'Make the sleeves longer.') in pg.locator('#sanswer').text_content()
    pg.close()


def test_the_family_room_held_by_a_retired_rule_can_be_made(browser):
    pg = page(browser)
    go(pg, ROOM)
    assert pg.locator('#shead b').text_content() == ROOM['head'] == 'The rule that held this set back no longer applies to a set: it can be made now.'   # B3
    assert 'landmark' not in pg.locator('#sets').inner_text() and pg.locator('#srefused').count() == 0
    assert bar(pg) == ['Make it', 'Go on without a reference'] and 'primary' in pg.locator('#smain [data-act="make"]').get_attribute('class')
    pg.locator('#smain [data-act="leave"]').click()
    assert pg.locator('#spanel label').text_content() == ROOM['loss']['text'] and answers(pg) == {}
    pg.locator('#scancel').click()
    pg.locator('#smain [data-act="make"]').click()
    assert answers(pg)[ROOM['line']]['choice'] == 'make'
    pg.close()


def test_the_other_sets_and_the_end_card(browser):
    pg = page(browser)
    pg.locator('#srail .srow', has=pg.locator('.snm', has_text=REST['name'])).click()
    make, some = pg.locator('#smain [data-rest="rest"]'), pg.locator('#smain [data-rest="some"]')
    assert make.text_content() == 'Make the other 17' and some.text_content() == 'Make only some of them' and make.is_disabled() and some.is_disabled()   # A12
    assert pg.locator('#sbefore b').text_content() == W['rest_before']
    pg.locator('.smore [data-acc="names"]').click()
    assert len(pg.locator('.smore .sbody li').all_text_contents()) == 17
    for l, act, more in ((MASON, 'approve', None), (ROOM, 'make', None)):
        go(pg, l)
        pg.locator(f'#smain [data-act="{act}"]').click()
    go(pg, DECK)
    pg.locator('#smain [data-act="again"]').click()
    pg.locator('#sagain').click()
    pg.locator('#srail .srow', has=pg.locator('.snm', has_text=REST['name'])).click()
    assert make.is_enabled()
    some.click()
    loss = btn(REST, 'rest_out')['loss']
    assert pg.locator('#spanel label').text_content() == loss['head'] and pg.locator('#spanel table tbody tr').count() == len(loss['rows']) and pg.locator('#srestout').text_content() == loss['button']
    pg.locator('#scancel').click()
    make.click()
    assert answers(pg)[REST['line']]['choice'] == 'rest' and foot(pg).startswith('4 of 4 answered.') and W['foot_done'] in foot(pg)
    pg.wait_for_selector('#send li')
    items = [' '.join(t.split()) for t in pg.locator('#send li').all_text_contents()]   # A13: what will happen, thing by thing
    assert pg.locator('#send h2').text_content() == W['end_head'] and len(items) == 4
    assert items[0] == f"{DECK['name']}: {btn(DECK, 'again')['say']}" and items[-1] == f"{REST['name']}: {btn(REST, 'rest')['say']}"
    # a judged answer taken back: "Make the other 17" no longer stands
    go(pg, MASON)
    pg.locator('#sundo').click()
    pg.wait_for_function('l => !window.__answers[l]', arg=REST['line'])
    pg.close()


def test_the_keys_and_the_help(browser):
    pg = page(browser)
    names = [l.get('name') or l['title'] for l in TODO + [REST]]
    pg.keyboard.press('ArrowRight')
    assert pg.locator('#smain .sname').text_content() == names[1]
    pg.keyboard.press('ArrowLeft')
    pg.keyboard.press('ArrowLeft')
    assert pg.locator('#smain .sname').text_content() == names[-1]
    go(pg, MASON)
    pg.locator('#smain [data-act="again"]').click()
    assert pg.locator('#spanel').count() == 1
    pg.keyboard.press('Escape')
    assert pg.locator('#spanel').count() == 0
    pg.locator('#shelp').click()
    assert pg.locator('#smain').inner_text().count(VW24['layout']['help'][1]) == 1 and W['keys'] in pg.locator('#smain').inner_text()
    pg.close()


def test_edge_cases_one_picture_not_checked_not_sure_large_picture_missing(browser):
    def change(l, d):
        p = made(l['set:MASON'])[2]
        p.update(faults=[], check_head='', check_none='Claude could not check this picture.')
        l['set:MASON']['rec'].update(do='doubt', label='Look closely', head='Claude recommends: look closely')
        for b in l['set:MASON']['buttons']:
            b.pop('sug', None)
    pg = page(browser, doc(change=change))
    go(pg, MASON)
    pg.locator('#sset .sth').nth(2).click()
    assert pg.locator('#sthis').text_content().strip() == 'Claude could not check this picture.' and 'no fault' not in pg.locator('#sthis').text_content()   # never "no fault found"
    assert 'doubt' in pg.locator('#srec').get_attribute('class') and W['suggested'] not in ' '.join(bar(pg)) and pg.locator('#smain .sbar .primary').count() == 0   # "not sure": neutral
    pg.locator('#smain [data-act="approve"]').click()
    assert pg.locator('#spanel').count() == 0 and answers(pg)[MASON['line']]['choice'] == 'yes'               # no against-advice question
    assert pg.locator('.snolarge').first.is_visible() and pg.locator('.snolarge').first.text_content() == W['no_large']   # the large pictures did not upload
    pg.close()
    single = next(l for l in EVERY['lines'] if l.get('case') == 'judge' and len(made(l)) == 1)
    pg = show(browser, EVERY, wait='#smain .swrap')
    go(pg, single)
    assert pg.locator('#sansh').text_content() == 'Your answer' and pg.locator('#smain .soneset').text_content() == 'This one picture is the reference.'
    assert not any('all' in b.lower() for b in bar(pg)) and pg.locator('#smainpick').count() == 0 and pg.locator('#smain .spill').count() == 0
    assert pg.locator('#smain .sgrp h4').first.text_content() == 'The picture that was made'
    pg.close()


def test_every_case_the_server_sends_draws_and_answers(browser):
    pg = show(browser, EVERY, wait='#smain .swrap')
    for l in [l for l in EVERY['lines'] if l['state'] == 'open' and l['key'] != 'sets:rest']:
        go(pg, l)
        assert bar(pg) == [b['label'] + (' ' + W['suggested'] if b.get('sug') else '') for b in l['buttons']], l['key']
        if l.get('kept'):
            assert l['kept'] in pg.locator('#sanswer').text_content()
    clean(pg)
    pg.close()


def test_a_narrow_window_puts_the_answer_under_the_picture(browser):
    pg = page(browser, size='800')
    go(pg, DECK)
    viewer, side = pg.locator('.sviewer').bounding_box(), pg.locator('.sside').bounding_box()
    assert side['y'] >= viewer['y'] + viewer['height'] - 1 and pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    pg.close()


def test_an_answer_that_cannot_be_saved_says_so(browser):
    pg = page(browser)
    go(pg, ROOM)
    pg.evaluate("window.__answers = new Proxy({}, {set(){ throw Object.assign(new Error('no'), {code: 'denied'}); }})")
    pg.locator('#smain [data-act="make"]').click()
    pg.wait_for_function("(document.querySelector('#smsg') || {}).textContent.includes('Could not save (denied)')")
    pg.close()
