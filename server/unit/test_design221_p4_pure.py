"""design/221 phase 4 (SK, 19 Nov 2026): rows 18 and 19, what the operator is shown while step 6 is made. The list of what step 6 must make, each
with its state in plain words; one line of counts in the chat; the page only when everything is made (a thing that could not be made is shown as
such); a finished drawn graphic shown in the chat once, asking nothing; a drawing held after its rounds as a chat card (select it anyway with a
reason, reject it, one more round once); "Passed, N notes" on the page; the still pictures ordered at the start. Without a database."""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from app import chat_flow as C, page_flow as PF, pictures as P, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import FakeConn, motion_store
from test_design217_browser_pure import CAVITIES, browser, doc, go, inside, page as draw   # noqa: F401 (`browser` is the fixture)
from test_design217_together_pure import RUN as RUN217, USER as USER217, emit, server   # noqa: F401 (`server` is the fixture)
from test_design221_p1_pure import NEW, edit_plan, edit_session, visuals
from test_design221_p2_pure import EVEN, LEAVES, SOLID, upload, verdict
from test_visuals_stage_pure import USER, g, saved

ROOT = Path(__file__).resolve().parents[2]
V2 = {'v': 2, 'pass': 'complete', 'elements': {}}   # a film whose reference round is of today's kind: step 6 is answered on the page


def plan_of(store):
    s = saved(store)
    return s, VS.current_plan(store, s)


def states(items):
    return [(i['kind'], i['id'], i['state']) for i in items]


def key(n, sid='IM1', status='candidate', look=True, **over):
    sha = str(n) * 64
    return {'id': f'k{n}', 'kind': 'keyframe', 'shot_id': sid, 'element_id': 'E1', 'status': status, 'name': f'k{n}', 'key': f'run-1/visuals/references/k{n}.png',
            **({'sha256': sha} if status != 'generating' else {}), **({'look': {'sha256': sha, 'lines': []}} if look and status == 'candidate' else {}), **over}


def drawn_job(jid='job-7', status='ready', unit='MO1'):
    return {'id': jid, 'run_id': 'run-1', 'unit': unit, 'provider': 'drawn', 'status': status, 'cost': None, 'request': {'kind': 'motion', 'request_key': f'run-1/takes/{jid}.motion.json'},
            'result': {'key': f'run-1/takes/{jid}.mp4', 'sheet_key': f'run-1/takes/{jid}-sheet.jpg', 'sha256': 'x' * 64, 'bytes': 1, 'evidence': {'timing_matches_placement': True}}}


# ---------- point 1: what step 6 must make, and each thing's state ----------

def test_the_list_names_every_still_drawn_graphic_and_component_with_its_state():
    s, plan = plan_of(motion_store())
    items = P.expected(s, plan, [])
    assert states(items) == [('drawn', 'MO1', 'being made'), ('still', 'IM1', 'not started'), ('component', 'E1', 'made and checked')]   # MO1: its still end-frame is approved
    assert P.status_line(items) == 'Drawn graphics: 1 being made. Stills: 1 not started. Components: 1 made and checked.'
    assert not P.complete(items) and P.complete([]) and P.status_line([]) == ''


@pytest.mark.parametrize('refs, state', [
    ([key(1, status='generating')], 'being made'),
    ([key(1, status='rejected'), key(2, status='generating')], 'being redone'),
    ([key(1, look=False, asked_at='2999-01-01T00:00:00+00:00')], 'being checked by Claude'),
    ([key(1)], 'made and checked'),
    ([key(1, status='failed')], 'could not be made'),
    ([key(1, status='rejected')], 'being redone'),
])
def test_a_still_shot_reads_its_state_from_its_pictures(refs, state):
    store = motion_store()
    edit_session(store, lambda s: (s.update(round=V2), s['references'].update({r['id']: r for r in refs})))
    s, plan = plan_of(store)
    assert dict(((i['kind'], i['id']), i['state']) for i in P.expected(s, plan, []))[('still', 'IM1')] == state


