"""Release 1, B3 (SK, 20 Nov 2026, answer 5: "One amber line, closed"): every check carries one short line, built on the server beside its
head (`short`), so the page's closed box and the chat say the same words: "Passed", "Passed, 1 note", "N warnings: <the first one's short
name>", or the sentence that says why it was not checked. The same for a still, a graphic in steps, a drawn graphic's fact check, the
server's own check of an older drawing, and an AI video take. In the chat the item says the short line, a warning in full, and only the
count of the lines that did not apply (the chat has no fold). Without a database."""
from app import pictures as P, takes as T, visuals_stage as V
from test_design217_server_pure import NOW, plan, ref, session, shot
from test_design222_takes_pure import guide, held, job, look, rec   # noqa: F401 (held: the fixture)
from test_design222_takes_pure import plan as take_plan, session as take_session, shot as take_shot


def looked(*rows):
    return {'sha256': 'a' * 64, 'lines': [{'id': str(n), 'check': c, 'pass': p, 'seen': seen} for n, (c, p, seen) in enumerate(rows)]}


def test_a_still_says_passed_or_its_warnings_by_the_first_ones_short_name_or_why_it_was_not_checked():
    s, p = session(), plan(shot('S1'))
    view = lambda r: P.check_view(s, r, p, NOW)
    assert view(ref('a', look=looked(('the place', True, 'a tiled roof'))))['short'] == 'Passed'
    one = view(ref('a', look=looked(('a real face', False, 'The face matches a bystander of the footage.'), ('the place', True, ''))))
    assert one['short'] == '1 warning: a real face' and one['state'] == 'fail' and one['head'].startswith("Claude's check found 1 problem")   # the head stays, for an older page
    two = view(ref('a', look=looked(('a real face', False, 'x'), ('nothing extra', False, 'a second ladder'), ('the place', 'na', 'a close view'))))
    assert two['short'] == '2 warnings: a real face' and two['na']['head'] == '1 line did not apply'
    late = view(ref('a', ready_at='2026-11-18T00:00:00+00:00', asked_at='2026-11-18T00:00:00+00:00'))
    assert late['state'] == 'not_checked' and late['short'] == late['head'] and late['short'].startswith('Not checked:')
    nothing = view(ref('a', look=looked(('the place', 'na', 'a close view'))))
    assert nothing['state'] == 'not_checked' and nothing['short'] == nothing['head']                    # every line "does not apply": never "Passed"
    older = P.check_view(session(v=1), ref('a', check={'lines': [{'check': 'the people', 'weight': 'must', 'pass': False, 'seen': 'three workers'}]}), p, NOW)
    assert older['short'] == '1 warning: the people' and older['who'] == 'model'                         # a picture the model checked before: the same short line


def test_a_graphic_in_steps_names_the_step_and_two_steps_alike_is_a_note(monkeypatch):
    monkeypatch.setattr(P, 'alike_steps', lambda store, chain: [(1, 2)])
    a, b = ref('a', 'state', 'G1', look=looked(('exact text', True, ''))), ref('b', 'state', 'G1', look=looked(('exact text', False, "it reads 'enviromental'")))
    s, p = session(a, b), plan(shot('G1', 'animation', states=2))
    v = P.steps_view(None, s, [a, b], p, NOW)
    assert v['short'] == '1 warning: step 2, exact text' and v['notes'] == ['Steps 1 and 2 look almost the same: the change between them is small.']
    b['look'] = looked(('exact text', True, ''))
    v = P.steps_view(None, s, [a, b], p, NOW)
    assert v['state'] == 'pass' and v['short'] == 'Passed, 1 note'                                       # what the second box asked about is a note in the closed line
    monkeypatch.setattr(P, 'alike_steps', lambda store, chain: [])
    v = P.steps_view(None, s, [a, b], p, NOW)
    assert v['short'] == 'Passed' and 'notes' not in v


def _job():
    return {'id': 'j9', 'unit': 'D1', 'provider': 'drawn', 'status': 'ready', 'request': {'kind': 'motion', 'request_key': 'k'}, 'result': {'key': 'v.mp4'}}


def test_a_drawn_graphics_fact_check_says_passed_its_notes_or_its_open_rules_cut_short(monkeypatch):
    monkeypatch.setattr(V, 'load_json', lambda store, k: {'sha256': 'p' * 64})
    long = 'The compression zone is drawn above the neutral axis and the tension zone below it, each in its own colour'
    rules = lambda *rows: {'D1': [{'sha256': 'p' * 64, 'round': 2, 'rules': [{'rule': r, 'pass': ok, **({'class': c} if c else {})} for r, ok, c in rows]}]}
    view = lambda checks: P.fact_view({**session(), 'motion_checks': checks}, None, _job(), 'D1')
    assert view({})['short'] == 'Not fact-checked yet.'
    assert view(rules(('r1', True, ''), ('r2', True, '')))['short'] == 'Passed'
    assert view(rules(('r1', True, ''), ('softer shadow', False, 'should')))['short'] == 'Passed, 1 note'
    assert view(rules(('r1', True, ''), ('n1', False, 'should'), ('n2', False, 'should')))['short'] == 'Passed, 2 notes'
    bad = view(rules((long, False, ''), ('r2', False, ''), ('n1', False, 'should')))
    assert bad['short'] == '2 warnings: The compression zone is drawn above the neutral axis and…' and bad['faults'][0] == long   # the short name is cut at a word; the rule in full is one click away
    assert P.server_view({'must_failed': [{'check': 'labels inside the frame'}]})['short'] == '1 warning: labels inside the frame'
    assert P.server_view(None)['short'] == 'Not checked yet.'


def test_the_chat_says_the_short_line_a_warning_in_full_and_only_the_count_of_the_lines_that_did_not_apply():
    s, p = session(), plan(shot('S1'))
    line = lambda r: {'where': 'In the film at 2:10.4', 'check': P.check_view(s, r, p, NOW)}
    ok = P.chat_text(line(ref('a', check={'code': []}, look=looked(('the place', True, 'a tiled roof'), ('the light', 'na', 'A close view shows no window.')))))
    assert ok == '- In the film at 2:10.4\n- Passed\n- 1 line did not apply'                                # no full text of a passed check
    bad = P.chat_text(line(ref('a', check={'code': []}, look=looked(('a real face', False, 'The face matches a bystander.'), ('nothing extra', False, 'A second ladder.')))))
    assert bad == '- In the film at 2:10.4\n- 2 warnings: a real face\n- a real face: The face matches a bystander.\n- nothing extra: A second ladder.'
    old = P.chat_text({'check': {'state': 'fail', 'head': "Claude's check found 1 problem: the place: a wall.", 'faults': ['the place: a wall.'], 'show': 'first'}})
    assert old == "- Claude's check found 1 problem: the place: a wall."                                   # a line with no short line (kept by an older server): its head, which names the first problem
