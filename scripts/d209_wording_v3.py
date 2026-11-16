"""design/209 (SK, 16 Nov 2026): instruction version 3, the visuals stage. After the plan is accepted the operator approves the drawings
(their parts and sizes) and the materials (their facts) on the page, in one visit, each size asked once; the chat, one at a time, only where
the page cannot be shown. Exact anchors, each found once; run once: python scripts/d209_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [   # (where: common or a part's name, the old sentence, the new one)
    ('common', 'The operator answers the treatment and the plan on the page (`vw visuals page`). Every other decision of this stage is asked here in the chat, one at a time '
               '(`vw visuals next`, `vw visuals decide`).',
     'The operator answers the treatment and the plan, then the drawings and the materials, on the page (`vw visuals page`): once the plan is accepted the page lists each '
     "drawing's parts and sizes and each material's facts in plain words, each size asked once; one visit, then `vw visuals page --record`. Where the page cannot be shown they are "
     'asked in the chat. Every other decision of this stage is asked here in the chat, one at a time (`vw visuals next`, `vw visuals decide`).'),
    ('plan', "they approve the run's specs in one table (`vw visuals spec` with no --shot) or send a correction (`vw visuals spec --shot S --notes \"…\"`, in `spec_corrections`): "
             'fold into out/visual-plan.json (`vw visuals plan`), propose again (approval refused until then); one late spec: `vw visuals spec --shot S --quote "…"`.',
     'after the plan is accepted they approve the drawings and the materials on the page (`vw visuals page`, one visit, then `vw visuals page --record`); in the chat, one at a '
     'time (`vw visuals next`), only where the page cannot be shown. A correction they send is in `spec_corrections`: fold into out/visual-plan.json (`vw visuals plan`), propose '
     'again (approval refused until then), then `vw visuals page` again; a correction said in the chat: `vw visuals spec --shot S --notes "…"`.'),
    ('later', 'it is shown on the References step beside the sheet and approved once (`vw visuals spec --element E`; a correction: `vw visuals spec --element E --notes`);',
     'it is approved once, on the page with the drawings (`vw visuals page`, after the plan is accepted; in the chat only where the page cannot be shown; a correction said in the '
     'chat: `vw visuals spec --element E --notes`);'),
    ('plan', 'fix what it names in the gap file (its helper for a judgement, you for a field or a spelling), join again, check again; out/visual-plan.json is never edited by '
             'hand (the join refuses to overwrite one that was; `--rebuild` drops the edits).',
     'fix what it names in the gap file (its helper for a judgement, you for a field or a spelling) or, for a shared part, in out/plan-base.json; join again, check again, '
     "before a proposal and after one: after a proposal the join carries your changes onto the server's plan and keeps what was corrected there. A hand edit of "
     'out/visual-plan.json is never overwritten: the join says what to do (`--rebuild` drops the hand edits).'),
]
STEP = (2, 'the operator answers every gap on the page, recorded on their done (`vw visuals page --record`), the card where it cannot be shown;',
        'the operator answers every gap on the page, then the drawings and the materials, recorded on their done (`vw visuals page --record`), the card where it cannot be shown;')


def apply_steps(steps):
    i, old, new = STEP
    if new not in steps[i]:
        if steps[i].count(old) != 1:
            sys.exit('not applied: step %d: not found once: %s' % (i, old[:60]))
        steps[i] = steps[i].replace(old, new)
    return steps


def apply(prompt, parts):
    """The visuals text with design/209's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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
    apply_steps(st['steps'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals: design/209, the drawings and the materials approved on the page')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
