"""One batch request to Gemini 4 Hydrogen (14 Nov 2026): is the look-again way accepted in a batch, and what does the half-price answer look like?
Outside the application; the key is read from the test key file and never printed. Writes only into model-test/out-vw19-hydrogen-settings/.

  python -X utf8 batch_vw19_hydrogen.py create [AGENTIC|STATIC]   one inline request for clip C0113, the application's own request
  python -X utf8 batch_vw19_hydrogen.py poll                      the state of every batch created; saves the answer when it is there"""
import json
import sys
import time

import httpx

import run_vw19_hydrogen as R
import settings_vw19_hydrogen as S
from app import analysis
from app.video_evidence.transport import GeminiTransport

BASE = 'https://generativelanguage.googleapis.com/v1beta/'
BOOK = S.OUT / 'batches.json'
HEAD = {'x-goog-api-key': S.KEY, 'Content-Type': 'application/json'}


def book():
    return json.loads(BOOK.read_text(encoding='utf-8')) if BOOK.exists() else []


def create(mode):
    name = S.CLIPS[0]
    clip = next(c for c in S.clips if c['name'] == name)
    req = analysis.build_request(S.run, S.procedure, S.brief, S.script, clip, S.POL)
    rp = S.OUT / f'{name}.upload.json'
    t = GeminiTransport(S.KEY, R.MODEL, terminal_deadline_seconds=600, initial_soft_wait_seconds=60, on_update=lambda e: None, capture_answer_deltas=False, allow_agentic_video=True)
    up = t.upload(R.RUN_DIR / clip['path'], req['mime'], clip['sha256'], existing_receipt=json.loads(rp.read_text()) if rp.exists() else None)
    rp.write_text(json.dumps(up))
    video = {'fileData': {'fileUri': up['uri'], 'mimeType': up['mimeType']}}
    if mode == 'AGENTIC':
        video['mediaProcessing'] = 'AGENTIC'
    request = {'contents': [{'role': 'user', 'parts': [video, {'text': req['prompt']}]}],
               'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': req['wire_schema'], 'thinkingConfig': {'thinkingLevel': 'HIGH'},
                                    'mediaResolution': 'MEDIA_RESOLUTION_HIGH', 'maxOutputTokens': 32768}}   # a batch refuses more than 32768 (found 14 Nov)
    body = {'batch': {'display_name': f'vw19-test-{mode.lower()}', 'input_config': {'requests': {'requests': [{'request': request, 'metadata': {'key': f'{name[:5]}-{mode}'}}]}}}}
    r = httpx.post(BASE + f'models/{R.MODEL}:batchGenerateContent', headers=HEAD, json=body, timeout=120)
    out = r.json() if r.headers.get('content-type', '').startswith('application/json') else {'text': r.text[:1000]}
    rows = book() + [{'mode': mode, 'http_status': r.status_code, 'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'name': out.get('name'), 'answer': out if r.status_code != 200 else {k: out.get(k) for k in ('name', 'metadata', 'done')}}]
    BOOK.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding='utf-8')
    print(mode, r.status_code, json.dumps(out, ensure_ascii=False)[:700])


def poll():
    rows = book()
    for row in rows:
        if not row.get('name'):
            continue
        r = httpx.get(BASE + row['name'], headers=HEAD, timeout=60)
        out = r.json()
        meta = out.get('metadata') or {}
        row['state'], row['polled_at'] = meta.get('state') or ('done' if out.get('done') else '?'), time.strftime('%Y-%m-%d %H:%M:%S')
        print(row['mode'], row['name'], row['state'], 'done' if out.get('done') else '', json.dumps(out.get('error') or '', ensure_ascii=False)[:300])
        if out.get('done'):
            (S.OUT / f"batch.{row['mode']}.result.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
            row['result_keys'] = list((out.get('response') or out.get('dest') or meta.get('output') or {}).keys())
    BOOK.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    create(sys.argv[2] if len(sys.argv) > 2 else 'AGENTIC') if sys.argv[1:2] == ['create'] else poll()
