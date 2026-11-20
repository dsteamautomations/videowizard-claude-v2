"""Fix set, the critic's points (SK, 19 Nov 2026), on the fixture with the shape of a real step 6 session.

1: a comparison that turns ready between the upload and the verdict is judged as it stood at the upload (a note for this verdict, due after).
2: an empty parts file stands only when nothing is shown by two or more drawings. 3: a `with` mark naming an id that never was a drawn shot is
refused at the upload; a shot cut from the plan stays closed. 4: the labels gate asks every `carries_text` shot again and says the way out.
5: a drawing being redone is not due for a comparison on its old project. 6: the round's list also names the musts that passed, answered only
when the upload broke one. 7: the still end-frames of a chain follow one another on the approvals; the motion waits for the earlier project; an
earlier still replaced later marks the next still to be made again. 8: depth words in a still's prompt. 9: the plan check's word lists.
10, 11: the still-prompts helper lists folders; the guard lets every helper the texts name through (plugin/tests/test_fixset4.py). Without a database."""
import json
import sys
from pathlib import Path

import pytest

from app import font_sample, library, pictures as P, visuals_stage as VS
from app.errors import Problem
from step6_shape import RULES, answers, build, load, upload, verdict
from test_design221_p1_pure import NEW, edit_plan, edit_session
from test_design221_p3c_pure import still_verdict
from test_design221_p4_pure import plan_of
from test_fixset2_pure import ABOVE, ALL_OK, SAME, SECTION, STILL_OK, approve, bound, comparing, drawn, frame, rendered, shots_of, still, warnings
from test_fixset3_pure import bare, now_job
from test_visuals_stage_pure import USER, accepted, g, saved

ROOT = Path(__file__).resolve().parents[2]
UNDER = ('part-block-under', 'part-base')   # what D3 places


@pytest.fixture(autouse=True)
def drawn_picture(monkeypatch):
    """The parts picture is drawn by Chromium on the server; here it is faked."""
    monkeypatch.setattr(font_sample, 'render', lambda html: b'\x89PNGparts')


def alone(store):
    """D4 as a drawing of its own (it returns to no other), so its still does not wait on D1's."""
    edit_plan(store, lambda d: shots_of(d, 1)[0].pop('return_of'))
    return store


def cut(store, gap, n):
    """A shot leaves the plan the way it does on a run: a new plan version without it; the version before stays stored."""
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])
    gone = shots_of(doc['document'], gap).pop(n)['id']
    store.files['run-1/visuals/plan-v2.json'] = json.dumps(doc).encode('utf-8')
    edit_session(store, lambda s: (s['versions'].append({'version': 2, 'file': {'key': 'run-1/visuals/plan-v2.json'}, 'plan_digest': 'd2', 'warnings': []}),
                                   s.update(current='d2', accepted=accepted(doc['document']))))
    return gone


def line(store):
    return P.starts(P.expected(*plan_of(store), []))


# ---------- 1: a comparison that turns ready between the upload and the verdict ----------

def test_p1_a_still_whose_comparison_turned_ready_after_its_upload_is_judged_as_it_stood_at_the_upload():
    store = alone(load())
    out = upload(store, 'D1', *SECTION, still=True, rules=comparing('D4'))   # D4 has no approved still: the rule is left out of the still's list, no frame is saved
    assert f'must: {SAME}' not in out['still_rules'] and 'compare' not in out
    still(store, 'D4', ABOVE)
    approve(store, 'D4')   # D4's still is approved while D1's checker runs
    done = still_verdict(store, out['sha256'], answers(STILL_OK), shot='D1', key=frame('D1'))   # the checker answered the list it was given
    assert done['next'].startswith('The still end-frame passed') and done['failed'] == []
    approve(store, 'D1')
    after = upload(store, 'D1', *SECTION, rules=comparing('D4'), more='b {}')   # afterwards it is a must: the animated project is given D4's frame
    assert after['compare'] == [{'shot_id': 'D4', 'key': frame('D4')}]
    with pytest.raises(Problem, match=r'D1: the verdict leaves 1 rule\(s\) of the project without an answer, first: "The rods are the same four rods'):
        verdict(store, 'D1', after['sha256'], ALL_OK)


