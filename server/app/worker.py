"""Single worker loop: python -m app.worker. Processes voice jobs (ported from v1 voice_worker, minus effects/voice lab).

Rules kept from v1: journal the raw timed response before parsing (bad timing can never trigger a second paid call);
check the MP3 before storing; store, then read back; never synthesize again for storage failures; an unknown provider
outcome becomes submission_unknown and waits for recover()."""
import hashlib
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from . import jobs
from . import narration_pieces as NP
from . import voice_direction as VD
from .config import settings
from .db import connect
from .elevenlabs import ElevenLabs, identifier
from .errors import Problem
from .storage import storage
from .voice_timing import check_words, clamp_words, decode_response, inspect_audio, timing_evidence

ALIGNMENT_TOLERANCE_S = 1.0  # MP3 frame padding: the provider's last character may end a little after the decoded duration

SPOOL = Path(os.environ.get('VW2_SPOOL') or Path(__file__).resolve().parents[1] / '.spool')

_MIRROR_CHECKED = 0.0
STOP = False  # set by SIGTERM: finish the current job, claim nothing new, exit (design/25)


def _stop(*_):
    global STOP
    STOP = True


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


def piece_paths(piece):
    base = SPOOL / f"piece-{piece['identity']}"
    return Path(f'{base}.response.json'), Path(f'{base}.mp3'), Path(f'{base}.meta.json')


def journaled_any(job):
    """True when a paid response of this job is retained on this server: a piece journal (design/40) or the older per-job files."""
    snap, jid = job['request'], str(job['id'])
    if snap.get('timing_mode') == 'generation':
        if any(p.is_file() for piece in NP.pieces_of(snap) for p in piece_paths(piece)[:2]):
            return True
    return any((SPOOL / f'{jid}{suffix}').is_file() for suffix in ('.response.json', '.mp3'))


def _headers(response):
    return {k: response.headers[k] for k in ('request-id', 'history-item-id', 'character-cost') if k in response.headers}


def _ensure_piece(piece, snap, provider, renew):
    """Journal one piece: reuse a journaled response or audio, otherwise one paid request. The raw timed response is written before
    it is parsed (a bad timing can never cause a second paid call)."""
    raw_path, mp3_path, meta_path = piece_paths(piece)
    if mp3_path.is_file() and meta_path.is_file():
        return
    if raw_path.is_file():
        saved = json.loads(raw_path.read_text(encoding='utf-8'))
        response = httpx.Response(200, content=saved['body'].encode('utf-8'), headers=saved['headers'])
    else:
        response = provider.synthesize({**snap, 'text': piece['text']})
        durable(raw_path, json.dumps({'body': response.text, 'received_at': datetime.now(timezone.utc).isoformat(), 'headers': _headers(response)}, ensure_ascii=False).encode('utf-8'))
    data, alignments = decode_response(response)
    if not is_mp3(data):
        raise Problem(502, 'PROVIDER_UNKNOWN', 'Provider response was not a usable MP3. The attempt is retained; check provider history.')
    durable(mp3_path, data)
    durable(meta_path, json.dumps({'headers': _headers(response), 'alignments': alignments, 'characters': len(piece['text'])}, ensure_ascii=False).encode('utf-8'))
    if renew:
        renew()


