"""design/210 part 1 (SK, 16 Nov 2026): pictures on the Claude artifact page, and the first step that uses them, the reference drawings.
A line names its pictures (`pics`: a code and a label each); the page's answer lists once, under `pictures`, the two sizes the server made of
each (a small one and a large one, never cropped). The reference drawings step comes after the drawings and materials: each line is the
chat's own item, answered through its own run function. Without a database: the harness of tests/check_shared_change.py."""
import hashlib
import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
from app import chat_flow as C, page_flow as P, visuals_stage as V   # noqa: E402
from test_design209_pure import PANEL, ans, by_key, page, plan_with, record, start   # noqa: E402

STEP = 'Reference drawings'


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(V, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 100.0})
    monkeypatch.setattr(V, 'not_this', lambda *a, **k: {})
    P._MADE.clear()


def png(size=(600, 400), mode='RGB'):
    out = io.BytesIO()
    Image.new(mode, size, 'white' if mode == 'RGB' else (255, 255, 255, 0)).save(out, 'PNG')
    return out.getvalue()


def put_set(store, eid='wall', sha='a' * 64, views=('Front', 'Side'), status='proposed', notes='', data=None):
    """A thing's drawing set as `drawings.set_drawing` leaves it in the session, its labelled sheets in the store."""
    s, rows = H.session(store), []
    for n, name in enumerate(views):
        key = f"r1/visuals/drawings/{sha}/{chr(97 + n)}.png"
        store.put(key, data if data is not None else png(), 'image/png')
        rows.append({'id': chr(97 + n), 'name': name, 'kind': 'front', 'width': 600, 'height': 400, 'labelled_key': key, 'labelled_sha256': 'l', 'plain_key': key + '.plain', 'plain_sha256': 'p'})
    s.setdefault('drawings', {})[eid] = {
        'sha256': sha, 'key': f'r1/visuals/drawings/{sha}/set.json', 'level': 'engineered', 'name': 'The wall', 'unit': 'mm', 'views': rows,
        'facts': [{'what': 'board thickness', 'value': 18, 'unit': 'mm', 'source': "the joiner's drawing"}, {'what': 'slope of a tail', 'value': '1 in 7', 'assumed': True}],
        'sourced': ["board thickness: 18 mm (the joiner's drawing)"], 'assumed': ['slope of a tail: 1 in 7'], 'status': status,
        **({'verdict': {'approved': False, 'notes': notes}} if notes else {})}
    V.save_session(store, H.RUN, s)
    return rows


def film(n_things=0):
    """A film whose plan is accepted and has no drawing spec or material: nothing stands before the reference drawings."""
    plan = plan_with([None, None])
    plan['elements'] += [{'id': f'T{i}', 'name': f'Thing {i}', 'kind': 'object', 'description': 'a thing'} for i in range(1, n_things + 1)]
    return start(plan)


def chat_items(store, conn):
    return C._drawing_items(C._ctx(conn, store, H.USER, H.RUN, {}))


# ---------- the picture contract ----------

def test_a_pictures_code_comes_from_its_storage_key_and_stays_the_same():
    assert P.pic_code('r1/visuals/x.png') == 'p' + hashlib.sha1(b'r1/visuals/x.png').hexdigest()[:12] == P.pic_code('r1/visuals/x.png')
    assert P.pic_code('r1/visuals/y.png') != P.pic_code('r1/visuals/x.png')
    assert P.pic('r1/visuals/x.png', 'Front') == {'code': P.pic_code('r1/visuals/x.png'), 'label': 'Front', '_key': 'r1/visuals/x.png'}


@pytest.mark.parametrize('size', [(5000, 60), (60, 5000), (3000, 2000), (200, 100), (1, 1)])
def test_both_sizes_stay_within_their_long_side_and_nothing_is_cropped(size):
    for which, side in (('thumb', 360), ('zoom', 1600)):
        im = Image.open(io.BytesIO(P.shrink(png(size), *P.PIC_SIZES[which][1:])))
        assert im.format == 'JPEG' and max(im.size) <= side and max(im.size) == min(side, max(size))
        w, h = size
        assert abs(im.size[0] * h - im.size[1] * w) <= max(w, h) * max(im.size), (size, im.size)   # the same shape: shrunk, never cut


def test_a_see_through_picture_is_put_on_white_and_one_that_is_not_a_picture_is_refused():
    im = Image.open(io.BytesIO(P.shrink(png((100, 100), 'RGBA'), 360, 60)))
    assert im.mode == 'RGB' and min(im.getpixel((50, 50))) > 240
    with pytest.raises(Exception):
        P.shrink(b'not a picture', 360, 60)


