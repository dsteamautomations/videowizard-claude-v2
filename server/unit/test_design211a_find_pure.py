"""design/211 part A (section 6.1): the digest of the footage, trial frames, the look record and the search record, the frames a round
may show, and the operator's two answers to a footage picture. Without a database: the shared fixture, a store in memory, ffmpeg faked."""
import copy
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
import check_shared_change as H   # noqa: E402
import d211_fixture as F   # noqa: E402
from app import ref_find as RF, ref_sets, visuals_stage as V   # noqa: E402

RUN, USER = F.RUN, {'id': 'u1', 'name': 'SK'}
CLIPS = [{'id': 'C001', 'name': 'C001.mp4', 'duration_s': 42.0, 'sha256': 'c' * 64}, {'id': 'C002', 'name': 'C002.mp4', 'duration_s': 20.0, 'sha256': 'c' * 64},
         {'id': 'C003', 'name': 'C003.mp4', 'duration_s': 10.0, 'sha256': 'c' * 64}]
MEDIA = {'stage': 'media', 'unit': None, 'summary': {'clips': CLIPS}, 'files': []}
TOLD = {}   # the plan the faked `current_plan` answers


def sub(pid, a, b, hero, action, props=(), defects=()):
    return {'sub_clip_id': pid, 'max_usable_window': {'in_s': a, 'out_s': b}, 'hero_frame_s': hero, 'usability_grade': 'A', 'shot_role': 'PROCESS_ACTION_B_ROLL',
            'camera_and_optics': {'native_shot_size': 'MS', 'camera_angle': 'Eye_Level'}, 'visual_action_observed': action, 'visual_action_uncertainty': 'the tool is partly hidden',
            'continuity_and_story': {'world_landmarks_and_props': list(props)}, 'people_and_speaker_analysis': {'people_count': 1},
            'technical_qc_and_remediation': {'defects_detected': list(defects)}}


def analysed(store, clip, subs, excluded=False):
    key = f"{RUN['id']}/analysis/{clip}.evidence.json"
    log = {'clip_overview': f'What {clip} shows.', 'lighting_and_weather': 'late morning sun', 'sub_clips': subs,
           'entities': [{'name': 'mason_trowel', 'kind': 'tool', 'first_seen_s': 0.0, 'last_seen_s': 40.0, 'description': 'a trowel', 'basis': 'seen', 'uncertainty': ''}]}
    store.put(key, json.dumps({'contract_version': 'clip-log-v1', 'log': log}).encode('utf-8'))
    return {'stage': 'analysis', 'unit': clip, 'summary': {'excluded': True} if excluded else {}, 'files': [{'name': f'{clip}.evidence.json', 'key': key}]}


def film(state='1', plan=None, trials=True):
    """The fixture's film in a store: its session, its trial frames, two analysed clips and one that is not."""
    store = H.Store()
    s = F.session(state)
    s['clip_safe_zoom'] = {'C001': 1.0, 'C002': 1.0}   # written by `prepare`: the analysed clips
    V.save_json(store, V.key(RUN, 'session.json'), s)
    if trials:
        V.save_json(store, V.key(RUN, 'trials.json'), F.trials())
    for c in CLIPS:
        store.put(f"{RUN['id']}/media/{c['name']}", b'video')
    outputs = [MEDIA, analysed(store, 'C001', [sub('C001-a', 0.0, 18.0, 6.4, 'the mason spreads mortar', ['trowel'], [{'defect': 'focus_hunt', 'in_tc': '00:00:02:00', 'out_tc': '00:00:03:00', 'description': 'soft'}]),
                                                sub('C001-b', 18.0, 42.0, 30.2, 'the trowel lies on the wall')]),
               analysed(store, 'C002', [])]
    TOLD['plan'] = plan or F.plan()
    return store, outputs


def sess(store):
    return V.load_json(store, V.key(RUN, 'session.json'))


def trials_of(store):
    return V.load_json(store, V.key(RUN, 'trials.json'))['trials']


def take(store, outputs, *rows):
    frames = [{'element_id': e, 'clip': c, 'at_s': at} for e, c, at in rows]
    return RF.trial_record(store, USER, RUN, outputs, frames, RF.cut_trials(store, RUN, outputs, frames))


def look(store, outputs, *things, by='helper'):
    return RF.look_record(H.Conn(), store, USER, RUN, outputs, list(things), by)


def a_look(trial, verdict='pass', view='side', seen='The whole thing, sharp.', **more):
    return {'trial': trial, 'view': view, 'verdict': verdict, 'seen': seen, **more}


@pytest.fixture(autouse=True)
def faked(monkeypatch):
    """ffmpeg writes a 1920x1080 picture (it fails at second 13); the plan is the fixture's; part B's two functions answer from the plan."""
    def run(cmd, **kw):
        if cmd[cmd.index('-ss') + 1].startswith('13.'):
            raise subprocess.CalledProcessError(1, cmd)
        Image.new('RGB', (1920, 1080), 'grey').save(cmd[-1])
    monkeypatch.setattr(subprocess, 'run', run)
    monkeypatch.setattr(V, 'current_plan', lambda store, session: TOLD['plan'])
    monkeypatch.setattr(ref_sets, 'view_names', lambda element: list(element.get('required_views') or []) + ['whole'])
    monkeypatch.setattr(ref_sets, 'thing_facts', lambda plan, session, element: {'id': element['id'], 'name': element['name'], 'views': list(element.get('required_views') or [])})