def process_voice(job, provider=None, store=None, renew=None):
    """Returns (status, result, error, cost, retry_in_minutes). A timed narration is one or more pieces (design/40); an audition is one request."""
    provider, store = provider or ElevenLabs(), store or storage()
    snap, jid = job['request'], str(job['id'])
    timed = snap.get('timing_mode') == 'generation'
    if not timed:
        return _process_audition(job, provider, store)
    pieces = NP.pieces_of(snap)
    audio_path, legacy_meta = SPOOL / f'{jid}.mp3', SPOOL / f'{jid}.meta.json'
    key = f"{job['run_id']}/voice/{jid}.mp3"
    try:
        legacy = audio_path.is_file() and legacy_meta.is_file() and not snap.get('pieces')   # a job journaled by the per-job scheme
        if job['status'] == 'storage_pending' and not legacy and not all(any(p.is_file() for p in piece_paths(piece)[:2]) for piece in pieces):
            raise Problem(409, 'PROVIDER_UNKNOWN', 'Saved response is missing. Recover from provider history; do not regenerate.')
        piece_results = []
        if legacy:
            meta = json.loads(legacy_meta.read_text(encoding='utf-8'))
            alignments, cost_chars, metas = meta.get('alignments') or {}, None, [meta]
        else:
            for piece in pieces:
                _ensure_piece(piece, snap, provider, renew)
            if not audio_path.is_file():
                NP.concat_mp3([piece_paths(piece)[1] for piece in pieces], audio_path, settings().FFMPEG_EXECUTABLE)
            metas = [json.loads(piece_paths(piece)[2].read_text(encoding='utf-8')) for piece in pieces]
            infos = [inspect_audio(piece_paths(piece)[1]) for piece in pieces]
            merged = NP.merge_alignments(NP.provider_text(snap), [{'offset': piece['offset'], 'text': piece['text'], 'alignment': (m['alignments'] or {}).get('alignment'),
                                                          'normalized_alignment': (m['alignments'] or {}).get('normalized_alignment'), 'duration_s': i['duration_s']}
                                                         for piece, m, i in zip(pieces, metas, infos)])
            alignments = {'alignment': merged['alignment'], 'normalized_alignment': merged['normalized_alignment']}
            if snap.get('tag_spans'):   # design/52 E: the tags never reach the timing; the remainder must be the accepted script
                alignments = {'alignment': VD.strip(merged['alignment'], snap['text_tagged'], [tuple(x) for x in snap['tag_spans']], snap['text']), 'normalized_alignment': None}
            piece_results = [{'identity': piece['identity'], 'characters': piece['characters'], 'duration_s': i['duration_s'], 'overshoot_s': x['overshoot_s'],
                              'request_id': m['headers'].get('request-id'), 'history_item_id': m['headers'].get('history-item-id')}
                             for piece, m, i, x in zip(pieces, metas, infos, merged['pieces'])]
        data = audio_path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        result = {'audio_key': key, 'sha256': sha, 'bytes': len(data), 'provider_request_id': metas[0]['headers'].get('request-id'),
                  'history_item_id': metas[0]['headers'].get('history-item-id'), 'pieces': piece_results}
        timing = timing_evidence(snap, alignments)
        timing['audio'] = inspect_audio(audio_path)
        check_words(clamp_words(timing, ALIGNMENT_TOLERANCE_S))
        timing_key = key.removesuffix('.mp3') + '.timing.json'
        timing_data = json.dumps(timing, ensure_ascii=False).encode('utf-8')
        store.put(timing_key, timing_data, 'application/json')
        result.update(timing_key=timing_key, timing_sha256=hashlib.sha256(timing_data).hexdigest(), timing_bytes=len(timing_data), duration_s=timing['audio']['duration_s'])
        store.put(key, data, 'audio/mpeg')
        if hashlib.sha256(store.get(key)).hexdigest() != sha:
            raise Problem(502, 'STORAGE', 'Recording read-back failed.')
        billed = [int(m['headers']['character-cost']) for m in metas if str(m['headers'].get('character-cost', '')).isdigit()]
        cost = {'characters': sum(billed) if len(billed) == len(metas) else snap['characters'], 'model': snap['model_id'], 'pieces': len(pieces)}
        return 'ready', result, None, cost, None
    except (Problem, OSError, ValueError, subprocess.SubprocessError) as exc:
        done = [piece for piece in pieces if any(p.is_file() for p in piece_paths(piece)[:2])]
        journaled = audio_path.is_file() or len(done) == len(pieces)
        rejected = isinstance(exc, Problem) and exc.code == 'PROVIDER_REJECTED'
        timing_bad = isinstance(exc, ValueError)
        status = 'storage_pending' if journaled and not timing_bad else 'failed' if rejected or timing_bad else 'submission_unknown'
        message = exc.message if isinstance(exc, Problem) else ('Timing validation failed; the original response and audio are retained. Do not regenerate.' if timing_bad else str(exc))
        result = {'pieces_done': len(done), 'pieces': len(pieces)} if status == 'submission_unknown' else None
        return status, result, message, None, 10 if status == 'storage_pending' else None


