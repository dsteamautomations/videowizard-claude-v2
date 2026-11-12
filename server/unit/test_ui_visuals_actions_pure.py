"""The one UI change of the visuals page, 11 Nov 2026 (videobuilder-v4/phase2/ui/requirements-and-test-plan.md): the server side.
R13: one answer of step 2 is stored as it is made (set_answer); Done records what is stored. R17, R18: one set that was not made is
made now (set_make), refused in plain words while its cause stands. R21, E17: a supplied file carries who supplied it, the words and
its length. R6 to R9: the waiting list names every thing by its kind, with a group on every item, and lists nothing that cannot be
acted on."""
import json

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design151_refs_pure import KILN, MASON, NEW, doc_with, frames_only, new_store, with_sets
from test_visuals_stage_pure import FakeConn, USER, accepted, g, job, saved, shot

OTHER = {'id': 'u2', 'name': 'Revathi'}
BRICK = {'id': 'BRICK', 'name': 'Red brick', 'kind': 'material', 'identity': 'exact', 'requirements': 'the fired red brick',
         'material_spec': {'dimensions': [{'part': 'brick', 'measure': 'length', 'value': 190, 'unit': 'mm', 'source': 'the brief p.2', 'status': 'confirmed'},
                                          {'part': 'brick', 'measure': 'height', 'value': 90, 'unit': 'mm', 'source': 'the brief p.2', 'status': 'confirmed'}],
                           'laid': 'on edge', 'joint': '10 mm mortar joints', 'pattern': 'one long face, one header', 'proportions': [], 'relationships': [], 'label': ''}}
ROWS = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'BRICK', 'prompt': 'one course of the brick'}]


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})


def sheets(s, eid, status='candidate'):
    return sorted(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid and r['status'] == status)


def back(store):
    """What the image worker writes when a set comes back (as with_sets does)."""
    s = saved(store)
    for r in list(s['references'].values()):
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            r.update(status='candidate', sha256='sha-' + r['id'], key=f"run-1/visuals/references/{r['id']}.png")
            s['references'][r['id'] + '-2'] = {**r, 'id': r['id'] + '-2', 'set_n': 2, 'sha256': 'sha-' + r['id'] + '-2'}
    VS.save_session(store, NEW, s)
    return s


def brick_round(spec=False):
    """A round at step 2 on a film with a material: E2's set is back; the brick's set was refused while its spec was not approved."""
    store, conn = frames_only(doc_with(KILN, BRICK)), FakeConn([])
    if spec:
        VS.approve_spec(store, USER, NEW, [], 'element:BRICK', '')
    VS.round_start(store, USER, NEW, [], ROWS, conn=conn)
    out = VS.round_done(store, USER, NEW, [], {r['element_id']: {'verdict': 'approve'} for r in ROWS}, 'yes', conn=conn)
    return store, conn, out, back(store)


def view(store, conn):
    return VS.page_view(conn, store, NEW, [], 'VW-20')


def kinds(items):
    return sorted(i['kind'] for i in items)


# ---------- R13: one answer stored as it is made ----------

def test_one_answer_is_stored_field_by_field_and_comes_back_in_the_page_data():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    pic = sheets(s, 'E2')[1]
    out = VS.set_answer(store, USER, NEW, [], 'E2', None, pic, '')   # only the starting picture so far
    assert out['stored'] is True and saved(store)['round']['elements']['E2']['answer']['golden'] == pic
    assert view(store, conn)['round']['elements']['E2']['answer'] == {'verdict': None, 'golden': pic, 'words': ''}
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', pic, '')
    VS.set_answer(store, USER, NEW, [], 'P1', 'correct', None, '  older, about fifty ')
    els = view(store, conn)['round']['elements']
    assert els['E2']['answer'] == {'verdict': 'yes', 'golden': pic, 'words': ''}
    assert els['P1']['answer'] == {'verdict': 'correct', 'golden': None, 'words': 'older, about fifty'}
    assert els['E1'].get('answer') is None   # nothing stored: no answer, and the page must not break on it
    assert saved(store)['references'][pic]['status'] == 'candidate'   # nothing is recorded before Done


def test_an_answer_changed_before_done_is_replaced_and_of_two_writers_the_later_wins():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    a, b = sheets(s, 'E2')
    VS.set_answer(store, USER, NEW, [], 'E2', 'no', None, '')
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', a, '')
    VS.set_answer(store, OTHER, NEW, [], 'E2', 'yes', b, '')   # a second browser tab, later
    stored = saved(store)['round']['elements']['E2']['answer']
    assert (stored['verdict'], stored['golden'], stored['by']) == ('yes', b, 'u2')
    assert view(store, conn)['round']['elements']['E2']['answer']['golden'] == b


def test_a_persons_answer_keeps_no_starting_picture():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    VS.set_answer(store, USER, NEW, [], 'P1', 'yes', sheets(s, 'P1')[0], '')
    assert saved(store)['round']['elements']['P1']['answer']['golden'] is None   # a person's full-length front picture is taken by the server


def test_an_answer_for_a_set_that_was_made_again_is_discarded():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    old = sheets(s, 'E2')[0]
    VS.set_answer(store, USER, NEW, [], 'P1', 'yes', None, '')
    VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'no', 'words': 'no chimney'}}, 'Again.', conn=conn, partial=True)
    s = back(store)
    assert VS._round_view(s)['pass'] == 2 and sheets(s, 'E2') and old not in sheets(s, 'E2')
    out = VS.set_answer(store, USER, NEW, [], 'E2', 'yes', old, '')   # a tab left open still holds a picture of the first set
    assert out['stored'] is False and out['discarded'] is True and 'made again since; judge the new set' in out['next']
    assert 'answer' not in saved(store)['round']['elements']['E2']
    s = saved(store)   # an answer stored before a set was made again (a row re-posted, a set made now) no longer fits
    s['round']['elements']['E2']['answer'] = {'verdict': 'no', 'golden': None, 'words': '', 'set': old}
    VS.save_session(store, NEW, s)
    e2 = view(store, conn)['round']['elements']['E2']
    assert e2['answer'] is None and e2['answer_discarded'] is True


