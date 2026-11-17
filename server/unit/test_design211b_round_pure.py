"""design/211 part B, the round (sections 3.5 and 3.8): the round file as proposals, the first go of three sets, the states, the looks at a
made set before the operator sees it, the second go on the operator's word, the remake by a rewritten request (three makes at most), a
second send of the round file that never orders a set, and every "what next" sentence of part B.

Each refusal is asserted against its constant. Part A's functions are stood in for by `finder` (test_design211b_sets_pure). Without a database."""
import copy
import io
import json

import pytest
from PIL import Image

from app import main, page_flow, ref_find, ref_sets as RS, visuals_stage as VS
from app.errors import Problem
import d211_fixture as F
from test_design211b_sets_pure import RUN, SHEET, el, finder, ready, saved, store_of   # noqa: F401 (finder is the stand-in for part A, on every test)
from test_visuals_stage_pure import FakeConn, USER

FILE = [{'element_id': e, 'rec': F.ROWS[e][0], 'reason': F.ROWS[e][1], **({'first': True} if F.ROWS[e][3] else {}), **({'prompt': F.ROWS[e][4]} if F.ROWS[e][4] else {})} for e in F.THINGS]
STEP1 = {'MASON': {'verdict': 'approve'}, 'TROWEL': {'verdict': 'approve'}, 'FAN': {'verdict': 'ignore'}, 'BRICK': {'verdict': 'approve'},
         'STREET': {'verdict': 'approve', 'words': 'The street is wider than it looks.'}, 'T_LAY': {'verdict': 'approve'}, 'TILE': {'verdict': 'approve'}}
SET_INR = '35'      # one set of three on Gemini at the test's prices, to the rupee
WHO = "Google's image model"


def fresh(**over):
    """A film whose plan is accepted and whose footage is searched; no round yet."""
    s = ready('1')
    s.pop('round')
    s.update(over)
    return s


def rows(**change):
    """The fixture's round file, with rows changed: rows(FAN={'rec': 'set'}); None drops a row."""
    out = []
    for r in copy.deepcopy(FILE):
        c = change.get(r['element_id'], {})
        if c is not None:
            out.append({**r, **c})
    return out


def film(session=None, plan=None):
    return store_of(session or fresh(), plan), FakeConn([])


def post(store, conn, file=None):
    return VS.guarded(lambda: VS.round_start(store, USER, RUN, [], FILE if file is None else file, conn=conn))


def refused(fn):
    with pytest.raises(Problem) as e:
        VS.guarded(fn)
    return e.value.message


def done(store, conn, verdicts=None, **change):
    return VS.guarded(lambda: VS.round_done(store, USER, RUN, [], {**copy.deepcopy(verdicts or STEP1), **change}, 'Done, on the page', conn=conn))


def put(store, s):
    store.files[f"{RUN['id']}/visuals/session.json"] = json.dumps(s).encode('utf-8')


def req(p):
    return p[2].obj if hasattr(p[2], 'obj') else p[2]


def jobs(conn):
    return {req(p)['reference']['element_id']: req(p) for p in conn.inserted}


def back(store, pictures=3, fail=()):
    """What the image worker leaves when the sets come back: `pictures` pictures each; a thing in `fail` gets none."""
    s = saved(store)
    for r in list(s['references'].values()):
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            if r['element_id'] in fail:
                r.update(status='failed', error=f"{WHO} {r['generation']['model']} returned no picture: SAFETY", failure={'failure': 'no_image', 'http_status': 400})
                continue
            r.update(status='candidate', key=f"{RUN['id']}/visuals/references/{r['id']}.png", sha256='sha-' + r['id'], bytes=9, width=2752, height=1536, notes='(1) One variant.', sources=[],
                     view=RS.view_names(el(r['element_id']))[0])
            for n in range(2, pictures + 1):
                s['references'][f"{r['id']}-{n}"] = {**r, 'id': f"{r['id']}-{n}", 'set_n': n, 'key': f"{RUN['id']}/visuals/references/{r['id']}-{n}.png", 'view': RS.view_names(el(r['element_id']))[n - 1]}
    put(store, s)


def looks(store, recommend='use', only=None, **change):
    """The looks a helper sends for the sets that are due, as `vw visuals round --looks` lists them."""
    out = []
    for s in RS.looks_due(store, RUN, [])['sets']:
        if only is None or s['element_id'] in only:
            out.append({'element_id': s['element_id'], 'set': s['set'], 'recommend': recommend, 'golden': s['pictures'][0]['ref'] if recommend == 'use' else None, 'reason': 'All agree with the plan.',
                        'pictures': [{'ref': p['ref'], 'view': p['view'], 'verdict': 'pass', 'seen': p['view'] + ': as asked.'} for p in s['pictures']], **change})
    return out


def look(store, **kw):
    return VS.guarded(lambda: RS.round_looks(store, USER, RUN, [], looks(store, **kw), 'helper'))


def judge(store, conn, verdicts, partial=True):
    return VS.guarded(lambda: VS.round_sets(store, USER, RUN, [], verdicts, 'Sets done', conn=conn, partial=partial))


def state(store):
    s = saved(store)
    return VS._round_pass(s, s['round'])


def at_two(session=None):
    """A round whose first three sets are back and looked at: the operator's turn."""
    store, conn = film(session)
    post(store, conn)
    done(store, conn)
    back(store)
    look(store)
    return store, conn


def yes(store, eid):
    row = saved(store)['round']['elements'][eid]
    return {'verdict': 'yes', 'golden': row['set']}


# ---------- the round file: a new round ----------

def test_a_film_with_no_round_gets_a_v2_round_with_the_fields_of_each_row():
    store, conn = film()
    out = post(store, conn)
    assert out == {'pass': 1, 'elements': 7, 'kept': True, 'v': 2, 'doubtful': 4, 'then': RS.ROUND_POSTED.format(n=7, d=4)}
    rd = saved(store)['round']
    assert (rd['v'], rd['pass'], rd['go'], rd['rest'], rd['kept'], rd['quote']) == (2, 1, 1, [], True, None) and sorted(rd['elements']) == sorted(F.THINGS)
    assert rd['elements']['TROWEL'] == {'frames': ['f-trowel-side', 'f-trowel-use'], 'keywords': '', 'verdict': None, 'search_id': None, 'error': None, 'prompt': '', 'corrections': [], 'set': None, 'round': 0,
                                        'rec': 'footage', 'reason': 'The film shows it whole and sharp from the side.', 'doubt': True, 'first': False, 'operator_words': [], 'history': [],
                                        'fp': ref_find.fingerprint(el('TROWEL'))}   # design/211 review (M5): the plan's entry as it was when the round was sent
    assert rd['elements']['T_LAY']['prompt'] == 'The brick is wet from soaking.' and rd['elements']['T_LAY']['first'] is True and rd['elements']['TILE']['frames'] == ['f-tile-under']
    assert VS.round_v2(saved(store)) and state(store) == 1 and conn.inserted == []


def test_an_empty_prompt_is_accepted_and_how_words_are_not_refused():
    store, conn = film()
    post(store, conn, rows(STREET={'prompt': ''}, T_LAY={'prompt': 'Step by step, the brick is lowered.'}))
    e = saved(store)['round']['elements']
    assert e['STREET']['prompt'] == '' and e['MASON']['prompt'] == '' and e['T_LAY']['prompt'] == 'Step by step, the brick is lowered.'


