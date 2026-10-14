"""Stage 1 schema, built in code from one definition (model-test/run_both.py, plus the design/12 §A additions).
The strict form is validated locally and digested for identity; the wire form (enums as descriptions) is what Gemini receives."""
from copy import deepcopy


def S(**p): return {'type': 'string', **p}
def N(**p): return {'type': 'number', **p}
def B(): return {'type': 'boolean'}
def I(**p): return {'type': 'integer', **p}
def E(*v): return {'type': 'string', 'enum': list(v)}
def A(items): return {'type': 'array', 'items': items}
def O(props, required=None): return {'type': 'object', 'properties': props, 'required': required or list(props), 'additionalProperties': False}
def NUL(x): return {'anyOf': [x, {'type': 'null'}]}


BOX = {'type': 'array', 'items': N(), 'minItems': 4, 'maxItems': 4, 'description': '[x, y, w, h] normalised 0.00-1.00, origin top-left'}
TC = S(description='HH:MM:SS:FF at source_fps')
WINDOW = O({'in_tc': TC, 'out_tc': TC, 'in_s': N(), 'out_s': N(), 'in_frame': I(), 'out_frame': I(), 'duration_s': N(),
            'video_handle_frames_before': I(), 'video_handle_frames_after': I(), 'audio_handle_frames_before': I(), 'audio_handle_frames_after': I()})
PEAK = O({'in_tc': TC, 'out_tc': TC, 'in_s': N(), 'out_s': N(), 'duration_s': N()})
EVENT = O({'tc': TC, 's': N(), 'frame': I(description='source_frame_index'), 'description': S()})   # design/12: frame on every logged time
INTERVAL = O({'in_tc': TC, 'out_tc': TC, 'in_s': N(), 'out_s': N(), 'duration_s': N(), 'description': S()})
BASIS = E('directly_seen', 'spoken_claim', 'illustrative', 'uncertain')
FACT = O({'fact': S(), 'basis': BASIS, 'matches_visual_on_screen': B(), 'visual_evidence_s': NUL(N()), 'limits': S(description='what this fact does not establish; empty only if nothing consequential')})
SPEECH_BLOCK = O({'speaker_id': S(), 'spoken_language': S(), 'speaker_role': E('SUBJECT_EXPLAINING', 'CAMERAMAN_DIRECTOR_CHATTER', 'BACKGROUND_CHATTER'),
                  'verbatim_transcript': S(description='original language with [MM:SS.s] timestamps'), 'english_translation': S(), 'transcription_status': E('clear', 'partial', 'unintelligible'),
                  'extracted_domain_facts': A(FACT), 'soundbite_grade': E('A_SOUNDBITE', 'CONTEXT_ONLY', 'UNUSABLE_SPEECH')})
CROP_MODULE = O({'speaker_head_mouth_box': BOX, 'speaker_full_body_box': BOX, 'must_preserve_action_box': BOX, 'sharp_in_crop_zone': B(),
                 'active_speech_tc_range': NUL(O({'in_tc': TC, 'out_tc': TC})), 'settle_buffer_applied_in_tc': NUL(TC),   # design/12 additions (blueprint CLIP_04)
                 'speaker_moves_during_subclip': B(), 'suggested_split_s': NUL(N()), 'limits': S(description='approximation of the boxes, occlusion, anything the crop solver should know')})
