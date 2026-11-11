"""Layer 3: the journeys. The reference round as the operator walked it on VW-19, one test per pass, and the Takes tab with a shot filled
by a supplied file. After each action the harness answers as the server would, with the payload of the next state (put.serve), so the
page is seen moving from one state to the next. The walk is written to the approved requirements (CONTRACT.md for the new names)."""
import re

from kit import card, clean, counts_wrong, golden, ident, kind_of, last_of, next_waiting_wrong, press_done, rail, round_of, set_of, show, stored, to_judge, verdict


def supplied(payload):
    payload['gaps'][1]['shots'][0]['asset'].update(by='SK', quote='My own shot of the pour.')


@ident('J1')
def test_step_one_answer_the_pictures_approve_the_specs_done(open_page, _id):
    put = open_page('refs-step1-to-answer')
    assert put.header_count() == 2 and not counts_wrong(put), f'two things wait (a footage picture, a material spec): {counts_wrong(open_page("refs-step1-to-answer"))}'
    put.open_tab('references')
    show(put, 'E1')   # the footage picture, answered in the centre
    card(put, 'E1').get_by_text('Use this picture', exact=True).click()
    put.wait_posts(1)
    assert last_of(put, 'approve') == {'action': 'approve', 'reference_id': 'F1', 'sha256': 'sha-F1'}
    put.serve('refs-step1-picture-answered-spec-waits')
    put.refresh()
    assert put.visible('#notmade') and 'Red brick' in put.text('#notmade')   # the brick's spec: its set would not be made (follow-up fix 5: by its name)
    show(put, 'BRICK')
    card(put, 'BRICK').locator('button[data-a="approve-spec"][data-shot="element:BRICK"]').click()
    put.wait_posts(2)
    assert last_of(put, 'approve-spec') == {'action': 'approve-spec', 'shot_id': 'element:BRICK', 'quote': ''}
    put.serve('refs-step1-answered')
    put.refresh()
    assert put.header_count() == 0 and not put.visible('#notmade')
    put.serve('refs-sets-being-made')
    press_done(put, 'round-done')
    assert last_of(put, 'round-done') == {'action': 'round-done', 'verdicts': {e: {'verdict': 'approve'} for e in ('BRICK', 'E1', 'E2', 'P1')}, 'quote': ''}
    assert put.bar()[0] == 'ok' and 'pass 2' not in put.bar()[1] and 'The pictures are being made.' in put.section_text()
    clean(put)


@ident('J2')
def test_the_sets_are_made_and_step_two_opens(open_page, _id):
    put = open_page('refs-sets-being-made', clock=True)
    assert put.page.locator('#s-references input, #s-references button').count() == 0 and put.header_count() == 0
    put.serve('refs-step2-all-sets-back')   # the image worker finished
    put.page.clock.fast_forward(15500)
    put.page.wait_for_timeout(300)
    assert 'Reference round, step 2 of 2' in put.section_text(), 'the page did not move to step 2 by itself'
    judged = to_judge(put)
    assert sorted(c['unit'] for c in put.cards() if c['waiting']) == sorted(judged), 'the sets to judge are not marked as waiting'
    assert put.header_count() == len(judged) == put.tab_counts()['references']
    assert not next_waiting_wrong(put)
    clean(put)


