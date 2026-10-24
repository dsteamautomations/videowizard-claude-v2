"""design/58 (L14): a broken connection is retried for up to three minutes inside request(); then the outcome is `unreachable`,
not `tell_builder`. A read that times out is the server busy (design/92), retried, then `wait`. The server is a fake client; sleep and the clock are patched."""
import json

import httpx
import pytest

from conftest import PLUGIN
import vw


class FakeClient:
    """Raises the given exceptions in turn, then answers 200 with a JSON body; records every request's json."""

    def __init__(self, failures, body=None):
        self.failures, self.body, self.sent = list(failures), body or {'ok': True}, []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def request(self, method, path, **kw):
        self.sent.append(kw.get('json'))
        if self.failures:
            raise self.failures.pop(0)
        return httpx.Response(200, json=self.body, request=httpx.Request(method, 'http://x' + path))


@pytest.fixture
def clock(monkeypatch):
    """time.sleep advances a fake monotonic clock instead of waiting; returns the list of sleeps."""
    state = {'now': 1000.0, 'sleeps': []}
    monkeypatch.setattr(vw.time, 'monotonic', lambda: state['now'])

    def sleep(s):
        state['sleeps'].append(s)
        state['now'] += s
    monkeypatch.setattr(vw.time, 'sleep', sleep)
    return state


def use(monkeypatch, client):
    monkeypatch.setattr(vw, 'api', lambda: client)
    return client


def test_a_connection_error_that_clears_is_retried_and_the_body_returned(monkeypatch, clock, capsys):
    c = use(monkeypatch, FakeClient([httpx.ConnectError('nodename nor servname provided'), httpx.ConnectError('nodename nor servname provided')]))
    payload, code = vw.request('GET', '/api/runs/r/analysis')
    assert (payload, code) == ({'ok': True}, 0) and len(c.sent) == 3
    assert clock['sleeps'] == [15, 15]
    err = capsys.readouterr().err
    assert err.count('trying again in 15 s') == 2 and 'ConnectError: nodename nor servname provided' in err


def test_after_three_minutes_the_outcome_is_unreachable_with_the_cause(monkeypatch, clock):
    c = use(monkeypatch, FakeClient([httpx.ConnectError('boom')] * 50))
    payload, code = vw.request('GET', '/api/runs/r/analysis')
    assert code == 2 and payload['action'] == 'unreachable'
    assert 'ConnectError: boom' in payload['message'] and '3 minutes' in payload['message'] and 'run the same command again' in payload['message']
    assert 'File a defect only if it is unreachable again' in payload['message'] and 'tell_builder' not in json.dumps(payload)
    assert sum(clock['sleeps']) <= 180 and 10 <= len(c.sent) <= 13   # every 15 s for three minutes, then it gives up


@pytest.mark.parametrize('exc', [httpx.ConnectTimeout('slow'), httpx.ReadError('reset'), httpx.RemoteProtocolError('closed')])
def test_the_other_broken_connection_errors_are_retried_too(monkeypatch, clock, exc):
    c = use(monkeypatch, FakeClient([exc]))
    assert vw.request('GET', '/x') == ({'ok': True}, 0) and len(c.sent) == 2 and clock['sleeps'] == [15]


def test_a_read_that_times_out_is_the_server_busy_never_a_defect(monkeypatch, clock):
    """design/92 (L60): a GET that times out is tried again every 15 s for three minutes; then `wait`, never `tell_builder`."""
    c = use(monkeypatch, FakeClient([httpx.ReadTimeout('slow')] * 2))
    assert vw.request('GET', '/x') == ({'ok': True}, 0) and len(c.sent) == 3 and clock['sleeps'] == [15, 15]
    clock['sleeps'].clear()
    use(monkeypatch, FakeClient([httpx.ReadTimeout('slow')] * 40))
    payload, code = vw.request('GET', '/x')
    assert code == 2 and payload['action'] == 'wait' and 'busy' in payload['message'] and 'not a defect' in payload['message'] and sum(clock['sleeps']) <= 180


def test_a_write_that_times_out_says_check_the_status_and_is_not_repeated(monkeypatch, clock):
    use(monkeypatch, FakeClient([httpx.ReadTimeout('slow')] * 3))
    payload, code = vw.request('POST', '/x', wait=600)
    assert code == 2 and payload['action'] == 'refused' and 'still working' in payload['message'] and clock['sleeps'] == []
    c = use(monkeypatch, FakeClient([httpx.ReadTimeout('slow')] * 3))
    payload, code = vw.request('POST', '/x', json={'a': 1})
    assert code == 2 and payload['action'] == 'wait' and 'status' in payload['message'] and 'not a defect' in payload['message'] and len(c.sent) == 1 and clock['sleeps'] == []


def test_a_retried_write_sends_the_same_request_id(monkeypatch, clock):
    c = use(monkeypatch, FakeClient([httpx.ConnectError('boom')], body={'id': 'out-1'}))
    assert vw.write('/api/runs/r/output', {'stage': 'intake'}) == {'id': 'out-1'}
    ids = [s['request_id'] for s in c.sent]
    assert len(ids) == 2 and len(set(ids)) == 1   # idempotent on the server: the retry is the same request


def test_the_command_doc_names_the_unreachable_outcome():
    doc = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert '`unreachable`' in doc and 'same command again' in doc and 'tell_builder' in doc
