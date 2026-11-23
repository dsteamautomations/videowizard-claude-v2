"""SK, 23 Nov 2026 (VW-25 options, plan of action Phase 2: A, B, C). Of VW-25's 28 refused pieces, 14 were workers wrongly taken for "the speaker on
camera" (design/125 P4: looks at the lens, OR mouth visible with speech heard). The data here is the stored study of those 28 real pieces.
A. The speaker on camera is a person who looks at the lens and speaks (or the shot's subject posed to the lens). Speaks away from the lens: allowed.
   Only glances at the lens: allowed, with a warning. Older way retired: design/125 P4.
B. A crop below the head may zoom to 1.65 on a source of the film's size, with the warning "soft picture"; beyond it the reason names the zoom needed.
C. A piece the study graded REJECT says why, in the study's words.
A stored study is judged again by today's rules when the options are prepared: the rules are the server's own and cost nothing."""
import json
from collections import Counter
from pathlib import Path

from app.clip_log import prompt as PR, solver as S

SERVER = Path(__file__).resolve().parents[1]
PIECES = json.loads((Path(__file__).parent / 'vw25_refused_pieces.json').read_text(encoding='utf-8'))
POLICY = {'allow_speaker_audio': False, 'show_speaker_video': False}


def sub_of(r):
    b = r['boxes']
    return {'usability_grade': r['grade'], 'client_safe': True, 'risk_flags': [], 'visual_action_observed': r['what'],
            'people_and_speaker_analysis': {'looking_at_lens': r['looking_at_lens'], 'mouth_visible': r['mouth_visible'], 'people_roles': r['roles'], 'audio_nature': r['audio'],
                                            'speech_translation_block': {'speaker_id': 'S'} if r['speech'] else None,
                                            'speaker_crop_module': {'speaker_head_mouth_box': b[0], 'speaker_full_body_box': b[1], 'must_preserve_action_box': b[2], 'sharp_in_crop_zone': r['sharp']} if b else None},
            'technical_qc_and_remediation': {'horizon_rotation_deg': r['rotation'], 'stabilization_needed': r['stabilize']},
            'camera_and_optics': {}, 'pacing_and_flow': {}}


def judged():
    out = {}
    for r in PIECES:
        sub = sub_of(r)
        e, sol, _ = S.eligibility(sub, POLICY, 1.35, r['width'], r['height'], 1920, 1080)
        out[r['piece']] = (e, S.warnings(sub, e, sol), (sol or {}).get('reason'))
    return out


