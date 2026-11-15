"""design/205 (SK, 15 Nov 2026): instruction version 3, the visuals stage, the treatment. The Direction is written, sent and answered alone before
any gap line is written; the motion style is chosen on the page; a still that must be read is held steady; the film's beats are not a fixed count.
Exact anchors, each found once; run once: python scripts/d205_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [
    ('A still always moves slowly.',
     'A still moves slowly; one the viewer must read (a document, a page, a sign) is held steady, your call.'),
    ('`shape`, the film from its opening to its end in three to five beats;',
     '`shape`, the film from its opening to its end in beats: one beat for each turn in what the viewer learns, as many as the film\'s length needs (about three in a one-minute film);'),
    ('Send the draft (`vw visuals treatment --file out/visual-treatment.json`); then `vw visuals page`: the operator answers the Direction, then every gap line, on a page, and nothing is '
     'recorded until they say done in the chat.',
     'Write the Direction alone first: send a draft that holds only the Direction (`vw visuals treatment --file out/visual-treatment.json`, no `gaps` in it), then `vw visuals page`: on a '
     'page the operator chooses the film\'s motion style (asked once; the page shows every style and the recommended one with its reason) and answers the Direction; nothing is recorded '
     'until they say done in the chat. Write no gap line before the Direction is accepted. Then write every gap line from the accepted Direction, send the whole treatment with the '
     'Direction unchanged, and `vw visuals page` again for the gap lines.'),
]
STEP = (1, 'Treatment (part-treatment.md): the direction, then one line per gap in out/visual-treatment.json; `vw visuals treatment --file out/visual-treatment.json` sends the draft; then',
        'Treatment (part-treatment.md): the Direction alone first, sent (`vw visuals treatment --file out/visual-treatment.json`) and answered on the page; then one line per gap, sent with '
        'the Direction unchanged; each time')


def apply(prompt, parts):
    """The visuals parts with design/205's sentences; the common part is unchanged. Applying twice changes nothing."""
    part = next(p for p in parts if p['name'] == 'treatment')
    for old, new in PAIRS:
        if new not in part['text']:
            if part['text'].count(old) != 1:
                sys.exit('not applied: treatment: not found once: ' + old[:60])
            part['text'] = part['text'].replace(old, new)
    return prompt


def apply_steps(steps):
    i, old, new = STEP
    if new not in steps[i]:
        if steps[i].count(old) != 1:
            sys.exit('not applied: step %d: not found once: %s' % (i, old[:60]))
        steps[i] = steps[i].replace(old, new)
    return steps


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    apply_steps(st['steps'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals, treatment: the Direction alone first; the motion style on the page; a still that must be read; beats')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
