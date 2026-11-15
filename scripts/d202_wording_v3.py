"""design/202 (SK, 15 Nov 2026): instruction version 3, the visuals stage, the treatment. The picture is chosen from the narration alone (the
script's visual notes are no longer used); meaning before a noun, the real thing first, action first, then the order of the ways; a symbol only
when it reads at a glance; words on the picture by the film's category; each shot's two reasons (`fits_why`, `way_why`). The opening-gap rule
loses its masonry example. Exact anchors, each found once; run once: python scripts/d202_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

CHOOSE = ("the effort, cost or convenience of a route never chooses the medium. Choose from the narration alone: the script's visual notes are not used and not cited. "
          "Choose from what the sentence tells the viewer, not from a noun in it, and show the real, tangible thing before a general view. For anything a camera could film, "
          "first ask who is doing what, and write the picture as a person doing one action that shows the meaning; the order of the ways for a scene is real footage that shows it; "
          "else AI video; else a still, with the reason. Use a symbol only when it reads at a glance; otherwise be literal. Bring the film's key pictures back (the same person, "
          "place or object). A still always moves slowly. Words on the picture: in an advertisement, product or social film, key words, three words or fewer at a time; in a "
          "documentary or explainer, none beyond a diagram's labels (the subtitles carry the words).")
SHOTS = ("and `shots` with each `route` and `seconds`, its `picture`, `fits_why` (why the picture fits the words and what the viewer understands better with it) and `way_why` "
         "(why it is made this way: could a real clip do it, why a diagram and not a photo, why a still and not a video), one or two sentences each, shown to the operator with "
         "the shot; a gap of one way with no `shots` carries the two reasons on its line.")
PAIRS = {
    'treatment': [
        ("the effort, cost or convenience of a route never chooses the medium.", CHOOSE),
        ("Treat the team's intended visuals (the script's visual notes per scene, in the package) as a stated requirement with its source: follow them where they fit the direction "
         "and the footage; say in the treatment why you depart from one. ", ""),
        ("the words under it; the team's intended visuals, cited or departed from with the reason; `picture` in one line;", "the words under it; `picture` in one line;"),
        ("opens on the subject at work, framed wide enough to see where (the mason laying bricks on the half-built wall, the site around), never an empty view of the place;",
         "opens on the subject, framed wide enough to see where, never an empty view of the place;"),
        ("and, for more than one route, `shots` with each `route` and `seconds`.", SHOTS),
    ],
}
PROMPT = [("the package carries the brief and its rules, the team's intended visuals, the world evidence per clip,", "the package carries the brief and its rules, the world evidence per clip,")]


def replace(text, pairs, where):
    for old, new in pairs:
        if new and new in text:
            continue   # applied before
        if text.count(old) != 1:
            if not new and old not in text:
                continue   # a removal applied before
            sys.exit(f'not applied: {where}: not found once: {old[:60]}')
        text = text.replace(old, new)
    return text


def apply(prompt, parts):
    """The visuals prompt and parts with design/202's sentences. Applying twice changes nothing."""
    for name, pairs in PAIRS.items():
        part = next(p for p in parts if p['name'] == name)
        part['text'] = replace(part['text'], pairs, name)
    return replace(prompt, PROMPT, 'prompt')


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals, treatment: the narration alone; action first; the two reasons; words on the picture by category')


if __name__ == '__main__':
    main()
