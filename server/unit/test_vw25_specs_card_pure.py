"""4e, parts 1 and 2 (SK, 26 Nov 2026: "Approve as written"; the note: design/_work/release-25-nov/4e-specs-one-card-requirements.md).
Part 1: where the page cannot be shown, two or more sizes, materials and graphic specs that wait come on ONE card in the chat, with the
answers Yes and Correct it; one Submit records every answer through the specs' own functions (`approve_spec`, `correct_spec`). One spec alone
and `vw visuals next --one` stay one question. A material's "not this" list is not made inside the card's one call: the server names it as
still to make and `vw visuals not-this` makes it.
Part 2: a spec whose approval the server would refuse is never offered to the operator, in the chat or on the page: the approval's own check
runs before the spec is offered; the assistant's next-step line names the spec with the refusal's own words; the page shows it as with the
assistant, with the reason. The plan check's warning says "the spec is shown to the operator once this is done".
Older ways: one question per spec in the chat, kept for one spec alone and for `--one`; "warned at the check, refused at the approval", retired.
Without a database: the harness of tests/check_shared_change.py."""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
from app import chat_flow as C, page_flow as P, visual_contract as VC, visuals_stage as V   # noqa: E402
from app.errors import Problem   # noqa: E402
from test_design209_pure import PANEL, SOURCE, ans, by_key, chat, dim, drawing, material, page, plan_with, record, start   # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
STEP = 'Sizes, materials and graphic specs'
UNKNOWN = 'a size is unknown: set illustrative true; the drawing then carries "not to scale" and shows no figure for that size.'


@pytest.fixture(autouse=True)
def lists(monkeypatch):
    """The "not this" list is a model call: faked. `lists` holds every element it was asked for; the fake keeps the list as the real one does."""
    made = []

    def not_this(store, user, run, outputs, element_id):
        made.append(element_id)
        s = V.session_of(store, run, outputs)
        s.setdefault('not_this', {})[element_id] = {'lines': ['no other bond'], 'from': {'library': 0, 'model': 1, 'rejections': 0}}
        V.save_session(store, run, s)
        return {'element_id': element_id}
    monkeypatch.setattr(V, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 100.0})
    monkeypatch.setattr(V, 'not_this', not_this)
    return made


def bad(**more):
    """A drawing whose approval is refused: a size is unknown and `illustrative` is not set."""
    return {**drawing([dim('box', 'wall thickness')]), 'illustrative': False, 'label': '', **more}


def film(specs, materials=(), change=None):
    """A film with every gap accepted: gap N's one shot carries specs[N-1]; one material element for each name in `materials`."""
    plan = plan_with(specs)
    for name in materials:
        plan['elements'].append({'id': name, 'name': name.capitalize() + ' tile', 'kind': 'material', 'description': 'a tile', 'material_spec': material([dim(name, 'length', 410)])})
    if change:
        change(plan)
    return start(plan)


def nxt(store, conn, **k):
    return C.next_item(conn, store, H.USER, H.RUN, {}, **k)


def send(store, conn, card, *rows, **k):
    return C.card_answer(conn, store, H.USER, H.RUN, {}, card['id'], [{'n': n, 'choice': c, 'notes': w} for n, c, w in rows], **k)


def entries(card):
    """The names of a card's entries, in their order, as its page holds them."""
    return re.findall(r'\{n:"((?:[^"\\]|\\.)*)"', card['widget_code'])


def refused(fn):
    with pytest.raises((ValueError, Problem)) as e:
        fn()
    return str(getattr(e.value, 'message', '') or e.value)


def propose_again(store, change):
    """The assistant's new plan version; every gap is accepted again, as after a correction."""
    plan = copy.deepcopy(V.current_plan(store, H.session(store)))
    change(plan)
    H.propose(store, plan)
    V.accept(store, H.USER, H.RUN, {}, [g['gap_id'] for g in plan['gaps']], 'yes')
    return plan


def shot_of(plan, n):
    return plan['gaps'][n - 1]['scenes'][0]['shots'][0]


# ---------- part 1: the card ----------

def test_two_specs_come_on_one_card_and_one_alone_is_one_question():
    assert 'spec' in C.CARD_KINDS and C.CARD_KINDS[:2] == ('treatment line', 'plan gap')
    store, conn = film([drawing(), drawing([dim('box', 'length', 600)])])
    out = nxt(store, conn)
    card = out['card']
    assert out['item'] is None and out['needed'] is True and card['entries'] == 2 and out['waiting_after_this'] == 0
    assert card['step'] == STEP == P.SPEC_STEP and card['say_before'] == 'Here are 2 sizes, materials and graphic specs on one card. Answer each one, then press Submit all.'
    assert entries(card) == ['Shot G1-S1 (G1-S1)', 'Shot G2-S1 (G2-S1)'] and card['answers_file'] == f"work/chat/{card['id']}.answers.json"
    assert out['how'].startswith(C.CARD_HOW) and '"accept" is their Yes' in out['how'] and '"change" is Correct it' in out['how']
    assert nxt(store, conn)['card']['id'] == card['id'], 'shown again: the same card'
    assert C.handed(out) == f"handed out card {card['id']} ({STEP}, 2 lines)"
    store, conn = film([drawing(), None])                                                  # one spec alone: one question, as before
    one = nxt(store, conn)
    assert 'card' not in one and one['item']['kind'] == 'spec' and one['item']['question'] == 'Shot G1-S1 (G1-S1): are the parts right?'
    assert [b['label'] for b in one['item']['buttons']] == ['Yes', 'Correct it']


