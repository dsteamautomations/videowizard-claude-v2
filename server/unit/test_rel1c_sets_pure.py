"""Release 1, the critic's point 8 (money): a first reference set whose every line was answered "does not apply" was judged on nothing, so it
does not count as "use" for the rule that orders the other sets with no word of the operator: it counts as not checked, and the others wait."""
from app import ref_sets as RS
import d211_fixture as F
from test_design211b_older_pure import saved
from test_design220_sample_by_check_pure import _v2_round, looks, made, ordered, send, written   # noqa: F401 (the fixtures)


def test_8_a_first_set_whose_every_line_does_not_apply_is_unchecked_and_the_other_sets_are_not_ordered(written):
    store, conn = made()
    sets = looks(store)
    for pic in sets[0]['pictures']:
        pic['lines'] = [{**l, 'pass': 'na', 'seen': 'This view cannot show it.'} for l in pic['lines']]
    out = send(store, conn, sets)
    rd = saved(store)['round']
    eid = sets[0]['element_id']
    assert out['refused'] == {} and 'rest_ordered' not in out and ordered(conn) == list(F.FIRST)          # nothing paid without the operator's word
    assert eid in RS.first_sets(saved(store), rd)['unchecked'] and rd['rest_held']['unchecked'] == [eid]
