"""design/119 set B, rule 4: one must line per object that a sent reference's own record names and the shot did not ask for, so a leaked thing fails
by name; the shot's own things get no such line."""
from app import visuals_stage as VS
from test_design106_pure import revise_start
from test_design119_a_pure import store_with_extras, three
from test_visuals_stage_pure import saved


def test_each_thing_a_look_reference_brings_is_a_must_line_of_its_own():
    store = store_with_extras()
    out = revise_start(store, **three('L2', "Image 3 is the wall's picture: take its light and air, nothing else."))
    lines = saved(store)['references'][out['reference_id']]['server_checklist']
    not_shown = [l for l in lines if l['check'].startswith('not shown: ')]
    assert [l['check'] for l in not_shown] == ['not shown: a parked bicycle', 'not shown: a clay water pot at the edge of the lane', 'not shown: a white kolam on the swept ground']
    assert all(l['weight'] == 'must' and 'Image 3' in l['pass_when'] and 'anywhere in the frame' in l['pass_when'] for l in not_shown)


def test_a_reference_of_the_pictures_own_thing_brings_no_such_line():
    store = store_with_extras()
    out = revise_start(store, role='start')   # K1 and R1 are both pictures of E1, the picture's own element
    lines = saved(store)['references'][out['reference_id']]['server_checklist'] or []
    assert not [l for l in lines if l['check'].startswith('not shown: ')]
