# Adapted from the supplied Gemini-ChatGPT-Workflow; experimental profiles are not exposed.
import copy
import re
from types import SimpleNamespace
from .contract import load_schema, validate_response, _schema_gaps, _number, _text
intake=SimpleNamespace(IntakeError=ValueError)
ADDITIONAL_FIELDS=('attempts','crop_guidance','clean_handles','continuity','preview_frames','speech_action_links','shorter_explanations','script_support','workflow_acknowledgement','unavailable')
def expanded_schema(job, *, model_feedback=False, feedback_question_ids=None, editorial_roles=False, world_context=False):
    """The adopted structured script-support contract, bound to one source."""
    if feedback_question_ids is not None:
        raise intake.IntakeError('Retired feedback diagnostics are unsupported in the Gemini-only workflow.')
    schema = load_schema()
    schema['properties']['additional_analysis'] = {
        'type': 'object', 'properties': {key: {'type': 'string'} for key in ADDITIONAL_FIELDS},
        'required': list(ADDITIONAL_FIELDS), 'additionalProperties': False}
    schema['required'].append('additional_analysis')
    fields = {
        'passage_id': {'type': 'string'},
        'script_clause': {'type': 'string'},
        'claim_id': {'type': 'string'},
        'support_classification': {'type': 'string', 'enum':
            ['directly_seen', 'spoken_claim', 'illustrative', 'uncertain']},
        'editorial_use': {'type': 'string'},
    }
    schema['properties']['additional_analysis']['properties']['script_support'] = {
        'type': 'object', 'properties': {'claims': {'type': 'array', 'items': {
            'type': 'object', 'properties': fields, 'required': list(fields),
            'additionalProperties': False}}}, 'required': ['claims'], 'additionalProperties': False}
    schema['properties']['sources'].update(minItems=1, maxItems=1)
    props = schema['$defs']['source']['properties']
    for key in ('source_id', 'window_id', 'media_kind'):
        props[key] = {'type': 'string', 'enum': [job[key]]}
    props['clock'] = {'type': 'string', 'enum': ['original_source_seconds']}
    props['requested_interval'] = {'type': 'object', 'properties': {
        key: {'type': 'number'}
        for key in ('start_s', 'end_s')}, 'required': ['start_s', 'end_s'], 'additionalProperties': False}
    fields = {
        'id': {'type': 'string'},
        'target_paths': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1},
        'claim': {'type': 'string'},
        'basis_type': {'type': 'string', 'enum': ['visual', 'speech', 'script', 'inference', 'unknown']},
        'time_scope': {'type': 'string', 'enum': ['instant', 'interval', 'unknown', 'not_applicable']},
        'start_s': {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
        'end_s': {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
        'cues': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'time_s': {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
            'cue': {'type': 'string'}}, 'required': ['time_s', 'cue'], 'additionalProperties': False}},
        'limits': {'type': 'string'},
    }
    schema['properties']['claim_evidence'] = {'type': 'array', 'items': {
        'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}}
    schema['required'].append('claim_evidence')
    if model_feedback:
        fields = {
            'issue_type': {'type': 'string', 'enum': [
                'unclear_evidence', 'conflicting_information', 'instruction_problem', 'missing_input']},
            'affected_paths': {'type': 'array', 'items': {'type': 'string'}},
            'description': {'type': 'string'},
            'suggested_check': {'type': 'string'},
        }
        schema['properties']['model_feedback'] = {'type': 'array', 'items': {
            'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}}
        schema['required'].append('model_feedback')
    if editorial_roles:
        from .editorial_roles import role_schema
        schema['properties']['editorial_roles'] = role_schema(job)
        schema['required'].append('editorial_roles')
    if world_context:
        from .world import add_schema
        add_schema(schema)
    return schema

def _model_feedback_gaps(body):
    """Check feedback structure and references, never completeness or truth."""
    gaps = []
    for index, row in enumerate(body['model_feedback']):
        label = f'model_feedback[{index}]'
        for field in ('description', 'suggested_check'):
            if not _text(row[field]):
                gaps.append(f'{label}.{field}: nonempty text required')
        seen = set()
        for path in row['affected_paths']:
            if path in seen:
                gaps.append(f'{label}: duplicate affected path {path!r}')
            seen.add(path)
            parts = path.split('/')[1:]
            if (not path.startswith('/') or re.search(r'~(?:[^01]|$)', path)
                    or not (parts[:2] == ['sources', '0']
                            or parts[:1] in [['additional_analysis'], ['claim_evidence']])):
                gaps.append(f'{label}: unsupported affected path {path!r}')
                continue
            node = body
            try:
                for part in parts:
                    part = part.replace('~1', '/').replace('~0', '~')
                    if isinstance(node, list):
                        if not re.fullmatch(r'0|[1-9][0-9]*', part):
                            raise ValueError('Invalid array index')
                        node = node[int(part)]
                    else:
                        node = node[part]
            except (KeyError, IndexError, TypeError, ValueError):
                gaps.append(f'{label}: unresolved affected path {path!r}')
    return gaps

def _claim_evidence_gaps(body, expected):
    """Check bindings and clock consistency, never whether a cue is true."""
    gaps, seen = [], set()
    window = expected['sources'][0]['requested_interval']
    def in_window(value):
        return _number(value) and window['start_s'] - 0.001 <= value <= window['end_s'] + 0.001
    for index, row in enumerate(body['claim_evidence']):
        label = f'claim_evidence[{index}]'
        if not _text(row['id']) or row['id'] in seen:
            gaps.append(f'{label}: missing or duplicate id')
        seen.add(row['id'])
        for field in ('claim', 'limits'):
            if not _text(row[field]):
                gaps.append(f'{label}.{field}: nonempty text required')
        for path in row['target_paths']:
            # Bind only to source findings or additional analysis, never to a
            # justification itself, request metadata, or another response.
            parts = path.split('/')[1:]
            source_fields = {'coverage', 'scope_omissions', 'entities', 'speech', 'visual_events',
                             'visible_text', 'interpretations', 'editorial_ideas', 'visual_slot_guidance', 'unresolved'}
            if not path.startswith('/') or re.search(r'~(?![01])', path) or not (
                    (len(parts) >= 3 and parts[:2] == ['sources', '0'] and parts[2] in source_fields)
                    or (len(parts) >= 2 and parts[0] == 'additional_analysis' and parts[1] in ADDITIONAL_FIELDS)):
                gaps.append(f'{label}: unsupported target {path!r}')
                continue
            node = body
            try:
                for part in parts:
                    part = part.replace('~1', '/').replace('~0', '~')
                    if isinstance(node, list):
                        if not part.isdecimal() or str(int(part)) != part:
                            raise ValueError('Invalid array index')
                        node = node[int(part)]
                    else:
                        node = node[part]
                if isinstance(node, list):
                    raise ValueError('Target a specific finding, not its whole collection')
            except (KeyError, IndexError, TypeError, ValueError):
                gaps.append(f'{label}: unresolved target {path!r}')
        start, end, scope = row['start_s'], row['end_s'], row['time_scope']
        if scope in {'instant', 'interval'}:
            if not (in_window(start) and in_window(end)):
                gaps.append(f'{label}: claim times outside requested source window')
            elif (scope == 'instant' and start != end) or (scope == 'interval' and start >= end):
                gaps.append(f'{label}: times do not match time_scope')
        elif start is not None or end is not None:
            gaps.append(f'{label}: unknown/not_applicable time requires null bounds')
        for cue in row['cues']:
            if not _text(cue['cue']):
                gaps.append(f'{label}: nonempty cue required')
            if cue['time_s'] is not None and not in_window(cue['time_s']):
                gaps.append(f'{label}: cue time outside requested source window')
        if row['basis_type'] != 'unknown' and not row['cues']:
            gaps.append(f'{label}: supported claim requires a cue')
        if row['basis_type'] == 'visual' and (
                scope not in {'instant', 'interval'} or any(c['time_s'] is None for c in row['cues'])):
            gaps.append(f'{label}: visual video claim requires timed observations and scope')
        if row['basis_type'] == 'visual' and in_window(start) and in_window(end):
            if not any(_number(c['time_s']) and start - 0.001 <= c['time_s'] <= end + 0.001
                       for c in row['cues']):
                gaps.append(f'{label}: no visual cue within the claimed time scope')
        if row['basis_type'] == 'script' and (
                scope != 'not_applicable' or any(c['time_s'] is not None for c in row['cues'])):
            gaps.append(f'{label}: script-only evidence requires not_applicable scope and null cue times')
    return gaps

def validate_expanded(body, expected, schema):
    if schema.get('properties', {}).get('model_feedback', {}).get('type') == 'object':
        raise intake.IntakeError('Retired feedback diagnostics are unsupported in the Gemini-only workflow.')
    core = copy.deepcopy(body)
    if isinstance(core, dict):
        core.pop('additional_analysis', None)
        core.pop('claim_evidence', None)
        for field in ('world_markers', 'evidence_limits'):
            if field in schema['properties']:
                core.pop(field, None)
        if 'editorial_roles' in schema['properties']:
            core.pop('editorial_roles', None)
        if 'model_feedback' in schema['properties']:
            core.pop('model_feedback', None)
    result = validate_response(core, expected)
    result['extension_gaps'] = _schema_gaps(body, schema, schema)
    if not result['identity_errors'] and 'editorial_roles' in schema['properties']:
        from .evidence_view_v2 import usable_view
        source = body['sources'][0]
        job = dict(source_id=source['source_id'], media_kind=source['media_kind'],
                   requested_interval=source['requested_interval'],
                   audio_track_count=expected['sources'][0].get('audio_track_count', 0))
        view = usable_view(job, {'result': body}, expected, schema)
        result['extension_gaps'].extend(view.get('editorial_role_gaps', []))
    if not result['identity_errors'] and not result['extension_gaps']:
        result['extension_gaps'].extend(_claim_evidence_gaps(body, expected))
        if not result['extension_gaps']:
            result['extension_gaps'].extend(_structured_script_support_gaps(body, expected))
        if 'model_feedback' in schema['properties']:
            result['extension_gaps'].extend(_model_feedback_gaps(body))
    return result


def _structured_script_support_gaps(body, expected):
    """Check declared claim bindings/classifications, not the truth of prose."""
    gaps, seen, classifications = [], set(), {}
    claims = {row['id']: row for row in body['claim_evidence']}
    passages = expected.get('script_passages', {})
    allowed = {
        'visual': {'directly_seen', 'uncertain'},
        'speech': {'spoken_claim', 'uncertain'},
        'inference': {'illustrative', 'uncertain'},
        'script': {'uncertain'},
        'unknown': {'uncertain'},
    }
    def normalized(text):
        return ' '.join(text.split()).casefold()
    for index, row in enumerate(body['additional_analysis']['script_support']['claims']):
        label = f'additional_analysis.script_support.claims[{index}]'
        for key in ('passage_id', 'script_clause', 'claim_id', 'editorial_use'):
            if not _text(row[key]):
                gaps.append(f'{label}.{key}: nonempty text required')
        passage, clause, claim_id = row['passage_id'], row['script_clause'], row['claim_id']
        if passage not in expected.get('passage_ids', []):
            gaps.append(f'{label}: unknown script passage {passage!r}')
        elif passage not in passages:
            gaps.append(f'{label}: local script text unavailable for clause validation')
        elif normalized(clause) and normalized(clause) not in normalized(passages[passage]):
            gaps.append(f'{label}: script_clause is not present in the supplied passage')
        key = (passage, normalized(clause), claim_id)
        if key in seen:
            gaps.append(f'{label}: duplicate passage/clause/claim binding')
        seen.add(key)
        if claim_id not in claims:
            gaps.append(f'{label}: unknown claim_id {claim_id!r}')
            continue
        classification = row['support_classification']
        if classification not in allowed[claims[claim_id]['basis_type']]:
            gaps.append(f'{label}: support_classification conflicts with claim basis_type')
        if claim_id in classifications and classifications[claim_id] != classification:
            gaps.append(f'{label}: repeated claim has inconsistent support_classification')
        classifications[claim_id] = classification
    return gaps
