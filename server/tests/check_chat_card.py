"""design/190: the card's own check, without a database (run: python tests/check_chat_card.py from server/).
The decision functions of visuals_stage are replaced by small stand-ins that keep the same state the real ones keep; what is checked is the card:
when it is handed out, what it holds, that it is recorded once, and what happens to an entry that changed, a changed direction and an old card."""
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import chat_flow as C   # noqa: E402
from app import visuals_stage as V   # noqa: E402

STATE = {}
CALLS = []


class Conn:
    def execute(self, *a):
        return self

    def fetchall(self):
        return []


def session_of(store, run, outputs, create=False):
    return copy.deepcopy(STATE['session'])


def save_session(store, run, session):
    STATE['session'] = copy.deepcopy(session)


def treatment(store, user, run, outputs, document, quote, accept=(), send_back=(), notes=''):
    CALLS.append(('treatment', list(accept), list(send_back), notes))
    s = STATE['session']
    lines = s['treatment_draft']['lines']
    for k in accept:
        lines[k] = {'digest': lines[k]['digest'], 'state': 'accepted', 'quote': quote}
    for k in send_back:
        lines[k] = {'digest': lines[k]['digest'], 'state': 'sent_back', 'note': notes}
    if all(v['state'] == 'accepted' for v in lines.values()):
        s['treatment'] = s.pop('treatment_draft')
    return {}


def accept(store, user, run, outputs, gap_ids, quote):
    CALLS.append(('accept', list(gap_ids)))
    for g in gap_ids:
        STATE['session']['accepted'][g] = {'quote': quote}
    return {}


def revise_gap(store, user, run, outputs, gap_id, notes, quote):
    CALLS.append(('revise', gap_id, notes))
    STATE['session'].setdefault('revisions', {})[gap_id] = {'notes': notes}
    return {}


for name, fn in dict(session_of=session_of, save_session=save_session, treatment=treatment, accept=accept, revise_gap=revise_gap,
                     current_plan=lambda store, session: STATE['plan'], cap_of=lambda s: 5000, take_jobs=lambda *a: [], waiting=lambda *a: [],
                     _set_budget=lambda *a: 0, visuals_spend=lambda *a: 0, _accepted_shots=lambda *a: [],
                     gap_digest=lambda plan, gap: hashlib.sha256(json.dumps(gap, sort_keys=True).encode()).hexdigest(),
                     chosen_scenes=lambda gap, sel: gap['scenes'], route_of=lambda s: s['route']).items():
    setattr(V, name, fn)

ARGS = (Conn(), None, {'id': 'u1'}, {'id': 'r1', 'code': 'VW-T'}, {})


def base():
    return {'source': {'fps': 25, 'gaps': {}}, 'current': None, 'accepted': {}, 'choice_selections': {}, 'references': {}, 'recorded_gaps': {}, 'selections': {}, 'assets': {}}


def treatment_state(n):
    lines = {'direction': {'digest': 'd' * 12, 'state': 'to_accept'}, **{f'G{i}': {'digest': f'{i:012d}', 'state': 'to_accept'} for i in range(1, n + 1)}}
    STATE['session'] = {**base(), 'treatment_draft': {'direction': 'Show the wall rising. Keep it calm.', 'lines': lines, 'totals': {'gaps': n, 'images': 2}, 'estimate_inr': 120,
                                                     'gaps': [{'gap_id': f'G{i}', 'picture': f'Picture {i} </script><b>x</b>', 'routes': ['video'], 'seconds': 4, 'images': 1, 'why': 'w' * 3000} for i in range(1, n + 1)]}}
    STATE['plan'] = None


def plan_state(n, choice_on=None):
    gaps = [{'gap_id': f'G{i}', 'title': f'Gap title {i}', 'scenes': [{'shots': [{'id': f'G{i}-S1', 'title': 'A shot', 'route': 'video', 'start_frame': 0, 'end_frame': 100, 'purpose': 'It shows | this', 'narration': 'words'}]}],
             **({'choices': [{'id': 'a', 'title': 'Way A', 'description': 'd', 'why': 'w', 'tradeoff': 't'}, {'id': 'b', 'title': 'Way B', 'description': 'd', 'why': 'w', 'tradeoff': 't'}]} if f'G{i}' == choice_on else {})}
            for i in range(1, n + 1)]
    STATE['session'] = {**base(), 'current': 'p1', 'treatment': {}}
    STATE['plan'] = {'gaps': gaps, 'elements': []}


def answers(*rows):
    return [{'n': n, 'choice': c, 'notes': w} for n, c, w in rows]


def refused(fn):
    try:
        fn()
    except ValueError as exc:
        return str(exc)
    raise AssertionError('not refused')


