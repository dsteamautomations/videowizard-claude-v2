"""design/213, the server core of "References step 5" (judging the reference sets): a place gets one picture in a round posted from now
on; the writer's words rank above the film's own pictures; the check asks "a real face" only where a picture of the film was sent, and
compares a picture with picture A as another view of the same thing; the image model's notes are kept per picture and the look says what
the model chose and set aside; a first set that cannot be made is replaced; a person the footage shows is made from their own pictures,
with the recorded permission; the limit is said with no amount. Without a database."""
import copy
import inspect

import pytest

from app import image_check as IC, ref_find, ref_sets as RS, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
import d211_fixture as F
from test_design211b_round_pure import at_two, back, done, film, fresh, jobs, judge, look, looks, post, put, refused, rows, saved   # noqa: F401
from test_design211b_sets_pure import RUN, el, finder, ready, request, set_picture, store_of   # noqa: F401 (finder stands in for part A, on every test)
from test_visuals_stage_pure import FakeConn, USER

MARKED = {'v': 2, 'place_one': True}


@pytest.fixture(autouse=True)
def new_round(monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', 2)   # conftest gives every module not named test_design211* the older round; these tests post a round of today


def frame(fid, view, verdict='pass', face=True, status='approved', child=None, eid='MASON', kind='person'):
    seen = {'who': 'helper', 'at': F.NOW, 'view': view, 'verdict': verdict, 'seen': 'As asked.', 'trial': 't-' + fid, 'ref': fid,
            **({} if face is None else {'face': face}), **({} if child is None else {'child': child})}
    return {'id': fid, 'element_id': eid, 'element_kind': kind, 'name': f'frame-{eid}', 'kind': 'frame', 'subject': eid, 'status': status, 'key': f"{RUN['id']}/visuals/references/{fid}.png",
            'sha256': fid[-1] * 64, 'bytes': 9, 'width': 1920, 'height': 1080, 'created_at': F.NOW, 'view': view, 'look': seen, 'weak': verdict == 'weak', 'trial': 't-' + fid}


def shown(s, *frames, eid='MASON'):
    """The session with these kept footage frames of a thing, in this view order."""
    for f in frames:
        s['references'][f['id']] = f
    s['found'][eid]['kept'] = [f['id'] for f in frames]
    return s


def mason(state='making', permission=True):
    s = shown(ready(state), frame('m-hand', 'right hand and forearm', face=False), frame('m-weak', 'the face', 'weak'), frame('m-face', 'full length, front'))
    if permission:
        s['likeness'] = {'MASON': {'quote': 'he agreed', 'by': 'u1', 'at': F.NOW}}
    return s


# ---------- P: a place gets one picture ----------

def test_a_round_posted_now_is_marked_and_its_places_get_one_view_the_others_three():
    store, conn = film()
    post(store, conn)
    rd = saved(store)['round']
    assert rd['place_one'] is True
    street = RS.views_for(el('STREET'), F.plan(), rd)
    assert [v['name'] for v in street] == ['the whole place'] == RS.view_names(el('STREET'), rd) and 'The street' in street[0]['ask']
    assert RS.view_names({**el('STREET'), 'required_views': ['from the gate', 'at night']}, rd) == ['the whole place']
    assert RS.view_names(el('STREET')) == F.VIEWS['STREET'] == RS.view_names(el('STREET'), F.session('2')['round'])   # a round with no mark (VW-24): three, also for a place not ordered yet
    assert all(len(RS.view_names(el(e), rd)) == 3 for e in ('MASON', 'TROWEL', 'BRICK', 'T_LAY', 'TILE'))
    assert RS.thing_facts(F.plan(), saved(store), el('STREET'))['views'] == ['the whole place'] and RS.thing_facts(F.plan(), F.session('2'), el('STREET'))['views'] == F.VIEWS['STREET']
    assert ', '.join(inspect.signature(RS.views_for).parameters) == 'element, plan, rd' and ', '.join(inspect.signature(RS.view_names).parameters) == 'element, rd'


def test_the_request_of_a_one_picture_place_never_says_three_and_its_check_has_no_picture_a_line():
    s = ready()
    s['round'].update(MARKED)
    r = request('STREET', session=s)
    assert len(r['views']) == 1 and r['parts']['views'] == ['the whole place'] and RS.ONE_LINE in r['prompt'] and 'The view: the whole place.' in r['prompt']
    assert RS.SET_LINE not in r['prompt'] and not any(w in r['prompt'] for w in ('three', 'The three views', 'across the set'))
    assert [l['check'] for l in r['lines']] == ['the view', 'matches the description', 'nothing floats', 'no text', 'the place is the subject']
    old = request('STREET')   # the fixture's round has no mark
    assert len(old['views']) == 3 and RS.SET_LINE in old['prompt'] and 'The three views: ' in old['prompt'] and RS.ONE_LINE not in old['prompt']
    assert RS.SET_LINE in request('BRICK', session=s)['prompt'] and len(request('MASON', session=s)['views']) == 3


def test_a_one_picture_set_is_ordered_made_and_shown_as_one_picture():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    job = jobs(conn)['STREET']
    assert job['view_names'] == ['the whole place'] and len(job['views']) == 1 and len(jobs(conn)['T_LAY']['views']) == 3
    back(store, pictures=1)   # one picture each: whole for the place, partial for the others
    s = saved(store)
    f = RS.set_facts(s, F.plan(), 'STREET', s['round']['elements']['STREET'])
    assert [(p['n'], p['view']) for p in f['pictures']] == [(1, 'the whole place')] and f['partial'] is None
    assert RS.set_facts(s, F.plan(), 'T_LAY', s['round']['elements']['T_LAY'])['partial'] == {'made': 1, 'asked': 3, 'missing': F.VIEWS['T_LAY'][1:]}
    sent = looks(store, only=['STREET'])
    assert len(sent[0]['pictures']) == 1 and RS.round_looks(store, USER, RUN, [], [{**sent[0], 'chose': 'A sandy street.', 'aside': 'A paved one.'}], 'helper')['recorded'] == ['STREET']


def test_the_limit_counts_one_picture_for_a_one_picture_set():
    store, conn = film(fresh(cap_inr=15))   # three pictures are about 35, one about 12
    post(store, conn)
    out = done(store, conn, **{e: {'verdict': 'ignore'} for e in ('MASON', 'BRICK', 'T_LAY', 'TILE')})
    assert out['queued'] == ['STREET'] and out['errors'] == {}
    store, conn = film(fresh(cap_inr=15))
    post(store, conn)
    out = done(store, conn, **{e: {'verdict': 'ignore'} for e in ('MASON', 'BRICK', 'STREET', 'TILE')})
    assert out['queued'] == [] and out['errors'] == {'T_LAY': RS.LIMIT_PLAIN}


# ---------- C: the plan against the footage ----------

def test_the_writers_words_rank_above_the_films_own_pictures_and_the_footage_line_lets_them_win():
    s = ready()
    both = RS.set_request(F.plan(), RUN, s, el('TROWEL'), {'prompt': 'The blade is narrow.', 'operator_words': ['The handle is red.']})
    order = "(1) the operator's words; (2) the words added by the film's writer; (3) the film's own footage picture; (4) the description from the film's plan; (5) real photographs from the web"
    assert both['prompt'].count(RS.AUTHORITY.format(order=order)) == 1
    line = lambda r, name: next(l['pass_when'] for l in r['lines'] if l['check'] == name)
    assert line(both, 'matches the footage picture').endswith("; where the operator's words or the words added by the film's writer say otherwise, they win")
    assert line(both, 'matches the description').startswith("it agrees with these, the earlier winning where two differ: the operator's words: The handle is red; the words added by the film's writer: The blade is narrow; ")
    writer = RS.set_request(F.plan(), RUN, s, el('TROWEL'), {'prompt': 'The blade is narrow.'})
    assert line(writer, 'matches the footage picture').endswith("; where the words added by the film's writer say otherwise, they win")
    assert "(1) the words added by the film's writer; (2) the film's own footage picture" in writer['prompt']
    assert line(RS.set_request(F.plan(), RUN, s, el('TROWEL'), {'operator_words': ['Red.']}), 'matches the footage picture').endswith("; where the operator's words say otherwise, they win")
    assert 'they win' not in line(RS.set_request(F.plan(), RUN, s, el('TROWEL'), {}), 'matches the footage picture')


# ---------- K: the check tells the truth ----------

def test_a_real_face_is_asked_only_where_a_picture_of_the_film_was_sent_and_never_of_a_permitted_likeness():
    names = lambda ref: [l['check'] for l in IC.lines_of(ref)]
    assert 'a real face' not in names(set_picture(1, request('FAN')['lines']))                                    # made from the web: no footage picture was sent
    assert 'a real face' not in names(set_picture(1, request('MASON')['lines'], element_kind='person'))           # a person made from words alone
    assert 'a real face' in names(set_picture(1, request('TROWEL')['lines']))                                     # its footage pictures were sent
    assert names(set_picture(1, request('TROWEL')['lines'])).count('a real face') == 1
    own = request('MASON', session=mason())
    assert 'a real face' not in names(set_picture(1, own['lines'], element_kind='person', generation={'parents': [{'id': 'm-face'}]}))   # their own pictures, with the permission
    older = {'id': 'x', 'kind': 'sheet', 'element_kind': 'object', 'set': 'x', 'set_n': 1, 'server_checklist': VS.KEPT_THING_LINES}
    assert IC.lines_of(older) == VS.KEPT_THING_LINES + IC.FIXED   # a set of an older round: as before


def test_another_view_of_the_same_thing_is_not_a_fault():
    lines = request('FAN')['lines']
    same = next(l for l in lines if l['check'] == IC.SAME_THING)
    assert IC.SAME_THING == "the same thing as picture A, seen as this picture's view asks" and same['pictures'] == [2, 3] and 'same as picture 1' not in [l['check'] for l in lines]
    assert 'a different side, distance or framing is not a difference' in same['pass_when']
    one, two = IC.lines_of(set_picture(1, lines)), IC.lines_of(set_picture(2, lines))
    mine = next(l for l in two if l['check'] == IC.SAME_THING)
    assert IC.SAME_THING not in [l['check'] for l in one] and mine['pass_when'].endswith(': the ask of picture 2') and 'pictures' not in mine


@pytest.mark.parametrize('name', [IC.SAME_THING, 'same as picture 1'])   # the second: a set whose lines were stored before this change
def test_picture_a_is_sent_beside_a_later_picture_under_either_name_of_the_line(monkeypatch, name):
    s = F.session('2')
    s['references']['s-street-1-2']['server_checklist'] = [{'check': name, 'weight': 'must', 'pass_when': 'x', 'pictures': [2, 3]}]
    store = store_of(s)
    for r in ('s-street-1', 's-street-1-2'):
        store.files[s['references'][r]['key']] = b'png-' + r.encode()
    sent = []
    monkeypatch.setattr(IC.keys, 'pool', lambda *a: ['k'])
    monkeypatch.setattr(IC, 'build', lambda png, parents, ls, prompt: sent.append(parents) or {})
    monkeypatch.setattr(IC.keys, 'gemini', lambda *a, **k: ({'body': {'lines': []}}, 0))
    ref = s['references']['s-street-1-2']
    IC._model_check(store, s, ref, {'key': ref['key'], 'width': 2752, 'height': 1536}, None)
    assert sent == [[('picture 1 of this set', b'png-s-street-1')]]


# ---------- N: the notes ----------

class Lock:
    def execute(self, *a, **k):
        return self


def came_back(monkeypatch, names):
    s = F.session('making')
    store = store_of(s)
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW.jobs, 'finish', lambda *a, **k: None)
    monkeypatch.setattr(VW.jobs, 'record_file', lambda *a, **k: None)
    job = {'id': 'job-s-street-1', 'run_id': RUN['id'], 'request': {'reference': {'id': 's-street-1'}, 'views': ['a', 'b', 'c'], **({'view_names': ['A', 'B', 'C']} if names else {})}}
    result = {'key': 'k1', 'sha256': 'a', 'bytes': 9, 'width': 2752, 'height': 1536, 'notes': 'First. Second. Third.', 'notes_each': ['First.', 'Second.', 'Third.'], 'sources': [],
              'extra': [{'key': f'k{n}', 'sha256': str(n), 'bytes': 9, 'width': 2752, 'height': 1536} for n in (2, 3)]}
    VW.finalize_image(Lock(), job, 'retained', result, None, {'provider': 'gemini', 'pictures': 3}, None)
    return saved(store)['references']


