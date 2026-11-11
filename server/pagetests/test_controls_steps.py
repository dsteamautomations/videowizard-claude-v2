"""Layer 1, one test per control: Treatment (page-facts 3.3), Plan (3.4), Pictures (3.8), Takes (3.9), Record (3.10)."""
from kit import ident, no_post, only_post, panel, rail, show


# ---------- 3.3 Treatment ----------

@ident('C-3.3-48')
def test_correct_this(open_page, _id):
    put = open_page('controls-treatment-footage')
    rail(put, '').click()
    assert 'Your footage: cinema camera, tripod, natural look (measured from the clips)' in put.section_text()
    assert not put.visible('#ft-form')
    put.click('#ft-open')
    assert put.visible('#ft-form')
    put.click('#ft-open')
    assert not put.visible('#ft-form')
    assert open_page('treatment-draft').page.locator('#ft-open').count() == 0, 'Correct this is shown with no footage line'


@ident('C-3.3-49')
def test_save_the_footage_correction(open_page, _id):
    put = open_page('controls-treatment-footage')
    rail(put, '').click()
    put.click('#ft-open')
    put.click('button[data-a="footage"]')
    assert put.red_line() == 'Choose what to correct first.'
    put.page.select_option('#ft-camera', 'phone')
    put.click('button[data-a="footage"]')
    assert put.red_line() == 'Say in your words what the footage really is.'
    no_post(put)
    put.page.fill('#ftwords', 'Shot on a phone, all of it.')
    put.click('button[data-a="footage"]')
    assert only_post(put) == {'action': 'footage', 'camera': 'phone', 'support': None, 'look': None, 'quote': 'Shot on a phone, all of it.'}


@ident('C-3.3-50')
def test_accept_a_line(open_page, _id):
    put = open_page('treatment-draft')
    rail(put, '').click()
    assert put.page.locator('button[data-a="t-accept"]').count() == 3   # the Direction and the two gaps
    put.click('button[data-a="t-accept"][data-line="G1"]')
    assert only_post(put) == {'action': 'treatment', 'accept': ['G1'], 'quote': ''}
    assert put.bar() == ('ok', 'G1 accepted.')
    assert open_page('treatment-accepted').page.locator('button[data-a="t-accept"]').count() == 0


@ident('C-3.3-51')
def test_send_back_a_line(open_page, _id):
    put = open_page('treatment-draft')
    rail(put, '').click()
    put.click('button[data-a="t-back"][data-line="G2"]')
    assert put.red_line() == 'Say what to change in this line, then Send back.'
    no_post(put)
    put.page.fill('[id="tn-G2"]', 'Pour from a bucket, not a hose.')
    put.click('button[data-a="t-back"][data-line="G2"]')
    assert only_post(put) == {'action': 'treatment', 'send_back': ['G2'], 'notes': 'Pour from a bucket, not a hose.', 'quote': ''}


@ident('C-3.3-52')
def test_approve_the_treatment(open_page, _id):
    put = open_page('treatment-draft')
    put.click('#action button[data-a="treatment"]')
    assert put.red_line() == 'Your words are required: type them in the box at the foot first.'
    no_post(put)
    put.page.fill('#words', 'Yes, this treatment.')
    put.click('#action button[data-a="treatment"]')
    assert only_post(put) == {'action': 'treatment', 'quote': 'Yes, this treatment.'}
    done = open_page('treatment-accepted')
    assert done.page.locator('#action button').count() == 0 and done.page.locator('#words').count() == 0


# ---------- 3.4 Plan ----------

@ident('C-3.4-53')
def test_gap_tick_box(open_page, _id):
    put = open_page('plan-proposed')
    rail(put, '').click()
    assert put.page.is_disabled('#action button[data-a="accept-selected"]') and put.page.is_disabled('#action button[data-a="revise-selected"]')
    put.page.check('input[data-sel="G1"]')
    assert put.text('#tray span') == '1 gap ticked:' and put.page.is_enabled('#action button[data-a="accept-selected"]')
    put.page.uncheck('input[data-sel="G1"]')
    assert put.page.is_disabled('#action button[data-a="accept-selected"]')
    assert open_page('record-recorded', tab='plan').page.locator('input[data-sel]').count() == 0, 'a recorded gap can be ticked'


@ident('C-3.4-54')
def test_choice_buttons(open_page, _id):
    put = open_page('controls-plan-two-choices')
    rail(put, '').click()
    b = put.page.locator('button[data-a="select"]')
    assert b.all_inner_texts() == ['From the side (recommended)', 'From above']
    b.nth(1).click()
    assert only_post(put) == {'action': 'select', 'gap_id': 'G2', 'choice_id': 'B'}
    assert open_page('plan-proposed').page.locator('button[data-a="select"]').count() == 0


