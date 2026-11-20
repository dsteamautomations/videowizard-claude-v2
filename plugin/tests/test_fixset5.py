"""Fix set, part 2 (SK, 20 Nov 2026), the tool's side, with the server faked: the page is never empty and its link is given only when it is filled.

(a) a loading note is handed first, before the pictures; (b) the link is printed only by `vw visuals page --shown`, after the round was read
back from the page; (c) a page published by an older tool is said at `vw visuals next`, long before the page is wanted; (d) a publish that went
to another link is refused; (e) a round handed and never confirmed is said at the next call; (f) a thing with no line is named."""
import json

from test_design210_pictures import URL, code, fake, with_pics
from test_visuals_cli import args, harness, jobs_answer, run   # noqa: F401 (harness is a fixture)
import vw

LOADING = {'note': 'The pictures of this step are being loaded: 1 line, about 1 minute. This page fills itself: there is no need to reload it.',
           'late': 'This is taking longer than expected: ask the assistant in the chat.', 'minutes': 1, 'expected': 1}
SAID = 'Preparing 12 pictures for the page, about 1 minute.'
SAY = '1 thing needs your answer:\n- The wall\nThen say done here.'
NEXT = {'item': None, 'working': ['2 drawings are being made.'], 'say_last': 'Nothing is needed from you now.'}


def page_at(ws, name):
    return ws / 'work' / 'page' / name


def linked(ws, version=None):
    """The run has a page: its link, and the tool that published it."""
    page_at(ws, '').mkdir(parents=True, exist_ok=True)
    page_at(ws, 'url.txt').write_text(URL + '\n', encoding='utf-8')
    page_at(ws, 'page-version.txt').write_text((version or vw.plugin_version()) + '\n', encoding='utf-8')


def read_back(ws, rnd, lines=None):
    """What ArtifactData's get saves under `answers_dir` for the round's document."""
    doc = json.loads(page_at(ws, f'{rnd}.json').read_text(encoding='utf-8'))
    out = page_at(ws, 'answers') / 'rounds' / f'{rnd}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'data': {**doc, 'lines': doc['lines'] if lines is None else lines}}), encoding='utf-8')


# ---------- (a) the loading note first ----------

def test_with_many_pictures_the_loading_note_is_handed_before_anything_is_fetched_and_only_once(harness, monkeypatch, capsys):
    ws, _ = harness
    linked(ws)
    got = fake(monkeypatch, lambda: with_pics('r1', *range(1, 13), preparing=SAID, say=SAY, loading=LOADING))
    rc, out, err = run(args(what='page', record=False), capsys)
    [w] = out['loading_write']
    doc = json.loads(open(w['file_path'], encoding='utf-8').read())
    assert rc == 0 and got == [] and (w['op'], w['collection']) == ('set', 'rounds') and w['doc_id'] == doc['round'] and doc['round'].startswith('loading-')
    assert doc['loading'] == {'minutes': 1, 'expected': 1, 'late': LOADING['late']} and doc['note'] == LOADING['note'] and doc['lines'] == [] and doc['open'] is False
    assert doc['step'] == 'Reference drawings' and doc['run'] == 'VW-9' and 'loading_write' in err and err.index('loading_write') < err.index('--fetch')
    rc, out, err = run(args(what='page', record=False, fetch=True), capsys)
    rnd = json.loads(page_at(ws, 'r1.json').read_text(encoding='utf-8'))
    assert rc == 0 and 'loading_write' not in out and rnd['at'] > doc['at']   # the round is the newer document: it takes the loading note's place on the page


