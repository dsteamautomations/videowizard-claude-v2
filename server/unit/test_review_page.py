"""design/62: the review page. Slide cues from the saved render plan, the page's data from the stage-2 session, the template, and the
rule that every page path a template calls has a route (the audio route was lost in the 0.20.0 cleanup and nothing caught it)."""
import json
import re
from pathlib import Path

import pytest

from app.stage2 import stage as S
from app.errors import Problem

APP = Path(__file__).resolve().parents[1] / 'app'
FPS = 25


# ---------- slide cues ----------

def plan(items):
    return {'kind': 'review', 'items': items, 'version': 1, 'digest': 'd1'}


def test_slide_cues_sum_the_screen_time_before_each_slide_card():
    items = [{'kind': 'slate', 'lines': ['#1 | Scene 1: The need | 27.4 s | 2 shots', 'Clips: a + b']},            # 75 frames (the slate default)
             {'kind': 'narration', 'start_s': 0, 'end_s': 10},                                                   # no screen time
             {'kind': 'event', 'sub_clip_id': 'x', 'timeline_frames': 100},
             {'kind': 'card', 'frames': 50, 'lines': ['#1A | BLANK | Scene 1: The need | 2.0 s', 'For AI video or animation']},
             {'kind': 'slate', 'frames': 75, 'lines': ['#1B | DECISION | Scene 1: The need', 'Keep or drop: c (3.0 s)']},
             {'kind': 'narration', 'start_s': 10, 'end_s': 13},
             {'kind': 'event', 'sub_clip_id': 'c', 'timeline_frames': 75},
             {'kind': 'slate', 'lines': ['#2 | Scene 2: Mixing | BACKUP for #1 | 20.0 s | 1 shot']},
             {'kind': 'event', 'sub_clip_id': 'd', 'timeline_frames': 500}]
    cues = S.slide_cues(plan(items), FPS)
    assert cues == {'1': 0.0, '1A': 7.0, '1B': 9.0, '2': 15.0}   # 75 → 175 → 225 → 300 → 375 frames


def test_slide_cues_tolerate_an_empty_or_strange_plan():
    assert S.slide_cues({}, FPS) == {} and S.slide_cues(plan([{'kind': 'narration'}, {'kind': 'event', 'timeline_frames': 10}]), FPS) == {}
    assert S.slide_cues(plan([{'kind': 'slate', 'lines': []}, {'kind': 'slate', 'lines': ['#3 | x']}]), FPS) == {'3': 3.0}


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
SLIDES = [{'no': '1', 'type': 'option', 'option_number': 1, 'beat_id': 'BEAT_01', 'scene': 'Scene 1: The need', 'frames': 685, 'shots': 2, 'backup_for': None, 'lines': ['#1 | Scene 1: The need | 27.4 s | 2 shots', 'Clips: a + b']},
          {'no': '1A', 'type': 'decision', 'option_number': 1, 'beat_id': 'BEAT_01', 'event_index': 1, 'frames': 75, 'kind': 'keep_or_drop', 'question': 'Keep the drone shot?', 'lines': ['#1A | DECISION | Scene 1: The need', 'Keep the drone shot?']},
          {'no': '2', 'type': 'backup', 'option_number': 2, 'beat_id': 'BEAT_01', 'scene': 'Scene 1: The need', 'frames': 500, 'shots': 1, 'backup_for': '1', 'lines': ['#2 | Scene 1: The need | BACKUP for #1 | 20.0 s | 1 shot']},
          {'no': '3', 'type': 'option', 'option_number': 3, 'beat_id': 'BEAT_02', 'scene': 'Scene 2: Mixing', 'frames': 300, 'shots': 1, 'backup_for': None, 'lines': ['#3 | Scene 2: Mixing | 12.0 s | 1 shot']},
          {'no': '3A', 'type': 'blank', 'option_number': 3, 'beat_id': 'BEAT_02', 'event_index': 0, 'frames': 100, 'intent': 'diagram', 'lines': ['#3A | BLANK | Scene 2: Mixing | 4.0 s', 'For AI video or animation']}]