@pytest.mark.parametrize('said', [ALL_OK, {**ALL_OK, SAME: True}], ids=['the rule left out, as the list it was given', 'the rule answered without the frame'])
def test_p1_an_animated_project_whose_comparison_turned_ready_after_its_upload_is_bound_and_the_comparison_is_due_after(said):
    store = alone(load())
    still(store, 'D1', SECTION, comparing('D4'))
    approve(store, 'D1')
    up = upload(store, 'D1', *SECTION, rules=comparing('D4'), more='b {}')
    assert 'compare' not in up
    still(store, 'D4', ABOVE)
    approve(store, 'D4')   # approved while D1's checker runs
    out = verdict(store, 'D1', up['sha256'], said)   # an answer given without the frame is not the drawing's
    assert out['next'].startswith('Passed') and saved(store)['motion_bound']['D1'] == up['sha256']
    assert SAME not in [r['rule'] for r in saved(store)['motion_checks']['D1'][-1]['rules']]
    item = drawn(store, [rendered('D1')])['D1']
    assert item['state'] == 'being checked by Claude' and 'its comparison with D4 is due' in item['due']   # the existing due path
    with pytest.raises(Problem, match=r'D1: the verdict leaves 1 rule\(s\) of the project without an answer'):
        verdict(store, 'D1', up['sha256'], {'0': True})   # now it is asked
    assert build(store, 'D1')['compare'] == [{'shot_id': 'D4', 'key': frame('D4')}]
    assert verdict(store, 'D1', up['sha256'], {SAME: False})['failed'] == [SAME]   # and a fail is a failed must


def test_p1_the_same_project_uploaded_again_once_the_other_still_is_approved_is_given_the_frame():
    store = alone(load())
    still(store, 'D1', SECTION, comparing('D4'))
    approve(store, 'D1')
    up = upload(store, 'D1', *SECTION, rules=comparing('D4'), more='b {}')
    still(store, 'D4', ABOVE)
    approve(store, 'D4')
    again = upload(store, 'D1', *SECTION, rules=comparing('D4'), more='b {}')
    assert again['sha256'] == up['sha256'] and again['compare'] == [{'shot_id': 'D4', 'key': frame('D4')}]
    with pytest.raises(Problem, match=r'leaves 1 rule\(s\) of the project without an answer'):
        verdict(store, 'D1', up['sha256'], ALL_OK)   # this upload was given the frame: the rule is its must


# ---------- 2: an empty parts file ----------

EMPTY = b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'


def test_p2_an_empty_parts_file_is_refused_while_things_are_shown_by_two_or_more_drawings():
    store = load(parts=False)
    with pytest.raises(Problem) as e:
        g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', EMPTY))
    assert e.value.message == ('The parts file is empty, and these things are shown by two or more drawings: E1 Block (D1, D2, D3); E2 Rod (D1, D2, D4); E3 Base (D3, D4). '
                               'Draw each once as a shared part (one <symbol id="part-…"> each) and upload the file again; an empty file is only for a film where nothing repeats.')
    assert 'motion_parts' not in saved(store) and 'motion_parts_approved' not in saved(store)   # nothing stands, nothing is approved


def test_p2_an_empty_parts_file_stands_with_no_card_when_nothing_repeats():
    store = load(parts=False)
    edit_plan(store, lambda d: [s.update(element_ids=ids) for s, ids in zip(shots_of(d)[:3] + shots_of(d, 1)[:1], (['E1'], ['E2'], ['E3'], []))])
    out = g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', EMPTY))
    assert out['parts'] == [] and VS.parts_ready(saved(store))


# ---------- 3: a `with` mark that names no drawn shot ----------

