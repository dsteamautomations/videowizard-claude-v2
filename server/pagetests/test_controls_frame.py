"""Layer 1, one test per control: what is always on the page (page-facts 3.1), the right panel and the viewer (3.2), and what acts
without a click (3.11). Each test opens the state where the control appears, operates it as the operator does and asserts its one
effect: the exact request, or the exact change on screen. The id of each test is its row in controls.json."""
import base64
import re

from conftest import REV
from kit import card, clean, ident, no_post, only_post, panel, rail, show

CODE = 'VW-20'


def k1_rejected(payload):
    for r in payload['references']:
        if r['id'] == 'K1':
            r.update(status='rejected')


def reject_k1(open_page):
    """Reject the still K1 in the panel, with a server that answers as the real one does: the picture is then rejected."""
    put = open_page('pictures-candidate')
    put.serve('pictures-candidate', k1_rejected)
    put.click('#panel button[data-a="reject"]')
    put.wait_posts(1)
    return put


def first_result(open_page, state='refs-older-pass1'):
    """An older film's round: the first search result of E2, open in the panel."""
    put = open_page(state)
    show(put, 'E2')
    put.page.locator('#s-references [data-unit="E2"] .pic[data-lb] img').first.click()
    return put


# ---------- 3.1 always on the page ----------

@ident('C-3.1-01')
def test_tab_links(open_page, _id):
    put = open_page('refs-step2-all-sets-back')
    assert put.page.locator('#steps a').count() == 6
    for tab in ['treatment', 'plan', 'pictures', 'takes', 'record', 'references']:
        put.click(f'#steps a[data-s="{tab}"]')
        assert put.active_tab() == tab and put.visible(f'#s-{tab}'), f'the {tab} tab did not open'
        assert put.page.locator('#stage > section:not([hidden])').count() == 1, 'more than one tab is shown'
    no_post(put, ' by a tab')
    old = first_result(open_page)   # leaving References with a ticked, unsaved picture asks first
    old.click('#p-tick')
    asked = []
    old.page.once('dialog', lambda d: (asked.append(d.message), d.dismiss()))
    old.click('#steps a[data-s="pictures"]')
    assert asked == ['1 ticked pictures are not saved. Leave anyway?'], f'the question on leaving with unsaved ticks: {asked}'
    assert old.active_tab() == 'references', 'the tab changed although the operator answered Cancel'


@ident('C-3.1-02')
def test_waiting_count_opens_the_list(open_page, _id):
    put = open_page('refs-step1-to-answer')
    n = len(put.payload['waiting'])
    assert put.header_count() == n and not put.visible('#wlist')
    put.click('#wcount')
    assert put.visible('#wlist') and put.page.locator('#wlist a').count() == n
    names = {e['id']: e['name'] for e in put.payload['elements']}   # follow-up fix 5: the name, not the id (the server's label carries the id; the page shows the name)
    assert put.page.locator('#wlist a').all_inner_texts() == [w['label'].replace(f"· {w['group']}", f"· {names[w['group']]}") for w in put.payload['waiting']]
    put.click('#wcount')
    assert not put.visible('#wlist')
    none = open_page('refs-round-complete')
    assert none.page.locator('#wcount').count() == 0, 'the count is shown though nothing waits'


@ident('C-3.1-03')
def test_waiting_list_link(open_page, _id):
    put = open_page('pictures-candidate', tab='record')
    put.click('#wcount')
    put.page.locator('#wlist a', has_text='Still · IM1').click()
    put.page.wait_for_timeout(100)
    assert put.page.evaluate('location.hash') == '#pictures/IM1/K1'
    assert put.active_tab() == 'pictures' and put.page.locator('#panel img[data-view="K1"]').count() == 1, 'the link did not open the still K1 in the panel'
    assert not put.red_line()
    no_post(put)


@ident('C-3.1-04')
def test_next_waiting(open_page, _id):
    put = open_page('pictures-candidate', tab='record')
    put.click('#wnext')
    put.page.wait_for_timeout(100)
    assert put.active_tab() == 'pictures' and put.page.locator('#panel img[data-view="K1"]').count() == 1
    assert not put.red_line()
    no_post(put)
    assert open_page('refs-round-complete').page.locator('#wnext').count() == 0, 'Next waiting is offered though nothing waits'


