"""design/210 part 2 (SK, 16 Nov 2026): the reference round on the Claude artifact page, in two screens. "References": every person, object and
place of the round in one visit, each with its footage pictures, the chat item's own buttons, the price on every button that makes a set, a
comment box and "Use my own picture"; one `round_done` once every thing is answered. "References: the sets": every set that is back with its
three pictures, each alone (a thing's set chosen on the picture or by its button), the sets not made with their cause, the sets being made and
the approved ones. Each answer goes through the chat item's own run function, so the chat ends in the same state. Without a database."""
import copy
import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

from app import chat_flow as CF, page_flow as P, visuals_stage as VS
from test_design151_refs_pure import KILN, MASON, NEW, doc_with, new_store
from test_visuals_stage_pure import FakeConn, USER, accepted, ref, saved

A, B = 'References', 'References: the sets'


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})
    P._MADE.clear()


def png(colour='white'):
    out = io.BytesIO()
    Image.new('RGB', (64, 48), colour).save(out, 'PNG')
    return out.getvalue()


ROWS = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'P1', 'prompt': 'kneels all day'}]


def film(doc=None, frames=('F1',), rows=ROWS, begin=True):
    """A film whose plan is accepted, with the footage pictures of E1 in the store; the reference round started when `begin`."""
    doc = doc or doc_with(KILN, MASON)
    refs = {f: {**ref(f), 'kind': 'frame', 'element_id': 'E1', 'width': 1920, 'height': 1080} for f in frames}
    store = new_store(doc, refs, accepted=accepted(doc))
    for f in frames:
        store.files[CF._ref_key(NEW, f)] = png()
    conn = FakeConn([])
    if begin:
        VS.round_start(store, USER, NEW, [], rows, conn=conn)
    return store, conn


def page(store, conn):
    return P.page(conn, store, USER, NEW, [])


def record(store, conn, answers):
    return P.page_record(conn, store, USER, NEW, [], answers)


def ans(line, choice, notes='', **more):
    return {'line': line['line'], 'key': line['key'], 'item': line.get('item', ''), 'choice': choice, 'notes': notes, **more}


def by(p):
    return {l['key']: l for l in p['lines']}


def price(store, conn):
    return VS._set_budget(NEW, saved(store), VS.visuals_spend(conn, NEW))[2]


def paid(store, conn):
    return f'paid, about ₹{price(store, conn):,.0f}'


def back(store, counts=None):
    """What the image worker writes when the sets come back: three pictures each, in the store."""
    s = saved(store)
    for r in list(s['references'].values()):
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            r.update(status='candidate', sha256='sha-' + r['id'], key=CF._ref_key(NEW, r['id']))
            store.files[r['key']] = png('red')
            for k in range(2, (counts or {}).get(r['element_id'], 3) + 1):
                s['references'][f"{r['id']}-{k}"] = {**r, 'id': f"{r['id']}-{k}", 'set_n': k, 'sha256': f"sha-{r['id']}-{k}", 'key': CF._ref_key(NEW, f"{r['id']}-{k}")}
                store.files[CF._ref_key(NEW, f"{r['id']}-{k}")] = png('blue')
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')


def step1(store, conn, **verdicts):
    """Every thing of step 1 answered on the page and done said: E1 from its footage, E2 and P1 a set each."""
    p = by(page(store, conn))
    return record(store, conn, [ans(p[f'ref:{e}'], verdicts.get(e, 'approve')) for e in ('E1', 'E2', 'P1')])


def at_sets(**verdicts):
    store, conn = film()
    step1(store, conn, **verdicts)
    back(store)
    return store, conn


def logged(conn):
    return [json.dumps(p, default=str, ensure_ascii=False) for sql, p in conn.sql if 'vw2_log' in sql]


# ---------- the step order ----------

def test_with_no_round_yet_the_page_says_what_the_assistant_does():
    store, conn = film(begin=False)
    p = page(store, conn)
    assert p['step'] not in (A, B) and p['open'] is False
    assert p['then'] == P.REFS_START and '`vw visuals digest`' in p['then'] and '`vw visuals look`' in p['then']   # design/211: the footage is searched first (was: the round file, then the page)


def test_the_references_come_after_the_plan_and_an_open_gap_holds_them_back():
    store, conn = film()
    assert page(store, conn)['step'] == A
    s = saved(store)
    s['accepted'].pop('G1')
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    assert page(store, conn)['step'] == 'Plan'


# ---------- screen A: the things ----------

