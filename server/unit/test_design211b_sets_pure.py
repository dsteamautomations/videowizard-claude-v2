"""design/211 part B, the sets (sections 3.5 to 3.7): the facts of a thing, the three views, the request per kind of thing with the plan's
own words placed by the server, the film's own pictures as inputs, the lines of the check, the repaired size check, the check on all three
pictures, what the page reads of a set (`check_summary`, `set_facts`), and the failure text that names who was really called.

Part A's functions (`ref_find.frames_of`, `round_frames`, `fingerprint`) are stubs in this worktree: `finder` stands in for them, from the
shared fixture's own data. Without a database."""
import copy
import hashlib
import json
import re

import pytest

from app import image_check as IC, library, ref_find, ref_sets as RS, visual_workers as VW, visuals_stage as VS
import d211_fixture as F
from test_design211b_older_pure import RUN, SESSION_KEY, saved, store_of   # noqa: F401 (the harness of the round's tests too)
from test_visuals_stage_pure import FakeConn, USER   # noqa: F401

KINDS = ('MASON', 'TROWEL', 'BRICK', 'STREET', 'T_LAY', 'TILE', 'FAN')
BANNED = re.compile(r'\b(site|trade)\b|how the work is done|natural daylight', re.I)
SHEET = 'drawing-TILE-iso-eeeeeeee'


def frames_of(session, eid):
    kept = ((session.get('found') or {}).get(eid) or {}).get('kept') or []
    rows = [r for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved') and r.get('look')]
    rows.sort(key=lambda r: kept.index(r['id']) if r['id'] in kept else 99)
    return [{'ref': r['id'], 'view': r['view'], 'verdict': r['look']['verdict'], 'seen': r['look']['seen'], 'weak': r['weak']} for r in rows]


def round_frames(session, plan, eid, named):
    for fid in named:
        VS.need((session['references'].get(fid) or {}).get('look'), ref_find.FRAME_NO_LOOK.format(fid=fid, eid=eid))
    VS.need((session.get('found') or {}).get(eid), ref_find.NOT_SEARCHED.format(eid=eid))
    return [f['ref'] for f in frames_of(session, eid) if not named or f['ref'] in named]


def fingerprint(element):
    return hashlib.sha256(json.dumps([element.get(k) for k in ('name', 'kind', 'identity', 'description', 'requirements', 'required_views', 'size')], sort_keys=True).encode()).hexdigest()


@pytest.fixture(autouse=True)
def finder(monkeypatch):
    monkeypatch.setattr(ref_find, 'frames_of', frames_of)
    monkeypatch.setattr(ref_find, 'round_frames', round_frames)
    monkeypatch.setattr(ref_find, 'fingerprint', fingerprint)
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})


def el(eid, plan=None):
    return next(e for e in (plan or F.plan())['elements'] if e['id'] == eid)


def ready(state='making', plan=None):
    """The fixture's session with what the sets need to be made: BRICK's material spec approved, TILE's drawing as an approved reference."""
    s = F.specs_approved(F.session(state), plan or F.plan(), VS.spec_digest)
    s['references'][SHEET] = {'id': SHEET, 'kind': 'drawing', 'element_id': 'TILE', 'status': 'approved', 'key': f"{RUN['id']}/visuals/drawings/TILE/iso.png", 'sha256': 'f' * 64,
                              'width': 1600, 'height': 900, 'name': 'Roof tile: angled', 'view': 'iso'}
    return s


def request(eid, state='making', row=None, plan=None, session=None):
    plan = plan or F.plan()
    s = session or ready(state, plan)
    return RS.set_request(plan, RUN, s, el(eid, plan), s['round']['elements'][eid] if row is None else row)


# ---------- the facts of a thing ----------

def test_the_facts_of_a_thing_its_shots_in_film_order_the_closest_and_the_scene_of_its_first_shot():
    plan, s = F.plan(), F.session('1')
    t = RS.thing_facts(plan, s, el('TROWEL'))
    assert t['shots'] == [{'gap': 'G2', 'shot': 'G2-S1-SH1', 'size': 'MS', 'way': 'video'}, {'gap': 'G2', 'shot': 'G2-S1-SH2', 'size': 'CU', 'way': 'image'}]
    assert t['shots_made'] == 2 and t['closest'] == 'CU' and t['scene'] == {'gap': 'G2', 'scene': 'G2-S1', 'place': 'the wall under construction, late morning'}
    assert (t['id'], t['name'], t['kind'], t['identity'], t['real_person']) == ('TROWEL', "Mason's trowel", 'object', 'exact', False)
    assert t['description'] == 'A pointed steel blade, a reddish-brown handle.' and t['requirements'] == 'The trowel the mason uses on this site.'
    assert t['sizes'] == [{'part': 'blade', 'measure': 'length', 'value': 18, 'unit': 'cm', 'status': 'measured'}] and t['views'] == RS.view_names(el('TROWEL'))
    mason = RS.thing_facts(plan, s, el('MASON'))
    assert [x['way'] for x in mason['shots']] == ['footage', 'video'] and mason['shots_made'] == 1 and mason['closest'] == 'MS' and mason['scene']['scene'] == 'G1-S1'
    assert RS.thing_facts(plan, s, el('STREET'))['signs'] == ['tyre tracks in the sand', 'a bicycle against the wall']
    assert RS.thing_facts(plan, s, {**el('MASON'), 'speaker': True})['real_person'] is True


def test_a_thing_no_shot_names_has_no_shots_and_no_scene():
    plan = F.plan()
    for gap in plan['gaps']:
        for sc in gap['scenes']:
            for sh in sc['shots']:
                sh['element_ids'] = [e for e in sh['element_ids'] if e != 'FAN']
    t = RS.thing_facts(plan, F.session('1'), el('FAN', plan))
    assert t['shots'] == [] and t['shots_made'] == 0 and t['closest'] == '' and t['scene'] is None


# ---------- the three views ----------

