"""design/213, the page checks: step 2 of the references ("the sets") in the layout of step 1, `plugin/pages/decisions.html` drawn in a
headless browser from a local copy with the round of `d213_sets_round.json` (the contract the server sends) and the stand-in for the page's
database and file store of design/212's page checks (no product server, no network). Every name, count and label is read from the round
file, so the file can be written again from the server's own output. Skipped where Playwright or its browser is not installed.
Set VW_SHOTS to a folder to keep screenshots."""
import copy
import json
import re
from pathlib import Path

import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import answers, browser, gone, picture, saved, shot, show   # noqa: F401 (`browser` is the fixture)

ROUND = json.loads((Path(__file__).with_name('d213_sets_round.json')).read_text(encoding='utf-8'))
LAY = ROUND['layout']
REST = next(l for l in ROUND['lines'] if l['key'] == 'sets:rest')
SETS = [l for l in ROUND['lines'] if l['key'] != 'sets:rest']
COUNTED = [l for l in SETS if l['state'] == 'open']
JUDGE = [l for l in SETS if l['case'] == 'judge']
WAITING = [l for l in SETS if l['key'] in REST['covers']]
KEPT = [l for l in COUNTED if l.get('kept')]
MAKE, OUT = REST['buttons'][0], next(b for b in REST['buttons'] if b.get('loss'))
CHAT_REST = [{'label': OUT['loss']['button']}]   # the words of the button that leaves some out: the server gives the chat's own label (asserted in test_design213_layout_pure)
COST = re.compile(r'\b(price|priced|paid|free|limit|cost|costs)\b|₹', re.I)


def one(pred):
    return next(l for l in SETS if pred(l))


def btn(l, act):
    return next(b for b in l['buttons'] if b['act'] == act)


def acts(l):
    return [b['act'] for b in l.get('buttons') or []]


def made(l):
    return [p for p in l.get('pics') or [] if not p.get('ref_only')]


PLACE = one(lambda l: l.get('pick') and any(p.get('ref_only') for p in l['pics']) and len(made(l)) == 3)     # three footage pictures, three made, one to choose
PERSON = one(lambda l: l['case'] == 'judge' and not l.get('pick') and (l.get('own') or {}).get('person'))   # three made pictures, the check found a fault
SINGLE = one(lambda l: l['case'] == 'judge' and len(made(l)) == 1)
AGAIN = one(lambda l: l.get('asked'))
MOST = one(lambda l: l.get('most'))
CHANGED = one(lambda l: l.get('changed'))
NOTMADE = one(lambda l: l['case'] == 'notmade')
PHOTO = one(lambda l: l['case'] == 'photo')
BACK = one(lambda l: l['case'] == 'back')
SETTLED = one(lambda l: l['case'] == 'settled' and len(l.get('pics') or []) > 1)


def doc(change=None):
    d = copy.deepcopy(ROUND)
    if change:
        change({l['key']: l for l in d['lines']}, d)
    return d


def keep(keys):
    """The round with these lines answered at an earlier visit."""
    return doc(lambda by, d: [by[k].update(kept=by[k]['buttons'][0]['label']) for k in keys])


def open_set(pg, l):
    row = pg.locator('#trail .trow', has=pg.locator('.tnm', has_text=re.compile(f'^{re.escape(l["name"])}$')))
    if not row.is_visible():
        pg.locator('#trail .tgh', has_text=l['group']).click()
    row.click()
    pg.wait_for_function('n => (document.querySelector("#tmain h2") || {}).textContent === n', arg=l['name'])
    pg.wait_for_function("![...document.querySelectorAll('#tmain .tbar button, #tmain .tpick')].some(b => b.disabled)")   # its pictures have shown


def bar(pg):
    return [' '.join(t.split()) for t in pg.locator('#tmain .tbar button').all_text_contents()]


def expected_bar(l):
    out = [b['label'] + (' Suggested' if b.get('sug') else '') for b in l['buttons']]
    if l.get('own'):
        out.insert(next((i for i, b in enumerate(l['buttons']) if i and b['act'] == 'leave'), len(out)), l['own']['label'])
    return out


def clean(pg):
    """No cost word in what the page shows now, no sideways scroll, no error in the console."""
    text = pg.locator('body').inner_text()
    assert not COST.search(text), COST.search(text).group(0)
    assert pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not pg.errors, pg.errors


def strip(pg):
    return pg.locator('#tanswer p').text_content()


