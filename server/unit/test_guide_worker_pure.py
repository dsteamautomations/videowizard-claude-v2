"""Integration steps B to D: the worker side of the guide route (app/guide_worker.py), the request to Gemini (app/video_providers.py) and the
reading lines of a guide take (app/image_check.py). Blender, ffmpeg and both providers are faked: no render, no paid call."""
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app import guide_worker as W, image_check as IC, video_providers as VP, visuals_stage as VS
from app.errors import Problem
from test_guide_spec_pure import home_walk
from test_visuals_stage_pure import FakeStore


def png(colour, size=(64, 36), box=None):
    im = Image.new('RGB', size, colour)
    if box:
        im.paste((250, 250, 250), box)
    buf = BytesIO()
    im.save(buf, format='PNG')
    return buf.getvalue()


@pytest.fixture
def blender(monkeypatch, tmp_path):
    """Blender faked: it writes one small picture per asked frame and records each call."""
    calls = []

    def run(spec_path, outdir, frames, samples, look='eevee'):
        assert json.loads(Path(spec_path).read_text(encoding='utf-8'))['recipe'] == 'walker'
        calls.append({'frames': list(frames), 'samples': samples, 'outdir': Path(outdir).name, 'look': look})
        Path(outdir).mkdir(parents=True, exist_ok=True)
        for f in frames:
            (Path(outdir) / f'g{f:04d}.png').write_bytes(png((10 * samples, 40, 90)))
    monkeypatch.setattr(W, 'run_blender', run)
    monkeypatch.setattr(W, 'spool', lambda: tmp_path)
    store = FakeStore({'run-1/visuals/guides/abc/scene.json': home_walk()})
    monkeypatch.setattr(W, 'storage', lambda: store)
    return calls, store, tmp_path


def job(kind, **req):
    return {'id': 'j1', 'run_id': 'run-1', 'request': {'kind': kind, 'shot_id': 'VS1', 'sha256': 'abc', 'spec_key': 'run-1/visuals/guides/abc/scene.json', **req}}


# ---------- renders ----------

def test_check_frames_are_rendered_stored_and_joined_into_one_strip_and_the_folder_is_deleted(blender):
    calls, store, tmp = blender
    status, result, error, cost, retry = W.process(job('guide-frames', frames=[1, 75, 150]))
    assert status == 'ready' and error is None and cost == {'provider': 'guide', 'inr': 0}
    assert calls == [{'frames': [1, 75, 150], 'samples': 1, 'outdir': 'check', 'look': 'flat'}]   # layout B: the check frames show what the video shows
    assert [f['key'] for f in result['frames']] == [f'run-1/visuals/guides/abc/check-{n:04d}.png' for n in (1, 75, 150)]
    strip = Image.open(BytesIO(store.files[result['strip_key']]))
    assert strip.height == 240 and strip.width > 3 * 240 and not (tmp / 'j1').exists()


def test_a_guide_is_rendered_in_chunks_with_the_claim_renewed_and_frame_one_again_at_full_quality(blender, monkeypatch):
    calls, store, tmp = blender
    renewed, encoded = [], []

    def ffmpeg(cmd, **kw):
        encoded.append(cmd)
        Path(cmd[-1]).write_bytes(b'\x00\x00\x00\x18ftypmp42-guide')
        return type('R', (), {'returncode': 0, 'stderr': ''})()
    monkeypatch.setattr(W.subprocess, 'run', ffmpeg)
    status, result, error, cost, retry = W.process(job('guide-render', seconds=5), renew=lambda: renewed.append(1))
    assert status == 'ready', error
    assert calls[0] == {'frames': [1], 'samples': 16, 'outdir': 'first', 'look': 'eevee'}
    assert [c['frames'][0] for c in calls[1:]] == [1, 31, 61, 91, 121] and calls[-1]['frames'][-1] == 150 and all(c['samples'] == 1 for c in calls[1:])
    assert len(renewed) == 5 and '-framerate' in encoded[0] and encoded[0][encoded[0].index('-framerate') + 1] == '30'
    assert result['guide_key'] == 'run-1/visuals/guides/abc/guide.mp4' and store.files[result['guide_key']].endswith(b'guide') and result['frames'] == 150
    assert Image.open(BytesIO(store.files[result['frame1_key']])).getpixel((0, 0))[0] == 160   # the 16-sample frame, not the fast one
    assert not (tmp / 'j1').exists()


