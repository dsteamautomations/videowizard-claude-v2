"""Defect 40 (VW-12, 31 Oct 2026): measure asked Gemini for 4,096 tokens with no thinking level, so the answer was cut off every time;
three more calls had the same shape. A measure naming a rejected frame now says which frame, why, and the approved ones."""
import json

import pytest

from app import visuals_stage as VS


def session_with_frames():
    return {'references': {'F1': {'id': 'F1', 'kind': 'frame', 'status': 'rejected', 'element_id': 'trowel', 'key': 'k1'},
                           'F2': {'id': 'F2', 'kind': 'frame', 'status': 'approved', 'element_id': 'trowel', 'key': 'k2', 'source': {'media_id': 'c1', 'requested_s': 3}}}}


def test_a_rejected_frame_is_named_with_the_approved_ones(monkeypatch):
    monkeypatch.setattr(VS, 'session_of', lambda store, run, outputs: session_with_frames())
    with pytest.raises(ValueError, match=r"F1 was rejected in the picture round: measure reads approved footage frames only; trowel's: F2\."):
        VS.measure(None, {'id': 'u'}, {'id': 'r'}, [], ['F1'], 'the blade length')


def test_measure_asks_for_room_to_answer(monkeypatch):
    s = session_with_frames()
    monkeypatch.setattr(VS, 'session_of', lambda store, run, outputs: s)
    monkeypatch.setattr(VS, 'save_session', lambda store, run, session: None)
    monkeypatch.setattr(VS.keys, 'pool', lambda *a: ['k'])
    sent = {}

    class T:
        def generate(self, req):
            sent.update(req)
            return {'body': {'measurements': [], 'limits': ''}}
    monkeypatch.setattr(VS.keys, 'gemini', lambda transport, model, call, *a, **kw: (call(T()), 0))

    class Store:
        def get(self, key):
            return b'png'
    VS.measure(Store(), {'id': 'u'}, {'id': 'r'}, [], ['F2'], 'the blade length')
    assert sent['generationConfig']['maxOutputTokens'] == 32768


def test_the_other_three_calls_think_low_with_room():
    src = open(VS.__file__, encoding='utf-8').read()
    for schema in ('FIGURE_SCHEMA', 'NOT_THIS_SCHEMA', 'PAIR_SCHEMA'):
        assert f"'responseJsonSchema': {schema}, 'thinkingConfig': {{'thinkingLevel': 'LOW'}}, 'maxOutputTokens': 8192}}" in src