def test_an_answer_is_refused_in_plain_words_outside_step_2_or_for_an_element_with_no_set_to_judge():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    for eid, words in (('ZZ', 'ZZ is not in the reference round'), ('E1', 'E1 is referenced by its footage picture')):
        with pytest.raises(Problem, match=words) as e:
            g(lambda: VS.set_answer(store, USER, NEW, [], eid, 'yes', None, ''))
        assert '`' not in e.value.message and 'vw ' not in e.value.message
    with pytest.raises(Problem, match='E2: the answer is Yes, No or Correct it'):
        g(lambda: VS.set_answer(store, USER, NEW, [], 'E2', 'maybe', None, ''))
    one = frames_only(doc_with(KILN, MASON))   # a round still at step 1
    VS.round_start(one, USER, NEW, [], [{'element_id': 'E2', 'prompt': 'the kiln'}], conn=FakeConn([]))
    with pytest.raises(Problem, match='not at step 2'):
        g(lambda: VS.set_answer(one, USER, NEW, [], 'E2', 'yes', None, ''))
    VS.round_done(one, USER, NEW, [], {'E2': {'verdict': 'approve'}}, 'yes', conn=FakeConn([]))   # the sets are being made
    with pytest.raises(Problem, match='E2: its set is being made'):
        g(lambda: VS.set_answer(one, USER, NEW, [], 'E2', 'yes', None, ''))
    none = frames_only(doc_with(KILN, MASON))   # no round at all
    with pytest.raises(Problem, match='not at step 2'):
        g(lambda: VS.set_answer(none, USER, NEW, [], 'E2', 'yes', None, ''))


# ---------- R15: Done records what is stored ----------

def test_done_records_the_stored_answers_and_clears_them():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    pic = sheets(s, 'E2')[1]
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', pic, '')
    VS.set_answer(store, USER, NEW, [], 'P1', 'correct', None, 'older')
    out = VS.round_sets(store, USER, NEW, [], {}, 'Done.', conn=conn)   # Done sends no verdict: the stored ones stand
    s = saved(store)
    assert out['pass'] == 'making' and out['queued'] == ['P1'] and out['approved'] == ['E2'] and s['golden']['E2'] == pic
    assert s['round']['elements']['P1']['corrections'] == ['older']
    assert not any('answer' in r for r in s['round']['elements'].values())   # recorded: nothing stored is left behind
    assert view(store, conn)['round']['elements']['P1'].get('answer_discarded') is not True   # its new set is not "made again since"


def test_a_verdict_sent_with_done_still_works_and_wins_over_a_stored_one():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    a, b = sheets(s, 'E2')
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', a, '')
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': b}, 'P1': {'verdict': 'yes'}}, 'From the chat tool.', conn=conn)
    assert out['pass'] == 'complete' and saved(store)['golden']['E2'] == b


