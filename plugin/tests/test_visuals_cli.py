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
            'subject': None, 'selector': None, 'answer': None, 'variants': None, 'end_answer': None, 'question': None, 'camera': None, 'support': None, 'look': None, 'reuse': None, 'considered': None, 'crop': None, 'move': None, 'wait': 0, 'keywords': None, 'search': None, 'n': None, 'note': None, 'reason': None, 'verdicts': None, 'picks': None}
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


def test_status_wait_keeps_waiting_while_a_job_runs_and_names_the_one_needing_a_decision(harness, monkeypatch, capsys):
    """design/106 T5 (was: the wait stopped at once when an old job needed a decision)."""
    _, slept = harness
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: jobs_answer(('j1', 'VS1', 'video', 'running'), ('j2', 'VS2', 'video', 'failed', 'Provider reported failed.')))
    code, out, err = run(args(what='status', wait=600), capsys)
    assert code == 0 and len(slept) == 40 and err.count('need a decision') == 1 and '1 need a decision: j2 (failed' in err


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


def test_prepare_take_needs_the_end_image_before_any_request(harness, monkeypatch, capsys):
    """design/66 D1: every take has a start and an end image; the plugin refuses without one and posts nothing."""
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'preparation_id': 'p1', 'duration_seconds': 6}))
    code, out, err = run(args(what='prepare-take', shot='VS1', start='R1', motion='pours', subject=['E1="pours water"']), capsys)
    assert code == 2 and 'start and an end image' in out['message'] and '--end' in out['message'] and not posted
    code, out, err = run(args(what='prepare-take', shot='VS1', start='R1', end='R2', motion='pours', subject=['E1="pours water"']), capsys)
    assert code == 2 and '--continuity' in out['message'] and not posted   # design/84 V2
    code, out, err = run(args(what='prepare-take', shot='VS1', start='R1', end='R2', motion='pours', subject=['E1="pours water"'], continuity='the wall stays; grey hair, white shirt'), capsys)
    assert code == 0 and posted['continuity_notes'].startswith('the wall stays') and posted['path'].endswith('/prepare-take') and posted['start_image'] == 'R1' and posted['end_image'] == 'R2' and posted['motion_prompt'] == 'pours'


def test_prepare_writes_the_library_files_per_step_behind_the_sentinel(harness, monkeypatch, capsys):
    """design/68 L4: one file per library file under work/visuals/library/<step>/, each beginning with the procedure sentinel so the guard keeps it from the operator."""
    ws, _ = harness
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'package': {'key': 'k'}, 'gaps': ['G1'], 'library_version': 'vwlib-x'})
    monkeypatch.setattr(vw, 'download_visuals_package', lambda m, key: [{'file': 'work/visuals/prompt.md', 'rows': 1, 'for': 'read first'}])
    lib = {'version': 'vwlib-x', 'always': [{'path': 'library/RULEBOOK.md', 'text': '# Rules\nread me'}],
           'steps': {'start': {'task': 'keyframe', 'playbook': 'video-frame', 'when': '', 'files': [{'path': 'library/playbooks/video-frame.md', 'text': '# Frames'}, {'path': 'library/video/gap-fill.md', 'text': '# Gaps'}]},
                     'frame': {'task': None, 'playbook': None, 'when': '', 'files': [{'path': 'library/video/gap-fill.md', 'text': '# Gaps'}]}},
           'compliance': {'path': 'library/agency/compliance-checklist.md', 'text': '# C'}, 'map': '# VideoWizard map', 'field_sources': '# Fields'}
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: lib if path.endswith('/library') else {})
    (ws / 'work' / 'visuals' / 'library' / 'old').mkdir(parents=True)
    (ws / 'work' / 'visuals' / 'library' / 'old' / 'stale.md').write_text('x', encoding='utf-8')
    code, out, err = run(args(what='prepare'), capsys)
    folder = ws / 'work' / 'visuals' / 'library'
    assert code == 0 and not (folder / 'old').exists()
    rules = (folder / 'always' / 'RULEBOOK.md').read_text(encoding='utf-8')
    assert rules.startswith('VW-PROCEDURE — for the assistant only, never for the operator.\n') and 'Library vwlib-x: library/RULEBOOK.md' in rules.split('\n')[1] and rules.endswith('# Rules\nread me\n')
    assert (folder / 'start' / 'playbooks__video-frame.md').exists() and (folder / 'start' / 'video__gap-fill.md').exists() and (folder / 'frame' / 'video__gap-fill.md').exists()
    assert (folder / 'VW-MAP.md').read_text(encoding='utf-8').startswith('VW-PROCEDURE') and (folder / 'compliance' / 'agency__compliance-checklist.md').exists()
    steps = json.loads((folder / 'steps.json').read_text(encoding='utf-8'))
    assert steps['start'] == {'task': 'keyframe', 'playbook': 'video-frame', 'when': '', 'files': ['playbooks__video-frame.md', 'video__gap-fill.md']}
    by = {f['file']: f for f in out['files']}
    assert by['work/visuals/library/always/RULEBOOK.md']['for'] == 'every prompt' and by['work/visuals/library/start/video__gap-fill.md']['for'] == 'start'
    assert 'work/visuals/library/' in err and out['library_version'] == 'vwlib-x'


def test_image_and_prepare_take_post_the_answer_from_the_file(harness, monkeypatch, capsys):
    """design/68 L5: --answer out/answers/<id>.json travels with the prompt; without it the body is as today."""
    ws, _ = harness
    (ws / 'out' / 'answers').mkdir()
    (ws / 'out' / 'answers' / 'a1.json').write_text(json.dumps({'status': 'ready', 'prompt': 'p', 'checklist': [], 'exact_text': []}), encoding='utf-8')
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'reference_id': 'R9', 'job_id': 'j', 'op': 'generate', 'model': 'gpt-image-2.5-flare', 'preparation_id': 'p1', 'duration_seconds': 6, 'exact_seconds': 5.5, 'provider': {'provider': 'google', 'model': 'gemini-omni-1.1-flash'}}))
    code, out, err = run(args(what='image', element='E1', kind='keyframe', prompt='p', answer='out/answers/a1.json'), capsys)
    assert code == 0 and posted['answer']['status'] == 'ready' and posted['prompt'] == 'p'
    posted.clear()
    run(args(what='image', element='E1', kind='keyframe', prompt='p'), capsys)
    assert 'answer' not in posted
    posted.clear()
    code, out, err = run(args(what='prepare-take', shot='VS1', start='R1', end='R2', motion='pours', subject=['E1="pours water"'], continuity='the wall stays', answer='out/answers/a1.json'), capsys)
    assert code == 0 and posted['answer']['prompt'] == 'p' and posted['end_image'] == 'R2'
    (ws / 'out' / 'images.json').write_text(json.dumps([{'element': 'E1', 'kind': 'sheet', 'prompt': 'p', 'answer': 'out/answers/a1.json'}, {'element': 'E2', 'kind': 'sheet', 'prompt': 'q'}]), encoding='utf-8')
    bodies = []
    monkeypatch.setattr(vw, 'request', lambda method, path, **kw: (bodies.append(kw['json']) or ({'reference_id': f'R{len(bodies)}'}, None)))
    code, out, err = run(args(what='image', file='out/images.json'), capsys)
    assert code == 0 and bodies[0]['answer']['prompt'] == 'p' and 'answer' not in bodies[1]


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
    monkeypatch.setattr(vw, 'call', lambda *a, **k: {'jobs': []})   # design/81: select reads the jobs to accept a shot id
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