def doubts(session=None, **change):
    store, conn = film(session)
    post(store, conn, rows(**change))
    return {eid: r['doubt'] for eid, r in saved(store)['round']['elements'].items()}


def test_a_row_is_doubtful_in_each_of_its_cases():
    d = doubts()
    assert d == {'MASON': False, 'TROWEL': True, 'FAN': True, 'BRICK': True, 'STREET': False, 'T_LAY': False, 'TILE': True}
    # TROWEL: a kept frame is weak. FAN: not found, with a closest picture. BRICK: not searched. TILE: the client's own thing, and the proposal is not its footage picture
    s = fresh()
    s['references']['f-trowel-use'].update(weak=False)
    assert doubts(s)['TROWEL'] is False and doubts(s, TROWEL={'rec': 'clean'})['TROWEL'] is False and doubts(s, TROWEL={'rec': 'set'})['TROWEL'] is True   # exact, and neither footage nor clean
    s = fresh()
    s['found']['FAN']['closest'] = None
    s['found']['BRICK'] = {**s['found']['STREET']}
    d = doubts(s, TILE={'rec': 'footage'})
    assert (d['FAN'], d['BRICK'], d['TILE']) == (False, False, False)
    assert doubts(s, STREET={'doubt': True})['STREET'] is True                      # the row says so
    s.pop('spec_approvals')                                                         # a cause stands: BRICK's material spec is not approved
    assert doubts(s)['BRICK'] is True and doubts(s, BRICK={'rec': 'no_set'})['BRICK'] is False


@pytest.mark.parametrize('change, message', [
    ({'FAN': {'rec': None}}, RS.REC_MISSING.format(eid='FAN')),
    ({'FAN': {'rec': 'web'}}, RS.REC_UNKNOWN.format(eid='FAN', rec='web')),
    ({'FAN': {'rec': 'footage'}}, RS.REC_NO_FRAME.format(eid='FAN', rec='footage')),
    ({'STREET': {'rec': 'clean'}}, RS.REC_NO_FRAME.format(eid='STREET', rec='clean')),
    ({'MASON': {'rec': 'no_set'}}, RS.REC_PERSON.format(eid='MASON')),
    ({'MASON': {'rec': 'leave'}}, RS.REC_PERSON.format(eid='MASON')),
    ({'BRICK': {'reason': '  '}}, RS.REASON_MISSING.format(eid='BRICK', max=300)),
    ({'BRICK': {'reason': 'x' * 301}}, RS.REASON_MISSING.format(eid='BRICK', max=300)),
    ({'BRICK': {'first': True}}, RS.FIRST_TOO_MANY.format(n=4, max=3)),
    ({'TROWEL': {'frames': ['f-tile-under-2']}}, ref_find.FRAME_NO_LOOK.format(fid='f-tile-under-2', eid='TROWEL')),
])
def test_a_faulty_row_is_refused_by_its_constant(change, message):
    store, conn = film()
    assert refused(lambda: post(store, conn, rows(**change))) == message
    assert 'round' not in saved(store)


def test_a_thing_with_no_search_record_is_refused_by_part_as_constant():
    s = fresh()
    s['found'].pop('STREET')
    store, conn = film(s)
    assert refused(lambda: post(store, conn)) == ref_find.NOT_SEARCHED.format(eid='STREET')


def test_every_faulty_row_is_named_in_one_refusal():
    store, conn = film()
    message = refused(lambda: post(store, conn, rows(FAN={'rec': None, 'reason': ''}, MASON={'rec': 'leave'}, STREET={'rec': 'clean'}, BRICK={'rec': 'photo'})))
    assert message.split('\n') == [RS.REC_PERSON.format(eid='MASON'), RS.REC_MISSING.format(eid='FAN'), RS.REASON_MISSING.format(eid='FAN', max=300), RS.REC_UNKNOWN.format(eid='BRICK', rec='photo'),
                                   RS.REC_NO_FRAME.format(eid='STREET', rec='clean')]


def test_the_older_refusals_of_a_round_file_stand_and_a_person_shown_in_a_made_picture_needs_its_row():
    store, conn = film()
    assert refused(lambda: post(store, conn, rows() + [{'element_id': 'DOG', 'rec': 'set', 'reason': 'x'}])) == VS.ANIMAL_NO_SHEET.format(eid='DOG')
    assert refused(lambda: post(store, conn, rows() + [{'element_id': 'NOPE', 'rec': 'set', 'reason': 'x'}])) == 'Unknown element NOPE.'
    assert 'add a row for MASON' in refused(lambda: post(store, conn, rows(MASON=None)))


def test_which_round_a_round_file_makes():
    store, conn = film()
    post(store, conn)
    again = post(store, conn, rows(FAN={'rec': 'set'}))                 # a v2 round still at step 1, sent again: a v2 round again
    assert again['v'] == 2 and saved(store)['round']['elements']['FAN']['rec'] == 'set' and saved(store)['round']['v'] == 2
    older = F.older_session()                                           # an older round still at step 1, sent again: an older round again, to its end
    older['round'].update({'pass': 1})
    store, conn = film(older)
    out = VS.round_start(store, USER, RUN, [], [{'element_id': e, 'prompt': 'The subject.'} for e in F.THINGS], conn=conn)
    assert out == {'pass': 1, 'elements': 7, 'kept': True} and 'v' not in saved(store)['round'] and 'rec' not in saved(store)['round']['elements']['FAN']


