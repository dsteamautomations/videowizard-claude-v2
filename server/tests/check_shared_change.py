"""design/191: a change to the plan's shared part is asked once, not once per gap; and the other places an approval was dropped when the
plan changed (section 11: A2, A4, A5, B1, B2, B4). Without a database (run: python tests/check_shared_change.py from server/): the real
decision functions of visuals_stage on a store kept in memory; only the plan's validation is left out (a new version is stored by the same
function `propose` calls after it)."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import chat_flow as C   # noqa: E402
from app import visuals_stage as V   # noqa: E402
from app.errors import Problem   # noqa: E402


class Store:
    def __init__(self):
        self.d = {}

    def get(self, k):
        if k not in self.d:
            raise Problem(404, 'NOT_FOUND', k)
        return self.d[k]

    def put(self, k, data, ctype=None):
        self.d[k] = data

    def exists(self, k):
        return k in self.d


class Conn:
    def __init__(self):
        self.log = []

    def execute(self, sql, args=()):
        if 'vw2_log' in sql:
            self.log.append(args)
        return self

    def fetchall(self):
        return []

    def fetchone(self):
        return None


RUN, USER = {'id': 'r1', 'code': 'VW-T'}, {'id': 'u1', 'name': 'SK'}


def shot(sid, purpose='It shows the wall', element='wall'):
    return {'id': sid, 'title': 'Shot ' + sid, 'visual_type': 'image', 'start_frame': 0, 'end_frame': 100, 'purpose': purpose, 'narration': 'words', 'element_ids': [element], 'size': 'WS'}


def plan_of(n=3, foundation='calm and plain', rules=('no shot repeats',), purposes=None, choices_on=None, choice_ids=('a', 'b'), drop=()):
    gaps = []
    for i in range(1, n + 1):
        gid = f'G{i}'
        if gid in drop:
            continue
        scenes = [{'ambient': 'quiet', 'shots': [shot(f'{gid}-S1', (purposes or {}).get(gid, 'It shows the wall'))]}]
        gaps.append({'gap_id': gid, 'title': f'Title {i}', **({'choices': [{'id': c, 'title': 'Way ' + c, 'description': 'd', 'why': 'w', 'tradeoff': 't', 'scenes': scenes} for c in choice_ids],
                                                              'recommended_choice': choice_ids[0]} if gid == choices_on else {'scenes': scenes})})
    return {'foundation': {'treatment': 'Show the wall rising.', 'style': foundation}, 'sequence_rules': [{'id': f'r{i}', 'rule': r} for i, r in enumerate(rules, 1)],
            'gaps': gaps, 'elements': [{'id': 'wall', 'name': 'The wall', 'kind': 'object', 'description': 'a brick wall', 'size': '2 m'}]}


def fresh(store):
    V.save_session(store, RUN, {'source': {'fps': 25, 'gaps': {}, 'plan_digest': 'src'}, 'versions': [], 'current': None, 'accepted': {}, 'choice_selections': {}, 'references': {}, 'bindings': {},
                                'reviews': {}, 'selections': {}, 'assets': {}, 'recorded_gaps': {}, 'treatment': {'gaps': []}})


def propose(store, plan):
    session = V.session_of(store, RUN, {})
    out = V.new_version(store, RUN, session, plan, USER, [])
    V.save_session(store, RUN, session)
    return out


def session(store):
    return V.session_of(store, RUN, {})


def items(store, conn):
    return C._candidates(C._ctx(conn, store, USER, RUN, {}))[0]


def refused(fn):
    try:
        fn()
    except (ValueError, Problem) as exc:
        return str(getattr(exc, 'message', '') or exc)
    raise AssertionError('not refused')


def start(n=3, accept=True, **kw):
    store, conn = Store(), Conn()
    fresh(store)
    propose(store, plan_of(n, **kw))
    if accept:
        V.accept(store, USER, RUN, {}, [f'G{i}' for i in range(1, n + 1)], 'yes to all')
    return store, conn


def demo():
    # the list of what changed: a foundation edit, a sequence rule edit, a shot edit
    a, b = plan_of(), plan_of(foundation='warm and busy')
    d = V._diff(a['foundation'], b['foundation'], 'The foundation')
    assert d == ['The foundation › style: "calm and plain" → "warm and busy"'], d
    d = V._diff(plan_of()['sequence_rules'], plan_of(rules=('no shot repeats twice', 'faces look left'))['sequence_rules'], 'The sequence rules')
    assert d == ['The sequence rules › r2: added', 'The sequence rules › r1 › rule: "no shot repeats" → "no shot repeats twice"'], d
    d = V._diff(plan_of()['gaps'][0]['scenes'], plan_of(purposes={'G1': 'It shows the trowel'})['gaps'][0]['scenes'], 'Scenes')
    assert d == ['Scenes › 1 › shots › G1-S1 › purpose: "It shows the wall" → "It shows the trowel"'], d

    long_a, long_b = 'x' * 200 + ' ends calm', 'x' * 200 + ' ends loud'
    d = V._diff({'style': long_a}, {'style': long_b}, 'The foundation')
    assert 'ends calm' in d[0] and 'ends loud' in d[0], d   # a long value shows where it differs, never the same words twice
    assert V._diff({'rules': ['a', 'b']}, {'rules': ['a', 'b', 'c']}, 'F') == ['F › rules: added "c"']

    # only the shared part changed: no gap is accepted, no gap is asked by itself, ONE question with two buttons says what changed
    store, conn = start()
    V.bind  # (the binding below is written as `bind` writes it)
    s = session(store)
    s['bindings']['G1-S1'] = {'gap_digest': s['accepted']['G1']['digest'], 'references': {}, 'quote': 'bind it', 'by': 'u1'}
    V.save_session(store, RUN, s)
    propose(store, plan_of(foundation='warm and busy'))
    s = session(store)
    assert not s['accepted'] and sorted(s['shared_pending']) == ['G1', 'G2', 'G3'], s
    assert 'Accept gap G1' in refused(lambda: V.locate(store, s, 'G1-S1'))   # nothing is silently kept: work on its shots is refused
    its = items(store, conn)
    assert [i['kind'] for i in its] == ['plan shared'], [i['kind'] for i in its]
    q = its[0]
    assert [b['label'] for b in q['buttons']] == ['Accept', 'Change this'] and q['buttons'][1].get('needs_words')
    assert '3 gaps' in q['question'] and 'style: "calm and plain" → "warm and busy"' in q['text'] and 'G1, G2, G3' in q['text'], q
    # the chat shows that single question (the plugin shows what the server hands out)
    out = C.next_item(conn, store, USER, RUN, {})
    assert out['item']['id'] == q['id'] and 'card' not in out and [b['label'] for b in out['item']['buttons']] == ['Accept', 'Change this']
    # Change this with no words is refused
    assert 'what to change' in refused(lambda: C.answer(conn, store, USER, RUN, {}, q['id'], 'change', 'Change this', '')).lower()
    # Accept: every gap is accepted under the new version with the operator's words; the binding holds again; one log line names the gaps and the change
    got = C.answer(conn, store, USER, RUN, {}, q['id'], 'accept', 'yes, the warmer look')
    s = session(store)
    assert sorted(s['accepted']) == ['G1', 'G2', 'G3'] and not s['shared_pending'] and all(v['quote'] == 'yes, the warmer look' and v['version'] == 2 for v in s['accepted'].values()), s['accepted']
    assert s['bindings']['G1-S1']['gap_digest'] == s['accepted']['G1']['digest'] == V.gap_digest(V.current_plan(store, s), V.current_plan(store, s)['gaps'][0])
    assert len(conn.log) == 1 and 'G1, G2, G3' in conn.log[0][5] and 'warm and busy' in conn.log[0][5] and conn.log[0][8] == 'yes, the warmer look', conn.log
    assert got['item'] is None and V.locate(store, s, 'G1-S1')

    # Change this: the words wait for the assistant, the question is not asked again, and no gap is asked by itself
    store, conn = start()
    propose(store, plan_of(foundation='warm and busy'))
    q = items(store, conn)[0]
    out = C.next_item(conn, store, USER, RUN, {})
    got = C.answer(conn, store, USER, RUN, {}, q['id'], 'change', 'keep it calm', 'keep it calm')
    s = session(store)
    assert s['shared_revision']['notes'] == 'keep it calm' and not s['accepted'] and got['item'] is None and any('shared rules' in w for w in got['working']), got
    assert V.status_shared(store, s)['revise']['notes'] == 'keep it calm'
    # the assistant puts the shared part back: every acceptance stands again, nothing is asked
    propose(store, plan_of())
    s = session(store)
    assert sorted(s['accepted']) == ['G1', 'G2', 'G3'] and not s.get('shared_pending') and not s.get('shared_revision') and not items(store, conn)

    # shared part and one gap's own content both changed: that gap is asked by itself, with what changed; the one question covers the others
    store, conn = start()
    propose(store, plan_of(foundation='warm and busy', purposes={'G2': 'It shows the trowel'}))
    its = items(store, conn)
    assert [i['kind'] for i in its] == ['plan shared', 'plan gap'] and '2 gaps' in its[0]['question'] and 'G1, G3' in its[0]['text']
    assert its[1]['id'].startswith('gap:G2:') and 'changed since you accepted it' in its[1]['question'] and 'purpose: "It shows the wall" → "It shows the trowel"' in its[1]['text'], its[1]
    # B3: a gap whose own content alone changed says what changed too
    store, conn = start()
    propose(store, plan_of(purposes={'G2': 'It shows the trowel'}))
    its = items(store, conn)
    assert [i['id'][:7] for i in its] == ['gap:G2:'] and 'It shows the trowel' in its[0]['text'] and sorted(session(store)['accepted']) == ['G1', 'G3']

    # shared part changed, no gap accepted yet: no shared question; the gaps are asked as normal (on one card)
    store, conn = start(accept=False)
    propose(store, plan_of(foundation='warm and busy'))
    assert [i['kind'] for i in items(store, conn)] == ['plan gap'] * 3 and 'changed since' not in items(store, conn)[0]['question']

    # only notes changed (a size, a scene's ambient): nothing is asked
    store, conn = start()
    p = plan_of()
    p['elements'][0]['size'], p['gaps'][0]['scenes'][0]['ambient'], p['gaps'][0]['scenes'][0]['shots'][0]['size'] = '3 m', 'loud', 'CU'
    propose(store, p)
    assert sorted(session(store)['accepted']) == ['G1', 'G2', 'G3'] and not items(store, conn)

    # a gap removed: its acceptance is dropped; a gap added: asked as a new gap
    store, conn = start()
    propose(store, plan_of(4, drop=('G2',)))
    s = session(store)
    assert sorted(s['accepted']) == ['G1', 'G3'] and [i['id'][:7] for i in items(store, conn)] == ['gap:G4:']

    # a gap with alternatives whose choice was made: the choice is kept when only the shared part changed
    store, conn = start(accept=False, choices_on='G2')
    V.select_choice(store, USER, RUN, {}, {'G2': 'b'})
    V.accept(store, USER, RUN, {}, ['G1', 'G2', 'G3'], 'yes')
    propose(store, plan_of(foundation='warm and busy', choices_on='G2'))
    q = items(store, conn)[0]
    C.next_item(conn, store, USER, RUN, {})
    C.answer(conn, store, USER, RUN, {}, q['id'], 'accept', 'yes')
    s = session(store)
    assert s['choice_selections']['G2']['choice_id'] == 'b' and s['accepted']['G2']['choice_id'] == 'b'
    # B1: the new version no longer has the chosen way: the choice is asked again instead of the chat stopping with an error
    propose(store, plan_of(foundation='warm and busy', choices_on='G2', choice_ids=('x', 'y')))
    s = session(store)
    assert 'G2' not in s['choice_selections'] and 'G2' not in s['accepted']
    assert [i['kind'] for i in items(store, conn)] == ['plan choice']

    # two new versions before the operator answers: the question compares the last accepted version with the current one
    store, conn = start()
    propose(store, plan_of(foundation='warm and busy'))
    propose(store, plan_of(foundation='warm and loud'))
    its = items(store, conn)
    assert [i['kind'] for i in its] == ['plan shared'] and 'style: "calm and plain" → "warm and loud"' in its[0]['text'] and 'busy' not in its[0]['text']

    # a very long shared change: the first 10 changes, then "and N more"
    store, conn = start(rules=tuple(f'rule {i}' for i in range(14)))
    propose(store, plan_of(rules=tuple(f'rule {i} changed' for i in range(14))))
    text = items(store, conn)[0]['text']
    assert text.count('→') == 10 and 'and 4 more' in text, text
    assert len(V.status_shared(store, session(store))['changes']) == 14   # the full list, for the visuals page

    # the earlier version cannot be read: each gap is asked, as before, and the answer says so
    store, conn = start()
    propose(store, plan_of(foundation='warm and busy'))
    del store.d[V.key(RUN, 'plan-v1.json')]
    its = items(store, conn)
    assert [i['kind'] for i in its] == ['plan gap'] * 3 and 'could not be read' in its[0]['text'], its[0]['text']
    C.next_item(conn, store, USER, RUN, {}, True)
    C.answer(conn, store, USER, RUN, {}, its[0]['id'], 'accept', 'yes', '', True)
    s = session(store)
    assert 'G1' in s['accepted'] and sorted(s['shared_pending']) == ['G2', 'G3']

    # a gap that waits behind the shared question and is accepted by itself (the page's Accept) keeps its shots' references bound
    store, conn = start()
    s = session(store)
    s['bindings']['G1-S1'] = {'gap_digest': s['accepted']['G1']['digest'], 'references': {}, 'quote': 'bind it', 'by': 'u1'}
    V.save_session(store, RUN, s)
    propose(store, plan_of(foundation='warm and busy'))
    V.accept(store, USER, RUN, {}, ['G1'], 'yes')
    s = session(store)
    assert s['bindings']['G1-S1']['gap_digest'] == s['accepted']['G1']['digest'] and sorted(s['shared_pending']) == ['G2', 'G3']

    # gaps accepted in different versions: the one question lists every change since each of them
    store, conn = start(2)
    propose(store, plan_of(3, foundation='warm and busy'))
    V.accept(store, USER, RUN, {}, ['G3'], 'yes')
    propose(store, plan_of(3, foundation='calm and plain', rules=('no shot repeats twice',)))
    text = items(store, conn)[0]['text']
    assert 'G1, G2, G3' in text and '"warm and busy" → "calm and plain"' in text and 'no shot repeats twice' in text, text

    # an acceptance from before this release (no split fingerprint) is asked again on any change, as before
    store, conn = start()
    s = session(store)
    for acc in s['accepted'].values():
        acc.pop('own'), acc.pop('shared'), acc.pop('version')
    V.save_session(store, RUN, s)
    propose(store, plan_of(foundation='warm and busy'))
    s = session(store)
    assert not s['accepted'] and not s.get('shared_pending') and [i['kind'] for i in items(store, conn)] == ['plan gap'] * 3

    # A2: a change the operator asked for on a gap is kept through a new version that left that gap's own content alone
    store, conn = start(accept=False)
    V.revise_gap(store, USER, RUN, {}, 'G2', 'show the trowel', 'show the trowel')
    propose(store, plan_of(foundation='warm and busy'))
    assert session(store)['revisions']['G2']['notes'] == 'show the trowel'
    propose(store, plan_of(foundation='warm and busy', purposes={'G2': 'It shows the trowel'}))   # the gap is proposed changed: the revision is answered
    assert 'G2' not in session(store)['revisions']

    # A5: a gap already recorded into the film, own content unchanged, is never asked again; the log says it was kept
    store, conn = start()
    s = session(store)
    s['recorded_gaps']['G1'] = 'out-1'
    V.save_session(store, RUN, s)
    out = propose(store, plan_of(foundation='warm and busy'))
    s = session(store)
    assert sorted(s['accepted']) == ['G1'] and sorted(s['shared_pending']) == ['G2', 'G3'] and out['kept_recorded'] == ['G1']
    assert 'G2, G3' in items(store, conn)[0]['text'] and 'G1,' not in items(store, conn)[0]['text']

    # A4: while the one question waits, the answer says why the shots of those gaps wait
    assert 'wait' in items(store, conn)[0]['text']

    # B2: a treatment line asked again says what changed
    sess = {'treatment_draft': {'direction': 'Show the wall rising.', 'gaps': [{'gap_id': 'G1', 'picture': 'a wall', 'seconds': 4}],
                                'lines': {'direction': {'digest': V._line_digests({'direction': 'Show the wall rising.'})['direction'], 'state': 'accepted', 'quote': 'y'},
                                          'G1': {'digest': V._line_digests({'gaps': [{'gap_id': 'G1', 'picture': 'a wall', 'seconds': 4}]})['G1'], 'state': 'accepted', 'quote': 'y'}}}}
    lines = V._carry_lines(sess, {'direction': 'Show the wall rising.', 'gaps': [{'gap_id': 'G1', 'picture': 'a finished wall', 'seconds': 4}]})
    assert lines['direction']['state'] == 'accepted' and lines['G1']['state'] == 'to_accept' and lines['G1']['changes'] == ['picture: "a wall" → "a finished wall"'], lines
    lines = V._carry_lines(sess, {'direction': 'Show the wall rising, warmly.', 'gaps': [{'gap_id': 'G1', 'picture': 'a wall', 'seconds': 4}]})
    assert lines['direction']['changes'] == ['Before: "Show the wall rising."'] and lines['G1']['state'] == 'accepted', lines

    # B4: a first-step answer of the reference round is kept when the round is posted again with the same footage pictures of that thing, and dropped when they changed
    assert C._round_kept({'wall': {'verdict': 'approve', 'quote': 'y', 'frames': 'f1,f2'}, 'door': {'verdict': 'ignore', 'quote': 'n', 'frames': 'f3'}},
                         {'wall': 'f1,f2', 'door': 'f9'}) == {'wall': {'verdict': 'approve', 'quote': 'y', 'frames': 'f1,f2'}}
    print('ok: the shared-change checks pass')


if __name__ == '__main__':
    demo()
