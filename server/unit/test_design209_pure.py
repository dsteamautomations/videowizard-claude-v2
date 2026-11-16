"""design/209 (SK, 16 Nov 2026): the drawings' parts and sizes and the materials' facts approved on the Claude artifact page, in one visit, in
plain words, each size asked once. One function (`chat_flow._spec_parts`) writes a spec as plain parts for the page and for the chat; the page's
lines are the chat's own items, and the answers go through their own run functions. And the plan's estimate also says what the reference sets
may cost. Without a database: the harness of tests/check_shared_change.py."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
from app import chat_flow as C, page_flow as P, visuals_stage as V   # noqa: E402

TRIED = 'The script states no size; the footage shows no ruler (S_DIAGRAM_ILLUSTRATIVE)'
SOURCE = "the maker's sheet, page 2"
FIELDS = ('dimensions', 'illustrative', 'view_reason', 'relationships', 'not_this', 'status', 'tried', 'True', 'False', 'part:', 'measure:', 'source:')


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(V, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 100.0})
    monkeypatch.setattr(V, 'not_this', lambda *a, **k: {})   # the list of wrong forms is a model call: not made here


def dim(part, measure, value=None, unit='mm', source=SOURCE):
    return {'part': part, 'measure': measure, 'value': value, 'unit': unit if value is not None else '', 'source': source if value is not None else '',
            'status': 'confirmed' if value is not None else 'unknown', 'tried': '' if value is not None else TRIED}


def drawing(dims=(), **more):
    unknown = any(d['value'] is None for d in dims)
    return {'parts': ['box', 'lid'], 'dimensions': list(dims), 'relationships': ['the lid sits on the box'], 'label': 'Illustrative, not to scale' if unknown else '',
            'proportions': ['the box is about 3 : 2 : 1'], 'illustrative': unknown, 'view': 'cutaway', 'view_reason': 'it shows what is inside', **more}


def material(dims):
    return {'parts': ['panel'], 'dimensions': list(dims), 'relationships': [], 'label': '', 'proportions': ['a panel is about 2 : 1'], 'illustrative': False, 'view': '', 'view_reason': '',
            'laid': 'flat, the long side to the viewer', 'joint': '3 mm gaps', 'pattern': 'each row starts half a panel along', 'not_this': []}


PANEL = [dim('panel', 'length', 410), dim('panel', 'width', 235)]


def plan_with(specs, panel=None, n=None):
    """A plan whose gap N's one shot carries specs[N-1] as its drawing spec (None for no spec), and a material element when `panel` is given."""
    plan = H.plan_of(n or len(specs))
    for gap, spec in zip(plan['gaps'], specs):
        if spec is not None:
            gap['scenes'][0]['shots'][0]['drawing_spec'] = spec
    if panel is not None:
        plan['elements'].append({'id': 'panel', 'name': 'Floor panel', 'kind': 'material', 'description': 'a floor panel', 'material_spec': material(panel)})
    return plan


def start(plan, run=H.RUN):
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    H.propose(store, plan)
    V.accept(store, H.USER, run, {}, [g['gap_id'] for g in plan['gaps']], 'yes')
    return store, conn


def page(store, conn, run=H.RUN):
    return P.page(conn, store, H.USER, run, {})


def record(store, conn, answers):
    return P.page_record(conn, store, H.USER, H.RUN, {}, answers)


def ans(line, choice, notes=''):
    return {'line': line['line'], 'key': line['key'], 'item': line.get('item', ''), 'choice': choice, 'notes': notes}


def by_key(p):
    return {l['key']: l for l in p['lines']}


def chat(store, conn):
    return [i for i in C._waiting_items(C._ctx(conn, store, H.USER, H.RUN, {})) if i['kind'] == 'spec']


# ---------- 1. one function, plain parts ----------

def test_a_drawing_spec_is_written_as_plain_parts_and_the_working_notes_are_not_shown():
    got = C._spec_parts(drawing([dim('box', 'length', 600), dim('box', 'wall thickness')]))
    assert got['drawn_as'] == 'a cutaway (it shows what is inside)' and got['words'] == 'Not to scale. It carries the words "Illustrative, not to scale".'
    assert got['parts'] == ['box', 'lid'] and got['sits'] == ['the lid sits on the box'] and got['proportions'] == ['the box is about 3 : 2 : 1']
    assert got['sizes'] == [['box', 'length', '600 mm', SOURCE]] and got['unknown'] == 'box wall thickness' and got['known'] == 1
    text = json.dumps(got, ensure_ascii=False) + C._spec_text(got)
    assert 'S_DIAGRAM' not in text and 'script states' not in text and not [f for f in FIELDS if f in text], text
    assert {'plan': 'seen from above', 'side': 'from the side', 'elevation': 'from the front'} == {v: C._spec_parts(drawing(view=v, view_reason=''))['drawn_as'] for v in ('plan', 'side', 'elevation')}