# ---------- the digest (3.1) ----------

def test_the_digest_gives_each_part_of_a_clip_and_names_what_was_not_searched():
    store, outputs = film()
    outputs.append(analysed(store, 'C004', [sub('C004-a', 0, 5, 1, 'left out by the operator')], excluded=True))
    d = RF.digest(store, RUN, outputs)
    assert d['contract'] == RF.DIGEST_CONTRACT == 'vw2-refs-digest-v1' and len(d['stamp']) == 64 and d['built_at']
    one, two = d['clips']
    assert (one['clip'], one['name'], one['duration_s'], one['overview'], one['light']) == ('C001', 'C001.mp4', 42.0, 'What C001 shows.', 'late morning sun')
    assert one['entities'] == [{'name': 'mason_trowel', 'kind': 'tool', 'first_seen_s': 0.0, 'last_seen_s': 40.0, 'description': 'a trowel', 'uncertainty': ''}]
    assert one['parts'][0] == {'id': 'C001-a', 'in_s': 0.0, 'out_s': 18.0, 'hero_s': 6.4, 'grade': 'A', 'role': 'PROCESS_ACTION_B_ROLL', 'size': 'MS', 'angle': 'Eye_Level',
                               'action': 'the mason spreads mortar', 'uncertain': 'the tool is partly hidden', 'props': ['trowel'], 'people': 1,
                               'defects': [{'defect': 'focus_hunt', 'in_tc': '00:00:02:00', 'out_tc': '00:00:03:00', 'description': 'soft'}]}
    assert [p['id'] for p in one['parts']] == ['C001-a', 'C001-b']
    assert two['clip'] == 'C002' and two['parts'] == []                                    # a clip without sub-clips
    assert 'C004' not in json.dumps(d)                                                      # the operator's exclusion: neither searched nor named
    assert d['not_searched'] == [{'clip': 'C003', 'name': 'C003.mp4', 'reason': 'no analysis'}]
    assert V.load_json(store, V.key(RUN, 'digest.json'))['stamp'] == d['stamp']


def test_the_same_clips_give_the_same_stamp_and_no_rebuild_and_a_new_clip_rebuilds():
    store, outputs = film()
    first = RF.digest(store, RUN, outputs)
    store.put(outputs[1]['files'][0]['key'], b'not read again')
    again = RF.digest(store, RUN, outputs)
    assert again == first
    outputs.append(analysed(store, 'C003', [sub('C003-a', 0, 9, 4, 'a yard')]))
    analysed(store, 'C001', [sub('C001-a', 0, 18, 6.4, 'the mason spreads mortar')])
    new = RF.digest(store, RUN, outputs)
    assert new['stamp'] != first['stamp'] and [c['clip'] for c in new['clips']] == ['C001', 'C002', 'C003'] and new['not_searched'] == []


def test_the_digest_answer_carries_the_things_the_rule_the_limits_and_what_next():
    store, outputs = film()
    s = sess(store)
    s['found'] = {}
    V.save_json(store, V.key(RUN, 'session.json'), s)
    out = RF.digest_answer(store, RUN, outputs)
    assert out['then'] == RF.FIND_START and out['rule'] == RF.FRAME_RULE
    assert out['limits'] == {'trials_per_thing': 8, 'kept_per_thing': 3, 'things_per_helper': 5, 'helpers': 6}
    assert [t['id'] for t in out['things']] == list(F.THINGS) and all(t['found'] is None for t in out['things'])   # no animal, no graphic
    assert [c['clip'] for c in out['digest']['clips']] == ['C001', 'C002']


def test_the_digest_answer_gives_each_things_result_so_a_run_taken_over_does_only_what_is_left():
    store, outputs = film()
    s = sess(store)
    for eid, rec in s['found'].items():
        rec['fingerprint'] = RF.fingerprint(next(e for e in F.plan()['elements'] if e['id'] == eid))
    s['found']['FAN']['fingerprint'] = 'the plan changed since'
    s['found'].pop('BRICK')
    V.save_json(store, V.key(RUN, 'session.json'), s)
    out = RF.digest_answer(store, RUN, outputs)
    found = {t['id']: t['found'] for t in out['things']}
    assert found == {'MASON': 'none', 'TROWEL': 'found', 'FAN': None, 'BRICK': None, 'STREET': 'none', 'T_LAY': 'none', 'TILE': 'found'} and out['then'] == RF.FIND_START
    s['found']['FAN']['fingerprint'] = RF.fingerprint(next(e for e in F.plan()['elements'] if e['id'] == 'FAN'))
    s['found']['BRICK'] = dict(s['found']['FAN'])
    s['found']['BRICK']['fingerprint'] = RF.fingerprint(next(e for e in F.plan()['elements'] if e['id'] == 'BRICK'))
    V.save_json(store, V.key(RUN, 'session.json'), s)
    assert RF.digest_answer(store, RUN, outputs)['then'] == RF.LOOK_ALL


def test_a_run_with_footage_and_no_digest_is_searched_by_words():
    store, outputs = film()
    out = RF.digest_answer(store, RUN, [MEDIA])   # media, no analysis
    assert out['then'] == RF.FIND_WORDS and out['digest']['clips'] == [] and len(out['digest']['not_searched']) == 3
    assert 'vw visuals elements' in RF.FIND_WORDS and 'by words only' in RF.FIND_WORDS
    assert not RF.footage(store, RUN, [MEDIA]) and RF.footage(store, RUN, outputs)