def test_p3_a_with_mark_naming_an_id_that_never_was_a_drawn_shot_is_refused_at_the_upload():
    store = load()
    with pytest.raises(Problem) as e:
        upload(store, 'D1', *SECTION, still=True, rules=comparing('D-4'))
    assert e.value.message == ('D1: the rule "The rods are the same four rods as in the other drawing." compares with D-4, which is not a drawn shot of this plan and '
                               'was in no earlier version of it. The drawn shots are D1, D2, D3, D4: correct the id in the rule\'s mark (`with <shot id>`) in rules.md, '
                               'then upload again.')
    assert not saved(store).get('motion_projects')   # nothing is stored: the must is not dropped
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    with pytest.raises(Problem, match='compares with D-4, which is not a drawn shot of this plan'):
        upload(store, 'D1', *SECTION, rules=comparing('D-4'), more='b {}')   # the animated project too
    assert upload(store, 'D1', *SECTION, rules=comparing('part-arrow'), more='b {}')['sha256']   # a shared part's id: a plain must, as before


def test_p3_a_shot_that_was_in_an_earlier_plan_version_and_was_cut_stays_closed():
    store = load()
    sha, _ = bound(store, 'D1', SECTION, comparing('D4'))
    assert cut(store, 1, 0) == 'D4'
    item = drawn(store, [rendered('D1')])['D1']
    assert item['due'] == 'D1: its comparison with D4 is closed (1 rule): D4 is no drawn graphic of the plan now.'
    again = upload(store, 'D1', *SECTION, rules=comparing('D4'), more='c {}')   # D4 was a drawn shot of version 1: accepted, and closed
    assert verdict(store, 'D1', again['sha256'], ALL_OK)['next'].startswith('Passed')


# ---------- 4: the labels gate ----------

def test_p4_a_carries_text_shot_with_a_corner_note_or_a_logo_and_no_labels_is_asked_and_told_the_way_out():
    for over in ({}, {'drawing_spec': None, 'element_ids': ['E1', 'E2', 'E9']}):   # a corner note (D2's spec is illustrative); a logo picture
        store = load()

        def change(d):
            d['elements'].append({'id': 'E9', 'name': "The maker's logo", 'kind': 'graphic', 'identity': 'exact', 'requirements': 'the logo file'})
            bare(d, 'D2', **over)
        edit_plan(store, change)
        with pytest.raises(Problem) as e:
            build(store, 'D1')   # the server cannot know the shot's own words: forgotten labels and "no words" look the same
        assert 'D2 carries text and has no scene_motion.labels' in e.value.message
        assert e.value.message.endswith(' If the only text of a shot is the corner note or a logo picture, set carries_text to false on that shot in the plan.')
        edit_plan(store, lambda d: shots_of(d)[1].update(carries_text=False))
        assert build(store, 'D1')['brief']   # the way out
    assert not hasattr(VS, 'note_or_logo_only')


# ---------- 5: a comparison that comes due while the drawing is being redone ----------

def test_p5_a_drawing_being_redone_is_not_due_for_a_comparison_on_its_old_project():
    store = load()
    sha, _ = bound(store, 'D1', SECTION, comparing('D4'))
    jobs = [now_job('D1')]
    upload(store, 'D1', *SECTION, still=True, rules=comparing('D4'), more='redrawn {}')   # a new still: unbound, being redone (A3.5)
    still(store, 'D4', ABOVE)
    approve(store, 'D4')
    item = drawn(store, jobs)['D1']
    assert item['state'] == 'being redone' and 'is due' not in item.get('due', '')   # not "being checked by Claude" on the old project
    with pytest.raises(Problem) as e:
        verdict(store, 'D1', sha, {SAME: True})   # an answer on the old project binds nothing
    assert e.value.message == ('D1 is being redone: a newer upload of it came after this project, so this project is not the drawing any more and no verdict is taken on it. '
                               'A comparison with another drawing is judged on the new upload.')
    assert 'D1' not in saved(store)['motion_bound']
    new = upload(store, 'D1', *SECTION, still=True, rules=comparing('D4'), more='redrawn again {}')   # the comparison is the new upload's must
    assert new['compare'] == [{'shot_id': 'D4', 'key': frame('D4')}] and f'must: {SAME}' in new['still_rules']


# ---------- 6: the round's list: the open rules, then the musts that passed ----------

