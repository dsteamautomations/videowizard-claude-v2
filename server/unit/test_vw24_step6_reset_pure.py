"""scripts/vw24_step6_reset.py (SK, 19 Nov 2026): VW-24 set back to the start of step 6. Its --check mode on a synthetic session file: what is
cleared, what is kept, the dry run writes nothing, --apply saves the session beside it first, --undo puts the same bytes back. Without a database."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import vw24_step6_reset as R   # noqa: E402

SESSION = {
    'versions': [{'version': 3, 'plan_digest': 'd3'}], 'current': 'd3', 'accepted': {'G1': {'digest': 'x'}}, 'spec_approvals': {'MO1': {'digest': 's'}},
    'references': {'k1': {'kind': 'keyframe', 'status': 'approved'}, 'sh1': {'kind': 'sheet', 'status': 'approved'}},
    'round': {'v': 2, 'pass': 'complete'}, 'golden': {'E1': 'sh1'}, 'treatment': {'digest': 't'}, 'font': {'name': 'NotoSans.ttf', 'key': 'f'},
    'motion_projects': {'a' * 64: {'shot_id': 'MO1', 'key': 'p.zip'}}, 'motion_checks': {'MO1': [{'round': 1}]}, 'motion_bound': {'MO1': 'a' * 64},
    'motion_stills': {'MO1': {'png': 'p'}}, 'motion_parts': {'sha256': 'p'}, 'motion_parts_approved': {'sha256': 'p'}, 'motion_held': {'MO1': {'answer': 'select'}},
    'motion_more': {'MO1': True}, 'motion_finish_off': {'MO2': {}}, 'drawings_shown': {'MO1': 'job-7'}, 'drawing_notes': [{'text': 'n', 'shots': ['MO1']}],
    'added_colours': {'c1': {'shots': ['MO1']}},
    'preparations': {'MO1': {'preparation_id': 'r1', 'drawn': True}, 'VS1': {'preparation_id': 'v1'}},
    'selections': {'MO1': {'job_id': 'job-7'}, 'VS1': {'job_id': 'job-2'}}, 'reviews': {'job-7': [{'decision': 'accepted'}], 'job-2': [{'decision': 'accepted'}]},
    'take_checks': {'job-7': {}}, 'chat_item': {'id': 'held:MO1:aaaa:3'},
}


def test_set_back_clears_every_drawn_trace_and_keeps_the_plan_specs_references_and_treatment():
    s = json.loads(json.dumps(SESSION))
    out = R.set_back(s, {'job-9': 'MO2'})
    assert not set(R.CLEARED) & set(s) and 'chat_item' not in s
    assert s['preparations'] == {'VS1': {'preparation_id': 'v1'}} and s['selections'] == {'VS1': {'job_id': 'job-2'}}
    assert s['reviews'] == {'job-2': [{'decision': 'accepted'}]} and s['take_checks'] == {}
    assert out['drawn_takes'] == {'selections': ['MO1'], 'reviews': ['job-7'], 'take_checks': ['job-7']}
    for k in R.KEPT:
        assert s[k] == SESSION[k], k
    assert set(out['kept']) == set(R.KEPT) and set(out['cleared']) == set(R.CLEARED) | {'preparations', 'chat_item'}


def test_every_motion_key_the_server_writes_is_cleared():
    import re
    keys = set()
    for p in (ROOT / 'server' / 'app').glob('*.py'):
        keys |= set(re.findall(r"session(?:\.get\(|\.setdefault\(|\[|\.pop\()'(motion_[a-z_]+)'", p.read_text(encoding='utf-8')))
    assert keys and keys <= set(R.CLEARED), keys - set(R.CLEARED)


def test_check_mode_dry_run_writes_nothing_apply_backs_up_first_and_undo_restores_the_same_bytes(tmp_path, capsys):
    f = tmp_path / 'session.json'
    raw = json.dumps(SESSION, indent=1).encode('utf-8')
    f.write_bytes(raw)
    R.main(['--check', str(f)])
    assert f.read_bytes() == raw and [p.name for p in tmp_path.iterdir()] == ['session.json'] and 'Dry run: nothing changed' in capsys.readouterr().out
    backup = R.main(['--check', str(f), '--apply'])
    printed = capsys.readouterr().out
    assert (tmp_path / backup).read_bytes() == raw and f'Backup of the whole session: {backup}' in printed and 'Log line (not written: no database)' in printed
    after = json.loads(f.read_bytes())
    assert 'motion_projects' not in after and after['spec_approvals'] == SESSION['spec_approvals']
    R.main(['--check', str(f), '--undo', str(tmp_path / backup)])
    assert f.read_bytes() == raw
    with pytest.raises(SystemExit, match='is no step-6 backup'):
        R.main(['--check', str(f), '--undo', str(tmp_path / 'other.json')])


def test_no_write_when_the_backup_does_not_read_back(tmp_path):
    f = tmp_path / 'session.json'
    raw = json.dumps(SESSION).encode('utf-8')
    f.write_bytes(raw)
    from app.storage import LocalStorage

    class Broken(LocalStorage):
        def get(self, key):
            return b'' if '.backup-step6-' in key else super().get(key)
    with pytest.raises(SystemExit, match='did not read back the same; nothing changed'):
        R.reset(Broken(tmp_path), 'session.json', None, True, print)
    assert f.read_bytes() == raw
