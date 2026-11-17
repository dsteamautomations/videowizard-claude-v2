"""design/211 part C (section 6.3): the answers of a v2 round recorded from the page (`page_flow.page_record`): "Accept the proposals", a
clean set, a picture answered on its own, "make the rest", a thing back after a second send; a stale answer; a refusal kept on its line;
and the one "what next" sentence after each record. Parts A and B are stood in for (test_design211c_kit_pure). Without a database."""
import json

import pytest

from app import chat_flow as CF, page_flow as P, ref_find, ref_sets
from app.main import PageAnswer
import d211_fixture as F
from test_design211c_kit_pure import Film, PAID, ans

WAIT_1 = ' thing(s) still wait for the operator on the page: write the new round to the page and give them the link again. The answers given are kept: nothing is made until every thing is answered.'
WAIT_2 = ' line(s) still wait for the operator on the page: write the new round to the page and give them the link again.'


def logged(film):
    return [json.dumps(p, default=str, ensure_ascii=False) for sql, p in film.conn.sql if 'vw2_log' in sql]


# ---------- "Accept the proposals" ----------

def test_accept_the_proposals_covers_every_routine_line_and_no_doubtful_one(monkeypatch):
    film = Film(monkeypatch)
    out = film.record(ans(film.lines()['refs:proposals'], 'accept_all'))
    held = film.session()['chat_round']
    assert sorted(held) == ['BRICK', 'MASON', 'STREET', 'TILE', 'T_LAY'] and 'TROWEL' not in held and 'FAN' not in held
    assert all(v['verdict'] == 'approve' and v['quote'] == 'Accept the 5 proposals (paid, about ₹175)' and v['words'] == '' for v in held.values())   # the priced label is their word
    assert out['kept'] == ['refs:proposals'] and out['refused'] == [] and film.called('round_done') == [] and out['then'] == '2' + WAIT_1
    l = {x['key']: x for x in out['page']['lines']}
    assert 'refs:proposals' not in l and l['ref:BRICK']['kept'] == 'Accept the 5 proposals (paid, about ₹175)' and l['ref:BRICK']['kept_note'] == P.REFS_KEPT and 'kept' not in l['ref:TROWEL']
    assert any('refs:proposals' in x and 'accept_all' in x and 'Accept the 5 proposals' in x for x in logged(film))   # one log line with their words


def test_a_real_persons_likeness_is_never_covered(monkeypatch):
    film = Film(monkeypatch)
    film.real.add('MASON')
    film.record(ans(film.lines()['refs:proposals'], 'accept_all'))
    assert sorted(film.session()['chat_round']) == ['BRICK', 'STREET', 'TILE', 'T_LAY']


