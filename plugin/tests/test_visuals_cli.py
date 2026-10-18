"""vw visuals batches, wait, still, bind, select, all-forms and the reading copy, with the server faked (design/45); the texts."""
import argparse
import json
import re

import pytest

from conftest import PLUGIN, STAGES
import vw

FORBIDDEN = ('visual-command', 'backend', 'connector', 'browser', 'Codex', 'codex', 'local_assets', 'local-asset', 'editable text', 'EDITABLE TEXT')


def args(**kw):
    base = {'what': 'status', 'file': None, 'gap': None, 'gaps': None, 'choice': None, 'quote': None, 'element': None, 'name': None, 'clip': None, 'at': None, 'url': None,
            'kind': None, 'prompt': None, 'parents': None, 'size': None, 'quality': None, 'ref': None, 'sha': None, 'shot': None, 'shots': None, 'provider': None, 'model': None,
            'start': None, 'end': None, 'motion': None, 'continuity': None, 'seconds': None, 'job': None, 'decision': None, 'notes': None, 'timing': None, 'refs': None,
            'subject': None, 'selector': None, 'wait': 0}
    return argparse.Namespace(**{**base, **kw})


@pytest.fixture
def harness(monkeypatch, tmp_path):
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    (tmp_path / 'runs' / 'VW-9' / 'out').mkdir(parents=True)
    (tmp_path / 'runs' / 'VW-9' / 'work').mkdir(parents=True)
    clock = [0.0]
    slept = []

    def sleep(s):
        slept.append(s)
        clock[0] += s
    monkeypatch.setattr(vw.time, 'sleep', sleep)
    monkeypatch.setattr(vw.time, 'monotonic', lambda: clock[0])
    return tmp_path / 'runs' / 'VW-9', slept


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_visuals(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


# ---------- 10.5 batches ----------

def test_image_file_sends_in_order_and_stops_at_the_first_refusal(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'out' / 'images.json').write_text(json.dumps([{'element': 'E1', 'kind': 'keyframe', 'prompt': 'a wall'}, {'element': 'E9', 'kind': 'keyframe', 'prompt': 'x'},
                                                        {'element': 'E2', 'kind': 'isolated', 'prompt': 'a brick', 'parents': 'R1,R2'}]), encoding='utf-8')
    sent = []

    def request(method, path, wait=None, **kw):
        body = kw['json']
        sent.append(body['element_id'])
        if body['element_id'] == 'E9':
            return {'action': 'refused', 'message': 'Reference must identify an element in the current plan.'}, 2
        return {'reference_id': 'ref-' + body['element_id'], 'job_id': 'j', 'model': 'gpt-image-2.5-flare', 'op': 'generate'}, 0
    monkeypatch.setattr(vw, 'request', request)
    code, out, err = run(args(what='image', file='out/images.json'), capsys)
    assert code == 2 and sent == ['E1', 'E9'] and out['queued'] == ['ref-E1'] and out['refused']['element'] == 'E9' and out['remaining'] == ['E2']
    (ws / 'out' / 'images.json').write_text(json.dumps([{'element': 'E2', 'kind': 'isolated', 'prompt': 'a brick', 'parents': 'R1,R2'}]), encoding='utf-8')
    sent.clear()
    bodies = []
    monkeypatch.setattr(vw, 'request', lambda m, p, wait=None, **kw: (bodies.append(kw['json']) or ({'reference_id': 'ref-E2', 'job_id': 'j', 'model': 'm', 'op': 'edit'}, 0)))
    code, out, err = run(args(what='image', file='out/images.json'), capsys)
    assert code == 0 and out['queued'] == ['ref-E2'] and bodies[0]['parents'] == ['R1', 'R2'] and bodies[0]['kind'] == 'isolated' and 'status --wait' in err


def test_take_shots_posts_each_and_all_means_every_prepared_shot(harness, monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(vw, 'request', lambda m, p, wait=None, **kw: (posted.append(kw['json']['shot_id']) or ({'job_id': 'j', 'shot_id': kw['json']['shot_id'], 'provider': 'google', 'model': 'm'}, 0)))
    code, out, err = run(args(what='take', shots=['VS1', 'VS2']), capsys)
    assert code == 0 and posted == ['VS1', 'VS2'] and out['queued'] == ['VS1', 'VS2'] and 'status --wait' in err
    posted.clear()
    status = {'state': 'prepared', 'gaps': [{'gap_id': 'G1', 'accepted': True, 'shots': [{'shot_id': 'VS1', 'visual_type': 'video', 'prepared': True, 'selected': False, 'asset': False},
                                                                                        {'shot_id': 'VS2', 'visual_type': 'video', 'prepared': True, 'selected': True, 'asset': False},
                                                                                        {'shot_id': 'VS3', 'visual_type': 'video', 'prepared': False, 'selected': False, 'asset': False}]}],
              'references': [], 'jobs': [{'id': 'j1', 'unit': 'VS1', 'provider': 'video', 'status': 'running'}]}
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: status)
    code, out, err = run(args(what='take', shots=['all']), capsys)
    assert code == 0 and posted == [] and out['queued'] == [] and 'no prepared shot without a take' in err   # VS1 open, VS2 selected, VS3 not prepared


def test_take_needs_a_shot_or_shots(harness, capsys):
    code, out, err = run(args(what='take'), capsys)
    assert code == 2 and '--shots' in out['message']


def jobs_answer(*jobs):
    return {'state': 'prepared', 'gaps': [], 'references': [], 'jobs': [{'id': j[0], 'unit': j[1], 'provider': j[2], 'status': j[3], 'error': j[4] if len(j) > 4 else None} for j in jobs]}


def test_status_wait_until_no_job_is_open(harness, monkeypatch, capsys):
    _, slept = harness
    answers = [jobs_answer(('j1', 'VS1', 'video', 'submitted'), ('j2', 'r1', 'openai', 'queued')), jobs_answer(('j1', 'VS1', 'video', 'ready'), ('j2', 'r1', 'openai', 'ready'))]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answers.pop(0) if answers else jobs_answer(('j1', 'VS1', 'video', 'ready'), ('j2', 'r1', 'openai', 'ready')))
    code, out, err = run(args(what='status', wait=600), capsys)
    assert code == 0 and slept == [15] and 'all done' in err and '2 ready' in err