@ident('J3')
def test_step_two_judge_every_set_and_done(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    want = {}
    for eid in to_judge(put):
        if eid == 'P1':   # Correct it with words
            verdict(put, eid, 'correct', 'too young')
            put.page.locator('[id="w-P1"]').blur()
            want[eid] = {'verdict': 'correct', 'words': 'too young', 'golden': ''}
        else:   # the golden picture, then Yes
            thing = kind_of(put, eid) != 'person'
            if thing:
                golden(put, eid, 1)
            verdict(put, eid, 'yes')
            want[eid] = {'verdict': 'yes', 'words': '', 'golden': set_of(put, eid)[1] if thing else ''}
        put.page.wait_for_timeout(120)
        a = last_of(put, 'set_answer')
        assert a and a['element_id'] == eid and a['verdict'] == want[eid]['verdict'] and a['golden'] == (want[eid]['golden'] or None), f'the answer of {eid} was not stored as it was made: {a}'
        said = ' '.join(rail(put, eid).inner_text().split()).lower()
        assert 'not recorded yet' in said and rail(put, eid).locator('.wdot').count() == 0, f'the card of {eid} says "{said}"'
    put.page.fill('#words', 'Pass one.')
    put.page.locator('button[data-a="round-sets"]').first.click()
    text = put.text('#done-confirm')
    assert re.search(rf'\b{len(want) - 1} approved\b', text) and re.search(r'\b1 made again \(paid\)', text) and re.search(r'\b0 unanswered\b', text), f'the confirmation reads "{text}"'
    put.serve('refs-step2-second-pass' if 'E1' not in want else 'refs-sets-being-made')
    put.click('#done-confirm button[data-a="round-sets"]')
    put.wait_posts(len(put.posts) + 1)
    assert last_of(put, 'round-sets') == {'action': 'round-sets', 'verdicts': want, 'quote': 'Pass one.'}
    assert put.bar()[0] == 'ok'
    clean(put)


@ident('J4')
def test_a_set_that_was_not_made(open_page, _id):
    put = open_page('refs-step2-some-sets-not-made')
    show(put, 'BRICK')
    c = card(put, 'BRICK')
    text = c.inner_text()
    assert 'vw visuals' not in text and 'Say No' not in text, f'the card says: "{" ".join(text.split())[:200]}"'
    c.locator('button[data-a="approve-spec"][data-shot="element:BRICK"]').click()   # the cause, settled on the card
    put.wait_posts(1)
    assert last_of(put, 'approve-spec') == {'action': 'approve-spec', 'shot_id': 'element:BRICK', 'quote': ''}
    put.serve('refs-step2-spec-approved-after-refusal')
    put.refresh()
    show(put, 'BRICK')
    assert 'spec approved' in card(put, 'BRICK').inner_text().lower() and 'is not approved' not in card(put, 'BRICK').inner_text()
    card(put, 'BRICK').locator('button[data-a="set-make"][data-el="BRICK"]').click()
    put.wait_posts(2)
    assert last_of(put, 'set_make') == {'action': 'set_make', 'element_id': 'BRICK'}
    put.serve('refs-step2-all-sets-back')   # the set came back
    put.refresh()
    show(put, 'BRICK')
    assert card(put, 'BRICK').locator('img[data-ref]').count() == 3 and put.page.is_enabled('input[name="v-BRICK"][value="yes"]')
    clean(put)


@ident('J5')
def test_the_second_pass(open_page, _id):
    put = open_page('refs-step2-second-pass')
    again = [e for e in to_judge(put) if round_of(put)[e].get('round', 1) > 1]
    assert again == ['P1']
    for eid in to_judge(put):
        if eid not in again:
            show(put, eid)
            assert 'approved' in card(put, eid).inner_text().lower() and card(put, eid).locator('input[type=radio]').count() == 0, f'{eid} was approved in the first pass and is asked again'
    show(put, 'P1')
    assert 'round 2' in card(put, 'P1').inner_text() and card(put, 'P1').locator('img[data-ref]').count() == 3
    verdict(put, 'P1', 'yes')
    put.page.fill('#words', 'Pass two.')
    put.page.locator('button[data-a="round-sets"]').first.click()
    assert re.search(r'\b1 approved\b.*\b0 made again', put.text('#done-confirm')), f'the confirmation reads "{put.text("#done-confirm")}"'
    put.serve('refs-round-complete')
    put.click('#done-confirm button[data-a="round-sets"]')
    put.wait_posts(1)
    assert last_of(put, 'round-sets') == {'action': 'round-sets', 'verdicts': {'P1': {'verdict': 'yes', 'words': '', 'golden': ''}}, 'quote': 'Pass two.'}
    assert put.header_count() == 0 and put.page.locator('#s-references button[data-a="round-undo"]').count() == 1, 'the page does not show the round as complete'
    clean(put)


@ident('J6')
def test_the_round_complete(open_page, _id):
    put = open_page('refs-round-complete')
    assert put.header_count() == 0 and put.page.locator('#wnext').count() == 0 and not counts_wrong(put)
    put.open_tab('references')
    for c in put.cards():
        rail(put, c['unit']).click()
        assert c['badge'].lower() in ('sheet approved', 'approved', 'from your footage'), f'{c["unit"]} is shown as "{c["badge"]}" though the round is complete'
        pics = put.page.locator('#s-references .strip .pic[data-item]:visible')
        said = [' '.join(t.split()) for t in pics.all_inner_texts()]
        assert said and all('approved' in t.lower() for t in said), f'{c["unit"]}: its pictures do not all say approved: {said}'
        assert put.page.locator('#s-references input[type=radio]').count() == 0
    clean(put)


@ident('J7')
def test_takes_with_a_shot_filled_by_a_supplied_file(open_page, _id):
    put = open_page('takes-shot-filled-with-supplied-movie', patch=supplied)
    tabs = put.tab_counts()   # the supplied file fills G2's only shot, so G2 is ready to record: that is the one thing that waits (N3: a gap ready to record is counted), and nothing waits on Takes
    assert tabs['takes'] == 0 and put.header_count() == tabs['record'] == 1 and not counts_wrong(put)
    put.open_tab('takes')
    assert rail(put, 'VS1').locator('.badge').inner_text().lower() == 'done', f'the left list says "{rail(put, "VS1").locator(".badge").inner_text()}"'
    rail(put, 'VS1').click()
    c = put.page.locator('[id="card-VS1"]')
    assert 'Supplied by SK' in c.inner_text() and 'My own shot of the pour.' in c.inner_text() and 'No take yet' not in c.inner_text()
    c.locator('button[data-play]').first.click()
    assert put.visible('#player') and put.page.get_attribute('#pl', 'src').endswith('/file/run-1/uploads/wall-pour.mp4')
    put.open_tab('record')
    assert 'VS1 ✓' in put.page.locator('#s-record tr[data-unit="G2"]').inner_text()
    assert not put.posts
    clean(put)
