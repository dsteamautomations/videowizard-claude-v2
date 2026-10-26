"""design/106 D1-D6: drawing specs are researched before the operator sees them; proportions always; `unknown` only after the sources were tried;
the operator approves, never types sizes; one approval for every spec of the run; the plan check refuses an untried unknown."""
import copy
import json
from fractions import Fraction
from pathlib import Path

import pytest

from app import visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_batch89b_pure import SPEC, graphic_session
from test_visuals_stage_pure import RUN, USER, g, gap_digest, saved, store_with
from test_visuals_pure import GAPS, plan, shot as pshot

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
TRIED = 'not in the client material; the footage frames show no ruler or known object at the cavity; no standard gives it'


def spec(**over):
    s = copy.deepcopy(SPEC)
    s['dimensions'][1]['tried'] = TRIED
    return {**s, **over}


def checked(sp):
    doc = plan([{**pshot('DG1', 0, 100, 'diagram'), 'drawing_spec': sp}, pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    return VC.validate_plan(doc, GAPS, Fraction(25))


# ---------- D2, D3, D6: the plan check ----------

def test_an_unknown_size_without_the_sources_tried_is_refused():
    untried = copy.deepcopy(SPEC)
    untried['dimensions'][1].pop('tried', None)
    with pytest.raises(ValueError, match='record the sources tried'):
        checked(untried)
    out, warns = checked(spec())
    assert out['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec']['dimensions'][1]['tried'] == TRIED


def test_a_spec_of_a_real_object_without_proportions_warns_and_with_them_does_not():
    _, warns = checked(spec())
    assert any(w['kind'] == 'spec_proportions_missing' and w['shot_id'] == 'DG1' for w in warns)
    _, warns = checked(spec(proportions=['brick about 3 : 1.5 : 1', 'both leaves the same thickness', 'the cavity about a third of the wall']))
    assert not any(w['kind'] == 'spec_proportions_missing' for w in warns)


def test_the_new_spec_fields_stay_absent_and_change_no_gap_digest():
    sp = copy.deepcopy(SPEC)
    sp['dimensions'][1]['status'] = 'confirmed'
    sp['dimensions'][1].update(value=40, source='client drawing')
    sp['dimensions'][1].pop('tried', None)   # an old spec: the new keys absent
    out, _ = checked(sp)
    stored = out['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec']
    assert 'proportions' not in stored and all('tried' not in d for d in stored['dimensions'])
    doc, _ = graphic_session()
    with_new = copy.deepcopy(doc)
    with_new['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec'] = spec(proportions=['both leaves the same thickness'])
    assert gap_digest(doc, doc['gaps'][0]) == gap_digest(with_new, with_new['gaps'][0])   # no re-acceptance
    assert VS.spec_digest(SPEC) != VS.spec_digest(spec(proportions=['x']))   # the spec itself changed: it is approved again


# ---------- D3: the operator sees the risk in one line ----------

def test_the_spec_table_shows_proportions_and_the_risk_of_an_unknown_size():
    rows = VS.spec_table(spec(proportions=['both leaves the same thickness']))
    unknown = next(r for r in rows if r['status'] == 'unknown')
    assert unknown['risk'] == f'cavity width not found ({TRIED}); drawn by eye'
    assert {'part': 'proportion', 'measure': '', 'size': 'both leaves the same thickness', 'source': '', 'status': 'ratio'} in rows


# ---------- D4, D5: approve without typing sizes; one approval for every spec ----------

def spec_store():
    doc, sess = graphic_session()
    doc['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec'] = spec()
    return store_with(sess, doc)


def test_a_spec_is_approved_without_words_and_a_correction_waits_for_the_assistant():
    store = spec_store()
    VS.correct_spec(store, USER, RUN, [], 'DG1', 'the cavity is 50 mm, not unknown')
    assert saved(store)['spec_corrections']['DG1']['words'] == 'the cavity is 50 mm, not unknown'
    out = VS.approve_spec(store, USER, RUN, [], 'DG1', '')
    s = saved(store)
    assert s['spec_approvals']['DG1']['quote'] == 'Approved by SK' and 'DG1' not in s.get('spec_corrections', {})
    with pytest.raises(Problem, match='Say what to correct'):
        g(lambda: VS.correct_spec(store, USER, RUN, [], 'DG1', '  '))


def test_every_spec_of_the_run_is_approved_in_one_call():
    store = spec_store()
    out = VS.approve_specs(store, USER, RUN, [], '')
    assert [r['shot_id'] for r in out['approved']] == ['DG1'] and saved(store)['spec_approvals']['DG1']['digest'] == VS.spec_digest(spec())
    assert VS.approve_specs(store, USER, RUN, [], '')['approved'] == []   # nothing left to approve


def test_the_operator_waits_on_one_spec_item_not_one_per_shot():
    doc, sess = graphic_session()
    doc['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec'] = spec()
    items = [i for i in VS.waiting(sess, doc, 'VW-9', []) if 'spec' in i['label'].lower()]
    assert len(items) == 1 and items[0]['label'] == 'Drawing specs · 1 to approve' and items[0]['link'].endswith('#pictures/specs/specs')


# ---------- D1: research first; the page and chat ----------

def test_the_procedure_researches_before_the_operator_sees_a_spec():
    doc = json.loads((ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8'))
    steps = next(s for s in doc['stages'] if s['name'] == 'visuals')['steps']
    text = steps[2].lower()
    for words in ('before a drawing spec is shown', 'the operator is never asked to type a size', 'one warning and yes covers every spec of the run', 'proportions', 'tried'):
        assert words in text, words


def test_the_page_offers_one_approval_and_a_correction_box_never_a_size_box():
    assert 'your words for these sizes' not in PAGE
    assert 'data-a="approve-specs"' in PAGE and 'data-a="correct-spec"' in PAGE and 'data-item="specs"' in PAGE
    assert 'no size or proportion given' in PAGE   # an empty spec shows as a row to research, never silently
