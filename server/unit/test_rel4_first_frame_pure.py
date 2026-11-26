"""Release 4 (SK, 20 Nov 2026): the first frame of a layout first, its video behind it.

Until this release one `guide-render` job made frame 1 (16 samples, under a minute) and then every frame of the video (about 4 s a frame: 16
minutes for an 8-second shot), one job at a time, so the still of every shot waited behind every video. The still needs only frame 1; the video
is needed only when the take is ordered. Now a passing check queues two jobs: the first frame (its own quick job, in the quick lane with the
check frames, frame 1 first) and the video (the render lane, as before). The still is ordered as soon as the first frame exists; `shoot`
refuses, in a sentence, until the video is ready. Files of the same scene still in storage are used again. Each test failed first.
Until 25 Nov 2026 the still also waited for the operator's Yes on the layout drawing; retired (A1): the check's pass and the first frame open it.
Without a database; Blender is faked as in test_guide_worker_pure.py."""
import hashlib
import json
import sys
from pathlib import Path

from app import chat_flow as CF, guide as GD, guide_worker as W, takes as T, visuals_stage as VS
from test_design151_refs_pure import NEW
from test_guide_route_pure import OTHER, STILL_WORDS, TAKE_WORDS, frames_back, passed, refused, scene, spec10, still_made, take_film   # noqa: F401 (take_film: the fixture)
from test_guide_worker_pure import blender, job   # noqa: F401 (blender: the fixture)
from test_hotfix_guide_lane_pure import Conn as LaneConn, job as lane_job, run_tick
import test_rel1d_layout_check_pure as R1
from test_visuals_stage_pure import USER, saved

ROOT = Path(__file__).resolve().parents[2]
RETRY = 'send the same scene again to render it again (`vw guide scene --shot VS1 --file work/guide/VS1/scene.json`)'
RENDERING = 'The layout video of VS1 is still being rendered (needed only for the take; about 20 minutes of rendering, one video at a time).'   # 10 s, 300 frames, about 4 s a frame
ORDER_NOW = 'First frame ready: the still can be ordered (`vw guide still --shot VS1 --file …`). '
NO_TAKE = ' No take is sent without it: send this again when `vw guide status --shot VS1` says it is ready.'
WAITING = 'waiting for the layout video'
STILL_DUE = 'first frame ready: the still can be ordered'


def base(store):
    return f"run-1/visuals/guides/{saved(store)['guides']['VS1']['sha256']}"


def back(store, kind, ok=True, error=None):
    """A worker's result on the session, as `guide_worker.finish` writes it."""
    s = saved(store)
    g = s['guides']['VS1']
    result = {'frame1_key': base(store) + '/frame1.png', 'frame1_sha256': 'sha-f1'}
    if kind == 'guide-render':
        result.update(guide_key=base(store) + '/guide.mp4', sha256='sha-guide', bytes=9, render_seconds=600)
    entry = GD.apply_result(s, {'id': 'job-x', 'request': {'kind': kind, 'shot_id': 'VS1', 'sha256': g['sha256']}}, 'ready' if ok else 'failed', result if ok else {}, error)
    VS.save_session(store, NEW, s)
    return entry


def start(take_film):
    """A scene whose check passed. (Until 25 Nov 2026 also the operator's Yes on its layout drawing; retired, A1.)"""
    store, conn = R1.film(take_film)
    passed(store, conn)
    return store, conn


def kinds(conn):
    return [q['request']['kind'] for q in conn.queued if q['provider'] == 'guide']


def nxt(store, conn):
    return GD.status(conn, store, NEW, [], 'VS1')['next']


def due(store):
    s = saved(store)
    return T.render_due(s, VS.current_plan(store, s))


def to_the_take(store, conn):
    """Frame 1 is back; the still is made and approved on it; the take's words are written. The video is not ready."""
    back(store, 'guide-frame1')
    sid = still_made(store, conn)
    GD.approve_still(conn, store, USER, NEW, [], 'VS1', sid, 'sha-still', 'Yes, it sits on the guide.')
    GD.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS)
    return sid


def shoot_cards(store, conn):
    return [i['kind'] for i in CF._guide_items(CF._ctx(conn, store, USER, NEW, []))]


