"""Fix set, part 1 (SK, 20 Nov 2026): the page and the chat offer the NEWEST render of a drawn graphic.

`visuals_stage.waiting` offered a drawn shot's oldest ready render (one item per label, the rows oldest first) while `pictures._drawn_state`
counted the newest: after a plan revision and a re-render the page line and its page copy were made from the old render, and its Select was
refused ("The plan changed since this drawing was rendered"). Now a drawn shot offers only the render that is counted; a render made before
it is not offered at all. AI video takes are not changed. Without a database."""

from pathlib import Path

from app import chat_flow as C, page_flow as PF, pictures as P, visuals_stage as VS
from test_design221_p4_pure import drawn_job, plan_of
from test_design222_takes_pure import guide, held, job, look, plan, rec, session, shot   # noqa: F401 (held is a fixture)
from test_fixset3_pure import finished
from test_visuals_stage_pure import FakeConn, USER
from test_design221_p1_pure import NEW

ROOT = Path(__file__).resolve().parents[2]


def renders(store, *ids, **over):
    """Render rows of MO1, oldest first, one a day; `over`: fields of the last one."""
    rows = []
    for n, jid in enumerate(ids, 1):
        store.files[f'run-1/takes/{jid}.motion.json'] = store.files['run-1/takes/job-7.motion.json']
        rows.append({**drawn_job(jid), 'created_at': f'2026-01-0{n}T00:00:00+00:00'})
    rows[-1].update(over)
    return rows


def offered(s, plan_, rows):
    return [w['item'] for w in VS.waiting(s, plan_, 'VW-1', rows, gate=False) if w['kind'] in ('take to select', 'held drawing')]


def test_after_two_re_renders_the_newest_is_offered_and_the_two_before_it_are_not():
    store = finished()
    rows = renders(store, 'job-7', 'job-8', 'job-9')
    s, plan_ = plan_of(store)
    assert next(i for i in P.expected(s, plan_, rows) if i['id'] == 'MO1')['job']['id'] == 'job-9'
    assert offered(s, plan_, rows) == ['job-9']


def test_a_render_selected_before_the_re_render_is_asked_again_on_the_new_render():
    store = finished()
    rows = renders(store, 'job-7', 'job-8')
    s, plan_ = plan_of(store)
    s['selections']['MO1'] = {'job_id': 'job-7'}   # selected on the plan of before; then the plan changed and the drawing was rendered again
    assert offered(s, plan_, rows) == ['job-8']    # the line asks again, on the new render; selecting it replaces the selection of the old one


def test_a_drawn_shot_whose_current_render_is_selected_offers_nothing_more():
    store = finished()
    rows = renders(store, 'job-7', 'job-8')
    s, plan_ = plan_of(store)
    s['selections']['MO1'] = {'job_id': 'job-8'}
    assert offered(s, plan_, rows) == []           # before: ['job-7'], the render made before it


def test_while_the_new_render_is_being_made_the_one_before_it_is_not_offered():
    store = finished()
    s, plan_ = plan_of(store)
    assert offered(s, plan_, renders(store, 'job-7', 'job-8', status='queued', result={})) == []


def test_a_render_of_a_project_other_than_the_bound_one_or_of_another_plan_is_not_offered():
    store = finished()
    s, plan_ = plan_of(store)
    [row] = renders(store, 'job-7')
    assert offered(s, plan_, [row]) == ['job-7']
    s['motion_bound'] = {'MO1': 'b' * 64}
    assert offered(s, plan_, [{**row, 'request': {**row['request'], 'sha256': 'a' * 64}}]) == []   # phase 3's A3.5: it reads being made
    s['motion_bound'] = {}
    assert offered(s, plan_, [{**row, 'request': {**row['request'], 'plan_digest': 'another plan'}}]) == []   # made on the plan of before: made again, never asked


def test_the_newest_render_rejected_leaves_the_one_the_count_falls_back_to():
    store = finished()
    rows = renders(store, 'job-7', 'job-8')
    s, plan_ = plan_of(store)
    s['reviews']['job-8'] = [{'decision': 'rejected', 'notes': 'the arrow is wrong'}]
    assert next(i for i in P.expected(s, plan_, rows) if i['id'] == 'MO1')['job']['id'] == 'job-7'   # pictures._drawn_state leaves a rejected render out
    assert offered(s, plan_, rows) == ['job-7']    # the page and the count agree


def test_the_page_line_and_its_video_copy_are_of_the_newest_render():
    store = finished()
    rows = renders(store, 'job-7', 'job-8')
    ctx = C._ctx(FakeConn(rows), store, USER, NEW, [])
    lines = [l for l in PF._pictures_lines({**ctx, 'page': True}) if l.get('kind') == 'drawn']
    assert [l['item'].split(':')[1] for l in lines] == ['job-8'] and lines[0]['video']['_key'] == 'run-1/takes/job-8.mp4'


def test_two_ai_video_takes_of_a_shot_are_listed_as_before(held, monkeypatch):
    """design/222: step 7 shows the takes of a shot on one line, on purpose: nothing of a `video` row is read by the new rule."""
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1', 'j2']))
    s['take_checks'].update(j1=rec(look=look()), j2=rec(look=look()))
    held(s, p)
    monkeypatch.setattr(VS, 'item_link', lambda *a: '')
    monkeypatch.setattr(P, '_drawn_state', lambda *a, **k: (_ for _ in ()).throw(AssertionError('a video take is not a drawn render')))
    rows = [job('j1'), job('j2', at='2026-11-19T11:00:00+00:00')]
    assert [(w['kind'], w['item']) for w in VS.waiting(s, p, 'VW-99', rows, gate=False)] == [('take to select', 'j2')]   # one line for the shot; design/223: its newest video is the one to answer (until then: the first with no rejection, 'j1'; design/35 row 328)


def test_the_older_way_is_in_the_decision_log():
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    assert '| 264 |' in log and 'pictures._drawn_state' in log.split('| 264 |', 1)[1]

