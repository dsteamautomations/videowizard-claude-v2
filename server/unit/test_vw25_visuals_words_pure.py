"""VW-25 issues 7, 8 and 9 (SK, 25 Nov 2026): the visuals cards and the visuals page say what they are about in words.
R9: every gap line of the treatment shows the narration under the gap and its time in the film. R7: a shot is named in words (its title, else
its gap's title and its number in the gap), its code last in brackets, and a drawing's spec says where it sits in the film, the words under it
and what it shows. R8: the spec also shows the line accepted for it at the treatment. Every row is added when a line is shown: nothing is
stored, no id changes. Without a database: the harness of tests/check_shared_change.py."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
from app import chat_flow as C, page_flow as P, pictures as PIC, takes as T, visuals_stage as V   # noqa: E402
from test_design209_pure import by_key, chat, drawing, page, plan_with   # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PARTS = {p['name']: p['text'] for s in json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals' for p in s['parts']}
TAMIL = 'இது ஒரு சுவர்'
LONG = ' '.join(f'word{n}' for n in range(90))   # about 550 characters, as VW-25's longest gap


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(V, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 100.0})
    monkeypatch.setattr(V, 'not_this', lambda *a, **k: {})


# ---------- R9: the words of every gap line ----------

def timed(a, b, words):
    """A gap as the server stores it: its frames and the narration's words under it."""
    return {'start_frame': a, 'end_frame': b, 'timing': {'sentences': [], 'words': [{'text': w, 'start_frame': a, 'end_frame': a + 1} for w in words.split()], 'before': None, 'after': None}}


def entry(gid, **more):
    return {'gap_id': gid, 'picture': 'two tiles', 'routes': ['still'], 'seconds': 4.5, 'images': 1, **more}


def treatment(entries, gaps, accepted=(), direction='accepted'):
    """A store whose treatment draft has these gap lines; `gaps` is the server's own record of each gap ({} for a film with no timing)."""
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    s = H.session(store)
    s['source']['gaps'] = gaps
    draft = {'direction': 'One calm film.', 'gaps': entries, 'totals': {}, 'estimate_inr': 0}
    draft['lines'] = {k: {'state': direction if k == 'direction' else 'accepted' if k in accepted else 'to_accept', 'digest': d} for k, d in V._line_digests(draft).items()}
    s['treatment_draft'] = draft
    s.pop('treatment', None)
    V.save_session(store, H.RUN, s)
    return store, conn


def lines(store, conn):
    return {i['_key']: i for i in C._treatment_items(C._ctx(conn, store, H.USER, H.RUN, {}))[0]}


def test_a_gap_line_begins_with_the_words_under_the_gap_and_its_time_in_the_film():
    store, conn = treatment([entry('G1', depicts=['two tiles side by side'])], {'G1': timed(6300, 6412, 'Fillers replace the tension zone.')})   # 25 frames a second: 4:12.0 to 4:16.5
    i = lines(store, conn)['G1']
    assert i['_card']['r'][:3] == [['The words', 'Fillers replace the tension zone.'], ['In the film', '4:12.0 to 4:16.5 (4.5 s)'], ['The picture', 'two tiles']]
    assert i['text'].splitlines()[:2] == ['- **The words:** Fillers replace the tension zone.', '- **In the film:** 4:12.0 to 4:16.5 (4.5 s)']
    assert C._public(i, '', 1)['message'].index('The words') < C._public(i, '', 1)['message'].index('The picture')   # the one-at-a-time question reads the same text


def test_the_direction_line_has_no_words_row():
    store, conn = treatment([entry('G1')], {'G1': timed(0, 100, 'some words')}, direction='to_accept')
    d = lines(store, conn)['direction']
    assert 'The words' not in d['text'] and 'In the film' not in d['text'] and 'The words' not in json.dumps(d['_card'])


