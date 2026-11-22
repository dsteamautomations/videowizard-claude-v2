"""design/223 (SK, 22 Nov 2026): the new take process. The first take once at 360p, shown as it is: no check by Claude, no helper, no measurement,
nothing set aside. The operator accepts or says what is wrong; the assistant chooses the route (edit, remake by reference, both in a row, the
first take again, or none); every version is 720p; the film takes only a 720p video; the price follows the size. Without a database, without a
provider: no video is made here."""
import json
from datetime import datetime, timezone
from io import BytesIO

import pytest

from app import corrections as C, guide as G, takes as T, video_generators as VG, video_providers as VP, visuals_stage as V
from app.errors import Problem

RUN, USER = {'id': 'run-1', 'code': 'VW-99'}, {'id': 'u1', 'name': 'Op'}
NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
PROMPT = ('This shot shows the mason checking a roof tile. The yard, the two men, the light and the fixed camera stay as in the reference video. '
          'The tile-maker holds the tile out and the mason takes it with both hands, raps it with a knuckle and looks along its edges. '
          'At the end the mason holds the tile in his left hand, looking at it.')


def shot(sid, kind='video', start=0, end=125, **more):
    return {'id': sid, 'visual_type': kind, 'narration': 'As the demand grows', 'start_frame': start, 'end_frame': end, 'element_ids': ['P1'], **more}


def plan(*shots):
    return {'elements': [{'id': 'P1', 'kind': 'person', 'name': 'Mason'}], 'gaps': [{'gap_id': 'G1', 'title': 'Housing at work', 'scenes': [{'id': 'sc1', 'shots': list(shots)}]}]}


def job(jid, sid='S1', status='ready', size='360p', at='2026-11-22T10:00:00+00:00', error=None, **req):
    return {'id': jid, 'run_id': 'run-1', 'unit': sid, 'provider': 'video', 'status': status, 'updated_at': at, 'created_at': at, 'error': error,
            'request': {'kind': 'take', 'request_key': f'run-1/visuals/takes/{jid}.request.json', 'duration_seconds': 5, **({'resolution': size} if size else {}), **req},
            'result': {'key': f'run-1/visuals/takes/{jid}.mp4', 'sha256': jid.ljust(64, '0'), 'bytes': 1, 'evidence': {'duration_seconds': 5.04, 'timing_matches_placement': True}} if status == 'ready' else {}}


def frames(n=11):
    return {'guide': True, 'frames': [{'at_s': k * 0.5, 'key': f'f/{k}.jpg'} for k in range(n)], 'sheet_key': 'f/sheet.jpg'}


def guide(**more):
    sha = 'g' * 64
    return {'sha256': sha, 'key': 'k', 'seconds': 5, 'drawing': {'status': 'approved', 'sha256': sha}, 'verdicts': [{'sha256': sha, 'pass': True}],
            'render': {'status': 'ready', 'guide_key': 'g.mp4', 'frame1_key': 'f1.png', 'sha256': 'r'},
            'stills': [{'id': 'st1', 'status': 'approved', 'guide_sha256': sha, 'key': 'run-1/still.png', 'sha256': 's' * 64, 'overlay_key': 'o.jpg', 'prompt': 'A mason at a wall with bamboo poles.'}],
            'take_prompt': {'prompt': 'ONE action only: he lays the brick.', 'at': 't'}, 'takes': [], 'checks': [], **more}


def session(**more):
    s = {'round': {'v': 2, 'kept': True, 'pass': 'complete', 'elements': {}}, 'accepted': {}, 'choice_selections': {}, 'questions': {}, 'reviews': {}, 'selections': {}, 'assets': {}, 'current': 'p1',
         'references': {'R1': {'id': 'R1', 'kind': 'sheet', 'element_id': 'P1', 'status': 'approved', 'key': 'run-1/visuals/references/R1.png', 'sha256': 'sha-R1'},
                        'R9': {'id': 'R9', 'kind': 'sheet', 'element_id': 'P1', 'status': 'candidate', 'key': 'run-1/visuals/references/R9.png', 'sha256': 'sha-R9'}},
         'guides': {'S1': guide()}, 'take_checks': {}, 'preparations': {}, 'source': {'fps': 25, 'gaps': {}}}
    s.update(more)
    return s


class Store:
    def __init__(self):
        self.files = {}

    def get(self, k):
        return self.files[k]

    def put(self, k, data, mime=None):
        self.files[k] = data


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    monkeypatch.setattr(V, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 9.0, 'video_360p_inr_per_s': 3.0, 'usd_inr': 88.0})


