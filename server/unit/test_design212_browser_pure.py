"""design/212, the page checks: step 1 of the references in its new layout, `plugin/pages/decisions.html` drawn in a headless browser from
a local copy with the round the server builds from the shared fixture and a stand-in for the page's database and file store (no product
server, no network). At 1366x768 and 1920x1080, light and dark: everything for one thing with three pictures in one view; each case's
buttons; the ticks; corrections with and without words; leaving out with its sentence; the upload panel for a person and for a thing;
undo; auto-advance; the filters and the folding; the routine list and "Accept all"; the keys; no error in the console; no cost anywhere.
And finding 1: the widths of the table of facts on the Reference drawings step. Skipped where Playwright or its browser is not installed.
Set VW_SHOTS to a folder to keep screenshots."""
import base64
import io
import json
import os
import re
from pathlib import Path

import pytest
from PIL import Image

sync_api = pytest.importorskip('playwright.sync_api')

import d211_fixture as F
from test_design211c_kit_pure import Film

PAGE = Path(__file__).resolve().parents[2] / 'plugin' / 'pages' / 'decisions.html'
SIZES = {'1366': {'width': 1366, 'height': 768}, '1920': {'width': 1920, 'height': 1080}, '1000': {'width': 1000, 'height': 700}}
STUB = """
window.__answers = {};
(function(){
  let cb = null;
  const fire = () => { if (cb) cb({docs: Object.keys(window.__answers).map(k => ({id: k, data: () => window.__answers[k]}))}); };
  const db = {
    collection(path){
      if (path === 'rounds') return {orderBy(){ return this; }, limit(){ return this; }, onSnapshot(f){ f({docs: [{data: () => window.__round}]}); return () => {}; }};
      return {onSnapshot(f){ cb = f; fire(); return () => { cb = null; }; }};
    },
    doc(path){
      const parts = path.split('/'), id = parts[parts.length - 1];
      if (parts[0] === 'pics') return {get: async () => ({exists: true, data: () => ({data: window.__pic})})};
      if (parts[0] === 'zoom') return {get: async () => ({exists: false})};
      return {set: async d => { window.__answers[id] = JSON.parse(JSON.stringify(d)); fire(); }, delete: async () => { delete window.__answers[id]; fire(); }};
    }
  };
  const assets = {upload: async f => ({id: 'a'.repeat(32), url: window.__pic, contentType: f.type, sizeBytes: f.size})};
  window.claude = {use: async name => { if (name === 'db') return db; if (name === 'assets') return assets; throw new Error('not here'); }};
})();
"""


def picture():
    out = io.BytesIO()
    img = Image.new('RGB', (320, 180), (120, 150, 170))
    img.paste((200, 120, 60), (90, 50, 230, 130))
    img.save(out, 'PNG')
    return out.getvalue()


@pytest.fixture(scope='module')
def browser():
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            yield b
            b.close()
    except sync_api.Error as exc:   # no browser on this machine
        pytest.skip(f'no headless browser: {exc}')


def three_pictures(film):
    """The trowel with a third footage picture, weak: a thing with three pictures."""
    film.change(lambda s: (s['references'].update({'f-trowel-3': F._frame('f-trowel-3', 'TROWEL', 'object', 'frame-TROWEL', 't0000000000a3')}),
                           s['found']['TROWEL']['kept'].append('f-trowel-3')))
    return film


def doc(page):
    return {'round': 'r1', 'at': F.NOW, 'run': 'VW-211', **{k: page[k] for k in ('step', 'open', 'summary', 'note', 'lines', 'layout') if k in page}}


