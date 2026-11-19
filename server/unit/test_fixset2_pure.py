"""Fix set phase 2 (SK, 19 Nov 2026): what cost the most time on VW-24's redo of step 6, on the fixture with the shape of a real session.

A1.1: the shared parts cover every shape that repeats, also one that is no thing of the plan (it names its drawings; their briefs list it; their
uploads place it); a film where no shape repeats. A1.2: a rule that compares with another drawing is a must while that drawing's approved still
end-frame exists; with none it waits as a note and never holds; it comes due when the other still is approved; closed only when the other drawing
leaves the plan. A1.3: the still cards in the order of the film. A1.4: the next-step line names what can start now and what waits on what.
A1.6: a later round is given the rules the round before left open, and a pass stands only for the same rules and brief lines. M1, M2, M4: the plan
check. M3: the labels gate names every shot. c1, c2: a still never loops on "not seen" and passes with no rule a still can show. Without a database."""
import json
import sys
from pathlib import Path

import pytest

from app import chat_flow as C, font_sample, motion as M, pictures as P, visuals_stage as VS
from app.errors import Problem
from step6_shape import RULES, answers, build, chat, load, parts_svg, rules_text, upload, verdict
from test_design130_p1_pure import FakeConn
from test_design221_p1_pure import NEW, edit_plan, edit_session
from test_design221_p3c_pure import still_verdict
from test_design221_p4_pure import V2, drawn_job, plan_of
from test_visuals_stage_pure import USER, g, saved

ROOT = Path(__file__).resolve().parents[2]
SECTION = ('part-block-section', 'part-rod-end')   # what a drawing cut across places (D1, D2)
ABOVE = ('part-rod-grid', 'part-base')              # what D4, seen from above, places
SAME = 'The rods are the same four rods as in the other drawing.'
STILL_OK = {'0': True, '1': True}
ALL_OK = {str(n): True for n in range(6)}


@pytest.fixture(autouse=True)
def drawn_picture(monkeypatch):
    """The parts picture is drawn by Chromium on the server; here it is faked."""
    monkeypatch.setattr(font_sample, 'render', lambda html: b'\x89PNGparts')


def comparing(other, shows='still'):
    """rules.md of the fixture with one more rule, which compares this drawing with another one."""
    return rules_text() + f'7. must ({shows}, with {other}): {SAME}\n'


def frame(shot):
    return f'run-1/visuals/motion/tools/{shot}/0.png'


def approve(store, shot):
    next(i for i in chat(store, 'still end-frame') if shot in i['question'])['_run']('approve', 'Approve', '')


def still(store, shot, parts, rules=None, said=STILL_OK, png=b'\x89PNGend', more=''):
    sha = upload(store, shot, *parts, still=True, rules=rules, more=more)['sha256']
    return sha, still_verdict(store, sha, answers(said), shot=shot, key=frame(shot), png=png)


def bound(store, shot, parts, rules=None, said=ALL_OK):
    """One drawing through its still, the approval and its animated round."""
    still(store, shot, parts, rules)
    approve(store, shot)
    sha = upload(store, shot, *parts, rules=rules, more='b {}')['sha256']
    return sha, verdict(store, shot, sha, said)


def rendered(shot):
    """A ready render of the shot's drawing, made before any verdict of these tests."""
    return {**drawn_job('job-1', unit=shot), 'created_at': '2026-01-01T00:00:00+00:00'}


def drawn(store, jobs=()):
    return {i['id']: i for i in P.expected(*plan_of(store), list(jobs)) if i['kind'] == 'drawn'}


def warnings(store, kind):
    s = VS.session_of(store, NEW, [])
    return [w for w in VS.carried_warnings(s, NEW, VS.current_plan(store, s), []) if w['kind'] == kind]


def shots_of(doc, gap=0):
    return doc['gaps'][gap]['scenes'][0]['shots']


# ---------- A1.1: the shared parts cover every shape that repeats ----------

def test_a11_the_parts_helper_is_given_every_drawn_shots_spec_and_asked_for_every_shape_that_repeats():
    brief = g(lambda: VS.parts_brief(load(parts=False), NEW, []))['brief']
    for sid in ('D1', 'D2', 'D3', 'D4'):
        assert f'## {sid}' in brief and f'# Brief: drawn shot {sid}' in brief
    assert brief.count('Drawing spec, view') == 4   # every drawn shot's spec, not only those of the plan's things
    assert ('Shapes that are no thing of the plan repeat too: read every spec below and list first each shape that two or more drawings show, with the '
            'drawings that show it and its count where a spec gives one; then draw each once, and name on its symbol the drawings that show it '
            '(data-shots, from: D1, D2, D3, D4).') in brief
    assert 'that is an open choice: answer with it and the count you recommend' in brief