def test_p6_the_rounds_list_names_the_musts_that_passed_and_a_false_on_one_is_a_failed_must():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    first = upload(store, 'D1', *SECTION, more='b {}')
    assert 'round_passed' not in first
    verdict(store, 'D1', first['sha256'], {'0': True, '1': False, '2': False, '3': True, '4': True, '5': True})
    again = upload(store, 'D1', *SECTION, more='c {}')
    assert again['round_rules'] == [f'must: {RULES[1]}', f'should: {RULES[2]}']   # the open rules: each is answered
    assert again['round_passed'] == [f'must: {RULES[0]}', f'must: {RULES[3]}', f'must: {RULES[4]}']   # the musts that passed before (a passed should is not listed)
    assert 'below them are the 3 musts that passed before: the checker answers one of those only when this upload broke it' in again['next']
    out = verdict(store, 'D1', again['sha256'], {'1': True, '2': True, '3': False}, rnd=2)   # the fix broke a must that had passed
    assert out['failed'] == [RULES[3]] and 'D1' not in saved(store).get('motion_bound', {})
    third = upload(store, 'D1', *SECTION, more='d {}')
    assert third['round_rules'] == [f'must: {RULES[3]}'] and third['round_passed'] == [f'must: {RULES[0]}', f'must: {RULES[1]}', f'must: {RULES[4]}']


# ---------- 7: the stills of a chain ----------

def test_p7_the_still_end_frames_of_a_chain_are_all_approved_before_any_motion():
    store = load()
    with pytest.raises(Problem) as e:
        build(store, 'D2')
    assert e.value.message == ("D2 continues from D1: its still end-frame opens on D1's approved still end-frame, and D1 has none now: have D1's still built, checked "
                               'and approved first, then brief D2.')
    d1, _ = still(store, 'D1', SECTION)
    assert line(store) == 'Waiting on another drawing: D2 on D1; D3 on D2; D4 on D1.'   # D1's card is the operator's turn
    approve(store, 'D1')
    assert line(store) == ('Start now, together in one message: the builders of the still end-frames of D2, D4 (2). The motion of D1 comes after the still end-frames. '
                           'Waiting on another drawing: D3 on D2.')
    got = build(store, 'D2')
    assert got['continues'] == {'shot_id': 'D1', 'project_key': f'run-1/visuals/motion/projects/{d1}.zip', 'opens_on_key': frame('D1')}   # the approved still: its frame and its files
    assert ("Its still end-frame comes first, built from D1's approved still end-frame (from-D1/opens-on.png, with that still's files); the motion is started only "
            "after D1's project has passed its fact check.") in got['brief']
    still(store, 'D2', SECTION, more='two {}')
    approve(store, 'D2')
    assert build(store, 'D3')['continues']['opens_on_key'] == frame('D2')
    still(store, 'D3', UNDER)
    approve(store, 'D3')
    still(store, 'D4', ABOVE)
    approve(store, 'D4')
    s = saved(store)
    assert all(VS.still_approved(s['motion_stills'][sid]) for sid in ('D1', 'D2', 'D3', 'D4')) and all(p.get('still') for p in s['motion_projects'].values())   # no motion yet
    assert line(store) == 'Start now, together in one message: the builders of the motion of D1 (1). Waiting on another drawing: D2 on D1; D3 on D2; D4 on D1.'


def test_p7_the_motion_of_a_continuing_drawing_is_refused_until_the_earlier_project_passed():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    still(store, 'D2', SECTION, more='two {}')
    told = VS.still_answer(store, USER, NEW, [], ['D2'], True, 'Approve')['for_the_assistant']
    assert told.endswith("D2 continues from D1: its motion waits until D1's project has passed its fact check; then run `vw motion brief --shot D2` again (it brings "
                         "D1's project) and build D2's motion on it.")
    with pytest.raises(Problem, match='D2 continues from D1: build and pass D1 first'):
        build(store, 'D2')   # its still is approved: the brief is now for its motion
    with pytest.raises(Problem, match='D2 continues from D1: build and pass D1 first'):
        upload(store, 'D2', *SECTION, more='two b {}')   # and an animated project built without D1's project is not taken
    sha = upload(store, 'D1', *SECTION, more='b {}')['sha256']
    verdict(store, 'D1', sha, ALL_OK)
    assert build(store, 'D2')['continues'] == {'shot_id': 'D1', 'sha256': sha, 'project_key': f'run-1/visuals/motion/projects/{sha}.zip', 'last_frame_key': '', 'last_second': 3.96}
    assert upload(store, 'D2', *SECTION, more='two b {}')['sha256']
    assert line(store).startswith('Start now, together in one message: the builders of the still end-frames of D3, D4 (2); the checkers of D2 (1).')