# ---------- a pass queues two jobs: the first frame, then the video ----------

def test_a_pass_queues_the_first_frame_and_then_the_video(take_film):
    store, conn = start(take_film)
    g = saved(store)['guides']['VS1']
    assert kinds(conn) == ['guide-frames', 'guide-frame1', 'guide-render']
    same = {'shot_id': 'VS1', 'sha256': g['sha256'], 'spec_key': g['key'], 'seconds': 10}
    assert conn.queued[1]['request'] == {'kind': 'guide-frame1', **same} and conn.queued[2]['request'] == {'kind': 'guide-render', **same, 'split': True}
    assert g['render'] == {'frame1_job_id': 'job-2', 'job_id': 'job-3', 'status': 'queued'}
    assert nxt(store, conn).endswith('The first frame of VS1 is being made (free, under a minute of rendering); the still can be ordered when it is ready.')


def test_the_use_it_as_it_is_answer_queues_the_same_two_jobs(take_film):
    store, conn = R1.film(take_film)
    for n in range(3):
        spec = spec10()
        spec['people'][2]['facing'] = [[0, 1], [1, 0], [-1, 0]][n]
        scene(store, conn, spec)
        R1.verdict(store, conn, frames_back(store, conn), False)
    g = saved(store)['guides']['VS1']
    out = GD.held_answer(conn, store, USER, NEW, [], 'VS1', g['sha256'], 'use', 'Use it.')
    assert kinds(conn)[-2:] == ['guide-frame1', 'guide-render'] and 'against its check' in out['next'] and 'first frame' in out['next']


# ---------- the still on the first frame; the take on the video ----------

