"""SK, 23 Nov 2026 (no-footage release 2b): the look boards. A film with no camera footage shows each Direction's look as a picture: one board
for each period of each Direction, always made with GPT Image, in the film's shape. The cost is said first and counts in the film's limit. The
board of the Direction the operator takes is the film's look picture. A board that is refused leaves the other and the words. A film with
footage gets no boards."""
import json
from pathlib import Path

import pytest

from app import chat_flow as CF, core, visual_workers as VW, visuals_stage as VS
from app.errors import Problem

SERVER = Path(__file__).resolve().parents[1]
VISUALS = next(s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
RUN = {'id': 'run-1', 'code': 'VW-T'}
LOOK = [{'period': '', 'look': 'Muted earth colours, soft overcast light.'}]
LOOK2 = [{'period': '', 'look': 'Warm evening light, deep shadows.'}]


def draft(look=LOOK, look2=LOOK2):
    return {'direction': 'The mason tells it.', 'direction_look': look, 'direction_alternative': {'text': 'The owner tells it.', 'parts': {}, 'look': look2},
            'lines': {'direction': {'state': 'to_accept', 'digest': 'd'}}, 'gaps': [], 'direction_only': True}


class Conn:
    def __init__(self):
        self.rows = []

    def execute(self, sql, params=()):
        if sql.startswith('insert into vw2_jobs'):
            self.rows.append(params)
        return self

    def fetchone(self):
        return {'id': f'job-{len(self.rows)}'}


@pytest.fixture
def film(monkeypatch):
    """A film with no camera footage whose two Directions wait for the operator; nothing is stored, nothing is called."""
    state = {'session': {'treatment_draft': draft(), 'references': {}}, 'footage': 'none', 'cap': [], 'saved': 0}
    monkeypatch.setattr(VS.core, 'footage_of', lambda run: state['footage'])
    monkeypatch.setattr(VS, 'session_of', lambda *a, **k: state['session'])
    monkeypatch.setattr(VS, 'save_session', lambda *a, **k: state.__setitem__('saved', state['saved'] + 1))
    monkeypatch.setattr(VS, 'reconcile', lambda *a, **k: 0)
    monkeypatch.setattr(VS, 'check_cap', lambda conn, run, session, inr, what: state['cap'].append((inr, what)))
    monkeypatch.setattr(VS, 'image_price_inr', lambda run, tier=None, provider=None: 20.0 if provider == 'openai' else 3.0)
    monkeypatch.setattr(VS, 'provider_of', lambda run: 'gemini')   # the run's picture AI is Nano Banana
    monkeypatch.setattr(VS, 'aspect_of', lambda *a, **k: '16:9')
    monkeypatch.setattr(VS, 'board_lettering', lambda store, outputs: True)
    return state


def boards(conn, make=None):
    return VS.look_boards(conn, None, {'id': 'u'}, RUN, [], make=make)


def test_a_film_with_footage_gets_no_boards(film):
    film['footage'] = 'own'
    with pytest.raises(ValueError) as e:
        boards(Conn())
    assert 'no camera footage' in str(e.value)


def test_no_board_before_the_direction_and_its_looks(film):
    film['session'] = {'references': {}}
    with pytest.raises(ValueError) as e:
        boards(Conn(), 'all')
    assert '`vw visuals treatment`' in str(e.value)


def test_the_cost_is_said_before_anything_is_made(film):
    conn = Conn()
    out = boards(conn)
    assert out['to_make'] == 2 and out['cost_inr'] == 40.0 and '₹40' in out['next'] and '--make all' in out['next']
    assert conn.rows == [] and 'boards' not in film['session'] and film['cap'] == []


def test_the_boards_are_asked_of_gpt_image_whatever_the_picture_ai_of_the_run(film):
    conn = Conn()
    out = boards(conn, 'all')
    assert len(conn.rows) == 2 and film['cap'] == [(40.0, '2 look boards')] and film['saved'] == 1
    for run_id, unit, request, request_id, provider in conn.rows:
        req = request.obj
        assert provider == 'openai' and req['provider'] == 'openai' and req['model'] == VS.IMAGE_MODELS['generate'] and req['op'] == 'generate' and req['parents'] == []
        assert req['reference']['kind'] == 'board' and unit == req['reference']['id'] and request_id == 'board:' + unit
    made = film['session']['boards']
    assert len(made) == 2 and {b['status'] for b in made.values()} == {'generating'} and film['session']['references'] == {}   # no reference list is touched
    assert [b['label'] for b in out['boards']] == ['First', 'Second'] and out['to_make'] == 0


def test_boards_already_asked_for_are_not_asked_for_twice(film):
    conn = Conn()
    boards(conn, 'all')
    out = boards(conn, 'all')
    assert len(conn.rows) == 2 and out['cost_inr'] == 0 and len(film['cap']) == 1


def test_a_film_of_two_periods_has_a_board_for_each_period_of_each_direction(film):
    two = [{'period': '1950s', 'look': 'Faded colour.'}, {'period': 'today', 'look': 'Clean daylight.'}]
    film['session']['treatment_draft'] = draft(two, [{'period': '1950s', 'look': 'Sepia.'}, {'period': 'today', 'look': 'Cool light.'}])
    conn = Conn()
    out = boards(conn, 'all')
    assert len(conn.rows) == 4 and [b['label'] for b in out['boards']] == ['First · 1950s', 'First · today', 'Second · 1950s', 'Second · today']
    assert 'The period: 1950s.' in conn.rows[0][2].obj['prompt']


def test_the_cost_limit_reached_keeps_nothing_half_made(film, monkeypatch):
    def stop(*a):
        raise Problem(409, 'VISUALS_CAP', 'over')
    monkeypatch.setattr(VS, 'check_cap', stop)
    conn = Conn()
    with pytest.raises(Problem):
        boards(conn, 'all')
    assert conn.rows == [] and not film['session'].get('boards') and film['saved'] == 0


def test_the_prompt_holds_the_look_and_never_a_real_person_or_a_logo():
    p = VS.board_prompt('The mason tells it.', LOOK[0], True)
    assert 'The mason tells it.' in p and 'Muted earth colours, soft overcast light.' in p and 'swatches' in p and 'lettering' in p
    assert 'real, named person' in p and 'logo' in p and 'period' not in p
    bare = VS.board_prompt('x', LOOK[0], False)
    assert 'lettering' not in bare and 'any writing' in bare   # a script whose letters the picture AI draws badly


def finish(session, n, status='candidate', **more):
    b = list(session['boards'].values())[n]
    b.update(status=status, **({'sha256': 's' + str(n), 'key': f"run-1/visuals/references/{b['id']}.png"} if status == 'candidate' else {}), **more)
    return b


def test_a_refused_board_leaves_the_other_and_the_words(film):
    boards(Conn(), 'all')
    finish(film['session'], 0, 'failed', error='OpenAI refused this picture: a likeness.')
    second = finish(film['session'], 1)
    out = boards(Conn())
    first, other = out['boards']
    assert first['status'] == 'failed' and 'likeness' in first['error'] and other['status'] == 'candidate'
    assert out['to_make'] == 0 and [f['key'] for f in out['show']] == [second['key']]   # a refused board is not asked for again by itself
    assert 'pick from the words' in out['next']


def test_the_assistant_has_a_board_made_again_once(film):
    boards(Conn(), 'all')
    first = finish(film['session'], 0)
    with pytest.raises(ValueError):
        boards(Conn(), 'no-such-board')
    conn = Conn()
    out = boards(conn, first['id'])
    assert len(conn.rows) == 1 and film['cap'][-1] == (20.0, '1 look board')
    again = out['boards'][0]
    assert again['id'] != first['id'] and again['status'] == 'generating'
    with pytest.raises(ValueError) as e:   # still being made
        boards(Conn(), again['id'])
    film['session']['boards'][again['id']]['status'] = 'candidate'
    with pytest.raises(ValueError) as e:
        boards(Conn(), again['id'])
    assert 'once' in str(e.value)


def test_a_board_that_failed_may_be_asked_for_again(film):
    boards(Conn(), 'all')
    first = finish(film['session'], 0, 'failed', error='down')
    conn = Conn()
    out = boards(conn, first['id'])
    assert len(conn.rows) == 1 and out['boards'][0]['status'] == 'generating'
    film['session']['boards'][out['boards'][0]['id']]['status'] = 'candidate'
    assert boards(conn, out['boards'][0]['id'])['boards'][0]['status'] == 'generating'   # a failure is not the one remake


def test_the_board_of_the_direction_taken_is_the_look_picture_of_the_film(film):
    boards(Conn(), 'all')
    finish(film['session'], 0), finish(film['session'], 1)
    s = film['session']
    assert VS.look_board(s) is None   # nothing taken yet
    d = s.pop('treatment_draft')
    s['treatment'] = {'direction': d['direction_alternative']['text'], 'direction_look': LOOK2}   # the operator took the second
    assert VS.look_board(s)['id'] == list(s['boards'].values())[1]['id']
    assert [b['label'] for b in boards(Conn())['boards']] == ['']   # the one look of the film now
    s['treatment'] = {'direction': 'A third way.', 'direction_look': LOOK}   # taken from words: no picture
    assert VS.look_board(s) is None


def test_a_scene_reads_the_board_of_its_period(film):
    two = [{'period': '1950s', 'look': 'Faded colour.'}, {'period': 'today', 'look': 'Clean daylight.'}]
    film['session']['treatment_draft'] = draft(two, two)
    boards(Conn(), 'all')
    s = film['session']
    old, new = finish(s, 0), finish(s, 1)
    s['treatment'] = {'direction': s.pop('treatment_draft')['direction'], 'direction_look': two}
    assert VS.look_board(s, {'period': 'Today'})['id'] == new['id'] and VS.look_board(s, {})['id'] == old['id']


def test_a_new_direction_has_its_own_boards_and_its_cost_is_said_again(film):
    boards(Conn(), 'all')
    film['session']['treatment_draft'] = draft(look2=[{'period': '', 'look': 'The light of the first, the colours of the second.'}])
    out = boards(Conn())
    assert out['to_make'] == 1 and out['cost_inr'] == 20.0   # the first Direction keeps its board


def test_a_finished_board_is_found_by_the_worker_and_by_the_repair(film):
    boards(Conn(), 'all')
    s = film['session']
    bid = next(iter(s['boards']))
    ref, board = VW.ref_of(s, bid)
    assert board and ref is s['boards'][bid]
    s['references']['r1'] = {'id': 'r1'}
    assert VW.ref_of(s, 'r1') == (s['references']['r1'], False) and VW.ref_of(s, 'nope') == (None, False)
    assert [r['id'] for r in VS.made_pictures(s)] == ['r1', *s['boards']]


def test_both_fronts_show_the_boards_beside_the_words(film):
    boards(Conn(), 'all')
    s = film['session']
    finish(s, 0, 'failed', error='OpenAI refused this picture.')
    made = finish(s, 1)
    rows, show, pics = CF.board_lines(RUN, s)
    assert dict(rows)['First · The look board'].startswith('Not made') and 'refused' in dict(rows)['First · The look board']
    assert 'Second · The look board' in dict(rows) and [f['key'] for f in show] == [made['key']]
    assert pics == [(made['key'], 'Second', made['sha256'])]
    assert CF.board_lines(RUN, {'treatment_draft': {'direction': 'x'}}) == ([], [], [])   # a film with footage


def test_the_instructions_send_such_a_film_to_the_boards():
    none, own = core.for_footage(VISUALS, 'none'), core.for_footage(VISUALS, 'own')
    part = lambda st: next(p['text'] for p in st['parts'] if p['name'] == 'treatment')
    assert '`vw visuals boards`' in part(none) and 'cost' in part(none)
    assert 'vw visuals boards' not in json.dumps(own)
