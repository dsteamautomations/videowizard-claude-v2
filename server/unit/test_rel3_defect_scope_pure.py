"""Release 3, C6 (SK, 20 Nov 2026, answer 7: "Block only what it names"): an open defect holds only the shot or the step it names; the rest of
the run continues. Before (design/48): one open defect refused every write of the run. The shot is kept as the first line of the defect's log
excerpt (no new column); a defect that names nothing holds the step it was filed in; a row written by the older server with no step holds
every write, as it did. Without a database."""
import uuid

import pytest

from app import core, main as API, visuals_stage as V
from app.errors import Problem

RUN_ID = uuid.uuid4()
USER = {'id': 'u1', 'name': 'Asha', 'role': 'Operator'}


class Conn:
    """The two statements the gate runs: the run, and its open defects."""
    def __init__(self, defects):
        self.defects, self.inserted = defects, None

    def execute(self, sql, params=()):
        conn = self

        class R:
            def fetchone(self):
                if 'insert into vw2_defects' in sql:
                    conn.inserted = params
                    return {'id': 9}
                return {'id': RUN_ID, 'owner_id': 'u1', 'status': 'open'}

            def fetchall(self):
                return [d for d in conn.defects if d.get('status', 'open') == 'open'] if 'vw2_defects' in sql else []
        return R()


def row(n, stage='visuals', shot='', status='open', log='the last lines'):
    return {'id': n, 'stage': stage, 'log_excerpt': (core.SHOT_LINE + shot + '\n' if shot else '') + log, 'status': status}


def write(defects, **about):
    return core.load_run(Conn(defects), USER, RUN_ID, lock=True, **about)


def refused(defects, **about):
    with pytest.raises(Problem) as e:
        write(defects, **about)
    assert e.value.code == 'DEFECT_OPEN' and e.value.status == 409
    return e.value


def test_a_defect_that_names_a_shot_holds_that_shot_and_nothing_else():
    one = [row(7, shot='S2')]
    assert write(one, stage='visuals', shots=['S1'])['id'] == RUN_ID            # a write for another shot passes
    assert write(one, stage='visuals')['id'] == RUN_ID                          # a write of the step that names no shot (the plan, the next card) passes
    assert write(one)['id'] == RUN_ID                                           # a write that states no step passes
    e = refused(one, stage='visuals', shots=['S2'])                             # the held shot is refused
    assert e.message == ('defect 7 is open on this run and holds shot S2 only; the rest of the run goes on. Do not send this call again now: tell the operator, '
                         'go on with the other shots, and send it once the builder says the defect is fixed.')
    assert e.extra == {'defect': 7, 'defects': [7], 'holds': {'shot': 'S2'}}
    refused(one, stage='visuals', shots=['S1', 'S2'])                           # a call for several shots, the held one among them


def test_a_defect_that_names_a_step_and_no_shot_holds_the_writes_of_that_step():
    step = [row(8, stage='visuals')]
    e = refused(step, stage='visuals', shots=['S1'])
    assert e.message == ('defect 8 is open on this run and holds the visuals step; the builder resolves it, then the run continues. Do not send this call again now: '
                         'tell the operator, and send it once the builder says the defect is fixed.')
    assert e.extra['holds'] == {'stage': 'visuals'}
    assert write(step, stage='voice')['id'] == RUN_ID                           # a write of another step passes
    refused(step, stage=('options', 'visuals'))                                 # a write taken at either of two steps
    refused(step)                                                               # a write that states no step is held, as before


def test_a_row_of_the_older_server_with_no_step_holds_every_write_as_it_did():
    old = [{'id': 3, 'stage': None, 'log_excerpt': None, 'status': 'open'}]
    assert refused(old, stage='visuals', shots=['S1']).message.startswith('defect 3 is open on this run and holds every step; the builder resolves it')
    refused(old, stage='voice')
    refused(old)


def test_two_defects_each_hold_their_own_and_a_fixed_one_releases():
    two = [row(7, shot='S2'), row(8, shot='S5')]
    assert write(two, stage='visuals', shots=['S1', 'S3'])['id'] == RUN_ID
    assert refused(two, stage='visuals', shots=['S5']).extra['defect'] == 8
    assert refused(two, stage='visuals', shots=['S5', 'S2']).extra['defects'] == [7, 8]
    assert write([row(7, shot='S2', status='fixed'), row(8, shot='S5')], stage='visuals', shots=['S2'])['id'] == RUN_ID   # 7 is fixed: S2 is free again
    assert write([row(8, stage='visuals', status='fixed')], stage='visuals')['id'] == RUN_ID
    assert core.load_run(Conn(two), USER, RUN_ID)['id'] == RUN_ID               # a read never stops on a defect


