"""design/206 (SK, 16 Nov 2026): the plan's gaps answered on the Claude artifact page, as the treatment is (design/204). Every plan question is
on one round, so one "done" answers the step: the shared rules, a gap offered two ways (each way with its own shots; taking a way accepts the
gap), and each gap's shots as a table. The lines come from the function the chat and the card ask from; the answers go through the same
decision functions. Without a database: the harness of tests/check_shared_change.py."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
from app import chat_flow as C, page_flow as P, visuals_stage as V   # noqa: E402


def start(plan=None, treatment=None):
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    if treatment:
        s = H.session(store)
        s['treatment'] = treatment
        V.save_session(store, H.RUN, s)
    H.propose(store, plan or H.plan_of())
    return store, conn


def page(store, conn):
    return P.page(conn, store, H.USER, H.RUN, {})


def record(store, conn, answers):
    return P.page_record(conn, store, H.USER, H.RUN, {}, answers)


def ans(line, choice, notes=''):
    return {'line': line['line'], 'key': line['key'], 'item': line.get('item', ''), 'choice': choice, 'notes': notes}


def by_key(p):
    return {l['key']: l for l in p['lines']}


def test_the_plan_step_shows_every_gap_with_its_shots_as_a_table():
    store, conn = start(treatment={'gaps': [{'gap_id': 'G1', 'picture': 'the wall from the street'}]})
    p = page(store, conn)
    assert p['step'] == 'Plan' and p['open'] is True and [l['key'] for l in p['lines']] == ['G1', 'G2', 'G3'] and all(l['state'] == 'open' for l in p['lines'])
    g = p['lines'][0]
    assert g['line'] == 'l01' and g['title'] == 'Gap G1 · Title 1' and g['item'].startswith('gap:G1:')
    assert g['cols'] == C.GAP_COLS and g['table'] == [['1', 'Shot G1-S1', 'a still picture', '4.0 s', 'It shows the wall', 'words']]
    assert g['total'] == '1 shots, 4.0 s in all.' and g['mix'] == 'Made as: 1 × a still picture'
    assert g['text'] == 'What you accepted in the treatment: the wall from the street' and 'text' not in p['lines'][1]
    assert [(b['choice'], b['needs_words']) for b in g['buttons']] == [('accept', False), ('change', True)]
    assert '3 gaps' in p['summary'] and '3 to answer' in p['summary'] and 'treatment' not in p['how'].split('.')[0]


def test_one_done_records_every_answer_and_the_page_follows():
    store, conn = start()
    p = page(store, conn)
    r = record(store, conn, [ans(p['lines'][0], 'accept'), ans(p['lines'][1], 'change', 'show  the gate, not the wall'), ans(p['lines'][2], 'accept')])
    assert r['recorded'] == ['G1', 'G2', 'G3'] and r['stale'] == [] and r['refused'] == [] and r['open'] == 0
    s = H.session(store)
    assert set(s['accepted']) == {'G1', 'G3'} and s['revisions']['G2']['notes'] == 'show the gate, not the wall'
    now = by_key(r['page'])
    assert now['G1']['state'] == 'recorded' and now['G1']['reopen'] is True and now['G2'] == {'line': 'l02', 'key': 'G2', 'title': 'Gap G2 · Title 2', 'state': 'with_assistant',
                                                                                             'note': 'show the gate, not the wall'}
    assert 'back with you' in r['then'] and 'vw visuals page' in r['then']
    assert len(conn.log) == 3   # design/205: one log line per answer, by the operator


def test_every_gap_accepted_says_what_is_next_and_nothing_is_left_to_reopen():
    store, conn = start()
    r = record(store, conn, [ans(l, 'accept') for l in page(store, conn)['lines']])
    assert r['open'] == 0 and r['page']['open'] is False and 'vw visuals next' in r['then'] and 'accepted' in r['page']['note']
    assert all(l['state'] == 'recorded' and not l.get('reopen') for l in r['page']['lines'])


def test_a_gap_offered_two_ways_shows_both_and_taking_a_way_accepts_the_gap_in_the_same_answer():
    store, conn = start(H.plan_of(choices_on='G2'))
    p = page(store, conn)
    g = by_key(p)['G2']
    assert [l['key'] for l in p['lines']] == ['G1', 'G2', 'G3'], 'the film\'s order, a choice among the gaps'
    assert [(w['title'], w['recommended'], w['table'][0][1], w['total']) for w in g['ways']] == [('Way a', True, 'Shot G2-S1', '1 shots, 4.0 s in all.'), ('Way b', False, 'Shot G2-S1', '1 shots, 4.0 s in all.')]
    assert g['ways'][0]['rows'] == [['What it is', 'd'], ['Why', 'w'], ['The cost of it', 't']] and g['cols'] == C.GAP_COLS
    assert [(b['label'], b['choice'], b['needs_words']) for b in g['buttons']] == [('Take Way a (advised)', 'way:a', False), ('Take Way b', 'way:b', False), ('Change this', 'change', True)]
    r = record(store, conn, [ans(g, 'way:b')])
    s = H.session(store)
    assert r['recorded'] == ['G2'] and s['choice_selections']['G2']['choice_id'] == 'b' and 'G2' in s['accepted'] and by_key(r['page'])['G2']['state'] == 'recorded'
    store, conn = start(H.plan_of(choices_on='G2'))
    r = record(store, conn, [ans(by_key(page(store, conn))['G2'], 'change', 'neither way')])   # sent back without a way taken
    assert r['recorded'] == ['G2'] and by_key(r['page'])['G2']['state'] == 'with_assistant' and not H.session(store)['choice_selections']
    assert record(store, conn, [ans(g, 'way:a')])['stale'] == ['G2'], 'G2 is with the assistant now: its question is not open'


def test_an_answer_that_is_not_one_of_the_lines_answers_is_refused_on_its_line_and_the_others_are_recorded():
    store, conn = start(H.plan_of(choices_on='G2'))
    p = page(store, conn)
    r = record(store, conn, [ans(by_key(p)['G2'], 'way:zz'), ans(by_key(p)['G1'], 'change', ''), ans(by_key(p)['G3'], 'accept')])
    assert r['recorded'] == ['G3'] and sorted(x['key'] for x in r['refused']) == ['G1', 'G2']
    now = by_key(r['page'])
    assert 'Not an answer to this line' in now['G2']['refused'] and 'your own words' in now['G1']['refused'] and now['G1']['state'] == 'open'


def test_an_answer_to_an_older_text_of_a_gap_is_stale_and_the_gap_is_asked_again_with_what_changed():
    store, conn = start()
    p = page(store, conn)
    record(store, conn, [ans(p['lines'][0], 'accept')])
    old = ans(p['lines'][1], 'accept')
    H.propose(store, H.plan_of(purposes={'G1': 'It shows the gate', 'G2': 'It shows the yard'}))
    r = record(store, conn, [old])
    assert r['stale'] == ['G2'] and r['recorded'] == [] and 'G2' not in H.session(store)['accepted']
    g1 = by_key(r['page'])['G1']
    assert g1['state'] == 'open' and g1['changed'] is True and any('gate' in c for c in g1['changes']) and g1['title'] == 'Gap G1 · Title 1'
    assert record(store, conn, [ans(g1, 'accept'), ans(g1, 'accept')])['stale'] == ['G1'], 'answered twice: the second is stale'


def test_the_shared_rules_are_one_line_first_and_its_yes_accepts_every_gap_behind_it():
    store, conn = start()
    record(store, conn, [ans(l, 'accept') for l in page(store, conn)['lines'][:2]])
    H.propose(store, H.plan_of(foundation='warm and close'))
    p = page(store, conn)
    sh = p['lines'][0]
    assert [l['key'] for l in p['lines']] == ['shared', 'G3'] and sh['title'] == "The film's shared rules changed" and sh['item'].startswith('shared:')
    assert any('warm and close' in c for c in sh['changes']) and sh['waits'] == ['G1', 'G2'] and 'G1, G2' in sh['text']
    r = record(store, conn, [ans(p['lines'][1], 'accept'), ans(sh, 'accept')])   # sent in any order: the shared rules are recorded first
    assert r['recorded'] == ['shared', 'G3'] and set(H.session(store)['accepted']) == {'G1', 'G2', 'G3'} and r['page']['open'] is False


def test_a_change_asked_in_the_shared_rules_keeps_the_gap_answers_given_beside_it():
    store, conn = start()
    record(store, conn, [ans(l, 'accept') for l in page(store, conn)['lines'][:2]])
    H.propose(store, H.plan_of(foundation='warm and close'))
    p = page(store, conn)
    r = record(store, conn, [ans(p['lines'][0], 'change', 'keep it calm'), ans(p['lines'][1], 'accept')])
    assert r['recorded'] == ['shared', 'G3'] and r['dropped'] == [] and 'G3' in H.session(store)['accepted']
    sh = r['page']['lines'][0]
    assert sh['key'] == 'shared' and sh['state'] == 'with_assistant' and sh['note'] == 'keep it calm' and sh['waits'] == ['G1', 'G2']


def test_an_accepted_gap_is_reopened_with_the_operators_words_while_the_plan_is_open():
    store, conn = start()
    r = record(store, conn, [ans(page(store, conn)['lines'][0], 'accept')])
    g1 = by_key(r['page'])['G1']
    assert g1['reopen'] is True
    assert record(store, conn, [ans(g1, 'reopen', '')])['refused'][0]['key'] == 'G1'
    r = record(store, conn, [ans(g1, 'reopen', 'the wall is too far')])
    assert r['recorded'] == ['G1'] and 'G1' not in H.session(store)['accepted'] and by_key(r['page'])['G1']['note'] == 'the wall is too far'
    assert record(store, conn, [ans(g1, 'reopen', 'again')])['stale'] == ['G1']


def test_nothing_answered_records_nothing_and_says_so():
    store, conn = start()
    r = record(store, conn, [])
    assert r['recorded'] == [] and r['open'] == 3 and r['then'].startswith('Nothing was answered on the page.') and '3 line(s) still wait' in r['then'] and r['log'] == 'nothing answered'


def test_forty_gaps_fit_one_round_and_no_plan_yet_says_so():
    plan = H.plan_of(40)
    for g in plan['gaps']:
        g['scenes'][0]['shots'] = [dict(H.shot(f"{g['gap_id']}-S{n}", 'x' * 300), narration='y' * 400) for n in range(1, 9)]
    store, conn = start(plan)
    p = page(store, conn)
    assert len(p['lines'][0]['table']) == 8 and len(p['lines'][0]['table'][0][5]) == 220
    shown = len(p['lines'])
    assert 1 < shown < 40 and [l['key'] for l in p['lines']] == [f'G{n}' for n in range(1, shown + 1)], 'the first gaps, in the film\'s order'
    assert len(json.dumps(p, ensure_ascii=False).encode('utf-8')) < 256 * 1024, 'one document of the page\'s database holds at most 256 KiB'
    assert f'{40 - shown} more gap(s) appear here after you answer these' in p['note'] and f'{40 - shown} more after these' in p['summary']
    r = record(store, conn, [ans(l, 'accept') for l in p['lines']])   # the rest come on the next round, the answered ones recorded
    assert len(r['recorded']) == shown and r['open'] > 0 and r['page']['lines'][0]['state'] == 'recorded' and 'still wait' in r['then']
    small = page(*start(H.plan_of(16)))
    assert len(small['lines']) == 16 and 'more' not in small['note'], 'a usual plan is one round'
    store = H.Store()
    H.fresh(store)
    p = P.page(H.Conn(), store, H.USER, H.RUN, {})
    assert p['step'] == 'Treatment' and p['open'] is False and 'recorded' in p['note'], 'a recorded treatment with no plan yet: as before'


def test_the_treatment_page_is_untouched_by_the_plan_lines():
    import inspect
    src = inspect.getsource(P.page)
    assert "_plan_page(" in src and "CF._treatment_items(ctx)" in src
    assert copy.deepcopy(P.CAPABILITIES) == {'db': {'rules': [{'path': 'rounds', 'read': 'view', 'write': 'owner'}]}, 'user': {}}
