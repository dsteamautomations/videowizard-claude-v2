"""design/62: the review page. Row cues from the saved render plan, the page's data from the stage-2 session, the template, and the
rule that every page path a template calls has a route (the audio route was lost in the 0.20.0 cleanup and nothing caught it).
design/127: the rows are scenes (headers), shots (1.1) and alternatives (1.2A1)."""
import json
import re
from pathlib import Path

import pytest

from app.stage2 import stage as S
from app.errors import Problem

APP = Path(__file__).resolve().parents[1] / 'app'
FPS = 25


# ---------- row cues ----------

def plan(items):
    return {'kind': 'review', 'items': items, 'version': 1, 'digest': 'd1'}


def test_slide_cues_give_each_row_its_start_and_end_and_a_scene_runs_to_its_last_piece():
    items = [{'kind': 'slate', 'slide': '1', 'lines': ['Scene 1', 'The need']},            # 75 frames (the slate default)
             {'kind': 'narration', 'start_s': 0, 'end_s': 10},                            # no screen time
             {'kind': 'card', 'frames': 50, 'slide': '1.1', 'lines': ['Scene 1 · Shot 1 · made with AI']},
             {'kind': 'event', 'sub_clip_id': 'x', 'timeline_frames': 100, 'slide': '1.2'},
             {'kind': 'slate', 'frames': 75, 'slide': '1.2A1', 'lines': ['Scene 1 · Shot 2 · Alternative 1']},
             {'kind': 'narration', 'start_s': 5, 'end_s': 9},
             {'kind': 'event', 'sub_clip_id': 'c', 'timeline_frames': 100, 'slide': '1.2A1'},
             {'kind': 'slate', 'slide': '2', 'lines': ['Scene 2']},
             {'kind': 'event', 'sub_clip_id': 'd', 'timeline_frames': 500, 'slide': '2.1'}]
    cues = S.slide_cues(plan(items), FPS)
    assert cues == {'1': [0.0, 16.0], '1.1': [3.0, 5.0], '1.2': [5.0, 9.0], '1.2A1': [9.0, 16.0], '2': [16.0, 39.0], '2.1': [19.0, 39.0]}


def test_slide_cues_tolerate_an_empty_or_strange_plan():
    assert S.slide_cues({}, FPS) == {} and S.slide_cues(plan([{'kind': 'narration'}, {'kind': 'event', 'timeline_frames': 10}]), FPS) == {}
    assert S.slide_cues(plan([{'kind': 'slate', 'lines': []}, {'kind': 'slate', 'slide': '3', 'lines': ['Scene 3']}]), FPS) == {'3': [3.0, 6.0]}


# ---------- the page's data ----------

class FakeStore:
    def __init__(self, files):
        self.files = {k: json.dumps(v).encode('utf-8') for k, v in files.items()}

    def get(self, key):
        if key not in self.files:
            raise Problem(404, 'FILE_MISSING', key)
        return self.files[key]

    def exists(self, key):
        return key in self.files

    def put(self, key, data, mime=None):
        self.files[key] = data
        return {'key': key, 'sha256': 'x', 'bytes': len(data)}


class FakeConn:
    def __init__(self, jobs):
        self.jobs = jobs

    def execute(self, sql, params=()):
        conn = self

        class R:
            def fetchone(_):
                return conn.jobs.get(params[0]) if params else None
        return R()