def test_p7_an_earlier_still_replaced_later_marks_the_next_still_to_be_made_again():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    still(store, 'D2', SECTION, more='two {}')
    approve(store, 'D2')
    assert saved(store)['motion_stills']['D2']['opens_on'] == saved(store)['motion_stills']['D1']['png']   # the picture D2's still opens on
    new = upload(store, 'D1', *SECTION, still=True, more='wider {}')['sha256']   # the operator asked for a change at the head of the chain
    item = drawn(store)['D2']
    assert item.get('waits_on') == 'D1' and 'turn' not in item   # at once: D2's still waits for D1's new still
    with pytest.raises(Problem) as e:
        upload(store, 'D2', *SECTION, more='two b {}')
    assert e.value.message == ("D2: D1's still end-frame, which D2's still opens on, was replaced since D2's still was built. Once D1's new still is approved, run "
                               "`vw motion brief --shot D2` again and build D2's still again from it (`vw motion upload --shot D2 --still`).")
    still_verdict(store, new, answers(STILL_OK), shot='D1', key=frame('D1'), png=b'\x89PNGwider')
    assert drawn(store)['D2'].get('waits_on') == 'D1'   # D1's new still waits for the operator
    approve(store, 'D1')
    assert drawn(store)['D2']['turn'] == 'still' and 'the builders of the still end-frames of D2, D4 (2)' in line(store)   # made again
    assert build(store, 'D2')['continues']['opens_on_key'] == frame('D1')
    still(store, 'D2', SECTION, more='two again {}', png=b'\x89PNGtwo')
    approve(store, 'D2')
    item = drawn(store)['D2']
    assert saved(store)['motion_stills']['D2']['opens_on'] == saved(store)['motion_stills']['D1']['png'] and item.get('waits_on') == 'D1'   # now only its motion waits, on D1's project
    with pytest.raises(Problem, match='D2 continues from D1: build and pass D1 first'):
        upload(store, 'D2', *SECTION, more='two b {}')


def test_p7_the_same_picture_made_again_at_the_head_of_the_chain_marks_nothing():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    still(store, 'D2', SECTION, more='two {}')
    approve(store, 'D2')
    still(store, 'D1', SECTION, more='same picture {}')   # its parts changed elsewhere: the same picture, its approval stays
    s, plan = plan_of(store)
    assert VS.still_approved(s['motion_stills']['D1']) and not VS.opens_changed(s, 'D1', s['motion_stills']['D2'])


# ---------- 8: depth words in a still's prompt ----------

DEPTH = ('Rows of tile stacks recede along the aisle; the further stacks and the shelves fall into shadow.', 'Further back, pallets wait by the door.',
         'A second figure stands further away, out of focus.', 'The figure is further from camera than the mixer.')
PLACED = ('Put the cup further left.', 'Move the label closer to the edge.', 'The crate stands closer to the corner.', 'The cup sits further right.')


def test_p8_closer_and_further_that_describe_depth_pass_in_a_stills_prompt_and_a_placement_is_refused():
    for said in DEPTH:
        assert library.check_prompt(said, picture=True) is None, said
        with pytest.raises(ValueError, match='with no landmark and measured distance'):
            library.check_prompt(said)   # a take's motion prompt and an end prompt: as before
    for said in PLACED:
        with pytest.raises(ValueError, match='with no landmark and measured distance'):
            library.check_prompt(said, picture=True)
    assert library.check_prompt('Put the cup two hands further left.', picture=True) is None   # a measured placement, as before


# ---------- 9: the plan check's word lists ----------

