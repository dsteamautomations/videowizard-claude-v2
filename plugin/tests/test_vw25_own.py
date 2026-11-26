"""VW-25 issues 10 and 11 (25 Nov 2026), the tool's side, with the server faked. An own answer of the page carries a list of up to three
pictures (`own`: [{id, name, ...}]); the older page's one picture (`own`: {id, ...}) is read as a list of one. Every picture is fetched and
handed to the server (`visuals/own`), a person's permission is recorded once before the first, and the answer then carries `own_refs`. One
picture that cannot be handed over is named in `own_error`; the others are still handed over, so they stay with the server. The operator's
comment travels as the answer's `notes` (the page), or with `vw visuals own --words` (the chat): the same server function takes both."""
import base64
import json

import pytest

from test_design210b_own import ID, ID2, begin, doc, own, record, sent
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
from test_visuals_page_actions_cli import posts
import vw

ID3, ID4 = 'c' * 32, 'd' * 32


def three():
    return [own(ID, name='front.jpg'), own(ID2, name='side.png'), own(ID3, name='top.webp')]


def files(ws, *names):
    folder = ws / 'work' / 'page' / 'own'
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        (folder / n).write_bytes(n.encode())
    return folder


def served(monkeypatch, calls, refuse=()):
    """The server's `visuals/own` gives each picture its own id; a name in `refuse` is refused with the server's sentence."""
    def request(method, path, wait=None, **kw):
        calls.append((path.rsplit('/visuals/', 1)[-1], kw['json']))
        if path.endswith('/own'):
            name = kw['json']['name']
            return ({'action': 'refused', 'message': refuse[name]}, 2) if name in refuse else ({'id': 'own-' + name, 'kind': 'supplied'}, 0)
        return {'likeness': True}, 0
    monkeypatch.setattr(vw, 'request', request)


def test_three_pictures_of_one_line_are_each_handed_over_and_the_answer_names_them_in_order(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=three(), notes='the kiln, from three sides')])
    served(monkeypatch, calls)
    files(ws, f'{ID}.jpg', f'{ID2}.png', f'{ID3}.webp')
    rc, out, err = record(capsys)
    assert rc == 0 and [c[0] for c in calls] == ['own', 'own', 'own', 'page/record'] and [c[1]['name'] for c in calls[:3]] == ['front.jpg', 'side.png', 'top.webp']
    assert base64.b64decode(calls[1][1]['content_base64']) == f'{ID2}.png'.encode() and all(c[1]['element_id'] == 'E1' and 'words' not in c[1] for c in calls[:3])
    assert sent(calls) == [{'line': 'l01', 'key': 'ref:E1', 'item': 'round1:E1', 'choice': 'own', 'notes': 'the kiln, from three sides',
                            'own_refs': ['own-front.jpg', 'own-side.png', 'own-top.webp']}]      # the comment is the answer's: one for the line


def test_the_older_pages_one_picture_is_a_list_of_one(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('set:E2', 'set:E2:R1', 'own', own=own(name='front.jpg'))])
    served(monkeypatch, calls)
    files(ws, f'{ID}.jpg')
    record(capsys)
    assert [c[0] for c in calls] == ['own', 'page/record'] and sent(calls)[0]['own_refs'] == ['own-front.jpg'] and 'own' not in sent(calls)[0] and 'own_error' not in sent(calls)[0]


def test_pictures_not_fetched_yet_are_all_listed_once_and_the_answer_waits_whole(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=three()), doc('ref:E2', 'round1:E2', 'ignore')])
    served(monkeypatch, calls)
    folder = files(ws, f'{ID}.jpg')                                                # one of the three is there already
    rc, out, err = record(capsys)
    assert out['own_fetch'] == [ID2, ID3] and [c[0] for c in calls] == ['page/record'] and [a['key'] for a in sent(calls)] == ['ref:E2']   # every other answer is recorded; nothing of the line is sent in part
    assert [a['key'] for a in json.loads((folder / 'pending.json').read_text(encoding='utf-8'))] == ['ref:E1']
    files(ws, f'{ID2}.png', f'{ID3}.webp')
    record(capsys)
    assert [c[0] for c in calls][1:] == ['own', 'own', 'own', 'page/record'] and sent(calls)[0]['own_refs'] == ['own-front.jpg', 'own-side.png', 'own-top.webp']
    assert not (folder / 'pending.json').exists()