def test_the_still_is_ordered_as_soon_as_the_first_frame_is_ready_and_shoot_waits_for_the_video(take_film):
    store, conn = start(take_film)
    assert 'The first frame of the layout is not rendered yet' in refused(lambda: still_made(store, conn))
    assert R1.said(store) == '' and R1.state(store) == ['being made']
    assert back(store, 'guide-frame1') == {'kind': 'first frame made', 'ok': True, 'frame1_key': base(store) + '/frame1.png'}
    g = saved(store)['guides']['VS1']
    assert g['render'] == {'frame1_job_id': 'job-2', 'job_id': 'job-3', 'status': 'queued', 'frame1_key': base(store) + '/frame1.png', 'frame1_sha256': 'sha-f1'}
    assert R1.said(store) == R1.START + R1.STILLS.format(ids='VS1', n=1) + '.'                      # named for its still while its video renders
    assert R1.state(store) == [STILL_DUE] and g['drawing']['status'] == 'proposed'                  # the first frame alone opens the still: nobody approved the layout drawing (A1)
    s = saved(store)
    assert T.status_line(T.expected(s, VS.current_plan(store, s), [])) == 'AI video: 1 first frame ready: the still can be ordered.'
    out = GD.status(conn, store, NEW, [], 'VS1')
    assert out['next'] == ORDER_NOW + RENDERING and 'frame1' in out['files'] and 'guide' not in out['files']
    assert GD.view(saved(store), 'VS1', lambda k: '/f/' + k)['render'] == {'status': 'queued', 'error': None, 'guide_url': None, 'frame1_url': '/f/' + base(store) + '/frame1.png'}
    to_the_take(store, conn)
    still_job = next(q for q in conn.queued if q['provider'] == 'guide-still')
    assert still_job['request']['parents'][0] == {'id': 'guide-frame-' + g['sha256'][:12], 'key': base(store) + '/frame1.png', 'sha256': 'sha-f1'}
    # everything for the take is there but the video: no card, no take, and the lines say what is waited for
    assert R1.state(store) == [WAITING] and shoot_cards(store, conn) == []
    s = saved(store)
    assert T.status_line(T.expected(s, VS.current_plan(store, s), [])) == 'AI video: 1 waiting for the layout video.'
    assert refused(lambda: GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.')) == RENDERING + NO_TAKE
    assert not any(q['provider'] == 'video' for q in conn.queued)
    assert nxt(store, conn) == 'Everything else for the take is ready: the word to shoot is asked when the layout video is ready. ' + RENDERING
    assert due(store).endswith('(VS1): ' + RENDERING + ' Everything else for its take is ready: its word to shoot is asked when the video is ready; go on with the other shots.')
    # the video is back: the card, and the take is sent with the whole video
    back(store, 'guide-render')
    assert R1.state(store) == ['waiting for you in the chat'] and shoot_cards(store, conn) == ['shoot'] and due(store) == ''
    assert nxt(store, conn).startswith('Ready to shoot') and 'guide' in GD.status(conn, store, NEW, [], 'VS1')['files']
    GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Yes, shoot it.')
    snap = json.loads(store.files[conn.queued[-1]['request']['request_key']])
    assert snap['guide'] == {'key': base(store) + '/guide.mp4', 'sha256': 'sha-guide', 'seconds': 10, 'scene_sha256': g['sha256']}   # what the take uploads and its checks read


# ---------- failures ----------

def test_a_failed_first_frame_is_named_and_comes_with_the_video_or_at_once_on_the_same_scene_sent_again(take_film):
    store, conn = start(take_film)
    assert back(store, 'guide-frame1', ok=False, error='RuntimeError: Blender gave no answer') == {'kind': 'first frame made', 'ok': False, 'error': 'RuntimeError: Blender gave no answer'}
    g = saved(store)['guides']['VS1']
    assert g['render']['status'] == 'queued' and g['render']['frame1_error'] == 'RuntimeError: Blender gave no answer'   # the video's job is left: it makes the frame too
    line = ('The first frame of VS1 failed (RuntimeError: Blender gave no answer): no still can be ordered yet. It is made again with the layout video, which is rendering; '
            'to make it at once, ' + RETRY + '.')
    assert nxt(store, conn) == line and due(store).endswith('(VS1): ' + line) and R1.said(store) == ''
    assert 'not rendered yet' in refused(lambda: still_made(store, conn))
    n = len(conn.queued)
    out = scene(store, conn)                                                                        # the retry: the same scene, sent again
    assert out['unchanged'] is True and out['next'] == 'This scene is already stored: its first frame is queued again (free).'
    assert kinds(conn)[-1] == 'guide-frame1' and len(conn.queued) == n + 1 and 'frame1_error' not in saved(store)['guides']['VS1']['render']
    assert scene(store, conn)['next'] == 'This scene is already stored; nothing was queued.' and len(conn.queued) == n + 1
    back(store, 'guide-render')                                                                     # or it comes with the video
    assert R1.said(store) == R1.START + R1.STILLS.format(ids='VS1', n=1) + '.' and due(store) == ''


def test_a_video_that_fails_after_the_still_is_approved_reads_waiting_with_the_error_and_the_retry(take_film):
    store, conn = start(take_film)
    to_the_take(store, conn)
    back(store, 'guide-render', ok=False, error='RuntimeError: the frames could not be joined into a video')
    g = saved(store)['guides']['VS1']
    assert g['render']['status'] == 'failed' and g['render']['frame1_key'] == base(store) + '/frame1.png' and g['render']['frame1_sha256'] == 'sha-f1'   # the first frame is kept
    failed = 'The layout video of VS1 failed (RuntimeError: the frames could not be joined into a video): ' + RETRY + '.'
    assert R1.state(store) == [WAITING] and shoot_cards(store, conn) == []
    assert due(store).endswith('(VS1): ' + failed) and nxt(store, conn).endswith(failed)
    assert refused(lambda: GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.')) == failed + NO_TAKE
    out = scene(store, conn)
    assert out['next'] == 'This scene is already stored: its layout video is queued again (free).' and kinds(conn)[-1] == 'guide-render'
    g = saved(store)['guides']['VS1']
    assert g['render']['status'] == 'queued' and 'error' not in g['render'] and g['stills'][0]['status'] == 'approved' and g.get('take_prompt')   # nothing else is lost
    back(store, 'guide-render')
    assert shoot_cards(store, conn) == ['shoot']


def test_a_failed_video_before_any_still_keeps_the_still_open(take_film):
    store, conn = start(take_film)
    back(store, 'guide-frame1')
    back(store, 'guide-render', ok=False, error='RuntimeError: Blender gave no answer')
    assert R1.said(store) == R1.START + R1.STILLS.format(ids='VS1', n=1) + '.'                      # the still needs only the first frame
    assert nxt(store, conn) == ORDER_NOW + 'The layout video of VS1 failed (RuntimeError: Blender gave no answer): ' + RETRY + '.'
    assert R1.state(store) == [STILL_DUE]
    assert still_made(store, conn)
    assert R1.state(store) == ['being checked by Claude']                                           # the still is made: no longer "can be ordered"


# ---------- a scene replaced ----------

def test_a_replaced_scene_gets_no_result_of_the_older_one_and_a_still_ordered_on_its_first_frame_is_dropped(take_film):
    store, conn = start(take_film)
    back(store, 'guide-frame1')
    old = saved(store)['guides']['VS1']['sha256']
    out = GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}])
    scene(store, conn, R1.changed())                                                                # the scene is replaced while its video is queued and its still is being made
    s = saved(store)
    g = s['guides']['VS1']
    assert g['sha256'] != old and 'render' not in g and g['stills'] == []                           # the existing rule: only an approved still is kept
    for kind in ('guide-frame1', 'guide-render'):
        assert GD.apply_result(s, {'id': 'j', 'request': {'kind': kind, 'shot_id': 'VS1', 'sha256': old}}, 'ready', {'frame1_key': 'x', 'frame1_sha256': 'y'}, None) is None
    still = {'id': out['job_id'], 'request': {'kind': 'guide-still', 'shot_id': 'VS1', 'sha256': old, 'reference': {'id': out['still_id']}}}
    assert GD.apply_result(s, still, 'retained', {'key': 'k'}, None) is None and 'render' not in g


