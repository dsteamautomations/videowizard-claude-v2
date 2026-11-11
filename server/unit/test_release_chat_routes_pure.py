"""design/177: the visuals page's new actions reach the chat tool. Each new server function has its API route in main.py behind the same
guard as its neighbours (`_visuals_call`: sign-in, the run's lock, the visuals stage, one receipt per request), read from main.py as the
handover test does; and an unexpected error in a visuals route reaches the chat tool as the page's plain sentence, never as a bare key name."""
import re
from pathlib import Path

import pytest

from app import visuals_stage as VS
from app.errors import Problem

SRC = (Path(__file__).resolve().parents[1] / 'app' / 'main.py').read_text(encoding='utf-8')

ROUTES = [   # (path under /api/runs/{run_id}/visuals, the route's function, the server function it calls with)
    ('/round/answer', 'visuals_round_answer', 'set_answer(storage(), user, run, outputs, body.element_id, body.verdict, body.golden, body.words)'),
    ('/round/make', 'visuals_round_make', 'set_make(conn, storage(), user, run, outputs, body.element_id)'),
    ('/round/aside', 'visuals_round_aside', 'set_aside(storage(), user, run, outputs, body.element_id, body.words, body.back)'),
    ('/references/{ref_id}/reapprove', 'visuals_reapprove', 'reapprove_reference(storage(), user, run, outputs, ref_id, body.sha256, body.quote, conn)'),
    ('/own', 'visuals_own', 'supply_own(conn, storage(), user, run, outputs, body.element_id,'),
]


@pytest.mark.parametrize('path,fn,call', ROUTES)
def test_each_new_page_action_has_its_api_route_behind_the_visuals_guard(path, fn, call):
    m = re.search(r"@app\.post\('/api/runs/\{run_id\}/visuals%s'[^\n]*\)\ndef %s\(run_id: UUID, (?:ref_id: str, )?body: \w+, user=User, conn=DB\):[^\n]*\n((?:    [^\n]*\n)+)" % (re.escape(path), fn), SRC)
    assert m, path
    assert 'return _visuals_call(conn, user, run_id, body, lambda run, outputs: visuals_stage.' + call in m.group(1), path


def test_the_step_2_answer_takes_only_the_three_verdicts_and_the_reapproval_the_exact_picture():
    assert re.search(r"class RoundAnswer\(Write\):[^\n]*\n    element_id: str\n    verdict: Literal\['yes', 'no', 'correct'\] \| None = None\n", SRC)
    assert re.search(r"def visuals_reapprove\(run_id: UUID, ref_id: str, body: ReferenceApprove,", SRC)   # the sha256 of the picture seen, as an approval


def test_an_unexpected_error_in_a_visuals_route_reaches_the_chat_tool_as_the_plain_sentence(caplog):
    from app import web

    def boom():
        raise KeyError('request_key')
    with pytest.raises(Problem) as e:
        VS.guarded(boom)
    assert e.value.message == web.PAGE_FAILED == 'That could not be done; nothing was changed. The builder has been told what failed.'
    assert e.value.status == 500 and 'request_key' not in e.value.message and 'request_key' in caplog.text   # the real text goes to the server log
    for exc in (TypeError("'NoneType' object is not subscriptable"), ZeroDivisionError('division by zero')):
        with pytest.raises(Problem) as e:
            VS.guarded(lambda: (_ for _ in ()).throw(exc))
        assert e.value.message == web.PAGE_FAILED
    with pytest.raises(Problem, match='P1: say what to correct') as e:   # a refusal written for the operator still arrives as written
        VS.guarded(lambda: VS.need(False, 'P1: say what to correct.'))
    assert e.value.status == 422 and e.value.code == 'VISUALS_CONTRACT'
    with pytest.raises(Problem) as e:   # a refusal raised as a Problem passes through unchanged
        VS.guarded(lambda: (_ for _ in ()).throw(Problem(409, 'REFERENCE_MISMATCH', 'Approve the exact stored image hash after viewing it.')))
    assert e.value.status == 409
    assert VS.guarded(lambda: {'done': True}) == {'done': True}
    assert "visuals_stage.guarded(lambda: fn(run, outputs))" in SRC   # the one place every visuals write route goes through
