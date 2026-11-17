"""design/211 part A, the tool and the helper: `vw visuals digest | trial | look` with the server faked, the finder's file, the guard."""
import json

from conftest import PLUGIN, run_hook
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

THEN = 'The references come next. Run `vw visuals digest`.'


def clip(i):
    return {'clip': f'C{i:03d}', 'name': f'C{i:03d}.mp4', 'duration_s': 10.0, 'overview': f'What clip {i} shows.', 'light': 'sun',
            'entities': [{'name': f'thing_{i}', 'kind': 'tool'}], 'parts': [{'id': f'C{i:03d}-a', 'in_s': 0.0, 'out_s': 10.0, 'hero_s': 4.0, 'action': 'x'}]}


def test_digest_writes_the_index_the_clip_files_of_25_and_the_things(harness, monkeypatch, capsys):
    ws, _ = harness
    answer = {'digest': {'contract': 'vw2-refs-digest-v1', 'clips': [clip(i) for i in range(1, 61)], 'not_searched': [{'clip': 'C099', 'name': 'C099.mp4', 'reason': 'no analysis'}]},
              'things': [{'id': 'PAN', 'name': 'A pan', 'views': ['side'], 'found': None}, {'id': 'LID', 'name': 'A lid', 'views': [], 'found': 'found'}],
              'rule': 'the rule of the server', 'limits': {'trials_per_thing': 8, 'kept_per_thing': 3, 'things_per_helper': 5, 'helpers': 6}, 'then': THEN}
    asked = []
    monkeypatch.setattr(vw, 'call', lambda method, path, **k: asked.append((method, path)) or answer)
    stale = ws / 'work' / 'visuals' / 'digest' / 'clips-9.json'
    stale.parent.mkdir(parents=True)
    stale.write_text('[]', encoding='utf-8')
    code, out, err = run(args(what='digest'), capsys)
    assert code == 0 and asked == [('GET', '/api/runs/run-1/visuals/digest')]
    assert err.strip() == THEN                                                             # the server's sentence, and no sentence of the tool's own
    folder = ws / 'work' / 'visuals' / 'digest'
    files = sorted(p.name for p in folder.glob('clips-*.json'))
    assert files == ['clips-1.json', 'clips-2.json', 'clips-3.json'] and not stale.exists()
    parts = [json.loads((folder / f).read_text(encoding='utf-8')) for f in files]
    assert [len(p) for p in parts] == [25, 25, 10] and parts[2][-1]['clip'] == 'C060' and parts[0][0]['parts'][0]['hero_s'] == 4.0
    index = json.loads((folder / 'index.json').read_text(encoding='utf-8'))
    assert len(index) == 60 and index[0] == {'clip': 'C001', 'name': 'C001.mp4', 'duration_s': 10.0, 'overview': 'What clip 1 shows.', 'entities': ['thing_1'], 'file': 'work/visuals/digest/clips-1.json'}
    assert index[25]['file'] == 'work/visuals/digest/clips-2.json' and index[59]['file'] == 'work/visuals/digest/clips-3.json'
    things = json.loads((ws / 'work' / 'visuals' / 'refs' / 'things.json').read_text(encoding='utf-8'))
    assert things['rule'] == 'the rule of the server' and things['limits']['trials_per_thing'] == 8 and [t['id'] for t in things['things']] == ['PAN', 'LID']
    assert things['not_searched'][0]['clip'] == 'C099'
    assert out['things'] == {'PAN': None, 'LID': 'found'} and out['clips'] == 60 and out['then'] == THEN   # a run taken over sees what is left


def test_trial_sends_the_rows_and_puts_each_frame_under_its_element(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'work' / 'g1.trials.json').write_text(json.dumps([{'element': 'PAN', 'clip': 'C001', 'at': 4.0}, {'element': 'LID', 'clip': 'C001', 'at': '4'},
                                                           {'element': 'PAN', 'clip': 'C002', 'at': 99}]), encoding='utf-8')
    sent, got = [], []
    answer = {'trials': [{'id': 't0a', 'clip': 'C001', 'at_s': 4.0, 'key': 'run-1/visuals/trials/t0a.jpg', 'elements': ['PAN', 'LID', 'OTHER']}],
              'failed': [{'clip': 'C002', 'at_s': 99.0, 'reason': 'C002 at 99.0 s: not a clip of this run, or the time is outside it.'}], 'left': {'PAN': 7, 'LID': 7},
              'then': 'Read each trial frame, then record what you saw.'}
    monkeypatch.setattr(vw, 'write', lambda path, body, **k: sent.append((path, body)) or answer)
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: got.append((key, rel)))
    code, out, err = run(args(what='trial', file='work/g1.trials.json'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/trials', {'frames': [{'element_id': 'PAN', 'clip': 'C001', 'at_s': 4.0}, {'element_id': 'LID', 'clip': 'C001', 'at_s': 4.0},
                                                                               {'element_id': 'PAN', 'clip': 'C002', 'at_s': 99.0}]})]
    assert got == [('run-1/visuals/trials/t0a.jpg', 'work/visuals/trials/PAN/t0a.jpg'), ('run-1/visuals/trials/t0a.jpg', 'work/visuals/trials/LID/t0a.jpg')]   # not for a thing this call did not ask
    assert out['frames'][0] == {'trial': 't0a', 'element': 'PAN', 'clip': 'C001', 'at_s': 4.0, 'file': 'work/visuals/trials/PAN/t0a.jpg'} and out['left'] == {'PAN': 7, 'LID': 7}
    assert err.strip() == 'C002 at 99.0 s: C002 at 99.0 s: not a clip of this run, or the time is outside it. Read each trial frame, then record what you saw.'


