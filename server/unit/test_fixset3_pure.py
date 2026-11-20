"""Fix set phase 3 (SK, 19 Nov 2026): the stills and the smaller faults of VW-24's redo of step 6.

A2.1: the reminder for the stills names the batch command and one call for all of them; one helper writes the prompts. A2.2: a picture another
picture is made from is an early decision: one chat card while the page is closed, and its approval is also the answer to "use it as the parent".
A2.3: a depth word in a still's prompt (what is nearer or further from the camera) places nothing. A3.1: the names on the parts picture are
wrapped to their cells, in the film's font. A3.3: the corner note and a logo picture are not text a drawn shot carries (the automatic pass was
taken out again by the critic's point 4: such a shot has carries_text false; test_fixset4_pure.py). A3.4: a finished drawing
is shown with the next answer too. A3.5: a new still of a shot with a bound project unbinds it at once and the shot is being redone. A3.6, M5:
the frame limit is the server's own sentence, with what to do. M6: the three refusals of the run end with the next step. The investigation: which
render of a drawn shot the page offers. Without a database."""
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app import chat_flow as C, core, font_sample, library, main as API, motion as M, pictures as P, visuals_stage as VS
from app.errors import Problem
from step6_shape import build, load, parts_svg, stills as still_ends, upload
from test_design130_p1_pure import motion_store
from test_design221_p1_pure import NEW, edit_plan, edit_session
from test_design221_p2_pure import EVEN, LEAVES, SOLID, upload as upload_mo, verdict as verdict_mo
from test_design221_p4_pure import V2, drawn_job, plan_of
from test_fixset2_pure import SECTION, bound, drawn, rendered, shots_of, still
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, g, plan_doc, ref, saved, session, shot, store_with

ROOT = Path(__file__).resolve().parents[2]
REAL = 'A yard of stacked goods at dusk, the nearest stack in focus, the further stacks soft.'   # the shape of the sentence refused on the run


@pytest.fixture(autouse=True)
def drawn_picture(monkeypatch):
    """The parts picture is drawn by Chromium on the server; here it is faked."""
    monkeypatch.setattr(font_sample, 'render', lambda html: b'\x89PNGparts')


# ---------- A2.1: the stills ordered at the start, all in one call ----------

def test_a21_the_reminder_names_the_batch_command_and_one_call_for_all_the_stills():
    items = [{'kind': 'still', 'id': s, 'state': P.STATE['none']} for s in ('IM1', 'IM2', 'IM3')]
    assert P.stills_due(items) == ('3 still shots have no picture asked for yet (IM1, IM2, IM3): order them now, all of them in one call, beside the drawn graphics '
                                   '(`vw visuals image --file out/images.json`, one row per still; one `vw-still-prompts` helper writes that file, started beside the '
                                   'parts helper); they need nothing from the drawings.')
    assert P.stills_due(items[:1]) == ('1 still shot has no picture asked for yet (IM1): order it now, beside the drawn graphics (`vw visuals image --shot S --element E '
                                       '--kind keyframe --prompt "…"`); it needs nothing from the drawings.')   # one still: one call as it is
    assert P.stills_due([{'kind': 'still', 'id': 'IM1', 'state': P.STATE['making']}]) == ''


# ---------- A2.2: a picture another picture is made from is an early decision ----------

def stills(failed=True, **k1):
    """A film whose step 6 is not finished (IM2 has no picture): IM1's picture K1 is made and Claude has looked at it (one must line failed)."""
    doc = plan_doc([shot('IM1', 0, 250, 'image'), shot('IM2', 250, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    sha = 'a' * 64
    look = {'sha256': sha, 'lines': [{'id': 'l1', 'check': 'signs of use', 'pass': not failed, 'seen': 'the surface is new'}]}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc), round=V2,
                   references={'K1': {**ref('K1'), 'sha256': sha, 'shot_id': 'IM1', 'look': look, **k1}})
    return store_with(sess, doc)


def order(store, parent='K1'):
    """The picture of IM2, made from IM1's picture."""
    body = {'request_id': str(uuid.uuid4()), 'element_id': 'E1', 'name': 'still-IM2', 'kind': 'keyframe', 'shot_id': 'IM2', 'subject': 'the wall', 'parents': [parent],
            'prompt': 'Image 1 is the start: take the wall from it; the same wall, now finished', 'region': {'left': 0.1, 'top': 0.1, 'width': 0.3, 'height': 0.3}}
    return g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], body))


