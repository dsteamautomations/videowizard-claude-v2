"""Release 2, the critic's points on e7901f5..804a720 (20 Nov 2026), each with a test that failed first. Without a database.

2. A layout is rebuilt and checked up to three times in a row with no word of the operator. When the third check in a row fails the shot is
   held: it is not named for a rebuild, it reads "waiting for you in the chat", no new scene is taken, and one card shows the latest layout
   drawing with the checker's finding and three answers: use it as it is (then it counts as checked and approved, against the check), try once
   more (three more rounds), change the shot (the operator's words; the next-step line says what the assistant does with them).
3. The next-step line names apart the shots with no guide and the shots to rebuild; the same failing scene sent again says it must differ.
4. An answer to an item of the handed-out group is taken although an earlier item became ready meanwhile.
7. Words in brackets after `must` or `should` are a mark only when they hold `still`, `motion` or `with`; both `still` and `motion` is refused.
8. A scene gets one verdict.
(Point 1 and 6: test_hotfix_guide_lane_pure.py. Point 5: test_rel2f_pure.py.)"""
import pytest

from app import chat_flow as CF, guide as G, pictures as P, takes as T, visuals_stage as V
from app.errors import Problem
from test_design151_refs_pure import NEW
from test_guide_route_pure import OTHER, frames_back, refused, scene, spec10, take_film   # noqa: F401 (take_film: the fixture)
from test_rel1d_layout_check_pure import AGAIN, CHECK, START, cards, film, rendered, said, state, verdict
from test_rel2b_group_pure import chat, end   # noqa: F401 (chat: the fixture)
from test_visuals_stage_pure import USER, saved

SCENES = 'the writers of the scene descriptions of {ids} ({n})'
REBUILD = ("the writers of the scene descriptions of {ids} ({n}), each rebuilt after its check or the operator's correction: read `vw guide status --shot S` first, "
           'it holds what must change')
FINDING = 'nothing floats (the brush, above the board)'
HELD_GATE = ('The layout of VS1 failed its check 3 times in a row: the shot is held and the operator is asked in the chat (`vw visuals next`). '
             'Send no new scene of it until they answer.')
FACINGS = ([1, 0], [0, 1], [-1, 0], [0.6, 0.8], [-0.6, 0.8], [0.8, 0.6], [-0.8, 0.6])


def variant(n):
    """The scene, different each round (n = 0: as first sent)."""
    spec = spec10()
    if n:
        spec['people'][2]['facing'] = list(FACINGS[n - 1])
    return spec


def round_(store, conn, n, ok=False):
    scene(store, conn, variant(n))
    return verdict(store, conn, frames_back(store, conn), ok)


def held_cards(store, conn):
    s = saved(store)
    ctx = {'session': s, 'plan': V.current_plan(store, s), 'run': NEW, 'store': store, 'user': USER, 'outputs': [], 'conn': conn}
    return [i for i in CF._drawing_items(ctx) if i['id'].startswith('layout-held:')]


def held3(take_film):
    store, conn = film(take_film)
    for n in range(3):
        out = round_(store, conn, n)
    assert out['next'] == ('Round 3 failed, the third check in a row: the shot is held and the operator is asked in the chat (`vw visuals next`). '
                           'Send no new scene of it until they answer. Still open: nothing floats')
    return store, conn


def due(store):
    s = saved(store)
    return T.held_due(s, V.current_plan(store, s))


# ---------- point 2: three checks in a row, then the operator ----------

def test_2_the_first_and_the_second_failed_check_are_rebuilt_with_no_card(take_film):
    store, conn = film(take_film)
    for n in range(2):
        out = round_(store, conn, n)
        assert out['next'] == 'Change the scene (one thing at a time) and upload it again: `vw guide scene`.'   # no "show the operator" at round 2
        assert said(store) == START + REBUILD.format(ids='VS1', n=1) + '.' and state(store) == ['being redone']
        assert held_cards(store, conn) == [] and cards(store, conn) == []
        assert 'change the scene' in G.status(conn, store, NEW, [], 'VS1')['next']                         # the status says what the line says


