"""Stage 2 (options → master → first cut), design/15 + 17. Validator unit tests on a synthetic package; end-to-end through the plugin with
the fake Gemini (clip-log-v1) and real FFmpeg renders on tiny clips."""
import json
import re
import subprocess
from copy import deepcopy

import psycopg
import pytest

from app.clip_log import solver
from app.stage2 import package as P, validator as V
from clip_log_fixture import synthetic_log
from conftest import vw
from test_analysis import FakeTransport, gemini, run_until_analysis, START as ANALYSIS_START  # noqa: F401
from test_voice_media import drain, fake  # noqa: F401

TL = {'width': 1920, 'height': 1080, 'fps': 25}
POLICY = {'allow_speaker_audio': False, 'show_speaker_video': False}


# ---------- synthetic package ----------

def make_package(n_clips=3, beats=None):
    rows, cards, landmarks = [], [], set()
    for i in range(n_clips):
        cid = f'clip{i}'
        clip = {'id': cid, 'name': f'c{i}.mp4', 'sha256': f'{i:064x}', 'bytes': 1, 'duration_s': 2.0, 'has_audio': True, 'width': 1920, 'height': 1080, 'fps': '25/1'}
        log = synthetic_log(f'CLIP{i}', clip['name'], 25.0, 50)
        solver.solve(log, POLICY, clip, TL)
        for s in log['sub_clips']:
            rows.append(P.sub_clip_row(clip, log, s, 25))
        cards.append({'clip_id': cid, 'clip_name': clip['name'], 'descriptive_name': log['descriptive_name'], 'lines': log['summary_card_lines']})
    beats = beats or [{'beat_id': 'BEAT_01', 'passage_id': 'P001', 'text': 'One.', 'timeline_start_frame': 0, 'timeline_end_frame': 37, 'target_beat_frames': 37, 'window_start_s': 0.0, 'window_end_s': 1.48},
                      {'beat_id': 'BEAT_02', 'passage_id': 'P002', 'text': 'Two.', 'timeline_start_frame': 37, 'timeline_end_frame': 50, 'target_beat_frames': 13, 'window_start_s': 1.48, 'window_end_s': 2.0}]
    return P.build({'id': 'r', 'code': 'VW-T', 'client': 'C'}, {}, beats, cards, rows, landmarks, [], [], TL, POLICY, 'prompt')


def ev(sid, a, b, **kw):
    return {'sub_clip_id': sid, 'source_in_frame': a, 'source_out_frame': b, 'crop': kw.pop('crop', 'full'), 'a2_intervals': kw.pop('a2', []), **kw}


def option(n, beat, rank, events, shared=''):
    return {'option_number': n, 'beat_id': beat, 'rank': rank, 'events': events,
            'slate_lines': [f'OPTION #{n} | {beat} ({rank}) | x.xs ({len(events)} Shots)', 'Clips: ' + ' + '.join(e['sub_clip_id'] for e in events), shared],
            'reasoning': 'synthetic', 'log_fields_cited': ['primary_fit_for_beats'], 'best_unchosen': {'sub_clip_id': 'none', 'rule': 'none better'}, 'shared_justification': 'nothing else fits' if shared else ''}


def good_doc():
    # BEAT_01 = 37 frames: clip0 SUB_01 (25) + clip1 SUB_01 (12); SECONDARY: clip2 SUB_01 (25) + clip0 SUB_02 cropped (12). BEAT_02 declared a gap.
    return {'contract': 'vw2-options-v1',
            'options': [option(1, 'BEAT_01', 'PRIMARY', [ev('clip0:SUB_01', 0, 25), ev('clip1:SUB_01', 0, 12)]),
                        option(2, 'BEAT_01', 'SECONDARY', [ev('clip2:SUB_01', 0, 25), ev('clip0:SUB_02', 25, 37, crop='solver')])],
            'gaps': [{'beat_id': 'BEAT_02', 'reason': 'zero coverage'}],
            'qc_self': {f'Q{i}': {'pass': True, 'evidence': 'synthetic'} for i in range(1, 9)}}


def refusals(doc, pk=None):
    return V.validate_options(deepcopy(doc), pk or make_package(), POLICY)['refusals']


# ---------- validator (S3–S11, G12, G13, Q1, Q4) ----------

def test_s1_good_document_validates_with_only_flags():
    r = V.validate_options(deepcopy(good_doc()), make_package(), POLICY)
    assert r['refusals'] == [], r
    assert any('R10' in f or 'R5' in f or 'R1' in f for f in r['flags']) or r['flags'] == []


