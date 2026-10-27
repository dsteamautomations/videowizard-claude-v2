"""design/96, Release 2: fair checks (design/93 X1-X4, J1-J3; the course's C1)."""
import json
from pathlib import Path

import pytest

from app import image_check as IC, library, visual_contract as VC, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from test_design94_r1_pure import cheap, film, image, pic, refs   # noqa: F401  (cheap: the autouse price fixture)
from test_l60_busy_pure import JOB, Locks, image_job_store
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, g, plan_doc, saved, session, shot, store_with

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
FAILED = {'check': 'label: Rat-trap bond', 'weight': 'must', 'pass': False, 'seen': 'the label reads Rat-trap bnod'}


def checked(rid, shot_id='DG1', **extra):
    """A candidate whose check failed one must line."""
    return pic(rid, shot_id, check={'lines': [FAILED], 'must_failed': [FAILED], 'model': 'm'}, server_checklist=[{'check': FAILED['check'], 'pass_when': 'reads exactly', 'weight': 'must'}], **extra)


# ---------- X1: no automatic fix; a fix on request with its line and cost ----------

def test_a_failed_check_no_longer_makes_a_fix_on_its_own(monkeypatch):
    log, store = [], image_job_store()
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'connect', lambda: Locks(log))
    monkeypatch.setattr(IC, 'run_check', lambda st, sess, r, result, f: {'lines': [], 'must_failed': [FAILED]})
    monkeypatch.setattr(VS, 'generate_image', lambda *a, **k: pytest.fail('a fix was made without a request'))
    VW.check_image(JOB, {'key': 'run-1/visuals/references/K1.png'})
    row = json.loads(store.files['run-1/visuals/session.json'])['references']['K1']
    assert row['check']['must_failed'] and 'fix_queued' not in row and not hasattr(IC, 'queue_fix')


def test_a_fix_on_request_names_its_line_and_cost_and_is_labelled():
    doc, sess = film(references=refs(checked('K1')))
    store = store_with(sess, doc)
    out = VS.request_fix(FakeConn([]), store, USER, RUN, [], 'K1')
    s = saved(store)
    fix = s['references'][out['reference_id']]
    assert out['for'] == 'label: Rat-trap bond' and out['cost_inr'] == 4.0 and out['of'] == 'K1'
    assert s['references']['K1']['fix_queued'] == out['reference_id'] and fix['fix_of'] == 'K1' and fix['fix_for'] == 'label: Rat-trap bond' and fix['shot_id'] == 'DG1'
    view = {r['id']: r for r in VS.page_view(FakeConn([]), store, RUN, [], 'VW-9')['references']}
    assert view[out['reference_id']]['fix_for'] == 'label: Rat-trap bond'   # X2: the page labels it


@pytest.mark.parametrize('row, message', [
    (pic('K1', 'DG1', check={'lines': [], 'must_failed': []}), 'nothing to fix: no must line failed'),
    (checked('K1', fix_of='K0'), 'a fix is not fixed again'),
    (checked('K1', fix_queued='F9'), 'a fix of this picture is already made: F9'),
    (checked('K1', status='approved'), 'only a candidate is fixed'),
    (pic('K1', 'DG1'), 'the check is still running'),
    (pic('K1', 'DG1', check={'lines': [{**FAILED, 'pass': None}], 'must_failed': []}), 'nothing to fix'),   # X4: an undecided line never starts a fix
])
def test_a_fix_request_is_refused_with_its_reason(row, message):
    doc, sess = film(references=refs(row))
    with pytest.raises(Problem, match=message):
        g(lambda: VS.request_fix(FakeConn([]), store_with(sess, doc), USER, RUN, [], 'K1'))


# ---------- X3: the spend counts fixes apart ----------

def test_the_spend_counts_fixes_apart_and_knows_an_old_fix_by_its_name():
    def job(name, fix_of=None):
        return {'run_id': 'run-1', 'provider': 'openai', 'status': 'ready', 'cost': None,
                'request': {'reference': {'name': name, **({'fix_of': fix_of} if fix_of else {})}}}
    sp = VS.visuals_spend(FakeConn([job('keyframe-TOWN'), job('keyframe-WALL'), job('keyframe-TOWN-fix'), job('state-B-2', fix_of='S1')]), RUN)
    assert sp['images'] == 4 and sp['fixes'] == 2


def test_a_fix_job_records_what_it_fixes():
    doc, sess = film(references=refs(checked('K1')))
    conn = FakeConn([])
    VS.request_fix(conn, store_with(sess, doc), USER, RUN, [], 'K1')
    request = conn.inserted[-1][2].obj
    assert request['reference']['fix_of'] == 'K1'


# ---------- J1: each step is checked for what it shows ----------

def build_film():
    states = [{'what_appears': 'the section of the wall', 'hold_s': 3}, {'what_appears': 'the cavities', 'hold_s': 3, 'words': 'an innovative bond'},
              {'what_appears': 'the air gap and the words: the cavity holds air', 'hold_s': 4}]
    an = shot('AN1', 0, 250, 'animation', states=states, claims=['the cavity holds air', 'fewer bricks are used'], descriptors=['innovative'],
              depicts='a rat-trap wall in section', drawing_spec={'parts': ['wall'], 'relationships': ['the cavity is inside the wall'], 'dimensions': [], 'label': ''})
    doc = plan_doc([an, shot('DG1', 250, 500, 'diagram', claims=['the cavity holds air'], depicts='a rat-trap wall in section')], [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc), repeat_rules='refuse')
    return doc, sess


