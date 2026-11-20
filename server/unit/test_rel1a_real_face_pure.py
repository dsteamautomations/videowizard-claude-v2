"""Release 1, section A (SK, 20 Nov 2026), row A7: "a real face" and the operator's permission, once per person.

A made picture may match a person of the film's own approved references. The operator's permission for a real person of the footage is the
record that exists since design/207 and design/213 (`session['likeness'][person]`: their words, who, when; asked on one card at step 1 of the
references, logged as the operator's decision): nothing new is recorded. With it, the line of Claude's list for a picture of a shot that shows
this person asks only that no other real face from the footage is shown; a match with the permitted person is not a fault. Without it (the
operator said stand-in) the line stays as it was for that person. A made character has no footage behind it: matching the film's own made
references is never a fault. A person of the footage nobody was asked about is said in the next step, to be asked once. Without a database."""
import pytest

from app import image_check as IC, pictures as P, ref_sets as RS
from test_design217_server_pure import NOW, RUN, USER, held, ref, session, shot   # noqa: F401 (held: the fixture)
from test_design222_takes_pure import guide
from test_design222_takes_pure import session as take_session

STAMP = {'quote': 'Her mother agreed in writing.', 'by': 'u1', 'at': NOW.isoformat()}
BASE = "no face that matches a real person in the footage pictures sent as references; a face that matches the film's own made references is never a fault"


def plan(*people, sid='S1'):
    sh = {**shot(sid), 'subjects': [{'element_id': p, 'role': 'primary'} for p in people]}
    return {'foundation': {}, 'elements': [{'id': 'GIRL', 'kind': 'person', 'name': 'the girl'}, {'id': 'MASON', 'kind': 'person', 'name': 'the mason'},
                                           {'id': 'ROOM', 'kind': 'place', 'name': 'the room'}],
            'gaps': [{'gap_id': '8', 'title': 'Homes that last', 'scenes': [{'id': 'sc1', 'shots': [sh]}]}]}


def face(s, p, r):
    return next(l for l in P.lines(s, p, r) if l['check'] == 'a real face')


def test_a_made_character_is_never_a_fault_and_the_line_says_whose_face_it_is_about():
    s, p = session(ref('k1')), plan('GIRL')
    assert face(s, p, s['references']['k1'])['pass_when'] == BASE                                 # no permission recorded, no footage person named: the film's own made references are not a fault
    assert [l['check'] for l in P.lines(s, p, s['references']['k1'])].count('a real face') == 1
    assert [l for l in IC.FIXED if l['check'] == 'a real face'][0]['pass_when'] == 'no face that matches a person in the footage frames sent as references'   # the model's line (footage pictures, older films): untouched


def test_with_the_operators_permission_a_match_with_that_person_is_not_a_fault_and_only_another_real_face_is(held):
    s, p = session(ref('k1')), plan('GIRL', 'MASON')
    s['likeness'] = {'GIRL': STAMP}
    line = face(s, p, s['references']['k1'])
    assert line['pass_when'] == ('no face that matches a real person in the footage pictures sent as references, other than the girl, whom the operator has permitted the film '
                                 "to show: a match with the girl is not a fault; a face that matches the film's own made references is never a fault")
    assert 'the mason' not in line['pass_when']                                                   # two people in one picture, one permitted and one not: only the permitted one is named
    s['likeness']['MASON'] = STAMP
    assert 'other than the girl and the mason, whom' in face(s, p, s['references']['k1'])['pass_when']
    assert face(s, plan('MASON'), s['references']['k1'])['pass_when'].count('the girl') == 0      # a picture that does not show her does not name her
    assert set(s['likeness']['GIRL']) == {'quote', 'by', 'at'}                                    # the record: the operator's words, who, when (visuals_stage.likeness writes it and logs it)


def test_after_no_the_line_stays_as_it_was_and_a_rejected_reference_does_not_take_the_permission_away():
    s, p = session(ref('k1'), ref('sheet1', 'sheet', None, status='rejected', element_id='GIRL')), plan('GIRL')
    s['likeness'] = {'GIRL': STAMP}
    assert 'other than the girl' in face(s, p, s['references']['k1'])['pass_when']                # the permission is for the person, not for one reference
    s['likeness'].pop('GIRL')
    s['stand_in'] = {'GIRL': STAMP}                                                               # the operator said no: a stand-in (visuals_stage.likeness, stand_in)
    assert face(s, p, s['references']['k1'])['pass_when'] == BASE


def test_the_line_of_step_7s_still_is_the_same_line():
    s = take_session()
    s['guides'].update(S1=guide(still='candidate'))
    s['likeness'] = {'GIRL': STAMP}
    p = plan('GIRL')
    sh = p['gaps'][0]['scenes'][0]['shots'][0]
    lines = P.start_lines(s, p, {**sh, 'element_ids': ['GIRL']}, s['guides']['S1']['stills'][0])
    assert 'other than the girl' in [l['pass_when'] for l in lines if l['check'] == 'a real face'][0]
    assert [l['pass_when'] for l in lines if l['check'] == 'a real face'] == [face(session(ref('k1')) | {'likeness': {'GIRL': STAMP}}, p, ref('k1'))['pass_when']]


def test_a_remade_picture_and_the_look_instructions_carry_it():
    s, p = session(ref('k1', status='rejected'), ref('k2', fix_of='k1')), plan('GIRL')
    s['likeness'] = {'GIRL': STAMP}
    assert [l['pass_when'] for l in P.lines(s, p, s['references']['k2']) if l['check'] == 'a real face'] == [face(s, p, s['references']['k1'])['pass_when']]   # once, the same
    how = ' '.join(P.LOOK_HOW['judge'])
    assert 'unless its line names that person as permitted' in how and "the film's own made references is never a fault" in how


def test_a_person_of_the_footage_nobody_was_asked_about_is_asked_once_when_their_first_look_is_due(held, monkeypatch):
    s, p = session(ref('k1')), plan('GIRL', 'MASON')
    held(s, p)
    state = {'GIRL': 'ask', 'MASON': None}                                                         # the footage shows her face and no answer is recorded; the mason is a made character
    monkeypatch.setattr(RS, 'footage_person', lambda s_, p_, eid: {'faces': ['f1'] if state.get(eid) else [], 'child': False, 'state': state.get(eid)})
    said = P.waits_words(s, p)
    assert P.W['face_ask'].format(name='the girl', eid='GIRL') in said and 'MASON' not in said and said.count('GIRL') == 2
    assert 'ask the operator once' in said and '`vw visuals likeness --element GIRL --quote' in said and '--stand-in' in said
    assert 'a real face' in [l['check'] for l in P.lines(s, p, s['references']['k1'])]            # until then the warning shows, as before
    state['GIRL'] = 'permitted'
    assert 'GIRL' not in P.waits_words(s, p)                                                      # recorded: never asked again
    state['GIRL'] = 'stand_in'
    assert 'GIRL' not in P.waits_words(s, p)
    state['GIRL'] = 'ask'
    s['references']['k1']['look'] = {'sha256': 'a' * 64, 'lines': []}
    assert P.waits_words(s, p) == ''                                                              # no picture of her waits for its look: nothing is said
