"""Release 2, B4 and B4b (SK, 20 Nov 2026): several still end-frames of drawn graphics, or several layout drawings of AI video shots, that
are ready together are handed out as a group and shown in one message, each with its own answer.

In v3.json, the visuals stage's common text (`prompt`):
- one sentence is added after "It answers with one item … and that nothing is needed.": the group, how it is shown and recorded;
- "Never show two items, … the server refuses a reply to any item but the one it handed out." becomes "Never show two items unless the
  server handed them out as a group, … any item but what it handed out." (the replaced words are in server/retired-sentences.json).
Registered in scripts/c1_split_v3.py after rel1c. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/rel2b_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

ONE = 'It answers with one item (where it is, the question, what to show, the buttons) or with what is being made and that nothing is needed.'   # design/188
GROUP = (' When several still end-frames of drawn graphics, or several layout drawings of AI video shots, are ready together, it answers with a `group` of up to four '
         'instead: show their pictures side by side in one message, ask one question for each in one call of the question tool, and record each reply with its own '
         '`vw visuals decide`.')
NEVER = ('Never show two items, never choose the order, never answer for the operator, never accept several at once: the server refuses a reply to any item but the one '
         'it handed out.')   # design/188
NEVER_NEW = ('Never show two items unless the server handed them out as a group, never choose the order, never answer for the operator, never accept several at once: '
             'the server refuses a reply to any item but what it handed out.')

RETIRED = ['Never show two items, never choose the order', 'the server refuses a reply to any item but the one it handed out']


def apply(prompt, parts):
    """The visuals text with these sentences: the common part is returned, the parts are untouched. Applying twice changes nothing."""
    for old, new in ((ONE, ONE + GROUP), (NEVER, NEVER_NEW)):
        if new in prompt:
            continue
        if prompt.count(old) != 1:
            sys.exit('not applied: not found once: %s' % old[:60])
        prompt = prompt.replace(old, new)
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    st['prompt'] = st['prompt'].replace(NEVER_NEW, NEVER).replace(GROUP, '')
    return st


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    rp = ROOT / 'server' / 'retired-sentences.json'
    raw = rp.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    print('visuals: several end-frames or layout drawings ready together come as a group, one question for each')


if __name__ == '__main__':
    main()
