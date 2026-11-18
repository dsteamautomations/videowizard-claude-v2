"""design/210, the review's findings (16 Nov 2026), the tool's side, with the server faked. 3: pictures offered again go to documents no
earlier batch wrote, and the round says which document holds each picture. 4: while the operator's own pictures are still to fetch, the tool
says only that. 5: the page calls wait longer, and a call that times out says what to do in one plain sentence."""
import json

import httpx

from conftest import PLUGIN
from test_design204_cli import page
from test_design210_pictures import answer_line, code, fake, with_pics
from test_design210b_own import NEXT, doc, own
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

PAGE = PLUGIN / 'pages' / 'decisions.html'
REQUEST = vw.request   # the tool's own, before the harness fakes it


def ids(out):
    return [w['doc_id'] for b in out.get('picture_batches') or [] for w in b]


def round_doc(out):
    return json.loads(open(out['round_file'], encoding='utf-8').read())


# ---------- fix 3: pictures sent again ----------

def test_a_first_send_is_as_before_the_document_is_the_code_and_the_round_names_none(harness, monkeypatch, capsys):
    fake(monkeypatch, lambda: with_pics('r1', 1, 2))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert ids(out) == [code(1), code(2)] and 'pic_docs' not in round_doc(out) and 'zoom_docs' not in round_doc(out)


def test_pictures_again_writes_every_picture_to_a_document_no_earlier_batch_used_and_the_round_names_it(harness, monkeypatch, capsys):
    ws, _ = harness
    folder = ws / 'work' / 'page'
    rounds = [with_pics('r1', 1, 2), with_pics('r2', 1, 2), with_pics('r3', 1, 2, 3), with_pics('r4', 1, 2, 3)]
    got = fake(monkeypatch, lambda: rounds.pop(0))
    used = ids(run(args(what='page', record=False), capsys)[1])
    rc, out, err = run(args(what='page', record=False, pictures_again=True), capsys)
    again = ids(out)
    assert again == [code(1) + '-1', code(2) + '-1'] and not set(again) & set(used) and len(got) == 4   # new documents; nothing downloaded again
    assert [w['file_path'] for w in out['picture_batches'][0]] == [str(folder / 'pics' / f'{code(n)}.json') for n in (1, 2)]   # the same files
    assert len(out['zoom_uploads'][0]) == 2
    names = {code(n): code(n) + '-1' for n in (1, 2)}
    assert round_doc(out)['pic_docs'] == names and round_doc(out)['zoom_docs'] == names
    f = folder / 'uploaded.txt'   # the large pictures uploaded again: their links go to new documents too
    f.write_text('\n'.join(answer_line(folder / 'zoom' / f'{code(n)}.jpg', f'{n:032x}') for n in (1, 2)) + '\n', encoding='utf-8')
    rc, up, err = run(args(what='page', record=False, uploaded=str(f)), capsys)
    assert [(w['collection'], w['doc_id']) for w in up['picture_batches'][0]] == [('zoom', code(1) + '-1'), ('zoom', code(2) + '-1')]
    used += again
    rc, out, err = run(args(what='page', record=False), capsys)   # a later round: only its new picture, and the round still names every document
    assert ids(out) == [code(3) + '-1'] and round_doc(out)['pic_docs'] == {code(n): code(n) + '-1' for n in (1, 2, 3)}
    used += ids(out)
    rc, out, err = run(args(what='page', record=False, pictures_again=True), capsys)   # and once more: new documents again
    assert ids(out) == [code(n) + '-2' for n in (1, 2, 3)] and not set(ids(out)) & set(used) and round_doc(out)['zoom_docs'][code(3)] == code(3) + '-2'


def test_a_page_published_at_a_new_link_starts_from_the_code_again(harness, monkeypatch, capsys):
    fake(monkeypatch, lambda: with_pics('r1', 1))
    run(args(what='page', url='https://claude.ai/artifact/abc', record=False), capsys)
    run(args(what='page', record=False), capsys)
    assert ids(run(args(what='page', record=False, pictures_again=True), capsys)[1]) == [code(1) + '-1']
    run(args(what='page', url='https://claude.ai/artifact/new', record=False), capsys)
    rc, out, err = run(args(what='page', record=False), capsys)
    assert ids(out) == [code(1)] and 'pic_docs' not in round_doc(out)


def test_the_page_reads_a_pictures_document_from_the_round():
    html = PAGE.read_text(encoding='utf-8')
    for needed in ("function docId(coll,code)", "round[coll==='pics'?'pic_docs':'zoom_docs']", "/^[pv][0-9a-f]{12}-[0-9]{1,4}$/", "db.doc(coll+'/'+docId(coll,code))",
                   "(line.pics||[]).map(p=>docId('pics',p.code))"):
        assert needed in html, needed
    assert 'innerHTML' not in html


