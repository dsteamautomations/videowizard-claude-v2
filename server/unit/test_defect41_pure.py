"""Defect 41 (VW-12, 31 Oct 2026): a visual plan of about 280 KB was refused by the 256 KB database guard (413) at check and propose,
though the plan is saved to storage. The plan's routes have their own limit (4 MB); every other write keeps 256 KB."""
import pytest

from app import main
from app.config import Settings
from app.errors import Problem


class Req:
    def __init__(self, n):
        self.headers = {'content-length': str(n)}


def test_a_300_kb_plan_passes_and_the_database_guard_is_unchanged():
    main.plan_size_guard(Req(300 * 1024))
    with pytest.raises(Problem):
        main.plan_size_guard(Req(5 * 1024 * 1024))
    with pytest.raises(Problem):
        main.size_guard(Req(300 * 1024))
    assert Settings.model_fields['MAX_BODY_BYTES'].default == 256 * 1024


def test_check_and_propose_use_the_plans_limit():
    src = open(main.__file__, encoding='utf-8').read()
    for route in ('check', 'propose'):
        assert f"@app.post('/api/runs/{{run_id}}/visuals/{route}', dependencies=[Depends(plan_size_guard)])" in src
