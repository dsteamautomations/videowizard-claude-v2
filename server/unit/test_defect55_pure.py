"""Defect 55 (VW-24, 17 Nov 2026): a picture on the page is its storage key AND its content. A reference round rolled back and made again
stored its new pictures under the keys of the round before; the server gave the small and large copies made of the old pictures, and the
page and the assistant's look showed the old ones. The code of a picture and the names of its two copies carry the content's mark (its
sha256); a v2 round posted from now on puts its own `at` in its sets' request ids, so a round started again never reuses an earlier round's
keys. Without a database."""
import io
import json
import uuid

import pytest
from PIL import Image

from app import chat_flow as CF, page_flow as P, ref_sets as RS, visuals_stage as VS
import check_shared_change as H
import d211_fixture as F
from test_design211b_round_pure import back, done, film, post, put, saved
from test_design211b_sets_pure import finder   # noqa: F401 (the stand-in for part A)
from test_design211c_kit_pure import Film, RUN, older_step1

KEY = 'r1/visuals/references/abc.png'
OLD, NEW = 'a' * 64, 'b' * 64


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', 2)   # the round of design/211, as the modules of design/211 run it (conftest)
    P._MADE.clear()


def png(colour, size=(600, 400)):
    out = io.BytesIO()
    Image.new('RGB', size, colour).save(out, 'PNG')
    return out.getvalue()


def colour_of(data):
    return Image.open(io.BytesIO(data)).convert('RGB').getpixel((5, 5))


def red(rgb):
    return rgb[0] > 200 and rgb[2] < 60


def blue(rgb):
    return rgb[2] > 200 and rgb[0] < 60


# ---------- the code and the two copies ----------

def test_the_same_key_with_other_content_is_another_picture_and_the_same_content_is_the_same_one():
    assert P.pic_code(KEY, OLD) != P.pic_code(KEY, NEW) and P.pic_code(KEY, OLD) == P.pic_code(KEY, OLD)
    assert P.pic_code(KEY, OLD) != P.pic_code(KEY) == P.pic_code(KEY, '') == P.pic_code(KEY, None)   # no mark: the key alone, as before
    assert all(len(c) == 13 and c[0] == 'p' for c in (P.pic_code(KEY, OLD), P.pic_code(KEY)))      # the tool's file names accept it
    assert P.pic(KEY, 'A', NEW) == {'code': P.pic_code(KEY, NEW), 'label': 'A', '_key': KEY, '_mark': NEW} and '_mark' not in P.pic(KEY, 'A')


def test_the_copies_of_a_picture_stored_again_under_its_key_are_made_from_the_new_picture():
    store = H.Store()
    store.put(KEY, png('red'))
    before = [P.sized(store, KEY, w, OLD) for w in ('thumb', 'zoom')]
    store.put(KEY, png('blue'))                                 # made again: the same key, other content
    after = [P.sized(store, KEY, w, NEW) for w in ('thumb', 'zoom')]
    assert not set(before) & set(after) and before[0] == KEY + '.' + OLD[:10] + P.PIC_SIZES['thumb'][0]
    assert all(red(colour_of(store.d[k])) for k in before) and all(blue(colour_of(store.d[k])) for k in after)   # the old copies stay stored, and are not given
    P._MADE.clear()
    store.d[after[0]] = b'kept'
    assert P.sized(store, KEY, 'thumb', NEW) == after[0] and store.d[after[0]] == b'kept'   # the same content: made once


def test_a_page_built_twice_hands_over_nothing_new_and_a_changed_picture_is_a_new_one():
    store = H.Store()
    store.put(KEY, png('red'))
    build = lambda mark: P._with_pictures(store, {'lines': [{'title': 'One', 'pics': [P.pic(KEY, 'A', mark)]}]})
    first, again = build(OLD), build(OLD)
    assert first == again and first['pictures'][0]['code'] == P.pic_code(KEY, OLD) and '_mark' not in json.dumps(first) and '_key' not in json.dumps(first)
    store.put(KEY, png('blue'))
    new = build(NEW)
    assert new['pictures'][0]['code'] != first['pictures'][0]['code'] and new['lines'][0]['pics'][0]['code'] == new['pictures'][0]['code']
    assert blue(colour_of(store.d[new['pictures'][0]['thumb']])) and blue(colour_of(store.d[new['pictures'][0]['zoom']]))


# ---------- every picture of the round carries its mark, on the page and in the chat ----------

def marks(session):
    """Every stored picture of the session by its key: the mark the page must carry."""
    out = {r['key']: r['sha256'] for r in session['references'].values() if r.get('key')}
    out.update({t['key']: t['sha256'] for t in F.trials()['trials'].values()})
    return out