def moves(store, words, flow=None):
    edit_plan(store, lambda d: shots_of(d)[0].update(information_progression=words, **({'camera_flow': flow} if flow else {})))
    return [w['message'] for w in warnings(store, 'camera_words')]


def test_p9_a_camera_move_is_flagged_only_when_the_camera_or_the_view_moves():
    store = load()
    for said in ('A pan with two eggs sits on the stove.', 'The cover pulls back to show the bars.', 'The lid tilts up and steam rises.', 'The belt tracks along the rollers.'):
        assert moves(store, said) == [], said   # the things move, not the camera
    for said, word in (('The camera pushes into the joint.', 'pushes into'), ('The camera moves closer to the joint.', 'moves closer'), ('The view pans.', 'pans'),
                       ('We orbit around the column.', 'orbit'), ('A slow push in on the block.', 'push in'), ('Zoom out to the whole wall.', 'Zoom out'),
                       ('A tracking shot along the rods.', 'tracking shot'), ('The frame pans across the rods.', 'pans across')):
        got = moves(store, said)
        assert len(got) == 1 and f'("{word}")' in got[0] and 'its camera flow is Fixed' in got[0], said
    assert moves(store, 'The camera pushes into the joint.', flow='step_closer') == []   # a flow that allows the move, as before
    assert len(moves(store, 'The view pans.', flow='step_closer')) == 1


def test_p9_a_large_end_change_is_flagged_only_for_the_frame_as_a_whole():
    store = load()

    def big(what):
        edit_plan(store, lambda d: shots_of(d, 1)[1].update(end_state_exact=True, changes=[{'what': what, 'beat_id': 'B1'}]))
        return warnings(store, 'end_change_large')
    for said in ('The whole label fades in.', 'The entire arrow turns red.', 'the rod is set down on the base'):
        assert big(said) == [], said
    for said in ('the whole frame is plastered wall now', 'most of the picture turns dark', 'three quarters of the frame is laid floor', 'the entire scene is flooded',
                 'the whole room is painted'):
        assert len(big(said)) == 1, said


# ---------- the texts ----------

def visuals():
    return next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')


def test_the_served_text_and_the_helpers_say_it_and_the_older_ways_are_named():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import fixset4_wording as W
    stage = visuals()
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    texts = {p['name']: p['text'] for p in stage['parts']}
    was = {p['name']: p['text'] for p in W.before(stage)['parts']}
    for where, old, new in W.PAIRS:
        assert texts[where].count(new) == 1 and was[where].count(old) == 1 and new not in was[where], old[:50]
    assert 'a shot whose only text they are has `carries_text: false`' in texts['plan'] and 'is not asked for labels' not in texts['plan']   # point 4
    later = texts['later']
    for said in ('the musts that passed before', 'once that shot\'s still end-frame is approved', 'opens-on.png', 'the still to make again'):
        assert said in later, said
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').replace('\r\n', '\n').count(new) == 1, (file, old[:50])
    helper = (ROOT / 'plugin' / 'agents' / 'vw-still-prompts.md').read_text(encoding='utf-8').replace('\r\n', '\n')
    assert 'tools: Read, Write, Glob\nmodel: opus\neffort: high\n---\n' in helper and 'list them with Glob' in helper   # point 10: it can list the folder it is told to read
    assert 'If a rule file you were named cannot be read, say so in your answer; never guess its rules.' in helper
    check = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert 'answer one of those only when this upload broke it' in check and 'opens-on.png' in check
    assert 'opens-on.png' in (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    everything = stage['prompt'] + ''.join(p['text'] for p in stage['parts'])
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired and s not in everything for s in W.RETIRED)
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('fixset3(prompt, parts)') < split.index('fixset4(prompt, parts)')
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "out.get('round_passed')" in vw and "c.get('opens_on_key')" in vw
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    assert all(f'| {n} |' in log for n in range(254, 264))   # the older way of each change
    for name in ('left_out', 'PARTS_EMPTY', 'ever_drawn', 'note_or_logo_only', 'round_passed', 'opens_on', 'PLACING', 'CAMERA_SUBJECT', 'VW_HELPERS'):
        assert name in log.split('| 254 |', 1)[1], name