def test_s3_window_exceeded_by_one_frame():
    d = good_doc(); d['options'][0]['events'][0]['source_out_frame'] = 26; d['options'][0]['events'][1]['source_out_frame'] = 11
    assert any('G1' in x for x in refusals(d))


def test_s4_action_peak_dropped():
    pk = make_package()
    row = next(r for r in pk['sub_clips'] if r['sub_clip_id'] == 'clip0:SUB_01'); row['action_peak'] = {'in_frame': 20, 'out_frame': 25}
    d = good_doc(); d['options'][0]['events'][0]['source_out_frame'] = 24; d['options'][0]['events'][1]['source_out_frame'] = 13
    assert any('G2' in x for x in refusals(d, pk))


def test_s5_three_same_size_shots():
    d = good_doc(); d['options'][0]['events'] = [ev('clip0:SUB_01', 0, 13), ev('clip1:SUB_01', 0, 12), ev('clip2:SUB_01', 0, 12)]
    assert any('G5' in x for x in refusals(d))


def test_s6_hard_sun_to_overcast_inside_a_beat():
    pk = make_package()
    next(r for r in pk['sub_clips'] if r['sub_clip_id'] == 'clip0:SUB_01')['lighting'] = 'HARD_SUN'
    next(r for r in pk['sub_clips'] if r['sub_clip_id'] == 'clip1:SUB_01')['lighting'] = 'SOFT_OVERCAST'
    assert any('G8' in x for x in refusals(good_doc(), pk))


def test_s7_shared_clip_without_warning():
    d = good_doc(); d['options'][1]['events'][0] = ev('clip0:SUB_01', 0, 25)
    assert any('Q4' in x for x in refusals(d))
    d['options'][0]['slate_lines'][2] = '[WARNING: SHARED CLIP] clip0:SUB_01 also in OPTION #2'; d['options'][0]['shared_justification'] = 'only wide'
    d['options'][1]['slate_lines'][2] = '[WARNING: SHARED CLIP] clip0:SUB_01 also in OPTION #1'; d['options'][1]['shared_justification'] = 'only wide'
    assert not any('Q4' in x for x in refusals(d))


def test_s8_duration_mismatch():
    d = good_doc(); d['options'][0]['events'][1]['source_out_frame'] = 11
    assert any('G11' in x for x in refusals(d))


def test_s9_speaker_on_screen_under_mode3_and_ineligible_sub_clip():
    pk = make_package()
    row = next(r for r in pk['sub_clips'] if r['sub_clip_id'] == 'clip0:SUB_02'); row['eligibility'] = 'ELIGIBLE_A_ROLL_SPEAKER'
    assert any('Q1' in x for x in refusals(good_doc(), pk))
    row['eligibility'] = 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT'
    assert any('G10' in x for x in refusals(good_doc(), pk))


def test_s10_a2_interval_outside_clean_nat_sound():
    d = good_doc(); d['options'][0]['events'][0]['a2_intervals'] = [{'in_frame': 0, 'out_frame': 10}]
    assert any('Q6' in x for x in refusals(d))


def test_s11_missing_best_unchosen_reasoning_and_qc():
    d = good_doc(); d['options'][0]['best_unchosen'] = {}; d['options'][1]['reasoning'] = ''; d['qc_self'].pop('Q5')
    r = refusals(d)
    assert any('R15' in x for x in r) and any('reasoning' in x for x in r) and any('Q5' in x for x in r)


def test_g12_g13_numbering_and_secondary_must_differ():
    d = good_doc(); d['options'][1]['option_number'] = 3
    assert any('G12' in x for x in refusals(d))
    d = good_doc(); d['options'][1]['events'] = deepcopy(d['options'][0]['events'])
    assert any('G13' in x for x in refusals(d))


def test_beat_neither_option_nor_gap_and_hold_last_frame_rule():
    d = good_doc(); d['gaps'] = []
    assert any('BEAT_02' in x for x in refusals(d))
    pk = make_package(); next(r for r in pk['sub_clips'] if r['sub_clip_id'] == 'clip1:SUB_01')['still_eligible'] = False
    d = good_doc(); d['options'][0]['events'][1]['hold_last_frame'] = True
    assert any('G16' in x for x in refusals(d, pk))