def session(**over):
    base = {'contract': 'vw2-stage2-session-v1', 'package': {'key': 'p', 'digest': 'pk1', 'narration_key': 'n'}, 'versions': [{'version': 1, 'digest': 'd1', 'file': {'key': 'run-1/stage2/options-v1.json'}, 'slides': SLIDES, 'options': 3, 'gaps': [], 'flags': []}],
            'current': 'd1', 'accepted': None, 'frames': {}, 'inspections': {}, 'renders': {}, 'decisions': {}, 'extra_rules': [], 'master': None, 'recorded': {}}
    return {**base, **over}


def files(sess, with_plan=True):
    f = {'run-1/stage2/session.json': sess, 'run-1/stage2/options-v1.json': {'document': {'options': []}, 'package_digest': 'pk1'}}
    if with_plan:
        f['run-1/stage2/render-review-v1.json'] = plan([{'kind': 'slate', 'lines': SLIDES[0]['lines']}, {'kind': 'event', 'timeline_frames': 100}, {'kind': 'slate', 'lines': SLIDES[1]['lines']}])
    return f


def test_review_view_before_a_film_says_the_render_state_and_lists_the_slides_with_lines():
    sess = session(renders={'review': {'job_id': 'j1', 'status': 'queued', 'digest': 'd1', 'version': 1}})
    view = S.review_view(FakeConn({'j1': {'status': 'running', 'result': None, 'error': None}}), FakeStore(files(sess, with_plan=False)), RUN)
    assert view['state'] == 'prepared' and view['version'] == 1 and view['film'] is None and view['cues'] == {}
    assert view['render'] == {'status': 'running', 'error': None, 'current': True} and view['accepted'] is False
    assert [s['slide'] for s in view['slides']] == ['1', '1A', '2', '3', '3A']
    assert view['slides'][0]['lines'] == SLIDES[0]['lines'] and view['slides'][0]['seconds'] == 27.4 and view['slides'][2]['backup_for'] == '1'
    assert view['slides'][1]['question'] == 'Keep the drone shot?' and view['slides'][4]['needs_answer'] is False
    assert view['slides'][1]['scene'] == 'Scene 1: The need' and view['slides'][4]['scene'] == 'Scene 2: Mixing'   # inner slides carry their scene
    assert view['answered'] == 0 and view['of'] == 4 and view['waiting'] == ['1', '1A', '2', '3']


def test_review_view_with_the_film_ready_carries_the_key_the_cues_and_the_answers():
    sess = session(renders={'review': {'job_id': 'j1', 'status': 'queued', 'digest': 'd1', 'version': 1}}, accepted={'version': 1, 'digest': 'd1', 'quote': 'yes', 'output': 'o1'},
                   recorded={'options': 'o1'}, decisions={'1': {'action': 'KEEP', 'type': 'option', 'note': '', 'by': 'u1', 'at': '2026-10-21T10:00:00Z'},
                                                           '1A': {'action': 'DROP', 'type': 'decision', 'note': '', 'by': 'u1', 'at': '2026-10-21T10:01:00Z'}})
    ready = {'status': 'ready', 'result': {'key': 'run-1/stage2/review-v1-d1.mp4', 'sha256': 's', 'bytes': 10, 'duration_s': 426.0}, 'error': None}
    view = S.review_view(FakeConn({'j1': ready}), FakeStore(files(sess)), RUN)
    assert view['film'] == {'key': 'run-1/stage2/review-v1-d1.mp4', 'duration_s': 426.0, 'sha256': 's'} and view['cues'] == {'1': 0.0, '1A': 7.0}
    assert view['accepted'] is True and view['render']['status'] == 'ready'
    by = {s['slide']: s for s in view['slides']}
    assert by['1']['answer'] == {'action': 'KEEP', 'note': '', 'edit': None, 'by': 'u1', 'at': '2026-10-21T10:00:00Z'} and by['1A']['answer']['action'] == 'DROP' and by['2']['answer'] is None
    assert view['answered'] == 2 and view['of'] == 4 and view['waiting'] == ['2', '3']


