"""Combined visual planning. Positions belong to the set, never to the camera."""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .planning.digest import digest


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Rule(Model):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    statement: str = Field(min_length=1, max_length=4000)
    scope: str = Field(min_length=1, max_length=1000)
    source: str = Field(min_length=1, max_length=2000)


class GraphicStyle(Model):   # design/89 C2: one graphic style per film, approved once
    palette: str = Field(min_length=1, max_length=1000)
    line_weight: str = Field(min_length=1, max_length=300)
    labels: str = Field(min_length=1, max_length=500)
    background: str = Field(min_length=1, max_length=500)
    frame_fill: str = Field(min_length=1, max_length=500)


class Foundation(Model):
    treatment: str = Field(min_length=1, max_length=16000)
    appearance: str = Field(min_length=1, max_length=8000)
    world: list[Rule] = Field(default_factory=list, max_length=100)
    exclusions: list[Rule] = Field(default_factory=list, max_length=100)
    specifications: list[Rule] = Field(default_factory=list, max_length=100)
    production_constraints: list[Rule] = Field(default_factory=list, max_length=100)
    editing_constraints: list[Rule] = Field(default_factory=list, max_length=100)
    graphic_style: GraphicStyle | None = None
    studio_background: str = Field(default='', max_length=1000)   # design/91 N9: why this film may show a subject on a plain background; empty: never


class Element(Model):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    name: str = Field(min_length=1, max_length=200)
    kind: Literal['person', 'object', 'place', 'graphic', 'animal', 'material', 'process']   # design/91 N6: a material or a process the film relies on
    identity: Literal['exact', 'representative']
    requirements: str = Field(min_length=1, max_length=4000)
    required_views: list[str] = Field(default_factory=list, max_length=20)
    size: list['Dimension'] = Field(default_factory=list, max_length=20)   # design/103 A5: real size, each with its source and status, never invented


class Position(Model):
    landmark_id: str = Field(min_length=1, max_length=80)
    relation: str = Field(min_length=1, max_length=1000)
    amount: float | None = None   # design/110 F2: the measured distance from the landmark, in a unit the picture shows
    unit: str = Field(default='', max_length=40)   # bricks, paces, body-lengths, hands, a doorway


class Heading(Model):   # design/110 F6: which way the front points, against a landmark and a frame edge, and the side toward the camera
    landmark_id: str = Field(min_length=1, max_length=80)
    edge: Literal['left', 'right', 'top', 'bottom', 'toward camera', 'away from camera']
    camera_side: str = Field(min_length=1, max_length=200)


class ObjectInFrame(Model):   # design/110 F4: a movable thing in the frame, counted and placed
    element_id: str = Field(min_length=1, max_length=80)
    count: int = Field(ge=0)
    place: Position


class State(Model):
    position: Position
    facing: Heading | str   # design/110 F6: a heading on a video shot's subject (the check requires it there); the old free words still load for a still's subject
    pose: str = Field(min_length=1, max_length=2000)
    holding: list[str] = Field(default_factory=list, max_length=20)
    progress: str = Field(min_length=1, max_length=2000)
    objects: list[ObjectInFrame] = Field(default_factory=list, max_length=30)   # design/110 F4


class Beat(Model):
    id: str = Field(min_length=1, max_length=80)
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    action: str = Field(min_length=1, max_length=3000)
    target: str = Field(min_length=1, max_length=1000)
    path: str = Field(min_length=1, max_length=2000)
    result: str = Field(min_length=1, max_length=2000)
    start: State
    end: State
    min_s: float = Field(default=0, ge=0)   # design/91 N2: the realistic minimum time for this action, from the facts of the process
    done: str = Field(default='', max_length=3000)   # design/110 F1: the action in the past tense ('set the third brick on edge beside the second'); the server never invents verb forms


class Subject(Model):
    element_id: str = Field(min_length=1, max_length=80)
    role: Literal['primary', 'secondary', 'background']
    screen_position: str = Field(min_length=1, max_length=1000)
    start: State
    end: State
    behaviour: Literal['acts', 'holds']
    hold_reason: str = Field(default='', max_length=2000)
    beats: list[Beat] = Field(default_factory=list, max_length=100)
    continuity_note: str = Field(default='', max_length=3000)


class GraphicState(Model):
    """design/65: one state of a graphic sequence, an approved still; the states play as a build with holds and dissolves."""
    what_appears: str = Field(min_length=1, max_length=2000)
    hold_s: float = Field(gt=0)
    words: str = Field(default='', max_length=500)   # design/89 C3: the words this state illustrates; it starts on them


class Dimension(Model):   # design/89 D1, D3
    part: str = Field(min_length=1, max_length=200)
    measure: str = Field(min_length=1, max_length=200)
    value: float | int | None = None
    unit: str = Field(default='', max_length=40)
    source: str = Field(default='', max_length=1000)   # the client's material, the footage (clip and time), a standard's URL, an approved picture
    status: Literal['confirmed', 'measured', 'unknown']
    tried: str = Field(default='', max_length=1000)   # design/106 D3: for an unknown size, the sources tried and why each failed


class DrawingSpec(Model):   # design/89 D1: the parts, the sizes with their sources, the relationships that must hold
    parts: list[str] = Field(default_factory=list, max_length=40)
    dimensions: list[Dimension] = Field(default_factory=list, max_length=60)
    relationships: list[str] = Field(default_factory=list, max_length=30)
    label: str = Field(default='', max_length=200)
    proportions: list[str] = Field(default_factory=list, max_length=20)   # design/106 D2: the ratios that matter, always, even on an illustrative drawing


class VisualFact(Model):   # design/91 N6: how something real looks and is done, with its source; an unknown fact is never invented
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    about: str = Field(default='', max_length=80)   # the element it describes
    looks: str = Field(min_length=1, max_length=1000)
    how: str = Field(default='', max_length=1000)
    setting: str = Field(default='', max_length=500)
    tools: str = Field(default='', max_length=500)
    source: str = Field(default='', max_length=1000)   # the client's material, the footage (clip and time), a web source on the operator's yes, an approved picture
    status: Literal['confirmed', 'observed', 'unknown']


class Change(Model):   # design/91 N1: what differs between a take's start and end picture, and the beat that causes it
    what: str = Field(min_length=1, max_length=500)
    beat_id: str = Field(min_length=1, max_length=80)


class PropEnd(Model):   # design/110 F5: where the action leaves a tool
    where: Literal['in_hand', 'set_down', 'carried_out']
    position: Position | None = None
    cause: str = Field(default='', max_length=500)


class Prop(Model):   # design/110 F5: a held tool or prop, a named thing of the shot like a person
    element_id: str = Field(min_length=1, max_length=80)
    holder: str = Field(min_length=1, max_length=80)
    start: Position
    end: PropEnd


class ClaimOut(Model):   # design/89 C1: a claim spoken over a graphic and left out on purpose
    claim: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=1000)


