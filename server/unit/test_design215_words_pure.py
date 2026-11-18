"""design/215, the words of the references steps: the three labels of the answer that was "Leave out" (change 1), each with the line naming
the shots made without a reference; the hint beside "Make a set"; "Make a set with words" (W1); what "Approve" says in the chat (W2); how
many sets are made first, said by the server (change 7); no amount in any sentence of these steps (W3); the step "Sizes, materials and graphic
specs" (change 6); the words the page renders, sent by the server. Without a database."""
import re

import pytest

from app import chat_flow as CF, page_flow as PF, ref_sets as RS, visuals_stage as VS
import d211_fixture as F
from test_design211b_round_pure import at_two, back, done, film, fresh, jobs, judge, look, post, put, refused, saved   # noqa: F401
from test_design211b_sets_pure import RUN, finder   # noqa: F401 (finder stands in for part A, on every test)
from test_visuals_stage_pure import USER

W = CF.WORDS
MONEY = re.compile(r'₹|\brupees?\b|\bINR\b|\bpaid\b|\bfree\b|\bcosts?\b|\bprice\b|\bspen[dt]\b', re.I)


@pytest.fixture(autouse=True)
def new_round(monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', 2)


def items(store, conn):
    return CF._round_items(CF._ctx(conn, store, USER, RUN, []), every=True)


def labels(item):
    return [b['label'] for b in item['buttons'] + list(item.get('other_choices') or [])]


def test_the_three_labels_and_none_of_the_older_words():
    assert (W['leave'], W['leave_failed'], W['rest_some']) == ('No reference needed', 'Go on without a reference', 'Make only some of them')   # design/216 (A12): the waiting sets' label is 'Make only some of them'; 'Do not make this set / these sets' retired
    assert W['fix1'] == 'Make a set with words' and W['go_set'] == 'Make a set with these words' and W['fix'] == 'Minor corrections'
    said = ' '.join(str(v) for v in W.values()) + ' '.join(CF.STEP1_GROUPS) + RS.MAKES_LIMIT + RS.CLEAN_NO_FRAME
    assert not re.search(r'leave (it|them|these \d+|some|\{them\}) out|\bleft out\b|leaving out|Leave out', said, re.I)


def test_step_4_offers_no_reference_needed_with_the_shots_that_lose_it_and_the_hint_beside_make_a_set():
    store, conn = film()
    post(store, conn)
    by = {i['_eid']: i for i in items(store, conn) if i['_eid']}
    trowel, fan = by['TROWEL'], by['FAN']   # a thing with footage pictures and a free choice; a thing with no picture
    assert 'No reference needed' in labels(trowel) and 'Make a set with words' in labels(trowel) and 'Minor corrections' not in labels(trowel)
    assert trowel['_line']['cost'].startswith('These shots are then made with no reference of it: shot ')
    hint = {b['label']: b.get('note') for b in trowel['buttons'] + trowel['other_choices']}
    assert hint['Make a set'] == W['set_hint'] == 'Picture not good? Make a set instead.'
    assert not any(b.get('note') for b in fan['buttons'] + list(fan.get('other_choices') or []))   # no picture: nothing to be "not good"
    go = {b['label']: b.get('go') for b in PF._round_buttons(trowel, 0)}
    assert go['Make a set with words'] == 'Make a set with these words' and PF._round_buttons(trowel, 0)[0].get('note') in (None, W['set_hint'])
    assert any(b.get('note') == W['set_hint'] for b in PF._round_buttons(trowel, 0))


def test_a_person_shown_in_a_made_shot_is_never_offered_to_go_without_a_reference():
    store, conn = at_two()
    for i in items(store, conn):
        if i.get('_person'):
            assert not any(l in labels(i) for l in (W['leave'], W['leave_failed'], W['rest_some']))


def test_step_5_a_set_that_could_not_be_made_offers_go_on_without_a_reference():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store, fail=('T_LAY',))
    look(store)
    item = next(i for i in items(store, conn) if i['id'] == 'setmake:T_LAY')
    assert labels(item) == ['Make it', 'Go on without a reference']
    page = {b['label']: b for b in item['_line']['buttons']}
    assert page['Go on without a reference']['act'] == 'leave' and page['Go on without a reference']['say'].startswith('Go on without a reference. ')
    assert item['_line']['loss']['text'].startswith(('These ', 'This 1 shot is then made with no reference of it:'))


def test_step_5_the_waiting_sets_are_not_made_under_their_own_label():
    store, conn = at_two()
    rest = next(i for i in items(store, conn) if i['id'].startswith('rest:'))
    assert labels(rest)[1] == 'Do not make these 2 sets' and rest['_line']['buttons'][1]['label'] == 'Make only some of them'
    assert rest['_line']['buttons'][1]['loss']['button'] == 'Do not make these 2 sets' and rest['_line']['buttons'][1]['loss']['cols'][0] == 'Not made'


