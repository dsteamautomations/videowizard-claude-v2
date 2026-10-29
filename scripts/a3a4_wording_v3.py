"""design/124 Phases A3 and A4: the copies that disagree made to agree, and SK's A4 answers, in instruction version 3 only (version 2 untouched).

Each pair is (item, old, new); every old text must occur exactly once in the visuals stage (prompt + steps).
"""
import json

P = r'C:/Coworkspace/Review Videobuilder Tool/videowizard-v2/server/procedures/v3.json'
FIXES = [
    # A3 item 1: labels go through exact_text (guide and step)
    ("A3-1 guide",
     "Put every label, number and caption in the prompt exactly as it must read, keep labels short, and check each one on the candidate before approval;",
     "Put every label, number and caption in the answer's `exact_text` (text, place, size), keep labels short; the server writes it into the prompt; check each one on the candidate before approval;"),
    ("A3-1 step",
     "For a diagram, chart or labelled picture write every label and number in the prompt exactly and check each on the candidate before asking for approval.",
     "For a diagram, chart or labelled picture put every label and number in the answer's `exact_text` (text, place, size); the server writes it into the prompt; check each on the candidate before asking for approval."),
    # A3 item 2: words alone do not decide the route; a figure takes the drawn route
    ("A3-2 guide",
     "Text is not a reason to choose or avoid a route: current image models write accurate text.",
     "Words alone do not decide the route (image models write words accurately); any figure (a number, size or count) in a graphic's claims or spec takes the drawn route, so charts and measured diagrams are drawn."),
    ("A3-2 step",
     "A graphic with measurements, quantities, sequences or labels that must be exact takes the drawn route:",
     "A graphic with measurements, quantities or sequences that must be exact (any figure in its claims or spec: a number, size or count; words alone do not decide the route) takes the drawn route:"),
    # A3 item 3: no whole end; one region or start-only
    ("A3-3 step",
     "the server masks it and copies the start back outside it; an end where several things change, or the framing, is made whole as before.",
     "the server masks it and copies the start back outside it."),
    # A3 items 3 and 9 (decision 9) in the guide's section 6
    ("A3-3 + A3-9 guide §6",
     "and only then gets an end image: generate it from the start image as its parent (`--kind keyframe --parents <start>`) with a prompt that names only the change, the same people, props, place and light, one small action further on, framed so that what the motion heads for is already in view in both. Approve the pair together.",
     "and only then gets an end image: write its request with the start (`end_prompt`, `end_answer`, `end_region`) with a prompt that names only the change, the same people, props, place and light, one small action further on, framed so that what the motion heads for is already in view in both; the server makes the end from the start once the operator approves the start, and the operator approves the end beside its start. An end image is an edit inside one region of its start (a third of the frame at most); if several places or the framing change, make the shot start-only."),
    # A3 item 4: background subjects with beats are elements; a passer-by lives in words
    ("A3-4 guide §4",
     "Plan beats for every visible person, animal or object that acts, including secondary and background subjects; a still subject holds",
     "Plan beats for every visible person, animal or object that acts, including secondary and background subjects (a background subject with beats is an element; a passer-by without beats lives only in the scene's words, its ambient line); a still subject holds"),
    ("A3-4 guide §5",
     "Derive the named elements from the planned shots, secondary subjects and props included;",
     "Derive the named elements from the planned shots, secondary subjects, background subjects with beats (no reference sheet unless it has a source picture) and props included;"),
    ("A3-4 step",
     "A background person who only passes is never a named element with a sheet: the scene says them in words, different in every scene.",
     "A background subject with beats is an element (no reference sheet unless it has a source picture); a passer-by without beats lives only in the scene's words (its ambient line), different in every scene."),
    # A3 decision 5 (a person's sheet from words) and item 7 (what shots bind), guide §5
    ("A3-5 guide §5 (sources)",
     "Every person, object or place gets one generated reference sheet from its footage frames, else from the operator's picks, its notes applied",
     "Every object or place gets one generated reference sheet from its approved footage frames and the operator's picks, its notes applied"),
    ("A3-5 + A3-7 guide §5 (person, bind)",
     "the sheet, not the frames or the picks, is what shots bind. A person from the footage or the web is never a parent for an edit nor copied: the sheet shows",
     "a person's sheet is made from words: look at their footage pictures and describe them (build, age, posture, garments and how they are worn, hair), and the sheet is made from that description. The golden picture (a person: the sheet), not the frames or the picks, is what shots bind. A footage or web picture of a person is never sent to the picture AI, as a parent or otherwise, nor copied: the sheet shows"),
    # decision 5 in the step
    ("A3-5 step (round sheets)",
     "(`image --kind sheet --parents F1,W2`, the notes added by the server under their pictures) and tell the operator",
     "(`image --kind sheet --parents F1,W2`, the notes added by the server under their pictures; a person's sheet from your description of them, with no picture parents) and tell the operator"),
    ("A3-5 + A3-7 step (sheet per element)",
     "Then one sheet per person, object or place: `image --element E --kind sheet --parents F1,W2` from its frames and picks, the notes added by the server under their pictures, a person as posture, dress, build and features only (a frame or a pick of a person is never a parent for an edit); the sheet is what shots bind.",
     "Then one sheet per object or place: `image --element E --kind sheet --parents F1,W2` from its frames and picks, the notes added by the server under their pictures; a person's sheet from your words only (build, age, posture, garments and how they are worn, hair, described from their footage pictures; a footage or web picture of a person is never sent to the picture AI); the golden picture (a person: the sheet) is what shots bind."),
    ("A3-5 step (sheet_due)",
     "write it at once with every source as a parent;",
     "write it at once with every source as a parent (a person: from your description, no picture parents);"),
    # A3 item 6: the client's object: frame before the golden picture, then the golden picture
    ("A3-6 guide §5",
     "a shot that shows it sends one of those frames as a parent, never words alone;",
     "before its golden picture exists, a picture of it sends one of those frames as a parent, never words alone; afterwards the golden picture carries it;"),
    ("A3-6 step (texture bind)",
     "When a shot shows a client material at medium or closer, bind its footage frame as the texture reference;",
     "When a shot shows a client material at medium or closer, bind its footage frame as the texture reference of the video (the video bind only; its pictures carry it through the golden picture);"),
    # A3 items 7 and 18: Image 1 and the input limit
    ("A3-7 + A3-18 step",
     "Up to sixteen pictures go in with a prompt (the model's limit), in this order: the picture edited or the scene parent, one identity sheet per person in frame, then every approved frame, golden picture or supplied reference",
     "Up to the image model's limit of pictures go in with a prompt (16 for GPT Image, 14 for Gemini, by kind; the server names the excess), in this order: Image 1 the golden picture of the element the picture is for (an end image: its start; else the picture edited or the scene parent), then one identity sheet per person in frame, then every other approved frame, golden picture or supplied reference"),
    # A3 item 18: the run's image model, not a fixed name
    ("A3-18 guide §1",
     "a picture generated with GPT Image 2.5 (`vw visuals image`;",
     "a picture generated with the run's image model (`vw visuals image`;"),
    ("A3-18 step",
     "paid OpenAI GPT Image 2.5; inform, do not ask;",
     "paid, the run's image model; inform, do not ask;"),
    # A3 item 8: the style sheet parents a graphic's first picture
    ("A3-8 guide §2",
     "approved, a parent of every graphic.",
     "approved, a parent of every graphic's first (or only) picture; later states inherit it through the chain."),
    ("A3-8 step",
     "approve it and name it in every graphic's --parents;",
     "approve it and name it in the --parents of every graphic's first (or only) picture (later states inherit it through the chain);"),
    # A3 item 9 (decision 9): the server makes the end after the start is approved
    ("A3-9 guide §5",
     "Post a start's end prompt with it (`end_answer`): the server makes the end from the approved start and checks every picture first.",
     "Post a start's end request with it (`end_prompt`, `end_answer`, `end_region`): the server makes the end from the start once the operator approves the start, and checks every picture first; no end is made from a start not yet approved."),
    ("A3-9 step (end image)",
     'The end image of a video shot: `image --element E --kind keyframe --parents <start keyframe> --prompt "<only what changes>"`, as soon as the start candidate exists; show the pair together and approve both.',
     "The end image of a video shot: write its request with the start (`end_prompt`, `end_answer`, `end_region`; the prompt names only what changes); the server makes it from the start once the operator approves the start; show the end beside its start for approval."),
    ("A3-9 step (wave)",
     "write the next shot's answers (and its end image from the start candidate at once: one approval wave per shot) instead of waiting",
     "write the next shot's answers (each start with its end request: one approval wave per shot) instead of waiting"),
    ("A3-9 step (video shots)",
     "then the start image, then the end image from the start candidate at once, the pair shown together; never a start image before the packet",
     "then the start image with its end request (`end_prompt`), the server making the end once the start is approved, the end shown beside its start; never a start image before the packet"),
    # A3 item 10: footage, the operator's own file, Google on their yes, AI
    ("A3-10 guide §5",
     "- A picture from the web: the round's searches, or `vw visuals search`; their own file with `supply`.",
     "- The operator's own file (`supply`); then, for what the footage lacks, a picture from the web on their yes: the round's searches, or `vw visuals search`."),
    # A3 item 11: one warning and one yes for every web figure of the run
    ("A3-11 step (A)",
     "a standard or a manufacturer's sheet on the web, on the operator's yes, with its URL and figure;",
     "a standard or a manufacturer's sheet on the web, with its URL and figure;"),
    ("A3-11 step (B)",
     "(one warning and yes covers every spec of the run)",
     "(one warning and one yes covers every web figure of the run)"),
    ("A3-11 guide §0 (C)",
     "a fact that can be measured or sourced, the next step",
     "a fact that can be measured or sourced (except the run's one yes for web figures), the next step"),
    # A3 item 12: one table for the run; per shot only for a single late spec
    ("A3-12 step",
     'Show the operator the spec as a table and record their words: `vw visuals spec --shot S --quote "…"` (or on the page).',
     'The operator approves every spec of the run in one table (below); a single late spec alone: `vw visuals spec --shot S --quote "…"` (or on the page).'),
    # A3 item 13: the cap (stays until design/122); only the builder changes it
    ("A3-13 guide §6",
     "The film has a cap, ₹5,000 unless the operator sets another; the server refuses a paid call that would pass it, with the spend so far: stop and tell the operator; the builder changes the cap on SK's word.",
     "The film has a cap of ₹5,000; only the builder changes it, on SK's word; the server refuses a paid call that would pass it, with the spend so far: stop and tell the operator."),
    # A3 item 14: acceptance belongs to the plan step
    ("A3-14 guide §8",
     'Accept gaps with `vw visuals accept --gaps all --quote "…"` (or the gaps the operator named) and record them when every shot has',
     "Record the gaps when every shot has"),
    # A3 item 15 (A4 answer 1): one change per edit
    ("A3-15 guide §5",
     "One change, two at most, per edit.",
     "One change per edit."),
    # A3 item 16: a plain reuse with the operator's words
    ("A3-16 guide §4",
     "The film never shows one picture twice: a return is reimagined (`return_of`, `differs_by`).",
     "The film never shows one picture twice: a return is reimagined (`return_of`, `differs_by`); a plain reuse only with the operator's words (`--reuse`, the plan step)."),
    # A3 item 17 and A4 answer 5: Gemini Omni only, 3 to 10 s; a longer passage split
    ("A3-17 + A4-5 guide §1",
     "Gemini Omni is the default generator and makes 3 to 10 seconds; a longer passage is several segments (section 6). Kling (3–15 s) and Seedance (4–30 s) are chosen per shot with `vw visuals generator` only when one action cannot be cut. A shot longer than its generator's maximum is refused at preparation.",
     "Gemini Omni is the generator and makes 3 to 10 seconds; a longer passage is several segments (section 6), split where an action begins or ends. A video shot longer than 10 seconds is refused: split it."),
    ("A3-17 + A4-5 step",
     "Video shots: `generator --shot S --provider … --model …` only when the shot is longer than the default makes (the check warns); `prepare-take",
     "Video shots: every take is Gemini Omni, 3 to 10 s; a longer passage is split into shots, cut where an action begins or ends; `prepare-take"),
    # A3 item 19: a graphic pushes in by default
    ("A3-19 guide §1",
     "with a short dissolve between them and, when the shot asks for it, a slow push.",
     "with a short dissolve between them and a slow push-in (motion none only with a reason)."),
    # A3 decision 20 with design/124 Change 4: only a gap that opens the film
    ("A3-20 + Change 4 step",
     "The first gap opens on the strongest picture of the film's subject, not a neutral establishing shot.",
     "The gap that opens the film (if one does) opens on the subject at work, framed wide enough to see where it is (the mason laying bricks on the half-built wall, with the site around), never an empty view of the place; a close-up comes after the subject has been seen wider."),
    # A3 item 21: a build of states or a drawn animation
    ("A3-21 guide §4",
     "a graphic over 4 s is a build.",
     "a graphic over 4 s is a build of 2 to 4 states or a drawn animation."),
    ("A3-21 step",
     "a graphic over 4 s is a build of 2 to 4 states.",
     "a graphic over 4 s is a build of 2 to 4 states or a drawn animation."),
    # A3 item 22: approval places the still
    ("A3-22 guide §1",
     "approved by the operator and held for the shot (`vw visuals still`).",
     "approved by the operator for its shot, which places it."),
    # A3 item 23: the scene's light word for word; the server adds the real-light line
    ("A3-23 guide §4",
     "state that light in the prompt (soft overcast light, muted greens).",
     "name the scene's light (its `light` field) word for word in the prompt (soft overcast light, muted greens); the server adds the measured real-light line under it."),
    # A3 item 24: one list once; later forks one question through ask
    ("A3-24 guide §0",
     "Missing facts are asked once, as one list, before the first picture.",
     "Missing facts: one list, once, before the first picture; any later fork: one question through `vw visuals ask`."),
    ("A3-24 guide §4",
     "recorded as a specific question in open_questions when",
     "recorded as a specific question in open_questions (and raised with `vw visuals ask`) when"),
    # A3 item 25: shot length with the AI video bounds
    ("A3-25 guide §4",
     "Shots run two to eight seconds as a rule.",
     "Shots run two to eight seconds as a rule (AI video at least 3 s and at most 10 s, 3–5 s inside an AI run)."),
    # A4 answer 2: steady videos, no guidance toward handheld movement
    ("A4-2 step (camera_reason)",
     "a slow push draws in, handheld feels raw; no angle has one fixed meaning",
     "a slow push draws in; no angle has one fixed meaning"),
]

if __name__ == '__main__':
    d = json.load(open(P, encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    parts = [st['prompt']] + list(st['steps'])
    for item, old, new in FIXES:
        n = sum(p.count(old) for p in parts)
        assert n == 1, (item, n, old[:60])
        parts = [p.replace(old, new) for p in parts]
    st['prompt'], st['steps'] = parts[0], parts[1:]
    d['note'] += (' Phases A3 and A4: the copies that disagreed made to agree (design/124-a3-disagreements.md, items 1-25 as resolved;'
                  ' one change per edit; a person\'s sheet from words; the end made by the server after the start is approved;'
                  ' the film-opening gap opens on the subject at work, framed wide); Gemini Omni only; steady takes.')
    open(P, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    t = '\n'.join(parts)
    print('left:', [k for k in ('Kling', 'Seedance', 'generator --shot', 'two at most', 'start candidate', 'made whole',
                                'handheld', 'GPT Image 2.5', 'sixteen', 'unless the operator sets') if k in t])
