"""Release 1 of 27 Nov 2026, phase 1, part A (SK approved, question 6): once the operator's answer is recorded, a refusal raised while the next
card is fetched does not refuse the request. Before: the request failed, the database part of the answer (the jobs it queued) was rolled back,
and the run's record in storage, already saved, still said the answer was given (VW-25: shot S01-1 "being made" for 28 hours with no job).
The reply says the answer is recorded, gives the refusal's own words and names `vw visuals next`; the run's log gets a line. A refusal of the
answer itself records nothing, as before. Each test failed first. Without a database."""
import pytest

from app import chat_flow as CF, visuals_stage as V
from app.errors import Problem
from test_design151_refs_pure import NEW
from test_guide_route_pure import refused, take_film   # noqa: F401 (take_film: the fixture)
from test_rel3b_critic_pure import item, still_to_answer, videos, with_a_still
from test_visuals_stage_pure import USER, saved

WORDS = 'No reference round is waiting for its sets.'


def breaks(monkeypatch, exc):
    monkeypatch.setattr(CF, 'next_item', lambda *a, **k: (_ for _ in ()).throw(exc))


@pytest.mark.parametrize('exc', [ValueError(WORDS), Problem(422, 'VISUALS_CONTRACT', WORDS)])
def test_the_answer_and_its_paid_job_stay_when_the_next_card_is_refused(take_film, monkeypatch, exc):
    store, conn = still_to_answer(take_film)   # phase 4 part B: the paid answer is "Approve and shoot"
    sid = item(store, conn, 'still:VS1')
    breaks(monkeypatch, exc)
    out = CF.answer(conn, store, USER, NEW, [], sid, 'approve', 'Yes, shoot it.')
    assert len(videos(conn)) == 1                                           # the take is ordered: nothing is rolled back
    assert out['answered'] == sid and out['next_refused'] == WORDS and not out.get('item')
    assert 'chat_item' not in saved(store)                                  # the card is spent
    assert 'The answer is recorded.' in out['then'] and WORDS in out['then'] and '`vw visuals next`' in out['then']
    assert 'show it now' not in out['then']                                 # nothing was handed out


def test_the_runs_log_line_names_the_refusal(take_film, monkeypatch):
    store, conn = still_to_answer(take_film)   # phase 4 part B: the paid answer is "Approve and shoot"
    sid = item(store, conn, 'still:VS1')
    breaks(monkeypatch, ValueError(WORDS))
    line = CF.logged(CF.answer(conn, store, USER, NEW, [], sid, 'approve', 'Yes, shoot it.'))['log']
    assert line == f'answer recorded; the next card was refused: {WORDS}'


def test_a_refusal_of_the_answer_itself_still_records_nothing(take_film, monkeypatch):
    store, conn = with_a_still(take_film)
    sid = item(store, conn, 'still:VS1')
    breaks(monkeypatch, ValueError(WORDS))
    assert 'Not an answer to this item' in refused(lambda: CF.answer(conn, store, USER, NEW, [], sid, 'no-such-choice', 'x'))
    assert saved(store)['guides']['VS1']['stills'][0]['status'] == 'candidate' and saved(store).get('chat_item')


def test_an_unexpected_error_is_not_swallowed(take_film, monkeypatch):
    """Only a refusal written for a person (a ValueError or a Problem) is turned into a line; anything else fails the request as before."""
    store, conn = still_to_answer(take_film)   # phase 4 part B: the paid answer is "Approve and shoot"
    sid = item(store, conn, 'still:VS1')
    breaks(monkeypatch, KeyError('plan'))
    with pytest.raises(KeyError):
        CF.answer(conn, store, USER, NEW, [], sid, 'approve', 'Yes, shoot it.')


def test_the_card_recorder_keeps_its_answers_too(monkeypatch):
    """`card_answer` fetches the next card through the same function, so one fix covers both (the source is read: a card needs a treatment film)."""
    import inspect
    for fn in (CF.answer, CF.card_answer):
        src = inspect.getsource(fn)
        assert '_next_after(' in src and 'nxt = next_item(' not in src, fn.__name__
