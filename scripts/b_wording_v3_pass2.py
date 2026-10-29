"""design/124 Phase B, pass 2: sections 1-4 of the visuals text of version 3 shortened (version 2 untouched).

Applied after scripts/b_wording_v3.py (the first pass, rebuilt here from its own build()):
  - every rule the server already refuses or warns on becomes one line naming the check, every number and condition kept;
  - the server's exact names (speaker, continues_footage, staged_clean, groups mode varied, gaze camera, hold_reason's small life, fixed at close sizes, shots[].seconds, ...);
  - two later sentences that contradicted decided changes corrected (LATER_FIXES); the rest of the later text unchanged.
Every first-pass sentence of sections 1-4 is traced (design/124-b-wording-trace.md, "Pass 2"). Run: python scripts/b_wording_v3_pass2.py [--check]
"""
import json, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b_wording_v3 as p1   # noqa: E402

HEADS = ['1. PREPARATION', '2. TREATMENT', '3. THE DETAILED PLAN', '4. THE PICTURE SEARCH']
NEXT = '5. GENERATED REFERENCES, SHEETS AND GOLDEN PICTURES'

# each section: paragraphs; each paragraph: (new sentence, the first-pass units it carries "line.unit")
NEW = {
"1. PREPARATION": [
    [
        ("Run `vw visuals prepare` once the first cut is approved (nothing is made or paid).",
         "28.0"),
        ("It writes the package under work/visuals/, one file per section (prompt.md, gaps.json, intended-visuals.json, brief.json, world-1.json and on with 25 clips each, "
         "schema.json, generators.json), and the image prompt library per step under work/visuals/library/ (section 6); read a file whole, never by line offsets.",
         "28.1"),
        ("Read prompt.md, gaps.json and intended-visuals.json first, the world files when you plan the scenes.",
         "28.2"),
        ("Give the operator the page link and tell them (never ask) its one line on the footage's look, measured from the clips; their correction (the page, or `vw visuals "
         "footage`) wins.",
         "28.3 28.4"),
        ("Then settle and record the treatment (section 2), before any plan or picture.",
         "28.5"),
    ],
],
"2. TREATMENT": [
    [
        ("`direction` comes first (refused without), the central creative choice: a few lines on what the audience should understand or feel by the end, the storytelling "
         "viewpoint, the principal visual approach and why, and the roles of footage, stills, generated scenes and graphics; foundation.treatment starts with it word for word "
         "unless the operator approves a new treatment.",
         "31.0 31.1"),
        ("A palette or \"documentary mix\" alone is not a direction.",
         "31.2"),
        ("Choose the picture from the film's purpose, audience and script before you think about how it is made: the effort, cost or convenience of a route never chooses the "
         "medium.",
         "31.3"),
        ("In a documentary or a client story, people, purposeful work and the material changing under their hands carry the film; a realistic representative scene is a legitimate "
         "picture when the footage lacks one, provided it does not pretend to be the client's own site, people or measured result.",
         "31.4"),
        ("There is no quota of AI video, footage or graphics: a technical record may lean on graphics, a human story on scenes; say in the direction which the film is and why.",
         "31.5"),
        ("With no footage, the direction also holds the film's one look (colours, contrast, light), approved once, read wherever a plan rule reads the footage beside a gap.",
         "31.6"),
    ],
    [
        ("Read the whole first cut, including the retained footage before, between and after the gaps.",
         "32.0"),
        ("Plan the missing passages in film order as one progression: what the audience already knows, what each adds, changes of pace, recurring visual ideas, how each enters "
         "from and exits into the neighbouring real pictures.",
         "32.1"),
        ("Use a diagram, chart or illustrated graphic when the meaning is invisible to a camera or must be read precisely: the inside of something (a cross-section, a cavity, a "
         "hidden layer); a flow, force, heat or load path; a number, comparison or proportion the narration rests on; a sequence where the order matters; scale; or before and "
         "after.",
         "32.2"),
        ("Use a scene (footage, or AI video or still of people and places) for people, places, materials, textures, effort, feeling and results, anything a camera could have "
         "filmed with more time.",
         "32.3"),
        ("Build the film's graphics as one visual language: one recurring diagram that develops across the film reads better than many unrelated drawings.",
         "32.4"),
        ("Vary the pictures: mix the shots of a gap longer than one shot (footage, an AI scene, a labelled scene, a graphic); two graphics in a row only when each passes the test "
         "above, the second's `warning_answers` saying why (warned, as is a gap of graphics only).",
         "32.5 32.6 32.7"),
        ("Treat the team's intended visuals (the script's visual notes per scene, in the package) as a stated requirement with its source: follow them where they fit the direction "
         "and the footage; say in the treatment why you depart from one.",
         "32.8"),
        ("The gap that opens the film (if one does) opens on the subject at work, framed wide enough to see where (the mason laying bricks on the half-built wall, the site "
         "around), never an empty view of the place; a close-up comes after a wider view.",
         "32.9"),
        ("Propose in the treatment the look of a gap with no real footage beside it (palette, contrast, saturation, muted and true to life by default, light; with no footage, the "
         "direction's look), approved with it.",
         "32.10"),
    ],
    [
        ("The treatment, in out/visual-treatment.json, has one entry per gap: `gap_id`; the words under it; the team's intended visuals, cited or departed from with the reason; "
         "`picture` in one line; `routes`; `seconds` (a video gap's segments with theirs); `images` (one start image per video segment, an end image only where the final state "
         "must be exact); `depicts`, one line per graphic, approved before anything is drawn; `activity_level` (quiet, normal or busy); `frozen_seconds` held still (usually 0); "
         "and, for more than one route, `shots` with each `route` and `seconds`.",
         "33.0 33.1 33.2 33.3 33.4 33.5 33.6 33.7 33.8 33.9 33.10 33.11"),
        ("End with your reasons; the server refuses a gap missing or twice or a field out of form, and adds per route the counts and seconds, the cost against the cap and the "
         "frozen share against its 10 % limit.",
         "33.12"),
    ],
    [
        ("Send the draft (`vw visuals treatment --file out/visual-treatment.json`); on the page (link printed) the operator accepts or sends back with a short note each line, the "
         "Direction first, then every gap.",
         "34.0 34.1"),
        ("In chat, present it line by line, passing their words: `vw visuals treatment --accept direction,G1,G2 --quote \"<their words>\"`, `vw visuals treatment --send-back G3 "
         "--notes \"<what to change>\"`; a yes to the whole: the draft command again with --quote \"<their yes>\".",
         "34.2"),
        ("Revise only a line sent back and send the draft again; unchanged accepted lines stay accepted, one your revision changed (a shared route, the totals) returns to \"to "
         "accept\".",
         "34.3"),
        ("Recorded when every line is accepted, the treatment comes before any plan or picture; the plan is checked against it.",
         "34.4 34.5"),
        ("Settle the direction in conversation before planning, and a material change as a decision before shots; never quietly rewrite an accepted foundation: a changed direction "
         "revises the treatment, sequence, affected world rules and scenes together, never a new rule beside shots that contradict it.",
         "34.6 34.7 34.8 34.9"),
    ],
],
"3. THE DETAILED PLAN": [
    [
        ("Order of work, in three steps, to the recorded treatment: foundation, elements, gaps (scenes, shots, states for animation shots, beats).",
         "37.0 37.1"),
        ("You write the shared parts in out/plan-base.json: foundation, elements, graphic style, sequence_overview, `gaps` (in order).",
         "37.2"),
        ("Then helpers (your own agents, a few gaps each; start with three or four) write the gaps at once from out/plan-base.json, the package, the recorded treatment and their "
         "neighbours (pictures before and after, the people's last state), never another helper's gaps, one file each in out/plan-gaps/ (a gap, or {\"gaps\": [...]}), things not "
         "among the elements in `new_elements` (id and name), never invented; a short film you may write alone.",
         "37.3 37.4 37.5"),
        ("`vw visuals plan-join --base out/plan-base.json --gaps out/plan-gaps/` writes out/visual-plan.json (film order, new things merged by name; a missing or doubled gap is "
         "refused).",
         "37.6"),
        ("`vw visuals check --file out/visual-plan.json` until valid (it checks across gaps and prints routes, graphic seconds, images and cost against the cap); fix what it names "
         "or send the gap back to its helper.",
         "37.7 37.8"),
        ("Answer each warning in the shot's `warning_answers` ({kind, answer}), never in the purpose, or change the plan; tell the operator the page's plain warnings, never the "
         "technical ones.",
         "37.9 37.10"),
        ("Before proposing, review each passage's meaning and treatment fit, every subject's beats, layout and scale against the landmarks, identity against the references, and "
         "continuity with the neighbours and across shots.",
         "37.11"),
        ("`vw visuals propose --file out/visual-plan.json` (refused before the recorded treatment, when a gap's route departs from it, or when foundation.treatment does not start "
         "with the direction); `vw visuals select --gap G --choice C` for an offered choice; the operator accepts each gap on the page or in chat (`vw visuals accept --gaps all "
         "--quote \"…\"`, or the gaps named).",
         "37.12"),
        ("Before any picture, read every gap's words in `vw visuals status`: a change asked for, or a gap sent back, is a revision (Revise, or `vw visuals revise --gap G --notes "
         "\"…\" --quote \"…\"`): revise its treatment entry and plan (one helper for one gap), propose again for fresh acceptance and generate nothing for it until then; unchanged "
         "gaps stay accepted.",
         "37.13 37.14 37.15"),
    ],
    [
        ("The foundation, a practical casting and production-design brief, has one topic per rule (id, statement, scope, source) in separate categories: world (place, period, "
         "people and their work, wardrobe, environment, materials, tools, signage, language, the process; short positive statements, only what this film needs, no invented region "
         "or dress); exclusions (detectable consequences of the direction, each naming the decision it protects; no generic negatives, no ban on a medium because one option was "
         "rejected); specifications; production_constraints (narration and first cut preserved); editing_constraints (rejected pictures, their intervals); appearance (style, "
         "colour, lighting; texture, sharp or soft, from the measured footage character, the operator's correction winning; with no footage, the direction's look).",
         "38.0 38.1 38.2 38.3 38.4 38.5 38.6 38.7 38.8 38.9 38.10 38.11"),
        ("Layouts live in scenes, identities in elements, temporal rules in sequence_rules; the foundation alone should let another director work.",
         "38.12 38.13"),
        ("Each statement is one of three kinds: a requirement or observed fact with its source (brief, script, the operator's words, a clip finding), applied no wider than the "
         "evidence; a creative choice marked Proposed, with its film-specific reason; a consequential unknown, asked in open_questions and `vw visuals ask`, when a choice would "
         "assert real geography, identity, culture or performance the sources do not establish.",
         "38.14 38.15 38.16"),
        ("Never fill an unknown with a stereotype or an inferred nationality, nor defer every casting and environment decision: propose the shared direction now, defer exact "
         "identities and props.",
         "38.17"),
        ("sequence_overview first: what each gap adds to the treatment's progression. An ordinary gap has one proposal in gap.scenes (treatment_fit: its part in the sequence); two "
         "choices (each with scenes, a recommended_choice, a plain decision_reason; other shapes refused) only for a real ambiguity, a production constraint or the operator's "
         "request.",
         "38.18 38.19 38.20"),
        ("A plain or studio background only when the treatment allows it (`studio_background`, with the reason); objects shown where made, kept or used, not alone.",
         "38.21"),
    ],
    [
        ("Meaning. Give each passage its key meaning, emotional weight and a concrete method (evidence, process, a person's experience, or another justified approach).",
         "39.0 39.1"),
        ("An abstract thought, feeling or statistic is valid narration: never rewrite it for a camera or fabricate documentary evidence (a graphic may explain a statistic); never "
         "invent facts, people, claims, scale or physical mechanisms.",
         "39.2 39.3"),
        ("Per shot (warned when missing): `claims` and `descriptors`, never shown as their opposite; `evidence`; `claim`, visible (footage first; warned on a graphic) or "
         "invisible; `fact_ids` into `visual_facts` (how a material, process or setting really looks and is done; source and status: confirmed, observed, unknown); `carries_over` "
         "for a process's next step (one process, one place, light and crew; \"on top of that\" or \"once\" is no process); `message`, with `adds` (a number, a cause, a consequence) "
         "when it repeats, or the two become one shot.",
         "39.4 39.5 39.6 39.7 39.9 39.10"),
        ("An MCU, CU or ECU resting on an unknown fact is refused: frame wider or ask the operator.",
         "39.8"),
    ],
    [
        ("Elements. Derive them from the planned shots (secondary subjects, named background workers, props), each exact (the same individual, object or place throughout) or "
         "representative, with its views.",
         "40.0 40.1"),
        ("Anything specific to the client the footage shows (a wall pattern, a product, a tool, a uniform) is its own exact object element, its footage frames as views and its "
         "description once in the world rules as exact text; until its golden picture exists, its pictures send one of those frames as a parent, never words alone.",
         "40.2 40.3 40.4"),
        ("A thing whose fact or size cites the footage (a clip or its frame; a maker's \"door frame\" is not footage) is `identity: exact` with an approved footage frame before any "
         "picture, measured first (`vw visuals measure`, status measured) when its size is unknown: warned in the plan, refused at the picture.",
         "40.5"),
        ("Materials and processes the film relies on are elements (kind material, process), as are tools in a holding or props list (object) and techniques a beat names as its "
         "working action (technique: pointing, plastering, welding; not a gesture or a tool's name: \"points at the crack\", \"picks up the drill\"), all in the reference round; a "
         "missing technique is refused (`status.needed_elements`).",
         "40.6 40.7 40.8 40.9"),
        ("Every person, object, animal and material has its real `size` (client material, `measure` on footage frames, a maker's sheet; else unknown, never invented; warned when "
         "missing); a claim or descriptor about the subject's own size, amount or scale is refused without a size value and `compare_to` (another element in frame), except on a "
         "graphic or drawn shot or for light, less, fewer or short not about size.",
         "40.10 40.11"),
        ("Refused without: a person's `description`, its fixed layer; each scene's `outfit` per person shown; `time_jump` (the script's words) when the colours change.",
         "40.12"),
        ("Two people in one film wear different colour families unless the footage or the brief fixes their clothes (a uniform).",
         "40.13"),
        ("A real person required speaking on camera is the real person: `speaker: true`, every shot of them footage (`visual_type: footage`), other angles (listening, hands at "
         "work, profile, from behind) only from their own footage; AI pictures or takes of them are refused.",
         "40.14"),
    ],
    [
        ("Scenes and life. A scene is one setting, time and purpose; beats are the smallest visible actions.",
         "41.0 41.1"),
        ("`activity_level` (quiet, normal or busy) from the narration and the brief; a normal or busy scene shows the implied life (who else does what) and the working equipment "
         "(warned).",
         "41.2"),
        ("Up to three background people are named workers (elements with beats; a sheet only with a source picture); more are a crowd: the ambient line plus one `groups` entry, "
         "`mode: varied`, a count and at least 2 traits used in turn; more than 3 named in a scene are refused; a passer-by without beats lives only in each scene's words, "
         "different each time (warned as an element).",
         "41.3 41.4"),
        ("Everything visible that acts (person, animal or object) has beats; a still one holds, with `hold_reason`, unchanged; in a video shot a living holder moves a body-length "
         "by the end unless `hold_reason` names small life (breathing, chewing, the head, the hands, the tail, the ears) and it is not standing in a normal or busy scene (refused "
         "otherwise).",
         "41.5 41.6"),
        ("A scene with a video shot has its ambient line (warned without), from the setting and the neighbouring footage, or 'still'; every scene its `light` once (warned without) "
         "and its air (dust, smoke, haze, steam or clean), matched to the footage beside the gap (with no footage, the direction's look) and named word for word in the prompt "
         "(soft overcast light, muted greens).",
         "41.7 41.8 41.9"),
        ("Props fit the work and the region (a tea glass on a site), never what the setting forbids (no smoking, flame or spark near fuel, gas or chemicals) or an unsafe practice "
         "shown as right.",
         "41.10"),
        ("Work leaves traces (tools, offcuts, mortar droppings, footprints; signs of use in a finished house): a place shown needs `signs_of_use` (two or more, each at one of its "
         "landmarks; refused without) unless approved clean (a show home at handover, a new empty room, a showroom), the reason in `staged_clean`.",
         "41.11 41.12"),
        ("In a video shot, several of a kind in one frame (counted above one, or a framing word such as workers, people, cows, unless negated: \"no workers yet\") need a `groups` "
         "entry, `same` (with the reason), `different` (one trait per head) or `varied` (at least 2 traits; refused otherwise).",
         "41.13"),
    ],
    [
        ("Positions, states and beats. Lay out each scene with named landmarks (the doorway, the table, the near wall), room positions apart from the screen sides; a moving "
         "subject heads for something in frame or coming into view.",
         "42.0 42.1 42.2"),
        ("Each subject: a role, screen position, start and end states, facing, pose, held objects and progress; an acting one ordered timed beats (start and end, target, path, "
         "contact, visible result).",
         "42.3 42.11"),
        ("Refused: a position without landmark, `amount` and `unit`; `facing` not a heading; `objects` without `count` and `place`; a held tool without `props`; a beat without "
         "`done` or with a free-word target (a landmark or an element id of the shot; describe it in path and result); a person's state without `gaze` (its target may be `camera`) "
         "unless `face_in_frame` is false; a video shot whose `fixed` is not three landmark ids (all when fewer; at MCU, CU or ECU only those in frame, none allowed); a beat "
         "shorter than its `min_s` (one brick, about 3 s) or actions that overrun the shot.",
         "42.4 42.5 42.6 42.7 42.8 42.9 42.10 42.11 42.12"),
        ("Warned: a missing `min_s`; a look as the only change (prefer a profile or a back view); an acting video shot without `changes` (none for ambient-only shots); a state "
         "changed between shots without a note (a cut never teleports a person or resets work).",
         "42.9 42.12 42.13 42.14"),
        ("The server writes the rule lines from these fields (two signs of use per shot, or 'clean and unused, as planned') and checks every picture and take against them; "
         "`status.figure_repeats` names repeated background figures.",
         "42.15 42.16"),
        ("`boundary_continuity` (required): how the first and last shot continue the neighbours on both sides, footage or planned (at the film's start or end, the one side).",
         "42.17"),
    ],
    [
        ("Timing and movement. Narration is timed per gap (gaps.json `timing`: sentences in seconds, words in frames; context.timing adds the sentences either side).",
         "43.0 43.1"),
        ("Cut in a pause, never inside a word; a shot's `narration` is the words it covers, its picture starting on or just before them, a title or label on its word (warned "
         "otherwise).",
         "43.2 43.18"),
        ("Shots run two to eight seconds as a rule, never mechanically equal; AI video 3 to 10 s (longer refused), 3–5 s in an AI run; over 12 s of AI video back to back in a gap "
         "is warned (`ai_run`), footage or not: break it with a frame, still or graphic.",
         "43.3 43.4"),
        ("Real footage in a gap is a footage shot (`visual_type: footage`, `vw visuals clip`), under the timing, crop, reuse and no-repeat rules only, not those for generated "
         "pictures (the 10 s limit among them).",
         "43.5"),
        ("Every still and graphic state moves 5 % (`motion`, from the composition); a graphic or a text picture only push_in or none; `none` needs `motion_reason` (refused "
         "otherwise).",
         "43.6"),
        ("Warned: a moving still over 4 s, a frozen one over 3 s, a graphic state over 5 s, one graphic over 4 s (not a title or text card: a build of 2 to 4 states or a drawn "
         "animation), a label or one number under three seconds, a run of graphics over 8 s (a building diagram fits within; break it with a camera shot).",
         "43.7 43.9"),
        ("Fill a longer stretch with several stills, a clip stretch (`vw visuals clip --shot S --clip C --at <in seconds>`) or a take.",
         "43.8"),
        ("Each shot has a size (EWS, WS, MWS, MS, MCU, CU, ECU) and a camera_reason (eye level honest, low powerful, high vulnerable, a slow push draws in; no angle has one fixed "
         "meaning; warned when missing, footage excepted).",
         "43.10 43.11"),
        ("Warned unless size_reason states a reveal: a scene opening closer than MWS, three shots in a row at one size, a close-up (MCU or closer) of a subject not yet seen wider "
         "(`continues_footage: true` on a scene counts the footage beside the gap as that view).",
         "43.10"),
        ("A clip needing more than 1.35× to fill the frame keeps bars (warned): crop it to the frame's shape (`vw visuals clip … --crop x,y,w,h`) or choose another.",
         "43.12"),
        ("A graphic dissolves in and out over 8 frames and other cuts are hard, so AI scenes and footage read as one world; otherwise `transition_in` (`transition_out` on a gap's "
         "last shot only): cut, dissolve or match, with `transition_reason` (refused without).",
         "43.13 43.14"),
        ("No picture shows twice: a clip on screen (first cut or here) is a reuse, a frozen frame of a clip playing elsewhere never shows, no two shots share a start image or "
         "still.",
         "43.15"),
        ("A return to a subject is a reimagined shot (`return_of`, `differs_by`; refused without), the earlier picture only as identity reference.",
         "43.16"),
        ("A plain reuse only when that adds nothing: `vw visuals clip|still … --reuse \"<reason>\" --considered \"<the reimagined shot and why it adds nothing>\" --crop x,y,w,h`, "
         "refused under 60 s from the other showing, on the same stretch or beyond the clip's safe enlargement, then held for the operator's words (the page, or `vw visuals reuse "
         "--shot S --quote \"<their words>\"`); warned: the frozen share, pictures that look alike.",
         "43.17 43.18"),
    ],
    [
        ("Graphics. A graphic that builds or reveals is one animation shot of two to four states, each adding something and holding at least three seconds, together filling the "
         "shot (refused otherwise); an unchanging one is a diagram shot, one still.",
         "44.0 44.1 44.2"),
        ("`graphic_kind`: `diagram`, `chart`, `map`, `title` or `text` (a card checked only for its words, spelling and size).",
         "44.3"),
        ("Each state names the claims and words it shows (`what_appears`, `words`; what none names is checked on the last) and starts on its `words`.",
         "44.4 44.5"),
        ("`depicts`: the film's subject in its own form; an alternative (the conventional way, a competitor's) only as a labelled contrast the narration calls for.",
         "44.6"),
        ("Labels: short complete phrases (\"25 % fewer bricks\", not \"↓ 25 %\"), numbers with units, leader lines ending on their part, at least 4 % of the frame height (titles 6 %), "
         "in the answer's exact text (section B).",
         "44.7"),
        ("Each claim spoken over a graphic is in `claims` (a must line) or `claims_left_out` with the reason; a build has a state per claim (warned); a state like the one before "
         "is refused; the assembly film is checked for every planned state.",
         "44.8 44.9"),
        ("One graphic style per film (foundation.graphic_style: palette from the client card, line weight, labels, background, frame fill), made first as a style sheet (`vw "
         "visuals image --element _STYLE --kind style --answer …`), approved, in the --parents of every graphic's first (or only) picture, later states inheriting it; every "
         "picture and take carries its --answer; warned: missing claims, depicts, style, spec approval or answers.",
         "44.10 44.11"),
    ],
    [
        ("Drawing specs. A drawing of a real object has a `drawing_spec` (warned without; an idea graphic with no real object or figure, such as heat leaving a house, needs none): "
         "parts, relationships, each size with status (confirmed: the client's source; measured; unknown) and source, and `view` with `view_reason` (refused without; a section "
         "defaults to cutaway), checked on the drawing.",
         "45.0 45.1 45.2"),
        ("Research every size before the spec is shown, in this order: the client's material; the footage, measured (`vw visuals measure --refs F1 F2 --question \"<what to "
         "measure>\"` on approved footage frames, each number keeping its clip and time; paid: announce, never ask); a standard or maker's sheet on the web, with URL and figure "
         "(one warning and one yes cover every web figure of the run); an approved reference picture for a shape numbers cannot hold.",
         "45.3 45.4 45.5 45.6 45.7"),
        ("Each value carries its source and status, a spec of a real object its proportions (a brick about 3 : 1.5 : 1; warned without).",
         "45.8 45.9"),
        ("Refused: an `unknown` size without all four sources in `tried`, an unknown with a value, `illustrative: true` when nothing is unknown or missing when something is, an "
         "illustrative drawing not labelled \"illustrative, not to scale\" (no numbers, no free proportions); `status.illustrative` warns above one in four.",
         "45.10 45.11"),
        ("The SVG scene labels known sizes with units.",
         "45.12"),
        ("The operator never types a size: they approve the run's specs in one table (`vw visuals spec` with no --shot, or the page) or send a correction (`vw visuals spec --shot "
         "S --notes \"…\"`, listed in `spec_corrections`) you fold in with `planning revise` (approval refused while one waits); one late spec: `vw visuals spec --shot S --quote "
         "\"…\"`.",
         "45.13 45.14 45.15 45.16"),
    ],
],
"4. THE PICTURE SEARCH": [
    [
        ("The references are one round for every element at once (people, objects, places, the materials and processes the film relies on), never one element at a time.",
         "48.0"),
        ("`vw visuals elements` shows where each is seen in the footage (work/visuals/elements.json); grab a frame of each the footage has (`vw visuals frame --file`, free); write "
         "out/reference-round.json, one row per element (element_id, its frame reference ids, the two-to-six-word keywords you would search), send it (`vw visuals round --file "
         "out/reference-round.json`) and give the operator the page link once.",
         "48.1"),
        ("Gather only what the plan needs, per element in this order: a clip frame; the operator's own picture (`supply`); for what the footage lacks, Google Images on the "
         "operator's yes (the round's searches); after the round, a picture by the picture AI (section 5).",
         "48.2"),
        ("A clip frame is free and exact, source and time kept (`vw visuals frame --element E --clip <id> --at <seconds>`); search the clip analyses first, footage left out of the "
         "edit included (not the operator's explicit exclusions), and take the sharpest frame, the subject large and evenly lit, never a blurred one for identity.",
         "48.3"),
        ("A footage frame or web picture of a person serves your description only, never the picture AI (a footage frame may still be a video take's start image), and so does a "
         "web search for a person or character not in the footage.",
         "48.4"),
    ],
    [
        ("`vw visuals status --wait 900` until the round is complete; ask nothing per element and generate nothing meanwhile.",
         "49.0 49.3"),
        ("Pass 1: each thing gets the footage picture, Search or Ignore this, Done waiting until every thing set to Google is searched; pass 2: a tick with notes, new words and "
         "Search again, or Ignore this, Done waiting for all.",
         "49.1 49.2"),
        ("With a source two searches come back; the ten pictures go to the page for ticks and notes; picks are approved when saved (reject one only if the file is not the picture "
         "ticked).",
         "49.4 49.5"),
        ("A \"nothing fits\" reason joins the not-this list; the next search is the operator's words (or Ignore this), never yours.",
         "49.6"),
        ("In chat: `vw visuals search --element E --keywords \"<two to six words: the thing and its place or trade>\" --source <stock site, outside the six words; empty for the "
         "plain search alone> --quote \"<their yes>\"` per thing sent to Google; `vw visuals pick --search S --n 2,5 --note 2=\"…\" --quote \"…\"`; `vw visuals nothing-fits --search S "
         "--reason \"…\"`; or a whole pass: `vw visuals round --verdicts out/round-verdicts.json --quote` ({element: {verdict: approve|search|ignore}}), then `vw visuals round "
         "--picks out/round-picks.json --quote` ({search id: [{n, note}], \"ignore\": [elements]}).",
         "49.7 49.8 49.9 49.10 49.11"),
        ("Meanwhile, for accepted gaps only and without generating or spending, draft the answer forms of every diagram, chart and title card, the drawing and material specs (the "
         "client's material and the plan; paid measures and web figures after the round) and the drawn layouts; nothing new on the page and no question until the round closes, "
         "then the drafts' questions as one list; update drafts the round changed.",
         "49.12 49.13 49.14 49.15"),
        ("One round is the default; the operator can redo one element at any time, add their own picture (`vw visuals supply`) or undo Done (`vw visuals round --undo`: pass 1 "
         "until a pick is saved, pass 2 until a sheet was made), never touching the others; a picture added after the sheet marks it 'sources changed': make a new sheet (the old "
         "one stays approved until then).",
         "49.16 49.17 49.18"),
        ("Then the picture AI references, sheets and golden pictures (sections 5 and 9).",
         "49.19"),
    ],
],
}