class Shot(Model):
    title: str = Field(default="", max_length=160)
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    visual_type: Literal['image', 'video', 'diagram', 'animation']
    graphic_kind: Literal['diagram', 'chart', 'map', 'title', 'text'] = 'diagram'   # design/96 J2: what a graphic is checked for; leader lines only on a diagram
    narration: str = Field(max_length=12000)
    purpose: str = Field(min_length=1, max_length=4000)
    relation: Literal['illustration', 'explanation', 'evocation', 'counterpoint', 'anticipation', 'bridge', 'context']
    framing: str = Field(min_length=1, max_length=2000)
    camera: str = Field(min_length=1, max_length=2000)
    focus: str = Field(min_length=1, max_length=2000)
    subjects: list[Subject] = Field(default_factory=list, max_length=100)
    element_ids: list[str] = Field(default_factory=list, max_length=100)
    information_progression: str = Field(default='', max_length=4000)
    appearance: str = Field(default='', max_length=2000)
    production_method: str = Field(default='', max_length=1500)
    review_notes: str = Field(default='', max_length=4000)
    states: list[GraphicState] = Field(default_factory=list, max_length=12)   # design/65: an animation shot is two to four states (validate_plan says so in words)
    motion: Literal['push_in', 'push_out', 'pan_left', 'pan_right', 'none'] = 'push_in'   # design/89 B2: a still or a graphic moves 5 % across its shot
    motion_reason: str = Field(default='', max_length=1000)   # why a still stays frozen (`none`)
    return_of: str = Field(default='', max_length=80)         # design/89 H7: the earlier shot whose subject this one shows again, reimagined
    differs_by: str = Field(default='', max_length=1000)      # what is different: angle, distance, moment
    claims: list[str] = Field(default_factory=list, max_length=10)   # design/89 C1: the claims spoken over a graphic, one must line each
    claims_left_out: list[ClaimOut] = Field(default_factory=list, max_length=10)
    drawing_spec: DrawingSpec | None = None   # design/89 D1: a technical drawing of a real object
    changes: list[Change] = Field(default_factory=list, max_length=20)   # design/91 N1: a video shot's change list
    props: list[Prop] = Field(default_factory=list, max_length=20)   # design/110 F5
    fact_ids: list[str] = Field(default_factory=list, max_length=20)   # design/91 N6: the facts this shot rests on
    descriptors: list[str] = Field(default_factory=list, max_length=10)   # design/91 N8: the narration's descriptive words about the subject
    evidence: str = Field(default='', max_length=1000)   # design/91 N17: how the picture shows its claims (a test, a table, the result)
    depicts: str = Field(default='', max_length=500)   # design/91 N10: what a graphic shows, in the subject's own form or as a labelled contrast
    carries_over: list[str] = Field(default_factory=list, max_length=10)   # design/91 N14: what the step before left, still visible
    message: str = Field(default='', max_length=500)   # design/91 N11: the message this shot carries
    adds: str = Field(default='', max_length=500)   # what it adds when it carries a message shown before
    transition_in: Literal['', 'cut', 'dissolve', 'match'] = ''   # design/91 N16: chosen, with a reason; empty: the default (a dissolve at graphics, else a cut)
    transition_out: Literal['', 'cut', 'dissolve', 'match'] = ''   # only on a gap's last shot: into the footage after the gap
    transition_reason: str = Field(default='', max_length=500)
    size: Literal['', 'EWS', 'WS', 'MWS', 'MS', 'MCU', 'CU', 'ECU'] = ''   # design/103 A3: the footage analysis's own words
    size_reason: str = Field(default='', max_length=500)   # a stated reveal or repeat
    camera_reason: str = Field(default='', max_length=1000)   # design/103 A4: what the viewer should feel or read, and why this camera gives it
    claim: Literal['', 'visible', 'invisible'] = ''   # design/103 G2: a claim a camera could film, or one it cannot


class Landmark(Model):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    description: str = Field(min_length=1, max_length=3000)


class Scene(Model):
    title: str = Field(default="", max_length=160)
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    purpose: str = Field(min_length=1, max_length=4000)
    location_time: str = Field(min_length=1, max_length=3000)
    layout: str = Field(min_length=1, max_length=6000)
    landmarks: list[Landmark] = Field(default_factory=list, max_length=100)
    boundary_continuity: str = Field(min_length=1, max_length=4000)
    shots: list[Shot] = Field(min_length=1, max_length=100)
    activity_level: Literal['', 'quiet', 'normal', 'busy'] = ''   # design/91 N4: from the narration and the brief
    ambient: str = Field(default='', max_length=1000)   # design/101 M1: what moves around the action in a take, or 'still'
    light: str = Field(default='', max_length=1000)   # design/103 A1: the sources against the landmarks, the main one, hard or soft, colour, strength
    air: str = Field(default='', max_length=500)   # design/103 A2: what hangs in the air, lit by that light, or 'clean'


class SourceCandidate(Model):
    media_id: str = Field(min_length=1, max_length=100)
    source_name: str = Field(min_length=1, max_length=300)
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    use: Literal['clip', 'still_in_film', 'generation_reference']
    evidence: str = Field(min_length=1, max_length=2000)
    inspected: bool = False


class Choice(Model):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    title: str = Field(min_length=1, max_length=160)
    formats: list[Literal['footage', 'frame_grab', 'ai_image', 'ai_video', 'diagram', 'graphic_overlay']] = Field(min_length=1, max_length=6)
    description: str = Field(min_length=1, max_length=4000)
    why: str = Field(min_length=1, max_length=2000)
    tradeoff: str = Field(min_length=1, max_length=2000)
    source_strategy: str = Field(min_length=1, max_length=3000)
    candidates: list[SourceCandidate] = Field(default_factory=list, max_length=30)
    scenes: list[Scene] = Field(min_length=1, max_length=100)


class Gap(Model):
    title: str = Field(default="", max_length=160)
    gap_id: str = Field(min_length=1, max_length=200)
    intent: str = Field(min_length=1, max_length=6000)
    treatment_fit: str = Field(min_length=1, max_length=4000)
    scenes: list[Scene] = Field(default_factory=list, max_length=100)
    choices: list[Choice] = Field(default_factory=list, max_length=2)
    recommended_choice: str = Field(default='', max_length=80)
    decision_reason: str = Field(default='', max_length=3000)
    source_strategy: str = Field(default='', max_length=3000)
    candidates: list[SourceCandidate] = Field(default_factory=list, max_length=30)


class Plan(Model):
    sequence_overview: str = Field(default='', max_length=12000)
    sequence_rules: list[Rule] = Field(default_factory=list, max_length=100)
    foundation: Foundation
    elements: list[Element] = Field(default_factory=list, max_length=500)
    gaps: list[Gap] = Field(default_factory=list, max_length=500)
    open_questions: list[str] = Field(default_factory=list, max_length=50)
    visual_facts: list[VisualFact] = Field(default_factory=list, max_length=100)   # design/91 N6


def _dimension_needs(label, dims):
    """design/106 D3, D6: an unknown size names what was tried and carries no number; a known one names its source."""
    for d in dims:
        need(d.status != 'unknown' or d.tried.strip(), f'{label}: {d.part} {d.measure} is unknown: record the sources tried and why each failed (tried): '
             'the client material, `measure` on footage frames, a standard or a maker figure, an approved picture (design/106 D3).')
        need(d.status != 'unknown' or d.value is None, f'{label}: {d.part} {d.measure} is unknown; an unknown number is never invented: leave its value empty.')
        need(d.status == 'unknown' or d.source.strip(), f'{label}: {d.part} {d.measure} is {d.status}: give its source (the client, the footage, a standard).')