def test_2_the_third_failed_check_in_a_row_holds_the_shot_with_one_card(take_film):
    store, conn = held3(take_film)
    g = saved(store)['guides']['VS1']
    assert G.held(g) and said(store) == '' and state(store) == ['waiting for you in the chat'] and cards(store, conn) == []   # not named for a rebuild
    (card,) = held_cards(store, conn)
    assert card['id'] == f"layout-held:VS1:{g['sha256'][:10]}" and card['kind'] == 'held layout' and card['position'] == 'Step 7, AI video: a layout that did not pass its check'
    assert card['question'].endswith(': the layout of this shot failed its check 3 times in a row. What should happen to it?')
    assert card['text'] == f'The checker still finds: {FINDING}.'
    assert [(b['label'], b['choice'], bool(b.get('needs_words'))) for b in card['buttons']] == [('Use this layout as it is', 'use', False), ('Try once more', 'again', False),
                                                                                                ('Change the shot', 'change', True)]
    assert len(card['show']) == 2 and all('-plain' not in f['key'] for f in card['show'])                 # the latest layout drawing, both sheets
    assert all(CF._says(b['label']) for b in card['buttons'])                                             # each button says what happens
    assert refused(lambda: scene(store, conn, variant(3))) == HELD_GATE                                    # the gate: no fourth scene without the operator
    assert G.status(conn, store, NEW, [], 'VS1')['next'].startswith('The check of this scene failed for the third time in a row (nothing floats): the shot is held')


def test_2_use_it_as_it_is_counts_as_checked_and_approved_against_the_check(take_film):
    store, conn = held3(take_film)
    (card,) = held_cards(store, conn)
    out = card['_run']('use', 'Use it, it reads fine.', '')
    g = saved(store)['guides']['VS1']
    assert G.checked(g) and not G.rebuild(g) and not G.held(g) and g['drawing']['status'] == 'approved' and g['drawing']['verdict']['against_check'] is True
    assert g['render']['status'] == 'queued' and 'against its check' in out['next']                          # rendered as after a pass
    assert held_cards(store, conn) == [] and cards(store, conn) == [] and state(store) == ['being made'] and said(store) == ''
    logs = [p for sql, p in conn.sql if 'insert into vw2_log' in sql]
    assert len(logs) == 1 and 'used as it is, against its check: nothing floats' in str(logs[0]) and 'Use it, it reads fine.' in str(logs[0])   # the operator's decision, in the log
    rendered(store)
    assert 'the stills of VS1 (1)' in said(store)                                                           # and on to its still, with no further card


def test_2_try_once_more_allows_three_more_rounds(take_film):
    store, conn = held3(take_film)
    held_cards(store, conn)[0]['_run']('again', 'Try once more', '')
    assert said(store) == START + REBUILD.format(ids='VS1', n=1) + '.' and state(store) == ['being redone'] and held_cards(store, conn) == []
    for n in (3, 4):
        round_(store, conn, n)
        assert held_cards(store, conn) == [] and state(store) == ['being redone']
    round_(store, conn, 5)                                                                                   # the sixth failure: the third since their word
    assert len(held_cards(store, conn)) == 1 and state(store) == ['waiting for you in the chat']


def test_2_change_the_shot_needs_the_operators_words_and_the_line_says_what_to_do(take_film):
    store, conn = held3(take_film)
    (card,) = held_cards(store, conn)
    assert next(b for b in card['buttons'] if b['choice'] == 'change')['tell'] == 'Ask the operator what the shot should become: cut into shorter shots, another angle, or left out.'
    assert 'what the shot becomes' in refused(lambda: card['_run']('change', 'Change the shot', ''))
    card['_run']('change', 'Change the shot', 'Cut it in two: the walk, then the door.')
    assert held_cards(store, conn) == [] and said(store) == '' and state(store) == ['being redone']         # not named for a rebuild by itself
    assert due(store).endswith('(VS1): its layout failed its check 3 times in a row and the operator said what the shot becomes: "Cut it in two: the walk, then the door.". '
                               'Do that: a plan revision when the shot is cut, shortened, left out or becomes another kind of shot; a new scene (`vw guide scene`) when it stays one AI video shot.')
    scene(store, conn, variant(3))                                                                           # a new scene is taken again; the words are not said twice
    assert due(store) == ''


