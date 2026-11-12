"""design/181 and integration step E (SK, 12 Nov 2026): instruction version 3, the visuals stage: an AI video shot is made from a guide (the vw:guide
skill), a take is 3 to 15 s, a shot may be a short cut of 1 s or more, one still per shot; the picture-to-video take (bind, packet, start and end
image, prepare-take, take) is retired from the text. Exact anchors; run once: python scripts/d181_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

# (where, the start of the passage, its end, the new text). The passage from start to end, both included, is replaced; each start and end is found exactly once.
SPANS = [
    ('common', "- AI video (`video`): a take driven by an approved start image", "A video shot longer than 10 seconds is refused: split it.",
     "- AI video (`video`): a take made from a guide: plain boxes rendered by the server, a still made from the guide's first frame, and the video model's edit of the guide "
     "(the `vw:guide` skill holds every step). It is one action per shot, of three kinds: a walker; one action, close; a transfer, close, ending before the set-down. "
     "A take is 3 to 15 seconds; a shot may be a short cut of 1 second or more; a video shot longer than 15 seconds is refused: split it. "
     "Any other kind (a crowd, a vehicle, a run, a door, night, people speaking) is not yet available as AI video: make it footage, a still or a drawn shot."),
    ('plan', "AI video 2 to 10 s on screen (made at 3 s", "longer refused)",
     "AI video 1 to 15 s on screen (a take is made at 3 s or more and trimmed; under 1 s use a picture; over 15 s refused; an action of 9 s or more is better as two shots cut on the action)"),
    ('plan', "(the 10 s limit and", "(the 10 s limit and", "(the 15 s limit and"),
    ('treatment', "`images`, a whole number for the gap (a count, never a list: one start image per video segment", "must be exact);",
     "`images`, a whole number for the gap (a count, never a list: one still per AI video shot); an AI video shot is one action, at most four people, nobody crossing, "
     "hand work close and in the right hand, every transfer named and close; a picture that needs more is re-staged, or is footage, a still or a drawn shot; "
     "a line that rests on a rule on trial says so;"),
    ('later', "Bind each video shot once its references are approved:", "one approval wave per shot.",
     "An AI video shot is made from a guide; load the `vw:guide` skill and follow it. In order: a `vw-guide-scene` helper writes the scene description "
     "(`vw guide scene --shot S --file …`; the server refuses it before any spend and says why); the check frames (`vw guide frames`); a fresh `vw-guide-check` helper's "
     "verdict (`vw guide verdict`); the server renders the guide; the still, made on GPT image from the guide's first frame (`vw guide still`, paid); the operator approves "
     "it on its overlay (`vw guide look`, `approve`, or `repair`, or `reject`); the take's words (`vw guide prompt`). Every video shot in which a subject acts lists its "
     "`changes`, each with the beat that causes it; nothing appears, vanishes or grows without a subject doing it in the shot's seconds. A passage longer than one take is "
     "several shots, each with its own guide and still, cut where an action begins or ends, never at a round number of seconds."),
    ('later', "Look at the approved keyframe before writing the movement;", "paid, tell the operator).",
     "The take is paid for only on the operator's word: show them the ready-to-shoot card (the guide, the still on its overlay, the words, the cost), then "
     "`vw guide shoot --shot S --quote \"<their words>\"`. A rejected take needs its cause before another (`vw guide cause`): the first frame against the still, then the "
     "guide, only then the words; the same request is never sent twice, and after two rejected takes from one camera the shot is cut, re-angled or left out."),
    ('later', "(a start keyframe for a video shot only after that shot's `bind` and `packet`;", "(a start keyframe for a video shot only after that shot's `bind` and `packet`;",
     "(never a start keyframe for a video shot: its still is made from its guide;"),
    ('later', "Video shots first: `bind --shot S --refs E1=R1,R2 E2=R3`", "(the server refuses it).",
     "Video shots: the guide, its still and its take, by the `vw:guide` skill; the older `bind`, `packet`, start image, `prepare-take` and `take` are retired for them (the server refuses each by name)."),
    ('later', "Video shots: every take is Gemini Omni, 3 to 10 s;", "fails the must line 'camera drift' with the figure on its card).",
     "Video shots: every take is an edit of a guide, 3 to 15 s, as long as its guide; a longer passage is split into shots, cut where an action begins or ends; a take is "
     "selected with where it starts in its slot (`select --job J --in-s 0.4`; with none, the slot sits in the middle of the take)."),
    ('later', "read the reply of each `prepare-take`:", "then `take --shots all` (paid; inform)",
     "then `vw guide shoot` for each shot the operator says to shoot (paid; ask)"),
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
    """For c1_split_v3.py --check (applied after design/151's)."""
    for where, start, end, new in SPANS:
        if where == 'common':
            prompt = _replace(prompt, where, start, end, new)
        else:
            part = next(p for p in parts if p['name'] == where)
            part['text'] = _replace(part['text'], where, start, end, new)
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