def test_a_placed_still_is_answered():
    store = motion_store()
    edit_session(store, lambda s: s['assets'].update(IM1={'kind': 'still', 'reference_id': 'k1'}))
    assert ('still', 'IM1', 'answered') in states(P.expected(*plan_of(store), []))


def check(rnd, failed=(), sha='a' * 64, still=False):
    return {'sha256': sha, 'round': rnd, 'rules': [{'rule': r, 'pass': r not in failed, 'class': 'must'} for r in (SOLID, LEAVES)], **({'still': True} if still else {})}


@pytest.mark.parametrize('change, jobs, state', [
    (lambda s: s.update(motion_projects={'a' * 64: {'shot_id': 'MO1', 'key': 'k'}}), [], 'being checked by Claude'),
    (lambda s: s.update(motion_checks={'MO1': [check(1, [SOLID])]}), [], 'being redone'),
    (lambda s: s.update(motion_checks={'MO1': [check(1)]}), [], 'being made'),   # its render comes next
    (lambda s: None, [drawn_job(status='queued')], 'being made'),
    (lambda s: None, [drawn_job()], 'made and checked'),   # only once its render is ready
    (lambda s: None, [drawn_job(status='failed')], 'being redone'),   # design/221 (the critic's point 3): one failed render is asked again; twice on one project: test_design221_p5
    (lambda s: s.update(motion_checks={'MO1': [check(3, [SOLID])]}), [], 'held (needs a decision)'),
    (lambda s: s.update(motion_checks={'MO1': [check(3, [SOLID])]}, motion_held={'MO1': {'sha256': 'a' * 64, 'round': 3, 'answer': 'reject'}}), [], 'being redone'),
    (lambda s: s.update(motion_checks={'MO1': [check(3, [SOLID])]}, motion_more={'MO1': True}), [], 'being redone'),   # one more round: round 4 comes
    (lambda s: s['selections'].update(MO1={'job_id': 'job-7'}), [drawn_job()], 'answered'),
    (lambda s: s['reviews'].update({'job-7': [{'decision': 'rejected'}]}), [drawn_job()], 'being made'),   # rejected: rebuilt with the operator's words
])
def test_a_drawn_graphic_reads_its_state_from_what_the_server_knows(change, jobs, state):
    store = motion_store()
    edit_session(store, change)
    assert dict(((i['kind'], i['id']), i['state']) for i in P.expected(*plan_of(store), jobs))[('drawn', 'MO1')] == state


def test_a_film_with_no_drawn_graphics_and_a_film_with_no_stills():
    stills_only = motion_store()
    edit_plan(stills_only, lambda d: d['gaps'][0]['scenes'][0]['shots'][0].update(visual_type='image'))
    edit_session(stills_only, lambda s: s.update(motion_stills={}, references={}))
    assert P.status_line(P.expected(*plan_of(stills_only), [])) == 'Stills: 2 not started.'
    drawn_only = motion_store()
    edit_plan(drawn_only, lambda d: d['gaps'][0]['scenes'][0]['shots'][1].update(visual_type='footage'))
    edit_session(drawn_only, lambda s: s.update(references={}))
    assert P.status_line(P.expected(*plan_of(drawn_only), [drawn_job()])) == 'Drawn graphics: 1 made and checked.'


def test_could_not_be_made_counts_as_done_for_the_page_and_held_does_not():
    assert P.complete([{'state': 'made and checked'}, {'state': 'answered'}, {'state': 'could not be made'}])
    assert not P.complete([{'state': 'made and checked'}, {'state': 'held (needs a decision)'}])


# ---------- point 5: the held drawing, and round 4 once ----------

def held(store):
    sha = upload(store)
    for rnd in (1, 2):
        verdict(store, sha, {SOLID: False, EVEN: True, LEAVES: True}, rnd=rnd)
    return sha, verdict(store, sha, {SOLID: False, EVEN: True, LEAVES: True}, rnd=3)


