"""design/117 P1: a component is a picture of a thing, alone on a transparent background in the approved style: made through generate_image with the
style picture as Image 1 and a transparent background asked of the image model, checked with two more must lines and a code line on the PNG's alpha,
approved like any picture, listed under its element."""
import json
from io import BytesIO

import pytest
from PIL import Image

from app import image_check as IC, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from test_design111_f11_pure import golden_store, image, put
from test_visuals_stage_pure import FakeConn, FakeStore, RUN, USER, g, ref, saved


def component_store(style=True):
    store = golden_store()
    s = saved(store)
    if style:
        s['references']['ST1'] = {**ref('ST1', 'approved'), 'kind': 'style', 'element_id': VS.STYLE}
    put(store, s)
    return store


def comp(store, **over):
    body = {'element_id': 'E2', 'name': 'wall-component', 'kind': 'component', 'subject': 'the wall', 'prompt': 'One rat-trap wall, front on, alone.', 'parents': []}
    return image(store, **{**body, **over})


def test_a_component_takes_the_style_as_image_1_and_asks_for_a_transparent_background():
    store = component_store()
    out = comp(store)
    s = saved(store)
    r = s['references'][out['reference_id']]
    assert r['kind'] == 'component' and r['status'] == 'generating' and r['generation']['op'] == 'edit' and r['generation']['parents'][0]['id'] == 'ST1'
    assert r['generation']['background'] == 'transparent'
    assert 'Image 1 is the approved style of this film' in r['generation']['prompt'] and 'transparent background' in r['generation']['prompt'] and 'alone, nothing else' in r['generation']['prompt']
    checks = [l['check'] for l in r['server_checklist']]
    assert 'one thing only' in checks and 'clean edge' in checks and "the film's world" not in checks


def test_a_component_needs_the_approved_style_and_is_a_picture_of_a_thing():
    with pytest.raises(Problem, match='approve the style picture first'):
        g(lambda: comp(component_store(style=False)))
    store = component_store()
    with pytest.raises(Problem, match='kind style with element _STYLE, and only it'):   # the style element is refused before the component rule speaks
        g(lambda: comp(store, element_id=VS.STYLE, kind='component'))
    s = saved(store)
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    doc['elements'].append({'id': 'P1', 'name': 'Mason', 'kind': 'person', 'identity': 'representative', 'requirements': 'a mason'})
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    with pytest.raises(Problem, match='component is a picture of a thing'):
        g(lambda: comp(store, element_id='P1', kind='component'))


def png(alpha_share, size=(40, 40)):
    im = Image.new('RGBA', size, (200, 80, 40, 255))
    n = int(size[0] * alpha_share)
    for x in range(n):
        for y in range(size[1]):
            im.putpixel((x, y), (0, 0, 0, 0))
    buf = BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


def test_the_alpha_line_passes_a_cut_out_and_fails_a_picture_without_a_transparent_background():
    ok = IC.alpha_line(png(0.5))
    assert ok['check'] == 'transparent background' and ok['pass'] is True and ok['weight'] == 'must' and '50%' in ok['seen']
    assert IC.alpha_line(png(0.1))['pass'] is False
    buf = BytesIO()
    Image.new('RGB', (40, 40), (200, 80, 40)).save(buf, 'PNG')
    no = IC.alpha_line(buf.getvalue())
    assert no['pass'] is False and 'no alpha' in no['seen']


def test_run_check_adds_the_alpha_line_for_a_component_and_fails_the_picture_on_it(monkeypatch):
    monkeypatch.setattr(IC, '_model_check', lambda *a, **k: {'lines': [], 'must_failed': [], 'model': IC.CHECK_MODEL})
    store = FakeStore({'run-1/visuals/references/C1.png': png(0.1)})
    rec = IC.run_check(store, {'references': {}}, {'id': 'C1', 'kind': 'component', 'element_kind': 'object', 'key': 'run-1/visuals/references/C1.png'}, {'key': 'run-1/visuals/references/C1.png'}, None)
    assert [l['check'] for l in rec['must_failed']] == ['transparent background']
    store.files['run-1/visuals/references/C1.png'] = png(0.5)
    rec = IC.run_check(store, {'references': {}}, {'id': 'C1', 'kind': 'component', 'element_kind': 'object', 'key': 'run-1/visuals/references/C1.png'}, {'key': 'run-1/visuals/references/C1.png'}, None)
    assert rec['must_failed'] == [] and any(l['check'] == 'transparent background' for l in rec['lines'])
    rec = IC.run_check(store, {'references': {}}, {'id': 'K1', 'kind': 'keyframe', 'element_kind': 'object', 'key': 'run-1/visuals/references/C1.png'}, {'key': 'run-1/visuals/references/C1.png'}, None)
    assert not any(l['check'] == 'transparent background' for l in rec['lines'])   # a keyframe is never asked for alpha
    assert IC.lines_of({'kind': 'component', 'element_kind': 'object'}) == IC.FIXED   # no scene lines for a cut-out


def test_the_worker_sends_the_background_to_the_image_api(monkeypatch, tmp_path):
    sent = {}

    class R:
        status_code = 200
        text = ''
        content = json.dumps({'data': [{'b64_json': __import__('base64').b64encode(png(0.5)).decode()}], 'usage': {}}).encode()
    monkeypatch.setattr(VW, '_openai', lambda path, **kw: sent.update(path=path, **kw) or R())
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    store = FakeStore({'run-1/visuals/references/ST1.png': png(0.0)})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    req = {'kind': 'image', 'op': 'edit', 'model': 'm', 'prompt': 'p', 'size': '1024x1024', 'quality': 'high', 'background': 'transparent',
           'parents': [{'id': 'ST1', 'key': 'run-1/visuals/references/ST1.png', 'sha256': 'x'}], 'reference': {'id': 'C1', 'kind': 'component', 'element_id': 'E2'}}
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': req})
    assert status == 'retained', error
    assert sent['path'] == '/images/edits' and sent['data']['background'] == 'transparent'
    req2 = {**req, 'op': 'generate', 'parents': []}
    monkeypatch.setattr(VW, 'SPOOL', tmp_path / 'b')
    VW.process_image({'id': 'j2', 'run_id': 'run-1', 'request': req2})
    assert sent['path'] == '/images/generations' and sent['json']['background'] == 'transparent'
    req3 = {**req2, 'reference': {'id': 'K9', 'kind': 'isolated', 'element_id': 'E2'}}
    req3.pop('background')
    monkeypatch.setattr(VW, 'SPOOL', tmp_path / 'c')
    VW.process_image({'id': 'j3', 'run_id': 'run-1', 'request': req3})
    assert 'background' not in sent['json']


def test_the_page_lists_a_component_under_its_element():
    page = (__import__('pathlib').Path(VS.__file__).resolve().parent / 'templates' / 'visuals.html').read_text(encoding='utf-8')
    assert "'isolated','sheet','component'" in page or "'isolated','sheet','style','component'" in page
