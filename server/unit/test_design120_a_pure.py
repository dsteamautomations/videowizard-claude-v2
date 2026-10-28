"""design/120 set A: a run is created with its image provider (openai or gemini), required, immutable, read everywhere; old runs are openai."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from app import main as M, visuals_stage as VS

ROOT = Path(__file__).resolve().parents[1]


def test_a_new_run_names_its_image_provider_and_nothing_else_is_accepted():
    assert M.NewRun(request_id='11111111-1111-1111-1111-111111111111', client='Cobuild', image_provider='gemini').image_provider == 'gemini'
    assert M.NewRun(request_id='11111111-1111-1111-1111-111111111111', client='Cobuild', image_provider='openai').image_provider == 'openai'
    with pytest.raises(ValidationError):
        M.NewRun(request_id='11111111-1111-1111-1111-111111111111', client='Cobuild')
    with pytest.raises(ValidationError):
        M.NewRun(request_id='11111111-1111-1111-1111-111111111111', client='Cobuild', image_provider='midjourney')


def test_the_migration_adds_the_column_with_openai_for_old_runs_and_the_two_values_only():
    sql = (ROOT / 'migrations' / '009_image_provider.sql').read_text(encoding='utf-8')
    assert "add column if not exists image_provider text not null default 'openai'" in sql and "check (image_provider in ('openai', 'gemini'))" in sql


def test_provider_of_reads_the_run_and_defaults_to_openai():
    assert VS.provider_of({'image_provider': 'gemini'}) == 'gemini' and VS.provider_of({'image_provider': 'openai'}) == 'openai' and VS.provider_of({}) == 'openai'


def test_create_run_writes_the_provider(monkeypatch):
    seen = {}
    import app.core as core
    monkeypatch.setattr(core, 'resolve_client', lambda c: {'client_name': c, 'client_id': 'c1'})   # the directory is not on this machine
    monkeypatch.setattr(core, 'stage_table', lambda v: {'intake': {}})   # the procedures table is not on this machine either

    class Conn:
        def execute(self, sql, params=()):
            seen['sql'], seen['params'] = sql, params

            class R:
                def fetchone(_):
                    return {'id': 'r', 'code': 'VW-1', 'image_provider': params[-1]}
            return R()
    import app.core as core
    row = core.create_run(Conn(), {'id': 'u', 'name': 'SK'}, 'title', 'Cobuild', None, 'gemini')
    assert 'image_provider' in seen['sql'] and seen['params'][-1] == 'gemini' and row['image_provider'] == 'gemini'
