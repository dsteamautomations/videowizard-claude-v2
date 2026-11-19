"""design/221 (SK, 19 Nov 2026): the critic's five points on phases 3 and 4 (design/_work/design221-critic-phases3-4.md) and A6.
1. A drawing that continues a held drawing the operator selected anyway (or a shot with a selection) is briefed on that project.
2. The brief says the plan's cues; a new project is checked with the plan's labels and cues while the plan names no sha256.
3. A failed render is "being redone" while it can be asked again or something newer of the shot exists; "could not be made" only when the same
   project's render failed twice and nothing newer exists; the next step says what to do.
4. A drawing rendered on an older plan or older shared parts "must be rendered again (the plan or the shared parts changed)", with the command.
5. The helper texts say the server binds the passed project; nothing names an upload in the plan.
A6. The operator's answers on the shared parts, the still end-frame and the held drawing cards are written to the run's log as their decision.
Without a database."""
import json
from pathlib import Path

import pytest

from app import chat_flow as C, pictures as P, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import FakeConn, motion_store, project
from test_design221_p1_pure import NEW, edit_plan, edit_session
from test_design221_p2_pure import EVEN, LEAVES, SOLID, upload, verdict
from test_design221_p3b_pure import continuing, no_sha
from test_design221_p3c_pure import drawn_picture, no_still, parts, still_verdict, two, upload as upload3c   # noqa: F401 (`drawn_picture` is autouse)
from test_design221_p4_pure import V2, drawn_job, held, plan_of, states
from test_visuals_stage_pure import USER, g, saved

ROOT = Path(__file__).resolve().parents[2]
ALL = {SOLID: True, EVEN: True, LEAVES: True}
LABEL = 'Solid brick-on-edge course at sill level'


def drawn_state(store, jobs):
    return dict(((i['kind'], i['id']), i['state']) for i in P.expected(*plan_of(store), jobs))[('drawn', 'MO1')]


# ---------- 1: a drawing that continues a held drawing ----------

def brief_mo2(store):
    return g(lambda: VS.motion_brief(store, NEW, [], 'MO2', build=True, conn=FakeConn([])))


def test_a_drawing_continuing_a_held_drawing_selected_anyway_is_briefed_on_it():
    store = continuing()
    sha, _ = held(store)
    with pytest.raises(Problem, match='build and pass MO1 first'):   # held, not answered: MO2 waits
        brief_mo2(store)
    edit_session(store, lambda s: s.update(motion_held={'MO1': {'sha256': sha, 'round': 3, 'answer': 'reject'}}))
    with pytest.raises(Problem, match='build and pass MO1 first'):   # rejected: rebuilt, MO2 still waits
        brief_mo2(store)
    edit_session(store, lambda s: s.update(motion_held={'MO1': {'sha256': sha, 'round': 3, 'answer': 'select'}}))
    assert brief_mo2(store)['continues']['sha256'] == sha
    edit_session(store, lambda s: (s.pop('motion_held'), s['selections'].update(MO1={'job_id': 'job-7'})))
    assert brief_mo2(store)['continues']['sha256'] == sha   # a shot with a selection: its bound project


# ---------- 2: the plan's cues in the brief and in every check of a new project ----------

def test_the_brief_has_a_cues_line_with_each_selector_and_its_word_or_second():
    store = motion_store()
    b = VS.motion_brief(store, NEW, [], 'MO1')['brief']
    assert 'Cues from the plan (each part has this id and starts to move at its word or second): #label at the word "solid".' in b
    edit_plan(store, lambda d: d['gaps'][0]['scenes'][0]['shots'][0]['scene_motion'].update(cues=[{'selector': '#label', 'word': 'solid'}, {'selector': '#arrow', 'at_s': 2.4}]))
    b = VS.motion_brief(store, NEW, [], 'MO1')['brief']
    assert 'move at its word or second): #label at the word "solid"; #arrow at 2.4 s.' in b
    assert b.index('Cues from the plan') > b.index("Each word's start")
    edit_plan(store, lambda d: d['gaps'][0]['scenes'][0]['shots'][0]['scene_motion'].update(cues=[]))
    assert 'Cues from the plan' not in VS.motion_brief(store, NEW, [], 'MO1')['brief']   # no cue: no line


def test_a_new_project_is_checked_with_the_plans_labels_and_cues_while_the_plan_names_no_sha():
    store = motion_store()
    no_sha(store)
    sha = upload(store)   # not bound yet: no verdict
    request = VS._motion_request(store, VS.session_of(store, NEW, []), NEW, 'MO1', sha)[3]
    assert request['labels'] == [LABEL] and '#label' in json.dumps(request['sidecar'])
    named = motion_store()   # the older way: the plan names another project; a check of this one has no timing
    sha2 = upload(named)
    request = VS._motion_request(named, VS.session_of(named, NEW, []), NEW, 'MO1', sha2)[3]
    assert request['labels'] == [] and '#label' not in json.dumps(request['sidecar'])


# ---------- 3: a failed render ----------