def fake_client(monkeypatch, body):
    class Resp:
        status_code = 200
        content = json.dumps(body).encode('utf-8')

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, path, follow_redirects=True):
            return Resp()
    monkeypatch.setattr(vw, 'api', lambda: Client())


def test_visuals_package_is_written_one_file_per_section(harness, monkeypatch):
    """design/65 B12: as the options package (design/61): small files, tables one row per line, the world evidence in files of 25 clips."""
    ws, _ = harness
    pk = {'source': {'gaps': {'G1': {'start_frame': 0, 'end_frame': 100, 'requirement': 'r'}}}, 'prompt': 'p' * 3000, 'plan_schema': {'a': 1}, 'brief': {'purpose': 'x'},
          'intended_visuals': [{'heading': 'Scene 1', 'lines': ['A kiln.'], 'narration_starts': 'Every brick'}], 'generator_catalog': [{'provider': 'google'}],
          'world_evidence': [{'clip': f'c{i}', 'entities': [{'name': 'Mason'}], 'landmarks': ['wall']} for i in range(30)], 'script_digest': 'd'}
    fake_client(monkeypatch, pk)
    (ws / 'work' / 'visuals' ).mkdir(parents=True, exist_ok=True)
    (ws / 'work' / 'visuals' / 'world-9.json').write_text('stale', encoding='utf-8')
    files = vw.download_visuals_package({'code': 'VW-9', 'run_id': 'run-1'}, 'k')
    names = sorted(p.name for p in (ws / 'work' / 'visuals').iterdir())
    assert names == ['brief.json', 'gaps.json', 'generators.json', 'intended-visuals.json', 'prompt.md', 'rest.json', 'schema.json', 'world-1.json', 'world-2.json']
    assert (ws / 'work' / 'visuals' / 'prompt.md').read_text(encoding='utf-8').startswith('ppp')
    gaps = json.loads((ws / 'work' / 'visuals' / 'gaps.json').read_text(encoding='utf-8'))
    assert gaps == [{'gap_id': 'G1', 'start_frame': 0, 'end_frame': 100, 'requirement': 'r'}]
    world1 = (ws / 'work' / 'visuals' / 'world-1.json').read_text(encoding='utf-8')
    rows = [l for l in world1.split('\n') if '"clip"' in l]
    assert len(rows) == 25 and all(json.loads(l.strip().rstrip(',')) for l in rows)
    assert json.loads((ws / 'work' / 'visuals' / 'intended-visuals.json').read_text(encoding='utf-8')) == pk['intended_visuals']
    by = {f['file']: f for f in files}
    assert by['work/visuals/world-1.json']['rows'] == 25 and by['work/visuals/world-2.json']['rows'] == 5 and by['work/visuals/gaps.json']['rows'] == 1
    assert by['work/visuals/prompt.md']['for'] == 'read first' and by['work/visuals/intended-visuals.json']['for'] == 'treatment'
    assert not (ws / 'work' / 'visuals-package.json').exists()


def test_prepare_writes_the_files_and_prints_the_page_link(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'server_url', lambda: 'https://x.example')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'package': {'key': 'k'}, 'gaps': ['G1'], 'next': 'treatment'})
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'version': 'vwlib-x', 'always': [], 'steps': {}, 'compliance': None, 'map': '', 'field_sources': ''})   # design/68 L4
    fake_client(monkeypatch, {'source': {'gaps': {'G1': {'start_frame': 0, 'end_frame': 100}}}, 'prompt': 'p', 'plan_schema': {}, 'world_evidence': [], 'intended_visuals': [], 'generator_catalog': []})
    code, out, err = run(args(what='prepare'), capsys)
    assert code == 0 and out['visuals_page_url'] == 'https://x.example/runs/VW-9/visuals' and 'work/visuals/' in err and 'https://x.example/runs/VW-9/visuals' in err
    assert any(f['file'] == 'work/visuals/prompt.md' for f in out['files'])


