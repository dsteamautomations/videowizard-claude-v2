"""Faults 1 to 4 of the VW-20 test run, 11 Nov 2026 (videobuilder-v4/phase2/testrun/requirements-faults-1-4.md): the page.
F1 the amount before Done is the server's price of a set; F2 an own picture is the reference and no set is made for it; F3 each card shows
its own state while a set is being made, and Done stays, switched off with the reason; F4 a set that failed says why and offers three ways
out; F5 the end state is true. The server side is in unit/test_round_faults_pure.py.
Elements of the test film: E1 Plinth (a thing, with a footage picture), E2 Clamp kiln (a place), P1 Mason (a person), BRICK Red brick."""
import re

from kit import app_text, card, clean, golden, ident, last_of, rail, verdict


def rupees(n):
    return '₹' + f'{round(n):,}'


def step1_confirm(put):
    put.page.locator('#action button[data-a="round-done"]').first.click()
    put.page.wait_for_timeout(150)
    return put.page.locator('#done-confirm').inner_text()


def sets_in(text):
    return int(re.search(r'(\d+) sets? will be made', text).group(1))


def actions(loc):
    return sorted(b.get_attribute('data-a') for b in loc.locator('button[data-a]').all() if b.is_visible())


@ident('F1')
def test_step_1_says_the_real_amount_before_done(open_page, _id):
    put = open_page('refs-step1-answered')
    text = step1_confirm(put)
    n, price = sets_in(text), put.payload['budget']['set_inr']
    assert price > 30 and f'about {rupees(n * price)}' in text, text
    clean(put)


@ident('F1-E9')
def test_no_amount_is_shown_when_the_price_is_missing(open_page, _id):
    def no_price(payload):
        payload['budget']['set_inr'] = 0
    text = step1_confirm(open_page('refs-step1-answered', patch=no_price))
    assert '(paid)' in text and 'about' not in text and '₹0' not in text, text


@ident('F1-step2')
def test_step_2_says_the_amount_of_the_sets_made_again(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    golden(put, 'E2')
    verdict(put, 'E2', 'yes')
    verdict(put, 'P1', 'no')
    verdict(put, 'BRICK', 'correct', 'lighter')
    put.page.wait_for_timeout(200)
    put.page.locator('#action button[data-a="round-sets"]').first.click()
    put.page.wait_for_timeout(150)
    text = put.page.locator('#done-confirm').inner_text()
    assert f"2 made again (paid, about {rupees(2 * put.payload['budget']['set_inr'])})" in text, text


@ident('F2')
def test_an_own_picture_at_step_1_is_counted_and_its_set_is_not(open_page, _id):
    put = open_page('refs-step1-own-picture')
    text = step1_confirm(put)
    assert '1 own picture used' in text and sets_in(text) == 2, text   # the mason and the brick; not the kiln, which has the own picture
    clean(put)


@ident('F3')
def test_each_card_shows_its_own_state_while_one_set_is_being_made(open_page, _id):
    put = open_page('refs-step2-one-set-being-made')
    assert 'being made' in rail(put, 'BRICK').inner_text().lower()
    assert 'yes' in rail(put, 'E2').inner_text().lower() and 'being made' not in rail(put, 'E2').inner_text().lower()
    assert 'from your footage' in rail(put, 'E1').inner_text().lower()
    assert 'being made' not in rail(put, 'P1').inner_text().lower()
    rail(put, 'BRICK').click()
    put.page.wait_for_timeout(100)
    assert 'being made' in card(put, 'BRICK').inner_text().lower() and actions(card(put, 'BRICK')) == []
    verdict(put, 'P1', 'yes')   # a ready set is answered meanwhile
    put.page.wait_for_timeout(200)
    sent = last_of(put, 'set_answer')
    assert sent and sent['element_id'] == 'P1' and sent['verdict'] == 'yes'
    clean(put)


@ident('F3-done')
def test_done_stays_visible_switched_off_with_the_reason(open_page, _id):
    put = open_page('refs-step2-one-set-being-made')
    done = put.page.locator('#action button[data-a="round-sets"]')
    assert done.count() == 1 and done.is_visible() and done.is_disabled()
    assert '1 set is still being made: Red brick' in put.page.locator('#tray').inner_text()
    assert 'nothing to do yet' not in app_text(put).lower()


@ident('F3-E14')
def test_after_done_on_step_2_the_approved_cards_say_approved(open_page, _id):
    put = open_page('refs-second-pass-being-made')
    assert 'approved' in rail(put, 'E2').inner_text().lower() and 'approved' in rail(put, 'P1').inner_text().lower()
    assert 'being made' in rail(put, 'BRICK').inner_text().lower()
    assert 'being made' not in rail(put, 'E2').inner_text().lower()


@ident('F4')
def test_a_failed_set_says_why_and_offers_three_ways_out(open_page, _id):
    put = open_page('refs-step2-set-failed-in-call')
    rail(put, 'BRICK').click()
    put.page.wait_for_timeout(100)
    c = card(put, 'BRICK')
    assert 'The picture service refused the request' in c.inner_text()
    assert actions(c) == ['set-aside', 'set-make', 'supply'], actions(c)
    assert c.locator('input[type=file]').count() == 1
    clean(put)


@ident('F2-E3')
def test_an_own_picture_on_a_failed_card_is_its_reference(open_page, _id):
    put = open_page('refs-step2-own-picture-on-failed-set')
    assert 'your picture' in rail(put, 'BRICK').inner_text().lower()
    rail(put, 'BRICK').click()
    put.page.wait_for_timeout(100)
    c = card(put, 'BRICK')
    assert 'your picture' in c.inner_text().lower() and 'set-make' not in actions(c) and 'not made' not in c.inner_text().lower()
    assert 'Red brick' not in put.page.locator('#tray').inner_text()   # nothing waits on it
    clean(put)


@ident('F5')
def test_the_end_state_is_true_for_an_own_picture_and_a_thing_set_aside(open_page, _id):
    put = open_page('refs-round-complete-own-picture-and-set-aside')
    assert 'judge it on step 2' not in app_text(put).lower()
    assert 'your picture' in rail(put, 'E2').inner_text().lower()
    assert 'set aside' in rail(put, 'BRICK').inner_text().lower()
    clean(put)