def test_every_thing_is_on_the_page_at_once_with_its_footage_pictures_and_the_chats_own_buttons():
    store, conn = film(frames=('F1', 'F2', 'F3', 'F4', 'F5'), rows=[{'element_id': 'E1', 'frames': ['F1', 'F2', 'F3', 'F4', 'F5'], 'prompt': 'the plinth top'}] + ROWS[1:])
    p = page(store, conn)
    l = by(p)
    assert p['step'] == A and p['open'] is True and [x['key'] for x in p['lines']] == ['ref:E1', 'ref:E2', 'ref:P1'] and [x['line'] for x in p['lines']] == ['l01', 'l02', 'l03']
    assert [x['title'] for x in p['lines']] == ['Plinth (an object)', 'Clamp kiln (a place)', 'Mason (a person)']
    assert [x['item'] for x in p['lines']] == ['round1:E1', 'round1:E2', 'round1:P1'] and all(x['state'] == 'open' and x['comment'] is True for x in p['lines'])
    assert len(l['ref:E1']['pics']) == 4 and [x['label'] for x in l['ref:E1']['pics']] == ['Footage picture 1', 'Footage picture 2', 'Footage picture 3', 'Footage picture 4']   # up to four, as the chat shows
    assert l['ref:E1']['pics'][0]['code'] == P.pic_code(CF._ref_key(NEW, 'F1'), saved(store)['references']['F1']['sha256']) and len(p['pictures']) == 4
    assert l['ref:E1']['buttons'] == [{'label': 'Yes, use it', 'choice': 'approve', 'needs_words': False}, {'label': 'No reference needed', 'choice': 'ignore', 'needs_words': False}]   # design/216 (B6): was 'Leave it out'
    assert 'nothing is paid' in l['ref:E1']['text'] and l['ref:E1']['ask'] == 'Use this picture from your footage as the reference?'
    assert 'pics' not in l['ref:E2'] and l['ref:E2']['buttons'][0] == {'label': f'Yes, make one ({paid(store, conn)})', 'choice': 'approve', 'needs_words': False}
    assert l['ref:E2']['buttons'][1]['label'] == 'No reference needed' and 'no picture of it' in l['ref:E2']['text']
    chat = CF._round_items(CF._ctx(conn, store, USER, NEW, []))
    assert [i['id'] for i in chat] == ['round1:E1'] and [b['label'] for b in chat[0]['buttons']] == ['Yes, use it', 'No reference needed']   # the chat still asks one at a time
    assert len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) < P.ROUND_BYTES and '_' not in ''.join(k[0] for x in p['lines'] for k in x)


def test_a_thing_with_one_footage_picture_shows_it():
    store, conn = film()
    assert [x['label'] for x in by(page(store, conn))['ref:E1']['pics']] == ['Footage picture 1']


def test_a_person_gets_a_set_even_with_footage_and_the_line_says_so_with_the_price_and_the_permission():
    doc = doc_with(KILN, MASON)
    store = new_store(doc, {'F9': {**ref('F9'), 'kind': 'frame', 'element_id': 'P1'}}, accepted=accepted(doc))
    store.files[CF._ref_key(NEW, 'F9')] = png()
    conn = FakeConn([])
    VS.round_start(store, USER, NEW, [], ROWS[1:], conn=conn)
    l = by(page(store, conn))['ref:P1']
    assert len(l['pics']) == 1 and l['buttons'][0]['label'] == f'Yes, use it ({paid(store, conn)})' and 'even with footage' in l['text'] and 'every person' in l['text']
    assert l['own']['person'] is True and l['own']['permitted'] is False and 'permission' in l['own']['text'] and paid(store, conn) in l['own']['label']
    assert by(page(store, conn))['ref:E2']['own'] == {'label': 'Use my own picture', 'person': False, 'permitted': True, 'text': by(page(store, conn))['ref:E2']['own']['text']}
    VS.likeness(store, USER, NEW, [], 'P1', 'He signed the release.', conn=conn)
    assert by(page(store, conn))['ref:P1']['own']['permitted'] is True


def test_a_thing_with_approved_drawings_gets_a_set_even_with_footage_and_says_so():
    store, conn = film()
    s = saved(store)
    s['drawings'] = {'E1': {'status': 'approved', 'sha256': 'a' * 64, 'views': []}}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    l = by(page(store, conn))['ref:E1']
    assert l['buttons'][0]['label'] == f'Yes, use it ({paid(store, conn)})' and 'drawings' in l['text'] and 'even with footage' in l['text']


def test_the_top_of_the_page_gives_the_bounds_the_server_knows():
    store, conn = film()
    p = page(store, conn)
    spent, cap, one = VS._set_budget(NEW, saved(store), VS.visuals_spend(conn, NEW))
    assert p['summary'] == f'3 things: 3 to answer, 0 kept; up to 2 sets, about ₹{2 * one:,.0f}, of the ₹{cap:,.0f} limit; spent so far ₹{spent:,.0f}.'
    assert 'say done' in p['note']


