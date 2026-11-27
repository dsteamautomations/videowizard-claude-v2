"""Release 1 of 27 Nov 2026 (SK approved): the sentences of the served visuals text this release changes.

Part F (the operator's answer to the assistant's own question is followed): the command of a question names `--keeps`, the one choice that
leaves the item as it is; after any other answer the server holds the item until a plan change proposed with `--answers` applies it (the
server's own replies say so; nothing more is written here).
Part H (every card names its shot by its voiceover words): one sentence for the assistant's own chat text (+18 words).
Phase 2, part B (signs of use only where the shot's words ask): three sentences of the plan part; the parts are changed in place.
Registered in scripts/c1_split_v3.py after minor_edit. Exact anchors; applying twice changes nothing. Run once: python scripts/rel27nov_wording.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

COMMON = [   # (the words before, the words now) in the common part
    ('--choices "a|b" [--cost <INR>]`;', '--choices "a|b" [--cost <INR>] [--keeps "<the choice that changes nothing>"]`;'),
    # part H (every card names its shot by its voiceover; the server cannot see the assistant's own chat text, so the instruction says it)
    ('is accepted with that answer, with no second card.',
     'is accepted with that answer, with no second card. In your own chat text, name a shot by its words and its voiceover, never by its code alone.'),
]


PARTS = [   # (the part, the words before, the words now); phase 2 part B: the server adds no signs of use; a shot's own words say what it shows
    ('plan', 'a place shown has two `signs_of_use` or `staged_clean`; ', 'a place shown clean has its reason in `staged_clean`; '),
    ('plan', 'a place shown needs `signs_of_use` (two or more, each at one of its landmarks; refused without) unless the treatment approves it clean (a new empty room, a showroom, a product studio), the reason in `staged_clean`.',
     'write them in the shot that should show them: the server adds none. A place the treatment approves clean (a new empty room, a showroom, a product studio) has the reason in `staged_clean`.'),
    ('plan', "(two signs of use per shot, or 'clean and unused, as planned')", "('clean and unused, as planned' for a place staged clean)"),
    # phase 2 part C: a still is ordered only after the references of what it shows are approved
    ('later', 'counts the still shots with no picture asked for yet.', 'names the still shots due: a still waits for its references.'),
    # phase 2 part A has no sentence here: the picture-search paragraph is pinned whole by the design/211 scripts; the server's own words say it (ref_sets.PEOPLE_WAIT, PERMISSION_FIRST)
]


def apply(prompt, parts):
    """The common part with these sentences is returned. Applying twice changes nothing."""
    for old, new in COMMON:
        assert old in prompt or new in prompt, 'not applied: not found: ' + old[:60]
        prompt = prompt.replace(new, old).replace(old, new)
    for where, old, new in PARTS:
        part = next(p for p in parts if p['name'] == where)
        assert old in part['text'] or new in part['text'], 'not applied: %s: not found: %s' % (where, old[:60])
        part['text'] = part['text'].replace(new, old).replace(old, new)
    return prompt


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    for st in d['stages']:
        if st['name'] == 'visuals':
            st['prompt'] = apply(st['prompt'], st.get('parts') or [])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    print('visuals: release 1 of 27 Nov 2026 wording applied')


if __name__ == '__main__':
    main()
