"""SK, 28 Nov 2026 (VW-26, the operator's "remove all camera shake"; finding F4): the server asked for a tiny handheld drift in every AI video shot
(the layout camera, the take's words, the take page). It is removed for every film: the camera is held still on a tripod.
And: `vw next` names the open text overlays step once visuals is done, so a chat that starts again finds it without a refused call."""
from pathlib import Path

from app import core, guide, overlay_stage as S
from app.errors import Problem

ROOT = Path(__file__).resolve().parents[2]
RUN = {'id': 'r1', 'code': 'VW-30', 'client_id': 'c1'}
FILM = {'fps': 25, 'frames': 400, 'cuts': [], 'words': [], 'font': 'Inter', 'scripts': ['latin']}


class Store(dict):
    def put(self, key, data, mime=None):
        self[key] = data

    def get(self, key):
        if key not in self:
            raise Problem(404, 'NOT_FOUND', key)
        return self[key]

    def exists(self, key):
        return key in self


def read(*parts):
    return (ROOT.joinpath(*parts)).read_text(encoding='utf-8')


def test_the_layout_camera_stands_still():
    src = read('server', 'blender', 'guide_scene.py')
    assert 'shake' not in src and 'handheld' not in src and 'p_, a_ = cpos, caim' in src


def test_the_take_words_and_the_take_page_say_a_still_camera():
    assert 'handheld' not in guide.TAKE_OPEN
    assert 'as in the video (held still on a tripod: no shake, no drift). One continuous shot' in guide.TAKE_OPEN
    page = read('server', 'app', 'takes.py')
    assert 'handheld' not in page and 'held still on a tripod, with no shake, no zoom and no pan' in page


def test_the_helpers_are_not_told_of_a_drift():
    for parts in (('plugin', 'skills', 'guide', 'SKILL.md'), ('plugin', 'agents', 'vw-guide-check.md')):
        text = read(*parts)
        assert 'handheld' not in text and 'small drift' not in text and 'shifts by a few pixels' not in text, parts


def test_the_open_overlays_step_is_said_in_one_line_and_nothing_once_it_is_settled():
    store = Store()
    line = S.first_line(store, RUN)
    assert line.startswith("First the text overlays, the last step of visuals, before the editor's package:") and '`vw overlays start`' in line
    session = S.session_of(store, RUN)
    assert S.answer(store, RUN, session, {'answer': 'none'}, FILM) == []
    assert S.first_line(store, RUN) is None


def test_next_names_the_overlays_step_when_the_assembly_is_next(monkeypatch):
    from app import storage
    store = Store()
    monkeypatch.setattr(storage, 'storage', lambda: store)
    monkeypatch.setattr(core, 'current_outputs', lambda conn, rid: [])
    monkeypatch.setattr(core, 'attempts_for', lambda conn, rid: {})
    monkeypatch.setattr(core, 'open_defect_rows', lambda conn, rid: [])
    monkeypatch.setattr(core, 'stage_table', lambda v: [])
    for stage, said in (('assembly', True), ('visuals', False), ('delivery', False)):
        monkeypatch.setattr(core, 'compute_next', lambda *a, stage=stage: {'stage': stage})
        nxt = core.next_for(None, {**RUN, 'procedure_version': 'v3'})
        assert ('`vw overlays start`' in (nxt.get('do_first') or '')) is said, stage
