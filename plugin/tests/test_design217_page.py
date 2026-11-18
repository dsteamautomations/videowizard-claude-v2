"""design/217: the page file holds step 6 ("Pictures and drawn graphics") as a third layout of the sets screen's frame, and holds none of its words:
every label, sentence and button of the screen comes from the round (`lines`, `layout.words.pictures`, `layout.coming`). No amount anywhere (D1).
The drawing in a browser is checked by `server/unit/test_design217_browser_pure.py`."""
import json
import re

from conftest import PLUGIN
from test_visuals_cli import harness   # noqa: F401 (a fixture)

PAGE = PLUGIN / 'pages' / 'decisions.html'
FIXTURE = PLUGIN.parent / 'server' / 'unit' / 'd217_pictures_round.json'


def _pictures_part(html):
    start = html.index('// ---------- design/217 (SK, 18 Nov 2026): step 6')
    return html[start:html.index('function sRestView')]


def test_the_pictures_layout_is_drawn_in_the_sets_frame():
    html = PAGE.read_text(encoding='utf-8')
    assert "kind==='pictures'" in html and "sets=kind==='sets'||kind==='pictures'" in html
    assert "W().pictures" in html and 'function pThing(l)' in html and "(round.layout||{}).coming" in html
    assert 'sAnswer(l,b.choice' in _pictures_part(html)        # answers through the one writer of the sets frame (`write`)


def test_the_page_holds_none_of_the_screens_words():
    html = PAGE.read_text(encoding='utf-8')
    part = _pictures_part(html)
    doc = json.loads(FIXTURE.read_text(encoding='utf-8'))
    words = list(doc['layout']['words']['pictures'].values())
    words = [w for w in words if isinstance(w, str)] + list(doc['layout']['words']['pictures']['done'].values())
    for l in doc['lines']:
        words += [b['label'] for b in l['buttons']] + [l['ask'], l['kind_words']] + ([l['check']['head']] if 'check' in l else [])
        words += [l[k] for k in ('held', 'finish', 'strip_head', 'foot_head', 'words_head', 'from') if l.get(k)]
    words += [c['note'] for c in doc['layout']['coming']]
    found = [w for w in set(words) if f"'{w}" in part or f'"{w}' in part or f'>{w}' in part]   # as a string of the page's own
    assert not found, found


def test_a_drawings_video_is_fetched_as_zoom_code_mp4_and_offered_again_under_the_rounds_document(harness, monkeypatch, capsys):
    """design/217: `videos` [{code, key}] of the server: the tool fetches each as zoom/<code>.mp4, uploads it with the large pictures, and when
    the pictures are offered again the round names the video's new document too (`zoom_docs`), as the page reads it (`docId`)."""
    from test_design210_pictures import fake, with_pics
    from test_design210_review import round_doc
    from test_visuals_cli import args, run
    ws, _ = harness
    vid = [{'code': 'v' + 'a' * 12, 'key': 'run-1/takes/j1.mp4.page.mp4'}]
    got = fake(monkeypatch, lambda: with_pics('r1', 1, videos=vid))
    rc, out, err = run(args(what='page', record=False), capsys)
    folder = ws / 'work' / 'page'
    assert rc == 0 and 'run-1/takes/j1.mp4.page.mp4' in got and (folder / 'zoom' / f"{vid[0]['code']}.mp4").is_file()
    assert str(folder / 'zoom' / f"{vid[0]['code']}.mp4") in out['zoom_uploads'][0] and 'videos' not in round_doc(out)
    rc, out, err = run(args(what='page', record=False, pictures_again=True), capsys)
    assert round_doc(out)['zoom_docs'][vid[0]['code']] == vid[0]['code'] + '-1'
    assert "/^[pv][0-9a-f]{12}-[0-9]{1,4}$/" in PAGE.read_text(encoding='utf-8')


def test_no_amount_of_money_in_the_page():
    part = _pictures_part(PAGE.read_text(encoding='utf-8'))
    assert not re.search(r'[₹$€£]\s?\d|\b(price|cost|paid|rupee|dollar)', part, re.I)
