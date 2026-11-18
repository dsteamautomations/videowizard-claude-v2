"""design/217 (18 Nov 2026): instruction version 3, the visuals stage: step 6 "Pictures and drawn graphics" on the page, and Claude's check.

Five sentences change. The check of a step-6 picture is Claude's (`vw visuals pictures --looks`, helpers above five pictures, "not checked"
after 30 minutes), the operator answers step 6 on the page, and the fix round is retired for "Correct it" (C1-C3, D3); a component is
approved by Claude's check, never asked (D4), and made in the style only when the film has one (D5); the style sheet only when the plan has
a graphic in steps (D5); repeated background figures are a line of Claude's check (C5); a fact check answers every rule the server holds (C6).
The older sentences are listed in server/retired-sentences.json. Registered in scripts/c1_split_v3.py after design/216b's script. Exact
anchors; one sentence is in the text twice and both are changed. Run once: python scripts/d217_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('later', 'A failed check marks the picture and shows its lines; a fix is made only on request: `vw visuals fix --ref R` (paid: tell the operator the line and the cost).',
     "On a film whose reference round is of the new kind, Claude checks every still, step of a graphic, style sheet and component before the operator sees it: "
     "`vw visuals pictures --looks` lists the pictures waiting with their lines; answer every line from what you see in the picture (up to five pictures yourself, more with "
     "`vw-picture-look` helpers, about five each) and send the file; a picture whose check does not come within 30 minutes is shown as not checked. The operator answers "
     "the pictures and drawn graphics on the page (`vw visuals page`), as they become ready; a failed line is shown with its words, and a picture is changed only by "
     '"Correct it", its box opened with those words (the fix round is retired).'),
    ('later', 'made in the approved style (the style picture is Image 1, added by the server) on a transparent background, checked for one thing alone with a clean edge and a '
              'transparent PNG, approved on the Pictures step like any picture,',
     'made in the approved style when the film has a style sheet (the style picture is Image 1, added by the server) on a transparent background, checked for one thing alone '
     "with a clean edge and a transparent PNG, approved by Claude's check and never asked of the operator (it is judged with its drawing),"),
    ('later', 'and `vw motion verdict --shot S --file work/motion/S/check-N.json`.',
     'and `vw motion verdict --shot S --file work/motion/S/check-N.json`: the server holds the rules of rules.md sent with the upload, and a verdict answers every one of '
     'them by its words (a failed rule with `where`), or it is refused.'),
    ('plan', '`status.figure_repeats` names repeated background figures.',
     "on a film whose reference round is of the new kind a background figure repeated from another picture of the scene is a line of Claude's check; before, "
     '`status.figure_repeats` names repeated background figures.'),
    ('plan', 'made first as a style sheet (`vw visuals image --element _STYLE --kind style --answer …`),',
     'made first as a style sheet when the plan has a graphic in steps (`vw visuals image --element _STYLE --kind style --answer …`; a film whose graphics are all drawn has none),'),
]
RETIRED = ['a fix is made only on request: `vw visuals fix --ref R`', 'approved on the Pictures step like any picture',
           'made first as a style sheet (`vw visuals image --element _STYLE --kind style']


def apply(prompt, parts):
    """The visuals text with this design's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = None if where == 'common' else next(p for p in parts if p['name'] == where)
        text = prompt if part is None else part['text']
        if old not in text:
            if new in text:
                continue
            sys.exit('not applied: %s: not found: %s' % (where, old[:60]))
        text = text.replace(old, new)
        if part is None:
            prompt = text
        else:
            part['text'] = text
    return prompt


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals: design/217')


if __name__ == '__main__':
    main()
