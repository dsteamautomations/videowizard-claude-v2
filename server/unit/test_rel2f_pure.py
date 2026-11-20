"""Release 2, section F (SK, 20 Nov 2026): the faults a second critic reproduced in step 6 of live 0.118.0 (design/_work/next-build-requirements-20-nov.md,
rows F1 to F15), each on the real-shape fixture: sequences where something is redone after later work was finished (a chain whose first still is
replaced, a comparison that comes due on a bound or selected drawing, a held or rejected drawing nothing names), the view a shot states against the
views its things are drawn in, a rule list marked in part or in another order, a picture record of another run. Then the sequences the critic found
correct, which must stay so, and a film in progress or finished, which must read as before."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app import font_sample, pictures as P, storage as S, visuals_stage as VS
from app.errors import Problem
from step6_shape import build, chat, load, parts_svg, upload, verdict
from test_design221_p1_pure import NEW, edit_plan, edit_session
from test_design221_p3c_pure import still_verdict
from test_design221_p4_pure import drawn_job, plan_of
from test_fixset2_pure import ABOVE, ALL_OK, SAME, SECTION, STILL_OK, approve, bound, comparing, drawn, frame, shots_of, still
from test_fixset4_pure import UNDER, alone, cut
from test_visuals_stage_pure import USER, g, saved, shot

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def drawn_picture(monkeypatch):
    """The parts picture is drawn by Chromium on the server; here it is faked."""
    monkeypatch.setattr(font_sample, 'render', lambda html: b'\x89PNGparts')


def job(shot_id, sha, jid=None):
    """A ready render of this project of the shot, made now (after everything before it, before everything after it)."""
    time.sleep(0.02)
    j = drawn_job(jid or f'job-{shot_id}-{sha[:6]}', unit=shot_id)
    j = {**j, 'request': {**j['request'], 'sha256': sha}, 'created_at': datetime.now(timezone.utc).isoformat()}
    time.sleep(0.02)
    return j


def moved(store, shot_id, parts, more, rules=None, said=ALL_OK):
    """The animated project of a shot whose still is approved: uploaded, passed, rendered. (its sha, its render)"""
    sha = upload(store, shot_id, *parts, rules=rules, more=more)['sha256']
    verdict(store, shot_id, sha, said)
    return sha, job(shot_id, sha)


def chain(store, d3=False):
    """D1, D2, D3 continue one another: every still approved in order, then the motion of D1 and D2 (and D3) passed and rendered. The renders."""
    still(store, 'D1', SECTION, png=b'\x89PNG-1')
    approve(store, 'D1')
    still(store, 'D2', SECTION, more='two {}', png=b'\x89PNG-2')
    approve(store, 'D2')
    still(store, 'D3', UNDER, more='three {}', png=b'\x89PNG-3')
    approve(store, 'D3')
    return [moved(store, 'D1', SECTION, 'b {}')[1], moved(store, 'D2', SECTION, 'two b {}')[1]] + ([moved(store, 'D3', UNDER, 'three b {}')[1]] if d3 else [])


def line(store, jobs=()):
    """What the next-step line says of the drawn graphics: what is due, then what can start."""
    items = P.expected(*plan_of(store), list(jobs))
    return ' '.join(x for x in (P.drawn_due(items), P.starts(items)) if x)


def states(store, jobs=(), ids=('D1', 'D2', 'D3')):
    return [drawn(store, jobs)[sid]['state'] for sid in ids]


# ---------- F1 (critical), F6: a chain whose earlier still is replaced after later work was finished ----------

def test_f1_the_first_still_of_a_finished_chain_replaced_sends_the_drawings_after_it_back_to_their_stills():
    store = load()
    jobs = chain(store)
    assert states(store, jobs) == ['made and checked', 'made and checked', 'being made']
    old = saved(store)['motion_bound']['D2']
    still(store, 'D1', SECTION, more='wider {}', png=b'\x89PNG-1b')   # the operator asked for a change at the head of the chain: another picture, checked
    approve(store, 'D1')
    d = drawn(store, jobs)
    assert d['D2']['state'] == 'being redone' and d['D2']['turn'] == 'still' and 'job' not in d['D2']   # built on D1's old still: its still is made again, its old render is not the drawing
    assert d['D3']['state'] == 'being redone' and d['D3'].get('waits_on') == 'D2' and 'turn' not in d['D3']
    assert 'the builders of the still end-frames of D2' in line(store, jobs) and 'D3 on D2' in line(store, jobs)
    # the bypass the critic walked: D3 briefed and built on D2's stale project, D2's old project judged again
    for call in (lambda: build(store, 'D3'), lambda: upload(store, 'D3', *UNDER, still=True, more='three again {}')):
        with pytest.raises(Problem) as e:
            call()
        assert e.value.message == ("D3 continues from D2: its still end-frame opens on D2's approved still end-frame, and D2 has none now: have D2's still built, "
                                   'checked and approved first, then brief D3.')
    with pytest.raises(Problem, match="D2: D1's still end-frame, which D2's still opens on, was replaced since D2's still was built"):
        verdict(store, 'D2', old, ALL_OK)   # a verdict binds no project built on the replaced picture
    with pytest.raises(Problem, match="D3: D2's still end-frame, which D3's still opens on, was replaced since D3's still was built"):
        upload(store, 'D3', *UNDER, more='three b {}')
    s, plan = plan_of(store)
    assert VS.passed_project(s, shots_of(plan)[1]) == '' and s['motion_bound']['D2'] == old   # D2's old project is no passed project for the drawing after it


def test_f1_the_chain_is_complete_again_once_each_drawing_is_redone_in_order():
    store = load()
    jobs = chain(store)
    still(store, 'D1', SECTION, more='wider {}', png=b'\x89PNG-1b')
    approve(store, 'D1')
    still(store, 'D2', SECTION, more='two again {}', png=b'\x89PNG-2b')   # opens on D1's new still
    approve(store, 'D2')
    assert saved(store)['motion_stills']['D2']['opens_on'] == saved(store)['motion_stills']['D1']['png']
    assert drawn(store, jobs)['D3']['turn'] == 'still'
    still(store, 'D3', UNDER, more='three again {}', png=b'\x89PNG-3b')
    approve(store, 'D3')
    assert saved(store)['motion_stills']['D3']['opens_on'] == saved(store)['motion_stills']['D2']['png']   # recorded with what it opens on
    jobs += [moved(store, 'D1', SECTION, 'b2 {}')[1]]
    assert states(store, jobs)[:2] == ['made and checked', 'being redone'] and drawn(store, jobs)['D2']['turn'] == 'motion'
    jobs += [moved(store, 'D2', SECTION, 'two b2 {}')[1], moved(store, 'D3', UNDER, 'three b {}')[1]]
    assert states(store, jobs) == ['made and checked'] * 3


def test_f6_a_plan_version_that_cuts_the_middle_drawing_sends_the_later_one_back_to_its_still():
    store = load()
    jobs = chain(store, d3=True)
    assert states(store, jobs) == ['made and checked'] * 3
    old = saved(store)['motion_bound']['D3']
    assert cut(store, 0, 1) == 'D2'   # D3 now continues D1, and its still opens on the last frame of a drawing that is gone
    item = drawn(store, jobs)['D3']
    assert item['state'] == 'being redone' and item['turn'] == 'still' and 'job' not in item
    with pytest.raises(Problem, match="D3: D1's still end-frame, which D3's still opens on, was replaced since D3's still was built"):
        verdict(store, 'D3', old, ALL_OK)
    assert drawn(store, jobs)['D1']['state'] == 'made and checked'


def test_f6_the_stills_only_variant_behaves_as_before():
    store = load()
    for sid, parts, n in (('D1', SECTION, 1), ('D2', SECTION, 2), ('D3', UNDER, 3)):
        still(store, sid, parts, more=f'{n} {{}}', png=b'\x89PNG-%d' % n)
        approve(store, sid)
    cut(store, 0, 1)
    assert drawn(store)['D3']['turn'] == 'still'


# ---------- F2: a drawing that continues another and compares with it ----------

def test_f2_a_comparison_with_the_replaced_still_is_not_answered_on_the_old_project():
    store = load()
    still(store, 'D1', SECTION, png=b'\x89PNG-1')
    approve(store, 'D1')
    still(store, 'D2', SECTION, comparing('D1'), {**STILL_OK, SAME: True}, png=b'\x89PNG-2', more='two {}')
    approve(store, 'D2')
    jobs = [moved(store, 'D1', SECTION, 'b {}')[1]]
    d2, j2 = moved(store, 'D2', SECTION, 'two b {}', comparing('D1'), {**ALL_OK, SAME: True})
    jobs += [j2]
    assert states(store, jobs)[:2] == ['made and checked'] * 2
    still(store, 'D1', SECTION, more='wider {}', png=b'\x89PNG-1b')
    approve(store, 'D1')
    item = drawn(store, jobs)['D2']
    assert item['state'] == 'being redone' and item['turn'] == 'still'   # not "being checked by Claude" on the project built on the old picture
    with pytest.raises(Problem, match="D2: D1's still end-frame, which D2's still opens on, was replaced since D2's still was built"):
        verdict(store, 'D2', d2, {SAME: True})
    assert saved(store)['motion_checks']['D2'][-1]['rules'][-1].get('with_png') != saved(store)['motion_stills']['D1']['png']


# ---------- F3, F8: a bound drawing uploaded again ----------

def test_f3_the_same_bound_project_uploaded_again_for_its_frame_stays_bound_and_the_comparison_is_judged():
    store = alone(load())
    d1, _ = bound(store, 'D1', SECTION, comparing('D4'))   # D4 has no still yet: the comparison waits as a note
    jobs = [job('D1', d1)]
    still(store, 'D4', ABOVE)
    approve(store, 'D4')
    assert 'its comparison with D4 is due' in drawn(store, jobs)['D1']['due']
    again = upload(store, 'D1', *SECTION, rules=comparing('D4'), more='b {}')   # the supported way to get D4's frame before the verdict
    assert again['sha256'] == d1 and again['compare'] == [{'shot_id': 'D4', 'key': frame('D4')}]
    assert saved(store)['motion_bound']['D1'] == d1
    item = drawn(store, jobs)['D1']
    assert item['state'] == 'being checked by Claude' and 'its comparison with D4 is due' in item['due']   # never "made and checked" with the must not judged
    assert verdict(store, 'D1', d1, {SAME: False})['failed'] == [SAME]
    assert drawn(store, jobs)['D1']['state'] == 'being redone'


def test_f8_a_new_animated_project_after_a_ready_render_is_a_redraw_at_once():
    store = load()
    d1, _ = bound(store, 'D1', SECTION)
    jobs = [job('D1', d1)]
    assert drawn(store, jobs)['D1']['state'] == 'made and checked'
    upload(store, 'D1', *SECTION, more='b {}')   # the same bound project again: no redraw (F3)
    assert drawn(store, jobs)['D1']['state'] == 'made and checked' and saved(store)['motion_bound']['D1'] == d1
    upload(store, 'D1', *SECTION, more='c {}')   # another animated project: the old render is not the drawing any more
    item = drawn(store, jobs)['D1']
    assert item['state'] == 'being redone' and item['turn'] == 'check' and 'job' not in item
    assert not P.complete([item]) and 'the checkers of D1 (1)' in line(store, jobs)


# ---------- F4: a held drawing the operator rejects ----------

def test_f4_a_held_drawing_the_operator_rejects_is_named_for_a_rebuild():
    """held_answer needs a database job: the state it records is written here (motion_held, and the rejected review of the render)."""
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    for rnd in (1, 2, 3):
        sha = upload(store, 'D1', *SECTION, more=f'round {rnd} {{}}')['sha256']
        verdict(store, 'D1', sha, {**ALL_OK, '1': False}, rnd=rnd)
    jobs = [job('D1', sha, 'job-held')]
    assert drawn(store, jobs)['D1']['state'] == 'held (needs a decision)'
    edit_session(store, lambda s: (s.setdefault('motion_held', {}).update(D1={'sha256': sha, 'round': 3, 'answer': 'reject', 'words': 'the rods are uneven'}),
                                   s['reviews'].update({'job-held': [{'decision': 'rejected', 'notes': 'the rods are uneven'}]})))
    item = drawn(store, jobs)['D1']
    assert item['state'] == 'being redone' and item['turn'] == 'motion'
    assert 'The motion of D1 comes after the still end-frames.' in line(store, jobs)   # named (D2's and D4's stills come first)
    new = upload(store, 'D1', *SECTION, more='rebuilt {}')['sha256']
    assert drawn(store, jobs)['D1']['turn'] == 'check'
    assert verdict(store, 'D1', new, ALL_OK)['next'].startswith('Passed')   # checked again from round 1


# ---------- F5: the view the shot states, and things drawn only in other views ----------

def other_view(store, svg):
    out = g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', svg.encode('utf-8')))
    VS.parts_answer(store, USER, NEW, [], out['sha256'], True, 'Approve')
    return store


def test_f5_a_thing_drawn_only_in_another_view_is_not_demanded_and_the_brief_says_so():
    base = '<symbol id="part-base" viewBox="0 0 200 100" data-element="E3"'
    store = other_view(alone(load(parts=False)), parts_svg().replace(base, base + ' data-view="cutaway"'))   # D4 is seen from above; the base is drawn cut across only
    brief = build(store, 'D4')['brief']
    assert ('Place the view this drawing shows, plan (part-rod-grid), with <use href="#part-<name>"> (one view of a thing is enough): the server puts them in the page, '
            'and parts.svg beside this brief shows them. No part of Base is drawn in the view plan: draw it in this drawing yourself, and place no part of another view for it.') in brief
    assert upload(store, 'D4', 'part-rod-grid', still=True)['sha256']   # was refused: "place part-base", the wrong picture
    two = base.replace('part-base', 'part-base-side') + ' data-view="side"><title>Base, from the side</title><rect width="200" height="100"/></symbol>\n' + base
    store = other_view(alone(load(parts=False)), parts_svg().replace(base, two + ' data-view="cutaway"'))   # two parts, both in other views
    assert upload(store, 'D4', 'part-rod-grid', still=True)['sha256']


def test_f5_a_part_of_the_stated_view_or_of_no_view_is_still_demanded():
    store = alone(load())
    assert 'No part of' not in build(store, 'D4')['brief']   # every thing of D4 has a part it may place: the brief line is as it was
    with pytest.raises(Problem, match='D4 shows Base but does not use its shared part: place part-base'):
        upload(store, 'D4', 'part-rod-grid', still=True)   # the base's one part names no view: it fits any
    edit_plan(store, lambda d: shots_of(d)[0]['drawing_spec'].update(view='elevation'))   # no part of the block is an elevation; one names no view
    with pytest.raises(Problem, match='D1 shows Block but does not use its shared part: place part-block-under'):
        upload(store, 'D1', 'part-block-top', 'part-rod-grid', still=True)
    assert upload(store, 'D1', 'part-block-under', still=True)['sha256']   # the rod has parts in other views only: nothing of it is demanded


# ---------- F7, F11: the shared parts change after a still was approved ----------

CHANGED = ('<title>Block, cut across</title><rect width="200"', '<title>Block, cut across</title><rect width="180"')


def test_f7_a_still_whose_parts_changed_is_named_again_and_not_its_motion():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    assert drawn(store)['D1']['turn'] == 'motion'
    other_view(store, parts_svg().replace(*CHANGED))   # new shared parts approved; a part D1 places is drawn anew
    assert drawn(store)['D1']['turn'] == 'still'   # was "the builders of the motion of D1": built, then refused as stale
    with pytest.raises(Problem, match='D1'):
        upload(store, 'D1', *SECTION, more='b {}')
    other_view(store, parts_svg().replace('<title>Arrow</title><rect width="200"', '<title>Arrow</title><rect width="180"'))   # a part D1 does not place
    still(store, 'D1', SECTION)
    assert drawn(store)['D1']['turn'] == 'motion'


def test_f11_new_shared_parts_not_yet_approved_hold_the_builders_and_the_line_names_the_parts_card():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', parts_svg().replace(*CHANGED).encode('utf-8')))   # uploaded, on its card, not approved
    said = line(store)
    assert 'the motion of D1' not in said and 'still end-frames of' not in said   # the brief is refused now: no builder is named
    assert said.count(VS.PARTS_WAIT) == 1
    with pytest.raises(Problem) as e:
        upload(store, 'D1', *SECTION, more='b {}')   # an animated project built without a brief in that window
    assert e.value.message == VS.PARTS_WAIT
    none = load(parts=False)   # no parts at all: the line says what is waited on
    assert line(none) == VS.PARTS_FIRST.format(n=4)
    assert P.starts(P.expected(*plan_of(none), [])) == ''


# ---------- F9, F10, F13: the rule list's marks ----------

PARTLY = '# Rules\n1. must: The block stands on the rods.\n2. should (still): The rods are level.\n3. must (motion): The block is lowered.\n'


def test_f9_an_unmarked_must_of_a_partly_marked_list_is_required_on_the_still():
    store = load()
    out = upload(store, 'D1', *SECTION, still=True, rules=PARTLY)
    assert out['still_rules'] == ['must: The block stands on the rods.']   # the checker is given it
    with pytest.raises(Problem, match=r'D1: the verdict leaves 1 rule\(s\) of the project without an answer, first: "The block stands on the rods."'):
        still_verdict(store, out['sha256'], {'The rods are level.': True}, shot='D1')   # so a verdict without it does not pass the still
    asked = still_verdict(store, out['sha256'], {'The block stands on the rods.': 'not seen'}, shot='D1')   # nor is "not seen" dropped: its frame is asked for
    assert asked['not_seen'] == [{'rule': 'The block stands on the rods.', 'need': 'a crop of the sill'}] and not asked['next'].startswith('The still end-frame passed')
    assert still_verdict(store, out['sha256'], {'The block stands on the rods.': True}, shot='D1')['next'].startswith('The still end-frame passed')


def test_f10_a_still_no_rule_could_be_checked_on_says_so_on_its_card():
    store = load()
    sha = upload(store, 'D1', *SECTION, still=True, rules='# Rules\n1. must (motion): The block is lowered.\n')['sha256']
    still_verdict(store, sha, {}, shot='D1', key=frame('D1'))
    card = next(i for i in chat(store, 'still end-frame') if 'D1' in i['question'])
    assert card['question'] == ('D1: this is the drawing as it stands at the end of the shot, before any motion is added. Is it right? '
                                'No rule could be checked on this still: judge it by eye.')
    checked = load()
    still(checked, 'D1', SECTION)
    assert next(i for i in chat(checked, 'still end-frame'))['question'].endswith('Is it right?')


def test_f13_a_mark_is_read_in_either_order_and_with_a_comma_or_a_semicolon():
    held = P.rules_of('1. must (with D4, still): One.\n2. must (still; with D4): Two.\n3. should (with D1; motion): Three.\n4. **must (still, with D4):** Four.\n5. must (with D4): Five.\n')
    assert [(r['class'], r.get('shows'), r.get('with'), r['rule']) for r in held] == [('must', 'still', 'D4', 'One.'), ('must', 'still', 'D4', 'Two.'), ('should', 'motion', 'D1', 'Three.'),
                                                                                    ('must', 'still', 'D4', 'Four.'), ('must', None, 'D4', 'Five.')]
    store = alone(load())
    with pytest.raises(Problem, match='compares with D9, which is not a drawn shot of this plan'):
        upload(store, 'D1', *SECTION, still=True, rules='1. must (with D9, still): The rods are the same.\n')   # the comparison is read, so a mistyped id is refused


def test_f13_a_mark_that_cannot_be_read_is_refused_at_the_upload():
    store = load()
    with pytest.raises(Problem) as e:
        upload(store, 'D1', *SECTION, still=True, rules='1. must (still): The block stands.\n2. must (stil, with D4): The rods are the same.\n')
    assert e.value.message == ('D1: the mark of the rule "must (stil, with D4): The rods are the same." cannot be read, so the rule would lose it. A rule starts with `must:` or '
                               '`should:`, and its mark is one of `(still)`, `(motion)`, `(still, with <shot id>)`, `(motion, with <shot id>)`: correct it in rules.md, then upload again.')
    assert upload(store, 'D1', *SECTION, still=True, rules='1. must: Must (as drawn) the block stand on the rods.\n')['sha256']   # words in brackets are no mark


# ---------- F12: a comparison that comes due on a drawing already selected ----------

def test_f12_a_comparison_that_comes_due_on_a_selected_drawing_is_said_and_a_failure_reopens_it():
    store = alone(load())
    d1, _ = bound(store, 'D1', SECTION, comparing('D4'))
    j = job('D1', d1)
    edit_session(store, lambda s: s['selections'].update(D1={'job_id': j['id']}))   # selected on the page
    assert drawn(store, [j])['D1']['state'] == 'answered'
    still(store, 'D4', ABOVE, png=b'\x89PNG-4')
    approve(store, 'D4')
    item = drawn(store, [j])['D1']
    assert item['state'] == 'being checked by Claude' and 'D1: its comparison with D4 is due' in item['due'] and 'D1: its comparison with D4 is due' in line(store, [j])
    assert verdict(store, 'D1', d1, {SAME: True})['next'].startswith('Passed')
    assert drawn(store, [j])['D1'] == {'kind': 'drawn', 'id': 'D1', 'name': 'D1', 'state': 'answered'}   # judged and passed: the selection stands, nothing more is said
    still(store, 'D4', ABOVE, png=b'\x89PNG-4b', more='wider {}')   # replaced again; this time the comparison fails
    approve(store, 'D4')
    assert verdict(store, 'D1', d1, {SAME: False})['failed'] == [SAME]
    item = drawn(store, [j])['D1']
    assert item['state'] == 'being redone' and item['turn'] == 'motion'
    assert item['due'] == ('D1 was selected, and a comparison with another drawing failed on it afterwards: it is being redone. Tell the operator; the new drawing is '
                           'asked on the page when it is made.')
    new = upload(store, 'D1', *SECTION, rules=comparing('D4'), more='c {}')['sha256']
    verdict(store, 'D1', new, {**ALL_OK, SAME: True, '0': False}, rnd=2)   # the redo fails another rule: still being redone
    assert drawn(store, [j])['D1']['state'] == 'being redone'
    last = upload(store, 'D1', *SECTION, rules=comparing('D4'), more='d {}')['sha256']
    verdict(store, 'D1', last, {**ALL_OK, SAME: True}, rnd=3)
    assert drawn(store, [j])['D1']['state'] == 'answered'   # clean again: its new render is asked on the page, as any render made after a selection


# ---------- F14: a picture record naming a file of another run ----------

def test_f14_a_picture_record_naming_another_runs_file_is_treated_as_missing():
    store = load()
    store.files['run-2/visuals/references/comp-rod.png'] = b'\x89PNGother'
    edit_session(store, lambda s: s['references']['comp-rod'].update(key='run-2/visuals/references/comp-rod.png'))
    s = saved(store)
    assert VS.picture_file(store, NEW, s, 'comp-rod') == 'run-1/visuals/references/comp-rod.png'   # the run's own file of that name, never the other run's
    del store.files['run-1/visuals/references/comp-rod.png']
    assert VS.picture_file(store, NEW, s, 'comp-rod') == '' and VS.fetch_key(store, NEW, 'run-1/visuals/references/comp-rod.png') == ''
    with pytest.raises(Problem, match='the file of an approved picture of this brief is not with the run: comp-rod'):
        build(store, 'D1')


# ---------- F15: a clean drawing whose take the operator rejects ----------

def test_f15_a_clean_drawing_the_operator_rejects_is_named_for_a_rebuild_with_their_words():
    """The page's Reject on a drawn graphic's line ends in `review_take` (through `chat_flow`'s item): a rejected review on the render, with the
    operator's words as its notes. Its answer is the review itself and tells the assistant nothing, so the next-step line must."""
    store = load()
    d1, _ = bound(store, 'D1', SECTION)
    j = job('D1', d1)
    assert drawn(store, [j])['D1']['state'] == 'made and checked'
    store.files[j['request']['request_key']] = json.dumps({'kind': 'motion', 'sha256': d1}).encode('utf-8')

    class One:   # the one render row, as the database gives it
        execute = lambda self, *a: self
        fetchone = lambda self: j
    out = VS.review_take(One(), store, USER, NEW, [], j['id'], 'rejected', 'the rods are too thin', '', 'Reject')
    assert out['decision'] == 'rejected' and 'for_the_assistant' not in out
    item = drawn(store, [j])['D1']
    assert item['state'] == 'being redone' and item['turn'] == 'motion'   # was "being made" with no turn: a new render of the same project is no answer
    assert item['due'] == ('D1: the operator rejected this drawing: "the rods are too thin". Give these words to a new `vw-motion-shot` helper to build its motion again '
                           '(a new project, not a new render of this one), upload it and check it again from round 1.')
    assert item['due'] in line(store, [j])
    new = upload(store, 'D1', *SECTION, more='thicker {}')['sha256']
    item = drawn(store, [j])['D1']
    assert item['turn'] == 'check' and 'due' not in item   # the rebuild is uploaded: its checker is named, the words are not said again
    verdict(store, 'D1', new, ALL_OK)
    assert drawn(store, [j, job('D1', new)])['D1']['state'] == 'made and checked'


def test_f15_a_render_made_again_without_the_effect_is_no_rebuild():
    store = load()
    d1, _ = bound(store, 'D1', SECTION)
    j = job('D1', d1)
    edit_session(store, lambda s: s['reviews'].update({j['id']: [{'decision': 'rejected', 'notes': "made again without the effect, at the operator's word"}]}))
    again = {**job('D1', d1, 'job-plain'), 'status': 'queued'}   # `motion_finish` ordered the new render before the review was recorded
    item = drawn(store, [j, again])['D1']
    assert item['state'] == 'being made' and 'due' not in item and 'turn' not in item


# ---------- (b), (c): the checks asked beside the rows ----------

def test_b_a_storage_that_cannot_be_reached_is_not_read_as_a_missing_file():
    store = S.SupabaseStorage.__new__(S.SupabaseStorage)
    store.bucket = 'b'

    def call(status):
        def _call(method, path, **kw):
            raise Problem(status, 'STORAGE', 'no')
        return _call
    store._call = call(404)
    assert store.exists('run-1/x.png') is False
    store._call = call(503)
    with pytest.raises(Problem):
        store.exists('run-1/x.png')


def test_c_a_comparison_with_a_drawing_replaced_by_the_operators_own_file_is_closed():
    store = alone(load())
    d1, _ = bound(store, 'D1', SECTION, comparing('D4'))
    j = job('D1', d1)
    assert 'its comparison with D4 waits' in drawn(store, [j])['D1']['due']
    edit_session(store, lambda s: s['assets'].update(D4={'kind': 'movie', 'key': 'run-1/own.mp4'}))   # D4 will never have a still end-frame
    item = drawn(store, [j])['D1']
    assert item['state'] == 'made and checked' and item['due'] == 'D1: its comparison with D4 is closed (1 rule): D4 is no drawn graphic of the plan now.'


# ---------- the sequences the critic found correct stay correct ----------

def test_kept_the_middle_still_of_a_chain_rejected_is_made_again_and_the_next_waits():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    still(store, 'D2', SECTION, more='two {}')
    VS.still_answer(store, USER, NEW, [], ['D2'], False, 'Reject', 'show the gap')
    d = drawn(store)
    assert d['D2']['turn'] == 'still' and d['D3'].get('waits_on') == 'D2' and d['D1']['turn'] == 'motion'


def test_kept_a_drawing_turned_into_another_kind_of_shot_frees_the_one_after_it():
    store = load()
    still(store, 'D1', SECTION)
    approve(store, 'D1')
    edit_plan(store, lambda d: shots_of(d).__setitem__(1, shot('D2', 100, 200, 'image')))
    d = drawn(store)
    assert 'D2' not in d and d['D3']['turn'] == 'still' and 'waits_on' not in d['D3']   # D3 continues no drawing now


def test_kept_one_drawn_shot_and_no_drawn_shot():
    one = load(parts=False)
    edit_plan(one, lambda d: (shots_of(d).__delitem__(slice(1, 3)), shots_of(d, 1).__delitem__(0)))
    assert list(drawn(one)) == ['D1'] and line(one) == 'Start now, together in one message: the builders of the still end-frames of D1 (1).'   # no shared parts are waited for
    assert upload(one, 'D1', still=True)['sha256']
    none = load(parts=False)
    edit_plan(none, lambda d: (shots_of(d).__delitem__(slice(0, 3)), shots_of(d, 1).__delitem__(0)))
    assert drawn(none) == {} and line(none) == ''


def test_kept_two_drawings_comparing_with_each_other_do_not_wait_on_each_other():
    store = alone(load())
    still(store, 'D1', SECTION, comparing('D4'))
    still(store, 'D4', ABOVE, comparing('D1'))
    assert len(chat(store, 'still end-frame')) == 2 and 'waits_on' not in drawn(store)['D1'] and 'waits_on' not in drawn(store)['D4']


# ---------- a film in progress, and a finished step 6 ----------

def before_the_release(s):
    """A session as live 0.118.0 could have left it: no still or project says what it opens on."""
    for row in list(s['motion_stills'].values()) + list(s['motion_projects'].values()):
        row.pop('opens_on', None), row.pop('opens_from', None)


def test_a_film_in_progress_whose_stills_do_not_say_what_they_open_on_reads_as_before():
    store = load()
    jobs = chain(store, d3=True)
    edit_session(store, before_the_release)
    assert states(store, jobs) == ['made and checked'] * 3
    still(store, 'D1', SECTION, more='wider {}', png=b'\x89PNG-1b')
    approve(store, 'D1')
    assert states(store, jobs) == ['being redone', 'made and checked', 'made and checked']   # nothing is marked that does not say what it was built on
    old = load(views=False)   # parts from before a part named its view
    assert upload(old, 'D1', 'part-block-top', 'part-rod-grid', still=True)['sha256']


def test_a_finished_step_6_stays_finished_and_is_reopened_only_by_what_is_replaced_afterwards():
    store = alone(load())
    still(store, 'D1', SECTION, comparing('D4'), png=b'\x89PNG-1')
    approve(store, 'D1')
    still(store, 'D4', ABOVE, png=b'\x89PNG-4')
    approve(store, 'D4')
    still(store, 'D2', SECTION, more='two {}', png=b'\x89PNG-2')
    approve(store, 'D2')
    still(store, 'D3', UNDER, more='three {}', png=b'\x89PNG-3')
    approve(store, 'D3')
    jobs = [moved(store, 'D1', SECTION, 'b {}', comparing('D4'), {**ALL_OK, SAME: True})[1], moved(store, 'D2', SECTION, 'two b {}')[1], moved(store, 'D3', UNDER, 'three b {}')[1],
            moved(store, 'D4', ABOVE, 'four b {}')[1]]
    edit_session(store, lambda s: s['selections'].update({j['unit']: {'job_id': j['id']} for j in jobs}))   # every drawing selected on the page
    ids = ('D1', 'D2', 'D3', 'D4')
    assert states(store, jobs, ids) == ['answered'] * 4 and line(store, jobs) == ''
    edit_session(store, before_the_release)
    assert states(store, jobs, ids) == ['answered'] * 4 and line(store, jobs) == ''
    upload(store, 'D2', *SECTION, more='two c {}')   # a project uploaded after the selection replaces nothing the operator chose
    assert states(store, jobs, ids) == ['answered'] * 4
    still(store, 'D4', ABOVE, png=b'\x89PNG-4b', more='wider {}')   # the picture D1 compares with is really replaced
    approve(store, 'D4')
    assert states(store, jobs, ids) == ['being checked by Claude', 'answered', 'answered', 'answered']


def test_the_older_ways_are_in_the_decision_log():
    log = (ROOT / 'design/35-decision-log.md').read_text(encoding='utf-8')
    for n in range(281, 289):
        assert f'| {n} |' in log
    assert 'release 2 (F)' in log