@pytest.mark.parametrize('size,scheme', [('1366', 'light'), ('1366', 'dark'), ('1920', 'light'), ('1920', 'dark')])
def test_the_sets_in_the_layout_of_step_1(browser, size, scheme):
    pg = show(browser, doc(), size, scheme)
    tag = f'{size}-{scheme}'
    pg.locator('#tauto').uncheck()
    # the top bar and the list: the groups in the server's order with their counts, "Settled" folded
    assert pg.locator('#things').is_visible() and pg.locator('#wrap').is_hidden()
    assert pg.locator('#tstep').text_content() == ROUND['step'] and pg.locator('#tnextopen').text_content() == 'Next to judge'
    assert pg.locator('#tprogt').text_content() == f'{len(KEPT)} of {len(COUNTED)} judged'
    groups = [g for g in LAY['groups'] if any(l['group'] == g for l in SETS)]
    assert pg.locator('#trail .tgh span').all_text_contents() == groups
    assert [' '.join(t.split()) for t in pg.locator('#trail .tgh').all_text_contents()] == [g + str(sum(l['group'] == g for l in SETS)) for g in groups]
    assert pg.locator('#trail .tgh').evaluate_all("b => b.map(x => x.getAttribute('aria-expanded'))") == ['false' if all(l['state'] == 'recorded' for l in SETS if l['group'] == g) else 'true' for g in groups]
    assert pg.locator('#trail [data-filter]').all_text_contents() == ['All', 'To judge', 'Judged']
    assert pg.locator('#trail .tprop p').first.text_content() == REST['head']                                    # the waiting sets, on top of the list
    first = next(l for l in COUNTED if not l.get('kept'))
    assert pg.locator('#tmain h2').text_content() == first['name']                                               # the first set to judge
    assert pg.locator('#trail .trow[aria-current] .ttag').text_content() == first['tag']
    assert pg.evaluate('getComputedStyle(document.body).backgroundColor') == ('rgb(16, 22, 28)' if scheme == 'dark' else 'rgb(245, 247, 248)')
    # a judged set with three footage pictures and three made pictures: one view, the buttons under the pictures
    open_set(pg, PLACE)
    assert pg.locator('#tmain .tfcell').count() == 3 and pg.locator('#tmain .ttile').count() == 3
    assert pg.locator('#tmain .tlab').all_text_contents() == ['Compare with your footage', 'The set that was made']
    assert len(set(pg.evaluate("[...document.querySelectorAll('#tmain .ttile')].map(e => Math.round(e.getBoundingClientRect().top))"))) == 1
    assert bar(pg) == expected_bar(PLACE) and pg.locator('#tmain .tbar .go').count() == sum(1 for b in PLACE['buttons'] if b.get('sug'))
    assert pg.evaluate("document.querySelector('#tmade').getBoundingClientRect().bottom <= window.innerHeight")   # the buttons and the line under them are in view
    assert pg.evaluate("(() => { const m = document.querySelector('#tmain'); return m.scrollHeight <= m.clientHeight; })()")   # nothing to scroll for
    assert pg.evaluate("document.querySelector('#tmain .tpics').getBoundingClientRect().bottom <= document.querySelector('#tmain .tbar').getBoundingClientRect().top")
    assert pg.evaluate("document.querySelector('#tmain .tbar').getBoundingClientRect().top - document.querySelector('#tmain .tpics').getBoundingClientRect().bottom") < 20   # directly under
    assert pg.locator('#tmade').text_content() == LAY['made']
    assert pg.locator('#tmain .tletter').all_text_contents() == [p['letter'] for p in made(PLACE)]
    assert pg.locator('#tmain .tflag').count() == sum(1 for p in PLACE['pics'] if p.get('flag')) and pg.locator('#tmain .tweak').count() == sum(1 for p in PLACE['pics'] if p.get('weak'))
    assert pg.locator('#tdiffers').is_visible() and pg.locator('#tdiffers').text_content() == PLACE['differs']   # said openly
    assert pg.locator('#tmain .tsuggest').text_content().startswith('Claude suggests: ' + PLACE['rec']['label']) and pg.locator('#twhy').is_hidden()
    pg.locator('#twhyb').click()
    assert pg.locator('#twhy').text_content() == PLACE['rec']['reason']
    assert pg.locator('#tcheckb').text_content() == PLACE['check']['chip'] and pg.locator('#tcheck').is_hidden()   # one chip for the check
    pg.locator('#tcheckb').click()
    assert pg.locator('#tcheck').text_content() == PLACE['check']['by'] + ''.join(PLACE['check']['lines'])
    shot(pg, f'check-open-{tag}')
    assert pg.locator('#tlook').is_hidden() and pg.locator('#tlookb').text_content() == 'What the image model did'
    pg.locator('#tlookb').click()
    assert pg.locator('#tlook p').all_text_contents() == ['It chose: ' + PLACE['look']['chose'], 'It set aside: ' + PLACE['look']['aside']]
    pg.keyboard.press('Escape')
    assert pg.locator('#tlook').is_hidden() and pg.locator('#tcheck').is_hidden() and pg.locator('#twhy').is_hidden()
    pg.locator('#tshots').click()
    assert pg.locator('#tshots').text_content() == PLACE['shots'] and pg.locator('#tused').text_content() == PLACE['used']
    pg.locator('#tinfo0').click()
    assert pg.locator('#tsaw0').text_content() == 'What Claude saw: ' + made(PLACE)[0]['note']
    pg.keyboard.press('Escape')
    # which picture is the reference: none at the start; Approve is refused until one is chosen
    picks = lambda: pg.locator('#tmain .tpick').evaluate_all("b => b.map(x => x.getAttribute('aria-checked'))")
    assert picks() == ['false'] * 3 and pg.locator('#tmain .tpick').first.text_content() == 'Use as the reference1'
    pg.locator('#tmain [data-act="approve"]').click()
    assert pg.locator('#tmsg').text_content() == LAY['pick'] and PLACE['line'] not in answers(pg)
    shot(pg, f'place-{tag}')
    pg.locator('#tpick2').click()
    assert picks() == ['false', 'true', 'false'] and pg.locator('#tpick2').text_content() == 'The reference2' and pg.locator('#tmsg').is_hidden()
    pg.locator('#tmain [data-act="approve"]').click()
    chosen = made(PLACE)[1]
    a = saved(pg, PLACE['line'], chosen['choice'])
    assert (a['key'], a['item'], a['notes']) == (PLACE['key'], PLACE['item'], '') and 'pics' not in a
    assert pg.locator('#tanswer').text_content() == 'Your answer: ' + chosen['say'] + 'Undo'
    assert pg.locator('#trail .trow[aria-current] .ttag').text_content() == btn(PLACE, 'approve')['label']
    assert pg.locator('#tprogt').text_content() == f'{len(KEPT) + 1} of {len(COUNTED)} judged'
    pg.locator('#tpick3').click()                                                                               # the answer follows the choice
    assert saved(pg, PLACE['line'], made(PLACE)[2]['choice']) and strip(pg) == 'Your answer: ' + made(PLACE)[2]['say']
    pg.locator('#tundo').click()
    gone(pg, PLACE['line'])
    assert pg.locator('#tanswer').count() == 0
    # the large picture is the page's own: the made pictures, then the footage
    pg.locator('#tmain .timg').first.click()
    assert pg.locator('.zoom').count() == 1 and f'(1 of {len(PLACE["pics"])})' in pg.locator('.zoom').text_content()
    pg.keyboard.press('Escape')
    assert pg.locator('.zoom').count() == 0
    clean(pg)
    # a person's set: no picture to choose; Approve writes the button's own choice
    open_set(pg, PERSON)
    assert pg.locator('#tmain .tpick').count() == 0 and pg.locator('#tmain .ttile').count() == len(made(PERSON)) and bar(pg) == expected_bar(PERSON)
    assert pg.locator('#tmain .trule').text_content() == PERSON['rule']
    assert pg.evaluate("document.querySelector('#tmade').getBoundingClientRect().bottom <= window.innerHeight")
    shot(pg, f'person-{tag}')
    pg.locator('#tmain [data-act="approve"]').click()
    saved(pg, PERSON['line'], btn(PERSON, 'approve')['choice'])
    assert strip(pg) == 'Your answer: ' + btn(PERSON, 'approve')['say']
    clean(pg)
    pg.close()


