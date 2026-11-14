"""design/193 (14 Nov 2026): instruction version 3. The analysis: Gemini 4 Hydrogen, the look-again way for every clip, the fit by sentence.
The options: each piece's own lines on the list, a related piece is not a direct match, two clips of one subject filmed there and back are one
choice. Exact anchors, each found once; run once: python scripts/d193_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

ANALYSIS_STEP = ('One paid Gemini 3.8 Flash request per clip (agentic for a clip over 15 seconds, plain for a shorter one); tell the operator, do not ask.',
                 'One paid Gemini 4 Hydrogen request per clip, each watched the look-again way; tell the operator, with the likely cost (about 0.33 US dollars a clip), do not ask.')
OPTIONS = [
    ("\n8. Notes: a shot that needs the operator's eye carries a note",
     " Each piece's row carries its own lines: `what` (what this piece shows; `seen` is its whole clip), `does_not_show`, and `fits` (the clip study's fit of this piece to this scene's "
     "sentences: EXACT, PARTLY or RELATED, with the seconds of the clip and what is missing). Choose from these, not from the clip's line. A piece only RELATED to a sentence, or with no fit "
     "for it, is never a direct match for that sentence: place it as B-roll, choose another piece, or leave a blank; the server refuses it otherwise."
     "\n8. Notes: a shot that needs the operator's eye carries a note"),
    ('never side by side at the same shot size.',
     'never side by side at the same shot size. Two clips that show the same subject with the camera moving in opposite directions (a pan one way and back, a move in and out) are one '
     'choice: use one of them, never both in neighbouring shots.'),
]


def _swap(text, where, old, new):
    if new in text:
        return text
    if text.count(old) != 1:
        sys.exit(f'not applied: {where}: not found once: {old[:60]}')
    return text.replace(old, new)


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    an = next(s for s in d['stages'] if s['name'] == 'analysis')
    an['model'], an['paid'] = 'gemini-4-hydrogen', 'gemini-4-hydrogen'
    an['settings'] = {k: v for k, v in {**an['settings'], 'processing_mode': 'AGENTIC', 'fit_unit': 'sentence'}.items() if k != 'agentic_over_seconds'}
    an['steps'] = [_swap(s, 'analysis step', *ANALYSIS_STEP) if isinstance(s, str) and (ANALYSIS_STEP[0] in s or ANALYSIS_STEP[1] in s) else s for s in an['steps']]
    if not any(isinstance(s, str) and ANALYSIS_STEP[1] in s for s in an['steps']):
        sys.exit('not applied: the analysis step that names the model was not found')
    op = next(s for s in d['stages'] if s['name'] == 'options')
    for old, new in OPTIONS:
        op['prompt'] = _swap(op['prompt'], 'options', old, new)
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('analysis: Gemini 4 Hydrogen, look-again for every clip, fit by sentence; options: the piece\'s own lines and the two rules')


if __name__ == '__main__':
    main()
