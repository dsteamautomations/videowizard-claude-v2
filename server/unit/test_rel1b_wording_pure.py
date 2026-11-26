"""Release 1, rows B1 and D (SK, 20 Nov 2026): the served text says one click against the check (no second question, no typed reason), the
checkers started together, the cards of step 7 in two batches and the two limits it did not name; the wording script is registered, the
replaced words are retired, and the older ways are in the decision log (rows 275 to 279)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def test_the_served_text_says_it_and_the_replaced_words_are_retired():
    import rel1b_wording as W
    import d223_wording   # design/223 retired the take sentences this script wrote (Select, Make another, Reject; the takes' checkers): the text is read as it was before it
    stage = d223_wording.before(__import__('a1_wording').before(next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')))   # A1 (25 Nov 2026) replaced "no still before their Yes", which this script's sentence follows
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    later = next(p for p in stage['parts'] if p['name'] == 'later')['text']
    was = next(p for p in W.before(stage)['parts'] if p['name'] == 'later')['text']
    for where, old, new in W.PAIRS:
        assert later.count(new) == 1 and new not in was and was.count(old) == 1, old[:50]
    for said in ('Yes or Select is one click whatever it says, recorded as approved against the check (no second question, no typed reason); rejecting needs their words',
                 'Start the checkers of the stills and of the takes together, in one message',
                 "every still's card, each with Claude's check, then every word to shoot",
                 'A still takes at most 16 pictures', 'the cost limit of the film is tested before every still and every take, and only the owner can change it'):
        assert said in later, said
    for file, old, new in W.HELPERS:   # D4b: the helper and the skill give the form of `changed_from_plan`
        md = (ROOT / 'plugin' / file).read_text(encoding='utf-8').replace('\r\n', '\n')
        new = __import__('a1_wording').now(file, new)   # A1 (25 Nov 2026): the lines are shown with the still, not with the shot's drawing
        assert md.count(new) == 1 and (new.startswith(old) or old not in md), file
    everything = stage['prompt'] + ''.join(p['text'] for p in stage['parts']) + ''.join((ROOT / 'plugin' / f).read_text(encoding='utf-8') for f, _, _ in W.HELPERS)
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired and s not in everything for s in W.RETIRED)
    assert 'with their reason when the check did not pass' not in everything and 'Use it all the same' not in everything
    for word in ('brick', 'ceiling', 'kiln', 'tumbler', 'documentar'):   # generic words: every category of video
        assert word not in (W.SELECT_NEW + W.NA_NEW + W.AGAIN_NEW).lower()
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('rel1a(prompt, parts)') < split.index('rel1b(prompt, parts)')


def test_the_older_ways_are_in_the_decision_log():
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    rows = {n: next((l for l in log.splitlines() if l.startswith(f'| {n} |')), '') for n in (275, 276, 277, 278, 279)}
    assert all(rows.values()), [n for n, r in rows.items() if not r]
    assert 'Use it all the same' in rows[275] and '**Retired' in rows[275] and '`pictures.picture_line`' in rows[275] and '**kept**' in rows[275]   # B1: the second box
    assert 'D6 of design/222' in rows[276] and '**Retired' in rows[276] and '`takes.answer`' in rows[276] and 'a reason typed on an older page is taken' in rows[276]   # B1: the typed reason
    assert '`chat_flow._guide_items`' in rows[277] and '**Retired' in rows[277] and 'two batches in film order' in rows[277]                       # D2: the per-shot order
    assert '`pictures.short`' in rows[278] and 'One amber line, closed' in rows[278]                                                               # B3
    assert '`visuals_stage.vertical_video`' in rows[279] and 'vertical' in rows[279]                                                               # C5
    assert all('release 1' in r for r in rows.values())


def test_the_retired_words_are_gone_from_the_code_and_the_page_keeps_only_what_the_log_says_is_kept():
    from app import pictures as P, takes as T
    for gone in ('sure', 'sure_go', 'sure_steps', 'sure_steps_alike', 'sure_steps_go', 'hint_why', 'go_why', 'need_why', 'say_select_why'):
        assert gone not in P.W, gone
    for gone in ('hint_why', 'hint_why_none', 'hint_why_short', 'hint_why_old', 'go_why', 'need_why', 'say_select_why'):
        assert gone not in T.W, gone
    said = json.dumps([P.W, P.PAGE, T.W, T.PAGE], ensure_ascii=False)
    assert 'Use it all the same' not in said and 'say why' not in said and 'Why is it right for the film' not in said
    page = (ROOT / 'plugin' / 'pages' / 'decisions.html').read_text(encoding='utf-8')
    assert "id:'pcheckb'" in page and "'aria-expanded'" in page and "id:'pmore'" not in page                # B3: the line is a button; "See all N" is gone