def cards(store, conn=None):
    return [i for i in C._waiting_items(C._ctx(conn or FakeConn([]), store, USER, RUN, [])) if i['kind'] == 'picture']


def test_a22_a_picture_nothing_is_made_from_stays_for_the_page():
    store = stills()
    assert cards(store) == []   # the page is closed (IM2 is not made): a still waits for it


def test_a22_a_picture_another_is_made_from_is_one_chat_card_while_the_page_is_closed(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    store = stills()
    with pytest.raises(Problem) as e:
        order(store)
    assert e.value.message.endswith('K1 is asked of the operator now, in the chat (`vw visuals next`): once it is approved, order this picture again.')
    assert saved(store)['references']['K1']['parent_wanted'] is True
    with pytest.raises(Problem):
        order(store)   # asked again before the answer: refused again, and still one card
    [card] = cards(store)
    assert card['id'].startswith('picture:K1:')
    assert ("Another picture is made from this one, so it is asked now, before the page. Claude's check failed a must line (signs of use: the surface is new.): "
            'Yes approves it all the same, and also allows it as the parent of new pictures.') in card['text']


def test_a22_its_approval_is_also_the_answer_to_use_it_as_the_parent_recorded_once_as_the_operators(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    store = stills()
    with pytest.raises(Problem):
        order(store)
    conn = FakeConn([])
    [card] = cards(store, conn)
    card['_run']('yes', 'Yes', '')
    k1 = saved(store)['references']['K1']
    assert k1['status'] == 'approved' and k1['parent_ok'] is True and 'K1' not in (saved(store).get('questions') or {})
    logged = [p for sql, p in conn.sql if 'insert into vw2_log' in sql]
    assert len(logged) == 1 and logged[0][3] == 'picture K1' and logged[0][6] == 'operator'
    assert logged[0][5] == "approved, also as the parent of new pictures, although Claude's check failed a must line: signs of use: the surface is new."
    assert order(store)['reference_id']   # the picture made from it is ordered now: no second question about the same picture
    assert 'K1' not in (saved(store).get('questions') or {}) and cards(store) == []


def test_a22_a_parent_whose_check_passed_says_only_that_approving_allows_it_as_the_parent(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    store = stills(failed=False)
    with pytest.raises(Problem):
        order(store)
    [card] = cards(store)
    assert 'Another picture is made from this one, so it is asked now, before the page. Yes also allows it as the parent of new pictures.' in card['text']
    assert 'failed a must line' not in card['text']


def test_a22_the_older_approve_call_answers_the_parent_question_too_and_an_unmarked_parent_is_asked_as_before(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    store = stills(parent_wanted=True)
    VS.approve_reference(store, USER, RUN, [], 'K1', 'a' * 64, 'Approve', FakeConn([]))   # `vw visuals approve`, the reference's own call
    assert saved(store)['references']['K1']['parent_ok'] is True
    store = stills()
    VS.approve_reference(store, USER, RUN, [], 'K1', 'a' * 64, 'Approve', FakeConn([]))   # approved before anything was made from it
    assert not saved(store)['references']['K1'].get('parent_ok')
    with pytest.raises(Problem, match='K1 was approved with a failed must line'):
        order(store)   # then the parent question is asked once, as before
    assert saved(store)['questions']['K1']['fork'] == 'parent'


# ---------- A2.3: a depth word in a still's prompt places nothing ----------

def test_a23_what_is_nearer_or_further_from_the_camera_is_no_placement_in_a_stills_prompt():
    assert library.check_prompt(REAL, picture=True) is None
    assert library.check_prompt('The crates further from the camera are out of focus.', picture=True) is None
    with pytest.raises(ValueError, match="places something at 'further' with no landmark and measured distance"):
        library.check_prompt(REAL)   # any other prompt (a take's motion): as before
    for placed in ('The crate stands further along the shelf, in soft light.', 'Put the bucket closer to the wall.', 'The mat lies in the middle of the floor.'):
        with pytest.raises(ValueError, match='with no landmark and measured distance'):
            library.check_prompt(placed, picture=True)   # a true placement is still refused
    assert library.check_prompt('The crate stands two paces further along the shelf.', picture=True) is None


def test_a23_the_order_of_a_still_reads_its_prompt_as_a_pictures(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    store = stills()
    body = lambda prompt: {'request_id': str(uuid.uuid4()), 'element_id': 'E1', 'name': 'still-IM2', 'kind': 'keyframe', 'shot_id': 'IM2', 'subject': 'the wall', 'prompt': prompt}
    assert g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], body(REAL)))['reference_id']   # ordered: the depth words place nothing
    with pytest.raises(Problem, match="places something at 'closer' with no landmark and measured distance"):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], body('Put the bucket closer to the wall.')))


