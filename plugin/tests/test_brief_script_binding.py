"""Brief and script prepare trust the local cleaned script only when it matches the recorded digest (design/34 1.14),
and stamp their times (1.19)."""
import json

import pytest

from conftest import STAGES
from stages_text import Refused, brief_prepare, brief_record, digest, script_prepare, script_record

CLEANED = 'Narration: Earth blocks are made from the soil beneath our feet.\n\nNarration: Each block is pressed, not fired.\n'


def outputs(ws):
    intake = {'summary': {'title': 'Earth Blocks', 'client': 'VK', 'source_digest': digest(CLEANED)}}
    brief = {'summary': {k: 'x' for k in ('purpose', 'audience', 'message', 'tone', 'ending', 'constraints')} | {'content_digest': 'abc'}}
    return lambda stage: {'intake': intake, 'brief': brief}[stage]


def test_matching_script_is_accepted_and_stamped(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED, encoding='utf-8')
    out = brief_prepare(ws, STAGES['brief'], outputs(ws))
    assert out['inputs']['script'] == CLEANED and out['prepared_at'].endswith('Z')
    out = script_prepare(ws, STAGES['script'], outputs(ws))
    assert out['inputs']['script'] == CLEANED and out['prepared_at'].endswith('Z')


def test_edited_script_is_refused(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED.replace('pressed', 'PRESSED'), encoding='utf-8')
    for fn in (brief_prepare, script_prepare):
        with pytest.raises(Refused) as exc:
            fn(ws, STAGES['brief'], outputs(ws))
        assert 'differs from the recorded one' in str(exc.value) and 'vw pull' in str(exc.value)


def test_missing_script_is_refused(ws):
    with pytest.raises(Refused) as exc:
        brief_prepare(ws, STAGES['brief'], outputs(ws))
    assert 'missing' in str(exc.value)


def test_records_carry_prepared_and_recorded_at(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED, encoding='utf-8')
    brief_prepare(ws, STAGES['brief'], outputs(ws))
    (ws / 'out' / 'brief.json').write_text(json.dumps({'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 't', 'ending': 'e',
                                                       'production': {'field_speech_languages': ['ta'], 'narration_language': 'en'}}), encoding='utf-8')
    s = brief_record(ws, STAGES['brief'], outputs(ws))['summary']
    assert s['prepared_at'] and s['recorded_at'] >= s['prepared_at']
    script_prepare(ws, STAGES['script'], outputs(ws))
    (ws / 'out' / 'script.json').write_text(json.dumps({'spoken_text': CLEANED, 'notes': '', 'assessment': '', 'changes': []}), encoding='utf-8')
    s = script_record(ws, STAGES['script'], outputs(ws))['summary']
    assert s['prepared_at'] and s['recorded_at'] >= s['prepared_at'] and s['beats'] == 2