RUN = {'id': 'run-1', 'code': 'VW-9'}
ONE = {'number': 1, 'scheme': 3, 'beat_id': 'BEAT_01', 'option_number': 1, 'colour': '#1D9E75', 'scene': 'Scene 1: The need'}
TWO = {'number': 2, 'scheme': 3, 'beat_id': 'BEAT_02', 'option_number': 2, 'colour': '#7F77DD', 'scene': 'Scene 2: Mixing'}
SLIDES = [{**ONE, 'no': '1', 'type': 'scene', 'title': 'Scene 1', 'frames': 685, 'lines': ['Scene 1', 'The need', 'Total time: 27.4 s', 'Shots: 2 (footage)']},
          {**ONE, 'no': '1.1', 'type': 'shot', 'title': 'Scene 1 · Shot 1', 'event_index': 0, 'frames': 300, 'clip': 'a drone', 'b_roll': False, 'words': 'The need',
           'note': {'kind': 'check_by_eye', 'question': 'Keep the drone shot?'}, 'lines': ['Scene 1 · Shot 1', 'a drone', 'Time: 12.0 s', '"The need"']},
          {**ONE, 'no': '1.2', 'type': 'shot', 'title': 'Scene 1 · Shot 2', 'event_index': 1, 'frames': 385, 'clip': 'workers', 'b_roll': True, 'words': 'is real',
           'note': None, 'lines': ['Scene 1 · Shot 2 · B-roll', 'workers', 'Time: 15.4 s']},
          {**ONE, 'no': '1.2A1', 'type': 'alternative', 'title': 'Scene 1 · Shot 2 · Alternative 1', 'of': '1.2', 'alt_index': 0, 'event_index': 1, 'frames': 385,
           'clip': 'bricks', 'lines': ['Scene 1 · Shot 2 · Alternative 1']},
          {**ONE, 'no': '1.2A2', 'type': 'alternative', 'title': 'Scene 1 · Shot 2 · Alternative 2', 'of': '1.2', 'alt_index': 1, 'event_index': 1, 'frames': 385,
           'clip': 'site', 'lines': ['Scene 1 · Shot 2 · Alternative 2']},
          {**TWO, 'no': '2', 'type': 'scene', 'title': 'Scene 2', 'frames': 300, 'lines': ['Scene 2', 'Mixing', 'Total time: 12.0 s', 'Shots: 2 (1 made with AI, 1 footage)']},
          {**TWO, 'no': '2.1', 'type': 'shot', 'title': 'Scene 2 · Shot 1', 'event_index': 0, 'frames': 200, 'clip': 'mixer', 'b_roll': False, 'note': None, 'lines': ['Scene 2 · Shot 1']},
          {**TWO, 'no': '2.2', 'type': 'ai', 'title': 'Scene 2 · Shot 2', 'event_index': 1, 'frames': 100, 'intent': 'diagram', 'lines': ['Scene 2 · Shot 2 · made with AI']}]


def session(**over):
    base = {'contract': 'vw2-stage2-session-v1', 'package': {'key': 'p', 'digest': 'pk1', 'narration_key': 'n'}, 'versions': [{'version': 1, 'digest': 'd1', 'file': {'key': 'run-1/stage2/options-v1.json'}, 'slides': SLIDES, 'options': 2, 'gaps': [], 'flags': []}],
            'current': 'd1', 'accepted': None, 'frames': {}, 'inspections': {}, 'renders': {}, 'decisions': {}, 'extra_rules': [], 'master': None, 'recorded': {}}
    return {**base, **over}


def files(sess, with_plan=True):
    f = {'run-1/stage2/session.json': sess, 'run-1/stage2/options-v1.json': {'document': {'options': []}, 'package_digest': 'pk1'}}
    if with_plan:
        f['run-1/stage2/render-review-v1.json'] = plan([{'kind': 'slate', 'slide': '1', 'lines': SLIDES[0]['lines']}, {'kind': 'event', 'timeline_frames': 100, 'slide': '1.1'},
                                                        {'kind': 'slate', 'slide': '1.2A1', 'lines': SLIDES[3]['lines']}])
    return f


def kept(action='KEEP', **extra):
    return {'action': action, 'note': '', 'by': 'u1', 'at': '2026-10-21T10:00:00Z', **extra}


def test_review_view_before_a_film_says_the_render_state_and_lists_the_rows_with_lines():
    sess = session(renders={'review': {'job_id': 'j1', 'status': 'queued', 'digest': 'd1', 'version': 1}})
    view = S.review_view(FakeConn({'j1': {'status': 'running', 'result': None, 'error': None}}), FakeStore(files(sess, with_plan=False)), RUN)
    assert view['state'] == 'prepared' and view['version'] == 1 and view['film'] is None and view['cues'] == {}
    assert view['render'] == {'status': 'running', 'error': None, 'current': True} and view['accepted'] is False
    assert [s['slide'] for s in view['slides']] == ['1', '1.1', '1.2', '1.2A1', '1.2A2', '2', '2.1', '2.2']
    by = {s['slide']: s for s in view['slides']}
    assert by['1']['lines'] == SLIDES[0]['lines'] and by['1']['seconds'] == 27.4 and by['1']['answerable'] is False and by['1']['colour'] == '#1D9E75'
    assert by['1.1']['note'] == {'kind': 'check_by_eye', 'question': 'Keep the drone shot?'} and by['1.1']['words'] == 'The need' and by['1.2']['b_roll'] is True
    assert by['1.2A1']['why'] == 'answer Scene 1 · Shot 2 first' and by['2.2']['needs_answer'] is False and by['2.2']['answerable'] is False
    assert view['answered'] == 0 and view['of'] == 3 and view['waiting'] == ['1.1', '1.2', '2.1']


