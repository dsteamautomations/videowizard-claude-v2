"""design/207, the fixes after its review (16 Nov 2026). A person's picture reaches the picture service only with the recorded permission, on every
path (a guide's still, a look, a picture handed in, the pictures an end image inherits); the permission can be recorded, a photo given or the
person made a stand-in after the reference round is complete; a storage hiccup never rewrites a film's cost limit; the operator's plain lines
are on the plan page; "not to scale" is taken with every size known; people who read alike are named together at the check; smaller faults."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
from app import chat_flow as CF, guide as GD, guide_spec as GS, page_flow as PF, visual_contract as VC, visuals_stage as VS   # noqa: E402
from app.errors import Problem   # noqa: E402
from test_batch89b_pure import SPEC   # noqa: E402
from test_design111_f19_pure import base as drawing   # noqa: E402
from test_design151_refs_pure import HELPER, KILN, MASON, NEW, OLD, _req, doc_with, frames_only, new_store, with_sets   # noqa: E402
from test_design207_checker_pure import check, element, framing_doc, kinds, pic, refused as plan_refused, scenes_of, with_person   # noqa: E402
from test_design207_page_cost_pure import AGREED, FILM, carried, prepared, small_plan, still   # noqa: E402
from test_design207_pictures_pure import WORDS, refused, yes   # noqa: E402
from test_ui_visuals_actions_pure import own, sheets, view   # noqa: E402
from test_visuals_pure import plan   # noqa: E402
from test_visuals_stage_pure import RUN, USER, FakeConn, FakeStore, accepted, g, ref, saved, session, store_with   # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})


@pytest.fixture
def long_shots(monkeypatch):   # the borrowed drawing plans hold long video shots and test other rules
    real = VC._default_generator
    monkeypatch.setattr(VC, '_default_generator', lambda: {**real(), 'max_seconds': 60})


# ---------- 1. a person's picture and the permission, on every path ----------

FRAME = {**ref('F2', 'approved'), 'kind': 'frame', 'element_id': 'P1'}
MINE = {**ref('M1', 'approved'), 'kind': 'supplied', 'element_id': 'P1'}
WEB = {**ref('W1', 'approved'), 'kind': 'web', 'element_id': 'P1'}
PEOPLE = {'P1': 'Mason'}


def test_one_function_says_why_a_persons_picture_is_not_sent():
    for row, word in ((FRAME, 'a footage frame'), (MINE, "the operator's own picture")):
        said = VS.person_picture_refused({}, PEOPLE, row)
        assert word in said and 'permission' in said and 'vw visuals likeness --element P1' in said
        assert VS.person_picture_refused({'likeness': {'P1': {'quote': WORDS}}}, PEOPLE, row) is None   # with the recorded permission it goes
    for s in ({}, {'likeness': {'P1': {'quote': WORDS}}}):
        assert 'a picture of a person from the web is never sent to the picture AI' in VS.person_picture_refused(s, PEOPLE, WEB)   # never, permission or not
    assert VS.person_picture_refused({}, PEOPLE, {**FRAME, 'element_id': 'E1'}) is None   # a thing's frame
    assert VS.person_picture_refused({}, PEOPLE, {'id': 'S1', 'status': 'approved'}) is None and VS.person_picture_refused({}, PEOPLE, None) is None


def guide_store(refs, **over):
    import test_guide_route_pure as GR
    doc = doc_with(KILN, MASON)
    store, conn = new_store(doc, refs, accepted=accepted(doc), **over), GR.Conn()
    GR.rendered(store, conn)
    for rid in refs:
        store.files[f'run-1/visuals/references/{rid}.png'] = b'png'
    return store, conn, GR.STILL_WORDS


@pytest.mark.parametrize('row, word', [(FRAME, 'a footage frame'), (MINE, "the operator's own picture"), (WEB, 'a web picture')])
def test_a_guides_still_takes_no_picture_of_a_person_without_the_permission(row, word):
    row = {**row, 'key': f"run-1/visuals/references/{row['id']}.png"}
    store, conn, words = guide_store({row['id']: row})
    n = len(conn.queued)
    said = refused(lambda: GD.request_still(conn, store, USER, NEW, [], 'VS1', words, [{'id': row['id'], 'job': 'the mason: copy his face'}]))
    assert word in said and said == VS.person_picture_refused({}, PEOPLE, row) and len(conn.queued) == n
    said = refused(lambda: GD.request_still(conn, store, USER, NEW, [], 'VS1', words, [], look=row['id']))   # the look reference is the same door
    assert said == VS.person_picture_refused({}, PEOPLE, row) and len(conn.queued) == n


def test_a_guides_still_takes_the_persons_frame_once_the_permission_is_recorded():
    row = {**FRAME, 'key': 'run-1/visuals/references/F2.png'}
    store, conn, words = guide_store({'F2': row}, likeness={'P1': {'quote': WORDS}})
    n = len(conn.queued)
    GD.request_still(conn, store, USER, NEW, [], 'VS1', words, [{'id': 'F2', 'job': 'the mason: copy his face'}])
    assert len(conn.queued) == n + 1


def test_a_picture_handed_in_for_a_person_needs_the_permission_too():
    doc = doc_with(KILN, MASON)
    store = new_store(doc)
    body = {'request_id': 'q1', 'element_id': 'P1', 'name': 'mason', 'kind': 'supplied', 'subject': 'the mason'}
    said = refused(lambda: VS.add_reference(FakeConn([]), store, USER, NEW, [], body, b'x'))
    assert said == VS.own_picture_refused('person', {}, 'P1') and not saved(store)['references']


def test_an_end_image_does_not_inherit_a_persons_frame_from_its_start_without_the_permission():
    doc = doc_with(KILN, MASON)
    doc['gaps'][1]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'P1']
    start = {**ref('K1', 'approved'), 'kind': 'keyframe', 'element_id': 'E1', 'shot_id': 'VS1', 'role': 'start', 'generation': {'parents': [{'id': 'F2'}], 'prompt': 'p'}}
    store = new_store(doc, {'F2': FRAME, 'K1': start}, accepted=accepted(doc))
    body = {'request_id': 'q1', 'element_id': 'E1', 'name': 'end', 'kind': 'keyframe', 'subject': 'the plinth', 'shot_id': 'VS1', 'parents': ['K1'], 'region': {'left': 0.1, 'top': 0.1, 'width': 0.3, 'height': 0.3},
            'prompt': 'Image 1 is the start image: change only the top course, now one brick higher.'}
    said = refused(lambda: VS.generate_image(FakeConn([]), store, USER, OLD, [], body))
    assert said == VS.person_picture_refused({}, PEOPLE, FRAME)


# ---------- 2. the permission, a photo or a stand-in after the round is complete ----------

def complete_round(photo=False):
    """A kept round, complete: P1's set approved (made from the photo when asked), E2's too."""
    store, conn, s = with_sets(doc_with(KILN, MASON))
    if photo:
        yes(store, conn)
        own(store, conn, 'P1')
        VS.set_make(conn, store, USER, NEW, [], 'P1')
        s = saved(store)
        for r in s['references'].values():
            if r.get('kind') == 'sheet' and r['status'] == 'generating':
                r.update(status='candidate', sha256='sha-' + r['id'], key='k')
        VS.save_session(store, NEW, s)
    s = saved(store)
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sheets(s, 'E2')[0]}, 'P1': {'verdict': 'yes'}}, 'yes', conn=conn)
    assert out['pass'] == 'complete'
    return store, conn


def test_after_the_round_is_complete_a_photo_with_the_permission_makes_the_sheet_again():
    store, conn = complete_round()
    said = refused(lambda: VS.set_make(conn, store, USER, NEW, [], 'P1'))
    assert 'not at the step where its sets are made' in said   # nothing changed: a complete round stays complete
    yes(store, conn)
    photo = own(store, conn, 'P1')
    assert 'vw visuals round --make P1' in photo['next']
    row = view(store, conn)['round']['elements']['P1']
    assert row['spec_changed'] is True and row['photo_changed'] is True   # the page says so on a complete round too
    assert 'not at the step' in refused(lambda: VS.set_make(conn, store, USER, NEW, [], 'E2'))   # only the person whose photo changed
    n0 = len(conn.inserted)
    out = VS.set_make(conn, store, USER, NEW, [], 'P1')
    assert out['queued'] is True and [p['id'] for p in _req(conn.inserted[n0])['parents']] == [photo['id']]
    s = saved(store)
    assert s['round']['pass'] == 'making' and 'P1' not in s['golden'] and not sheets(s, 'P1', 'approved')


def test_a_stand_in_takes_the_sheet_made_from_the_photo_out_of_use():
    store, conn = complete_round(photo=True)
    s = saved(store)
    assert sheets(s, 'P1', 'approved') and s['golden']['P1'] in sheets(s, 'P1', 'approved')
    out = yes(store, conn, quote='He would rather not be shown.', stand_in=True)
    s = saved(store)
    assert not sheets(s, 'P1', 'approved') and not sheets(s, 'P1') and 'P1' not in s['golden']   # the photo-made set is rejected, its golden picture gone
    assert s['round']['pass'] == 2 and 'vw visuals round --make P1' in out['next']               # the round is open again for this person
    assert sheets(s, 'E2', 'approved')                                                           # nobody else is touched
    n0 = len(conn.inserted)
    VS.set_make(conn, store, USER, NEW, [], 'P1')
    assert _req(conn.inserted[n0])['parents'] == [] and 'Image 1' not in _req(conn.inserted[n0])['prompt']   # made from the description


def test_a_set_made_from_the_photo_is_not_approved_once_the_permission_is_gone():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    yes(store, conn)
    own(store, conn, 'P1')
    VS.set_make(conn, store, USER, NEW, [], 'P1')       # being made from the photo
    yes(store, conn, quote='No longer.', stand_in=True)  # the permission goes while it is made
    s = saved(store)
    for r in s['references'].values():
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            r.update(status='candidate', sha256='sha-' + r['id'], key='k')
    VS.save_session(store, NEW, s)
    said = refused(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sheets(s, 'E2')[0]}, 'P1': {'verdict': 'yes'}}, 'yes', conn=conn))
    assert "P1: this set was made from the person's photo and the permission is no longer recorded" in said and 'vw visuals round --make P1' in said
    assert not sheets(saved(store), 'P1', 'approved')


def test_a_stand_in_for_a_person_with_no_permission_record_says_so_and_logs_nothing():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    out = yes(store, conn, quote='Make him a stand-in.', stand_in=True)
    assert out == {'element_id': 'P1', 'likeness': False, 'next': 'P1 is already a stand-in: no permission is recorded for this person. Nothing was changed.'}
    assert not [1 for sql, _ in conn.sql if 'vw2_log' in sql] and sheets(saved(store), 'P1')


@pytest.mark.parametrize('error', ['Provider rejected the request.', 'The model returned no picture: blocked (PROHIBITED_CONTENT).'])
def test_a_photo_that_gives_no_picture_offers_another_photo_or_a_stand_in(error):
    store, conn, s = with_sets(doc_with(KILN, MASON))
    yes(store, conn)
    own(store, conn, 'P1')
    VS.set_make(conn, store, USER, NEW, [], 'P1')
    s = saved(store)
    for r in s['references'].values():
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            r.update(status='failed', error=error)
    VS.save_session(store, NEW, s)
    row = view(store, conn)['round']['elements']['P1']
    assert row['problem'].endswith(' ' + VS.LIKENESS_REFUSED) and 'vw visuals likeness --element P1 --stand-in' in row['next']
    s = saved(store)
    ctx = {'session': s, 'plan': VS.current_plan(store, s), 'run': NEW, 'store': store, 'user': USER, 'outputs': [], 'conn': conn}
    assert [i for i in CF._round_items(ctx) if i['id'].startswith('likeness:P1')]


# ---------- 3. the cost limit and a storage hiccup ----------

class Hiccup(FakeStore):
    def exists(self, key):
        return False   # as the real store answers on any failed call


def test_a_failed_storage_call_never_rewrites_a_running_films_limit(monkeypatch):
    for sess, cap, how in ((session(updated_at='2026-11-01T00:00:00+00:00'), None, None),                                          # the older ₹5,000, no figure in the session
                           (session(updated_at='2026-11-01T00:00:00+00:00', cap_inr=900.0, cap_from='owner'), 900.0, 'owner'),      # the owner's figure
                           (session(updated_at='2026-11-01T00:00:00+00:00', cap_inr=4000.0), 4000.0, None)):                        # a figure with no source: left alone
        store = Hiccup({'run-1/visuals/session.json': sess})
        prepared(monkeypatch, store, 15000)
        assert saved(store).get('cap_inr') == cap and saved(store).get('cap_from') == how
    store = Hiccup({})   # a film that was never prepared gets its limit, and a length-based limit still rises
    prepared(monkeypatch, store, 1500)
    assert saved(store)['cap_inr'] == 1500.0 and saved(store)['cap_from'] == 'length'
    prepared(monkeypatch, store, 15000)
    assert saved(store)['cap_inr'] == 7500.0


# ---------- 7. "not to scale" with every size known ----------

def test_a_drawing_not_to_scale_with_every_size_known_is_taken(long_shots):
    known = {**SPEC, 'illustrative': True, 'dimensions': [SPEC['dimensions'][0]]}
    said = lambda d: ' | '.join(w['message'] for w in check(d)[1] if w['kind'] == 'spec_unresearched')
    assert said(drawing({**known, 'label': 'The wall, not to scale'})) == ''
    VC.spec_research_needs('shot DG1', VC.DrawingSpec.model_validate(known))   # the approval's check takes it too
    assert 'shot DG1: the drawing is marked illustrative (not drawn to scale): its label carries the words "not to scale".' in str(plan_refused(drawing({**known, 'label': 'The wall'})))
    assert 'a size is unknown: set illustrative true' in said(drawing({**SPEC, 'illustrative': False}))   # the other half stays
    assert 'researched' not in VC._illustrative_needs.__doc__ and 'four' not in VC._illustrative_needs.__doc__


# ---------- 8. who sets the cost limit ----------

def test_the_limits_messages_say_the_owner_runs_it_from_their_own_sign_in():
    store = store_with(session(cap_inr=1500.0, cap_from='length'))
    with pytest.raises(Problem) as exc:
        g(lambda: VS.set_cap(H.Conn(), store, {**USER, 'role': 'Member'}, RUN, [], 3000, 'raise it'))
    assert exc.value.status == 403 and exc.value.message == ('Only the owner can set the cost limit of a film, from their own sign-in. This sign-in is not the owner\'s: '
                                                           'tell the operator to ask the owner.')
    for sess, clause in ((session(cap_inr=10.0, cap_from='length'), "The limit follows the film's length. "), (session(cap_inr=10.0, cap_from='owner'), 'The owner set this limit. '),
                         (session(), 'This film keeps the older limit. ')):
        with pytest.raises(Problem) as exc:
            VS.check_cap(FakeConn([]), RUN, {**sess, 'cap_inr': 10.0}, 40.0, 'a 5 s take')
        assert exc.value.message == ("₹0 spent of ₹10 on this film's visuals; a 5 s take needs about ₹40. Stop and tell the operator the spend. " + clause +
                                     "Only the owner can set another figure for this film, from their own sign-in (`vw visuals cap`): tell the operator to ask the owner.")


# ---------- 10. people who read alike, all at once, at the check ----------

def alike_doc():
    twin = lambda pid: {'id': pid, 'name': pid, 'kind': 'person', 'identity': 'representative', 'requirements': 'a visitor', 'description': 'a friendly visitor in a blue coat'}
    return doc_with(KILN, MASON, HELPER, twin('P3'), twin('P4'), twin('P5'))


def test_the_check_names_every_pair_of_people_who_read_alike_in_one_warning():
    assert VS.alike_people(alike_doc()) == [('P3', 'P4'), ('P3', 'P5'), ('P4', 'P5')] and VS.alike_people(doc_with(KILN, MASON, HELPER)) == []
    ws = [w for w in VS.carried_warnings(session(), NEW, alike_doc(), []) if w['kind'] == 'people_alike']
    assert ws == [{'kind': 'people_alike', 'answered': False,
                   'message': 'These people read alike in their descriptions (age, build, hair, face): P3 and P4; P3 and P5; P4 and P5. The reference round refuses people who cannot be told apart. '
                              "Write each person's age, build, hair and face in their `description`, so that every pair differs in at least one."}]
    assert 'people_alike' in VC.WARNING_TECHNICAL and 'people_alike' not in VC.WARNING_PLAIN
    assert not [w for w in VS.carried_warnings(session(), OLD, alike_doc(), []) if w['kind'] == 'people_alike']   # an older film's round does not compare people
    with pytest.raises(ValueError, match='These two people read alike, '):   # the refusal at the round, one pair; design/216 (B5): in plain words (before: 'P3 and P4 are alike on every compared trait')
        VS.distinct_people(alike_doc())


# ---------- 11. smaller faults ----------

def test_a_gap_the_treatment_gave_as_footage_may_show_its_frame_as_a_still():
    footage = {'gaps': [{'gap_id': 'G1', 'routes': ['footage', 'video'], 'seconds': 20, 'shots': [{'route': 'footage', 'seconds': 4}, {'route': 'video', 'seconds': 16}]}]}
    assert not carried(small_plan([still()]), run={**RUN, **FILM}, treatment=footage)   # a frame shown in the film is a still in the plan
    assert [w['kind'] for w in carried(small_plan([still()]), run={**RUN, **FILM}, treatment=AGREED)] == ['still_more_than_agreed']


def test_a_group_of_forty_can_be_planned_one_trait_per_head():
    VC.Group.model_validate({'kind': 'people', 'count': 40, 'mode': 'different', 'items': [f'trait {n}' for n in range(40)]})
    with pytest.raises(ValueError):
        VC.Group.model_validate({'kind': 'people', 'count': 101, 'mode': 'different', 'items': [f'trait {n}' for n in range(101)]})


def test_a_scene_level_fault_does_not_blame_the_next_scenes_first_shot():
    d = with_person(plan([]))
    d = scenes_of(d, [pic('I1', 0, 300)], [pic('I2', 300, 1000)])
    d['gaps'][0]['scenes'][0]['outfit'] = {}
    assert plan_refused(d).errors == ['scene SC1 shows E1: give outfit[E1], the garment colours of this scene.']


def test_a_scene_of_unsized_shots_does_not_wipe_what_was_shown_just_before():
    d, wide, close = framing_doc()
    unsized = pic('IM4', 300, 400, element_ids=['E1', 'ROOM'])
    assert 'size' not in unsized or not unsized['size']
    found = kinds(scenes_of(d, [wide], [unsized], [{**close, 'start_frame': 400, 'end_frame': 1000}]))
    assert ('IM2', 'size_open') not in found and ('IM2', 'size_close_first') not in found


def test_the_untried_kind_is_told_for_ai_video_shots_only():
    assert 'video_untried' not in {k for _, k in kinds(plan([pic('IM1', 0, 1000, recipe='other')]))}


def test_a_card_of_words_is_not_warned_on_a_film_with_no_category_recorded():
    card = {'id': 'T1', 'visual_type': 'diagram', 'graphic_kind': 'title', 'start_frame': 0, 'end_frame': 100, 'element_ids': []}
    assert not carried(small_plan([card]), run=RUN)   # an older film: no film record at all
    assert [w['kind'] for w in carried(small_plan([card]), run={**RUN, 'film': {'category': {'value': 'documentary-explainer'}}})] == ['text_card']


def test_a_person_seen_only_in_their_own_footage_needs_no_row_in_the_round():
    doc = doc_with(KILN, MASON, HELPER)
    doc['gaps'][0]['scenes'][0]['shots'][0].update(visual_type='footage', element_ids=['E1', 'P2'])   # the helper is only in the footage
    doc['gaps'][1]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'P1']
    store, conn = frames_only(doc), FakeConn([])
    rows = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln'}]
    said = refused(lambda: VS.round_start(store, USER, NEW, [], rows, conn=conn))
    assert 'add a row for P1 ' in said and 'P2' not in said
    VS.round_start(store, USER, NEW, [], rows + [{'element_id': 'P1', 'prompt': 'kneels'}], conn=conn)


def test_a_face_is_added_only_while_the_picture_service_has_room():
    refs = {}
    for n in range(1, 4):
        for k in (1, 3):
            refs[f'S{n}-{k}' if k > 1 else f'S{n}'] = {'id': f'S{n}-{k}' if k > 1 else f'S{n}', 'kind': 'sheet', 'set': f'S{n}', 'set_n': k, 'element_id': f'P{n}', 'status': 'approved'}
    s, people = {'references': refs}, {f'P{n}': f'Person {n}' for n in range(1, 4)}
    fronts = [refs['S1'], refs['S2'], refs['S3']]
    parents, lines = VS.with_faces(s, fronts, people)
    assert len(parents) == 6 and len(lines) == 3
    parents, lines = VS.with_faces(s, fronts, people, room=1)   # one more picture fits in all
    assert [p['id'] for p in parents] == ['S1', 'S2', 'S3', 'S1-3'] and lines == ['Image 4 is the face of P1 (Person 1): take the face from it, nothing else.']
    parents, lines = VS.with_faces(s, fronts, people, room=5, faces=2)   # two more pictures of people fit
    assert [p['id'] for p in parents] == ['S1', 'S2', 'S3', 'S1-3', 'S2-3'] and len(lines) == 2 and not any('P3' in l for l in lines)   # no line says a picture is attached when it is not
    assert VS.with_faces(s, fronts, people, room=0) == (fronts, [])


def test_the_messages_are_generic_and_never_send_the_operator_to_the_servers_page():
    assert 'side workers' not in VS.distinct_people.__doc__ + str(_alike_message())
    said = VS.own_picture_refused('person', {}, 'P1')
    assert 'on the page' not in said and 'vw visuals likeness --element P1 --quote' in said
    src = (ROOT / 'server' / 'app' / 'visuals_stage.py').read_text(encoding='utf-8')
    assert 'approve it on the References step' not in src and '(`vw visuals spec`, or on the page)' not in src
    d = with_person(plan([pic('I1', 0, 1000)]))
    d['elements'][0]['description'] = ''
    assert plan_refused(d).errors == ["E1 is a person: give description, the fixed layer every prompt carries: the face, build, age, skin and hair. The clothes belong to each scene's outfit."]


def _alike_message():
    with pytest.raises(ValueError) as e:
        VS.distinct_people(alike_doc())
    return e.value


# ---------- 4. the operator's plain lines on the plan page ----------

def warned_page(choices_on=None):
    plan = H.plan_of(3, choices_on=choices_on)
    plan['elements'].append({'id': 'asha', 'name': 'Asha Rao', 'kind': 'person', 'speaker': True, 'description': 'a woman of about forty'})
    for sc in H.V.all_scenes(plan['gaps'][2]):
        sc['shots'][0]['element_ids'] = ['wall', 'asha']
    store, conn = H.Store(), H.Conn()
    H.fresh(store)
    s = H.session(store)
    VS.new_version(store, H.RUN, s, plan, H.USER, [{'kind': 'people_many', 'shot_id': 'G1-S1', 'message': 'for the assistant'}, {'kind': 'size_open', 'shot_id': 'G1-S1', 'message': 'technical'},
                                                   {'kind': 'stills_many', 'gap_id': 'G2', 'message': 'film-wide, attached to its first gap'}])
    VS.save_session(store, H.RUN, s)
    return store, conn


def lines_of(store, conn):
    return {l['key']: l for l in PF.page(conn, store, H.USER, H.RUN, {})['lines']}


def test_each_open_gap_of_the_plan_page_carries_its_plain_lines_and_never_a_technical_one():
    store, conn = warned_page()
    lines = lines_of(store, conn)
    assert lines['G1']['warnings'] == ['Shot G1-S1 (G1-S1): ' + VC.WARNING_PLAIN['people_many']]          # the shot's title leads; the technical warning is not told
    assert lines['G2']['warnings'] == [VC.WARNING_PLAIN['stills_many']]                            # a film-wide line shows on the gap it is attached to
    assert lines['G3']['warnings'] == ['Shot G3-S1 (G3-S1): ' + VC.WARNING_PLAIN['stand_in_real']]         # worked out now: the stored proposal holds no such line
    assert lines['G1']['table'] and lines['G1']['state'] == 'open'


def test_the_stand_in_line_goes_once_the_permission_is_recorded_without_a_new_proposal():
    store, conn = warned_page()
    s = H.session(store)
    s['likeness'] = {'asha': {'quote': WORDS, 'by': 'u1', 'at': 'now'}}
    VS.save_session(store, H.RUN, s)
    lines = lines_of(store, conn)
    assert 'warnings' not in lines['G3'] and lines['G1']['warnings']
    assert VS.plain_warnings(H.session(store), VS.current_plan(store, H.session(store))['gaps'][2], VS.current_plan(store, H.session(store))) == []   # the server's page reads the same


def test_a_gap_offered_two_ways_carries_its_plain_lines_too_and_the_chat_says_them():
    store, conn = warned_page(choices_on='G2')
    line = lines_of(store, conn)['G2']
    assert line['ways'] and line['warnings'] == [VC.WARNING_PLAIN['stills_many']]
    item = next(i for i in H.items(store, conn) if i['id'].startswith('gap:G1:'))
    assert '**Read before you answer:** Shot G1-S1 (G1-S1): ' + VC.WARNING_PLAIN['people_many'] in item['text']
