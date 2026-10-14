"""Fixtures for clip-log-v1 tests: the real Flash C0120 log upgraded to the frozen schema, and a small synthetic log for pipeline tests."""
import json
from copy import deepcopy
from pathlib import Path

FIXTURE = Path(__file__).parent / 'fixtures' / 'clip_log' / 'C0120.flash.json'
C0120 = {'fps': 50.0, 'frames': 960, 'width': 1920, 'height': 1080}


def tc(frame, fps):
    f = int(round(fps))
    s, ff = divmod(int(frame), f)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f'{h:02d}:{m:02d}:{s:02d}:{ff:02d}'


def upgrade(body, fps):
    """The experiment ran before four fields and one rename were added (design/12 §A). Fill them so the real log is strictly valid."""
    b = deepcopy(body)
    for sub in b['sub_clips']:
        if 'technical_qc' in sub:
            sub['technical_qc_and_remediation'] = sub.pop('technical_qc')
        for d in sub['technical_qc_and_remediation']['defects_detected']:
            if d['defect'] not in ('focus_hunt', 'exposure_pump', 'camera_bump', 'rolling_shutter', 'single_channel_audio'):
                d['defect'] = 'other'
        sub.setdefault('hero_frame_index', int(round(sub['hero_frame_s'] * fps)))
        for key in ('natural_cut_points', 'accent_events'):
            for ev in sub['pacing_and_flow'][key]:
                ev.setdefault('frame', int(round(ev['s'] * fps)))
        m = sub['people_and_speaker_analysis'].get('speaker_crop_module')
        if m:
            m.setdefault('active_speech_tc_range', None)
            m.setdefault('settle_buffer_applied_in_tc', None)
    return b


def real_log():
    return upgrade(json.loads(FIXTURE.read_text(encoding='utf-8')), C0120['fps'])


def real_request(policy=None):
    from app.clip_log import CONTRACT, schema as S
    body = json.loads(FIXTURE.read_text(encoding='utf-8'))
    clip = {'id': 'c0120', 'name': body['filename'], 'sha256': 'f' * 64, 'bytes': 1, 'duration_s': 19.2, 'has_audio': True, 'width': 1920, 'height': 1080, 'fps': '50/1'}
    schema = S.build_schema(body['clip_id'], body['filename'])
    return {'contract_version': CONTRACT, 'identity': {'clip_tag': body['clip_id'], 'source_id': 'c0120', 'model': 'gemini-3.8-flash'}, 'schema': schema, 'clip': clip,
            'fps': '50/1', 'duration_frames': 960, 'policy': policy or {'allow_speaker_audio': False, 'show_speaker_video': False},
            'timeline': {'width': 1920, 'height': 1080, 'fps': 25}, 'audio_removed': False}


def window(a, b, fps):
    return {'in_tc': tc(a, fps), 'out_tc': tc(b, fps), 'in_s': a / fps, 'out_s': b / fps, 'in_frame': a, 'out_frame': b, 'duration_s': (b - a) / fps,
            'video_handle_frames_before': 0, 'video_handle_frames_after': 0, 'audio_handle_frames_before': 0, 'audio_handle_frames_after': 0}