def test_review_view_with_the_film_ready_carries_the_key_the_cues_and_the_answers():
    sess = session(renders={'review': {'job_id': 'j1', 'status': 'queued', 'digest': 'd1', 'version': 1}}, accepted={'version': 1, 'digest': 'd1', 'quote': 'yes', 'output': 'o1'},
                   recorded={'options': 'o1'}, decisions={'1.1': {'action': 'KEEP', 'type': 'shot', 'note': '', 'by': 'u1', 'at': '2026-10-21T10:00:00Z'},
                                                           '1.2': {'action': 'REJECT', 'type': 'shot', 'note': '', 'by': 'u1', 'at': '2026-10-21T10:01:00Z'}})
    ready = {'status': 'ready', 'result': {'key': 'run-1/stage2/review-v1-d1.mp4', 'sha256': 's', 'bytes': 10, 'duration_s': 426.0}, 'error': None}
    view = S.review_view(FakeConn({'j1': ready}), FakeStore(files(sess)), RUN)
    assert view['film'] == {'key': 'run-1/stage2/review-v1-d1.mp4', 'duration_s': 426.0, 'sha256': 's'}
    assert view['cues'] == {'1': [0.0, 10.0], '1.1': [3.0, 7.0], '1.2A1': [7.0, 10.0]}
    assert view['accepted'] is True and view['render']['status'] == 'ready'
    by = {s['slide']: s for s in view['slides']}
    assert by['1.1']['answer'] == {'action': 'KEEP', 'note': '', 'edit': None, 'by': 'u1', 'at': '2026-10-21T10:00:00Z'} and by['1.2']['answer']['action'] == 'REJECT'
    assert by['1.2A1']['needs_answer'] is True   # its shot is rejected: the alternatives open
    assert view['answered'] == 2 and view['of'] == 5 and view['waiting'] == ['1.2A1', '1.2A2', '2.1']


def test_review_view_without_a_session_or_a_version_says_so():
    assert S.review_view(FakeConn({}), FakeStore({}), RUN) == {'state': 'not_prepared'}
    assert S.review_view(FakeConn({}), FakeStore(files(session(current=None))), RUN) == {'state': 'no_version'}


def test_a_film_of_another_version_is_not_offered():
    sess = session(renders={'review': {'job_id': 'j1', 'status': 'ready', 'digest': 'OLD', 'version': 1, 'result': {'key': 'k', 'sha256': 's', 'bytes': 1}}})
    view = S.review_view(FakeConn({'j1': {'status': 'ready', 'result': {'key': 'k', 'sha256': 's', 'bytes': 1}, 'error': None}}), FakeStore(files(sess)), RUN)
    assert view['film'] is None and view['render'] == {'status': 'ready', 'error': None, 'current': False}


def test_slides_view_rows_carry_the_lines_for_the_chat_questions():
    """design/62 A: the assistant asks each shot with its own lines, so the slides endpoint carries them."""
    view = S.slides_view(FakeStore(files(session(), with_plan=False)), RUN)
    assert view['slides'][1]['lines'] == SLIDES[1]['lines'] and view['of'] == 3


# ---------- design/127: one alternative of a shot ----------

def test_keeping_one_alternative_switches_the_others_off():
    sess = session(accepted={'version': 1, 'digest': 'd1'}, decisions={'1.2': kept('REJECT')})
    store = FakeStore(files(sess, with_plan=False))
    assert S.decide(FakeConn({}), store, {'id': 'u1'}, RUN, '1.2a1', 'keep', '', None)['action'] == 'KEEP'
    with pytest.raises(Problem, match=r'Scene 1 · Shot 2 · Alternative 1 is kept: the other alternatives are off'):
        S.decide(FakeConn({}), store, {'id': 'u1'}, RUN, '1.2A2', 'KEEP', '', None)
    assert S.missing_answers(SLIDES, {'1.1': kept(), '1.2': kept('REJECT'), '1.2A1': kept(), '2.1': kept()}) == []
    assert S.decide(FakeConn({}), store, {'id': 'u1'}, RUN, '1.2A1', 'REJECT', '', None)['action'] == 'REJECT'   # changed: Alternative 2 opens again
    assert S.decide(FakeConn({}), store, {'id': 'u1'}, RUN, '1.2A2', 'KEEP', '', None)['action'] == 'KEEP'


def test_missing_answers_open_the_alternatives_only_after_a_reject():
    assert S.missing_answers(SLIDES, {}) == ['1.1', '1.2', '2.1']
    assert S.missing_answers(SLIDES, {'1.1': kept(), '1.2': kept('REJECT'), '2.1': kept()}) == ['1.2A1', '1.2A2']
    assert S.missing_answers(SLIDES, {'1.1': kept(), '1.2': kept('TRIM'), '2.1': kept()}) == []


# ---------- the template and the routes ----------

def test_the_review_template_renders_in_every_state():
    """Rendered with a plain Jinja environment: the web module imports the auth module, whose 3.10 annotations this Python cannot load."""
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(APP / 'templates')), autoescape=True)
    env.globals['version'] = 't'
    html = env.get_template('review.html').render(user={'name': 'SK', 'role': 'Admin'}, run={'code': 'VW-9', 'title': 'Film'})
    for needed in ('id="app"', 'data-code="VW-9"', 'id="film"', 'id="slides"', 'id="fmsg"', "'/runs/'+code+'/review'", 'KEEP', 'REJECT', 'TRIM', 'old_form'):
        assert needed in html, needed


