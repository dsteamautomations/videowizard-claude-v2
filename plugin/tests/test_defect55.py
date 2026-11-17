"""Defect 55 (VW-24, 17 Nov 2026), the tool's side, with the server faked. The server now gives a picture whose content changed under the
same storage key a new code and new names for its two sizes; the tool, unchanged, then fetches it again, writes a new `pics/<code>` document
and offers a new large file, and matches nothing by an older name. The files the helpers open (`work/visuals/sets/<thing>/input-N`,
`picture-N`; `work/ref-<id>.png`; `work/chat/<name>`) are fetched at every call: a kept file is reused only with the server's fingerprint."""
import hashlib
import json

from test_design210_pictures import LINE, code, fake, page
from test_design211b_round import DUE, server
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw


def picture(n, mark):
    """One picture as the server lists it: its code and the names of its two sizes carry the content's mark."""
    key = 'run-1/visuals/references/set-1.png'
    return {'code': code(n), 'thumb': f'{key}.{mark}.page-thumb.jpg', 'zoom': f'{key}.{mark}.page-zoom.jpg'}


def round_(rnd, n, mark):
    return {**page(rnd, ({**LINE, 'pics': [{'code': code(n), 'label': 'A'}]},)), 'step': 'Reference sets', 'pictures': [picture(n, mark)]}


def test_a_picture_made_again_under_its_key_is_fetched_and_handed_over_again(harness, monkeypatch, capsys):
    ws, _ = harness
    rounds = [round_('r1', 1, 'aaaaaaaaaa'), round_('r2', 1, 'aaaaaaaaaa'), round_('r3', 2, 'bbbbbbbbbb')]   # r3: the same key, other content: a new code
    got = fake(monkeypatch, lambda: rounds.pop(0))
    folder = ws / 'work' / 'page'
    run(args(what='page', record=False), capsys)
    rc, out, err = run(args(what='page', record=False), capsys)
    assert len(got) == 2 and 'picture_batches' not in out                                # the same content: fetched once, sent once
    rc, out, err = run(args(what='page', record=False), capsys)
    assert got[2:] == [picture(2, 'bbbbbbbbbb')['thumb'], picture(2, 'bbbbbbbbbb')['zoom']]
    assert [w['doc_id'] for w in out['picture_batches'][0]] == [code(2)] and str(folder / 'zoom' / f'{code(2)}.jpg') in out['zoom_uploads'][0]
    assert b'bbbbbbbbbb' in (folder / 'zoom' / f'{code(2)}.jpg').read_bytes() and b'aaaaaaaaaa' in (folder / 'zoom' / f'{code(1)}.jpg').read_bytes()
    assert json.loads((folder / 'pictures.json').read_text(encoding='utf-8'))['thumbs'] == [code(1), code(2)]


class Api:
    """The server's file link, answering with the picture stored now."""
    def __init__(self, data):
        self.data, self.asked = data, []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, follow_redirects=False):
        self.asked.append(url)
        return type('R', (), {'status_code': 200, 'content': self.data, 'headers': {}})()


def test_a_kept_file_is_reused_only_with_the_servers_fingerprint(harness, monkeypatch):
    ws, _ = harness
    m = {'code': 'VW-9', 'run_id': 'run-1'}
    api = Api(b'made today')
    monkeypatch.setattr(vw, 'api', lambda: api)
    for rel in ('work/visuals/sets/STREET/picture-1.jpg', 'work/ref-abc.png', 'work/chat/STREET-1.png'):   # what the set-look helper, `vw visuals fetch --ref` and the chat open
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_bytes(b'made yesterday')
        vw._download(m, 'run-1/visuals/references/abc.png', rel)
        assert (ws / rel).read_bytes() == b'made today', rel
    asked = len(api.asked)
    rel = 'work/ref-abc.png'
    vw._download(m, 'run-1/visuals/references/abc.png', rel, expect={'sha256': hashlib.sha256(b'made today').hexdigest()})
    assert len(api.asked) == asked                                                       # the same content: kept
    (ws / rel).write_bytes(b'made yesterday')
    vw._download(m, 'run-1/visuals/references/abc.png', rel, expect={'sha256': hashlib.sha256(b'made today').hexdigest()})
    assert len(api.asked) == asked + 1 and (ws / rel).read_bytes() == b'made today'      # other content under the same name: fetched again


def test_the_pictures_of_a_look_are_fetched_at_every_call(harness, monkeypatch, capsys):
    ws, _ = harness
    server(monkeypatch, {}, get=DUE)
    fetched = []
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: fetched.append(rel) or str(ws / rel))
    run(args(what='round', looks=True), capsys)
    first = list(fetched)
    run(args(what='round', looks=True), capsys)
    assert first and fetched == first * 2 and all(rel.startswith('work/visuals/sets/STREET/') for rel in first)
