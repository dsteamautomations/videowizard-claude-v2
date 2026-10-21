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


def test_prepare_take_needs_the_end_image_before_any_request(harness, monkeypatch, capsys):
    """design/66 D1: every take has a start and an end image; the plugin refuses without one and posts nothing."""
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'preparation_id': 'p1', 'duration_seconds': 6}))
    code, out, err = run(args(what='prepare-take', shot='VS1', start='R1', motion='pours', subject=['E1="pours water"']), capsys)
    assert code == 2 and 'start and an end image' in out['message'] and '--end' in out['message'] and not posted
    code, out, err = run(args(what='prepare-take', shot='VS1', start='R1', end='R2', motion='pours', subject=['E1="pours water"']), capsys)
    assert code == 0 and posted['path'].endswith('/prepare-take') and posted['start_image'] == 'R1' and posted['end_image'] == 'R2' and posted['motion_prompt'] == 'pours'


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
    code, out, err = run(args(what='cap', inr='1500', quote='Raise it.'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/cap') and posted[-1][1] == {'inr': 1500.0, 'quote': 'Raise it.'}
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'spent_inr': 120.0, 'cap_inr': 1000.0, 'left_inr': 880.0, 'images': 6, 'take_seconds': 0.0, 'planned': {'images': 40, 'video_seconds': 41.0, 'inr': 1128.0}, 'prices': {}})
    code, out, err = run(args(what='budget'), capsys)
    assert code == 0 and '₹120' in err and '₹1,000' in err and '₹1,128' in err and 'over the cap' in err


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
    assert len(prompt.split()) <= 3500
    for word in FORBIDDEN:
        assert word not in prompt, word
    for cmd in ('vw visuals frame', 'vw visuals image', 'vw visuals still', 'vw visuals take', 'vw visuals select', 'vw visuals asset', 'vw visuals record',
                'vw visuals treatment', 'vw visuals sequence', 'vw visuals cap'):
        assert cmd in prompt, cmd
    assert 'design/45' in STAGES['visuals']['prompt_origin']
    # design/65: every picture is made in the pipeline; graphics move as state sequences; the team's intended visuals are a source; the treatment is recorded; the cap
    for gone in ('hand-made', 'editor makes', 'Nothing in this pipeline draws', 'shall the editor make them', 'the animation answer'):
        assert gone not in prompt, gone
    for kept in ('graphic sequence', 'two to four states', 'as its parent', 'on their instruction; never plan one', 'intended visuals', 'A plan is refused until the treatment is recorded',
                 'Text is not a reason', 'Footage first', 'no quota', 'three to five seconds', 'do not add a new rule while keeping shots that contradict it',
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
    assert 'images.json' in steps[3] and 'warning' in steps[3] and 'status --wait 300' in steps[3] and 'exactly' in steps[3] and '--kind state' in steps[3]
    assert 'sequence --shot S --refs' in steps[4] and 'take --shots all' in steps[4] and 'select --job J --notes' in steps[4] and 'still --shot S --ref R' in steps[4] and '--end' in steps[4]
    assert 'record --gaps all' in steps[5]
    joined = ' '.join(steps)
    assert 'hand-made' not in joined and 'shall the editor' not in joined and 'on their instruction only' in joined   # the operator's file stays, never planned
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'take --shots all' in md and 'status --wait' in md and 'still --shot' in md and 'record --gaps all' in md and 'hand-made' not in md
    assert 'vw visuals treatment' in md and 'vw visuals sequence' in md and 'vw visuals cap' in md and 'visuals page' in md
