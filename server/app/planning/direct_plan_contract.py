"""Structured editorial explanations for Gemini's plans; no editorial decisions here."""
from copy import deepcopy


def build_schema(base, source_ids, passage_ids, editorial_roles=False):
    """Extend a v2 schema without mutating it or importing the request runner."""
    result = deepcopy(base)
    text = {'type': 'string', 'minLength': 1}
    def obj(properties):
        return {'type': 'object', 'properties': properties, 'required': list(properties),
                'additionalProperties': False}
    def array(items, minimum=0):
        return {'type': 'array', 'items': items, 'minItems': minimum}
    props = result['properties']
    ref = deepcopy(props['shots']['items']['properties']['evidence_refs']['items'])
    notes = obj({
        'shot_decisions': array(obj({'shot_id': text, 'meaning_and_support': text,
            'new_information': text, 'duration_reason': text, 'crop_tradeoff': text,
            'limitations': {'type': 'string'}})),
        'combinations': array(obj({'shot_ids': array(text, 2), 'first_shot_establishes': text,
            'following_shots_add': array(obj({'shot_id': text, 'contribution': text}), 1),
            'better_than_single_shot': text, 'unintended_meaning_and_treatment': text})),
        'story_check': obj({key: text for key in ('opening', 'progression', 'new_information',
                                                'action_readability', 'pace_and_ending')}),
        'important_omissions': array(obj({'source_id': {'type': 'string', 'enum': source_ids},
            'contribution': text, 'reason': text, 'evidence_refs': array(ref, 1)})),
        'factual_conflicts': array(text)})
    if editorial_roles:
        from .editorial_roles import ROLES
        decision = notes['properties']['shot_decisions']['items']
        decision['properties'].update({
            'role': {'type': 'string', 'enum': ROLES},
            'source_audio_role': {'type': 'string', 'enum': ROLES},
            'required_companion': {'type': 'string'},
            'script_connections': array(obj({'passage_id': {'type': 'string', 'enum': passage_ids},
                'script_clause': text, 'connection': text, 'evidence_refs': array(ref, 1)}), 1)})
        decision['required'] = list(decision['properties'])
    props['contract'] = {'type': 'string', 'enum': ['direct-gemini-edit-v3']}
    props['decision_notes'] = notes
    alternative = {key: deepcopy(props[key]) for key in
                   ('shots', 'narration_pauses', 'sequence_reason', 'unresolved', 'decision_notes')}
    if 'source_audio_segments' in props:
        alternative['source_audio_segments'] = deepcopy(props['source_audio_segments'])
    alternative.update({'id': text, 'title': text, 'tradeoff': text,
        'passage_ids': array({'type': 'string', 'enum': passage_ids}, 1),
        'duration_frames': {'type': 'integer', 'minimum': 1}})
    props['alternatives'] = array(obj(alternative))
    result['required'] = list(props)
    return result


