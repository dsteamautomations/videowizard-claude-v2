"""Release 1, C5 (SK, 20 Nov 2026, answer 11: "Not now; say so plainly"): vertical AI video is not built. An AI video shot on a film whose
shape, or whose AI video shape, is vertical is refused when the plan is checked and when it is proposed, with one plain sentence that
says what the operator can do; a vertical film with no AI video shot is refused nothing. Step 7 itself (the first step of a shot: its
scene description) refuses with the same sentence, before anything is rendered or paid, should such a plan have slipped through.
Without a database."""
import pytest

from app import guide as GD, visuals_stage as V
from test_design151_refs_pure import NEW
from test_guide_route_pure import refused, scene, spec10, take_film   # noqa: F401 (take_film: the fixture)
from test_visuals_stage_pure import USER

VERTICAL = {**NEW, 'film': {'shape': {'value': 'vertical', 'video': 'horizontal', 'fps': 25}}}
VIDEO_VERTICAL = {**NEW, 'film': {'shape': {'value': 'horizontal', 'video': 'vertical', 'fps': 25}}}
OLDER = {**NEW, 'film': None}
UNSET = {**NEW, 'film': {}}


def plan(*kinds, choices=False):
    shots = [{'id': f'S{n}', 'visual_type': k} for n, k in enumerate(kinds, 1)]
    return {'gaps': [{'gap_id': 'G1', **({'choices': [{'choice_id': 'a', 'scenes': [{'id': 'sc', 'shots': shots}]}]} if choices else {'scenes': [{'id': 'sc', 'shots': shots}]})}]}


def test_an_ai_video_shot_on_a_vertical_film_is_named_with_what_the_operator_can_do():
    out = V.vertical_video(VERTICAL, plan('image', 'video', 'drawn', 'video'))
    assert out == ['S2, S4: AI video is not built for a vertical film yet: the video AI makes its takes in the horizontal shape only. '
                   'Make each of these shots a still, a drawn graphic or footage in the plan, then check the plan again.']
    one = V.vertical_video(VIDEO_VERTICAL, plan('video'))                                    # the AI video shape recorded as vertical: the same
    assert one == ['S1: AI video is not built for a vertical film yet: the video AI makes its takes in the horizontal shape only. '
                   'Make this shot a still, a drawn graphic or footage in the plan, then check the plan again.']
    assert V.vertical_video(VERTICAL, plan('image', 'video', choices=True))[0].startswith('S2: ')   # a shot inside one of a gap's two ways


def test_nothing_is_refused_without_an_ai_video_shot_or_on_a_horizontal_or_older_film():
    assert V.vertical_video(VERTICAL, plan('image', 'drawn', 'footage', 'animation')) == []   # a vertical film with no AI video shot
    assert V.vertical_video(NEW, plan('video')) == []                                         # horizontal
    assert V.vertical_video(OLDER, plan('video')) == [] and V.vertical_video(UNSET, plan('video')) == []   # a film from before the shape was recorded; a shape not recorded yet (asked elsewhere)


@pytest.fixture
def checked(monkeypatch):
    """The plan check and the proposal with everything before and after the vertical rule answered at once."""
    def use(p):
        monkeypatch.setattr(V, 'session_of', lambda *a, **k: {'source': {'gaps': {}, 'fps': 25}, 'treatment': {'gaps': []}})
        monkeypatch.setattr(V, 'ensure_timing', lambda *a, **k: None)
        monkeypatch.setattr(V, '_with_direction', lambda s, d: d)
        monkeypatch.setattr(V, 'validate_plan', lambda *a, **k: (p, []))
        monkeypatch.setattr(V, 'film_frames', lambda outputs: 0)
        monkeypatch.setattr(V, 'media_clips', lambda outputs: [])
        monkeypatch.setattr(V, '_ways_departed', lambda s, p_: pytest.fail('the vertical rule comes first'))
    return use


def test_the_plan_check_refuses_it_as_an_error_not_a_warning(checked):
    checked(plan('image', 'video'))
    out = V.check(None, VERTICAL, [], {})
    assert out['status'] == 'rejected' and out['errors'] == V.vertical_video(VERTICAL, plan('image', 'video')) and out['error'].startswith('S2: AI video is not built for a vertical film yet')


def test_the_proposal_refuses_it_too(checked):
    checked(plan('video'))
    with pytest.raises(Exception, match='S1: AI video is not built for a vertical film yet'):
        V.propose(None, None, USER, VERTICAL, [], {})


def test_step_7_refuses_the_scene_of_a_shot_on_a_vertical_film_before_anything_is_made(take_film):
    store, conn = take_film
    n = len(conn.queued)
    said = refused(lambda: GD.set_scene(conn, store, USER, VERTICAL, [], 'VS1', spec10()))
    assert said == V.vertical_video(VERTICAL, {'gaps': [{'gap_id': 'G', 'scenes': [{'id': 'sc', 'shots': [{'id': 'VS1', 'visual_type': 'video'}]}]}]})[0]   # the same sentence
    assert len(conn.queued) == n                                                              # nothing rendered, nothing paid
    assert scene(store, conn)                                                                 # the same shot on a horizontal film: taken as before
