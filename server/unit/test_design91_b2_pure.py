"""design/91 batch 2: N17 the step being narrated, N14 consecutive steps agree (options and visuals), N6 facts, N7 practice, N8 the words, N10 the subject itself."""
import sys
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from clip_log_fixture import synthetic_log   # noqa: E402  (pure: the Docker suite's synthetic clip log)

from app import image_check as IC, visual_contract as VC, visuals_stage as VS   # noqa: E402
from app.clip_log import solver   # noqa: E402
from app.errors import Problem   # noqa: E402
from app.stage2 import package as P, validator as V   # noqa: E402
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, g, plan_doc, ref, saved, session, shot, store_with   # noqa: E402
from test_visuals_pure import GAPS, plan, shot as pshot   # noqa: E402

TL = {'width': 1920, 'height': 1080, 'fps': 25}
POLICY = {'allow_speaker_audio': False, 'show_speaker_video': False}


# ---------- the options (N17, N14) ----------

def package(stages=(['laying'], ['laying'])):
    rows, cards = [], []
    for i in range(3):
        cid = f'clip{i}'
        clip = {'id': cid, 'name': f'c{i}.mp4', 'sha256': f'{i:064x}', 'bytes': 1, 'duration_s': 2.0, 'has_audio': True, 'width': 1920, 'height': 1080, 'fps': '25/1'}
        log = synthetic_log(f'CLIP{i}', clip['name'], 25.0, 50)
        solver.solve(log, POLICY, clip, TL)
        for s in log['sub_clips']:
            rows.append(P.sub_clip_row(clip, log, s, 25))
        cards.append({'clip_id': cid, 'clip_name': clip['name'], 'descriptive_name': log['descriptive_name'], 'lines': log['summary_card_lines']})
    beats = [{'beat_id': 'BEAT_01', 'passage_id': 'P001', 'text': 'Mortar is mixed. Strings are fixed.', 'process_stages': list(stages[0]), 'timeline_start_frame': 0, 'timeline_end_frame': 37,
              'target_beat_frames': 37, 'window_start_s': 0.0, 'window_end_s': 1.48},
             {'beat_id': 'BEAT_02', 'passage_id': 'P002', 'text': 'Bricks go on.', 'process_stages': list(stages[1]), 'timeline_start_frame': 37, 'timeline_end_frame': 50,
              'target_beat_frames': 13, 'window_start_s': 1.48, 'window_end_s': 2.0}]
    narration = {'sentences': [{'text': 'Mortar is mixed.', 'start_frame': 0, 'end_frame': 18}, {'text': 'Strings are fixed.', 'start_frame': 20, 'end_frame': 36},
                               {'text': 'Bricks go on.', 'start_frame': 38, 'end_frame': 49}], 'words': [], 'silences': []}
    pk = P.build({'id': 'r', 'code': 'VW-T', 'client': 'C'}, {}, beats, cards, rows, set(), [], [], TL, POLICY, 'prompt', narration=narration)
    for r in pk['sub_clips']:
        r['process_stage'], r['color_group'], r['landmarks'] = 'laying', 'GRP_A', ['the plinth', 'a mortar pan']
    return pk


def ev(sid, a, b, **kw):
    return {'sub_clip_id': sid, 'source_in_frame': a, 'source_out_frame': b, 'crop': 'full', 'a2_intervals': [], 'match': 'direct', 'evidence': 'primary_fit_for_beats names this scene', **kw}


def option(n, beat, rank, events, **kw):
    return {'option_number': n, 'beat_id': beat, 'rank': rank, 'events': events, 'reasoning': 'synthetic', 'log_fields_cited': ['primary_fit_for_beats'],
            'best_unchosen': {'sub_clip_id': 'none', 'rule': 'none better'}, **kw}


def steps(*rows):
    return [{'step_id': s, 'event': e, **({'why': w} if w else {})} for s, e, w in rows]