@pytest.fixture
def held(monkeypatch):
    """One film held in memory: the session, its plan, the jobs queued, the snapshots saved, the record of generations, the cost limit."""
    box = {'queued': [], 'record': [], 'cap': None, 'rows': [], 'selected': [], 'store': Store()}

    def use(s, p, rows=()):
        box.update(s=s, p=p, rows=list(rows))
        monkeypatch.setattr(V, 'session_of', lambda *a, **k: box['s'])
        monkeypatch.setattr(V, 'save_session', lambda store, run, s_: box.update(s=s_))
        monkeypatch.setattr(V, 'current_plan', lambda *a, **k: box['p'])
        monkeypatch.setattr(V, '_accepted_shots', lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']])
        monkeypatch.setattr(V, 'locate', lambda store, s_, sid: (box['p'], box['p']['gaps'][0], box['p']['gaps'][0]['scenes'][0], next(sh for sh in box['p']['gaps'][0]['scenes'][0]['shots'] if sh['id'] == sid)))
        monkeypatch.setattr(V, 'load_json', lambda store, key: json.loads(box['store'].files[key]) if key in box['store'].files else {'kind': 'guide', 'placement': {'exact_seconds': 5.0}})
        monkeypatch.setattr(V, 'save_json', lambda store, key, doc: box['store'].put(key, json.dumps(doc).encode('utf-8')))
        monkeypatch.setattr(V, 'need_free', lambda *a, **k: None)
        monkeypatch.setattr(V, 'take_jobs', lambda conn, run, shot_id=None: [j for j in box['rows'] if not shot_id or j['unit'] == shot_id])

        def cap(conn, run, s_, amount, what):
            box.setdefault('asked', []).append(round(float(amount), 2))
            if box['cap'] is not None and amount > box['cap']:
                raise Problem(409, 'VISUALS_CAP', 'the cost limit is reached')
        monkeypatch.setattr(V, 'check_cap', cap)

        def queue(conn, run, shot_id, provider, request):
            jid = f'v{len(box["queued"]) + 1}'
            box['queued'].append({'id': jid, 'unit': shot_id, 'provider': provider, 'request': request})
            return jid
        monkeypatch.setattr(G, '_queue', queue)
        from app import generations
        monkeypatch.setattr(generations, 'add', lambda conn, run_id, shot_id, how, entry: box['record'].append(entry))
        monkeypatch.setattr(generations, 'closed', lambda *a, **k: None)
        monkeypatch.setattr(V, 'review_take', lambda conn, store, user, run, outputs, jid, decision, notes, timing, quote: box['s']['reviews'].setdefault(jid, []).append({'decision': decision, 'notes': notes}))
        monkeypatch.setattr(V, 'select_take', lambda conn, store, user, run, outputs, jid, quote, notes='', timing='', in_s=None: (box['selected'].append(jid), box['s']['selections'].update(S1={'job_id': jid}))[0])
        monkeypatch.setattr(C, 'picture', lambda store, run, s_, shot_id, p, people: {'id': p['id'], 'key': f"small/{p['id']}.jpg", 'sha256': 'sha-' + p['id'], 'mime_type': 'image/jpeg', 'job': p.get('job') or ''})
        return box
    return use


def answer(box, choice, words='', sid='S1'):
    return T.answer(None, box['store'], USER, RUN, [], sid, box['rows'], choice, 'the operator', words)


def send(box, body, sid='S1'):
    return C.send(None, box['store'], USER, RUN, [], sid, body)


def refused(fn):
    with pytest.raises((Problem, ValueError)) as e:
        fn()
    return getattr(e.value, 'message', None) or str(e.value)


def snap(box, n=-1):
    return json.loads(box['store'].files[box['queued'][n]['request']['request_key']])


EDIT = {'route': 'edit', 'reason': 'Only the poles are wrong; the rest is fine.', 'changes': ['Remove the bamboo poles on the left, for the whole video. The wall behind them is bare red brick.'],
        'keep': 'the mason and what he does, the street, the camera, the light and the timing'}
REMAKE = {'route': 'remake', 'reason': 'The first two seconds are right; the hand-over after them is wrong.', 'cut_s': 2.0,
          'pictures': [{'id': 'R1', 'job': 'the mason: his face, build and clothes'}], 'prompt': PROMPT}


# ---------- R1, R10, U15: the sizes, each one setting ----------

def test_the_first_take_is_360p_and_a_version_720p():
    assert VG.GUIDE['resolution'] == '360p' and C.VERSION_SIZE == '720p'
    assert (C.CLIP_MIN_S, C.CLIP_MAX_S, C.PICTURES_MAX, C.PICTURE_SIDE) == (1.0, 3.0, 6, 1536)


def test_only_a_video_at_the_version_size_can_go_in_the_film():
    assert not C.final(job('j1')) and C.final(job('j2', size='720p'))
    assert C.final(job('j0', size=None))   # U16: a take made before this change (no size on its job) is 720p


# ---------- section 7: the price follows the size ----------

def test_a_second_is_priced_by_its_size():
    assert V.video_price('360p') == 3.0 and V.video_price('720p') == 9.0 and V.video_price(None) == 9.0


def test_the_spend_counts_each_take_at_the_price_of_its_size(monkeypatch):
    rows = [{'provider': 'video', 'status': 'ready', 'request': {'duration_seconds': 5, 'resolution': '360p'}, 'cost': None},
            {'provider': 'video', 'status': 'ready', 'request': {'duration_seconds': 5, 'resolution': '720p'}, 'cost': None},
            {'provider': 'video', 'status': 'ready', 'request': {'duration_seconds': 5}, 'cost': None},          # made before this change: 720p
            {'provider': 'video', 'status': 'failed', 'request': {'duration_seconds': 5, 'resolution': '720p'}, 'cost': None}]   # E9: a failed call is not counted
    conn = type('Conn', (), {'execute': lambda self, sql, params=(): type('R', (), {'fetchall': lambda _: rows})()})()
    sp = V.visuals_spend(conn, RUN)
    assert sp['spent_inr'] == 5 * 3.0 + 5 * 9.0 + 5 * 9.0 and sp['take_seconds'] == 15.0


def test_the_plans_estimate_counts_the_first_take_and_its_full_size_video(monkeypatch):
    monkeypatch.setattr(V, 'image_price_inr', lambda run, *a, **k: 4.0)
    assert V.plan_estimate(RUN, {'images_estimated': 2, 'video_take_seconds': 10}) == 2 * 4.0 + 10 * (3.0 + 9.0)   # U17
    assert V.rerun_allowance(10, V.prices()) == round(10 * V.RERUN_SHARE * 9.0, 2)   # a correction is a 720p video


# ---------- R8, R9, R12: what goes to the provider ----------

class Sender(VP.Provider):
    def __init__(self):
        self.name, self.key, self.key_index, self.uploaded = 'google', 'k', 0, []

    def upload(self, data, mime='video/mp4'):
        self.uploaded.append(data)
        return 'files/abc'


def version(kind, **more):
    return {'kind': kind, 'model': 'gemini-omni-1.2-flash', 'aspect_ratio': '16:9', 'resolution': '720p', 'duration_seconds': 5, 'effective_prompt': 'the words',
            'source': {'key': 'take.mp4', 'sha256': 'a'}, 'pictures': [], **more}


def test_an_edit_sends_the_whole_video_and_the_words_and_no_picture():
    store, p = Store(), Sender()
    store.put('take.mp4', b'WHOLE')
    body = p.build(version('edit'), store)
    assert p.uploaded == [b'WHOLE'] and [i['type'] for i in body['input']] == ['video', 'text'] and body['input'][1]['text'] == 'the words'
    assert body['response_format'] == {'type': 'video', 'aspect_ratio': '16:9', 'resolution': '720p', 'duration': '5s'} and 'generation_config' not in body
    assert body['model'] == 'gemini-omni-1.2-flash' and body['background'] is True


def test_a_remake_sends_the_clip_the_pictures_and_the_words_as_reference_to_video(monkeypatch):
    store, p = Store(), Sender()
    store.put('small/R1.jpg', b'JPEG')
    monkeypatch.setattr(C, 'clip', lambda store_, snapshot: b'CLIP')
    body = p.build(version('remake', cut_s=2.0, pictures=[{'id': 'R1', 'key': 'small/R1.jpg', 'mime_type': 'image/jpeg'}]), store)
    assert p.uploaded == [b'CLIP'] and [i['type'] for i in body['input']] == ['video', 'image', 'text'] and body['input'][1]['mime_type'] == 'image/jpeg'
    assert body['generation_config'] == {'video_config': {'task': 'reference_to_video'}} and body['response_format']['resolution'] == '720p' and body['response_format']['duration'] == '5s'


def test_the_clip_is_cut_from_the_start_to_the_cut_with_no_sound():
    args = C.clip_args('ffmpeg', 'in.mp4', 'out.mp4', 2.5)
    assert args[0] == 'ffmpeg' and args[args.index('-t') + 1] == '2.5' and '-an' in args and args[-1] == 'out.mp4' and '-ss' not in args


def test_a_real_clip_is_two_seconds_long_and_kept_beside_the_request(tmp_path):
    """With ffmpeg on the machine: a 5 s video is cut to its first 2 s. Skipped where ffmpeg is not installed."""
    import shutil
    import subprocess
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('no ffmpeg on this machine')
    src = tmp_path / 'take.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=320x180:rate=24', '-pix_fmt', 'yuv420p', str(src)], check=True, timeout=120)
    store = Store()
    store.put('take.mp4', src.read_bytes())
    data = C.clip(store, {'source': {'key': 'take.mp4'}, 'cut_s': 2.0, 'clip_key': 'run-1/visuals/takes/x.clip.mp4'})
    out = tmp_path / 'clip.mp4'
    out.write_bytes(data)
    secs = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(out)], capture_output=True, text=True, check=True, timeout=60).stdout)
    assert abs(secs - 2.0) < 0.1 and store.files['run-1/visuals/takes/x.clip.mp4'] == data and data[4:8] == b'ftyp'


