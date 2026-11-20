"""design/217, the page checks: step 6, "Pictures and drawn graphics", `plugin/pages/decisions.html` drawn in a headless browser from a local copy
with the frozen round of the contract (`d217_pictures_round.json`, every kind) and a stand-in for the page's database (no product server). The
stand-in pictures are 16:9; the drawn graphic's video is a short webm the browser records itself. Every label is read from the round file: the
page holds none of its own. The fit: at page areas of 1536 x 510 and 1900 x 830, for every kind, the name, the whole media, the check line, the
question and every answer button are inside the window with no scrolling of the main area. Skipped where Playwright or its browser is not
installed. Set VW_SHOTS to a folder to keep screenshots."""
import base64
import copy
import json
import re
from pathlib import Path

import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import PAGE, SIZES, answers, browser, picture, shot   # noqa: F401 (`browser` is the fixture)

ROUND = json.loads((Path(__file__).with_name('d217_pictures_round.json')).read_text(encoding='utf-8'))
W = ROUND['layout']['words']['pictures']
COST = re.compile(r'[₹$€£]\s?\d|\b\d[\d,.]*\s?(USD|INR|EUR|dollars?|rupees?|cents?)\b|\b(price|priced|paid|(?<!-)costs?)\b', re.I)   # no amount anywhere (D1); the film's own "low-cost homes" is not one
HOST = 'http://vw217.test/'
BLOB = '/_blob/' + 'b' * 32
LARGE = '/_blob/' + 'a' * 32
SIZES.setdefault('fit-small', {'width': 1536, 'height': 510})
SIZES.setdefault('fit-large', {'width': 1900, 'height': 830})
L = {l['line']: l for l in ROUND['lines']}
QUESTION, STYLE, BUILDING, KILN, STEPS, CAVITIES, WALL, HOUSING = (L[f'l0{n}'] for n in range(1, 9))
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
      if (parts[0] === 'pics') return {get: async () => ({exists: !(window.__nopic || []).includes(id), data: () => ({data: window.__pic})})};
      if (parts[0] === 'zoom') return {get: async () => ({exists: !!window.__zoom[id], data: () => ({url: window.__zoom[id]})})};
      return {set: async d => { window.__answers[id] = JSON.parse(JSON.stringify(d)); fire(); }, delete: async () => { delete window.__answers[id]; fire(); }};
    }
  };
  window.claude = {use: async name => { if (name === 'db') return db; throw new Error('not here'); }};
})();
"""
_VIDEO = {}


def big_picture():
    """A 1280 x 720 stand-in for a large copy (16:9)."""
    if 'p' not in _VIDEO:
        import io
        from PIL import Image
        out = io.BytesIO()
        img = Image.new('RGB', (1280, 720), (150, 170, 185))
        img.paste((190, 110, 60), (360, 200, 920, 520))
        img.save(out, 'PNG')
        _VIDEO['p'] = out.getvalue()
    return _VIDEO['p']


def webm(browser):
    """A 1.5 s 16:9 webm, recorded by the browser from a canvas (no file in the repository, no tool outside the browser)."""
    if 'v' not in _VIDEO:
        pg = browser.new_page()
        _VIDEO['v'] = base64.b64decode(pg.evaluate("""async () => {
          const c = document.createElement('canvas'); c.width = 320; c.height = 180; const x = c.getContext('2d');
          const r = new MediaRecorder(c.captureStream(25), {mimeType: 'video/webm'}), parts = [];
          r.ondataavailable = e => parts.push(e.data); let t = 0;
          const tick = setInterval(() => { x.fillStyle = '#e8e2d4'; x.fillRect(0, 0, 320, 180); x.fillStyle = '#b5532f'; x.fillRect(20 + (t++ * 6) % 260, 60, 40, 60); }, 40);
          r.start(); await new Promise(f => setTimeout(f, 1500)); r.stop(); await new Promise(f => r.onstop = f); clearInterval(tick);
          const b = new Uint8Array(await new Blob(parts, {type: 'video/webm'}).arrayBuffer()); let s = ''; b.forEach(v => s += String.fromCharCode(v)); return btoa(s); }"""))
        pg.close()
    return _VIDEO['v']


def doc(change=None):
    d = copy.deepcopy(ROUND)
    if change:
        change({l['line']: l for l in d['lines']}, d)
    return d


def page(browser, d=None, size='fit-large', video=True, scheme='light', nopic=(), large=True):
    """The page file as a document of its own at a test origin (so the video's file store link resolves), drawn with one round."""
    d = d or doc()
    pg = browser.new_page(viewport=SIZES[size], color_scheme=scheme)
    pg.errors = []
    pg.on('console', lambda m: pg.errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: pg.errors.append(str(e)))
    zoom = {p['code']: LARGE for l in d['lines'] for p in l['pics']} if large else {}   # the large copies of the file store
    zoom.update({l['video']['code']: BLOB for l in d['lines'] if (l.get('video') or {}).get('code')} if video else {})   # each drawing's video page copy: `zoom/<code>`, as the tool writes it
    zoom = {(d.get('zoom_docs') or {}).get(k, k): v for k, v in zoom.items()}   # offered again: the document the round names
    html = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
            f"<script>window.__round = {json.dumps(d).replace('</', '<\\/')}; window.__zoom = {json.dumps(zoom)}; window.__nopic = {json.dumps(list(nopic))};"
            f"window.__pic = 'data:image/png;base64,{base64.b64encode(picture()).decode()}';{STUB}</script>" + PAGE.read_text(encoding='utf-8') + '</body></html>')
    clip = webm(browser) if video else b''

    def route(r):
        u = r.request.url
        if u == HOST:
            return r.fulfill(status=200, content_type='text/html', body=html)
        if u == HOST + BLOB[1:] and clip:
            return r.fulfill(status=200, content_type='video/webm', body=clip)
        if u == HOST + LARGE[1:]:
            return r.fulfill(status=200, content_type='image/png', body=big_picture())
        return r.fulfill(status=200, content_type='text/css', body='')   # the fonts' stylesheet: answered empty, no network
    pg.route('**/*', route)
    pg.goto(HOST)
    try:
        pg.wait_for_selector('#smain .swrap', state='attached', timeout=10000)
    except Exception:
        raise AssertionError(f'the page did not draw: {pg.errors}')
    return pg