@ident('C-3.1-05')
def test_history(open_page, _id):
    put = open_page('pictures-candidate')
    assert not put.visible('#mhist')
    put.click('#mhist-b')
    assert put.text('#mhist') == 'No message yet.'
    put.click('#mhist-b')
    assert not put.visible('#mhist')
    put.click('#panel button[data-a="approve"]')
    put.wait_posts(1)
    put.click('#mhist-b')
    lines = put.page.locator('#mhist div').all_inner_texts()
    assert any(re.fullmatch(r'\d\d:\d\d\s+Picture approved\.', x.strip()) for x in lines), f'History does not hold the last message: {lines}'


@ident('C-3.1-06')
def test_rail_filter_all(open_page, _id):
    put = open_page('pictures-candidate')
    everything = [c['unit'] for c in put.cards()]
    put.click('#rfil [data-rf="wait"]')
    put.click('#rfil [data-rf="all"]')
    assert [c['unit'] for c in put.cards()] == everything == ['', 'IM1']
    assert 'on' in put.page.get_attribute('#rfil [data-rf="all"]', 'class')


@ident('C-3.1-07')
def test_rail_filter_waiting_for_me(open_page, _id):
    put = open_page('pictures-candidate')
    assert put.text('#rfil [data-rf="wait"]') == '● Waiting for me (1)'
    put.click('#rfil [data-rf="wait"]')
    assert [c['unit'] for c in put.cards()] == ['IM1'] and all(c['waiting'] for c in put.cards())
    none = open_page('pictures-nothing-yet')
    none.click('#rfil [data-rf="wait"]')
    assert none.cards() == [] and none.text('#rcards') == 'Nothing waits for you on this step.'


@ident('C-3.1-08')
def test_rail_filter_by_gap(open_page, _id):
    put = open_page('takes-ready-to-select')
    assert put.page.locator('#rf-gap option').all_inner_texts() == ['a gap…', 'G2']
    put.page.select_option('#rf-gap', 'G2')
    assert [c['unit'] for c in put.cards()] == ['VS1']
    put.page.select_option('#rf-gap', '')
    assert [c['unit'] for c in put.cards()] == ['', 'VS1']
    assert open_page('refs-step2-all-sets-back').page.locator('#rf-gap').count() == 0, 'the gap filter is shown where no card belongs to a gap'


@ident('C-3.1-09')
def test_rail_card(open_page, _id):
    put = open_page('pictures-candidate')
    rail(put, '').click()
    assert put.page.locator('#rcards .rcard.on').get_attribute('data-unit-card') == '' and not put.visible('#panel')
    rail(put, 'IM1').click()
    assert put.page.locator('#rcards .rcard.on').get_attribute('data-unit-card') == 'IM1'
    assert put.visible('#card-IM1') and put.page.locator('#panel img[data-view="K1"]').count() == 1, 'the card did not open its shot with its picture'
    assert put.page.evaluate('location.hash') == '#pictures/IM1'
    no_post(put)
    takes = open_page('controls-takes-two-takes')   # a card with a take that waits opens that take
    rail(takes, '').click()
    rail(takes, 'VS1').click()
    assert 'Take · VS1' in panel(takes) and takes.page.locator('#panel button[data-a="select-take"][data-job="job-take-2"]').count() == 1, f'the card of a shot whose take waits opened: {panel(takes)[:80]!r}'


@ident('C-3.1-10')
def test_grip_drag(open_page, _id):
    put = open_page('pictures-candidate')
    p = put.page
    width = lambda: p.evaluate('getComputedStyle(document.getElementById("app")).getPropertyValue("--rail").trim()')
    box = p.locator('#grip').bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + 200

    def drag(to):
        nonlocal x
        p.mouse.move(x, y)
        p.mouse.down()
        p.mouse.move(to, y, steps=4)
        p.mouse.up()
        b = p.locator('#grip').bounding_box()
        x = b['x'] + b['width'] / 2
    assert width() == '260px'
    drag(x + 60)
    assert 300 <= int(width()[:-2]) <= 330, f'the list is {width()} wide after a drag of 60 px'
    assert p.evaluate(f'localStorage.getItem("vz:{CODE}:rail")') == width()[:-2], 'the width is not kept on this computer'
    drag(1200)
    assert width() == '360px'
    drag(0)
    assert width() == '200px'


