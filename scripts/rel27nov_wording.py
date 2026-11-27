"""Release 1 of 27 Nov 2026 (SK approved): the sentences of the served visuals text this release changes.

Part F (the operator's answer to the assistant's own question is followed): the command of a question names `--keeps`, the one choice that
leaves the item as it is; after any other answer the server holds the item until a plan change proposed with `--answers` applies it (the
server's own replies say so; nothing more is written here).
Registered in scripts/c1_split_v3.py after minor_edit. Exact anchors; applying twice changes nothing. Run once: python scripts/rel27nov_wording.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

COMMON = [   # (the words before, the words now) in the common part
    ('--choices "a|b" [--cost <INR>]`;', '--choices "a|b" [--cost <INR>] [--keeps "<the choice that changes nothing>"]`;'),
]


def apply(prompt, parts):
    """The common part with these sentences is returned. Applying twice changes nothing."""
    for old, new in COMMON:
        assert old in prompt or new in prompt, 'not applied: not found: ' + old[:60]
        prompt = prompt.replace(new, old).replace(old, new)
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