def doc(**over):
    o1 = option(1, 'BEAT_01', 'PRIMARY', [ev('clip0:SUB_01', 0, 25), ev('clip1:SUB_01', 0, 12)],
                steps=steps(('BEAT_01.S1', 1, 'process_stage laying: the mortar pan is worked'), ('BEAT_01.S2', 2, 'outcome_state: a line is stretched')))
    o2 = option(2, 'BEAT_02', 'PRIMARY', [ev('clip2:SUB_01', 0, 13)], steps=steps(('BEAT_02.S1', 1, 'process_stage laying')))
    return {'contract': 'vw2-options-v1', 'options': [o1, o2], 'gaps': [], 'qc_self': {f'Q{i}': {'pass': True, 'evidence': 'synthetic'} for i in range(1, 9)}, **over}


def check(d, pk=None):
    return V.validate_options(deepcopy(d), pk or package(), POLICY)


def n17(r):
    return [x for x in r if 'N17' in x or 'N14' in x]


def test_the_package_gives_every_scene_its_steps_from_the_timed_sentences():
    pk = package()
    assert [s['step_id'] for s in pk['beats'][0]['steps']] == ['BEAT_01.S1', 'BEAT_01.S2'] and pk['beats'][0]['steps'][1]['text'] == 'Strings are fixed.'
    assert [s['step_id'] for s in pk['beats'][1]['steps']] == ['BEAT_02.S1']


def test_every_step_is_shown_by_an_event_or_left_as_a_blank():
    """N17: a step left out, an unknown event, a real shot without its why are refused; a full map passes."""
    r = check(doc())
    assert not r['refusals'] and not n17(r['flags'])
    d = doc()
    d['options'][0]['steps'] = d['options'][0]['steps'][:1]
    assert any('BEAT_01.S2' in x and 'N17' in x for x in check(d)['refusals'])
    d = doc()
    d['options'][0]['steps'][1]['event'] = 7
    assert any('N17' in x and 'event 7' in x for x in check(d)['refusals'])
    d = doc()
    d['options'][0]['steps'][1].pop('why')
    assert any('N17' in x and 'why' in x for x in check(d)['refusals'])


def test_an_option_without_a_step_map_is_flagged_this_release():
    d = doc()
    for o in d['options']:
        o.pop('steps')
    r = check(d)
    assert not n17(r['refusals']) and any('N17' in x and 'refused from the next' in x for x in r['flags'])


def test_footage_of_another_process_stage_and_a_claim_shown_by_footage_are_flagged():
    pk = package()
    pk['sub_clips'][0]['process_stage'] = 'curing'
    d = doc()
    d['options'][0]['steps'][0]['claim'] = True
    flags = n17(check(d, pk)['flags'])
    assert any('curing' in x and 'laying' in x for x in flags) and any('claim' in x for x in flags)


def test_a_shot_without_the_state_carried_over_is_flagged():
    """N14: the option names what the step before left; a clip that does not show it is flagged."""
    d = doc()
    d['options'][1]['carries_over'] = ['the plinth']
    assert not n17(check(d)['flags'])
    pk = package()
    for r in pk['sub_clips']:
        if r['clip_id'] == 'clip2':
            r['landmarks'] = ['bare sand']
    assert any('N14' in x and 'the plinth' in x for x in check(d, pk)['flags'])


def test_consecutive_scenes_of_one_process_in_two_places_are_flagged_unless_the_move_is_named():
    pk = package()
    for r in pk['sub_clips']:
        if r['clip_id'] == 'clip2':
            r['color_group'] = 'GRP_B'
    assert any('N14' in x and 'GRP_B' in x for x in check(doc(), pk)['flags'])
    d = doc()
    d['options'][1]['moves_place'] = 'the narration moves to the kiln yard'
    assert not n17(check(d, pk)['flags'])
    assert not [x for x in check(doc(), package(stages=(['laying'], ['curing'])))['flags'] if 'N14' in x]   # two processes: a new place is expected


# ---------- the plan (N6, N8, N10, N14, N17) ----------

def kinds(doc_):
    return {(w.get('shot_id'), w['kind']) for w in VC.validate_plan(doc_, GAPS, Fraction(25))[1]}


def rest(a=100):
    return [pshot('VS1', a, 500, 'video'), pshot('VS2', 500, 1000, 'video')]


FACT = {'id': 'F1', 'about': 'M1', 'looks': 'sun-dried, reddish brown, solid, never hollow', 'how': 'moulded by hand and dried in rows', 'setting': 'beside the kiln',
        'tools': 'a wooden mould', 'source': 'clip c3 at 12 s', 'status': 'observed'}