def test_a_blender_fault_fails_the_job_with_its_reason_and_leaves_nothing_behind(blender, monkeypatch):
    calls, store, tmp = blender

    def broken(*a, **kw):
        raise RuntimeError('Blender did not build the guide: GUIDE FAILED: KeyError: colour')
    monkeypatch.setattr(W, 'run_blender', broken)
    status, result, error, cost, retry = W.process(job('guide-frames', frames=[1]))
    assert status == 'failed' and 'GUIDE FAILED: KeyError: colour' in error and cost is None and not (tmp / 'j1').exists()
    assert not [k for k in store.files if 'check-' in k]


def test_blender_succeeds_only_on_its_done_line_and_with_every_frame_on_disk(monkeypatch, tmp_path):
    def proc(stdout, code=0):
        return lambda cmd, **kw: type('R', (), {'returncode': code, 'stdout': stdout, 'stderr': 'boom'})()
    monkeypatch.setattr(W.subprocess, 'run', proc('FRAMETIME 1 4.0\nGUIDE FAILED: an unknown scene\n', 1))
    with pytest.raises(RuntimeError, match='an unknown scene'):
        W.run_blender(tmp_path / 's.json', tmp_path / 'o', [1], 1)
    monkeypatch.setattr(W.subprocess, 'run', proc('Blender quit\n'))   # exit 0 and no "GUIDE DONE": never taken as a finished guide
    with pytest.raises(RuntimeError, match='did not build the guide'):
        W.run_blender(tmp_path / 's.json', tmp_path / 'o', [1], 1)
    monkeypatch.setattr(W.subprocess, 'run', proc('GUIDE DONE 2\n'))   # says done, wrote nothing
    with pytest.raises(RuntimeError, match='no picture for frames'):
        W.run_blender(tmp_path / 's.json', tmp_path / 'o', [1, 2], 1)


def test_the_blender_call_runs_the_servers_own_script_in_software_graphics(monkeypatch, tmp_path):
    seen = {}

    def run(cmd, **kw):
        seen.update(cmd=cmd, env=kw['env'], timeout=kw['timeout'])
        (tmp_path / 'o').mkdir()
        (tmp_path / 'o' / 'g0001.png').write_bytes(b'x')
        return type('R', (), {'returncode': 0, 'stdout': 'GUIDE DONE 1\n', 'stderr': ''})()
    monkeypatch.setattr(W.subprocess, 'run', run)
    W.run_blender(tmp_path / 's.json', tmp_path / 'o', [1], 16)
    cmd = seen['cmd']
    assert cmd[1:5] == ['-b', '--factory-startup', '--gpu-backend', 'opengl'] and cmd[6].endswith('guide_scene.py') and Path(cmd[6]).exists()
    assert cmd[-3:] == ['frames=1', 'samples=16', 'look=eevee'] and seen['env']['LIBGL_ALWAYS_SOFTWARE'] == '1' and seen['timeout'] == 900


# ---------- the overlay ----------

def test_the_overlay_draws_the_guides_edges_in_red_over_the_still_with_both_pictures_below():
    frame = png((30, 30, 30), (128, 72), box=(40, 20, 80, 60))   # one bright box on a dark ground: its outline is the edge
    still = png((90, 120, 90), (256, 144))
    out = Image.open(BytesIO(W.overlay(frame, still))).convert('RGB')
    assert out.size == (256, 144 + 72)
    r, g, b = out.getpixel((80, 80))    # on the box's left edge (x 40 of 128 scaled to 256), mid height
    assert r > 200 and g < 90 and b < 90
    r, g, b = out.getpixel((10, 10))    # away from any edge: the still shows through
    assert abs(r - 90) < 25 and abs(g - 120) < 25
    assert out.getpixel((10, 200))[0] < 80   # below: the guide frame, small


# ---------- design/223 (SK, 22 Nov 2026): nothing is measured on a take ----------
# The tests of the checks that set a returned clip aside (as long as the guide, real footage, the first frame against the still) and of the
# scorecard are removed with the code they tested (design/35 rows 319, 320, 327); `test_design223_take_process_pure` pins that they are gone.

def test_a_guide_take_is_read_against_its_own_lines_never_frozen_person_or_surroundings_move():
    lines = IC.take_lines_for({'kind': 'guide', 'ambient': 'leaves stir', 'camera_move': ''})
    names = [l['check'] for l in lines]
    assert names == ['people', 'the action', 'objects', 'bodies and contact', 'the place and the light']
    assert not any('frozen' in l['pass_when'] or 'ambient' in l['pass_when'] for l in lines)
    old = [l['check'] for l in IC.take_lines_for({'ambient': 'leaves stir'})]
    assert 'frozen person' in old and 'surroundings move' in old   # a take made the older way is read as before


# ---------- the request to Gemini ----------

