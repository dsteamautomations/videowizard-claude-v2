"""The options package: beats with timeline windows (narration stays one continuous file; windows follow its natural gaps, design/17 C1),
summary cards, the eligible sub-clip table derived from the clip logs and the Stage 1.5 solver, learned client rules."""
import math
import re
from fractions import Fraction

SHOT_SIZES = ['EWS', 'WS', 'MWS', 'MS', 'MCU', 'CU', 'ECU']
GRID = ['Top_Left', 'Top_Center', 'Top_Right', 'Mid_Left', 'Mid_Center', 'Mid_Right', 'Bottom_Left', 'Bottom_Center', 'Bottom_Right']


def frames_of(seconds, fps):
    return int(round(Fraction(str(seconds)) * Fraction(str(fps))))


def beat_windows(script_beats, timing, timeline_fps, audio_duration_s):
    """Beat i runs from its first word's start to beat i+1's first word's start (last: to the end of the recording). Frames at timeline fps."""
    words = timing['words']
    starts = []
    for b in script_beats:
        own = [w for w in words if w['passage_id'] == b['passage_id']]
        if not own:
            raise ValueError(f"narration timing has no words for {b['beat_id']}")
        starts.append((b, own[0]['start_s'], own[-1]['end_s']))
    out = []
    for i, (b, first, last) in enumerate(starts):
        start_s = 0.0 if i == 0 else first
        end_s = starts[i + 1][1] if i + 1 < len(starts) else float(audio_duration_s)
        a, z = frames_of(start_s, timeline_fps), frames_of(end_s, timeline_fps)
        if z <= a:
            raise ValueError(f"{b['beat_id']} has no timeline length")
        out.append({'beat_id': b['beat_id'], 'passage_id': b['passage_id'], 'text': b['text'], 'timeline_start_frame': a, 'timeline_end_frame': z,
                    'target_beat_frames': z - a, 'narration_first_word_s': first, 'narration_last_word_s': last, 'window_start_s': start_s, 'window_end_s': end_s})
    return out


def lighting_class(text):
    t = (text or '').lower()
    if 'hard' in t and 'sun' in t:
        return 'HARD_SUN'
    if 'overcast' in t or 'soft' in t:
        return 'SOFT_OVERCAST'
    if 'interior' in t or 'mixed' in t:
        return 'MIXED_INTERIOR'
    return 'UNCLASSIFIED'


def confidence_of(sub):
    """R14: uncertainty is a cost. 1.0 when every uncertainty field is empty and tc_confidence HIGH; lower otherwise."""
    score = 1.0
    if sub.get('tc_confidence') == 'MEDIUM':
        score -= 0.2
    if sub.get('tc_confidence') == 'NEEDS_BOUNDARY_CHECK':
        score -= 0.5
    for text in (sub.get('visual_action_uncertainty'), sub.get('sub_clip_uncertainty'), (sub.get('people_and_speaker_analysis') or {}).get('uncertainty'),
                 (sub.get('camera_and_optics') or {}).get('uncertainty'), (sub.get('continuity_and_story') or {}).get('beat_fit_limits')):
        if str(text or '').strip():
            score -= 0.08
    return round(max(0.0, score), 2)


