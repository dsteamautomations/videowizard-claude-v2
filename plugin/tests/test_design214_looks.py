"""design/214, the tool's side, with the server faked: `vw visuals round --looks` keeps each picture's check list in looks.json as the
server gave it, and sends the look's line answers and `not_checked` as written. The helper file tells the looker to answer every line."""
import json
from pathlib import Path

from test_design211b_round import DUE, THEN, put, server
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

PLUGIN = Path(__file__).resolve().parents[1]
LINES = [{'id': '9a2a4ea2', 'check': 'the view', 'pass_when': 'the picture shows what its turn asked: the whole of The street, seen wide'},
         {'id': '0c1d2e3f', 'check': 'drawn fact: lug to lug: 120 mm', 'pass_when': 'the picture shows it as the approved drawings do: lug to lug: 120 mm', 'say': True}]


def test_looks_alone_keeps_each_pictures_check_list_as_the_server_gave_it(harness, monkeypatch, capsys):
    ws, _ = harness
    due = json.loads(json.dumps(DUE))
    for p in due['sets'][0]['pictures']:
        p.pop('check', None)
        p['lines'] = LINES
    server(monkeypatch, {}, get=due)
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: str(ws / rel))
    code, out, err = run(args(what='round', looks=True), capsys)
    listed = json.loads((ws / 'work' / 'visuals' / 'sets' / 'looks.json').read_text(encoding='utf-8'))
    assert code == 0 and err.strip() == THEN and all(p['lines'] == LINES and p['file'] for p in listed['sets'][0]['pictures'])


def test_the_looks_file_sends_the_line_answers_and_not_checked_as_written(harness, monkeypatch, capsys):
    ws, _ = harness
    looks = [{'element_id': 'STREET', 'set': 's-street-1', 'recommend': 'doubt', 'golden': None, 'reason': 'One picture would not open.', 'chose': 'A sandy street.', 'aside': 'A paved one.',
              'pictures': [{'ref': 's-street-1', 'view': 'the whole place', 'verdict': 'pass', 'seen': 'ok',
                            'lines': [{'id': '9a2a4ea2', 'pass': True, 'seen': ''}, {'id': '0c1d2e3f', 'pass': False, 'seen': 'The lugs sit closer than the drawing shows.'}]},
                           {'ref': 's-street-1-2', 'not_checked': 'The file would not open.'}]}]
    put(ws, 'work/visuals/sets/g1.looks.json', {'by': 'helper', 'sets': looks})
    sent = server(monkeypatch, {'recorded': ['STREET'], 'then': THEN})
    code, out, err = run(args(what='round', looks='work/visuals/sets/g1.looks.json'), capsys)
    assert code == 0 and sent == [('/round/looks', {'by': 'helper', 'sets': looks})]


def test_the_helper_answers_every_line_from_the_picture_and_the_plugin_is_0_95_0():
    helper = (PLUGIN / 'agents' / 'vw-set-look.md').read_text(encoding='utf-8')
    for said in ('Answer every line of every picture', 'from what you see in the picture, never from the request or the notes', 'against the drawing sheet among the inputs',
                 'Never pass a line you did not look at', '"not_checked": "<why>"', 'No model checks a set', "one answer for each line of that picture's list"):
        assert said in helper, said
    assert "program's check" not in helper and 'Gemini' not in helper
    assert 'answer every line of every picture' in (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert json.loads((PLUGIN / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))['version'] == '0.110.0'   # release 0.125.0 / 0.107.0 (23 Nov 2026), the VW-25 set; before: release 0.121.0 / 0.105.0 (20 Nov 2026): layout B (the layout video flat with thin outlines, a purple back mark; the checker's helper text names them); before: release 0.120.0 / 0.104.0 (20 Nov 2026): releases 1 to 4 (the served text now names `vw motion render --wait`, `vw visuals propose --answers` and `vw defect --shot`, which an older tool lacks; 0.119.0 / 0.103.0 was never deployed): Claude's check with judgement (a line answered "na"), one click, the closed check box, step 7's order (a look with "na" is refused by an older server, and an older tool lacks the helper texts); before: release 0.118.0 / 0.102.0 (20 Nov 2026): step 7 on the page, the step 6 fix set, the page fixes; design/221: 0.101.0; design/218: 0.100.0; design/217: 0.99.0; design/216b: 0.98.0; design/216: 0.97.0; design/215: 0.96.0
