"""design/130 phase 1: the HyperFrames motion route on the server (the project upload and its rules, the labels word for word, the timing sidecar from the
plan's cues, the run's drawn route, the render and tool jobs in the worker with the CLI faked, held selection, the render cap)."""
import copy
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from app import drawn as D, motion as M, visual_contract as VC, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from test_batch89b_pure import SPEC
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, g, plan_doc, ref, saved, session, shot, store_with

MRUN = {**RUN, 'drawn_route': 'motion'}
FONTS = ('Noto Sans',)

INDEX = '''<!doctype html><html><head><meta charset="utf-8"><script src="assets/vendor/gsap.min.js"></script>
<style>@font-face { font-family: "Noto Sans"; src: url("assets/fonts/NotoSans-Variable.ttf"); } body { font-family: "Noto Sans", sans-serif; }</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="4" data-fps="25" data-width="1920" data-height="1080">
<div id="wall" data-composition-id="wall" data-composition-src="compositions/wall.html" data-start="0" data-duration="4"></div></div>
<script>window.__timelines["main"] = gsap.timeline({ paused: true });</script></body></html>'''
WALL = '''<template><style>#root { position: absolute; inset: 0; font-family: "Noto Sans", sans-serif; }</style>
<div id="root" data-composition-id="wall" data-width="1920" data-height="1080">
<svg viewBox="0 0 1920 1080"><image href="assets/ref/comp-1.png" x="0" y="0" width="200" height="100"/></svg>
<div id="label" class="clip" data-start="1" data-duration="3">Solid brick-on-edge course<br>at sill level</div>
<div id="note" class="clip" data-start="0" data-duration="4">Illustrative, not to scale</div></div>
<script>const tl = gsap.timeline({ paused: true }); tl.fromTo("#label", { opacity: 0 }, { opacity: 1, duration: 0.2 }, 1); window.__timelines["wall"] = tl;</script></template>'''


def zipped(files, top=''):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for name, text in files.items():
            z.writestr(top + name, text)
    return buf.getvalue()


def project(**over):
    files = {'index.html': INDEX, 'compositions/wall.html': WALL}
    files.update(over)
    return {k: v for k, v in files.items() if v is not None}


def unpack(files, top=''):
    return M.unpack(zipped(files, top))


REFS = {'comp-1': {'status': 'approved', 'key': 'run-1/visuals/references/comp-1.png'}, 'cand-1': {'status': 'candidate'}}


def probs(files, **kw):
    args = dict(refs=REFS, fonts=FONTS, frames=100, fps='25', width=1920, height=1080)
    args.update(kw)
    return M.problems(files, **args)


# ---------- the project and its rules ----------

def test_unpack_reads_a_zip_strips_one_top_folder_and_refuses_what_is_not_a_project():
    assert set(unpack(project(), top='shot/')) == {'index.html', 'compositions/wall.html'}
    with pytest.raises(ValueError, match='not a zip'):
        M.unpack(b'not a zip')
    with pytest.raises(ValueError, match='outside the project'):
        unpack({'index.html': INDEX, '../evil.js': 'x'})
    with pytest.raises(ValueError, match='outside the project'):
        unpack({'index.html': INDEX, '/etc/x.js': 'x'})
    with pytest.raises(ValueError, match='too many files'):
        unpack({**{f'f{i}.css': '' for i in range(M.MAX_FILES + 1)}, 'index.html': INDEX})


def test_a_good_project_passes_the_rules():
    assert probs(unpack(project())) == []


@pytest.mark.parametrize('over,match', [
    ({'index.html': INDEX.replace('assets/vendor/gsap.min.js', 'https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js')}, 'loads from the network'),
    ({'compositions/wall.html': WALL.replace('#root {', '@import url("https://fonts.googleapis.com/css2?family=Inter"); #root {')}, 'loads from the network'),
    ({'compositions/wall.html': WALL.replace('font-family: "Noto Sans", sans-serif;', 'font-family: "Inter", sans-serif;')}, 'font Inter'),
    ({'compositions/wall.html': WALL.replace('tl.fromTo', 'Math.random(); tl.fromTo')}, 'Math.random'),
    ({'compositions/wall.html': WALL.replace('comp-1.png', 'cand-1.png')}, 'ref cand-1 is not an approved picture'),
    ({'compositions/wall.html': WALL.replace('comp-1.png', 'nope.png')}, 'ref nope is not an approved picture'),
    ({'assets/vendor/gsap.min.js': 'evil'}, 'the server supplies assets/vendor'),
    ({'index.html': None}, 'no index.html'),
    ({'run.exe': 'x'}, 'run.exe: a .exe file'),
])
def test_the_rules_refuse_what_breaks_them(over, match):
    assert any(match in p for p in probs(unpack(project(**over)))), probs(unpack(project(**over)))