def go(pg, l):
    pg.locator(f'#srail .srow[data-line="{l["line"]}"]').click()
    pg.wait_for_function('n => (document.querySelector("#smain .sname") || {}).textContent === n', arg=l['name'])
    if l.get('pics'):
        pg.wait_for_function("![...document.querySelectorAll('#pbar button')].some(b => b.disabled)")   # its pictures have shown


def bar(pg):
    return [' '.join(t.split()) for t in pg.locator('#pbar button').all_text_contents()]


def foot(pg):
    return ' '.join(pg.locator('#sfoot > *').all_text_contents())


def rail(pg):
    return pg.locator('#srail > ul:first-of-type .srow').evaluate_all('rs => rs.map(r => [r.querySelector(".sdot").textContent, r.querySelector(".snm").firstChild.textContent])')


def saved(pg, line, choice):
    pg.wait_for_function('([l, c]) => (window.__answers[l] || {}).choice === c', arg=[line, choice])
    return answers(pg)[line]


def clean(pg):
    text = pg.locator('body').inner_text()
    assert not COST.search(text), COST.search(text).group(0)
    assert pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not pg.errors, pg.errors


def inside(pg, sel):
    box = pg.locator(sel).first.bounding_box()
    vp = pg.viewport_size
    assert box and box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= vp['width'] + 0.5 and box['y'] + box['height'] <= vp['height'] + 0.5, (sel, box, vp)
    return box


def btn(l, choice):
    return next(b for b in l['buttons'] if b['choice'] == choice)


# ---------- the fit: every kind, both page areas ----------

@pytest.mark.parametrize('size', ['fit-small', 'fit-large'])
@pytest.mark.parametrize('line', [l['line'] for l in ROUND['lines']])
def test_every_kind_fits_with_no_scrolling(browser, size, line):
    l = L[line]
    pg = page(browser, size=size)
    go(pg, l)
    if l['kind'] == 'drawn' and l['video']['code']:
        pg.wait_for_function("(() => { const v = document.querySelector('#pvideo'); return v && v.readyState >= 2 && !v.paused; })()")
    for sel in ['#smain .sname', '#sansh'] + (['#sbig'] if l['pics'] else []) + (['#pcheck'] if l.get('check') else []):
        inside(pg, sel)
    for i in range(pg.locator('#pbar button').count()):
        inside(pg, f'#pbar button >> nth={i}')
    assert pg.evaluate("(() => { const m = document.querySelector('#smain'); return m.scrollHeight <= m.clientHeight; })()")   # the main area does not scroll
    assert pg.evaluate("(() => { const s = document.querySelector('.sside'); return !s || s.scrollTop === 0; })()")
    # the whole media: every picture of it inside the window, and it gave way only to about 200 px
    for i in range(pg.locator('#sbig .sbigb, #sbig .pvbox').count()):
        inside(pg, f'#sbig :is(.sbigb, .pvbox) >> nth={i}')
    if l['pics'] and l['kind'] != 'steps':
        assert pg.locator('#sbig :is(.sbigb, .pvbox)').first.bounding_box()['height'] >= 195, pg.locator('#sbig :is(.sbigb, .pvbox)').first.bounding_box()
    if l['kind'] == 'steps':   # the steps shrink together: one height, side by side
        boxes = [pg.locator('#sbig .sbigb').nth(i).bounding_box() for i in range(len([p for p in l['pics'] if p['role'] == 'step']))]
        assert len({round(b['height']) for b in boxes}) == 1 and len({round(b['y']) for b in boxes}) == 1 and boxes[0]['height'] >= 80, boxes
    # the captions are never cut: they wrap, and they are in view
    cut = pg.evaluate("""[...document.querySelectorAll('#smain figcaption, #smain .pthl, #smain .pfaults')].filter(e => {
        const s = getComputedStyle(e); return s.textOverflow === 'ellipsis' || e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1; }).map(e => e.textContent)""")
    assert not cut, cut
    for i in range(pg.locator('#sbig figcaption').count()):
        inside(pg, f'#sbig figcaption >> nth={i}')
    shot(pg, f'd217-{size}-{line}-{l["kind"]}')
    clean(pg)
    pg.close()