def test_a_material_spec_gives_its_unit_sizes_how_it_is_laid_its_pattern_and_its_proportions():
    got = C._spec_parts(material(PANEL))
    assert got['sizes'] == [['panel', 'length', '410 mm', SOURCE], ['panel', 'width', '235 mm', SOURCE]]
    assert got['facts'] == [['How it is laid', 'flat, the long side to the viewer'], ['Joints', '3 mm gaps'], ['Pattern', 'each row starts half a panel along']]
    assert got['proportions'] == ['a panel is about 2 : 1'] and 'drawn_as' not in got and 'unknown' not in got


def test_a_long_source_is_one_short_line_and_a_value_is_printed_as_the_assistant_wrote_it():
    got = C._spec_parts(drawing([dim('box', 'length', 0.6, 'm', 'clip A012_C003.mov at 00:01:12, read against the door frame.\nSecond line ' + 'x' * 300)]))
    row = got['sizes'][0]
    assert row[2] == '0.6 m' and row[3].startswith('clip A012_C003.mov at 00:01:12') and len(row[3]) <= 100 and '\n' not in row[3] and row[3].endswith('…')


def test_a_record_of_an_unknown_shape_is_listed_plainly_and_never_raises():
    odd = {'parts': 'not a list', 'dimensions': [5, 'x', {'part': 'box'}], 'odd': {'deep': ['a plain value', 7, True, None]}}
    got = C._spec_parts(odd)
    assert 'a plain value' in got['other'] and '7' in got['other'] and 'not a list' in got['other'] and 'box' in got['other']
    assert 'odd' not in json.dumps(got) and 'deep' not in json.dumps(got) and 'True' not in json.dumps(got)
    for strange in (None, 'just words', 7, [], {'dimensions': None}, {'dimensions': [{'part': 'a', 'measure': 'b', 'value': 'wide'}]}):
        assert isinstance(C._spec_parts(strange), dict) and isinstance(C._spec_text(C._spec_parts(strange)), str)
    assert C._spec_parts('just words')['other'] == ['just words']


# ---------- 2. the page's step ----------

def test_with_no_spec_waiting_the_page_stays_on_the_plan_step_as_before():
    store, conn = start(plan_with([None, None, None]))
    p = page(store, conn)
    assert p['step'] == 'Plan' and p['open'] is False and 'accepted' in p['note']
    store, conn = H.Store(), H.Conn()   # the plan is not complete: its gaps are asked first, whatever specs it holds
    H.fresh(store)
    H.propose(store, plan_with([drawing(), None], PANEL))
    assert page(store, conn)['step'] == 'Plan'


def test_the_step_lists_the_materials_first_then_the_drawings_in_the_films_order_each_with_the_chats_own_item():
    store, conn = start(plan_with([drawing([dim('box', 'length', 600)]), None, drawing([dim('lid', 'thickness')])], PANEL))
    p = page(store, conn)
    assert p['step'] == 'Drawings and materials' and p['open'] is True
    assert [(l['line'], l['key'], l['title'], l['state']) for l in p['lines']] == [('l01', 'element:panel', 'Floor panel', 'open'), ('l02', 'G1-S1', 'Shot G1-S1', 'open'), ('l03', 'G3-S1', 'Shot G3-S1', 'open')]
    assert [l['item'] for l in p['lines']] == [i['id'] for i in chat(store, conn)] and all(l['item'].startswith('spec:' + l['key'] + ':') for l in p['lines'])
    assert [l['ask'] for l in p['lines']] == ['Are these facts right?', 'Are the parts and the known sizes right?', 'Are the parts right?']
    assert all([(b['label'], b['choice'], b['needs_words']) for b in l['buttons']] == [('Yes', 'yes', False), ('Correct it', 'correct', True)] for l in p['lines'])
    assert p['summary'] == '1 material and 2 drawings: 3 to answer, 0 recorded, 0 with the assistant.' and p['note'] == 'Answer each line, then say done in the chat.'
    text = json.dumps(p['lines'], ensure_ascii=False)
    assert 'S_DIAGRAM' not in text and not [f for f in FIELDS if f in text]
    assert p['how'] == P.HOW and p['capabilities'] == P.CAPABILITIES