VAGUE_PLACE = re.compile(r'(?:(?:at|in|to|on)\s+)?(?:the\s+)?(?:centre|center|middle|nearby|near|closer|further|beside|next to|close by)', re.I)   # design/110 F2


def need(value, message):
    if not value:
        raise ValueError(message)


def unique(rows, key, label):
    values = [getattr(r, key) for r in rows]
    need(len(values) == len(set(values)), f'Duplicate {label} identity.')
    return set(values)


MAX_GENERATED_SHOT_S = 30   # design/21 E7: today's AI video tools make at most 30 s per shot; longer blanks are several shots
GRAPHIC_TYPES = ('diagram', 'animation')   # design/65: a diagram is a still, an animation a graphic sequence of stills; both are graphics for the pacing rules
STILL_TYPES = ('image', 'diagram')         # filled by one approved picture (`vw visuals still`)
MIN_STATE_S = 3                            # a state is read, not glanced
MIN_GRAPHIC_S = 3                          # a graphic shorter than this is warned
STILL_MOVING_MAX_S = 4                     # design/89 B1 (SK, 23 Oct): a still that moves, at most 4 s
STILL_FROZEN_MAX_S = 3                     # a still marked motion none, at most 3 s
STATE_MAX_S = 5                            # one state of a graphic, at most 5 s
GRAPHIC_BUILD_S = 4                        # a graphic on screen longer than this is a build of states or a drawn animation
FROZEN_SHARE = 0.10                        # design/89 B4 (SK): warn when frozen pictures pass 10 % of the film
NEXT_RELEASE = ' (warned in this release; refused from the next)'
PAUSE_GAP_S = 0.12                         # design/89 A3: a silence between words this long is a pause a cut may fall in
CUT_TOLERANCE_S = 0.3                      # a cut further than this from a pause is warned
WORD_TOLERANCE_S = 0.5                     # a picture that starts more than this after its words is warned
AI_RUN_S = 12   # design/85 G2: seconds of AI video back to back in one gap before the check warns


def _default_generator():
    from .video_generators import CATALOG, DEFAULT
    default = next(c for c in CATALOG if c['provider'] == DEFAULT['provider'] and c['model'] == DEFAULT['model'])
    longest = max(CATALOG, key=lambda c: c['max_seconds'])
    return default, longest


def route_of(shot):
    return 'video' if shot['visual_type'] == 'video' else 'graphic_sequence' if shot['visual_type'] == 'animation' else 'still'


def routes(plan, fps=25):
    """design/65 B1: every shot is made in the pipeline. Counts and seconds per route (video takes, stills, graphic sequences), the seconds of
    graphics, and the images the plan will need: a start and an end image per video shot, where consecutive video shots in a scene share their
    boundary picture (design/66: a run of n segments needs n + 1), one picture per still, one per state of a sequence."""
    out = {'video': 0, 'still': 0, 'graphic_sequence': 0, 'seconds': {'video': 0.0, 'still': 0.0, 'graphic_sequence': 0.0}, 'graphic_seconds': 0.0, 'images_estimated': 0}
    for gap in plan.get('gaps', []):
        scenes = gap.get('scenes') or []
        if gap.get('choices'):
            chosen = next((c for c in gap['choices'] if c['id'] == gap.get('recommended_choice')), gap['choices'][0])
            scenes = chosen['scenes']
        for scene in scenes:
            segments = 0   # consecutive video shots so far
            for shot in scene['shots']:
                kind = route_of(shot)
                seconds = (shot['end_frame'] - shot['start_frame']) / float(fps)
                out[kind] += 1
                out['seconds'][kind] = round(out['seconds'][kind] + seconds, 2)
                if shot['visual_type'] in GRAPHIC_TYPES:
                    out['graphic_seconds'] = round(out['graphic_seconds'] + seconds, 2)
                if kind == 'video':
                    out['images_estimated'] += 2 if segments == 0 else 1
                    segments += 1
                else:
                    segments = 0
                    out['images_estimated'] += len(shot.get('states') or []) or 1 if kind == 'graphic_sequence' else 1
    return out


