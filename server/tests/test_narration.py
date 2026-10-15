"""Scene beats and sentence-end pauses on the real VW-1 narration timing (design/19 A1–A7). Pure arithmetic; no AI, no ffmpeg."""
import json
from pathlib import Path

import pytest

from app.stage2 import narration as N
from app.voice_timing import clamp_words

FPS = 25
T = clamp_words(json.loads((Path(__file__).parent / 'fixtures' / 'vw1' / 'voice' / '328d22ee-427f-4586-9d63-3018bd9a27e7.timing.json').read_text(encoding='utf-8')), 1.0)
W = T['words']
DUR = T['audio']['duration_s']
SENT = N.sentence_ranges(W)


def ends(k):
    return W[SENT[k][1]]['id']


def starts(k):
    return W[SENT[k][0]]['id']


def test_no_pauses_is_the_recording_itself():
    plan, tl = N.plan(W, DUR, FPS)
    assert plan['pieces'] == [{'source_start_frame': 0, 'source_end_frame': N.frame(DUR, FPS), 'timeline_start_frame': 0}]
    assert plan['total_frames'] == N.frame(DUR, FPS) and tl(1000) == 1000


def test_pause_inserts_only_what_the_recording_lacks_and_cuts_in_silence():
    w = W[SENT[2][1]]
    gap = W[SENT[2][1] + 1]['start_s'] - w['end_s']
    plan, tl = N.plan(W, DUR, FPS, [{'after_word_id': w['id'], 'seconds': 2.0, 'reason': 'let the brick settle'}])
    c = plan['cuts'][0]
    assert c['inserted_frames'] == N.frame(2.0 - gap, FPS)                 # the natural gap counts toward the 2 s
    assert w['end_s'] * FPS <= c['source_cut_frame'] <= W[SENT[2][1] + 1]['start_s'] * FPS + 1   # cut in the silence, not in a word
    assert len(plan['pieces']) == 2 and plan['pieces'][1]['timeline_start_frame'] == c['source_cut_frame'] + c['inserted_frames']
    assert plan['total_frames'] == N.frame(DUR, FPS) + c['inserted_frames']
    # words after the pause move by exactly the inserted frames; words before do not move
    after = W[SENT[2][1] + 1]
    assert tl(N.frame(after['start_s'], FPS)) == N.frame(after['start_s'], FPS) + c['inserted_frames']
    assert tl(N.frame(W[0]['start_s'], FPS)) == N.frame(W[0]['start_s'], FPS)


def test_a_voiceover_that_already_breathes_gets_nothing_extra():
    words = [dict(w) for w in W]
    i = SENT[1][1]
    shift = 1.5
    for w in words[i + 1:]:
        w['start_s'] += shift
        w['end_s'] += shift
    plan, _ = N.plan(words, DUR + shift, FPS, [{'after_word_id': words[i]['id'], 'seconds': 1.2, 'reason': 'step'}])
    assert plan['cuts'][0]['inserted_frames'] == 0 and plan['cuts'][0]['natural_gap_s'] >= 1.2


def test_pause_rules():
    mid = W[SENT[0][0] + 1]
    with pytest.raises(ValueError, match='sentence'):
        N.plan(W, DUR, FPS, [{'after_word_id': mid['id'], 'seconds': 1.0, 'reason': 'x'}])
    with pytest.raises(ValueError, match='at most'):
        N.plan(W, DUR, FPS, [{'after_word_id': ends(0), 'seconds': 4.5, 'reason': 'x'}])
    with pytest.raises(ValueError, match='reason'):
        N.plan(W, DUR, FPS, [{'after_word_id': ends(0), 'seconds': 1.0, 'reason': ''}])
    with pytest.raises(ValueError, match='Two pauses'):
        N.plan(W, DUR, FPS, [{'after_word_id': ends(0), 'seconds': 1.0, 'reason': 'x'}, {'after_word_id': ends(0), 'seconds': 2.0, 'reason': 'y'}])
    plan, _ = N.plan(W, DUR, FPS, [{'after_word_id': W[-1]['id'], 'seconds': 2.0, 'reason': 'end card'}])   # after the last word: silence at the end
    assert plan['total_frames'] > N.frame(DUR, FPS) and len(plan['pieces']) == 1


