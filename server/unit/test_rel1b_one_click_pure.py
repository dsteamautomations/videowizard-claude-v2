"""Release 1, B1 (SK, 20 Nov 2026, answer 3: "One click, both steps"): the warning is shown before the buttons, and "Yes, put it in the film"
(a still, a graphic in steps) and "Select" (a drawn graphic, an AI video take) record at once as approved against the check: no second
box, no "Go back", no typed reason. The run's log keeps that it was approved against the check. This replaces step 7's D6 (the typed
reason). Rejecting still needs words. A reason typed on an older page is still taken. An answer to a take whose check changed after it was
shown is stale (as built in 0.118.0). Without a database."""
import pytest

from app import chat_flow as CF, guide as G, page_flow as PF, pictures as P, takes as T, visuals_stage as V
from test_design151_refs_pure import NEW
from test_design217_server_pure import NOW, RUN, plan, ref, session, shot
from test_design217_server_pure import USER as OP
from test_design217_server_pure import held as held6   # noqa: F401 (the fixture)
from test_design222_critic2_pure import film, item, landed, on_page, second_take   # noqa: F401 (film: the fixture)
from test_design222_takes_pure import guide, held, job, look, rec   # noqa: F401 (held: the fixture)
from test_design222_takes_pure import plan as take_plan, session as take_session, shot as take_shot
from test_guide_route_pure import take_film   # noqa: F401 (the fixture `film` builds on)
from test_visuals_stage_pure import USER, saved

FAILED = {'sha256': 'a' * 64, 'lines': [{'id': '1', 'check': 'a real face', 'pass': False, 'seen': 'The face matches a bystander of the footage.'}]}


# ---------- the lines: no second box, no typed reason; the button says it goes against the check ----------

def test_yes_on_a_still_with_warnings_has_no_second_box_and_says_it_goes_against_the_check(monkeypatch):
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    bad, good = ref('k1', look=FAILED), ref('k2', look={'sha256': 'a' * 64, 'lines': []})
    yes = P.picture_line(None, session(bad), plan(shot('S1')), bad)['buttons'][0]
    assert yes['label'] == 'Yes, put it in the film' and 'sure' not in yes and yes['needs_words'] is False and yes['against'] is True
    clean = P.picture_line(None, session(good), plan(shot('S1')), good)['buttons'][0]
    assert 'sure' not in clean and 'against' not in clean
    no, fix = P.picture_line(None, session(bad), plan(shot('S1')), bad)['buttons'][1:]
    assert fix['needs_words'] and no['act'] == 'again'                                                  # rejecting with a correction still needs words


def test_yes_on_a_graphic_in_steps_has_no_second_box_for_a_warning_or_for_two_steps_alike(monkeypatch):
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    monkeypatch.setattr(P, 'alike_steps', lambda store, chain: [(1, 2)])
    a, b = ref('a', 'state', 'G1', look={'sha256': 'a' * 64, 'lines': []}), ref('b', 'state', 'G1', look=FAILED)
    s, p = session(a, b), plan(shot('G1', 'animation', states=2))
    yes = P.steps_line(None, s, p, 'G1', [a, b])['buttons'][0]
    assert 'sure' not in yes and yes['against'] is True and not yes['needs_words']
    b['look'] = {'sha256': 'a' * 64, 'lines': []}
    line = P.steps_line(None, s, p, 'G1', [a, b])
    assert 'sure' not in line['buttons'][0] and 'against' not in line['buttons'][0] and line['check']['short'] == 'Passed, 1 note'   # two steps alike: a note in view, not a question


def _drawn(**res):
    return {'id': 'j9', 'unit': 'D1', 'provider': 'drawn', 'status': 'ready', 'request': {'kind': 'motion', 'request_key': 'k'},
            'result': {'key': 'v.mp4', 'sheet_key': 'sheet.jpg', 'evidence': {'timing_matches_placement': True, 'exact_seconds': 4.04}, **res}}


def test_select_on_a_drawn_graphic_asks_no_reason_when_its_check_did_not_pass_and_says_why_before_the_buttons(monkeypatch):
    monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    monkeypatch.setattr(V, 'load_json', lambda store, k: {'sha256': 'p' * 64})
    s, p = session(), plan(shot('D1', 'drawn', title='The wall'))
    line = P.drawn_line(None, s, p, _drawn(), {}, [], True)                                              # no fact check yet
    sel, rej = line['buttons'][:2]
    assert not sel['needs_words'] and sel['against'] is True and sel['say'] == 'Selected. It goes in the film at 2:10.4.' and not {'hint', 'go', 'need', 'sure'} & set(sel)
    assert line['held'] == 'It has no fact check yet. Select uses it all the same.' and 'say why' not in ' '.join(P.W[k] for k in P.W if k.startswith('held_'))
    assert rej['needs_words'] and rej['hint'] == 'What is wrong with it?'                               # D3: rejecting needs words
    s['motion_checks'] = {'D1': [{'sha256': 'p' * 64, 'round': 1, 'rules': [{'rule': 'r', 'pass': False}]}]}
    line = P.drawn_line(None, s, p, _drawn(), {}, [], True)
    assert line['held'] == 'Its fact check did not pass. Select uses it all the same.' and line['buttons'][0]['against'] is True
    s['motion_checks'] = {'D1': [{'sha256': 'p' * 64, 'round': 1, 'rules': [{'rule': 'r', 'pass': True}]}]}
    line = P.drawn_line(None, s, p, _drawn(), {}, [], True)
    assert line['held'] == '' and 'against' not in line['buttons'][0]