def test_a_drawing_with_no_sizes_and_one_whose_sizes_are_all_unknown():
    store, conn = start(plan_with([drawing(), drawing([dim('box', 'length'), dim('lid', 'thickness')])]))
    a, b = page(store, conn)['lines']
    assert 'sizes' not in a['spec'] and 'unknown' not in a['spec'] and a['ask'] == 'Are the parts right?' and a['spec']['parts'] == ['box', 'lid']
    assert 'sizes' not in b['spec'] and b['spec']['unknown'] == 'box length, lid thickness' and b['ask'] == 'Are the parts right?'


# ---------- 3. each fact asked once ----------

def test_a_materials_unit_size_is_asked_once_at_the_material_and_three_drawings_that_repeat_it_say_already_confirmed():
    repeat = lambda *more: drawing(PANEL + list(more))
    store, conn = start(plan_with([repeat(), repeat(dim('box', 'length', 600)), repeat()], PANEL))
    m, d1, d2, d3 = page(store, conn)['lines']
    assert len(m['spec']['sizes']) == 2 and 'confirmed' not in m['spec']
    assert d1['spec']['confirmed'] == d3['spec']['confirmed'] == 'panel: length 410 mm, width 235 mm' and 'sizes' not in d1['spec'] and 'sizes' not in d3['spec']
    assert d2['spec']['sizes'] == [['box', 'length', '600 mm', SOURCE]] and d2['spec']['confirmed'] == 'panel: length 410 mm, width 235 mm'
    assert d1['ask'] == 'Are the parts and the known sizes right?'
    assert sum(json.dumps(l['spec']).count('410 mm') for l in (m, d1, d2, d3)) == 4   # in full once, then one short line in each drawing


def test_the_same_part_and_measure_with_another_value_is_shown_in_full_in_both_and_each_says_it_differs():
    store, conn = start(plan_with([drawing([dim('box', 'length', 600)]), drawing([dim('Box', 'Length', 650)])]))
    a, b = page(store, conn)['lines']
    assert a['spec']['sizes'] == [['box', 'length', '600 mm', SOURCE]] and b['spec']['sizes'] == [['Box', 'Length', '650 mm', SOURCE]]
    assert a['spec']['differs'] == ['box length: differs from Shot G2-S1: 650 mm'] and b['spec']['differs'] == ['Box Length: differs from Shot G1-S1: 600 mm']
    assert 'confirmed' not in a['spec'] and 'confirmed' not in b['spec']


def test_a_size_approved_in_an_earlier_round_and_repeated_in_another_drawing_is_already_confirmed_on_the_page_and_in_the_chat():
    store, conn = start(plan_with([drawing([dim('lid', 'length', 300)]), drawing([dim('lid', 'length', 300), dim('lid', 'width', 200)])]))
    r = record(store, conn, [ans(page(store, conn)['lines'][1], 'yes')])   # the later drawing approved alone
    a, b = r['page']['lines']
    assert r['recorded'] == ['G2-S1'] and a['state'] == 'open' and a['spec']['confirmed'] == 'lid: length 300 mm' and 'sizes' not in a['spec']
    assert b['state'] == 'recorded' and len(b['spec']['sizes']) == 2, 'what was approved is read back in full'
    item, = chat(store, conn)   # the chat, one at a time, in the same words
    assert item['question'] == 'Shot G1-S1: are the parts and the known sizes right?' and C._split(item['question']) == ('Shot G1-S1', 'Are the parts and the known sizes right?')
    assert 'Already confirmed: lid: length 300 mm' in item['text'] and 'Sizes to confirm' not in item['text'] and 'Drawn as: a cutaway (it shows what is inside)' in item['text']
    assert 'Parts: box, lid' in item['text'] and not [f for f in FIELDS if f in item['text']]


def test_the_chat_question_of_a_material_and_of_a_drawing_with_unknown_sizes_reads_plainly():
    store, conn = start(plan_with([drawing([dim('box', 'length', 600), dim('box', 'wall thickness')])], PANEL))
    m, d = chat(store, conn)
    assert m['question'] == 'Floor panel: are these facts right?' and '- panel length: 410 mm (from ' + SOURCE + ')' in m['text'] and 'How it is laid: flat, the long side to the viewer' in m['text']
    assert d['question'] == 'Shot G1-S1: are the parts and the known sizes right?' and 'Not known, so no figure is shown: box wall thickness' in d['text']
    assert 'S_DIAGRAM' not in d['text'] and 'Not to scale. It carries the words "Illustrative, not to scale".' in d['text']


