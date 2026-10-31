"""design/126: the version 3 wording (scripts/d126_wording_v3.py): IN1, BR1-BR3, SC1-SC5, AN1, OP2, OP3, U5. Version 2 untouched."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = {s['name']: s for s in json.loads((ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8'))['stages']}
V3 = {s['name']: s for s in json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']}


def flat(t):
    return ' '.join(t.split())   # the stored prompts are wrapped; a sentence may cross a line


def test_in1_intake_prompt_trimmed_rules_kept():
    p = flat(V3['intake']['prompt'])
    assert 'survives it easily' not in p and 'honest, inspectable relationship' not in p and 'Return only JSON' not in p
    assert 'Write this to out/intake.json:' in p
    assert 'YOU NEVER REWRITE A LINE' in p and 'So the bar for removing is HIGH' in p and 'A line you wrongly KEEP' in p
    assert 'Return only JSON' in V2['intake']['prompt']   # version 2 untouched


def test_br1_br2_br3_brief_prompt():
    p = flat(V3['brief']['prompt'])
    assert 'label it a recommendation' not in p and 'force this stage to pass' not in p and 'Where not supplied, its reason says so.' in p
    for gone, kept in (('Do not turn every missing fact into a required answer.', 'Only consequential unresolved questions may be required.'),
                       ('Do not re-ask questions already answered.', 'ask again only if their meaning or underlying source actually changed'),
                       ('Each question has a stable id', 'A recommended answer is never a human answer.'),
                       ('Never prefill an answer because it seems obvious.', 'A recommended answer is never a human answer.')):
        assert gone not in p and kept in p, gone
    assert 'Never fill `answers` yourself' in ' '.join(V3['brief']['steps'])
    assert 'Return a proposal' not in p and 'Ask for one grouped acceptance' not in p
    assert p.endswith('The file is the proposal; present its meaning and open questions in readable chat, not JSON the operator has to copy.')


def test_sc1_to_sc5_script_prompt_and_step():
    p = flat(V3['script']['prompt'])
    assert 'prior proposals' not in p and 'and the directory facts the prepare prints. Read all current inputs.' in p   # SC1
    assert 'filmability' not in p and 'gate' not in p   # SC2
    assert 'Pictures and footage come later: missing footage is not a defect in narration.' in p and 'Accepting a script starts no voice or paid call.' in p
    step2 = V3['script']['steps'][2]
    assert 'show what the source page says' in step2 and 'show what you found' not in step2 and 'I want to check X, because' in step2   # SC3
    assert 'each change carries decision' not in p and 'must not leak' not in p   # SC4
    assert 'add `decision` to every change' in V3['script']['steps'][3] and 'The tool checks that only the accepted changes are applied' in p
    assert 'fixed-row' not in p and 'can use an empty before' not in p and 'a deletion has an empty after; anchor an insertion on a short before excerpt.' in p   # SC5
    assert 'Every edit must be a listed change with an exact before that occurs once.' in V3['script']['steps'][1]
    shape = json.dumps(V3['script']['output_shape'])   # SC5 follow-up: the answer shape agrees with the prompt
    assert 'empty for an insertion' not in shape and 'an insertion anchors on a short excerpt' in shape


def test_an1_analysis_starts_without_asking():
    s = V3['analysis']['steps'][0]
    assert '?' not in s and 'without asking' in s and '--understand-audio no' in s and '--exclude' in s and '15 seconds' in s


def test_op2_op3_options_steps():
    assert 'list every chapter the paragraph covers; split a paragraph only when the operator asks' in V3['options']['steps'][1]
    assert 'a scene covers one chapter' not in V3['options']['steps'][1]
    assert 'E2, N17 (claims), N14' in V3['options']['steps'][3]


def test_u5_keywords_two_to_twelve_words():
    v = V3['visuals']
    every = '\n'.join([v['prompt'], *v['steps'], *(p['text'] for p in v['parts'])])
    assert 'two to six' not in every and 'two-to-six' not in every and 'the six words' not in every
    assert 'two to twelve words' in every and 'two-to-twelve-word' in every and 'outside the twelve words' in every
