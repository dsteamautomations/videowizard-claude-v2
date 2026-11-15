"""design/204 (SK, 15 Nov 2026): instruction version 3, the visuals stage, the treatment. The operator answers the treatment on a Claude artifact
page (`vw visuals page`); the card stays for a machine that cannot show the page. One exact anchor, found once; run once: python scripts/d204_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

OLD = ("then `vw visuals next`: the server hands the operator every line on one card, the Direction first, and you record the card with `vw visuals card` (section E; one line at a time "
       "with `vw visuals decide` where the card cannot be shown).")
NEW = ("then `vw visuals page`: the operator answers the Direction, then every gap line, on a page, and nothing is recorded until they say done in the chat. Do what its `how` says, in "
       "order: publish the page once by its file, write each round to it from the round file (type none of it), give the operator the link, and when they say done read their answers "
       "and record them with `vw visuals page --record`. Where the page cannot be shown, say so once and use `vw visuals next`: the server hands the operator every line on one card, "
       "the Direction first, and you record the card with `vw visuals card` (section E; one line at a time with `vw visuals decide` where the card cannot be shown either).")


def apply(prompt, parts):
    """The visuals parts with design/204's sentence; the common part is unchanged. Applying twice changes nothing."""
    part = next(p for p in parts if p['name'] == 'treatment')
    if NEW not in part['text']:
        if part['text'].count(OLD) != 1:
            sys.exit('not applied: treatment: not found once: ' + OLD[:60])
        part['text'] = part['text'].replace(OLD, NEW)
    return prompt


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals, treatment: answered on a page; the card where the page cannot be shown')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
