"""Integration steps B to D: the server steps of the new AI video route (app/guide.py): the scene with its checks before spend, the fresh
checker's verdict, the still on GPT image 2.6, its approval on the overlay, the take's words, and Shoot. No Blender, no paid call."""
import json

import pytest

from app import guide as GD, guide_spec as G, visuals_stage as VS
from app.errors import Problem
from test_design151_refs_pure import KILN, MASON, NEW, doc_with, new_store
from test_guide_spec_pure import home_walk
from test_step_a_generations_pure import Conn as RecordConn
from test_visuals_stage_pure import USER, accepted, saved

OTHER = {'id': 'u2', 'name': 'Revathi'}
STILL_WORDS = ('A wide shot at eye level from across the lane: a modest single-storey brick home with a verandah along its front. The blue box is the father, '
               'walking to the right; the orange box is the daughter behind him; the magenta box is the mother, standing on the verandah. THE MOMENT: they have not '
               'reached the verandah. LIGHT: late morning, soft daylight from the upper left.')
TAKE_WORDS = ('BLUE box = the father in the image. ORANGE box = the daughter in the image. MAGENTA box = the mother in the image, on the verandah. '
              'ONE action only: the father and the daughter walk home. From the first frame both are ALREADY WALKING to the right, exactly on their boxes, '
              'and are still walking at 10.0 s. The mother stands in place the whole time. Exactly three people; no one else appears.')


class Conn(RecordConn):
    """The record's fake, plus job inserts kept with their provider and request, and an open take when asked."""

    def __init__(self):
        super().__init__()
        self.queued, self.open_take = [], None

    def execute(self, sql, params=()):
        conn = self
        if 'insert into vw2_jobs' in sql:
            self.queued.append({'unit': params[1], 'provider': params[2], 'request': params[3].obj})
            return type('R', (), {'fetchone': lambda _: {'id': f'job-{len(conn.queued)}'}})()
        if 'update vw2_generations' in sql:
            if 'set record' in sql:
                run_id, shot_id, how = params[1], params[2], params[3]
                rows = [r for r in self.rows if (r['run_id'], r['shot_id'], r['how']) == (run_id, shot_id, how) and r['verdict'] is None]
                if rows:
                    rows[-1]['record'] = rows[-1]['record'] + params[0].obj
                return type('R', (), {'fetchone': lambda _: ({'attempt': rows[-1]['attempt']} if rows else None)})()
            rows = [r for r in self.rows if (r['run_id'], r['shot_id'], r['how']) == (params[1], params[2], params[3]) and r['verdict'] is None]
            if rows:
                rows[-1]['verdict'] = params[0]
            return type('R', (), {'fetchone': lambda _: None})()
        if "provider='video' and status in" in sql:
            return type('R', (), {'fetchone': lambda _: conn.open_take})()
        return super().execute(sql, params)


def spec10():
    s = home_walk()
    s['seconds'] = 10   # the fixture's video shot VS1 runs 250 frames at 25 a second: a 10 s slot
    s['action'] = {'start': 0, 'end': 10}
    for p in s['people'][:2]:
        p['path'][1] = {'t': 10, 'at': [p['path'][0]['at'][0] + 0.95 * 10 * 0.5, -0.8, 0.0]}
        p['pace'] = None
        del p['pace']
    return s


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})


@pytest.fixture
def film():
    doc = doc_with(KILN, MASON)
    refs = {'R1': {'id': 'R1', 'kind': 'sheet', 'element_id': 'P1', 'status': 'approved', 'key': 'run-1/visuals/references/R1.png', 'sha256': 'sha-R1'},
            'R2': {'id': 'R2', 'kind': 'sheet', 'element_id': 'P1', 'status': 'candidate', 'key': 'run-1/visuals/references/R2.png', 'sha256': 'sha-R2'}}
    return new_store(doc, refs, accepted=accepted(doc)), Conn()


def refused(fn):
    with pytest.raises((Problem, ValueError)) as e:
        fn()
    return getattr(e.value, 'message', None) or str(e.value)


def scene(store, conn, spec=None, **kw):
    return GD.set_scene(conn, store, USER, NEW, [], 'VS1', spec or spec10(), **kw)


