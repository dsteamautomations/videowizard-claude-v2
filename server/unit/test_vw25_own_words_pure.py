"""VW-25 issue 11 (SK, 25 Nov 2026: "agreed"): the comment the operator writes with their own picture is used. It is logged with the answer;
where a set is made from the picture (a person, a thing with approved drawings) it is "The operator's words" of the set's request, and it
stays with the thing through a make that fails; where the picture is the reference itself (no set) it is kept as the thing's correction
(`thing_corrections`, design/215), which every later picture of the thing carries. The chat gives the words through the same server function
(`visuals_stage.supply_own(words=…)`, `vw visuals own --words`).

Before: the words were dropped at step 2 for a person (`set_make(…, quote=label)`), at step 2 for a thing (`use:<picture>` with ''), and at
step 1 wherever no set was made. The real modules run, on the film of design/211. Without a database."""
import pytest

from app import chat_flow as CF, page_flow as P, ref_sets as RS, visuals_stage as VS
from app.main import OwnPicture
from test_design211_together_pure import USER, ans, at_step_1, outside   # noqa: F401 (outside: on every test)
from test_vw25_own_pictures_pure import at_step_2, give, mine, others, own, permitted

SAID = 'He wears the cap low over the eyes.'
CREAM = 'The dial is cream, not white.'


@pytest.fixture(autouse=True)
def _v2_round(monkeypatch, _older_round_tests):
    monkeypatch.setattr(VS, 'ROUND_V', 2)


def thing(film, eid):
    return next(e for e in film.plan['elements'] if e['id'] == eid)


def request(film, eid):
    """The request of the thing's set, as the next make sends it."""
    s = film.session()
    return RS.set_request(film.plan, film.run, s, thing(film, eid), s['round']['elements'][eid])


def kept(film, eid):
    return RS.corrections_of(film.session(), film.plan, eid)


def logged(film):
    return [str(p[8]) for sql, p in film.conn.sql if 'vw2_log' in sql]   # the words of each log line


def says(film, eid, words):
    r = request(film, eid)
    return r['parts']['operator'] == words and RS.OPERATOR_LINE.format(words=words) in r['prompt']


# ---------- step 1 ----------

def test_step_1_a_persons_photo_with_words_the_words_are_the_operators_words_of_the_set():
    film, _ = at_step_1()
    permitted(film)
    photo = give(film, 'MASON')['id']
    l = film.lines()
    out = film.record(own(l['ref:MASON'], [photo], notes=SAID), *others(l))
    assert out['refused'] == [] and 'MASON' in film.ordered() and film.row('MASON')['operator_words'] == [SAID]
    assert says(film, 'MASON', SAID) and [i['role'] for i in request(film, 'MASON')['inputs']] == ['photo']
    assert any(x.endswith(': ' + SAID) for x in logged(film)) and kept(film, 'MASON') == []   # logged with the answer; said once, in its own place


def test_step_1_a_thing_whose_own_picture_is_the_reference_keeps_the_words_as_its_correction():
    film, _ = at_step_1()
    l = film.lines()
    a = give(film, 'BRICK')['id']
    out = film.record(own(l['ref:BRICK'], [a], notes='The brick is hand made, with a rough face.'), *others(l, 'ref:BRICK'))
    s = film.session()
    assert out['refused'] == [] and s['round']['elements']['BRICK']['from_footage'] and 'BRICK' not in film.ordered()   # no set: the picture is the reference
    assert kept(film, 'BRICK') == ['The brick is hand made, with a rough face.'] and s['thing_corrections']['BRICK'][0]['by'] == USER['id']
    assert 'hand made, with a rough face' in VS.with_corrections(s, film.plan, 'A wall of brick in the sun.', ['BRICK'])   # every later picture of the thing carries them
    assert any(x.endswith(': The brick is hand made, with a rough face.') for x in logged(film))


def test_step_1_a_thing_with_drawings_gets_its_set_from_the_picture_with_the_words():
    film, _ = at_step_1()
    l = film.lines()
    a = give(film, 'TILE')['id']
    out = film.record(own(l['ref:TILE'], [a], notes='The tile is darker at the edge.'), *others(l, 'ref:TILE'))
    assert out['refused'] == [] and film.row('TILE')['operator_words'] == ['The tile is darker at the edge.'] and not film.row('TILE').get('from_footage')
    assert says(film, 'TILE', 'The tile is darker at the edge.') and a in [i['ref'] for i in request(film, 'TILE')['inputs']]


