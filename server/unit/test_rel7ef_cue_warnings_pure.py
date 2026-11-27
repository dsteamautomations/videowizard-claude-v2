"""Release 1 of 27 Nov 2026, phase 3, parts E and F (SK approved; E: under 0.5 s).

E (6.12): a part keyed to a word 0.04 s before its shot's end was asked of the operator. Now the plan check warns of a cue that leaves under
0.5 s, and tells the assistant to move it itself. F (6.9): a cue word said twice in its shot is keyed to the first time; the render's check
then failed a part meant for the second. Now the plan check warns with both seconds, and the brief's Cues line shows the second each cue
resolves to. Each test failed first. Without a database."""
from app import drawn, visual_contract as VC, visuals_stage as VS
from test_design130_p1_pure import motion_store
from test_design221_p1_pure import NEW, edit_plan, edit_session

SAID = [('the', 0), ('slab', 32), ('rests', 50), ('on', 60), ('the', 70), ('beams', 80), ('and', 100), ('the', 110), ('slab', 154), ('aggregates', 188)]   # frames at 25 fps; the shot is 200 frames = 8 s


def film(cues, timed=True, words=SAID, end=200):
    shot = {'id': 'MO1', 'visual_type': 'drawn', 'start_frame': 0, 'end_frame': end, 'narration': ' '.join(w for w, _ in words), 'scene_motion': {'cues': cues}}
    session = {'source': {'fps': 25, 'gaps': {'g1': {'timing': {'words': [{'text': w, 'start_frame': f} for w, f in words]}} if timed else {}}}}
    return session, {'gaps': [{'gap_id': 'g1', 'scenes': [{'id': 's1', 'shots': [shot]}]}]}


def kinds(cues, **more):
    return [(w['kind'], w['shot_id'], w['message']) for w in VS.cue_warnings(*film(cues, **more))]


# ---------- E ----------

def test_a_cue_inside_the_last_half_second_warns_and_names_the_shot_the_part_and_the_seconds_left():
    (kind, shot, said), = kinds([{'selector': '#aggregates', 'word': 'aggregates'}])   # 7.52 s of 8 s
    assert (kind, shot) == ('cue_late', 'MO1')
    assert said == ('shot MO1: #aggregates appears 0.48 s before the shot ends, too late to be seen. Move it earlier yourself (an earlier word, or a second) '
                    'and tell the operator in one line what you moved. Do not ask them.')
    assert [k for k, _, _ in kinds([{'selector': '#late', 'at_s': 7.9}])] == ['cue_late']   # a second is judged the same


def test_a_cue_with_more_time_left_or_at_second_zero_does_not_warn():
    assert kinds([{'selector': '#beams', 'word': 'beams'}]) == []
    assert kinds([{'selector': '#a', 'at_s': 7.4}]) == [] and kinds([{'selector': '#a', 'at_s': 7.5}]) == []   # 0.6 s and exactly 0.5 s left
    assert kinds([{'selector': '#a', 'at_s': 0}]) == []
    assert kinds([{'selector': '#a', 'at_s': 0}], end=10) == []   # a shot shorter than 0.5 s: second 0 is free of it
    assert [k for k, _, _ in kinds([{'selector': '#a', 'at_s': 0.2}], end=10)] == ['cue_late']


def test_a_word_cue_on_a_film_with_no_timed_narration_is_not_called_late():
    assert kinds([{'selector': '#aggregates', 'word': 'aggregates'}], timed=False) == []


# ---------- F ----------

def test_a_word_said_twice_warns_with_both_seconds():
    (kind, shot, said), = kinds([{'selector': '#slab', 'word': 'slab'}])
    assert (kind, shot) == ('cue_twice', 'MO1')
    assert said == ("shot MO1: the word 'slab' is said twice in this shot, at 1.28 s and at 6.16 s. The cue of #slab is keyed to the first. "
                    'If it belongs to a later one, give a longer phrase that is said only there, or a second.')


def test_a_longer_phrase_a_second_or_a_word_said_once_does_not_warn():
    session, plan = film([{'selector': '#slab', 'word': 'and the slab'}])
    assert VS.cue_warnings(session, plan) == []
    assert drawn.cue_seconds({'actions': [{'word': 'and the slab'}]}, plan['gaps'][0]['scenes'][0]['shots'][0], session['source']['gaps']['g1']['timing']['words'], 25) == [4.0]   # its own place
    assert kinds([{'selector': '#slab', 'at_s': 6.1}]) == [] and kinds([{'selector': '#beams', 'word': 'beams'}]) == []


def test_a_phrase_said_twice_warns_too_and_a_word_of_the_next_shot_does_not_count():
    assert [k for k, _, _ in kinds([{'selector': '#slab', 'word': 'the slab'}])] == ['cue_twice']
    assert kinds([{'selector': '#slab', 'word': 'slab'}], end=150) == []   # the second "slab" is said after this shot


def test_with_no_timed_narration_the_warning_is_raised_from_the_text_without_seconds():
    (kind, _, said), = kinds([{'selector': '#slab', 'word': 'slab'}], timed=False)
    assert kind == 'cue_twice' and "the word 'slab' is said twice in this shot. The cue of #slab" in said


def test_a_late_cue_that_is_also_said_twice_gets_both_warnings():
    words = [('slab', 0), ('and', 100), ('slab', 190)]
    assert [k for k, _, _ in kinds([{'selector': '#x', 'word': 'slab'}], words=words)] == ['cue_twice']   # the first time, second 0, is not late
    words = [('the', 0), ('slab', 190), ('slab', 195)]
    assert sorted(k for k, _, _ in kinds([{'selector': '#x', 'word': 'slab'}], words=words)) == ['cue_late', 'cue_twice']


def test_both_kinds_are_warnings_the_plan_can_answer():
    assert {'cue_late', 'cue_twice'} <= set(VC.WARNING_TECHNICAL)


def test_the_briefs_cue_line_shows_the_second_each_cue_resolves_to():
    store, got = motion_store(), {}
    edit_plan(store, lambda d: got.update(gap=d['gaps'][0]['gap_id'], shot=d['gaps'][0]['scenes'][0]['shots'][0]))
    at = got['shot']['start_frame'] + 30
    edit_session(store, lambda s: s['source']['gaps'].setdefault(got['gap'], {}).update(timing={'words': [{'text': 'solid', 'start_frame': at}]}))
    edit_session(store, lambda s: got.update(fps=s['source']['fps']))
    t = drawn.cue_seconds({'actions': [{'word': 'solid'}]}, got['shot'], [{'text': 'solid', 'start_frame': at}], got['fps'])[0]
    assert f'#label at the word "solid" ({t:g} s).' in VS.motion_brief(store, NEW, [], 'MO1')['brief']