def test_every_thing_answered_is_one_round_done_and_the_sets_are_being_made():
    store, conn = film()
    r = step1(store, conn, E1='approve')
    s = saved(store)
    assert r['recorded'] == ['ref:E1', 'ref:E2', 'ref:P1'] and r['kept'] == [] and r['refused'] == [] and r['open'] == 0
    assert s['round']['pass'] == 'making' and 'chat_round' not in s and len(conn.inserted) == 2 and s['round']['elements']['E1']['from_footage'] is True
    assert s['references']['F1']['status'] == 'approved' and s['round']['quote'] == 'Done, on the page'
    now = r['page']
    assert now['step'] == B and [(l['key'], l['state']) for l in now['lines']] == [('set:E2', 'making'), ('set:P1', 'making')] and now['lines'][0]['note'] == 'Its set is being made.'
    assert r['then'].endswith(P.SETS_WAIT) and '2 reference set(s) are now being made' in r['then'] and '`vw visuals status --wait 900`' in r['then'] and '`vw visuals page`' in r['then']
    said = logged(conn)
    assert len(said) == 3 and 'Yes, use it' in said[0] and f'Yes, make one ({paid(store, conn)})' in said[1] and 'line ref:E2, choice approve' in said[1]   # the button, with its price, is the operator's word


def test_done_with_some_unanswered_keeps_the_answers_and_records_and_queues_nothing():
    store, conn = film()
    p = by(page(store, conn))
    r = record(store, conn, [ans(p['ref:E2'], 'approve'), ans(p['ref:P1'], 'ignore')])
    s = saved(store)
    assert r['kept'] == ['ref:E2', 'ref:P1'] and r['recorded'] == [] and r['open'] == 1 and s['round']['pass'] == 1 and conn.inserted == []
    assert s['round']['elements']['E2']['verdict'] is None and s['references']['F1']['status'] == 'candidate'
    now = by(r['page'])
    assert r['page']['step'] == A and now['ref:E1']['state'] == 'open' and 'kept' not in now['ref:E1']
    assert now['ref:E2']['kept'] == f'Yes, make one ({paid(store, conn)})' and now['ref:P1']['kept'] == 'No reference needed' and now['ref:E2']['kept_note'] == P.REFS_KEPT
    assert 'the sets are made when every thing is answered' in P.REFS_KEPT and now['ref:E2']['state'] == 'open' and now['ref:E2']['buttons']   # it can still be changed
    assert '1 to answer, 2 kept' in r['page']['summary'] and '1 thing(s) still wait' in r['then'] and 'nothing is made' in r['then']


def test_an_answer_changed_before_the_last_one_is_the_one_recorded():
    store, conn = film()
    p = by(page(store, conn))
    record(store, conn, [ans(p['ref:E2'], 'approve')])
    r = record(store, conn, [ans(p['ref:E2'], 'ignore'), ans(p['ref:P1'], 'approve'), ans(p['ref:E1'], 'approve')])
    s = saved(store)
    assert s['round']['elements']['E2']['ignored'] is True and len(conn.inserted) == 1 and sorted(r['recorded']) == ['ref:E1', 'ref:E2', 'ref:P1']
    assert [l['key'] for l in r['page']['lines']] == ['set:P1']


def test_done_with_nothing_answered_records_nothing():
    store, conn = film()
    r = record(store, conn, [])
    assert r['recorded'] == [] and r['kept'] == [] and r['log'] == 'nothing answered' and r['then'].startswith('Nothing was answered on the page. 3 thing(s) still wait') and saved(store)['round']['pass'] == 1


def test_an_answer_to_a_thing_that_left_the_round_is_stale_and_a_wrong_choice_is_refused_on_its_line():
    store, conn = film()
    p = by(page(store, conn))
    r = record(store, conn, [{**ans(p['ref:E2'], 'approve'), 'item': 'round1:E9'}, ans(p['ref:P1'], 'maybe')])
    assert r['stale'] == ['ref:E2'] and [x['key'] for x in r['refused']] == ['ref:P1'] and 'Yes, make one' in r['refused'][0]['message'] and 'chat_round' not in saved(store)
    assert by(r['page'])['ref:P1']['refused'] == r['refused'][0]['message']


def test_the_comment_is_kept_in_the_answers_log_line():
    store, conn = film()
    p = by(page(store, conn))
    record(store, conn, [ans(p['ref:E2'], 'approve', '  the  kiln at dusk, with smoke ')])
    assert 'the kiln at dusk, with smoke' in logged(conn)[0] and 'Yes, make one' in logged(conn)[0]


