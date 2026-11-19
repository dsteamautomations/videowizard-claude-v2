"""design/221 (SK, 19 Nov 2026): the critic's seven points on phase 2 (design/_work/design221-critic-phase2.md) and phase 3b, row 2.

In v3.json: the labels and cues of every drawn shot go in the plan with the plan, before the first brief, with no sha256 (plan part); a clean
verdict binds the passed project to its shot and the render needs no plan change (the sentence that put the sha in the plan and proposed a revision
per drawing is retired; section 11). In plugin/: the planner writes `scene_motion` with the plan; the checker names the four must kinds word for word. The replaced sentences are in server/retired-sentences.json. Registered in scripts/c1_split_v3.py after design/221c's script.
Exact anchors, each found once; run once: python scripts/d221d_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PLAN_OLD = 'A flow the film\'s motion style does not allow is warned.'
PLAN_NEW = (PLAN_OLD + ' A drawn shot of a HyperFrames film carries its texts and cues in the plan, with the plan, before the first brief: '
            '`scene_motion: {labels, cues}` (labels: every text the viewer reads, word for word, never the corner note, which is the server\'s; cues '
            '`{selector: "#id", word or at_s}`; no sha256: the server binds the project that passes its fact check). A drawing with no text at all has '
            '`labels: []`. `vw motion brief` is refused while a drawn shot that carries text has none.')
BIND_OLD = ('Put `scene_motion: {sha256, labels, cues}` on the shot (labels word for word, never the spec\'s not-to-scale note: the server draws it in the '
            'lower right corner of every frame; cues `{selector: "#id", word or at_s}`), propose the revision, then `vw motion render --shot S` (free; it '
            'checks the timing).')
BIND_NEW = ('A clean verdict (no failed must, nothing not seen) binds: the server binds the project that passed to its shot, and nothing goes in the plan '
            '(the labels and cues are there from the start; never the corner note: the server draws it in the lower right corner of every frame). Then '
            '`vw motion render --shot S` (free; it checks the timing). A later upload of the shot is bound only by its own clean verdict.')

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('plan', PLAN_OLD, PLAN_NEW),
    ('later', BIND_OLD, BIND_NEW),
]

GAPS_OLD = 'One camera flow per shot; fixed when in doubt.'
GAPS_NEW = (GAPS_OLD + '\n- `scene_motion` on a drawn shot of a HyperFrames film, with the plan: `{labels, cues}`. Labels: every text the viewer reads, '
            'word for word, never the corner note (the server draws it). Cues: `{selector: "#id", word or at_s}`, a word of the narration or a second of '
            'the shot. No `sha256`: the server binds the project that passes its fact check. A drawing with no text at all has `labels: []`.')
KIND_OLD = 'then write "class": "must" and in "kind" that kind in one line.'
KIND_NEW = ('then write "class": "must" and in "kind" that kind in its words: "a wrong count", "a wrong fact", "a part that reads as something else" or '
            '"a label that cannot be read" (any other kind is a should).')

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('agents/vw-plan-gaps.md', GAPS_OLD, GAPS_NEW),
    ('agents/vw-motion-check.md', KIND_OLD, KIND_NEW),
]

RETIRED = ['Put `scene_motion: {sha256, labels, cues}` on the shot',
           'propose the revision, then `vw motion render --shot S`',
           'and in "kind" that kind in one line']


def apply(prompt, parts):
    """The visuals text with this design's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = None if where == 'common' else next(p for p in parts if p['name'] == where)
        text = prompt if part is None else part['text']
        if new in text:
            continue
        if text.count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        text = text.replace(old, new)
        if part is None:
            prompt = text
        else:
            part['text'] = text
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
        if where == 'common':
            st['prompt'] = st['prompt'].replace(new, old)
        else:
            part = next(p for p in st['parts'] if p['name'] == where)
            part['text'] = part['text'].replace(new, old)
    return st


def now(file, text):
    """An earlier script's sentence for one plugin file as it reads after this script (for that script's test)."""
    for f, old, new in HELPERS:
        if f == file and new not in text:
            text = text.replace(old, new)
    return text


def _swap(path, pairs, name):
    """The pairs applied to one text file, each old sentence found once; bytes in and out, so the file keeps its line ends."""
    raw = path.read_bytes()
    end = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf-8').replace('\r\n', '\n')
    for old, new in pairs:
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: %s: not found once: %s' % (name, old[:60]))
            text = text.replace(old, new)
    path.write_bytes(text.replace('\n', end).encode('utf-8'))


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    for name in sorted({h[0] for h in HELPERS}):
        _swap(ROOT / 'plugin' / name, [(old, new) for file, old, new in HELPERS if file == name], 'plugin/' + name)
    rp = ROOT / 'server' / 'retired-sentences.json'
    r = json.loads(rp.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('visuals: design/221, the critic\'s seven points and phase 3b')


if __name__ == '__main__':
    main()
