"""Animatic gate test (design/155 phase 0). One run per call; nothing from the server is imported.
usage: omni_test.py RUN --video cartoon.mp4 | --images f00.png,... [--refs a.png,b.png] --prompt prompt.txt [--task edit] [--out DIR]
Reads the key from /opt/vw2/app/server/.env (VW2_GEMINI_API_KEY, else the first of VW2_GEMINI_API_KEYS). Never prints it."""
import argparse, base64, json, mimetypes, os, sys, time
import httpx

API = 'https://generativelanguage.googleapis.com'
MODEL = 'gemini-omni-1.1-flash'


def key():
    for line in open('/opt/vw2/app/server/.env', encoding='utf-8'):
        if line.startswith('VW2_GEMINI_API_KEY='):
            v = line.split('=', 1)[1].strip().strip('"\'')
            if v:
                return v
    for line in open('/opt/vw2/app/server/.env', encoding='utf-8'):
        if line.startswith('VW2_GEMINI_API_KEYS='):
            v = line.split('=', 1)[1].strip().strip('"\'').split(',')[0].strip()
            if v:
                return v
    sys.exit('no gemini key in .env')


def log(out, msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)
    with open(os.path.join(out, 'log.txt'), 'a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + msg + '\n')


def upload_video(client, h, path, out):
    data = open(path, 'rb').read()
    mime = mimetypes.guess_type(path)[0] or 'video/mp4'
    r = client.post(f'{API}/upload/v1beta/files', headers={**h, 'X-Goog-Upload-Protocol': 'resumable', 'X-Goog-Upload-Command': 'start',
                    'X-Goog-Upload-Header-Content-Length': str(len(data)), 'X-Goog-Upload-Header-Content-Type': mime, 'Content-Type': 'application/json'},
                    json={'file': {'display_name': os.path.basename(path)}})
    r.raise_for_status()
    url = r.headers['X-Goog-Upload-URL']
    r = client.post(url, headers={'X-Goog-Upload-Offset': '0', 'X-Goog-Upload-Command': 'upload, finalize', 'Content-Length': str(len(data))}, content=data)
    r.raise_for_status()
    f = r.json()['file']
    log(out, f"uploaded {path}: state {f.get('state')} name {f.get('name')}")
    while f.get('state') == 'PROCESSING':
        time.sleep(5)
        f = client.get(f"{API}/v1beta/{f['name']}", headers=h).json()
        log(out, f"file state {f.get('state')}")
    if f.get('state') != 'ACTIVE':
        sys.exit(f"file not active: {json.dumps(f)[:500]}")
    return f['uri'], mime


def img(path):
    mime = mimetypes.guess_type(path)[0] or 'image/png'
    return {'type': 'image', 'mime_type': mime, 'data': base64.b64encode(open(path, 'rb').read()).decode()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('run'); p.add_argument('--video'); p.add_argument('--images', default=''); p.add_argument('--refs', default='')
    p.add_argument('--prompt', required=True); p.add_argument('--task'); p.add_argument('--out', default='/tmp/anim-test/out')
    p.add_argument('--resolution', default='720p')
    p.add_argument('--model', default=MODEL); p.add_argument('--duration', help='whole seconds, e.g. 10 (Omni 1.2: 3-15)')
    a = p.parse_args()
    out = os.path.join(a.out, a.run); os.makedirs(out, exist_ok=True)
    h = {'x-goog-api-key': key(), 'Api-Revision': '2026-05-20'}
    client = httpx.Client(timeout=120, follow_redirects=True)
    parts = []
    t0 = time.time()
    if a.video:
        uri, mime = upload_video(client, h, a.video, out)
        parts.append({'type': 'video', 'uri': uri, 'mime_type': mime})
    for f in [x for x in a.images.split(',') if x]:
        parts.append(img(f))
    for f in [x for x in a.refs.split(',') if x]:
        parts.append(img(f))
    parts.append({'type': 'text', 'text': open(a.prompt, encoding='utf-8').read().strip()})
    body = {'model': a.model, 'background': True, 'store': True, 'input': parts,
            'response_format': {'type': 'video', 'aspect_ratio': '16:9', 'resolution': a.resolution}}
    if a.duration:
        body['response_format']['duration'] = f'{int(a.duration)}s'
    if a.task:
        body['generation_config'] = {'video_config': {'task': a.task}}
    json.dump({**body, 'input': [{k: (v if k != 'data' else f'<{len(v)} b64>') for k, v in q.items()} for q in parts]}, open(os.path.join(out, 'request.json'), 'w'), indent=1)
    log(out, f"{a.run}: submit {len(parts)} parts (video={bool(a.video)}, images={len(parts)-1-int(bool(a.video))}, task={a.task})")
    r = client.post(f'{API}/v1beta/interactions', headers=h, json=body)
    open(os.path.join(out, 'submit.json'), 'w').write(r.text[:20000])
    if r.status_code >= 300:
        log(out, f"REFUSED {r.status_code}: {r.text[:1500]}")
        return
    res = r.json(); iid = res['id']
    log(out, f"accepted id {iid} status {res.get('status')}")
    polls = 0
    while res.get('status') in ('in_progress', 'queued', 'pending', 'processing'):
        time.sleep(20); polls += 1
        res = client.get(f'{API}/v1beta/interactions/{iid}', headers=h).json()
        if polls % 3 == 0:
            log(out, f"poll {polls}: {res.get('status')}")
    elapsed = time.time() - t0
    slim = json.loads(json.dumps(res))
    for s in slim.get('steps', []):
        for c in s.get('content', []):
            if c.get('data'):
                c['data'] = f"<{len(c['data'])} b64>"
    json.dump(slim, open(os.path.join(out, 'result.json'), 'w'), indent=1)
    log(out, f"status {res.get('status')} after {elapsed:.0f}s; usage {json.dumps(res.get('usage'))}")
    if res.get('status') != 'completed':
        log(out, f"NOT COMPLETED: {json.dumps(slim)[:1500]}")
        return
    vids = [c for s in res.get('steps', []) if s.get('type') == 'model_output' for c in s.get('content', []) if c.get('type') == 'video']
    for i, v in enumerate(vids):
        path = os.path.join(out, f'output{i}.mp4')
        if v.get('data'):
            open(path, 'wb').write(base64.b64decode(v['data']))
        elif v.get('uri'):
            f = client.get(v['uri'], headers=h)
            open(path, 'wb').write(f.content)
        log(out, f"saved {path} {os.path.getsize(path)} bytes")
    texts = [c.get('text') for s in res.get('steps', []) for c in s.get('content', []) if c.get('type') == 'text']
    if texts:
        log(out, 'model text: ' + ' | '.join(t[:300] for t in texts if t))


if __name__ == '__main__':
    main()