def test_with_a_few_pictures_the_loading_note_comes_with_the_round_and_is_the_older_document(harness, monkeypatch, capsys):
    ws, _ = harness
    linked(ws)
    fake(monkeypatch, lambda: with_pics('r1', 1, 2, loading=LOADING))
    rc, out, err = run(args(what='page', record=False), capsys)
    doc = json.loads(open(out['loading_write'][0]['file_path'], encoding='utf-8').read())
    assert doc['at'] < json.loads(page_at(ws, 'r1.json').read_text(encoding='utf-8'))['at'] and 'send `loading_write` first' in err
    sent = vw._pictures_sent(page_at(ws, ''))
    page_at(ws, 'pictures.json').write_text(json.dumps({**sent, 'zoom': {code(1): 'a' * 32, code(2): 'b' * 32}}), encoding='utf-8')   # the large files are uploaded
    rc, out, err = run(args(what='page', record=False), capsys)
    assert 'loading_write' not in out   # nothing left to send: no note


def test_an_older_server_gives_no_loading_note(harness, monkeypatch, capsys):
    fake(monkeypatch, lambda: with_pics('r1', 1, 2))
    assert 'loading_write' not in run(args(what='page', record=False), capsys)[1]


# ---------- (b) the link only when the round is on the page ----------

def test_the_link_is_not_printed_with_the_round_and_shown_gives_it_once_the_round_is_read_back(harness, monkeypatch, capsys):
    ws, _ = harness
    linked(ws)
    fake(monkeypatch, lambda: with_pics('r1', 1, say=SAY))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert out['url'] == URL and URL not in err and '`vw visuals page --shown`' in out['after_round'] and 'action "get"' in out['after_round'] and 'for your tool calls only' in err
    rc, out, err = run(args(what='page', record=False, shown=True), capsys)
    assert rc == 2 and URL not in json.dumps(out) + err and 'was not read back from the page' in out['message'] and '`vw visuals next`' in out['message']
    read_back(ws, 'r1', lines=[])
    rc, out, err = run(args(what='page', record=False, shown=True), capsys)
    assert rc == 2 and 'holds 0 lines, not 1' in out['message'] and URL not in err   # a short round on the page is not the round
    read_back(ws, 'r1')
    rc, out, err = run(args(what='page', record=False, shown=True), capsys)
    assert rc == 0 and out == {'shown': True, 'url': URL, 'round': 'r1', 'say': SAY} and err.rstrip().endswith(URL) and 'exactly as it is' in err


def test_a_round_with_nothing_to_answer_asks_for_no_link(harness, monkeypatch, capsys):
    ws, _ = harness
    linked(ws)
    quiet = with_pics('r1', 1)
    quiet['lines'][0]['state'] = 'recorded'
    fake(monkeypatch, lambda: quiet)
    rc, out, err = run(args(what='page', record=False), capsys)
    assert 'after_round' not in out and not page_at(ws, 'handed.json').exists()
    rc, out, err = run(args(what='page', record=False, shown=True), capsys)
    assert rc == 2 and 'No round waits for its link' in out['message']


# ---------- (c) a page published by an older tool is said early ----------

def test_next_says_to_publish_again_now_while_things_are_made_and_stops_once_it_is_done(harness, monkeypatch, capsys):
    ws, _ = harness
    linked(ws, version='0.0.1')
    page_at(ws, 'capabilities.json').write_text(json.dumps({'db': {}}), encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: dict(NEXT))
    rc, out, err = run(args(what='next', one=False), capsys)
    assert rc == 0 and out['republish_now'] == {'page_file': out['republish_now']['page_file'], 'url': URL, 'capabilities': {'db': {}}} and out['republish_now']['page_file'].endswith('decisions.html')
    assert 'publish it again now, to the same link' in err and 'never a new page' in err and URL not in err
    run(args(what='page', url=URL, record=False), capsys)   # published again to the same link
    rc, out, err = run(args(what='next', one=False), capsys)
    assert 'republish_now' not in out and 'publish it again' not in err


def test_the_closed_page_says_it_too_and_a_run_with_no_page_says_nothing(harness, monkeypatch, capsys):
    ws, _ = harness
    closed = {'closed': True, 'say': 'Stills: 2 being made.', 'then': 'Stills: 2 being made.', 'how': 'Say the line of counts.', 'capabilities': {'db': {}}}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: dict(closed))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert 'republish_now' not in out
    linked(ws, version='0.0.1')
    rc, out, err = run(args(what='page', record=False), capsys)
    assert out['republish_now']['url'] == URL and out['republish_now']['capabilities'] == {'db': {}} and 'publish it again now' in err


