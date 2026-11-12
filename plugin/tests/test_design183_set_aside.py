"""design/183: the status line names the clips the server set aside, with the model's reason."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('vw', Path(__file__).resolve().parents[1] / 'scripts' / 'vw.py')
vw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vw)


def test_set_aside_clips_carry_name_and_reason():
    units = [{'unit': 'a1', 'name': 'DJI_0091.mp4', 'status': 'rejected', 'excluded': True,
              'summary': {'excluded': True, 'set_aside': True, 'name': 'DJI_0091.mp4', 'note': 'Set aside by the server: the analysis model refused this clip (HTTP 400): INVALID_ARGUMENT: bad video'}},
             {'unit': 'b2', 'name': 'B.mp4', 'status': 'retained', 'summary': {'sub_clips': 3}},
             {'unit': 'c3', 'name': 'C.mp4', 'status': 'rejected', 'excluded': True, 'summary': {'excluded': True, 'note': 'operator left it out'}},
             {'unit': 'd4', 'status': 'queued', 'summary': None}]
    assert vw.set_aside(units) == [{'unit': 'a1', 'name': 'DJI_0091.mp4', 'reason': 'the analysis model refused this clip (HTTP 400): INVALID_ARGUMENT: bad video'}]
    assert vw.set_aside([]) == []


def test_design186_the_motion_command_takes_a_finish_off_or_on_and_the_skill_and_guide_say_how():
    root = Path(__file__).resolve().parents[1]
    src = (root / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "'finish']" in src and "base + '/motion/finish'" in src and "a.off == a.on" in src
    skill = (root / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'finish.json' in skill and 'data-hf-motion-blur' in skill and 'complete and right without the finish' in skill
    assert 'vw motion finish --shot S --off' in (root / 'commands' / 'vw.md').read_text(encoding='utf-8')
