"""design/203 (SK, 15 Nov 2026): instruction version 3, the visuals stage, the treatment. The Direction is written as six short labelled
parts (`direction_parts`): the idea in one sentence, who it is for and what it must do, whose story, how it should feel, how the film moves,
what each kind of picture does; and a second Direction that differs in kind when the operator asks for one (`direction_alternative`).
One exact anchor, found once; run once: python scripts/d203_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

OLD = ("`direction` comes first (refused without), the central creative choice: a few lines (at most 2000 characters) on what the audience should understand or feel by the end, "
       "the storytelling viewpoint, the principal visual approach and why, and the roles of footage, stills, generated scenes and graphics;")
NEW = ("The Direction comes first (refused without), the central creative choice, written as `direction_parts`, six short parts in this order, two or three sentences each: "
       "`idea`, the film's one idea in one sentence (if it cannot be said in one, the idea is not clear yet); `purpose`, who the film is for and what it must do, taken from the "
       "brief (where the Direction departs from the brief, say so there); `viewpoint`, whose story it is: One viewpoint, held for the whole film; `feel`, what the viewer should "
       "feel, tied to concrete choices of pace, light and movement (\"cinematic\" or \"immersive\" alone is not a tone); `shape`, the film from its opening to its end in three to "
       "five beats; `pictures`, what real footage, generated scenes and graphics each do and why, how each follows from the idea, and what the film will not do. Be specific and "
       "committed (\"short scenes of one person doing one thing\", not \"a mix of techniques\"). The server joins the parts into `direction` under their headings, refuses a part "
       "over its length (160, 300, 200, 300, 400 and 500 characters) and shows the operator a part not given as not given. When the operator asks for a different direction, keep "
       "the first, write a second in `direction_alternative` (its six parts, `answers_brief`, `risk`) that differs in viewpoint or approach, not in wording, and give each of the "
       "two how it answers the brief and what it risks (the first's in `direction_answers_brief` and `direction_risk`); the operator takes one;")


def apply(prompt, parts):
    """The visuals parts with design/203's sentences; the common part is unchanged. Applying twice changes nothing."""
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
    print('visuals, treatment: the Direction in six parts; a second Direction that differs in kind')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
