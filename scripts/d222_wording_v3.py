"""design/222 (SK, 19 Nov 2026): step 7, AI video, on the page.

In v3.json (the later steps, sections 6 and 7): the finished takes are answered on the page once every take is made and checked, never one by one
in the chat; Claude checks each take from frames the server takes from it (`vw visuals pictures --looks`, `vw-take-look` helpers) and Gemini no
longer watches it; "Make another" on the page is the operator's word for one more take, so a second take has no Shoot card; after "done" the chat
says one line with the number of new takes, their length and the amount. The replaced sentences are in server/retired-sentences.json. Registered
in scripts/c1_split_v3.py after design/221f's script. Exact anchors. Run once: python scripts/d222_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

SHOOT_OLD = ('show them the ready-to-shoot card (the guide, the still on its overlay, the words, the cost), then `vw guide shoot --shot S --quote "<their words>"`.')
SHOOT_NEW = (SHOOT_OLD + ' That card is for the first take of a shot. A second take is ordered by the operator on the page ("Make another", with their words): '
             'it is their word, so no card is shown again: say what caused the fault (`vw guide cause`), change that one thing, then `vw guide shoot --shot S`.')
CHECK_OLD = ('Gemini reads every ready take before the operator watches it: anything appearing or vanishing without a cause, the same tools, clothes and faces, '
             'an action repeated without its precondition, a change of shape or size, the planned end. Its marks, with their seconds, are on the take\'s card and in '
             '`vw visuals status`: tell the operator what was marked, then let them watch; they keep the take or ask for another, never taken again on a mark alone. '
             'Fetch each ready take (`vw visuals fetch --job J`) and let the operator watch it; a thumbnail is not a review. Say what you will check (the answer\'s '
             'checklist) and, after they have watched, what you saw, with the measured duration against the placement. On their yes, `vw visuals select --job J '
             '--notes … --quote …` records the review and the selection; on a no, `vw visuals review --job J --decision rejected --notes … --quote …`; a new take '
             'only when the operator asks.')
CHECK_NEW = ('Claude checks every ready take before the operator sees it, from frames the server takes from it (you cannot play a video): '
             '`vw visuals pictures --looks` lists the takes waiting (kind `take`) with the sheet at four frames a second, one frame every half second with its '
             'second, the approved still and five lines (people, the action, objects, bodies and contact, the place and the light); `vw-take-look` helpers judge '
             'them, about three takes each, and send the file; with a fail say what you saw and its second. A take whose check does not come within 30 minutes is '
             'shown as not checked. The server measures the rest: real footage, the length, the first frame, one continuous shot. Nothing of step 7 is asked one '
             'by one: `vw visuals next` and `vw visuals status` give its line of counts ("AI video: 11 made and checked, 4 being made."): say it each time it '
             'changes, as it is, and ask nothing with it. When every take is made and checked the operator answers them on the page (`vw visuals page`), in one '
             'visit: Select (with their reason when the check did not pass it), Make another, or Reject; until then `vw visuals page` answers with the line of '
             'counts and nothing is published. After they say done, `vw visuals page --record` gives one line with the number of new takes ordered, their length '
             'and the amount: say it as it is and ask nothing with it; then, for each, the cause, the one change and the take. A take rejected with no new one '
             'ordered: ask the operator in the chat what happens to the shot (cut it, another angle, or leave it out).')

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one, how many times it is in the text)
    ('later', SHOOT_OLD, SHOOT_NEW, 1),
    ('later', CHECK_OLD, CHECK_NEW, 1),
]

RETIRED = ['Gemini reads every ready take before the operator watches it',                 # Claude checks a take from frames
           'Fetch each ready take (`vw visuals fetch --job J`) and let the operator watch it',   # the takes are answered on the page, all together
           'a new take only when the operator asks']                                       # "Make another" on the page


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
    print('visuals: design/222')


if __name__ == '__main__':
    main()
