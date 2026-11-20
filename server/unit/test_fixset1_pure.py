"""Fix set phase 1 (SK, 19 Nov 2026): the proper fixes for the three hotfixes of VW-24's step 6, on a fixture with the shape of a real session.

B4: the fixture (step6_real_shape.json, loaded by step6_shape). B1 (defect 55): one function says where a picture's file is; the brief and the
fetch both use it; nothing is copied; a missing file is named in the brief's refusal. B2 (defect 56) and A3.2: the brief names the view this drawing
shows and the upload checks that view; no stated view, or parts that name no view: any one view, as the hotfix. B3 (the stuck stills): each rule is
marked as one a still can show or one only motion shows; the still round is given and expects only the first kind; a list with no marks keeps the
hotfix's behaviour. Without a database."""
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

from app import font_sample, motion as M, pictures as P, visuals_stage as VS
from app.errors import Problem
from step6_shape import RULES, SHAPE, answers, build, load, parts_svg, play, rules_text, upload, verdict
from test_design221_p1_pure import NEW, edit_plan
from test_design221_p3c_pure import still_verdict
from test_visuals_stage_pure import g, saved

ROOT = Path(__file__).resolve().parents[2]
SECTION = ('part-block-section', 'part-rod-end')   # what a drawing cut across places


@pytest.fixture(autouse=True)
def drawn_picture(monkeypatch):
    """The parts picture is drawn by Chromium on the server; here it is faked."""
    monkeypatch.setattr(font_sample, 'render', lambda html: b'\x89PNGparts')


# ---------- B4: the fixture ----------

def test_b4_the_fixture_has_the_shape_of_a_real_step_6_session():
    views = Counter(p['element'] for p in SHAPE['parts'])
    assert (views['E1'], views['E2'], views['E3'], views['']) == (3, 2, 1, 1)   # a thing with three views, one with two, one with one, a part of no thing
    assert {k.split('/')[2] for k in SHAPE['files']} == {'references', 'drawings'}   # both places a run keeps a picture
    assert {r['shows'] for r in SHAPE['rules']} == {'still', 'motion'} and {r['class'] for r in SHAPE['rules']} == {'must', 'should'}
    store = load()
    s = saved(store)
    plan = VS.current_plan(store, s)
    assert VS.drawn_ids(plan, s) == ['D1', 'D2', 'D3', 'D4']
    for sid, before in SHAPE['continues'].items():   # the chain: D2 on D1, D3 on D2, D4 returns to D1
        _, gap, _, shot = VS.locate(store, s, sid)
        assert VS.continues_from(plan, s, gap, shot) == before
    assert [p['id'] for p in s['motion_parts_approved']['parts']] == [p['id'] for p in SHAPE['parts']]
    with pytest.raises(Problem, match="D2 continues from D1: its still end-frame opens on D1's approved still end-frame, and D1 has none now"):
        build(store, 'D2')   # fix set, the critic's point 7: D2's still waits for D1's approved still; its motion for D1's passed project
    out = play(store, 'D1', *SECTION)   # the still round, the approval, the animated round
    assert out['still']['next'].startswith('The still end-frame passed') and out['animated']['next'].startswith('Passed, 1 note')
    assert [bool(c.get('still')) for c in saved(store)['motion_checks']['D1']] == [True, False]
    assert build(store, 'D2')['continues']['sha256'] == out['sha256']


# ---------- B1 (defect 55): where a picture's file is ----------

def test_b1_a_picture_in_each_place_is_fetchable_and_nothing_is_copied():
    store = load()
    had = set(store.files)
    refs = build(store, 'D1')['refs']
    assert {'f-block', 'drawing-E1-a-0a1b2c3d', 'drawing-E1-b-0a1b2c3d', 'comp-rod', 'style-1'} == set(refs)
    s = saved(store)
    for rid in refs:
        at = VS.picture_file(store, NEW, s, rid)
        assert at == s['references'][rid]['key'] and store.exists(at)
        assert VS.fetch_key(store, NEW, f'run-1/visuals/references/{rid}.png') == at   # the plugin asks for this name; the fetch serves the file where it is
    assert set(store.files) == had and not hasattr(VS, 'refs_fetchable')   # the hotfix's copy is gone
    assert VS.fetch_key(store, NEW, 'run-1/visuals/session.json') == 'run-1/visuals/session.json'   # any other file of the run: as before
    assert VS.fetch_key(store, NEW, 'run-1/visuals/references/nobody.png') == '' and VS.fetch_key(store, NEW, 'run-1/out/none.json') == ''
    src = (ROOT / 'server' / 'app' / 'files.py').read_text(encoding='utf-8')
    assert 'visuals_stage.fetch_key(store, run, key)' in src   # the plugin's download route asks the same function