def test_a_gap_with_no_narration_says_none():
    store, conn = treatment([entry('G1', words='the assistant wrote these')], {'G1': timed(0, 50, '')})
    assert lines(store, conn)['G1']['_card']['r'][:2] == [['The words', 'none (no narration under this gap)'], ['In the film', '0:00.0 to 0:02.0 (2.0 s)']]


def test_without_the_servers_timing_the_assistants_words_are_shown_and_without_both_it_says_not_available():
    store, conn = treatment([entry('G1', words='the  assistant wrote\nthese'), entry('G2')], {'G1': {'start_frame': 0, 'end_frame': 50}})   # no options package: no timing; G2 is not in the record at all
    got = lines(store, conn)
    assert got['G1']['_card']['r'][:2] == [['The words', 'the assistant wrote these'], ['In the film', '0:00.0 to 0:02.0 (2.0 s)']]
    assert got['G2']['_card']['r'][:2] == [['The words', 'not available'], ['The picture', 'two tiles']]   # no frames known: no time row, and never an error


def test_the_servers_words_win_over_the_assistants_shortened_ones_and_a_long_gap_is_shown_whole():
    store, conn = treatment([entry('G1', words='word0 word1 …')], {'G1': timed(0, 1000, LONG)})
    i = lines(store, conn)['G1']
    assert i['_card']['r'][0] == ['The words', LONG] and LONG in i['text'] and len(LONG) > 540


def test_marks_in_the_narration_are_plain_text_in_the_chat_and_on_the_card_and_another_script_is_shown_as_written():
    store, conn = treatment([entry('G1'), entry('G2')], {'G1': timed(0, 50, 'the *best* tile_pair | ever'), 'G2': timed(50, 100, TAMIL)})
    got = lines(store, conn)
    assert got['G1']['_card']['r'][0] == ['The words', 'the *best* tile_pair | ever']
    assert got['G1']['text'].splitlines()[0] == '- **The words:** the \\*best\\* tile\\_pair \\| ever'
    assert got['G2']['_card']['r'][0] == ['The words', TAMIL] and TAMIL in got['G2']['text']


def test_a_gap_split_into_shots_has_one_words_row():
    shots = [{'route': 'still', 'seconds': 2, 'picture': 'p', 'fits_why': 'f', 'way_why': 'w'}] * 2
    store, conn = treatment([entry('G1', shots=shots)], {'G1': timed(0, 100, 'one two three')})
    assert [r[0] for r in lines(store, conn)['G1']['_card']['r']].count('The words') == 1


def test_the_rows_are_not_stored_the_lines_id_and_digest_stay_and_the_current_words_are_always_shown():
    e = entry('G1')
    bare, conn = treatment([e], {})
    store, conn = treatment([e], {'G1': timed(0, 100, 'first words')})
    before = lines(store, conn)['G1']
    assert before['id'] == lines(bare, conn)['G1']['id'] == f"treatment:G1:{V._line_digests({'gaps': [e]})['G1'][:10]}"
    s = H.session(store)
    assert 'first words' not in json.dumps(s['treatment_draft'])
    s['source']['gaps']['G1'] = timed(10, 110, 'later words')   # the gap's timing changed after the draft
    V.save_session(store, H.RUN, s)
    after = lines(store, conn)['G1']
    assert after['id'] == before['id'] and after['_card']['r'][:2] == [['The words', 'later words'], ['In the film', '0:00.4 to 0:04.4 (4.0 s)']]


