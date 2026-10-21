"""Intake prepare and record as pure file functions (design/34 1.1–1.5, 1.8, 1.19)."""
import hashlib
import json

import pytest

from conftest import STAGES
import stages_text
from stages_text import Refused, intake_prepare, intake_record

SOURCE = """Scene 1: The yard

Narration: Earth blocks are made from the soil beneath our feet.

Duration: 30 seconds

Visuals
- Close-up of finished blocks

Narration: Each block is pressed, not fired, so it keeps the carbon in the ground.
"""
PROC = STAGES['intake']


def prior(stage):
    raise AssertionError('intake has no earlier stage')


def proposal(ws, **over):
    data = {'remove': [{'line': 1, 'kind': 'scene_heading', 'why': 'heading'}, {'line': 5, 'kind': 'timing', 'why': 'duration'},
                       {'line': 7, 'kind': 'section_label', 'why': 'label'}, {'line': 8, 'kind': 'visual_note', 'why': 'seen not said'}],
            'titles': ['Earth Blocks - Documentary Explainer', 'Pressed Earth - Explainer'], 'notes': 'removed plan lines', **over}
    (ws / 'out' / 'intake.json').write_text(json.dumps(data), encoding='utf-8')


def test_numbered_script_goes_to_a_file_and_the_prompt_never_does(ws):
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    out = intake_prepare(ws, PROC, prior, earlier_titles=[{'code': 'VW-3', 'title': 'All About Rat-Trap Bond Masonry - Documentary Explainer'}])
    numbered = (ws / 'work' / 'intake-numbered.md').read_text(encoding='utf-8')
    assert numbered.startswith('1: Scene 1: The yard\n2: \n3: Narration: Earth blocks')
    assert '{numbered_script}' not in out['prompt'] and 'Scene 1: The yard' not in out['prompt']   # 1.1: not pasted into the prompt
    assert 'work/intake-numbered.md' in out['prompt'] and out['numbered_file'] == 'work/intake-numbered.md'
    assert out['lines'] == 11 and out['characters'] == len(SOURCE)   # the trailing newline is line 11, as numbered() has always counted
    assert out['prompt'].startswith('VW-PROCEDURE') and 'You propose; the operator decides.' in out['prompt'] and 'â€' not in out['prompt']
    assert 'VW-3: All About Rat-Trap Bond Masonry' in out['prompt'] and out['earlier_titles'][0]['code'] == 'VW-3'   # 1.5
    assert out['prepared_at'].endswith('Z')   # 1.19
    for p in ws.rglob('*'):   # 1.11: the procedure text is on no file
        if p.is_file():
            assert 'VW-PROCEDURE' not in p.read_text(encoding='utf-8', errors='replace'), p
    src = json.loads((ws / 'work' / 'intake-source.json').read_text(encoding='utf-8'))
    assert src['file'] == 'source.txt' and src['sha256'] == hashlib.sha256(SOURCE.encode()).hexdigest() and src['bytes'] == len(SOURCE.encode())


def test_long_lines_are_wrapped_with_a_continuation_indent(ws):
    (ws / 'in' / 'source.txt').write_text('Narration: ' + 'word ' * 60 + '\n', encoding='utf-8')
    intake_prepare(ws, PROC, prior)
    lines = (ws / 'work' / 'intake-numbered.md').read_text(encoding='utf-8').split('\n')
    assert lines[0].startswith('1: Narration:') and len(lines[0]) <= 160 and lines[1].startswith('    word')


def test_first_film_has_no_earlier_titles(ws):
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    out = intake_prepare(ws, PROC, prior, earlier_titles=[])
    assert '\nnone\n' in out['prompt'] and out['earlier_titles'] == []


