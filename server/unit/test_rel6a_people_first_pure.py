"""Release 1 of 27 Nov 2026, phase 2, part A (SK approved): the permission for a real person comes first.

A real person (a person of the plan who speaks in the film) whom the footage never shows got no question at step 1 of the references: the
set was made from the description, and made again when the permission came later (VW-25). Now every real person is asked before any set
of theirs is ordered, with the two answers of before (the permission, or a stand-in); the chat asks all of them on one card; the server
refuses the set of a person with no answer in the one function that orders sets, and the other sets go on. Each test failed first.
Without a database."""
from app import chat_flow as CF, pictures as P, ref_sets as RS, visuals_stage as VS
import d211_fixture as F
from test_design211c_kit_pure import Film, RUN, USER, ans

W = CF.WORDS


def film_of(monkeypatch, speaks=('MASON',), state='1'):
    plan = F.plan()
    for e in plan['elements']:
        if e['id'] in speaks:
            e['speaker'] = True
    film = Film(monkeypatch, state, plan=plan)
    film.real = set(speaks)
    return film


def chat(film):
    return film.items(every=False)


# ---------- who is asked ----------

def test_a_film_with_no_real_person_asks_nothing_new(monkeypatch):
    film = film_of(monkeypatch, speaks=())
    assert RS.permission_waits(film.session(), film.plan) == [] and RS.people_wait(film.session(), film.plan) == ''
    assert film.lines()['ref:MASON']['case'] == 'auto'                         # a made person the footage does not show: a set at "done", as before
    assert not [i for i in chat(film) if i['id'].startswith('people:')]


def test_a_real_person_the_footage_never_shows_is_asked_all_the_same(monkeypatch):
    film = film_of(monkeypatch)
    assert RS.footage_person(film.session(), film.plan, 'MASON')['state'] == 'ask'
    m = film.lines()['ref:MASON']
    assert m['case'] == 'likeness' and m['group'] != CF.STEP1_GROUPS[4] and m['likeness'] == {'ask': W['likeness_ask_none']}
    assert 'no picture' in W['likeness_ask_none'] and 'tick' not in m          # the card says there is no picture of him; no picture has to be ticked
    assert [(b['label'], b['choice']) for b in m['buttons']] == [('I have their permission', 'permit'), ('Make a stand-in', 'standin')]
    assert RS.people_wait(film.session(), film.plan) .startswith("1 real person waits for the operator's answer (their permission, or a stand-in): The mason. No set of theirs is ordered before. Each answer is recorded")


def test_the_page_records_the_permission_of_a_person_with_no_picture(monkeypatch):
    film = film_of(monkeypatch)
    said = []
    monkeypatch.setattr(VS, 'likeness', lambda store, user, run, outputs, eid, quote, conn=None, stand_in=False: said.append((eid, quote, stand_in)))
    m = film.lines()['ref:MASON']
    assert film.record(ans(m, 'permit'))['refused'][0]['key'] == 'ref:MASON' and not said          # their own words are required, as before
    assert film.record(ans(m, 'permit', 'He agreed by phone.'))['refused'] == []                   # no picture is needed for it
    assert said == [('MASON', 'He agreed by phone.', False)] and film.session()['chat_round']['MASON']['verdict'] == 'approve'


def test_a_stand_in_for_a_person_with_no_picture_is_recorded_and_not_asked_again(monkeypatch):
    film = film_of(monkeypatch)
    VS.likeness(film.store, USER, RUN, [], 'MASON', 'Use a stand-in.', conn=film.conn, stand_in=True)
    s = film.session()
    assert s['stand_in']['MASON']['quote'] == 'Use a stand-in.' and RS.footage_person(s, film.plan, 'MASON')['state'] == 'stand_in'
    assert RS.permission_waits(s, film.plan) == [] and film.lines()['ref:MASON']['case'] == 'auto'   # his set is made from the description, as today
    assert P.faces_to_ask(s, film.plan) == []                                                      # the later question is not asked again