DEFECT = E('focus_hunt', 'exposure_pump', 'camera_bump', 'rolling_shutter', 'single_channel_audio', 'other')
SUB_CLIP = O({
    'sub_clip_id': S(), 'tc_confidence': E('HIGH', 'MEDIUM', 'NEEDS_BOUNDARY_CHECK'),
    'client_safe': B(), 'risk_flags': A(S()), 'ocr_text_on_screen': A(S()),
    'usability_grade': E('A', 'B', 'C', 'REJECT'),
    'shot_role': E('ESTABLISHING', 'PROCESS_ACTION_B_ROLL', 'DETAIL_INSERT_B_ROLL', 'TALKING_HEAD_A_ROLL', 'HYBRID_SPEAKER_ACTION', 'TRANSITION'),
    'pairing_constraints': A(S()),
    'max_usable_window': WINDOW, 'must_include_action_peak': NUL(PEAK), 'hero_frame_tc': TC, 'hero_frame_s': N(), 'hero_frame_index': I(),
    'action_completeness': E('COMPLETE', 'PARTIAL_ONGOING', 'TRUNCATED_CUT_OFF', 'STATIC_ENVIRONMENT'),
    'visual_action_observed': S(), 'visual_action_uncertainty': S(description='what in visual_action_observed is inferred rather than seen; empty only if nothing'), 'why_sliced_here': S(),
    'people_and_speaker_analysis': O({'people_count': I(), 'people_roles': A(S()), 'audio_nature': E('MOS_SILENT', 'NAT_SOUND_ONLY', 'OFF_CAMERA_SPEECH', 'ON_CAMERA_SPEECH'),
                                      'mouth_visible': B(), 'looking_at_lens': B(), 'uncertainty': S(), 'speech_translation_block': NUL(SPEECH_BLOCK), 'speaker_crop_module': NUL(CROP_MODULE)}),
    'camera_and_optics': O({'native_shot_size': E('EWS', 'WS', 'MWS', 'MS', 'MCU', 'CU', 'ECU'), 'camera_angle': E('Eye_Level', 'High_Angle', 'Low_Angle', 'Overhead'),
                            'lens_feel': E('Ultra_Wide', 'Standard', 'Telephoto'), 'movement_type': E('Static', 'Pan', 'Tilt', 'Dolly', 'Handheld', 'Gimbal', 'Digital_Zoom'),
                            'movement_direction': S(), 'movement_speed': E('None', 'Slow', 'Medium', 'Fast'), 'movement_easing': E('Smooth_Bezier', 'Smooth_Linear_Trimmed', 'Abrupt_Linear', 'Not_Applicable'),
                            'has_3d_parallax': B(), 'has_internal_scene_motion': B(),
                            'subject_screen_direction': E('Left_to_Right', 'Right_to_Left', 'Toward_Lens', 'Away', 'Neutral'),
                            'depth_of_field': E('Shallow_Bokeh', 'Deep_Sharp'), 'leading_lines': A(S()), 'uncertainty': S()}),
    'pacing_and_flow': O({'entry_eye_grid': S(), 'exit_eye_grid': S(), 'kinetic_energy_score': I(minimum=1, maximum=10), 'min_comprehension_hold_s': N(),
                          'time_manipulation_options': A(E('SLOW_MO_ELIGIBLE', 'SPEED_WARP_OK', 'HOLD_LAST_FRAME_OK')),
                          'natural_cut_points': A(EVENT), 'accent_events': A(EVENT),
                          'text_safe_zone': NUL(O({'grid': S(), 'valid_in_tc': TC, 'valid_out_tc': TC, 'contrast': E('DARK_BG_USE_WHITE_TEXT', 'BRIGHT_BG_USE_DARK_TEXT')}))}),
    'continuity_and_story': O({'primary_fit_for_beats': A(S()), 'secondary_fit_for_beats': A(S()), 'beat_fit_reasoning': S(), 'beat_fit_basis': BASIS, 'beat_fit_limits': S(description='what the matched beats say that this sub-clip does NOT show'),
                               'process_stage': S(), 'prerequisite_action': S(), 'outcome_state': S(), 'world_landmarks_and_props': A(S()),
                               'marketing_value_tag': E('SCALE', 'PROCESS', 'QUALITY', 'PEOPLE_TRUST', 'TECHNOLOGY', 'RESULT'),
                               'mood_tag': E('Calm', 'Industrial', 'Energetic', 'Warm', 'Clinical')}),
    'audio_and_sfx_plan': O({'clean_nat_sound_intervals': A(INTERVAL),
                             'creative_sfx_cues': A(O({'target_track': E('A3'), 'sfx_type': S(), 'start_tc': TC, 'end_tc': TC, 'duration_s': N(), 'description': S(),
                                                       'resolved_sfx_file': E('HUMAN_TO_SOURCE')}))}),
    'technical_qc_and_remediation': O({'defects_detected': A(O({'defect': DEFECT, 'in_tc': TC, 'out_tc': TC, 'description': S()})),
                                       'stabilization_needed': B(), 'horizon_rotation_deg': N(), 'voice_isolation_recommended': B(), 'dual_mono_channel_fix': B(), 'uncertainty': S()}),
    'vfx_and_graphics_opportunities': A(O({'type': S(description='e.g. callout_label, animated_arrow, cutaway_diagram, dynamic_zoom, speed_ramp, clean_plate_removal, text_overlay'),
                                           'in_tc': TC, 'out_tc': TC, 'what_and_why': S()})),
    'editorial_ideas': A(S(description='how an editor could use this sub-clip in the film')),
    'sub_clip_uncertainty': S(description='consequential uncertainties of this sub-clip as a whole: approximate boundaries, unseen outcomes'),
})