def test_a_drawing_still_open_holds_the_round_with_the_servers_sentence_and_its_approval_lets_it_go():
    store, conn = film()
    p = by(page(store, conn))
    s = saved(store)
    s['drawings'] = {'E2': {'status': 'proposed', 'sha256': 'b' * 64, 'name': 'Clamp kiln', 'views': [], 'facts': [], 'assumed': []}}   # sent while the operator was on the page
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    r = record(store, conn, [ans(p[k], 'approve') for k in ('ref:E1', 'ref:E2', 'ref:P1')])
    assert r['kept'] == ['ref:E1', 'ref:E2', 'ref:P1'] and r['recorded'] == [] and conn.inserted == [] and saved(store)['round']['pass'] == 1
    assert [x['key'] for x in r['refused']] == ['references'] and 'reference drawings of E2 are not approved yet' in r['refused'][0]['message']
    assert r['page']['step'] == P.DRAW_STEP and r['refused'][0]['message'] in r['then']
    r = record(store, conn, [ans(r['page']['lines'][0], 'yes')])
    assert r['recorded'][0] == 'drawing:E2' and saved(store)['round']['pass'] == 'making' and len(conn.inserted) == 2 and r['page']['step'] == B and r['then'].endswith(P.SETS_WAIT)


def test_a_limit_too_low_for_the_sets_refuses_the_whole_step_and_queues_nothing():
    store, conn = film()
    s = saved(store)
    s['cap_inr'] = price(store, conn) * 1.5   # room for one set, two are asked for
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    r = step1(store, conn)
    now = saved(store)
    assert r['recorded'] == [] and conn.inserted == [] and now['round']['pass'] == 1 and len(now['chat_round']) == 3 and now['references']['F1']['status'] == 'candidate'
    msg = r['refused'][0]['message']
    assert r['refused'][0]['key'] == 'references' and '2 sets' in msg and 'limit' in msg and 'Nothing was made' in msg and 'owner' in msg
    assert r['page']['step'] == A and r['page']['note'].startswith('Not recorded: ' + msg) and msg in r['then'] and all(l['kept'] for l in r['page']['lines'])
    r = record(store, conn, [ans(by(r['page'])['ref:E2'], 'ignore')])   # one set fewer: it fits now
    assert saved(store)['round']['pass'] == 'making' and len(conn.inserted) == 1 and 'refused' not in json.dumps(r['page']['lines'])


def test_sixty_things_are_held_under_the_size_of_one_round_and_recorded_only_after_the_last(monkeypatch):
    doc = doc_with()
    doc['elements'] += [{'id': f'T{i:02d}', 'name': f'Thing {i}', 'kind': 'object', 'identity': 'representative', 'requirements': 'a thing'} for i in range(1, 60)]
    rows = [{'element_id': e['id'], 'prompt': 'what it is'} for e in doc['elements']]
    store, conn = film(doc, rows=rows)
    p = page(store, conn)
    assert len(p['lines']) == 60 and len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) <= P.ROUND_BYTES
    monkeypatch.setattr(P, 'ROUND_BYTES', 12000)
    p = page(store, conn)
    held = 60 - len(p['lines'])
    assert 0 < held < 60 and len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) <= 12000 and f'{held} more' in p['summary']
    assert f'{held} more' in p['note'] and 'after the last' in p['note']
    seen, rounds = set(), 0
    while saved(store)['round']['pass'] == 1 and rounds < 20:
        p = page(store, conn)
        todo = [l for l in p['lines'] if not l.get('kept')]
        assert todo and not seen & {l['key'] for l in todo}
        seen |= {l['key'] for l in todo}
        r = record(store, conn, [ans(l, 'ignore') for l in todo])
        rounds += 1
        assert conn.inserted == [] and (len(seen) == 60 or (r['recorded'] == [] and saved(store)['round']['pass'] == 1))
    assert len(seen) == 60 and rounds > 1 and saved(store)['round']['pass'] == 'complete' and len(r['recorded']) == 60


def test_the_chat_path_one_at_a_time_ends_in_the_same_state_as_the_page():
    store, conn = film()
    step1(store, conn)
    other, conn2 = film()
    for _ in range(3):
        item = CF._round_items(CF._ctx(conn2, other, USER, NEW, []))[0]
        item['_run']('approve', item['buttons'][0]['label'], '')
    a, b = saved(store)['round'], saved(other)['round']
    assert a['pass'] == b['pass'] == 'making' and len(conn.inserted) == len(conn2.inserted) == 2
    assert {e: (r['verdict'], r.get('ignored'), bool(r.get('set')), r.get('from_footage')) for e, r in a['elements'].items()} == {e: (r['verdict'], r.get('ignored'), bool(r.get('set')), r.get('from_footage')) for e, r in b['elements'].items()}


# ---------- screen B: the sets ----------

