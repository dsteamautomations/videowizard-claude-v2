"""design/92 (L60, with L59): the image check and the round's searches run before the run lock; reads never wait for the lock or stop on a defect."""
import json
import types

import pytest

from app import core, image_check as IC, visual_workers as VW, visuals_stage as VS
from test_visuals_stage_pure import FakeConn, FakeStore, RUN, USER, accepted, plan_doc, ref, saved, session, shot, store_with


class Locks:
    """A connection that records the lock calls, in order with the work done between them."""

    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.log.append('commit')
        return False

    def execute(self, sql, params=()):
        if 'advisory' in sql:
            self.log.append('lock')
        return types.SimpleNamespace(fetchone=lambda: None, fetchall=lambda: [])


def image_job_store(**ref_over):
    r = {**ref('K1'), 'status': 'candidate', 'job_id': 'j1', 'check_pending': True, 'server_checklist': [{'check': 'x', 'pass_when': 'y', 'weight': 'must'}], **ref_over}
    return FakeStore({'run-1/visuals/session.json': {'references': {'K1': r}}})


JOB = {'id': 'j1', 'run_id': 'run-1', 'request': {'reference': {'id': 'K1'}}}


def test_the_image_check_runs_with_no_lock_held_and_only_the_save_is_locked(monkeypatch):
    log = []
    store = image_job_store()
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'connect', lambda: Locks(log))
    monkeypatch.setattr(IC, 'run_check', lambda st, sess, r, result, f: log.append('check') or {'lines': [], 'must_failed': [{'check': 'x', 'pass_when': 'y'}]})
    queued = []
    monkeypatch.setattr(IC, 'queue_fix', lambda conn, st, run_id, ref_id: queued.append(ref_id))
    VW.check_image(JOB, {'key': 'run-1/visuals/references/K1.png'})
    assert log == ['check', 'lock', 'commit']   # the check first, then the lock only for the save
    row = json.loads(store.files['run-1/visuals/session.json'])['references']['K1']
    assert row['check']['must_failed'] and 'check_pending' not in row and queued == ['K1']


def test_a_picture_changed_while_it_was_checked_keeps_what_it_has(monkeypatch):
    store = image_job_store(status='rejected')
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'connect', lambda: Locks([]))
    monkeypatch.setattr(IC, 'run_check', lambda *a: {'lines': [], 'must_failed': []})
    VW.check_image(JOB, {'key': 'k'})
    assert 'check' not in json.loads(store.files['run-1/visuals/session.json'])['references']['K1']
    store = image_job_store(job_id='j9')   # another job made this reference since
    monkeypatch.setattr(VW, 'storage', lambda: store)
    VW.check_image(JOB, {'key': 'k'})
    assert 'check' not in json.loads(store.files['run-1/visuals/session.json'])['references']['K1']
    VW.check_image({**JOB, 'run_id': 'gone'}, {'key': 'k'})   # never raises


def test_finalize_marks_the_picture_as_being_checked_and_runs_no_check(monkeypatch):
    store = FakeStore({'run-1/visuals/session.json': {'references': {'K1': {**ref('K1'), 'status': 'generating', 'job_id': 'j1',
                                                                                'server_checklist': [{'check': 'x', 'pass_when': 'y', 'weight': 'must'}]}}}})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW.jobs, 'finish', lambda *a, **k: None)
    monkeypatch.setattr(IC, 'run_check', lambda *a: pytest.fail('the check runs outside the lock'))
    due = VW.finalize_image(Locks([]), JOB, 'retained', {'key': 'run-1/visuals/references/K1.png', 'sha256': 's', 'bytes': 1, 'width': 1, 'height': 1}, None, None, None)
    row = json.loads(store.files['run-1/visuals/session.json'])['references']['K1']
    assert due is True and row['status'] == 'candidate' and row['check_pending'] is True


def test_reads_say_busy_and_write_nothing_when_the_lock_is_taken():
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc))
    store = store_with(sess, doc)
    before = store.files['run-1/visuals/session.json']
    out = VS.status(FakeConn([]), store, RUN, [], repair=False)
    assert out['busy'] is True and store.files['run-1/visuals/session.json'] == before
    assert VS.status(FakeConn([]), store, RUN, [])['busy'] is False


def test_try_lock_asks_postgres_without_waiting():
    seen = []

    class C:
        def execute(self, sql, params=()):
            seen.append(sql)
            return types.SimpleNamespace(fetchone=lambda: {'got': False})
    assert core.try_lock(C(), 'run-1') is False and 'pg_try_advisory_xact_lock' in seen[0]


