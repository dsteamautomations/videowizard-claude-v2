"""Make the reference pictures with the run's Gemini image model (the same generateContent call the server uses, design/120).
usage: gen_refs.py OUTDIR  (prompts in OUTDIR/ref-*.txt). Reads VW2_GEMINI_IMAGE_MODEL and the key from /opt/vw2/app/server/.env; never prints the key."""
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


def main(out):
    key = env('VW2_GEMINI_API_KEY') or env('VW2_GEMINI_API_KEYS').split(',')[0].strip()
    model = env('VW2_GEMINI_IMAGE_MODEL', 'gemini-3-pro-image')
    print('model', model)
    for p in sorted(glob.glob(os.path.join(out, 'ref-*.txt'))):
        name = os.path.basename(p)[:-4]
        prompt = open(p, encoding='utf-8').read().strip()
        body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': '16:9', 'imageSize': '1K'}}}
        t = time.time()
        r = httpx.post(URL.format(model=model), headers={'x-goog-api-key': key, 'Content-Type': 'application/json'}, json=body, timeout=300)
        if r.status_code >= 400:
            print(name, 'ERROR', r.status_code, r.text[:400]); continue
        parts = r.json()['candidates'][0]['content']['parts']
        imgs = [q['inlineData'] for q in parts if 'inlineData' in q]
        if not imgs:
            print(name, 'NO IMAGE', json.dumps(r.json())[:400]); continue
        ext = 'png' if 'png' in imgs[0]['mimeType'] else 'jpg'
        path = os.path.join(out, f'{name}.{ext}')
        open(path, 'wb').write(base64.b64decode(imgs[0]['data']))
        print(name, 'saved', path, os.path.getsize(path), 'bytes', f'{time.time()-t:.0f}s', 'usage', json.dumps(r.json().get('usageMetadata')))


if __name__ == '__main__':
    main(sys.argv[1])
