"""design/125 stage 7, builder B: the crop rule (P4, P5, P6) on VW-11's real pieces, and the old ways retired by refusal (design/35 "Old ways")."""
import pytest

from app.clip_log import solver
from app.errors import Problem

SPEECH = {'speaker_id': 'SPK_01', 'verbatim_transcript': 'x', 'english_translation': 'x'}


def sub(body=None, head=None, keep=None, speech=False, mouth=True, lens=False):
    crop = {'speaker_head_mouth_box': head, 'speaker_full_body_box': body, 'must_preserve_action_box': keep, 'sharp_in_crop_zone': True} if body else None
    return {'usability_grade': 'A', 'client_safe': True, 'risk_flags': [],
            'technical_qc_and_remediation': {'horizon_rotation_deg': 0.0, 'stabilization_needed': False},
            'people_and_speaker_analysis': {'mouth_visible': mouth, 'looking_at_lens': lens, 'speech_translation_block': SPEECH if speech else None, 'speaker_crop_module': crop}}


def elig(s):
    return solver.eligibility(s, {'allow_speaker_audio': False, 'show_speaker_video': False}, 1.35, 1920, 1080, 1920, 1080)


# ---------- P4: a silent worker is not a speaker ----------

def test_p4_c0109_two_silent_workers_are_used_as_is():
    assert elig(sub([0.18, 0, 0.45, 0.45], [0.47, 0, 0.15, 0.2], [0, 0.25, 0.85, 0.65]))[0] == 'ELIGIBLE_AS_IS'


def test_p4_c0093_one_silent_worker_is_used_as_is():
    assert elig(sub([0.26, 0, 0.72, 1.0], [0.43, 0, 0.28, 0.16], [0, 0.05, 0.85, 0.95]))[0] == 'ELIGIBLE_AS_IS'


def test_p4_a_visible_mouth_with_speech_heard_is_still_a_speaker():
    assert elig(sub([0.18, 0, 0.45, 0.45], [0.47, 0, 0.15, 0.2], [0, 0.25, 0.85, 0.65], speech=True))[0] == 'ELIGIBLE_WITH_CROP'   # cropped from the top, not as is


def test_p4_a_person_looking_at_the_lens_with_no_feasible_crop_stays_rejected():
    e, sol, _ = elig(sub([0.3, 0.2, 0.4, 0.8], [0.4, 0.3, 0.15, 0.2], [0.1, 0.1, 0.8, 0.8], mouth=False, lens=True))
    assert e == 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT' and sol['feasible'] is False


# ---------- P5: crop from the top or the bottom ----------

def test_p5_c0128_speaker_above_the_work_is_cropped_from_the_top():
    e, sol, _ = elig(sub([0.43, 0, 0.25, 0.4], [0.43, 0, 0.11, 0.16], [0.02, 0.28, 0.96, 0.55], speech=True))
    assert e == 'ELIGIBLE_WITH_CROP' and sol['zoom_x'] == 1.22 and sol['crop_rect'][1] == 0.18 and sol['crop_rect'][1] + sol['crop_rect'][3] == pytest.approx(1.0)


def test_p5_speaker_below_the_work_is_cropped_from_the_bottom():
    sol = solver.compute_davinci_crop([0.4, 0.6, 0.25, 0.4], [0.02, 0.17, 0.96, 0.55], 1920, 1080, 1920, 1080, 1.35, head_box=[0.45, 0.84, 0.11, 0.16])
    assert sol['feasible'] and sol['crop_rect'][1] == 0 and sol['crop_rect'][3] == 0.82 and sol['zoom_x'] == 1.22


def test_p5_a_speaker_whose_head_overlaps_the_work_on_every_side_stays_rejected():
    e, sol, _ = elig(sub([0.35, 0.3, 0.2, 0.6], [0.4, 0.4, 0.1, 0.1], [0.1, 0.1, 0.8, 0.8], speech=True))
    assert e == 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT' and sol['feasible'] is False


def test_p5_a_top_crop_over_the_zoom_limit_stays_rejected():
    sol = solver.compute_davinci_crop([0.55, 0.15, 0.3, 0.73], [0.0, 0.55, 0.65, 0.45], 1920, 1080, 1920, 1080, 1.35, head_box=[0.62, 0.15, 0.1, 0.2])
    assert sol['feasible'] is False


