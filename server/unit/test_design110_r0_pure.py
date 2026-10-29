"""design/110 rule 0: an open question is a server state on a picture, a shot or an element. Asked once, answered by the operator, shown on the
card, in status and in waiting; derived work from that item waits; the server asks itself at two forks it can see (two pictures approved for
one slot; a flawed parent); Done can be undone until the next step used it; a new source marks the element's sheet; the page stores the
operator's own picture as an approved reference."""
import json
from io import BytesIO
from pathlib import Path

import pytest

from app import image_check as IC, visuals_stage as VS
from app.errors import Problem
from test_design106_pure import approvable, revise_start, start_store
from test_visuals_stage_pure import RUN, USER, FakeConn, g, plan_doc, ref, saved, session, shot, store_with

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def png(w=64, h=48):
    from PIL import Image
    buf = BytesIO()
    Image.new('RGB', (w, h), (120, 80, 40)).save(buf, 'PNG')
    return buf.getvalue()


def put(store, s):
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')


# ---------- the state: ask, answer, shown ----------

def test_a_question_is_asked_once_shown_everywhere_and_answered_by_the_operator():
    store = start_store()
    out = VS.ask(store, USER, RUN, [], 'K1', 'Which brick length: 230 mm or 190 mm?', ['230 mm (one more picture, 4 INR)', '190 mm'], cost_inr=4.0)
    assert out['item'] == 'K1' and 'nothing is made from K1' in out['next']
    q = saved(store)['questions']['K1']
    assert q['question'].startswith('Which brick') and len(q['choices']) == 2 and q['by'] == USER['id'] and q['cost_inr'] == 4.0 and q['at']
    with pytest.raises(Problem, match='K1 already waits'):
        g(lambda: VS.ask(store, USER, RUN, [], 'K1', 'again?', ['a', 'b']))
    with pytest.raises(Problem, match='not a picture, a shot or an element'):
        g(lambda: VS.ask(store, USER, RUN, [], 'nope', 'x?', ['a', 'b']))
    with pytest.raises(Problem, match='at least two choices'):
        g(lambda: VS.ask(store, USER, RUN, [], 'VS1', 'x?', ['a']))
    st = VS.status(FakeConn([]), store, RUN, [], repair=False)
    assert st['questions']['K1']['question'] == q['question'] and st['questions']['K1']['choices'] == q['choices']
    assert any(w['item'] == 'K1' and w['label'].startswith('Question · K1') for w in st['waiting'])
    view = VS.page_view(FakeConn([]), store, RUN, [], 'VW-9', False)
    assert view['questions']['K1']['choices'] == q['choices']
    with pytest.raises(Problem, match='No open question on VS1'):
        g(lambda: VS.answer(store, USER, RUN, [], 'VS1', '190 mm'))
    with pytest.raises(Problem, match='Say the answer'):
        g(lambda: VS.answer(store, USER, RUN, [], 'K1', '  '))
    out = VS.answer(store, USER, RUN, [], 'K1', '190 mm')
    s = saved(store)
    assert 'K1' not in s['questions'] and s['answered'][-1]['item'] == 'K1' and s['answered'][-1]['answer'] == '190 mm' and s['answered'][-1]['answered_by'] == USER['id']
    assert out['item'] == 'K1' and out['answer'] == '190 mm'
    assert VS.status(FakeConn([]), store, RUN, [], repair=False)['questions'] == {}


# ---------- derived work waits ----------

def test_derived_work_from_an_item_with_an_open_question_is_refused():
    store = start_store()
    VS.ask(store, USER, RUN, [], 'K1', 'Keep K1 as the parent?', ['yes', 'no'])
    waits = "K1 waits for the operator's answer: Keep K1 as the parent"
    with pytest.raises(Problem, match=waits):
        g(lambda: revise_start(store, role='start'))   # K1 among the parents
    with pytest.raises(Problem, match=waits):
        g(lambda: VS.approve_reference(store, USER, RUN, [], 'K1', 'a' * 64, '', FakeConn([])))
    with pytest.raises(Problem, match=waits):
        g(lambda: VS.request_fix(FakeConn([]), store, USER, RUN, [], 'K1'))
    VS.answer(store, USER, RUN, [], 'K1', 'yes')
    VS.ask(store, USER, RUN, [], 'VS1', 'Shorten VS1 to 4 s?', ['yes', 'no'])
    waits = "VS1 waits for the operator's answer: Shorten VS1"
    with pytest.raises(Problem, match=waits):
        g(lambda: revise_start(store, role='start'))   # made for VS1
    with pytest.raises(Problem, match=waits):
        g(lambda: VS.prepare_take(store, USER, RUN, [], {'shot_id': 'VS1', 'motion_prompt': 'm', 'subject_reconciliation': {'E1': 'the mason'}, 'start_image': 'R1', 'end_image': 'R2', 'continuity_notes': 'c'}))
    with pytest.raises(Problem, match=waits):
        g(lambda: VS.bind(store, USER, RUN, [], 'VS1', {}, {}, ''))
    VS.answer(store, USER, RUN, [], 'VS1', 'no')
    assert revise_start(store, role='start')['reference_id']   # answered: the work goes on


