"""design/117 P3: the render in headless Chromium: the text boxes measured, the frames at the film's size with the component drawn and the build
stepping, the same request rendered twice byte for byte, a closed browser recovered. Skipped where Playwright's Chromium is not installed."""
import shutil
from io import BytesIO

import pytest
from PIL import Image

from app import drawn as D
from svg_fixture import ACTIONS, SVG, with_

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as _p:
        _p.chromium.launch().close()
    CHROMIUM = True
except Exception:   # the package or the browser is missing on this machine
    CHROMIUM = False

pytestmark = pytest.mark.skipif(not CHROMIUM, reason='Playwright Chromium is not installed on this machine (playwright install chromium)')


@pytest.fixture(scope='module', autouse=True)
def stop_playwright_after_the_module():
    yield
    D.stop()   # the sync driver keeps an event loop on the main thread; later tests start their own
W, H = 640, 360


def fonts():
    return {'Noto Sans': D.font_file().read_bytes()}


def component():
    buf = BytesIO()
    Image.new('RGBA', (64, 64), (20, 120, 220, 255)).save(buf, 'PNG')   # a blue square as the 'flame' component
    return {'comp-1': ('image/png', buf.getvalue())}


def request(frames=12, fps='24'):
    acts = [dict(a, every_s=0.1) if a['kind'] == 'build' else a for a in ACTIONS]   # a course every 0.1 s: frames 0, 2 and 5 at 24 fps
    return {'scene': {'actions': acts}, 'width': W, 'height': H, 'fps': fps, 'frames': frames, 'cues': [0.0, 0.0, 0.25, 0.3, 0.4]}


def test_measure_gives_each_texts_box_and_outside_names_the_one_that_leaves_the_safe_area():
    boxes = {b['id']: b for b in D.measure(SVG, W, H, fonts(), component())}
    t = boxes['title']
    assert 0 < t['x'] < W / 2 < t['x'] + t['w'] < W and 0 < t['y'] < H * 0.2 and t['text'] == 'Bricks for the same wall'   # centred by text-anchor
    assert D.outside(list(boxes.values()), W, H) == []
    off = with_(old='x="800" y="130" text-anchor="middle"', new='x="1400" y="110"')
    assert [b['id'] for b in D.outside(D.measure(off, W, H, fonts(), component()), W, H)] == ['title']


def test_the_frames_show_the_component_and_the_build_steps_one_course_at_a_time():
    req = request()
    f0 = Image.open(BytesIO(D.frame_png(req, 0, SVG, component(), fonts()))).convert('RGB')
    assert f0.size == (W, H) and f0.getpixel((460, 260))[2] > 180   # the flame component (a blue square at 1000..1300 × 500..800 in the viewBox, 0.4 scale)
    assert f0.getpixel((200, 292))[0] < 245 and f0.getpixel((200, 268))[0] > 230   # course 1 drawn (brick red), course 2 not yet (the paper background)
    f8 = Image.open(BytesIO(D.frame_png(req, 8, SVG, component(), fonts()))).convert('RGB')
    assert f8.getpixel((200, 268))[0] > 150 and f8.getpixel((200, 268))[1] < 150   # course 2 is there by frame 8
    assert f8.getpixel((200, 244))[0] > 150 and f8.getpixel((200, 244))[1] < 200   # course 3 too (the gradient)


def test_the_render_has_the_shots_frames_at_the_films_size_and_keeps_the_sheets_frames(tmp_path):
    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg is missing on this machine')
    req = request(frames=12)
    out = D.render(req, tmp_path / 'out.mp4', SVG, component(), fonts(), keep={0, 11})
    assert out['frames'] == 12 and sorted(out['kept']) == [0, 11] and (tmp_path / 'out.mp4').stat().st_size > 1000
    from app.visual_workers import probe
    ev = probe(tmp_path / 'out.mp4')
    assert (ev.get('width'), ev.get('height')) == (W, H) and abs(float(ev['duration_seconds']) - 0.5) < 0.05
    jpeg = D.sheet(out['kept'], '24', W, H)
    assert Image.open(BytesIO(jpeg)).format == 'JPEG'


def test_the_same_request_renders_the_same_bytes_twice_and_a_closed_browser_is_started_again():
    req = request(frames=3)
    a = D.frame_png(req, 2, SVG, component(), fonts())
    D.reset()
    b = D.frame_png(req, 2, SVG, component(), fonts())
    assert a == b
    D.browser().close()   # a crash
    assert D.frame_png(req, 0, SVG, component(), fonts())[:8] == b'\x89PNG\r\n\x1a\n'
