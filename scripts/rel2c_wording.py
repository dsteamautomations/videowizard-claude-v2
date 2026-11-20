"""Release 2, the critic's points 2 and 8 (20 Nov 2026): a scene gets one verdict; a layout whose third check in a row fails is held and the
operator is asked on one card. The skill said "After two failed rounds, show the operator what is still open before another round", for which
the server had no card and no gate.

In v3.json, part `later`, one clause added after "a fresh `vw-guide-check` helper's verdict (`vw guide verdict`);".
In the plugin: the guide skill's sentence on failed rounds (the replaced words are in server/retired-sentences.json).
Registered in scripts/c1_split_v3.py after rel2b. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/rel2c_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

VERDICT = "a fresh `vw-guide-check` helper's verdict (`vw guide verdict`);"   # design/200
HELD = (' one verdict for each scene; a layout whose third check in a row fails is held: `vw visuals next` asks the operator (use it as it is, try once more, or '
        'change the shot), and no new scene of that shot is sent until they answer;')
PAIRS = [('later', VERDICT, VERDICT + HELD)]   # (the part, the sentence as it is, the sentence as it becomes)

SKILL_OLD = 'After two failed rounds, show the operator what is still open before another round.'
SKILL_NEW = ('A scene gets one verdict. After the third failed check in a row the server holds the shot and asks the operator in the chat (`vw visuals next`): '
             'build nothing more for it until they answer.')
HELPERS = [('skills/guide/SKILL.md', SKILL_OLD, SKILL_NEW)]   # (file under plugin/, the old sentence, the new one)

RETIRED = [SKILL_OLD]


def apply(prompt, parts):
    """The visuals text with this clause: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    for f, old, new in HELPERS:
        path = ROOT / 'plugin' / f
        data = path.read_bytes()
        if new.encode('utf-8') in data:
            continue
        if data.count(old.encode('utf-8')) != 1:
            sys.exit('not applied: %s: not found once: %s' % (f, old[:60]))
        path.write_bytes(data.replace(old.encode('utf-8'), new.encode('utf-8')))   # bytes: the file keeps its line ends
    rp = ROOT / 'server' / 'retired-sentences.json'
    raw = rp.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    print('visuals: one verdict for each scene; a layout held after its third failed check in a row')


if __name__ == '__main__':
    main()
