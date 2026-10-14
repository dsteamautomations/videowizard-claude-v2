"""clip-log-v1 unit tests (design/14 §3): schema and wire form, the Stage 1.5 solver on the blueprint's own numbers, the gate on the real Flash C0120 log."""
import json
from copy import deepcopy

import pytest

from app.clip_log import CONTRACT, gate, schema as S, solver
from clip_log_fixture import C0120, real_log, real_request, synthetic_log


# ---------- schema (E15, E16) ----------

def test_wire_form_has_no_multi_value_enums_and_strict_digest_is_stable():
    from app.analysis import digest
    strict = S.build_schema('CLIP_X', 'x.mp4')
    wire = S.wire_schema(strict)
    assert S.count_enums(wire) == 0 and S.count_enums(strict) > 80
    assert 'Exactly one of: A | B | C | REJECT' in json.dumps(wire)
    assert digest(strict) == digest(S.build_schema('CLIP_X', 'x.mp4'))
    looser = deepcopy(strict); looser['properties']['clip_overview']['description'] = 'changed description only'
    assert digest(S.wire_schema(looser)) != digest(wire)  # wire text differs
    assert digest(strict) != digest({**strict, 'properties': {**strict['properties'], 'new_field': {'type': 'string'}}})


# ---------- solver (E6–E11, E14) ----------

def test_e8_blueprint_clip04_numbers():
    # Blueprint CLIP_04 worked example: 1.45x, posX -431.3, posY -7.8 (speaker on the left edge, sieve action on the right)
    # Blueprint Part B, CLIP_04 SUB_04_02 boxes through the blueprint's own solver code (ported verbatim). The blueprint's prose example
    # (-431.3 / -7.8 / crop y 0.15) was hand-rounded; its code gives -431.5 / +7.8 / 0.16. The code is the authority ("run this deterministic solver").
    sol = solver.compute_davinci_crop([0.00, 0.12, 0.29, 0.88], [0.35, 0.20, 0.60, 0.60], 3840, 2160, 1920, 1080, 2.0)
    assert sol['feasible'] and sol['zoom_x'] == 1.45 and sol['position_x'] == -431.5 and sol['position_y'] == 7.8 and sol['crop_rect'] == [0.31, 0.16, 0.69, 0.69] and sol['within_safe_zoom_limit']


def test_e9_c0120_overlap_is_infeasible_with_reason():
    log = real_log()
    sub2 = next(s for s in log['sub_clips'] if s['sub_clip_id'].endswith('_02'))
    m = sub2['people_and_speaker_analysis']['speaker_crop_module']
    sol = solver.compute_davinci_crop(m['speaker_full_body_box'], m['must_preserve_action_box'], 1920, 1080, 1920, 1080, 1.35)
    assert sol['feasible'] is False and 'overlaps' in sol['reason']