# ---------- A3.1: the names on the parts picture ----------

LONG = [{'id': 'part-a', 'title': 'Two roof tiles of fired clay, one laid on another, cut across'}, {'id': 'part-b', 'title': 'A roof tile of fired clay seen from above, its ribs shown'},
        {'id': 'part-c', 'title': 'Rod'}, {'id': 'part-d', 'title': 'Supercalifragilisticexpialidociousness of the base'}]


def names(svg):
    """[(the text element's x, its lines)] of the picture."""
    return [(int(x), re.findall(r'<tspan[^>]*>([^<]*)</tspan>', body)) for x, body in re.findall(r'<text x="(\d+)"[^>]*>(.*?)</text>', svg, re.S)]


def test_a31_each_name_is_wrapped_to_its_cell_and_no_line_is_wider_than_the_cell():
    svg = M.parts_preview(parts_svg(), LONG, '#FFFFFF', '#2B2B2B')
    cell, size = 300, 20
    rows = names(svg)
    assert [x for x, _ in rows] == [150, 450, 750, 150]   # each name under its own part, centred in its cell
    assert len(rows[0][1]) >= 2 and len(rows[1][1]) >= 2 and rows[2][1] == ['Rod'] and len(rows[3][1]) >= 2   # a long name is several lines; a word longer than the cell is cut
    for (_, lines), p in zip(rows, LONG):
        assert ''.join(lines).replace(' ', '') == p['title'].replace(' ', '')   # nothing of the name is lost
        assert all(len(line) * size * M.PART_NAME_EM <= cell - 20 for line in lines)   # no line wider than its cell: no name runs into its neighbour
    high = int(re.search(r'<svg[^>]*height="(\d+)"', svg).group(1))
    most = max(len(lines) for _, lines in rows)
    assert high == 2 * (cell + (most - 1) * M.PART_NAME_LINE)   # the rows grow by the extra lines, so no name runs into the row below


def test_a31_the_names_are_in_the_films_font_when_it_has_one_else_the_default():
    plain = M.parts_preview(parts_svg(), LONG, '#FFFFFF', '#2B2B2B')
    assert 'font-family="sans-serif"' in plain and '@font-face' not in plain
    svg = M.parts_preview(parts_svg(), LONG, '#FFFFFF', '#2B2B2B', fonts=['file:///fonts/Catamaran-wght.ttf'])
    assert "@font-face{font-family:'vw-part-0';src:url('file:///fonts/Catamaran-wght.ttf')}" in svg and 'font-family="\'vw-part-0\',sans-serif"' in svg


def test_a31_the_parts_card_is_drawn_with_the_films_font(monkeypatch):
    store = load(parts=False)
    seen = []
    monkeypatch.setattr(font_sample, 'render', lambda html: seen.append(html) or b'\x89PNGparts')
    g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', parts_svg().encode('utf-8')))
    assert 'font-family="sans-serif"' in seen[-1]   # the film's font is Noto Sans: the default
    monkeypatch.setattr(VS, 'film_font_files', lambda run: {'Catamaran-wght.ttf': 'server'})
    g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', parts_svg().replace('Arrow', 'Arrow head').encode('utf-8')))
    from app.drawn import FONTS
    assert f"src:url('{(FONTS / 'Catamaran-wght.ttf').as_uri()}')" in seen[-1] and "'vw-part-0',sans-serif" in seen[-1]


# ---------- A3.3: the corner note and a logo picture are not carried text ----------

def bare(d, *ids, **over):
    """These drawn shots say they carry text and list no label (the plan's own "no text at all": labels [])."""
    for s in [s for gap in d['gaps'] for s in gap['scenes'][0]['shots'] if s['id'] in ids]:
        s.update(carries_text=True, scene_motion={'labels': [], 'cues': []}, **over)


