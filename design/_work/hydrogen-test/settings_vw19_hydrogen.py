"""Settings test on two VW-19 clips with Gemini 4 Hydrogen, look-again way (14 Nov 2026): does a lower thinking level or picture quality, or another
order of the request, cut the cost and the time, and do the facts hold?

Outside the application, as run_vw19_hydrogen.py: the server's own request builder, VW-19's files read only, a test key never printed.
Writes only into model-test/out-vw19-hydrogen-settings/.

  python -X utf8 settings_vw19_hydrogen.py grid     thinking HIGH/MEDIUM/LOW x picture quality HIGH/MEDIUM/LOW, both clips (18 requests)
  python -X utf8 settings_vw19_hydrogen.py order    the cache trials: the instruction before the video; then the instruction with everything
                                                    that is the same for every clip first and the clip's own values last (5 requests)
A request that already has an answer or an error file is skipped."""
import hashlib
import json
import sys
import time
from pathlib import Path

import run_vw19_hydrogen as R
from app import analysis
from app.video_evidence.transport import GeminiTransport, GeminiTransportError

OUT = R.HERE / 'out-vw19-hydrogen-settings'
CLIPS = ['C0113_02781556.mp4', 'C0032_02881492.mp4']
run, procedure, brief, script, clips = R.inputs()
POL = {**R.POLICY, 'collection': [{'id': c['id'], 'sha256': c['sha256']} for c in clips]}
KEY = R.keys()[0]


def common_first(text, req):
    """The same instruction with the clip's own values moved to the end, so that everything before them is word for word the same for every clip."""
    start, end = text.index('FFPROBE FILE METADATA for the attached clip:'), text.index('SPEAKER POLICY IN FORCE')
    block = text[start:end].strip()
    body = text[:start] + text[end:]
    frames, tag = req['duration_frames'], req['identity']['clip_tag']
    a, b = f'(0 to {frames - 1})', f'SUB_{tag}_'
    assert body.count(a) == 1 and body.count(b) >= 1, (body.count(a), body.count(b))
    body = body.replace(a, '(0 to duration_frames minus 1; duration_frames is given at the end)').replace(b, 'SUB_<clip_id>_')   # every sub-clip id example
    assert tag not in body, 'a value of this clip is still in the common part'
    tail = 'Return only the JSON object required by the response schema.'
    block += '\nIn every sub_clip_id, <clip_id> is the clip_id above.'
    assert body.rstrip().endswith(tail)
    return body.rstrip()[:-len(tail)].rstrip() + '\n\nTHE CLIP (its own values; everything above is the same for every clip of this film)\n' + block + '\n\n' + tail


def send(name, thinking, quality, variant='as-is', n=1):
    clip = next(c for c in clips if c['name'] == name)
    req = analysis.build_request(run, procedure, brief, script, clip, POL)
    stem = f"{name[:5]}.{variant}.T-{thinking}.Q-{quality}" + (f'.{n}' if n > 1 else '')
    if (OUT / f'{stem}.response.json').exists() or (OUT / f'{stem}.error.json').exists():
        return print(stem, '| kept', flush=True)
    text = common_first(req['prompt'], req) if variant == 'common-first' else req['prompt']
    path = R.RUN_DIR / clip['path']
    t = GeminiTransport(KEY, R.MODEL, terminal_deadline_seconds=1800, initial_soft_wait_seconds=60, on_update=lambda e: None, capture_answer_deltas=False, allow_agentic_video=True)
    t0 = time.time()
    try:
        rp = OUT / f'{name}.upload.json'
        up = t.upload(path, req['mime'], clip['sha256'], existing_receipt=json.loads(rp.read_text()) if rp.exists() else None)
        rp.write_text(json.dumps(up))
        video = {'fileData': {'fileUri': up['uri'], 'mimeType': up['mimeType']}, 'mediaProcessing': 'AGENTIC'}
        parts = [video, {'text': text}] if variant == 'as-is' else [{'text': text}, video]
        payload = {'contents': [{'role': 'user', 'parts': parts}],
                   'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': req['wire_schema'], 'thinkingConfig': {'thinkingLevel': thinking},
                                        'mediaResolution': 'MEDIA_RESOLUTION_' + quality, 'maxOutputTokens': 65536}}
        got = t.generate(payload)
    except GeminiTransportError as exc:
        meta = exc.metadata or {}
        (OUT / f'{stem}.error.json').write_text(json.dumps({'error': exc.code, 'http_status': exc.http_status, 'provider_error': meta.get('provider_error'), 'message': str(exc)[:1500], 'usage': meta.get('usage'),
                                                            'seconds': round(time.time() - t0, 1)}, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
        return print(stem, '| FAILED', exc.code, exc.http_status, str(meta.get('provider_error'))[:160], flush=True)
    raw = got.get('raw') or json.dumps(got['body'], ensure_ascii=False)
    meta = got.get('metadata') or {}
    secs = round(time.time() - t0, 1)
    (OUT / f'{stem}.response.json').write_text(json.dumps({'raw': raw, 'metadata': meta, 'seconds': secs, 'variant': variant, 'thinking': thinking, 'quality': quality,
                                                           'prompt_sha': hashlib.sha256(text.encode()).hexdigest()}, indent=1, ensure_ascii=False), encoding='utf-8')
    u = meta.get('usage') or {}
    print(stem, f"| ok {secs} s, {R.cost_of(u)} USD, looks {meta.get('media_processing_calls')}, cached {u.get('cachedContentTokenCount')}", flush=True)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else 'grid'
    if what == 'grid':
        for name in CLIPS:
            for thinking in ('HIGH', 'MEDIUM', 'LOW'):
                for quality in ('HIGH', 'MEDIUM', 'LOW'):
                    send(name, thinking, quality)
    if what == 'order':
        for name in CLIPS:                       # the instruction before the video, the text as it is
            send(name, 'HIGH', 'HIGH', 'text-first')
        for name, n in ((CLIPS[0], 1), (CLIPS[1], 1), (CLIPS[0], 2)):   # the common part first: two clips, then the first again
            send(name, 'HIGH', 'HIGH', 'common-first', n)
