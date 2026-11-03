"""design/149 Set B (SK, 3 Nov 2026): the plan step's rules in instruction version 3, one exact replacement each. B1 the missing facts before the helpers,
asked with choices and reasons; B2 the clean outfit line; B4 a size claim in `claims`; B5 the techniques named at plan-base, a stray verb warned;
B6 a figure the film states is never unknown; B7 the gap files as master; B9 nothing in the frame vanishes; B10 a size proposed from a named standard, confirmed by the operator, never on screen.
Applied after design/148's in c1_split_v3.py --check; writes v3.json when run alone."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

COMMON = [
    ('B1', 'Missing facts: one list, once, before the first picture; any later fork: one question through `vw visuals ask`.',
     "Missing facts: one list, once, after out/plan-base.json and before the helpers plan the gaps; each question through the question tool with the two to four choices "
     "that fit this film, one line each on why (the footage, the brief, the client card, the region), the plan's proposal first; an answer goes into plan-base.json as a "
     "visual fact (status confirmed, source \"the operator: <their words>\"), a \"no preference\" keeps the plan's proposal and stays an open question; any later fork: "
     "one question through `vw visuals ask`."),
]

PLAN = [
    ('B5', "You write the shared parts in out/plan-base.json: foundation, elements, graphic style, sequence_overview, `gaps` (in order). Then helpers",
     "You write the shared parts in out/plan-base.json: foundation, elements (the film's techniques among them, kind technique, named once here from the treatment and "
     "the footage; a beat verb outside them is warned, never refused), graphic style, sequence_overview, `gaps` (in order); then the missing facts (section A), their "
     "answers written into plan-base.json. Then helpers"),
    ('B4', "a claim or descriptor about the subject's own size, amount or scale is refused without a size value and `compare_to` (another element in frame)",
     "a claim in `claims` about the subject's own size, amount or scale is refused without a size value and `compare_to` (another element in frame); a size word in "
     "`descriptors` or a beat describes and is not checked"),
    ('B2', "each scene's `outfit` per person shown; `time_jump` (the script's words) when the colours change.",
     "each scene's `outfit` per person shown (garments and colours only, identical for a person across scenes; a framing note goes in the shot's `focus`, a question in "
     "`open_questions`); `time_jump` (the script's words) when a garment or a colour changes."),
    ('B9', "Two people in one film wear different colour families unless the footage or the brief fixes their clothes (a uniform).",
     "Two people in one film wear different colour families unless the footage or the brief fixes their clothes (a uniform). Nothing in the frame vanishes: everything "
     "in the shot at its start is accounted for at its end, still there at a stated place (a subject's `end`, a prop's end) or gone by a stated action of someone; "
     "anything that moves or is moved is a named subject or prop of the shot, the container that brings a thing included (warned as container_unnamed)."),
    ('B6', 'Refused: an unknown with a value, an illustrative drawing not labelled',
     "Refused: an unknown with a value, a figure the shot's narration or claims state marked unknown (it is confirmed from the script), an illustrative drawing not labelled"),
    ('B10', "Every person, object and animal has its real `size` (client material, `measure` on footage frames, a maker's sheet; else unknown, never invented; warned when missing)",
     "Every person, object and animal has its real `size` (client material, `measure` on footage frames, a maker's sheet; else unknown, never invented; warned when missing; "
     "a generic, standardised thing's size may be proposed from a named standard or maker figure, status `proposed`, source \"recalled: <standard>, to confirm\", put to the "
     "operator in the missing-facts list beside its alternatives and the footage measure, and recorded on their word as confirmed, source \"the operator confirmed <standard>\": "
     "it may shape the drawing, never a number written on screen (that needs the script, the client's document or a web check); a client's own thing is never proposed from recall)"),
    ('B7', 'fix what it names or send the gap back to its helper.',
     'fix what it names in the gap file (its helper for a judgement, you for a field or a spelling), join again, check again; out/visual-plan.json is never edited by '
     'hand (the join refuses to overwrite one that was; `--rebuild` drops the edits).'),
]


def apply_visuals(prompt, parts):
    for change, old, new in COMMON:
        assert prompt.count(old) == 1, ('design/149', change)
        prompt = prompt.replace(old, new)
    part = next(p for p in parts if p['name'] == 'plan')
    for change, old, new in PLAN:
        assert part['text'].count(old) == 1, ('design/149', change)
        part['text'] = part['text'].replace(old, new)
    return prompt


if __name__ == '__main__':
    d = json.loads(P.read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply_visuals(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('design/149: seven replacements in the visuals text')
