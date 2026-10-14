"""Analysis stage: build one frozen Gemini request per clip (ported from v1 video_analysis.build_request) and gate the answer.

Nothing large lives in a database row: the frozen request, the raw response and the evidence are files in storage;
the job row holds digests, status, cost."""
import hashlib
import json
import math
import re
from copy import deepcopy
from fractions import Fraction

from .errors import Problem
from .video_evidence.expanded import expanded_schema
from .video_evidence.gate import derive

STAGE = 'analysis'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str).encode()).hexdigest()


def passages_of(script):
    return [{'passage_id': pid, 'text': text} for pid, text in script['passages'].items()]


def processing_mode(procedure, duration_s):
    mode = procedure['settings'].get('processing_mode', 'auto')
    if mode == 'auto':
        return 'AGENTIC' if duration_s > procedure['settings'].get('agentic_over_seconds', 300) else 'STATIC'
    return mode


TIMELINE = {'width': 1920, 'height': 1080, 'fps': 25, 'aspect_ratio': '16:9'}


def speaker_policy(policy, production):
    """design/14 §2 default mapping: camera audio excluded → Mode 3; allowed → Mode 2, or Mode 1 when the brief shows the speaker."""
    allow = policy.get('camera_audio') == 'allowed'
    show = bool((production or {}).get('show_speaker_video')) and allow
    return {'allow_speaker_audio': allow, 'show_speaker_video': show}