def test_an_entry_shows_what_the_one_question_shows_its_name_the_rows_above_its_parts_its_sizes_and_its_notes():
    def change(plan):
        shot_of(plan, 1).update(depicts='the box and its lid', narration='Fillers replace the tension zone.')
    store, conn = film([drawing([dim('box', 'length', 600), dim('box', 'wall thickness')]), drawing([dim('Box', 'Length', 650)])], ('panel',), change)
    s = H.session(store)
    s['treatment'] = {'gaps': [{'gap_id': 'G1', 'depicts': ['a box with its lid lifted']}]}
    V.save_session(store, H.RUN, s)
    items = chat(store, conn)
    code = nxt(store, conn)['card']['widget_code']
    assert len(items) == 3
    for item in items:                                                                     # every line of the one question is on the card, word for word
        for line in item['text'].splitlines():
            line = line[2:] if line.startswith('- ') else line
            assert json.dumps(line, ensure_ascii=False)[1:-1] in code, line
    d = next(i for i in items if i['id'].startswith('spec:G1-S1:'))
    for said in ('In the film at 0:00.0 to 0:04.0 (4.0 s) · Gap G1, Title 1', 'The words under it: Fillers replace the tension zone.', 'Shows: the box and its lid',
                 'What you accepted for this drawing: a box with its lid lifted', 'Parts: box, lid', 'box length: 600 mm (from ' + SOURCE + ')', 'Not known, so no figure is shown: box wall thickness',
                 'Note: box length: differs from Shot G2-S1 (G2-S1): 650 mm', 'Are the parts and the known sizes right?', 'Are these facts right?', 'How it is laid: flat, the long side to the viewer'):
        assert json.dumps(said, ensure_ascii=False)[1:-1] in code, said
    assert '**' not in code and 'S_DIAGRAM' not in code and d['question'].startswith('Shot G1-S1 (G1-S1)')
    assert max(len(line) for line in code.split('\n')) < 2000 and '__DATA__' not in code and code.count('</script>') == 1


def test_the_two_answers_read_yes_and_correct_it_and_correct_it_needs_the_operators_words():
    store, conn = film([drawing(), drawing()])
    card = nxt(store, conn)['card']
    code = card['widget_code']
    assert 'lab:["Yes","Correct it"' in code and 'choose Yes or Correct it' in code and 'Accept or Change this' not in code
    said = refused(lambda: send(store, conn, card, (1, 'accept', ''), (2, 'change', '  ')))
    assert said == 'Entry 2: say what should change (notes).' and not H.session(store).get('spec_approvals')
    page_file = Path(C.__file__).with_name('chat_card.html').read_text(encoding='utf-8')   # the card's page: the answers' words come with the card; without them, as before
    assert "D.lab||['Accept','Change this'" in page_file and "choice:'accept'" in page_file and "choice:'change'" in page_file
    store, conn = H.start(accept=False)                                                    # a plan card keeps Accept and Change this
    plan_card = nxt(store, conn)['card']
    assert plan_card['step'] == 'Plan' and 'lab:' not in plan_card['widget_code'] and 'choose Accept or Change this' in plan_card['widget_code']


def test_one_submit_records_every_answer_through_the_specs_own_functions(monkeypatch):
    calls = []
    approve, correct = V.approve_spec, V.correct_spec
    monkeypatch.setattr(V, 'approve_spec', lambda store, user, run, outputs, key, quote, **k: calls.append(('approve', key)) or approve(store, user, run, outputs, key, quote, **k))
    monkeypatch.setattr(V, 'correct_spec', lambda store, user, run, outputs, key, words: calls.append(('correct', key, words)) or correct(store, user, run, outputs, key, words))
    store, conn = film([drawing(), drawing([dim('box', 'length', 600)]), drawing(view='plan')], ('panel',))
    card = nxt(store, conn)['card']
    assert entries(card) == ['Panel tile', 'Shot G1-S1 (G1-S1)', 'Shot G2-S1 (G2-S1)', 'Shot G3-S1 (G3-S1)'], 'the materials first, then the drawings in the order of the film'
    got = send(store, conn, card, (1, 'accept', ''), (2, 'accept', ''), (3, 'change', 'the box is 650 long'), (4, 'accept', ''))
    assert calls == [('correct', 'G2-S1', 'the box is 650 long'), ('approve', 'element:panel'), ('approve', 'G1-S1'), ('approve', 'G3-S1')], 'the corrections first, as on the page'
    s = H.session(store)
    assert set(s['spec_approvals']) == {'element:panel', 'G1-S1', 'G3-S1'} and s['spec_corrections']['G2-S1']['words'] == 'the box is 650 long'
    assert all(a['quote'] == f"Yes on the card ({card['id']})" and a['by'] == 'u1' for a in s['spec_approvals'].values())
    assert got['answered_card'] == card['id'] and got['recorded'] == [1, 2, 3, 4] and got['not_open'] == [] and got['refused'] == [] and got['again'] == []
    assert got['item'] is None and not got.get('card') and got['needed'] is False, 'nothing is left to answer'
    assert '4 answer(s) recorded.' in got['then'] and 'asked for a correction in entries 3' in got['then']
    assert chat(store, conn) == [] and page(store, conn)['summary'] == '1 material and 3 graphic specs: 0 to answer, 3 recorded, 1 with the assistant.', 'the page reads the same record'


