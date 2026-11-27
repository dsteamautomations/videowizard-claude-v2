"""Release 1 of 27 Nov 2026, phase 3, part D (SK approved: no card, one status line).

A spec the operator corrected came back for a second approval once the assistant had revised it. Now the plan change that revises it records
it as approved with the operator's own words, and one line says which rows changed. The same when the plan change applies the operator's
answer to the assistant's question (`--answers`). Each test failed first. Without a database."""
import copy
import json

from app import visuals_stage as VS
from test_design106d_pure import spec_store
from test_design111_f10_pure import material_store
from test_visuals_stage_pure import RUN, USER, saved

SAID = 'the cavity is 50 mm, not unknown'


def plans(store, change, key='DG1'):
    """(session, the plan in force, the same plan with the spec of `key` changed)."""
    s = saved(store)
    prev = VS.current_plan(store, s)
    new = copy.deepcopy(prev)
    change(spec_of(new, key))
    return s, prev, new


def spec_of(plan, key):
    if key.startswith('element:'):
        return next(e for e in plan['elements'] if e['id'] == key[8:])['material_spec']
    return next(sh for g in plan['gaps'] for sc in g['scenes'] for sh in sc['shots'] if sh['id'] == key)['drawing_spec']


def cavity(spec, **to):
    spec['dimensions'][1].update({'value': 50, 'source': 'the operator, on site', 'status': 'confirmed', 'tried': '', **to})


def test_a_spec_revised_under_a_waiting_correction_is_approved_with_the_corrections_words_and_no_card():
    store = spec_store()
    VS.correct_spec(store, USER, RUN, [], 'DG1', SAID)
    assert saved(store)['spec_corrections']['DG1']['spec'] == spec_of(VS.current_plan(store, saved(store)), 'DG1')   # the spec as it was is kept, not only its fingerprint
    s, prev, new = plans(store, cavity)
    told = VS.revise_specs(s, prev, new, None, USER, 2)
    got = s['spec_approvals']['DG1']
    assert (got['digest'], got['quote'], got['by'], got['revised']) == (VS.spec_digest(spec_of(new, 'DG1')), SAID, USER['id'], 2)
    assert 'DG1' not in s['spec_corrections']
    assert told == [{'key': 'DG1', 'words': SAID, 'line': f"The spec of DG1 was revised as you said ('{SAID}'). Changed: cavity width."}]
    assert not VS.correction_pending(s, 'DG1', spec_of(new, 'DG1'))


def test_the_line_lists_every_row_that_changed():
    store = spec_store()
    VS.correct_spec(store, USER, RUN, [], 'DG1', SAID)
    s, prev, new = plans(store, lambda spec: (cavity(spec), spec['dimensions'][0].update(value=115), spec.update(view='side', proportions=['leaf to cavity about 2 : 1'])))
    line = VS.revise_specs(s, prev, new, None, USER, 2)[0]['line']
    assert line.endswith('Changed: leaf thickness, cavity width, view, proportions.')


def test_a_revision_that_fails_the_source_check_stays_with_the_assistant_and_says_the_fault():
    store = spec_store()
    VS.correct_spec(store, USER, RUN, [], 'DG1', SAID)
    s, prev, new = plans(store, lambda spec: spec['dimensions'][1].update(tried=''))   # an unknown size that says nothing of what was tried
    assert VS.revise_specs(s, prev, new, None, USER, 2) == []
    c = s['spec_corrections']['DG1']
    assert 'DG1' not in (s.get('spec_approvals') or {}) and c['fault'] and VS.correction_pending(s, 'DG1', spec_of(new, 'DG1'))   # not asked of the operator
    assert c['spec'] == spec_of(prev, 'DG1')   # the rows are still compared with the spec the operator corrected
    again = copy.deepcopy(new)
    cavity(spec_of(again, 'DG1'))
    assert [t['key'] for t in VS.revise_specs(s, new, again, None, USER, 3)] == ['DG1'] and 'DG1' not in s['spec_corrections']   # revised again: recorded


