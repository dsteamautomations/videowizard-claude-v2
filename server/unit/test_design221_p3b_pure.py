"""design/221 (SK, 19 Nov 2026): the critic's seven points on phase 2 (design/_work/design221-critic-phase2.md) and phase 3b, row 2.
A1: the labels and cues of every drawn shot go in the plan with the plan (scene_motion without sha256); the brief before a build is refused while a
drawn shot that carries text has none; a clean verdict binds the passed project to its shot (motion_bound) and the render needs no plan change; a
later upload clears the binding; a verdict record keeps the digest of the rules and brief it answered and a record for other rules is ignored.
A2: whole labels in the short-label rule. A3: a checker's own must only with one of the four must kinds. A4: "not seen" twice in a round is a failed
must. A5: once a must, always a must; no downgrade without rules. A6: no verdict with a database and no finished check of the project.
Row 2 (A7): a drawing that continues another is built on its passed project and its last frame, started only after it passed.
Part C: the style texts agree with their camera head line. Without a database."""
import json
import re
import sys
from pathlib import Path

import pytest

from app import film, pictures as P, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import FakeConn, motion_shot, motion_store, project
from test_design221_p1_pure import NEW, edit_plan, edit_session, visuals
from test_design221_p2_pure import EVEN, LEAVES, RULES, SOLID, WARN, Jobs, selectable, two_drawn, upload, verdict
from test_visuals_stage_pure import USER, g, saved

ROOT = Path(__file__).resolve().parents[2]
ALL = {SOLID: True, EVEN: True, LEAVES: True}
LABEL = 'Solid brick-on-edge course at sill level'


def no_sha(store, n=0):
    """The plan as the planner now writes it: scene_motion with labels and cues, no sha256."""
    edit_plan(store, lambda d: d['gaps'][0]['scenes'][0]['shots'][n]['scene_motion'].pop('sha256'))


def fact(store, sha, shot='MO1'):
    orig, VS.load_json = VS.load_json, (lambda store_, k: {'sha256': sha})
    try:
        return P.fact_view(saved(store), store, {'unit': shot, 'request': {'request_key': 'k'}}, shot)
    finally:
        VS.load_json = orig


# ---------- A1: labels and cues in the plan first; the server binds the passed project ----------

def test_the_plan_names_labels_and_cues_without_a_sha():
    s = VC.Shot.model_validate(motion_shot(scene_motion={'labels': [LABEL], 'cues': [{'selector': '#label', 'word': 'solid'}]}))
    assert s.scene_motion.sha256 is None and s.scene_motion.labels == [LABEL]
    VC.motion_needs(s, 4.0)


def test_the_brief_before_a_build_is_refused_while_a_drawn_shot_with_text_has_no_labels():
    for over in ({'carries_text': True, 'drawing_spec': None},   # design/221 phase 3c: a shot's message alone is its point, not text on screen; fix set A3.3: with a corner note (an illustrative spec) and `labels: []` it is not asked
                 {'drawing_spec': {**motion_shot()['drawing_spec'], 'illustrative': False, 'label': 'Sill course'}}):
        store = motion_store(sh=motion_shot(scene_motion={'labels': [], 'cues': []}, **over))
        with pytest.raises(Problem) as e:
            g(lambda: VS.motion_brief(store, NEW, [], 'MO1', build=True, conn=FakeConn([])))
        assert ('MO1 carries text and has no scene_motion.labels: add scene_motion: {labels: [every text the viewer reads, word for word, never the corner '
                'note], cues: [{selector: "#id", word or at_s}]} to it in the plan, then propose the plan.') in str(e.value), over
        VS.motion_brief(store, NEW, [], 'MO1')   # the brief's lines for a check or a page are not gated
    quiet = motion_store(sh=motion_shot(scene_motion={'labels': [], 'cues': []}))   # no text at all: an empty list passes (the spec's label is the corner note)
    out = g(lambda: VS.motion_brief(quiet, NEW, [], 'MO1', build=True, conn=FakeConn([])))
    assert 'Text on screen, word for word, and only these: none.' in out['brief'] and 'continues' not in out