def test_done_from_the_chat_tool_still_needs_every_verdict_and_the_page_may_record_a_part():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    pic = sheets(s, 'E2')[0]
    with pytest.raises(Problem, match='P1: a verdict is required'):
        g(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': pic}}, 'yes', conn=conn))
    VS.set_answer(store, USER, NEW, [], 'P1', 'no', None, '')   # stored from another tab: this page's confirmation did not count it, so its Done does not record it
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': pic}}, 'These for now.', conn=conn, partial=True)
    s = saved(store)
    assert out['approved'] == ['E2'] and out['unanswered'] == ['P1'] and out['pass'] == 2 and VS._round_view(s)['pass'] == 2
    assert all(s['references'][i]['status'] == 'candidate' for i in sheets(s, 'P1')) and s['round']['elements']['P1']['answer']['verdict'] == 'no'   # the set still waits, its stored answer kept
    with pytest.raises(Problem, match='nothing to record'):
        g(lambda: VS.round_sets(store, USER, NEW, [], {}, 'Nothing.', conn=conn, partial=True))
    out = VS.round_sets(store, USER, NEW, [], {'P1': {'verdict': 'yes'}}, 'And the mason.', conn=conn, partial=True)
    assert out['pass'] == 'complete'


# ---------- R17, R18, E14, E15: one set that was not made ----------

def test_a_set_not_made_is_refused_in_plain_words_while_its_spec_is_not_approved_then_queued_once():
    store, conn, out, s = brick_round()
    assert 'BRICK' in out['errors'] and not sheets(s, 'BRICK', 'generating') and VS._round_view(s)['pass'] == 2
    row = view(store, conn)['round']['elements']['BRICK']
    assert row['cause']['kind'] == 'spec' and row['cause']['element_id'] == 'BRICK' and 'is not approved' in row['cause']['text']
    with pytest.raises(Problem, match='BRICK: its set cannot be made yet: the material spec of Red brick is not approved') as e:
        g(lambda: VS.set_make(conn, store, USER, NEW, [], 'BRICK'))
    assert '`' not in e.value.message and 'vw ' not in e.value.message
    VS.approve_spec(store, USER, NEW, [], 'element:BRICK', '')
    row = view(store, conn)['round']['elements']['BRICK']
    assert row['cause'] is None and row['settled'] == 'spec approved'   # the present reason, not the stored one
    n = len(conn.inserted)
    made = VS.set_make(conn, store, USER, NEW, [], 'BRICK')
    s = saved(store)
    assert made['queued'] is True and len(conn.inserted) == n + 1 and len(sheets(s, 'BRICK', 'generating')) == 1 and VS._round_view(s)['pass'] == 'making'
    assert s['round']['elements']['BRICK']['error'] is None
    again = VS.set_make(conn, store, USER, NEW, [], 'BRICK')   # pressed twice, or from a second tab
    assert again['queued'] is False and len(conn.inserted) == n + 1 and 'already being made' in again['next']


def test_a_set_not_made_is_refused_while_the_spend_cap_stands_and_nothing_is_queued():
    store, conn, out, s = brick_round(spec=True)
    for r in s['references'].values():   # the brick's set did not come back
        if r.get('kind') == 'sheet' and r['element_id'] == 'BRICK':
            r['status'] = 'failed'
    s['cap_inr'] = 100.0
    VS.save_session(store, NEW, s)
    conn.jobs += [{**job('gemini-image'), 'id': f'j-{k}'} for k in range(6)]
    n = len(conn.inserted)
    row = view(store, conn)['round']['elements']['BRICK']
    assert row['cause']['kind'] == 'cap' and 'spend cap' in row['cause']['text'] and '₹' in row['cause']['text']
    with pytest.raises(Problem, match='spend cap') as e:
        g(lambda: VS.set_make(conn, store, USER, NEW, [], 'BRICK'))
    assert len(conn.inserted) == n and '`' not in e.value.message and "SK's" not in e.value.message


def test_a_set_not_made_is_refused_while_a_size_is_not_measured():
    doc = doc_with({**KILN, 'size': [{'part': 'kiln', 'measure': 'height', 'value': None, 'unit': 'm', 'source': '', 'status': 'unknown'}]})
    store, conn = frames_only(doc), FakeConn([])
    VS.round_start(store, USER, NEW, [], [{'element_id': 'E2', 'prompt': 'the kiln during firing'}], conn=conn)
    VS.round_done(store, USER, NEW, [], {'E2': {'verdict': 'approve'}}, 'yes', conn=conn)
    s = saved(store)
    for r in s['references'].values():
        if r.get('kind') == 'sheet':
            r['status'] = 'failed'   # the set did not come back
    s['references']['F2'] = {**s['references']['F1'], 'id': 'F2', 'element_id': 'E2', 'status': 'approved'}   # a footage picture of the kiln, approved since
    VS.save_session(store, NEW, s)
    assert view(store, conn)['round']['elements']['E2']['cause']['kind'] == 'size'
    with pytest.raises(Problem, match='E2: its set cannot be made yet: a size of Clamp kiln is not measured') as e:
        g(lambda: VS.set_make(conn, store, USER, NEW, [], 'E2'))
    assert 'F2' not in e.value.message and '`' not in e.value.message


def test_a_set_that_has_its_pictures_or_is_outside_the_round_is_not_made_again():
    store, conn, out, s = brick_round(spec=True)
    for eid, words in (('E2', 'E2 has its set: judge it'), ('E1', 'E1 is referenced by its footage picture'), ('ZZ', 'ZZ is not in the reference round')):
        with pytest.raises(Problem, match=words):
            g(lambda: VS.set_make(conn, store, USER, NEW, [], eid))
    one = frames_only(doc_with(KILN))
    VS.round_start(one, USER, NEW, [], [{'element_id': 'E2', 'prompt': 'the kiln'}], conn=FakeConn([]))
    with pytest.raises(Problem, match='nothing to make now'):
        g(lambda: VS.set_make(FakeConn([]), one, USER, NEW, [], 'E2'))


def test_a_spec_corrected_after_its_set_was_made_is_said_and_the_set_is_made_again_once_the_revised_spec_is_approved():
    store, conn, out, s = brick_round(spec=True)
    first = sheets(s, 'BRICK')
    assert first and view(store, conn)['round']['elements']['BRICK'].get('spec_changed') is not True
    VS.correct_spec(store, USER, NEW, [], 'element:BRICK', 'the joint is 12 mm, not 10')
    row = view(store, conn)['round']['elements']['BRICK']
    assert row['spec_changed'] is True and row['cause']['kind'] == 'spec' and 'the assistant revises it' in row['cause']['text']
    with pytest.raises(Problem, match='its set cannot be made yet'):
        g(lambda: VS.set_make(conn, store, USER, NEW, [], 'BRICK'))
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])   # the assistant revises the spec; the operator approves the revised one
    next(e for e in doc['document']['elements'] if e['id'] == 'BRICK')['material_spec']['joint'] = '12 mm mortar joints'
    store.files['run-1/visuals/plan-v1.json'] = json.dumps(doc).encode('utf-8')
    VS.approve_spec(store, USER, NEW, [], 'element:BRICK', '')
    row = view(store, conn)['round']['elements']['BRICK']
    assert row['spec_changed'] is True and row['cause'] is None
    VS.set_answer(store, USER, NEW, [], 'BRICK', 'yes', first[0], '')   # an answer on the old set
    made = VS.set_make(conn, store, USER, NEW, [], 'BRICK')
    s = saved(store)
    assert made['queued'] is True and all(s['references'][i]['status'] == 'rejected' for i in first) and len(sheets(s, 'BRICK', 'generating')) == 1
    assert 'answer' not in s['round']['elements']['BRICK']   # it was for the old set


# ---------- R21, E17: a supplied file says who supplied it, with which words, and how long it is ----------

class FilesConn(FakeConn):
    def execute(self, sql, params=()):
        if 'from vw2_files' in sql:
            return type('R', (), {'fetchone': lambda _: {'key': params[1], 'sha256': 'sha-movie', 'bytes': 1000}})()
        return super().execute(sql, params)


def test_a_supplied_file_carries_who_supplied_it_the_words_and_its_length(monkeypatch):
    doc = doc_with(KILN, MASON)
    store, conn = new_store(doc, {}, accepted=accepted(doc)), FilesConn([])
    monkeypatch.setattr(VS, '_movie_seconds', lambda store_, key_: 6.0)
    VS.add_asset(conn, store, USER, NEW, [], 'VS1', 'run-1/uploads/pour.mp4', 'sha-movie', 1000, 'movie', 'My own shot of the pour.', 'By hand.')
    asset = view(store, conn)['gaps'][1]['shots'][0]['asset']
    assert (asset['kind'], asset['by'], asset['quote'], asset['duration_s']) == ('movie', 'SK', 'My own shot of the pour.', 6.0)
    VS.add_asset(conn, store, OTHER, NEW, [], 'VS1', 'run-1/uploads/wall.png', 'sha-movie', 1000, 'still', 'A photograph instead.', 'By hand.')
    asset = view(store, conn)['gaps'][1]['shots'][0]['asset']
    assert (asset['kind'], asset['by'], asset['quote'], asset['duration_s']) == ('still', 'Revathi', 'A photograph instead.', None)


