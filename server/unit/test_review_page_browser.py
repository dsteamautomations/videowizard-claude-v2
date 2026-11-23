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
from test_design127_review_pure import USER, items_of, saved, session_store
from test_review_page import FakeConn, RUN

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


def view(store):
    cues = S.slide_cues({'items': items_of()[0]}, 25)
    return {'run': {'code': 'VW-9', 'title': 'Film', 'status': 'open', 'stage': 'master', 'open_defects': []}, **S.review_view(FakeConn({}), store, RUN),
            'film': {'key': 'run-1/stage2/review.mp4', 'duration_s': 30.0, 'sha256': 's'}, 'cues': cues}


def act(store, body):
    """What web._review_act does, without the sign-in and the database."""
    a = body.get('action')
    if a == 'decide':
        out = S.decide(FakeConn({}), store, USER, RUN, body.get('slide'), str(body.get('decision') or ''), str(body.get('note') or ''), body.get('edit') or None, body.get('sub_clip_id') or None)
        return {**out, 'view': view(store)}
    return S.others(store, RUN, body.get('slide')) if a == 'others' else S.trim_room(store, RUN, body.get('slide'))


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def open_page(browser, store, review_source=None):
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.errors = errors

    def serve(route):
        url = route.request.url
        if url == URL:
            return route.fulfill(status=200, content_type='text/html', body=html_of(review_source))
        if url.endswith('/review/data'):
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(view(store)))
        if url.endswith('/review/act'):
            try:
                return route.fulfill(status=200, content_type='application/json', body=json.dumps(act(store, json.loads(route.request.post_data))))
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
    top = page.locator('#line .st').first
    assert 'Scene 1 is 0.4 s short after the trim. Fix it under the scene before the master film.' in top.inner_text() and 'err' in top.get_attribute('class')
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
