"""Analysis stage: build one frozen Gemini request per clip (ported from v1 video_analysis.build_request) and gate the answer.

Nothing large lives in a database row: the frozen request, the raw response and the evidence are files in storage;
the job row holds digests, status, cost."""
import hashlib
import json
import math
from fractions import Fraction

from .errors import Problem

STAGE = 'analysis'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str).encode()).hexdigest()


def client_profile(card):
    """design/50 D: the identity and brand strings the clip model may use (competitor names for the brand flag, trademark patterns for on-screen text)."""
    if not card:
        return {}
    return {'industry': card.get('industry') or '', 'description': card.get('client_description') or '', 'services': card.get('services_products') or [],
            'competitors': card.get('competitors') or [], 'trademark_patterns': card.get('trademark_patterns') or ''}


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


def request_policy(policy, production):
    """The speaker policy plus the waived risk flags (design/60 L20): the solver reads both from the request's policy, and the waivers
    are part of the analysis identity, as they are after a re-policy."""
    sp = speaker_policy(policy, production)
    if policy.get('waived_risk_flags'):
        sp['waived_risk_flags'] = list(policy['waived_risk_flags'])
        sp['waiver_note'] = policy.get('waiver_note') or policy.get('note') or ''
    return sp


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
    sp = request_policy(policy, production)
    clip_tag = clip['id'].upper()[:12]
    project_config = {'project_id': run.get('code') or str(run['id']), 'client_name': run.get('client') or 'unspecified',
                      'video_purpose': brief.get('purpose', ''), 'target_audience': brief.get('audience', ''), 'tone_and_mood': brief.get('tone', ''), 'intended_takeaway': brief.get('message', ''),
                      'target_aspect_ratio': TIMELINE['aspect_ratio'], 'timeline_resolution_width': TIMELINE['width'], 'timeline_resolution_height': TIMELINE['height'], 'timeline_fps': TIMELINE['fps'],
                      'target_runtime_seconds': production.get('target_runtime_s'),
                      'speaker_policy': {**sp, 'mode': P.MODES[P.mode_of(sp)]},
                      'language_config': {'expected_field_speech_languages': production.get('field_speech_languages') or ['en'], 'final_vo_language': production.get('narration_language') or 'en'},
                      'script_mode': 'SCRIPTED', 'script_beats': beats, 'process_stages': production.get('process_stages') or [],
                      'brand_and_safety_rules': production.get('brand_and_safety_rules') or [], 'learned_client_rules': production.get('learned_client_rules') or [],
                      'client_profile': client_profile(brief.get('client_card') or {})}   # design/50 D
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
    if procedure.get('contract_version') != 'clip-log-v1':   # design/35 Old ways 2: the version-1 evidence contract is gone
        raise Problem(409, 'RETIRED', 'The version-1 evidence contract is retired; analysis uses the clip log (clip-log-v1) of procedure version 3.')
    if policy.get('camera_audio') not in ('allowed', 'excluded'):
        raise Problem(422, 'ANALYSIS_POLICY', 'camera_audio must be allowed or excluded.')
    return build_request_clip_log(run, procedure, brief, script, clip, policy, generation=generation)


def review_response(raw, request):
    from .clip_log import gate
    return gate.review(raw, request)


def summary_of(reviewed, clip):
    from .clip_log import gate
    return gate.summary_of(reviewed, clip)