@pytest.mark.parametrize('size', ['fit-small', 'fit-large'])
def test_what_opens_beside_still_fits(browser, size):
    pg = page(browser, size=size)
    go(pg, KILN)
    pg.locator('#sfootage [data-role="earlier"]').click()                                 # an earlier try beside the picture
    for i in range(2):
        inside(pg, f'#sbig .sbigb >> nth={i}')
    for sel in ('#pcheck', '#sansh'):
        inside(pg, sel)
    for i in range(pg.locator('#pbar button').count()):
        inside(pg, f'#pbar button >> nth={i}')
    go(pg, STEPS)
    pg.locator('#sfootage [data-role="after"]').click()                                   # the footage after joins the steps at the end
    assert pg.locator('#sbig figure').count() == 4
    for i in range(4):
        inside(pg, f'#sbig .sbigb >> nth={i}')
    for i in range(pg.locator('#pbar button').count()):
        inside(pg, f'#pbar button >> nth={i}')
    assert pg.evaluate("(() => { const m = document.querySelector('#smain'); return m.scrollHeight <= m.clientHeight; })()")
    shot(pg, f'd217-{size}-steps-beside')
    pg.close()


# ---------- the screen ----------

def test_the_screen_the_list_the_fold_and_the_count(browser):
    pg = page(browser)
    assert pg.locator('#sets').is_visible() and pg.locator('#things').is_hidden() and pg.locator('#wrap').is_hidden()
    assert pg.locator('#sstep').text_content() == ROUND['step'] and pg.locator('#shelp').text_content() == W['help']
    # only what needs an answer, numbered, in the round's order; the kind under the name
    assert rail(pg) == [[str(n), l['name']] for n, l in enumerate(ROUND['lines'], 1)]
    assert pg.locator('#srail .srow .pkw').all_text_contents() == [' · '.join(x for x in (l['kind_words'], l.get('film_at')) if x) for l in ROUND['lines']]   # the film time under the name, as the trial
    assert pg.locator('#srail .srow[data-line="l03"] .pkw').text_content() == 'A still · 1:35.1'
    assert pg.locator('#srail h2').first.text_content() == W['todo']
    # `layout.coming`: one folded row, not counted
    fold = pg.locator('#srail [data-fold="coming"]')
    assert fold.locator('span').text_content() == W['coming'] and fold.text_content().endswith('4') and pg.locator('#pcoming').count() == 0
    fold.click()
    rows = pg.locator('#pcoming li')
    assert rows.count() == 4 and [rows.nth(i).evaluate('e => e.firstChild.textContent') for i in range(4)] == [c['name'] for c in ROUND['layout']['coming']]
    assert ROUND['layout']['coming'][2]['note'] in rows.nth(2).text_content() and rows.nth(2).get_attribute('data-state') == 'failed'   # design/221 phase 4: the fold lists what could not be made
    assert pg.locator('#pcoming button').count() == 0
    assert foot(pg) == W['foot'].replace('{n}', '0').replace('{m}', '8') + ' ' + W['foot_wait']
    # the first that needs an answer opens; the fonts
    assert pg.locator('#smain .sname').text_content() == QUESTION['name']
    font = pg.evaluate("[getComputedStyle(document.querySelector('#sets')).fontSize, getComputedStyle(document.querySelector('#sets')).fontFamily, getComputedStyle(document.querySelector('#smain .sname')).fontSize, getComputedStyle(document.querySelector('#smain .sname')).fontFamily]")
    assert font[0] == '14px' and font[1].startswith('Inter') and font[2] == '20px' and font[3].startswith('"Space Grotesk"')
    go(pg, BUILDING)
    sizes = pg.evaluate("[...document.querySelectorAll('#smain figcaption, #smain .pthl')].map(e => getComputedStyle(e).fontSize)")
    assert sizes and set(sizes) == {'12px'}
    clean(pg)
    pg.close()


