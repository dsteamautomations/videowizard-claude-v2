"""design/117 P4 (and the server side of P2/P3): the scene upload, the SVG render request, the lines a sheet is read against, the sheet read and the fix
call through Gemini (fakes), the loop in the worker (render, sheet, read, fix, render again; the best pass kept; invalid fixes dropped; no key: unchecked),
the record on the session, and the hold on a drawing whose must lines still fail (SK's answer 1)."""
import contextlib
import copy
import hashlib
import json
import types
from pathlib import Path

import pytest
from pydantic import SecretStr

from app import drawn as D, image_check as IC, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from svg_fixture import ACTIONS, SVG, with_
from test_batch89b_pure import SPEC
from test_visuals_stage_pure import FakeConn, FakeStore, RUN, USER, accepted, g, plan_doc, ref, saved, session, shot, store_with

SHA = hashlib.sha256(SVG.encode('utf-8')).hexdigest()


def svg_store(approved=True, uploaded=True, refs_ok=True):
    sh = {**shot('DR1', 0, 100, 'diagram'), 'visual_type': 'drawn', 'depicts': 'the wall', 'narration': 'The cavity between the two leaves holds still air.',
          'drawing_spec': copy.deepcopy(SPEC), 'scene_svg': {'sha256': SHA, 'actions': copy.deepcopy(ACTIONS)}}
    doc = plan_doc([sh, shot('IM1', 100, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    doc['foundation']['graphic_style'] = {'palette': 'terracotta #B5543A, paper #F4EDE1, charcoal #2F2F2F, saffron #E8902A'}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   spec_approvals={'DR1': {'digest': VS.spec_digest(SPEC)}} if approved else {})
    sess['source']['gaps']['G1'] = {**sess['source']['gaps']['G1'], 'timing': {'words': [{'text': 'The', 'start_frame': 0, 'end_frame': 4}, {'text': 'cavity', 'start_frame': 40, 'end_frame': 50}]}}
    sess['references'] = {'comp-1': {**ref('comp-1', 'approved' if refs_ok else 'candidate'), 'kind': 'component', 'element_id': 'E1'},
                          'ST1': {**ref('ST1', 'approved'), 'kind': 'style', 'element_id': VS.STYLE}}
    store = store_with(sess, doc)
    if uploaded:
        VS.set_scene(store, USER, RUN, [], 'DR1', 'scene.svg', SVG.encode('utf-8'))
    return store


# ---------- the upload and the request ----------

def test_set_scene_stores_the_file_names_its_parts_and_refuses_what_breaks_a_rule():
    store = svg_store(uploaded=False)
    out = VS.set_scene(store, USER, RUN, [], 'DR1', 'scene.svg', SVG.encode('utf-8'))
    assert out['sha256'] == SHA and out['pictures'] == ['comp-1'] and 'Bricks for the same wall' in out['texts'] and 'wall' in out['ids'] and SHA in out['next']
    assert saved(store)['scenes'][SHA]['key'] == f'run-1/visuals/scenes/{SHA}.svg' and store.files[f'run-1/visuals/scenes/{SHA}.svg'] == SVG.encode('utf-8')
    with pytest.raises(Problem, match='one .svg file'):
        g(lambda: VS.set_scene(store, USER, RUN, [], 'DR1', 'scene.txt', SVG.encode('utf-8')))
    with pytest.raises(Problem, match='breaks the rules.*script'):
        g(lambda: VS.set_scene(store, USER, RUN, [], 'DR1', 'scene.svg', with_(old='<path id="arrow"', new='<script>x()</script><path id="arrow"').encode('utf-8')))
    with pytest.raises(Problem, match='candidate, not approved'):
        g(lambda: VS.set_scene(svg_store(uploaded=False, refs_ok=False), USER, RUN, [], 'DR1', 'scene.svg', SVG.encode('utf-8')))


def test_render_drawn_builds_the_svg_request_with_the_pictures_the_style_the_palette_and_the_spec():
    store, conn = svg_store(), FakeConn([])
    out = VS.render_drawn(conn, store, USER, RUN, [], {'shot_id': 'DR1'})
    assert out['job_id'] == 'job-1' and out['frames'] == 100 and 'sheet of every frame' in out['next']
    req = json.loads(store.files[saved(store)['preparations']['DR1']['key']])
    assert req['svg_key'] == f'run-1/visuals/scenes/{SHA}.svg' and req['scene'] == {'sha256': SHA, 'actions': ACTIONS} and req['cues'] == [0.0, 0.5, 2.0, 2.5, 3.0]
    assert req['images'] == {'comp-1': 'run-1/visuals/references/comp-1.png'} and req['style_key'] == 'run-1/visuals/references/ST1.png' and 'terracotta' in req['palette']
    assert req['spec']['dimensions'][0]['part'] == 'leaf' and req['relationships'] == SPEC['relationships'] and req['view'] == 'cutaway' and (req['width'], req['height']) == (1920, 1080)
    again = VS.render_drawn(FakeConn([{'id': 'job-1', 'unit': 'DR1', 'provider': 'drawn', 'status': 'ready', 'request': {'preparation_id': out['preparation_id']}}]), store, USER, RUN, [], {'shot_id': 'DR1'})
    assert again['cached'] and again['job_id'] == 'job-1'
    with pytest.raises(Problem, match='names no uploaded scene'):
        g(lambda: VS.render_drawn(FakeConn([]), svg_store(uploaded=False), USER, RUN, [], {'shot_id': 'DR1'}))
    with pytest.raises(Problem, match='drawing spec of DR1 is not approved'):
        g(lambda: VS.render_drawn(FakeConn([]), svg_store(approved=False), USER, RUN, [], {'shot_id': 'DR1'}))
    with pytest.raises(Problem, match='IM1 is image: `draw` is for a drawn shot'):
        g(lambda: VS.render_drawn(FakeConn([]), store, USER, RUN, [], {'shot_id': 'IM1'}))


# ---------- the read and the fix ----------

def keyed(monkeypatch, key='k', fix_model=None):
    s = types.SimpleNamespace(GEMINI_API_KEY=SecretStr(key), **({'DRAWN_FIX_MODEL': fix_model} if fix_model else {}))
    monkeypatch.setattr(IC, 'settings', lambda: s)


def test_the_asks_and_the_sheet_read(monkeypatch):
    asks = IC.drawn_asks({'claims': ['one course saves a quarter'], 'relationships': ['the two leaves are the same thickness'], 'view': 'cutaway', 'palette': 'terracotta #B5543A'}, ['course pitch 75 mm'])
    checks = [a['check'] for a in asks]
    assert checks[:4] == ['claim: one course saves a quarter', 'relationship: the two leaves are the same thickness', 'label: course pitch 75 mm', 'view: cutaway']
    assert 'text whole' in checks and 'things look like their names' in checks and 'builds step' in checks and 'palette' in checks and 'terracotta #B5543A' in asks[-1]['pass_when']
    calls = []

    class Transport:
        def __init__(self, key, model, **kw):
            Transport.model = model

        def generate(self, payload):
            calls.append(payload)
            return {'body': {'lines': [{'n': 1, 'pass': True, 'seen': 'ok'}, {'n': 2, 'pass': False, 'seen': 'the title is cut at the right edge'}]}, 'raw': ''}
    keyed(monkeypatch)
    lines = asks[:2]
    rec = IC.drawn_sheet_check(b'\xff\xd8sheet', [('the approved style', b'\x89PNG'), ('picture comp-1', b'\x89PNG')], lines, 'cutaway drawing of DR1', Transport)
    assert [l['pass'] for l in rec['lines']] == [True, False] and [l['check'] for l in rec['must_failed']] == [lines[1]['check']] and rec['model'] == IC.CHECK_MODEL
    parts = calls[0]['contents'][0]['parts']
    mimes = [p['inlineData']['mimeType'] for p in parts if 'inlineData' in p]
    assert mimes == ['image/png', 'image/png', 'image/jpeg'] and 'Reference 1 (the approved style)' in parts[0]['text'] and 'contact sheet' in parts[-1]['text']
    keyed(monkeypatch, key='')
    assert IC.drawn_sheet_check(b'\xff\xd8', [], lines, 'x', Transport)['error'] == 'no Gemini key on the server'


def test_the_fix_call_returns_the_corrected_svg_and_what_changed_or_an_error(monkeypatch):
    calls = []

    class Transport:
        def __init__(self, key, model, **kw):
            Transport.model = model

        def generate(self, payload):
            calls.append(payload)
            return {'body': {'svg': '<svg/>', 'changed': 'moved the title inside the frame'}, 'raw': ''}
    keyed(monkeypatch, fix_model='gemini-3.8-pro')
    out = IC.drawn_fix(SVG, b'\xff\xd8', [{'check': 'text whole', 'seen': 'cut at the right'}], 'the rules', Transport)
    assert out == {'svg': '<svg/>', 'changed': 'moved the title inside the frame', 'key_index': 0, 'model': 'gemini-3.8-pro'} and Transport.model == 'gemini-3.8-pro'
    text = calls[0]['contents'][0]['parts'][-1]['text']
    assert 'text whole: cut at the right' in text and 'the rules' in text and SVG in text and calls[0]['generationConfig']['responseJsonSchema'] == IC.FIX_SCHEMA

    class Broken(Transport):
        def generate(self, payload):
            raise RuntimeError('boom')
    assert 'RuntimeError' in IC.drawn_fix(SVG, b'', [], '', Broken)['error']
    keyed(monkeypatch, key='')
    assert IC.drawn_fix(SVG, b'', [], '', Transport)['error'] == 'no Gemini key on the server'


# ---------- the loop ----------

def loop_store(svg=SVG):
    req = {'kind': 'drawn', 'shot_id': 'DR1', 'scene': {'sha256': SHA, 'actions': ACTIONS}, 'svg_key': 'run-1/visuals/scenes/s.svg', 'width': 640, 'height': 360, 'fps': '24', 'frames': 12,
           'cues': [0.0, 0.0, 0.25, 0.3, 0.4], 'images': {'comp-1': 'run-1/visuals/references/comp-1.png'}, 'style_key': 'run-1/visuals/references/ST1.png', 'palette': 'terracotta',
           'claims': [], 'relationships': [], 'view': None, 'spec': {'dimensions': []},
           'placement': {'start_frame': 0, 'end_frame': 12, 'film_fps': '24', 'duration_seconds': '1/2', 'exact_seconds': 0.5}}
    return FakeStore({'run-1/visuals/takes/p1.drawn.json': req, 'run-1/visuals/scenes/s.svg': svg.encode('utf-8'), 'run-1/visuals/references/comp-1.png': b'\x89PNG', 'run-1/visuals/references/ST1.png': b'\x89PNG'})


def fakes(monkeypatch, store, tmp_path, reads, fix=None, render_fail_first=False):
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(D, 'measure', lambda *a, **k: [])
    calls = {'render': [], 'fix': [], 'reset': 0}

    def render(request, out_path, svg, images, fonts, keep=None):
        calls['render'].append(svg)
        if render_fail_first and len(calls['render']) == 1:
            raise RuntimeError('browser gone')
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b'MP4' + str(len(calls['render'])).encode())
        return {'frames': 12, 'digest': 'x', 'kept': {0: b'\x89PNG0', 11: b'\x89PNG11'}}
    monkeypatch.setattr(D, 'render', render)
    monkeypatch.setattr(D, 'reset', lambda: calls.__setitem__('reset', calls['reset'] + 1))
    monkeypatch.setattr(D, 'sheet', lambda frames, fps, W, H, **k: b'\xff\xd8sheet' + str(len(calls['render'])).encode())
    monkeypatch.setattr(VW, 'probe', lambda path: {'duration_seconds': 0.5, 'width': 640, 'height': 360, 'issues': []})
    it = iter(reads)
    monkeypatch.setattr(IC, 'drawn_sheet_check', lambda sheet, pictures, lines, prompt, tf: calls.setdefault('reads', []).append((sheet, [p[0] for p in pictures], [l['check'] for l in lines])) or next(it))
    monkeypatch.setattr(IC, 'drawn_fix', lambda svg, sheet, failed, rules, tf: calls['fix'].append(failed) or (fix or {'error': 'no fix'}))
    return calls


JOB = {'id': 'j1', 'run_id': 'run-1', 'request': {'request_key': 'run-1/visuals/takes/p1.drawn.json', 'preparation_id': 'p1'}}
FAIL = {'lines': [{'check': 'text whole', 'weight': 'must', 'pass': False, 'seen': 'cut'}], 'must_failed': [{'check': 'text whole', 'weight': 'must', 'pass': False, 'seen': 'cut'}], 'model': 'm'}
PASS = {'lines': [{'check': 'text whole', 'weight': 'must', 'pass': True, 'seen': 'whole'}], 'must_failed': [], 'model': 'm'}


def test_the_loop_renders_reads_fixes_and_renders_again_and_keeps_the_best_pass(monkeypatch, tmp_path):
    store = loop_store()
    fixed = with_(old='x="800" y="130"', new='x="800" y="140"')
    calls = fakes(monkeypatch, store, tmp_path, [FAIL, PASS], fix={'svg': fixed, 'changed': 'moved the title down'})
    status, result, error, cost, retry = VW.process_drawn(JOB)
    assert status == 'ready', error
    assert calls['render'] == [SVG, fixed] and calls['fix'] == [FAIL['must_failed']] and cost == {'provider': 'drawn', 'seconds': 0.5, 'inr': 0}
    assert calls['reads'][0][1] == ['the approved style', 'picture comp-1'] and 'label: Bricks for the same wall' in calls['reads'][0][2] and 'palette' in calls['reads'][0][2]
    ch = result['check']
    assert ch['best_pass'] == 2 and ch['must_failed'] == [] and [p['pass'] for p in ch['passes']] == [1, 2] and ch['passes'][0]['changed'] == 'moved the title down' and ch['passes'][0]['failed'] == ['text whole']
    assert result['key'] == 'run-1/visuals/drawn/j1.mp4' and store.files[result['key']] == b'MP42' and result['sheet_key'] == 'run-1/visuals/drawn/j1-sheet-2.jpg'
    assert store.files['run-1/visuals/drawn/j1-sheet-1.jpg'] == b'\xff\xd8sheet1' and store.files['run-1/visuals/drawn/j1-fixed.svg'] == fixed.encode('utf-8') and result['fixed_svg_key'].endswith('j1-fixed.svg')
    assert [c['check'] for c in result['code']] == ['frames', 'size'] and result['evidence']['timing_matches_placement'] is True


def test_an_invalid_fix_is_dropped_and_the_first_pass_stands_with_its_failures(monkeypatch, tmp_path):
    store = loop_store()
    calls = fakes(monkeypatch, store, tmp_path, [FAIL, PASS], fix={'svg': with_(old='<path id="arrow"', new='<script>x()</script><path id="arrow"'), 'changed': 'x'})
    status, result, error, _, _ = VW.process_drawn(JOB)
    assert status == 'ready' and len(calls['render']) == 1 and result['check']['best_pass'] == 1 and [l['check'] for l in result['check']['must_failed']] == ['text whole']
    assert 'script' in ' '.join(result['check']['passes'][0]['fix_dropped']) and result['fixed_svg_key'] is None


def test_three_passes_at_most_and_the_pass_with_the_fewest_failures_is_kept(monkeypatch, tmp_path):
    store = loop_store()
    two = {**FAIL, 'must_failed': FAIL['must_failed'] + [{'check': 'palette', 'weight': 'must', 'pass': False, 'seen': 'green'}]}
    calls = fakes(monkeypatch, store, tmp_path, [two, FAIL, two], fix={'svg': with_(old='y="130"', new='y="140"'), 'changed': 'nudged'})
    status, result, error, _, _ = VW.process_drawn(JOB)
    assert status == 'ready' and len(calls['render']) == 3 and len(calls['fix']) == 2 and result['check']['best_pass'] == 2 and len(result['check']['must_failed']) == 1
    assert store.files[result['key']] == b'MP42' and result['sheet_key'].endswith('-sheet-2.jpg')


def test_the_rules_refuse_before_any_render_and_no_key_leaves_the_drawing_unchecked(monkeypatch, tmp_path):
    bad = loop_store(svg=with_(old='<path id="arrow"', new='<foreignObject/><path id="arrow"'))
    calls = fakes(monkeypatch, bad, tmp_path, [PASS])
    status, result, error, _, _ = VW.process_drawn(JOB)
    assert status == 'failed' and 'cannot be rendered' in error and 'foreignObject' in error and calls['render'] == []
    store = loop_store()
    calls = fakes(monkeypatch, store, tmp_path / 'b', [{'lines': [], 'must_failed': [], 'model': 'm', 'error': 'no Gemini key on the server'}])
    status, result, error, _, _ = VW.process_drawn(JOB)
    assert status == 'ready' and result['check']['error'] == 'no Gemini key on the server' and len(calls['render']) == 1 and calls['fix'] == [] and result['check']['must_failed'] == []


def test_a_crashed_browser_is_started_again_once_and_a_text_outside_the_safe_area_fails_the_render(monkeypatch, tmp_path):
    store = loop_store()
    calls = fakes(monkeypatch, store, tmp_path, [PASS], render_fail_first=True)
    status, result, error, _, _ = VW.process_drawn(JOB)
    assert status == 'ready' and calls['reset'] == 1 and len(calls['render']) == 2
    monkeypatch.setattr(D, 'measure', lambda *a, **k: [{'id': 'title', 'text': 'Bricks for the same wall', 'x': 600, 'y': 20, 'w': 100, 'h': 30}])
    status, result, error, _, _ = VW.process_drawn(JOB)
    assert status == 'failed' and 'leaves the safe area' in error and 'Bricks for the same wall' in error


def test_check_drawn_keeps_the_loops_record_on_the_session(monkeypatch):
    store = FakeStore({'run-1/visuals/session.json': {'take_checks': {}}})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'connect', lambda: contextlib.nullcontext(FakeConn([])))
    check = {'lines': [{'check': 'frames', 'pass': True}], 'must_failed': [], 'best_pass': 1, 'sheet_key': 'k', 'passes': [{'pass': 1, 'failed': []}]}
    VW.check_drawn(JOB, {'check': check, 'code': []})
    assert json.loads(store.files['run-1/visuals/session.json'])['take_checks']['j1'] == check