# first-pass units dropped with no new home (none expected: anything here is listed with its reason)
REMOVED = {}

# the later text: only these two sentences change (decided changes the first pass left contradicted)
LATER_FIXES = [
    ("Every video shot lists its `changes`: each visible difference between the start and the end picture, with the beat that causes it.",
     "Every video shot in which a subject acts lists its `changes`: each visible difference between the start picture and the end of the shot, with the beat that causes it; a shot where only the ambient moves lists none.",
     'section 6: a video is made from its start image alone by default (end image only with `end_state_exact`), and film-type item 5 (an ambient-only shot lists no changes); '
     'the old wording assumed a start and end picture for every shot'),
    ("AI video or a graphic build there needs its reason in `purpose` ('because …'), the check warns without one;",
     "AI video or a graphic build there needs its reason in its `warning_answers` (kind short_route), never in the purpose; the check warns without one;",
     'section 9: design/124 Change 7: warnings and reasons are answered in `warning_answers`; the purpose stays a clean description of the picture'),
]

# the server's exact names, checked against server/app/visual_contract.py, visuals_stage.py and plugin/scripts/vw.py (working copy, 29 Oct 2026)
NAMES = [
    'Added: `speaker: true` on a person element (visual_contract: refused on any other kind; every shot showing it must be `visual_type: footage`; visuals_stage refuses any AI picture of it).',
    'Added: `continues_footage: true` on a scene (course_warnings: the footage beside the gap counts as the wider view for size_open / size_close_first).',
    'Added: the small life a `hold_reason` may name (SMALL_LIFE: breathing, chewing, the head, the hands, the tail, the ears; also blink, nod, fingers, shifts, sways), not for a standing figure in a normal or busy scene; '
    'the first pass named "breathing, a head turn, the hands" and no exception.',
    'Added: `fixed` at MCU, CU or ECU names only the landmarks in frame, none allowed (CLOSE_SIZES; len(fixed) <= wanted); the first pass said "down to none at MCU or closer" (same rule, now with CU and ECU named).',
    'Named: groups `mode: varied` with at least 2 traits (the first pass said "the count and a few traits used in turn", no mode name, no number); more than 3 named background people refused (CROWD = 3).',
    'Named: the treatment field `routes` (TREATMENT_ROUTES; the first pass said "its route or routes"), and `shots` with each `route` and `seconds` (design/124-b item 14).',
    'Kept as named, confirmed in code: `visual_type: footage`, `staged_clean`, `signs_of_use`, gaze target `camera` (GAZE_CAMERA), `warning_answers` ({kind, answer}), treatment `direction`, '
    '`--accept` / `--send-back` / `--notes` (vw.py), `plan-join --base --gaps` (vw.py, nothing sent to the server), `status.needed_elements`, `status.illustrative`, `status.figure_repeats`, `spec_corrections`.',
    'No first-pass name was found different from the code.',
]