def test_the_root_must_match_the_shot_length_the_frame_rate_and_the_size():
    assert any('4 s is 100 frames at 25 fps; the shot is 139' in p for p in probs(unpack(project()), frames=139))
    assert any('data-fps 25' in p for p in probs(unpack(project()), fps='30', frames=120))
    assert any('1920x1080' in p for p in probs(unpack(project()), width=1080, height=1920))


def test_labels_are_read_word_for_word_from_the_visible_text():
    files = unpack(project())
    assert 'Solid brick-on-edge course at sill level' in M.visible_text(files)
    assert M.missing_labels(files, ['Solid brick-on-edge course at sill level', 'Illustrative, not to scale']) == []
    assert M.missing_labels(files, ['Solid course at sill level', 'illustrative, not to scale']) == ['Solid course at sill level', 'illustrative, not to scale']
    assert 'tl.fromTo' not in M.visible_text(files)


def test_the_sidecar_puts_each_cue_on_its_selector_and_a_missing_selector_is_named():
    files = unpack(project())
    assert M.sidecar([1.0, 0.0], ['#label', '#note']) == {'assertions': [{'kind': 'appearsBy', 'selector': '#label', 'bySec': 1.6}, {'kind': 'appearsBy', 'selector': '#note', 'bySec': 0.6}]}
    assert M.missing_selectors(files, ['#label', '#ghost']) == ['#ghost']


def test_prepare_places_the_server_files_beside_the_project(tmp_path):
    M.prepare(tmp_path, unpack(project()), gsap=b'gsap!', fonts={'NotoSans-Variable.ttf': b'font'}, refs={'comp-1': b'png'}, sidecar={'assertions': []})
    assert (tmp_path / 'assets/vendor/gsap.min.js').read_bytes() == b'gsap!' and (tmp_path / 'assets/fonts/NotoSans-Variable.ttf').read_bytes() == b'font'
    assert (tmp_path / 'assets/ref/comp-1.png').read_bytes() == b'png' and not (tmp_path / 'index.motion.json').exists()   # M1, 11 Nov 2026: no cue, no timing file
    assert (tmp_path / 'compositions/wall.html').read_text(encoding='utf-8') == WALL


# ---------- the plan contract ----------

def motion_shot(**over):
    sh = {**shot('MO1', 0, 100, 'diagram'), 'visual_type': 'drawn', 'depicts': 'the wall', 'narration': 'Providing a solid course at sill level improves strength.',
          'drawing_spec': copy.deepcopy(SPEC), 'scene_motion': {'sha256': 'b' * 64, 'labels': ['Solid brick-on-edge course at sill level'], 'cues': [{'selector': '#label', 'word': 'solid'}]}}
    sh.update(over)
    return sh


def test_the_contract_takes_a_motion_scene_and_checks_its_cues():
    s = VC.Shot.model_validate(motion_shot())
    assert s.scene_motion.labels == ['Solid brick-on-edge course at sill level'] and s.scene_motion.cues[0].selector == '#label'
    VC.motion_needs(s, 4.0)
    with pytest.raises(ValueError, match="the word 'mortar' is not in the narration"):
        VC.motion_needs(VC.Shot.model_validate(motion_shot(scene_motion={'sha256': 'b' * 64, 'labels': [], 'cues': [{'selector': '#label', 'word': 'mortar'}]})), 4.0)
    with pytest.raises(ValueError, match='past the end'):
        VC.motion_needs(VC.Shot.model_validate(motion_shot(scene_motion={'sha256': 'b' * 64, 'labels': [], 'cues': [{'selector': '#label', 'at_s': 9}]})), 4.0)
    with pytest.raises(ValueError, match='scene_svg or scene_motion, not both'):
        VC.motion_needs(VC.Shot.model_validate(motion_shot(scene_svg={'sha256': 'a' * 64, 'actions': []})), 4.0)
    with pytest.raises(Exception):
        VC.Shot.model_validate(motion_shot(scene_motion={'sha256': 'b' * 64, 'labels': [], 'cues': [{'selector': 'label', 'at_s': 1}]}))


