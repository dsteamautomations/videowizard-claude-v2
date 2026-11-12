"""Layer 3: one test per approved edge case E1 to E20 (requirements-and-test-plan.md, section 5). A second browser tab, a timed reload,
a dropped connection, a lapsed sign-in and a slow answer are produced with Playwright. Names not in the requirements are in CONTRACT.md."""
import re
import time

from kit import HEX, answer_all, app_text, card, counts_wrong, golden, ident, kind_of, last_of, next_waiting_wrong, rail, round_of, set_of, show, stored, to_judge, verdict
from test_states import LAYOUT, PICTURES

CODE = 'VW-20'


def checked(put, eid):
    c = put.page.locator(f'input[name="v-{eid}"]:checked')
    return c.get_attribute('value') if c.count() else None


def supplied(shot=0, **more):
    def patch(payload):
        payload['gaps'][1]['shots'][shot]['asset'].update(by='SK', quote='A photograph of the wet wall instead.', **more)
    return patch


@ident('E01')
def test_no_elements_or_no_round_yet(open_page, _id):
    for state in ('refs-no-elements', 'refs-no-round-kept'):
        put = open_page(state)
        assert len(put.section_text('references')) > 20, f'{state}: the References tab does not say what comes next'
        assert not next_waiting_wrong(put), f'{state}: a dead Next waiting: {next_waiting_wrong(open_page(state))}'
        assert not counts_wrong(put), f'{state}: {counts_wrong(open_page(state))}'


@ident('E02')
def test_a_very_large_round(open_page, _id):
    put = open_page('cross-large-round-58-elements')
    assert len(put.cards()) == 58
    box = put.page.evaluate('(() => { const b = document.getElementById("rcards"); return [b.scrollHeight, b.clientHeight, getComputedStyle(b).overflowY]; })()')
    assert box[0] > box[1] and box[2] in ('auto', 'scroll'), f'the list of 58 cards does not scroll: {box}'
    assert not counts_wrong(put), f'{counts_wrong(open_page("cross-large-round-58-elements"))}'
    put.open_tab('references')
    t = time.time()
    verdict(put, 'E30', 'no')
    put.wait_posts(1, 1000)
    took = time.time() - t
    assert last_of(put, 'set_answer') == {'action': 'set_answer', 'element_id': 'E30', 'verdict': 'no', 'golden': None, 'words': ''}, 'the answer of one card of 58 was not stored on its own'
    assert took < 2, f'one answer took {took:.1f} s on the large round'


@ident('E03')
def test_two_browser_tabs_on_one_run(open_page, _id):
    a, b = open_page('refs-step2-all-sets-back'), open_page('refs-step2-all-sets-back')
    pic = set_of(a, 'BRICK')[0]
    golden(a, 'BRICK')
    verdict(a, 'BRICK', 'yes')
    a.page.wait_for_timeout(150)
    first = last_of(a, 'set_answer')
    assert first and first['verdict'] == 'yes' and first['golden'] == pic, 'the answer made in the first tab never reached the server, so the second tab cannot show it'
    for put in (a, b):
        put.serve('refs-step2-all-sets-back', stored({'BRICK': first}))
    b.refresh()
    assert checked(b, 'BRICK') == 'yes' and b.page.locator(f'[data-golden="BRICK:{pic}"]').get_attribute('aria-pressed') == 'true', 'the second tab does not show the answer after its refresh'
    verdict(b, 'BRICK', 'no')
    b.page.wait_for_timeout(150)
    later = last_of(b, 'set_answer')
    for put in (a, b):
        put.serve('refs-step2-all-sets-back', stored({'BRICK': later}))
    a.refresh()
    assert checked(a, 'BRICK') == checked(b, 'BRICK') == 'no', 'the later answer did not win in both tabs'


@ident('E04')
def test_the_timed_reload_keeps_typed_words(open_page, _id):
    put = open_page('refs-step2-all-sets-back', clock=True)
    verdict(put, 'P1', 'correct')
    put.page.locator('[id="w-P1"]').press_sequentially('older, about fif')
    put.page.locator('#words').press_sequentially('Pass one, with ')
    n = put.data_gets
    put.page.clock.fast_forward(61000)
    put.page.wait_for_timeout(300)
    assert put.data_gets > n, 'the page did not reload itself'
    show(put, 'P1')
    assert put.page.input_value('[id="w-P1"]') == 'older, about fif', 'the words typed on the card were lost by the reload'
    assert put.page.input_value('#words') == 'Pass one, with ', 'the words typed at the foot were lost by the reload'
    assert checked(put, 'P1') == 'correct'