# numbers written fewer times in sections 1-4 after pass 2, with the reason (anything else fails the check)
NUMBERS_FEWER = {
    '8': 'duplicate merged: "fits within the 8 s a run of graphics may last" and "a run of graphics over 8 s is broken" said the same limit; written once ("a run of graphics over 8 s (a building diagram fits within it")',
    'two': 'duplicate merged: "Offer two choices only for …: two concrete options" written once ("two choices (each with its scenes …)"); and the lines the server itself adds are no longer listed ("the groups line (all alike / no two alike) with two must lines": written by the server, not the assistant; the groups rules for the plan are kept)',
    '5': 'duplicate merged: "3–5 s inside an AI run" and "shots 3–5 s" in the ai_run sentence said the same; written once',
}


def first_pass():
    return p1.build()


def units_of(prompt):
    """(id, text) of every first-pass unit of sections 1-4, id = line.unit of the first-pass prompt; heading lines left out."""
    lines = prompt.split('\n')
    start, end = lines.index(HEADS[0]), lines.index(NEXT)
    out = []
    for li in range(start, end):
        if lines[li] in HEADS or not lines[li].strip():
            continue
        out += [(f'{li}.{ui}', u) for ui, u in enumerate(p1.units(lines[li]))]
    return out


def build():
    prompt, steps = first_pass()
    a = prompt.index('\n' + HEADS[0] + '\n')
    b = prompt.index('\n' + NEXT + '\n')
    block = '\n' + '\n\n'.join(h + '\n' + '\n'.join(' '.join(t for t, _ in para) for para in NEW[h]) for h in HEADS) + '\n'
    later = prompt[b:]
    for old, new, _ in LATER_FIXES:
        assert later.count(old) == 1, f'later fix not found once: {old[:60]}'
        later = later.replace(old, new)
    return prompt[:a] + block + later, steps


