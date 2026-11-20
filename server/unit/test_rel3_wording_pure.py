"""Release 3 (SK, 20 Nov 2026), the words. E3: the placing rule's examples are generic (no building-film units). E4: "Nothing of this is asked
one at a time during the builds" has a path for a question nobody could foresee. C1 to C4, C6, E2: the served text and the plugin's two texts
say the new behaviour once each. Through scripts/rel3_wording.py, registered in scripts/c1_split_v3.py; the replaced words are retired."""
import json
import sys
from pathlib import Path

import pytest

from app import library

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def visuals():
    return next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')


def part(st, name):
    return next(p['text'] for p in st['parts'] if p['name'] == name)


def test_e3_the_placing_rule_names_units_of_any_film():
    with pytest.raises(ValueError) as e:
        library.check_prompt('A cup stands in the middle of the table.')
    said = str(e.value)
    assert said.endswith("say the landmark and how far from it, in a unit the picture shows (a hand, a pace, the width of a thing in the frame).")
    src = (ROOT / 'server' / 'app' / 'library.py').read_text(encoding='utf-8')
    assert '(bricks, paces, a hand, a doorway)' not in src
    library.check_prompt('A cup stands in the middle of the table, two hands from its near edge.')   # a measured place is taken as before


def test_e4_a_question_nobody_could_foresee_has_its_path():
    import rel3_wording as R
    later = part(visuals(), 'later')
    assert R.UNFORESEEN in later and R.ONE_AT_A_TIME not in later
    for words in ('A question nobody could foresee', 'is asked at once', '`vw visuals ask`', 'your recommended answer first', 'the builds that do not depend on the answer go on'):
        assert words in R.UNFORESEEN, words
    assert later.index('a choice that changes a fact or a proportion is asked once, with the others, before the first drawing is built') < later.index(R.UNFORESEEN)


def test_the_plan_step_the_common_text_and_the_render_say_the_new_behaviour_once():
    import rel3_wording as R
    st = visuals()
    plan, later = part(st, 'plan'), part(st, 'later')
    assert plan.count(R.NO_TEXT + R.AT_THE_PLAN) == 1 and '`labels_missing`' in R.AT_THE_PLAN and '`supplied_missing`' in R.AT_THE_PLAN and 'in/brand/' in R.AT_THE_PLAN
    assert 'ask the operator nothing' in R.AT_THE_PLAN and 'a label in new words is asked with its gap' in R.AT_THE_PLAN
    assert st['prompt'].count(R.QUOTING + R.ANSWERS) == 1 and '`vw visuals propose --file out/visual-plan.json --answers <the item>`' in R.ANSWERS
    assert later.count('--wait` returns when the render is ready') == 1 and R.RENDER not in later
    text = json.dumps(st, ensure_ascii=False)
    assert text.count('`vw motion render --shot S --wait`') == 1                           # the wait is named once


def test_before_gives_the_older_text_and_applying_twice_changes_nothing():
    import rel3_wording as R
    st = visuals()
    old = R.before(st)
    assert R.ONE_AT_A_TIME in part(old, 'later') and R.UNFORESEEN not in part(old, 'later') and R.RENDER in part(old, 'later')
    assert R.AT_THE_PLAN not in part(old, 'plan') and R.ANSWERS not in old['prompt']
    again = json.loads(json.dumps(st))
    assert R.apply(again['prompt'], again['parts']) == st['prompt'] and again['parts'] == st['parts']
    words = lambda s: len(s['prompt'].split()) + sum(len(p['text'].split()) for p in s['parts'])
    assert words(st) - words(old) == 177, words(st) - words(old)                          # what the visuals word pin rises by


def test_the_plugins_texts_say_what_a_defect_holds():
    import rel3_wording as R
    cmd = (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    op = (ROOT / 'plugin' / 'operator-CLAUDE.md').read_text(encoding='utf-8')
    assert cmd.count(R.DEFECT_NEW) == 1 and R.DEFECT_OLD not in cmd and '`--shot S`' in R.DEFECT_NEW
    assert op.count(R.OPERATOR_NEW) == 1 and R.OPERATOR_OLD not in op


def test_the_replaced_words_are_retired_and_the_script_is_registered():
    import rel3_wording as R
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    text = json.dumps(visuals(), ensure_ascii=False) + (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8') + (ROOT / 'plugin' / 'operator-CLAUDE.md').read_text(encoding='utf-8')
    for s in R.RETIRED:
        assert s in retired and s not in text, s
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('from rel2c_wording import') < split.index('from rel3_wording import apply as rel3') < split.index('from d132_wording_v3 import')
