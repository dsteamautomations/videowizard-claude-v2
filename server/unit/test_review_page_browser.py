"""SK, 23 Nov 2026 (VW-25, plan of action Phase 4): the review page in a real browser (Chromium, Playwright), on a copy of the page: no server,
no database, no network. The page's posts are answered by the same server functions the live routes call (stage.decide, others, trim_room,
review_view) on the small film of test_design127_review_pure. The film element is a stand-in (no video file): the test moves its clock.
- Other clips and Find footage list the pieces; "Use this" records the swap on that row only.
- A trim is typed in seconds; a refused trim says what the shot can take; a scene out of balance is named, one click hands the time over,
  and "all answered" waits for it.
- The pause fault SK reported: Play pressed on the film (or a click on a row) while it waited for an answer left the wait set, and the film
  never stopped again. The last test shows the fault on the page as it was before this change, and that it is gone."""
import json
import subprocess
from pathlib import Path

import pytest

pytest.importorskip('playwright')
import jinja2
from playwright.sync_api import sync_playwright

from app.errors import Problem
from app.stage2 import stage as S
from test_design127_review_pure import USER, answer_all, items_of, saved, session_store
from test_review_page import FakeConn, RUN
from test_vw25_review_page_pure import fit_store

SERVER = Path(__file__).resolve().parents[1]
TEMPLATES = SERVER / 'app' / 'templates'
URL = 'http://vw.test/runs/VW-9/review'
FILM = '''() => { const f = document.getElementById('film'); let p = true, t = 0;
  Object.defineProperty(f, 'paused', {get: () => p}); Object.defineProperty(f, 'currentTime', {get: () => t, set: v => { t = v; }});
  f.play = () => { p = false; f.dispatchEvent(new Event('play')); return Promise.resolve(); }; f.pause = () => { p = true; };
  window.tick = v => { t = v; f.dispatchEvent(new Event('timeupdate')); }; }'''


def html_of(review_source=None):
    """The page as the server renders it; review_source: the text of review.html to test instead of the working copy."""
    loader = jinja2.FileSystemLoader(str(TEMPLATES))
    if review_source is not None:
        loader = jinja2.ChoiceLoader([jinja2.DictLoader({'review.html': review_source}), loader])
    env = jinja2.Environment(loader=loader, autoescape=True)
    env.globals['version'] = 't'
    return env.get_template('review.html').render(user={'name': 'SK', 'role': 'Admin'}, run={'code': 'VW-9', 'title': 'Film'})


def view(store, film=True, stage='master'):
    cues = S.slide_cues({'items': items_of()[0]}, 25)
    return {'run': {'code': 'VW-9', 'title': 'Film', 'status': 'open', 'stage': stage, 'open_defects': []}, **S.review_view(FakeConn({}), store, RUN),
            **({'film': {'key': 'run-1/stage2/review.mp4', 'duration_s': 30.0, 'sha256': 's'}, 'cues': cues} if film else {})}


def act(store, body, **shown):
    """What web._review_act does, without the sign-in and the database."""
    a = body.get('action')
    if a == 'decide':
        out = S.decide(FakeConn({}), store, USER, RUN, body.get('slide'), str(body.get('decision') or ''), str(body.get('note') or ''), body.get('edit') or None, body.get('sub_clip_id') or None)
        return {**out, 'view': view(store, **shown)}
    return S.others(store, RUN, body.get('slide')) if a == 'others' else S.trim_room(store, RUN, body.get('slide'))


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def open_page(browser, store, review_source=None, width=1400, height=900, **shown):
    """shown: film=False for a version with no review film yet, stage='options' for the page before the first answer."""
    page = browser.new_page(viewport={'width': width, 'height': height})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.errors = errors

    def serve(route):
        url = route.request.url
        if url == URL:
            return route.fulfill(status=200, content_type='text/html', body=html_of(review_source))
        if url.endswith('/review/data'):
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(view(store, **shown)))
        if url.endswith('/review/act'):
            try:
                return route.fulfill(status=200, content_type='application/json', body=json.dumps(act(store, json.loads(route.request.post_data), **shown)))
            except Problem as e:
                return route.fulfill(status=422, content_type='application/json', body=json.dumps({'message': e.message}))
        if '/static/style.css' in url:
            return route.fulfill(status=200, content_type='text/css', body=(SERVER / 'app' / 'static' / 'style.css').read_text(encoding='utf-8'))
        return route.fulfill(status=404, body='')
    page.route('**/*', serve)
    page.goto(URL)
    page.wait_for_selector('.row[data-slide="1.2"]')
    page.evaluate(FILM)
    return page


