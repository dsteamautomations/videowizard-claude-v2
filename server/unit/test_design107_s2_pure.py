"""design/107 slice 2 on the server: the final approval accepts the operator's side-by-side check of the timeline (free Resolve) as well as a Studio readback."""
from app.stage3 import delivery as D


def test_final_needs_the_timeline_to_have_matched_the_film_by_either_route():
    film = 'f' * 64
    assert D.verification_missing({'state': 'reported', 'film_sha256': film, 'report': {'drt_verified': True}}, film) == []
    assert D.verification_missing({'state': 'reported', 'film_sha256': film, 'report': {'route': 'free', 'timeline_verified': True}}, film) == []
    assert D.verification_missing({'state': 'reported', 'film_sha256': film, 'report': {'route': 'free', 'timeline_verified': False}}, film) == ['the timeline matched the film (the report says it did not)']
    assert D.verification_missing({'state': 'dispatched', 'film_sha256': film, 'report': {}}, film) == ['a report that the timeline matched this film']
    assert D.verification_missing({}, film) == ['a report that the timeline matched this film']