def test_the_edit_words_have_the_fixed_opening_each_change_as_a_line_and_what_stays():
    one = C.edit_text(['Remove the bamboo poles.'], 'the mason, the street, the camera, the light and the timing')
    assert one == 'Edit the video. Make only this change: Remove the bamboo poles.\n\nKeep everything else exactly the same: the mason, the street, the camera, the light and the timing.'
    two = C.edit_text(['Remove the poles.', 'The wall is a brick parapet.'], 'the ponds, the camera.')
    assert two == 'Edit the video. Make only these changes:\n1. Remove the poles.\n2. The wall is a brick parapet.\n\nKeep everything else exactly the same: the ponds, the camera.'


def test_the_copy_asks_for_the_same_video_at_full_detail_and_nothing_else_changed():
    """SK's test of 22 Nov 2026 (5 paid calls; vw2-archive/2026-11-22/upscale-test): "make no change" gave the 360p picture made bigger; these words
    gave a picture as detailed as a true 720p take on three videos, frame for frame on the input. The words are kept as tested."""
    assert C.copy_text() == ('Edit the video. Make only this change: the picture becomes true 720p footage with sharp, fine detail: skin, cloth, surfaces, textures and edges '
                             'as a camera records them at 720p. The video given is a small 360p picture; do not simply enlarge it.\n\n'
                             'Keep everything else exactly the same, frame for frame: the people and what they do, every object, the place, the camera, the light and the timing.')
    assert C.COPY_WAY == 'edit' and 'make no change' not in C.copy_text().lower() and 'same video again' not in C.copy_text()
    later = C.copy_text('720p', '1080p')   # the two sizes come from the settings: when a version becomes 1080p the words follow
    assert 'true 1080p footage' in later and 'at 1080p.' in later and 'a small 720p picture' in later and '360p' not in later


def test_the_remake_words_name_each_picture_then_the_prompt_then_one_continuous_shot():
    t = C.remake_text(5, ['the mason: his face', 'the roof tile'], PROMPT)
    assert t.index('Picture 1 = the mason: his face') < t.index('Picture 2 = the roof tile') < t.index(PROMPT) < t.index('One continuous shot.') and '5-second' in t


# ---------- U11: what the server refuses before anything is paid ----------

@pytest.mark.parametrize('change, said', [
    ({'route': 'guess'}, 'The route is one of'),
    ({'reason': 'ok'}, 'why this route'),
    ({'changes': []}, 'at least one change'),
    ({'keep': ''}, 'what must stay'),
    ({'pictures': [{'id': 'R1', 'job': 'the mason'}]}, 'An edit sends no picture'),
])
def test_an_edit_is_refused_with_no_change_no_keep_line_or_a_picture(change, said):
    assert said in ' '.join(C.problems({**EDIT, **change}, 5))