def validate_decisions(sequence, context, error=ValueError):
    """Check explanation references and coverage, never judge or rewrite the choices."""
    def fail(message):
        raise error(message)
    def fields(value, keys, label):
        if not isinstance(value, dict) or set(value) != set(keys):
            fail(f'{label} has missing or unsupported fields.')
    def text(value, label, empty=False):
        if not isinstance(value, str) or (not empty and not value.strip()):
            fail(f'{label} must be a nonempty string.' if not empty else f'{label} must be a string.')
    def rows(value, label):
        if not isinstance(value, list):
            fail(f'{label} must be an array.')
        return value
    notes = sequence.get('decision_notes')
    fields(notes, ('shot_decisions', 'combinations', 'story_check', 'important_omissions',
                   'factual_conflicts'), 'Decision notes')
    videos = [s for s in sequence.get('shots', []) if s.get('kind') == 'video']
    ids = [s['id'] for s in videos]
    if len(ids) != len(set(ids)):
        fail('Video shot IDs must be unique.')
    decisions = rows(notes['shot_decisions'], 'Shot decisions')
    roles_required = context.get('editorial_roles_contract') == 'edit-roles-v1'
    seen = []
    for decision in decisions:
        keys = ('shot_id', 'meaning_and_support', 'new_information', 'duration_reason',
                'crop_tradeoff', 'limitations')
        role_keys = ('role', 'source_audio_role', 'required_companion', 'script_connections') if roles_required else ()
        from .planning_checks import enabled
        check_keys = ('relevance', 'action_support', 'reuse') if enabled(context) else ()
        fields(decision, keys + role_keys + check_keys, 'Shot decision')
        for key in keys:
            text(decision[key], key, empty=key == 'limitations')
        seen.append(decision['shot_id'])
        if roles_required:
            from .editorial_roles import ROLES
            if decision['role'] not in ROLES or decision['source_audio_role'] not in ROLES:
                fail('Unknown picture or source audio role.')
            text(decision['required_companion'], 'Required companion', empty=True)
            shot = next((s for s in videos if s['id'] == decision['shot_id']), None)
            if shot is None:
                fail('Role must refer to a selected video shot.')
            connections = rows(decision['script_connections'], 'Role script connections')
            if not connections:
                fail('A selected shot role needs a script connection.')
            for connection in connections:
                fields(connection, ('passage_id', 'script_clause', 'connection', 'evidence_refs'), 'Role script connection')
                text(connection['script_clause'], 'Role script clause')
                text(connection['connection'], 'Role connection')
                passage = connection['passage_id']
                text(passage, 'Role passage ID')
                if (passage not in shot['passage_ids'] or
                        connection['script_clause'] not in context.get('script_passages', {}).get(passage, '')):
                    fail('Role script clause must belong to a passage linked to this shot.')
                refs = rows(connection['evidence_refs'], 'Role evidence references')
                if not refs or any(ref not in shot['evidence_refs'] for ref in refs):
                    fail('Role evidence must resolve through this shot evidence.')
            if (context['workflow_situation']['source_audio_in_output'] == 'none'
                    and decision['source_audio_role'] != 'neither'):
                fail('Muted source audio cannot have a role in the output.')
    if len(seen) != len(set(seen)) or set(seen) != set(ids):
        fail('Each video shot needs exactly one decision note; gaps are not video shots.')
    from .planning_checks import validate_sequence
    validate_sequence(sequence, context, error)
    groups = []
    for combination in rows(notes['combinations'], 'Combinations'):
        fields(combination, ('shot_ids', 'first_shot_establishes', 'following_shots_add',
            'better_than_single_shot', 'unintended_meaning_and_treatment'), 'Combination')
        members = rows(combination['shot_ids'], 'Combination shot IDs')
        if (len(members) < 2 or any(not isinstance(v, str) or v not in ids for v in members)
                or len(set(members)) != len(members)):
            fail('Combinations need at least two distinct actual video shot IDs.')
        if members != [v for v in ids if v in members]:
            fail('Combination shot IDs must follow the actual shot order.')
        for key in ('first_shot_establishes', 'better_than_single_shot', 'unintended_meaning_and_treatment'):
            text(combination[key], key)
        following = rows(combination['following_shots_add'], 'Following shot contributions')
        for item in following:
            fields(item, ('shot_id', 'contribution'), 'Following shot contribution')
            text(item['shot_id'], 'Following shot ID')
            text(item['contribution'], 'Following shot contribution')
        if [item['shot_id'] for item in following] != members[1:]:
            fail('Following shot contributions must cover every following shot in order.')
        if members in groups:
            fail('Duplicate combination explanation.')
        groups.append(members)
    for passage in context.get('passage_ids', []):
        members = [s['id'] for s in videos if passage in s.get('passage_ids', [])]
        if len(members) >= 2 and not any(set(members).issubset(group) for group in groups):
            fail(f'Passage {passage} needs a combination explanation for all its video placements.')
    story_keys = ('opening', 'progression', 'new_information', 'action_readability', 'pace_and_ending')
    fields(notes['story_check'], story_keys, 'Story check')
    for key in story_keys:
        text(notes['story_check'][key], key)
    sources, registry = context.get('sources', {}), context.get('evidence_registry', {})
    for omission in rows(notes['important_omissions'], 'Important omissions'):
        fields(omission, ('source_id', 'contribution', 'reason', 'evidence_refs'), 'Important omission')
        text(omission['source_id'], 'Omitted source ID')
        if omission['source_id'] not in sources:
            fail('Omitted source must resolve in the current context.')
        text(omission['contribution'], 'Omitted contribution')
        text(omission['reason'], 'Omission reason')
        refs = rows(omission['evidence_refs'], 'Omission evidence references')
        if not refs or not any(isinstance(r, dict) and r.get('source_id') == omission['source_id'] for r in refs):
            fail('An omission needs evidence from its own source.')
        for ref in refs:
            fields(ref, ('source_id', 'collection', 'item_id'), 'Omission evidence reference')
            for key in ref:
                text(ref[key], key)
            pointer = '/'.join(ref[k] for k in ('source_id', 'collection', 'item_id'))
            row = registry.get(pointer)
            if (ref['source_id'] not in sources or not isinstance(row, dict)
                    or row.get('source_id', ref['source_id']) != ref['source_id']
                    or row.get('id', row.get('claim_id', ref['item_id'])) != ref['item_id']):
                fail(f'Unresolved or mismatched omission evidence: {pointer}.')
    for conflict in rows(notes['factual_conflicts'], 'Factual conflicts'):
        text(conflict, 'Factual conflict')
