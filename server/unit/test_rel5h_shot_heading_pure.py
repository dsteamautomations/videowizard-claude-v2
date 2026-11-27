"""Release 1 of 27 Nov 2026, phase 1, part H (SK approved; "the heading: let's show the voiceover"): every card names its shot by its
voiceover words.

The operators' words (through SK): a code such as S01-4 tells them nothing; the voiceover of the shot does. One heading for a shot, built by
the server in one place (`pictures.heading`): the name in words with the code last, "Voiceover:" and the narration spoken during the shot (cut
at a sentence when long), and the shot's picture where one exists. It is on the still, the Shoot card, the assistant's own question (for a
thing: the first three shots that show it, then "and N more"), and the gap card, which lists every shot of the gap in order with its
picture and takes a comment. Each test failed first. Without a database."""
import pytest

from app import chat_flow as CF, pictures as P, takes as T, visuals_stage as V
from test_design151_refs_pure import NEW
from test_guide_route_pure import KILN, MASON, TakeConn, accepted, doc_with, new_store
from test_rel3_plan_cards_pure import change, doc, film
from test_rel3b_critic_pure import ready_to_shoot, with_a_still
from test_visuals_stage_pure import RUN, USER, saved

SAID = 'The mason sets the first course. Then the line is checked.'


@pytest.fixture
def take_film():
    """The AI video film of the guide route's tests, with words spoken during VS1."""
    doc = doc_with(KILN, MASON)
    for gap in doc['gaps']:
        for sc in V.all_scenes(gap):
            for sh in sc['shots']:
                if sh['id'] == 'VS1':
                    sh['narration'] = SAID
    refs = {'R1': {'id': 'R1', 'kind': 'sheet', 'element_id': 'P1', 'status': 'approved', 'key': 'run-1/visuals/references/R1.png', 'sha256': 'sha-R1'}}
    return new_store(doc, refs, accepted=accepted(doc)), TakeConn()


def card(conn, store, prefix):
    out = CF.next_item(conn, store, USER, NEW, [])
    assert (out.get('item') or {}).get('id', '').startswith(prefix), out
    return out['item']


# ---------- the heading itself ----------

def test_the_heading_gives_the_name_in_words_the_code_last_and_the_voiceover():
    store, sess, d = film(change(doc(), lambda s, _: s['D2'].update(narration=SAID, title='The closing card')))
    plan = V.current_plan(store, sess)
    h = P.heading(sess, plan, 'D2')
    assert h['name'].endswith('(D2)') and h['voiceover'] == SAID
    assert P.heading_text(sess, plan, ['D2']) == f'Voiceover: {SAID}'             # one shot: the card's question already begins with its name
    assert P.heading(sess, plan, 'P1')['voiceover'] == P.W['no_voiceover']          # nothing is spoken during it: said, never left empty


def test_a_long_voiceover_is_cut_at_a_sentence_and_another_script_is_shown_as_written():
    long = ' '.join(f'Sentence number {n} of the narration is spoken here.' for n in range(1, 40))
    cut = P.voiceover(long)
    assert len(cut) <= P.VOICEOVER_MAX + 2 and cut.endswith('. …') and long.startswith(cut[:-2])
    assert P.voiceover('கலவை சரியாக இருக்க வேண்டும்.') == 'கலவை சரியாக இருக்க வேண்டும்.'
    one = 'word ' * 200
    assert P.voiceover(one).endswith('…') and len(P.voiceover(one)) <= P.VOICEOVER_MAX + 2   # no sentence end to cut at: cut at a word


def test_several_shots_are_listed_in_order_and_after_three_the_rest_is_counted():
    store, sess, d = film(change(doc(), lambda s, _: [s[i].update(narration=f'Words of {i}.') for i in ('D1', 'P1', 'D2')]))
    plan = V.current_plan(store, sess)
    text = P.heading_text(sess, plan, ['D1', 'P1', 'D2'])
    assert text.index('(D1)') < text.index('(P1)') < text.index('(D2)') and text.count('Voiceover: ') == 3 and 'Words of P1.' in text
    assert P.heading_text(sess, plan, ['D1', 'P1', 'D2', 'D1', 'P1'], most=3).endswith('and 2 more shots.')
    assert P.heading_text(sess, plan, ['D1', 'P1', 'D2', 'D1'], most=3).endswith('and 1 more shot.')


# ---------- the cards that named a shot by its code alone ----------

def test_the_still_and_the_shoot_card_of_an_ai_video_shot_carry_the_voiceover(take_film):
    store, conn = with_a_still(take_film)
    assert f'Voiceover: {SAID}' in card(conn, store, 'still:VS1')['message']


def test_the_shoot_card_carries_the_voiceover(take_film):
    store, conn = ready_to_shoot(take_film)
    assert f'Voiceover: {SAID}' in card(conn, store, 'shoot:VS1')['message']


def test_the_assistants_own_question_on_a_shot_carries_its_name_and_voiceover(take_film):
    store, conn = with_a_still(take_film)
    V.ask(store, USER, NEW, [], 'VS1', 'A still with a push-in, or a trial AI video?', ['Still with push-in', 'Trial AI video'])
    msg = card(conn, store, 'question:VS1')['message']
    assert f'Voiceover: {SAID}' in msg and '(VS1)' in msg


