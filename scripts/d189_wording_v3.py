"""design/189 (SK, 12 Nov 2026, from VW-22): instruction version 3, the options stage: the shape of the answers file is said where the operator
first answers the review shots (it was only in the master stage's text, read later), and the common rule on offering a choice is added to
plugin/commands/vw.md by hand. One exact replacement; run once: python scripts/d189_wording_v3.py"""
import json
import sys
from pathlib import Path

P = Path(__file__).resolve().parents[1] / 'server' / 'procedures' / 'v3.json'
OLD = "In chat instead, they watch out/review.mp4 and answer each shot with you (`vw master decide`): the first answer approves the options."
NEW = ("In chat instead, they watch out/review.mp4 and answer each shot with you: one answer is `vw master decide --slide 2.1 --action KEEP` "
       "(`--action KEEP|REJECT|TRIM`, `--note \"<their words>\"`, and for a TRIM `--edit \"in:+12,out:-6\"`); several are a file, out/decisions.json, a list with one object per answer, "
       "`[{\"slide\": \"2.1\", \"action\": \"KEEP\", \"note\": \"\", \"edit\": \"\"}]`, sent with `vw master decide --file out/decisions.json`. `vw master slides` says which shots still wait. "
       "Never guess a file's shape: when a command's input is not written here, run the command with no input and read its refusal first. The first answer approves the options.")

d = json.loads(P.read_text(encoding='utf-8'))
st = next(s for s in d['stages'] if s['name'] == 'options')
hits = [i for i, s in enumerate(st['steps']) if OLD in s]
if any(NEW in s for s in st['steps']):
    sys.exit('already applied')
if len(hits) != 1:
    sys.exit('not applied: the sentence is not found once')
st['steps'][hits[0]] = st['steps'][hits[0]].replace(OLD, NEW)
P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('options stage: the answers file is described where the review starts')