def with_spare_piece(store, **more):
    """c5 becomes a piece that fits scenes 1 and 2 by chapter; c1 fits scene 1 too (it is already in the cut)."""
    pk = json.loads(store.files['p'])
    pk['sub_clips'][4].update(fit_kinds={'BEAT_01': 'chapter', 'BEAT_02': 'chapter'}, eligibility='ELIGIBLE_AS_IS', grade='A', what='A mason lays bricks.', process_stage='Laying', **more)
    pk['sub_clips'][0].update(fit_kinds={'BEAT_01': 'chapter'}, eligibility='ELIGIBLE_AS_IS', grade='B')
    store.files['p'] = json.dumps(pk).encode('utf-8')
    return store


def row(page, slide):
    return page.locator(f'.row[data-slide="{slide}"]')


def test_other_clips_lists_the_pieces_and_use_this_changes_that_row_only(browser):
    store = with_spare_piece(session_store())
    page = open_page(browser, store)
    row(page, '1.2').get_by_role('button', name='Keep').click()
    page.wait_for_function("document.querySelector('.row[data-slide=\"1.2\"] .ans')")
    row(page, '1.3').get_by_role('button', name='Other clips').click()
    page.wait_for_selector('.oth .pc')
    pieces = page.locator('.oth .pc')
    assert pieces.count() == 2
    assert 'C5.MP4 · grade A' in pieces.nth(0).inner_text() and 'from the same chapter · chapter “Laying”' in pieces.nth(0).inner_text() and 'A mason lays bricks.' in pieces.nth(0).inner_text()
    assert pieces.nth(0).locator('video').get_attribute('src') == '/runs/VW-9/film/run-1/media/C5.MP4#t=0,3'   # the part of the clip that would be used
    assert 'Cannot be used: already in the cut' in pieces.nth(1).inner_text() and pieces.nth(1).locator('button.use').count() == 0
    pieces.nth(0).get_by_role('button', name='Use this').click()
    page.wait_for_function("(document.querySelector('.row[data-slide=\"1.3\"] .ans')||{}).textContent==='Other clip: C5.MP4'")
    d = saved(store)['decisions']
    assert d['1.3']['action'] == 'SWAP' and d['1.3']['swap']['sub_clip_id'] == 'c5:S' and d['1.2']['action'] == 'KEEP' and set(d) == {'1.2', '1.3'}   # no other answer changed
    assert 'on' in row(page, '1.3').get_by_role('button', name='Other clips').get_attribute('class') and page.locator('.oth').count() == 0
    row(page, '1.3').get_by_role('button', name='Other clips').click()                     # opened again: the chosen piece is marked
    page.wait_for_selector('.oth .pc.sel')
    assert 'In use here' in page.locator('.oth .pc.sel').inner_text() and not page.errors