def test_more_than_twelve_come_as_cards_of_ten_and_twelve_as_one():
    store, conn = film([drawing() for _ in range(13)])
    out = nxt(store, conn)
    assert out['card']['entries'] == 10 and out['waiting_after_this'] == 3 and entries(out['card']) == [f'Shot G{n}-S1 (G{n}-S1)' for n in range(1, 11)]
    got = send(store, conn, out['card'], *[(n, 'accept', '') for n in range(1, 11)])
    assert got['recorded'] == list(range(1, 11)) and got['card']['entries'] == 3 and got['card']['id'] != out['card']['id'] and got['waiting_after_this'] == 0
    assert entries(got['card']) == ['Shot G11-S1 (G11-S1)', 'Shot G12-S1 (G12-S1)', 'Shot G13-S1 (G13-S1)']
    store, conn = film([drawing() for _ in range(12)])
    assert nxt(store, conn)['card']['entries'] == 12


def test_only_the_specs_are_on_the_card_and_what_else_waits_is_asked_after_it_in_its_order():
    store, conn = film([drawing(), drawing()], ('panel',))
    V.ask(store, H.USER, H.RUN, {}, 'G1-S1', 'Which side faces the viewer?', ['The long side', 'The short side'])
    out = nxt(store, conn)
    assert out['card']['entries'] == 3 and out['waiting_after_this'] == 1 and 'Which side' not in out['card']['widget_code']
    got = send(store, conn, out['card'], (1, 'accept', ''), (2, 'accept', ''), (3, 'accept', ''))
    assert got['item']['kind'] == 'question' and got['item']['question'] == 'Which side faces the viewer?' and not got.get('card')
    assert 'What comes next is in this answer' in got['then']
    store, conn = film([drawing(), None])                                                  # one spec and a question: today's order, the question first
    V.ask(store, H.USER, H.RUN, {}, 'G1-S1', 'Which side faces the viewer?', ['The long side', 'The short side'])
    first = nxt(store, conn)
    assert first['item']['kind'] == 'question' and 'card' not in first
    second = C.answer(conn, store, H.USER, H.RUN, {}, first['item']['id'], 'c1', 'The long side')
    assert second['item']['kind'] == 'spec' and 'card' not in second


def test_next_one_still_asks_one_at_a_time_and_a_card_shown_before_is_no_longer_answered():
    store, conn = film([drawing(), drawing()], ('panel',))
    card = nxt(store, conn)['card']
    one = nxt(store, conn, one=True)
    assert 'card' not in one and one['item']['id'].startswith('spec:element:panel:') and one['item']['waiting_after_this'] == 2
    assert '`vw visuals decide --one --item' in one['item']['how']
    assert 'not the card that is open' in refused(lambda: send(store, conn, card, (1, 'accept', ''), (2, 'accept', ''), (3, 'accept', '')))
    two = C.answer(conn, store, H.USER, H.RUN, {}, one['item']['id'], 'yes', 'Yes', '', True)
    assert two['item']['id'].startswith('spec:G1-S1:') and 'card' not in two and 'element:panel' in H.session(store)['spec_approvals']
    three = C.answer(conn, store, H.USER, H.RUN, {}, two['item']['id'], 'correct', '', 'the lid is hinged', True)
    assert three['item']['id'].startswith('spec:G2-S1:') and H.session(store)['spec_corrections']['G1-S1']['words'] == 'the lid is hinged'


def test_the_page_is_unchanged():
    store, conn = film([drawing([dim('box', 'length', 600)]), drawing()], ('panel',))
    p = page(store, conn)
    assert p['step'] == STEP and [(l['key'], l['state']) for l in p['lines']] == [('element:panel', 'open'), ('G1-S1', 'open'), ('G2-S1', 'open')]
    assert [l['item'] for l in p['lines']] == [i['id'] for i in chat(store, conn)] and 'then' not in p
    assert all([(b['label'], b['choice'], b['needs_words']) for b in l['buttons']] == [('Yes', 'yes', False), ('Correct it', 'correct', True)] for l in p['lines'])
    assert all(set(l) <= {'line', 'key', 'title', 'state', 'item', 'ask', 'spec', 'buttons', 'rows'} for l in p['lines'])
    assert p['summary'] == '1 material and 2 graphic specs: 3 to answer, 0 recorded, 0 with the assistant.'


# ---------- part 1: the edge cases ----------

def test_a_spec_that_changed_while_the_card_was_open_is_named_as_no_longer_open_and_the_others_are_recorded():
    store, conn = film([drawing([dim('box', 'length', 600)]), drawing(), drawing(view='plan')])
    card = nxt(store, conn)['card']
    propose_again(store, lambda plan: shot_of(plan, 1)['drawing_spec']['dimensions'][0].update(value=640))   # the assistant corrected it meanwhile
    got = send(store, conn, card, (1, 'accept', ''), (2, 'accept', ''), (3, 'change', 'seen from the side'))
    s = H.session(store)
    assert got['recorded'] == [2, 3] and got['not_open'] == [1] and 'G1-S1' not in s['spec_approvals'] and 'G2-S1' in s['spec_approvals'] and 'G3-S1' in s['spec_corrections']
    assert 'no longer open (recorded before, or changed since the card): entries 1' in got['then']
    assert got['item']['id'].startswith('spec:G1-S1:') and '640 mm' in got['item']['text'], 'it is asked again as it is now, alone'


def test_the_same_card_sent_twice_is_recorded_once(monkeypatch):
    store, conn = film([drawing(), drawing()])
    card = nxt(store, conn)['card']
    assert send(store, conn, card, (1, 'accept', ''), (2, 'change', 'the lid is hinged'))['recorded'] == [1, 2]
    before = copy.deepcopy(H.session(store))
    monkeypatch.setattr(V, 'approve_spec', lambda *a, **k: pytest.fail('recorded twice'))
    monkeypatch.setattr(V, 'correct_spec', lambda *a, **k: pytest.fail('recorded twice'))
    again = send(store, conn, card, (1, 'change', 'something else'), (2, 'accept', ''))
    assert again['already'] is True and again['recorded'] == [] and 'nothing was changed' in again['then']
    after = H.session(store)
    assert after['spec_approvals'] == before['spec_approvals'] and after['spec_corrections'] == before['spec_corrections']