def show(browser, round_doc, size='1366', scheme='light', wait='#tmain .thead'):
    """The page file, as a document of its own, drawn with one round. The network is cut: the fonts' stylesheet is answered empty."""
    pg = browser.new_page(viewport=SIZES[size], color_scheme=scheme)
    pg.errors = []
    pg.on('console', lambda m: pg.errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: pg.errors.append(str(e)))
    pg.route('**/*', lambda route: route.fulfill(status=200, content_type='text/css', body='') if route.request.url.startswith('http') else route.continue_())
    data = json.dumps(round_doc).replace('</', '<\\/')
    pg.set_content('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
                   f"<script>window.__round = {data}; window.__pic = 'data:image/png;base64,{base64.b64encode(picture()).decode()}';{STUB}</script>"
                   + PAGE.read_text(encoding='utf-8') + '</body></html>')
    pg.wait_for_selector(wait, state='attached')
    return pg


def shot(pg, name):
    if os.environ.get('VW_SHOTS'):
        pg.screenshot(path=str(Path(os.environ['VW_SHOTS']) / f'{name}.png'))


def thing(pg, name):
    pg.locator('#trail .trow', has=pg.locator('.tnm', has_text=re.compile(f'^{re.escape(name)}$'))).click()
    pg.wait_for_function('n => document.querySelector("#tmain h2").textContent === n', arg=name)
    pg.wait_for_function("![...document.querySelectorAll('#tmain .tbar button')].some(b => b.disabled)")   # its pictures have shown


def bar(pg):
    return [' '.join(t.split()) for t in pg.locator('#tmain .tbar button').all_text_contents()]


def answers(pg):
    return pg.evaluate('window.__answers')


def saved(pg, line, choice):
    pg.wait_for_function('([l, c]) => (window.__answers[l] || {}).choice === c', arg=[line, choice])
    return answers(pg)[line]


def gone(pg, line):
    pg.wait_for_function('l => !window.__answers[l]', arg=line)


