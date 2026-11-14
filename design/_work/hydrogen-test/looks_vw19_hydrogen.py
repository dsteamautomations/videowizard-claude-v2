"""What each "look" is (14 Nov 2026): the same look-again request sent straight to Google, keeping what the application's transport throws away:
what each look asked for, how much came back, and the model's own short notes of its thinking between the looks.
Outside the application; the key is never printed. Writes only into model-test/out-vw19-hydrogen-settings/.

  python -X utf8 looks_vw19_hydrogen.py C0113 HIGH HIGH"""
import json
import sys
import time

import httpx

import run_vw19_hydrogen as R
import settings_vw19_hydrogen as S
from app import analysis

name = next(n for n in [c['name'] for c in S.clips] if n.startswith(sys.argv[1]))
thinking, quality = sys.argv[2], sys.argv[3]
clip = next(c for c in S.clips if c['name'] == name)
req = analysis.build_request(S.run, S.procedure, S.brief, S.script, clip, S.POL)
up = json.loads((S.OUT / f'{name}.upload.json').read_text())
payload = {'contents': [{'role': 'user', 'parts': [{'fileData': {'fileUri': up['uri'], 'mimeType': up['mimeType']}, 'mediaProcessing': 'AGENTIC'}, {'text': req['prompt']}]}],
           'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': req['wire_schema'], 'thinkingConfig': {'thinkingLevel': thinking, 'includeThoughts': True},
                                'mediaResolution': 'MEDIA_RESOLUTION_' + quality, 'maxOutputTokens': 65536}}
steps, answer, usage, t0 = [], [], None, time.time()
with httpx.stream('POST', f'https://generativelanguage.googleapis.com/v1beta/models/{R.MODEL}:streamGenerateContent?alt=sse', headers={'x-goog-api-key': S.KEY}, json=payload, timeout=900) as r:
    if r.status_code != 200:
        r.read()
        raise SystemExit(f'{r.status_code} {r.text[:800]}')
    for line in r.iter_lines():
        if not line.startswith('data:'):
            continue
        ev = json.loads(line[5:])
        usage = ev.get('usageMetadata') or usage
        for cand in ev.get('candidates') or []:
            for part in (cand.get('content') or {}).get('parts') or []:
                at = round(time.time() - t0, 1)
                call, resp = part.get('toolCall') or part.get('tool_call'), part.get('toolResponse') or part.get('tool_response')
                if call:
                    steps.append({'at_s': at, 'kind': 'look', 'asked': {k: v for k, v in call.items() if k not in ('thoughtSignature',)}})
                elif resp:
                    steps.append({'at_s': at, 'kind': 'came back', 'what': json.dumps(resp, ensure_ascii=False)[:600]})
                elif part.get('thought') and isinstance(part.get('text'), str):
                    if steps and steps[-1]['kind'] == 'note':
                        steps[-1]['text'] += part['text']
                    else:
                        steps.append({'at_s': at, 'kind': 'note', 'text': part['text']})
                elif isinstance(part.get('text'), str):
                    answer.append(part['text'])
out = S.OUT / f'{name[:5]}.looks.T-{thinking}.Q-{quality}.json'
out.write_text(json.dumps({'seconds': round(time.time() - t0, 1), 'usage': usage, 'steps': steps, 'raw': ''.join(answer)}, indent=1, ensure_ascii=False), encoding='utf-8')
print(out.name, round(time.time() - t0, 1), 's', R.cost_of(usage), 'USD', Counter := {k: sum(1 for s in steps if s['kind'] == k) for k in ('look', 'came back', 'note')})
for s in steps:
    print(s['at_s'], s['kind'], (json.dumps(s.get('asked'), ensure_ascii=False) if s['kind'] == 'look' else s.get('what') or s.get('text') or '')[:420].replace('\n', ' '))
