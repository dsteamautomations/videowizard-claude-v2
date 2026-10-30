"""design/125 stage 7, builder A: O7 (two parts of one
clip in one scene), P1 (prepare names the scenes first), P7 (two chapters warned), P8 (the clip study's fits kept),
P11 (act-on warnings in full, the information-only kinds as one count line), P12, P13 (simpler: an AI-only scene is one blank), P14, and the old ways
retired by refusal. VW-11's own data (trimmed) is in vw11_stage7.json."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.errors import Problem
from app.stage2 import narration as NR, package as P, slides as SL, stage as S, validator as V
from test_design91_b2_pure import POLICY, doc as b2_doc, ev, option, package as b2_package
from test_review_page import FakeConn, FakeStore, RUN

HERE = Path(__file__).resolve().parent
APP = HERE.parent / 'app'
VW11 = json.loads((HERE / 'vw11_stage7.json').read_text(encoding='utf-8'))
USER = {'id': 'u1'}


# ---------- P8: the clip study's fits kept beside the chapter ----------

def vw11_paragraphs():
    """VW-11's scenes are its paragraphs, one each: paragraph BEAT_k spans the sentences that start in scene k."""
    out = {}
    for b in VW11['beats']:
        own = [s for s in VW11['sentences'] if b['timeline_start_frame'] <= s['start_frame'] < b['timeline_end_frame']]
        out[b['beat_id']] = (own[0]['start_frame'], own[-1]['end_frame'])
    return out


def test_p8_vw11_scene_3_gets_the_clip_studys_19_direct_and_43_related_pieces():
    rows = deepcopy(VW11['rows'])
    P.scene_fits(rows, VW11['beats'], vw11_paragraphs())
    cov = {c['beat_id']: c for c in P.coverage(VW11['beats'], rows, {})}
    assert cov['BEAT_03']['kinds'] == {'direct': 19, 'related': 43, 'chapter': 0} and not cov['BEAT_03']['alerts']
    assert cov['BEAT_04']['kinds'] == {'direct': 1, 'related': 4, 'chapter': 0}
    assert cov['BEAT_06']['kinds'] == {'direct': 75, 'related': 12, 'chapter': 0}   # scene 6: every same-chapter piece was also a clip-study match
    assert cov['BEAT_09']['kinds'] == {'direct': 12, 'related': 19, 'chapter': 9}   # scene 9: 9 pieces fit by chapter only, counted apart
    r = next(r for r in rows if 'BEAT_03' in r['model_fits']['primary'])
    assert r['fit_kinds']['BEAT_03'] == 'direct' and 'BEAT_03' in r['primary_fits']


def test_p8_direct_and_chapter_make_primary_related_makes_secondary_and_a_paragraph_reaches_every_scene_it_overlaps():
    windows = [{'beat_id': 'BEAT_01', 'process_stages': ['mix'], 'timeline_start_frame': 0, 'timeline_end_frame': 100},
               {'beat_id': 'BEAT_02', 'process_stages': ['lay'], 'timeline_start_frame': 100, 'timeline_end_frame': 200},
               {'beat_id': 'BEAT_03', 'process_stages': [], 'timeline_start_frame': 200, 'timeline_end_frame': 300}]
    paragraphs = {'BEAT_01': (5, 150), 'BEAT_02': (160, 290)}   # the script had two paragraphs; the first was split into scenes 1 and 2
    rows = [{'primary_fits': ['BEAT_01'], 'secondary_fits': [], 'process_stage': 'other'},
            {'primary_fits': [], 'secondary_fits': ['BEAT_02'], 'process_stage': 'mix'},
            {'primary_fits': [], 'secondary_fits': [], 'process_stage': 'lay'}]
    P.scene_fits(rows, windows, paragraphs)
    assert rows[0]['primary_fits'] == ['BEAT_01', 'BEAT_02'] and rows[0]['secondary_fits'] == [] and rows[0]['fit_kinds'] == {'BEAT_01': 'direct', 'BEAT_02': 'direct'}
    assert rows[1]['primary_fits'] == ['BEAT_01'] and rows[1]['secondary_fits'] == ['BEAT_02', 'BEAT_03']
    assert rows[1]['fit_kinds'] == {'BEAT_01': 'chapter', 'BEAT_02': 'related', 'BEAT_03': 'related'}
    assert rows[2]['primary_fits'] == ['BEAT_02'] and rows[2]['fit_kinds'] == {'BEAT_02': 'chapter'}
    assert rows[0]['model_fits'] == {'primary': ['BEAT_01'], 'secondary': []}