def sub_clip_row(clip, log, sub, timeline_fps):
    src_fps = Fraction(str(clip.get('fps') or timeline_fps))
    w = sub['max_usable_window']
    st = sub['stage15']
    cam, pace, story, people = sub['camera_and_optics'], sub['pacing_and_flow'], sub['continuity_and_story'], sub['people_and_speaker_analysis']
    peak = sub.get('must_include_action_peak')
    crop = (st.get('crop_solution') or {}) if st['visual_eligibility'] == 'ELIGIBLE_WITH_CROP' else {}
    return {'sub_clip_id': f"{clip['id']}:{sub['sub_clip_id']}", 'log_sub_clip_id': sub['sub_clip_id'], 'clip_id': clip['id'], 'clip_name': clip['name'], 'source_fps': str(src_fps), 'source_width': clip.get('width'), 'source_height': clip.get('height'),
            'in_frame': w['in_frame'], 'out_frame': w['out_frame'], 'duration_s': w['duration_s'],
            'handles': {k: w[k] for k in ('video_handle_frames_before', 'video_handle_frames_after')},
            'grade': sub['usability_grade'], 'shot_role': sub['shot_role'], 'client_safe': st.get('client_safe_effective', sub['client_safe']),
            'risk_flags': st.get('risk_flags_effective', sub.get('risk_flags') or []), 'risk_flags_waived': st.get('risk_flags_waived') or [],
            'native_shot_size': cam['native_shot_size'], 'effective_shot_size': st.get('effective_post_crop_shot_size') or cam['native_shot_size'],
            'eligibility': st['visual_eligibility'], 'crop_rect': crop.get('crop_rect'), 'zoom': crop.get('zoom_x'), 'position': [crop.get('position_x'), crop.get('position_y')] if crop else None,
            'ui_path': st.get('ui_path'), 'still_eligible': st.get('still_frame_dynamic_zoom_eligible'),
            'entry_eye_grid': pace['entry_eye_grid'], 'exit_eye_grid': pace['exit_eye_grid'], 'screen_direction': cam['subject_screen_direction'],
            'lighting': lighting_class(log.get('lighting_and_weather')), 'color_group': log.get('color_match_group_id'), 'energy': pace['kinetic_energy_score'],
            'min_hold_s': pace['min_comprehension_hold_s'], 'action_peak': {'in_frame': frames_of(peak['in_s'], src_fps), 'out_frame': frames_of(peak['out_s'], src_fps)} if peak else None,
            'pairing_constraints': sub.get('pairing_constraints') or [],
            'natural_cut_frames': sorted({e.get('frame') if isinstance(e.get('frame'), int) else frames_of(e['s'], src_fps) for e in pace.get('natural_cut_points') or []}),
            'accent_frames': sorted({e.get('frame') if isinstance(e.get('frame'), int) else frames_of(e['s'], src_fps) for e in pace.get('accent_events') or []}),
            'primary_fits': story.get('primary_fit_for_beats') or [], 'secondary_fits': story.get('secondary_fit_for_beats') or [], 'beat_fit_basis': story.get('beat_fit_basis'),
            'beat_fit_limits': story.get('beat_fit_limits'), 'landmarks': story.get('world_landmarks_and_props') or [], 'process_stage': story.get('process_stage'),
            'outcome_state': story.get('outcome_state'), 'action_completeness': sub.get('action_completeness'),
            'nat_sound': [{'in_frame': frames_of(i['in_s'], src_fps), 'out_frame': frames_of(i['out_s'], src_fps), 'description': i.get('description', '')} for i in sub['audio_and_sfx_plan'].get('clean_nat_sound_intervals') or []],
            'sfx_cues': sub['audio_and_sfx_plan'].get('creative_sfx_cues') or [],
            'speech': bool(people.get('speech_translation_block')), 'facts_match_visual': any(f.get('matches_visual_on_screen') for f in ((people.get('speech_translation_block') or {}).get('extracted_domain_facts') or [])),
            'tc_confidence': sub.get('tc_confidence'), 'confidence': confidence_of(sub), 'stabilization_needed': bool((sub.get('technical_qc_and_remediation') or {}).get('stabilization_needed')),
            'horizon_rotation_deg': (sub.get('technical_qc_and_remediation') or {}).get('horizon_rotation_deg') or 0.0,
            'editorial_ideas': sub.get('editorial_ideas') or []}


def scene_fits(rows, windows, paragraphs):
    """design/125 P8: after the scenes are approved, a row fits a scene directly when the clip study put it in primary for a paragraph whose words
    fall inside that scene, related when in secondary, and by chapter when its process_stage is the scene's chapter. paragraphs: the script beat id
    (the clip study's beat) → (first frame, last frame) of its words on the timeline. primary_fits = direct ∪ chapter (what consumers read),
    secondary_fits = related; fit_kinds names the kind per scene; the clip study's own lists stay in model_fits."""
    over = {p: [w['beat_id'] for w in windows if w['timeline_start_frame'] < z and a < w['timeline_end_frame']] for p, (a, z) in paragraphs.items()}
    for r in rows:
        r['model_fits'] = {'primary': r['primary_fits'], 'secondary': r['secondary_fits']}
        direct = {b for p in r['primary_fits'] for b in over.get(p, [])}
        related = {b for p in r['secondary_fits'] for b in over.get(p, [])}
        chapter = {w['beat_id'] for w in windows if r.get('process_stage') and r['process_stage'] in w['process_stages']}
        kinds = {}
        for w in windows:
            b = w['beat_id']
            kind = 'direct' if b in direct else 'chapter' if b in chapter else 'related' if b in related else None
            if kind:
                kinds[b] = kind
        r['primary_fits'] = [b for b, k in kinds.items() if k != 'related']
        r['secondary_fits'] = [b for b, k in kinds.items() if k == 'related']
        r['fit_kinds'] = kinds
        r['fit_source'] = 'clip study by paragraph, and scene chapter'
    return rows


