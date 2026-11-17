"""design/211 part B, the instructions (section 3.12): the wording script of part B changes its own sentences of the picture search and the
same ones in the plugin's command file, each anchor found once, and retires the sentences it replaces. The script is not run against the
repository by a builder (the merger runs the three scripts once): these tests apply it to a copy. The instruction, the request and the check
say the same of a way of working: hands may be shown. Without a database."""
import copy
import json
import sys
from pathlib import Path

from app import ref_sets as RS
import d211_fixture as F

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import d211b_wording_v3 as W   # noqa: E402

OTHERS = ('`vw visuals elements` shows where each is seen', 'A clip frame is free and exact', 'never a blurred one for identity', 'The operator answers both steps on the page',
          'In the chat, one at a time (`vw visuals next`, section E)', "except the plugin's helpers the steps name")   # the anchors of parts A and C: never inside one of part B's


def stage():
    return next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')


def applied():
    st = stage()
    parts = copy.deepcopy(st['parts'])
    prompt = W.apply(st['prompt'], parts)
    return st, prompt, parts


def commands(text):
    for old, new in W.COMMANDS:
        if new not in text:
            assert text.count(old) == 1, old[:70]
            text = text.replace(old, new)
    return text


def test_each_anchor_of_part_b_is_found_once_in_the_picture_search():
    part = next(p for p in stage()['parts'] if p['name'] == 'picture-search')['text']
    assert len(W.PAIRS) == 7 and all(where == 'picture-search' for where, _, _ in W.PAIRS)
    for _, old, new in W.PAIRS:
        assert part.count(old) == 1 or new in part, old[:70]            # the second: the merger has run the script
        assert old != new and not any(o in old for o in OTHERS), old[:70]
    olds = [old for _, old, _ in W.PAIRS]
    assert not any(a in b for a in olds for b in olds if a is not b)    # no anchor inside another


def test_the_script_puts_its_sentences_in_and_applying_twice_changes_nothing():
    st, prompt, parts = applied()
    text = next(p for p in parts if p['name'] == 'picture-search')['text']
    assert prompt == st['prompt'] and all(new in text for _, _, new in W.PAIRS)
    again = copy.deepcopy(parts)
    assert W.apply(prompt, again) == prompt and again == parts
    untouched = {p['name']: p['text'] for p in st['parts'] if p['name'] != 'picture-search'}
    assert {p['name']: p['text'] for p in parts if p['name'] != 'picture-search'} == untouched
    for words in ("A round whose answer has no `v` is an older round: follow the tool's answers.", '`rec`, your proposal', '`prompt` only for what the plan does not say',
                  '`vw visuals round --looks`', '`vw-set-look` helpers', '`vw visuals round --rewrite out/round-rewrites.json`', '`vw visuals round --rest --quote`',
                  '`vw visuals round --make E --quote`', 'verdict: approve|clean|ignore', 'orders the first three sets only', 'a set is made three times at most',
                  "the film's picture wins over the web", 'what comes next (`then`)', 'The server shows the operator no set before its look.'):
        assert words in text, words
    import d211a_wording_v3 as A, d211c_wording_v3 as C   # after the merge: the sentences of parts A and C are in, beside part B's
    for where, old, new in A.PAIRS + C.PAIRS:
        assert where != 'picture-search' or (new in text and old not in text), new[:70]


def test_the_replaced_sentences_are_retired_and_gone_from_what_the_assistant_reads():
    st, prompt, parts = applied()
    now = prompt + ''.join(p['text'] for p in parts)
    before = st['prompt'] + ''.join(p['text'] for p in st['parts'])
    cmd_before = (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    cmd = commands(cmd_before)
    agents = ''.join(p.read_text(encoding='utf-8') for p in (ROOT / 'plugin' / 'agents').glob('*.md'))
    listed = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert len(W.RETIRED) == len(set(W.RETIRED)) == 10
    assert all(len(s.split()) >= 4 for s in W.RETIRED)                   # the retired list takes sentences of four words or more
    for old in W.RETIRED:
        assert old not in now and old not in cmd and old not in agents, old
        assert old in before or old in cmd_before or old in listed, old  # it was really said before
    assert all(new in cmd for _, new in W.COMMANDS) and len(W.COMMANDS) == 5
    assert '\r\n' not in cmd or '\r\n' in cmd_before


def test_the_instruction_the_request_and_the_check_agree_that_a_way_of_working_may_show_hands():
    _, _, parts = applied()
    text = next(p for p in parts if p['name'] == 'picture-search')['text']
    assert 'a way of working at its key moment, its result, and the tool meeting the material (hands and forearms, no face)' in text
    assert 'hands and forearms doing it' in RS.MAY_SHOW['technique'] and RS.MAY_SHOW['process'] == RS.MAY_SHOW['technique'] and 'No face' in RS.MAY_SHOW['technique']
    lay = next(e for e in F.plan()['elements'] if e['id'] == 'T_LAY')
    lines = {name: when for name, when in RS._kind_lines(lay['kind'])}
    assert 'the hands and the tool doing it' in lines['the action is shown'] and 'no person' not in lines and 'no person' in dict(RS._kind_lines('object'))
    helper = (ROOT / 'plugin' / 'agents' / 'vw-set-look.md').read_text(encoding='utf-8')
    assert 'a way of working with the hands and forearms doing it, and no face' in helper and 'Hands in a way of working are right, not a fault.' in helper
    assert [v['name'] for v in RS.WAY] == ['the action at its key moment', 'the result just after', 'the tool meeting the material']
    assert 'an object or a material whole, as the film uses it, and its telling detail (no person; a hand only in use)' in text and 'a hand may hold it only' in RS.MAY_SHOW['object']


def test_the_commands_the_sentences_name_are_the_tools():
    tool = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    for flag in ("'--rest'", "'--rewrite'", "'--looks'", "base + '/round/looks'", "base + '/round/rest'", "base + '/round/rewrite'"):
        assert flag in tool, flag
    assert '`vw visuals round --rewrite out/round-rewrites.json`' in RS.REWRITE_DUE and '`vw visuals round --looks`' in RS.SETS_LOOK and '`vw-set-look` helpers' in RS.SETS_LOOK
