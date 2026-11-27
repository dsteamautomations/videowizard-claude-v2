"""Release 1 of 27 Nov 2026, phase 1, part G (SK approved): the page's "done" with many answers is recorded quickly.

Seen on VW-25: one "done" with 30 picture answers took 286 s, 27 took 284 s, 7 took 69 s (the server's request lines): about 10 s an answer,
whatever the answer was, against the tool's limit of 300 s. Measured on the live server on 27 Nov (read only): loading the run's state is two
reads of the store and takes 0.3 to 1.5 s; `page_record` loaded it again before every answer, each answer's own function loaded it again, and
the list of the step's items was rebuilt for each answer. Now one "done" reads each stored file once: what it reads is kept for the visit, and
what it writes is written at once, as before, and kept too. Each test failed first. Without a database."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
from app import page_flow as PF, visuals_stage as V   # noqa: E402
from app.errors import Problem   # noqa: E402
from test_design209_pure import ans, dim, drawing, page, plan_with, quiet, start   # noqa: E402,F401 (quiet: the fixture)


class Counting(H.Store):
    def __init__(self):
        super().__init__()
        self.reads, self.writes, self.deleted = [], [], []

    def get(self, k):
        self.reads.append(k)
        return super().get(k)

    def put(self, k, data, ctype=None):
        self.writes.append(k)
        return super().put(k, data, ctype)

    def delete(self, keys):
        self.deleted += list(keys)
        for k in keys:
            self.d.pop(k, None)

    def signed_download(self, k):
        return 'https://signed/' + k


# ---------- the visit's store ----------

def test_a_file_is_read_once_in_a_visit_and_a_write_is_read_back_from_memory():
    inner = Counting()
    inner.d['a'] = b'one'
    v = PF._Visit(inner)
    assert v.get('a') == b'one' and v.get('a') == b'one' and inner.reads == ['a']
    v.put('a', b'two', 'text/plain')
    assert inner.d['a'] == b'two' and inner.writes == ['a']                  # written at once, as before
    assert v.get('a') == b'two' and inner.reads == ['a']                     # and not read again
    v.put('b', b'new')
    assert v.get('b') == b'new' and inner.reads == ['a']


def test_a_missing_file_is_asked_again_and_a_deleted_one_is_forgotten():
    inner = Counting()
    v = PF._Visit(inner)
    for _ in range(2):
        with pytest.raises(Problem):
            v.get('gone')
    assert inner.reads == ['gone', 'gone']                                   # a refusal is never kept
    inner.d['x'] = b'1'
    assert v.get('x') == b'1'
    v.delete(['x'])
    assert inner.deleted == ['x']
    with pytest.raises(Problem):
        v.get('x')


def test_everything_else_goes_to_the_store_itself():
    inner = Counting()
    inner.d['a'] = b'1'
    v = PF._Visit(inner)
    assert v.exists('a') and not v.exists('b') and v.signed_download('a') == 'https://signed/a'
    assert v.count() == {'reads': 0, 'writes': 0}
    v.get('a'), v.get('a'), v.put('c', b'3')
    assert v.count() == {'reads': 1, 'writes': 1}


# ---------- a "done" with many answers ----------

def visit(n, wrapped=True, monkeypatch=None):
    """A page of n drawings' specs, every one answered yes in one "done": (the answer of the record call, the store)."""
    plan = plan_with([drawing([dim('box', 'length', 600 + i)]) for i in range(n)])
    store, conn = start(plan)
    counting = Counting()
    counting.d = store.d
    lines = [l for l in page(counting, conn)['lines'] if l['state'] == 'open']
    assert len(lines) == n
    counting.reads.clear(), counting.writes.clear()
    if not wrapped:
        monkeypatch.setattr(PF, '_Visit', lambda inner: inner)
    out = PF.page_record(conn, counting, H.USER, H.RUN, {}, [ans(l, 'yes') for l in lines])
    return out, counting


def session_reads(store):
    return sum(1 for k in store.reads if k.endswith('session.json'))


def test_the_reads_of_one_done_do_not_grow_with_the_number_of_answers(monkeypatch):
    few, three = visit(3)
    many, nine = visit(9)
    assert len(few['recorded']) == 3 and len(many['recorded']) == 9
    assert session_reads(three) == session_reads(nine) == 1                  # the run's state: read once, whatever the number of answers
    assert len(set(nine.reads)) == len(nine.reads)                           # no file is read twice in one visit
    _, before = visit(9, wrapped=False, monkeypatch=monkeypatch)
    assert session_reads(before) > 9                                         # the way before: again for every answer, and more


def test_what_is_recorded_is_what_was_recorded_before(monkeypatch):
    new, a = visit(6)
    old, b = visit(6, wrapped=False, monkeypatch=monkeypatch)
    for k in ('recorded', 'kept', 'stale', 'refused', 'dropped', 'open', 'then'):
        assert new[k] == old[k], k
    approvals = lambda store: {sid: x['digest'] for sid, x in V.session_of(store, H.RUN, {}).get('spec_approvals', {}).items()}
    assert approvals(a) == approvals(b) and len(approvals(a)) == 6
    assert a.writes == b.writes                                              # every write, in the same order, at once


def test_a_refused_line_is_kept_for_its_line_and_the_others_are_recorded():
    plan = plan_with([drawing([dim('box', 'length', 600 + i)]) for i in range(3)])
    store, conn = start(plan)
    lines = [l for l in page(store, conn)['lines'] if l['state'] == 'open']
    out = PF.page_record(conn, store, H.USER, H.RUN, {}, [ans(lines[0], 'yes'), ans(lines[1], 'no-such-choice'), ans(lines[2], 'yes')])
    assert len(out['recorded']) == 2 and [r['key'] for r in out['refused']] == [lines[1]['key']]


def test_the_record_calls_log_line_says_how_long_it_took_and_how_much_it_read():
    out, _ = visit(3)
    assert out['took']['answers'] == 3 and out['took']['reads'] >= 1 and out['took']['writes'] >= 1 and out['took']['seconds'] >= 0
    assert f"{out['took']['reads']} file(s) read" in out['log'] and 'recorded' in out['log']