def test_a_digest_that_cannot_be_built_falls_back_to_the_words():
    store, outputs = film()
    store.put(outputs[1]['files'][0]['key'], b'{broken')
    assert RF.digest_answer(store, RUN, outputs)['then'] == RF.FIND_WORDS


def test_a_film_with_no_footage_skips_the_search():
    store, _ = film()
    s = sess(store)
    s['clip_safe_zoom'], s['found'] = {}, {}
    V.save_json(store, V.key(RUN, 'session.json'), s)
    assert RF.footage(store, RUN, []) is False
    assert RF.digest_answer(store, RUN, [])['then'] == RF.LOOK_ALL                 # nothing to search: the round comes next
    assert RF.round_frames(s, F.plan(), 'STREET', []) == []                        # no search record asked


# ---------- trial frames (3.2) ----------

def test_the_trial_id_is_the_same_for_the_same_moment():
    a = RF.trial_id('C001', 30.2)
    assert a == RF.trial_id('C001', 30.21) == RF.trial_id('C001', '30.2') and a != RF.trial_id('C001', 30.3) != RF.trial_id('C002', 30.3)
    assert a.startswith('t') and len(a) == 13 and int(a[1:], 16) >= 0


def test_a_trial_frame_is_small_is_recorded_and_is_not_a_reference():
    store, outputs = film(trials=False)
    before = sess(store)['references']
    out = take(store, outputs, ('STREET', 'C002', 4.0), ('STREET', 'C002', 4.04), ('BRICK', 'C002', 4.0), ('STREET', 'C001', 9.5))
    tid = RF.trial_id('C002', 4.0)
    assert out['then'] == RF.TRIAL_NEXT and out['failed'] == []
    assert [t['id'] for t in out['trials']] == [tid, RF.trial_id('C001', 9.5)]             # the same moment asked twice, and for two things: one frame
    assert out['trials'][0] == {'id': tid, 'clip': 'C002', 'at_s': 4.0, 'key': f"{RUN['id']}/visuals/trials/{tid}.jpg", 'elements': ['STREET', 'BRICK']}
    assert out['left'] == {'STREET': 6, 'BRICK': 7}                                        # not counted twice
    img = Image.open(BytesIO(store.get(out['trials'][0]['key'])))
    assert img.format == 'JPEG' and max(img.size) == 640
    row = trials_of(store)[tid]
    assert set(row) == {'id', 'clip', 'at_s', 'key', 'sha256', 'elements', 'looks', 'at', 'by'} and row['looks'] == {} and row['by'] == 'u1' and len(row['sha256']) == 64
    assert sess(store)['references'] == before                                             # never in the references
    assert take(store, outputs, ('STREET', 'C002', 5.0))['left'] == {'STREET': 5}


def test_a_moment_that_cannot_be_cut_is_named_and_the_others_go_on():
    store, outputs = film(trials=False)
    out = take(store, outputs, ('STREET', 'C001', 13.0), ('STREET', 'C001', 14.0))
    assert [f['at_s'] for f in out['failed']] == [13.0] and out['failed'][0]['clip'] == 'C001' and out['failed'][0]['reason']
    assert [t['at_s'] for t in out['trials']] == [14.0] and out['left'] == {'STREET': 7}


def test_trial_too_many_is_refused_and_nothing_is_cut():
    store, outputs = film(trials=False)
    frames = [{'element_id': 'STREET', 'clip': 'C001', 'at_s': float(i)} for i in range(9)]
    cut = RF.cut_trials(store, RUN, outputs, frames)
    assert cut == []
    with pytest.raises(ValueError) as exc:
        RF.trial_record(store, USER, RUN, outputs, frames, cut)
    assert str(exc.value) == RF.TRIAL_TOO_MANY.format(max=8, n=9) and not store.exists(V.key(RUN, 'trials.json'))


def test_trial_limit_stops_the_ninth_frame_of_a_thing():
    store, outputs = film(trials=False)
    assert take(store, outputs, *[('STREET', 'C001', float(i)) for i in range(8)])['left'] == {'STREET': 0}
    out = take(store, outputs, ('STREET', 'C001', 20.0), ('BRICK', 'C001', 20.0), ('STREET', 'C001', 3.0))
    assert out['failed'] == [{'clip': 'C001', 'at_s': 20.0, 'reason': RF.TRIAL_LIMIT.format(max=8, eid='STREET')}]
    assert [t['elements'] for t in out['trials']] == [['BRICK'], ['STREET']] and out['left'] == {'STREET': 0, 'BRICK': 7}   # a frame it already has is not a ninth


def test_trial_unknown_clip_names_a_clip_that_is_not_the_runs_and_a_time_outside_it():
    store, outputs = film(trials=False)
    out = take(store, outputs, ('STREET', 'C999', 1.0), ('STREET', 'C002', 20.0), ('STREET', 'C002', -1), ('STREET', 'C002', 19.9))
    assert [f['reason'] for f in out['failed']] == [RF.TRIAL_UNKNOWN_CLIP.format(clip='C999', at_s=1.0), RF.TRIAL_UNKNOWN_CLIP.format(clip='C002', at_s=20.0),
                                                   RF.TRIAL_UNKNOWN_CLIP.format(clip='C002', at_s=-1.0)]
    assert len(out['trials']) == 1
    with pytest.raises(ValueError, match='Unknown element DOOR'):
        take(store, outputs, ('DOOR', 'C002', 1.0))
    with pytest.raises(ValueError, match='DOG'):
        take(store, outputs, ('DOG', 'C002', 1.0))   # an animal has no reference


