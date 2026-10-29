"""design/106 N1-N4, R1-R3: a picture's note is easy to give and stays editable (design/121 change 4: after the sheet too, marking it); the References step puts the sheet first."""
import json
from pathlib import Path

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design94_r1_pure import cheap, film, pic, refs   # noqa: F401  (cheap: the autouse price fixture)
from test_visuals_stage_pure import RUN, USER, FakeConn, g, saved, store_with

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def web(rid, status='approved', note='keep the red oxide'):
    return pic(rid, status=status, kind='web', source={'note': note, 'search_id': 's1', 'n': 1})


# ---------- N4: the note stays editable until the element's sheet is made ----------

def test_a_saved_pictures_note_can_be_changed_and_after_the_sheet_marks_it():
    doc, sess = film(references=refs(web('W1')))
    store = store_with(sess, doc)
    out = VS.note_reference(store, USER, RUN, [], 'W1', 'keep the red oxide; avoid the shine')
    assert saved(store)['references']['W1']['source']['note'] == 'keep the red oxide; avoid the shine' and 'note saved' in out['next'].lower()
    doc, sess = film(references=refs(web('W1'), pic('S1', status='candidate', kind='sheet', parents=['W1'])))
    store = store_with(sess, doc)
    VS.note_reference(store, USER, RUN, [], 'W1', 'after the sheet')   # design/121 change 4: saved, and the sheet is marked for a new one
    assert saved(store)['references']['S1']['sources_changed'] is True
    doc, sess = film(references=refs(web('W1'), pic('S1', status='rejected', kind='sheet', parents=['W1'])))
    VS.note_reference(store_with(sess, doc), USER, RUN, [], 'W1', 'a rejected sheet does not block')   # the next sheet reads the new note


def test_the_assistant_reads_the_latest_note_in_status():
    doc, sess = film(references=refs(web('W1', note='avoid the brand text')))
    st = VS.status(FakeConn([]), store_with(sess, doc), RUN, [], repair=False)
    assert next(r for r in st['references'] if r['id'] == 'W1')['note'] == 'avoid the brand text'


# ---------- N1-N3, R1-R2: the page ----------

def test_the_round_shows_a_note_under_every_ticked_picture_and_asks_before_finishing():
    card = PAGE[PAGE.index('function resultCard('):PAGE.index('function elState(')]
    assert 'data-gnote=' in card                                                             # N1
    assert 'words for the whole pass' in PAGE and 'picture notes go under each ticked picture' in PAGE.lower()   # N2
    assert 'finish pass 2?' in PAGE and 'data-a="round-picks-back"' in PAGE                   # N3
    assert 'data-a="save-note"' in PAGE                                                       # N4 on the page


def test_the_references_step_puts_the_sheet_first_and_folds_the_rest():
    body = PAGE[PAGE.index('function renderReferences('):PAGE.index('function tickChips(')]
    assert "show all ('" in body and 'saved=' in body                                         # R1: saved picks fold the unpicked results and the search
    assert "sheet=sheets.filter(r=>r.status!=='rejected').pop()" in body and body.index("'<h3>Reference sheet") < body.index('src+web')   # R2: the sheet first whenever one exists
