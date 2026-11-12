"""Step A of the integration (videobuilder-v4/integration/step-a-requirements.md, SK 12 Nov 2026): one record row per attempt of a shot,
never overwritten; a handed-in file says how it was made and is recorded and shown as "made outside; checks skipped"."""
import pytest

from app import generations, visuals_stage as VS
from app.errors import Problem
from test_design151_refs_pure import KILN, MASON, NEW, doc_with, new_store
from test_visuals_stage_pure import FakeConn, USER, accepted, saved

OTHER = {'id': 'u2', 'name': 'Revathi'}
KEY, SHA = 'run-1/uploads/pour.mp4', 'sha-movie'


class Conn(FakeConn):
    """vw2_files answers for the upload; vw2_generations is a list of rows, as the table would hold them."""

    def __init__(self, broken=False):
        super().__init__([])
        self.rows, self.broken = [], broken

    def execute(self, sql, params=()):
        conn = self
        if 'from vw2_files' in sql:
            return type('R', (), {'fetchone': lambda _: {'key': params[1], 'sha256': SHA, 'bytes': 1000}})()
        if 'insert into vw2_generations' in sql:
            if self.broken:
                raise RuntimeError('the database is away')
            run_id, shot_id, how, record = params[0], params[1], params[2], params[3].obj
            row = {'run_id': run_id, 'shot_id': shot_id, 'attempt': 1 + max([r['attempt'] for r in self.rows if (r['run_id'], r['shot_id']) == (run_id, shot_id)] or [0]),
                   'how': how, 'verdict': None, 'record': record, 'created_at': '2026-11-12T10:00:00Z', 'updated_at': '2026-11-12T10:00:00Z'}
            self.rows.append(row)
            return type('R', (), {'fetchone': lambda _: row})()
        if 'from vw2_generations' in sql:
            return type('R', (), {'fetchall': lambda _: sorted((r for r in conn.rows if (r['run_id'], r['shot_id']) == (params[0], params[1])), key=lambda r: r['attempt'])})()
        return super().execute(sql, params)


@pytest.fixture
def film():
    doc = doc_with(KILN, MASON)
    return new_store(doc, {}, accepted=accepted(doc)), Conn()


def hand_in(store, conn, made, user=USER, shot='VS1', kind='movie'):
    return VS.add_asset(conn, store, user, NEW, [], shot, KEY, SHA, 1000, kind, 'Use my own file.', made)


def refused(fn):
    """The words of a refusal: a `need` (a ValueError the route turns into a refusal) or a Problem."""
    with pytest.raises((Problem, ValueError)) as e:
        fn()
    return getattr(e.value, 'message', None) or str(e.value)


# ---------- A2: a handed-in file says how it was made ----------

def test_a_hand_in_writes_one_record_row_with_the_words_the_file_and_who(film):
    store, conn = film
    hand_in(store, conn, 'Blender guide, GPT image still, Gemini edit, by hand on 11 Nov.')
    rows = generations.of_shot(conn, NEW['id'], 'VS1')
    assert [(r['attempt'], r['how']) for r in rows] == [(1, 'handed in')]
    entry = rows[0]['record'][0]
    assert entry['kind'] == 'handed in' and entry['checks'] == 'not run' and entry['made'].startswith('Blender guide')
    assert (entry['sha256'], entry['file_kind'], entry['by_name']) == (SHA, 'movie', 'SK') and entry['at']
    assert saved(store)['assets']['VS1']['made'].startswith('Blender guide')


@pytest.mark.parametrize('made', ['', '   ', '\n\t'])
def test_a_hand_in_without_the_words_is_refused_and_nothing_is_stored(film, made):   # edge 1
    store, conn = film
    message = refused(lambda: hand_in(store, conn, made))
    assert '--made' in message and 'how the file was made' in message
    assert 'VS1' not in saved(store)['assets'] and conn.rows == []


def test_words_longer_than_the_limit_are_refused_not_cut(film):   # edge 2
    store, conn = film
    message = refused(lambda: hand_in(store, conn, 'x' * 2049))
    assert '2,048' in message and 'VS1' not in saved(store)['assets'] and conn.rows == []
    hand_in(store, conn, 'x' * 2048)   # the limit itself is allowed
    assert len(conn.rows) == 1