def test_treatment_sequence_cap_and_budget_post_what_the_server_expects(harness, monkeypatch, capsys):
    ws, _ = harness
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'recorded': True, 'totals': {'images': 4}, 'estimate_inr': 160.0, 'cap_inr': 1000.0, 'shot_id': 'AN1', 'states': 3, 'warnings': [], 'kind': 'sequence'})
    (ws / 'out' / 'visual-treatment.json').write_text(json.dumps({'gaps': [{'gap_id': 'G1', 'routes': ['still'], 'picture': 'p', 'seconds': 5, 'images': 1}]}), encoding='utf-8')
    code, out, err = run(args(what='treatment', file='out/visual-treatment.json', quote='Yes, this treatment.'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/treatment') and posted[-1][1]['document']['gaps'][0]['gap_id'] == 'G1' and posted[-1][1]['quote'] == 'Yes, this treatment.'
    assert 'Treatment recorded' in err and '4 images' in err and '₹160' in err and '₹1,000' in err
    code, out, err = run(args(what='sequence', shot='AN1', refs=['R1,R2,R3'], quote='Yes, these states.'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/sequence') and posted[-1][1] == {'shot_id': 'AN1', 'reference_ids': ['R1', 'R2', 'R3'], 'quote': 'Yes, these states.'}
    assert '3 states' in err
    assert 'cap' not in vw.VISUALS_WHAT   # design/74 L26: no front end raises the cap
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'spent_inr': 120.0, 'cap_inr': 1000.0, 'left_inr': 880.0, 'images': 6, 'take_seconds': 0.0, 'planned': {'images': 40, 'video_seconds': 41.0, 'inr': 1128.0}, 'prices': {}})
    code, out, err = run(args(what='budget'), capsys)
    assert code == 0 and '₹120' in err and '₹1,000' in err and '₹1,128' in err and 'over the cap' in err and 'builder' in err and 'raise it' not in err


def test_check_line_prints_routes_images_and_cost(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'out' / 'visual-plan.json').write_text('{}', encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'status': 'valid', 'warnings': [{'shot_id': 'DG1', 'kind': 'graphic_short', 'message': 'm'}],
                                                                     'routes': {'video': 8, 'still': 1, 'graphic_sequence': 25, 'seconds': {'video': 41.0, 'still': 4.0, 'graphic_sequence': 180.0}, 'graphic_seconds': 184.0, 'images_estimated': 84},
                                                                     'budget': {'spent_inr': 0.0, 'cap_inr': 1000.0, 'planned_inr': 2008.0}})
    code, out, err = run(args(what='check', file='out/visual-plan.json'), capsys)
    assert code == 0 and 'check: valid' in err and '8 video (41 s)' in err and '25 graphic sequences (180 s)' in err and '1 still (4 s)' in err and '84 images' in err
    assert '₹2,008' in err and 'cap ₹1,000' in err and '1 warning' in err


def test_image_state_kind_posts_one_parent(harness, monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append(body) or {'reference_id': 'R2', 'job_id': 'j', 'model': 'm', 'op': 'edit'})
    code, out, err = run(args(what='image', element='E1', kind='state', parents='R1', prompt='the cavities appear'), capsys)
    assert code == 0 and posted[-1]['kind'] == 'state' and posted[-1]['parents'] == ['R1']


# ---------- the prompt, the steps and the command text ----------

def test_visuals_prompt_is_rewritten_for_v2():
    prompt = STAGES['visuals']['prompt']
    assert prompt.startswith('VW-PROCEDURE')
    for word in FORBIDDEN:
        assert word not in prompt, word
    for cmd in ('vw visuals frame', 'vw visuals image', 'vw visuals still', 'vw visuals take', 'vw visuals select', 'vw visuals asset', 'vw visuals record',
                'vw visuals treatment', 'vw visuals sequence'):
        assert cmd in prompt, cmd
    assert 'vw visuals cap' not in prompt   # design/74 L26
    assert 'design/45' in STAGES['visuals']['prompt_origin']
    # design/65: every picture is made in the pipeline; graphics move as state sequences; the team's intended visuals are a source; the treatment is recorded; the cap
    for gone in ('hand-made', 'editor makes', 'Nothing in this pipeline draws', 'shall the editor make them', 'the animation answer'):
        assert gone not in prompt, gone
    for kept in ('graphic sequence', 'two to four states', 'as its parent', 'on their instruction; never plan one', 'intended visuals', 'A plan is refused until the treatment is recorded',
                 'Text is not a reason', 'Footage first', 'no quota', '3–5 s', 'do not add a new rule while keeping shots that contradict it',
                 # design/66: segments at action boundaries, a start and an end image per take, the shared boundary picture, the cap
                 '--start R --end R2', 'cut where an action begins or ends', 'the end image of one segment is the start image of the next', 'segments plus one for video', '₹5,000'):
        assert kept in prompt, kept
    for gone in ('final state matters', 'a shot that needs a middle state is two shots', '₹1,000'):
        assert gone not in prompt, gone
    assert 'design/66' in STAGES['visuals']['prompt_origin']
    assert '--start R --end R2' in STAGES['visuals']['steps'][4] and '--kind keyframe --parents <start keyframe>' in STAGES['visuals']['steps'][3] and 'segments plus one' in STAGES['visuals']['steps'][1]


def test_steps_and_command_text_carry_the_new_flow():
    steps = STAGES['visuals']['steps']
    assert 'work/visuals/' in steps[0] and 'intended-visuals.json' in steps[0] and 'never by line offsets' in steps[0]
    assert 'vw visuals treatment' in steps[1] and 'visuals page' in steps[1] and 'Nothing else before this' in steps[1] and 'cost' in steps[1]
    assert 'vw visuals check' in steps[2] and 'propose' in steps[2] and 'accept --gaps all' in steps[2] and 'answer every warning' in steps[2]
    assert 'images.json' in steps[3] and 'their yes' in steps[3] and 'status --wait 300' in steps[3] and 'exactly' in steps[3] and '--kind state' in steps[3]   # design/73: the web step is the search on the operator's yes
    assert 'sequence --shot S --quote' in steps[4] and 'take --shots all' in steps[4] and 'select --job J --notes' in steps[4] and 'still --shot S --ref R' in steps[4] and '--end' in steps[4]
    assert 'record --gaps all' in steps[5]
    joined = ' '.join(steps)
    assert 'hand-made' not in joined and 'shall the editor' not in joined and 'on their instruction only' in joined   # the operator's file stays, never planned
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'take --shots all' in md and 'status --wait' in md and 'still --shot' in md and 'record --gaps all' in md and 'hand-made' not in md
    assert 'vw visuals treatment' in md and 'vw visuals sequence' in md and 'vw visuals cap' not in md and 'visuals page' in md and 'vw visuals reject' in md and 'vw visuals feedback' in md


# ---------- design/71: the VideoWizard answer form (F1), a face is a look reference (P5), a retry from the approved picture (P6) ----------

def test_prompt_and_steps_carry_the_videowizard_form_the_face_rule_and_the_retry_rule():
    prompt = STAGES['visuals']['prompt']
    assert "the library's VideoWizard answer form" in prompt and 'look reference' in prompt and 'never a parent' in prompt
    assert 'from the approved start' in prompt and 'not from the candidate chain' in prompt and 'from the last approved state' in prompt
    assert 'design/71' in STAGES['visuals']['prompt_origin']
    steps = STAGES['visuals']['steps']
    assert 'from the approved start' in steps[3] and 'look reference' in steps[3]


def test_prompt_and_steps_carry_the_boundary_rule_the_wave_rule_and_no_cap_command():
    """design/74 L24, L26, L27."""
    prompt, steps = STAGES['visuals']['prompt'], STAGES['visuals']['steps']
    assert 'only within one continuous shot' in prompt and 'a cut starts a new pair' in prompt
    assert 'one approval wave' in prompt and 'the builder changes the cap' in prompt and 'Only the operator raises the cap' not in prompt
    assert "next shot's answers" in steps[3] and 'status --wait' in steps[3] and 'vw visuals cap' not in ' '.join(steps)
    assert 'design/74' in STAGES['visuals']['prompt_origin']


def test_prompt_and_step_say_a_change_request_in_the_gap_words_is_a_revision():
    """design/75 (defect 20)."""
    prompt, steps = STAGES['visuals']['prompt'], STAGES['visuals']['steps']
    assert 'accepted afresh' in prompt and "every gap's words" in prompt
    assert 'accepted afresh' in steps[2] and 'before any picture' in steps[2]
    assert 'design/75' in STAGES['visuals']['prompt_origin']


def test_still_bind_and_approve_take_a_file_of_rows_in_order_and_stop_at_the_first_refusal(harness, monkeypatch, capsys):
    """design/77 L33b: nine stills, nine binds or nine approvals in one call each, as image --file."""
    ws, _ = harness
    (ws / 'out' / 'stills.json').write_text(json.dumps([{'shot': 'IM1', 'ref': 'R1', 'quote': 'yes'}, {'shot': 'IM2', 'ref': 'R2', 'quote': 'yes'}, {'shot': 'IM3', 'ref': 'R3', 'quote': 'yes'}]), encoding='utf-8')
    calls = []

    def req(method, path, json=None, **kw):
        calls.append((path, json))
        if json.get('shot_id') == 'IM2':
            return {'action': 'refused', 'message': 'shot IM2 is an animation shot'}, 422
        return {'shot_id': json.get('shot_id'), 'kind': 'still'}, 0
    monkeypatch.setattr(vw, 'request', req)
    code, out, err = run(args(what='still', file='out/stills.json'), capsys)
    assert code == 2 and [c[1]['shot_id'] for c in calls] == ['IM1', 'IM2'] and calls[0][1] == {'shot_id': 'IM1', 'reference_id': 'R1', 'quote': 'yes'}
    assert out['done'] == ['IM1'] and out['refused']['shot'] == 'IM2' and out['remaining'] == ['IM3'] and 'animation shot' in err
    (ws / 'out' / 'bindings.json').write_text(json.dumps([{'shot': 'VS1', 'refs': {'E1': ['R1', 'R2']}}, {'shot': 'VS2', 'refs': {'E1': ['R3']}, 'selectors': {'E1': {'R3': 'the chair'}}}]), encoding='utf-8')
    calls.clear()
    monkeypatch.setattr(vw, 'request', lambda m, p, json=None, **kw: calls.append((p, json)) or ({'shot_id': json['shot_id'], 'elements': list(json['references'])}, 0))
    code, out, err = run(args(what='bind', file='out/bindings.json'), capsys)
    assert code == 0 and calls[0][1]['references'] == {'E1': ['R1', 'R2']} and 'subject_selectors' not in calls[0][1] and calls[1][1]['subject_selectors'] == {'E1': {'R3': 'the chair'}}
    assert out['done'] == ['VS1', 'VS2'] and '2 shots bound' in err and 'packet' in err
    (ws / 'out' / 'approvals.json').write_text(json.dumps([{'ref': 'R1', 'sha': 'a' * 64, 'quote': 'yes'}, {'ref': 'R2', 'sha': 'b' * 64, 'quote': 'yes'}]), encoding='utf-8')
    calls.clear()
    monkeypatch.setattr(vw, 'request', lambda m, p, json=None, **kw: calls.append((p, json)) or ({'id': p.split('/')[-2], 'status': 'approved'}, 0))
    code, out, err = run(args(what='approve', file='out/approvals.json'), capsys)
    assert code == 0 and calls[0][0].endswith('/references/R1/approve') and calls[1][1] == {'sha256': 'b' * 64, 'quote': 'yes'} and out['done'] == ['R1', 'R2'] and '2 approved' in err


def test_prompt_and_steps_say_a_still_shot_needs_no_bind_and_name_the_file_forms():
    """design/77 L33a."""
    prompt, steps = STAGES['visuals']['prompt'], STAGES['visuals']['steps']
    assert 'Bind each video shot' in prompt and 'A still shot needs no bind' in prompt
    assert 'Still shots need no bind' in steps[4] and 'still --file' in steps[4] and 'bind --file' in steps[4] and 'approve --file' in steps[3]
    assert 'design/77' in STAGES['visuals']['prompt_origin']


def test_prompt_and_steps_carry_the_packet_order_the_material_rule_and_the_footage_character():
    """design/77 L35, L41, L42."""
    prompt, steps = STAGES['visuals']['prompt'], STAGES['visuals']['steps']
    assert 'never a start image before the packet' in steps[4] and 'the end image from the start candidate at once' in steps[4] and "after that shot's `bind` and `packet`" in steps[3]
    assert 'anything specific to the client that the footage shows' in prompt and 'never words alone' in prompt
    assert 'recorded footage character' in prompt and 'never from an assumption' in prompt


def test_revise_posts_the_gap_and_the_words_and_the_step_names_it(harness, monkeypatch, capsys):
    """design/76 (L32)."""
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'gap_id': 'G2', 'revise': True})
    code, out, err = run(args(what='revise', gap='G2', notes='AI video instead', quote='Make G2 an AI video.'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/revise') and posted[-1][1] == {'gap_id': 'G2', 'notes': 'AI video instead', 'quote': 'Make G2 an AI video.'} and 'under revision' in err
    assert 'vw visuals revise' in STAGES['visuals']['steps'][2] and 'vw visuals revise' in (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')


def test_elements_search_pick_and_nothing_fits_post_what_the_server_expects(harness, monkeypatch, capsys):
    """design/73 R1, R3, R4, R4b on the chat path."""
    ws, _ = harness
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'elements': [{'id': 'E1', 'name': 'Mason'}], 'matches': {'E1': [{'clip': 'c1', 'seconds': 2.0, 'entity': 'mason', 'score': 3}]}})
    code, out, err = run(args(what='elements'), capsys)
    assert code == 0 and json.loads((ws / 'work' / 'visuals' / 'elements.json').read_text(encoding='utf-8'))['matches']['E1'][0]['clip'] == 'c1' and 'E1: seen in c1 at 2.0 s' in err
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'search_id': 's1', 'element_id': 'E1', 'keywords': 'kadapari tool', 'results': [{'n': 1, 'site': 'a.in', 'width': 800, 'height': 600, 'title': 'k', 'page_url': 'https://a.in/p'}]})
    code, out, err = run(args(what='search', element='E1', keywords='kadapari tool', quote='Yes, search.'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/search') and posted[-1][1] == {'element_id': 'E1', 'keywords': 'kadapari tool', 'quote': 'Yes, search.'} and '1. a.in 800x600' in err and 'visuals page' in err
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'search_id': 's1', 'references': [{'id': 'r2'}, {'id': 'r1'}]})
    code, out, err = run(args(what='pick', search='s1', n='2,1', note=['2=avoid brand text'], quote='These two.'), capsys)
    assert code == 0 and posted[-1][1] == {'search_id': 's1', 'picks': [{'n': 2, 'note': 'avoid brand text'}, {'n': 1, 'note': ''}], 'quote': 'These two.'} and '2 web references' in err
    code, out, err = run(args(what='nothing-fits', search='s1', reason='wrong tool, try the Tamil name'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/nothing-fits') and posted[-1][1] == {'search_id': 's1', 'reason': 'wrong tool, try the Tamil name'}


def test_prompt_steps_and_doc_carry_the_sheet_per_element_the_people_rule_and_the_search_route():
    """design/73 R2, R5, R6."""
    prompt, steps = STAGES['visuals']['prompt'], STAGES['visuals']['steps']
    assert 'one generated reference sheet' in prompt and 'posture, dress, build and features' in prompt and 'vw visuals search' in prompt
    assert 'vw visuals elements' in steps[3] and 'two to six words' in steps[3] and 'pick --search' in steps[3] and 'never a parent for an edit' in steps[3]
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'vw visuals search' in md and 'pick' in md and 'design/73' in STAGES['visuals']['prompt_origin']


def test_round_posts_the_elements_the_verdicts_and_the_picks_and_status_waits_for_the_page(harness, monkeypatch, capsys):
    """design/79 Q3."""
    ws, _ = harness
    (ws / 'out' / 'reference-round.json').write_text(json.dumps([{'element_id': 'E1', 'frames': ['F1'], 'keywords': 'village mason Tamil Nadu'}, {'element_id': 'E2', 'frames': [], 'keywords': 'brick kiln'}]), encoding='utf-8')
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'pass': 1, 'elements': 2})
    code, out, err = run(args(what='round', file='out/reference-round.json'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/round') and posted[-1][1]['elements'][1] == {'element_id': 'E2', 'frames': [], 'keywords': 'brick kiln'} and 'two passes' in err and 'ask nothing per element' in err
    (ws / 'out' / 'round-verdicts.json').write_text(json.dumps({'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'search', 'keywords': 'clamp kiln'}}), encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'pass': 2, 'searched': ['E2'], 'errors': {}})
    code, out, err = run(args(what='round', verdicts='out/round-verdicts.json', quote='Yes, as ticked.'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/round/done') and posted[-1][1]['verdicts']['E2']['keywords'] == 'clamp kiln' and posted[-1][1]['quote'] == 'Yes, as ticked.' and 'pass 2' in err
    (ws / 'out' / 'round-picks.json').write_text(json.dumps({'s1': [{'n': 2, 'note': 'colour only'}]}), encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'complete': True, 'references': ['r1'], 'failed': {}})
    code, out, err = run(args(what='round', picks='out/round-picks.json', quote='These.'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/round/picks') and posted[-1][1]['picks'] == {'s1': [{'n': 2, 'note': 'colour only'}]} and 'one sheet per element' in err
    answers = [{'jobs': [], 'round': {'pass': 1}}, {'jobs': [], 'round': {'pass': 'complete'}}]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answers.pop(0) if answers else {'jobs': [], 'round': {'pass': 'complete'}})
    monkeypatch.setattr(vw.time, 'sleep', lambda s: None)
    code, out, err = run(args(what='status', wait=60), capsys)
    assert code == 0 and 'reference round at pass complete' in err and 'read the verdicts' in err and not answers   # it waited through pass 1


def test_status_prints_one_line_per_job_and_writes_the_whole_answer_to_the_run_folder(harness, monkeypatch, capsys):
    """design/81 (defect 21): over 100 KB of status never reached the assistant; the job ids must."""
    ws, _ = harness
    big = {'state': 'prepared', 'plan_digest': 'pd', 'round': None, 'budget': {'spent_inr': 1},
           'gaps': [{'gap_id': 'G1', 'shots': [{'shot_id': 'VS1'}, {'shot_id': 'VS2'}], 'words': 'x' * 40000}, {'gap_id': 'G2', 'shots': [{'shot_id': 'VS3'}], 'words': 'y' * 40000}],
           'references': [{'id': f'R{i}', 'element_id': 'E1', 'status': 'approved', 'checklist': ['c'] * 50} for i in range(40)],
           'jobs': [{'id': 'aaaaaaaa-0000-0000-0000-00000000000' + str(i), 'unit': f'VS{i}', 'provider': 'video', 'status': 'ready', 'error': None, 'checklist': ['c'] * 50} for i in (1, 2, 3)]
                   + [{'id': 'bbbbbbbb-0000-0000-0000-000000000009', 'unit': 'VS1', 'provider': 'video', 'status': 'failed', 'error': 'e' * 300, 'checklist': []}]}
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: big)
    code, out, err = run(args(what='status'), capsys)
    assert code == 0 and len(json.dumps(out)) < 4000 and 'work/visuals/status.json' in err
    assert [j['id'] for j in out['jobs']] == ['aaaaaaaa-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000002', 'aaaaaaaa-0000-0000-0000-000000000003', 'bbbbbbbb-0000-0000-0000-000000000009']
    assert out['jobs'][3]['error'] == 'e' * 80 and out['references'] == {'E1': {'approved': 40}} and 'checklist' not in json.dumps(out)
    assert json.loads((ws / 'work' / 'visuals' / 'status.json').read_text(encoding='utf-8'))['plan_digest'] == 'pd'
    code, out, err = run(args(what='status', shot='VS2'), capsys)
    assert [j['shot'] for j in out['jobs']] == ['VS2']
    code, out, err = run(args(what='status', gap='G1'), capsys)
    assert sorted(j['shot'] for j in out['jobs']) == ['VS1', 'VS1', 'VS2']


def test_fetch_and_select_take_the_shot_id_when_it_has_one_ready_take(harness, monkeypatch, capsys):
    """design/81 T2."""
    jobs_ = [{'id': 'aaaaaaaa-0000-0000-0000-000000000001', 'unit': 'VS1', 'provider': 'video', 'status': 'ready', 'checklist': []},
             {'id': 'aaaaaaaa-0000-0000-0000-000000000002', 'unit': 'VS2', 'provider': 'video', 'status': 'ready', 'checklist': []},
             {'id': 'aaaaaaaa-0000-0000-0000-000000000003', 'unit': 'VS2', 'provider': 'video', 'status': 'ready', 'checklist': []}]
    monkeypatch.setattr(vw, '_download', lambda m, key, name: name)
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'id': path.rsplit('/', 1)[1], 'status': 'ready', 'result': {'key': 'k', 'sha256': 's', 'evidence': {}}} if '/jobs/' in path else {'jobs': jobs_, 'references': []})
    code, out, err = run(args(what='fetch', job='VS1'), capsys)
    assert code == 0 and out['job'] == 'aaaaaaaa-0000-0000-0000-000000000001'
    code, out, err = run(args(what='fetch', job='VS2'), capsys)
    assert code == 2 and '2 ready takes' in out['message'] and '--shot VS2' in out['message']
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.update(body) or {'ok': True})
    code, out, err = run(args(what='select', job='VS1', quote='Watched, yes.'), capsys)
    assert code == 0 and posted['job_id'] == 'aaaaaaaa-0000-0000-0000-000000000001'


def test_frame_file_posts_the_rows_in_order_and_stops_at_the_first_refusal(harness, monkeypatch, capsys):
    """design/83 P2."""
    ws, _ = harness
    (ws / 'out' / 'frames.json').write_text(json.dumps([{'element': 'E1', 'clip': 'c1', 'at': 12.5, 'subject': 'the mason'}, {'element': 'E2', 'clip': 'c2', 'at': 3}, {'element': 'E3', 'clip': 'c9', 'at': 1}]), encoding='utf-8')
    posted = []
    def request(method, path, **kw):
        posted.append(kw['json'])
        return ({'action': 'refused', 'message': 'Unknown clip c9.'}, 422) if kw['json']['source_media_id'] == 'c9' else ({'id': 'R-' + kw['json']['element_id'], 'kind': 'frame'}, 0)
    monkeypatch.setattr(vw, 'request', request)
    code, out, err = run(args(what='frame', file='out/frames.json'), capsys)
    assert code == 2 and [p['element_id'] for p in posted] == ['E1', 'E2', 'E3'] and posted[0] == {'element_id': 'E1', 'name': 'frame-E1', 'kind': 'frame', 'subject': 'the mason', 'source_media_id': 'c1', 'requested_s': 12.5}
    assert 'E1@12.5' in json.dumps(out) and 'E2@3' in json.dumps(out) and 'Unknown clip c9' in json.dumps(out)
    assert 'frame --file' in json.dumps(STAGES['visuals']) and 'frame --file' in (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')


def test_steps_and_command_text_carry_the_long_blank_the_ai_run_and_the_continuity_rules():
    """design/84 V3, design/85 G1-G3."""
    vis, opt, doc = json.dumps(STAGES['visuals']), json.dumps(STAGES['options']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'ai_run' in vis and '3–5 s' in STAGES['visuals']['prompt'] and 'E2' in opt and 'blank over 12 s' in opt
    assert '--continuity' in doc and 'ai_run' in doc and 'E2, a blank over 12 s' in doc
    assert 'end_answer' in vis and '--variants 2' in vis and 'One change, two at most' in vis and 'close reference' in vis and 'checks every picture' in vis   # design/86 K1, K4, K5, K8
    assert '--end-answer' in doc and '--variants 2' in doc and 'one change per edit' in doc


def test_image_posts_two_variants_and_the_end_answer_written_with_the_start(harness, monkeypatch, capsys):
    """design/86 K1, K4."""
    ws, _ = harness
    (ws / 'out' / 'answers').mkdir(parents=True, exist_ok=True)
    (ws / 'out' / 'answers' / 'end.json').write_text(json.dumps({'status': 'ready', 'prompt': 'Image 1 is the start; the bucket empty.', 'checklist': [{'check': 'c', 'pass_when': 'p', 'weight': 'must'}]}), encoding='utf-8')
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'reference_id': 'R-a', 'reference_ids': ['R-a', 'R-b'], 'job_id': 'j', 'model': 'm', 'op': 'edit'}))
    code, out, err = run(args(what='image', element='E1', kind='keyframe', prompt='the wall', parents='R1', variants='2', end_answer='out/answers/end.json'), capsys)
    assert code == 0 and posted['variants'] == 2 and posted['end_prompt'] == 'Image 1 is the start; the bucket empty.' and posted['end_answer']['checklist'][0]['check'] == 'c'
    (ws / 'out' / 'images.json').write_text(json.dumps([{'element': 'E1', 'kind': 'keyframe', 'prompt': 'the wall', 'parents': 'R1', 'variants': 2, 'end_answer': 'out/answers/end.json'}]), encoding='utf-8')
    bodies = []
    monkeypatch.setattr(vw, 'request', lambda method, path, **kw: (bodies.append(kw['json']) or ({'reference_id': 'R-a', 'reference_ids': ['R-a', 'R-b'], 'job_id': 'j', 'model': 'm', 'op': 'edit'}, 0)))
    code, out, err = run(args(what='image', file='out/images.json'), capsys)
    assert code == 0 and bodies[0]['variants'] == 2 and bodies[0]['end_prompt'].startswith('Image 1')


def test_footage_tells_the_line_and_posts_a_correction_with_the_words(harness, monkeypatch, capsys):
    """design/88 F4."""
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'footage': {'line': 'Your footage: mirrorless camera, handheld, natural look (measured from the clips)'}})
    code, out, err = run(args(what='footage'), capsys)
    assert code == 0 and err.strip().startswith('Your footage: mirrorless camera')
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'line': 'Your footage: cinema camera, handheld, natural look (your correction)'}))
    code, out, err = run(args(what='footage', camera='cinema', quote='professional camera'), capsys)
    assert code == 0 and posted['path'].endswith('/visuals/footage') and posted['camera'] == 'cinema' and posted['support'] is None and posted['quote'] == 'professional camera' and 'your correction' in err