def demo():
    # the treatment: every line on one card; the code holds each entry, cannot end its script, and no line of it is too long to read back
    treatment_state(3)
    out = C.next_item(*ARGS)
    card = out['card']
    assert out['item'] is None and card['entries'] == 4 and card['step'] == 'Treatment', out
    code = card['widget_code']
    assert '__DATA__' not in code and code.count('</script>') == 1 and '<\\/script>' in code and 'dir:1' in code
    assert max(len(line) for line in code.split('\n')) < 2000, max(len(line) for line in code.split('\n'))
    assert C.next_item(*ARGS)['card']['id'] == card['id']   # shown again: the same card

    # recorded once: the changes first, the accepted ones in one record; the same card again changes nothing
    CALLS.clear()
    got = C.card_answer(*ARGS, card['id'], answers((1, 'accept', ''), (2, 'accept', ''), (3, 'change', 'show the finished wall'), (4, 'accept', '')))
    assert got['recorded'] == [1, 2, 3, 4] and CALLS == [('treatment', [], ['G2'], 'show the finished wall'), ('treatment', ['direction', 'G1', 'G3'], [], '')], (got, CALLS)
    before = copy.deepcopy(STATE['session'])
    CALLS.clear()
    again = C.card_answer(*ARGS, card['id'], answers((1, 'change', 'x')))
    assert again['already'] and not CALLS and STATE['session'] == before

    # a changed direction: only the direction is recorded, and no gap line is asked until it is back
    treatment_state(3)
    card = C.next_item(*ARGS)['card']
    CALLS.clear()
    got = C.card_answer(*ARGS, card['id'], answers((1, 'change', 'warmer'), (2, 'accept', ''), (3, 'accept', ''), (4, 'accept', '')))
    assert got['recorded'] == [1] and got['held'] == [2, 3, 4] and CALLS == [('treatment', [], ['direction'], 'warmer')], (got, CALLS)
    assert got['item'] is None and not got.get('card') and got['needed'] is False

    # an older card, a missing entry, a change without words, an entry answered twice: refused, nothing recorded
    treatment_state(3)
    card = C.next_item(*ARGS)['card']
    CALLS.clear()
    assert 'not the card that is open' in refused(lambda: C.card_answer(*ARGS, 'card-0000000000', answers((1, 'accept', ''))))
    assert 'no entry 9' in refused(lambda: C.card_answer(*ARGS, card['id'], answers((9, 'accept', ''))))
    assert 'what should change' in refused(lambda: C.card_answer(*ARGS, card['id'], answers((2, 'change', ' '))))
    assert 'twice' in refused(lambda: C.card_answer(*ARGS, card['id'], answers((2, 'accept', ''), (2, 'accept', ''))))
    assert not CALLS

    # an entry that changed after the card was shown is not recorded and comes again; the others are recorded
    STATE['session']['treatment_draft']['lines']['G2']['digest'] = 'changed00000'
    got = C.card_answer(*ARGS, card['id'], answers((1, 'accept', ''), (2, 'accept', ''), (3, 'accept', ''), (4, 'accept', '')))
    assert got['recorded'] == [1, 2, 4] and got['not_open'] == [3] and got['item']['id'].startswith('treatment:G2:changed'), got   # one left: asked on its own

    # a first attempt that failed halfway had recorded entry 2's change: sent again, it counts as recorded and the change is passed on
    treatment_state(3)
    card = C.next_item(*ARGS)['card']
    STATE['session']['treatment_draft']['lines']['G1'] = {'digest': '000000000001', 'state': 'sent_back', 'note': 'shorter'}
    CALLS.clear()
    got = C.card_answer(*ARGS, card['id'], answers((1, 'accept', ''), (2, 'change', 'shorter'), (3, 'accept', ''), (4, 'accept', '')))
    assert got['recorded'] == [1, 2, 3, 4] and not got['not_open'] and 'change in entries 2' in got['then'] and CALLS == [('treatment', ['direction', 'G2', 'G3'], [], '')], (got, CALLS)

    # the direction was accepted elsewhere while the card was open: its change is not open any more, and the gaps are still recorded
    treatment_state(3)
    card = C.next_item(*ARGS)['card']
    STATE['session']['treatment_draft']['lines']['direction']['state'] = 'accepted'
    got = C.card_answer(*ARGS, card['id'], answers((1, 'change', 'warmer'), (2, 'accept', ''), (3, 'accept', ''), (4, 'accept', '')))
    assert got['recorded'] == [2, 3, 4] and got['not_open'] == [1] and not got['held'], got

    # one at a time, the older way: an item, and a card shown before is no longer answered
    treatment_state(3)
    card = C.next_item(*ARGS)['card']
    one = C.next_item(*ARGS, True)
    assert one['item']['id'].startswith('treatment:direction') and 'card' not in one
    assert 'not the card that is open' in refused(lambda: C.card_answer(*ARGS, card['id'], answers((1, 'accept', ''))))
    nxt = C.answer(*ARGS, one['item']['id'], 'accept', 'Accept', '', True)
    assert nxt['item']['id'].startswith('treatment:G1') and 'card' not in nxt

    # the plan: an offered choice is asked first, on its own; then the gaps on one card; a long plan in cards of ten
    plan_state(3, choice_on='G2')
    first = C.next_item(*ARGS)
    assert first['item']['kind'] == 'plan choice', first
    STATE['session']['choice_selections']['G2'] = {'choice_id': 'a'}
    card = C.next_item(*ARGS)['card']
    assert card['step'] == 'Plan' and card['entries'] == 3 and 'It shows / this' in card['widget_code'] and 'dir:0' in card['widget_code']
    CALLS.clear()
    got = C.card_answer(*ARGS, card['id'], answers((1, 'accept', ''), (2, 'change', 'shorter'), (3, 'accept', '')))
    assert CALLS == [('revise', 'G2', 'shorter'), ('accept', ['G1', 'G3'])] and got['recorded'] == [1, 2, 3] and got['needed'] is False, (CALLS, got)
    plan_state(20)
    out = C.next_item(*ARGS)
    assert out['card']['entries'] == 10 and out['waiting_after_this'] == 10
    got = C.card_answer(*ARGS, out['card']['id'], answers(*[(n, 'accept', '') for n in range(1, 11)]))
    assert got['card']['entries'] == 10 and got['card']['id'] != out['card']['id'] and got['waiting_after_this'] == 0
    plan_state(12)
    assert C.next_item(*ARGS)['card']['entries'] == 12
    print('ok: the card checks pass')


if __name__ == '__main__':
    demo()
