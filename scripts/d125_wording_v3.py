"""design/125: the agreed wording changes in instruction version 3 (I1-I3, B1-B3, S1-S3, V1-V3, M2, A2-A4), one exact replacement each.
Writes server/procedures/v3.json and the trace design/125-wording-trace.md (old -> new per pair). Every old text must occur exactly once."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [
    # stage, field, change, old, new
    ('intake', 'steps[2]', 'I1, I2',
     " The client is already on the run (chosen at `vw start` from the directory). Before `vw start`, ask the operator which image model this film uses, GPT Image (openai) or Gemini Nano Banana (gemini): `vw start --client … --images openai|gemini`; the choice is recorded on the run and never changes (design/120); on a gemini run a prompt takes up to 14 pictures by kind (6 of things, 5 of people, 3 of style), a region edit is said in words (the server still copies the start back outside the region), and a component is made on chroma green that the server keys out.",
     " The client and the film's picture AI are already on the run (both chosen at `vw start`)."),
    ('visuals', 'parts.later', 'I1',
     '(16 for GPT Image, 14 for Gemini, by kind; the server names the excess)',
     '(16 for GPT Image; 14 for Gemini, by kind: 6 of things, 5 of people, 3 of style; the server names the excess)'),
    ('visuals', 'parts.later', 'I1',
     'name the landmark in the prompt); the server masks it and copies the start back outside it.',
     'name the landmark in the prompt); the server masks it and copies the start back outside it. On a Gemini film a region edit is also said in words (the server still copies the start back outside the region), and a component is made on chroma green, which the server keys out.'),
    ('intake', 'prompt', 'I3',
     '  "titles": ["...", "...", "..."]\n}',
     '  "titles": ["...", "...", "..."],\n  "notes": "a short explanation of what was removed"\n}'),
    ('brief', 'prompt', 'B2', '# VW-BRIEF v2.0 — purposeful, low-friction Brief\n\n', ''),
    ('brief', 'prompt', 'B2',
     ' Do not silently accept model defaults. A malformed\nproposal gets at most one correction with this same prompt, then explain the issue\nand offer supplied input or a pause.', ''),
    ('brief', 'prompt', 'B3',
     "Brand and safety rules,\nwhether the speaker may be seen on camera, the languages spoken in the footage and the\nnarration language are the operator's words, asked on every film. Ask in the same\nmessage where the film plays and its frame shape (production.format: frame 16:9, 9:16,\n1:1 or 4:5; destinations such as YouTube or Instagram; whether it is watched muted);\n16:9 and no destinations unless they say.",
     "Brand and safety rules,\nwhether the speaker may be seen on camera, the languages spoken in the footage, the\nnarration language, and where the film plays and its frame shape (production.format:\nframe 16:9, 9:16, 1:1 or 4:5) are the operator's words, asked on every film in one\nmessage; the list is in the steps."),
    ('brief', 'steps[1]', 'B1, B3',
     'Ask the operator, in one message, on every film: the brand and safety rules (for example: no competitor logos, PPE required or not, nothing staged; an empty list if none), the languages spoken in the footage, and the narration language.',
     'Ask the operator, in one message, on every film: the brand and safety rules (for example: no competitor logos, PPE required or not, nothing staged; an empty list if none), the languages spoken in the footage (an empty list if nobody speaks or there is no footage), the narration language, whether the speaker may be seen on camera, and where the film plays and its frame shape (16:9, 9:16, 1:1 or 4:5; destinations such as YouTube or Instagram; watched muted or not; 16:9 and no destinations unless they say).'),
    ('script', 'prompt', 'S1', '# VW-SCRIPT-PREPARATION v2.1 — one meaningful wording pass\n\n', ''),
    ('script', 'prompt', 'S1', ' Do not reproduce normalize, check, remediate, filmability, lock or per-line tagging gates.', None),   # filled from the file below
    ('script', 'prompt', 'S1', '\nDo not require VO/DIALOGUE/ACTION tagging of every physical line from the operator.', ''),
    ('script', 'prompt', 'S1', 'On malformed output make at most one correction with this same prompt; then\nexplain and offer user-supplied text or pause. ', ''),
    ('script', 'prompt', 'S2',
     'The record step rebuilds the text from the\ncleaned script plus the accepted changes and refuses anything else, so every edit\nmust be a listed change with an exact before that occurs once; anchor an insertion\non a short before excerpt rather than an empty one.',
     'Every edit must be a listed change with an exact before that occurs once; anchor an insertion on a short before excerpt rather than an empty one.'),
    ('script', 'prompt', 'S2',
     'Verify the agreed changes are present and all unaccepted changes are absent. This\nis verification of the agreed edit, not a second critique or another round of\nmandatory recommendations.',
     'The tool checks that only the accepted changes are applied; do not critique again.'),
    ('script', 'steps[1]', 'S3',
     'Every edit must be a listed change with an exact before that occurs once.',
     'Every edit must be a listed change with an exact before that occurs once. When the assessment names figures or claims the message rests on, list them in `claims` (each {text, checked: true or false, source when checked}); the visuals stage reads them, so a graphic shows the figure the narration speaks.'),
    ('visuals', 'parts.preparation', 'S3',
     'Read prompt.md, gaps.json and intended-visuals.json first,',
     'Read prompt.md, gaps.json and intended-visuals.json first, and claims.json (the figures the narration rests on, and whether the operator had them checked: a picture or graphic shows the same figure, and a checked one is not searched again),'),
    ('voice', 'prompt', 'V3', '# VW-VOICE v4 — choose a narrator, direct the delivery, record once\n\n', ''),
    ('voice', 'prompt', 'V2', None, None),   # FIND and COMPARE, filled below
    ('voice', 'direction_prompt', 'V3', '# VW-DIRECTION v1 — how the narration should be delivered\n\n', ''),
    ('voice', 'direction_prompt', 'V1',
     'the register tag at the top governs them. A list of forty tags on forty sentences is wrong.',
     'the register tag at the top governs them. A list of forty tags on forty sentences is wrong.\nThe register is placed at the top for you; do not repeat it on the first sentence.'),
    ('voice', 'steps[1]', 'V3', 'the direction and the test passage (design/54 B): run', 'the direction and the test passage: run'),
    ('voice', 'steps[3]', 'V2',
     'Chat fallback: one question per message, recommendation first with its reason from the brief, and wait for each answer: gender; age group; accent; register. Repeat the four and ask for a yes. Then one `vw voice catalog --gender … --age … --accent … [--search <name>] [--page N]` call',
     "Chat fallback: one question per message, recommendation first with its reason from the brief, and wait for each answer: gender; age group; accent (language and accent are different things; never from the client's name); register (warm, authoritative, conversational, measured). Repeat the four and ask for a yes. Only then one `vw voice catalog --gender … --age … --accent … [--search <name>] [--page N]` call, library scope, with exactly those filters (one line per voice; it prints the voices page link with the same filters; `vw voice history --voice ID` says more about a favourite)"),
    ('voice', 'steps[3]', 'V2',
     'A library voice is saved to the account automatically when it is auditioned or narrated (no custom slot is used).',
     'A library voice is saved to the account automatically when it is auditioned or narrated (no custom slot is used); `vw voice add-library` is only for a voice the catalog never listed.'),
    ('media', 'prompt', 'M2',
     ' Facts of the tool: clips go in runs/<code>/in/, at most 200 MB each; a variable-frame-rate clip is converted to constant frame rate before upload and reported; prepare reports the clip count and total MB; the upload runs three clips at a time with retries and reports each finished clip; re-run record to resume an interrupted upload, finished clips are skipped.',
     ' The tool\'s facts (size limit, conversion, upload, resume) are in the steps.'),
    ('media', 'steps[1]', 'M2', ' (design/107).', '.'),
    ('media', 'steps[2]', 'M2', 'Re-run record to resume an interrupted upload.', 'Re-run record to resume an interrupted upload; finished clips are skipped.'),
    ('media', 'steps[2]', 'M2', 'uploads with receipts, prints one line per finished clip', 'uploads with receipts, three clips at a time with retries, prints one line per finished clip'),
    ('analysis', 'steps[0]', 'A2, A3',
     '(agentic); tell the operator, do not ask. The log follows the blueprint Stage 1 contract (clip-log-v1); the server computes eligibility and crops.',
     '(agentic for a clip over 15 seconds, plain for a shorter one); tell the operator, do not ask. The server computes eligibility and crops.'),
    ('analysis', 'steps[2]', 'A4',
     'A failed clip: tell the operator the reason from status.',
     'A clip that fails for a passing reason (an error in the provider\'s stream, an answer cut off or empty, a busy service) is retried by the server up to three times on its own; only then does it reach you. A failed clip: tell the operator the reason from status.'),
]

FIND_NEW = ("FIND. For a repeat client the last voice comes first; then the favourites (`vw stage voice prepare`\n"
            "lists them with where each was used); then the catalogue. The voices page is the default (the operator\n"
            "signs in: they play the provider's sample of every voice, shortlist, audition, pick, narrate and make a narration final; `vw next` and\n"
            "`vw stage voice prepare` tell you what they did there); the chat path is in the steps.\n"
            "Never substitute a curated three for the matching results, and never say an incomplete search\n"
            "exhausted the catalogue. No name-only matching: a voice is its exact id.\n\n"
            "COMPARE. Propose one to six account voices, one supported model and settings; every candidate\n"
            "reads the chosen test passage (one exact contiguous excerpt of the accepted script, 50 to 100 words and at\n"
            "most 3,000 characters). Present voices, reasons, model, settings and the passage together. Auditions\n"
            "are paid: say what will be generated and proceed. A description justifies a recommendation; only the\n"
            "operator's listening establishes a preference. Never claim to have heard anything.\n\n")


def apply_visuals(parts):
    """The design/125 pairs that land in the visuals parts, for c1_split_v3.py --check (applied after the C2 fixes)."""
    for stage, name, change, old, new in PAIRS:
        if stage == 'visuals':
            part = next(p for p in parts if p['name'] == name[6:])
            assert part['text'].count(old) == 1, (change, old[:60])
            part['text'] = part['text'].replace(old, new)


def field(stage, name):
    if name.startswith('steps['):
        return stage['steps'], int(name[6:-1])
    if name.startswith('parts.'):
        part = next(p for p in stage['parts'] if p['name'] == name[6:])
        return part, 'text'
    return stage, name


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    stages = {s['name']: s for s in d['stages']}
    script_prompt = stages['script']['prompt']
    i = script_prompt.index('Do not reproduce')
    j = script_prompt.index('tagging gates.', i) + len('tagging gates.')
    voice_prompt = stages['voice']['prompt']
    find_old = voice_prompt[voice_prompt.index('FIND.'):voice_prompt.index('MODELS AND SETTINGS.')]
    trace = ['# 125 — wording trace, instruction version 3', '', 'Every agreed wording change, old text → new text, in the order applied. Made by `scripts/d125_wording_v3.py`.', '']
    for stage, name, change, old, new in PAIRS:
        if change == 'S1' and new is None:
            old, new = script_prompt[i - 1:j], ''   # the sentence crosses a line break in the file
        if change == 'V2' and old is None:
            old, new = find_old, FIND_NEW
        holder, k = field(stages[stage], name)
        text = holder[k]
        if text.count(old) != 1:
            sys.exit(f'{stage} {name} ({change}): the old text occurs {text.count(old)} times: {old[:80]!r}')
        holder[k] = text.replace(old, new)
        trace += [f'## {change} — {stage}, {name}', '', '**Old:**', '', '> ' + old.replace('\n', '\n> '), '', '**New:**', '', ('> ' + new.replace('\n', '\n> ')) if new else '> (removed)', '']
    a = stages['analysis']
    a['settings'] = {**a['settings'], 'processing_mode': 'auto', 'agentic_over_seconds': 15}
    trace += ['## A2 — analysis, settings', '', '**Old:** `processing_mode: AGENTIC`, `agentic_over_seconds: 300`', '', '**New:** `processing_mode: auto`, `agentic_over_seconds: 15`', '']
    s = stages['script']
    s['output_shape'] = {**s['output_shape'], 'claims': [{'text': 'a figure or claim the message rests on', 'checked': False, 'source': 'where it was checked, when checked'}]}
    trace += ['## S3 — script, output_shape', '', '**New:** `claims: [{text, checked, source}]`', '']
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    (ROOT / 'design' / '125-wording-trace.md').write_text('\n'.join(trace) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(PAIRS)} replacements and 2 settings written')


if __name__ == '__main__':
    main()
