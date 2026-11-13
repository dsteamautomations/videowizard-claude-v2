"""design/190 (SK, 13 Nov 2026): instruction version 3, the visuals stage: the treatment's lines and the plan's gaps are answered on one card
and submitted once (`vw visuals card`); one at a time stays for every other decision, and for a machine that cannot show the card
(`vw visuals next --one`). Exact anchors, each found once; run once: python scripts/d190_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

CARD = ("THE CARD, FOR THE TREATMENT AND THE PLAN. For the treatment's lines and for the plan's gaps the server answers `vw visuals next` with a card instead of one item: "
        "every entry of the step on one card, answered by the operator and submitted once. The tool saves the card as a file and names it. Say the one line it gives, then show the card "
        "with the card tool (`mcp__visualize__show_widget`): its `widget_code` is the whole text of the card file, character for character. Never write the card yourself, never change a word "
        "of it, never call `read_me` for it, and do not post the entries as text as well. Then wait; ask nothing else. When the operator presses Submit all, one message arrives: "
        "\"Card answers: {…}\". Write the part from { to } as it is into the answers file the tool named and run `vw visuals card --file <that file>`: one call records every answer and "
        "brings what comes next. If the operator answers in words instead of on the card, write the same file from their words. A card is recorded once. Never send an answer the operator "
        "did not give, and never fill in an entry they left open. If the card tool is not there or fails, run `vw visuals next --one` and go on one at a time. A long plan comes as "
        "several cards, one after another.\n")

# (where, old, new): each old found exactly once
SWAPS = [
    ('common', 'make; change only that, send it again, and it returns in its turn.\n', 'make; change only that, send it again, and it returns in its turn.\n' + CARD),
    ('treatment', 'the server hands the operator one line at a time, the Direction first, then every gap, and you record each reply with `vw visuals decide` (section E). There is no yes to the whole.',
     'the server hands the operator every line on one card, the Direction first, and you record the card with `vw visuals card` (section E; one line at a time with `vw visuals decide` where the card cannot be shown). There is no yes to the whole.'),
    ('plan', 'the server hands the operator one gap at a time (an offered choice first, as buttons), and you record each reply with `vw visuals decide` (section E); never `accept --gaps all`.',
     'the server asks an offered choice first, as buttons, then hands the operator the gaps on one card, and you record the card with `vw visuals card` (section E; one gap at a time with `vw visuals decide` where the card cannot be shown); never `accept --gaps all`.'),
]


def _swap(text, where, old, new):
    if new in text:
        return text   # already applied
    if text.count(old) != 1:
        sys.exit(f'not applied: {where}: not found once: {old[:60]}')
    return text.replace(old, new)


def apply(prompt, parts):
    """For c1_split_v3.py --check (applied after design/188's)."""
    for where, old, new in SWAPS:
        if where == 'common':
            prompt = _swap(prompt, where, old, new)
        else:
            part = next(p for p in parts if p['name'] == where)
            part['text'] = _swap(part['text'], where, old, new)
    return prompt


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals instructions: the card is in section E, the treatment and the plan')


if __name__ == '__main__':
    main()
