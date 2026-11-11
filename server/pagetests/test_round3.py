"""Round 3 (11 Nov 2026), after SK's walk of the local page (videobuilder-v4/phase2/reference-page-ui-issues.md): U17 a verdict on one picture is
changed both ways until a later step used it; U19 the operator's own picture on a set's card; U18 a refusal or a failure is said beside the button
that was pressed; U14's leftover, a tab switch and the right panel. The server side is in unit/test_ui_visuals_actions_pure.py.
Elements of the test film: E1 Plinth (a thing, with a footage picture), E2 Clamp kiln (a place), P1 Mason (a person), BRICK Red brick."""
import base64
import io

from kit import answer_all, card, golden, ident, last_of, no_post, only_post, opened, panel, press_done, show, verdict

PEOPLE = "A person's reference is made from the description; an uploaded photo is not used for people."
REFUSED = 'The plan, references or generator changed since this take was prepared; prepare a current take.'


def png(size=(64, 48)):
    from PIL import Image
    out = io.BytesIO()
    Image.new('RGB', size, (120, 80, 40)).save(out, format='PNG')
    return out.getvalue()


def labels(loc):
    """The visible buttons inside a locator, by their text."""
    return [b.inner_text().strip() for b in loc.locator('button').all() if b.is_visible()]


def actions(loc):
    return sorted(b.get_attribute('data-a') for b in loc.locator('button[data-a]').all() if b.is_visible())


def near(put):
    return put.page.locator('#app .near')


def own_id(put):
    return next(r['id'] for r in put.payload['references'] if r['kind'] == 'supplied')


def under(put, button, note):
    """The note sits directly beside or under the button: in the same box, no further than a line or two away."""
    b, n = button.bounding_box(), note.bounding_box()
    return abs(n['y'] - b['y']) <= 120 and abs(n['x'] - b['x']) <= 700


def abort_act(put):
    put.page.route('**/visuals/act', lambda route: route.abort())


# ---------- U17: a verdict on one picture, both ways ----------

@ident('U17-footage')
def test_a_footage_picture_at_step_one_offers_the_opposite_verdict(open_page, _id):
    put = open_page('refs-step1-to-answer')
    show(put, 'E1')
    assert labels(card(put, 'E1').locator('[data-item="F1"]')) == ['Use this picture', 'Ignore']
    put = open_page('refs-step1-answered')   # used: Ignore is offered
    show(put, 'E1')
    pic = card(put, 'E1').locator('[data-item="F1"]')
    assert labels(pic) == ['Ignore'], f'a used footage picture offers {labels(pic)}'
    pic.get_by_text('Ignore').click()
    assert only_post(put) == {'action': 'reject', 'reference_id': 'F1'}
    put = open_page('refs-step1-footage-picture-ignored')   # ignored: it stays on its card and Use this picture is offered
    show(put, 'E1')
    pic = card(put, 'E1').locator('[data-item="F1"]')
    assert pic.count() == 1, 'an ignored footage picture left its card: it cannot be used after all'
    assert 'rejected' in pic.inner_text() and labels(pic) == ['Use this picture'], f'an ignored footage picture shows "{pic.inner_text()}"'
    pic.get_by_text('Use this picture').click()
    assert only_post(put) == {'action': 'reapprove', 'reference_id': 'F1', 'sha256': 'sha-F1'}
    assert not put.red_line() and not put.js_errors


@ident('U17-picture')
def test_a_candidate_picture_on_pictures_offers_the_opposite_verdict(open_page, _id):
    put = open_page('pictures-candidate')
    put.click('#s-pictures img[data-ref="K1"]')
    assert opened(put)['buttons'] == ['approve', 'reject']
    put = open_page('controls-pictures-approved-not-placed')   # approved: Reject is offered
    put.click('#s-pictures img[data-ref="K1"]')
    assert 'reject' in opened(put)['buttons'] and 'approve' not in opened(put)['buttons']
    put = open_page('pictures-picture-rejected')   # rejected: Approve is offered
    put.click('#s-pictures img[data-ref="K1"]')
    assert opened(put)['buttons'] == ['reapprove'], f'a rejected picture offers {opened(put)["buttons"]}'
    assert labels(put.page.locator('#panel .act')) == ['Approve']
    put.click('#panel button[data-a="reapprove"]')
    assert only_post(put) == {'action': 'reapprove', 'reference_id': 'K1', 'sha256': 'sha-K1'}