def test_the_queued_first_frame_and_the_queued_video_of_a_replaced_scene_are_both_closed():
    sql = ' '.join(W.SUPERSEDE.split())
    assert "j.status='queued' and j.request->>'kind' in ('guide-frames','guide-frame1','guide-render') and exists (" in sql
    assert sql.endswith("n.request->>'kind'='guide-frames' and n.created_at > j.created_at)") and "status='running'" not in sql   # a running render is not stopped


# ---------- the same scene again: its files in storage are used ----------

def test_a_scene_sent_again_uses_the_first_frame_and_the_video_still_in_storage(take_film):
    store, conn = R1.film(take_film)
    scene(store, conn)
    a = base(store)
    scene(store, conn, R1.changed())                                                                # another scene, then back to the first
    scene(store, conn)
    store.files[a + '/frame1.png'], store.files[a + '/guide.mp4'] = b'frame-one', b'the-video'      # as its earlier render left them
    n = len(conn.queued)
    out = GD.verdict(conn, store, OTHER, NEW, [], 'VS1', frames_back(store, conn), True, [{'look': 'everyone reads as a person', 'pass': True}])
    assert len(conn.queued) == n and 'used again' in out['next']                                    # nothing is rendered again
    assert saved(store)['guides']['VS1']['render'] == {'status': 'ready', 'reused': True, 'frame1_key': a + '/frame1.png', 'frame1_sha256': hashlib.sha256(b'frame-one').hexdigest(),
                                                       'guide_key': a + '/guide.mp4', 'sha256': hashlib.sha256(b'the-video').hexdigest(), 'bytes': 9}


def test_only_the_first_frame_in_storage_queues_only_the_video(take_film):
    store, conn = R1.film(take_film)
    scene(store, conn)
    store.files[base(store) + '/frame1.png'] = b'frame-one'
    passed(store, conn)
    g = saved(store)['guides']['VS1']
    assert kinds(conn) == ['guide-frames', 'guide-render'] and g['render']['status'] == 'queued' and g['render']['frame1_key'] == base(store) + '/frame1.png'
    assert R1.said(store) == R1.START + R1.STILLS.format(ids='VS1', n=1) + '.'


# ---------- the film in mid-step at the deploy ----------