def test_the_plans_views_come_first_and_the_kind_fills_to_three():
    # design/211 review (S10, S7): a default view the plan's own view already shows is left out; a material has its own views
    assert RS.view_names(el('TROWEL')) == ['side', 'in the hand, lifting mortar', 'the detail that shows how it is made']
    assert RS.view_names(el('TILE')) == ['underside', 'a stacked pair', 'as the film uses it']
    assert RS.view_names(el('FAN')) == ['whole and at rest', 'as the film uses it', 'the detail that shows how it is made']
    assert RS.view_names(el('BRICK')) == ['a surface of it, filling the frame', 'as the film uses it', 'very close: what it is made of']
    assert RS.view_names(el('STREET')) == F.VIEWS['STREET'] and RS.view_names(el('T_LAY')) == F.VIEWS['T_LAY'] and RS.view_names(el('MASON')) == F.VIEWS['MASON']
    four = {**el('TROWEL'), 'required_views': ['side', 'top', 'underside', 'in the hand']}
    assert RS.view_names(four) == ['side', 'top', 'underside']
    for eid in F.THINGS:
        views = RS.views_for(el(eid), F.plan())
        assert len(views) == 3 and all(v['name'] and v['ask'] for v in views) and [v['name'] for v in views] == RS.view_names(el(eid))


def test_two_views_that_read_the_same_are_one_and_the_kinds_own_view_is_never_added_twice():
    assert RS.view_names({**el('TROWEL'), 'required_views': ['side', 'Side view', 'the side']}) == ['side', 'as the film uses it', 'the detail that shows how it is made']
    assert RS.view_names({**el('TROWEL'), 'required_views': ['the whole trowel, at rest']})[1:] == ['as the film uses it', 'the detail that shows how it is made']
    assert RS.view_names({**el('STREET'), 'required_views': ['from the other side']}) == ['from the other side', 'the whole place', 'its fixed things']
    for views in (['side', 'Side view', 'the side'], ['underside', 'the underside view', 'whole and at rest']):
        names = RS.view_names({**el('TROWEL'), 'required_views': views})
        assert len(names) == len(set(names)) == 3


def test_a_persons_pictures_one_and_three_are_fixed_and_the_plan_drives_picture_two():
    assert [v['name'] for v in RS.views_for(el('MASON'), F.plan())] == ['full length, front', 'right hand and forearm', 'the face']
    assert RS.view_names({**el('MASON'), 'required_views': []}) == ['full length, front', 'full length, side', 'the face']
    assert RS.view_names({**el('MASON'), 'required_views': ['the face', 'front', 'kneeling at the wall']}) == ['full length, front', 'kneeling at the wall', 'the face']
    asks = ' '.join(v['ask'] for v in RS.views_for({**el('MASON'), 'required_views': []}, F.plan()))
    assert 'working pose' not in asks and not BANNED.search(asks)


# ---------- the request, per kind ----------

@pytest.mark.parametrize('eid', KINDS)
def test_the_request_places_the_plans_description_and_requirements_word_for_word(eid):
    r, e = request(eid), el(eid)
    assert e['description'] in r['prompt'] and e['requirements'] in r['prompt'] and e['name'] in r['prompt']
    assert r['parts']['description'] == e['description'] and r['parts']['requirements'] == e['requirements'] and r['parts']['kind'] == e['kind'] and r['parts']['subject'] == e['name']
    assert [v['name'] for v in r['views']] == RS.view_names(e) == r['parts']['views'] and len(r['views']) == 3
    assert set(r) == {'prompt', 'views', 'inputs', 'search', 'lines', 'parts'}
    assert set(r['parts']) == {'kind', 'subject', 'description', 'requirements', 'sizes', 'material', 'signs', 'place', 'look', 'category', 'added', 'operator', 'corrections', 'views', 'inputs', 'source'}
    assert r['parts']['look'] == 'handheld, natural colours, as the footage' and r['parts']['look'] in r['prompt']
    library.check_prompt(r['prompt'])       # the server's own lints pass on the server's own text
    library.check_quoted(r['prompt'], [])
    assert not library.image_names_missing(r['prompt'], len(r['inputs']))   # every picture sent is named


def test_no_request_carries_a_word_tied_to_one_kind_of_film():
    plan = F.plan()
    el('TROWEL', plan)['requirements'] = 'The trowel the mason uses here.'   # the plan's own words are the plan's; the fixed text is what is tested
    for eid in KINDS:
        for state in ('1', 'making'):
            r = request(eid, state, plan=plan)
            assert not BANNED.search(r['prompt']), (eid, BANNED.search(r['prompt']).group(0))
            assert not BANNED.search(' '.join(v['ask'] for v in r['views']) + ' '.join(l['pass_when'] for l in r['lines'])), eid
    for name in ('OPENING', 'FROM_WEB', 'FROM_FOOTAGE', 'ONE_THING', 'ONE_THING_FOOTAGE', 'SET_LINE', 'FINISH', 'NOTES', 'PERSON_SET'):
        assert not BANNED.search(getattr(RS, name)), name
    assert BANNED.search(VS.KEPT_PREAMBLE) and BANNED.search(VS.KEPT_COSMETICS) and BANNED.search(VS.PERSON_SET)   # the older text has them: it stays for an older round


def test_the_fixed_text_keeps_the_two_ideas_of_the_owners_text():
    r = request('FAN')
    assert RS.OPENING in r['prompt'] and RS.ONE_THING in r['prompt'] and RS.SET_LINE in r['prompt'] and RS.FINISH in r['prompt'] and RS.NOTES in r['prompt']
    assert 'correctness matters more than anything else' in RS.OPENING and 'the AI will copy exactly what it sees, including any mistake' in RS.OPENING
    assert 'show one real thing, as one real photograph would' in RS.ONE_THING and 'Do not combine them' in RS.ONE_THING and 'the photographs win' not in RS.FROM_WEB and 'the earlier one wins' in RS.AUTHORITY   # design/211 review (C3): one order of authority, said once
    assert 'never as a collage' in RS.SET_LINE and 'with URLs' in RS.NOTES