@ident('U17-saved')
def test_a_saved_picture_of_an_older_film_offers_the_opposite_verdict(open_page, _id):
    put = open_page('refs-older-no-round-element-view')
    web = next(r for r in put.payload['references'] if r['kind'] == 'web')
    show(put, web['element_id'])
    put.click(f'#s-references img[data-ref="{web["id"]}"]')
    assert opened(put)['buttons'].count('reject') == 1 and 'approve' not in opened(put)['buttons']   # approved: Reject

    def rejected(payload):
        r = next(r for r in payload['references'] if r['kind'] == 'web')
        r.update(status='rejected', rejection={'notes': 'the wrong kiln', 'quote': 'No.', 'by': 'u1', 'at': ''})
    put = open_page('refs-older-no-round-element-view', patch=rejected)
    show(put, web['element_id'])
    put.click(f'#s-references img[data-ref="{web["id"]}"]')
    assert 'reapprove' in opened(put)['buttons'] and 'reject' not in opened(put)['buttons'], f'a rejected saved picture offers {opened(put)["buttons"]}'
    put.click('#panel button[data-a="reapprove"]')
    assert only_post(put) == {'action': 'reapprove', 'reference_id': web['id'], 'sha256': web['sha256']}


@ident('U17-locked')
def test_a_picture_a_later_step_used_says_why_in_one_line(open_page, _id):
    put = open_page('refs-step2-all-sets-back')   # step 1 is done: its footage picture was used
    put.go_hash('references/E1/F1')
    line = put.page.locator('#panel [data-locked="F1"]')
    assert line.count() == 1 and 'Step 1 of the reference round is done' in line.inner_text() and 'can no longer be changed here' in line.inner_text()
    assert not [a for a in opened(put)['buttons'] if a in ('approve', 'reapprove', 'reject')], f'a used picture still offers {opened(put)["buttons"]}'
    put = open_page('controls-pictures-many')   # a rejected picture with another one in its place
    put.go_hash('pictures/IM1/K0')
    line = put.page.locator('#panel [data-locked="K0"]')
    assert line.count() == 1 and 'Another picture stands in its place' in line.inner_text()
    assert 'reapprove' not in opened(put)['buttons']
    assert not put.red_line() and not put.js_errors


@ident('U17-take')
def test_a_take_offers_the_opposite_verdict_until_its_gap_is_recorded(open_page, _id):
    put = open_page('takes-rejected')
    put.click('#s-takes tr[data-take="job-take-1"]')
    assert opened(put)['buttons'] == ['select-take'], f'a rejected take offers {opened(put)["buttons"]}'
    put.click('#panel button[data-a="select-take"]')
    assert only_post(put) == {'action': 'select-take', 'job_id': 'job-take-1'}
    put = open_page('takes-selected')
    put.click('#s-takes tr[data-take="job-take-1"]')
    assert opened(put)['buttons'] == ['reject-take'], f'a selected take offers {opened(put)["buttons"]}'
    put.click('#panel button[data-a="reject-take"]')
    assert only_post(put) == {'action': 'reject-take', 'job_id': 'job-take-1'}
    put = open_page('record-recorded', tab='takes')
    put.click('#s-takes tr[data-take="job-take-1"]')
    assert opened(put)['buttons'] == [] and 'The gap is recorded; this take can no longer be changed here.' in panel(put)