def test_b1_a_picture_whose_file_is_missing_is_named_in_the_briefs_refusal():
    store = load()
    del store.files['run-1/visuals/drawings/0a1b2c3d4e5f/a-plain.png']
    with pytest.raises(Problem) as e:
        build(store, 'D1')
    assert ('D1: the file of an approved picture of this brief is not with the run: drawing-E1-a-0a1b2c3d. It cannot be fetched: file a defect '
            '(`vw defect`) that names it; do not build from the brief without it.') in str(e.value)
    with pytest.raises(Problem, match='The shared parts: the file of an approved picture of this brief is not with the run: drawing-E1-a-0a1b2c3d'):
        g(lambda: VS.parts_brief(store, NEW, []))
    assert VS.motion_brief(store, NEW, [], 'D1')['brief']   # the brief's lines for a check or the page are not gated
    store.files['run-1/visuals/references/drawing-E1-a-0a1b2c3d.png'] = b'\x89PNG'   # a copy the hotfix left on a run is still found
    assert 'drawing-E1-a-0a1b2c3d' in build(store, 'D1')['refs']


# ---------- B2 (defect 56) and A3.2: the view this drawing shows ----------

def test_b2_a_part_names_its_view_and_a_view_that_is_no_view_is_refused():
    parts, problems = M.read_parts(parts_svg(), {'E1', 'E2', 'E3'})
    assert problems == [] and [p['view'] for p in parts] == [p['view'] for p in SHAPE['parts']]
    _, problems = M.read_parts(parts_svg().replace('data-view="plan"', 'data-view="from above"', 1), {'E1', 'E2', 'E3'})
    assert problems == ['part-block-top: data-view is the view the part is drawn in, one of cutaway, plan, side, elevation, or left out']


def test_a32_the_brief_says_place_the_view_this_drawing_shows_and_names_it():
    store = load()
    brief = build(store, 'D1')['brief']
    assert ('Use these parts (drawn once for the whole film; do not redraw them): part-block-section: Block, cut across (view cutaway); '
            'part-block-top: Block from above (view plan); part-block-under: Block from below; part-rod-end: Rod, its cut end (view cutaway); '
            'part-rod-grid: Rods from above (view plan); part-arrow: Arrow. Place the view this drawing shows, cutaway (part-block-section, part-rod-end), '
            'with <use href="#part-<name>"> (one view of a thing is enough): the server puts them in the page, and parts.svg beside this brief shows them.') in brief
    assert 'Place each' not in brief
    unstated = VS.motion_brief(store, NEW, [], 'D3')['brief']   # a shot that states no view: no view is named
    assert 'part-base: Base; part-arrow: Arrow. Place the view this drawing shows with <use href="#part-<name>"> (one view of a thing is enough):' in unstated


def test_b2_a_cross_section_passes_with_the_section_view_and_is_refused_with_the_view_from_above():
    store = load()
    assert upload(store, 'D1', *SECTION, still=True)['sha256']
    with pytest.raises(Problem) as e:
        upload(store, 'D1', 'part-block-top', 'part-rod-end', still=True)   # the tile from above in a drawing cut across
    assert ('D1 shows Block in the view cutaway but does not place its part of that view: place part-block-section with <use href="#part-…"> '
            '(drawn once for the whole film; do not redraw it).') in str(e.value)
    assert upload(store, 'D1', *SECTION, 'part-block-top', still=True)['sha256']   # the stated view placed; another view beside it is no fault


def test_b2_a_shot_with_no_stated_view_passes_with_any_one_view():
    store = load()
    for view in ('part-block-section', 'part-block-top', 'part-block-under'):
        assert upload(store, 'D3', view, 'part-base', still=True)['sha256']
    with pytest.raises(Problem) as e:
        upload(store, 'D3', 'part-base', still=True)
    assert ('D3 shows Block but uses none of its shared parts: place the view this drawing shows, one of part-block-section, part-block-top, '
            'part-block-under, with <use href="#part-…">') in str(e.value)


def test_b2_a_thing_with_one_view_behaves_as_before():
    store = load()
    with pytest.raises(Problem) as e:
        upload(store, 'D3', 'part-block-top', still=True)
    assert 'D3 shows Base but does not use its shared part: place part-base with <use href="#part-base">' in str(e.value)
    assert upload(store, 'D4', 'part-rod-grid', 'part-base', still=True)['sha256']   # D4 states "plan"; the base's one part names no view: placing it is enough
    with pytest.raises(Problem, match='D4 shows Rod in the view plan but does not place its part of that view: place part-rod-grid'):
        upload(store, 'D4', 'part-rod-end', 'part-base', still=True)


def test_b2_a_stated_view_no_part_is_drawn_in_and_parts_that_name_no_view_keep_the_any_one_rule():
    store = load()
    edit_plan(store, lambda d: d['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec'].update(view='elevation'))   # no part of the block or the rod is an elevation
    assert upload(store, 'D1', 'part-block-top', 'part-rod-grid', still=True)['sha256']
    old = load(views=False)   # a parts file approved before a part named its view (defect 56's fix, kept)
    assert all(not p['view'] for p in saved(old)['motion_parts_approved']['parts'])
    assert upload(old, 'D1', 'part-block-top', 'part-rod-grid', still=True)['sha256']
    with pytest.raises(Problem, match='D1 shows Block but uses none of its shared parts'):
        upload(old, 'D1', 'part-rod-end', still=True)


# ---------- B3 (the stuck stills): a still can show it, or only motion shows it ----------