def test_status_wait_stops_when_a_job_needs_a_decision(harness, monkeypatch, capsys):
    _, slept = harness
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: jobs_answer(('j1', 'VS1', 'video', 'running'), ('j2', 'VS2', 'video', 'failed', 'Provider reported failed.')))
    code, out, err = run(args(what='status', wait=600), capsys)
    assert code == 0 and slept == [] and '1 need a decision: j2 (failed' in err


def test_status_wait_expiry_counts_open_jobs(harness, monkeypatch, capsys):
    _, slept = harness
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: jobs_answer(('j1', 'VS1', 'video', 'submitted'), ('j2', 'r1', 'openai', 'running'), ('j3', 'VS3', 'video', 'ready')))
    code, out, err = run(args(what='status', wait=30), capsys)
    assert code == 0 and len(slept) == 2 and '1 image, 1 take open; 1 ready' in err and 'run again with --wait' in err


def test_status_without_wait_answers_once(harness, monkeypatch, capsys):
    _, slept = harness
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: jobs_answer(('j1', 'VS1', 'video', 'submitted')))
    code, out, err = run(args(), capsys)
    assert code == 0 and slept == [] and '1 take open' in err and 'run again' not in err


# ---------- 10.3 still, 10.4 two yeses ----------

def test_still_posts_shot_and_reference(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'shot_id': 'IS1', 'kind': 'still', 'reference_id': 'R1'}))
    code, out, err = run(args(what='still', shot='IS1', ref='R1', quote='yes, that picture'), capsys)
    assert code == 0 and posted['path'].endswith('/visuals/still') and posted['shot_id'] == 'IS1' and posted['reference_id'] == 'R1' and posted['quote'] == 'yes, that picture'


def test_bind_sends_the_quote_only_when_given(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body) or {'shot_id': 'VS1', 'elements': ['E1']}))
    code, out, err = run(args(what='bind', shot='VS1', refs=['E1=R1,R2']), capsys)
    assert code == 0 and 'quote' not in posted and posted['references'] == {'E1': ['R1', 'R2']}
    posted.clear()
    run(args(what='bind', shot='VS1', refs=['E1=R1'], quote='yes'), capsys)
    assert posted['quote'] == 'yes'