def ready(store, out):
    """The worker's part: the picture stored, a candidate with its hash."""
    s = saved(store)
    s['references'][out['reference_id']].update(status='candidate', sha256='sha-' + out['reference_id'], key='k')
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    return out


def lines_for(store, out):
    return {l['check'] for l in saved(store)['references'][out['reference_id']].get('server_checklist') or []}


def test_each_state_is_checked_only_for_what_it_shows_and_keeps_the_states_before():
    doc, sess = build_film()
    store = store_with(sess, doc)
    s1 = ready(store, image(store, shot_id='AN1', request_id='s1'))
    s2 = ready(store, image(store, kind='state', parents=[s1['reference_id']], request_id='s2'))
    s3 = ready(store, image(store, kind='state', parents=[s2['reference_id']], request_id='s3'))
    one, two, three = lines_for(store, s1), lines_for(store, s2), lines_for(store, s3)
    assert not any(c.startswith(('claim:', 'word:', 'depicts:', 'relationship:')) for c in one)
    assert 'word: innovative' in two and 'claim: the cavity holds air' not in two and 'depicts: a rat-trap wall in section' not in two
    assert {'word: innovative', 'claim: the cavity holds air', 'claim: fewer bricks are used', 'depicts: a rat-trap wall in section', 'relationship: the cavity is inside the wall'} <= three


def test_a_still_diagram_is_one_state_with_every_line():
    doc, sess = build_film()
    store = store_with(sess, doc)
    assert {'claim: the cavity holds air', 'depicts: a rat-trap wall in section'} <= lines_for(store, image(store, shot_id='DG1'))


# ---------- J2: rules by graphic type ----------

def kind_film(kind):
    doc = plan_doc([shot('DG1', 0, 250, 'diagram', claims=['the cavity holds air'], depicts='a wall', descriptors=['strong'], **({'graphic_kind': kind} if kind else {}))],
                   [shot('VS1', 900, 1150, 'video')])
    return doc, session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc))


def answered(text):
    return {'exact_text': [{'text': text, 'place': {'region': 'centre of the frame'}, 'size_pct': 6}]}   # design/111 F13: an entry with its place and size


@pytest.mark.parametrize('kind', ['title', 'text'])
def test_a_title_or_text_card_is_checked_for_its_words_size_and_readability_only(monkeypatch, kind):
    monkeypatch.setattr(library, 'check_answer', lambda answer, prompt: None)
    doc, sess = kind_film(kind)
    store = store_with(sess, doc)
    out = image(store, shot_id='DG1', answer=answered('Fewer materials, same strength'))
    rows = {l['check']: l for l in saved(store)['references'][out['reference_id']]['server_checklist']}
    assert not any(c.startswith(('claim:', 'word:', 'depicts:')) for c in rows)
    label = rows['label: Fewer materials, same strength']['pass_when']
    assert 'leader line' not in label and '6 %' in label and 'spelled' in label


def test_only_a_diagram_has_leader_lines_and_a_chart_keeps_its_claims(monkeypatch):
    monkeypatch.setattr(library, 'check_answer', lambda answer, prompt: None)
    for kind, leader, claims in ((None, True, True), ('diagram', True, True), ('chart', False, True), ('map', False, True)):
        doc, sess = kind_film(kind)
        store = store_with(sess, doc)
        out = image(store, shot_id='DG1', answer=answered('25 % fewer bricks'))
        rows = {l['check']: l for l in saved(store)['references'][out['reference_id']]['server_checklist']}
        assert ('leader line' in rows['label: 25 % fewer bricks']['pass_when']) is leader, kind
        assert ('claim: the cavity holds air' in rows) is claims, kind


def test_a_plan_without_a_graphic_kind_is_a_diagram():
    assert VC.Shot.model_fields['graphic_kind'].default == 'diagram'


# ---------- J3, X2, X3: the page ----------

def test_the_page_offers_a_fix_labels_it_counts_fixes_and_says_state_n_of_m():
    assert 'data-a="fix"' in PAGE and 'Try a fix (₹' in PAGE and "'fix of '" in PAGE and ' fixes' in PAGE
    assert "' of '+s.state_order.length" in PAGE and "' · ok'" in PAGE and "' to look at'" in PAGE


# ---------- C1: an edit names its pictures ----------

def test_an_edit_that_does_not_name_each_picture_is_warned():
    assert library.image_names_missing('Image 1 is the wall; take the bond from it.', 3) == [2, 3]
    assert library.image_names_missing('Image 1 is the wall; images 2 onward are its sheets.', 3) == []
    assert library.image_names_missing('Image 1 the wall, images 2–3 the bricks.', 3) == []
    assert library.image_names_missing('Image 1, Image 2 and Image 3.', 3) == []
    assert library.image_names_missing('A wall.', 0) == []


def test_generate_image_refuses_an_edit_naming_too_few_pictures_but_not_a_generate():   # design/111 F21: the warning of design/96 C1 became the refusal
    doc, sess = film(references=refs(pic('S1', status='approved', kind='sheet'), pic('S2', status='approved', kind='sheet')))
    store = store_with(sess, doc)
    with pytest.raises(Problem, match='does not say what Image 2 is for'):
        g(lambda: image(store, shot_id='DG1', parents=['S1', 'S2'], prompt='Image 1 is the wall section.'))
    out = image(store, shot_id='DG1', request_id='q2')
    assert not any('Image 1 to Image' in w for w in out.get('warnings') or [])
