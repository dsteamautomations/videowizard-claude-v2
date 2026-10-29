"""design/124 Phase B: the visuals stage text of instruction version 3 restructured (version 2 untouched).

Builds the new `prompt` and `steps` of stage "visuals" from the old version 3 text (git commit OLD_COMMIT):
  A-D  the common part (stop and ask; what the stage makes and the five routes; plain language; paid steps and the cap), word for word;
  1-4  one section per reviewed phase (preparation, treatment, the detailed plan, the picture search), each topic written once;
  5-10 the later phases' text, word for word in its old order (old guide sections 5-8 remainder, then the old steps' remainder, then brand).
Every old sentence of the four phases is traced (design/124-b-wording-trace.md). Run: python scripts/b_wording_v3.py [--check]
"""
import json, re, subprocess, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V3, V2 = ROOT / 'server/procedures/v3.json', ROOT / 'server/procedures/v2.json'
TRACE = ROOT / 'design/124-b-wording-trace.md'
OLD_COMMIT = '1a184e5'   # the version 3 text after A1-A4 (design/124 A3 + A4 built)

# ---------- the old text, split into units (sentences; a sentence over 70 words also at each '; ') ----------
SPLIT = re.compile(r'(?<=[.!?”"\)])\s+(?=[A-Z`"“(])')
EXTRA = {'S3': ['), a generated image (']}   # S3.25 holds the end of the search list and the start of the generated-image item


def units(text):
    out, i = [], 0
    for m in SPLIT.finditer(text):
        out.append(text[i:m.start()] + m.group(0)); i = m.end()
    out.append(text[i:])
    res = []
    for u in out:
        res += re.split(r'(?<=; )', u) if len(u.split()) > 70 else [u]
    return res


def old_units(stage):
    rows = []
    for pi, line in enumerate(stage['prompt'].split('\n')):
        for ui, u in enumerate(units(line)):
            rows.append([f'P{pi}.{ui}', u, pi, 'P'])
    for si, s in enumerate(stage['steps']):
        us = units(s)
        ids = [f'S{si}.{ui}' for ui in range(len(us))]
        for cut in EXTRA.get(f'S{si}', []):
            k = next(j for j, u in enumerate(us) if cut in u)
            a, b = us[k].split(cut)
            us[k:k + 1] = [a + cut[:3], cut[3:] + b]   # "), " stays with the first part
            ids[k:k + 1] = [ids[k], ids[k] + 'b']        # the second part keeps the number with a "b"
        for uid, u in zip(ids, us):
            rows.append([uid, u, si, 'S'])
    return rows


def tag(uid):
    """C common (kept), H heading, P preparation, T treatment, L plan, S picture search, X later (kept word for word)."""
    src, rest = uid[0], uid[1:]
    if rest.endswith('b'):
        return 'X'   # S3.25b: the generated-image item, a later step
    line, n = (int(x) for x in rest.split('.'))
    if src == 'P':
        if line in (0, 2, 4, 7, 18, 28, 32, 38, 45, 53, 57) and (line in (0, 2) or n <= 1):
            return 'H'
        if line in (5, 8, 10, 11, 12, 13, 14, 15, 16, 29, 30, 49):
            return 'C'
        if line in (19, 20, 21, 22, 24):
            return 'T'
        if line == 23:
            return 'T' if n == 6 else 'L'
        if line in (25, 26, 33, 34, 36, 54):
            return 'L'
        if line == 35:
            return 'P' if n == 11 else 'L'
        if line == 39:
            return 'L' if n <= 4 else 'X' if n == 5 else 'S'
        if line in (40, 41):
            return 'S'
        return 'X'   # 42, 43, 46-48, 51, 55, 58-60
    if line == 0:
        return 'P'
    if line == 1:
        return 'T'
    if line == 2:
        return 'L'
    if line == 3:
        if n in (47, 48, 79, 80):
            return 'L'
        if n <= 14 or n in (16, 17, 19, 20, 21, 22, 23, 24, 25, 34, 46):
            return 'S'
        return 'X'
    return 'X'


OLD = json.loads(subprocess.run(['git', 'show', f'{OLD_COMMIT}:server/procedures/v3.json'], capture_output=True, cwd=ROOT, check=True).stdout.decode('utf-8'))
OLD_ST = next(s for s in OLD['stages'] if s['name'] == 'visuals')
ROWS = old_units(OLD_ST)
assert ''.join(r[1] for r in ROWS if r[3] == 'P') == OLD_ST['prompt'].replace('\n', ''), 'the prompt split loses text'
assert [''.join(r[1] for r in ROWS if r[3] == 'S' and r[2] == i) for i in range(len(OLD_ST['steps']))] == OLD_ST['steps'], 'the steps split loses text'
UNIT = {r[0]: r[1] for r in ROWS}
TAG = {r[0]: tag(r[0]) for r in ROWS if r[1].strip()}


def U(uid):
    return UNIT[uid].strip()


def cap(t):
    return t[:1].upper() + t[1:]


# ---------- the new text of the four phases: (text, old units it carries) per sentence, sentences grouped in paragraphs ----------
SEC = {}

SEC['1. PREPARATION'] = [[
    ("Run `vw visuals prepare` once the first cut is approved; nothing is made or paid at this step. It writes the package for reading under work/visuals/, "
     "one file per section (prompt.md, gaps.json, intended-visuals.json, brief.json, world-1.json and on with 25 clips each, schema.json, generators.json), "
     "and the image prompt library per step under work/visuals/library/ (how to read it: section 6), and prints the list with row counts; read a file whole, never by line offsets.",
     ['S0.0', 'S0.2']),
    ("Read prompt.md, gaps.json and intended-visuals.json first; the world files when you plan the scenes.", ['S0.1']),
    ("It prints the visuals page link: give it to the operator.", ['S0.3']),
    ("It prints how the footage looks, measured from the clips, in one line: tell the operator, never ask; their correction (on the page, or `vw visuals footage`) wins.", ['P35.11']),
    ("Then settle the treatment with the operator and record it (section 2), before any plan or picture.", []),
]]