# The two tests of the automatic pass (a corner note or a logo with `labels: []` was not asked) went with it: the critic's point 4, test_fixset4_pure.py.

def test_a33_a_shot_that_really_carries_words_is_still_asked():
    store = load()
    edit_plan(store, lambda d: bare(d, 'D2', drawing_spec=None))   # no corner note and no logo: its text is its own
    with pytest.raises(Problem, match='D2 carries text and has no scene_motion.labels'):
        build(store, 'D1')
    store = load()
    edit_plan(store, lambda d: [s.update(carries_text=True) or s.pop('scene_motion') for s in shots_of(d)[1:2]])   # a corner note, and its texts not written yet (no scene_motion)
    with pytest.raises(Problem, match='D2 carries text and has no scene_motion.labels'):
        build(store, 'D1')
    store = load()
    edit_plan(store, lambda d: [s.update(scene_motion={'labels': [], 'cues': []}, drawing_spec={**s['drawing_spec'], 'illustrative': False, 'label': 'Section A'}) for s in shots_of(d)[1:2]])
    with pytest.raises(Problem, match='D2 carries text and has no scene_motion.labels'):
        build(store, 'D1')   # a spec's own label is a text on screen, as before


# ---------- A3.4: a finished drawing is shown with the next answer too ----------

def finished():
    store = motion_store()
    sha = upload_mo(store)
    verdict_mo(store, sha, {SOLID: True, EVEN: False, LEAVES: True})
    edit_session(store, lambda s: s.update(round=V2))
    store.files['run-1/takes/job-7.motion.json'] = json.dumps({'sha256': sha}).encode('utf-8')
    return store


def test_a34_a_finished_drawing_is_shown_while_a_question_waits_and_only_once():
    store = finished()
    VS.ask(store, USER, NEW, [], 'IM1', 'Which wall is shown?', ['the north wall', 'the south wall'])
    out = C.next_item(FakeConn([drawn_job()]), store, USER, NEW, [])
    assert out['item']['id'] == 'question:IM1'
    assert out['show'] == [{'key': 'run-1/takes/job-7.mp4', 'name': 'MO1-drawing.mp4', 'say': 'MO1: made and checked, 1 note. You judge it on the page with the others.'}]
    assert out['show_how'] == C.SHOW_FIRST and 'ask nothing about it' in C.SHOW_FIRST
    again = C.next_item(FakeConn([drawn_job()]), store, USER, NEW, [])
    assert again['item']['id'] == 'question:IM1' and 'show' not in again   # shown once, as before
    assert saved(store)['drawings_shown'] == {'MO1': 'job-7'}


def test_a34_a_drawing_finished_while_an_answer_is_recorded_comes_with_that_answer():
    store = finished()
    VS.ask(store, USER, NEW, [], 'IM1', 'Which wall is shown?', ['the north wall', 'the south wall'])
    VS.ask(store, USER, NEW, [], 'VS1', 'Which yard?', ['the front yard', 'the back yard'])
    first = C.next_item(FakeConn([]), store, USER, NEW, [])   # no drawing is rendered yet
    assert 'show' not in first
    out = C.answer(FakeConn([drawn_job()]), store, USER, NEW, [], first['item']['id'], 'c1', 'the north wall')
    assert out['item'] and [f['name'] for f in out['show']] == ['MO1-drawing.mp4']   # the next decision, and the drawing that finished meanwhile


# ---------- A3.5: a new still of a shot with a bound project ----------

def now_job(shot_id):
    return {**rendered(shot_id), 'created_at': datetime.now(timezone.utc).isoformat()}


def test_a35_a_new_still_of_a_bound_shot_unbinds_it_at_once_and_the_shot_is_being_redone():
    store = load()
    sha, _ = bound(store, 'D1', SECTION)
    jobs = [now_job('D1')]
    assert saved(store)['motion_bound']['D1'] == sha and drawn(store, jobs)['D1']['state'] == 'made and checked'
    assert build(store, 'D2')['continues']['sha256'] == sha
    upload(store, 'D1', *SECTION, still=True, more='redrawn {}')   # the drawing is redrawn after its render: a new still
    assert 'D1' not in saved(store)['motion_bound']
    item = drawn(store, jobs)['D1']
    assert item['state'] == 'being redone' and 'job' not in item   # the old render is not the drawing any more: the line of counts is right
    assert P.status_line(P.expected(*plan_of(store), jobs)).startswith('Drawn graphics: 1 being redone')
    with pytest.raises(Problem, match="D2 continues from D1: its still end-frame opens on D1's approved still end-frame, and D1 has none now"):
        build(store, 'D2')   # a drawing that continues it is handed neither the old project nor the old still (the critic's point 7)