def test_clip_fills_a_shot_and_reuse_posts_the_operators_words(harness, monkeypatch, capsys):
    """design/89 B3, H7."""
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.append((path, body)) or {'in_s': 4.0, 'out_s': 14.0}))
    code, out, err = run(args(what='clip', shot='VS1', clip='c1', at='4', quote='this stretch', reuse='the only kiln shot', considered='a drone view: none', crop='0.1,0.1,0.7,0.7'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/clip') and posted[-1][1] == {'shot_id': 'VS1', 'clip_id': 'c1', 'in_s': 4.0, 'quote': 'this stretch', 'reuse': 'the only kiln shot',
                                                                                        'considered': 'a drone view: none', 'crop': [0.1, 0.1, 0.7, 0.7]}
    code, out, err = run(args(what='clip', shot='VS1', clip='c1', quote='this stretch'), capsys)   # finding 8: no --at is a refusal, never a traceback
    assert code == 2 and '--at' in out['message']
    code, out, err = run(args(what='reuse', shot='VS1', quote='Yes, reuse it.'), capsys)
    assert code == 0 and posted[-1] == (posted[-1][0], {'shot_id': 'VS1', 'quote': 'Yes, reuse it.'}) and posted[-1][0].endswith('/visuals/reuse')


def test_the_prompt_steps_and_doc_carry_timing_movement_and_no_repeats():
    """design/89 A2, B, H; the footage route no longer shows a frame of a clip that plays elsewhere."""
    prompt, steps, doc = STAGES['visuals']['prompt'], ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'over six seconds must earn' not in prompt and 'used in the edit or not, can be the still' not in prompt
    assert 'A still moves 5 %' in prompt and 'return_of' in prompt and "narration's pauses" in prompt and 'vw visuals clip' in prompt
    for needle in ('never inside a word', 'graphics push_in only', 'at most 4 s, a frozen one 3 s', 'reimagined shot', 'at least 60 s', 'safe enlargement', 'vw visuals reuse --shot S', 'frozen_seconds'):
        assert needle in steps, needle
    assert 'vw visuals clip --shot S' in doc and 'vw visuals reuse --shot S' in doc and 'return_of' in doc


def test_packet_before_bind_says_bind_first_and_bind_names_packet(harness, monkeypatch, capsys):
    """design/74 L31 (defect 19)."""
    monkeypatch.setattr(vw, 'request', lambda method, path, **kw: ({'action': 'refused', 'message': 'Bind references for this shot under the current accepted plan.'}, 422))
    code, out, err = run(args(what='packet', shot='VS1'), capsys)
    assert code == 2 and out['message'].startswith('Bind first: `vw visuals bind --shot VS1 --refs E1=R1,R2`, then `vw visuals packet --shot VS1`')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'shot_id': 'VS1', 'elements': ['E1']})
    code, out, err = run(args(what='bind', shot='VS1', refs=['E1=R1']), capsys)
    assert code == 0 and 'vw visuals packet --shot VS1' in err


