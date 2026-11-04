"""design/151 (SK, 4 Nov 2026): instruction version 3, the visuals stage: the picture search part says the kept round (frames, then every set made
silently, then one shot of verdicts); the later part says what shots bind and names the older way. Exact anchors; run once: python scripts/d151_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

SEARCH_OLD_START = "write out/reference-round.json, one row per element (element_id, its frame reference ids, the two-to-twelve-word keywords you would search), send it"
SEARCH_OLD_END = "Then the picture AI references, sheets and golden pictures (sections 5 and 9, in part-later.md)."
SEARCH_NEW = ("write out/reference-round.json, one row per element: element_id, its frame reference ids, and `prompt` (a thing: the subject block, what the picture must represent, its frame, nobody in it, "
              "never how the work is done; the server adds the kept preamble, the set line, the cosmetics from the plan and the four notes; a person: the why line); "
              "send it (`vw visuals round --file out/reference-round.json`) and give the operator the page link once. A clip frame is free and exact, source and time kept (`vw visuals frame --element E --clip <id> --at <seconds>`); "
              "search the clip analyses first, footage left out of the edit included (not the operator's explicit exclusions), and take the sharpest frame, the subject large and evenly lit, never a blurred one for identity. "
              "A footage frame of a person serves your description only, never the picture AI (a footage frame may still be a video take's start image); the server writes a person's sheet from the plan (description, outfits, place, "
              "your why line, one line against every other person) as three separate pictures: full length, working pose, the face; every worker the words act with is an element (the check warns of one missing).\n"
              "`vw visuals status --wait 900` until the round is complete; ask nothing per element and generate nothing meanwhile. Step 1: each thing gets the footage picture or Ignore this; Done approves the frames and makes "
              "every set at once, silently, by the kept method: two to four separate pictures from real photographs with Google Search on (a thing with an approved frame is made from it; a size still unknown on such a thing is "
              "refused: measure first). Step 2, when every set is back: the operator judges them all in one shot: Yes (ticking the golden picture of a thing, the one every shot starts from; a person's is the full-length front), No, "
              "or Correct it with their words; Done records all; the No and Correct it sets are made again with the words in the prompt, never from a rejected picture, and come back for another step 2. In chat: "
              "`vw visuals round --verdicts out/round-verdicts.json --quote` ({element: {verdict: approve|ignore}}), then `vw visuals round --sets out/round-sets.json --quote` ({element: {verdict: yes|no|correct, words, golden}}). "
              "Refused by name on such a film: the Google Images search, the picks, nothing-fits, the separate golden call; a round answer without `kept` is an older film's and keeps them (search keywords: two to twelve words, the thing and its place or trade): follow the tool's answers. "
              "Meanwhile, for accepted gaps only and without generating or spending, draft the answer forms of every diagram, chart and title card, the drawing and material specs (the client's material and the plan; paid measures "
              "and web figures after the round) and the drawn layouts; nothing new on the page and no question until the round closes, then the drafts' questions as one list; update drafts the round changed. "
              "The operator can add their own picture (`vw visuals supply`) or undo Done on step 1 (`vw visuals round --undo`). Then part-later.md, sections 5 and 9.")
LATER = [
    ("Then one sheet per element from its approved frames and picks (`image --kind sheet --parents F1,W2`, the notes added by the server under their pictures; a person's sheet from your description of them, "
     "with no picture parents) and tell the operator the sheets are on the page to approve.",
     "Then the round's sets (the kept method, part-picture-search.md): every element's set judged on the page in one shot, Yes, No or Correct it (`vw visuals round --sets` in chat); an older film: one sheet per "
     "element from its approved frames and picks (`image --kind sheet --parents F1,W2`; a person's from your description, no picture parents)."),
    (" Then one sheet per object or place: `image --element E --kind sheet --parents F1,W2` from its frames and picks, the notes added by the server under their pictures; a person's sheet from your words only "
     "(build, age, posture, garments and how they are worn, hair, described from their footage pictures; a footage or web picture of a person is never sent to the picture AI); the golden picture (a person: the sheet) is what shots bind.",
     " The golden picture (the ticked picture of a thing's set; a person's full-length front, which brings the face close-up into every shot by default) is what shots bind; a footage or web picture of a person is "
     "never sent to the picture AI. An older film: one sheet per object or place from its frames and picks (`image --kind sheet --parents F1,W2`), a person's from your words, its sheet the golden picture."),
]


def apply_visuals(parts):
    """The same changes on the split's parts (scripts/c1_split_v3.py --check)."""
    parts = {p['name']: p for p in parts}
    t = parts['picture-search']['text']
    if SEARCH_NEW not in t:
        i, j = t.find(SEARCH_OLD_START), t.find(SEARCH_OLD_END)
        if i < 0 or j < 0:
            sys.exit('not applied: picture-search anchors not found')
        parts['picture-search']['text'] = t[:i] + SEARCH_NEW + t[j + len(SEARCH_OLD_END):]
    t = parts['later']['text']
    for old, new in LATER:
        if new in t:
            continue
        if t.count(old) != 1:
            sys.exit(f'not applied: later anchor not found once: {old[:60]}')
        t = t.replace(old, new)
    parts['later']['text'] = t


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    v = next(s for s in d['stages'] if s['name'] == 'visuals')
    apply_visuals(v['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('applied')


if __name__ == '__main__':
    main()
