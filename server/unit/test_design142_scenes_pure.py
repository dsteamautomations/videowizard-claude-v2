"""design/142 R8, R9 (SK, 2 Nov 2026; Revathi's points 1, 4, 5, 7): the chapter message says what it checks; a scene may name every chapter it covers;
every brief chapter is covered or dropped with the operator's words, and an uncovered one shows the client's picture notes behind it; a pause inside a
scene is refused by name; the scenes shape is in the package."""
import pytest

from app.stage2 import narration as NR

STAGES = ['Mixing and pouring', 'Compacting and levelling', 'Training programmes and visitors']
NOTES = [{'heading': 'Scene 9', 'lines': ['Visitors observing and learning', 'Training programmes in progress'], 'narration_starts': 'The demonstration centre'}]


def scenes(*chapters):
    return [{'first_word_id': f'W{i}', 'title': f'S{i}', 'process_stages': list(c)} for i, c in enumerate(chapters)]


def test_the_message_says_no_scene_names_a_chapter_and_a_closing_may_have_none():
    words = [{'id': 'W0', 'text': 'A.', 'start_s': 0, 'end_s': 1}]
    with pytest.raises(ValueError) as e:
        NR.validate_scenes(words, [{'first_word_id': 'W0', 'title': 'x'}], STAGES)
    assert 'No scene names a chapter' in str(e.value) and 'closing' in str(e.value)


def test_every_chapter_is_covered_or_dropped_with_words():
    with pytest.raises(ValueError) as e:
        NR.scenes_cover(scenes(['Mixing and pouring', 'Compacting and levelling']), STAGES, [], NOTES)
    msg = str(e.value)
    assert 'Training programmes and visitors' in msg and 'Training programmes in progress' in msg and 'picture notes' in msg
    NR.scenes_cover(scenes(['Mixing and pouring', 'Compacting and levelling'], ['Training programmes and visitors']), STAGES, [], NOTES)
    NR.scenes_cover(scenes(['Mixing and pouring', 'Compacting and levelling']), STAGES, [{'chapter': 'Training programmes and visitors', 'words': 'drop it, the narration never says it'}], NOTES)
    with pytest.raises(ValueError):
        NR.scenes_cover(scenes(['Mixing and pouring', 'Compacting and levelling']), STAGES, [{'chapter': 'Training programmes and visitors'}], NOTES)   # no words


def test_a_pause_inside_a_scene_is_refused_by_name():
    with pytest.raises(ValueError) as e:
        NR.scenes_cover([{'first_word_id': 'W0', 'title': 'x', 'process_stages': STAGES, 'pauses': [{'after_word_id': 'W3', 'seconds': 1}]}], STAGES, [], [])
    assert 'pauses' in str(e.value) and 'top' in str(e.value)


def test_the_scenes_shape_is_in_the_package():
    from app.stage2 import package as P
    shape = P.SCENES_SHAPE
    assert 'pauses' in shape and 'dropped_chapters' in shape and shape['scenes'][0]['process_stages'] and 'pauses' not in shape['scenes'][0]
