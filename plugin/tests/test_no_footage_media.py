"""SK, 23 Nov 2026 (no-footage release 1b): the media step of a film with no camera footage of its own. Nothing is listed, probed or uploaded, and
no camera question is asked; the step records an empty clip list, so the analysis has no unit and the run goes to the first cut. A film with
footage behaves as before."""
import json

import pytest

from conftest import STAGES
from stages_av import Refused, media_prepare, media_record

PROC = STAGES['media']


def never(*a):
    raise AssertionError('nothing is uploaded on a film with no camera footage')


def test_prepare_needs_no_clip_and_asks_for_the_shape(ws):
    out = media_prepare(ws, PROC, None, has_footage='none')
    assert out['clips'] == [] and out['footage'] == 'none' and 'vw shape' in out['message'] and 'camera' not in out['message'].replace('no camera footage', '')
    assert out['steps'] == PROC['steps'] and out['prompt'] == PROC['prompt']   # the text is the server's, already the one for this film
    assert not (ws / 'work' / 'media-clips.json').exists()


def test_photographs_in_the_folder_are_left_for_the_visuals_step(ws):
    (ws / 'in' / 'factory.jpg').write_bytes(b'x')
    (ws / 'in' / 'logo.png').write_bytes(b'x')
    out = media_prepare(ws, PROC, None, has_footage='none')
    assert out['clips'] == [] and out['pictures_seen'] == 2 and 'visuals' in out['message']


def test_a_video_file_in_the_folder_is_refused_by_name(ws):
    (ws / 'in' / 'site-walk.MP4').write_bytes(b'x')
    for step in (lambda: media_prepare(ws, PROC, None, has_footage='none'), lambda: media_record(ws, PROC, None, never, has_footage='none', shape='horizontal')):
        with pytest.raises(Refused) as e:
            step()
        assert 'site-walk.MP4' in str(e.value) and 'no camera footage' in str(e.value)


def test_record_asks_no_camera_question_and_records_an_empty_list(ws):
    res = media_record(ws, PROC, None, never, has_footage='none', shape='horizontal')
    s = res['summary']
    assert s['clips'] == [] and s['units'] == {'analysis': []} and s['total_duration_s'] == 0 and s['footage'] == 'none'
    assert s['camera_audio'] == 'excluded' and s['copies'] is None and s['shot_on'] is None and s['recorded_at']
    assert res['files'] == ['out/media.json'] and res['stored'] == [] and json.loads((ws / 'out' / 'media.json').read_text(encoding='utf-8')) == {'clips': []}


def test_record_waits_for_the_shape(ws):
    with pytest.raises(Refused) as e:
        media_record(ws, PROC, None, never, has_footage='none', shape=None)
    assert 'vw shape' in str(e.value) and not (ws / 'out' / 'media.json').exists()


def test_a_film_with_footage_is_asked_for_its_clips_as_before(ws):
    for kw in ({}, {'has_footage': 'own'}):
        with pytest.raises(Refused) as e:
            media_prepare(ws, PROC, None, **kw)
        assert 'Put the source clips in' in str(e.value)
    with pytest.raises(Refused) as e:
        media_record(ws, PROC, None, never, has_footage='own')
    assert 'camera originals or copies' in str(e.value)