SEC['2. TREATMENT'] = [[
    ("Direction is the central creative choice, and the treatment starts with it: `direction`, a few lines saying what the audience should understand or feel by the end, "
     "the storytelling viewpoint, the principal visual approach and the reason for it, and the roles of footage, stills, generated scenes and graphics in this film. "
     "The plan's foundation.treatment starts with it word for word, unchanged unless the operator approves a new treatment.",
     ['P19.0', 'P19.1']),
    ("A palette or \"documentary mix\" alone is not a direction.", ['P19.2']),
    (U('P19.3'), ['P19.3']),
    (U('P19.4'), ['P19.4']),
    ("There is no quota of AI video, footage or graphics: a technical record may lean on graphics, a human story on scenes; say in the direction which the film is and why.",
     ['P19.5', 'P19.6']),
    ("In a film with no footage the direction also holds the film's one look (colours, contrast, light), approved once; every rule of the plan that reads the footage beside a gap then reads this look.", []),
], [
    (U('P22.0'), ['P22.0']),
    (U('P22.1'), ['P22.1']),
    (U('P22.2'), ['P22.2']),
    (U('P22.3'), ['P22.3']),
    (U('P22.4'), ['P22.4']),
    (U('P24.0'), ['P24.0']),
    (U('P24.1'), ['P24.1']),
    ("Two graphic shots follow each other only when each one passes the test above on its own; then the second shot's `warning_answers` says why it stays a graphic.", ['P24.2']),
    (U('P22.5'), ['P22.5']),
    (U('S1.6'), ['S1.6']),
    ("When a gap has no real footage beside it, propose its look in the treatment: the palette, the contrast, the saturation (muted and true to life by default) and the light "
     "(in a film with no footage, the direction's look); the operator approves it with the treatment.", ['S1.7']),
], [
    ("The treatment is a record, written after the direction to out/visual-treatment.json: one entry per gap: `gap_id`; the words under the gap; "
     "the team's intended visuals for it, cited or departed from with the reason; your proposed picture in one line (`picture`); its route or routes "
     "(footage, still, graphic_sequence, drawn, video); its seconds; for a video gap its segments with their seconds; the images it needs (`images`: one start image per video segment, "
     "plus an end image only where the final state must be exact); for every graphic what it depicts (`depicts`), so the operator approves it before anything is drawn; "
     "for every gap its `activity_level` (quiet, normal or busy); and `frozen_seconds`, the seconds of the gap held without movement (usually 0).",
     ['P20.0', 'P20.1', 'S1.0', 'S1.4', 'S1.5', 'P23.6']),
    ("A gap with more than one route lists its shots with their route and seconds (`shots`), so the totals count each route's seconds.", []),
    ("End with your reasons; the server adds the counts per route, the seconds of graphics, the estimated cost against the film's cap, and the film's frozen share against its 10 % limit.",
     ['P20.2', 'S1.1', 'S1.5']),
], [
    ("Send it as the draft: `vw visuals treatment --file out/visual-treatment.json`. The operator reads it on the visuals page (the link is printed), the Direction first, "
     "and accepts or sends back each line, the Direction and every gap, a line sent back with a short note of what to change.",
     ['S1.1', 'P20.1']),
    ("In chat, present it line by line and pass their words: `vw visuals treatment --accept direction,G1,G2 --quote \"<their words>\"`, "
     "`vw visuals treatment --send-back G3 --notes \"<what to change>\"`; their yes to the whole: the draft command again with --quote \"<their yes>\".",
     ['S1.2', 'P20.3']),
    ("A line sent back: revise only that line and send the draft again; accepted lines whose text did not change stay accepted, and a line your revision changed too "
     "(a shared route, the totals) returns to \"to accept\", marked changed. The treatment is recorded when the Direction and every gap are accepted; the plan is checked against it.",
     ['P20.3']),
    ("Nothing else before the recorded treatment: no plan, no picture.", ['S1.3', 'P20.4']),
    (U('P21.0'), ['P21.0']),
    (U('P21.1'), ['P21.1']),
    (U('P21.2'), ['P21.2']),
    (U('P21.3'), ['P21.3']),
]]