def frames_back(store, conn, ok=True):
    s = saved(store)
    g = s['guides']['VS1']
    job = {'id': g['frames']['job_id'], 'request': {'kind': 'guide-frames', 'shot_id': 'VS1', 'sha256': g['sha256']}}
    GD.apply_result(s, job, 'ready' if ok else 'failed', {'frames': [{'n': 1, 'key': 'k1'}], 'strip_key': 'strip'} if ok else None, None if ok else 'Blender failed')
    VS.save_session(store, NEW, s)
    return g['sha256']


def passed(store, conn):
    if 'guides' not in saved(store):
        scene(store, conn)
    sha = frames_back(store, conn)
    return GD.verdict(conn, store, OTHER, NEW, [], 'VS1', sha, True, [{'look': 'everyone reads as a person', 'pass': True}])


def rendered(store, conn):
    passed(store, conn)
    s = saved(store)
    g = s['guides']['VS1']
    job = {'id': g['render']['job_id'], 'request': {'kind': 'guide-render', 'shot_id': 'VS1', 'sha256': g['sha256']}}
    GD.apply_result(s, job, 'ready', {'guide_key': 'run-1/visuals/guides/x/guide.mp4', 'sha256': 'sha-guide', 'bytes': 9, 'frame1_key': 'run-1/visuals/guides/x/frame1.png', 'frame1_sha256': 'sha-f1', 'render_seconds': 600}, None)
    VS.save_session(store, NEW, s)


def still_made(store, conn, ok=True):
    out = GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}])
    s = saved(store)
    job = {'id': out['job_id'], 'request': {'kind': 'guide-still', 'shot_id': 'VS1', 'sha256': s['guides']['VS1']['sha256'], 'reference': {'id': out['still_id']}}}
    GD.apply_result(s, job, 'retained' if ok else 'failed', {'key': 'run-1/visuals/references/st.png', 'sha256': 'sha-still', 'bytes': 5, 'width': 1536, 'height': 864, 'overlay_key': 'ov.jpg', 'cost': {}} if ok else None,
                    None if ok else 'the provider refused the picture')
    VS.save_session(store, NEW, s)
    return out['still_id']


def ready(store, conn):
    rendered(store, conn)
    sid = still_made(store, conn)
    GD.approve_still(conn, store, USER, NEW, [], 'VS1', sid, 'sha-still', 'Yes, it sits on the guide.')
    GD.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS)
    return sid


# ---------- step B: the scene ----------

def test_a_scene_is_stored_its_check_frames_queued_and_its_warnings_and_layout_returned(film):
    store, conn = film
    out = scene(store, conn)
    g = saved(store)['guides']['VS1']
    assert out['sha256'] == g['sha256'] and out['frames'] == [1, 150, 300] and 'cannot see' in out['cannot_see'] and out['layout'].startswith('EXACT LAYOUT')
    assert conn.queued == [{'unit': 'VS1', 'provider': 'guide', 'request': {'kind': 'guide-frames', 'shot_id': 'VS1', 'sha256': g['sha256'], 'spec_key': g['key'], 'frames': [1, 150, 300]}}]
    assert json.loads(store.files[g['key']])['recipe'] == 'walker' and g['frames'] == {'job_id': 'job-1', 'status': 'queued'}
    row = conn.rows[0]
    assert (row['how'], row['attempt']) == ('guide', 1) and row['record'][0]['kind'] == 'scene' and row['record'][0]['process_note'].startswith('A family')


def test_the_same_scene_again_queues_nothing(film):
    store, conn = film
    scene(store, conn)
    assert scene(store, conn)['unchanged'] is True and len(conn.queued) == 1


@pytest.mark.parametrize('change, word', [
    (lambda s: s.update(recipe='crowd'), 'not yet available'),
    (lambda s: (s.clear(), s.update(home_walk())), "the shot's slot is 10.0 s"),   # a 5 s guide for a 10 s slot
    (lambda s: s['people'][0]['path'].__setitem__(1, {'t': 10, 'at': [40.0, -0.8, 0.0]}), 'm/s'),
])
def test_a_scene_is_refused_before_anything_is_rendered(film, change, word):
    store, conn = film
    spec = spec10()
    change(spec)
    assert word in refused(lambda: scene(store, conn, spec))
    assert conn.queued == [] and 'guides' not in saved(store) and conn.rows == []


def test_a_guide_is_only_for_an_ai_video_shot(film):
    store, conn = film
    assert 'not an AI video shot' in refused(lambda: GD.set_scene(conn, store, USER, NEW, [], 'IM1', spec10()))


