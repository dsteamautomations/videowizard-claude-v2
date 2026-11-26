"""VW-25 issue 10 (SK, 25 Nov 2026: "Yes, three and one"): "Use my own picture" takes up to three pictures of one thing, and one photo of a
real person. The rule lives in the server: `visuals_stage.supply_own` (the door both front ends hand a picture in by: the page's tool call
and `vw visuals own`) takes the same picture once and refuses a thing's fourth; `page_flow._round_answer` reads an own answer as a list of
pictures (`own_refs`; the older tool's one `own_ref` as a list of one), takes the same picture once and refuses the fourth by its sentence.

The real `visuals_stage`, `ref_sets`, `chat_flow` and `page_flow` run, on the film of design/211 (test_design211_together_pure): BRICK has no
footage picture and no drawing (its own picture is the reference itself), TILE has approved drawings (its set is made from the own pictures
and the drawings), MASON is a person, TROWEL has footage pictures. Every row of the note's table that the server holds has its test; the
page's own rows are in test_vw25_own_browser_pure. Without a database."""
import json

import pytest

from app import page_flow as P, ref_sets as RS, visuals_stage as VS
from app.main import OwnPicture, PageAnswer, PageAnswers
import d211_fixture as F
from test_design211_together_pure import SESSION, USER, ans, approve, at_step_1, outside   # noqa: F401 (outside: what is outside the five modules, on every test)

COLOURS = ('green', 'blue', 'red', 'yellow', 'purple')


@pytest.fixture(autouse=True)
def _v2_round(monkeypatch, _older_round_tests):   # conftest: a module not named test_design211* posts an older round; these post the round of today
    monkeypatch.setattr(VS, 'ROUND_V', 2)


def png(colour):
    import io
    from PIL import Image
    out = io.BytesIO()
    Image.new('RGB', (64, 48), colour).save(out, 'PNG')
    return out.getvalue()


def give(film, eid, colour='green', name=None, **more):
    """One own picture handed to the server, as `vw visuals own` and the page's tool call do."""
    return film.do(lambda: VS.supply_own(film.conn, film.store, USER, film.run, film.outputs, eid, content=png(colour), name=name or f'{colour}.png', **more))


def own(line, refs=(), notes='', **more):
    """The page's own answer to a line, as `vw visuals page --record` sends it: it passes the server's own model."""
    return PageAnswer(line=line['line'], key=line['key'], item=line.get('item', ''), choice='own', notes=notes, own_refs=list(refs), **more).model_dump()


def mine(film, eid):
    s = film.session()
    return sorted(VS._own_pictures(s, eid), key=lambda r: s['references'][r]['created_at'])


def others(l, *but):
    """An answer for every other thing of step 1, so that the step is recorded: the proposals accepted, the rest left out."""
    return [ans(l[k], 'ignore') for k in ('ref:TROWEL', 'ref:FAN', 'ref:BRICK', 'ref:TILE') if k not in but] + [ans(l['refs:proposals'], 'accept_all')]


def at_step_2():
    """Step 1 recorded and the first three sets back and looked at: MASON, STREET and T_LAY wait for the operator's answer."""
    film, _ = at_step_1()
    l = film.lines()
    film.record(*others(l))
    film.back()
    film.set_looks()
    assert film.state() == 2
    return film


# ---------- one, three and four pictures ----------

def test_one_own_picture_of_a_thing_is_its_reference_as_before():
    film, _ = at_step_1()
    l = film.lines()
    a = give(film, 'BRICK')['id']
    out = film.record(own(l['ref:BRICK'], [a]), *others(l, 'ref:BRICK'))
    s = film.session()
    assert out['refused'] == [] and 'ref:BRICK' in out['recorded'] and s['golden']['BRICK'] == a
    assert s['round']['elements']['BRICK']['from_footage'] and s['round']['elements']['BRICK']['own'] is True and 'BRICK' not in film.ordered()   # no set is made of it


def test_three_own_pictures_of_a_thing_are_taken_and_the_first_is_the_one_pictures_start_from():
    film, _ = at_step_1()
    l = film.lines()
    a, b, c = (give(film, 'BRICK', k)['id'] for k in COLOURS[:3])
    out = film.record(own(l['ref:BRICK'], [a, b, c]), *others(l, 'ref:BRICK'))
    s = film.session()
    assert out['refused'] == [] and 'ref:BRICK' in out['recorded']
    assert mine(film, 'BRICK') == [a, b, c] and all(s['references'][r]['status'] == 'approved' for r in (a, b, c))
    assert s['golden']['BRICK'] == a and s['round']['elements']['BRICK']['own'] is True