def test_each_picture_of_a_v2_set_keeps_its_own_notes_and_an_older_set_the_whole(monkeypatch):
    refs = came_back(monkeypatch, names=True)
    assert [refs[r]['notes'] for r in ('s-street-1', 's-street-1-2', 's-street-1-3')] == ['First.', 'Second.', 'Third.']
    refs = came_back(monkeypatch, names=False)   # an older round's request names no views
    assert [refs[r]['notes'] for r in ('s-street-1', 's-street-1-2', 's-street-1-3')] == ['First. Second. Third.'] * 3


def test_the_worker_holds_the_notes_of_each_turn_and_joins_them_as_before(monkeypatch):
    class R:
        status_code = 200

        def __init__(self, parts):
            self.parts = parts

        def json(self):
            return {'candidates': [{'content': {'parts': self.parts}}], 'usageMetadata': {}}
    pic = {'inlineData': {'mimeType': 'image/png', 'data': 'x'}}
    turns = [R([{'text': 'The first.'}, pic]), R([pic]), R([{'text': 'I cannot.'}])]
    monkeypatch.setattr(VW, '_gemini_post', lambda model, payload, tries: (turns.pop(0), 0))
    out = VW._gemini_set({'model': 'm', 'prompt': 'p', 'views': ['a', 'b', 'c'], 'size': {'aspect': '16:9', 'tier': '2K'}}, [], []).json()
    assert out['notes_each'] == ['The first.', 'picture 3 (c) did not come back: I cannot.'] and out['notes'] == 'The first. picture 3 (c) did not come back: I cannot.' and len(out['data']) == 2