def test_only_the_support_refusal_can_be_overridden_and_the_reason_is_kept(film):
    store, conn = film
    spec = spec10()
    spec['set'].append({'id': 'SHELF', 'name': 'the shelf', 'shape': 'box', 'min': [3.0, 1.9, 1.5], 'max': [4.0, 2.0, 1.55], 'colour': [0.1, 0.4, 0.4]})
    assert 'rests on nothing' in refused(lambda: scene(store, conn, spec))
    assert 'Only the support check' in refused(lambda: scene(store, conn, spec, overrides={'speed': 'he must run'}))
    scene(store, conn, spec, overrides={'support': 'the shelf is fixed to the wall behind it'})
    g = saved(store)['guides']['VS1']
    assert g['overrides'][0]['check'] == 'support' and g['overrides'][0]['reason'].startswith('the shelf is fixed') and g['overrides'][0]['by_name'] == 'SK'
    assert conn.rows[0]['record'][0]['overrides'] == {'support': 'the shelf is fixed to the wall behind it'}


# ---------- the double check: a fresh checker's verdict, rounds counted by the server ----------

def test_a_verdict_needs_the_frames_and_the_current_scene(film):
    store, conn = film
    sha = scene(store, conn)['sha256']
    looks = [{'look': 'everyone reads as a person', 'pass': True}]
    assert 'not ready yet' in refused(lambda: GD.verdict(conn, store, OTHER, NEW, [], 'VS1', sha, True, looks))
    frames_back(store, conn)
    assert 'The scene changed' in refused(lambda: GD.verdict(conn, store, OTHER, NEW, [], 'VS1', 'f' * 64, True, looks))
    assert 'passes only when every look passes' in refused(lambda: GD.verdict(conn, store, OTHER, NEW, [], 'VS1', sha, True, [{'look': 'a', 'pass': False}]))


def test_a_pass_queues_the_render_once_and_a_fail_does_not(film):
    store, conn = film
    scene(store, conn)
    sha = frames_back(store, conn)
    out = GD.verdict(conn, store, OTHER, NEW, [], 'VS1', sha, False, [{'look': 'the door reads as a door', 'pass': False, 'fix': 'make it taller'}], 'the door is a slit')
    assert out['round'] == 1 and out['failed'] == ['the door reads as a door'] and len(conn.queued) == 1
    out = GD.verdict(conn, store, OTHER, NEW, [], 'VS1', sha, True, [{'look': 'the door reads as a door', 'pass': True}])
    assert out['round'] == 2 and conn.queued[-1]['request']['kind'] == 'guide-render' and saved(store)['guides']['VS1']['render']['status'] == 'queued'
    GD.verdict(conn, store, OTHER, NEW, [], 'VS1', sha, True, [{'look': 'again', 'pass': True}])
    assert sum(1 for q in conn.queued if q['request']['kind'] == 'guide-render') == 1


def test_the_rounds_are_counted_across_changed_scenes_and_the_operator_is_brought_in_after_two(film):
    store, conn = film
    scene(store, conn)
    sha = frames_back(store, conn)
    GD.verdict(conn, store, OTHER, NEW, [], 'VS1', sha, False, [{'look': 'a', 'pass': False}])
    changed = spec10()
    changed['people'][2]['at'] = [4.0, 1.2, 0.3]
    scene(store, conn, changed)
    sha2 = frames_back(store, conn)
    out = GD.verdict(conn, store, OTHER, NEW, [], 'VS1', sha2, False, [{'look': 'a', 'pass': False}])
    assert out['round'] == 2 and 'Show the operator what is still open' in out['next']


def test_a_result_for_a_scene_that_changed_meanwhile_is_ignored(film):
    store, conn = film
    scene(store, conn)
    s = saved(store)
    assert GD.apply_result(s, {'id': 'job-1', 'request': {'kind': 'guide-frames', 'shot_id': 'VS1', 'sha256': 'old'}}, 'ready', {'frames': [], 'strip_key': 'x'}, None) is None
    assert s['guides']['VS1']['frames']['status'] == 'queued'


def test_failed_check_frames_say_why(film):
    store, conn = film
    scene(store, conn)
    frames_back(store, conn, ok=False)
    g = saved(store)['guides']['VS1']
    assert g['frames']['status'] == 'failed' and g['frames']['error'] == 'Blender failed'