def test_a11_a_part_of_no_plan_thing_names_its_drawings_and_only_their_briefs_list_it():
    store = load(parts=False)
    svg = parts_svg().replace('<symbol id="part-arrow"', '<symbol id="part-arrow" data-shots="D1 D4"')
    out = g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', svg.encode('utf-8')))
    VS.parts_answer(store, USER, NEW, [], out['sha256'], True, 'Approve')
    arrow = next(p for p in saved(store)['motion_parts_approved']['parts'] if p['id'] == 'part-arrow')
    assert arrow['element'] == '' and arrow['shots'] == ['D1', 'D4']
    lists = lambda sid: 'part-arrow: Arrow' in VS.motion_brief(store, NEW, [], sid)['brief']
    assert lists('D1') and lists('D4') and not lists('D2') and not lists('D3')
    with pytest.raises(Problem) as e:
        upload(store, 'D1', *SECTION, still=True)   # a drawing its part names does not draw its own copy
    assert 'D1 shows Arrow but does not use its shared part: place part-arrow with <use href="#part-arrow">' in str(e.value)
    assert upload(store, 'D1', *SECTION, 'part-arrow', still=True)['sha256']
    with pytest.raises(Problem, match='part-arrow: data-shots names the drawn shots that show the part; D9 is none of them'):
        g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', svg.replace('D1 D4', 'D1 D9').encode('utf-8')))


def test_a11_a_part_that_names_no_drawing_is_listed_in_every_brief_as_before():
    store = load()   # the fixture's arrow: no thing of the plan, no data-shots (a parts file drawn before this release)
    assert all('part-arrow: Arrow' in VS.motion_brief(store, NEW, [], sid)['brief'] for sid in ('D1', 'D2', 'D3', 'D4'))
    assert upload(store, 'D1', *SECTION, still=True)['sha256']   # and no upload is held to it


def test_a11_a_film_where_no_shape_repeats_has_no_shared_parts_and_is_not_held():
    store = load(parts=False)
    with pytest.raises(Problem, match='their shared parts are drawn once, before any brief'):
        build(store, 'D1')
    out = g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'))
    assert out['parts'] == [] and out['next'].startswith('No shape repeats across the drawings: there are no shared parts')
    assert chat(store, 'parts') == [] and VS.parts_ready(saved(store))   # nothing to show: no card
    brief = build(store, 'D1')
    assert 'Use these parts' not in brief['brief'] and 'parts_key' not in brief
    _, problems = M.read_parts('<svg xmlns="http://www.w3.org/2000/svg"><defs/></svg>', set())   # a file that draws something but no part is still refused
    assert problems == ['the parts file has no <symbol id="part-…">: one symbol per shared part']


# ---------- A1.2: a rule that compares with another drawing ----------

def test_a12_the_rule_writer_marks_the_other_drawing_and_the_mark_is_not_in_the_rules_words():
    held = P.rules_of('1. must (still, with D4): It matches.\n2. should (motion, with D2): It follows.\n3. must (with part-arrow): It is the arrow.\n4. must (still): It is whole.\n')
    assert [(r['class'], r.get('shows'), r.get('with'), r['rule']) for r in held] == [
        ('must', 'still', 'D4', 'It matches.'), ('should', 'motion', 'D2', 'It follows.'), ('must', None, 'part-arrow', 'It is the arrow.'), ('must', 'still', None, 'It is whole.')]
    assert held[0]['id'] == P.rule_id('It matches.')
    store = load()
    s = saved(store)
    assert VS.comparing(s, VS.current_plan(store, s), held) == {
        held[0]['id']: {'with': 'D4', 'rule': 'It matches.', 'state': 'waits'}, held[1]['id']: {'with': 'D2', 'rule': 'It follows.', 'state': 'waits'}}   # a shared part is always there: a plain must


