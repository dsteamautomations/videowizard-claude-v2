"""design/194 (Deepa, 13 Nov 2026, voice rows 10, 16, 17; SK's yes to build, 14 Nov): instruction version 3, the voice stage: a word that sounds wrong
is corrected after listening, on the voices page or with `vw voice pronounce --word`; the tag control is named for what it does. Each anchor is found
once; run once: python scripts/d194_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
MARK = 'A word sounds wrong'

PAIRS = [
    ('listen, tweak a sentence for one voice, make one narration final with their words, download.',
     "listen, change a sentence's tone or pace for one voice (A sentence's tone or pace), correct a word that sounds wrong (A word sounds wrong: pick the word in the script, "
     'type how it should sound, hear it in that voice, make it final, narrate again with the final words), make one narration final with their words, download.'),
    ('Fetch, let them listen, and when they say which narration is the final one,',
     'Fetch, let them listen. A word that sounds wrong is corrected then, never asked about before the narration: '
     '`vw voice pronounce --word W --say "<how it sounds>" --hear --voice ID` (a small paid try), their listening, another `--say` as often as needed, '
     '`vw voice pronounce --word W --final`, and narrate again. When they say which narration is the final one,'),
]


def apply(d):
    st = next(s for s in d['stages'] if s['name'] == 'voice')
    if any(MARK in s for s in st['steps']):
        return False
    for old, new in PAIRS:
        hits = [i for i, s in enumerate(st['steps']) if old in s]
        if len(hits) != 1 or st['steps'][hits[0]].count(old) != 1:
            sys.exit(f'not applied: voice steps: found in {len(hits)} steps: {old[:60]}')
        st['steps'][hits[0]] = st['steps'][hits[0]].replace(old, new)
    return True


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    if not apply(d):
        print('already applied')
        return
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('voice instructions: design/194 applied')


if __name__ == '__main__':
    main()