def test_the_two_sizes_are_made_once_and_stored_beside_the_picture():
    store = H.Store()
    store.put('r1/visuals/x.png', png((3000, 2000)))
    small, large = P.sized(store, 'r1/visuals/x.png', 'thumb'), P.sized(store, 'r1/visuals/x.png', 'zoom')
    assert small.startswith('r1/visuals/x.png.') and large.startswith('r1/visuals/x.png.') and small != large
    assert Image.open(io.BytesIO(store.d[small])).size == (360, 240) and Image.open(io.BytesIO(store.d[large])).size == (1600, 1067)
    store.d[small] = b'kept'
    P._MADE.clear()
    assert P.sized(store, 'r1/visuals/x.png', 'thumb') == small and store.d[small] == b'kept'   # stored: never made again


def test_the_same_picture_on_two_lines_has_one_code_and_is_listed_once_and_a_broken_one_is_named():
    store = H.Store()
    store.put('r1/a.png', png())
    store.put('r1/bad.png', b'half a file')
    got = P._with_pictures(store, {'lines': [{'title': 'One', 'pics': [P.pic('r1/a.png', 'Front'), P.pic('r1/bad.png', 'Side')]}, {'title': 'Two', 'pics': [P.pic('r1/a.png', 'Front again')]},
                                             {'title': 'Three', 'pics': [P.pic('r1/gone.png', 'Top')]}, {'title': 'No pictures'}]})
    code = P.pic_code('r1/a.png')
    assert got['pictures'] == [{'code': code, 'thumb': 'r1/a.png' + P.PIC_SIZES['thumb'][0], 'zoom': 'r1/a.png' + P.PIC_SIZES['zoom'][0]}]
    assert got['pictures_failed'] == ['One: Side', 'Three: Top']
    assert got['lines'][0]['pics'] == [{'code': code, 'label': 'Front'}, {'code': P.pic_code('r1/bad.png'), 'label': 'Side', 'missing': True}]
    assert got['lines'][1]['pics'] == [{'code': code, 'label': 'Front again'}] and '_key' not in json.dumps(got)
    plain = P._with_pictures(store, {'lines': [{'title': 'No pictures'}]})
    assert 'pictures' not in plain and 'pictures_failed' not in plain   # a round with no pictures is as before


def test_the_page_may_use_its_file_store_and_is_told_the_order():
    assert P.CAPABILITIES['assets'] == {} and P.CAPABILITIES['user'] == {} and {'pics', 'zoom', 'rounds'} <= {r['path'] for r in P.CAPABILITIES['db']['rules']}
    how = P.HOW
    assert how.index('picture_batches') < how.index('zoom_uploads') < how.index('--uploaded') < how.index('collection "rounds"') < how.index('Open this page')
    assert '`capabilities` again, exactly as given' in how and 'large pictures are not available' in how and 'vw visuals next' in how


# ---------- the step ----------

def test_with_no_drawing_set_waiting_the_step_is_skipped():
    store, conn = film()
    p = page(store, conn)
    assert p['step'] == 'Plan' and 'pictures' not in p
    put_set(store, status='approved')
    assert page(store, conn)['step'] == 'Plan'   # an approved set alone asks nothing


def test_a_set_with_one_sheet_is_the_chats_own_item_with_its_picture_its_facts_and_its_question():
    store, conn = film()
    rows = put_set(store, views=('Front',))
    p, item = page(store, conn), chat_items(store, conn)[0]
    line = p['lines'][0]
    assert p['step'] == STEP and p['open'] is True and len(p['lines']) == 1 and line['state'] == 'open' and line['line'] == 'l01'
    assert line['item'] == item['id'] == 'drawing:wall:' + 'a' * 10 and line['key'] == 'drawing:wall' and line['title'] == 'The wall'
    assert line['buttons'] == [{'label': 'Yes', 'choice': 'yes', 'needs_words': False}, {'label': 'Correct it', 'choice': 'correct', 'needs_words': True}]
    assert line['pics'] == [{'code': P.pic_code(rows[0]['labelled_key'], 'l'), 'label': 'Front'}] and line['ask'] == 'Is the shape and arrangement right?'
    assert line['facts'] == [['board thickness', '18 mm', "the joiner's drawing"]] and line['assumed'] == 'slope of a tail: 1 in 7' and line['text'].startswith('1 sheet.')
    pic = p['pictures'][0]
    assert p['pictures'] == [{'code': line['pics'][0]['code'], 'thumb': pic['thumb'], 'zoom': pic['zoom']}] and pic['thumb'].startswith('r1/') and pic['zoom'].startswith('r1/')
    assert max(Image.open(io.BytesIO(store.d[pic['thumb']])).size) == 360 and Image.open(io.BytesIO(store.d[pic['zoom']])).size == (600, 400)
    assert '1 thing: 1 to answer' in p['summary'] and 'say done' in p['note'] and len(json.dumps(p['lines']).encode()) < P.ROUND_BYTES


