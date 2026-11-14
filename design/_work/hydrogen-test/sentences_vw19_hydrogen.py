"""Phase 1, test 2 (14 Nov 2026): every VW-19 clip through Gemini 4 Hydrogen, look-again way, high thinking and high picture quality, with the script
given as its 11 SENTENCES, and one added question: for each piece, which sentence it shows, from which second to which, how exactly, and what is missing.

Outside the application. The request is the server's own (`analysis.build_request`) with two changes made here, in the test only:
  1. the script's "beats" are the narration's sentences instead of its paragraphs;
  2. one field is added to each piece (`sentence_fits`) and one paragraph to the instruction that asks for it.
A clip the look-again way is refused for is sent the plain way, as the application does. Writes only into model-test/out-vw19-hydrogen-sentences/.

  python -X utf8 sentences_vw19_hydrogen.py [--minutes 14] [--workers 2] [--again C0113,C0032]
It stops starting new requests after --minutes, so it can be run again and again; a clip that has an answer is skipped. --again sends the named clips a second time (test 3)."""
import argparse
import copy
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import run_vw19_hydrogen as R
from app import analysis, analysis_jobs
from app.clip_log import schema as CS
from app.video_evidence.transport import GeminiTransport, GeminiTransportError

OUT = R.HERE / 'out-vw19-hydrogen-sentences'
run, procedure, brief, script, clips = R.inputs()
POL = {**R.POLICY, 'collection': [{'id': c['id'], 'sha256': c['sha256']} for c in clips]}
KEY = R.keys()[0]
SENTENCES = [s['text'] for s in json.loads((R.RUN_DIR / 'work/options/narration.json').read_text(encoding='utf-8'))['sentences']]
SCRIPT = {**script, 'beats': [{'beat_id': f'BEAT_{i:02d}', 'text': t} for i, t in enumerate(SENTENCES, 1)]}
ASK = ('SENTENCE FIT. Each BEAT above is ONE sentence of the narration, not a paragraph. primary_fit_for_beats: only the sentences whose words this sub-clip shows exactly. '
       'secondary_fit_for_beats: the sentences it shows in part, or only suits. In beat_fit_reasoning write one line for each fitted sentence, best first, each starting with the beat_id, '
       'the seconds of this clip that show it (inside the window of the sub-clip, from-to with one decimal) and one of EXACT, PARTLY or RELATED, then why; for example '
       '"BEAT_05 2.9-4.5 s PARTLY: the brick is placed on edge, but no mortar is applied". In beat_fit_limits write, for each fitted sentence, what the sentence says that those seconds '
       'do not show, each line starting with the beat_id. Empty lists are the right answer when the sub-clip suits no sentence. Never stretch a fit.')
FIT = None   # no field is added: in the look-again way the provider refuses the form with even one more field ("invalid argument", found 14 Nov); the fit goes into the fields the form has
TAIL = 'Return only the JSON object required by the response schema.'
LOCK = threading.Lock()


def request_of(clip):
    req = analysis.build_request(run, procedure, brief, SCRIPT, clip, POL)
    text = req['prompt']
    assert text.rstrip().endswith(TAIL)
    text = text.rstrip()[:-len(TAIL)].rstrip() + '\n\n' + ASK + '\n\n' + TAIL
    schema = copy.deepcopy(req['schema'])
    return req, text, schema


def one(clip, n):
    stem = clip['name'] + ('' if n == 1 else f'.{n}')
    if (OUT / f'{stem}.response.json').exists():
        return stem, 'kept'
    req, text, schema = request_of(clip)
    make = lambda: GeminiTransport(KEY, R.MODEL, terminal_deadline_seconds=1800, initial_soft_wait_seconds=60, on_update=lambda e: None, capture_answer_deltas=False, allow_agentic_video=True)
    t0 = time.time()
    try:
        t = make()
        rp = OUT / f"{clip['name']}.upload.json"
        with LOCK:
            receipt = json.loads(rp.read_text()) if rp.exists() else None
        up = t.upload(R.RUN_DIR / clip['path'], req['mime'], clip['sha256'], existing_receipt=receipt)
        rp.write_text(json.dumps(up))
        payload = {'contents': [{'role': 'user', 'parts': [{'fileData': {'fileUri': up['uri'], 'mimeType': up['mimeType']}, 'mediaProcessing': 'AGENTIC'}, {'text': text}]}],
                   'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': CS.wire_schema(schema), 'thinkingConfig': {'thinkingLevel': 'HIGH'},
                                        'mediaResolution': 'MEDIA_RESOLUTION_HIGH', 'maxOutputTokens': 65536}}
        got, plain = analysis_jobs.generate(t, payload, make)
    except GeminiTransportError as exc:
        meta = exc.metadata or {}
        row = {'clip': stem, 'duration_s': clip['duration_s'], 'error': exc.code, 'http_status': exc.http_status, 'provider_error': meta.get('provider_error'), 'usage': meta.get('usage'),
               'usd': R.cost_of(meta.get('usage')), 'seconds': round(time.time() - t0, 1)}
        with LOCK:
            with (OUT / 'ledger.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
        return stem, f"FAILED {exc.code} {exc.http_status or ''}"
    raw = got.get('raw') or json.dumps(got['body'], ensure_ascii=False)
    meta = got.get('metadata') or {}
    row = {'clip': stem, 'duration_s': clip['duration_s'], 'plain_fallback': plain, 'usage': meta.get('usage'), 'usd': R.cost_of(meta.get('usage')), 'seconds': round(time.time() - t0, 1),
           'looks': meta.get('media_processing_calls')}
    (OUT / f'{stem}.response.json').write_text(json.dumps({'raw': raw, 'metadata': meta, 'plain_fallback': plain, 'seconds': row['seconds'], 'prompt_sha': hashlib.sha256(text.encode()).hexdigest()},
                                                          indent=1, ensure_ascii=False), encoding='utf-8')
    with LOCK:
        with (OUT / 'ledger.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
    return stem, f"ok {row['seconds']} s, {row['usd']} USD, looks {row['looks']}{', PLAIN FALLBACK' if plain else ''}"


def status():
    rows = [json.loads(x) for x in (OUT / 'ledger.jsonl').read_text(encoding='utf-8').splitlines()] if (OUT / 'ledger.jsonl').exists() else []
    done = len(list(OUT.glob('*.mp4.response.json')))
    return f"answered {done} of {len(clips)}; requests {len(rows)}; failed {sum(1 for r in rows if r.get('error'))}; spent {sum(r.get('usd') or 0 for r in rows):.2f} USD"


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--minutes', type=float, default=14)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--again', default='')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    if a.dry:
        req, text, schema = request_of(clips[0])
        print(len(SENTENCES), 'sentences;', len(text), 'chars;', text[-900:])
        raise SystemExit
    jobs = ([(c, 2) for c in clips if any(c['name'].startswith(x) for x in a.again.split(','))] if a.again
            else [(c, 1) for c in sorted(clips, key=lambda c: c['duration_s'])])
    jobs = [j for j in jobs if not (OUT / f"{j[0]['name']}{'' if j[1] == 1 else '.' + str(j[1])}.response.json").exists()]
    stop = time.time() + a.minutes * 60

    def guarded(job):
        if time.time() > stop:
            return None
        return one(*job)
    with ThreadPoolExecutor(a.workers) as pool:
        for out in pool.map(guarded, jobs):
            if out:
                print(out[0], '|', out[1], flush=True)
    print(time.strftime('%H:%M'), status(), flush=True)
