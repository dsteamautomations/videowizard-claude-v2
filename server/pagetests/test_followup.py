"""Follow-up, ten fixes (11 Nov 2026), after SK's walk of the page. One test per fix, F01 to F10; the server side of fixes 2, 3, 7 and 9 is in
unit/test_ui_visuals_actions_pure.py. Elements of the test film: E1 Plinth, E2 Clamp kiln, P1 Mason, BRICK Red brick, E3 Yard wall."""
import re

from kit import answer_all, app_text, card, counts_wrong, golden, ident, last_of, press_done, rail, show, verdict

IDS = re.compile(r'\b(E1|E2|E3|P1|BRICK)\b')
FAILED = 'That could not be done; nothing was changed. The builder has been told what failed.'
CONTROLS = '#app button[data-a], #app input[type=radio], #app [data-golden]'


def off(put):
    return sorted(f"{b.get_attribute('data-a') or b.get_attribute('name') or 'golden'}" for b in put.page.locator(CONTROLS).all() if b.is_visible() and not b.is_enabled())


def confirm(put, action='round-sets'):
    put.page.locator(f'#action button[data-a="{action}"]').first.click()
    put.page.wait_for_timeout(150)
    return put.page.locator('#done-confirm')


@ident('F01')
def test_a_busy_answer_never_turns_the_page_read_only(open_page, _id):
    put = open_page('cross-run-busy-read-only', clock=True)
    assert put.payload['busy'] is True
    assert 'read-only' not in app_text(put).lower(), 'the page still says read-only on a busy answer'
    assert off(put) == off(open_page('refs-step2-all-sets-back')), f'a busy answer switched controls off: {off(put)}'
    n = put.data_gets
    put.page.clock.fast_forward(6000)
    put.page.wait_for_timeout(250)
    assert put.data_gets == n, 'the page still re-reads after 5 s on a busy answer'
    verdict(put, 'E2', 'no')
    put.page.wait_for_timeout(150)
    assert last_of(put, 'set_answer') and last_of(put, 'set_answer')['element_id'] == 'E2', 'an answer made while the server was busy was not sent'
    assert not put.red_line()


@ident('F02')
def test_done_at_the_spend_cap_records_the_yes_answers(open_page, _id):
    put = open_page('cross-spend-cap-reached-sets-back')
    assert 'spend cap reached' in put.text('#line').lower()
    golden(put, 'BRICK')
    verdict(put, 'BRICK', 'yes')
    verdict(put, 'P1', 'yes')
    verdict(put, 'E2', 'no')
    put.page.wait_for_timeout(200)
    assert put.page.locator('#action button[data-a="round-sets"]').is_enabled(), 'Done is off at the cap: a Yes, which costs nothing, cannot be recorded'
    box = confirm(put)
    text = ' '.join(box.inner_text().split())
    assert '2 approved' in text and '1 set to be made again will not be made' in text and '₹100' in text and 'answered and waiting' in text, f'the confirmation at the cap says: "{text}"'
    assert not IDS.search(text)
    put.answers['round-sets'] = (200, {'pass': 2, 'approved': ['BRICK', 'P1'], 'queued': [], 'errors': {}, 'unanswered': [],
                                      'held': {'E2': 'the spend cap of ₹100 is reached (₹120 spent): the set is not made again; its answer is kept and waits'}})
    fin = box.locator('button[data-a="round-sets"]')
    assert fin.is_enabled()
    fin.click()
    put.wait_posts(4)
    sent = last_of(put, 'round-sets')['verdicts']
    assert {k: v['verdict'] for k, v in sent.items()} == {'BRICK': 'yes', 'P1': 'yes', 'E2': 'no'}
    put.page.wait_for_timeout(150)
    kind, bar = put.bar()
    assert kind != 'err' and '2 approved' in bar and 'spend cap' in bar and 'being made again' not in bar and 'complete' not in bar, f'after Done at the cap the bar says: "{bar}"'


