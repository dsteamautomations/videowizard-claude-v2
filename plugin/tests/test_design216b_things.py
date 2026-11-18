"""design/216b, the tool's side, with the server faked: `vw visuals round --things` with no file writes what Claude reads to name the things
shown in each place; with a file it sends the rows as written and says the server's `then`."""
import json

from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

ASKED = {'places': [{'element_id': 'SITE_DECK', 'name': 'The roof deck', 'description': 'A deck.', 'shots': ['The tiles go in.'], 'things': None}],
         'candidates': [{'id': 'TILE', 'name': 'Mangalore clay roof tile', 'kind': 'object', 'description': 'A tile.'}]}


def test_things_with_no_file_writes_what_to_read(harness, monkeypatch, capsys):
    ws, _ = harness
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: ASKED if method == 'GET' and path.endswith('/round/things') else {})
    rc, out, err = run(args(what='round', things=True), capsys)
    assert rc == 0 and out['places'] == ['SITE_DECK'] and 'work/visuals/things.json' in err
    assert json.loads((ws / 'work' / 'visuals' / 'things-asked.json').read_text(encoding='utf-8')) == ASKED


def test_things_with_a_file_sends_the_rows(harness, monkeypatch, capsys):
    ws, _ = harness
    rows = [{'element_id': 'SITE_DECK', 'things': ['TILE'], 'reason': 'The roof is tiled.'}]
    (ws / 'work' / 'visuals').mkdir(parents=True, exist_ok=True)
    (ws / 'work' / 'visuals' / 'things.json').write_text(json.dumps(rows), encoding='utf-8')
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or {'recorded': ['SITE_DECK'], 'then': '1 place(s) have their things.'})
    rc, out, err = run(args(what='round', things='work/visuals/things.json'), capsys)
    assert rc == 0 and sent[-1][0].endswith('/round/things') and sent[-1][1] == {'rows': rows} and '1 place(s) have their things.' in err
