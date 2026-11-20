"""Release 4 (SK, 20 Nov 2026): the first frame of a layout first, its video behind it. The still needs only the guide's first frame; the video
is needed only for the take. The texts said "the server renders the guide" and, in the skill's table, one row "free, several minutes" before the
still: read that way, a still waited for the whole video.

In v3.json, part `later`, the clause "the server renders the guide;" becomes the two renders and when the still is ordered.
In the plugin: row 4 of the guide skill's table (the replaced row is in server/retired-sentences.json).
Registered in scripts/c1_split_v3.py after rel2c. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/rel4_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

OLD = 'the server renders the guide;'   # design/200
NEW = ("the server renders the guide, its first frame first (under a minute) and its video behind it: order each shot's still as soon as its first frame is ready "
       '(`vw visuals next` names them); the video is needed only for the take;')
PAIRS = [('later', OLD, NEW)]   # (the part, the sentence as it is, the sentence as it becomes)

SKILL_OLD = '| 4. The guide is rendered | by the server, after a passing verdict; `vw guide status --shot S` | free, several minutes |'
SKILL_NEW = ('| 4. The guide is rendered | by the server, after a passing verdict: its first frame first (under a minute), its video behind it (several minutes; needed only '
             'for the take, row 8). Order the still (row 5) as soon as the first frame is ready; `vw guide status --shot S` says which is ready | free |')
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
    print('visuals: the first frame of a layout first, its video behind it; the still as soon as the first frame is ready')


if __name__ == '__main__':
    main()