SEC['3. THE DETAILED PLAN'] = [[
    ("Order of work. Write the plan to the recorded treatment in three steps (foundation, elements, gaps with scenes, shots, states for every animation shot, beats).", ['S2.0']),
    ("First the shared parts, yourself, in out/plan-base.json: the foundation, the elements, the graphic style, sequence_overview, and `gaps`: the film's gap ids in order.", []),
    ("Then helpers write the gaps at the same time, through your own agents, a few gaps each (start with three or four helpers): each is given out/plan-base.json, the package files, "
     "the recorded treatment and what comes before and after its gaps (the neighbouring gaps' pictures and the people's last state), never another helper's gaps, "
     "and writes its gaps' scenes, shots, states and beats as one file in out/plan-gaps/ (a gap, or {\"gaps\": [...]}); a thing not among the elements goes in that file's "
     "`new_elements` (its id and name), never an invented identity. A short film may be written by you alone the same way.", []),
    ("Then join them: `vw visuals plan-join --base out/plan-base.json --gaps out/plan-gaps/` writes out/visual-plan.json (the gaps in film order, the new things merged once by name; "
     "a gap missing or written twice is refused by name).", []),
    ("`vw visuals check --file out/visual-plan.json` until valid: it sees the whole film, so the rules across gaps are checked there (no picture shown twice, a person's state carried "
     "from shot to shot, the frozen share); fix what it names yourself, or send a gap back to its helper. It prints the routes, the graphic seconds, the images and the cost against the cap.",
     ['S2.2']),
    ("Answer each warning in its shot's `warning_answers` ({kind, answer}), never in the purpose, or change the plan; the purpose stays a clean description of the picture. "
     "The operator sees on the page, with the gap, the plain sentence of each warning that changes what they will see; tell them those in the same plain words in chat, never the technical ones.",
     ['S2.2', 'S2.16']),
    (U('P54.0').replace("(section 1)", "(section B)").replace("continuity with the neighbouring real pictures", "continuity with the neighbouring pictures"), ['P54.0']),
    ("`vw visuals propose --file out/visual-plan.json`: refused until the treatment is recorded, when a gap's route departs from it, and when foundation.treatment does not start with the direction; "
     "`vw visuals select --gap G --choice C` where you offered a choice; the operator accepts each gap on the page, or in chat `vw visuals accept --gaps all --quote \"…\"` (or the gaps they named).",
     ['S2.3', 'P20.4']),
    ("Then read every gap's words in `vw visuals status` before any picture: words asking for a change are a revision, not a yes, and so is a gap sent back "
     "(Revise on the page, or `vw visuals revise --gap G --notes \"…\" --quote \"…\"` on the operator's words): change that gap's treatment entry and plan (one helper for one gap), "
     "propose the next version and have it accepted afresh; generate nothing for it until then. Accepted gaps stay accepted unless they changed.",
     ['S2.4', 'S2.5', 'P26.2']),
], [
    ("The foundation. The foundation is a practical casting and production-design brief for pictures still to be made; foundation.treatment starts with the recorded direction, word for word.",
     ['P35.0', 'P19.1']),
    ("Keep its categories separate, one topic per rule, each with id, statement, scope and source: world (the shared reality: place and period, people and their work, wardrobe, environment, "
     "materials, tools, signage and language, the process; short positive statements, only what this film needs, no invented region or dress); exclusions (the concrete visual and storytelling "
     "consequences of the chosen direction, each naming what a reviewer could detect and which decision it protects; not a generic negative list, and never a ban on a medium because one option "
     "was rejected); specifications (resolution, aspect, frame rate, duration); production_constraints (the narration and the first cut are preserved); editing_constraints (previously rejected "
     "pictures and their intervals); appearance (the shared photographic or graphic style, colour and lighting; its texture line, sharp or soft, comes from the recorded footage character in "
     "the package, measured from the clips, never from an assumption, and the operator's correction wins; in a film with no footage, from the direction's look).",
     ['P35.1', 'P35.2', 'P35.3', 'P35.4', 'P35.5', 'P35.6', 'P35.7', 'P35.8', 'P35.9', 'P35.10', 'P35.12']),
    (U('P35.13'), ['P35.13']),
    (U('P35.14'), ['P35.14']),
    (U('P34.0') + ' ' + U('P34.1') + ' ' + U('P34.2'), ['P34.0', 'P34.1', 'P34.2']),
    (U('P34.3'), ['P34.3']),
    ("Write sequence_overview, before the detailed gaps, as a short account of the progression the treatment set: what each gap adds to the film.", ['P25.0']),
    (U('P26.0'), ['P26.0']),
    (U('P26.1'), ['P26.1']),
    (U('P33.10'), ['P33.10', 'S2.31']),
], [
    ("Meaning. " + U('P33.0'), ['P33.0']),
    (U('P33.1'), ['P33.1']),
    (U('P33.2'), ['P33.2']),
    (U('P33.3'), ['P33.3', 'S2.25']),
    (U('P33.4'), ['P33.4', 'S2.25']),
    ("Each claim has its kind (`claim`: visible, a camera could film it, so footage first; invisible, a graphic may show it).", ['S2.37', 'S2.38']),
    (U('P33.5'), ['P33.5', 'S2.26']),
    ("An unknown fact is never invented: frame the shot wider or ask the operator (the check refuses an MCU, CU or ECU whose subject rests on an unknown fact).", ['P33.6', 'S2.27']),
    ("A shot that is the next step of a process, its subject acting on the work, names what the step before left (`carries_over`); steps of one process share one place, light and crew; "
     "a figure of speech in the narration (\"on top of that\", \"once\") is not a process.", ['P33.8', 'S2.30']),
    (U('P33.12'), ['P33.12', 'S2.31']),
], [
    ("Elements. Derive the named elements from the planned shots, secondary subjects, the named background workers and props included; for each, say whether its identity is exact "
     "(the same individual, object or place across appearances) or representative, and list the views needed.", ['P39.0', 'P39.4']),
    ("Anything specific to the client that the footage shows (a wall pattern, a product, a tool, a uniform) is an element of its own, kind object, identity exact, its footage frames as its views, "
     "its description once in the foundation's world rules as exact text every prompt reuses; before its golden picture exists, a picture of it sends one of those frames as a parent, "
     "never words alone; afterwards the golden picture carries it.", ['P39.1', 'P39.2', 'P39.3']),
    ("A thing whose fact or size cites the footage (a clip, or a frame of one; a maker's \"door frame\" is not footage) is `identity: exact` and has an approved footage frame before any "
     "picture of it (the plan warns, the server refuses); a thing with a frame and a size still unknown is measured first (`vw visuals measure`) and the value put in the plan as measured.",
     ['S3.79']),
    ("A material or a process the film relies on is an element of its own (kind material or process), and so is every tool in a holding or props list (kind object) and every technique "
     "a beat names as its working action (kind technique: pointing, plastering, welding and the like; a gesture or a tool's name is not one: \"points at the crack\", \"picks up the drill\"); "
     "each joins the reference round. The check refuses a plan without them (`status.needed_elements` lists them): add what it names.", ['P33.7', 'P36.17']),
    ("Give every person, object, animal and material its real size (`size`: height, width, depth or length, each with its source and status), from the client's material, `measure` on "
     "footage frames, or a maker's sheet; unknown when none, never invented.", ['S3.48']),
    ("When a shot's claim or descriptor is about its subject's own size, amount or scale, the subject carries a size value and the shot names `compare_to`, a thing in frame to read it against; "
     "a graphic or drawn shot shows size by its figures and needs neither, nor does a word such as light, less, fewer or short that is not about the subject's size.", ['P36.18', 'P36.19']),
    ("Every person element carries `description`, its fixed layer (build, age, skin, hair, posture, garment types and how worn), and every scene that shows a person gives `outfit` "
     "(person id to the garment colours of that scene), with `time_jump` (the script's words) when the colours change from the scene before; the check refuses a plan without them.",
     ['P36.20', 'P36.21']),
    ("Two people in one film wear clothes of different colour families, unless the footage or the brief fixes their clothes (a uniform).", ['S3.47']),
    ("Where a real person is required speaking on camera, it is the real person, never an AI lookalike: offer non-speaking angles of them (listening, hands at work, profile, from behind) "
     "from their own footage only; no AI picture of an identified speaker.", ['S2.39']),
], [
    ("Scenes and life. " + U('P36.0'), ['P36.0']),
    ("Every scene states its activity level (`activity_level`: quiet, normal or busy) from the narration and the brief; a normal or busy scene has the life the narration implies: "
     "who else is there and what they do, and the working equipment.", ['P36.2', 'S2.31']),
    ("Up to three background people are named workers: elements with beats (no reference sheet unless they have a source picture); more than three are a crowd: the scene's ambient line "
     "plus one `groups` entry on the shot (the count and a few traits used in turn), never named elements. A passer-by without beats lives only in the scene's words (its ambient line), "
     "different in every scene.", ['P36.1', 'S3.80']),
    ("Plan beats for every visible person, animal or object that acts: the primary and secondary subjects and the named background workers; a still subject holds, with its reason and unchanged state.",
     ['P36.1']),
    ("A living thing that is not the actor, standing in a normal or busy scene, moves a body-length by the end; one that rightly stays put (seated, listening, bent over its own work, asleep) "
     "holds, with `hold_reason` naming its small life (breathing, a head turn, the hands).", ['P36.10']),
    (U('S2.1').split('; the server writes')[0] + '.', ['S2.1']),
    ("Every AI still and take sits in the film's world, matched to the footage beside it (the packet's footage neighbours; in a film with no footage, the direction's look): give each scene "
     "its light once (`light`: the sources against the landmarks, the main one, hard or soft, colour, strength) and its air (dust, smoke, haze, steam, or clean), and name the scene's light "
     "word for word in the prompt (soft overcast light, muted greens).", ['S2.35', 'P33.9']),
    (U('S2.33'), ['S2.33']),
    ("Work leaves traces: tools, offcuts, mortar droppings, footprints on an active site; signs of use in a finished house. A place the film shows carries `signs_of_use` (two or more traces "
     "of work or living, each at one of its landmarks); a place the treatment approved clean (a show home at handover, a new empty room, a product in a showroom) says so in `staged_clean`, "
     "with the reason, and needs none.", ['S2.34', 'P36.26']),
    ("Several of a kind in one frame (an object counted above one, or the framing's own word: workers, people, cows; not a word the framing denies, as in \"no workers yet\") are a `groups` "
     "entry on the shot, `same` with the reason or `different` with one trait per head.", ['P36.23']),
], [
    ("Positions, states and beats. " + U('P36.3'), ['P36.3', 'S2.31']),
    (U('P36.4'), ['P36.4']),
    ("Every subject has a role, a screen position, start and end states relative to a landmark, facing, pose, held objects and work progress; the check refuses what is missing or vague: "
     "a position is its landmark plus a measured `amount` and `unit` the picture shows (bricks, paces, body-lengths, a hand, a doorway), never 'the centre' or 'nearby' alone; `facing` is "
     "a heading (`landmark_id`, `edge` of the frame, `camera_side`); `objects` lists the movable things in frame with `count` and `place`, the end being the start after the action, every "
     "changed count named in `changes`; every held tool is a `props` entry with its `holder`, its start place and its `end` (in_hand, set_down with a position, or carried_out with a cause); "
     "every beat carries `done`, its action in the past tense.", ['P36.5', 'P36.6', 'P36.7', 'P36.8', 'P36.9']),
    ("A person's every state carries `gaze` (target: a landmark, a named person, or `camera` for a look into the lens; head_turn; mouth) unless the shot's `face_in_frame` is false "
     "(a back view, hands in close); a shot whose only change is a look is better planned as a profile or a back view.", ['P36.11', 'P36.12', 'P36.13']),
    ("Every video shot names its `fixed` things: three landmark ids in frame (fewer when fewer are in frame, down to none at MCU or closer), the built and grown things that never change in the shot; "
     "a carriable thing is an object, never fixed.", ['P36.14', 'P36.15']),
    (cap(U('P36.33')) + ' ' + U('P36.34'), ['P36.33', 'P36.34']),
    ("Each beat carries `min_s`, the realistic time its action takes (laying one brick, about 3 s); the check refuses a beat shorter than its action and a shot whose actions cannot fit its "
     "seconds: drop an action or split the shot.", ['P36.35', 'S2.24']),
    ("Every video shot in which a subject acts lists its `changes`: what differs between its start and end picture, and the `beat_id` of the beat that causes it; a shot where only the "
     "ambient moves (fronds, steam) lists none.", ['S2.24']),
    (U('P36.36'), ['P36.36']),
    ("You write the picture, the server writes the rules: from these fields it writes under your prompt and into the motion text the start and end targets (cause, path, result), "
     "the heading, tool and inventory lines, how a thing set down sits (from the facts and the material spec), the sizes with the true-sizes must, the person line (both layers) with the "
     "garment negatives in the not-this line, the groups line (all alike / no two alike) with two must lines, two signs of use per shot with the must 'the place looks occupied or in use' "
     "('clean and unused, as planned' for a place approved clean), the ambient line in every take, and the measured real-light line (composed once per run from the footage character and "
     "the measured light of the approved footage frames) with the light-and-colour line against the footage beside the gap as a must; it checks every start, end and take against them, "
     "marks a large jump in light and colour, and, when a picture with background people or animals is approved, compares its figures with the scene's approved pictures "
     "(`status.figure_repeats` names a repeat to reimagine).",
     ['P36.32', 'P36.16', 'P36.19', 'P36.22', 'P36.24', 'P36.25', 'P36.27', 'P33.11', 'S2.1']),
    ("Show scene entry and exit through the first and last shot and explain in `boundary_continuity` the continuity with the neighbouring pictures on both sides, footage or planned "
     "(at the film's start or end, the one side there is).", ['P36.37']),
], [
    ("Timing and movement. " + U('S2.7'), ['S2.7']),
    (U('S2.8'), ['S2.8', 'P36.41']),
    ("Shots run two to eight seconds as a rule (AI video at least 3 s and at most 10 s, 3–5 s inside an AI run), with no mechanical equal cuts.", ['P36.38', 'P36.43']),
    ("Consecutive AI video in a gap under 12 s (ai_run): break it with a frame, still or graphic; shots 3–5 s; the same in a film with no footage.", ['P36.39']),
    ("A stretch of real footage in a gap is a footage shot (`visual_type: footage`, placed with `vw visuals clip`): it keeps the timing, crop, reuse and no-repeat rules and none of "
     "those made for generated pictures (still length and motion, the video form, the 10 s limit, the AI run, cost, life, light and camera reason).", []),
    ("Every still and graphic state moves 5 %: set `motion` from the composition (push_in, push_out, pan_left, pan_right; graphics push_in only); `none` needs `motion_reason`.",
     ['S2.9', 'P36.40']),
    (U('S2.10'), ['S2.10', 'P36.40']),
    (U('S2.11'), ['S2.11']),
    ("A graphic stays on screen long enough to read its text twice: at least three seconds for a label or one number; a diagram that builds fits within the 8 s a run of graphics may last, "
     "and a run of graphics over 8 s is broken with a camera shot.", ['P36.43']),
    ("Each shot has its size (EWS, WS, MWS, MS, MCU, CU, ECU: a new place opens wide, a close-up comes after the subject is seen wider (the footage beside the gap counts as that wider view "
     "when the scene continues its place), a reveal is stated in size_reason) and its camera_reason (what the viewer should feel or read, and why this angle, size and move give it: "
     "eye level is honest, low is powerful, high is vulnerable, a slow push draws in; no angle has one fixed meaning).", ['S2.36', 'S2.37']),
    (U('P33.13'), ['P33.13', 'S2.32']),
    (U('P33.14'), ['P33.14', 'S2.32']),
    (U('P33.15'), ['P33.15', 'S2.32']),
    ("The film never shows one picture twice: a clip already on screen, in the first cut or here, is a reuse, and a frozen frame of a clip that plays elsewhere is never shown; "
     "two shots never share a start image or a still.", ['S2.12', 'S2.15', 'P36.42']),
    (U('S2.13'), ['S2.13', 'P36.42']),
    (U('S2.14'), ['S2.14', 'P36.42']),
    ("The check warns on cuts off a pause, pictures off their words, long stills, the frozen share and pictures that look alike.", ['S2.16']),
], [
    ("Graphics. " + U('P23.0'), ['P23.0']),
    (U('P23.2'), ['P23.2']),
    (U('P23.3'), ['P23.3', 'S2.28']),
    (U('P23.4') + ' Each state names its `words` and starts on them.', ['P23.4', 'P23.12', 'S2.17', 'S2.29']),
    (U('P23.5'), ['P23.5', 'S2.28']),
    (U('P23.7').rstrip('.') + ', each in the answer\'s exact text (section B).', ['P23.7', 'S2.32']),
    (U('P23.9'), ['P23.9', 'S2.32']),
    (U('P23.10'), ['P23.10', 'S2.17']),
    ("One graphic style per film, foundation.graphic_style (palette from the client card, line weight, labels, background, frame fill), made once, first, as a style sheet "
     "(`vw visuals image --element _STYLE --kind style --answer …`), approved, and named in the --parents of every graphic's first (or only) picture; later states inherit it through the chain; "
     "every picture and every take carries its --answer.", ['P23.11', 'S2.17', 'S2.22']),
    ("The check warns on missing claims, style, spec approval or answer forms.", ['S2.23']),
], [
    ("Drawing specs. A drawing of a real object carries a `drawing_spec`: its parts, its relationships, each size with its status (confirmed: the client's source; measured; unknown) and its source; "
     "it names its `view` (cutaway, plan, side or elevation) with `view_reason`, a section defaulting to cutaway, and the finished drawing is checked for that view. An idea graphic that names "
     "no real object and no figure (heat leaving a house) needs none.", ['P23.13', 'S2.18', 'P36.30']),
    ("Before a spec is shown, research it: fill every size it depends on from the sources, in this order: the client's own material; the footage, measured (`vw visuals measure --refs F1 F2 "
     "--question \"<what to measure>\"` on approved footage frames, each number keeping its clip and time; paid: announce it, never ask); a standard or a maker's sheet on the web, with its URL "
     "and figure (one warning and one yes covers every web figure of the run); an approved reference picture for a shape numbers cannot hold. Each value carries its source and status.",
     ['S2.19', 'S2.20', 'S2.40', 'S2.41', 'P23.13']),
    (U('S2.42').split(';')[0] + '.', ['S2.42']),
    ("A size is `unknown` only after all four sources were tried, recorded in `tried` with why each failed; it has no value and is never invented, and its drawing or material spec "
     "carries `illustrative: true` (never when nothing is unknown): the drawing reads \"illustrative, not to scale\", no numbers printed, never free proportions.",
     ['S2.43', 'S2.18', 'P23.13', 'P36.28', 'S2.42']),
    (U('P36.29').rstrip(';') + '.', ['P36.29']),
    (cap(U('P36.31')), ['P36.31']),
    ("The operator is never asked to type a size: they approve every spec of the run in one table (`vw visuals spec` with no --shot, or the page), or send a correction "
     "(`vw visuals spec --shot S --notes \"…\"`; it shows under `spec_corrections` in `vw visuals status`), which you fold into the plan with `planning revise` before they approve; "
     "an approval is refused while a correction waits; a single late spec alone: `vw visuals spec --shot S --quote \"…\"` (or on the page).", ['S2.44', 'S2.21', 'P23.14']),
]]

