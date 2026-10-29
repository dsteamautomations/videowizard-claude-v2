"""design/124 Phase B: the independent check's problems P1-P9 and P12 corrected in version 3 (after b_wording_v3.py and b_wording_v3_pass2.py)."""
import json

P = 'server/procedures/v3.json'
FIXES = [
    # P1: the end_state warning was removed with the approved dead-weight fix
    ("(`end_state_exact: true`; the check warns when a shot with a change list is left start-only, so it is a choice)",
     "(`end_state_exact: true`; start-only is the default, with no warning)"),
    # P2 + P3: the conditions of each warning, and what evidence is
    ("Per shot (warned when missing): `claims` and `descriptors`, never shown as their opposite; `evidence`; `claim`, visible (footage first; warned on a graphic) or invisible;",
     "Per shot: `claims` and `descriptors`, never shown as their opposite (warned when missing on a shot with narration); `evidence` when it carries a claim (a test, a table, or the result in a scene, never an unrelated picture; warned when missing); `claim`, visible (footage first; warned on a graphic) or invisible;"),
    ("`fact_ids` into `visual_facts` (how a material, process or setting really looks and is done; source and status: confirmed, observed, unknown);",
     "`fact_ids` into `visual_facts` (how a material, process or setting really looks and is done; source and status: confirmed, observed, unknown; warned when missing on a shot of a material or process);"),
    ("Every person, object, animal and material has its real `size` (client material, `measure` on footage frames, a maker's sheet; else unknown, never invented; warned when missing);",
     "Every person, object and animal has its real `size` (client material, `measure` on footage frames, a maker's sheet; else unknown, never invented; warned when missing), a material its sizes in its `material_spec`;"),
    # P4: what the ambient line is
    ("A scene with a video shot has its ambient line (warned without), from the setting and the neighbouring footage, or 'still';",
     "A scene with a video shot has its ambient line: one line on what moves around the action (leaves in the breeze, dust or smoke in the air, people at work behind), from the setting and the neighbouring footage, or 'still' (warned without; the server writes it into every take and the take check asks for it);"),
    # P5: what a light line holds, and the measured check
    ("every scene its `light` once (warned without) and its air",
     "every scene its `light` once (the sources against the landmarks, the main one, hard or soft, colour, strength; warned without; the check measures each picture's light and colour against the footage beside it and marks a large jump) and its air"),
    # P6: the rest of the before-proposing review
    ("identity against the references, and continuity with the neighbours and across shots.",
     "identity against the references, continuity with the neighbours and across shots, every shot's route and length against its generator, every sequence's states, and exact placement timing."),
    # P7: the treatment approves a clean place
    ("unless approved clean (a show home at handover, a new empty room, a showroom), the reason in `staged_clean`.",
     "unless the treatment approves it clean (a show home at handover, a new empty room, a showroom), the reason in `staged_clean`."),
    # P8: two refusals the text lost
    ("a held tool without `props`;",
     "a held tool without `props`; an object count that changes without its `changes` entry; a carriable thing in `fixed`;"),
    # P9: the approved dead-weight fix: the treatment's activity_level is no longer asked (the plan's scenes keep theirs)
    ("`activity_level` (quiet, normal or busy); `frozen_seconds` held still (usually 0);",
     "`frozen_seconds` held still (usually 0);"),
    # P12: small losses
    ("picks are approved when saved (reject one only if the file is not the picture ticked)",
     "picks are approved when saved (show them; reject one only if the file is not the picture ticked)"),
    ("at least 4 % of the frame height (titles 6 %), in the answer's exact text (section B).",
     "at least 4 % of the frame height (titles 6 %), readable on a phone, in the answer's exact text (section B)."),
]

d = json.load(open(P, encoding='utf-8'))
st = next(s for s in d['stages'] if s['name'] == 'visuals')
for old, new in FIXES:
    assert st['prompt'].count(old) == 1, old[:70]
    st['prompt'] = st['prompt'].replace(old, new)
open(P, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
print('applied', len(FIXES))