@ident('F03')
def test_a_set_never_made_is_set_aside_and_brought_back(open_page, _id):
    put = open_page('refs-step2-size-not-measured')
    show(put, 'E3')
    b = card(put, 'E3').locator('button[data-a="set-aside"][data-el="E3"]')
    assert b.count() == 1 and b.inner_text() == 'Set aside', 'a set that cannot be made has no "Set aside"'
    show(put, 'BRICK')
    assert put.page.locator('button[data-a="set-aside"][data-el="BRICK"]').count() == 0, 'a set that was made offers "Set aside"'
    show(put, 'E3')
    put.page.fill('#words', 'we film the wall ourselves')
    b.click()
    put.wait_posts(1)
    assert put.posts[-1] == {'action': 'set_aside', 'element_id': 'E3', 'words': 'we film the wall ourselves'}

    aside = open_page('refs-step2-set-aside')
    assert aside.payload['round']['elements']['E3']['ignored'] is True
    assert 'set aside' in rail(aside, 'E3').inner_text().lower() and rail(aside, 'E3').locator('.wdot').count() == 0, 'the left list does not show the element as set aside'
    assert not counts_wrong(aside), f'{counts_wrong(open_page("refs-step2-set-aside"))}'
    aside.open_tab('references')
    show(aside, 'E3')
    text = card(aside, 'E3').inner_text()
    assert 'set aside' in text.lower() and 'we film the wall ourselves' in text
    back = card(aside, 'E3').locator('button[data-a="set-back"][data-el="E3"]')
    assert back.count() == 1 and back.inner_text() == 'Bring back'
    back.click()
    aside.wait_posts(1)
    assert aside.posts[-1] == {'action': 'set_aside', 'element_id': 'E3', 'back': True}

    rest = open_page('refs-step2-set-aside-rest-approved')   # every other set approved: Done closes the round with nothing left to judge
    box = confirm(rest)
    assert 'closes the round' in box.inner_text() and box.locator('button[data-a="round-sets"]').is_enabled(), f'the round cannot be closed: "{" ".join(box.inner_text().split())}"'
    box.locator('button[data-a="round-sets"]').click()
    rest.wait_posts(1)
    assert last_of(rest, 'round-sets')['verdicts'] == {}


@ident('F04')
def test_make_it_now_only_where_the_operator_can_settle_the_cause(open_page, _id):
    put = open_page('refs-step2-size-not-measured')
    show(put, 'E3')
    c = card(put, 'E3')
    text = ' '.join(c.inner_text().split())
    assert c.locator('button[data-a="set-make"]').count() == 0, 'a "Make it now" that can only be refused is offered (a size is not measured)'
    assert 'not measured' in text and 'the assistant measures it from the approved footage picture' in text, f'the card does not say what will settle it: "{text[:300]}"'
    assert c.locator('button[data-a="set-aside"]').count() == 1
    spec = open_page('refs-step2-some-sets-not-made')   # a spec to approve: the operator settles it on the card, so the flow stays as built
    show(spec, 'BRICK')
    c = card(spec, 'BRICK')
    assert c.locator('button[data-a="set-make"]').count() == 1 and c.locator('button[data-a="approve-spec"]').count() == 1 and c.locator('button[data-a="set-aside"]').count() == 1


