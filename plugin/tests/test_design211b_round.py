"""design/211 part B, the tool's side, with the server faked: `vw visuals round --looks` (the sets to look at, fetched; the looks recorded),
`--rest` (the second go, on the operator's words), `--rewrite` (the rewritten requests), `--make` with the operator's words. For an answer
of a v2 round the tool prints the server's `then` and no sentence of its own; for an older round it prints what it printed before. The
set-look helper's file."""
import json

from conftest import PLUGIN
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

THEN = 'The server says what comes next.'
DUE = {'sets': [{'element_id': 'STREET', 'name': 'The street', 'set': 's-street-1', 'facts': {'id': 'STREET', 'description': 'A sandy unpaved street.'}, 'request': 'the request sent',
                 'inputs': [{'ref': 'f-1', 'role': 'footage', 'view': 'side', 'key': 'run-1/visuals/references/f-1.png.zoom.jpg'}],
                 'pictures': [{'ref': 's-street-1', 'n': 1, 'view': 'the whole place', 'key': 'run-1/visuals/references/s-street-1.png.zoom.jpg', 'check': {'state': 'pass', 'failed': [], 'error': None}},
                              {'ref': 's-street-1-2', 'n': 2, 'view': 'from the other side', 'key': 'run-1/visuals/references/s-street-1-2.png', 'check': {'state': 'none', 'failed': [], 'error': None}}],
                 'notes': 'the notes'}], 'then': THEN}


def server(monkeypatch, answer, get=None):
    """The server's calls recorded: (path after /visuals, the body sent)."""
    sent = []

    def write(path, body, wait=None):
        sent.append((path.rsplit('/visuals', 1)[-1], body))
        return dict(answer)

    def call(method, path, wait=None, **kw):
        sent.append((method + ' ' + path.rsplit('/visuals', 1)[-1], None))
        return json.loads(json.dumps(get if get is not None else answer))
    monkeypatch.setattr(vw, 'write', write)
    monkeypatch.setattr(vw, 'call', call)
    return sent


def put(ws, rel, value):
    (ws / rel).parent.mkdir(parents=True, exist_ok=True)
    (ws / rel).write_text(json.dumps(value), encoding='utf-8')


# ---------- the looks ----------

def test_looks_alone_lists_the_sets_and_fetches_their_pictures(harness, monkeypatch, capsys):
    ws, _ = harness
    sent = server(monkeypatch, {}, get=DUE)
    fetched = []
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: fetched.append((key, rel)) or str(ws / rel))
    code, out, err = run(args(what='round', looks=True), capsys)
    assert code == 0 and sent == [('GET /round/looks', None)] and err.strip() == THEN
    assert fetched == [('run-1/visuals/references/f-1.png.zoom.jpg', 'work/visuals/sets/STREET/input-1.jpg'),
                       ('run-1/visuals/references/s-street-1.png.zoom.jpg', 'work/visuals/sets/STREET/picture-1.jpg'),
                       ('run-1/visuals/references/s-street-1-2.png', 'work/visuals/sets/STREET/picture-2.png')]
    listed = json.loads((ws / 'work' / 'visuals' / 'sets' / 'looks.json').read_text(encoding='utf-8'))
    assert listed['sets'][0]['request'] == 'the request sent' and listed['sets'][0]['facts']['description'] == 'A sandy unpaved street.' and listed['then'] == THEN
    assert listed['sets'][0]['pictures'][0]['file'] == 'work/visuals/sets/STREET/picture-1.jpg' and listed['sets'][0]['inputs'][0]['file'] == 'work/visuals/sets/STREET/input-1.jpg'
    assert out == {'file': 'work/visuals/sets/looks.json', 'sets': ['STREET'], 'then': THEN}


def test_looks_alone_with_nothing_to_look_at_adds_no_sentence(harness, monkeypatch, capsys):
    ws, _ = harness
    server(monkeypatch, {}, get={'sets': [], 'then': None})
    code, out, err = run(args(what='round', looks=True), capsys)
    assert code == 0 and out['sets'] == [] and err.strip() == 'ok'