def test_the_status_says_it_too(harness, monkeypatch, capsys):
    ws, _ = harness
    linked(ws, version='0.0.1')
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: jobs_answer(('j1', 'D1', 'drawn', 'ready')))
    rc, out, err = run(args(what='status', wait=0), capsys)
    assert rc == 0 and out['republish_now']['url'] == URL and 'capabilities' not in out['republish_now'] and err.startswith('The page of this run was published by an older tool')
    assert 'leave `capabilities` out, the page keeps its own' in err   # a run folder from before this change kept none


# ---------- (d) republish is one safe action ----------

def test_a_publish_that_went_to_another_link_is_refused_and_nothing_is_changed(harness, monkeypatch, capsys):
    ws, _ = harness
    linked(ws, version='0.0.1')
    page_at(ws, 'pictures.json').write_text('{"again": 0, "thumbs": ["p1"], "zoom": {}}', encoding='utf-8')
    rc, out, err = run(args(what='page', url='https://claude.ai/artifact/new', record=False), capsys)
    assert rc == 2 and URL in out['message'] and 'another link' in out['message'] and '`vw visuals next`' in out['message'] and '--new-page' in out['message']
    assert page_at(ws, 'url.txt').read_text(encoding='utf-8').strip() == URL and page_at(ws, 'page-version.txt').read_text(encoding='utf-8').strip() == '0.0.1'
    assert page_at(ws, 'pictures.json').exists()
    rc, out, err = run(args(what='page', url='https://claude.ai/artifact/new', record=False, new_page=True), capsys)   # on the operator's word only
    assert rc == 0 and page_at(ws, 'url.txt').read_text(encoding='utf-8').strip() == 'https://claude.ai/artifact/new' and not page_at(ws, 'pictures.json').exists()


# ---------- (e) a failed or stopped load is said ----------

def test_a_round_handed_and_never_confirmed_is_said_at_the_next_call_with_the_chat_path(harness, monkeypatch, capsys):
    ws, _ = harness
    linked(ws)
    fake(monkeypatch, lambda: with_pics('r1', 1, 2, say=SAY))
    run(args(what='page', record=False), capsys)   # the round is handed; then the call that fills the page is stopped
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: dict(NEXT))
    rc, out, err = run(args(what='next', one=False), capsys)
    assert out['page_unconfirmed'] == {'round': 'r1', 'step': 'Reference drawings', 'lines': 1, 'large_not_uploaded': 2}
    assert 'was handed out and never confirmed on the page' in err and '2 large files were not uploaded' in err and 'Ask this step in the chat' in err
    fake(monkeypatch, lambda: with_pics('r2', 1, 2, say=SAY))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert 'never confirmed on the page' in err and out['round'] == 'r2'   # said once more with the round given anew
    read_back(ws, 'r2')
    run(args(what='page', record=False, shown=True), capsys)
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: dict(NEXT))
    rc, out, err = run(args(what='next', one=False), capsys)
    assert 'page_unconfirmed' not in out and 'never confirmed' not in err


# ---------- (f) a thing with no line is named ----------

def test_what_is_not_on_the_page_is_passed_on(harness, monkeypatch, capsys):
    ws, _ = harness
    linked(ws)
    missing = 'Not on the page: The wall (made and checked). Tell the operator which, and ask about them in the chat (`vw visuals next`): never leave them out silently.'
    fake(monkeypatch, lambda: with_pics('r1', 1, not_on_page=missing))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert out['not_on_page'] == missing and missing in err


def test_the_instructions_say_the_one_path():
    md = (vw.Path(vw.__file__).resolve().parents[1] / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'give the operator the link only when `vw visuals page --shown` prints it' in md
    assert 'as soon as the tool says so (`republish_now`' in md and 'never a new page' in md