SEC['4. THE PICTURE SEARCH'] = [[
    ("The references are one round for every element of the plan at once (people, objects, places, and the materials and processes the film relies on), never one element at a time. "
     "`vw visuals elements` shows where each is seen in the footage (work/visuals/elements.json); grab a frame for every element the footage has (`vw visuals frame --file`, free); "
     "write out/reference-round.json, one row per element: element_id, its frame reference ids, the two-to-six-word keywords you would search; send it with "
     "`vw visuals round --file out/reference-round.json` and give the operator the page link once.",
     ['S3.0', 'S3.1', 'S3.2', 'S3.3', 'S3.4', 'S3.17']),
    ("Gather only the references the plan needs, per element in this order: a frame from a clip; the operator's own picture (`supply`); for what the footage lacks, Google Images on the "
     "operator's yes (the round's searches); then a picture made by the picture AI, after the round (section 5).", ['P39.6', 'P41.0', 'S3.19']),
    ("A frame from a clip is free and exact, its source and time kept (`vw visuals frame --element E --clip <id> --at <seconds>`): search the clip analyses first, including footage not used "
     "in the edit (editorial non-selection is not a prohibition, the operator's explicit exclusions are); grab the sharpest frame, the subject large and evenly lit, never a blurred frame as "
     "an identity source.", ['P40.0', 'P40.1', 'S3.19', 'S3.46']),
    ("A footage frame or a web picture of a person is a reference for your description of them only, never sent to the picture AI (a footage frame may still be a video take's start image); "
     "a web search for a person or character not in the footage serves that description.", ['P40.2', 'S3.34']),
], [
    ("`vw visuals status --wait 900` until the round is complete. On pass 1 the operator answers every thing: use the footage picture, Search (each thing's own button: the plain search and, "
     "with the source word, a stock search beside it, every picture downloaded at once), or Ignore this; Done waits until every thing set to Google is searched. On pass 2 every searched "
     "thing gets a tick with notes, new words and Search again, or Ignore this; Done waits for all of them. Ask nothing per element and generate nothing meanwhile.",
     ['S3.5', 'S3.6', 'S3.7']),
    ("With a source two searches come back, the plain one and the stock one; the ten pictures go to the visuals page, where the operator ticks and notes them. "
     "The picked pictures are approved when saved: show them, and reject one only if the saved file is not the picture ticked. "
     "A \"nothing fits\" reason joins the element's not-this list, and the next search is the operator's own words (or Ignore this), never yours.",
     ['S3.21', 'S3.22', 'S3.23', 'S3.24']),
    ("An operator who answers in chat: `vw visuals search --element E --keywords \"<two to six words: the thing and its place or trade>\" --source <stock site, outside the six words; "
     "empty for the plain search alone> --quote \"<their yes>\"` for each thing they send to Google; `vw visuals pick --search S --n 2,5 --note 2=\"…\" --quote \"…\"`; "
     "`vw visuals nothing-fits --search S --reason \"…\"`; or a whole pass at once: `vw visuals round --verdicts out/round-verdicts.json --quote` ({element: {verdict: approve|search|ignore}}), "
     "then `vw visuals round --picks out/round-picks.json --quote` ({search id: [{n, note}], \"ignore\": [elements]}).",
     ['S3.16', 'S3.19', 'S3.20', 'S3.22', 'S3.25']),
    (U('S3.8') + ' ' + U('S3.9') + ' ' + U('S3.10') + ' ' + U('S3.11'), ['S3.8', 'S3.9', 'S3.10', 'S3.11']),
    (U('S3.12') + ' ' + U('S3.13') + ' ' + U('S3.14'), ['S3.12', 'S3.13', 'S3.14']),
    ("When the round is complete, the references made by the picture AI, the sheets and the golden pictures follow (sections 5 and 9).", []),
]]