def test_a_question_of_claude(browser):
    pg = page(browser)
    go(pg, QUESTION)
    assert pg.locator('#pfromq').text_content() == QUESTION['from'] and pg.locator('#sansh').text_content() == QUESTION['ask']
    assert bar(pg) == [b['label'] + b['say'] for b in QUESTION['buttons']] and pg.locator('#pbar small').all_text_contents() == [b['say'] for b in QUESTION['buttons']]   # each button says what happens
    assert pg.locator('#pcheck').count() == 0
    assert pg.locator('#sbig figure').count() == 1 and pg.locator('#sfootage').count() == 0
    pg.locator('#pbar [data-choice="c2"]').click()
    got = saved(pg, 'l01', 'c2')
    assert got['key'] == QUESTION['key'] and got['item'] == QUESTION['item'] and got['notes'] == '' and set(got) == {'key', 'item', 'choice', 'notes', 'at'}
    row = pg.locator('#srail .srow[data-line="l01"]')
    assert 'done' in row.get_attribute('class') and row.locator('.sdot').get_attribute('title') == W['done']['answer']
    pg.wait_for_function('n => document.querySelector("#smain .sname").textContent !== n', arg=QUESTION['name'])   # the next opens
    assert pg.locator('#smain .sname').text_content() == STYLE['name']
    pg.close()


def test_a_question_with_no_picture(browser):
    pg = page(browser, doc(lambda l, d: l['l01'].update(pics=[])))
    go(pg, QUESTION)
    assert pg.locator('#sbig').count() == 0 and not pg.locator('#pbar button').first.is_disabled()
    inside(pg, '#pbar button >> nth=1')
    pg.close()


def test_the_style_sheet(browser):
    pg = page(browser)
    go(pg, STYLE)
    assert pg.locator('#pctx').text_content() == STYLE['sub'] and pg.locator('#sansh').text_content() == STYLE['ask']
    assert pg.locator('#pcheck b').text_content() == STYLE['check']['head'] and pg.locator('#pcheck').get_attribute('data-state') == 'pass' and 'bad' not in pg.locator('#pcheck').get_attribute('class')
    assert pg.locator('#pcheck .pby').count() == 0                                            # release 1, B3: the box is closed; who checked is one click away
    pg.locator('#pcheckb').click()
    assert pg.locator('#pcheck .pby').text_content() == STYLE['check']['by']
    assert bar(pg) == [b['label'] for b in STYLE['buttons']] and 'primary' in pg.locator('#pbar [data-choice="yes"]').get_attribute('class')
    # the passed lines and the program's advice: folded under Details, with the server's rows
    heads = pg.locator('.smore .sacc > button span:first-child').all_text_contents()
    assert heads == [STYLE['check']['passed_head'], STYLE['check']['advice_head']] + [d[0] for d in STYLE['details']] and pg.locator('.smore .sbody').count() == 0
    pg.locator('.smore [data-acc="d0"]').click()
    assert pg.locator('.smore .sbody li').all_text_contents() == STYLE['check']['passed']
    pg.locator('#pbar [data-choice="no"]').click()                                        # D7: a bare No, no reason, no question
    got = saved(pg, 'l02', 'no')
    assert got['notes'] == '' and pg.locator('#spanel').count() == 0
    assert btn(STYLE, 'no')['say'] in pg.locator('#sanswer').text_content()
    pg.locator('#sundo').click()                                                          # undo
    pg.wait_for_function('() => !window.__answers.l02')
    assert pg.locator('#sanswer').count() == 0 and 'done' not in (pg.locator('#srail .srow[data-line="l02"]').get_attribute('class') or '')
    pg.close()


def test_a_still_with_footage_only_ever_beside_it(browser):
    pg = page(browser)
    go(pg, BUILDING)
    main = next(p for p in BUILDING['pics'] if p['role'] == 'main')
    assert pg.locator('#sbig figure').count() == 1 and pg.locator('#sbig figcaption').count() == 0 and pg.locator('#sfootage .sth.on .pthl').text_content() == main['label']   # one picture large: named in the row under it
    assert pg.locator('#pctx .pwhere').first.text_content() == BUILDING['where'] and BUILDING['words'] in pg.locator('#pctx').text_content() and BUILDING['words_head'] in pg.locator('#pctx').text_content()
    assert pg.locator('#sfootage h4, .sgrp h4').first.text_content() == BUILDING['foot_head']
    assert pg.locator('#sfootage .sth').evaluate_all('t => t.map(x => x.getAttribute("data-role"))') == ['before', 'main', 'after']   # film order
    pg.locator('#sfootage [data-role="before"]').click()
    figs = pg.locator('#sbig figure')
    assert figs.count() == 2 and figs.nth(0).get_attribute('data-role') == 'main' and figs.nth(1).get_attribute('data-role') == 'before'   # beside, never in its place
    assert pg.locator('#sbig figure >> nth=0').locator('figcaption').text_content() == main['label']
    assert pg.locator('#sbig figure >> nth=1').locator('figcaption').text_content() == BUILDING['pics'][0]['cmp_cap']
    pg.locator('#sfootage [data-role="after"]').click()
    assert figs.count() == 2 and figs.nth(0).get_attribute('data-role') == 'main' and figs.nth(1).get_attribute('data-role') == 'after'
    pg.locator('#scompare').click()
    assert figs.count() == 1 and pg.locator('#scompare').count() == 0
    pg.locator('#pbar [data-choice="yes"]').click()                                       # a passed check: no question
    assert saved(pg, 'l03', 'yes')['notes'] == '' and pg.locator('#spanel').count() == 0
    pg.close()


