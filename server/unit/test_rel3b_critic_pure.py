"""The critic's points on releases 3 and 4 (20 Nov 2026).
1. A defect filed with `--shot S` holds S on every path: the chat's answers and the page's buttons reach the same server functions as the tool,
   and those functions refuse while an open defect holds the shot (`visuals_stage.need_free`); another shot goes on.
2. The drawings that continue from a held shot are held by the server too, not only by the next-step sentence (`visuals_stage.held_chain`).
3. An answer about a thing accepts, with no card, only its own change: the thing's record and its place in `element_ids` of the shots that showed
   it in the plan in force; any other change of those shots, or a shot that did not show it, brings the card as before.
5. The first-frame jobs of older video jobs are queued under one lock, so two workers never queue two for the same render.
6. A defect row written before the scope rule (no "holds" line) holds every write, as it did when it was filed.
Each test failed first. Without a database."""
import contextlib

import pytest

from app import chat_flow as CF, core, guide_worker as W, main as API, visuals_stage as V, web
from app import storage as storage_mod
from app.errors import Problem
from test_design151_refs_pure import NEW
from test_guide_route_pure import still_made, take_film   # noqa: F401 (take_film: the fixture)
from test_hotfix_guide_lane_pure import Conn as LaneConn
from test_rel4_first_frame_pure import back, start, to_the_take
from test_visuals_stage_pure import USER, saved
import test_rel3_defect_scope_pure as D
import test_rel3_plan_cards_pure as PC


def defects(monkeypatch, *rows):
    monkeypatch.setattr(core, 'open_defect_rows', lambda conn, run_id: [dict(r) for r in rows])


def held(fn):
    with pytest.raises(Problem) as e:
        fn()
    assert e.value.code == 'DEFECT_OPEN' and e.value.status == 409, e.value.message
    return e.value


def item(store, conn, prefix):
    """The item the chat hands out now (`vw visuals next`), as the operator sees it."""
    out = CF.next_item(conn, store, USER, NEW, [])
    got = (out.get('item') or {}).get('id') or ''
    assert got.startswith(prefix), out
    return got


def videos(conn):
    return [q for q in conn.queued if q['provider'] == 'video']


def ready_to_shoot(take_film):
    store, conn = start(take_film)
    to_the_take(store, conn)
    back(store, 'guide-render')
    return store, conn


def with_a_still(take_film):
    store, conn = start(take_film)
    back(store, 'guide-frame1')
    still_made(store, conn)
    s = saved(store)
    s['guides']['VS1']['stills'][0]['asked_at'] = '2026-01-01T00:00:00+00:00'   # Claude's look never came: the card is shown as not checked
    V.save_session(store, NEW, s)
    return store, conn


OTHERS = ({'defect': 7, 'shot': 'VS9'}, {'defect': 8, 'stage': 'voice'})   # another shot's defect, another step's defect


# ---------- 1. the chat ----------

def test_the_chat_cannot_shoot_a_held_shot_and_shoots_when_the_defect_is_on_another(take_film, monkeypatch):
    store, conn = ready_to_shoot(take_film)
    sid = item(store, conn, 'shoot')
    defects(monkeypatch, {'defect': 7, 'shot': 'VS1'})
    e = held(lambda: CF.answer(conn, store, USER, NEW, [], sid, 'shoot', 'Yes, shoot it.'))
    assert e.extra['holds'] == {'shot': 'VS1'} and 'holds shot VS1 only' in e.message and videos(conn) == []   # nothing paid
    defects(monkeypatch, *OTHERS)
    CF.answer(conn, store, USER, NEW, [], sid, 'shoot', 'Yes, shoot it.')
    assert len(videos(conn)) == 1


def test_the_chat_cannot_approve_a_held_shots_still(take_film, monkeypatch):
    store, conn = with_a_still(take_film)
    sid = item(store, conn, 'still:VS1')
    defects(monkeypatch, {'defect': 7, 'shot': 'VS1'})
    held(lambda: CF.answer(conn, store, USER, NEW, [], sid, 'approve', 'Yes, it sits on the guide.'))
    assert saved(store)['guides']['VS1']['stills'][0]['status'] == 'candidate'
    defects(monkeypatch, *OTHERS)
    CF.answer(conn, store, USER, NEW, [], sid, 'approve', 'Yes, it sits on the guide.')
    assert saved(store)['guides']['VS1']['stills'][0]['status'] == 'approved'


def test_the_chat_cannot_record_a_verdict_on_a_held_shots_drawing(take_film, monkeypatch):
    store, conn = start(take_film, layout=False)
    sid = item(store, conn, 'shot-drawing:VS1')
    defects(monkeypatch, {'defect': 7, 'shot': 'VS1'})
    held(lambda: CF.answer(conn, store, USER, NEW, [], sid, 'yes', 'yes, that is the shot'))
    assert saved(store)['guides']['VS1']['drawing']['status'] == 'proposed'
    defects(monkeypatch, *OTHERS)
    CF.answer(conn, store, USER, NEW, [], sid, 'yes', 'yes, that is the shot')
    assert saved(store)['guides']['VS1']['drawing']['status'] == 'approved'


