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
            'slate_lines': [f"OPTION #{n} | {beat} ({rank}) | {sum(e['source_out_frame'] - e['source_in_frame'] for e in events) / 25:.1f}s ({len(events)} Shot{'s' if len(events) != 1 else ''})", 'Clips: ' + ' + '.join(e['sub_clip_id'] for e in events), shared],
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


# ---------- design/19: slate, word-timed flags, scenes and pauses ----------

def test_c1_slate_line_1_states_real_length_and_shots():
    d = good_doc()
    d['options'][0]['slate_lines'][0] = 'OPTION #1 | BEAT_01 (PRIMARY) | 9.9s (2 Shots)'
    assert any('slate line 1 must end with "| 1.5s (2 Shots)"' in r for r in refusals(d))
    d = good_doc()
    d['options'][0]['slate_lines'][0] = 'OPTION #1 | BEAT_01 (PRIMARY) | 1.5s (3 Shots)'
    assert any('slate line 1' in r for r in refusals(d))


def word_pk(silences=()):
    pk = make_package()
    pk['narration'] = {'words': [{'id': 'W1', 'text': 'Bricks', 'start_frame': 31, 'end_frame': 36}, {'id': 'W2', 'text': 'pressed.', 'start_frame': 40, 'end_frame': 45}],
                       'silences': list(silences)}
    return pk


def flags_of(d, pk):
    r = V.validate_options(deepcopy(d), pk, POLICY)
    assert r['refusals'] == [], r
    return r['flags']


def test_b1_b2_b3_word_timed_flags():
    d = good_doc()   # option 1 shot 2 (clip1:SUB_01, accent at its frame 0) starts on timeline frame 25
    d['options'][0]['events'][1]['illustrates_word_id'] = 'W1'   # W1 at 31: 6 frames of pre-roll
    d['options'][0]['events'][1]['action_word_id'] = 'W1'        # accent at 25, word at 31: within 6
    assert not any(' B' in f for f in flags_of(d, word_pk()))
    d['options'][0]['events'][1]['illustrates_word_id'] = 'W2'   # 15 frames early
    d['options'][0]['events'][1]['action_word_id'] = 'W2'
    fl = flags_of(d, word_pk())
    assert any('B1 pre-roll' in f for f in fl) and any("B2 the word 'pressed.'" in f for f in fl)
    fl = flags_of(good_doc(), word_pk([{'start_frame': 20, 'end_frame': 50}]))
    assert any('B3' in f for f in fl)                             # cut at 25 inside a 1.2 s+ silence, no clean nat sound
    pk = word_pk([{'start_frame': 20, 'end_frame': 50}])
    for r in pk['sub_clips']:
        if r['sub_clip_id'] in ('clip1:SUB_01', 'clip0:SUB_02'):
            r['nat_sound'] = [{'in_frame': r['in_frame'], 'out_frame': r['out_frame']}]
    assert not any('B3' in f for f in flags_of(good_doc(), pk))   # the next shot carries natural sound: allowed


def approve_scenes(home, ws, pause_s=0.5):
    """Split 'Earth blocks are pressed. / Not fired.' into two scenes with a pause after 'pressed.' (the scene boundary)."""
    pk = json.loads((ws / 'work' / 'options-package.json').read_text(encoding='utf-8'))
    sents = pk['narration']['sentences']
    doc = {'scenes': [{'first_word_id': sents[0]['first_word_id'], 'title': 'Pressing'}, {'first_word_id': sents[1]['first_word_id'], 'title': 'Not fired'}],
           'pauses': [{'after_word_id': sents[0]['last_word_id'], 'seconds': pause_s, 'reason': 'let the press finish on screen'}]}
    (ws / 'out' / 'scenes.json').write_text(json.dumps(doc), encoding='utf-8')
    rc, out, err = vw(home, 'options', 'scenes', '--file', 'out/scenes.json', '--quote', 'yes, these scenes and the pause')
    assert rc == 0, (out, err)
    return out, json.loads((ws / 'work' / 'options-package.json').read_text(encoding='utf-8'))


def silences_in(path, min_s=0.25):
    err = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(path), '-af', f'silencedetect=noise=-50dB:d={min_s}', '-f', 'null', '-'], capture_output=True).stderr.decode(errors='replace')
    starts = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', err)]
    durs = [float(x) for x in re.findall(r'silence_duration: ([0-9.]+)', err)]
    return list(zip(starts, durs))