def coverage(beats, rows, policy):
    """Blueprint §3 step 1.3 + design/17: counts per beat by primary/secondary fit and grade, uncoverable beats, low-confidence primaries, alerts."""
    report = []
    for b in beats:
        prim = [r for r in rows if b['beat_id'] in r['primary_fits'] and r['eligibility'].startswith('ELIGIBLE')]
        sec = [r for r in rows if b['beat_id'] in r['secondary_fits'] and r['eligibility'].startswith('ELIGIBLE')]
        window_s = b['target_beat_frames'] / 25.0
        holds = [r['min_hold_s'] for r in prim + sec]
        entry = {'beat_id': b['beat_id'], 'target_beat_frames': b['target_beat_frames'],
                 'primary': {g: sum(1 for r in prim if r['grade'] == g) for g in ('A', 'B', 'C')}, 'secondary': {g: sum(1 for r in sec if r['grade'] == g) for g in ('A', 'B', 'C')},
                 'candidates': [r['sub_clip_id'] for r in prim] + [r['sub_clip_id'] for r in sec if r not in prim],
                 'low_confidence': [r['sub_clip_id'] for r in prim if r['confidence'] < 0.6], 'alerts': [],
                 'kinds': {k: sum(1 for r in rows if r['eligibility'].startswith('ELIGIBLE') and _kind(r, b['beat_id']) == k) for k in ('direct', 'related', 'chapter')}}   # design/125 P8
        if not prim and not sec:
            entry['alerts'].append('ZERO COVERAGE: no eligible sub-clip fits this beat' + (' (Mode 1: stay on A-roll is possible)' if policy.get('show_speaker_video') else '; same-stage detail shot or a visuals gap'))
        if holds and min(holds) > window_s:
            entry['alerts'].append(f'UNCOVERABLE: every candidate needs at least {min(holds)} s but the beat is {window_s:.2f} s')
        report.append(entry)
    return report


def _kind(r, bid):
    """How a row fits a scene: its fit_kinds after the scenes are approved; before, the clip study's own primary (direct) or secondary (related)."""
    return (r.get('fit_kinds') or {}).get(bid) or ('direct' if bid in r['primary_fits'] else 'related' if bid in r['secondary_fits'] else None)


def with_steps(beats, sentences):
    """design/91 N17: a scene's steps are its timed sentences, numbered BEAT_03.S2; a sentence belongs to the scene its first word starts in."""
    out = []
    for b in beats:
        own = [s for s in sentences or [] if b['timeline_start_frame'] <= s['start_frame'] < b['timeline_end_frame']]
        out.append({**b, 'steps': [{'step_id': f"{b['beat_id']}.S{n}", 'text': s['text'], 'start_frame': s['start_frame'], 'end_frame': s['end_frame']} for n, s in enumerate(own, 1)]})
    return out


def build(run, production, beats, cards, rows, landmarks, entities, learned_rules, timeline, policy, prompt, narration=None):
    beats = with_steps(beats, (narration or {}).get('sentences'))
    return {'contract': 'vw2-options-package-v1', 'project': {'code': run['code'], 'client': run.get('client'), **production}, 'timeline': timeline, 'policy': policy,
            'narration': narration or {}, 'beats': beats, 'cards': cards, 'sub_clips': rows, 'landmarks': sorted(landmarks), 'entities': entities, 'learned_rules': learned_rules,
            'coverage': coverage(beats, rows, policy), 'prompt': prompt,
            'shapes': {'options': {'contract': 'vw2-options-v1', 'options': [{'option_number': 1, 'beat_id': 'BEAT_01', 'rank': 'PRIMARY|SECONDARY',
                                                                              'events': [{'sub_clip_id': '', 'source_in_frame': 0, 'source_out_frame': 0, 'hold_last_frame': False, 'crop': 'solver|full|hands_only',
                                                                                          'a2_intervals': [{'in_frame': 0, 'out_frame': 0}], 'marker': {'name': '', 'note': '', 'colour': 'Blue'},
                                                                                          'match': 'direct|b_roll', 'evidence': 'the log fields showing this shot shows the words it sits under',
                                                                                          'decision': {'kind': 'b_roll|reuse|check_by_eye|poor_quality|join|other', 'question': 'what the operator decides'},
                                                                                          'hold_reason': 'only for a real shot over 4 s', 'illustrates_word_id': '', 'action_word_id': ''},
                                                                                         {'blank': True, 'timeline_frames': 75, 'intent': 'what the AI video or animation must show', 'short_reason': 'only for a blank under 3 s'}],
                                                                              'reasoning': 'why these sub-clips, which log fields drove it', 'log_fields_cited': ['SUB_x.primary_fit_for_beats'],
                                                                              'best_unchosen': {'sub_clip_id': '', 'rule': 'the rule that excluded it'},
                                                                              'steps': [{'step_id': 'BEAT_01.S1', 'event': 1, 'why': 'the logged action, process_stage or outcome_state that shows this step',
                                                                                         'claim': False}],   # design/91 N17: every step of the scene once
                                                                              'carries_over': ['what the step before left, which must still be visible'],   # design/91 N14
                                                                              'moves_place': 'only when the narration moves to another place mid-process'}],
                                   'qc_self': {f'Q{i}': {'pass': True, 'evidence': ''} for i in range(1, 9)}}}}