@ident('F05')
def test_names_not_ids_in_everything_the_operator_reads(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    foot = put.text('#twait')
    assert 'Clamp kiln' in foot and 'Mason' in foot and 'Red brick' in foot and not IDS.search(foot), f'the foot line says: "{foot}"'
    show(put, 'E2')
    assert card(put, 'E2').locator('.nm').first.inner_text() == 'Clamp kiln', 'the card heading does not lead with the name'
    assert rail(put, 'E2').locator('.t1').inner_text() == 'Clamp kiln', 'the left-list card does not lead with the name'
    put.click('#wcount')
    wl = put.text('#wlist')
    assert 'Set to judge · Clamp kiln' in wl and not IDS.search(wl), f'the waiting list says: "{wl}"'
    verdict(put, 'E2', 'correct')
    box = confirm(put)
    assert not IDS.search(box.inner_text())
    put.answers['round-sets'] = (400, {'message': 'P1: say what to correct.'})
    verdict(put, 'P1', 'no')
    box = confirm(put)
    box.locator('button[data-a="round-sets"]').click()
    put.page.wait_for_timeout(300)
    kind, bar = put.bar()
    assert kind == 'err' and bar.startswith('Mason: say what to correct') and not IDS.search(bar), f'the refusal reads: "{bar}"'
    show(put, 'P1')
    assert 'not recorded' in card(put, 'P1').inner_text() and not IDS.search(card(put, 'P1').locator('[data-astate]').inner_text())

    one = open_page('refs-step1-to-answer')
    box = one.text('#notmade')
    assert 'Red brick' in box and not IDS.search(box), f'the "will not be made" box says: "{box}"'


@ident('F06')
def test_the_green_line_after_done_says_what_happened(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    put.answers['round-sets'] = (200, {'pass': 'complete', 'approved': ['E2', 'P1', 'BRICK'], 'queued': [], 'errors': {}, 'held': {}, 'unanswered': []})
    answer_all(put)
    press_done(put)
    put.page.wait_for_timeout(200)
    kind, bar = put.bar()
    assert kind == 'ok' and '3 approved' in bar and 'the round is complete' in bar.lower() and 'made again' not in bar, f'every answer was Yes; the bar says: "{bar}"'

    two = open_page('refs-step2-all-sets-back')
    two.answers['round-sets'] = (200, {'pass': 'making', 'approved': ['E2', 'BRICK'], 'queued': ['P1'], 'errors': {}, 'held': {}, 'unanswered': []})
    answer_all(two)
    verdict(two, 'P1', 'no')
    press_done(two)
    two.page.wait_for_timeout(200)
    bar = two.bar()[1]
    assert '2 approved' in bar and '1 being made again' in bar and 'complete' not in bar, f'one set is made again; the bar says: "{bar}"'


@ident('F07')
def test_ignoring_a_footage_picture_on_a_kept_film(open_page, _id):
    put = open_page('refs-step1-to-answer')
    show(put, 'E1')
    card(put, 'E1').locator('button[data-a="reject"]').first.click()
    put.wait_posts(1)
    put.page.wait_for_timeout(150)
    bar = put.bar()[1]
    assert 'search' not in bar.lower() and 'next one' not in bar and 'ignored' in bar and 'made from its description' in bar, f'the answer to Ignore reads: "{bar}"'


@ident('F08')
def test_the_confirmation_before_done_at_step_1_carries_the_counts(open_page, _id):
    put = open_page('refs-step1-to-answer')
    box = confirm(put, 'round-done')
    text = ' '.join(box.inner_text().split())
    assert box.is_visible() and '1 footage picture used' in text and '0 ignored' in text, f'the confirmation of step 1 says: "{text}"'
    assert '2 sets will be made' in text and 'paid' in text and '₹120' in text, f'the sets and their cost are not said: "{text}"'
    assert '1 will not be made' in text and 'Red brick' in text and 'is not approved' in text and not IDS.search(text), f'what will not be made is not said: "{text}"'
    assert not put.posts
    put.click('button[data-a="round-picks-back"]')
    verdict(put, 'P1', 'ignore')
    text = ' '.join(confirm(put, 'round-done').inner_text().split())
    assert '1 set will be made' in text and '₹60' in text and '1 thing set to Ignore' in text, f'after Ignore on the mason: "{text}"'


@ident('F09')
def test_no_bare_key_name_reaches_the_operator(open_page, _id):
    for status, body in ((422, {'message': "'request_key'"}), (500, {'code': 'PAGE_ACTION_FAILED', 'message': FAILED})):
        put = open_page('takes-ready-to-select')
        put.answers['select-take'] = (status, body)
        show(put, 'VS1')
        put.click('#panel button[data-a="select-take"]')
        put.wait_posts(1)
        put.page.wait_for_timeout(150)
        kind, bar = put.bar()
        assert kind == 'err' and bar == FAILED, f'the bar says: "{bar}"'
        assert 'request_key' not in app_text(put)
        put.click('#mhist-b')
        assert 'request_key' not in app_text(put)


@ident('F10')
def test_the_header_never_points_at_a_finished_step(open_page, _id):
    put = open_page('takes-ready-to-select')
    assert put.payload['round']['pass'] == 'complete' and put.payload['waiting'][0]['step'] == 'takes'
    line = put.text('#line')
    assert 'References is the step' not in line and 'Takes is the step the run is at' in line, f'the header says: "{line[:120]}"'
    done = open_page('refs-round-complete')
    assert 'References is the step' not in done.text('#line'), f'the round is complete; the header says: "{done.text("#line")[:120]}"'
