"""design/89 batch 2: C graphics say what the narration says (claims, one style per film, builds on the words, the answer form);
D technical drawings come from a sourced spec (the spec, its status rules, the measure call, the approval, the check)."""
import json
from fractions import Fraction
import types

import pytest

from app import image_check as IC, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_visuals_stage_pure import FakeConn, FakeStore, RUN, USER, accepted, g, gap_digest, plan_doc, ref, saved, session, shot, store_with
from test_visuals_pure import GAPS, plan, shot as pshot, states

SPEC = {'parts': ['inner leaf', 'outer leaf', 'cavity'], 'relationships': ['the two leaves are the same thickness', 'the cavity is inside the wall'],
        'dimensions': [{'part': 'leaf', 'measure': 'thickness', 'value': 110, 'unit': 'mm', 'source': 'client brochure p.4', 'status': 'confirmed'},
                       {'part': 'cavity', 'measure': 'width', 'value': None, 'unit': 'mm', 'source': '', 'status': 'unknown',
                        'tried': 'not in the client brochure; no footage frame shows the cavity; no standard or maker figure for this wall; no approved picture shows it'}],   # design/106 D3, design/111 F19: all four sources tried
        'label': 'illustrative, not to scale', 'illustrative': True, 'view': 'cutaway', 'view_reason': 'the cavity is inside the wall'}   # design/111 F19


def kinds(doc, gaps=GAPS):
    return {(w.get('shot_id'), w['kind']) for w in VC.validate_plan(doc, gaps, Fraction(25))[1]}


# ---------- the plan ----------

