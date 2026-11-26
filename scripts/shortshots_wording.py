"""Short shots and list items (SK, 25 Nov 2026: VW-25 issues 3b and 2; requirements R3b and R2, "Approve as written").

In v3.json (the replaced words are in server/retired-sentences.json):
- options, rule 2: "2 to 3.5 s each is normal" becomes the short-shot rule: the field `short` and its six reasons, the cases never cut
  short, the lowest length of 1 s, a shot under 1.5 s only in a run of three or more;
- options, rule 1: each thing a sentence names has its own shot, a blank, or a note for the operator (the check's flag N18);
- options, the rules the server enforces: the hold, but for a shot marked `short`;
- options, the step that authors the cut: N18 among the flags to act on;
- options, the rules the server enforces: three shots in a row that are each cut short may be of one size (SK, 26 Nov 2026: "Yes, exempt");
- master, the build step: "a blank under 3 s" leaves the list of refusals (no code ever made that refusal).
In the plugin: two lines of `vw-scene-review` (the second look knows the field and the list rule). They ride on the next plugin release.
No sentence of an earlier wording script is changed, so no older pin chains through this one. The visuals stage is not touched: the
registration in scripts/c1_split_v3.py checks that v3.json holds these sentences.
Exact anchors, each found once; applying twice changes nothing. Run once: python scripts/shortshots_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

RULE2 = 'Several short real shots may run together; 2 to 3.5 s each is normal.'
RULE2_NEW = ("Several short real shots may run together. A shot may go under its piece's hold (min_comprehension_hold_s), down to 1 s, only when it carries `short`, "
             'its reason: list_item (one of several things the sentence names, cut on its word), thing (the words name an object or a material, not an action; steady '
             'and close), kinds (kinds of one thing side by side), repeated_action (one stroke or cycle of a repeating action; its action peak stays whole), recap (an '
             'opening, a closing or a summing-up of things shown at length elsewhere), b_roll (B-roll under words with no specific claim). Only repeated_action must '
             'keep the action peak. Never short: a step being shown (the sentence says how something is done and the shot is its exact match), a wide shot, something '
             'to read, a cut into a camera move, the first time the film shows a thing the words explain, a heavy crop, a pause in the narration. A shot under 1.5 s '
             "only inside a run of three or more short shots. The operator sees the reason on the shot and decides; an alternative takes its shot's `short`.")
RULE1 = 'A match may cover part of a sentence; leave the rest blank.'
RULE1_NEW = (RULE1 + ' When a sentence names several things, each thing named has its own shot (a short shot, rule 2), or a blank, or a note for the operator saying '
             'it is not shown; never one treatment for one item and nothing for the next. A picture of several things together is not a picture of each one. The check '
             'flags such a sentence with too few shots and blanks under it (N18).')
HOLD = 'respect min_comprehension_hold_s;'
HOLD_NEW = 'respect min_comprehension_hold_s (but for a shot marked `short`, rule 2);'
FLAGS = 'N17 (claims), N14; each says what to do'
FLAGS_NEW = 'N17 (claims), N14, N18 (lists); each says what to do'
SIZES = 'never three of the same size;'   # SK, 26 Nov 2026 ("Yes, exempt"): the things of a list are close-ups of one size
SIZES_NEW = 'never three of the same size (three in a row that are each cut short, rule 2, may be);'
BUILD = "(a scene sent back to find footage, a blank under 3 s, a trim that changes a scene's length, a clip used twice)"
BUILD_NEW = "(a scene sent back to find footage, a trim that changes a scene's length, a clip used twice)"
# (the stage, the sentence as it is, the sentence as it becomes); each is looked for in the stage's prompt and steps
PAIRS = [('options', RULE2, RULE2_NEW), ('options', RULE1, RULE1_NEW), ('options', HOLD, HOLD_NEW), ('options', FLAGS, FLAGS_NEW), ('options', SIZES, SIZES_NEW),
         ('master', BUILD, BUILD_NEW)]

LAST = 'say why in `carries_over_seen`.'
SHORT_LINE = ("- A shot that carries `short` (list_item, thing, kinds, repeated_action, recap, b_roll) may be shorter than its piece's hold, down to 1 s: keep the field on a "
              'shot you keep, and give it to a shot you cut under its hold only for one of those reasons, never on a wide shot or into a camera move; a shot under 1.5 s '
              'stands only in a run of three or more short shots.')
LIST_LINE = ('- When a sentence names several things, each thing named has its own shot, or a blank, or a note for the operator saying it is not shown.')
HELPERS = [('agents/vw-scene-review.md', LAST, LAST + '\n' + SHORT_LINE + '\n' + LIST_LINE)]   # (file under plugin/, the old text, the new one)

RETIRED = ['2 to 3.5 s each is normal', 'a blank under 3 s']


def texts(stage):
    """Every text of a stage with where it sits: ('prompt', None) or ('steps', i)."""
    return [(('prompt', None), stage.get('prompt') or '')] + [(('steps', i), t) for i, t in enumerate(stage.get('steps') or [])]


def apply(d):
    """The instruction document with these sentences, changed in place. Applying twice changes nothing."""
    for name, old, new in PAIRS:
        stage = next(s for s in d['stages'] if s['name'] == name)
        if any(new in t for _, t in texts(stage)):
            continue
        found = [(where, t) for where, t in texts(stage) if old in t]
        if len(found) != 1 or found[0][1].count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (name, old[:60]))
        (key, i), t = found[0]
        if i is None:
            stage[key] = t.replace(old, new)
        else:
            stage[key][i] = t.replace(old, new)
    return d


def check(d):
    """For scripts/c1_split_v3.py --check: v3.json holds every sentence of this script and none it replaced."""
    for name, old, new in PAIRS:
        text = '\n'.join(t for _, t in texts(next(s for s in d['stages'] if s['name'] == name)))
        assert new in text and (old in new or old not in text), 'v3.json does not hold the short-shot wording: %s: %s' % (name, new[:60])


def main():
    raw = P.read_bytes()
    d = apply(json.loads(raw.decode('utf-8')))
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
    raw = rp.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    print('options and master: short shots where they fit, each thing named in a list, no "blank under 3 s"; the second-look helper knows both')


if __name__ == '__main__':
    main()