def test_a_persons_set_shows_its_three_pictures_alone_and_asks_yes_no_or_correct_it():
    store, conn = at_sets()
    p = page(store, conn)
    l = by(p)['set:P1']
    rows = sorted(s['id'] for s in saved(store)['references'].values() if s.get('kind') == 'sheet' and s['element_id'] == 'P1')
    assert p['step'] == B and [x['key'] for x in p['lines']] == ['set:E2', 'set:P1'] and l['title'] == 'Mason (a person)' and l['item'] == f"set:P1:{rows[0]}"
    assert [x['label'] for x in l['pics']] == ['A', 'B', 'C'] and [x['code'] for x in l['pics']] == [P.pic_code(CF._ref_key(NEW, r), saved(store)['references'][r]['sha256']) for r in rows] and not any('choice' in x for x in l['pics'])
    cost = paid(store, conn)
    assert l['buttons'] == [{'label': 'Yes', 'choice': 'yes', 'needs_words': False}, {'label': f'No ({cost}: the set is made again)', 'choice': 'no', 'needs_words': False},
                            {'label': f'Correct it ({cost}: the set is made again)', 'choice': 'correct', 'needs_words': True}]
    assert l['ask'] == 'is this set right for this person?' or l['ask'] == 'Is this set right for this person?'
    assert len(p['pictures']) == 6 and 'side-by-side' not in json.dumps(p) and '2 sets: 2 to answer' in p['summary']
    r = record(store, conn, [ans(l, 'yes')])
    s = saved(store)
    assert r['recorded'] == ['set:P1'] and s['round']['elements']['P1']['verdict'] == 'yes' and s['golden']['P1'] == rows[0] and s['round']['pass'] == 2
    now = by(r['page'])['set:P1']
    assert now['state'] == 'recorded' and len(now['pics']) == 3 and 'buttons' not in now and '1 line(s) still wait' in r['then']   # an approved set keeps its pictures


@pytest.mark.parametrize('letter', [0, 1, 2])
def test_use_a_b_or_c_is_yes_with_that_picture_as_the_starting_picture(letter):
    store, conn = at_sets()
    l = by(page(store, conn))['set:E2']
    rows = sorted(s['id'] for s in saved(store)['references'].values() if s.get('kind') == 'sheet' and s['element_id'] == 'E2')
    assert [b['label'] for b in l['buttons'][:3]] == ['Use A', 'Use B', 'Use C'] and [b['choice'] for b in l['buttons'][:3]] == ['use:' + r for r in rows]
    assert [x.get('choice') for x in l['pics']] == ['use:' + r for r in rows]   # the same choice sits on the picture itself
    assert [b['choice'] for b in l['buttons'][3:]] == ['no', 'correct'] and l['buttons'][3]['label'].startswith('None of these (paid, about ₹') and l['buttons'][4]['needs_words'] is True
    r = record(store, conn, [ans(l, l['pics'][letter]['choice'])])
    s = saved(store)
    assert r['recorded'] == ['set:E2'] and s['golden']['E2'] == rows[letter] and all(s['references'][x]['status'] == 'approved' for x in rows)
    now = by(r['page'])['set:E2']
    assert now['state'] == 'recorded' and [x['label'] for x in now['pics']] == [('ABC'[i] + (' (the starting picture)' if i == letter else '')) for i in range(3)]


def test_none_of_these_and_correct_it_make_the_set_again_and_correct_it_needs_words():
    store, conn = at_sets()
    p = by(page(store, conn))
    r = record(store, conn, [ans(p['set:E2'], 'correct', '')])
    assert [x['key'] for x in r['refused']] == ['set:E2'] and 'your own words' in r['refused'][0]['message'] and r['recorded'] == [] and len(conn.inserted) == 2
    now = by(r['page'])
    assert now['set:E2']['state'] == 'open' and now['set:E2']['refused'] and P.ROUND_REFUSED in r['then']
    r = record(store, conn, [ans(now['set:E2'], 'correct', 'the chimney is  too short')])
    s = saved(store)
    assert r['recorded'] == ['set:E2'] and s['round']['elements']['E2']['corrections'] == ['the chimney is too short'] and len(conn.inserted) == 3 and s['round']['pass'] == 'making'
    assert [(l['key'], l['state']) for l in r['page']['lines']] == [('set:E2', 'making'), ('set:P1', 'open')] and '1 line(s) still wait' in r['then']
    assert 'the chimney is too short' in logged(conn)[-1] and 'Correct it (paid, about' in logged(conn)[-1]
    r = record(store, conn, [ans(by(r['page'])['set:P1'], 'no')])   # while E2 is being made again. VW-25 issue 13: recorded at once (the older way, kept until E2 is back, is retired)
    assert r['recorded'] == ['set:P1'] and r['kept'] == [] and len(conn.inserted) == 4 and r['page']['open'] is False and r['then'].endswith(P.SETS_WAIT)   # None of these: made again, with no words
    assert [(l['key'], l['state']) for l in r['page']['lines']] == [('set:E2', 'making'), ('set:P1', 'making')]
    back(store)
    now = by(page(store, conn))
    assert len(conn.inserted) == 4 and now['set:P1']['state'] == 'open' and now['set:E2']['state'] == 'open'