def test_a_clean_verdict_binds_the_project_and_the_render_needs_no_plan_change():
    store = motion_store()
    no_sha(store)
    sha = upload(store)
    out = verdict(store, sha, ALL)
    assert out['next'] == 'Passed, 0 notes: `vw motion render --shot MO1`.'
    assert saved(store)['motion_bound'] == {'MO1': sha}
    request = VS._motion_request(store, VS.session_of(store, NEW, []), NEW, 'MO1')[3]
    assert request['sha256'] == sha and request['labels'] == [LABEL] and '#label' in json.dumps(request['sidecar'])   # the plan's labels and cues count for it
    assert VS.render_motion(FakeConn([]), store, USER, NEW, [], {'shot_id': 'MO1'})['frames'] == 100


def test_a_later_upload_clears_the_binding_until_its_own_clean_verdict():
    store = motion_store()
    no_sha(store)
    sha = upload(store)
    verdict(store, sha, ALL)
    sha2 = upload(store, project(**{'style.css': 'body { margin: 0; }'}))
    assert saved(store)['motion_bound'] == {}
    with pytest.raises(Problem, match='no project of MO1 has passed its fact check yet'):
        g(lambda: VS.render_motion(FakeConn([]), store, USER, NEW, [], {'shot_id': 'MO1'}))
    verdict(store, sha2, {SOLID: False, EVEN: True, LEAVES: True})
    assert saved(store)['motion_bound'] == {}   # not clean: not bound
    verdict(store, sha2, ALL, rnd=2)
    assert saved(store)['motion_bound'] == {'MO1': sha2}


def test_a_passed_verdict_names_a_project_the_plan_still_points_away_from():
    store = motion_store()   # the plan names 'b' * 64, the older way
    sha = upload(store)
    assert 'The plan names another project for MO1' in verdict(store, sha, ALL)['next']


def test_a_clean_record_does_not_cover_rules_added_since_on_the_page_or_at_select():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, ALL)
    conn = selectable(store, sha)
    upload(store, rules=RULES + '4. must: The sill course is one brick deep.\n')   # the same project, a rule more
    assert fact(store, sha)['state'] == 'none'
    with pytest.raises(Problem, match='no fact check of its project yet'):
        g(lambda: VS.select_take(conn, store, USER, NEW, [], 'job-9', 'yes'))
    rec = saved(store)['motion_checks']['MO1'][-1]
    assert rec['answered'] != VS.answered(saved(store)['motion_projects'][sha])


# ---------- A2 to A6 ----------

def test_the_short_label_rule_compares_whole_labels():
    one = {'warnings': [WARN('Cement', 0.36)]}
    assert len(VS.short_labels(one, own=['Cement'], shared=['Cement mortar'])) == 1   # a neighbour's longer label does not exempt it
    assert VS.short_labels(one, own=['Cement mortar'], shared=[]) == []   # nor is it this shot's
    assert VS.short_labels(one, own=['Cement.'], shared=['cement']) == []   # case and a trailing full stop aside


def test_a_checkers_own_must_needs_one_of_the_four_kinds():
    def added(kind):
        store = motion_store()
        return verdict(store, upload(store), ALL, extra=[{'group': 'seen', 'pass': False, 'where': 'at 2 s', 'rule': 'A label is cut.', 'class': 'must', 'kind': kind}])
    assert added('it looks wrong')['failed'] == [] and added('it looks wrong')['notes'] == ['A label is cut.']
    assert added('A label that cannot be read.')['failed'] == ['A label is cut.'] and added('a wrong count')['failed'] == ['A label is cut.']


