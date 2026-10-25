"""design/86 K2: the check before the operator, with the transport faked."""
import json
import types

from app import image_check as IC

REF = {'id': 'k1', 'element_id': 'E1', 'name': 'keyframe-start-VS1', 'kind': 'keyframe', 'subject': 'the mason', 'key': 'run-1/visuals/references/k1.png', 'status': 'candidate',
       'generation': {'op': 'edit', 'prompt': 'Image 1 is the sheet. The mason at the wall.', 'size': '1536x864', 'parents': [{'id': 'S1'}]},
       'answer': {'status': 'ready', 'prompt': 'Image 1 is the sheet. The mason at the wall.', 'checklist': [{'check': 'scale', 'pass_when': 'the wall is taller than the mason', 'weight': 'must'},
                                                                                                           {'check': 'light', 'pass_when': 'soft morning light', 'weight': 'should'}]}}
SESSION = {'references': {'k1': REF, 'S1': {'id': 'S1', 'kind': 'sheet', 'status': 'approved', 'key': 'run-1/visuals/references/S1.png'}}}
RESULT = {'key': 'run-1/visuals/references/k1.png', 'width': 1536, 'height': 864}


class Store:
    def get(self, key):
        return b'png-' + key.encode()


def transport(answer=None, raise_=None):
    class T:
        def __init__(self, key, model, **kw):
            self.model = model
            self.payloads = []

        def generate(self, payload):
            T.last = payload
            if raise_:
                raise raise_
            return {'body': answer, 'metadata': {}, 'raw': json.dumps(answer)}
    return T


def key_set(monkeypatch, value='k'):
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: value)))


def test_the_lines_are_the_writers_then_the_three_fixed_ones_and_the_request_carries_the_parents_and_the_candidate():
    lines = IC.lines_of(REF)
    assert [l['check'] for l in lines] == ['scale', 'light', 'readable text', 'a real face', 'nothing extra', 'plausible setting', 'practitioner']   # design/91 N7: a scene picture
    payload = IC.build(b'cand', [('sheet', b'p1')], lines, REF['generation']['prompt'])
    parts = payload['contents'][0]['parts']
    assert parts[0]['text'] == 'Reference 1 (sheet).' and 'inlineData' in parts[1] and parts[2]['text'] == 'The candidate picture.' and 'inlineData' in parts[3]
    assert '1. scale: passes when the wall is taller than the mason' in parts[4]['text'] and '5. nothing extra' in parts[4]['text'] and payload['generationConfig']['responseJsonSchema'] == IC.SCHEMA


def test_the_answer_is_read_line_by_line_and_a_failed_must_line_is_listed(monkeypatch):
    key_set(monkeypatch)
    answer = {'lines': [{'n': 1, 'pass': False, 'seen': 'the mason is taller than the wall'}, {'n': 2, 'pass': True, 'seen': 'soft light'}, {'n': 3, 'pass': True, 'seen': 'no text'},
                        {'n': 4, 'pass': True, 'seen': 'no face match'}, {'n': 5, 'pass': False, 'seen': 'a second worker at the left'}]}
    rec = IC.run_check(Store(), SESSION, REF, RESULT, transport(answer))
    assert rec['lines'][0] == {'check': 'scale', 'weight': 'must', 'pass': False, 'seen': 'the mason is taller than the wall'}   # design/92: stored without what the checklist holds
    assert IC.expand(rec, REF)['lines'][0]['pass_when'] == 'the wall is taller than the mason'
    assert [l['check'] for l in rec['must_failed']] == ['scale'] and rec['code'][0]['pass'] is True and rec['code'][1]['check'] == 'parent' and 'error' not in rec
    assert rec['lines'][4]['pass'] is False and rec['lines'][4]['weight'] == 'should'


def test_a_transport_error_or_no_key_leaves_the_candidate_with_the_error_on_the_check(monkeypatch):
    key_set(monkeypatch)
    rec = IC.run_check(Store(), SESSION, REF, RESULT, transport(raise_=RuntimeError('boom')))
    assert rec['error'] == 'RuntimeError: boom' and rec['must_failed'] == [] and rec['lines'] == []
    key_set(monkeypatch, '')
    assert IC.run_check(Store(), SESSION, REF, RESULT, transport({}))['error'] == 'no Gemini key on the server'
    wrong = IC.code_checks({**REF, 'generation': {**REF['generation'], 'size': '1024x1024'}}, RESULT, [])
    assert wrong[0]['pass'] is False and wrong[0]['seen'] == '1536x864'


def test_the_fix_round_is_one_change_from_the_failed_line(monkeypatch):
    failed = {'check': 'scale', 'pass_when': 'the wall is taller than the mason', 'weight': 'must', 'pass': False, 'seen': 'x'}
    body = IC.fix_body(REF, failed)
    assert body['parents'] == ['k1'] and body['fix_of'] == 'k1' and body['name'] == 'keyframe-start-VS1-fix' and body['kind'] == 'keyframe'
    assert 'Change only: the wall is taller than the mason.' in body['prompt'] and body['prompt'].count('Change only') == 1 and body['answer']['single_change'] == failed['pass_when']
    from app import library
    assert library.check_prompt(body['prompt']) is None   # the fix passes the lint, one change
