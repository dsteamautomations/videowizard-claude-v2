"""design/139 R9 (SK, 2 Nov 2026, design/138 C6): an AI video needs 3 s to generate, so it is made at 3 s and cut to at least 2 s on screen; under 2 s it is
one picture. A blank has no minimum (a 1-2 s drawing or picture is fine). The longest take stays Omni's 10 s. The long-blank, long-AI-run and long-real-shot
warnings are gone."""
from fractions import Fraction

import pytest

from app import visual_contract as VC, visuals_stage as VS
from app.stage2 import validator as V
from test_design103_pure import doc_
from test_visuals_pure import GAPS, shot as pshot


def tail(a):   # camera shots to the gap's end, each within a take's 10 s
    cuts = list(range(a, 1000, 200)) + [1000]
    return [pshot(f'VS{n}', x, y, 'video') for n, (x, y) in enumerate(zip(cuts, cuts[1:]), 1)]


def test_the_removed_length_rules_are_gone():
    for name in ('MIN_BLANK_S', 'LONG_BLANK_S', 'LONG_REAL_S', 'long_blank_flag'):
        assert not hasattr(V, name), name
    assert not hasattr(VC, 'AI_RUN_S') and 'ai_run' not in VC.WARNING_PLAIN


def test_an_ai_video_under_two_seconds_is_refused():
    with pytest.raises(ValueError, match='use a single picture'):
        VC.validate_plan(doc_(pshot('V0', 0, 47, 'video'), *tail(47)), GAPS, Fraction(25))


def test_an_ai_video_of_two_seconds_passes_and_is_made_at_three():
    VC.validate_plan(doc_(pshot('V0', 0, 50, 'video'), *tail(50)), GAPS, Fraction(25))
    assert VC.take_seconds(2.0) == 3


def test_a_one_second_still_passes():
    VC.validate_plan(doc_(pshot('S0', 0, 25, 'image'), *tail(25)), GAPS, Fraction(25))


def test_long_ai_runs_are_not_warned():
    _, warnings = VC.validate_plan(doc_(*tail(0)), GAPS, Fraction(25))
    assert 'ai_run' not in [w['kind'] for w in warnings]
    entry = {'gap_id': 'G1', 'shots': [{'id': f'V{i}', 'route': 'video', 'seconds': 9.0} for i in range(3)]}
    assert 'ai_run' not in [w['kind'] for w in VS.treatment_length_warnings(entry)]
