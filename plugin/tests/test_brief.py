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
    assert 'from run VW-3:' in p and 'field_speech_languages: ta' in p
    assert 'process_stages' not in p.split('from run VW-3:')[1].split('\n\n')[0] and 'Plinth' not in p   # design/56 L10: chapters are this film's, never a recommendation
    assert 'answer to brand-safety (Any brand or safety rules?): NO Brand and safety rules' in p and 'answer to field-languages: Tamil' in p
    assert '- Rejected option #4: no close-ups of unfinished walls (from VW-3)' in p
    assert out['inputs']['last_brief'] == LAST and out['inputs']['client_rules'] == RULES
    assert '{last_brief}' not in p and '{client_rules}' not in p


def test_first_film_shows_none(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED, encoding='utf-8')
    p = brief_prepare(ws, PROC, prior_of())['prompt']
    assert p.count('\nnone\n') == 3 and '{last_brief}' not in p   # last brief, rules, document timing (design/53 L2)


def test_steps_carry_chapters_production_block_and_the_web_rule():
    steps = ' '.join(PROC['steps'])
    assert 'chapters of the film' in steps and 'production block' in steps and 'I am deviating from the usual procedure' in steps
    assert 'never taken from a previous brief' in steps and 'not an identifier' in steps   # design/56 L10
    assert 'on every film' in steps and 'same as last time' in steps


def test_languages_are_required_on_every_film():
    for prod in ({}, {'field_speech_languages': ['ta']}, {'narration_language': 'en'}):
        with pytest.raises(Refused) as exc:
            production_inputs(prod)
        assert 'every film' in str(exc.value)
    with pytest.raises(Refused):
        production_inputs({'field_speech_languages': 'ta', 'narration_language': 'en'})
    assert production_inputs({'field_speech_languages': [], 'narration_language': 'en'})['field_speech_languages'] == []   # design/125 B1: nobody speaks
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


@pytest.mark.parametrize('names', [['Chapter_1_The_Need_For_Better_Building', 'Mixing the mortar'], ['Stage 2 Mixing'], ['Scene1: the site'], ['Part 4'],
                                   ['3. Curing'], ['3) Curing'], ['Curing', 'curing'], ['---'], ['Mixing_the_mortar']])
def test_chapter_identifiers_numbering_and_duplicates_are_refused(names):
    """design/56 L10: a chapter is the plain name of what the footage shows; the list is numbered when presented."""
    with pytest.raises(Refused) as exc:
        production_inputs({'field_speech_languages': ['ta'], 'narration_language': 'en', 'process_stages': names})
    assert 'plain names' in str(exc.value) and 'no numbering' in str(exc.value)


def test_plain_chapter_names_are_accepted():
    names = ['Mixing the mortar', 'Pointing the joints', 'Sill course at the window', 'Curing for 7 days', 'Chapter house visit']
    out = production_inputs({'field_speech_languages': ['ta'], 'narration_language': 'en', 'process_stages': names})
    assert out['process_stages'] == names


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


# ---------- design/53 L2, L3, L4, L7 ----------

def test_prompt_shows_the_document_timing_and_says_what_chapters_are(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED, encoding='utf-8')
    intake = {'summary': {'title': 'Earth Blocks', 'client': 'VK', 'source_digest': digest(CLEANED), 'timing_lines': ['Suggested Duration: 5–6 Minutes', 'Duration: 30 seconds']}}
    out = brief_prepare(ws, PROC, lambda s: {'intake': intake}[s])
    assert 'Suggested Duration: 5–6 Minutes' in out['prompt'] and out['inputs']['document_timing'] == intake['summary']['timing_lines']
    assert 'what the footage will show' in out['prompt'] and 'never an argument of the script' in out['prompt']
    assert 'Do not recreate ten mandatory fields' not in out['prompt'] and 'Do not add coverage, feasibility' not in out['prompt']
    assert 'frame shape' in out['prompt'] and 'watched muted' in out['prompt']
    out = brief_prepare(ws, PROC, prior_of())
    assert 'DOCUMENT' in out['prompt'] and 'none' in out['prompt'] and out['inputs']['document_timing'] == []
    assert 'chapters are what the footage' in ' '.join(PROC['steps']).lower() or 'what the footage will show' in ' '.join(PROC['steps'])
    assert 'frame shape' in ' '.join(PROC['steps'])


def test_format_is_validated_and_defaulted():
    out = production_inputs({'field_speech_languages': ['ta'], 'narration_language': 'en'})
    assert out['format'] == {'frame': '16:9', 'destinations': [], 'watched_muted': False} and 'format' in out['defaults_applied']
    out = production_inputs({'field_speech_languages': ['ta'], 'narration_language': 'en', 'format': {'frame': '9:16', 'destinations': ['Instagram', 'TikTok'], 'watched_muted': True}})
    assert out['format'] == {'frame': '9:16', 'destinations': ['Instagram', 'TikTok'], 'watched_muted': True} and 'format' not in out['defaults_applied']
    for bad in ({'frame': '21:9'}, {'frame': '16:9', 'destinations': 'YouTube'}, {'frame': '16:9', 'watched_muted': 'yes'}, 'vertical'):
        with pytest.raises(Refused):
            production_inputs({'field_speech_languages': ['ta'], 'narration_language': 'en', 'format': bad})