def test_three_pictures_and_one_comment_are_one_comment_for_the_line():
    film, _ = at_step_1()
    l = film.lines()
    refs = [give(film, 'BRICK', k)['id'] for k in ('green', 'blue', 'red')]
    out = film.record(own(l['ref:BRICK'], refs, notes=CREAM), *others(l, 'ref:BRICK'))
    assert out['refused'] == [] and kept(film, 'BRICK') == [CREAM] and len([x for x in logged(film) if CREAM in x]) == 1


# ---------- step 2 ----------

def test_step_2_a_persons_photo_with_words_the_set_is_made_again_with_the_words():
    film = at_step_2()
    permitted(film)
    photo = give(film, 'MASON')['id']
    n = len(film.ordered())
    l = film.lines()
    out = film.record(own(l['set:MASON'], [photo], notes=SAID))
    assert out['refused'] == [] and film.ordered()[n:] == ['MASON'] and film.row('MASON')['operator_words'][-1] == SAID   # before: the words were dropped here
    assert says(film, 'MASON', SAID) and request(film, 'MASON')['inputs'][0]['ref'] == photo
    assert l['set:MASON']['own']['label'] + ': ' + SAID in logged(film)


def test_step_2_a_thing_whose_own_picture_becomes_the_reference_keeps_the_words_as_its_correction():
    film = at_step_2()
    a = give(film, 'STREET')['id']
    l = film.lines()
    out = film.record(own(l['set:STREET'], [a], notes='The street is narrower than in these pictures.'))
    s = film.session()
    assert out['refused'] == [] and out['recorded'] == ['set:STREET'] and s['golden']['STREET'] == a
    assert kept(film, 'STREET') == ['The street is narrower than in these pictures.'] and s['thing_corrections']['STREET'][0]['set'] == film.row('STREET')['set']
    assert 'The street is narrower than in these pictures.' not in film.row('STREET')['operator_words']
    assert l['set:STREET']['own']['label'] + ': The street is narrower than in these pictures.' in logged(film)
    assert 'narrower than in these pictures' in VS.with_corrections(s, film.plan, 'The street at noon.', ['STREET'])   # every later picture of the thing carries them


def test_step_2_a_thing_whose_set_was_not_made_keeps_the_words_too():
    film, _ = at_step_1()
    l = film.lines()
    film.record(*others(l))
    film.back(fail=('STREET',))
    film.set_looks()
    line = film.lines()['set:STREET']                                          # the line as the operator answered it: its set did not come back
    a = give(film, 'STREET')['id']                                             # the tool hands the picture over first: it is the reference at once (F2, E3)
    assert film.row('STREET')['own'] is True and film.session()['golden']['STREET'] == a
    for _ in range(2):                                                         # the same answer sent twice keeps the words once
        out = film.record(own(line, [a], notes=CREAM))
        assert out['refused'] == [] and out['recorded'] == ['set:STREET']
    assert kept(film, 'STREET') == [CREAM]


# ---------- no words; later words; another language ----------

def test_with_no_words_nothing_is_added():
    film = at_step_2()
    permitted(film)
    photo, a = give(film, 'MASON')['id'], give(film, 'STREET')['id']
    l = film.lines()
    out = film.record(own(l['set:MASON'], [photo]), own(l['set:STREET'], [a]))
    s = film.session()
    assert out['refused'] == [] and s['round']['elements']['MASON']['operator_words'] == [] and 'thing_corrections' not in s
    assert request(film, 'MASON')['parts']['operator'] == '' and "The operator's words" not in request(film, 'MASON')['prompt']
    assert l['set:MASON']['own']['label'] in logged(film)