def test_a_record_of_the_older_code_reads_as_before(take_film):
    store, conn = start(take_film)
    s = saved(store)
    g = s['guides']['VS1']
    g['render'] = {'job_id': 'r', 'status': 'queued'}                                               # one job, queued before the deploy
    VS.save_session(store, NEW, s)
    assert R1.state(store) == ['being made'] and R1.said(store) == '' and due(store) == ''
    assert nxt(store, conn).endswith('The first frame of VS1 is being made (free, under a minute of rendering); the still can be ordered when it is ready.')
    back(store, 'guide-frame1')                                                                     # the first frame the new worker makes for it (`BACKFILL`)
    assert R1.said(store) == R1.START + R1.STILLS.format(ids='VS1', n=1) + '.'
    R1.rendered(store)                                                                              # the older job's own result: both files, as before
    g = saved(store)['guides']['VS1']
    assert g['render'] == {'job_id': 'r', 'status': 'ready', 'guide_key': 'g.mp4', 'sha256': 'sha-guide', 'bytes': 9, 'frame1_key': 'f1.png', 'frame1_sha256': 'sha-f1', 'render_seconds': 600}
    to = GD.ready_card(saved(store), 'VS1', 8.0)
    assert to['missing'] == ['an approved still made from this guide', 'the overlay', "the take's words"] and to['guide_key'] == 'g.mp4'


def test_a_queued_video_job_of_the_older_kind_gets_its_first_frame_job_from_the_worker(monkeypatch):
    sql = ' '.join(W.BACKFILL.split())
    assert sql.startswith("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) select j.run_id, j.stage, j.unit, j.provider, "
                          "jsonb_set(j.request, '{kind}', '\"guide-frame1\"'), gen_random_uuid() from vw2_jobs j where j.provider='guide' and j.status='queued' "
                          "and j.request->>'kind'='guide-render' and not (j.request ? 'split') and not exists (")
    assert sql.endswith("n.request->>'kind'='guide-frame1' and n.request->>'sha256'=j.request->>'sha256')") and '%' not in sql
    conn = LaneConn(running=set(), queued=[])
    run_tick(monkeypatch, conn)
    sqls = [s for s, _ in conn.sql]
    first_claim = next(i for i, s in enumerate(sqls) if 'update vw2_jobs set status = case' in s and conn.sql[i][1][0] == 'guide')
    assert sqls.index(W.SUPERSEDE) < sqls.index(W.BACKFILL) < first_claim                           # after the replaced jobs are closed, before the quick lane takes a job


def test_a_fault_in_the_backfill_never_stops_the_lanes(monkeypatch):
    class Faulty(LaneConn):
        def execute(self, sql, params=()):
            if sql == W.BACKFILL:
                raise RuntimeError('syntax error')
            return super().execute(sql, params)
    conn = Faulty(running=set(), queued=[lane_job('guide-render'), lane_job('guide-frames')])
    assert run_tick(monkeypatch, conn) == ['guide-frames', 'guide-render']


# ---------- the worker: two kinds of job, today's settings ----------

def ffmpeg_into(monkeypatch, encoded):
    def ffmpeg(cmd, **kw):
        encoded.append(cmd)
        Path(cmd[-1]).write_bytes(b'\x00\x00\x00\x18ftypmp42-guide')
        return type('R', (), {'returncode': 0, 'stderr': ''})()
    monkeypatch.setattr(W.subprocess, 'run', ffmpeg)


def test_the_first_frame_job_is_one_blender_call_at_full_quality(blender):
    calls, store, tmp = blender
    status, result, error, cost, retry = W.process(job('guide-frame1', seconds=5))
    assert status == 'ready' and error is None and cost == {'provider': 'guide', 'inr': 0}
    assert calls == [{'frames': [1], 'samples': 16, 'outdir': 'first', 'look': 'eevee'}]                          # the same call as the frame-1 step of the one job before
    data = store.files['run-1/visuals/guides/abc/frame1.png']
    assert result['frame1_key'] == 'run-1/visuals/guides/abc/frame1.png' and result['frame1_sha256'] == hashlib.sha256(data).hexdigest() and 'guide_key' not in result
    assert not [k for k in store.files if k.endswith('.mp4')] and not (tmp / 'j1').exists()


