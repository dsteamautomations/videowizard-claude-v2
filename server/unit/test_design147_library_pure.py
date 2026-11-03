"""design/147 L1 (SK, 3 Nov 2026): the brand-generic library: candidates from the studied clips, the mark recorded with the operator's words (every studied
clip stored, the named ones generic), the gate before the first cut, unmark by any team member, and the older way (films from before skip it)."""
import json

import pytest

from app import brandlib as B
from app.errors import Problem

CLIENT = 'NARDEP'
RUN = {'id': 'r1', 'code': 'VW-20', 'status': 'open', 'client_id': CLIENT, 'film': {}}
OLD = {'id': 'r0', 'code': 'VW-13', 'status': 'open', 'client_id': CLIENT, 'film': None}
USER = {'id': 'u1', 'name': 'Revathi'}


def outputs(excluded=()):
    media = {'stage': 'media', 'unit': None, 'summary': {'clips': [{'id': 'a1', 'name': 'C1.mp4', 'sha256': 'a' * 64, 'duration_s': 4.0, 'fps': '25', 'width': 1920, 'height': 1080},
                                                                   {'id': 'b2', 'name': 'C2.mp4', 'sha256': 'b' * 64, 'duration_s': 6.0, 'fps': '25', 'width': 1920, 'height': 1080},
                                                                   {'id': 'c3', 'name': 'C3.mp4', 'sha256': 'c' * 64, 'duration_s': 2.0, 'fps': '25'}]}}
    an = [{'stage': 'analysis', 'unit': 'a1', 'files': [{'name': 'a1.evidence.json', 'key': 'r1/analysis/a1.evidence.json'}],
           'summary': {'descriptive_name': 'yard wide shot', 'summary_card': ['1 OVERVIEW: the yard'], 'contract_version': 'clip-log-v1', 'excluded': 'a1' in excluded}},
          {'stage': 'analysis', 'unit': 'b2', 'files': [], 'summary': {'descriptive_name': 'the MD speaking', 'summary_card': ['1 OVERVIEW: speech'], 'contract_version': 'clip-log-v1'}},
          {'stage': 'analysis', 'unit': 'c3', 'files': [], 'summary': {'excluded': True, 'note': 'bad file'}}]   # excluded before a study: no description
    return [media] + an


class Conn:
    def __init__(self):
        self.sql = []

    def execute(self, sql, args=()):
        self.sql.append((sql, args))
        return type('R', (), {'fetchone': lambda s: None, 'fetchall': lambda s: []})()


class Store:
    def get(self, k):
        return json.dumps({'log': {'clip_overview': 'The yard from the gate.', 'entities': [{'name': 'mortar pan'}, {'name': 'plinth'}]}}).encode()


def test_candidates_are_the_studied_clips_with_their_short_description():
    rows = B.candidates(None, RUN, outputs(excluded=('a1',)))
    assert [r['name'] for r in rows] == ['C1.mp4', 'C2.mp4'] and rows[0]['excluded'] is True and rows[0]['descriptive_name'] == 'yard wide shot'
    assert rows[0]['evidence_key'] == 'r1/analysis/a1.evidence.json' and rows[1]['card'] == ['1 OVERVIEW: speech']


def test_the_gate_waits_for_the_answer_on_a_new_film_and_skips_an_older_one():
    with pytest.raises(Problem) as e:
        B.need_marked(RUN)
    assert 'vw library mark' in e.value.message
    B.need_marked(OLD)
    B.need_marked({**RUN, 'film': {'library': {'asked': True, 'generic': []}}})
    assert B.asked(OLD) == {'skipped': 'a film started before the library'} and B.asked(RUN) is None


def test_mark_stores_every_studied_clip_and_records_the_answer_with_the_words(monkeypatch):
    monkeypatch.setattr(B, 'fingerprint', lambda store, run, clip, ffmpeg='ffmpeg': [1, 2, 3])
    conn = Conn()
    out = B.mark(conn, Store(), USER, RUN, outputs(), ['C1.mp4'], 'yes, the yard shot is generic')
    assert out == {'stored': 2, 'generic': ['C1.mp4'], 'skipped': None}
    inserts = [a for s, a in conn.sql if 'insert into vw2_library' in s]
    assert len(inserts) == 2 and inserts[0][3] is True and inserts[1][3] is False   # C1 generic, C2 stored but not generic
    assert inserts[0][6] == 'r1/media/C1.mp4' and inserts[0][5].obj['overview'] == 'The yard from the gate.' and inserts[0][5].obj['entities'] == ['mortar pan', 'plinth']
    rec = next(a for s, a in conn.sql if 'update vw2_runs set film' in s)
    assert rec[0].obj['generic'] == ['C1.mp4'] and rec[0].obj['quote'] == 'yes, the yard shot is generic' and rec[0].obj['by'] == 'Revathi'


def test_mark_refuses_an_unknown_name_no_words_and_an_older_film():
    with pytest.raises(Problem) as e:
        B.mark(Conn(), Store(), USER, RUN, outputs(), ['C9.mp4'], 'yes')
    assert 'C9.mp4' in e.value.message and 'C1.mp4' in e.value.message
    with pytest.raises(Problem):
        B.mark(Conn(), Store(), USER, RUN, outputs(), [], ' ')
    with pytest.raises(Problem) as e:
        B.mark(Conn(), Store(), USER, OLD, outputs(), [], 'none')
    assert 'started before' in e.value.message


def test_none_is_an_answer_and_a_run_without_a_client_stores_nothing(monkeypatch):
    monkeypatch.setattr(B, 'fingerprint', lambda *a, **k: None)
    conn = Conn()
    assert B.mark(conn, Store(), USER, RUN, outputs(), [], 'none of these')['generic'] == []
    out = B.mark(Conn(), Store(), USER, {**RUN, 'client_id': None}, outputs(), [], 'none')
    assert out['stored'] == 0 and 'no client' in out['skipped']


def test_unmark_needs_the_name_and_the_words():
    with pytest.raises(Problem):
        B.unmark(Conn(), USER, RUN, 'C1.mp4', '')
    with pytest.raises(Problem):
        B.unmark(Conn(), USER, {**RUN, 'client_id': None}, 'C1.mp4', 'wrong, it shows the MD')
    with pytest.raises(Problem) as e:
        B.unmark(Conn(), USER, RUN, 'C1.mp4', 'wrong, it shows the MD')   # the fake conn finds no row
    assert e.value.status == 404
