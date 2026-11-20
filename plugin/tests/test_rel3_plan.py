"""Release 3 on the tool. C2: `vw visuals propose --answers <item>` sends the item of the question the operator answered, and says what the
server kept without asking and what it asks again. C3: when the plan check names a logo or brand file that has not been given, the tool looks
in the run folder's in/brand/ (the server cannot) and says what is there, or where the file goes."""
import json

from test_visuals_cli import args, harness, run   # noqa: F401  (harness is a fixture)
import vw

MISSING = {'kind': 'supplied_missing', 'shot_id': 'S9', 'answered': False, 'message': 'shot S9 shows Client logo (E-logo) and no file of it has been given.'}


def sent_by(monkeypatch, answer):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or dict(answer))
    return sent


def plan_file(ws):
    (ws / 'out' / 'plan.json').write_text(json.dumps({'gaps': []}), encoding='utf-8')


# ---------- C2 ----------

def test_propose_sends_the_answered_question_only_when_it_is_named(harness, monkeypatch, capsys):
    ws, _ = harness
    plan_file(ws)
    sent = sent_by(monkeypatch, {'version': 5, 'kept_without_asking': ["gap G2: accepted with the operator's answer on D2"], 'asked_again': ['gap G1: its change is larger']})
    code, out, err = run(args(what='propose', file='out/plan.json', answers='D2'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/propose', {'plan': {'gaps': []}, 'answers': 'D2'})]
    assert "Kept without asking the operator: gap G2: accepted with the operator's answer on D2." in err and 'Asked again: gap G1: its change is larger.' in err
    sent.clear()
    run(args(what='propose', file='out/plan.json'), capsys)
    assert sent[0][1] == {'plan': {'gaps': []}}                                          # the body an older server takes
    sent.clear()
    run(args(what='check', file='out/plan.json'), capsys)
    assert sent[0][1] == {'plan': {'gaps': []}}


def test_answers_is_a_flag_of_propose_only(harness, capsys):
    ws, _ = harness
    plan_file(ws)
    a = vw.build_parser().parse_args(['visuals', 'propose', '--file', 'out/plan.json', '--answers', 'D2'])
    assert a.answers == 'D2' and 'answers' in vw.VISUALS_FLAGS['propose'] and 'answers' not in vw.VISUALS_FLAGS['check']


# ---------- C3 ----------

def test_a_missing_logo_file_is_said_with_what_the_brand_folder_holds(harness, monkeypatch, capsys):
    ws, _ = harness
    plan_file(ws)
    sent_by(monkeypatch, {'status': 'valid', 'warnings': [MISSING]})
    code, out, err = run(args(what='check', file='out/plan.json'), capsys)
    assert code == 0 and 'A logo or brand file is not given yet (S9). in/brand/ of the run folder is empty: run `vw brand fetch`, or ask the operator now to put the file in ' in err
    assert str(ws / 'in' / 'brand') in err and 'this is a warning, the plan is not held' in err
    (ws / 'in' / 'brand').mkdir(parents=True)
    (ws / 'in' / 'brand' / 'logo-dark.png').write_bytes(b'x')
    (ws / 'in' / 'brand' / 'logo.svg').write_bytes(b'x')
    code, out, err = run(args(what='propose', file='out/plan.json'), capsys)
    assert 'A logo or brand file is not given yet (S9). in/brand/ of the run folder holds logo-dark.png, logo.svg: give the right one with `vw visuals supply --element E --file in/brand/<name>`' in err
    sent_by(monkeypatch, {'status': 'valid', 'warnings': [{**MISSING, 'answered': True, 'answer': 'the film closes without a logo'}]})
    assert 'A logo or brand file' not in run(args(what='check', file='out/plan.json'), capsys)[2]   # answered: the film goes on without it
    sent_by(monkeypatch, {'status': 'valid', 'warnings': []})
    assert 'A logo or brand file' not in run(args(what='check', file='out/plan.json'), capsys)[2]   # a film with no supplied file
