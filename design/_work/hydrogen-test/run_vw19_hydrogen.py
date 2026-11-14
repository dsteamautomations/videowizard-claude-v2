"""VW-19's clips through Gemini 4 Hydrogen with the application's own analysis request (13 Nov 2026, the test of design/_work/hydrogen-test-list.md).

Outside the application: reads the application's code (videowizard-v2-handover/server, import only), VW-19's run folder on this computer (read only)
and a test key file (never printed). Writes only into model-test/out-vw19-hydrogen/. No server, database or run is touched.

The request is built by `analysis.build_request`, the function the server calls, with the policy and settings VW-19's own jobs recorded; only the
model name differs. The payload is the worker's (analysis_jobs.process). Each clip is watched as production would: plain (STATIC) at 15 s or
less, look-again (AGENTIC) above; `--mode` forces one way for the short-clip pairs (T4).

Usage (from model-test/):
  python -X utf8 run_vw19_hydrogen.py --only C0032_02881492.mp4,... --mode AGENTIC
  python -X utf8 run_vw19_hydrogen.py --cap 15 --workers 3
A clip that already has an answer for that way is skipped, so the run can be started again. It stops starting new requests once the spend reaches the cap."""
import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'videowizard-v2-handover' / 'server'))
from app import analysis, analysis_jobs, core   # noqa: E402  (import only)
from app.video_evidence.transport import GeminiTransport, GeminiTransportError   # noqa: E402

RUN_DIR = Path('C:/Coworkspace/VideoWizard-Operator/runs/VW-19')
OUT = HERE / 'out-vw19-hydrogen'
MODEL = 'gemini-4-hydrogen'
USD_IN, USD_OUT = 1.50, 7.50   # per million tokens, Hydrogen's listed price (the review page, section 7)

# as VW-19's own analysis jobs recorded them (vw2_jobs.request, read 13 Nov)
POLICY = {'exclude': [], 'film_type': '', 'duplicates': None, 'waiver_note': 'the brief recorded no brand or safety rules', 'camera_audio': 'excluded', 'understand_audio': True,
          'waived_risk_flags': ['ppe', 'glove', 'helmet', 'hard_hat', 'hardhat', 'footwear', 'sandal', 'barefoot', 'boot', 'goggle', 'eye_protection', 'mask', 'harness', 'vest', 'high_vis'],
          'camera_audio_source': 'media'}
FILM = {'shape': {'value': 'horizontal', 'video': 'horizontal', 'fps': 50}, 'category': {'value': 'documentary-explainer'}}


def keys():
    for line in (ROOT / 'omni-test-keys.env').read_text(encoding='utf-8').splitlines():
        if line.startswith('VW2_GEMINI_API_KEYS='):
            return [k.strip() for k in line.split('=', 1)[1].strip().strip('"').split(',') if k.strip()]
    raise SystemExit('no VW2_GEMINI_API_KEYS in the test key file')