def test_set_facts_gives_each_pictures_notes_the_sets_notes_once_what_the_model_chose_and_the_footage_beside():
    s = F.session('2')
    row = s['round']['elements']['T_LAY']
    f = RS.set_facts(s, F.plan(), 'T_LAY', row)
    assert set(f) == {'pictures', 'inputs', 'from', 'notes', 'sources', 'partial', 'rec', 'makes', 'makes_left', 'asked', 'history', 'changed', 'fail', 'model', 'footage', 'searched'}
    assert f['notes'].startswith('(1) One method') and f['notes'].count('(1) One method') == 1 and [p['notes'] for p in f['pictures']] == ['', '', '']   # stored before the notes were split: said once, of the set
    assert f['model'] is None and f['footage'] == []
    for n, rid in enumerate(('s-t_lay-1', 's-t_lay-1-2', 's-t_lay-1-3'), 1):
        s['references'][rid]['notes'] = f'Note {n}.'
    row['set_look'].update(chose='The brick pressed into the bed.', aside='A dry bed.')
    s['references']['f-lay'] = frame('f-lay', 'the action at its key moment', eid='T_LAY', kind='technique')
    s['found']['T_LAY']['kept'] = ['f-lay']
    f = RS.set_facts(s, F.plan(), 'T_LAY', row)
    assert f['notes'] == 'Note 1. Note 2. Note 3.' and [p['notes'] for p in f['pictures']] == ['Note 1.', 'Note 2.', 'Note 3.']
    assert f['model'] == {'chose': 'The brick pressed into the bed.', 'aside': 'A dry bed.'} and f['footage'] == [{'ref': 'f-lay', 'view': 'the action at its key moment'}]
    row['parts']['inputs'] = [{'ref': 'f-lay', 'role': 'footage', 'view': 'the action at its key moment'}]
    assert RS.set_facts(s, F.plan(), 'T_LAY', row)['footage'] == []   # an input is not said twice