@pytest.mark.parametrize('state', ['1', '2'])
def test_every_picture_of_a_v2_round_is_known_by_its_key_and_its_content(monkeypatch, state):
    film_ = Film(monkeypatch, state)
    known = marks(film_.session())
    items = {i['id']: i for i in film_.items()}
    seen = 0
    for l in film_.page()['lines']:
        keys = [x['key'] for x in items[l['item']]['show']] if l.get('item') in items else None
        pics = (l.get('pics') or []) + (l.get('earlier') or [])
        if keys is not None:
            assert [x['code'] for x in pics] == [P.pic_code(k, known[k]) for k in keys], l['key']   # the chat shows the same pictures: their keys, read fresh each time
        for x in pics:
            seen += 1
            assert x['code'] in {P.pic_code(k, m) for k, m in known.items()} and x['code'] not in {P.pic_code(k) for k in known}, (l['key'], x['label'])
    assert seen


def test_a_set_made_again_under_the_same_ids_is_shown_new(monkeypatch):
    film_ = Film(monkeypatch, '2')
    line = lambda: next(l for l in film_.page()['lines'] if l['key'] == 'set:T_LAY')
    before, sizes = line(), {p['code']: p for p in film_.page()['pictures']}

    def again(s):   # the round rolled back and the set made again: the same ids and keys, other pictures
        for r in s['references'].values():
            if r.get('element_id') == 'T_LAY' and r.get('kind') == 'sheet':
                r['sha256'] = 'd' * 64
                film_.store.files[r['key']] = png('blue')
    film_.change(again)
    after, new = line(), {p['code']: p for p in film_.page()['pictures']}
    changed = [(a, b) for a, b in zip(before['pics'], after['pics']) if not a.get('ref_only')]
    assert changed and all(a['code'] != b['code'] and a['label'] == b['label'] for a, b in changed)
    for _a, b in changed:
        assert b['code'] not in sizes and blue(colour_of(film_.store.files[new[b['code']]['zoom']]))


def test_an_older_rounds_page_is_as_it_was_but_for_the_codes(monkeypatch):
    film_ = Film(monkeypatch, session=older_step1())
    refs = film_.session()['references']
    lines = [l for l in film_.page()['lines'] if l.get('pics')]
    assert lines
    for l in lines:
        live = [f for f in refs if refs[f].get('element_id') == l['key'].split(':')[1] and refs[f].get('kind') == 'frame'][:4]
        assert l['pics'] == [{'code': P.pic_code(CF._ref_key(RUN, f), refs[f]['sha256']), 'label': f'Footage picture {n}'} for n, f in enumerate(live, 1)]


# ---------- the assistant's look at a made set ----------

def test_the_look_gets_the_large_copy_of_the_set_made_now():
    store, conn = film()
    post(store, conn)
    done(store, conn, TROWEL={'verdict': 'clean'}, MASON={'verdict': 'approve'}, STREET={'verdict': 'ignore'}, BRICK={'verdict': 'ignore'}, TILE={'verdict': 'ignore'})
    back(store)
    s = saved(store)
    ref = s['round']['elements']['TROWEL']['set']
    key = s['references'][ref]['key']
    first = lambda: next(x for x in RS.looks_due(store, RUN, [])['sets'] if x['element_id'] == 'TROWEL')['pictures'][0]['key']
    store.files[key] = png('red')
    old = first()
    assert old == key + '.' + s['references'][ref]['sha256'][:10] + P.PIC_SIZES['zoom'][0] and red(colour_of(store.files[old]))
    s['references'][ref]['sha256'] = 'made-again-' + ref     # the set made again under the same id
    put(store, s)
    store.files[key] = png('blue')
    new = first()
    assert new != old and blue(colour_of(store.files[new]))


# ---------- the ids of a round's sets ----------

def older_id(eid, n=1):
    return VS.digest({'run': str(RUN['id']), 'request': str(uuid.uuid5(uuid.NAMESPACE_OID, f"{RUN['id']}-set-{eid}-{n}"))})[:32]


def test_a_round_posted_now_never_reuses_the_ids_of_an_earlier_round():
    made = []
    for at in ('2026-11-16T10:00:00+00:00', '2026-11-17T10:00:00+00:00'):
        store, conn = film()
        post(store, conn)
        s = saved(store)
        assert s['round']['own_ids'] is True
        s['round']['at'] = at
        put(store, s)
        done(store, conn)
        made.append(saved(store)['round']['elements']['T_LAY']['set'])
        assert made[-1] == VS.digest({'run': str(RUN['id']), 'request': str(uuid.uuid5(uuid.NAMESPACE_OID, f"{RUN['id']}-set-T_LAY-1-{at}"))})[:32]   # the same on a retry inside the round
    assert made[0] != made[1] and older_id('T_LAY') not in made


def test_a_round_posted_before_keeps_its_ids():
    store, conn = film()
    post(store, conn)
    s = saved(store)
    s['round'].pop('own_ids')        # a round posted before 0.109.2
    put(store, s)
    done(store, conn)
    assert saved(store)['round']['elements']['T_LAY']['set'] == older_id('T_LAY')
