"""The browser harness for the visuals page (no server, no database, no network).

The real template is rendered with Jinja2 with the variables the server gives it (web.py visuals_page: user, run; the global `version`),
served to Playwright's Chromium, and every request the page makes is answered from memory: the data, the act POST (recorded), the
stylesheet, the pictures. See README.md.

Environment:
  VW_PAGE_REV       a git revision: the template, base.html and style.css are read from it (default: the working tree)
  VW_PAGE_TEMPLATE  a path to a visuals.html to test instead (wins over VW_PAGE_REV for that one file)
  VW_PAGE_DATA      the folder under data/ with the states (default: main)
"""
import io
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from jinja2 import DictLoader, Environment
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
REV = os.environ.get('VW_PAGE_REV') or None
DATA = HERE / 'data' / (os.environ.get('VW_PAGE_DATA') or 'main')
LABEL = DATA.name + ('' if not REV and not os.environ.get('VW_PAGE_TEMPLATE') else '-page-' + (REV or 'custom'))
OUT = HERE / 'out'
STEPS = ['treatment', 'plan', 'references', 'pictures', 'takes', 'record']
SIZES = {'1920x1080': (1920, 1080), '1366x768': (1366, 768)}


def source(rel):
    """A file of server/app, from the working tree or from VW_PAGE_REV."""
    if REV:
        return subprocess.run(['git', '-C', str(SERVER.parent), 'show', f'{REV}:server/app/{rel}'], capture_output=True, check=True).stdout.decode('utf-8')
    return (SERVER / 'app' / rel).read_text(encoding='utf-8')


def states():
    return sorted(p.stem for p in DATA.glob('*.json'))


def load_state(name):
    return json.loads((DATA / f'{name}.json').read_text(encoding='utf-8'))


def png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (320, 180), (150, 160, 170)).save(buf, format='PNG')
    return buf.getvalue()


# What the server answers to a POST, beside the whole new payload as `view` (web.py _visuals_act). A test may pass its own per action.
ANSWERS = {'round-done': {'pass': 'making', 'queued': [], 'errors': {}}, 'round-sets': {'pass': 'complete'}, 'search': {'results': [], 'stock_results': []}}


