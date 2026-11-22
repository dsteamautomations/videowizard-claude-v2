"""design/223 (SK, 22 Nov 2026), the new take process through the page's own route, with nothing mocked: a real session in a store, a fake
connection that holds the job rows (the harness of design/222's second critic: one AI video shot, VS1, its first take made by the real
functions). Without a database, without a provider."""
import json

from app import corrections as C, guide as G, pictures as P, takes as T, visuals_stage as V
from test_design151_refs_pure import NEW
from test_design222_critic2_pure import film, item, landed, on_page   # noqa: F401 (`film` is the fixture)
from test_design223_take_process_pure import EDIT, NOW, refused
from test_guide_route_pure import take_film   # noqa: F401 (the fixture `film` stands on)
from test_visuals_stage_pure import USER as SK, saved


def test_accepting_the_small_take_orders_its_copy_and_the_copy_goes_in_the_film(film):
    store, conn, job_id, wrote = film
    said, _ = on_page(store, conn, 'select')
    s, q = saved(store), conn.queued[-1]
    c = s['guides']['VS1']['corrections'][0]
    assert said == 'Accept' and 'VS1' not in s['selections'] and s['reviews'][job_id][-1]['decision'] == 'accepted'   # U3: the 360p take is not in the film
    assert q['request']['route'] == 'copy' and q['request']['resolution'] == '720p' and q['request']['from_job'] == job_id and c['route'] == 'copy' and len(c['jobs']) == 1
    sn = json.loads(store.files[q['request']['request_key']])
    assert sn['kind'] == 'edit' and sn['source']['key'] == f'run-1/visuals/takes/{job_id}.mp4' and sn['effective_prompt'] == C.copy_text() and sn['duration_seconds'] == 10
    assert sn['placement']['exact_seconds'] == 10.0 and sn['plan_digest'] == V.digest(V.current_plan(store, s))   # its place in the film is the take's
    assert any('full-size video ordered' in w['entry'] for w in wrote)   # a decision of the operator in the run's log
    assert '1 full-size video' in C.ordered(s, V.current_plan(store, s))
    landed(conn, store, c['jobs'][0], 'sha-copy')
    _, it = item(store, conn)
    line = it['_line']
    assert it['id'] == f"take:{c['jobs'][0]}" and line['compare'] == {'from': 1, 'new': 2, 'play': 'Play both together'} and line['takes'][1]['how'] == 'The full-size copy of take 1.'
    on_page(store, conn, 'select')
    s = saved(store)
    assert s['selections']['VS1']['job_id'] == c['jobs'][0] and conn.rows[-1]['verdict'] == 'accepted'   # A4: the copy the operator saw goes in the film


def test_a_correction_is_asked_routed_made_shown_beside_the_take_and_accepted(film):
    store, conn, job_id, wrote = film
    on_page(store, conn, 'again', 'There are poles on the left; there should be none.')
    s = saved(store)
    plan_ = V.current_plan(store, s)
    assert s['guides']['VS1']['corrections'][0]['words'].startswith('There are poles') and 'VS1' in C.due(s, plan_, conn.takes)
    assert 'being corrected' in [i['state'] for i in T.expected(s, plan_, conn.takes, NOW)]
    row = C.listed(store, s, plan_, conn.takes)['corrections'][0]
    assert row['shot_id'] == 'VS1' and len(row['frames']) == 13 and row['seconds'] == 10 and row['size'] == '360p' and row['take_words'].startswith('BLUE box')
    n = len(conn.queued)
    out = C.send(conn, store, SK, NEW, [], 'VS1', EDIT)
    q = conn.queued[-1]
    assert len(conn.queued) == n + 1 and q['request']['route'] == 'edit' and q['request']['from_job'] == job_id and out['jobs'] == saved(store)['guides']['VS1']['corrections'][0]['jobs']
    assert json.loads(store.files[q['request']['request_key']])['effective_prompt'].startswith('Edit the video. Make only this change: Remove the bamboo poles')
    assert conn.rows[-1]['record'][-1]['kind'] == 'version sent' and conn.rows[-1]['record'][-1]['route'] == 'edit'   # U7: in the record of generations
    assert any(w['entry'].startswith('route edit: ') and w['by_kind'] == 'assistant' for w in wrote)                  # and in the run's log
    landed(conn, store, out['jobs'][0], 'sha-edit')
    _, it = item(store, conn)
    assert it['_line']['compare']['from'] == 1 and it['_line']['takes'][1]['how'] == 'An edit of take 1.' and it['_line']['takes'][0]['rejected'].startswith('You said: There are poles')
    on_page(store, conn, 'select')
    assert saved(store)['selections']['VS1']['job_id'] == out['jobs'][0]


def test_the_first_take_again_goes_through_the_real_shoot_with_the_same_request(film):
    store, conn, job_id, wrote = film
    on_page(store, conn, 'again', 'It is still the boxes.')
    n = len(conn.queued)
    out = C.send(conn, store, SK, NEW, [], 'VS1', {'route': 'first_take', 'reason': 'The video is the layout itself: nothing of it is usable.'})
    q, c = conn.queued[-1], saved(store)['guides']['VS1']['corrections'][0]
    assert len(conn.queued) == n + 1 and q['request']['resolution'] == '360p' and 'route' not in q['request'] and c['route'] == 'first_take' and c['jobs'] == out['jobs']
    assert saved(store)['guides']['VS1']['takes'][-1]['quote'] == 'It is still the boxes.'   # made on the operator's own words


def test_a_first_take_that_failed_at_the_provider_is_sent_again_once_on_the_operators_word(film):
    store, conn, job_id, wrote = film
    assert 'the same request is never sent twice' in refused(lambda: G.shoot(conn, store, SK, NEW, [], 'VS1', 'Again.', again=True))   # a take that was made: never
    conn.takes[0]['status'] = 'failed'
    assert 'could not be made at the provider' in refused(lambda: G.shoot(conn, store, SK, NEW, [], 'VS1', 'Again.'))
    G.shoot(conn, store, SK, NEW, [], 'VS1', 'Send it once more.', again=True)
    conn.takes.append({**conn.takes[0], 'id': saved(store)['guides']['VS1']['takes'][-1]['job_id']})
    assert 'already sent twice' in refused(lambda: G.shoot(conn, store, SK, NEW, [], 'VS1', 'And again.', again=True))


def test_a_look_sent_for_a_take_is_refused_by_name_and_no_take_is_listed_for_a_look(film):
    store, conn, job_id, wrote = film
    out = P.record_looks(store, SK, NEW, [], [{'ref': job_id, 'sha10': 'sha-take-1', 'lines': []}], 'helper', take_rows=conn.takes)
    assert out['refused'] == {job_id: T.W['look_retired']} and out['recorded'] == []
    assert [p for p in P.looks_due(store, NEW, [], conn.takes)['pictures'] if p['kind'] == 'take'] == []


def test_the_frame_rate_of_a_file_is_still_read():
    from app import guide_worker as GW
    assert GW.frame_rate('24/1') == 24.0 and GW.frame_rate('nothing') == 24.0