def test_the_tests_of_the_older_round_can_still_start_one(monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', None)
    store, conn = film()
    out = VS.round_start(store, USER, RUN, [], [{'element_id': e, 'prompt': 'The subject.'} for e in F.THINGS], conn=conn)
    assert out == {'pass': 1, 'elements': 7, 'kept': True} and 'v' not in saved(store)['round']
    assert 'the reference round is next, before any picture: `vw visuals elements`' in VS.round_due(fresh(accepted={'G1': {}}), F.plan())


def test_a_film_with_no_round_is_sent_to_the_search_first():
    assert VS.round_due(fresh(), F.plan()) == ref_find.FIND_START and VS.ROUND_V == 2
    assert VS.round_due(F.session('1'), F.plan()) is None and VS.round_due(fresh(accepted={}), F.plan()) is None


# ---------- step 1 recorded: the first go ----------

def test_done_orders_the_three_marked_sets_and_the_others_wait():
    store, conn = film()
    post(store, conn)
    out = done(store, conn)
    assert out['queued'] == ['MASON', 'STREET', 'T_LAY'] and out['rest'] == ['BRICK', 'TILE'] and out['from_footage'] == ['TROWEL'] and out['errors'] == {} and out['pass'] == 'making'
    assert out['then'] == RS.GO1_MAKING.format(k=3, x='106', r=2) and out['cost_inr'] == 106.13
    s = saved(store)
    rd = s['round']
    assert rd['rest'] == ['BRICK', 'TILE'] and rd['go'] == 1 and list(jobs(conn)) == ['MASON', 'STREET', 'T_LAY'] and state(store) == 'making'
    assert s['golden'] == {'TROWEL': 'f-trowel-side'} and rd['elements']['TROWEL']['from_footage'] and rd['elements']['FAN']['ignored'] and not rd['elements']['BRICK'].get('set')
    assert all(s['references'][f]['status'] == 'approved' for f in ('f-trowel-side', 'f-trowel-use', 'f-tile-under'))
    assert all(rd['elements'][e]['corrections'] == [] and rd['elements'][e]['round'] == 1 for e in F.FIRST)


def test_the_request_of_an_ordered_set_is_the_servers_with_its_views_and_the_row_keeps_its_parts():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    s = saved(store)
    for eid in F.FIRST:
        want = RS.set_request(F.plan(), RUN, s, el(eid), {k: v for k, v in s['round']['elements'][eid].items() if k != 'parts'})
        job, row = jobs(conn)[eid], s['round']['elements'][eid]
        assert job['prompt'].startswith(want['prompt']) and job['views'] == [v['ask'] for v in want['views']] and job['view_names'] == RS.view_names(el(eid)) and job['set'] is True
        assert row['parts'] == want['parts'] and row['made']['fp'] == RS.fp(F.plan(), s, el(eid)) and s['references'][row['set']]['server_checklist'] == want['lines']
        assert VS.KEPT_PREAMBLE not in job['prompt'] and VS.PERSON_SET not in job['prompt'] and 'Sizes: ' not in job['prompt'].replace(want['prompt'], '')
    assert jobs(conn)['STREET']['search'] is True and 'search' not in jobs(conn)['MASON'] and jobs(conn)['MASON']['parents'] == []
    assert "The operator's words: The street is wider than it looks." in jobs(conn)['STREET']['prompt']       # the step-1 comment reaches the request
    assert s['round']['elements']['STREET']['operator_words'] == ['The street is wider than it looks.'] and s['round']['elements']['MASON']['operator_words'] == []


def test_fewer_marked_rows_are_filled_by_kind_in_the_plans_order():
    store, conn = film()
    post(store, conn, rows(MASON={'first': False}, STREET={'first': False}))     # only T_LAY is marked
    out = done(store, conn)
    assert out['queued'] == ['MASON', 'BRICK', 'T_LAY'] and out['rest'] == ['STREET', 'TILE']   # a person and a material beside the way of working; the plan's order
    store, conn = film()
    post(store, conn, rows(MASON={'first': False}, STREET={'first': False}, T_LAY={'first': False}))
    assert done(store, conn)['queued'] == ['MASON', 'BRICK', 'STREET']                           # none marked: the first of three kinds


def test_things_of_one_kind_are_filled_in_the_plans_order_up_to_three():
    plan = F.plan()
    for e in plan['elements']:
        if e['id'] in ('BRICK', 'STREET', 'T_LAY'):
            e.update(kind='object', material_spec=None, signs_of_use=[])
    s = ready('1', plan)
    s.pop('round')
    store, conn = film(s, plan)
    post(store, conn, [dict(r, first=False) for r in rows(FAN={'rec': 'set'})])
    out = done(store, conn, FAN={'verdict': 'approve'})
    assert out['queued'] == ['MASON', 'FAN', 'BRICK'] and out['rest'] == ['STREET', 'T_LAY', 'TILE'] and out['from_footage'] == ['TROWEL']   # a person, an object, then the next object: no third kind


def test_three_sets_or_fewer_in_all_are_ordered_at_once():
    store, conn = film()
    post(store, conn)
    out = done(store, conn, BRICK={'verdict': 'ignore'}, TILE={'verdict': 'ignore'})
    assert out['queued'] == ['MASON', 'STREET', 'T_LAY'] and out['rest'] == [] and out['then'] == RS.ALL_MAKING.format(k=3, x='106')
    store, conn = film()
    post(store, conn)
    out = done(store, conn, **{e: {'verdict': 'ignore'} for e in ('BRICK', 'TILE', 'STREET', 'T_LAY')})
    assert out['queued'] == ['MASON'] and out['then'] == RS.ALL_MAKING.format(k=1, x=SET_INR) and saved(store)['round']['rest'] == []


def test_a_marked_thing_the_operator_left_out_gives_its_place_to_another():
    store, conn = film()
    post(store, conn)
    out = done(store, conn, STREET={'verdict': 'ignore'})
    assert out['queued'] == ['MASON', 'BRICK', 'T_LAY'] and out['rest'] == ['TILE'] and out['then'] == RS.GO1_MAKING.format(k=3, x='106', r=1)


def test_nothing_to_make_completes_the_round_and_says_so():
    store, conn = film()
    post(store, conn)
    out = done(store, conn, **{e: {'verdict': 'ignore'} for e in F.THINGS if e != 'TROWEL'})
    assert out['pass'] == 'complete' and out['queued'] == [] and out['from_footage'] == ['TROWEL'] and state(store) == 'complete' and conn.inserted == []
    assert out['then'] == RS.STEP1_NO_SET + ' ' + page_flow.ROUND_NEXT   # design/211 review (N8): one sentence, never "ok"


def test_clean_makes_a_set_from_the_footage_pictures():
    store, conn = film()
    post(store, conn)
    out = done(store, conn, TROWEL={'verdict': 'clean'}, BRICK={'verdict': 'ignore'}, TILE={'verdict': 'ignore'}, STREET={'verdict': 'ignore'})
    assert out['queued'] == ['MASON', 'TROWEL', 'T_LAY'] and out['from_footage'] == []
    s = saved(store)
    row, job = s['round']['elements']['TROWEL'], jobs(conn)['TROWEL']
    assert row['clean'] is True and not row.get('from_footage') and 'TROWEL' not in s['golden'] and row['parts']['source'] == 'footage'
    assert [p['id'] for p in job['parents']] == ['f-trowel-side', 'f-trowel-use'] and RS.FROM_FOOTAGE in job['prompt'] and job['search'] is True
    assert RS.FRAME_WEAK_LINE.format(k=2, name="Mason's trowel", view='in the hand, lifting mortar') in job['prompt']
    assert s['round']['elements']['MASON']['clean'] is False


def test_clean_without_a_footage_picture_is_refused():
    store, conn = film()
    post(store, conn)
    assert refused(lambda: done(store, conn, FAN={'verdict': 'clean'})) == RS.CLEAN_NO_FRAME.format(eid='FAN')
    assert saved(store)['round']['pass'] == 1 and conn.inserted == []
    assert 'a verdict is required: approve, clean' in refused(lambda: done(store, conn, FAN={'verdict': 'maybe'}))


def test_a_frame_marked_not_this_is_neither_an_input_nor_the_golden_picture():
    store, conn = film()
    post(store, conn)
    s = saved(store)
    s['references']['f-trowel-side'].update(status='rejected')           # part A's "Not this picture" rejects the frame
    put(store, s)
    out = done(store, conn)
    s = saved(store)
    assert out['from_footage'] == ['TROWEL'] and s['golden']['TROWEL'] == 'f-trowel-use' and s['round']['elements']['TROWEL']['frames'] == ['f-trowel-use']
    assert s['references']['f-trowel-side']['status'] == 'rejected'
    store, conn = film()
    post(store, conn)
    s = saved(store)
    s['references']['f-trowel-side'].update(status='rejected')
    put(store, s)
    done(store, conn, TROWEL={'verdict': 'clean'}, BRICK={'verdict': 'ignore'}, TILE={'verdict': 'ignore'}, STREET={'verdict': 'ignore'})
    assert [p['id'] for p in jobs(conn)['TROWEL']['parents']] == ['f-trowel-use']


def test_the_golden_picture_of_a_thing_from_footage_is_the_first_in_view_order():
    s = fresh()
    s['found']['TROWEL']['kept'] = ['f-trowel-use', 'f-trowel-side']     # the view order part A gives
    store, conn = film(s)
    post(store, conn, rows(TROWEL={'frames': []}))
    done(store, conn)
    assert saved(store)['golden']['TROWEL'] == 'f-trowel-use'


# ---------- the states ----------

def test_the_fixtures_states_read_as_the_contract_names_them():
    for name, want in {'1': 1, 'making': 'making', 'looking': 'looking', '2': 2, 'rewrite': 'rewrite', 'complete': 'complete'}.items():
        s = F.session(name)
        assert VS._round_pass(s, s['round']) == want and want in RS.STATES, name
        assert VS._round_view(s, F.plan())['pass'] == want


def test_the_round_moves_through_its_states_and_the_stored_pass_keeps_its_four_values():
    store, conn = film()
    post(store, conn)
    assert state(store) == 1
    done(store, conn)
    assert state(store) == 'making'
    back(store)
    assert state(store) == 'looking' and saved(store)['round']['pass'] == 'making'
    look(store, only=['MASON', 'STREET'])
    assert state(store) == 'looking'                                    # one set still has no look
    assert look(store)['then'] == RS.SETS_PAGE and state(store) == 2
    out = judge(store, conn, {'T_LAY': {'verdict': 'correct', 'words': 'Show the hand pressing the brick down.'}})
    assert state(store) == 'rewrite' == out['pass'] and saved(store)['round']['pass'] == 2
    VS.guarded(lambda: RS.round_rewrite(conn, store, USER, RUN, [], [{'element_id': 'T_LAY', 'prompt': 'The right hand presses the wet brick into the mortar bed.'}]))
    assert state(store) == 'making'
    back(store)
    assert state(store) == 'looking'
    look(store)
    assert state(store) == 2
    judge(store, conn, {e: yes(store, e) for e in F.FIRST})
    assert state(store) == 2 and saved(store)['round']['rest'] == ['BRICK', 'TILE']    # the round stays open while sets wait for the second go
    VS.guarded(lambda: RS.round_rest(conn, store, USER, RUN, [], 'make the others'))
    assert state(store) == 'making'
    back(store)
    look(store)
    out = judge(store, conn, {e: yes(store, e) for e in F.REST})
    assert out['pass'] == 'complete' == state(store) and saved(store)['round']['pass'] == 'complete'
    assert {saved(store)['round']['pass']} <= {1, 'making', 2, 'complete'}


def test_while_the_round_waits_for_claude_every_status_repeats_what_to_do():
    assert VS.round_due(F.session('looking'), F.plan()) == RS.SETS_LOOK and VS.round_due(F.session('rewrite'), F.plan()) == RS.rewrite_due(F.session('rewrite'))
    assert all(VS.round_due(F.session(k), F.plan()) is None for k in ('1', 'making', '2', 'complete')) and VS.round_due(F.older_session(), F.plan()) is None
    assert RS.then_of(F.session('2')) == RS.SETS_PAGE and RS.then_of(F.session('making')) is None and RS.then_of(F.session('complete')) is None


def test_a_failed_set_is_with_the_operator_and_its_line_names_who_failed():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store, fail=('STREET',))
    look(store)
    s = saved(store)
    assert state(store) == 2
    view = VS._round_view(s, F.plan(), VS._set_budget(RUN, s, VS.visuals_spend(conn, RUN)))['elements']['STREET']
    model = s['references'][s['round']['elements']['STREET']['set']]['generation']['model']
    assert view['problem'] == f'{WHO} {model} returned no picture.' and view['cause'] is None and 'OpenAI' not in view['problem']
    assert RS.set_facts(s, F.plan(), 'STREET', s['round']['elements']['STREET'])['fail']['cause'] == 'no_picture'