# ---------- 4. the answers ----------

def test_one_done_records_every_answer_through_the_specs_own_functions_and_the_page_follows():
    store, conn = start(plan_with([drawing([dim('box', 'length', 600)]), drawing()], PANEL))
    m, a, b = page(store, conn)['lines']
    r = record(store, conn, [ans(a, 'yes'), ans(m, 'yes'), ans(b, 'correct', 'the lid  is hinged, not loose')])
    assert sorted(r['recorded']) == ['G1-S1', 'G2-S1', 'element:panel'] and r['stale'] == [] and r['refused'] == [] and r['open'] == 0
    s = H.session(store)
    assert set(s['spec_approvals']) == {'element:panel', 'G1-S1'} and s['spec_corrections']['G2-S1']['words'] == 'the lid is hinged, not loose'
    now = by_key(r['page'])
    assert now['element:panel']['state'] == 'recorded' and now['element:panel']['spec']['facts'][0][0] == 'How it is laid' and 'buttons' not in now['element:panel']
    assert now['G2-S1']['state'] == 'with_assistant' and now['G2-S1']['note'] == 'the lid is hinged, not loose'
    assert r['page']['summary'] == '1 material and 2 drawings: 0 to answer, 2 recorded, 1 with the assistant.'
    assert r['then'] == P.SPEC_BACK and 'vw visuals page' in r['then'] and 'propose' in r['then']
    assert len(conn.log) == 3 and [x for x in conn.log if 'the lid is hinged, not loose' in json.dumps(x, default=str)], 'one log line per answer, with the operator\'s words'


def test_every_spec_approved_keeps_its_content_on_its_recorded_line_and_names_what_is_next():
    store, conn = start(plan_with([drawing([dim('box', 'length', 600)])], PANEL))
    r = record(store, conn, [ans(l, 'yes') for l in page(store, conn)['lines']])
    assert r['open'] == 0 and r['page']['open'] is False and r['page']['step'] == 'Drawings and materials' and r['then'] == P.SPEC_NEXT and 'vw visuals next' in r['then']
    assert all(l['state'] == 'recorded' and l['spec']['sizes'] for l in r['page']['lines']) and 'approved' in r['page']['note']
    assert chat(store, conn) == []


def test_a_correction_without_words_is_refused_on_its_line_and_the_other_answers_are_recorded():
    store, conn = start(plan_with([drawing(), drawing()]))
    a, b = page(store, conn)['lines']
    r = record(store, conn, [ans(a, 'correct', '  '), ans(b, 'yes'), {'key': 'G1-S1', 'item': a['item'], 'choice': 'maybe'}])
    assert r['recorded'] == ['G2-S1'] and [x['key'] for x in r['refused']] == ['G1-S1', 'G1-S1']
    now = by_key(r['page'])
    assert now['G1-S1']['state'] == 'open' and 'Not an answer to this line' in now['G1-S1']['refused'] and now['G2-S1']['state'] == 'recorded'
    assert '1 line(s) still wait' in r['then']
    r = record(store, conn, [ans(now['G1-S1'], 'correct', '')])
    assert 'your own words' in by_key(r['page'])['G1-S1']['refused']


def test_an_answer_to_a_spec_that_changed_since_or_is_no_longer_open_is_stale():
    store, conn = start(plan_with([drawing([dim('box', 'length', 600)]), drawing()]))
    a, b = page(store, conn)['lines']
    assert record(store, conn, [ans(b, 'yes'), ans(b, 'yes')])['stale'] == ['G2-S1'], 'answered twice: the second is stale'
    s = H.session(store)
    plan = V.current_plan(store, s)
    plan['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec']['dimensions'][0]['value'] = 640   # the assistant changed the spec; the gap is accepted again
    H.propose(store, plan)
    V.accept(store, H.USER, H.RUN, {}, ['G1'], 'yes')
    r = record(store, conn, [ans(a, 'yes')])
    assert r['stale'] == ['G1-S1'] and r['recorded'] == [] and 'G1-S1' not in H.session(store)['spec_approvals']
    assert by_key(r['page'])['G1-S1']['spec']['sizes'][0][2] == '640 mm' and by_key(r['page'])['G1-S1']['item'] != a['item']


def test_done_with_nothing_answered_records_nothing_and_says_so():
    store, conn = start(plan_with([drawing(), drawing()]))
    r = record(store, conn, [])
    assert r['recorded'] == [] and r['open'] == 2 and r['then'].startswith('Nothing was answered on the page.') and '2 line(s) still wait' in r['then'] and r['log'] == 'nothing answered'


