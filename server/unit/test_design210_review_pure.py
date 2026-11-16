"""design/210, the review's five findings (16 Nov 2026), the server's side. 1: step 2 of the reference round ends when its last answer is
"Leave it out" or the operator's own picture, on the page and in the chat alike. 2: on the page, "No" or "None of these" given with words
makes the set again with those words. 3: the way out when pictures did not reach the page is named to the assistant. 5: the two sizes of a
page's pictures are made several at a time. Without a database: the harnesses of test_design210b_pure.py and test_design210_pure.py."""
import json
import threading

import pytest

from app import chat_flow as CF, page_flow as P, visuals_stage as VS
from test_design210_pure import H, png as picture
from test_design210b_pure import A, B, USER, NEW, ans, at_sets, back, by, logged, not_made, own, page, record, saved


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})
    P._MADE.clear()


def at(store):
    s = saved(store)
    return VS._round_pass(s, s['round'])


def ended(store, r):
    """The round is complete and the assistant is told to go on; nothing is said to be kept."""
    assert saved(store)['round']['pass'] == 'complete'
    assert r['then'] == P.ROUND_NEXT and r['page']['step'] not in (A, B) and r['open'] == 0 and r['kept'] == []


# ---------- fix 1: the last answer of step 2 ends the round ----------

def test_leave_it_out_after_the_yes_ends_the_round():
    store, conn = not_made()
    p = by(page(store, conn))
    r = record(store, conn, [ans(p['set:P1'], 'yes')])
    assert at(store) == 2 and '1 line(s) still wait' in r['then']
    r = record(store, conn, [ans(by(r['page'])['set:E2'], 'aside', 'we do not need it')])
    assert r['recorded'] == ['set:E2']
    ended(store, r)
    later = page(store, conn)   # every later visit: not the sets with no line
    assert later['step'] not in (A, B) and saved(store)['round']['pass'] == 'complete'


def test_the_yes_and_leave_it_out_in_one_visit_end_the_round_in_either_order():
    for order in (('set:P1', 'set:E2'), ('set:E2', 'set:P1')):
        store, conn = not_made()
        p = by(page(store, conn))
        r = record(store, conn, [ans(p[k], 'yes' if k == 'set:P1' else 'aside') for k in order])
        assert sorted(r['recorded']) == ['set:E2', 'set:P1'], order
        ended(store, r)


def test_leave_it_out_first_and_the_yes_later_ends_the_round_as_before():
    store, conn = not_made()
    r = record(store, conn, [ans(by(page(store, conn))['set:E2'], 'aside')])
    assert at(store) == 2
    r = record(store, conn, [ans(by(r['page'])['set:P1'], 'yes')])
    ended(store, r)


def test_my_own_picture_as_the_last_answer_ends_the_round():
    store, conn = not_made()
    p = by(page(store, conn))
    record(store, conn, [ans(p['set:P1'], 'yes')])
    mine = own(store, conn, 'E2')   # the tool hands the picture over before the line is recorded
    r = record(store, conn, [ans(p['set:E2'], 'own', own_ref=mine)])
    assert r['recorded'] == ['set:E2'] and saved(store)['golden']['E2'] == mine
    ended(store, r)


def test_the_chat_path_ends_in_the_same_state_as_the_page():
    store, conn = not_made()
    p = by(page(store, conn))
    record(store, conn, [ans(p['set:P1'], 'yes'), ans(p['set:E2'], 'aside')])
    other, conn2 = not_made()
    for start, choice in (('set:P1:', 'yes'), ('setmake:E2', 'aside')):   # the same two answers, each through the chat item's own run function
        item = next(i for i in CF._round_items(CF._ctx(conn2, other, USER, NEW, []), every=True) if i['id'].startswith(start))
        item['_run'](choice, 'Yes' if choice == 'yes' else 'Leave it out', '')
    got = CF.next_item(conn2, other, USER, NEW, [])   # `vw visuals next`
    a, b = saved(store)['round'], saved(other)['round']
    assert a['pass'] == b['pass'] == 'complete' and not any(str((got.get('item') or {}).get('id', '')).startswith(('set', 'round1')) for _ in [0])
    state = lambda rd: {e: (r.get('verdict'), bool(r.get('ignored')), bool(r.get('aside'))) for e, r in rd['elements'].items()}
    assert state(a) == state(b)


