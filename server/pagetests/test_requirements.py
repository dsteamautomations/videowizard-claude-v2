"""Layer 3: one test per approved requirement R1 to R24 (videobuilder-v4/phase2/ui/requirements-and-test-plan.md, section 3).
Each asserts what the requirement says the operator sees. A requirement not built yet fails here; the names it is tested by are in
CONTRACT.md. Nothing is skipped or marked as an expected failure."""
import re

from kit import (HEX, answer_all, app_text, card, counts_wrong, golden, ident, kind_of, last_of, next_waiting_wrong, opened, panel, press_done, rail, round_of, set_of, show,
                 stored, to_judge, verdict)

KINDS = ('picture to answer', 'set to judge', 'material spec to approve', 'drawing spec to approve', 'spec to approve')
VERDICT_BUTTONS = '#panel button[data-a="approve"], #panel button[data-a="reject"], #panel button[data-a="fix"]'


def shown_set_pictures(put):
    by = {r['id']: r for r in put.payload['references']}
    return [(eid, rid) for eid, r in round_of(put).items() if not r.get('ignored') for rid in r.get('set') or [] if by.get(rid, {}).get('status') in ('candidate', 'approved')]


def supplied(payload):
    payload['gaps'][1]['shots'][0]['asset'].update(by='SK', quote='My own shot of the pour.')


@ident('R01')
def test_a_set_is_decided_in_one_place(open_page, _id):
    wrong = []
    for state in ('refs-step2-all-sets-back', 'refs-step2-second-pass'):
        put = open_page(state)
        for eid, rid in shown_set_pictures(put):
            show(put, eid)
            card(put, eid).locator(f'img[data-ref="{rid}"]').click()
            b = put.page.locator(VERDICT_BUTTONS).all_inner_texts()
            if b:
                wrong.append(f'{state}, {eid} picture {rid[-2:]}: {b}')
    assert not wrong, f'the large picture of a set being judged carries its own verdict buttons: {wrong[:4]} ({len(wrong)} pictures)'


