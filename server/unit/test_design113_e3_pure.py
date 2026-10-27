"""design/113 E3: a rendered drawing is reviewed like a take: the code lines and one Gemini read of the first and last frame against the claims, the
relationships and the labels; approve (select) or reject with words; a selection needs the plan the drawing was rendered from."""
import contextlib
import json
from pathlib import Path

import pytest

from app import image_check as IC, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from test_design113_e2_pure import drawn_store
from test_visuals_stage_pure import RUN, USER, FakeConn, FakeStore, g, saved

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def rendered(store):
    """The drawn job as the worker leaves it, on a connection that answers the job queries."""
    out = VS.render_drawn(FakeConn([]), store, USER, RUN, [], {'shot_id': 'DR1'})
    prep = saved(store)['preparations']['DR1']
    job = {'id': 'j-drawn-1', 'unit': 'DR1', 'run_id': 'run-1', 'provider': 'drawn', 'status': 'ready', 'error': None, 'cost': {'provider': 'drawn', 'seconds': 4.0, 'inr': 0},
           'request': {'kind': 'drawn', 'request_key': prep['key'], 'preparation_id': out['preparation_id'], 'duration_seconds': 4.0},
           'result': {'key': 'run-1/visuals/drawn/j-drawn-1.mp4', 'sha256': 'd' * 64, 'bytes': 9, 'evidence': {'duration_seconds': 4.0, 'timing_matches_placement': True, 'issues': []},
                      'code': [{'check': 'frames', 'weight': 'must', 'pass': True, 'seen': '4.000 s'}]}}

    class Conn(FakeConn):
        def execute(self, sql, params=()):
            if 'from vw2_jobs where id=' in sql:
                class R:
                    def fetchone(_):
                        return job
                return R()
            return super().execute(sql, params)
    return job, Conn([job])


def test_a_drawing_is_rejected_with_words_or_selected_and_the_selection_needs_the_plan_it_was_rendered_from():
    store = drawn_store()
    job, conn = rendered(store)
    review = VS.review_take(conn, store, USER, RUN, [], 'j-drawn-1', 'rejected', 'the cavity label hides the arrow', '', 'No, move the label.')
    assert review['decision'] == 'rejected' and saved(store)['feedback'][-1]['kind'] == 'take' and saved(store)['feedback'][-1]['what_went_wrong'] == 'the cavity label hides the arrow'
    sel = VS.select_take(conn, store, USER, RUN, [], 'j-drawn-1', 'Yes, the section reads.', notes='the leaves and the cavity are right')
    assert sel['job_id'] == 'j-drawn-1' and saved(store)['selections']['DR1']['take']['key'] == 'run-1/visuals/drawn/j-drawn-1.mp4' and 'in the film at' in sel['next']
    req = json.loads(store.files[saved(store)['preparations']['DR1']['key']])
    assert req['claims'] == [] and req['relationships'] == ['the two leaves are the same thickness', 'the cavity is inside the wall'] and req['view'] == 'cutaway'
    req['plan_digest'] = 'another plan'
    store.files[saved(store)['preparations']['DR1']['key']] = json.dumps(req).encode('utf-8')
    with pytest.raises(Problem, match='The plan changed since this drawing was rendered'):
        g(lambda: VS.select_take(conn, store, USER, RUN, [], 'j-drawn-1', 'Yes.', notes='again'))


def test_the_check_reads_the_first_and_last_frame_against_the_claims_relationships_and_labels(monkeypatch):
    calls = []

    class Transport:
        def __init__(self, key, model, **kw):
            Transport.model = model

        def generate(self, payload):
            calls.append(payload)
            return {'body': {'lines': [{'n': 1, 'pass': True, 'seen': 'two equal leaves'}, {'n': 2, 'pass': False, 'seen': 'the label reads 100 mm'}]}, 'raw': ''}
    monkeypatch.setattr(IC, 'settings', lambda: __import__('types').SimpleNamespace(GEMINI_API_KEY=__import__('types').SimpleNamespace(get_secret_value=lambda: 'k')))
    lines = [{'check': 'relationship: the two leaves are the same thickness', 'pass_when': 'in the drawing, the two leaves are the same thickness', 'weight': 'must'},
             {'check': 'label: leaf thickness 110 mm', 'pass_when': 'the label reads exactly "leaf thickness 110 mm"', 'weight': 'must'}]
    rec = IC.drawn_lines_check(b'first', b'last', lines, 'a wall section', Transport)
    assert rec['model'] == IC.CHECK_MODEL and [l['pass'] for l in rec['lines']] == [True, False] and [l['check'] for l in rec['must_failed']] == ['label: leaf thickness 110 mm']
    texts = ' '.join(p.get('text', '') for p in calls[0]['contents'][0]['parts'])
    assert 'Reference 1 (first frame)' in texts and 'The candidate picture' in texts and 'relationship:' in texts
    assert IC.drawn_lines_check(b'first', b'last', [], 'x', Transport)['lines'] == [] and len(calls) == 1   # nothing to ask: no call
    monkeypatch.setattr(IC, 'settings', lambda: __import__('types').SimpleNamespace(GEMINI_API_KEY=__import__('types').SimpleNamespace(get_secret_value=lambda: '')))
    assert IC.drawn_lines_check(b'first', b'last', lines, 'x', Transport)['error'] == 'no Gemini key on the server'


def test_the_worker_assembles_the_drawings_lines_from_the_request_and_keeps_them_on_the_session(monkeypatch):
    store = drawn_store()
    job, conn = rendered(store)
    store.files['run-1/visuals/drawn/j-drawn-1-first.png'] = b'first'
    store.files['run-1/visuals/drawn/j-drawn-1-last.png'] = b'last'
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'connect', lambda: contextlib.nullcontext(conn))
    asked = {}
    monkeypatch.setattr(IC, 'drawn_lines_check', lambda first, last, lines, prompt, tf: asked.update(lines=lines, first=first, last=last) or
                        {'lines': [{**l, 'pass': True, 'seen': 'ok'} for l in lines], 'must_failed': [], 'model': IC.CHECK_MODEL})
    VW.check_drawn(job, {**job['result'], 'first_png_key': 'run-1/visuals/drawn/j-drawn-1-first.png', 'last_png_key': 'run-1/visuals/drawn/j-drawn-1-last.png'})
    rec = saved(store)['take_checks']['j-drawn-1']
    checks = [l['check'] for l in rec['lines']]
    assert checks[0] == 'frames' and 'relationship: the cavity is inside the wall' in checks and 'label: leaf thickness 110 mm' in checks and 'label: Rat-trap bond, section' in checks and 'view: cutaway' in checks
    assert asked['first'] == b'first' and asked['last'] == b'last' and rec['must_failed'] == [] and rec['model'] == IC.CHECK_MODEL


def test_the_page_lists_drawn_shots_on_the_takes_step():
    assert "['video','drawn'].includes(s.route)" in PAGE and "s.route==='drawn'?'Drawn'" in PAGE and 'watch the drawing' in PAGE
