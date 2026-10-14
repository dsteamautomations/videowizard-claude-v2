"""Voice (V1–V4) and media (M1–M6) through the plugin, with a fake ElevenLabs and local storage. Worker runs in-process."""
import base64
import hashlib
import json
import subprocess
from pathlib import Path

import httpx
import psycopg
import pytest

from app import elevenlabs, worker
from conftest import connected, vw
from test_stages_text import SOURCE, start_run, write_proposal

# ---------- fake provider ----------

MP3 = None


def mp3_bytes(seconds=2):
    global MP3
    if MP3 is None:
        out = Path(__file__).parent / '_tone.mp3'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}', '-codec:a', 'libmp3lame', '-b:a', '128k', str(out)], check=True)
        MP3 = out.read_bytes()
    return MP3


class FakeEleven:
    mode = 'ok'          # ok | reject | unknown | timing_bad | timing_padding
    history = []
    calls = []

    @classmethod
    def request(cls, self, method, path, **kw):
        cls.calls.append((method, path))
        if path == '/v1/models':
            return httpx.Response(200, json=[{'model_id': 'eleven_v4', 'name': 'Eleven v4', 'can_do_text_to_speech': True, 'maximum_text_length_per_request': 10000, 'languages': []}])
        if path.startswith('/v1/voices/'):
            vid = path.rsplit('/', 1)[1]
            return httpx.Response(200, json={'voice_id': vid, 'name': 'Voice ' + vid, 'preview_url': f'https://cdn.example/{vid}.mp3', 'labels': {'accent': 'indian'}})
        if path == '/v2/voices':
            return httpx.Response(200, json={'voices': [{'voice_id': 'v1', 'name': 'Asha', 'labels': {}, 'accent': 'indian', 'gender': 'female'},
                                                        {'voice_id': 'v2', 'name': 'Ravi', 'labels': {}, 'accent': 'indian', 'gender': 'male'}], 'has_more': False})
        if path.startswith('/v1/history/') and path.endswith('/audio'):
            return httpx.Response(200, content=mp3_bytes())
        if path == '/v1/history':
            return httpx.Response(200, json={'history': cls.history, 'has_more': False})
        if method == 'POST' and path.startswith('/v1/text-to-speech/'):
            if cls.mode == 'reject':
                e = Exception  # mimic adapter behaviour: a 429 becomes PROVIDER_REJECTED
                from app.errors import Problem
                err = Problem(502, 'PROVIDER_REJECTED', 'ElevenLabs did not complete the request (HTTP 429).')
                raise err
            if cls.mode == 'unknown':
                from app.errors import Problem
                raise Problem(502, 'PROVIDER_UNKNOWN', 'Provider connection interrupted (ReadTimeout, 480s).')
            text = kw['json']['text']
            audio = mp3_bytes()
            headers = {'request-id': 'req-' + hashlib.sha256(text.encode()).hexdigest()[:8], 'character-cost': str(len(text))}
            if path.endswith('/with-timestamps'):
                n = len(text)
                dur = {'timing_bad': 9.0, 'timing_padding': 2.3}.get(cls.mode, 2.0)  # padding: ends ~0.3 s after the decoded MP3, as ElevenLabs does
                starts = [round(i * dur / n, 4) for i in range(n)]
                ends = [round((i + 1) * dur / n, 4) for i in range(n)]
                body = {'audio_base64': base64.b64encode(audio).decode(), 'alignment': {'characters': list(text), 'character_start_times_seconds': starts, 'character_end_times_seconds': ends}, 'normalized_alignment': None}
                return httpx.Response(200, json=body, headers=headers)
            return httpx.Response(200, content=audio, headers=headers)
        return httpx.Response(404)


@pytest.fixture
def fake(monkeypatch):
    FakeEleven.mode, FakeEleven.history, FakeEleven.calls = 'ok', [], []
    monkeypatch.setattr(elevenlabs.ElevenLabs, 'request', lambda self, m, p, **kw: FakeEleven.request(self, m, p, **kw))
    return FakeEleven


