"""Optional, request-versioned world observations and evidence limits."""
from collections import Counter
from copy import deepcopy
from .contract import _schema_gaps, _text, _interval

FIELDS = ('world_markers', 'evidence_limits')


def provider_schema(schema, processing_mode):
    """Keep the frozen validator; reduce the agentic API's enum complexity only.

    Gemini rejects the combined world contract in AGENTIC mode with the category
    enum, but accepts the same shape with those choices in its description.
    derive_world still enforces the original enum before exposing any evidence.
    """
    if processing_mode != 'AGENTIC' or not all(k in schema.get('properties', {}) for k in FIELDS):
        return schema
    category = schema['properties']['world_markers']['items']['properties']['category']
    if not category.get('enum'):
        return schema
    result = deepcopy(schema)
    target = result['properties']['world_markers']['items']['properties']['category']
    choices = target.pop('enum')
    target['description'] = 'Use exactly one of: ' + ', '.join(choices) + '. Other values are rejected by application validation.'
    return result


def add_schema(schema):
    text = {'type': 'string'}
    refs = {'type': 'array', 'items': {'type': 'object', 'properties': {
        'source_id': text, 'window_id': text,
        'collection': {'type': 'string', 'enum': ['entities', 'visual_events', 'visible_text']},
        'item_id': text}, 'required': ['source_id', 'window_id', 'collection', 'item_id'],
        'additionalProperties': False}}
    interval = {'type': 'object', 'properties': {'start_s': {'type': 'number'},
        'end_s': {'type': 'number'}}, 'required': ['start_s', 'end_s'], 'additionalProperties': False}
    common = {'id': text, 'evidence_refs': refs}
    marker = {**common, 'category': {'type': 'string', 'enum': [
        'people', 'wardrobe', 'place_era', 'environment', 'architecture', 'tools_props',
        'vehicles', 'animals', 'signage_language', 'material_state', 'condition', 'other']},
        'observation': text, 'entity_ids': {'type': 'array', 'items': text},
        'interval': interval, 'uncertainty': text}
    marker['evidence_refs'] = {**refs, 'minItems': 1}
    limit = {**common, 'subject': text, 'kind': {'type': 'string',
        'enum': ['not_visible', 'ambiguous', 'not_established']}, 'limitation': text,
        'interval': {'anyOf': [interval, {'type': 'null'}]}}
    for name, fields in zip(FIELDS, (marker, limit)):
        schema['properties'][name] = {'type': 'array', 'items': {'type': 'object',
            'properties': fields, 'required': list(fields), 'additionalProperties': False}}
        schema['required'].append(name)


def derive_world(body, schema, job, usable):
    """Salvage independent valid entries; never fill missing historical fields."""
    result, excluded = {}, []
    for name in FIELDS:
        if name not in schema['properties']:
            continue
        rows = body.get(name)
        result[name] = None if not isinstance(rows, list) else []
        if not isinstance(rows, list):
            excluded.append({'collection': name, 'item_id': None, 'index': None,
                             'reasons': ['Missing or malformed collection remains unknown.']})
            continue
        counts = Counter(r.get('id') for r in rows if isinstance(r, dict) and isinstance(r.get('id'), str))
        for index, row in enumerate(rows):
            reasons = _schema_gaps(row, schema['properties'][name]['items'], schema)
            if not reasons:
                required = ('id', 'observation') if name == 'world_markers' else ('id', 'subject', 'limitation')
                if any(not _text(row[k]) for k in required) or counts[row['id']] != 1:
                    reasons.append('Missing text or duplicate identity.')
                span, window = row['interval'], job['requested_interval']
                if span is not None and (not _interval(span) or not
                    window['start_s'] <= span['start_s'] < span['end_s'] <= window['end_s']):
                    reasons.append('Invalid or out-of-bounds original-source interval.')
                for ref in row['evidence_refs']:
                    key = (ref['collection'], ref['item_id'])
                    target = usable.get(key)
                    if ref['source_id'] != job['source_id'] or ref['window_id'] != job['window_id'] or target is None:
                        reasons.append('Reference to external, missing or unusable observation.')
                    elif span is not None and _interval(target.get('interval')) and (
                        span['end_s'] <= target['interval']['start_s'] or span['start_s'] >= target['interval']['end_s']):
                        reasons.append('Referenced observation does not overlap the stated interval.')
                if name == 'world_markers' and any(('entities', entity) not in usable for entity in row['entity_ids']):
                    reasons.append('Unknown or unusable subject identity.')
            if reasons:
                excluded.append({'collection': name, 'item_id': row.get('id') if isinstance(row, dict) else None,
                                 'index': index, 'reasons': reasons})
            else:
                result[name].append(deepcopy(row))
    return result, excluded
