"""Minor corrections as an edit (SK, 25 Nov 2026), the tool's side, with the server faked. `vw visuals round --rewrite` alone lists the sets
that wait for the assistant and fetches their pictures (the marked copies); with a file it sends the where lines ({element_id, where}, or
`unclear`) beside the requests written again ({element_id, prompt}). `vw visuals page --record` carries the operator's marks and the tick
to the server as the page saved them, three marks a picture at most; on the operator's own picture the marks are named by the picture's id
on the server."""
import json

from test_design210b_own import ID, ID2, begin, doc, own, record, sent
from test_design211b_round import THEN, put, server
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
from test_vw25_own import files, served
import vw

WAIT = {'sets': [{'element_id': 'T LAY', 'name': 'Laying a brick', 'edit': True, 'words': 'Take the stains off the handle.', 'every': True,
                  'pictures': [{'ref': 's-1', 'n': 1, 'view': 'the action', 'key': 'run-1/visuals/references/s-1.marked.jpg', 'marks': 2},
                               {'ref': 's-1-2', 'n': 2, 'view': 'closer', 'key': 'run-1/visuals/references/s-1-2.png', 'marks': 0}]},
                 {'element_id': 'STREET', 'name': 'The street', 'edit': False, 'words': 'Wider.', 'request': 'the request as it stands'}],
        'how': ['Name the thing by what the picture shows.'], 'then': THEN}
RECT, STROKE = {'r': [0.1, 0.1, 0.2, 0.2]}, {'p': [0.1, 0.1, 0.2, 0.15], 's': 0.04}


def test_rewrite_alone_lists_the_sets_that_wait_and_fetches_their_pictures(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = server(monkeypatch, {}, get=WAIT)
    fetched = []
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: fetched.append((key, rel)) or str(ws / rel))
    code, out, err = run(args(what='round', rewrite=True), capsys)
    assert code == 0 and calls == [('GET /round/rewrite', None)] and '`how`' in err and 'out/round-rewrites.json' in err
    assert fetched == [('run-1/visuals/references/s-1.marked.jpg', 'work/visuals/sets/T-LAY/correct-1.jpg'), ('run-1/visuals/references/s-1-2.png', 'work/visuals/sets/T-LAY/correct-2.png')]
    listed = json.loads((ws / 'work' / 'visuals' / 'sets' / 'rewrites.json').read_text(encoding='utf-8'))
    assert listed['how'] == WAIT['how'] and listed['sets'][0]['pictures'][0]['file'] == 'work/visuals/sets/T-LAY/correct-1.jpg' and listed['sets'][1]['request'] == 'the request as it stands'
    assert out == {'file': 'work/visuals/sets/rewrites.json', 'sets': ['T LAY', 'STREET'], 'then': THEN}


def test_rewrite_with_a_file_sends_where_lines_and_requests_and_refuses_a_row_with_neither(harness, monkeypatch, capsys):
    ws, _ = harness
    rows = [{'element_id': 'T_LAY', 'where': 'the wooden handle, at the lower right of the frame'}, {'element_id': 'FAN', 'unclear': 'Which of the two fans?'},
            {'element_id': 'STREET', 'prompt': 'A wider sandy street.'}]
    put(ws, 'out/round-rewrites.json', rows)
    calls = server(monkeypatch, {'pass': 'making', 'queued': ['T_LAY', 'STREET'], 'errors': {}, 'then': THEN})
    code, out, err = run(args(what='round', rewrite='out/round-rewrites.json'), capsys)
    assert code == 0 and calls == [('/round/rewrite', {'rows': rows})] and err.strip() == THEN
    put(ws, 'out/bad.json', [{'element_id': 'T_LAY', 'where': ''}])
    calls = server(monkeypatch, {})
    code, out, err = run(args(what='round', rewrite='out/bad.json'), capsys)
    assert code == 2 and calls == [] and '{element_id, where}' in out['message']


def test_record_carries_the_marks_and_the_tick_as_the_page_saved_them(harness, monkeypatch, capsys):
    ws, _ = harness
    marks = {'s-1': [RECT, STROKE, RECT, RECT, 'x'], 's-1-2': [STROKE], 'bad': 'no list'}
    calls = begin(ws, monkeypatch, capsys, [doc('set:T_LAY', 'set:T_LAY:s-1', 'correct', notes='Take the stains off.', marks=marks, every=False),
                                            doc('set:FAN', 'set:FAN:s-2', 'no', notes='Make it smaller.', every='yes', marks=[])])
    rc, out, err = record(capsys)
    got = sent(calls)
    assert rc == 0 and got[0] == {'line': 'l01', 'key': 'set:T_LAY', 'item': 'set:T_LAY:s-1', 'choice': 'correct', 'notes': 'Take the stains off.',
                                  'marks': {'s-1': [RECT, STROKE, RECT], 's-1-2': [STROKE]}, 'every': False}     # three a picture; what is no mark is left out; the server checks the rest
    assert got[1] == {'line': 'l02', 'key': 'set:FAN', 'item': 'set:FAN:s-2', 'choice': 'no', 'notes': 'Make it smaller.'}   # "Make again" keeps its comment


def test_marks_on_the_operators_own_picture_are_named_by_the_servers_id(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('set:E1', 'set:E1:s-1', 'own', own=[own(ID, name='front.jpg'), own(ID2, name='side.png')], notes='Take the pole out.',
                                                fix=True, every=True, marks={ID2: [RECT], 'f' * 32: [RECT]})])
    served(monkeypatch, calls)
    files(ws, f'{ID}.jpg', f'{ID2}.png')
    rc, out, err = record(capsys)
    got = sent(calls)[0]
    assert rc == 0 and got['own_refs'] == ['own-front.jpg', 'own-side.png'] and got['marks'] == {'own-side.png': [RECT]} and got['fix'] is True and got['every'] is True
    assert got['notes'] == 'Take the pole out.' and 'own' not in got