def test_a_set_with_eight_sheets_shows_all_of_them_in_their_order():
    store, conn = film()
    names = ('Front', 'Side', 'From above', 'Section', 'Back', 'Detail', 'Three-quarter', 'Underside')
    rows = put_set(store, views=names)
    p = page(store, conn)
    assert [x['label'] for x in p['lines'][0]['pics']] == list(names) and [x['code'] for x in p['lines'][0]['pics']] == [P.pic_code(r['labelled_key'], 'l') for r in rows]
    assert len(p['pictures']) == 8 and p['lines'][0]['text'].startswith('8 sheets.')


def test_the_drawings_and_materials_are_answered_before_the_reference_drawings():
    store, conn = start(plan_with([None, None], PANEL))
    put_set(store)
    p = page(store, conn)
    assert p['step'] == P.SPEC_STEP and 'pictures' not in p
    record(store, conn, [ans(l, 'yes') for l in p['lines'] if l['state'] == 'open'])
    assert page(store, conn)['step'] == STEP


def test_an_approved_set_is_recorded_and_keeps_its_pictures_and_facts_and_all_approved_goes_on():
    store, conn = film(1)
    put_set(store)
    put_set(store, 'T1', 'b' * 64, ('Front',))
    p = page(store, conn)
    assert [l['title'] for l in p['lines']] == ['The wall', 'Thing 1'] and '2 things: 2 to answer' in p['summary']
    r = record(store, conn, [ans(by_key(p)['drawing:wall'], 'yes')])
    now = by_key(r['page'])
    assert r['recorded'] == ['drawing:wall'] and r['open'] == 1 and r['page']['step'] == STEP and '1 line(s) still wait' in r['then']
    assert now['drawing:wall']['state'] == 'recorded' and len(now['drawing:wall']['pics']) == 2 and now['drawing:wall']['facts'] and 'buttons' not in now['drawing:wall']
    assert H.session(store)['drawings']['wall']['status'] == 'approved' and H.session(store)['drawings']['wall']['verdict']['quote'] == 'Yes'
    assert len(r['page']['pictures']) == 3 and len(conn.log) == 1
    r = record(store, conn, [ans(now['drawing:T1'], 'yes')])
    assert r['recorded'] == ['drawing:T1'] and r['then'] == P.DRAW_NEXT and '`vw visuals next`' in r['then'] and r['page']['step'] != STEP


def test_a_set_sent_back_is_with_the_assistant_with_the_operators_words_and_the_redraw_is_named():
    store, conn = film()
    put_set(store)
    r = record(store, conn, [ans(page(store, conn)['lines'][0], 'correct', 'the  lid is on the wrong side')])
    line = r['page']['lines'][0]
    assert r['recorded'] == ['drawing:wall'] and line['state'] == 'with_assistant' and line['note'] == 'the lid is on the wrong side' and 'pics' not in line
    assert r['then'] == P.DRAW_BACK and '`vw drawing set --element E --file' in r['then'] and '`vw visuals page`' in r['then'] and r['page']['open'] is False
    assert conn.log and 'the lid is on the wrong side' in json.dumps(conn.log[-1], default=str)
    assert H.session(store)['drawings']['wall']['status'] == 'rejected'
    put_set(store, sha='c' * 64)   # redrawn: asked again, as a new item
    p = page(store, conn)
    assert p['lines'][0]['state'] == 'open' and p['lines'][0]['item'] == 'drawing:wall:' + 'c' * 10


def test_an_answer_to_a_set_that_was_redrawn_meanwhile_is_stale():
    store, conn = film()
    put_set(store)
    old = page(store, conn)['lines'][0]
    put_set(store, sha='c' * 64)
    r = record(store, conn, [ans(old, 'yes')])
    assert r['stale'] == ['drawing:wall'] and r['recorded'] == [] and H.session(store)['drawings']['wall']['status'] == 'proposed' and r['open'] == 1


def test_done_with_nothing_answered_and_with_some_unanswered():
    store, conn = film(1)
    put_set(store)
    put_set(store, 'T1', 'b' * 64)
    r = record(store, conn, [])
    assert r['recorded'] == [] and r['log'] == 'nothing answered' and r['then'].startswith('Nothing was answered on the page. 2 line(s) still wait')
    r = record(store, conn, [ans(r['page']['lines'][1], 'yes')])
    assert r['recorded'] == ['drawing:T1'] and r['open'] == 1 and [l['state'] for l in r['page']['lines']] == ['open', 'recorded']