def test_the_page_shows_the_rows_on_an_open_gap_line_on_an_accepted_one_and_when_the_treatment_is_recorded():
    gaps = {'G1': timed(0, 100, 'first words'), 'G2': timed(100, 150, '')}
    store, conn = treatment([entry('G1'), entry('G2')], gaps, accepted=('G1',))
    p = by_key(page(store, conn))
    assert p['G1']['state'] == 'recorded' and p['G1']['rows'] == [['The words', 'first words'], ['In the film', '0:00.0 to 0:04.0 (4.0 s)']]
    assert p['G2']['state'] == 'open' and p['G2']['rows'][:2] == [['The words', 'none (no narration under this gap)'], ['In the film', '0:04.0 to 0:06.0 (2.0 s)']]
    assert 'rows' not in p['direction']
    s = H.session(store)   # every line accepted: the treatment is recorded and its lines stay readable
    s['treatment'] = {'direction': 'One calm film.', 'gaps': s.pop('treatment_draft')['gaps']}
    V.save_session(store, H.RUN, s)
    done = by_key(page(store, conn))
    assert done['G1']['state'] == 'recorded' and done['G1']['rows'] == p['G1']['rows'] and done['G2']['rows'] == p['G2']['rows'][:2] and 'rows' not in done['direction']


def test_the_treatment_instruction_asks_for_the_reason_and_no_longer_for_the_words():
    t = PARTS['treatment']
    assert '`gap_id`; `picture` in one line' in t and '`gap_id`; the words under it' not in t   # D7: the server shows the words
    assert 'never the words themselves' in t and 'the operator asked' in t   # `fits_why` is the reason


# ---------- R7: a shot is named in words ----------

def untitled(plan, *gids):
    for gap in plan['gaps']:
        if gap['gap_id'] in gids:
            for sc in gap['scenes']:
                for sh in sc['shots']:
                    sh['title'] = ''
    return plan


def two_shots(plan, gid='G1'):
    gap = next(g for g in plan['gaps'] if g['gap_id'] == gid)
    first = gap['scenes'][0]['shots'][0]
    first['end_frame'] = 50
    gap['scenes'][0]['shots'].append({**H.shot(f'{gid}-S2'), 'start_frame': 50, 'end_frame': 100})
    return plan


def accepted(plan):
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    H.propose(store, plan)
    V.accept(store, H.USER, H.RUN, {}, [g['gap_id'] for g in plan['gaps']], 'yes')
    return store, conn


def ctx_of(store, conn):
    return C._ctx(conn, store, H.USER, H.RUN, {})


def test_the_name_rule_the_title_else_the_gaps_title_and_the_number_in_the_gap():
    gap = {'gap_id': 'BEAT_03-B1', 'title': 'Fillers replace the tension zone'}
    assert V.name_of(gap, {'id': 'S1', 'title': 'The two tiles'}, 2, 3) == 'The two tiles'
    assert V.name_of(gap, {'id': 'S1'}, 2, 3) == 'Fillers replace the tension zone, shot 2'
    assert V.name_of(gap, {'id': 'S1', 'title': ''}, 1, 1) == 'Fillers replace the tension zone'   # a gap with one shot: no ", shot 1"
    assert V.name_of({'gap_id': 'BEAT_03-B1'}, {'id': 'S1'}, 2, 2) == 'Gap BEAT_03-B1, shot 2'   # a gap with no title
    assert T.name_of is V.name_of   # one rule, the takes' own


def test_every_accepted_shot_has_its_name_and_the_code_follows_in_brackets():
    plan = untitled(two_shots(H.plan_of(2)), 'G1')
    plan['gaps'][1]['scenes'][0]['shots'][0]['title'] = 'Same title'
    store, conn = accepted(plan)
    ctx = ctx_of(store, conn)
    names = V.shot_names(ctx['plan'], ctx['session'])
    assert names == {'G1-S1': 'Title 1, shot 1', 'G1-S2': 'Title 1, shot 2', 'G2-S1': 'Same title'}
    assert V.coded(names, 'G1-S2') == 'Title 1, shot 2 (G1-S2)' and V.coded(names, 'G2-S1') == 'Same title (G2-S1)'   # two shots with one title: the code tells them apart
    assert V.coded(names, 'not-a-shot') == 'not-a-shot'


