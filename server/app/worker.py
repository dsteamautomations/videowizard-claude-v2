"""Single worker loop: python -m app.worker. Processes voice jobs (ported from v1 voice_worker, minus effects/voice lab).

Rules kept from v1: journal the raw timed response before parsing (bad timing can never trigger a second paid call);
check the MP3 before storing; store, then read back; never synthesize again for storage failures; an unknown provider
outcome becomes submission_unknown and waits for recover()."""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from . import jobs
from .config import settings
from .db import connect
from .elevenlabs import ElevenLabs, identifier
from .errors import Problem
from .storage import storage
from .voice_timing import check_words, clamp_words, decode_response, inspect_audio, timing_evidence

ALIGNMENT_TOLERANCE_S = 1.0  # MP3 frame padding: the provider's last character may end a little after the decoded duration

SPOOL = Path(os.environ.get('VW2_SPOOL') or Path(__file__).resolve().parents[1] / '.spool')


def durable(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)


def is_mp3(data):
    return bool(data) and len(data) <= 50 * 1024 * 1024 and (data.startswith(b'ID3') or (len(data) > 1 and data[0] == 255 and data[1] & 224 == 224))


def process_voice(job, provider=None, store=None):
    """Returns (status, result, error, cost, retry_in_minutes)."""
    provider, store = provider or ElevenLabs(), store or storage()
    snap, jid = job['request'], str(job['id'])
    timed = snap.get('timing_mode') == 'generation'
    raw_path, audio_path = SPOOL / f'{jid}.response.json', SPOOL / f'{jid}.mp3'
    key = f"{job['run_id']}/voice/{jid}.mp3"
    try:
        if job['status'] == 'storage_pending' and not audio_path.is_file() and not raw_path.is_file():
            raise Problem(409, 'PROVIDER_UNKNOWN', 'Saved response is missing. Recover from provider history; do not regenerate.')
        if timed and raw_path.is_file():
            saved = json.loads(raw_path.read_text(encoding='utf-8'))
            response = httpx.Response(200, content=saved['body'].encode('utf-8'), headers=saved['headers'])
        elif audio_path.is_file():
            response = None
        else:
            response = provider.synthesize(snap)
            if timed:
                durable(raw_path, json.dumps({'body': response.text, 'received_at': datetime.now(timezone.utc).isoformat(),
                                              'headers': {k: response.headers[k] for k in ('request-id', 'history-item-id', 'character-cost') if k in response.headers}}, ensure_ascii=False).encode('utf-8'))
        if response is not None:
            data, alignments = decode_response(response) if timed else (response.content, None)
            if not is_mp3(data):
                raise Problem(502, 'PROVIDER_UNKNOWN', 'Provider response was not a usable MP3. The attempt is retained; check provider history.')
            durable(audio_path, data)
            headers = {k: response.headers[k] for k in ('request-id', 'history-item-id', 'character-cost') if k in response.headers}
            durable(SPOOL / f'{jid}.meta.json', json.dumps({'headers': headers, 'alignments': alignments}, ensure_ascii=False).encode('utf-8'))
        meta = json.loads((SPOOL / f'{jid}.meta.json').read_text(encoding='utf-8'))
        data = audio_path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        result = {'audio_key': key, 'sha256': sha, 'bytes': len(data), 'provider_request_id': meta['headers'].get('request-id'),
                  'history_item_id': meta['headers'].get('history-item-id')}
        if timed:
            timing = timing_evidence(snap, meta.get('alignments') or {})
            timing['audio'] = inspect_audio(audio_path)
            check_words(clamp_words(timing, ALIGNMENT_TOLERANCE_S))
            timing_key = key.removesuffix('.mp3') + '.timing.json'
            timing_data = json.dumps(timing, ensure_ascii=False).encode('utf-8')
            store.put(timing_key, timing_data, 'application/json')
            result.update(timing_key=timing_key, timing_sha256=hashlib.sha256(timing_data).hexdigest(), timing_bytes=len(timing_data), duration_s=timing['audio']['duration_s'])
        else:
            result['duration_s'] = inspect_audio(audio_path)['duration_s']
        store.put(key, data, 'audio/mpeg')
        if hashlib.sha256(store.get(key)).hexdigest() != sha:
            raise Problem(502, 'STORAGE', 'Recording read-back failed.')
        cost = {'characters': int(meta['headers']['character-cost']) if str(meta['headers'].get('character-cost', '')).isdigit() else snap['characters'], 'model': snap['model_id']}
        return 'ready', result, None, cost, None
    except (Problem, OSError, ValueError) as exc:
        journaled = audio_path.is_file() or (timed and raw_path.is_file())
        rejected = isinstance(exc, Problem) and exc.code == 'PROVIDER_REJECTED'
        timing_bad = timed and isinstance(exc, ValueError)
        status = 'storage_pending' if journaled and not timing_bad else 'failed' if rejected or timing_bad else 'submission_unknown'
        message = exc.message if isinstance(exc, Problem) else ('Timing validation failed; the original response and audio are retained. Do not regenerate.' if timing_bad else str(exc))
        return status, None, message, None, 10 if status == 'storage_pending' else None