def test_p8_prepare_uses_the_new_fits():
    src = (APP / 'stage2' / 'stage.py').read_text(encoding='utf-8')
    assert 'P.scene_fits(' in src and "r['secondary_fits'] = []" not in src


# ---------- P11, P12 ----------

def test_p11_vw11_flags_give_three_to_act_on_and_one_count_line():
    out = V.answer_flags(VW11['flags'])
    assert len(out['act_on']) == 3 and all('N17' in f for f in out['act_on'])
    assert out['for_information'] == '38 for information: R1 17, R10 13, R4 5, R8 3'
    assert V.answer_flags([]) == {'act_on': [], 'for_information': ''}


def test_p11_the_check_and_propose_answer_with_the_grouping():
    src = (APP / 'stage2' / 'stage.py').read_text(encoding='utf-8')
    assert 'flags_by_rule' not in src and src.count('V.answer_flags(') == 2


def test_p12_the_n17_message_promises_nothing():
    d = b2_doc()
    for o in d['options']:
        o.pop('steps')
    flags = V.validate_options(d, b2_package(), POLICY)['flags']
    assert any('N17 no step map' in f for f in flags) and not any('refused from the next' in f for f in flags)


# ---------- P13: a declared gap is retired; an AI-only scene is one blank ----------

def test_p13_a_declared_gap_is_refused_and_a_missing_scene_says_one_blank():
    d = b2_doc(gaps=[{'beat_id': 'BEAT_02', 'reason': 'zero coverage'}])
    d['options'] = d['options'][:1]
    refusals = V.validate_options(d, b2_package(), POLICY)['refusals']
    assert "declare a gap is retired; write it as one blank of the scene's length" in refusals
    assert any(r.startswith('BEAT_02: no option') and 'one blank' in r for r in refusals)


def test_p13_the_scene_summary_has_no_declared_blank_note():
    assert 'declared blank' not in (APP / 'stage2' / 'slides.py').read_text(encoding='utf-8')
    assert 'gaps' not in P.build({'id': 'r', 'code': 'c'}, {}, [], [], [], set(), [], [], {'fps': 25}, {}, '')['shapes']['options']


# ---------- a small approved film (the old-ways tests below) ----------

def o1_session():
    """A film with scene 1 cut from two shots and a 3 s blank between; the options are approved."""
    pk = {'beats': [{'beat_id': 'BEAT_01', 'title': 'Need', 'timeline_start_frame': 0, 'timeline_end_frame': 250, 'target_beat_frames': 250}],
          'sub_clips': [{'sub_clip_id': f'c{i}:S', 'clip_id': f'c{i}', 'clip_name': f'C{i}.MP4', 'in_frame': 0, 'out_frame': 200, 'source_fps': '25', 'min_hold_s': 1.0,
                         'action_peak': None, 'sfx_cues': []} for i in (1, 2)],
          'cards': [], 'narration': {'words': []}, 'project': {}, 'timeline': {'fps': 25}}
    shot = lambda sid, n: {'sub_clip_id': sid, 'source_in_frame': 0, 'source_out_frame': n, 'timeline_frames': n, 'match': 'direct', 'evidence': 'x'}
    doc = {'options': [{'option_number': 1, 'beat_id': 'BEAT_01', 'events': [shot('c1:S', 100), {'blank': True, 'timeline_frames': 75, 'intent': 'a diagram'}, shot('c2:S', 75)]}]}
    sl = SL.slides(doc, pk, 25)
    sess = {'contract': 'vw2-stage2-session-v1', 'package': {'key': 'p', 'digest': 'pk1'}, 'current': 'd1', 'accepted': {'version': 1, 'digest': 'd1'},
            'versions': [{'version': 1, 'digest': 'd1', 'file': {'key': 'run-1/stage2/options-v1.json'}, 'slides': sl}],
            'frames': {}, 'inspections': {}, 'renders': {}, 'decisions': {}, 'extra_rules': [], 'master': None, 'recorded': {}}
    return FakeStore({'run-1/stage2/session.json': sess, 'run-1/stage2/options-v1.json': {'document': doc, 'package_digest': 'pk1'}, 'p': pk})


def saved(store):
    return json.loads(store.files['run-1/stage2/session.json'])


# ---------- O7: two parts of one clip in one scene ----------

def q4(d):
    return [r for r in V.validate_options(deepcopy(d), b2_package(), POLICY)['refusals'] if 'Q4' in r]


