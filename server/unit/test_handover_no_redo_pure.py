"""Handover (SK, 11 Nov 2026): a run taken over on another computer starts where it stands; nothing finished is done again.
H1 the stage report (`next` carries `stage3` with one `do_next` line), H4 a repeated bundle, prepare, build or render is a no-op, H5 the DaVinci
ledger at the assembly stage, H6 the proof film waits to be watched; the edge cases H-E1 to H-E4 and H-E12; the digest question; the journey."""
import re
from pathlib import Path

import pytest

from app import core
from app.errors import Problem
from app.stage3 import assembly as A, delivery as D

ROOT = Path(__file__).resolve().parents[2]
RUN = {'id': 'r1', 'code': 'VW-19', 'client': 'c', 'procedure_version': '3'}
USER = {'id': 'u1'}
PLAN = {'duration_frames': 100, 'events': [{'kind': 'gap', 'beat_id': 'B1', 'gap_id': 'G1', 'timeline_in_frame': 0, 'timeline_out_frame': 100, 'timeline_frames': 100}],
        'gaps': [{'shot_id': 'G1', 'start_frame': 0, 'end_frame': 100}]}
MASTER = {'id': 'm-1', 'stage': 'master', 'unit': None, 'summary': {'version': 2, 'plan_digest': 'm2'}, 'files': [{'name': 'master-v2.json', 'key': 'k/m', 'sha256': 'm' * 64, 'bytes': 9}]}
VOICE = {'id': 'v-1', 'stage': 'voice', 'unit': None, 'summary': {}, 'files': [{'name': 'narration.mp3', 'key': 'k/n', 'sha256': 'n' * 64, 'bytes': 5}]}
MEDIA = {'id': 'me-1', 'stage': 'media', 'unit': None, 'summary': {'clips': []}, 'files': []}
FILM = {'key': 'k/film', 'sha256': 'f' * 64, 'bytes': 9}


def vis(oid='o-1'):
    return {'id': oid, 'stage': 'visuals', 'unit': 'G1', 'files': [{'name': 'VS1-asset.png', 'key': 'k/vs1-' + oid, 'sha256': 'a' * 64, 'bytes': 3}],
            'summary': {'shots': [{'shot_id': 'VS1', 'source': 'asset', 'kind': 'still', 'placement': {'start_frame': 0, 'end_frame': 100}, 'media': {'kind': 'still'}}]}}


OUTPUTS = [MASTER, VOICE, MEDIA, vis()]


class Store:
    def __init__(self):
        self.d, self.puts = {}, []

    def get(self, k):
        if k not in self.d:
            raise Problem(404, 'NOT_FOUND', 'no file')
        return self.d[k]

    def put(self, k, data, mime):
        self.d[k] = data
        self.puts.append(k)

    def exists(self, k):
        return k in self.d

    def made(self):
        """Everything written except the session itself: what a redo would add to."""
        return [k for k in self.puts if not k.endswith('stage3/session.json')]


class Rows:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class Conn:
    """The render jobs table, nothing else."""
    def __init__(self):
        self.jobs = {}

    def execute(self, sql, params=()):
        if sql.startswith('insert into vw2_jobs'):
            jid = f'job-{len(self.jobs) + 1}'
            self.jobs[jid] = {'status': 'queued', 'result': None, 'error': None}
            return Rows({'id': jid})
        if 'from vw2_jobs where id' in sql:
            return Rows(self.jobs.get(params[0]))
        return Rows(None)

    def finish(self, status='ready'):
        self.jobs[f'job-{len(self.jobs)}'].update(status=status, result=dict(FILM) if status == 'ready' else None, error=None if status == 'ready' else 'ffmpeg stopped')


@pytest.fixture
def film(monkeypatch):
    """Storage in memory, the render jobs in a dict, the stage 2 package fixed: bundle, prepare, build and render run for real."""
    monkeypatch.setattr(A.S2, '_file', lambda store, o, name: (PLAN, None))
    monkeypatch.setattr(A.S2, 'session_of', lambda store, run: {'package': {'narration_key': 'k/n', 'key': 'k/p', 'sha256': 'p' * 64, 'bytes': 1}})
    monkeypatch.setattr(A.S2, '_package', lambda store, s2: {'timeline': {'fps': 25, 'width': 1920, 'height': 1080}, 'sub_clips': [], 'narration': {}})
    monkeypatch.setattr(D.jobs, 'record_file', lambda *a, **kw: None)
    return Store(), Conn()