def test_an_answer_to_a_set_made_again_meanwhile_is_refused_by_name():
    store, conn = at_sets()
    old = by(page(store, conn))['set:E2']
    record(store, conn, [ans(old, 'no')])
    back(store)
    r = record(store, conn, [ans(old, old['pics'][0]['choice'])])
    # VW-25 issue 13: named with its reason (the older way, a silent "stale", is retired for a set's answer)
    assert [x['key'] for x in r['refused']] == ['set:E2'] and 'made again after this answer was given' in r['refused'][0]['message'] and r['stale'] == []
    assert r['recorded'] == [] and saved(store)['round']['elements']['E2']['verdict'] == 'no'
    assert by(r['page'])['set:E2']['item'] != old['item'] and by(r['page'])['set:E2']['state'] == 'open'


def not_made(cap=False):
    """E2's set was refused before it was made; with `cap`, the limit leaves no room for one more."""
    store, conn = at_sets()
    s = saved(store)
    row = s['round']['elements']['E2']
    for rid in [k for k, v in s['references'].items() if v.get('kind') == 'sheet' and v['element_id'] == 'E2']:
        s['references'].pop(rid)
    row.update(set=None, error='the picture service refused the request')
    if cap:
        s['cap_inr'] = 1.0
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    return store, conn


def test_a_set_that_was_not_made_is_made_now_or_left_out():
    store, conn = not_made()
    l = by(page(store, conn))['set:E2']
    assert l['item'] == 'setmake:E2' and l['state'] == 'open' and 'pics' not in l and 'was not made' in l['text']
    assert [b['label'] for b in l['buttons']] == [f'Make it ({paid(store, conn)})', 'Go on without a reference']
    n = len(conn.inserted)
    r = record(store, conn, [ans(l, 'make')])
    assert r['recorded'] == ['set:E2'] and len(conn.inserted) == n + 1 and by(r['page'])['set:E2']['state'] == 'making'
    store, conn = not_made()
    r = record(store, conn, [ans(by(page(store, conn))['set:E2'], 'aside', 'we do not need it')])
    s = saved(store)
    assert r['recorded'] == ['set:E2'] and s['round']['elements']['E2']['aside']['words'] == 'we do not need it' and 'set:E2' not in by(r['page'])


def test_a_set_the_limit_holds_says_its_cause_and_make_it_is_refused_on_its_line():
    store, conn = not_made(cap=True)
    l = by(page(store, conn))['set:E2']
    assert 'the spend cap is reached' in l['text'] and [b['choice'] for b in l['buttons']] == ['make', 'aside']
    n = len(conn.inserted)
    r = record(store, conn, [ans(l, 'make')])
    assert r['recorded'] == [] and len(conn.inserted) == n and 'the spend cap is reached' in r['refused'][0]['message'] and by(r['page'])['set:E2']['refused']
    assert [i['id'] for i in CF._round_items(CF._ctx(conn, store, USER, NEW, []))] == [f"set:P1:{saved(store)['round']['elements']['P1']['set']}"]   # the chat still leaves it for its own turn


def test_a_remake_the_limit_holds_stays_open_with_the_servers_sentence():
    store, conn = at_sets()
    s = saved(store)
    s['cap_inr'] = 1.0
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    p = by(page(store, conn))
    n = len(conn.inserted)
    r = record(store, conn, [ans(p['set:P1'], 'no'), ans(p['set:E2'], p['set:E2']['pics'][1]['choice'])])
    now = by(r['page'])
    assert r['recorded'] == ['set:E2'] and len(conn.inserted) == n and [x['key'] for x in r['refused']] == ['set:P1'] and 'spend cap of ₹1 is reached' in r['refused'][0]['message']
    assert now['set:P1']['state'] == 'open' and now['set:P1']['refused'] == r['refused'][0]['message'] and now['set:P1']['kept'].startswith('No (') and now['set:E2']['state'] == 'recorded'
    assert saved(store)['round']['elements']['P1']['answer']['verdict'] == 'no' and saved(store)['round']['pass'] == 2


def test_an_answer_on_a_set_that_is_back_is_recorded_while_another_set_is_still_being_made():   # VW-25 issue 13 (the older way, kept until every set is back, is retired)
    store, conn = film()
    step1(store, conn)
    s = saved(store)
    first = next(r for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == 'E2')
    first.update(status='candidate', sha256='sha', key=CF._ref_key(NEW, first['id']))   # E2 is back, P1 is still being made
    store.files[first['key']] = png()
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    p = page(store, conn)
    assert [(l['key'], l['state']) for l in p['lines']] == [('set:E2', 'open'), ('set:P1', 'making')] and '1 to answer' in p['summary'] and '1 being made' in p['summary']
    r = record(store, conn, [ans(p['lines'][0], p['lines'][0]['pics'][0]['choice'])])
    now = by(r['page'])['set:E2']
    assert r['recorded'] == ['set:E2'] and r['kept'] == [] and now['state'] == 'recorded' and 'kept' not in now and saved(store)['round']['elements']['E2']['verdict'] == 'yes'
    assert r['then'].endswith(P.SETS_WAIT) and saved(store)['round']['pass'] == 'making'   # the round stays open for the set being made
    back(store)
    p = page(store, conn)
    assert by(p)['set:E2']['state'] == 'recorded' and by(p)['set:P1']['state'] == 'open' and VS._round_pass(saved(store), saved(store)['round']) == 2