def words(text):
    return len(text.split())


def on_first_pass(fn):
    """Run a first-pass function (its check, its trace) with p1.V3 pointing at a copy of v3.json holding the first-pass text."""
    old_prompt, old_steps = first_pass()
    with tempfile.TemporaryDirectory() as tmp:
        d = json.loads(p1.V3.read_text(encoding='utf-8'))
        st = next(s for s in d['stages'] if s['name'] == 'visuals')
        st['prompt'], st['steps'] = old_prompt, old_steps
        tmp_v3 = Path(tmp) / 'v3.json'
        tmp_v3.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        keep, p1.V3 = p1.V3, tmp_v3
        try:
            return fn()
        finally:
            p1.V3 = keep


def check(new_prompt, new_steps):
    report = []
    old_prompt, old_steps = first_pass()
    d3 = json.loads(p1.V3.read_text(encoding='utf-8'))
    d2 = json.loads(p1.V2.read_text(encoding='utf-8'))
    st = next(s for s in d3['stages'] if s['name'] == 'visuals')
    assert st['prompt'] == new_prompt and st['steps'] == new_steps, 'v3.json does not hold the pass-2 text'
    assert [s['name'] for s, t in zip(d2['stages'], d3['stages']) if s != t] == ['visuals'], 'a stage other than visuals differs from v2'
    report.append('- JSON loads; only the visuals stage differs from v2')
    # the first pass's own check, on the first-pass text (its trace and number checks stay valid)
    first = on_first_pass(lambda: p1.check(old_prompt, old_steps))
    report.append(f'- first-pass check (b_wording_v3.check on the first-pass text): {len(first)} lines, passed')
    # every first-pass unit traced
    ids = dict(units_of(old_prompt))
    covered = {i for h in HEADS for para in NEW[h] for _, srcs in para for i in srcs.split()}
    unknown = covered - set(ids)
    assert not unknown, f'unknown unit ids: {sorted(unknown)}'
    missing = set(ids) - covered - set(REMOVED)
    assert not missing, f'first-pass units with no new home: {sorted(missing, key=lambda x: [int(n) for n in x.split(".")])}'
    report.append(f'- {len(ids)} first-pass units of sections 1-4: every one traced ({len(REMOVED)} removed with a reason)')
    # later text: unchanged except LATER_FIXES
    ob, nb = old_prompt.index('\n' + NEXT + '\n'), new_prompt.index('\n' + NEXT + '\n')
    old_later, new_later = old_prompt[ob:], new_prompt[nb:]
    for old, new, _ in LATER_FIXES:
        old_later = old_later.replace(old, new)
    assert old_later == new_later, 'the later text differs beyond the two fixes'
    assert old_prompt[:old_prompt.index('\n' + HEADS[0] + '\n')] == new_prompt[:new_prompt.index('\n' + HEADS[0] + '\n')], 'the common part changed'
    assert old_steps == new_steps, 'the steps list changed'
    report.append(f'- common part and steps list unchanged; later text unchanged except {len(LATER_FIXES)} sentences')
    # numbers in sections 1-4
    o_sec, n_sec = p1.section_text(old_prompt, HEADS[0], NEXT), p1.section_text(new_prompt, HEADS[0], NEXT)
    on, nn = p1.numbers(o_sec), p1.numbers(n_sec)
    gone = sorted(k for k in on if nn[k] == 0)
    fewer = sorted(k for k in on if 0 < nn[k] < on[k])
    bad = [k for k in gone + fewer if k not in NUMBERS_FEWER]
    assert not bad, 'numbers fewer or gone without a reason: ' + ', '.join(f'{k} ({on[k]} -> {nn[k]})' for k in bad)
    report.append('- numbers gone from sections 1-4: ' + (', '.join(gone) if gone else 'none'))
    report.append('- numbers written fewer times (before, after): ' + ('; '.join(f'{k} ({on[k]}, {nn[k]}): {NUMBERS_FEWER[k]}' for k in fewer) if fewer else 'none'))
    added = sorted(k for k in nn if nn[k] > on[k])
    report.append('- numbers written more times (the server\'s figures named): ' + (', '.join(f'{k} ({on[k]}, {nn[k]})' for k in added) if added else 'none'))
    # words
    tot_o, tot_n = words(o_sec), words(n_sec)
    report.append(f'- words, sections 1-4: {tot_o} -> {tot_n} ({(tot_o - tot_n) / tot_o:.0%} shorter); prompt+steps {words(old_prompt) + words(" ".join(old_steps))} -> '
                  f'{words(new_prompt) + words(" ".join(new_steps))}')
    for i, h in enumerate(HEADS):
        nxt = HEADS[i + 1] if i + 1 < len(HEADS) else NEXT
        report.append(f'-   {h}: {words(p1.section_text(old_prompt, h, nxt))} -> {words(p1.section_text(new_prompt, h, nxt))}')
    return report