def test_words_that_contradict_an_earlier_correction_the_later_one_wins():
    film = at_step_2()
    s = film.session()
    RS.correction_kept(s, USER, 'STREET', 'The street is paved with stone.', None)
    VS.save_session(film.store, film.run, s)
    a = give(film, 'STREET')['id']
    film.record(own(film.lines()['set:STREET'], [a], notes='The street is bare earth, not paved.'))
    assert kept(film, 'STREET') == ['The street is paved with stone.', 'The street is bare earth, not paved.']
    assert RS.corrections_shown(film.session(), film.plan, 'STREET')[-1] == RS.CORRECTION_LATER.format(words='The street is bare earth, not paved.')
    # a person: the later words are the ones the request says
    permitted(film)
    photo = give(film, 'MASON')['id']
    film.record(own(film.lines()['set:MASON'], [photo], notes='A thick moustache.'))
    film.do(lambda: VS.supply_own(film.conn, film.store, USER, film.run, film.outputs, 'MASON', content=_png('blue'), name='later.png', words='No moustache: he is clean shaven.'))
    assert film.row('MASON')['operator_words'][-2:] == ['A thick moustache.', 'No moustache: he is clean shaven.'] and says(film, 'MASON', 'No moustache: he is clean shaven.')


def _png(colour):
    from test_vw25_own_pictures_pure import png
    return png(colour)


@pytest.mark.parametrize('words', ['தெரு இதைவிட குறுகலானது.', 'गली इससे पतली है, और कच्ची है।'])
def test_words_in_another_language_are_kept_as_written(words):
    film = at_step_2()
    a = give(film, 'STREET')['id']
    out = film.record(own(film.lines()['set:STREET'], [a], notes=words))
    assert out['refused'] == [] and kept(film, 'STREET') == [words] and any(x.endswith(': ' + words) for x in logged(film))


def test_words_that_cannot_be_kept_for_every_picture_refuse_the_line_with_the_reason_and_record_nothing():
    film = at_step_2()
    a = give(film, 'STREET')['id']
    l = film.lines()
    out = film.record(own(l['set:STREET'], [a], notes='Put the logo of the brand on the wall.'), ans(l['set:T_LAY'], 'no'))
    assert [r['key'] for r in out['refused']] == ['set:STREET'] and out['refused'][0]['message'].startswith(VS.OWN_WORDS_REFUSED.split('{')[0]) and 'logo' in out['refused'][0]['message']
    assert out['recorded'] == ['set:T_LAY'] and kept(film, 'STREET') == [] and 'STREET' not in film.session()['golden']
    out = film.record(own(film.lines()['set:STREET'], [a], notes='The wall is bare.'))      # written again without it: taken
    assert out['refused'] == [] and kept(film, 'STREET') == ['The wall is bare.']


# ---------- a make that fails keeps the words ----------

def test_a_make_that_is_refused_before_the_call_keeps_the_words_for_the_next_make(monkeypatch):
    film = at_step_2()
    permitted(film)
    photo = give(film, 'MASON')['id']
    n, real = len(film.ordered()), VS._queue_sets
    monkeypatch.setattr(VS, '_queue_sets', lambda *a, **k: ([], {'MASON': 'the picture service did not answer in time'}))
    out = film.record(own(film.lines()['set:MASON'], [photo], notes=SAID))
    assert [r['key'] for r in out['refused']] == ['set:MASON'] and 'did not answer in time' in out['refused'][0]['message'] and len(film.ordered()) == n
    assert film.row('MASON')['operator_words'][-1] == SAID and says(film, 'MASON', SAID)      # stored with the thing, though nothing was made
    monkeypatch.setattr(VS, '_queue_sets', real)
    out = film.record(own(film.lines()['set:MASON'], [photo]))                                 # asked again, the words not typed again
    assert out['refused'] == [] and film.ordered()[n:] == ['MASON'] and film.row('MASON')['operator_words'].count(SAID) == 1 and says(film, 'MASON', SAID)


def test_a_make_that_comes_back_with_no_picture_keeps_the_words_for_the_next_make():
    film = at_step_2()
    permitted(film)
    photo = give(film, 'MASON')['id']
    film.record(own(film.lines()['set:MASON'], [photo], notes=SAID))
    n = len(film.ordered())
    film.back(fail=('MASON',))                                                 # the model refused: no picture came back
    assert film.row('MASON')['operator_words'][-1] == SAID
    assert film.lines()['set:MASON']['head'] == "The picture service refused this person's photo."   # the line asks for another photo, in the chat
    other = film.do(lambda: VS.supply_own(film.conn, film.store, USER, film.run, film.outputs, 'MASON', content=_png('blue'), name='another.png'))['id']
    out = film.do(lambda: VS.set_make(film.conn, film.store, USER, film.run, film.outputs, 'MASON', quote='Make it from this photo.'))
    assert out['queued'] is True and film.ordered()[n:] == ['MASON'] and film.row('MASON')['operator_words'] == [SAID]
    assert says(film, 'MASON', SAID) and request(film, 'MASON')['inputs'][0]['ref'] == other   # the next make says them; the operator did not type them again