def test_a_rule_not_seen_twice_in_a_round_is_a_failed_must():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {SOLID: True, EVEN: 'not seen', LEAVES: True})
    out = verdict(store, sha, {EVEN: 'not seen'})   # a should, not seen again in the same round
    assert out['failed'] == [EVEN] and out['not_seen'] == [] and 'round 2' in out['next']
    assert saved(store)['motion_checks']['MO1'][-1]['rules'][1]['class'] == 'must'


def test_once_a_must_always_a_must_and_no_downgrade_without_rules():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {SOLID: False, EVEN: True, LEAVES: True})
    sha2 = upload(store, project(**{'style.css': 'body { margin: 0; }'}), rules=RULES.replace('1. must:', '1. should:'))
    out = verdict(store, sha2, {SOLID: False}, rnd=2)
    assert out['failed'] == [SOLID] and out['notes'] == []
    bare = motion_store()
    sha3 = upload(bare, rules='')
    out = verdict(bare, sha3, {}, extra=[{'rule': 'The wall is whole.', 'pass': False, 'where': 'at 1 s', 'class': 'should'}])
    assert out['failed'] == ['The wall is whole.'] and out['notes'] == []


def test_no_verdict_without_a_finished_check_of_the_project():
    store = motion_store()
    sha = upload(store)
    with pytest.raises(Problem, match=r'no finished check of .* run `vw motion check --shot MO1 --sha'):
        g(lambda: verdict(store, sha, ALL, conn=Jobs([])))
    failed = [{'id': 'c1', 'run_id': 'run-1', 'unit': 'MO1', 'provider': 'motion', 'status': 'failed', 'request': {'kind': 'motion-check', 'sha256': sha}, 'result': None}]
    with pytest.raises(Problem, match='no finished check'):
        g(lambda: verdict(store, sha, ALL, conn=Jobs(failed)))
    ready = [{**failed[0], 'status': 'ready', 'result': {'ok': True, 'warnings': []}}]
    assert verdict(store, sha, ALL, conn=Jobs(ready))['failed'] == []


# ---------- row 2 (A7): a drawing that continues an earlier one ----------

LINE = ("Continues from MO1: this drawing is built on MO1's project: start from a copy of MO1's files and from MO1's last frame, and open exactly as MO1 "
        "ends (same framing, same size, same parts). It is started only after MO1's project has passed its fact check.")


def continuing():
    store = motion_store()
    two_drawn(store)
    no_sha(store)
    edit_session(store, lambda s: s.update(motion_parts_approved={'sha256': 'p', 'key': 'k', 'parts': []}, motion_parts={'sha256': 'p'}))   # design/221 phase 3c: two drawn graphics, their parts approved
    return store


def test_the_brief_says_the_drawing_is_built_on_the_earlier_project():
    store = continuing()
    assert LINE in VS.motion_brief(store, NEW, [], 'MO2')['brief'] and 'Continues from' not in VS.motion_brief(store, NEW, [], 'MO1')['brief']


def test_a_continuing_drawing_is_refused_until_the_earlier_one_passed_then_gets_its_project_and_last_frame():
    store = continuing()
    with pytest.raises(Problem, match=r'MO2 continues from MO1: build and pass MO1 first'):
        g(lambda: VS.motion_brief(store, NEW, [], 'MO2', build=True, conn=FakeConn([])))
    sha = upload(store)
    verdict(store, sha, {SOLID: True, EVEN: 'not seen', LEAVES: True})
    with pytest.raises(Problem, match='build and pass MO1 first'):   # not clean yet
        g(lambda: VS.motion_brief(store, NEW, [], 'MO2', build=True, conn=FakeConn([])))
    verdict(store, sha, {EVEN: True})
    out = g(lambda: VS.motion_brief(store, NEW, [], 'MO2', build=True, conn=FakeConn([])))
    assert out['continues'] == {'shot_id': 'MO1', 'sha256': sha, 'project_key': f'run-1/visuals/motion/projects/{sha}.zip', 'last_frame_key': '', 'last_second': 3.96}
    snaps = [{'id': 's1', 'run_id': 'run-1', 'unit': 'MO1', 'provider': 'motion', 'status': 'ready', 'request': {'kind': 'motion-snapshot', 'sha256': sha},
              'result': {'snapshots': [{'at': 1.0, 'key': 'k1'}, {'at': 3.96, 'key': 'k-last'}]}},
             {'id': 's2', 'run_id': 'run-1', 'unit': 'MO1', 'provider': 'motion', 'status': 'ready', 'request': {'kind': 'motion-snapshot', 'sha256': 'f' * 64},
              'result': {'snapshots': [{'at': 3.96, 'key': 'other-project'}]}}]
    assert g(lambda: VS.motion_brief(store, NEW, [], 'MO2', build=True, conn=FakeConn(snaps)))['continues']['last_frame_key'] == 'k-last'
    assert VS.motion_brief(store, NEW, [], 'MO2')['lines']['Continues from'] == out['lines']['Continues from']   # the line does not change when MO1 passes


