"""SK, 23 Nov 2026 (no-footage release 1d): the visuals stage of a film with no clip at all (no camera footage of its own and no library
clip in its first cut). Nothing about footage is said, measured or accepted on such a film: no footage line, no footage shot, no scene that
"continues the footage", no rule that waits for a footage frame, and no guidebook about matching real neighbours. A film with clips behaves
as before. One addition holds for every film: the treatment says when its estimate is above the film's cost limit."""
import json
from pathlib import Path

import pytest

from app import chat_flow as CF, core, footage as FM, library, ref_sets, visuals_stage as VS

SERVER = Path(__file__).resolve().parents[1]
VISUALS = next(s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
CLIP = {'id': 'c1', 'name': 'c1.mp4', 'width': 1920, 'height': 1080, 'fps': 25}


def session(clips=(), events=(), **more):
    measured = FM.measure(list(clips), {})
    return {'footage_measured': measured, 'footage': FM.apply_correction(measured, more.get('footage_correction')), 'first_cut_events': list(events), **more}


NONE, OWN, LIBRARY = session(), session([CLIP]), session(events=[{'sub_clip_id': 'lib:S1'}])


def test_a_film_has_no_clip_only_when_it_has_neither_its_own_nor_a_library_clip_in_its_cut():
    assert VS.no_real_clip(NONE) and not VS.no_real_clip(OWN) and not VS.no_real_clip(LIBRARY)
    assert not VS.no_real_clip({}) and not VS.no_real_clip({'first_cut_events': []})   # a session not prepared yet: not known, so nothing changes


def test_no_footage_line_is_said_when_nothing_was_measured():
    assert VS.footage_view(NONE) is None and VS.footage_view(LIBRARY) is None
    assert VS.footage_view(OWN)['line'].startswith('Your footage: ')
    said = session(footage_correction={'camera': 'phone', 'quote': 'shot on a phone'})   # a correction recorded before this release still shows
    assert VS.footage_view(said) is not None


def test_the_footage_line_cannot_be_corrected_on_a_film_with_no_clip(monkeypatch):
    monkeypatch.setattr(VS, 'session_of', lambda store, run, outputs=None, **k: NONE)
    with pytest.raises(ValueError) as e:   # `need`: the route turns it into the refusal the operator reads
        VS.correct_footage(None, {'id': 'u'}, {'id': 'r'}, [], {'camera': 'phone'}, 'it was a phone')
    assert 'no camera footage' in str(e.value)


def plan(route='footage', continues=False):
    return {'gaps': [{'gap_id': 'G1', 'scenes': [{'id': 'S1', 'continues_footage': continues, 'shots': [{'id': 'G1-a', 'visual_type': route}, {'id': 'G1-b', 'visual_type': 'image'}]}]}]}


def test_a_footage_shot_and_a_scene_that_continues_the_footage_are_refused_in_one_sentence_each():
    assert VS.no_clip_plan(OWN, plan('footage', True)) == [] and VS.no_clip_plan(LIBRARY, plan('footage', True)) == [] and VS.no_clip_plan(NONE, plan('image')) == []
    out = VS.no_clip_plan(NONE, plan('footage', True))
    assert len(out) == 2 and 'G1-a' in out[0] and 'no clip' in out[0] and 'S1' in out[1] and 'continues_footage' in out[1]
    assert VS.no_clip_routes(NONE, 'G1', ['still', 'footage']) and not VS.no_clip_routes(NONE, 'G1', ['still', 'video']) and not VS.no_clip_routes(OWN, 'G1', ['footage'])


def test_no_rule_waits_for_a_footage_frame_that_cannot_exist():
    assert VS.footage_frame_needed(NONE, 'the client drawing, seen in the footage', []) is False   # F13
    assert VS.footage_frame_needed(OWN, 'seen in the footage', []) is True and VS.footage_frame_needed(OWN, 'seen in the footage', [{'id': 'f1'}]) is False
    assert VS.footage_frame_needed(OWN, '', []) is False
    exact = {'identity': 'exact'}
    assert ref_sets.exact_doubt(exact, 'set', none=False) and not ref_sets.exact_doubt(exact, 'footage', none=False)   # N3: as before
    assert not ref_sets.exact_doubt(exact, 'set', none=True) and not ref_sets.exact_doubt({'identity': 'similar'}, 'set', none=False)


def test_the_guidebook_about_real_neighbours_is_not_handed_out():
    version = library.latest()
    own, none = library.steps(version), library.steps(version, footage='none')
    gap_fill = 'library/video/gap-fill.md'
    assert any(f['path'] == gap_fill for f in own['steps']['take']['files']) and 'frame' in own['steps']
    assert 'frame' not in none['steps'] and all(f['path'] != gap_fill for s in none['steps'].values() for f in s['files'])
    assert library.steps(version, footage='own') == own
    for step in ('still-scene', 'start', 'end', 'take'):
        assert gap_fill in library.step_files(step) and gap_fill not in library.step_files(step, footage='none')
        assert [p for p in library.step_files(step) if p != gap_fill] == library.step_files(step, footage='none')


def test_the_treatment_says_when_its_estimate_is_above_the_limit():
    assert VS.over_limit(2100.0, 300.0, 2250.0) == [{'kind': 'over_limit', 'message': VS.OVER_LIMIT.format(estimate='2,400', cap='2,250')}]
    assert VS.over_limit(1000.0, 300.0, 2250.0) == [] and VS.over_limit(2250.0, 0.0, 2250.0) == []
    assert '`vw visuals cap`' in VS.OVER_LIMIT and 'owner' in VS.OVER_LIMIT


def test_the_round_never_tells_such_a_film_what_its_footage_lacks():
    said = [CF.WORDS['auto'], CF.WORDS['auto_people'], 'Kiln: your footage has no picture of it. Have a reference set made (paid)?', 'Your footage has no picture of this person. A yes has a set made.']
    for text in said:   # F12
        assert 'footage' not in CF.no_clip_words(NONE, text) and CF.no_clip_words(OWN, text) == text and CF.no_clip_words(LIBRARY, text) == text
    assert CF.no_clip_words(NONE, said[2]) == 'Kiln: Have a reference set made (paid)?'
    assert CF.no_clip_words(NONE, CF.WORDS['auto']).startswith('A set will be made from the description')

FOOTAGE_WORDS = ('vw visuals footage', 'vw visuals frame', 'vw visuals digest', 'vw visuals trial', 'vw-reference-finder', 'continues_footage: true', 'footage first', 'the footage line',
                 'measured footage', 'neighbouring footage', 'footage beside', 'retained footage', 'footage pictures', 'footage frame', 'real footage', 'per clip', 'from the clips',
                 'its footage', 'the footage shows', 'in the footage', 'footage clip')


def test_the_visuals_instructions_of_a_film_with_no_footage_do_not_speak_of_footage():
    st = core.for_footage(VISUALS, 'none')
    text = json.dumps({k: st.get(k) for k in ('prompt', 'steps', 'parts')}, ensure_ascii=False).lower().replace('no camera footage', '').replace('no footage', '')
    assert [w for w in FOOTAGE_WORDS if w in text] == []
    assert text.count('footage') == 0, [text[max(0, i - 80):i + 60] for i in range(len(text)) if text.startswith('footage', i)][:12]


def test_the_visuals_instructions_tell_such_a_film_where_its_look_and_its_real_pictures_come_from():
    st = core.for_footage(VISUALS, 'none')
    text = json.dumps({k: st.get(k) for k in ('prompt', 'steps', 'parts')}, ensure_ascii=False)
    assert "the Direction's look" in text or "the direction's look" in text
    assert '`vw visuals own`' in text or 'Upload my own' in text   # the operator's own photographs come in at the references