ERR = 'HyperFrames: the timing check failed'


def failed(jid, sha='a' * 64, at='2026-11-19T10:00:00+00:00'):
    j = drawn_job(jid, status='failed')
    return {**j, 'request': {**j['request'], 'sha256': sha}, 'result': None, 'error': ERR, 'created_at': at}


def project_at(store, sha, at):
    edit_session(store, lambda s: s.setdefault('motion_projects', {}).update({sha: {'shot_id': 'MO1', 'key': 'k', 'at': at}}))


def test_a_failed_render_is_being_redone_and_the_next_step_says_render_it_again():
    store = motion_store()
    project_at(store, 'a' * 64, '2026-11-19T09:00:00+00:00')
    items = P.expected(*plan_of(store), [failed('j1')])
    assert ('drawn', 'MO1', 'being redone') in states(items) and not P.complete(items)
    assert P.drawn_due(items) == f'MO1: its render failed ({ERR}): render it again (`vw motion render --shot MO1`).'


def test_the_same_projects_render_failing_twice_with_nothing_newer_could_not_be_made():
    store = motion_store()
    project_at(store, 'a' * 64, '2026-11-19T09:00:00+00:00')
    jobs = [failed('j1'), failed('j2', at='2026-11-19T10:05:00+00:00')]
    items = P.expected(*plan_of(store), jobs)
    assert ('drawn', 'MO1', 'could not be made') in states(items)
    assert P.drawn_due(items) == (f'MO1: its render failed twice on the same project ({ERR}): fix that fault in the project with a `vw-motion-shot` helper, '
                                  'upload it, check it and render it again (`vw motion render --shot MO1`).')
    other = [failed('j1', sha='c' * 64), failed('j2', at='2026-11-19T10:05:00+00:00')]   # two failures of two projects: asked again
    assert drawn_state(store, other) == 'being redone'


@pytest.mark.parametrize('newer', [
    lambda s: s['motion_projects'].update({'b' * 64: {'shot_id': 'MO1', 'key': 'k2', 'at': '2026-11-19T11:00:00+00:00'}}),
    lambda s: s.update(motion_checks={'MO1': [{'sha256': 'a' * 64, 'round': 2, 'rules': [], 'at': '2026-11-19T11:00:00+00:00'}]}),
    lambda s: s['motion_stills']['MO1'].update(at='2026-11-19T11:00:00+00:00'),
])
def test_anything_newer_of_the_shot_after_the_failures_reads_being_redone_with_no_render_line(newer):
    store = motion_store()
    project_at(store, 'a' * 64, '2026-11-19T09:00:00+00:00')
    edit_session(store, newer)
    items = P.expected(*plan_of(store), [failed('j1'), failed('j2', at='2026-11-19T10:05:00+00:00')])
    assert ('drawn', 'MO1', 'being redone') in states(items) and P.drawn_due(items) == ''


def test_the_status_says_the_failed_render_line():
    store = motion_store()
    edit_session(store, lambda s: s.update(round=V2))
    st = VS.status(FakeConn([failed('j1')]), store, NEW, [])
    assert 'Drawn graphics: 1 being redone.' in st['step6'] and 'render it again (`vw motion render --shot MO1`)' in st['step6']


# ---------- 4: a drawing gone stale ----------

STALE = 'must be rendered again (the plan or the shared parts changed)'


def ready(plan_digest, used=None):
    j = drawn_job()
    return {**j, 'request': {**j['request'], 'plan_digest': plan_digest, **({'parts': used} if used is not None else {})}}


def test_a_drawing_rendered_on_an_older_plan_must_be_rendered_again_in_the_counts_and_the_next_step():
    store = motion_store()
    s, plan = plan_of(store)
    assert drawn_state(store, [ready(VS.digest(plan))]) == 'made and checked'
    items = P.expected(s, plan, [ready('an older plan')])
    assert ('drawn', 'MO1', STALE) in states(items) and not P.complete(items)
    assert P.status_line(items).startswith(f'Drawn graphics: 1 {STALE}.')
    assert P.drawn_due(items) == f'1 drawn graphic {STALE}: `vw motion render --shot MO1`.'
    assert drawn_state(store, [drawn_job()]) == 'made and checked'   # a render row from before carries no plan digest: read as before


def test_a_drawing_rendered_with_older_shared_parts_must_be_rendered_again():
    store = motion_store()
    edit_session(store, lambda s: s.update(motion_parts_approved={'sha256': 'p2', 'key': 'k', 'parts': [{'id': 'part-wall', 'digest': 'new'}]}))
    s, plan = plan_of(store)
    assert drawn_state(store, [ready(VS.digest(plan), {'part-wall': 'new'})]) == 'made and checked'
    assert drawn_state(store, [ready(VS.digest(plan), {'part-wall': 'old'})]) == STALE
    two_items = [{'kind': 'drawn', 'id': i, 'state': STALE, 'due': ''} for i in ('MO1', 'MO2')]
    assert P.drawn_due(two_items) == f'2 drawn graphics {STALE}: `vw motion render --shot S` for each (MO1, MO2).'