def inputs():
    manifest = json.loads((RUN_DIR / 'manifest.json').read_text(encoding='utf-8'))
    brief = json.loads((RUN_DIR / 'out/brief.json').read_text(encoding='utf-8'))
    # no client card is added: with the brief as it is in the run folder, the request's text and form have the same fingerprints as VW-19's own jobs (checked 13 Nov)
    script = json.loads((RUN_DIR / 'out/script.json').read_text(encoding='utf-8'))
    clips = json.loads((RUN_DIR / 'work/media-clips.json').read_text(encoding='utf-8'))
    run = {'id': manifest['run_id'], 'code': manifest['code'], 'client': manifest.get('client'), 'client_id': manifest.get('client_id'), 'procedure_version': '3', 'film': FILM}
    stages = json.loads((ROOT / 'videowizard-v2-handover' / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']   # the file the server loads; no database here
    procedure = {**core._stage(stages, analysis.STAGE), 'model': MODEL}
    return run, procedure, brief, script, clips


def cost_of(usage):
    u = usage or {}
    tin = (u.get('promptTokenCount') or 0) + (u.get('toolUsePromptTokenCount') or 0)
    tout = (u.get('candidatesTokenCount') or 0) + (u.get('thoughtsTokenCount') or 0)
    return round(tin * USD_IN / 1e6 + tout * USD_OUT / 1e6, 4)


LOCK = threading.Lock()


def ledger():
    p = OUT / 'ledger.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'spent_usd': 0.0, 'requests': []}


def spend(row):
    with LOCK:
        led = ledger()
        led['requests'].append(row)
        led['spent_usd'] = round(sum(r.get('usd') or 0 for r in led['requests']), 4)
        (OUT / 'ledger.json').write_text(json.dumps(led, indent=1), encoding='utf-8')
        return led['spent_usd']


def one(job, key, key_index, cap):
    run, procedure, brief, script, clips, clip, forced = job
    req = analysis.build_request(run, procedure, brief, script, clip, {**POLICY, 'collection': [{'id': c['id'], 'sha256': c['sha256']} for c in clips]})
    mode = forced or req['identity']['settings']['processing_mode']
    stem = f"{clip['name']}.{mode}"
    if (OUT / f'{stem}.response.json').exists():
        return stem, 'kept'
    with LOCK:
        if ledger()['spent_usd'] >= cap:
            return stem, 'not started: the limit is reached'
    (OUT / f"{clip['name']}.request.json").write_text(json.dumps({'model': MODEL, 'identity': req['identity'], 'project_config': req['project_config'], 'ffprobe_meta': req['ffprobe_meta'],
                                                                'prompt': req['prompt'], 'schema': req['schema']}, indent=1, ensure_ascii=False), encoding='utf-8')
    make = lambda: GeminiTransport(key, MODEL, terminal_deadline_seconds=1800, initial_soft_wait_seconds=60, on_update=lambda e: None, capture_answer_deltas=False, allow_agentic_video=True)
    path = RUN_DIR / clip['path']
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha == clip['sha256'], f"{clip['name']}: the file differs from the media record"
    t0 = time.time()
    try:
        transport = make()
        rp = OUT / f"{clip['name']}.upload.k{key_index}.json"
        up = transport.upload(path, req['mime'], sha, existing_receipt=json.loads(rp.read_text()) if rp.exists() else None)
        rp.write_text(json.dumps(up))
        parts = [{'fileData': {'fileUri': up['uri'], 'mimeType': up['mimeType']}}, {'text': req['prompt']}]
        if mode == 'AGENTIC':
            parts[0]['mediaProcessing'] = 'AGENTIC'
        s = req['identity']['settings']
        payload = {'contents': [{'role': 'user', 'parts': parts}],
                   'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': req['wire_schema'], 'thinkingConfig': {'thinkingLevel': s['thinking_level']},
                                        'mediaResolution': s['media_resolution'], 'maxOutputTokens': s['max_output_tokens']}}
        received, plain = analysis_jobs.generate(transport, payload, make)
    except GeminiTransportError as exc:
        meta = exc.metadata or {}
        row = {'clip': clip['name'], 'mode': mode, 'duration_s': clip['duration_s'], 'error': exc.code, 'http_status': exc.http_status, 'provider_error': meta.get('provider_error'),
               'usage': meta.get('usage'), 'usd': cost_of(meta.get('usage')), 'seconds': round(time.time() - t0, 1)}
        (OUT / f'{stem}.error.json').write_text(json.dumps({**row, 'message': str(exc)[:2000], 'metadata': meta}, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
        return stem, f"FAILED {exc.code} {exc.http_status or ''}; spent {spend(row)}"
    raw = received.get('raw') or json.dumps(received['body'], ensure_ascii=False)
    meta = received.get('metadata') or {}
    row = {'clip': clip['name'], 'mode': mode, 'duration_s': clip['duration_s'], 'plain_fallback': plain, 'usage': meta.get('usage'), 'usd': cost_of(meta.get('usage')),
           'seconds': round(time.time() - t0, 1), 'looks': meta.get('media_processing_calls'), 'finish_reason': meta.get('finish_reason')}
    (OUT / f'{stem}.response.json').write_text(json.dumps({'raw': raw, 'metadata': meta, 'plain_fallback': plain, 'seconds': row['seconds'], 'mode': mode}, indent=1, ensure_ascii=False), encoding='utf-8')
    return stem, f"ok {row['seconds']} s, {row['usd']} USD, looks {row['looks']}{', PLAIN FALLBACK' if plain else ''}; spent {spend(row)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--mode', choices=['AGENTIC', 'STATIC'], default=None)
    ap.add_argument('--cap', type=float, default=15.0)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--dry', action='store_true', help='build every request, send nothing')
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    run, procedure, brief, script, clips = inputs()
    chosen = [c for c in clips if not a.only or c['name'] in a.only.split(',')]
    chosen.sort(key=lambda c: c['duration_s'])   # the short, cheap clips first, so the limit stops the fewest clips
    if a.dry:
        for c in chosen:
            req = analysis.build_request(run, procedure, brief, script, c, {**POLICY, 'collection': [{'id': x['id'], 'sha256': x['sha256']} for x in clips]})
            print(c['name'], c['duration_s'], req['identity']['settings']['processing_mode'], len(req['prompt']), 'chars')
        print(len(chosen), 'clips;', 'model', procedure['model'], '; settings', procedure['settings'])
        return
    ks = keys()
    n = max(1, min(a.workers, len(ks)))
    jobs = [(run, procedure, brief, script, clips, c, a.mode) for c in chosen]
    with ThreadPoolExecutor(n) as pool:
        for stem, said in pool.map(lambda ij: one(ij[1], ks[ij[0] % n], ij[0] % n, a.cap), enumerate(jobs)):
            print(stem, '|', said, flush=True)
    print('spent in all:', ledger()['spent_usd'], 'USD of', a.cap)


if __name__ == '__main__':
    main()