def test_bind_selector_names_an_object_inside_a_place_picture(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body) or {'shot_id': 'VS1', 'elements': ['E1', 'E2']}))
    code, out, err = run(args(what='bind', shot='VS1', refs=['E1=R1', 'E2=R1'], selector=['E2=R1:"the near wooden chair"']), capsys)
    assert code == 0 and posted['subject_selectors'] == {'E2': {'R1': 'the near wooden chair'}}
    code, out, err = run(args(what='bind', shot='VS1', refs=['E1=R1'], selector=['E2:R1']), capsys)
    assert code == 2 and 'ELEMENT=REF:' in out['message']


def test_select_job_carries_the_notes(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'job_id': 'j1'}))
    code, out, err = run(args(what='select', job='j1', notes='hands and wall checked', quote='yes, that one'), capsys)
    assert code == 0 and posted['path'].endswith('/select-take') and posted['notes'] == 'hands and wall checked' and posted['quote'] == 'yes, that one'


def test_accept_and_record_take_all(harness, monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.append((path, body)) or {'accepted': ['G1', 'G2'], 'recorded': ['G1'], 'skipped': {'G2': 'shot VS2 has no selection or asset'}}))
    code, out, err = run(args(what='accept', gaps=['all'], quote='yes'), capsys)
    assert code == 0 and posted[-1][1]['gap_ids'] == ['all']
    code, out, err = run(args(what='record', gaps=['all'], quote='yes'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/record') and posted[-1][1]['gap_ids'] == ['all'] and '1 recorded' in err and 'G2' in err
    code, out, err = run(args(what='record', gap='G1', quote='yes'), capsys)   # the old form still works
    assert code == 0 and posted[-1][1]['gap_ids'] == ['G1']


# ---------- 10.9 the reading copy of the visuals package ----------

def test_visuals_package_is_written_one_clip_per_line(harness, monkeypatch):
    ws, _ = harness
    pk = {'source': {'gaps': {'G1': {'start_frame': 0}}}, 'prompt': 'p' * 3000, 'plan_schema': {'a': 1},
          'world_evidence': [{'clip': 'c1', 'entities': [{'name': 'Mason'}], 'landmarks': ['wall']}, {'clip': 'c2', 'entities': [], 'landmarks': []}]}

    class Resp:
        status_code = 200
        content = json.dumps(pk).encode('utf-8')

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, path, follow_redirects=True):
            return Resp()
    monkeypatch.setattr(vw, 'api', lambda: Client())
    p = vw._download({'code': 'VW-9', 'run_id': 'run-1'}, 'k', 'work/visuals-package.json')
    text = open(p, encoding='utf-8').read()
    got = json.loads(text)
    assert got['world_evidence'] == pk['world_evidence'] and got['plan_schema'] == {'a': 1} and 'read visuals-package.prompt.md' in got['prompt']
    clips = [l for l in text.split('\n') if '"clip"' in l]
    assert len(clips) == 2 and all(json.loads(l.strip().rstrip(',')) for l in clips)


# ---------- the prompt, the steps and the command text ----------

def test_visuals_prompt_is_rewritten_for_v2():
    prompt = STAGES['visuals']['prompt']
    assert prompt.startswith('VW-PROCEDURE')
    assert len(prompt.split()) <= 3500
    for word in FORBIDDEN:
        assert word not in prompt, word
    for cmd in ('vw visuals frame', 'vw visuals image', 'vw visuals still', 'vw visuals take', 'vw visuals select', 'vw visuals asset', 'vw visuals record'):
        assert cmd in prompt, cmd
    assert 'design/45' in STAGES['visuals']['prompt_origin']


def test_steps_and_command_text_carry_the_new_flow():
    steps = STAGES['visuals']['steps']
    assert 'one clip per line' in steps[0]
    assert 'hand-made animations' in steps[1] and 'AI stills' in steps[1] and 'accept --gaps all' in steps[1] and 'once per run' in steps[1]
    assert 'images.json' in steps[2] and 'warning' in steps[2] and 'status --wait 300' in steps[2]
    assert 'take --shots all' in steps[3] and 'status --wait 600' in steps[3] and 'select --job J --notes' in steps[3] and 'still --shot S --ref R' in steps[3] and 'no quote' in steps[3]
    assert 'record --gaps all' in steps[4]
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'take --shots all' in md and 'status --wait' in md and 'still --shot' in md and 'record --gaps all' in md and 'hand-made' in md
