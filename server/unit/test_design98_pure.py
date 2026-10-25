"""design/98: the options approved by the first answer (A), a reject without a reason (B), the final narration by its click (C)."""
import json
from pathlib import Path

import pytest

from app import core, voices
from app.errors import Problem
from app.stage2 import stage as S
from test_review_page import FakeConn, FakeStore, RUN, SLIDES, files, session

APP = Path(__file__).resolve().parents[1] / 'app'
USER = {'id': 'u1', 'name': 'SK'}
FILM = {'status': 'ready', 'digest': 'd1', 'version': 1, 'job_id': 'j1', 'result': {'key': 'run-1/stage2/review-v1-d1.mp4', 'sha256': 'f', 'bytes': 10, 'duration_s': 60.0}}


@pytest.fixture
def recorded(monkeypatch):
    """The database side of record_options, faked: the output row and the file receipts."""
    rows = []
    monkeypatch.setattr(S, '_refresh', lambda conn, store, run, session: None)
    monkeypatch.setattr(S, '_same_package', lambda store, session, entry: None)
    monkeypatch.setattr(S.jobs, 'record_file', lambda *a, **k: None)
    monkeypatch.setattr(S.core, 'output', lambda conn, user, run, body: rows.append(body) or {'id': f'o{len(rows)}'})
    return rows


def at_options(**over):
    sess = session(renders={'review': dict(FILM)}, **over)
    sess['package'] = {'key': 'p', 'digest': 'pk1', 'narration_key': 'n', 'sha256': 'p', 'bytes': 1}
    sess['versions'][0]['file'] = {'key': 'run-1/stage2/options-v1.json', 'sha256': 'o', 'bytes': 1}
    sess['versions'][0]['options'] = 3
    return FakeStore(files(sess, with_plan=False))


def saved(store):
    return json.loads(store.files['run-1/stage2/session.json'])


# ---------- A: the first answer approves the options ----------

def test_the_first_answer_records_the_options_and_the_answer_in_one_call(recorded):
    store = at_options()
    out = S.decide(FakeConn({}), store, USER, RUN, '1', 'KEEP', '', None)
    s = saved(store)
    assert out['action'] == 'KEEP' and s['decisions']['1']['action'] == 'KEEP'
    assert len(recorded) == 1 and recorded[0]['stage'] == 'options'
    assert recorded[0]['accepted_quote'] == 'Approved by answering the review slides: first answer #1 KEEP'
    assert recorded[0]['summary']['approved_by'] == {'how': 'first_answer', 'slide': '1'}
    assert s['accepted']['digest'] == 'd1' and s['accepted']['approved_by']['slide'] == '1'
    S.decide(FakeConn({}), store, USER, RUN, '2', 'REJECT', 'too dark', None)
    assert len(recorded) == 1   # a second answer does not record the options again


def test_the_first_answers_note_goes_into_the_approval(recorded):
    store = at_options()
    S.decide(FakeConn({}), store, USER, RUN, '2', 'REJECT', 'the first cut is better', None)
    assert recorded[0]['accepted_quote'] == 'Approved by answering the review slides: first answer #2 REJECT — the first cut is better'


def test_no_answer_before_the_review_film_and_a_bad_answer_approves_nothing(recorded):
    sess = session()
    with pytest.raises(Problem, match='not rendered yet'):
        S.decide(FakeConn({}), FakeStore(files(sess, with_plan=False)), USER, RUN, '1', 'KEEP', '', None)
    store = at_options()
    with pytest.raises(Problem, match='No slide #9'):
        S.decide(FakeConn({}), store, USER, RUN, '9', 'KEEP', '', None)
    with pytest.raises(Problem, match='KEEP or DROP'):
        S.decide(FakeConn({}), store, USER, RUN, '1A', 'REJECT', '', None)
    assert recorded == [] and saved(store)['accepted'] is None


