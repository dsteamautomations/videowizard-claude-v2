"""Minor corrections as an edit (SK, 25 Nov 2026: "Approve as written"): step 2 of the references, in the served text.

In v3.json, part `picture-search` (once for each kind of film; the replaced words are in server/retired-sentences.json):
- the answers of step 2: "Minor corrections" corrects the set's own pictures from the operator's words and, on the page, their marks; "Make
  again" is the new set, with their comment (until then: both made a new set from the request written again);
- what the assistant writes: for "Make again" the request again, as before; for "Minor corrections" one where line, or `unclear` with one
  question. The rules of a where line are not written here: the server gives them with the sets that wait (`vw visuals round --rewrite`
  alone, the field `how`), so the instruction grows by the fewest words;
- a correction counts as one of the three makes; all the pictures asked for are corrected, or none;
- a set that was corrected shows the set before and the operator's words, as a set made again does.
In plugin/commands/vw.md the sentence of step 2 says the same (it rides on the next plugin release). Registered in scripts/c1_split_v3.py after specs_card. Exact anchors; applying twice changes nothing.
Run once: python scripts/minor_edit_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [   # (the part, the words before, the words now)
    ('picture-search', 'Minor corrections with their words, or Make again; one click orders the other sets.',
     "Minor corrections (their words and, on the page, their marks: the set's own pictures are corrected, the rest of each kept), or Make again (a new set, "
     'their comment with it); one click orders the other sets.'),
    ('picture-search', 'After Make again or Minor corrections nothing is made until you rewrite that request from their words, your check and your look: '
     'out/round-rewrites.json, rows {element_id, prompt}, sent with `vw visuals round --rewrite out/round-rewrites.json`. The same words are refused, the earlier '
     'request is kept, a rejected picture is never an input, and a set is made three times at most, a make that returned no picture not counted.',
     'After Make again nothing is made until you rewrite that request from their words, your check and your look; after Minor corrections, until you write its '
     'where line, or `unclear` with one question where you cannot tell which thing is meant: `vw visuals round --rewrite` lists the sets that wait, their '
     'pictures as the operator marked them, and how a where line is written. out/round-rewrites.json, rows {element_id, prompt} or {element_id, where}, sent with '
     '`vw visuals round --rewrite out/round-rewrites.json`. The same words are refused, the earlier request is kept, a rejected picture is never an input, a '
     'correction is made in every picture asked for or in none, and a set is made three times at most, a correction counted, a make that returned no picture not counted.'),
    ('picture-search', "a set made again shows the set before and the operator's words.", "a set made again or corrected shows the set before and the operator's words."),
    ('picture-search', "at step 2 a set is made again from the request you rewrite with the operator's words,",
     "at step 2 a set is corrected in its own pictures, or made again from the request you rewrite, with the operator's words,"),
]
COMMANDS = [   # (the old sentence, the new one) in plugin/commands/vw.md
    ('Minor corrections with their words, or Make again (nothing is made until you rewrite that request from their words, `vw visuals round --rewrite out/round-rewrites.json`; '
     'never from a rejected picture; three makes at most, a make that returned no picture not counted)',
     "Minor corrections (their words and, on the page, their marks: the set's own pictures are corrected), or Make again (a new set, their comment with it); nothing is "
     'corrected or made until you write its where line or rewrite that request (`vw visuals round --rewrite` lists what waits and says how, then '
     '`vw visuals round --rewrite out/round-rewrites.json`; a set made again never starts from a rejected picture; three makes at most, a correction counted, a make that '
     'returned no picture not counted)'),
]
RETIRED = ['Minor corrections with their words, or Make again', 'After Make again or Minor corrections nothing is made until you rewrite that request',
           'rows {element_id, prompt}, sent with', 'at step 2 a set is made again from the request you rewrite with']


def apply(prompt, parts):
    """The visuals text with these sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing.
    A part's sentence stands once in the text of one kind of film and once for each kind in v3.json: every place is changed."""
    for where, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == where)
        if old not in part['text'] and new not in part['text']:
            sys.exit('not applied: %s: not found: %s' % (where, old[:60]))
        part['text'] = part['text'].replace(new, old).replace(old, new)   # a place already changed is not changed twice
    return prompt


def before(stage):
    """The visuals stage as it read before this script (for the tests of the earlier scripts)."""
    st = json.loads(json.dumps(stage))
    for where, old, new in PAIRS:
        part = next(p for p in st['parts'] if p['name'] == where)
        part['text'] = part['text'].replace(new, old)
    return st


def before_commands(text):
    """plugin/commands/vw.md as it read before this script."""
    for old, new in COMMANDS:
        text = text.replace(new, old)
    return text


def _write(path, data, raw):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    _write(P, d, raw)
    rp = ROOT / 'server' / 'retired-sentences.json'
    raw = rp.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    _write(rp, r, raw)
    cmd = ROOT / 'plugin' / 'commands' / 'vw.md'
    text = cmd.read_bytes().decode('utf-8')
    for old, new in COMMANDS:
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: plugin/commands/vw.md: not found once: %s' % old[:60])
            text = text.replace(old, new)
    cmd.write_bytes(text.encode('utf-8'))   # bytes: the file keeps its line ends
    print('visuals: Minor corrections corrects the pictures of the set (a where line); Make again is the new set, with the comment')


if __name__ == '__main__':
    main()
