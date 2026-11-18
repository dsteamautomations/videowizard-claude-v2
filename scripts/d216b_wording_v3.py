"""design/216b (18 Nov 2026): instruction version 3, the visuals stage: Claude names the things shown in each place.

One sentence in the picture-search part, after the fields of a proposal row: for a place, `things` (the ids of the film's objects and
materials that are fixed parts of it or always stand in it, never a tool or a prop that only passes through a shot, never a person; []
when none) and `things_reason`; and `vw visuals round --things` when the server asks for a place's list later. No sentence is retired:
the older way (the things a place's shots share, guessed by the server) was never in the instruction text. Registered in
scripts/c1_split_v3.py after design/216's script. Exact anchors, each found once; run once: python scripts/d216b_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('picture-search', '`first` on up to three rows of different kinds, the sets made first; and `prompt` only for what the plan does not say.',
     '`first` on up to three rows of different kinds, the sets made first; and `prompt` only for what the plan does not say. For a place, also `things`: the ids of '
     "the film's own objects and materials that are fixed parts of it or always stand in it in the film (a tiled roof's tile, a room's window shutter), most important "
     'first, never a tool or a prop that only passes through a shot and never a person, [] when there are none, and `things_reason`, one plain line: a place is made only '
     'after their sets are approved, with their pictures. When the server asks for a place\'s list later, `vw visuals round --things` shows what to read and takes the file.'),
]


def apply(prompt, parts):
    """The visuals text with this design's sentence: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals: design/216b')


if __name__ == '__main__':
    main()
