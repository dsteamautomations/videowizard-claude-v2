"""design/218 A and B (SK, 18 Nov 2026): the operator is not asked what needs no answer. A neutral colour the film's palette does not name is
chosen by Claude, recorded once per thing with its reason (beside the plan, never in it), given to every later drawing's brief and shown under
Details on the drawn graphic's line; a hue, or a second colour for the same thing, needs the operator's words. B: the plan check warns of a
thing two drawn shots show with no colour in the palette. Without a database."""
import pytest

from app import pictures as P, visual_contract as VC, visuals_stage as V

USER = {'id': 'u1', 'name': 'Claude'}


def plan(*shots, palette='navy #12324A, orange #FF8800, concrete mid grey #8A8A8A'):
    return {'foundation': {'graphic_style': {'palette': palette}}, 'gaps': [{'gap_id': 'G01', 'scenes': [{'id': 'SC1', 'shots': list(shots)}]}]}


def drawn(sid, parts=()):
    return {'id': sid, 'visual_type': 'drawn', 'drawing_spec': {'parts': list(parts)}}


def add(session, p, colour='#5A524C', thing='walls', quote='', shots=('D1',)):
    return V.added_colour(session, p, USER, thing, colour, 'dark warm grey', 'the palette named none', list(shots), quote)


def test_a_neutral_colour_is_recorded_once_beside_the_plan_with_its_reason():
    s, p = {}, plan(drawn('D1'), drawn('D2'))
    row = add(s, p)
    assert s['added_colours']['walls'] == row and row['colour'] == '#5A524C' and row['by'] == 'claude' and row['shots'] == ['D1']
    assert 'walls' not in str(p)   # the accepted plan is never changed (its gaps stay accepted)
    again = add(s, p, shots=('D2',))   # the same colour again: one record, the shot added
    assert again['shots'] == ['D1', 'D2'] and len(s['added_colours']) == 1
    assert add(s, p, thing='  Walls ')['colour'] == '#5A524C'   # the thing's name is matched without case or spaces


def test_neutral_is_measured_by_chroma_with_a_named_threshold():
    assert V.NEUTRAL_MAX_CHROMA == 0.10
    for c in ('#5A524C', '#F5F0E6', '#2B2522', '#8A8A8A', '#FFFFFF'):
        assert V.chroma(c) <= V.NEUTRAL_MAX_CHROMA, c
    for c in ('#A0522D', '#12324A', '#FF8800'):
        assert V.chroma(c) > V.NEUTRAL_MAX_CHROMA, c


def test_a_hue_needs_the_operators_words():
    s, p = {}, plan(drawn('D1'))
    with pytest.raises(ValueError) as e:
        add(s, p, colour='#A0522D')
    assert 'not a neutral' in str(e.value) and '0.10' in str(e.value) and 'ask the operator' in str(e.value)
    row = add(s, p, colour='#A0522D', quote='Use a brick red for the walls.')
    assert row['by'] == 'operator' and row['quote'] == 'Use a brick red for the walls.'


def test_a_second_colour_for_the_same_thing_is_refused_unless_the_operator_says_so():
    s, p = {}, plan(drawn('D1'))
    add(s, p)
    with pytest.raises(ValueError) as e:
        add(s, p, colour='#8A8A8A')
    assert '#5A524C' in str(e.value) and 'stands' in str(e.value)
    assert add(s, p, colour='#8A8A8A', quote='Make the walls mid grey.')['colour'] == '#8A8A8A'


def test_bad_input_is_refused_by_name():
    s, p = {}, plan(drawn('D1'), {'id': 'F1', 'visual_type': 'footage'})
    for kw, word in (({'colour': 'grey'}, '#RRGGBB'), ({'shots': ()}, 'drawn shot'), ({'shots': ('F1',)}, 'F1'), ({'thing': ' '}, 'thing')):
        with pytest.raises(ValueError) as e:
            add(s, p, **kw)
        assert word in str(e.value), kw
    with pytest.raises(ValueError):
        V.added_colour(s, p, USER, 'walls', '#5A524C', 'dark warm grey', '', ['D1'], '')   # no reason


def test_every_later_brief_gets_the_plans_palette_and_the_added_colours():
    s, p = {}, plan(drawn('D1'))
    assert V.palette_line(p, s) == 'Palette: navy #12324A, orange #FF8800, concrete mid grey #8A8A8A.'
    add(s, p)
    assert V.palette_line(p, s) == ('Palette: navy #12324A, orange #FF8800, concrete mid grey #8A8A8A. Added for every drawing of this film: '
                                     'walls #5A524C (dark warm grey).')
    assert 'palette_line(plan, session)' in open(V.__file__, encoding='utf-8').read()   # motion_brief's palette line is this one


