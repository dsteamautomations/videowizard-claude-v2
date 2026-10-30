"""Defect 34 (VW-12, 30 Oct 2026): `vw next` said "paid: openai-images,video" at the visuals step of a run started with --images gemini.
The pictures follow the run's choice (visuals_stage.provider_of); the paid line was the procedure's fixed text. It now names the run's picture AI."""
import json
from pathlib import Path

from app import core

STAGES = [s for s in json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals']


def run(provider):
    return {'id': 'r', 'code': 'VW-12', 'procedure_version': '3', 'active_machine': None, 'status': 'active', **({'image_provider': provider} if provider else {})}


def test_the_paid_line_names_the_runs_picture_ai():
    assert core.compute_next(run('gemini'), STAGES, [], {})['paid'] == 'gemini-images,video'
    assert core.compute_next(run('openai'), STAGES, [], {})['paid'] == 'openai-images,video'
    assert core.compute_next(run(None), STAGES, [], {})['paid'] == 'openai-images,video'   # runs from before the choice are openai


def test_other_stages_keep_their_line():
    stage = {**STAGES[0], 'name': 'voice', 'paid': 'elevenlabs'}
    assert core.compute_next(run('gemini'), [stage], [], {})['paid'] == 'elevenlabs'