def test_fetch_prints_the_checklist_beside_the_picture_and_the_take(harness, monkeypatch, capsys):
    """design/74 L6."""
    lines = [{'check': 'label', 'pass_when': 'reads air', 'weight': 'must'}, {'check': 'bucket', 'pass_when': 'empty', 'weight': 'should'}]
    monkeypatch.setattr(vw, '_download', lambda m, key, name: name)
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'id': 'j1', 'status': 'ready', 'result': {'key': 'k', 'sha256': 's', 'evidence': {}}} if path.endswith('/jobs/j1')
                        else {'references': [{'id': 'R1', 'sha256': 's', 'checklist': lines}], 'jobs': [{'id': 'j1', 'checklist': lines}]})
    code, out, err = run(args(what='fetch', ref='R1'), capsys)
    assert code == 0 and out['checklist'] == lines and 'must: label — reads air' in err and 'should: bucket — empty' in err
    code, out, err = run(args(what='fetch', job='j1'), capsys)
    assert code == 0 and out['checklist'] == lines and 'must: label — reads air' in err


def test_reject_posts_the_words_and_feedback_writes_the_yaml(harness, monkeypatch, capsys):
    """design/74 L7."""
    ws, _ = harness
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'id': 'R1', 'status': 'rejected'})
    code, out, err = run(args(what='reject', ref='R1', notes='the bucket is full', quote='No, the bucket is full.'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/references/R1/reject') and posted[-1][1] == {'notes': 'the bucket is full', 'quote': 'No, the bucket is full.'} and 'rejected' in err
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'records': 2, 'yaml': '- app: videowizard\n  verdict: pass\n- app: videowizard\n  verdict: reject\n'})
    code, out, err = run(args(what='feedback'), capsys)
    assert code == 0 and (ws / 'work' / 'visuals' / 'feedback.yaml').read_text(encoding='utf-8').startswith('- app: videowizard\n') and '2 records' in err