def test_sizes_carry_their_status_unknown_left_out_and_proposed_as_about():
    tile, trowel, mason = request('TILE'), request('TROWEL'), request('MASON')
    assert tile['parts']['sizes'] == ['tile length 41 cm', 'tile width about 24 cm'] and 'Sizes: tile length 41 cm; tile width about 24 cm.' in tile['prompt']
    assert trowel['parts']['sizes'] == ['blade length 18 cm'] and 'Sizes: blade length 18 cm.' in trowel['prompt']
    assert mason['parts']['sizes'] == [] and 'Sizes:' not in mason['prompt'] and 'height' not in mason['prompt']
    assert 'Sizes:' not in request('FAN')['prompt']


def test_a_material_gets_the_sentence_of_its_approved_spec_only():
    r = request('BRICK')
    assert r['parts']['material'] == VS.material_sentence(el('BRICK')) and r['parts']['material'] in r['prompt'] and r['parts']['sizes'] == []
    plain = request('BRICK', session=F.session('making'))   # the spec not approved: no sentence (the set is not made either: visuals_stage.set_cause)
    assert plain['parts']['material'] == '' and 'Material spec' not in plain['prompt']


def test_each_thing_is_placed_in_the_scene_of_its_own_first_shot_never_the_films_first_scene():
    first = 'the sandy street in front of the house'
    for eid, place in (('T_LAY', 'the wall under construction, late morning'), ('TROWEL', 'the wall under construction, late morning'), ('BRICK', 'the wall under construction, late morning'),
                       ('FAN', 'the family room, evening'), ('TILE', 'the family room, evening')):
        r = request(eid)
        assert r['parts']['place'] == place and f'Setting: {place}' in r['prompt'] and first not in r['prompt'], eid
    assert VS._place_look(F.plan())[0].startswith(first)   # what the older request used for every thing
    street = request('STREET')
    assert street['parts']['place'] == 'A sandy unpaved street between low houses' and 'Setting: the place itself, as described, in its own light and time: the sandy street in front of the house, morning.' in street['prompt']
    plan = F.plan()
    plan['gaps'][2]['scenes'][0]['shots'][0]['element_ids'] = []
    nowhere = request('FAN', plan=plan)
    assert nowhere['parts']['place'] == '' and f'Setting: {RS.NO_PLACE}' in nowhere['prompt'] and first not in nowhere['prompt']


def test_a_place_gets_its_first_two_signs_of_use_unless_it_is_staged_clean():
    r = request('STREET')
    assert r['parts']['signs'] == ['tyre tracks in the sand', 'a bicycle against the wall'] and 'Signs of use: tyre tracks in the sand; a bicycle against the wall.' in r['prompt']
    plan = F.plan()
    el('STREET', plan)['signs_of_use'].append({'landmark_id': 'gate', 'what': 'a third trace'})
    assert request('STREET', plan=plan)['parts']['signs'] == ['tyre tracks in the sand', 'a bicycle against the wall']
    el('STREET', plan)['staged_clean'] = 'shown at the handover'
    clean = request('STREET', plan=plan)
    assert clean['parts']['signs'] == [] and 'Signs of use' not in clean['prompt']
    assert request('T_LAY')['parts']['signs'] == []


def test_the_writers_added_words_are_placed_and_win_over_the_description_and_an_empty_one_adds_nothing():
    r = request('T_LAY')
    assert r['parts']['added'] == 'The brick is wet from soaking.' and "Added by the film's writer: The brick is wet from soaking." in r['prompt']
    assert "(1) the words added by the film's writer; (2) the description from the film's plan; (3) real photographs from the web" in r['prompt']   # design/211 review (C3): they win over the description by the order said once
    none = request('STREET', row={'prompt': '', 'operator_words': []})
    assert none['parts']['added'] == '' and none['parts']['operator'] == '' and 'Added by' not in none['prompt'] and "The operator's words" not in none['prompt']


def test_the_operators_latest_words_are_in_the_request_and_the_earlier_ones_are_not():
    r = request('STREET')   # the step-1 comment of the fixture
    assert r['parts']['operator'] == 'The street is wider than it looks.' and "The operator's words: The street is wider than it looks." in r['prompt']
    later = request('STREET', row={'prompt': '', 'operator_words': ['The street is wider than it looks.', 'No cars in it.']})
    assert "The operator's words: No cars in it." in later['prompt'] and 'wider than it looks' not in later['prompt'] and later['parts']['operator'] == 'No cars in it.'
    assert "The operator's words: Older hands." in request('MASON', row={'prompt': '', 'operator_words': ['Older hands.']})['prompt']


def test_a_footage_picture_is_the_first_input_it_wins_over_the_web_and_search_stays_on():
    web, own = request('FAN'), request('TROWEL')
    assert web['inputs'] == [] and web['parts']['source'] == 'web' and web['search'] is True and RS.FROM_WEB in web['prompt'] and RS.FROM_FOOTAGE not in web['prompt']
    assert "This film's own footage shows no picture of the subject" in RS.FROM_WEB
    assert own['inputs'] == [{'ref': 'f-trowel-side', 'role': 'footage', 'view': 'side'}, {'ref': 'f-trowel-use', 'role': 'footage', 'view': 'in the hand, lifting mortar'}] == own['parts']['inputs']
    assert own['parts']['source'] == 'footage' and own['search'] is True and RS.FROM_FOOTAGE in own['prompt'] and RS.ONE_THING_FOOTAGE in own['prompt'] and RS.FROM_WEB not in own['prompt']
    assert "the film's picture wins" in RS.FROM_FOOTAGE and "only for what the film's picture does not show" in RS.FROM_FOOTAGE
    assert RS.FRAME_LINE.format(k=1, name="Mason's trowel", view='side') in own['prompt'] and RS.NOTES_FOOTAGE in own['prompt'] and RS.NOTES not in own['prompt'] and RS.NOTES_FOOTAGE.startswith(RS.NOTES[:-1])


def test_a_weak_frame_is_named_weak_in_the_request():
    r = request('TROWEL')
    assert RS.FRAME_WEAK_LINE.format(k=2, name="Mason's trowel", view='in the hand, lifting mortar') in r['prompt']
    assert 'take its form, colour and material' in RS.FRAME_WEAK_LINE and 'show the thing whole and uncovered' in RS.FRAME_WEAK_LINE and 'weak picture' not in request('TILE')['prompt']