def test_correct_it_with_no_words_is_refused_on_its_line_and_the_other_answer_is_recorded():
    store, conn = film(1)
    put_set(store)
    put_set(store, 'T1', 'b' * 64)
    p = by_key(page(store, conn))
    r = record(store, conn, [ans(p['drawing:wall'], 'correct', '  '), ans(p['drawing:T1'], 'yes'), ans(p['drawing:wall'], 'maybe')])
    now = by_key(r['page'])
    assert r['recorded'] == ['drawing:T1'] and [x['key'] for x in r['refused']] == ['drawing:wall', 'drawing:wall'] and 'your own words' in r['refused'][0]['message']
    assert now['drawing:wall']['state'] == 'open' and now['drawing:wall']['refused'] and 'refused' in r['then'] and 'refused' not in now['drawing:T1']
    r = record(store, conn, [ans(now['drawing:wall'], 'yes')])
    assert 'refused' not in json.dumps(r['page']['lines'])


def test_thirty_things_stay_under_the_size_of_one_round_and_a_longer_list_holds_the_later_ones(monkeypatch):
    store, conn = film(30)
    for i in range(1, 31):
        put_set(store, f'T{i}', f'{i:064d}', ('Front', 'Side', 'From above', 'Section'))
    p = page(store, conn)
    assert len(p['lines']) == 30 and len(p['pictures']) == 120 and len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) <= P.ROUND_BYTES
    assert len(json.dumps({k: v for k, v in p.items() if k != 'pictures'}, ensure_ascii=False).encode('utf-8')) < 256 * 1024
    monkeypatch.setattr(P, 'ROUND_BYTES', 6000)
    p = page(store, conn)
    held = 30 - len(p['lines'])
    assert 0 < held < 30 and f'{held} more' in p['summary'] and f'{held} more' in p['note'] and len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) <= 6000
    assert len(p['pictures']) == 4 * len(p['lines'])   # only the pictures of the lines shown
    r = record(store, conn, [ans(l, 'yes') for l in p['lines']])
    assert len(r['recorded']) == len(p['lines']) and r['page']['step'] == STEP and r['open'] > 0   # the held ones come next


def test_a_sheet_that_cannot_be_read_is_named_and_the_rest_of_the_page_is_built():
    store, conn = film(1)
    put_set(store)
    rows = put_set(store, 'T1', 'b' * 64, ('Front', 'Side'))
    store.d[rows[1]['labelled_key']] = b'half a file'
    p = page(store, conn)
    assert p['pictures_failed'] == ['Thing 1: Side'] and len(p['pictures']) == 3 and len(p['lines']) == 2
    assert by_key(p)['drawing:T1']['pics'][1] == {'code': P.pic_code(rows[1]['labelled_key'], 'l'), 'label': 'Side', 'missing': True}


def test_the_layout_drawing_of_a_shot_is_not_this_step_and_the_chat_path_is_unchanged():
    store, conn = film()
    put_set(store)
    items = chat_items(store, conn)
    assert [i['id'] for i in H.items(store, conn)] == [i['id'] for i in items] == ['drawing:wall:' + 'a' * 10] and items[0]['show'][0]['name'] == 'drawing-wall-a.png'
    items[0]['_run']('yes', 'Yes', '')
    assert H.session(store)['drawings']['wall']['status'] == 'approved' and page(store, conn)['step'] == 'Plan'


def test_the_instructions_send_the_reference_drawings_to_the_page_and_the_chat_is_the_way_back():
    root = Path(__file__).resolve().parents[2]
    d = json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    search = next(p['text'] for p in st['parts'] if p['name'] == 'picture-search')
    assert "Except a thing's reference drawings: they too are approved on the page" in st['prompt'] and '(`vw visuals page`, which also sends the pictures as it says' in st['prompt']
    assert '`vw visuals next` then shows the operator the labelled sheets' in json.loads((root / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    sys.path.insert(0, str(root / 'scripts'))
    import copy
    import d210_wording_v3 as W
    parts = copy.deepcopy(st['parts'])
    assert W.apply(st['prompt'], parts) == st['prompt'] and parts == st['parts'], 'applying twice changes nothing'
    assert 'The operator approves the reference drawings on the page (`vw visuals page`' in search and 'only where the page cannot be shown' in search
    assert '`vw visuals next` then shows the operator the labelled sheets' not in search
    vw = (root / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'the operator approves the drawings on the page (`vw visuals page`' in vw and 'the operator approves the drawings in the chat;' not in vw