def test_what_each_button_of_a_set_writes(browser):
    pg = show(browser, doc())
    pg.locator('#tauto').uncheck()
    open_set(pg, PERSON)
    fix, again = btn(PERSON, 'fix'), btn(PERSON, 'again')
    # minor corrections: the words are required, and travel with the choice
    pg.locator('#tmain [data-act="fix"]').click()
    assert pg.locator('#tpanel label').text_content() == 'What should change?' and pg.locator('#tpanel button').all_text_contents() == ['Send corrections', 'Cancel']
    pg.locator('#tfixsend').click()
    assert pg.locator('#tmsg').text_content() == 'Write what should change first.' and PERSON['line'] not in answers(pg)
    pg.locator('#tfix').fill('Picture B: only the hand.')
    pg.locator('#tfixsend').click()
    a = saved(pg, PERSON['line'], fix['choice'])
    assert a['notes'] == 'Picture B: only the hand.' and pg.locator('#tpanel').count() == 0
    assert strip(pg) == 'Your answer: ' + fix['say'].replace('{words}', 'Picture B: only the hand.')
    assert pg.locator('#trail .trow[aria-current] .ttag').text_content() == fix['label']
    pg.locator('#tundo').click()
    gone(pg, PERSON['line'])
    # make again: a small confirm first
    pg.locator('#tmain [data-act="again"]').click()
    assert pg.locator('#tpanel p').text_content() == again['ask'] and pg.locator('#tpanel button').all_text_contents() == [again['label'], 'Cancel']
    assert PERSON['line'] not in answers(pg)
    pg.locator('#tcancel').click()
    assert pg.locator('#tpanel').count() == 0
    pg.locator('#tmain [data-act="again"]').click()
    pg.locator('#tagain').click()
    assert saved(pg, PERSON['line'], again['choice'])['notes'] == '' and strip(pg) == 'Your answer: ' + again['say']
    # upload my own, for a person: the page's own upload, their words of permission first
    pg.locator('#tmain [data-act="own"]').click()
    perm = pg.locator('#tpanel input[type=text]')
    assert perm.count() == 1 and PERSON['own']['text'] in pg.locator('#tpanel').text_content()
    perm.fill('He agreed that we use his photo.')
    pg.locator('#tpanel input[type=file]').set_input_files({'name': 'him.png', 'mimeType': 'image/png', 'buffer': picture()})
    a = saved(pg, PERSON['line'], 'own')
    assert a['permission'] == 'He agreed that we use his photo.' and a['own']['name'] == 'him.png'
    assert strip(pg) == 'Your answer: ' + PERSON['own']['say'] and pg.locator('#tanswer img.ownpic').count() == 1
    clean(pg)
    # a set made the most times: no "make again"; it can be left out
    open_set(pg, MOST)
    assert 'again' not in acts(MOST) and pg.locator('#tmain [data-act="again"]').count() == 0 and bar(pg) == expected_bar(MOST)
    assert pg.locator('#tmost').is_visible() and pg.locator('#tmost').text_content() == MOST['most']
    assert pg.locator('#tmain .thead').text_content().count(MOST['made_n']) == 1
    # a set whose thing changed: said openly; its button writes at once; a refusal of the server is said on the set
    open_set(pg, CHANGED)
    assert pg.locator('#tchanged').text_content() == CHANGED['changed'] and pg.locator('#tpartial').text_content() == CHANGED['partial']
    assert pg.locator('#trefused').text_content() == 'Not recorded: ' + CHANGED['refused']
    pg.locator('#tmain [data-act="remake"]').click()
    saved(pg, CHANGED['line'], btn(CHANGED, 'remake')['choice'])
    assert strip(pg) == 'Your answer: ' + btn(CHANGED, 'remake')['say']
    # a set made again as asked: said openly, the set before folded
    open_set(pg, AGAIN)
    assert pg.locator('#tasked').text_content().startswith(AGAIN['asked']) and pg.locator('#tearlier').is_hidden()
    pg.locator('#tearlierb').click()
    assert pg.locator('#tearlierb').text_content() == 'The set before' and pg.locator('#tearlier button').count() == len(AGAIN['earlier'])
    # a set of one picture: nothing to choose, no letter; Approve writes its choice
    open_set(pg, SINGLE)
    assert pg.locator('#tmain .ttile').count() == 1 and pg.locator('#tmain .tpick').count() == 0 and pg.locator('#tmain .tletter').count() == 0
    assert pg.locator('#tcheckb').text_content() == SINGLE['check']['chip']
    shot(pg, 'one-picture')
    pg.locator('#tmain [data-act="approve"]').click()
    saved(pg, SINGLE['line'], btn(SINGLE, 'approve')['choice'])
    # an answer kept from an earlier visit
    kept = KEPT[0]
    open_set(pg, kept)
    assert strip(pg).startswith('Kept from before: ' + kept['kept']) and kept['kept_note'] in strip(pg) and pg.locator('#tundo').count() == 0
    assert pg.locator('#trail .trow[aria-current]').get_attribute('class') == 'trow done' and bar(pg) == expected_bar(kept)
    clean(pg)
    pg.close()