@pytest.mark.parametrize('size,scheme', [('1366', 'light'), ('1366', 'dark'), ('1920', 'light'), ('1920', 'dark')])
def test_step_1_in_its_new_layout(monkeypatch, browser, size, scheme):
    pg = show(browser, doc(three_pictures(Film(monkeypatch)).page()), size, scheme)
    tag = f'{size}-{scheme}'
    # the layout: the top bar, the list in its groups, one thing on the right
    assert pg.locator('#things').is_visible() and pg.locator('#wrap').is_hidden() and pg.locator('#dots .dot').count() == 0                     # 1: no rows of number circles
    assert pg.locator('#tstep').text_content() == 'References, step 1' and pg.locator('#tprogt').text_content() == '1 of 7 answered'           # 2: the person not in the footage counts from the start
    assert pg.locator('#trail .tgh span').all_text_contents() == ['Routine: accept together', 'With footage pictures', 'No action needed']      # 3: the groups, in the server's order
    assert [' '.join(t.split()) for t in pg.locator('#trail .tgh').all_text_contents()] == ['Routine: accept together4', 'With footage pictures2', 'No action needed1']   # 4
    assert pg.locator('#tmain h2').text_content() == 'Brick' and pg.locator('#trail .trow[aria-current]').locator('.tnm').text_content() == 'Brick'   # 5: the first thing to answer
    assert pg.evaluate('getComputedStyle(document.body).backgroundColor') == ('rgb(16, 22, 28)' if scheme == 'dark' else 'rgb(245, 247, 248)')  # 6: both themes
    # case 1, footage pictures: everything for a thing with three pictures in one view
    thing(pg, "Mason's trowel")
    assert bar(pg) == ['Approve Suggested', 'Make a set', 'Make a set with words', 'Upload my own', 'No reference needed']                                    # 7: the suggested answer first, and marked
    assert pg.locator('#tmain .tbar button').first.get_attribute('class') == 'tbtn go'                                                         # 8
    assert pg.locator('#tmain .ttile').count() == 3 and pg.locator('#tmain .tweak').count() == 2                                                 # 9
    tops = pg.evaluate("[...document.querySelectorAll('#tmain .ttile')].map(e => Math.round(e.getBoundingClientRect().top))")
    assert len(set(tops)) == 1                                                                                                                  # 10: the pictures in one row
    assert pg.evaluate("document.querySelector('#tmade').getBoundingClientRect().bottom <= window.innerHeight")                                # 11: the buttons and the line under them are in view
    assert pg.evaluate("(() => { const m = document.querySelector('#tmain'); return m.scrollHeight <= m.clientHeight; })()")                    # 12: nothing to scroll for
    assert pg.evaluate("document.querySelector('#tmain .tpics').getBoundingClientRect().bottom < document.querySelector('#tmain .tbar').getBoundingClientRect().top")   # 13: the buttons directly under the pictures
    assert pg.locator('#tmade').text_content() == 'Nothing is made until you say done in the chat.'                                            # 14
    assert pg.locator('#tmain .tsuggest').text_content() == 'Claude suggests: Use footageWhy?' and pg.locator('#twhy').is_hidden()             # 15
    pg.locator('#twhyb').click()
    assert pg.locator('#twhy').text_content() == 'The film shows it whole and sharp from the side.'                                            # 16
    assert pg.locator('#tshots').text_content() == 'Used in 2 shots · closest: a close-up' and pg.locator('#tused').is_hidden()                 # 17
    pg.locator('#tshots').click()
    assert pg.locator('#tused').text_content() == 'Used in 2 shots; the closest is a close-up (shot 2 of gap 2).'                              # 18: the full sentence, no code name
    pg.locator('#tinfo0').click()
    assert pg.locator('#tsaw0').text_content() == 'What Claude saw: The whole trowel, side on, sharp; the handle is reddish-brown.'             # 19
    shot(pg, f'three-pictures-{tag}')
    assert pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth') and '₹' not in pg.locator('body').inner_text()             # 20: no cost on the page
    # the ticks (the review of 17 Nov): the pictures Claude's proposal uses start ticked, weak or not; one the operator unticks is "not this picture"
    assert pg.evaluate("[...document.querySelectorAll('#tmain .tck input')].map(e => e.checked)") == [True, True, True]                         # 21: "use footage": all three, two of them weak
    pg.locator('#tmain [data-act="use"]').click()
    a = saved(pg, 'l06', 'use')
    assert (a['key'], a['item'], a['pics'], a['notes']) == ('ref:TROWEL', 'round1:TROWEL', {}, '')                                              # 22: nothing is marked
    assert pg.locator('#tanswer').text_content() == 'Your answer: Approve: the 3 ticked pictures are the reference.Undo'                       # 23: what will happen, said plainly
    assert pg.locator('#trail .trow[aria-current] .ttag').text_content() == 'Approved' and pg.locator('#tprogt').text_content() == '2 of 7 answered'   # 24
    pg.locator('#tck2').uncheck()
    pg.wait_for_function("Object.keys(window.__answers.l06.pics).length === 1")
    assert answers(pg)['l06']['pics'] == {'f-trowel-3': 'not'} and 'the 2 ticked pictures are the reference' in pg.locator('#tanswer').text_content()   # 25: the answer follows the ticks; the operator's own untick is "not this picture"
    pg.locator('#tck0').uncheck()
    pg.locator('#tck1').uncheck()
    gone(pg, 'l06')
    assert pg.locator('#tmsg').text_content() == 'Tick at least one picture first.' and pg.locator('#tanswer').count() == 0                     # 26: no picture kept: the answer is taken back, and says why
    pg.locator('#tmain [data-act="set"]').click()
    assert pg.locator('#tmsg').text_content() == 'Tick at least one picture first: the set is made from it.' and 'l06' not in answers(pg)       # 27: a refused click is said inline
    pg.locator('#tck0').check()
    assert pg.locator('#tmsg').is_hidden()                                                                                                      # 28
    # corrections: the words are required
    pg.locator('#tmain [data-act="fix"]').click()
    assert pg.locator('#tpanel label').text_content() == 'What should change?'                                                                 # 29
    pg.locator('#tfixsend').click()
    assert pg.locator('#tmsg').text_content() == 'Write what should change first.' and 'l06' not in answers(pg)                                 # 30
    pg.locator('#tfix').fill('Keep it, with a new handle.')
    shot(pg, f'corrections-{tag}')
    pg.locator('#tfixsend').click()
    a = saved(pg, 'l06', 'fix')
    assert (a['notes'], a['pics']) == ('Keep it, with a new handle.', {'f-trowel-use': 'not', 'f-trowel-3': 'not'}) and pg.locator('#tpanel').count() == 0   # 31
    pg.locator('#tundo').click()
    gone(pg, 'l06')
    assert pg.locator('#tanswer').count() == 0                                                                                                  # 32: undo
    # leaving out: the shots that lose the thing, then Leave it out or Cancel
    pg.locator('#tmain [data-act="ignore"]').click()
    assert pg.locator('#tpanel p').first.text_content() == 'These shots are then made with no reference of it: shot 1 of gap 2, shot 2 of gap 2.'   # 33
    assert pg.locator('#tpanel button').all_text_contents() == ['No reference needed', 'Cancel']                                                      # 34
    shot(pg, f'leave-out-{tag}')
    pg.locator('#tcancel').click()
    assert pg.locator('#tpanel').count() == 0 and 'l06' not in answers(pg)                                                                      # 35
    pg.locator('#tmain [data-act="ignore"]').click()
    pg.locator('#tleave').click()
    a = saved(pg, 'l06', 'ignore')
    assert a['pics'] == {} and pg.locator('#tanswer p').text_content() == 'Your answer: No reference needed.'                                         # 36
    # the upload panel, for a thing: no words of permission
    pg.locator('#tmain [data-act="own"]').click()
    assert pg.locator('#tpanel input[type=file]').count() == 1 and pg.locator('#tpanel input[type=text]').count() == 0                          # 37
    assert 'add your own' in pg.locator('#tpanel').text_content()                                                                              # 38
    pg.locator('#tpanel input[type=file]').set_input_files({'name': 'mine.png', 'mimeType': 'image/png', 'buffer': picture()})
    a = saved(pg, 'l06', 'own')
    assert a['own'][0]['name'] == 'mine.png' and a['permission'] == '' and pg.locator('#tanswer img.ownpic').count() == 1                          # 39
    # case 2, only a "closest found" picture: Approve needs its tick
    thing(pg, 'Wall fan regulator')
    assert bar(pg) == ['No reference needed Suggested', 'Approve', 'Make a set', 'Upload my own']                                                         # 40
    assert pg.locator('#tmain .tisit').text_content() == 'Closest found: is this it?' and pg.locator('#tck0').is_checked() is False             # 41
    pg.locator('#tmain [data-act="use"]').click()
    assert pg.locator('#tmsg').text_content() == 'Tick the picture first, if that is it.' and 'l07' not in answers(pg)                          # 42
    pg.locator('#tck0').check()
    pg.locator('#tmain [data-act="use"]').click()
    assert saved(pg, 'l07', 'use')['pics'] == {'t0000000000c1': 'use'}                                                                         # 43: a ticked closest picture is "that is it"
    shot(pg, f'closest-{tag}')
    # case 3, no picture, a thing
    thing(pg, 'Brick')
    assert bar(pg) == ['Make a set Suggested', 'Upload my own', 'No reference needed'] and pg.locator('#tmain [data-act="words"]').text_content() == 'Add words for the picture (optional)'   # 44
    assert pg.locator('#tmain .tnopics').text_content() == 'Not in your footage. why'                                                          # 45
    pg.locator('#tsearchwhy').click()
    assert pg.locator('#tmain .tnopics').text_content() == 'Not in your footage. The helper was stopped. less'                                 # 46: the reason behind "why"
    pg.locator('#tmain [data-act="words"]').click()
    assert pg.locator('#tpanel label').text_content() == 'What must the picture show?'                                                         # 47
    pg.locator('#tfix').fill('A wet brick.')
    pg.locator('#tfixsend').click()
    assert saved(pg, 'l02', 'fix')['notes'] == 'A wet brick.'                                                                                  # 48
    shot(pg, f'no-picture-{tag}')
    # case 4, a person the footage does not show: nothing to decide
    thing(pg, 'The mason')
    assert bar(pg) == ['Add words for the picture', 'Upload my own'] and pg.locator('#tmain .tsug').count() == 0                               # 49
    assert pg.locator('#tmain .tnopics').text_content().startswith('Not in your footage. A set will be made from the description when you say done in the chat. No answer is needed;')   # 50
    assert pg.locator('#tanswer').text_content() == 'Decided: A set will be made. No answer is needed.' and pg.locator('#tundo').count() == 0   # 51
    pg.locator('#tmain [data-act="own"]').click()
    perm = pg.locator('#tpanel input[type=text]')
    assert perm.count() == 1 and "permission" in perm.get_attribute('placeholder')                                                             # 52: the words of permission first, for a person
    pg.locator('#tpanel input[type=file]').set_input_files({'name': 'him.png', 'mimeType': 'image/png', 'buffer': picture()})
    assert "Write first that you have this person's permission" in pg.locator('#tpanel').text_content() and 'l08' not in answers(pg)           # 53
    shot(pg, f'upload-person-{tag}')
    perm.fill('He agreed that we use his photo.')
    pg.locator('#tpanel input[type=file]').set_input_files({'name': 'him.png', 'mimeType': 'image/png', 'buffer': picture()})
    assert saved(pg, 'l08', 'own')['permission'] == 'He agreed that we use his photo.'                                                         # 54
    assert not pg.errors, pg.errors                                                                                                            # 55: no error in the console
    pg.close()