def test_the_same_shot_handed_in_twice_is_two_rows_and_the_first_is_unchanged(film):   # edges 3, 4
    store, conn = film
    hand_in(store, conn, 'First try, by hand.')
    first = dict(conn.rows[0], record=[dict(e) for e in conn.rows[0]['record']])
    hand_in(store, conn, 'Second try, a new still.', user=OTHER, kind='still')
    rows = generations.of_shot(conn, NEW['id'], 'VS1')
    assert [r['attempt'] for r in rows] == [1, 2] and rows[0] == first
    assert (rows[1]['record'][0]['by_name'], rows[1]['record'][0]['file_kind']) == ('Revathi', 'still')
    assert saved(store)['assets']['VS1']['made'] == 'Second try, a new still.'   # the shot shows the latest file


def test_when_the_record_cannot_be_written_no_file_is_placed(film):   # edge 5
    store, conn = film
    conn.broken = True
    with pytest.raises(RuntimeError):
        hand_in(store, conn, 'By hand.')
    assert 'VS1' not in saved(store)['assets']


def test_a_shot_that_does_not_exist_is_refused_before_any_record(film):   # edge 6
    store, conn = film
    refused(lambda: hand_in(store, conn, 'By hand.', shot='NOPE'))
    assert conn.rows == []


# ---------- A1: reading the record ----------

def test_a_shot_with_no_attempts_says_so(film):   # edge 7
    store, conn = film
    out = VS.generations_of(conn, store, NEW, [], 'VS1')
    assert out == {'shot_id': 'VS1', 'generations': [], 'message': 'No generations yet for VS1.'}


def test_a_shot_that_does_not_exist_and_has_no_rows_is_refused(film):   # edge 8
    store, conn = film
    assert 'NOPE' in refused(lambda: VS.generations_of(conn, store, NEW, [], 'NOPE'))


def test_rows_of_a_shot_the_plan_no_longer_holds_are_still_read(film):   # edge 9
    store, conn = film
    generations.opened(conn, NEW['id'], 'GONE', 'handed in', {'kind': 'handed in'})
    out = VS.generations_of(conn, store, NEW, [], 'GONE')
    assert [g['attempt'] for g in out['generations']] == [1]


def test_reading_lists_attempts_oldest_first_and_only_this_shot(film):
    store, conn = film
    hand_in(store, conn, 'One.')
    generations.opened(conn, NEW['id'], 'OTHER', 'handed in', {'kind': 'handed in'})
    hand_in(store, conn, 'Two.')
    out = VS.generations_of(conn, store, NEW, [], 'VS1')
    assert [(g['attempt'], g['record'][0]['made']) for g in out['generations']] == [(1, 'One.'), (2, 'Two.')] and 'message' not in out


def test_every_entry_is_dated_so_the_time_per_step_can_be_read():
    conn = Conn()
    row = generations.opened(conn, 'run-1', 'S1', 'handed in', {'kind': 'handed in'})
    assert row['record'][0]['at'].endswith('Z') and len(row['record'][0]['at']) >= 20


# ---------- the page and the status say "made outside; checks skipped" ----------

def test_the_page_and_the_status_mark_a_handed_in_shot(film):
    store, conn = film
    hand_in(store, conn, 'By hand, outside the application.')
    asset = VS.page_view(conn, store, NEW, [], 'VW-20')['gaps'][1]['shots'][0]['asset']
    assert asset['made_outside'] is True and asset['made'] == 'By hand, outside the application.'
    shot = next(s for gap in VS.status(conn, store, NEW, [], repair=False)['gaps'] for s in gap['shots'] if s['shot_id'] == 'VS1')
    assert shot['made_outside'] is True


def test_a_file_handed_in_before_this_release_is_marked_all_the_same(film):   # edge 10
    store, conn = film
    hand_in(store, conn, 'By hand.')
    s = saved(store)
    s['assets']['VS1'].pop('made')   # as stored before this release; no record row exists either
    VS.save_session(store, NEW, s)
    conn.rows.clear()
    asset = VS.page_view(conn, store, NEW, [], 'VW-20')['gaps'][1]['shots'][0]['asset']
    assert asset['made_outside'] is True and asset['made'] == ''


def test_a_shot_filled_by_the_application_is_not_marked(film):
    store, conn = film
    shots = [s for gap in VS.status(conn, store, NEW, [], repair=False)['gaps'] for s in gap['shots']]
    assert shots and not any(s.get('made_outside') for s in shots)
