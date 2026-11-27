"""SK, 23 Nov 2026 (no-footage release 1b): the media step and the shape of a film with no camera footage of its own.
The shape is asked plainly (there is no clip to count), and it is fixed once the first cut is recorded: before this, a film with no analysis
job could change shape at any time (study finding B3)."""
import json
from pathlib import Path

import pytest

from app import core, film
from app.errors import Problem

SERVER = Path(__file__).resolve().parents[1]
MEDIA = next(s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'media')
NONE = {'id': 'r1', 'status': 'open', 'film': {'footage': {'value': 'none'}}}
CLIP_WORDS = ('camera sound', '--camera-audio', '--copies', '--shot-on', 'originals', 'upload', 'runs/<code>/in/', 'counts the horizontal', 'the clips', 'clip count', 'per clip', 'each clip')


def test_a_film_with_no_footage_reads_a_media_step_with_no_clip_in_it():
    text = json.dumps(core.for_footage(MEDIA, 'none'), ensure_ascii=False).lower()
    assert [w for w in CLIP_WORDS if w.lower() in text] == []
    steps = core.for_footage(MEDIA, 'none')['steps']
    assert len(steps) == 2 and '`vw shape' in steps[0] and '--fps' in steps[0] and '`vw stage media record --quote' in steps[1]
    assert 'never ask' in ' '.join(steps).lower() and 'visuals' in ' '.join(steps)   # the operator's photographs wait for the visuals step


def test_the_shape_is_asked_without_a_clip_count():
    assert film.recommend([], 'none') == {'counts': {'horizontal': 0, 'vertical': 0, 'square': 0}, 'shape': None, 'fps_counts': {}, 'fps': 25,
                                          'note': film.NO_FOOTAGE_SHAPE}
    assert film.recommend([])['fps'] is None and 'note' not in film.recommend([])   # a film with footage: as before
    with pytest.raises(Problem) as e:
        film.timeline(NONE)
    assert e.value.code == 'FILM_SHAPE' and 'clip count' not in e.value.message and '`vw shape' in e.value.message
    with pytest.raises(Problem) as e:
        film.timeline({'film': {}})
    assert 'clip count' in e.value.message


class Conn:
    def __init__(self, jobs=False, first_cut=False):
        self.jobs, self.first_cut = jobs, first_cut

    def execute(self, sql, args=None):
        conn = self

        class R:
            def fetchone(self):
                if 'vw2_jobs' in sql:
                    return {'x': 1} if conn.jobs else None
                if 'vw2_stage_outputs' in sql:
                    assert "'master'" in sql and 'not stale' in sql
                    return {'x': 1} if conn.first_cut else None
                return {'film': {'shape': args[1].obj}}
        return R()


def test_the_shape_is_fixed_once_the_first_cut_is_recorded():
    user = {'id': 'u1'}
    out = film.record(Conn(), user, NONE, 'shape', 'vertical', 'vertical please', 'vertical', 25)
    assert out['shape']['value'] == 'vertical'
    with pytest.raises(Problem) as e:
        film.record(Conn(first_cut=True), user, NONE, 'shape', 'horizontal', 'changed my mind', 'horizontal', 25)
    assert e.value.code == 'FILM_LOCKED' and 'first cut' in e.value.message
    with pytest.raises(Problem) as e:   # a film with footage: the analysis fixes it first, as before
        film.record(Conn(jobs=True), user, {'id': 'r2', 'status': 'open', 'film': {}}, 'shape', 'horizontal', 'x', 'horizontal', 25)
    assert e.value.code == 'FILM_LOCKED' and 'analysis' in e.value.message


def test_the_same_answer_again_is_not_a_change_and_is_never_refused():
    """Sweep of 27 Nov 2026, intake finding 3: the intake record passes the category every time; once the visuals stage had started the same
    category again was refused ("cannot change now"), so the intake of such a film could not be recorded again."""
    user = {'id': 'u1'}
    run = {'id': 'r3', 'status': 'open', 'film': {'category': {'value': 'documentary-explainer', 'quote': 'first words', 'by': 'Asha', 'at': 't0'},
                                                 'shape': {'value': 'vertical', 'video': 'vertical', 'fps': 25, 'quote': 'q', 'by': 'Asha', 'at': 't0'}}}
    assert film.record(Conn(jobs=True), user, run, 'category', 'documentary-explainer', 'the same as before') == run['film']   # nothing written: the first words stand
    assert film.record(Conn(jobs=True, first_cut=True), user, run, 'shape', 'vertical', 'same', 'vertical', 25) == run['film']
    with pytest.raises(Problem) as e:   # another value is still a change
        film.record(Conn(jobs=True), user, run, 'category', 'advertisement-product', 'changed my mind')
    assert e.value.code == 'FILM_LOCKED'
    with pytest.raises(Problem) as e:   # one part of the shape changed
        film.record(Conn(jobs=True), user, run, 'shape', 'vertical', 'x', 'vertical', 30)
    assert e.value.code == 'FILM_LOCKED'