def test_not_made_waiting_and_settled(browser):
    pg = show(browser, doc())
    pg.locator('#tauto').uncheck()
    # could not be made: the reason behind "why"; make it, or leave it out after seeing which shots lose it
    open_set(pg, NOTMADE)
    assert pg.locator('#tmain .ttile').count() == 0 and pg.locator('#tmain .tnopics b').text_content() == NOTMADE['head'] and pg.locator('#twhynot').is_hidden()
    pg.locator('#twhynotb').click()
    assert pg.locator('#twhynot').text_content().strip() == NOTMADE['why']
    assert bar(pg) == expected_bar(NOTMADE)
    shot(pg, 'not-made')
    pg.locator('#tmain [data-act="make"]').click()
    saved(pg, NOTMADE['line'], btn(NOTMADE, 'make')['choice'])
    assert strip(pg) == 'Your answer: ' + btn(NOTMADE, 'make')['say']
    pg.locator('#tundo').click()
    gone(pg, NOTMADE['line'])
    pg.locator('#tmain [data-act="leave"]').click()
    assert pg.locator('#tpanel p').text_content() == NOTMADE['loss']['text'] and pg.locator('#tpanel li').all_text_contents() == NOTMADE['loss']['shots']
    assert pg.locator('#tpanel button').all_text_contents() == ['Leave it out', 'Cancel'] and pg.evaluate('document.activeElement.id') == 'tcancel'   # never one key away
    assert NOTMADE['line'] not in answers(pg)
    shot(pg, 'leave-out')
    pg.locator('#tleave').click()
    saved(pg, NOTMADE['line'], btn(NOTMADE, 'leave')['choice'])
    assert strip(pg) == 'Your answer: ' + btn(NOTMADE, 'leave')['say'] and pg.locator('#trail .trow[aria-current] .ttag').text_content() == btn(NOTMADE, 'leave')['label']
    # a real person whose photo is needed: the photo, or a stand-in in the operator's words
    open_set(pg, PHOTO)
    assert bar(pg) == expected_bar(PHOTO)
    stand = btn(PHOTO, 'standin')
    pg.locator('#tmain [data-act="standin"]').click()
    assert pg.locator('#tpanel label').text_content() == stand['hint'] and pg.locator('#tpanel button').all_text_contents() == [stand['label'], 'Cancel']
    pg.locator('#tfix').fill('A woman of 60 with grey hair.')
    pg.locator('#tfixsend').click()
    assert saved(pg, PHOTO['line'], stand['choice'])['notes'] == 'A woman of 60 with grey hair.' and strip(pg) == 'Your answer: ' + stand['say'].replace('{words}', 'A woman of 60 with grey hair.')
    pg.locator('#tmain [data-act="photo"]').click()
    saved(pg, PHOTO['line'], btn(PHOTO, 'photo')['choice'])
    # a thing that came back
    open_set(pg, BACK)
    assert bar(pg) == expected_bar(BACK) and pg.locator('#tmain .tnopics b').text_content() == BACK['head'] and pg.locator('#twhynotb').count() == 0
    pg.locator('#tmain [data-act="set"]').click()
    saved(pg, BACK['line'], btn(BACK, 'set')['choice'])
    # a waiting set and a settled one: nothing to press
    wait = WAITING[0]
    open_set(pg, wait)
    assert pg.locator('#tmain .tbar').count() == 0 and pg.locator('#tmade').count() == 0 and pg.locator('#tmain .tnopics').text_content() == wait['head']
    assert pg.locator('#trail .trow[aria-current]').get_attribute('class') == 'trow calm' and pg.locator('#trail .trow[aria-current] .ttag').text_content() == wait['tag']
    open_set(pg, SETTLED)
    assert pg.locator('#tmain .tbar').count() == 0 and pg.locator('#tmain .ttile').count() == len(SETTLED['pics']) and pg.locator('#tmain .tpick').count() == 0
    assert pg.locator('#tmain .tnopics').text_content() == SETTLED['head']
    pg.locator('#tmain .timg').first.click()
    assert pg.locator('.zoom').count() == 1
    pg.keyboard.press('Escape')
    pg.locator('#tdetb').click()
    assert pg.locator('#tdetails dt').all_text_contents() == [r[0] for r in SETTLED['details']]
    shot(pg, 'settled')
    for key in 'aclmu123':                                                                                      # no key answers a line with nothing to press
        pg.keyboard.press(key)
    assert SETTLED['line'] not in answers(pg) and pg.locator('#tpanel').count() == 0
    # the filters count only what is judged
    pg.locator('#trail [data-filter="done"]').click()
    done = {l['name'] for l in COUNTED if l.get('kept') or l['line'] in answers(pg)}
    assert set(pg.locator('#trail .trow .tnm').all_text_contents()) == done
    pg.locator('#trail [data-filter="open"]').click()
    assert set(pg.locator('#trail .trow .tnm').all_text_contents()) == {l['name'] for l in COUNTED} - done
    clean(pg)
    pg.close()