def test_a_failed_still_asks_once_and_is_marked_against_the_check(browser):
    pg = page(browser)
    go(pg, KILN)
    c = KILN['check']
    assert pg.locator('#pcheck').get_attribute('data-state') == 'fail' and 'bad' in pg.locator('#pcheck').get_attribute('class') and pg.locator('#pcheck b').text_content() == c['head']
    assert pg.locator('#pcheck li').count() == 0 and pg.locator('#pmore').count() == 0       # F1; release 1, B3: one line (this older round's head names the first fault), the rest one click away
    pg.locator('#pcheckb').click()
    assert pg.locator('#pcheck li').all_text_contents() == c['faults'] and pg.locator('#pcheckb').get_attribute('aria-expanded') == 'true'
    assert 'faults' not in KILN['pics'][1] and pg.locator('#sbig .pfaults').count() == 0   # the picture's failed lines are the check's: sent once, said once
    assert pg.locator('#ptry').text_content() == KILN['try']
    assert 'primary' not in (pg.locator('#pbar [data-choice="yes"]').get_attribute('class') or '')
    yes = btn(KILN, 'yes')
    pg.locator('#pbar [data-choice="yes"]').click()                                       # asks once
    assert pg.locator('#spanel label').text_content() == yes['sure']['ask'] and pg.locator('#ssure').text_content() == yes['sure']['go'] and answers(pg) == {}
    assert pg.evaluate('document.activeElement.id') == 'sback'
    pg.locator('#sback').click()
    assert pg.locator('#spanel').count() == 0 and answers(pg) == {}
    pg.locator('#pbar [data-choice="yes"]').click()
    pg.locator('#ssure').click()
    got = saved(pg, 'l04', 'yes')
    assert set(got) == {'key', 'item', 'choice', 'notes', 'at'} and got['notes'] == ''          # the page writes nothing extra
    row = pg.locator('#srail .srow[data-line="l04"]')
    assert 'against' in row.get_attribute('class') and row.locator('.sdot').get_attribute('title') == W['against'] and row.locator('.sdot').text_content() == '!'
    assert W['against'] in pg.locator('#sanswer').text_content() and 'against' in pg.locator('#sanswer').get_attribute('class')
    pg.locator('#sundo').click()
    pg.wait_for_function('() => !window.__answers.l04')
    assert 'against' not in (row.get_attribute('class') or '')
    pg.close()


def test_the_earlier_try_with_its_reason_and_correct_it_with_claudes_lines(browser):
    pg = page(browser)
    go(pg, KILN)
    earlier = KILN['pics'][3]
    assert pg.locator('#sfootage .sth').evaluate_all('t => t.map(x => x.getAttribute("data-role"))') == ['before', 'main', 'after', 'earlier']
    pg.locator('#sfootage [data-role="earlier"]').click()
    side = pg.locator('#sbig figure >> nth=1')
    assert side.get_attribute('data-role') == 'earlier' and side.locator('figcaption').nth(0).text_content() == earlier['cmp_cap'] and side.locator('.pwhy').text_content() == earlier['why']
    fix = btn(KILN, 'correct')
    pg.locator('#pbar [data-choice="correct"]').click()                                   # D3: the box opens with Claude's failed lines, to send or change
    assert pg.locator('#spanel label').text_content() == fix['hint'] and pg.locator('#sfix').input_value() == fix['prefill'] and pg.locator('#sfixsend').text_content() == fix['go']
    pg.locator('#sfix').fill('')
    pg.locator('#sfixsend').click()
    assert pg.locator('#smsg').text_content() == W['words_need'] and answers(pg) == {}
    pg.locator('#sfix').fill('Two distant workers.')
    pg.locator('#sfixsend').click()
    got = saved(pg, 'l04', 'correct')
    assert got['notes'] == 'Two distant workers.' and fix['say'].replace('{words}', 'Two distant workers.') in pg.locator('#sanswer').text_content()
    assert pg.locator('#srail .srow[data-line="l04"] .sdot').get_attribute('title') == W['done']['fix']
    pg.close()


