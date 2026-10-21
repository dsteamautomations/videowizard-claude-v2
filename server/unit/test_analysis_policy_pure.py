"""design/60 L20: "no brand or safety rules" at the brief waives PPE risk flags from the start of the analysis."""
from app import analysis as A
from app import analysis_jobs as AJ
from app.clip_log import solver


def test_no_rules_at_the_brief_waives_the_ppe_flags_from_the_start():
    out = AJ.start_policy({'understand_audio': True, 'camera_audio': 'excluded'}, {'brand_and_safety_rules': []})
    assert out['waived_risk_flags'] == list(AJ.PPE_WAIVERS) and 'no brand or safety rules' in out['waiver_note']
    assert out['understand_audio'] is True and out['camera_audio'] == 'excluded'


def test_a_rule_at_the_brief_or_an_operator_waiver_leaves_the_policy_alone():
    kept = {'understand_audio': True}
    assert AJ.start_policy(kept, {'brand_and_safety_rules': ['PPE required on site']}) == kept
    given = {'understand_audio': True, 'waived_risk_flags': ['sandal'], 'note': 'their words'}
    assert AJ.start_policy(given, {'brand_and_safety_rules': []}) == given
    assert AJ.start_policy(kept, {}) ['waived_risk_flags'] == list(AJ.PPE_WAIVERS)   # no production block at all: no rules


def test_the_ppe_waivers_match_the_model_flag_names_and_nothing_else():
    for flag in ('missing_ppe_gloves', 'open_toed_sandals', 'no_hard_hat', 'worker_without_helmet', 'barefoot_worker', 'missing_safety_goggles', 'no_high_vis_vest'):
        assert solver.waived(flag, AJ.PPE_WAIVERS), flag
    for flag in ('competitor_logo', 'staged_scene', 'child_on_site', 'alcohol_visible', 'unsafe_scaffold_height'):
        assert not solver.waived(flag, AJ.PPE_WAIVERS), flag


def test_the_request_policy_carries_the_waivers_when_present_and_nothing_extra_when_not():
    production = {'show_speaker_video': False}
    plain = A.request_policy({'camera_audio': 'allowed'}, production)
    assert plain == {'allow_speaker_audio': True, 'show_speaker_video': False}
    waived = A.request_policy({'camera_audio': 'excluded', 'waived_risk_flags': ['ppe', 'sandal'], 'waiver_note': 'the brief recorded no brand or safety rules'}, production)
    assert waived == {'allow_speaker_audio': False, 'show_speaker_video': False, 'waived_risk_flags': ['ppe', 'sandal'], 'waiver_note': 'the brief recorded no brand or safety rules'}