@pytest.mark.parametrize('change, said', [
    ({'cut_s': 3.5}, 'at most 3'),
    ({'cut_s': 0.5}, 'at least 1'),            # E5: the fault starts in the first second: not a remake
    ({'cut_s': 'two'}, 'a number of seconds'),
    ({'pictures': [{'id': f'R{n}', 'job': 'x'} for n in range(7)]}, 'at most 6'),   # E3
    ({'prompt': 'He takes the tile.'}, 'too short'),
    ({'prompt': PROMPT + ' 0.0–1.5 s: he lifts it. 1.5–3.0 s: he raps it.'}, 'a second for every move'),
    ({'prompt': PROMPT + ' The BLUE box is the mason.'}, 'box'),
    ({'prompt': PROMPT + ' ' + 'word ' * 400}, 'short'),
])
def test_a_remake_is_refused_over_its_limits(change, said):
    assert said in ' '.join(C.problems({**REMAKE, **change}, 5))


def test_a_remake_leaves_at_least_a_second_to_be_made_new():
    assert 'before its end' in ' '.join(C.problems({**REMAKE, 'cut_s': 3.0}, 3))   # E6: a 3 s video cut at 3 s leaves nothing
    assert C.problems({**REMAKE, 'cut_s': 2.0}, 3) == [] and C.problems(EDIT, 5) == [] and C.problems(REMAKE, 5) == []


def test_a_picture_is_made_smaller_before_it_is_sent(monkeypatch):
    from PIL import Image
    store, buf = Store(), BytesIO()
    Image.new('RGB', (3072, 1728), (200, 60, 40)).save(buf, format='PNG')
    store.put('run-1/visuals/references/R1.png', buf.getvalue())
    monkeypatch.setattr(V, 'person_picture_refused', lambda *a, **k: '')
    out = C.picture(store, RUN, session(), 'S1', {'id': 'R1', 'job': 'the mason: his face, build and clothes'}, {})
    with Image.open(BytesIO(store.files[out['key']])) as im:
        assert max(im.size) == 1536 and im.format == 'JPEG'
    assert out['mime_type'] == 'image/jpeg' and out['job'].startswith('the mason')
    assert 'not approved' in refused(lambda: C.picture(store, RUN, session(), 'S1', {'id': 'R9', 'job': 'the mason'}, {}))


# ---------- R2, A1, O2 to O5, O12: nobody checks a take; nothing is measured or set aside ----------

def test_a_take_is_offered_the_moment_it_is_made(held):
    s, p = session(), plan(shot('S1'))
    held(s, p)
    rows = [job('j1')]   # no record of frames yet, no look, no check
    assert T.offered(s, rows[0], NOW) and [i['state'] for i in T.expected(s, p, rows, NOW)] == ['made'] and T.complete(T.expected(s, p, rows, NOW))