def test_an_explicit_approval_still_works_and_then_answers_do_not_record_again(recorded):
    store = at_options()
    S.record_options(FakeConn({}), store, USER, RUN, 'Yes, these options.')
    assert recorded[0]['accepted_quote'] == 'Yes, these options.' and 'approved_by' not in recorded[0]['summary']
    S.decide(FakeConn({}), store, USER, RUN, '1', 'KEEP', '', None)
    assert len(recorded) == 1


# ---------- B: a reject without a reason ----------

def test_a_reject_records_with_or_without_a_reason(recorded):
    store = FakeStore(files(session(accepted={'version': 1, 'digest': 'd1'}), with_plan=False))
    assert S.decide(FakeConn({}), store, USER, RUN, '2', 'REJECT', '', None)['action'] == 'REJECT'
    assert saved(store)['decisions']['2']['note'] == ''
    S.decide(FakeConn({}), store, USER, RUN, '2', 'REJECT', 'weaker', None)
    assert saved(store)['decisions']['2']['note'] == 'weaker'


# ---------- C: the final narration by its click ----------

def test_the_final_narration_needs_no_words(monkeypatch):
    bodies = []
    job = {'id': 'j9', 'status': 'ready', 'cost': None, 'request': {'kind': 'narration', 'voice_id': 'v1', 'name': 'Shardul K', 'model_id': 'm', 'settings': {}, 'source_script': 'sc1'},
           'result': {'audio_key': 'a.mp3', 'sha256': 'a', 'bytes': 1, 'timing_key': 't.json', 'timing_sha256': 't', 'timing_bytes': 1, 'duration_s': 58.0}}

    class Conn:
        def execute(self, sql, params=()):
            return type('R', (), {'fetchone': lambda _s: job})()
    monkeypatch.setattr(voices, 'script_text', lambda store, outputs: ({}, {'summary': {'content_digest': 'sc1'}}))
    monkeypatch.setattr(voices, 'beat_rows', lambda script, timing: [])
    monkeypatch.setattr(voices, 'direction_of', lambda store, run: None)
    monkeypatch.setattr(voices, 'page_state', lambda store, run: {'narrations': []})
    monkeypatch.setattr(voices, 'save_doc', lambda store, run, name, doc: None)
    monkeypatch.setattr(core, 'output', lambda conn, user, run, body: bodies.append(body) or {'id': 'o1'})
    store = FakeStore({'t.json': {}})
    voices.finalise(Conn(), store, USER, RUN, [], 'j9', '', 'page')
    assert bodies[-1]['accepted_quote'] == 'Made final on the voices page by SK'
    voices.finalise(Conn(), store, USER, RUN, [], 'j9', 'This one, the warm one.', 'page')
    assert bodies[-1]['accepted_quote'] == 'This one, the warm one.'


def test_a_final_narration_recorded_in_chat_without_words_says_so():
    assert core.acceptance_quote('voice', '', USER) == 'Chosen as final in chat by SK'
    assert core.acceptance_quote('voice', 'the second one', USER) == 'the second one'
    assert core.acceptance_quote('brief', '', USER) == ''   # every other stage still needs the operator's words


# ---------- the pages ----------

REVIEW = (APP / 'templates' / 'review.html').read_text(encoding='utf-8')
VOICES = (APP / 'templates' / 'voices2.html').read_text(encoding='utf-8')


def test_the_review_page_answers_without_an_approval_box_and_the_reason_is_optional():
    assert 'Approve these options with your own words' not in REVIEW and 'do-record' not in REVIEW
    assert 'your first answer approves these options' in REVIEW and 'Why? (optional)' in REVIEW and 'A reason is required' not in REVIEW
    assert 'Options approved by your first answer' in REVIEW


def test_the_voices_page_sends_the_operator_back_to_the_chat_and_the_pick_is_clear():
    assert 'Done here. Go back to the Claude chat to continue.' in VOICES and 'what is next for ' in VOICES and 'data-copy=' in VOICES
    assert 'Pick the narration you want as final (click its row)' in VOICES and '>Pick one<' in VOICES
    assert 'your words (required)' not in VOICES and 'tr.pick' in VOICES