# ---------- the stage: upload, tools, render ----------

def motion_store(approved=True, sh=None):
    doc = plan_doc([sh or motion_shot(), shot('IM1', 100, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    doc['foundation']['graphic_style'] = {'palette': 'terracotta #B5543A, paper #F4EDE1'}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   spec_approvals={'MO1': {'digest': VS.spec_digest(SPEC)}} if approved else {})
    sess['source']['gaps']['G1'] = {**sess['source']['gaps']['G1'], 'timing': {'words': [{'text': 'Providing', 'start_frame': 0, 'end_frame': 10}, {'text': 'solid', 'start_frame': 21, 'end_frame': 30}]}}
    sess['references'] = {'comp-1': {**ref('comp-1', 'approved'), 'kind': 'component', 'element_id': 'E1'}, 'ST1': {**ref('ST1', 'approved'), 'kind': 'style', 'element_id': VS.STYLE}}
    store = store_with(sess, doc)
    store.files['run-1/visuals/references/comp-1.png'] = b'\x89PNGcomp'
    return store


def upload(store, files=None, run=MRUN):
    return VS.set_motion(store, USER, run, [], 'MO1', 'shot.zip', zipped(files or project()))


def named(store, sha):
    """The plan's scene_motion pointed at the uploaded project, as the planner does after the upload."""
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])
    doc['document']['gaps'][0]['scenes'][0]['shots'][0]['scene_motion']['sha256'] = sha
    store.files['run-1/visuals/plan-v1.json'] = json.dumps(doc).encode('utf-8')


def test_set_motion_stores_the_project_and_refuses_on_an_svg_run_or_a_broken_project():
    store = motion_store()
    out = upload(store)
    sha = hashlib.sha256(zipped(project())).hexdigest()
    assert out['sha256'] == sha and out['refs'] == ['comp-1'] and 'Solid brick-on-edge course at sill level' in out['text'] and sha in out['next']
    assert saved(store)['motion_projects'][sha]['key'] == f'run-1/visuals/motion/projects/{sha}.zip' and store.files[f'run-1/visuals/motion/projects/{sha}.zip'] == zipped(project())
    with pytest.raises(Problem, match='draws its drawn shots as SVG scenes'):
        g(lambda: upload(motion_store(), run=RUN))
    with pytest.raises(Problem, match='breaks the rules.*network'):
        g(lambda: upload(motion_store(), project(**{'index.html': INDEX.replace('assets/vendor/gsap.min.js', 'https://cdn.jsdelivr.net/gsap.js')})))
    with pytest.raises(Problem, match='one .zip file'):
        g(lambda: VS.set_motion(motion_store(), USER, MRUN, [], 'MO1', 'shot.html', b'x'))


def test_render_motion_builds_the_request_and_refuses_what_is_not_ready():
    store = motion_store()
    sha = upload(store)['sha256']
    named(store, sha)
    conn = FakeConn([])
    out = VS.render_motion(conn, store, USER, MRUN, [], {'shot_id': 'MO1'})
    assert out['job_id'] == 'job-1' and out['frames'] == 100
    assert conn.inserted and "'drawn'" in conn.sql[-1][0]
    req = json.loads(store.files[saved(store)['preparations']['MO1']['key']])
    assert req['kind'] == 'motion' and req['project_key'] == f'run-1/visuals/motion/projects/{sha}.zip' and req['frames'] == 100 and req['fps'] == '25'
    assert req['labels'] == ['Solid brick-on-edge course at sill level'] and req['images'] == {'comp-1': 'run-1/visuals/references/comp-1.png'}
    assert req['sidecar'] == {'assertions': [{'kind': 'appearsBy', 'selector': '#label', 'bySec': 1.44}]}   # 'solid' starts at frame 21 = 0.84 s
    assert req['claims'] == [] and req['relationships'] == SPEC['relationships'] and 'terracotta' in req['palette']
    again = VS.render_motion(FakeConn([{'id': 'job-1', 'unit': 'MO1', 'provider': 'drawn', 'status': 'ready', 'request': {'preparation_id': out['preparation_id']}}]), store, USER, MRUN, [], {'shot_id': 'MO1'})
    assert again['cached'] and again['job_id'] == 'job-1'
    with pytest.raises(Problem, match='draws its drawn shots with HyperFrames'):
        g(lambda: VS.render_drawn(FakeConn([]), store, USER, MRUN, [], {'shot_id': 'MO1'}))
    with pytest.raises(Problem, match='names no uploaded project'):
        g(lambda: VS.render_motion(FakeConn([]), motion_store(), USER, MRUN, [], {'shot_id': 'MO1'}))
    unapproved = motion_store(approved=False)
    named(unapproved, upload(unapproved)['sha256'])
    with pytest.raises(Problem, match='drawing spec of MO1 is not approved'):
        g(lambda: VS.render_motion(FakeConn([]), unapproved, USER, MRUN, [], {'shot_id': 'MO1'}))
    wrong = motion_store(sh=motion_shot(scene_motion={'sha256': 'b' * 64, 'labels': ['Solid course at sill level'], 'cues': []}))
    named(wrong, upload(wrong)['sha256'])
    with pytest.raises(Problem, match='does not show the label "Solid course at sill level"'):
        g(lambda: VS.render_motion(FakeConn([]), wrong, USER, MRUN, [], {'shot_id': 'MO1'}))


