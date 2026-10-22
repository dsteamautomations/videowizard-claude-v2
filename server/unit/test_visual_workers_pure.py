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


def test_a_429_or_5xx_goes_back_to_the_queue_with_a_growing_delay_and_the_fourth_attempt_is_rejected(tmp_path, monkeypatch):
    """design/82 U3: retry with backoff, as OpenAI's guide says."""
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: None)
    monkeypatch.setattr(VW, 'openai_client', lambda path, **kw: Resp(429, {'error': {'type': 'rate_limit'}}))
    for attempt, delay in ((1, 1), (2, 2), (3, 4)):
        status, result, error, cost, retry = VW.process_image({**JOB, 'attempt': attempt})
        assert (status, retry) == ('queued', delay) and result['http_status'] == 429 and f'attempt {attempt + 1} of 4' in error
    status, result, error, cost, retry = VW.process_image({**JOB, 'attempt': 4})
    assert status == 'rejected' and retry is None and 'no further retry' in error


def test_a_take_keeps_the_providers_usage_beside_the_seconds():
    """design/82 U5."""
    snap = {'provider': 'google', 'model': 'gemini-omni-1.1-flash', 'duration_seconds': 6}
    assert VW.take_cost(snap, {'usage': {'video_tokens': 34752}}) == {'provider': 'google', 'model': 'gemini-omni-1.1-flash', 'seconds': 6, 'usage': {'video_tokens': 34752}}
    assert VW.take_cost(snap, {'steps': []}) == {'provider': 'google', 'model': 'gemini-omni-1.1-flash', 'seconds': 6}


def test_the_take_text_follows_the_librarys_omni_house_shape():
    """design/84 V1: the frame tags, the motion brief, the continuity line, one unbroken shot, no dialogue or music, the length last."""
    from app.video_providers import motion_text
    snap = {'motion_prompt': 'The mason lays the brick.', 'subject_reconciliation': {'H_MASON': 'lays'}, 'continuity_notes': 'the wall, the light; grey hair, white shirt', 'duration_seconds': 8, 'end_image': {'key': 'k'}}
    t = motion_text(snap)
    assert t.startswith('[# Sources <FIRST_FRAME>@Image1 <LAST_FRAME>@Image2]\nThe mason lays the brick.') and t.endswith('\n8s')
    assert 'Continuity: the wall, the light; grey hair, white shirt' in t and 'In a single unbroken scene, one continuous shot, no scene cuts, no jump cuts.' in t
    assert 'No dialogue. No music.' in t and 'Use Image1 as the starting frame and Image2 as the final frame' in t and 'Preserve the depicted identities' in t
    one = motion_text({**snap, 'end_image': None})
    assert one.startswith('[# Sources <FIRST_FRAME>@Image1]') and 'LAST_FRAME' not in one and 'Image2' not in one


def test_another_400_keeps_todays_message(tmp_path, monkeypatch):
    status, result, error, cost, retry = refused(tmp_path, monkeypatch, {'error': {'type': 'invalid_request_error', 'message': 'size is wrong'}})
    assert status == 'failed' and result['failure'] == 'provider' and error == 'OpenAI rejected the request (HTTP 400).'