def test_the_waiting_sets_are_made_or_left_out_together(browser):
    last = next(l for l in JUDGE if not l.get('pick') and not l.get('kept'))
    pg = show(browser, keep([l['key'] for l in JUDGE if l is not last]))
    pg.locator('#tauto').uncheck()
    make = pg.locator(f'#trail [data-rest="{MAKE["choice"]}"]')
    # "Make them" waits for the judged sets
    assert make.text_content() == MAKE['label'] and make.is_disabled() and pg.locator('#trestwhy').text_content() == REST['why']
    # "Show the N": the waiting sets, each with "Open"
    pg.locator('#trail [data-rest="show"]').click()
    assert pg.locator('#trail [data-rest="show"]').text_content() == REST['show'] and pg.locator('#tmain h2').text_content() == REST['list_head']
    assert pg.locator('#tmain .tprow b').all_text_contents() == [l['name'] for l in WAITING]
    assert pg.locator('#tmain .tprow').first.text_content() == WAITING[0]['name'] + ' ' + WAITING[0]['kind'] + WAITING[0]['wait_note'] + 'Open'
    assert pg.locator('#tmain .tnote').first.text_content() == REST['list_note']
    shot(pg, 'the-waiting-listed')
    pg.keyboard.press('Escape')
    assert pg.locator('#tmain .tprow').count() == 0                                                             # Esc closes the list
    pg.locator('#trail [data-rest="show"]').click()
    pg.locator('#tmain .tprow button').nth(1).click()
    assert pg.locator('#tmain h2').text_content() == WAITING[1]['name']
    # "Leave some out": the table of what is lost, the people, and the button that does it
    loss = OUT['loss']
    pg.locator(f'#trail [data-rest="{OUT["choice"]}"]').click()
    assert pg.locator('#tmain h2').text_content() == loss['head'] and pg.locator('#tmain .tnote').first.text_content() == loss['intro']
    assert pg.locator('#tmain table.loss th').all_text_contents() == loss['cols']
    assert pg.locator('#tmain table.loss tbody tr').count() == len(loss['rows'])
    assert pg.locator('#tmain table.loss tbody tr').first.locator('td').all_text_contents() == [str(c) for c in loss['rows'][0]]
    assert pg.locator('#tpeople').text_content() == loss['people'] and pg.locator('#trestout').text_content() == loss['button']
    assert pg.evaluate('document.activeElement.id') == 'tclose' and pg.locator('#tclose').text_content() == 'Cancel' and REST['line'] not in answers(pg)
    # design/213 review: the button says all it does (the people's sets are made with it), and waits for the judged sets as "Make them" does
    assert loss['button'] == next(b['label'] for b in CHAT_REST) and 'and make the other' in loss['button'] and 'made' in loss['people']
    assert pg.locator('#trestout').is_disabled() and pg.locator('#trestoutwhy').text_content() == REST['why']
    pg.locator('#trestout').click(force=True)
    assert REST['line'] not in answers(pg)
    shot(pg, 'leave-some-out')
    clean(pg)
    pg.locator('#tclose').click()
    # the last set judged: "Make them" works, and says what will happen
    open_set(pg, last)
    pg.locator('#tmain [data-act="approve"]').click()
    saved(pg, last['line'], btn(last, 'approve')['choice'])
    assert make.is_enabled() and pg.locator('#trestwhy').count() == 0
    make.click()
    a = saved(pg, REST['line'], MAKE['choice'])
    assert (a['key'], a['item']) == ('sets:rest', REST['item'])
    assert pg.locator('#trail .tprop p').first.text_content() == MAKE['say'] and pg.locator('#trail .tprop button').all_text_contents() == [REST['show'], 'Undo']
    tags = lambda: [pg.locator('#trail .trow', has=pg.locator('.tnm', has_text=re.compile(f'^{re.escape(l["name"])}$'))).locator('.ttag').text_content() for l in WAITING]
    assert tags() == ['Will be made'] * len(WAITING)
    # a judged answer taken back: "Make them" no longer stands
    pg.locator('#tundo').click()
    gone(pg, last['line'])
    gone(pg, REST['line'])
    assert make.is_disabled()
    pg.locator('#tmain [data-act="approve"]').click()
    saved(pg, last['line'], btn(last, 'approve')['choice'])
    # leaving some out
    pg.locator(f'#trail [data-rest="{OUT["choice"]}"]').click()
    assert pg.locator('#trestout').is_enabled() and pg.locator('#trestoutwhy').count() == 0
    pg.locator('#trestout').click()
    saved(pg, REST['line'], OUT['choice'])
    assert pg.locator('#trail .tprop p').first.text_content() == OUT['say']
    assert tags() == ['Left out' if l.get('out') else 'Will be made' for l in WAITING]
    open_set(pg, next(l for l in WAITING if l.get('out')))
    assert 'Left out' in pg.locator('#tmain .tnopics').text_content()
    pg.locator('#trail [data-rest="undo"]').click()
    gone(pg, REST['line'])
    assert tags() == [l['tag'] for l in WAITING]
    clean(pg)
    pg.close()


