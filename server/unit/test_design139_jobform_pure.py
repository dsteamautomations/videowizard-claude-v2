"""design/139 R14 (SK, 2 Nov 2026, design/138 C19): the job form's industry is read from the client card or the brief, never "other" for a new film;
R1: a still or graphic takes the film's shape, a take the AI video shape; a film from before keeps its brief's frame and the old fallbacks."""
import pytest

from app import library as L
from app.errors import Problem
from test_library import GAP, PLAN, REFS, SCENE, SHOT

NEW = {'id': 'run-2', 'code': 'VW-20', 'client_id': 'X', 'image_provider': 'openai',
       'film': {'shape': {'value': 'vertical', 'video': 'horizontal', 'fps': 30}, 'category': {'value': 'training-education'}}}
OLD = {'id': 'run-1', 'code': 'VW-13', 'client_id': 'X', 'image_provider': 'openai'}


def form(step, run, brief, card):
    return L.job_form(step, run=run, plan=PLAN, gap=GAP, scene=SCENE, shot=SHOT, refs=REFS, generator=None, brief=brief, card=card, rules=[], fps=30)


def test_a_new_film_reads_industry_from_the_brief_and_its_shapes_from_the_record():
    f = form('start', NEW, {'audience': 'masons', 'production': {'industry': 'construction'}}, {})
    assert f['industry'] == 'construction' and f['audience'] == 'masons'
    assert f['placement'] == '16:9' and f['video_aspect'] == '16:9'   # a start picture is the take's first frame: the AI video shape
    s = form('still-scene', NEW, {'audience': 'masons', 'production': {'industry': 'construction'}}, {})
    assert s['placement'] == '9:16' and s['video_aspect'] == '16:9'   # a still sits in the film


def test_the_card_industry_wins():
    assert form('start', NEW, {'audience': 'a', 'production': {'industry': 'x'}}, {'industry': 'cement'})['industry'] == 'cement'


def test_a_new_film_without_an_industry_is_refused():
    with pytest.raises(Problem) as e:
        form('start', NEW, {'audience': 'a', 'production': {}}, {})
    assert 'industry' in e.value.message


def test_an_older_film_keeps_its_fallbacks_and_its_brief_frame():
    f = form('start', OLD, None, None)
    assert f['industry'] == 'other' and f['audience'] == 'general' and f['placement'] == '16:9'
    assert form('start', OLD, {'audience': 'a', 'production': {'format': {'frame': '9:16'}}}, None)['placement'] == '9:16'