def with_material(shots, facts=None):
    d = plan(shots)
    d['elements'].append({'id': 'M1', 'name': 'Unburnt brick', 'kind': 'material', 'identity': 'representative', 'requirements': 'green brick',   # design/111 F10: a material carries its spec
                          'material_spec': {'dimensions': [{'part': 'brick', 'measure': 'length', 'value': 230, 'unit': 'mm', 'source': 'the maker', 'status': 'confirmed'}],
                                            'laid': 'flat, in rows', 'pattern': 'rows drying side by side', 'proportions': ['about twice as long as wide']}})
    if facts is not None:
        d['visual_facts'] = facts
    return d


def test_facts_come_with_their_source_and_an_unknown_one_is_never_shown_close():
    """N6."""
    im = {**pshot('IM1', 0, 100, 'image'), 'element_ids': ['M1']}
    assert ('IM1', 'facts_missing') in kinds(with_material([im] + rest()))
    assert ('IM1', 'facts_missing') not in kinds(with_material([{**im, 'fact_ids': ['F1']}] + rest(), [FACT]))
    with pytest.raises(ValueError, match='source'):
        VC.validate_plan(with_material([im] + rest(), [{**FACT, 'source': ''}]), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='F9'):
        VC.validate_plan(with_material([{**im, 'fact_ids': ['F9']}] + rest(), [FACT]), GAPS, Fraction(25))
    close = {**im, 'framing': 'close-up of the brick face', 'fact_ids': ['F1']}
    with pytest.raises(ValueError, match='never invented'):
        VC.validate_plan(with_material([close] + rest(), [{**FACT, 'status': 'unknown', 'source': ''}]), GAPS, Fraction(25))
    out, _ = VC.validate_plan(plan([pshot('IM1', 0, 100, 'image')] + rest()), GAPS, Fraction(25))
    assert 'visual_facts' not in out and 'fact_ids' not in out['gaps'][0]['scenes'][0]['shots'][0]   # absent stays absent


def test_every_shot_lists_its_claims_and_words_and_a_claim_says_how_it_is_shown():
    """N8, N17."""
    im = {**pshot('IM1', 0, 100, 'image'), 'narration': 'Well burnt bricks are stronger.'}
    assert ('IM1', 'claims_missing') in kinds(plan([im] + rest()))
    listed = {**im, 'claims': ['well burnt bricks are stronger'], 'descriptors': ['well burnt']}
    found = kinds(plan([listed] + rest()))
    assert ('IM1', 'claims_missing') not in found and ('IM1', 'evidence_missing') in found
    assert ('IM1', 'evidence_missing') not in kinds(plan([{**listed, 'evidence': 'a brick struck against another rings clear: the result shown'}] + rest()))


def test_a_graphic_says_what_it_depicts():
    """N10."""
    dg = {**pshot('DG1', 0, 100, 'diagram'), 'claims_left_out': [{'claim': 'x', 'reason': 'y'}]}
    assert ('DG1', 'depicts_missing') in kinds(plan([dg] + rest()))
    assert ('DG1', 'depicts_missing') not in kinds(plan([{**dg, 'depicts': 'a rat-trap wall in elevation'}] + rest()))


def test_the_next_step_says_what_it_carries_over():
    """N14 in the plan."""
    from test_design91_b1_pure import subject
    im = {**pshot('IM1', 0, 100, 'image'), 'narration': 'Then the bricks are laid on the plinth.', 'claims_left_out': [{'claim': 'x', 'reason': 'y'}],
          'subjects': [subject((0, 100, None))]}   # design/124-b item 20: a next step of a process, where a subject acts
    assert ('IM1', 'carries_over_missing') in kinds(plan([im] + rest()))
    assert ('IM1', 'carries_over_missing') not in kinds(plan([{**im, 'carries_over': ['the plinth under the first course']}] + rest()))


# ---------- the pictures (N6, N7, N8, N10, N14) ----------