def test_a_frame_not_yet_approved_or_marked_not_this_is_no_input_and_three_at_most():
    assert request('TROWEL', state='1')['inputs'] == [] and request('TROWEL', state='1')['parts']['source'] == 'web'   # candidates at step 1: nothing is sent before the operator's answer
    s = ready()
    s['references']['f-trowel-side'].update(status='rejected')   # "Not this picture"
    assert [i['ref'] for i in request('TROWEL', session=s)['inputs']] == ['f-trowel-use']
    s = ready()
    for n in range(3):
        s['references'][f'f-more-{n}'] = {**copy.deepcopy(s['references']['f-trowel-side']), 'id': f'f-more-{n}'}
    assert len([i for i in request('TROWEL', session=s)['inputs'] if i['role'] == 'footage']) == 3


def test_the_approved_drawings_follow_the_footage_pictures_with_their_facts_and_a_photograph_is_asked():
    s = ready()
    s['drawings']['TILE']['facts'] = [{'what': 'ribs along the tile', 'value': 5}]
    r = request('TILE', session=s)
    assert r['inputs'] == [{'ref': 'f-tile-under', 'role': 'footage', 'view': 'underside'}, {'ref': SHEET, 'role': 'drawing', 'view': 'iso'}]
    assert RS.SHEET_LINE.format(k=2, name='Roof tile', view='iso') in r['prompt'] and VS.KEPT_DRAWN_LINE in r['prompt'] and '- ribs along the tile: 5' in r['prompt']
    checks = [l['check'] for l in r['lines']]
    assert 'drawn fact: ribs along the tile: 5' in checks and VS.DRAWN_LOOK_LINE in r['lines'] and 'matches the footage picture' in checks
    how = request('TILE', session=s, row={**s['round']['elements']['TILE'], 'drawn_how': 'How to read the drawings.\nImage 2 is the angled view.'})
    assert 'How to read the drawings.\nImage 2 is the angled view.' in how['prompt'] and RS.SHEET_LINE.format(k=2, name='Roof tile', view='iso') not in how['prompt']


def test_a_person_is_made_from_the_description_alone_and_from_their_photo_only_with_the_permission():
    r = request('MASON')
    assert r['inputs'] == [] and r['search'] is False and r['parts']['source'] == 'words' and RS.FROM_WEB not in r['prompt'] and 'Google' not in r['prompt']
    assert r['prompt'].startswith('Character sheet of The mason, a person in this film.') and 'Garments: a white shirt, a checked lungi.' in r['prompt']   # design/211 review: no code name
    assert RS.PERSON_SET.format(a='a full-length front view, standing at ease', b='right hand and forearm, the same person', c='a close view of the face') in r['prompt']
    s = ready()
    s['references']['own-1'] = {'id': 'own-1', 'kind': 'supplied', 'element_id': 'MASON', 'status': 'approved', 'created_at': F.NOW}
    assert request('MASON', session=s)['inputs'] == []   # a photo without the recorded permission is not sent
    s['likeness'] = {'MASON': {'quote': 'he agreed', 'by': 'u1', 'at': F.NOW}}
    own = request('MASON', session=s)
    assert own['inputs'] == [{'ref': 'own-1', 'role': 'photo', 'view': ''}] and VS.LIKENESS_PHOTO_LINE in own['prompt'] and own['parts']['source'] == 'footage' and own['search'] is False


def test_a_way_of_working_may_show_hands_in_the_request_and_its_lines_do_not_forbid_them():
    r = request('T_LAY')
    # design/211 review (C1): hands, forearms and a tool are allowed where the description names them, never required
    assert 'Hands, forearms and a tool are allowed where the description names them, never required.' in r['prompt'] and 'No face.' in r['prompt'] and 'No person and no face' not in r['prompt']
    checks = {l['check']: l['pass_when'] for l in r['lines']}
    assert 'no person' not in checks and 'hands and a tool are allowed, not required' in checks['the action is shown'] and 'no face' in checks['the action is shown']
    assert not any(re.search(r'no hands?\b', w) for w in checks.values())
    assert any('no hands' in l['pass_when'] for l in VS.KEPT_THING_LINES)   # the older lines forbade them: they stay for an older round
    thing = request('FAN')
    assert 'No person and no face in any picture. In a picture whose view shows it in use, the hand that holds it and the material it works on may be shown' in thing['prompt']
    assert 'No person as the subject.' in request('STREET')['prompt']


# ---------- the lines of the check ----------

def test_the_lines_of_a_set_by_kind_all_must():
    names = lambda eid, **kw: [l['check'] for l in request(eid, **kw)['lines']]
    assert names('FAN') == ['the view', IC.SAME_THING, 'matches the description', 'one thing only', 'nothing floats', 'no text', 'no person']
    assert names('BRICK') == names('FAN')
    assert names('TROWEL') == ['the view', IC.SAME_THING, 'matches the footage picture', 'matches the description', 'one thing only', 'nothing floats', 'no text', 'no person', 'a real face']   # design/213: its footage pictures are sent, so the face line is its own
    assert names('STREET') == ['the view', IC.SAME_THING, 'matches the description', 'nothing floats', 'no text', 'the place is the subject']
    assert names('T_LAY') == ['the view', IC.SAME_THING, 'matches the description', 'one thing only', 'nothing floats', 'no text', 'the action is shown']
    assert names('MASON') == ['the view', IC.SAME_THING, 'matches the description', 'no text', 'one person', 'plain ground']
    for eid in KINDS:
        lines = request(eid)['lines']
        assert all(l['weight'] == 'must' and l['pass_when'] for l in lines) and next(l for l in lines if l['check'] == IC.SAME_THING)['pictures'] == [2, 3]
        assert el(eid)['description'] in next(l for l in lines if l['check'] == 'matches the description')['pass_when']


