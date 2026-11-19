"""design/221 phase 4 (SK, 19 Nov 2026): rows 18 and 19, what the operator is shown while step 6 is made.

In v3.json (section 6 and section 11): step 6 is answered on the page once everything of it is made, never as things become ready; until then the
chat says one line of counts, as it is, asking nothing; a finished drawn graphic is shown in the chat once, asking nothing; each drawn graphic is
rendered as soon as its verdict is clean, never waiting for the others; the still pictures are ordered at the start of the step, beside the drawn
graphics; a drawing with an open must after round 3 is a chat card (select it anyway with a reason, reject it, or one more round, once), no longer
"show the operator the open musts". The replaced sentences are in server/retired-sentences.json. Registered in scripts/c1_split_v3.py after
design/221e's script. Exact anchors; the first is in the text twice and both are changed. Run once: python scripts/d221f_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAGE_OLD = 'The operator answers the pictures and drawn graphics on the page (`vw visuals page`), as they become ready;'
PAGE_NEW = ('The operator answers the pictures and drawn graphics on the page (`vw visuals page`) once everything of step 6 is made, in one visit '
            '(see "While step 6 is made");')
HELD_OLD = 'At most two redo rounds caused by a must, then show the operator the open musts.'
HELD_NEW = ('At most two redo rounds caused by a must. A drawing with a must still open after round 3 is held: render it (`vw motion render --shot S`) and '
            'the chat asks the operator with its card (`vw visuals next`): select it anyway with their reason, reject it (rebuilt from round 1), or '
            '"One more round", allowed once (the server then takes round 4; after it the card offers the first two).')
LAST_OLD = 'uploaded, snapshotted and checked again; its approval stays when the picture is the same.'   # the end of design/221e's still end-frame paragraph
LAST_NEW = (LAST_OLD + ' While step 6 is made: order the still pictures at the start of the step, at the same time as the drawn graphics are begun '
            '(`vw visuals image --shot S --element E --kind keyframe --prompt "…"`); they need nothing from the drawings, and the tool\'s next-step line '
            'counts the still shots with no picture asked for yet. Render each drawn graphic as soon as its verdict is clean; never wait for the others. '
            '`vw visuals next` (when nothing waits for an answer) and `vw visuals status` give a line of counts ("Drawn graphics: 5 made and checked, 3 being '
            'redone, 1 held (needs a decision). Stills: 9 made and checked."): say it to the operator each time it changes, as it is, and ask nothing with '
            'it. A drawn graphic whose render is ready comes once in `vw visuals next` to show with its one line; it asks nothing: the operator judges it on '
            'the page with the others. Nothing of step 6 is put on the page one by one: the page opens when every still, graphic in steps, component and '
            'drawn graphic is made and checked (one that could not be made is listed as such) and every held drawing is answered; until then '
            '`vw visuals page` answers with the line of counts, and nothing is published.')

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one, how many times it is in the text)
    ('later', PAGE_OLD, PAGE_NEW, 2),
    ('later', HELD_OLD, HELD_NEW, 1),
    ('later', LAST_OLD, LAST_NEW, 1),
]

RETIRED = ['as they become ready; a failed line is shown with its words',   # row 18: the page only when everything is made
           'then show the operator the open musts']                        # row 18: the held drawing is a card in the chat


def apply(prompt, parts):
    """The visuals text with this design's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new, n in PAIRS:
        part = None if where == 'common' else next(p for p in parts if p['name'] == where)
        text = prompt if part is None else part['text']
        if new in text:
            continue
        if text.count(old) != n:
            sys.exit('not applied: %s: not found %d times: %s' % (where, n, old[:60]))
        text = text.replace(old, new)
        if part is None:
            prompt = text
        else:
            part['text'] = text
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new, _n in reversed(PAIRS):
        if where == 'common':
            st['prompt'] = st['prompt'].replace(new, old)
        else:
            part = next(p for p in st['parts'] if p['name'] == where)
            part['text'] = part['text'].replace(new, old)
    return st


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    rp = ROOT / 'server' / 'retired-sentences.json'
    r = json.loads(rp.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('visuals: design/221 phase 4')


if __name__ == '__main__':
    main()