def test_prepare_writes_the_videowizard_answer_form_under_always(harness, monkeypatch, capsys):
    ws, _ = harness
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'package': {'key': 'k'}, 'gaps': ['G1'], 'library_version': 'vwlib-x'})
    monkeypatch.setattr(vw, 'download_visuals_package', lambda m, key: [])
    lib = {'version': 'vwlib-x', 'always': [{'path': 'library/forms/answer-form.videowizard.md', 'text': '# Answer form, VideoWizard cut'}], 'steps': {}, 'map': '# map', 'field_sources': '# f'}
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: lib if path.endswith('/library') else {})
    code, out, err = run(args(what='prepare'), capsys)
    form = ws / 'work' / 'visuals' / 'library' / 'always' / 'forms__answer-form.videowizard.md'
    assert code == 0 and form.read_text(encoding='utf-8').endswith('# Answer form, VideoWizard cut\n')


def test_spec_posts_the_operators_words_and_measure_posts_the_frames_and_question(harness, monkeypatch, capsys):
    """design/89 D2, D4."""
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.append((path, body)) or {'shot_id': 'DG1', 'table': [{'part': 'leaf', 'measure': 'thickness', 'size': '110 mm', 'source': 'brochure', 'status': 'confirmed'}],
                                                                                                     'measure_id': 'm1', 'measurements': [{'part': 'brick', 'measure': 'length', 'value': 230, 'unit': 'mm', 'source': 'clip c1 at 4.5 s'}]}))
    code, out, err = run(args(what='spec', shot='DG1'), capsys)
    assert code == 2 and '--quote' in out['message'] and not posted
    code, out, err = run(args(what='spec', shot='DG1', quote='The sizes are right.'), capsys)
    assert code == 0 and posted[-1] == (posted[-1][0], {'shot_id': 'DG1', 'quote': 'The sizes are right.'}) and posted[-1][0].endswith('/visuals/spec') and 'leaf thickness 110 mm' in err
    code, out, err = run(args(what='measure', refs=['F1,F2'], question='How long is a brick?'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/measure') and posted[-1][1] == {'reference_ids': ['F1', 'F2'], 'question': 'How long is a brick?'} and 'clip c1 at 4.5 s' in err
    code, out, err = run(args(what='measure', refs=['F1']), capsys)
    assert code == 2 and '--question' in out['message']


def test_the_prompt_and_steps_carry_claims_style_and_the_drawing_spec():
    """design/89 C, D."""
    prompt, steps, doc = STAGES['visuals']['prompt'], ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for needle in ('claims_left_out', 'graphic_style', 'drawing_spec', 'never invented', 'not to scale', 'vw visuals measure', 'vw visuals spec', '--kind style'):
        assert needle in prompt and needle in steps, needle
    assert 'vw visuals spec --shot S' in doc and 'vw visuals measure --refs' in doc


def test_status_shows_a_takes_marks_with_their_seconds():
    """design/91 N3."""
    st = {'state': 'prepared', 'jobs': [{'id': 'j1', 'unit': 'VS1', 'provider': 'video', 'status': 'ready', 'check_marks': [{'check': 'appear or vanish', 'at_s': 5.2}, {'check': 'planned end', 'at_s': None}]},
                                        {'id': 'j2', 'unit': 'VS2', 'provider': 'video', 'status': 'ready', 'check_marks': []}]}
    jobs_ = vw._short_status(st)['jobs']
    assert jobs_[0]['marked'] == ['appear or vanish at 5.2 s', 'planned end'] and 'marked' not in jobs_[1]


def test_the_prompt_and_steps_carry_the_change_list_the_action_budget_and_the_take_check():
    """design/91 N1, N2, N3; the 3,500-word limit is gone (SK, 23 Oct)."""
    prompt, steps, doc = STAGES['visuals']['prompt'], ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for needle in ('`changes`', '`min_s`', 'marks any difference', 'Gemini reads every ready take'):
        assert needle in prompt, needle
    for needle in ('`changes`', '`min_s`', 'is marked', 'read by Gemini first'):
        assert needle in steps, needle
    assert '`changes`' in doc and '`min_s`' in doc


def test_an_image_names_the_shot_it_is_for(harness, monkeypatch, capsys):
    """design/91 N8."""
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.append((path, body)) or {'model': 'gpt-image-2.5', 'reference_id': 'R1'}))
    code, out, err = run(args(what='image', element='E1', kind='keyframe', prompt='A mason at the wall.', shot='VS1'), capsys)
    assert code == 0 and posted[-1][1]['shot_id'] == 'VS1'
    run(args(what='image', element='E1', kind='keyframe', prompt='A mason at the wall.'), capsys)
    assert 'shot_id' not in posted[-1][1]


