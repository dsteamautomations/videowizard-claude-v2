"""Layer 1, one test per control: the References tab. A round open on a kept film (page-facts 3.5, the case SK used), a round open on an
older film (3.6), and no round open (3.7)."""
from kit import REV, card, ident, kind_of, no_post, only_post, panel, rail, round_of, set_of, show, to_judge, verdict


def unfold(put):
    """Open the fold that holds the search results, when they are folded away."""
    for d in put.page.locator('#s-references details', has_text='show all').all():
        if d.get_attribute('open') is None:
            d.locator('summary').first.click()


def ticked(open_page, state, ns=(1,)):
    """An older film: the results of E2 on screen, some ticked."""
    put = open_page(state)
    show(put, 'E2')
    sid = put.page.locator('#s-references [data-tick]').first.get_attribute('data-tick').split(':')[0]
    for n in ns:
        unfold(put)
        put.click(f'#s-references [data-tick="{sid}:{n}"]')
    unfold(put)
    return put, sid


# ---------- 3.5 a round open on a kept film ----------

@ident('C-3.5-58')
def test_step1_radios(open_page, _id):
    put = open_page('refs-step1-to-answer')
    labels = {}
    for eid in round_of(put):
        show(put, eid)
        r = card(put, eid).locator(f'input[name="v-{eid}"]')
        assert r.count() == 2 and r.first.is_checked() and r.first.get_attribute('value') == 'approve' and r.nth(1).get_attribute('value') == 'ignore'
        labels[eid] = [t.strip() for t in card(put, eid).locator('label').all_inner_texts()]
    assert labels['E1'] == ['Use the footage picture' + ('' if REV else ' (no AI picture is made)'), 'Ignore this']   # the live version's shorter wording
    assert labels['E2'] == ['Make its pictures', 'Ignore this'] and labels['P1'] == ['Make the character sheet', 'Ignore this']
    verdict(put, 'P1', 'ignore')
    put.click('#action button[data-a="round-done"]')
    put.click('#action button[data-a="round-done"]')
    assert only_post(put)['verdicts'] == {'BRICK': {'verdict': 'approve'}, 'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'approve'}, 'P1': {'verdict': 'ignore'}}
    assert open_page('refs-step2-all-sets-back').page.locator('input[value="approve"], input[value="ignore"]').count() == 0, 'step 2 still shows the radios of step 1'


@ident('C-3.5-59')
def test_footage_thumbnail(open_page, _id):
    put = open_page('refs-step1-to-answer')
    show(put, 'E1')
    assert not put.visible('#panel')
    card(put, 'E1').locator('img[data-ref="F1"]').click()
    assert put.page.locator('#panel img[data-view="F1"]').count() == 1
    assert card(put, 'E2').locator('img[data-ref]').count() == 0 and 'Not in your footage' in card(put, 'E2').inner_text()


@ident('C-3.5-60')
def test_step1_done(open_page, _id):
    put = open_page('refs-step1-to-answer')
    b = put.page.locator('#action button[data-a="round-done"]')
    assert b.inner_text() == 'Done (4 elements)' and b.is_enabled()
    b.click()
    no_post(put, ' by the first press of Done: it asks first')
    assert put.text('#action span') == 'Done with 4 elements?'
    assert put.page.locator('#action button').all_inner_texts() == ['Back', 'Finish']
    put.click('#action button[data-a="round-picks-back"]')
    assert put.page.locator('#action button').all_inner_texts() == ['Done (4 elements)']
    put.click('#action button[data-a="round-done"]')
    put.click('#action button[data-a="round-done"]')
    assert only_post(put) == {'action': 'round-done', 'verdicts': {e: {'verdict': 'approve'} for e in round_of(put)}, 'quote': ''}


@ident('C-3.5-61')
def test_making_has_no_control(open_page, _id):
    put = open_page('refs-sets-being-made', clock=True)
    assert put.page.locator('#s-references input, #s-references button, #s-references textarea, #s-references [data-golden]').count() == 0
    assert put.page.locator('#action button').count() == 0 and put.text('#tray') == 'The pictures are being made; nothing to do yet.'
    assert 'being made' in put.section_text()
    n = put.data_gets
    put.page.clock.fast_forward(15500)
    put.page.wait_for_timeout(250)
    assert put.data_gets == n + 1, 'the page does not refresh itself while the sets are made'


@ident('C-3.5-62')
def test_golden_tick(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    for eid in to_judge(put):
        show(put, eid)
        assert card(put, eid).locator('[data-golden]').count() == (0 if kind_of(put, eid) == 'person' else len(set_of(put, eid))), f'{eid}: the ticks do not match its pictures'
    show(put, 'BRICK')
    ticks = card(put, 'BRICK').locator('[data-golden]')
    on = lambda: [t.get_attribute('data-golden').split(':')[1] for t in card(put, 'BRICK').locator('[data-golden].on').all()]
    pics = set_of(put, 'BRICK')
    ticks.nth(1).click()   # R2 (the UI change of 11 Nov 2026): a labelled control, not a bare tick showing a star
    chosen = card(put, 'BRICK').locator('[data-golden].on')
    assert on() == [pics[1]] and chosen.inner_text() == 'Use this as the starting picture' and chosen.get_attribute('aria-pressed') == 'true'
    ticks.nth(2).click()
    assert on() == [pics[2]], 'a second tick did not replace the first'
    ticks.nth(2).click()
    assert on() == []
    put.wait_posts(3)   # R13: every change is stored as it is made (before: nothing was sent until Done)
    assert [(b['action'], b['element_id'], b['verdict'], b['golden']) for b in put.posts] == [('set_answer', 'BRICK', None, pics[1]), ('set_answer', 'BRICK', None, pics[2]), ('set_answer', 'BRICK', None, None)]


@ident('C-3.5-63')
def test_set_thumbnail(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    show(put, 'E2')
    rid = set_of(put, 'E2')[1]
    card(put, 'E2').locator(f'img[data-ref="{rid}"]').click()
    assert put.page.locator(f'#panel img[data-view="{rid}"]').count() == 1
    assert 'sel' in card(put, 'E2').locator(f'.pic[data-item="{rid}"]').get_attribute('class')


@ident('C-3.5-64')
def test_yes_no_correct_radios(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    for eid in to_judge(put):
        show(put, eid)
        r = card(put, eid).locator(f'input[name="v-{eid}"]')
        assert [x.get_attribute('value') for x in r.all()] == ['yes', 'no', 'correct'] and not any(x.is_checked() for x in r.all()) and all(x.is_enabled() for x in r.all())
    for v in ('yes', 'no', 'correct'):
        verdict(put, 'E2', v)
        assert put.page.locator('input[name="v-E2"]:checked').get_attribute('value') == v
    put.wait_posts(3)   # R13 (the UI change of 11 Nov 2026): each answer is stored as it is made (before: nothing was sent until Done)
    assert [(b['action'], b['element_id'], b['verdict']) for b in put.posts] == [('set_answer', 'E2', 'yes'), ('set_answer', 'E2', 'no'), ('set_answer', 'E2', 'correct')]
    empty = open_page('refs-step2-some-sets-not-made')
    show(empty, 'BRICK')   # R17: a set that was not made is not answered with No to get it made (retired): it has no Yes / No / Correct it, it offers Make it now
    assert card(empty, 'BRICK').locator('input[type=radio]').count() == 0 and card(empty, 'BRICK').locator('button[data-a="set-make"][data-el="BRICK"]').count() == 1


@ident('C-3.5-65')
def test_correction_words(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    verdict(put, 'P1', 'correct')
    assert 'Mason' in put.text('#tray span.err').split(':')[-1]   # follow-up fix 5: the name, not the id
    put.page.locator('[id="w-P1"]').press_sequentially('older, about fifty')
    assert 'P1' not in put.text('#tray span.err').split(':')[-1], 'the words for Correct it were typed and the card is still named as unanswered'
    verdict(put, 'E2', 'no')   # a redraw keeps the words
    show(put, 'P1')
    assert put.page.input_value('[id="w-P1"]') == 'older, about fifty'


@ident('C-3.5-66')
def test_notes_and_sources_fold(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    show(put, 'E2')
    d = card(put, 'E2').locator('details')
    assert d.locator('summary').inner_text() == "the model's notes and sources" and d.get_attribute('open') is None
    d.locator('summary').click()
    a = d.locator('a')
    assert '(1) one method chosen' in d.inner_text() and (a.get_attribute('href'), a.get_attribute('target')) == ('https://example.org/kiln', '_blank')


@ident('C-3.5-67')
def test_from_your_footage_card(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    foot = [e for e, r in round_of(put).items() if r.get('from_footage')]
    if not foot:   # the live version: a thing with an approved footage picture still gets a set, so no such card exists
        assert 'from your footage' not in put.section_text().lower()
        return
    show(put, 'E1')
    c = card(put, 'E1')
    assert c.locator('.badge').inner_text().lower() == 'from your footage' and c.locator('input, textarea, [data-golden]').count() == 0
    c.locator('img[data-ref="F1"]').click()
    assert put.page.locator('#panel img[data-view="F1"]').count() == 1
    making = open_page('refs-sets-being-made')
    assert 'FROM YOUR FOOTAGE' in making.section_text().upper()


@ident('C-3.5-68')
def test_step2_done(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    done = put.page.locator('#action button[data-a="round-sets"]')
    assert done.is_enabled() and 'need an answer' in put.text('#tray span.err')   # R15 (the UI change of 11 Nov 2026): Done is not locked by an unanswered card; its confirmation counts them (before: disabled until every card had its answer)
    want = {}
    for eid in to_judge(put):
        if eid == 'BRICK':
            show(put, eid)
            card(put, eid).locator('[data-golden]').first.click()
            verdict(put, eid, 'yes')
            want[eid] = {'verdict': 'yes', 'words': '', 'golden': set_of(put, eid)[0]}
        elif eid == 'P1':
            verdict(put, eid, 'correct', 'older, about fifty')
            want[eid] = {'verdict': 'correct', 'words': 'older, about fifty', 'golden': ''}
        else:
            verdict(put, eid, 'no')
            want[eid] = {'verdict': 'no', 'words': '', 'golden': ''}
    assert done.is_enabled() and put.page.locator('#tray span.err').count() == 0, f'a card is still named as unanswered though every card is answered: {put.text("#tray")}'
    put.page.fill('#words', 'Pass one.')
    done.click()   # R15: the first press asks, with the counts, and records nothing (before: one click recorded the round)
    put.page.wait_for_timeout(150)
    assert not [b for b in put.posts if b['action'] == 'round-sets'] and '1 approved · 2 made again (paid) · 0 unanswered' in put.text('#done-confirm')
    put.click('#done-confirm button[data-a="round-sets"]')
    put.wait_posts(len(put.posts) + 1)
    assert put.posts[-1] == {'action': 'round-sets', 'verdicts': want, 'quote': 'Pass one.'}


# ---------- 3.6 a round open on an older film ----------

@ident('C-3.6-69')
def test_older_pass1_radios(open_page, _id):
    put = open_page('refs-older-pass1')
    show(put, 'E1')
    assert [x.get_attribute('value') for x in card(put, 'E1').locator('input[name="v-E1"]').all()] == ['approve', 'search', 'ignore']
    assert put.page.locator('input[name="v-E1"]:checked').get_attribute('value') == 'approve' and put.page.locator('[id="kw-E1"]').count() == 0
    verdict(put, 'E1', 'search')
    assert put.visible('[id="kw-E1"]') and 'Plinth' in put.text('#tray span.err'), 'Search Google did not open the search words, or Done is not locked until it is searched'
    show(put, 'E2')
    assert [x.get_attribute('value') for x in card(put, 'E2').locator('input[name="v-E2"]').all()] == ['search', 'ignore']
    no_post(put)


@ident('C-3.6-70')
def test_older_search(open_page, _id):
    put = open_page('refs-older-pass1')
    show(put, 'E2')
    put.page.fill('[id="kw-E2"]', 'kiln')
    put.click('button[data-a="round-search"][data-el="E2"]')
    assert put.red_line() == 'Two to twelve words to search for: the thing and its place or trade.'
    no_post(put)
    put.page.fill('[id="kw-E2"]', 'clamp kiln south India')
    put.page.fill('[id="src-E2"]', 'pexels')
    put.click('button[data-a="round-search"][data-el="E2"]')
    assert only_post(put) == {'action': 'search', 'element_id': 'E2', 'keywords': 'clamp kiln south India', 'source': 'pexels'}
    two = open_page('refs-older-pass2')
    show(two, 'E2')
    assert two.page.locator('button[data-a="round-search"][data-el="E2"]').count() == 1


@ident('C-3.6-71')
def test_result_tick(open_page, _id):
    put, sid = ticked(open_page, 'refs-older-pass1', ())
    put.click(f'[data-tick="{sid}:2"]')
    put.click(f'[data-tick="{sid}:1"]')
    assert put.page.locator(f'[data-tick="{sid}:2"]').inner_text() == '1' and put.page.locator(f'[data-tick="{sid}:1"]').inner_text() == '2'
    assert put.page.locator(f'.pic[data-lb="{sid}:2"] .badge').inner_text().lower() == 'ticked · not saved'
    put.click(f'[data-tick="{sid}:2"]')
    assert put.page.locator(f'[data-tick="{sid}:1"]').inner_text() == '1' and not put.visible('#panel')
    no_post(put)


@ident('C-3.6-72')
def test_result_thumbnail(open_page, _id):
    put, sid = ticked(open_page, 'refs-older-pass1', ())
    put.click(f'.pic[data-lb="{sid}:3"] img')
    assert 'E2 · 3 of 3 · site.example · 800×600' in panel(put) and put.page.get_attribute('#panel img[data-sview]', 'src') == 'https://img.example/3.jpg'


@ident('C-3.6-73')
def test_note_under_a_ticked_result(open_page, _id):
    put, sid = ticked(open_page, 'refs-older-pass1', ())
    assert put.page.locator('input[data-gnote]').count() == 0
    put.click(f'[data-tick="{sid}:1"]')
    put.page.locator(f'input[data-gnote="{sid}:1"]').press_sequentially('keep the chimney')
    put.click(f'.pic[data-lb="{sid}:1"] img')
    assert put.page.input_value('#p-note') == 'keep the chimney', 'the note typed under the picture is not the note in the panel'


@ident('C-3.6-74')
def test_add_your_own_picture_opens_the_box(open_page, _id):
    put = open_page('controls-older-search-found-nothing')
    show(put, 'E2')
    assert 'No picture came back for these words.' in card(put, 'E2').inner_text()
    card(put, 'E2').locator('button[data-a="supply-open"]').first.click()
    assert 'E2 · the search found no picture' in panel(put) and put.page.locator('#panel button[data-a="supply"][data-el="E2"]').count() == 1
    no_post(put)


@ident('C-3.6-75')
def test_ignore_and_undo_ignore(open_page, _id):
    put = open_page('refs-older-pass2')
    show(put, 'E2')
    b = lambda: card(put, 'E2').locator('button[data-a="ignore"]')
    assert b().inner_text() == 'Ignore this' and 'Clamp kiln' in put.text('#tray span.err')   # follow-up fix 5: the name, not the id
    b().click()
    assert b().inner_text() == 'Undo Ignore' and card(put, 'E2').locator('.badge').inner_text().lower() == 'ignored' and put.page.locator('#tray span.err').count() == 0
    b().click()
    assert b().inner_text() == 'Ignore this'
    no_post(put)


@ident('C-3.6-76')
def test_tick_chips(open_page, _id):
    put, sid = ticked(open_page, 'refs-older-pass2', (2, 3))
    chips = put.page.locator('#tray .fchip')
    assert [' '.join(c.split()) for c in chips.all_inner_texts()] == ['Image 1 · E2 · 2 ✕', 'Image 2 · E2 · 3 ✕']
    chips.nth(1).click(position={'x': 8, 'y': 8})
    assert '3 of 3' in panel(put)
    put.click(f'#tray [data-untick="{sid}:2"]')
    assert [' '.join(c.split()) for c in put.page.locator('#tray .fchip').all_inner_texts()] == ['Image 1 · E2 · 3 ✕']
    no_post(put)


@ident('C-3.6-77')
def test_older_pass2_done(open_page, _id):
    put = open_page('refs-older-pass2')
    assert put.page.is_disabled('#action button[data-a="round-picks"]')
    show(put, 'E2')
    sid = put.page.locator('#s-references [data-tick]').first.get_attribute('data-tick').split(':')[0]
    put.click(f'[data-tick="{sid}:1"]')
    put.page.locator(f'input[data-gnote="{sid}:1"]').press_sequentially('colour only')
    put.page.fill('#words', 'This one.')
    put.click('#action button[data-a="round-picks"]')
    no_post(put, ' by the first press of Done: it asks first')
    assert put.text('#action span') == '1 picture ticked, 1 note: finish pass 2?'
    put.click('#action button[data-a="round-picks"]')
    assert only_post(put) == {'action': 'round-picks', 'picks': {s: ([{'n': 1, 'note': 'colour only'}] if s == sid else []) for s in round_of(put)['E2']['search_ids']},
                              'ignore': [], 'quote': 'This one.'}


@ident('C-3.6-78')
def test_undo_done_back_to_pass1(open_page, _id):
    put = open_page('refs-older-pass2')
    b = put.page.locator('#action button[data-a="round-undo"]')
    assert b.inner_text() == 'Undo Done (back to pass 1)'
    b.click()
    assert only_post(put) == {'action': 'round-undo', 'quote': ''}
    assert open_page('refs-older-pass1').page.locator('button[data-a="round-undo"]').count() == 0


# ---------- 3.7 no round open: one element at a time ----------

@ident('C-3.7-79a')
def test_element_list_is_hidden(open_page, _id):
    put = open_page('refs-no-round-kept')
    a = put.page.locator('#s-references .list a')
    assert a.count() == len(put.payload['elements']) and not a.first.is_visible(), 'the old element list is in the page and must stay hidden: the left list replaces it'


@ident('C-3.7-80')
def test_undo_done_reopen(open_page, _id):
    put = open_page('refs-round-complete')
    b = put.page.locator('#s-references button[data-a="round-undo"]')
    assert b.inner_text() == 'Undo Done (reopen pass 2)'
    b.click()
    assert only_post(put) == {'action': 'round-undo', 'quote': ''}
    assert open_page('refs-no-round-kept').page.locator('button[data-a="round-undo"]').count() == 0, 'Undo Done is offered before any round'


@ident('C-3.7-81')
def test_approve_the_material_spec(open_page, _id):
    put = open_page('refs-no-round-kept')
    rail(put, 'BRICK').click()
    box = put.page.locator('[id="card-mspec-BRICK"]')
    assert box.locator('.badge').inner_text().lower() == 'to approve' and box.locator('table tr').count() == 7   # the heading, the four sizes, laid, pattern
    box.locator('button[data-a="approve-spec"]').click()
    assert only_post(put) == {'action': 'approve-spec', 'shot_id': 'element:BRICK', 'quote': ''}
    done = open_page('refs-round-complete')
    rail(done, 'BRICK').click()
    assert done.page.locator('[id="card-mspec-BRICK"] .badge').inner_text().lower() == 'approved' and done.page.locator('[id="card-mspec-BRICK"] button').count() == 0


@ident('C-3.7-82')
def test_correct_the_material_spec(open_page, _id):
    put = open_page('refs-no-round-kept')
    rail(put, 'BRICK').click()
    put.click('[id="card-mspec-BRICK"] button[data-a="correct-spec"]')
    assert put.red_line() == 'Say which value is wrong and what it should be.'
    no_post(put)
    put.page.fill('[id="sp-c-element:BRICK"]', 'the joint is 12 mm')
    put.click('[id="card-mspec-BRICK"] button[data-a="correct-spec"]')
    assert only_post(put) == {'action': 'correct-spec', 'shot_id': 'element:BRICK', 'words': 'the joint is 12 mm'}


@ident('C-3.7-83')
def test_element_view_thumbnails(open_page, _id):
    put = open_page('refs-round-complete')
    rail(put, 'E2').click()
    pics = put.page.locator('#s-references .strip .pic[data-item]')
    assert pics.count() == 2 and all('approved' in t.lower() for t in pics.all_inner_texts())
    rid = pics.nth(1).get_attribute('data-item')
    pics.nth(1).locator('img').click()
    assert put.page.locator(f'#panel img[data-view="{rid}"]').count() == 1


@ident('C-3.7-84')
def test_element_view_search(open_page, _id):
    put = open_page('refs-older-no-round-element-view')
    rail(put, 'E2').click()
    b = put.page.locator('#s-references button[data-a="search"][data-el="E2"]')
    assert b.inner_text() == 'Search again' and put.page.input_value('[id="kw-E2"]') == 'clamp kiln Tamil Nadu'
    put.page.fill('[id="kw-E2"]', 'country brick kiln firing')
    put.page.fill('[id="src-E2"]', '')
    b.click()
    assert only_post(put) == {'action': 'search', 'element_id': 'E2', 'keywords': 'country brick kiln firing', 'source': ''}
    assert open_page('refs-no-round-kept').page.locator('button[data-a="search"]').count() == 0, 'a new film offers the search box'


@ident('C-3.7-85')
def test_element_view_folds(open_page, _id):
    put = open_page('refs-older-no-round-element-view')
    rail(put, 'E2').click()
    d = put.page.locator('#s-references details', has_text='show all (3 search results)')
    assert d.get_attribute('open') is None
    d.locator('summary').first.click()
    assert d.locator('.pic[data-lb]').count() == 3 and d.locator('.pic[data-lb]').first.is_visible()
    d.locator('[data-tick]').first.click()
    d = put.page.locator('#s-references details', has_text='show all (3 search results)')
    assert d.get_attribute('open') is not None, 'ticking a picture inside the fold closes the fold: the next picture cannot be ticked without opening it again'


@ident('C-3.7-86')
def test_save_n_pictures(open_page, _id):
    put, sid = ticked(open_page, 'refs-older-no-round-element-view', (2, 3))
    b = put.page.locator('#action button[data-a="pick"]')
    assert b.inner_text() == 'Save 2 pictures'
    b.click()
    assert only_post(put) == {'action': 'pick', 'search_id': sid, 'picks': [{'n': 2, 'note': ''}, {'n': 3, 'note': ''}]}


@ident('C-3.7-87')
def test_clear_the_ticks(open_page, _id):
    put, sid = ticked(open_page, 'refs-older-no-round-element-view', (2, 3))
    put.click('#action button[data-a="clear-ticks"]')
    assert put.page.locator('#s-references .tick.on').count() == 0 and put.page.locator('#action button[data-a="pick"]').count() == 0
    no_post(put)


@ident('C-3.7-88')
def test_nothing_fits(open_page, _id):
    put = open_page('refs-older-no-round-element-view')
    rail(put, 'E2').click()
    sid = max((s for s in put.payload['searches'] if s['element_id'] == 'E2'), key=lambda s: s['at'])['search_id']
    assert put.page.locator('#action button[data-a="nothing-fits"]').count() == 1
    box = put.page.locator('#words:visible, #pwords:visible')
    assert box.count() == 1, 'Nothing fits needs the operator\'s words, and this view has no words box to type them in'
    box.fill('All are factory kilns.')
    put.click('#action button[data-a="nothing-fits"]')
    assert only_post(put) == {'action': 'nothing-fits', 'search_id': sid, 'reason': 'All are factory kilns.'}