def test_a_changed_plan_drops_the_things_trial_frames_and_the_count_starts_again():
    store, outputs = film(trials=False)
    take(store, outputs, ('STREET', 'C001', 1.0), ('STREET', 'C001', 2.0), ('BRICK', 'C001', 1.0))
    plan = F.plan()
    next(e for e in plan['elements'] if e['id'] == 'STREET')['description'] = 'A paved street.'
    TOLD['plan'] = plan
    out = take(store, outputs, ('STREET', 'C001', 3.0))
    assert out['left'] == {'STREET': 7}
    rows = trials_of(store)
    assert rows[RF.trial_id('C001', 1.0)]['elements'] == ['BRICK'] and RF.trial_id('C001', 2.0) not in rows and rows[RF.trial_id('C001', 3.0)]['elements'] == ['STREET']


# ---------- the look record and the search record (3.3, 3.4) ----------

def searched(store, outputs, eid='STREET', times=(1.0, 2.0, 3.0), clip='C001'):
    take(store, outputs, *[(eid, clip, t) for t in times])
    return [RF.trial_id(clip, t) for t in times]


def test_the_server_decides_the_result_in_each_of_the_four_cases():
    store, outputs = film(trials=False)
    a, b, c = searched(store, outputs, 'STREET')
    d, = searched(store, outputs, 'BRICK', (5.0,))
    e, = searched(store, outputs, 'T_LAY', (6.0,))
    out = look(store, outputs,
               {'element': 'STREET', 'clips': ['C001'], 'note': 'One clip shows it.', 'looks': [a_look(a, 'weak', 'whole', keep=True), a_look(b, 'pass', 'from the other side', keep=True), a_look(c, 'fail')]},
               {'element': 'BRICK', 'clips': ['C001'], 'note': 'Only half covered.', 'looks': [a_look(d, 'weak', 'whole', keep=True)]},
               {'element': 'T_LAY', 'clips': ['C001', 'C002'], 'note': 'Never seen whole.', 'looks': [a_look(e, 'fail', closest=True)]},
               {'element': 'FAN', 'not_searched': 'The helper was stopped.'})
    assert out['recorded'] == ['STREET', 'BRICK', 'T_LAY', 'FAN'] and out['refused'] == {}
    assert out['results'] == {'STREET': 'found', 'BRICK': 'weak', 'T_LAY': 'none', 'FAN': 'not_searched'}
    s = sess(store)
    rec = s['found']['T_LAY']
    assert set(rec) == {'result', 'by', 'at', 'fingerprint', 'clips', 'note', 'kept', 'closest'}
    assert (rec['result'], rec['by'], rec['clips'], rec['note'], rec['kept'], rec['closest']) == ('none', 'helper', ['C001', 'C002'], 'Never seen whole.', [], e)
    assert rec['fingerprint'] == RF.fingerprint(next(x for x in F.plan()['elements'] if x['id'] == 'T_LAY'))
    assert s['found']['FAN']['result'] == 'not_searched' and s['found']['FAN']['note'] == 'The helper was stopped.' and s['found']['FAN']['kept'] == []
    assert out['kept']['STREET'] == s['found']['STREET']['kept'] and len(out['kept']['STREET']) == 2 and out['kept']['T_LAY'] == []


def test_a_kept_frame_is_a_reference_with_its_view_look_weak_and_trial_in_view_order():
    store, outputs = film(trials=False)
    plan = F.plan()
    next(e for e in plan['elements'] if e['id'] == 'STREET')['required_views'] = ['from the gate', 'from the far end']
    TOLD['plan'] = plan
    a, b, _ = searched(store, outputs, 'STREET')
    out = look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'note': 'n', 'by': 'x',
                                'looks': [a_look(a, 'weak', 'from the far end', 'Far, half in shade.', keep=True), a_look(b, 'pass', 'From the gate', 'Whole and sharp.', keep=True)]}, by='assistant')
    s = sess(store)
    first, second = out['kept']['STREET']
    r = s['references'][first]
    assert (r['kind'], r['element_id'], r['status'], r['view'], r['weak'], r['trial']) == ('frame', 'STREET', 'candidate', 'From the gate', False, b)   # view order, not the order given
    assert r['source'] == {'media_id': 'C001', 'source_sha256': 'c' * 64, 'requested_s': 2.0} and (r['width'], r['height']) == (1920, 1080)   # the full-size frame
    assert r['look'] == {'who': 'assistant', 'at': r['look']['at'], 'view': 'From the gate', 'verdict': 'pass', 'seen': 'Whole and sharp.', 'trial': b, 'ref': first}
    assert s['references'][second]['weak'] is True and s['references'][second]['view'] == 'from the far end'
    assert trials_of(store)[b]['looks']['STREET'] == r['look'] and s['found']['STREET']['by'] == 'assistant'
    assert RF.frames_of(s, 'STREET') == [{'ref': first, 'view': 'From the gate', 'verdict': 'pass', 'seen': 'Whole and sharp.', 'weak': False},
                                         {'ref': second, 'view': 'from the far end', 'verdict': 'weak', 'seen': 'Far, half in shade.', 'weak': True}]