def test_2_a_pass_at_round_2_is_the_normal_card(take_film):
    store, conn = film(take_film)
    round_(store, conn, 0)
    round_(store, conn, 1, ok=True)
    (card,) = cards(store, conn)
    assert card['text'].startswith(AGAIN) and held_cards(store, conn) == [] and state(store) == ['waiting for you in the chat']


def test_2_a_live_film_whose_third_failure_came_before_this_release_is_held_at_once(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    s = saved(store)
    g = s['guides']['VS1']                                                                                   # as the older server left it: two rounds on earlier scenes, the third failed on this one
    g['rounds_before'] = 2
    g['verdicts'] = [{'round': 3, 'sha256': sha, 'pass': False, 'looks': [{'look': 'nothing floats', 'pass': False, 'where': 'the brush, above the board'}]}]
    V.save_session(store, NEW, s)
    assert len(held_cards(store, conn)) == 1 and said(store) == '' and state(store) == ['waiting for you in the chat']
    g['verdicts'][0]['round'] = 2                                                                            # the second failure only: rebuilt, as before
    g['rounds_before'] = 1
    V.save_session(store, NEW, s)
    assert held_cards(store, conn) == [] and said(store) == START + REBUILD.format(ids='VS1', n=1) + '.'


# ---------- point 8: one verdict per scene ----------

def test_8_a_second_verdict_on_the_same_scene_is_refused(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    verdict(store, conn, sha, True)
    job = saved(store)['guides']['VS1']['render']['job_id']
    msg = refused(lambda: verdict(store, conn, sha, False))                                                  # a second checker of the same scene, failing after the pass
    assert msg == ('This scene of VS1 is already judged (round 1: passed): a scene gets one verdict. Its guide is rendered and its layout drawing goes to the operator '
                   '(`vw guide status --shot VS1`).')
    g = saved(store)['guides']['VS1']
    assert len(g['verdicts']) == 1 and G.checked(g) and g['render']['job_id'] == job and len(cards(store, conn)) == 1   # nothing flipped
    G.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, False, 'no', 'the mother faces the wrong way')   # corrected: a new scene, which fails
    round_(store, conn, 1)
    msg = refused(lambda: verdict(store, conn, saved(store)['guides']['VS1']['sha256'], True))
    assert msg == 'This scene of VS1 is already judged (round 2: failed): a scene gets one verdict. Change the scene and send it again (`vw guide scene --shot VS1 --file …`).'
    assert CHECK.format(ids='VS1', n=1) not in said(store)                                                   # and the line never asks for a second one


# ---------- point 3: no guide yet, and a rebuild, are named apart ----------

def test_3_a_shot_with_no_guide_and_a_shot_to_rebuild_are_two_groups(take_film):
    store, conn = film(take_film)
    assert said(store) == START + SCENES.format(ids='VS1', n=1) + '.'                                        # no guide yet: as before
    round_(store, conn, 0)
    assert said(store) == START + REBUILD.format(ids='VS1', n=1) + '.'
    out = scene(store, conn, variant(0))                                                                     # the same scene sent again
    assert out['unchanged'] is True and out['next'] == (f'This is the scene whose check failed ({FINDING}): nothing was queued. The new scene must differ from it: '
                                                        'change what the check names and send it again.')
    round_(store, conn, 1, ok=True)
    assert scene(store, conn, variant(1))['next'] == 'This scene is already stored; nothing was queued.'     # a scene that stands: as before
    sha = saved(store)['guides']['VS1']['sha256']
    G.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, False, 'no', 'the mother faces the wrong way')
    assert said(store) == START + REBUILD.format(ids='VS1', n=1) + '.'
    assert scene(store, conn, variant(1))['next'] ==('This is the scene whose layout the operator corrected (the mother faces the wrong way): nothing was queued. '
                                                      'The new scene must differ from it: make their correction and send it again.')


