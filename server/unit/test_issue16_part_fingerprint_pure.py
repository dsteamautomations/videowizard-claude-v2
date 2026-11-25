"""Issue 16, requirement R1 (VW-25, SK 25 Nov 2026): a shared part whose drawing did not change keeps its fingerprint.

Seen on VW-25: one drawing was taken off the list of drawings (data-shots) of eight shared parts; no drawing of any part changed. The server's
fingerprint of a part covered its three labels (data-shots, data-element, data-view), so six approved stills counted as changed, were uploaded and
checked again, and their verdicts were then refused: "the brief changed after these rules were written, in the line(s): "Use these parts"".
Now a part whose drawing is the same as in the approved file takes over the approved part's fingerprint when the new file is uploaded. The older
way (any change inside a part's <symbol>, also of its labels or its spacing, made every still, render and brief that uses the part stale) is
retired. A part redrawn is stale as before: test_design221_p3c_pure. Without a database."""
import hashlib
from xml.etree import ElementTree as ET

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design221_p1_pure import NEW
from test_design221_p3c_pure import PARTS, SOLID, USES, chat, no_still, parts, project, selectable, still_verdict, two, upload
from test_visuals_stage_pure import USER, g, saved

WALL = '<symbol id="part-wall" viewBox="0 0 200 100" data-element="E1"'
listed = lambda shots, text=PARTS: text.replace(WALL, WALL + f' data-shots="{shots}"')   # the wall's part naming these drawings
REDRAWN = PARTS.replace('height="100" fill', 'height="80" fill')
prints = lambda store: {p['id']: p['digest'] for p in saved(store)['motion_parts_approved']['parts']}
lines = lambda store, shot='MO1': VS.motion_brief(store, NEW, [], shot)['lines']


def approved_still(store):
    still = upload(store, project(**{'compositions/wall.html': USES}), still=True)
    still_verdict(store, still, {SOLID: True})
    chat(store, 'still end-frame')[0]['_run']('approve', 'Approve', '')
    return still


def test_a_list_change_alone_leaves_the_approved_still_and_the_next_upload():
    store = no_still(two())
    parts(store, listed('MO1 MO2'))
    approved_still(store)
    parts(store, listed('MO1'))   # as on VW-25: a drawing leaves the part's list; the wall is drawn as before
    st = saved(store)['motion_stills']['MO1']
    assert VS.still_approved(st) and not VS.still_stale(store, saved(store), st)
    assert upload(store, project(**{'compositions/wall.html': USES, 'style.css': 'b {}'}))   # was refused: "its parts changed since the still end-frame was approved"


def test_a_list_change_alone_asks_no_render_again():
    store = two()
    parts(store, listed('MO1 MO2'))
    sha = upload(store, project(**{'compositions/wall.html': USES}))
    conn = selectable(store, sha)
    said = VS.parts_answer(store, USER, NEW, [], parts(store, listed('MO1'), ok=False)['sha256'], True, 'Approve')
    assert 'Its parts changed' not in said['for_the_assistant']
    with pytest.raises(Problem, match='This drawing has no fact check of its project yet'):   # the gate after the parts gate, which refused before:
        g(lambda: VS.select_take(conn, store, USER, NEW, [], 'job-9', 'yes'))   # "Its parts changed since this drawing was rendered: render it again"


def test_the_refusal_of_25_nov_the_verdict_after_a_list_change():
    store = no_still(two())
    parts(store, listed('MO1 MO2'))
    still = upload(store, project(**{'compositions/wall.html': USES}), still=True)
    was = lines(store)
    assert 'Use these parts' in was
    parts(store, listed('MO1'))
    assert lines(store) == was
    still_verdict(store, still, {SOLID: True})   # was refused: the brief changed after these rules were written, in the line(s): "Use these parts"
    assert len(chat(store, 'still end-frame')) == 1


def test_a_drawing_taken_off_a_list_reads_its_own_brief_again_and_no_other_does():
    store = no_still(two())
    parts(store, listed('MO1 MO2'))
    one, two_ = lines(store), lines(store, 'MO2')
    parts(store, listed('MO1'))
    assert VS.brief_changed(one, lines(store)) == []
    assert VS.brief_changed(two_, lines(store, 'MO2')) == ['Use these parts']


@pytest.mark.parametrize('text', [
    PARTS.replace(' data-element="E1"', ''),                 # only the thing
    PARTS.replace(WALL, WALL + ' data-view="cutaway"'),      # only the view
    PARTS.replace(WALL, '<symbol   data-element="E1"\n  viewBox="0 0 200 100" id="part-wall"').replace('<title>Wall section</title>', '\n  <title>Wall section</title>\n  ')
         .replace('</symbol>\n<symbol id="part-arrow"', '\n</symbol>\n\n<symbol id="part-arrow"'),   # the same drawing, written with other spacing and attribute order
    listed('MO1', PARTS.replace('<title>Wall section</title>', '<title>  Wall section </title>')),   # a text that differs by the spaces at its ends
])
def test_labels_and_spacing_are_not_the_drawing(text):
    store = two()
    parts(store)
    was = prints(store)
    parts(store, text)
    assert prints(store) == was


def test_a_part_redrawn_or_added_gets_a_new_fingerprint_and_the_others_keep_theirs():
    store = two()
    parts(store)
    was = prints(store)
    parts(store, listed('MO1', REDRAWN).replace('</svg>', '<symbol id="part-new" viewBox="0 0 10 10"><title>New</title><rect width="10" height="10"/></symbol>\n</svg>'))
    now = prints(store)
    assert now['part-wall'] != was['part-wall'] and now['part-arrow'] == was['part-arrow'] and len(now['part-new']) == 16


def test_the_first_file_of_a_film_is_fingerprinted_as_before():
    store = two()
    parts(store)
    assert prints(store) == {el.get('id'): hashlib.sha256(ET.tostring(el)).hexdigest()[:16] for el in ET.fromstring(PARTS)}


def test_two_list_changes_in_a_row_keep_the_first_fingerprint():
    store = no_still(two())
    parts(store)
    was = prints(store)
    approved_still(store)
    parts(store, listed('MO1 MO2'))
    parts(store, listed('MO1'))
    st = saved(store)['motion_stills']['MO1']
    assert prints(store) == was and not VS.still_stale(store, saved(store), st)


def test_a_new_file_is_compared_with_the_approved_one_not_with_a_rejected_one():
    store = two()
    parts(store)
    was = prints(store)
    VS.parts_answer(store, USER, NEW, [], parts(store, REDRAWN, ok=False)['sha256'], False, 'Reject', 'the wall is too low')
    parts(store, listed('MO1'))   # the approved drawing again, with a list
    assert prints(store) == was
    parts(store, listed('MO1', REDRAWN), ok=False)   # the rejected drawing again: not the approved one, so a new fingerprint
    assert {p['id']: p['digest'] for p in saved(store)['motion_parts']['parts']}['part-wall'] != was['part-wall']


def test_an_approved_file_that_cannot_be_read_carries_nothing_and_stops_nothing():
    store = two()
    parts(store)
    was = prints(store)
    del store.files[saved(store)['motion_parts_approved']['key']]
    parts(store, listed('MO1'))   # the upload succeeds; the part is fingerprinted as a new one, the older way
    assert prints(store)['part-wall'] != was['part-wall'] and prints(store)['part-arrow'] == was['part-arrow']