def scene_session():
    im = shot('IM1', 0, 500, 'image', narration='Well burnt bricks ring clear.', element_ids=['E2'], claims=['well burnt bricks are stronger'], descriptors=['well burnt'],
              carries_over=['the stack from the kiln'], fact_ids=['F1'], evidence='a brick rings when struck')
    dg = shot('DG1', 900, 1150, 'diagram', narration='The rat-trap wall.', depicts='a rat-trap wall in elevation', claims_left_out=[{'claim': 'x', 'reason': 'y'}])
    doc_ = plan_doc([im], [dg])
    doc_['elements'].append({'id': 'E2', 'name': 'Burnt brick', 'kind': 'material', 'identity': 'representative', 'requirements': 'a burnt brick'})
    doc_['visual_facts'] = [{'id': 'F1', 'about': 'E2', 'looks': 'deep red, dry, a clear ring when struck', 'how': 'fired in a clamp kiln', 'setting': 'the kiln yard',
                             'tools': '', 'source': 'client brochure p.2', 'status': 'confirmed'}]
    return doc_, session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc_))


def test_a_picture_for_a_named_shot_carries_its_claims_words_state_and_facts(monkeypatch):
    """N6, N8, N14: never the opposite of a claim; the words; the state carried over; the element's facts."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc_, sess = scene_session()
    store = store_with(sess, doc_)
    body = {'request_id': 'k1', 'element_id': 'E2', 'name': 'bricks', 'kind': 'keyframe', 'subject': 'bricks', 'prompt': 'Bricks in a stack.', 'shot_id': 'IM1'}
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    lines = {l['check']: l for l in saved(store)['references'][out['reference_id']]['server_checklist']}
    assert 'opposite' in lines['claim: well burnt bricks are stronger']['pass_when'] and lines['word: well burnt']['weight'] == 'must'
    assert lines['carried over: the stack from the kiln']['weight'] == 'must' and 'deep red' in lines['fact: F1']['pass_when']
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'request_id': 'k2', 'shot_id': None, 'kind': 'isolated'})   # design/94: an element reference, no shot
    lines = {l['check'] for l in saved(store)['references'][out['reference_id']]['server_checklist']}
    assert 'fact: F1' in lines and 'claim: well burnt bricks are stronger' not in lines   # the element's facts on every picture; a shot's words only when it is named


def test_a_graphic_carries_what_it_depicts_and_the_spec_repeats_it(monkeypatch):
    """N10."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc_, sess = scene_session()
    store = store_with(sess, doc_)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'g1', 'element_id': 'E1', 'name': 'wall', 'kind': 'keyframe', 'subject': 'the wall', 'prompt': 'A wall.', 'shot_id': 'DG1'})
    lines = {l['check']: l for l in saved(store)['references'][out['reference_id']]['server_checklist']}
    assert lines['depicts: a rat-trap wall in elevation']['weight'] == 'must'


def test_scene_pictures_are_checked_for_plausible_setting_and_practice_graphics_are_not():
    """N7: should lines, so they never start a fix round alone."""
    scene = IC.lines_of({'element_kind': 'material', 'kind': 'keyframe'})
    graphic = IC.lines_of({'element_kind': 'graphic', 'kind': 'isolated'})
    practice = [l for l in scene if l['check'] in ('plausible setting', 'practitioner')]
    assert len(practice) == 2 and all(l['weight'] == 'should' for l in practice)
    assert not [l for l in graphic if l['check'] in ('plausible setting', 'practitioner')]


def test_a_material_element_matches_material_seen_in_the_footage():
    """N6: materials and processes join the reference round like any element."""
    assert 'material' in VS.KIND_MATCH['material'] and VS.KIND_MATCH['process']


def test_the_api_takes_a_style_sheet_and_the_shot_a_picture_is_for():
    """The batch-2 slip (design/89 C2): the request model refused kind style; design/91 N8: shot_id."""
    from app.main import ImageGenerate
    body = ImageGenerate(request_id='00000000-0000-0000-0000-000000000001', element_id='_STYLE', name='style', kind='style', subject='the style', prompt='A style sheet.', shot_id=None)
    assert body.kind == 'style'
    assert ImageGenerate(request_id='00000000-0000-0000-0000-000000000002', element_id='E1', name='k', kind='keyframe', subject='s', prompt='p', shot_id='IM1').shot_id == 'IM1'
