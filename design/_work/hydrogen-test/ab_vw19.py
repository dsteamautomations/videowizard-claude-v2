"""Phase 1, test 6 (14 Nov 2026): for each sentence, today's pick and the new pick as two short video files, A and B, with no names, for a person to judge.
Which is which is drawn by lot and kept in key.json (not to be opened before judging). Reads VW-19's clips (read only); writes model-test/out-vw19-ab/.
  python -X utf8 ab_vw19.py"""
import json
import random
import subprocess

import phase1_vw19 as P
import run_vw19_hydrogen as R

OUT = R.HERE / 'out-vw19-ab'
OUT.mkdir(exist_ok=True)
new = {s['n']: s for s in json.loads((P.OUT / 'new-cut.json').read_text(encoding='utf-8'))['sentences']}
today = P.todays_cut()
rng = random.Random(1911)
key, sheet = {}, ['# VW-19: today\'s pick against the new pick, sentence by sentence', '',
                  'For each sentence there are up to two files, A and B. One is the footage placed in today\'s cut, the other is the footage chosen from Gemini 4 Hydrogen\'s sentence fit. Which is which was drawn by lot; the key is in `key.json`: open it only after marking.',
                  '', 'Watch each file and mark it: **shows exactly this**, **partly**, or **not**. Then say which is better, or "neither, leave a blank".', '',
                  'The files are in `C:\\Coworkspace\\Review Videobuilder Tool\\model-test\\out-vw19-ab\\`.', '']


def cut(shots, path):
    """The shots of one side, joined into one small file (640 px wide, no sound)."""
    parts = []
    for i, s in enumerate(shots):
        part = OUT / f'_{path.stem}_{i}.mp4'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f"{s['from_s']:.2f}", '-to', f"{s['to_s']:.2f}", '-i', str(R.RUN_DIR / 'in' / s['clip']), '-an', '-vf', 'scale=640:-2', '-r', '25',
                        '-c:v', 'libx264', '-crf', '26', '-preset', 'veryfast', str(part)], check=True)
        parts.append(part)
    lst = OUT / f'_{path.stem}.txt'
    lst.write_text(''.join(f"file '{p.name}'\n" for p in parts), encoding='utf-8')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(path)], check=True, cwd=str(OUT))
    for p in parts + [lst]:
        p.unlink()


for s in P.SENT:
    n = s['n']
    t = [x for x in today if x['sentence'] == s['id']]
    w = new[n]['shots'] if n in new else []
    same = [(x['clip'], round(x['from_s']), round(x['to_s'])) for x in t] == [(x['clip'], round(x['from_s']), round(x['to_s'])) for x in w]
    sides = [('today', t), ('new', w)]
    rng.shuffle(sides)
    key[n] = {}
    sheet += [f"## Sentence {n} ({s['seconds']} s)", '', f"> {s['text']}", '']
    for letter, (who, shots) in zip('AB', sides):
        key[n][letter] = {'who': who, 'shots': [{k: x[k] for k in ('clip', 'from_s', 'to_s')} for x in shots]}
        if shots:
            cut(shots, OUT / f'S{n:02d}-{letter}.mp4')
            sheet.append(f"- **{letter}:** `S{n:02d}-{letter}.mp4` ({sum(x['to_s'] - x['from_s'] for x in shots):.1f} s, {len(shots)} shot{'s' if len(shots) != 1 else ''}). Mark: ")
        else:
            sheet.append(f'- **{letter}:** no footage: a blank for an AI-made video or a graphic. Is a blank right here? ')
    if same:
        sheet.append('- A and B are the same footage here.')
    sheet += ['- Better: ', '']
(OUT / 'key.json').write_text(json.dumps(key, indent=1), encoding='utf-8')
(OUT / 'sheet.md').write_text('\n'.join(sheet) + '\n', encoding='utf-8')
print('files:', sorted(p.name for p in OUT.glob('S*.mp4')))