def test_e6_e7_e10_e11_e14_eligibility_rules():
    base = synthetic_log('CLIP_T', 't.mp4', 25.0, 100)
    policy = {'allow_speaker_audio': False, 'show_speaker_video': False}
    tl = {'width': 1920, 'height': 1080, 'fps': 25}
    clip = {'width': 1920, 'height': 1080, 'fps': '25/1'}
    # E6 speaker visible, no boxes
    log = deepcopy(base); log['sub_clips'][1]['people_and_speaker_analysis']['speaker_crop_module'] = None
    solver.solve(log, policy, clip, tl)
    assert log['sub_clips'][1]['stage15']['visual_eligibility'] == 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT' and 'no crop boxes' in log['sub_clips'][1]['stage15']['crop_solution']['reason']
    # E7 boxes outside 0-1 / zero size
    log = deepcopy(base); log['sub_clips'][1]['people_and_speaker_analysis']['speaker_crop_module']['speaker_full_body_box'] = [0.9, 0.0, 0.5, 0.0]
    solver.solve(log, policy, clip, tl)
    assert log['sub_clips'][1]['stage15']['visual_eligibility'] == 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT' and 'invalid crop boxes' in log['sub_clips'][1]['stage15']['notes']
    # E10 cumulative zoom over the limit → reject with reason; E14 slow-mo stripped at 25 fps
    log = deepcopy(base); log['sub_clips'][1]['people_and_speaker_analysis']['speaker_crop_module']['must_preserve_action_box'] = [0.02, 0.35, 0.24, 0.20]
    log['sub_clips'][1]['people_and_speaker_analysis']['speaker_crop_module']['speaker_full_body_box'] = [0.30, 0.15, 0.25, 0.73]
    log['sub_clips'][1]['people_and_speaker_analysis']['speaker_crop_module']['speaker_head_mouth_box'] = [0.35, 0.15, 0.10, 0.20]
    solver.solve(log, policy, clip, tl)
    st = log['sub_clips'][1]['stage15']
    assert st['visual_eligibility'] == 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT' and st['crop_solution']['within_safe_zoom_limit'] is False and 'exceeds' in st['crop_solution']['reason']
    assert st['time_manipulation_options'] == ['HOLD_LAST_FRAME_OK'] and any('SLOW_MO' in n for n in st['notes'])
    # E11 head outside body → NEEDS_BOUNDARY_CHECK
    log = deepcopy(base); log['sub_clips'][1]['people_and_speaker_analysis']['speaker_crop_module']['speaker_head_mouth_box'] = [0.05, 0.05, 0.10, 0.10]
    solver.solve(log, policy, clip, tl)
    assert log['sub_clips'][1]['tc_confidence'] == 'NEEDS_BOUNDARY_CHECK'
    # the clean case: silent sub-clip AS_IS, talking sub-clip cropped; Mode 1 shows the speaker instead
    log = deepcopy(base); solver.solve(log, policy, clip, tl)
    assert [s['stage15']['visual_eligibility'] for s in log['sub_clips']] == ['ELIGIBLE_AS_IS', 'ELIGIBLE_WITH_CROP']
    assert log['sub_clips'][1]['stage15']['ui_path'].startswith('Inspector') and log['sub_clips'][1]['stage15']['effective_post_crop_shot_size'] in ('WS', 'MWS', 'MS')
    log = deepcopy(base); solver.solve(log, {'allow_speaker_audio': True, 'show_speaker_video': True}, clip, tl)
    assert log['sub_clips'][1]['stage15']['visual_eligibility'] == 'ELIGIBLE_A_ROLL_SPEAKER'
    # 4K source → zoom cap 2.0; 1080p → 1.35 even if the model says more
    assert solver.max_safe_zoom(3840, 2160, 1920, 1080, 5.0) == 2.0 and solver.max_safe_zoom(1920, 1080, 1920, 1080, 5.0) == 1.35 and solver.max_safe_zoom(1920, 1080, 1920, 1080, 1.2) == 1.2


# ---------- gate on the real log (E1–E5, E12, E13, E17, E21) ----------