REMOVED = {
    'S2.6': 'removed: a sub-heading of the old step list ("Timing, movement and no repeats."); section 3 has its own sub-headings',
    'P23.1': 'removed: duplicate; how a state is made is in section B (an AI graphic sequence: each state made from the previous one) and the state command in section 9, word for word',
    'P23.8': 'removed: duplicate of section B ("Put every label, number and caption in the answer\'s `exact_text` …"); section 3 points to it',
}

# notes per old unit for the trace: which decision or approved fix rewrote it (otherwise "merged" or "kept")
WHY = {
    'P19.1': 'Change 3: the directing brief is written first, as the treatment\'s `direction`; foundation.treatment starts with it word for word',
    'P19.2': 'Change 3: "treatment" became "direction"', 'P19.6': 'Change 3: said in the direction',
    'P20.1': 'Change 6: on the page per line (Accept / Send back); merged with the step copy', 'P20.3': 'Change 6: per-line --accept / --send-back; the whole-yes path kept',
    'S1.1': 'Change 6; the totals added by the server', 'S1.2': 'Change 6: per line in chat', 'P20.4': 'one line with the propose refusals (section 3) and "nothing else before" (section 2)',
    'P24.2': 'Change 7: the reason goes in warning_answers, never in the purpose', 'S1.7': 'film-type item 13: in a film with no footage, the direction\'s look',
    'S2.2': 'Change 7: answers in warning_answers; Change 8: the operator sees the plain sentences', 'S2.16': 'Change 7 (answer place); the list of warnings kept',
    'S2.0': 'Change 9: base, helpers, plan-join', 'S2.3': 'one line: propose and its refusals (with Change 3\'s start-with-the-direction refusal)',
    'P35.11': 'preparation: the footage line told at prepare', 'P35.12': 'kept in the appearance rule', 'P35.9': 'film-type item 13: no-footage condition added',
    'P36.1': 'decision (a): up to three background people are named workers; more are a crowd', 'S3.80': 'decision (a); merged with the guide copy',
    'P36.10': 'film-type item 3: a holding subject keeps its place with hold_reason', 'P36.11': 'film-type item 17: gaze target `camera`',
    'P36.14': 'film-type item 16: only landmarks in frame; fewer down to none at MCU or closer', 'P36.17': 'film-type item 5: only a working action is a technique',
    'P36.18': 'film-type item 6: about the subject\'s own size; graphics and drawn shots exempt', 'P36.23': 'film-type item 9: a word the framing denies is not a group',
    'P36.26': 'film-type item 4: `staged_clean`', 'S2.34': 'film-type item 4; merged with the guide copy',
    'P36.37': 'dead weight: boundary_continuity is "the neighbouring pictures, footage or planned"', 'P33.6': 'film-type item 8: refusal on MCU/CU/ECU of the subject\'s unknown fact',
    'S2.27': 'film-type item 8', 'P33.8': 'film-type item 20: a figure of speech is not a process', 'S2.30': 'film-type item 20',
    'S2.24': 'film-type item 10: changes only when a subject acts', 'P33.9': 'film-type item 13: no-footage condition', 'S2.36': 'film-type item 11: the footage beside the gap counts as the wider view',
    'S3.47': 'film-type item 18: "or the brief fixes their clothes (a uniform)"', 'S2.39': 'decision (c): a real speaker only from their own footage; no AI picture of an identified speaker',
    'S3.79': 'film-type item 21: "footage" means a clip, not the word "frame"', 'P36.39': 'decision (d): kept, also in a film with no footage',
    'P36.43': 'decision (b): "six to ten seconds for a diagram that builds" brought in line with the 8 s run limit',
    'P23.13': 'film-type item 19: an idea graphic needs no drawing spec; merged with the step copies', 'S2.18': 'film-type item 19; merged',
    'P40.2': 'decision 5 (and SK\'s yes on a footage frame as a video start image); "the image models refuse to edit it" replaced by the decided reason',
    'S3.34': 'decision 5; duplicate of the guide copy', 'S3.19': 'A3 item 10 order kept; decision (e) for people',
    'P54.0': 'pointer "(section 1)" now "(section B)"; "real pictures" now "pictures" (dead weight: a gap may sit beside planned pictures)',
    'P39.0': 'background workers per decision (a); the sheet note moved to the background-workers sentence',
}

