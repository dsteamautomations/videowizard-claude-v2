"""Defect 35 (VW-12, 31 Oct 2026): `vw visuals image --parents …` failed with NameError (helpers defined after the start block);
`frame --file` rows went without their request id and were refused with no reason ("refused: None"); an image sent with its
answer form but no --prompt was refused; a refusal without a message now says the server's reason."""
import ast
import json
from pathlib import Path

from test_visuals_cli import args, harness, run  # noqa: F401  (the fixture rides along)
import vw


def test_the_start_block_is_the_last_statement_so_every_helper_exists():
    tree = ast.parse(Path(vw.__file__).read_text(encoding='utf-8'))
    last = tree.body[-1]
    assert isinstance(last, ast.If) and '__name__' in ast.unparse(last.test)
    assert vw._parents_and_crops('K1') == {'parents': ['K1']}


def test_frame_file_rows_carry_a_request_id(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'out' / 'frames.json').write_text(json.dumps([{'element': 'E1', 'clip': 'c1', 'at': 1.5}, {'element': 'E2', 'clip': 'c2', 'at': 2}]), encoding='utf-8')
    sent = []
    monkeypatch.setattr(vw, 'request', lambda m, p, wait=None, **kw: (sent.append(kw['json']) or ({'id': 'R', 'kind': 'frame'}, 0)))
    code, out, err = run(args(what='frame', file='out/frames.json'), capsys)
    assert code == 0 and len(sent) == 2 and all(b.get('request_id') for b in sent) and sent[0]['request_id'] != sent[1]['request_id']


def test_a_refusal_without_a_message_says_the_servers_reason(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'out' / 'frames.json').write_text(json.dumps([{'element': 'E1', 'clip': 'c1', 'at': 1}]), encoding='utf-8')
    detail = {'detail': [{'loc': ['body', 'request_id'], 'msg': 'Field required', 'type': 'missing'}]}
    monkeypatch.setattr(vw, 'request', lambda m, p, wait=None, **kw: (detail, 422))
    code, out, err = run(args(what='frame', file='out/frames.json'), capsys)
    assert code == 2 and out['refused']['message'] == 'request_id: Field required' and 'None' not in err
    assert vw.why({}) == 'refused (no reason given)' and vw.why({'message': 'm'}) == 'm'


def test_an_image_with_its_answer_form_and_no_prompt_sends_the_answers_prompt(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'out' / 'answers').mkdir()
    (ws / 'out' / 'answers' / 'sheet-E1.json').write_text(json.dumps({'prompt': 'one brick on edge', 'subject': 'brick'}), encoding='utf-8')
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body) or {'model': 'm', 'reference_id': 'R1'}))
    code, out, err = run(args(what='image', element='E1', kind='sheet', parents='R0', answer='out/answers/sheet-E1.json'), capsys)
    assert code == 0 and posted['prompt'] == 'one brick on edge' and posted['parents'] == ['R0']
    (ws / 'out' / 'images.json').write_text(json.dumps([{'element': 'E1', 'kind': 'sheet', 'answer': 'out/answers/sheet-E1.json'}]), encoding='utf-8')
    sent = []
    monkeypatch.setattr(vw, 'request', lambda m, p, wait=None, **kw: (sent.append(kw['json']) or ({'reference_id': 'R2'}, 0)))
    code, out, err = run(args(what='image', file='out/images.json'), capsys)
    assert code == 0 and sent[0]['prompt'] == 'one brick on edge'
