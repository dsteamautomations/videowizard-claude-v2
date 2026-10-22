"""design/71 P5: a refused picture says why. The OpenAI client and the storage are faked; nothing is sent."""
import json

from app import visual_workers as VW


class Resp:
    def __init__(self, status, body):
        self.status_code, self.text = status, json.dumps(body)

    def json(self):
        return json.loads(self.text)


JOB = {'id': 'j1', 'run_id': 'run-1', 'request': {'op': 'generate', 'prompt': 'p', 'size': '1536x864', 'quality': 'high', 'parents': [], 'reference': {'id': 'r1'}, 'model': 'gpt-image-2.5-flare'}}


def refused(tmp_path, monkeypatch, body, status=400):
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: None)
    monkeypatch.setattr(VW, 'openai_client', lambda path, **kw: Resp(status, body))
    return VW.process_image(JOB)


def test_a_moderation_block_names_the_stage_and_the_categories_and_says_what_to_do(tmp_path, monkeypatch):
    status, result, error, cost, retry = refused(tmp_path, monkeypatch, {'error': {'type': 'moderation_blocked', 'moderation_stage': 'input', 'categories': ['violence'], 'message': 'blocked'}})
    assert status == 'failed' and result['failure'] == 'moderation_blocked' and cost is None and retry is None
    assert error.startswith('OpenAI refused the pictures or the prompt (moderation, stage input, violence).')
    assert 'A frame with a recognisable face cannot be edited: use it as a look reference only, pick a frame without a face, or change the prompt.' in error


def test_a_user_error_says_the_prompt_or_the_pictures_are_the_problem(tmp_path, monkeypatch):
    status, result, error, cost, retry = refused(tmp_path, monkeypatch, {'error': {'type': 'image_generation_user_error', 'message': 'bad input'}})
    assert status == 'failed' and result['failure'] == 'image_generation_user_error'
    assert error == 'OpenAI refused the request: the prompt or the pictures are the problem; do not resend unchanged. (bad input)'


def test_another_400_keeps_todays_message(tmp_path, monkeypatch):
    status, result, error, cost, retry = refused(tmp_path, monkeypatch, {'error': {'type': 'invalid_request_error', 'message': 'size is wrong'}})
    assert status == 'failed' and result['failure'] == 'provider' and error == 'OpenAI rejected the request (HTTP 400).'