def test_a_thing_with_drawings_gets_its_set_from_all_three_own_pictures():
    film, _ = at_step_1()
    l = film.lines()
    a, b, c = (give(film, 'TILE', k)['id'] for k in COLOURS[:3])
    out = film.record(own(l['ref:TILE'], [a, b, c]), *others(l, 'ref:TILE'))
    s = film.session()
    assert out['refused'] == [] and not s['round']['elements']['TILE'].get('from_footage')
    tile = next(e for e in film.plan['elements'] if e['id'] == 'TILE')
    given = [i['ref'] for i in RS.inputs_of(s, tile)[0] if i['role'] == 'footage']
    assert sorted(given) == sorted([a, b, c])   # the set's request takes the three; the footage picture was set aside for them


def test_the_server_refuses_a_things_fourth_own_picture_in_the_notes_sentence():
    film, _ = at_step_1()
    for k in COLOURS[:3]:
        give(film, 'BRICK', k)
    said = film.refused(lambda: VS.supply_own(film.conn, film.store, USER, film.run, film.outputs, 'BRICK', content=png('yellow'), name='fourth.png'))
    assert said.startswith('Three pictures at most. Remove one first') and VS._plain(said) == VS.OWN_MOST == 'Three pictures at most. Remove one first.'
    assert '`vw visuals reject --ref' in said                                  # how the assistant removes one, in the chat
    assert len(mine(film, 'BRICK')) == 3                                       # nothing of the fourth is stored
    # one of the three removed: the next one is taken
    first = mine(film, 'BRICK')[0]
    film.do(lambda: VS.reject_reference(film.store, USER, film.run, film.outputs, first, '', 'Not this one.'))
    assert give(film, 'BRICK', 'yellow')['id'] in mine(film, 'BRICK') and len(mine(film, 'BRICK')) == 3


def test_an_answer_that_names_four_pictures_is_refused_on_its_line_and_the_others_are_recorded():
    film, _ = at_step_1()
    l = film.lines()
    refs = [give(film, 'BRICK', k)['id'] for k in COLOURS[:3]]
    s = film.session()   # a fourth picture of the thing, stored before the limit was there
    s['references']['own-4'] = {**s['references'][refs[0]], 'id': 'own-4', 'sha256': 'x' * 64}
    film.store.files[SESSION] = json.dumps(s).encode('utf-8')
    out = film.record(own(l['ref:BRICK'], refs + ['own-4']), ans(l['ref:FAN'], 'ignore'))
    assert out['refused'] == [{'key': 'ref:BRICK', 'message': 'Three pictures at most. Remove one first.'}] and out['kept'] == ['ref:FAN']
    assert film.lines()['ref:BRICK']['refused'] == 'Three pictures at most. Remove one first.'


# ---------- the same picture twice ----------

def test_the_same_picture_given_twice_is_stored_once():
    film, _ = at_step_1()
    a = give(film, 'BRICK', 'green', 'first.png')
    again = give(film, 'BRICK', 'green', 'the same again.png')
    assert again['id'] == a['id'] and again['duplicate'] is True and mine(film, 'BRICK') == [a['id']]
    assert 'already' in again['next'] and 'once' in again['next']
    assert give(film, 'TILE', 'green')['id'] != a['id']                        # the same file for another thing is that thing's picture


def test_an_answer_that_names_the_same_picture_twice_takes_it_once():
    film, _ = at_step_1()
    l = film.lines()
    a, b = give(film, 'BRICK', 'green')['id'], give(film, 'BRICK', 'blue')['id']
    out = film.record(own(l['ref:BRICK'], [a, a, b, a]), *others(l, 'ref:BRICK'))   # four entries, two pictures: not a fourth
    assert out['refused'] == [] and 'ref:BRICK' in out['recorded'] and film.session()['golden']['BRICK'] == a


# ---------- one failed among three ----------