def test_one_picture_the_server_refuses_among_three_is_named_and_the_other_two_are_handed_over(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=three()), doc('ref:E2', 'round1:E2', 'ignore')])
    served(monkeypatch, calls, refuse={'side.png': 'That file is not a picture this page can read: use a PNG, JPEG or WebP image.'})
    files(ws, f'{ID}.jpg', f'{ID2}.png', f'{ID3}.webp')
    record(capsys)
    got = sent(calls)
    assert [c[0] for c in calls] == ['own', 'own', 'own', 'page/record'] and [a['key'] for a in got] == ['ref:E1', 'ref:E2']
    assert got[0]['own_refs'] == ['own-front.jpg', 'own-top.webp']                                # the other two stay with the server
    assert got[0]['own_error'] == 'side.png: That file is not a picture this page can read: use a PNG, JPEG or WebP image.' and 'own_error' not in got[1]


def test_a_wrong_type_a_file_too_large_and_one_never_fetched_are_each_named_and_the_good_one_goes(harness, monkeypatch, capsys):
    ws, _ = harness
    four = three() + [own(ID4, name='late.jpg')]
    calls = begin(ws, monkeypatch, capsys, [doc('set:E1', 'set:E1:R1', 'own', own=four)])
    served(monkeypatch, calls)
    record(capsys)                                                                 # nothing fetched yet: the answer waits once
    folder = files(ws, f'{ID2}.gif')
    (folder / f'{ID}.jpg').write_bytes(b'small')
    (folder / f'{ID3}.webp').write_bytes(b'x' * 20)
    monkeypatch.setattr(vw, 'OWN_PICTURE_MAX', 10)
    record(capsys)
    got = sent(calls)[0]
    assert [c[0] for c in calls][1:] == ['own', 'page/record'] and got['own_refs'] == ['own-front.jpg']
    assert got['own_error'] == ('side.png: the file is not a PNG, JPEG or WebP picture; top.webp: the picture is larger than 15 MB: choose a smaller file; '
                                'late.jpg: the picture could not be fetched from the page')
    assert len(got['own_error']) <= 600


def test_a_persons_permission_is_recorded_once_before_the_first_picture(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:P1', 'round1:P1', 'own', own=[own(name='him.jpg')], permission='He said yes.', notes='He wears the cap low.')])
    served(monkeypatch, calls)
    files(ws, f'{ID}.jpg')
    record(capsys)
    assert [c[0] for c in calls] == ['likeness', 'own', 'page/record'] and calls[0][1]['quote'] == 'He said yes.'
    assert sent(calls)[0]['notes'] == 'He wears the cap low.' and sent(calls)[0]['own_refs'] == ['own-him.jpg'] and 'permission' not in sent(calls)[0]


def test_an_own_answer_with_no_picture_or_a_list_of_things_that_are_not_pictures_is_said_on_its_line(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=[], notes='only words'), doc('ref:E2', 'round1:E2', 'own', own=['x', {'id': '../../secret'}])])
    served(monkeypatch, calls)
    rc, out, err = record(capsys)
    got = sent(calls)
    assert 'own_fetch' not in out and [c[0] for c in calls] == ['page/record'] and all('no picture' in a['own_error'] and 'own_refs' not in a for a in got) and len(got) == 2


# ---------- the chat: `vw visuals own --words` ----------

def test_own_sends_the_operators_words_with_the_picture(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'in').mkdir()
    (ws / 'in' / 'kiln.jpg').write_bytes(b'\xff\xd8 a picture')
    sent_ = posts(monkeypatch, {'id': 'own1', 'kind': 'supplied', 'status': 'approved', 'element_id': 'E1', 'next': 'Your picture is saved and approved for E1.'})
    code, out, err = run(args(what='own', element='E1', file='in/kiln.jpg', words='  The door is on the   left side. '), capsys)
    assert code == 0 and sent_[0][1] == {'element_id': 'E1', 'content_base64': base64.b64encode(b'\xff\xd8 a picture').decode(), 'url': '', 'name': '', 'words': 'The door is on the left side.'}
    assert 'own' in vw.VISUALS_FLAGS and 'words' in vw.VISUALS_FLAGS['own']
    a = vw.build_parser().parse_args(['visuals', 'own', '--element', 'E1', '--file', 'in/kiln.jpg', '--words', 'The door is on the left side.'])
    assert a.words == 'The door is on the left side.' and not vw.visuals_flags_refused(a)


def test_own_refuses_words_over_300_characters_before_anything_is_sent(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'in').mkdir()
    (ws / 'in' / 'kiln.jpg').write_bytes(b'\xff\xd8 a picture')
    sent_ = posts(monkeypatch, {'id': 'own1'})
    code, out, err = run(args(what='own', element='E1', file='in/kiln.jpg', words='x' * 301), capsys)
    assert code == 2 and sent_ == [] and '300 characters' in out['message'] and 'nothing was sent' in out['message'].lower()
    code, out, err = run(args(what='own', element='E1', file='in/kiln.jpg', words='x' * 300), capsys)
    assert code == 0 and len(sent_[0][1]['words']) == 300