def test_the_shot_is_kept_in_the_first_line_of_the_log_excerpt_and_read_back(monkeypatch):
    monkeypatch.setattr(core, 'next_for', lambda conn, run: {'stage': 'visuals'})
    conn = Conn([])
    assert core.file_defect(conn, USER, {'id': RUN_ID}, None, 'the brief is refused', 'line 1\nline 2', shot='S2') == {'ticket': 9, 'holds': {'shot': 'S2'}}
    assert conn.inserted == (RUN_ID, 'visuals', 'the brief is refused', 'holds shot: S2\nline 1\nline 2', 'u1')   # the step it was filed in, when none is named
    assert core.defect_shot({'log_excerpt': conn.inserted[3]}) == 'S2'
    assert core.file_defect(conn, USER, {'id': RUN_ID}, 'voice', 'no sound', None) == {'ticket': 9, 'holds': {'stage': 'voice'}}
    assert conn.inserted == (RUN_ID, 'voice', 'no sound', '', 'u1')            # no shot: the excerpt as it was sent
    assert core.defect_shot({'log_excerpt': 'a log that happens to say holds shot: S9 further down\nholds shot: S9'}) == ''   # only the first line, from its start
    assert core.defect_shot({'log_excerpt': None}) == ''


def test_next_says_what_each_open_defect_holds(monkeypatch):
    monkeypatch.setattr(core, 'current_outputs', lambda c, rid: [])
    monkeypatch.setattr(core, 'attempts_for', lambda c, rid: {})
    monkeypatch.setattr(core, 'stage_table', lambda v: [])
    monkeypatch.setattr(core, 'compute_next', lambda *a: {'stage': 'visuals'})
    nxt = core.next_for(Conn([row(7, shot='S2'), row(8)]), {'id': RUN_ID, 'procedure_version': '3'})
    assert nxt['open_defects'] == [7, 8]                                        # as the older tool and the pages read it
    assert nxt['held'] == [{'defect': 7, 'shot': 'S2'}, {'defect': 8, 'stage': 'visuals'}]


def test_a_request_names_its_shots():
    assert API.shots_of(API.Draw(request_id=uuid.uuid4(), shot_id='S2')) == ['S2']
    assert API.shots_of(API.MotionColour(request_id=uuid.uuid4(), thing='t', colour='#112233', words='w', reason='r', shots=['S1', 'S4'])) == ['S1', 'S4']
    assert API.shots_of(API.Write(request_id=uuid.uuid4())) == []


def test_the_page_is_closed_only_by_a_defect_that_holds_its_step():
    held = [{'defect': 7, 'shot': 'S2'}, {'defect': 8, 'stage': 'voice'}]
    assert core.holding({'held': held}, 'visuals') == []                        # a shot's defect, another step's defect: the visuals page stays open
    assert core.holding({'held': held + [{'defect': 9, 'stage': 'visuals'}]}, 'visuals') == [9]
    assert core.holding({'held': [{'defect': 3}]}, 'visuals') == [3]            # the older row: every step
    assert core.holding({'open_defects': [4]}, 'visuals') == []


PLAN = {'gaps': [{'gap_id': 'G1', 'scenes': [{'id': 'sc', 'shots': [
    {'id': 'D1', 'visual_type': 'drawn', 'start_frame': 0}, {'id': 'D2', 'visual_type': 'drawn', 'start_frame': 50},
    {'id': 'D3', 'visual_type': 'drawn', 'start_frame': 100}, {'id': 'P1', 'visual_type': 'image', 'start_frame': 150},
    {'id': 'D4', 'visual_type': 'drawn', 'start_frame': 200}]}]}]}
SESSION = {'choice_selections': {}}


def test_the_next_step_line_names_the_held_shot_and_the_drawings_that_wait_on_it():
    line = V.held_line(PLAN, SESSION, [{'defect': 7, 'shot': 'D1'}])
    assert line == ('Defect 7 is open on D1: nothing more is sent for D1 until the builder says it is fixed. D2, D3 continue from it and wait for it too. '
                    'Everything else goes on.')
    assert V.held_line(PLAN, SESSION, [{'defect': 7, 'shot': 'D4'}]) == ('Defect 7 is open on D4: nothing more is sent for D4 until the builder says it is fixed. '
                                                                        'Everything else goes on.')   # D4 follows a picture: nothing continues from it
    assert V.held_line(PLAN, SESSION, [{'defect': 8, 'stage': 'visuals'}]) == ''   # a step's defect refuses the call itself
    assert V.held_line(PLAN, SESSION, []) == ''
