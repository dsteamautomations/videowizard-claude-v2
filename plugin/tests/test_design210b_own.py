"""design/210 part 2: the reference round on the artifact page, with the server faked. The operator's own picture, added on the page, is
fetched from the page's file store by the assistant (the Artifact tool's read, into work/page/own/), handed to the server through the same
calls as `vw visuals likeness` and `vw visuals own`, and only then is its line's answer recorded; a picture that cannot be handed over is
said on its line and the other answers are still recorded. The guard lets that one read through. The page file draws the two screens."""
import base64
import json

from conftest import PLUGIN
from test_design204_cli import page
from test_design204_page import active, guard
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

PAGE = PLUGIN / 'pages' / 'decisions.html'
URL = 'https://claude.ai/artifact/abc'
ID, ID2 = 'a' * 32, 'b' * 32
NEXT = {'recorded': [], 'kept': [], 'stale': [], 'refused': [], 'dropped': [], 'then': 'T.'}


def doc(key, item, choice, **more):
    return {'key': key, 'item': item, 'choice': choice, 'notes': '', 'at': 'x', **more}


def own(ident=ID, **more):
    return {'id': ident, 'url': '/_blob/' + ident, 'name': 'my kiln.jpg', 'type': 'image/jpeg', 'size': 5, **more}


def begin(ws, monkeypatch, capsys, docs, own_ok=True):
    """A round on the page, the operator's answers saved as the list of the page's answers; the server's calls are recorded."""
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: page('r1'))
    run(args(what='page', record=False), capsys)
    folder = ws / 'work' / 'page' / 'answers' / 'rounds' / 'r1' / 'answers'
    folder.mkdir(parents=True)
    for n, d in enumerate(docs, 1):
        (folder / f'l{n:02d}.json').write_text(json.dumps(d), encoding='utf-8')
    calls = []

    def request(method, path, wait=None, **kw):
        calls.append((path.rsplit('/visuals/', 1)[-1], kw['json']))
        if path.endswith('/own'):
            return ({'id': 'own-1', 'kind': 'supplied'}, 0) if own_ok else ({'action': 'refused', 'message': 'That file is not a picture this page can read: use a PNG, JPEG or WebP image.'}, 2)
        return {'likeness': True}, 0

    def write(path, body, wait=None):
        calls.append((path.rsplit('/visuals/', 1)[-1], body))
        return {**NEXT, 'page': page('r' + str(len(calls) + 1))}
    monkeypatch.setattr(vw, 'request', request)
    monkeypatch.setattr(vw, 'write', write)
    return calls


def record(capsys):
    return run(args(what='page', record=True), capsys)


def sent(calls, n=-1):
    return [c for c in calls if c[0] == 'page/record'][n][1]['answers']


def test_an_own_picture_not_fetched_yet_is_listed_and_the_rest_is_recorded(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=own()), doc('ref:E2', 'round1:E2', 'approve')])
    rc, out, err = record(capsys)
    folder = ws / 'work' / 'page' / 'own'
    assert rc == 0 and [c[0] for c in calls] == ['page/record'] and sent(calls) == [{'line': 'l02', 'key': 'ref:E2', 'item': 'round1:E2', 'choice': 'approve', 'notes': ''}]
    assert out['own_fetch'] == [ID] and out['own_dir'] == str(folder) and folder.is_dir()
    assert 'action "read"' in err and f'`path` {ID}' in err and str(folder) in err and '`vw visuals page --record` again' in err and 'Nothing is recorded for' in err
    assert [a['key'] for a in json.loads((folder / 'pending.json').read_text(encoding='utf-8'))] == ['ref:E1']


def test_a_fetched_picture_goes_to_the_server_as_vw_visuals_own_does_and_then_its_line_is_recorded(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=own(), notes='the side with the door')])
    record(capsys)
    folder = ws / 'work' / 'page' / 'own'
    (folder / f'{ID}.jpg').write_bytes(b'\xff\xd8pic')
    rc, out, err = record(capsys)
    names = [c[0] for c in calls]
    assert rc == 0 and names == ['page/record', 'own', 'page/record'] and sent(calls, 0) == []
    body = calls[1][1]
    assert body['element_id'] == 'E1' and base64.b64decode(body['content_base64']) == b'\xff\xd8pic' and body['name'] == 'my kiln.jpg' and body['url'] == '' and body['request_id']
    assert sent(calls) == [{'line': 'l01', 'key': 'ref:E1', 'item': 'round1:E1', 'choice': 'own', 'notes': 'the side with the door', 'own_ref': 'own-1'}]
    assert 'own_fetch' not in out and not (folder / 'pending.json').exists()
    rc, out, err = record(capsys)   # nothing is sent twice
    assert [c[0] for c in calls][3:] == ['page/record'] and sent(calls) == []


