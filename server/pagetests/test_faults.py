"""Layer 3: one test per reported fault. U1 to U16 are what SK met on VW-19 (videobuilder-v4/phase2/reference-page-ui-issues.md), X1 to
X7 were found reading the code (page-facts.md, section 2), N1 to N4 by layer 2 (layer2-findings.md). Each test does what the operator
did and asserts the fault is ABSENT: it fails while the fault is in the page and passes once it is fixed."""
import re

from kit import HEX, answer_all, card, counts_wrong, golden, ident, last_of, opened, panel, press_done, rail, set_of, show, stored, to_judge, verdict
from test_states import PICTURES

SPEC_BUTTON = 'button[data-a="approve-spec"]:visible, button[data-a="approve-specs"]:visible'
KINDS = ('picture to answer', 'set to judge', 'material spec to approve', 'drawing spec to approve', 'spec to approve')


# ---------- what SK met ----------

@ident('U01')
def test_the_three_numbers_agree_and_name_what_waits(open_page, _id):
    put = open_page('refs-step1-to-answer')
    header, tab = put.header_count(), put.tab_counts()['references']
    marked = sum(c['waiting'] for c in put.cards())
    assert header == sum(put.tab_counts().values()) and tab == marked == put.waiting_chip(), \
        f'the header says {header} waiting, the References tab {tab}, the list shows {marked} marked cards and "Waiting for me ({put.waiting_chip()})"'
    put.click('#wcount')
    labels = put.page.locator('#wlist a').all_inner_texts()
    assert all(any(k in t.lower() for k in KINDS) for t in labels), f'the waiting things are not named by their kind: {labels}'


@ident('U02')
def test_approved_and_rejected_are_plain_to_see(open_page, _id):
    put = open_page('refs-step1-answered')
    show(put, 'E1')
    pic = card(put, 'E1').locator('.pic').first.inner_text().lower()
    assert 'approved' in pic, f'the approved footage picture\'s thumbnail says only "{pic.strip()}"'
    two = open_page('refs-step2-second-pass')
    show(two, 'P1')
    assert re.search(r'\d+ (approved|rejected|not answered)', card(two, 'P1').inner_text().lower()), 'the card has no plain summary of its pictures'


@ident('U03')
def test_a_waiting_mark_says_what_waits(open_page, _id):
    put = open_page('refs-step1-picture-answered-spec-waits')
    marked = put.page.locator('#rcards .rcard:has(.wdot)')
    assert marked.count() == 1
    text = ' '.join(marked.inner_text().split()).lower()
    assert 'spec to approve' in text, f'the marked card says "{text}": nothing says that a spec waits'
    marked.locator('.wdot').click()
    assert put.page.locator(SPEC_BUTTON).count() >= 1, 'a click on the mark does not open the spec'


@ident('U04')
def test_specs_can_be_seen_and_approved_and_their_links_open(open_page, _id):
    put = open_page('refs-step1-to-answer', tab='record')
    put.go_hash('references/BRICK/specs')
    assert not put.red_line(), f'the link printed: "{put.red_line()}"'
    assert put.page.locator('#s-references table:visible').count() >= 1 and put.page.locator(SPEC_BUTTON).count() >= 1, 'the brick\'s card shows no spec table and no Approve'
    film = open_page('pictures-drawing-specs-waiting-drawn-only-film', tab='record')
    film.go_hash('pictures/specs/specs')
    assert not film.red_line(), f'the link printed: "{film.red_line()}"'
    assert film.page.locator(SPEC_BUTTON).count() >= 1, f'the link opened: "{film.section_text()[:70]}"'


@ident('U05')
def test_done_at_step_one_says_what_will_not_be_made(open_page, _id):
    put = open_page('refs-step1-to-answer')
    assert put.visible('#notmade') and 'Red brick' in put.text('#notmade'), 'Done is offered with nothing said about the brick\'s set, whose spec is not approved'
    put.answers['round-done'] = (200, {'pass': 'making', 'queued': ['E2', 'P1'], 'errors': {'BRICK': 'the material spec of BRICK is not approved'}})
    press_done(put, 'round-done')
    assert 'Red brick' in put.bar()[1] and 'BRICK' not in put.bar()[1], f'after Done the page says only: "{put.bar()[1]}"'


@ident('U06')
def test_a_click_on_a_card_opens_the_same_as_next_waiting(open_page, _id):
    a = open_page('refs-step1-to-answer', tab='record')
    a.click('#wnext')
    a.page.wait_for_timeout(100)
    b = open_page('refs-step1-to-answer')
    rail(b, 'E1').click()
    assert opened(b)['pictures'] == opened(a)['pictures'] == ['F1'], f'Next waiting opens {opened(a)["pictures"]}, the card opens {opened(b)["pictures"]}'


@ident('U07')
def test_no_tool_command_on_a_set_not_made(open_page, _id):
    for state in ('refs-step2-some-sets-not-made', 'cross-spend-cap-reached'):
        text = open_page(state).section_text()
        assert 'vw visuals' not in text and '`' not in text, f'{state}: the card tells the operator to run a command: "{text[text.find("`"):][:60]}"'