def test_in_a_gap_offered_two_ways_the_number_counts_inside_the_chosen_way():
    plan = H.plan_of(1, choices_on='G1')
    a, b = plan['gaps'][0]['choices']
    a['scenes'] = [{'ambient': 'quiet', 'shots': [{**H.shot('A1'), 'title': ''}]}]
    b['scenes'] = [{'ambient': 'quiet', 'shots': [{**H.shot('B1'), 'title': '', 'end_frame': 50}, {**H.shot('B2'), 'title': '', 'start_frame': 50}]}]
    gap = plan['gaps'][0]
    assert V.way_names(gap, a['scenes']) == {'A1': 'Title 1'} and V.way_names(gap, b['scenes']) == {'B1': 'Title 1, shot 1', 'B2': 'Title 1, shot 2'}
    session = {'source': {'fps': 25}, 'choice_selections': {}}
    assert [r[1] for r in C._gap_rows(session, gap, {'choice_id': 'b'})[0]] == ['Title 1, shot 1 (B1)', 'Title 1, shot 2 (B2)'] and [r[1] for r in C._gap_rows(session, gap, {'choice_id': 'a'})[0]] == ['Title 1 (A1)']


def test_a_plan_line_and_its_warnings_name_the_shot_in_words(monkeypatch):
    plan = untitled(two_shots(H.plan_of(1)), 'G1')
    gap = plan['gaps'][0]
    session = {'source': {'fps': 25}, 'choice_selections': {}}
    assert [r[1] for r in C._gap_rows(session, gap)[0]] == ['Title 1, shot 1 (G1-S1)', 'Title 1, shot 2 (G1-S2)']
    monkeypatch.setattr(V, 'plain_warnings', lambda *a, **k: [{'shot_id': 'G1-S2', 'plain': 'It is short.'}, {'plain': 'The gap is long.'}])
    assert V.warning_lines(session, gap, plan) == ['Title 1, shot 2 (G1-S2): It is short.', 'The gap is long.']


def spec_film(specs, treatment=None, change=None):
    plan = plan_with(specs)
    if change:
        change(plan)
    store, conn = accepted(plan)
    if treatment is not None:
        s = H.session(store)
        s['treatment'] = treatment
        V.save_session(store, H.RUN, s)
    return store, conn


def view_of(store, conn, key):
    return next(v for v in C._spec_views(ctx_of(store, conn)) if v['key'] == key)


def test_a_drawings_spec_says_where_it_sits_the_words_under_it_and_what_it_shows():
    def change(plan):
        two_shots(untitled(plan, 'G1'))
        plan['gaps'][0]['scenes'][0]['shots'][1].update(drawing_spec=drawing(), depicts='two tiles side by side', narration='Fillers replace the tension zone.', title='')
    store, conn = spec_film([None, drawing()], change=change)
    v = view_of(store, conn, 'G1-S2')
    assert v['title'] == 'Title 1, shot 2 (G1-S2)' and v['name'] == 'Title 1, shot 2'
    assert v['rows'] == [['', 'In the film at 0:02.0 to 0:04.0 (2.0 s) · Gap G1, Title 1'], ['The words under it', 'Fillers replace the tension zone.'], ['Shows', 'two tiles side by side']]
    assert v['item'] == f"spec:G1-S2:{V.spec_digest(drawing())[:10]}"   # the id is the spec's own: the rows are not part of it
    item = next(i for i in chat(store, conn) if i['id'] == v['item'])
    assert item['question'] == 'Title 1, shot 2 (G1-S2): are the parts right?'
    assert item['text'].splitlines()[:3] == ['- In the film at 0:02.0 to 0:04.0 (2.0 s) · Gap G1, Title 1', '- The words under it: Fillers replace the tension zone.', '- Shows: two tiles side by side']   # a list: plain lines run together in the chat
    assert 'Drawn as: a cutaway' in item['text']
    out = C._public(item, '', 1)
    assert out['ask'] == 'Title 1, shot 2: are the parts right?' and '### Title 1, shot 2 (G1-S2)' in out['message']   # the button panel names the drawing
    other = view_of(store, conn, 'G2-S1')   # a titled shot with no `depicts`: its title, and no Shows row
    assert other['title'] == 'Shot G2-S1 (G2-S1)' and [r[0] for r in other['rows']] == ['', 'The words under it']


