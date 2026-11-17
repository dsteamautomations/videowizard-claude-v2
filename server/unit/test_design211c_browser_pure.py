"""design/211 part C (section 6.3, the page checks): `plugin/pages/decisions.html` drawn in a headless browser from a local copy, with the
rounds the server builds from the shared fixture and a stand-in for the page's database (no product server, no network). A v2 round: the
groups fold, Claude's proposal and its button, a weak tag, what Claude saw, a picture's own button toggles and is saved with the answer,
the check list, the folded notes and the set before; at desktop and phone width, light and dark. A line of an older round draws as before.
Skipped where Playwright or its browser is not installed."""
import base64
import json
from pathlib import Path

import pytest

sync_api = pytest.importorskip('playwright.sync_api')

import d211_fixture as F
from test_design211c_kit_pure import Film, older_step1, png
from test_design211c_lines_pure import remade

PAGE = Path(__file__).resolve().parents[2] / 'plugin' / 'pages' / 'decisions.html'
VIEWS = {'desktop': {'width': 1200, 'height': 900}, 'phone': {'width': 375, 'height': 812}}
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
  window.claude = {use: async name => { if (name === 'db') return db; throw new Error('not here'); }};
})();
"""


@pytest.fixture(scope='module')
def browser():
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            yield b
            b.close()
    except sync_api.Error as exc:   # no browser on this machine
        pytest.skip(f'no headless browser: {exc}')


def doc(page):
    return {'round': 'r1', 'at': F.NOW, 'run': 'VW-211', 'step': page['step'], 'open': page['open'], 'summary': page['summary'], 'note': page['note'], 'lines': page['lines']}


def show(browser, round_doc, view='desktop', scheme='light'):
    """The page file, as a document of its own, drawn with one round. Every network call is cut: the page is local."""
    pg = browser.new_page(viewport=VIEWS[view], color_scheme=scheme)
    pg.route('**/*', lambda route: route.abort() if route.request.url.startswith('http') else route.continue_())
    data = json.dumps(round_doc).replace('</', '<\\/')
    pg.set_content('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
                   f"<script>window.__round = {data}; window.__pic = 'data:image/png;base64,{base64.b64encode(png()).decode()}';{STUB}</script>"
                   + PAGE.read_text(encoding='utf-8') + '</body></html>')
    pg.wait_for_selector('section.item', state='attached')   # a group with nothing to answer is folded
    return pg


def block(pg, title):
    return pg.locator('section.item', has=pg.locator('h2', has_text=title))


def ready(pg, blk):
    """The block on screen with its pictures shown: they load when the row nears the screen, and the picture buttons work only then."""
    blk.scroll_into_view_if_needed()
    blk.locator('button.pick').first.wait_for()
    pg.wait_for_function("el => ![...el.querySelectorAll('button.pick')].some(b => b.disabled)", arg=blk.element_handle())


def answers(pg):
    return pg.evaluate('window.__answers')


def no_side_scroll(pg):
    return pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')


@pytest.mark.parametrize('view,scheme', [('desktop', 'light'), ('desktop', 'dark'), ('phone', 'light'), ('phone', 'dark')])
def test_step_1_of_a_v2_round_on_the_page(monkeypatch, browser, view, scheme):
    pg = show(browser, doc(Film(monkeypatch).page()), view, scheme)
    heads = pg.locator('button.ghead')
    assert [t.split(' ', 1)[1] for t in heads.locator('span:first-child').all_text_contents()] == ['Doubtful: answer these yourself', 'People', 'Things', 'Materials', 'Places', 'Ways of working']   # 1
    assert heads.nth(0).locator('.count').text_content() == '2 lines, 2 to answer' and heads.nth(0).get_attribute('aria-expanded') == 'true'   # 2
    first = pg.locator('section.item').first
    assert first.locator('.acts button').first.text_content() == 'Accept the 5 proposals (paid, about ₹175)' and 'go' in first.locator('.acts button').first.get_attribute('class')   # 3
    trowel = block(pg, "Mason's trowel")
    assert trowel.locator('p.prop').text_content() == 'Claude proposes: Use it as the reference. The film shows it whole and sharp from the side.'   # 4
    assert trowel.locator('.acts > button').all_text_contents() == ['Use it as the reference', 'Make a clean set from it (paid, about ₹35)', 'Leave it out']   # 5: the proposed answer first
    assert 'go' in trowel.locator('.acts > button').first.get_attribute('class')   # 6
    assert trowel.locator('.pcell .tag').all_text_contents() == ['Weak']   # 7
    assert trowel.locator('.pnote').all_text_contents() == ['Claude saw: The whole trowel, side on, sharp; the handle is reddish-brown.', 'Claude saw: In the hand, the blade half covered by mortar.']   # 8
    assert 'Read before you answer' in trowel.locator('.note').text_content()   # 9
    assert trowel.locator('.acts textarea').get_attribute('placeholder').startswith('Words for the picture (optional)')   # 10
    assert 'If you leave it out, these shots are made with no reference of it: G2-S1-SH1, G2-S1-SH2.' in trowel.locator('.acts').text_content()   # 11
    assert block(pg, 'The mason').locator('.acts > button').all_text_contents() == ['Have a set made (paid, about ₹35)']   # 12: no "Leave it out" for a person in a made picture
    assert no_side_scroll(pg)   # 13
    assert pg.evaluate('getComputedStyle(document.body).backgroundColor') == ('rgb(16, 22, 28)' if scheme == 'dark' else 'rgb(245, 247, 248)')   # 14: both themes
    # a picture's own button toggles and is saved with the answer
    ready(pg, trowel)
    marks = trowel.locator('button.pick')
    assert marks.all_text_contents() == ['Not this picture', 'Not this picture']   # 15
    marks.nth(1).click()
    pg.wait_for_function("window.__answers.l02 && window.__answers.l02.choice === 'pics'")
    a = answers(pg)['l02']
    assert (a['key'], a['item'], a['pics']) == ('ref:TROWEL', 'round1:TROWEL', {'f-trowel-use': 'not'})   # 16
    assert trowel.locator('.pcell.no').count() == 1 and trowel.locator('button.pick.on').text_content() == 'Not this picture (marked: undo)'   # 17
    assert trowel.locator('.head .tag').text_content() == 'A picture answered; the line still to answer' and trowel.locator('.acts > button').count() == 3   # 18: the line is still to answer
    trowel.locator('.acts > button', has_text='Use it as the reference').click()
    pg.wait_for_function("window.__answers.l02.choice === 'approve'")
    assert answers(pg)['l02']['pics'] == {'f-trowel-use': 'not'} and trowel.locator('.head .tag').text_content() == 'You chose: Use it as the reference'   # 19: saved with the answer
    trowel.locator('button', has_text='Undo my answer').click()
    pg.wait_for_function("window.__answers.l02.choice === 'pics'")
    assert answers(pg)['l02']['pics'] == {'f-trowel-use': 'not'}   # 20: the mark stays until it is undone under its picture
    trowel.locator('button.pick.on').click()
    pg.wait_for_function('!window.__answers.l02')
    assert trowel.locator('.pcell.no').count() == 0   # 21
    fan = block(pg, 'Wall fan regulator')
    assert fan.locator('button.pick').text_content() == 'That is it'   # 22
    ready(pg, fan)
    fan.locator('button.pick').click()
    pg.wait_for_function('window.__answers.l03')
    assert answers(pg)['l03']['pics'] == {'t0000000000c1': 'use'} and fan.locator('.pcell.sel').count() == 1   # 23
    # the groups fold
    mason = block(pg, 'The mason')
    heads.nth(1).click()
    assert mason.is_hidden() and heads.nth(1).get_attribute('aria-expanded') == 'false'   # 24
    heads.nth(1).click()
    assert mason.is_visible()   # 25
    brick = block(pg, 'Brick (a material)')
    brick.locator('.acts > button', has_text='Leave it out').click()
    pg.wait_for_function('window.__answers.l06')
    assert brick.is_hidden() and heads.nth(3).locator('.count').text_content() == '1 line, none to answer'   # 26: a group whose lines are all answered folds
    pg.locator('#dots .dot').nth(5).click()
    assert brick.is_visible()   # 27: its number in the bar opens it again
    first.locator('.acts button').first.click()
    pg.wait_for_function("window.__answers.l01 && window.__answers.l01.choice === 'accept_all'")
    assert answers(pg)['l01']['key'] == 'refs:proposals'   # 28
    # the large picture still opens, and closes
    trowel.locator('button.pic').first.click()
    assert pg.locator('.zoom').count() == 1   # 29
    pg.keyboard.press('Escape')
    assert pg.locator('.zoom').count() == 0 and no_side_scroll(pg)   # 30
    pg.close()


@pytest.mark.parametrize('view,scheme', [('desktop', 'light'), ('phone', 'dark')])
def test_step_2_of_a_v2_round_on_the_page(monkeypatch, browser, view, scheme):
    film = Film(monkeypatch, '2')
    film.inputs['T_LAY'] = [{'ref': 'f-trowel-side', 'role': 'footage', 'view': 'side'}]
    film.change(lambda s: (s['references'].pop('s-street-1-3'), [r.pop('check') for r in s['references'].values() if r.get('set') == 's-mason-1']))
    pg = show(browser, doc(film.page()), view, scheme)
    assert [t.split(' ', 1)[1] for t in pg.locator('button.ghead span:first-child').all_text_contents()] == ['Doubtful: look at these first', 'People', 'Not ready yet', 'Recorded']   # 1
    rest = pg.locator('section.item').first
    assert rest.locator('.acts > button').all_text_contents() == ['Make the other 2 sets (paid, about ₹70)', 'Leave these 2 out']   # 2
    lay = block(pg, 'Laying a brick')
    assert lay.locator('.note strong').text_content() == "The program's check (Gemini): it found faults." and lay.locator('.note li').all_text_contents() == ['Picture B: the action is shown: A tool lying still; no hand.']   # 3
    assert lay.locator('p.prop').text_content().startswith('Claude proposes: Correct it (paid, about ₹35: the set is made again). Picture B shows no hand at work.')   # 4
    notes = lay.locator('details.group', has=pg.locator('summary', has_text="The image model's notes (1 source)"))
    assert notes.count() == 1 and notes.evaluate('d => d.open') is False and 'I drew bamboo' in notes.text_content()   # 5: folded
    cells = lay.locator('.pcell')
    assert cells.first.locator('.pnote').all_text_contents() == ['To compare with'] and cells.first.locator('button.pick').count() == 0 and 'ref' in cells.first.get_attribute('class')   # 6: the footage picture, to compare with
    assert lay.locator('button.pick').all_text_contents() == ['Use A', 'Use B', 'Use C'] and lay.locator('.pcell .tag').all_text_contents() == ['Weak']   # 7
    ready(pg, lay)
    lay.locator('button.pick', has_text='Use B').click()
    pg.wait_for_function('Object.keys(window.__answers).length === 1')
    a = list(answers(pg).values())[0]
    assert a['choice'] == 'use:s-t_lay-1-2' and 'pics' not in a and lay.locator('.pcell.sel button.pick').text_content() == 'Chosen'   # 8: a set picture is the line's answer, as before
    street = block(pg, 'The street')
    assert street.locator('p.changed').text_content() == '2 of 3 pictures came back; missing: its fixed things.'   # 9
    mason = block(pg, 'The mason')
    assert "The program's check (Gemini): the check did not run." in mason.locator('.body').text_content()   # 10
    assert street.locator('p.said', has_text="The program's check (Gemini): passed.").count() == 1   # 11: one line when it passed
    brick = block(pg, 'Brick (a material)')
    pg.locator('button.ghead').nth(2).click()   # "Not ready yet" has nothing to answer: folded until opened
    assert brick.is_visible() and brick.locator('.head .tag').text_content() == 'Not ordered' and 'Not ordered yet' in brick.locator('.body').text_content()   # 12
    assert no_side_scroll(pg)   # 13
    assert pg.locator('#dots .dot.rec').first.evaluate('e => e.offsetWidth') == 28   # 14: the proposal's style leaves the progress dots alone
    pg.close()


def test_a_set_made_again_shows_the_set_before_folded_and_the_operators_words(monkeypatch, browser):
    film = Film(monkeypatch, '2', session=F.session('complete'))
    film.change(remade)
    pg = show(browser, doc(film.page()))
    lay = block(pg, 'Laying a brick')
    before = lay.locator('details.group', has=pg.locator('summary', has_text='The set before'))
    assert before.count() == 1 and before.evaluate('d => d.open') is False and before.locator('button.pic').count() == 3   # 1
    asked = lay.locator('details.changed')
    assert asked.evaluate('d => d.open') is True and 'Made again as you asked: "Show the hand pressing the brick down."' in asked.text_content()   # 2
    pg.close()


def test_the_lines_claude_is_looking_at_say_so(monkeypatch, browser):
    pg = show(browser, doc(Film(monkeypatch, 'looking').page()))
    pg.locator('button.ghead').first.click()
    mason = block(pg, 'The mason')
    assert mason.locator('.head .tag').text_content() == 'Claude is looking' and 'Claude is looking at it.' in mason.text_content() and mason.locator('button.pic').count() == 0   # 1
    pg.close()


@pytest.mark.parametrize('view', ['desktop', 'phone'])
def test_a_line_of_an_older_round_draws_as_before(monkeypatch, browser, view):
    pg = show(browser, doc(Film(monkeypatch, session=older_step1()).page()), view)
    assert pg.locator('button.ghead').count() == 0 and pg.locator('p.prop').count() == 0 and pg.locator('.pnote').count() == 0 and pg.locator('.pcell').count() == 0   # 1: none of the new parts
    trowel = block(pg, "Mason's trowel")
    assert trowel.locator('.acts > button').all_text_contents() == ['Yes, use it', 'Leave it out'] and trowel.locator('button.pic').all_text_contents() == ['Footage picture 1', 'Footage picture 2']   # 2
    assert trowel.locator('.acts textarea').get_attribute('placeholder').startswith('Add a comment (optional). It is kept with your answer')   # 3
    assert pg.locator('section.item').count() == 7 and no_side_scroll(pg)   # 4
    pg.close()
    pg = show(browser, doc(Film(monkeypatch, session=F.older_session()).page()), view)
    street = block(pg, 'The street')
    assert street.locator('button.pick').all_text_contents() == ['Choose A', 'Choose B', 'Choose C'] and pg.locator('button.ghead').count() == 0   # 5
    ready(pg, street)
    street.locator('button.pick').first.click()
    pg.wait_for_function('Object.keys(window.__answers).length === 1')
    a = list(answers(pg).values())[0]
    assert a['choice'] == 'use:s-street-1' and 'pics' not in a and street.locator('button.pick.on').text_content() == 'Chosen' and street.locator('.pcell.sel').count() == 1   # 6
    pg.close()