def build_schema(clip_id, filename, max_safe_zoom_hint='1.35 for 1080p source on a 1080p timeline; 2.0 for 4K'):
    return O({
        'clip_id': E(clip_id), 'filename': E(filename), 'descriptive_name': S(description='short filename-safe name for this clip'),
        'tc_confidence': E('HIGH', 'MEDIUM', 'NEEDS_BOUNDARY_CHECK'),
        'clip_overview': S(description='2-3 sentences: what the clip shows end to end'), 'clip_overview_uncertainty': S(),
        'audio_observed': E('MOS_SILENT', 'NAT_SOUND_ONLY', 'OFF_CAMERA_SPEECH', 'ON_CAMERA_SPEECH', 'MIXED'),
        'lighting_and_weather': S(), 'exposure_health': E('Proper', 'Overexposed_Highlights', 'Underexposed_Shadows', 'Mixed'),
        'contrast_profile': E('Flat_Low_Contrast', 'Standard_Normal', 'High_Contrast'), 'color_match_group_id': S(),
        'max_safe_zoom_limit': N(description=max_safe_zoom_hint),
        'entities': A(O({'name': S(), 'kind': E('person', 'tool', 'material', 'machine', 'structure', 'vehicle', 'text', 'other'), 'first_seen_s': N(), 'last_seen_s': N(), 'description': S(), 'basis': BASIS, 'uncertainty': S()})),
        'sub_clips': A(SUB_CLIP),
        'clip_level_notes_for_editor': A(S()),
        'summary_card_lines': {'type': 'array', 'items': S(), 'minItems': 10, 'maxItems': 10},
        'unavailable_or_uncertain': A(O({'field': S(), 'reason': S()})),
    })


def wire_schema(s):
    """Gemini rejects schemas with roughly more than 100 enum values: every multi-value enum goes into the description. Enums are re-checked locally."""
    if isinstance(s, dict):
        if 'enum' in s and s.get('type') == 'string' and len(s['enum']) > 1:
            return {'type': 'string', 'description': (s.get('description', '') + ' Exactly one of: ' + ' | '.join(s['enum'])).strip()}
        return {k: wire_schema(v) for k, v in s.items()}
    if isinstance(s, list):
        return [wire_schema(x) for x in s]
    return s


def count_enums(s):
    if isinstance(s, dict):
        return (len(s['enum']) if 'enum' in s and len(s.get('enum') or []) > 1 else 0) + sum(count_enums(v) for v in s.values())
    if isinstance(s, list):
        return sum(count_enums(x) for x in s)
    return 0


def errors(document, schema):
    from jsonschema import Draft202012Validator
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message[:160]}" for e in sorted(Draft202012Validator(schema).iter_errors(document), key=lambda e: list(e.absolute_path))]


def sub_clip_schema():
    return deepcopy(SUB_CLIP)