def test_the_render_row_carries_its_plan_digest_project_and_parts():
    store = motion_store()
    no_sha(store)
    sha = upload(store)
    verdict(store, sha, ALL)
    conn = FakeConn([])
    VS.render_motion(conn, store, USER, NEW, [], {'shot_id': 'MO1'})
    row = conn.inserted[-1][2].obj
    assert row['plan_digest'] == VS.digest(plan_of(store)[1]) and row['sha256'] == sha and row['parts'] == {}


# ---------- 5: the helper texts ----------

def test_the_helper_texts_say_the_server_binds_the_passed_project():
    skill = (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    shot = (ROOT / 'plugin' / 'agents' / 'vw-motion-shot.md').read_text(encoding='utf-8')
    for text in (skill, shot):
        assert 'names your upload in the plan' not in text
        assert 'the server binds the project that passes its fact check; the main assistant renders it.' in text
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert 'The main assistant names your upload in the plan and renders it.' in retired


# ---------- A6: the three new cards' answers in the run's log ----------

def logged(conn):
    return [p for sql, p in conn.sql if 'insert into vw2_log' in sql]


def test_the_held_drawing_answer_is_the_operators_decision_in_the_log(monkeypatch):
    from test_design221_p4_pure import recorders
    store = motion_store()
    held(store)
    recorders(monkeypatch, store)
    conn = FakeConn([drawn_job()])
    item = [i for i in C._waiting_items(C._ctx(conn, store, USER, NEW, [])) if i['kind'] == 'held drawing'][0]
    item['_run']('select', 'Select it anyway', 'The joint reads well enough.')
    (row,) = logged(conn)
    assert row[1:] == ('visuals', 'decision', 'shot MO1', 'design/221 row 18 (a held drawing, decided in the chat)',
                       'the held drawing selected anyway: "The joint reads well enough."', 'operator', 'SK', 'The joint reads well enough.', None)


def test_a_refused_answer_writes_nothing_to_the_log():
    store = motion_store()
    held(store)
    conn = FakeConn([drawn_job()])
    item = [i for i in C._waiting_items(C._ctx(conn, store, USER, NEW, [])) if i['kind'] == 'held drawing'][0]
    with pytest.raises(Problem):
        g(lambda: item['_run']('select', 'Select it anyway', ''))
    assert logged(conn) == []


def test_the_parts_and_still_answers_are_the_operators_decision_in_the_log():
    store = two()
    parts(store, ok=False)
    conn = FakeConn([])
    item = [i for i in C._waiting_items(C._ctx(conn, store, USER, NEW, [])) if i['kind'] == 'parts'][0]
    item['_run']('reject', 'Reject', 'The wall is too tall.')
    (row,) = logged(conn)
    assert row[2:6] == ('decision', 'the shared parts', 'design/221 row 1 (the shared parts, approved in the chat)', 'the shared parts rejected: "The wall is too tall."')
    assert row[6:9] == ('operator', 'SK', 'The wall is too tall.')
    store = no_still(motion_store())
    still_verdict(store, upload3c(store, still=True), {SOLID: True})
    conn = FakeConn([])
    item = [i for i in C._waiting_items(C._ctx(conn, store, USER, NEW, [])) if i['kind'] == 'still end-frame'][0]
    item['_run']('approve', 'Approve', '')
    (row,) = logged(conn)
    assert row[2:9] == ('decision', 'shot MO1', 'design/221 row 3 (the still end-frame, approved in the chat)', 'the still end-frame approved', 'operator', 'SK', 'Approve')


# ---------- defect 55 (VW-24): a brief's picture kept under another name is fetchable ----------

def test_defect55_a_picture_kept_under_another_name_is_copied_to_where_the_plugin_fetches_it():
    from app import visuals_stage as V

    class Store:
        def __init__(self):
            self.d = {'R/visuals/drawings/abc/a-plain.png': b'PNG-A', 'R/visuals/references/f1.png': b'PNG-F'}
            self.puts = []

        def exists(self, k):
            return k in self.d

        def get(self, k):
            return self.d[k]

        def put(self, k, data, mime=None, **kw):
            self.d[k] = data
            self.puts.append(k)

    st = Store()
    session = {'references': {'drawing-TILE-a-1': {'key': 'R/visuals/drawings/abc/a-plain.png'}, 'f1': {'key': 'R/visuals/references/f1.png'}, 'gone': {}}}
    ids = ['drawing-TILE-a-1', 'f1', 'gone', 'unknown']
    assert V.refs_fetchable(st, {'id': 'R'}, session, ids) == ids
    assert st.d['R/visuals/references/drawing-TILE-a-1.png'] == b'PNG-A' and st.puts == ['R/visuals/references/drawing-TILE-a-1.png']
    V.refs_fetchable(st, {'id': 'R'}, session, ids)   # a second brief copies nothing again
    assert st.puts == ['R/visuals/references/drawing-TILE-a-1.png']