def test_a_partial_set_is_looked_at_and_judged_as_it_is():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store, pictures=2)
    due = RS.looks_due(store, RUN, [])['sets']
    assert [len(s['pictures']) for s in due] == [2, 2, 2]
    look(store)
    s = saved(store)
    assert state(store) == 2 and RS.set_facts(s, F.plan(), 'STREET', s['round']['elements']['STREET'])['partial'] == {'made': 2, 'asked': 3, 'missing': ['its fixed things']}


# ---------- the looks at a made set ----------

def png():
    out = io.BytesIO()
    Image.new('RGB', (64, 36), 'red').save(out, 'PNG')
    return out.getvalue()


def test_the_sets_to_look_at_come_with_their_facts_request_inputs_and_large_pictures():
    store, conn = film()
    post(store, conn)
    done(store, conn, TROWEL={'verdict': 'clean'}, MASON={'verdict': 'approve'}, STREET={'verdict': 'ignore'}, BRICK={'verdict': 'ignore'}, TILE={'verdict': 'ignore'})
    assert RS.looks_due(store, RUN, []) == {'sets': [], 'then': None, 'how': RS.LOOK_HOW}   # being made: nothing to look at yet
    back(store)
    s = saved(store)
    for r in ('f-trowel-side', s['round']['elements']['TROWEL']['set']):
        store.files[s['references'][r]['key']] = png()
    page_flow._MADE.clear()
    out = RS.looks_due(store, RUN, [])
    assert out['then'] == RS.SETS_LOOK and [x['element_id'] for x in out['sets']] == ['MASON', 'TROWEL', 'T_LAY']
    t = out['sets'][1]
    assert set(t) == {'element_id', 'name', 'set', 'facts', 'request', 'inputs', 'pictures', 'notes'} and t['name'] == "Mason's trowel" and t['set'] == s['round']['elements']['TROWEL']['set']
    assert t['facts'] == RS.thing_facts(F.plan(), s, el('TROWEL')) and t['request'] == jobs(conn)['TROWEL']['prompt'] and t['notes'] == '(1) One variant.'
    zoom = page_flow.PIC_SIZES['zoom'][0]
    assert t['inputs'][0] == {'ref': 'f-trowel-side', 'role': 'footage', 'view': 'side', 'key': s['references']['f-trowel-side']['key'] + zoom} and store.exists(t['inputs'][0]['key'])
    assert [(p['ref'], p['n'], p['view']) for p in t['pictures']] == [(t['set'], 1, 'side'), (t['set'] + '-2', 2, 'in the hand, lifting mortar'), (t['set'] + '-3', 3, 'the detail that shows how it is made')]
    assert t['pictures'][0]['key'].endswith(zoom) and t['pictures'][0]['check'] == {'state': 'none', 'failed': [], 'error': None}
    assert t['pictures'][1]['key'] == s['references'][t['set'] + '-2']['key']        # a picture that cannot be shrunk is given at its full size
    assert RS.looks_due(store_of(F.older_session()), RUN, []) == {'sets': [], 'then': None}