# ---------- 1. the page ----------

def page(monkeypatch, store, conn, body):
    monkeypatch.setattr(web, 'page_user', lambda s: USER)
    monkeypatch.setattr(web, 'db_connect', lambda: contextlib.nullcontext(conn))
    monkeypatch.setattr(web, '_run_at', lambda c, u, code, stage: NEW)
    monkeypatch.setattr(web, '_visuals_payload', lambda *a, **k: {})
    monkeypatch.setattr(storage_mod, 'storage', lambda: store)
    monkeypatch.setattr(core, 'current_outputs', lambda c, rid: [])
    return web._visuals_act(NEW['code'], 'cookie', body)


def test_the_page_cannot_shoot_a_held_shot(take_film, monkeypatch):
    store, conn = ready_to_shoot(take_film)
    defects(monkeypatch, {'defect': 7, 'shot': 'VS1'})
    held(lambda: page(monkeypatch, store, conn, {'action': 'guide-shoot', 'shot_id': 'VS1', 'quote': 'Shoot'}))
    assert videos(conn) == []
    defects(monkeypatch, *OTHERS)
    page(monkeypatch, store, conn, {'action': 'guide-shoot', 'shot_id': 'VS1', 'quote': 'Shoot'})
    assert len(videos(conn)) == 1


def test_the_page_cannot_approve_a_held_shots_still(take_film, monkeypatch):
    store, conn = with_a_still(take_film)
    st = saved(store)['guides']['VS1']['stills'][0]
    body = {'action': 'guide-approve', 'shot_id': 'VS1', 'still_id': st['id'], 'sha256': st['sha256'], 'quote': 'Approve'}
    defects(monkeypatch, {'defect': 7, 'shot': 'VS1'})
    held(lambda: page(monkeypatch, store, conn, body))
    defects(monkeypatch, *OTHERS)
    page(monkeypatch, store, conn, body)
    assert saved(store)['guides']['VS1']['stills'][0]['status'] == 'approved'


# ---------- 2. the chain ----------

def chain_film(monkeypatch):
    monkeypatch.setattr(V, 'session_of', lambda *a, **k: D.SESSION)
    monkeypatch.setattr(V, 'current_plan', lambda store, session: D.PLAN)
    defects(monkeypatch, {'defect': 7, 'shot': 'D1'})


def test_a_drawing_that_continues_from_a_held_shot_is_held_with_the_reason(monkeypatch):
    chain_film(monkeypatch)
    run = {'id': 'run-1'}
    e = held(lambda: V.need_free(object(), None, run, ['D2']))
    assert e.message == ('defect 7 is open on this run and holds shot D1; D2 continues from it and waits for it too, and the rest of the run goes on. Do not send '
                         'this call again now: tell the operator, go on with the other shots, and send it once the builder says the defect is fixed.')
    assert e.extra == {'defect': 7, 'defects': [7], 'holds': {'shot': 'D1'}}
    held(lambda: V.need_free(object(), None, run, ['D3']))                       # it continues D2, which continues D1
    assert 'holds shot D1 only' in held(lambda: V.need_free(object(), None, run, ['D1'])).message
    V.need_free(object(), None, run, ['D4'])                                      # after a picture: nothing continues from D1
    V.need_free(object(), None, run, ['P1'])
    assert V.held_line(D.PLAN, D.SESSION, [{'defect': 7, 'shot': 'D1'}]).startswith('Defect 7 is open on D1: nothing more is sent for D1')   # the same chain


def test_the_tools_motion_upload_and_render_for_a_continuing_drawing_are_refused(monkeypatch):
    chain_film(monkeypatch)
    monkeypatch.setattr(core, 'load_run', lambda *a, **k: {'id': 'run-1', 'status': 'open'})
    monkeypatch.setattr(core, 'next_for', lambda c, r: {'stage': 'visuals'})
    monkeypatch.setattr(core, 'current_outputs', lambda c, rid: [])
    monkeypatch.setattr(API, 'storage', lambda: None)
    for shots in (['D2'], API.shots_of(API.Draw(request_id=D.uuid.uuid4(), shot_id='D3'))):   # `vw motion upload` / `render` send the shot
        assert 'continues from it' in held(lambda: API._visuals_run(object(), USER, 'run-1', shots)).message
    assert API._visuals_run(object(), USER, 'run-1', ['D4'])[0]['id'] == 'run-1'


# ---------- 3. an answer accepts only its own change ----------

