"""Small, opt-in checks for explanation support and passage-level choices."""
from copy import deepcopy
from fractions import Fraction
import math

CONTRACT = 'passage-review-v1'
TEXT = {'type': 'string', 'minLength': 1}

def obj(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}

def arr(item):
    return {'type': 'array', 'items': item}

def extend_schema(schema):
    result = deepcopy(schema)
    ref = result['properties']['shots']['items']['properties']['evidence_refs']['items']
    stage = obj({'description': TEXT, 'evidence_ref': ref,
        'coverage': {'type': 'string', 'enum': ['full', 'partial', 'uncertain']}})
    for notes in (result['properties']['decision_notes'],
                  result['properties']['alternatives']['items']['properties']['decision_notes']):
        decision = notes['properties']['shot_decisions']['items']
        decision['properties'].update({'relevance': TEXT, 'action_support': arr(stage),
            'reuse': obj({'earlier_shot_ids': arr(TEXT), 'reason': {'type': 'string'}})})
        decision['required'] = list(decision['properties'])
    candidate = obj({'source_id': TEXT, 'source_start_frame': {'type': 'integer', 'minimum': 0},
        'source_end_frame': {'type': 'integer', 'minimum': 1}, 'evidence_refs': arr(ref), 'comparison': TEXT})
    result['properties']['alternative_review'] = arr(obj({'passage_ids': arr(TEXT), 'title': TEXT,
        'recommendation_reason': TEXT, 'status': {'type': 'string', 'enum': ['alternatives_available',
        'no_relevant_footage', 'no_added_information', 'brief_conflict', 'insufficient_evidence', 'user_reserved']},
        'reason': TEXT, 'candidates': arr(candidate), 'alternative_ids': arr(TEXT)}))
    result['properties']['gap_decisions'] = arr(obj({'shot_id': TEXT,
        'basis': {'type': 'string', 'enum': ['user_reserved', 'no_suitable_evidence', 'uncertain']},
        'reason': TEXT}))
    result['required'] = list(result['properties'])
    from .review_cards import explanation_schema
    result['properties']['review_explanations'] = explanation_schema()
    return result


def enabled(context):
    return context.get('planning_checks_contract') == CONTRACT


def evidence(ref, context, source_id, error):
    key = '/'.join(ref.get(k, '') for k in ('source_id', 'collection', 'item_id'))
    row = context['evidence_registry'].get(key)
    if ref.get('source_id') != source_id or not isinstance(row, dict):
        raise error('Evidence must resolve to the selected source: ' + key)
    return row


def validate_sequence(sequence, context, error=ValueError):
    if not enabled(context):
        return
    earlier = []
    notes = {n['shot_id']: n for n in sequence['decision_notes']['shot_decisions']}
    for shot in sequence['shots']:
        if shot['kind'] != 'video':
            continue
        note = notes[shot['id']]
        if not isinstance(note.get('relevance'), str) or not note['relevance'].strip():
            raise error('Each video needs a specific relevance explanation.')
        reuse = note.get('reuse', {})
        ids = reuse.get('earlier_shot_ids', [])
        previous = {s['id'] for s in earlier}
        same_source = {s['id'] for s in earlier if s['source_id'] == shot['source_id']}
        if len(ids) != len(set(ids)) or not set(ids) <= previous or not same_source <= set(ids):
            raise error('Reuse must identify earlier same-source shots; additional semantic reuse may be named.')
        if ids and not str(reuse.get('reason', '')).strip():
            raise error('Repeated source use needs a reason for user review.')
        support = note.get('action_support')
        if not isinstance(support, list):
            raise error('Explicit action_support is required; [] means no action claim.')
        fps = Fraction(str(context['sources'][shot['source_id']]['metadata']['frame_rate']))
        start, end = float(Fraction(shot['source_start_frame'])/fps), float(Fraction(shot['source_end_frame'])/fps)
        for stage in support:
            if not stage.get('description', '').strip() or stage.get('coverage') not in {'full', 'partial', 'uncertain'}:
                raise error('Action support needs a description and explicit coverage.')
            ref = stage['evidence_ref']
            if ref not in shot['evidence_refs']:
                raise error('Action support must use evidence cited by this shot.')
            row = evidence(ref, context, shot['source_id'], error)
            interval = row.get('interval')
            if not interval or any(not isinstance(interval.get(k), (int, float)) or not math.isfinite(interval[k]) for k in ('start_s', 'end_s')):
                if stage['coverage'] != 'uncertain':
                    raise error('Untimed evidence cannot establish full or partial action coverage.')
                continue
            a, b = interval['start_s'], interval['end_s']
            if b <= a or min(b, end) <= max(a, start):
                raise error('Claimed action evidence lies outside the selected excerpt: ' + shot['id'])
            if stage['coverage'] == 'full' and (a < start-1e-8 or b > end+1e-8):
                raise error('Full action claim is cut by the selected excerpt: ' + shot['id'])
        earlier.append(shot)