# ---------- step C: the still ----------

def test_no_still_before_the_guide_is_rendered(film):
    store, conn = film
    scene(store, conn)
    assert 'not rendered yet' in refused(lambda: GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, []))


def test_the_still_is_gpt_image_2_6_on_any_film_with_the_guide_frame_first_the_layout_numbers_and_each_pictures_job(film):
    store, conn = film
    assert NEW['image_provider'] == 'gemini'   # this film's own picture AI is not GPT image
    rendered(store, conn)
    store.files['run-1/visuals/references/R1.png'] = b'png'
    GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}])
    q = conn.queued[-1]
    r = q['request']
    assert q['provider'] == 'guide-still' and (r['model'], r['size'], r['quality'], r['op'], r['provider']) == ('gpt-image-2.6-sunburst', '1536x864', 'high', 'edit', 'openai')
    assert [p['key'] for p in r['parents']] == ['run-1/visuals/guides/x/frame1.png', 'run-1/visuals/references/R1.png']
    assert r['prompt'].startswith('The FIRST image is a rough 3D layout') and STILL_WORDS in r['prompt'] and 'EXACT LAYOUT, measured from the first image' in r['prompt']
    assert 'Exactly 3 people in view; no one else.' in r['prompt'] and 'Image 1 is the layout: take from it positions and framing only. Image 2 is the mason: copy his face, build and clothes.' in r['prompt']
    still = saved(store)['guides']['VS1']['stills'][0]
    assert still['status'] == 'generating' and still['prompt'] == STILL_WORDS and still['inputs'] == [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}]


@pytest.mark.parametrize('parents, word', [
    ([{'id': 'R2', 'job': 'the mason'}], 'not approved'),
    ([{'id': 'R9', 'job': 'the mason'}], 'not a picture of this film'),
    ([{'id': 'R1'}], 'say what the picture is for'),
])
def test_only_approved_pictures_each_with_its_job_go_into_a_still(film, parents, word):
    store, conn = film
    rendered(store, conn)
    n = len(conn.queued)
    assert word in refused(lambda: GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, parents))
    assert len(conn.queued) == n


def test_a_still_is_refused_over_the_cap_and_one_at_a_time(film, monkeypatch):
    store, conn = film
    rendered(store, conn)
    GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [])
    assert 'being made' in refused(lambda: GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, []))
    s = saved(store)
    s['guides']['VS1']['stills'][0]['status'] = 'failed'
    s['cap_inr'] = 1
    VS.save_session(store, NEW, s)
    with pytest.raises(Problem) as e:
        GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [])
    assert e.value.code == 'VISUALS_CAP'


def test_a_still_is_approved_by_its_exact_file_on_its_overlay_and_a_failed_one_says_why(film):
    store, conn = film
    rendered(store, conn)
    sid = still_made(store, conn)
    with pytest.raises(Problem) as e:
        GD.approve_still(conn, store, USER, NEW, [], 'VS1', sid, 'another-sha', 'yes')
    assert e.value.code == 'REFERENCE_MISMATCH'
    out = GD.approve_still(conn, store, USER, NEW, [], 'VS1', sid, 'sha-still', 'Yes.')
    g = saved(store)['guides']['VS1']
    assert out['status'] == 'approved' and g['stills'][0]['approval']['quote'] == 'Yes.' and g['stills'][0]['approval']['sha256'] == 'sha-still'
    bad = still_made(store, conn, ok=False)
    failed = next(s for s in saved(store)['guides']['VS1']['stills'] if s['id'] == bad)
    assert failed['status'] == 'failed' and failed['error'] == 'the provider refused the picture'
    assert 'finished still' in refused(lambda: GD.approve_still(conn, store, USER, NEW, [], 'VS1', bad, 'x', 'yes'))


def test_a_still_without_its_overlay_cannot_be_approved(film):
    store, conn = film
    rendered(store, conn)
    sid = still_made(store, conn)
    s = saved(store)
    s['guides']['VS1']['stills'][0]['overlay_key'] = None
    VS.save_session(store, NEW, s)
    assert 'no overlay yet' in refused(lambda: GD.approve_still(conn, store, USER, NEW, [], 'VS1', sid, 'sha-still', 'yes'))