# ---------- the answers, through the page's own route: recorded at once, and the log keeps that it went against the check ----------


# ---------- step 6, through the chat's own items (the page calls the same run function) ----------

def _ctx6(box):
    return {'session': box['s'], 'plan': box['p'], 'run': RUN, 'store': None, 'user': OP, 'outputs': [], 'conn': object()}


def test_yes_on_a_still_with_warnings_approves_at_once_and_the_log_keeps_it(monkeypatch, held6):
    box = held6(session(ref('k1', look=FAILED)), plan(shot('S1')))
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run: [])
    monkeypatch.setattr(V, 'waiting', lambda *a_, **k: [{'kind': 'picture to answer', 'group': 'S1', 'item': 'k1', 'label': 'p', 'step': 'pictures'}])
    monkeypatch.setattr(V, '_set_budget', lambda *a_: None)
    monkeypatch.setattr(V, 'visuals_spend', lambda *a_: 0)
    calls, wrote = [], []
    monkeypatch.setattr(V, 'approve_reference', lambda *a_: calls.append(a_[4:7]) or {})
    monkeypatch.setattr(CF, '_decided', lambda conn, run, user, about, rule, entry, words: wrote.append((about, entry)))
    it = CF._waiting_items(_ctx6(box))[0]
    assert [(b['choice'], bool(b.get('needs_words'))) for b in it['buttons']] == [('yes', False), ('no', False), ('correct', True)]
    it['_run']('yes', 'Yes, put it in the film', '')
    assert calls == [('k1', 'a' * 64, 'Yes, put it in the film')]
    assert wrote == [('picture k1', 'approved against the check: a real face: The face matches a bystander of the footage.')]
    box['s']['references']['k1']['look'] = {'sha256': 'a' * 64, 'lines': []}
    CF._waiting_items(_ctx6(box))[0]['_run']('yes', 'Yes', '')
    assert len(wrote) == 1                                                                              # a clean picture: nothing about the check in the log


def test_select_on_a_drawn_graphic_that_is_held_selects_at_once_with_the_fixed_note_and_the_log_keeps_it(monkeypatch, held6):
    box = held6(session(), plan(shot('D1', 'drawn', title='The wall')))
    box['s']['motion_checks'] = {'D1': [{'sha256': 'p' * 64, 'round': 1, 'rules': [{'rule': 'the load arrow points down', 'pass': False}]}]}
    monkeypatch.setattr(V, 'load_json', lambda store, k: {'sha256': 'p' * 64})
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run: [_drawn()])
    monkeypatch.setattr(V, 'waiting', lambda *a_, **k: [{'kind': 'take to select', 'group': 'D1', 'item': 'j9', 'label': 't', 'step': 'takes'}])
    monkeypatch.setattr(V, '_set_budget', lambda *a_: None)
    monkeypatch.setattr(V, 'visuals_spend', lambda *a_: 0)
    monkeypatch.setattr(V, 'motion_brief', lambda *a_, **k: {'lines': {}})
    monkeypatch.setattr(V, 'stale_brief', lambda *a_, **k: [])
    calls, wrote = [], []
    monkeypatch.setattr(V, 'review_take', lambda *a_: calls.append(('review',) + a_[6:9]))
    monkeypatch.setattr(V, 'select_take', lambda *a_: calls.append(('select',) + a_[7:9]))
    monkeypatch.setattr(CF, '_decided', lambda conn, run, user, about, rule, entry, words: wrote.append((about, entry)))
    it = CF._waiting_items(_ctx6(box))[0]
    assert it['buttons'][0]['choice'] == 'select' and not it['buttons'][0].get('needs_words') and 'It' not in (it['buttons'][0].get('tell') or 'x')[:0]
    assert 'ask the operator why' not in str(it['buttons'][0])                                          # the chat asks no reason either
    it['_run']('select', 'Select: use it in the film', '')
    assert calls == [('select', P.W['against_note'], '')]
    assert wrote == [('shot D1', 'selected against the check: Its fact check did not pass: the load arrow points down')]
    it['_run']('select', 'Select', 'It reads right at film speed.')                                      # a reason typed on an older page is kept as it is
    assert calls[-1] == ('select', 'It reads right at film speed.', '')
