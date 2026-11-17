"""design/213, the tool's side, with the server faked: `vw visuals round --looks` also fetches the thing's footage pictures that were not
inputs of its set, and sends `chose` and `aside` of each set as written; `vw visuals look` sends `face` and `child` as written."""
import json

from test_design211b_round import DUE, THEN, put, server
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw


def test_looks_alone_fetches_the_footage_pictures_beside_the_inputs(harness, monkeypatch, capsys):
    ws, _ = harness
    due = json.loads(json.dumps(DUE))
    due['sets'][0]['footage'] = [{'ref': 'f-2', 'view': 'from the gate', 'key': 'run-1/visuals/references/f-2.png.zoom.jpg'}]
    server(monkeypatch, {}, get=due)
    fetched = []
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: fetched.append((key, rel)) or str(ws / rel))
    code, out, err = run(args(what='round', looks=True), capsys)
    assert code == 0 and err.strip() == THEN and fetched[-1] == ('run-1/visuals/references/f-2.png.zoom.jpg', 'work/visuals/sets/STREET/footage-1.jpg') and len(fetched) == 4
    listed = json.loads((ws / 'work' / 'visuals' / 'sets' / 'looks.json').read_text(encoding='utf-8'))
    assert listed['sets'][0]['footage'][0]['file'] == 'work/visuals/sets/STREET/footage-1.jpg'


def test_the_looks_file_sends_what_the_model_chose_and_set_aside_as_written(harness, monkeypatch, capsys):
    ws, _ = harness
    looks = [{'element_id': 'STREET', 'set': 's-street-1', 'recommend': 'use', 'golden': 's-street-1', 'reason': 'All agree.', 'chose': 'A sandy street.', 'aside': 'A paved one.',
              'pictures': [{'ref': 's-street-1', 'view': 'the whole place', 'verdict': 'pass', 'seen': 'ok'}]}]
    put(ws, 'work/visuals/sets/g1.looks.json', {'by': 'helper', 'sets': looks})
    sent = server(monkeypatch, {'recorded': ['STREET'], 'then': THEN})
    code, out, err = run(args(what='round', looks='work/visuals/sets/g1.looks.json'), capsys)
    assert code == 0 and sent == [('/round/looks', {'by': 'helper', 'sets': looks})]


def test_a_look_at_a_footage_frame_sends_face_and_child_as_written(harness, monkeypatch, capsys):
    ws, _ = harness
    things = [{'element': 'MASON', 'clips': ['C001'], 'note': '', 'looks': [{'trial': 't1', 'view': 'the face', 'verdict': 'pass', 'seen': 'His face.', 'keep': True, 'face': True, 'child': False}]}]
    put(ws, 'out/looks.json', {'by': 'helper', 'things': things})
    sent = server(monkeypatch, {'recorded': ['MASON'], 'then': THEN})
    code, out, err = run(args(what='look', file='out/looks.json'), capsys)
    assert code == 0 and sent == [('/looks', {'by': 'helper', 'things': things})]
