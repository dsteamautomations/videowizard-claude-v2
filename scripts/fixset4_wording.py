"""Fix set, the critic's points (SK, 19 Nov 2026), in the served text and the helpers' texts.

In v3.json: a shot whose only text is the corner note or a logo has `carries_text: false` (point 4: phase 3's sentence "is not asked for
labels" is replaced; the server asks every `carries_text` shot again); the round's list also names the musts that passed, answered only when
the upload broke one (point 6); the still end-frame of a drawing that continues another is started once the earlier still is approved, its
motion only after the earlier project passed, and `vw motion brief` puts the earlier approved still beside the brief (point 7). In plugin/:
the checker is told the second part of the round's list and the frame a continuing still opens on; the skill the same frame; the still-prompts
helper may list a folder (Glob) and says when a rule file cannot be read (point 10). The replaced sentences are in server/retired-sentences.json.
Registered in scripts/c1_split_v3.py after fix set phase 3's script. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/fixset4_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

LABELS_OLD = ('The corner note and a logo picture are not text the shot carries: a shot whose only text they are has `labels: []` and is not asked for '
              'labels.')   # fix set phase 3 (A3.3)
LABELS_NEW = 'The corner note and a logo picture are not text the shot carries: a shot whose only text they are has `carries_text: false`.'
ROUND = 'when the brief changed since, there is no such file and every rule is answered again.'
ROUND_NEW = (ROUND + ' Below those rules the file lists the musts that passed before: the checker answers one of them only when this upload broke it, and a '
             'fail there is a failed must.')
CHAIN_OLD = '(a shot whose brief says "Continues from <shot>" is started only after that shot\'s project has passed its fact check)'
CHAIN_NEW = ('(the still end-frame of a shot whose brief says "Continues from <shot>" is started once that shot\'s still end-frame is approved, its motion only '
             'after that shot\'s project has passed its fact check)')
ORDER = 'a change the operator asks for then reaches every drawing before anything is animated.'
ORDER_NEW = (ORDER + ' For the still end-frame of a drawing that continues another, `vw motion brief` puts the earlier drawing\'s approved still end-frame '
             '(opens-on.png) and that still\'s files in work/motion/S/from-<that shot>/, so the stills of a chain follow one another on the approvals; when the '
             'earlier still is replaced later, the next-step line names the still to make again.')

PAIRS = [   # (the part's name, the old sentence, the new one)
    ('plan', LABELS_OLD, LABELS_NEW),
    ('later', ROUND, ROUND_NEW),
    ('later', CHAIN_OLD, CHAIN_NEW),
    ('later', ORDER, ORDER_NEW),
]

LIST = '(the server keeps it as a note and asks for it when the frame exists).'
LIST_NEW = (LIST + ' Below the open rules, rules-round.md lists the musts that passed before: answer one of those only when this upload broke it, with '
            '"pass": false and where.')
FROM = 'compare against it only what the rules say continues.'
FROM_NEW = (FROM + ' On a still end-frame built before that shot\'s project has passed, the frame is `from-<shot>/opens-on.png`, that shot\'s approved still '
            'end-frame.')
COPY = 'open exactly as it ends and change only what this shot adds.'
COPY_NEW = (COPY + ' For the still end-frame, while that shot\'s project has not passed, `from-<shot>/` holds its approved still end-frame (`opens-on.png`) '
            'and that still\'s files: build this still from them.')
TOOLS_OLD = 'tools: Read, Write\nmodel: opus'
TOOLS_NEW = 'tools: Read, Write, Glob\nmodel: opus'
ALWAYS_OLD = '- `work/visuals/library/`: `always/` once, and the folder `steps.json` maps to a still picture.'
ALWAYS_NEW = ('- `work/visuals/library/`: every file of `always/` once (list them with Glob), and the folder `steps.json` maps to a still picture. If a rule '
              'file you were named cannot be read, say so in your answer; never guess its rules.')

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('agents/vw-motion-check.md', LIST, LIST_NEW),
    ('agents/vw-motion-check.md', FROM, FROM_NEW),
    ('skills/motion/SKILL.md', COPY, COPY_NEW),
    ('agents/vw-still-prompts.md', TOOLS_OLD, TOOLS_NEW),
    ('agents/vw-still-prompts.md', ALWAYS_OLD, ALWAYS_NEW),
]

RETIRED = ['a shot whose only text they are has `labels: []` and is not asked for labels',                       # point 4: the server asks; the way out is carries_text false
           'is started only after that shot\'s project has passed its fact check)']                                # point 7: the still once the earlier still is approved


def apply(prompt, parts):
    """The visuals text with this set's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == where)
        if new in part['text']:
            continue
        if part['text'].count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        part['text'] = part['text'].replace(old, new)
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
        part = next(p for p in st['parts'] if p['name'] == where)
        part['text'] = part['text'].replace(new, old)
    return st


def now(file, text):
    """An earlier script's sentence for one plugin file as it reads after this script (for that script's test)."""
    for f, old, new in HELPERS:
        if f == file and new not in text:
            text = text.replace(old, new)
    return text


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    for file, old, new in HELPERS:
        path = ROOT / 'plugin' / file
        raw = path.read_bytes()   # bytes in and out, so the file keeps its line ends
        end = '\r\n' if b'\r\n' in raw else '\n'
        text = raw.decode('utf-8').replace('\r\n', '\n')
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: plugin/%s: not found once: %s' % (file, old[:60]))
            path.write_bytes(text.replace(old, new).replace('\n', end).encode('utf-8'))
    rp = ROOT / 'server' / 'retired-sentences.json'
    r = json.loads(rp.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('visuals and helpers: the critic\'s points on the fix set')


if __name__ == '__main__':
    main()