def test_find_footage_on_an_all_ai_scene_opens_the_same_list(browser):
    store = session_store()
    page = open_page(browser, store)
    row(page, '2.1').get_by_role('button', name='Find footage').click()
    page.wait_for_selector('.oth')
    page.wait_for_function("document.querySelector('.oth').textContent.includes('No clip fits this scene. Keep AI.')")
    assert saved(store)['decisions'] == {}                                                 # looking records nothing
    page.locator('.oth button.ask').click()                                                # the older way stays reachable: the assistant is asked
    page.wait_for_function("(document.querySelector('.row[data-slide=\"2.1\"] .ans')||{}).textContent==='Find footage: the assistant is asked'")
    with_spare_piece(store)
    row(page, '2.1').get_by_role('button', name='Find footage').click()
    page.wait_for_selector('.oth .pc button.use')
    page.locator('.oth .pc button.use').click()
    page.wait_for_function("(document.querySelector('.row[data-slide=\"2.1\"] .ans')||{}).textContent==='Other clip: C5.MP4'")
    assert saved(store)['decisions']['2.1']['swap']['timeline_frames'] == 100 and not page.errors


def test_a_trim_is_typed_in_seconds_and_a_scene_out_of_balance_is_named_and_fixed_with_one_click(browser):
    store = session_store()
    page = open_page(browser, store)
    for slide in ('1.3', '3.1'):
        row(page, slide).get_by_role('button', name='Keep', exact=True).click()
        page.wait_for_function(f"document.querySelector('.row[data-slide=\"{slide}\"] .ans')")
    row(page, '2.1').get_by_role('button', name='Keep AI').click()
    page.wait_for_function("document.querySelector('.row[data-slide=\"2.1\"] .ans')")
    row(page, '1.2').get_by_role('button', name='Trim').click()
    page.wait_for_function("(document.querySelector('.form .room')||{}).textContent==='This shot: 3.0 s. It can lose up to 2.0 s (start up to 2.0 s later, end up to 2.0 s earlier). It can grow by up to 5.0 s (start up to 0.0 s earlier, end up to 5.0 s later).'")
    inputs = page.locator('.form input')
    inputs.nth(0).fill('2.5')                                                              # more than the shot can lose
    page.locator('.form button.go').click()
    page.wait_for_function("document.getElementById('fmsg').textContent.includes('shorter than its hold')")
    assert 'It can lose up to 2.0 s' in page.locator('#fmsg').inner_text() and page.locator('.form .room').count() == 1 and '1.2' not in saved(store)['decisions']   # refused, said why, the form stays
    inputs = page.locator('.form input')
    inputs.nth(0).fill('0')
    inputs.nth(1).fill('0.4')
    page.locator('.form button.go').click()
    page.wait_for_selector('.bal')
    assert row(page, '1.2').locator('.ans').inner_text() == 'Trim: ends 0.4 s earlier' and saved(store)['decisions']['1.2']['edit'] == 'in:0,out:-10'
    assert page.locator('.bal').inner_text().replace('\n', ' ').startswith('Scene 1 is 0.4 s short after the trim. Give 0.4 s to:')
    assert [b.inner_text() for b in page.locator('.bal button').all()] == ['Shot 2 (undo its trim)', 'Shot 3']
    top, red = page.locator('#line .st').nth(0), page.locator('#line .st').nth(1)   # 25 Nov 2026 (VW-25 issue 4): the count first, the red scene line with it (it replaced the count before)
    assert top.inner_text().startswith('4 of 4 answered.') and 'err' not in top.get_attribute('class')
    assert red.inner_text() == 'Scene 1 is 0.4 s short after the trim. Fix it under the scene before the master film.' and 'err' in red.get_attribute('class')
    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    red.locator('a.go').click()                                                            # the scene's line is a link to the scene
    assert page.evaluate(SEEN, ['.head', '1'])['seen']
    assert 'All 4 answered' not in page.locator('#app').inner_text() and 'The master film cannot be built until each scene adds up' in page.locator('#action').inner_text()   # every shot is answered, and the page does not say "build"
    page.locator('.bal button', has_text='Shot 3').click()
    page.wait_for_function("!document.querySelector('.bal')")
    assert row(page, '1.3').locator('.ans').inner_text() == 'Trim: ends 0.4 s later' and 'All 4 answered' in page.locator('#line .st').first.inner_text()
    S.build_master(FakeConn({}), store, USER, RUN)                                          # and the master builds
    assert not page.errors