def test_the_round_complete_goes_on_with_vw_visuals_next():
    store, conn = at_sets()
    p = by(page(store, conn))
    r = record(store, conn, [ans(p['set:P1'], 'yes'), ans(p['set:E2'], p['set:E2']['pics'][2]['choice'])])
    assert saved(store)['round']['pass'] == 'complete' and r['then'] == P.ROUND_NEXT and '`vw visuals next`' in r['then'] and r['page']['step'] not in (A, B) and r['open'] == 0


def test_the_sets_text_stays_under_one_round_and_long_lists_hold_the_later_sets(monkeypatch):
    store, conn = at_sets()
    monkeypatch.setattr(P, 'ROUND_BYTES', 900)
    p = page(store, conn)
    assert len(p['lines']) == 1 and '1 more' in p['summary'] and len(p['pictures']) == 3


# ---------- the operator's own picture ----------

def own(store, conn, eid):
    return VS.supply_own(conn, store, USER, NEW, [], eid, content=png('green'), name='mine.png')['id']


def test_my_own_picture_of_a_thing_at_step_one_is_its_reference_and_no_set_is_made():
    store, conn = film()
    p = by(page(store, conn))
    assert p['ref:E1']['own']['label'] == 'Use my own picture' and p['ref:P1']['own']['label'].startswith('Use my own picture (paid')
    mine = own(store, conn, 'E1')
    r = record(store, conn, [ans(p['ref:E1'], 'own', own_ref=mine), ans(p['ref:E2'], 'ignore'), ans(p['ref:P1'], 'ignore')])
    s = saved(store)
    assert r['recorded'] == ['ref:E1', 'ref:E2', 'ref:P1'] and conn.inserted == [] and s['round']['pass'] == 'complete'
    assert s['golden']['E1'] == mine and s['round']['elements']['E1']['own'] is True and s['references']['F1']['status'] == 'rejected'   # the footage picture is not its reference
    assert 'Use my own picture' in logged(conn)[0]


def test_an_own_picture_that_did_not_arrive_is_said_on_its_line_and_the_rest_is_recorded():
    store, conn = film()
    p = by(page(store, conn))
    r = record(store, conn, [ans(p['ref:E1'], 'own', own_error='the file is larger than 15 MB: choose a smaller one'), ans(p['ref:E2'], 'ignore'), ans(p['ref:P1'], 'own')])
    assert r['kept'] == ['ref:E2'] and [x['key'] for x in r['refused']] == ['ref:E1', 'ref:P1']
    assert r['refused'][0]['message'] == 'Your own picture was not used: the file is larger than 15 MB: choose a smaller one' and by(r['page'])['ref:E1']['refused']
    assert r['refused'][1]['message'] == P.OWN_PERMISSION and 'permission' in P.OWN_PERMISSION and 'box' in P.OWN_PERMISSION   # a person: how to give the permission
    other = own(store, conn, 'E2')
    r = record(store, conn, [ans(by(r['page'])['ref:E1'], 'own', own_ref=other)])   # a picture of another thing
    assert r['refused'][0]['message'] == P.OWN_MISSING and 'chat_round' in saved(store) and 'E1' not in saved(store)['chat_round']


def test_my_own_photo_of_a_person_with_the_permission_recorded_makes_their_set_from_it():
    store, conn = film()
    p = by(page(store, conn))
    VS.likeness(store, USER, NEW, [], 'P1', 'She said yes on the phone.', conn=conn)   # what the tool does first, with the words of the page
    mine = own(store, conn, 'P1')
    r = record(store, conn, [ans(p['ref:P1'], 'own', own_ref=mine), ans(p['ref:E1'], 'approve'), ans(p['ref:E2'], 'ignore')])
    s = saved(store)
    assert sorted(r['recorded']) == ['ref:E1', 'ref:E2', 'ref:P1'] and len(conn.inserted) == 1 and s['round']['elements']['P1']['made']['photo'] == mine