def test_b3_each_rule_is_marked_when_it_is_written_and_the_mark_is_not_in_its_words():
    held = P.rules_of(rules_text())
    assert [(r['class'], r['shows'], r['rule']) for r in held] == [(r['class'], r['shows'], r['rule']) for r in SHAPE['rules']]
    assert held[0]['id'] == P.rule_id(RULES[0])   # neither the class nor the mark is part of the id
    assert all('shows' not in r for r in P.rules_of(rules_text(marked=False)))   # a list written before the marks
    odd = P.rules_of('- **must (motion):** It turns.\n- Should (Still) : It is level.\n- must(still): It is whole.\n- must: It is plain.\n')
    assert [(r['class'], r.get('shows'), r['rule']) for r in odd] == [('must', 'motion', 'It turns.'), ('should', 'still', 'It is level.'), ('must', 'still', 'It is whole.'),
                                                                     ('must', None, 'It is plain.')]


def test_b3_the_still_round_is_given_no_rule_that_only_motion_shows():
    store = load()
    out = upload(store, 'D1', *SECTION, still=True)
    assert out['still_rules'] == [f'must: {RULES[0]}', f'must: {RULES[1]}']   # the musts a still can show: no should, no rule about motion
    assert 'rules-still.md' in out['next']
    assert 'still_rules' not in upload(store, 'D1', *SECTION, still=True, marked=False)   # a list with no marks: nothing to leave out by


def test_b3_the_still_verdict_does_not_expect_the_motion_rules_and_an_answer_to_one_is_not_the_stills():
    store = load()
    sha = upload(store, 'D1', *SECTION, still=True)['sha256']
    with pytest.raises(Problem, match=r'D1: the verdict leaves 1 rule\(s\) of the project without an answer, first: "There are four rods, evenly spaced."'):
        still_verdict(store, sha, answers({'0': True}), shot='D1')   # a must a still can show is answered
    out = still_verdict(store, sha, answers({'0': True, '1': True, '3': False, '4': 'not seen'}), shot='D1')   # a checker that answers the motion rules all the same
    assert out['next'].startswith('The still end-frame passed') and out['failed'] == [] and out['not_seen'] == []
    assert [r['rule'] for r in saved(store)['motion_checks']['D1'][-1]['rules']] == RULES[:2]
    sha2 = upload(store, 'D1', *SECTION, still=True, more='c {}')['sha256']
    asked = still_verdict(store, sha2, answers({'0': 'not seen', '1': True}), shot='D1')   # a rule a still can show, not seen: a crop is asked for, as on any drawing
    assert asked['not_seen'] == [{'rule': RULES[0], 'need': 'a crop of the sill'}] and not asked['next'].startswith('The still end-frame passed')


def test_b3_the_animated_round_answers_every_rule():
    store = load()
    out = play(store, 'D1', *SECTION)
    assert len(saved(store)['motion_checks']['D1'][-1]['rules']) == len(RULES) and out['animated']['notes'] == [RULES[2]]
    with pytest.raises(Problem, match=r'D1: the verdict leaves 2 rule\(s\) of the project without an answer, first: "The rods appear before'):
        verdict(store, 'D1', upload(store, 'D1', *SECTION, more='d {}')['sha256'], {'0': True, '1': True, '2': True, '5': True})


def test_b3_a_rule_list_written_before_the_marks_passes_as_with_the_hotfix():
    store = load()
    sha = upload(store, 'D1', *SECTION, still=True, marked=False)['sha256']
    out = still_verdict(store, sha, answers(SHAPE['rounds']['D1']['still']), shot='D1')   # the motion rules answered "not seen", as on VW-24
    assert out['next'].startswith('The still end-frame passed') and out['not_seen'] == []
    sha2 = upload(store, 'D1', *SECTION, still=True, marked=False, more='c {}')['sha256']
    assert still_verdict(store, sha2, answers({'0': True}), shot='D1')['next'].startswith('The still end-frame passed')   # and any rule may be left out, as before


# ---------- the texts ----------

def test_the_helpers_are_told_of_the_marks_the_stills_list_and_the_view():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import fixset1_wording as W
    for file, old, new in W.HELPERS:
        text = (ROOT / 'plugin' / file).read_text(encoding='utf-8')
        assert text.count(new) == 1 and old in new, file   # sentences are added after their anchor; none is replaced
    rules = (ROOT / 'plugin' / 'agents' / 'vw-motion-rules.md').read_text(encoding='utf-8')
    assert '`must (still):`' in rules and '`must (motion):`' in rules
    check = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert 'rules-still.md' in check and 'only motion shows' in check
    assert 'data-view' in (ROOT / 'plugin' / 'agents' / 'vw-motion-parts.md').read_text(encoding='utf-8')
    assert 'place the view this drawing shows' in (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "out.get('still_rules')" in vw and "'rules-still.md'" in vw
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    assert all(f'| {n} |' in log for n in (232, 233, 234, 235)) and 'refs_fetchable' in log and 'PARTS_LINE' in log   # the older way of each change
    assert json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']   # no served sentence is retired by this set