def test_a12_with_nothing_to_compare_with_the_rule_waits_as_a_note_and_the_drawing_is_bound():
    store = load()
    sha, out = bound(store, 'D1', SECTION, comparing('D4'))   # D4 is not started: no verdict answers the comparison
    assert out['next'].startswith('Passed') and saved(store)['motion_bound']['D1'] == sha
    assert SAME not in [r['rule'] for c in saved(store)['motion_checks']['D1'] for r in c['rules']]   # no answer is recorded for it
    item = drawn(store, [rendered('D1')])['D1']
    assert item['state'] == 'made and checked'
    assert item['due'] == "D1: its comparison with D4 waits until D4's still end-frame is approved (1 rule); D1 is not held by it."
    s, plan = plan_of(store)
    assert 'compare' not in build(store, 'D1') and P.complete([item]) is True


def test_a12_an_answer_given_while_nothing_exists_is_not_the_drawings():
    store = load()
    sha, out = bound(store, 'D1', SECTION, comparing('D4'), said={**ALL_OK, SAME: False})   # a checker that judged it all the same, with nothing to compare with
    assert out['next'].startswith('Passed') and out['failed'] == []


def test_a12_the_comparison_comes_due_when_the_other_still_is_approved_and_is_checked_then():
    store = load()
    sha, _ = bound(store, 'D1', SECTION, comparing('D4'))
    jobs = [rendered('D1')]
    still(store, 'D4', ABOVE)
    assert drawn(store, jobs)['D1']['state'] == 'made and checked'   # D4's still waits for the operator: nothing to compare with yet
    approve(store, 'D4')
    item = drawn(store, jobs)['D1']
    assert item['state'] == 'being checked by Claude' and 'job' not in item
    assert item['due'] == ("D1: its comparison with D4 is due (D4's still end-frame is approved): run `vw motion brief --shot D1` (it saves D4's frame in "
                           'work/motion/D1/with-D4/), give a fresh vw-motion-check helper the rule "' + SAME + '" with that frame and D1\'s last frame, and send '
                           'its verdict with the same round (1): a fail is a failed must of D1.')
    assert build(store, 'D1')['compare'] == [{'shot_id': 'D4', 'key': frame('D4')}]
    with pytest.raises(Problem, match=r'D1: the verdict leaves 1 rule\(s\) of the project without an answer, first: "The rods are the same four rods'):
        verdict(store, 'D1', sha, {'0': True})   # a verdict now answers it
    out = verdict(store, 'D1', sha, {SAME: True})   # the comparison alone, with the same round: the other passes stand
    assert out['next'].startswith('Passed') and saved(store)['motion_bound']['D1'] == sha
    last = saved(store)['motion_checks']['D1'][-1]['rules']
    assert len(last) == 7 and next(r for r in last if r['rule'] == SAME)['with_png'] == saved(store)['motion_stills']['D4']['png']
    item = drawn(store, jobs)['D1']
    assert item['state'] == 'made and checked' and 'due' not in item


def test_a12_a_comparison_that_fails_when_it_comes_due_is_a_failed_must_and_the_drawing_is_being_redone():
    store = load()
    sha, _ = bound(store, 'D1', SECTION, comparing('D4'))
    still(store, 'D4', ABOVE)
    approve(store, 'D4')
    out = verdict(store, 'D1', sha, {SAME: False})
    assert out['failed'] == [SAME] and 'D1' not in saved(store)['motion_bound']
    assert drawn(store, [rendered('D1')])['D1']['state'] == 'being redone'   # its old render no longer counts as made and checked


def test_a12_with_an_approved_still_to_compare_with_the_rule_is_a_must_from_the_start():
    store = load()
    bound(store, 'D1', SECTION)
    out = upload(store, 'D4', *ABOVE, still=True, rules=comparing('D1'))
    assert out['compare'] == [{'shot_id': 'D1', 'key': frame('D1')}] and "D1's approved still end-frame" in out['next']
    assert f'must: {SAME}' in out['still_rules']
    with pytest.raises(Problem, match=r'D4: the verdict leaves 1 rule\(s\) of the project without an answer, first: "The rods are the same four rods'):
        still_verdict(store, out['sha256'], answers(STILL_OK), shot='D4', key=frame('D4'))
    failed = still_verdict(store, out['sha256'], answers({**STILL_OK, SAME: False}), shot='D4', key=frame('D4'))
    assert failed['failed'] == [SAME] and failed['next'].startswith('1 rules failed on the still')