def test_the_drawn_line_shows_it_under_details_without_asking(monkeypatch):
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    s, p = {'references': {}, 'source': {'gaps': {}}}, plan(drawn('D1'))
    add(s, p)
    assert P.colour_notes(s, 'D1') == ['Added by Claude: dark warm grey for the walls, because the palette named none.']
    assert P.colour_notes(s, 'D9') == []
    src = open(P.__file__, encoding='utf-8').read()
    assert "['Colours', colour_notes(session, shot_id)]" in src


# ---------- B: the cause, earlier ----------

def _b_plan(palette='navy #12324A, orange #FF8800, concrete slabs mid grey #8A8A8A'):
    spec = lambda *parts: {'parts': list(parts)}
    return {'foundation': {'graphic_style': {'palette': palette} if palette else None},
            'gaps': [{'gap_id': 'G01', 'scenes': [{'id': 'SC1', 'shots': [{'id': 'D1', 'visual_type': 'drawn', 'drawing_spec': spec('Slab', 'Brick walls', 'Lintel')},
                                                                          {'id': 'D2', 'visual_type': 'drawn', 'drawing_spec': spec('slabs', 'Wall')},
                                                                          {'id': 'D3', 'visual_type': 'drawn', 'drawing_spec': spec('Lintel')},
                                                                          {'id': 'F1', 'visual_type': 'footage'}]}]}]}


def test_the_plan_warns_of_a_thing_two_drawn_shots_show_with_no_colour_in_the_palette():
    w = VC.palette_warnings(_b_plan())
    assert [x['kind'] for x in w] == ['palette_missing', 'palette_missing']
    assert 'brick walls' in w[0]['message'].lower() and 'D1' in w[0]['message'] and 'D2' in w[0]['message']   # "Brick walls" and "Wall" are one thing
    assert 'lintel' in w[1]['message'].lower()   # two drawn shots show it
    assert all('slab' not in x['message'].lower() for x in w)   # the palette names the slabs
    assert 'before the operator approves the plan' in w[0]['message']
    assert 'palette_missing' in VC.WARNING_TECHNICAL
    assert VC.palette_warnings(_b_plan('navy, orange, slabs mid grey, walls dark warm grey, lintel near black')) == []
    assert VC.palette_warnings(_b_plan(None)) == []   # no palette at all is the style_missing warning's, not this one's


def test_a_part_with_a_recorded_colour_is_never_named():
    added = {'walls': {'thing': 'walls', 'colour': '#5A524C'}}
    w = VC.palette_warnings(_b_plan(), added)
    assert len(w) == 1 and 'lintel' in w[0]['message'].lower()


def test_the_warning_is_raised_only_while_no_gap_was_ever_accepted():
    p = _b_plan()
    assert [x['kind'] for x in V.palette_due({'accepted': {}}, p)] == ['palette_missing', 'palette_missing']
    assert V.palette_due({'accepted': {'G01': {'digest': 'd'}}}, p) == []   # an approved plan with specs: never (its palette is not edited)
    assert V.palette_due({'accepted': {}, 'shared_pending': {'G01': {}}}, p) == []
    assert V.palette_due({'accepted': {}, 'added_colours': {'lintel': {'thing': 'lintel'}, 'walls': {'thing': 'walls'}}}, p) == []
    src = open(V.__file__, encoding='utf-8').read()
    assert 'palette_due(session, plan)' in src and 'palette_warnings(plan)' not in open(VC.__file__, encoding='utf-8').read()


def test_the_texts_say_claude_chooses_a_missing_neutral_and_the_operator_only_a_hue():
    import json
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'scripts'))
    import d218_wording_v3 as W
    later = next(p['text'] for s in json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals'
                 for p in s['parts'] if p['name'] == 'later')
    assert later.count(W.COLOUR) == 1 and '`vw motion colour --shot D1,D2' in later
    for file, old, new in W.HELPERS:
        text = (root / 'plugin' / file).read_text(encoding='utf-8')
        assert text.count(new) == 1, file
    assert 'Colours to add' in (root / 'plugin' / 'agents' / 'vw-motion-rules.md').read_text(encoding='utf-8')
    assert 'never stop to ask' in (root / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
