from copy import deepcopy
import math
from . import intake
CONTRACT="edit-clarification-v1"
TEXT={"type":"string","minLength":1}

def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}

def array(item):
    return {'type': 'array', 'items': item}

def extend_schema(schema, source_ids):
    result = deepcopy(schema)
    span = obj({'source_id': {'type': 'string', 'enum': source_ids},
                'start_s': {'type': 'number', 'minimum': 0}, 'end_s': {'type': 'number', 'minimum': 0}})
    question = obj({'id': TEXT, 'recipient': {'type': 'string', 'enum': ['flash', 'user', 'codex']},
                    'sequence_id': TEXT, 'shot_id': TEXT, 'property': TEXT, 'question': TEXT,
                    'why_needed': TEXT, 'what_answer_changes': TEXT, 'inspect': array(span)})
    result['properties']['clarification_questions'] = array(question)
    result['required'].append('clarification_questions')
    return result

def flash_schema():
    observation = obj({'source_id': TEXT, 'start_s': {'type': 'number'}, 'end_s': {'type': 'number'},
                       'visual_observation': TEXT, 'relevant_speech': {'type': 'string'}, 'limits': TEXT})
    return obj({'answers': array(obj({'question_id': TEXT,
        'status': {'type': 'string', 'enum': ['answered', 'partly_answered', 'unanswerable']},
        'answer': TEXT, 'observations': array(observation), 'interpretation': TEXT,
        'uncertainty': TEXT, 'inspection_method': TEXT, 'sampling_rate': TEXT})), 'inspection_limits': TEXT})

def sequences(plan):
    return [('recommendation', plan)] + [(a['id'], a) for a in plan.get('alternatives', [])]

def execution_digest(plan, parent=None):
    parent = parent or plan
    keys = ('duration_frames', 'shots', 'narration_pauses', 'sequence_reason', 'unresolved', 'source_audio_segments')
    value = {k: plan[k] for k in keys if k in plan}
    value.update(experiment_id=parent['experiment_id'], fps=parent['fps'])
    return intake.digest(value)

def validate_questions(plan, context):
    questions = plan.get('clarification_questions')
    if not isinstance(questions, list):
        raise ValueError('New plan must explicitly return clarification_questions (empty is allowed).')
    by_sequence = dict(sequences(plan))
    seen = set()
    for q in questions:
        if not q['id'].strip() or q['id'] in seen:
            raise ValueError('Question IDs must be unique and nonempty.')
        seen.add(q['id'])
        sequence = by_sequence.get(q['sequence_id'], {})
        if q['shot_id'] not in {s['id'] for s in sequence.get('shots', [])}:
            raise ValueError('Question must bind a real shot in the recommendation or an alternative.')
        if q['recipient'] == 'flash' and not q['inspect']:
            raise ValueError('Footage question needs original-source inspection intervals.')
        if len({s['source_id'] for s in q['inspect']}) > 3:
            raise ValueError('Split a footage question that requires more than three originals.')
        for span in q['inspect']:
            validate_span(span, context)
    return questions

def validate_span(span, context):
    source = context['sources'].get(span['source_id'])
    duration = source.get('duration_s', source.get('metadata', {}).get('duration_s')) if source else None
    a, b = span['start_s'], span['end_s']
    if (duration is None or not all(type(t) in (int, float) and math.isfinite(t) for t in (a, b))
            or not 0 <= a < b <= duration + 1e-6):
        raise ValueError('Inspection interval does not bind an eligible original source.')

def bind_observations(questions, response, context):
    """One row per original observation; never join spans or turn permission into evidence."""
    by_id = {q['id']: q for q in questions if q['recipient'] == 'flash'}
    answers = response['answers']
    ids = [a['question_id'] for a in answers]
    if len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise ValueError('Flash must answer each routed question exactly once.')
    rows = []
    for answer in answers:
        q = by_id[answer['question_id']]
        for index, observation in enumerate(answer['observations']):
            validate_span(observation, context)
            if observation['source_id'] not in {s['source_id'] for s in q['inspect']}:
                raise ValueError('Observation source differs from the question sources.')
            within_target = any(span['source_id'] == observation['source_id'] and span['start_s'] <= observation['start_s'] < observation['end_s'] <= span['end_s'] for span in q['inspect'])
            eligibility = ({'usable_for_target': within_target, 'scope_status': 'inside_target' if within_target else 'outside_target_excluded'} if context.get('focused_observations_contract') else {})
            rows.append({**eligibility, 'id': q['id'] + ':' + str(index), 'question_id': q['id'],
                'sequence_id': q['sequence_id'], 'shot_id': q['shot_id'], 'property': q['property'],
                'observation': deepcopy(observation), 'answer_status': answer['status'],
                'interpretation': answer['interpretation'], 'reported_uncertainty': answer['uncertainty'],
                'reported_method': answer.get('inspection_method', 'unknown'),
                'reported_sampling_rate': answer.get('sampling_rate', 'unknown'),
                'inspection_limits': answer.get('batch_inspection_limits', response['inspection_limits']),
                'method_independently_verified': False, 'continuous_clearance': 'not_established'})
    return rows