def test_a_file_supplied_before_this_change_or_one_that_cannot_be_measured_still_opens():
    doc = doc_with(KILN, MASON)
    store, conn = new_store(doc, {}, accepted=accepted(doc)), FilesConn([])
    VS.add_asset(conn, store, USER, NEW, [], 'VS1', 'run-1/uploads/pour.mp4', 'sha-movie', 1000, 'movie', 'Mine.', 'By hand.')   # no such file in the store: the length is unknown, never an error
    s = saved(store)
    assert s['assets']['VS1']['duration_s'] is None
    s['assets']['VS1'] = {k: v for k, v in s['assets']['VS1'].items() if k not in ('by_name', 'duration_s')}   # as stored before this change
    VS.save_session(store, NEW, s)
    asset = view(store, conn)['gaps'][1]['shots'][0]['asset']
    assert asset['by'] == '' and asset['quote'] == 'Mine.' and asset['duration_s'] is None


# ---------- R6 to R9: the waiting list tells the truth ----------

def test_step_1_names_each_waiting_thing_by_its_kind_with_its_card():
    store, conn = frames_only(doc_with(KILN, BRICK)), FakeConn([])
    VS.round_start(store, USER, NEW, [], ROWS, conn=conn)
    items = view(store, conn)['waiting']
    assert kinds(items) == ['material spec to approve', 'picture to answer']
    by = {i['kind']: i for i in items}
    assert by['picture to answer']['label'] == 'Picture to answer · E1 · frame' and by['picture to answer']['link'] == '/runs/VW-20/visuals#references/E1/F1'
    assert by['material spec to approve']['label'] == 'Material spec to approve · BRICK' and by['material spec to approve']['link'] == '/runs/VW-20/visuals#references/BRICK/specs'
    assert all(i['group'] and i['step'] and i['kind'] for i in items)


def test_step_2_lists_one_item_per_set_to_judge_and_an_answered_set_leaves_the_list():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    items = view(store, conn)['waiting']
    assert [(i['kind'], i['group'], i['label']) for i in items] == [('set to judge', 'E2', 'Set to judge · E2'), ('set to judge', 'P1', 'Set to judge · P1')]   # E1 is from the footage
    assert items[0]['link'] == '/runs/VW-20/visuals#references/E2/set'
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', None, '')   # Yes on a thing with no starting picture is not an answer yet
    VS.set_answer(store, USER, NEW, [], 'P1', 'correct', None, '')   # nor is Correct it with no words
    assert [i['group'] for i in view(store, conn)['waiting']] == ['E2', 'P1']
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', sheets(s, 'E2')[0], '')
    VS.set_answer(store, USER, NEW, [], 'P1', 'no', None, '')
    assert view(store, conn)['waiting'] == []


def test_a_set_not_made_is_listed_only_when_it_can_be_made_now():
    store, conn, out, s = brick_round()
    items = view(store, conn)['waiting']
    assert [(i['kind'], i['group']) for i in items] == [('set to judge', 'E2'), ('material spec to approve', 'BRICK')]   # the brick: its spec waits, not its set
    VS.approve_spec(store, USER, NEW, [], 'element:BRICK', '')
    items = view(store, conn)['waiting']
    assert sorted((i['kind'], i['group'], i['link'].rsplit('/', 1)[1]) for i in items) == [('set to judge', 'E2', 'set'), ('set to make', 'BRICK', 'make')]
    s = saved(store)
    s['cap_inr'] = 100.0
    VS.save_session(store, NEW, s)
    conn.jobs += [{**job('gemini-image'), 'id': f'j-{k}'} for k in range(6)]
    assert [(i['kind'], i['group']) for i in view(store, conn)['waiting']] == [('set to judge', 'E2')]   # the cap: the operator cannot make it


def test_nothing_is_listed_that_has_no_card_to_act_on():
    doc = doc_with(KILN)
    store, conn = frames_only(doc), FakeConn([])
    s = saved(store)
    s['references']['F9'] = {**s['references']['F1'], 'id': 'F9', 'element_id': 'GONE'}   # a footage picture of a thing the plan no longer has
    VS.save_session(store, NEW, s)
    assert [i['link'].rsplit('/', 1)[1] for i in view(store, conn)['waiting']] == ['F1']
    VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth'}, {'element_id': 'E2', 'prompt': 'the kiln'}], conn=conn)
    VS.round_done(store, USER, NEW, [], {'E1': {'verdict': 'ignore'}, 'E2': {'verdict': 'approve'}}, 'yes', conn=conn)
    back(store)
    assert [(i['kind'], i['group']) for i in view(store, conn)['waiting']] == [('set to judge', 'E2')]   # E1 is ignored: its picture asks nothing now


def test_a_drawing_spec_waits_on_the_card_of_its_own_shot_on_the_tab_that_shows_it():
    doc = doc_with(KILN)
    spec = {'dimensions': [{'part': 'cavity', 'measure': 'width', 'value': 75, 'unit': 'mm', 'source': 'the brief', 'status': 'confirmed'}], 'proportions': [], 'relationships': [], 'label': ''}
    doc['gaps'][0]['scenes'][0]['shots'] = [shot('IM1', 0, 250, 'image', element_ids=['E1'], drawing_spec=dict(spec)), shot('DR1', 250, 500, 'drawn', element_ids=['E1'], drawing_spec=dict(spec))]
    store = new_store(doc, {}, accepted=accepted(doc))
    items = [i for i in view(store, FakeConn([]))['waiting'] if 'spec' in i['kind']]
    assert [(i['kind'], i['step'], i['group'], i['label']) for i in items] == [('drawing spec to approve', 'pictures', 'IM1', 'Drawing spec to approve · IM1'),
                                                                               ('drawing spec to approve', 'takes', 'DR1', 'Drawing spec to approve · DR1')]
    assert items[0]['link'] == '/runs/VW-20/visuals#pictures/IM1/spec'



# ---------- Follow-up, ten fixes (11 Nov 2026): the cap at Done (2), a set set aside at step 2 (3), the kept wording for an ignored footage picture (7), no bare key name to the operator (9) ----------

