"""Optional, source-bound editorial roles. Labels are proposals, not placements."""
from collections import Counter
from copy import deepcopy
from ..video_evidence.contract import _schema_gaps, _number, _text

ROLES = ['a_roll', 'b_roll', 'context_dependent', 'neither', 'uncertain']


def role_schema(job):
    text = {'type': 'string'}
    def obj(fields):
        return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
    connection = obj(dict(passage_id=text, script_clause=text,
        support_classification={'type': 'string', 'enum': ['directly_seen', 'spoken_claim', 'illustrative', 'uncertain']},
        connection=text))
    ref = obj(dict(collection={'type': 'string', 'enum': ['visual_events', 'speech', 'visible_text']}, item_id=text))
    excerpt = obj(dict(id=text, source_id={'type': 'string', 'enum': [job['source_id']]},
        interval=obj(dict(start_s={'type': 'number'}, end_s={'type': 'number'})),
        role={'type': 'string', 'enum': ROLES},
        audio_role={'type': 'string', 'enum': ROLES},
        why_this_role=text, intended_presentation=text, what_it_adds=text,
        script_connections={'type': 'array', 'items': connection},
        evidence_refs={'type': 'array', 'items': ref, 'minItems': 1},
        audio_use={'type': 'string', 'enum': ['understanding_only', 'source_speech', 'ambient', 'both', 'none']},
        visible_speaking={'type': 'string', 'enum': ['present', 'absent', 'uncertain']},
        required_companion=text, uncertainty=text))
    return obj(dict(contract={'type': 'string', 'enum': ['editorial-roles-v1']},
                    situation_summary=text, excerpts={'type': 'array', 'items': excerpt}, unclassified_reason=text))


PROMPT = """EDITORIAL ROLES:
Return editorial_roles using contract editorial-roles-v1. A-roll is the main picture carrying this part of the story; B-roll is supporting picture, including process coverage over a voice. Classify useful excerpts in the supplied situation, not entire filenames by appearance. A process can be A-roll; a speaking face is not automatically A-roll. Allow context_dependent, neither or uncertain. Do not fill a quota or invent a script match. If no excerpt can be classified, leave excerpts empty and explain unclassified_reason.
Use original source seconds and the supplied source_id. Each excerpt needs an ID, interval, picture role, separate audio_role, why_this_role, intended_presentation, what_it_adds, script_connections, evidence_refs, audio_use, visible_speaking, required_companion and uncertainty. audio_role describes its proposed role in the output: use neither when original sound is only for understanding. audio_use concerns the proposed output use; original sound can still be examined when muted. Visible speaking describes what is observed, not permission to show it. If forbidden speaking is present or uncertain, explain the required cover, exclusion or supported crop; do not treat that excerpt as cleared for use.
For each useful script connection, give the supplied passage_id, an exact contiguous script_clause, support_classification and a concise explanation. Directly_seen needs visual evidence; spoken_claim needs clear speech. Illustration is not proof of hidden composition, strength, quantities or elapsed time. Reference actual visual_events, speech or visible_text IDs within this source, with overlapping times. Keep observations distinct from proposed presentation. State what complementary speech or picture is needed; do not invent or claim to have viewed an unattached companion. Give concise evidence-based editorial reasons, not private thinking steps. Roles are candidates for the later Gemini planner; they do not authorize a cut or an audio mix.
"""


def validated_roles(value, job, expected, usable):
    """Keep independently valid rows; never repair model data or its first response."""
    schema = role_schema(job)
    errors, retained = [], []
    if not isinstance(value, dict):
        return None, ['editorial_roles is missing or malformed']
    envelope = deepcopy(value)
    envelope['excerpts'] = []
    errors.extend(_schema_gaps(envelope, schema, schema))
    if errors or not isinstance(value.get('excerpts'), list):
        return None, errors or ['editorial_roles.excerpts must be an array']
    if not _text(value['situation_summary']):
        errors.append('editorial_roles.situation_summary is empty')
    counts = Counter(r.get('id') for r in value['excerpts'] if isinstance(r, dict) and isinstance(r.get('id'), str))
    window = job['requested_interval']
    passages = expected.get('script_passages', {})
    policy = expected.get('workflow_situation', {})
    for i, row in enumerate(value['excerpts']):
        gaps = _schema_gaps(row, schema['properties']['excerpts']['items'], schema)
        if not gaps:
            if not _text(row['id']) or counts[row['id']] != 1:
                gaps.append('missing or duplicate role ID')
            start, end = row['interval']['start_s'], row['interval']['end_s']
            if not (_number(start) and _number(end) and window['start_s'] <= start < end <= window['end_s'] + .001):
                gaps.append('role interval is outside the attached source')
            for key in ('why_this_role', 'intended_presentation', 'what_it_adds'):
                if not _text(row[key]):
                    gaps.append(key + ' is empty')
            refs = []
            for ref in row['evidence_refs']:
                evidence = usable.get((ref['collection'], ref['item_id']))
                if evidence is None:
                    gaps.append('unusable evidence reference: ' + ref['item_id'])
                    continue
                span = evidence.get('interval')
                if not span or span['end_s'] <= start or span['start_s'] >= end:
                    gaps.append('evidence does not overlap the excerpt: ' + ref['item_id'])
                refs.append(ref['collection'])
            for connection in row['script_connections']:
                clause = connection['script_clause']
                if not _text(clause) or clause not in passages.get(connection['passage_id'], ''):
                    gaps.append('script clause does not belong to the supplied passage')
                if not _text(connection['connection']):
                    gaps.append('script connection explanation is empty')
                classification = connection['support_classification']
                if classification == 'directly_seen' and not set(refs) & {'visual_events', 'visible_text'}:
                    gaps.append('directly_seen lacks visual evidence')
                if classification == 'spoken_claim' and 'speech' not in refs:
                    gaps.append('spoken_claim lacks usable speech')
            allowed_audio = {'none': {'none', 'understanding_only'},
                'ambient': {'none', 'understanding_only', 'ambient'},
                'speech': {'none', 'understanding_only', 'source_speech'},
                'both': {'none', 'understanding_only', 'source_speech', 'ambient', 'both'}}
            if policy and row['audio_use'] not in allowed_audio[policy['source_audio_in_output']]:
                gaps.append('proposed audio use conflicts with the user situation')
            if row['audio_use'] in {'none', 'understanding_only'} and row['audio_role'] != 'neither':
                gaps.append('muted original sound cannot carry an output audio role')
        if gaps:
            errors.extend(f'editorial_roles.excerpts[{i}]: {gap}' for gap in gaps)
        else:
            retained.append(deepcopy(row))
    result = deepcopy(value)
    result['excerpts'] = retained
    if not value['excerpts'] and not _text(value['unclassified_reason']):
        errors.append('empty excerpts need an unclassified_reason')
    return result, errors
