"""design/206 (SK, 16 Nov 2026): instruction version 3, the visuals stage, the plan. The operator answers the plan on the Claude artifact page
(`vw visuals page`), every question in one visit; the card stays for a machine that cannot show the page. Exact anchors, each found once; run
once: python scripts/d206_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

OLD = ("then `vw visuals next`: the server asks an offered choice first, as buttons, then hands the operator the gaps on one card, and you record the card with `vw visuals card` "
       "(section E; one gap at a time with `vw visuals decide` where the card cannot be shown); never `accept --gaps all`.")
NEW = ("then `vw visuals page`: the operator answers the whole plan on the page in one visit (a change of the shared rules, a gap offered two ways with each way's shots, every "
       "gap's shots as a table), and nothing is recorded until they say done in the chat. Do what its `how` says, then `vw visuals page --record`; change what they sent back, "
       "propose again, and `vw visuals page` again. Where the page cannot be shown, say so once and use `vw visuals next`: the server asks an offered choice first, as buttons, "
       "then hands the operator the gaps on one card, and you record the card with `vw visuals card` (section E; one gap at a time with `vw visuals decide` where the card "
       "cannot be shown either); never `accept --gaps all`.")
STEP = (2, '`vw visuals propose`; the operator accepts each gap (`vw visuals accept`);',
        '`vw visuals propose`; `vw visuals page`: the operator answers every gap on the page, recorded on their done (`vw visuals page --record`), the card where it cannot be shown;')


def apply(prompt, parts):
    """The visuals parts with design/206's sentence; the common part is unchanged. Applying twice changes nothing."""
    part = next(p for p in parts if p['name'] == 'plan')
    if NEW not in part['text']:
        if part['text'].count(OLD) != 1:
            sys.exit('not applied: plan: not found once: ' + OLD[:60])
        part['text'] = part['text'].replace(OLD, NEW)
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
    print('visuals, plan: answered on the page in one visit; the card where the page cannot be shown')


if __name__ == '__main__':
    main()