def test_the_looks_are_recorded_on_each_picture_and_on_the_row():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    sent = looks(store, only=['STREET'])
    out = RS.round_looks(store, USER, RUN, [], sent, 'helper')
    assert out == {'recorded': ['STREET'], 'refused': {}, 'left': ['MASON', 'T_LAY'], 'then': RS.SETS_LOOK}
    s = saved(store)
    row = s['round']['elements']['STREET']
    assert row['set_look'] == {'who': 'helper', 'at': row['set_look']['at'], 'set': row['set'], 'recommend': 'use', 'golden': row['set'], 'reason': 'All agree with the plan.'}
    pic = s['references'][row['set'] + '-2']
    assert pic['look'] == {'who': 'helper', 'at': row['set_look']['at'], 'view': 'from the other side', 'verdict': 'pass', 'seen': 'from the other side: as asked.', 'trial': None, 'ref': pic['id']}
    assert RS.looked(s, 'STREET', row) and not RS.looked(s, 'MASON', s['round']['elements']['MASON'])
    out = RS.round_looks(store, USER, RUN, [], looks(store, recommend='doubt'), 'someone')
    assert out['recorded'] == ['MASON', 'T_LAY'] and out['left'] == [] and out['then'] == RS.SETS_PAGE and saved(store)['round']['elements']['MASON']['set_look']['who'] == 'assistant'


@pytest.mark.parametrize('change, message', [
    ({'set': 's-older'}, lambda s: RS.LOOK_SET_UNKNOWN.format(eid='STREET', set='s-older')),
    ({'pictures': 'drop'}, lambda s: RS.LOOK_PICTURES.format(eid='STREET', missing='its fixed things')),
    ({'recommend': 'maybe'}, lambda s: RS.LOOK_VERDICT.format(eid='STREET')),
    ({'pictures': 'verdict'}, lambda s: RS.LOOK_VERDICT.format(eid='STREET')),
    ({'reason': ' '}, lambda s: RS.LOOK_SEEN.format(eid='STREET', max=300)),
    ({'pictures': 'seen'}, lambda s: RS.LOOK_SEEN.format(eid='STREET', max=300)),
    ({'pictures': 'long'}, lambda s: RS.LOOK_SEEN.format(eid='STREET', max=300)),
    ({'golden': 'f-trowel-side'}, lambda s: RS.LOOK_GOLDEN.format(eid='STREET')),
])
def test_a_faulty_look_is_refused_by_its_constant_and_the_other_sets_are_recorded(change, message):
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    sent = looks(store)
    mine = next(s for s in sent if s['element_id'] == 'STREET')
    how = change.pop('pictures', None)
    mine.update(change)
    if how == 'drop':
        mine['pictures'].pop()
    elif how:
        mine['pictures'][1].update({'verdict': {'verdict': 'good'}, 'seen': {'seen': ''}, 'long': {'seen': 'x' * 301}}[how])
    out = RS.round_looks(store, USER, RUN, [], sent, 'helper')
    assert out['refused'] == {'STREET': message(saved(store))} and out['recorded'] == ['MASON', 'T_LAY'] and out['left'] == ['STREET'] and out['then'] == RS.SETS_LOOK
    assert 'set_look' not in saved(store)['round']['elements']['STREET'] and state(store) == 'looking'


def test_a_look_for_a_set_that_was_never_made_or_at_step_1_is_refused():
    store, conn = film()
    post(store, conn)
    assert refused(lambda: RS.round_looks(store, USER, RUN, [], [], 'helper')) == 'No set of the reference round waits for a look.'
    done(store, conn)
    out = RS.round_looks(store, USER, RUN, [], [{'element_id': 'BRICK', 'set': None, 'recommend': 'use', 'reason': 'x', 'pictures': []}], 'helper')
    assert out['refused'] == {'BRICK': RS.LOOK_SET_UNKNOWN.format(eid='BRICK', set=None)}


def test_no_set_is_answered_before_its_look_is_recorded():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    assert refused(lambda: judge(store, conn, {'STREET': {'verdict': 'no'}})) == RS.SET_NO_LOOK.format(eid='STREET')
    assert refused(lambda: judge(store, conn, {})) == RS.SET_NO_LOOK.format(eid='MASON')
    assert refused(lambda: VS.set_answer(store, USER, RUN, [], 'STREET', 'yes', None, '')) == RS.SET_NO_LOOK.format(eid='STREET')
    look(store, only=['STREET'])
    assert VS.set_answer(store, USER, RUN, [], 'STREET', 'no', None, '')['stored'] is True       # its own look is recorded: its answer can be stored
    assert refused(lambda: VS.set_answer(store, USER, RUN, [], 'MASON', 'yes', None, '')) == RS.SET_NO_LOOK.format(eid='MASON')
    assert refused(lambda: judge(store, conn, {'STREET': {'verdict': 'no'}})) == 'No reference round is waiting for its sets.'   # the round is still with Claude
    assert saved(store)['references'][saved(store)['round']['elements']['STREET']['set']]['status'] == 'candidate'


def test_the_first_sets_are_judged_from_the_chat_tool_while_the_others_wait():
    store, conn = at_two()
    out = judge(store, conn, {e: yes(store, e) for e in F.FIRST}, partial=False)      # the chat tool: every set needs its answer; BRICK and TILE are not sets yet
    assert out['approved'] == ['MASON', 'STREET', 'T_LAY'] and out['pass'] == 2 and out['then'] is None and saved(store)['golden']['STREET'] == saved(store)['round']['elements']['STREET']['set']
    assert 'a verdict is required' in refused(lambda: judge(at_two()[0], conn, {'MASON': {'verdict': 'yes'}}, partial=False))   # of the first sets, each is still asked
    store, conn = at_two()
    VS.set_aside(store, USER, RUN, [], 'FAN', back=True)                               # FAN is back with the operator (they asked for it by name): the round stays open for it
    assert judge(store, conn, {e: yes(store, e) for e in F.FIRST}, partial=False)['pass'] == 2
    VS.set_aside(store, USER, RUN, [], 'BRICK', '')
    VS.set_aside(store, USER, RUN, [], 'TILE', '')
    assert judge(store, conn, {})['pass'] == 2 and saved(store)['round']['elements']['FAN']['reopened'] == 'asked'


# ---------- the second go ----------

def test_the_other_sets_are_ordered_on_the_operators_word():
    store, conn = at_two()
    out = VS.guarded(lambda: RS.round_rest(conn, store, USER, RUN, [], 'make the other two'))
    assert out == {'pass': 'making', 'queued': ['BRICK', 'TILE'], 'errors': {}, 'cost_inr': 70.75, 'then': RS.ALL_MAKING.format(k=2, x='71')}
    rd = saved(store)['round']
    assert rd['rest'] == [] and rd['go'] == 2 and rd['rest_word']['quote'] == 'make the other two' and list(jobs(conn)) == ['MASON', 'STREET', 'T_LAY', 'BRICK', 'TILE']
    tile = jobs(conn)['TILE']
    assert [p['id'] for p in tile['parents']] == ['f-tile-under', SHEET] and RS.FROM_FOOTAGE in tile['prompt'] and VS.KEPT_DRAWN_LINE in tile['prompt']
    assert VS.material_sentence(el('BRICK')) in jobs(conn)['BRICK']['prompt'] and jobs(conn)['BRICK']['prompt'].count('Material spec, Brick') == 1
    assert refused(lambda: RS.round_rest(conn, store, USER, RUN, [], 'again')) == RS.REST_NOT_NOW      # the second go is given once