@ident('C-3.4-55')
def test_shots_fold(open_page, _id):
    put = open_page('plan-proposed')
    rail(put, '').click()
    d = put.page.locator('#s-plan tr[data-unit="G1"] details')
    assert d.locator('summary').inner_text() == '1 shot' and d.get_attribute('open') is None
    d.locator('summary').click()
    assert d.get_attribute('open') is not None and 'IM1 · still' in d.inner_text()


@ident('C-3.4-56')
def test_accept_the_ticked_gaps(open_page, _id):
    put = open_page('plan-proposed')
    rail(put, '').click()
    put.page.check('input[data-sel="G1"]')
    put.page.check('input[data-sel="G2"]')
    put.click('#action button[data-a="accept-selected"]')
    assert put.red_line() == 'Your yes for these gaps is required.'
    no_post(put)
    put.page.fill('#words', 'Yes, both gaps.')
    put.click('#action button[data-a="accept-selected"]')
    assert only_post(put) == {'action': 'accept', 'gap_ids': ['G1', 'G2'], 'quote': 'Yes, both gaps.'}


@ident('C-3.4-57')
def test_revise_the_ticked_gaps(open_page, _id):
    put = open_page('plan-proposed')
    rail(put, '').click()
    put.page.check('input[data-sel="G1"]')
    put.page.check('input[data-sel="G2"]')
    put.page.fill('#words', 'Show both from above.')
    put.click('#action button[data-a="revise-selected"]')
    put.wait_posts(2)
    assert put.posts == [{'action': 'revise', 'gap_id': g, 'notes': 'Show both from above.', 'quote': 'Show both from above.'} for g in ('G1', 'G2')]


# ---------- 3.8 Pictures ----------

@ident('C-3.8-89')
def test_gap_filter_buttons_are_hidden(open_page, _id):
    put = open_page('pictures-candidate')
    b = put.page.locator('#s-pictures .tabs button[data-g]')
    assert b.count() == 2 and not b.first.is_visible(), 'the old gap buttons are in the page and must stay hidden: the left list replaces them'


@ident('C-3.8-90')
def test_approve_all_specs(open_page, _id):
    put = open_page('pictures-drawing-specs-waiting')
    show(put, 'specs')
    assert put.page.locator('#card-specs table tr').count() >= 3
    put.click('#card-specs button[data-a="approve-specs"]')
    assert only_post(put) == {'action': 'approve-specs', 'quote': ''}
    assert open_page('pictures-candidate').page.locator('button[data-a="approve-specs"]').count() == 0


@ident('C-3.8-91')
def test_picture_thumbnails(open_page, _id):
    put = open_page('pictures-candidate')
    put.click('#p-close')
    put.click('#card-IM1 img[data-ref="K1"]')
    assert put.page.locator('#panel img[data-view="K1"]').count() == 1 and 'sel' in put.page.get_attribute('#card-IM1 .pic[data-item="K1"]', 'class')
    placed = open_page('pictures-approved')
    placed.click('#card-IM1 img[data-ref="K1"]')
    assert 'Approved · in the film at 0:00–0:20 (IM1)' in panel(placed)


@ident('C-3.8-92')
def test_remove_a_clip(open_page, _id):
    put = open_page('controls-pictures-clip-placed')
    show(put, 'IM1')
    assert 'Filled with C0120.MP4 from 2 s to 22 s ✓' in put.text('#card-IM1')
    put.click('#card-IM1 button[data-a="unplace"]')
    assert only_post(put) == {'action': 'unplace', 'shot_id': 'IM1'}


@ident('C-3.8-93')
def test_loose_picture(open_page, _id):
    put = open_page('controls-pictures-many')
    show(put, 'IM1')
    d = put.page.locator('#card-IM1 details', has_text='No shot recorded (1)')
    d.locator('summary').first.click()
    assert d.locator('button[data-a]').all_inner_texts() == ['Use for the shot', 'Reject']
    d.locator('button[data-a="still"]').click()
    assert only_post(put) == {'action': 'still', 'shot_id': 'IM1', 'reference_id': 'L1', 'reuse': None, 'considered': None, 'crop': None}
    again = open_page('controls-pictures-many')
    show(again, 'IM1')
    d = again.page.locator('#card-IM1 details', has_text='No shot recorded (1)')
    d.locator('summary').first.click()
    d.locator('button[data-a="reject"]').click()
    assert only_post(again) == {'action': 'reject', 'reference_id': 'L1'}


