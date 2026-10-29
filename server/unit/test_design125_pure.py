"""design/125, the review of the whole flow on VW-11: the server side and the version 3 wording.
I1-I3 intake wording; B2-B3 brief wording; S1-S3 script wording and the claims handed to visuals; V1 a repeated tag not sent, V2-V3 voice wording;
M2 media wording; A2 short clips in the plain mode; A3 analysis wording; A4 up to three automatic retries for a passing failure."""
import json
from pathlib import Path

import pytest

from app import analysis, analysis_jobs as AJ, voice_direction as VD, visuals_stage as VS

ROOT = Path(__file__).resolve().parents[1]
V2 = {s['name']: s for s in json.loads((ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8'))['stages']}
V3 = {s['name']: s for s in json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']}


def text_of(stage):
    s = V3[stage]
    return '\n'.join([s.get('prompt') or '', s.get('direction_prompt') or '', *(s.get('steps') or [])])


# ---------- wording, version 3 only ----------

def test_i1_i2_the_picture_ai_question_left_the_intake_and_its_details_live_in_the_pictures_part():
    intake = text_of('intake')
    assert '--images' not in intake and 'design/' not in intake and 'chroma' not in intake and 'Nano Banana' not in intake
    later = next(p for p in V3['visuals']['parts'] if p['name'] == 'later')['text']
    assert '6 of things, 5 of people, 3 of style' in later and later.count('6 of things, 5 of people, 3 of style') == 1
    assert 'chroma green' in later and 'said in words' in later
    assert 'Nano Banana' in '\n'.join(V2['intake']['steps'])   # version 2 untouched


def test_i3_the_prompts_example_answer_has_the_same_keys_as_the_answer_shape():
    example = V3['intake']['prompt'][V3['intake']['prompt'].rindex('{\n  "remove"'):]
    assert set(json.loads(example)) == set(V3['intake']['output_shape']) == {'remove', 'titles', 'notes'}


def test_b2_s1_v3_the_first_systems_leftovers_and_the_labels_are_gone():
    for stage, gone in (('brief', ['VW-BRIEF v2.0', 'at most one correction', 'model defaults']),
                        ('script', ['VW-SCRIPT-PREPARATION', 'at most one correction', 'filmability, lock', 'VO/DIALOGUE/ACTION']),
                        ('voice', ['VW-VOICE v4', 'VW-DIRECTION v1', 'design/54']),
                        ('media', ['design/107']),
                        ('analysis', ['clip-log-v1', 'blueprint Stage 1'])):
        t = text_of(stage)
        for g in gone:
            assert g not in t, (stage, g)
    assert 'at most one correction' in V2['brief']['prompt']   # version 2 untouched


def test_b3_one_list_of_what_to_ask_on_every_film_in_the_steps():
    step = V3['brief']['steps'][1]
    for words in ('brand and safety rules', 'languages spoken in the footage (an empty list if nobody speaks or there is no footage)', 'narration language',
                  'speaker may be seen on camera', 'frame shape', '16:9 and no destinations unless they say', 'watched muted'):
        assert words in step, words
    assert '16:9, 9:16, 1:1 or 4:5' in V3['brief']['prompt']


def test_s2_s3_the_tools_check_said_once_and_the_claims_asked_for():
    p = V3['script']['prompt']
    assert 'Verify the agreed changes are present' not in p and 'The tool checks that only the accepted changes are applied' in p
    assert 'anchor an insertion on a short before excerpt' in p
    assert '`claims`' in V3['script']['steps'][1] and 'claims' in V3['script']['output_shape']
    prep = next(p for p in V3['visuals']['parts'] if p['name'] == 'preparation')['text']
    assert 'claims.json' in prep


def test_v2_the_chat_path_written_once_with_the_tools_word_limits():
    p = V3['voice']['prompt']
    assert '45 to 70 words' not in p and '50 to 100 words' in p and '3,000 characters' in p
    assert 'gender; age group; accent' not in p   # the chat path's questions live in the steps only
    steps = '\n'.join(V3['voice']['steps'])
    assert 'gender; age group; accent (language and accent are different things' in steps and 'register (warm, authoritative' in steps and 'exactly those filters' in steps and 'add-library' in steps
    assert 'The register is placed at the top for you' in V3['voice']['direction_prompt']


def test_m2_the_media_facts_in_the_steps_only():
    assert 'Facts of the tool' not in V3['media']['prompt']
    steps = '\n'.join(V3['media']['steps'])
    assert '200 MB' in steps and 'three clips at a time' in steps and 'Re-run record to resume' in steps


def test_a2_short_clips_use_the_plain_mode_from_version_3():
    proc = V3['analysis']
    assert proc['settings']['processing_mode'] == 'auto' and proc['settings']['agentic_over_seconds'] == 15
    assert analysis.processing_mode(proc, 15.0) == 'STATIC' and analysis.processing_mode(proc, 15.1) == 'AGENTIC'
    assert V2['analysis']['settings']['processing_mode'] == 'AGENTIC'
    assert 'up to three times' in '\n'.join(proc['steps'])


# ---------- V1: a tag that repeats the one in force is not sent ----------

SCRIPT = 'One sentence here. Two sentence here.\n\nThree sentence here.\n'


def items(*rows):
    return [{'passage_id': p, 'sentence': s, 'tag': t} for p, s, t in rows]


def test_v1_a_first_sentence_tag_equal_to_the_register_is_sent_once():
    tagged, spans = VD.apply(SCRIPT, items(('P001', 1, '[measured]')), '[measured]')
    assert tagged.startswith('[measured] One sentence') and tagged.count('[measured]') == 1
    assert VD.untag(tagged, spans) == SCRIPT


def test_v1_a_tag_equal_to_the_previous_tag_is_dropped_and_a_change_is_kept():
    tagged, _ = VD.apply(SCRIPT, items(('P001', 1, '[warm]'), ('P001', 2, '[warm]'), ('P002', 1, '[measured]')), '[measured]')
    assert tagged == '[measured] [warm] One sentence here. Two sentence here.\n\n[measured] Three sentence here.\n'


def test_v1_the_directions_digest_is_unchanged():
    rows = items(('P001', 1, '[measured]'))
    assert VD.digest(rows, '[measured]') == VD.digest(list(rows), '[measured]')


# ---------- S3: the script's claims handed to the visuals package ----------

def test_s3_the_scripts_claims_reach_the_visuals_package():
    claims = [{'text': '20, 35 and 75 kg/cm2 for one, two and three storeys', 'checked': False}]
    assert VS.script_claims({'summary': {'claims': claims}}) == claims
    assert VS.script_claims({'summary': {}}) == [] and VS.script_claims(None) == []


# ---------- A4: up to three automatic retries for a passing failure ----------

class Conn:
    def __init__(self):
        self.inserts = []

    def execute(self, sql, params=None):
        if 'insert into vw2_jobs' in sql:
            self.inserts.append(json.loads(json.dumps(params[3].obj)))
        return self


@pytest.fixture
def conn(monkeypatch):
    monkeypatch.setattr(AJ.jobs, 'finish', lambda *a, **k: None)
    monkeypatch.setattr(AJ, '_pool_size', lambda: 5)
    return Conn()


def job(**request):
    return {'id': 'j0', 'run_id': 'run-1', 'unit': 'c1', 'request': {'analysis_key': 'k', **request}}


STREAM = ('failed', {'failure': 'provider_stream_error'})


def test_a4_a_stream_error_is_retried_three_times_then_waits_for_the_operator(conn):
    request = {'analysis_key': 'k'}
    for n in (1, 2, 3):
        AJ.finalize(conn, None, {'id': f'j{n}', 'run_id': 'run-1', 'unit': 'c1', 'request': request}, *STREAM, 'x', None, None)
        request = conn.inserts[-1]
        assert request['auto_retries'] == n and request['auto_retry_of'] == f'j{n}'
    AJ.finalize(conn, None, {'id': 'j4', 'run_id': 'run-1', 'unit': 'c1', 'request': request}, *STREAM, 'x', None, None)
    assert len(conn.inserts) == 3


@pytest.mark.parametrize('status,result', [('failed', {'failure': 'incomplete_response'}), ('failed', {'failure': 'empty_response'}),
                                           ('rejected', {'http_status': 429, 'category': 'rate_limit'}), ('rejected', {'http_status': 503})])
def test_a4_the_other_passing_failures_are_retried(conn, status, result):
    AJ.finalize(conn, None, job(), status, result, 'x', None, None)
    assert len(conn.inserts) == 1 and conn.inserts[0]['auto_retries'] == 1


@pytest.mark.parametrize('status,result', [('failed', {'failure': 'blocked_response'}), ('failed', {'failure': 'model_json'}), ('failed', {'phase': 'prepare'}),
                                           ('rejected', {'http_status': 400}), ('rejected', {'http_status': 403}),
                                           ('submission_unknown', {'failure': 'timeout', 'phase': 'generate'}), ('retained_unstructured', {})])
def test_a4_a_failure_that_would_repeat_is_not_retried(conn, status, result):
    AJ.finalize(conn, None, job(), status, result, 'x', None, None)
    assert conn.inserts == []


def test_a4_a_billing_limit_with_one_key_is_not_retried(conn, monkeypatch):
    monkeypatch.setattr(AJ, '_pool_size', lambda: 1)
    AJ.finalize(conn, None, job(), 'rejected', {'http_status': 429, 'category': 'spending_or_billing_limit'}, 'x', None, None)
    assert conn.inserts == []


def test_a4_an_operators_retry_gets_no_automatic_retries_and_an_automatic_row_is_not_an_operators_retry(conn):
    AJ.finalize(conn, None, job(retry_of='j0', retry_note='their words'), *STREAM, 'x', None, None)
    assert conn.inserts == []
    AJ.finalize(conn, None, job(), *STREAM, 'x', None, None)
    assert 'retry_of' not in conn.inserts[0] and 'retry_note' not in conn.inserts[0]