def finalize_voice(conn, job, status, result, error, cost, retry_in):
    if status == 'ready':
        jobs.record_file(conn, job['run_id'], 'voice', result['audio_key'], Path(result['audio_key']).name, result['sha256'], result['bytes'], 'audio/mpeg')
        if result.get('timing_key'):
            jobs.record_file(conn, job['run_id'], 'voice', result['timing_key'], Path(result['timing_key']).name, result['timing_sha256'], result['timing_bytes'], 'application/json')
    jobs.finish(conn, job['id'], status, result=result, error=error, cost=cost, retry_in=retry_in)


def recover_voice(job, provider=None):
    """Recover audio of a submission_unknown job from provider history (ported). Never submits text-to-speech."""
    provider = provider or ElevenLabs()
    snap, jid = job['request'], str(job['id'])
    if snap.get('timing_mode') == 'generation':
        raise Problem(409, 'TIMING_RECOVERY', 'Narration needs its original timed response; history audio has no alignment. Start narration again (the server never reuses an unknown attempt).')
    start = job['created_at'].timestamp() - 5
    end = job['updated_at'].timestamp() + 600
    found, cursor, seen = [], None, set()
    for _ in range(100):
        params = {'page_size': 100, 'source': 'TTS', 'model_id': snap['model_id'], 'date_after_unix': int(start), 'date_before_unix': int(end) + 1,
                  **({'start_after_history_item_id': cursor} if cursor else {})}
        data = provider.request('GET', '/v1/history', params=params).json()
        items = data.get('history', [])
        for h in items:
            if h.get('voice_id') == snap['voice_id'] and h.get('model_id') == snap['model_id'] and h.get('text') == snap['text']:
                found.append(h)
        if not data.get('has_more'):
            break
        cursor = data.get('last_history_item_id') or (items[-1].get('history_item_id') if items else None)
        if not cursor or cursor in seen:
            break
        seen.add(cursor)
    if len(found) != 1:
        raise Problem(409, 'HISTORY_MATCH', f'{len(found)} matching recordings in provider history; need exactly one. Nothing was regenerated.')
    hid = identifier(found[0]['history_item_id'])
    audio = provider.request('GET', f'/v1/history/{hid}/audio').content
    if not is_mp3(audio):
        raise Problem(409, 'HISTORY_AUDIO', 'The historical response is not a usable MP3.')
    durable(SPOOL / f'{jid}.mp3', audio)
    durable(SPOOL / f'{jid}.meta.json', json.dumps({'headers': {'request-id': found[0].get('request_id'), 'history-item-id': hid}, 'alignments': None}).encode('utf-8'))


def tick():
    """One pass over every provider family: voice, then analysis. Returns True when anything was processed."""
    busy = False
    with connect() as conn:
        job = jobs.claim(conn, 'elevenlabs')
    if job:
        status, result, error, cost, retry_in = process_voice(job)
        with connect() as conn:
            finalize_voice(conn, job, status, result, error, cost, retry_in)
        busy = True
    from . import analysis_jobs, visual_workers
    if analysis_jobs.tick():
        busy = True
    if visual_workers.tick():
        busy = True
    from .stage2 import render_jobs
    if render_jobs.tick():
        busy = True
    return busy


def main():
    n = settings().WORKERS
    if n > 1 and os.environ.get('VW2_WORKER_CHILD') != '1':
        import subprocess, sys
        children = [subprocess.Popen([sys.executable, '-m', 'app.worker'], env={**os.environ, 'VW2_WORKER_CHILD': '1'}) for _ in range(n - 1)]
        print(f'started {n} workers', flush=True)
        try:
            loop()
        finally:
            for c in children:
                c.terminate()
        return
    loop()


def loop():
    failures = 0
    while True:
        try:
            busy = tick()
            failures = 0
            time.sleep(2 if busy else 10)
        except KeyboardInterrupt:
            return
        except Exception as exc:  # connection problems: back off, keep job identities intact
            failures += 1
            print(f'worker error ({exc.__class__.__name__}); retrying', flush=True)
            if failures >= 5:
                raise SystemExit('Worker stopped after five consecutive failures. Restore connectivity and restart.')
            time.sleep(10)


if __name__ == '__main__':
    main()
