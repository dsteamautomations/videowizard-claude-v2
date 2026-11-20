"""Fix set, 20 Nov 2026 (SK): the page is never empty, and its link is given only when it is filled; in the served text and the command text.

In v3.json, the common part: after the sentence on `say` and `preparing`, the link is given only when `vw visuals page --shown` prints it
(after the round is on the page); a page of an older tool is published again as soon as the tool says so (`republish_now`); a publish that
fails or goes to another link is never a new page. Nothing is replaced there: the sentences are added. In plugin/commands/vw.md the same two
points, in the sentences that say how the page is used; the two replaced sentences are in server/retired-sentences.json. Registered in
scripts/c1_split_v3.py after the script of the critic's points. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/fixset5_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

SAY = 'when `vw visuals page` first gives `preparing`, say that sentence as it is, then run `vw visuals page --fetch`.'   # design/216
SAY_NEW = (SAY + ' Give the operator the link only when `vw visuals page --shown` prints it, after the round is on the page; until then say one progress line. '
           'When the tool says `republish_now`, publish the page again at once, to the same link. A publish that fails, or that goes to another link, is never '
           'a new page: say so and ask the step in the chat (`vw visuals next`).')

LINK = 'typing none of it; give the operator the link; when they say done'   # design/204
LINK_NEW = ('typing none of it; give the operator the link only when `vw visuals page --shown` prints it, after the round is read back from the page; when they '
            'say done')
AGAIN = 'If it says `republish`, publish the page again to the same link first, as it says.'   # design/206
AGAIN_NEW = ('If it says `republish`, publish the page again to the same link first, as it says; do it as soon as the tool says so (`republish_now`, at '
             '`vw visuals next` or the status), while things are still being made. A publish that fails or names another link is never a new page: say so and '
             'ask the step in the chat.')

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('commands/vw.md', LINK, LINK_NEW),
    ('commands/vw.md', AGAIN, AGAIN_NEW),
]

RETIRED = ['typing none of it; give the operator the link; when they say done',                       # the link only from `vw visuals page --shown`
           'publish the page again to the same link first, as it says.']                                # as soon as the tool says so; never a new page


def apply(prompt, parts):
    """The visuals text with this set's sentences: the common part is returned (the parts are not changed). Applying twice changes nothing."""
    if SAY_NEW in prompt:
        return prompt
    if prompt.count(SAY) != 1:
        sys.exit('not applied: the common part: not found once: %s' % SAY[:60])
    return prompt.replace(SAY, SAY_NEW)


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    st['prompt'] = st['prompt'].replace(SAY_NEW, SAY)
    return st


def now(file, text):
    """An earlier script's sentence for one plugin file as it reads after this script (for that script's test)."""
    for f, old, new in HELPERS:
        if f == file and new not in text:
            text = text.replace(old, new)
    return text


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    for file, old, new in HELPERS:
        path = ROOT / 'plugin' / file
        raw = path.read_bytes()   # bytes in and out, so the file keeps its line ends
        end = '\r\n' if b'\r\n' in raw else '\n'
        text = raw.decode('utf-8').replace('\r\n', '\n')
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: plugin/%s: not found once: %s' % (file, old[:60]))
            path.write_bytes(text.replace(old, new).replace('\n', end).encode('utf-8'))
    rp = ROOT / 'server' / 'retired-sentences.json'
    r = json.loads(rp.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('visuals and the command text: the page is never empty, the link only when it is filled')


if __name__ == '__main__':
    main()
