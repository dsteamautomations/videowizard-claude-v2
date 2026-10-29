"""design/124 C1 (Change 2): the visuals text of instruction version 3 split by step (version 2 untouched).

From the Phase B text (git commit BASE): `prompt` = the common part (header, sections A-D) plus a reading guide; `parts` = preparation (1), treatment (2),
plan (3), picture-search (4), later (5-10). The text is moved, not rewritten: common + the parts' texts == the Phase B prompt, asserted. The steps'
pointers name their part file. Run: python scripts/c1_split_v3.py [--check]   (--check: build and compare with v3.json, write nothing)
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / 'server/procedures/v3.json'
BASE = '51b8f95'   # design/124 Phase B: the four reviewed phases tidied
PARTS = [('preparation', 'Preparation', '1. PREPARATION'), ('treatment', 'Treatment', '2. TREATMENT'), ('plan', 'The detailed plan', '3. THE DETAILED PLAN'),
         ('picture-search', 'The picture search', '4. THE PICTURE SEARCH'),
         ('later', 'The later steps (references, sheets and golden pictures; shot pictures and videos; checks; review and record; brand)',
          '5. GENERATED REFERENCES, SHEETS AND GOLDEN PICTURES')]
GUIDE = ('Reading guide: this file is the common part (sections A to D), read once. Each step has its own part in a file beside this one; read it when you '
         'reach that step: part-preparation.md (section 1), part-treatment.md (section 2), part-plan.md (section 3), part-picture-search.md (section 4), '
         'part-later.md (sections 5 to 10).')
STEPS = [('Preparation (prompt.md section 1)', 'Preparation (part-preparation.md)'), ('Treatment (section 2)', 'Treatment (part-treatment.md)'),
         ('The detailed plan (section 3)', 'The detailed plan (part-plan.md)'), ('The picture search (section 4)', 'The picture search (part-picture-search.md)'),
         ('sheets and golden pictures: sections 5 and 9.', 'sheets and golden pictures: part-later.md, sections 5 and 9.'),
         ('Shot pictures and videos: sections 6 and 9', 'Shot pictures and videos: part-later.md, sections 6 and 9'),
         ('Review and record: sections 8 and 9', 'Review and record: part-later.md, sections 8 and 9'), ('Brand: section 10.', 'Brand: part-later.md, section 10.')]
NOTE = (' C1: the visuals text split by step (design/124 Change 2): `prompt` is the common part with a reading guide; `parts` holds preparation, treatment,'
        ' plan, picture-search and the later steps, moved word for word (scripts/c1_split_v3.py).')


def build():
    old = json.loads(subprocess.run(['git', 'show', f'{BASE}:server/procedures/v3.json'], capture_output=True, cwd=ROOT, check=True).stdout.decode('utf-8'))
    st = next(s for s in old['stages'] if s['name'] == 'visuals')
    text = st['prompt']
    cuts = []
    for _, _, head in PARTS:
        assert text.count('\n' + head + '\n') == 1, head
        cuts.append(text.index('\n' + head + '\n') + 1)
    assert cuts == sorted(cuts)
    common = text[:cuts[0]]
    parts = [{'name': n, 'title': t, 'text': text[a:b]} for (n, t, _), a, b in zip(PARTS, cuts, cuts[1:] + [len(text)])]
    assert common + ''.join(p['text'] for p in parts) == text, 'the split lost or changed text'   # word for word
    steps = list(st['steps'])
    assert len(steps) == len(STEPS)
    for i, (a, b) in enumerate(STEPS):
        assert steps[i].count(a) == 1, a
        steps[i] = steps[i].replace(a, b)
    return old, common + GUIDE, parts, steps


if __name__ == '__main__':
    old, prompt, parts, steps = build()
    d = json.loads(V3.read_text(encoding='utf-8'))
    for s_old, s_new in zip(old['stages'], d['stages']):   # every other stage as it was
        assert s_old == s_new or s_new['name'] == 'visuals', s_new['name']
    if '--check' in sys.argv:
        st = next(s for s in d['stages'] if s['name'] == 'visuals')
        sys.path.insert(0, str(ROOT / 'scripts'))
        from c1_part_refs import FIXES   # applied after the split: references naming another part's file
        for where, pairs in FIXES.items():
            for a, b in pairs:
                if where == 'common':
                    prompt = prompt.replace(a, b)
                else:
                    part = next(x for x in parts if x['name'] == where)
                    part['text'] = part['text'].replace(a, b)
        from c2_fixes_v3 import apply   # design/124 C2: the trial's wording fixes, applied after the part references
        prompt = apply(prompt, parts)
        assert (st['prompt'], st['parts'], st['steps']) == (prompt, parts, steps), 'v3.json does not hold the split (with the part references)'
        print('ok: v3.json holds the split (common + parts == the Phase B text, asserted in build) with the part references')
    else:
        st = next(s for s in d['stages'] if s['name'] == 'visuals')
        st['prompt'], st['steps'] = prompt, steps
        st['parts'] = parts
        if NOTE not in d['note']:
            d['note'] += NOTE
        V3.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        print('wrote v3.json:', {p['name']: len(p['text'].split()) for p in parts}, 'common', len(prompt.split()))
