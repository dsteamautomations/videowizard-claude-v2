"""design/119 set C, rule 1: a parent may carry a crop (left, top, width, height as fractions); the server crops before the upload, stores the crop
beside the reference, sends the crop as Image k, and the check reads the crop as that reference. Refusals: outside the frame, too small."""
import json
import types
from io import BytesIO

import pytest
from PIL import Image
from pydantic import SecretStr

from app import image_check as IC, visuals_stage as VS, visual_workers as VW
from app.errors import Problem
from test_design106_pure import revise_start
from test_design119_a_pure import store_with_extras
from test_visuals_stage_pure import saved


def png(w, h, colour=(200, 80, 40)):
    buf = BytesIO()
    Image.new('RGB', (w, h), colour).save(buf, 'PNG')
    return buf.getvalue()


def cropped_store():
    store = store_with_extras()
    store.files['run-1/visuals/references/R1.png'] = png(400, 200)
    store.files['run-1/visuals/references/K1.png'] = png(400, 200, (10, 10, 10))
    return store


REGION = {'left': 0.5, 'top': 0.0, 'width': 0.5, 'height': 0.5}   # the top right quarter: 200 x 100 of 400 x 200


def test_a_cropped_parent_is_stored_sent_and_recorded_with_its_region():
    store = cropped_store()
    out = revise_start(store, role='start', crops={'R1': REGION})
    gen = saved(store)['references'][out['reference_id']]['generation']
    r1 = next(p for p in gen['parents'] if p['id'] == 'R1')
    assert r1['crop'] == REGION and '-crop-' in r1['key'] and r1['full_key'] == 'run-1/visuals/references/R1.png'
    with Image.open(BytesIO(store.files[r1['key']])) as im:
        assert im.size == (200, 100)
    k1 = next(p for p in gen['parents'] if p['id'] == 'K1')
    assert 'crop' not in k1 and k1['key'] == 'run-1/visuals/references/K1.png'


@pytest.mark.parametrize('region, says', [
    ({'left': 0.8, 'top': 0.0, 'width': 0.5, 'height': 0.5}, 'inside the frame'),
    ({'left': 0.0, 'top': 0.0, 'width': 0.05, 'height': 0.05}, 'too small to send'),
    ({'left': 0.0, 'top': 0.0, 'width': 0, 'height': 0.5}, 'inside the frame'),
])
def test_a_crop_outside_the_frame_or_too_small_is_refused(region, says):
    with pytest.raises(Problem, match=says):
        VS.guarded(lambda: revise_start(cropped_store(), role='start', crops={'R1': region}))


def test_a_crop_of_a_picture_not_among_the_parents_is_refused():
    with pytest.raises(Problem, match='crops names L2, which is not among the parents'):
        VS.guarded(lambda: revise_start(cropped_store(), role='start', crops={'L2': REGION}))


def test_the_check_reads_the_crop_as_that_reference(monkeypatch):
    store = cropped_store()
    out = revise_start(store, role='start', crops={'R1': REGION})
    s = saved(store)
    r = s['references'][out['reference_id']]
    r['status'] = 'candidate'
    r['key'] = 'run-1/visuals/references/cand.png'
    store.files[r['key']] = png(400, 200, (1, 2, 3))
    seen = []

    class Transport:
        def __init__(self, key, model, **kw):
            pass

        def generate(self, payload):
            seen.extend(p['inlineData']['data'] for p in payload['contents'][0]['parts'] if 'inlineData' in p)
            return {'body': {'lines': []}, 'raw': ''}
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=SecretStr('k')))
    IC._model_check(store, s, r, {'key': r['key']}, Transport)
    import base64
    crop_key = next(p['key'] for p in r['generation']['parents'] if p['id'] == 'R1')
    assert base64.b64encode(store.files[crop_key]).decode() in seen and base64.b64encode(store.files['run-1/visuals/references/R1.png']).decode() not in seen


def test_the_worker_sends_the_crop_file(monkeypatch, tmp_path):
    store = cropped_store()
    out = revise_start(store, role='start', crops={'R1': REGION})
    gen = saved(store)['references'][out['reference_id']]['generation']
    sent = {}

    class R:
        status_code = 200
        text = ''
        content = json.dumps({'data': [{'b64_json': __import__('base64').b64encode(png(8, 8)).decode()}], 'usage': {}}).encode()
    monkeypatch.setattr(VW, '_openai', lambda path, **kw: sent.update(kw) or R())
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: store)
    req = {'kind': 'image', 'op': 'edit', 'model': 'm', 'prompt': 'p', 'size': '1536x864', 'quality': 'high', 'parents': gen['parents'], 'reference': {'id': 'X9', 'kind': 'keyframe', 'element_id': 'E1'}}
    VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': req})
    names = [f[1][0] for f in sent['files']]
    bodies = [f[1][1] for f in sent['files']]
    crop_key = next(p['key'] for p in gen['parents'] if p['id'] == 'R1')
    assert 'R1.png' in names and store.files[crop_key] in bodies and store.files['run-1/visuals/references/R1.png'] not in bodies