def test_the_procedures_carry_the_step_map_facts_words_and_depicts():
    """design/91 batch 2."""
    op, osteps = STAGES['options']['prompt'], ' '.join(STAGES['options']['steps'])
    for needle in ('`steps`', 'BEAT_03.S2', '`carries_over`', '`moves_place`', 'N17 and N14'):
        assert needle in op, needle
    assert '`steps` map' in osteps
    vp, vsteps, doc = STAGES['visuals']['prompt'], ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for needle in ('`descriptors`', '`evidence`', '`visual_facts`', '`fact_ids`', 'never invented', '`depicts`', '`carries_over`', '`--shot S`'):
        assert needle in vp and needle in vsteps, needle
    assert '`steps` map' in doc and '`depicts`' in doc


def test_the_procedure_carries_life_intent_one_world_and_one_message():
    """design/91 batch 3."""
    vp, vsteps, doc = STAGES['visuals']['prompt'], ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for needle in ('`activity_level`', 'comes into view', '`studio_background`', '`message`', '`adds`'):
        assert needle in vp and needle in vsteps, needle
    assert 'light and colour' in vp and '`activity_level`' in doc and '`message`' in doc


def test_the_procedure_carries_builds_labels_the_frame_and_transitions():
    """design/91 batch 4 (SK: an 8-frame dissolve at graphics; labels 4 %, titles 6 %)."""
    vp, vsteps, doc = STAGES['visuals']['prompt'], ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for needle in ('4 % of the frame height', '`transition_in`', '`transition_reason`', '1.35×'):
        assert needle in vp and needle in vsteps and needle in doc, needle
    assert '8 frames' in vp and 'titles 6 %' in vp and 'state per claim' in vsteps

def test_approve_says_where_the_picture_went_and_unplace_sequence_and_move_post_the_words(harness, monkeypatch, capsys):
    """design/94 R1.6-R1.9."""
    posted = []
    replies = {'/approve': {'id': 'K2', 'status': 'approved', 'placed': 'DG1', 'replaced': 'K1'}, '/unplace': {'shot_id': 'DG1', 'removed': 'K2'},
               '/sequence': {'shot_id': 'AN1', 'states': 3, 'warnings': []}, '/still': {'shot_id': 'DG1', 'kind': 'still', 'reference_id': 'K1'}}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or next(v for k, v in replies.items() if path.endswith(k)))
    code, out, err = run(args(what='approve', ref='K2', sha='s', quote='The second.'), capsys)
    assert code == 0 and 'placed in DG1' in err and 'K1' in err
    code, out, err = run(args(what='unplace', shot='DG1', quote='Take it out.'), capsys)
    assert posted[-1][0].endswith('/unplace') and posted[-1][1] == {'shot_id': 'DG1', 'quote': 'Take it out.'} and 'DG1' in err
    run(args(what='sequence', shot='AN1', quote='yes'), capsys)
    assert posted[-1][1] == {'shot_id': 'AN1', 'reference_ids': [], 'quote': 'yes'}
    run(args(what='still', shot='DG1', ref='K1', quote='yes', move='Use it here.'), capsys)
    assert posted[-1][1]['move'] == 'Use it here.'


def test_the_procedure_says_approving_places_and_how_to_take_a_picture_out():
    """design/94."""
    vp, vsteps, doc = STAGES['visuals']['prompt'], ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for text in (vsteps, doc):
        assert 'approving places it' in text and 'vw visuals unplace --shot' in text and '--refs R1,R2,R3' not in text

def test_the_plugin_sends_its_own_version_with_every_call(monkeypatch):
    """design/95 F5: the version from plugin.json, not an environment variable nothing sets."""
    version = json.loads((PLUGIN / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))['version']
    monkeypatch.delenv('VW2_PLUGIN_VERSION', raising=False)
    assert vw.plugin_version() == version
    monkeypatch.setenv('VW2_PLUGIN_VERSION', '0.0.1')   # the server tests simulate an old plugin this way
    assert vw.plugin_version() == '0.0.1'
    monkeypatch.setattr(vw, 'server_url', lambda: 'https://example.test')
    monkeypatch.setattr(vw, 'session', lambda: {'token': 't'})
    assert vw.api().headers['X-VW-Plugin'] == vw.VERSION


def test_approve_file_names_each_placement(harness, monkeypatch, capsys):
    """design/95 F8."""
    ws, _ = harness
    (ws / 'out' / 'approvals.json').write_text(json.dumps([{'ref': 'K2', 'sha': 's', 'quote': 'yes'}, {'ref': 'S1', 'sha': 's', 'quote': 'yes'}]), encoding='utf-8')
    replies = {'K2': {'id': 'K2', 'placed': 'DG1', 'replaced': 'K1'}, 'S1': {'id': 'S1'}}
    monkeypatch.setattr(vw, 'request', lambda method, path, wait=None, **kw: (replies[path.split('/')[-2]], 0))
    code, out, err = run(args(what='approve', file='out/approvals.json'), capsys)
    assert code == 0 and 'K2 placed in DG1 (replaces K1)' in err and 'S1 placed' not in err