# ---------- fork 3: two pictures approved for one slot ----------

def test_a_second_approved_start_for_one_shot_asks_which_to_keep():
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    approvable(store, rid)
    with pytest.raises(Problem, match='Two start images for VS1'):
        g(lambda: VS.approve_reference(store, USER, RUN, [], rid, 'a' * 64, '', FakeConn([])))
    s = saved(store)
    q = s['questions']['VS1']
    assert q['fork'] == 'slot' and set(q['choices']) == {'K1', rid} and q['by'] == 'server' and s['references'][rid]['status'] == 'candidate'
    with pytest.raises(Problem, match='one of'):
        g(lambda: VS.answer(store, USER, RUN, [], 'VS1', 'both'))
    VS.answer(store, USER, RUN, [], 'VS1', rid)
    s = saved(store)
    assert s['references']['K1']['status'] == 'rejected' and 'the operator kept' in s['references']['K1']['rejection']['notes'] and 'VS1' not in s['questions']
    row = VS.approve_reference(store, USER, RUN, [], rid, 'a' * 64, '', FakeConn([]))
    assert row['status'] == 'approved' and row.get('end_reference_id')


# ---------- fork 4: a flawed parent ----------

def test_a_parent_approved_with_a_failed_must_line_is_asked_about_once():
    store = start_store()
    s = saved(store)
    s['references']['K1']['check'] = {'lines': [{'check': 'cavity', 'weight': 'must', 'pass': False, 'seen': 'no cavity'}], 'must_failed': [{'check': 'cavity', 'weight': 'must', 'pass': False, 'seen': 'no cavity'}]}
    put(store, s)
    with pytest.raises(Problem, match="K1 was approved with a failed must line \\(cavity\\)"):
        g(lambda: revise_start(store, role='start'))
    q = saved(store)['questions']['K1']
    assert q['fork'] == 'parent' and q['choices'] == ['use it as the parent', 'make a new one'] and q['by'] == 'server'
    VS.answer(store, USER, RUN, [], 'K1', 'use it as the parent')
    assert saved(store)['references']['K1']['parent_ok'] is True
    rid = revise_start(store, role='start')['reference_id']
    assert rid and 'K1' not in saved(store)['questions']
    s = saved(approvable(store, rid))
    s['references'][rid]['check'] = s['references']['K1']['check']
    put(store, s)
    fix = VS.generate_image(FakeConn([]), store, USER, RUN, [], IC.fix_body(s['references'][rid], {'check': 'cavity', 'pass_when': 'the cavity shows', 'weight': 'must'}))
    assert fix['reference_id'] and rid not in saved(store)['questions']   # a fix is the remedy for the failed line, never a question


# ---------- Done can be undone until the next step used it ----------

def round_store(pass_, picked=(), sheet=None):
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    refs = {'F1': {**ref('F1', 'approved'), 'kind': 'frame', 'element_id': 'E1'}}
    if picked:
        refs['W1'] = {**ref('W1', 'approved'), 'kind': 'web', 'element_id': 'E1'}
    if sheet:
        refs['SH1'] = {**ref('SH1', sheet), 'kind': 'sheet', 'element_id': 'E1', 'generation': {'op': 'edit', 'parents': [{'id': 'F1'}, {'id': 'W1'}]}}
    rd = {'pass': pass_, 'quote': 'yes', 'elements': {'E1': {'frames': ['F1'], 'keywords': 'village mason', 'verdict': 'search', 'search_id': 'S1', 'error': None}}}
    searches = {'S1': {'search_id': 'S1', 'element_id': 'E1', 'keywords': 'village mason', 'results': [{'n': 1, 'image_url': 'https://img.example/1.jpg', 'site': 'x'}], 'picked': list(picked)}}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', references=refs, round=rd, searches=searches)
    return store_with(sess, doc)


