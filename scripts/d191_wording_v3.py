"""design/191 (SK, 13 Nov 2026): instruction version 3, the visuals stage, the plan step: a new plan version that changes only the part every
gap shares is answered by the operator once, for all the gaps whose own shots are unchanged; the server lists what changed.
One exact anchor, found once; run once: python scripts/d191_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

OLD = 'where the card cannot be shown); never `accept --gaps all`.'
NEW = (OLD + ' A plan proposed again keeps every acceptance it did not touch. When the new version changes only the part every gap shares (the foundation, the sequence rules), '
       'the server asks the operator ONE question for all the gaps whose own shots are unchanged, and lists what changed; a gap whose own shots changed is asked by itself, with what changed. '
       'Never ask those gaps one by one, never say yourself what changed or that a gap is unchanged: show what the server hands out. Change the foundation or a sequence rule only when the '
       'change asked for needs it, and say so before you propose.')


def apply(prompt, parts):
    """For c1_split_v3.py --check (applied after design/190's)."""
    part = next(p for p in parts if p['name'] == 'plan')
    if NEW not in part['text']:
        if part['text'].count(OLD) != 1:
            sys.exit(f'not applied: plan: not found once: {OLD[:60]}')
        part['text'] = part['text'].replace(OLD, NEW)
    return prompt


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals instructions: the plan part says the shared change is asked once')


if __name__ == '__main__':
    main()