def test_a_graphic_in_steps(browser):
    pg = page(browser)
    go(pg, STEPS)
    steps = [p for p in STEPS['pics'] if p['role'] == 'step']
    assert pg.locator('#sbig figure').count() == 3 and pg.locator('#sbig figure figcaption').all_text_contents() == [p['caption'] for p in steps]   # all side by side
    assert pg.locator('#sbig figure >> nth=2').locator('.pfaults li').all_text_contents() == steps[2]['faults'] and pg.locator('#sbig figure >> nth=2').locator('.pfaults b').text_content() == steps[2]['check_head']
    assert pg.locator('#sbig .pfaults').count() == 1 and pg.locator('#pcap').text_content().startswith(STEPS['strip_head'])
    assert pg.locator('#pcap').bounding_box()['y'] < pg.locator('#sbig').bounding_box()['y']   # the heading of the steps above them
    assert bar(pg) == [b['label'] for b in STEPS['buttons']] == ['Yes, use all 3 steps', 'Correct 1', 'Correct 2', 'Correct 3']   # F2: one per step, no "No"
    assert pg.locator('#sfootage .sth').evaluate_all('t => t.map(x => x.getAttribute("data-role"))') == ['before', 'after', 'earlier']
    pg.locator('#sfootage [data-role="before"]').click()                                  # the footage before joins the row first, in film order
    assert pg.locator('#sbig figure').evaluate_all('f => f.map(x => x.getAttribute("data-role"))') == ['before', 'step', 'step', 'step']
    pg.locator('#pbar [data-choice="yes"]').click()                                       # R3: two steps alike and a fault: asks once
    assert pg.locator('#spanel label').text_content() == btn(STEPS, 'yes')['sure']['ask'] and answers(pg) == {}
    pg.locator('#pbar [data-choice="correct:2"]').click()
    assert pg.locator('#spanel label').text_content() == btn(STEPS, 'correct:2')['hint'] and pg.locator('#sfix').input_value() == ''
    pg.locator('#pbar [data-choice="correct:3"]').click()
    assert pg.locator('#sfix').input_value() == btn(STEPS, 'correct:3')['prefill']
    pg.locator('#sfixsend').click()
    got = saved(pg, 'l05', 'correct:3')
    assert got['notes'] == btn(STEPS, 'correct:3')['prefill']
    pg.close()


@pytest.mark.parametrize('n', [2, 3, 4])
def test_a_graphic_of_two_and_of_four_steps(browser, n):
    def change(l, d):
        s = l['l05']
        steps = [p for p in s['pics'] if p['role'] == 'step']
        while len(steps) < n:
            steps.append({**copy.deepcopy(steps[0]), 'code': f'pfeed{len(steps):08d}', 'n': len(steps) + 1, 'label': f'Step {len(steps) + 1}', 'caption': f'Step {len(steps) + 1}: on \'the words\': one more thing appears.', 'faults': []})
        steps = steps[:n]
        s['pics'] = [p for p in s['pics'] if p['role'] == 'before'] + steps + [p for p in s['pics'] if p['role'] in ('after', 'earlier')]
        s['buttons'] = [{**s['buttons'][0], 'label': f'Yes, use all {n} steps'}] + [{**s['buttons'][1], 'label': f'Correct {i}', 'choice': f'correct:{i}'} for i in range(1, n + 1)]
    for size in ('fit-small', 'fit-large'):
        pg = page(browser, doc(change), size=size)
        go(pg, STEPS)
        assert pg.locator('#sbig figure').count() == n and len(bar(pg)) == n + 1
        boxes = [inside(pg, f'#sbig .sbigb >> nth={i}') for i in range(n)]
        assert len({round(b['height']) for b in boxes}) == 1
        rows = sorted({round(b['y']) for b in boxes})
        if n == 4 and size == 'fit-small':   # 4 steps at 1536 x 510: two rows of two, each large enough to judge
            assert len(rows) == 2 and len({round(b['x']) for b in boxes}) == 2 and boxes[0]['height'] >= 120, boxes
        else:   # 2 and 3 steps, and 4 at 1900 x 830: one row
            assert len(rows) == 1, boxes
        tops = {round(pg.locator(f'#pbar button >> nth={i}').bounding_box()['y']) for i in range(n + 1)}
        assert len(tops) == 1, tops   # the step buttons on one line
        for i in range(n + 1):
            inside(pg, f'#pbar button >> nth={i}')
        assert pg.evaluate("(() => { const m = document.querySelector('#smain'); return m.scrollHeight <= m.clientHeight; })()")
        shot(pg, f'd217-{size}-steps-{n}')
        pg.close()