def test_the_status_route_reads_without_the_lock_and_through_an_open_defect(monkeypatch):
    from app import main
    calls = []
    monkeypatch.setattr(main.core, 'load_run', lambda conn, user, run_id, lock=False: calls.append(lock) or {'id': run_id})
    monkeypatch.setattr(main.core, 'try_lock', lambda conn, run_id: False)
    monkeypatch.setattr(main.core, 'current_outputs', lambda conn, run_id: [])
    monkeypatch.setattr(main, 'storage', lambda: None)
    monkeypatch.setattr(main.visuals_stage, 'status', lambda conn, store, run, outputs, repair=True: {'busy': not repair})
    out = main.visuals_status('run-1', USER, object())
    assert calls == [False] and json.loads(out.body)['busy'] is True


def test_the_rounds_searches_run_before_the_lock_and_the_save_uses_them(monkeypatch):
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    doc['elements'][0]['kind'] = 'object'
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1',
                   round={'pass': 1, 'elements': {'E1': {'frames': [], 'keywords': 'village mason Tamil Nadu', 'verdict': None, 'search_id': None, 'error': None}}})
    store = store_with(sess, doc)
    rows = [{'n': 1, 'thumbnail': 'https://t/1.jpg', 'image_url': 'https://i/1.jpg', 'page_url': 'https://p/1', 'site': 's', 'width': 8, 'height': 6, 'title': 't'}]
    calls = []
    monkeypatch.setattr(VS.apify, 'search_images', lambda keywords, n=10: calls.append(keywords) or rows)
    found = VS.round_searches(store, RUN, [], {'E1': {'verdict': 'search'}})
    assert found == {'E1': rows} and calls == ['village mason Tamil Nadu']
    monkeypatch.setattr(VS.apify, 'search_images', lambda *a, **k: pytest.fail('searched again inside the lock'))
    out = VS.round_done(store, USER, RUN, [], {'E1': {'verdict': 'search'}}, 'Yes, search.', found=found)
    assert out['pass'] == 2 and saved(store)['searches'][out['searched'] and saved(store)['round']['elements']['E1']['search_id']]['results'] == rows


def test_the_page_buttons_do_their_work_off_the_event_loop(monkeypatch):
    """design/92: one server process serves every request; a button's blocking work (searches, renders, providers) must not stop the others."""
    import asyncio
    import threading
    from app import elevenlabs, web
    seen = []
    monkeypatch.setattr(web, 'page_user', lambda s: USER)
    monkeypatch.setattr(elevenlabs, 'ElevenLabs', lambda: object())

    def stop():
        seen.append(threading.get_ident())
        raise RuntimeError('stop here')
    monkeypatch.setattr(web, 'db_connect', stop)

    class Req:
        async def json(self):
            return {'action': 'record', 'quote': 'yes'}
    loop_thread = threading.get_ident()
    for handler in (web.visuals_act, web.review_act, web.voices2_act):
        with pytest.raises(RuntimeError, match='stop here'):
            asyncio.run(handler(Req(), 'VW-9', 'cookie'))
    assert len(seen) == 3 and loop_thread not in seen


def test_a_check_is_stored_without_the_pass_conditions_its_checklist_already_holds_and_the_page_shows_them():
    """design/92: the session kept small; the light line, which no checklist holds, keeps its own; a failed must line is stored short too."""
    r = {**ref('K1'), 'status': 'candidate', 'element_kind': 'graphic', 'server_checklist': [{'check': 'label: 25 % fewer', 'pass_when': 'reads exactly', 'weight': 'must'}]}
    stored = IC.compact({'lines': [{'check': 'label: 25 % fewer', 'pass_when': 'reads exactly', 'weight': 'must', 'pass': True, 'seen': 'ok'},
                                   {'check': 'light and colour', 'pass_when': 'match the footage', 'weight': 'should', 'pass': False, 'seen': 'brighter'}],
                         'must_failed': [{'check': 'label: 25 % fewer', 'pass_when': 'reads exactly'}]}, r)
    assert 'pass_when' not in stored['lines'][0] and stored['lines'][1]['pass_when'] == 'match the footage' and 'pass_when' not in stored['must_failed'][0]
    shown = IC.expand(stored, r)
    assert shown['lines'][0]['pass_when'] == 'reads exactly' and shown['must_failed'][0]['pass_when'] == 'reads exactly'   # the fix round reads it back


def test_a_still_for_a_named_image_shot_needs_no_bind_or_packet_of_the_elements_video_shot(monkeypatch):
    """Defect 24 (VW-7): the start-image gate (design/77 L35) followed every video shot of the element and ignored --shot."""
    from test_visuals_stage_pure import g
    from app.errors import Problem
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])   # E1 in both; VS1 never bound
    store = store_with(session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc)), doc)
    body = {'request_id': 'd24', 'element_id': 'E1', 'name': 'house', 'kind': 'keyframe', 'subject': 'a house', 'prompt': 'A half-built house in the sun.'}
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'shot_id': 'IM1'})
    assert out['reference_id']
    with pytest.raises(Problem, match='Bind the shot and read its packet'):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'request_id': 'd24b', 'shot_id': 'VS1'}))   # a video shot still needs its packet
    with pytest.raises(Problem, match='Bind the shot and read its packet'):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'request_id': 'd24c'}))   # no shot named: as before