def sub_clip(sid, a, b, fps, talking=False, bad_enum=False):
    crop = {'speaker_head_mouth_box': [0.82, 0.15, 0.08, 0.18], 'speaker_full_body_box': [0.78, 0.15, 0.20, 0.73], 'must_preserve_action_box': [0.05, 0.30, 0.40, 0.50],
            'sharp_in_crop_zone': True, 'active_speech_tc_range': {'in_tc': tc(a, fps), 'out_tc': tc(b, fps)}, 'settle_buffer_applied_in_tc': None,
            'speaker_moves_during_subclip': False, 'suggested_split_s': None, 'limits': 'boxes approximate'} if talking else None
    speech = {'speaker_id': 'SPK_01', 'spoken_language': 'ta', 'speaker_role': 'SUBJECT_EXPLAINING', 'verbatim_transcript': '[00:00.5] test', 'english_translation': 'test',
              'transcription_status': 'clear', 'extracted_domain_facts': [], 'soundbite_grade': 'CONTEXT_ONLY'} if talking else None
    return {'sub_clip_id': sid, 'tc_confidence': 'HIGH', 'client_safe': True, 'risk_flags': [], 'ocr_text_on_screen': [], 'usability_grade': 'A' if not bad_enum else 'GREAT',
            'shot_role': 'PROCESS_ACTION_B_ROLL', 'pairing_constraints': [], 'max_usable_window': window(a, b, fps), 'must_include_action_peak': None,
            'hero_frame_tc': tc(a, fps), 'hero_frame_s': a / fps, 'hero_frame_index': a, 'action_completeness': 'STATIC_ENVIRONMENT',
            'visual_action_observed': 'test pattern', 'visual_action_uncertainty': '', 'why_sliced_here': 'whole clip',
            'people_and_speaker_analysis': {'people_count': 1 if talking else 0, 'people_roles': ['Subject_Speaking'] if talking else [], 'audio_nature': 'ON_CAMERA_SPEECH' if talking else 'MOS_SILENT',
                                            'mouth_visible': talking, 'looking_at_lens': False, 'uncertainty': '', 'speech_translation_block': speech, 'speaker_crop_module': crop},
            'camera_and_optics': {'native_shot_size': 'WS', 'camera_angle': 'Eye_Level', 'lens_feel': 'Standard', 'movement_type': 'Static', 'movement_direction': 'none', 'movement_speed': 'None',
                                  'movement_easing': 'Not_Applicable', 'has_3d_parallax': False, 'has_internal_scene_motion': False, 'subject_screen_direction': 'Neutral', 'depth_of_field': 'Deep_Sharp',
                                  'leading_lines': [], 'uncertainty': ''},
            'pacing_and_flow': {'entry_eye_grid': 'Mid_Center', 'exit_eye_grid': 'Mid_Center', 'kinetic_energy_score': 2, 'min_comprehension_hold_s': 1.0,
                                'time_manipulation_options': ['SLOW_MO_ELIGIBLE', 'HOLD_LAST_FRAME_OK'], 'natural_cut_points': [], 'accent_events': [{'tc': tc(a, fps), 's': a / fps, 'frame': a, 'description': 'start'}],
                                'text_safe_zone': None},
            'continuity_and_story': {'primary_fit_for_beats': ['BEAT_01'], 'secondary_fit_for_beats': [], 'beat_fit_reasoning': 'synthetic', 'beat_fit_basis': 'illustrative', 'beat_fit_limits': '',
                                     'process_stage': 'Stage_1_Setup', 'prerequisite_action': '', 'outcome_state': '', 'world_landmarks_and_props': ['test_pattern'], 'marketing_value_tag': 'PROCESS', 'mood_tag': 'Calm'},
            'audio_and_sfx_plan': {'clean_nat_sound_intervals': [], 'creative_sfx_cues': []},
            'technical_qc_and_remediation': {'defects_detected': [], 'stabilization_needed': False, 'horizon_rotation_deg': 0.0, 'voice_isolation_recommended': False, 'dual_mono_channel_fix': False, 'uncertainty': ''},
            'vfx_and_graphics_opportunities': [], 'editorial_ideas': ['use as a bed'], 'sub_clip_uncertainty': ''}


def synthetic_log(clip_id, filename, fps, frames, bad_enum=False, nine_lines=False):
    half = max(1, frames // 2)
    return {'clip_id': clip_id, 'filename': filename, 'descriptive_name': 'synthetic_test_clip', 'tc_confidence': 'HIGH', 'clip_overview': 'A test pattern.', 'clip_overview_uncertainty': '',
            'audio_observed': 'MIXED', 'lighting_and_weather': 'synthetic', 'exposure_health': 'Proper', 'contrast_profile': 'Standard_Normal', 'color_match_group_id': 'GRP_TEST',
            'max_safe_zoom_limit': 1.35, 'entities': [{'name': 'pattern', 'kind': 'other', 'first_seen_s': 0.0, 'last_seen_s': frames / fps, 'description': 'colour bars', 'basis': 'directly_seen', 'uncertainty': ''}],
            'sub_clips': [sub_clip('SUB_01', 0, half, fps), sub_clip('SUB_02', half, frames - 1, fps, talking=True, bad_enum=bad_enum)],
            'clip_level_notes_for_editor': [], 'summary_card_lines': [f'{i}. line' for i in range(1, 10 if nine_lines else 11)],
            'unavailable_or_uncertain': [{'field': 'speaker boxes', 'reason': 'synthetic'}]}
