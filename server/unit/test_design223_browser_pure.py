"""design/223 (SK, 22 Nov 2026), the page checks: step 7 with the new take process, `plugin/pages/decisions.html` drawn in a headless browser from a
local copy (the harness of design/222: the frozen round, the stand-in database, a webm the browser records itself; no product server). The round's
lines are given the new shape here: a take has no check; its answers are Accept and Say what is wrong; a version is shown beside the video it
was made from, with "Play both together"; a new video that could not be made is said, with "Send it again". Every label comes from the round.
Skipped where Playwright or its browser is not installed."""
import pytest

pytest.importorskip('playwright.sync_api')

from app import takes as T   # noqa: E402
from test_design212_browser_pure import browser   # noqa: E402,F401 (the fixture)
from test_design217_browser_pure import inside, saved   # noqa: E402
from test_design222_browser_pure import bar, clean, doc, go, page, playing, still_main   # noqa: E402

W, PAID = T.PAGE, T.W['paid']


def button(label, choice, act, take, say, end, words=False, paid=False, sure=None):
    return {'label': label, 'choice': choice, 'act': act, 'take': take, 'needs_words': words, 'hint': T.W['hint_again'] if words else '', 'go': T.W['go_again'] if words else '',
            'prefill': '', 'need': T.W['need_words'] if words else '', 'note': PAID if paid else '', 'say': say, 'end': end, **({'paid': True} if paid else {}), **({'sure': sure} if sure else {})}


def new(extra=None):
    """The frozen round in design/223's shape. l01: take 1 (360p), which the operator spoke of, and take 2 (720p), an edit of it: shown side by
    side. l02: one first take (360p). l03: answered earlier."""
    def change(l, d):
        d['layout']['words']['takes'], d['layout']['help'] = W, T.W['help']
        for ln in d['lines']:
            for t in ln['takes']:
                t.pop('check', None)
                t.update(tab=t['label'], size='360p' if t['n'] == 1 else '720p', how=T.W['how_first'] if t['n'] == 1 else T.W['how_edit'].format(m=1), rejected='')
            if ln.get('answer'):
                ln['answer'].pop('against', None)
        two, one = l['l01'], l['l02']
        two['takes'][0]['rejected'] = T.W['said'].format(words='The helper looks into the camera.')
        two['compare'] = {'from': 1, 'new': 2, 'play': T.W['play_both']}
        at = two['film_at']
        two['buttons'] = [button('Accept', 'select', 'select', 2, T.W['say_select'].format(n=2, at=at), T.W['end_select'].format(n=2, at=at)),
                          button('Say what is wrong', 'again', 'again', 2, T.W['say_again'].format(n=2, words='{words}'), T.W['end_again'].format(n=2, words='{words}'), words=True, paid=True),
                          button('Use take 1 after all', 'old:1', 'select', 2, T.W['say_copy'].format(n=1), T.W['end_copy'].format(n=1), paid=True,
                                 sure={'ask': T.W['old_ask'].format(n=1), 'go': 'Use take 1 after all', 'back': T.W['back']})]
        one['buttons'] = [button('Accept', 'select', 'select', 1, T.W['say_copy'].format(n=1), T.W['end_copy'].format(n=1), paid=True),
                          button('Say what is wrong', 'again', 'again', 1, T.W['say_again'].format(n=1, words='{words}'), T.W['end_again'].format(n=1, words='{words}'), words=True, paid=True)]
        if extra:
            extra(l, d)
    return doc(change)


def test_a_first_take_has_no_check_and_two_answers_and_accept_is_one_click(browser):
    d = new()
    pg = page(browser, d)
    go(pg, {l['line']: l for l in d['lines']}['l02'])
    playing(pg)
    assert bar(pg) == ['Accept', 'Say what is wrong'] and pg.locator('#pcheck').count() == 0 and pg.locator('#kpair').count() == 0   # nobody checked it; nothing to compare it with
    assert 'primary' in pg.locator('#pbar [data-choice="select"]').get_attribute('class')
    pg.locator('#pbar [data-choice="select"]').click()
    got = saved(pg, 'l02', 'select')
    text = pg.locator('#sanswer').text_content()
    assert got['choice'] == 'select' and 'full-size video' in text and 'against' not in (pg.locator('#sanswer').get_attribute('class') or '')
    row = pg.locator('#srail .srow[data-line="l02"]')
    assert row.locator('.sdot').text_content() == '✓' and row.get_attribute('title') == W['done']['select'] and 'against' not in row.get_attribute('class')
    clean(pg)