STOP_WORDS = {'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'is', 'are', 'it', 'its', 'with', 'for', 'by', 'as', 'at', 'this', 'that', 'be', 'than'}
MESSAGE_REPEAT, MESSAGE_REPEAT_NEXT = 0.6, 0.4   # design/91 N11: shared words between two messages; ponytail: word overlap, a meaning check if it misses


def _tokens(text):
    return re.findall(r"[a-z0-9']+", str(text or '').lower())


def timing_warnings(gap_id, shots, timing, fps):
    """design/89 A3: a cut falls in a pause, never inside a word; a shot's picture is on screen when its words are spoken."""
    words = (timing or {}).get('words') or []
    if not words or not fps or not shots:
        return []
    f, out = float(fps), []
    pauses = [(a['end_frame'] / f, b['start_frame'] / f) for a, b in zip(words, words[1:]) if (b['start_frame'] - a['end_frame']) / f >= PAUSE_GAP_S]
    for sh, nxt in zip(shots, shots[1:]):
        t = sh.end_frame / f
        inside = next((w for w in words if w['start_frame'] / f < t < w['end_frame'] / f), None)
        dist = min((0.0 if a <= t <= b else min(abs(t - a), abs(t - b)) for a, b in pauses), default=None)
        if inside or (dist is not None and dist > CUT_TOLERANCE_S):
            where = f"inside the word '{inside['text']}'" if inside else f'{dist:.1f} s from the nearest pause'
            out.append({'gap_id': gap_id, 'shot_id': nxt.id, 'kind': 'cut_off_pause', 'message': f'the cut from {sh.id} to {nxt.id} at {t:.1f} s falls {where}: move it into a pause between sentences or phrases'})
    flat = [(tok, w) for w in words for tok in _tokens(w['text'])]
    pos = 0   # each shot's words are found after the previous shot's words: the same phrase twice is two places
    for sh in shots:
        want = _tokens(sh.narration)[:3]
        i = next((k for k in range(pos, len(flat) - len(want) + 1) if [x[0] for x in flat[k:k + len(want)]] == want), None) if want else None
        state_start, at = sh.start_frame / f, pos if i is None else i   # design/89 C3: each state of a build starts on the words it illustrates
        for n, st in enumerate(sh.states, 1):
            sw = _tokens(st.words)[:3]
            k = next((x for x in range(at, len(flat) - len(sw) + 1) if [y[0] for y in flat[x:x + len(sw)]] == sw), None) if sw else None
            if k is not None:
                said = flat[k][1]['start_frame'] / f
                if abs(state_start - said) > WORD_TOLERANCE_S:
                    out.append({'gap_id': gap_id, 'shot_id': sh.id, 'kind': 'state_off_words', 'message': f"state {n} of shot {sh.id} starts at {state_start:.1f} s but its words ('{' '.join(sw)}…') "
                                                                                      f'are spoken at {said:.1f} s: change the holds so it appears on them'})
                at = k + len(sw)
            state_start += st.hold_s
        if i is None:
            pos = max(pos, at)
            continue
        pos = max(i + len(want), at)
        spoken = flat[i][1]['start_frame'] / f
        if spoken < sh.start_frame / f - WORD_TOLERANCE_S or spoken >= sh.end_frame / f:
            out.append({'gap_id': gap_id, 'shot_id': sh.id, 'kind': 'words_off_picture', 'message': f"shot {sh.id}: its words ('{' '.join(want)}…') are spoken at {spoken:.1f} s but the shot runs "
                                                                                         f'{sh.start_frame / f:.1f}–{sh.end_frame / f:.1f} s: start the picture on or just before its words'})
    return out


def validate_plan(document, source_gaps, fps=None, film_frames=None, frozen_limit=FROZEN_SHARE):
    plan = Plan.model_validate(document)
    elements = unique(plan.elements, 'id', 'element')
    for e in plan.elements:   # review 27 Oct: an element's sizes (design/103 A5) are checked like a drawing spec's
        _dimension_needs(f'element {e.id}', e.size)
    unique(plan.visual_facts, 'id', 'fact')   # design/91 N6
    facts, ekind = {f.id: f for f in plan.visual_facts}, {e.id: e.kind for e in plan.elements}
    for f in plan.visual_facts:
        need(f.status == 'unknown' or f.source.strip(), f'fact {f.id} is {f.status}: give its source (the client, the footage with clip and time, a standard).')
        need(not f.about or f.about in elements, f'fact {f.id} is about {f.about}, which is not an element of the plan.')
    unique(plan.gaps, 'gap_id', 'gap')
    unique(plan.foundation.world + plan.foundation.exclusions + plan.foundation.specifications + plan.foundation.production_constraints + plan.foundation.editing_constraints + plan.sequence_rules, 'id', 'rule')
    scene_ids, shot_ids, beat_ids = set(), set(), set()
    warnings = []
    placed = []   # (gap_id, shot_id, visual_type, start, end) in film order, for the pacing warnings (design/65 B4)
    frozen, starts, returns = 0.0, {}, []   # design/89 B4, H7
    said = []   # design/91 N11: the counted shots, for the repeated messages
    graphic_seen = False   # design/89 C2
    for gap in plan.gaps:
        need(gap.gap_id in source_gaps, 'Plan names an unknown first-cut gap.')
        window = source_gaps[gap.gap_id]
        if gap.choices:
            need(len(gap.choices) == 2 and not gap.scenes, 'A focused comparison needs a recommendation and an alternative, each with its own scenes.')
            choice_ids = unique(gap.choices, 'id', 'choice')
            need(gap.recommended_choice in choice_ids, 'Recommend one offered choice; this is not user selection.')
            need(not gap.candidates and not gap.source_strategy, 'Keep comparison sources with their corresponding option.')
        else:
            need(gap.scenes and not gap.recommended_choice and not gap.decision_reason, 'A single proposal needs scenes; comparison fields apply only to a focused alternative.')
        for candidate in list(gap.candidates) + [v for c in gap.choices for v in c.candidates]:
            need(candidate.end_s > candidate.start_s, 'Source candidate time window must be positive.')
        counted = next((c.scenes for c in gap.choices if c.id == gap.recommended_choice), None) if gap.choices else gap.scenes   # design/89 B4: the recommended choice counts
        for scenes in ([c.scenes for c in gap.choices] if gap.choices else [gap.scenes]):
            cursor = window['start_frame']
            gap_shots = []
            for scene in scenes:
                need(scene.id not in scene_ids, 'Duplicate scene identity.')
                scene_ids.add(scene.id)
                landmarks = unique(scene.landmarks, 'id', 'landmark')
                if scenes is counted and any(s.visual_type not in GRAPHIC_TYPES for s in scene.shots):   # design/91 N4: life in the frame
                    if not scene.activity_level:
                        warnings.append({'scene_id': scene.id, 'kind': 'activity_missing', 'message': f'scene {scene.id}: state its activity level (activity_level: quiet, normal or busy) '
                                         'from the narration and the brief'})
                    elif scene.activity_level != 'quiet' and not any(sub.role in ('secondary', 'background') for s in scene.shots for sub in s.subjects):
                        warnings.append({'scene_id': scene.id, 'kind': 'life_missing', 'message': f'scene {scene.id} is {scene.activity_level} but shows one subject and no background '
                                         'activity: add who else is there and what they do (secondary or background subjects with beats) and the working equipment'})
                if scenes is counted and any(s.visual_type == 'video' for s in scene.shots) and not scene.ambient.strip():   # design/101 M2
                    warnings.append({'scene_id': scene.id, 'kind': 'ambient_missing', 'message': f"scene {scene.id}: say what moves around the action (ambient): "
                                     "trees, air, people in the background, or 'still'"})
                last_states = {}
                for shot in scene.shots:
                    need(shot.id not in shot_ids, 'Duplicate shot identity.')
                    shot_ids.add(shot.id)
                    need(shot.start_frame == cursor and shot.end_frame > cursor,
                         'Shots must cover their gap in order, without overlaps or missing frames.')
                    cursor = shot.end_frame
                    if fps and shot.visual_type == 'video':   # design/65: an animation is stills now; only a video take has the generator's cap
                        need((shot.end_frame - shot.start_frame) <= MAX_GENERATED_SHOT_S * float(fps),
                             f'A generated shot is at most {MAX_GENERATED_SHOT_S} s; split a longer stretch into several shots.')
                    seconds = (shot.end_frame - shot.start_frame) / float(fps) if fps else None
                    placed.append((gap.gap_id, shot.id, shot.visual_type, shot.start_frame, shot.end_frame))
                    if scenes is counted:
                        said.append(shot)
                    if shot.visual_type == 'animation' and len(shot.claims) > len(shot.states):   # design/91 N12: a build shows every claim it covers
                        warnings.append({'shot_id': shot.id, 'kind': 'build_short', 'message': f'shot {shot.id} covers {len(shot.claims)} claims in {len(shot.states)} states: '
                                         'give each claim its state, so the build shows all of them'})
                    if shot.visual_type == 'animation':   # design/65: a graphic sequence of states
                        if len(shot.states) == 1:
                            need(False, f'shot {shot.id}: one state is a diagram still: plan it as a diagram, or add a state.')
                        need(2 <= len(shot.states) <= 4, f'shot {shot.id}: an animation shot is a graphic sequence of two to four states (`states`).')
                        for n, st in enumerate(shot.states, 1):
                            need(st.hold_s >= MIN_STATE_S, f'state {n} of shot {shot.id} holds {st.hold_s:.1f} s; a state holds at least {MIN_STATE_S} s.')
                        if seconds is not None:
                            total = sum(st.hold_s for st in shot.states)
                            need(abs(total - seconds) <= 0.2, f"shot {shot.id}: the states' holds add up to {total:.1f} s; the shot is {seconds:.1f} s.")
                    else:
                        need(not shot.states, f'states belong to an animation shot (shot {shot.id} is a {shot.visual_type}).')
                    if seconds is not None and shot.visual_type in GRAPHIC_TYPES and seconds < MIN_GRAPHIC_S:
                        warnings.append({'shot_id': shot.id, 'kind': 'graphic_short', 'message': f'shot {shot.id} is a graphic of {seconds:.1f} s: at least {MIN_GRAPHIC_S} s to read it'})
                    if shot.visual_type in STILL_TYPES + ('animation',):   # design/89 B2: graphics move closer only; a frozen still says why
                        need(shot.visual_type not in GRAPHIC_TYPES or shot.motion in ('push_in', 'none'), f'shot {shot.id}: a graphic moves closer only (push_in) or not at all, so its labels never slide out of frame.')
                        need(shot.motion != 'none' or shot.motion_reason.strip(), f'shot {shot.id}: motion none needs a reason (motion_reason).')
                        if seconds is not None and shot.motion == 'none' and scenes is counted:
                            frozen += seconds
                    if seconds is not None and shot.visual_type == 'image':   # design/89 B1 (SK): 4 s moving, 3 s frozen
                        limit = STILL_FROZEN_MAX_S if shot.motion == 'none' else STILL_MOVING_MAX_S
                        if seconds > limit + 0.04:
                            warnings.append({'shot_id': shot.id, 'kind': 'still_long', 'message': f"shot {shot.id} is a {'frozen ' if shot.motion == 'none' else ''}still of {seconds:.1f} s: at most {limit} s; "
                                             'fill the stretch with several different stills or a moving shot (a clip stretch or a take)' + NEXT_RELEASE})
                    if seconds is not None and shot.visual_type == 'diagram' and seconds > GRAPHIC_BUILD_S + 0.04:
                        warnings.append({'shot_id': shot.id, 'kind': 'graphic_unbuilt', 'message': f'shot {shot.id} is one graphic held {seconds:.1f} s: over {GRAPHIC_BUILD_S} s a graphic is a build of 2 to 4 states '
                                         '(an animation shot) or a drawn animation' + NEXT_RELEASE})
                    for fid in shot.fact_ids:   # design/91 N6
                        need(fid in facts, f'shot {shot.id} names the fact {fid}, which the plan does not have.')
                    rests_on = {fid: facts[fid] for fid in shot.fact_ids} | {f.id: f for f in plan.visual_facts if f.about and f.about in shot.element_ids}
                    if 'close' in shot.framing.lower():
                        for f in rests_on.values():
                            need(f.status != 'unknown', f'shot {shot.id} is close on what fact {f.id} describes, and that fact is unknown: it is never invented; '
                                                       'frame the shot wider, or ask the operator.')
                    if any(ekind.get(e) in ('material', 'process') for e in shot.element_ids) and not rests_on:
                        warnings.append({'shot_id': shot.id, 'kind': 'facts_missing', 'message': f'shot {shot.id} shows a material or a process: give the facts it rests on (visual_facts, '
                                         'fact_ids): how it looks and is done, with the source'})
                    if shot.visual_type not in GRAPHIC_TYPES and shot.narration.strip():   # design/91 N8, N17
                        if not shot.claims and not shot.claims_left_out and not shot.descriptors:
                            warnings.append({'shot_id': shot.id, 'kind': 'claims_missing', 'message': f'shot {shot.id}: list the claims and the descriptive words spoken over it (claims, '
                                             'descriptors); the picture never shows their opposite' + NEXT_RELEASE})
                        if shot.claims and not shot.evidence.strip():
                            warnings.append({'shot_id': shot.id, 'kind': 'evidence_missing', 'message': f'shot {shot.id}: say how its picture shows its claims (evidence): a test, a table, '
                                             'or the result in a scene, never an unrelated picture'})
                    if (re.match(r'\s*(then|next|after (that|this)|once)\b', shot.narration, re.I) or re.search(r'\bon top of\b', shot.narration, re.I)) and not shot.carries_over:
                        warnings.append({'shot_id': shot.id, 'kind': 'carries_over_missing', 'message': f'shot {shot.id} is the next step of a process: name what the step before left that '
                                         'must still be visible (carries_over)'})   # design/91 N14
                    if shot.visual_type in GRAPHIC_TYPES:   # design/89 C1, D1, D3
                        if not shot.depicts.strip():   # design/91 N10
                            warnings.append({'shot_id': shot.id, 'kind': 'depicts_missing', 'message': f'shot {shot.id}: say what the graphic depicts (depicts), in the subject\'s own form, '
                                             'or an alternative labelled as the contrast; the operator approves it with the treatment' + NEXT_RELEASE})
                        graphic_seen = True
                        if shot.narration.strip() and not shot.claims and not shot.claims_left_out:
                            warnings.append({'shot_id': shot.id, 'kind': 'claims_missing', 'message': f'shot {shot.id}: list the claims spoken over this graphic (claims), each a must line on its checklist, '
                                             'or name one left out on purpose with the reason (claims_left_out)' + NEXT_RELEASE})
                        if shot.drawing_spec is None:
                            warnings.append({'shot_id': shot.id, 'kind': 'spec_missing', 'message': f'shot {shot.id}: a drawing of a real object (a section, a part, a profile) needs a drawing_spec with '
                                             'its sources; a chart, a timeline or a label needs none: say so in production_method'})
                        else:
                            spec = shot.drawing_spec
                            _dimension_needs(f'shot {shot.id}', spec.dimensions)
                            if not spec.proportions:   # design/106 D2
                                warnings.append({'shot_id': shot.id, 'kind': 'spec_proportions_missing', 'message': f'shot {shot.id}: give the proportions that matter (proportions), '
                                                 'for example a brick about 3 : 1.5 : 1, both leaves the same thickness; "illustrative" means no numbers printed, never free proportions'})
                            if any(d.status == 'unknown' for d in spec.dimensions):
                                need('not to scale' in spec.label.lower(), f'shot {shot.id}: a size is unknown, so the drawing is labelled "illustrative, not to scale" (label) and shows no figure for it.')
                    for n, st in enumerate(shot.states, 1):
                        if st.hold_s > STATE_MAX_S + 0.04:
                            warnings.append({'shot_id': shot.id, 'kind': 'state_long', 'message': f'state {n} of shot {shot.id} holds {st.hold_s:.1f} s: a graphic state holds at most {STATE_MAX_S} s; add a state' + NEXT_RELEASE})
                    if scenes is counted:   # a return names a shot the film shows: the recommended choice, never the alternative
                        starts[shot.id] = shot.start_frame
                    returns.append(shot)
                    gap_shots.append(shot)
                    if shot.visual_type == 'video' and seconds is not None:   # design/45 10.7
                        default, longest = _default_generator()
                        if seconds > default['max_seconds']:
                            warnings.append({'shot_id': shot.id, 'kind': 'length', 'message': f"shot {shot.id} is {seconds:.1f} s; the default generator makes at most {default['max_seconds']} s: "
                                                                                             f"split it, or choose {longest['label'].split(' ·')[0]} (up to {longest['max_seconds']} s) with `vw visuals generator`"})
                    need(set(shot.element_ids) <= elements, 'Shot names an unknown reference element.')
                    subjects = unique(shot.subjects, 'element_id', 'visible subject')
                    need(subjects <= set(shot.element_ids), 'Every visible subject must be a required shot element.')
                    for subject in shot.subjects:
                        states = [subject.start, subject.end]
                        previous = last_states.get(subject.element_id)
                        if previous and previous != subject.start.model_dump() and not subject.continuity_note.strip():
                            warnings.append({'shot_id': shot.id, 'element_id': subject.element_id,
                                             'message': 'Subject state changed between shots; explain the movement, elapsed time or intended discontinuity.'})
                        living = shot.visual_type == 'video' and ekind.get(subject.element_id) in ('person', 'animal')
                        if subject.behaviour == 'holds':
                            need(not subject.beats and subject.hold_reason.strip(), 'A held subject needs its reason, not invented beats.')
                            if living:   # design/110 F6: a living thing that is not the actor still gets its own small change
                                need(subject.start.position != subject.end.position, f'shot {shot.id}: {subject.element_id} is a living thing that stands still from start to end; give it a small move '
                                     '(its end position a body-length or so from its start, against a landmark) (design/110 F6).')
                                need(subject.start.pose == subject.end.pose and subject.start.holding == subject.end.holding and subject.start.progress == subject.end.progress,
                                     'A held subject cannot change what it holds or its progress.')
                            else:
                                need(subject.start == subject.end, 'A held subject cannot change position or progress.')
                        else:
                            need(bool(subject.beats), 'Every acting subject, including background subjects, needs beats.')
                        end = shot.start_frame
                        state = subject.start
                        for beat in subject.beats:
                            need(beat.id not in beat_ids, 'Duplicate beat identity.')
                            beat_ids.add(beat.id)
                            need(end <= beat.start_frame < beat.end_frame <= shot.end_frame,
                                 'A subject cannot perform overlapping beats or actions outside its shot.')
                            need(beat.start == state, 'Beat starting state must continue this subject\'s preceding state.')
                            states.extend([beat.start, beat.end])
                            state, end = beat.end, beat.end_frame
                        if subject.beats:
                            need(state == subject.end, 'Final beat must leave the subject in the shot\'s ending state.')
                        for state in states:
                            need(state.position.landmark_id in landmarks, 'Subject positions must refer to a named scene landmark.')
                            need(set(state.holding) <= elements, 'Held objects must have element identities.')
                            if shot.visual_type == 'video':   # design/110 F2: landmark + measured amount in a visible unit; a vague relation alone is refused
                                pos = state.position
                                need(not VAGUE_PLACE.fullmatch(pos.relation.strip()), f'shot {shot.id}: {subject.element_id}\'s position "{pos.relation}" alone says nothing a picture can place: '
                                     'name the landmark and how far from it (design/110 F2).')
                                need(pos.amount is not None and pos.unit.strip(), f'shot {shot.id}: {subject.element_id}\'s position "{pos.relation} {pos.landmark_id}" needs a measured amount and a '
                                     'visible unit (amount, unit: bricks, paces, body-lengths, a hand, a doorway) (design/110 F2).')
                        if shot.visual_type == 'video':   # design/110 F4, F6: counted objects; a heading on every state
                            for state in states:
                                need(isinstance(state.facing, Heading), f'shot {shot.id}: {subject.element_id}\'s facing is a heading: landmark_id, edge (left, right, top, bottom, toward camera, away from camera) '
                                     'and camera_side, the side that faces the camera (design/110 F6).')
                                need(state.facing.landmark_id in landmarks, f'shot {shot.id}: {subject.element_id}\'s heading names a landmark of the scene (design/110 F6).')
                                for o in state.objects:
                                    need(o.element_id in elements, f'shot {shot.id}: {subject.element_id}\'s objects name elements of the plan ({o.element_id} is not one) (design/110 F4).')
                                    need(o.place.landmark_id in landmarks, f'shot {shot.id}: the place of {o.element_id} names a landmark of the scene (design/110 F4).')
                            before = {o.element_id: o.count for o in subject.start.objects}
                            after = {o.element_id: o.count for o in subject.end.objects}
                            for eid in set(before) | set(after):
                                if before.get(eid, 0) != after.get(eid, 0):
                                    name_ = next((e.name for e in plan.elements if e.id == eid), eid).lower()
                                    need(any(eid.lower() in ch.what.lower() or name_ in ch.what.lower() for ch in shot.changes),
                                         f'shot {shot.id}: {subject.element_id}\'s {eid} goes from {before.get(eid, 0)} to {after.get(eid, 0)} between the start and the end; name the change that does it '
                                         '(changes), so the counts agree with the action (design/110 F4).')
                        if shot.visual_type == 'video':   # design/110 F1: the past tense comes from the plan, never from the server
                            for beat in subject.beats:
                                need(beat.done.strip(), f'shot {shot.id}: beat {beat.id} needs done, its action in the past tense ("set the third brick on edge beside the second") (design/110 F1).')
                        last_states[subject.element_id] = subject.end.model_dump()
                    if shot.visual_type == 'video':   # design/110 F5: every held thing is a prop with a holder and an end
                        held = {h for s in shot.subjects for stt in [s.start, s.end] + [x for b in s.beats for x in (b.start, b.end)] for h in stt.holding}
                        props = {p.element_id: p for p in shot.props}
                        for h in held:
                            need(h in props, f'shot {shot.id}: {h} is held but has no props entry (element_id, holder, start position, end: in_hand, set_down with its position, or carried_out with its cause) (design/110 F5).')
                        for p in shot.props:
                            need(p.holder in {s.element_id for s in shot.subjects}, f'shot {shot.id}: the holder of {p.element_id} is a subject of the shot (design/110 F5).')
                            need(p.start.landmark_id in landmarks and (p.end.position is None or p.end.position.landmark_id in landmarks), f'shot {shot.id}: the places of {p.element_id} name landmarks of the scene (design/110 F5).')
                            need(p.end.where != 'set_down' or p.end.position is not None, f'shot {shot.id}: {p.element_id} set down needs its position (against a landmark) (design/110 F5).')
                            need(p.end.where != 'carried_out' or p.end.cause.strip(), f'shot {shot.id}: {p.element_id} carried out needs its cause (who carries it, where) (design/110 F5).')
                    if shot.visual_type == 'video':   # design/91 N1, N2
                        own = {b.id: b for s in shot.subjects for b in s.beats}
                        for ch in shot.changes:
                            need(ch.beat_id in own, f"shot {shot.id}: the change '{ch.what}' names {ch.beat_id}, which is not a beat of this shot.")
                        if not shot.changes:
                            warnings.append({'shot_id': shot.id, 'kind': 'changes_missing', 'message': f'shot {shot.id}: list what differs between its start and end picture and the beat that '
                                             'causes each (changes); the pair is checked against it' + NEXT_RELEASE})
                        acting = [s for s in shot.subjects if s.behaviour == 'acts']
                        if fps:
                            f, length = float(fps), (shot.end_frame - shot.start_frame) / float(fps)
                            for s in acting:
                                need_s = sum(b.min_s for b in s.beats)
                                need(need_s <= length + 0.04, f'shot {shot.id}: the actions of {s.element_id} need {need_s:.1f} s but the shot has {length:.1f} s: drop an action or split the shot.')
                                for b in s.beats:
                                    have = (b.end_frame - b.start_frame) / f
                                    need(have >= b.min_s - 0.04, f'shot {shot.id}: beat {b.id} ({b.action}) has {have:.1f} s for an action that needs {b.min_s:g} s: give it the time or drop it.')
                        if any(not b.min_s for s in acting for b in s.beats):
                            warnings.append({'shot_id': shot.id, 'kind': 'min_s_missing', 'message': f'shot {shot.id}: give every beat its min_s, the realistic time its action takes, so the shot '
                                             'holds only what fits its seconds'})
                    if not shot.subjects:
                        need(shot.information_progression.strip(), 'Describe the composition or information progression for a shot without acting subjects.')
            last = scenes[-1].shots[-1].id if scenes and scenes[-1].shots else None   # design/91 N16
            for sh in (s for sc in scenes for s in sc.shots):
                need(not sh.transition_out or sh.id == last, f'shot {sh.id}: transition_out is for the last shot of a gap; set the next shot\'s transition_in instead.')
                need(not (sh.transition_in or sh.transition_out) or sh.transition_reason.strip(), f'shot {sh.id}: a chosen transition needs its reason (transition_reason); '
                                                                                            'without a choice, a graphic dissolves 8 frames and everything else cuts.')
            need(cursor == window['end_frame'], 'Planned pictures must cover the exact approved working gap duration. Propose a timing revision before changing it.')
            warnings += timing_warnings(gap.gap_id, gap_shots, window.get('timing'), fps)   # design/89 A3
    said.sort(key=lambda s: s.start_frame)   # design/91 N11: one message once, unless the later shot says what it adds
    words = [set(_tokens(s.message)) - STOP_WORDS for s in said]
    for j, later in enumerate(said):
        if not words[j] or later.adds.strip():
            continue
        for i in range(j):
            overlap = len(words[i] & words[j]) / len(words[i] | words[j]) if words[i] else 0
            consecutive = i == j - 1 and set(said[i].element_ids) & set(later.element_ids)
            if overlap >= MESSAGE_REPEAT or (consecutive and overlap >= MESSAGE_REPEAT_NEXT):
                warnings.append({'shot_id': later.id, 'kind': 'message_repeated', 'message': f'shot {later.id} carries the message of {said[i].id} again '
                                 f"('{later.message}'): merge them into one shot in context, or say what it adds (adds: a number, a cause, a consequence)"})
                break
    # design/65 B4: graphics back to back, inside a gap or across two gaps with no footage between; a gap of several shots that is all graphics
    placed.sort(key=lambda p: p[3])
    for prev, cur in zip(placed, placed[1:]):
        if prev[2] in GRAPHIC_TYPES and cur[2] in GRAPHIC_TYPES and (prev[0] == cur[0] or prev[4] == cur[3]):
            warnings.append({'shot_id': cur[1], 'kind': 'graphics_back_to_back', 'message': f"shots {prev[1]} and {cur[1]} are graphics back to back: the second shot's purpose must say why it stays a graphic"})
    for gap in plan.gaps:   # design/85 G2, G3: a run of AI video over AI_RUN_S in one gap, unbroken by a frame, a still or a graphic
        own = sorted((p for p in placed if p[0] == gap.gap_id), key=lambda p: p[3])
        run_, runs = [], []
        for p in own + [None]:
            if p and p[2] == 'video' and (not run_ or run_[-1][4] == p[3]):
                run_.append(p)
                continue
            if run_:
                runs.append(run_)
            run_ = [p] if p and p[2] == 'video' else []
        for r in runs:
            seconds = (r[-1][4] - r[0][3]) / float(fps or 25)
            if seconds > AI_RUN_S:
                warnings.append({'gap_id': gap.gap_id, 'shot_id': r[0][1], 'kind': 'ai_run', 'message': f"gap {gap.gap_id}: shots {', '.join(p[1] for p in r)} are {seconds:.1f} s of AI video back to back, over {AI_RUN_S} s: "
                                 'break the run with a frame from the footage, a still or a graphic, and cut the AI shots to three to five seconds each; a run that long reads as synthetic'})
    for gap in plan.gaps:
        own = [p for p in placed if p[0] == gap.gap_id]
        if len(own) > 1 and all(p[2] in GRAPHIC_TYPES for p in own):
            warnings.append({'gap_id': gap.gap_id, 'kind': 'all_graphics', 'message': f'gap {gap.gap_id} is {len(own)} shots, all graphics: mix in a frame from the footage or a scene unless each one earns its place'})
    if graphic_seen and plan.foundation.graphic_style is None:   # design/89 C2
        warnings.append({'kind': 'style_missing', 'message': 'the plan has graphics: give foundation.graphic_style (palette from the client card, line weight, labels, background, how the frame '
                                                           'is filled); the operator approves it once as a style sheet picture and every graphic is bound to it' + NEXT_RELEASE})
    for shot in returns:   # design/89 H7: a return is reimagined, with what differs
        if shot.return_of:
            need(shot.return_of in starts and starts[shot.return_of] < shot.start_frame, f'shot {shot.id}: return_of names an earlier shot of this plan ({shot.return_of} is not one).')
            need(shot.differs_by.strip(), f'shot {shot.id} returns to {shot.return_of}: say what differs (differs_by): the angle, the distance or the moment.')
    if film_frames and fps and frozen / (film_frames / float(fps)) > frozen_limit:   # design/89 B4
        share = frozen / (film_frames / float(fps))
        warnings.append({'kind': 'frozen_share', 'message': f'{frozen:.1f} s of frozen pictures, {share:.0%} of the film: over {frozen_limit:.0%}; give the stills movement, '
                                                          'build the graphics, or say why this film needs them still'})
    warnings.extend(course_warnings(plan, fps))   # design/103
    result = plan.model_dump()
    for key in ('sequence_overview', 'sequence_rules', 'visual_facts'):
        if key not in document: result.pop(key)
    for key in ('specifications', 'production_constraints', 'editing_constraints', 'graphic_style', 'studio_background'):
        if key not in document['foundation']: result['foundation'].pop(key)
    for element, original_element in zip(result['elements'], document.get('elements', [])):
        if 'size' not in original_element: element.pop('size')   # design/103: absent stays absent
        for d, od in zip(element.get('size') or [], original_element.get('size') or []):
            if 'tried' not in od: d.pop('tried', None)
    # New presentation fields must not change legacy approval digests when absent.
    for gap, original_gap in zip(result['gaps'], document.get('gaps', [])):
        for key in ('title', 'choices', 'recommended_choice', 'decision_reason', 'source_strategy', 'candidates'):
            if key not in original_gap: gap.pop(key)
        scene_pairs = list(zip(gap['scenes'], original_gap.get('scenes', [])))
        for choice, original_choice in zip(gap.get('choices', []), original_gap.get('choices', [])):
            scene_pairs.extend(zip(choice['scenes'], original_choice['scenes']))
        for scene, original_scene in scene_pairs:
            if 'title' not in original_scene: scene.pop('title')
            if 'activity_level' not in original_scene: scene.pop('activity_level')
            for key in ('ambient', 'light', 'air'):   # design/101, 103: absent stays absent
                if key not in original_scene: scene.pop(key)
            for shot, original_shot in zip(scene['shots'], original_scene['shots']):
                for key in ('title', 'appearance', 'production_method', 'review_notes', 'states', 'motion', 'motion_reason', 'return_of', 'differs_by',
                            'claims', 'claims_left_out', 'drawing_spec', 'changes', 'fact_ids', 'descriptors', 'evidence', 'depicts', 'carries_over', 'message', 'adds',
                            'transition_in', 'transition_out', 'transition_reason', 'size', 'size_reason', 'camera_reason', 'claim'):   # design/89, 91, 103: absent stays absent
                    if key not in original_shot: shot.pop(key)
                if shot.get('drawing_spec') and original_shot.get('drawing_spec'):   # design/106: absent stays absent
                    if 'proportions' not in original_shot['drawing_spec']: shot['drawing_spec'].pop('proportions', None)
                    for d, od in zip(shot['drawing_spec'].get('dimensions') or [], original_shot['drawing_spec'].get('dimensions') or []):
                        if 'tried' not in od: d.pop('tried', None)
                for st, original_st in zip(shot.get('states') or [], original_shot.get('states') or []):
                    if 'words' not in original_st: st.pop('words', None)
                for sub, original_sub in zip(shot.get('subjects') or [], original_shot.get('subjects') or []):
                    for b, original_b in zip(sub.get('beats') or [], original_sub.get('beats') or []):
                        if 'min_s' not in original_b: b.pop('min_s', None)
    return result, warnings


SCENE_NOTES, SHOT_NOTES, ELEMENT_NOTES = ('ambient', 'light', 'air'), ('size', 'size_reason', 'camera_reason', 'claim'), ('size',)   # design/101, 103


def _drop(d, keys):
    return {k: v for k, v in d.items() if k not in keys}


def _note_free_shot(sh):
    out = _drop(sh, SHOT_NOTES)
    if isinstance(out.get('drawing_spec'), dict):   # design/106: a spec's proportions and tried sources are approved with the spec, not the gap
        sp = _drop(out['drawing_spec'], ('proportions',))
        if 'dimensions' in sp:
            sp['dimensions'] = [_drop(d, ('tried',)) for d in sp['dimensions']]
        out['drawing_spec'] = sp
    return out


def note_free_scene(scene):
    return {**_drop(scene, SCENE_NOTES), **({'shots': [_note_free_shot(sh) for sh in scene['shots']]} if 'shots' in scene else {})}


def note_free_gap(gap):
    """design/101, 103: a gap without the notes that need no re-acceptance (ambient, light, air, size, the camera's reason, the claim's kind)."""
    out = dict(gap)
    if gap.get('scenes'):
        out['scenes'] = [note_free_scene(s) for s in gap['scenes']]
    if gap.get('choices'):
        out['choices'] = [{**c, 'scenes': [note_free_scene(s) for s in c['scenes']]} for c in gap['choices']]
    return out


def note_free_elements(elements):
    return [_drop(e, ELEMENT_NOTES) for e in elements]


CLOSE_SIZES, OPEN_SIZES = ('MCU', 'CU', 'ECU'), ('EWS', 'WS', 'MWS')
SIZE_ORDER = ['EWS', 'WS', 'MWS', 'MS', 'MCU', 'CU', 'ECU']


def course_warnings(plan, fps):
    """design/103: the course's planning rules (A1, A3, A4, A5) and design/93 G1, G2, on the counted scenes; warnings only in this release."""
    out = []
    for e in plan.elements:   # A5
        if e.kind in ('person', 'object', 'animal', 'material') and not e.size:
            out.append({'element_id': e.id, 'kind': 'element_size_missing', 'message': f'element {e.id} ({e.kind}): give its real size (size: height, width, depth or length, '
                                                                                       'each with its source and status: confirmed, measured or unknown); never invent one'})
    for gap in plan.gaps:
        scenes = next((c.scenes for c in gap.choices if c.id == gap.recommended_choice), []) if gap.choices else gap.scenes
        run_s, run_ids = 0.0, []
        for scene in scenes:
            if any(s.visual_type not in GRAPHIC_TYPES for s in scene.shots) and not scene.light.strip():   # A1
                out.append({'scene_id': scene.id, 'kind': 'light_missing', 'message': f'scene {scene.id}: describe its light once (light): the sources against the landmarks, '
                                                                                      'the main one, hard or soft, colour, strength'})
            seen, sizes = {}, []   # A3: the widest size each element was seen at so far in the scene; the sizes in order
            for shot in scene.shots:
                if shot.visual_type in GRAPHIC_TYPES:
                    run_s += (shot.end_frame - shot.start_frame) / float(fps) if fps else 0
                    run_ids.append(shot.id)
                    if shot.claim == 'visible':   # G2
                        out.append({'shot_id': shot.id, 'kind': 'claim_visible_graphic', 'message': f'shot {shot.id}: its claim is about something a camera can film; '
                                                                                                    'show it with footage first, then an AI scene, and keep graphics for what a camera cannot show'})
                    continue
                if run_s > 8:   # G1: a camera shot ends a run of graphics
                    out.append(_graphics_run(gap.gap_id, run_ids, run_s))
                run_s, run_ids = 0.0, []
                if not shot.camera_reason.strip():   # A4
                    out.append({'shot_id': shot.id, 'kind': 'camera_reason_missing',
                                'message': f'shot {shot.id}: say what the viewer should feel or read, and why this angle, size and move give it (camera_reason)'})
                if not shot.size:   # review 27 Oct: an unsized shot breaks the run and is the opener if it comes first; it is never skipped over
                    sizes.append(None)
                    continue
                reason = shot.size_reason.strip()
                if not sizes and shot.size not in OPEN_SIZES and not reason:   # A3 (1)
                    out.append({'shot_id': shot.id, 'kind': 'size_open',
                                'message': f'shot {shot.id} opens scene {scene.id} at {shot.size}: a new place opens wide or medium-wide, unless a reveal is stated (size_reason)'})
                if len(sizes) >= 2 and sizes[-1] == sizes[-2] == shot.size and not reason:   # A3 (2)
                    out.append({'shot_id': shot.id, 'kind': 'size_repeat', 'message': f'shot {shot.id}: three {shot.size} shots in a row; change the size, or say why (size_reason)'})
                if shot.size in CLOSE_SIZES and not reason and shot.element_ids and not any(seen.get(e, 99) < SIZE_ORDER.index('MCU') for e in shot.element_ids):   # A3 (3)
                    out.append({'shot_id': shot.id, 'kind': 'size_close_first',
                                'message': f'shot {shot.id} is a {shot.size} of a subject not seen wider in this scene yet; show it wider first, or state the reveal (size_reason)'})
                for e in shot.element_ids:
                    seen[e] = min(seen.get(e, 99), SIZE_ORDER.index(shot.size))
                sizes.append(shot.size)
        if run_s > 8:
            out.append(_graphics_run(gap.gap_id, run_ids, run_s))
    return out


def _graphics_run(gap_id, ids, seconds):   # design/93 G1
    return {'gap_id': gap_id, 'kind': 'graphics_run', 'message': f"{seconds:.1f} s of graphics in a row in {gap_id} ({', '.join(ids)}): above 8 s, break it with a camera shot"
                                                              + ('; above 12 s it will be refused from the next release unless the treatment gives a reason' if seconds > 12 else '')}


def gap_digest(plan, gap):
    """Only relevant elements invalidate a gap; descriptive edits elsewhere do not."""
    used = {eid for scene in all_scenes(gap) for shot in scene['shots'] for eid in shot['element_ids']}
    content = {'foundation': plan['foundation'], 'gap': note_free_gap(gap),   # design/101, 103: the notes need no re-acceptance
               'elements': note_free_elements([e for e in plan['elements'] if e['id'] in used])}
    if plan.get('sequence_rules'): content['sequence_rules'] = plan['sequence_rules']
    return digest(content)


def all_scenes(gap):
    return [scene for choice in gap.get('choices', []) for scene in choice['scenes']] if gap.get('choices') else gap['scenes']


def chosen_scenes(gap, selection):
    if not gap.get('choices'): return gap['scenes']
    identity = (selection or {}).get('choice_id')
    choice = next((c for c in gap['choices'] if c['id'] == identity), None)
    need(choice, 'Resolve the focused visual alternative before accepting this gap.')
    return choice['scenes']
