"""design/223 (SK, 22 Nov 2026): the new take process, in the served text.

In v3.json, part `later`, each replaced (the replaced words are in server/retired-sentences.json):
- the first take is made once, small (360p), and no second Shoot card is shown ("Make another" and `vw guide cause` are retired);
- nobody checks a finished take: not Claude, not a helper, not the server (Claude's check from frames, the `vw-take-look` helpers, the 30 minutes
  and the server's measured lines are retired); the still's check before its card is unchanged;
- the operator accepts a take or says what is wrong in plain words (Select / Make another / Reject are retired); step 6's one click is unchanged;
- after done: the one line of what was ordered, the full-size video of an accepted small take, and the correction's route, chosen by the assistant
  from the server's one rule (`vw guide corrections`, `vw guide correct`); no limit on rounds.
Registered in scripts/c1_split_v3.py after layoutb2. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/d223_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

SHOOT = ('That card is for the first take of a shot. A second take is ordered by the operator on the page ("Make another", with their words): '
         'it is their word, so no card is shown again: say what caused the fault (`vw guide cause`), change that one thing, then `vw guide shoot --shot S`.')
SHOOT_NEW = ('That card is for the first take of a shot, which is made once, small (360p). No second Shoot card is shown: a take the operator says is wrong is '
             'corrected (the takes, below); only a first take that could not be made at the provider is offered once more, on their word.')
CAUSE = ('A rejected take needs its cause before another (`vw guide cause`): the first frame against the still, then the guide, only then the words; '
         'the same request is never sent twice, and after two rejected takes from one camera the shot is cut, re-angled or left out.')
CAUSE_NEW = ('Never make a take again on your own, and never send the same request twice; there is no limit on the rounds of correction: the '
             "operator decides when to stop, and the film's cost limit is the only other stop.")
CHECK = ('Claude checks every ready take before the operator sees it, from frames the server takes from it (you cannot play a video): '
         '`vw visuals pictures --looks` lists the takes waiting (kind `take`) with the sheet at four frames a second, one frame every half second with its '
         'second, the approved still and five lines (people, the action, objects, bodies and contact, the place and the light); `vw-take-look` helpers judge '
         'them, about three takes each, and send the file; with a fail say what you saw and its second. A take whose check does not come within 30 minutes is '
         'shown as not checked. The still an AI video shot starts from is checked the same way before its card: it is listed with the pictures (kind `start`).')
CHECK_NEW = ('Nobody checks a finished take: not you, not a helper, not the server; it is shown as it was made. The still an AI video shot starts from '
             'is checked by Claude before its card, as before: `vw visuals pictures --looks` lists it with the pictures (kind `start`).')
START = ('Start the checkers of the stills and of the takes together, in one message: `vw visuals next` names what can start now. The server measures the '
         'rest: real footage, the length, the first frame, one continuous shot.')
START_NEW = 'Start the checkers of the stills together, in one message: `vw visuals next` names what can start now.'
COUNT = '("AI video: 11 made and checked, 4 being made.")'
COUNT_NEW = '("AI video: 11 made, 4 being made.")'
ANSWER = ("When every take is made and checked the operator answers them on the page (`vw visuals page`), in one visit: Select, Make another, or Reject; "
          "on the pages of steps 6 and 7 the check's warning is in view and Yes or Select is one click whatever it says, recorded as approved against the "
          'check (no second question, no typed reason); rejecting needs their words; until then')
ANSWER_NEW = ('When every take is made the operator answers them on the page (`vw visuals page`), in one visit: they accept a take, or say what is wrong '
              'with it in plain words. Never ask them for seconds, a cause or a way to correct. '
              "On the page of step 6 the check's warning is in view and Yes is one click whatever it says, recorded as approved against the "
              'check (no second question, no typed reason); rejecting needs their words. Until the takes are all made')
DONE = ('After they say done, `vw visuals page --record` gives one line with the number of new takes ordered, their length and the amount: say it as it '
        'is and ask nothing with it; then, for each, the cause, the one change and the take. A take rejected with no new one ordered: ask the operator in '
        'the chat what happens to the shot (cut it, another angle, or leave it out).')
DONE_NEW = ('After they say done, `vw visuals page --record` gives one line with what their answers ordered, its length and the amount: say it as it is '
            'and ask nothing with it. An accepted small take gets its full-size video by itself; they see the two side by side before it goes in the '
            'film. For each correction you choose the route (the `vw:guide` skill, "When a take is wrong"): `vw guide corrections` gives their words, the '
            'frames, the pictures and `rule`, the one place the choice is written; then `vw guide correct --shot S --file …`. You give no verdict on a '
            "take. A video that could not be made is shown with the provider's answer: they may send it once more, never you.")
PAIRS = [('later', SHOOT, SHOOT_NEW), ('later', CAUSE, CAUSE_NEW), ('later', CHECK, CHECK_NEW), ('later', START, START_NEW), ('later', COUNT, COUNT_NEW),
         ('later', ANSWER, ANSWER_NEW), ('later', DONE, DONE_NEW)]   # (the part, the sentence as it is, the sentence as it becomes)

RETIRED = ['A second take is ordered by the operator on the page ("Make another"',   # the operator says what is wrong; the assistant chooses the route
           'A rejected take needs its cause before another',                        # `vw guide cause` and the ladder
           'Claude checks every ready take before the operator sees it',            # nobody checks a take
           'The server measures the rest: real footage',                            # nothing is measured on a take
           'When every take is made and checked the operator answers them',         # the page opens when every take is made
           'then, for each, the cause, the one change and the take']                # a correction's route


def apply(prompt, parts):
    """The visuals text with these sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == where)
        if new in part['text']:
            continue
        if part['text'].count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        part['text'] = part['text'].replace(old, new)
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
        part = next(p for p in st['parts'] if p['name'] == where)
        part['text'] = part['text'].replace(new, old)
    return st


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    rp = ROOT / 'server' / 'retired-sentences.json'
    r = json.loads(rp.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('visuals: design/223')


if __name__ == '__main__':
    main()