def card(store, jobs):
    return [i for i in C._waiting_items(C._ctx(FakeConn(jobs), store, USER, NEW, [])) if i['kind'] in ('held drawing', 'take')]


def test_after_round_three_the_drawing_is_held_bound_for_its_render_and_round_four_is_refused():
    store = motion_store()
    sha, out = held(store)
    assert out['next'] == ('Held after round 3: 1 must rule still fails. Render it (`vw motion render --shot MO1`): the operator decides on its card in the chat '
                           '(`vw visuals next`): select it anyway with a reason, reject it, or one more round (once).')
    assert saved(store)['motion_bound'] == {'MO1': sha}   # rendered for the card; select still needs the reason
    with pytest.raises(Problem) as e:
        g(lambda: verdict(store, sha, {SOLID: False, EVEN: True, LEAVES: True}, rnd=4))
    assert ('MO1: round 4 is past the last round (3): the drawing is held and the operator decides on its card in the chat (`vw visuals next`); '
            '"One more round" there allows round 4, once.') in str(e.value)


def test_the_held_drawing_is_one_chat_card_with_its_open_musts_in_full_and_three_answers():
    store = motion_store()
    held(store)
    items = card(store, [drawn_job()])
    assert [i['kind'] for i in items] == ['held drawing']   # never also a take to select
    item = items[0]
    assert item['question'] == 'Gap G1, shot 1 (MO1): held after round 3: 1 must rule still fails. What do you decide?'
    assert item['text'] == f'- {SOLID}'
    assert [b['label'] for b in item['buttons']] == ['Select it anyway', 'Reject it', 'One more round'] and not item['buttons'][0].get('needs_words')   # release 1, B1 (the critic's point 10a): one click, no reason asked
    assert item['show'] == [{'key': 'run-1/takes/job-7.mp4', 'name': 'MO1-drawing.mp4'}, {'key': 'run-1/takes/job-7-sheet.jpg', 'name': 'MO1-frames.jpg'}]
    s, plan = plan_of(store)
    assert [w['kind'] for w in VS.waiting(s, plan, 'VW-9', [drawn_job()])] == ['held drawing']
    assert card(store, []) == []   # no card before its render is ready; the state says held
    assert ('drawn', 'MO1', 'held (needs a decision)') in states(P.expected(s, plan, []))


def recorders(monkeypatch, store):
    calls = []

    def review(conn, store_, user, run, outputs, job_id, decision, notes, timing, quote):
        edit_session(store, lambda s: s['reviews'].setdefault(job_id, []).append({'decision': decision, 'notes': notes}))
        calls.append(('review', job_id, decision, notes))
        return {}

    def select(conn, store_, user, run, outputs, job_id, quote, notes='', timing='', in_s=None):
        edit_session(store, lambda s: s['selections'].update(MO1={'job_id': job_id}))
        calls.append(('select', job_id, notes))
        return {'next': 'Take selected.'}
    monkeypatch.setattr(VS, 'review_take', review)
    monkeypatch.setattr(VS, 'select_take', select)
    return calls


def test_select_it_anyway_needs_the_reason_and_selects_with_it(monkeypatch):
    store = motion_store()
    held(store)
    calls = recorders(monkeypatch, store)
    card(store, [drawn_job()])[0]['_run']('select', 'Select it anyway', 'The joint reads well enough.')   # a reason given is kept; with none the fixed note is recorded (release 1, B1: test_rel1c_critic_pure)
    assert calls == [('select', 'job-7', 'The joint reads well enough.')]
    assert saved(store)['motion_held']['MO1']['answer'] == 'select' and ('drawn', 'MO1', 'answered') in states(P.expected(*plan_of(store), [drawn_job()]))


