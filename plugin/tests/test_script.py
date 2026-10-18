"""Script prepare and record as pure file functions (design/38 3.1–3.5)."""
import json

import pytest

from conftest import STAGES
from stages_text import Refused, apply_changes, digest, first_difference, script_prepare, script_record

SOURCE = 'Narration: Earth blocks are made from the soil beneath our feet.\n\nNarration: Each block is pressed, not fired, so it keeps the carbon in the ground.\n'
PROC = STAGES['script']


def prior_of():
    intake = {'summary': {'title': 'Earth Blocks', 'client': 'VK', 'source_digest': digest(SOURCE)}}
    brief = {'summary': {'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 't', 'ending': 'e', 'constraints': 'no competitor names',
                         'answers': {'brand-safety': 'never name the competitor'}, 'content_digest': 'abc',
                         'production': {'narration_language': 'ta', 'brand_and_safety_rules': ['no competitor names'], 'process_stages': ['Plinth', 'Curing'],
                                        'field_speech_languages': ['ta']}}}
    return lambda stage: {'intake': intake, 'brief': brief}[stage]


def proposal(ws, text, changes=(), **over):
    (ws / 'out' / 'script.json').write_text(json.dumps({'spoken_text': text, 'notes': '', 'assessment': 'fits', 'changes': list(changes), **over}), encoding='utf-8')


def record(ws):
    return script_record(ws, PROC, prior_of())


def ch(before, after, decision='accepted', **extra):
    return {'before': before, 'after': after, 'reason': 'r', 'decision': decision, **extra}


