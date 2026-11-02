"""design/139 R2 (SK, 2 Nov 2026, design/138 A4): Eleven v4 only; its two settings shown and changeable on the voices page; a narration uses the settings of
that voice's latest audition (the fault: it used the defaults); v2 and v3 are refused on both front ends."""
import pytest

from app import jobs, voices as V
from app.errors import Problem


def test_v4_settings_are_checked_and_default_to_half_and_three_quarters():
    assert V.v4_settings(None) == {'stability': 0.5, 'similarity_boost': 0.75}
    assert V.v4_settings({'stability': 0.3, 'similarity_boost': 0.9}) == {'stability': 0.3, 'similarity_boost': 0.9}
    for bad in ({'stability': 1.2, 'similarity_boost': 0.5}, {'stability': 0.5}, {'stability': 0.5, 'similarity_boost': 0.5, 'style': 0}, {'stability': 'high', 'similarity_boost': 0.5}):
        with pytest.raises(Problem):
            V.v4_settings(bad)


class Conn:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql, args):
        row = self.rows.get(args[1])
        return type('R', (), {'fetchone': lambda s: row})()


def test_the_narration_uses_the_latest_audition_settings(monkeypatch):
    state = V.new_page_state()
    conn = Conn({'v1': {'model': 'eleven_v4', 'settings': {'stability': 0.3, 'similarity_boost': 0.8}},
                 'v3': {'model': 'eleven_multilingual_v2', 'settings': {'stability': 0.5, 'similarity_boost': 0.75, 'style': 0, 'speed': 1, 'use_speaker_boost': True}}})
    sent = []
    monkeypatch.setattr(V, 'page_state', lambda store, run: state)
    monkeypatch.setattr(V, 'save_doc', lambda *a: None)
    monkeypatch.setattr(V, 'direction_of', lambda store, run: None)   # design/144 V3: the narration reads the direction's number
    monkeypatch.setattr(V, 'script_text', lambda store, outputs: ({'spoken_text': 'Hello.'}, None))
    monkeypatch.setattr(jobs, 'submit_voice', lambda conn, user, run, outputs, req, rid, store=None: (sent.append(req) or {'id': 1, 'request': req}))
    for vid in ('v1', 'v2', 'v3'):
        V.narrate(conn, None, {'name': 'SK'}, {'id': 'r'}, [], vid, 'rid')
    assert sent[0]['model_id'] == 'eleven_v4' and sent[0]['settings'] == {'stability': 0.3, 'similarity_boost': 0.8}
    assert sent[1]['settings'] == sent[2]['settings'] == {'stability': 0.5, 'similarity_boost': 0.75}   # no audition, or one on a retired model: the v4 defaults


def test_v2_and_v3_are_refused():
    with pytest.raises(Problem) as e:
        jobs.voice_model({'model_id': 'eleven_multilingual_v2'})
    assert 'v4' in e.value.message
    assert jobs.voice_model({}) == 'eleven_v4' and jobs.voice_model({'model_id': 'eleven_v4'}) == 'eleven_v4'