# ---------- the chat: one card for all ----------

def test_the_chat_asks_all_the_real_people_on_one_card_first(monkeypatch):
    film = film_of(monkeypatch)
    said = []
    monkeypatch.setattr(VS, 'likeness', lambda store, user, run, outputs, eid, quote, conn=None, stand_in=False: said.append((eid, quote, stand_in)))
    card = chat(film)[0]
    assert card['id'] == 'people:MASON' and 'The mason' in card['text'] and 'no picture' in card['text']
    assert [(b['label'], b['choice'], bool(b.get('needs_words'))) for b in card['buttons']] == [('I have their permission', 'permit_all', True), ('Make a stand-in', 'standin_all', False)]
    card['_run']('permit_all', 'I have their permission', 'He agreed by phone.')
    card['_run']('standin_all', 'Make a stand-in', '')
    assert said == [('MASON', 'He agreed by phone.', False), ('MASON', 'Make a stand-in', True)]


def test_the_card_is_gone_once_every_real_person_has_an_answer(monkeypatch):
    film = film_of(monkeypatch)
    VS.likeness(film.store, USER, RUN, [], 'MASON', 'He agreed.', conn=film.conn)
    assert not [i for i in chat(film) if i['id'].startswith('people:')]
    assert RS.people_wait(film.session(), film.plan) == ''


# ---------- the server refuses the set ----------

def test_a_persons_set_is_not_ordered_before_the_answer_and_the_other_sets_go_on(monkeypatch):
    film = film_of(monkeypatch, state='2')
    ordered = []

    def order(conn, store, user, run, outputs, body, **k):
        ordered.append(body['element_id'])
        return {'reference_id': 'new-' + body['element_id'], 'job_id': 'j'}
    monkeypatch.setattr(VS, 'generate_image', order)
    film.change(lambda s: [s['round']['elements'][e].update(set=None) for e in ('MASON', 'BRICK')])
    queued, errors = VS._queue_sets(film.conn, film.store, USER, RUN, [], ['MASON', 'BRICK'])
    assert ordered == ['BRICK'] and queued == ['BRICK']
    assert errors == {'MASON': RS.PERMISSION_FIRST.format(name='The mason', eid='MASON')}
    assert film.session()['round']['elements']['MASON']['error'] == errors['MASON']
    VS.likeness(film.store, USER, RUN, [], 'MASON', 'Use a stand-in.', conn=film.conn, stand_in=True)
    queued, errors = VS._queue_sets(film.conn, film.store, USER, RUN, [], ['MASON'])
    assert queued == ['MASON'] and not errors


# ---------- later: a person added by a plan change ----------

def test_a_real_person_who_comes_later_is_named_in_the_next_step_line_with_true_words(monkeypatch):
    film = film_of(monkeypatch)
    monkeypatch.setattr(P, '_made_shots', lambda s, plan: [sh for g in plan['gaps'] for sc in g['scenes'] for sh in sc['shots'] if sh['visual_type'] != 'footage'])   # a made shot shows him
    said = P.faces_to_ask(film.session(), film.plan)
    assert len(said) == 1 and 'The mason (MASON) is a real person' in said[0] and 'of the footage' not in said[0] and '--stand-in' in said[0]


def test_a_speaker_seen_only_in_the_camera_footage_is_not_asked(monkeypatch):
    """The self-review: no picture is made of them, so there is nothing to permit."""
    film = film_of(monkeypatch)
    for g in film.plan['gaps']:
        for sc in g['scenes']:
            for sh in sc['shots']:
                if sh['visual_type'] != 'footage' and 'MASON' in sh['element_ids']:
                    sh['element_ids'].remove('MASON')
    assert RS.footage_person(film.session(), film.plan, 'MASON')['state'] is None and RS.permission_waits(film.session(), film.plan) == []