def test_a_send_that_stopped_halfway_is_sent_again_and_each_answer_counts_once(lists):
    store, conn = film([drawing(), drawing()], ('panel',))
    card = nxt(store, conn)['card']
    V.correct_spec(store, H.USER, H.RUN, {}, 'G1-S1', 'the lid is hinged')                # the first attempt recorded entries 1 and 2, then stopped
    V.approve_spec(store, H.USER, H.RUN, {}, 'element:panel', 'Yes')
    at = H.session(store)['spec_approvals']['element:panel']['at']
    got = send(store, conn, card, (1, 'accept', ''), (2, 'change', 'the lid is hinged'), (3, 'accept', ''))
    s = H.session(store)
    assert got['recorded'] == [1, 2, 3] and got['not_open'] == [] and s['spec_approvals']['element:panel']['at'] == at and 'G2-S1' in s['spec_approvals']
    assert 'asked for a correction in entries 2' in got['then']


def test_an_entry_left_unanswered_records_nothing_and_the_card_says_which():
    store, conn = film([drawing(), drawing(), drawing(view='plan')])
    card = nxt(store, conn)['card']
    assert refused(lambda: send(store, conn, card, (1, 'accept', ''), (3, 'accept', ''))) == 'Answer every entry of the card first; still to answer: 2. Nothing was recorded.'
    assert 'twice' in refused(lambda: send(store, conn, card, (1, 'accept', ''), (1, 'accept', ''), (2, 'accept', ''), (3, 'accept', '')))
    assert 'no entry 4' in refused(lambda: send(store, conn, card, (4, 'accept', '')))
    assert not H.session(store).get('spec_approvals') and nxt(store, conn)['card']['id'] == card['id'], 'the card stays open'
    page_file = Path(C.__file__).with_name('chat_card.html').read_text(encoding='utf-8')
    assert "'Answer these first: '+m.map(i=>i+1).join(', ')" in page_file, 'the card itself names the entries before anything is sent'


def test_a_materials_not_this_list_is_made_after_the_answers_are_recorded_not_inside_the_cards_call(lists, monkeypatch):
    store, conn = film([drawing()], ('panel', 'tile', 'slab'))
    card = nxt(store, conn)['card']
    got = send(store, conn, card, *[(n, 'accept', '') for n in range(1, 5)])
    s = H.session(store)
    assert lists == [], 'no model call inside the one request, however many materials'
    assert got['recorded'] == [1, 2, 3, 4] and {'element:panel', 'element:tile', 'element:slab'} <= set(s['spec_approvals']) and not s.get('not_this')
    due = V.not_this_due(V.current_plan(store, s), s)
    assert due and due in got['then'] and '`vw visuals not-this --element <id>`' in due and 'panel, tile, slab' in due and 'the approval stands' in due
    assert due in nxt(store, conn)['then'], 'said again by every next call until the lists are there'
    V.not_this(store, H.USER, H.RUN, {}, 'panel')                                          # the assistant runs the command for one
    s = H.session(store)
    assert 'tile, slab' in V.not_this_due(V.current_plan(store, s), s) and 'panel' not in V.not_this_due(V.current_plan(store, s), s)
    for eid in ('tile', 'slab'):
        V.not_this(store, H.USER, H.RUN, {}, eid)
    assert V.not_this_due(V.current_plan(store, H.session(store)), H.session(store)) == '' and 'not-this' not in str(nxt(store, conn).get('then') or '')

    def fails(*a, **k):
        raise Problem(502, 'NOT_THIS_FAILED', 'The not-this call failed')
    store, conn = film([drawing()], ('panel', 'tile'))                                     # making it fails: the material stays approved, and the list is still named
    card = nxt(store, conn)['card']
    send(store, conn, card, *[(n, 'accept', '') for n in range(1, 4)])
    monkeypatch.setattr(V, 'not_this', fails)
    assert 'failed' in refused(lambda: V.not_this(store, H.USER, H.RUN, {}, 'panel'))
    s = H.session(store)
    assert V.material_approved(s, V.current_plan(store, s)['elements'][-1]) and 'panel, tile' in nxt(store, conn)['then']


def test_one_material_alone_and_the_page_still_make_the_list_with_the_approval(lists):
    store, conn = film([None], ('panel',))
    one = nxt(store, conn)
    C.answer(conn, store, H.USER, H.RUN, {}, one['item']['id'], 'yes', 'Yes')
    assert lists == ['panel'] and V.not_this_due(V.current_plan(store, H.session(store)), H.session(store)) == ''
    lists.clear()
    store, conn = film([drawing()], ('panel', 'tile'))
    record(store, conn, [ans(l, 'yes') for l in page(store, conn)['lines']])
    assert sorted(lists) == ['panel', 'tile']


