"""design/108 I1-I4: a small copy of every picture, made once and cached; the page uses it everywhere but the viewer; full files cached across redraws."""
import re
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app import web
from app.errors import Problem
from app.files import file_redirect
from test_visuals_stage_pure import FakeStore

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
RUN = 'run-1'
KEY = f'{RUN}/visuals/references/K1.png'


def png(w=1536, h=864):
    buf = BytesIO()
    Image.new('RGB', (w, h), (180, 60, 40)).save(buf, 'PNG')
    return buf.getvalue()


# ---------- I1 ----------

def test_the_small_copy_is_made_once_at_most_768_wide_and_stored_beside_the_picture():
    store = FakeStore({KEY: png()})
    data = web.thumb_bytes(store, KEY)
    img = Image.open(BytesIO(data))
    assert img.format == 'JPEG' and img.width == 768 and img.height == 432 and len(data) < 200_000
    assert store.files[KEY + '.thumb.jpg'] == data
    store.files[KEY + '.thumb.jpg'] = b'STORED'
    assert web.thumb_bytes(store, KEY) == b'STORED'   # served from storage next time, never made again
    small = FakeStore({KEY: png(400, 300)})
    assert Image.open(BytesIO(web.thumb_bytes(small, KEY))).width == 400   # a small picture is not enlarged


# ---------- I2 ----------

def test_the_small_copy_is_served_with_a_days_cache_and_an_etag():
    store = FakeStore({KEY: png()})
    resp = web.thumb_response(store, RUN, KEY, None)
    assert resp.status_code == 200 and resp.media_type == 'image/jpeg' and resp.headers['cache-control'] == 'private, max-age=86400'
    etag = resp.headers['etag']
    assert etag.startswith('"') and web.thumb_response(store, RUN, KEY, etag).status_code == 304
    with pytest.raises(Problem):
        web.thumb_response(store, RUN, 'run-2/visuals/references/K1.png', None)   # another run's key
    with pytest.raises(Problem):
        web.thumb_response(store, RUN, f'{RUN}/visuals/references/missing.png', None)
    class Signing(FakeStore):
        def signed_download(self, key):
            return 'https://store/' + key
    clip = Signing({f'{RUN}/visuals/takes/t.mp4': b'mp4'})
    assert web.thumb_response(clip, RUN, f'{RUN}/visuals/takes/t.mp4', None).status_code == 307   # not a picture: the full file, as before


# ---------- I3 ----------

def test_the_page_shows_small_copies_everywhere_but_the_viewer_and_loads_grids_lazily():
    assert "function thumbOf(u)" in PAGE
    for fn in ('function big(r)', 'function refCard(', 'function renderRound(', 'function renderPictures('):
        body = PAGE[PAGE.index(fn):]
        body = body[:body.index('\nfunction ', 10)]
        assert 'thumbOf(' in body, fn
    card = PAGE[PAGE.index('function refCard('):PAGE.index('function resultCard(')]
    assert 'loading="lazy"' in card and 'decoding="async"' in card
    viewer = PAGE[PAGE.index('function drawViewer('):]
    assert re.search(r'src="\'\+esc\(r\.url\)\+\'" alt="" draggable', viewer) and 'thumbOf' not in viewer[:viewer.index('\nfunction ', 10)]


# ---------- I4 ----------

def test_the_redirect_to_a_full_file_is_cached_under_the_signed_links_hour():
    r = file_redirect('https://store/x')
    assert r.status_code == 307 and r.headers['location'] == 'https://store/x' and r.headers['cache-control'] == 'private, max-age=3000'
    src = (Path(__file__).resolve().parents[1] / 'app').joinpath('web.py').read_text(encoding='utf-8')
    assert 'return file_redirect(store.signed_download(key))' in src   # the page's audio, film and file routes
    src = (Path(__file__).resolve().parents[1] / 'app').joinpath('files.py').read_text(encoding='utf-8')
    assert 'return file_redirect(store.signed_download(key))' in src   # the plugin's download route