HEAD = ("VW-PROCEDURE — for the assistant only, never for the operator.\n\n"
        "VW-VISUALS v2.0 — direction, references, pictures and takes for the blanks of the first cut\n\n"
        "How to read this: sections A to D apply to every step; sections 1 to 4 are the steps up to the picture search, each complete for its step; "
        "sections 5 to 10 are the later steps.")
LATER_HEADS = {38: '5. GENERATED REFERENCES, SHEETS AND GOLDEN PICTURES', 45: '6. SHOT IMAGES AND VIDEO', 53: '7. CHECKS AFTER A TAKE', 57: '8. REVIEW OF A TAKE OR A SEQUENCE'}
STEP_HEADS = {3: '9. THE LATER STEPS, IN ORDER', 6: '10. BRAND'}
CONNECTORS = {'S3.25b': 'References made by the picture AI, the fourth source after the round: '}   # before the generated-image item of the old step 3

NEW_STEPS = [
    "Preparation (prompt.md section 1): `vw visuals prepare`; read prompt.md, gaps.json and intended-visuals.json; give the operator the page link and the footage line.",
    "Treatment (section 2): the direction, then one line per gap in out/visual-treatment.json; `vw visuals treatment --file out/visual-treatment.json` sends the draft; "
    "then `vw visuals treatment --accept … --quote …` or `--send-back … --notes …` per line on the operator's words, until every line is accepted.",
    "The detailed plan (section 3): out/plan-base.json; helpers write out/plan-gaps/; `vw visuals plan-join`; `vw visuals check` until valid; `vw visuals propose`; "
    "the operator accepts each gap (`vw visuals accept`); read every gap's words in `vw visuals status`.",
    "The picture search (section 4): `vw visuals elements`; `vw visuals frame --file`; out/reference-round.json; `vw visuals round`; `vw visuals status --wait 900`, writing the drafts meanwhile; "
    "then the drafts' questions as one list.",
    "References made by the picture AI, reference sheets and golden pictures: sections 5 and 9.",
    "Shot pictures and videos: sections 6 and 9; the checks after a take: section 7.",
    "Review and record: sections 8 and 9 (`vw visuals record`, then `vw next`).",
    "Brand: section 10.",
]


