"""design/221 phase 1 (SK, 19 Nov 2026): instruction version 3, the visuals stage, and the motion helpers' texts: the brief tells the truth.

In v3.json: the planner times `information_progression` in seconds from the shot's start (row 6); step 6 and step 7 are named apart (row 21);
the font comes first, no brief before it (row 20); the rule writer's questions and notes go to questions.md, which the main assistant decides
(row 15); a verdict on rules written from an older brief is refused and names the changed line (row 14, S3); the operator's answers are logged
as theirs (row 22). In plugin/: the rule writer writes no rule for what the server checks, no palette rule from a palette not yet approved, no
invented numbers, examples from several kinds of film, its questions in questions.md (rows 14, 15); the skill's letter size is for labels and
names questions.md; the builder's agent file names rules.md. The replaced sentences are in server/retired-sentences.json. Registered in
scripts/c1_split_v3.py after design/220's script. Exact anchors, each found once; run once: python scripts/d221_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

FONT_OLD = "Before the first drawn graphic the server asks the film's font in the chat: run `vw font --sample`"
FONT_NEW = ("In Step 6, pictures and drawn graphics, the font comes first: run `vw font` before any brief (`vw motion brief` is refused until the film's motion "
            "style and its font are recorded). If no font is recorded, ask it in the chat with its sample: run `vw font --sample`")
RULES_OLD = ('(it writes work/motion/S/rules.md before anything is drawn); when the brief leaves a fact open, show the operator rules.md and ask them to '
             'tick, strike or add, once.')
RULES_NEW = ('(it writes work/motion/S/rules.md before anything is drawn, and its questions and notes in work/motion/S/questions.md, which is never '
             'uploaded as rules; an upload whose rules hold a list under a Questions or Notes heading is refused). Read every questions.md and decide '
             'each point: a choice with no fact behind it is yours, and you log it (`vw log`); a question about a fact is put to the operator once, with '
             'the other drawings\' questions, before the first drawing is built. An answer the operator gives with the question tool is logged as '
             'theirs (kind `answer`); an answer typed in the chat, log it as theirs: `vw log --kind answer "<their words>"`.')
STALE_OLD = 'a verdict answers every one of them by its words (a failed rule with `where`), or it is refused.'
STALE_NEW = (STALE_OLD + ' A verdict is refused too when the brief changed after the rules were written (a font, the palette, a size): the '
             'refusal names the changed line; read the rules of that drawing again against the new brief, then upload again with them.')

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('common', 'shot.information_progression: what appears, changes and remains, in two to four short steps, for a shot without acting subjects.',
     'shot.information_progression: what appears, changes and remains, in two to four short steps, for a shot without acting subjects; each step '
     "timed in seconds from the shot's start, never in frame numbers of the whole film."),
    ('later', '6. SHOT IMAGES AND VIDEO\nAn AI video shot is made from a guide;',
     '6. SHOT IMAGES AND VIDEO\nTwo steps are named apart: "Step 6, pictures and drawn graphics" (the stills, the graphics in steps and the drawn '
     'shots of section 11, answered on the page) and "Step 7, AI video (in the chat)" (the AI video shots, answered in the chat). Step 7, AI '
     'video: an AI video shot is made from a guide;'),
    ('later', FONT_OLD, FONT_NEW),
    ('later', RULES_OLD, RULES_NEW),
    ('later', STALE_OLD, STALE_NEW),
]

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('agents/vw-motion-rules.md', 'writes work/motion/<shot>/rules.md, the numbered rules the picture must keep.',
     'writes work/motion/<shot>/rules.md, the numbered rules the picture must keep, and work/motion/<shot>/questions.md, its questions and notes.'),
    ('agents/vw-motion-rules.md', '1. **From the brief**: every label word for word and that no other text appears; what appears when (each cued element by '
     "its word's second); the length; the palette; each claim; each size, relationship and proportion of the drawing spec; the view.",
     "1. **From the brief**: that no text other than the brief's labels appears; what appears when (each cued element by its word's second); the "
     'palette, only when the brief marks it approved; each claim; each size, relationship and proportion of the drawing spec, and the sizes the brief '
     'confirms for the things in the shot; the view.'),
    ('agents/vw-motion-rules.md', '(an opening has a lintel; masonry has no continuous vertical joint; a load rests on something; an arrow of heat goes from hot to cold).',
     "(an opening has a lintel; a load rests on something; an arrow of heat goes from hot to cold; a chart's bars start from zero; a product's "
     'buttons sit where the real one has them).'),
    ('agents/vw-motion-rules.md', 'Keep rules concrete and checkable ("the lintel spans the opening and bears on both sides", not "the drawing is accurate").',
     'Keep rules concrete and checkable ("the lintel spans the opening and bears on both sides", "the tallest bar is the year the narration calls the '
     'best", not "the drawing is accurate").'),
    ('agents/vw-motion-rules.md', 'Leave out what the server checks itself and no still frame can show: the length, the frame rate, the sound, and the second each cued element appears.',
     'Write no rule for what the server checks itself: the font, the frame size, the length, the frame rate, the sound, the second each cued element '
     'appears, a label\'s wording and the letter size. Write no "no colour outside the palette" rule while the brief marks the palette "not yet '
     'approved". A rule about the look carries no number the brief does not give (never a size in pixels or a share such as "three quarters" of '
     'your own).'),
    ('agents/vw-motion-rules.md', 'list it at the end under "Questions for the operator", one line each, with why.',
     'write it in `work/motion/<shot>/questions.md`, one line each, with why; a note of yours goes there too. rules.md '
     'holds rules only: a list under a Questions or Notes heading in it is refused at upload.'),
    ('agents/vw-motion-rules.md', 'that keeps the thing apart from what touches it, and list it under "Colours to add"',
     'that keeps the thing apart from what touches it, and list it in questions.md under "Colours to add"'),
    ('agents/vw-motion-rules.md', 'Answer with the number of rules in each group and the questions, if any.',
     'Answer with the number of rules in each group and the number of lines in questions.md.'),
    ('skills/motion/SKILL.md', 'text inside the 80 % title-safe box; text at least 2.6 % of the frame height.',
     'text inside the 80 % title-safe box; every label at least 2.6 % of the frame height.'),
    ('skills/motion/SKILL.md', 'and `refs/` (the approved pictures, to look at).',
     'and `refs/` (the approved pictures, to look at). `questions.md` beside them holds the rule writer\'s questions and notes: they are not rules, '
     'and they are not yours. The main assistant decides each point (a choice with no fact behind it is its own, and logged; a question about a fact '
     'goes to the operator once, with the others, before the first drawing is built).'),
    ('agents/vw-motion-shot.md', 'Work only in `work/motion/<shot>/` inside the run folder: read `brief.md`',
     'Work only in `work/motion/<shot>/` inside the run folder: read `rules.md` (the rules a fact checker holds your frames to; every one must be '
     'plainly true in your drawing), read `brief.md`'),
]


def apply(prompt, parts):
    """The visuals text with this design's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = None if where == 'common' else next(p for p in parts if p['name'] == where)
        text = prompt if part is None else part['text']
        if new in text:
            continue
        if text.count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        text = text.replace(old, new)
        if part is None:
            prompt = text
        else:
            part['text'] = text
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
        if where == 'common':
            st['prompt'] = st['prompt'].replace(new, old)
        else:
            part = next(p for p in st['parts'] if p['name'] == where)
            part['text'] = part['text'].replace(new, old)
    return st


def now(file, text):
    """An earlier script's sentence for one plugin file as it reads after this script (for that script's test)."""
    for f, old, new in HELPERS:
        if f == file and new not in text:
            text = text.replace(old, new)
    return text


def _swap(path, pairs, name):
    """The pairs applied to one text file, each old sentence found once; bytes in and out, so the file keeps its line ends."""
    raw = path.read_bytes()
    end = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf-8').replace('\r\n', '\n')
    for old, new in pairs:
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: %s: not found once: %s' % (name, old[:60]))
            text = text.replace(old, new)
    path.write_bytes(text.replace('\n', end).encode('utf-8'))


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    for name in sorted({h[0] for h in HELPERS}):
        _swap(ROOT / 'plugin' / name, [(old, new) for file, old, new in HELPERS if file == name], 'plugin/' + name)
    print('visuals: design/221 phase 1')


if __name__ == '__main__':
    main()
