"""Release 2, B4 and B4b (SK, 20 Nov 2026): the served text of the visuals stage says that several still end-frames, or several layout
drawings, ready together come as a group, shown side by side in one message with one question for each; "never show two items" no longer
contradicts it. Through scripts/rel2b_wording.py, registered in scripts/c1_split_v3.py; the replaced words are retired."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def visuals():
    return next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')


def test_the_served_text_says_the_group_and_no_longer_forbids_it():
    import rel2b_wording as R
    st = visuals()
    assert R.GROUP in st['prompt'] and R.NEVER_NEW in st['prompt'] and R.NEVER not in st['prompt']
    assert 'side by side in one message' in R.GROUP and 'one question for each' in R.GROUP and 'up to four' in R.GROUP and '`vw visuals decide`' in R.GROUP
    assert st['prompt'].index(R.ONE) < st['prompt'].index(R.GROUP) < st['prompt'].index(R.NEVER_NEW)   # said where one item at a time is said
    old = R.before(st)
    assert R.GROUP not in old['prompt'] and R.NEVER in old['prompt'] and old['parts'] == st['parts']
    again = json.loads(json.dumps(st))
    assert R.apply(again['prompt'], again['parts']) == st['prompt'] and again['parts'] == st['parts']   # applying twice changes nothing
    added = len(st['prompt'].split()) - len(old['prompt'].split())
    assert 0 < added <= 70, added


def test_the_replaced_words_are_retired_and_the_script_is_registered():
    import rel2b_wording as R
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    text = json.dumps(visuals(), ensure_ascii=False)
    for s in R.RETIRED:
        assert s in retired and s not in text, s
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('from rel1c_wording import') < split.index('from rel2b_wording import apply as rel2b') < split.index('from d132_wording_v3 import')
