"""design/215, the page checks: `plugin/pages/decisions.html` renders the words the server sends and holds none of the older ones; the tick
"This applies to every picture of this thing" (off unless ticked) sends the server's own choice; a hint beside a button and the operator's
corrections of a thing are shown at step 1. Drawn in a headless browser from the round of `d213_sets_round.json` and step 1 of design/212's
page checks (no product server, no network). Skipped where Playwright or its browser is not installed."""
import copy
import re
from pathlib import Path

import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import answers, browser, saved, show   # noqa: F401 (`browser` is the fixture)
import test_design212_browser_pure as B1
from test_design211c_kit_pure import Film
from test_design213_browser_pure import PERSON, ROUND, btn, doc, open_set

PAGE = (Path(__file__).resolve().parents[2] / 'plugin' / 'pages' / 'decisions.html').read_text(encoding='utf-8')
OLD = re.compile(r'Leave out|Leave it out|Left out|If you leave it out|Send corrections|Minor corrections, or|\'Corrections\'')


def test_the_page_holds_none_of_the_older_words_and_no_amount():
    assert not OLD.search(PAGE) and 'layout||{}).words' in PAGE and '₹' not in PAGE.split('design/213')[-1]


def test_the_fixture_carries_the_servers_words():
    w = ROUND['layout']['words']
    assert w['leave'] == 'No reference needed' and w['leave_set'] == 'Go on without a reference' and w['wait_out'] == 'Not made'
    assert btn(PERSON, 'fix')['all'] == {'label': 'This applies to every picture of this thing', 'choice': 'correct_all'} and btn(PERSON, 'fix')['go'] == 'Make it again with these words'


def test_the_tick_is_off_and_sends_the_servers_choice_only_when_ticked(browser):
    fix = btn(PERSON, 'fix')
    pg = show(browser, doc())
    pg.locator('#tauto').uncheck()
    open_set(pg, PERSON)
    pg.locator('#tmain [data-act="fix"]').click()
    assert pg.locator('#tall').is_checked() is False and pg.locator('label[for="tall"]').text_content().strip() == fix['all']['label']
    pg.locator('#tfix').fill('The side view is too dark.')
    pg.locator('#tfixsend').click()
    assert saved(pg, PERSON['line'], 'correct')['notes'] == 'The side view is too dark.'   # one view: it stays on this set
    pg.locator('#tmain [data-act="fix"]').click()
    pg.locator('#tall').check()
    pg.locator('#tfix').fill('Make the sleeves longer.')
    pg.locator('#tfixsend').click()
    a = saved(pg, PERSON['line'], 'correct_all')
    assert a['notes'] == 'Make the sleeves longer.' and 'Make the sleeves longer.' in pg.locator('#tanswer').text_content()   # said back with the button's own sentence
    assert pg.locator('#tkeys2 #tk2leave').text_content() == 'Go on without a reference'
    pg.close()


def test_step_1_shows_the_hint_the_corrections_and_the_servers_labels(monkeypatch, browser):
    film = Film(monkeypatch)
    film.change(lambda s: s.update(thing_corrections={'TROWEL': [{'words': 'Make the handle longer.', 'at': 'a', 'by': 'u', 'set': 'x'},
                                                                 {'words': 'Make the handle shorter after all.', 'at': 'b', 'by': 'u', 'set': 'y'}]}))
    pg = show(browser, B1.doc(film.page()))
    pg.locator('#tauto').uncheck()
    B1.thing(pg, "Mason's trowel")   # a thing with footage pictures and a free choice
    assert pg.locator('#tmain [data-note="set"]').text_content() == 'Picture not good? Make a set instead.'
    details = pg.locator('#tdetails').text_content()
    assert "The operator's corrections" in details and 'Make the handle shorter after all. (the later one: in force where the two disagree)' in details
    assert 'With no reference of it' in details and 'If you leave' not in details
    pg.locator('#tmain [data-act="ignore"]').click()
    assert pg.locator('#tpanel button').all_text_contents() == ['No reference needed', 'Cancel']
    pg.locator('#tcancel').click()
    pg.locator('#tmain [data-act="fix"]').click()
    assert pg.locator('#tpanel button').all_text_contents() == ['Make a set with these words', 'Cancel']
    assert pg.locator('#tk1leave').text_content() == 'No reference needed' and pg.locator('#tk1fix').text_content() == 'Make a set with words, or words for the picture'
    pg.close()