@ident('U08')
def test_the_reason_is_refreshed_when_its_cause_is_settled(open_page, _id):
    put = open_page('refs-step2-spec-approved-after-refusal')
    show(put, 'BRICK')
    assert 'is not approved' not in card(put, 'BRICK').inner_text(), 'the card still says the spec is not approved, after it was approved'


@ident('U09')
def test_no_is_not_the_way_to_make_a_set(open_page, _id):
    put = open_page('refs-step2-some-sets-not-made')
    show(put, 'BRICK')
    text = card(put, 'BRICK').inner_text()
    assert 'Say No' not in text, 'the page asks for "No" to get the set made'
    assert card(put, 'BRICK').get_by_text('Make it now', exact=True).count() == 1


@ident('U10')
def test_one_place_for_the_decision_on_a_set(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    show(put, 'BRICK')
    card(put, 'BRICK').locator('img[data-ref]').nth(2).click()
    assert put.page.locator('#panel button[data-a]').all_inner_texts() == [], 'the large picture has its own Approve and Reject beside the set\'s Yes, No and Correct it'
    tick = card(put, 'BRICK').locator('[data-golden]').first
    assert tick.inner_text().strip() == 'Use this as the starting picture', 'the control that chooses the starting picture is an unlabelled circle'


@ident('U11')
def test_done_is_not_hit_by_accident(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    answer_all(put)
    put.page.locator('button[data-a="round-sets"]').first.click()
    put.page.wait_for_timeout(200)
    assert not last_of(put, 'round-sets'), 'one click on Done recorded the whole round and started the paid remakes'
    assert re.search(r'\d+ approved .*\d+ made again \(paid.*\d+ unanswered', put.text('#done-confirm'))


@ident('U12')
def test_an_answer_shows_in_the_left_list_at_once(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    golden(put, 'BRICK')
    verdict(put, 'BRICK', 'yes')
    text = ' '.join(rail(put, 'BRICK').inner_text().split()).lower()
    assert 'your verdict' not in text and re.search(r'\byes\b', text), f'after the starting picture and Yes the card still says "{text}"'
    assert rail(put, 'BRICK').locator('.wdot').count() == 0


@ident('U13')
def test_done_is_not_refused_over_a_picture_approved_on_the_right(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    show(put, 'BRICK')
    pic = set_of(put, 'BRICK')[2]
    card(put, 'BRICK').locator(f'img[data-ref="{pic}"]').click()
    assert put.page.locator('#panel button[data-a="approve"]').count() == 0, 'a set picture can be approved on the right, which takes it out of its set'
    put.answers['round-sets'] = (400, {'message': f'BRICK: {pic} is not a picture of its set.'})   # what the server answered SK
    answer_all(put)
    press_done(put)
    put.page.wait_for_timeout(150)
    assert put.bar()[1] and not HEX.search(put.bar()[1]), f'the refusal prints a picture id: "{put.bar()[1]}"'


@ident('U14')
def test_the_panel_is_empty_on_a_card_with_no_picture(open_page, _id):
    put = open_page('refs-step2-some-sets-not-made')
    show(put, 'P1')
    card(put, 'P1').locator('img[data-ref]').first.click()
    rail(put, 'BRICK').click()
    assert opened(put) == {'pictures': [], 'take': '', 'buttons': []}, f'on the card with no picture the panel shows: {opened(put)}'


@ident('U15')
def test_the_selections_are_stored(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    pic = set_of(put, 'BRICK')[0]
    golden(put, 'BRICK')
    verdict(put, 'BRICK', 'yes')
    verdict(put, 'E2', 'no')
    put.open_tab('plan')
    put.open_tab('references')
    seen = [put.page.locator(f'input[name="v-{e}"]:checked').count() for e in ('BRICK', 'E2')]
    assert seen == [1, 1], 'a look at another tab lost the answers'
    answers = {p['element_id']: p for p in put.posts if p['action'] == 'set_answer'}
    stored(answers)(put.payload)   # the server holds what the page stored
    put.page.reload()
    put.page.wait_for_function('document.getElementById("line").textContent !== "Loading…"')
    put.open_tab('references')
    back = {e: (put.page.locator(f'input[name="v-{e}"]:checked').get_attribute('value') if put.page.locator(f'input[name="v-{e}"]:checked').count() else None) for e in ('BRICK', 'E2')}
    assert back == {'BRICK': 'yes', 'E2': 'no'}, f'after the page was opened again the answers are {back}'
    assert put.page.locator(f'[data-golden="BRICK:{pic}"]').get_attribute('aria-pressed') == 'true'


@ident('U16')
def test_a_supplied_video_is_visible_on_takes(open_page, _id):
    put = open_page('takes-shot-filled-with-supplied-movie')
    show(put, 'VS1')
    text = put.page.locator('[id="card-VS1"]').inner_text()
    assert 'Waiting for the assistant' not in text and 'No take yet' not in text, f'the filled shot says: "{" ".join(text.split())[-110:]}"'
    assert put.page.locator('[id="card-VS1"] video, [id="card-VS1"] button[data-play]').count() >= 1, 'the supplied video cannot be played'
    assert 'with the assistant' not in rail(put, 'VS1').inner_text().lower()


# ---------- found while reading the code ----------

@ident('X1')
def test_next_waiting_at_step_two(open_page, _id):
    put = open_page('refs-step2-all-sets-back', tab='plan')
    put.click('#wnext')
    put.page.wait_for_timeout(100)
    assert put.red_line() == '' and put.active_tab() == 'references'


@ident('X2')
def test_set_cards_carry_the_waiting_mark_at_step_two(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    marked = sorted(c['unit'] for c in put.cards() if c['waiting'])
    assert marked == sorted(to_judge(put)), f'the sets to judge are {sorted(to_judge(put))}; the cards marked as waiting are {marked}'
    assert put.waiting_chip() == len(marked)


@ident('X3')
def test_a_specs_link_where_the_table_is_on_screen(open_page, _id):
    put = open_page('refs-no-round-kept')
    put.go_hash('references/BRICK/specs')
    assert put.visible('[id="card-mspec-BRICK"]') and put.red_line() == '', f'the table is on screen and the link prints: "{put.red_line()}"'


@ident('X4')
def test_the_green_line_after_done_on_step_one(open_page, _id):
    put = open_page('refs-step1-answered')
    press_done(put, 'round-done')
    assert 'pass 2' not in put.bar()[1], f'a kept film has no pass 2: "{put.bar()[1]}"'


@ident('X5')
def test_a_set_approved_earlier_needs_nothing_on_a_later_pass(open_page, _id):
    put = open_page('refs-step2-second-pass')
    verdict(put, 'P1', 'yes')
    assert put.page.locator('button[data-a="round-sets"]').first.is_enabled(), f'Done stays locked: "{put.text("#tray span")}"'


@ident('X6')
def test_nothing_fits_can_take_its_words(open_page, _id):
    put = open_page('refs-older-no-round-element-view')
    rail(put, 'E2').click()
    put.click('#action button[data-a="nothing-fits"]')
    assert put.page.locator('.foot textarea:visible').count() == 1, f'the page asks for words ("{put.red_line()}") and has no box to type them in'


@ident('X7')
def test_a_failed_request_and_a_refusal_look_different(open_page, _id):
    refused = open_page('pictures-candidate')
    refused.answers['approve'] = (400, {'message': 'IM1: the picture changed; look at it again.'})
    refused.click('#panel button[data-a="approve"]')
    refused.page.wait_for_timeout(200)
    dropped = open_page('pictures-candidate')
    dropped.page.route('**/visuals/act', lambda r: r.abort())
    dropped.click('#panel button[data-a="approve"]')
    dropped.page.wait_for_timeout(200)
    assert refused.bar()[0] != dropped.bar()[0], f'a refusal shows as {refused.bar()}, a failed connection as {dropped.bar()}'


# ---------- found by layer 2 ----------

@ident('N1')
def test_the_link_to_a_waiting_footage_picture(open_page, _id):
    for state in ('refs-step1-to-answer', 'refs-older-pass1'):
        put = open_page(state, tab='plan')
        put.go_hash('references/E1/F1')
        assert put.red_line() == '', f'{state}: the picture waits and the link prints "{put.red_line()}"'
        assert 'F1' in opened(put)['pictures'] or card(put, 'E1').locator('img[data-ref="F1"]').is_visible()


@ident('N2')
def test_a_material_spec_is_not_shown_as_a_drawing_spec_on_pictures(open_page, _id):
    put = open_page('refs-no-round-kept', tab='pictures')
    marked = [c['title'] for c in put.cards() if c['waiting']]
    assert put.tab_counts()['pictures'] == len(marked) == put.waiting_chip(), f'the Pictures tab says {put.tab_counts()["pictures"]} waiting and marks {marked}'


@ident('N3')
def test_things_waiting_on_treatment_plan_and_record_are_counted(open_page, _id):
    wrong = {}
    for state in ('treatment-draft', 'plan-proposed', 'record-gaps-ready'):
        put = open_page(state)
        marked = sum(c['waiting'] for c in put.cards())
        if not (marked and put.header_count() >= marked and put.page.locator('#wnext').count() == 1) or counts_wrong(put):
            wrong[state] = f'{marked} cards wait, the header says {put.header_count()}'
    assert not wrong, f'{wrong}'


@ident('N4')
def test_a_missing_picture_file_shows_a_placeholder(open_page, _id):
    put = open_page('cross-picture-file-missing')
    broken = put.page.evaluate(PICTURES)
    assert not broken, f'{len(broken)} broken pictures; the first: {broken[0]}'
    assert panel(put) == '' or 'picture not available' in put.section_text().lower()