def build():
    lines = HEAD.split('\n')
    p = OLD_ST['prompt'].split('\n')
    common = [('A. STOP AND ASK, NEVER GUESS', [5]), ('B. WHAT THIS STAGE MAKES', [8, None, 10, 11, 12, 13, 14, 15, 16]),
              ('C. PLAIN LANGUAGE', [29, 30]), ('D. PAID STEPS AND THE CAP', [49])]
    for head, idx in common:
        lines += ['', head] + [('' if i is None else p[i]) for i in idx]
    for head, paras in SEC.items():
        lines += ['', head] + [' '.join(t for t, _ in para) for para in paras]
    later = []   # (heading or None, paragraph)
    for li in range(38, len(p)):
        if li in LATER_HEADS:
            later.append(('', LATER_HEADS[li]))
        txt = ''.join(u for uid, u, line, s in ROWS if s == 'P' and line == li and TAG.get(uid) == 'X')
        if txt.strip():
            later.append((None, txt))
        elif li == 50 and later:   # the blank line before the library paragraph
            later.append((None, ''))
    for si in range(3, len(OLD_ST['steps'])):
        if si in STEP_HEADS:
            later.append(('', STEP_HEADS[si]))
        txt = ''.join(CONNECTORS.get(uid, '') + u for uid, u, line, s in ROWS if s == 'S' and line == si and TAG.get(uid) == 'X')
        later.append((None, txt.rstrip()))
    later = [(h, t.rstrip()) for h, t in later]   # the old separators' trailing spaces only
    for head, txt in later:
        lines += ['', txt] if head == '' else [txt]
    return '\n'.join(lines), NEW_STEPS


def section_text(prompt, start, end):
    a = prompt.index('\n' + start + '\n')
    b = prompt.index('\n' + end + '\n') if end else len(prompt)
    return prompt[a:b]


NUMWORDS = r'\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|sixteen|twenty|thirty)\b'


def numbers(text):
    return Counter(re.findall(r'\d+(?:[.,:]\d+)?', text) + [w.lower() for w in re.findall(NUMWORDS, text, re.I)])


# numbers that are fewer in the new four-phase text, with the reason (anything else fails the check)
NUMBERS_REMOVED = {}
NUMBERS_FEWER = {
    '1.35': 'duplicate merged: the crop limit was written in the guide (section 4) and in step 2',
    '4': 'duplicates merged: labels at least 4 % (guide section 2, step 2), a moving still at most 4 s and a graphic over 4 s (guide section 4, step 2)',
    'six': 'decision (b): "six to ten seconds for a diagram that builds" brought in line with the 8 s limit on a run of graphics',
    'ten': 'decision (b), the same sentence',
}


def check(new_prompt, new_steps):
    report = []
    d3 = json.loads(V3.read_text(encoding='utf-8'))
    d2 = json.loads(V2.read_text(encoding='utf-8'))
    st = next(s for s in d3['stages'] if s['name'] == 'visuals')
    assert st['prompt'] == new_prompt and st['steps'] == new_steps, 'v3.json does not hold the built text'
    assert [s['name'] for s, t in zip(d2['stages'], d3['stages']) if s != t] == ['visuals'], 'a stage other than visuals differs from v2'
    old_other = {k: v for k, v in OLD.items() if k != 'stages'}
    assert {k: v for k, v in d3.items() if k not in ('stages', 'note')} == {k: v for k, v in old_other.items() if k != 'note'}, 'top-level fields changed'
    report.append('JSON loads; only the visuals stage differs from v2')
    # every unit of the four phases is traced
    used = {s for paras in SEC.values() for para in paras for _, srcs in para for s in srcs}
    phase = [uid for uid, t in TAG.items() if t in 'PTLS']
    missing = [uid for uid in phase if uid not in used and uid not in REMOVED]
    assert not missing, ('untraced', missing)
    stray = [s for s in used if TAG.get(s) not in ('P', 'T', 'L', 'S')]
    assert not stray, ('a source outside the four phases', stray)
    report.append(f'{len(phase)} old units of the four phases: every one traced')
    # common and headings word for word
    common = section_text(new_prompt, 'A. STOP AND ASK, NEVER GUESS', '1. PREPARATION')
    for uid, t in TAG.items():
        if t == 'C':
            assert UNIT[uid].strip() in common, ('common unit lost', uid)
    report.append('common part (old sections 0, 1, 3 and the cap paragraph) word for word')
    # the later phases' text byte-identical: the later part is exactly the old X units in order, plus the listed headings and connectors
    later = new_prompt[new_prompt.index('\n' + LATER_HEADS[38] + '\n'):]
    stripped = later
    for h in list(LATER_HEADS.values()) + list(STEP_HEADS.values()):
        stripped = stripped.replace('\n' + h + '\n', '\n', 1)
    for c in CONNECTORS.values():
        stripped = stripped.replace(c, '', 1)
    expect = [u for uid, u, line, s in ROWS if TAG.get(uid) == 'X']
    assert re.sub(r'\s+', '', stripped) == re.sub(r'\s+', '', ''.join(expect)), 'later text differs'
    pos = 0
    for u in expect:
        k = later.find(u.strip(), pos)
        assert k >= 0, ('later unit not verbatim or out of order', u[:80])
        pos = k + len(u.strip())
    report.append(f'later phases: {len(expect)} old units byte-identical, in their old order (headings and {len(CONNECTORS)} connector added between them)')
    # numbers
    old_txt = ' '.join(UNIT[u] for u in phase)
    new_txt = ''.join(section_text(new_prompt, h, n) for h, n in (('1. PREPARATION', '2. TREATMENT'), ('2. TREATMENT', '3. THE DETAILED PLAN'),
                                                                  ('3. THE DETAILED PLAN', '4. THE PICTURE SEARCH'), ('4. THE PICTURE SEARCH', LATER_HEADS[38])))
    fewer = {k: (v, numbers(new_txt)[k]) for k, v in numbers(old_txt).items() if numbers(new_txt)[k] < v}
    absent = sorted(k for k, (o, n) in fewer.items() if n == 0)
    unexplained = [k for k in absent if k not in NUMBERS_REMOVED] + [k for k in fewer if k not in absent and k not in NUMBERS_FEWER]
    report.append('numbers written fewer times (old, new): ' + '; '.join(f'{k} ({o}, {n}): {NUMBERS_FEWER.get(k, "?")}' for k, (o, n) in sorted(fewer.items())))
    report.append('numbers gone from the four phases: ' + (', '.join(f'{k}: {NUMBERS_REMOVED[k]}' for k in absent) or 'none'))
    assert not unexplained, ('a number is gone with no reason', unexplained)
    words = lambda s: len(s.split())
    old_all = OLD_ST['prompt'] + ' ' + ' '.join(OLD_ST['steps'])
    report.append(f'words: prompt+steps {words(old_all)} -> {words(new_prompt + " " + " ".join(new_steps))}; '
                  f'four phases {words(old_txt)} -> {words(new_txt)}; steps {words(" ".join(OLD_ST["steps"]))} -> {words(" ".join(new_steps))}')
    for h, n in (('1. PREPARATION', '2. TREATMENT'), ('2. TREATMENT', '3. THE DETAILED PLAN'), ('3. THE DETAILED PLAN', '4. THE PICTURE SEARCH'), ('4. THE PICTURE SEARCH', LATER_HEADS[38])):
        ph = {'1. PREPARATION': 'P', '2. TREATMENT': 'T', '3. THE DETAILED PLAN': 'L', '4. THE PICTURE SEARCH': 'S'}[h]
        report.append(f'  {h}: old {words(" ".join(UNIT[u] for u in phase if TAG[u] == ph))} words -> new {words(section_text(new_prompt, h, n))}')
    return report