def test_a_picture_already_in_the_folder_is_handed_over_at_the_first_done(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('set:E2', 'set:E2:R1', 'own', own=own(type='image/png'))])
    folder = ws / 'work' / 'page' / 'own'
    folder.mkdir(parents=True)
    (folder / f'{ID}.png').write_bytes(b'png')
    rc, out, err = record(capsys)
    assert [c[0] for c in calls] == ['own', 'page/record'] and calls[0][1]['element_id'] == 'E2' and sent(calls)[0]['own_ref'] == 'own-1' and 'own_fetch' not in out


def test_a_persons_permission_is_recorded_first_with_the_operators_words(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:P1', 'round1:P1', 'own', own=own(), permission='  She said yes  on the phone. ')])
    folder = ws / 'work' / 'page' / 'own'
    folder.mkdir(parents=True)
    (folder / f'{ID}.jpeg').write_bytes(b'jpg')
    record(capsys)
    assert [c[0] for c in calls] == ['likeness', 'own', 'page/record']
    assert calls[0][1]['element_id'] == 'P1' and calls[0][1]['quote'] == 'She said yes on the phone.' and calls[0][1]['stand_in'] is False
    assert sent(calls)[0]['own_ref'] == 'own-1' and 'permission' not in sent(calls)[0] and 'own' not in sent(calls)[0]


def test_a_refusal_of_the_server_is_said_on_the_line_and_the_other_answers_are_still_recorded(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:P1', 'round1:P1', 'own', own=own()), doc('ref:E2', 'round1:E2', 'ignore')], own_ok=False)
    folder = ws / 'work' / 'page' / 'own'
    folder.mkdir(parents=True)
    (folder / f'{ID}.webp').write_bytes(b'webp')
    record(capsys)
    got = sent(calls)
    assert [c[0] for c in calls] == ['own', 'page/record'] and [a['key'] for a in got] == ['ref:P1', 'ref:E2']   # no words of permission on the page: none is recorded for them
    assert got[0]['own_error'] == 'That file is not a picture this page can read: use a PNG, JPEG or WebP image.' and 'own_ref' not in got[0] and 'own_error' not in got[1]


def test_a_file_of_a_wrong_type_or_too_large_never_leaves_the_machine(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=own()), doc('ref:E2', 'round1:E2', 'own', own=own(ID2))])
    folder = ws / 'work' / 'page' / 'own'
    folder.mkdir(parents=True)
    (folder / f'{ID}.gif').write_bytes(b'gif')
    (folder / f'{ID2}.png').write_bytes(b'x' * 20)
    monkeypatch.setattr(vw, 'OWN_PICTURE_MAX', 10)
    record(capsys)
    got = sent(calls)
    assert [c[0] for c in calls] == ['page/record'] and 'PNG, JPEG or WebP' in got[0]['own_error'] and 'larger than 15 MB' in got[1]['own_error']


def test_an_id_that_is_not_an_id_is_refused_and_never_fetched(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=own('../../secret')), doc('ref:E2', 'round1:E2', 'own')])
    rc, out, err = record(capsys)
    got = sent(calls)
    assert 'own_fetch' not in out and [c[0] for c in calls] == ['page/record'] and all('no picture' in a['own_error'] for a in got) and len(got) == 2


def test_a_picture_that_never_arrives_is_said_on_its_line_at_the_second_done(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=own())])
    record(capsys)
    rc, out, err = record(capsys)   # the fetch failed: no file
    assert 'could not be fetched' in sent(calls)[0]['own_error'] and 'own_fetch' not in out and not (ws / 'work' / 'page' / 'own' / 'pending.json').exists()


def test_an_answer_given_again_on_the_new_round_replaces_the_one_that_waited(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'own', own=own())])
    record(capsys)
    rnd = (ws / 'work' / 'page' / 'current.txt').read_text(encoding='utf-8').strip()
    folder = ws / 'work' / 'page' / 'answers' / 'rounds' / rnd / 'answers'
    folder.mkdir(parents=True)
    (folder / 'l01.json').write_text(json.dumps(doc('ref:E1', 'round1:E1', 'ignore')), encoding='utf-8')
    record(capsys)
    assert [(a['key'], a['choice']) for a in sent(calls)] == [('ref:E1', 'ignore')]


