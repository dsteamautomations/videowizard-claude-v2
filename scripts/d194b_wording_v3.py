"""design/194, the re-review (SK, 14 Nov 2026: "the pronunciation step is not asked in the chat because it has to be done in the UI"; "one round of
re-review" of the instructions against the revised order). Instruction version 3: the voice prompt and step 5 send a word that sounds wrong to the voices
page and never ask about pronunciation in the chat; the brief's first step names what the prepare now prints; the script's claim checks come before
the approval question. Each anchor is found once (line breaks inside an anchor may differ); run once: python scripts/d194b_wording_v3.py"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
MARK = 'never ask a pronunciation question in the chat'

VOICE_PROMPT = [
    ("(the operator signs in: they play the provider's sample of every voice, shortlist, audition, pick, narrate and make a narration final;",
     "(the link the tool gives signs their browser in: they play the provider's sample of every voice, shortlist, audition, pick, narrate,\n"
     "correct a word that sounds wrong and make a narration final;"),
    ("Fetch the recording and ask the operator to listen for pronunciation, pace, complete wording and the intended delivery. "
     "Correct an issue once within the operator's explicit scope; never retry paid work on your own.",
     "Fetch the recording and ask the operator to listen\nfor pace, complete wording, the intended delivery and any word that sounds wrong. Pronunciation is the\n"
     "operator's own step on the voices page ('A word sounds wrong'): never ask a pronunciation question in the chat\nand never propose a list of words. "
     "Correct any other issue once within the operator's explicit scope; never retry\npaid work on your own."),
]
VOICE_STEPS = [
    ('A word that sounds wrong is corrected then, never asked about before the narration: `vw voice pronounce --word W --say "<how it sounds>" --hear --voice ID` (a small paid try), '
     'their listening, another `--say` as often as needed, `vw voice pronounce --word W --final`, and narrate again.',
     "A word that sounds wrong is corrected by the operator on the voices page ('A word sounds wrong' on the narration's row), never by a question in the chat, before or after "
     'the narration: give them the page link (`vw next` prints a fresh one). Only when they say they cannot use the page, the same steps exist in the tool, with their own spelling, never yours: '
     '`vw voice pronounce --word W --say "<their spelling>" --hear --voice ID` (a small paid try), their listening, `vw voice pronounce --word W --final`, and narrate again.'),
]
BRIEF_STEPS = [
    ('the rules remembered for this client, and this prompt.',
     "the rules remembered for this client, the film's category, the client's last production values filled in (`same_as_last`, when there is a latest brief) and this prompt."),
]
SCRIPT_STEPS = [
    ('Ask one question: approve this wording, or changes? Claim checks, by five rules:', 'First the claim checks, by five rules:'),
    ('any change is a normal before/after the operator decides.',
     'any change is a normal before/after the operator decides. Then, with the checks settled, ask one question: approve this wording, or changes?'),
]


def swap(text, old, new, where):
    pattern = r'\s+'.join(re.escape(tok) for tok in old.split())
    found = re.findall(pattern, text)
    if len(found) != 1:
        sys.exit(f'not applied: {where}: found {len(found)} times: {old[:70]}')
    return re.sub(pattern, lambda _: new, text, count=1)


def swap_steps(steps, pairs, where):
    for old, new in pairs:
        pattern = r'\s+'.join(re.escape(tok) for tok in old.split())
        hits = [i for i, s in enumerate(steps) if re.search(pattern, s)]
        if len(hits) != 1:
            sys.exit(f'not applied: {where}: in {len(hits)} steps: {old[:70]}')
        steps[hits[0]] = swap(steps[hits[0]], old, new, where)


def apply(d):
    st = {s['name']: s for s in d['stages']}
    if MARK in st['voice']['prompt']:
        return False
    for old, new in VOICE_PROMPT:
        st['voice']['prompt'] = swap(st['voice']['prompt'], old, new, 'voice prompt')
    swap_steps(st['voice']['steps'], VOICE_STEPS, 'voice steps')
    swap_steps(st['brief']['steps'], BRIEF_STEPS, 'brief steps')
    swap_steps(st['script']['steps'], SCRIPT_STEPS, 'script steps')
    return True


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    if not apply(d):
        print('already applied')
        return
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('voice, brief and script instructions: the re-review of design/194 applied')


if __name__ == '__main__':
    main()
