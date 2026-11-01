"""The sweep of 31 Oct 2026 (design/126 W1-W3, W7-W11, W13), on the tool."""
import json

import pytest

from test_visuals_cli import args, harness, run  # noqa: F401  (the fixture rides along)
import vw


def test_a_success_without_a_message_never_says_refused(capsys):   # W1
    with pytest.raises(SystemExit):
        vw.emit({'shot_id': 'S1', 'preparation_id': 'p'}, 0)
    assert 'refused' not in capsys.readouterr().err
    with pytest.raises(SystemExit):
        vw.emit({'detail': [{'loc': ['body', 'x'], 'msg': 'bad'}]}, 2)
    assert 'x: bad' in capsys.readouterr().err


def test_review_without_notes_or_quote_sends_empty_text(harness, monkeypatch, capsys):   # W2
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body) or {'job_id': 'j'}))
    code, out, err = run(args(what='review', job='j1', decision='rejected'), capsys)
    assert code == 0 and posted['notes'] == '' and posted['quote'] == ''


def test_take_all_leaves_drawn_shots_out(harness, monkeypatch, capsys):   # W3
    st = {'jobs': [], 'gaps': [{'shots': [{'shot_id': 'V1', 'visual_type': 'video', 'prepared': True}, {'shot_id': 'D1', 'visual_type': 'drawn', 'prepared': True}]}]}
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: st)
    sent = []
    monkeypatch.setattr(vw, 'request', lambda m, p, wait=None, **kw: (sent.append(kw['json']['shot_id']) or ({'job_id': 'j', 'shot_id': kw['json']['shot_id']}, 0)))
    code, out, err = run(args(what='take', shots=['all']), capsys)
    assert sent == ['V1']


def test_scene_and_font_files_are_read_from_the_run_folder(harness, monkeypatch, capsys):   # W7
    ws, _ = harness
    (ws / 'work' / 'scene-D1.svg').write_text('<svg/>', encoding='utf-8')
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body) or {'next': 'ok'}))
    code, out, err = run(args(what='scene', shot='D1', file='work/scene-D1.svg'), capsys)
    assert code == 0 and posted['name'] == 'scene-D1.svg'


def test_a_material_spec_prints_the_servers_line(harness, monkeypatch, capsys):   # W8
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'element_id': 'brick', 'table': [], 'next': 'Material spec of brick approved.'})
    code, out, err = run(args(what='spec', element='brick'), capsys)
    assert 'Material spec of brick approved.' in err and 'None' not in err


def test_bind_and_still_rows_read_like_the_single_commands(harness, monkeypatch, capsys):   # W9
    ws, _ = harness
    (ws / 'out' / 'bind.json').write_text(json.dumps([{'shot': 'S1', 'refs': {'E1': 'R1,R2'}}, {'shot': 'S2', 'refs': ['E1=R3']}]), encoding='utf-8')
    sent = []
    monkeypatch.setattr(vw, 'request', lambda m, p, wait=None, **kw: (sent.append(kw['json']) or ({'shot_id': kw['json']['shot_id'], 'elements': []}, 0)))
    code, out, err = run(args(what='bind', file='out/bind.json'), capsys)
    assert code == 0 and sent[0]['references'] == {'E1': ['R1', 'R2']} and sent[1]['references'] == {'E1': ['R3']}
    (ws / 'out' / 'stills.json').write_text(json.dumps([{'shot': 'S3', 'ref': 'R9', 'move': 'their words', 'crop': '0,0,0.5,0.5'}]), encoding='utf-8')
    sent.clear()
    code, out, err = run(args(what='still', file='out/stills.json'), capsys)
    assert code == 0 and sent[0]['move'] == 'their words' and sent[0]['crop'] == [0.0, 0.0, 0.5, 0.5]


def test_select_and_fetch_without_their_flags_are_refused(harness, capsys):   # W10
    assert run(args(what='select'), capsys)[0] == 2
    assert run(args(what='fetch'), capsys)[0] == 2


def test_bad_numbers_are_refused_not_crashed(harness, capsys):   # W11
    code, out, err = run(args(what='clip', shot='S1', clip='C1', at='1:20'), capsys)
    assert code == 2 and '--at' in out['message']
    code, out, err = run(args(what='asset', shot='S1'), capsys)
    assert code == 2 and 'asset' in out['message']


def test_an_image_without_kind_is_named_as_a_keyframe(harness, monkeypatch, capsys):   # W13
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body) or {'model': 'm', 'reference_id': 'R'}))
    run(args(what='image', element='E1', prompt='p'), capsys)
    assert posted['name'] == 'keyframe-E1'