def test_closest_is_stored_only_when_nothing_is_kept():
    store, outputs = film(trials=False)
    a, b, _ = searched(store, outputs, 'STREET')
    look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'looks': [a_look(a, 'pass', 'whole', keep=True), a_look(b, 'weak', closest=True)]})
    assert sess(store)['found']['STREET']['closest'] is None
    c, = searched(store, outputs, 'BRICK', (9.0,))
    look(store, outputs, {'element': 'BRICK', 'clips': ['C001'], 'looks': [a_look(c, 'weak', closest=True)]})
    assert sess(store)['found']['BRICK']['closest'] == c and sess(store)['found']['BRICK']['result'] == 'none'


REFUSALS = [
    ('LOOK_UNKNOWN_TRIAL', lambda t: {'looks': [a_look('t00000000zzzz')]}, lambda t: {'eid': 'STREET', 'trial': 't00000000zzzz'}),
    ('LOOK_VERDICT', lambda t: {'looks': [a_look(t[0], 'good')]}, lambda t: {'eid': 'STREET', 'verdict': 'good'}),
    ('LOOK_SEEN', lambda t: {'looks': [a_look(t[0], seen='  ')]}, lambda t: {'eid': 'STREET', 'max': 300}),
    ('LOOK_SEEN', lambda t: {'looks': [a_look(t[0], seen='x' * 301)]}, lambda t: {'eid': 'STREET', 'max': 300}),
    ('LOOK_VIEW', lambda t: {'looks': [a_look(t[0], view=' ', keep=True)]}, lambda t: {'eid': 'STREET'}),
    ('KEEP_FAIL', lambda t: {'looks': [a_look(t[0], 'fail', keep=True)]}, lambda t: {'eid': 'STREET', 'trial': t[0]}),
    ('KEEP_LIMIT', lambda t: {'looks': [a_look(x, view=f'view {i}', keep=True) for i, x in enumerate(t)]}, lambda t: {'eid': 'STREET', 'max': 3}),
    ('KEEP_LIMIT', lambda t: {'looks': [a_look(t[0], view='side', keep=True), a_look(t[1], 'weak', view=' Side', keep=True)]}, lambda t: {'eid': 'STREET', 'max': 3}),
    ('LOOK_NOTHING', lambda t: {'looks': [], 'clips': [], 'note': 'nothing'}, lambda t: {'eid': 'STREET'}),
]


@pytest.mark.parametrize('name,row,fields', REFUSALS, ids=[f'{r[0]}-{i}' for i, r in enumerate(REFUSALS)])
def test_each_refusal_of_a_look_refuses_the_whole_thing_and_records_the_others(name, row, fields):
    store, outputs = film(trials=False)
    t = searched(store, outputs, 'STREET', (1.0, 2.0, 3.0, 4.0))
    b, = searched(store, outputs, 'BRICK', (5.0,))
    before = sess(store)
    out = look(store, outputs, {'element': 'STREET', 'clips': ['C001'], **row(t)}, {'element': 'BRICK', 'clips': ['C001'], 'looks': [a_look(b, keep=True)]})
    assert out['refused'] == {'STREET': getattr(RF, name).format(**fields(t))}
    assert out['recorded'] == ['BRICK'] and out['results'] == {'BRICK': 'found'}            # one refused thing does not stop the others
    s = sess(store)
    assert s['found'].get('STREET') == before['found'].get('STREET')                       # the refused thing keeps what it had
    assert not [r for r in s['references'].values() if r['element_id'] == 'STREET' and r['id'] not in before['references']]
    assert all('STREET' not in trials_of(store)[x]['looks'] for x in t)


def test_a_look_on_a_frame_taken_for_another_thing_is_refused():
    store, outputs = film(trials=False)
    b, = searched(store, outputs, 'BRICK', (5.0,))
    out = look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'looks': [a_look(b)]})
    assert out['refused'] == {'STREET': RF.LOOK_UNKNOWN_TRIAL.format(trial=b, eid='STREET')}
    assert look(store, outputs, {'element': 'DOOR', 'clips': ['C001']})['refused'] == {'DOOR': 'Unknown element DOOR.'}
    with pytest.raises(ValueError, match='helper or assistant'):
        look(store, outputs, {'element': 'STREET', 'clips': ['C001']}, by='operator')


def test_what_next_after_a_look_names_the_things_left_then_the_round():
    store, outputs = film(trials=False)
    s = sess(store)
    for eid, rec in s['found'].items():
        rec['fingerprint'] = RF.fingerprint(next(e for e in F.plan()['elements'] if e['id'] == eid))
    for eid in ('STREET', 'BRICK'):
        s['found'].pop(eid)
    s['found']['FAN']['fingerprint'] = 'the plan changed since'   # a search of an older plan counts as not searched
    V.save_json(store, V.key(RUN, 'session.json'), s)
    out = look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'note': 'not there'})
    assert out['left'] == ['FAN', 'BRICK'] and out['then'] == RF.LOOK_MORE.format(n=1, left=2, ids='FAN, BRICK') == '1 thing(s) recorded. 2 are not searched yet: FAN, BRICK.'
    out = look(store, outputs, {'element': 'BRICK', 'not_searched': 'no clip shows a wall'}, {'element': 'FAN', 'clips': ['C001', 'C002']})
    assert out['left'] == [] and out['then'] == RF.LOOK_ALL and '`vw visuals round --file out/reference-round.json`' in RF.LOOK_ALL


