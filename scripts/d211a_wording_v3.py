"""design/211, part A (finding the footage pictures): instruction version 3, the visuals stage.

The footage is no longer matched to the things by words and a frame is no longer grabbed unseen: the assistant, or `vw-reference-finder`
helpers, read the digest of the clip analyses (`vw visuals digest`), take small trial frames (`vw visuals trial`), look at each and record
what was seen (`vw visuals look`); a frame becomes a footage picture only through its look, and the rule for a good frame is the server's.
The older ways: the word match (`vw visuals elements`) is kept as the way back for a run with no digest; "grab a frame of each" and the
assistant's own frame rule are retired by name (server/retired-sentences.json). Part A's anchors of design/211 section 3.12 and no other
part's. Registered in scripts/c1_split_v3.py. A builder does not run it against the repository: the merger runs the three scripts once,
after the merge (design/211 section 3.0, rule 6). Exact anchors, each found once; run once: python scripts/d211a_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('picture-search',   # the digest, the helpers, trial frames and looks; the word match only as the way back
     '`vw visuals elements` shows where each is seen in the footage (work/visuals/elements.json); grab a frame of each the footage has (`vw visuals frame --file`, '
     'free).',
     'Find each thing in the footage first, free: `vw visuals digest` writes what every clip shows, part by part with seconds (work/visuals/digest/index.json, then '
     'the clips files it names), and the things with the frame rule and the limits (work/visuals/refs/things.json); then do what its answer says. With more than '
     'five things start `vw-reference-finder` helpers, about five things each, up to six at a time, each given a group name and its thing ids; with five or fewer do '
     'the same yourself. For each thing: name the likely moments from the digest, take small trial frames (`vw visuals trial --file`, rows {element, clip, at}), read '
     'every frame, and record what was seen (`vw visuals look --file`: {by, things: [{element, clips, note, looks: [{trial, view, verdict, seen, keep, closest}]}]}; '
     "verdict pass, weak or fail): `keep` on the best frame of each of the thing's views, `closest` on the nearest frame where none can be kept, `not_searched` with "
     'the reason where no search was possible. A trial frame is not a reference. The server decides each thing\'s result, refuses a look on a frame that was not '
     'fetched, and names the things still to search. On a run with no digest its answer says so: `vw visuals elements` then names the likely clips by words '
     '(work/visuals/elements.json), every frame still needs its look, and the operator is told the footage was searched by words only.'),
    ('picture-search',   # the rule is the server's; a frame is kept through its look
     'A clip frame is free and exact, source and time kept (`vw visuals frame --element E --clip <id> --at <seconds>`); search the clip analyses first, footage left '
     "out of the edit included (not the operator's explicit exclusions), and take the sharpest frame, the subject large and evenly lit, never a blurred one for "
     'identity.',
     'The rule for a good frame is the server\'s and travels in things.json: judge every frame by it and by no rule of your own. A frame becomes a footage picture '
     'only through its look: the server cuts a kept frame at full size, source and time kept, and refuses, when the round is sent, a footage picture with no '
     "recorded look and a thing with no search record. Footage left out of the edit is searched too (not the operator's explicit exclusions)."),
]
RETIRED = ['grab a frame of each the footage has',   # the sentences replaced, for server/retired-sentences.json
           'take the sharpest frame, the subject large and evenly lit',
           'a frame for every element the footage has']
COMMANDS = [   # (the old sentence, the new one) in plugin/commands/vw.md
    ('`vw visuals elements`, a frame for every element the footage has (`vw visuals frame --file out/frames.json`, rows `{element, clip, at, name, subject}`, one '
     'call), then ',
     '`vw visuals digest` (what every clip shows, work/visuals/digest/; the things, the frame rule and the limits, work/visuals/refs/things.json), then each thing '
     'is found in the footage, by `vw-reference-finder` helpers of about five things each, or by you with five things or fewer: trial frames (`vw visuals trial '
     '--file`, rows `{element, clip, at}`, free), each frame read, and what was seen recorded with the frames to keep (`vw visuals look --file`); on a run with no '
     'digest `vw visuals elements` names the likely clips by words; then '),
    ('(`vw-scene-review`, `vw-plan-gaps`, on a `--drawn motion` film',   # The web: both new helpers named
     '(`vw-scene-review`, `vw-plan-gaps`, for the references `vw-reference-finder` and `vw-set-look`, on a `--drawn motion` film'),
]


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
    print('visuals: design/211 part A')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
