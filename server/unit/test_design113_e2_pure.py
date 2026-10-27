"""design/113 E2 and E4: the renderer draws the scene's exact frames (Pillow and ffmpeg), keyed to seconds or narration words; the render is a free
job reviewed like a take; the font is the repo's Noto Sans or the run's brand font, never a silent substitute."""
import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app import drawn as D, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from test_batch89b_pure import SPEC
from test_design113_e1_pure import SCENE
from test_visuals_stage_pure import RUN, USER, FakeConn, FakeStore, accepted, g, gap_digest, plan_doc, saved, session, shot

ARIAL = Path('C:/Windows/Fonts/arial.ttf')
FONT = str(ARIAL) if ARIAL.exists() else None


def request(frames=10, fps='25', **over):
    return {'scene': copy.deepcopy(SCENE), 'labels': [{'id': 'label-1', 'kind': 'text', 'x': 158, 'y': 30, 'text': 'leaf thickness 110 mm', 'size_pct': 4, 'stroke': '#222222', 'bold': False, 'leader': [150, 30]}],
            'width': 320, 'height': 180, 'fps': fps, 'frames': frames, 'cues': [0.0, 0.2, 0.3], **({'font': FONT} if FONT else {}), **over}


# ---------- the timeline ----------

def test_actions_set_each_shapes_state_per_frame():
    sc = copy.deepcopy(SCENE)
    st = D.states(sc, [0.0, 1.0, 2.5], '25', 100)
    assert st[0]['outer']['visible'] and not st[0]['cavity']['visible'] and not st[0]['air']['visible']   # named by a build: waits
    assert st[25]['cavity']['visible'] and not st[25]['air']['visible'] and st[38]['air']['visible']   # every 0.5 s: the second shape 12-13 frames later
    assert st[62]['cavity']['highlight'] == 1.0 and st[90]['cavity']['highlight'] == 0.0   # one second of highlight from 2.5 s
    sc['actions'].append({'kind': 'fade', 'ids': ['title'], 'seconds': 1})
    sc['actions'].append({'kind': 'move', 'ids': ['air'], 'path': [[200, 250], [200, 150]], 'seconds': 2})
    st = D.states(sc, [0.0, 1.0, 2.5, 2.0, 1.0], '25', 100)
    assert st[74]['title']['alpha'] < 0.1 and not st[75]['title']['visible'] and st[50]['air']['dy'] == -50.0 and st[99]['air']['dy'] == -100.0   # the fade from 2.0 s over 1 s
    sc['shapes'].append({'id': 'both', 'kind': 'group', 'members': ['outer', 'inner']})
    sc['actions'] = [{'kind': 'appear', 'ids': ['both'], 'at_s': 1}]
    st = D.states(sc, [1.0], '25', 50)
    assert not st[0]['outer']['visible'] and st[25]['inner']['visible']   # a group stands for its members


def test_cues_come_from_seconds_or_the_timed_narration():
    sh = {'id': 'DR1', 'start_frame': 100, 'end_frame': 200}
    words = [{'text': 'The', 'start_frame': 100, 'end_frame': 104}, {'text': 'cavity', 'start_frame': 140, 'end_frame': 150}, {'text': 'holds', 'start_frame': 160, 'end_frame': 170},
             {'text': 'still', 'start_frame': 171, 'end_frame': 180}, {'text': 'air.', 'start_frame': 181, 'end_frame': 190}]
    assert D.cue_seconds(SCENE, sh, words, '25') == [0.0, 1.6, 2.5]
    sc = copy.deepcopy(SCENE)
    sc['actions'][1]['word'] = 'still air'
    assert D.cue_seconds(sc, sh, words, '25')[1] == 2.84
    with pytest.raises(ValueError, match="'cavity' but the run has no timed narration: give at_s"):
        D.cue_seconds(SCENE, sh, [], '25')
    with pytest.raises(ValueError, match="not spoken inside DR1"):
        D.cue_seconds(SCENE, {'id': 'DR1', 'start_frame': 0, 'end_frame': 90}, words, '25')


def test_the_canvas_is_contained_with_a_margin():
    to, scale = D.layout({'width': 400, 'height': 300}, 1920, 1080)
    assert abs(scale - 1080 * 0.92 / 300) < 1e-9 and to(0, 0)[1] == pytest.approx(1080 * 0.04) and to(400, 300)[1] == pytest.approx(1080 * 0.96)


def test_a_missing_or_unreadable_font_fails_by_name(tmp_path, monkeypatch):
    assert D.font_file(False, None).name == 'NotoSans-Variable.ttf' and D.font_file(True, None).name == 'NotoSans-Variable.ttf'   # the repo font, one file for both weights
    assert D.typeface(D.font_file(True), 40, True).getlength('Rat-trap') > D.typeface(D.font_file(False), 40, False).getlength('Rat-trap')   # the Bold instance is wider
    monkeypatch.setattr(D, 'FONTS', tmp_path / 'no-fonts')
    with pytest.raises(ValueError, match='NotoSans-Variable.ttf is not there \(under server/fonts\)'):
        D.font_file(False, None)
    bad = tmp_path / 'brand.ttf'
    bad.write_bytes(b'not a font')
    with pytest.raises(ValueError, match='brand.ttf cannot be read by Pillow'):
        D.font_file(False, str(bad))
    with pytest.raises(ValueError, match='gone.otf is not there \\(the brand font of this run\\)'):
        D.font_file(False, str(tmp_path / 'gone.otf'))


