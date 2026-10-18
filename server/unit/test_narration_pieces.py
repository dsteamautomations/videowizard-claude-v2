"""design/40: splitting, identity, merged timing and the audio join, without a database."""
import shutil
import subprocess

import pytest

from app import narration_pieces as NP
from app.voice_timing import inspect_audio, timing_evidence, validate_alignment

SNAP = {'voice_id': 'v1', 'model_id': 'eleven_v4', 'settings': {'stability': 0.5, 'similarity_boost': 0.75}, 'format': 'mp3_44100_128'}


def paragraphs(sizes, sentence='Earth blocks are pressed. '):
    """Paragraphs of about the given character counts, made of whole sentences."""
    out = []
    for size in sizes:
        out.append((sentence * (size // len(sentence) + 1))[:size].rstrip())
        if not out[-1].endswith('.'):
            out[-1] = out[-1].rsplit('.', 1)[0] + '.'
    return '\n\n'.join(out) + '\n'


def texts_of(text, pieces):
    return [text[p['offset']:p['offset'] + p['characters']] for p in pieces]


# ---------- split_for_narration ----------

def test_short_script_is_one_piece():
    text = 'Earth blocks are pressed.\n\nNot fired.\n'
    pieces = NP.split_for_narration(text, 10000)
    assert pieces == [{'offset': 0, 'characters': len(text.rstrip())}] and texts_of(text, pieces) == [text.rstrip()]


def test_long_script_splits_at_paragraph_ends_and_round_trips():
    text = paragraphs([8000, 8000, 8000])
    pieces = NP.split_for_narration(text, 10000)
    assert len(pieces) == 3 and all(p['characters'] <= 10000 for p in pieces)
    assert all(t.endswith('.') and not t.startswith('\n') for t in texts_of(text, pieces))
    assert '\n\n'.join(texts_of(text, pieces)) == text.rstrip()   # every spoken character, in order


def test_small_paragraphs_are_packed_together():
    text = paragraphs([3000, 3000, 3000, 3000])
    pieces = NP.split_for_narration(text, 10000)
    assert len(pieces) == 2 and pieces[0]['characters'] > 6000 and pieces[0]['characters'] <= 10000
    assert '\n\n' in texts_of(text, pieces)[0]   # a piece keeps its internal paragraph break


def test_one_long_paragraph_splits_at_sentence_ends():
    text = paragraphs([12000])
    pieces = NP.split_for_narration(text, 10000)
    assert len(pieces) == 2 and all(t.endswith('.') for t in texts_of(text, pieces))
    assert ' '.join(texts_of(text, pieces)) == text.rstrip()


def test_one_long_sentence_is_refused():
    text = 'a' * 10500 + '.\n'
    with pytest.raises(ValueError) as exc:
        NP.split_for_narration(text, 10000)
    assert 'one sentence' in str(exc.value) and 'script stage' in str(exc.value)


def test_empty_text_has_no_pieces():
    assert NP.split_for_narration('\n\n  \n', 10000) == []


# ---------- identity and pieces_of ----------

def test_identity_depends_on_voice_model_settings_and_text():
    base = NP.piece_identity(SNAP, 'Earth.')
    assert len(base) == 64 and NP.piece_identity(SNAP, 'Earth.') == base
    assert NP.piece_identity({**SNAP, 'voice_id': 'v2'}, 'Earth.') != base
    assert NP.piece_identity({**SNAP, 'settings': {'stability': 0.6, 'similarity_boost': 0.75}}, 'Earth.') != base
    assert NP.piece_identity(SNAP, 'Earth!') != base


def test_pieces_of_rebuilds_texts_and_defaults_to_one_piece():
    text = paragraphs([8000, 8000])
    snap = {**SNAP, 'text': text, 'pieces': NP.split_for_narration(text, 10000)}
    pieces = NP.pieces_of(snap)
    assert len(pieces) == 2 and pieces[0]['text'] == text[:pieces[0]['characters']] and pieces[1]['identity'] != pieces[0]['identity']
    assert NP.pieces_of({**SNAP, 'text': 'Just this.\n'})[0]['text'] == 'Just this.\n'


# ---------- merge_alignments ----------

def alignment_for(text, duration, pad=0.0):
    n = len(text)
    starts = [round(i * duration / n, 4) for i in range(n)]
    ends = [round((i + 1) * duration / n, 4) for i in range(n)]
    ends[-1] = round(ends[-1] + pad, 4)   # provider padding after the decoded audio
    return {'characters': list(text), 'character_start_times_seconds': starts, 'character_end_times_seconds': ends}


def test_merge_two_pieces_offsets_clamps_and_fills_the_gap():
    text = 'Earth blocks are pressed.\n\nNot fired.\n'
    p1, p2 = 'Earth blocks are pressed.', 'Not fired.'
    merged = NP.merge_alignments(text, [{'offset': 0, 'text': p1, 'alignment': alignment_for(p1, 2.0, pad=0.3), 'duration_s': 2.0},
                                        {'offset': text.index(p2), 'text': p2, 'alignment': alignment_for(p2, 1.0), 'duration_s': 1.0}])
    a = merged['alignment']
    assert validate_alignment(a) == text and merged['normalized_alignment'] is None
    assert a['character_end_times_seconds'][len(p1) - 1] == 2.0   # clamped to the piece's decoded duration
    assert merged['pieces'][0]['overshoot_s'] == 0.3 and merged['pieces'][1]['overshoot_s'] == 0.0
    gap = range(len(p1), text.index(p2))
    assert all(a['character_start_times_seconds'][i] == 2.0 and a['character_end_times_seconds'][i] == 2.0 for i in gap)
    assert a['character_start_times_seconds'][text.index(p2)] == 2.0 and a['character_end_times_seconds'][-1] == 3.0
    timing = timing_evidence({**SNAP, 'text': text, 'source_script': 'x'}, {'alignment': a, 'normalized_alignment': None})
    assert timing['script_characters_match'] and [w['passage_id'] for w in timing['words']] == ['P001'] * 4 + ['P002'] * 2
    assert timing['words'][4]['start_s'] >= 2.0 and timing['last_character_end_s'] == 3.0


def test_merge_refuses_a_piece_whose_alignment_is_not_its_text():
    with pytest.raises(ValueError):
        NP.merge_alignments('Earth.', [{'offset': 0, 'text': 'Earth.', 'alignment': alignment_for('Mars.', 1.0), 'duration_s': 1.0}])


def test_merge_one_piece_keeps_the_normalized_alignment():
    text = 'Earth.'
    merged = NP.merge_alignments(text, [{'offset': 0, 'text': text, 'alignment': alignment_for(text, 1.0), 'duration_s': 1.0, 'normalized_alignment': {'x': 1}}])
    assert merged['normalized_alignment'] == {'x': 1}


# ---------- concat_mp3 (needs ffmpeg) ----------

@pytest.mark.skipif(shutil.which('ffmpeg') is None, reason='ffmpeg not installed')
def test_concat_joins_pieces_and_durations_add_up(tmp_path):
    pieces = []
    for i, seconds in enumerate((1, 2)):
        p = tmp_path / f'p{i}.mp3'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}', '-codec:a', 'libmp3lame', '-b:a', '128k', str(p)], check=True)
        pieces.append(p)
    out = NP.concat_mp3(pieces, tmp_path / 'out' / 'narration.mp3')
    assert out.is_file() and not (tmp_path / 'out' / 'narration.mp3.tmp').exists()
    total = inspect_audio(out)['duration_s']
    parts = sum(inspect_audio(p)['duration_s'] for p in pieces)
    assert abs(total - parts) < 0.2 and inspect_audio(out)['sample_rate'] == 44100
    single = NP.concat_mp3([pieces[0]], tmp_path / 'single.mp3')
    assert single.read_bytes() == pieces[0].read_bytes()