def test_review_view_without_a_session_or_a_version_says_so():
    assert S.review_view(FakeConn({}), FakeStore({}), RUN) == {'state': 'not_prepared'}
    assert S.review_view(FakeConn({}), FakeStore(files(session(current=None))), RUN) == {'state': 'no_version'}


def test_a_film_of_another_version_is_not_offered():
    sess = session(renders={'review': {'job_id': 'j1', 'status': 'ready', 'digest': 'OLD', 'version': 1, 'result': {'key': 'k', 'sha256': 's', 'bytes': 1}}})
    view = S.review_view(FakeConn({'j1': {'status': 'ready', 'result': {'key': 'k', 'sha256': 's', 'bytes': 1}, 'error': None}}), FakeStore(files(sess)), RUN)
    assert view['film'] is None and view['render'] == {'status': 'ready', 'error': None, 'current': False}


def test_slides_view_rows_carry_the_lines_for_the_chat_questions():
    """design/62 A: the assistant asks each slide with its own lines, so the slides endpoint carries them."""
    sess = session()
    view = S.slides_view(FakeStore(files(sess, with_plan=False)), RUN)
    assert view['slides'][0]['lines'] == SLIDES[0]['lines'] and view['of'] == 4


# ---------- the template and the routes ----------

def test_the_review_template_renders_in_every_state():
    """Rendered with a plain Jinja environment: the web module imports the auth module, whose 3.10 annotations this Python cannot load."""
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(APP / 'templates')), autoescape=True)
    env.globals['version'] = 't'
    html = env.get_template('review.html').render(user={'name': 'SK', 'role': 'Admin'}, run={'code': 'VW-9', 'title': 'Film'})
    for needed in ('id="app"', 'data-code="VW-9"', 'id="film"', 'id="slides"', 'id="fmsg"', "'/runs/'+code+'/review'", 'KEEP', 'DROP', 'REJECT', 'KEEP_WITH_EDIT'):
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


# ---------- design/63: after the operator has seen both cuts ----------

def kept(action='KEEP', **extra):
    return {'action': action, 'note': '', 'by': 'u1', 'at': '2026-10-21T10:00:00Z', **extra}


def test_both_cuts_kept_is_said_on_both_rows_and_in_the_decide_reply():
    sess = session(accepted={'version': 1, 'digest': 'd1'}, decisions={'1': kept(), '2': kept()})
    view = S.review_view(FakeConn({}), FakeStore(files(sess, with_plan=False)), RUN)
    by = {s['slide']: s for s in view['slides']}
    assert by['1']['conflict'] == '#2 is also kept: reject it or this one' and by['2']['conflict'] == '#1 is also kept: reject it or this one'
    assert by['3'].get('conflict') is None and view['both_kept'] == [{'scene': 'Scene 1: The need', 'slides': ['1', '2']}]
    sess = session(accepted={'version': 1, 'digest': 'd1'}, decisions={'1': kept()})
    store = FakeStore(files(sess, with_plan=False))
    out = S.decide(store, {'id': 'u1'}, RUN, '2', 'KEEP', '', None)
    assert out['conflict'] == '#1 is also kept: reject it or this one' and out['decided'] == 2
    out = S.decide(store, {'id': 'u1'}, RUN, '2', 'REJECT', 'the first cut is better', None)
    assert 'conflict' not in out


def test_decision_slides_inside_a_rejected_cut_need_no_answer():
    inner = [{'no': '2A', 'type': 'decision', 'option_number': 2, 'beat_id': 'BEAT_01', 'event_index': 0, 'frames': 50, 'kind': 'keep_or_drop', 'question': 'Keep the pan?', 'lines': ['#2A | DECISION | Scene 1: The need', 'Keep the pan?']}]
    sess = session(accepted={'version': 1, 'digest': 'd1'}, decisions={'1': kept(), '2': kept('REJECT', note='weaker')})
    sess['versions'][0]['slides'] = SLIDES + inner
    view = S.review_view(FakeConn({}), FakeStore(files(sess, with_plan=False)), RUN)
    by = {s['slide']: s for s in view['slides']}
    assert by['1A']['needs_answer'] is True and by['1A']['why'] is None            # inside the kept cut #1
    assert by['3']['needs_answer'] is True and by['3A']['needs_answer'] is False    # a blank never needs one
    assert by['2A']['needs_answer'] is False                                        # inside the rejected cut #2
    assert view['of'] == 4 and view['answered'] == 2 and view['waiting'] == ['1A', '3']   # 1, 1A, 2, 3 count; 2A does not
    # un-rejecting the cut brings its questions back
    sess['decisions']['2'] = kept()
    view = S.review_view(FakeConn({}), FakeStore(files(sess, with_plan=False)), RUN)
    assert view['of'] == 5 and view['waiting'] == ['1A', '3', '2A']   # film order of this fixture