def test_the_look_says_what_the_model_chose_and_set_aside_where_the_pictures_carry_notes():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)   # every picture carries notes
    sent = looks(store, only=['STREET'])[0]
    for change in ({'chose': None, 'aside': None}, {'chose': 'x', 'aside': ' '}, {'chose': 'x' * 301, 'aside': 'y'}):
        out = RS.round_looks(store, USER, RUN, [], [{**sent, **change}], 'helper')
        assert out['refused'] == {'STREET': RS.LOOK_MODEL.format(eid='STREET', max=300)} and 'set_look' not in saved(store)['round']['elements']['STREET']
    out = RS.round_looks(store, USER, RUN, [], [{**sent, 'chose': ' A sandy street,\n wide. ', 'aside': 'A paved one.'}], 'helper')
    s = saved(store)
    row = s['round']['elements']['STREET']
    assert out['recorded'] == ['STREET'] and (row['set_look']['chose'], row['set_look']['aside']) == ('A sandy street, wide.', 'A paved one.')
    assert RS.set_facts(s, F.plan(), 'STREET', row)['model'] == {'chose': 'A sandy street, wide.', 'aside': 'A paved one.'}
    for r in s['references'].values():   # no notes: the two lines are optional
        r.pop('notes', None)
    put(store, s)
    plain = {k: v for k, v in looks(store, only=['MASON'])[0].items() if k not in ('chose', 'aside')}
    assert RS.round_looks(store, USER, RUN, [], [plain], 'helper')['recorded'] == ['MASON'] and 'chose' not in saved(store)['round']['elements']['MASON']['set_look']
    assert RS.set_facts(saved(store), F.plan(), 'MASON', saved(store)['round']['elements']['MASON'])['model'] is None
    said = ' '.join(RS.LOOK_HOW['judge']) + RS.LOOK_HOW['send'] + str(RS.LOOK_HOW['file'])
    assert '`chose`' in said and '`aside`' in said and 'chose' in RS.LOOK_HOW['file']['sets'][0] and 'aside' in RS.LOOK_HOW['file']['sets'][0] and '`footage`' in said