def set_picture(n, lines, **more):
    return {'id': 's1' if n == 1 else f's1-{n}', 'kind': 'sheet', 'element_kind': 'object', 'set': 's1', 'set_n': n, 'server_checklist': lines, 'ask': f'the ask of picture {n}',
            'generation': {'size': {'aspect': '16:9', 'tier': '2K'}, 'parents': []}, **more}


def test_each_picture_of_a_set_reads_its_own_lines_the_view_of_its_turn_and_picture_one_only_from_the_second_on():
    lines = request('FAN')['lines']
    one, two = IC.lines_of(set_picture(1, lines)), IC.lines_of(set_picture(2, lines))
    assert IC.SAME_THING not in [l['check'] for l in one] and IC.SAME_THING in [l['check'] for l in two]   # design/213: the line's name
    assert one[0] == {'check': 'the view', 'weight': 'must', 'pass_when': 'the picture shows what its turn asked: the ask of picture 1'} and two[0]['pass_when'].endswith('the ask of picture 2')
    assert all('pictures' not in l for l in one + two) and [l['check'] for l in one[-2:]] == ['readable text', 'nothing extra']   # design/213: no footage picture was sent, so "a real face" is not asked
    older = {'id': 'x', 'kind': 'sheet', 'element_kind': 'object', 'set': 'x', 'set_n': 1, 'server_checklist': VS.KEPT_THING_LINES}
    assert IC.lines_of(older) == VS.KEPT_THING_LINES + IC.FIXED   # an older set's lines are read as before


def test_a_real_face_is_not_asked_of_a_persons_set_made_from_their_own_permitted_photo():
    lines = request('MASON')['lines']
    photo = set_picture(1, lines, element_kind='person', generation={'parents': [{'id': 'own-1'}]})
    words = set_picture(1, lines, element_kind='person')
    assert 'a real face' not in [l['check'] for l in IC.lines_of(photo)] and 'a real face' not in [l['check'] for l in IC.lines_of(words)]   # design/213: nor of a person made from words alone
    assert 'a real face' in [l['check'] for l in IC.lines_of(set_picture(1, request('TROWEL')['lines'], generation={'parents': [{'id': 'f-trowel-side'}]}))]


# ---------- the size check, repaired (for every run) ----------

def size_line(size, w, h):
    return IC.code_checks({'generation': {'size': size}}, {'width': w, 'height': h}, [])[0]


def test_the_size_line_compares_the_pictures_shape_with_the_aspect_asked():
    ok = size_line({'aspect': '16:9', 'tier': '2K'}, 2752, 1536)
    assert ok == {'check': 'size', 'pass_when': 'the picture is 16:9', 'weight': 'must', 'pass': True, 'seen': '2752x1536'}
    assert size_line({'aspect': '16:9', 'tier': '2K'}, 1536, 2752)['pass'] is False and size_line({'aspect': '9:16', 'tier': '2K'}, 1536, 2752)['pass'] is True
    assert size_line({'aspect': '16:9'}, 1920, 1080)['pass'] is True and size_line({'aspect': '16:9'}, 1920, 1200)['pass'] is False   # 2 % at most
    assert size_line({'aspect': '16:9'}, None, None)['pass'] is None and size_line({'aspect': 'wide'}, 100, 50)['pass'] is None and size_line({}, 100, 50)['pass'] is None


def test_a_size_given_as_a_string_is_compared_as_before():
    assert size_line('1536x1024', 1536, 1024) == {'check': 'size', 'pass_when': 'the picture is 1536x1024', 'weight': 'must', 'pass': True, 'seen': '1536x1024'}
    assert size_line('1536x1024', 1024, 1536)['pass'] is False and size_line(None, 10, 10)['pass'] is None and size_line('1536x1024', None, None)['pass'] is None


# ---------- all three pictures checked ----------

class Lock:
    def execute(self, *a, **k):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def finished(monkeypatch, request_more=None, extra=2, lines=True, older=False):
    """A set's job comes back with `extra` more pictures: finalize_image on a session whose first picture is being made."""
    s = F.session('making')
    first = s['references']['s-street-1']
    if older:
        first.pop('view')   # a set of an older round has no view on its pictures
        s['round'].pop('v')   # design/214: and its round is an older one: its pictures are still checked by the model
    if lines:
        first['server_checklist'] = request('STREET')['lines']
    store = store_of(s)
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW.jobs, 'finish', lambda *a, **k: None)
    monkeypatch.setattr(VW.jobs, 'record_file', lambda *a, **k: None)
    job = {'id': 'job-s-street-1', 'run_id': RUN['id'], 'request': {'reference': {'id': 's-street-1'}, **(request_more or {})}}
    result = {'key': f"{RUN['id']}/visuals/references/s-street-1.png", 'sha256': 'a', 'bytes': 9, 'width': 2752, 'height': 1536, 'notes': 'n', 'sources': [],
              'extra': [{'key': f"{RUN['id']}/visuals/references/s-street-1-{n}.png", 'sha256': str(n), 'bytes': 9, 'width': 2752, 'height': 1536} for n in range(2, 2 + extra)]}
    due = VW.finalize_image(Lock(), job, 'retained', result, None, {'provider': 'gemini', 'pictures': 1 + extra}, None)
    return store, job, result, due


def test_every_picture_of_a_set_waits_for_its_own_check_and_a_v2_set_carries_its_views(monkeypatch):
    views = RS.views_for(el('STREET'), F.plan())
    store, job, result, due = finished(monkeypatch, {'views': [v['ask'] for v in views], 'view_names': [v['name'] for v in views]})
    refs = saved(store)['references']
    # design/214: no model check for a set of a v2 round: nothing is due, nothing waits; each picture keeps the code checks (its size)
    assert not due and all('check_pending' not in refs[r] and list(refs[r]['check']) == ['code'] and refs[r]['check']['code'][0]['pass'] is True for r in ('s-street-1', 's-street-1-2', 's-street-1-3'))
    assert [refs[r]['view'] for r in ('s-street-1', 's-street-1-2', 's-street-1-3')] == F.VIEWS['STREET'] and refs['s-street-1-2']['ask'] == views[1]['ask']
    assert refs['s-street-1-3']['server_checklist'] == refs['s-street-1']['server_checklist'] and refs['s-street-1-2']['set_n'] == 2