@ident('C-3.1-11')
def test_keys_up_and_down(open_page, _id):
    put = open_page('pictures-candidate')
    on = lambda: put.page.locator('#rcards .rcard.on').get_attribute('data-unit-card')
    assert on() == 'IM1'
    put.page.keyboard.press('ArrowUp')
    assert on() == ''
    put.page.keyboard.press('ArrowDown')
    assert on() == 'IM1'
    put2 = open_page('pictures-drawing-specs-waiting')   # not while typing in a text field
    show(put2, 'IM1')
    before = put2.page.locator('#rcards .rcard.on').get_attribute('data-unit-card')
    put2.page.locator('textarea[id^="sp-c-"]:visible').first.click()
    put2.page.keyboard.press('ArrowDown')
    assert put2.page.locator('#rcards .rcard.on').get_attribute('data-unit-card') == before


@ident('C-3.1-12')
def test_key_escape_closes_the_panel(open_page, _id):
    put = open_page('pictures-candidate')
    assert put.visible('#panel')
    put.page.keyboard.press('Escape')
    assert not put.visible('#panel')


@ident('C-3.1-13')
def test_header_links_sign_out_theme(open_page, _id):
    put = open_page('pictures-candidate')
    p = put.page
    assert [p.locator(f'header a[href="{h}"], a[href="{h}"]').count() > 0 for h in ('/runs', '/voices', '/defects')] == [True, True, True]
    assert put.text('form[action="/logout"] button') == 'Sign out SK'
    was = p.evaluate('document.documentElement.getAttribute("data-theme")')
    p.click('#theme-toggle')
    now = p.evaluate('document.documentElement.getAttribute("data-theme")')
    assert now in ('light', 'dark') and now != was and p.evaluate('localStorage.getItem("vw2-theme")') == now
    with p.expect_request(lambda r: r.url.endswith('/logout') and r.method == 'POST'):
        p.click('form[action="/logout"] button')


@ident('C-3.1-14')
def test_docked_player(open_page, _id):
    put = open_page('takes-ready-to-select')
    assert not put.visible('#player')
    put.click('#card-VS1 button[data-play]')
    assert put.visible('#player') and put.page.get_attribute('#pl', 'controls') is not None
    assert put.page.get_attribute('#pl', 'src').endswith('/file/run-1/visuals/takes/job-take-1.mp4')
    assert put.text('#pl-name') == 'VS1 · job-take'
    no_post(put)


# ---------- 3.2 the right panel and the viewer ----------

@ident('C-3.2-15')
def test_panel_close(open_page, _id):
    put = open_page('pictures-candidate')
    put.click('#p-close')
    assert not put.visible('#panel')
    no_post(put)


@ident('C-3.2-16')
def test_large_picture_opens_the_viewer(open_page, _id):
    put = open_page('pictures-candidate')
    assert not put.visible('#viewer')
    put.click('#panel img[data-view="K1"]')
    assert put.visible('#viewer') and put.page.get_attribute('#vw-img', 'src').endswith('/file/run-1/visuals/references/K1.png')


@ident('C-3.2-17')
def test_version_tabs(open_page, _id):
    put = open_page('controls-pictures-many')
    show(put, 'IM1')
    put.click('#card-IM1 img[data-ref="K1"]')
    tabs = put.page.locator('#panel [data-vref]')
    assert tabs.all_inner_texts() == ['Version 2 · new', 'Version 1 · rejected']
    put.click('#panel [data-vref="K0"]')
    assert 'Rejected: “the mark reads 320 mm”' in panel(put) and 'on' in put.page.get_attribute('#panel [data-vref="K0"]', 'class')
    assert put.page.locator('#panel button[data-a="approve"]').count() == 0, 'a rejected version can be approved'
    assert open_page('pictures-candidate').page.locator('[data-vref]').count() == 0, 'version tabs are shown for a picture with one version'


@ident('C-3.2-18')
def test_take_tabs(open_page, _id):
    put = open_page('controls-takes-two-takes')
    rail(put, '').click()
    put.click('tr[data-take="job-take-2"]')
    assert put.page.locator('#panel [data-vtake]').all_inner_texts() == ['Take 2 · new', 'Take 1 · rejected']
    put.click('#panel [data-vtake="job-take-1"]')
    assert 'Rejected: the water pours upward' in panel(put)
    assert open_page('takes-ready-to-select').page.locator('[data-vtake]').count() == 0


