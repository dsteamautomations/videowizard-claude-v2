"""design/151 section 13 (SK, 4 Nov 2026): a reference set is one conversation with the picture AI, one picture per turn, on gemini-nano-banana-2.1 with
Google Search + Image Search grounding and thinking HIGH on every turn; the views named by the server."""
import base64
import copy
import json
import types
from io import BytesIO

import pytest
from pydantic import SecretStr

from app import visual_workers as VW
from app import visuals_stage as VS
from test_design151_refs_pure import FakeStore, Resp, png_bytes


def _settings(monkeypatch, tmp_path):
    from app import keys
    keys.reset()
    monkeypatch.setattr(VW, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=SecretStr(''), GEMINI_API_KEYS=SecretStr('g1'), OPENAI_API_KEY=SecretStr(''), OPENAI_API_KEYS=SecretStr(''),
                                                                      GEMINI_IMAGE_MODEL='gemini-nano-banana-2.1', GEMINI_IMAGE_SIZE='2K'))
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    store = FakeStore({})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    return store


def turn(n, text='', image=True, chunks=()):
    parts = [{'text': text or f'Here is image {n}. '}]
    if image:
        parts.append({'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(png_bytes(64, 32, (n * 40, 10, 10))).decode()}})
    gm = {'groundingChunks': [{'web': {'uri': u, 'title': t}} for u, t in chunks], 'webSearchQueries': ['clay pot'], 'imageSearchQueries': ['clay pot photo']}
    return {'candidates': [{'content': {'role': 'model', 'parts': parts}, 'groundingMetadata': gm}], 'usageMetadata': {'promptTokenCount': 100 * n, 'candidatesTokenCount': 2000, 'thoughtsTokenCount': 900}}


REQ = {'kind': 'image', 'op': 'generate', 'provider': 'gemini', 'model': 'gemini-nano-banana-2.1', 'prompt': 'PREAMBLE. The pot.', 'size': {'aspect': '16:9', 'tier': '2K'}, 'quality': 'high',
       'parents': [], 'reference': {'id': 'S1', 'kind': 'sheet', 'element_id': 'E2'}, 'set': True, 'search': True, 'views': ['the whole pot', 'a three-quarter view', 'a close-up of the rim']}


def test_a_set_is_three_turns_of_one_conversation_with_image_search_and_thinking_high(monkeypatch, tmp_path):
    store = _settings(monkeypatch, tmp_path)
    sent = []
    answers = [turn(1, chunks=[('https://a', 'A')]), turn(2, chunks=[('https://a', 'A'), ('https://b', 'B')]), turn(3, 'Here is image 3: the rim. What the photographs showed: fired red clay.')]
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append(copy.deepcopy(kw['json'])) or Resp(200, answers[len(sent) - 1]))
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': REQ})
    assert status == 'retained', error
    assert len(sent) == 3
    for body in sent:   # SK's AI Studio settings on every turn
        assert body['tools'] == [{'google_search': {'searchTypes': {'webSearch': {}, 'imageSearch': {}}}}]
        assert body['generationConfig']['thinkingConfig'] == {'thinkingLevel': 'high'} and body['generationConfig']['responseModalities'] == ['TEXT', 'IMAGE']
    # turn 1: the prompt and the first view; turn n: the earlier turns (the model's text and picture) then the next view
    assert sent[0]['contents'][0]['role'] == 'user' and 'Image 1 of 3: the whole pot.' in sent[0]['contents'][0]['parts'][-1]['text'] and 'PREAMBLE' in sent[0]['contents'][0]['parts'][-1]['text']
    assert [c['role'] for c in sent[2]['contents']] == ['user', 'model', 'user', 'model', 'user']
    assert any(p.get('inlineData') for p in sent[2]['contents'][1]['parts']) and sent[2]['contents'][-1]['parts'][0]['text'] == 'Image 3 of 3: a close-up of the rim.'
    assert [x['key'] for x in result['extra']] == ['run-1/visuals/references/S1-2.png', 'run-1/visuals/references/S1-3.png'] and all(k in store.files for k in ('run-1/visuals/references/S1.png', 'run-1/visuals/references/S1-3.png'))
    assert 'fired red clay' in result['notes'] and result['sources'] == [{'url': 'https://a', 'title': 'A'}, {'url': 'https://b', 'title': 'B'}]   # the turns' sources, each once
    assert cost['pictures'] == 3 and cost['input_tokens'] == 600 and cost['output_tokens'] == 6000


def test_a_turn_without_a_picture_ends_the_set_with_a_note_and_keeps_what_came_back(monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)
    answers = [turn(1), turn(2, 'I cannot draw that.', image=False), turn(3)]
    sent = []
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append(1) or Resp(200, answers[len(sent) - 1]))
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': REQ})
    assert status == 'retained' and len(sent) == 2 and result['extra'] == [] and cost['pictures'] == 1
    assert 'picture 2 (a three-quarter view) did not come back: I cannot draw that.' in result['notes']


def test_no_picture_on_the_first_turn_fails_the_set_as_today(monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: Resp(200, turn(1, 'Blocked.', image=False)))
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': REQ})
    assert status == 'failed' and result['failure'] == 'no_image' and 'Blocked.' in error


def test_a_limit_on_a_later_turn_requeues_the_whole_set(monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)
    answers = [Resp(200, turn(1)), Resp(429, {'error': {'message': 'slow down'}})]
    sent = []
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append(1) or answers[len(sent) - 1])
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': REQ, 'attempt': 1})
    assert status == 'queued' and retry == 1 and result['http_status'] == 429


def test_a_persons_set_has_its_three_views_without_the_search_tool(monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)
    sent = []
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append(copy.deepcopy(kw['json'])) or Resp(200, turn(len(sent))))
    req = {**REQ, 'search': False, 'views': VS.PERSON_VIEWS, 'reference': {'id': 'S2', 'kind': 'sheet', 'element_id': 'P1'}}
    status, result, error, cost, retry = VW.process_image({'id': 'j2', 'run_id': 'run-1', 'request': req})
    assert status == 'retained' and len(sent) == 3 and all('tools' not in b for b in sent) and all(b['generationConfig']['thinkingConfig'] == {'thinkingLevel': 'high'} for b in sent)
    assert cost['pictures'] == 3 and 'Image 3 of 3: a close-up of the face.' == sent[2]['contents'][-1]['parts'][0]['text']


def test_the_views_and_the_set_lines_are_one_picture_per_turn():
    assert len(VS.THING_VIEWS) == 3 and len(VS.PERSON_VIEWS) == 3 and VS.SET_MAX == 3
    assert 'one per turn' in VS.KEPT_SET_LINE and 'two to four' not in VS.KEPT_SET_LINE and 'one per turn' in VS.PERSON_SET
    assert VS.set_views({'kind': 'object', 'name': 'the water pot'}) == [v.format(name='the water pot') for v in VS.THING_VIEWS]
    assert VS.set_views({'kind': 'person', 'name': 'Mason'}) == VS.PERSON_VIEWS


def test_the_instructions_and_the_command_text_say_three_pictures_one_per_turn():
    from pathlib import Path
    root = Path(VS.__file__).resolve().parents[2]
    v3 = json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    search = next(p['text'] for p in next(s for s in v3['stages'] if s['name'] == 'visuals')['parts'] if p['name'] == 'picture-search')
    assert 'three separate pictures, one per turn of one conversation' in search and 'two to four separate pictures' not in search and 'Image Search' in search
    md = (root / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'three separate pictures, one per turn' in md and 'two to four separate pictures' not in md