def test_my_own_picture_at_step_two_is_the_starting_picture_of_a_thing_and_remakes_a_persons_set():
    store, conn = at_sets()
    p = by(page(store, conn))
    assert p['set:E2']['own']['label'] == 'Use my own picture' and p['set:P1']['own']['label'].startswith('Use my own picture (paid') and p['set:P1']['own']['person'] is True
    mine = own(store, conn, 'E2')
    r = record(store, conn, [ans(p['set:E2'], 'own', own_ref=mine)])
    s = saved(store)
    assert r['recorded'] == ['set:E2'] and s['golden']['E2'] == mine and s['round']['elements']['E2']['verdict'] == 'yes' and by(r['page'])['set:E2']['state'] == 'recorded'
    VS.likeness(store, USER, NEW, [], 'P1', 'He signed.', conn=conn)
    photo, n = own(store, conn, 'P1'), len(conn.inserted)
    r = record(store, conn, [ans(by(r['page'])['set:P1'], 'own', own_ref=photo)])
    assert r['recorded'] == ['set:P1'] and len(conn.inserted) == n + 1 and saved(store)['round']['elements']['P1']['made']['photo'] == photo and by(r['page'])['set:P1']['state'] == 'making'


def test_my_own_picture_for_a_set_that_was_not_made_is_its_reference():
    store, conn = not_made()
    l = by(page(store, conn))['set:E2']
    mine = own(store, conn, 'E2')   # the server's own-picture path already takes it as the reference
    r = record(store, conn, [ans(l, 'own', own_ref=mine)])
    s = saved(store)
    assert r['recorded'] == ['set:E2'] and s['round']['elements']['E2']['own'] is True and s['golden']['E2'] == mine and 'set:E2' not in by(r['page'])


# ---------- shared ----------

def test_the_reference_drawings_point_to_the_references_when_they_are_next():
    store, conn = film()
    s = saved(store)
    s['drawings'] = {'E2': {'status': 'proposed', 'sha256': 'b' * 64, 'name': 'Clamp kiln', 'views': [], 'facts': [], 'assumed': []}}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    p = page(store, conn)
    assert p['step'] == P.DRAW_STEP
    r = record(store, conn, [ans(p['lines'][0], 'yes')])
    assert r['then'] == 'Every reference drawing is approved. ' + P.REFS_HERE and r['page']['step'] == A   # design/210 wording review: the round is in this answer, so no second `vw visuals page`
    store, conn = film(begin=False)
    s = saved(store)
    s['drawings'] = {'E2': {'status': 'proposed', 'sha256': 'b' * 64, 'name': 'Clamp kiln', 'views': [], 'facts': [], 'assumed': []}}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    r = record(store, conn, [ans(page(store, conn)['lines'][0], 'yes')])
    assert r['then'] == 'Every reference drawing is approved. ' + P.REFS_START


def test_the_page_is_told_how_the_operators_own_picture_is_fetched_and_no_line_names_a_kind_of_film():
    assert 'own_fetch' in P.HOW and 'action "read"' in P.HOW and '`vw visuals page --record` again' in P.HOW
    store, conn = at_sets()
    text = json.dumps([page(store, conn)['lines'], P.REFS_START, P.REFS_GO, P.SETS_WAIT, P.ROUND_NEXT, P.OWN_PERMISSION, P.OWN_MISSING, P.REFS_KEPT, P.SETS_HELD]).lower()
    assert not any(w in text for w in ('building', 'construction', 'brick', 'documentary'))   # the kiln's own name aside, nothing here is tied to one kind of film


def test_the_instructions_send_the_round_to_the_page_and_the_chat_is_the_way_back():
    root = Path(__file__).resolve().parents[2]
    d = json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    part = {p['name']: p['text'] for p in st['parts']}
    assert "The round's two steps are answered on the page too" in st['prompt']
    assert 'The operator answers both steps on the page (`vw visuals page`), each in one visit' in part['picture-search'] and 'No cost is shown or named at the references, on the page, in the chat or in a reason you write' in part['picture-search']   # design/212 (SK, 17 Nov 2026); before: a paid answer showed its price on its button
    assert 'on the page (Upload my own' in part['picture-search'] and '`vw visuals supply`' not in part['picture-search'] and '`vw visuals own`' in part['picture-search']
    assert "every element's set judged on the page" in part['later']
    retired = json.loads((root / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    for old in ('The operator answers both steps in the chat, one at a time', "every element's set judged in the chat, one at a time"):
        assert old in retired and old not in part['picture-search'] and old not in part['later']
    # the design/210 wording review (scripts/d210c_wording_v3.py) changed one of this script's sentences (Done on step 1 is not undone), so "applying twice changes nothing" is
    # checked on the last script, in test_design210_wording_pure.py; scripts/c1_split_v3.py --check still builds the text through every script in order
    vw = (root / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'the operator answers both steps on the page (`vw visuals page`), each in one visit' in vw and 'the operator answers both steps in the chat, one at a time (`vw visuals next`);' not in vw