def test_a_size_shown_on_an_earlier_entry_is_already_confirmed_on_the_later_ones_and_a_yes_that_rested_on_a_corrected_size_is_asked_again():
    repeat = lambda *more: drawing(PANEL + list(more))
    store, conn = start(plan_with([repeat(), repeat(dim('box', 'length', 600))], PANEL))
    card = nxt(store, conn)['card']
    code = card['widget_code']
    assert code.count('panel length: 410 mm') == 1 and code.count('Already confirmed: panel: length 410 mm, width 235 mm') == 2, 'in full once, at the material'
    got = send(store, conn, card, (1, 'accept', ''), (2, 'accept', ''), (3, 'accept', ''))  # all Yes: all recorded
    assert got['recorded'] == [1, 2, 3] and got['again'] == []
    store, conn = start(plan_with([repeat(), drawing([dim('box', 'length', 600)])], PANEL))
    card = nxt(store, conn)['card']
    got = send(store, conn, card, (1, 'change', 'the panel is 400 long, not 410'), (2, 'accept', ''), (3, 'accept', ''))   # as on the page (design/209)
    s = H.session(store)
    assert got['recorded'] == [1, 3] and got['again'] == [2] and 'G1-S1' not in s.get('spec_approvals', {}) and 'G2-S1' in s['spec_approvals']
    assert 'rested on a size' in got['then'] and 'entries 2' in got['then']
    assert got['item']['id'].startswith('spec:G1-S1:') and 'Sizes to confirm' in got['item']['text'], 'asked again, its sizes in full now'


def test_a_long_spec_is_shown_whole():
    big = drawing([dim(f'part {i:02d}', 'length ' + 'x' * 150, 100 + i) for i in range(60)])   # the most sizes a spec may hold
    store, conn = film([big, drawing()])
    item = chat(store, conn)[0]
    code = nxt(store, conn)['card']['widget_code']
    assert len(item['text']) < 6200 and 'part 59' not in item['text'], 'the one question cuts the spec at 6000 characters, as before'
    assert max(len(line) for line in code.split('\n')) < 2000, 'in lines short enough to be read back whole'
    assert all(f'part {i:02d} length' in code.replace('"+\n"', '') for i in range(60))


def test_one_answer_refused_for_a_real_reason_names_the_entry_and_the_others_are_recorded(monkeypatch):
    store, conn = film([drawing(), drawing(), drawing(view='plan')])
    card = nxt(store, conn)['card']
    approve = V.approve_spec

    def one_fails(store, user, run, outputs, key, quote, **k):
        V.need(key != 'G2-S1', 'shot G2-S1: the server could not approve it.')
        return approve(store, user, run, outputs, key, quote, **k)
    monkeypatch.setattr(V, 'approve_spec', one_fails)
    got = send(store, conn, card, (1, 'accept', ''), (2, 'accept', ''), (3, 'accept', ''))
    assert got['recorded'] == [1, 3] and got['refused'] == [{'n': 2, 'name': 'Shot G2-S1 (G2-S1)', 'message': 'shot G2-S1: the server could not approve it.'}]
    assert set(H.session(store)['spec_approvals']) == {'G1-S1', 'G3-S1'}
    assert 'Refused: entry 2 (Shot G2-S1 (G2-S1)): shot G2-S1: the server could not approve it.' in got['then'] and '2 answer(s) recorded.' in got['then']
    assert send(store, conn, card, (1, 'accept', ''), (2, 'accept', ''), (3, 'accept', ''))['already'] is True, 'the card is spent: the refused one comes again by itself'


# ---------- part 2: a Yes that would be refused is not asked ----------

def test_the_check_before_a_spec_is_offered_is_the_approvals_own():
    """Each kind of refusal the approval gives, and a spec it takes: offered exactly when the approval would take it."""
    untried = drawing([dim('box', 'wall thickness')])
    untried['dimensions'][0]['tried'] = ''
    cases = {'unknown size, not illustrative': bad(), 'unknown size, nothing tried': untried, 'no sizes': drawing(), 'known size': drawing([dim('box', 'length', 600)]),
             'unknown size, said so': drawing([dim('box', 'wall thickness')])}
    for name, spec in cases.items():
        store, conn = film([spec, drawing(view='plan')])
        s = H.session(store)
        plan = V.current_plan(store, s)
        fault = V.spec_fault(plan, shot=shot_of(plan, 1))
        offered = 'G1-S1' in [w['group'] for w in V.waiting(s, plan, 'VW-T', [])]
        try:
            V.approve_spec(store, H.USER, H.RUN, {}, 'G1-S1', 'Yes')
            said = ''
        except Problem as exc:
            said = exc.message
        assert fault == said and offered == (not said), name
        assert V.specs_held(plan, s) == ({'G1-S1': said} if said else {}), name
    wrong = material([dim('panel', 'length')])                                             # a material: the same, by its own check
    wrong['dimensions'][0]['tried'] = ''
    plan = plan_with([None])
    plan['elements'].append({'id': 'panel', 'name': 'Floor panel', 'kind': 'material', 'description': 'a floor panel', 'material_spec': wrong})
    store, conn = start(plan)
    s = H.session(store)
    said = refused(lambda: V.approve_spec(store, H.USER, H.RUN, {}, 'element:panel', 'Yes'))
    assert said.startswith('material spec of panel: panel length is unknown: record the sources tried') and V.specs_held(V.current_plan(store, s), s) == {'element:panel': said}
    assert V.waiting(s, V.current_plan(store, s), 'VW-T', []) == [] and 'spec_approvals' not in H.session(store)


