"""Release 1 of 27 Nov 2026, phase 3, parts G and H (SK approved).

G (6.6): one colour added for one drawing was written into the Palette line of every drawing, so every finished drawing read as "not
checked". Now a drawing's Palette line names only the colours added for it. H (4.10): an upload that redraws shared parts was refused once
for each missing part; now one refusal names them all, and the brief says the rule right after what the drawing shows. Each test failed
first. Without a database."""
import pytest

from app import visuals_stage as V
from app.errors import Problem
from test_design218_colours_pure import add, drawn, plan
from test_design221_p3c_pure import PARTS, build, parts, two, upload

BASE = 'Palette (not yet approved): navy #12324A, orange #FF8800, concrete mid grey #8A8A8A.'


# ---------- G ----------

def test_a_colour_added_for_one_drawing_is_in_that_drawings_palette_line_only():
    s, p = {}, plan(drawn('D1'), drawn('D2'))
    add(s, p, shots=('D1',))
    assert V.palette_line(p, s, 'D1') == BASE + ' Added for this drawing (the spec wins where they differ): walls #5A524C (dark warm grey).'
    assert V.palette_line(p, s, 'D2') == BASE                                  # a finished drawing elsewhere keeps its line, so its check stands


def test_the_same_colour_added_later_for_a_second_drawing_changes_only_that_one():
    s, p = {}, plan(drawn('D1'), drawn('D2'), drawn('D3'))
    add(s, p, shots=('D1',))
    one, three = V.palette_line(p, s, 'D1'), V.palette_line(p, s, 'D3')
    add(s, p, shots=('D2',))
    assert V.palette_line(p, s, 'D1') == one and V.palette_line(p, s, 'D3') == three and 'walls #5A524C' in V.palette_line(p, s, 'D2')


def test_a_colour_named_for_every_drawing_is_in_every_line():
    s, p = {}, plan(drawn('D1'), drawn('D2'))
    add(s, p, shots=('D1', 'D2'))
    assert all('walls #5A524C' in V.palette_line(p, s, d) for d in ('D1', 'D2'))


# ---------- H ----------

def test_one_refusal_names_every_missing_part():
    store = two()
    parts(store, PARTS.replace('<symbol id="part-arrow"', '<symbol id="part-arrow" data-shots="MO1"'))   # the arrow's part names this drawing
    with pytest.raises(Problem) as e:
        upload(store)
    said = str(e.value)
    assert 'place part-wall with <use href="#part-wall">' in said and 'place part-arrow with <use href="#part-arrow">' in said   # was: the wall alone, the arrow on the next upload
    assert said.count(V.PARTS_AGAIN.strip()) == 1                               # the next step is said once


def test_the_brief_says_the_rule_right_after_what_the_drawing_shows():
    store = two()
    parts(store)
    b = build(store)['brief']
    assert b.index('Use these parts') < b.index('Claims (each must') and 'An upload that redraws one of them is refused.' in b