def wall_round():
    """Step 2 where the kiln's set did not come back and cannot be made: a size is not measured (a footage picture of it was approved since). The mason's set is back."""
    doc = doc_with({**KILN, 'size': [{'part': 'kiln', 'measure': 'height', 'value': None, 'unit': 'm', 'source': '', 'status': 'unknown'}]}, MASON)
    store, conn = frames_only(doc), FakeConn([])
    VS.round_start(store, USER, NEW, [], [{'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'P1', 'prompt': 'kneels all day'}], conn=conn)
    VS.round_done(store, USER, NEW, [], {'E2': {'verdict': 'approve'}, 'P1': {'verdict': 'approve'}}, 'yes', conn=conn)
    s = back(store)
    for r in s['references'].values():
        if r.get('kind') == 'sheet' and r['element_id'] == 'E2':
            r['status'] = 'failed'
    s['references']['F2'] = {**s['references']['F1'], 'id': 'F2', 'element_id': 'E2', 'status': 'approved'}
    VS.save_session(store, NEW, s)
    return store, conn


def test_a_set_never_made_is_set_aside_at_step_2_and_counts_as_nothing_waiting():
    store, conn = wall_round()
    assert view(store, conn)['round']['elements']['E2']['cause']['kind'] == 'size'
    out = VS.set_aside(store, USER, NEW, [], 'E2', 'we film it ourselves')
    row = view(store, conn)['round']['elements']['E2']
    assert out['aside'] is True and row['ignored'] is True and row['aside']['words'] == 'we film it ourselves' and row['aside']['by'] == USER['id']
    assert not row.get('cause') and not [i for i in view(store, conn)['waiting'] if i['group'] == 'E2']
    assert '`' not in out['next'] and 'vw ' not in out['next']


def test_a_set_that_was_made_or_an_element_outside_the_round_cannot_be_set_aside():
    store, conn = wall_round()
    for eid, words in (('P1', 'P1 has its set'), ('ZZ', 'ZZ is not in the reference round')):
        with pytest.raises(Problem, match=words):
            g(lambda: VS.set_aside(store, USER, NEW, [], eid))
    assert not saved(store)['round']['elements']['P1'].get('ignored')
    one = frames_only(doc_with(KILN))
    VS.round_start(one, USER, NEW, [], [{'element_id': 'E2', 'prompt': 'the kiln'}], conn=FakeConn([]))
    with pytest.raises(Problem, match='nothing can be set aside'):   # step 1 has its own Ignore
        g(lambda: VS.set_aside(one, USER, NEW, [], 'E2'))


def test_a_set_aside_element_is_brought_back_while_the_round_is_open():
    store, conn = wall_round()
    with pytest.raises(Problem, match='E2 was not set aside'):
        g(lambda: VS.set_aside(store, USER, NEW, [], 'E2', back=True))
    VS.set_aside(store, USER, NEW, [], 'E2')
    with pytest.raises(Problem, match='E2 is set aside already'):
        g(lambda: VS.set_aside(store, USER, NEW, [], 'E2'))
    out = VS.set_aside(store, USER, NEW, [], 'E2', back=True)
    row = view(store, conn)['round']['elements']['E2']
    assert out['aside'] is False and not row['ignored'] and 'aside' not in row and row['cause']['kind'] == 'size'


def test_the_round_completes_when_one_set_is_set_aside_and_every_other_set_is_approved():
    store, conn = wall_round()
    VS.set_aside(store, USER, NEW, [], 'E2')
    out = VS.round_sets(store, USER, NEW, [], {'P1': {'verdict': 'yes'}}, 'The mason.', conn=conn, partial=True)
    assert out['pass'] == 'complete' and out['approved'] == ['P1']
    with pytest.raises(Problem, match='nothing can be set aside'):   # the round is closed: nothing is brought back
        g(lambda: VS.set_aside(store, USER, NEW, [], 'E2', back=True))
    # the other order: the mason approved first, the kiln set aside afterwards; the page's Done then closes the round with nothing left to judge
    store, conn = wall_round()
    assert VS.round_sets(store, USER, NEW, [], {'P1': {'verdict': 'yes'}}, 'The mason.', conn=conn, partial=True)['pass'] == 2
    VS.set_aside(store, USER, NEW, [], 'E2')
    assert VS.round_sets(store, USER, NEW, [], {}, 'That is all.', conn=conn, partial=True)['pass'] == 'complete'


@pytest.mark.parametrize('partial', [True, False])
def test_done_at_the_spend_cap_records_the_approvals_and_holds_the_remakes_with_their_answers(partial):
    store, conn, s = with_sets(doc_with(KILN, MASON))
    pic = sheets(s, 'E2')[0]
    s['cap_inr'] = 100.0
    VS.save_session(store, NEW, s)
    conn.jobs += [{**job('gemini-image'), 'id': f'j-{k}'} for k in range(6)]   # over the cap
    n = len(conn.inserted)
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': pic}, 'P1': {'verdict': 'correct', 'words': 'older, about fifty'}}, 'These.', conn=conn, partial=partial)
    s = saved(store)
    assert out['approved'] == ['E2'] and len(sheets(s, 'E2', 'approved')) == 2 and s['golden']['E2'] == pic   # a Yes costs nothing
    assert out['queued'] == [] and len(conn.inserted) == n and out['pass'] == 2
    assert list(out['held']) == ['P1'] and 'spend cap' in out['held']['P1'] and '₹100' in out['held']['P1'] and '`' not in out['held']['P1']
    row = s['round']['elements']['P1']
    assert len(sheets(s, 'P1')) == 3 and row['answer']['verdict'] == 'correct' and row['answer']['words'] == 'older, about fifty'   # nothing lost: the set and its answer wait
    assert not row.get('corrections') and not [i for i in view(store, conn)['waiting'] if i['group'] == 'P1']   # answered: it does not ask again
    s['cap_inr'] = 100000.0   # the cap raised: Done records the kept answer and the set is made again
    VS.save_session(store, NEW, s)
    out = VS.round_sets(store, USER, NEW, [], {} if not partial else {'P1': {'verdict': 'correct', 'words': 'older, about fifty'}}, 'Now.', conn=conn, partial=partial)
    assert out['queued'] == ['P1'] and out['pass'] == 'making' and not out['held'] and saved(store)['round']['elements']['P1']['corrections'] == ['older, about fifty']


def test_ignoring_a_footage_picture_on_a_kept_film_is_answered_in_the_kept_methods_words():
    store, conn = frames_only(doc_with(KILN)), FakeConn([])
    VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}], conn=conn)
    out = VS.reject_reference(store, USER, NEW, [], 'F1', '', '')
    assert 'search' not in out['next'].lower() and "operator's words" not in out['next']
    assert 'ignored' in out['next'] and 'made from its description' in out['next']


