"""design/105, Release 7 (course E-b, E-c; E-a as a note): the AI-shot list and the editor's table, written from the assembly and the visuals record."""
from app.stage3 import delivery as D

FPS = 25


def fill(sid, at_s, source, kind, graphic=False, secs=4):
    return {'kind': 'fill', 'gap_id': 'G1', 'shot_id': sid, 'source': source, 'media': {'kind': kind, 'graphic': graphic},
            'timeline_in_frame': at_s * FPS, 'timeline_frames': secs * FPS}


EVENTS = [{'kind': 'event', 'sub_clip_id': 'c1:1', 'timeline_in_frame': 0, 'timeline_frames': 250},
          fill('VS1', 10, 'take', 'movie'),          # AI video
          fill('IM1', 14, 'asset', 'still'),          # AI still
          fill('FR1', 18, 'asset', 'still'),          # a footage frame held as a still: not AI
          fill('AN1', 22, 'asset', 'sequence'),       # a graphic sequence
          fill('DG1', 26, 'asset', 'still', True),    # a drawn diagram
          fill('CL1', 30, 'clip', 'clip')]            # a stretch of an original clip: not AI

VIS = {'VS1': {'narration': 'It uses 25 % fewer bricks than a solid wall.', 'ambient': 'palm fronds sway; dust drifts'},
       'IM1': {'reference_kind': 'keyframe', 'check_lines': [{'check': 'light and colour', 'pass': False, 'seen': 'brighter by 0.20 than the footage beside it (3 frames)'},
                                                             {'check': 'fine detail', 'pass': False, 'seen': '0.52 of the fine detail of the footage beside it (3 frames)'},
                                                             {'check': 'nothing extra', 'pass': False, 'seen': 'a ladder at the right edge'}]},
       'FR1': {'reference_kind': 'frame'}}


# ---------- E-c ----------

def test_the_ai_shot_list_names_every_ai_shot_with_its_timecode_and_kind_and_leaves_footage_out():
    rows = D.ai_shots(EVENTS, FPS, VIS)
    assert [(r['shot_id'], r['kind'], r['timecode']) for r in rows] == [('VS1', 'AI video', '00:10'), ('IM1', 'AI still', '00:14'), ('AN1', 'graphic', '00:22'), ('DG1', 'graphic', '00:26')]
    md = D.ai_shots_md(rows)
    assert 'AI-generated or altered-content' in md and '## Graphics' in md and md.index('VS1') < md.index('## Graphics') < md.index('AN1')
    assert D.ai_shots([e for e in EVENTS if e['kind'] == 'event' or e['source'] == 'clip'], FPS, VIS) == []
    assert 'AI-shots.md' in D.open_edit_text({'code': 'VW-9'}, ai=True) and 'AI-shots.md' not in D.open_edit_text({'code': 'VW-9'})


# ---------- E-b ----------

def lines(events=EVENTS, vis=VIS, fmt=None):
    return D.editors_table(events, FPS, vis, fmt)


def test_each_rule_writes_its_line_when_its_trigger_is_there():
    got = {(r['rule'], r['shot']): r for r in lines()}
    assert 'palm fronds sway' in got[('E5', 'VS1')]['line'] and ('E5', 'IM1') in got and ('E5', 'AN1') not in got and ('E5', 'FR1') not in got
    assert "'25 %'" in got[('E6', 'VS1')]['line']
    assert 'brighter by 0.20' in got[('E7', 'IM1')]['line'] and '0.52' in got[('E8', 'IM1')]['line'] and 'a ladder at the right edge' in got[('E10', 'IM1')]['line']
    assert '1 AI take is 720p' in got[('E11', '')]['line'] and ('E16', '') in got and ('E13', '') in got and ('E15', '') in got
    assert got[('E7', 'IM1')]['where'] == '00:14' and got[('E7', 'IM1')]['kind'] == 'look' and got[('E5', 'VS1')]['kind'] == 'sound'


def test_a_rule_is_silent_without_its_trigger_and_the_once_lines_appear_once():
    rows = lines(vis={'VS1': {'narration': 'The wall stands.'}, 'IM1': {'reference_kind': 'keyframe', 'check_lines': [{'check': 'light and colour', 'pass': True}]}})
    rules = [r['rule'] for r in rows]
    assert 'E6' not in rules and 'E7' not in rules and 'E8' not in rules and 'E10' not in rules and 'E17' not in rules
    assert rules.count('E13') == 1 and rules.count('E15') == 1 and rules.count('E11') == 1 and rules.count('E16') == 1
    footage_only = [r['rule'] for r in lines(events=[e for e in EVENTS if e['kind'] == 'event' or e['source'] == 'clip'])]
    assert sorted(footage_only) == ['E13', 'E15']   # no AI shot: no AI lines


def test_a_vertical_or_social_film_gets_the_export_line():
    assert any(r['rule'] == 'E17' for r in lines(fmt={'frame': '9:16'}))
    assert any(r['rule'] == 'E17' for r in lines(fmt={'frame': '16:9', 'destinations': ['Instagram reels']}))
    assert not any(r['rule'] == 'E17' for r in lines(fmt={'frame': '16:9', 'destinations': ['the client website']}))


def test_the_table_is_written_grouped_by_kind_in_the_checklist():
    md = D.editors_table_md(lines())
    assert md.startswith("\n## Editor's table\n") and md.index('### Look') < md.index('### Sound') < md.index('### Finishing')
    assert '- [00:14] IM1: ' in md and '(E7)' in md


# ---------- the review's finding: a file the operator supplied (`vw visuals asset`) is not labelled AI ----------

def test_operator_supplied_files_are_listed_apart_and_get_no_ai_lines():
    events = EVENTS + [fill('HM1', 34, 'asset', 'movie'), fill('HS1', 38, 'asset', 'still')]
    vis = {**VIS, 'HM1': {'supplied': True}, 'HS1': {'supplied': True}}
    rows = D.ai_shots(events, FPS, vis)
    kinds = {r['shot_id']: r['kind'] for r in rows}
    assert kinds['HM1'] == kinds['HS1'] == 'supplied' and kinds['VS1'] == 'AI video'
    md = D.ai_shots_md(rows)
    assert '## Supplied by the operator' in md and 'check whether they were made with AI' in md
    assert md.index('## Supplied by the operator') < md.index('HM1') and 'HM1: AI' not in md
    assert not any(r['shot'] in ('HM1', 'HS1') for r in D.editors_table(events, FPS, vis))
    only = D.ai_shots([fill('HM1', 34, 'asset', 'movie')], FPS, {'HM1': {'supplied': True}})
    assert not D.has_ai(only) and D.has_ai(rows) and 'tick the platform' not in D.ai_shots_md(only) and 'tick the platform' in md   # a film of supplied files only: no "tick the AI option" line in OPEN-EDIT
