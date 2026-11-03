"""design/146 (SK, 3 Nov 2026): the media step asks the camera once, only for clips whose file carries no maker. One sentence added to the media
instruction. Run once: python scripts/d146_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
ANCHOR = 'a good copy keeps the original\'s name, length, frame rate and timecode.'
ADDED = (' When prepare prints a camera_unknown_note (clips whose file carries no camera maker, usually an export), ask the operator once which camera those clips '
         'were shot on and pass their words as `--shot-on "<their words>"`; never ask when the files say it.')


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'media')
    if ADDED.strip() in st['steps'][1]:
        sys.exit('already applied')
    if st['steps'][1].count(ANCHOR) != 1:
        sys.exit('not applied: the anchor sentence was not found once')
    st['steps'][1] = st['steps'][1].replace(ANCHOR, ANCHOR + ADDED)
    st['steps'][2] = st['steps'][2].replace('`vw stage media record --camera-audio allowed|excluded --copies originals|copies', '`vw stage media record --camera-audio allowed|excluded --copies originals|copies [--shot-on "<their words>"]')
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('applied')


if __name__ == '__main__':
    main()