PAUSE = '''async () => {
  const f = document.getElementById('film'), wait = document.getElementById('wait'), out = {};
  const click = async (slide, name) => { [...document.querySelectorAll('.row[data-slide="' + slide + '"] button')].find(b => b.textContent === name).click(); await new Promise(r => setTimeout(r, 300)); };
  f.play(); tick(9.9);   out.stops_at_the_first_shot = f.paused && !wait.hidden;
  f.play(); await 0;     out.play_on_the_film_continues = !f.paused && wait.hidden;
  tick(12.9);            out.stops_at_the_next_shot = f.paused && !wait.hidden;
  await click('1.3', 'Reject'); out.goes_on_after_the_answer = !f.paused && wait.hidden;
  tick(18.9);            out.stops_after_the_alternative = f.paused && !wait.hidden;
  document.querySelector('.row[data-slide="3.1"] .t').click(); await 0; out.a_click_on_a_row_ends_the_wait = !f.paused && wait.hidden;
  tick(32.9);            out.stops_at_the_row_clicked = f.paused && !wait.hidden;
  tick(18.9); await click('1.3', 'Keep'); f.pause(); tick(18.9);   // back at the alternative, which is now off: nothing to wait for
  out.no_wait_for_an_alternative_that_is_off = wait.hidden || !/Alternative/.test(wait.textContent);
  return out; }'''


def test_the_film_stops_at_every_shot_after_play_on_the_film_or_a_click_on_a_row(browser):
    page = open_page(browser, session_store())
    got = page.evaluate(PAUSE)
    assert all(got.values()), got
    old = subprocess.run(['git', 'show', 'HEAD:server/app/templates/review.html'], capture_output=True, text=True, encoding='utf-8', cwd=SERVER)
    if old.returncode:
        pytest.skip('the page before this change is not in git here')
    before = open_page(browser, session_store(), old.stdout).evaluate(PAUSE)
    assert before['stops_at_the_first_shot'] and not before['stops_at_the_next_shot'], before   # the fault SK saw: after Play on the film it never stopped again


# ---------- SK, 25 Nov 2026: set A of design/_work/vw25-fixes-requirements-25-nov.md (VW-25 issues 1, 3a, 4, 5) ----------

BOX = """([slide, inner]) => { const r = document.querySelector('.row[data-slide="' + slide + '"]' + (inner ? ' ' + inner : '')).getBoundingClientRect();
  return {x: r.left, y: r.top, w: r.width, b: r.bottom, r: r.right}; }"""
SEEN = """([kind, slide]) => { const el = document.querySelector(kind + '[data-slide="' + slide + '"]'), r = el.getBoundingClientRect(), f = document.getElementById('film');
  const top = document.querySelector('.rv .top').getBoundingClientRect().bottom, foot = document.querySelector('.rv .foot').getBoundingClientRect().top;
  return {seen: r.top >= top - 1 && r.bottom <= foot + 1, off_middle: Math.abs((r.top + r.bottom) / 2 - innerHeight / 2), cur: el.classList.contains('cur'),
          outlined: [...document.querySelectorAll('.row.cur')].map(e => e.dataset.slide), at: f.currentTime, playing: !f.paused}; }"""


def box(page, slide, inner=''):
    return page.evaluate(BOX, [slide, inner])


def reject_with(page, slide, note):
    """Reject, then the note typed in the box that opens."""
    row(page, slide).get_by_role('button', name='Reject').click()
    page.locator(f'[id="f-{slide}"] input').fill(note)
    page.locator(f'[id="f-{slide}"] button.go').click()
    page.wait_for_function("s => (document.querySelector('.row[data-slide=\"' + s + '\"] .ans') || {textContent: ''}).textContent.includes(' · ')", arg=slide)