def answer_rows(questions, answers, recipient):
    expected = {q['id'] for q in questions if q['recipient'] == recipient}
    ids = [a['question_id'] for a in answers]
    if set(ids) != expected or len(ids) != len(set(ids)):
        raise ValueError('Missing, duplicate or unrelated ' + recipient + ' answers.')
    if any(not isinstance(a.get('answer'), str) or not a['answer'].strip() for a in answers):
        raise ValueError('Actual answers required; elapsed time is not an answer.')
    return deepcopy(answers)

def unchecked_properties(plan):
    return [{'sequence_id': sid, 'shot_id': s['id'], 'shot_sha256': intake.digest(s),
        'continuous_picture_and_sound_review': 'not_established_by_clarification',
        'inspection_between_samples': 'unknown',
        'model_uncertainty': s.get('uncertainty', ''),
        'note': 'A question answer addresses only its named property and observation. Permission is not factual proof.'}
        for sid, seq in sequences(plan) for s in seq['shots'] if s['kind'] == 'video']

def ledger(plan, questions, response, user, mechanical, context):
    observations = bind_observations(questions, response, context)
    permissions = answer_rows(questions, user, 'user')
    checks = answer_rows(questions, mechanical, 'codex')
    draft_shots = {(sid, s['id']): s for sid, seq in sequences(plan) for s in seq['shots']}
    for row in observations:
        row['draft_shot_sha256'] = intake.digest(draft_shots[(row['sequence_id'], row['shot_id'])])
    return {'contract': CONTRACT, 'observations': observations, 'inspector_answers': deepcopy(response['answers']), 'user_permissions': permissions,
            'mechanical_answers': checks, 'unchecked_properties': unchecked_properties(plan),
            'automatic_execution_allowed': False, 'semantic_review_required': True}

def focused_question_package(question, plan, context):
    """Select exact existing fields; never infer a new actor, observation or clause."""
    validate_questions(dict(plan, clarification_questions=[question]), context)
    sequence = dict(sequences(plan))[question['sequence_id']]
    shot = next(s for s in sequence['shots'] if s['id'] == question['shot_id'])
    notes = [n for n in sequence.get('decision_notes', {}).get('shot_decisions', [])
             if n['shot_id'] == shot['id']]
    source_ids = {span['source_id'] for span in question['inspect']}
    refs = list(shot.get('evidence_refs', []))
    for note in notes:
        for connection in note.get('script_connections', []):
            refs += connection.get('evidence_refs', [])
    keys = sorted({'/'.join(r[k] for k in ('source_id', 'collection', 'item_id')) for r in refs
                   if isinstance(r, dict) and r.get('source_id') in source_ids})
    registry = context.get('evidence_registry', {})
    if any(key not in registry for key in keys):
        raise ValueError('Focused question references unavailable prior evidence.')
    return {'contract': 'focused-question-package-v1',
            'workflow_situation': deepcopy(context.get('workflow_situation')),
            'question': deepcopy(question),
            'clock': 'original_source_seconds; proposed output frames are a separate clock',
            'sources': {sid: {k: deepcopy(context['sources'][sid][k]) for k in
                        ('source_id', 'sha256', 'metadata', 'duration_s') if k in context['sources'][sid]}
                        for sid in sorted(source_ids)},
            'proposed_edit_not_observations': {'sequence_id': question['sequence_id'], 'fps': plan['fps'],
                        'shot': deepcopy(shot), 'decision_notes': deepcopy(notes)},
            'narration_words': [deepcopy(w) for w in context.get('mapped_words', [])
                                if w['passage_id'] in shot.get('passage_ids', [])],
            'prior_observations_not_fresh_inspection': {key: deepcopy(registry[key]) for key in keys}}

def separate_supplemental_notes(plan):
    """Preserve gap comments/exact cross-sequence duplicates without editing decisions."""
    selected = deepcopy(plan)
    supplemental = []
    seqs = sequences(plan)
    for sid, seq in sequences(selected):
        if 'decision_notes' not in seq:
            continue
        videos = {s['id'] for s in seq['shots'] if s['kind'] == 'video'}
        gaps = {s['id'] for s in seq['shots'] if s['kind'] == 'gap'}
        kept = []
        for note in seq['decision_notes']['shot_decisions']:
            target = note['shot_id']
            duplicate = any(other_id != sid and
                target in {s['id'] for s in other['shots'] if s['kind'] == 'video'} and
                note in other.get('decision_notes', {}).get('shot_decisions', [])
                for other_id, other in seqs)
            if target not in videos and (target in gaps or duplicate):
                supplemental.append({'sequence_id': sid, 'note': deepcopy(note),
                    'reason': 'gap_comment' if target in gaps else 'exact_cross_sequence_duplicate'})
            else:
                kept.append(note)  # Unknown references remain invalid; never invent a binding.
        seq['decision_notes']['shot_decisions'] = kept
    return selected, {'original_plan_sha256': intake.digest(plan),
        'selected_plan_sha256': intake.digest(selected), 'supplemental_notes': supplemental,
        'scope': 'Only gap comments and exact cross-sequence duplicate notes separated. All placements and selected-video explanations unchanged.'}