def test_a_spec_back_with_the_assistant_is_shown_with_the_operators_words_and_is_not_counted_as_confirmed():
    store, conn = start(plan_with([drawing([dim('lid', 'length', 300)]), drawing([dim('lid', 'length', 300)])]))
    V.correct_spec(store, H.USER, H.RUN, {}, 'G1-S1', 'the lid is 320 long')
    a, b = page(store, conn)['lines']
    assert a == {'line': 'l01', 'key': 'G1-S1', 'title': 'Shot G1-S1', 'state': 'with_assistant', 'note': 'the lid is 320 long'}
    assert b['state'] == 'open' and b['spec']['sizes'] == [['lid', 'length', '300 mm', SOURCE]] and 'confirmed' not in b['spec']


def test_forty_drawings_are_held_under_the_size_of_one_round():
    big = lambda n: drawing([dim(f'part {n}-{i}', 'length ' + 'x' * 150, 100 + i, source='s' * 900) for i in range(60)], relationships=['r' * 400] * 30)
    store, conn = start(plan_with([big(n) for n in range(40)]))
    p = page(store, conn)
    shown = len(p['lines'])
    assert 1 < shown < 40 and [l['key'] for l in p['lines']] == [f'G{n}-S1' for n in range(1, shown + 1)], 'the first drawings, in the film\'s order'
    assert len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) <= P.ROUND_BYTES and len(json.dumps(p, ensure_ascii=False).encode('utf-8')) < 256 * 1024
    assert f'{40 - shown} more after these' in p['summary'] and f'{40 - shown} more appear here after you answer these' in p['note']
    r = record(store, conn, [ans(l, 'yes') for l in p['lines']])
    assert len(r['recorded']) == shown and r['open'] > 0 and 'still wait' in r['then']
    assert len(json.dumps(r['page']['lines'], ensure_ascii=False).encode('utf-8')) <= P.ROUND_BYTES, 'the recorded lines give up their content before a line to answer is lost'


def test_the_treatment_and_the_plan_pages_are_as_before():
    import inspect
    src = inspect.getsource(P._page)   # design/210: `page` is `_page` with the pictures its lines name
    assert '_plan_page(' in src and 'CF._treatment_items(ctx)' in src and '_spec_page(' in src
    assert copy.deepcopy(P.CAPABILITIES) == {'db': {'rules': [{'path': p, 'read': 'view', 'write': 'owner'} for p in ('rounds', 'pics', 'zoom')]}, 'assets': {}, 'user': {}}   # design/210: the pictures of a line, and the page's file store
    assert not hasattr(C, '_spec_text') or 'for k, v in (spec or {}).items()' not in inspect.getsource(C._spec_text), 'the field-by-field listing is gone'


# ---------- 5. the reference sets in the estimate ----------

PAID = {**H.RUN, 'image_provider': 'openai'}


def kept_film(plan):
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    s = H.session(store)
    s.update(cap_inr=1500, refs='kept')
    V.save_session(store, H.RUN, s)
    H.propose(store, plan)
    return store, conn


def test_the_plan_page_says_what_the_reference_sets_may_cost_beside_the_shots():
    plan = plan_with([None, None, None], PANEL)
    plan['elements'] += [{'id': 'chart', 'name': 'A chart', 'kind': 'graphic'}, {'id': 'dog', 'name': 'A dog', 'kind': 'animal'}, {'id': V.STYLE, 'name': 'style', 'kind': 'style'}]
    store, conn = kept_film(plan)
    one = round(V.image_price_inr(PAID, provider='gemini') * V.SET_MAX, 2)
    assert V.set_estimate(PAID, H.session(store), plan) == {'sets': 2, 'inr': round(2 * one, 2)}   # the wall and the panel; a graphic, an animal and the style get none
    assert page(store, conn, PAID)['summary'] == f'3 gaps: 3 to answer, 0 recorded, 0 with the assistant; estimate ₹60 for the shots, and up to ₹{2 * one:g} for 2 reference sets, of the ₹1500 limit.'
    assert V.plan_estimate(PAID, V.routes(plan, 25)) == 60.0, 'the figure of the shots means what it meant'
    s = H.session(store)
    s['round'] = {'kept': True, 'pass': 2, 'elements': {'wall': {'from_footage': True}, 'panel': {}}}   # the wall keeps its footage picture: no set is made for it
    V.save_session(store, H.RUN, s)
    assert V.set_estimate(PAID, s, plan) == {'sets': 1, 'inr': one} and f'and up to ₹{one:g} for 1 reference set, of' in page(store, conn, PAID)['summary']