def test_the_list_its_filters_its_folding_and_the_routine_things(monkeypatch, browser):
    pg = show(browser, doc(three_pictures(Film(monkeypatch)).page()))
    pg.locator('#tauto').uncheck()
    rows = lambda: pg.locator('#trail .trow:visible .tnm').all_text_contents()
    assert rows() == ['Brick', 'The street', 'Laying a brick', 'Roof tile', "Mason's trowel", 'Wall fan regulator', 'The mason']               # 1: the groups' order; the plan's order inside
    pg.locator('#trail [data-filter="done"]').click()
    assert rows() == ['The mason']                                                                                                             # 2
    pg.locator('#trail [data-filter="open"]').click()
    assert len(rows()) == 6 and 'The mason' not in rows()                                                                                      # 3
    pg.locator('#trail [data-filter="all"]').click()
    pg.locator('#trail .tgh').first.click()
    assert rows() == ["Mason's trowel", 'Wall fan regulator', 'The mason'] and pg.locator('#trail .tgh').first.get_attribute('aria-expanded') == 'false'   # 4: a group folds
    pg.locator('#trail .tgh').first.click()
    assert len(rows()) == 7                                                                                                                    # 5
    # the routine things, seen before they are accepted together; one answered alone keeps its answer
    assert pg.locator('#trail .tprop p').first.text_content() == "Accept Claude's proposals for the 4 routine things"                           # 6
    assert pg.locator('#taccept').text_content() == 'Accept all 4' and pg.locator('#tshow').text_content() == 'Show the 4'                      # 7
    thing(pg, 'The street')
    pg.locator('#tmain [data-act="ignore"]').click()
    pg.locator('#tleave').click()
    saved(pg, 'l03', 'ignore')
    pg.locator('#tshow').click()
    assert pg.locator('#tmain .tprow').count() == 4 and pg.locator('#tmain h2').text_content() == "Accept Claude's proposals for the 4 routine things"   # 8
    tile = pg.locator('#tmain .tprow', has_text='Roof tile')
    assert tile.locator('.tpim').count() == 1 and 'Claude suggests: Make a set' in tile.text_content() and 'It has approved drawings' in tile.text_content()   # 9: its pictures, the suggestion and the reason
    assert 'You answered: No reference' in pg.locator('#tmain .tprow', has_text='The street').text_content()                                       # 10
    shot(pg, 'routine-list')
    pg.locator('#taccepthere').click()
    a = saved(pg, 'l01', 'accept_all')
    assert a['key'] == 'refs:proposals' and answers(pg)['l03']['choice'] == 'ignore'                                                           # 11: the thing answered alone keeps its answer
    assert pg.locator('#taccepthere').text_content() == 'All accepted' and pg.locator('#taccepthere').is_disabled()                             # 12
    assert pg.locator('#tprogt').text_content() == '5 of 7 answered'                                                                           # 13
    tile.locator('button', has_text='Open').click()
    assert pg.locator('#tmain h2').text_content() == 'Roof tile' and pg.locator('#tanswer p').text_content() == "Your answer: Make a set. (Claude's proposal, accepted.)"   # 14
    pg.locator('#tunaccept').click()
    gone(pg, 'l01')
    assert pg.locator('#tprogt').text_content() == '2 of 7 answered'                                                                           # 15: the acceptance undone
    assert not pg.errors, pg.errors
    pg.close()