def test_no_state_of_a_take_waits_for_a_check_and_nothing_names_a_checker(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    held(s, p)
    assert 'being checked by Claude' not in [i['state'] for i in T.expected(s, p, [job('j1')], NOW)]
    assert 'vw-take-look' not in T.starts(s, p, [job('j1')]) and 'checkers of the takes' not in json.dumps(T.W)
    for gone in ('look_lines', 'record', 'listed', 'due', 'asked', 'check_view', 'again_due'):
        assert not hasattr(T, gone), gone


def test_the_worker_keeps_only_the_frames_of_a_take_and_measures_nothing():
    from app import guide_worker as GW
    for gone in ('length_line', 'same_line', 'first_frame_line', 'continuous_line', 'jumps', 'blocked_by', 'released', 'scorecard', 'take_checks'):
        assert not hasattr(GW, gone), gone
    assert callable(GW.take_frames)


def test_a_look_sent_for_a_take_and_a_cause_are_refused_by_name():
    from app import pictures as P
    assert 'retired' in T.W['look_retired'] and 'design/223' in T.W['look_retired']
    assert 'retired' in G.CAUSE_RETIRED and 'vw guide correct' in G.CAUSE_RETIRED
    with pytest.raises(Problem) as e:
        G.cause_retired()
    assert e.value.status == 410 and not hasattr(G, 'set_cause') and not hasattr(G, 'LADDER') and not hasattr(P, 'TAKE_LOOK_HOW')


# ---------- R4, R13, A3: the page's line of a take ----------

def test_a_take_has_two_answers_accept_and_say_what_is_wrong(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    ln = T.line(box['store'], s, p, p['gaps'][0], p['gaps'][0]['scenes'][0]['shots'][0], 1, 1, box['rows'], NOW)
    assert [(b['label'], b['choice'], b['needs_words']) for b in ln['buttons']] == [('Accept', 'select', False), ('Say what is wrong', 'again', True)]
    assert 'check' not in ln['takes'][0] and 'compare' not in ln and 'full-size' in ln['buttons'][0]['say']   # accepted at 360p: its full-size video is made
    assert '₹' not in json.dumps(ln, ensure_ascii=False)   # no amount on the page


def test_a_version_is_shown_beside_the_video_it_was_made_from(held):
    s = session(take_checks={'j1': frames(), 'v1': frames()})
    s['guides']['S1']['corrections'] = [{'id': 'c1', 'job_id': 'j1', 'words': 'the poles', 'route': 'edit', 'jobs': ['v1']}]
    s['reviews']['j1'] = [{'decision': 'rejected', 'notes': 'the poles'}]
    p = plan(shot('S1'))
    box = held(s, p, [job('j1'), job('v1', size='720p', route='edit', from_job='j1')])
    ln = T.line(box['store'], s, p, p['gaps'][0], p['gaps'][0]['scenes'][0]['shots'][0], 1, 1, box['rows'], NOW)
    assert ln['compare'] == {'from': 1, 'new': 2, 'play': 'Play both together'} and ln['takes'][1]['how'] == 'An edit of take 1.' and ln['takes'][1]['size'] == '720p'
    assert [b['choice'] for b in ln['buttons']] == ['select', 'again', 'old:1'] and 'full-size' not in ln['buttons'][0]['say']   # a 720p video goes in the film
    assert not any(b.get('sure') for b in ln['buttons']) and ln['buttons'][2]['label'] == 'Use take 1 after all'   # SK, 22 Nov 2026: one click, no second question (the answer can be undone)


def test_the_shot_before_is_shown_by_its_last_picture(held):
    s = session(take_checks={'j0': frames(), 'j1': frames()}, selections={'S0': {'job_id': 'j0', 'take': {'sha256': 'x'}}})
    s['guides']['S0'] = guide()
    p = plan(shot('S0', end=125), shot('S1', start=125, end=250), shot('S2', start=250, end=375))
    s['selections']['S2'] = {'job_id': 'j1', 'take': {'sha256': 'y'}}
    held(s, p)
    before, after = T._beside(s, p, p['gaps'][0], p['gaps'][0]['scenes'][0]['shots'][1], [])
    assert before[0]['_key'] == 'f/10.jpg' and after[0]['_key'] == 'f/0.jpg'   # A3: the picture the cut leaves from; the picture it arrives at


# ---------- R5, R12, U1, U3, A4: accept ----------

def test_accepting_a_360p_take_orders_its_720p_copy_and_puts_nothing_in_the_film(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'select')
    q = box['queued'][0]
    assert box['selected'] == [] and box['s']['selections'] == {} and box['s']['reviews']['j1'][-1]['decision'] == 'accepted'
    assert q['provider'] == 'video' and q['request']['resolution'] == '720p' and q['request']['route'] == 'copy' and q['request']['from_job'] == 'j1' and q['request']['duration_seconds'] == 5
    sn = snap(box)
    assert sn['kind'] == 'edit' and sn['source'] == {'job_id': 'j1', 'key': 'run-1/visuals/takes/j1.mp4', 'sha256': 'j1'.ljust(64, '0')} and sn['effective_prompt'] == C.copy_text() and sn['pictures'] == []
    assert box['asked'] == [5 * 9.0]   # U2: the cost limit is asked at the 720p price
    c = box['s']['guides']['S1']['corrections'][0]
    assert c['route'] == 'copy' and c['jobs'] == ['v1'] and box['record'][-1]['kind'] == 'version sent' and box['record'][-1]['route'] == 'copy'


def test_accepting_a_720p_video_puts_it_in_the_film(held):
    s, p = session(take_checks={'j1': frames(), 'v1': frames()}), plan(shot('S1'))
    s['guides']['S1']['corrections'] = [{'id': 'c1', 'job_id': 'j1', 'route': 'copy', 'jobs': ['v1']}]
    box = held(s, p, [job('j1'), job('v1', size='720p', route='copy', from_job='j1')])
    answer(box, 'select')
    assert box['selected'] == ['v1'] and box['queued'] == []


def test_a_720p_take_made_before_this_change_is_accepted_as_it_is(held):
    s, p = session(take_checks={'j1': {'guide': True, 'blocked': None, 'scorecard': [{'line': 'people', 'state': 'Fail'}], 'not_read': True, 'frames': [], 'sheet_key': None}}), plan(shot('S1'))
    box = held(s, p, [job('j1', size=None)])   # U16: VW-24's takes
    assert [i['state'] for i in T.expected(s, p, box['rows'], NOW)] == ['made']
    answer(box, 'select')
    assert box['selected'] == ['j1'] and box['queued'] == []


def test_the_same_accept_twice_orders_one_copy(held):
    s, p = session(), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'select')
    assert 'already' in refused(lambda: answer(box, 'select')) and len(box['queued']) == 1   # E16


def test_reject_as_an_answer_is_retired_by_name(held):
    s, p = session(), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    assert 'retired' in refused(lambda: answer(box, 'reject', 'bad'))


# ---------- R4 to R7, U7: say what is wrong; the assistant chooses the route ----------

def test_the_operators_words_are_kept_and_nothing_is_sent_until_the_route_is_chosen(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    assert 'what is wrong' in refused(lambda: answer(box, 'again', ' '))
    answer(box, 'again', 'There are bamboo poles on the left; there should be none.')
    c = box['s']['guides']['S1']['corrections'][0]
    assert box['queued'] == [] and c['job_id'] == 'j1' and c['words'].startswith('There are bamboo poles') and 'route' not in c
    assert box['s']['reviews']['j1'][-1] == {'decision': 'rejected', 'notes': 'There are bamboo poles on the left; there should be none.'}
    assert [i['state'] for i in T.expected(box['s'], p, box['rows'], NOW)] == ['being corrected'] and not T.complete(T.expected(box['s'], p, box['rows'], NOW))   # U8
    due = C.due(box['s'], p, box['rows'])
    assert 'bamboo poles' in due and 'vw guide corrections' in due and 'S1' in due


def test_the_rule_for_the_route_is_one_text_and_it_is_given_with_what_the_assistant_needs(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'again', 'The poles must go.')
    out = C.listed(box['store'], box['s'], p, box['rows'])
    row = out['corrections'][0]
    assert out['rule'] is C.RULE and all(r in C.RULE for r in ('edit', 'remake', 'both', 'first_take', 'none')) and 'cut earlier' in C.RULE
    assert row['shot_id'] == 'S1' and row['words'] == 'The poles must go.' and len(row['frames']) == 11 and row['sheet'] == 'f/sheet.jpg' and row['seconds'] == 5
    assert row['take_words'].startswith('ONE action only') and row['still_words'].startswith('A mason at a wall') and row['pictures'] == [{'id': 'R1', 'kind': 'sheet', 'element_id': 'P1', 'key': 'run-1/visuals/references/R1.png'}]


def test_an_edit_is_sent_as_one_720p_call_and_its_route_and_reason_are_recorded(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'again', 'The poles must go.')
    out = send(box, EDIT)
    sn, c = snap(box), box['s']['guides']['S1']['corrections'][0]
    assert sn['kind'] == 'edit' and sn['effective_prompt'] == C.edit_text(EDIT['changes'], EDIT['keep']) and sn['resolution'] == '720p' and sn['source']['job_id'] == 'j1'
    assert box['queued'][0]['request']['route'] == 'edit' and c['route'] == 'edit' and c['reason'] == EDIT['reason'] and c['jobs'] == ['v1'] and c['by_route'] == 'Op'
    rec = box['record'][-1]
    assert rec['kind'] == 'version sent' and rec['route'] == 'edit' and rec['reason'] == EDIT['reason'] and rec['words'] == 'The poles must go.' and rec['from_job'] == 'j1' and rec['prompt'] == sn['effective_prompt']
    assert '5 s' in out['tell'] and '₹45' in out['tell'] and C.due(box['s'], p, box['rows'] + [job('v1', status='queued', size='720p')]) == ''


def test_a_remake_is_sent_with_its_cut_its_pictures_and_its_short_prompt(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'again', 'He takes the tile far too slowly.')
    send(box, REMAKE)
    sn = snap(box)
    assert sn['kind'] == 'remake' and sn['cut_s'] == 2.0 and sn['pictures'] == [{'id': 'R1', 'key': 'small/R1.jpg', 'sha256': 'sha-R1', 'mime_type': 'image/jpeg', 'job': 'the mason: his face, build and clothes'}]
    assert sn['effective_prompt'] == C.remake_text(5, ['the mason: his face, build and clothes'], PROMPT) and sn['duration_seconds'] == 5 and sn['clip_key'].endswith('.clip.mp4')
    assert box['record'][-1]['cut_s'] == 2.0 and box['record'][-1]['pictures'] == ['R1']


def test_a_route_is_refused_when_no_correction_waits_and_a_faulty_one_sends_nothing(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    assert 'No correction' in refused(lambda: send(box, EDIT))
    answer(box, 'again', 'The poles must go.')
    assert 'An edit sends no picture' in refused(lambda: send(box, {**EDIT, 'pictures': [{'id': 'R1', 'job': 'x'}]})) and box['queued'] == []


# ---------- A5, E1: both kinds of fault: the edit, then the remake from the edited video, in a row ----------

BOTH = {**REMAKE, **{k: EDIT[k] for k in ('changes', 'keep')}, 'route': 'both', 'reason': 'The poles are wrong and the hand-over is wrong.'}


def test_both_faults_send_the_edit_first_and_the_remake_when_the_edit_is_back(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'again', 'Poles, and the hand-over is slow.')
    out = send(box, BOTH)
    assert len(box['queued']) == 1 and snap(box)['kind'] == 'edit' and box['asked'][-1] == 2 * 5 * 9.0 and 'two' in out['tell']   # the cost limit is asked for both calls
    waiting = [i['state'] for i in T.expected(box['s'], p, box['rows'] + [job('v1', size='720p', route='both', from_job='j1')], NOW)]
    assert waiting == ['being corrected']   # the in-between video is not offered
    C.landed(None, box['store'], RUN, box['s'], job('v1', size='720p', route='both', from_job='j1'), True)
    sn = snap(box)
    assert len(box['queued']) == 2 and sn['kind'] == 'remake' and sn['source']['job_id'] == 'v1' and sn['source']['key'] == 'run-1/visuals/takes/v1.mp4'
    assert box['s']['guides']['S1']['corrections'][0]['jobs'] == ['v1', 'v2'] and 'then' not in box['s']['guides']['S1']['corrections'][0]


def test_the_remake_is_not_sent_when_the_edit_failed(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'again', 'Poles, and the hand-over is slow.')
    send(box, BOTH)
    C.landed(None, box['store'], RUN, box['s'], job('v1', status='failed', size='720p', route='both', from_job='j1'), False)
    assert len(box['queued']) == 1


def test_the_page_compares_the_final_video_of_both_with_the_one_the_operator_answered(held):
    s = session(take_checks={'j1': frames(), 'v1': frames(), 'v2': frames()})
    s['guides']['S1']['corrections'] = [{'id': 'c1', 'job_id': 'j1', 'words': 'x', 'route': 'both', 'jobs': ['v1', 'v2']}]
    p = plan(shot('S1'))
    box = held(s, p, [job('j1'), job('v1', size='720p', route='both', from_job='j1'), job('v2', size='720p', route='both', from_job='v1')])
    ln = T.line(box['store'], s, p, p['gaps'][0], p['gaps'][0]['scenes'][0]['shots'][0], 1, 1, box['rows'], NOW)
    assert ln['compare']['from'] == 1 and ln['compare']['new'] == 3


# ---------- A1, A2, E7, E8, E20: the first take again; no route ----------

def test_the_first_take_is_made_again_when_nothing_is_usable(held, monkeypatch):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    shot_ = {}
    monkeypatch.setattr(G, 'shoot', lambda conn, store, user, run, outputs, sid, quote, again=False, same=False: shot_.update(sid=sid, quote=quote, same=same) or {'job_id': 'j2', 'seconds': 5})
    monkeypatch.setattr(G, 'set_prompt', lambda conn, store, user, run, outputs, sid, words: shot_.update(words=words))
    answer(box, 'again', 'It is still the boxes.')
    send(box, {'route': 'first_take', 'reason': 'The video is the layout itself: nothing of it is usable.'})
    c = box['s']['guides']['S1']['corrections'][0]
    assert shot_ == {'sid': 'S1', 'quote': 'It is still the boxes.', 'same': True} and c['route'] == 'first_take' and c['jobs'] == ['j2']


def test_our_own_words_are_corrected_when_they_asked_for_the_fault(held, monkeypatch):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    said = {}
    monkeypatch.setattr(G, 'set_prompt', lambda conn, store, user, run, outputs, sid, words: said.update(words=words))
    answer(box, 'again', 'The poles must go.')
    send(box, {**EDIT, 'our_words': {'what': 'The still\'s words and the take words asked for bamboo poles.', 'take_words': 'ONE action only: he lays the brick. No poles stand at the wall.'}})
    c = box['s']['guides']['S1']['corrections'][0]
    assert said['words'].endswith('No poles stand at the wall.') and c['our_words']['what'].startswith('The still') and box['record'][-1]['asked_by_our_words'] is True   # R11, A2
    assert len(box['queued']) == 1   # the still is not made again, the plan is not changed: one edit


def test_no_route_pays_for_nothing_and_the_shot_waits_in_the_chat(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'again', 'Not good.')
    out = send(box, {'route': 'none', 'reason': 'The words do not say what should be different.', 'say': 'What should be different in this shot?'})
    assert box['queued'] == [] and out['tell'] == 'What should be different in this shot?'
    items = T.expected(box['s'], p, box['rows'], NOW)
    assert items[0]['state'] == 'waiting for you in the chat' and items[0].get('aside') and C.due(box['s'], p, box['rows']) == ''


def test_a_correction_withdrawn_leaves_the_video_to_be_answered_again(held):
    s, p = session(take_checks={'j1': frames()}), plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'again', 'Not good.')
    send(box, {'route': 'none', 'reason': 'The operator withdrew the correction.', 'withdrawn': True})
    assert [i['state'] for i in T.expected(box['s'], p, box['rows'], NOW)] == ['made'] and box['queued'] == []


# ---------- U5, U6, E13, E15: which video ----------

def test_a_correction_starts_from_the_video_the_operator_answered_or_the_one_named(held):
    s = session(take_checks={'j1': frames(), 'v1': frames()})
    s['guides']['S1']['corrections'] = [{'id': 'c1', 'job_id': 'j1', 'words': 'x', 'route': 'edit', 'jobs': ['v1']}]
    p = plan(shot('S1'))
    box = held(s, p, [job('j1'), job('v1', size='720p', route='edit', from_job='j1')])
    answer(box, 'again', 'Now the wall is wrong; the first one was better.')
    assert 'not a video of this shot' in refused(lambda: send(box, {**EDIT, 'from': 'zz'})) and box['queued'] == []
    send(box, {**EDIT, 'from': 'j1'})
    assert snap(box)['source']['job_id'] == 'j1' and box['s']['guides']['S1']['corrections'][1]['job_id'] == 'v1'


def test_an_earlier_720p_video_can_be_accepted_after_all_and_an_earlier_360p_one_gets_its_copy(held):
    s = session(take_checks={'j1': frames(), 'v1': frames(), 'v2': frames()})
    s['guides']['S1']['corrections'] = [{'id': 'c1', 'job_id': 'j1', 'words': 'x', 'route': 'edit', 'jobs': ['v1']}, {'id': 'c2', 'job_id': 'v1', 'words': 'y', 'route': 'edit', 'jobs': ['v2']}]
    p = plan(shot('S1'))
    box = held(s, p, [job('j1'), job('v1', size='720p', from_job='j1'), job('v2', size='720p', from_job='v1')])
    answer(box, 'old:2')
    assert box['selected'] == ['v1']
    answer(box, 'old:1')
    assert box['queued'][-1]['request']['route'] == 'copy' and box['queued'][-1]['request']['from_job'] == 'j1'


def test_an_accepted_shot_can_be_corrected_while_the_film_is_in_this_step(held):
    s = session(take_checks={'j1': frames(), 'v1': frames()}, selections={'S1': {'job_id': 'v1'}})
    p = plan(shot('S1'))
    box = held(s, p, [job('j1'), job('v1', size='720p', from_job='j1')])
    assert [i['state'] for i in T.expected(s, p, box['rows'], NOW)] == ['answered']
    C.reopen(None, box['store'], USER, RUN, [], 'S1', 'The roof is wrong after all.', 'the operator')   # E13
    assert box['s']['guides']['S1']['corrections'][-1]['job_id'] == 'v1' and box['s']['reviews']['v1'][-1]['decision'] == 'rejected'


def test_no_correction_while_a_video_of_the_shot_is_being_made(held):
    s, p = session(), plan(shot('S1'))
    box = held(s, p, [job('j1'), job('v1', status='running', size='720p')])
    assert 'being made' in refused(lambda: answer(box, 'again', 'The roof is wrong.'))


# ---------- R3, E9 to E11, O11: a call that fails at the provider ----------

def test_the_providers_own_status_and_message_are_kept(monkeypatch):
    class Reply:
        is_success, status_code, text = False, 429, '{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current quota."}}'

        def read(self):
            return self.text.encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(VP.httpx, 'stream', lambda *a, **k: Reply())
    p = Sender()
    p.key_index = None
    with pytest.raises(Problem) as e:
        p.submit({}, 'id')
    assert e.value.extra['http_status'] == 429 and 'RESOURCE_EXHAUSTED' in e.value.extra['provider_message'] and 'k' != e.value.extra['provider_message']
    assert VP.provider_message({'status': 'failed', 'error': {'code': 'RESOURCE_EXHAUSTED', 'message': 'quota'}}) == 'RESOURCE_EXHAUSTED: quota'
    assert VP.provider_message({'status': 'failed'}) == ''


def test_a_failed_version_is_shown_with_the_providers_message_and_the_earlier_video_stays(held):
    s = session(take_checks={'j1': frames()})
    s['guides']['S1']['corrections'] = [{'id': 'c1', 'job_id': 'j1', 'words': 'the poles', 'route': 'edit', 'jobs': ['v1']}]
    p = plan(shot('S1'), shot('S2', start=125, end=250))
    s['guides']['S2'] = guide()
    rows = [job('j1'), job('v1', status='failed', size='720p', route='edit', from_job='j1', error='The provider ended the call as failed: RESOURCE_EXHAUSTED: quota'), job('k1', sid='S2')]
    box = held(s, p, rows)
    items = T.expected(s, p, rows, NOW)
    assert [i['state'] for i in items] == ['made', 'made'] and T.complete(items)   # E11: the others are shown as usual
    ln = T.line(box['store'], s, p, p['gaps'][0], p['gaps'][0]['scenes'][0]['shots'][0], 1, 2, rows, NOW)
    assert 'RESOURCE_EXHAUSTED' in ln['failed'] and [b['choice'] for b in ln['buttons']] == ['select', 'again', 'resend'] and ln['buttons'][2]['label'] == 'Send it again'


def test_a_failed_version_is_sent_again_once_and_not_twice(held):
    s = session(take_checks={'j1': frames()})
    p = plan(shot('S1'))
    box = held(s, p, [job('j1')])
    answer(box, 'again', 'The poles must go.')
    send(box, EDIT)
    box['rows'].append(job('v1', status='failed', size='720p', route='edit', from_job='j1', error='failed', request_key=box['queued'][0]['request']['request_key']))
    answer(box, 'resend')
    assert len(box['queued']) == 2 and box['queued'][1]['request']['request_key'] == box['queued'][0]['request']['request_key'] and box['s']['guides']['S1']['corrections'][0]['jobs'] == ['v1', 'v2']
    box['rows'].append(job('v2', status='failed', size='720p', route='edit', from_job='j1', error='failed'))
    ln = T.line(box['store'], box['s'], p, p['gaps'][0], p['gaps'][0]['scenes'][0]['shots'][0], 1, 1, box['rows'], NOW)
    assert 'resend' not in [b['choice'] for b in ln['buttons']] and 'once' in refused(lambda: answer(box, 'resend'))


def test_a_first_take_that_failed_is_listed_apart_with_the_providers_message(held):
    s, p = session(), plan(shot('S1'))
    held(s, p)
    rows = [job('j1', status='failed', error='The provider refused the call (HTTP 429): RESOURCE_EXHAUSTED')]
    items = T.expected(s, p, rows, NOW)
    assert items[0]['state'] == 'could not be made' and 'RESOURCE_EXHAUSTED' in T.coming(items, rows)[0]['note']


# ---------- E12: the cost limit in the middle of a run ----------

def test_at_the_cost_limit_a_video_waits_and_goes_when_the_limit_is_raised(held):
    s, p = session(), plan(shot('S1'), shot('S2', start=125, end=250))
    s['guides']['S2'] = guide()
    box = held(s, p, [job('j1'), job('k1', sid='S2')])
    answer(box, 'select', sid='S1')
    box['cap'] = 10
    answer(box, 'select', sid='S2')   # refused by the limit: kept, not lost, not raised to the operator as an error
    c = box['s']['guides']['S2']['corrections'][0]
    assert len(box['queued']) == 1 and 'cost limit' in c['waiting'] and 'jobs' not in c
    items = T.expected(box['s'], p, box['rows'], NOW)
    assert items[1]['state'] == 'waiting for the cost limit' and items[1].get('aside') and 'cost limit' in C.due(box['s'], p, box['rows'])
    box['cap'] = None
    assert C.go_waiting(None, box['store'], RUN, box['s']) == 1
    assert len(box['queued']) == 2 and box['queued'][1]['unit'] == 'S2' and 'waiting' not in box['s']['guides']['S2']['corrections'][0]


# ---------- U1: the one line after done ----------

def test_the_chat_says_once_what_was_ordered_with_its_seconds_and_amount(held):
    s, p = session(), plan(shot('S1'), shot('S2', start=125, end=250))
    s['guides']['S2'] = guide()
    box = held(s, p, [job('j1'), job('k1', sid='S2')])
    answer(box, 'select', sid='S1')
    answer(box, 'again', 'The poles must go.', sid='S2')
    said = C.ordered(box['s'], p)
    assert '1 full-size video' in said and '1 correction' in said and '10 s' in said and '₹90' in said
    assert C.ordered(box['s'], p) == ''


# ---------- E17, F7 ----------

def test_a_video_made_for_an_earlier_plan_cannot_be_accepted(held):
    s, p = session(), plan(shot('S1'))
    box = held(s, p, [job('j1', plan_digest='another plan')])
    assert [i['state'] for i in T.expected(s, p, box['rows'], NOW)] == ['must be made again (the plan changed)']
    assert 'earlier plan' in refused(lambda: answer(box, 'select'))


def test_a_version_as_long_as_its_take_starts_in_its_slot_as_a_take_does():
    j = {'result': {'evidence': {'duration_seconds': 6.0}}}
    assert V.take_in_point({'kind': 'edit', 'placement': {'exact_seconds': 5.0}}, j, None) == {'in_s': 0.5} == V.take_in_point({'kind': 'guide', 'placement': {'exact_seconds': 5.0}}, j, None)
