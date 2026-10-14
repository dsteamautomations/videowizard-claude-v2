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


def validate_plan(document, source_gaps):
    plan = Plan.model_validate(document)
    elements = unique(plan.elements, 'id', 'element')
    unique(plan.gaps, 'gap_id', 'gap')
    unique(plan.foundation.world + plan.foundation.exclusions + plan.foundation.specifications + plan.foundation.production_constraints + plan.foundation.editing_constraints + plan.sequence_rules, 'id', 'rule')
    scene_ids, shot_ids, beat_ids = set(), set(), set()
    warnings = []
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
                for key in ('title', 'appearance', 'production_method', 'review_notes'):
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