def test_the_second_go_is_not_taken_before_the_first_sets_are_back_and_looked_at():
    store, conn = film()
    post(store, conn)
    assert refused(lambda: RS.round_rest(conn, store, USER, RUN, [], 'now')) == RS.REST_NOT_NOW      # step 1
    done(store, conn)
    assert refused(lambda: RS.round_rest(conn, store, USER, RUN, [], 'now')) == RS.REST_NOT_NOW      # being made
    back(store)
    assert refused(lambda: RS.round_rest(conn, store, USER, RUN, [], 'now')) == RS.REST_NOT_NOW      # not looked at
    assert refused(lambda: RS.round_rest(conn, store_of(F.older_session()), USER, RUN, [], 'now')) == RS.REST_NOT_NOW
    assert len(conn.inserted) == 3


def test_the_second_go_is_taken_while_a_first_set_waits_for_its_rewrite():
    store, conn = at_two()
    judge(store, conn, {'T_LAY': {'verdict': 'no'}})
    assert state(store) == 'rewrite' and RS.round_rest(conn, store, USER, RUN, [], 'and the others')['queued'] == ['BRICK', 'TILE']


def test_no_set_waiting_is_refused():
    store, conn = film()
    post(store, conn)
    done(store, conn, BRICK={'verdict': 'ignore'}, TILE={'verdict': 'ignore'})
    back(store)
    look(store)
    assert refused(lambda: RS.round_rest(conn, store, USER, RUN, [], 'now')) == RS.REST_NONE
    store, conn = at_two()
    VS.set_aside(store, USER, RUN, [], 'BRICK', 'not needed')
    VS.set_aside(store, USER, RUN, [], 'TILE', 'not needed')
    assert RS.rest_of(saved(store)['round']) == [] and refused(lambda: RS.round_rest(conn, store, USER, RUN, [], 'now')) == RS.REST_NONE
    assert judge(store, conn, {e: yes(store, e) for e in F.FIRST})['pass'] == 'complete'     # the others set aside: nothing holds the round open


def test_when_the_limit_has_no_room_for_all_of_them_none_is_ordered():
    store, conn = at_two()
    s = saved(store)
    s['cap_inr'] = 50
    put(store, s)
    assert refused(lambda: RS.round_rest(conn, store, USER, RUN, [], 'now')) == RS.REST_CAP.format(n=2, x='71', spent='0', cap='50')
    assert len(conn.inserted) == 3 and saved(store)['round']['rest'] == ['BRICK', 'TILE'] and saved(store)['round']['go'] == 1 and state(store) == 2


# ---------- "No" and "Correct it": the rewrite ----------

def test_no_orders_nothing_and_waits_for_the_rewrite():
    store, conn = at_two()
    before = saved(store)['round']['elements']['T_LAY']['set']
    out = judge(store, conn, {'T_LAY': {'verdict': 'correct', 'words': 'Show the hand pressing the brick down.'}, 'STREET': {'verdict': 'no'}})
    assert out['queued'] == [] and out['rewrite'] == ['STREET', 'T_LAY'] and out['pass'] == 'rewrite' and len(conn.inserted) == 3 and out['then'] == RS.rewrite_due(saved(store)) and out['then'].startswith('2 set(s) wait for your rewrite: STREET (no words')
    s = saved(store)
    lay, street = s['round']['elements']['T_LAY'], s['round']['elements']['STREET']
    assert lay['rewrite_due'] == {'words': 'Show the hand pressing the brick down.', 'set': before, 'at': lay['rewrite_due']['at']} and lay['operator_words'] == ['Show the hand pressing the brick down.']
    assert street['rewrite_due']['words'] == '' and street['operator_words'] == ['The street is wider than it looks.'] and lay['corrections'] == [] == street['corrections']
    assert all(s['references'][r]['status'] == 'rejected' for r in (before, before + '-2', before + '-3')) and lay['verdict'] == 'correct' and lay['round'] == 1


def rewritten(store, conn, prompt='The right hand presses the wet brick into the mortar bed.', eid='T_LAY'):
    return VS.guarded(lambda: RS.round_rewrite(conn, store, USER, RUN, [], [{'element_id': eid, 'prompt': prompt}]))


def test_the_rewrite_keeps_the_earlier_request_and_orders_the_set_once():
    store, conn = at_two()
    before = saved(store)['round']['elements']['T_LAY']['set']
    judge(store, conn, {'T_LAY': {'verdict': 'correct', 'words': 'Show the hand pressing the brick down.'}})
    out = rewritten(store, conn)
    assert out == {'pass': 'making', 'queued': ['T_LAY'], 'errors': {}, 'cost_inr': 35.38, 'then': RS.REWRITE_MAKING.format(n=1, x=SET_INR)} and len(conn.inserted) == 4
    s = saved(store)
    row, job = s['round']['elements']['T_LAY'], req(conn.inserted[-1])
    assert row['history'] == [{'n': 1, 'set': before, 'added': 'The brick is wet from soaking.', 'operator': 'Show the hand pressing the brick down.', 'at': row['history'][0]['at']}]
    assert row['prompt'] == 'The right hand presses the wet brick into the mortar bed.' and 'rewrite_due' not in row and row['round'] == 2 and row['set'] != before
    assert "Added by the film's writer: The right hand presses the wet brick into the mortar bed." in job['prompt'] and "The operator's words: Show the hand pressing the brick down." in job['prompt']
    assert 'The brick is wet from soaking.' not in job['prompt'] and "The operator's correction" not in job['prompt'] and job['parents'] == []
    assert s['references'][before]['generation']['prompt'] != job['prompt']          # the earlier request stays on the earlier set
    assert refused(lambda: rewritten(store, conn, 'Another one.')) == RS.REWRITE_NOT_DUE.format(eid='T_LAY') and len(conn.inserted) == 4
    back(store)
    look(store)
    f = RS.set_facts(saved(store), F.plan(), 'T_LAY', saved(store)['round']['elements']['T_LAY'])
    assert f['asked'] == 'Show the hand pressing the brick down.' and f['makes'] == 2 and f['makes_left'] == 1 and len(f['history']) == 1


@pytest.mark.parametrize('prompt, message', [('', RS.REWRITE_EMPTY.format(eid='T_LAY')), ('   ', RS.REWRITE_EMPTY.format(eid='T_LAY')),
                                             ('The brick is wet from soaking.', RS.REWRITE_SAME.format(eid='T_LAY')), ('the brick  is wet from SOAKING.', RS.REWRITE_SAME.format(eid='T_LAY'))])
def test_an_empty_rewrite_and_the_same_words_are_refused(prompt, message):
    store, conn = at_two()
    judge(store, conn, {'T_LAY': {'verdict': 'no'}})
    assert refused(lambda: rewritten(store, conn, prompt)) == message
    assert len(conn.inserted) == 3 and 'rewrite_due' in saved(store)['round']['elements']['T_LAY'] and state(store) == 'rewrite'