def test_a_shot_with_no_narration_says_none_and_another_script_is_shown_as_written():
    def change(plan):
        plan['gaps'][0]['scenes'][0]['shots'][0]['narration'] = ''
        plan['gaps'][1]['scenes'][0]['shots'][0]['narration'] = TAMIL
    store, conn = spec_film([drawing(), drawing()], change=change)
    assert view_of(store, conn, 'G1-S1')['rows'][1] == ['The words under it', 'none'] and view_of(store, conn, 'G2-S1')['rows'][1] == ['The words under it', TAMIL]


def test_a_title_with_marks_of_its_own_still_splits_into_the_name_and_the_question_and_a_long_name_is_cut_at_80():
    odd = 'What. Is it right? Yes: a look'

    def change(plan):
        plan['gaps'][0]['scenes'][0]['shots'][0]['title'] = odd
        plan['gaps'][1]['scenes'][0]['shots'][0]['title'] = 'x' * 150
    store, conn = spec_film([drawing(), drawing()], change=change)
    first, second = [C._public(i, '', 2) for i in chat(store, conn)]
    assert first['ask'] == odd + ': are the parts right?' and f'### {odd} (G1-S1)' in first['message']
    assert second['ask'] == 'x' * 80 + ': are the parts right?' and f"### {'x' * 150} (G2-S1)" in second['message']
    assert C._split('Gap G1 (changed). Do you accept this line?') == ('Gap G1 (changed)', 'Do you accept this line?')   # every other question splits as before
    assert C._split(f'{odd} (S1): the layout failed its check 3 times in a row. What should happen to it?', f'{odd} (S1)') == (f'{odd} (S1): the layout failed its check 3 times in a row',
                                                                                                                          'What should happen to it?')


def test_a_materials_spec_belongs_to_no_shot_and_is_unchanged():
    from test_design209_pure import PANEL
    plan = plan_with([drawing()], PANEL)
    store, conn = accepted(plan)
    m = view_of(store, conn, 'element:panel')
    assert m['title'] == 'Floor panel' and m['rows'] == []
    item = next(i for i in chat(store, conn) if i['id'] == m['item'])
    assert item['question'] == 'Floor panel: are these facts right?' and C._public(item, '', 1)['ask'] == 'Are these facts right?' and 'In the film' not in item['text']


def test_the_pages_open_spec_line_carries_the_rows_and_the_name():
    store, conn = spec_film([drawing(depicts_note=None)], change=lambda plan: plan['gaps'][0]['scenes'][0]['shots'][0].update(depicts='the box and its lid'))
    line = page(store, conn)['lines'][0]
    assert line['title'] == 'Shot G1-S1 (G1-S1)' and line['state'] == 'open'
    assert line['rows'] == [['', 'In the film at 0:00.0 to 0:04.0 (4.0 s) · Gap G1, Title 1'], ['The words under it', 'words'], ['Shows', 'the box and its lid']]


def test_a_row_that_cannot_be_worked_out_is_left_out_and_the_card_still_asks(monkeypatch):
    store, conn = spec_film([drawing()])
    monkeypatch.setattr(PIC, 'where', lambda *a, **k: (_ for _ in ()).throw(KeyError('start_frame')))
    v = view_of(store, conn, 'G1-S1')
    assert v['rows'] == [] and v['state'] == 'open' and [i['id'] for i in chat(store, conn)] == [v['item']]