def test_done_can_be_undone_until_the_next_step_used_the_result():
    store = round_store(2)
    out = VS.round_undo(store, USER, RUN, [], 'undo pass 1')
    assert out['pass'] == 1 and saved(store)['round']['pass'] == 1 and saved(store)['round']['undone'][-1]['from'] == 2
    with pytest.raises(Problem, match='pick is saved'):
        g(lambda: VS.round_undo(round_store(2, picked=[1]), USER, RUN, [], 'undo'))
    store = round_store('complete', picked=[1])
    assert VS.round_undo(store, USER, RUN, [], 'undo')['pass'] == 2
    with pytest.raises(Problem, match='sheet SH1 was made'):
        g(lambda: VS.round_undo(round_store('complete', picked=[1], sheet='candidate'), USER, RUN, [], 'undo'))
    with pytest.raises(Problem, match='Nothing to undo'):
        g(lambda: VS.round_undo(round_store(1), USER, RUN, [], 'undo'))


# ---------- a new source marks the sheet; the operator's own picture ----------

def test_a_new_source_marks_the_elements_sheet_and_a_new_sheet_clears_it():
    store = round_store('complete', picked=[1], sheet='approved')
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'mine', 'kind': 'supplied', 'subject': 'the mason'}
    VS.add_reference(FakeConn([]), store, USER, RUN, [], body, png())
    s = saved(store)
    assert s['references']['SH1']['sources_changed'] is True
    st = VS.status(FakeConn([]), store, RUN, [], repair=False)
    assert next(r for r in st['references'] if r['id'] == 'SH1')['sources_changed'] is True
    assert any(w['label'] == 'Reference sheet · E1 · sources changed' and w['item'] == 'SH1' for w in st['waiting'])
    s['references']['SH2'] = {**ref('SH2', 'candidate'), 'kind': 'sheet', 'element_id': 'E1', 'sha256': 'b' * 64}
    put(store, s)
    VS.approve_reference(store, USER, RUN, [], 'SH2', 'b' * 64, '', FakeConn([]))
    assert not saved(store)['references']['SH1'].get('sources_changed')


def test_the_page_stores_the_operators_own_picture_as_an_approved_reference():
    store = round_store(1)
    out = VS.supply_own(FakeConn([]), store, USER, RUN, [], 'E1', content=png(), name='my-photo.png')
    row = saved(store)['references'][out['id']]
    assert row['kind'] == 'supplied' and row['status'] == 'approved' and row['approval']['quote'] == 'Added by the operator on the page' and row['name'] == 'my-photo.png'
    with pytest.raises(Problem, match='a file or an https link'):
        g(lambda: VS.supply_own(FakeConn([]), store, USER, RUN, [], 'E1', content=None, url='http://x/y.png'))
    with pytest.raises(Problem, match='not an element'):
        g(lambda: VS.supply_own(FakeConn([]), store, USER, RUN, [], 'E9', content=png()))


def test_redoing_one_element_leaves_the_others_references_alone():
    store = round_store('complete', picked=[1], sheet='approved')
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    doc['elements'].append({'id': 'E2', 'name': 'Brick kiln', 'kind': 'place', 'identity': 'representative', 'requirements': 'a kiln'})
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    before = {k: dict(v) for k, v in saved(store)['references'].items()}
    VS.supply_own(FakeConn([]), store, USER, RUN, [], 'E2', content=png(), name='kiln.png')
    after = saved(store)['references']
    assert all(after[k] == v for k, v in before.items())   # E1's frame, pick and sheet untouched (no sources_changed on E1's sheet)


# ---------- the page and the words ----------

def test_the_page_shows_the_question_the_controls_and_the_undo():
    assert 'Waiting for operator decision' in PAGE and 'data-a="answer"' in PAGE and "if(a==='answer')" in PAGE
    assert 'Add your own picture' in PAGE and 'data-a="supply"' in PAGE and 'type="file"' in PAGE and 'FileReader' in PAGE
    assert 'data-a="round-undo"' in PAGE and 'Undo Done' in PAGE and 'Done with ' in PAGE
    assert "searchBox+webFold" in PAGE or 'searchBox+' in PAGE   # the search box stays outside the fold
    assert 'sources changed' in PAGE


def test_the_procedure_and_the_tool_text_carry_rule_0():
    proc = (ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8')
    for words in ('STOP AND ASK', 'vw visuals ask', 'vw visuals answer', 'Add your own picture', 'round --undo', 'never guess'):
        assert words in proc, words
    vwmd = (ROOT.parent / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'vw visuals ask' in vwmd and 'one question' in vwmd