def test_the_looker_gets_the_things_footage_pictures_that_were_not_inputs_and_nothing_of_a_stand_ins_footage_person():
    store, conn = film()
    post(store, conn)
    done(store, conn)
    back(store)
    s = shown(saved(store), frame('m-face', 'the face'))
    shown(s, frame('f-lay', 'the action at its key moment', eid='T_LAY', kind='technique'), eid='T_LAY')
    put(store, s)
    due = {x['element_id']: x for x in RS.looks_due(store, RUN, [])['sets']}
    assert set(due['T_LAY']) == {'element_id', 'name', 'set', 'facts', 'request', 'inputs', 'pictures', 'notes', 'footage'}
    assert due['T_LAY']['footage'] == [{'ref': 'f-lay', 'view': 'the action at its key moment', 'key': s['references']['f-lay']['key']}] and due['STREET']['footage'] == []
    assert due['MASON']['footage'] == []                                 # no permission is recorded: a stand-in, never compared with the person in the footage
    s['likeness'] = {'MASON': {'quote': 'he agreed', 'by': 'u1', 'at': F.NOW}}
    put(store, s)
    due = {x['element_id']: x for x in RS.looks_due(store, RUN, [])['sets']}
    assert [x['ref'] for x in due['MASON']['footage']] == ['m-face']     # the set was made from words before the permission: his pictures are beside it


# ---------- F: a first set that cannot be made is replaced ----------

def refusing(monkeypatch, bad, code='VISUALS_REFUSED'):
    real = VS.generate_image

    def fake(conn, store, user, run, outputs, body, **kw):
        if body['element_id'] in bad:
            raise Problem(409, code, f"{body['element_id']}: its request cannot be written.")
        return real(conn, store, user, run, outputs, body, **kw)
    monkeypatch.setattr(VS, 'generate_image', fake)


def test_a_first_set_refused_before_the_call_is_replaced_by_the_next_waiting_one(monkeypatch):
    refusing(monkeypatch, {'STREET'})
    store, conn = film()
    post(store, conn)
    out = done(store, conn)
    assert out['queued'] == ['MASON', 'T_LAY', 'BRICK'] and out['rest'] == ['TILE'] and out['errors'] == {'STREET': 'STREET: its request cannot be written.'} and out['pass'] == 'making'
    s = saved(store)
    street = s['round']['elements']['STREET']
    assert street['error'] and not street.get('set') and RS.set_facts(s, F.plan(), 'STREET', street)['fail'] == {'cause': 'other', 'model': None, 'text': 'STREET: its request cannot be written.'}
    assert s['round']['rest'] == ['TILE'] and s['round']['elements']['BRICK']['set']


