"""design/194 (14 Nov 2026): instruction version 3, the visuals stage only. Accurate images: a thing that must be right is drawn before the
reference round (`vw drawing set`, the `vw:drawing` skill) and the operator approves the drawings; an AI video shot's drawing is made from its
scene and approved before the still; the still may name a look reference. Exact anchors, each found once; run once: python scripts/d194_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

DRAW_FIRST = ("A thing whose construction, pattern or mechanism must be right in a picture, or which a picture AI is unlikely to know, is drawn before the round: load the `vw:drawing` skill; "
              "a `vw-drawing` helper writes its drawing set as data (its facts, each with its source or marked assumed; its pieces in real sizes; its views) and sends it, "
              "`vw drawing set --element E --file work/drawing/E/set.json` (free; the server draws every view and refuses a faulty set in plain words). `vw visuals next` then shows the operator "
              "the labelled sheets with the sources and the assumed sizes, and they answer Yes or Correct it. Approved drawings go with that thing's set by themselves, with the words that explain "
              "them and its facts. Where the footage and the plan's sizes disagree, draw from the footage and tell the operator in one line. A loose or living thing gets a form sheet; "
              "a person never gets a drawing set.\n")
WAIT = "`vw visuals status --wait 900` until the round is complete; ask nothing per element and generate nothing meanwhile."
PAIRS = {
    'picture-search': [
        (WAIT, DRAW_FIRST + WAIT),
        ("(a thing with an approved footage picture gets no AI set: that picture is its reference and its golden picture)",
         "(a thing with an approved footage picture and no approved drawings gets no AI set: that picture is its reference and its golden picture; "
         "with approved drawings its set is made from the footage picture and the drawings)"),
    ],
    'later': [
        ("the server refuses it before any spend and says why); the check frames (`vw guide frames`);",
         "the server refuses it before any spend and says why, a posture no person can hold included: a hand behind the shoulders, a body turned away from what it watches); "
         "the server draws the shot from the scene, each person with front, back and working arm marked (free), and `vw visuals next` asks the operator whether the shot is laid out right "
         "(`vw guide drawing`): no still before their Yes; the check frames (`vw guide frames`);"),
        ("the still, made on GPT image from the guide's first frame (`vw guide still`, paid);",
         "the still, made on GPT image from the guide's first frame and the shot's drawings, which the server adds by itself with the words that explain them (`vw guide still`, paid; "
         "`\"look\"` in its file names an approved picture whose look is to be kept, when a still comes out looking drawn);"),
    ],
}


def apply(prompt, parts):
    """The visuals parts with design/194's sentences; the common part is unchanged. Applying twice changes nothing."""
    for name, pairs in PAIRS.items():
        part = next(p for p in parts if p['name'] == name)
        for old, new in pairs:
            if new in part['text']:
                continue
            if part['text'].count(old) != 1:
                sys.exit(f'not applied: {name}: not found once: {old[:60]}')
            part['text'] = part['text'].replace(old, new)
    return prompt


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals: a thing drawn before the round; the shot\'s drawing before the still; the look reference')


if __name__ == '__main__':
    main()
