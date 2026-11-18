"""design/218b (SK, 18 Nov 2026): a part seen from another direction or at another scale is the same part. Each drawing follows its own
approved spec and view; the assistant does not ask, makes the change of view readable and records one plain line (`vw motion note`), kept
beside the plan, carried in the brief of each drawing it names and shown under Details on their page lines. Only two approved specs that
truly contradict are asked. No new refusal on an upload or a verdict. Without a database."""
import json
import sys
from pathlib import Path

import pytest

from app import pictures as P, visuals_stage as VS
from test_design130_p1_pure import MRUN, motion_store

ROOT = Path(__file__).resolve().parents[2]
USER = {'id': 'u1', 'name': 'Claude'}
LINE = 'The steel is shown from the side in MO0 and cut across here.'


def plan(*ids):
    return {'gaps': [{'gap_id': 'G1', 'scenes': [{'id': 'SC1', 'shots': [{'id': i, 'visual_type': 'drawn'} for i in ids] + [{'id': 'F1', 'visual_type': 'footage'}]}]}]}


def test_a_note_is_recorded_once_for_the_drawings_it_names():
    s = {}
    row = VS.drawing_note(s, plan('D1', 'D2'), USER, ['D1', 'D2'], LINE)
    assert s['drawing_notes'] == [row] and row['shots'] == ['D1', 'D2'] and row['text'] == LINE and row['by'] == 'claude'
    assert VS.drawing_note(s, plan('D1', 'D2'), USER, ['D2', 'D1'], f'  {LINE} ') is row and len(s['drawing_notes']) == 1   # the same line again: one record
    for shots, text, word in ((['F1'], LINE, 'F1'), ([], LINE, 'drawn shot'), (['D1'], ' ', 'one plain line'), (['D1'], 'x' * 301, '300')):
        with pytest.raises(ValueError) as e:
            VS.drawing_note(s, plan('D1', 'D2'), USER, shots, text)
        assert word in str(e.value)


def test_the_note_is_shown_under_details_on_each_drawing_it_names():
    s = {}
    VS.drawing_note(s, plan('D1', 'D2'), USER, ['D2'], LINE)
    assert P.drawing_notes(s, 'D2') == [LINE] and P.drawing_notes(s, 'D1') == []
    assert "['Notes', drawing_notes(session, shot_id, plan)]" in Path(P.__file__).read_text(encoding='utf-8')


def test_the_brief_of_a_later_drawing_carries_the_note():
    store = motion_store()
    before = VS.motion_brief(store, MRUN, [], 'MO1')['brief']
    assert LINE not in before
    s = VS.session_of(store, MRUN, [])
    VS.drawing_note(s, VS.current_plan(store, s), USER, ['MO1'], LINE)
    VS.save_session(store, MRUN, s)
    brief = VS.motion_brief(store, MRUN, [], 'MO1')['brief']
    assert f'Note on the view (the spec above wins where they differ): {LINE}' in brief and 'Recorded for this drawing' not in brief
    assert brief.index('Drawing spec, view') < brief.index('Note on the view')   # the note sits below the spec


def test_a_spec_without_a_view_says_so_in_the_brief():
    assert VS.view_words({'view': 'cutaway'}) == 'cutaway'
    assert VS.view_words({}) == VS.VIEW_UNSTATED and 'the spec does not state the view' in VS.VIEW_UNSTATED
    assert 'view_words(spec)' in Path(VS.__file__).read_text(encoding='utf-8')


def test_nothing_new_refuses_an_upload_or_a_verdict():
    src = Path(VS.__file__).read_text(encoding='utf-8')
    for fn in ('def set_motion(', 'def motion_verdict('):
        body = src[src.index(fn):src.index('\ndef ', src.index(fn) + 5)]
        assert 'drawing_notes' not in body and 'view_words' not in body, fn


def test_the_texts_say_a_view_is_not_a_change_of_shape_and_never_asked():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d218b_wording_v3 as W
    stage = next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
    part = {p['name']: p['text'] for p in stage['parts']}
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    before = W.before(stage)
    for where, old, new in W.PAIRS:
        assert part[where].count(new) == 1 and next(p['text'] for p in before['parts'] if p['name'] == where).count(old) == 1
    assert '`vw motion note --shot' in part['later'] and 'truly contradict' in part['later'] and 'is not redrawn to match another view' in part['later']
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').count(new) == 1, file
    rules = (ROOT / 'plugin' / 'agents' / 'vw-motion-rules.md').read_text(encoding='utf-8')
    assert 'the steel is the same bars as in drawing D1, here seen cut across' in rules and 'never "the steel looks as in drawing D1"' in rules
    assert 'its stated view' in (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert 'never a part that morphs' in (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('d218(prompt, parts)') < split.index('d218b(prompt, parts)')


def test_a_note_is_withdrawn_for_one_drawing_and_deleted_with_its_last():
    s = {}
    VS.drawing_note(s, plan('D1', 'D2'), USER, ['D1', 'D2'], LINE)
    VS.withdraw_note(s, ['D2'], f' {LINE}')
    assert s['drawing_notes'][0]['shots'] == ['D1']
    VS.withdraw_note(s, ['D1'], LINE)
    assert s['drawing_notes'] == []
    with pytest.raises(ValueError) as e:
        VS.withdraw_note(s, ['D1'], LINE)
    assert 'No note on D1 reads' in str(e.value)


def test_notes_and_colours_of_a_shot_no_longer_drawn_in_the_plan_are_skipped():
    s = {}
    VS.drawing_note(s, plan('D1', 'D2'), USER, ['D2'], LINE)
    VS.added_colour(s, plan('D1', 'D2'), USER, 'walls', '#5A524C', 'dark warm grey', 'the palette named none', ['D2'], '')
    now = plan('D1')   # a revision took D2 out
    assert P.drawing_notes(s, 'D2', now) == [] and P.colour_notes(s, 'D2', now) == []
    assert P.drawing_notes(s, 'D2', plan('D2')) == [LINE] and P.colour_notes(s, 'D2', plan('D2'))
    assert 'walls' not in VS.palette_line(now, s) and 'walls #5A524C' in VS.palette_line(plan('D2'), s)
    assert '(the spec wins where they differ)' in VS.palette_line(plan('D2'), s)
    src = Path(P.__file__).read_text(encoding='utf-8')
    assert 'drawing_notes(session, shot_id, plan)' in src and 'colour_notes(session, shot_id, plan)' in src


def test_the_texts_say_the_spec_wins_and_how_a_note_is_withdrawn():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d218b_wording_v3 as W
    later = next(p['text'] for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals'
                 for p in s['parts'] if p['name'] == 'later')
    assert later.count(W.VIEW) == 1 and 'below their spec, which wins where they differ' in W.VIEW and '--remove' in W.VIEW
    assert 'the spec wins where they differ' in (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'its drawing spec wins' in (ROOT / 'plugin' / 'agents' / 'vw-motion-shot.md').read_text(encoding='utf-8')
