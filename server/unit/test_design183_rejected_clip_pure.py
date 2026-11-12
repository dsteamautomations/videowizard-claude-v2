"""design/183 (SK, 12 Nov 2026, defect 48): a clip the analysis model refuses keeps the model's own reason, is set aside by the server, and does not block the stage."""
from app import analysis_jobs as A

GOOGLE = {'format': 'google_error', 'truncated': False, 'code': 400, 'status': 'INVALID_ARGUMENT', 'message': 'The video could not be processed.'}


def rejected(http, diagnostic=GOOGLE, category='inspect_required'):
    return {'failure': 'http_error', 'http_status': http, 'category': category, 'key_index': 0, 'provider_error': diagnostic}


def test_the_reason_is_the_providers_own_words_in_one_line():
    assert A.provider_reason(GOOGLE) == 'INVALID_ARGUMENT: The video could not be processed.'
    assert A.provider_reason({**GOOGLE, 'reasons': ['UNSUPPORTED_MEDIA']}) == 'INVALID_ARGUMENT: The video could not be processed. (UNSUPPORTED_MEDIA)'


def test_no_readable_answer_says_so_and_never_fails():
    for d in (None, {}, {'format': 'non_json_omitted'}, {'format': 'oversized', 'truncated': True}, 'text', {'message': 7}):
        assert A.provider_reason(d) == 'no reason given'


def test_the_reason_is_trimmed():
    assert len(A.provider_reason({'message': 'x' * 5000})) == 500


def test_a_refused_clip_is_set_aside_with_the_reason():
    assert A.set_aside_reason('rejected', rejected(400)) == 'the analysis model refused this clip (HTTP 400): INVALID_ARGUMENT: The video could not be processed.'
    assert 'HTTP 413' in A.set_aside_reason('rejected', rejected(413, {'message': 'Request payload size exceeds the limit'}))
    assert A.set_aside_reason('rejected', rejected(400, None)).endswith('no reason given')


def test_a_fault_of_the_key_or_the_account_never_sets_a_clip_aside():
    for http in (401, 403, 404, 429, 503):
        assert A.set_aside_reason('rejected', rejected(http)) is None
    for category in ('spending_or_billing_limit', 'quota_limit'):
        assert A.set_aside_reason('rejected', rejected(400, category=category)) is None
    assert A.set_aside_reason('rejected', rejected(400, {'status': 'INVALID_ARGUMENT', 'message': 'API key not valid. Please pass a valid API key.'})) is None
    assert A.set_aside_reason('rejected', rejected(400, {'status': 'INVALID_ARGUMENT', 'reasons': ['API_KEY_INVALID']})) is None


def test_only_a_rejection_sets_aside():
    for status in ('failed', 'submission_unknown', 'retained', 'storage_pending'):
        assert A.set_aside_reason(status, rejected(400)) is None
    assert A.set_aside_reason('rejected', None) is None
    assert A.set_aside_reason('rejected', {'failure': 'http_error'}) is None


def test_the_last_footage_is_never_set_aside():
    assert A.others_remain(retained=1, open_jobs=0) and A.others_remain(retained=0, open_jobs=3)
    assert not A.others_remain(retained=0, open_jobs=0)   # every clip refused: the stage stops and shows the reasons, as before


def test_the_error_line_of_a_rejected_job_carries_the_reason():
    assert A.rejected_error('request', 400, GOOGLE) == 'Provider rejected the request (HTTP 400): INVALID_ARGUMENT: The video could not be processed.'
    assert A.rejected_error('inspection', 429, None) == 'Provider rejected the inspection (HTTP 429): no reason given'


# ---- the plain-mode fallback (SK, 12 Nov 2026: "Yes, add it"): defect 48's clip is refused only in agentic mode with the answer schema ----

from app.video_evidence.transport import GeminiTransportError


def payload(agentic=True):
    part = {'fileData': {'fileUri': 'u', 'mimeType': 'video/mp4'}}
    if agentic:
        part['mediaProcessing'] = 'AGENTIC'
    return {'contents': [{'role': 'user', 'parts': [part, {'text': 'p'}]}], 'generationConfig': {'responseJsonSchema': {}}}


class Transport:
    """Like the real one: after a failure it refuses every further call, so the second send needs a new transport."""
    def __init__(self, *outcomes):
        self.outcomes, self.sent, self.made, self.dead = list(outcomes), [], 0, False

    def generate(self, p):
        assert not self.dead, 'a failed transport was used again'
        self.sent.append(p)
        o = self.outcomes.pop(0)
        if isinstance(o, Exception):
            self.dead = True
            raise o
        return o

    def fresh(self):
        self.made, self.dead = self.made + 1, False
        return self


def refused(http=400, diagnostic=GOOGLE):
    return GeminiTransportError('http_error', 'x', http_status=http, metadata={'provider_error': diagnostic})


def test_an_agentic_request_refused_with_400_is_sent_once_more_in_plain_mode():
    t, p = Transport(refused(), {'body': 1}), payload()
    assert A.generate(t, p, t.fresh) == ({'body': 1}, True) and t.made == 1
    assert len(t.sent) == 2 and 'mediaProcessing' not in t.sent[1]['contents'][0]['parts'][0] and t.sent[1]['generationConfig'] == p['generationConfig']
    assert p['contents'][0]['parts'][0]['mediaProcessing'] == 'AGENTIC'   # the frozen request is not changed


def test_an_accepted_request_is_sent_once():
    t = Transport({'body': 1})
    assert A.generate(t, payload(), t.fresh) == ({'body': 1}, False) and len(t.sent) == 1 and t.made == 0


def test_a_plain_request_refused_is_not_sent_again():
    t = Transport(refused())
    try:
        A.generate(t, payload(agentic=False), t.fresh)
        raise AssertionError('not raised')
    except GeminiTransportError as e:
        assert e.http_status == 400 and len(t.sent) == 1


def test_a_refusal_that_is_not_the_clips_is_not_sent_again():
    for exc in (refused(429), refused(403), refused(413), refused(400, {'message': 'API key not valid.'}), GeminiTransportError('connection_error', 'x')):
        t = Transport(exc)
        try:
            A.generate(t, payload(), t.fresh)
            raise AssertionError('not raised')
        except GeminiTransportError:
            assert len(t.sent) == 1


def test_when_plain_mode_is_refused_too_the_second_refusal_is_the_one_reported():
    t = Transport(refused(), refused(400, {'status': 'INVALID_ARGUMENT', 'message': 'second'}))
    try:
        A.generate(t, payload(), t.fresh)
        raise AssertionError('not raised')
    except GeminiTransportError as e:
        assert e.metadata['provider_error']['message'] == 'second' and len(t.sent) == 2
