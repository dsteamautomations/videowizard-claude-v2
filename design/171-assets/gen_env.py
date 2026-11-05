"""Make environment pictures with the run's image model (the server's generateContent call, design/120), with parent pictures.
usage: gen_env.py DIR   (DIR/env-*.txt prompts; a sidecar DIR/env-*.parents lists parent picture paths, one per line, sent before the text).
Runs on the VM; reads VW2_GEMINI_IMAGE_MODEL and the key from /opt/vw2/app/server/.env; never prints the key."""
import base64, glob, json, os, sys, time
import httpx

URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'


def env(name, default=''):
    for line in open('/opt/vw2/app/server/.env', encoding='utf-8'):
        if line.startswith(name + '='):
            v = line.split('=', 1)[1].strip().strip('"\'')
            if v:
                return v
    return default


def main(d):
    key = env('VW2_GEMINI_API_KEY') or env('VW2_GEMINI_API_KEYS').split(',')[0].strip()
    model = env('VW2_GEMINI_IMAGE_MODEL', 'gemini-3-pro-image')
    print('model', model)
    for p in sorted(glob.glob(os.path.join(d, 'env-*.txt'))):
        name = os.path.basename(p)[:-4]
        if os.path.exists(os.path.join(d, name + '.png')):
            print(name, 'exists'); continue
        prompt = open(p, encoding='utf-8').read().strip()
        parts = []
        side = os.path.join(d, name + '.parents')
        if os.path.exists(side):
            for n, path in enumerate(l.strip() for l in open(side, encoding='utf-8') if l.strip()):
                data = open(path, 'rb').read()
                mime = 'image/png' if data[:4] == b'\x89PNG' else 'image/jpeg'
                parts += [{'text': f'Picture {n + 1}:'}, {'inlineData': {'mimeType': mime, 'data': base64.b64encode(data).decode()}}]
        parts.append({'text': prompt})
        body = {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': '16:9', 'imageSize': '1K'}}}
        t = time.time()
        r = httpx.post(URL.format(model=model), headers={'x-goog-api-key': key, 'Content-Type': 'application/json'}, json=body, timeout=300)
        if r.status_code >= 400:
            print(name, 'ERROR', r.status_code, r.text[:400]); continue
        cand = r.json().get('candidates') or [{}]
        imgs = [q['inlineData'] for q in (cand[0].get('content') or {}).get('parts', []) if 'inlineData' in q]
        if not imgs:
            print(name, 'NO IMAGE', json.dumps(r.json())[:400]); continue
        path = os.path.join(d, name + ('.png' if 'png' in imgs[0]['mimeType'] else '.jpg'))
        open(path, 'wb').write(base64.b64decode(imgs[0]['data']))
        print(name, 'saved', os.path.getsize(path), 'bytes', f'{time.time() - t:.0f}s', json.dumps(r.json().get('usageMetadata')))


if __name__ == '__main__':
    main(sys.argv[1])
