"""Release 2, B4 and B4b (SK, 20 Nov 2026, the end-frame answer): several still end-frames of drawn graphics that are ready together, and
several layout drawings of AI video shots, are handed out in ONE message: a group of at most four, in the order of the film, each with its
own answer. Still one decision per picture: each answer is recorded on its own, in any order; one that is not answered stays open and is
handed out again, alone or with what became ready since. Only one ready: exactly as before. A tool that does not say it can take a group
(an older plugin), and `--one`, get one item at a time as before; an answer to anything outside what was handed out is refused with the
same sentence as before. Both kinds go through one function (`chat_flow._together`). Without a database."""
import pytest

from app import chat_flow as CF, guide as G, visuals_stage as V
from test_design222_takes_pure import RUN, USER, plan, shot

WHERE = 'Step 6, drawn graphics: the still end-frame'
OPEN = 'is not the decision that is open'


@pytest.fixture
def chat(monkeypatch):
    """The chat's flow over a list of waiting items (as `_candidates` gives them) and one session; an answered item leaves the list."""
    st = {'session': {}, 'items': [], 'answers': []}
    monkeypatch.setattr(V, 'session_of', lambda store, run, outputs: st['session'])
    monkeypatch.setattr(V, 'save_session', lambda store, run, s: None)
    monkeypatch.setattr(V, 'round_due', lambda s, p: None)
    monkeypatch.setattr(CF, 'flush_sets', lambda *a, **k: None)
    monkeypatch.setattr(CF, 'working', lambda conn, run: [])
    monkeypatch.setattr(CF, '_candidates', lambda ctx: (list(st['items']), '', []))
    st['next'] = lambda **k: CF.next_item(None, None, USER, RUN, [], **k)
    st['answer'] = lambda iid, choice, notes='', **k: CF.answer(None, None, USER, RUN, [], iid, choice, '', notes, **{'many': True, **k})
    st['add'] = lambda *items: st['items'].extend(items)
    return st


def card(st, ident, kind, question, buttons, tell):
    def run_(choice, quote, words):
        st['answers'].append((ident, choice, words))
        st['items'][:] = [i for i in st['items'] if i['id'] != ident]
        return {}
    return CF._item(ident, kind, WHERE, question, run_, [CF._button(buttons[0], buttons[0].lower()), CF._button(buttons[1], buttons[1].lower(), words=True, tell=tell)],
                    show=[{'key': f'k/{ident}.png', 'name': f'{ident.split(":")[1]}.png'}])


def end(st, sid):
    """A still end-frame's item, as `_waiting_items` writes it."""
    return card(st, f'still-end:{sid}:{"a" * 10}', 'still end-frame', f'{sid}: this is the drawing as it stands at the end of the shot, before any motion is added. Is it right?',
                ('Approve', 'Reject'), 'Ask the operator what to change in the still, in their words.')


def layout(st, sid):
    """A layout drawing's item, as `_layout_items` writes it."""
    return card(st, f'shot-drawing:{sid}:{"b" * 10}', 'drawing', f'{sid}: is the shot laid out right in these two drawings?', ('Yes', 'Correct'), 'Ask the operator what is wrong in the drawing of the shot.')


def ids(out):
    return [i['id'].split(':')[1] for i in out['group']['items']] if out.get('group') else [out['item']['id'].split(':')[1]] if out.get('item') else []


def refused(fn):
    with pytest.raises((ValueError, V.Problem)) as e:
        fn()
    return str(getattr(e.value, 'message', '') or e.value)


# ---------- B4: still end-frames ----------

def test_several_end_frames_ready_together_come_in_one_group_each_with_its_own_answer(chat):
    chat['add'](*(end(chat, s) for s in ('D1', 'D2', 'D3')))
    out = chat['next'](many=True)
    g = out['group']
    assert out['item'] is None and out['needed'] is True and out['say_last'] == CF.NEEDED and out['waiting_after_this'] == 0
    assert ids(out) == ['D1', 'D2', 'D3'] and g['kind'] == 'still end-frame' and '3 still end-frames' in g['heading']   # one shared heading
    for sid, i in zip(('D1', 'D2', 'D3'), g['items']):
        assert i['ask'].startswith(sid + ': ') and i['ask'].endswith('Is it right?')                            # each question names its own picture
        assert [(b['label'], b['choice']) for b in i['buttons']] == [('Approve', 'approve'), ('Reject', 'reject')] and all(b['description'] for b in i['buttons'])
        assert [f['name'] for f in i['show']] == [sid + '.png'] and 'how' not in i and '_run' not in i
    assert 'side by side' in out['how'] and 'one question for each' in out['how'] and '`vw visuals next --one`' in out['how']
    assert chat['session']['chat_item']['group'] == [i['id'] for i in g['items']]                              # the gate holds the whole group


