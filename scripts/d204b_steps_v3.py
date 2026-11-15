"""design/204 hotfix (SK, 15 Nov 2026): instruction version 3, the visuals stage, two step lines brought in line with design/202 and 204.
The notes file is written empty and is not read; the treatment is answered on the page. Run once: python scripts/d204b_steps_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [(0, 'read prompt.md, gaps.json and intended-visuals.json;', 'read prompt.md and gaps.json;'),
         (1, "then `vw visuals treatment --accept … --quote …` or `--send-back … --notes …` per line on the operator's words, until every line is accepted.",
          'then `vw visuals page`: the operator answers on a page, recorded on their done (`vw visuals page --record`); the card where it cannot be shown.')]


def apply(steps):
    """The visuals step lines with the two changes. Applying twice changes nothing."""
    for i, old, new in PAIRS:
        if new not in steps[i]:
            if steps[i].count(old) != 1:
                sys.exit('not applied: step %d: not found once: %s' % (i, old[:60]))
            steps[i] = steps[i].replace(old, new)
    return steps


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    apply(st['steps'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals, steps 0 and 1: the notes file not read; the treatment on the page')


if __name__ == '__main__':
    main()