def test_one_picture_that_failed_among_three_refuses_the_line_by_its_reason_and_the_other_two_stay():
    film, _ = at_step_1()
    l = film.lines()
    a, b = give(film, 'BRICK', 'green', 'front.png')['id'], give(film, 'BRICK', 'blue', 'side.png')['id']
    out = film.record(own(l['ref:BRICK'], [a, b], own_error='top.heic: the file is not a PNG, JPEG or WebP picture'), ans(l['ref:FAN'], 'ignore'), ans(l['ref:TILE'], 'ignore'))
    assert out['refused'] == [{'key': 'ref:BRICK', 'message': 'Your own picture was not used: top.heic: the file is not a PNG, JPEG or WebP picture'}]
    assert out['kept'] == ['ref:FAN', 'ref:TILE'] and out['stale'] == []       # every other answer of the page is taken; nothing is asked again
    brick = film.lines()['ref:BRICK']
    assert brick['refused'].endswith('top.heic: the file is not a PNG, JPEG or WebP picture')
    assert mine(film, 'BRICK') == [a, b]                                       # the other two stay with the server
    assert 'Given already: front.png, side.png (2 of 3).' in brick['own']['text']   # and the line names them
    # the server's own refusal of a picture reaches the line without the tool's command in it
    out = film.record(own(brick, [a, b], own_error='fourth.png: ' + VS.OWN_MOST[:-1] + ' (`vw visuals reject --ref <picture> --quote "<the operator\'s words>"`).'))
    assert out['refused'][0]['message'] == 'Your own picture was not used: fourth.png: Three pictures at most. Remove one first.'


def test_an_own_answer_with_no_picture_that_reached_the_server_is_refused_on_its_line():
    film, _ = at_step_1()
    l = film.lines()
    out = film.record(own(l['ref:BRICK'], [], notes='Only a comment, no picture.'), ans(l['ref:FAN'], 'ignore'))
    assert out['refused'] == [{'key': 'ref:BRICK', 'message': P.OWN_MISSING}] and out['kept'] == ['ref:FAN']
    other = give(film, 'TILE')['id']
    out = film.record(own(film.lines()['ref:BRICK'], [other]))                 # a picture of another thing
    assert out['refused'][0]['message'] == P.OWN_MISSING


# ---------- the older single-object shape ----------

def test_the_older_tools_one_own_ref_is_read_as_a_list_of_one():
    film, _ = at_step_1()
    l = film.lines()
    a = give(film, 'BRICK')['id']
    older = PageAnswer(line=l['ref:BRICK']['line'], key='ref:BRICK', item=l['ref:BRICK']['item'], choice='own', own_ref=a).model_dump()
    assert older['own_refs'] == []
    out = film.record(older, *others(l, 'ref:BRICK'))
    assert out['refused'] == [] and 'ref:BRICK' in out['recorded'] and film.session()['golden']['BRICK'] == a


def test_the_servers_models_take_the_list_and_refuse_nothing_by_shape_that_a_sentence_must_refuse():
    a = PageAnswer(key='ref:E', choice='own', own_refs=['a', 'b', 'c', 'd'])   # the fourth is refused by its sentence, on its line, never as a broken request
    assert a.own_refs == ['a', 'b', 'c', 'd'] and a.own_ref == ''
    assert PageAnswers(request_id='00000000-0000-0000-0000-000000000001', answers=[a]).answers[0].own_refs[3] == 'd'
    with pytest.raises(ValueError):
        PageAnswer(key='ref:E', choice='own', own_refs=['x'] * 9)
    assert OwnPicture(request_id='00000000-0000-0000-0000-000000000001', element_id='E').words == ''


# ---------- a real person keeps one photo ----------

def permitted(film, eid='MASON'):
    return film.do(lambda: VS.likeness(film.store, USER, film.run, film.outputs, eid, 'He agreed that we use his photo.', conn=film.conn))