def test_the_text_of_a_card_keeps_its_width_whatever_the_note_and_the_answer_is_a_line_of_its_own(browser):
    """VW-25 issue 1 (R1). The older way, retired: the answer and its note in the button column, which a long note widened."""
    page = open_page(browser, session_store())
    note = ('We need to show the finished filler slab here, seen from below. ' * 6)[:300].strip()
    reject_with(page, '1.3', note)
    card, text, plain = box(page, '1.3'), box(page, '1.3', '.info'), box(page, '1.2', '.info')
    assert text['w'] >= 0.7 * card['w'] and abs(text['w'] - plain['w']) < 1                # as wide as on a card with no note
    ans, btns = box(page, '1.3', '.ans'), box(page, '1.3', '.btns')
    assert btns['x'] >= text['r'] and ans['y'] >= text['b'] and ans['y'] >= btns['b']       # the buttons beside the text; the answer under both
    assert abs(ans['x'] - text['x']) < 1 and ans['w'] >= 0.9 * card['w']                    # left-aligned, the full width
    assert row(page, '1.3').locator('.ans').inner_text() == 'REJECT · ' + note
    assert page.evaluate("[...document.querySelectorAll('.btns')].every(b => [...b.children].every(c => c.tagName === 'BUTTON'))")   # the right column holds the buttons only
    reject_with(page, '1.2', 'https://example.com/' + 'a' * 480)                            # 500 characters in one piece: it wraps, the card does not grow sideways
    wide = page.evaluate("(() => { const r = document.querySelector('.row[data-slide=\"1.2\"]'); return [r.scrollWidth, r.clientWidth, document.documentElement.scrollWidth, innerWidth]; })()")
    assert wide[0] <= wide[1] and wide[2] <= wide[3] and abs(box(page, '1.2')['w'] - card['w']) < 1 and abs(box(page, '1.2', '.info')['w'] - plain['w']) < 1
    reject_with(page, '3.1', '<i>x</i> & "q" \'s\'')                                        # shown as text
    assert row(page, '3.1').locator('.ans').inner_text() == 'REJECT · <i>x</i> & "q" \'s\'' and row(page, '3.1').locator('.ans i').count() == 0
    assert not page.errors


def test_the_parts_of_a_card_have_bold_labels_only_where_there_is_text_and_nothing_is_cut_short(browser):
    store = session_store()
    question = ' '.join(f'word{i}' for i in range(90))
    sess = saved(store)
    next(s for s in sess['versions'][0]['slides'] if s['no'] == '3.1')['note']['question'] = question
    store.files['run-1/stage2/session.json'] = json.dumps(sess).encode('utf-8')
    page = open_page(browser, store)
    labels = lambda slide: [x.inner_text() for x in row(page, slide).locator('.lb').all()]
    assert labels('1.2') == ['Clip', 'Words'] and labels('1.1') == ['Words', 'For AI'] and labels('3.1') == ['Clip', 'Words', 'Question'] and labels('1.3A1') == ['Clip', 'Words']
    assert page.evaluate("getComputedStyle(document.querySelector('.row .lb')).fontWeight") == '700'
    assert question in row(page, '3.1').inner_text()                                        # a 90-word question shows whole
    assert row(page, '1.2').locator('.part').count() == 2 and row(page, '3.1').locator('.part').count() == 3
    assert page.evaluate("getComputedStyle(document.querySelectorAll('.row[data-slide=\"1.2\"] .part')[1]).borderTopWidth") == '1px'   # the thin line between the clip and the words
    assert page.evaluate("getComputedStyle(document.querySelectorAll('.row[data-slide=\"1.2\"] .part')[0]).borderTopWidth") == '0px'
    assert page.evaluate("[...document.querySelectorAll('.row .part, .row .info > div, .row .part > div, .row .ans, .row .why')].every(e => e.textContent.trim())")   # no empty lines
    assert row(page, '1.2').locator('.ans, .why').count() == 0                              # no answer yet: no line under the card
    assert page.evaluate("document.querySelector('.row[data-slide=\"1.2\"] .info').lastElementChild.textContent").startswith('Keep uses it, Reject leaves an AI stretch')   # the hint stays last
    assert row(page, '1.1').locator('.why').inner_text() == 'nothing to answer' and row(page, '1.3A1').locator('.why').inner_text() == 'answer Scene 1 · Shot 3 first'
    assert not page.errors