@ident('C-3.2-19')
def test_approve(open_page, _id):
    put = open_page('pictures-candidate')
    put.click('#panel button[data-a="approve"]')
    assert only_post(put) == {'action': 'approve', 'reference_id': 'K1', 'sha256': 'sha-K1'}
    assert put.bar() == ('ok', 'Picture approved.')
    done = open_page('pictures-approved')
    done.click('#card-IM1 img[data-ref="K1"]')
    assert done.page.locator('#panel button[data-a="approve"]').count() == 0, 'an approved picture offers Approve again'
    if not REV:   # main: a set's picture is judged on step 2, never approved one by one in the panel
        rnd = open_page('refs-step2-all-sets-back')
        rnd.page.locator('#s-references [data-unit="BRICK"] img[data-ref]').first.click()
        assert 'judge the whole set on step 2' in panel(rnd) and rnd.page.locator('#panel button[data-a]').count() == 0


@ident('C-3.2-20')
def test_reject(open_page, _id):
    put = reject_k1(open_page)
    assert only_post(put) == {'action': 'reject', 'reference_id': 'K1'}
    assert put.visible('#rwhy'), 'the reason box did not open after the reject'
    stay = open_page('pictures-approved')   # an approved picture placed in a gap offers Remove, not Reject
    stay.click('#card-IM1 img[data-ref="K1"]')
    assert stay.page.locator('#panel button[data-a]').all_inner_texts() == ['Remove']


@ident('C-3.2-21')
def test_use_for_the_shot(open_page, _id):
    put = open_page('controls-pictures-approved-not-placed')
    put.click('#card-IM1 img[data-ref="K1"]')
    put.click('#panel button[data-a="still"]')
    assert only_post(put) == {'action': 'still', 'shot_id': 'IM1', 'reference_id': 'K1', 'reuse': None, 'considered': None, 'crop': None}
    assert open_page('pictures-candidate').page.locator('#panel button[data-a="still"]').count() == 0, 'a picture not yet approved can be used for the shot'


@ident('C-3.2-22')
def test_remove(open_page, _id):
    put = open_page('pictures-approved')
    put.click('#card-IM1 img[data-ref="K1"]')
    put.click('#panel button[data-a="unplace"]')
    assert only_post(put) == {'action': 'unplace', 'shot_id': 'IM1'}
    seq = open_page('controls-pictures-sequence-placed')
    seq.page.locator('#card-AN1 img[data-ref="R2"]').click()
    seq.click('#panel button[data-a="unplace"]')
    assert only_post(seq) == {'action': 'unplace', 'shot_id': 'AN1'}
    rec = open_page('record-recorded', tab='pictures')
    rec.click('#card-IM1 img[data-ref]')
    assert rec.page.locator('#panel button[data-a="unplace"]').count() == 0, 'a recorded gap offers Remove'


@ident('C-3.2-23')
def test_approve_the_sequence(open_page, _id):
    put = open_page('controls-pictures-sequence-states-made')
    show(put, 'AN1')
    put.click('#card-AN1 img[data-ref="R3"]')
    assert put.page.locator('#panel .pair img').count() == 3, 'the three states are not side by side'
    put.click('#panel button[data-a="sequence"]')
    assert only_post(put) == {'action': 'sequence', 'shot_id': 'AN1'}
    one = open_page('controls-pictures-sequence-one-state')
    show(one, 'AN1')
    one.click('#card-AN1 img[data-ref="R1"]')
    assert one.page.locator('#panel button[data-a="sequence"]').count() == 0, 'the sequence can be approved with states still to make'
    assert '2 state(s) still to make' in panel(one)
    assert one.page.locator('#panel button[data-a]').all_inner_texts() == ['Approve state 1', 'Reject state 1']
    one.click('#panel button[data-a="approve"]')
    assert only_post(one) == {'action': 'approve', 'reference_id': 'R1', 'sha256': 'sha-R1'}


