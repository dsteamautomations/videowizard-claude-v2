"""Hand-over stoppers (SK, 23 Nov 2026). Fix 1: the final on Resolve Studio takes the Resolve timeline file into the delivery record only when
it is a file stored for this run; a path on the editing computer (every plugin up to 0.106.1) no longer stops the final. Films for the team:
every signed-in member of the application opens every film (before: the member who started it, and Admins). Without a database."""
import pytest

from app import core
from app.errors import Problem
from app.stage3 import delivery as D

RUN = {'id': 'r1', 'code': 'VW-19'}
FILM = {'name': 'assembly.mp4', 'key': 'r1/assembly/assembly.mp4', 'sha256': 'f' * 64, 'bytes': 9}
OUTPUTS = [{'stage': 'assembly', 'unit': None, 'files': [FILM]}]
QUOTE = 'I watched it, listened to it, read the subtitles (srt), the timeline is verified and the package is complete'
STORED = {'name': 'VW-19.drt', 'key': 'r1/delivery/VW-19.drt', 'sha256': 'd' * 64, 'bytes': 7, 'receipt': True, 'location': 'storage'}


def final(monkeypatch, report):
    session = {'bundle': {'film_sha256': FILM['sha256'], 'manifest': {'key': 'r1/delivery/manifest.json', 'sha256': 'm' * 64, 'bytes': 3}},
               'resolve': {'state': 'reported', 'machine': 'pc-b', 'film_sha256': FILM['sha256'], 'report': report}}
    sent = {}
    monkeypatch.setattr(D, 'session_of', lambda store, run: session)
    monkeypatch.setattr(D, 'save_session', lambda store, run, s: None)
    monkeypatch.setattr(D.S2, 'load_json', lambda store, key: {'files': [{'name': 'Subtitles.srt', 'key': 'r1/delivery/Subtitles.srt', 'sha256': 's' * 64, 'bytes': 5}]})
    monkeypatch.setattr(D.jobs, 'record_file', lambda *a, **kw: None)
    monkeypatch.setattr(D.core, 'output', lambda conn, user, run, body: sent.update(body) or {'id': 'o-9'})
    out = D.final(None, None, {'id': 'u2'}, RUN, OUTPUTS, QUOTE)
    return out, [f['name'] for f in sent['files']]


def test_the_final_on_studio_no_longer_stops_on_a_timeline_file_sent_as_a_path(monkeypatch):
    out, names = final(monkeypatch, {'route': 'studio', 'drt_verified': True, 'drt': 'C:\\runs\\VW-19\\edit\\Timeline\\VW-19.drt', 'drp': 'C:\\x.drp'})
    assert names == ['Approved-film.mp4', 'manifest.json', 'Subtitles.srt'] and out['timeline_file'] is False


def test_a_stored_timeline_file_is_taken_into_the_delivery_record(monkeypatch):
    out, names = final(monkeypatch, {'route': 'studio', 'drt_verified': True, 'drt': STORED})
    assert names[-1] == 'Approved-timeline.drt' and out['timeline_file'] is True and out['files'] == 4


def test_a_timeline_record_of_another_film_or_a_half_record_is_left_out(monkeypatch):
    for bad in ({**STORED, 'key': 'r2/delivery/VW-20.drt'}, {'key': 'r1/delivery/VW-19.drt'}, ['r1/delivery/VW-19.drt']):
        out, names = final(monkeypatch, {'route': 'studio', 'drt_verified': True, 'drt': bad})
        assert 'Approved-timeline.drt' not in names and out['timeline_file'] is False


def test_the_free_route_sends_no_timeline_file_and_the_final_is_as_before(monkeypatch):
    out, names = final(monkeypatch, {'route': 'free', 'timeline_verified': True})
    assert names == ['Approved-film.mp4', 'manifest.json', 'Subtitles.srt']


# ---------- films for the team ----------

class Conn:
    def __init__(self, row):
        self.row, self.sql = row, []

    def execute(self, sql, params=()):
        self.sql.append(sql)
        conn = self

        class R:
            def fetchone(self):
                return conn.row

            def fetchall(self):
                return [conn.row]
        return R()


COLLEAGUE = {'id': 'u2', 'name': 'Gautam', 'role': 'Member'}


def test_a_member_opens_a_film_a_colleague_started():
    assert core.load_run(Conn({'id': 'r1', 'owner_id': 'u1', 'status': 'open'}), COLLEAGUE, 'r1')['owner_id'] == 'u1'


def test_a_film_that_does_not_exist_is_still_not_found():
    with pytest.raises(Problem) as exc:
        core.load_run(Conn(None), COLLEAGUE, 'r9')
    assert exc.value.status == 404


def test_a_member_lists_every_film_the_newest_two_hundred():
    conn = Conn({'id': 'r1', 'owner_id': 'u1'})
    assert core.list_runs(conn, COLLEAGUE) == [conn.row]
    assert 'owner_id =' not in conn.sql[0] and 'limit 200' in conn.sql[0]
