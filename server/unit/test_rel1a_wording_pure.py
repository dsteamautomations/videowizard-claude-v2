"""Release 1, section A (SK, 20 Nov 2026): the served text and the helper texts say the third answer with its guard (A3, A4) and step 7's
still under Claude's check (A1); the wording script is registered, its replaced sentence is retired, and the older ways are in the decision log."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def test_the_served_text_and_the_helpers_say_it_and_the_replaced_sentence_is_retired():
    import rel1a_wording as W
    import d223_wording   # design/223 retired this script's take sentence (the 30 minutes): the text is read as it was before it
    stage = d223_wording.before(next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals'))
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    HELPERS = [h for h in W.HELPERS if h[0] != 'agents/vw-take-look.md']   # design/223: that helper is retired and its file removed
    later = next(p for p in stage['parts'] if p['name'] == 'later')['text']
    was = next(p for p in W.before(stage)['parts'] if p['name'] == 'later')['text']
    for where, old, new in W.PAIRS:
        assert later.count(new) == 1 and new not in was and was.count(old) == 1, old[:50]
    for said in ('is answered "na" with `why`: it is recorded once as a note', 'is checked the same way before its card', 'may also be answered "na", it does not apply here, with one sentence why'):
        assert said in later, said
    for file in sorted({f for f, _, _ in HELPERS}):
        md = (ROOT / 'plugin' / file).read_text(encoding='utf-8').replace('\r\n', '\n')
        md = md.replace(*reversed(__import__('rel27nov_wording').SKILL_4))   # release 1 of 27 Nov, phase 4 part A: the skill no longer shows the operator the overlay; read as before it
        for f, old, new in HELPERS:
            if f == file:
                assert md.count(new) == 1 and (new.startswith(old) or old not in md), (file, old[:50])
    for file in ('agents/vw-picture-look.md', 'agents/vw-set-look.md'):   # design/223: the vw-take-look helper is retired   # A4: the guard, with its two examples, where the helper answers its lines
        md = (ROOT / 'plugin' / file).read_text(encoding='utf-8')
        assert '`"pass": "na"`' in md and 'only when' in md and 'cannot show the thing the line asks about' in md and 'Never for something that is in view' in md, file
        assert 'where no hand is in the frame; a line about the whole room, on a close view of one object' in md, file
    rule = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert '"pass": "na"' in rule and 'never for a rule that passed or failed in an earlier round' in rule and 'no frame is taken and no round is counted for it' in rule
    everything = stage['prompt'] + ''.join(p['text'] for p in stage['parts']) + ''.join((ROOT / 'plugin' / f).read_text(encoding='utf-8') for f in {f for f, _, _ in HELPERS})
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired and s not in everything for s in W.RETIRED)
    for word in ('brick', 'ceiling', 'kiln', 'tumbler'):   # generic words: every category of video
        assert word not in (W.GUARD + W.RULE_NEW + W.SEEN_NEW + W.TAKE_NEW).lower()
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('fixset5(prompt, parts)') < split.index('rel1a(prompt, parts)')


def test_the_older_ways_are_in_the_decision_log():
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    rows = {n: next((l for l in log.splitlines() if l.startswith(f'| {n} |')), '') for n in (271, 272, 273, 274)}
    assert all(rows.values()), [n for n, r in rows.items() if not r]
    assert 'Gemini 3.8 Flash' in rows[271] and '`pictures.claude_checks`' in rows[271] and '**kept**' in rows[271]            # A1: who checks; a picture checked before keeps it
    assert "Claude's check found" in rows[272] and '`pictures._named`' in rows[272]                                            # A2: the names
    assert 'true or false' in rows[273] and '`visuals_stage.NA`' in rows[273] and '**kept**' in rows[273]                      # A3-A5: two answers, kept for stored looks
    assert 'a real face' in rows[274] and '`pictures.face_line`' in rows[274] and '`session.likeness`' in rows[274]            # A7
    assert all('release 1' in r for r in rows.values())