def test_looks_with_a_file_records_them(harness, monkeypatch, capsys):
    ws, _ = harness
    looks = [{'element_id': 'STREET', 'set': 's-street-1', 'recommend': 'use', 'golden': 's-street-1', 'reason': 'All agree.', 'pictures': [{'ref': 's-street-1', 'view': 'the whole place', 'verdict': 'pass', 'seen': 'ok'}]}]
    put(ws, 'work/visuals/sets/g1.looks.json', {'by': 'helper', 'sets': looks})
    sent = server(monkeypatch, {'recorded': ['STREET'], 'refused': {}, 'left': [], 'then': THEN})
    code, out, err = run(args(what='round', looks='work/visuals/sets/g1.looks.json'), capsys)
    assert code == 0 and sent == [('/round/looks', {'by': 'helper', 'sets': looks})] and err.strip() == THEN and out['recorded'] == ['STREET']
    put(ws, 'work/visuals/sets/g2.looks.json', looks)       # a bare list: the assistant's own looks
    sent = server(monkeypatch, {'recorded': [], 'refused': {'STREET': 'refused by the server'}, 'left': ['STREET'], 'then': THEN})
    code, out, err = run(args(what='round', looks='work/visuals/sets/g2.looks.json'), capsys)
    assert sent == [('/round/looks', {'by': 'assistant', 'sets': looks})] and err.strip() == THEN and out['refused'] == {'STREET': 'refused by the server'}


def test_a_looks_file_that_is_missing_sends_nothing(harness, monkeypatch, capsys):
    sent = server(monkeypatch, {})
    code, out, err = run(args(what='round', looks='work/visuals/sets/none.json'), capsys)
    assert code == 2 and sent == [] and 'missing or not valid JSON' in out['message']


# ---------- the second go, the rewrite, one set made ----------

def test_rest_sends_the_operators_words_and_prints_then(harness, monkeypatch, capsys):
    sent = server(monkeypatch, {'pass': 'making', 'queued': ['BRICK', 'TILE'], 'errors': {}, 'cost_inr': 70.75, 'then': THEN})
    code, out, err = run(args(what='round', rest=True, quote='make the other two'), capsys)
    assert code == 0 and sent == [('/round/rest', {'quote': 'make the other two'})] and err.strip() == THEN
    sent = server(monkeypatch, {'then': THEN})
    run(args(what='round', rest=True), capsys)
    assert sent == [('/round/rest', {'quote': ''})]          # no words: the server refuses, not the tool (one flow, two front ends)


def test_rewrite_sends_the_rows_and_prints_then(harness, monkeypatch, capsys):
    ws, _ = harness
    rows = [{'element_id': 'T_LAY', 'prompt': 'The right hand presses the wet brick into the mortar bed.'}]
    put(ws, 'out/round-rewrites.json', rows)
    sent = server(monkeypatch, {'pass': 'making', 'queued': ['T_LAY'], 'errors': {}, 'cost_inr': 35.38, 'then': THEN})
    code, out, err = run(args(what='round', rewrite='out/round-rewrites.json'), capsys)
    assert code == 0 and sent == [('/round/rewrite', {'rows': rows})] and err.strip() == THEN
    put(ws, 'out/bad.json', [{'element_id': 'T_LAY'}])
    sent = server(monkeypatch, {})
    code, out, err = run(args(what='round', rewrite='out/bad.json'), capsys)
    assert code == 2 and sent == [] and 'must be a list of {element_id, prompt' in out['message']


def test_make_sends_the_operators_words(harness, monkeypatch, capsys):
    sent = server(monkeypatch, {'element_id': 'STREET', 'queued': True, 'pass': 'making', 'cost_inr': 35.38, 'next': 'STREET: its set is being made; it comes back on step 2.', 'then': THEN})
    code, out, err = run(args(what='round', make='STREET', quote='yes, again'), capsys)
    assert code == 0 and sent == [('/round/make', {'element_id': 'STREET', 'quote': 'yes, again'})] and err.strip() == THEN
    sent = server(monkeypatch, {'element_id': 'STREET', 'queued': True, 'pass': 'making', 'cost_inr': 35.38, 'next': 'STREET: its set is being made; it comes back on step 2.'})
    code, out, err = run(args(what='round', make='STREET'), capsys)      # an older round's answer: the line of before
    assert sent == [('/round/make', {'element_id': 'STREET'})]
    assert err.strip() == 'STREET: its set is being made; it comes back on step 2. (about ₹35; paid: tell the operator.) Then `vw visuals status --wait 900`.'


# ---------- a v2 answer: `then` and nothing else; an older answer: the line of before ----------