@ident('E05')
def test_an_answer_changed_before_done(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    pics = set_of(put, 'BRICK')
    golden(put, 'BRICK', 0)
    verdict(put, 'BRICK', 'no')
    golden(put, 'BRICK', 2)
    verdict(put, 'BRICK', 'yes')
    put.page.wait_for_timeout(150)
    assert [x.get_attribute('data-golden') for x in card(put, 'BRICK').locator('[data-golden].on, [data-golden][aria-pressed="true"]').all()] == [f'BRICK:{pics[2]}'], 'the tick moved to another picture did not replace the first'
    assert last_of(put, 'set_answer') == {'action': 'set_answer', 'element_id': 'BRICK', 'verdict': 'yes', 'golden': pics[2], 'words': ''}, f'the stored answer is not the last one: {last_of(put, "set_answer")}'


@ident('E06')
def test_yes_with_no_starting_picture_and_correct_with_no_words(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    verdict(put, 'BRICK', 'yes')
    verdict(put, 'P1', 'correct')
    show(put, 'BRICK')
    assert 'choose the starting picture' in card(put, 'BRICK').inner_text().lower(), 'the card does not say that the starting picture is missing'
    show(put, 'P1')
    assert 'say what to correct' in card(put, 'P1').inner_text().lower(), 'the card does not say that the words are missing'
    done = put.page.locator('button[data-a="round-sets"]').first
    assert done.is_enabled(), 'Done cannot be pressed: its confirmation is where the unanswered cards are counted'
    done.click()
    assert re.search(rf'\b{len(to_judge(put))} unanswered\b', put.text('#done-confirm')), f'the confirmation reads "{put.text("#done-confirm")}"'


@ident('E07')
def test_done_pressed_twice(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    answer_all(put)
    put.page.evaluate('(() => { const f = window.fetch; window.fetch = (u, o) => o && o.method === "POST" ? new Promise(r => setTimeout(r, 600)).then(() => f(u, o)) : f(u, o); })()')   # a slow answer
    done = put.page.locator('button[data-a="round-sets"]').first
    done.click()
    put.page.wait_for_timeout(100)
    fin = put.page.locator('#done-confirm button[data-a="round-sets"]')
    target = fin.first if fin.count() else done
    if fin.count():
        target.click()
    try:
        target.click(timeout=400)   # the second press, while the first is still being recorded
    except Exception:
        pass   # the button is gone or off: the second press did nothing
    put.page.wait_for_timeout(60)
    assert not put.red_line(), f'the second press printed a red line: "{put.red_line()}"'
    put.page.wait_for_timeout(1600)
    assert len([p for p in put.posts if p['action'] == 'round-sets']) == 1, f'{len([p for p in put.posts if p["action"] == "round-sets"])} recordings were sent'
    assert not put.red_line(), f'the second press printed a red line: "{put.red_line()}"'


@ident('E08')
def test_the_server_refuses_done(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    put.answers['round-sets'] = (400, {'message': 'E2: the picture file of its set is gone; make the set again.'})
    said = answer_all(put)
    put.page.locator('button[data-a="round-sets"]').first.click()
    put.page.wait_for_timeout(150)
    fin = put.page.locator('#done-confirm button[data-a="round-sets"]')
    if fin.count():
        fin.click()
    put.page.wait_for_timeout(200)
    assert put.red_line() == 'Clamp kiln: the picture file of its set is gone; make the set again.'   # follow-up fix 5: the name, not the id (the server's refusal names E2)
    assert {e: checked(put, e) for e in said} == {e: a['verdict'] for e, a in said.items()}, 'the answers were lost by the refusal'
    show(put, 'E2')
    assert 'not recorded' in card(put, 'E2').inner_text().lower(), 'the card the refusal names shows nothing'


@ident('E09')
def test_the_connection_drops_while_an_answer_is_stored(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    sent = []
    put.page.route('**/visuals/act', lambda r: (sent.append(r.request.post_data), r.abort()))
    verdict(put, 'E2', 'no')
    put.page.wait_for_timeout(300)
    assert any('set_answer' in (s or '') for s in sent), 'no answer was sent, so nothing could fail to be saved'
    show(put, 'E2')
    assert 'not saved, try again' in card(put, 'E2').inner_text().lower()
    assert card(put, 'E2').locator('button[data-a="set-answer-retry"][data-el="E2"]').count() == 1
    assert 'not recorded yet' not in rail(put, 'E2').inner_text().lower(), 'the left list shows the answer as stored'


@ident('E10')
def test_the_sign_in_lapses(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    rail(put, 'E2').click()
    put.page.route('**/visuals/data', lambda r: r.fulfill(status=401, body=''))
    put.page.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
    put.page.wait_for_url('**/login?next=*', timeout=3000)
    assert put.page.url.endswith(f'/login?next=%2Fruns%2F{CODE}%2Fvisuals%23references%2FE2'), f'after signing in the operator is not returned to the card: {put.page.url}'
    back = open_page('refs-step2-all-sets-back', patch=stored({'E2': {'verdict': 'no', 'golden': None}}))
    back.go_hash('references/E2')
    assert card(back, 'E2').is_visible() and checked(back, 'E2') == 'no', 'the stored answer is not shown on return'


@ident('E11')
def test_a_set_comes_back_while_the_operator_is_on_another_card(open_page, _id):
    put = open_page('refs-step2-some-sets-not-made')
    rail(put, 'P1').click()
    verdict(put, 'P1', 'correct')
    put.page.locator('[id="w-P1"]').press_sequentially('older, about fifty')
    put.serve('refs-step2-all-sets-back')   # the brick's set is back
    put.refresh()
    assert put.page.locator('#rcards .rcard.on').get_attribute('data-unit-card') == 'P1' and card(put, 'P1').is_visible(), 'the operator\'s place was lost'
    assert put.page.input_value('[id="w-P1"]') == 'older, about fifty' and checked(put, 'P1') == 'correct', 'the typed words or the answer were lost'
    rail(put, 'BRICK').click()
    assert card(put, 'BRICK').locator('img[data-ref]').count() == 3, 'the card of the set that came back did not update'


@ident('E12')
def test_a_set_with_fewer_pictures_or_a_failed_picture(open_page, _id):
    put = open_page('refs-step2-set-with-a-failed-picture')
    show(put, 'E2')
    assert card(put, 'E2').locator('img[data-ref]').count() == 2   # a set of two, shown as it is
    show(put, 'BRICK')
    c = card(put, 'BRICK')
    srcs = [i.get_attribute('src') for i in c.locator('img').all()]
    assert all(srcs) and len(srcs) == 2, f'the failed picture is drawn as a picture with no file: {srcs}'
    assert 'failed' in c.inner_text().lower(), 'the card does not say that one picture failed'
    assert c.locator('[data-golden]').count() == 2 and all(c.locator(f'input[name="v-BRICK"][value="{v}"]').is_enabled() for v in ('yes', 'no', 'correct'))


@ident('E13')
def test_an_element_set_to_ignore(open_page, _id):
    one = open_page('refs-step1-to-answer')
    verdict(one, 'P1', 'ignore')
    assert 'ignored' in rail(one, 'P1').inner_text().lower() and rail(one, 'P1').locator('.wdot').count() == 0, 'step 1: the ignored element is not shown as ignored'
    verdict(one, 'P1', 'approve')   # brought back before Done
    assert 'ignored' not in rail(one, 'P1').inner_text().lower()
    two = open_page('refs-step2-element-ignored')
    assert 'ignored' in rail(two, 'P1').inner_text().lower() and rail(two, 'P1').locator('.wdot').count() == 0, f'step 2: the ignored element\'s card says "{" ".join(rail(two, "P1").inner_text().split())}"'
    assert 'P1' not in to_judge(two) and not counts_wrong(two)
    # follow-up fix 3: no longer step 1 only. A set that was never made is set aside at step 2: shown as set aside, nothing waits on it, and it can be brought back while the round is open
    three = open_page('refs-step2-set-aside')
    assert 'set aside' in rail(three, 'E3').inner_text().lower() and rail(three, 'E3').locator('.wdot').count() == 0, 'step 2: the element set aside is not shown as set aside'
    assert 'E3' not in to_judge(three) and not counts_wrong(three)
    three.open_tab('references')
    show(three, 'E3')
    assert card(three, 'E3').locator('button[data-a="set-back"]').inner_text() == 'Bring back'


@ident('E14')
def test_a_spec_corrected_after_its_set_was_made(open_page, _id):
    put = open_page('refs-step2-spec-corrected-after-set')
    show(put, 'BRICK')
    c = card(put, 'BRICK')
    assert 'the spec changed' in c.inner_text().lower(), 'the card does not say that the spec changed after the set was made'
    assert c.locator('button[data-a="set-make"][data-el="BRICK"]').count() == 1


@ident('E15')
def test_the_spend_cap_is_reached(open_page, _id):
    put = open_page('cross-spend-cap-reached')
    text = app_text(put)
    assert 'spend cap reached' in text.lower() and '₹120' in text and '₹100' in text, 'the page does not say in words that the spend cap is reached'
    assert not HEX.search(text) and 'vw ' not in text
    make = put.page.locator('button[data-a="set-make"]')
    if put.payload['round']['pass'] == 2:
        assert make.count() >= 1, 'no "Make it now" on the sets the cap refused'
    assert all(b.is_disabled() for b in make.all()), '"Make it now" is live though the cap is reached'
    done = put.page.locator('#action button.go').first
    assert done.count() and done.is_enabled(), 'follow-up fix 2: Done is off at the cap, so a Yes (which costs nothing) cannot be recorded'   # was: Done disabled at the cap
    if done.count() and done.is_enabled():
        done.click()
        put.page.wait_for_timeout(150)
        again = put.page.locator('#action button.go, #done-confirm button.go').first
        if again.count() and again.is_enabled():
            again.click()
        put.page.wait_for_timeout(200)
    assert not put.posts, f'something was sent to be queued: {put.posts}'


@ident('E16')
def test_a_picture_file_is_missing(open_page, _id):
    put = open_page('cross-picture-file-missing')
    broken = put.page.evaluate(PICTURES)
    assert not broken, f'{len(broken)} broken pictures on screen'
    assert put.page.locator('#s-references .ph').count() >= 1 and 'picture not available' in put.section_text().lower()
    show(put, 'BRICK')
    assert put.page.is_enabled('input[name="v-BRICK"][value="no"]'), 'the card cannot be answered'


@ident('E17')
def test_a_supplied_still_and_a_short_supplied_movie(open_page, _id):
    still = open_page('takes-shot-filled-with-supplied-still', patch=supplied())
    show(still, 'VS1')
    text = still.page.locator('[id="card-VS1"]').inner_text()
    assert 'made outside; checks skipped' in text and 'My own photograph.' in text, 'integration step A: a handed-in still does not say it was made outside, with how'
    assert 'Supplied by SK' in text and 'assembly holds the last frame' in text, f'a supplied still is shown as: "{" ".join(text.split())[:160]}"'
    assert still.page.locator('[id="card-VS1"] img[src*="uploads/wall.png"]').count() == 1, 'the supplied still is not shown'
    movie = open_page('takes-shot-filled-with-supplied-movie', patch=supplied(duration_s=6.0))   # the slot is 10 s
    show(movie, 'VS1')
    text = movie.page.locator('[id="card-VS1"]').inner_text()
    assert 'Supplied by SK' in text and 'assembly holds the last frame' in text, 'a supplied movie shorter than its slot does not say what assembly will do'


@ident('E18')
def test_long_names_and_long_words(open_page, _id):
    for size in ('1920x1080', '1366x768'):
        put = open_page('cross-long-names', size=size)
        show(put, 'E3')
        put.page.fill('[id="w-E3"]', 'the wall is too clean and too new; it should look weathered, with moss at the foot and a chipped corner ' * 4)
        put.page.fill('#words', 'A long line of words from the operator about this pass of the round. ' * 6)
        got = put.page.evaluate(LAYOUT)
        assert got['pageWidth'] <= got['width'] and not got['outside'], f'at {size}: the page is {got["pageWidth"]} px wide in {got["width"]} px; outside: {got["outside"][:4]}'
        title = rail(put, 'E3').locator('.t1').bounding_box()
        box = put.page.locator('#rail').bounding_box()
        assert title['x'] + title['width'] <= box['x'] + box['width'] + 1, f'at {size}: the long name runs out of the left list'


@ident('E19')
def test_a_run_held_by_another_machine(open_page, _id):
    """Changed by the follow-up (fix 1). The page's data cannot say that another operator's machine holds the run: `busy` only says the run's lock
    was held at the moment of that read (the chat tool was making a call). So the page says so quietly and every control stays usable.
    E19 itself is NOT covered until the data carries who holds the run (README, CONTRACT)."""
    put = open_page('cross-run-busy-read-only')
    assert put.payload['busy'] is True
    line = put.text('#line').lower()
    assert 'read-only' not in line and 'the server is busy; the page reads again shortly' in line, f'the header says: "{put.text("#line")}"'
    assert put.page.locator('#line .err').count() == 0 and put.bar()[0] != 'err', 'a busy answer is shown as an error'
    dead = [b for b in put.page.locator('#app button[data-a], #app input[type=radio], #app [data-golden]').all() if b.is_visible() and not b.is_enabled()]
    assert not dead, f'{len(dead)} controls were switched off by a busy answer'


@ident('E20')
def test_a_run_with_an_open_defect(open_page, _id):
    put = open_page('cross-open-defect')
    assert 'a defect is open; nothing can be recorded until it is fixed' in put.text('#line')
    live = [b for b in put.page.locator('#app button[data-a], #app input[type=radio], #app [data-golden]').all() if b.is_visible() and b.is_enabled() and b.get_attribute('aria-disabled') != 'true']
    assert not live, f'{len(live)} controls are on though every write is refused'
    assert kind_of(put, 'BRICK') == 'material' and round_of(put)
