"""Server unit tests that need no database, no Docker and no live provider (design/40 §D). Run on any machine with the venv:
`.venv/bin/python -m pytest server/unit`. The database-backed tests stay in server/tests."""
import os
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
os.environ.setdefault('VW2_DATABASE_URL', '')   # settings load without a database


import pytest   # noqa: E402

# design/124 A4 decision 5: the plan check now refuses a video shot longer than Omni's 10 s. The plans these modules build were written before that,
# with 12-30 s video shots, and test other rules; for them only, Omni's maximum is lifted. Every other module (test_design124_a3a4_pure among them) runs the real limit.
LONG_SHOT_FIXTURES = {'test_visuals_pure', 'test_visuals_stage_pure', 'test_batch89_pure', 'test_batch89b_pure', 'test_design103_pure',
                      'test_design91_b2_pure', 'test_design106d_pure', 'test_defect35_pure', 'test_design101_pure', 'test_design110_f456_pure',
                      'test_design111_f14f15_pure', 'test_design111_f19_pure', 'test_design111_f7f8f9_pure', 'test_design112_k_pure', 'test_design117_p2_pure',
                      'test_design119_e_pure', 'test_design91_b3_pure', 'test_design91_b4_pure', 'test_review_c_pure', 'test_design110_f1f2_pure',
                      'test_design111_f10_pure', 'test_design111_f16_pure', 'test_design111_f17_pure', 'test_design111_f18_pure', 'test_design113_e6_pure',
                      'test_design94_r1_pure', 'test_design95_pure'}


@pytest.fixture(autouse=True)
def _long_shot_fixtures(request, monkeypatch):
    if request.module.__name__ in LONG_SHOT_FIXTURES:
        from app import visual_contract as VC
        real = VC._default_generator
        monkeypatch.setattr(VC, '_default_generator', lambda: {**real(), 'max_seconds': 60})