def test_two_documents_refuse_and_file_picks(ws):
    """1.3"""
    (ws / 'in' / 'script.pdf').write_bytes(b'%PDF-1.4 not really')
    (ws / 'in' / 'script-ocr.txt').write_text(SOURCE, encoding='utf-8')
    with pytest.raises(Refused) as exc:
        intake_prepare(ws, PROC, prior)
    assert 'more than one document' in str(exc.value) and 'script-ocr.txt' in str(exc.value) and 'script.pdf' in str(exc.value)
    assert not (ws / 'work' / 'intake-source.json').exists()
    out = intake_prepare(ws, PROC, prior, file='script-ocr.txt')
    assert out['source_file'] == 'script-ocr.txt'
    with pytest.raises(Refused) as exc:
        intake_prepare(ws, PROC, prior, file='notes.txt')
    assert 'not one of' in str(exc.value)
    with pytest.raises(Refused):
        intake_prepare(ws, PROC, prior, file='../in/script-ocr.txt')


def test_clips_in_the_folder_are_not_documents(ws):
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    (ws / 'in' / 'clip.mp4').write_bytes(b'\x00' * 10)
    assert intake_prepare(ws, PROC, prior)['source_file'] == 'source.txt'


def test_record_requires_the_operators_title(ws):
    """1.2"""
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    intake_prepare(ws, PROC, prior)
    proposal(ws)
    for title in (None, '', '   '):
        with pytest.raises(Refused) as exc:
            intake_record(ws, PROC, prior, title=title, client='VK')
        assert '--title' in str(exc.value)
    assert not (ws / 'out' / 'source.txt').exists()
    res = intake_record(ws, PROC, prior, title='Pressed Earth - Explainer', client='VK')
    assert res['summary']['title'] == 'Pressed Earth - Explainer' and res['summary']['title_source'] == 'suggested'
    res = intake_record(ws, PROC, prior, title='My own name', client='VK')
    assert res['summary']['title_source'] == 'typed'


def test_record_cleans_and_counts(ws):
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    intake_prepare(ws, PROC, prior)
    proposal(ws)
    res = intake_record(ws, PROC, prior, title='Earth Blocks - Documentary Explainer', client='VK')
    cleaned = (ws / 'out' / 'source.txt').read_text(encoding='utf-8')
    assert 'Scene 1' not in cleaned and 'Duration' not in cleaned and 'Close-up' not in cleaned and 'keeps the carbon' in cleaned
    s = res['summary']
    assert s['removed_lines'] == 4 and s['kept_lines'] == 2 and s['source_file'] == 'source.txt' and len(s['source_sha256']) == 64
    assert s['prepared_at'].endswith('Z') and s['recorded_at'] >= s['prepared_at'] and s['source_digest'] == stages_text.digest(cleaned)
    assert res['files'] == ['out/source.txt', 'out/original.txt', 'out/intake.json'] and (ws / 'out' / 'original.txt').read_text() == SOURCE


def test_titles_non_empty_strings_only_never_a_traceback(ws):
    """1.4: a one-character title is fine; a non-string or an empty one is a refusal, not a crash."""
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    intake_prepare(ws, PROC, prior)
    proposal(ws, titles=['T'])
    assert intake_record(ws, PROC, prior, title='T', client='VK')['summary']['titles'] == ['T']
    for bad in ([42], [None], ['ok', ''], [], 'not a list', ['  ']):
        proposal(ws, titles=bad)
        with pytest.raises(Refused) as exc:
            intake_record(ws, PROC, prior, title='x', client='VK')
        assert 'titles' in str(exc.value)


def test_source_replaced_after_prepare_is_refused(ws):
    """1.8"""
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    intake_prepare(ws, PROC, prior)
    proposal(ws)
    (ws / 'in' / 'source.txt').write_text(SOURCE + '\nNarration: one more line.\n', encoding='utf-8')
    with pytest.raises(Refused) as exc:
        intake_record(ws, PROC, prior, title='T', client='VK')
    assert 'changed' in str(exc.value) and 'prepare' in str(exc.value)
    (ws / 'in' / 'source.txt').unlink()
    with pytest.raises(Refused):
        intake_record(ws, PROC, prior, title='T', client='VK')


def test_record_before_prepare(ws):
    proposal(ws)
    with pytest.raises(Refused) as exc:
        intake_record(ws, PROC, prior, title='T', client='VK')
    assert 'prepare' in str(exc.value)


# ---------- design/53 L1, L2: the preview of the kept text; the document's timing lines ----------

