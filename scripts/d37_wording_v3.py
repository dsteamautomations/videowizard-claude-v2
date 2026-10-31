"""Defect 37 (VW-12, 31 Oct 2026): version 3's plan part folded a spec correction in with `planning revise`, retired with the planning
stage (design/125). The correction goes into out/visual-plan.json (`vw visuals plan` brings it) and the plan is proposed again.
Run once: python scripts/d37_wording_v3.py (fails unless the old text is found exactly once). c1_split_v3.py --check applies apply_visuals."""
import json
import sys
from pathlib import Path

V3 = Path(__file__).resolve().parents[1] / 'server' / 'procedures' / 'v3.json'
PAIRS = [('plan',
          'send a correction (`vw visuals spec --shot S --notes "…"`, listed in `spec_corrections`) you fold in with `planning revise` (approval refused while one waits)',
          'send a correction (`vw visuals spec --shot S --notes "…"`, in `spec_corrections`): fold into out/visual-plan.json (`vw visuals plan`), propose again (approval refused until then)')]   # 24 words, as before (the word count never grows)


def apply_visuals(parts):
    for name, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == name)
        assert part['text'].count(old) == 1, (name, old[:60])
        part['text'] = part['text'].replace(old, new)


if __name__ == '__main__':
    d = json.loads(V3.read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    apply_visuals(st['parts'])
    V3.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    for name, old, new in PAIRS:
        print(name, len(old.split()), '->', len(new.split()), 'words')
    sys.exit(0)