def test_a_tool_job_checks_or_snapshots_any_uploaded_project_of_the_shot():
    store = motion_store()
    sha = upload(store)['sha256']
    conn = FakeConn([])
    out = VS.motion_tool(conn, store, USER, MRUN, [], {'shot_id': 'MO1', 'op': 'snapshot', 'sha256': sha, 'at': [0.5, 2.0], 'zoom': '#label'})
    assert out['job_id'] == 'job-1' and "'motion'" in conn.sql[-1][0]
    req = json.loads(store.files[out['request_key']])
    assert req['kind'] == 'motion-snapshot' and req['at'] == [0.5, 2.0] and req['zoom'] == '#label' and req['project_key'].endswith(f'{sha}.zip')
    with pytest.raises(Problem, match='op is check or snapshot'):
        g(lambda: VS.motion_tool(FakeConn([]), store, USER, MRUN, [], {'shot_id': 'MO1', 'op': 'render', 'sha256': sha}))
    with pytest.raises(Problem, match='no uploaded project'):
        g(lambda: VS.motion_tool(FakeConn([]), store, USER, MRUN, [], {'shot_id': 'MO1', 'op': 'check', 'sha256': 'c' * 64}))


# ---------- the worker, with the CLI faked ----------

def tiny_mp4(path, frames, size='64x36'):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc=size={size}:rate=25', '-frames:v', str(frames), '-pix_fmt', 'yuv420p', str(path)], check=True)


def worker_fakes(monkeypatch, store, tmp_path, frames=100, check_ok=True):
    calls = {'check': 0, 'render': [], 'snapshot': []}
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(M, 'gsap_bytes', lambda: b'gsap')

    def check(folder):
        calls['check'] += 1
        assert (Path(folder) / 'assets/vendor/gsap.min.js').exists()   # M1: the timing file is there only with a cue
        return {'ok': check_ok, 'errors': [] if check_ok else [{'code': 'motion_appears_late', 'message': '#label appears at 2.1 s, after 1.44 s', 'fix': 'start it earlier'}], 'warnings': []}

    def render(folder, fps, out):
        calls['render'].append(fps)
        tiny_mp4(out, frames)
        return out

    def snapshot(folder, at, zoom, out_dir):
        calls['snapshot'].append((at, zoom))
        paths = []
        for n, t in enumerate(at):
            p = Path(out_dir) / f'{n}.png'
            p.write_bytes(b'\x89PNG' + str(t).encode())
            paths.append(p)
        return paths

    monkeypatch.setattr(M, 'check', check)
    monkeypatch.setattr(M, 'render', render)
    monkeypatch.setattr(M, 'snapshot', snapshot)
    monkeypatch.setattr(D, 'sheet', lambda frames_, fps, W, H, **k: b'\xff\xd8sheet')
    monkeypatch.setattr(VW, 'probe', lambda path: {'duration_seconds': frames / 25, 'width': 1920, 'height': 1080, 'issues': []})
    return calls


def render_job(store):
    sha = upload(store)['sha256']
    named(store, sha)
    VS.render_motion(FakeConn([]), store, USER, MRUN, [], {'shot_id': 'MO1'})
    prep = saved(store)['preparations']['MO1']
    return {'id': 'job-9', 'run_id': 'run-1', 'unit': 'MO1', 'provider': 'drawn', 'request': {'kind': 'motion', 'request_key': prep['key'], 'shot_id': 'MO1', 'frames': 100}}


