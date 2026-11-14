"""design/195 (SK, 14 Nov 2026, after the 52 flagged pieces of VW-23): a flag warns the user, it does not block the piece. The check no longer refuses a
flagged piece or one marked not safe; "not safe" no longer removes a piece; every shot and alternative shows its flags; the clip study rejects only
useless footage and never a person talking by itself; the assistant may place a flagged piece."""
import json
from pathlib import Path

from app.clip_log import prompt as PR, solver
from app.stage2 import slides as SL, validator as V
from test_design127_review_pure import by_no, film

ROOT = Path(__file__).resolve().parents[2]


def row(**kw):
    return {'eligibility': 'ELIGIBLE_AS_IS', 'client_safe': True, 'risk_flags': [], 'in_frame': 0, 'out_frame': 500, 'source_fps': '50', 'min_hold_s': 1.0,
            'action_peak': {'in_frame': 100, 'out_frame': 300}, 'camera_moves': [], **kw}


def refusals(r):
    out = []
    V._piece('T', {'source_in_frame': 90, 'source_out_frame': 320, 'match': 'direct', 'evidence': 'x', 'crop': 'full'}, r, {}, out, [])
    return out


def test_the_check_passes_a_flagged_piece_and_one_marked_not_safe():
    assert refusals(row(risk_flags=['background_motorcycle_license_plate_unreadable'])) == []
    assert refusals(row(client_safe=False, risk_flags=['licence_plate_visible'])) == []


def test_the_check_still_refuses_a_piece_that_was_removed():
    for e in ('REJECT_ALL', 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT'):
        r = refusals(row(eligibility=e, risk_flags=['clutter']))
        assert r and 'not eligible' in r[0]


def sub(grade='B', safe=True, flags=()):
    return {'usability_grade': grade, 'client_safe': safe, 'risk_flags': list(flags), 'technical_qc_and_remediation': {},
            'people_and_speaker_analysis': {'mouth_visible': False, 'looking_at_lens': False, 'speech_translation_block': None, 'speaker_crop_module': None}}


def elig(s):
    return solver.eligibility(s, {'allow_speaker_audio': False, 'show_speaker_video': False}, 1.35, 1920, 1080, 1920, 1080)[0]


def test_not_safe_no_longer_removes_a_piece_and_a_reject_grade_still_does():
    assert elig(sub(safe=False, flags=['licence_plate_partially_visible', 'yard_clutter_in_background'])) == 'ELIGIBLE_AS_IS'
    assert elig(sub(safe=False)) == 'ELIGIBLE_AS_IS'
    assert elig(sub(grade='REJECT')) == 'REJECT_ALL'


def test_a_shot_and_its_alternative_show_their_flags_in_plain_words():
    doc, pk = film()
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    rows['c1:S'].update(risk_flags=['background_banner_signage', 'minor_crew_bag_in_far_background'], client_safe=True)
    rows['c4:S'].update(risk_flags=[], client_safe=False)
    b = by_no(SL.slides(doc, pk, 25))
    assert b['1.2']['flags'] == ['background banner signage', 'minor crew bag in far background']
    assert any(l.startswith('Has: background banner signage') for l in b['1.2']['lines'])
    assert b['1.3A1']['flags'] == ['marked not safe for the client by the clip study']
    assert b['1.3'].get('flags') is None and b['3.1'].get('flags') is None   # no flag: nothing shown; a piece without the fields (an older package) too


def test_the_page_and_the_chat_carry_the_flags():
    page = (ROOT / 'server' / 'app' / 'templates' / 'review.html').read_text(encoding='utf-8')
    stage = (ROOT / 'server' / 'app' / 'stage2' / 'stage.py').read_text(encoding='utf-8')
    assert 's.flags' in page and "'Has: '" in page
    assert stage.count("'flags'") >= 2   # the page's rows and the proposal's slides


def test_the_clip_study_rejects_only_useless_footage():
    text = PR.GRADES_AND_FLAGS
    for needle in ('REJECT is only for footage nobody could use', 'never by itself a reason for REJECT', 'speaker_crop_module', 'slice', 'A flag never lowers the grade',
                   'a technique, not a defect'):
        assert needle in text, needle
    assert text in PR.build({}, {}, 50.0, 100, [], 'TAG', {'allow_speaker_audio': False, 'show_speaker_video': False})


def test_the_assistant_may_place_a_flagged_piece():
    v3 = json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    p = next(s for s in v3['stages'] if s['name'] == 'options')['prompt']
    assert 'A piece with `risk_flags` may be used' in p and 'the operator sees the flags on the shot' in p
    agent = (ROOT / 'plugin' / 'agents' / 'vw-scene-review.md').read_text(encoding='utf-8')
    assert 'never rejected for its flag alone' in agent