def test_a_spec_that_would_be_refused_is_not_offered_in_the_chat_and_is_named_to_the_assistant():
    store, conn = film([drawing(), bad(), drawing(view='plan')])
    out = nxt(store, conn)
    said = 'shot G2-S1: ' + UNKNOWN
    assert refused(lambda: V.approve_spec(store, H.USER, H.RUN, {}, 'G2-S1', 'Yes')) == said
    assert entries(out['card']) == ['Shot G1-S1 (G1-S1)', 'Shot G3-S1 (G3-S1)'] and out['waiting_after_this'] == 0
    assert [i['id'].split(':')[1] for i in chat(store, conn)] == ['G1-S1', 'G3-S1']
    assert out['then'].startswith('1 spec is not shown to the operator yet, because its approval would be refused: Shot G2-S1 (G2-S1): ' + said)
    assert 'out/visual-plan.json' in out['then'] and 'propose the plan again' in out['then'] and 'shown to the operator once this is done' in out['then']
    got = send(store, conn, out['card'], (1, 'accept', ''), (2, 'accept', ''))
    assert got['recorded'] == [1, 2] and got['item'] is None and got['needed'] is False and 'Shot G2-S1 (G2-S1): ' + said in got['then']
    assert got['working'] == ['Sizes, materials and graphic specs: 1 is with the assistant, to be completed before it is shown to you.']
    one = nxt(film([drawing(), bad()])[0], H.Conn())                                       # one that can be asked, one that cannot: the one, alone
    assert one['item']['id'].startswith('spec:G1-S1:') and 'card' not in one and 'Shot G2-S1 (G2-S1): ' + said in one['then']


def test_the_page_shows_such_a_spec_as_with_the_assistant_with_the_reason():
    store, conn = film([drawing(), bad()], ('panel',))
    p = page(store, conn)
    held = by_key(p)['G2-S1']
    assert held == {'line': 'l03', 'key': 'G2-S1', 'title': 'Shot G2-S1 (G2-S1)', 'state': 'with_assistant', 'note': '',
                    'text': 'Not ready for your answer yet. The assistant completes it first: shot G2-S1: ' + UNKNOWN}
    assert [(l['key'], l['state']) for l in p['lines']] == [('element:panel', 'open'), ('G1-S1', 'open'), ('G2-S1', 'with_assistant')]
    assert p['summary'] == '1 material and 2 graphic specs: 2 to answer, 0 recorded, 1 with the assistant.' and p['open'] is True
    assert p['then'].startswith('1 spec is not shown to the operator yet') and 'Shot G2-S1 (G2-S1): shot G2-S1: ' + UNKNOWN in p['then']
    r = record(store, conn, [ans(l, 'yes') for l in p['lines'] if l['state'] == 'open'] + [{'key': 'G2-S1', 'item': '', 'choice': 'yes'}])
    assert sorted(r['recorded']) == ['G1-S1', 'element:panel'] and r['stale'] == ['G2-S1'] and r['refused'] == [] and 'G2-S1' not in H.session(store)['spec_approvals']
    assert r['then'].startswith('1 spec is not shown to the operator yet') and 'Shot G2-S1 (G2-S1): shot G2-S1: ' + UNKNOWN in r['then'], 'the step is not finished: the assistant has the spec and what is missing'
    assert P.SPEC_DONE not in r['then'] and P.SPEC_BACK not in r['then'], 'the operator sent nothing back, and not every spec is approved'
    assert r['page']['step'] == STEP and r['page']['open'] is False and 'with the assistant' in r['page']['note'].lower()


def test_when_every_spec_would_be_refused_there_is_no_card_and_the_assistant_has_the_list():
    store, conn = film([bad(), bad()])
    out = nxt(store, conn)
    assert out['item'] is None and 'card' not in out and out['needed'] is False
    assert out['working'] == ['Sizes, materials and graphic specs: 2 are with the assistant, to be completed before they are shown to you.']
    assert out['then'].startswith('2 specs are not shown to the operator yet, because their approval would be refused: ')
    assert 'Shot G1-S1 (G1-S1): shot G1-S1: ' + UNKNOWN in out['then'] and 'Shot G2-S1 (G2-S1): shot G2-S1: ' + UNKNOWN in out['then']
    p = page(store, conn)
    assert p['step'] == STEP and p['open'] is False and [l['state'] for l in p['lines']] == ['with_assistant'] * 2 and all('buttons' not in l and 'item' not in l for l in p['lines'])
    assert p['summary'] == '2 graphic specs: 0 to answer, 0 recorded, 2 with the assistant.' and p['then'] == out['then']
    assert V.waiting(H.session(store), V.current_plan(store, H.session(store)), 'VW-T', []) == []


def test_the_answer_that_accepts_the_plan_on_its_card_names_the_specs_that_are_with_the_assistant():
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    H.propose(store, plan_with([bad(), bad()]))
    card = nxt(store, conn)['card']
    assert card['step'] == 'Plan' and 'not shown to the operator' not in str(nxt(store, conn).get('then') or ''), 'no gap is accepted yet: no spec is in turn'
    got = send(store, conn, card, (1, 'accept', ''), (2, 'accept', ''))
    assert got['recorded'] == [1, 2] and got['item'] is None and not got.get('card') and got['needed'] is False
    assert 'No decision waits now' in got['then'] and '2 specs are not shown to the operator yet' in got['then'] and 'Shot G2-S1 (G2-S1): shot G2-S1: ' + UNKNOWN in got['then']


def test_once_the_assistant_fixed_it_in_a_new_plan_version_the_spec_is_offered_on_the_next_call():
    store, conn = film([drawing(), bad()])
    assert nxt(store, conn)['item']['id'].startswith('spec:G1-S1:')
    propose_again(store, lambda plan: shot_of(plan, 2)['drawing_spec'].update(illustrative=True, label='Illustrative, not to scale'))
    out = nxt(store, conn)
    assert entries(out['card']) == ['Shot G1-S1 (G1-S1)', 'Shot G2-S1 (G2-S1)'] and 'not shown to the operator' not in str(out.get('then') or '')
    assert 'Not to scale.' in out['card']['widget_code'] and 'Not known, so no figure is shown: box wall thickness' in out['card']['widget_code'], 'no rule about sizes changed: unknown is allowed'
    assert [l['state'] for l in page(store, conn)['lines']] == ['open', 'open'] and 'then' not in page(store, conn)
    got = send(store, conn, out['card'], (1, 'accept', ''), (2, 'accept', ''))
    assert got['recorded'] == [1, 2] and got['refused'] == []