def test_a35_the_same_still_uploaded_again_keeps_the_binding_and_the_redone_drawing_counts_again_when_rendered():
    store = load()
    sha, _ = bound(store, 'D1', SECTION)
    jobs = [now_job('D1')]
    upload(store, 'D1', *SECTION, still=True)   # the same still again (its parts changed elsewhere): nothing is redrawn
    assert saved(store)['motion_bound']['D1'] == sha and drawn(store, jobs)['D1']['state'] == 'made and checked'
    still(store, 'D1', SECTION, png=b'\x89PNGnew', more='redrawn {}')
    assert drawn(store, jobs)['D1']['state'] == 'being redone'
    from test_fixset2_pure import ALL_OK, approve
    from step6_shape import verdict
    approve(store, 'D1')
    new = upload(store, 'D1', *SECTION, more='redrawn b {}')['sha256']
    verdict(store, 'D1', new, ALL_OK)
    assert saved(store)['motion_bound']['D1'] == new
    of = lambda project: {**now_job('D1'), 'request': {**now_job('D1')['request'], 'sha256': project}}   # a render row names the project it rendered
    assert drawn(store, [of(sha)])['D1']['state'] == 'being made'   # the redrawn project passed: the render of the project before is not counted; its own comes next
    assert drawn(store, [of(sha), of(new)])['D1']['state'] == 'made and checked'   # its new render is the drawing


# ---------- A3.6, M5, M6: the limits and the refusals say the next step ----------

def test_a36_the_frame_limit_is_the_servers_own_refusal_and_says_what_to_do():
    body = API.MotionTool(request_id=uuid.uuid4(), shot_id='D1', op='snapshot', at=[n / 10 for n in range(13)])   # the route takes the call: the server's own sentence answers it
    with pytest.raises(Problem) as e:
        g(lambda: VS.motion_tool(FakeConn([]), load(), USER, NEW, [], API.body_dict(body)))
    assert e.value.message == 'A snapshot call takes at most 12 frames (--at); 13 were asked: nothing was taken. Ask in two calls of 12 or fewer.'
    assert VS.SNAPSHOT_FRAMES == 12


def test_m6_the_refusals_seen_on_the_run_end_with_the_next_step():
    again = ' Change the drawing, then upload it again: the same file is refused again.'
    assert VS.PARTS_USE_ONE.endswith(again) and VS.PARTS_USE.endswith(again) and VS.PARTS_USE_VIEW.endswith(again)
    assert core.defect_open({'defect': 7, 'stage': 'visuals'}) == ('defect 7 is open on this run and holds the visuals step; the builder resolves it, then the run continues. '   # release 3, C6: it says what it holds
                                                                   'Do not send this call again now: tell the operator, and send it once the builder says the defect is fixed.')
    assert "raise Problem(409, 'DEFECT_OPEN', defect_open(opened[0])" in (ROOT / 'server' / 'app' / 'core.py').read_text(encoding='utf-8')   # the write refused while a defect is open says it
    store = still_ends(load(), ('D1', *SECTION), ('D2', *SECTION))   # release 2, F1: D3 continues D2, so its still comes after theirs
    with pytest.raises(Problem) as e:
        upload(store, 'D3', 'part-base', still=True)   # D3 shows the block and places none of its three views
    assert 'D3 shows Block but uses none of its shared parts' in e.value.message and e.value.message.endswith(again)


# ---------- the investigation (report only): which render of a drawn shot the page offers ----------