@ident('C-3.2-24')
def test_try_a_fix(open_page, _id):
    put = open_page('pictures-failed-check')
    b = put.page.locator('#panel button[data-a="fix"]')
    assert b.inner_text() == 'Try a fix (₹20)'
    b.click()
    assert only_post(put) == {'action': 'fix', 'reference_id': 'K1'}
    assert open_page('pictures-candidate').page.locator('button[data-a="fix"]').count() == 0, 'a fix is offered for a picture with no failed line'


@ident('C-3.2-25')
def test_note_and_save_the_note(open_page, _id):
    put = open_page('refs-no-round-kept')
    rail(put, 'E1').click()
    put.click('#s-references img[data-ref="F1"]')
    put.page.fill('#ref-note', 'keep the chamfer')
    put.click('#panel button[data-a="save-note"]')
    assert only_post(put) == {'action': 'note', 'reference_id': 'F1', 'note': 'keep the chamfer'}


@ident('C-3.2-26')
def test_reason_chips(open_page, _id):
    put = reject_k1(open_page)
    chips = put.page.locator('#panel [data-rchip]')
    assert chips.all_inner_texts() == ['wrong subject', 'text wrong', 'light or colour', 'framing', 'not like the footage']
    chips.nth(3).click()
    chips.nth(1).click()
    assert put.page.input_value('#rwhy') == 'framing; text wrong'
    assert len(put.posts) == 1, 'a chip sent a request'


@ident('C-3.2-27')
def test_reason_text(open_page, _id):
    put = reject_k1(open_page)
    put.page.fill('#rwhy', 'the mark reads 320 mm')
    put.page.locator('#panel [data-rchip]').first.click()
    assert put.page.input_value('#rwhy') == 'the mark reads 320 mm; wrong subject'


@ident('C-3.2-28')
def test_save_the_reason(open_page, _id):
    put = reject_k1(open_page)
    put.page.fill('#rwhy', 'the mark reads 320 mm')
    put.click('#panel button[data-a="reject-why"]')
    assert only_post(put, 2) == {'action': 'reject', 'reference_id': 'K1', 'notes': 'the mark reads 320 mm'}
    empty = reject_k1(open_page)
    empty.click('#panel button[data-a="reject-why"]')
    empty.page.wait_for_timeout(150)
    assert len(empty.posts) == 1 and not empty.visible('#rwhy'), 'an empty reason was sent, or its box stayed open'
    take = open_page('takes-ready-to-select')
    take.click('tr[data-take="job-take-1"]')
    take.click('#panel button[data-a="reject-take"]')
    take.wait_posts(1)
    take.page.fill('#rwhy', 'the water pours upward')
    take.click('#panel button[data-a="reject-take-why"]')
    assert only_post(take, 2) == {'action': 'reject-take', 'job_id': 'job-take-1', 'notes': 'the water pours upward'}


@ident('C-3.2-29')
def test_skip_the_reason(open_page, _id):
    put = reject_k1(open_page)
    put.click('#panel button[data-a="reason-skip"]')
    put.page.wait_for_timeout(100)
    assert not put.visible('#rwhy') and len(put.posts) == 1


@ident('C-3.2-30')
def test_question_answers_in_the_panel(open_page, _id):
    put = open_page('controls-pictures-many')
    show(put, 'IM1')
    put.click('#card-IM1 img[data-ref="K1"]')
    q = put.page.locator('#panel button[data-a="answer"]')
    assert 'Keep the chalk mark on this picture?' in panel(put) and q.all_inner_texts() == ['Keep it', 'Remove it']
    q.nth(1).click()
    assert only_post(put) == {'action': 'answer', 'item': 'K1', 'answer': 'Remove it'}


@ident('C-3.2-31')
def test_select_a_take(open_page, _id):
    put = open_page('takes-ready-to-select')
    put.click('tr[data-take="job-take-1"]')
    put.click('#panel button[data-a="select-take"]')
    assert only_post(put) == {'action': 'select-take', 'job_id': 'job-take-1'}
    for state in ('takes-selected', 'takes-rejected', 'takes-being-made'):
        other = open_page(state)
        other.click('tr[data-take="job-take-1"]')
        assert other.page.locator('#panel button[data-a="select-take"], #panel button[data-a="reject-take"]').count() == 0, f'{state}: the take still offers Select or Reject'


