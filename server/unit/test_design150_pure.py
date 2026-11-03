"""design/150 Set C: the treatment part of instruction version 3 states what the server enforces (the Direction's 2000 characters, `seconds` one number per gap)
and the one-clip rule; the helper brief says an icon has no sizes (the B10 correction)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V3 = {s['name']: s for s in json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']}
TREATMENT = next(p for p in V3['visuals']['parts'] if p['name'] == 'treatment')['text']
BRIEF = (ROOT.parent / 'plugin' / 'agents' / 'vw-plan-gaps.md').read_text(encoding='utf-8')


def test_the_treatment_text_states_the_two_limits_the_server_enforces():
    assert 'a few lines (at most 2000 characters)' in TREATMENT   # C1: visuals_stage refuses over 2000
    assert "`seconds`, one number, the gap's total" in TREATMENT and 'never a list in `seconds`' in TREATMENT   # C2: visuals_stage refuses a list
    assert "a video gap's segments with theirs);" not in TREATMENT   # the sentence that read as seconds per segment is gone


def test_the_treatment_text_names_a_footage_thing_at_one_gap_only():
    assert 'is named at one gap only; a second gap that wants it says why in its line, or takes another' in TREATMENT   # C3


def test_the_brief_says_an_icon_has_no_sizes():
    assert 'An icon or an idea graphic' in BRIEF and 'no sizes and no drawing_spec' in BRIEF