def test_the_keys_the_large_picture_and_auto_advance(monkeypatch, browser):
    pg = show(browser, doc(three_pictures(Film(monkeypatch)).page()))
    name = lambda: pg.locator('#tmain h2').text_content()
    assert name() == 'Brick'
    pg.keyboard.press('ArrowRight')
    assert name() == 'The street'                                                                                                              # 1
    pg.keyboard.press('k')
    pg.keyboard.press('j')
    pg.keyboard.press('ArrowLeft')
    assert name() == 'Brick'                                                                                                                   # 2
    thing(pg, "Mason's trowel")
    pg.keyboard.press('2')
    assert not pg.locator('#tck1').is_checked()                                                                                                # 3: a number ticks or unticks a picture
    pg.keyboard.press('2')
    assert pg.locator('#tck1').is_checked()
    pg.keyboard.press('c')
    assert pg.locator('#tpanel #tfix').count() == 1                                                                                            # 4
    pg.keyboard.press('Escape')
    assert pg.locator('#tpanel').count() == 0                                                                                                  # 5
    pg.keyboard.press('l')
    assert pg.locator('#tleave').count() == 1                                                                                                  # 6
    pg.keyboard.press('Escape')
    pg.locator('[data-pop="tkeys"]').click()
    assert pg.locator('#tkeys').is_visible() and 'Make a set with words' in pg.locator('#tkeys').text_content()                                    # 7
    pg.keyboard.press('Escape')
    assert pg.locator('#tkeys').is_hidden()                                                                                                    # 8
    pg.locator('[data-pop="thow"]').click()
    how = pg.locator('#thow').text_content()
    assert 'A set is three pictures of one thing, which become its reference; for a person, their three views; a place gets one picture.' in how and 'C003.mp4' in how   # 9: what a set is, and the clips nobody could search, said once
    pg.keyboard.press('Escape')
    # the large picture is the page's own
    pg.locator('#tmain .timg').first.click()
    assert pg.locator('.zoom').count() == 1 and 'side (1 of 3)' in pg.locator('.zoom').text_content()                                         # 10
    pg.keyboard.press('ArrowRight')
    assert 'in the hand, lifting mortar (2 of 3)' in pg.locator('.zoom').text_content() and name() == "Mason's trowel"                         # 11: the arrows move in the large view only
    pg.keyboard.press('Escape')
    assert pg.locator('.zoom').count() == 0                                                                                                    # 12
    # auto-advance: on at first; after an answer the next thing still to answer comes by itself
    assert pg.locator('#tauto').is_checked()                                                                                                   # 13
    pg.keyboard.press('a')
    saved(pg, 'l06', 'use')
    pg.wait_for_function("document.querySelector('#tmain h2').textContent === 'Wall fan regulator'", timeout=5000)                             # 14
    pg.locator('#tauto').uncheck()
    pg.keyboard.press('s')
    saved(pg, 'l07', 'set')
    pg.wait_for_timeout(1500)
    assert name() == 'Wall fan regulator'                                                                                                      # 15: off: it stays
    pg.locator('#tnextopen').click()
    assert name() == 'Brick'                                                                                                                   # 16: "Next to answer" goes round to the first that waits
    assert not pg.errors, pg.errors
    pg.close()