def session(store):
    return A.session_of(store, RUN)


def report(store, conn, outputs=OUTPUTS):
    s = session(store)
    A._refresh(conn, s)
    return A.progress(s, outputs)


def to_rendered(store, conn, outputs=OUTPUTS):
    """Computer A: the package, the fills, the build and the finished render."""
    D.bundle(conn, store, USER, RUN, outputs)
    A.prepare(conn, store, USER, RUN, outputs)
    A.build(conn, store, USER, RUN, outputs)
    A.render(conn, store, USER, RUN)
    conn.finish()


# ---------- H1: the stage report, one sub-state at a time ----------

def test_no_package_the_report_names_the_bundle():
    p = A.progress(None, OUTPUTS)
    assert p['package']['state'] == 'none' and '`vw delivery bundle`' in p['do_next'] and p['handover'] is None
    assert p['fills']['settled'] is False and p['built'] is None and p['film']['state'] == 'none' and p['review'] is None and p['resolve'] is None


def test_a_current_package_and_nothing_prepared(film):
    store, conn = film
    D.bundle(conn, store, USER, RUN, OUTPUTS)
    p = report(store, conn)
    assert p['package']['state'] == 'current' and p['package']['files'] >= 1
    assert '`vw assembly prepare`' in p['do_next'] and '`vw delivery check`' in p['handover']


def test_prepared_but_never_built_the_operator_is_still_to_be_asked(film):
    store, conn = film
    D.bundle(conn, store, USER, RUN, OUTPUTS)
    A.prepare(conn, store, USER, RUN, OUTPUTS)
    p = report(store, conn)
    assert p['fills'] == {'prepared': True, 'settled': False, 'count': 1} and p['built'] is None
    assert 'ask' in p['do_next'] and '`vw assembly build`' in p['do_next']


def test_built_and_not_rendered(film):
    store, conn = film
    D.bundle(conn, store, USER, RUN, OUTPUTS)
    A.prepare(conn, store, USER, RUN, OUTPUTS)
    A.build(conn, store, USER, RUN, OUTPUTS)
    p = report(store, conn)
    assert p['fills']['settled'] is True and p['built'] == {'version': 1} and p['film']['state'] == 'none'
    assert '`vw assembly render`' in p['do_next'] and 'ask' not in p['do_next']


def test_a_failed_render_is_named_and_may_be_started_again(film):
    store, conn = film
    to_rendered(store, conn)
    conn.finish('failed')
    p = report(store, conn)
    assert p['film']['state'] == 'failed' and 'ffmpeg stopped' in p['do_next'] and '`vw assembly render`' in p['do_next']
    A.render(conn, store, USER, RUN)
    assert len(conn.jobs) == 2


def test_h6_a_rendered_film_not_yet_reviewed_waits_to_be_watched(film):
    store, conn = film
    to_rendered(store, conn)
    p = report(store, conn)
    assert p['film'] == {'state': 'ready', 'version': 1, 'current': True} and p['review'] is None
    assert '`vw assembly fetch`' in p['do_next'] and 'watch and listen' in p['do_next'] and 'build' not in p['do_next'] and 'render' not in p['do_next'].replace('rendered', '')


def test_an_accepted_review_leads_to_the_record(film):
    store, conn = film
    to_rendered(store, conn)
    A.review(conn, store, USER, RUN, 'accepted', '', [], 'watched it and listened to it, yes')
    p = report(store, conn)
    assert p['review']['decision'] == 'accepted' and '`vw assembly record --quote`' in p['do_next']


def test_a_rejected_review_names_the_way_back(film):
    store, conn = film
    to_rendered(store, conn)
    A.review(conn, store, USER, RUN, 'rejected', 'the wall is wrong', [], 'no')
    p = report(store, conn)
    assert p['review']['decision'] == 'rejected' and 'the wall is wrong' in p['do_next'] and '`vw revise' in p['do_next']


def asm_output():
    return {'id': 'a-1', 'stage': 'assembly', 'unit': None, 'summary': {}, 'files': [{'name': 'assembly.mp4', **FILM}]}


def test_delivery_stage_the_early_package_is_not_the_full_one():
    p = A.progress({'bundle': {'early': True, 'film_sha256': None, 'files': 4, 'bytes': 9, 'inputs': A.early_inputs(OUTPUTS)}}, OUTPUTS + [asm_output()])
    assert p['recorded'] is True and p['package']['state'] == 'stale' and '`vw delivery bundle`' in p['do_next'] and p['handover'] is None


