"""Text overlays (requirements version 3 of 28 Nov 2026, parts I and J): the assembly and delivery steps of instruction version 3.
The package names the overlays and waits for their step; person A goes on through the assembly and the proof film and hands over after it, so the pull,
check, download and opening in Resolve are person B's; no question before the film except a fill with an issue; a change to an overlay after the film.
Writes server/procedures/v3.json. A second run fails (the old text is gone)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

AFTER = ("The server refuses the package while the overlays step is open, the assembly without the package, and again after a gap is recorded anew or an overlay changed: run it again. "
         "Then the assembly below and the proof film, on this computer: person A watches the film with its overlays and hands over after it. "
         "The pull, check, download and opening in Resolve are person B's, after the hand-over (the delivery stage).")
QUESTION = ("No question before the film, with one exception. When the table names a fill with an issue, ask the operator before the build on one card that names each such fill: the shot, its picture, and the issue in plain words "
            "(untagged colour: \"the picture's colour information is missing, so its colours may look different in the film\"; rotation: \"the picture is stored turned on its side\"). The answers per fill: \"Use it as it is\" "
            "(`vw assembly choose --shot S --offset 0 --end trim|hold_last --accept-as-is`, with the fill's default end) or \"Swap it in visuals\" (`vw revise --stage visuals`). Nothing is assumed: the build waits for the answer. "
            "Trims, holds and shaky shots are not asked: every fill uses its default. A change the operator asks for is recorded with `vw assembly choose --shot S --offset f --end trim|hold_last` or `vw assembly stabilize --sub X --choice ffmpeg`.")
CHANGE = (" A change to a text overlay is asked in the operator's words (a marked frame may come with it): record the review as changes, write the changed overlay (`vw overlays change O01 --file <row file>`) or answer the start card "
          "again for the film's look, show the new picture, record the operator's approval; the server makes the changed clip; then `vw delivery bundle` again, `vw assembly build` and `vw assembly render`, and the operator watches again.")

# (stage, the old words, the new words); each is applied to every step that holds the old words, and must fit one step or more
PAIRS = [
    ('assembly', 'once every gap is recorded, `vw delivery bundle`', 'once every gap is recorded and the text overlays are settled, `vw delivery bundle`'),
    ('assembly', 'the raw AI files, the timeline', 'the raw AI files, the approved text overlays as transparent clips on their own tracks with Overlays.csv, the timeline'),
    ('assembly', "The server refuses the assembly without it, and again after a gap is recorded anew: run it again. On the operator's computer (Windows or Mac): `vw pull <code>`, `vw delivery check`, "
                 "`vw delivery download` (no camera copies by default), then `vw delivery open --originals \"<folder>\"` on Resolve Studio. Then the assembly below, the proof copy.",
     AFTER + ' Person B links the camera cuts there with `vw delivery open --originals "<folder>"`.'),
    ('assembly', 'Show the operator that table and ask once', None),   # the whole step: QUESTION
    ('assembly', 'The operator watches AND listens.', 'The film carries the approved text overlays. With the film, say as plain facts, asking nothing: the fills that hold their last frame, and the shots flagged as shaky. The operator watches AND listens.'),
    ('delivery', 'narration, normalised fills', None),   # see below
]
NO_FOOTAGE = ("The server refuses the assembly without it, and again after a gap is recorded anew: run it again. On the operator's computer (Windows or Mac): `vw pull <code>`, `vw delivery check`, "
              "`vw delivery download`, then `vw delivery open` on Resolve Studio.", AFTER)


def _each(steps, old, fn, need=True):
    hit = [i for i, s in enumerate(steps) if old in s]
    assert hit or not need, old[:70]
    for i in hit:
        steps[i] = fn(steps[i])
    return len(hit)


def apply_steps(stages):
    """Also for c1_split_v3.py --check, where a film with footage is served (the steps of a film with no footage are then absent)."""
    st = {s['name']: s for s in stages}
    asm, dl = st['assembly']['steps'], st['delivery']['steps']
    for stage, old, new in PAIRS[:3]:
        _each(asm, old, lambda s, old=old, new=new: s.replace(old, new))
    if _each(asm, NO_FOOTAGE[0], lambda s: s.replace(NO_FOOTAGE[0], NO_FOOTAGE[1]).replace(' Then the assembly below, the proof copy.', ''), need=False):
        assert not any('Then the assembly below, the proof copy.' in s for s in asm)
    _each(asm, 'Show the operator that table and ask once', lambda s: QUESTION)
    _each(asm, PAIRS[4][1], lambda s: s.replace(PAIRS[4][1], PAIRS[4][2]))
    _each(asm, 'On their yes (it must say watched and listened)', lambda s: s + CHANGE)
    _each(dl, '`vw delivery bundle` again writes the full package', lambda s: s + ' The approved text overlays are in it, each on its own track above the picture.')
    _each(dl, "On the operator's computer (Windows or Mac): `vw pull <code>`, then `vw delivery check`",
          lambda s: s.replace("On the operator's computer (Windows or Mac):", 'On the editing computer (person B, after the hand-over; Windows or Mac):', 1)
          + ' The text overlays are on their own tracks: switch those tracks off when comparing with Approved-film.mp4, which already shows them, or they show twice.')


def main():
    raw = open(P, encoding='utf-8', newline='').read()
    d = json.loads(raw)
    try:
        apply_steps(d['stages'])
    except AssertionError as exc:
        sys.exit(f'not applied: {exc}')
    open(P, 'w', encoding='utf-8', newline='').write((json.dumps(d, ensure_ascii=False, indent=2) + '\n').replace('\n', '\r\n' if '\r\n' in raw else '\n'))   # the file's own line ends
    print('assembly and delivery steps written')


if __name__ == '__main__':
    main()