def test_the_round_file_of_a_v2_round_prints_then_only(harness, monkeypatch, capsys):
    ws, _ = harness
    put(ws, 'out/reference-round.json', [{'element_id': 'STREET', 'rec': 'set', 'reason': 'The opening place.'}])
    sent = server(monkeypatch, {'pass': 1, 'elements': 1, 'kept': True, 'v': 2, 'doubtful': 0, 'then': THEN})
    code, out, err = run(args(what='round'), capsys)
    assert code == 0 and sent == [('/round', {'elements': [{'element_id': 'STREET', 'rec': 'set', 'reason': 'The opening place.'}]})] and err.strip() == THEN
    server(monkeypatch, {'pass': 2, 'kept': True, 'v': 2, 'merged': ['BRICK'], 'reopened': ['FAN'], 'queued': [], 'errors': {}, 'elements': 7, 'cost_inr': 0, 'then': THEN})
    assert run(args(what='round'), capsys)[2].strip() == THEN            # a second send: never "missing set(s) being made"


def test_the_round_file_of_an_older_round_prints_the_lines_of_before(harness, monkeypatch, capsys):
    ws, _ = harness
    put(ws, 'out/reference-round.json', [{'element_id': 'E1', 'prompt': 'the plinth'}])
    server(monkeypatch, {'pass': 1, 'elements': 1, 'kept': True})
    err = run(args(what='round'), capsys)[2]
    assert err.startswith('Reference round posted for 1 elements (the kept method). Now `vw visuals page`') and 'Done makes every set at once' in err
    server(monkeypatch, {'pass': 'making', 'kept': True, 'merged': ['E1'], 'queued': ['E1'], 'errors': {}, 'elements': 3, 'cost_inr': 35.38})
    assert run(args(what='round'), capsys)[2].startswith('Round kept: 1 missing set(s) being made (about ₹35); the round is at making.')


def test_step_1_and_the_sets_print_then_for_a_v2_round_and_the_line_of_before_for_an_older_one(harness, monkeypatch, capsys):
    ws, _ = harness
    put(ws, 'out/v.json', {'STREET': {'verdict': 'approve'}})
    sent = server(monkeypatch, {'pass': 'making', 'queued': ['STREET'], 'errors': {}, 'from_footage': [], 'cost_inr': 35.38, 'rest': ['BRICK'], 'then': THEN})
    code, out, err = run(args(what='round', verdicts='out/v.json', quote='Done'), capsys)
    assert sent == [('/round/done', {'verdicts': {'STREET': {'verdict': 'approve'}}, 'quote': 'Done'})] and err.strip() == THEN
    server(monkeypatch, {'pass': 'complete', 'queued': [], 'errors': {}, 'from_footage': ['TROWEL'], 'cost_inr': 0, 'rest': [], 'then': None})
    assert run(args(what='round', verdicts='out/v.json', quote='Done'), capsys)[2].strip() == 'ok'       # nothing comes next from part B: no sentence is made up
    server(monkeypatch, {'pass': 'making', 'queued': ['STREET'], 'errors': {}, 'from_footage': [], 'cost_inr': 35.38})
    assert run(args(what='round', verdicts='out/v.json', quote='Done'), capsys)[2].startswith('Step 1 recorded: 1 set(s) being made (about ₹35); the round is at making.')
    sent = server(monkeypatch, {'pass': 'rewrite', 'queued': [], 'errors': {}, 'approved': [], 'held': {}, 'rewrite': ['STREET'], 'then': THEN})
    assert run(args(what='round', sets='out/v.json', quote='Sets done'), capsys)[2].strip() == THEN and sent[0][0] == '/round/sets'
    server(monkeypatch, {'pass': 'making', 'queued': ['STREET'], 'errors': {}, 'approved': [], 'held': {}})
    assert run(args(what='round', sets='out/v.json', quote='Sets done'), capsys)[2].startswith('Sets recorded: 0 approved, 1 being made again; the round is making.')


# ---------- the helper ----------

def test_the_set_look_helpers_file():
    text = (PLUGIN / 'agents' / 'vw-set-look.md').read_text(encoding='utf-8')
    assert text.startswith('---\nname: vw-set-look\n') and 'tools: Read, Write, Bash\nmodel: opus\neffort: high\n---\n' in text and 'Not built yet' not in text
    body = text.split('---\n', 2)[2]
    for words in ('work/visuals/sets/looks.json', 'work/visuals/sets/<element>/', '`vw visuals round --looks work/visuals/sets/<group>.looks.json`', 'recommend', 'use', 'remake', 'doubt',
                  'pass', 'weak', 'fail', 'golden', 'never approve', 'never order'):
        assert words in body, words
    for point in ('shows the view', "film's own", "plan's description", 'three pictures agree', 'image model changed'):   # the five things it judges by (design/211 section 3.11)
        assert point in body, point
    assert 'hands' in body and 'way of working' in body                  # the helper agrees with the request and the check: a way of working may show hands
    assert '\r' not in text and 'vw visuals image' not in body and 'vw visuals approve' not in body
