"""Combined visual planning. Positions belong to the set, never to the camera."""
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


class Foundation(Model):
    treatment: str = Field(min_length=1, max_length=16000)
    appearance: str = Field(min_length=1, max_length=8000)
    world: list[Rule] = Field(default_factory=list, max_length=100)
    exclusions: list[Rule] = Field(default_factory=list, max_length=100)
    specifications: list[Rule] = Field(default_factory=list, max_length=100)
    production_constraints: list[Rule] = Field(default_factory=list, max_length=100)
    editing_constraints: list[Rule] = Field(default_factory=list, max_length=100)


class Element(Model):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    name: str = Field(min_length=1, max_length=200)
    kind: Literal['person', 'object', 'place', 'graphic', 'animal']
    identity: Literal['exact', 'representative']
    requirements: str = Field(min_length=1, max_length=4000)
    required_views: list[str] = Field(default_factory=list, max_length=20)


class Position(Model):
    landmark_id: str = Field(min_length=1, max_length=80)
    relation: str = Field(min_length=1, max_length=1000)


class State(Model):
    position: Position
    facing: str = Field(min_length=1, max_length=1000)
    pose: str = Field(min_length=1, max_length=2000)
    holding: list[str] = Field(default_factory=list, max_length=20)
    progress: str = Field(min_length=1, max_length=2000)


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


class Shot(Model):
    title: str = Field(default="", max_length=160)
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    visual_type: Literal['image', 'video', 'diagram', 'animation']
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
MAX_STATIC_S = 6                           # a still longer than this must earn its time (G15)
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


def validate_plan(document, source_gaps, fps=None):
    plan = Plan.model_validate(document)
    elements = unique(plan.elements, 'id', 'element')
    unique(plan.gaps, 'gap_id', 'gap')
    unique(plan.foundation.world + plan.foundation.exclusions + plan.foundation.specifications + plan.foundation.production_constraints + plan.foundation.editing_constraints + plan.sequence_rules, 'id', 'rule')
    scene_ids, shot_ids, beat_ids = set(), set(), set()
    warnings = []
    placed = []   # (gap_id, shot_id, visual_type, start, end) in film order, for the pacing warnings (design/65 B4)
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
        for scenes in ([c.scenes for c in gap.choices] if gap.choices else [gap.scenes]):
            cursor = window['start_frame']
            for scene in scenes:
                need(scene.id not in scene_ids, 'Duplicate scene identity.')
                scene_ids.add(scene.id)
                landmarks = unique(scene.landmarks, 'id', 'landmark')
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
                    if seconds is not None and shot.visual_type in STILL_TYPES and seconds > MAX_STATIC_S:
                        warnings.append({'shot_id': shot.id, 'kind': 'static_long', 'message': f'shot {shot.id} is a still of {seconds:.1f} s: over {MAX_STATIC_S} s it must earn the time '
                                                                                               '(new information, reading, a build); say how in its purpose'})
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
                        if subject.behaviour == 'holds':
                            need(not subject.beats and subject.hold_reason.strip(), 'A held subject needs its reason, not invented beats.')
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
                        last_states[subject.element_id] = subject.end.model_dump()
                    if not shot.subjects:
                        need(shot.information_progression.strip(), 'Describe the composition or information progression for a shot without acting subjects.')
            need(cursor == window['end_frame'], 'Planned pictures must cover the exact approved working gap duration. Propose a timing revision before changing it.')
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
    result = plan.model_dump()
    for key in ('sequence_overview', 'sequence_rules'):
        if key not in document: result.pop(key)
    for key in ('specifications', 'production_constraints', 'editing_constraints'):
        if key not in document['foundation']: result['foundation'].pop(key)
    # New presentation fields must not change legacy approval digests when absent.
    for gap, original_gap in zip(result['gaps'], document.get('gaps', [])):
        for key in ('title', 'choices', 'recommended_choice', 'decision_reason', 'source_strategy', 'candidates'):
            if key not in original_gap: gap.pop(key)
        scene_pairs = list(zip(gap['scenes'], original_gap.get('scenes', [])))
        for choice, original_choice in zip(gap.get('choices', []), original_gap.get('choices', [])):
            scene_pairs.extend(zip(choice['scenes'], original_choice['scenes']))
        for scene, original_scene in scene_pairs:
            if 'title' not in original_scene: scene.pop('title')
            for shot, original_shot in zip(scene['shots'], original_scene['shots']):
                for key in ('title', 'appearance', 'production_method', 'review_notes', 'states'):
                    if key not in original_shot: shot.pop(key)
    return result, warnings


def gap_digest(plan, gap):
    """Only relevant elements invalidate a gap; descriptive edits elsewhere do not."""
    used = {eid for scene in all_scenes(gap) for shot in scene['shots'] for eid in shot['element_ids']}
    content = {'foundation': plan['foundation'], 'gap': gap,
               'elements': [e for e in plan['elements'] if e['id'] in used]}
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
