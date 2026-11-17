"""design/210 part 1: pictures on the artifact page, with the server faked. `vw visuals page` fetches the two sizes of each picture once into
the run folder, hands the assistant ready-made batches for the small ones and upload lists for the large ones, reads the upload's answer by
file name, and offers each picture once. The guard lets these batches and uploads through from the run folder only. The page file draws a
row of small pictures and opens one large."""
import base64
import json

from conftest import PLUGIN
from test_design204_cli import LINE, page
from test_design204_page import active, guard
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

PAGE = PLUGIN / 'pages' / 'decisions.html'
URL = 'https://claude.ai/artifact/abc'


def code(n):
    return 'p%012x' % n


def pictures(*ns):
    return [{'code': code(n), 'thumb': f'run-1/visuals/d/{n}.png.page-thumb.jpg', 'zoom': f'run-1/visuals/d/{n}.png.page-zoom.jpg'} for n in ns]


def with_pics(rnd, *ns, **more):
    line = {**LINE, 'pics': [{'code': code(n), 'label': f'Sheet {n}'} for n in ns]}
    return {**page(rnd, (line,)), 'step': 'Reference drawings', 'pictures': pictures(*ns), **more}


def fake(monkeypatch, answer, size=20):
    """The server faked: `answer()` is the page; a download writes `size` bytes named after its key. Returns the keys downloaded."""
    got = []

    def download(m, key, rel, expect=None):
        got.append(key)
        dest = vw.workspace(m['code']) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((b'\xff\xd8' + key.encode()).ljust(size, b'x'))
        return str(dest)
    monkeypatch.setattr(vw, '_download', download)
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: answer())
    return got


def answer_line(path, blob, ident=None):
    return f'- "{json.dumps(str(path))[1:-1]}" (175437 bytes, image/jpeg) → "/_blob/{blob}" (id {ident or blob})'


def test_each_picture_is_one_small_document_and_one_large_file_named_by_its_code(harness, monkeypatch, capsys):
    ws, _ = harness
    got = fake(monkeypatch, lambda: with_pics('r1', 1, 2))
    rc, out, err = run(args(what='page', record=False), capsys)
    folder = ws / 'work' / 'page'
    assert rc == 0 and sorted(got) == sorted(p[k] for p in pictures(1, 2) for k in ('thumb', 'zoom'))
    doc = json.loads((folder / 'pics' / f'{code(1)}.json').read_text(encoding='utf-8'))
    assert set(doc) == {'code', 'data'} and doc['code'] == code(1) and doc['data'].startswith('data:image/jpeg;base64,')
    assert base64.b64decode(doc['data'].split(',', 1)[1]).startswith(b'\xff\xd8run-1/visuals/d/1.png.page-thumb.jpg')
    assert sorted(p.name for p in (folder / 'pics').iterdir()) == [f'{code(1)}.json', f'{code(2)}.json']   # the downloaded small file is not kept beside its document
    assert sorted(p.name for p in (folder / 'zoom').iterdir()) == [f'{code(1)}.jpg', f'{code(2)}.jpg']
    assert out['picture_batches'] == [[{'op': 'set', 'collection': 'pics', 'doc_id': code(n), 'file_path': str(folder / 'pics' / f'{code(n)}.json')} for n in (1, 2)]]
    assert out['zoom_uploads'] == [[str(folder / 'zoom' / f'{code(n)}.jpg') for n in (1, 2)]] and out['uploaded_file'] == str(folder / 'uploaded.txt')
    assert 'Pictures first (step 2 of `how`): 2 small in 1 batch(es), 2 large in 1 upload(s).' in err
    assert 'pictures' not in json.loads((folder / 'r1.json').read_text(encoding='utf-8'))   # the round holds the lines, not where the pictures are stored


def test_nothing_is_downloaded_or_offered_twice_and_a_later_round_sends_only_the_new_pictures(harness, monkeypatch, capsys):
    ws, _ = harness
    rounds = [with_pics('r1', 1, 2), with_pics('r2', 1, 2), with_pics('r3', 1, 2, 3)]
    got = fake(monkeypatch, lambda: rounds.pop(0))
    run(args(what='page', record=False), capsys)
    first = list(got)
    rc, out, err = run(args(what='page', record=False), capsys)
    assert got == first and 'picture_batches' not in out and out['zoom_uploads'] == [[str(ws / 'work' / 'page' / 'zoom' / f'{code(n)}.jpg') for n in (1, 2)]]   # the large ones are offered until uploaded
    rc, out, err = run(args(what='page', record=False), capsys)
    assert len(got) == 6 and [w['doc_id'] for w in out['picture_batches'][0]] == [code(3)] and len(out['zoom_uploads'][0]) == 3