def test_a_question_on_a_thing_lists_the_shots_that_show_it(take_film):
    store, conn = with_a_still(take_film)
    s = saved(store)
    plan = V.current_plan(store, s)
    thing = next(e for sh in [sh for g in plan['gaps'] for sc in V.all_scenes(g) for sh in sc['shots'] if sh['id'] == 'VS1'] for e in sh['element_ids'])
    V.ask(store, USER, NEW, [], thing, 'Which finish does it have?', ['Rough', 'Smooth'])
    msg = card(conn, store, f'question:{thing}')['message']
    assert f'Voiceover: {SAID}' in msg and '(VS1)' in msg


def test_no_card_says_the_voiceover_twice():
    line = {'words': SAID, 'where': 'In the film at 0:10'}
    item = CF._item('take:j1', 'take', 'Step 6', 'The closing card (D2): is this drawing right for the film?', lambda *a: {}, [], text='- In the film at 0:10', name='The closing card (D2)')
    item['_line'] = line
    assert CF._message(item, '').count(SAID) == 1 and f'Voiceover: {SAID}' in CF._message(item, '')
    sheet = CF._item('picture:r1', 'picture', 'Step 5', 'The style sheet: is this picture right?', lambda *a: {}, [])
    sheet['_line'] = {'words': '', 'where': ''}                                  # a picture of no shot (the style sheet): no voiceover line at all
    assert 'Voiceover' not in CF._message(sheet, '')
    item = CF._item('x', 'still end-frame', 'Step 6', 'The closing card (D2): is it right?', lambda *a: {}, [], text=f'Voiceover: {SAID}', head=f'Voiceover: {SAID}')
    assert CF._message(item, '').count(SAID) == 1


def test_the_page_and_the_chat_use_the_same_word_for_it():
    assert P.W['words_head'] == 'Voiceover:' and T.PAGE['words_label'] == 'Voiceover'
    assert P.heading_text({'accepted': {}}, {'gaps': [], 'elements': []}, []) == ''


# ---------- the gap card ----------

def gap_ready(**words):
    """G2 of the plan-card film: its one shot D2 chosen, so the gap asks to be recorded."""
    store, sess, d = film(change(doc(), lambda s, _: [s[i].update(narration=w) for i, w in words.items()]))
    sess.update(selections={}, assets={'D2': {'kind': 'still', 'reference_id': 'K2'}, 'D1': {'kind': 'still', 'reference_id': 'K1'}, 'P1': {'kind': 'still', 'reference_id': 'K3'}},
                recorded_gaps={}, references={f'K{n}': {'id': f'K{n}', 'key': f'run-1/visuals/references/K{n}.png', 'sha256': 'a' * 64, 'status': 'approved'} for n in (1, 2, 3)})
    V.save_session(store, RUN, sess)
    ctx = {'session': sess, 'plan': V.current_plan(store, sess), 'store': store, 'conn': None, 'user': USER, 'run': RUN, 'outputs': []}
    return store, ctx


def test_the_gap_card_lists_every_shot_in_order_with_its_voiceover_and_picture():
    store, ctx = gap_ready(D1='Words of the first shot.', P1='Words of the second shot.', D2='Words of the closing shot.')
    items = {i['id']: i for i in CF._record_items(ctx)}
    one = items['record:G1']
    msg = CF._message(one, '')
    assert msg.index('(D1)') < msg.index('(P1)') and 'Voiceover: Words of the first shot.' in msg and 'Voiceover: Words of the second shot.' in msg
    assert [x['key'] for x in one['show']] == ['run-1/visuals/references/K1.png', 'run-1/visuals/references/K3.png']   # each shot's picture, in film order
    assert 'Voiceover: Words of the closing shot.' in CF._message(items['record:G2'], '') and len(items['record:G2']['show']) == 1   # a gap with one shot
    assert one['question'].endswith('Record it into the film?') and [b['label'] for b in one['buttons']] == ['Record it', 'Not yet']
    assert P.W['gap_comment'] in msg                                               # the card says what a comment does


def test_not_yet_needs_a_comment_and_a_comment_with_record_it_keeps_the_gap_open(monkeypatch):
    store, ctx = gap_ready(D2='Words.')
    recorded = []
    monkeypatch.setattr(V, 'record_gaps', lambda *a, **k: recorded.append(a[5]) or {'recorded': a[5]})
    run_ = {i['id']: i for i in CF._record_items(ctx)}['record:G2']['_run']
    with pytest.raises(ValueError, match='what should change'):
        run_('wait', 'Not yet', '')
    out = run_('record', 'Record it', 'The second picture is too dark.')            # a comment always means something should change
    assert recorded == [] and out['for_the_assistant'] == 'The second picture is too dark.'
    s = V.session_of(store, RUN, [])
    assert s['chat_record_wait']['G2']['words'] == 'The second picture is too dark.' and 'G2' not in s['recorded_gaps']
    line = CF.gap_waits(s)
    assert 'G2' in line and 'The second picture is too dark.' in line              # the next-step line says the gap waits for it
    store, ctx = gap_ready(D2='Words.')
    run_ = {i['id']: i for i in CF._record_items(ctx)}['record:G2']['_run']
    assert run_('record', 'Record it', '') == {'recorded': ['G2']} and recorded == [['G2']]