def test_an_unexpected_error_in_a_page_action_reaches_the_operator_as_a_plain_sentence(caplog):
    from app import web

    def boom():
        raise KeyError('request_key')
    with pytest.raises(Problem) as e:
        web._page_call(boom, 'select-take')
    assert e.value.message == 'That could not be done; nothing was changed. The builder has been told what failed.'
    assert 'request_key' not in e.value.message and 'request_key' in caplog.text   # the real text goes to the server log
    with pytest.raises(Problem, match='P1: say what to correct'):   # a refusal written for the operator still arrives as written
        web._page_call(lambda: VS.need(False, 'P1: say what to correct.'), 'round-sets')
    assert web._page_call(lambda: {'done': True}, 'approve') == {'done': True}


# ---------- Round 3 (11 Nov 2026). U17: a verdict on one picture is changed both ways until a later step used it. U19: the operator's own picture as the starting picture ----------

from test_design151_refs_pure import OLD, png_bytes   # noqa: E402
from test_visuals_stage_pure import ref   # noqa: E402

STEP1 = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'P1', 'prompt': 'kneels'}]
NO = {'notes': 'wrong kiln', 'quote': 'No.', 'by': 'u1'}


def pic(store, conn, rid):
    return next(r for r in view(store, conn)['references'] if r['id'] == rid)


def test_a_footage_pictures_verdict_is_changed_both_ways_until_step_1_is_done():
    store, conn = frames_only(doc_with(KILN, MASON)), FakeConn([])
    VS.round_start(store, USER, NEW, [], STEP1, conn=conn)
    VS.reject_reference(store, USER, NEW, [], 'F1', 'too dark', '')
    assert pic(store, conn, 'F1')['status'] == 'rejected' and pic(store, conn, 'F1')['locked'] is None
    out = g(lambda: VS.reapprove_reference(store, USER, NEW, [], 'F1', 'sha-F1', '', conn))   # reject, then approve
    r = saved(store)['references']['F1']
    assert out['status'] == 'approved' and r['status'] == 'approved' and not r.get('rejection') and r['rejections'][0]['notes'] == 'too dark'   # the earlier rejection is kept as history
    assert pic(store, conn, 'F1')['rejection'] is None and pic(store, conn, 'F1')['locked'] is None
    VS.reject_reference(store, USER, NEW, [], 'F1', '', '')   # approve, then reject
    assert saved(store)['references']['F1']['status'] == 'rejected'
    g(lambda: VS.reapprove_reference(store, USER, NEW, [], 'F1', 'sha-F1', '', conn))
    with pytest.raises(Problem, match='Only a rejected picture'):
        g(lambda: VS.reapprove_reference(store, USER, NEW, [], 'F1', 'sha-F1', '', conn))
    VS.round_done(store, USER, NEW, [], {r['element_id']: {'verdict': 'approve'} for r in STEP1}, 'yes', conn=conn)   # step 1 done: the picture was used
    lock = pic(store, conn, 'F1')['locked']
    assert 'Step 1' in lock and 'can no longer be changed here' in lock and '`' not in lock and 'F1' not in lock
    with pytest.raises(Problem, match='Step 1 of the reference round is done'):
        g(lambda: VS.reject_reference(store, USER, NEW, [], 'F1', '', ''))
    assert saved(store)['references']['F1']['status'] == 'approved'


def test_a_footage_picture_ignored_at_step_1_is_not_approved_after_done():
    store, conn = frames_only(doc_with(KILN, MASON)), FakeConn([])
    VS.round_start(store, USER, NEW, [], STEP1, conn=conn)
    VS.reject_reference(store, USER, NEW, [], 'F1', '', '')
    VS.round_done(store, USER, NEW, [], {r['element_id']: {'verdict': 'approve'} for r in STEP1}, 'yes', conn=conn)
    with pytest.raises(Problem, match='Step 1 of the reference round is done'):
        g(lambda: VS.reapprove_reference(store, USER, NEW, [], 'F1', 'sha-F1', '', conn))
    assert saved(store)['references']['F1']['status'] == 'rejected' and 'ignored' in pic(store, conn, 'F1')['locked']
    s = saved(store)   # a footage picture grabbed and approved after step 1 was not answered there: it can still be rejected (it may be what stands in a set's way)
    s['references']['F9'] = {**ref('F9', 'approved'), 'kind': 'frame', 'element_id': 'E2'}
    VS.save_session(store, NEW, s)
    assert pic(store, conn, 'F9')['locked'] is None
    assert VS.reject_reference(store, USER, NEW, [], 'F9', '', '')['status'] == 'rejected'


def test_a_picture_a_sheet_was_made_from_is_not_changed_until_the_sheet_is_rejected():
    web = lambda rid, status, **o: {**ref(rid, status), 'kind': 'web', 'element_id': 'E2', **o}
    store, conn = new_store(doc_with(KILN), {'W1': web('W1', 'approved'), 'W2': web('W2', 'rejected', rejection=dict(NO)),
                                             'S1': {**ref('S1'), 'kind': 'sheet', 'element_id': 'E2', 'generation': {'op': 'generate', 'parents': [{'id': 'W1'}]}}}), FakeConn([])
    assert 'A sheet was made from this picture' in VS.verdict_lock(saved(store), saved(store)['references']['W1'])
    with pytest.raises(Problem, match='A sheet was made from this picture; it can no longer be changed here'):
        g(lambda: VS.reject_reference(store, USER, OLD, [], 'W1', '', ''))
    with pytest.raises(Problem, match='A sheet was made after this picture was rejected'):
        g(lambda: VS.reapprove_reference(store, USER, OLD, [], 'W2', 'sha-W2', '', conn))
    assert saved(store)['references']['W2']['status'] == 'rejected' and saved(store)['references']['W2']['rejection']['notes'] == 'wrong kiln'   # refused: nothing changed
    VS.reject_reference(store, USER, OLD, [], 'S1', 'not this kiln', '')   # the sheet rejected: its sources can be changed again
    VS.reject_reference(store, USER, OLD, [], 'W1', '', '')
    assert g(lambda: VS.reapprove_reference(store, USER, OLD, [], 'W2', 'sha-W2', '', conn))['status'] == 'approved'


