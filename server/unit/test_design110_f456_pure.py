"""design/110 F4, F5, F6. F4: each state lists its movable objects with counts and places; the counts agree with the action; the server composes
the inventory line into start and end prompts and the check counts. F5: tools are props of the shot with a holder and an end (in hand, set down,
carried out); the same tool sentence goes into start, end and motion text; the end picture and the take are checked. F6: every subject state's
facing is a heading (landmark, frame edge, the side toward the camera); the prompts carry it; a flipped heading fails; secondary living things get
their own small change. The server appends what it composes to a keyframe's prompt when the writer left it out."""
import copy
import json
import types
from fractions import Fraction

import pytest

from app import image_check as IC, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from app.video_providers import motion_text
from test_design101_pure import take_store
from test_design106_pure import revise_start, start_store
from test_design91_b1_pure import Video, st, subject, video
from test_visuals_pure import GAPS, plan, shot as pshot
from test_visuals_stage_pure import RUN, USER, FakeConn, g, saved

HEAD = {'landmark_id': 'L1', 'edge': 'right', 'camera_side': 'left side'}


def rich(sid='VS1', a=0, b=500):
    """A video shot with a tool, movable bricks and a secondary cow."""
    sh = video(sid, a, b, [(a, (a + b) // 2, 3), ((a + b) // 2, b, 3)])
    m = sh['subjects'][0]
    for state in (m['start'], m['beats'][0]['start']):
        state['holding'] = ['TROWEL']
        state['objects'] = [{'element_id': 'BRICK', 'count': 2, 'place': {'landmark_id': 'L1', 'relation': 'on', 'amount': 0, 'unit': 'hand'}}]
    for state in (m['beats'][0]['end'], m['beats'][1]['start']):
        state['holding'] = ['TROWEL']
        state['objects'] = [{'element_id': 'BRICK', 'count': 3, 'place': {'landmark_id': 'L1', 'relation': 'on', 'amount': 0, 'unit': 'hand'}}]
    for state in (m['end'], m['beats'][1]['end']):
        state['holding'] = []
        state['objects'] = [{'element_id': 'BRICK', 'count': 4, 'place': {'landmark_id': 'L1', 'relation': 'on', 'amount': 0, 'unit': 'hand'}}]
    sh['changes'] = [{'what': 'two more bricks on the wall, set by the mason', 'beat_id': 'B2'}, {'what': 'the trowel set down on the course', 'beat_id': 'B2'}]
    sh['props'] = [{'element_id': 'TROWEL', 'holder': 'E1', 'start': {'landmark_id': 'L1', 'relation': 'in the hand above', 'amount': 1, 'unit': 'hand'},
                    'end': {'where': 'set_down', 'position': {'landmark_id': 'L1', 'relation': 'on the top course of', 'amount': 2, 'unit': 'bricks'}}}]
    cow = {'element_id': 'COW', 'role': 'background', 'screen_position': 'right', 'behaviour': 'holds', 'hold_reason': 'it grazes', 'beats': [],
           'start': {**st('grazing'), 'position': {'landmark_id': 'L1', 'relation': 'to the right of', 'amount': 4, 'unit': 'body-lengths'}},
           'end': {**st('grazing'), 'position': {'landmark_id': 'L1', 'relation': 'to the right of', 'amount': 3, 'unit': 'body-lengths'}}}
    sh['subjects'].append(cow)
    sh['element_ids'] = ['E1', 'TROWEL', 'BRICK', 'COW']
    return sh


def doc_with(*shots):
    d = plan(list(shots))
    d['elements'] += [{'id': 'TROWEL', 'name': 'Pointing trowel', 'kind': 'object', 'identity': 'exact', 'requirements': 'a steel trowel with a wooden handle'},
                      {'id': 'BRICK', 'name': 'Red brick', 'kind': 'object', 'identity': 'representative', 'requirements': 'a fired brick'},
                      {'id': 'COW', 'name': 'Cow', 'kind': 'animal', 'identity': 'representative', 'requirements': 'a village cow'}]
    d['elements'][0].update(kind='person', name='Mason')
    return d


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def broken(mutate):
    d = doc_with(rich(), pshot('VS2', 500, 1000, 'video'))
    mutate(d['gaps'][0]['scenes'][0]['shots'][0])
    return d


# ---------- the plan check ----------

def test_the_plan_check_holds_the_counts_the_props_and_the_headings_to_account():
    check(doc_with(rich(), pshot('VS2', 500, 1000, 'video')))
    with pytest.raises(ValueError, match='BRICK goes from 2 to 4'):
        check(broken(lambda sh: sh.__setitem__('changes', [{'what': 'the trowel set down', 'beat_id': 'B2'}])))
    with pytest.raises(ValueError, match='TROWEL is held but has no props entry'):
        check(broken(lambda sh: sh.__setitem__('props', [])))
    with pytest.raises(ValueError, match='set down needs its position'):
        check(broken(lambda sh: sh['props'][0].__setitem__('end', {'where': 'set_down'})))
    with pytest.raises(ValueError, match='carried out needs its cause'):
        check(broken(lambda sh: sh['props'][0].__setitem__('end', {'where': 'carried_out'})))
    with pytest.raises(ValueError, match='facing is a heading'):
        check(broken(lambda sh: sh['subjects'][0]['start'].__setitem__('facing', 'the wall') or sh['subjects'][0]['beats'][0]['start'].__setitem__('facing', 'the wall')))
    with pytest.raises(ValueError, match='heading names a landmark of the scene'):
        check(broken(lambda sh: sh['subjects'][1]['start'].__setitem__('facing', {**HEAD, 'landmark_id': 'L9'})))
    with pytest.raises(ValueError, match='COW is a living thing that stands still'):
        check(broken(lambda sh: sh['subjects'][1].__setitem__('end', copy.deepcopy(sh['subjects'][1]['start']))))
    with pytest.raises(ValueError, match='objects name elements'):
        check(broken(lambda sh: sh['subjects'][0]['end']['objects'].__setitem__(0, {'element_id': 'NOPE', 'count': 1, 'place': {'landmark_id': 'L1', 'relation': 'on', 'amount': 0, 'unit': 'hand'}})
                     or sh['subjects'][0]['beats'][1]['end']['objects'].__setitem__(0, {'element_id': 'NOPE', 'count': 1, 'place': {'landmark_id': 'L1', 'relation': 'on', 'amount': 0, 'unit': 'hand'}})))
    still = {**pshot('IM1', 0, 500, 'image'), 'subjects': [{**subject((0, 250, 3)), 'start': {**st('0 laid'), 'facing': 'the wall'}}]}
    still['subjects'][0]['beats'][0]['start'] = still['subjects'][0]['start']
    check(doc_with(still, pshot('VS2', 500, 1000, 'video')))   # a still's subject keeps free facing


# ---------- what the server composes ----------

def test_the_server_composes_the_inventory_the_tool_sentence_and_the_headings():
    d = doc_with(rich())
    scene, sh = d['gaps'][0]['scenes'][0], d['gaps'][0]['scenes'][0]['shots'][0]
    inv = VS.inventory_line(d, scene, sh, 'start')
    assert inv == 'Inventory, exactly: Red brick × 2 on the table; Pointing trowel × 1 in E1\'s hands. Nothing else of these kinds in frame; nothing rests on top of the stack.'
    assert VS.inventory_line(d, scene, sh, 'end') == 'Inventory, exactly: Red brick × 4 on the table; E1 holds nothing. Nothing else of these kinds in frame; nothing rests on top of the stack.'
    tools = VS.tool_lines(d, scene, sh, 'start')
    assert tools == ["The same Pointing trowel: it keeps its shape, size, colour and handle (where it has one) in every picture it appears in; E1 holds nothing else; no second one appears; it is fully inside the frame. "
                     'At the start it is in the hand above the table, 1 hand from it.']
    assert VS.tool_lines(d, scene, sh, 'end')[0].endswith('At the end it is set down on the top course of the table, 2 bricks from it.')
    assert VS.tool_lines(d, scene, sh, 'motion')[0].endswith('By the end it is set down on the top course of the table, 2 bricks from it; it never changes into another thing and never simply disappears.')
    heads = VS.heading_lines(scene, sh, 'end')
    assert heads[0] == 'Heading of E1: front toward the table at the right edge; the left side faces the camera; it must not turn, reverse or show its other side.'
    assert heads[1] == 'COW has moved at least one body-length toward the table and turned a little; it does not stand where it stood in the start.'
    turned = copy.deepcopy(sh)
    turned['changes'].append({'what': 'E1 turns to the stack', 'beat_id': 'B2'})
    turned['subjects'][0]['end']['facing'] = {**HEAD, 'edge': 'left'}
    assert VS.heading_lines(scene, turned, 'end')[0] == 'Heading of E1: it turns, as the change says; at the end its front is toward the table at the left edge; the left side faces the camera.'
    block = VS.composed_block(d, scene, sh, 'start')
    assert block.startswith('E1: about to') and 'Heading of E1' in block and 'The same Pointing trowel' in block and block.rstrip().endswith('nothing rests on top of the stack.')
    assert 'Because E1 has laid one brick' in VS.composed_block(d, scene, sh, 'end')


def test_the_picture_lines_count_the_inventory_keep_the_tool_and_the_heading():
    d = doc_with(rich())
    scene, sh = d['gaps'][0]['scenes'][0], d['gaps'][0]['scenes'][0]['shots'][0]
    start = VS.picture_rule_lines(d, scene, sh, 'start')
    assert [l['check'] for l in start] == ['inventory'] and 'Red brick × 2' in start[0]['pass_when'] and start[0]['weight'] == 'must'
    end = VS.picture_rule_lines(d, scene, sh, 'end')
    assert [l['check'] for l in end] == ['inventory', 'same tool', 'heading kept']
    assert 'set down on the top course of the table, 2 bricks from it' in end[1]['pass_when'] and 'same landmark and shows the same side as in Image 1' in end[2]['pass_when']
    assert VS.picture_rule_lines(d, scene, {**sh, 'subjects': [], 'props': []}, 'end') == []


# ---------- the prompts get the block; the take gets its lines ----------

def test_the_server_appends_its_block_to_a_keyframe_prompt_once_and_never_to_a_fix():
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    row = saved(store)['references'][rid]
    p = row['generation']['prompt']
    assert p.count('E1: about to lays one brick') == 1 and p.startswith('Image 1 is the old start') and 'Heading of E1' in p
    again = revise_start(store, role='start', request_id='r-again', prompt='Image 1 is the old start; the labourer at the stack.\n' + VS.composed_block(
        json.loads(store.files['run-1/visuals/plan-v1.json'])['document'], *VS.locate(store, saved(store), 'VS1')[2:], 'start'))
    assert saved(store)['references'][again['reference_id']]['generation']['prompt'].count('E1: about to lays one brick') == 1   # already there: not twice
    assert [l['check'] for l in row['server_checklist'] if l['check'] in ('inventory', 'not yet done')] == ['not yet done']   # no objects in this fixture: no inventory line


def test_a_take_carries_the_tool_and_heading_lines_into_the_motion_text_and_the_check(monkeypatch, tmp_path):
    store, doc = take_store()
    sh = doc['gaps'][1]['scenes'][0]['shots'][0]
    sh['subjects'][0]['start']['holding'] = sh['subjects'][0]['beats'][0]['start']['holding'] = ['TROWEL']
    sh['props'] = [{'element_id': 'TROWEL', 'holder': 'E1', 'start': {'landmark_id': 'L2', 'relation': 'in the hand above', 'amount': 1, 'unit': 'hand'}, 'end': {'where': 'in_hand'}}]
    doc['elements'].append({'id': 'TROWEL', 'name': 'Pointing trowel', 'kind': 'object', 'identity': 'exact', 'requirements': 'a trowel'})
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    from test_visuals_stage_pure import accepted
    s['accepted'] = accepted(doc)
    s['bindings']['VS1']['gap_digest'] = s['accepted']['G2']['digest']
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    monkeypatch.setattr(VS, '_gemini_transport', lambda: None)
    out = VS.prepare_take(store, USER, RUN, [], {'shot_id': 'VS1', 'motion_prompt': 'he lays one brick', 'subject_reconciliation': {'E1': 'the mason'}, 'start_image': 'R1', 'end_image': 'R2',
                                                 'continuity_notes': 'the wall'})
    record = json.loads(store.files[saved(store)['preparations']['VS1']['key']])
    assert record['tool_lines'][0].startswith('The same Pointing trowel') and record['heading_lines'][0].startswith('Heading of E1')
    text = motion_text(record)
    assert 'The same Pointing trowel' in text and 'Heading of E1' in text and text.index('Heading of E1') < text.index('In a single unbroken scene')
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: 'k')))
    video_path = tmp_path / 'o.mp4'
    video_path.write_bytes(b'mp4')
    rec = IC.run_take_check({'motion_prompt': 'm', 'tool_lines': record['tool_lines'], 'heading_lines': record['heading_lines']}, video_path, 'a' * 64, Video)
    assert [l['check'] for l in rec['lines']][-2:] == ['tool kept', 'heading kept'] and len(rec['lines']) == 8
    assert len(IC.run_take_check({'motion_prompt': 'm'}, video_path, 'a' * 64, Video)['lines']) == 6
