"""design/124 Phase A2, groups 1, 2, 3 and 5: out-of-date wording corrected in instruction version 3 only (version 2 untouched)."""
import json

P = r'C:/Coworkspace/Review Videobuilder Tool/videowizard-v2/server/procedures/v3.json'
FIXES = [
    # group 2: five routes, the drawn one named where the others are; moving parts exist in the drawn route
    ("Four routes make a picture, all inside this pipeline:",
     "Five routes make a picture, all inside this pipeline:"),
    ("This is how a diagram, chart or illustration moves. Arrows that travel and parts that slide are not available in this release; plan a build or a reveal instead.\n- AI video:",
     "This is how a diagram, chart or illustration builds. In an AI graphic sequence, arrows that travel and parts that slide are not available; plan a build or a reveal, or use a drawn diagram.\n"
     "- A drawn diagram: for what must be exact (sizes, counts, a sequence of courses, a comparison of measured things), the server draws an SVG scene the plan writes, "
     "with the approved pictures placed in it and its parts appearing, building, moving along a path, highlighting or fading on the narration; rendered free (`vw visuals draw`).\n- AI video:"),
    # group 5: the pointer
    ("a longer passage is several segments (section 5)", "a longer passage is several segments (section 6)"),
    # group 1: a start image per video; an end image only where the final state must be exact
    ("the images it needs (segments plus one for video, counted within one continuous shot only: a cut starts a new pair)",
     "the images it needs (one start image per video segment, plus an end image only where the final state must be exact)"),
    ("the images it needs (segments plus one for video)",
     "the images it needs (one start image per video segment, plus an end image only where the final state must be exact)"),
    ("the end image of one segment is the start image of the next only within one continuous shot, same place and framing; a cut starts a new pair, so three segments of one shot need four images.",
     "where a segment has an end image, it is the start image of the next only within one continuous shot, same place and framing; a cut starts afresh with its own start image."),
    ("Prepare the take with both images, the motion prompt",
     "Prepare the take with its start image (and its end image where the shot has one), the motion prompt"),
    # group 3: the promise that never came
    ("Missing claims, style, spec approval or answer forms are warned in this release and refused from the next.",
     "Missing claims, style, spec approval or answer forms are warned."),
]

d = json.load(open(P, encoding='utf-8'))
st = next(s for s in d['stages'] if s['name'] == 'visuals')
parts = [st['prompt']] + list(st['steps'])
for old, new in FIXES:
    n = sum(p.count(old) for p in parts)
    assert n == 1, (n, old[:60])
    parts = [p.replace(old, new) for p in parts]
st['prompt'], st['steps'] = parts[0], parts[1:]
d['note'] += ' Phase A2: out-of-date wording corrected (five routes; a start image per video, an end only where exact; no "next release" promise; a section pointer).'
open(P, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
t = '\n'.join(parts)
print('left:', [k for k in ('Four routes', 'segments plus one', 'four images', 'both images', 'next release', 'from the next', 'section 5)') if k in t])