def test_o7_a_later_non_overlapping_part_in_the_same_scene_is_not_a_reuse():
    d = b2_doc()
    d['options'][0]['events'] = [ev('clip0:SUB_01', 0, 12), ev('clip1:SUB_01', 0, 12), ev('clip0:SUB_02', 25, 38)]
    assert q4(d) == []
    d['options'][0]['events'][2] = ev('clip0:SUB_01', 6, 19)   # overlaps the first part
    assert q4(d)
    d['options'][0]['events'] = [ev('clip0:SUB_02', 25, 37), ev('clip1:SUB_01', 0, 12), ev('clip0:SUB_01', 0, 13)]   # an earlier moment
    assert q4(d)
    d = b2_doc()
    d['options'][1]['events'] = [ev('clip0:SUB_02', 25, 38)]   # another scene: still a reuse question
    assert q4(d)


def test_o7_two_parts_of_one_clip_side_by_side_at_one_size_are_refused():
    pk = b2_package()
    pk['sub_clips'][1]['effective_shot_size'] = 'WS'   # clip0's second part at the first part's size
    d = b2_doc()
    d['options'][0]['events'] = [ev('clip0:SUB_01', 0, 12), ev('clip0:SUB_02', 25, 38), ev('clip1:SUB_01', 0, 12)]
    r = V.validate_options(deepcopy(d), pk, POLICY)['refusals']
    assert any('two parts of clip clip0 side by side' in x for x in r) and not any('Q4' in x for x in r)
    d['options'][0]['events'] = [ev('clip0:SUB_01', 0, 12), ev('clip1:SUB_02', 25, 38), ev('clip0:SUB_02', 25, 37)]   # another shot between: fine
    assert not any('side by side' in x for x in V.validate_options(deepcopy(d), pk, POLICY)['refusals'])


def test_o7_the_master_takes_two_parts_of_one_sub_clip_in_one_scene():
    pk = {'beats': [{'beat_id': 'BEAT_01', 'target_beat_frames': 60}], 'project': {}, 'timeline': {'fps': 25}}
    e = lambda a, z, at: {'kind': 'event', 'sub_clip_id': 'c1:S', 'beat_id': 'BEAT_01', 'approved_from_option': 1, 'source_in_frame': a, 'source_out_frame': z,
                          'timeline_frames': z - a, 'timeline_in_frame': at, 'timeline_out_frame': at + z - a}
    assert V.validate_master({'events': [e(0, 30, 0), e(40, 70, 30)]}, pk)['refusals'] == []
    assert any('Q4' in r for r in V.validate_master({'events': [e(0, 30, 0), e(20, 50, 30)]}, pk)['refusals'])


# ---------- P1, P7, P14 ----------

def test_p1_prepare_names_the_scenes_step_until_they_are_approved():
    assert 'propose the scenes' in S.prepare_next(False) and 'coverage' in S.prepare_next(True)
    assert 'propose the scenes' not in S.prepare_next(True)


def test_p7_a_scene_with_two_chapters_is_warned():
    scenes = [{'title': b['title'], 'process_stages': b['process_stages']} for b in VW11['beats']]
    w = NR.chapter_warnings(scenes)
    assert len(w) == 2 and w[0].startswith('Scene 2 lists two chapters') and w[1].startswith('Scene 6 lists two chapters')
    assert 'set_scenes' in (APP / 'stage2' / 'stage.py').read_text(encoding='utf-8') and "'warnings': NR.chapter_warnings(" in (APP / 'stage2' / 'stage.py').read_text(encoding='utf-8')


def test_p14_the_message_after_propose_says_the_first_answer_approves():
    assert S.PROPOSE_NEXT == '`vw options render`; the operator watches and answers the slides on the page; the first answer approves the options'
    assert 'vw options record' not in (APP / 'stage2' / 'stage.py').read_text(encoding='utf-8')


# ---------- old ways retired by refusal ----------

def test_the_explicit_options_approval_is_refused():
    with pytest.raises(Problem, match='answering the first slide approves the options'):
        S.record_options(FakeConn({}), o1_session(), USER, RUN, 'Yes, these options.')


def test_the_separate_first_cut_record_is_refused():
    with pytest.raises(Problem, match='the first cut is recorded with the master'):
        S.record_first_cut(FakeConn({}), FakeStore({}), USER, RUN, [], 'watched and listened')


def test_a_version_without_stored_slides_is_refused():
    store = o1_session()
    sess = saved(store)
    del sess['versions'][0]['slides']
    store.files['run-1/stage2/session.json'] = json.dumps(sess).encode('utf-8')
    with pytest.raises(Problem, match='no stored slides'):
        S.slides_view(store, RUN)
