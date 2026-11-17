"""design/211 part C (section 6.3): the words. The wording script of part C finds each of its anchors once and retires what it replaces;
the sentences the operator reads are one table in `chat_flow`, generic for every category of film, and the page file draws its few fixed
words the same way; every paid label of that table carries its price. Without a database."""
import copy
import importlib.util
import json
import re
from pathlib import Path

from app import chat_flow as CF, page_flow as P

ROOT = Path(__file__).resolve().parents[2]
PAGE = (ROOT / 'plugin' / 'pages' / 'decisions.html').read_text(encoding='utf-8')
ONE_KIND = ('building', 'construction', 'brick', 'documentary', 'mason', 'trade', 'site')   # words that would tie a sentence to one kind of film


def script():
    spec = importlib.util.spec_from_file_location('d211c_wording_v3', ROOT / 'scripts' / 'd211c_wording_v3.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def visuals():
    d = json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    spec = importlib.util.spec_from_file_location('d211d_wording_v3', ROOT / 'scripts' / 'd211d_wording_v3.py')   # design/211, the review: a later script that changes a sentence of this one
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)
    return review.before(next(s for s in d['stages'] if s['name'] == 'visuals'))   # the text as it was before it


def test_each_anchor_of_script_c_is_found_once_or_is_already_applied():
    w, st = script(), visuals()
    assert len(w.PAIRS) == 2 and all(where == 'picture-search' for where, _old, _new in w.PAIRS) and w.COMMANDS == []
    text = next(p for p in st['parts'] if p['name'] == 'picture-search')['text']
    for _where, old, new in w.PAIRS:
        assert (text.count(old) == 1) != (new in text), old[:60]   # found once before the merger runs the script; replaced after


def test_script_c_changes_nothing_when_applied_twice_and_retires_what_it_replaces():
    w, st = script(), visuals()
    parts = copy.deepcopy(st['parts'])
    prompt = w.apply(st['prompt'], parts)
    once = json.dumps([prompt, parts])
    assert json.dumps([w.apply(prompt, parts), parts]) == once and prompt == st['prompt']   # only the part changes
    text = next(p for p in parts if p['name'] == 'picture-search')['text']
    assert w.RETIRED and all(old not in text for old in w.RETIRED) and all(any(r in old for r in w.RETIRED) for _w, old, _n in w.PAIRS)
    for _where, _old, new in w.PAIRS:
        assert new in text and not any(re.search(rf'\b{x}\b', new.lower()) for x in ONE_KIND)
    assert 'A paid answer on the page shows its price on its button: the click, then their done, is their word.' in text   # kept
    assert '`vw visuals round --verdicts out/round-verdicts.json --quote`' in text                                       # the next sentence is part B's: untouched


def test_the_sentences_of_a_v2_round_are_generic_and_the_refusals_are_named():
    said = list(CF.WORDS.values()) + list(CF.REC_WORDS.values()) + list(CF.SIZE_WORDS.values()) + list(CF.GROUPS.values()) + [CF.ACCEPT_NONE, CF.PIC_UNKNOWN, CF.GROUP_DOUBT, CF.GROUP_SETS_DOUBT, P.REST_LEFT, P.REFS_OVER, P.MARKED]
    for text in said:
        assert not any(re.search(rf'\b{x}\b', text.lower()) for x in ONE_KIND), text
        assert 'has no picture of' not in text
    assert CF.ACCEPT_NONE == 'No routine thing is left to accept: answer the open lines one by one.'
    assert CF.PIC_UNKNOWN.format(pic='f1') == 'f1 is not a picture on this line: nothing was marked. Open the page again and mark the picture there.'
    assert P.REST_LEFT == 'The first sets are judged. {r} more are not ordered: the operator orders them on the page (`vw visuals page`), or leaves them.'
    assert CF.LOOK_ONLY == 'do not study them yourself unless the operator asks you to'   # kept for the pictures shown in the chat


def test_a_paid_label_of_the_table_carries_its_price():
    assert CF.WORDS['paid'].format(x=35) == 'paid, about ₹35' and CF.WORDS['again'].format(label='No', paid='paid, about ₹35') == 'No (paid, about ₹35: the set is made again)'
    assert CF.WORDS['rest_make'].format(sets='2 sets', paid='paid, about ₹70') == 'Make the other 2 sets (paid, about ₹70)'
    assert CF.WORDS['accept'].format(n='5 proposals', price='paid, about ₹175') == 'Accept the 5 proposals (paid, about ₹175)'


def test_the_page_file_draws_the_new_fields_with_the_same_words():
    assert CF.WORDS['proposes'].startswith('Claude proposes: {label}. ') and "'Claude proposes: '+line.rec.label+'. '" in PAGE
    for state, tail in (('pass', ': passed.'), ('fail', ': it found faults.'), ('none', ': the check did not run.')):
        assert CF.WORDS['check_' + state] == '{by}' + tail and f"'{tail}'" in PAGE
    for word in ("'The set before'", "'Claude saw: '", "'Weak'", "'To compare with'", 'line.comment_hint||', 'line.partial', 'line.cost', 'line.notes', 'line.earlier', 'p.choice_label||', 'line.tag||',
                 "choice:'pics'", 'function heading(', 'function setMark('):
        assert word in PAGE, word
    assert 'Read before you answer' in PAGE and CF.WORDS['read_first'].startswith('Read before you answer: ')
    assert PAGE.count('fonts.googleapis.com') == 1 and '<script src' not in PAGE   # no new library
