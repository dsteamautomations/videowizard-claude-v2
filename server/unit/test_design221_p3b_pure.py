"""design/221 (SK, 19 Nov 2026): the critic's seven points on phase 2 (design/_work/design221-critic-phase2.md).
A1: the labels and cues of every drawn shot go in the plan with the plan (scene_motion without sha256); the brief before a build is refused while a
drawn shot that carries text has none; a clean verdict binds the passed project to its shot (motion_bound) and the render needs no plan change; a
later upload clears the binding; a verdict record keeps the digest of the rules and brief it answered and a record for other rules is ignored.
A2: whole labels in the short-label rule. A3: a checker's own must only with one of the four must kinds. A4: "not seen" twice in a round is a failed
must. A5: once a must, always a must; no downgrade without rules. A6: no verdict with a database and no finished check of the project.
Without a database."""
import json
import sys
from pathlib import Path

import pytest

from app import pictures as P, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import FakeConn, motion_shot, motion_store, project
from test_design221_p1_pure import NEW, edit_plan, visuals
from test_design221_p2_pure import EVEN, LEAVES, RULES, SOLID, WARN, Jobs, selectable, upload, verdict
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
    for over in ({'carries_text': True}, {'message': 'The course spreads the load.'},
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


# ---------- the texts ----------

def test_the_texts_say_labels_first_and_the_binding():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d221d_wording_v3 as W
    stage = visuals()
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
    assert 'the server binds the project that passed to its shot' in later
    assert '`scene_motion: {labels, cues}`' in texts['plan'] and 'before the first brief' in texts['plan']
    gaps = (ROOT / 'plugin' / 'agents' / 'vw-plan-gaps.md').read_text(encoding='utf-8')
    assert '- `scene_motion` on a drawn shot' in gaps and 'never the corner note' in gaps
    check = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert '"a wrong count", "a wrong fact", "a part that reads as something else" or "a label that cannot be read"' in check
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired for s in W.RETIRED)
    assert 'put scene_motion: {sha256' not in (ROOT / 'server' / 'app' / 'visuals_stage.py').read_text(encoding='utf-8')