def test_a12_a_comparison_whose_other_drawing_is_cut_from_the_plan_is_closed_and_said():
    store = load()
    sha, _ = bound(store, 'D1', SECTION, comparing('D4'))
    edit_plan(store, lambda d: shots_of(d, 1).pop(0))   # D4 leaves the plan
    item = drawn(store, [rendered('D1')])['D1']
    assert item['state'] == 'made and checked'   # not held
    assert item['due'] == 'D1: its comparison with D4 is closed (1 rule): D4 is no drawn graphic of the plan now.'
    sha2 = upload(store, 'D1', *SECTION, rules=comparing('D4'), more='c {}')['sha256']
    assert verdict(store, 'D1', sha2, ALL_OK)['next'].startswith('Passed')   # and no later verdict is asked for it


def test_a12_a_drawing_redrawn_after_its_render_makes_the_comparison_wait_then_due_again():
    store = load()
    sha, _ = bound(store, 'D1', SECTION, comparing('D4'))
    jobs = [rendered('D1')]
    still(store, 'D4', ABOVE)
    approve(store, 'D4')
    verdict(store, 'D1', sha, {SAME: True})
    assert drawn(store, jobs)['D1']['state'] == 'made and checked'
    still(store, 'D4', ABOVE, png=b'\x89PNGredrawn', more='r {}')   # D4 is drawn again: its new still passed its check and waits for the operator
    item = drawn(store, jobs)['D1']
    assert item['state'] == 'made and checked' and 'its comparison with D4 waits' in item['due']
    approve(store, 'D4')
    item = drawn(store, jobs)['D1']
    assert item['state'] == 'being checked by Claude' and 'its comparison with D4 is due' in item['due']   # compared with the other picture: checked again
    assert verdict(store, 'D1', sha, {SAME: False})['failed'] == [SAME]


def test_a12_a_rule_list_written_before_the_mark_behaves_as_today():
    store = load()
    old = rules_text(marked=False) + f'7. must: {SAME}\n'
    still(store, 'D1', SECTION, old, said={'0': True})
    approve(store, 'D1')
    sha = upload(store, 'D1', *SECTION, rules=old, more='b {}')['sha256']
    out = verdict(store, 'D1', sha, {**ALL_OK, SAME: 'not seen'})   # nothing marks it: it holds the drawing until its frame is given, as on VW-24
    assert out['not_seen'] == [{'rule': SAME, 'need': 'a crop of the sill'}] and 'D1' not in saved(store).get('motion_bound', {})
    assert 'due' not in drawn(store)['D1']


# ---------- A1.3: the still cards in the order of the film ----------

def test_a13_several_still_cards_wait_in_the_order_of_the_film_and_are_answered_one_at_a_time():
    store = load()
    st = lambda n: {'sha256': n * 64, 'frame_key': f'k{n}', 'png': f'p{n}', 'parts': {}}
    edit_session(store, lambda s: s.update(motion_stills={'D4': st('4'), 'D3': st('3'), 'D1': st('1')}))   # checked in another order than the film's
    s, plan = plan_of(store)
    cards = [w for w in VS.waiting(s, plan, 'VW-1', []) if w['kind'] == 'still end-frame to approve']
    assert [w['item'] for w in cards] == ['D1', 'D3', 'D4']
    assert [i['question'].split(':')[0] for i in chat(store, 'still end-frame')] == ['D1', 'D3', 'D4']


# ---------- A1.4: what can start now, and what waits on what ----------

def test_a14_the_next_step_line_names_what_can_start_now_and_which_drawing_waits_on_which():
    store = load()
    line = lambda: P.starts(P.expected(*plan_of(store), []))
    waits = ' Waiting on another drawing: D2 on D1; D3 on D2; D4 on D1.'
    assert line() == 'Start now, together in one message: the builders of the still end-frames of D1 (1).' + waits
    sha = upload(store, 'D1', *SECTION, still=True)['sha256']
    assert line() == 'Start now, together in one message: the checkers of D1 (1).' + waits
    still_verdict(store, sha, answers(STILL_OK), shot='D1', key=frame('D1'))
    assert line() == waits.strip()   # its card is the operator's turn
    approve(store, 'D1')
    assert line() == 'Start now, together in one message: the builders of the motion of D1 (1).' + waits
    sha = upload(store, 'D1', *SECTION, more='b {}')['sha256']
    assert line() == 'Start now, together in one message: the checkers of D1 (1).' + waits
    verdict(store, 'D1', sha, {**ALL_OK, '1': False})
    assert line() == 'Start now, together in one message: the builders of the motion of D1 (1).' + waits   # a failed must: its redo
    verdict(store, 'D1', upload(store, 'D1', *SECTION, more='c {}')['sha256'], ALL_OK, rnd=2)
    assert line() == 'Start now, together in one message: the builders of the still end-frames of D2, D4 (2). Waiting on another drawing: D3 on D2.'


