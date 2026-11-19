"""design/221 phase 3c (SK, 19 Nov 2026): row 1, the shared parts drawn once and approved in the chat.

In v3.json (section 11): the shared parts of a film with two or more drawn graphics, drawn once by one `vw-motion-parts` helper before any brief,
uploaded with `vw motion parts --file`, approved in the chat with their picture; the brief names the parts to use; a changed part is rendered again,
not rebuilt. In plugin/: the builder places the parts and never redraws one (the skill and its agent file); the rule writer writes no rule about how
a shared part is drawn; the checker never fails it. Sentences are added, none replaced. Registered in scripts/c1_split_v3.py after design/221d's
script. Exact anchors, each found once; run once: python scripts/d221e_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

LAST_OLD = 'never as a fact-check rule, and never a second time.'
PARTS_TEXT = (' The shared parts: when the film has two or more drawn graphics, after the shared look and before any brief, `vw motion parts` writes '
              'work/motion/parts/brief.md (the things two or more drawings show, then every drawn shot\'s brief) with the pictures to look at; one '
              '`vw-motion-parts` helper draws each repeating part once, as an SVG symbol, in work/motion/parts/parts.svg; upload it with '
              '`vw motion parts --file work/motion/parts/parts.svg`. The server draws one picture of the parts and the chat asks the operator: Approve, or '
              'Reject with their words, which go to a new `vw-motion-parts` helper; the next upload is asked again. `vw motion brief` is refused until the '
              'parts are approved; each brief then names the parts to use and saves parts.svg beside it, the server puts them in every drawing\'s page, '
              'and an upload that draws its own copy of a part it should use is refused. A parts file changed after the approval is approved again; a '
              'drawing that uses a changed part is rendered again, not rebuilt: its brief changed, so its rules are read again and the same project is '
              'uploaded and checked again before `vw motion render`. With one drawn graphic there are no shared parts.')
LAST_NEW = LAST_OLD + PARTS_TEXT

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('later', LAST_OLD, LAST_NEW),
]

LOOK = 'Open the pictures the brief lists under "Look at these before you draw" first: a part the film is about is drawn from what its picture shows, not from the words alone.'
SILENT = '- Silent: no audio, no music.'   # the last line of "The brief is the contract"; earlier scripts' sentences end here, so it is appended after
SKILL_NEW = (SILENT + '\n- The brief\'s "Use these parts" line names the film\'s shared parts, drawn once for the whole film and approved by the operator: place '
             'each with `<use href="#part-<name>">` at the size and place this drawing needs (the server puts them in the page; `parts.svg` beside the brief '
             'shows them): never redraw one, never copy its inside into your files, and give none of your own elements a `part-` id. A part that is missing '
             'or wrong: say so in REVIEW.md and give it back to the main assistant; do not draw your own.')
SHOT_NEW = (LOOK + ' Place the shared parts the brief names under "Use these parts" with `<use href="#part-<name>">`; never redraw one. A part that is '
            'missing or wrong: say so in REVIEW.md and give it back to the main assistant.')
NOTE_RULE = 'Write no rule about the corner note the brief says the server draws ("Illustrative, not to scale" or the like): the server sets its words, size and place.'
RULES_NEW = (NOTE_RULE + ' Write no rule about how a shared part (a part the brief names under "Use these parts") is drawn: it was drawn once and approved '
             'by the operator; rules about where it sits and how many there are still apply.')
NOTE_CHECK = "nothing of the drawing lies in the note's box (right of 80 % of the width and below 90 % of the height)."   # the end of design/221c's sentence
CHECK_NEW = (NOTE_CHECK + ' A shared part (a part the brief names under "Use these parts") was drawn once and approved by the operator: never fail how a '
             'shared part is drawn; judge where it sits and how many there are.')

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('skills/motion/SKILL.md', SILENT, SKILL_NEW),
    ('agents/vw-motion-shot.md', LOOK, SHOT_NEW),
    ('agents/vw-motion-rules.md', NOTE_RULE, RULES_NEW),
    ('agents/vw-motion-check.md', NOTE_CHECK, CHECK_NEW),
]

RETIRED = []   # row 1 adds sentences; none is replaced


def apply(prompt, parts):
    """The visuals text with this design's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = None if where == 'common' else next(p for p in parts if p['name'] == where)
        text = prompt if part is None else part['text']
        if new in text:
            continue
        if text.count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        text = text.replace(old, new)
        if part is None:
            prompt = text
        else:
            part['text'] = text
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
        if where == 'common':
            st['prompt'] = st['prompt'].replace(new, old)
        else:
            part = next(p for p in st['parts'] if p['name'] == where)
            part['text'] = part['text'].replace(new, old)
    return st


def now(file, text):
    """An earlier script's sentence for one plugin file as it reads after this script (for that script's test)."""
    for f, old, new in HELPERS:
        if f == file and new not in text:
            text = text.replace(old, new)
    return text


def _swap(path, pairs, name):
    """The pairs applied to one text file, each old sentence found once; bytes in and out, so the file keeps its line ends."""
    raw = path.read_bytes()
    end = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf-8').replace('\r\n', '\n')
    for old, new in pairs:
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: %s: not found once: %s' % (name, old[:60]))
            text = text.replace(old, new)
    path.write_bytes(text.replace('\n', end).encode('utf-8'))


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    for name in sorted({h[0] for h in HELPERS}):
        _swap(ROOT / 'plugin' / name, [(old, new) for file, old, new in HELPERS if file == name], 'plugin/' + name)
    rp = ROOT / 'server' / 'retired-sentences.json'
    r = json.loads(rp.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('visuals: design/221 phase 3c')


if __name__ == '__main__':
    main()
