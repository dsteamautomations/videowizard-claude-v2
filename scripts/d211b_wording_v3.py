"""design/211, part B (the sets): instruction version 3, the visuals stage. The sentences of the picture search that part B owns (design/211
section 3.12), and the same ones in the plugin's command file: a row of the round file is a proposal with its reason, and `prompt` holds
only what the plan does not say; the three views of a set, by kind of thing; the server's answer says what comes next, and the made sets
are looked at before the operator sees them; the answers of step 1, the first three sets only, a set made from the film's own pictures; at
step 2 a "No" or "Correct it" waits for the rewritten request, three makes at most; the chat tool's recording flags, with the operator's
words for every paid one; an older round is told apart by its answer.
The older ways: the sentences replaced are retired by name (server/retired-sentences.json); the older round keeps its code, not its sentences.
A builder does not run it against the repository: the merger runs the three scripts once, after the merge (design/211 section 3.0, rule 6).
Exact anchors, each found once; run once: python scripts/d211b_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('picture-search',   # the row is a proposal with its reason; `prompt` only for what the plan does not say
     'Then the round, once any drawing set is approved: write out/reference-round.json, one row per element, every person included and none for an animal: element_id, its '
     'frame reference ids, and `prompt` (a thing: the subject block, what the picture must represent, its frame, nobody in it, never how the work is done; the server '
     'adds the kept preamble, the set line, the cosmetics from the plan and the four notes; a person: the why line); send it (`vw visuals round --file '
     'out/reference-round.json`) and run `vw visuals page`: the operator answers step 1 there.',
     'Then the round, once every thing is searched and any drawing set is approved: write out/reference-round.json, one row per element, every person a picture is made '
     'of included and none for an animal: element_id; `rec`, your proposal (`footage`: use its footage picture; `clean`: a clean set made from it; `set`: have a set '
     'made; `no_set`: its words carry it; `leave`: leave it out); `reason`, one line the operator reads; `first` on up to three rows of different kinds, the sets made '
     'first; and `prompt` only for what the plan does not say. The server writes each request itself, by kind of thing, from the plan (description, requirements, sizes, '
     "views, the place of the thing's first shot), with the film's own approved footage pictures and drawings as its inputs. Send it (`vw visuals round --file "
     'out/reference-round.json`): the server names every faulty row at once; then do what its answer says.'),
    ('picture-search',   # the views of a set, by kind
     "The server writes a person's sheet from the plan (description, outfits, place, your why line, one line against every other person), and from the person's photo "
     'when the permission is recorded, as three separate pictures: full length, working pose, the face;',
     "The server writes a person's sheet from the plan (description, outfits, the place of their first shot, your added words, one line against every other person), and "
     "from the person's photo when the permission is recorded, as three separate pictures: full length from the front, the plan's first view (else full length from the "
     "side), the face. A thing's three pictures are the views the plan names (`required_views`), filled to three by its kind and never two alike: an object or a "
     'material whole, as the film uses it, and its telling detail (no person; a hand only in use); a place whole, from the other side, and its fixed things; a way of '
     'working at its key moment, its result, and the tool meeting the material (hands and forearms, no face);'),
    ('picture-search',   # the states of the round: follow `then`; the looks before the operator
     '`vw visuals status --wait 900` between the two steps and after a set is made again: it ends when the sets are back; then `vw visuals page`.',
     "Every answer of the round says what comes next (`then`): do that and add nothing of your own. `vw visuals status --wait 900` while sets are made. When they are "
     'back, look at them before the operator does: `vw visuals round --looks` lists them and fetches their pictures (work/visuals/sets/); with more than five sets start '
     '`vw-set-look` helpers, about five sets each; each look is recorded with `vw visuals round --looks <file>`. The server shows the operator no set before its look.'),
    ('picture-search',   # the answers of step 1; two goes; made from the footage picture
     'Step 1: each thing gets the footage picture or Ignore this; Done approves the frames and makes every set at once, silently, by the kept method: three separate '
     'pictures, one per turn of one conversation, from real photographs with Google Search and Image Search on (a thing with an approved footage picture and no approved '
     'drawings gets no AI set: that picture is its reference and its golden picture; with approved drawings its set is made from the footage picture and the drawings).',
     'Step 1: each thing gets one answer: use its footage picture as the reference (free; no AI set, and the first picture in view order is its golden picture), have a '
     'clean set made from it (paid), have a set made (paid), or leave it out; one footage picture can be marked not this one. Done approves the frames and orders the '
     "first three sets only; the others are ordered on the operator's word, once they have judged the first. A set is three separate pictures, one per turn of one "
     "conversation, made from the film's own approved footage pictures and drawings where it has them (the film's picture wins over the web), else from real photographs "
     'with Google Search and Image Search on.'),
    ('picture-search',   # the looks first; the rewrite; three makes
     "Step 2, when every set is back: the operator judges them all in one shot: Yes (ticking the golden picture of a thing, the one every shot starts from; a person's "
     'is the full-length front), No, or Correct it with their words; Done records all; the No and Correct it sets are made again with the words in the prompt, never '
     'from a rejected picture, and come back for another step 2.',
     "Step 2, when the sets are back and looked at: the operator judges each: Yes (ticking the golden picture of a thing, the one every shot starts from; a person's is "
     'the full-length front), No, or Correct it with their words; one click orders the other sets. After No or Correct it nothing is made until you rewrite that request '
     'from their words, the check and your look: out/round-rewrites.json, rows {element_id, prompt}, sent with `vw visuals round --rewrite out/round-rewrites.json`. The '
     'same words are refused, the earlier request is kept, a rejected picture is never an input, and a set is made three times at most.'),
    ('picture-search',   # the new verdict `clean`; `--rest`, `--make` with the operator's words
     '`vw visuals round --verdicts out/round-verdicts.json --quote` ({element: {verdict: approve|ignore}}) and `vw visuals round --sets out/round-sets.json --quote` '
     '({element: {verdict: yes|no|correct, words, golden}}) only record answers the operator has already given in their own words: never use them to answer for the '
     'operator.',
     '`vw visuals round --verdicts out/round-verdicts.json --quote` ({element: {verdict: approve|clean|ignore, words}}), `vw visuals round --sets out/round-sets.json '
     '--quote` ({element: {verdict: yes|no|correct, words, golden}}), `vw visuals round --rest --quote` (the other sets) and `vw visuals round --make E --quote` (one set '
     'that was not made) only record answers the operator has already given in their own words: never use them to answer for the operator, and nothing paid is ordered '
     'without their words.'),
    ('picture-search',   # only the first sets are ordered at Done; an older round
     "Done on step 1 is not undone (the sets are ordered and paid then): at step 2 a set is made again with the operator's words, and one that was not made can be left "
     'out.',
     "Done on step 1 is not undone (the first sets are ordered and paid then; the others only on the operator's word): at step 2 a set is made again from the request you "
     "rewrite with the operator's words, and one that was not made can be left out. A round whose answer has no `v` is an older round: follow the tool's answers."),
]
COMMANDS = [   # (the old sentence, the new one) in plugin/commands/vw.md
    ("`vw visuals round --file out/reference-round.json` (rows `{element_id, frames, prompt}`: a thing's subject block, what the picture must represent and never how; a "
     "person's why line; the server adds the kept preamble, the set line, the cosmetics from the plan and the four notes, and writes a person's sheet from the plan as "
     'three separate pictures)',
     '`vw visuals round --file out/reference-round.json` (rows `{element_id, rec, reason, first, prompt}`: `rec` is your proposal, footage, clean, set, no_set or leave, '
     'with its reason in one line; `first` on up to three rows; `prompt` only for what the plan does not say; the server writes each request itself, by kind of thing, '
     "from the plan's words and views and the film's own pictures, as three separate pictures)"),
    ('`vw visuals page` for step 1, then `status --wait 900` between the two steps and after a set is made again (it ends when the sets are back; then `vw visuals '
     'page`): step 1 the operator approves the footage pictures and Done makes every set silently (three separate pictures, one per turn of one conversation, from real '
     'photographs, Google Search and Image Search on; a thing with an approved footage picture gets no AI set: that picture is its reference and golden picture, unless '
     'it has approved drawings, when its set is made from the footage picture and the drawings)',
     'then do what each answer says (`then`): `vw visuals page` for step 1; `status --wait 900` while sets are made; `vw visuals round --looks` to look at the sets '
     'before the operator does (`vw-set-look` helpers for more than five; `round --looks <file>` records the looks): step 1 each thing gets its footage picture as the '
     "reference (free), a clean set made from it, a set, or is left out, and Done orders the first three sets only, the others on the operator's word (three separate "
     "pictures, one per turn of one conversation, from the film's own approved footage pictures and drawings where it has them, else from real photographs, Google "
     'Search and Image Search on)'),
    ('step 2 they judge every set in one shot, Yes with the golden tick on a thing without a footage picture (the one every shot starts from; a person\'s golden is the '
     'full-length front, and the face close-up follows it into shots), No, or Correct it (made again with their words, never from a rejected picture)',
     'step 2 they judge each set, Yes with the golden tick on a thing (the one every shot starts from; a person\'s golden is the full-length front, and the face close-up '
     'follows it into shots), No, or Correct it (nothing is made until you rewrite that request from their words, `vw visuals round --rewrite out/round-rewrites.json`; '
     'never from a rejected picture; three makes at most), and one click orders the other sets'),
    ('`vw visuals round --verdicts` ({element: {verdict: approve|ignore}}) and `round --sets`',
     '`vw visuals round --verdicts` ({element: {verdict: approve|clean|ignore, words}}), `round --rest --quote "<their words>"` (the other sets) and `round --sets`'),
    ('a set that was not made is made with `vw visuals round --make <element>` (paid: inform; refused in plain words while its cause stands)',
     'a set that was not made is made with `vw visuals round --make <element> --quote "<their words>"` (paid: only on the operator\'s words; refused in plain words while '
     "its cause stands); a round whose answer has no `v` is an older round: follow the tool's answers"),
]
RETIRED = ['its frame reference ids, and `prompt` (a thing: the subject block',   # the sentences replaced, for server/retired-sentences.json
           'full length, working pose, the face',
           'between the two steps and after a set is made again',
           'Done approves the frames and makes every set at once',
           'the No and Correct it sets are made again with the words in the prompt',
           '({element: {verdict: approve|ignore}}) and',
           'Done on step 1 is not undone (the sets are ordered and paid then)',
           'rows `{element_id, frames, prompt}`',
           'Done makes every set silently',
           'step 2 they judge every set in one shot']


def apply(prompt, parts):
    """The visuals text with this part's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    raw = R.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    R.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    raw = CMD.read_bytes()
    text = raw.decode('utf-8')
    for old, new in COMMANDS:
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: plugin/commands/vw.md: not found once: %s' % old)
            text = text.replace(old, new)
    CMD.write_bytes(text.encode('utf-8'))   # bytes: the file keeps its line ends
    print('visuals: design/211 part B')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
