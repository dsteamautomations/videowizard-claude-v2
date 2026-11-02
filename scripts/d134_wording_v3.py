"""design/134 (the Codex process review, SK 2 Nov 2026): instruction version 3, findings 9 and 10, one exact replacement each; every new text
is shorter. The old wording goes on RETIRED (server/retired-sentences.json), which a test keeps out of v3.json for good.
Run once: python scripts/d134_wording_v3.py. c1_split_v3.py --check applies apply()."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

COMMON = [
    ('10a', "Words alone do not decide the route (image models write words accurately); any figure (a number, size or count) in a graphic's claims or spec takes the drawn route, so charts and measured diagrams are drawn.",
     "A labelled diagram is drawn (HyperFrames on a motion film); on a `--drawn svg` film any number, size or count in a graphic's claims or spec takes the drawn route."),
    ('10b', '- A drawn diagram (`drawn`): for what must be exact (sizes, counts, a sequence of courses, a comparison of measured things), the server draws an SVG scene the plan writes, with the approved pictures placed in it and its parts appearing, building, moving along a path, highlighting or fading on the narration; rendered free (`vw visuals draw`).',
     '- A drawn diagram (`drawn`): anything exact or labelled; drawn with HyperFrames by default (section 11, in part-later.md), with `vw visuals draw` only on a `--drawn svg` film; rendered free.'),
    ('10c', "a photograph-like scene, an illustration, or a diagram or labelled picture without figures (a chart, or anything carrying a number, size or count, is drawn), approved",
     "a photograph-like scene or an illustration (a labelled diagram, a chart or anything carrying a number is drawn), approved"),
]
PARTS = [
    ('later', '9a', "Post a start's end request with it (`end_prompt`, `end_answer`, `end_region`): the server makes the end from the start once the operator approves the start, and checks every picture first; no end is made from a start not yet approved. ",
     ''),
    ('later', '9b', 'then the start image with its end request (`end_prompt`), the server making the end once the start is approved, the end shown beside its start;',
     'then the start image, with an end request only when `end_state_exact` is true;'),
]


def apply(prompt, parts):
    """For c1_split_v3.py --check (applied last)."""
    for change, old, new in COMMON:
        assert prompt.count(old) == 1, (change, old[:60])
        prompt = prompt.replace(old, new)
    for name, change, old, new in PARTS:
        part = next(p for p in parts if p['name'] == name)
        assert part['text'].count(old) == 1, (change, old[:60])
        part['text'] = part['text'].replace(old, new)
    return prompt


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    try:
        st['prompt'] = apply(st['prompt'], st['parts'])
    except AssertionError as exc:
        sys.exit(f'not applied: {exc}')
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    for change, old, new in COMMON + [(c, o, n) for _, c, o, n in PARTS]:
        print(change, len(old.split()), '->', len(new.split()), 'words')


if __name__ == '__main__':
    main()