# ---------- point 4: an answer of the group, while an earlier item became ready ----------

def test_4_an_answer_to_the_last_of_the_group_is_taken_when_an_earlier_item_appears_meanwhile(chat):
    chat['add'](*(end(chat, s) for s in ('D2', 'D3', 'D4', 'D5')))
    d5 = chat['items'][3]['id']
    assert len(chat['next'](many=True)['group']['items']) == 4
    chat['items'].insert(0, end(chat, 'D1'))                                                                 # an earlier drawing's end-frame became ready: the first four are now D1 to D4
    out = chat['answer'](d5, 'approve')
    assert chat['answers'] == [(d5, 'approve', '')] and [i['id'].split(':')[1] for i in out['group']['items']] == ['D1', 'D2', 'D3', 'D4']
    d1 = chat['items'][0]['id']
    chat['session']['chat_item'] = {'id': chat['items'][1]['id'], 'group': [i['id'] for i in chat['items'][1:]]}   # D1 was never handed out
    assert 'is not the decision that is open' in refused(lambda: chat['answer'](d1, 'approve'))
    chat['items'].insert(0, CF._item('question:S4:1', 'question', 'Step 6', 'S4: which wall?', lambda *a: {}, [CF._button('North', 'north')]))
    assert 'is not the decision that is open' in refused(lambda: chat['answer'](chat['items'][2]['id'], 'approve'))   # another kind in front: asked first, as before


# ---------- point 7: what is a mark ----------

def test_7_words_in_brackets_are_a_mark_only_when_they_hold_a_mark_word():
    held = P.rules_of('1. must (per the spec): The block stands.\n2. must (see note): The rods are grey.\n3. should (optional): The label fades in.\n4. must (still): Four.\n')
    assert [(r['class'], r.get('shows'), r['rule']) for r in held] == [('must', None, 'must (per the spec): The block stands.'), ('must', None, 'must (see note): The rods are grey.'),
                                                                     ('must', None, 'should (optional): The label fades in.'), ('must', 'still', 'Four.')]   # as before F13
    assert [bool(P.RULE_MARKED.match(r['rule'])) for r in held] == [False, False, False, False]              # none is refused
    for odd in ('must (stil, with D4): x', 'must (still motion): x', 'must (still, motion): x', 'should (motion; still): x', 'must (with D1, with D2): x', 'must (with): x'):
        (r,) = P.rules_of('1. ' + odd + '\n')
        assert P.RULE_MARKED.match(r['rule']) and 'shows' not in r and 'with' not in r, odd                  # a mark that cannot be read: refused at the upload, never half read
    assert V.RULE_MARK.count('`(still)`') == 1 and '`(motion, with <shot id>)`' in V.RULE_MARK              # the refusal names the accepted forms


# ---------- the served text and the skill (points 2 and 8) ----------

def test_the_served_text_and_the_skill_say_the_held_layout_and_one_verdict():
    import json
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'scripts'))
    import rel2c_wording as R
    st = next(s for s in json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
    later = next(p for p in st['parts'] if p['name'] == 'later')['text']
    assert later.count(R.VERDICT + R.HELD) == 1 and 'third check in a row' in R.HELD and 'one verdict for each scene' in R.HELD
    old = R.before(st)
    assert R.HELD not in next(p for p in old['parts'] if p['name'] == 'later')['text'] and old['prompt'] == st['prompt']
    added = sum(len(p['text'].split()) for p in st['parts']) - sum(len(p['text'].split()) for p in old['parts'])
    assert 0 < added <= 50, added
    skill = (root / 'plugin' / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8')
    retired = json.loads((root / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert skill.count(R.SKILL_NEW) == 1 and R.SKILL_OLD not in skill and R.SKILL_OLD in retired and 'show the operator what is still open' not in skill
    split = (root / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('from rel2b_wording import') < split.index('from rel2c_wording import apply as rel2c') < split.index('from d132_wording_v3 import')
    assert 'Show the operator what is still open' not in (root / 'server' / 'app' / 'guide.py').read_text(encoding='utf-8')