def test_fix_is_asked_for_and_says_its_line_and_cost(harness, monkeypatch, capsys):
    """design/96 X1: a fix only on request."""
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'reference_id': 'F1', 'of': 'K1', 'for': 'label: Rat-trap bond', 'cost_inr': 4.0})
    code, out, err = run(args(what='fix', ref='K1'), capsys)
    assert code == 0 and posted[-1][0].endswith('/references/K1/fix') and "label: Rat-trap bond" in err and '₹4' in err and 'F1' in err


def test_budget_counts_fixes_apart(harness, monkeypatch, capsys):
    """design/96 X3."""
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'spent_inr': 64.0, 'cap_inr': 5000, 'left_inr': 4936, 'images': 16, 'fixes': 2, 'planned': {'inr': 0}})
    code, out, err = run(args(what='budget'), capsys)
    assert 'images: 14 requested + 2 fixes' in err


def test_the_procedure_says_fixes_are_asked_for_and_names_the_graphic_kind():
    """design/96."""
    vp, vsteps, doc = STAGES['visuals']['prompt'], ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for text in (vsteps, doc):
        assert 'vw visuals fix --ref' in text and 'Image 1 to Image N' in text
    assert '`graphic_kind`' in vp and '`graphic_kind`' in vsteps

def test_status_lists_each_waiting_item_with_its_label_and_link(harness, monkeypatch, capsys):
    """design/97 W4: the label and the link, never only "on the page"."""
    st = {'jobs': [], 'references': [], 'gaps': [], 'waiting': [{'label': 'Still · DG1', 'link': '/runs/VW-9/visuals#pictures/DG1/K1', 'step': 'pictures'},
                                                               {'label': 'Take · VS1', 'link': '/runs/VW-9/visuals#takes/VS1/j1', 'step': 'takes'}]}
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: st)
    monkeypatch.setattr(vw, 'server_url', lambda: 'https://vw.test')
    code, out, err = run(args(what='status'), capsys)
    assert '2 waiting for the operator: Still · DG1 https://vw.test/runs/VW-9/visuals#pictures/DG1/K1; Take · VS1 https://vw.test/runs/VW-9/visuals#takes/VS1/j1' in err


@pytest.mark.parametrize('what, extra', [('approve', {'ref': 'K1', 'sha': 's'}), ('reject', {'ref': 'K1', 'notes': 'n'}), ('sequence', {'shot': 'AN1'}),
                                         ('unplace', {'shot': 'DG1'}), ('select', {'job': '11111111-1111-1111-1111-111111111111'})])
def test_a_verdict_prints_what_happens_next(harness, monkeypatch, capsys, what, extra):
    """design/97 A4: the server's line, the same on the page."""
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'next': 'Approved: in the film at 0:14–0:17 (DG1).'})
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'jobs': []})   # select looks the job up first
    code, out, err = run(args(what=what, quote='yes', **extra), capsys)
    assert 'Approved: in the film at 0:14–0:17 (DG1).' in err


def test_the_procedure_gives_the_label_and_the_link():
    """design/97 W4."""
    vsteps, doc = ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for text in (vsteps, doc):
        assert 'the label and the link' in text

def test_the_procedure_says_the_first_answer_approves_a_reason_is_optional_and_the_final_needs_no_words():
    """design/98."""
    options, master, voice = (' '.join(STAGES[k]['steps']) for k in ('options', 'master', 'voice'))
    doc = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'the first answer approves the options' in options and 'the first answer approves the options' in master and 'the first answer approves the options' in doc
    assert 'A REJECT is followed by one question for the reason' not in master and 'the reason is optional' in master
    assert 'their reply as `--quote` if they gave one' in voice

@pytest.mark.parametrize('what, extra', [('approve', {'ref': 'K1', 'sha': 's'}), ('reject', {'ref': 'K1'}), ('sequence', {'shot': 'AN1'}), ('still', {'shot': 'DG1', 'ref': 'K1'}),
                                         ('unplace', {'shot': 'DG1'}), ('select', {'job': '11111111-1111-1111-1111-111111111111'}), ('pick', {'search': 's1', 'n': '1,2'})])
def test_a_click_needs_no_quote_in_chat_either(harness, monkeypatch, capsys, what, extra):
    """design/99 C2-C5: the words are optional; the server records who and when."""
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append(body) or {'next': 'ok.', 'references': [], 'shot_id': 'S', 'states': 1})
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'jobs': []})
    code, out, err = run(args(what=what, **extra), capsys)
    assert code == 0 and posted and posted[-1]['quote'] == ''


def test_the_procedure_says_a_click_needs_no_words():
    """design/99."""
    vsteps, doc = ' '.join(STAGES['visuals']['steps']), (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for text in (vsteps, doc):
        assert 'no typed words' in text

def test_the_procedure_says_picks_are_approved_when_saved():
    """design/100 S1."""
    text = STAGES['visuals']['prompt'] + ' '.join(STAGES['visuals']['steps'])
    assert 'the picked pictures are approved when saved' in text
    assert 'approve with its hash, then generate' not in (PLUGIN / 'scripts' / 'vw.py').read_text(encoding='utf-8')


def test_a_rejected_take_is_not_counted_ready_and_a_shot_names_its_one_unrejected_take(harness, monkeypatch, capsys):
    """Defect 30 (VW-7): status listed two rejected takes as ready."""
    answer = jobs_answer(('j1', 'VS1', 'video', 'ready'), ('j2', 'VS1', 'video', 'ready'), ('j3', 'VS1', 'video', 'ready'))
    answer['jobs'][0]['verdict'] = answer['jobs'][1]['verdict'] = 'rejected'
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answer)
    code, out, err = run(args(what='status'), capsys)
    assert code == 0 and 'all done: 1 ready, 2 rejected' in err
    assert vw._take_job('/api/runs/run-1/visuals', 'VS1') == 'j3'


# ---------- design/106 T3, T5 ----------

def test_a_flag_the_subcommand_does_not_use_is_refused_by_name(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda *a, **k: pytest.fail('nothing may reach the server'))
    monkeypatch.setattr(vw, 'write', lambda *a, **k: pytest.fail('nothing may reach the server'))
    code, out, err = run(args(what='select', job='j1', decision='reject', notes='a cut', quote='no'), capsys)
    assert code == 2 and 'vw visuals review --job J --decision rejected' in out['message']
    code, out, err = run(args(what='approve', ref='r1', sha='s', shot='S1'), capsys)
    assert code == 2 and '--shot' in out['message'] and 'approve' in out['message']


def test_status_wait_keeps_waiting_for_running_jobs_and_names_an_old_failed_job_once(harness, monkeypatch, capsys):
    _, slept = harness
    answers = [jobs_answer(('j1', 'VS1', 'video', 'running'), ('j0', 'VS1', 'video', 'failed', 'Storage not reachable')),
               jobs_answer(('j1', 'VS1', 'video', 'ready'), ('j0', 'VS1', 'video', 'failed', 'Storage not reachable'))]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answers.pop(0) if answers else jobs_answer(('j1', 'VS1', 'video', 'ready'), ('j0', 'VS1', 'video', 'failed', 'x')))
    code, out, err = run(args(what='status', wait=600), capsys)
    assert code == 0 and slept == [15] and 'all done: 1 ready' in err and err.count('need a decision') == 1 and 'j0' in err
