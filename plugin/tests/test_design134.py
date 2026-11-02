"""design/134: SK's decisions on the Codex process review (2 Nov 2026), the plugin side. Findings 4, 5, 11, 13, 14, 17."""
import argparse
import json

import pytest

from conftest import PLUGIN
from test_design125_stage7 import opt, options_doc, read_rows, run, ws  # noqa: F401  (ws is a fixture)
from test_design130 import margs, mrun, project
from test_visuals_cli import harness  # noqa: F401  (the fixture rides along)
import vw

AGENTS = PLUGIN / 'agents'


def test_4_the_second_look_keeps_b_roll_the_options_allow():
    text = (AGENTS / 'vw-scene-review.md').read_text(encoding='utf-8')
    assert 'Direct matches show the same action, object and method. B-roll may illustrate ideas without specific claims; it must not contradict the narration.' in text
    assert 'related is not enough' not in text


def test_11_the_helper_knows_the_clip_parts_other_scenes_use_and_the_reuse_rule():
    text = (AGENTS / 'vw-scene-review.md').read_text(encoding='utf-8')
    assert '`used_elsewhere`' in text and 'kind reuse' in text and 'never the same part' in text


def test_11_each_scene_file_lists_the_parts_other_scenes_use(ws, monkeypatch, capsys):  # noqa: F811
    monkeypatch.setattr(vw, 'request', lambda method, path, **kw: ({'frames': []}, 0))
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: rel)
    code, out, err = run(vw.cmd_options, opt(what='second-look'), capsys)
    one = read_rows(ws / 'work' / 'options' / 'scenes' / 'BEAT_01.json')
    two = read_rows(ws / 'work' / 'options' / 'scenes' / 'BEAT_02.json')
    mine = {e['sub_clip_id'] for o in options_doc()['options'] if o['beat_id'] == 'BEAT_02' for e in o['events'] if e.get('sub_clip_id')}
    assert code == 0 and {u['sub_clip_id'] for u in one['used_elsewhere']} == mine and all(u['scene'] == 'BEAT_02' for u in one['used_elsewhere'])
    assert all(u['scene'] != 'BEAT_02' for u in two['used_elsewhere'])


def test_13_the_checker_may_read_the_upload_file():
    text = (AGENTS / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert 'Also read last-upload.json; never read the project\'s HTML or REVIEW.md.' in text and 'or anything else' not in text


def test_14_the_brief_reply_starts_the_rules_helper_first(harness, monkeypatch, capsys):  # noqa: F811
    hws, _ = harness
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'brief': '# Brief\n', 'refs': []})
    code, out, err = mrun(margs(what='brief', shot='MO1'), capsys)
    assert code == 0 and 'start vw-motion-rules for MO1, then vw-motion-shot.' in err


def test_5_a_new_upload_clears_the_old_snapshots_and_the_same_upload_keeps_them(harness, monkeypatch, capsys):  # noqa: F811
    hws, _ = harness
    sha = {'v': 'a' * 64}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'sha256': sha['v'], 'next': 'stored'})
    project(hws)
    snaps = hws / 'work' / 'motion' / 'MO1' / 'snapshots'
    mrun(margs(what='upload', shot='MO1'), capsys)
    snaps.mkdir(parents=True, exist_ok=True)
    (snaps / 'at-1s.png').write_bytes(b'old')
    mrun(margs(what='upload', shot='MO1'), capsys)   # the same project again: the snapshots stay
    assert (snaps / 'at-1s.png').exists()
    sha['v'] = 'b' * 64
    mrun(margs(what='upload', shot='MO1'), capsys)   # a corrected project: the old snapshots go
    assert not (snaps / 'at-1s.png').exists()


def test_17_the_old_rebuild_is_refused_by_name(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(vw, 'call', lambda *a, **k: {'bundle': {'manifest': {'key': 'k'}}, 'resolve': None})   # never the network
    monkeypatch.setattr(vw, 'write', lambda *a, **k: pytest.fail('the old rebuild reserved the ledger'))
    a = argparse.Namespace(what='resolve', check=False, run_it=True, inspect=False, close=False, authorization='yes', note=None, quote=None, originals=None, camera=False)
    with pytest.raises(SystemExit) as exc:
        vw.cmd_delivery(a)
    out = json.loads(capsys.readouterr().out)
    assert exc.value.code == 2 and 'retired' in out['message'] and '`vw delivery download`' in out['message'] and '`vw delivery open`' in out['message']