@ident('C-3.2-32')
def test_reject_a_take(open_page, _id):
    put = open_page('takes-ready-to-select')
    put.click('tr[data-take="job-take-1"]')
    put.click('#panel button[data-a="reject-take"]')
    assert only_post(put) == {'action': 'reject-take', 'job_id': 'job-take-1'}
    assert put.visible('#rwhy') and put.page.locator('#panel button[data-a="reject-take-why"]').count() == 1


@ident('C-3.2-33')
def test_take_video(open_page, _id):
    put = open_page('takes-ready-to-select')
    put.click('tr[data-take="job-take-1"]')
    v = put.page.locator('#panel video')
    assert v.get_attribute('controls') is not None and v.get_attribute('src').endswith('/file/run-1/visuals/takes/job-take-1.mp4')


@ident('C-3.2-34')
def test_panel_folds(open_page, _id):
    put = open_page('pictures-failed-check')
    d = put.page.locator('#panel details.pdet')
    assert d.get_attribute('open') is None
    d.locator('summary').click()
    assert d.get_attribute('open') is not None and 'keyframe' in d.inner_text()
    c = put.page.locator('#panel details.chkd').first
    assert c.locator('summary').inner_text() == '1 passed · 1 to look at: the width mark'
    c.locator('summary').click()
    assert c.locator('li').count() == 2 and c.locator('li.err').is_visible()


@ident('C-3.2-35')
def test_previous_and_next(open_page, _id):
    put = first_result(open_page)
    assert '1 of 3' in panel(put) and put.page.is_disabled('#p-prev') and put.page.is_enabled('#p-next')
    put.click('#p-next')
    assert '2 of 3' in panel(put)
    put.click('#p-next')
    assert '3 of 3' in panel(put) and put.page.is_disabled('#p-next')
    put.click('#p-prev')
    assert '2 of 3' in panel(put)
    no_post(put)


@ident('C-3.2-36')
def test_tick_as_image(open_page, _id):
    put = first_result(open_page)
    assert put.text('#p-tick') == 'Tick as Image 1'
    put.click('#p-tick')
    assert put.text('#p-tick') == 'Untick (Image 1)' and put.page.locator('#s-references .tick.on').inner_text() == '1'
    put.click('#p-tick')
    assert put.text('#p-tick') == 'Tick as Image 1' and put.page.locator('#s-references .tick.on').count() == 0
    no_post(put)


@ident('C-3.2-37')
def test_picture_note(open_page, _id):
    put = first_result(open_page)
    assert put.page.locator('#p-note').count() == 0 and 'Tick it to add a note.' in panel(put)
    put.click('#p-tick')
    put.page.locator('#p-note').press_sequentially('keep the chimney')
    put.click('#p-next')
    put.click('#p-prev')
    assert put.page.input_value('#p-note') == 'keep the chimney', 'the note was lost on moving to another picture and back'


@ident('C-3.2-38')
def test_note_chips(open_page, _id):
    put = first_result(open_page)
    put.click('#p-tick')
    assert put.page.locator('#panel [data-pchip]').all_inner_texts() == ['avoid brand text', 'posture only, not the person', 'colour only']
    put.click('#panel [data-pchip="colour only"]')
    put.click('#panel [data-pchip="avoid brand text"]')
    assert put.page.input_value('#p-note') == 'colour only; avoid brand text'


@ident('C-3.2-39')
def test_save_a_result(open_page, _id):
    put = first_result(open_page)
    sid = put.payload['round']['elements']['E2']['search_id']
    assert put.page.locator('#p-save').count() == 0, 'Save is offered before the picture is ticked'
    put.click('#p-tick')
    put.page.locator('#p-note').press_sequentially('colour only')
    put.click('#p-save')
    assert only_post(put) == {'action': 'pick', 'search_id': sid, 'picks': [{'n': 1, 'note': 'colour only'}]}
    assert put.bar() == ('ok', 'Image saved with its note for Clamp kiln.')   # follow-up fix 5: the name, not the id


@ident('C-3.2-40')
def test_source_link(open_page, _id):
    put = first_result(open_page)
    a = put.page.locator('#panel a', has_text='source')
    assert (a.get_attribute('href'), a.get_attribute('target'), a.get_attribute('rel')) == ('https://site.example/p1', '_blank', 'noopener')