def test_two_calls_for_the_same_thing_in_a_row_leave_one_consistent_record():
    store, outputs = film(trials=False)
    a, b, _ = searched(store, outputs, 'STREET')
    body = {'element': 'STREET', 'clips': ['C001'], 'note': 'n', 'looks': [a_look(a, 'pass', 'whole', keep=True), a_look(b, 'weak', 'from the other side', keep=True)]}
    first = look(store, outputs, copy.deepcopy(body))
    again = look(store, outputs, copy.deepcopy(body))
    s = sess(store)
    assert again['kept'] == first['kept'] and again['refused'] == {} and s['found']['STREET']['kept'] == first['kept']['STREET']
    assert len([r for r in s['references'].values() if r['element_id'] == 'STREET' and r['kind'] == 'frame']) == 2


def test_a_second_helper_replaces_the_search_record_and_cannot_keep_over_the_limit():
    store, outputs = film(trials=False)
    t = searched(store, outputs, 'STREET', (1.0, 2.0, 3.0, 4.0, 5.0))
    look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'note': 'first', 'looks': [a_look(t[0], view='v1', keep=True), a_look(t[1], view='v2', keep=True)]})
    out = look(store, outputs, {'element': 'STREET', 'clips': ['C002'], 'note': 'second', 'looks': [a_look(t[2], 'weak', view='v3', keep=True)]})
    rec = sess(store)['found']['STREET']
    assert (rec['note'], rec['clips'], rec['result'], len(rec['kept'])) == ('second', ['C002'], 'found', 3) and out['kept']['STREET'] == rec['kept']
    for extra in (a_look(t[3], view='v4', keep=True), a_look(t[4], view='V1', keep=True)):
        assert look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'looks': [extra]})['refused'] == {'STREET': RF.KEEP_LIMIT.format(eid='STREET', max=3)}
    assert sess(store)['found']['STREET'] == rec


def test_a_thing_searched_again_after_the_plan_changed_starts_from_nothing():
    store, outputs = film(trials=False)
    a, = searched(store, outputs, 'STREET', (1.0,))
    old = look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'looks': [a_look(a, view='whole', keep=True)]})['kept']['STREET'][0]
    plan = F.plan()
    next(e for e in plan['elements'] if e['id'] == 'STREET')['description'] = 'A paved street.'
    TOLD['plan'] = plan
    assert RF.found_all(store, RUN, sess(store), plan)['STREET']['stale'] is True
    assert look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'looks': [a_look(a, view='whole', keep=True)]})['refused'] == {'STREET': RF.LOOK_UNKNOWN_TRIAL.format(trial=a, eid='STREET')}   # its old trial frames are dropped
    b, = searched(store, outputs, 'STREET', (2.0,))
    new = look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'looks': [a_look(b, view='whole', keep=True)]})['kept']['STREET']
    s = sess(store)
    assert len(new) == 1 and new[0] != old and old not in s['references'] and RF.found_all(store, RUN, s, plan)['STREET']['stale'] is False


def test_the_same_frame_kept_for_two_things_is_one_trial_frame_and_a_reference_for_each():
    store, outputs = film(trials=False)
    take(store, outputs, ('STREET', 'C001', 7.0), ('BRICK', 'C001', 7.0))
    t = RF.trial_id('C001', 7.0)
    out = look(store, outputs, {'element': 'STREET', 'clips': ['C001'], 'looks': [a_look(t, view='whole', seen='The street, wide.', keep=True)]},
               {'element': 'BRICK', 'clips': ['C001'], 'looks': [a_look(t, 'weak', view='whole', seen='A wall of it, far.', keep=True)]})
    (a,), (b,) = out['kept']['STREET'], out['kept']['BRICK']
    s, row = sess(store), trials_of(store)[t]
    assert a != b and s['references'][a]['element_id'] == 'STREET' and s['references'][b]['weak'] is True
    assert row['looks']['STREET']['ref'] == a and row['looks']['BRICK']['ref'] == b and row['looks']['BRICK']['seen'] == 'A wall of it, far.'


def test_a_film_with_an_older_round_takes_no_trial_frame_and_no_look():
    store, outputs = film(trials=False)
    V.save_json(store, V.key(RUN, 'session.json'), F.older_session())
    before = store.get(V.key(RUN, 'session.json'))
    for call in (lambda: take(store, outputs, ('STREET', 'C001', 1.0)), lambda: look(store, outputs, {'element': 'STREET', 'not_searched': 'x'})):
        with pytest.raises(ValueError) as exc:
            call()
        assert str(exc.value) == RF.OLDER_ROUND
    assert store.get(V.key(RUN, 'session.json')) == before and not store.exists(V.key(RUN, 'trials.json'))   # exactly as before


# ---------- what a round may show (3.3) ----------

def test_round_frames_gives_the_looked_frames_in_view_order():
    s = F.session('1')
    assert RF.round_frames(s, F.plan(), 'TROWEL', []) == ['f-trowel-side', 'f-trowel-use']
    assert RF.round_frames(s, F.plan(), 'TROWEL', ['f-trowel-use', 'f-trowel-side']) == ['f-trowel-side', 'f-trowel-use']
    assert RF.round_frames(s, F.plan(), 'TROWEL', ['f-trowel-use']) == ['f-trowel-use'] and RF.round_frames(s, F.plan(), 'STREET', []) == []
    s['references']['old'] = {**copy.deepcopy(s['references']['f-trowel-side']), 'id': 'old'}
    for k in ('view', 'look', 'weak', 'trial'):
        s['references']['old'].pop(k)
    assert RF.round_frames(s, F.plan(), 'TROWEL', []) == ['f-trowel-side', 'f-trowel-use']   # a frame with no look is not shown


