"""design/148 A2 + A3 (SK, 3 Nov 2026): one sentence added to the visuals plan part: the join names the new things still to complete; a helper's file is
the proof it finished when its report does not arrive (never relaunch one whose file exists); the check lists every item's first failure together.
Applied after design/139's in c1_split_v3.py --check; writes v3.json when run alone."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

OLD = "a missing or doubled gap is refused). `vw visuals check --file out/visual-plan.json` until valid"
NEW = ("a missing or doubled gap is refused; it names the new things still to complete). When a helper's report does not arrive, its file under out/plan-gaps/ "
       "(read by its full path) is the proof it finished: never relaunch a helper whose file exists. `vw visuals check --file out/visual-plan.json` until valid "
       "(it lists every item's first failure together)")


def apply_visuals(parts):
    part = next(p for p in parts if p['name'] == 'plan')
    assert part['text'].count(OLD) == 1, 'design/148: the plan sentence is not where it was'
    part['text'] = part['text'].replace(OLD, NEW)


if __name__ == '__main__':
    d = json.loads(P.read_text(encoding='utf-8'))
    apply_visuals(next(s for s in d['stages'] if s['name'] == 'visuals')['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('design/148: one sentence added to the plan part')
