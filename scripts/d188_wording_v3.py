"""design/188 (SK, 12 Nov 2026): instruction version 3, the visuals stage: the operator's decisions are taken in the chat, one at a time, handed out
by the server (`vw visuals next`, `vw visuals decide`); the visuals page is no longer where the operator decides. Release A: the common rule, the
treatment and the plan. Exact anchors; run once: python scripts/d188_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

COMMON = ("E. THE OPERATOR'S DECISIONS, ONE AT A TIME, IN THE CHAT\n"
          "The operator decides everything of this stage here in the chat, never on a page: do not give a page link or say \"on the page\". The server hands out one decision at a time: "
          "`vw visuals next`. It answers with one item (where it is, the question, what to show, the buttons) or with what is being made and that nothing is needed. "
          "Post the item's `message` as your own text, exactly as it is laid out (where it is, what it is about, the lines, the totals), and show its pictures; then ask with the question tool: the question is the item's short `ask` and nothing else, with the item's buttons, in their order, and no others. The operator may always answer in their own words instead. "
          "Record the reply with `vw visuals decide --item <id> --choice <the button's choice> --quote \"<their words>\"` (`--notes` for what to change); its answer already holds the next item: show that one at once. Run `vw visuals next` only to begin, or after waiting for something to be made. "
          "Post only the question: never what you did, how you did it, or a summary of the step. Never show two items, never choose the order, never answer for the operator, never accept several at once: "
          "the server refuses a reply to any item but the one it handed out. A change the operator asks for is yours to make; change only that, send it again, and it returns in its turn.\n"
          "When helpers work at the same time, say so before they start, in these words with the numbers filled in: \"<N> helpers are now working on <what>. There will be some back and forth between them and it takes a few minutes. "
          "You do not need to do anything; I will ask you when the first is ready.\" Each time one finishes, run `vw visuals next` and give its lines as they are; end every such message with the server's last line "
          "(\"Nothing is needed from you now.\" or \"Your answer is needed.\"), so the operator always knows whether to wait.\n\n")

# (where, the start of the passage, its end, the new text): the passage from start to end, both included, is replaced; each found exactly once
SPANS = [
    ('common', 'Reading guide: this file is the common part (sections A to D), read once.', 'Reading guide: this file is the common part (sections A to D), read once.',
     COMMON + 'Reading guide: this file is the common part (sections A to E), read once.'),
    ('treatment', 'on the page (link printed) the operator accepts or sends back with a short note each line', 'the draft command again with --quote "<their yes>".',
     'then `vw visuals next`: the server hands the operator one line at a time, the Direction first, then every gap, and you record each reply with `vw visuals decide` (section E). There is no yes to the whole.'),
    ('plan', 'the operator accepts each gap on the page or in chat (`vw visuals accept --gaps all --quote "…"`, or the gaps named).', 'the operator accepts each gap on the page or in chat (`vw visuals accept --gaps all --quote "…"`, or the gaps named).',
     'then `vw visuals next`: the server hands the operator one gap at a time (an offered choice first, as buttons), and you record each reply with `vw visuals decide` (section E); never `accept --gaps all`.'),
]


# (where, old, new): every occurrence is replaced; the page as the place where the operator decides, taken out of the later steps
SWAPS = [
    ('preparation', 'Give the operator the page link and tell them (never ask', 'Tell the operator (never ask'),
    ('picture-search', 'and give the operator the page link once', 'and run `vw visuals next` (section E)'),
    ('later', ', or Try a fix on the page', ''),
    ('later', 'on the visuals page or in chat', 'in the chat'),
    ('later', "every element's set judged on the page in one shot, Yes, No or Correct it (`vw visuals round --sets` in chat", "every element's set judged in the chat, one at a time (`vw visuals next`, section E; never `vw visuals round --sets` for the operator"),
    ('later', ', or on the page', ''),
    ('later', 'On the visuals page a verdict is one click with no typed words', 'In the chat a verdict is one button with no typed words'),
    ('later', ', or the page', ''),
]


def _replace(text, name, start, end, new):
    if new in text:
        return text   # already applied
    if text.count(start) != 1:
        sys.exit(f'not applied: {name}: the start is not found once: {start[:60]}')
    a = text.index(start)
    b = text.find(end, a)
    if b < 0:
        sys.exit(f'not applied: {name}: the end is not found after the start: {end[:60]}')
    return text[:a] + new + text[b + len(end):]


def apply(prompt, parts):
    """For c1_split_v3.py --check (applied after design/181's)."""
    for where, start, end, new in SPANS:
        if where == 'common':
            prompt = _replace(prompt, where, start, end, new)
        else:
            part = next(p for p in parts if p['name'] == where)
            part['text'] = _replace(part['text'], where, start, end, new)
    for where, old, new in SWAPS:
        part = next(p for p in parts if p['name'] == where)
        part['text'] = part['text'].replace(old, new)
    return prompt


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    words = lambda: sum(len(t.split()) for t in [st['prompt'], *st['steps'], *(p['text'] for p in st['parts'])])
    before = words()
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'visuals instructions: {before} words before, {words()} after')


if __name__ == '__main__':
    main()