@pytest.mark.parametrize('width', [700, 375])
def test_in_a_narrow_window_the_buttons_go_under_the_text(browser, width):
    page = open_page(browser, session_store(), width=width)
    text, btns = box(page, '1.2', '.info'), box(page, '1.2', '.btns')
    assert btns['y'] >= text['b'] and text['w'] >= btns['w']                                # the text is never narrower than the buttons
    # no card runs off the window (at 375 px the page's own header does, its Theme button: base.html, as before this change)
    assert page.evaluate("[...document.querySelectorAll('.row')].every(r => r.getBoundingClientRect().right <= innerWidth && r.scrollWidth <= r.clientWidth)") and not page.errors


def test_a_part_match_is_labelled_on_its_card_and_an_exact_match_is_not(browser):
    """VW-25 issue 3a (R3a). The older way, retired: no label for a part match."""
    page = open_page(browser, fit_store())
    assert row(page, '1.1').locator('.fit').inner_text() == 'Shows part of what the words say. Not shown: the finished slab'
    assert page.evaluate("document.querySelector('.row[data-slide=\"1.1\"] .fit').nextElementSibling.textContent") == 'ClipC1.MP4'   # before the clip line
    assert row(page, '1.2A1').locator('.fit').inner_text() == 'Shows part of what the words say.'                                      # the study names nothing missing
    assert row(page, '1.2').locator('.fit').count() == 0 and row(page, '1.3').locator('.fit').count() == 0                             # exact; related only
    assert page.locator('.broll').count() == 0                                                                                         # plain, not the large badge
    assert [b.inner_text() for b in row(page, '1.1').locator('.btns button').all()] == ['Keep', 'Reject', 'Trim', 'Other clips']       # the label changes no answer
    row(page, '1.2').get_by_role('button', name='Other clips').click()                      # the operator puts a part-match piece on the exact shot
    page.wait_for_selector('.oth .pc button.use')
    page.locator('.oth .pc', has_text='C5.MP4').get_by_role('button', name='Use this').click()
    page.wait_for_function("(document.querySelector('.row[data-slide=\"1.2\"] .ans')||{}).textContent==='Other clip: C5.MP4 · Shows part of what the words say. Not shown: the second filler'")
    assert row(page, '1.2').locator('.fit').count() == 0 and not page.errors                # said with the clip now in use, not beside the replaced clip's name


def test_what_is_left_is_named_and_each_name_is_a_link_to_its_row(browser):
    """VW-25 issue 4 (R4). The older way, retired: the bare "1 left" and "waiting: 2.1"."""
    store = session_store()
    page = open_page(browser, store, height=420)
    top = lambda: page.locator('#line .st').first.inner_text()
    links = lambda: [a.inner_text() for a in page.locator('#line .st a.go').all()]
    assert top().startswith('0 of 4 answered. 4 left: Scene 1 · Shot 2, Scene 1 · Shot 3, Scene 2 · Shot 1 and 1 more')
    assert links() == ['Scene 1 · Shot 2', 'Scene 1 · Shot 3', 'Scene 2 · Shot 1']
    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    page.locator('#line .st a.go', has_text='Scene 2 · Shot 1').click()
    got = page.evaluate(SEEN, ['.row', '2.1'])
    assert got['seen'] and got['outlined'] == ['2.1'] and got['at'] == 22.0 and got['playing'], got   # in view, outlined, the film moved to it (as a click on the row)
    assert got['off_middle'] < 40, got                                                       # in the middle of the window
    page.locator('#line .st a.go').first.focus()                                                 # the keyboard: Tab to the name, Enter
    page.keyboard.press('Enter')
    got = page.evaluate(SEEN, ['.row', '1.2'])
    assert got['seen'] and got['outlined'] == ['1.2'] and got['at'] == 7.0, got
    row(page, '1.2').get_by_role('button', name='Keep', exact=True).click()
    page.wait_for_function("document.querySelector('#line .st').textContent.startsWith('1 of 4 answered. 3 left: Scene 1 · Shot 3, Scene 2 · Shot 1, Scene 3 · Shot 1')")
    assert ' more' not in top()                                                              # three left: all named
    row(page, '1.3').get_by_role('button', name='Reject').click()                            # its alternative now needs an answer: listed
    page.wait_for_function("document.querySelector('#line .st').textContent.startsWith('2 of 5 answered. 3 left: Scene 1 · Shot 3 · Alternative 1, Scene 2 · Shot 1, Scene 3 · Shot 1')")
    page.locator('#more').click()
    assert 'waiting: Scene 1 · Shot 3 · Alternative 1, Scene 2 · Shot 1, Scene 3 · Shot 1' in page.locator('#line .det').inner_text()   # under Details: names, not numbers
    S.decide(FakeConn({}), store, USER, RUN, '2.1', 'KEEP', '', None)                        # a second person answers a row a moment before the click
    page.locator('#line .st a.go', has_text='Scene 2 · Shot 1').click()
    assert page.evaluate(SEEN, ['.row', '2.1'])['outlined'] == ['2.1']                      # the link still lands on the row
    page.goto(URL)                                                                           # the next reload takes it off the list
    page.wait_for_selector('.row[data-slide="1.2"]')
    assert links() == ['Scene 1 · Shot 3 · Alternative 1', 'Scene 3 · Shot 1'] and not page.errors


