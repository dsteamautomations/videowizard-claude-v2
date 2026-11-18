"""design/215, the instruction text (version 3, the visuals stage), the command file, the finder's helper file and the operator's rules
file after `scripts/d215_wording_v3.py`: the three labels, how the making goes, no cost word at the references, an unticked picture, one
order of authority (the program's), the corrections kept per thing, the search record, the step's new name, the look and an object in use
by category. The older sentences are retired by name. Without a database."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import d215_wording_v3 as W   # noqa: E402

from app import ref_sets as RS   # noqa: E402
from app.config import Settings   # noqa: E402

STAGE = next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
PART = {p['name']: p['text'] for p in STAGE['parts']}
REFS = PART['picture-search']
CMD = (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
RULES = (ROOT / 'plugin' / 'operator-CLAUDE.md').read_text(encoding='utf-8')
FINDER = (ROOT / 'plugin' / 'agents' / 'vw-reference-finder.md').read_text(encoding='utf-8')


def test_every_new_sentence_is_in_and_applying_twice_changes_nothing():
    st = json.loads(json.dumps(STAGE))
    assert W.apply(st['prompt'], st['parts']) == STAGE['prompt'] and st['parts'] == STAGE['parts']
    for where, old, new in W.PAIRS:
        text = STAGE['prompt'] if where == 'common' else PART[where]
        assert new in text and (old in new or old not in text), old[:60]
    before = W.before(STAGE)
    for where, old, new in W.PAIRS:   # each anchor was there once before the script
        text = before['prompt'] if where == 'common' else next(p['text'] for p in before['parts'] if p['name'] == where)
        assert text.count(old) == 1, old[:60]
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert 'from d215_wording_v3 import apply as d215' in split and split.index('d214(prompt, parts)') < split.index('d215(prompt, parts)')


def test_the_replaced_sentences_are_retired_by_name_and_gone():
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    everything = STAGE['prompt'] + ''.join(PART.values())
    for s in W.RETIRED:
        assert s in retired and s not in everything, s


def test_the_references_part_names_no_cost_word_and_no_older_label():
    assert not re.search(r'\bfree\b|\bpaid\b|₹', REFS.replace('(never "free" or "paid")', ''))   # the two words are named once, to forbid them
    assert not re.search(r'Leave out|leave it out|operator left out|can be left out|leaving some out|character sheet|Use my own picture', REFS)
    for label in ('No reference needed', 'Do not make this set', 'Go on without a reference', 'Make a set with words', 'Upload my own'):
        assert label in REFS, label
    assert 'names no cost and no cost word (never "free" or "paid")' in REFS and 'says the limit with no figure' in REFS


def test_the_text_says_what_the_program_does():
    assert 'an unticked picture is only not used, and no other is searched' in REFS                                    # W5
    order = "the operator's words, your added words, the film's own pictures"                                           # W6: the program's order, said once
    assert order in REFS and "the operator's words, the film's own pictures (the approved drawing" not in REFS
    assert [RS.BY_OPERATOR, RS.BY_WRITER] == RS._authority(True, True, True, False, True)[:2]
    assert 'made to check the method' in REFS and 'pass it on as it is' in REFS                                          # change 7
    assert "never write a correction into the plan's description" in REFS and 'This applies to every picture of this thing' in REFS   # change 5
    assert 'searched (with the pages, where it gave any), did not search, not asked (a person\'s set), or not known' in REFS          # change 3
    assert '"measure it first" and the "Not this" list are not applied to a set' in REFS                                # R1 to R5
    assert 'on a documentary-explainer film no person, only the hand that holds it' in REFS                             # W8
    assert "by default the look the film's category and the Direction call for: on a documentary-explainer film muted and true to life" in PART['treatment']   # change 4
    assert 'sizes, materials and graphic specs' in STAGE['prompt'] and 'sizes, materials and graphic specs' in PART['plan']                                     # change 6
    assert 'the drawings and the materials' not in STAGE['prompt'] + PART['plan']


def test_the_command_file_the_helper_and_the_operators_rules_say_the_same():
    for old, new in W.COMMANDS:
        assert new in CMD and old not in CMD, old[:60]
    assert W.before_commands(CMD) != CMD and 'tell the operator the spend)' not in CMD.split('the server refuses a call past')[0]
    refs = CMD[CMD.index('trial frames (`vw visuals trial --file`'):CMD.index('Other pictures:')]
    assert not re.search(r'\(free\)|, free\)|\(paid|Use my own picture|is left out', refs)
    assert 'it never names a cost or a cost word' in FINDER
    assert '`vw-reference-finder` and `vw-set-look`' in RULES and "nothing is ordered there without the operator's own word, and no amount or cost word is said there" in RULES   # W7, W3


def test_the_versions_of_this_release():
    assert Settings.model_fields['SERVER_VERSION'].default == '0.112.0' and Settings.model_fields['PLUGIN_MIN_VERSION'].default == '0.96.0'
    assert json.loads((ROOT / 'plugin' / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))['version'] == '0.96.0'