def test_the_worker_checks_renders_and_keeps_the_movie_the_sheet_and_the_code_lines(monkeypatch, tmp_path):
    store = motion_store()
    calls = worker_fakes(monkeypatch, store, tmp_path)
    status, result, error, cost, retry = VW.process_drawn(render_job(store))
    assert status == 'ready' and error is None and cost == {'provider': 'motion', 'seconds': 4.0, 'inr': 0}
    assert calls['check'] == 1 and calls['render'] == ['25']
    assert result['provider_id'] == 'motion' and result['key'] == 'run-1/visuals/drawn/job-9.mp4' and store.files[result['key']][:4] != b''
    assert result['sheet_key'] == 'run-1/visuals/drawn/job-9-sheet-1.jpg' and store.files[result['sheet_key']] == b'\xff\xd8sheet'
    assert result['evidence']['timing_matches_placement'] and all(c['pass'] for c in result['code']) and result['check']['must_failed'] == []


def test_a_check_error_fails_the_render_with_the_finding_and_a_wrong_length_is_held(monkeypatch, tmp_path):
    store = motion_store()
    worker_fakes(monkeypatch, store, tmp_path, check_ok=False)
    status, result, error, _, _ = VW.process_drawn(render_job(store))
    assert status == 'failed' and result['phase'] == 'check' and 'motion_appears_late' in error and 'start it earlier' in error
    store2 = motion_store()
    worker_fakes(monkeypatch, store2, tmp_path / 'b', frames=90)
    status, result, _, _, _ = VW.process_drawn(render_job(store2))
    assert status == 'ready' and [c['check'] for c in result['check']['must_failed']] == ['frames']


def test_tool_jobs_return_the_findings_or_store_the_snapshots(monkeypatch, tmp_path):
    store = motion_store()
    sha = upload(store)['sha256']
    worker_fakes(monkeypatch, store, tmp_path, check_ok=False)
    out = VS.motion_tool(FakeConn([]), store, USER, MRUN, [], {'shot_id': 'MO1', 'op': 'check', 'sha256': sha})
    status, result, error, _, _ = VW.process_motion_tool({'id': 'job-3', 'run_id': 'run-1', 'request': {'kind': 'motion-check', 'request_key': out['request_key']}})
    assert status == 'ready' and result['ok'] is False and result['errors'][0]['code'] == 'motion_appears_late'
    out = VS.motion_tool(FakeConn([]), store, USER, MRUN, [], {'shot_id': 'MO1', 'op': 'snapshot', 'sha256': sha, 'at': [0.5, 2.0]})
    status, result, _, _, _ = VW.process_motion_tool({'id': 'job-4', 'run_id': 'run-1', 'request': {'kind': 'motion-snapshot', 'request_key': out['request_key']}})
    assert status == 'ready' and [s['at'] for s in result['snapshots']] == [0.5, 2.0] and store.files[result['snapshots'][1]['key']] == b'\x89PNG2.0'


# ---------- select, the cap, the run ----------

def test_a_held_motion_drawing_is_selected_only_with_notes():
    store = motion_store()
    job = render_job(store)
    s = saved(store)
    s['take_checks'] = {'job-9': {'must_failed': [{'check': 'frames'}]}}
    s['reviews'] = {'job-9': [{'id': 'r1', 'decision': 'accepted'}]}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    row = {**job, 'status': 'ready', 'result': {'key': 'k', 'sha256': 'x', 'bytes': 1, 'evidence': {'timing_matches_placement': True}}, 'request': {**job['request'], 'preparation_id': 'p'}}
    class One(FakeConn):
        def execute(self, sql, params=()):
            if sql.startswith('select * from vw2_jobs where id'):
                return type('R', (), {'fetchone': lambda _: row, 'fetchall': lambda _: [row]})()
            return super().execute(sql, params)
    with pytest.raises(Problem, match='This drawing is held: frames'):
        g(lambda: VS.select_take(One([]), store, USER, MRUN, [], 'job-9', 'yes'))


def test_the_render_cap_counts_running_drawn_and_motion_jobs():
    class Count:
        def __init__(self, n):
            self.n, self.sql = n, []

        def execute(self, sql, params=()):
            self.sql.append(sql)
            return self

        def fetchone(self):
            return {'n': self.n}
    assert VW.renders_free(Count(1), 2) and not VW.renders_free(Count(2), 2)