def validate_bundle(bundle, context, error=ValueError):
    if not enabled(context):
        return
    passages = context['passage_ids']
    rows = bundle.get('alternative_review', [])
    if [p for r in rows for p in r['passage_ids']] != passages or any(not r['passage_ids'] for r in rows):
        raise error('Alternative review must cover every passage once, in order.')
    alternatives = {a['id']: a for a in bundle['alternatives']}
    used = []
    allowed = {'alternatives_available', 'no_relevant_footage', 'no_added_information', 'brief_conflict', 'insufficient_evidence', 'user_reserved'}
    for row in rows:
        if row.get('status') not in allowed or any(not str(row.get(k, '')).strip() for k in ('title','reason','recommendation_reason')):
            raise error('Passage comparison needs a status and specific reasons.')
        ids = row['alternative_ids']
        if bool(ids) != (row['status'] == 'alternatives_available') or len(ids) != len(set(ids)):
            raise error('Alternative status and IDs disagree.')
        for identity in ids:
            if identity not in alternatives or not set(alternatives[identity]['passage_ids']) <= set(row['passage_ids']):
                raise error('Alternative must bind the compared passage group.')
        used += ids
        for candidate in row['candidates']:
            sid = candidate['source_id']; src = context['sources'].get(sid)
            if not src:
                raise error('Unknown alternative candidate source.')
            fps = Fraction(str(src['metadata']['frame_rate']))
            limit = src.get('native_frame_count')
            if limit is None:
                limit = math.floor(float(src.get('duration_s', src['metadata'].get('duration_s')))*float(fps))
            a,b = candidate['source_start_frame'],candidate['source_end_frame']
            if type(a) is not int or type(b) is not int or not 0 <= a < b <= limit or not candidate['evidence_refs']:
                raise error('Candidate needs valid native frames and evidence.')
            for ref in candidate['evidence_refs']:
                ev = evidence(ref, context, sid, error)
                interval = ev.get('interval')
                if interval and min(interval['end_s'],float(Fraction(b)/fps)) <= max(interval['start_s'],float(Fraction(a)/fps)):
                    raise error('Candidate evidence does not overlap its excerpt.')
        if row['status'] in {'alternatives_available','no_added_information','brief_conflict'} and not row['candidates']:
            raise error('This comparison status requires actual candidate evidence.')
    if len(used) != len(set(used)) or set(used) != set(alternatives):
        raise error('Every executable alternative must appear once in alternative_review.')
    gaps = {s['id'] for s in bundle['shots'] if s['kind'] == 'gap'}
    decisions = bundle.get('gap_decisions', [])
    if len(decisions) != len(gaps) or {d['shot_id'] for d in decisions} != gaps:
        raise error('Each recommended gap needs an explicit basis.')
    for d in decisions:
        if d.get('basis') not in {'user_reserved','no_suitable_evidence','uncertain'} or not d.get('reason','').strip():
            raise error('Gap basis or explanation missing.')