def test_a_spec_approved_before_this_release_stays_approved():
    store, conn = film([bad(), drawing()])
    s = H.session(store)
    s['spec_approvals'] = {'G1-S1': {'digest': V.spec_digest(shot_of(V.current_plan(store, s), 1)['drawing_spec']), 'quote': 'Approved', 'by': 'u1', 'at': '2026-11-20T10:00:00+00:00'}}   # as the server recorded it before
    V.save_session(store, H.RUN, s)
    plan = V.current_plan(store, s)
    assert V.specs_held(plan, s) == {} and [w['group'] for w in V.waiting(s, plan, 'VW-T', [])] == ['G2-S1']
    out = nxt(store, conn)
    assert out['item']['id'].startswith('spec:G2-S1:') and 'not shown to the operator' not in str(out.get('then') or '')
    assert [(l['key'], l['state']) for l in page(store, conn)['lines']] == [('G1-S1', 'recorded'), ('G2-S1', 'open')]
    assert H.session(store)['spec_approvals']['G1-S1']['at'] == '2026-11-20T10:00:00+00:00'


def diagram(plan):
    """Gap 1's drawing draws a real thing of the plan (the wall), which carries a proportion of its own: its spec needs none."""
    shot_of(plan, 1).update(graphic_kind='diagram')
    shot_of(plan, 1)['drawing_spec'].update(proportions=[])
    plan['elements'][0].update(material_spec=material(PANEL))


def test_an_approval_still_refused_because_the_plan_changed_between_the_card_and_the_answer_is_refused_by_name():
    store, conn = film([drawing(), drawing(view='plan')], change=diagram)
    V.approve_spec(store, H.USER, H.RUN, {}, 'element:wall', 'Yes')
    card = nxt(store, conn)['card']
    assert entries(card) == ['Shot G1-S1 (G1-S1)', 'Shot G2-S1 (G2-S1)']
    propose_again(store, lambda plan: plan['elements'][0].pop('material_spec'))     # the wall lost its sizes: the drawing's own spec is as the card showed it
    got = send(store, conn, card, (1, 'accept', ''), (2, 'accept', ''))
    why = 'shot G1-S1: this diagram draws a real thing of the plan, and its spec has no proportion and no known size.'
    assert got['recorded'] == [2] and got['not_open'] == [] and [(r['n'], r['name']) for r in got['refused']] == [(1, 'Shot G1-S1 (G1-S1)')] and got['refused'][0]['message'].startswith(why)
    assert 'Refused: entry 1 (Shot G1-S1 (G1-S1)): ' + why in got['then'] and set(H.session(store)['spec_approvals']) >= {'G2-S1'} and 'G1-S1' not in H.session(store)['spec_approvals']
    assert got['item'] is None and '1 spec is not shown to the operator yet' in got['then'], 'it is with the assistant now, with the same words'
    store, conn = film([drawing(), drawing(view='plan')], change=diagram)                  # a correction to it is not taken either: it is no longer open, as on the page
    V.approve_spec(store, H.USER, H.RUN, {}, 'element:wall', 'Yes')
    card = nxt(store, conn)['card']
    propose_again(store, lambda plan: plan['elements'][0].pop('material_spec'))
    got = send(store, conn, card, (1, 'change', 'the wall is taller'), (2, 'accept', ''))
    assert got['recorded'] == [2] and got['not_open'] == [1] and got['refused'] == [] and not H.session(store).get('spec_corrections')
    store, conn = film([drawing(), drawing(view='plan')], change=diagram)                  # the same on the page: refused on its line, by name
    V.approve_spec(store, H.USER, H.RUN, {}, 'element:wall', 'Yes')
    lines = page(store, conn)['lines']
    propose_again(store, lambda plan: plan['elements'][0].pop('material_spec'))
    r = record(store, conn, [ans(l, 'yes') for l in lines if l['state'] == 'open'])
    assert r['recorded'] == ['G2-S1'] and r['stale'] == [] and [x['key'] for x in r['refused']] == ['G1-S1'] and r['refused'][0]['message'].startswith(why)
    assert by_key(r['page'])['G1-S1']['state'] == 'with_assistant' and why in by_key(r['page'])['G1-S1']['text'] and r['then'].startswith(P.SPEC_REFUSED) and why in r['then']


def test_the_plan_checks_warning_keeps_its_words_and_says_when_the_spec_is_shown():
    spec = VC.DrawingSpec.model_validate(bad())
    w, = VC._research_warning('shot S1', spec, shot_id='S1')
    assert w['kind'] == 'spec_unresearched' and w['shot_id'] == 'S1'
    assert w['message'] == 'shot S1: ' + UNKNOWN + ' (the spec is shown to the operator once this is done; the research comes after the picture search)'
    assert 'refused when the spec is approved' not in w['message']
    assert VC._research_warning('shot S1', VC.DrawingSpec.model_validate(drawing([dim('box', 'wall thickness')]))) == [], 'an unknown size that says so is no warning'


# ---------- the words, and the assistant's instructions ----------