def test_a_rewrite_nobody_asked_for_is_refused_and_one_faulty_row_stops_the_call():
    store, conn = at_two()
    assert refused(lambda: rewritten(store, conn, 'New words.', 'STREET')) == RS.REWRITE_NOT_DUE.format(eid='STREET')
    judge(store, conn, {'T_LAY': {'verdict': 'no'}})
    both = [{'element_id': 'T_LAY', 'prompt': 'New words.'}, {'element_id': 'STREET', 'prompt': 'New words.'}]
    assert refused(lambda: RS.round_rewrite(conn, store, USER, RUN, [], both)) == RS.REWRITE_NOT_DUE.format(eid='STREET') and len(conn.inserted) == 3
    assert refused(lambda: RS.round_rewrite(conn, store_of(F.older_session()), USER, RUN, [], both)) == 'No reference round waits for a rewrite.'


def test_after_three_makes_no_and_correct_it_are_held():
    store, conn = at_two()
    for n, words in ((2, 'Second.'), (3, 'Third.')):
        judge(store, conn, {'T_LAY': {'verdict': 'no'}})
        rewritten(store, conn, words)
        back(store)
        look(store)
        assert saved(store)['round']['elements']['T_LAY']['round'] == n
    live = saved(store)['round']['elements']['T_LAY']['set']
    out = judge(store, conn, {'T_LAY': {'verdict': 'correct', 'words': 'Once more.'}})
    assert out['held'] == {'T_LAY': RS.MAKES_LIMIT.format(eid='T_LAY', max=3)} and out['queued'] == [] and out['rewrite'] == [] and len(conn.inserted) == 5
    s = saved(store)
    row = s['round']['elements']['T_LAY']
    assert 'rewrite_due' not in row and s['references'][live]['status'] == 'candidate' and row['operator_words'] == [] and state(store) == 2 and len(row['history']) == 2
    assert refused(lambda: VS.set_answer(store, USER, RUN, [], 'T_LAY', 'no', None, '')) == RS.MAKES_LIMIT.format(eid='T_LAY', max=3)
    assert RS.set_facts(s, F.plan(), 'T_LAY', row)['makes_left'] == 0
    assert judge(store, conn, {'T_LAY': yes(store, 'T_LAY')})['approved'] == ['T_LAY']                 # "use one of these" still stands


def test_a_set_made_three_times_can_be_left_out_and_one_made_less_often_cannot():
    store, conn = at_two()
    assert 'only a set that was never made can be set aside' in refused(lambda: VS.set_aside(store, USER, RUN, [], 'T_LAY', 'no'))
    s = saved(store)
    s['round']['elements']['T_LAY']['round'] = 3
    put(store, s)
    live = s['round']['elements']['T_LAY']['set']
    assert VS.set_aside(store, USER, RUN, [], 'T_LAY', 'None of these.')['aside'] is True
    s = saved(store)
    assert s['round']['elements']['T_LAY']['ignored'] and s['references'][live]['status'] == 'rejected' and s['references'][live]['rejection']['notes'] == 'None of these.'


def test_the_others_left_out_do_not_hold_the_round_open():
    store, conn = at_two()
    judge(store, conn, {e: yes(store, e) for e in F.FIRST})
    assert state(store) == 2                                          # BRICK and TILE wait
    VS.set_aside(store, USER, RUN, [], 'BRICK', '')
    assert state(store) == 2
    VS.set_aside(store, USER, RUN, [], 'TILE', '')                    # "Leave these out": nothing is left with the operator
    assert state(store) == 'complete' and VS._round_view(saved(store), F.plan())['pass'] == 'complete'
    store, conn = at_two()
    VS.set_aside(store, USER, RUN, [], 'BRICK', '')
    VS.set_aside(store, USER, RUN, [], 'TILE', '')
    assert state(store) == 2                                          # the first sets are not judged yet
    judge(store, conn, {'T_LAY': {'verdict': 'no'}})
    assert state(store) == 'rewrite' and VS.set_aside(store, USER, RUN, [], 'BRICK', '', back=True)['aside'] is False   # brought back while Claude rewrites


# ---------- a second send of the round file ----------

def test_a_second_send_orders_nothing_and_only_a_new_thing_goes_back_to_the_operator():   # design/211 review (M5): a thing the operator left out stays left out
    store, conn = at_two()
    s = saved(store)
    s['round']['elements'].pop('TILE')                                   # as if the plan named TILE only after the round was posted
    s['round']['rest'] = ['BRICK']
    s['round']['elements']['BRICK'].update(error='the material spec of BRICK is not approved')
    put(store, s)
    out = post(store, conn, rows(FAN={'rec': 'set', 'reason': 'Seen close after all.'}, BRICK={'prompt': 'A wire-cut face.'}, STREET={'prompt': 'Another street.'}))
    assert out == {'pass': 2, 'kept': True, 'v': 2, 'merged': ['BRICK'], 'reopened': ['TILE'], 'left': ['MASON', 'TROWEL', 'FAN', 'STREET', 'T_LAY'], 'queued': [], 'errors': {}, 'elements': 7,
                   'cost_inr': 0, 'then': RS.MERGE_ASK.format(n=1)}
    assert len(conn.inserted) == 3                                       # nothing was ordered
    e = saved(store)['round']['elements']
    assert 'reopened' not in e['FAN'] and e['FAN']['ignored'] is True and e['FAN']['rec'] == 'no_set' and e['FAN']['reason'] != 'Seen close after all.'   # left out: the new row is not taken
    assert e['TILE']['reopened'] == 'new' and e['TILE']['verdict'] is None and e['TILE']['set'] is None and e['TILE']['frames'] == ['f-tile-under']
    assert e['BRICK']['prompt'] == 'A wire-cut face.' and e['BRICK']['error'] is None and not e['BRICK'].get('set') and 'reopened' not in e['BRICK']   # not made: its paid button stays
    assert e['STREET']['prompt'] == '' and e['STREET']['set'] and e['TROWEL']['from_footage']                                                         # a set that is there is never replaced


def test_a_second_send_of_a_complete_round_opens_it_only_for_what_came_back():
    s = F.session('complete')
    store, conn = film(F.specs_approved(s, F.plan(), VS.spec_digest))
    out = post(store, conn, rows(FAN={'rec': 'set'}))                   # design/211 review (M5): the same plan: the things left out stay left out, the round stays complete
    assert out['reopened'] == [] and out['then'] == RS.MERGE_NONE and out['pass'] == 'complete' and conn.inserted == []
    back = VS.set_aside(store, USER, RUN, [], 'FAN', back=True)         # the operator asks for one by name: an open line, and the round is with them again
    assert back['then'] == RS.BACK_ASKED.format(eid='FAN') and saved(store)['round']['elements']['FAN']['reopened'] == 'asked' and state(store) == 2 and conn.inserted == []


def test_a_thing_that_came_back_is_answered_with_the_meaning_of_step_1():
    store, conn = at_two()
    VS.set_aside(store, USER, RUN, [], 'FAN', back=True)
    out = VS.guarded(lambda: RS.round_reopen(conn, store, USER, RUN, [], 'FAN', 'approve', 'The white one.', 'yes, make it'))
    assert out == {'element_id': 'FAN', 'queued': True, 'pass': 'making', 'cost_inr': 35.38, 'then': RS.ALL_MAKING.format(k=1, x=SET_INR)} and len(conn.inserted) == 4
    row = saved(store)['round']['elements']['FAN']
    assert 'reopened' not in row and row['ignored'] is False and row['verdict'] == 'approve' and row['operator_words'] == ['The white one.'] and row['answered']['quote'] == 'yes, make it'
    assert "The operator's words: The white one." in req(conn.inserted[-1])['prompt']
    assert refused(lambda: RS.round_reopen(conn, store, USER, RUN, [], 'FAN', 'approve', '', 'yes')) == RS.REOPEN_NOT_DUE.format(eid='FAN')
    assert refused(lambda: RS.round_reopen(conn, store, USER, RUN, [], 'STREET', 'ignore', '', 'no')) == RS.REOPEN_NOT_DUE.format(eid='STREET')