def test_reject_it_rebuilds_from_round_one(monkeypatch):
    store = motion_store()
    held(store)
    calls = recorders(monkeypatch, store)
    out = card(store, [drawn_job()])[0]['_run']('reject', 'Reject it', 'The joint is wrong.')
    assert calls == [('review', 'job-7', 'rejected', 'The joint is wrong.')]
    assert out['for_the_assistant'] == ('MO1: the operator rejected the held drawing: "The joint is wrong.". Give a new `vw-motion-shot` helper the open musts and these '
                                        'words to rebuild it, and check it again from round 1.')
    assert card(store, [drawn_job()]) == [] and ('drawn', 'MO1', 'being redone') in states(P.expected(*plan_of(store), [drawn_job()]))


def test_one_more_round_is_allowed_once_then_the_card_offers_two_answers(monkeypatch):
    store = motion_store()
    sha, _ = held(store)
    calls = recorders(monkeypatch, store)
    out = card(store, [drawn_job()])[0]['_run']('more', 'One more round', '')
    assert calls == [('review', 'job-7', 'rejected', "one more round, at the operator's word")]
    assert out['for_the_assistant'] == ('MO1: one more round, at the operator\'s word: give the open musts to a `vw-motion-shot` helper to redo it and send its verdict '
                                        'as round 4. After it the operator decides again: select it anyway or reject it.')
    again = verdict(store, sha, {SOLID: False, EVEN: True, LEAVES: True}, rnd=4)   # the server takes round 4 now
    assert again['next'].startswith('Held after round 4') and '(once)' not in again['next']
    item = card(store, [drawn_job('job-8')])[0]
    assert [b['label'] for b in item['buttons']] == ['Select it anyway', 'Reject it']
    with pytest.raises(Problem, match='MO1: the one more round is used: select it anyway with a reason, or reject it.'):
        g(lambda: VS.held_answer(FakeConn([drawn_job('job-8')]), store, USER, NEW, [], 'MO1', 'job-8', 'more', 'One more round', ''))
    with pytest.raises(Problem, match='past the last round'):
        g(lambda: verdict(store, sha, {SOLID: False, EVEN: True, LEAVES: True}, rnd=5))


# ---------- points 2, 4, 7: the line of counts, a finished drawing shown once, the stills at the start ----------

def nothing_needed(store, jobs):
    return C.next_item(FakeConn(jobs), store, USER, NEW, [])


def test_nothing_needed_gives_the_line_of_counts_first_and_the_stills_reminder():
    store = motion_store()
    edit_session(store, lambda s: s.update(round=V2))
    out = nothing_needed(store, [])
    assert out['item'] is None and out['working'][0] == 'Drawn graphics: 1 being made. Stills: 1 not started. Components: 1 made and checked. AI video: 1 not started.'   # design/222: step 7's counts join the line
    assert 'the first is the count of step 6: say it each time it changes, as it is, and ask nothing with it' in out['how']
    assert ('1 still shot has no picture asked for yet (IM1): order it now, beside the drawn graphics (`vw visuals image --shot S --element E --kind keyframe '
            '--prompt "…"`); it needs nothing from the drawings.') in out['then']
    st = VS.status(FakeConn([]), store, NEW, [])
    assert st['step6'].startswith('Drawn graphics: 1 being made.') and 'IM1' in st['step6']


def test_a_finished_drawing_is_shown_once_in_the_chat_with_its_line_and_no_question():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {SOLID: True, EVEN: False, LEAVES: True})
    edit_session(store, lambda s: s.update(round=V2))
    store.files['run-1/takes/job-7.motion.json'] = json.dumps({'sha256': sha}).encode('utf-8')
    out = nothing_needed(store, [drawn_job()])
    assert out['item'] is None and out['show'] == [{'key': 'run-1/takes/job-7.mp4', 'name': 'MO1-drawing.mp4',
                                                    'say': 'Gap G1, shot 1 (MO1): made and checked, 1 note. You judge it on the page with the others.'}]
    assert 'ask nothing about it' in out['how']
    assert 'show' not in nothing_needed(store, [drawn_job()])   # shown once
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "out.get('show')" in vw and "out.get('closed')" in vw