@ident('R02')
def test_the_starting_picture_has_a_labelled_control(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    for eid in to_judge(put):
        show(put, eid)
        if kind_of(put, eid) == 'person':
            assert 'the full-length front picture is taken automatically' in card(put, eid).inner_text(), f'{eid}: a person\'s set does not say which picture is taken'
            continue
        texts = [t.strip() for t in card(put, eid).locator('[data-golden]').all_inner_texts()]
        assert texts == ['Use this as the starting picture'] * len(set_of(put, eid)), f'{eid}: the control that chooses the starting picture reads {texts}'
    golden(put, 'BRICK', 1)
    assert [x.get_attribute('aria-pressed') for x in card(put, 'BRICK').locator('[data-golden]').all()] == ['false', 'true', 'false']


@ident('R03')
def test_a_footage_picture_is_answered_in_the_centre(open_page, _id):
    put = open_page('refs-step1-to-answer')
    show(put, 'E1')
    c = card(put, 'E1')
    n = c.locator('img[data-ref]').count()
    assert n == 1
    assert c.get_by_text('Use this picture', exact=True).count() == n and c.get_by_text('Ignore', exact=True).count() == n, 'the footage picture has no "Use this picture" and "Ignore" of its own in the centre'
    c.locator('img[data-ref="F1"]').click()
    assert put.page.locator(VERDICT_BUTTONS).all_inner_texts() == [], 'the large picture carries a second set of verdict buttons'


@ident('R04')
def test_the_right_panel_follows_the_selected_card(open_page, _id):
    put = open_page('refs-step2-some-sets-not-made')
    show(put, 'P1')
    card(put, 'P1').locator('img[data-ref]').first.click()
    assert opened(put)['pictures'] == [set_of(put, 'P1')[0]]
    rail(put, 'BRICK').click()   # a card with no picture
    assert opened(put)['pictures'] == [], f'the panel still shows another card\'s picture: {panel(put)[:60]!r}'
    rail(put, 'E2').click()
    assert set(opened(put)['pictures']) <= set(set_of(put, 'E2')) and opened(put)['pictures'], 'the panel does not show the selected card\'s picture'


@ident('R05')
def test_a_card_opens_what_next_waiting_opens(open_page, _id):
    differ = []
    for state in ('refs-step1-to-answer', 'pictures-candidate', 'takes-ready-to-select'):
        a = open_page(state, tab='record')
        w = a.payload['waiting'][0]
        a.click('#wnext')
        a.page.wait_for_timeout(100)
        by_next = opened(a)
        b = open_page(state, tab='record')
        b.open_tab(w['step'])
        rail(b, w['group']).click()
        by_card = opened(b)
        if by_next != by_card or not (by_card['pictures'] or by_card['take']):
            differ.append(f'{w["label"]}: Next waiting opens {by_next}, the card opens {by_card}')
    assert not differ, '; '.join(differ)


@ident('R06')
def test_the_three_counts_agree(open_page, _id):
    wrong = {}
    for state in ('refs-step1-to-answer', 'refs-step2-all-sets-back', 'refs-step2-some-sets-not-made', 'pictures-drawing-specs-waiting'):
        w = counts_wrong(open_page(state))
        if w:
            wrong[state] = w
    assert not wrong, f'{wrong}'


@ident('R07')
def test_every_waiting_thing_is_named_by_its_kind(open_page, _id):
    unnamed = []
    for state in ('refs-step1-to-answer', 'refs-step2-all-sets-back', 'pictures-drawing-specs-waiting'):
        put = open_page(state)
        put.click('#wcount')
        unnamed += [f'{state}, the list: "{t}"' for t in put.page.locator('#wlist a').all_inner_texts() if not any(k in t.lower() for k in KINDS)]
        cards = put.page.locator('#rcards .rcard:has(.wdot)').all_inner_texts()
        assert cards, f'{state}: no card carries the waiting mark'
        unnamed += [f'{state}, the card: "{" ".join(t.split())}"' for t in cards if not any(k in t.lower() for k in KINDS)]
    assert not unnamed, f'waiting things not named by their kind: {unnamed}'


@ident('R08')
def test_the_waiting_mark_says_what_waits_and_opens_it(open_page, _id):
    put = open_page('refs-step1-answered', patch=None)
    assert put.page.locator('#rcards .rcard .wdot').count() == 0, 'a card is marked though its picture is answered and its spec approved'
    put = open_page('refs-step1-to-answer')
    brick = rail(put, 'BRICK')
    assert brick.locator('.wdot').count() == 1 and 'spec to approve' in brick.inner_text().lower(), f'the brick\'s card says "{" ".join(brick.inner_text().split())}"'
    brick.locator('.wdot').click()
    box = put.page.locator('[id="card-mspec-BRICK"]')
    assert box.count() == 1 and box.is_visible() and box.locator('button[data-a="approve-spec"]').is_visible(), 'a click on the mark did not open the spec that waits'


@ident('R09')
def test_next_waiting_always_lands_on_something(open_page, _id):
    wrong = {}
    for state in ('refs-step1-to-answer', 'refs-step2-all-sets-back', 'refs-step2-some-sets-not-made', 'pictures-drawing-specs-waiting-drawn-only-film'):
        w = next_waiting_wrong(open_page(state))
        if w:
            wrong[state] = w
    assert not wrong, f'{wrong}'


@ident('R10')
def test_every_link_opens_what_it_names(open_page, _id):
    dead = []
    for state in ('refs-step1-to-answer', 'refs-no-round-kept', 'refs-step2-some-sets-not-made', 'pictures-drawing-specs-waiting', 'pictures-drawing-specs-waiting-drawn-only-film'):
        put = open_page(state, tab='record')
        for w in put.payload['waiting']:
            h = w['link'].split('#', 1)[1]
            put.go_hash(h)
            if put.red_line():
                dead.append(f'{state}: "{w["label"]}" prints "{put.red_line()}"')
            elif h.endswith('/specs') and not put.page.locator('button[data-a="approve-spec"]:visible, button[data-a="approve-specs"]:visible').count():
                dead.append(f'{state}: "{w["label"]}" shows no spec to approve')
    assert not dead, f'{dead}'


@ident('R11')
def test_specs_are_shown_as_tables_with_approve_and_correct(open_page, _id):
    for state in ('refs-step1-to-answer', 'refs-step2-some-sets-not-made'):   # a material spec, while a round is open
        put = open_page(state)
        show(put, 'BRICK')
        box = card(put, 'BRICK').locator('[id="card-mspec-BRICK"]')
        assert box.count() == 1, f'{state}: the brick\'s card shows no material spec table'
        assert box.locator('table tr').count() >= 4 and box.locator('button[data-a="approve-spec"][data-shot="element:BRICK"]').is_visible() and box.locator('button[data-a="correct-spec"]').is_visible()
    draw = open_page('pictures-drawing-specs-waiting-drawn-only-film', tab='record')   # a drawing spec, where its waiting link points
    draw.go_hash(draw.payload['waiting'][0]['link'].split('#', 1)[1])
    for shot in ('IM1', 'DG2'):
        show(draw, shot)
        c = draw.page.locator(f'[id="card-{shot}"]')
        assert c.count() == 1 and c.locator('table tr').count() >= 3, f'the card of {shot} shows no drawing spec table on the {draw.active_tab()} tab'
        assert c.locator(f'button[data-a="approve-spec"][data-shot="{shot}"]').is_visible() and c.locator('button[data-a="correct-spec"]').is_visible()


@ident('R12')
def test_before_done_the_page_lists_what_will_not_be_made(open_page, _id):
    put = open_page('refs-step1-to-answer')
    box = put.page.locator('#notmade')
    assert box.count() == 1 and box.is_visible(), 'nothing says before Done that the brick\'s set will not be made'
    assert '1 will not be made' in box.inner_text()
    line = box.locator('[data-notmade="BRICK"]')
    assert 'spec' in line.inner_text().lower() and line.locator('button[data-a="approve-spec"][data-shot="element:BRICK"]').is_visible(), 'the line has no reason, or no control to settle it'
    settled = open_page('refs-step1-answered')
    assert not settled.visible('#notmade'), 'the list is shown though every set will be made'


@ident('R13')
def test_each_answer_is_stored_as_it_is_made(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    pic = set_of(put, 'BRICK')[1]
    golden(put, 'BRICK', 1)
    put.page.wait_for_timeout(150)
    assert last_of(put, 'set_answer') == {'action': 'set_answer', 'element_id': 'BRICK', 'verdict': None, 'golden': pic, 'words': ''}, f'choosing the starting picture stored nothing: {put.posts}'
    verdict(put, 'BRICK', 'yes')
    put.page.wait_for_timeout(150)
    assert last_of(put, 'set_answer') == {'action': 'set_answer', 'element_id': 'BRICK', 'verdict': 'yes', 'golden': pic, 'words': ''}
    verdict(put, 'E2', 'no')
    put.page.wait_for_timeout(150)
    assert last_of(put, 'set_answer') == {'action': 'set_answer', 'element_id': 'E2', 'verdict': 'no', 'golden': None, 'words': ''}
    verdict(put, 'P1', 'correct', 'older, about fifty')
    put.page.locator('[id="w-P1"]').blur()
    put.page.wait_for_timeout(150)
    assert last_of(put, 'set_answer') == {'action': 'set_answer', 'element_id': 'P1', 'verdict': 'correct', 'golden': None, 'words': 'older, about fifty'}
    again = open_page('refs-step2-all-sets-back', patch=stored({'BRICK': {'verdict': 'yes', 'golden': pic}, 'E2': {'verdict': 'no', 'golden': None}, 'P1': {'verdict': 'correct', 'golden': None, 'words': 'older, about fifty'}}))
    shown = {e: (again.page.locator(f'input[name="v-{e}"]:checked').get_attribute('value') if again.page.locator(f'input[name="v-{e}"]:checked').count() else None) for e in ('BRICK', 'E2', 'P1')}
    assert shown == {'BRICK': 'yes', 'E2': 'no', 'P1': 'correct'}, f'reopening the page shows {shown}'
    assert again.page.locator(f'[data-golden="BRICK:{pic}"]').get_attribute('aria-pressed') == 'true' and again.page.input_value('[id="w-P1"]') == 'older, about fifty'


@ident('R14')
def test_an_answered_card_shows_its_answer_in_the_left_list(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    pic = set_of(put, 'BRICK')[1]
    golden(put, 'BRICK', 1)
    verdict(put, 'BRICK', 'yes')
    verdict(put, 'E2', 'no')
    verdict(put, 'P1', 'correct', 'older')
    said = {e: ' '.join(rail(put, e).inner_text().split()).lower() for e in ('BRICK', 'E2', 'P1')}
    for e, word in (('BRICK', 'yes'), ('E2', 'no'), ('P1', 'correct it')):
        assert re.search(rf'\b{word}\b', said[e]) and 'not recorded yet' in said[e], f'the card of {e} says "{said[e]}"'
        assert rail(put, e).locator('.wdot').count() == 0, f'{e} still carries the waiting mark'
    assert pic in (rail(put, 'BRICK').locator('img').get_attribute('src') or ''), 'the card does not show the chosen starting picture'


@ident('R15')
def test_done_asks_once_with_the_counts(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    judged = to_judge(put)
    things = [e for e in judged if kind_of(put, e) != 'person']
    golden(put, things[0])
    verdict(put, things[0], 'yes')
    verdict(put, things[1], 'no')
    n = len(put.posts)
    done = put.page.locator('button[data-a="round-sets"]').first
    assert done.is_enabled(), 'Done cannot be pressed with a card unanswered: it must count it, not hide'
    done.click()
    put.page.wait_for_timeout(200)
    assert not last_of(put, 'round-sets'), 'Done recorded at the first press, with no confirmation'
    text = put.text('#done-confirm')
    assert re.search(r'\b1 approved\b', text) and re.search(r'\b1 made again \(paid', text) and re.search(rf'\b{len(judged) - 2} unanswered\b', text), f'the confirmation reads "{text}"'
    put.click('#done-confirm button[data-a="round-picks-back"]')
    assert not put.visible('#done-confirm') and len([b for b in put.posts[n:] if b['action'] == 'round-sets']) == 0


@ident('R16')
def test_a_later_pass_asks_only_for_the_sets_made_again(open_page, _id):
    put = open_page('refs-step2-second-pass')
    for eid in ('BRICK', 'E2'):
        show(put, eid)
        c = card(put, eid)
        assert 'approved' in c.inner_text().lower() and c.locator('input[type=radio]').count() == 0, f'{eid}, approved in the first pass, is asked again'
    verdict(put, 'P1', 'yes')
    assert put.page.locator('button[data-a="round-sets"]').first.is_enabled(), f'Done is locked: {put.text("#tray")}'
    put.page.fill('#words', 'Pass two.')
    press_done(put)
    assert last_of(put, 'round-sets')['verdicts'] == {'P1': {'verdict': 'yes', 'words': '', 'golden': ''}}


@ident('R17')
def test_a_set_not_made_offers_make_it_now(open_page, _id):
    put = open_page('refs-step2-some-sets-not-made')
    show(put, 'BRICK')
    b = card(put, 'BRICK').locator('button[data-a="set-make"][data-el="BRICK"]')
    assert b.count() == 1 and b.inner_text() == 'Make it now', 'the card of a set that was not made has no "Make it now"'
    assert 'say no' not in card(put, 'BRICK').inner_text().lower(), 'the operator is told to answer No to get the set made'
    b.click()
    put.wait_posts(1)
    assert last_of(put, 'set_make') == {'action': 'set_make', 'element_id': 'BRICK'}


@ident('R18')
def test_the_reason_on_a_set_not_made_is_the_present_one(open_page, _id):
    put = open_page('refs-step2-spec-approved-after-refusal')
    show(put, 'BRICK')
    text = card(put, 'BRICK').inner_text().lower()
    assert 'is not approved' not in text, 'the card still gives the old reason: the spec has been approved since'
    assert 'spec approved' in text and card(put, 'BRICK').locator('button[data-a="set-make"]').count() == 1


@ident('R19')
def test_no_message_gives_a_command_or_an_internal_id(open_page, _id):
    put = open_page('refs-step2-some-sets-not-made')
    text = app_text(put)
    assert 'vw visuals' not in text and '`' not in text, 'the page tells the operator to run a tool command'
    made = open_page('refs-step2-all-sets-back')
    pic = set_of(made, 'BRICK')[2]
    made.answers['round-sets'] = (400, {'message': f'BRICK: {pic} is not a picture of its set.'})
    answer_all(made)
    press_done(made)
    made.page.wait_for_timeout(150)
    bar = made.bar()[1]
    assert bar and not HEX.search(bar), f'the message prints an internal picture id: "{bar}"'
    assert not HEX.search(app_text(made)), 'the page prints an internal id'


@ident('R20')
def test_every_thumbnail_carries_its_state(open_page, _id):
    bare, no_summary = [], []
    for state in ('refs-step1-answered', 'refs-step2-all-sets-back', 'refs-step2-second-pass'):
        put = open_page(state)
        for eid in round_of(put):
            show(put, eid)
            c = card(put, eid)
            pics = c.locator('.pic')
            if not c.count() or not pics.count():
                continue
            bare += [f'{state}, {eid}' for t in pics.all_inner_texts() if not re.search(r'approved|rejected|not answered', t.lower())]
            if not re.search(r'\d+ (approved|rejected|not answered)', c.inner_text().lower()):
                no_summary.append(f'{state}, {eid}')
    assert not bare, f'{len(bare)} thumbnails show no state: {sorted(set(bare))}'
    assert not no_summary, f'cards with no one-line summary: {no_summary}'


@ident('R21')
def test_a_supplied_shot_is_shown_as_done_on_takes(open_page, _id):
    put = open_page('takes-shot-filled-with-supplied-movie', patch=supplied)
    assert rail(put, 'VS1').locator('.badge').inner_text().lower() == 'done', f'the left list says "{rail(put, "VS1").locator(".badge").inner_text()}"'
    show(put, 'VS1')
    c = put.page.locator('[id="card-VS1"]')
    text = c.inner_text()
    assert 'waiting for the assistant' not in text.lower() and 'No take yet' not in text, 'the shot is shown as waiting though it is filled'
    assert 'ok' in c.locator('.turn').get_attribute('class').split() and 'Supplied by SK' in text and 'My own shot of the pour.' in text
    player = c.locator('video, button[data-play]')
    src = player.first.get_attribute('src') or player.first.get_attribute('data-play')
    assert src.endswith('/file/run-1/uploads/wall-pour.mp4'), 'the supplied file cannot be played'
    assert '1 done' in put.text('.turn.head')


@ident('R22')
def test_done_on_step_one_uses_the_kept_words(open_page, _id):
    put = open_page('refs-step1-answered')
    press_done(put, 'round-done')
    kind, text = put.bar()
    assert kind == 'ok' and 'pass 2' not in text and 'searched' not in text, f'the green line uses the older film\'s words: "{text}"'


@ident('R23')
def test_nothing_fits_has_its_words_box(open_page, _id):
    put = open_page('refs-older-no-round-element-view')
    rail(put, 'E2').click()
    box = put.page.locator('.foot textarea:visible')
    assert box.count() == 1, 'the bottom bar has no words box beside "Nothing fits"'
    box.fill('All are factory kilns.')
    put.click('#action button[data-a="nothing-fits"]')
    put.wait_posts(1)
    assert last_of(put, 'nothing-fits')['reason'] == 'All are factory kilns.'


@ident('R24')
def test_a_refusal_and_a_failed_connection_look_different(open_page, _id):
    refused = open_page('refs-step2-all-sets-back')
    refused.answers['round-sets'] = (400, {'message': 'BRICK: its set was made again; judge the new set.'})
    answer_all(refused)
    press_done(refused)
    refused.page.wait_for_timeout(150)
    dropped = open_page('refs-step2-all-sets-back')
    answer_all(dropped)
    dropped.page.route('**/visuals/act', lambda r: r.abort() if 'round-sets' in (r.request.post_data or '') else r.fallback())
    dropped.page.locator('button[data-a="round-sets"]').first.click()
    dropped.page.wait_for_timeout(200)
    fin = dropped.page.locator('#done-confirm button[data-a="round-sets"]')
    if fin.count():
        fin.click()
        dropped.page.wait_for_timeout(200)
    a, b = refused.bar(), dropped.bar()
    assert a[0] == 'err' and b[0] == 'net', f'a refusal shows as {a}, a failed connection as {b}: the operator cannot tell them apart'
    show(refused, 'BRICK')
    assert 'not recorded' in card(refused, 'BRICK').inner_text().lower(), 'the card the refusal names does not show that nothing was recorded'