def test_a_graphic_lists_the_claims_spoken_over_it_or_names_what_it_leaves_out():
    """C1."""
    bare = plan([{**pshot('DG1', 0, 100, 'diagram'), 'narration': 'Rat-trap bond saves bricks and keeps heat out.'}, pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    assert ('DG1', 'claims_missing') in kinds(bare)
    bare['gaps'][0]['scenes'][0]['shots'][0]['claims'] = ['saves bricks']
    bare['gaps'][0]['scenes'][0]['shots'][0]['claims_left_out'] = [{'claim': 'keeps heat out', 'reason': 'the next shot shows it'}]
    assert ('DG1', 'claims_missing') not in kinds(bare)


def test_a_film_with_graphics_has_one_graphic_style():
    """C2."""
    doc = plan([pshot('DG1', 0, 100, 'diagram'), pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    assert (None, 'style_missing') in kinds(doc)
    doc['foundation']['graphic_style'] = {'palette': 'brick red, warm grey, off-white', 'line_weight': '3 px', 'labels': 'sans, 28 px', 'background': 'off-white', 'frame_fill': 'fills the frame'}
    assert (None, 'style_missing') not in kinds(doc)
    out, _ = VC.validate_plan(plan([pshot('VS1', 0, 500, 'video'), pshot('VS2', 500, 1000, 'video')]), GAPS, Fraction(25))
    assert 'graphic_style' not in out['foundation']   # absent stays absent


def test_each_state_of_a_build_starts_on_the_words_it_illustrates():
    """C3."""
    w = lambda text, a, b: {'text': text, 'start_frame': a, 'end_frame': b}
    timing = {'words': [w('First', 0, 10), w('the', 12, 15), w('leaves.', 16, 30), w('Then', 80, 90), w('the', 92, 95), w('cavity.', 96, 120)]}
    gaps = {'G1': {'start_frame': 0, 'end_frame': 1000, 'timing': timing}}
    sts = [{'what_appears': 'two leaves', 'hold_s': 3.2, 'words': 'First the leaves'}, {'what_appears': 'the cavity', 'hold_s': 3.0, 'words': 'Then the cavity'}]
    doc = plan([{**pshot('AN1', 0, 155, 'animation'), 'states': sts}, pshot('VS1', 155, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    assert ('AN1', 'state_off_words') not in kinds(doc, gaps)   # the second state starts at 3.2 s; its words at 3.2 s
    sts[0]['hold_s'], sts[1]['hold_s'] = 4.6, 1.6
    doc['gaps'][0]['scenes'][0]['shots'][0]['states'] = [sts[0], {**sts[1], 'hold_s': 1.6}]
    with pytest.raises(ValueError):
        VC.validate_plan(doc, gaps, Fraction(25))   # a state holds at least 3 s
    doc['gaps'][0]['scenes'][0]['shots'][0].update(end_frame=200, states=[{**sts[0], 'hold_s': 5.0}, {**sts[1], 'hold_s': 3.0}])
    doc['gaps'][0]['scenes'][0]['shots'][1]['start_frame'] = 200
    found = {w['kind']: w['message'] for w in VC.validate_plan(doc, gaps, Fraction(25))[1] if w.get('shot_id') == 'AN1'}
    assert 'state_off_words' in found and 'state 2' in found['state_off_words'] and '3.2 s' in found['state_off_words']


def test_a_drawing_spec_never_invents_a_number_and_says_where_each_comes_from():
    """D1, D3."""
    from drawn_fixture import as_drawn
    base = lambda spec: plan([as_drawn({**pshot('DG1', 0, 100, 'diagram'), 'drawing_spec': spec}), pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])   # SK 27 Oct: exact sizes are drawn
    VC.validate_plan(base(SPEC), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='never invented'):
        VC.validate_plan(base({**SPEC, 'dimensions': [{**SPEC['dimensions'][1], 'value': 60}]}), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='not to scale'):
        VC.validate_plan(base({**SPEC, 'label': ''}), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='its source'):
        VC.validate_plan(base({**SPEC, 'dimensions': [{**SPEC['dimensions'][0], 'source': ''}], 'label': ''}), GAPS, Fraction(25))
    assert ('DG1', 'spec_missing') in kinds(plan([pshot('DG1', 0, 100, 'diagram'), pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')]))


# ---------- the pictures ----------

def graphic_session(**over):
    doc = plan_doc([shot('DG1', 0, 100, 'diagram', narration='Rat-trap bond saves bricks.', claims=['saves bricks'], drawing_spec=SPEC), shot('IM1', 100, 500, 'image')],
                   [shot('VS1', 900, 1150, 'video', subjects=[])])
    doc['foundation']['graphic_style'] = {'palette': 'brick red', 'line_weight': '3 px', 'labels': 'sans', 'background': 'off-white', 'frame_fill': 'fills the frame'}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc), **over)
    return doc, sess


ANSWER = {'status': 'ready', 'prompt': 'Image 1 is the style sheet: take its style. A flat drawing of the wall section.', 'checklist': [{'check': 'look', 'pass_when': 'flat', 'weight': 'must'}], 'exact_text': []}


def test_a_graphic_picture_carries_the_claims_and_relationships_as_must_lines_and_warns_without_style_spec_or_answer(monkeypatch):
    """C1, C2, C4, D4, D5: warned in this release, refused from the next."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc, sess = graphic_session()
    store = store_with(sess, doc)
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'diagram-E1', 'kind': 'isolated', 'subject': 'the wall section', 'prompt': ANSWER['prompt'], 'shot_id': 'DG1'}
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    w = ' | '.join(out['warnings'])
    assert 'answer form' in w and 'style sheet' in w and 'drawing spec' in w and 'refused from the next' in w
    row = saved(store)['references'][out['reference_id']]
    lines = {(l['check'], l['weight']) for l in row['server_checklist']}
    assert ('claim: saves bricks', 'must') in lines and ('relationship: the two leaves are the same thickness', 'must') in lines and ('relationship: the cavity is inside the wall', 'must') in lines
    assert [l['check'] for l in IC.lines_of(row)][:3] == ['claim: saves bricks', 'relationship: the two leaves are the same thickness', 'relationship: the cavity is inside the wall']
    # with a style sheet approved and bound, the spec approved and an answer: no warnings
    s = saved(store)
    s['references']['ST1'] = {**ref('ST1', 'approved'), 'kind': 'style', 'element_id': '_STYLE'}
    s['spec_approvals'] = {'DG1': {'digest': VS.spec_digest(SPEC), 'quote': 'yes'}}
    store = store_with(s, doc)
    named = 'Image 1 is the style sheet: take its palette and line weight. ' + ANSWER['prompt']   # design/96 C1: an edit names its pictures
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'request_id': 'r2', 'parents': ['ST1'], 'prompt': named, 'answer': {**ANSWER, 'prompt': named}})
    assert not out.get('warnings')
    assert [l['check'] for l in saved(store)['references'][out['reference_id']]['answer']['checklist']][0] == 'look'
    # the spec changed after its approval: warned again
    doc2 = json.loads(json.dumps(doc))
    doc2['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec']['relationships'] = ['the leaves differ']
    s2 = {**saved(store), 'accepted': accepted(doc2)}   # the changed plan is accepted again; its spec is not
    out = VS.generate_image(FakeConn([]), store_with(s2, doc2), USER, RUN, [], {**body, 'request_id': 'r3', 'parents': ['ST1'], 'answer': ANSWER})
    assert any('drawing spec' in x for x in out['warnings'])


def test_the_style_sheet_is_a_picture_of_its_own_and_the_packet_names_it(monkeypatch):
    """C2."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc, sess = graphic_session()
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 's1', 'element_id': '_STYLE', 'name': 'style', 'kind': 'style', 'subject': 'the film\'s graphic style',
                                                                  'prompt': 'A style sheet: palette swatches, a line, a label.', 'answer': {**ANSWER, 'prompt': 'A style sheet: palette swatches, a line, a label.'}})
    assert saved(store)['references'][out['reference_id']]['kind'] == 'style'
    with pytest.raises(Problem, match='style'):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 's2', 'element_id': '_STYLE', 'name': 'x', 'kind': 'isolated', 'subject': 'x', 'prompt': 'x'}))


def test_the_operator_approves_the_drawing_spec_as_a_table():
    """D4: one approval per spec, with the operator's words; the same function for the page and chat."""
    doc, sess = graphic_session()
    store = store_with(sess, doc)
    # design/106 D4 (was: the operator's words were required): a spec is approved without words; the sizes come from the planner
    with pytest.raises(Problem, match='no drawing spec'):
        g(lambda: VS.approve_spec(store, USER, RUN, [], 'IM1', 'yes'))
    out = VS.approve_spec(store, USER, RUN, [], 'DG1', 'The sizes are right.')
    assert out['shot_id'] == 'DG1' and saved(store)['spec_approvals']['DG1']['digest'] == VS.spec_digest(SPEC)
    assert out['table'][0] == {'part': 'leaf', 'measure': 'thickness', 'size': '110 mm', 'source': 'client brochure p.4', 'status': 'confirmed'}


def test_the_footage_is_measured_from_approved_frames_with_the_clip_and_time_kept(monkeypatch):
    """D2: Gemini reads the frames; the answer keeps where each number came from."""
    doc, sess = graphic_session(references={'F1': {**ref('F1', 'approved'), 'kind': 'frame', 'source': {'media_id': 'c1', 'requested_s': 4.5}}, 'R1': ref('R1', 'approved')})
    store = store_with(sess, doc)
    store.files['run-1/visuals/references/F1.png'] = b'png'
    monkeypatch.setattr(VS, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: 'k')))

    class T:
        def __init__(self, key, model, **kw):
            pass

        def generate(self, payload):
            T.payload = payload
            return {'body': {'measurements': [{'part': 'brick', 'measure': 'length', 'value': 230, 'unit': 'mm', 'how': 'against the 1 m level'}], 'limits': 'one angle'}}
    monkeypatch.setattr(VS, '_gemini_transport', lambda: T)
    with pytest.raises(Problem, match='footage frames'):
        g(lambda: VS.measure(store, USER, RUN, [], ['R1'], 'How long is a brick?'))
    out = VS.measure(store, USER, RUN, [], ['F1'], 'How long is a brick?')
    m = out['measurements'][0]
    assert m['value'] == 230 and m['status'] == 'measured' and m['source'] == 'clip c1 at 4.5 s' and saved(store)['measurements'][out['measure_id']]['question'] == 'How long is a brick?'
    assert 'How long is a brick?' in json.dumps(T.payload)


def test_a_take_without_its_answer_form_is_warned():
    """C4 for takes."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': {**ref('R1', 'approved'), 'kind': 'sheet'}, 'R2': ref('R2', 'approved')},
                   bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}})
    out = VS.prepare_take(store_with(sess, doc), USER, RUN, [], {'shot_id': 'VS1', 'motion_prompt': 'water poured', 'subject_reconciliation': {}, 'start_image': 'R1', 'end_image': 'R2',
                                                                 'continuity_notes': 'the wall stays'})
    assert any('answer form' in w and 'refused from the next' in w for w in out['warnings'])


def test_every_picture_without_its_answer_form_is_warned_and_a_drawing_is_checked_against_its_sizes_and_label(monkeypatch):
    """C4 for every picture, not only graphics; D3, D5: an unknown size shows no figure, the label is on the drawing, a known size reads right."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc, sess = graphic_session()
    doc['elements'].append({'id': 'E2', 'name': 'Kiln', 'kind': 'object', 'identity': 'representative', 'requirements': 'a kiln'})
    doc['gaps'][1]['scenes'][0]['shots'][0]['element_ids'] = ['E2']
    sess['accepted'] = accepted(doc)
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'k1', 'element_id': 'E2', 'name': 'kiln', 'kind': 'isolated', 'subject': 'a kiln', 'prompt': 'A brick kiln.'})
    assert len(out['warnings']) == 1 and 'answer form' in out['warnings'][0] and 'refused from the next' in out['warnings'][0]
    assert [l['check'] for l in saved(store)['references'][out['reference_id']].get('server_checklist') or []] == ["the film's world"]   # design/91 N9: only the world line
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'k2', 'element_id': 'E1', 'name': 'wall', 'kind': 'isolated', 'subject': 'the wall', 'prompt': 'A wall section.', 'shot_id': 'DG1'})
    lines = {l['check']: l for l in saved(store)['references'][out['reference_id']]['server_checklist']}
    assert lines['unknown: cavity width']['weight'] == 'must' and 'no figure' in lines['unknown: cavity width']['pass_when']
    assert lines['label: illustrative, not to scale']['weight'] == 'must'
    assert lines['size: leaf thickness 110 mm']['weight'] == 'should' and '110 mm' in lines['size: leaf thickness 110 mm']['pass_when']