@pytest.mark.skipif(not FONT, reason='no TTF to draw with on this machine')
def test_frames_are_drawn_the_same_twice_and_change_with_the_actions():
    req = request()
    first, again, last = D.frame_png(req, 0), D.frame_png(req, 0), D.frame_png(req, 9)
    assert first == again and first != last   # the build has happened by the last frame
    assert len(first) > 1000


@pytest.mark.skipif(not (FONT and shutil.which('ffmpeg') and shutil.which('ffprobe')), reason='ffmpeg or a font is missing on this machine')
def test_the_render_has_exactly_the_shots_frames_at_the_films_size(tmp_path):
    out = tmp_path / 'dr1.mp4'
    rec = D.render(request(frames=12), out)
    assert rec['frames'] == 12 and out.exists() and len(rec['digest']) == 64
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames,width,height', '-of', 'json', str(out)],
                                      capture_output=True, check=True, timeout=60).stdout)['streams'][0]
    assert int(probe['nb_read_frames']) == 12 and (probe['width'], probe['height']) == (320, 180)


# ---------- the job ----------

def drawn_store(approved=True, words=True):
    sh = {**shot('DR1', 0, 100, 'diagram'), 'visual_type': 'drawn', 'depicts': 'the wall section', 'narration': 'The cavity between the two leaves holds still air.',
          'drawing_spec': copy.deepcopy(SPEC), 'scene_drawn': copy.deepcopy(SCENE)}
    doc = plan_doc([sh, shot('IM1', 100, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   spec_approvals={'DR1': {'digest': VS.spec_digest(SPEC)}} if approved else {})
    sess['source']['gaps']['G1'] = {**sess['source']['gaps']['G1'], 'timing': {'words': [{'text': 'The', 'start_frame': 0, 'end_frame': 4}, {'text': 'cavity', 'start_frame': 40, 'end_frame': 50}]}} if words else {k: v for k, v in sess['source']['gaps']['G1'].items() if k != 'timing'}
    return store_with_(sess, doc)


def store_with_(sess, doc):
    from test_visuals_stage_pure import store_with
    return store_with(sess, doc)


def test_the_render_job_needs_the_approved_spec_and_is_free_and_cached_by_its_scene():
    with pytest.raises(Problem, match='drawing spec of DR1 is not approved'):
        g(lambda: VS.render_drawn(FakeConn([]), drawn_store(approved=False), USER, RUN, [], {'shot_id': 'DR1'}))
    with pytest.raises(Problem, match="keyed to the word 'cavity' but the run has no timed narration"):
        g(lambda: VS.render_drawn(FakeConn([]), drawn_store(words=False), USER, RUN, [], {'shot_id': 'DR1'}))
    with pytest.raises(Problem, match='IM1 is image: `draw` is for a drawn shot'):
        g(lambda: VS.render_drawn(FakeConn([]), drawn_store(), USER, RUN, [], {'shot_id': 'IM1'}))
    store, conn = drawn_store(), FakeConn([])
    out = VS.render_drawn(conn, store, USER, RUN, [], {'shot_id': 'DR1'})
    assert out['job_id'] == 'job-1' and out['frames'] == 100 and 'free' in out['next']
    sql, params = conn.inserted[0][0] if isinstance(conn.inserted[0], tuple) and len(conn.inserted[0]) == 2 and isinstance(conn.inserted[0][0], str) else (None, conn.inserted[0])
    assert params[1] == 'DR1' and "'drawn'" in conn.sql[-1][0]
    req = json.loads(store.files[saved(store)['preparations']['DR1']['key']])
    assert req['cues'] == [0.0, 1.6, 2.5] and req['width'] == 1920 and req['frames'] == 100 and req['labels'][0]['text'] == 'leaf thickness 110 mm'
    again = VS.render_drawn(FakeConn([{'id': 'job-1', 'unit': 'DR1', 'provider': 'drawn', 'status': 'ready', 'request': {'preparation_id': out['preparation_id']}}]), store, USER, RUN, [], {'shot_id': 'DR1'})
    assert again['cached'] and again['job_id'] == 'job-1'


@pytest.mark.skipif(not (FONT and shutil.which('ffmpeg')), reason='ffmpeg or a font is missing on this machine')
def test_the_worker_renders_stores_and_measures_the_file(tmp_path, monkeypatch):
    req = request(frames=10)
    req.update(placement={'start_frame': 0, 'end_frame': 10, 'film_fps': '25', 'duration_seconds': '2/5', 'exact_seconds': 0.4}, images={})
    store = FakeStore({'run-1/visuals/takes/p1.drawn.json': req})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    status, result, error, cost, retry = VW.process_drawn({'id': 'j1', 'run_id': 'run-1', 'request': {'request_key': 'run-1/visuals/takes/p1.drawn.json', 'preparation_id': 'p1'}})
    assert status == 'ready' and result['key'] == 'run-1/visuals/drawn/j1.mp4' and store.files[result['key']] and cost == {'provider': 'drawn', 'seconds': 0.4, 'inr': 0}
    assert [c['check'] for c in result['code']] == ['frames', 'size'] and all(c['pass'] for c in result['code'])
    monkeypatch.setattr(VW, 'SPOOL', tmp_path / 'again')
    status, result, error, _, _ = VW.process_drawn({'id': 'j2', 'run_id': 'run-1', 'request': {'request_key': 'run-1/visuals/takes/none.json', 'preparation_id': 'p2'}})
    assert status == 'failed' and 'Render failed' in error