# ---------- the hold ----------

def test_a_drawing_whose_must_lines_still_fail_is_held_until_the_operator_says_why():
    store = svg_store()
    out = VS.render_drawn(FakeConn([]), store, USER, RUN, [], {'shot_id': 'DR1'})
    prep = saved(store)['preparations']['DR1']
    job = {'id': 'j-drawn-1', 'unit': 'DR1', 'run_id': 'run-1', 'provider': 'drawn', 'status': 'ready', 'error': None,
           'request': {'kind': 'drawn', 'request_key': prep['key'], 'preparation_id': out['preparation_id']},
           'result': {'key': 'run-1/visuals/drawn/j-drawn-1.mp4', 'sha256': 'd' * 64, 'bytes': 9, 'evidence': {'duration_seconds': 4.0, 'timing_matches_placement': True, 'issues': []}}}

    class Conn(FakeConn):
        def execute(self, sql, params=()):
            if 'from vw2_jobs where id=' in sql:
                class R:
                    def fetchone(_):
                        return job
                return R()
            return super().execute(sql, params)
    s = saved(store)
    s['take_checks'] = {'j-drawn-1': {'lines': [], 'must_failed': [{'check': 'text whole', 'pass': False}, {'check': 'palette', 'pass': False}], 'best_pass': 3}}
    s['reviews'] = {'j-drawn-1': [{'id': 'r1', 'decision': 'accepted', 'notes': '', 'quote': 'ok', 'by': 'u1'}]}   # accepted on the page, no reason given
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    with pytest.raises(Problem, match='held: text whole, palette still failed'):
        g(lambda: VS.select_take(Conn([]), store, USER, RUN, [], 'j-drawn-1', 'take it'))
    sel = VS.select_take(Conn([]), store, USER, RUN, [], 'j-drawn-1', 'take it', notes='the title is whole on the final frame; the palette line misread the gradient')
    assert sel['job_id'] == 'j-drawn-1' and saved(store)['reviews']['j-drawn-1'][-1]['notes'].startswith('the title is whole')   # the reason is kept with the selection