def test_delivery_stage_a_full_package_then_the_hand_over_then_the_final():
    s = {'bundle': {'film_sha256': FILM['sha256'], 'files': 9, 'bytes': 99}, 'resolve': None}
    p = A.progress(s, OUTPUTS + [asm_output()])
    assert p['package']['state'] == 'current' and '`vw delivery check`' in p['handover'] and '`vw delivery open`' in p['do_next']
    s['resolve'] = {'state': 'reported', 'machine': 'pc-davinci', 'film_sha256': FILM['sha256']}
    p = A.progress(s, OUTPUTS + [asm_output()])
    assert p['resolve'] == {'state': 'reported', 'machine': 'pc-davinci', 'this_package': True} and p['handover'] is None
    assert '`vw delivery final' in p['do_next'] and 'pc-davinci' in p['do_next']


def test_a_ledger_in_the_middle_is_shown_with_its_computer():
    s = {'bundle': {'early': True, 'film_sha256': None, 'files': 4, 'bytes': 9, 'inputs': A.early_inputs(OUTPUTS)}, 'resolve': {'state': 'dispatched', 'machine': 'mac-1', 'film_sha256': None}}
    p = A.progress(s, OUTPUTS)
    assert p['resolve']['state'] == 'dispatched' and 'mac-1' in p['handover'] and 'dispatched' in p['handover']


def test_next_carries_the_report_at_assembly_and_never_raises(film, monkeypatch):
    store, conn = film
    to_rendered(store, conn)
    from app import storage as ST
    monkeypatch.setattr(core, 'stage_table', lambda v: [])
    monkeypatch.setattr(core, 'current_outputs', lambda c, rid: OUTPUTS)
    monkeypatch.setattr(core, 'attempts_for', lambda c, rid: {})
    monkeypatch.setattr(core, 'open_defects', lambda c, rid: [])
    monkeypatch.setattr(ST, 'storage', lambda: store)
    monkeypatch.setattr(core, 'compute_next', lambda *a: {'stage': 'assembly'})
    assert '`vw assembly fetch`' in core.next_for(conn, RUN)['stage3']['do_next']
    monkeypatch.setattr(core, 'compute_next', lambda *a: {'stage': 'visuals'})
    assert 'stage3' not in core.next_for(conn, RUN)

    def broken():
        raise RuntimeError('storage down')
    monkeypatch.setattr(ST, 'storage', broken)
    monkeypatch.setattr(core, 'compute_next', lambda *a: {'stage': 'delivery'})
    assert core.next_for(conn, RUN)['stage3'] is None


# ---------- the digest question (requirements, section 6) ----------

def test_an_identical_rebuild_gives_the_same_digest(film):
    store, conn = film
    D.bundle(conn, store, USER, RUN, OUTPUTS)
    A.prepare(conn, store, USER, RUN, OUTPUTS)
    first = A.build(conn, store, USER, RUN, OUTPUTS)
    s = session(store)
    s['versions'], s['current'] = [], None   # forget the build: the second one is made from the same fills, gaps and master
    A.save_session(store, RUN, s)
    assert A.build(conn, store, USER, RUN, OUTPUTS)['digest'] == first['digest']


# ---------- H4: a repeated command does not redo finished work ----------

def test_a_repeated_bundle_answers_current_and_builds_nothing(film):
    store, conn = film
    first = D.bundle(conn, store, USER, RUN, OUTPUTS)
    made = store.made()
    again = D.bundle(conn, store, USER, RUN, OUTPUTS)   # H-E2: a second request waits for the run's lock, then lands here
    assert again['current'] is True and again['manifest'] == first['manifest'] and again['files'] == first['files'] and again['bytes'] == first['bytes']
    assert store.made() == made and 'current' in again['next']


def test_a_repeated_prepare_says_the_fills_are_settled_and_asks_nothing(film):
    store, conn = film
    to_rendered(store, conn)
    out = A.prepare(conn, store, USER, RUN, OUTPUTS)
    assert out['settled'] is True and out['choices']['VS1']['end_policy'] == 'hold_last' and 'VS1' in out['fills']
    assert 'ask' not in out['next'] and 'settled' in out['next'] and '`vw assembly fetch`' in out['next']
    assert session(store)['current'] and session(store)['renders']['assembly']['job_id'] == 'job-1'