def test_a_drawn_graphic_plays_on_a_loop_with_no_sound_its_frames_one_click_away(browser):
    pg = page(browser)
    go(pg, CAVITIES)
    pg.wait_for_function("(() => { const v = document.querySelector('#pvideo'); return v && v.readyState >= 2 && !v.paused; })()")
    v = pg.evaluate("(() => { const v = document.querySelector('#pvideo'); return [v.loop, v.muted, v.getAttribute('aria-label'), v.src.endsWith('" + BLOB + "')]; })()")
    assert v == [True, True, CAVITIES['video']['label'], True]                             # D6
    assert pg.locator('#pfinish').text_content() == CAVITIES['finish'] and pg.locator('#sfootage [data-role="sheet"] .pthl').text_content() == CAVITIES['pics'][1]['label']
    assert pg.locator('#pcheck b').text_content() == CAVITIES['check']['head'] and pg.locator('#pcheck .pby').count() == 0   # release 1, B3: closed
    pg.locator('#pcheckb').click()
    assert pg.locator('#pcheck .pby').text_content() == CAVITIES['check']['by']
    pg.locator('#pcheckb').click()
    assert 'primary' in pg.locator('#pbar [data-choice="select"]').get_attribute('class') and 'danger' in pg.locator('#pbar [data-choice="reject"]').get_attribute('class')
    assert bar(pg) == [b['label'] for b in CAVITIES['buttons']]
    pg.locator('#pframes').click()                                                       # the frame sheet, one click away
    assert pg.locator('#pvideo').count() == 0 and pg.locator('#sbig figure').get_attribute('data-role') == 'sheet' and pg.locator('#pframes').text_content() == W['video']
    pg.locator('#pframes').click()
    assert pg.locator('#pvideo').count() == 1 and pg.locator('#pframes').text_content() == W['frames']
    pg.locator('#sfootage [data-role="after"]').click()                                   # footage beside the video
    assert pg.locator('#sbig figure').evaluate_all('f => f.map(x => x.getAttribute("data-role"))') == ['video', 'after']
    pg.locator('#pbar [data-choice="plain"]').click()                                     # D8: no confirmation
    assert saved(pg, 'l06', 'plain')['notes'] == '' and pg.locator('#srail .srow[data-line="l06"] .sdot').get_attribute('title') == W['done']['plain']
    pg.close()


def test_a_drawn_graphic_with_open_rules_and_no_video_needs_a_reason(browser):
    pg = page(browser)
    go(pg, WALL)
    assert pg.locator('#pvideo').count() == 0 and pg.locator('#sbig figure').get_attribute('data-role') == 'sheet' and pg.locator('#pnone').text_content() == WALL['video']['none']
    assert pg.locator('#pframes').count() == 0 and pg.locator('#pfinish').count() == 0
    pg.locator('#pcheckb').click()                                                        # release 1, B3: the box is closed; one click
    assert pg.locator('#pcheck li').all_text_contents() == WALL['check']['faults'] and pg.locator('#pmore').count() == 0   # the open rules in full
    assert bar(pg) == ['Select: use it in the film', 'Reject'] and pg.locator('#pbar [data-act="plain"]').count() == 0   # no finish: no "Take the effect away"
    sel = btn(WALL, 'select')
    pg.locator('#pbar [data-choice="select"]').click()                                    # F3: the reason is asked
    assert pg.locator('#pheld').text_content() == WALL['held'] and pg.locator('#spanel label').text_content() == sel['hint'] and pg.locator('#sfixsend').text_content() == sel['go']
    pg.locator('#sfixsend').click()
    assert pg.locator('#smsg').text_content() == sel['need'] and answers(pg) == {}
    pg.locator('#sfix').fill('The end frames hold long enough.')
    pg.locator('#sfixsend').click()
    got = saved(pg, 'l07', 'select')
    assert got['notes'] == 'The end frames hold long enough.' and sel['say'].replace('{words}', got['notes']) in pg.locator('#sanswer').text_content()
    pg.close()


def test_the_servers_video_field_a_code_its_zoom_document_offered_again_and_none(browser):
    """design/217: the server's `video` of a drawn line: a code `v` + 12 hex whose page copy the tool uploads and links as `zoom/<code>` (or the
    document `zoom_docs` names when the pictures were offered again); `code` "" with `none` when no copy could be made: the frames, with that sentence."""
    code = 'v' + '0123456789ab'
    pg = page(browser, doc(lambda l, d: (l['l06']['video'].update(code=code), d.update(zoom_docs={code: code + '-1'}))))
    go(pg, CAVITIES)
    pg.wait_for_function("(() => { const v = document.querySelector('#pvideo'); return v && v.readyState >= 2 && !v.paused; })()")
    assert pg.evaluate("document.querySelector('#pvideo').src").endswith(BLOB) and pg.locator('#pnone').count() == 0
    pg.close()
    pg = page(browser, doc(lambda l, d: l['l06']['video'].update(code='', none=WALL['video']['none'])))
    go(pg, CAVITIES)
    assert pg.locator('#pvideo').count() == 0 and pg.locator('#pnone').text_content() == WALL['video']['none'] and pg.locator('#sbig figure').get_attribute('data-role') == 'sheet'
    assert pg.locator('#pframes').count() == 0 and pg.locator('#pfinish').text_content() == CAVITIES['finish']
    pg.close()


def test_the_video_that_cannot_be_shown_falls_back_to_its_frames(browser):
    pg = page(browser, video=False)                                                      # the zoom link of the video is missing
    go(pg, CAVITIES)
    pg.wait_for_selector('#pnone')
    assert pg.locator('#pvideo').count() == 0 and pg.locator('#pnone').text_content() == W['video_bad'] and pg.locator('#pframes').count() == 0
    pg.close()