def test_a_refusal_after_done_is_shown_and_a_kept_answer_reads_as_answered(monkeypatch, browser):
    from test_design211c_kit_pure import ans
    film = three_pictures(Film(monkeypatch))
    l = film.lines()
    out = film.record(ans(l['ref:TROWEL'], 'use', pics={'f-trowel-side': 'not', 'f-trowel-use': 'not', 'f-trowel-3': 'not'}), ans(l['ref:BRICK'], 'set'))
    page = out['page']
    page['layout']['stopped'] = 'The answers ask for 80 sets, and the limit of this film is passed.'
    pg = show(browser, doc(page))
    assert pg.locator('#tstop').is_visible() and pg.locator('#tstop').text_content().startswith('Not recorded: The answers ask for 80 sets')    # 1: the one place the limit is named
    thing(pg, "Mason's trowel")
    assert pg.locator('#trefused').text_content() == 'Not recorded: Tick at least one picture first.'                                          # 2: the server's refusal, on its thing
    thing(pg, 'Brick')
    assert pg.locator('#tanswer').text_content() == 'Kept from before: Make a set. Choose another answer to change it.' and pg.locator('#tundo').count() == 0   # 3
    assert pg.locator('#tprogt').text_content() == '2 of 7 answered'                                                                           # 4
    pg.close()


