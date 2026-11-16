"""design/207 (SK, 16 Nov 2026): instruction version 3, the visuals stage, after the review of the visuals rules. Any kind of shot may be an AI
video; clothes change with time; a real person is own likeness or a stand-in; a liquid has an amount, not unit sizes; a size is read against a
person; ten named people and no loose group; the world rule; the same set-up not twice and a reuse kept without the operator; a drawing to scale
or "not to scale"; framing as instructions; the check lists everything; the Direction placed by the server; the page for the treatment and the
plan; the cost limit by length; examples for every kind of film. Exact anchors, each found once; run once: python scripts/d207_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [   # (where: common or a part's name, the old sentence, the new one)
    # 1: any kind of AI video
    ('common', 'It is one action per shot, of three kinds: a walker; one action, close; a transfer, close, ending before the set-down.',
     "Any kind of shot may be an AI video. Three kinds are proven here; name one in the shot's `recipe` when the shot is one: `walker` (a person walking), `one_action_close` (one action, "
     'seen close), `transfer_close` (a pour, a pick-up or a hand-over, seen close, ending before the set-down). Any other kind is `recipe: other`: describe plainly what moves, how far, '
     'how fast and in what order; a thing that travels has a `path` in the scene description; expect a trial take, and the operator is told. A shot with no person is a normal shot. '
     'A person does one action in a shot.'),
    ('common', 'Any other kind (a crowd, a vehicle, a run, a door, night, people speaking) is not yet available as AI video: make it footage, a still or a drawn shot.',
     'More than four people, a run and people whose paths overlap are warned, never refused. The known weak cases: a camera that follows a runner has failed, so keep the camera fixed. '
     "People whose paths overlap come out as copies, so keep the paths apart. A door whose swing meets a person's path fails, so keep the path clear of it. People speaking: a take has "
     'no sound and lips do not match the words.'),
    ('treatment', 'an AI video shot is one action, at most four people, nobody crossing, hand work close and in the right hand, every transfer named and close; a picture that needs more is '
                  're-staged, or is footage, a still or a drawn shot;',
     'an AI video shot may be any kind of shot, with or without a person (section B); a person in it does one action, hand work is close and in the right hand, and every transfer is named and close;'),
    # 17: the cost limit
    ('common', "tell the operator the estimate and the film's cap (₹5,000; only the builder changes it, on SK's word); the server refuses a paid call that would pass it, with the spend so far: "
               'stop and tell the operator.',
     "tell the operator the estimate and the film's cost limit. The limit follows the film's length; `vw visuals prepare` and the page tell the figure. Only the owner sets another figure "
     'for a film (`vw visuals cap --inr N --quote "<the owner\'s words>"`). The server refuses a paid call that would pass the limit, with the spend so far: stop and tell the operator.'),
    # 16: where the operator answers
    ('common', 'The operator decides everything of this stage here in the chat, never on a page: do not give a page link or say "on the page".',
     'The operator answers the treatment and the plan on the page (`vw visuals page`). Every other decision of this stage is asked here in the chat, one at a time (`vw visuals next`, '
     '`vw visuals decide`).'),
    ('common', "THE CARD, FOR THE TREATMENT AND THE PLAN. For the treatment's lines and for the plan's gaps the server answers `vw visuals next` with a card instead of one item:",
     "THE CARD, WHERE THE PAGE CANNOT BE SHOWN. The card is the way back for the treatment and the plan, only where the page cannot be shown. There, for the treatment's lines and for the "
     "plan's gaps, the server answers `vw visuals next` with a card instead of one item:"),
    # 13: the Direction is placed by the server
    ('treatment', 'the operator takes one; foundation.treatment starts with it word for word unless the operator approves a new treatment.',
     "the operator takes one; the server places the accepted Direction at the head of the plan's `foundation.treatment`."),
    ('plan', "(refused before the recorded treatment, when a gap's route departs from it, or when foundation.treatment does not start with the direction);",
     "(refused before the recorded treatment or when a gap's route departs from it; the server places the accepted Direction at the head of `foundation.treatment`: write only your own "
     'text there, or leave it out);'),
    # 12: the checklist and the check
    ('plan', 'then the missing facts (section A), their answers written into plan-base.json. Then helpers',
     'then the missing facts (section A), their answers written into plan-base.json. Before the first check, read your own part once: every person has a `description`; a material has its '
     'unit sizes or its amount; a place shown has two `signs_of_use` or `staged_clean`; no size is left `proposed`; `world` holds the place, the period and what is normally there, and '
     '`exclusions` what the period forbids. Then helpers'),
    ('plan', "`vw visuals check --file out/visual-plan.json` until valid (it lists every item's first failure together) (it checks across gaps",
     "`vw visuals check --file out/visual-plan.json` until valid: it lists every shot's first fault and the plan-wide faults together (a way the treatment did not name among them); fix "
     'them all before sending again; a clean check means the proposal is taken (it checks across gaps'),
    # 7: the world, in the foundation
    ('plan', 'signage, language, the process; short positive statements,', 'signage, language, the process, and what is normally there; short positive statements,'),
    ('plan', 'each naming the decision it protects; no generic negatives,', 'each naming the decision it protects, and what the period forbids; no generic negatives,'),
    # 14: footage first, where two ways are offered
    ('plan', "only for a real ambiguity, a production constraint or the operator's request.",
     "only for a real ambiguity, a production constraint or the operator's request; the order of preference holds for each way: real footage that shows it, else AI video, else a still."),
    # examples for every kind of film
    ('plan', '(secondary subjects, named background workers, props)', '(secondary subjects, named background people, props)'),
    ('plan', '(a wall pattern, a product, a tool, a uniform)', '(a pattern, a product, a tool, a uniform)'),
    ('plan', '(technique: pointing, plastering, welding; not a gesture or a tool\'s name: "points at the crack", "picks up the drill")',
     '(technique: kneading, soldering, welding; not a gesture or a tool\'s name: "points at the screen", "picks up the drill")'),
    ('plan', 'and the working equipment (warned)', 'and the things in use around them (warned)'),
    ('plan', '(one brick, about 3 s)', '(setting one cup down, about 2 s)'),
    ('plan', '("25 % fewer bricks", not "↓ 25 %")', '("25 % less material", not "↓ 25 %")'),
    ('plan', '(a brick about 3 : 1.5 : 1;', '(a box about 3 : 2 : 1;'),
    ('later', "('Heights: the plinth top reaches a standing person's knee …')", "('Heights: the table top reaches a standing person's hip …')"),
    ('later', 'arrows, bars, courses as `<use>` repeats', 'arrows, bars, rows as `<use>` repeats'),
    ('later', 'sizes, counts, a sequence of courses, a comparison of measured things', 'sizes, counts, a sequence of steps, a comparison of measured things'),
    # 4: materials
    ('plan', 'a material its sizes in its `material_spec`;',
     'a material laid as repeating units (tiles, planks, pavers) its unit sizes in its `material_spec`; a liquid or a loose material (water, sand, paint) carries none: its `requirements` '
     'say how much is used or how much of the surface it covers, and the shot shows it;'),
    ('later', 'Every repeating material (kind material, or `repeating: true`: bricks, tiles, blocks, planks, pavers) carries one `material_spec`',
     'Every material laid as repeating units (kind material: tiles, blocks, planks, pavers; a liquid or a loose material has no spec) carries one `material_spec`'),
    # 5: size is the message
    ('plan', 'is refused without a size value and `compare_to` (another element in frame);',
     'is refused without a size value and `compare_to` (another element in frame: a person first; with no person, a thing whose size is generally fixed, such as a door, a chair or a '
     "hand tool); the server puts the size sentence into the prompt of the still and of the AI video's starting picture;"),
    # 2: people and clothes over time
    ('plan', "Refused without: a person's `description`, its fixed layer; each scene's `outfit` per person shown (garments and colours only, identical for a person across scenes; a framing "
             "note goes in the shot's `focus`, a question in `open_questions`); `time_jump` (the script's words) when a garment or a colour changes. Two people in one film wear different "
             'colour families unless the footage or the brief fixes their clothes (a uniform).',
     "Refused without: a person's `description`, the fixed layer (face, build, hair), which never changes; each scene's `outfit` per person shown (garments and colours only; a framing "
     "note goes in the shot's `focus`, a question in `open_questions`). A person keeps the same clothes within one continuous time. When the time changes (later the same day, another "
     "day, another season, years later) the clothes may change: the scene's `outfit` then names the garment types as well as the colours, and `time_jump` says what changed in time, from "
     "the script or the scene's own time (refused without). Two different people in one scene are not dressed in the same colours unless a uniform is the point."),
    # 3: real people
    ('plan', 'A real person required speaking on camera is the real person: `speaker: true`, every shot of them footage (`visual_type: footage`), other angles (listening, hands at work, '
             'profile, from behind) only from their own footage; AI pictures or takes of them are refused.',
     "`speaker: true` marks a real, named person and nothing more. Each person is one of two kinds. Own likeness: the operator gives the person's photo and says, in their own words, that "
     'they have the person\'s permission (`vw visuals likeness --element E --quote "<their words>"`, then `vw visuals own --element E --file <photo>`); the sheet is made from the photo. '
     'A stand-in: no photo; the person is made from the description. If the picture service refuses the photo, ask the operator for another photo or make the person a stand-in '
     '(`vw visuals likeness --element E --stand-in --quote "…"`). The server tells the operator in one plain line when a real, named person is shown as a stand-in. A take has no sound: a '
     'person can be shown, not made to speak in time with the voice.'),
    ('picture-search', 'one row per element: element_id, its frame reference ids,', 'one row per element, every person included and none for an animal: element_id, its frame reference ids,'),
    ('picture-search', "A footage frame of a person serves your description only, never the picture AI (a footage frame may still be a video take's start image); the server writes a person's "
                       'sheet from the plan (description, outfits, place, your why line, one line against every other person) as three separate pictures: full length, working pose, the face; '
                       'every worker the words act with is an element (the check warns of one missing).',
     "A footage frame of a person serves your description; it goes to the picture AI only with the person's recorded permission (own likeness, part-plan.md; a footage frame may still be "
     "a video take's start image). Every person gets a character sheet; an animal gets none. The server writes a person's sheet from the plan (description, outfits, place, your why "
     "line, one line against every other person), and from the person's photo when the permission is recorded, as three separate pictures: full length, working pose, the face; every "
     'person the words act with is an element (the check warns of one missing).'),
    ('later', "a person's sheet is made from words: look at their footage pictures and describe them (build, age, posture, garments and how they are worn, hair), and the sheet is made from "
              'that description.',
     "a person's sheet is made from their own photo when the permission is recorded (own likeness, part-plan.md); else the person is a stand-in: describe them (build, age, posture, "
     'garments and how they are worn, hair), and the sheet is made from that description.'),
    ('later', 'A footage or web picture of a person is never sent to the picture AI, as a parent or otherwise, nor copied: the sheet shows a representative person',
     "A picture of a person from the web is never sent to the picture AI, as a parent or otherwise, nor copied. A footage frame or the operator's own photo of a person is sent only with "
     'the recorded permission; without it the sheet shows a representative person'),
    ('later', 'a footage or web picture of a person is never sent to the picture AI. An older film:',
     'a picture of a person from the web is never sent to the picture AI, a footage frame or an own photo only with the recorded permission. An older film:'),
    # 6: people in a scene
    ('plan', 'Up to three background people are named workers (elements with beats; a sheet only with a source picture); more are a crowd: the ambient line plus one `groups` entry, '
             "`mode: varied`, a count and at least 2 traits used in turn; more than 3 named in a scene are refused; a passer-by without beats lives only in each scene's words, different "
             'each time (warned as an element).',
     'Up to ten people are named in the background of a scene, each an element with their own description and beats; beyond ten, each further person is described one by one in a '
     '`groups` entry with `mode: different` (one trait per head). `mode: varied` is retired. Never write "crowd", or a word that suggests one, in anything that goes to a picture. Every '
     'named person gets a character sheet in the reference round. This holds for stills as well as AI video.'),
    ('plan', 'In a video shot, several of a kind in one frame (counted above one, or a framing word such as workers, people, cows, unless negated: "no workers yet") need a `groups` entry, '
             '`same` (with the reason), `different` (one trait per head) or `varied` (at least 2 traits; refused otherwise).',
     'In a video shot or a still, several of a kind in one frame (counted above one, or a framing word such as people, children, cows, unless negated: "no people yet") need a `groups` '
     'entry, `same` (with the reason) or `different` (one trait per head); refused otherwise.'),
    # 7: the world; 8: traces of use
    ('plan', 'Props fit the work and the region (a tea glass on a site), never what the setting forbids (no smoking, flame or spark near fuel, gas or chemicals) or an unsafe practice shown as right.',
     'Props fit the work and the region (a kettle in a kitchen), never what the setting forbids (no smoking, flame or spark near fuel, gas or chemicals) or an unsafe practice shown as '
     'right. Ask of the world: for this place and this time, what would a viewer expect to see that the script does not name? Write it once in `world`, as exact kinds (for example '
     'overhead wires on poles along a road, a street dog of the region, house sparrows), and write once in `exclusions` what the period forbids (a film set in 1850: nothing electric, no '
     'plastic, no motor vehicle). Use it lightly: a picture takes at most one or two of these, and not every shot has one. A living extra is an element of kind `animal`, named by its '
     'exact kind with its `size`, so it stays the same size; it gets no reference sheet. A shot shows one kind of animal. The same living extra is not in two shots in a row unless it '
     'carries on from the shot before. Fixed things (poles, wires, signs, street furniture) are landmarks of the place and stay where they are in every picture of it. This applies to '
     'stills and to the starting picture of an AI video; plan no moving animal in an AI video.'),
    ('plan', 'Work leaves traces (tools, offcuts, mortar droppings, footprints; signs of use in a finished house): a place shown needs `signs_of_use` (two or more, each at one of its '
             'landmarks; refused without) unless the treatment approves it clean (a show home at handover, a new empty room, a showroom),',
     'People leave traces where they work or live (tools left out, offcuts, spills, footprints; a worn chair, cups on a desk): a place shown needs `signs_of_use` (two or more, each at '
     'one of its landmarks; refused without) unless the treatment approves it clean (a new empty room, a showroom, a product studio),'),
    # 11: framing
    ('plan', ' a look as the only change (prefer a profile or a back view);', ''),
    ('plan', 'Warned unless size_reason states a reveal: a scene opening closer than MWS, three shots in a row at one size, a close-up (MCU or closer) of a subject not yet seen wider '
             '(`continues_footage: true` on a scene counts the footage beside the gap as that view).',
     "A scene's first camera shot is EWS, WS or MWS. Never frame a third shot in a row at one size. Frame MCU or closer only after its subject was seen at MS or wider in this scene or the "
     'one just before. When the footage beside the gap already showed the place, set `continues_footage: true`; when the gap before showed it, or a reveal is meant, write `size_reason`. '
     "A shot about a look or an expression is framed MCU or closer with the face in frame, and the person's face picture is among its references. A miss comes back to you as a technical "
     'warning to fix; the operator is not told.'),
    # 9: no picture twice
    ('plan', 'No picture shows twice: a clip on screen (first cut or here) is a reuse, a frozen frame of a clip playing elsewhere never shows, no two shots share a start image or still. A '
             'return to a subject is a reimagined shot (`return_of`, `differs_by`; refused without), the earlier picture only as identity reference. A plain reuse only when that adds '
             'nothing: `vw visuals clip|still … --reuse "<reason>" --considered "<the reimagined shot and why it adds nothing>" --crop x,y,w,h`, refused under 60 s from the other showing, '
             "on the same stretch or beyond the clip's safe enlargement, then held for the operator's words (the page, or `vw visuals reuse --shot S --quote \"<their words>\"`); warned: "
             'the frozen share, pictures that look alike.',
     'The same person may appear as often as the film needs. The same person in the same place, in the same clothes and at the same size, is not shown twice: the second showing differs '
     'in angle, distance or moment (`return_of`, `differs_by`), the earlier picture only as identity reference. When the script itself stays in one place (a workplace), the place may '
     'stay and the framing changes. The identical picture is never used in two shots, and a frozen frame of a clip playing elsewhere never shows. A clip shown again (first cut or here) '
     'is a reuse: give the reason and the reimagined shot you considered, `vw visuals clip|still … --reuse "<reason>" --considered "<the reimagined shot and why it adds nothing>" '
     '--crop x,y,w,h`. A reuse that passes the checks is kept: another stretch of the clip, within its safe enlargement, at least 60 s from the other showing, or a quarter of the film '
     'when that is shorter. It does not wait for the operator; `vw visuals reuse` is retired. Warned, for you to fix: the frozen share, pictures that look alike.'),
    # 15: a card of words
    ('plan', '`title` or `text` (a card checked only for its words, spelling and size).',
     '`title` or `text` (a card checked only for its words, spelling and size); in a documentary or an explaining film a card of words is warned and the operator is told: show the thing, '
     'and let the voice say the words.'),
    # 10: a drawing of a real object
    ('plan', 'Drawing specs. A drawing of a real object has a `drawing_spec` (warned without;',
     'Drawing specs. A drawing of a real object is drawn to the convention of its field (a plan, a section or an elevation; dimension lines with units) and to scale. If it is not to '
     'scale, or any size in it is unknown, it carries the words "not to scale" (`illustrative: true`, the words in its `label`) and shows no figure for the unknown size. A size the '
     'narration states is always shown as stated. It has a `drawing_spec` (warned without;'),
    ('plan', 'and `view` with `view_reason` (refused without; a section defaults to cutaway)', 'and `view` with `view_reason` (give both; a section defaults to cutaway)'),
    ('plan', 'an `unknown` size without all four sources in `tried`,', 'an `unknown` size that does not say in `tried` what was tried,'),
]


def apply(prompt, parts):
    """The visuals text with design/207's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = None if where == 'common' else next(p for p in parts if p['name'] == where)
        text = prompt if part is None else part['text']
        if (new and new in text) or (not new and old not in text):
            continue
        if text.count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        text = text.replace(old, new)
        if part is None:
            prompt = text
        else:
            part['text'] = text
    return prompt


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals: design/207, the visuals rules after the review')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