def run_until_voice(home, database):
    code, ws = start_run(home, database)
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    vw(home, 'stage', 'intake', 'prepare')
    write_proposal(ws, 'intake', {'remove': [], 'titles': ['Earth Blocks'], 'notes': '', 'client': 'VK'})
    assert vw(home, 'stage', 'intake', 'record', '--quote', 'yes')[0] == 0
    write_proposal(ws, 'brief', {'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 't', 'ending': 'e'})
    assert vw(home, 'stage', 'brief', 'record', '--quote', 'yes')[0] == 0
    write_proposal(ws, 'script', {'spoken_text': 'Earth blocks are pressed.\n\nNot fired.', 'notes': '', 'assessment': '', 'changes': []})
    assert vw(home, 'stage', 'script', 'record', '--quote', 'yes')[0] == 0
    assert vw(home, 'next')[1]['stage'] == 'voice'
    return code, ws


def drain():
    while worker.tick():
        pass


def test_v1_auditions_then_narration_then_record(home, database, fake):
    code, ws = run_until_voice(home, database)
    rc, out, err = vw(home, 'voice', 'catalog', '--accent', 'indian')
    assert rc == 0 and [v['name'] for v in out['voices']] == ['Asha', 'Ravi']
    assert vw(home, 'voice', 'preview', '--voice', 'v1')[1]['url'].startswith('https://')
    rc, out, _ = vw(home, 'voice', 'audition', '--voice', 'v1', '--excerpt', 'Blocks of mud are pressed.')  # not in the accepted script
    assert rc == 2 and 'contiguous' in out['message']
    rc, out, _ = vw(home, 'voice', 'audition', *[x for v in ('v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7') for x in ('--voice', v)], '--excerpt', 'Earth blocks are pressed.')
    assert rc == 2 and 'six' in out['message']
    rc, out, err = vw(home, 'voice', 'audition', '--voice', 'v1', '--voice', 'v2', '--excerpt', 'Earth blocks are pressed.')
    assert rc == 0 and len(out['jobs']) == 2, err
    drain()
    jobs = vw(home, 'voice', 'jobs')[1]
    assert [j['status'] for j in jobs] == ['ready', 'ready'] and all(j['cost']['characters'] == 25 for j in jobs)
    assert 'text' not in jobs[0]['request']
    rc, out, _ = vw(home, 'voice', 'fetch', '--job', jobs[0]['id'])
    assert rc == 0 and (ws / 'out' / 'audition-v1.mp3').stat().st_size > 1000
    rc, out, err = vw(home, 'voice', 'narrate', '--voice', 'v2')
    assert rc == 0, err
    drain()
    job = [j for j in vw(home, 'voice', 'jobs')[1] if j['request']['kind'] == 'narration'][0]
    assert job['status'] == 'ready' and job['result']['timing_key'].endswith('.timing.json') and 1.9 < job['result']['duration_s'] < 2.2
    assert vw(home, 'voice', 'fetch', '--job', job['id'])[0] == 0
    timing = json.loads((ws / 'out' / 'timing.json').read_text(encoding='utf-8'))
    assert timing['script_characters_match'] is True and timing['words'][-1]['passage_id'] == 'P002'
    rc, out, err = vw(home, 'stage', 'voice', 'record', '--quote', 'yes, that voice')
    assert rc == 0, err
    assert {f['name'] for f in out['files']} == {'voice.json', 'narration.mp3', 'timing.json'} and all(f['receipt'] for f in out['files'])
    beats = out['summary']['beats']
    assert [b['beat_id'] for b in beats] == ['BEAT_01', 'BEAT_02'] and all(b['breathing_pause_s'] == 0.8 for b in beats)
    assert all(b['target_beat_duration_s'] == round(b['measured_vo_duration_s'] + 0.8, 3) for b in beats)
    assert beats[0]['end_s'] <= beats[1]['start_s'] and beats[-1]['end_s'] <= out['summary']['duration_s']
    assert out['summary']['cost']['characters'] == len('Earth blocks are pressed.\n\nNot fired.\n')
    assert vw(home, 'next')[1]['stage'] == 'media'


def test_v2_unknown_outcome_blocks_second_narration_until_resolved(home, database, fake):
    run_until_voice(home, database)
    fake.mode = 'unknown'
    rc, out, _ = vw(home, 'voice', 'narrate', '--voice', 'v1')
    assert rc == 0
    drain()
    job = vw(home, 'voice', 'jobs')[1][0]
    assert job['status'] == 'submission_unknown'
    fake.mode = 'ok'
    rc, out, _ = vw(home, 'voice', 'narrate', '--voice', 'v1')
    assert rc == 2 and out['code'] == 'JOB_OPEN'
    posts = [c for c in fake.calls if c[0] == 'POST']
    assert len(posts) == 1  # no second charge
    rc, out, _ = vw(home, 'voice', 'recover', '--job', job['id'])
    assert rc == 2 and out['code'] == 'TIMING_RECOVERY'
    assert vw(home, 'voice', 'resolve', '--job', job['id'], '--note', 'checked account: no charge')[0] == 0
    assert vw(home, 'voice', 'narrate', '--voice', 'v1')[0] == 0


def test_v2c_alignment_padding_tolerated_and_failed_job_reprocessed_from_journal(home, database, fake):
    run_until_voice(home, database)
    fake.mode = 'timing_padding'
    assert vw(home, 'voice', 'narrate', '--voice', 'v1')[0] == 0
    drain()
    job = vw(home, 'voice', 'jobs')[1][0]
    assert job['status'] == 'ready', job
    from app.storage import storage
    timing = json.loads(storage().get(job['result']['timing_key']).decode('utf-8'))
    assert 0.1 < timing['alignment_overshoot_s'] < 1.0 and timing['script_characters_match']
    assert timing['words_clamped'] >= 1 and all(w['end_s'] <= timing['audio']['duration_s'] for w in timing['words'])
    # a job that failed validation keeps its paid response; recover re-processes it without a second synthesis
    fake.mode = 'timing_bad'
    assert vw(home, 'voice', 'narrate', '--voice', 'v2')[0] == 0
    drain()
    bad = next(j for j in vw(home, 'voice', 'jobs')[1] if j['request']['voice_id'] == 'v2')
    assert bad['status'] == 'failed' and 'retained' in bad['error']
    posts = len([c for c in fake.calls if c[0] == 'POST'])
    rc, out, _ = vw(home, 'voice', 'recover', '--job', bad['id'])
    assert rc == 0 and out['status'] == 'storage_pending' and 'no new synthesis' in out['message']
    drain()
    assert next(j for j in vw(home, 'voice', 'jobs')[1] if j['id'] == bad['id'])['status'] == 'failed'  # still over tolerance
    assert len([c for c in fake.calls if c[0] == 'POST']) == posts  # and not paid again


def test_v2d_real_vw1_timing_clamped_once_and_accepted_by_planning_rule():
    """Defect 2 (14 Oct 2026): the real VW-1 narration ends 0.16 s after the decoded MP3; planning refused it. The producer's clamp
    makes the file valid for every reader; applying it twice changes nothing; a word entirely inside the padding still orders."""
    from copy import deepcopy
    from pathlib import Path
    from app.voice_timing import check_words, clamp_words
    raw = json.loads((Path(__file__).parent / 'fixtures' / 'vw1' / 'voice' / '328d22ee-427f-4586-9d63-3018bd9a27e7.timing.json').read_text(encoding='utf-8'))
    assert raw['words'][-1]['end_s'] > raw['audio']['duration_s']
    with pytest.raises(ValueError):
        check_words(deepcopy(raw))
    once = check_words(clamp_words(deepcopy(raw), 1.0))
    assert once['words_clamped'] == 1 and once['alignment_overshoot_s'] == 0.16 and once['words'][-1]['end_s'] == once['audio']['duration_s']
    twice = check_words(clamp_words(deepcopy(once), 1.0))
    assert twice['words'] == once['words'] and twice['words_clamped'] == 0
    # a whole word inside the padding
    deep = deepcopy(raw); deep['words'][-1]['start_s'] = raw['audio']['duration_s'] + 0.05
    fixed = check_words(clamp_words(deep, 1.0))
    assert fixed['words'][-1]['start_s'] < fixed['words'][-1]['end_s'] == fixed['audio']['duration_s']
    # beyond the tolerance: refused, nothing clamped
    far = deepcopy(raw); far['last_character_end_s'] = raw['audio']['duration_s'] + 1.5
    with pytest.raises(ValueError):
        clamp_words(far, 1.0)


def test_v2b_audition_recovered_from_history(home, database, fake):
    run_until_voice(home, database)
    fake.mode = 'unknown'
    vw(home, 'voice', 'audition', '--voice', 'v1', '--excerpt', 'Not fired.')
    drain()
    job = vw(home, 'voice', 'jobs')[1][0]
    assert job['status'] == 'submission_unknown'
    fake.history = [{'history_item_id': 'h1', 'voice_id': 'v1', 'model_id': 'eleven_v4', 'text': 'Not fired.', 'request_id': 'r1'}]
    assert vw(home, 'voice', 'recover', '--job', job['id'])[0] == 0
    drain()
    assert vw(home, 'voice', 'jobs')[1][0]['status'] == 'ready'


def test_v3_provider_rejects(home, database, fake):
    run_until_voice(home, database)
    fake.mode = 'reject'
    vw(home, 'voice', 'narrate', '--voice', 'v1')
    drain()
    job = vw(home, 'voice', 'jobs')[1][0]
    assert job['status'] == 'failed' and '429' in job['error']
    assert len([c for c in fake.calls if c[0] == 'POST']) == 1  # the worker never retries the provider


def test_v4_timing_mismatch_fails_and_is_retained(home, database, fake):
    run_until_voice(home, database)
    fake.mode = 'timing_bad'
    vw(home, 'voice', 'narrate', '--voice', 'v1')
    drain()
    job = vw(home, 'voice', 'jobs')[1][0]
    assert job['status'] == 'failed' and 'Timing' in job['error']
    assert list(Path(worker.SPOOL).glob(f"{job['id']}.response.json"))


def test_v_narration_must_match_script(home, database, fake):
    code, ws = run_until_voice(home, database)
    script = json.loads((ws / 'out' / 'script.json').read_text(encoding='utf-8'))
    script['spoken_text'] = 'Changed.'
    (ws / 'out' / 'script.json').write_text(json.dumps(script), encoding='utf-8')
    rc, out, _ = vw(home, 'voice', 'narrate', '--voice', 'v1')
    assert rc == 2 and out['code'] == 'SCRIPT_CHANGED'


# ---------- media ----------

def clip(path, seconds=1, audio=True, tone=440):
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'testsrc=duration={seconds}:size=64x64:rate=10']
    if audio:
        cmd += ['-f', 'lavfi', '-i', f'sine=frequency={tone}:duration={seconds}', '-c:a', 'aac']
    cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)]
    subprocess.run(cmd, check=True)