def test_an_older_set_gets_three_checks_too_and_no_view(monkeypatch):
    store, job, result, due = finished(monkeypatch, {'views': VS.set_views(el('STREET'))}, older=True)   # the request of an older round: no view names
    refs = saved(store)['references']
    assert due is True and all(refs[r]['check_pending'] for r in ('s-street-1', 's-street-1-2', 's-street-1-3'))
    assert not any(k in refs[r] for k in ('ask', 'view') for r in ('s-street-1', 's-street-1-2', 's-street-1-3'))
    store, job, result, due = finished(monkeypatch, lines=False)
    assert not due and not any(r.get('check_pending') for r in saved(store)['references'].values())   # no checklist: nothing to check, as before


def test_the_check_runs_once_per_picture_and_each_keeps_its_own_record(monkeypatch):
    views = RS.views_for(el('STREET'), F.plan())
    store, job, result, due = finished(monkeypatch, {'views': [v['ask'] for v in views], 'view_names': [v['name'] for v in views]}, older=True)   # design/214: an older round's set
    seen = []

    def run_check(st, session, ref, res, transport):
        seen.append((ref['id'], res['key'], res['width'], res['height']))
        return {'code': [], 'lines': [{'check': 'the view', 'weight': 'must', 'pass': ref['id'] != 's-street-1-2', 'seen': ref['id']}], 'must_failed': [], 'model': 'm'}
    monkeypatch.setattr(IC, 'run_check', run_check)
    monkeypatch.setattr(VW, 'connect', lambda: Lock())
    VW.check_image(job, result)
    refs = saved(store)['references']
    assert [x[0] for x in seen] == ['s-street-1', 's-street-1-2', 's-street-1-3'] and seen[1][1:] == (f"{RUN['id']}/visuals/references/s-street-1-2.png", 2752, 1536)
    assert [refs[r]['check']['lines'][0]['seen'] for r in ('s-street-1', 's-street-1-2', 's-street-1-3')] == ['s-street-1', 's-street-1-2', 's-street-1-3']
    assert not any('check_pending' in refs[r] for r in ('s-street-1', 's-street-1-2', 's-street-1-3'))


def test_a_partial_set_checks_what_came(monkeypatch):
    store, job, result, due = finished(monkeypatch, extra=1, older=True)   # design/214: an older round's set
    seen = []
    monkeypatch.setattr(IC, 'run_check', lambda st, session, ref, res, transport: seen.append(ref['id']) or {'code': [], 'lines': [], 'must_failed': [], 'model': 'm'})
    monkeypatch.setattr(VW, 'connect', lambda: Lock())
    VW.check_image(job, result)
    assert seen == ['s-street-1', 's-street-1-2'] and 's-street-1-3' not in saved(store)['references']


def test_pictures_two_and_three_are_checked_with_picture_one_beside_them(monkeypatch):
    s = F.session('2')
    lines = request('STREET')['lines']
    for r in ('s-street-1', 's-street-1-2'):
        s['references'][r]['server_checklist'] = lines
    store = store_of(s)
    for r in ('s-street-1', 's-street-1-2'):
        store.files[s['references'][r]['key']] = b'png-' + r.encode()
    sent = []
    monkeypatch.setattr(IC.keys, 'pool', lambda *a: ['k'])
    monkeypatch.setattr(IC, 'build', lambda png, parents, ls, prompt: sent.append((png, parents, [l['check'] for l in ls])) or {})
    monkeypatch.setattr(IC.keys, 'gemini', lambda *a, **k: ({'body': {'lines': []}}, 0))
    for r in ('s-street-1', 's-street-1-2'):
        ref = s['references'][r]
        IC._model_check(store, s, ref, {'key': ref['key'], 'width': 2752, 'height': 1536}, None)
    assert sent[0][1] == [] and IC.SAME_THING not in sent[0][2]
    assert sent[1][1] == [('picture 1 of this set', b'png-s-street-1')] and IC.SAME_THING in sent[1][2] and sent[1][0] == b'png-s-street-1-2'


# ---------- one picture's check, for the page ----------

def test_check_summary_says_pass_fail_or_that_the_check_did_not_run():
    s = F.session('2')
    assert RS.check_summary(s, 's-street-1') == {'state': 'pass', 'failed': [], 'error': None}
    assert RS.check_summary(s, 's-t_lay-1-2') == {'state': 'fail', 'failed': [{'check': 'the action is shown', 'seen': 'A tool lying still; no hand.'}], 'error': None}
    assert RS.check_summary(s, s['references']['s-t_lay-1-2']) == RS.check_summary(s, 's-t_lay-1-2')   # the row itself is taken too
    assert RS.check_summary(F.session('making'), 's-street-1') == {'state': 'none', 'failed': [], 'error': None} == RS.check_summary(s, 'no-such-picture')
    # design/214: a set of a v2 round is checked by Claude's look; a model's record stored before (its error, its lines) is not read. The code checks stay.
    s['references']['s-street-1']['check'] = {'code': [{'check': 'size', 'weight': 'must', 'pass': True, 'seen': '2752x1536'}], 'lines': [], 'must_failed': [], 'model': 'm', 'error': 'no Gemini key on the server'}
    assert RS.check_summary(s, 's-street-1') == {'state': 'pass', 'failed': [], 'error': None}
    s['references']['s-street-1']['check']['code'][0].update({'pass': False, 'seen': '1536x2752'})   # the shape is wrong: the shape is still said
    assert RS.check_summary(s, 's-street-1') == {'state': 'fail', 'failed': [{'check': 'size', 'seen': '1536x2752'}], 'error': None}
    old = F.older_session()   # a set of an older round: the model's record, read as before
    old['references']['s-street-1']['check'] = {'code': [{'check': 'size', 'weight': 'must', 'pass': False, 'seen': '1536x2752'}], 'lines': [], 'must_failed': [], 'model': 'm', 'error': 'no Gemini key on the server'}
    assert RS.check_summary(old, 's-street-1') == {'state': 'fail', 'failed': [{'check': 'size', 'seen': '1536x2752'}], 'error': 'no Gemini key on the server'}
    old['references']['s-street-1']['check']['code'][0]['pass'] = True
    assert RS.check_summary(old, 's-street-1') == {'state': 'none', 'failed': [], 'error': 'no Gemini key on the server'}