def test_frame_no_look_refuses_a_named_frame_nobody_looked_at():
    s = F.session('1')
    s['references']['f-tile-under'].pop('look')
    with pytest.raises(ValueError) as exc:
        RF.round_frames(s, F.plan(), 'TILE', ['f-tile-under'])
    assert str(exc.value) == RF.FRAME_NO_LOOK.format(fid='f-tile-under', eid='TILE')
    with pytest.raises(ValueError, match='f-trowel-side is not a footage frame of TILE'):
        RF.round_frames(s, F.plan(), 'TILE', ['f-trowel-side'])


def test_not_searched_refuses_a_thing_with_no_search_record_while_the_run_has_footage():
    s = F.session('1')
    s['found'].pop('STREET')
    with pytest.raises(ValueError) as exc:
        RF.round_frames(s, F.plan(), 'STREET', [])
    assert str(exc.value) == RF.NOT_SEARCHED.format(eid='STREET')
    s['clip_safe_zoom'] = {}   # `prepare` found no analysed clip: a film with no footage
    assert RF.round_frames(s, F.plan(), 'STREET', []) == []


def test_frames_of_gives_the_candidate_and_approved_looked_frames():
    s = F.session('2')   # the frames are approved by now
    assert RF.frames_of(s, 'TROWEL') == [{'ref': 'f-trowel-side', 'view': 'side', 'verdict': 'pass', 'seen': 'The whole trowel, side on, sharp; the handle is reddish-brown.', 'weak': False},
                                         {'ref': 'f-trowel-use', 'view': 'in the hand, lifting mortar', 'verdict': 'weak', 'seen': 'In the hand, the blade half covered by mortar.', 'weak': True}]
    s['references']['f-trowel-side']['status'] = 'rejected'
    assert [f['ref'] for f in RF.frames_of(s, 'TROWEL')] == ['f-trowel-use'] and RF.frames_of(s, 'FAN') == [] and RF.frames_of({}, 'FAN') == []


def test_found_all_gives_each_result_with_its_clips_its_closest_picture_and_stale():
    store, outputs = film()
    RF.digest(store, RUN, outputs)
    s, plan = sess(store), F.plan()
    s['found']['TILE']['fingerprint'] = RF.fingerprint(next(e for e in plan['elements'] if e['id'] == 'TILE'))
    s['found']['FAN']['clips'] = ['C001', 'C002', 'C003', 'C004', 'C005', 'C006']
    s['found'].pop('T_LAY')
    s['found']['GONE'] = dict(s['found']['FAN'])   # a thing the plan no longer names
    out = RF.found_all(store, RUN, s, plan)
    assert set(out) == {'MASON', 'TROWEL', 'FAN', 'BRICK', 'STREET', 'TILE'}                  # a thing with no record is absent
    assert {k: v['result'] for k, v in out.items()} == {'MASON': 'none', 'TROWEL': 'found', 'FAN': 'none', 'BRICK': 'not_searched', 'STREET': 'none', 'TILE': 'found'}
    fan = out['FAN']
    assert set(fan) == {'result', 'by', 'at', 'clips', 'clip_names', 'not_searched', 'note', 'closest', 'stale'}
    assert fan['clips'] == 6 and fan['clip_names'] == ['C001.mp4', 'C002.mp4', 'C003.mp4', 'C004', 'C005'] and fan['not_searched'] == ['C003.mp4'] and fan['note'] == 'No indoor wall is filmed.'
    assert fan['closest'] == {'trial': 't0000000000c1', 'key': f"{RUN['id']}/visuals/trials/t0000000000c1.jpg", 'view': 'whole', 'seen': 'A switch plate on a wall, not a fan regulator.'}
    assert out['STREET']['closest'] is None and out['BRICK']['clips'] == 0 and out['BRICK']['note'] == 'The helper was stopped.'
    assert out['TILE']['stale'] is False and out['TROWEL']['stale'] is True
    s['found']['TROWEL']['result'] = 'weak'
    assert RF.found_all(store, RUN, s, plan)['TROWEL']['result'] == 'weak'


FIELDS = {'name': 'Another name', 'kind': 'material', 'identity': 'representative', 'description': 'A blunt blade.', 'requirements': 'Any trowel.',
          'required_views': ['side'], 'size': []}


def test_the_fingerprint_changes_with_each_of_its_fields_and_with_no_other():
    trowel = next(e for e in F.plan()['elements'] if e['id'] == 'TROWEL')
    base = RF.fingerprint(trowel)
    assert len(base) == 64 and base == RF.fingerprint(copy.deepcopy(trowel))
    for field, value in FIELDS.items():
        assert RF.fingerprint({**trowel, field: value}) != base, field
    assert RF.fingerprint({**trowel, 'id': 'T2', 'speaker': True, 'signs_of_use': ['x'], 'material_spec': {'parts': []}}) == base


# ---------- the operator's answers to a footage picture (3.4) ----------