def test_a_masked_repair_sends_only_the_still_its_region_and_the_fixed_words(film):
    store, conn = film
    rendered(store, conn)
    sid = still_made(store, conn)
    assert 'names its region' in refused(lambda: GD.request_still(conn, store, USER, NEW, [], 'VS1', 'the band at the wall foot is teal; make it grey stone paving.', None, repair_of=sid))
    GD.request_still(conn, store, USER, NEW, [], 'VS1', 'the band at the wall foot is teal; make it grey stone paving.', None, repair_of=sid, region={'left': 0.2, 'top': 0.8, 'width': 0.4, 'height': 0.15})
    r = conn.queued[-1]['request']
    assert [p['id'] for p in r['parents']] == [sid] and r['region'] == {'left': 0.2, 'top': 0.8, 'width': 0.4, 'height': 0.15}
    assert r['prompt'].startswith('Change ONLY the transparent (masked) area: the band at the wall foot') and 'EXACT LAYOUT' not in r['prompt']
    assert saved(store)['guides']['VS1']['stills'][-1]['repair_of'] == sid


def test_rejecting_a_still_needs_the_words_and_says_the_ways_forward(film):
    store, conn = film
    rendered(store, conn)
    sid = still_made(store, conn)
    assert 'Say what is wrong' in refused(lambda: GD.reject_still(conn, store, USER, NEW, [], 'VS1', sid, '', ''))
    out = GD.reject_still(conn, store, USER, NEW, [], 'VS1', sid, 'the father is twice as tall as his box', '')
    assert 'masked repair' in out['next'] and saved(store)['guides']['VS1']['stills'][0]['status'] == 'rejected'


# ---------- step D: the take's words ----------

@pytest.mark.parametrize('bad, word', [
    ('The camera is locked off on a tripod.', 'camera gear'),
    ('A calm, serene morning.', 'mood words'),
    ('He walks on. Do not let him stop.', 'lock sentences'),
    ('Use Image 2 as the end frame.', 'end picture'),
    ('She walks VERY FAST to the door.', 'push words'),
    ('The light comes from the left.', 'the light is fixed in the still'),
])
def test_a_take_prompt_never_carries_what_the_tests_showed_to_fail(film, bad, word):
    store, conn = film
    rendered(store, conn)
    assert word in refused(lambda: GD.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS + ' ' + bad))
    assert 'take_prompt' not in saved(store)['guides']['VS1']


def test_the_tested_wordings_are_not_refused():
    for ok in ('it turns slowly to the left to follow her, keeping her a little right of centre; no zoom', 'Light stays exactly as in the image.', 'NO footsteps, no speech, no music.',
               'a quiet village morning ambience', 'her LEFT hand hangs STILL at her side', 'at an ordinary everyday pace, exactly on her box'):
        assert GD.prompt_problems(ok) == [], ok


def test_the_prompt_as_sent_has_the_fixed_opening_the_writers_words_and_the_two_closing_lines_once(film):
    store, conn = film
    rendered(store, conn)
    out = GD.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS + ' Light stays exactly as in the image.')
    sent = out['prompt']
    assert sent.startswith('Edit the video. It is a rough 3D blocking render') and TAKE_WORDS in sent and sent.count('Light stays exactly as in the image.') == 1
    assert sent.endswith('No dialogue. No extra sound effects.') and 'How to read the video' not in sent and 'documentary' not in sent
    assert 'ONE action only' in refused(lambda: GD.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS.replace('ONE action only:', 'The action:')))


def test_a_guide_with_marks_explains_them_in_one_fixed_line():
    sent = GD.effective_prompt({'marks': {'band': 'LANE', 'stripes': True}}, TAKE_WORDS)
    assert 'How to read the video: the coloured band on the ground only marks where the walking line runs' in sent and "marks that person's side" in sent


# ---------- step D: Shoot ----------