def test_a_run_records_its_drawn_route_and_defaults_to_svg():
    assert VS.drawn_route({'id': 'r'}) == 'svg' and VS.drawn_route(MRUN) == 'motion'


def test_the_brief_carries_the_length_the_timed_words_the_labels_the_pictures_and_the_rules():
    out = VS.motion_brief(motion_store(), MRUN, [], 'MO1')
    b = out['brief']
    assert out['refs'] == ['comp-1', 'ST1'] and out['frames'] == 100
    assert 'exactly 100 frames at 25 fps = 4.000 s' in b and 'data-duration="4"' in b and 'solid 0.84' in b
    assert '"Solid brick-on-edge course at sill level"' in b and 'assets/ref/comp-1.png' in b and '"Noto Sans"' in b and 'assets/vendor/gsap.min.js' in b
    with pytest.raises(Problem, match='draws its drawn shots as SVG scenes'):
        g(lambda: VS.motion_brief(motion_store(), RUN, [], 'MO1'))


# ---------- phase 3: the fact-check loop ----------

def verdict(sha, failed=(), n=4):
    return {'shot_id': 'MO1', 'sha256': sha, 'round': 1, 'stranger': ['A brick wall in elevation with a window.'],
            'rules': [{'n': i, 'group': 'truth', 'rule': f'rule {i}', 'pass': i not in failed, 'where': 'left', 'fix': 'add it' if i in failed else ''} for i in range(1, n + 1)]}


def test_a_verdict_is_kept_per_shot_and_its_failed_rules_are_named():
    store = motion_store()
    sha = upload(store)['sha256']
    out = VS.motion_verdict(store, USER, MRUN, [], verdict(sha, failed=(2, 4)))
    assert out['failed'] == ['rule 2', 'rule 4'] and 'redo' in out['next']
    rec = saved(store)['motion_checks']['MO1'][-1]
    assert rec['sha256'] == sha and rec['round'] == 1 and len(rec['rules']) == 4
    clean = VS.motion_verdict(store, USER, MRUN, [], {**verdict(sha), 'round': 2})
    assert clean['failed'] == [] and 'render' in clean['next']
    with pytest.raises(Problem, match='every rule has pass true or false'):
        g(lambda: VS.motion_verdict(store, USER, MRUN, [], {**verdict(sha), 'rules': [{'n': 1, 'rule': 'x'}]}))
    with pytest.raises(Problem, match='no uploaded project'):
        g(lambda: VS.motion_verdict(store, USER, MRUN, [], verdict('c' * 64)))


def test_select_holds_a_motion_drawing_without_a_clean_fact_check_of_its_project():
    store = motion_store()
    job = render_job(store)
    sha = json.loads(store.files[saved(store)['preparations']['MO1']['key']])['sha256']
    s = saved(store)
    s['reviews'] = {'job-9': [{'id': 'r1', 'decision': 'accepted'}]}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    row = {**job, 'status': 'ready', 'result': {'key': 'k', 'sha256': 'x', 'bytes': 1, 'evidence': {'timing_matches_placement': True}}, 'request': {**job['request'], 'preparation_id': 'p'}}

    class One(FakeConn):
        def execute(self, sql, params=()):
            if sql.startswith('select * from vw2_jobs where id'):
                return type('R', (), {'fetchone': lambda _: row, 'fetchall': lambda _: [row]})()
            return super().execute(sql, params)
    with pytest.raises(Problem, match='no fact check'):
        g(lambda: VS.select_take(One([]), store, USER, MRUN, [], 'job-9', 'yes'))
    VS.motion_verdict(store, USER, MRUN, [], verdict(sha, failed=(3,)))
    with pytest.raises(Problem, match='fact check failed: rule 3'):
        g(lambda: VS.select_take(One([]), store, USER, MRUN, [], 'job-9', 'yes'))
    VS.motion_verdict(store, USER, MRUN, [], {**verdict(sha), 'round': 2})
    out = g(lambda: VS.select_take(One([]), store, USER, MRUN, [], 'job-9', 'yes'))
    assert out['job_id'] == 'job-9'