def trace_md():
    where = {}
    for head, paras in SEC.items():
        for para in paras:
            for text, srcs in para:
                for s in srcs:
                    where.setdefault(s, []).append((head, text))
    names = {'P': 'preparation', 'T': 'treatment', 'L': 'detailed plan', 'S': 'picture search'}
    esc = lambda s: s.replace('|', '\\|').replace('\n', ' ')
    out = ['# design/124 Phase B: wording trace (old version 3 → new version 3, stage visuals)', '',
           f'Built by `scripts/b_wording_v3.py` from version 3 at commit {OLD_COMMIT}. One row per old sentence of the four reviewed phases '
           '(a sentence over 70 words is split at each "; "). "P" rows are the old guide (`prompt`, line.unit), "S" rows the old step list (`steps[n]`, step.unit).', '',
           'Not in this table: the common part (old guide sections 0, 1 and 3, and the cap paragraph), kept word for word in sections A to D; '
           'the later phases (old guide 5–8 remainder and the old steps 3–6 remainder), kept word for word in sections 5 to 10 in their old order, with one connector '
           f'added before the old step 3\'s generated-image item: "{CONNECTORS["S3.25b"]}".', '',
           '| Old | Phase | Old sentence | Where it went | New sentence | Why |', '|---|---|---|---|---|---|']
    for uid, u, line, s in ROWS:
        t = TAG.get(uid)
        if t not in ('P', 'T', 'L', 'S'):
            continue
        if uid in REMOVED:
            out.append(f'| {uid} | {names[t]} | {esc(u.strip())} | {REMOVED[uid]} | — | |')
            continue
        dests = where[uid]
        first = dests[0]
        rest = '' if len(dests) == 1 else f' (also merged into {len(dests) - 1} more sentence{"s" if len(dests) > 2 else ""} of {", ".join(sorted({h for h, _ in dests[1:]}))})'
        kind = 'kept' if any(u.strip() == x.strip() for _, x in dests) or any(u.strip() in x for _, x in dests) else 'merged into'
        out.append(f'| {uid} | {names[t]} | {esc(u.strip())} | {first[0]}{rest}: {kind} | {esc(first[1])} | {esc(WHY.get(uid, ""))} |')
    out += ['', '## New sentences with no old source', '']
    for head, paras in SEC.items():
        for para in paras:
            for text, srcs in para:
                if not srcs:
                    why = next((w for k, w in NEW_WHY.items() if text.startswith(k)), '')
                    out.append(f'- {head} ({why}): {text}')
    prompt, steps = build()
    out += ['', '## Script check (python scripts/b_wording_v3.py --check)', ''] + [f'- {line}' for line in check(prompt, steps)]
    return '\n'.join(out) + '\n'


NEW_WHY = {'Then settle the treatment': 'Change 1', 'In a film with no footage': 'Change 3 and film-type item 13', 'A gap with more than one route': 'film-type item 14',
           'First the shared parts': 'Change 9', 'Then helpers write': 'Change 9', 'Then join them': 'Change 9', 'A stretch of real footage': 'film-type item 1',
           'When the round is complete': 'a pointer to the later sections (Change 2: each part self-contained)'}


if __name__ == '__main__':
    prompt, steps = build()
    if '--check' not in sys.argv:
        d = json.loads(V3.read_text(encoding='utf-8'))
        assert V3.read_text(encoding='utf-8') == json.dumps(d, ensure_ascii=False, indent=2) + '\n', 'v3.json is not in the expected layout'
        st = next(s for s in d['stages'] if s['name'] == 'visuals')
        st['prompt'], st['steps'] = prompt, steps
        if 'Phase B' not in d['note']:
            d['note'] += (' Phase B: the visuals text restructured: a common part, one self-contained section per reviewed step (preparation, treatment, the detailed plan,'
                          ' the picture search) with each topic written once, the later steps word for word; design/124 Changes 1, 3, 6-9, SK\'s five decisions and the'
                          ' approved film-type fixes (text side); the steps list points to the sections.')
        V3.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        TRACE.write_text(trace_md(), encoding='utf-8', newline='\n')
    for line in check(prompt, steps):
        print(line)
