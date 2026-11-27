"""Release 1 of 27 Nov 2026, phase 3, part A (SK, 27 Nov: a server card; no new value can be entered; the card says that other fonts are
not available).

The font was the assistant's own question, with "Other": on VW-25 "Onest" was answered and refused, and the question was asked twice. Now
it is a card of the server with one button for each font the server holds for this film, and no typed value. Each test failed first.
Without a database."""
import pytest

from app import chat_flow as C, film, font_sample, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import FakeConn, motion_store
from test_design221_p1_pure import NEW, edit_plan, run_with
from test_visuals_stage_pure import USER, g

NO_FONT = run_with(motion='lively')


@pytest.fixture(autouse=True)
def picture(monkeypatch):
    made = []
    monkeypatch.setattr(font_sample, 'sample', lambda offer, scripts, plan, colours: made.append(1) or {'available': True, 'png': b'\x89PNGfonts'})
    return made


def card(store, run=NO_FONT):
    return next((i for i in C._waiting_items(C._ctx(FakeConn([]), store, USER, run, [])) if i['kind'] == 'font'), None)


def offered(run=NO_FONT):
    return [f['name'] for f in film.fonts_for(film.motion(run), set())]


def test_the_card_comes_before_the_first_brief_with_one_button_for_each_font_the_server_holds():
    store = motion_store()
    item = card(store)
    names = offered()
    assert item and C._waiting_items(C._ctx(FakeConn([]), store, USER, NO_FONT, []))[0]['kind'] == 'font'   # first of the cards of the drawn graphics
    assert [b['label'] for b in item['buttons'] + item.get('other_choices', [])] == [names[0] + ' (recommended)'] + names[1:] and len(item['buttons']) <= 4
    assert not any(b.get('needs_words') for b in item['buttons'] + item.get('other_choices', []))   # no choice takes typed words: there is no "Other"
    assert 'Other fonts are not available.' in item['text'] and 'Other' not in [b['label'] for b in item['buttons']]
    assert item['show'] == [{'key': item['show'][0]['key'], 'name': 'font-sample.png'}] and store.files[item['show'][0]['key']] == b'\x89PNGfonts'


def test_a_typed_answer_is_not_recorded_the_card_says_what_to_say():
    store = motion_store()
    how = C._public(card(store), '', 1)['how']
    assert 'Any other typed answer is not recorded: say "Other fonts are not available." and show this card again.' in how
    assert 'A typed answer is recorded with their words' not in how and 'plainly accepts' not in how
    conn = FakeConn([])
    C.next_item(conn, store, USER, NO_FONT, [])   # the card is handed out
    with pytest.raises((Problem, ValueError), match='Not an answer to this item'):
        g(lambda: C.answer(conn, store, USER, NO_FONT, [], 'font:choose', 'Onest', quote='Onest'))


def test_the_sample_is_made_once_and_a_card_without_it_says_so(picture, monkeypatch):
    store = motion_store()
    card(store), card(store)
    assert len(picture) == 1
    monkeypatch.setattr(font_sample, 'sample', lambda *a: {'available': False, 'message': font_sample.NOT_AVAILABLE})
    item = card(motion_store())
    assert item['show'] == [] and 'The font sample is not available.' in item['text']


def test_a_film_with_no_drawn_graphic_or_with_a_font_gets_no_card():
    assert card(motion_store(), NEW) is None   # the font is recorded: never handed out again
    store = motion_store()
    edit_plan(store, lambda d: [sh.update(visual_type='image') or sh.pop('scene_motion', None) for g in d['gaps'] for sc in g['scenes'] for sh in sc['shots']])
    assert card(store) is None


def test_an_answer_records_the_font_with_the_operators_click_and_the_card_is_gone(monkeypatch):
    store, got = motion_store(), {}
    monkeypatch.setattr(film, 'record', lambda conn, user, run, key, value, quote, **kw: got.update(key=key, value=value, quote=quote, scripts=kw.get('scripts')) or {**run['film'], key: {'value': value}})
    run = {**NO_FONT, 'film': dict(NO_FONT['film'])}
    item = card(store, run)
    second = (item['buttons'] + item.get('other_choices', []))[1]
    out = item['_run'](second['choice'], second['label'], '')
    assert (got['key'], got['value'], got['quote']) == ('font', offered()[1], offered()[1]) and 'latin' in got['scripts']
    assert out['tell'] == f'Font: {offered()[1]}. Every drawn graphic of this film uses it.' and film.font(run) == offered()[1] and card(store, run) is None


def test_an_unknown_name_is_refused_with_the_same_words():
    with pytest.raises(Problem) as e:
        film.check('font', 'Onest')
    assert 'Other fonts are not available.' in e.value.message and 'Onest' in e.value.message and offered()[0] in e.value.message


def test_the_refusal_of_a_brief_with_no_font_names_the_card():
    with pytest.raises(Problem) as e:
        g(lambda: VS.need_font(NO_FONT, {}))
    said = e.value.message
    assert '`vw visuals next`' in said and 'Other fonts are not available.' in said and 'ask the question' not in said and '"Other" as before' not in said