def test_at_1000_px_the_layout_holds_and_the_name_keeps_its_room(monkeypatch, browser):
    pg = show(browser, doc(three_pictures(Film(monkeypatch)).page()), '1000')
    thing(pg, "Mason's trowel")
    assert pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')                                                            # 1
    assert pg.evaluate("document.querySelector('#tmain h2').scrollWidth <= document.querySelector('#tmain h2').clientWidth")                    # 2: the name is whole (finding 14)
    assert pg.locator('#tmain .ttile').count() == 3 and pg.locator('#tnextopen').is_visible()                                                   # 3
    shot(pg, 'narrow-1000')
    pg.close()


def test_every_thing_answered_says_go_back_to_the_chat(monkeypatch, browser):
    film = Film(monkeypatch)
    page = film.page()
    for line in page['lines']:
        line['kept'] = line.get('kept') or 'Make a set'
    page['lines'] = [x for x in page['lines'] if x['key'] != 'refs:proposals']
    pg = show(browser, doc(page), wait='#tmain .talldone')
    assert pg.locator('#tmain .talldone').text_content() == 'All answered.Go back to the chat and say done.' and pg.locator('#tprogt').text_content() == '7 of 7 answered'
    pg.close()


def test_the_table_of_facts_gives_its_room_to_the_value(browser):
    """Finding 1 (SK, 17 Nov 2026): on the Reference drawings step the VALUE column was narrow and FROM wide and empty; FACT broke short labels."""
    facts = [['tile length', 'raised ribs and grooves running along the length of the tile, two lugs at the head on the underside, a rounded nose at the tail', 'the plan'],
             ['tile width', '24 cm', 'a standard: the common size of this tile in the region, taken from the maker\'s sheet'],
             ['a longer label than twenty-four characters', '41 cm', 'the client']]
    line = {'line': 'l01', 'key': 'drawing:TILE', 'title': 'Roof tile', 'state': 'open', 'item': 'drawing:TILE:x', 'ask': 'Is the shape and arrangement right?', 'text': '1 sheet.',
            'pics': [{'code': 'p00000000000a', 'label': 'Front'}], 'facts': facts, 'buttons': [{'label': 'Yes', 'choice': 'yes', 'needs_words': False}]}
    pg = show(browser, {'round': 'r1', 'at': F.NOW, 'run': 'VW-211', 'step': 'Reference drawings', 'open': True, 'summary': '', 'note': '', 'lines': [line]}, '1366', wait='table.facts')
    w = pg.evaluate("[...document.querySelectorAll('table.facts tbody tr:first-child td')].map(e => e.getBoundingClientRect().width)")
    assert w[1] > w[0] and w[1] > w[2] and w[1] > 0.5 * sum(w)                                                                                  # 1: VALUE the widest
    one_line = pg.evaluate("(() => { const td = document.querySelector('table.facts tbody td'); const r = document.createRange(); r.selectNodeContents(td); return r.getClientRects().length; })()")
    assert one_line == 1                                                                                                                        # 2: a short label is not broken
    assert pg.evaluate("getComputedStyle(document.querySelector('table.facts tbody tr:nth-child(2) td:nth-child(3)')).whiteSpace") == 'normal'  # 3: FROM wraps
    assert pg.locator('#things').is_hidden() and pg.locator('section.item').count() == 1                                                        # 4: this step keeps its own layout
    shot(pg, 'facts-table')
    pg.close()