def test_what_the_chat_says_under_each_button():
    store, conn = at_two()
    for i in items(store, conn):
        shown = CF._public(i, '', 1)
        for b in shown['buttons']:
            assert b['description'] and not MONEY.search(b['description']), b
            if b['label'] == 'Approve':
                assert b['description'] == 'Use this as the reference'
            if b['label'].startswith('Approve ') and not b['label'].startswith('Approve all '):
                assert b['description'] == 'Use this picture as the reference'
    store, conn = film()
    post(store, conn)
    trowel = CF._public(next(i for i in items(store, conn) if i['_eid'] == 'TROWEL'), '', 1)
    says = {b['label']: b['description'] for b in trowel['buttons']}
    assert says['Approve'] == 'Use the ticked footage pictures as the reference; nothing is made' and 'three' not in says['Make a set']


@pytest.mark.parametrize('n, said', [
    (0, ''), (1, 'The set is made now.'), (2, 'All 2 sets are made now.'), (3, 'All 3 sets are made now.'),
    (4, 'The first 3 sets are made to check the method. After you judge them, the other 1 is made in one go. A set you ask to change is made again, at most 3 times.'),
    (18, 'The first 3 sets are made to check the method. After you judge them, the other 15 are made in one go. A set you ask to change is made again, at most 3 times.')])
def test_how_many_sets_are_made_first_by_count(n, said):
    assert RS.goes_said(n) == said


def test_the_server_says_it_when_step_4_is_recorded_and_again_at_make_them():
    store, conn = film()
    post(store, conn)
    out = done(store, conn)   # five sets asked: three now, two wait
    assert out['then'].startswith('The first 3 sets are made to check the method. After you judge them, the other 2 are made in one go.') and 'cost_inr' not in out
    back(store)
    look(store)
    out = VS.guarded(lambda: RS.round_rest(conn, store, USER, RUN, [], 'Make them'))
    assert out['then'].startswith('The other 2 sets are made now, in one go. A set you ask to change is made again, at most 3 times.') and 'cost_inr' not in out
    store, conn = film()   # three or fewer: all at once; a first set that cannot be made is replaced, and the sentence still says three
    post(store, conn)
    out = done(store, conn, STREET={'verdict': 'ignore'}, TILE={'verdict': 'ignore'})
    assert out['then'].startswith('All 3 sets are made now.')
    store, conn = film()
    post(store, conn)
    only = {e: {'verdict': 'ignore'} for e in ('MASON', 'BRICK', 'STREET', 'T_LAY', 'TILE')}
    assert 'made now' not in done(store, conn, **only)['then']   # no set asked: no sentence about the making


def test_the_page_and_the_accept_all_line_say_it_too():
    assert 'Up to 3 sets are made first, to check the method' in W['help'] and 'at most 3 times' in W['help'] and 'The first 3' not in W['help']
    assert 'Up to 3 sets are made first, to check the method' in W['goes'].format(m=3, x=3)


def test_no_sentence_of_the_references_steps_names_an_amount():
    said = [v for k, v in vars(RS).items() if k.isupper() and isinstance(v, str) and k != 'REST_CAP'] + [str(v) for v in W.values()]
    assert not [s for s in said if '₹' in s or re.search(r'\bpaid\b|\bfree\b', s)]
    store, conn = film(fresh(cap_inr=15))   # "done" on the page past the limit: the plain sentence, no figure
    post(store, conn)
    s = saved(store)
    s['chat_round'] = {e: {'verdict': 'approve', 'quote': 'x', 'frames': i['_stamp'], 'words': '', 'pics': {}} for i in items(store, conn) if (e := i['_eid'])}
    put(store, s)
    msg = refused(lambda: PF._round_close(CF._ctx(conn, store, USER, RUN, [])))
    assert msg.startswith(RS.LIMIT_PLAIN) and not MONEY.search(msg.replace('limit', ''))


def test_the_step_of_the_sizes_is_named_for_what_it_holds():
    assert PF.SPEC_STEP == 'Sizes, materials and graphic specs'
    assert 'drawing' not in PF.SPEC_DONE.lower() and 'Drawings and materials' not in PF.SPEC_BACK


def test_the_server_sends_the_words_the_page_renders():
    words = PF.page_words()
    assert words == {'leave': 'No reference needed', 'leave_set': 'Go on without a reference', 'set': 'Make a set', 'fix': 'Make a set with words', 'loss_head': 'With no reference of it',
                     'done': {'use': 'Approved', 'set': 'Make a set', 'fix': 'Set with your words', 'own': 'Own picture', 'ignore': 'No reference'},
                     'wait_out': 'Not made', 'wait_made': 'Will be made', 'corrections_head': "The operator's corrections", 'searched_head': 'What the picture model searched', 'sets': CF.SETS_PAGE}   # design/216