# Fixed on SK's word of 20 Nov 2026 (test_fixset5_pure.py): visuals_stage.waiting offered the shot's oldest ready render; it offers the one pictures.expected counts.
def test_investigation_after_a_render_is_made_again_the_page_offers_the_render_that_is_counted():
    store = finished()
    old, new = {**drawn_job('job-7'), 'created_at': '2026-01-01T00:00:00+00:00'}, {**drawn_job('job-8'), 'created_at': '2026-01-02T00:00:00+00:00'}
    store.files['run-1/takes/job-8.motion.json'] = store.files['run-1/takes/job-7.motion.json']
    s, plan = plan_of(store)
    counted = next(i for i in P.expected(s, plan, [old, new]) if i['id'] == 'MO1')
    assert counted['state'] == 'made and checked' and counted['job']['id'] == 'job-8'   # the newest render is the one counted
    offered = [w['item'] for w in VS.waiting(s, plan, 'VW-1', [old, new], gate=False) if w['kind'] == 'take to select']
    assert offered == ['job-8']   # before: ['job-7'], the older render (made on the plan of before)


# ---------- the texts ----------

def visuals():
    return next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')


def test_the_served_text_and_the_helpers_say_it_and_the_older_ways_are_named():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import fixset3_wording as W
    import fixset4_wording as FIX4   # fix set, the critic's points: the sentence on the corner note and a logo is replaced (carries_text false)
    stage = FIX4.before(visuals())
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    texts = {p['name']: p['text'] for p in stage['parts']}
    was = {p['name']: p['text'] for p in W.before(stage)['parts']}
    for where, old, new in W.PAIRS:
        assert texts[where].count(new) == 1 and was[where].count(old) == 1 and new not in was[where], old[:50]
    later = texts['later']
    for said in ('all of them in one call (`vw visuals image --file out/images.json`)', 'one `vw-still-prompts` helper', 'every field as text',
                 'its approval also allows it as the parent', 'One call takes at most 12 frames'):
        assert said in later, said
    assert 'The corner note and a logo picture are not text the shot carries' in texts['plan']
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').replace('\r\n', '\n').count(new) == 1, (file, old[:50])
    for file in ('agents/vw-motion-check.md', 'agents/vw-motion-shot.md'):
        text = (ROOT / 'plugin' / file).read_text(encoding='utf-8')
        assert 'at most 12 frames' in text and 'two calls of 12 or fewer' in text, file
    shot_ = (ROOT / 'plugin' / 'agents' / 'vw-motion-shot.md').read_text(encoding='utf-8')
    assert 'A refused call is never sent again unchanged: read the refusal and change the call.' in shot_
    helper = (ROOT / 'plugin' / 'agents' / 'vw-still-prompts.md').read_text(encoding='utf-8')
    assert helper.startswith('---\nname: vw-still-prompts\n') and 'tools: Read, Write, Glob\nmodel: opus\neffort: high\n---\n' in helper and 'out/images.json' in helper   # Glob: the critic's point 10
    everything = stage['prompt'] + ''.join(p['text'] for p in stage['parts'])
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired and s not in everything for s in W.RETIRED)
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('fixset2(prompt, parts)') < split.index('fixset3(prompt, parts)')
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    assert all(f'| {n} |' in log for n in range(246, 254))   # the older way of each change
    for name in ('parent_wanted', 'stills_due', 'carries_text', 'drawings_shown', 'max_length=12', 'sans-serif', 'no landmark'):
        assert name in log.split('| 246 |', 1)[1], name


def test_m7_the_example_of_the_still_batch_file_holds_every_field_as_text_and_the_route_takes_it():
    later = next(p['text'] for p in visuals()['parts'] if p['name'] == 'later')
    helper = (ROOT / 'plugin' / 'agents' / 'vw-still-prompts.md').read_text(encoding='utf-8')
    for text in (later, helper):
        rows = json.loads(re.search(r'`(\[\{"element": .*?\}\])`', text).group(1))
        assert rows and all(isinstance(v, str) and v for row in rows for v in row.values()), rows
        for row in rows:   # the row as `vw visuals image --file` sends it (plugin/tests/test_fixset3.py runs the tool itself on it)
            body = API.ImageGenerate(request_id=uuid.uuid4(), element_id=row['element'], name=row['name'], kind=row['kind'], subject=row.get('subject') or row['element'],
                                     prompt=row['prompt'], shot_id=row['shot'])
            assert (body.element_id, body.kind, body.shot_id) == (row['element'], 'keyframe', row['shot'])
    with pytest.raises(Exception, match='element_id'):
        API.ImageGenerate(request_id=uuid.uuid4(), element_id=None, name='n', kind='keyframe', subject=None, prompt=None)   # the first call of the run: rows whose fields were not text