def test_a_round_that_stalled_before_is_ended_by_the_next_visit_and_the_assistant_is_told():
    store, conn = not_made()
    record(store, conn, [ans(by(page(store, conn))['set:P1'], 'yes')])
    VS.set_aside(store, USER, NEW, [], 'E2', 'not needed')   # as an older server left it: step 2 with nothing to answer
    assert at(store) == 2
    p = page(store, conn)
    assert saved(store)['round']['pass'] == 'complete' and p['step'] not in (A, B) and p['then'] == P.ROUND_NEXT
    assert 'then' not in page(store, conn)   # said once, when it ended


def test_a_set_still_to_answer_or_being_made_keeps_the_round_open():
    store, conn = not_made()
    r = record(store, conn, [ans(by(page(store, conn))['set:E2'], 'aside')])
    assert at(store) == 2 and r['page']['step'] == B and [l['key'] for l in r['page']['lines']] == ['set:P1']   # P1 still waits
    store, conn = at_sets()
    p = by(page(store, conn))
    r = record(store, conn, [ans(p['set:P1'], 'yes'), ans(p['set:E2'], 'no')])   # E2 is made again
    assert saved(store)['round']['pass'] == 'making' and r['then'].endswith(P.SETS_WAIT)


def test_the_answers_kept_sentence_is_given_only_when_an_answer_is_kept():
    store, conn = at_sets()
    s = saved(store)
    s['cap_inr'] = 1.0
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    p = by(page(store, conn))
    r = record(store, conn, [ans(p['set:E2'], p['set:E2']['pics'][0]['choice']), ans(p['set:P1'], 'no')])   # the limit holds P1's remake: its answer is kept
    assert r['then'].endswith(P.SETS_STAND) and by(r['page'])['set:P1']['kept'] and at(store) == 2
    store, conn = not_made()
    p = by(page(store, conn))
    r = record(store, conn, [ans(p['set:P1'], 'yes'), ans(p['set:E2'], 'aside')])   # nothing is kept
    assert P.SETS_STAND not in r['then']


# ---------- fix 2: a paid remake carries the operator's words ----------

@pytest.mark.parametrize('key, button', [('set:E2', 'None of these (paid'), ('set:P1', 'No (paid')])
def test_none_of_these_or_no_with_words_makes_the_set_again_with_the_words(key, button):
    store, conn = at_sets()
    eid, n = key.split(':')[1], len(conn.inserted)
    r = record(store, conn, [ans(by(page(store, conn))[key], 'no', '  the chimney is  too short ')])
    row = saved(store)['round']['elements'][eid]
    assert r['recorded'] == [key] and len(conn.inserted) == n + 1 and row['corrections'] == ['the chimney is too short']
    assert "The operator's correction: the chimney is too short." in json.dumps(conn.inserted[-1][2].obj)   # the words are in the new set's prompt, as Correct it puts them
    assert button in logged(conn)[-1] and 'the chimney is too short' in logged(conn)[-1]   # the button pressed, and the words


def test_none_of_these_with_no_words_is_as_before():
    store, conn = at_sets()
    n = len(conn.inserted)
    r = record(store, conn, [ans(by(page(store, conn))['set:E2'], 'no')])
    row = saved(store)['round']['elements']['E2']
    assert r['recorded'] == ['set:E2'] and len(conn.inserted) == n + 1 and row['verdict'] == 'no' and not row.get('corrections')
    assert "The operator's correction" not in json.dumps(conn.inserted[-1][2].obj)