def test_a_placed_picture_and_a_rejected_one_with_another_in_its_place_are_locked():
    doc = doc_with(KILN)
    store, conn = new_store(doc, {'K0': {**ref('K0', 'rejected'), 'shot_id': 'IM1', 'rejection': dict(NO)}, 'K1': {**ref('K1'), 'shot_id': 'IM1'}}, accepted=accepted(doc)), FakeConn([])
    with pytest.raises(Problem, match='Another picture stands in its place now'):
        g(lambda: VS.reapprove_reference(store, USER, OLD, [], 'K0', 'sha-K0', '', conn))
    assert g(lambda: VS.approve_reference(store, USER, OLD, [], 'K1', 'sha-K1', 'Yes.', conn))['placed'] == 'IM1'
    assert 'placed in shot IM1' in pic(store, conn, 'K1')['locked']
    with pytest.raises(Problem, match='placed in shot IM1'):
        g(lambda: VS.reject_reference(store, USER, OLD, [], 'K1', '', ''))
    VS.unplace(store, USER, OLD, [], 'IM1', 'out')
    assert pic(store, conn, 'K1')['locked'] is None
    VS.reject_reference(store, USER, OLD, [], 'K1', '', '')   # nothing stands in K0's place now
    assert g(lambda: VS.reapprove_reference(store, USER, OLD, [], 'K0', 'sha-K0', '', conn))['status'] == 'approved'


def test_a_refused_second_approval_leaves_the_picture_rejected():
    store, conn = new_store(doc_with(KILN), {'G1': {**ref('G1', 'rejected'), 'kind': 'isolated', 'element_id': 'E2', 'golden_candidate': True, 'rejection': dict(NO)}}), FakeConn([])
    with pytest.raises(Problem, match='cannot be the golden picture'):   # design/111 F11 stands: a picture rejected before is never golden
        g(lambda: VS.reapprove_reference(store, USER, OLD, [], 'G1', 'sha-G1', '', conn))
    r = saved(store)['references']['G1']
    assert r['status'] == 'rejected' and r['rejection']['notes'] == 'wrong kiln' and not saved(store).get('golden')
    with pytest.raises(Problem, match='exact stored image'):
        g(lambda: VS.reapprove_reference(store, USER, OLD, [], 'G1', 'not-its-hash', '', conn))
    assert saved(store)['references']['G1']['status'] == 'rejected'


def test_a_set_picture_is_never_approved_on_its_own_after_its_set_was_answered_no():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'no', 'words': ''}}, 'Again.', conn=conn, partial=True)
    old = sheets(saved(store), 'E2', 'rejected')[0]
    with pytest.raises(Problem, match='judged as a whole'):
        g(lambda: VS.reapprove_reference(store, USER, NEW, [], old, 'sha-' + old, '', conn))


def test_a_takes_verdict_is_changed_both_ways_by_the_functions_of_today():
    """U17, takes: nothing new on the server: a rejected take is selected (the page sends its note with Select), a selected take is rejected."""
    import test_design117_p4_pure as P4
    store = P4.svg_store()
    out = VS.render_drawn(FakeConn([]), store, USER, P4.RUN, [], {'shot_id': 'DR1'})
    prep = saved(store)['preparations']['DR1']
    row = {'id': 'j1', 'unit': 'DR1', 'run_id': 'run-1', 'provider': 'drawn', 'status': 'ready', 'error': None, 'request': {'kind': 'drawn', 'request_key': prep['key'], 'preparation_id': out['preparation_id']},
           'result': {'key': 'run-1/visuals/drawn/j1.mp4', 'sha256': 'd' * 64, 'bytes': 9, 'evidence': {'duration_seconds': 4.0, 'timing_matches_placement': True, 'issues': []}}}

    class Conn(FakeConn):
        def execute(self, sql, params=()):
            return type('R', (), {'fetchone': lambda _: row})() if 'from vw2_jobs where id=' in sql else super().execute(sql, params)
    VS.review_take(Conn([]), store, USER, P4.RUN, [], 'j1', 'rejected', 'the arrow is late', '', '')
    assert saved(store)['reviews']['j1'][-1]['decision'] == 'rejected'
    assert VS.select_take(Conn([]), store, USER, P4.RUN, [], 'j1', '', 'approved on the visuals page')['job_id'] == 'j1'   # reject, then select
    VS.review_take(Conn([]), store, USER, P4.RUN, [], 'j1', 'rejected', '', '', '')   # select, then reject
    assert 'DR1' not in saved(store)['selections'] and saved(store)['reviews']['j1'][-1]['decision'] == 'rejected'


def test_a_set_answer_is_changed_as_often_as_wanted_until_done_records_it():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    first = sheets(s, 'E2')[0]
    for v, gold, words in (('yes', first, ''), ('no', None, ''), ('correct', None, 'a taller kiln'), ('yes', first, '')):
        VS.set_answer(store, USER, NEW, [], 'E2', v, gold, words)
        assert view(store, conn)['round']['elements']['E2']['answer'] == {'verdict': v, 'golden': gold, 'words': words}
    assert saved(store)['references'][first]['status'] == 'candidate'
    VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': first}}, 'This.', conn=conn, partial=True)
    with pytest.raises(Problem, match='approved already'):
        g(lambda: VS.set_answer(store, USER, NEW, [], 'E2', 'no', None, ''))


def own(store, conn, eid, colour=(9, 9, 9), name='mine.png'):
    return g(lambda: VS.supply_own(conn, store, USER, NEW, [], eid, content=png_bytes(64, 48, colour), name=name))


def test_an_own_picture_of_the_element_is_accepted_as_its_starting_picture():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    mine = own(store, conn, 'E2')
    assert mine['kind'] == 'supplied' and mine['status'] == 'approved' and mine['element_id'] == 'E2'
    out = VS.set_answer(store, USER, NEW, [], 'E2', 'yes', mine['id'], '')
    assert out['stored'] is True and out['answer']['golden'] == mine['id']
    assert not [i for i in view(store, conn)['waiting'] if i['group'] == 'E2']   # a whole answer: it waits for Done only
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': mine['id']}}, 'Mine.', conn=conn, partial=True)
    s = saved(store)
    assert out['approved'] == ['E2'] and s['golden']['E2'] == mine['id'] and len(sheets(s, 'E2', 'approved')) == 2   # Done records it as the golden picture
    lock = pic(store, conn, mine['id'])['locked']
    assert 'starting picture' in lock and 'can no longer be changed here' in lock
    with pytest.raises(Problem, match='starting picture'):
        g(lambda: VS.reject_reference(store, USER, NEW, [], mine['id'], '', ''))


