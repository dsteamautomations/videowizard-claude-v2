"""design/210 part 1 (SK, 16 Nov 2026): instruction version 3, the visuals stage. The operator approves a thing's reference drawings on the
page, its sheets as pictures (small on the page, large on a click), after the drawings and the materials; `vw visuals page` also says how the
pictures are sent; the chat, one at a time, only where the page cannot be shown. The same sentence in the plugin's command file.
Exact anchors, each found once; run once: python scripts/d210_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

PAIRS = [   # (where: common or a part's name, the old sentence, the new one)
    ('common', 'Every other decision of this stage is asked here in the chat, one at a time (`vw visuals next`, `vw visuals decide`).',   # design/209's sentence stays whole; one follows it
     "Every other decision of this stage is asked here in the chat, one at a time (`vw visuals next`, `vw visuals decide`). Except a thing's reference drawings: they too are "
     'approved on the page, after the drawings and the materials, their sheets as pictures, small and large on a click (`vw visuals page`, which also sends the pictures as it '
     'says: the small ones, then the large ones, then the round; one visit, then `vw visuals page --record`); in the chat only where the page cannot be shown.'),
    ('picture-search', '`vw visuals next` then shows the operator the labelled sheets with the sources and the assumed sizes, and they answer Yes or Correct it.',
     'The operator approves the reference drawings on the page (`vw visuals page`, which also sends the pictures as it says): the labelled sheets, small and large on a click, with '
     'the sources and the assumed sizes, and they answer Yes or Correct it; in the chat, one at a time (`vw visuals next`), only where the page cannot be shown.'),
]
COMMAND = ('and the operator approves the drawings in the chat;',
           'and the operator approves the drawings on the page (`vw visuals page`, which also sends the pictures as it says; in the chat only where the page cannot be shown);')
RETIRED = ['`vw visuals next` then shows the operator the labelled sheets']


def apply(prompt, parts):
    """The visuals text with design/210's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    raw = R.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    R.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    raw = CMD.read_bytes()
    text, (old, new) = raw.decode('utf-8'), COMMAND
    if new not in text:
        if text.count(old) != 1:
            sys.exit('not applied: plugin/commands/vw.md: not found once: %s' % old)
        CMD.write_bytes(text.replace(old, new).encode('utf-8'))   # bytes: the file keeps its line ends
    print('visuals: design/210, the reference drawings approved on the page, with their pictures')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