def test_what_a_tick_means_on_vw24s_things(monkeypatch, browser):
    """The review of 17 Nov 2026, fault 1, on VW-24's shapes at 1366x768: the starting ticks follow the proposal; a picture left unticked is not used
    and is never "not this picture"; the answer says what will happen; and a new picture that came asks for one look."""
    from test_design212_layout_pure import vw24
    film, _things = vw24(monkeypatch)
    page = film.page()
    by = {l['key']: l for l in page['lines']}
    by['ref:PAN'].update(note='A new picture was found for this thing. Look at it, then confirm or change your answer.', again={'choice': 'fix', 'notes': 'Without the mortar in it.'})
    pg = show(browser, doc(page))
    ticks = lambda: pg.evaluate("[...document.querySelectorAll('#tmain .tck input')].map(e => e.checked)")
    line = lambda key: by[key]['line']
    # a person, a set proposed, three weak pictures: none starts ticked; "Make a set" marks no picture and says it is made from the description
    thing(pg, 'Thing Helper')
    assert ticks() == [False, False, False] and pg.locator('#tmain .tweak').count() == 3                                                        # 1
    pg.locator('#tmain [data-act="set"]').click()
    a = saved(pg, line('ref:HELPER'), 'set')
    assert a['pics'] == {}                                                                                                                     # 2: no "not this picture"
    assert pg.locator('#tanswer p').text_content() == 'Your answer: Make a set from the description; the footage pictures are not used.'       # 3
    assert pg.locator('#tmain .ttile').count() == 3                                                                                            # 4: its pictures stay
    shot(pg, 'ticks-from-the-description')
    pg.locator('#tck1').check()
    pg.wait_for_function('l => Object.keys(window.__answers[l].pics).length === 1', arg=line('ref:HELPER'))
    assert answers(pg)[line('ref:HELPER')]['pics'] == {'f-HELPER-1': 'on'}                                                                     # 5: a picture the operator ticked is used
    assert pg.locator('#tanswer p').text_content() == 'Your answer: Make a set from the 1 ticked picture.'                                     # 6
    shot(pg, 'ticks-one-ticked')
    # "use footage" with a weak picture: all start ticked; the operator's own untick is "not this picture"
    thing(pg, 'Thing Concrete')
    assert ticks() == [True, True, True] and pg.locator('#tmain .tweak').count() == 1                                                           # 7
    pg.locator('#tck0').uncheck()
    pg.locator('#tmain [data-act="use"]').click()
    assert saved(pg, line('ref:CONCRETE'), 'use')['pics'] == {'f-CONCRETE-0': 'not'}                                                           # 8
    assert pg.locator('#tanswer p').text_content() == 'Your answer: Approve: the 2 ticked pictures are the reference.'                         # 9
    # a new picture came for a thing: the answer given waits for one look
    thing(pg, 'Thing Pan')
    assert pg.locator('#tcame').text_content().startswith('A new picture was found for this thing. Look at it, then confirm or change your answer.')   # 10
    pg.locator('#tconfirm').click()
    a = saved(pg, line('ref:PAN'), 'fix')
    assert a['notes'] == 'Without the mortar in it.' and 'A set is made from the 3 ticked pictures, with these words.' in pg.locator('#tanswer p').text_content()   # 11
    assert not pg.errors, pg.errors
    pg.close()