def test_master_validator_duplicates_gaps_and_runtime():
    pk = make_package()
    m = {'events': [{'kind': 'event', 'sub_clip_id': 'a', 'approved_from_option': 1, 'timeline_in_frame': 0, 'timeline_out_frame': 20, 'timeline_frames': 20},
                    {'kind': 'event', 'sub_clip_id': 'a', 'approved_from_option': 3, 'timeline_in_frame': 21, 'timeline_out_frame': 50, 'timeline_frames': 29}]}
    r = V.validate_master(m, pk)
    assert any('Q4' in x for x in r['refusals']) and any('gap or overlap' in x for x in r['refusals'])


# ---------- end to end ----------

def run_until_options(home, database, fake, gemini):
    code, ws, units = run_until_analysis(home, database, fake, n_clips=3, seconds=2, rate=25)
    assert vw(home, *ANALYSIS_START)[0] == 0
    drain()
    nxt = vw(home, 'next')[1]
    assert nxt['stage'] == 'options', nxt
    rc, out, err = vw(home, 'options', 'prepare')
    assert rc == 0, (out, err)
    pk = json.loads((ws / 'work' / 'options-package.json').read_text(encoding='utf-8'))
    return code, ws, pk


def author(pk):
    """Author options programmatically from the package: fill BEAT_01 with two sub-clips, declare the rest as gaps."""
    beats = pk['beats']
    rows = [r for r in pk['sub_clips'] if r['eligibility'] == 'ELIGIBLE_AS_IS']
    crops = [r for r in pk['sub_clips'] if r['eligibility'] == 'ELIGIBLE_WITH_CROP']
    b1 = beats[0]
    need = b1['target_beat_frames']
    first = rows[0]
    n1 = min(need - 10, first['out_frame'] - first['in_frame'])
    second = rows[1]
    n2 = need - n1
    assert second['out_frame'] - second['in_frame'] >= n2, (need, n1, n2, second)
    third, fourth = rows[2], crops[0]
    opts = [option(1, b1['beat_id'], 'PRIMARY', [ev(first['sub_clip_id'], first['in_frame'], first['in_frame'] + n1), ev(second['sub_clip_id'], second['in_frame'], second['in_frame'] + n2)]),
            option(2, b1['beat_id'], 'SECONDARY', [ev(third['sub_clip_id'], third['in_frame'], third['in_frame'] + n1), ev(fourth['sub_clip_id'], fourth['in_frame'], fourth['in_frame'] + n2, crop='solver')])]
    return {'contract': 'vw2-options-v1', 'options': opts, 'gaps': [{'beat_id': b['beat_id'], 'reason': 'zero coverage'} for b in beats[1:]],
            'qc_self': {f'Q{i}': {'pass': True, 'evidence': 'synthetic'} for i in range(1, 9)}}


