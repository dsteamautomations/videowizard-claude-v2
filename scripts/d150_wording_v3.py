"""design/150 Set C (SK, 3 Nov 2026): the treatment step's rules the VW-18 refusals and the plan step found missing from the text: C1 the Direction's limit
(2000 characters), C2 `seconds` is one number per gap (the segments carry theirs inside shots), C3 a footage clip or thing is named at one gap only.
Applied after design/149's in c1_split_v3.py --check; writes v3.json when run alone."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

TREATMENT = [
    ('C1', '`direction` comes first (refused without), the central creative choice: a few lines on what the audience should understand or feel by the end,',
     '`direction` comes first (refused without), the central creative choice: a few lines (at most 2000 characters) on what the audience should understand or feel by the end,'),
    ('C2', "`routes`; `seconds` (a video gap's segments with theirs);",
     "`routes`; `seconds`, one number, the gap's total (a video gap's segments carry theirs inside `shots`, never a list in `seconds`);"),
    ('C3', "Treat the team's intended visuals",
     "A footage clip, or a specific thing the footage shows (one building, one machine), is named at one gap only; a second gap that wants it says why in its line, or takes another. "
     "Treat the team's intended visuals"),
]


def apply_visuals(parts):
    part = next(p for p in parts if p['name'] == 'treatment')
    for change, old, new in TREATMENT:
        assert part['text'].count(old) == 1, ('design/150', change)
        part['text'] = part['text'].replace(old, new)


if __name__ == '__main__':
    d = json.loads(P.read_text(encoding='utf-8'))
    apply_visuals(next(s for s in d['stages'] if s['name'] == 'visuals')['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('design/150: three replacements in the treatment part')