def test_saying_what_is_wrong_needs_words_and_writes_them(browser):
    d = new()
    pg = page(browser, d)
    go(pg, {l['line']: l for l in d['lines']}['l02'])
    pg.locator('#pbar [data-choice="again"]').click()
    assert T.W['hint_again'] in pg.locator('#spanel').text_content() and PAID in pg.locator('#spanel').text_content()
    pg.locator('#sfixsend').click()
    assert pg.locator('#smsg').text_content() == T.W['need_words']   # the correction is made from their words
    pg.locator('#sfix').fill('There are poles on the left; there should be none.')
    pg.locator('#sfixsend').click()
    got = saved(pg, 'l02', 'again')
    assert got['notes'] == 'There are poles on the left; there should be none.' and 'There are poles on the left' in pg.locator('#sanswer').text_content()
    row = pg.locator('#srail .srow[data-line="l02"]')
    assert row.locator('.sdot').text_content() == '↻' and row.get_attribute('title') == W['done']['again']
    clean(pg)


@pytest.mark.parametrize('size', ['fit-small', 'fit-large'])
def test_a_version_is_shown_beside_the_video_it_was_made_from_and_both_play_together(browser, size):
    pg = page(browser, new(), size=size)
    playing(pg)
    pg.wait_for_function("(() => { const v = document.querySelector('#pvideo2'); return v && v.readyState >= 2; })()")
    a, b = inside(pg, '#sbig2'), inside(pg, '#sbig')   # the one before on the left, the new one on the right, both in view
    assert a['x'] + a['width'] <= b['x'] + 1 and abs(a['y'] - b['y']) < 2 and abs(a['width'] - b['width']) < 2 and a['height'] >= 100
    caps = [' '.join(t.split()) for t in pg.locator('#kpair figcaption').all_text_contents()]
    assert caps == [f"{W['compare_from']} · Take 1", f"{W['compare_new']} · Take 2"]
    assert bar(pg) == ['Accept', 'Say what is wrong', 'Use take 1 after all'] and pg.locator('#pwas').count() == 0
    pg.evaluate("document.querySelectorAll('#pvideo, #pvideo2').forEach(v => { v.pause(); v.currentTime = 1; })")
    assert pg.locator('#kboth').text_content() == T.W['play_both']
    pg.locator('#kboth').click()
    pg.wait_for_function("[...document.querySelectorAll('#pvideo, #pvideo2')].every(v => !v.paused && v.currentTime < 0.9)")
    inside(pg, '#pbar'), inside(pg, '#kboth')
    assert still_main(pg)
    pg.locator('#ptabs [data-take="1"]').click()   # the earlier take alone: nothing to compare, and what the operator said of it
    pg.wait_for_function("!document.querySelector('#kpair')")
    assert T.W['said'].format(words='The helper looks into the camera.') in pg.locator('#pwas').text_content()
    clean(pg)


def test_a_new_video_that_could_not_be_made_is_said_and_can_be_sent_again(browser):
    said = T.W['failed_new'].format(why='The provider ended the call as failed: RESOURCE_EXHAUSTED: quota.')

    def failed(l, d):
        l['l02']['failed'] = said
        l['l02']['buttons'].append(button('Send it again', 'resend', 'again', 1, T.W['say_resend'], T.W['end_resend'], paid=True))
    d = new(failed)
    pg = page(browser, d)
    go(pg, {l['line']: l for l in d['lines']}['l02'])
    assert pg.locator('#pfailed').text_content() == said and bar(pg) == ['Accept', 'Say what is wrong', 'Send it again']
    pg.locator('#pbar [data-choice="resend"]').click()
    assert saved(pg, 'l02', 'resend')['choice'] == 'resend' and T.W['say_resend'] in pg.locator('#sanswer').text_content()
    clean(pg)


def test_the_end_card_counts_every_video_done_will_make(browser):
    d = new()
    pg = page(browser, d)
    pg.locator('#pbar [data-choice="select"]').click()   # l01: take 2 is 720p: it goes in the film, nothing is made
    saved(pg, 'l01', 'select')
    go(pg, {l['line']: l for l in d['lines']}['l02'])
    pg.locator('#pbar [data-choice="select"]').click()   # l02: a 360p take accepted: its full-size video is made
    saved(pg, 'l02', 'select')
    pg.wait_for_selector('#send li')
    assert pg.locator('#eagain').text_content() == W['end_again'].replace('{n}', '1') and pg.locator('#ereject').count() == 0
    rows = [' '.join(t.split()) for t in pg.locator('#send li').all_text_contents()]
    assert any(T.W['end_copy'].format(n=1) in r for r in rows) and not any('against' in r for r in rows)
    clean(pg)