def test_the_flag_is_offered_by_the_tool():
    text = (PLUGIN / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "'--pictures-again'" in text and 'under new document names: for a batch that failed or a picture that stays grey on the page' in text


# ---------- fix 4: own pictures still to fetch ----------

def test_while_own_pictures_are_to_fetch_only_the_fetch_is_said_and_no_new_round_is_handed_over(harness, monkeypatch, capsys):
    ws, _ = harness
    folder = ws / 'work' / 'page'
    fake(monkeypatch, lambda: page('r1'))
    run(args(what='page', record=False), capsys)
    answers = folder / 'answers' / 'rounds' / 'r1' / 'answers'
    answers.mkdir(parents=True)
    (answers / 'l01.json').write_text(json.dumps(doc('ref:E1', 'round1:E1', 'own', own=own())), encoding='utf-8')
    (answers / 'l02.json').write_text(json.dumps(doc('ref:E2', 'round1:E2', 'approve')), encoding='utf-8')
    then = '1 thing(s) still wait for the operator on the page: write the new round to the page and give them the link again.'
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {**NEXT, 'kept': ['ref:E2'], 'then': then, 'page': with_pics('r2', 1)})
    rc, out, err = run(args(what='page', record=True), capsys)
    assert rc == 0 and out['own_fetch'] == ['a' * 32] and out['own_dir'] == str(folder / 'own') and out['kept'] == ['ref:E2']
    assert '1 picture(s) the operator added on the page are still to fetch' in err and '`vw visuals page --record` again' in err and 'kept, not recorded yet: ref:E2' in err
    assert 'still wait' not in err and 'New round' not in err and 'Pictures first' not in err   # one instruction, not two that disagree
    assert not {'then', 'round', 'round_file', 'picture_batches', 'zoom_uploads'} & set(out)
    assert (folder / 'current.txt').read_text(encoding='utf-8').strip() == 'r1' and not (folder / 'r2.json').exists() and not (folder / 'pictures.json').exists()
    (folder / 'own' / ('a' * 32 + '.jpg')).write_bytes(b'\xff\xd8pic')   # fetched: the second "record" says what comes next and hands the round over, its pictures too
    monkeypatch.setattr(vw, 'request', lambda method, path, wait=None, **kw: ({'id': 'own-1'}, 0))
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {**NEXT, 'recorded': ['ref:E1'], 'then': 'NEXT STEP.', 'page': with_pics('r3', 1)})
    rc, out, err = run(args(what='page', record=True), capsys)
    assert 'own_fetch' not in out and out['then'] == 'NEXT STEP.' and 'NEXT STEP.' in err and 'New round r3' in err and ids(out) == [code(1)]


# ---------- fix 5: the page calls wait longer ----------

def test_the_page_calls_wait_five_minutes(harness, monkeypatch, capsys):
    waits = []

    def write(path, body, wait=None):
        waits.append((path.rsplit('/visuals/', 1)[-1], wait))
        return page('r1') if path.endswith('/page') else {**NEXT, 'page': page('r2')}
    monkeypatch.setattr(vw, 'write', write)
    run(args(what='page', record=False), capsys)
    run(args(what='page', record=True), capsys)
    assert waits == [('page', 300), ('page/record', 300)] and vw.PAGE_WAIT == 300


class Slow:
    """A server that does not answer in time."""
    seen = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def request(self, method, path, **kw):
        Slow.seen.append((path.rsplit('/visuals/', 1)[-1], kw.get('timeout')))
        raise httpx.ReadTimeout('too slow')


def test_a_page_call_that_times_out_says_what_to_do_in_one_plain_sentence(harness, monkeypatch, capsys):
    ws, _ = harness
    Slow.seen = []
    monkeypatch.setattr(vw, 'request', REQUEST)
    monkeypatch.setattr(vw, 'api', lambda: Slow())
    said = 'The page is still preparing its pictures on the server. Run `vw visuals page` again in a minute: nothing is lost.'
    rc, out, err = run(args(what='page', record=False), capsys)
    assert rc == 2 and out == {'action': 'wait', 'message': said} and err.strip() == said and Slow.seen == [('page', 300)]
    (ws / 'work' / 'page' / 'current.txt').write_text('r1\n', encoding='utf-8')
    rc, out, err = run(args(what='page', record=True), capsys)
    assert rc == 2 and out['message'] == said and Slow.seen[-1] == ('page/record', 300)
    payload, rc = REQUEST('POST', '/api/runs/run-1/visuals/prepare', 600, json={})   # every other long call says what it said before
    assert rc == 2 and 'still working on this after 600 s' in payload['message']