def test_a_still_not_checked_and_with_no_footage_before(browser):
    pg = page(browser)
    go(pg, HOUSING)
    assert pg.locator('#pcheck').get_attribute('data-state') == 'not_checked' and 'doubt' in pg.locator('#pcheck').get_attribute('class') and pg.locator('#pcheck b').text_content() == HOUSING['check']['head']
    assert pg.locator('#pcheck .pby').count() == 0 and 'primary' not in (pg.locator('#pbar [data-choice="yes"]').get_attribute('class') or '')
    assert pg.locator('#sfootage .sth').evaluate_all('t => t.map(x => x.getAttribute("data-role"))') == ['main', 'after']
    pg.locator('#pbar [data-choice="yes"]').click()                                       # no `sure`: no question
    assert saved(pg, 'l08', 'yes') and pg.locator('#spanel').count() == 0
    pg.close()


def test_the_end_card_lists_what_will_happen(browser):
    pg = page(browser)
    plan = [(QUESTION, 'c1', None), (STYLE, 'yes', None), (BUILDING, 'no', None), (KILN, 'yes', 'sure'), (STEPS, 'correct:1', 'Fewer icons.'), (CAVITIES, 'select', None), (WALL, 'reject', ''), (HOUSING, 'yes', None)]
    for l, choice, more in plan:
        go(pg, l)
        pg.locator(f'#pbar [data-choice="{choice}"]').click()
        if more == 'sure':
            pg.locator('#ssure').click()
        elif more is not None:
            if more:
                pg.locator('#sfix').fill(more)
            pg.locator('#sfixsend').click()
        saved(pg, l['line'], choice)
    assert foot(pg) == W['foot'].replace('{n}', '8').replace('{m}', '8') + ' ' + W['foot_done']
    pg.wait_for_selector('#send li')
    items = [' '.join(t.split()) for t in pg.locator('#send li').all_text_contents()]
    assert pg.locator('#send h2').text_content() == W['end_head'] and len(items) == 8
    assert items[0] == f"{QUESTION['name']}: {btn(QUESTION, 'c1')['say']}"
    assert items[3] == f"{KILN['name']}: {btn(KILN, 'yes')['say']} ({W['against']})"
    assert items[4] == f"{STEPS['name']}: " + btn(STEPS, 'correct:1')['say'].replace('{words}', 'Fewer icons.')
    assert items[6] == f"{WALL['name']}: " + btn(WALL, 'reject')['say'].replace('{words}', btn(WALL, 'reject')['prefill'])
    assert W['end_foot'] in pg.locator('#send').text_content()
    clean(pg)
    pg.close()


def test_nothing_to_answer(browser):
    pg = page(browser, doc(lambda l, d: d.update(lines=[], open=False, note=d['layout']['words']['pictures']['nothing'])))
    assert pg.locator('#send h2').text_content() == W['nothing'] and pg.locator('#srail .srow').count() == 0 and pg.locator('#srail [data-fold="coming"]').count() == 1
    assert foot(pg) == W['nothing']
    pg.close()


def test_a_refusal_a_missing_picture_and_a_failed_save(browser):
    pg = page(browser, doc(lambda l, d: l['l03'].update(refused='Not recorded: the picture was made again.')), nopic=['pf7b6e6385e7a'])
    go(pg, STYLE)
    pg.locator('#srail .srow[data-line="l03"]').click()
    pg.wait_for_function("(document.querySelector('#sgate') || {}).textContent.startsWith('A picture is missing')", timeout=90000)
    assert pg.locator('#sgate').text_content() == W['gate_bad'].replace('{pics}', BUILDING['pics'][2]['label']) and pg.locator('#pbar button').first.is_disabled()
    assert pg.locator('#srefused').text_content() == 'Not recorded: the picture was made again.'
    pg.close()
    pg = page(browser)
    go(pg, STYLE)
    pg.evaluate("window.__answers = new Proxy({}, {set(){ throw Object.assign(new Error('no'), {code: 'denied'}); }})")
    pg.locator('#pbar [data-choice="yes"]').click()
    pg.wait_for_function("(document.querySelector('#smsg') || {}).textContent.includes('Could not save (denied)')")
    pg.close()


def test_the_keys_and_the_help(browser):
    pg = page(browser)
    pg.keyboard.press('ArrowRight')
    assert pg.locator('#smain .sname').text_content() == STYLE['name']
    pg.keyboard.press('ArrowLeft')
    pg.keyboard.press('ArrowLeft')
    assert pg.locator('#smain .sname').text_content() == HOUSING['name']
    go(pg, BUILDING)
    pg.locator('#pbar [data-choice="correct"]').click()
    assert pg.locator('#spanel').count() == 1
    pg.keyboard.press('Escape')
    assert pg.locator('#spanel').count() == 0
    pg.locator('#shelp').click()
    text = pg.locator('#smain').inner_text()
    assert all(p in text for p in ROUND['layout']['help']) and W['keys'] in text
    pg.locator('#shelpclose').click()
    pg.close()


@pytest.mark.parametrize('scheme', ['light', 'dark'])
def test_no_money_and_no_error_in_either_scheme(browser, scheme):
    pg = page(browser, size='fit-large', scheme=scheme)
    for l in ROUND['lines']:
        go(pg, l)
        clean(pg)
    pg.close()
