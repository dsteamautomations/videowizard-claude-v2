"""design/119 set D, rule 2: once an element's sources are approved and it has no sheet, the server cues the sheet like the golden picture; the sheet
prompt gets the server's lines (each required view labelled, the thing alone on plain ground, one job line per source) and the check one must line per
required view and one for nothing but the thing."""
import json

from app import visuals_stage as VS
from test_design111_f11_pure import golden_store, image, put
from test_visuals_stage_pure import FakeConn, RUN, ref, saved


def sheet_store():
    store = golden_store()
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    doc['elements'].append({'id': 'E3', 'name': 'Short straw broom', 'kind': 'object', 'identity': 'representative', 'requirements': 'a short coconut-stalk broom', 'required_views': ['front', 'in the hand']})
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    s['references']['W3'] = {**ref('W3', 'approved'), 'kind': 'web', 'element_id': 'E3'}
    s['references']['U3'] = {**ref('U3', 'approved'), 'kind': 'supplied', 'element_id': 'E3'}
    put(store, s)
    return store


def test_the_sheet_is_due_once_the_sources_are_approved_and_not_while_one_is_being_made():
    store = sheet_store()
    due = VS.status(FakeConn([]), store, RUN, [], repair=False)['sheet_due']
    assert due == [{'element_id': 'E3', 'next': 'write the reference sheet of E3 now: `vw visuals image --element E3 --kind sheet --parents W3,U3 …` (front, in the hand; the thing alone on plain ground)'}]
    assert VS.sheet_due(saved(store), json.loads(store.files['run-1/visuals/plan-v1.json'])['document']) == due
    out = image(store, element_id='E3', kind='sheet', name='sheet-E3', subject='the broom', parents=['W3', 'U3'],
                prompt='Image 1 is the web picture of the broom: take its form. Image 2 is the supplied picture: take its binding.')
    assert VS.status(FakeConn([]), store, RUN, [], repair=False)['sheet_due'] == []   # being made: not due twice
    assert out['reference_id']


def test_the_sheet_prompt_and_check_carry_the_views_and_the_thing_alone():
    store = sheet_store()
    out = image(store, element_id='E3', kind='sheet', name='sheet-E3', subject='the broom', parents=['W3', 'U3'],
                prompt='Image 1 is the web picture of the broom: take its form. Image 2 is the supplied picture: take its binding.')
    r = saved(store)['references'][out['reference_id']]
    assert 'Reference sheet of Short straw broom: the views front, in the hand, each labelled; the thing alone on plain ground, nothing else in the frame.' in r['generation']['prompt']
    checks = [l['check'] for l in r['server_checklist']]
    assert 'view: front' in checks and 'view: in the hand' in checks and 'nothing but the thing' in checks and all(l['weight'] == 'must' for l in r['server_checklist'] if l['check'].startswith(('view:', 'nothing but')))


def test_an_element_with_no_approved_source_or_with_a_sheet_is_not_due():
    store = golden_store()   # E2 has its sheet S2; E1 has no sources
    assert VS.status(FakeConn([]), store, RUN, [], repair=False)['sheet_due'] == []