def test_the_chat_tools_done_takes_a_stored_answer_with_an_own_picture():
    store, conn, s = with_sets(doc_with(KILN), person=False)
    mine = own(store, conn, 'E2')
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', mine['id'], '')
    out = VS.round_sets(store, USER, NEW, [], {}, 'Done.', conn=conn)   # not partial: the stored answer stands
    assert out['pass'] == 'complete' and saved(store)['golden']['E2'] == mine['id']


def test_another_elements_own_picture_is_refused_as_the_starting_picture():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    other = own(store, conn, 'E1')
    with pytest.raises(Problem, match='E2: the starting picture chosen is a picture of another element'):
        g(lambda: VS.set_answer(store, USER, NEW, [], 'E2', 'yes', other['id'], ''))
    assert saved(store)['round']['elements']['E2'].get('answer') is None
    with pytest.raises(Problem, match='E2: the starting picture chosen is a picture of another element'):
        g(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': other['id']}}, 'This.', conn=conn, partial=True))
    assert not sheets(saved(store), 'E2', 'approved')


PEOPLE = "A person's reference is made from the description; an uploaded photo is not used for people."


def test_an_uploaded_photo_is_not_used_for_a_person_until_the_one_condition_is_switched(monkeypatch):
    store, conn, s = with_sets(doc_with(KILN, MASON))
    n = len(saved(store)['references'])
    with pytest.raises(Problem) as e:
        own(store, conn, 'P1')
    assert e.value.message == PEOPLE and len(saved(store)['references']) == n
    monkeypatch.setattr(VS, 'OWN_PICTURE_FOR_PEOPLE', True)   # the one line, switched
    photo = own(store, conn, 'P1')
    assert VS.set_answer(store, USER, NEW, [], 'P1', 'yes', photo['id'], '')['answer']['golden'] == photo['id']
    monkeypatch.setattr(VS, 'OWN_PICTURE_FOR_PEOPLE', False)
    for call in (lambda: VS.set_answer(store, USER, NEW, [], 'P1', 'yes', photo['id'], ''),
                 lambda: VS.round_sets(store, USER, NEW, [], {'P1': {'verdict': 'yes', 'golden': photo['id']}}, 'This.', conn=conn, partial=True)):
        with pytest.raises(Problem) as e:
            g(call)
        assert e.value.message == PEOPLE
    out = VS.round_sets(store, USER, NEW, [], {'P1': {'verdict': 'yes'}}, 'This.', conn=conn, partial=True)   # as before: the full-length front picture
    assert out['approved'] == ['P1'] and saved(store)['golden']['P1'] == min(sheets(saved(store), 'P1', 'approved'))
    monkeypatch.setattr(VS, 'OWN_PICTURE_FOR_PEOPLE', True)
    store, conn, s = with_sets(doc_with(KILN, MASON))
    photo = own(store, conn, 'P1')
    VS.round_sets(store, USER, NEW, [], {'P1': {'verdict': 'yes', 'golden': photo['id']}}, 'This.', conn=conn, partial=True)
    assert saved(store)['golden']['P1'] == photo['id']


def test_an_upload_that_is_not_a_picture_or_too_large_is_refused_and_nothing_is_saved():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    n = len(saved(store)['references'])
    for content, words in ((b'these are words, not a picture', 'not a picture'), (b'\0' * (15 * 1024 * 1024 + 1), 'larger than 15 MB'),
                           (png_bytes(6001, 4001, (1, 1, 1)), '24 megapixels')):
        with pytest.raises(Problem) as e:
            g(lambda: VS.supply_own(conn, store, USER, NEW, [], 'E2', content=content, name='x'))
        assert words in e.value.message and '`' not in e.value.message
        assert len(saved(store)['references']) == n   # nothing shown as saved


def test_a_second_upload_is_added_and_the_first_stays_and_an_upload_while_the_sets_are_made_is_kept():
    store, conn = frames_only(doc_with(KILN, MASON)), FakeConn([])
    VS.round_start(store, USER, NEW, [], STEP1, conn=conn)
    VS.round_done(store, USER, NEW, [], {r['element_id']: {'verdict': 'approve'} for r in STEP1}, 'yes', conn=conn)
    assert view(store, conn)['round']['pass'] == 'making'
    first = own(store, conn, 'E2', name='one.png')   # while its set is being made (an upload at step 1 stops the set: F2, test_round_faults_pure)
    second = own(store, conn, 'E2', (200, 9, 9), name='two.png')   # while its set is being made
    mine = [r for r in view(store, conn)['references'] if r['kind'] == 'supplied' and r['element_id'] == 'E2']
    assert sorted(r['id'] for r in mine) == sorted([first['id'], second['id']]) and all(r['status'] == 'approved' and r['url'] for r in mine)
    assert view(store, conn)['round']['pass'] == 'making' and sheets(saved(store), 'E2', 'generating')   # the set being made is untouched
    back(store)
    assert VS.set_answer(store, USER, NEW, [], 'E2', 'yes', first['id'], '')['stored'] is True   # either can be chosen at step 2


def test_removing_an_own_picture_clears_a_stored_answer_that_chose_it():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    mine = own(store, conn, 'E2')
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', mine['id'], '')
    VS.reject_reference(store, USER, NEW, [], mine['id'], '', '')
    assert view(store, conn)['round']['elements']['E2']['answer'] == {'verdict': 'yes', 'golden': None, 'words': ''}
    assert [i['kind'] for i in view(store, conn)['waiting'] if i['group'] == 'E2'] == ['set to judge']   # it asks for its starting picture again
    assert g(lambda: VS.reapprove_reference(store, USER, NEW, [], mine['id'], mine['sha256'], '', conn))['status'] == 'approved'
