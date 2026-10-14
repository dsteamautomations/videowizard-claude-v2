"""Derived v2 evidence: no correction of raw text, paths, timestamps or claims."""
from __future__ import annotations

import copy
import re
from collections import Counter

from .contract import load_schema, _schema_gaps, _interval, _number, _text

DEFINITIONS = {'entities': 'entity', 'speech': 'speech', 'visual_events': 'visual_event',
               'visible_text': 'visible_text', 'interpretations': 'interpretation',
               'editorial_ideas': 'editorial_idea'}


def _rows(value):
    return value if isinstance(value, list) else []


def _span_ok(span, job, optional=False):
    if span is None:
        return optional or job['media_kind'] == 'image'
    window = job.get('requested_interval')
    return (job['media_kind'] == 'video' and _interval(span) and _interval(window)
            and window['start_s'] - .001 <= span['start_s'] < span['end_s'] <= window['end_s'] + .001)


def _pointer(body, path):
    if not isinstance(path, str) or not path.startswith('/') or re.search(r'~(?![01])', path):
        raise ValueError('Invalid RFC 6901 pointer.')
    parts = [part.replace('~1', '/').replace('~0', '~') for part in path.split('/')[1:]]
    node = body
    for part in parts:
        if isinstance(node, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', part):
                raise ValueError('Invalid array index.')
            node = node[int(part)]
        elif isinstance(node, dict):
            node = node[part]
        else:
            raise ValueError('Pointer crosses a scalar.')
    if isinstance(node, list):
        raise ValueError('Pointer must name a finding, not a whole collection.')
    return parts


def usable_view(job, record, expected, expanded_schema):
    """Keep independent valid rows; omit bad rows and dependent references.

    Free-text additional analysis is explicitly provisional. It never supplies
    the visual-event references required by the editorial plan validator.
    """
    body = record['result']
    source = body['sources'][0]
    schema = load_schema()
    usable, excluded = {}, []
    counts = Counter(row['id'] for name in DEFINITIONS for row in _rows(source.get(name))
                     if isinstance(row, dict) and isinstance(row.get('id'), str))
    def reject(collection, row, reasons, index=None):
        excluded.append({'collection': collection, 'item_id': row.get('id') if isinstance(row, dict) else None,
                         'index': index, 'reasons': reasons})
    for collection, definition in DEFINITIONS.items():
        if not isinstance(source.get(collection), list):
            reject(collection, None, ['Missing or malformed collection remains unknown.'])
        for index, row in enumerate(_rows(source.get(collection))):
            reasons = _schema_gaps(row, schema['$defs'][definition], schema)
            if isinstance(row, dict):
                identifier = row.get('id')
                if not _text(identifier) or counts.get(identifier, 0) != 1:
                    reasons.append('Missing or duplicate item identity.')
                if collection not in ('entities', 'interpretations') and not _span_ok(
                        row.get('interval'), job, optional=collection == 'editorial_ideas'):
                    reasons.append('Unknown, invalid or out-of-bounds original-source timing.')
                for field in {'entities': ('label',), 'speech': ('original_text', 'english_translation'),
                              'visual_events': ('label', 'description'), 'visible_text': ('original_text',),
                              'interpretations': ('claim',), 'editorial_ideas': ('reason',)}[collection]:
                    if not _text(row.get(field)):
                        reasons.append(field + ' is unknown or empty.')
                if collection == 'speech' and (row.get('transcription_status') != 'clear'
                        or job['media_kind'] != 'video' or not job.get('audio_track_count')):
                    reasons.append('Unusable or incomplete speech cannot establish meaning.')
                if collection == 'visible_text' and row.get('legibility') != 'clear':
                    reasons.append('Partial/unreadable writing remains unknown.')
                if collection == 'interpretations' and not row.get('evidence_refs'):
                    reasons.append('Interpretation lacks supporting evidence.')
                if collection == 'editorial_ideas':
                    details = row.get('details') if isinstance(row.get('details'), dict) else {}
                    if any(p not in expected.get('passage_ids', []) for p in _rows(row.get('passage_ids'))):
                        reasons.append('Unknown script passage.')
                    if row.get('kind') != 'future_visual' and not row.get('evidence_refs'):
                        reasons.append('Recommendation lacks supporting evidence.')
                    if row.get('kind') == 'source_audio' and expected.get('source_audio_allowed') is not True:
                        reasons.append('Actionable camera audio contradicts the current output policy.')
                    if row.get('kind') == 'future_visual' and details.get('asset_status') != 'planned_not_created':
                        reasons.append('Proposed future visual is not an existing asset.')
                    if not _span_ok(details.get('alternative_interval'), job, optional=True):
                        reasons.append('Invalid alternative source interval.')
            if reasons:
                reject(collection, row, reasons, index)
            else:
                usable[(collection, row['id'])] = copy.deepcopy(row)

    def dependencies(key):
        row, collection = usable[key], key[0]
        refs = list(row.get('evidence_refs', []))
        details = row.get('details')
        if isinstance(details, dict):
            refs += details.get('alternative_refs') or []
        result = []
        for ref in refs:
            if ref.get('source_id') != job['source_id'] or ref.get('window_id') != job['window_id']:
                return None
            result.append((ref.get('collection'), ref.get('item_id')))
        if collection == 'visual_events':
            result += [('entities', item) for item in row['actor_ids'] + row['object_ids']]
        if collection == 'speech' and row['speaker_id'] is not None:
            result.append(('entities', row['speaker_id']))
        return result
    def supported(key, visiting):
        if key not in usable or key in visiting:
            return False
        refs = dependencies(key)
        return refs is not None and all(supported(ref, visiting | {key}) for ref in refs)
    bad = [key for key in usable if not supported(key, set())]
    for key in bad:
        reject(key[0], usable.pop(key), ['Reference to missing, unusable, external or cyclic evidence.'])

    raw_analysis = body.get('additional_analysis')
    analysis = raw_analysis if isinstance(raw_analysis, dict) else {}
    analysis_rule = expanded_schema['properties']['additional_analysis']['properties']
    provisional = {name: analysis.get(name) if isinstance(analysis.get(name), str) else None
                   for name in analysis_rule if name != 'script_support'}
    claims = []
    claim_rule = expanded_schema['properties']['claim_evidence']['items']
    claim_counts = Counter(row['id'] for row in _rows(body.get('claim_evidence'))
                           if isinstance(row, dict) and isinstance(row.get('id'), str))
    for index, row in enumerate(_rows(body.get('claim_evidence'))):
        reasons = _schema_gaps(row, claim_rule, expanded_schema)
        if not reasons:
            if not _text(row['id']) or claim_counts[row['id']] != 1 or not _text(row['claim']) or not _text(row['limits']):
                reasons.append('Missing text or duplicate claim identity.')
            start, end, scope = row['start_s'], row['end_s'], row['time_scope']
            window = job.get('requested_interval')
            def in_window(value):
                return _number(value) and window is not None and window['start_s'] - .001 <= value <= window['end_s'] + .001
            if scope in {'instant', 'interval'}:
                if not (in_window(start) and in_window(end)) or (start != end if scope == 'instant' else start >= end):
                    reasons.append('Invalid claim time scope.')
            elif start is not None or end is not None:
                reasons.append('Untimed claim has invented bounds.')
            if row['basis_type'] != 'unknown' and not row['cues']:
                reasons.append('Supported claim has no cue.')
            for cue in row['cues']:
                if not _text(cue['cue']) or (cue['time_s'] is not None and not in_window(cue['time_s'])):
                    reasons.append('Invalid cue or cue time.')
            if row['basis_type'] == 'visual' and job['media_kind'] == 'video' and (
                    scope not in {'instant', 'interval'} or any(c['time_s'] is None for c in row['cues'])
                    or not any(in_window(c['time_s']) and _number(start) and _number(end)
                               and start <= c['time_s'] <= end for c in row['cues'])):
                reasons.append('Visual video claim lacks a cue inside its time scope.')
            if row['basis_type'] == 'script' and (scope != 'not_applicable' or any(c['time_s'] is not None for c in row['cues'])):
                reasons.append('Script-only evidence must remain untimed.')
            for path in row['target_paths']:
                try:
                    parts = _pointer(body, path)
                    if len(parts) >= 3 and parts[:2] == ['sources', '0']:
                        if parts[2] not in schema['$defs']['source']['properties'] or parts[2] in {
                                'source_id', 'window_id', 'media_kind', 'clock', 'requested_interval', 'review_status'}:
                            raise ValueError('Unsupported source target.')
                        if parts[2] in DEFINITIONS:
                            target = source[parts[2]][int(parts[3])]
                            if not isinstance(target, dict) or (parts[2], target.get('id')) not in usable:
                                raise ValueError('Target evidence is unusable.')
                    elif len(parts) >= 2 and parts[0] == 'additional_analysis' and parts[1] in analysis_rule:
                        pass
                    else:
                        raise ValueError('Unsupported target root.')
                except (KeyError, IndexError, TypeError, ValueError):
                    reasons.append('Unresolved, malformed or unusable target pointer; no path repair applied.')
        if reasons:
            reject('claim_evidence', row, reasons, index)
        else:
            claims.append(copy.deepcopy(row))

    support = []
    support_rule = analysis_rule['script_support']['properties']['claims']['items']
    claim_ids = {row['id']: row for row in claims}
    raw_support = analysis.get('script_support')
    rows = _rows(raw_support.get('claims')) if isinstance(raw_support, dict) else []
    seen = set()
    declared = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get('claim_id'), str) and isinstance(row.get('support_classification'), str):
            declared.setdefault(row['claim_id'], set()).add(row['support_classification'])
    allowed = {'visual': {'directly_seen', 'uncertain'}, 'speech': {'spoken_claim', 'uncertain'},
               'inference': {'illustrative', 'uncertain'}, 'script': {'uncertain'}, 'unknown': {'uncertain'}}
    for index, row in enumerate(rows):
        reasons = _schema_gaps(row, support_rule, expanded_schema)
        if not reasons:
            if any(not _text(row[field]) for field in ('passage_id', 'script_clause', 'claim_id', 'editorial_use')):
                reasons.append('Missing support text remains unknown.')
            claim = claim_ids.get(row['claim_id'])
            passage = expected.get('script_passages', {}).get(row['passage_id'])
            clause = ' '.join(row['script_clause'].split()).casefold()
            binding = (row['passage_id'], clause, row['claim_id'])
            if not passage or not clause or clause not in ' '.join(passage.split()).casefold():
                reasons.append('Clause does not occur in the current script passage.')
            if not claim or row['support_classification'] not in allowed[claim['basis_type']]:
                reasons.append('Missing usable claim or incompatible evidence basis.')
            if binding in seen or len(declared.get(row['claim_id'], set())) > 1:
                reasons.append('Duplicate or inconsistent claim classification.')
            seen.add(binding)
        if reasons:
            reject('script_support', row, reasons, index)
        else:
            support.append(copy.deepcopy(row))
    slots = []
    for index, row in enumerate(_rows(source.get('visual_slot_guidance'))):
        reasons = _schema_gaps(row, schema['$defs']['visual_slot'], schema)
        if not reasons:
            if any(p not in expected.get('passage_ids', []) for p in row['passage_ids']):
                reasons.append('Unknown script passage.')
            supplied = next((slot for slot in expected.get('planned_visual_slots', [])
                             if slot.get('origin') == 'user_supplied' and slot.get('slot_id') == row['slot_id']), None)
            if row['origin'] == 'user_supplied' and supplied is None:
                reasons.append('No matching user-supplied visual reservation.')
            if supplied and (row['intended_kind'] != supplied.get('intended_kind') or row['preserve_reservation'] is not True):
                reasons.append('Supplied visual reservation is not preserved.')
            if row['origin'] == 'agent_proposal' and (row['preserve_reservation'] is True
                    or (row['intended_kind'] == 'generated_video' and row['asset_status'] != 'planned_not_created')):
                reasons.append('Agent proposal cannot establish a reservation or an existing generated asset.')
        if reasons:
            reject('visual_slot_guidance', row, reasons, index)
        else:
            slots.append(copy.deepcopy(row))
    extension = {}
    if 'editorial_roles' in expanded_schema.get('properties', {}):
        from .editorial_roles import validated_roles
        roles, gaps = validated_roles(body.get('editorial_roles'), job, expected, usable)
        extension = {'editorial_roles': roles, 'editorial_role_gaps': gaps}
    from .world import derive_world
    world, rejected = derive_world(body, expanded_schema, job, usable)
    excluded.extend(rejected)
    return {**extension, **world, 'usable': usable, 'excluded_rows': excluded, 'provisional_analysis': provisional,
            'claim_evidence': claims if isinstance(body.get('claim_evidence'), list) else None,
            'script_support': {'claims': support} if isinstance(raw_support, dict) and isinstance(raw_support.get('claims'), list) else None,
            'visual_slot_guidance': slots if isinstance(source.get('visual_slot_guidance'), list) else None,
            'coverage': copy.deepcopy(source.get('coverage')), 'scope_omissions': copy.deepcopy(source.get('scope_omissions')),
            'unresolved': copy.deepcopy(source.get('unresolved'))}
