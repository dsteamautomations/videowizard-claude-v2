"""design/125 stage 7: the independent check's fixes to the version 3 wording (problems 1-6 of its report), one exact replacement each,
applied after scripts/d125_stage7_wording_v3.py. Appends old -> new to design/125-stage7-wording-trace.md and prints the word count per stage."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
TRACE = ROOT / 'design' / '125-stage7-wording-trace.md'

PAIRS = [
    ('options', 'prompt', 'check 1, 5: E2 for an AI-only scene; one list of flags',
     'Flags come grouped by rule: act on R5, B1, B2, rule 11 and E1, on E2 (a blank over 12 s: find a footage cut-in, a B-roll clip or a frame that relates and split it; a run of AI pictures that long reads as synthetic); and on N17 and N14 (the step and the place: another clip, a blank, or a decision for the operator); R1, R10, R8 and R4 inform.',
     'E2 (a blank over 12 s, an AI-only scene included): a run of AI pictures that long reads as synthetic; find a footage cut-in, a B-roll clip or a frame that relates and split it, or say in intent why it must stay whole. The steps list the flags to act on.'),
    ('options', 'prompt', 'check 3: P9 keeps "by default" and the B-roll gate',
     '3. An abstract idea is a sentence with nothing to show (savings, cost, comfort, strength claims): a blank. A sentence naming something the camera can see is matched like any other. B-roll: clearly related to the words, nothing wrong.',
     '3. Abstract ideas (savings, cost, comfort, strength claims) are blanks by default; a sentence naming something the camera can see is matched like any other. B-roll only when clearly relevant, relatable to the words, and nothing in it wrong.'),
    ('options', 'steps[3]', 'check 5: what each act-on flag is',
     '`check` and `propose` list in full the flags to act on (`act_on`: R5, B1, B2, rule 11, E1, E2, N17 and N14) and count the rest (`for_information`: R1, R10, R8, R4).',
     '`check` and `propose` list in full the flags to act on (`act_on`: R5 a hold, B1 and B2 word timing, rule 11 a long real shot, E1 a short blank, E2 a long blank, N17 and N14 the step and the place: another clip, a blank or a question) and count the rest (`for_information`: R1, R10, R8, R4).'),
    ('options', 'steps[0]', 'check 6: the per-file limit said',
     'pieces-<scene>.json: each scene\'s sentences and the pieces that fit it, direct first;',
     'pieces-<scene>.json: each scene\'s sentences and the pieces that fit it, direct first, a large scene continuing in pieces-<scene>-2.json;'),
    ('master', 'steps[0]', 'check 2, 4: a scene decided by its parts; keep one of two versions',
     'scene slides (1, 2 …) and second choices (2-2) KEEP, REJECT or KEEP_WITH_EDIT, but a scene whose shots are all decisions takes only KEEP_WITH_EDIT (trim a shot): its parts decide it;',
     'scene slides (1, 2 …) and second choices (2-2, keep one of the two) KEEP, REJECT or KEEP_WITH_EDIT; a scene slide whose footage is all questions (no second choice) needs no answer: its parts decide it, a trim (KEEP_WITH_EDIT) if wanted;'),
    ('master', 'steps[0]', 'check 2, 4: offset (the next sentence said twice)',
     ' Watch the review film, then answer each slide (on the page, or `vw master decide`): the first answer approves the options.',
     ' The first answer approves the options.'),
]


def words(stage):
    return len(' '.join([stage.get('prompt') or '', stage.get('direction_prompt') or '', *(stage.get('steps') or []),
                         *(p['text'] for p in stage.get('parts') or [])]).split())


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    stages = {s['name']: s for s in d['stages']}
    before = {n: words(stages[n]) for n in ('options', 'master')}
    trace = ['', '## Fixes after the independent check (30 Oct 2026, `scripts/d125_stage7_fixes_v3.py`)', '']
    for stage, name, why, old, new in PAIRS:
        s = stages[stage]
        holder, k = (s['steps'], int(name[6:-1])) if name.startswith('steps[') else (s, name)
        if holder[k].count(old) != 1:
            sys.exit(f'{stage} {name}: the old text occurs {holder[k].count(old)} times: {old[:70]!r}')
        holder[k] = holder[k].replace(old, new)
        trace += [f'### {why} — {stage}, {name}', '', '**Old:**', '', '> ' + old.strip(), '', '**New:**', '', '> ' + new.strip(), '']
    after = {n: words(stages[n]) for n in ('options', 'master')}
    trace += ['Words: ' + '; '.join(f'{n} {before[n]} → {after[n]}' for n in before), '']
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    with TRACE.open('a', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(trace) + '\n')
    print(before, '->', after)


if __name__ == '__main__':
    main()