def test_every_page_path_a_template_calls_has_a_route():
    """The 0.20.0 cleanup removed /runs/<code>/audio/<key> while voices2.html still played from it; this reads the routes from the source."""
    source = (APP / 'web.py').read_text(encoding='utf-8')
    served = set(re.findall(r"@router\.(?:get|post)\('/runs/\{code\}/([a-z0-9-]+)", source))
    wanted = set()
    for t in (APP / 'templates').glob('*.html'):
        text = t.read_text(encoding='utf-8')
        wanted |= set(re.findall(r"/runs/\$\{code\}/([a-z0-9-]+)", text)) | set(re.findall(r"'/runs/'\s*\+\s*code\s*\+\s*'/([a-z0-9-]+)", text))
        wanted |= set(re.findall(r'/runs/\{\{ run\.code \}\}/([a-z0-9-]+)', text))
    assert wanted and wanted <= served, sorted(wanted - served)


def test_the_page_routes_import_the_stage_module_not_the_package():
    """The first deploy of the page answered 500: `from . import stage2` is the package, which exports nothing; the stage logic is stage2.stage."""
    source = (APP / 'web.py').read_text(encoding='utf-8')
    assert 'from . import stage2' not in source and source.count('from .stage2 import stage as stage2') >= 2
    from app import stage2 as pkg
    assert not hasattr(pkg, 'review_view') and hasattr(S, 'review_view') and hasattr(S, 'record_options') and hasattr(S, 'decide')


def test_the_template_shows_the_reason():
    html = (APP / 'templates' / 'review.html').read_text(encoding='utf-8')
    assert 's.why' in html and 'conflict' not in html   # design/127: two kept alternatives cannot happen


# ---------- design/63 addendum: what a page load and a click cost ----------

class CountingStore(FakeStore):
    def __init__(self, files):
        super().__init__(files)
        self.gets, self.puts = [], []

    def get(self, key):
        self.gets.append(key)
        return super().get(key)

    def put(self, key, data, mime=None):
        self.puts.append(key)
        return super().put(key, data, mime)


def test_a_page_load_reads_the_session_once_writes_nothing_and_skips_the_version_document():
    S._CUES.clear()
    sess = session(renders={'review': {'job_id': 'j1', 'status': 'queued', 'digest': 'd1', 'version': 1}})
    ready = {'status': 'ready', 'result': {'key': 'k.mp4', 'sha256': 's', 'bytes': 10, 'duration_s': 426.0}, 'error': None}
    store = CountingStore(files(sess))
    view = S.review_view(FakeConn({'j1': ready}), store, RUN)
    assert view['film'] and view['cues']['1.1'] == [3.0, 7.0]
    assert store.puts == [] and store.gets == ['run-1/stage2/session.json', 'run-1/stage2/render-review-v1.json']   # no document, no write
    store.gets.clear()
    S.review_view(FakeConn({'j1': ready}), store, RUN)
    assert store.gets == ['run-1/stage2/session.json']   # the cues of a rendered version are kept in memory


def test_a_version_without_stored_slides_is_refused():
    """design/125: cuts proposed without stored slides (before design/21) are retired; design/127: the page says so instead of failing."""
    sess = session()
    del sess['versions'][0]['slides']
    view = S.review_view(FakeConn({}), CountingStore(files(sess, with_plan=False)), RUN)
    assert view['state'] == 'old_form' and 'no stored slides' in view['message']
    with pytest.raises(Problem, match='no stored slides'):
        S.slides_view(CountingStore(files(sess, with_plan=False)), RUN)


def test_the_page_draws_from_the_act_reply_without_a_second_request():
    html = (APP / 'templates' / 'review.html').read_text(encoding='utf-8')
    assert 'j.view' in html and 'will-change:transform' in html


def test_the_visuals_template_renders_with_its_hooks():
    """design/65 §8: the visuals page; the route-exists test above covers its paths."""
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(APP / 'templates')), autoescape=True)
    env.globals['version'] = 't'
    html = env.get_template('visuals.html').render(user={'name': 'SK', 'role': 'Admin'}, run={'code': 'VW-9', 'title': 'Film'})
    for needed in ('id="app"', 'data-code="VW-9"', "'/runs/'+code+'/visuals'", 'id="s-plan"', 'id="s-record"', 'id="fmsg"', 'treatment', 'sequence', 'select-take', 'reject-take', 'record', 'cap', 'approve', "'/data'", "'/act'"):   # design/78: six step sections
        assert needed in html, needed
