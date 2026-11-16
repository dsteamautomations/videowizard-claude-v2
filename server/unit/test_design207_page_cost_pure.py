"""design/207 package B1 (SK, 16 Nov 2026): the world of the film on the plan page, what was accepted at the treatment under each gap, the
plan's estimate against the limit, the Direction placed by the server, the check reporting what only the proposal refused, the carry-over
warnings, and the cost limit by the film's length. Without a database: the harness of tests/check_shared_change.py for the page, the fakes
of test_visuals_stage_pure for the check, the proposal and the limit."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
from app import chat_flow as C, page_flow as P, visuals_stage as VS   # noqa: E402
from app.errors import Problem   # noqa: E402
from test_visuals_stage_pure import RUN, USER, FakeConn, FakeStore, TREATMENT, g, plan_doc, saved, session, shot, store_with   # noqa: E402

PAID = {**H.RUN, 'image_provider': 'openai'}   # a film that names its picture AI, so an estimate can be worked out
STATES = [{'what_appears': 'a', 'hold_s': 7}, {'what_appears': 'b', 'hold_s': 7}, {'what_appears': 'c', 'hold_s': 6}]
NEW = 'Show the hollow inside the wall.'


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})


def rule(n, text):
    return {'id': f'r{n}', 'statement': text, 'scope': 'the film', 'source': 'the script'}


def world_plan(n=3):
    plan = H.plan_of(n)
    plan['foundation'] = {'treatment': 'The Direction, accepted at the treatment.', 'appearance': 'Warm daylight,  plain and close.',
                          'world': [rule(1, 'A small town in the hills, today.'), rule(2, 'People wear everyday clothes.')], 'exclusions': [rule(3, 'No aerial views.')],
                          'specifications': [rule(4, 'Every label is in English.')],
                          'graphic_style': {'palette': 'two blues', 'line_weight': 'thin', 'labels': 'sentence case', 'background': 'white', 'frame_fill': 'none'}}
    plan['elements'] = [{'id': 'wall', 'name': 'The wall', 'kind': 'object', 'requirements': 'a wall', 'description': 'a garden wall, waist high',
                         'size': [{'part': 'wall', 'measure': 'height', 'value': 0.9, 'unit': 'm', 'status': 'confirmed'}, {'part': 'wall', 'measure': 'length', 'value': None, 'status': 'unknown'}]},
                        {'id': 'asha', 'name': 'Asha', 'kind': 'person', 'requirements': 'the owner, about forty', 'description': ''},
                        {'id': 'chart', 'name': 'Cost chart', 'kind': 'graphic', 'requirements': 'a bar chart'},
                        {'id': 'tile', 'name': 'Floor tile', 'kind': 'material', 'requirements': 'square tiles', 'description': 'grey floor tiles',
                         'material_spec': {'dimensions': [{'part': 'tile', 'measure': 'side', 'value': 300, 'unit': 'mm', 'status': 'confirmed'}]}}]
    return plan


def start(plan=None, treatment=None):
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    if treatment:
        s = H.session(store)
        s['treatment'] = treatment
        VS.save_session(store, H.RUN, s)
    H.propose(store, plan or H.plan_of())
    return store, conn


def page(store, conn, run=H.RUN):
    return P.page(conn, store, H.USER, run, {})


# ---------- 1. the world of the film ----------

def test_the_world_rows_say_the_look_the_rules_the_graphic_style_and_each_thing_but_never_the_direction_or_a_graphic():
    rows = C._world_rows(world_plan())
    assert rows == [['The look', 'Warm daylight, plain and close.'], ['The world', 'A small town in the hills, today.'], ['The world', 'People wear everyday clothes.'],
                    ['Not shown', 'No aerial views.'], ['Specification', 'Every label is in English.'],
                    ['The graphic style', 'palette: two blues; line weight: thin; labels: sentence case; background: white; frame fill: none'],
                    ['Object · The wall', 'a garden wall, waist high. Known sizes: wall height 0.9 m'], ['Person · Asha', 'the owner, about forty'],
                    ['Material · Floor tile', 'grey floor tiles. Known sizes: tile side 300 mm']]
    assert not [r for r in rows if 'Direction' in r[1] or 'chart' in r[0].lower()]


def test_a_plan_with_an_empty_foundation_has_no_world_rows_and_no_world_block():
    assert C._world_rows({'foundation': {}, 'elements': [], 'gaps': []}) == [] and C._world_rows({'gaps': []}) == []
    assert C._world_rows(H.plan_of()) == []   # only the Direction and things: nothing of the world is written
    store, conn = start()
    assert [l['key'] for l in page(store, conn)['lines']] == ['G1', 'G2', 'G3']


def test_the_world_is_the_first_line_of_the_plan_page_read_only_and_not_counted():
    store, conn = start(world_plan())
    p = page(store, conn)
    w = p['lines'][0]
    assert [l['key'] for l in p['lines']] == ['world', 'G1', 'G2', 'G3'] and w['line'] == 'l01' and p['lines'][1]['line'] == 'l02'
    assert w['title'] == 'The world of this film' and w['state'] == 'recorded' and w['rows'] == C._world_rows(world_plan())
    assert not {'buttons', 'reopen', 'item'} & set(w)
    assert p['summary'].startswith('3 gaps: 3 to answer, 0 recorded, 0 with the assistant') and p['open'] is True


def test_an_answer_sent_to_the_world_line_is_named_stale_and_changes_nothing():
    store, conn = start(world_plan())
    before = json.dumps(H.session(store), sort_keys=True)
    for choice in ('accept', 'change', 'reopen'):
        r = P.page_record(conn, store, H.USER, H.RUN, {}, [{'line': 'l01', 'key': 'world', 'item': '', 'choice': choice, 'notes': 'make it night'}])
        assert r['stale'] == ['world'] and r['recorded'] == [] and r['refused'] == []
    after = H.session(store)
    assert after['accepted'] == {} and not after.get('revisions') and json.loads(before)['versions'] == after['versions']


def test_a_very_large_world_is_shortened_and_no_gap_is_held_back():
    plan = world_plan()
    plan['foundation'].update(world=[rule(n, f'{n} ' + 'w' * 3990) for n in range(100)], exclusions=[rule(n, 'x' * 3990) for n in range(100, 200)],
                              specifications=[rule(n, 's' * 3990) for n in range(200, 300)])
    plan['elements'] = [{'id': f'e{n}', 'name': f'Thing {n}', 'kind': 'object', 'requirements': 'r', 'description': 'd' * 3000} for n in range(300)] + [plan['elements'][0]]
    store, conn = start(plan)
    p = page(store, conn)
    assert len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) <= P.ROUND_BYTES
    assert [l['key'] for l in p['lines']] == ['world', 'G1', 'G2', 'G3'] and 'more after these' not in p['summary']
    rows = p['lines'][0]['rows']
    assert len(rows) == 603 and all(len(r[1]) <= 400 for r in rows) and rows[1][1].endswith('…')


# ---------- 2. what was accepted at the treatment, under each gap ----------

def test_a_gap_shows_the_shots_and_reasons_accepted_at_the_treatment_and_a_gap_without_an_entry_shows_nothing_extra():
    entry = {'gap_id': 'G1', 'picture': 'the wall from the street', 'routes': ['still', 'video'],
             'shots': [{'route': 'still', 'seconds': 4, 'picture': 'the wall, whole', 'fits_why': 'the words name the wall', 'way_why': 'nothing moves'},
                       {'route': 'video', 'seconds': 6, 'picture': 'a hand on the wall', 'fits_why': 'the words say touch'}]}
    store, conn = start(treatment={'gaps': [entry], 'reasons_missing': []})
    p = page(store, conn)
    g1, g2 = p['lines'][0], p['lines'][1]
    assert g1['text'] == 'What you accepted in the treatment: the wall from the street'
    assert g1['rows'] == [[k, str(v)] for k, v in C._shot_rows(entry)] and ['Shot 1 · why this way', 'nothing moves'] in g1['rows'] and ['Shot 2 · why this way', 'not given'] in g1['rows']
    assert g1['table'] and 'rows' not in g2 and 'text' not in g2


# ---------- 3. the plan's estimate against the limit ----------

def test_the_plan_page_summary_says_the_estimate_against_the_films_limit():
    store, conn = start()
    s = H.session(store)
    s['cap_inr'] = 1500
    VS.save_session(store, H.RUN, s)
    p = page(store, conn, PAID)
    assert p['summary'] == '3 gaps: 3 to answer, 0 recorded, 0 with the assistant; estimate ₹60 of the ₹1500 limit.'   # three stills at ₹20
    assert VS.plan_estimate(PAID, VS.routes(H.plan_of(), 25)) == 60.0
    assert 'estimate' not in page(store, conn)['summary']   # a film with no picture AI named: no figure is guessed


# ---------- 4. the Direction placed by the server ----------

def doc_of():
    return plan_doc([shot('AN1', 0, 500, 'animation', states=STATES)], [shot('VS1', 900, 1150, 'video')])


def with_treatment(direction=NEW, **over):
    store = store_with(session(**over))
    VS.treatment(store, USER, RUN, [], {**TREATMENT, **({'direction': direction} if direction else {})}, 'yes')
    return store


def stored(store, version=1):
    return json.loads(store.files[f'run-1/visuals/plan-v{version}.json'])['document']


def test_check_and_propose_place_the_direction_at_the_head_and_agree_on_the_digest():
    store, doc = with_treatment(), doc_of()
    c = VS.check(store, RUN, [], doc)
    assert c['status'] == 'valid'
    out = VS.propose(FakeConn(), store, USER, RUN, [], doc)
    assert out['plan_digest'] == c['plan_digest']
    assert stored(store)['foundation']['treatment'] == NEW + '\n\ntechnical record with scenes of work'
    assert doc['foundation']['treatment'] == 'technical record with scenes of work'   # the sender's document is not changed in place
    again = VS.check(store, RUN, [], stored(store))
    assert again['plan_digest'] == c['plan_digest']   # placed once: the stored plan is left as it is


def test_a_direction_already_at_the_head_is_left_alone_and_a_missing_text_becomes_the_direction():
    store, doc = with_treatment(), doc_of()
    doc['foundation']['treatment'] = 'Show the hollow  inside the wall.\nThen the rest of the brief.'   # spacing is not a difference
    out = VS.propose(FakeConn(), store, USER, RUN, [], doc)
    assert stored(store)['foundation']['treatment'] == 'Show the hollow  inside the wall.\nThen the rest of the brief.'
    assert VS.check(store, RUN, [], doc)['plan_digest'] == out['plan_digest']
    bare = doc_of()
    del bare['foundation']['treatment']
    assert VS.check(store, RUN, [], bare)['status'] == 'valid'
    VS.propose(FakeConn(), store, USER, RUN, [], bare)
    assert stored(store, 2)['foundation']['treatment'] == NEW


def test_a_direction_changed_in_the_treatment_after_a_plan_is_placed_anew():
    store, doc = with_treatment(), doc_of()
    VS.propose(FakeConn(), store, USER, RUN, [], doc)
    VS.treatment(store, USER, RUN, [], {**TREATMENT, 'direction': 'Follow one family through a day.'}, 'yes, the new one')
    VS.propose(FakeConn(), store, USER, RUN, [], stored(store))
    assert stored(store, 2)['foundation']['treatment'] == 'Follow one family through a day.\n\n' + NEW + '\n\ntechnical record with scenes of work'


def test_no_recorded_direction_places_nothing():
    old = {'gaps': TREATMENT['gaps'], 'quote': 'yes', 'by': 'u1', 'at': 't', 'digest': 'x', 'totals': {}, 'estimate_inr': 0}   # a treatment from before the Direction
    store, doc = store_with(session(treatment=old)), doc_of()
    VS.propose(FakeConn(), store, USER, RUN, [], doc)
    assert stored(store)['foundation']['treatment'] == 'technical record with scenes of work'
    assert VS.check(store_with(session()), RUN, [], doc)['status'] == 'valid'   # no treatment at all: the check still reads the plan


def test_a_plan_text_too_long_once_the_direction_is_placed_is_refused_plainly_on_both_paths():
    store, doc = with_treatment(), doc_of()
    doc['foundation']['treatment'] = 'x' * 15990
    c = VS.check(store, RUN, [], doc)
    assert c['status'] == 'rejected' and '16,000' in c['error'] and 'Direction' in c['error'] and c['errors'] == [c['error']]
    with pytest.raises(Problem, match='16,000'):
        g(lambda: VS.propose(FakeConn(), store, USER, RUN, [], doc))


# ---------- 5. the check reports a way the treatment did not name ----------

def test_the_check_reports_a_way_the_treatment_did_not_name_and_the_proposal_still_refuses_it():
    store = with_treatment(TREATMENT['direction'])
    departed = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])   # G1 planned as a still, the treatment said a sequence
    c = VS.check(store, RUN, [], departed)
    fault = "gap G1: the plan uses ['still'] but the treatment says ['graphic_sequence']; record a new treatment with the reason, or change the plan."
    assert c['status'] == 'rejected' and c['errors'] == [fault] and c['error'] == fault
    with pytest.raises(Problem, match='gap G1: the plan uses'):
        g(lambda: VS.propose(FakeConn(), store, USER, RUN, [], departed))
    assert VS.check(store, RUN, [], doc_of())['status'] == 'valid'


# ---------- 6. the carry-over warnings ----------

def small_plan(g1, elements=()):
    return {'foundation': {}, 'elements': list(elements),
            'gaps': [{'gap_id': 'G1', 'scenes': [{'id': 'SC1', 'shots': g1}]},
                     {'gap_id': 'G2', 'scenes': [{'id': 'SC2', 'shots': [{'id': 'V1', 'visual_type': 'video', 'start_frame': 900, 'end_frame': 1150, 'element_ids': []}]}]}]}


def still(sid='IM1', a=0, b=500, **extra):
    return {'id': sid, 'visual_type': 'image', 'start_frame': a, 'end_frame': b, 'element_ids': [], **extra}


def carried(plan, run=RUN, outputs=(), **over):
    return VS.carried_warnings(session(**over), run, plan, list(outputs))


def kinds(ws):
    return [w['kind'] for w in ws]


AGREED = {'gaps': [{'gap_id': 'G1', 'routes': ['still', 'video'], 'seconds': 20, 'shots': [{'route': 'still', 'seconds': 4}, {'route': 'video', 'seconds': 16}]},
                   {'gap_id': 'G2', 'routes': ['video'], 'seconds': 10}]}
FILM = {'film': {'category': {'value': 'advertisement-product'}}}   # a category that takes cards of words


def test_a_gap_with_more_still_seconds_than_accepted_at_the_treatment_warns_once_for_the_gap():
    ws = carried(small_plan([still()]), run={**RUN, **FILM}, treatment=AGREED)   # 20 s of stills planned, 4 s accepted
    assert ws == [{'kind': 'still_more_than_agreed', 'gap_id': 'G1', 'answered': False,
                   'message': 'gap G1: the plan has 20 s of still pictures; 4 s were accepted in the treatment. Make some of them moving shots, or record the treatment again.'}]
    assert not carried(small_plan([still(b=110)]), run={**RUN, **FILM}, treatment=AGREED)   # 4.4 s: within half a second
    assert kinds(carried(small_plan([still(b=115)]), run={**RUN, **FILM}, treatment=AGREED)) == ['still_more_than_agreed']
    assert not carried(small_plan([still()]), run={**RUN, **FILM}, treatment={'gaps': []})   # a gap with no treatment entry: nothing to compare
    assert not carried(small_plan([still()]), run={**RUN, **FILM})   # no treatment recorded
    unsplit = {'gaps': [{'gap_id': 'G1', 'routes': ['still', 'video'], 'seconds': 20}]}   # several ways and no shots: the split was never told, so it is not guessed
    assert not carried(small_plan([still()]), run={**RUN, **FILM}, treatment=unsplit)


def test_stills_over_the_share_of_the_film_warn_at_the_plan_on_the_first_gap_with_a_still():
    film = [{'stage': 'first_cut', 'unit': None, 'summary': {'duration_frames': 2500}}]   # 100 s
    plan = small_plan([{'id': 'D1', 'visual_type': 'diagram', 'start_frame': 0, 'end_frame': 200, 'element_ids': []}, still(a=200, b=500)])   # 12 s of stills; the diagram is not one
    ws = carried(plan, run={**RUN, **FILM}, outputs=film)
    assert ws == [{'kind': 'stills_many', 'gap_id': 'G1', 'answered': False, 'message': 'Still pictures are 12 % of the film: above 10 %. Make some of them moving shots.'}]
    assert not carried(small_plan([still(b=250)]), run={**RUN, **FILM}, outputs=film)   # exactly a tenth
    assert not carried(plan, run={**RUN, **FILM})   # the film's length is not known: no share is worked out


def test_a_card_of_words_warns_in_a_documentary_or_explaining_film_only():
    card = {'id': 'T1', 'visual_type': 'diagram', 'graphic_kind': 'title', 'start_frame': 0, 'end_frame': 100, 'element_ids': []}
    plan = small_plan([card, {**card, 'id': 'T2', 'graphic_kind': 'text'}, {**card, 'id': 'D1', 'graphic_kind': 'chart'}])
    ws = carried(plan, run={**RUN, 'film': {'category': {'value': 'documentary-explainer'}}})
    assert [(w['kind'], w['shot_id']) for w in ws] == [('text_card', 'T1'), ('text_card', 'T2')]
    assert ws[0]['message'] == ('shot T1 is a card of words. In a documentary or an explaining film the words are said by the voice and the picture shows the thing: '
                                'plan a picture here, or say why the card is needed.')
    assert not carried(plan, run={**RUN, **FILM}) and not carried(plan, run={**RUN, 'film': {}})   # another category; a film with no category
    alt = {'foundation': {}, 'elements': [], 'gaps': [{'gap_id': 'G1', 'recommended_choice': 'a', 'choices': [{'id': 'a', 'scenes': [{'id': 'S1', 'shots': [still()]}]},
                                                                                                         {'id': 'b', 'scenes': [{'id': 'S2', 'shots': [card]}]}]}]}
    assert not carried(alt, run={**RUN, 'film': {'category': {'value': 'documentary-explainer'}}})   # only the shots the film counts


def test_a_real_speaker_shown_without_their_recorded_permission_gives_one_line_on_their_first_made_shot():
    people = [{'id': 'P1', 'name': 'Asha Rao', 'kind': 'person', 'speaker': True}, {'id': 'P2', 'name': 'A passer-by', 'kind': 'person'}]
    plan = small_plan([{'id': 'F1', 'visual_type': 'footage', 'start_frame': 0, 'end_frame': 50, 'element_ids': ['P1']}, still('IM1', 50, 60, element_ids=['P1', 'P2']),
                       still('IM2', 60, 70, element_ids=['P1'])], people)
    ws = carried(plan, run={**RUN, **FILM})
    assert [(w['kind'], w['shot_id']) for w in ws] == [('stand_in_real', 'IM1')]   # her own footage is not a stand-in; one line, on the first made shot
    assert ws[0]['message'] == ('shot IM1 shows Asha Rao, a real person, as a stand-in: the picture is made from the description, not from their own photo. '
                                'To show them as they are, the operator gives a photo and records their permission.')
    assert not carried(plan, run={**RUN, **FILM}, likeness={'P1': {'quote': 'she said yes'}})


def test_the_carried_warnings_come_back_from_the_check_and_are_kept_with_the_proposal():
    store = store_with(session())
    VS.treatment(store, USER, RUN, [], {'direction': TREATMENT['direction'], 'gaps': [{'gap_id': 'G1', 'picture': 'the wall', 'routes': ['still', 'video'], 'seconds': 20, 'images': 1,
                                                                                   'shots': [{'route': 'still', 'seconds': 4, 'picture': 'a'}, {'route': 'video', 'seconds': 16, 'picture': 'b'}]},
                                                                                  TREATMENT['gaps'][1]]}, 'yes')
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    c = VS.check(store, RUN, [], doc)
    assert c['status'] == 'valid' and 'still_more_than_agreed' in kinds(c['warnings'])
    out = VS.propose(FakeConn(), store, USER, RUN, [], doc)
    assert 'still_more_than_agreed' in kinds(out['warnings']) and 'still_more_than_agreed' in kinds(saved(store)['versions'][0]['warnings'])


# ---------- 7. the cost limit by the film's length ----------

def test_the_limit_follows_the_films_length_with_a_lowest_figure():
    assert VS.cap_for(60) == 1500.0 and VS.cap_for(600) == 7500.0 and VS.cap_for(None) == 1500.0 and VS.cap_for(0) == 1500.0
    assert VS.cap_for(181) == 2262.0   # ₹2,262.50, to the rupee
    assert VS.cap_of(session()) == 5000.0   # a film in progress, begun before the limit by length: the older figure


def prepared(monkeypatch, store, frames=None):
    src = session()['source']
    monkeypatch.setattr(VS, 'gaps_source', lambda store, outputs: src)
    monkeypatch.setattr(VS.core, 'stage_table', lambda v: [{'name': 'visuals', 'prompt': '', 'steps': []}])
    monkeypatch.setattr(VS.core, 'effective_rules', lambda conn, run, outputs: [])
    outputs = [{'stage': 'first_cut', 'unit': None, 'files': [], 'summary': {'duration_frames': frames}}] if frames else []
    return VS.prepare(FakeConn([]), store, USER, {**RUN, 'procedure_version': '3'}, outputs)


@pytest.mark.parametrize('frames, cap', [(1500, 1500.0), (15000, 7500.0), (None, 1500.0), (4500, 2250.0)])   # one minute, ten minutes, no length, three minutes (at 25 a second)
def test_prepare_gives_a_new_film_its_limit_by_length(monkeypatch, frames, cap):
    store = FakeStore({})
    out = prepared(monkeypatch, store, frames)
    s = saved(store)
    assert s['cap_inr'] == cap and s['cap_from'] == 'length' and out['cap_inr'] == cap and VS.cap_of(s) == cap


def test_prepare_never_lowers_a_running_films_limit_and_never_touches_the_owners_figure(monkeypatch):
    store = store_with(session())   # a film in progress: its session exists and holds no limit
    out = prepared(monkeypatch, store, 1500)
    assert 'cap_inr' not in saved(store) and out['cap_inr'] == 5000.0
    store = store_with(session(cap_inr=900.0, cap_from='owner', cap_quote='keep this one under nine hundred'))
    prepared(monkeypatch, store, 15000)
    assert saved(store)['cap_inr'] == 900.0 and saved(store)['cap_from'] == 'owner'
    store = FakeStore({})
    prepared(monkeypatch, store, None)       # prepared before the length was known: the lowest figure
    prepared(monkeypatch, store, 15000)      # the length is known now: the limit follows it up
    assert saved(store)['cap_inr'] == 7500.0
    prepared(monkeypatch, store, 1500)       # a shorter cut later never lowers it
    assert saved(store)['cap_inr'] == 7500.0


def test_only_the_owner_sets_another_limit_with_their_words_and_it_is_logged():
    store, conn, admin = store_with(session(cap_inr=1500.0, cap_from='length')), H.Conn(), {**USER, 'role': 'Admin'}
    with pytest.raises(Problem) as exc:
        g(lambda: VS.set_cap(conn, store, {**USER, 'role': 'Member'}, RUN, [], 3000, 'raise it'))
    assert exc.value.status == 403 and exc.value.message == 'Only the owner can set the cost limit of a film.'
    for inr, quote, said in ((3000, '  ', "The owner's words are needed"), (0, 'free', 'above zero'), (-5, 'less', 'above zero'), ('many', 'more', 'above zero'), (True, 'yes', 'above zero')):
        with pytest.raises(Problem, match=said):
            g(lambda: VS.set_cap(conn, store, admin, RUN, [], inr, quote))
    assert saved(store)['cap_inr'] == 1500.0 and conn.log == []
    out = VS.set_cap(conn, store, admin, RUN, [], 3000, 'This one may cost up to three thousand.')
    s = saved(store)
    assert s['cap_inr'] == 3000.0 and s['cap_from'] == 'owner' and s['cap_by'] == 'u1' and s['cap_at'] and s['cap_quote'] == 'This one may cost up to three thousand.'
    assert out['cap_inr'] == 3000.0 and out['was_inr'] == 1500.0 and VS.cap_of(s) == 3000.0
    assert len(conn.log) == 1 and 'This one may cost up to three thousand.' in conn.log[0] and any('₹1,500' in str(x) and '₹3,000' in str(x) for x in conn.log[0])


def test_the_refusal_at_the_limit_says_how_the_limit_is_set():
    with pytest.raises(Problem) as exc:
        VS.check_cap(FakeConn([]), RUN, session(cap_inr=10.0), 40.0, 'a 5 s take')
    assert exc.value.message == ("₹0 spent of ₹10 on this film's visuals; a 5 s take needs about ₹40. Stop and tell the operator the spend. "
                                 "The limit follows the film's length; the owner can set another figure for this film with `vw visuals cap`.")


def test_the_settings_and_the_route():
    from app import main
    from app.config import Settings
    s = Settings()
    assert s.VISUALS_CAP_INR_PER_MIN == 750.0 and s.VISUALS_CAP_FLOOR_INR == 1500.0 and s.VISUALS_CAP_INR == 5000.0
    assert any(getattr(r, 'path', '') == '/api/runs/{run_id}/visuals/cap' and 'POST' in r.methods for r in main.app.routes)