def test_the_batches_keep_to_forty_writes_and_to_the_size_limit(harness, monkeypatch, capsys):
    fake(monkeypatch, lambda: with_pics('r1', *range(1, 96)))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert [len(b) for b in out['picture_batches']] == [40, 40, 15] and [len(u) for u in out['zoom_uploads']] == [25, 25, 25, 20]
    assert [w['doc_id'] for b in out['picture_batches'] for w in b] == [code(n) for n in range(1, 96)]


def test_large_small_pictures_are_split_by_bytes(harness, monkeypatch, capsys):
    from pathlib import Path
    fake(monkeypatch, lambda: with_pics('r1', *range(1, 31)), size=100_000)   # each document is about 133 KB of text
    rc, out, err = run(args(what='page', record=False), capsys)
    sizes = [sum(Path(w['file_path']).stat().st_size for w in b) for b in out['picture_batches']]
    assert len(out['picture_batches']) > 1 and max(sizes) <= 900_000 and sum(len(b) for b in out['picture_batches']) == 30


def uploaded(ws, monkeypatch, capsys, lines, ns=(1, 2, 3)):
    fake(monkeypatch, lambda: with_pics('r1', *ns))
    run(args(what='page', record=False), capsys)
    f = ws / 'work' / 'page' / 'uploaded.txt'
    f.write_text('Uploaded files:\n' + '\n'.join(lines) + '\n', encoding='utf-8')
    return run(args(what='page', record=False, uploaded=str(f)), capsys)


def test_the_uploads_answer_is_matched_by_file_name_whatever_the_order(harness, monkeypatch, capsys):
    ws, _ = harness
    zoom = ws / 'work' / 'page' / 'zoom'
    ids = {n: f'{n:032x}' for n in (1, 2, 3)}
    rc, out, err = uploaded(ws, monkeypatch, capsys, [answer_line(zoom / f'{code(n)}.jpg', ids[n]) for n in (3, 1, 2)])
    docs = ws / 'work' / 'page' / 'zoomdocs'
    assert rc == 0 and out['matched'] == [code(1), code(2), code(3)] and out['refused'] == [] and out['not_uploaded'] == []
    assert json.loads((docs / f'{code(3)}.json').read_text(encoding='utf-8')) == {'code': code(3), 'url': '/_blob/' + ids[3]}
    assert out['picture_batches'] == [[{'op': 'set', 'collection': 'zoom', 'doc_id': code(n), 'file_path': str(docs / f'{code(n)}.json')} for n in (1, 2, 3)]]
    assert out['round_file'].endswith('r1.json') and '3 large picture(s) matched' in err and 'step 3' in err
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: with_pics('r2', 1, 2, 3))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert 'zoom_uploads' not in out and 'picture_batches' not in out and 'Pictures first' not in err   # all sent: nothing is offered again


def test_an_unknown_name_a_doubled_code_a_bad_id_and_an_unreadable_line_are_each_refused_by_name(harness, monkeypatch, capsys):
    ws, _ = harness
    zoom = ws / 'work' / 'page' / 'zoom'
    lines = [answer_line(zoom / 'pffffffffffff.jpg', 'a' * 32),                                      # not a picture of this run
             answer_line(zoom / f'{code(1)}.jpg', 'b' * 32), answer_line(zoom / f'{code(1)}.jpg', 'c' * 32),   # one code, two ids
             answer_line(zoom / f'{code(2)}.jpg', 'xyz'),                                            # not an id
             f'- "{zoom / (code(3) + ".jpg")}": not uploaded, the file is too large',               # no link on the line
             '- something else entirely']
    rc, out, err = uploaded(ws, monkeypatch, capsys, lines)
    names = [r['name'] for r in out['refused']]
    assert rc == 0 and out['matched'] == [] and 'picture_batches' not in out and not (ws / 'work' / 'page' / 'zoomdocs').exists()
    assert names == ['pffffffffffff.jpg', f'{code(1)}.jpg', f'{code(2)}.jpg', f'{code(3)}.jpg', '- something else entirely'] and all(r['why'] for r in out['refused'])
    assert out['not_uploaded'] == [code(1), code(2), code(3)] and 'pffffffffffff.jpg' in err and 'large pictures are not available' in err
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: with_pics('r2', 1, 2, 3))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert len(out['zoom_uploads'][0]) == 3   # not uploaded: offered again