def test_what_is_kept_and_what_comes_next_are_said(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {**page('r1'), 'step': 'References: the sets', 'then': 'WAIT 900.'})
    rc, out, err = run(args(what='page', record=False), capsys)
    assert out['then'] == 'WAIT 900.' and 'WAIT 900.' in err
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {**NEXT, 'kept': ['ref:E2'], 'page': page('r2')})
    rc, out, err = record(capsys)
    assert out['kept'] == ['ref:E2'] and 'kept, not recorded yet: ref:E2' in err


def test_a_reference_asked_in_the_chat_points_to_the_page(harness, monkeypatch, capsys):
    item = {'id': 'round1:E1', 'kind': 'reference', 'position': 'References, 1 of 3', 'question': 'Plinth: use it?', 'buttons': [{'label': 'Yes, use it', 'choice': 'approve'}], 'how': 'HOW', 'show': []}
    for ident in ('round1:E1', 'set:E2:R1', 'setmake:E2', 'likeness:P1:R2'):
        monkeypatch.setattr(vw, 'write', lambda path, body, wait=None, ident=ident: {'item': {**item, 'id': ident}})
        assert run(args(what='next', one=False), capsys)[2].startswith('The references are answered on the page, in one visit: run `vw visuals page` instead; ask here only where the page cannot be shown. ')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'item': {**item, 'id': 'still:S1:x'}})
    assert 'on the page' not in run(args(what='next', one=False), capsys)[2]


# ---------- the guard ----------

def test_the_operators_own_picture_is_read_into_the_runs_own_folder_and_nothing_else_is_read(tmp_path):
    folder = active(tmp_path)
    ok = {'action': 'read', 'url': URL, 'path': ID, 'out_dir': str(folder / 'own')}
    assert guard('Artifact', ok, tmp_path)[0] == 0
    for bad in ({**ok, 'url': ''}, {k: v for k, v in ok.items() if k != 'url'}, {**ok, 'path': 'index.html'}, {**ok, 'path': ID.upper()}, {**ok, 'path': ID + 'a'}, {**ok, 'path': ID[:-1]},
                {k: v for k, v in ok.items() if k != 'path'}, {k: v for k, v in ok.items() if k != 'out_dir'}, {**ok, 'out_dir': str(folder)}, {**ok, 'out_dir': str(folder / 'zoom')},
                {**ok, 'out_dir': str(tmp_path / 'own')}, {**ok, 'out_dir': str(folder / 'own' / '..' / '..' / '..' / 'out')}, {**ok, 'paths': [ID]}, {**ok, 'page': True},
                {**ok, 'type_url': 'x'}, {'action': 'read', 'url': URL}, {'action': 'list'}, {'action': 'delete', 'url': URL, 'path': ID}):
        rc, err = guard('Artifact', bad, tmp_path)
        assert rc == 2 and 'decisions page' in err, bad
    assert guard('Artifact', {**ok, 'out_dir': str(folder / 'own' / 'sub')}, tmp_path)[0] == 2   # the folder itself, nothing under or over it


def test_without_an_active_run_nothing_is_read_from_a_page(tmp_path):
    assert guard('Artifact', {'action': 'read', 'url': URL, 'path': ID, 'out_dir': str(tmp_path / 'runs' / 'VW-3' / 'work' / 'page' / 'own')}, tmp_path)[0] == 2


# ---------- the page file ----------

def test_the_page_draws_the_two_screens_of_the_reference_round():
    html = PAGE.read_text(encoding='utf-8')
    for needed in ("claude.use('assets')", 'assets.upload(', "line.state==='making'", "'Being made'", 'line.kept', "'Kept: '", 'line.comment', 'Add a comment (optional)',
                   'p.choice', "'Chosen'", "'Choose '", 'aria-pressed', 'Use my own picture', "'Remove my picture'", 'image/png,image/jpeg,image/webp', '15*1024*1024',
                   'This picture is larger than 15 MB', 'is not a PNG, JPEG or WebP picture', "Write first that you have this person's permission", 'The picture could not be added',
                   'own:', 'permission:', 'function thumbs(line,onChange)'):
        assert needed in html, needed
    assert 'innerHTML' not in html and html.count("claude.use('db')") == 1 and 'assets.delete' not in html   # old pictures are left in the page's file store
