"""design/211 part A, the instructions: each anchor of the wording script is found once, applying it twice changes nothing, its old
sentences are retired, and the new sentences name what the server really has. It passes before the merger has run the script (the
script is applied here to a copy) and after."""
import copy
import json
import sys
from pathlib import Path

from app import ref_find as RF

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import d211a_wording_v3 as W   # noqa: E402


def stage():
    return next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')


def applied():
    st = stage()
    parts = copy.deepcopy(st['parts'])
    prompt = W.apply(st['prompt'], parts)   # it stops (SystemExit) when an anchor is not found exactly once
    return st, prompt, parts


def test_each_anchor_is_found_once_and_applying_twice_changes_nothing():
    st, prompt, parts = applied()
    text = prompt + ''.join(p['text'] for p in parts)
    assert W.PAIRS and all(where == 'picture-search' and new in text and old not in text for where, old, new in W.PAIRS)
    again = copy.deepcopy(parts)
    assert W.apply(prompt, again) == prompt and again == parts
    assert prompt == st['prompt']                                                           # part A changes the picture search only
    assert [p['name'] for p in parts if p not in st['parts']] in ([], ['picture-search'])


def test_the_old_sentences_are_retired_and_gone_from_what_the_assistant_reads():
    st, prompt, parts = applied()
    cmd = (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    for old, new in W.COMMANDS:
        assert new in cmd or cmd.count(old) == 1, old
        cmd = cmd if new in cmd else cmd.replace(old, new)
    read = prompt + ''.join(p['text'] for p in parts) + cmd + ''.join(p.read_text(encoding='utf-8') for p in (ROOT / 'plugin' / 'agents').glob('*.md'))
    assert W.RETIRED and all(len(s.split()) >= 4 and s not in read for s in W.RETIRED)
    assert '`vw-reference-finder` and `vw-set-look`' in cmd and '`vw visuals digest`' in cmd and '`vw visuals trial --file`' in cmd and '`vw visuals look --file`' in cmd
    if all(new in json.dumps(st, ensure_ascii=False) for _, _, new in W.PAIRS):            # the merger has run the script: the list is written
        retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
        assert all(s in retired for s in W.RETIRED)


def test_the_new_sentences_name_the_servers_commands_and_keep_the_word_match_as_the_way_back():
    _, _, parts = applied()
    text = next(p['text'] for p in parts if p['name'] == 'picture-search')
    for said in ('`vw visuals digest`', '`vw-reference-finder` helpers, about five things each, up to six at a time', '`vw visuals trial --file`', '`vw visuals look --file`',
                 'A trial frame is not a reference.', "The rule for a good frame is the server's", '`vw visuals elements` then names the likely clips by words'):
        assert said in text, said
    assert (RF.THINGS_PER_HELPER, RF.HELPERS) == (5, 6)                                     # the two figures the sentence says
    assert RF.FRAME_RULE[:40] not in text                                                   # the rule's text lives in the server only
    for field in ('trial', 'view', 'verdict', 'seen', 'keep', 'closest', 'not_searched', 'clips', 'note'):   # the fields `look_record` reads
        assert field in text
    assert 'Then the round, once any drawing set is approved' in text                       # part B's anchor is left as it was