@ident('C-3.2-41')
def test_search_result_large_picture(open_page, _id):
    put = first_result(open_page)
    put.click('#panel img[data-sview]')
    assert put.visible('#viewer') and put.page.get_attribute('#vw-img', 'src') == 'https://img.example/1.jpg'
    assert put.text('#viewer .vw-side .btns .ds') == '1 of 3'


@ident('C-3.2-42')
def test_add_your_own_picture(open_page, _id):
    put = first_result(open_page)
    put.click('#panel button[data-a="supply"]')
    assert put.red_line() == 'Choose a file or paste an https link first.'
    no_post(put)
    put.page.fill('#panel [id="url-E2"]', 'https://example.org/kiln.jpg')
    put.click('#panel button[data-a="supply"]')
    assert only_post(put) == {'action': 'supply', 'element_id': 'E2', 'url': 'https://example.org/kiln.jpg'}
    assert put.bar() == ('ok', 'Your picture is saved and approved for Clamp kiln.')   # follow-up fix 5: the name, not the id
    f = first_result(open_page)
    f.page.set_input_files('#panel [id="up-E2"]', {'name': 'kiln.png', 'mimeType': 'image/png', 'buffer': b'not really a png'})
    f.click('#panel button[data-a="supply"]')
    assert only_post(f) == {'action': 'supply', 'element_id': 'E2', 'name': 'kiln.png', 'content_base64': base64.b64encode(b'not really a png').decode()}
    elem = open_page('refs-older-no-round-element-view')   # also in the one-element view of an older film
    assert elem.page.locator('#s-references button[data-a="supply"]').count() == 1
    assert open_page('refs-no-round-kept').page.locator('button[data-a="supply"]').count() == 0, 'a new film offers the own-picture box before the round'


@ident('C-3.2-43')
def test_viewer_buttons(open_page, _id):
    put = first_result(open_page)
    put.click('#panel img[data-sview]')
    p = put.page
    scale = lambda: p.evaluate('document.getElementById("vw-img").style.transform')
    assert p.is_disabled('#vw-prev')
    p.click('#vw-next')
    assert put.text('#viewer .vw-side .btns .ds') == '2 of 3' and p.get_attribute('#vw-img', 'src') == 'https://img.example/2.jpg'
    p.click('#vw-prev')
    assert put.text('#viewer .vw-side .btns .ds') == '1 of 3'
    p.click('#vw-in')
    assert 'scale(1.25)' in scale()
    p.click('#vw-out')
    assert 'scale(1)' in scale()
    p.click('#vw-close')
    assert not put.visible('#viewer')
    no_post(put)


@ident('C-3.2-44')
def test_viewer_wheel_and_drag(open_page, _id):
    put = open_page('pictures-candidate')
    put.click('#panel img[data-view="K1"]')
    p = put.page
    tr = lambda: p.evaluate('document.getElementById("vw-img").style.transform')
    b = p.locator('#vw-stage').bounding_box()
    cx, cy = b['x'] + b['width'] / 2, b['y'] + b['height'] / 2
    p.mouse.move(cx, cy)
    p.mouse.wheel(0, -120)
    p.wait_for_timeout(60)
    assert 'scale(1.15)' in tr(), f'the wheel did not zoom in: {tr()}'
    p.mouse.down()
    p.mouse.move(cx + 80, cy + 40, steps=3)
    p.mouse.up()
    assert 'translate(80px, 40px)' in tr(), f'the drag did not move the picture: {tr()}'
    p.mouse.wheel(0, 120)
    p.wait_for_timeout(60)
    assert 'scale(1.0005' in tr() or 'scale(1)' in tr()


@ident('C-3.2-45')
def test_viewer_keys(open_page, _id):
    put = first_result(open_page)
    put.click('#panel img[data-sview]')
    p = put.page
    scale = lambda: p.evaluate('document.getElementById("vw-img").style.transform')
    p.keyboard.press('ArrowRight')
    assert put.text('#viewer .vw-side .btns .ds') == '2 of 3'
    p.keyboard.press('ArrowLeft')
    assert put.text('#viewer .vw-side .btns .ds') == '1 of 3'
    p.keyboard.press('+')
    assert 'scale(1.25)' in scale()
    p.keyboard.press('-')
    assert 'scale(1)' in scale()
    p.keyboard.press('Escape')
    assert not put.visible('#viewer')