def test_a_decision_inside_a_rejected_cut_is_greyed_with_the_reason():
    inner = [{'no': '2A', 'type': 'decision', 'option_number': 2, 'beat_id': 'BEAT_01', 'event_index': 0, 'frames': 50, 'kind': 'keep_or_drop', 'question': 'Keep the pan?', 'lines': ['#2A | DECISION | Scene 1: The need', 'Keep the pan?']}]
    sess = session(accepted={'version': 1, 'digest': 'd1'}, decisions={'2': kept('REJECT', note='weaker')})
    sess['versions'][0]['slides'] = SLIDES + inner
    view = S.review_view(FakeConn({}), FakeStore(files(sess, with_plan=False)), RUN)
    by = {s['slide']: s for s in view['slides']}
    assert by['2A']['needs_answer'] is False and by['2A']['why'] == 'inside rejected #2' and '2A' not in view['waiting']


def test_missing_answers_for_the_build_ignore_slides_inside_a_rejected_cut():
    inner = [{'no': '2A', 'type': 'decision', 'option_number': 2, 'beat_id': 'BEAT_01', 'event_index': 0, 'frames': 50, 'kind': 'keep_or_drop', 'question': 'Keep the pan?', 'lines': []}]
    sl = SLIDES + inner
    assert S.missing_answers(sl, {'1': kept(), '2': kept('REJECT', note='x'), '3': kept()}) == ['1A']
    assert S.missing_answers(sl, {'1': kept(), '2': kept(), '3': kept()}) == ['1A', '2A']
    assert S.missing_answers(sl, {}) == ['1', '1A', '2', '3', '2A']   # film order, as the slides are listed


def test_the_template_shows_the_conflict_and_the_reason():
    import jinja2
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(APP / 'templates')), autoescape=True)
    env.globals['version'] = 't'
    html = env.get_template('review.html').render(user={'name': 'SK', 'role': 'Admin'}, run={'code': 'VW-9', 'title': 'Film'})
    assert 's.conflict' in html and 's.why' in html and 'both_kept' in html


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
    assert view['film'] and view['cues'] == {'1': 0.0, '1A': 7.0}
    assert store.puts == [] and store.gets == ['run-1/stage2/session.json', 'run-1/stage2/render-review-v1.json']   # no document, no write
    store.gets.clear()
    S.review_view(FakeConn({'j1': ready}), store, RUN)
    assert store.gets == ['run-1/stage2/session.json']   # the cues of a rendered version are kept in memory


def test_a_version_without_stored_slides_still_loads_its_document():
    sess = session()
    del sess['versions'][0]['slides']
    sess['package'] = {'key': 'p', 'digest': 'pk1', 'narration_key': 'n'}
    store = CountingStore(files(sess, with_plan=False))
    store.files['run-1/stage2/options-v1.json'] = json.dumps({'document': {'options': []}, 'package_digest': 'pk1'}).encode('utf-8')
    store.files['p'] = json.dumps({'beats': [], 'sub_clips': [], 'cards': []}).encode('utf-8')
    view = S.review_view(FakeConn({}), store, RUN)
    assert view['slides'] == [] and 'run-1/stage2/options-v1.json' in store.gets


def test_the_page_draws_from_the_act_reply_without_a_second_request():
    html = (APP / 'templates' / 'review.html').read_text(encoding='utf-8')
    assert 'j.view' in html and 'will-change:transform' in html
