from copy import deepcopy

def schema(experiment_id, source_ids, passage_ids, fps, frames, contract_version='direct-gemini-edit-v2', situation=None):
    text = {'type': 'string'}
    integer = {'type': 'integer', 'minimum': 0}
    nullable_int = {'type': ['integer', 'null'], 'minimum': 0}
    crop = {'type': ['object', 'null'], 'properties': {k: integer for k in ('x','y','width','height')},
            'required': ['x','y','width','height'], 'additionalProperties': False}
    ref = {'type':'object','properties':{'source_id':{'type':'string','enum':source_ids},
            'collection':text,'item_id':text}, 'required':['source_id','collection','item_id'],
            'additionalProperties':False}
    props = {'id':text,'kind':{'type':'string','enum':['video','gap']},
        'source_id':{'type':['string','null'],'enum':source_ids+[None]},
        'source_start_frame':nullable_int,'source_end_frame':nullable_int,
        'timeline_start_frame':integer,'timeline_end_frame':integer,'crop_px':crop,
        'passage_ids':{'type':'array','items':{'type':'string','enum':passage_ids},'minItems':1},
        'reason':text,'uncertainty':text,
        'visible_talking':{'type':'string','enum':['absent','uncertain','not_applicable']},
        'evidence_refs':{'type':'array','items':ref}}
    if situation and situation['visible_speaking'] in {'allow', 'selective'}:
        props['visible_talking']['enum'].append('present')
    top = {'contract':{'type':'string','enum':['direct-gemini-edit-v2']},
        'experiment_id':{'type':'string','enum':[experiment_id]},
        'fps':{'type':'integer','enum':[fps]},'duration_frames':{'type':'integer','minimum':frames},
        'shots':{'type':'array','items':{'type':'object','properties':props,'required':list(props),
                                      'additionalProperties':False},'minItems':1},
        'narration_pauses':{'type':'array','items':{'type':'object','properties':{
            'after_passage_id':{'type':'string','enum':passage_ids},
            'additional_frames':{'type':'integer','minimum':1},'reason':text},
            'required':['after_passage_id','additional_frames','reason'],'additionalProperties':False}},
        'sequence_reason':text,'unresolved':{'type':'array','items':text}}
    base = {'type':'object','properties':top,'required':list(top),'additionalProperties':False}
    if situation and situation['source_audio_in_output'] != 'none':
        audio = {key: props[key] for key in ('id', 'source_start_frame', 'source_end_frame',
                 'timeline_start_frame', 'timeline_end_frame', 'evidence_refs', 'reason')}
        audio['source_id'] = {'type': 'string', 'enum': source_ids}
        audio['content'] = {'type': 'string', 'enum': ['speech', 'ambient', 'both']}
        for key in ('source_start_frame', 'source_end_frame'):
            audio[key] = integer
        top['source_audio_segments'] = {'type': 'array', 'items': {
            'type': 'object', 'properties': audio, 'required': list(audio), 'additionalProperties': False}}
        base['required'].append('source_audio_segments')
    if contract_version == 'direct-gemini-edit-v3':
        from .direct_plan_contract import build_schema
        return build_schema(base, source_ids, passage_ids, editorial_roles=bool(situation))
    if contract_version != 'direct-gemini-edit-v2':
        raise ValueError('Unsupported planning contract.')
    return base

def planning_prompt(doc, marker, situation=None):
    """Legacy prompt stays byte-identical; new situations opt into policy guidance."""
    prompt = marker + ':' + doc.split('```text\n' + marker + ':', 1)[1].split('\n```', 1)[0]
    if situation is None:
        return prompt
    if marker != 'DIRECT EDIT WITH EDITORIAL CHOICES':
        raise ValueError('Workflow situation planning requires the v3 editorial choices prompt.')
    from ..video_evidence.situation import situation_prompt
    paragraphs = prompt.split('\n\n')
    policy_index = next(i for i, p in enumerate(paragraphs) if p.startswith('Apply the supplied editorial rules'))
    paragraphs[policy_index] = (
        'Apply the supplied workflow_situation and film brief. Assess camera sound and visible speaking separately. '
        'Visible faces do not establish speaking. Report observed visible_talking as present, absent or uncertain '
        'as allowed by the response schema. When visible_speaking is avoid, do not knowingly retain a speaking '
        'face; use supported bounds or crops and retain uncertainty. When allow, a person explaining a process '
        'can remain on screen. When selective, follow only the recorded exceptions and speaker choices. '
        'Do not reject useful explanations merely because a person speaks. Never claim images prove hidden '
        'composition, measured quantities, strength or elapsed curing time.')
    prompt = '\n\n'.join(paragraphs).replace(
        'Source audio stays muted during these pauses.',
        'Source audio follows workflow_situation during these pauses.')
    if situation['source_audio_in_output'] != 'none':
        prompt += ('\n\nSOURCE AUDIO PLACEMENTS: Return source_audio_segments separately from picture shots, '
            'including for each alternative. Source frame endpoints use the original video frame rate; '
            'timeline endpoints use output fps. Preserve natural speed. State content (speech, ambient or both), '
            'reason and source evidence_refs. You may cover a source voice with another source picture when '
            'the situation allows it. The renderer plays the whole first original audio track; it cannot isolate '
            'speech from ambient sound. Select only intervals compatible with the sound permission. '
            'The supplied narration remains intact. Place original sound only in added narration pauses or '
            'other unoccupied audio time; overlapping narration or two source audio segments is not supported '
            'without an explicit mixing contract. Do not invent ducking or replace narration. Empty arrays are '
            'allowed; explain missing requested sound coverage in unresolved.')
    section = 'DIRECT EDIT SITUATION AND ROLES:'
    appendix = section + doc.split('```text\n' + section, 1)[1].split('\n```', 1)[0]
    return prompt.replace(marker + ':', 'DIRECT EDIT WITH SITUATION AND ROLES:', 1) + '\n\n' + appendix + '\n\n' + situation_prompt(situation)