def test_every_set_judged_then_the_waiting_sets_then_all_answered(browser):
    pg = show(browser, keep([l['key'] for l in COUNTED]), wait='#trestcard')
    assert pg.locator('#tprogt').text_content() == f'{len(COUNTED)} of {len(COUNTED)} judged'
    assert pg.locator('#trestcard h2').text_content() == REST['head'] and pg.locator('#trestcard .tnote').text_content() == LAY['made']
    assert [' '.join(t.split()) for t in pg.locator('#trestcard button').all_text_contents()] == [MAKE['big'], REST['show'], OUT['label']]
    shot(pg, 'judged-the-rest-waits')
    pg.locator(f'#trestcard [data-rest="{MAKE["choice"]}"]').click()
    saved(pg, REST['line'], MAKE['choice'])
    assert pg.locator('#tmain .talldone').text_content() == 'All answered.Go back to the chat and say done.' + MAKE['say']
    shot(pg, 'all-answered')
    clean(pg)
    pg.close()
    # a round with no waiting set
    none = keep([l['key'] for l in COUNTED])
    none['lines'] = [l for l in none['lines'] if l['key'] != 'sets:rest' and l['case'] != 'wait']
    pg = show(browser, none, wait='#tmain .talldone')
    assert pg.locator('#tmain .talldone').text_content() == 'All answered.Go back to the chat and say done.' and pg.locator('#trail .tprop').count() == 0
    pg.close()