def test_only_one_ready_looks_exactly_as_before(chat):
    chat['add'](end(chat, 'D1'))
    alone = chat['next'](many=True)
    chat['session'].clear()
    before = chat['next']()
    assert 'group' not in alone and alone['item'] == before['item'] and set(alone) == set(before)
    assert 'group' not in chat['session']['chat_item']


def test_a_tool_that_knows_one_item_gets_one_at_a_time_and_the_second_is_refused(chat):
    chat['add'](*(end(chat, s) for s in ('D1', 'D2', 'D3')))
    for out in (chat['next'](), chat['next'](one=True, many=True)):                                             # an older plugin; `--one`, the way back
        assert 'group' not in out and ids(out) == ['D1'] and out['item']['waiting_after_this'] == 2
    d2 = chat['items'][1]['id']
    said = refused(lambda: chat['answer'](d2, 'approve', many=False))
    assert OPEN in said and 'One decision at a time' in said and chat['items'][0]['id'] in said and chat['answers'] == []
    out = chat['answer'](chat['items'][0]['id'], 'approve', many=False)
    assert ids(out) == ['D2'] and 'group' not in out and chat['answers'] == [(out['answered'], 'approve', '')]


def test_more_than_four_the_first_four_in_film_order_then_the_rest(chat):
    chat['add'](*(end(chat, f'D{n}') for n in range(1, 7)))
    out = chat['next'](many=True)
    assert ids(out) == ['D1', 'D2', 'D3', 'D4'] and out['waiting_after_this'] == 2
    for i in list(chat['items'][:4]):
        out = chat['answer'](i['id'], 'approve')
    assert ids(out) == ['D5', 'D6'] and len(chat['answers']) == 4                                              # the rest in the next message


def test_answers_in_any_order_each_recorded_on_its_own_and_one_left_is_handed_out_again(chat):
    chat['add'](*(end(chat, s) for s in ('D1', 'D2', 'D3')))
    d1, d2, d3 = (i['id'] for i in chat['items'])
    chat['next'](many=True)
    out = chat['answer'](d3, 'approve')
    assert out['answered'] == d3 and ids(out) == ['D1', 'D2'] and 'record those first' in out['then']         # nothing is shown again between two records
    out = chat['answer'](d1, 'reject', 'The arrow points the wrong way.')
    assert chat['answers'] == [(d3, 'approve', ''), (d1, 'reject', 'The arrow points the wrong way.')]        # one record per answer
    assert ids(out) == ['D2'] and 'group' not in out                                                           # the one not answered stays open: alone, as a single card
    chat['add'](end(chat, 'D4'))                                                                               # another became ready meanwhile
    assert ids(chat['next'](many=True)) == ['D2', 'D4']
    out = chat['answer'](chat['items'][1]['id'], 'approve')
    assert ids(out) == ['D2']
    out = chat['answer'](d2, 'approve')
    assert out['item'] is None and 'group' not in out and out['needed'] is False and len(chat['answers']) == 4


def test_a_reject_needs_its_words_and_does_not_hold_the_others(chat):
    chat['add'](*(end(chat, s) for s in ('D1', 'D2')))
    d1, d2 = (i['id'] for i in chat['items'])
    chat['next'](many=True)
    assert refused(lambda: chat['answer'](d1, 'reject')) == 'Ask the operator what to change in the still, in their words.'
    assert chat['answers'] == []
    chat['answer'](d2, 'approve')                                                                              # the other is recorded all the same
    out = chat['answer'](d1, 'reject', 'Too dark.')
    assert chat['answers'] == [(d2, 'approve', ''), (d1, 'reject', 'Too dark.')] and out['item'] is None


def test_an_answer_outside_the_group_is_refused_as_before(chat):
    chat['add'](*(end(chat, f'D{n}') for n in range(1, 6)))
    chat['next'](many=True)
    d5 = chat['items'][4]['id']
    said = refused(lambda: chat['answer'](d5, 'approve'))                                                      # the fifth was not handed out
    assert OPEN in said and 'One decision at a time' in said and chat['items'][0]['id'] in said and chat['answers'] == []
    assert OPEN in refused(lambda: chat['answer']('still-end:D9:' + 'a' * 10, 'approve'))                    # nor one that does not wait
    old = chat['items'][1]['id']
    chat['items'][1] = end(chat, 'D2')
    chat['items'][1]['id'] = 'still-end:D2:' + 'c' * 10                                                        # the still was replaced since the message: its old card is spent
    assert OPEN in refused(lambda: chat['answer'](old, 'approve')) and chat['answers'] == []


