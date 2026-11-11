"""Handover (SK, 11 Nov 2026): `vw pull` says where the run stands and whether DaVinci Resolve is on this computer (H2, H3, H-E5);
`vw next` prints the server's one next thing; the lines of a repeated bundle, prepare, build and render say nothing was made again (H4); the text (H7)."""
import argparse
import json

import pytest

from conftest import PLUGIN
import vw

HANDOVER = '`vw delivery check`, `vw delivery download`, then `vw delivery open`'
PROOF = 'the proof film (version 1) is ready to watch and listen: `vw assembly fetch`, then on the operator\'s yes `vw assembly record --quote`; nothing is made again'
STALE = "G1 was recorded again after the editor's package; run `vw delivery bundle` again, then the assembly."
FIRST = "The editor's package comes first: run `vw delivery bundle`, then the assembly."
STUDIO = {'found': True, 'version': '20.1', 'edition': 'studio'}
FREE = {'found': True, 'version': '20.1', 'edition': 'free'}
NONE = {'found': False, 'version': None, 'edition': None}


def nxt(do_next=PROOF, handover=HANDOVER, state='current', stage='assembly'):
    return {'stage': stage, 'active_machine': 'this-pc', 'stage3': {'package': {'state': state}, 'do_next': do_next, 'handover': handover}}


@pytest.fixture
def pulled(monkeypatch, tmp_path, capsys):
    """`vw pull VW-19` against a fake server; returns run(next answer, what find_resolve says) -> (exit code, JSON, line, calls)."""
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(vw, 'machine_id', lambda: 'this-pc')

    def run(answer, found):
        calls = []
        full = {'id': 'run-1', 'code': 'VW-19', 'procedure_version': '3', 'outputs': [], 'next': {'stage': answer['stage'], 'active_machine': 'this-pc'}}

        def call(method, path, wait=None, **kw):
            calls.append((method, path))
            return [full] if path == '/api/runs' else answer if path.endswith('/next') else full
        monkeypatch.setattr(vw, 'call', call)
        monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: calls.append(('POST', path)) or {})
        monkeypatch.setattr(vw.handoff, 'find_resolve', lambda: found)
        with pytest.raises(SystemExit) as exc:
            vw.cmd_pull(argparse.Namespace(code='VW-19', take_over=False))
        out, err = capsys.readouterr()
        return exc.value.code, json.loads(out), err.strip(), calls
    return run


def test_pull_with_resolve_and_a_current_package_offers_the_hand_over_first(pulled):
    code, out, line, calls = pulled(nxt(), STUDIO)
    assert code == 0 and line.startswith('Pulled VW-19.') and 'DaVinci Resolve Studio is on this computer' in line
    assert 'Next, the hand-over: ' + HANDOVER in line and line.index('`vw delivery check`') < line.index('`vw assembly fetch`')
    assert 'prepare' not in line and 'bundle' not in line
    assert out['resolve'] == STUDIO and out['next']['stage3']['handover'] == HANDOVER and out['workspace']
    assert ('GET', '/api/runs/run-1/next') in calls and not [c for c in calls if c[0] == 'POST']   # the run is this computer's already: nothing is written


def test_pull_with_free_resolve_names_the_edition(pulled):
    assert 'DaVinci Resolve (free) is on this computer' in pulled(nxt(), FREE)[2]


def test_he5_pull_without_resolve_says_so_and_names_what_can_be_done_here(pulled):
    code, out, line, _ = pulled(nxt(), NONE)
    assert code == 0 and 'DaVinci Resolve is not on this computer' in line
    assert 'What can be done here: ' + PROOF in line and 'Waiting for a computer with DaVinci: ' + HANDOVER in line
    assert line.index('`vw assembly fetch`') < line.index('`vw delivery check`')


def test_pull_without_resolve_at_delivery_only_the_hand_over_is_left(pulled):
    line = pulled(nxt(do_next=HANDOVER, stage='delivery'), NONE)[2]
    assert 'Nothing in this stage can be done here' in line and 'Waiting for a computer with DaVinci: ' + HANDOVER in line


@pytest.mark.parametrize('found', [STUDIO, NONE])
def test_pull_with_a_stale_package_says_why_and_offers_no_hand_over(pulled, found):
    line = pulled(nxt(do_next=STALE, handover=None, state='stale'), found)[2]
    assert STALE in line and 'hand-over' not in line and '`vw delivery check`' not in line and 'this computer' in line


@pytest.mark.parametrize('found', [STUDIO, NONE])
def test_pull_with_no_package_names_the_bundle(pulled, found):
    line = pulled(nxt(do_next=FIRST, handover=None, state='none'), found)[2]
    assert '`vw delivery bundle`' in line and 'hand-over' not in line


