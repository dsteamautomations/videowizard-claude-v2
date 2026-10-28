"""design/120 set C: the worker's Gemini image call through the key pool: the request shape, the image part parsed and stored as PNG, the usage as cost,
a 429 cooling the key and moving to the next, an answer with no image failing with its text; chroma green keyed out for a component; both job families claimed."""
import base64
import json
import types
from io import BytesIO

from PIL import Image
from pydantic import SecretStr

from app import keys, visual_workers as VW
from test_visuals_stage_pure import FakeStore


def jpeg(colour=(200, 80, 40), size=(64, 32)):
    buf = BytesIO()
    Image.new('RGB', size, colour).save(buf, 'JPEG')
    return buf.getvalue()


def answer(image=True, text='A wall.', jpg=None):
    parts = ([{'text': text}] if text else []) + ([{'inlineData': {'mimeType': 'image/jpeg', 'data': base64.b64encode(jpg or jpeg()).decode()}}] if image else [])
    return {'candidates': [{'content': {'parts': parts}}], 'usageMetadata': {'promptTokenCount': 1200, 'candidatesTokenCount': 1290}}


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body
        self.text = json.dumps(body)
        self.content = self.text.encode()

    def json(self):
        return self._body


def settings_with(keys_csv='g1,g2'):
    return types.SimpleNamespace(GEMINI_API_KEY=SecretStr(''), GEMINI_API_KEYS=SecretStr(keys_csv), OPENAI_API_KEY=SecretStr(''), OPENAI_API_KEYS=SecretStr(''),
                                 GEMINI_IMAGE_MODEL='gemini-3-pro-image', GEMINI_IMAGE_SIZE='2K')


def req(**over):
    return {'kind': 'image', 'op': 'edit', 'provider': 'gemini', 'model': 'gemini-3-pro-image', 'prompt': 'Image 1 is the sheet: take identity. The wall.', 'size': {'aspect': '16:9', 'tier': '2K'}, 'quality': 'high',
            'parents': [{'id': 'S2', 'key': 'run-1/visuals/references/S2.png', 'sha256': 'x'}], 'reference': {'id': 'G1', 'kind': 'isolated', 'element_id': 'E2'}, **over}


def test_the_gemini_call_posts_generate_content_with_the_pictures_and_stores_a_png(monkeypatch, tmp_path):
    keys.reset()
    monkeypatch.setattr(VW, 'settings', settings_with)
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    store = FakeStore({'run-1/visuals/references/S2.png': b'\x89PNGsheet'})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    sent = []
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append((url, kw)) or Resp(200, answer()))
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': req()})
    assert status == 'retained', error
    url, kw = sent[0]
    assert url == 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent' and kw['headers']['x-goog-api-key'] == 'g1'
    body = kw['json']
    assert body['generationConfig'] == {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': '16:9', 'imageSize': '2K'}}
    parts = body['contents'][0]['parts']
    assert parts[0]['text'].startswith('Image 1.') and parts[1]['inlineData']['data'] == base64.b64encode(b'\x89PNGsheet').decode() and parts[-1]['text'] == req()['prompt']
    with Image.open(BytesIO(store.files['run-1/visuals/references/G1.png'])) as im:
        assert im.format == 'PNG' and im.size == (64, 32)
    assert (result['width'], result['height']) == (64, 32) and cost == {'provider': 'gemini', 'model': 'gemini-3-pro-image', 'tier': '2K', 'inputs': 1, 'input_tokens': 1200, 'output_tokens': 1290} and result['key_index'] == 0


def test_a_limited_key_cools_and_the_next_key_answers(monkeypatch, tmp_path):
    keys.reset()
    monkeypatch.setattr(VW, 'settings', settings_with)
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: FakeStore({'run-1/visuals/references/S2.png': b'p'}))
    seen = []

    def post(url, **kw):
        seen.append(kw['headers']['x-goog-api-key'])
        return Resp(429, {'error': {'message': 'quota'}}) if kw['headers']['x-goog-api-key'] == 'g1' else Resp(200, answer())
    monkeypatch.setattr(VW.httpx, 'post', post)
    status, result, error, cost, retry = VW.process_image({'id': 'j2', 'run_id': 'run-1', 'request': req()})
    assert status == 'retained' and seen == ['g1', 'g2'] and keys.cooling('gemini') == [0] and result['key_index'] == 1


def test_an_answer_with_no_image_fails_with_the_models_words(monkeypatch, tmp_path):
    keys.reset()
    monkeypatch.setattr(VW, 'settings', settings_with)
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: FakeStore({'run-1/visuals/references/S2.png': b'p'}))
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: Resp(200, answer(image=False, text='I cannot draw a real person.')))
    status, result, error, cost, retry = VW.process_image({'id': 'j3', 'run_id': 'run-1', 'request': req()})
    assert status == 'failed' and 'I cannot draw a real person.' in error and result['failure'] == 'no_image'


def test_chroma_green_is_keyed_out_for_a_component(monkeypatch, tmp_path):
    im = Image.new('RGB', (40, 40), (0, 255, 0))
    for x in range(10, 30):
        for y in range(10, 30):
            im.putpixel((x, y), (180, 70, 40))
    buf = BytesIO()
    im.save(buf, 'PNG')
    out = Image.open(BytesIO(VW.key_out_green(buf.getvalue()))).convert('RGBA')
    assert out.getpixel((2, 2))[3] == 0 and out.getpixel((20, 20))[3] == 255 and out.getpixel((20, 20))[:3] == (180, 70, 40)
    keys.reset()
    monkeypatch.setattr(VW, 'settings', settings_with)
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    store = FakeStore({'run-1/visuals/references/S2.png': b'p'})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: Resp(200, answer(jpg=buf.getvalue())))
    status, result, error, cost, retry = VW.process_image({'id': 'j4', 'run_id': 'run-1', 'request': req(chroma_key=True, reference={'id': 'C1', 'kind': 'component', 'element_id': 'E2'})})
    assert status == 'retained' and Image.open(BytesIO(store.files['run-1/visuals/references/C1.png'])).convert('RGBA').getpixel((2, 2))[3] == 0


def test_the_worker_claims_both_image_families():
    claimed = []

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=()):
            claimed.append(params[0] if params else None)

            class R:
                def fetchone(_):
                    return None
            return R()
    import contextlib
    saved_connect = VW.connect
    VW.connect = lambda: Conn()
    try:
        VW.tick()
    except Exception:
        pass
    finally:
        VW.connect = saved_connect
    assert 'openai' in claimed and 'gemini-image' in claimed