@pytest.fixture
def src(ws):
    (ws / 'out' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    script_prepare(ws, PROC, prior_of())
    return ws


# ---------- apply_changes and first_difference ----------

def test_zero_changes_must_equal_the_source():
    rebuilt, expected = apply_changes(SOURCE, [], 'Narration:   Earth blocks are made from the soil beneath our feet.\nNarration: Each block is pressed, not fired, so it keeps the carbon in the ground.')
    assert rebuilt == expected   # whitespace only differs
    rebuilt, expected = apply_changes(SOURCE, [], SOURCE.replace('pressed', 'squeezed'))
    assert rebuilt != expected


def test_accepted_deletion_insertion_and_reworded():
    text = 'Narration: Earth blocks are made from the soil beneath our feet. They are old.\n\nNarration: Each block is pressed rather than fired.\n'
    changes = [ch('pressed, not fired, so it keeps the carbon in the ground.', 'pressed rather than fired.'),
               ch('', 'They are old.'),                                            # insertion: present once in the text
               ch('beneath our feet', 'under our feet', decision='reworded', operator_wording='beneath our feet')]   # operator kept the original words
    rebuilt, expected = apply_changes(SOURCE, changes, text)
    assert rebuilt == expected
    rebuilt, expected = apply_changes(SOURCE, [ch(' so it keeps the carbon in the ground', '')], SOURCE.replace(' so it keeps the carbon in the ground', ''))
    assert rebuilt == expected


def test_rejected_change_is_not_applied():
    changes = [ch('pressed, not fired', 'pressed rather than fired', decision='rejected')]
    rebuilt, expected = apply_changes(SOURCE, changes, SOURCE)
    assert rebuilt == expected
    rebuilt, expected = apply_changes(SOURCE, changes, SOURCE.replace('pressed, not fired', 'pressed rather than fired'))
    assert rebuilt != expected   # the rejected wording is in the text


def test_before_must_occur_exactly_once_and_decisions_are_required():
    with pytest.raises(Refused) as exc:
        apply_changes(SOURCE, [ch('Narration:', 'Voice:')], SOURCE)
    assert 'quote more words' in str(exc.value)
    with pytest.raises(Refused) as exc:
        apply_changes(SOURCE, [ch('not present at all', 'x')], SOURCE)
    assert 'before not found' in str(exc.value)
    with pytest.raises(Refused) as exc:
        apply_changes(SOURCE, [{'before': 'pressed', 'after': 'squeezed', 'reason': 'r'}], SOURCE)
    assert 'decision' in str(exc.value)
    with pytest.raises(Refused):
        apply_changes(SOURCE, [ch('pressed', 'x', decision='maybe')], SOURCE)
    with pytest.raises(Refused) as exc:
        apply_changes(SOURCE, [ch('pressed', 'x', decision='reworded')], SOURCE)
    assert 'operator_wording' in str(exc.value)
    with pytest.raises(Refused) as exc:
        apply_changes(SOURCE, [ch('', 'They are old.')], SOURCE)   # insertion absent from the text
    assert 'exactly once' in str(exc.value)


def test_first_difference_names_the_sentence():
    a = 'One is here. Two is here. Three is here.'
    assert first_difference(a, 'One is here. Two was here. Three is here.') == ('Two is here.', 'Two was here.')
    assert first_difference(a, 'One is here. Two is here.') == ('Three is here.', '(end of text)')
    assert first_difference(a, a) is None


# ---------- script_record ----------

def test_record_zero_changes_equal_text(src):
    proposal(src, SOURCE.replace('\n\n', '\n \n'))   # whitespace differs only
    s = record(src)['summary']
    assert s['changes_proposed'] == 0 and s['changes_accepted'] == 0 and s['passages'] == 2 and s['beats'] == 2


def test_record_refuses_a_text_that_differs_and_names_the_sentence(src):
    proposal(src, SOURCE.replace('not fired', 'never fired'))
    with pytest.raises(Refused) as exc:
        record(src)
    msg = str(exc.value)
    assert 'not the cleaned script plus the accepted changes' in msg and 'not fired' in msg and 'never fired' in msg


def test_record_accepts_a_listed_change_and_counts_decisions(src):
    text = SOURCE.replace('pressed, not fired', 'pressed rather than fired')
    proposal(src, text, [ch('pressed, not fired', 'pressed rather than fired'), ch('beneath our feet', 'under our feet', decision='rejected')])
    res = record(src)
    s = res['summary']
    assert s['changes_proposed'] == 2 and s['changes_accepted'] == 1 and s['changes_rejected'] == 1 and s['changes'] == 1
    saved = json.loads((src / 'out' / 'script.json').read_text(encoding='utf-8'))
    assert len(saved['changes']) == 2 and saved['changes'][1]['decision'] == 'rejected'   # the proposal stays as history
    assert saved['beats'][1]['text'].startswith('Narration: Each block is pressed rather than fired')


def test_record_refuses_an_unlisted_rewording_and_a_leaked_rejection(src):
    proposal(src, SOURCE.replace('pressed, not fired', 'pressed rather than fired').replace('our feet', 'our boots'), [ch('pressed, not fired', 'pressed rather than fired')])
    with pytest.raises(Refused) as exc:
        record(src)
    assert 'our boots' in str(exc.value)
    proposal(src, SOURCE.replace('pressed, not fired', 'pressed rather than fired'), [ch('pressed, not fired', 'pressed rather than fired', decision='rejected')])
    with pytest.raises(Refused):
        record(src)


def test_record_refuses_without_decisions_and_malformed_changes(src):
    proposal(src, SOURCE, [{'before': 'pressed', 'after': 'x', 'reason': 'r'}])
    with pytest.raises(Refused) as exc:
        record(src)
    assert 'decision' in str(exc.value)
    proposal(src, SOURCE, [{'before': 'pressed', 'after': 'x'}])   # no reason
    with pytest.raises(Refused):
        record(src)
    proposal(src, '   ')
    with pytest.raises(Refused) as exc:
        record(src)
    assert 'spoken_text' in str(exc.value)


# ---------- script_prepare inputs and the procedure text ----------

def test_prepare_passes_the_four_brief_values(src):
    out = script_prepare(src, PROC, prior_of())
    i = out['inputs']
    assert i['answers'] == {'brand-safety': 'never name the competitor'} and i['narration_language'] == 'ta'
    assert i['brand_and_safety_rules'] == ['no competitor names'] and i['chapters'] == ['Plinth', 'Curing']
    assert i['brief']['message'] == 'm' and i['script'] == SOURCE and out['prepared_at']


def test_prompt_and_steps_are_clean_and_carry_the_new_rules():
    p = PROC['prompt']
    for stale in ('propose_script', 'save_script', 'accept_script', 'employee', 'backend', 'browser', 'run revision', 'request ID', 'paid model', 'published Voice context'):
        assert stale not in p, stale
    assert p.startswith('VW-PROCEDURE') and 'rebuilds the text' in p and 'decision' in p and 'operator_wording' in p
    assert "operator's answers" in p and 'narration language' in p and 'chapters of the film' in p
    steps = ' '.join(PROC['steps'])
    assert 'I am deviating from the usual procedure' in steps and 'rebuilds the text' in steps and 'decision' in steps
    change = PROC['output_shape']['changes'][0]
    assert 'decision' in change and 'operator_wording' in change