@ident('U17-answers')
def test_a_set_answer_at_step_two_is_changed_as_often_as_wanted_until_done(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    for v in ('yes', 'no', 'correct', 'yes'):
        verdict(put, 'P1', v)
        put.page.wait_for_timeout(120)
        assert last_of(put, 'set_answer')['verdict'] == v and last_of(put, 'set_answer')['element_id'] == 'P1'
        assert all(put.page.locator(f'input[name="v-P1"][value="{x}"]').is_enabled() for x in ('yes', 'no', 'correct')), 'an answer made switched the other answers off'
    assert put.page.locator('input[name="v-P1"]:checked').get_attribute('value') == 'yes'
    assert not last_of(put, 'round-sets')


# ---------- U19: the operator's own picture on a card ----------

@ident('U19-control')
def test_upload_my_own_picture_is_on_the_card_of_a_thing_or_a_place_and_not_of_a_person(open_page, _id):
    for state in ('refs-step2-all-sets-back', 'refs-step1-to-answer'):
        put = open_page(state)
        for eid in ('E2', 'BRICK') + (('E1',) if 'step1' in state else ()):
            show(put, eid)
            box = card(put, eid).locator(f'[data-own="{eid}"]')
            assert box.count() == 1, f'{state}: no upload on the card of {eid}'
            assert box.locator('input[type=file]').get_attribute('accept') == 'image/png,image/jpeg,image/webp'
            assert box.locator(f'[id="url-{eid}"]').count() == 1 and labels(box) == ['Upload my own picture']
        show(put, 'P1')
        assert card(put, 'P1').locator('[data-own], input[type=file], button[data-a="supply"]').count() == 0, f'{state}: a person\'s card offers an upload'
        assert PEOPLE in card(put, 'P1').inner_text(), f'{state}: the person\'s card does not say why there is no upload'
    put = open_page('refs-sets-being-made')   # nothing to choose between yet
    assert put.page.locator('#s-references [data-own]').count() == 0


@ident('U19-upload')
def test_an_uploaded_picture_shows_on_the_card_and_is_chosen_as_the_starting_picture(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    show(put, 'E2')
    assert card(put, 'E2').locator('[data-own-pic]').count() == 0
    put.page.set_input_files('[id="up-E2"]', {'name': 'my-kiln.png', 'mimeType': 'image/png', 'buffer': png()})
    put.serve('refs-step2-own-picture')   # what the server holds once it is saved
    card(put, 'E2').locator('button[data-a="supply"]').click()
    sent = only_post(put)
    assert {k: sent[k] for k in ('action', 'element_id', 'name')} == {'action': 'supply', 'element_id': 'E2', 'name': 'my-kiln.png'} and base64.b64decode(sent['content_base64']) == png()
    put.page.wait_for_timeout(150)
    mine = card(put, 'E2').locator('[data-own-pic="E2"]')
    assert mine.count() == 1 and 'your picture' in mine.inner_text(), 'the uploaded picture is not on its card, labelled'
    assert put.bar()[0] == 'ok' and near(put).count() == 0
    mine.locator('[data-golden]').click()   # chosen like any picture of the set
    put.page.wait_for_timeout(150)
    assert last_of(put, 'set_answer')['golden'] == own_id(put)
    assert mine.locator('[data-golden]').get_attribute('aria-pressed') == 'true'
    verdict(put, 'E2', 'yes')
    put.page.wait_for_timeout(150)
    a = last_of(put, 'set_answer')
    assert (a['element_id'], a['verdict'], a['golden']) == ('E2', 'yes', own_id(put))
    assert 'not recorded yet' in card(put, 'E2').inner_text() and 'choose the starting picture' not in card(put, 'E2').inner_text()
    press_done(put)
    assert last_of(put, 'round-sets')['verdicts'] == {'E2': {'verdict': 'yes', 'words': '', 'golden': own_id(put)}}
    assert not put.js_errors


@ident('U19-link')
def test_an_own_picture_is_also_given_as_a_link(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    show(put, 'E2')
    put.page.fill('[id="url-E2"]', 'https://example.org/kiln.jpg')
    card(put, 'E2').locator('button[data-a="supply"]').click()
    assert only_post(put) == {'action': 'supply', 'element_id': 'E2', 'url': 'https://example.org/kiln.jpg'}


@ident('U19-refused-here')
def test_a_file_too_large_or_not_a_picture_is_refused_before_anything_is_sent(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    show(put, 'E2')
    button = card(put, 'E2').locator('button[data-a="supply"]')
    for file, words in (({'name': 'huge.png', 'mimeType': 'image/png', 'buffer': b'\0' * (15 * 1024 * 1024 + 1)}, 'larger than 15 MB'),
                        ({'name': 'notes.txt', 'mimeType': 'text/plain', 'buffer': b'these are words'}, 'not a PNG, JPEG or WebP picture'), (None, 'Choose a file or paste an https link first')):
        put.page.set_input_files('[id="up-E2"]', file or [])
        button.click()
        put.page.wait_for_timeout(200)
        assert words in put.red_line(), f'the bar says "{put.bar()}"'
        assert near(put).count() == 1 and words in near(put).inner_text() and card(put, 'E2').locator('.near').count() == 1, 'the refusal is not beside the upload'
    no_post(put, ' for a file the page can tell is wrong')
    assert card(put, 'E2').locator('[data-own-pic]').count() == 0


@ident('U19-refused')
def test_a_refused_or_broken_upload_shows_nothing_as_saved(open_page, _id):
    put = open_page('refs-step2-all-sets-back', answers={'supply': (422, {'code': 'VISUALS_CONTRACT', 'message': 'That file is not a picture this page can read: use a PNG, JPEG or WebP image.'})})
    show(put, 'E2')
    put.page.set_input_files('[id="up-E2"]', {'name': 'broken.png', 'mimeType': 'image/png', 'buffer': b'not really a picture'})
    card(put, 'E2').locator('button[data-a="supply"]').click()
    only_post(put)
    put.page.wait_for_timeout(150)
    assert 'not a picture this page can read' in put.red_line() and 'not a picture this page can read' in card(put, 'E2').locator('.near').inner_text()
    assert card(put, 'E2').locator('[data-own-pic]').count() == 0 and 'saved' not in card(put, 'E2').inner_text()
    put = open_page('refs-step2-all-sets-back')   # the upload fails midway: the connection drops
    show(put, 'E2')
    abort_act(put)
    put.page.set_input_files('[id="up-E2"]', {'name': 'my-kiln.png', 'mimeType': 'image/png', 'buffer': png()})
    card(put, 'E2').locator('button[data-a="supply"]').click()
    put.page.wait_for_timeout(300)
    assert put.bar()[0] == 'net' and 'nothing was recorded' in put.bar()[1]
    note = card(put, 'E2').locator('.near')
    assert note.count() == 1 and 'net' in note.get_attribute('class') and 'nothing was recorded' in note.inner_text()
    assert card(put, 'E2').locator('[data-own-pic]').count() == 0 and 'saved' not in card(put, 'E2').inner_text()
    assert card(put, 'E2').locator('button[data-a="supply"]').is_enabled()


@ident('U19-kept')
def test_own_pictures_stay_on_the_card_and_are_removed_and_used_again(open_page, _id):
    put = open_page('refs-step1-own-picture')   # uploaded at step 1: shown, kept for step 2
    show(put, 'E2')
    mine = card(put, 'E2').locator('[data-own-pic="E2"]')
    assert mine.count() == 1 and 'your picture' in mine.inner_text() and mine.locator('[data-golden]').count() == 0 and labels(mine) == ['Remove']

    def two(payload):   # uploaded twice: the later picture is added, the first stays
        first = next(r for r in payload['references'] if r['kind'] == 'supplied')
        payload['references'].append({**first, 'id': 'second-own-picture', 'name': 'my-kiln-2.png', 'status': 'rejected'})
    put = open_page('refs-step2-own-picture', patch=two)
    show(put, 'E2')
    mine = card(put, 'E2').locator('[data-own-pic="E2"]')
    assert mine.count() == 2
    kept, removed = mine.nth(0) if 'approved' in mine.nth(0).inner_text() else mine.nth(1), put.page.locator('[data-item="second-own-picture"]')
    assert labels(kept) == ['Use this as the starting picture', 'Remove'] and labels(removed) == ['Use it again'], f'{labels(kept)} / {labels(removed)}'
    removed.get_by_text('Use it again').click()
    assert only_post(put)['action'] == 'reapprove' and put.posts[-1]['reference_id'] == 'second-own-picture'
    kept.get_by_text('Remove').click()
    assert only_post(put, 2) == {'action': 'reject', 'reference_id': own_id(put)}
    assert not put.js_errors


# ---------- U18: a refusal or a failure is said where the operator is looking ----------

@ident('U18-refused')
def test_a_refused_action_is_said_beside_the_button_that_was_pressed(open_page, _id):
    put = open_page('takes-ready-to-select', answers={'select-take': (422, {'code': 'VISUALS_CONTRACT', 'message': REFUSED})})
    button = put.page.locator('#panel button[data-a="select-take"]')
    button.click()
    only_post(put)
    put.page.wait_for_timeout(150)
    note = put.page.locator('#panel .near')
    assert note.count() == 1, 'a refused Select says nothing near the button: it looks like a dead click'
    assert note.inner_text().strip() == put.red_line() == REFUSED   # the same plain text as the bar's, which keeps its line
    assert under(put, button, note) and button.is_enabled() and 'busy' not in (button.get_attribute('class') or '')
    put.answers['select-take'] = (200, {'job_id': 'job-take-1', 'next': 'Take selected: in the film at 0:36 (VS1).'})   # the next action: the note goes
    button.click()
    put.wait_posts(2)
    put.page.wait_for_timeout(150)
    assert near(put).count() == 0 and put.bar()[0] == 'ok'


@ident('U18-card')
def test_a_refusal_lands_in_the_card_of_the_button_and_in_the_foot_for_done(open_page, _id):
    put = open_page('refs-step2-spec-approved-after-refusal', answers={'set_make': (422, {'code': 'VISUALS_CONTRACT', 'message': 'BRICK: its set cannot be made yet: the spend cap is reached: ₹120 spent of ₹100.'})})
    show(put, 'BRICK')
    button = card(put, 'BRICK').locator('button[data-a="set-make"]')
    button.click()
    only_post(put)
    put.page.wait_for_timeout(150)
    note = card(put, 'BRICK').locator('.near')
    assert note.count() == 1 and near(put).count() == 1, 'the refusal is not inside the card of the button pressed'
    assert note.inner_text().strip() == put.red_line() and 'Red brick' in note.inner_text() and under(put, button, note)
    put = open_page('refs-step2-all-sets-back', answers={'round-sets': (422, {'code': 'VISUALS_CONTRACT', 'message': 'E2: say what to correct.'})})
    answer_all(put)
    press_done(put)
    put.page.wait_for_timeout(200)
    note = put.page.locator('.foot .near')
    assert note.count() == 1 and note.inner_text().strip() == put.red_line(), 'a refused Done says nothing at the foot, where its button is'


@ident('U18-net')
def test_a_failed_connection_is_said_beside_the_button_too(open_page, _id):
    put = open_page('takes-ready-to-select')
    abort_act(put)
    button = put.page.locator('#panel button[data-a="reject-take"]')
    button.click()
    put.page.wait_for_timeout(300)
    note = put.page.locator('#panel .near')
    assert note.count() == 1 and 'net' in note.get_attribute('class') and note.inner_text().strip() == put.bar()[1] and put.bar()[0] == 'net'
    assert under(put, button, note) and button.is_enabled()


@ident('U18-ok')
def test_a_successful_action_leaves_no_note(open_page, _id):
    put = open_page('takes-ready-to-select')
    put.click('#panel button[data-a="select-take"]')
    only_post(put)
    put.page.wait_for_timeout(150)
    assert near(put).count() == 0 and put.page.locator('#app button.busy').count() == 0 and not put.red_line()
    put = open_page('pictures-candidate')
    put.click('#s-pictures img[data-ref="K1"]')
    put.click('#panel button[data-a="approve"]')
    only_post(put)
    put.page.wait_for_timeout(150)
    assert near(put).count() == 0 and put.page.locator('#app .saving').count() == 0


@ident('U18-busy')
def test_the_button_shows_it_is_working_while_its_request_runs(open_page, _id):
    put = open_page('takes-ready-to-select')
    held = []
    put.page.route('**/visuals/act', lambda route: held.append(route))   # the answer is held back
    button = put.page.locator('#panel button[data-a="select-take"]')
    button.click()
    for _ in range(40):
        if held:
            break
        put.page.wait_for_timeout(25)
    assert held, 'the press sent nothing'
    assert button.is_disabled() and 'busy' in (button.get_attribute('class') or ''), 'the button does not show that it is working while its request runs'
    assert put.page.evaluate("getComputedStyle(document.querySelector('#panel button[data-a=\"select-take\"]'), '::after').content").strip('"').strip() == '…'
    held[0].fallback()   # the answer arrives
    put.wait_posts(1)
    put.page.wait_for_timeout(150)
    assert put.page.locator('#app button.busy').count() == 0 and len(put.posts) == 1


# ---------- U14, leftover: the right panel never shows another tab's picture ----------

@ident('U14-tabs')
def test_a_tab_switch_closes_the_panel_or_shows_an_item_of_the_new_tab(open_page, _id):
    put = open_page('controls-takes-two-takes', tab='references')
    refs = {r['id']: r for r in put.payload['references']}
    shots = {s['shot_id']: s['route'] for g in put.payload['gaps'] for s in g['shots']}
    takes = {k['job_id'] for g in put.payload['gaps'] for s in g['shots'] for k in s['takes']}
    put.page.locator('#s-references img[data-ref]').first.click()
    first = opened(put)['pictures']
    assert first and refs[first[0]]['kind'] in ('frame', 'sheet', 'supplied', 'web'), 'no reference picture opened on References'
    assert put.page.evaluate('location.hash').startswith('#references')

    def of_tab(tab, now):
        """Every picture and take in the panel belongs to this tab."""
        if tab == 'references':
            return all(not refs[i].get('shot_id') for i in now['pictures']) and not now['take']
        video = lambda i: shots.get(refs[i].get('shot_id')) in ('video', 'drawn')
        return tab in ('pictures', 'takes') and all(refs[i].get('shot_id') and video(i) == (tab == 'takes') for i in now['pictures'])
    for tab in ('takes', 'pictures', 'record', 'plan', 'treatment', 'references', 'takes'):
        put.open_tab(tab)
        put.page.wait_for_timeout(80)
        now = opened(put)
        assert not put.visible('#panel') or of_tab(tab, now), f'{tab}: the right panel shows another tab\'s item: {now}'
        assert not (set(now['pictures']) & set(first)) or tab == 'references', f'{tab}: the picture opened on References is still in the panel'
        h = put.page.evaluate('location.hash')
        assert h == '#' + tab or h.startswith('#' + tab + '/'), f'{tab}: the address says {h}'
    put.click('#s-takes tr[data-take]')   # and the other way: a take opened on Takes
    assert put.visible('#panel video') or put.visible('#panel')
    put.open_tab('references')
    now = opened(put)
    assert not now['take'] and (not put.visible('#panel') or of_tab('references', now)), f'references: the panel still shows the take: {now}'
    assert put.page.evaluate('location.hash').startswith('#references') and not put.js_errors and takes
