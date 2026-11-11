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
    with pytest.raises(Problem, match='not at step 2'):
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
    VS.add_asset(conn, store, USER, NEW, [], 'VS1', 'run-1/uploads/pour.mp4', 'sha-movie', 1000, 'movie', 'My own shot of the pour.')
    asset = view(store, conn)['gaps'][1]['shots'][0]['asset']
    assert (asset['kind'], asset['by'], asset['quote'], asset['duration_s']) == ('movie', 'SK', 'My own shot of the pour.', 6.0)
    VS.add_asset(conn, store, OTHER, NEW, [], 'VS1', 'run-1/uploads/wall.png', 'sha-movie', 1000, 'still', 'A photograph instead.')
    asset = view(store, conn)['gaps'][1]['shots'][0]['asset']
    assert (asset['kind'], asset['by'], asset['quote'], asset['duration_s']) == ('still', 'Revathi', 'A photograph instead.', None)


def test_a_file_supplied_before_this_change_or_one_that_cannot_be_measured_still_opens():
    doc = doc_with(KILN, MASON)
    store, conn = new_store(doc, {}, accepted=accepted(doc)), FilesConn([])
    VS.add_asset(conn, store, USER, NEW, [], 'VS1', 'run-1/uploads/pour.mp4', 'sha-movie', 1000, 'movie', 'Mine.')   # no such file in the store: the length is unknown, never an error
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
