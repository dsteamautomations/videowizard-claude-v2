"""design/217: the page file holds step 6 ("Pictures and drawn graphics") as a third layout of the sets screen's frame, and holds none of its words:
every label, sentence and button of the screen comes from the round (`lines`, `layout.words.pictures`, `layout.coming`). No amount anywhere (D1).
The drawing in a browser is checked by `server/unit/test_design217_browser_pure.py`."""
import json
import re

from conftest import PLUGIN

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


def test_no_amount_of_money_in_the_page():
    part = _pictures_part(PAGE.read_text(encoding='utf-8'))
    assert not re.search(r'[₹$€£]\s?\d|\b(price|cost|paid|rupee|dollar)', part, re.I)
