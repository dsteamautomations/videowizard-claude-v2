"""SK, 23 Nov 2026: a film with no camera footage of its own (design/_work/no-footage-design-and-build-plan-23-nov.md, release 1a).
The footage answer is a film choice asked with the title; the instruction text is one text with marks, filtered by the server for each run:
a line that starts `[footage]` is read only by a film with camera footage, a line that starts `[no footage]` only by a film without, and a
line with no mark by every film. A film with footage (and every film from before) reads exactly what it read before."""
import json
from pathlib import Path

import pytest

from app import core, film
from app.errors import Problem

SERVER = Path(__file__).resolve().parents[1]
STAGES = json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']
NONE = {'film': {'footage': {'value': 'none'}}}
OWN = {'film': {'footage': {'value': 'own'}}}
TAGGED = ('intake', 'brief')   # the stages whose no-footage text is written so far; each release adds its own
CLIP_WORDS = ('camera sound', '--copies', '--shot-on', '`vw shape` (the clip', 'vw library show', 'find footage', '--originals', 'relink', 'stabil',
              'vw visuals footage', 'continues_footage', 'what the footage will show', 'what its footage will show', 'seen on camera', 'footage languages',
              'after the clips are listed')


# ---------- the filter ----------

def test_a_line_is_read_by_its_own_kind_of_film_and_the_mark_is_never_shown():
    text = 'Every film.\n[footage] List the clips.\n[no footage] Ask the shape.\nRecord.'
    assert core.for_footage(text, 'own') == 'Every film.\nList the clips.\nRecord.'
    assert core.for_footage(text, 'none') == 'Every film.\nAsk the shape.\nRecord.'


def test_text_with_no_mark_is_returned_as_it_is():
    text = 'One.\n\n  Two, indented.\nThree [footage] inside a line is not a mark.\n'
    assert core.for_footage(text, 'own') == text and core.for_footage(text, 'none') == text


def test_a_step_with_nothing_left_is_dropped_and_parts_are_filtered_too():
    stage = {'name': 'x', 'needs_acceptance': True, 'cap': 3, 'prompt': 'P.\n[footage] clips.', 'steps': ['[footage] one', 'two\n[no footage] two b', '[no footage] three'],
             'parts': {'plan': 'A.\n[no footage] B.', 'list': ['[footage] c', 'd']}}
    own, none = core.for_footage(stage, 'own'), core.for_footage(stage, 'none')
    assert own['steps'] == ['one', 'two\n'] and none['steps'] == ['two\ntwo b', 'three']
    assert own['parts'] == {'plan': 'A.\n', 'list': ['c', 'd']} and none['parts'] == {'plan': 'A.\nB.', 'list': ['d']}
    assert own['prompt'] == 'P.\nclips.' and none['prompt'] == 'P.\n'
    assert own['needs_acceptance'] is True and none['cap'] == 3 and stage['steps'][0] == '[footage] one'   # flags kept; the stored text is not changed


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        core.for_footage('x', 'some')


# ---------- the stage a reader is given ----------

def test_every_reader_of_a_stage_gets_no_mark_and_a_film_from_before_reads_as_a_film_with_footage():
    for st in STAGES:
        for kind in ('own', 'none'):
            assert '[footage]' not in json.dumps(core.for_footage(st, kind)) and '[no footage]' not in json.dumps(core.for_footage(st, kind)), (st['name'], kind)
        assert core._stage(STAGES, st['name']) == core.for_footage(st, 'own')
    assert film.footage({}) == 'own' and film.footage({'film': None}) == 'own' and film.footage({'film': {'category': {'value': 'social-ugc'}}}) == 'own'
    assert film.footage(NONE) == 'none' and film.footage(OWN) == 'own'


def test_the_stage_of_a_run_follows_its_footage_answer(monkeypatch):
    monkeypatch.setattr(core, 'stage_table', lambda version: STAGES)
    for name in TAGGED:
        own = core.procedure_for({'procedure_version': '3', **OWN}, name)
        none = core.procedure_for({'procedure_version': '3', **NONE}, name)
        assert own == core._stage(STAGES, name) and (none != own) == (name != 'intake'), name   # intake is read before the answer exists: one text


@pytest.mark.parametrize('name', TAGGED)
def test_a_film_with_no_footage_is_never_shown_a_step_about_clips(name):
    text = json.dumps(core.for_footage(next(s for s in STAGES if s['name'] == name), 'none'), ensure_ascii=False).lower()
    assert [w for w in CLIP_WORDS if w.lower() in text] == []


def test_the_first_question_asks_for_the_footage_and_the_record_carries_it():
    intake = next(s for s in STAGES if s['name'] == 'intake')
    for kind in ('own', 'none'):   # the answer is not known yet when intake is read: both kinds read the same intake
        steps = ' '.join(core.for_footage(intake, kind)['steps'])
        assert 'camera footage of its own' in steps and '--footage' in steps and 'in four parts' in steps


# ---------- the choice ----------

def test_the_footage_answer_is_own_or_none():
    assert film.check('footage', 'none') == {'value': 'none'} and film.check('footage', 'own') == {'value': 'own'}
    for bad in ('', 'yes', 'photos', None):
        with pytest.raises(Problem) as e:
            film.check('footage', bad)
        assert e.value.code == 'FILM_CHOICE' and 'own' in e.value.message and 'none' in e.value.message


class Conn:
    def __init__(self, media_recorded):
        self.media, self.sql = media_recorded, []

    def execute(self, sql, args=None):
        self.sql.append(' '.join(sql.split()))
        conn = self

        class R:
            def fetchone(self):
                if 'vw2_stage_outputs' in sql:
                    return {'x': 1} if conn.media else None
                if 'update vw2_runs' in sql:
                    return {'film': {'footage': args[1].obj}}
                return None
        return R()


def test_the_answer_is_recorded_with_the_operators_words_and_fixed_once_the_media_step_is_recorded():
    run = {'id': 'r1', 'status': 'open', 'film': {}}
    out = film.record(Conn(False), {'id': 'u1', 'name': 'Asha'}, run, 'footage', 'none', 'no, nothing was shot')
    assert out['footage']['value'] == 'none' and out['footage']['quote'] == 'no, nothing was shot'
    with pytest.raises(Problem) as e:
        film.record(Conn(False), {'id': 'u1'}, run, 'footage', 'none', '  ')
    assert e.value.code == 'FILM_CHOICE'
    with pytest.raises(Problem) as e:
        film.record(Conn(True), {'id': 'u1'}, run, 'footage', 'own', 'we do have clips')
    assert e.value.code == 'FILM_LOCKED' and 'media' in e.value.message
