"""design/125 stage 7, builder C: the version 3 wording of the options, master, first-cut and visuals stages.
P2 labels; P7 one chapter a scene; P9 rule 3; P13 an AI-only scene is one blank; O7 two parts of one clip in a scene; O1-O3 scene numbers and
second choices; O4-O6 the second look by helpers; O9 the plan's named helper; P14 the first slide answer approves; the first-cut record retired.
Every stage's words the same or fewer (scripts/d125_stage7_wording_v3.py)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = {s['name']: s for s in json.loads((ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8'))['stages']}
V3 = {s['name']: s for s in json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']}
BEFORE = {'options': 1619, 'master': 454, 'first_cut': 53, 'analysis': 328, 'visuals': 10227}   # words read by the assistant, measured before this change


def texts(stage):
    s = V3[stage]
    return [s.get('prompt') or '', *(s.get('steps') or []), *(p['text'] for p in s.get('parts') or [])]


def words(stage):
    return sum(len(t.split()) for t in texts(stage))


def rule(n):
    p = V3['options']['prompt']
    return p[p.index(f'\n{n}. ') + 1:p.index(f'\n{n + 1}. ')]


def test_every_stage_is_the_same_length_or_shorter():
    for stage, before in BEFORE.items():
        assert words(stage) <= before, (stage, words(stage), before)


def test_p2_no_change_history_labels_and_the_rule_codes_kept():
    for stage in ('options', 'master', 'first_cut'):
        assert all('design/' not in t for t in texts(stage)), stage
    o = '\n'.join(texts('options'))
    for code in ('R1', 'R5', 'B1', 'E2', 'N14', 'N17'):
        assert code in o, code


def test_p7_a_scene_covers_one_chapter():
    assert 'a scene covers one chapter: a paragraph covering two is split where the second begins' in V3['options']['steps'][1]


def test_p9_rule_3_an_abstract_idea_has_nothing_to_show_and_is_no_longer():
    r3 = rule(3)
    assert 'blanks by default' in r3 and 'camera can see is matched like any other' in r3 and 'B-roll only when clearly relevant' in r3   # the independent check: the gate and 'by default' kept
    old = V2['options']['prompt']
    old3 = old[old.index('\n3. ') + 1:old.index('\n4. ')]
    assert len(r3.split()) <= len(old3.split())


def test_p13_an_ai_only_scene_is_one_blank_and_a_declared_gap_is_refused():
    p = V3['options']['prompt']
    assert "one blank of the scene's length" in p and 'declaring a gap is refused' in p and 'declared in `gaps`' not in p


def test_o7_a_later_part_of_the_same_clip_in_the_same_scene():
    r4 = rule(4)
    assert 'same scene' in r4 and 'not overlapping' in r4 and 'side by side at the same shot size' in r4 and 'decision of kind reuse' in r4
    assert 'including another part of the same clip' not in r4


def test_o1_o3_scene_numbers_second_choices_and_trim_only_rows():
    master = V3['master']['steps'][0]
    assert 'next number' not in master and 'between 2 and 3' not in master
    assert '2-2, keep one of the two' in master and 'needs no answer: its parts decide it, a trim (KEEP_WITH_EDIT) if wanted' in master
    p = V3['options']['prompt']
    assert 'running numbers' not in p and "scene's number" in p and 'second choice' in p and '#2-2A' in p


def test_o4_o6_the_second_look_between_check_and_propose():
    s = V3['options']['steps'][3]
    for needle in ('`vw options second-look`', 'work/options/scenes/', '`vw-scene-review`', 'out/second-look/', '`vw options join-second-look`'):
        assert needle in s, needle
    assert s.index('until valid') < s.index('second look') < s.index('vw options propose')


def test_o9_the_plan_names_its_helper():
    plan = next(p for p in V3['visuals']['parts'] if p['name'] == 'plan')['text']
    assert '`vw-plan-gaps` helper' in plan and 'your own agents' not in plan


def test_p14_the_first_slide_answer_approves_and_the_explicit_record_is_gone():
    o = '\n'.join(texts('options'))
    assert 'remains for an explicit approval' not in o and 'record with their yes' not in o and 'vw options record' not in o
    assert 'the first answer approves the options' in V3['options']['steps'][4] and 'the first answer approves the options' in V3['master']['steps'][0].lower()


def test_the_first_cut_record_is_retired_in_one_line():
    (step,) = V3['first_cut']['steps']
    assert 'vw first-cut record' not in step and 'retired' in step and '`vw master record`' in step and len(step.split()) <= 20


def test_p3_the_steps_name_the_pieces_by_scene():
    s0 = V3['options']['steps'][0]
    assert 'pieces-' in s0 and 'cards-1.json' not in s0 and 'sub-clips-1.json' not in s0 and '`vw options show --sub' in s0
    assert 'cards-N.json' not in V3['options']['steps'][3]


def test_version_2_is_untouched():
    assert '`vw options record --quote "<their yes>"` remains for an explicit approval' in V2['options']['steps'][4]
    assert 'design/44' in V2['first_cut']['steps'][0] and 'between 2 and 3' in V2['master']['steps'][0]