def trace_md(report):
    old_prompt, _ = first_pass()
    ids = units_of(old_prompt)
    new_of = {}
    for h in HEADS:
        for para in NEW[h]:
            for text, srcs in para:
                for s in srcs.split():
                    new_of.setdefault(s, []).append(text)
    esc = lambda s: s.replace('|', '\\|').replace('\n', ' ')
    srcs_of = {t: srcs for h in HEADS for para in NEW[h] for t, srcs in para}
    head_of = {}
    for i, h in enumerate(HEADS):
        for para in NEW[h]:
            for _, srcs in para:
                for s in srcs.split():
                    head_of.setdefault(s, h)
    out = ['', '---', '', '# Pass 2 (scripts/b_wording_v3_pass2.py): sections 1-4 shortened, the server\'s names, two later sentences', '',
           'One row per first-pass sentence of sections 1-4 ("F" + line.unit of the first-pass prompt). "kept" means the sentence is unchanged; "merged into" means the new sentence carries '
           'it with others; a sentence the server already checks became one line naming the check ("the check refuses …", "the check warns …", "the server refuses …"), every number and '
           'condition kept. Names checked against server/app/visual_contract.py and visuals_stage.py and the chat tool (plugin/scripts/vw.py: `plan-join`, `--accept`, `--send-back`).', '',
           '| First pass | Section | Old sentence | Change | New sentence |', '|---|---|---|---|---|']
    for uid, text in ids:
        if uid in REMOVED:
            out.append(f'| F{uid} | | {esc(text.strip())} | removed: {esc(REMOVED[uid])} | |')
            continue
        news = new_of[uid]
        same = any(n.strip() == text.strip().rstrip(';').strip() or n.strip() == text.strip() for n in news)
        alone = len(news) == 1 and len(srcs_of[news[0]].split()) == 1
        change = 'kept' if same else 'rewritten as' if alone else ('merged into' if len(news) == 1 else f'merged into {len(news)} sentences')
        out.append(f'| F{uid} | {head_of[uid]} | {esc(text.strip())} | {change} | {"<br>".join(esc(n) for n in news) if not same else ""} |')
    out += ['', "## Pass 2: the server's names", ''] + [f'- {n}' for n in NAMES]
    out += ['', '## Pass 2: the two later sentences', '', '| Old | New | Why |', '|---|---|---|']
    out += [f'| {esc(o)} | {esc(n)} | {esc(w)} |' for o, n, w in LATER_FIXES]
    out += ['', '## Pass 2: script check (python scripts/b_wording_v3_pass2.py --check)', ''] + report + ['']
    return '\n'.join(out)


if __name__ == '__main__':
    prompt, steps = build()
    if '--check' not in sys.argv:
        d = json.loads(p1.V3.read_text(encoding='utf-8'))
        st = next(s for s in d['stages'] if s['name'] == 'visuals')
        st['prompt'], st['steps'] = prompt, steps
        if 'Pass 2' not in d['note']:
            d['note'] += (' Pass 2: sections 1-4 shortened (the rules the server checks one line each, naming the check), the server\'s exact names, and two later sentences'
                          ' corrected (changes for a start-only video; a reason in warning_answers, never in the purpose).')
        p1.V3.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    report = check(prompt, steps)
    for line in report:
        print(line)
    if '--check' not in sys.argv:
        p1.TRACE.write_text(on_first_pass(p1.trace_md) + trace_md(report), encoding='utf-8', newline='\n')