def test_a_person_keeps_one_photo_a_later_one_takes_its_place_and_two_in_one_answer_are_refused():
    film, _ = at_step_1()
    permitted(film)
    a, b = give(film, 'MASON', 'green')['id'], give(film, 'MASON', 'blue')['id']   # a later photo is never refused: it replaces the earlier one, as before
    assert VS.likeness_photo(film.session(), 'MASON') == b
    for k in COLOURS[2:]:
        give(film, 'MASON', k)                                                # no limit of three for a person's photos
    l = film.lines()
    out = film.record(own(l['ref:MASON'], [a, b]), ans(l['ref:FAN'], 'ignore'))
    assert out['refused'] == [{'key': 'ref:MASON', 'message': 'One photo of a person at most. Remove one first.'}] and out['kept'] == ['ref:FAN']
    out = film.record(own(film.lines()['ref:MASON'], [b]))
    assert out['refused'] == [] and out['kept'] == ['ref:MASON']


# ---------- what the box says before the upload ----------

def test_the_box_says_three_for_a_thing_one_for_a_person_and_carries_the_refusal_sentence():
    film, _ = at_step_1()
    l = film.lines()
    brick, mason, said = l['ref:BRICK']['own'], l['ref:MASON']['own'], film.page()['layout']['words']['own']
    assert said == P.OWN_PAGE and (said['most'], said['one']) == ('Three pictures at most. Remove one first.', 'One photo of a person at most. Remove one first.')
    assert said['count'].startswith('Up to three pictures of this thing') and said['count_one'].startswith('One photo of this person') and said['again'] == 'Try again'
    assert brick['max'] == 3 and (mason['max'], mason['person']) == (1, True) and 'three' not in mason['text'].lower()   # said once, with the layout: 60 things stay one document
    assert 'Given already' not in brick['text']
    give(film, 'BRICK', 'green', 'kiln side.jpg')
    assert 'Given already: kiln side.jpg (1 of 3).' in film.lines()['ref:BRICK']['own']['text']
    assert 'user' not in json.dumps([brick, mason, said]).lower()


def test_step_2_takes_up_to_three_and_a_thing_with_footage_pictures_is_told_its_set_is_still_made_from_them():
    film, _ = at_step_1()
    l = film.lines()
    film.record(ans(l['ref:TROWEL'], 'set'), ans(l['ref:FAN'], 'ignore'), ans(l['ref:BRICK'], 'ignore'), ans(l['ref:TILE'], 'ignore'), ans(l['refs:proposals'], 'accept_all'))
    film.back()
    film.set_looks()
    l = film.lines()
    film.record(ans(l['sets:rest'], 'rest'))
    film.back()
    film.set_looks()
    l = film.lines()
    trowel, street = l['set:TROWEL']['own'], l['set:STREET']['own']
    assert film.page()['layout']['words']['own'] == P.OWN_PAGE
    assert trowel['max'] == street['max'] == 3 and l['set:MASON']['own']['max'] == 1
    assert P.OWN_FOOTAGE in trowel['text'] and P.OWN_FOOTAGE not in street['text']   # said before the upload, only where the thing has footage pictures
    # three own pictures on a set that is back: stored and approved; the set stays as made and is approved; pictures of the thing start from the first one given
    a, b, c = (give(film, 'TROWEL', k)['id'] for k in COLOURS[:3])
    out = film.record(own(l['set:TROWEL'], [a, b, c]))
    s = film.session()
    assert out['refused'] == [] and out['recorded'] == ['set:TROWEL'] and s['golden']['TROWEL'] == a and mine(film, 'TROWEL') == [a, b, c]
    assert VS._set_rows(s, 'TROWEL', s['round']['elements']['TROWEL']['set'], ('approved',))
    trowel_el = next(e for e in film.plan['elements'] if e['id'] == 'TROWEL')
    assert not [i for i in RS.inputs_of(s, trowel_el)[0] if i['ref'] in (a, b, c)]   # today's rule: its set is made from the footage pictures


def test_the_fourth_answer_on_a_set_is_refused_too():
    film = at_step_2()
    l = film.lines()
    refs = [give(film, 'STREET', k)['id'] for k in COLOURS[:3]]
    s = film.session()
    s['references']['own-4'] = {**s['references'][refs[0]], 'id': 'own-4', 'sha256': 'x' * 64}
    film.store.files[SESSION] = json.dumps(s).encode('utf-8')
    out = film.record(own(l['set:STREET'], refs + ['own-4']), ans(l['set:T_LAY'], approve(l['set:T_LAY'])))
    assert out['refused'] == [{'key': 'set:STREET', 'message': 'Three pictures at most. Remove one first.'}] and out['recorded'] == ['set:T_LAY']