def test_pull_before_stage_three_and_from_an_older_server_still_names_the_stage(pulled):
    line = pulled({'stage': 'visuals', 'active_machine': 'this-pc'}, STUDIO)[2]
    assert line.startswith('Pulled VW-19. Next: visuals.')
    assert 'Next: assembly.' in pulled({'stage': 'assembly', 'active_machine': 'this-pc', 'stage3': None}, NONE)[2]


def test_pull_of_a_run_active_elsewhere_still_asks_for_the_take_over(pulled, monkeypatch):
    monkeypatch.setattr(vw, 'machine_id', lambda: 'other-pc')
    code, out, line, calls = pulled(nxt(), STUDIO)
    assert code == 2 and out['action'] == 'take_over'


def test_next_line_prints_the_one_next_thing_and_the_hand_over():
    line = vw.next_line(nxt())
    assert line.startswith('Next: assembly.') and PROOF in line and 'On a computer with DaVinci Resolve: ' + HANDOVER in line
    assert vw.next_line(nxt(do_next=HANDOVER, stage='delivery')).count('`vw delivery check`') == 1
    assert vw.next_line({'stage': 'assembly', 'stage3': None}) == 'Next: assembly.'


# ---------- H4: what the tool prints when the server made nothing again ----------

def args(**kw):
    base = {'what': 'status', 'shot': None, 'offset': None, 'end': None, 'sub': None, 'choice': None, 'decision': None, 'notes': None, 'quote': None,
            'accept_as_is': False, 'frame_note': None, 'file': None, 'wait': 0}
    return argparse.Namespace(**{**base, **kw})


@pytest.fixture
def tool(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-19', 'run_id': 'run-1', 'files': []})
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, **kw: rel)

    def run(cmd, what, answer):
        monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: answer)
        with pytest.raises(SystemExit) as exc:
            cmd(args(what=what))
        return exc.value.code, capsys.readouterr().err.strip()
    return run


def test_the_line_of_a_settled_prepare_asks_nothing(tool):
    fills = {'VS1': {'slot_frames': 100, 'available_frames': None, 'default': {'end_policy': 'hold_last'}, 'issues': []}}
    code, line = tool(vw.cmd_assembly, 'prepare', {'fills': fills, 'settled': True, 'next': 'the fills are settled and the film is built from them: nothing to put to the operator again. ' + PROOF})
    assert code == 0 and 'VS1: slot 100 f' in line and 'ask' not in line and 'the fills are settled' in line and '`vw assembly fetch`' in line
    code, line = tool(vw.cmd_assembly, 'prepare', {'fills': fills, 'next': 'ask the operator per fill'})
    assert line.endswith('Show this table and ask once; the defaults need no command.')


def test_the_line_of_an_unchanged_build_and_of_a_ready_render(tool):
    code, line = tool(vw.cmd_assembly, 'build', {'version': 1, 'unchanged': True, 'next': PROOF})
    assert code == 0 and line == 'Nothing changed since version 1: the built film and its render are kept. ' + PROOF
    assert tool(vw.cmd_assembly, 'build', {'version': 2, 'unchanged': False, 'next': 'x'})[1] == 'ok'
    code, line = tool(vw.cmd_assembly, 'render', {'job_id': 'j', 'ready': True, 'next': 'the film of this build is already rendered; nothing was queued: `vw assembly fetch`'})
    assert code == 0 and 'rendering' not in line and 'already rendered' in line
    assert tool(vw.cmd_assembly, 'render', {'job_id': 'j'})[1] == 'Assembly film rendering; wait with `vw assembly status --wait 900`.'


def test_the_line_of_a_current_bundle(tool):
    answer = {'manifest': {'key': 'k'}, 'files': 12, 'bytes': 3e6, 'early': True, 'current': True, 'next': "the editor's package is current; nothing was built again. " + PROOF}
    code, line = tool(vw.cmd_delivery, 'bundle', answer)
    assert code == 0 and line.startswith("The editor's package is current (12 files, 3 MB); nothing was built again.") and 'vw pull' not in line


# ---------- H7: the instruction text ----------

def test_the_instruction_says_to_read_where_the_stage_stands_and_do_only_what_is_left():
    paras = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8').split('\n')
    nxt_p = next(p for p in paras if p.startswith('**The next stage.**'))
    asm_p = next(p for p in paras if p.startswith('**Assembly and delivery**'))
    for p in (nxt_p, asm_p):
        assert '`vw next`' in p and 'only what is left' in p and 'from the top' in p
