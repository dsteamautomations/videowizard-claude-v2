"""Stage 1 prompt (model-test/run_both.py PROMPT, round 2), parametrised. The evidence-discipline section is verbatim."""
import json

MODES = {1: 'Mode 1: Speaker on screen (allow_speaker_audio=true, show_speaker_video=true)',
         2: 'Mode 2: Voice only (allow_speaker_audio=true, show_speaker_video=false)',
         3: 'Mode 3: Pure Visual Infill (allow_speaker_audio=false, show_speaker_video=false)',
         4: 'Mode 4: Picture only (allow_speaker_audio=false, show_speaker_video=true)'}


def mode_of(policy):
    a, v = bool(policy.get('allow_speaker_audio')), bool(policy.get('show_speaker_video'))
    return 1 if a and v else 2 if a else 4 if v else 3


def policy_paragraph(policy):
    mode = mode_of(policy)
    if mode == 3:
        return ('SPEAKER POLICY IN FORCE: Mode 3, Pure Visual Infill (allow_speaker_audio=false, show_speaker_video=false). All source speech will be muted in the film; '
                'transcribe and translate it ONLY so the editor has context and domain facts. Anyone visibly talking to camera or looking at the lens must be trimmed or cropped out. '
                'EXCEPTION: silent workers doing their job, or people with backs turned or too far to see lips (mouth_visible=false AND looking_at_lens=false) are allowed full frame.')
    if mode == 2:
        return ('SPEAKER POLICY IN FORCE: Mode 2, Voice only (allow_speaker_audio=true, show_speaker_video=false). Source speech may be kept as audio; the speaker must not be seen talking: '
                'anyone visibly talking to camera or looking at the lens must be trimmed or cropped out, exactly as in Mode 3, while the speech is logged in full for use on the audio track.')
    if mode == 1:
        return ('SPEAKER POLICY IN FORCE: Mode 1, Speaker on screen (allow_speaker_audio=true, show_speaker_video=true). Talking heads are allowed on screen; still log boxes, '
                'speech and settle buffers so the assembler can choose A-roll windows precisely.')
    return ('SPEAKER POLICY IN FORCE: Mode 4, Picture only (allow_speaker_audio=false, show_speaker_video=true). Source speech is muted; people may be seen talking. Log speech for context.')


