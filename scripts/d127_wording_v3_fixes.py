"""design/127: the independent check's fixes to the version 3 wording (scripts/d127_wording_v3.py): claims stay out of round 2, a rejected shot
takes its kept alternative, "first answer", what an alternative is checked for, alternatives asked after the reject, what a note's answer is,
a clip used twice among the build's refusals. Appends to design/127-wording-trace.md."""
import json
import re

P = 'server/procedures/v3.json'
TRACE = 'design/127-wording-trace.md'
FIXES = [   # (stage, 'prompt' or step index, old, new)
    ('options', 'prompt', 'have no exact match: round 2 or a blank;', 'have no exact match: a blank, or round 2 B-roll only where the words make no specific claim;'),
    ('options', 'prompt', 'B-roll needs no note. The operator answers every footage shot KEEP, REJECT or TRIM; a rejected shot becomes a blank.',
     'B-roll needs no note. The operator answers every footage shot KEEP, REJECT or TRIM, a noted one too (a kept reuse is approved); a rejected shot becomes its kept alternative, else a blank.'),
    ('options', 'prompt', 'the same timeline length as the shot, a clip used nowhere else in the cut. The operator sees it only after rejecting the shot.',
     'the same timeline length as the shot, a clip used nowhere else in the cut (not the shot\'s own), checked like a shot; never on a blank. The operator sees it only after rejecting the shot; keeping the shot or one alternative switches the others off.'),
    ('options', 'prompt', "the operator's first slide answer approves", "the operator's first answer approves"),
    ('master', 0, 'an alternative (2.1A1) KEEP or REJECT, asked only after its shot is rejected;', 'an alternative (2.1A1) KEEP or REJECT, asked in the message after its shot\'s REJECT;'),
    ('master', 1, '(a scene sent back to find footage, a blank under 3 s, a trim that changes a scene\'s length)', '(a scene sent back to find footage, a blank under 3 s, a trim that changes a scene\'s length, a clip used twice)'),
]


def words(t):
    return len(re.findall(r'\S+', t))


d = json.load(open(P, encoding='utf-8'))
stages = {s['name']: s for s in d['stages']}
out = ['', '## Fixes after the independent check', '']
for name, where, old, new in FIXES:
    st = stages[name]
    text = st['prompt'] if where == 'prompt' else st['steps'][where]
    assert text.count(old) == 1, old
    text = text.replace(old, new)
    if where == 'prompt':
        st['prompt'] = text
    else:
        st['steps'][where] = text
    out += [f'- {name} {where if where == "prompt" else "step " + str(where + 1)}: "{old}" ({words(old)} words) → "{new}" ({words(new)} words)']
open(P, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
open(TRACE, 'a', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('ok')
