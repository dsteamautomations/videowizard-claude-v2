"""Release 3, C1 and C2 (SK, 20 Nov 2026, N5: "Remove both kinds of card").
C1: a plan change that only adds labels to drawn shots, in the plan's own approved words, asks nothing (already so: the labels are a note of
the shot, proved here); a label with a word the shot's approved text does not hold is asked (new); `carries_text` set to false on a drawn shot
whose only text is the corner note or a logo is no longer asked (new). C2: a plan change proposed with the operator's answer to a question
(`answers`) is accepted with that answer when it stays inside what the question names; anything larger is asked as before.
Without a database."""
import copy
import json

import pytest

from app import chat_flow as C, visuals_stage as V
from app.errors import Problem
from test_visuals_stage_pure import FakeConn, FakeStore, RUN, USER, plan_doc, session, shot


def drawn(sid, a, b, **extra):
    return shot(sid, a, b, 'drawn', depicts='The compression zone above, the tension zone below', message='Only the top works', **extra)


def doc():
    d = plan_doc([drawn('D1', 0, 200, carries_text=True), shot('P1', 200, 500, 'image')], [drawn('D2', 900, 1150, carries_text=True)])
    d['elements'].append({'id': 'E2', 'name': 'Client logo', 'kind': 'graphic', 'identity': 'exact', 'requirements': 'the logo as supplied'})
    return d


def film(d=None):
    """Version 1 proposed and every gap accepted by the operator, as `accept` records it."""
    store, sess, d = FakeStore(), session(), d or doc()
    V.new_version(store, RUN, sess, d, USER, [])
    for gap in d['gaps']:
        sess['accepted'][gap['gap_id']] = {'digest': V.gap_digest(d, gap), 'own': V.gap_own_digest(d, gap), 'shared': V.shared_digest(d), 'version': 1, 'choice_id': None, 'quote': 'Accept', 'by': 'u1'}
    return store, sess, d


def change(d, fn):
    new = copy.deepcopy(d)
    fn({s['id']: s for g in new['gaps'] for sc in g['scenes'] for s in sc['shots']}, new)
    return new


def cards(store, sess):
    """The plan cards the chat would hand out now: the gaps asked."""
    ctx = {'session': sess, 'plan': V.current_plan(store, sess), 'store': store, 'conn': None, 'user': USER, 'run': RUN, 'outputs': []}
    return [i['id'].split(':')[1] for i in C._plan_items(ctx)[0]]


# ---------- C1 ----------

def test_labels_in_the_plans_own_words_ask_nothing_and_are_logged_as_the_assistants_change():
    store, sess, d = film()
    assert cards(store, sess) == []
    new = change(d, lambda s, _: (s['D1'].update(scene_motion={'labels': ['Compression zone', 'tension ZONE', 'Wall  section'], 'cues': []}),
                                  s['D2'].update(scene_motion={'labels': ['Only the top works'], 'cues': []})))
    out = V.new_version(store, RUN, sess, new, USER, [])
    assert sorted(sess['accepted']) == ['G1', 'G2'] and cards(store, sess) == []        # the words of the shot and its thing's name: no card
    assert out['quiet'] == [{'gap': 'G1', 'why': 'labels', 'shots': ['D1']}, {'gap': 'G2', 'why': 'labels', 'shots': ['D2']}]
    assert V.QUIET['labels'] == "labels added in the plan's own words: no decision; the acceptance is kept"


