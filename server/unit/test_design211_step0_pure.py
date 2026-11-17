"""design/211, step 0: the contract's stubs can be imported, the shared fixture has the contract's shapes, and a round without `v == 2`
is read as before. Without a database."""
import inspect

from app import ref_find, ref_sets, visuals_stage as VS
import d211_fixture as F

STATES = {'1': 1, 'making': 'making', 'looking': 'looking', '2': 2, 'rewrite': 'rewrite', 'complete': 'complete'}


def test_round_v2_is_true_only_for_a_round_made_after_the_rebuild():
    assert all(VS.round_v2(F.session(state)) for state in STATES)
    assert not VS.round_v2(F.older_session()) and not VS.round_v2({}) and not VS.round_v2(None) and not VS.round_v2({'round': None})


def test_an_older_round_is_read_as_before():
    s = F.older_session()
    assert VS._round_pass(s, s['round']) == 2 and VS.kept(s)
    assert VS.golden_of(s, 'TROWEL') == 'f-trowel-side'
    assert [r['id'] for r in VS._set_rows(s, 'STREET', s['round']['elements']['STREET']['set'])] == ['s-street-1', 's-street-1-2', 's-street-1-3']


def test_the_contracts_names_and_signatures():
    want = {ref_find: {'footage': 'store, run, outputs', 'digest': 'store, run, outputs', 'digest_answer': 'store, run, outputs', 'trial_id': 'clip, at_s',
                       'cut_trials': 'store, run, outputs, frames', 'trial_record': 'store, user, run, outputs, frames, cut',
                       'look_record': 'conn, store, user, run, outputs, things, by', 'round_frames': 'session, plan, eid, named', 'frames_of': 'session, eid',
                       'found_all': 'store, run, session, plan', 'fingerprint': 'element', 'not_this': 'conn, store, user, run, outputs, eid, ref_id, quote',
                       'that_is_it': 'conn, store, user, run, outputs, eid, trial, quote'},
            ref_sets: {'thing_facts': 'plan, session, element', 'views_for': 'element, plan, rd', 'view_names': 'element, rd', 'set_request': 'plan, run, session, element, row',
                       'check_summary': 'session, ref', 'set_facts': 'session, plan, eid, row', 'looks_due': 'store, run, outputs',
                       'round_looks': 'store, user, run, outputs, sets, by', 'round_rest': 'conn, store, user, run, outputs, quote',
                       'round_rewrite': 'conn, store, user, run, outputs, rows', 'round_reopen': 'conn, store, user, run, outputs, eid, verdict, words, quote'}}
    for module, names in want.items():
        for name, params in names.items():
            assert ', '.join(inspect.signature(getattr(module, name)).parameters) == params, (module.__name__, name)
    for name in ('FIND_START', 'FIND_WORDS', 'TRIAL_NEXT', 'LOOK_MORE', 'LOOK_ALL', 'FRAME_RULE', 'TRIAL_TOO_MANY', 'TRIAL_LIMIT', 'TRIAL_UNKNOWN_CLIP', 'LOOK_UNKNOWN_TRIAL',
                 'LOOK_VERDICT', 'LOOK_SEEN', 'LOOK_VIEW', 'KEEP_FAIL', 'KEEP_LIMIT', 'LOOK_NOTHING', 'FRAME_NO_LOOK', 'NOT_SEARCHED'):
        assert isinstance(getattr(ref_find, name), str), name
    for name in ('ROUND_POSTED', 'GO1_MAKING', 'ALL_MAKING', 'SETS_LOOK', 'SETS_PAGE', 'REWRITE_DUE', 'REWRITE_MAKING', 'MERGE_ASK', 'REC_MISSING', 'REC_UNKNOWN', 'REC_NO_FRAME',
                 'REC_PERSON', 'REASON_MISSING', 'FIRST_TOO_MANY', 'CLEAN_NO_FRAME', 'SET_NO_LOOK', 'LOOK_SET_UNKNOWN', 'LOOK_PICTURES', 'LOOK_VERDICT', 'LOOK_SEEN', 'LOOK_GOLDEN',
                 'REST_NOT_NOW', 'REST_NONE', 'REST_CAP', 'REWRITE_NOT_DUE', 'REWRITE_EMPTY', 'REWRITE_SAME', 'MAKES_LIMIT', 'MAKE_NO_QUOTE'):
        assert isinstance(getattr(ref_sets, name), str), name
    assert ref_sets.REWRITE_DUE.format(n=2, things='A; B').count('{element_id, prompt}') == 1   # the braces of the rows survive the formatting (design/211 review: the sentence names the things)
    assert set(ref_sets.REC_VERDICT) == set(ref_sets.RECS) and set(ref_sets.REC_VERDICT.values()) == set(ref_sets.STEP1_VERDICTS)


def test_the_fixture_has_the_contracts_shapes():
    plan = F.plan()
    kinds = {e['id']: e['kind'] for e in plan['elements']}
    assert {kinds[e] for e in F.THINGS} == {'person', 'object', 'material', 'place', 'technique'} and kinds['DOG'] == 'animal'
    for state in STATES:
        s = F.session(state)
        rd = s['round']
        assert rd['v'] == 2 and rd['kept'] and set(rd['elements']) == set(F.THINGS), state
        for eid, row in rd['elements'].items():
            assert row['rec'] in ref_sets.RECS and row['reason'] and isinstance(row['doubt'], bool) and isinstance(row['operator_words'], list), (state, eid)
        for ref in s['references'].values():
            if ref['kind'] == 'frame':
                assert ref['look']['verdict'] in ref_find.VERDICTS and ref['weak'] == (ref['look']['verdict'] == 'weak') and ref['view'] and ref['trial'] in F.TRIALS
        assert {v['result'] for v in s['found'].values()} == {'found', 'none', 'not_searched'}
    assert F.session('1')['round']['pass'] == 1 and not F.session('1')['round']['rest']
    making, looking, two, rewrite, done = (F.session(k) for k in ('making', 'looking', '2', 'rewrite', 'complete'))
    assert making['round']['rest'] == ['BRICK', 'TILE'] and making['references']['s-mason-1']['status'] == 'generating' and 's-mason-1-2' not in making['references']
    assert 'look' not in looking['references']['s-street-1'] and looking['references']['s-street-1']['check']['must_failed'] == []
    assert two['references']['s-t_lay-1-2']['check']['must_failed'] and two['round']['elements']['T_LAY']['set_look']['recommend'] == 'remake'
    assert all(two['references'][r]['look']['ref'] == r for r in ('s-street-1', 's-street-1-2', 's-street-1-3'))
    assert rewrite['round']['elements']['T_LAY']['rewrite_due']['set'] == 's-t_lay-1' and rewrite['references']['s-t_lay-1']['status'] == 'rejected'
    assert done['round']['pass'] == 'complete' and done['round']['elements']['T_LAY']['round'] == 2 and len(done['round']['elements']['T_LAY']['history']) == 1
    trials = F.trials()['trials']
    assert trials['t0000000000a1']['looks']['TROWEL']['ref'] == 'f-trowel-side' and trials['t0000000000c1']['looks']['FAN']['verdict'] == 'fail'
    assert [c['clip'] for c in F.digest()['clips']] == ['C001', 'C002'] and F.digest()['not_searched'][0]['clip'] == 'C003'
    assert VS.material_approved(F.specs_approved(F.session('2'), plan, VS.spec_digest), next(e for e in plan['elements'] if e['id'] == 'BRICK'))