def test_a14_no_motion_is_named_while_a_still_end_frame_is_left_to_build_or_check():
    store = load()
    bound(store, 'D1', SECTION)
    still(store, 'D4', ABOVE)
    approve(store, 'D4')   # D4's motion could start; D2's still is not built yet
    line = P.starts(P.expected(*plan_of(store), []))
    assert line == ('Start now, together in one message: the builders of the still end-frames of D2 (1). The motion of D4 comes after the still end-frames. '
                    'Waiting on another drawing: D3 on D2.')


def test_a14_nothing_is_said_to_start_before_the_shared_parts_are_approved_and_the_line_is_in_the_next_step():
    assert P.starts(P.expected(*plan_of(load(parts=False)), [])) == ''
    store = load()
    edit_session(store, lambda s: s.update(round=V2))
    out = C.next_item(FakeConn([]), store, USER, NEW, [])
    assert 'Start now, together in one message: the builders of the still end-frames of D1 (1).' in out['then']
    assert 'Start now, together in one message' in VS.status(FakeConn([]), store, NEW, [])['step6']


# ---------- A1.6: what a later round answers ----------

def test_a16_a_later_round_is_given_only_the_rules_the_round_before_left_open():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    first = upload(store, 'D1', *SECTION, more='b {}')
    assert 'round_rules' not in first and 'rules-round.md' not in first['next']   # round 1: every rule of rules.md
    verdict(store, 'D1', first['sha256'], {'0': True, '1': False, '2': False, '3': True, '4': True, '5': True})
    again = upload(store, 'D1', *SECTION, more='c {}')
    assert again['round_rules'] == [f'must: {RULES[1]}', f'should: {RULES[2]}']   # the failed must and the failed should; no rule that passed
    assert 'The 2 rules the round before left open are in work/motion/D1/rules-round.md' in again['next']
    out = verdict(store, 'D1', again['sha256'], {'1': True, '2': True}, rnd=2)
    assert out['next'].startswith('Passed') and len(saved(store)['motion_checks']['D1'][-1]['rules']) == 6   # the passes before stand
    assert 'round_rules' not in upload(store, 'D1', *SECTION, more='d {}')   # after a clean verdict: nothing is left open


def test_a16_a_pass_stands_only_for_the_same_rules_and_brief_lines():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    first = upload(store, 'D1', *SECTION, more='b {}')
    verdict(store, 'D1', first['sha256'], {'0': True, '1': False, '2': True, '3': True, '4': True, '5': True})
    edit_plan(store, lambda d: shots_of(d)[0].update(framing='wide, from the left'))   # the brief changes: the rules are read again and uploaded with it
    again = upload(store, 'D1', *SECTION, more='c {}')
    assert 'round_rules' not in again   # no list of the round: every rule is answered again
    with pytest.raises(Problem, match=r'D1: the verdict leaves 5 rule\(s\) of the project without an answer'):
        verdict(store, 'D1', again['sha256'], {'1': True}, rnd=2)   # the earlier passes were given on another brief
    assert verdict(store, 'D1', again['sha256'], ALL_OK, rnd=2)['next'].startswith('Passed')


# ---------- c1, c2: the still ----------

def test_c1_a_still_rule_not_seen_twice_is_left_out_and_never_a_failed_must():
    store = load()
    sha = upload(store, 'D1', *SECTION, still=True)['sha256']
    asked = still_verdict(store, sha, answers({'0': 'not seen', '1': True}), shot='D1', key=frame('D1'))
    assert asked['not_seen'] == [{'rule': RULES[0], 'need': 'a crop of the sill'}]   # the first time: its crop is asked for, as on any drawing
    out = still_verdict(store, sha, answers({'0': 'not seen'}), shot='D1', key=frame('D1'))
    assert out['next'].startswith('The still end-frame passed') and out['failed'] == [] and out['not_seen'] == []
    assert [r['rule'] for r in saved(store)['motion_checks']['D1'][-1]['rules']] == [RULES[1]]
    approve(store, 'D1')
    with pytest.raises(Problem, match=r'D1: the verdict leaves 1 rule\(s\) of the project without an answer, first: "The block rests on the rods'):
        verdict(store, 'D1', upload(store, 'D1', *SECTION, more='b {}')['sha256'], {k: True for k in '12345'})   # the animated drawing answers it