def test_in_the_chat_no_stays_no_whatever_the_operator_said():
    store, conn = at_sets()
    item = next(i for i in CF._round_items(CF._ctx(conn, store, USER, NEW, []), every=True) if i['id'].startswith('set:E2:'))
    item['_run']('no', 'No, none of them', 'none of them')
    assert not saved(store)['round']['elements']['E2'].get('corrections')


# ---------- fix 3: the way out when pictures did not reach the page ----------

def test_the_way_out_for_pictures_that_did_not_arrive_is_named():
    how = P.HOW
    assert ('If a batch fails, or a picture stays grey on the page, run `vw visuals page --pictures-again` and send what it gives; '
            'if that fails too, stop here, run `vw visuals next` and ask this step in the chat.') in how
    assert 'once more' not in how   # the same batch cannot be written twice
    assert how.index('picture_batches') < how.index('--pictures-again') < how.index('zoom_uploads')


# ---------- fix 5: the sizes are made several at a time ----------

def test_the_sizes_are_made_through_a_pool_of_eight_in_the_lines_order_and_a_broken_picture_is_named(monkeypatch):
    store, pools, threads = H.Store(), [], set()
    for n in range(20):
        store.put(f'r1/{n:02d}.png', b'half a file' if n == 7 else picture((80, 60)))
    real = P.ThreadPoolExecutor

    class Pool(real):
        def __init__(self, *a, **k):
            pools.append(k.get('max_workers') or (a[0] if a else None))
            super().__init__(*a, **k)
    monkeypatch.setattr(P, 'ThreadPoolExecutor', Pool)
    made, shrink = [], P.shrink

    def counted(data, side, quality):
        made.append(side)
        threads.add(threading.current_thread().name)
        return shrink(data, side, quality)
    monkeypatch.setattr(P, 'shrink', counted)
    lines = [{'title': f'Thing {n // 5}', 'pics': [P.pic(f'r1/{k:02d}.png', f'Sheet {k}') for k in range(n, n + 5)]} for n in (0, 5, 10, 15)]
    lines.append({'title': 'Again', 'pics': [P.pic('r1/03.png', 'Sheet 3 again'), P.pic('r1/07.png', 'Sheet 7 again')]})   # the same pictures on a second line
    got = P._with_pictures(store, {'lines': lines})
    good = [n for n in range(20) if n != 7]
    assert pools == [8] and P.PIC_WORKERS == 8 and 'MainThread' not in threads
    assert [p['code'] for p in got['pictures']] == [P.pic_code(f'r1/{n:02d}.png') for n in good]   # the order of the lines, whichever finished first
    assert all(p['thumb'] == f'r1/{n:02d}.png.page-thumb.jpg' and p['zoom'] == f'r1/{n:02d}.png.page-zoom.jpg' for p, n in zip(got['pictures'], good))
    assert got['pictures_failed'] == ['Thing 1: Sheet 7'] and got['lines'][1]['pics'][2]['missing'] is True and got['lines'][4]['pics'][1]['missing'] is True
    assert 'missing' not in got['lines'][4]['pics'][0] and '_key' not in json.dumps(got)
    assert sorted(made) == [360] * 20 + [1600] * 19   # each size of each picture once, the picture on two lines too (the broken one stops at its first size)
    assert all(store.exists(f'r1/{n:02d}.png{s}') for n in good for s in ('.page-thumb.jpg', '.page-zoom.jpg'))
    made.clear()
    P._with_pictures(store, {'lines': [{'title': 'Later', 'pics': [P.pic('r1/01.png', 'Sheet 1')]}]})
    assert made == []   # stored: never made again


def test_a_page_with_no_picture_starts_no_pool(monkeypatch):
    monkeypatch.setattr(P, 'ThreadPoolExecutor', lambda *a, **k: pytest.fail('no pool is needed'))
    assert P._with_pictures(H.Store(), {'lines': [{'title': 'No pictures'}]}) == {'lines': [{'title': 'No pictures'}]}