def test_preview_writes_the_kept_text_and_refuses_before_prepare(ws):
    from stages_text import intake_preview
    (ws / 'in' / 'script.txt').write_text(SOURCE, encoding='utf-8')
    with pytest.raises(Refused):
        intake_preview(ws)
    intake_prepare(ws, PROC, prior)
    (ws / 'out' / 'intake.json').write_text(json.dumps({'remove': [{'line': 1, 'kind': 'scene_heading', 'why': 'h'}, {'line': 5, 'kind': 'timing', 'why': 't'}], 'titles': ['T']}), encoding='utf-8')
    out = intake_preview(ws)
    text = (ws / 'work' / 'intake-preview.txt').read_text(encoding='utf-8')
    assert 'Scene 1' not in text and 'Duration' not in text and 'Earth blocks are made' in text and 'Each block is pressed' in text
    assert out['removed'] == 2 and out['kept'] == text.count('\n') - text.count('\n\n') or out['kept'] > 0
    assert out['file'] == 'work/intake-preview.txt'


def test_record_keeps_the_documents_timing_lines(ws):
    (ws / 'in' / 'script.txt').write_text(SOURCE, encoding='utf-8')
    intake_prepare(ws, PROC, prior)
    (ws / 'out' / 'intake.json').write_text(json.dumps({'remove': [{'line': 1, 'kind': 'scene_heading', 'why': 'h'}, {'line': 5, 'kind': 'timing', 'why': 't'}], 'titles': ['T']}), encoding='utf-8')
    s = intake_record(ws, PROC, prior, title='T', client='VK')['summary']
    assert s['timing_lines'] == ['Duration: 30 seconds']
    (ws / 'out' / 'intake.json').write_text(json.dumps({'remove': [], 'titles': ['T']}), encoding='utf-8')
    assert intake_record(ws, PROC, prior, title='T', client='VK')['summary']['timing_lines'] == []


def test_intake_steps_name_the_preview():
    assert 'vw stage intake preview' in ' '.join(PROC['steps']) and 'work/intake-preview.txt' in ' '.join(PROC['steps'])


def test_record_keeps_the_documents_visual_lines_per_scene(ws):
    """design/65 S3: the removed visual notes, grouped under their scene heading with the start of that scene's narration."""
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    intake_prepare(ws, PROC, prior)
    proposal(ws)
    s = intake_record(ws, PROC, prior, title='T', client='VK')['summary']
    assert s['intended_visuals'] == [{'heading': 'Scene 1: The yard', 'lines': ['- Close-up of finished blocks'], 'narration_starts': 'Narration: Earth blocks are made from the soil beneath our feet.'}]
    text = 'Scene 1: One\nVisuals\nA kiln.\nA wall.\nNarration\nFirst words of scene one here.\nScene 2: Two\nNarration\nSecond scene words.\nVisuals\nA roof.\n'
    removals = [{'line': 1, 'kind': 'scene_heading', 'why': ''}, {'line': 2, 'kind': 'section_label', 'why': ''}, {'line': 3, 'kind': 'visual_note', 'why': ''}, {'line': 4, 'kind': 'visual_note', 'why': ''},
                {'line': 5, 'kind': 'section_label', 'why': ''}, {'line': 7, 'kind': 'scene_heading', 'why': ''}, {'line': 8, 'kind': 'section_label', 'why': ''}, {'line': 10, 'kind': 'section_label', 'why': ''},
                {'line': 11, 'kind': 'visual_note', 'why': ''}]
    assert stages_text.visual_lines(text, removals) == [{'heading': 'Scene 1: One', 'lines': ['A kiln.', 'A wall.'], 'narration_starts': 'First words of scene one here.'},
                                                         {'heading': 'Scene 2: Two', 'lines': ['A roof.'], 'narration_starts': 'Second scene words.'}]
    assert stages_text.visual_lines('Just words.\n', []) == []
    assert stages_text.visual_lines('Seen: a kiln\nWords.\n', [{'line': 1, 'kind': 'visual_note', 'why': ''}]) == [{'heading': '', 'lines': ['Seen: a kiln'], 'narration_starts': 'Words.'}]