def test_a_later_answer_to_one_line_wins_over_accept_the_proposals(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    film.record(ans(l['ref:BRICK'], 'ignore'), ans(l['refs:proposals'], 'accept_all'))   # in any order on the page: the line's own answer stands
    held = film.session()['chat_round']
    assert held['BRICK']['verdict'] == 'ignore' and held['BRICK']['quote'] == 'Leave it out' and held['STREET']['verdict'] == 'approve'
    film.record(ans(film.lines()['ref:STREET'], 'ignore'))                             # and on a later visit
    assert film.session()['chat_round']['STREET']['verdict'] == 'ignore'


def test_accept_with_no_routine_line_left_is_refused(monkeypatch):
    film = Film(monkeypatch)
    film.record(ans(film.lines()['refs:proposals'], 'accept_all'))
    with pytest.raises(ValueError) as e:
        CF.round_accept(film.ctx(), 'again')
    assert str(e.value) == CF.ACCEPT_NONE
    assert 'round1:all' not in [i['id'] for i in film.items()]                        # and the line is not offered any more


def test_every_thing_answered_records_step_1_once_and_says_the_servers_sentence(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    out = film.record(ans(l['refs:proposals'], 'accept_all'), ans(l['ref:TROWEL'], 'clean', 'Show the blade clean.'), ans(l['ref:FAN'], 'ignore'), ans(l['ref:STREET'], 'approve', 'It is wider than it looks.'))
    (verdicts, quote), = film.called('round_done')
    assert verdicts['TROWEL'] == {'verdict': 'clean', 'words': 'Show the blade clean.'} and verdicts['STREET'] == {'verdict': 'approve', 'words': 'It is wider than it looks.'}
    assert verdicts['FAN'] == {'verdict': 'ignore', 'words': ''} and verdicts['MASON'] == {'verdict': 'approve', 'words': ''} and quote == 'Done, on the page'
    assert out['then'] == ref_sets.GO1_MAKING.format(k=3, x='105', r=2) and out['kept'] == [] and 'refs:proposals' in out['recorded'] and 'ref:TROWEL' in out['recorded']
    assert out['page']['step'] == P.SETS_STEP and 'chat_round' not in film.session()


def test_the_words_of_step_1_are_kept_only_where_a_set_follows(monkeypatch):
    film = Film(monkeypatch)
    film.record(ans(film.lines()['ref:TROWEL'], 'approve', 'fine as it is'))
    assert film.session()['chat_round']['TROWEL'] == {'verdict': 'approve', 'quote': 'Use it as the reference', 'frames': 'f-trowel-side,f-trowel-use', 'words': '', 'pics': {}}
    assert any('fine as it is' in x for x in logged(film))                             # the words are in the log all the same


def test_the_sets_alone_passing_the_limit_still_refuses_the_step_and_nothing_else_does(monkeypatch):
    film = Film(monkeypatch)
    monkeypatch.setattr(P.V, '_set_budget', lambda run, s, spend: (3700.0, F.CAP, F.SET_PRICE))
    l = film.lines()
    out = film.record(ans(l['refs:proposals'], 'accept_all'), ans(l['ref:TROWEL'], 'approve'), ans(l['ref:FAN'], 'ignore'))
    assert film.called('round_done') == [] and out['refused'][0]['key'] == 'references' and 'The answers ask for 5 sets, about ₹175' in out['refused'][0]['message']
    assert out['then'].startswith('The references are not recorded yet: ')


# ---------- a picture answered on its own ----------

def test_not_this_picture_goes_to_part_a_and_the_line_comes_back_open(monkeypatch):
    film = Film(monkeypatch)
    out = film.record(ans(film.lines()['ref:TROWEL'], 'pics', pics={'f-trowel-use': 'not'}))
    assert film.called('not_this') == [('TROWEL', 'f-trowel-use', P.MARKED)] and out['recorded'] == ['ref:TROWEL'] and out['kept'] == [] and out['refused'] == []
    t = {x['key']: x for x in out['page']['lines']}['ref:TROWEL']
    assert [x['label'] for x in t['pics']] == ['side'] and 'kept' not in t and 'TROWEL' not in (film.session().get('chat_round') or {}) and '1 picture.' in t['text']
    assert any('Pictures answered: f-trowel-use not' in x for x in logged(film))


def test_that_is_it_makes_the_closest_picture_a_footage_picture_of_the_line(monkeypatch):
    film = Film(monkeypatch)
    out = film.record(ans(film.lines()['ref:FAN'], 'pics', pics={'t0000000000c1': 'use'}))
    assert film.called('that_is_it') == [('FAN', 't0000000000c1', P.MARKED)] and out['recorded'] == ['ref:FAN']
    fan = {x['key']: x for x in out['page']['lines']}['ref:FAN']
    assert [(x['label'], x.get('weak'), x['choice']) for x in fan['pics']] == [('whole', True, 'not:f-FAN-it')] and 'From your footage: 1 picture.' in fan['text']
    assert [b['choice'] for b in fan['buttons']] == ['ignore', 'approve', 'clean']    # now it can be used as it is, or a clean set made from it


def test_a_mark_on_a_picture_that_is_not_on_the_line_is_refused_and_kept_on_its_line(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    out = film.record(ans(l['ref:TROWEL'], 'approve', pics={'f-tile-under': 'not'}), ans(l['ref:FAN'], 'pics', pics={'t0000000000a1': 'use'}), ans(l['ref:BRICK'], 'ignore'))
    assert out['refused'] == [{'key': 'ref:TROWEL', 'message': CF.PIC_UNKNOWN.format(pic='f-tile-under')}, {'key': 'ref:FAN', 'message': CF.PIC_UNKNOWN.format(pic='t0000000000a1')}]
    assert film.called('not_this') == [] and film.called('that_is_it') == [] and out['kept'] == ['ref:BRICK']   # nothing half done; the other answers are recorded
    now = {x['key']: x for x in out['page']['lines']}
    assert now['ref:TROWEL']['refused'] == CF.PIC_UNKNOWN.format(pic='f-tile-under') and 'refused' not in now['ref:BRICK']
    assert out['then'].startswith(P.ROUND_REFUSED + ' ')


def test_a_picture_mark_with_a_line_answer_keeps_the_answer_when_it_still_means_the_same(monkeypatch):
    film = Film(monkeypatch)
    out = film.record(ans(film.lines()['ref:TROWEL'], 'approve', pics={'f-trowel-use': 'not'}))
    assert film.called('not_this') == [('TROWEL', 'f-trowel-use', 'Use it as the reference')] and out['kept'] == ['ref:TROWEL']
    assert film.session()['chat_round']['TROWEL'] == {'verdict': 'approve', 'quote': 'Use it as the reference', 'frames': 'f-trowel-side', 'words': '', 'pics': {'f-trowel-use': 'not'}}


def test_a_picture_mark_that_brings_an_unseen_picture_leaves_the_line_open(monkeypatch):
    film = Film(monkeypatch)
    film.next_frame = {**film.session()['references']['f-trowel-use'], 'id': 'f-trowel-next', 'view': 'in the hand, lifting mortar'}
    out = film.record(ans(film.lines()['ref:TROWEL'], 'approve', pics={'f-trowel-use': 'not'}))
    assert out['recorded'] == ['ref:TROWEL'] and out['kept'] == [] and 'TROWEL' not in (film.session().get('chat_round') or {})   # the operator has not seen the next best: it is shown first
    assert [x['choice'] for x in {x['key']: x for x in out['page']['lines']}['ref:TROWEL']['pics']] == ['not:f-trowel-side', 'not:f-trowel-next']


def test_the_last_picture_rejected_leaves_the_line_open_with_the_paid_and_the_leave_out_choice(monkeypatch):
    film = Film(monkeypatch)
    out = film.record(ans(film.lines()['ref:TROWEL'], 'approve', pics={'f-trowel-use': 'not', 'f-trowel-side': 'not'}))
    assert len(film.called('not_this')) == 2 and out['kept'] == []                     # "use it" would now mean a paid set: it is asked again
    t = {x['key']: x for x in out['page']['lines']}['ref:TROWEL']
    assert [b['label'] for b in t['buttons']] == [f'Have a set made ({PAID})', 'Leave it out'] and 'None was found in your footage.' in t['text'] and 'pics' not in t


# ---------- step 2 ----------

def test_make_the_rest_goes_to_part_b_with_the_priced_label_as_the_operators_word(monkeypatch):
    film = Film(monkeypatch, '2', session=F.session('rewrite'))
    film.change(lambda s: s['round']['elements']['T_LAY'].update(ignored=True))   # the first sets are judged: only the others wait
    rest = film.lines()['sets:rest']
    out = film.record(ans(rest, 'rest'))
    assert film.called('round_rest') == [('Make the other 2 sets (paid, about ₹70)',)] and out['recorded'] == ['sets:rest'] and out['then'] == ref_sets.ALL_MAKING.format(k=2, x='70')
    assert any('sets:rest' in x and 'Make the other 2 sets (paid, about ₹70)' in x for x in logged(film))


def test_leave_the_rest_out_sets_each_thing_aside_and_pays_nothing(monkeypatch):
    film = Film(monkeypatch, '2')
    out = film.record(ans(film.lines()['sets:rest'], 'rest_out'))
    s = film.session()['round']['elements']
    assert s['BRICK']['ignored'] and s['TILE']['ignored'] and film.called('round_rest') == [] and 'sets:rest' not in [l['key'] for l in out['page']['lines']]


def test_a_thing_back_after_a_second_send_is_answered_through_part_b(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: s['round']['elements']['FAN'].update(reopened='left_out'))
    out = film.record(ans(film.lines()['set:FAN'], 'approve', 'The dial is black.'))
    assert film.called('round_reopen') == [('FAN', 'approve', 'The dial is black.', f'Have a set made ({PAID})')] and out['recorded'] == ['set:FAN']
    film.record(ans(film.lines()['set:FAN'], 'ignore'))
    assert film.called('round_reopen')[1][:2] == ('FAN', 'ignore')


def test_a_set_is_judged_through_the_same_server_functions_as_before(monkeypatch):
    film = Film(monkeypatch, '2')
    l = film.lines()
    out = film.record(ans(l['set:MASON'], 'yes'), ans(l['set:STREET'], 'use:s-street-1-2'), ans(l['set:T_LAY'], 'no', 'Show the hand pressing the brick down.'))
    sent = [v for v, _q in film.called('round_sets')]
    assert sent[0] == {'MASON': {'verdict': 'yes', 'golden': None, 'words': ''}} and sent[1]['STREET'] == {'verdict': 'yes', 'golden': 's-street-1-2', 'words': ''}
    assert sent[2]['T_LAY'] == {'verdict': 'correct', 'golden': None, 'words': 'Show the hand pressing the brick down.'}   # a "No" with words is made again with them, as before
    assert out['refused'] == [] and sorted(out['recorded']) == ['set:MASON', 'set:STREET', 'set:T_LAY']


def test_a_set_not_made_is_made_with_the_operators_word_and_a_changed_set_made_again(monkeypatch):
    film = Film(monkeypatch, '2')
    film.changed.add('STREET')
    film.change(lambda s: [r.update(status='failed') for r in s['references'].values() if r.get('set') == 's-mason-1'])
    l = film.lines()
    film.record(ans(l['set:MASON'], 'make'), ans(l['set:STREET'], 'remake'))
    assert film.called('set_make') == [('MASON', f'Make it ({PAID})'), ('STREET', f'Make it again from the changed plan ({PAID})')]


def test_an_answer_to_a_set_made_again_since_is_stale_and_an_unknown_choice_is_refused_on_its_line(monkeypatch):
    film = Film(monkeypatch, '2')
    l = film.lines()
    out = film.record({**ans(l['set:MASON'], 'yes'), 'item': 'set:MASON:s-mason-0'}, ans(l['set:STREET'], 'clean'), ans(l['sets:rest'], 'accept_all'))
    assert out['stale'] == ['set:MASON'] and film.called('round_sets') == [] and film.called('round_rest') == []
    assert [r['key'] for r in out['refused']] == ['set:STREET', 'sets:rest'] and all(r['message'].startswith('Not an answer to this line: ') for r in out['refused'])
    assert {x['key']: x for x in out['page']['lines']}['set:STREET']['refused'].startswith("Not an answer to this line: 'clean'. Its answers are: Use A")


def test_the_answer_of_the_page_may_carry_picture_marks():
    a = PageAnswer(key='ref:TROWEL', choice='pics', pics={'f-trowel-use': 'not', 't0000000000c1': 'use'})
    assert a.model_dump()['pics'] == {'f-trowel-use': 'not', 't0000000000c1': 'use'} and PageAnswer(key='k', choice='yes').pics == {}
    with pytest.raises(ValueError):
        PageAnswer(key='k', choice='pics', pics={f'p{i}': 'not' for i in range(9)})   # at most 8


# ---------- the one "what next" after each record ----------

def test_then_with_no_round_yet_is_find_start(monkeypatch):
    s = F.session('1')
    s.pop('round')
    film = Film(monkeypatch, session=s)
    p = film.page()
    assert p['then'] == ref_find.FIND_START and P.REFS_START == ref_find.FIND_START and p['step'] not in (P.REFS_STEP, P.SETS_STEP)
    assert film.record()['then'] == 'Nothing was answered on the page. ' + P.PLAN_DONE + ref_find.FIND_START


def test_then_refs_here_when_the_round_is_in_this_answer(monkeypatch):
    film = Film(monkeypatch)
    real, calls = P._plan_step, []
    monkeypatch.setattr(P, '_plan_step', lambda ctx: ('plan', []) if not calls.append(1) and len(calls) == 1 else real(ctx))   # this "done" was said on the plan; the page is at the references now
    out = film.record()
    assert out['page']['step'] == P.REFS_STEP and out['then'] == 'Nothing was answered on the page. ' + P.PLAN_DONE + P.REFS_HERE


def test_then_refs_go_when_the_round_is_started_and_not_in_this_answer(monkeypatch):
    film = Film(monkeypatch)
    assert P._after(film.ctx(), {'step': 'Plan', 'lines': []}, 'Lead. ', 'END') == 'Lead. ' + P.REFS_GO


def test_then_sets_wait_while_the_first_sets_are_made(monkeypatch):
    assert Film(monkeypatch, 'making').record()['then'] == 'Nothing was answered on the page. ' + P.SETS_WAIT


def test_then_sets_look_while_claude_looks_at_the_sets(monkeypatch):
    film = Film(monkeypatch, 'looking')
    assert film.record()['then'] == 'Nothing was answered on the page. ' + ref_sets.SETS_LOOK and film.page()['then'] == ref_sets.SETS_LOOK


def test_then_rewrite_due_while_a_request_is_written_again(monkeypatch):
    film = Film(monkeypatch, 'rewrite')
    assert film.record()['then'] == 'Nothing was answered on the page. ' + ref_sets.REWRITE_DUE.format(n=1) and film.page()['then'] == ref_sets.REWRITE_DUE.format(n=1)
    assert '{element_id, prompt}' in film.page()['then']


def test_then_rest_left_when_only_the_other_sets_are_not_ordered(monkeypatch):
    film = Film(monkeypatch, '2', session=F.session('rewrite'))
    film.change(lambda s: s['round']['elements']['T_LAY'].update(ignored=True))
    out = film.record()
    assert [l['key'] for l in out['page']['lines'] if l['state'] == 'open'] == ['sets:rest']
    assert out['then'] == 'Nothing was answered on the page. ' + P.REST_LEFT.format(r=2) == 'Nothing was answered on the page. The first sets are judged. 2 more are not ordered: the operator orders them on the page (`vw visuals page`), or leaves them.'


def test_then_lines_still_wait_while_a_set_is_to_judge(monkeypatch):
    assert Film(monkeypatch, '2').record()['then'] == 'Nothing was answered on the page. 4' + WAIT_2


def test_then_sets_stand_when_only_kept_answers_wait(monkeypatch):
    film = Film(monkeypatch, '2')

    def keep(s):
        rows = s['round']['elements']
        s['round']['rest'] = []
        for eid in ('BRICK', 'TILE'):
            rows[eid].update(ignored=True)
        for eid in ('MASON', 'STREET', 'T_LAY'):
            rows[eid]['answer'] = {'verdict': 'no', 'golden': None, 'words': '', 'set': rows[eid]['set']}
    film.change(keep)
    assert film.record()['then'] == 'Nothing was answered on the page. ' + P.SETS_STAND


def test_a_refusal_of_the_second_go_or_of_a_remake_is_kept_on_its_line_and_the_rest_is_recorded(monkeypatch):
    film = Film(monkeypatch, '2')
    cap = ref_sets.REST_CAP.format(n=2, x='70', spent='3,700', cap='3,754')
    limit = ref_sets.MAKES_LIMIT.format(eid='T_LAY', max=3)

    def refuse(conn, store, user, run, outputs, quote):
        raise ValueError(cap)

    def sets(store, user, run, outputs, verdicts, quote, conn=None, partial=False):
        if 'T_LAY' in verdicts:
            raise ValueError(limit)
        return film.round_sets(store, user, run, outputs, verdicts, quote, conn, partial)
    monkeypatch.setattr(ref_sets, 'round_rest', refuse)
    monkeypatch.setattr(P.V, 'round_sets', sets)
    l = film.lines()
    out = film.record(ans(l['sets:rest'], 'rest'), ans(l['set:MASON'], 'yes'), ans(l['set:T_LAY'], 'correct', 'Show the hand.'))
    assert [r['key'] for r in out['refused']] == ['sets:rest', 'set:T_LAY'] and out['refused'][0]['message'] == cap and limit in out['refused'][1]['message']
    assert 'set:MASON' in out['recorded'] and film.called('round_rest') == []
    now = {x['key']: x for x in out['page']['lines']}
    assert now['sets:rest']['refused'] == cap and limit in now['set:T_LAY']['refused'] and 'refused' not in now['set:STREET']   # each refusal stays on its own line
    assert out['then'].startswith(P.ROUND_REFUSED + ' ') and any('refused' in x and 'sets:rest' in x for x in logged(film))


def test_then_sets_none_when_nothing_waits_at_the_sets(monkeypatch):
    film = Film(monkeypatch, '2', session=F.session('complete'))
    out = film.record()
    assert out['page']['step'] == P.SETS_STEP and out['then'] == 'Nothing was answered on the page. ' + P.SETS_NONE


def test_then_round_next_when_the_round_is_complete(monkeypatch):
    film = Film(monkeypatch, 'complete')
    real, calls = P._plan_step, []
    monkeypatch.setattr(P, '_plan_step', lambda ctx: ('sets', []) if not calls.append(1) and len(calls) == 1 else real(ctx))   # this "done" was said on the sets; the round ended
    assert film.record()['then'] == 'Nothing was answered on the page. ' + P.ROUND_NEXT


def test_then_round_refused_when_the_server_refuses_an_answer(monkeypatch):
    film = Film(monkeypatch, '2')
    out = film.record(ans(film.lines()['set:MASON'], 'rest'))
    assert out['then'] == P.ROUND_REFUSED + ' 4' + WAIT_2 and out['refused'][0]['key'] == 'set:MASON'