@ident('C-3.8-94')
def test_picture_folds(open_page, _id):
    put = open_page('pictures-drawing-specs-waiting')
    show(put, 'IM1')
    spec = put.page.locator('#card-IM1 details', has_text='The drawing spec').first
    assert spec.get_attribute('open') is not None, 'a spec still to approve is not open'
    spec.locator('summary').first.click()
    assert spec.get_attribute('open') is None
    many = open_page('controls-pictures-many')
    show(many, 'IM1')
    for words in ('Use a stretch of a clip instead', 'References used (', 'No shot recorded (1)'):
        d = many.page.locator('#card-IM1 details', has_text=words).last
        assert d.get_attribute('open') is None
        d.locator('summary').first.click()
        assert d.get_attribute('open') is not None, f'the fold "{words}" did not open'


@ident('C-3.8-95')
def test_approve_the_spec(open_page, _id):
    put = open_page('pictures-drawing-specs-waiting')
    show(put, 'IM1')
    assert put.page.locator('#card-IM1 table tr').count() >= 3
    put.click('#card-IM1 button[data-a="approve-spec"]')
    assert only_post(put) == {'action': 'approve-spec', 'shot_id': 'IM1', 'quote': ''}
    assert put.bar() == ('ok', 'Drawing spec approved.')


@ident('C-3.8-96')
def test_correct_the_spec(open_page, _id):
    put = open_page('pictures-drawing-specs-waiting')
    show(put, 'DG2')
    put.click('#card-DG2 button[data-a="correct-spec"]')
    assert put.red_line() == 'Say which value is wrong and what it should be.'
    no_post(put)
    put.page.fill('[id="sp-c-DG2"]', 'the cavity is 50 mm')
    put.click('#card-DG2 button[data-a="correct-spec"]')
    assert only_post(put) == {'action': 'correct-spec', 'shot_id': 'DG2', 'words': 'the cavity is 50 mm'}


@ident('C-3.8-97')
def test_measure(open_page, _id):
    put = open_page('pictures-drawing-specs-waiting')
    show(put, 'IM1')
    put.click('#card-IM1 button[data-a="measure"]')
    assert put.red_line() == 'Pick the footage frames and say what to measure.'
    no_post(put)
    put.page.select_option('[id="ms-f-IM1"]', 'F1')
    put.page.fill('[id="ms-q-IM1"]', 'how thick is the leaf?')
    put.click('#card-IM1 button[data-a="measure"]')
    assert only_post(put) == {'action': 'measure', 'reference_ids': ['F1'], 'question': 'how thick is the leaf?'}


@ident('C-3.8-98')
def test_use_a_stretch_of_a_clip(open_page, _id):
    put = open_page('controls-pictures-many')
    show(put, 'IM1')
    put.page.locator('#card-IM1 details', has_text='Use a stretch of a clip instead').last.locator('summary').first.click()
    assert put.page.locator('[id="cf-c-IM1"] option').all_inner_texts() == ['C0120.MP4 (42 s)']
    put.click('#card-IM1 button[data-a="clip"]')
    assert put.red_line() == 'Say from which second of the clip.'
    put.page.fill('[id="cf-at-IM1"]', '2.5')
    put.click('#card-IM1 button[data-a="clip"]')
    assert put.red_line() == 'Your words for this stretch are required.'
    no_post(put)
    put.page.fill('[id="rf-why-IM1"]', 'the only shot of the plinth')
    put.page.fill('[id="rf-alt-IM1"]', 'from above adds nothing')
    put.page.fill('[id="rf-crop-IM1"]', '0.1,0.1,0.7,0.7')
    put.page.fill('[id="cf-w-IM1"]', 'Use the clip here.')
    put.click('#card-IM1 button[data-a="clip"]')
    assert only_post(put) == {'action': 'clip', 'shot_id': 'IM1', 'clip_id': 'C0120', 'in_s': 2.5, 'quote': 'Use the clip here.', 'reuse': 'the only shot of the plinth',
                              'considered': 'from above adds nothing', 'crop': [0.1, 0.1, 0.7, 0.7]}
    assert open_page('pictures-candidate').page.locator('button[data-a="clip"]').count() == 0, 'the clip form is shown on a run with no clips'


@ident('C-3.8-99')
def test_approve_the_reuse(open_page, _id):
    put = open_page('controls-pictures-many')
    show(put, 'IM1')
    assert 'Clip C0120 is already on screen in G1 at 0:04.' in put.text('#card-IM1')
    put.click('#card-IM1 button[data-a="approve-reuse"]')
    assert put.red_line() == 'Say in your words why the same footage is right here.'
    no_post(put)
    put.page.fill('[id="rw-IM1"]', 'It is the same wall, later.')
    put.click('#card-IM1 button[data-a="approve-reuse"]')
    assert only_post(put) == {'action': 'approve-reuse', 'shot_id': 'IM1', 'quote': 'It is the same wall, later.'}


