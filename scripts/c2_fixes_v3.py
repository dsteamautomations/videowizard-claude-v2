"""design/124 C2 trial, after c1_part_refs.py: the wording of the seven problems the trial found (SK, 29 Oct 2026: "Yes, fix all seven").
Each old text occurs once in its part; c1_split_v3.py --check applies these after c1_part_refs' FIXES."""
import json

P = 'server/procedures/v3.json'
FIXES = {  # where -> [(old, new)]
    'common': [  # 1. the routes' code words
        ("Five routes make a picture, all inside this pipeline:",
         "Five routes make a picture, all inside this pipeline, each with its code word; the treatment's `routes` and `shots[].route` use these words:"),
        ("- Footage: a moving stretch", "- Footage (`footage`): a moving stretch"),
        ("- An AI still: a picture", "- An AI still (`still`): a picture"),
        ("- An AI graphic sequence: two", "- An AI graphic sequence (`graphic_sequence`): two"),
        ("- A drawn diagram: for what", "- A drawn diagram (`drawn`): for what"),
        ("- AI video: a take", "- AI video (`video`): a take")],
    'treatment': [  # 3. images is a count
        ("`images` (one start image per video segment, an end image only where the final state must be exact)",
         "`images`, a whole number for the gap (a count, never a list: one start image per video segment, plus an end image only where the final state must be exact)")],
    'plan': [
        # 2. beats and states
        ("an acting one ordered timed beats (start and end, target, path, contact, visible result).",
         "an acting one ordered timed beats (start and end, target, path, contact, visible result). Its first beat starts exactly in the subject's `start` state and its last "
         "beat ends exactly in its `end` state, field for field (position, facing, pose, holding, progress, objects, gaze), and each beat starts in the previous beat's end "
         "(refused otherwise, naming the shot, the subject, the beat and the fields that differ)."),
        # 4. a material spec without proportions is refused
        ("a spec of a real object its proportions (a brick about 3 : 1.5 : 1; warned without)",
         "a spec of a real object its proportions (a brick about 3 : 1.5 : 1; a drawing spec is warned without them, a material spec refused)"),
        # 5. footage carries no information_progression
        ("not those for generated pictures (the 10 s limit among them)", "not those for generated pictures (the 10 s limit and `information_progression` among them)"),
        # 6. a drawn shot is named at plan time; research waits for the approval
        ("an unchanging one is a diagram shot, one still.",
         "an unchanging one is a diagram shot, one still. A drawn shot is named at plan time by `visual_type: drawn` alone (no `scene_svg` yet); its scene is drawn, "
         "uploaded and named after the picture search (section 9, in part-later.md)."),
        ("Refused: an `unknown` size without all four sources in `tried`, an unknown with a value, `illustrative: true` when nothing is unknown or missing when something is, "
         "an illustrative drawing not labelled \"illustrative, not to scale\" (no numbers, no free proportions);",
         "Refused: an unknown with a value, an illustrative drawing not labelled \"illustrative, not to scale\" (no numbers, no free proportions). A size may still wait for "
         "its research (paid measures and web figures come after the picture search): an `unknown` size without all four sources in `tried`, and `illustrative: true` when "
         "nothing is unknown or missing when something is, are warned in the plan (`spec_unresearched`) and refused when the spec is approved;"),
        # 7. light; a technique's identity
        ("every scene its `light` once (", "every scene its `light` once (a scene of graphics only (diagrams, sequences, drawn) has none; "),
        ("all in the reference round;",
         "all in the reference round; a technique is `identity: representative` (the trade's usual way) unless its fact or size cites the footage (the client's own "
         "technique, as filmed): then `identity: exact` with an approved footage frame, like any thing the footage shows;")],
    'later': [  # 6. the scene comes after the picture search
        ("`visual_type: drawn` with `scene_svg`; the scene is one SVG file (data, never code), uploaded first with `vw visuals scene --shot S --file scene.svg` and named in "
         "the plan by the sha256 the upload returns,",
         "`visual_type: drawn`, named so in the plan; its `scene_svg` comes after the picture search, once the pictures it places are approved and its spec's sizes are "
         "researched: the scene is one SVG file (data, never code), uploaded then with `vw visuals scene --shot S --file scene.svg` (checked against the rules below on "
         "upload, refused with the reasons) and named in the plan by the sha256 the upload returns (a revision; the gap stays accepted),"),
        ("`vw visuals draw --shot S` renders it free:",
         "`vw visuals draw --shot S` (refused while the shot has no uploaded scene or its drawing spec is not approved) renders it free:")],
}


def apply(prompt, parts):
    """The fixes on the common part and the parts (dicts with name and text), in place; each old text occurs once."""
    for where, pairs in FIXES.items():
        for old, new in pairs:
            if where == 'common':
                assert prompt.count(old) == 1, old
                prompt = prompt.replace(old, new)
            else:
                part = next(p for p in parts if p['name'] == where)
                assert part['text'].count(old) == 1, old
                part['text'] = part['text'].replace(old, new)
    return prompt


if __name__ == '__main__':   # importing it (c1_split_v3.py --check) only reads FIXES
    d = json.load(open(P, encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    open(P, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    print('ok')