class Reply:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body or {}, headers or {}
        self.is_success = 200 <= status < 300

    def json(self):
        return self._body


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(VP, 'configured', lambda name: 'the-key')
    monkeypatch.setattr(VP.time if hasattr(VP, 'time') else __import__('time'), 'sleep', lambda s: None)
    return VP.Provider('google')


def test_the_guide_is_uploaded_on_the_providers_own_key_and_waited_on(provider, monkeypatch):
    posts, gets = [], []
    states = iter(['PROCESSING', 'ACTIVE'])

    def post(url, **kw):
        posts.append((url, kw))
        if 'upload/v1beta/files' in url:
            return Reply(headers={'x-goog-upload-url': 'https://up.example/session'})
        return Reply(body={'file': {'name': 'files/abc', 'state': 'PROCESSING'}})

    def get(url, **kw):
        gets.append(url)
        return Reply(body={'name': 'files/abc', 'state': next(states), 'uri': 'https://files.example/abc'})
    monkeypatch.setattr(VP.httpx, 'post', post)
    monkeypatch.setattr(VP.httpx, 'get', get)
    assert provider.upload(b'guide-bytes') == 'https://files.example/abc'
    start, send = posts
    assert start[1]['headers']['x-goog-api-key'] == 'the-key' and start[1]['headers']['X-Goog-Upload-Header-Content-Length'] == '11' and start[1]['headers']['X-Goog-Upload-Command'] == 'start'
    assert send[0] == 'https://up.example/session' and send[1]['content'] == b'guide-bytes' and send[1]['headers']['X-Goog-Upload-Command'] == 'upload, finalize'
    assert len(gets) == 2 and gets[0].endswith('/v1beta/files/abc')


def test_the_providers_cap_at_the_upload_is_named_as_the_cap_and_nothing_is_sent(provider, monkeypatch):
    monkeypatch.setattr(VP.httpx, 'post', lambda url, **kw: Reply(429))
    with pytest.raises(Problem) as e:
        provider.upload(b'x')
    assert 'spend cap or rate limit' in e.value.message and 'Nothing was charged' in e.value.message


def test_a_stuck_or_failed_upload_is_reported_and_is_not_a_take(provider, monkeypatch):
    monkeypatch.setattr(VP.httpx, 'post', lambda url, **kw: Reply(headers={'x-goog-upload-url': 'https://up.example/s'}) if 'upload/v1beta' in url else Reply(body={'file': {'name': 'files/a', 'state': 'FAILED'}}))
    with pytest.raises(Problem) as e:
        provider.upload(b'x')
    assert 'did not finish (state FAILED)' in e.value.message and 'no take was made' in e.value.message
    monkeypatch.setattr(VP.httpx, 'post', lambda url, **kw: Reply(500))
    with pytest.raises(Problem) as e:
        provider.upload(b'x')
    assert 'HTTP 500' in e.value.message


def test_the_request_carries_the_guide_then_the_still_then_the_words_and_the_length_in_the_request(provider, monkeypatch):
    monkeypatch.setattr(VP.Provider, 'upload', lambda self, data, mime='video/mp4': 'https://files.example/' + data.decode())
    store = FakeStore({'g.mp4': b'guide', 's.png': b'still'})
    snap = {'kind': 'guide', 'model': 'gemini-omni-1.2-flash', 'guide': {'key': 'g.mp4'}, 'start_image': {'key': 's.png', 'mime_type': 'image/png'}, 'effective_prompt': 'Edit the video. …',
            'aspect_ratio': '16:9', 'resolution': '720p', 'duration_seconds': 7}
    body = provider.build(snap, store)
    assert [p['type'] for p in body['input']] == ['video', 'image', 'text'] and body['input'][0] == {'type': 'video', 'uri': 'https://files.example/guide'}
    assert body['input'][2]['text'] == 'Edit the video. …' and body['response_format'] == {'type': 'video', 'aspect_ratio': '16:9', 'resolution': '720p', 'duration': '7s'}
    assert body['model'] == 'gemini-omni-1.2-flash' and body['background'] is True and body['store'] is True and 'task' not in json.dumps(body)


def test_a_take_made_the_older_way_is_built_as_before(provider):
    store = FakeStore({'a.png': b'start'})
    body = provider.build({'model': 'gemini-omni-1.1-flash', 'start_image': {'key': 'a.png', 'mime_type': 'image/png'}, 'effective_prompt': 'p', 'aspect_ratio': '16:9', 'resolution': '720p'}, store)
    assert [p['type'] for p in body['input']] == ['image', 'text'] and 'duration' not in body['response_format']