class PageUnderTest:
    """One open page and what it did. `page` is the Playwright page for anything not covered by a helper."""

    def __init__(self, page, state, code):
        self.page, self.state, self.payload, self.code = page, state, state['payload'], code
        self.posts, self.js_errors, self.console_errors, self.failed_requests, self.unstubbed = [], [], [], [], []
        self.data_gets, self.answers = 0, {}   # how many times the page read its data; the answers per action, which a test may change while the page is open

    # ----- doing -----
    def click(self, target, **kw):
        """Click by CSS selector, or by visible text with text=..., or by role with role=button[name="..."] (Playwright selectors)."""
        self.page.click(target, **kw)

    def click_text(self, text):
        self.page.get_by_text(text, exact=True).first.click()

    def click_role(self, role, name):
        self.page.get_by_role(role, name=name).first.click()

    def open_tab(self, tab):
        self.page.click(f'#steps a[data-s="{tab}"]')
        self.page.wait_for_function('s => !document.getElementById("s-" + s).hidden', arg=tab)

    def go_hash(self, h):
        """Follow a link inside the page: its part after #."""
        self.clear_bar()
        self.page.evaluate('h => { if (location.hash === "#" + h) window.dispatchEvent(new HashChangeEvent("hashchange")); else location.hash = h; }', h)
        self.page.wait_for_timeout(80)

    def clear_bar(self):
        self.page.evaluate('() => { const f = document.getElementById("fmsg"); f.className = "status"; f.textContent = ""; }')

    def screenshot(self, name):
        path = OUT / 'screens' / f'{name}.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path))
        return path

    def serve(self, state_name, patch=None):
        """From now on the server answers with another state's payload (what a real server would hold after the last action)."""
        self.payload = load_state(state_name)['payload']
        if patch:
            patch(self.payload)

    def refresh(self):
        """The page reads its data again, as it does on its timer or when the operator returns to the browser tab."""
        n = self.data_gets
        self.page.evaluate('document.dispatchEvent(new Event("visibilitychange"))')
        self.page.wait_for_function('true', timeout=2000)
        for _ in range(40):
            if self.data_gets > n:
                break
            self.page.wait_for_timeout(25)
        self.page.wait_for_timeout(60)

    def wait_posts(self, n=1, ms=1500):
        """Wait until n requests were sent (or ms passed); returns the posts."""
        for _ in range(ms // 25):
            if len(self.posts) >= n:
                break
            self.page.wait_for_timeout(25)
        self.page.wait_for_timeout(60)
        return self.posts

    def visible(self, selector):
        loc = self.page.locator(selector)
        return loc.count() > 0 and loc.first.is_visible()

    def text(self, selector):
        loc = self.page.locator(selector)
        return loc.first.inner_text().strip() if loc.count() else ''

    # ----- reading -----
    def header_count(self):
        """The N of "N waiting for your verdict" in the header; 0 when the header shows none."""
        b = self.page.locator('#wcount b')
        return int(b.inner_text()) if b.count() else 0

    def tab_counts(self):
        """{tab: N} from the tabs' "· N waiting"."""
        out = {}
        for a in self.page.locator('#steps a').all():
            m = re.search(r'(\d+) waiting', a.inner_text())
            out[a.get_attribute('data-s')] = int(m.group(1)) if m else 0
        return out

    def active_tab(self):
        return self.page.get_attribute('#steps a.on', 'data-s')

    def cards(self):
        """The left list: [{unit, title, badge, waiting}]."""
        return self.page.eval_on_selector_all('#rcards .rcard', '''els => els.map(e => ({unit: e.dataset.unitCard, title: (e.querySelector(".t1") || {}).innerText || "",
            badge: (e.querySelector(".badge") || {}).innerText || "", waiting: !!e.querySelector(".wdot"), selected: e.classList.contains("on")}))''')

    def waiting_chip(self):
        """The N of the filter "Waiting for me (N)"."""
        m = re.search(r'\((\d+)\)', self.page.inner_text('#rfil [data-rf="wait"]'))
        return int(m.group(1)) if m else None

    def bar(self):
        """(kind, text) of the message bar: kind is ok, err, info, dec or ''."""
        cls = (self.page.get_attribute('#fmsg', 'class') or '').replace('status', '').strip()
        return cls, self.page.inner_text('#fmsg').strip()

    def red_line(self):
        """The bar's text when it is red, else ''."""
        kind, text = self.bar()
        return text if kind == 'err' else ''

    def section_text(self, tab=None):
        return self.page.inner_text(f'#s-{tab or self.active_tab()}').strip()

    def links(self):
        """Every link that points inside the page: the payload's waiting links and the page's own hash links. [(label, hash)]."""
        out = [(w['label'], w['link'].split('#', 1)[1]) for w in self.payload.get('waiting') or [] if '#' in w.get('link', '')]
        here = self.page.eval_on_selector_all('a[href*="#"]', 'els => els.map(e => [e.innerText.trim(), e.getAttribute("href")])')
        for label, href in here:
            path, _, h = href.partition('#')
            if h and (not path or path.endswith(f'/runs/{self.code}/visuals')) and (label, h) not in out:
                out.append((label, h))
        return out


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture(scope='session')
def assets():
    template = Path(os.environ['VW_PAGE_TEMPLATE']).read_text(encoding='utf-8') if os.environ.get('VW_PAGE_TEMPLATE') else source('templates/visuals.html')
    return {'env': Environment(loader=DictLoader({'base.html': source('templates/base.html'), 'visuals.html': template}), autoescape=True), 'css': source('static/style.css'), 'png': png()}


@pytest.fixture
def open_page(browser, assets):
    """open_page(state_name, size='1920x1080', tab=<the state's own tab>, answers={action: (status, body)}) -> PageUnderTest, loaded and on that tab."""
    contexts = []

    def _open(state_name, size='1920x1080', tab=None, answers=None, patch=None, clock=False, context=None, wait=True):
        state = load_state(state_name)
        if patch:   # a field the approved contract adds to the data and the server does not send yet (CONTRACT.md)
            patch(state['payload'])
        payload, code = state['payload'], state['payload']['run']['code']
        html = assets['env'].get_template('visuals.html').render(run={'code': code}, user={'name': 'SK', 'role': 'Admin'}, version='pagetests', request=None)
        w, h = SIZES[size]
        ctx = context or browser.new_context(viewport={'width': w, 'height': h})   # a new context: empty localStorage, no remembered tab
        if not context:
            contexts.append(ctx)
        page = ctx.new_page()
        page.set_default_timeout(5000)   # a control that is not there fails in seconds, not in half a minute
        put = PageUnderTest(page, state, code)
        put.answers = dict(answers or {})
        if clock:
            page.clock.install()   # the page's timers run only when the test moves the clock

        def handle(route):
            rq = route.request
            path = rq.url.split('?')[0].split('#')[0]
            if path.endswith(f'/runs/{code}/visuals'):
                return route.fulfill(content_type='text/html', body=html)
            if path.endswith('/visuals/data'):
                put.data_gets += 1
                return route.fulfill(content_type='application/json', body=json.dumps(put.payload))
            if path.endswith('/visuals/act'):
                body = json.loads(rq.post_data or '{}')
                put.posts.append(body)
                status, answer = put.answers.get(body.get('action'), (200, ANSWERS.get(body.get('action'), {'done': True})))
                return route.fulfill(status=status, content_type='application/json', body=json.dumps(answer if status >= 400 else {**answer, 'view': put.payload}))
            if path.endswith('/static/style.css'):
                return route.fulfill(content_type='text/css', body=assets['css'])
            if '/thumb/' in path or '/file/' in path or rq.resource_type == 'image':   # the run's pictures, and a search result's picture on an outside site
                if state.get('pictures') == 'missing':
                    return route.fulfill(status=404, body='')
                return route.fulfill(content_type='video/mp4' if path.endswith('.mp4') else 'image/png', body=b'' if path.endswith('.mp4') else assets['png'])
            put.unstubbed.append(rq.url)
            return route.fulfill(status=404, body='')

        page.on('pageerror', lambda e: put.js_errors.append(str(e)))
        page.on('console', lambda m: (put.failed_requests if m.text.startswith('Failed to load resource') else put.console_errors).append(m.text) if m.type == 'error' else None)
        page.on('requestfailed', lambda r: put.failed_requests.append(f'{r.url}: {r.failure}'))
        page.route('**/*', handle)
        page.goto(f'http://vw.test/runs/{code}/visuals')
        if wait:
            page.wait_for_function('document.getElementById("line").textContent !== "Loading…"')
            put.open_tab(tab or state['tab'])
        return put

    yield _open
    for ctx in contexts:
        ctx.close()


# ---------- the one-command summary: totals on screen and in out/results-<label>.json ----------

_results = []


def pytest_runtest_logreport(report):
    if report.when == 'call' or (report.when == 'setup' and report.failed):
        msg = ''
        if report.failed:
            crash = getattr(report.longrepr, 'reprcrash', None)
            msg = (crash.message if crash else str(report.longrepr)).split('\nassert')[0].strip()
        _results.append({'file': report.nodeid.split('::')[0].split('/')[-1], 'test': report.nodeid.split('::')[-1], 'outcome': report.outcome, 'seconds': round(report.duration, 2), 'message': msg})


def pytest_terminal_summary(terminalreporter):
    if not _results:
        return
    OUT.mkdir(exist_ok=True)
    (OUT / f'results-{LABEL}.json').write_text(json.dumps(_results, indent=1, ensure_ascii=False), encoding='utf-8')
    kind = lambda r: r['test'].split('[')[0]
    name = lambda r: re.sub(r'(^\d+x\d+-)|(-\d+x\d+$)', '', r['test'].partition('[')[2].rstrip(']'))
    l2 = [r for r in _results if r['file'] == 'test_states.py']
    failed = lambda k: sorted({name(r) for r in l2 if kind(r) == k and r['outcome'] == 'failed'})
    n = len({name(r) for r in l2})
    tr = terminalreporter
    tr.write_sep('=', f'visuals page, layer 2: page {REV or "working tree"}, data {DATA.name}')
    tr.write_line(f'states rendered without a script or console error: {n - len(failed("test_loads_without_script_or_console_errors"))} of {n}')
    for k, words in [('test_loads_without_script_or_console_errors', 'states with script errors'), ('test_nothing_is_blank', 'states with a blank tab'),
                     ('test_counts_agree', 'states with count mismatches'), ('test_next_waiting_lands_on_something_actionable', 'states where Next waiting fails'),
                     ('test_every_inside_link_opens_something', 'states with dead links'), ('test_every_picture_loads_or_shows_a_placeholder', 'states with a broken picture'),
                     ('test_layout_holds', 'states with a layout fault')]:
        f = failed(k)
        tr.write_line(f'{words}: {len(f)}' + (f'  ({", ".join(f)})' if f else ''))
    ident = lambda r: r['test'].partition('[')[2].rstrip(']')

    def line(words, rows):   # one layer: how many pass, and the ids that fail
        bad = sorted(ident(r) for r in rows if r['outcome'] != 'passed')
        if rows:
            tr.write_line(f'{words}: {len(rows) - len(bad)} of {len(rows)}' + (f'  (failing: {", ".join(bad)})' if bad else ''))
    tr.write_sep('=', 'layer 1: every control')
    line('controls doing their one thing', [r for r in _results if r['file'].startswith('test_controls_') and ident(r).startswith('C-')])
    tr.write_sep('=', 'layer 3: requirements, edge cases, faults, journeys')
    line('requirements passing', [r for r in _results if r['file'] == 'test_requirements.py'])
    line('edge cases passing', [r for r in _results if r['file'] == 'test_edge_cases.py'])
    line('reported faults absent', [r for r in _results if r['file'] == 'test_faults.py'])
    line('journeys walked to the end', [r for r in _results if r['file'] == 'test_journeys.py'])
    line('follow-up fixes passing', [r for r in _results if r['file'] == 'test_followup.py'])
    line('round 3 passing', [r for r in _results if r['file'] == 'test_round3.py'])
    tr.write_line(f'results: {OUT / ("results-" + LABEL + ".json")}; screenshots: {OUT / "screens"}')