def run_until_media(home, database, fake):
    code, ws = run_until_voice(home, database)
    vw(home, 'voice', 'narrate', '--voice', 'v1')
    drain()
    job = vw(home, 'voice', 'jobs')[1][0]
    vw(home, 'voice', 'fetch', '--job', job['id'])
    assert vw(home, 'stage', 'voice', 'record', '--quote', 'yes')[0] == 0
    return code, ws


def test_m1_oversized_clip_refused_before_upload(home, database, fake):
    code, ws = run_until_media(home, database, fake)
    (ws / 'in' / 'big.mp4').write_bytes(b'\0' * (200 * 1024 * 1024 + 1))
    rc, out, _ = vw(home, 'stage', 'media', 'prepare')
    assert rc == 2 and '200 MB' in out['message']
    with psycopg.connect(database) as c:
        assert c.execute("select count(*) from vw2_files where stage='media'").fetchone()[0] == 0  # nothing of the clip reached storage


def test_m2_m4_m5_m6_media_upload_resume_dedupe_close(home, database, fake):
    code, ws = run_until_media(home, database, fake)
    clip(ws / 'in' / 'a.mp4')
    clip(ws / 'in' / 'b.mp4', audio=False)
    (ws / 'in' / 'z-copy.mp4').write_bytes((ws / 'in' / 'a.mp4').read_bytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=duration=2:size=64x64:rate=25', '-vf', "select='not(eq(mod(n,7),3))'", '-fps_mode', 'vfr',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(ws / 'in' / 'v.mp4')], check=True)   # variable frame rate, as phones record
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-display_rotation', '90', '-i', str(ws / 'in' / 'b.mp4'), '-c', 'copy', str(ws / 'in' / 'r.mp4')], check=True)  # rotated 90°
    rc, out, err = vw(home, 'stage', 'media', 'prepare')
    assert rc == 0, err
    assert len(out['clips']) == 4 and out['duplicates_skipped'] == 1  # M4
    by = {c['name']: c for c in out['clips']}
    assert by['a.mp4']['has_audio'] and not by['b.mp4']['has_audio']  # M6
    assert by['a.mp4']['audio_channels'] == 1 and by['a.mp4']['audio_sample_rate_hz'] == 44100 and by['b.mp4']['audio_channels'] == 0
    assert by['v.mp4']['transcoded_from_vfr'] and by['v.mp4']['is_variable_frame_rate'] is False and by['v.mp4']['fps'] == '25/1' and by['v.mp4']['path'] == 'work/cfr/v.mp4'
    assert by['r.mp4']['rotation_deg'] == 90 and (by['r.mp4']['width'], by['r.mp4']['height']) == (64, 64) and by['r.mp4']['stored_width'] == 64
    assert not by['a.mp4'].get('transcoded_from_vfr') and by['a.mp4']['rotation_deg'] == 0
    # M2: one clip uploaded beforehand (simulating a previous, interrupted record) is skipped on record
    assert vw(home, 'upload', '--stage', 'media', '--file', 'in/a.mp4')[0] == 0
    rc, out, err = vw(home, 'stage', 'media', 'record', '--quote', 'yes these clips')
    assert rc == 0, err
    assert out['summary']['units']['analysis'] == [c['id'] for c in out['summary']['clips']]
    assert next(c for c in out['summary']['clips'] if c['name'] == 'v.mp4')['transcoded_from_vfr'] is True
    with psycopg.connect(database) as c:
        assert c.execute("select count(*) from vw2_files where stage='media' and name like '%%.mp4'").fetchone()[0] == 4  # a.mp4 once (resumed), b, v (CFR copy), r; the copy deduped
    nxt = vw(home, 'next')[1]
    assert nxt['stage'] == 'analysis' and nxt['units_open'] == out['summary']['units']['analysis'] and nxt['paid'] == 'gemini-3.8-flash'
    # M5: close (remaining stages are not done, so close is not allowed yet) — verify receipts instead via a direct close attempt
    rc, out, _ = vw(home, 'close')
    assert rc == 2 and out['code'] == 'NOT_ALLOWED'


def test_m3_receipt_with_wrong_hash(client, alice, database):
    from conftest import rid
    run = client.post('/api/runs', json={'request_id': rid(), 'procedure_version': 'test'}, headers=alice).json()
    signed = client.post(f"/api/runs/{run['id']}/files/sign", json={'request_id': rid(), 'stage': 's2', 'name': 'x.bin'}, headers=alice).json()
    assert client.put(signed['url'], content=b'hello').status_code == 200
    r = client.post(f"/api/runs/{run['id']}/files/receipt", json={'request_id': rid(), 'key': signed['key'], 'sha256': 'ab' * 32, 'bytes': 5}, headers=alice)
    assert r.status_code == 409 and r.json()['code'] == 'FILE_MISMATCH'
    r = client.post(f"/api/runs/{run['id']}/files/receipt", json={'request_id': rid(), 'key': signed['key'], 'sha256': hashlib.sha256(b'hello').hexdigest(), 'bytes': 5}, headers=alice)
    assert r.status_code == 200 and r.json()['receipt'] is True
    # an output declaring a stored file without a receipt is refused
    r = client.post(f"/api/runs/{run['id']}/output", json={'request_id': rid(), 'stage': 's1', 'accepted_quote': 'yes',
                    'files': [{'name': 'y.bin', 'key': f"{run['id']}/s1/y.bin", 'sha256': 'cd' * 32, 'bytes': 1, 'location': 'storage'}]}, headers=alice)
    assert r.status_code == 422 and r.json()['code'] == 'FILE_NOT_RECEIVED'