# ---------- point 3: the page only when complete (the film of design/217's test) ----------

def unlooked_k4(server):
    server['s']['references']['k4'].update(status='candidate', sha256='d' * 64)
    server['s']['references']['k4'].pop('look', None)


def test_the_page_stays_closed_until_everything_is_made_and_says_the_line_of_counts(server):
    unlooked_k4(server)
    pg = emit(server)
    line = ('Drawn graphics: 2 made and checked. Stills: 3 made and checked, 1 being checked by Claude, 1 could not be made. '
            'Graphics in steps: 1 made and checked.')
    assert pg['closed'] and not pg['open'] and pg['lines'] == [] and pg['say'] == line
    assert pg['then'] == line + ' ' + P.W['page_later'] and P.W['page_later'] == 'The page opens when everything of step 6 is made.'
    assert pg['how'] == PF.PICTURES_CLOSED and 'do not publish' in pg['how']
    server['s']['references']['k4']['look'] = {'sha256': 'd' * 64, 'lines': []}
    assert emit(server)['open'] and not emit(server).get('closed')   # made while the operator was away: the page opens


def test_a_thing_that_could_not_be_made_is_shown_as_such_and_the_page_opens(server):
    pg = emit(server)
    assert pg['open'] and [(c['name'], c['state'], c['note']) for c in pg['layout']['coming']] == [
        ('The brick kiln at dusk (S4)', 'failed', P.W['failed']), ('The kiln at night (S5)', 'failed', P.W['failed'])]
    assert pg['layout']['words']['pictures']['coming'] == 'Could not be made'
    assert 'joins the list when it is checked' not in ' '.join(pg['layout']['help'])


def test_asking_for_the_page_early_answers_with_the_line_of_counts_not_a_refusal(server):
    unlooked_k4(server)
    out = PF.page_record(None, server['store'], USER217, RUN217, [], [])
    assert out['refused'] == [] and out['page'].get('closed') and P.W['page_later'] in out['then'] and 'Stills: 3 made and checked' in out['then']


def test_every_answer_of_a_page_visit_is_recorded_though_the_first_makes_a_still_again(server):
    L = {l['name']: l for l in emit(server)['lines']}
    first, second = L['The finished three-storey building'], L['The kiln worker with the clay pan']
    out = PF.page_record(None, server['store'], USER217, RUN217, [], [{'line': 'l1', 'key': first['key'], 'item': first['item'], 'choice': 'no', 'notes': ''},
                                                                     {'line': 'l2', 'key': second['key'], 'item': second['item'], 'choice': 'yes', 'notes': ''}])
    assert sorted(out['recorded']) == sorted([first['key'], second['key']]) and out['stale'] == [] and out['refused'] == []
    assert out['page'].get('closed') and 'Stills: 4 answered' not in out['then'] and '1 being redone' in out['then']   # k1 is made again: the page waits for it


def test_the_chat_does_not_hand_out_a_ready_still_while_others_are_made(server):
    unlooked_k4(server)
    ids = [i['id'].split(':')[0] + ':' + i['id'].split(':')[1] for i in C._waiting_items(C._ctx(None, server['store'], USER217, RUN217, []))]
    assert ids == ['question:k3', 'picture:sty']   # the question and the style sheet are early decisions; the stills, the steps and the drawings wait for the page
    server['s']['references']['k4']['look'] = {'sha256': 'd' * 64, 'lines': []}
    out = C.next_item(None, server['store'], USER217, RUN217, [])
    assert out['item']['how'].startswith(P.W['page_now'])   # everything is made: the next call offers the page


# ---------- point 6: "Passed, N notes" on the page ----------