@ident('C-3.2-46')
def test_panel_buttons_inside_the_viewer(open_page, _id):
    put = open_page('pictures-candidate')
    put.click('#panel img[data-view="K1"]')
    assert put.page.locator('#vw-panel button[data-a]').all_inner_texts() == ['Approve', 'Reject']
    put.click('#vw-panel button[data-a="approve"]')
    assert only_post(put) == {'action': 'approve', 'reference_id': 'K1', 'sha256': 'sha-K1'}
    assert not put.visible('#viewer'), 'the viewer stayed open after the verdict'
    res = first_result(open_page)   # a search result: tick, note and Save beside the large picture
    sid = res.payload['round']['elements']['E2']['search_id']
    res.click('#panel img[data-sview]')
    res.click('#vw-panel #p-tick')
    res.click('#vw-panel #p-save')
    assert only_post(res) == {'action': 'pick', 'search_id': sid, 'picks': [{'n': 1, 'note': ''}]}


@ident('C-3.2-47')
def test_keys_left_and_right_over_results(open_page, _id):
    put = first_result(open_page)
    put.page.keyboard.press('ArrowRight')
    assert '2 of 3' in panel(put)
    put.page.keyboard.press('ArrowLeft')
    assert '1 of 3' in panel(put)


# ---------- 3.11 what acts without a click ----------

@ident('C-3.11-106')
def test_timer(open_page, _id):
    def reads_after(state, ms, patch=None):
        put = open_page(state, clock=True, patch=patch)
        n = put.data_gets
        put.page.clock.fast_forward(ms)
        put.page.wait_for_timeout(250)
        return put.data_gets - n
    assert reads_after('refs-sets-being-made', 14000) == 0, 'the page read its data before 15 s'
    assert reads_after('refs-sets-being-made', 15500) == 1, 'while pictures are being made the page reads its data every 15 s'
    assert reads_after('refs-round-complete', 20000) == 0, 'with nothing being made the page read its data before 60 s'
    assert reads_after('refs-round-complete', 60500) == 1, 'with nothing being made the page reads its data every 60 s'
    assert reads_after('refs-round-complete', 60500, lambda p: p['run'].update(stage='assembly')) == 0, 'the page keeps reading after the run left the visuals stage'


@ident('C-3.11-107')
def test_return_to_the_browser_tab(open_page, _id):
    put = open_page('refs-round-complete')
    n = put.data_gets
    put.refresh()
    assert put.data_gets == n + 1


@ident('C-3.11-108')
def test_hash_change(open_page, _id):
    put = open_page('takes-ready-to-select', tab='plan')
    put.go_hash('takes/VS1/job-take-1')
    assert put.active_tab() == 'takes' and 'Take · VS1' in panel(put)
    assert 'hl' in put.page.get_attribute('tr[data-take="job-take-1"]', 'class') and not put.red_line()


@ident('C-3.11-109')
def test_leaving_with_unsaved_ticks(open_page, _id):
    put = first_result(open_page)
    asks = 'const e = new Event("beforeunload", {cancelable: true}); window.dispatchEvent(e); e.defaultPrevented'
    assert put.page.evaluate(asks) is False, 'the browser asks before leaving though nothing is ticked'
    put.click('#p-tick')
    assert put.page.evaluate(asks) is True, 'the browser does not ask before leaving with an unsaved tick'


@ident('C-3.11-110')
def test_lapsed_sign_in(open_page, _id):
    put = open_page('refs-round-complete')
    put.page.route('**/visuals/data', lambda r: r.fulfill(status=401, body=''))
    put.page.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
    put.page.wait_for_url('**/login?next=*', timeout=3000)
    assert put.page.url.endswith(f'/login?next=%2Fruns%2F{CODE}%2Fvisuals')


def test_no_script_error_while_operating(open_page):
    """The controls of the busiest state, pressed one after another, leave no script error."""
    put = open_page('controls-pictures-many')
    rail(put, '').click()
    for sel in ('#rfil [data-rf="wait"]', '#rfil [data-rf="all"]', '#mhist-b', '#wcount', '#wnext'):
        put.click(sel)
    assert card(put, 'IM1').count() == 1
    clean(put)