def test_the_replacements_stop_at_three_ordered_or_when_nothing_waits(monkeypatch):
    refusing(monkeypatch, {'STREET', 'T_LAY', 'BRICK'})
    store, conn = film()
    post(store, conn)
    out = done(store, conn)
    assert out['queued'] == ['MASON', 'TILE'] and out['rest'] == [] and sorted(out['errors']) == ['BRICK', 'STREET', 'T_LAY']


def test_with_nothing_refused_the_waiting_sets_stay_waiting():
    store, conn = film()
    post(store, conn)
    out = done(store, conn)
    assert out['queued'] == ['MASON', 'STREET', 'T_LAY'] and out['rest'] == ['BRICK', 'TILE']


# ---------- L: a person the footage shows ----------

def test_the_look_at_a_footage_frame_records_face_and_child_as_given():
    row ={'trial': 't1', 'view': 'the face', 'verdict': 'pass', 'seen': 'His face, sharp.', 'keep': False, 'closest': False}
    assert ref_find.look_extra({'face': True, 'child': False}, 'person') == {'face': True, 'child': False}
    assert ref_find.look_extra({'face': 'yes', 'child': 1}, 'person') == {} and ref_find.look_extra(row, 'person') == {}       # said by the looker as true or false, never guessed
    assert ref_find.look_extra({'face': False, 'child': True}, 'object') == {'face': False}                                  # `child` is a person's


def test_footage_person_says_whether_to_ask_and_gives_the_best_face_first():
    s = mason(permission=False)
    out = RS.footage_person(s, F.plan(), 'MASON')
    assert out == {'faces': ['m-face', 'm-weak'], 'child': False, 'state': 'ask'}   # pass before weak; the frame that shows no face is not among them
    s['references']['m-weak']['look']['child'] = True
    assert RS.footage_person(s, F.plan(), 'MASON')['child'] is True
    s['likeness'] = {'MASON': {'quote': 'he agreed', 'by': 'u1', 'at': F.NOW}}
    assert RS.footage_person(s, F.plan(), 'MASON')['state'] == 'permitted'
    s.pop('likeness')
    s['stand_in'] = {'MASON': {'quote': 'no', 'by': 'u1', 'at': F.NOW}}
    assert RS.footage_person(s, F.plan(), 'MASON')['state'] == 'stand_in'
    assert RS.footage_person(ready(), F.plan(), 'MASON') == {'faces': [], 'child': False, 'state': None}      # no face frame
    assert RS.footage_person(s, F.plan(), 'TROWEL') == {'faces': [], 'child': False, 'state': None}           # not a person
    assert ', '.join(inspect.signature(RS.footage_person).parameters) == 'session, plan, eid'


def test_a_permitted_person_is_made_from_their_own_footage_pictures_the_best_face_first():
    s = mason()
    r = request('MASON', session=s)
    assert r['inputs'] == [{'ref': 'm-face', 'role': 'footage', 'view': 'full length, front'}, {'ref': 'm-weak', 'role': 'footage', 'view': 'the face'},
                           {'ref': 'm-hand', 'role': 'footage', 'view': 'right hand and forearm'}]
    assert r['parts']['source'] == 'footage' and r['search'] is False and VS.LIKENESS_PHOTO_LINE not in r['prompt']
    assert "Images 1 to 3 are the film's own pictures of this person, used with their permission: take the face, the build, the skin and the hair from them, nothing else;" in r['prompt']
    names = [l['check'] for l in r['lines']]
    assert 'the face matches the footage' in names and 'matches the footage picture' not in names and 'a real face' not in names
    assert VS.likeness_photo(s, 'MASON') == 'm-face'
    s['references']['m-weak']['status'] = 'candidate'     # only an approved picture is sent
    one = shown(ready(), frame('m-face', 'the face'))
    one['likeness'] = dict(s['likeness'])
    assert [i['ref'] for i in request('MASON', session=s)['inputs']] == ['m-face', 'm-hand'] and "Image 1 is the film's own picture of this person" in request('MASON', session=one)['prompt']
    s['references']['own-1'] = {'id': 'own-1', 'kind': 'supplied', 'element_id': 'MASON', 'status': 'approved', 'created_at': F.NOW}
    own = request('MASON', session=s)
    assert own['inputs'] == [{'ref': 'own-1', 'role': 'photo', 'view': ''}] and VS.LIKENESS_PHOTO_LINE in own['prompt'] and 'the face matches the footage' not in [l['check'] for l in own['lines']]
    none = request('MASON', session=mason(permission=False))
    assert none['inputs'] == [] and none['parts']['source'] == 'words' and 'own pictures' not in none['prompt']