# ---------- P6: up to 10 % of the area to keep may be trimmed at its edge ----------

def test_p6_c0120_side_crop_trims_about_7_percent_of_the_height():
    e, sol, _ = elig(sub([0.8, 0, 0.2, 0.85], [0.85, 0.05, 0.1, 0.15], [0, 0.15, 0.78, 0.85], speech=True))
    x, y, w, h = sol['crop_rect']
    assert e == 'ELIGIBLE_WITH_CROP' and sol['zoom_x'] == 1.28 and round(0.85 - h, 2) == 0.07


def test_p6_c0124_side_crop_trims_2_percent_of_one_side():
    e, sol, _ = elig(sub([0.85, 0, 0.15, 0.65], [0.88, 0.02, 0.08, 0.12], [0, 0.25, 0.85, 0.75], speech=True))
    assert e == 'ELIGIBLE_WITH_CROP' and sol['zoom_x'] == 1.2 and sol['crop_rect'][2] == 0.83


def test_p6_more_than_10_percent_off_one_edge_stays_rejected():
    # a 0.68 window on a full-height keep box trims 0.16 off the top and the bottom each
    sol = solver.compute_davinci_crop([0.7, 0, 0.3, 0.6], [0, 0, 0.6, 1.0], 1920, 1080, 1920, 1080, 1.35)
    assert sol['feasible'] is False and 'clipped' in sol['reason']


def test_the_blueprint_numbers_are_unchanged():
    sol = solver.compute_davinci_crop([0.00, 0.12, 0.29, 0.88], [0.35, 0.20, 0.60, 0.60], 3840, 2160, 1920, 1080, 2.0)
    assert sol['feasible'] and sol['zoom_x'] == 1.45 and sol['position_x'] == -431.5 and sol['position_y'] == 7.8 and sol['crop_rect'] == [0.31, 0.16, 0.69, 0.69]


# ---------- old ways retired by refusal ----------

@pytest.mark.parametrize('version', ['1', '2'])
def test_creating_or_adopting_a_run_on_a_retired_version_is_refused(version):
    from app import core
    msg = f'procedure version {version} is retired; new films use version 3'
    with pytest.raises(Problem) as e:
        core.create_run(None, {'id': 'u'}, 't', 'c', version)
    assert e.value.message == msg
    with pytest.raises(Problem) as e:
        core.adopt(None, {'id': 'u'}, {'id': 'r'}, version)
    assert e.value.message == msg


def test_the_planning_endpoints_are_refused_naming_options_and_master():
    from app import main as M
    paths = {r.path for r in M.app.routes if '/planning' in getattr(r, 'path', '')}
    assert paths == {'/api/runs/{run_id}/planning', '/api/runs/{run_id}/planning/{rest:path}'}
    with pytest.raises(Problem) as e:
        M.planning_retired('r', 'prepare')
    assert e.value.status == 410 and 'options and master' in e.value.message


def test_deciding_by_option_number_is_refused_naming_slide():
    from uuid import uuid4
    from app import main as M
    with pytest.raises(Problem) as e:
        M.DecideBody(request_id=uuid4(), option_number=2, action='KEEP')
    assert e.value.message == 'option_number is retired; answer by slide (`slide`, a label such as 2 or 2B).'
    assert M.DecideBody(request_id=uuid4(), slide='2B', action='KEEP').slide == '2B'


def test_the_version_1_evidence_contract_is_refused():
    from app import analysis
    with pytest.raises(Problem, match='version-1 evidence contract is retired'):
        analysis.build_request({'id': 'r'}, {'model': 'm', 'settings': {}}, {}, {}, {}, {'camera_audio': 'allowed'})
    assert not hasattr(analysis, 'build_request_v2') and not hasattr(analysis, 'review_response_v2')


def test_kling_and_seedance_are_refused_and_no_longer_read():
    from app import video_generators as VG, video_providers as VP
    assert VG.known('higgsfield', 'kling-video/v3.0/std/image-to-video') is None and not hasattr(VG, 'RETIRED')
    with pytest.raises(Problem) as e:
        VP.configured('higgsfield')
    assert e.value.message == 'Kling and Seedance are retired; every video take is Gemini Omni'
