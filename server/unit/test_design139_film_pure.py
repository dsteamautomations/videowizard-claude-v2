"""design/137 and design/139 R1: the film's category, shape, AI video shape and frame rate, chosen by the operator with their words; never assumed for a
new film; a film made before design/139 (film NULL) keeps 16:9 at 25 and the documentary guidebooks."""
import pytest

from app import film as F
from app.errors import Problem

OLD = {'id': 'r0', 'film': None}
NEW = {'id': 'r1', 'film': {}}


def clip(w, h, fps=25, rot=0, name='c'):
    return {'id': name, 'name': name, 'width': w, 'height': h, 'fps': fps, 'rotation_deg': rot}


def test_older_film_keeps_what_it_was_made_with():
    assert F.frame(OLD) == '16:9' and F.frame(OLD, video=True) == '16:9' and F.fps(OLD) == 25
    assert F.category(OLD) == 'documentary-explainer'
    assert F.timeline(OLD) == {'width': 1920, 'height': 1080, 'fps': 25, 'aspect_ratio': '16:9'}


def test_new_film_is_never_assumed():
    assert F.frame(NEW) is None and F.fps(NEW) is None and F.category(NEW) is None
    with pytest.raises(Problem) as e:
        F.timeline(NEW)
    assert 'vw shape' in e.value.message


def test_vertical_film_with_horizontal_ai_video():
    run = {'film': {'shape': {'value': 'vertical', 'video': 'horizontal', 'fps': 30}}}
    assert F.frame(run) == '9:16' and F.frame(run, video=True) == '16:9' and F.fps(run) == 30
    assert F.timeline(run) == {'width': 1080, 'height': 1920, 'fps': 30, 'aspect_ratio': '9:16'}


def test_shape_count_recommends_the_majority():
    r = F.recommend([clip(1920, 1080, name=f'h{i}') for i in range(3)] + [clip(1080, 1920, name='v')])
    assert r['counts'] == {'horizontal': 3, 'vertical': 1, 'square': 0} and r['shape'] == 'horizontal' and r['fps'] == 25


def test_rotated_phone_clip_counts_as_seen():
    r = F.recommend([clip(1920, 1080, rot=90), clip(1920, 1080, rot=-90, name='b')])
    assert r['shape'] == 'vertical'


def test_tie_and_no_clips_give_no_recommendation():
    assert F.recommend([clip(1920, 1080), clip(1080, 1920, name='v')])['shape'] is None
    assert F.recommend([])['shape'] is None and F.recommend([])['fps'] is None


def test_square_clips_vote_for_neither():
    r = F.recommend([clip(1080, 1080), clip(1920, 1080, name='h')])
    assert r['counts']['square'] == 1 and r['shape'] == 'horizontal'


def test_ntsc_rates_round_to_whole():
    assert F.rate_of(29.97) == 30 and F.rate_of('30000/1001') == 30 and F.rate_of(23.976) == 24 and F.rate_of(59.94) == 60 and F.rate_of(25) == 25
    r = F.recommend([clip(1920, 1080, fps=29.97), clip(1920, 1080, fps=29.97, name='b'), clip(1920, 1080, fps=25, name='c')])
    assert r['fps'] == 30 and r['fps_counts'] == {30: 2, 25: 1}


def test_choice_checks():
    assert F.check('shape', 'vertical', video='horizontal', fps=30) == {'value': 'vertical', 'video': 'horizontal', 'fps': 30}
    for bad in ('1:1', '4:5', 'square'):
        with pytest.raises(Problem) as e:
            F.check('shape', bad, video='horizontal', fps=25)
        assert 'future update' in e.value.message
    with pytest.raises(Problem):
        F.check('shape', 'vertical', video=None, fps=25)
    with pytest.raises(Problem):
        F.check('shape', 'vertical', video='vertical', fps=29)
    assert F.check('category', 'training-education') == {'value': 'training-education'}
    with pytest.raises(Problem) as e:
        F.check('category', 'documentary')
    assert 'advertisement-product' in e.value.message


def test_locks():
    assert F.locked_by('category') == 'visuals' and F.locked_by('shape') == 'analysis'


def test_pictures_and_takes_follow_their_shape():   # design/139 R1
    from app import visuals_stage as VS
    run = {'film': {'shape': {'value': 'vertical', 'video': 'horizontal', 'fps': 25}}}
    brief = [{'stage': 'brief', 'unit': None, 'summary': {'production': {'format': {'frame': '9:16'}}}}]
    assert VS.aspect_of(run, [], 'take') == '16:9' and VS.aspect_of(run, [], 'keyframe') == '16:9' and VS.aspect_of(run, [], 'sheet') == '9:16'
    assert VS.aspect_of(run, [], 'take', {'aspect_ratio': '9:16'}) == '9:16'   # said on the request
    old = {'film': None}
    assert VS.aspect_of(old, brief, 'take', {'aspect_ratio': None}) == '16:9' and VS.aspect_of(old, brief, 'sheet') == '9:16'   # a film from before reads as it did
