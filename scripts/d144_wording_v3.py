"""design/144 V2 (operator, VW-16, 2 Nov 2026): volume-lowering tags made a deep voice husky; the direction instruction stops offering them in the best
fit and warns about them. One exact replacement; the old wording goes on RETIRED (server/retired-sentences.json). Run once: python scripts/d144_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
OLD = ('Register: [measured], [warm], [confident], [thoughtful], [earnest],\n[reassuring], [matter-of-fact], [quietly proud], [emphatic], [softly], and free descriptions in the\n'
       'same spirit ("[lower, thoughtful]", "[gradually building energy]", "[lighter, inviting]").')
NEW = ('Register: [measured], [warm], [confident], [thoughtful], [earnest],\n[reassuring], [matter-of-fact], [emphatic], and free descriptions in the same spirit\n'
       '("[gradually building energy]", "[lighter, inviting]"). Tags that lower the volume (softly, quietly,\nlower, whispered) can make a deep or low voice breathy or husky: '
       'on a deep voice use attitude and\npace instead (confident, warm, thoughtful, unhurried); a volume-lowering tag goes only in the\nexperimental list, with that note to the operator.')
RETIRED = ['[quietly proud], [emphatic], [softly], and free descriptions']


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'voice')
    if st['direction_prompt'].count(OLD) != 1:
        sys.exit('not applied: the vocabulary line was not found once')
    st['direction_prompt'] = st['direction_prompt'].replace(OLD, NEW)
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    r = json.loads(R.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    R.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('applied')


if __name__ == '__main__':
    main()