def test_the_28_refused_pieces_of_vw25_under_the_new_rules():
    got = judged()
    assert all(not r['was'].startswith('ELIGIBLE') for r in PIECES) and len(PIECES) == 28          # every one was refused
    assert Counter(e for e, _, _ in got.values()) == {'ELIGIBLE_AS_IS': 9, 'ELIGIBLE_WITH_CROP': 5, 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT': 9, 'REJECT_ALL': 5}
    for piece in ('C0050_1 04', 'C0058_1 01', 'C0025_1 01', 'C0015_1 01'):                         # a worker; speech is heard; nobody looks at the lens
        assert got[piece][:2] == ('ELIGIBLE_AS_IS', []), piece
    assert got['C0098_1 02'][:2] == ('ELIGIBLE_AS_IS', ['a person speaks on camera'])              # he speaks to someone else: allowed, and whoever chooses is told
    for piece in ('C0014_1 03', 'C0026_1 05', 'C0027_1 02', 'C0027_1 04'):                         # a silent glance at the lens
        assert got[piece][:2] == ('ELIGIBLE_AS_IS', ['glances at the camera']), piece
    for piece, zoom in (('C0058_1 02', 1.47), ('C0058_1 03', 1.47), ('C0027_1 01', 1.59), ('C0059_1 01', 1.61), ('C0059_1 03', 1.61)):   # looks and speaks, the work in view
        assert got[piece][:2] == ('ELIGIBLE_WITH_CROP', [f'soft picture, zoom {zoom}']), piece
    presenter = [p for p in got if p.split('_')[0] in ('C0040', 'C0041', 'C0083', 'C0103')]
    assert len(presenter) == 9 and all(got[p][0] == 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT' for p in presenter)   # the presenter facing the lens stays out, speaking or between two sentences


def test_a_refused_shake_piece_says_why_in_the_studys_words():
    got = judged()
    shakes = [p for p, (e, _, _) in got.items() if e == 'REJECT_ALL']
    assert sorted(shakes) == ['C0019_1 03', 'C0039_1 02', 'C0063_1 05', 'C0066_1 05', 'C0091_1 04']
    assert got['C0063_1 05'][2].startswith('the clip study graded it REJECT: End-of-take abrupt camera tilt up and pan left')
    bare = S.eligibility({**sub_of(PIECES[0]), 'usability_grade': 'REJECT', 'visual_action_observed': None}, POLICY, 1.35, 1920, 1080, 1920, 1080)
    assert bare[0] == 'REJECT_ALL' and bare[1]['reason'] == 'the clip study graded it REJECT'     # no words in the study: still a reason, never "reject all"


def crop(limit, source=1920, **boxes):
    b = {'body': [0.26, 0.03, 0.52, 0.97], 'keep': [0.44, 0.47, 0.34, 0.53], 'head': [0.38, 0.03, 0.18, 0.27], **boxes}
    return S.compute_davinci_crop(b['body'], b['keep'], source, source * 9 // 16, 1920, 1080, limit, head_box=b['head'])


def test_a_crop_below_the_head_goes_to_165_and_beyond_it_names_the_zoom_needed():
    soft = crop(1.35)                                                                              # C0058: the tile in the hands, the head above
    assert soft['feasible'] and soft['total_cumulative_zoom'] == 1.47 and soft['within_safe_zoom_limit'] is False
    sharp = crop(2.0)                                                                              # the same boxes on a 4K source: inside the usual limit
    assert sharp['feasible'] and sharp['within_safe_zoom_limit'] is True
    far = crop(1.35, head=[0.38, 0.03, 0.18, 0.40], keep=[0.44, 0.60, 0.34, 0.40])                 # the head reaches lower: the window below it is smaller
    assert far['feasible'] is False and 'a crop below or above the head needs zoom' in far['reason'] and 'the limit is 1.65' in far['reason']
    assert float(far['reason'].split('needs zoom ')[1].split(',')[0]) > 1.65
    side = S.compute_davinci_crop([0.8, 0, 0.2, 0.85], [0, 0.15, 0.78, 0.85], 1920, 1080, 1920, 1080, 1.35, head_box=[0.85, 0.05, 0.1, 0.15])
    assert side['feasible'] and side['zoom_x'] == 1.28 and side['within_safe_zoom_limit'] is True  # a side crop keeps its limit and is preferred when it works


def person(**over):
    return {'usability_grade': 'A', 'client_safe': True, 'risk_flags': [], 'technical_qc_and_remediation': {},
            'people_and_speaker_analysis': {'mouth_visible': True, 'looking_at_lens': False, 'speech_translation_block': None, 'speaker_crop_module': None, **over}}


def test_the_edges_of_the_speaker_rule():
    speech = {'speaker_id': 'S'}
    judge = lambda p, policy=POLICY: S.eligibility(person(**p), policy, 1.35, 1920, 1080, 1920, 1080)[0]
    assert judge({}) == 'ELIGIBLE_AS_IS'                                                           # a silent worker, as before
    assert judge({'looking_at_lens': True, 'speech_translation_block': speech}) == 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT'   # talks to the camera, no boxes logged: out
    assert judge({'looking_at_lens': True, 'people_roles': ['Subject_Silent']}) == 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT'   # the subject posed to the lens, silent in this piece
    assert judge({'looking_at_lens': True, 'people_roles': ['Worker_Silent']}) == 'ELIGIBLE_AS_IS'                     # a worker's glance
    assert judge({'speech_translation_block': speech}) == 'ELIGIBLE_AS_IS'                         # speaks away from the lens, no boxes: used as it is, never refused
    assert judge({'looking_at_lens': None, 'mouth_visible': None, 'people_roles': None}) == 'ELIGIBLE_AS_IS'           # nothing logged about the person
    clean = {'speaker_head_mouth_box': [0.85, 0.05, 0.1, 0.15], 'speaker_full_body_box': [0.8, 0, 0.2, 0.85], 'must_preserve_action_box': [0, 0.15, 0.78, 0.85], 'sharp_in_crop_zone': True}
    assert judge({'speech_translation_block': speech, 'speaker_crop_module': clean}) == 'ELIGIBLE_WITH_CROP'           # speaks away from the lens and a clean crop hides the lips: cropped, as design/125 P5
    assert judge({'looking_at_lens': True, 'speech_translation_block': speech}, {'show_speaker_video': True}) == 'ELIGIBLE_A_ROLL_SPEAKER'   # a film that shows its speaker: unchanged
    assert judge({'looking_at_lens': True}, {'show_speaker_video': True}) == 'ELIGIBLE_AS_IS'


def test_the_warnings_reach_whoever_chooses_and_a_stored_study_is_judged_by_todays_rules():
    r = next(p for p in PIECES if p['piece'] == 'C0014_1 03')
    log = {'sub_clips': [{**sub_of(r), 'risk_flags': ['no_gloves']}]}
    S.solve(log, POLICY, {'width': 1920, 'height': 1080, 'fps': '50'}, {'width': 1920, 'height': 1080, 'fps': 50})
    st = log['sub_clips'][0]['stage15']
    assert st['visual_eligibility'] == 'ELIGIBLE_AS_IS' and st['risk_flags_effective'] == ['no_gloves', 'glances at the camera']   # beside the study's own flags, on every surface that shows them
    stage = (SERVER / 'app' / 'stage2' / 'stage.py').read_text(encoding='utf-8')
    assert "solver.solve(log, (log['sub_clips'][0].get('stage15') or {}).get('policy') or doc['identity'].get('speaker_policy') or {}, clip, timeline(run))" in stage
    for mode in (2, 3):
        text = PR.policy_paragraph({'allow_speaker_audio': mode == 2, 'show_speaker_video': False})
        assert 'looks at the lens and speaks to the camera must be trimmed or cropped out' in text and 'or looking at the lens must' not in text   # the study is told the same rule