def test_another_kind_of_card_in_front_is_asked_first_and_alone(chat):
    q = card(chat, 'question:S4:1', 'question', 'S4: which wall is meant?', ('North', 'Other'), 'Ask the operator.')
    chat['add'](end(chat, 'D1'), end(chat, 'D2'))
    chat['next'](many=True)
    d1 = chat['items'][0]['id']
    chat['items'].insert(0, q)                                                                                 # an open question now comes first, as the server orders it
    assert OPEN in refused(lambda: chat['answer'](d1, 'approve')) and chat['answers'] == []
    out = chat['next'](many=True)
    assert ids(out) == ['S4'] and 'group' not in out
    out = chat['answer']('question:S4:1', 'north')
    assert ids(out) == ['D1', 'D2']
    chat['items'].insert(1, card(chat, 'parts:abc', 'parts', 'The shared parts: are they right?', ('Approve', 'Reject'), 'Ask.'))
    assert ids(chat['next'](many=True)) == ['D1', 'D2']                                                        # the end-frames that wait come together, whatever stands between them


def test_a_film_in_mid_step_with_one_item_handed_out_by_the_older_server_keeps_working(chat):
    chat['add'](*(end(chat, s) for s in ('D1', 'D2')))
    d1 = chat['items'][0]['id']
    chat['session']['chat_item'] = {'id': d1, 'at': '2026-11-20T09:00:00+00:00'}                              # as the older server wrote it
    out = chat['answer'](d1, 'approve')
    assert chat['answers'] == [(d1, 'approve', '')] and ids(out) == ['D2']


# ---------- B4b: layout drawings of AI video shots ----------

def test_layout_drawings_go_through_the_same_group(chat):
    chat['add'](*(layout(chat, s) for s in ('S1', 'S2', 'S3', 'S4', 'S5')))
    out = chat['next'](many=True)
    assert ids(out) == ['S1', 'S2', 'S3', 'S4'] and out['waiting_after_this'] == 1 and out['group']['kind'] == 'layout drawing' and '4 layout drawings' in out['group']['heading']
    assert out['group']['items'][1]['ask'] == 'S2: Is the shot laid out right in these two drawings?'
    s2 = chat['items'][1]['id']
    assert refused(lambda: chat['answer'](s2, 'correct')) == 'Ask the operator what is wrong in the drawing of the shot.'
    out = chat['answer'](s2, 'correct', 'The mason faces away from the wall.')
    assert chat['answers'] == [(s2, 'correct', 'The mason faces away from the wall.')] and ids(out) == ['S1', 'S3', 'S4', 'S5']


def test_reference_drawings_and_other_kinds_are_not_grouped(chat):
    ref = card(chat, 'drawing:E1:' + 'd' * 10, 'drawing', 'The kiln: are these reference drawings right?', ('Yes', 'Correct'), 'Ask.')
    chat['add'](ref, layout(chat, 'S1'), layout(chat, 'S2'))
    out = chat['next'](many=True)
    assert 'group' not in out and ids(out) == ['E1']
    assert CF._together(chat['items'][1:], True) == chat['items'][1:] and CF._together(chat['items'], True) == [ref] and CF._together([], True) == []
    assert sorted(CF.TOGETHER) == ['shot-drawing:', 'still-end:'] and CF.GROUP_MAX == 4                        # the question card takes four questions


def test_the_layout_drawings_wait_in_the_order_of_the_film(monkeypatch):
    p = plan(shot('S1', start=0), shot('S2', start=130), shot('S3', start=260))
    guide = lambda sha: {'sha256': sha, 'verdicts': [{'pass': True}], 'drawing': {'status': 'proposed', 'sha256': sha, 'views': [{'id': 'camera', 'labelled_key': 'k/' + sha}]}}
    s = {'guides': {'S3': guide('3' * 64), 'S1': guide('1' * 64), 'S2': guide('2' * 64)}}                      # written in another order than the film's; each passed its check
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    ctx = {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': USER, 'outputs': [], 'conn': None}
    items = CF._layout_items(ctx)   # VW-25 issue 14: their own function
    assert [i['id'].split(':')[:2] for i in items] == [['shot-drawing', 'S1'], ['shot-drawing', 'S2'], ['shot-drawing', 'S3']]
    assert all(any(i['id'].startswith(pre) for pre in CF.TOGETHER) for i in items)                             # the ids the group is keyed on
    # release 1 (a layout is checked before its card is shown) holds inside a group: a layout not yet checked, or whose check failed, is no card
    s['guides']['S1']['verdicts'] = []
    s['guides']['S3']['verdicts'] = [{'pass': True}, {'pass': False}]
    items = CF._layout_items(ctx)
    assert [i['id'].split(':')[1] for i in items] == ['S2'] and CF._together(items, True) == items
    s['guides']['S1']['verdicts'] = [{'pass': True}]                                                           # its check passed since: it joins the next message
    s['guides']['S2']['rounds_before'] = 1                                                                     # a rebuilt layout says so on its own entry
    items = CF._layout_items(ctx)
    assert [i['id'].split(':')[1] for i in CF._together(items, True)] == ['S1', 'S2']
    assert [G.REDRAWN in CF._entry(i)['text'] for i in items] == [False, True]
