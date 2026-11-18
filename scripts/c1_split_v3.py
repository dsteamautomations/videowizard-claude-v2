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
        assert s_old == s_new or s_new['name'] in ('visuals', 'intake', 'brief', 'script', 'voice', 'media', 'analysis', 'options', 'master', 'first_cut', 'assembly', 'delivery'), s_new['name']   # design/125 changed these in version 3; design/132 the assembly and delivery
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
        from d125_wording_v3 import apply_visuals   # design/125 I1, S3: two sentences in the parts
        apply_visuals(parts)
        from d125_stage7_wording_v3 import apply_visuals as stage7   # design/125 stage 7, O9: the plan's named helper
        stage7(parts)
        from d37_wording_v3 import apply_visuals as d37   # defect 37: the spec correction folded into out/visual-plan.json
        d37(parts)
        from d126_wording_v3 import apply_visuals as d126   # design/126 U5: two to twelve keywords
        d126(parts)
        from d130_wording_v3 import apply_visuals as d130   # design/130: the HyperFrames motion route (section 11)
        d130(parts)
        from d134_wording_v3 import apply as d134   # design/134: the Codex process review, findings 9 and 10
        prompt = d134(prompt, parts)
        from d139_wording_v3 import apply_visuals as d139   # design/139: SK's design/138 answers
        prompt = d139(prompt, parts)
        from d148_wording_v3 import apply_visuals as d148   # design/148 A2, A3: the join's list, the helper's file as proof, the check's full list
        d148(parts)
        from d149_wording_v3 import apply_visuals as d149   # design/149 Set B: the plan step's rules (B1, B2, B4, B5, B6, B7, B9)
        prompt = d149(prompt, parts)
        from d150_wording_v3 import apply_visuals as d150   # design/150 Set C: the treatment's limits and the one-clip rule in the text
        d150(parts)
        from d151_wording_v3 import apply_visuals as d151   # design/151: the kept reference round
        d151(parts)
        from d151b_wording_v3 import apply_visuals as d151b   # design/151 section 13: the set as turns
        d151b(parts)
        from d181_wording_v3 import apply as d181   # design/181, integration step E: an AI video shot is made from a guide; 3 to 15 s; the older take is retired from the text
        prompt = d181(prompt, parts)
        from d188_wording_v3 import apply as d188   # design/188: the operator's decisions in the chat, one at a time
        prompt = d188(prompt, parts)
        from d190_wording_v3 import apply as d190   # design/190: the treatment and the plan on one card
        prompt = d190(prompt, parts)
        from d191_wording_v3 import apply as d191   # design/191: a change of the plan's shared part is asked once
        prompt = d191(prompt, parts)
        from d200_wording_v3 import apply as d200   # design/200: a thing drawn before the round; the shot's drawing before the still; the look reference
        prompt = d200(prompt, parts)
        from d202_wording_v3 import apply as d202   # design/202: the narration alone; action first; each shot's two reasons; words on the picture by category
        prompt = d202(prompt, parts)
        from d203_wording_v3 import apply as d203   # design/203: the Direction in six parts; a second Direction that differs in kind
        prompt = d203(prompt, parts)
        from d204_wording_v3 import apply as d204   # design/204: the treatment answered on a Claude artifact page
        prompt = d204(prompt, parts)
        from d204b_steps_v3 import apply as d204b   # design/204 hotfix: two step lines (the notes file not read; the treatment on the page)
        d204b(steps)
        from d205_wording_v3 import apply as d205, apply_steps as d205s   # design/205: the Direction alone first; the motion style on the page; a still that must be read; beats
        prompt = d205(prompt, parts)
        d205s(steps)
        from d206_wording_v3 import apply as d206, apply_steps as d206s   # design/206: the plan answered on the page in one visit
        prompt = d206(prompt, parts)
        d206s(steps)
        from d207_wording_v3 import apply as d207, apply_steps as d207s   # design/207: the visuals rules after the review (any kind of AI video, the world, likeness, the page, the cost limit by length)
        prompt = d207(prompt, parts)
        d207s(steps)
        from d209_wording_v3 import apply as d209, apply_steps as d209s   # design/209: the drawings and the materials approved on the page, after the plan
        prompt = d209(prompt, parts)
        d209s(steps)
        from d210_wording_v3 import apply as d210   # design/210: the reference drawings approved on the page, with their pictures
        prompt = d210(prompt, parts)
        from d210b_wording_v3 import apply as d210b, apply_steps as d210bs   # design/210 part 2: the reference round answered on the page, in two visits
        prompt = d210b(prompt, parts)
        d210bs(steps)
        from d210c_wording_v3 import apply as d210c   # design/210, the wording review: each step sent to where it is answered; the picture search in the order it is done
        prompt = d210c(prompt, parts)
        from d211a_wording_v3 import apply as d211a   # design/211 part A: the footage pictures found by helpers (the digest, trial frames, looks)
        prompt = d211a(prompt, parts)
        from d211b_wording_v3 import apply as d211b   # design/211 part B: the sets (the proposal, the views, two goes, the looks, the rewrite)
        prompt = d211b(prompt, parts)
        from d211c_wording_v3 import apply as d211c   # design/211 part C: what the operator sees and decides (the proposals, the doubtful first)
        prompt = d211c(prompt, parts)
        from d211d_wording_v3 import apply as d211d, apply_steps as d211ds   # design/211, the review: the step list, the views by kind, the order of authority, what a helper is given, three makes, a second send
        prompt = d211d(prompt, parts)
        d211ds(steps)
        from d212_wording_v3 import apply as d212   # design/212: step 1 of the references in its new layout (five groups, the buttons by case, a person not in the footage not asked, no cost shown)
        prompt = d212(prompt, parts)
        from d213_wording_v3 import apply as d213   # design/213: the references sets screen in the new layout, and the corrections of step 5 (a place one picture, a person the footage shows, the plan against the footage, the notes as two lines, the limit with no amount)
        prompt = d213(prompt, parts)
        from d214_wording_v3 import apply as d214   # design/214: Claude checks the sets of a reference round (each picture's check list answered by the look); no model checks them
        prompt = d214(prompt, parts)
        from d215_wording_v3 import apply as d215   # design/215: the references fix set (three labels for "Leave out", how the making goes, no cost word, one order of authority, the corrections per thing, the search record, the step's new name, the look and an object in use by category)
        prompt = d215(prompt, parts)
        from d216_wording_v3 import apply as d216   # design/216: the page's `say` posted unchanged with the link, and `preparing` said before `vw visuals page --fetch`
        prompt = d216(prompt, parts)
        from d132_wording_v3 import apply_steps as d132   # design/132: the editor's package before the assembly
        later = {s['name']: s for s in old['stages'] if s['name'] in ('assembly', 'delivery')}
        d132(list(later.values()))
        assert all(later[s['name']] == s for s in d['stages'] if s['name'] in later), 'v3.json assembly and delivery are not design/132\'s'
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