# ---------- the chat: the same server function ----------

def test_the_chat_gives_the_words_with_the_picture_through_the_same_function():
    film, _ = at_step_1()
    out = give(film, 'BRICK', 'green', 'kiln side.jpg', words=CREAM)           # a thing with no drawings: its own picture is the reference, the words its correction
    assert kept(film, 'BRICK') == [CREAM] and CREAM in logged(film) and '1 of 3' in out['next']
    give(film, 'BRICK', 'green', 'kiln side.jpg', words=CREAM)                 # the same picture and the same words again: once
    assert kept(film, 'BRICK') == [CREAM] and len(mine(film, 'BRICK')) == 1
    give(film, 'TILE', 'green', words='The tile is darker at the edge.')       # approved drawings: a set is made from the picture, with the words
    assert film.row('TILE')['operator_words'] == ['The tile is darker at the edge.'] and kept(film, 'TILE') == []
    permitted(film)
    give(film, 'MASON', 'green', words=SAID)                                   # a person: the words of the set
    assert film.row('MASON')['operator_words'] == [SAID] and kept(film, 'MASON') == []
    assert give(film, 'FAN', 'green')['id'] and kept(film, 'FAN') == [] and film.row('FAN')['operator_words'] == []   # no words: as before
    said = film.refused(lambda: VS.supply_own(film.conn, film.store, USER, film.run, film.outputs, 'FAN', content=_png('blue'), name='b.png', words='Add the logo of the maker.'))
    assert said.startswith(VS.OWN_WORDS_REFUSED.split('{')[0]) and len(mine(film, 'FAN')) == 1   # refused before the picture is stored


def test_the_chat_before_any_round_keeps_the_words_with_the_thing():
    from test_design211_together_pure import Film
    film = Film()
    give(film, 'BRICK', words=CREAM)
    assert kept(film, 'BRICK') == [CREAM]


def test_the_words_are_300_characters_at_most_in_the_chat_door():
    assert OwnPicture(request_id='00000000-0000-0000-0000-000000000001', element_id='E', words='x' * 300).words == 'x' * 300
    with pytest.raises(ValueError):
        OwnPicture(request_id='00000000-0000-0000-0000-000000000001', element_id='E', words='x' * 301)
    assert VS.OWN_WORDS_MAX == 300 and P.OWN_PAGE['max'] == 300 and 'user' not in str(P.OWN_PAGE).lower()


def test_words_over_300_characters_in_a_page_answer_refuse_the_line_and_record_nothing():
    """The page stops at 300 characters; an answer that carries more all the same is refused by its line, in plain words."""
    film = at_step_2()
    a = give(film, 'STREET')['id']
    out = film.record(own(film.lines()['set:STREET'], [a], notes='x' * 301))
    assert [r['key'] for r in out['refused']] == ['set:STREET'] and '301' in out['refused'][0]['message'] and '300 characters at most' in out['refused'][0]['message']
    assert kept(film, 'STREET') == [] and 'STREET' not in film.session()['golden']
    out = film.record(own(film.lines()['set:STREET'], [a], notes='x' * 300))
    assert out['refused'] == [] and kept(film, 'STREET') == ['x' * 300]


def test_the_line_offers_the_words_box_with_the_own_picture_on_both_steps():
    film, _ = at_step_1()
    assert film.page()['layout']['words']['own'] == P.OWN_PAGE and film.lines()['ref:BRICK']['own']['max'] == 3
    film = at_step_2()
    l = film.lines()
    assert film.page()['layout']['words']['own'] == P.OWN_PAGE and P.OWN_PAGE['label'] and P.OWN_PAGE['only'] and P.OWN_PAGE['chars'] == '{n} of {max} characters'
    assert (l['set:MASON']['own']['max'], l['set:STREET']['own']['max']) == (1, 3)
    assert CF.WORDS['own_instead'] == l['set:STREET']['own']['label']