def test_the_list_on_a_fresh_page_with_no_film_and_when_nothing_is_left(browser):
    store = session_store()
    sess = saved(store)
    sess['accepted'] = None
    store.files['run-1/stage2/session.json'] = json.dumps(sess).encode('utf-8')
    page = open_page(browser, store, stage='options')                                        # before the first answer: all are left
    assert page.locator('#line .st').first.inner_text().startswith(
        'Answer each shot. Your first answer approves these options. 4 left: Scene 1 · Shot 2, Scene 1 · Shot 3, Scene 2 · Shot 1 and 1 more')
    page = open_page(browser, session_store(), film=False, height=420)                       # no review film: the link scrolls and outlines; the film part is skipped
    page.locator('#line .st a.go', has_text='Scene 2 · Shot 1').click()
    got = page.evaluate(SEEN, ['.row', '2.1'])
    assert got['seen'] and got['outlined'] == ['2.1'] and got['at'] == 0 and not got['playing'] and not page.errors, got
    store = session_store()
    answer_all(store)
    page = open_page(browser, store)                                                         # 0 left: as before, no list
    assert page.locator('#line .st').first.inner_text().startswith('All 4 answered. The assistant builds the master film next.') and page.locator('#line a.go').count() == 0
    S.build_master(FakeConn({}), store, USER, RUN)
    page = open_page(browser, store)                                                         # the answers are closed: no list
    assert page.locator('#line .st').first.inner_text().startswith('Answers closed. The master film is built.')
    page.locator('#more').click()
    assert page.locator('#line a.go').count() == 0 and 'waiting' not in page.locator('#line .det').inner_text() and not page.errors


def test_the_page_says_what_a_reject_note_does(browser):
    """VW-25 issue 5 (R5). The older words, retired: "(a reason is optional)" and "Why? (optional)"."""
    page = open_page(browser, session_store())
    said = page.locator('#action').inner_text()
    assert 'Reject: not this one; an AI stretch takes its place. A note says what the picture should show there. It does not bring another clip: for that use Other clips, and Trim for a shorter cut.' in said
    row(page, '1.2').get_by_role('button', name='Reject').click()
    box_ = page.locator('[id="f-1.2"] input')
    assert box_.get_attribute('placeholder') == 'What should the picture show instead? (optional)'
    assert box_.bounding_box()['width'] >= 300 and box(page, '1.2', '.form button.no')['y'] < box(page, '1.2', '.form input')['b'] and not page.errors   # wide enough for the words; Save and Close stay beside it
