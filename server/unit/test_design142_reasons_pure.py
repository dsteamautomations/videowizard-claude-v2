"""design/142 R2 (SK, 2 Nov 2026, Revathi's point 2): the first cut carries its own reasons. Every blank names the clips considered and why each was turned
down (or none_fit); every shot with alternatives says why it was preferred; the package lists the sub-clips the analysis ruled out, with its reason."""
from app.stage2 import validator as V

ROWS = {'c1:S1': {'clip_id': 'c1'}, 'c2:S1': {'clip_id': 'c2'}}


def cut(*events):
    return {'options': [{'option_number': 1, 'beat_id': 'BEAT_01', 'events': list(events)}]}


def blank(**kw):
    return {'blank': True, 'timeline_frames': 50, 'intent': 'the idea', **kw}


def test_a_blank_without_its_reasons_is_refused():
    r = V.cut_reasons(cut(blank()), ROWS)
    assert len(r) == 1 and 'considered' in r[0] and 'none_fit' in r[0]


def test_a_blank_with_considered_clips_or_none_fit_passes():
    assert V.cut_reasons(cut(blank(considered=[{'sub_clip_id': 'c1:S1', 'why': 'wrong action'}])), ROWS) == []
    assert V.cut_reasons(cut(blank(none_fit='no clip shows the ceiling from below')), ROWS) == []


def test_a_reason_must_be_one_of_the_kinds_and_other_needs_words():
    assert 'why' in V.cut_reasons(cut(blank(considered=[{'sub_clip_id': 'c1:S1', 'why': 'meh'}])), ROWS)[0]
    assert V.cut_reasons(cut(blank(considered=[{'sub_clip_id': 'c1:S1', 'why': 'other'}])), ROWS)
    assert V.cut_reasons(cut(blank(considered=[{'sub_clip_id': 'c1:S1', 'why': 'other', 'words': 'the mason looks at the lens'}])), ROWS) == []


def test_an_unknown_clip_is_refused():
    assert 'unknown' in V.cut_reasons(cut(blank(considered=[{'sub_clip_id': 'zz:S9', 'why': 'too short'}])), ROWS)[0]


def test_a_shot_with_alternatives_says_why_it_won():
    shot = {'sub_clip_id': 'c1:S1', 'alternatives': [{'sub_clip_id': 'c2:S1'}]}
    assert 'preferred_because' in V.cut_reasons(cut(shot), ROWS)[0]
    assert V.cut_reasons(cut({**shot, 'preferred_because': 'the whole tile laid, not only lifted'}), ROWS) == []


def test_the_package_lists_the_sub_clips_ruled_out_with_the_reason():
    rows = [{'sub_clip_id': 'c1:S1', 'clip_name': 'c1.mp4', 'eligibility': 'ELIGIBLE', 'ruled_out_reason': None},
            {'sub_clip_id': 'c1:S2', 'clip_name': 'c1.mp4', 'eligibility': 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT', 'ruled_out_reason': 'crop zone is not sharp'}]
    from app.stage2 import package as P
    assert P.ruled_out(rows) == [{'sub_clip_id': 'c1:S2', 'clip': 'c1.mp4', 'eligibility': 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT', 'reason': 'crop zone is not sharp'}]


# ---------- R3: "stays visible" by word and by meaning (design/140 Q1; Revathi's point 6) ----------

def test_spaces_underscores_and_hyphens_count_as_the_same():
    assert V.carried(['steel bars'], ['reinforcement_steel_bars']) and V.carried(['wet-concrete'], ['wet_concrete_slurry'])
    assert not V.carried(['rebar'], ['reinforcement_steel_bars'])


def test_the_flag_is_answered_by_a_reason_and_stays_without_one():
    assert V.carry_flag('steel bars', {'sub_clip_id': 'a'}, ['reinforcement_steel_bars']) is False
    assert V.carry_flag('rebar', {'sub_clip_id': 'a', 'carries_over_seen': 'reinforcement_steel_bars is the rebar'}, ['reinforcement_steel_bars']) is False
    assert V.carry_flag('rebar', {'sub_clip_id': 'a'}, ['reinforcement_steel_bars']) is True
    assert V.carry_flag('rebar', {'blank': True}, []) is False