# ---------- what the page reads of a set ----------

def facts(s, eid, plan=None):
    return RS.set_facts(s, plan or F.plan(), eid, s['round']['elements'][eid])


def test_set_facts_of_a_made_set_its_pictures_checks_looks_notes_and_the_recommendation():
    s = F.session('2')
    f = facts(s, 'T_LAY')
    assert set(f) == {'pictures', 'inputs', 'from', 'notes', 'sources', 'partial', 'rec', 'makes', 'makes_left', 'asked', 'history', 'changed', 'fail', 'model', 'footage'}   # design/213
    assert [(p['ref'], p['n'], p['view']) for p in f['pictures']] == [('s-t_lay-1', 1, F.VIEWS['T_LAY'][0]), ('s-t_lay-1-2', 2, F.VIEWS['T_LAY'][1]), ('s-t_lay-1-3', 3, F.VIEWS['T_LAY'][2])]
    assert [p['check']['state'] for p in f['pictures']] == ['pass', 'fail', 'pass'] and f['pictures'][1]['look']['verdict'] == 'weak' and f['pictures'][0]['look']['ref'] == 's-t_lay-1'
    assert f['rec'] == {'do': 'remake', 'golden': None, 'reason': 'Picture B shows no hand at work.'} and f['from'] == 'web' and f['inputs'] == []
    assert f['notes'].startswith('(1) One method') and f['sources'] == [{'url': 'https://example.org/a', 'title': 'A page'}]
    assert (f['makes'], f['makes_left'], f['asked'], f['history'], f['partial'], f['fail']) == (1, 2, None, [], None, None)
    assert facts(F.session('looking'), 'STREET')['rec'] is None and facts(F.session('looking'), 'STREET')['pictures'][0]['look'] is None
    s['round']['elements']['STREET']['parts'] = request('TROWEL', session=ready('2'))['parts']
    assert facts(s, 'STREET')['from'] == 'footage' and [i['ref'] for i in facts(s, 'STREET')['inputs']] == ['f-trowel-side', 'f-trowel-use']


def test_set_facts_after_a_remake_the_words_asked_the_history_and_the_makes_left():
    f = facts(F.session('complete'), 'T_LAY')
    assert f['makes'] == 2 and f['makes_left'] == 1 and f['asked'] == 'Show the hand pressing the brick down.' and f['rec']['do'] == 'use'
    assert f['history'] == [{'n': 1, 'set': 's-t_lay-1', 'added': 'The brick is wet from soaking.', 'operator': 'Show the hand pressing the brick down.'}]
    s = F.session('complete')
    s['round']['elements']['T_LAY']['round'] = 3
    assert facts(s, 'T_LAY')['makes_left'] == 0
    waiting = facts(F.session('rewrite'), 'T_LAY')   # rejected, the rewrite not sent yet: no picture of a set to judge
    assert waiting['pictures'] == [] and waiting['fail'] is None and waiting['rec'] is None and waiting['asked'] is None


def test_a_partial_set_is_shown_as_it_is_with_the_missing_view_named():
    s = F.session('2')
    s['references'].pop('s-street-1-3')
    f = facts(s, 'STREET')
    assert f['partial'] == {'made': 2, 'asked': 3, 'missing': ['its fixed things']} and len(f['pictures']) == 2
    s['references'].pop('s-street-1-2')
    assert facts(s, 'STREET')['partial'] == {'made': 1, 'asked': 3, 'missing': ['from the other side', 'its fixed things']}
    assert facts(F.session('2'), 'STREET')['partial'] is None


def failed_set(provider='gemini', model='gemini-nano-banana-2.1', error='', failure=None):
    s = F.session('making')
    s['references']['s-street-1'].update(status='failed', error=error, **({'failure': failure} if failure else {}))
    s['references']['s-street-1']['generation'].update(provider=provider, model=model)
    return s


def test_the_failure_names_the_provider_the_model_and_the_real_cause_never_openai_for_a_gemini_job():
    who = "Google's image model gemini-nano-banana-2.1"
    cases = [("Google's image model gemini-nano-banana-2.1 returned no picture: SAFETY", {'failure': 'no_image', 'http_status': 400}, 'no_picture', who + ' returned no picture.'),
             (who + ' rejected the request (HTTP 400): bad input.', {'failure': 'provider', 'http_status': 400}, 'refused', who + ' refused the request.'),
             (who + ' returned HTTP 429 on 4 attempts; no further retry.', {'failure': 'provider', 'http_status': 429}, 'limit', who + ' is at its limit for now: too many requests.'),
             ('The picture service did not answer in time (timeout).', None, 'timeout', who + ' did not answer in time.'),
             ('KeyError: data', None, 'other', who + ' could not make the picture.')]
    for error, failure, cause, text in cases:
        f = facts(failed_set(error=error, failure=failure), 'STREET')['fail']
        assert f == {'cause': cause, 'model': 'gemini-nano-banana-2.1', 'text': text} and 'OpenAI' not in f['text']
    old = facts(failed_set(error='OpenAI rejected the request (HTTP 400).'), 'STREET')['fail']   # a failure recorded before the release, with the false name: the job's own record wins
    assert old['text'] == who + ' refused the request.' and old['cause'] == 'refused'
    gpt = facts(failed_set('openai', 'gpt-image-2', 'OpenAI refused the request: the prompt or the pictures are the problem'), 'STREET')['fail']
    assert gpt == {'cause': 'refused', 'model': 'gpt-image-2', 'text': "OpenAI's image model gpt-image-2 refused the request."}
    assert facts(F.session('making'), 'STREET')['fail'] is None and facts(F.session('2'), 'STREET')['fail'] is None