def test_scene_rules():
    with pytest.raises(ValueError, match='first word'):
        N.validate_scenes(W, [{'first_word_id': starts(1), 'title': 'x'}])
    with pytest.raises(ValueError, match='beginning of a sentence'):
        N.validate_scenes(W, [{'first_word_id': W[0]['id'], 'title': 'a'}, {'first_word_id': W[SENT[1][0] + 1]['id'], 'title': 'b'}])
    with pytest.raises(ValueError, match='after scene'):
        N.validate_scenes(W, [{'first_word_id': W[0]['id'], 'title': 'a'}, {'first_word_id': starts(3), 'title': 'b'}, {'first_word_id': starts(2), 'title': 'c'}])
    with pytest.raises(ValueError, match='not in the brief'):
        N.validate_scenes(W, [{'first_word_id': W[0]['id'], 'title': 'a', 'process_stages': ['Stage_X']}], ['Stage_1'])
    N.validate_scenes(W, [{'first_word_id': W[0]['id'], 'title': 'a', 'process_stages': ['Stage_1']}, {'first_word_id': starts(4), 'title': 'b'}], ['Stage_1'])


def test_beats_tile_the_timeline_and_a_boundary_pause_belongs_to_the_scene_that_ended():
    scenes = [{'first_word_id': W[0]['id'], 'title': 'one'}, {'first_word_id': starts(3), 'title': 'two'}, {'first_word_id': starts(8), 'title': 'three'}]
    pauses = [{'after_word_id': ends(2), 'seconds': 2.0, 'reason': 'scene change'}, {'after_word_id': ends(5), 'seconds': 1.5, 'reason': 'step one done'}]
    plan, tl = N.plan(W, DUR, FPS, pauses)
    bs = N.beats(W, scenes, plan, tl, FPS)
    assert bs[0]['timeline_start_frame'] == 0 and bs[-1]['timeline_end_frame'] == plan['total_frames']
    assert all(a['timeline_end_frame'] == b['timeline_start_frame'] for a, b in zip(bs, bs[1:]))
    assert sum(b['target_beat_frames'] for b in bs) == plan['total_frames']
    assert [p['after_word_id'] for p in bs[0]['pauses']] == [ends(2)] and [p['after_word_id'] for p in bs[1]['pauses']] == [ends(5)]
    cut = plan['cuts'][0]
    assert bs[1]['timeline_start_frame'] == cut['source_cut_frame'] + cut['inserted_frames']   # scene two starts after the silence
    sents = N.sentences(W, FPS, tl)
    assert len(sents) == len(SENT) and sents[3]['start_frame'] >= bs[1]['timeline_start_frame']
    sil = N.silences(W, FPS, tl, plan['total_frames'])
    assert any(s['start_frame'] < bs[1]['timeline_start_frame'] <= s['end_frame'] for s in sil)   # the 2 s pause is a silence of ≥ 1.2 s


def test_paragraph_default_matches_the_old_beat_windows():
    from app.stage2 import package as P
    script_beats = [{'beat_id': 'BEAT_01', 'passage_id': W[0]['passage_id'], 'text': ''}]
    old = P.beat_windows(script_beats, T, FPS, DUR)
    plan, tl = N.plan(W, DUR, FPS)
    new = N.beats(W, N.paragraph_scenes(script_beats, W), plan, tl, FPS, ids=['BEAT_01'])
    assert (new[0]['timeline_start_frame'], new[0]['timeline_end_frame']) == (old[0]['timeline_start_frame'], old[0]['timeline_end_frame'])
