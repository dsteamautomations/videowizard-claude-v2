"""Defect 29 (VW-7): after the operator had used two steps, the page held two panels with id "panel"; the controls were wired to the first, a hidden
stale one, so Approve, Reject and zoom on the visible panel did nothing. A step that is not shown is emptied, so one panel exists at a time."""
from pathlib import Path

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def test_render_empties_every_step_not_shown():
    body = PAGE[PAGE.index('function render(){'):]
    body = body[:body.index('\n}\n')]
    assert "if(k!==step)sec.innerHTML=''" in body


def test_every_step_change_goes_through_render():
    for site in ("step=s;remember('step',s);render();", "step=st;remember('step',st);"):
        assert site in PAGE
    assert PAGE.count("remember('step'") == 2