def test_a_set_the_server_refused_before_any_call_says_the_servers_own_reason():
    s = F.session('making')
    s['round']['elements']['BRICK'].update(error='the material spec of BRICK is not approved, or changed since: the operator approves it first, on the page (`vw visuals page`), before a picture shows it.')
    f = facts(s, 'BRICK')['fail']
    assert f['cause'] == 'other' and f['model'] is None and f['text'].startswith('the material spec of BRICK is not approved') and '`' not in f['text']
    s['round']['elements']['BRICK']['error'] = "₹3,700 spent of ₹3,754 on this film's visuals; a set of three needs about ₹106."
    assert facts(s, 'BRICK')['fail']['cause'] == 'limit'


def test_a_set_is_marked_changed_when_the_plan_the_spec_or_the_photo_changed_since_it_was_made():
    plan = F.plan()
    s = ready('2', plan)
    for eid in F.FIRST:
        s['round']['elements'][eid]['made'].update(fp=RS.fp(plan, s, el(eid, plan)), photo=None)
    assert not facts(s, 'STREET', plan)['changed'] and not facts(s, 'T_LAY', plan)['changed'] and not facts(s, 'MASON', plan)['changed']
    changed = copy.deepcopy(plan)
    el('STREET', changed)['description'] = 'A paved street between low houses.'
    assert facts(s, 'STREET', changed)['changed'] and not facts(s, 'T_LAY', changed)['changed']
    moved = copy.deepcopy(plan)
    moved['gaps'][1]['scenes'][0]['location_time'] = 'the yard behind the house, noon'   # the place the set of T_LAY was made in
    assert facts(s, 'T_LAY', moved)['changed'] and not facts(s, 'STREET', moved)['changed']
    s['likeness'] = {'MASON': {'quote': 'he agreed', 'by': 'u1', 'at': F.NOW}}
    s['references']['own-1'] = {'id': 'own-1', 'kind': 'supplied', 'element_id': 'MASON', 'status': 'approved', 'created_at': F.NOW}
    assert facts(s, 'MASON', plan)['changed']   # a photo given since
    b = ready('2', plan)
    sid, rows = F._set('STREET', 'material')
    b['references'].update({k.replace('street', 'brick'): {**v, 'id': k.replace('street', 'brick'), 'element_id': 'BRICK', 'set': 's-brick-1'} for k, v in rows.items()})
    b['round']['elements']['BRICK'].update(set='s-brick-1', round=1, made={'at': F.NOW, 'photo': None, 'specs': {'BRICK': VS.spec_digest(el('BRICK', plan)['material_spec'])}, 'fp': RS.fp(plan, b, el('BRICK', plan))})
    assert not facts(b, 'BRICK', plan)['changed']
    b['round']['elements']['BRICK']['made']['specs'] = {'BRICK': 'another digest'}
    assert facts(b, 'BRICK', plan)['changed']
    assert not facts(F.session('making'), 'STREET')['changed']   # nothing made yet


# ---------- the worker's own failure text ----------

class Answer:
    def __init__(self, status, body=None, text=''):
        self.status_code, self._body, self.text, self.content = status, body or {}, text or json.dumps(body or {}), b'{}'

    def json(self):
        return self._body


def test_a_gemini_failure_is_named_as_googles_with_its_model_and_an_openai_one_as_before(monkeypatch, tmp_path):
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: None)
    gem = {'provider': 'gemini', 'model': 'gemini-nano-banana-2.1', 'op': 'generate', 'prompt': 'p', 'size': {'aspect': '16:9'}, 'quality': 'high', 'parents': [], 'reference': {'id': 'r1'}}
    who = "Google's image model gemini-nano-banana-2.1"
    for n, (answer, attempt, status, text) in enumerate([
            (Answer(400, {'error': {'type': 'provider', 'message': 'bad input'}}), 1, 'failed', who + ' rejected the request (HTTP 400): bad input.'),
            (Answer(400, {'error': {'type': 'no_image', 'message': 'SAFETY'}}), 1, 'failed', who + ' returned no picture: SAFETY'),
            (Answer(429), 4, 'rejected', who + ' returned HTTP 429 on 4 attempts; no further retry.'),
            (Answer(503), 1, 'queued', who + ' returned HTTP 503; attempt 2 of 4 in 1 min.'),
            (Answer(404), 1, 'rejected', 'Google reports the model gemini-nano-banana-2.1 is unavailable on this account.')]):
        monkeypatch.setattr(VW, '_gemini_image', lambda req, parents, a=answer: a)
        out = VW.process_image({'id': f'j{n}', 'run_id': 'run-1', 'request': gem, 'attempt': attempt})
        assert (out[0], out[2]) == (status, text) and 'OpenAI' not in out[2]
    assert VW.refusal(Answer(400))[1] == 'OpenAI rejected the request (HTTP 400).' == VW.refusal(Answer(400), {'provider': 'openai', 'model': 'gpt-image-2'})[1]
    monkeypatch.setattr(VW, 'openai_client', lambda path, **kw: Answer(503))
    out = VW.process_image({'id': 'j9', 'run_id': 'run-1', 'request': {**gem, 'provider': 'openai', 'model': 'gpt-image-2', 'size': '1536x1024'}, 'attempt': 1})
    assert out[2] == 'OpenAI returned HTTP 503; attempt 2 of 4 in 1 min.'


def test_a_failed_job_leaves_what_failed_on_its_picture(monkeypatch):
    ref = {'id': 'r1', 'status': 'generating'}
    assert VW.apply_image_result(None, 'run-1', ref, 'failed', {'failure': 'no_image', 'http_status': 400, 'detail': 'x'}, 'no picture', None)
    assert ref == {'id': 'r1', 'status': 'failed', 'error': 'no picture', 'failure': {'failure': 'no_image', 'http_status': 400}}
    plain = {'id': 'r2', 'status': 'generating'}
    VW.apply_image_result(None, 'run-1', plain, 'failed', {'phase': 'prepare'}, 'KeyError', None)
    assert plain == {'id': 'r2', 'status': 'failed', 'error': 'KeyError'}