def test_vw_brief_puts_the_earlier_project_and_frame_beside_the_brief():
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "out.get('continues')" in vw and "f'work/motion/{a.shot}/from-{c[\"shot_id\"]}" in vw and 'last-frame.png' in vw and 'vw motion snapshot --shot' in vw


# ---------- the texts ----------

def test_the_texts_say_labels_first_the_binding_and_the_order_of_a_diagram():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d221d_wording_v3 as W
    import fixset2_wording as FIX2   # fix set phase 2: sentences added inside this script's sentences, and one replaced
    stage = FIX2.before(visuals())
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    before = W.before(stage)
    texts = {'common': stage['prompt'], **{p['name']: p['text'] for p in stage['parts']}}
    olds = {'common': before['prompt'], **{p['name']: p['text'] for p in before['parts']}}
    for where, old, new in W.PAIRS:
        assert texts[where].count(new) == 1 and olds[where].count(old) == 1, old[:50]
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').count(new) == 1, file
    later = texts['later']
    assert 'propose the revision, then `vw motion render --shot S`' not in later and 'Put `scene_motion: {sha256, labels, cues}`' not in later
    assert 'the server binds the project that passed to its shot' in later and 'shots of one diagram are built in order' in later
    assert 'copy it to work/motion/S/refs/continues-from.png' not in later and 'from-<that shot>/' in later
    assert '`scene_motion: {labels, cues}`' in texts['plan'] and 'before the first brief' in texts['plan']
    gaps = (ROOT / 'plugin' / 'agents' / 'vw-plan-gaps.md').read_text(encoding='utf-8')
    assert '- `scene_motion` on a drawn shot' in gaps and 'never the corner note' in gaps
    check = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert '"a wrong count", "a wrong fact", "a part that reads as something else" or "a label that cannot be read"' in check and 'from-<shot>/last-frame.png' in check
    skill = (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'start from a copy of the files in `from-<shot>/`' in skill and 'refs/continues-from.png' not in skill
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired for s in W.RETIRED)
    assert 'put scene_motion: {sha256' not in (ROOT / 'server' / 'app' / 'visuals_stage.py').read_text(encoding='utf-8')


# ---------- part C: the style texts and their camera ----------

def test_a_style_that_allows_a_camera_move_says_so_and_bold_keeps_the_frame_on_a_shot_that_explains():
    st = film.styles()
    assert 'When the shot\'s Camera line names Step closer, Pull back or Pan along, the whole view moves that way, as one group.' in st['technical']['text']
    assert 'unless the shot\'s Camera line names a move: then the whole picture moves as one group.' in st['lively']['text']
    assert 'On a shot that explains the frame stays fixed: these cuts are for shots that do not explain.' in st['bold']['text']
    for name, s in st.items():
        assert 120 <= len(re.findall(r'\w+', s['text'])) <= 260, name   # the word pin of test_motion_style_fonts_pure