def test_the_new_words_say_operator_and_assistant_and_never_user():
    store, conn = film([drawing(), drawing(), bad()], ('panel', 'tile'))
    out = nxt(store, conn)
    got = send(store, conn, out['card'], *[(n, 'accept', '') for n in range(1, 5)])
    p = page(store, conn)
    text = ' '.join([out['how'], out['then'], out['card']['say_before'], out['card']['widget_code'].split('<script>')[1], got['then'], ' '.join(got['working']), p['then'], json.dumps(p['lines'])])
    assert not re.search(r'\busers?\b', text, re.I) and 'operator' in text and 'assistant' in text


def test_the_instructions_say_the_card_for_the_specs_and_what_happens_to_a_spec_that_is_not_ready():
    d = json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    plan = next(p for p in st['parts'] if p['name'] == 'plan')['text']
    sys.path.insert(0, str(ROOT / 'scripts'))
    import specs_card_wording as W
    for where, old, new in W.PAIRS:
        text = st['prompt'] if where == 'common' else next(p for p in st['parts'] if p['name'] == where)['text']
        assert text.count(new) == (1 if where == 'common' else 2) and old not in text, (where, old[:60])   # a part's sentence stands once for each kind of film
    assert 'two or more come on one card' in plan and 'it is shown to the operator once this is done' in plan
    assert 'the treatment, the plan and the sizes, materials and graphic specs' in st['prompt'] and 'for two or more specs, the server answers' in st['prompt']
    was = W.before(st)
    parts = copy.deepcopy(st['parts'])
    assert W.apply(st['prompt'], parts) == st['prompt'] and parts == st['parts'], 'applying twice changes nothing'
    assert was != st and W.apply(was['prompt'], was['parts']) == st['prompt'] and was['parts'] == st['parts'], 'and from the text before it, it gives the text of today'
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    everything = json.dumps(d, ensure_ascii=False) + ''.join(f.read_text(encoding='utf-8') for folder in ('agents', 'commands') for f in (ROOT / 'plugin' / folder).glob('*.md'))
    for s in W.RETIRED:
        assert s in retired and len(s.split()) >= 4 and s not in everything, s
    assert 'specs_card_wording' in (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')


# ---------- in a browser: the card as the operator uses it, and the page's line ----------

@pytest.fixture
def browser():
    sync_api = pytest.importorskip('playwright.sync_api')
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            yield b
            b.close()
    except sync_api.Error as exc:   # no browser on this machine
        pytest.skip(f'no headless browser: {exc}')


def test_in_a_browser_the_card_reads_yes_and_correct_it_and_one_submit_gives_every_answer(browser):
    store, conn = film([drawing([dim('box', 'length', 600)]), drawing()], ('panel',))
    card = nxt(store, conn)['card']
    pg = browser.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.set_content('<!doctype html><html><body><script>window.sent=[];function sendPrompt(t){window.sent.push(t)}</script>' + card['widget_code'] + '</body></html>')
    assert pg.locator('#acc').inner_text() == 'Yes' and pg.locator('#chg').inner_text() == 'Correct it' and pg.locator('#ttl').inner_text() == 'Panel tile'
    assert 'choose Yes or Correct it' in pg.locator('#say').inner_text() and 'Are these facts right?' in pg.locator('#body').inner_text()
    pg.locator('#sub').click()
    assert pg.locator('#left').inner_text() == 'Answer these first: 1, 2, 3' and pg.evaluate('window.sent') == [], 'an entry left unanswered: nothing is sent, the card says which'
    pg.locator('#acc').click()
    pg.wait_for_function("document.getElementById('ttl').textContent === 'Shot G1-S1 (G1-S1)'")
    assert 'box length: 600 mm' in pg.locator('#body').inner_text()
    pg.locator('#chg').click()
    pg.locator('#save').click()
    assert pg.locator('#err').is_visible() and pg.locator('#err').inner_text() == 'Type what to correct first', 'Correct it needs the words'
    pg.locator('#note').fill('the box is 650 long')
    pg.locator('#save').click()
    pg.wait_for_function("document.getElementById('ttl').textContent === 'Shot G2-S1 (G2-S1)'")
    pg.locator('#acc').click()
    pg.locator('#sub').click()
    sent = pg.evaluate('window.sent')
    assert len(sent) == 1 and sent[0].startswith('Card answers (press Enter to send; do not edit or delete): ')
    doc = json.loads(sent[0].split(': ', 1)[1])
    assert doc == {'card': card['id'], 'answers': [{'n': 1, 'choice': 'accept'}, {'n': 2, 'choice': 'change', 'notes': 'the box is 650 long'}, {'n': 3, 'choice': 'accept'}]}
    got = C.card_answer(conn, store, H.USER, H.RUN, {}, doc['card'], [{'notes': '', **a} for a in doc['answers']])
    assert got['recorded'] == [1, 2, 3] and not errors


def test_in_a_browser_the_page_shows_a_spec_that_is_not_ready_as_with_the_assistant_with_the_reason(browser):
    from test_fixset5_browser_pure import live
    store, conn = film([drawing(), bad()])
    pg = live(browser, page(store, conn))
    blocks = pg.evaluate("[...document.querySelectorAll('#list .item')].map(b => ({tag: b.querySelector('.tag').textContent, text: b.querySelector('.body').innerText, buttons: b.querySelectorAll('button').length}))")
    assert blocks[1]['tag'] == 'With the assistant' and 'Not ready for your answer yet. The assistant completes it first: shot G2-S1: ' + UNKNOWN in blocks[1]['text']
    assert blocks[1]['buttons'] == 0 and blocks[0]['buttons'] >= 2 and not pg.errors