def test_a_first_prepare_still_asks(film):
    store, conn = film
    D.bundle(conn, store, USER, RUN, OUTPUTS)
    out = A.prepare(conn, store, USER, RUN, OUTPUTS)
    assert not out.get('settled') and 'ask the operator per fill' in out['next']


def test_a_repeated_build_keeps_the_version_the_film_and_the_render(film):
    store, conn = film
    to_rendered(store, conn)
    made = store.made()
    out = A.build(conn, store, USER, RUN, OUTPUTS)
    s = session(store)
    assert out['unchanged'] is True and out['version'] == 1 and len(s['versions']) == 1 and s['renders']['assembly']['job_id'] == 'job-1'
    assert store.made() == made and '`vw assembly fetch`' in out['next']


def test_a_repeated_render_answers_ready_without_queueing(film):
    store, conn = film
    to_rendered(store, conn)   # the session still says queued: the answer reads the job row first
    out = A.render(conn, store, USER, RUN)
    assert out['ready'] is True and out['job_id'] == 'job-1' and len(conn.jobs) == 1 and '`vw assembly fetch`' in out['next']


def test_he1_taken_over_while_the_film_renders_no_second_render(film):
    store, conn = film
    D.bundle(conn, store, USER, RUN, OUTPUTS)
    A.prepare(conn, store, USER, RUN, OUTPUTS)
    A.build(conn, store, USER, RUN, OUTPUTS)
    A.render(conn, store, USER, RUN)
    conn.jobs['job-1']['status'] = 'running'
    p = report(store, conn)
    assert p['film']['state'] == 'running' and 'rendering' in p['do_next'] and '`vw assembly status --wait 900`' in p['do_next']
    with pytest.raises(Problem) as exc:
        A.render(conn, store, USER, RUN)
    assert exc.value.code == 'JOB_OPEN' and len(conn.jobs) == 1
    assert A.build(conn, store, USER, RUN, OUTPUTS)['unchanged'] is True and session(store)['renders']['assembly']['job_id'] == 'job-1'


def test_he3_a_gap_recorded_again_the_package_is_rebuilt_once_then_the_hand_over(film):
    store, conn = film
    to_rendered(store, conn)
    s = session(store)
    s['resolve'] = {'state': 'reported', 'machine': 'pc-davinci', 'film_sha256': None}   # the older package was already opened in DaVinci
    A.save_session(store, RUN, s)
    now = [MASTER, VOICE, MEDIA, vis('o-9')]
    p = report(store, conn, now)
    assert p['package']['state'] == 'stale' and 'G1' in p['package']['why'] and 'G1' in p['do_next'] and '`vw delivery bundle`' in p['do_next'] and p['handover'] is None
    made = store.made()
    out = D.bundle(conn, store, USER, RUN, now)
    assert not out.get('current') and len(store.made()) > len(made)
    assert session(store)['resolve'] is None   # that import was of the older timeline: the new package is handed over afresh
    p = report(store, conn, now)
    assert p['package']['state'] == 'current' and '`vw delivery check`' in p['handover']
    assert D.bundle(conn, store, USER, RUN, now)['current'] is True
    assert not A.prepare(conn, store, USER, RUN, now).get('settled')   # the fill's file changed: the fills are asked about, and the film is built again
    assert A.build(conn, store, USER, RUN, now)['version'] == 2 and 'assembly' not in session(store)['renders']


def test_he4_only_a_changed_fill_rebuilds_and_renders_again(film):
    store, conn = film
    to_rendered(store, conn)
    A.choose(store, {'id': 'u2'}, RUN, 'VS1', 0, 'hold_last', False)   # the same value, said again on the second computer
    assert session(store)['current'] and session(store)['choices']['VS1'].get('by') is None
    A.choose(store, {'id': 'u2'}, RUN, 'VS1', 0, 'trim', False)
    assert session(store)['current'] is None
    p = report(store, conn)
    assert p['fills']['settled'] is False and p['film']['state'] == 'stale' and '`vw assembly build`' in p['do_next']
    out = A.build(conn, store, USER, RUN, OUTPUTS)
    assert out['version'] == 2 and not out['unchanged'] and 'assembly' not in session(store)['renders']
    assert not A.render(conn, store, USER, RUN).get('ready') and len(conn.jobs) == 2


