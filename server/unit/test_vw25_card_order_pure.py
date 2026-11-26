"""VW-25 issue 14 (SK, 25 Nov 2026): the order of the chat's cards. Step 6's own cards (questions, the shared parts of the drawn graphics,
drawing specs, still end-frames) come before the layout cards of AI video shots: reference drawings, the references round, step 6's waiting
cards, the layout cards, step 7's stills and words to make the take. The layout cards are made in their own function (`_layout_items`), after
`_waiting_items`. A layout card, or a group of them, already handed out stays the open one until it is answered: a step 6 card that becomes
ready meanwhile is next. With nothing of step 6 waiting the layout cards come as before: together, up to four, in the film's order.
Older way retired: the layout cards made inside `_drawing_items`, first in the order. Without a database."""
import pytest

from app import chat_flow as CF, visuals_stage as V
from test_design222_takes_pure import RUN, USER, plan, shot

STEPS = ('_drawing_items', '_round_items', '_waiting_items', '_layout_items', '_guide_items', '_record_items')
OPEN = 'is not the decision that is open'


@pytest.fixture
def chat(monkeypatch):
    """The chat's flow over the real order (`_candidates`), each step a list of waiting items; an answered item leaves its list."""
    st = {'session': {}, 'answers': [], 'asked': [], **{name: [] for name in STEPS}}
    monkeypatch.setattr(V, 'session_of', lambda store, run, outputs: st['session'])
    monkeypatch.setattr(V, 'save_session', lambda store, run, s: None)
    monkeypatch.setattr(V, 'round_due', lambda s, p: None)
    monkeypatch.setattr(CF, 'flush_sets', lambda *a, **k: None)
    monkeypatch.setattr(CF, 'working', lambda conn, run: [])
    monkeypatch.setattr(CF, '_round_frames', lambda ctx: [])
    monkeypatch.setattr(CF, '_treatment_items', lambda ctx: ([], '', []))
    monkeypatch.setattr(CF, '_plan_items', lambda ctx: ([], []))
    for name in STEPS:
        monkeypatch.setattr(CF, name, lambda ctx, name=name: st['asked'].append(name) or list(st[name]))
    st['next'] = lambda **k: CF.next_item(None, None, USER, RUN, [], **{'many': True, **k})
    st['answer'] = lambda iid, choice='yes', **k: CF.answer(None, None, USER, RUN, [], iid, choice, '', '', **{'many': True, **k})
    return st


def card(st, step, ident, kind='drawing'):
    def run_(choice, quote, words):
        st['answers'].append(ident)
        st[step][:] = [i for i in st[step] if i['id'] != ident]
        return {}
    item = CF._item(ident, kind, 'somewhere', f'{ident}: is it right?', run_, [CF._button('Yes', 'yes'), CF._button('Correct it', 'correct', words=True, tell='Ask.')])
    st[step].append(item)
    return item


layout = lambda st, sid: card(st, '_layout_items', f'shot-drawing:{sid}:{"b" * 10}')
held = lambda st, sid: card(st, '_layout_items', f'layout-held:{sid}:{"c" * 10}', 'held layout')
parts = lambda st, n=1: card(st, '_waiting_items', f'parts:{n}', 'shared parts')


def ids(out):
    return [i['id'].split(':')[1] for i in out['group']['items']] if out.get('group') else [out['item']['id'].split(':')[1]] if out.get('item') else []


def refused(fn):
    with pytest.raises((ValueError, V.Problem)) as e:
        fn()
    return str(getattr(e.value, 'message', '') or e.value)


def test_the_steps_are_asked_in_this_order(chat):
    assert chat['next']()['needed'] is False                                               # nothing waits: every step was asked, in the order
    assert chat['asked'][:len(STEPS)] == list(STEPS)


def test_a_step_6_card_comes_before_the_layout_cards_and_they_before_step_7(chat):
    layout(chat, 'S1'), layout(chat, 'S2'), parts(chat), card(chat, '_guide_items', 'still:S9:x', 'still')
    out = chat['next']()
    assert ids(out) == ['1'] and out['item']['kind'] == 'shared parts'                     # today's fault: the layout cards went ahead and the drawn graphics did not start
    out = chat['answer']('parts:1')
    assert ids(out) == ['S1', 'S2'] and out['group']['kind'] == 'layout drawing'           # then the layout cards, together
    chat['answer'](f'shot-drawing:S1:{"b" * 10}')
    out = chat['answer'](f'shot-drawing:S2:{"b" * 10}')
    assert ids(out) == ['S9'] and out['item']['kind'] == 'still'                           # then step 7's own cards


def test_with_nothing_of_step_6_waiting_the_layout_cards_come_as_before(chat):
    for sid in ('S1', 'S2', 'S3', 'S4', 'S5'):
        layout(chat, sid)
    out = chat['next']()
    assert ids(out) == ['S1', 'S2', 'S3', 'S4'] and out['waiting_after_this'] == 1         # together, four at most, in the film's order
    assert ids(chat['next'](many=False)) == ['S1']                                         # a tool that shows one at a time: one, as before
    held(chat, 'S0')
    chat['_layout_items'].insert(0, chat['_layout_items'].pop())                           # a held layout earlier in the film: alone, in its place
    chat['session'].clear()
    assert ids(chat['next']()) == ['S0']


