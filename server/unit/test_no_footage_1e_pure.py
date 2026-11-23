"""SK, 23 Nov 2026 (no-footage release 1e): the assembly and the hand-over of a film with no camera file in its cut. Nothing promises a camera
file, a folder of originals or a relink: the editor's package says what it holds, and the next step names no `--originals`. A cut with a camera
file (the film's own, or a library clip) reads as before."""
import json
from pathlib import Path

import pytest

from app import core
from app.stage3 import delivery as D, early as E

SERVER = Path(__file__).resolve().parents[1]
STAGES = {s['name']: s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']}
RUN = {'code': 'VW-T', 'client': 'C'}
CAMERA_WORDS = ('camera', 'original', 'relink', 'nat sound')


def clean(text):
    return [w for w in CAMERA_WORDS if w in text.lower()]


def test_the_early_package_names_no_camera_file_when_the_cut_has_none():
    with_, without = E.open_edit_text('VW-T'), E.open_edit_text('VW-T', camera=False)
    assert E.open_edit_text('VW-T', camera=True) == with_ and '--originals' in with_ and 'Relink-list.csv' in with_   # as before
    assert clean(without) == [] and '`vw delivery open`' in without and 'Timeline/VW-T.fcpxml' in without and 'Media/AI/' in without
    assert 'Cut-list.csv' in without and 'Super Scale' in without   # what holds for an AI film stays


def test_the_next_step_of_the_early_package_asks_for_no_folder_of_originals():
    assert '--originals' in D.early_next(True) and 'no camera copies by default' in D.early_next(True)
    assert clean(D.early_next(False)) == [] and '`vw delivery download`' in D.early_next(False) and '`vw delivery open`' in D.early_next(False)


def test_the_full_package_has_no_relink_section_when_the_cut_has_no_camera_file():
    with_, without = D.open_edit_text(RUN, ai=True), D.open_edit_text(RUN, ai=True, camera=False)
    assert D.open_edit_text(RUN, ai=True, camera=True) == with_ and '## Relink to the full-quality originals' in with_
    assert clean(without) == [] and 'AI-shots.md' in without and 'On Resolve Studio the plugin can do the import itself' in without
    assert 'the voiceover on A1' in without and 'A2' not in without.split('A3')[0]   # no camera sound track is promised


def test_the_finishing_checklist_names_no_camera_sound_when_the_cut_has_no_clip():
    said = lambda subs: ' '.join(i['item'] for i in D.checklist_of({}, {'sub_clips': subs}, {}))
    assert 'nat-sound' in said([{'sub_clip_id': 's1'}]) and 'nat-sound' not in said([]) and 'Master bus' in said([])


@pytest.mark.parametrize('name', ['assembly', 'delivery'])
def test_the_instructions_of_a_film_with_no_footage_ask_for_no_camera_file(name):
    own, none = core.for_footage(STAGES[name], 'own'), core.for_footage(STAGES[name], 'none')
    text = json.dumps(none['steps'], ensure_ascii=False).lower().replace('no camera footage', '').replace('no camera file', '')
    assert [w for w in ('--originals', 'relink-check', 'camera', 'originals used', 'the relink list') if w in text] == []
    assert len(none['steps']) == len(own['steps']) and '`vw delivery bundle`' in none['steps'][0]
    assert '--originals' in json.dumps(own['steps'])   # a film with footage reads what it read