@ident('C-3.8-100')
def test_question_answers_on_the_card(open_page, _id):
    put = open_page('controls-pictures-many')
    show(put, 'IM1')
    q = put.page.locator('#card-IM1 > .card button[data-a="answer"][data-item="IM1"]')
    assert 'Make the plinth from above or from the side? (about 20 INR)' in put.text('#card-IM1') and q.all_inner_texts() == ['From above', 'From the side']
    q.first.click()
    assert only_post(put) == {'action': 'answer', 'item': 'IM1', 'answer': 'From above'}


# ---------- 3.9 Takes ----------

@ident('C-3.9-101')
def test_start_image_thumbnails_and_earlier_pictures(open_page, _id):
    put = open_page('controls-takes-two-takes')
    show(put, 'VS1')
    put.click('#card-VS1 .strip img[data-ref="K1"]')
    assert put.page.locator('#panel .pair img[data-view="K1"]').count() == 1 and 'start image' in panel(put)
    d = put.page.locator('#card-VS1 details.chkd', has_text='1 earlier picture')
    assert d.get_attribute('open') is None
    d.locator('summary').first.click()
    assert d.locator('img[data-ref="K0"]').is_visible()


@ident('C-3.9-102')
def test_take_row(open_page, _id):
    put = open_page('takes-ready-to-select')
    put.click('#p-close')
    put.click('tr[data-take="job-take-1"]')
    assert 'Take · VS1' in panel(put) and 'sel' in put.page.get_attribute('tr[data-take="job-take-1"]', 'class')
    no_post(put)
    assert open_page('takes-nothing-yet').page.locator('tr[data-take]').count() == 0


@ident('C-3.9-103')
def test_play(open_page, _id):
    put = open_page('takes-ready-to-select')
    put.click('#p-close')
    put.click('#card-VS1 button[data-play]')
    assert put.visible('#player') and put.page.get_attribute('#pl', 'src').endswith('job-take-1.mp4')
    assert not put.visible('#panel'), 'Play also opened the take in the panel'
    assert open_page('takes-being-made').page.locator('button[data-play]').count() == 0, 'a take still being made offers Play'


@ident('C-3.9-104')
def test_spec_clip_reuse_and_question_on_a_take_card(open_page, _id):
    spec = open_page('pictures-drawing-specs-waiting-drawn-only-film', tab='takes')
    show(spec, 'DG2')
    spec.click('#card-DG2 button[data-a="approve-spec"]')
    assert only_post(spec) == {'action': 'approve-spec', 'shot_id': 'DG2', 'quote': ''}
    q = open_page('controls-takes-two-takes')
    show(q, 'VS1')
    q.page.locator('#card-VS1 button[data-a="answer"]', has_text='A hose').click()
    assert only_post(q) == {'action': 'answer', 'item': 'VS1', 'answer': 'A hose'}
    reuse = open_page('controls-takes-two-takes')
    show(reuse, 'VS1')
    reuse.page.fill('[id="rw-VS1"]', 'The same pour, closer.')
    reuse.click('#card-VS1 button[data-a="approve-reuse"]')
    assert only_post(reuse) == {'action': 'approve-reuse', 'shot_id': 'VS1', 'quote': 'The same pour, closer.'}
    clip = open_page('controls-takes-two-takes')
    show(clip, 'VS1')
    clip.page.locator('#card-VS1 details', has_text='Use a stretch of a clip instead').last.locator('summary').first.click()
    clip.page.fill('[id="cf-at-VS1"]', '3')
    clip.page.fill('[id="cf-w-VS1"]', 'My own pour.')
    clip.click('#card-VS1 button[data-a="clip"]')
    assert only_post(clip) == {'action': 'clip', 'shot_id': 'VS1', 'clip_id': 'C0120', 'in_s': 3, 'quote': 'My own pour.', 'reuse': None, 'considered': None, 'crop': None}


# ---------- 3.10 Record ----------

@ident('C-3.10-105')
def test_record_the_gaps(open_page, _id):
    put = open_page('record-gaps-ready')
    b = put.page.locator('#action button[data-a="record"]')
    assert b.inner_text() == 'Record 2 gaps' and b.is_enabled()
    b.click()
    assert put.red_line() == 'Your words are required: type them in the box at the foot first.'
    no_post(put)
    put.page.fill('#words', 'Record both.')
    b.click()
    assert only_post(put) == {'action': 'record', 'gap_ids': ['G1', 'G2'], 'quote': 'Record both.'}
    none = open_page('takes-nothing-yet', tab='record')
    assert none.page.is_disabled('#action button[data-a="record"]') and none.text('#tray span') == 'No gap is ready to record yet.'
