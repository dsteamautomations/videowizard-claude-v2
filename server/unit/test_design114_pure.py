"""design/114: the key pool. Keys in turn, a cooling key skipped and back after its time, every key cooling gives the soonest one, the old single key
alone is a pool of one; an image call retried on the next key within the attempt; a Gemini call retried on the next key; records carry an index."""
import types

import pytest
from pydantic import SecretStr

from app import image_check as IC, keys as K, visual_workers as VW
from app.video_evidence.transport import GeminiTransportError


def cfg(openai='', openais='', gemini='', geminis=''):
    return types.SimpleNamespace(OPENAI_API_KEY=SecretStr(openai), OPENAI_API_KEYS=SecretStr(openais), GEMINI_API_KEY=SecretStr(gemini), GEMINI_API_KEYS=SecretStr(geminis))


@pytest.fixture(autouse=True)
def fresh():
    K.reset()
    yield
    K.reset()


def test_the_pool_is_the_old_key_then_the_list_stripped_and_without_doubles():
    s = cfg(gemini=' g1 ', geminis='g2, g1 ,, g3 ')
    assert K.pool('gemini', s) == ['g1', 'g2', 'g3'] and K.pool('openai', s) == []
    assert K.pool('openai', cfg(openai='o1')) == ['o1']   # the old single key alone: a pool of one, today's behaviour
    assert K.sizes(s) == {'openai': 0, 'gemini': 3}


def test_keys_go_in_turn_a_cooling_key_is_skipped_and_comes_back(monkeypatch):
    s = cfg(geminis='g1,g2,g3')
    assert [i for i, _ in K.each('gemini', s)] == [0, 1, 2] and [i for i, _ in K.each('gemini', s)] == [1, 2, 0]
    now = [1000.0]
    monkeypatch.setattr(K.time, 'monotonic', lambda: now[0])
    K.cool('gemini', 2, 'rate')
    assert K.cooling('gemini') == [2] and [i for i, _ in K.each('gemini', s)] == [0, 1]
    now[0] += 61
    assert K.cooling('gemini') == [] and len(K.each('gemini', s)) == 3
    K.cool('gemini', 0, 'quota')
    K.cool('gemini', 1, 'revoked')
    K.cool('gemini', 2, 'rate')
    assert [i for i, _ in K.each('gemini', s)] == [2]   # every key cooling: the one back soonest, so the provider answers
    assert K.COOL == {'rate': 60, 'quota': 600, 'revoked': 3600}   # SK's answer 1
    assert K.reason_of(429) == 'rate' and K.reason_of(403) == 'revoked' and K.reason_of(400, 'quota_limit') == 'quota' and K.reason_of(500) is None


def test_an_image_call_is_retried_on_the_next_key_within_the_attempt(monkeypatch):
    monkeypatch.setattr(VW, 'settings', lambda: cfg(openais='o1,o2,o3'))
    monkeypatch.setattr(VW, 'openai_client', None)
    seen = []

    class R:
        def __init__(self, status):
            self.status_code, self.text = status, '{}'
    monkeypatch.setattr(VW.httpx, 'post', lambda url, headers=None, **kw: seen.append(headers['Authorization']) or R(429 if headers['Authorization'].endswith('o1') else 200))
    r = VW._openai('/images/generations', json={})
    assert r.status_code == 200 and seen == ['Bearer o1', 'Bearer o2'] and r.key_index == 1 and K.cooling('openai') == [0]
    r = VW._openai('/images/generations', json={})   # the turn moves on and the cooling key is skipped
    assert r.status_code == 200 and seen[-1] in ('Bearer o2', 'Bearer o3')
    monkeypatch.setattr(VW.httpx, 'post', lambda url, headers=None, **kw: R(429))
    r = VW._openai('/images/generations', json={})   # every key limited: the last answer comes back, so the job requeues as before
    assert r.status_code == 429 and K.cooling('openai') == [0, 1, 2]
    monkeypatch.setattr(VW, 'settings', lambda: cfg())
    with pytest.raises(Exception, match='Configure VW2_OPENAI_API_KEY'):
        VW._openai('/images/generations', json={})


def test_a_gemini_call_is_retried_on_the_next_key_and_the_record_carries_the_index(monkeypatch):
    made = []

    class Transport:
        def __init__(self, key, model, **kw):
            self.key = key
            made.append(key)

        def generate(self, payload):
            if self.key == 'g1':
                raise GeminiTransportError('http_error', 'limited', http_status=429)
            if self.key == 'g2':
                raise GeminiTransportError('http_error', 'gone', http_status=403)
            return {'body': {'lines': [{'n': 1, 'pass': True, 'seen': 'ok'}]}, 'raw': ''}
    s = cfg(geminis='g1,g2,g3')
    received, idx = K.gemini(Transport, 'm', lambda t: t.generate({}), s)
    assert idx == 2 and made == ['g1', 'g2', 'g3'] and K.cooling('gemini') == [0, 1]
    monkeypatch.setattr(IC, 'settings', lambda: s)
    monkeypatch.setattr(IC, 'transport_factory', Transport, raising=False)
    rec = IC.drawn_sheet_check(b'a', [], [{'check': 'x', 'pass_when': 'y', 'weight': 'must'}], 'p', Transport)   # design/117: the sheet read
    assert rec['key_index'] == 2 and rec['lines'][0]['pass'] is True

    class Blocked(Transport):
        def generate(self, payload):
            raise GeminiTransportError('blocked_response', 'safety')
    with pytest.raises(GeminiTransportError, match='safety'):   # not the key's fault: no cooling, the error is the caller's as before
        K.gemini(Blocked, 'm', lambda t: t.generate({}), s)
    assert K.cooling('gemini') == [0, 1]
    with pytest.raises(RuntimeError, match='No Gemini key'):
        K.gemini(Transport, 'm', lambda t: t.generate({}), cfg())