def test_with_no_helper_the_same_commands_work_one_by_one(harness, monkeypatch, capsys):
    ws, _ = harness
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, **k: sent.append((path, body)) or {'trials': [], 'failed': [], 'left': {'PAN': 7}, 'then': 'next'})
    code, out, err = run(args(what='trial', element='PAN', clip='C001', at='12.5'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/trials', {'frames': [{'element_id': 'PAN', 'clip': 'C001', 'at_s': 12.5}]})] and err.strip() == 'next'
    sent.clear()
    code, out, _ = run(args(what='trial', element='PAN'), capsys)
    assert code == 2 and sent == [] and '--element E --clip C --at <seconds>' in out['message']
    code, out, _ = run(args(what='trial', element='PAN', clip='C001', at='soon'), capsys)
    assert code == 2 and sent == [] and '--at takes a number' in out['message']


def test_look_sends_the_file_and_says_the_servers_refusals_and_what_next(harness, monkeypatch, capsys):
    ws, _ = harness
    doc = {'by': 'helper', 'things': [{'element': 'PAN', 'clips': ['C001'], 'note': 'n', 'looks': [{'trial': 't0a', 'view': 'side', 'verdict': 'pass', 'seen': 'whole', 'keep': True}]},
                                      {'element': 'LID', 'clips': []}]}
    (ws / 'work' / 'g1.looks.json').write_text(json.dumps(doc), encoding='utf-8')
    sent = []
    answer = {'recorded': ['PAN'], 'refused': {'LID': 'LID: give its looks, or the clips searched, or why it was not searched (`not_searched`).'}, 'results': {'PAN': 'found'},
              'kept': {'PAN': ['r1']}, 'left': ['LID'], 'then': '1 thing(s) recorded. 1 are not searched yet: LID.'}
    monkeypatch.setattr(vw, 'write', lambda path, body, **k: sent.append((path, body)) or answer)
    code, out, err = run(args(what='look', file='work/g1.looks.json'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/looks', doc)] and out == answer
    assert err.strip() == 'LID: give its looks, or the clips searched, or why it was not searched (`not_searched`). 1 thing(s) recorded. 1 are not searched yet: LID.'
    sent.clear()
    (ws / 'work' / 'bad.json').write_text(json.dumps(doc['things']), encoding='utf-8')
    code, out, _ = run(args(what='look', file='work/bad.json'), capsys)
    assert code == 2 and sent == [] and 'must be {by, things:' in out['message']
    code, out, _ = run(args(what='look'), capsys)
    assert code == 2 and sent == []


def test_a_flag_the_command_does_not_read_is_refused_by_name(harness, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda *a, **k: sent.append(a) or {})
    monkeypatch.setattr(vw, 'call', lambda *a, **k: sent.append(a) or {})
    for kw, flag in (({'what': 'digest', 'element': 'PAN'}, '--element'), ({'what': 'trial', 'file': 'x.json', 'quote': 'yes'}, '--quote'), ({'what': 'look', 'file': 'x.json', 'clip': 'C1'}, '--clip')):
        code, out, _ = run(args(**kw), capsys)
        assert code == 2 and out['message'] == f"vw visuals {kw['what']} does not take {flag}; nothing was sent.", kw
    assert sent == []


def test_the_guard_allows_the_two_helpers_and_still_blocks_another_name(tmp_path):
    for helper in ('vw:vw-reference-finder', 'vw-reference-finder', 'vw:vw-set-look', 'vw-set-look'):
        assert run_hook('guard.py', {'tool_name': 'Agent', 'tool_input': {'subagent_type': helper, 'prompt': 'g1: PAN, LID'}}, tmp_path)[0] == 0, helper
    assert run_hook('guard.py', {'tool_name': 'Agent', 'tool_input': {'subagent_type': 'vw-frame-finder', 'prompt': 'PAN'}}, tmp_path)[0] == 2


def test_the_finders_file_has_its_front_matter_and_no_rule_text_of_its_own():
    text = (PLUGIN / 'agents' / 'vw-reference-finder.md').read_text(encoding='utf-8')
    assert text.startswith('---\nname: vw-reference-finder\n') and 'tools: Read, Write, Bash\nmodel: opus\neffort: high\n---\n' in text
    body = text.split('---\n', 2)[2]
    assert 'not built' not in body.lower()
    for given in ('work/visuals/refs/things.json', 'work/visuals/digest/index.json', '`vw visuals trial --file work/visuals/refs/<group>.trials.json`',
                  '`vw visuals look --file work/visuals/refs/<group>.looks.json`', 'work/visuals/trials/<element>/<trial id>.jpg'):
        assert given in body, given
    assert 'by the `rule` in `things.json` and by nothing else' in body                    # the rule is the server's: it travels in things.json
    for own in ('not covered', 'large enough to read', 'still recognised', 'sharp'):       # no sentence of the rule is written here
        assert own not in body, own
    for number in ('8 trial', '3 kept', 'three frames'):                                   # the limits are read from the file
        assert number not in body
    for one_kind in ('site', 'mason', 'brick', 'trade', 'documentary'):                    # generic for every category of film
        assert one_kind not in body.lower(), one_kind
    last = body.strip().splitlines()[-1]
    assert 'never approve' in last and 'found, weak, not found' in last and 'not searched' in last