def test_a_thing_that_came_back_can_be_left_out_or_take_its_footage_picture():
    s = F.session('complete')
    store, conn = film(F.specs_approved(s, F.plan(), VS.spec_digest))
    for eid in ('FAN', 'BRICK', 'TILE'):
        VS.set_aside(store, USER, RUN, [], eid, back=True)
    out = VS.guarded(lambda: RS.round_reopen(conn, store, USER, RUN, [], 'BRICK', 'ignore', '', 'leave it'))
    assert out['queued'] is False and conn.inserted == [] and saved(store)['round']['elements']['BRICK']['ignored'] is True and 'reopened' not in saved(store)['round']['elements']['BRICK']
    assert refused(lambda: RS.round_reopen(conn, store, USER, RUN, [], 'FAN', 'clean', '', 'clean it')) == RS.CLEAN_NO_FRAME.format(eid='FAN')
    s = saved(store)
    s['drawings'] = {}                                                   # TILE without drawings: its footage picture is the reference, free
    put(store, s)
    out = VS.guarded(lambda: RS.round_reopen(conn, store, USER, RUN, [], 'TILE', 'approve', '', 'use it'))
    assert out['queued'] is False and conn.inserted == [] and saved(store)['golden']['TILE'] == 'f-tile-under' and saved(store)['round']['elements']['TILE']['from_footage'] is True


# ---------- one set made now ----------

def test_making_one_set_from_the_chat_tool_needs_the_operators_words():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store, fail=('STREET',))
    look(store)
    assert refused(lambda: VS.set_make(conn, store, USER, RUN, [], 'STREET', quote='')) == RS.MAKE_NO_QUOTE.format(eid='STREET')
    assert refused(lambda: VS.set_make(conn, store, USER, RUN, [], 'STREET', quote='  ')) == RS.MAKE_NO_QUOTE.format(eid='STREET') and len(conn.inserted) == 3
    out = VS.set_make(conn, store, USER, RUN, [], 'STREET', quote='yes, make it again')
    assert out['queued'] is True and out['then'] == RS.ALL_MAKING.format(k=1, x=SET_INR) and len(conn.inserted) == 4
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store, fail=('STREET',))
    look(store)
    assert VS.set_make(conn, store, USER, RUN, [], 'STREET')['queued'] is True      # the page and the chat question: the operator's click or answer is the word
    older = store_of(F.older_session())
    assert VS.set_make(FakeConn([]), older, USER, RUN, [], 'T_LAY', quote='')['queued'] is True and 'then' not in VS.set_make(FakeConn([]), store_of(F.older_session()), USER, RUN, [], 'T_LAY')


def test_a_set_whose_plan_changed_is_made_again_on_the_operators_word_and_never_by_itself():
    store, conn = at_two()
    assert refused(lambda: VS.set_make(conn, store, USER, RUN, [], 'STREET', quote='again')) == 'STREET has its set: judge it (Yes, No or Correct it).'
    plan = F.plan()
    el('STREET', plan)['description'] = 'A paved street between low houses.'
    store.files[f"{RUN['id']}/visuals/plan-v1.json"] = json.dumps({'document': plan}).encode('utf-8')
    s = saved(store)
    old = s['round']['elements']['STREET']['set']
    assert RS.set_facts(s, plan, 'STREET', s['round']['elements']['STREET'])['changed'] and len(conn.inserted) == 3 and state(store) == 2    # marked; nothing made
    out = VS.set_make(conn, store, USER, RUN, [], 'STREET', quote='the plan changed, make it again')
    assert out['queued'] is True and 'A paved street between low houses.' in req(conn.inserted[-1])['prompt']
    s = saved(store)
    assert s['references'][old]['status'] == 'rejected' and s['references'][old]['rejection']['notes'].startswith('the plan changed') and s['round']['elements']['STREET']['round'] == 2


def test_the_fourth_make_of_one_thing_is_refused_for_a_set_made_by_hand_too():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store, fail=('STREET',))
    look(store)
    s = saved(store)
    s['round']['elements']['STREET']['round'] = 4                      # design/211 review (M2): ordered four times, and the first returned no picture: three makes
    put(store, s)
    assert RS.makes(s, 'STREET', s['round']['elements']['STREET']) == 3
    assert refused(lambda: VS.set_make(conn, store, USER, RUN, [], 'STREET', quote='once more')) == RS.MAKES_LIMIT.format(eid='STREET', max=3)


# ---------- gap 23, in part ----------

def test_a_still_that_leaves_out_an_approved_reference_of_a_thing_its_shot_names_is_warned():
    s = F.session('complete')
    shot = F.plan()['gaps'][1]['scenes'][0]['shots'][1]                  # G2-S1-SH2: a still of TROWEL and BRICK
    trowel = s['references']['f-trowel-side']
    assert RS.unused_refs(s, F.plan(), shot, []) == [RS.UNUSED_REF.format(shot='G2-S1-SH2', name="Mason's trowel", eid='TROWEL')]     # BRICK has no approved reference: nothing to say
    assert RS.unused_refs(s, F.plan(), shot, [trowel]) == []
    wide = F.plan()['gaps'][0]['scenes'][0]['shots'][0]                  # STREET and the dog: an animal has no reference
    assert RS.unused_refs(s, F.plan(), wide, []) == [RS.UNUSED_REF.format(shot='G1-S1-SH1', name='The street', eid='STREET')]
    assert RS.unused_refs(F.session('1'), F.plan(), shot, []) == []     # nothing approved yet


def test_the_warning_is_given_for_a_still_only_and_never_for_a_set():
    text = open(VS.__file__, encoding='utf-8').read().splitlines()
    line = text[next(n for n, l in enumerate(text) if 'ref_sets.unused_refs(session, plan, named, parents)' in l) - 2]   # the condition the warning stands behind
    assert "round_v2(session)" in line and "named.get('visual_type') == 'image'" in line and "body['kind'] in ('keyframe', 'isolated')" in line and "not body.get('fix_of')" in line
    store, conn = film()
    post(store, conn)
    out = done(store, conn)
    assert 'warnings' not in out and not any('approved reference' in str(v) for v in out.values())


# ---------- the routes ----------

def test_the_routes_of_part_b_stand_after_the_round_routes():
    paths = {(r.path, tuple(sorted(r.methods))) for r in main.app.routes if hasattr(r, 'methods')}
    base = '/api/runs/{run_id}/visuals/round/'
    assert {(base + 'looks', ('GET',)), (base + 'looks', ('POST',)), (base + 'rest', ('POST',)), (base + 'rewrite', ('POST',))} <= paths
    assert main.RoundMake.model_fields['quote'].default == '' and set(main.RoundRest.model_fields) == {'request_id', 'quote'}
    assert set(main.RoundRewrite.model_fields) == {'request_id', 'rows'} and set(main.RoundLooks.model_fields) == {'request_id', 'by', 'sets'}