def test_the_keys_and_auto_advance(browser):
    pg = show(browser, doc())
    name = lambda: pg.locator('#tmain h2').text_content()
    at = SETS.index(next(l for l in COUNTED if not l.get('kept')))
    assert name() == SETS[at]['name']
    pg.keyboard.press('ArrowRight')
    assert name() == SETS[at + 1]['name']
    pg.keyboard.press('k')
    pg.keyboard.press('j')
    pg.keyboard.press('ArrowLeft')
    assert name() == SETS[at]['name']
    pg.locator('[data-pop="tkeys"]').click()
    keys = pg.locator('#tkeys dl:visible').text_content()
    assert 'Choose picture A, B or C as the reference' in keys and 'Make again, or make it' in keys and 'Make a set' not in keys
    pg.keyboard.press('Escape')
    assert pg.locator('#tkeys').is_hidden()
    pg.locator('[data-pop="thow"]').click()
    assert pg.locator('#thow p').all_text_contents() == LAY['help']
    pg.keyboard.press('Escape')
    # the letters open what the buttons open
    open_set(pg, PERSON)
    pg.keyboard.press('c')
    assert pg.locator('#tpanel #tfix').count() == 1
    pg.keyboard.press('Escape')
    assert pg.locator('#tpanel').count() == 0
    pg.keyboard.press('m')
    assert pg.locator('#tagain').count() == 1
    pg.keyboard.press('Escape')
    pg.keyboard.press('u')
    assert pg.locator('#tpanel input[type=file]').count() == 1
    pg.keyboard.press('Escape')
    open_set(pg, NOTMADE)
    pg.keyboard.press('l')
    assert pg.locator('#tleave').count() == 1 and NOTMADE['line'] not in answers(pg)
    pg.keyboard.press('Escape')
    # 1 2 3 choose the reference, A approves, and the next set still to judge comes by itself
    open_set(pg, PLACE)
    assert pg.locator('#tauto').is_checked()
    pg.keyboard.press('a')
    assert pg.locator('#tmsg').text_content() == LAY['pick']
    pg.keyboard.press('3')
    assert pg.locator('#tpick3').get_attribute('aria-checked') == 'true'
    pg.keyboard.press('a')
    saved(pg, PLACE['line'], made(PLACE)[2]['choice'])
    nxt = next(l for l in SETS[SETS.index(PLACE) + 1:] if l in COUNTED and not l.get('kept'))
    pg.wait_for_function('n => document.querySelector("#tmain h2").textContent === n', arg=nxt['name'], timeout=5000)
    # M makes a set that could not be made, at once
    open_set(pg, NOTMADE)
    pg.keyboard.press('m')
    saved(pg, NOTMADE['line'], btn(NOTMADE, 'make')['choice'])
    pg.locator('#tauto').uncheck()
    pg.locator('#tnextopen').click()
    assert name() == next(l for l in SETS[SETS.index(NOTMADE) + 1:] if l in COUNTED and not l.get('kept'))['name']
    clean(pg)
    pg.close()