def build(project_config, ffprobe_meta, fps, frames, beats, clip_tag, policy, audio_removed=False):
    n = len(beats)
    text = f"""You are Stage 1 (single-pass video ingestion) of a video editing pipeline. You inspect ONE raw clip once and log raw, observable evidence so that a later assembly stage (which has NOT seen the footage) can build a film from many such logs. Be exact, be literal, and never invent what you cannot see or hear.

PROJECT CONFIG (Stage 0):
{json.dumps(project_config, ensure_ascii=False, indent=1)}

FFPROBE FILE METADATA for the attached clip:
{json.dumps(ffprobe_meta, ensure_ascii=False, indent=1)}

{policy_paragraph(policy)}

GLOBAL RULES
1. Timecode discipline: log HH:MM:SS:FF at source_fps ({fps:g} fps) AND seconds AND integer source_frame_index (0 to {frames - 1}). Report tc_confidence HIGH, MEDIUM or NEEDS_BOUNDARY_CHECK per sub-clip.
2. Settle buffer and zero-handle rule: apply a 0.5 s safety buffer after a person stops talking or stops looking at the lens before a clean in_tc. Whenever an in_tc or out_tc is bounded by a speaker trim or a technical defect, set the matching video_handle_frames_before/after to 0. Record the buffer you applied in settle_buffer_applied_in_tc and the speech window in active_speech_tc_range.
3. Decoupled observation vs policy: you log raw observations and bounding boxes. You do NOT compute crop rectangles, zoom values, DaVinci transforms, cumulative zoom, or the final visual_eligibility enum. A deterministic solver does that from your boxes. Do not include those values anywhere.
4. Conditional blocks: speech_translation_block is null when no speech is audible in the sub-clip. speaker_crop_module is null unless mouth_visible or looking_at_lens is true for someone in the sub-clip; when it is filled, give the three boxes so the solver can hide the speaker while keeping the action.
5. Not every field can be determined from every clip. Where something is genuinely unobservable, give the most conservative value the schema allows and list the field with the reason in unavailable_or_uncertain. Never pad with plausible-sounding guesses.
6. Beats: the script is split into BEAT_01..BEAT_{n:02d} above. For each sub-clip give primary_fit_for_beats (Tier-1 direct, literal match: the visual shows exactly what the sentence says) and secondary_fit_for_beats (Tier-2 contextual or illustrative). Empty lists are valid. Explain in beat_fit_reasoning.

EVIDENCE DISCIPLINE (applies to every field)
- Match the certainty of every statement to its supporting evidence. Describe visual observations from visual evidence alone; attribute spoken content to the speaker and never promote a spoken claim into an observed fact.
- Never invent: unclear words, illegible text, exact coordinates, a preceding or following action you did not see, a risk to fill a field, or verification you did not perform. "Not visible in this clip" never means "does not exist".
- Every uncertainty, limits and basis field is mandatory. Use them for the consequential doubt about that block: approximate boundaries, occlusion, inferred identity of an object, unseen outcomes. An empty uncertainty string is allowed only when nothing consequential is in doubt.
- basis values: directly_seen (visible on screen), spoken_claim (said by someone), illustrative (a reasonable inference connecting what is seen to the script), uncertain.
- Mark partial or unreadable content rather than guessing. Approximate source timestamps are localisation leads; say approximate when a boundary is a transition rather than an exact instant.

PILLAR 1 — Spatio-temporal segmentation and sub-clip harvesting. Slice the clip whenever camera movement changes, a person starts or stops speaking, or an action changes state. Harvest ALL distinct usable sub-clips (ids SUB_{clip_tag}_01, _02, ...), including short ones, so the assembler has primary and secondary options. For each: shot_role, max_usable_window with separate video and audio handles, must_include_action_peak (the 1-3 s core moment that must survive any trim; null for static environment), action_completeness, pairing_constraints (e.g. "MUTUALLY_EXCLUSIVE_WITH: SUB_{clip_tag}_02" to avoid yo-yo zooms), natural_cut_points (subject exits frame, wipe, whip-pan), accent_events (visual or audio impacts for SFX and music sync), hero_frame_tc with hero_frame_index, usability_grade A/B/C/REJECT, and why_sliced_here. Every event carries tc, seconds and frame.

PILLAR 2 — People, multi-language audio and speaker isolation. visual_action_observed (objective), audio_nature, people_count and people_roles (Worker_Silent, Subject_Speaking, Bystander, Child...), mouth_visible, looking_at_lens. If speech is audible: speaker_id, ISO language code, speaker_role (never use cameraman or director chatter), verbatim transcript with timestamps, accurate English translation preserving negations, extracted_domain_facts each with matches_visual_on_screen, soundbite_grade. If a speaker leans into the action later in the sub-clip, prefer splitting the sub-clip (suggested_split_s, 0.5 s before) over a moving crop. Speech is logged per sub-clip; the sub-clip whose window contains the speech carries it.

PILLAR 3 — Cinematography and continuity: native_shot_size, camera_angle, lens_feel, movement_type/direction/speed/easing, has_3d_parallax, has_internal_scene_motion (hands, machine parts, wind, smoke), subject_screen_direction (180-degree axis), depth_of_field, leading_lines.

PILLAR 4 — Visual flow and pacing: entry_eye_grid and exit_eye_grid on the 3x3 grid (Top_Left ... Bottom_Right), kinetic_energy_score 1-10, min_comprehension_hold_s, time_manipulation_options (SLOW_MO_ELIGIBLE only if source_fps >= 50 and motion suits it), text_safe_zone with valid window and contrast.

PILLAR 5 — Script-beat alignment, process continuity and marketing value: beats as above, process_stage from project_config.process_stages, prerequisite_action and outcome_state, world_landmarks_and_props as standardised snake_case nouns (reuse the same noun for the same object everywhere), marketing_value_tag, mood_tag.

PILLAR 6 — Colour and audio: clip-level lighting_and_weather, exposure_health, contrast_profile, color_match_group_id (so matching shots can be graded together). Per sub-clip: clean_nat_sound_intervals (speech-free mechanical or ambient sound worth keeping on track A2, exact in/out) and creative_sfx_cues for track A3 with exact start/end/duration and a description; resolved_sfx_file is always HUMAN_TO_SOURCE because no asset manifest exists.

PILLAR 7 — Per-sub-clip client safety and technical QC (technical_qc_and_remediation): ocr_text_on_screen, client_safe plus risk_flags (missing PPE, trash or clutter, competitor brands, licence plates, children, copyrighted music), defects_detected with ranges (focus_hunt, exposure_pump, camera_bump, rolling_shutter, single_channel_audio, other), stabilization_needed, horizon_rotation_deg, voice_isolation_recommended, dual_mono_channel_fix.

EXTRA (beyond the blueprint, keep them): vfx_and_graphics_opportunities per sub-clip: where a callout, arrow, cutaway diagram, dynamic zoom, speed ramp, clean-plate removal or text overlay would help the explainer, with exact window and why. editorial_ideas per sub-clip: how an editor could use it. entities at clip level with first/last seen. clip_level_notes_for_editor for anything that does not fit a field.

FINALLY write summary_card_lines: exactly 10 lines in this order: 1 OVERVIEW, 2 SOURCE SPECS, 3 SUB-CLIPS HARVESTED (one line, semicolon separated with window, duration, grade), 4 SPEAKER & AUDIO STATUS, 5 SCRIPT BEAT MATCHES, 6 CONTINUITY & STAGE, 7 MARKETING & MOOD, 8 VISUAL FLOW of the best sub-clip, 9 AUDIO / SFX PLAN, 10 PAIRING & NOTES.

Return only the JSON object required by the response schema."""
    if audio_removed:
        text += ('\n\nAnalysis audio choice: original audio was removed from the attached analysis copy at the user request. '
                 'Report audio_observed as MOS_SILENT and every speech block as null; do not invent speech or sound. The original is preserved.')
    return text