def test_scenes_and_pauses_end_to_end(home, database, fake, gemini):
    code, ws, pk0 = run_until_options(home, database, fake, gemini)
    assert pk0['narration']['scenes_approved'] is False and pk0['narration']['cuts'] == [] and len(pk0['narration']['sentences']) == 2
    sents = pk0['narration']['sentences']
    words = pk0['narration']['words']
    # refusals: no quote; a scene inside a sentence; a pause inside a sentence; a pause over 4 s
    bad = [({'scenes': [{'first_word_id': words[0]['id'], 'title': 'a'}, {'first_word_id': words[1]['id'], 'title': 'b'}]}, 'beginning of a sentence'),
           ({'scenes': [{'first_word_id': words[0]['id'], 'title': 'a'}], 'pauses': [{'after_word_id': words[1]['id'], 'seconds': 1, 'reason': 'x'}]}, 'sentence ends'),
           ({'scenes': [{'first_word_id': words[0]['id'], 'title': 'a'}], 'pauses': [{'after_word_id': sents[0]['last_word_id'], 'seconds': 5, 'reason': 'x'}]}, 'at most')]
    (ws / 'out' / 'scenes.json').write_text(json.dumps(bad[0][0]), encoding='utf-8')
    rc, out, _ = vw(home, 'options', 'scenes', '--file', 'out/scenes.json')
    assert rc == 2 and 'approval' in out['message'], out
    for doc, msg in bad:
        (ws / 'out' / 'scenes.json').write_text(json.dumps(doc), encoding='utf-8')
        rc, out, _ = vw(home, 'options', 'scenes', '--file', 'out/scenes.json', '--quote', 'yes')
        assert rc == 2 and msg in out['message'], (msg, out)
    out, pk = approve_scenes(home, ws)
    cut = pk['narration']['cuts'][0]
    natural = cut['natural_gap_s']
    assert cut['inserted_frames'] == round((0.5 - natural) * 25) and out['inserted_seconds'] == round(cut['inserted_frames'] / 25, 2)
    total = pk['narration']['total_frames']
    assert total == 50 + cut['inserted_frames'] and out['film_seconds'] == total / 25
    b1, b2 = pk['beats']
    assert (b1['title'], b2['title']) == ('Pressing', 'Not fired') and b1['timeline_end_frame'] == b2['timeline_start_frame'] == cut['source_cut_frame'] + cut['inserted_frames']
    assert b2['timeline_end_frame'] == total and [p['after_word_id'] for p in b1['pauses']] == [sents[0]['last_word_id']]
    assert pk['narration']['sentences'][1]['start_frame'] == sents[1]['start_frame'] + cut['inserted_frames']   # words after the pause move; before do not
    assert pk['narration']['sentences'][0]['start_frame'] == sents[0]['start_frame']
    # options on the new beats; the review film carries the pause inside BEAT_01's window
    doc = author(pk)
    (ws / 'out' / 'options.json').write_text(json.dumps(doc), encoding='utf-8')
    rc, out, err = vw(home, 'options', 'propose', '--file', 'out/options.json')
    assert rc == 0, (out, err)
    assert vw(home, 'options', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'options', 'fetch')
    assert rc == 0 and abs(out['duration_s'] - (2 * 75 + 2 * b1['target_beat_frames']) / 25) < 0.15, (out, err)
    pause_at, pause_len = cut['source_cut_frame'] / 25, cut['inserted_frames'] / 25
    sil = silences_in(ws / 'out' / 'review.mp4')
    beat_s = b1['target_beat_frames'] / 25   # the pause closes BEAT_01, so in option 1 it runs into the next (silent) slate; option 2 ends the film with it
    assert any(abs(s - (3.0 + pause_at)) < 0.1 and abs(d - (pause_len + 3.0)) < 0.1 for s, d in sil), (sil, pause_at, pause_len)
    assert any(abs(s - (6.0 + beat_s + pause_at)) < 0.1 and abs(d - pause_len) < 0.1 for s, d in sil), (sil, pause_at, pause_len)
    rc, out, err = vw(home, 'options', 'record', '--quote', 'yes, these options')
    assert rc == 0, (out, err)
    summary = vw(home, 'view', '--stage', 'options')[1]['outputs'][0]['summary']
    assert summary['scenes']['version'] == 1 and summary['scenes']['pauses'] == 1 and summary['scenes']['quote'].startswith('yes')
    # master: the whole timeline including the pause; the silence sits at the cut
    assert vw(home, 'master', 'decide', '--option', '1', '--action', 'KEEP')[0] == 0
    assert vw(home, 'master', 'decide', '--option', '2', '--action', 'REJECT', '--note', 'prefer the wide')[0] == 0
    rc, out, err = vw(home, 'master', 'build')
    assert rc == 0 and out['duration_frames'] == total, (out, err)
    assert vw(home, 'master', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'master', 'fetch')
    assert rc == 0 and abs(out['duration_s'] - total / 25) < 0.15, (out, err)
    sil = silences_in(ws / 'out' / 'master.mp4')
    assert any(abs(s - pause_at) < 0.1 and abs(d - pause_len) < 0.1 for s, d in sil), (sil, pause_at, pause_len)


# ---------- ticket 7 (15 Oct 2026): recorded scenes vanished ----------

def test_t7_supabase_reads_bypass_the_cdn(monkeypatch):
    from app import storage as S
    seen = []
    st = S.SupabaseStorage.__new__(S.SupabaseStorage)
    st.bucket = 'b'
    monkeypatch.setattr(st, '_call', lambda method, path, **kw: seen.append(path) or type('R', (), {'content': b'{}'})())
    st.get('run/stage2/session.json')
    st.get('run/stage2/session.json')
    assert all('?nocache=' in p for p in seen) and seen[0] != seen[1]   # a unique URL each read: never a cached copy


def test_t7_failed_session_read_is_not_a_new_session():
    from app.errors import Problem
    from app.stage2 import stage as S

    class Flaky:
        def get(self, k):
            raise Problem(502, 'STORAGE', 'Storage returned 520.')

        def exists(self, k):
            return True
    with pytest.raises(Problem) as e:
        S.session_of(Flaky(), {'id': 'r'}, create=True)
    assert e.value.status == 502


def test_t7_scene_process_stage_may_be_singular():
    from app.stage2 import narration as N
    out = N.normalise_scenes([{'first_word_id': 'W1', 'title': 'a', 'process_stage': 'Stage_1'}, {'first_word_id': 'W9', 'title': 'b', 'process_stages': ['Stage_2']}])
    assert [s['process_stages'] for s in out] == [['Stage_1'], ['Stage_2']] and 'process_stage' not in out[0]