def test_the_video_job_does_not_render_the_first_frame_again_and_encodes_as_before(blender, monkeypatch):
    calls, store, tmp = blender
    store.files['run-1/visuals/guides/abc/frame1.png'] = b'the-first-frame-as-its-own-job-left-it'
    encoded, renewed = [], []
    ffmpeg_into(monkeypatch, encoded)
    status, result, error, cost, retry = W.process(job('guide-render', seconds=5, split=True), renew=lambda: renewed.append(1))
    assert status == 'ready', error
    assert [c['frames'][0] for c in calls] == [1, 31, 61, 91, 121] and all(c['samples'] == 1 and c['outdir'] == 'all' for c in calls) and len(renewed) == 5   # no 16-sample call
    folder = str(tmp / 'j1')
    assert encoded == [[W.settings().FFMPEG_EXECUTABLE, '-y', '-v', 'error', '-framerate', '30', '-i', str(Path(folder) / 'all' / 'g%04d.png'), '-c:v', 'libx264', '-crf', '16',
                        '-pix_fmt', 'yuv420p', str(Path(folder) / 'guide.mp4')]]                    # the encoder's line, as it was
    assert store.files['run-1/visuals/guides/abc/frame1.png'] == b'the-first-frame-as-its-own-job-left-it'
    assert result['frame1_sha256'] == hashlib.sha256(b'the-first-frame-as-its-own-job-left-it').hexdigest() and result['frames'] == 150
    assert set(result) == {'guide_key', 'sha256', 'bytes', 'frame1_key', 'frame1_sha256', 'frames', 'render_seconds', 'look'}   # the same record as before, with the look (layout B)


def test_a_blender_fault_fails_the_first_frame_job_with_its_reason(blender, monkeypatch):
    calls, store, tmp = blender

    def broken(*a, **kw):
        raise RuntimeError('Blender did not build the guide: GUIDE FAILED: KeyError: colour')
    monkeypatch.setattr(W, 'run_blender', broken)
    status, result, error, cost, retry = W.process(job('guide-frame1', seconds=5))
    assert status == 'failed' and result == {'phase': 'guide-frame1'} and 'KeyError: colour' in error and not [k for k in store.files if k.endswith('frame1.png')]


# ---------- the lanes ----------

def test_the_first_frame_is_taken_while_a_video_renders_and_before_the_check_frames(monkeypatch):
    conn = LaneConn(running={'guide-render'}, queued=[lane_job('guide-render'), lane_job('guide-frames'), lane_job('guide-frame1')])
    assert run_tick(monkeypatch, conn) == ['guide-frame1']                                          # a passed layout is further along; never behind a video
    assert [j['request']['kind'] for j in conn.queued] == ['guide-render', 'guide-frames']
    assert run_tick(monkeypatch, conn) == ['guide-frames']


def test_one_quick_blender_job_at_a_time_beside_one_video(monkeypatch):
    conn = LaneConn(running={'guide-frames'}, queued=[lane_job('guide-frame1'), lane_job('guide-render')])
    assert run_tick(monkeypatch, conn) == ['guide-render']
    conn = LaneConn(running={'guide-frame1'}, queued=[lane_job('guide-frames')])
    assert run_tick(monkeypatch, conn) == []
    conn = LaneConn(running=set(), queued=[lane_job('guide-render'), lane_job('guide-frames'), lane_job('guide-frame1')])
    assert run_tick(monkeypatch, conn) == ['guide-frame1', 'guide-render']


# ---------- the words ----------

def test_the_served_text_and_the_skill_say_the_first_frame_first():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import rel4_wording as R
    st = next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
    later = next(p for p in st['parts'] if p['name'] == 'later')['text']
    assert later.count(R.NEW) == 1 and 'as soon as its first frame is ready' in R.NEW and 'needed only for the take' in R.NEW
    old = R.before(st)
    was = next(p for p in old['parts'] if p['name'] == 'later')['text']
    assert was.count(R.OLD) == 1 and R.NEW not in was and old['prompt'] == st['prompt']
    added = sum(len(p['text'].split()) for p in st['parts']) - sum(len(p['text'].split()) for p in old['parts'])
    assert 0 < added <= 45, added
    skill = (ROOT / 'plugin' / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8')
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert skill.count(R.SKILL_NEW) == 1 and R.SKILL_OLD not in skill and R.SKILL_OLD in retired
    assert GD.START_PICTURE_RETIRED.endswith('`vw guide still --shot S --file …` as soon as that first frame is rendered (the vw:guide skill).')   # until then: "after the guide is rendered"
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('from rel2c_wording import apply as rel2c') < split.index('from rel4_wording import apply as rel4') < split.index('from d132_wording_v3 import')
