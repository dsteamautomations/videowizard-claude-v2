"""SK, 23 Nov 2026 (no-footage release 3): the operator's real images (case 2). The assistant plans each picture into a still shot
(`supplied`) or lists it not used; the same picture may show twice, with a warning when the two showings are next to each other or framed
alike; a shot filled with the operator's file is done at step 7; a still that waits for the operator's picture is said so; the operator's
picture of a thing stands in for a footage picture in its set, its clean set and its sizes; a large photo is made smaller, not refused;
the AI list names the operator's picture "supplied" on every kind of shot. A film with footage is unchanged."""
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app import chat_flow as CF, core, pictures as P, ref_sets, takes as T, visual_contract as VC, visuals_stage as VS
from app.stage3 import delivery as D

SERVER = Path(__file__).resolve().parents[1]
VISUALS = next(s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
NONE = {'film': {'footage': {'value': 'none'}}}


def shot(sid, start, supplied='', framing='wide', vt='image'):
    return {'id': sid, 'start_frame': start, 'end_frame': start + 50, 'visual_type': vt, 'framing': framing, **({'supplied': supplied} if supplied else {})}


def plan(*shots, unused=()):
    return {'gaps': [{'gap_id': 'g1', 'scenes': [{'id': 'sc1', 'shots': list(shots)}]}], **({'images_not_used': list(unused)} if unused else {})}


# ---- the plan (F15, F18)

def test_a_shot_may_name_the_operators_picture_and_a_plan_the_pictures_not_used():
    assert VC.Shot.model_fields['supplied'].default == '' and 'images_not_used' in VC.Plan.model_fields
    assert 'supplied_repeat' in VC.WARNING_PLAIN


def test_the_same_picture_twice_is_allowed_and_warned_when_next_to_each_other_or_framed_alike():
    kinds = lambda p: [(w['shot_id'], w['kind']) for w in VC.supplied_warnings(p)]
    assert kinds(plan(shot('s1', 0, 'in/a.jpg'), shot('s2', 50, 'in/a.jpg', 'close'))) == [('s2', 'supplied_repeat')]   # next to each other
    assert kinds(plan(shot('s1', 0, 'in/a.jpg'), shot('s2', 50), shot('s3', 100, 'in/A.jpg', 'Wide '))) == [('s3', 'supplied_repeat')]   # the same framing
    assert kinds(plan(shot('s1', 0, 'in/a.jpg'), shot('s2', 50), shot('s3', 100, 'in/a.jpg', 'close'))) == []
    assert kinds(plan(shot('s1', 0, 'in/a.jpg'), shot('s2', 50, 'in/b.jpg'))) == [] and kinds(plan(shot('s1', 0), shot('s2', 50))) == []


def test_the_operators_picture_fills_a_still_shot_only():
    with pytest.raises(ValueError) as e:
        VC.supplied_warnings(plan(shot('s1', 0, 'in/a.jpg', vt='video')))
    assert 's1' in str(e.value) and 'still' in str(e.value)


def test_every_picture_the_operator_gave_has_a_place_or_a_reason():
    p = plan(shot('s1', 0, 'in/a.jpg'), unused=[{'file': 'in/b.jpg', 'reason': 'Shows the old factory.'}])
    assert VS.supplied_plan(NONE, p, ['in/a.jpg', 'in/B.jpg']) == []
    left = VS.supplied_plan(NONE, p, ['in/a.jpg', 'in/b.jpg', 'in/c.png'])
    assert len(left) == 1 and 'in/c.png' in left[0] and '`images_not_used`' in left[0]
    gone = VS.supplied_plan(NONE, p, ['in/b.jpg'])
    assert len(gone) == 1 and 's1' in gone[0] and 'in/a.jpg' in gone[0]
    assert VS.supplied_plan(NONE, p, None) == []   # an older tool sends no list: nothing is checked
    assert VS.supplied_plan({}, plan(shot('s1', 0)), ['in/c.png']) == []   # a film with footage: as before


def test_the_operator_sees_the_place_of_each_picture_and_those_not_used():
    session = {'source': {'fps': 25}, 'choice_selections': {}}
    rows, _ = CF._gap_rows(session, plan(shot('s1', 0, 'in/a.jpg') | {'purpose': 'p', 'narration': 'n'}, shot('s2', 50) | {'purpose': 'p', 'narration': 'n'})['gaps'][0])
    assert 'your picture in/a.jpg' in rows[0][2] and 'your picture' not in rows[1][2]
    world = CF._world_rows({'foundation': {}, 'images_not_used': [{'file': 'in/b.jpg', 'reason': 'Shows the old factory.'}]})
    assert ['Your picture, not used', 'in/b.jpg: Shows the old factory.'] in world


# ---- step 6 and step 7 (N4, N1)

def test_a_still_that_waits_for_the_operators_picture_is_said_so():
    items = [{'kind': 'still', 'id': 's1', 'state': P.STATE['none'], 'supplied': 'in/a.jpg'}, {'kind': 'still', 'id': 's2', 'state': P.STATE['none']}]
    assert 's1' not in P.stills_due(items) and 's2' in P.stills_due(items)
    due = P.supplied_due(items)
    assert 's1' in due and 'in/a.jpg' in due and '`vw visuals asset' in due and P.supplied_due(items[1:]) == ''
    assert P.supplied_due([{**items[0], 'state': P.STATE['answered']}]) == ''


def test_an_ai_video_shot_filled_with_the_operators_file_is_done():
    assert T._state({'assets': {'s1': {'kind': 'movie'}}}, {}, {'id': 's1'}, [], None) == ('answered', None, False)
    assert T._state({'selections': {'s1': {}}}, {}, {'id': 's1'}, [], None) == ('answered', None, False)   # as before


# ---- the operator's picture as a reference (N2, F16, F17, F18)

OWN = {'id': 'o1', 'kind': 'supplied', 'status': 'approved', 'element_id': 'e1', 'name': 'own-e1', 'key': 'k'}


def test_the_operators_picture_goes_into_the_set_of_a_thing_with_no_footage_picture(monkeypatch):
    from app import drawings, ref_find
    monkeypatch.setattr(drawings, 'approved_sheets', lambda session, eid: [])
    session = {'references': {'o1': OWN}}
    monkeypatch.setattr(ref_find, 'frames_of', lambda s, eid: [])
    assert ref_sets.inputs_of(session, {'id': 'e1', 'kind': 'object'}) == ([{'ref': 'o1', 'role': 'footage', 'view': 'as given'}], set())
    session['references']['f1'] = {'id': 'f1', 'status': 'approved'}
    monkeypatch.setattr(ref_find, 'frames_of', lambda s, eid: [{'ref': 'f1', 'view': 'front', 'weak': False}])
    assert [i['ref'] for i in ref_sets.inputs_of(session, {'id': 'e1', 'kind': 'object'})[0]] == ['f1']   # a thing with a footage picture: as before


def test_a_clean_set_may_be_made_from_the_operators_picture():
    assert ref_sets.clean_from({'references': {'o1': OWN}}, 'e1', []) and ref_sets.clean_from({'references': {}}, 'e1', ['f1'])
    assert not ref_sets.clean_from({'references': {}}, 'e1', []) and not ref_sets.clean_from({'references': {'o1': {**OWN, 'status': 'candidate'}}}, 'e1', [])


def test_sizes_may_be_measured_from_the_operators_picture(monkeypatch):
    session = {'references': {'o1': OWN, 'w1': {**OWN, 'id': 'w1', 'kind': 'web'}}}
    monkeypatch.setattr(VS, 'session_of', lambda *a, **k: session)
    monkeypatch.setattr(VS.keys, 'pool', lambda *a, **k: None)
    with pytest.raises(ValueError) as e:
        VS.measure({'k': b'png'}, {'id': 'u'}, {}, [], ['o1'], 'How wide is the press?')
    assert 'No Gemini key' in str(e.value)   # it passed the gate of the pictures
    with pytest.raises(ValueError) as e:
        VS.measure(None, {'id': 'u'}, {}, [], ['w1'], 'How wide is the press?')
    assert 'w1' in str(e.value) and 'web' in str(e.value)


def test_two_shots_may_show_the_operators_own_picture():
    assert VS.repeat_allowed(OWN) and not VS.repeat_allowed({**OWN, 'kind': 'keyframe'}) and not VS.repeat_allowed({**OWN, 'kind': 'frame'})


# ---- a large photo (V7)

def test_a_large_photo_is_made_smaller_on_the_way_in():
    raw = BytesIO()
    Image.new('L', (7000, 4000)).save(raw, format='PNG')   # 28 megapixels
    png, (w, h) = VS.image_bytes(raw.getvalue())
    assert w * h <= 24_000_000 and abs(w / h - 7000 / 4000) < 0.01 and Image.open(BytesIO(png)).size == (w, h)
    small = BytesIO()
    Image.new('RGB', (640, 360)).save(small, format='JPEG')
    assert VS.image_bytes(small.getvalue())[1] == (640, 360)


def test_a_file_that_is_not_a_picture_the_server_reads_is_refused_in_plain_words():
    gif = BytesIO()
    Image.new('P', (10, 10)).save(gif, format='GIF')
    with pytest.raises(ValueError) as e:
        VS.image_bytes(gif.getvalue())
    assert 'PNG, JPEG or WebP' in str(e.value)


# ---- the package (B4)

def test_the_ai_list_names_the_operators_picture_supplied_on_every_kind_of_shot():
    ev = lambda **media: {'kind': 'fill', 'source': 'reference', 'shot_id': 's1', 'media': media}
    own, none = {'s1': {'reference_kind': 'supplied'}}, {'s1': {}}
    assert D.ai_kind(ev(kind='still', graphic=True), own) == 'supplied' and D.ai_kind(ev(kind='sequence'), own) == 'supplied' and D.ai_kind(ev(kind='still'), own) == 'supplied'
    assert D.ai_kind(ev(kind='still', graphic=True), none) == 'graphic' and D.ai_kind(ev(kind='still'), none) == 'AI still' and D.ai_kind(ev(kind='movie'), none) == 'AI video'   # as before
    assert D.ai_kind(ev(kind='still'), {'s1': {'reference_kind': 'frame'}}) is None   # a footage frame: as before
    assert D.ai_kind({'kind': 'fill', 'source': 'asset', 'shot_id': 's1', 'media': {'kind': 'still', 'graphic': True}}, {'s1': {'supplied': True}}) == 'supplied'


# ---- the instructions (F15, F19)

def test_the_instructions_of_such_a_film_plan_the_operators_pictures():
    none, own = json.dumps(core.for_footage(VISUALS, 'none')), json.dumps(core.for_footage(VISUALS, 'own'))
    assert 'never plan one' in own and 'never plan one' not in none
    assert '`supplied`' in none and '`images_not_used`' in none and 'SVG' in none
    assert '`images_not_used`' not in own