def test_e1_real_flash_log_retained_with_experiment_eligibility():
    req = real_request()
    reviewed = gate.review(json.dumps(real_log()), req)
    assert reviewed['status'] == 'retained' and reviewed['identity_errors'] == [] and reviewed['excluded_sub_clips'] == []
    elig = [s['stage15']['visual_eligibility'] for s in reviewed['log']['sub_clips']]
    assert elig == ['ELIGIBLE_AS_IS', 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT', 'ELIGIBLE_AS_IS']   # as in model-test/REPORT.md round 2
    summary = gate.summary_of(reviewed, req['clip'])
    assert summary['sub_clips'] == 3 and summary['speech_present'] and len(summary['summary_card']) == 10 and summary['descriptive_name'].startswith('mason')
    doc = gate.evidence_document(reviewed, req, req['clip'])
    assert doc['contract_version'] == CONTRACT and doc['log']['sub_clips'][1]['stage15']['crop_solution']['feasible'] is False


def test_e2_invalid_enum_excludes_only_that_sub_clip():
    log = real_log(); log['sub_clips'][0]['usability_grade'] = 'GREAT'
    reviewed = gate.review(json.dumps(log), real_request())
    assert reviewed['status'] == 'retained' and [e['sub_clip_id'] for e in reviewed['excluded_sub_clips']] == [log['sub_clips'][0]['sub_clip_id']]
    assert len(reviewed['log']['sub_clips']) == 2 and 'usability_grade' in reviewed['excluded_sub_clips'][0]['errors'][0]


def test_e3_wrong_identity_is_a_mismatch_not_a_retry():
    log = real_log(); log['clip_id'] = 'CLIP_OTHER'
    reviewed = gate.review(json.dumps(log), real_request())
    assert reviewed['status'] == 'identity_mismatch' and reviewed['identity_errors'] and reviewed['log'] is None


def test_e4_nine_card_lines_is_a_gap_not_a_failure():
    log = real_log(); log['summary_card_lines'] = log['summary_card_lines'][:9]
    reviewed = gate.review(json.dumps(log), real_request())
    assert reviewed['status'] == 'retained' and any('summary_card_lines has 9' in g for g in reviewed['gaps'])


def test_e5_no_speech_anywhere_is_accepted():
    log = real_log()
    for s in log['sub_clips']:
        s['people_and_speaker_analysis'].update(speech_translation_block=None, speaker_crop_module=None, mouth_visible=False, looking_at_lens=False, audio_nature='NAT_SOUND_ONLY')
    reviewed = gate.review(json.dumps(log), real_request())
    assert reviewed['status'] == 'retained' and all(s['stage15']['visual_eligibility'] == 'ELIGIBLE_AS_IS' for s in reviewed['log']['sub_clips'])


def test_e12_e13_timecode_disagreement_and_frames_outside_clip():
    log = real_log()
    log['sub_clips'][0]['max_usable_window']['in_s'] = 3.0            # tc says 0
    log['sub_clips'][2]['max_usable_window']['out_frame'] = 5000       # beyond 960
    reviewed = gate.review(json.dumps(log), real_request())
    assert any('in_tc' in g and 'disagree' in g for g in reviewed['gaps'])
    assert [e['sub_clip_id'] for e in reviewed['excluded_sub_clips']] == [log['sub_clips'][2]['sub_clip_id']]


def test_e17_speech_reported_although_audio_removed_is_a_gap():
    req = real_request(); req['audio_removed'] = True
    reviewed = gate.review(json.dumps(real_log()), req)
    assert any('audio was removed' in g for g in reviewed['gaps'])


def test_e21_no_uncertainty_with_filled_blocks_is_surfaced():
    log = real_log(); log['unavailable_or_uncertain'] = []
    reviewed = gate.review(json.dumps(log), real_request())
    assert any('no uncertainty' in g for g in reviewed['gaps'])


def test_unstructured_answer_is_retained_not_failed():
    reviewed = gate.review('not json {', real_request())
    assert reviewed['status'] == 'retained_unstructured'


# ---------- request builder (identity, mode line, audio removed) ----------

def test_build_request_clip_log_identity_mode_and_audio_sentence():
    from app import analysis
    procedure = {'contract_version': 'clip-log-v1', 'model': 'gemini-3.8-flash', 'settings': {'thinking_level': 'HIGH', 'processing_mode': 'AGENTIC', 'media_resolution': 'MEDIA_RESOLUTION_HIGH', 'max_output_tokens': 65536}}
    run = {'id': 'r1', 'code': 'VW-9', 'client': 'VK'}
    brief = {'purpose': 'p', 'audience': 'a', 'tone': 't', 'message': 'm', 'content_digest': 'b', 'production': {'show_speaker_video': False, 'process_stages': ['Stage_1_Setup'], 'brand_and_safety_rules': [], 'field_speech_languages': ['en', 'ta'], 'narration_language': 'en', 'target_runtime_s': 90}}
    script = {'content_digest': 's', 'passages': {'P001': 'One.', 'P002': 'Two.'}, 'beats': [{'beat_id': 'BEAT_01', 'passage_id': 'P001', 'text': 'One.'}, {'beat_id': 'BEAT_02', 'passage_id': 'P002', 'text': 'Two.'}]}
    clip = {'id': 'abc123def4567890', 'name': 'c.mp4', 'sha256': 'a' * 64, 'bytes': 1, 'duration_s': 2.0, 'has_audio': True, 'width': 1920, 'height': 1080, 'fps': '25/1', 'audio_channels': 2, 'audio_sample_rate_hz': 48000}
    a = analysis.build_request(run, procedure, brief, script, clip, {'camera_audio': 'excluded'})
    assert a['contract_version'] == CONTRACT and a['identity']['clip_tag'] == 'ABC123DEF456' and a['duration_frames'] == 50
    assert 'Mode 3' in a['prompt'] and 'BEAT_01..BEAT_02' in a['prompt'] and '"target_runtime_seconds": 90' in a['prompt'] and 'audio was removed' not in a['prompt']
    b = analysis.build_request(run, procedure, brief, script, clip, {'camera_audio': 'allowed'})
    assert 'Mode 2' in b['prompt'] and b['analysis_key'] != a['analysis_key']
    c = analysis.build_request(run, procedure, {**brief, 'production': {**brief['production'], 'show_speaker_video': True}}, script, clip, {'camera_audio': 'allowed'})
    assert 'Mode 1' in c['prompt']
    d = analysis.build_request(run, procedure, brief, script, clip, {'camera_audio': 'excluded', 'understand_audio': False})
    assert 'audio was removed' in d['prompt'] and d['audio_removed'] and d['ffprobe_meta']['audio_channels'] == 0
    assert S.count_enums(a['wire_schema']) == 0 and a['schema']['properties']['clip_id']['enum'] == ['ABC123DEF456']


@pytest.mark.skipif(True, reason='live probe: run by hand with a key (design/14 E23)')
def test_e23_live_schema_probe():
    pass