def build_request_clip_log(run, procedure, brief, script, clip, policy, *, generation=None):
    from .clip_log import CONTRACT, prompt as P, schema as S
    duration = float(clip.get('duration_s') or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise Problem(422, 'ANALYSIS_SOURCE', f"Clip {clip.get('name')} has no usable duration.")
    try:
        fps = Fraction(str(clip.get('fps') or TIMELINE['fps']))
    except (ValueError, ZeroDivisionError):
        fps = Fraction(TIMELINE['fps'])
    frames = int(math.floor(Fraction(str(duration)) * fps))
    beats = [{'beat_id': b['beat_id'], 'text': b['text']} for b in (script.get('beats') or [])] or \
        [{'beat_id': f'BEAT_{i + 1:02d}', 'text': t} for i, t in enumerate(passages_of(script) and [p['text'] for p in passages_of(script)])]
    production = brief.get('production') or {}
    sp = speaker_policy(policy, production)
    clip_tag = clip['id'].upper()[:12]
    project_config = {'project_id': run.get('code') or str(run['id']), 'client_name': run.get('client') or 'unspecified',
                      'video_purpose': brief.get('purpose', ''), 'target_audience': brief.get('audience', ''), 'tone_and_mood': brief.get('tone', ''), 'intended_takeaway': brief.get('message', ''),
                      'target_aspect_ratio': TIMELINE['aspect_ratio'], 'timeline_resolution_width': TIMELINE['width'], 'timeline_resolution_height': TIMELINE['height'], 'timeline_fps': TIMELINE['fps'],
                      'target_runtime_seconds': production.get('target_runtime_s'),
                      'speaker_policy': {**sp, 'mode': P.MODES[P.mode_of(sp)]},
                      'language_config': {'expected_field_speech_languages': production.get('field_speech_languages') or ['en'], 'final_vo_language': production.get('narration_language') or 'en'},
                      'script_mode': 'SCRIPTED', 'script_beats': beats, 'process_stages': production.get('process_stages') or [],
                      'brand_and_safety_rules': production.get('brand_and_safety_rules') or [], 'learned_client_rules': production.get('learned_client_rules') or []}
    ffprobe_meta = {'clip_id': clip_tag, 'filename': clip['name'], 'source_resolution_width': clip.get('width'), 'source_resolution_height': clip.get('height'),
                    'source_fps': float(fps), 'is_variable_frame_rate_vfr': False, 'transcoded_from_vfr': bool(clip.get('transcoded_from_vfr')), 'rotation_flag_deg': clip.get('rotation_deg') or 0,
                    'color_transfer': clip.get('color_transfer') or 'unknown', 'duration_seconds': round(duration, 3), 'duration_frames': frames,
                    'duration_tc': tc_of(frames, fps), 'audio_channels': clip.get('audio_channels') or 0, 'audio_sample_rate_hz': clip.get('audio_sample_rate_hz'),
                    'creation_timestamp': clip.get('creation_time')}
    understand_audio = bool(policy.get('understand_audio', True))
    if not understand_audio:
        ffprobe_meta['audio_channels'] = 0
    text = P.build(project_config, ffprobe_meta, float(fps), frames, beats, clip_tag, sp, audio_removed=not understand_audio)
    schema = S.build_schema(clip_tag, clip['name'])
    identity = {'contract_version': CONTRACT, 'run_id': str(run['id']), 'source_id': clip['id'], 'clip_tag': clip_tag, 'source_sha256': clip['sha256'], 'script_digest': script['content_digest'],
                'brief_digest': brief.get('content_digest'), 'camera_audio': policy['camera_audio'], 'understand_audio': understand_audio, 'speaker_policy': sp,
                'prompt_digest': digest(text), 'schema_digest': digest(schema), 'model': procedure['model'], 'settings': {**procedure['settings'], 'processing_mode': processing_mode(procedure, duration)},
                'timeline': TIMELINE, **({'generation': str(generation)} if generation else {})}
    return {'contract_version': CONTRACT, 'identity': identity, 'analysis_key': digest(identity), 'prompt': text, 'schema': schema, 'wire_schema': S.wire_schema(schema),
            'clip': clip, 'mime': 'video/mp4', 'fps': str(fps), 'duration_frames': frames, 'policy': sp, 'timeline': TIMELINE, 'audio_removed': not understand_audio,
            'project_config': project_config, 'ffprobe_meta': ffprobe_meta}


def tc_of(frames, fps):
    f = int(round(float(fps)))
    s, ff = divmod(int(frames), max(f, 1))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f'{h:02d}:{m:02d}:{s:02d}:{ff:02d}'


def build_request(run, procedure, brief, script, clip, policy, *, generation=None):
    if procedure.get('contract_version') == 'clip-log-v1':
        if policy.get('camera_audio') not in ('allowed', 'excluded'):
            raise Problem(422, 'ANALYSIS_POLICY', 'camera_audio must be allowed or excluded.')
        return build_request_clip_log(run, procedure, brief, script, clip, policy, generation=generation)
    return build_request_v2(run, procedure, brief, script, clip, policy, generation=generation)


def build_request_v2(run, procedure, brief, script, clip, policy, *, generation=None):
    """clip: {'id','name','sha256','bytes','duration_s','has_audio','width','height','fps'} from the media output.
    policy: {'camera_audio': allowed|excluded, 'understand_audio': bool, 'film_type': str, 'exclude': [ids]}."""
    if policy.get('camera_audio') not in ('allowed', 'excluded'):
        raise Problem(422, 'ANALYSIS_POLICY', 'camera_audio must be allowed or excluded.')
    duration = float(clip.get('duration_s') or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise Problem(422, 'ANALYSIS_SOURCE', f"Clip {clip.get('name')} has no usable duration.")
    understand_audio = bool(policy.get('understand_audio', True))
    passages = passages_of(script)
    job = {'source_id': clip['id'], 'window_id': 'full', 'media_kind': 'video', 'duration_s': duration,
           'requested_interval': {'start_s': 0, 'end_s': duration}, 'audio_track_count': (1 if clip.get('has_audio') else 0) if understand_audio else 0}
    script_id = script['content_digest']
    request_id = digest({'run': str(run['id']), 'clip': clip['sha256'], 'script': script_id, 'generation': generation})[:32]
    expected = {'contract_version': 'source-evidence-v2', 'request_id': request_id, 'script_id': script_id,
                'passage_ids': [p['passage_id'] for p in passages], 'script_passages': {p['passage_id']: p['text'] for p in passages},
                'sources': [job], 'source_audio_allowed': policy['camera_audio'] == 'allowed', 'planned_visual_slots': [],
                'workflow_situation': {'enabled': False}}
    brief_doc = {k: brief.get(k, '') for k in ('purpose', 'audience', 'message', 'tone', 'ending', 'constraints')}
    manifest = {'attached_source': {**job, 'sha256': clip['sha256'], 'metadata': {k: clip.get(k) for k in ('duration_s', 'width', 'height', 'fps', 'has_audio', 'bytes')}},
                'original_clock_mapping': 'original_seconds = attached_seconds; whole original starts at zero',
                'response_consumer': 'editing_agent',
                'media_brief': {'generated_video_intent': 'later gap filling; no generated asset exists', 'planned_visual_slots': [],
                                'planned_visual_slots_status': 'exact_passage_level_reservations_not_supplied',
                                'force_recorded_footage_for_every_passage': False, 'automatic_media_generation': False},
                'source_audio_policy': {'intake': 'include_original_sound' if understand_audio else 'audio_removed_for_analysis', 'output': policy['camera_audio']},
                'output': {'status': 'use accepted delivery settings; no final timeline exists yet'},
                'envelope': {k: expected[k] for k in ('contract_version', 'request_id', 'script_id')},
                'accepted_brief': brief_doc, 'accepted_script': {'spoken_text': script['spoken_text'], 'content_digest': script_id},
                'workflow_situation': {'enabled': False}, 'available_media_kinds': ['video'],
                'excluded_sources': list(policy.get('exclude') or []), 'collection': policy.get('collection') or [],
                'actual_settings': deepcopy(procedure['settings'])}
    replacements = {'[FILM_TYPE_OR_UNSPECIFIED]': str(policy.get('film_type') or 'unspecified'),
                    '[AUDIENCE_AND_PURPOSE]': json.dumps({'audience': brief_doc['audience'] or 'unspecified', 'purpose': brief_doc['purpose'] or 'unspecified'}, ensure_ascii=False),
                    '[STYLE_AND_INTENDED_TAKEAWAY]': json.dumps({'style': brief_doc['tone'] or 'unspecified', 'intended_takeaway': brief_doc['message'] or 'unspecified'}, ensure_ascii=False),
                    '[COMPLETE_SCRIPT_WITH_PASSAGE_IDS]': '\n\n'.join(p['passage_id'] + ': ' + p['text'] for p in passages),
                    '[MEDIA_BRIEF_AND_SOURCE_MANIFEST_WITH_WINDOW_MAPPING]': json.dumps(manifest, ensure_ascii=False)}
    prompt = '\n\n'.join(procedure['prompt_blocks'])
    prompt = re.sub('|'.join(re.escape(k) for k in replacements), lambda m: replacements[m.group()], prompt)
    prompt += '\n\n' + procedure['naming_prompt']
    if not understand_audio:
        prompt += ('\n\nAnalysis audio choice: original audio was removed from the attached analysis copy at the user request. '
                   'Report no audio track for this copy; do not invent speech or sound. The original is preserved.')
    schema = expanded_schema(job, world_context=procedure.get('evidence_extensions') == 'world-context-v1')
    schema['properties']['descriptive_name'] = {'type': 'string'}
    schema['required'].append('descriptive_name')
    mode = processing_mode(procedure, duration)
    settings = {**procedure['settings'], 'processing_mode': mode}
    identity = {'run_id': str(run['id']), 'source_id': clip['id'], 'source_sha256': clip['sha256'], 'script_digest': script_id,
                'brief_digest': brief.get('content_digest'), 'camera_audio': policy['camera_audio'], 'understand_audio': understand_audio,
                'film_type': replacements['[FILM_TYPE_OR_UNSPECIFIED]'], 'prompt_digest': digest(procedure['prompt_blocks'] + [procedure['naming_prompt']]),
                'schema_digest': digest(schema), 'model': procedure['model'], 'settings': settings, **({'generation': str(generation)} if generation else {})}
    return {'identity': identity, 'analysis_key': digest(identity), 'expected': expected, 'prompt': prompt, 'schema': schema,
            'passages': passages, 'clip': clip, 'mime': 'video/mp4'}


def review_response(raw, request):
    if request.get('contract_version') == 'clip-log-v1':
        from .clip_log import gate
        return gate.review(raw, request)
    return review_response_v2(raw, request)


def review_response_v2(raw, request):
    """Keep the first response and explicit gaps; never resubmit to repair formatting (ported)."""
    try:
        def reject(_):
            raise ValueError('Non-finite JSON')

        def finite(value):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError('Non-finite JSON')
            return number
        body = json.loads(raw, parse_constant=reject, parse_float=finite)
    except (ValueError, TypeError):
        return {'status': 'retained_unstructured', 'raw': raw, 'result': None, 'identity_errors': [],
                'gaps': ['The provider answer is not structured JSON. Preserve it for review; do not automatically regenerate.']}
    validation = derive(body, request['expected'], request['schema'])
    return {'status': 'identity_mismatch' if validation['identity_errors'] else 'retained', 'raw': raw, 'result': deepcopy(body),
            'identity_errors': validation['identity_errors'], 'gaps': validation['gaps'], 'evidence': validation['evidence']}


def summary_of(reviewed, clip):
    if reviewed.get('contract_version') == 'clip-log-v1':
        from .clip_log import gate
        return gate.summary_of(reviewed, clip)
    return summary_of_v2(reviewed, clip)


def summary_of_v2(reviewed, clip):
    ev = reviewed.get('evidence') or {}
    counts = {}
    for row in ev.get('usable') or []:  # list of {'ref': {'collection': …}, 'item': …}
        c = (row.get('ref') or {}).get('collection', '?')
        counts[c] = counts.get(c, 0) + 1
    return {'status': reviewed['status'], 'clip': {k: clip.get(k) for k in ('id', 'name', 'duration_s')},
            'descriptive_name': (reviewed.get('result') or {}).get('descriptive_name'),
            'usable_rows': counts, 'excluded_rows': len(ev.get('excluded_rows') or []), 'gaps': len(reviewed.get('gaps') or []),
            'identity_errors': reviewed.get('identity_errors') or []}