def test_shoot_is_refused_until_everything_on_the_card_is_there_and_names_what_is_missing(film):
    store, conn = film
    scene(store, conn)
    said_ = refused(lambda: GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.'))
    assert 'still missing: the rendered guide, an approved still made from this guide, the overlay, the take\'s words' in said_
    assert not any(q['provider'] == 'video' for q in conn.queued)


def test_shoot_needs_the_operators_words_and_sends_one_take_as_long_as_the_guide(film):
    store, conn = film
    sid = ready(store, conn)
    assert "on the operator's word" in refused(lambda: GD.shoot(conn, store, USER, NEW, [], 'VS1', ''))
    out = GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Yes, shoot it.')
    q = conn.queued[-1]
    assert q['provider'] == 'video' and q['request']['duration_seconds'] == 10 and q['request']['model'] == 'gemini-omni-1.2-flash' and out['seconds'] == 10
    snap = json.loads(store.files[q['request']['request_key']])
    assert snap['kind'] == 'guide' and snap['guide'] == {'key': 'run-1/visuals/guides/x/guide.mp4', 'sha256': 'sha-guide', 'seconds': 10, 'scene_sha256': saved(store)['guides']['VS1']['sha256']}
    assert snap['start_image']['reference_id'] == sid and snap['start_image']['key'] == 'run-1/visuals/references/st.png' and snap['resolution'] == '720p' and snap['aspect_ratio'] == '16:9'
    assert snap['effective_prompt'].startswith('Edit the video.') and snap['placement']['exact_seconds'] == 10.0 and 'end_image' not in snap
    s = saved(store)
    assert s['preparations']['VS1']['guide'] is True and s['guides']['VS1']['takes'][0]['quote'] == 'Yes, shoot it.'
    assert conn.rows[0]['record'][-1]['kind'] == 'take sent' and conn.rows[0]['record'][-1]['prompt'] == snap['effective_prompt']


def test_the_same_request_is_never_sent_twice(film):
    store, conn = film
    ready(store, conn)
    GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.')
    n = len(conn.queued)
    assert 'the same request is never sent twice' in refused(lambda: GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Again.'))
    assert 'the same request is never sent twice' in refused(lambda: GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Again.', again=True))
    assert len(conn.queued) == n
    GD.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS + ' The neem leaves stir a little.')   # one thing changed: the words
    GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot the changed one.')
    assert len(conn.queued) == n + 1


def test_a_take_that_came_back_unusable_may_be_sent_once_more_on_the_operators_word(film):
    store, conn = film
    ready(store, conn)
    job_id = GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.')['job_id']
    s = saved(store)
    s.setdefault('take_checks', {})[job_id] = {'blocked': 'the guide came back unedited'}
    VS.save_session(store, NEW, s)
    assert 'the operator says so' in refused(lambda: GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.'))
    GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Send it once more.', again=True)
    s = saved(store)
    s['take_checks'][s['guides']['VS1']['takes'][-1]['job_id']] = {'blocked': 'the guide came back unedited'}
    VS.save_session(store, NEW, s)
    assert 'already sent twice' in refused(lambda: GD.shoot(conn, store, USER, NEW, [], 'VS1', 'And again.', again=True))


def test_no_second_take_while_one_is_open_and_none_over_the_cap(film):
    store, conn = film
    ready(store, conn)
    conn.open_take = {'id': 'job-open'}
    with pytest.raises(Problem) as e:
        GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.')
    assert e.value.code == 'JOB_OPEN'
    conn.open_take = None
    s = saved(store)
    s['cap_inr'] = 50   # a 10 s take at 8 rupees a second needs 80
    VS.save_session(store, NEW, s)
    with pytest.raises(Problem) as e:
        GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.')
    assert e.value.code == 'VISUALS_CAP'


def test_a_still_made_from_an_older_scene_does_not_count(film):
    store, conn = film
    ready(store, conn)
    changed = spec10()
    changed['people'][2]['at'] = [4.0, 1.2, 0.3]
    scene(store, conn, changed)
    assert 'an approved still made from this guide' in refused(lambda: GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.'))


# ---------- what the page and the chat tool are shown ----------

def test_the_view_of_a_guide_lists_where_it_stands_and_every_picture(film):
    store, conn = film
    ready(store, conn)
    v = GD.view(saved(store), 'VS1', lambda k: '/f/' + k)
    assert v['frames']['strip_url'] == '/f/strip' and v['render']['guide_url'].endswith('guide.mp4') and v['stills'][0]['overlay_url'] == '/f/ov.jpg'
    assert v['card'] == {'ready': True, 'missing': [], 'seconds': 10, 'cost_inr': 80.0, 'prompt': v['card']['prompt'], 'look_for': v['card']['look_for']} and 'red outlines' in v['card']['look_for']
    assert GD.view(saved(store), 'IM1', lambda k: k) is None