def test_at_1000_px_the_layout_holds(browser):
    pg = show(browser, doc(), '1000')
    for l in (PLACE, PERSON):
        open_set(pg, l)
        assert pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert pg.evaluate("document.querySelector('#tmain h2').scrollWidth <= document.querySelector('#tmain h2').clientWidth")   # the name is whole
        assert pg.locator('#tmain .ttile').count() == 3 and pg.locator('#tnextopen').is_visible()
        assert len(set(pg.evaluate("[...document.querySelectorAll('#tmain .tbar button')].map(e => Math.round(e.getBoundingClientRect().top))"))) == 1
        shot(pg, 'narrow-1000-' + l['key'][4:].lower())
    clean(pg)
    pg.close()



def test_step_1_asks_the_permission_of_a_person_the_footage_shows_and_says_the_writers_words(monkeypatch, browser):
    """design/213, on the screen of step 1: the one question of a person whose kept footage picture shows the face, its two answers, the
    words box of the permission, what each answer will do in the server's own sentence; and the writer's added words, said openly."""
    from test_design212_browser_pure import doc as doc1, thing
    from test_design213_layout_pure import person_film
    film, _said = person_film(monkeypatch)
    film.change(lambda s: s['round']['elements']['TROWEL'].update(prompt='The look from the footage, the place from the plan.'))
    page = film.page()
    by = {l['key']: l for l in page['lines']}
    mason, permit, standin = by['ref:MASON'], by['ref:MASON']['buttons'][0], by['ref:MASON']['buttons'][1]
    pg = show(browser, doc1(page))
    pg.locator('#tauto').uncheck()
    thing(pg, mason['name'])
    assert pg.locator('#tlikeness').text_content() == mason['likeness']['ask'] and pg.locator('#tlikeness').is_visible()
    pg.wait_for_function("![...document.querySelectorAll('#tmain .tbar button')].some(b => b.disabled)")
    assert [' '.join(x.split()) for x in pg.locator('#tmain .tbar button').all_text_contents()] == [permit['label'], standin['label'], mason['own']['label']]
    pg.locator('#tmain [data-act="permit"]').click()
    assert pg.locator('#tpanel label').text_content() == permit['hint']
    pg.locator('#tfixsend').click()
    assert mason['line'] not in answers(pg) and pg.locator('#tmsg').text_content() == permit['hint']              # their own words are required
    pg.locator('#tfix').fill('He agreed on site.')
    pg.locator('#tfixsend').click()
    assert saved(pg, mason['line'], 'permit')['notes'] == 'He agreed on site.'
    assert pg.locator('#tanswer p').text_content() == 'Your answer: ' + permit['say'].replace('{words}', 'He agreed on site.').replace('{pictures}', '1 ticked picture')   # design/213 review: which pictures go
    pg.locator('#tundo').click()
    gone(pg, mason['line'])
    pg.locator('#tmain [data-act="standin"]').click()
    saved(pg, mason['line'], 'standin')
    assert pg.locator('#tanswer p').text_content() == 'Your answer: ' + standin['say'] and 'will differ from the person in your clips' in standin['say']
    thing(pg, by['ref:TROWEL']['name'])
    assert pg.locator('#tdiffers').is_visible() and pg.locator('#tdiffers').text_content() == by['ref:TROWEL']['differs']
    clean(pg)
    pg.close()