def test_s1_s2_s12_s15_s16_s17_s18_s19_end_to_end(home, database, fake, gemini):
    code, ws, pk = run_until_options(home, database, fake, gemini)
    # S2: coverage report names the zero-coverage beat
    rc, cov, _ = vw(home, 'options', 'coverage')
    assert rc == 0 and any('ZERO COVERAGE' in a for e in cov['coverage'] for a in e['alerts'])
    doc = author(pk)
    (ws / 'out' / 'options.json').write_text(json.dumps(doc), encoding='utf-8')
    rc, out, err = vw(home, 'options', 'check', '--file', 'out/options.json')
    assert rc == 0 and out['status'] == 'valid', (out, err)
    # S12: three refused proposals → decision
    bad = deepcopy(doc); bad['options'][0]['events'][1]['source_out_frame'] -= 1
    (ws / 'out' / 'bad.json').write_text(json.dumps(bad), encoding='utf-8')
    for _ in range(3):
        rc, out, _ = vw(home, 'options', 'propose', '--file', 'out/bad.json')
        assert rc == 2 and out['code'] == 'OPTIONS_REJECTED', out
    rc, out, _ = vw(home, 'options', 'propose', '--file', 'out/bad.json')
    assert rc == 3 and out['code'] == 'NEEDS_USER_DECISION'
    assert vw(home, 'decide', '--stage', 'options', '--decision', 'retry')[0] == 0
    rc, out, err = vw(home, 'options', 'propose', '--file', 'out/options.json')
    assert rc == 0 and out['version'] == 1 and out['gaps'] == ['BEAT_02'], (out, err)
    assert vw(home, 'options', 'show', '--option', '2')[1]['rank'] == 'SECONDARY'
    # S19: review film: 2 slates of 75 frames + 2 × 37 beat frames = 224 frames = 8.96 s
    assert vw(home, 'options', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'options', 'fetch')
    assert rc == 0, (out, err)
    assert abs(out['duration_s'] - (2 * 75 + 2 * pk['beats'][0]['target_beat_frames']) / 25) < 0.15, out['duration_s']
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(ws / 'out' / 'review.mp4')], capture_output=True, check=True).stdout)
    v = next(s for s in probe['streams'] if s['codec_type'] == 'video'); a = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    assert v['codec_name'] == 'h264' and v['pix_fmt'] == 'yuv420p' and v['width'] == 1920 and a['codec_name'] == 'aac' and a['sample_rate'] == '48000'
    rc, out, err = vw(home, 'options', 'record', '--quote', 'yes, these options')
    assert rc == 0, (out, err)
    assert vw(home, 'next')[1]['stage'] == 'master'
    # S13: keeping both options of one beat is refused; S15/S16: keep one with an edit, reject the other with a reason
    assert vw(home, 'master', 'decide', '--option', '1', '--action', 'KEEP')[0] == 0
    assert vw(home, 'master', 'decide', '--option', '2', '--action', 'KEEP')[0] == 0
    rc, out, _ = vw(home, 'master', 'build')
    assert rc == 2 and 'both options kept' in out['message']
    rc, out, _ = vw(home, 'master', 'decide', '--option', '2', '--action', 'REJECT')
    assert rc == 2 and 'reason' in out['message']
    assert vw(home, 'master', 'decide', '--option', '2', '--action', 'REJECT', '--note', 'too tight, prefer the wide')[0] == 0
    # S14: an edit that breaks the beat total is refused; a balanced one passes
    assert vw(home, 'master', 'decide', '--option', '1', '--action', 'KEEP_WITH_EDIT', '--edit', 'shot:1,in:+2,out:0')[0] == 0
    rc, out, _ = vw(home, 'master', 'build')
    assert rc == 2 and 'frames; the beat needs' in out['message']
    assert vw(home, 'master', 'decide', '--option', '1', '--action', 'KEEP_WITH_EDIT', '--edit', 'shot:2,in:+2,out:+2')[0] == 0
    rc, out, err = vw(home, 'master', 'build')
    assert rc == 0 and out['gaps'] == ['BEAT_02'] and out['events'] == 2 and out['duration_frames'] == 50, (out, err)
    assert vw(home, 'master', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'master', 'fetch')
    assert rc == 0 and abs(out['duration_s'] - 2.0) < 0.15, (out, err)   # S18: master = sum of beats, gap shown as a slate
    rc, out, err = vw(home, 'master', 'record', '--quote', 'yes the master')
    assert rc == 0 and out['learned_rules_added'] == 1, (out, err)
    with psycopg.connect(database) as c:
        assert c.execute("select count(*) from vw2_client_rules where client_id='c-vk' and rule like 'Rejected option #2%%'").fetchone()[0] == 1
    # first cut: needs watched + listened
    rc, out, _ = vw(home, 'first-cut', 'record', '--quote', 'yes')
    assert rc == 2 and 'listened' in out['message']
    rc, out, err = vw(home, 'first-cut', 'record', '--quote', 'yes, I watched it and listened to it')
    assert rc == 0 and out['gaps'] == ['BEAT_02'], (out, err)
    # S17: the gap is the visuals unit; the visuals stage reads it from the master/first cut
    nxt = vw(home, 'next')[1]
    assert nxt['stage'] == 'visuals' and nxt['units_open'] == ['BEAT_02'], nxt
    rc, out, err = vw(home, 'visuals', 'prepare')
    assert rc == 0 and out['gaps'] == ['BEAT_02'], (out, err)


def test_s21_boundary_frames_and_paid_inspection(home, database, fake, gemini):
    code, ws, pk = run_until_options(home, database, fake, gemini)
    crop = next(r for r in pk['sub_clips'] if r['eligibility'] == 'ELIGIBLE_WITH_CROP')
    rc, out, err = vw(home, 'options', 'frames', '--sub', crop['sub_clip_id'], '--edge', 'in')
    assert rc == 0 and len(out['frames']) >= 5 and all((ws / p).exists() for p in out['paths']), (out, err)
    calls = dict(gemini.calls)
    rc, out, err = vw(home, 'options', 'inspect', '--sub', crop['sub_clip_id'], '--edge', 'in')
    assert rc == 0 and out['paid'] is True, (out, err)
    drain()
    st = vw(home, 'options', 'status')[1]
    j = st['inspections'][f"{crop['sub_clip_id'].replace(':', '-')}-in"]
    assert j['status'] == 'retained' and j['answer']['residual_lip_movement'] == 'no' and gemini.calls['generate'] == calls['generate'] + 1
