"""Defect 51 (14 Nov 2026): an upload the provider refused or that never got through left the clip marked running for the whole lease, with no worker
on it, and fifteen such clips filled every analysis slot. Nothing was sent to the model yet, so the clip is handed back at once with its reason."""
import hashlib
import json

import pytest

from app import analysis_jobs as AJ
from app.video_evidence.transport import GeminiTransportError

DATA = b'clip bytes'


class Store:
    def get(self, key):
        return DATA


def run(monkeypatch, tmp_path, error):
    class Transport:
        def __init__(self, *a, **kw):
            pass

        def upload(self, *a, **kw):
            raise error

    monkeypatch.setattr(AJ, 'SPOOL', tmp_path)
    monkeypatch.setattr(AJ, 'storage', lambda: Store())
    monkeypatch.setattr(AJ, 'renew', lambda jid, phase: None)
    monkeypatch.setattr(AJ, '_key', lambda: (0, 'k'))
    monkeypatch.setattr(AJ, '_cool', lambda exc, idx: None)
    monkeypatch.setattr(AJ, 'transport_factory', Transport)
    request = {'clip': {'name': 'a.mp4', 'sha256': hashlib.sha256(DATA).hexdigest(), 'duration_s': 5}, 'identity': {'understand_audio': True, 'model': 'm'}, 'mime': 'video/mp4'}
    (tmp_path / 'j1.request.json').write_text(json.dumps(request), encoding='utf-8')
    return AJ.process({'id': 'j1', 'run_id': 'r1', 'status': 'running', 'request': {}})


def test_a_refused_upload_is_handed_back_as_rejected_with_the_providers_reason(monkeypatch, tmp_path, capsys):
    exc = GeminiTransportError('http_error', 'refused', http_status=429, metadata={'provider_error': {'message': 'Spending cap reached', 'status': 'RESOURCE_EXHAUSTED'}})
    status, result, error, cost, retry_in = run(monkeypatch, tmp_path, exc)
    assert status == 'rejected' and result['http_status'] == 429 and result['phase'] == 'upload' and result['key_index'] == 0
    assert 'upload' in error and '429' in error and cost is None and retry_in is None
    assert 'analysis upload failed' in capsys.readouterr().out   # the worker's log names the step and the reason


def test_an_upload_that_never_got_through_is_a_failure_the_server_retries(monkeypatch, tmp_path):
    status, result, error, _, _ = run(monkeypatch, tmp_path, GeminiTransportError('network_error', 'no connection'))
    assert status == 'failed' and result == {'failure': 'upload', 'detail': 'network_error'} and 'no connection' in error
    assert AJ.passing_failure(status, result)   # retried by the server, up to three times; nothing was sent to the model


@pytest.mark.parametrize('code', ['upload_identity', 'upload_expired', 'source_identity'])
def test_a_receipt_or_source_fault_is_failed_and_not_retried_by_itself(monkeypatch, tmp_path, code):
    status, result, _, _, _ = run(monkeypatch, tmp_path, GeminiTransportError(code, 'x'))
    assert status == 'failed' and not AJ.passing_failure(status, result)