def test_c2_a_marked_list_with_no_rule_a_still_can_show_passes_the_still_with_an_empty_list():
    store = load()
    only_motion = f'1. must (motion): {RULES[3]}\n2. should (still): {RULES[2]}\n'
    out = upload(store, 'D1', *SECTION, still=True, rules=only_motion)
    assert out['still_rules'] == [] and 'No rule of this drawing is one a still can show' in out['next'] and '"rules": []' in out['next']
    done = still_verdict(store, out['sha256'], {}, shot='D1', key=frame('D1'))
    assert done['next'].startswith('The still end-frame passed') and len(chat(store, 'still end-frame')) == 1
    with pytest.raises(Problem, match='The verdict lists the rules checked'):
        still_verdict(store, upload(store, 'D1', *SECTION, still=True, more='c {}')['sha256'], {}, shot='D1', key=frame('D1'))   # a list with a rule a still can show: an empty verdict is refused, as before


# ---------- M1, M2, M4: the plan check; M3: the labels gate ----------

def test_m1_the_plan_check_flags_a_drawn_shot_whose_words_ask_for_a_camera_move_its_flow_does_not_allow():
    store = load()
    assert warnings(store, 'camera_words') == []
    edit_plan(store, lambda d: shots_of(d)[0].update(information_progression='the rods, then the camera pushes in on the block'))
    hit = warnings(store, 'camera_words')
    assert len(hit) == 1 and hit[0]['shot_id'] == 'D1'
    assert hit[0]['message'] == ('shot D1: its words ask for a camera move ("pushes in") and its camera flow is Fixed. Settle it now, in the plan, not at the build: name '
                                 'the flow the shot needs (camera_flow), or take the move out of its words; when the choice is the operator\'s, ask it with the plan.')
    edit_plan(store, lambda d: shots_of(d)[0].update(camera_flow='step_closer'))
    assert warnings(store, 'camera_words') == []   # a move toward a part, and the flow allows one
    edit_plan(store, lambda d: shots_of(d)[0].update(framing='the frame pans along the rods'))
    assert 'its camera flow is Step closer' in warnings(store, 'camera_words')[0]['message'] and '"pans along"' in warnings(store, 'camera_words')[0]['message']
    edit_plan(store, lambda d: shots_of(d)[0].update(camera_flow='pan_along'))
    assert '"pushes in"' in warnings(store, 'camera_words')[0]['message']   # a sideways flow does not allow the push-in
    edit_plan(store, lambda d: shots_of(d)[0].update(warning_answers=[{'kind': 'camera_words', 'answer': 'the words describe the parts'}]))
    assert warnings(store, 'camera_words')[0]['answered'] is True


def apart(d):
    """The still IM1 between the drawings D2 and D3."""
    d1, d2, d3, im1 = shots_of(d)
    im1.update(start_frame=200, end_frame=400)
    d3.update(start_frame=400, end_frame=500)
    shots_of(d)[:] = [d1, d2, im1, d3]


def test_m2_a_drawing_continues_another_only_when_they_are_next_to_each_other_in_the_film():
    store = load()
    assert warnings(store, 'continues_apart') == []
    s, plan = plan_of(store)
    cont = lambda sid: VS.continues_from(*plan_of(store)[::-1], VS.locate(store, saved(store), sid)[1], VS.locate(store, saved(store), sid)[3])
    assert (cont('D2'), cont('D3'), cont('D4')) == ('D1', 'D2', 'D1')   # next to each other; a return the plan names (return_of)
    edit_plan(store, apart)
    assert (cont('D2'), cont('D3')) == ('D1', '')
    hit = warnings(store, 'continues_apart')
    assert len(hit) == 1 and hit[0]['shot_id'] == 'D3'
    assert hit[0]['message'] == ('shot D3 does not continue the drawing D2: IM1 is between them in the film. A drawing opens where another ends only when the two are next '
                                 'to each other, so D3 is built as its own drawing. Put them next to each other to continue, or name the return (return_of) when the '
                                 'same diagram comes back.')
    brief = build(store, 'D3')   # no gate on D2, and no "Continues from" line
    assert 'Continues from' not in brief['brief'] and 'continues' not in brief


