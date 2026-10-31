"""design/126: the agreed wording changes in instruction version 3 (IN1, BR1-BR3, SC1-SC5, AN1, OP2, OP3, U5), one exact replacement each.
Writes server/procedures/v3.json and the trace design/126-wording-trace.md (old -> new per pair, word counts per field).
Every old text must occur exactly once (a second run fails on the first pair). Version 2 is not touched."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
FIELDS = [('intake', 'prompt'), ('brief', 'prompt'), ('script', 'prompt'), ('script', 'steps'), ('analysis', 'steps'), ('options', 'steps'),
          ('visuals', 'parts.picture-search')]

PAIRS = [
    # stage, field, change, old, new
    ('intake', 'prompt', 'IN1', ' That is the situation this tool has\nalways been in and it survives it easily.', ''),
    ('intake', 'prompt', 'IN1',
     '\n\nPreserve spoken words exactly so the chosen script has an honest, inspectable relationship to its original source.', ''),
    ('intake', 'prompt', 'IN1', 'Return only JSON, no prose around it:', 'Write this to out/intake.json:'),
    ('brief', 'prompt', 'BR1', 'Where not supplied, label it a recommendation.', 'Where not supplied, its reason says so.'),
    ('brief', 'prompt', 'BR1', ' Do not rewrite\n  intake to force this stage to pass.', ''),
    # BR2: each removed sentence keeps its other copy (named in the trace)
    ('brief', 'prompt', 'BR2', 'Do not turn every missing fact into a required answer. ', ''),
    ('brief', 'prompt', 'BR2', 'Do not re-ask\nquestions already answered. ', ''),
    ('brief', 'prompt', 'BR2',
     'Each question has a stable id, question, why it matters, an optional recommendation\nand a boolean required flag. ', ''),
    ('brief', 'prompt', 'BR2', 'Never prefill an answer because it seems\nobvious. ', ''),
    ('brief', 'prompt', 'BR3',
     'Return a proposal containing purpose, audience, message, tone, ending, constraints,\nreasons keyed by the five field names, questions and '
     'production. Do not include\nanswers or approval. The file is the proposal; present its meaning and open\nquestions in readable chat, not JSON the '
     'operator has to copy. Ask for one grouped\nacceptance or corrections.',
     'The file is the proposal; present its meaning and open questions in readable chat, not JSON the operator has to copy.'),
    ('script', 'prompt', 'SC1',
     "exact title and client, any\npreviously accepted prepared script, exact supplied wording and notes, prior\nproposals and the operator's decisions. "
     'Read all current inputs.',
     'exact title and client, and the directory facts the prepare prints. Read all current inputs.'),
    ('script', 'prompt', 'SC2',
     'Defer Treatment, shots, media study, visual achievability, AI makeability, material\ncoverage and filmability. Missing footage is not a defect in '
     'narration. Do not gate\nthis stage on visual plans, casting, location, voice selection or provider settings.\nNo voice generation, paid call or '
     'automatic progression into Voice is authorized by\naccepting a script.',
     'Pictures and footage come later: missing footage is not a defect in narration. Accepting a script starts no voice or paid call.'),
    ('script', 'steps[2]', 'SC3', 'Search only after the operator says yes; show what you found;',
     'Search only after the operator says yes; show what the source page says;'),
    ('script', 'steps[2]', 'SC3', 'I want to check X in the script, because', 'I want to check X, because'),
    ('script', 'prompt', 'SC4',
     'After the operator decides, each change carries decision: accepted, rejected, or\nreworded with operator_wording; rejected changes stay in the '
     'file and are not\napplied. ', ''),
    ('script', 'prompt', 'SC4', 'Unaccepted edits must not leak into the final text. ', ''),
    ('script', 'prompt', 'SC5',
     'Return the complete proposed spoken_text, optional notes, a concise assessment and\nchanges containing before, after and reason. Use exact before '
     'excerpts from the\ncurrent working wording and show the corresponding proposed wording; insertions or\ndeletions can use an empty before or after. '
     'Keep unchanged text exact. Changes can\ncross physical lines; there is no fixed-row constraint. Make the full proposal\nconsistent with the listed '
     'changes. Every edit must be a listed change with an exact before that occurs once; anchor an insertion on a short before excerpt rather than an '
     'empty one.',
     'Use exact before excerpts from the current working wording and show the proposed wording; a deletion has an empty after; anchor an insertion on '
     'a short before excerpt. Keep unchanged text exact. Changes can cross physical lines.'),
    ('analysis', 'steps[0]', 'AN1', None,
     "Run `vw analysis start [--understand-audio no] [--exclude <clip name> …]` without asking: the clip list was confirmed at media, and the model "
     "listens to the clips' sound unless the operator said there that it must not be used even for analysis. One paid Gemini 3.8 Flash request per "
     "clip (agentic for a clip over 15 seconds, plain for a shorter one); tell the operator, do not ask. The server computes eligibility and crops."),
    ('options', 'steps[1]', 'OP2', 'a scene covers one chapter: a paragraph covering two is split where the second begins',
     'list every chapter the paragraph covers; split a paragraph only when the operator asks'),
    ('options', 'steps[3]', 'OP3', 'E2, N17, N14; each says what to do', 'E2, N17 (claims), N14; each says what to do'),
    ('visuals', 'parts.picture-search', 'U5', 'the two-to-six-word keywords', 'the two-to-twelve-word keywords'),
    ('visuals', 'parts.picture-search', 'U5', '<two to six words: the thing and its place or trade>', '<two to twelve words: the thing and its place or trade>'),
    ('visuals', 'parts.picture-search', 'U5', '<stock site, outside the six words;', '<stock site, outside the twelve words;'),
]

KEPT = {   # BR2: where each removed sentence is still said
    'Do not turn every missing fact into a required answer. ': 'prompt: "Only consequential unresolved questions may be required."',
    'Do not re-ask\nquestions already answered. ': 'prompt: "ask again only if their meaning or underlying source actually changed, explaining why."',
    'Each question has a stable id, question, why it matters, an optional recommendation\nand a boolean required flag. ':
        'brief step 1 and the answer shape (`questions` with id, question, why, recommendation, required)',
    'Never prefill an answer because it seems\nobvious. ': 'prompt: "A recommended answer is never a human answer."; step 1: "Never fill `answers` yourself"',
}


def apply_visuals(parts):
    """The U5 pairs that land in the visuals parts, for c1_split_v3.py --check (applied after design/125's)."""
    for stage, name, change, old, new in PAIRS:
        if stage == 'visuals':
            part = next(p for p in parts if p['name'] == name[6:])
            assert part['text'].count(old) == 1, (change, old[:60])
            part['text'] = part['text'].replace(old, new)


def field(stage, name):
    if name.startswith('steps['):
        return stage['steps'], int(name[6:-1])
    if name.startswith('parts.'):
        return next(p for p in stage['parts'] if p['name'] == name[6:]), 'text'
    return stage, name


def words(stages, stage, name):
    s = stages[stage]
    if name == 'steps':
        return sum(len(t.split()) for t in s['steps'])
    holder, k = field(s, name)
    return len(holder[k].split())


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    stages = {s['name']: s for s in d['stages']}
    before = {f: words(stages, *f) for f in FIELDS}
    trace = ['# 126 — wording trace, instruction version 3', '',
             'Every agreed wording change of design/126 (IN1, BR1-BR3, SC1-SC5, AN1, OP2, OP3, U5), old text → new text, in the order applied. '
             'Made by `scripts/d126_wording_v3.py`; version 2 untouched. Line breaks inside the stored prompts are shown as they are.', '']
    for stage, name, change, old, new in PAIRS:
        holder, k = field(stages[stage], name)
        text = holder[k]
        if old is None:   # the whole step is replaced
            old = text
        if text.count(old) != 1:
            sys.exit(f'{stage} {name} ({change}): the old text occurs {text.count(old)} times: {old[:80]!r}')
        holder[k] = text.replace(old, new)
        trace += [f'## {change} — {stage}, {name} ({len(old.split())} → {len(new.split())} words)', '', '**Old:**', '',
                  '> ' + old.strip('\n').replace('\n', '\n> '), '', '**New:**', '', ('> ' + new.replace('\n', '\n> ')) if new else '> (removed)', '']
        if old in KEPT:
            trace += [f'Kept copy: {KEPT[old]}.', '']
    after = {f: words(stages, *f) for f in FIELDS}
    trace += ['## Words read by the assistant, per field', '', '| Field | Before | After |', '|---|---|---|',
              *(f'| {s} {n} | {before[(s, n)]} | {after[(s, n)]} |' for s, n in FIELDS), '']
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    (ROOT / 'design' / '126-wording-trace.md').write_text('\n'.join(trace) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(PAIRS)} replacements written')
    for f in FIELDS:
        print(f, before[f], '->', after[f])


if __name__ == '__main__':
    main()