def logo_film():
    """D2 (gap G2) shows the client logo E2; every gap accepted; the operator answered the question on E2."""
    store, sess, d = PC.film(PC.change(PC.doc(), lambda s, _: s['D2'].update(element_ids=['E2'])))
    PC.answered(sess, 'E2')
    return store, sess, d


def logo(new, **record):
    next(e for e in new['elements'] if e['id'] == 'E2').update(record)


def test_the_answer_on_a_thing_accepts_its_record_and_where_it_shows_with_no_card():
    store, sess, d = logo_film()
    out = V.new_version(store, PC.RUN, sess, PC.change(d, lambda s, new: logo(new, requirements='the logo file the operator gave')), PC.USER, [], answers='E2')
    assert PC.cards(store, sess) == [] and sess['accepted']['G2']['quote'] == 'Use the client logo' and out['quiet'][0]['shots'] == ['D2']


def test_the_answer_on_a_thing_does_not_carry_a_shot_that_did_not_show_it():
    store, sess, d = logo_film()
    V.new_version(store, PC.RUN, sess, PC.change(d, lambda s, _: s['D1'].update(element_ids=['E1', 'E2'], visual_type='video')), PC.USER, [], answers='E2')
    assert PC.cards(store, sess) == ['G1']                                        # D1 never showed the logo: given it and made AI video, it is asked
    store, sess, d = logo_film()
    V.new_version(store, PC.RUN, sess, PC.change(d, lambda s, _: s['D1'].update(element_ids=['E1', 'E2'])), PC.USER, [], answers='E2')
    assert PC.cards(store, sess) == ['G1']                                        # given the logo alone: asked too


@pytest.mark.parametrize('edit', [{'visual_type': 'video'}, {'start_frame': 920}, {'purpose': 'the closing card with the supplied logo'},
                                  {'depicts': 'The client logo, centred'}, {'camera': 'slow push in'}])
def test_the_answer_on_a_thing_does_not_carry_another_change_of_a_shot_that_shows_it(edit):
    store, sess, d = logo_film()
    V.new_version(store, PC.RUN, sess, PC.change(d, lambda s, new: (s['D2'].update(edit), logo(new, requirements='the logo file'))), PC.USER, [], answers='E2')
    assert PC.cards(store, sess) == ['G2'] and 'G2' not in sess['accepted']


# ---------- 5. one backfill ----------

def test_the_backfill_takes_its_lock_first_in_the_same_transaction(monkeypatch):
    conn = LaneConn(running=set(), queued=[])

    def connect():
        conn.sql.append(('CONNECT', ()))   # each `with connect()` is one transaction (psycopg: committed when the block ends)
        return contextlib.nullcontext(conn)
    monkeypatch.setattr(W, 'connect', connect)
    from app import visual_workers, worker
    monkeypatch.setattr(worker, 'STOP', False, raising=False)
    monkeypatch.setattr(visual_workers, 'renders_free', lambda c, cap: True)
    W.tick()
    sqls = [s for s, _ in conn.sql]
    at = sqls.index(W.BACKFILL)
    assert sqls[at - 2:at] == ['CONNECT', W.BACKFILL_LOCK]
    assert W.BACKFILL_LOCK == "select pg_advisory_xact_lock(hashtext('vw2-guide-backfill'))"


# ---------- 6. an older defect row ----------

def test_a_defect_row_from_before_the_scope_rule_holds_every_write_as_it_did():
    old = [{'id': 4, 'stage': 'visuals', 'log_excerpt': 'Traceback (most recent call last)', 'status': 'open'}]   # the older server kept the step it was filed in
    assert D.refused(old, stage='voice').message.startswith('defect 4 is open on this run and holds every step')
    D.refused(old, stage='visuals', shots=['S1'])
    new = [{'id': 5, 'stage': 'visuals', 'log_excerpt': core.STEP_LINE + 'visuals\nTraceback', 'status': 'open'}]   # filed under the scope rule
    assert D.write(new, stage='voice')['id'] == D.RUN_ID
    assert D.refused(new, stage='visuals').extra['holds'] == {'stage': 'visuals'}


def test_a_defect_filed_now_without_a_shot_says_its_step_first(monkeypatch):
    monkeypatch.setattr(core, 'next_for', lambda conn, run: {'stage': 'visuals'})
    conn = D.Conn([])
    assert core.file_defect(conn, USER, {'id': D.RUN_ID}, None, 'no sound', 'line 1') == {'ticket': 9, 'holds': {'stage': 'visuals'}}
    assert conn.inserted[3] == 'holds step: visuals\nline 1'
    assert core.open_defect_rows(D.Conn([{'id': 9, 'stage': 'visuals', 'log_excerpt': conn.inserted[3]}]), D.RUN_ID) == [{'defect': 9, 'stage': 'visuals'}]