def test_m3_the_labels_gate_names_every_drawn_shot_that_lacks_labels_in_one_refusal():
    store = load()
    def bare(d):
        for s in (shots_of(d)[1], shots_of(d)[2], shots_of(d, 1)[0]):
            s.update(carries_text=True, scene_motion={'labels': [], 'cues': []})
    edit_plan(store, bare)
    with pytest.raises(Problem) as e:
        build(store, 'D1')
    assert 'the texts of every drawn shot go in the plan: D2, D3, D4 carry text and have no scene_motion.labels' in str(e.value)


def test_m4_the_plan_check_flags_an_exact_end_picture_whose_change_is_larger_than_an_edit_region():
    store = load()
    change = lambda what: edit_plan(store, lambda d: shots_of(d, 1)[1].update(end_state_exact=True, changes=[{'what': what, 'beat_id': 'B1'}]))
    change('the rod is set down on the base')
    assert warnings(store, 'end_change_large') == []
    change('the whole ceiling is now plastered')
    hit = warnings(store, 'end_change_large')
    assert len(hit) == 1 and hit[0]['shot_id'] == 'VS1'
    assert hit[0]['message'] == ('shot VS1 ends on an exact end picture, which is an edit inside one region of its start, a third of the frame at most; its change reads as '
                                 'larger ("the whole ceiling is now plastered"). Plan it start-only (end_state_exact false), so the motion carries the change, or as a new '
                                 'picture of its own.')
    change('three quarters of the floor is laid')
    assert len(warnings(store, 'end_change_large')) == 1
    edit_plan(store, lambda d: shots_of(d, 1)[1].update(end_state_exact=False))
    assert warnings(store, 'end_change_large') == []   # no end picture: nothing to flag
    with pytest.raises(ValueError, match='The region covers 75 % of the frame: an edit changes one region of a third at most; for an end image, make the shot start-only'):
        VS.check_region({'left': 0, 'top': 0, 'width': 1, 'height': 0.75})   # a picture ordered as an edit of another is not in the plan: the refusal says what to do


# ---------- the texts ----------

def visuals():
    return next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')


def test_the_served_text_and_the_helpers_say_it_and_the_older_ways_are_named():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import fixset2_wording as W
    stage = visuals()
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    later = next(p['text'] for p in stage['parts'] if p['name'] == 'later')
    was = next(p['text'] for p in W.before(stage)['parts'] if p['name'] == 'later')
    for where, old, new in W.PAIRS:
        assert where == 'later' and later.count(new) == 1 and was.count(old) == 1 and new not in was, old[:50]
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').replace('\r\n', '\n').count(new) == 1, (file, old[:50])
    for said in ('all started in one message', 'the order of the film, before any motion is built', '`must (still, with D1):`', 'rules-round.md',
                 'not only the things of the plan', 'State there the count of each shape that repeats', 'a verdict with an empty rule list', 'in the same go'):
        assert said in later, said
    parts = (ROOT / 'plugin' / 'agents' / 'vw-motion-parts.md').read_text(encoding='utf-8')
    assert 'data-shots' in parts and 'your open choices' in parts and 'not only the things of the plan' in parts
    assert '`must (still, with D1):`' in (ROOT / 'plugin' / 'agents' / 'vw-motion-rules.md').read_text(encoding='utf-8')
    check = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert 'rules-round.md' in check and 'with-<that shot>/last-frame.png' in check
    skill = (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'place each with' not in skill and 'place the view this drawing shows with `<use href="#part-<name>">`' in skill   # c4
    everything = stage['prompt'] + ''.join(p['text'] for p in stage['parts'])
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired and s not in everything for s in W.RETIRED)
    cmd = (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'the AI video and the recording are asked in the chat, one at a time' in retired and 'the AI video and the recording are asked in the chat, one at a time' not in cmd   # c3
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('d222(prompt, parts)') < split.index('fixset2(prompt, parts)')
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "'rules-round.md'" in vw and "out.get('compare')" in vw
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    assert all(f'| {n} |' in log for n in range(236, 245))   # the older way of each change
    for name in ('continues_from', 'round_rules', 'data-shots', 'three or four at once', 'not seen twice', 'with <shot>'):
        assert name in log.split('| 236 |', 1)[1], name
