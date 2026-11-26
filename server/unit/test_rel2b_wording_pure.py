"""Release 2, B4 (SK, 20 Nov 2026): the served text of the visuals stage says that several still end-frames ready together come as a
group, shown side by side in one message with one question for each; "never show two items" no longer contradicts it. Through
scripts/rel2b_wording.py, registered in scripts/c1_split_v3.py; the replaced words are retired. Until 25 Nov 2026 the sentence also named
several layout drawings (B4b); retired (A1): shortened through scripts/a1_wording.py (`GROUP_NEW`)."""
import json
from app import core as _core   # SK, 23 Nov 2026: v3.json is read as a film with footage is served it
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def visuals():
    return next(s for s in _core.for_footage(json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8')), 'own')['stages'] if s['name'] == 'visuals')


def test_the_served_text_says_the_group_and_no_longer_forbids_it():
    import a1_wording as A1
    import rel2b_wording as R
    st = visuals()
    assert st['prompt'].count(A1.GROUP_NEW) == 1 and R.GROUP not in st['prompt'] and R.NEVER_NEW in st['prompt'] and R.NEVER not in st['prompt']
    assert A1.GROUP_NEW.startswith(' When several still end-frames of drawn graphics are ready together, it answers with a `group` of up to four instead:') and 'layout drawings' not in st['prompt']
    assert 'side by side in one message' in A1.GROUP_NEW and 'one question for each' in A1.GROUP_NEW and '`vw visuals decide`' in A1.GROUP_NEW
    assert st['prompt'].index(R.ONE) < st['prompt'].index(A1.GROUP_NEW) < st['prompt'].index(R.NEVER_NEW)   # said where one item at a time is said
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert 'or several layout drawings of AI video shots' in A1.RETIRED and 'or several layout drawings of AI video shots' in retired
    # release 2's own step is still found under A1's: with A1's sentence taken back the text holds release 2's, and `before` and `apply` work on it as they did
    rel2 = {**json.loads(json.dumps(st)), 'prompt': st['prompt'].replace(A1.GROUP_NEW, R.GROUP)}
    old = R.before(rel2)
    assert R.GROUP not in old['prompt'] and A1.GROUP_NEW not in old['prompt'] and R.NEVER in old['prompt'] and old['parts'] == st['parts']
    again = json.loads(json.dumps(rel2))
    assert R.apply(again['prompt'], again['parts']) == rel2['prompt'] and again['parts'] == st['parts']   # applying twice changes nothing
    again = json.loads(json.dumps(st))
    assert A1.apply(again['prompt'], again['parts']) == st['prompt'] and again['parts'] == st['parts']    # nor does A1's
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