def test_a_picture_matched_once_stays_and_the_same_line_twice_is_one_picture(harness, monkeypatch, capsys):
    ws, _ = harness
    zoom = ws / 'work' / 'page' / 'zoom'
    line = answer_line(zoom / f'{code(1)}.jpg', 'd' * 32)
    rc, out, err = uploaded(ws, monkeypatch, capsys, [line, line])
    assert out['matched'] == [code(1)] and out['refused'] == [] and out['not_uploaded'] == [code(2), code(3)]


def test_the_uploads_answer_file_must_exist(harness, monkeypatch, capsys):
    rc, out, err = run(args(what='page', record=False, uploaded='work/page/none.txt'), capsys)
    assert rc == 2 and 'none.txt' in out['message']


def test_pictures_again_and_a_new_link_offer_every_picture_once_more(harness, monkeypatch, capsys):
    ws, _ = harness
    got = fake(monkeypatch, lambda: with_pics('r1', 1, 2))
    run(args(what='page', record=False), capsys)
    rc, out, err = run(args(what='page', record=False, pictures_again=True), capsys)
    assert len(out['picture_batches'][0]) == 2 and len(out['zoom_uploads'][0]) == 2 and len(got) == 4   # offered again; nothing downloaded again
    run(args(what='page', url=URL, record=False), capsys)
    assert 'picture_batches' not in run(args(what='page', record=False), capsys)[1]
    run(args(what='page', url=URL, record=False), capsys)   # the same link again (published again in place): its pictures are still there
    assert 'picture_batches' not in run(args(what='page', record=False), capsys)[1]
    run(args(what='page', url='https://claude.ai/artifact/new', record=False), capsys)   # another page: it holds no picture yet
    assert len(run(args(what='page', record=False), capsys)[1]['picture_batches'][0]) == 2


def test_a_picture_the_server_could_not_prepare_is_named_and_a_code_that_is_not_a_code_is_left_out(harness, monkeypatch, capsys):
    odd = with_pics('r1', 1, pictures_failed=['Thing 1: Side'])
    odd['pictures'].append({'code': '../../x', 'thumb': 'k', 'zoom': 'k'})
    got = fake(monkeypatch, lambda: odd)
    rc, out, err = run(args(what='page', record=False), capsys)
    assert rc == 0 and len(got) == 2 and out['pictures_failed'] == ['Thing 1: Side'] and 'could not be prepared' in err and 'Thing 1: Side' in err


def test_a_round_with_no_pictures_is_as_before(harness, monkeypatch, capsys):
    ws, _ = harness
    got = fake(monkeypatch, lambda: page('r1'))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert rc == 0 and got == [] and not {'picture_batches', 'zoom_uploads', 'uploaded_file', 'pictures_failed'} & set(out) and 'Pictures first' not in err
    assert sorted(p.name for p in (ws / 'work' / 'page').iterdir()) == ['current.txt', 'r1.json']


def test_the_round_after_a_record_carries_its_new_pictures(harness, monkeypatch, capsys):
    ws, _ = harness
    fake(monkeypatch, lambda: with_pics('r1', 1))
    run(args(what='page', record=False), capsys)
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'recorded': [], 'stale': [], 'refused': [], 'dropped': [], 'then': 'T.', 'page': with_pics('r2', 1, 2)})
    rc, out, err = run(args(what='page', record=True), capsys)
    assert rc == 0 and [w['doc_id'] for w in out['picture_batches'][0]] == [code(2)] and 'Pictures first' in err


def test_publishing_again_passes_the_capabilities_again_and_a_drawing_in_the_chat_points_to_the_page(harness, monkeypatch, capsys):
    assert '`capabilities` again, exactly as given' in vw.REPUBLISH
    item = {'id': 'drawing:E1:abc', 'kind': 'drawing', 'position': 'Reference drawings, 1 of 1', 'question': 'The wall: are these reference drawings right?', 'buttons': [{'label': 'Yes', 'choice': 'yes'}],
            'how': 'HOW', 'show': []}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'item': dict(item)})
    assert run(args(what='next', one=False), capsys)[2].startswith('The reference drawings are approved on the page, in one visit: run `vw visuals page` instead; ask here only where the page cannot be shown. ')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'item': {**item, 'id': 'shot-drawing:S1:abc'}})
    assert 'on the page' not in run(args(what='next', one=False), capsys)[2]


# ---------- the guard ----------

def batch(folder, **more):
    return {'action': 'batch', 'url': URL, 'writes': [{'op': 'set', 'collection': 'pics', 'doc_id': 'p1', 'file_path': str(folder / 'pics' / 'p1.json')},
                                                      {'op': 'set', 'collection': 'zoom', 'doc_id': 'p1', 'file_path': str(folder / 'zoomdocs' / 'p1.json')}], **more}


