"""Brief prepare and record as pure file functions (design/37 2.1, 2.2, 2.3, 2.5, 2.8)."""
import json

import pytest

from conftest import STAGES
from stages_text import Refused, brief_prepare, brief_record, digest, production_inputs

CLEANED = 'Narration: Earth blocks are made from the soil beneath our feet.\n\nNarration: Each block is pressed, not fired.\n'
PROC = STAGES['brief']
LAST = {'run': 'VW-3', 'production': {'process_stages': ['Plinth', 'Curing'], 'field_speech_languages': ['ta'], 'narration_language': 'en',
                                      'show_speaker_video': False, 'brand_and_safety_rules': [], 'target_runtime_s': None},
        'answers': {'brand-safety': 'NO Brand and safety rules', 'field-languages': 'Tamil'},
        'questions': [{'id': 'brand-safety', 'question': 'Any brand or safety rules?'}]}
RULES = [{'rule': 'Rejected option #4: no close-ups of unfinished walls', 'source_run': 'VW-3', 'at': '2026-10-17'}]


def prior_of():
    intake = {'summary': {'title': 'Earth Blocks', 'client': 'VK', 'source_digest': digest(CLEANED)}}
    return lambda stage: {'intake': intake}[stage]


def base(**over):
    return {'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 't', 'ending': 'e', 'constraints': '', 'questions': [], 'answers': {},
            'production': {'field_speech_languages': ['ta'], 'narration_language': 'en', **over.pop('production', {})}, **over}


def test_prompt_is_clean_of_v1_machinery_and_carries_the_client_memory(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED, encoding='utf-8')
    out = brief_prepare(ws, PROC, prior_of(), last_brief=LAST, client_rules=RULES)
    p = out['prompt']
    for stale in ('save_brief', 'accept_brief', 'employee', 'connector', 'backend', 'browser', 'legacy', 'research a client from its name'):
        assert stale not in p, stale
    assert p.startswith('VW-PROCEDURE') and 'PRODUCTION VALUES' in p and 'propose a web search' in p
    assert 'from run VW-3:' in p and 'field_speech_languages: ta' in p and 'process_stages: Plinth, Curing' in p
    assert 'answer to brand-safety (Any brand or safety rules?): NO Brand and safety rules' in p and 'answer to field-languages: Tamil' in p
    assert '- Rejected option #4: no close-ups of unfinished walls (from VW-3)' in p
    assert out['inputs']['last_brief'] == LAST and out['inputs']['client_rules'] == RULES
    assert '{last_brief}' not in p and '{client_rules}' not in p


def test_first_film_shows_none(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED, encoding='utf-8')
    p = brief_prepare(ws, PROC, prior_of())['prompt']
    assert p.count('\nnone\n') == 2 and '{last_brief}' not in p


def test_steps_carry_chapters_production_block_and_the_web_rule():
    steps = ' '.join(PROC['steps'])
    assert 'chapters of the film' in steps and 'production block' in steps and 'I am deviating from the usual procedure' in steps
    assert 'on every film' in steps and 'same as last time' in steps


def test_languages_are_required_on_every_film():
    for prod in ({}, {'field_speech_languages': ['ta']}, {'narration_language': 'en'}, {'field_speech_languages': [], 'narration_language': 'en'}):
        with pytest.raises(Refused) as exc:
            production_inputs(prod)
        assert 'every film' in str(exc.value)
    with pytest.raises(Refused):
        production_inputs({'field_speech_languages': 'ta', 'narration_language': 'en'})
    out = production_inputs({'field_speech_languages': ['ta', 'en'], 'narration_language': 'en'})
    assert out['field_speech_languages'] == ['ta', 'en'] and out['narration_language'] == 'en'
    assert 'field_speech_languages' not in out['defaults_applied'] and 'narration_language' not in out['defaults_applied']


def test_chapters_default_empty_generic_refused_script_names_accepted():
    out = production_inputs({'field_speech_languages': ['ta'], 'narration_language': 'en'})
    assert out['process_stages'] == [] and 'process_stages' in out['defaults_applied']
    with pytest.raises(Refused) as exc:
        production_inputs({'field_speech_languages': ['ta'], 'narration_language': 'en',
                           'process_stages': ['Stage_1_Setup', 'Stage_2_Preparation', 'Stage_3_Execution', 'Stage_4_Result']})
    assert 'chapters' in str(exc.value)
    out = production_inputs({'field_speech_languages': ['ta'], 'narration_language': 'en', 'process_stages': ['Plinth', 'Curing']})
    assert out['process_stages'] == ['Plinth', 'Curing'] and 'process_stages' not in out['defaults_applied']


def test_record_refuses_without_languages_and_records_with_them(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED, encoding='utf-8')
    brief_prepare(ws, PROC, prior_of())
    data = base()
    del data['production']['narration_language']
    (ws / 'out' / 'brief.json').write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(Refused) as exc:
        brief_record(ws, PROC, prior_of())
    assert 'narration_language' in str(exc.value)
    (ws / 'out' / 'brief.json').write_text(json.dumps(base(production={'process_stages': ['Plinth']})), encoding='utf-8')
    s = brief_record(ws, PROC, prior_of())['summary']
    assert s['production']['process_stages'] == ['Plinth'] and s['production']['field_speech_languages'] == ['ta'] and s['prepared_at']
