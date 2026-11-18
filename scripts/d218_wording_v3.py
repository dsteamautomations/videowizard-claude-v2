"""design/218 (18 Nov 2026): instruction version 3, the visuals stage, plugin/commands/vw.md and two motion texts: the font question shows its sample picture
first (`vw font --sample`), and step 6 ("Pictures and drawn graphics") is answered on the page: a chat card only for a question the server
says is asked in the chat (the film's font is one) or where the page cannot be shown (owed from the hotfix of 18 Nov). A graphic sequence is
reviewed at step 6 on the page, no longer in the chat. The older sentence is listed in server/retired-sentences.json. Registered in
scripts/c1_split_v3.py after design/217's script. Run once: python scripts/d218_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

FONT = ("Before the first drawn graphic the server asks the film's font in the chat: run `vw font --sample` and show its picture (each offered font "
        "drawn on the film's labels and colours; \"Other\" is not in it), then ask the question with the fonts `vw font` lists and Other, as before; "
        "when it says \"The font sample is not available.\", say that line and ask as before. ")
COLOUR = ('A colour the palette names none for is never asked: you choose a neutral (a grey, an off-white or a near-black) that keeps the thing apart '
          'from what touches it, or take the one a helper lists under "Colours to add" or "Colours added", and record it once for the whole film: '
          '`vw motion colour --shot D1,D2 --thing … --colour #RRGGBB --words … --reason …` (every later brief carries it; the operator sees it under '
          'Details on the drawing). Only a real hue, or a colour a brand colour rule of the film could break, is asked (then `--quote`).')
PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('common', 'Every other decision of this stage is asked here in the chat, one at a time (`vw visuals next`, `vw visuals decide`).',
     'Step 6, the pictures and drawn graphics, is answered on the page too: post a card in the chat only for a question the server says is asked '
     "in the chat (the film's font is one) or where the page cannot be shown. "
     'Every other decision of this stage is asked here in the chat, one at a time (`vw visuals next`, `vw visuals decide`).'),
    ('later', 'A graphic sequence is reviewed as its states, in the chat:',
     'A graphic sequence is reviewed as its states, on the page at step 6 (in the chat only where the page cannot be shown, and on an older film):'),
    ('later', "Once a drawn shot's pictures and spec are approved: `vw motion brief --shot S` for each;",
     FONT + "Once a drawn shot's pictures and spec are approved: `vw motion brief --shot S` for each;"),
    ('later', 'when the brief leaves a fact open, show the operator rules.md and ask them to tick, strike or add, once.',
     'when the brief leaves a fact open, show the operator rules.md and ask them to tick, strike or add, once. ' + COLOUR),
]
COMMANDS = [   # (the old sentence, the new one) in plugin/commands/vw.md
    ('(`vw visuals page`); the AI video and the recording are asked in the chat, one at a time:',
     "(`vw visuals page`), and in the chat only a question the server says is asked there (the film's font: show the picture of `vw font --sample` first, "
     'then ask as before) or where the page cannot be shown; the AI video and the recording are asked in the chat, one at a time:'),
]
HELPERS = [   # (file under plugin/, the old sentence, the new one): design/218 A, a missing neutral colour is Claude's
    ('agents/vw-motion-rules.md', 'list it at the end under "Questions for the operator", one line each, with why.',
     'list it at the end under "Questions for the operator", one line each, with why. A colour the palette names none for is not such a question: '
     'write the rule with a neutral (a grey, an off-white or a near-black) that keeps the thing apart from what touches it, and list it under '
     '"Colours to add" (the thing, #RRGGBB, its words, one reason); only a real hue, or a colour a brand rule in the brief could forbid, is a question.'),
    ('skills/motion/SKILL.md', '- Silent: no audio, no music.',
     "- Colours are the brief's palette, with the colours it lists as added for every drawing. A thing the palette gives no colour: choose a neutral "
     '(a grey, an off-white or a near-black) that keeps it apart from what touches it and name it in `REVIEW.md` under "Colours added" (the thing, '
     '#RRGGBB, its words, one reason); never stop to ask. A real hue is the operator\'s: name it in `REVIEW.md` as a question.\n- Silent: no audio, no music.'),
]
RETIRED = ['A graphic sequence is reviewed as its states, in the chat']


def apply(prompt, parts):
    """The visuals text with this design's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = None if where == 'common' else next(p for p in parts if p['name'] == where)
        text = prompt if part is None else part['text']
        if new in text:
            continue
        if old not in text:
            sys.exit('not applied: %s: not found: %s' % (where, old[:60]))
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
    raw = R.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    R.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    _swap(CMD, COMMANDS, 'plugin/commands/vw.md')
    for name in sorted({h[0] for h in HELPERS}):
        _swap(ROOT / 'plugin' / name, [(old, new) for file, old, new in HELPERS if file == name], 'plugin/' + name)
    print('visuals: design/218')


if __name__ == '__main__':
    main()