def test_the_page_says_passed_with_its_notes_and_a_note_needs_no_reason():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {SOLID: True, EVEN: False, LEAVES: True})
    orig, VS.load_json = VS.load_json, (lambda store_, k: {'sha256': sha})
    try:
        v = P.fact_view(saved(store), store, {'unit': 'MO1', 'request': {'request_key': 'k'}}, 'MO1')
    finally:
        VS.load_json = orig
    assert v['head'] == 'Passed, 1 note. Every must rule held, after 0 redo rounds. A note is not a fault: it needs no reason to select.' and v['notes'] == [EVEN]
    page = (ROOT / 'plugin' / 'pages' / 'decisions.html').read_text(encoding='utf-8')
    assert "id:'pnotes'" in page


@pytest.mark.parametrize('size', ['fit-small', 'fit-large'])
def test_a_drawing_with_three_notes_fits_the_page(browser, size):
    notes = ['The leader lines are not evenly spaced.', 'The arrow head touches the wall symbol.', 'The highlight is a shade lighter than the palette.']

    def change(L, d):
        c = L[CAVITIES['line']]
        c['check'] = {**c['check'], 'state': 'pass', 'faults': [], 'notes': notes,
                      'head': 'Passed, 3 notes. Every must rule held, after 1 redo round. A note is not a fault: it needs no reason to select.'}
        c['held'] = ''
    pg = draw(browser, doc(change), size=size)
    go(pg, CAVITIES)
    assert pg.locator('#pnotes').count() == 0                                             # release 1, B3: the box is closed; the notes are one click away
    pg.locator('#pcheckb').click()
    assert pg.locator('#pnotes li').all_text_contents() == notes
    for sel in ('#pcheck', '#sansh', '#smain .sname', '#sbig'):
        inside(pg, sel)
    for i in range(pg.locator('#pbar button').count()):
        inside(pg, f'#pbar button >> nth={i}')
    assert pg.evaluate("(() => { const m = document.querySelector('#smain'); return m.scrollHeight <= m.clientHeight; })()")   # the main area does not scroll
    assert pg.evaluate("(() => { const s = document.querySelector('.sside'); return !s || s.scrollTop === 0; })()")
    out = Path(os.environ.get('VW_P4_SHOTS') or tempfile.gettempdir()) / f'd221-p4-notes-{size}.png'
    pg.screenshot(path=str(out))
    pg.close()


# ---------- the texts ----------

def test_the_texts_say_the_page_at_the_end_the_counts_the_held_card_and_the_stills_first():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d221f_wording_v3 as W
    import fixset3_wording as FIX3   # fix set phase 3: the stills sentence of this script names the batch command now
    import rel1c_wording as REL1C   # release 1, the critic's point 10: the held card's "with their reason" is replaced inside this script's sentence
    stage = FIX3.before(REL1C.before(visuals()))
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    before = W.before(stage)
    texts = {'common': stage['prompt'], **{p['name']: p['text'] for p in stage['parts']}}
    olds = {'common': before['prompt'], **{p['name']: p['text'] for p in before['parts']}}
    for where, old, new, n in W.PAIRS:
        assert texts[where].count(new) == n and olds[where].count(old) == n, old[:50]
    later = texts['later']
    assert 'as they become ready' not in later and 'then show the operator the open musts' not in later
    assert 'order the still pictures at the start of the step, at the same time as the drawn graphics are begun' in later and 'they need nothing from the drawings' in later
    assert 'Render each drawn graphic as soon as its verdict is clean; never wait for the others.' in later
    assert 'say it to the operator each time it changes, as it is, and ask nothing with it' in later and '"One more round"' in later
    assert not any(w in later.lower() for w in ('wait for all drawings', 'when every drawing has passed', 'all drawings in one plan revision'))
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('d221e(prompt, parts)') < split.index('d221f(prompt, parts)')
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired for s in W.RETIRED)
    assert all(s not in json.dumps(P.W) for s in ('come to the page later', 'joins the list when', 'New pictures arrive while the film is being made'))