def test_an_older_film_and_a_film_with_no_picture_ai_keep_the_summary_they_had():
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    H.propose(store, H.plan_of())
    assert V.set_estimate(PAID, H.session(store), H.plan_of()) == {'sets': 0, 'inr': 0.0}
    assert 'estimate ₹60 of the ₹' in page(store, conn, PAID)['summary'] and 'estimate' not in page(store, conn)['summary']


def test_the_check_returns_the_reference_sets_with_the_plans_estimate():
    import inspect
    src = inspect.getsource(V.check)
    assert 'set_estimate(run, session, plan)' in src and "'sets'" in src and "'sets_inr'" in src and "'planned_inr': planned" in src


# ---------- 6. the assistant's instructions and the tool's lines ----------

def test_the_instructions_send_the_drawings_and_materials_to_the_page_and_the_chat_is_the_way_back():
    root = Path(__file__).resolve().parents[2]
    d = json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    part = {p['name']: p['text'] for p in st['parts']}
    assert 'then the drawings and the materials, on the page (`vw visuals page`)' in st['prompt']
    assert 'after the plan is accepted they approve the drawings and the materials on the page' in part['plan'] and 'only where the page cannot be shown' in part['plan']
    assert 'approved once, on the page with the drawings' in part['later']
    assert "they approve the run's specs in one table" not in part['plan'] and 'shown on the References step beside the sheet' not in part['later']
    retired = json.loads((root / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert "they approve the run's specs in one table" in retired and 'it is shown on the References step beside the sheet and approved once' in retired
    sys.path.insert(0, str(root / 'scripts'))
    import d209_wording_v3 as W
    parts = copy.deepcopy(st['parts'])
    assert W.apply(st['prompt'], parts) == st['prompt'] and parts == st['parts'], 'applying twice changes nothing'
    src = Path(V.__file__).read_text(encoding='utf-8')   # the tool's own lines point to the page first
    assert 'approves the specs as one table' not in src and 'approves the drawings and the materials on the page (`vw visuals page`)' in src


def test_a_yes_that_relied_on_a_size_corrected_in_the_same_visit_is_not_recorded():
    """The critic's check: the drawing showed the panel's length only as "Already confirmed", the operator corrected that length on the material
    and said yes on the drawing in the same visit. The yes is not recorded: the drawing is asked again once the material is right."""
    store, conn = start(plan_with([drawing(PANEL), drawing([dim('box', 'length', 600)])], PANEL))
    m, relies, own = page(store, conn)['lines']
    assert relies['spec'].get('confirmed') and 'confirmed' not in own['spec']
    r = record(store, conn, [ans(relies, 'yes'), ans(own, 'yes'), ans(m, 'correct', 'the panel is 400 long, not 410')])   # sent in any order: the correction is recorded first
    assert r['recorded'] == ['element:panel', 'G2-S1'] and r['stale'] == ['G1-S1']
    assert 'G1-S1' not in (V.session_of(store, H.RUN, {}).get('spec_approvals') or {})
    now = by_key(r['page'])
    assert now['element:panel']['state'] == 'with_assistant' and now['G1-S1']['state'] == 'open' and now['G2-S1']['state'] == 'recorded'
    store, conn = start(plan_with([drawing(PANEL)], PANEL))   # with no correction in the visit, the yes is recorded as before
    m, relies = page(store, conn)['lines']
    assert sorted(record(store, conn, [ans(relies, 'yes'), ans(m, 'yes')])['recorded']) == ['G1-S1', 'element:panel']


def test_a_yes_the_server_refuses_tells_the_assistant_to_fix_the_drawing_not_to_send_the_link_again():
    """The critic's check: an unknown size with nothing tried is refused at approval. The operator cannot act on that; the assistant is told to."""
    spec = drawing([dim('box', 'wall thickness')])
    spec['dimensions'][0]['tried'] = ''
    store, conn = start(plan_with([spec]))
    r = record(store, conn, [ans(page(store, conn)['lines'][0], 'yes')])
    assert [x['key'] for x in r['refused']] == ['G1-S1'] and r['recorded'] == []
    assert r['then'].startswith(P.SPEC_REFUSED) and 'yours to fix' in P.SPEC_REFUSED and 'propose again' in P.SPEC_REFUSED