def test_the_permission_and_the_stand_in_are_recorded_for_a_person_the_footage_shows():
    store, conn = store_of(mason('1', permission=False)), FakeConn([])
    out = VS.likeness(store, USER, RUN, [], 'MASON', 'He would rather not.', conn=conn, stand_in=True)
    s = saved(store)
    assert out['likeness'] is False and s['stand_in']['MASON']['quote'] == 'He would rather not.' and RS.footage_person(s, F.plan(), 'MASON')['state'] == 'stand_in'
    out = VS.likeness(store, USER, RUN, [], 'MASON', 'I have his permission.', conn=conn)
    s = saved(store)
    assert out['likeness'] is True and 'MASON' not in s.get('stand_in', {}) and s['likeness']['MASON']['quote'] == 'I have his permission.' and "film's own pictures" in out['next']
    assert RS.footage_person(s, F.plan(), 'MASON')['state'] == 'permitted'
    VS.likeness(store, USER, RUN, [], 'MASON', 'He changed his mind.', conn=conn, stand_in=True)
    s = saved(store)
    assert 'MASON' not in s['likeness'] and RS.footage_person(s, F.plan(), 'MASON')['state'] == 'stand_in'
    assert "operator's own words" in refused(lambda: VS.likeness(store, USER, RUN, [], 'MASON', ' ', conn=conn))
    plain = store_of(ready('1'))   # a person the footage does not show: a stand-in asked with no record changes nothing, as before
    VS.likeness(plain, USER, RUN, [], 'MASON', 'no', conn=conn, stand_in=True)
    assert 'stand_in' not in saved(plain)


# ---------- the limit, with no amount ----------

def test_the_limit_is_said_with_no_amount_in_a_v2_round():
    assert RS.LIMIT_PLAIN == 'These cannot be made now: the film has reached the limit its owner set. Ask the owner to raise it.'
    store, conn = at_two()
    s = saved(store)
    s['cap_inr'] = 50
    put(store, s)
    assert refused(lambda: RS.round_rest(conn, store, USER, RUN, [], 'now')) == RS.LIMIT_PLAIN
    assert saved(store)['round']['rest'] == ['BRICK', 'TILE'] and len(conn.inserted) == 3
    s = saved(store)
    s['cap_inr'] = 1
    put(store, s)
    out = judge(store, conn, {'T_LAY': {'verdict': 'no'}})
    assert out['held'] == {'T_LAY': RS.LIMIT_PLAIN}
    assert refused(lambda: VS.set_make(conn, store, USER, RUN, [], 'BRICK', 'make it')).endswith(RS.LIMIT_PLAIN)


def test_a_set_refused_for_the_limit_says_so_plainly_on_its_row():
    store, conn = film(fresh(cap_inr=15))   # no room for a set of three
    post(store, conn)
    out = done(store, conn, STREET={'verdict': 'ignore'}, TILE={'verdict': 'ignore'})
    assert out['queued'] == [] and out['errors'] == {e: RS.LIMIT_PLAIN for e in ('BRICK', 'MASON', 'T_LAY')}
    s = saved(store)
    row = s['round']['elements']['T_LAY']
    assert row['error'] == RS.LIMIT_PLAIN and RS.set_facts(s, F.plan(), 'T_LAY', row)['fail'] == {'cause': 'limit', 'model': None, 'text': RS.LIMIT_PLAIN}
    assert VS._set_state(s, F.plan(), VS._round_pass(s, s['round']), 'T_LAY', row, (0.0, 4000.0, 35.0))['settled'] == 'spend cap raised'