def test_one_label_with_a_word_the_plan_does_not_hold_brings_the_card_and_the_card_names_it():
    store, sess, d = film()
    new = change(d, lambda s, _: (s['D1'].update(scene_motion={'labels': ['Compression zone', 'Idle concrete'], 'cues': []}),
                                  s['D2'].update(scene_motion={'labels': ['Only the top works'], 'cues': []})))
    out = V.new_version(store, RUN, sess, new, USER, [])
    assert sorted(sess['accepted']) == ['G2'] and cards(store, sess) == ['G1']          # "Idle concrete" is new wording: G1 is asked; G2 is not
    assert out['asked'] == {'G1': ['D1: "Idle concrete"']} and sess['was_accepted'] == {'G1': 1}
    changes = V.gap_changes(store, sess, new, new['gaps'][0])
    assert any('D1' in c and 'Idle concrete' in c for c in changes), changes             # the card says which words are new
    sess['accepted']['G1'] = {'digest': V.gap_digest(new, new['gaps'][0]), 'own': V.gap_own_digest(new, new['gaps'][0]), 'shared': V.shared_digest(new), 'version': 2, 'quote': 'Accept', 'by': 'u1'}
    sess['was_accepted'].pop('G1')
    V.new_version(store, RUN, sess, copy.deepcopy(new), USER, [])                        # the same labels proposed again: answered once
    assert sorted(sess['accepted']) == ['G1', 'G2']


def test_labels_with_another_change_bring_the_card_as_before():
    store, sess, d = film()
    new = change(d, lambda s, _: s['D1'].update(scene_motion={'labels': ['Compression zone'], 'cues': []}, purpose='show something else'))
    out = V.new_version(store, RUN, sess, new, USER, [])
    assert cards(store, sess) == ['G1'] and out['quiet'] == [] and out['asked'] == {}


def test_carries_text_set_to_false_on_a_shot_whose_only_text_is_the_corner_note_or_a_logo_asks_nothing():
    note = {'label': 'Illustrative, not to scale', 'illustrative': True}
    base = change(doc(), lambda s, _: (s['D1'].update(drawing_spec=note), s['D2'].update(element_ids=['E1', 'E2'])))
    store, sess, d = film(base)
    new = change(d, lambda s, _: (s['D1'].update(carries_text=False), s['D2'].update(carries_text=False)))
    out = V.new_version(store, RUN, sess, new, USER, [])
    assert cards(store, sess) == [] and sorted(sess['accepted']) == ['G1', 'G2']         # the corner note (D1) and the logo element (D2)
    assert out['quiet'] == [{'gap': 'G1', 'why': 'no_text', 'shots': ['D1']}, {'gap': 'G2', 'why': 'no_text', 'shots': ['D2']}]
    assert sess['accepted']['G1']['digest'] == V.gap_digest(new, new['gaps'][0]) and sess['accepted']['G1']['version'] == 2 and sess['accepted']['G1']['quote'] == 'Accept'
    assert V.QUIET['no_text'] == 'carries_text set to false (its only text is the corner note or a logo): no decision; the acceptance is kept'


def test_carries_text_set_to_false_on_any_other_shot_is_asked_as_before():
    store, sess, d = film()                                                              # no corner note, no logo element
    V.new_version(store, RUN, sess, change(d, lambda s, _: s['D1'].update(carries_text=False)), USER, [])
    assert cards(store, sess) == ['G1']
    note = {'label': 'Illustrative, not to scale', 'illustrative': True}
    store, sess, d = film(change(doc(), lambda s, _: s['D1'].update(drawing_spec=note)))
    V.new_version(store, RUN, sess, change(d, lambda s, _: s['D1'].update(carries_text=False, scene_motion={'labels': ['Compression zone'], 'cues': []})), USER, [])
    assert cards(store, sess) == ['G1']                                                  # it lists a label of its own: it does carry text
    store, sess, d = film(change(doc(), lambda s, _: s['P1'].update(carries_text=True)))
    V.new_version(store, RUN, sess, change(d, lambda s, _: s['P1'].update(carries_text=False)), USER, [])
    assert cards(store, sess) == ['G1']                                                  # a still picture, not a drawn shot