def test_an_open_layout_group_is_finished_before_a_step_6_card_that_became_ready(chat):
    for sid in ('S1', 'S2', 'S3'):
        layout(chat, sid)
    assert ids(chat['next']()) == ['S1', 'S2', 'S3']
    parts(chat), layout(chat, 'S4')                                                        # a step 6 card and one more layout become ready while the group is open
    assert ids(chat['next']()) == ['S1', 'S2', 'S3']                                       # asked again: the same group, not the newer card
    assert OPEN in refused(lambda: chat['answer']('parts:1'))                              # the newer card is not the open one
    assert OPEN in refused(lambda: chat['answer'](f'shot-drawing:S4:{"b" * 10}'))          # nor a layout that was never handed out
    out = chat['answer'](f'shot-drawing:S2:{"b" * 10}')                                    # each answer on its own, in any order
    assert out['answered'].split(':')[1] == 'S2' and ids(out) == ['S1', 'S3']
    assert chat['session']['chat_item']['group'] == [f'shot-drawing:{s}:{"b" * 10}' for s in ('S1', 'S3')]
    assert ids(chat['next']()) == ['S1', 'S3']                                             # a look in between changes nothing
    assert ids(chat['answer'](f'shot-drawing:S3:{"b" * 10}')) == ['S1']
    out = chat['answer'](f'shot-drawing:S1:{"b" * 10}')
    assert ids(out) == ['1'] and out['item']['kind'] == 'shared parts'                     # the group is finished: the step 6 card is next
    assert ids(chat['answer']('parts:1')) == ['S4']                                        # then the layout that became ready
    assert chat['answers'] == [f'shot-drawing:{s}:{"b" * 10}' for s in ('S2', 'S3', 'S1')] + ['parts:1']


def test_one_open_layout_card_stays_the_open_one(chat):
    held(chat, 'S1')
    assert ids(chat['next']()) == ['S1']
    parts(chat)
    assert ids(chat['next']()) == ['S1']                                                   # the card on the operator's screen is not replaced
    said = refused(lambda: chat['answer']('parts:1'))
    assert OPEN in said and 'layout-held:S1' in said
    out = chat['answer'](f'layout-held:S1:{"c" * 10}', 'yes')
    assert ids(out) == ['1'] and 'chat_item' in chat['session'] and 'group' not in chat['session']['chat_item']


def test_an_open_layout_card_that_no_longer_waits_gives_way(chat):
    layout(chat, 'S1'), layout(chat, 'S2')
    assert ids(chat['next']()) == ['S1', 'S2']
    chat['_layout_items'][0]['id'] = f'shot-drawing:S1:{"d" * 10}'                         # S1's layout was rebuilt meanwhile: another card
    parts(chat)
    assert ids(chat['next']()) == ['S2']                                                   # what is left of the open group
    chat['_layout_items'][:] = chat['_layout_items'][:1]                                   # and S2's too: nothing of the group waits
    assert ids(chat['next']()) == ['1']                                                    # the usual order


def test_one_at_a_time_only_the_card_handed_out_is_open(chat):
    layout(chat, 'S1'), layout(chat, 'S2')
    assert ids(chat['next'](many=False)) == ['S1']
    parts(chat)
    out = chat['answer'](f'shot-drawing:S1:{"b" * 10}', many=False)
    assert ids(out) == ['1']                                                               # S2 was never handed out: the step 6 card is next
    assert ids(chat['answer']('parts:1', many=False)) == ['S2']


def test_a_group_of_still_end_frames_is_as_before(chat):
    for sid in ('D1', 'D2'):
        card(chat, '_waiting_items', f'still-end:{sid}:{"a" * 10}', 'still end-frame')
    assert ids(chat['next']()) == ['D1', 'D2']
    out = chat['answer'](f'still-end:D1:{"a" * 10}')
    assert ids(out) == ['D2'] and 'group' not in chat['session']['chat_item']              # the rest is handed out afresh, as before this change


def test_the_layout_cards_are_made_in_their_own_function(monkeypatch):
    p = plan(shot('S1', start=0), shot('S2', start=130))
    guide = lambda sha: {'sha256': sha, 'verdicts': [{'pass': True}], 'drawing': {'status': 'proposed', 'sha256': sha, 'views': [{'id': 'camera', 'labelled_key': 'k/' + sha}]}}
    s = {'guides': {'S2': guide('2' * 64), 'S1': guide('1' * 64)}}
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    ctx = {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': USER, 'outputs': [], 'conn': None}
    assert CF._drawing_items(ctx) == []                                                    # older way retired: none of them is made here
    assert [i['id'].split(':')[:2] for i in CF._layout_items(ctx)] == [['shot-drawing', 'S1'], ['shot-drawing', 'S2']]   # the film's order
    assert all(i['id'].startswith(CF.LAYOUT) for i in CF._layout_items(ctx)) and CF.LAYOUT == ('shot-drawing:', 'layout-held:')
    assert CF._layout_items({**ctx, 'plan': None}) == [] and CF._layout_items({**ctx, 'session': {}}) == []   # no plan, or no AI video: none
