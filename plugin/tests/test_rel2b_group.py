"""Release 2, B4 and B4b (SK, 20 Nov 2026): the tool says it can show a group (`many`), saves every entry's pictures and tells the assistant
the group in one line: the heading, each entry with its files, its question and its buttons, then the server's `how`. One item is told
exactly as before. With the server faked."""
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

BUTTONS = [{'label': 'Approve', 'choice': 'approve', 'description': 'It is right; go on'}, {'label': 'Reject', 'choice': 'reject', 'needs_words': True, 'description': 'I will ask you what is wrong with it'}]


def entry(sid):
    return {'id': f'still-end:{sid}:aaaaaaaaaa', 'kind': 'still end-frame', 'position': 'Step 6', 'name': sid, 'question': f'{sid}: is it right?', 'ask': f'{sid}: Is it right?',
            'message': '**Step 6**', 'text': '', 'show': [{'key': f'k/{sid}.png', 'name': f'{sid}-still-end.png'}], 'buttons': BUTTONS}


GROUP = {'item': None, 'group': {'kind': 'still end-frame', 'heading': '2 still end-frames of drawn graphics are ready.', 'items': [entry('D1'), entry('D2')]},
         'waiting_after_this': 0, 'needed': True, 'say_last': 'Your answer is needed.', 'how': 'HOW-GROUP'}


def faked(monkeypatch, answer):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path.rsplit('/', 1)[1], body)) or answer())
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: 'RUN/' + rel)
    return sent


def test_next_says_it_can_show_a_group_and_tells_every_entry_with_its_files_and_buttons(harness, monkeypatch, capsys):
    sent = faked(monkeypatch, lambda: {**GROUP, 'group': {**GROUP['group'], 'items': [entry('D1'), entry('D2')]}})
    code, out, err = run(args(what='next', one=False), capsys)
    assert code == 0 and sent == [('next', {'one': False, 'many': True})]
    assert [e['show_files'] for e in out['group']['items']] == [['RUN/work/chat/D1-still-end.png'], ['RUN/work/chat/D2-still-end.png']]   # every entry's pictures are saved
    assert err.startswith('2 still end-frames of drawn graphics are ready. Show them side by side in one message and ask one question for each: ')
    for sid in ('D1', 'D2'):
        assert (f'{sid} (item still-end:{sid}:aaaaaaaaaa): "{sid}: Is it right?" Files: RUN/work/chat/{sid}-still-end.png. Buttons: Approve [approve], Reject [reject].') in err
    assert err.strip().endswith('HOW-GROUP')


def test_decide_says_it_too_and_tells_the_group_that_is_left(harness, monkeypatch, capsys):
    sent = faked(monkeypatch, lambda: {'answered': 'still-end:D3:aaaaaaaaaa', 'choice': 'approve', 'then': 'THEN', **GROUP, 'group': {**GROUP['group'], 'items': [entry('D1'), entry('D2')]}})
    code, out, err = run(args(what='decide', item='still-end:D3:aaaaaaaaaa', choice='approve', quote='yes', notes=None, one=False), capsys)
    assert code == 0 and sent[0][0] == 'answer' and sent[0][1]['many'] is True and sent[0][1]['one'] is False
    assert err.startswith('Recorded. THEN 2 still end-frames of drawn graphics are ready.') and 'D2 (item still-end:D2:aaaaaaaaaa)' in err


def test_one_item_is_told_as_before(harness, monkeypatch, capsys):
    one = {**entry('D1'), 'how': 'HOW'}
    faked(monkeypatch, lambda: {'item': dict(one)})
    code, out, err = run(args(what='next', one=True), capsys)
    assert code == 0 and err.strip() == ('Step 6. Post `message` as it is, then ask `ask`: "D1: Is it right?" Files to show, in this order: RUN/work/chat/D1-still-end.png. '
                                         'Buttons: Approve [approve], Reject [reject]. HOW')
