"""Defect 70 (VW-26, 27 Nov 2026): the intake's footage answer was refused with 422. The tool (0.109.0) posts it to the film record as the key
`footage`; `film.record` takes that key; the request's own list of keys did not hold it, so every new film stopped at intake.
The test failed first. Without a database."""
import pytest
from pydantic import ValidationError

from app import film, main


@pytest.mark.parametrize('key', sorted(film.LOCKS))
def test_every_key_the_film_record_takes_is_accepted_by_the_request(key):
    assert main.FilmChoice(request_id='00000000-0000-0000-0000-000000000001', key=key, value='own', quote='Yes, it has camera footage').key == key


def test_an_unknown_key_is_still_refused():
    with pytest.raises(ValidationError):
        main.FilmChoice(request_id='00000000-0000-0000-0000-000000000001', key='anything', value='x', quote='x')