def test_stabilize_keeps_the_build_for_the_same_value_and_drops_it_for_another(film):
    store, conn = film
    A.save_session(store, RUN, {'stabilize': {'C1:1': {'flagged': True, 'choice': 'leave'}}, 'current': 'd1'})
    A.stabilize(store, USER, RUN, 'C1:1', 'leave')
    assert session(store)['current'] == 'd1'
    A.stabilize(store, USER, RUN, 'C1:1', 'ffmpeg')
    assert session(store)['current'] is None and session(store)['stabilize']['C1:1']['choice'] == 'ffmpeg'


def test_a_new_master_record_rebuilds(film):
    store, conn = film
    to_rendered(store, conn)
    now = [{**MASTER, 'id': 'm-2'}] + OUTPUTS[1:]   # a new narration ends in a new master record
    out = A.build(conn, store, USER, RUN, now)
    assert out['version'] == 2 and not out['unchanged'] and 'assembly' not in session(store)['renders']


def test_he12_changes_asked_the_report_says_which_and_what_is_rebuilt(film):
    store, conn = film
    to_rendered(store, conn)
    A.review(conn, store, USER, RUN, 'changes', 'hold the wall longer', [], 'change it')
    p = report(store, conn)
    assert p['review']['decision'] == 'changes' and p['do_next'].startswith('changes asked: hold the wall longer')
    assert '`vw assembly build`' in p['do_next'] and 'rendered again' in p['do_next']
    out = A.build(conn, store, USER, RUN, OUTPUTS)   # nothing was changed: the same film, and the report still asks for the change
    assert out['unchanged'] is True and out['next'].startswith('changes asked: hold the wall longer')


# ---------- H5: the DaVinci ledger before the proof film is recorded ----------

def test_the_ledger_routes_accept_the_assembly_stage_and_the_final_does_not():
    src = (ROOT / 'server' / 'app' / 'main.py').read_text(encoding='utf-8')
    for fn in ('delivery_reserve', 'delivery_mark'):
        assert re.search(r"def %s\(.*\n    return _s2\(conn, user, run_id, \('assembly', 'delivery'\)," % fn, src), fn
    assert re.search(r"def delivery_final\(.*\n    return _s2\(conn, user, run_id, 'delivery',", src)


def test_the_early_package_is_reserved_and_reported_then_not_offered_again(film):
    store, conn = film
    to_rendered(store, conn)
    D.resolve_reserve(store, USER, RUN, 'pc-davinci', 'open it in DaVinci')
    D.resolve_mark(store, USER, RUN, 'dispatched', 'pc-davinci')
    D.resolve_mark(store, USER, RUN, 'reported', 'pc-davinci', report={'route': 'free', 'timeline_verified': True})
    p = report(store, conn)
    assert p['resolve'] == {'state': 'reported', 'machine': 'pc-davinci', 'this_package': True} and p['handover'] is None
    assert D.verification_missing(session(store)['resolve'], FILM['sha256'])   # the early report never stands in for the approved film's


# ---------- the journey SK walked ----------

def test_the_journey_computer_a_then_computer_b_redoes_nothing(film):
    store, conn = film
    to_rendered(store, conn)                                   # computer A: bundle, prepare, build, render
    made, before = store.made(), session(store)
    p = report(store, conn)                                    # computer B after `vw pull`: what `next` says
    assert '`vw delivery check`' in p['handover'] and '`vw delivery download`' in p['handover'] and '`vw delivery open`' in p['handover']
    assert '`vw assembly fetch`' in p['do_next']
    b = D.bundle(conn, store, USER, RUN, OUTPUTS)              # B runs the recipe from the top anyway
    pr = A.prepare(conn, store, USER, RUN, OUTPUTS)
    bu = A.build(conn, store, USER, RUN, OUTPUTS)
    re_ = A.render(conn, store, USER, RUN)
    after = session(store)
    assert b['current'] and pr['settled'] and bu['unchanged'] and re_['ready']
    assert store.made() == made and len(conn.jobs) == 1                                             # nothing rebuilt
    assert all('ask' not in x['next'] for x in (b, pr, bu, re_))                                    # nothing asked
    assert after['versions'] == before['versions'] and after['current'] == before['current'] and after['bundle'] == before['bundle']
    assert report(store, conn)['handover'] == p['handover']                                         # the next step is still the hand-over
