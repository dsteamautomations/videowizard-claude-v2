"""design/130: the HyperFrames motion route in instruction version 3 (the visuals 'later' part), one exact replacement each.
Writes server/procedures/v3.json. Every old text must occur exactly once (a second run fails on the first pair). Version 2 is not touched."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

SECTION = (
    '\n\n11. DRAWN SHOTS WITH HYPERFRAMES\n'
    'A film draws with HyperFrames unless started with `--drawn svg` (`scene` and `draw` are refused on a motion film); there a diagram, chart, map or timeline '
    'that carries text is a drawn shot, never a painted one. Once a drawn shot\'s pictures and spec are approved: `vw motion brief --shot S` '
    'for each; one `vw-motion-rules` helper per shot, all at once (it writes work/motion/S/rules.md before anything is drawn); when the brief leaves a fact open, '
    'show the operator rules.md and ask them to tick, strike or add, once. Then one `vw-motion-shot` helper per shot, three or four at once, given only the shot id; '
    'each builds, uploads, checks and snapshots on the server and answers with its last upload\'s sha256 (with no pictures it stops at a still key frame first). '
    'Snapshot each shot at its beats with crops of the parts its rules name (`vw motion snapshot --shot S --at … --crop …`), then a fresh `vw-motion-check` helper per '
    'shot with the round number, and `vw motion verdict --shot S --file work/motion/S/check-N.json`. Failed rules go to a new `vw-motion-shot` helper with only '
    'those rules; at most two redo rounds, then show the operator the open rules. Put `scene_motion: {sha256, labels, cues}` on the shot (labels word for word; '
    'cues `{selector: "#id", word or at_s}`), propose the revision, then `vw motion render --shot S` (free; it checks the timing). It is selected like a take; '
    'a drawing without a clean verdict of its project is held. A correction the operator makes that holds for the subject: `vw motion rule --subject … --add "…" --quote "…"`.')

PAIRS = [
    # part, change, old, new
    ('later', 'M1', "takes the drawn route: `visual_type: drawn`, named so in the plan; its `scene_svg` comes after",
     "takes the drawn route: `visual_type: drawn`, named so in the plan; on a motion film (the default) it is made with HyperFrames (section 11); "
     "on a `--drawn svg` film its `scene_svg` comes after"),
    ('later', 'M2', '`vw visuals supply --element E --file in/brand/<name>`.', '`vw visuals supply --element E --file in/brand/<name>`.' + SECTION),
]


def apply_visuals(parts):
    """For c1_split_v3.py --check (applied after design/126's)."""
    for name, change, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == name)
        assert part['text'].count(old) == 1, (change, old[:60])
        part['text'] = part['text'].replace(old, new)


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    before = sum(len(p['text'].split()) for p in st['parts'])
    try:
        apply_visuals(st['parts'])
    except AssertionError as exc:
        sys.exit(f'not applied: {exc}')
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(PAIRS)} replacements written; visuals parts {before} -> {sum(len(p["text"].split()) for p in st["parts"])} words')


if __name__ == '__main__':
    main()