def _process_audition(job, provider, store):
    snap, jid = job['request'], str(job['id'])
    audio_path = SPOOL / f'{jid}.mp3'
    key = f"{job['run_id']}/voice/{jid}.mp3"
    try:
        if job['status'] == 'storage_pending' and not audio_path.is_file():
            raise Problem(409, 'PROVIDER_UNKNOWN', 'Saved response is missing. Recover from provider history; do not regenerate.')
        if not audio_path.is_file():
            response = provider.synthesize(snap)
            data = response.content
            if not is_mp3(data):
                raise Problem(502, 'PROVIDER_UNKNOWN', 'Provider response was not a usable MP3. The attempt is retained; check provider history.')
            durable(audio_path, data)
            durable(SPOOL / f'{jid}.meta.json', json.dumps({'headers': _headers(response), 'alignments': None}, ensure_ascii=False).encode('utf-8'))
        meta = json.loads((SPOOL / f'{jid}.meta.json').read_text(encoding='utf-8'))
        data = audio_path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        result = {'audio_key': key, 'sha256': sha, 'bytes': len(data), 'provider_request_id': meta['headers'].get('request-id'),
                  'history_item_id': meta['headers'].get('history-item-id'), 'duration_s': inspect_audio(audio_path)['duration_s']}
        store.put(key, data, 'audio/mpeg')
        if hashlib.sha256(store.get(key)).hexdigest() != sha:
            raise Problem(502, 'STORAGE', 'Recording read-back failed.')
        cost = {'characters': int(meta['headers']['character-cost']) if str(meta['headers'].get('character-cost', '')).isdigit() else snap['characters'], 'model': snap['model_id']}
        return 'ready', result, None, cost, None
    except (Problem, OSError, ValueError) as exc:
        journaled = audio_path.is_file()
        rejected = isinstance(exc, Problem) and exc.code == 'PROVIDER_REJECTED'
        status = 'storage_pending' if journaled else 'failed' if rejected else 'submission_unknown'
        message = exc.message if isinstance(exc, Problem) else str(exc)
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
        raise Problem(409, 'TIMING_RECOVERY', 'Narration needs its original timed response; history audio has no alignment. Narrate again: pieces already '
                                              'journaled on this server are reused without a second charge (design/40).')
    start = job['created_at'].timestamp() - 5
    end = job['updated_at'].timestamp() + 600
    found, cursor, seen = [], None, set()
    for _ in range(100):
        params = {'page_size': 100, 'source': 'TTS', 'model_id': snap['model_id'], 'date_after_unix': int(start), 'date_before_unix': int(end) + 1,
                  **({'start_after_history_item_id': cursor} if cursor else {})}
        data = provider.request('GET', '/v1/history', params=params).json()
        items = data.get('history', [])
        for h in items:
            if h.get('voice_id') == snap['voice_id'] and h.get('model_id') == snap['model_id'] and h.get('text') == NP.provider_text(snap):
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


def renew_lease(job_id):
    """A narration renews its lease after every piece (design/40 S5) so a long job is never re-claimed while it works."""
    with connect() as conn:
        conn.execute("update vw2_jobs set lease_until = now() + interval '20 minutes', updated_at = now() where id=%s", (job_id,))


def tick():
    """One pass over every provider family: voice, then analysis. Returns True when anything was processed."""
    busy = False
    if STOP:
        return busy
    with connect() as conn:
        job = jobs.claim(conn, 'elevenlabs')
    if job:
        status, result, error, cost, retry_in = process_voice(job, renew=lambda: renew_lease(job['id']))
        with connect() as conn:
            finalize_voice(conn, job, status, result, error, cost, retry_in)
        busy = True
    global _MIRROR_CHECKED
    if time.time() - _MIRROR_CHECKED > 600 and os.environ.get('VW2_WORKER_CHILD') != '1':   # design/54 A: the parent worker refreshes the catalogue mirror once a day
        _MIRROR_CHECKED = time.time()
        try:
            with connect() as conn:
                from . import voices
                voices.refresh_if_due(conn, ElevenLabs())
        except Exception:  # noqa: BLE001  the mirror is a convenience; it must never stop the worker
            pass
    from . import analysis_jobs, visual_workers
    from .stage2 import render_jobs
    for family in (analysis_jobs.tick, visual_workers.tick, render_jobs.tick):
        if STOP:
            break
        if family():
            busy = True
    return busy


def main():
    n = settings().WORKERS
    children = []
    if n > 1 and os.environ.get('VW2_WORKER_CHILD') != '1':
        import subprocess, sys
        children = [subprocess.Popen([sys.executable, '-m', 'app.worker'], env={**os.environ, 'VW2_WORKER_CHILD': '1'}) for _ in range(n - 1)]
        print(f'started {n} workers', flush=True)

    def on_term(signum, frame):
        _stop()
        for c in children:
            c.send_signal(signum)  # no-op for a child that already exited

    signal.signal(signal.SIGTERM, on_term)
    try:
        loop()
    finally:
        for c in children:
            c.terminate()  # POSIX: SIGTERM, so children drain; Windows: immediate kill, as before
        for c in children:
            c.wait()


def pause(seconds):
    for _ in range(seconds):
        if STOP:
            return
        time.sleep(1)


def loop():
    failures = 0
    while not STOP:
        try:
            busy = tick()
            failures = 0
            pause(2 if busy else 10)
        except KeyboardInterrupt:
            return
        except Exception as exc:  # connection problems: back off, keep job identities intact
            failures += 1
            print(f'worker error ({exc.__class__.__name__}); retrying', flush=True)
            if failures >= 5:
                raise SystemExit('Worker stopped after five consecutive failures. Restore connectivity and restart.')
            pause(10)


if __name__ == '__main__':
    main()
