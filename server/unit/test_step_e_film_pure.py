"""Integration step E, the film and the editor's package: a take's in point is chosen when it is selected and travels to the early package (made
before the assembly) and to the assembly's default; the offset is film frames everywhere and becomes the take's own frames once; an AI take is
declared without sound; the raw take ships beside its trimmed piece; the grain line says light."""
import copy
from fractions import Fraction

import pytest

from app import visuals_stage as VS
from app.stage3 import assembly as A, early as E, timeline as TL
import test_design115_pure as T115

GUIDE = {'kind': 'guide', 'placement': {'exact_seconds': 4.6}}
JOB = {'result': {'evidence': {'duration_seconds': 7.0}}}


# ---------- the in point, chosen at selection ----------

def test_a_guide_take_is_longer_than_its_slot_and_with_no_point_given_the_slot_sits_in_its_middle():
    assert VS.take_in_point(GUIDE, JOB, None) == {'in_s': 1.2}
    assert VS.take_in_point(GUIDE, JOB, '') == {'in_s': 1.2}
    assert VS.take_in_point(GUIDE, {'result': {'evidence': {'duration_seconds': 4.6}}}, None) == {}   # nothing to spare
    assert VS.take_in_point({'kind': 'motion', 'placement': {'exact_seconds': 4.6}}, JOB, None) == {}   # any other take starts at its first frame, as before


def test_a_given_in_point_is_kept_and_checked_against_the_take_and_its_slot():
    assert VS.take_in_point(GUIDE, JOB, 0.4) == {'in_s': 0.4} and VS.take_in_point(GUIDE, JOB, '2.4') == {'in_s': 2.4}
    for bad, word in ((-1, 'from 0'), (9, 'past the end'), (3.0, 'its slot needs 4.6 s'), ('soon', 'number of seconds')):
        with pytest.raises(ValueError, match=word):
            VS.take_in_point(GUIDE, JOB, bad)


# ---------- the editor's package, made before the assembly ----------

def vis(in_s=None, duration=7.0):
    v = copy.deepcopy(T115.VIS)
    take = next(s for s in v['summary']['shots'] if s['shot_id'] == 'VS1')
    take['media'] = {'kind': 'movie', 'duration_s': duration, **({'in_s': in_s} if in_s is not None else {})}
    return v


def take_event(v):
    return E.events_of(T115.PLAN, T115.PK, [v], T115.CLIPS)[0][1]


def test_the_early_package_places_the_take_from_its_in_point_for_its_slot():
    ev = take_event(vis(in_s=1.2))   # a 2 s slot (50 frames at 25) inside a 7 s take
    assert (ev['source_in_frame'], ev['source_out_frame']) == (30, 80) and 'hold the last frame' not in ev['marker']['note'] and ev['source_frames'] == 175
    assert (take_event(vis())['source_in_frame'], take_event(vis())['source_out_frame']) == (0, 50)   # no point recorded: its first frame, as before


def test_a_take_too_short_after_its_in_point_says_the_last_frame_is_held():
    ev = take_event(vis(in_s=1.0, duration=2.4))   # 35 frames left for a 50-frame slot
    assert (ev['source_in_frame'], ev['source_out_frame']) == (25, 60) and 'shorter than its slot: hold the last frame' in ev['marker']['note']


def test_an_ai_take_is_declared_without_sound_in_the_timeline_and_a_camera_file_keeps_its_sound():
    assert take_event(vis())['silent'] is True
    events, _ = E.events_of(T115.PLAN, T115.PK, [vis(in_s=1.2)], T115.CLIPS)
    assert 'silent' not in events[0] and 'silent' not in events[2]   # the camera cut and the picture
    xml = TL.fcpxml('VW-20', T115.PK['timeline'], events, [], [], [], 300, reference=False)
    xml = xml.decode('utf-8') if isinstance(xml, bytes) else xml
    assert _attr(xml, 'VS1.mp4', 'hasAudio') == '0' and _attr(xml, 'C0120.MP4', 'hasAudio') == '1'


def _attr(xml, name, attr):
    import re
    tag = re.search(r'<asset [^>]*name="%s"[^>]*>' % re.escape(name), xml).group(0)
    return re.search(r'%s="([^"]*)"' % attr, tag).group(1)


def test_the_package_notes_say_how_an_ai_take_is_placed_and_what_the_editor_may_do():
    text = E.open_edit_text('VW-20')
    assert 'without its own sound' in text and '1.15 times, never above 1.2' in text and 'light, or none' in text and 'patched frame by frame' in text


# ---------- the assembly ----------

PK25 = {'timeline': {'fps': '25'}}


def test_the_assemblys_default_start_is_the_in_point_in_film_frames():
    assert A.in_frames({'kind': 'movie', 'in_s': 1.2}, PK25, 175) == 30
    assert A.in_frames({'kind': 'movie'}, PK25, 175) == 0 and A.in_frames(None, PK25, None) == 0
    assert A.in_frames({'kind': 'movie', 'in_s': 99}, PK25, 175) == 174   # never past the take


def test_a_take_at_another_rate_than_the_film_is_said_to_the_operator():
    assert A.rate_note({'kind': 'movie', 'fps': '24'}, PK25) == "the take is 24 frames a second and the film 25: 1 frames in every second are repeated; a film at the take's rate avoids it"
    assert 'are repeated' in A.rate_note({'kind': 'movie', 'fps': '24'}, {'timeline': {'fps': '30'}}) and '6 frames' in A.rate_note({'kind': 'movie', 'fps': '24'}, {'timeline': {'fps': '30'}})
    assert A.rate_note({'kind': 'movie', 'fps': '25'}, PK25) == '' and A.rate_note({'kind': 'still'}, PK25) == '' and 'dropped' in A.rate_note({'kind': 'movie', 'fps': '30'}, PK25)


def test_the_offset_is_film_frames_and_becomes_the_takes_own_frames_once():
    """30 film frames at 25 a second is 1.2 s; in a 24-frame take that is frame 28 (it was used as frame 30, 0.05 s late)."""
    src = int(Fraction(30) * Fraction('24') / Fraction('25'))
    assert src == 28
    import inspect
    code = inspect.getsource(A.render)
    assert "src_in = int(Fraction(ev.get('offset_frames', 0)) * Fraction(str(fps)) / Fraction(str(pk['timeline']['fps'])))" in code and "'source_in_frame': src_in" in code