def test_a_film_with_no_drawn_shot_is_carried_and_asked_as_before():
    d = plan_doc([shot('P1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    store, sess, d = film(d)
    out = V.new_version(store, RUN, sess, copy.deepcopy(d), USER, [])
    assert sorted(sess['accepted']) == ['G1', 'G2'] and out['quiet'] == [] and out['asked'] == {}
    V.new_version(store, RUN, sess, change(d, lambda s, _: s['P1'].update(purpose='another purpose')), USER, [])
    assert cards(store, sess) == ['G1']


def test_an_acceptance_of_the_older_server_and_a_gap_already_waiting_keep_working():
    store, sess, d = film()
    sess['accepted']['G1'] = {'digest': sess['accepted']['G1']['digest'], 'quote': 'yes', 'by': 'u1'}   # before design/191: no `own`, no version
    V.new_version(store, RUN, sess, change(d, lambda s, _: s['D2'].update(purpose='changed')), USER, [])
    assert sorted(sess['accepted']) == ['G1'] and cards(store, sess) == ['G2']           # G1 untouched: carried; G2 asked
    V.new_version(store, RUN, sess, change(d, lambda s, _: (s['D2'].update(purpose='changed'), s['D1'].update(scene_motion={'labels': ['Compression zone'], 'cues': []}))), USER, [])
    assert sorted(sess['accepted']) == ['G1'] and cards(store, sess) == ['G2']           # the gap that waits for its card still waits, for the same card


# ---------- C2 ----------

def answered(sess, item, words='Use the client logo'):
    sess.setdefault('answered', []).append({'item': item, 'question': 'Which logo closes the film?', 'choices': ['Use the client logo', 'No logo'], 'by': 'u1',
                                            'answer': words, 'answered_by': 'u1', 'answered_at': '2026-11-20T10:00:00+00:00'})
    return sess['answered'][-1]


def test_a_change_inside_the_shot_the_answered_question_names_is_accepted_with_the_answer():
    store, sess, d = film()
    q = answered(sess, 'D2')
    new = change(d, lambda s, _: s['D2'].update(purpose='the closing card with the client logo', depicts='The client logo, centred'))
    out = V.new_version(store, RUN, sess, new, USER, [], answers='D2')
    assert cards(store, sess) == [] and sorted(sess['accepted']) == ['G1', 'G2']
    acc = sess['accepted']['G2']
    assert acc['quote'] == 'Use the client logo' and acc['version'] == 2 and acc['digest'] == V.gap_digest(new, new['gaps'][1]) and acc['answer_to'] == 'D2'
    assert out['quiet'] == [{'gap': 'G2', 'why': 'answer', 'shots': ['D2'], 'item': 'D2', 'question': 'Which logo closes the film?', 'answer': 'Use the client logo',
                             'changes': out['quiet'][0]['changes']}]
    assert any('purpose' in c and 'closing card' in c for c in out['quiet'][0]['changes'])   # the differences, for the log line
    assert q['plan_version'] == 2                                                        # used once
    with pytest.raises(ValueError, match='No answered question on D2 waits for its plan change'):
        V.new_version(store, RUN, sess, change(new, lambda s, _: s['D2'].update(purpose='again')), USER, [], answers='D2')


def test_a_question_about_a_thing_names_the_shots_that_show_it_and_the_thing_itself():
    store, sess, d = film(change(doc(), lambda s, _: s['D2'].update(element_ids=['E2'])))
    answered(sess, 'E2')

    def edit(s, new):   # the critic's point 3: the thing's own record; a change of D2's words is asked (test_rel3b_critic_pure.py)
        next(e for e in new['elements'] if e['id'] == 'E2').update(requirements='the logo file the operator gave')
    V.new_version(store, RUN, sess, change(d, edit), USER, [], answers='E2')
    assert cards(store, sess) == [] and sess['accepted']['G2']['quote'] == 'Use the client logo'


def test_a_change_larger_than_what_the_question_names_brings_the_card_as_before():
    store, sess, d = film()
    q = answered(sess, 'D2')
    new = change(d, lambda s, _: (s['D2'].update(purpose='the closing card'), s['D1'].update(purpose='also changed')))
    out = V.new_version(store, RUN, sess, new, USER, [], answers='D2')
    assert cards(store, sess) == ['G1'] and sorted(sess['accepted']) == ['G2']           # D2's gap goes with the answer; D1's gap is asked
    assert out['asked_beyond'] == ['G1'] and q['plan_version'] == 2
    store, sess, d = film()
    answered(sess, 'D2')
    shared = change(d, lambda s, new: (s['D2'].update(purpose='the closing card'), new['foundation'].update(appearance='cool daylight')))
    V.new_version(store, RUN, sess, shared, USER, [], answers='D2')
    assert sess['accepted'] == {} and sorted(sess['shared_pending']) == ['G1', 'G2']     # the part every gap shares changed: the one shared question, as before
    assert cards(store, sess) == [V.shared_digest(shared)[:10]]


def test_an_answer_is_needed_and_a_refused_plan_keeps_it(monkeypatch):
    store, sess, d = film()
    with pytest.raises(ValueError, match='No answered question on D2 waits for its plan change'):
        V.new_version(store, RUN, sess, change(d, lambda s, _: s['D2'].update(purpose='x')), USER, [], answers='D2')   # never asked, or still open
    assert len(sess['versions']) == 1
    q = answered(sess, 'D2')
    sess['treatment'] = {'gaps': []}
    monkeypatch.setattr(V, 'session_of', lambda *a, **k: sess)
    monkeypatch.setattr(V, 'ensure_timing', lambda *a, **k: None)
    monkeypatch.setattr(V, '_with_direction', lambda s, document: document)
    monkeypatch.setattr(V, 'film_frames', lambda outputs: 0)
    monkeypatch.setattr(V, 'media_clips', lambda outputs: [])
    monkeypatch.setattr(V, 'save_session', lambda *a, **k: None)

    def bad(*a, **k):
        raise ValueError('shot D2: the plan is not valid')
    monkeypatch.setattr(V, 'validate_plan', bad)
    with pytest.raises(Problem, match='the plan is not valid'):
        V.propose(FakeConn(), store, USER, RUN, [], {}, answers='D2')
    assert 'plan_version' not in q and sess['answered'] == [q]                           # the answer is kept; the refusal is said


def test_the_proposal_logs_the_answer_as_the_operators_decision_and_the_quiet_changes_as_the_assistants(monkeypatch):
    store, sess, d = film(change(doc(), lambda s, _: s['D1'].update(drawing_spec={'label': 'Illustrative, not to scale', 'illustrative': True})))
    answered(sess, 'D2')
    sess['treatment'] = {'gaps': []}
    new = change(d, lambda s, _: (s['D2'].update(purpose='the closing card with the client logo'), s['D1'].update(carries_text=False)))
    for name, fn in (('session_of', lambda *a, **k: sess), ('ensure_timing', lambda *a, **k: None), ('_with_direction', lambda s, document: document),
                     ('validate_plan', lambda *a, **k: (new, [])), ('film_frames', lambda outputs: 0), ('media_clips', lambda outputs: []), ('_ways_departed', lambda s, p: []),
                     ('carried_warnings', lambda *a, **k: []), ('palette_due', lambda *a, **k: []), ('save_session', lambda *a, **k: None), ('routes', lambda *a, **k: {}),
                     ('plan_log', lambda *a, **k: [])):
        monkeypatch.setattr(V, name, fn)
    conn = FakeConn()
    out = V.propose(conn, store, {**USER, 'name': 'Asha'}, RUN, [], {}, answers='D2')
    rows = [p for sql, p in conn.sql if 'insert into vw2_log' in sql]
    by = {r[3]: r for r in rows}                                                         # (run, stage, kind, about, rule, entry, by_kind, by_name, quote, request)
    assert by['gap G2'][2] == 'decision' and by['gap G2'][6:9] == ('operator', 'Asha', 'Use the client logo')
    assert by['gap G2'][5].startswith('the plan change that follows the operator\'s answer on D2 ("Which logo closes the film?"): ') and 'accepted with that answer, no second question' in by['gap G2'][5]
    assert by['gap G1'][6] == 'assistant' and by['gap G1'][5] == 'D1: ' + V.QUIET['no_text'] and by['gap G1'][4] == 'visual plan v2'
    assert out['kept_without_asking'] == ["gap G1: D1: " + V.QUIET['no_text'], "gap G2: accepted with the operator's answer on D2"]
    assert json.dumps(out)                                                               # plain JSON, for the receipt