def test_not_this_keeps_the_next_best_frame_of_the_same_view_pass_before_weak_never_fail():
    store, outputs = film()
    doc = F.trials()
    doc['trials']['t0000000000a4'] = {**copy.deepcopy(doc['trials']['t0000000000a3']), 'id': 't0000000000a4', 'at_s': 31.0, 'looks': {'TROWEL': {**F.LOOKS[('t0000000000a3', 'TROWEL')], 'verdict': 'pass', 'seen': 'Side on, sharp.', 'trial': 't0000000000a4'}}}
    doc['trials']['t0000000000a5'] = {**copy.deepcopy(doc['trials']['t0000000000a3']), 'id': 't0000000000a5', 'at_s': 32.0, 'looks': {'TROWEL': {**F.LOOKS[('t0000000000a3', 'TROWEL')], 'verdict': 'fail', 'trial': 't0000000000a5'}}}
    V.save_json(store, V.key(RUN, 'trials.json'), doc)
    conn = H.Conn()
    out = RF.not_this(conn, store, USER, RUN, outputs, 'TROWEL', 'f-trowel-side', 'The handle is cut off.')
    s = sess(store)
    new = s['references'][out['next']]
    assert s['references']['f-trowel-side']['status'] == 'rejected' and s['references']['f-trowel-side']['rejection']['quote'] == 'The handle is cut off.'
    assert (new['trial'], new['view'], new['weak'], new['status'], new['look']['verdict'], new['look']['ref']) == ('t0000000000a4', 'side', False, 'candidate', 'pass', out['next'])   # the pass before the weak one
    assert new['source']['requested_s'] == 31.0
    assert s['found']['TROWEL']['kept'] == [out['next'], 'f-trowel-use'] and s['found']['TROWEL']['result'] == 'found'
    assert s['round']['elements']['TROWEL']['frames'] == [out['next'], 'f-trowel-use']       # the line comes back with it
    assert len(conn.log) == 1 and 'The handle is cut off.' in conn.log[0]
    second = RF.not_this(conn, store, USER, RUN, outputs, 'TROWEL', out['next'], '')['next']
    assert sess(store)['references'][second]['trial'] == 't0000000000a3' and sess(store)['references'][second]['weak'] is True
    assert RF.not_this(conn, store, USER, RUN, outputs, 'TROWEL', second, 'Blurred.') == {'next': None}   # the one left has the verdict fail: never
    s = sess(store)
    assert s['found']['TROWEL']['kept'] == ['f-trowel-use'] and s['found']['TROWEL']['result'] == 'weak'
    again = look(store, outputs, {'element': 'TROWEL', 'clips': ['C001'], 'looks': [a_look('t0000000000a1', keep=True)]})   # a helper cannot bring a rejected frame back
    assert again['refused'] == {'TROWEL': RF.KEEP_REJECTED.format(eid='TROWEL', trial='t0000000000a1')}


def test_not_this_on_the_last_frame_leaves_none_was_found_and_refuses_what_is_not_a_frame_of_the_thing():
    store, outputs = film()
    assert RF.not_this(H.Conn(), store, USER, RUN, outputs, 'TILE', 'f-tile-under', 'Not our tile.') == {'next': None}
    s = sess(store)
    assert s['found']['TILE']['result'] == 'none' and s['found']['TILE']['kept'] == [] and s['round']['elements']['TILE']['frames'] == [] and RF.frames_of(s, 'TILE') == []
    with pytest.raises(ValueError, match='f-trowel-side is not a footage frame of TILE'):
        RF.not_this(H.Conn(), store, USER, RUN, outputs, 'TILE', 'f-trowel-side', '')


def test_that_is_it_makes_the_closest_picture_a_kept_weak_frame():
    store, outputs = film()
    conn = H.Conn()
    out = RF.that_is_it(conn, store, USER, RUN, outputs, 'FAN', 't0000000000c1', 'Yes, that is our regulator.')
    s = sess(store)
    r = s['references'][out['ref']]
    assert (r['kind'], r['element_id'], r['status'], r['weak'], r['trial'], r['view']) == ('frame', 'FAN', 'candidate', True, 't0000000000c1', 'whole')
    assert r['look']['verdict'] == 'weak' and r['look']['ref'] == out['ref'] and r['source']['requested_s'] == 35.0
    rec = s['found']['FAN']
    assert (rec['result'], rec['kept'], rec['closest']) == ('weak', [out['ref']], None) and s['round']['elements']['FAN']['frames'] == [out['ref']]
    assert len(conn.log) == 1 and 'Yes, that is our regulator.' in conn.log[0]
    assert RF.that_is_it(conn, store, USER, RUN, outputs, 'FAN', 't0000000000c1', 'again') == out   # said twice: one frame
    with pytest.raises(ValueError) as exc:
        RF.that_is_it(conn, store, USER, RUN, outputs, 'FAN', 't0000000000b1', '')
    assert str(exc.value) == RF.LOOK_UNKNOWN_TRIAL.format(trial='t0000000000b1', eid='FAN')


# ---------- what next (3.9), the constants as the contract writes them ----------

def test_the_what_next_sentences_are_the_contracts():
    assert RF.FIND_START.startswith('The references come next. Run `vw visuals digest`.') and '`vw-reference-finder` helpers, about 5 things each, up to 6 at a time' in RF.FIND_START
    assert RF.TRIAL_NEXT == 'Read each trial frame, then record what you saw: `vw visuals look --file <file>`. A trial frame is not a reference.'
    assert RF.FRAME_RULE.startswith('A frame is a good reference when the thing is whole, not covered, large enough to read, sharp, and its shape and size can be read.')
    for text in (RF.FIND_START, RF.FIND_WORDS, RF.TRIAL_NEXT, RF.LOOK_MORE, RF.LOOK_ALL, RF.FRAME_RULE):
        assert not any(w in text.lower() for w in ('site', 'trade', 'mason', 'brick'))   # generic for every category of film