def test_a_material_spec_the_same():
    store = material_store()
    VS.correct_spec(store, USER, RUN, [], 'element:BRICK', 'the joint is 12 mm on this site')
    s, prev, new = plans(store, lambda spec: spec['dimensions'][3].update(value=12), key='element:BRICK')
    told = VS.revise_specs(s, prev, new, None, USER, 2)
    assert told[0]['line'] == "The material spec of BRICK was revised as you said ('the joint is 12 mm on this site'). Changed: joint thickness."
    assert VS.material_approved(s, next(e for e in new['elements'] if e['id'] == 'BRICK')) and 'element:BRICK' not in s['spec_corrections']


def approved(store, key='DG1'):
    s = saved(store)
    s.setdefault('spec_approvals', {})[key] = {'digest': VS.spec_digest(spec_of(VS.current_plan(store, s), key)), 'quote': 'Approved', 'by': USER['id'], 'at': 'then'}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    return store


def test_a_spec_changed_by_the_plan_change_that_applies_the_operators_answer_is_approved_the_same_way():
    s, prev, new = plans(approved(spec_store()), cavity)
    answer = {'item': 'DG1', 'question': 'How wide is the cavity?', 'answer': '50 mm', 'holds': ['DG1']}
    told = VS.revise_specs(s, prev, new, answer, USER, 2)
    assert told[0]['line'] == "The spec of DG1 was revised as you said ('50 mm'). Changed: cavity width."
    assert s['spec_approvals']['DG1']['digest'] == VS.spec_digest(spec_of(new, 'DG1')) and s['spec_approvals']['DG1']['quote'] == '50 mm'


def test_a_change_with_no_correction_and_no_answer_is_still_asked():
    s, prev, new = plans(approved(spec_store()), cavity)
    assert VS.revise_specs(s, prev, new, None, USER, 2) == []
    assert s['spec_approvals']['DG1']['digest'] != VS.spec_digest(spec_of(new, 'DG1'))
    other = {'item': 'OTHER', 'question': 'q', 'answer': 'a', 'holds': ['OTHER']}   # an answer about something else
    assert VS.revise_specs(s, prev, new, other, USER, 2) == []
    s2, prev2, new2 = plans(spec_store(), cavity)   # a spec the operator never approved, changed with their answer: they have not seen it, so it is asked
    assert VS.revise_specs(s2, prev2, new2, {'item': 'DG1', 'question': 'q', 'answer': 'a'}, USER, 2) == []


def test_a_correction_whose_spec_did_not_change_keeps_waiting():
    store = spec_store()
    VS.correct_spec(store, USER, RUN, [], 'DG1', 'is the cavity really unknown?')
    s, prev, new = plans(store, lambda spec: None)
    assert VS.revise_specs(s, prev, new, None, USER, 2) == [] and s['spec_corrections']['DG1']['words'] == 'is the cavity really unknown?'


def test_the_correction_no_longer_promises_a_second_approval():
    out = VS.correct_spec(spec_store(), USER, RUN, [], 'DG1', SAID)
    assert 'then you approve it' not in out['next'] and 'recorded as approved with your words' in out['next']


def test_the_plan_change_itself_records_the_revision_and_keeps_a_faulty_one_with_the_assistant():
    from test_visuals_stage_pure import g
    for change, good in ((cavity, True), (lambda spec: spec['dimensions'][1].update(tried=''), False)):
        store = spec_store()
        VS.correct_spec(store, USER, RUN, [], 'DG1', SAID)
        s, _, new = plans(store, change)
        out = g(lambda: VS.guarded(lambda: VS.new_version(store, RUN, s, new, USER, [], '')))
        assert [r['key'] for r in out['spec_revised']] == (['DG1'] if good else []) and bool((s['spec_corrections'].get('DG1') or {}).get('fault')) is not good