def test_subject_rules_come_from_the_seed_and_the_operators_additions_and_reach_the_brief():
    store = motion_store()
    assert 'rat-trap-bond' in VS.subject_rule_files()
    out = VS.add_subject_rule(store, USER, MRUN, 'rat-trap-bond', 'A window opening has a lintel bearing on both sides.', 'yes, add it')
    assert out['rules'][-1]['rule'] == 'A window opening has a lintel bearing on both sides.' and out['rules'][-1]['quote'] == 'yes, add it'
    with pytest.raises(Problem, match='no subject rules file'):
        g(lambda: VS.add_subject_rule(store, USER, MRUN, 'pottery', 'x', 'yes'))
    assert 'Subject rules' not in VS.motion_brief(store, MRUN, [], 'MO1')['brief']   # nothing in this plan names the subject
    store2 = motion_store(sh=motion_shot(narration='In rat-trap bond, providing a solid course at sill level improves strength.'))
    store2.files['subject-rules/rat-trap-bond.json'] = store.files['subject-rules/rat-trap-bond.json']
    b = VS.motion_brief(store2, MRUN, [], 'MO1')['brief']
    assert 'Subject rules (rat-trap-bond)' in b and 'bearing on both sides' in b and 'no continuous vertical joint' in b.lower()


def test_snapshot_crops_are_cut_from_each_frame_and_kept(monkeypatch, tmp_path):
    from io import BytesIO
    from PIL import Image
    store = motion_store()
    sha = upload(store)['sha256']
    worker_fakes(monkeypatch, store, tmp_path)

    def snapshot(folder, at, zoom, out_dir):
        paths = []
        for n, t in enumerate(at):
            p = Path(out_dir) / f'{n}.png'
            Image.new('RGB', (1920, 1080), (200, 80, 40)).save(p)
            paths.append(p)
        return paths
    monkeypatch.setattr(M, 'snapshot', snapshot)
    out = VS.motion_tool(FakeConn([]), store, USER, MRUN, [], {'shot_id': 'MO1', 'op': 'snapshot', 'sha256': sha, 'at': [1.0], 'crops': [[0.5, 0.5, 0.25, 0.25]]})
    status, result, _, _, _ = VW.process_motion_tool({'id': 'job-5', 'run_id': 'run-1', 'request': {'kind': 'motion-snapshot', 'request_key': out['request_key']}})
    crop = result['snapshots'][0]['crops'][0]
    assert status == 'ready' and crop['box'] == [0.5, 0.5, 0.25, 0.25]
    with Image.open(BytesIO(store.files[crop['key']])) as im:
        assert im.size == (960, 540)   # 480x270 of the frame, shown at twice the size


def test_take_jobs_never_lists_a_helpers_check_or_snapshot():
    conn = FakeConn([])
    VS.take_jobs(conn, MRUN)
    assert "provider <> 'motion'" in conn.sql[-1][0]


# ---------- SK, 1 Nov: the motion route is the default, and a labelled graphic on a motion film is drawn ----------

def test_a_labelled_graphic_on_a_motion_film_must_be_drawn():
    from fractions import Fraction
    from test_visuals_pure import GAPS, plan, shot as pshot
    REST = [pshot('VS1', 100, 250, 'video'), pshot('VS2', 250, 500, 'video'), pshot('VS3', 500, 750, 'video'), pshot('VS4', 750, 1000, 'video')]   # takes of 10 s at most
    labelled = plan([{**pshot('DG1', 0, 100, 'diagram'), 'carries_text': True}, *REST])
    with pytest.raises(ValueError, match='DG1 is a diagram that carries text: on this film a labelled diagram, chart, map or timeline is drawn with HyperFrames'):
        VC.validate_plan(labelled, GAPS, Fraction(25), labels_drawn=True)
    VC.validate_plan(labelled, GAPS, Fraction(25))   # an SVG film keeps the older rule
    plain = plan([pshot('DG1', 0, 100, 'diagram'), *REST])
    VC.validate_plan(plain, GAPS, Fraction(25), labels_drawn=True)   # a graphic without words may still be painted
    figures = plan([{**pshot('DG1', 0, 100, 'diagram'), 'claims': ['1 brick in 4 is saved']}, *REST])
    with pytest.raises(ValueError, match='scene_motion'):
        VC.validate_plan(figures, GAPS, Fraction(25), labels_drawn=True)


def test_a_new_film_draws_with_hyperframes_unless_it_asks_for_svg():
    import inspect
    from app import core
    from app.main import NewRun
    assert NewRun.model_fields['drawn_route'].default == 'motion'
    assert inspect.signature(core.create_run).parameters['drawn_route'].default == 'motion'
    assert VS.drawn_route({'id': 'r'}) == 'svg'   # a run made before the column read as svg (the older way)