def test_step_6_names_a_drawing_by_the_same_rule():
    store, conn = accepted(untitled(two_shots(H.plan_of(1)), 'G1'))
    ctx = ctx_of(store, conn)
    w = PIC.where(ctx['session'], ctx['plan'], 'G1-S2')
    assert w['name'] == 'Title 1, shot 2 (G1-S2)' and w['where'] == 'In the film at 0:02.0 to 0:04.0 (2.0 s) · Gap G1, Title 1'
    assert PIC.where(ctx['session'], ctx['plan'], 'gone')['name'] == 'gone'


def test_the_card_of_the_drawing_at_the_end_of_the_shot_has_the_name_and_the_two_rows():
    from step6_shape import SHAPE, answers, chat as cards, load, upload
    from test_design221_p3c_pure import still_verdict
    from test_fixset1_pure import SECTION
    store, sid = load(), 'D1'
    sha = upload(store, sid, *SECTION, still=True)['sha256']
    still_verdict(store, sha, answers(SHAPE['rounds']['D1']['still']), shot=sid, key=f'run-1/visuals/motion/tools/{sid}/0.png')
    card = next(i for i in cards(store, 'still end-frame') if sid in i['question'])
    out = C._public(card, '', 1)
    assert f'({sid})' in card['question'] and not card['question'].startswith(sid + ':')   # the name in words, the code last
    assert out['ask'].startswith('Is it right?') and '### ' in out['message'] and f'({sid}): this is the drawing as it stands at the end of the shot' in out['message']
    assert card['text'].splitlines()[0].startswith('- In the film at ') and card['text'].splitlines()[1].startswith('- The words under it: ') and len(card['text'].splitlines()) == 2


# ---------- R8: what was accepted for the drawing ----------

def test_the_spec_shows_the_line_accepted_at_the_treatment_for_one_drawing_for_several_and_leaves_it_out_when_there_is_none():
    one = {'gaps': [{'gap_id': 'G1', 'picture': 'p', 'depicts': ['two tiles side by side, joined by a filler']}, {'gap_id': 'G2', 'picture': 'p'}]}
    store, conn = spec_film([drawing(), drawing()], treatment=one)
    assert view_of(store, conn, 'G1-S1')['rows'][-1] == ['What you accepted for this drawing', 'two tiles side by side, joined by a filler']
    assert 'What you accepted' not in json.dumps(view_of(store, conn, 'G2-S1')['rows'])   # the gap's treatment line names no graphic
    item = next(i for i in chat(store, conn) if i['id'].startswith('spec:G1-S1:'))
    assert '- What you accepted for this drawing: two tiles side by side, joined by a filler' in item['text'].split('Drawn as')[0]
    several = {'gaps': [{'gap_id': 'G1', 'depicts': ['the tile pair', 'the filler between them']}]}
    store, conn = spec_film([drawing()], treatment=several)
    assert view_of(store, conn, 'G1-S1')['rows'][-1] == ["What you accepted for this gap's graphics", 'the tile pair; the filler between them']
    for none in ({'gaps': []}, {}, None):   # no line for the gap, an older record, no recorded treatment
        store, conn = spec_film([drawing()], treatment=none)
        assert 'What you accepted' not in json.dumps(view_of(store, conn, 'G1-S1')['rows'])


def test_one_accepted_line_for_a_gap_with_two_drawings_is_said_of_the_gaps_graphics():
    def change(plan):
        two_shots(plan)
        plan['gaps'][0]['scenes'][0]['shots'][1]['drawing_spec'] = drawing()
    store, conn = spec_film([drawing()], treatment={'gaps': [{'gap_id': 'G1', 'depicts': ['the tile pair']}]}, change=change)
    assert view_of(store, conn, 'G1-S1')['rows'][-1] == view_of(store, conn, 'G1-S2')['rows'][-1] == ["What you accepted for this gap's graphics", 'the tile pair']


def test_the_plan_instruction_says_to_name_the_parts_with_the_words_of_the_accepted_line():
    assert PARTS['plan'].count('name the parts with the words of the accepted `depicts` line') == 2   # once for each kind of film