def test_a_batch_of_picture_files_from_the_run_folder_is_allowed_and_nothing_else(tmp_path):
    folder = active(tmp_path)
    assert guard('ArtifactData', batch(folder), tmp_path)[0] == 0
    one = batch(folder)['writes'][0]
    for bad in ([], None, 'x', [{**one, 'op': 'delete'}], [{**one, 'op': 'update'}], [{**one, 'collection': 'rounds'}], [{**one, 'collection': 'pics/x/y'}], [{**one, 'data': {'x': 1}}],
                [{k: v for k, v in one.items() if k != 'file_path'}], [{**one, 'file_path': str(tmp_path / 'elsewhere.json')}], [one, 'x'], [one, {**one, 'file_path': str(tmp_path / 'x.json')}]):
        rc, err = guard('ArtifactData', {'action': 'batch', 'url': URL, 'writes': bad}, tmp_path)
        assert rc == 2 and 'picture' in err, bad
    assert guard('ArtifactData', {'action': 'batch', 'url': URL}, tmp_path)[0] == 2


def test_only_the_runs_large_pictures_are_uploaded_and_only_to_a_page(tmp_path):
    folder = active(tmp_path)
    zoom = folder / 'zoom'
    ok = {'action': 'publish', 'url': URL, 'asset': True, 'file_paths': [str(zoom / 'p1.jpg'), str(zoom / 'p2.jpg')]}
    assert guard('Artifact', ok, tmp_path)[0] == 0
    assert guard('Artifact', {'action': 'publish', 'url': URL, 'asset': True, 'file_path': str(zoom / 'p1.jpg')}, tmp_path)[0] == 0
    assert guard('Artifact', {'url': URL, 'asset': True, 'file_paths': [str(zoom / 'p1.jpg')]}, tmp_path)[0] == 0
    for bad in ({**ok, 'url': ''}, {**ok, 'action': 'delete'}, {**ok, 'file_paths': []}, {**ok, 'file_paths': [str(zoom / 'p1.jpg'), str(folder / 'r1.json')]},
                {**ok, 'file_paths': [str(tmp_path / 'secret.jpg')]}, {**ok, 'file_paths': [str(zoom / '..' / '..' / '..' / 'out' / 'x.jpg')]}, {**ok, 'file_paths': 'x'},
                {**ok, 'from_url': 'https://claude.ai/artifact/other', 'asset_ids': ['a' * 32]}, {**ok, 'files': {'a.js': 'a.js'}}, {**ok, 'type_url': 'x'},
                {'action': 'publish', 'url': URL, 'asset': True}, {'action': 'publish', 'url': URL, 'asset': True, 'file_path': str(PAGE)}):
        rc, err = guard('Artifact', bad, tmp_path)
        assert rc == 2 and 'decisions page' in err, bad


def test_without_an_active_run_no_picture_is_sent(tmp_path):
    assert guard('Artifact', {'action': 'publish', 'url': URL, 'asset': True, 'file_paths': [str(tmp_path / 'runs' / 'VW-3' / 'work' / 'page' / 'zoom' / 'p1.jpg')]}, tmp_path)[0] == 2
    assert guard('ArtifactData', {'action': 'batch', 'url': URL, 'writes': []}, tmp_path)[0] == 2


# ---------- the page file ----------

def test_the_page_shows_a_lines_pictures_small_and_opens_one_large():
    html = PAGE.read_text(encoding='utf-8')
    for needed in ('function thumbs(line,onChange)', 'function openZoom(pics,i,opener)', 'function closeZoom()', "picDoc('pics',p.code,'data')", "picDoc('zoom',p.code,'url')",
                   'IntersectionObserver', 'The large picture is not available.', 'The buttons work when every picture of this line has shown.', 'A picture is missing: ',
                   "'Escape'", "'ArrowRight'", "'ArrowLeft'", "setAttribute('role','dialog')", "setAttribute('aria-modal','true')", 'opener.focus()', "'Previous'", "'Next'", "'Close'",
                   "/^\\/_blob\\/[0-9a-f]{32}$/", '/^data:image\\/(jpeg|png|webp);base64,/', 'if(line.pics&&line.pics.length) body.appendChild(pictures(line,check))',
                   "grid(['Fact','Value','From'],line.facts,'facts')", 'Assumed, with no source (say if any is wrong): '):
        assert needed in html, needed
    assert 'innerHTML' not in html and html.count("claude.use('db')") == 1
