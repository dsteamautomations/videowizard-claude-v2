"""design/177: the visuals page's new actions from the chat tool, with the server faked: the request each flag sends, the line it prints,
the refusal it relays. `round --answer`, `--make`, `--aside`, `--back`, `approve --again`, `own`, and `held` in `round --sets`."""
import base64
import json

import pytest

from conftest import PLUGIN
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is the fixture)
import vw

WRITE = vw.write


def posts(monkeypatch, answer):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or answer)
    return sent


def refuses(monkeypatch, message, status=422):
    """The server says no: vw.request's answer for a 4xx (refused) or a 5xx (tell the builder)."""
    sent = []
    monkeypatch.setattr(vw, 'write', WRITE)   # the real write again, after a faked one
    payload = {'action': 'tell_builder' if status >= 500 else 'refused', 'status': status, 'code': 'VISUALS_CONTRACT', 'message': message}
    monkeypatch.setattr(vw, 'request', lambda method, path, wait=None, **kw: sent.append((path, kw.get('json'))) or (payload, 2))
    return sent


def nothing_sent(monkeypatch):
    monkeypatch.setattr(vw, 'call', lambda *a, **k: pytest.fail('nothing may reach the server'))
    monkeypatch.setattr(vw, 'write', lambda *a, **k: pytest.fail('nothing may reach the server'))


# ---------- round --answer ----------

def test_round_answer_stores_one_answer_of_step_2(harness, monkeypatch, capsys):
    sent = posts(monkeypatch, {'element_id': 'E2', 'stored': True, 'answer': {'verdict': 'yes', 'golden': 'R5', 'words': ''}})
    code, out, err = run(args(what='round', answer='E2', verdict='yes', golden='R5'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/round/answer', {'element_id': 'E2', 'verdict': 'yes', 'golden': 'R5', 'words': ''})]
    assert err.strip() == 'Answer stored for E2: yes, starting picture R5. It is not recorded yet: Done on the page records it, or `vw visuals round --sets <file>` (a stored answer stands for an element the file leaves out).'
    sent = posts(monkeypatch, {'element_id': 'P1', 'stored': True, 'answer': {'verdict': 'correct', 'golden': None, 'words': 'older, grey hair'}})
    code, out, err = run(args(what='round', answer='P1', verdict='correct', words='older, grey hair'), capsys)
    assert code == 0 and sent[0][1] == {'element_id': 'P1', 'verdict': 'correct', 'golden': None, 'words': 'older, grey hair'} and 'Answer stored for P1: correct ("older, grey hair").' in err


def test_round_answer_says_when_the_set_was_made_again_and_relays_a_refusal(harness, monkeypatch, capsys):
    posts(monkeypatch, {'element_id': 'E2', 'stored': False, 'discarded': True, 'next': 'E2: made again since; judge the new set.'})
    code, out, err = run(args(what='round', answer='E2', verdict='yes', golden='R5'), capsys)
    assert code == 0 and err.strip() == 'E2: made again since; judge the new set.'
    sent = refuses(monkeypatch, 'The reference round is not at step 2: there is no set to answer now.')
    code, out, err = run(args(what='round', answer='E2', verdict='no'), capsys)
    assert code == 2 and sent[0][0].endswith('/visuals/round/answer') and out['message'] == 'The reference round is not at step 2: there is no set to answer now.' and out['message'] in err


def test_round_answer_needs_its_verdict_and_a_named_picture(harness, monkeypatch, capsys):
    nothing_sent(monkeypatch)
    code, out, err = run(args(what='round', answer='E2'), capsys)
    assert code == 2 and '--verdict yes|no|correct' in out['message']
    code, out, err = run(args(what='round', answer='E2', verdict='maybe'), capsys)
    assert code == 2 and '--verdict yes|no|correct' in out['message']
    code, out, err = run(args(what='round', answer='E2', verdict='yes', golden=True), capsys)   # --golden with no picture after it
    assert code == 2 and '--golden <picture id>' in out['message']
    code, out, err = run(args(what='round', verdict='yes'), capsys)   # a verdict for nothing
    assert code == 2 and '--answer <element>' in out['message']


# ---------- round --make ----------

def test_round_make_makes_one_set_that_was_not_made(harness, monkeypatch, capsys):
    sent = posts(monkeypatch, {'element_id': 'BRICK', 'queued': True, 'pass': 'making', 'cost_inr': 60.0, 'next': 'BRICK: its set is being made; it comes back on step 2.'})
    code, out, err = run(args(what='round', make='BRICK'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/round/make', {'element_id': 'BRICK'})]
    assert err.strip() == 'BRICK: its set is being made; it comes back on step 2. (about ₹60; paid: tell the operator.) Then `vw visuals status --wait 900`.'
    posts(monkeypatch, {'element_id': 'BRICK', 'queued': False, 'next': 'BRICK: its set is already being made.'})
    code, out, err = run(args(what='round', make='BRICK'), capsys)
    assert code == 0 and err.strip() == 'BRICK: its set is already being made.'


def test_round_make_relays_the_cause_that_stands(harness, monkeypatch, capsys):
    refuses(monkeypatch, 'BRICK: its set cannot be made yet: the material spec of Red brick is not approved.')
    code, out, err = run(args(what='round', make='BRICK'), capsys)
    assert code == 2 and out['action'] == 'refused' and 'the material spec of Red brick is not approved' in err


# ---------- round --aside, --back ----------

def test_round_aside_sets_a_never_made_set_aside_and_back_returns_it(harness, monkeypatch, capsys):
    sent = posts(monkeypatch, {'element_id': 'E2', 'aside': True, 'next': 'E2 is set aside for this round: nothing is made for it. Bring back returns it while the round is open.'})
    code, out, err = run(args(what='round', aside='E2', words='not needed in this film'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/round/aside', {'element_id': 'E2', 'words': 'not needed in this film', 'back': False})]
    assert err.strip() == 'E2 is set aside for this round: nothing is made for it. `vw visuals round --back E2` returns it while the round is open.'   # the page's button named as the command
    sent = posts(monkeypatch, {'element_id': 'E2', 'aside': False, 'next': 'E2 is back in the round.'})
    code, out, err = run(args(what='round', back='E2'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/round/aside', {'element_id': 'E2', 'words': '', 'back': True})] and err.strip() == 'E2 is back in the round.'


def test_round_aside_and_back_relay_their_refusals(harness, monkeypatch, capsys):
    refuses(monkeypatch, 'E2 has its set: answer it with No or Correct it; only a set that was never made can be set aside.')
    code, out, err = run(args(what='round', aside='E2'), capsys)
    assert code == 2 and 'only a set that was never made can be set aside' in err
    refuses(monkeypatch, 'E2 was not set aside at step 2: there is nothing to bring back.')
    code, out, err = run(args(what='round', back='E2'), capsys)
    assert code == 2 and out['message'] == 'E2 was not set aside at step 2: there is nothing to bring back.'


def test_one_round_action_at_a_time(harness, monkeypatch, capsys):
    nothing_sent(monkeypatch)
    code, out, err = run(args(what='round', make='E1', aside='E2'), capsys)
    assert code == 2 and 'one of --answer, --make, --aside, --back' in out['message']
    code, out, err = run(args(what='image', element='E1', kind='sheet', make='E1'), capsys)   # the new flags belong to round only
    assert code == 2 and '--make' in out['message'] and 'image' in out['message']


# ---------- round --sets prints what the cap holds ----------

def test_round_sets_prints_the_answers_held_at_the_spend_cap(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'out' / 'sets.json').write_text(json.dumps({'E1': {'verdict': 'yes', 'golden': 'R1'}, 'E2': {'verdict': 'no'}}), encoding='utf-8')
    held = {'E2': 'the spend cap of ₹2,000 is reached (₹1,980 spent): the set is not made again; its answer is kept and waits'}
    sent = posts(monkeypatch, {'pass': 2, 'queued': [], 'errors': {}, 'approved': ['E1'], 'held': held})
    code, out, err = run(args(what='round', sets='out/sets.json', quote='As said.'), capsys)
    assert code == 0 and sent[0][0].endswith('/visuals/round/sets') and out['held'] == held
    assert err.strip() == ('Sets recorded: 1 approved, 0 being made again; the round is 2. Held: E2: the spend cap of ₹2,000 is reached (₹1,980 spent): the set is not made again; '
                           'its answer is kept and waits. Tell the operator the spend; the builder changes the cap.')
    posts(monkeypatch, {'pass': 'complete', 'queued': [], 'errors': {}, 'approved': ['E1'], 'held': {}})   # nothing held: the line of before
    code, out, err = run(args(what='round', sets='out/sets.json'), capsys)
    assert code == 0 and err.strip() == 'Sets recorded: 1 approved, 0 being made again; the round is complete.'
    posts(monkeypatch, {'pass': 'complete', 'queued': [], 'errors': {}, 'approved': ['E1']})   # an older server sends no `held`
    code, out, err = run(args(what='round', sets='out/sets.json'), capsys)
    assert code == 0 and 'Held' not in err


# ---------- approve --again ----------

def test_approve_again_approves_a_rejected_picture_after_all(harness, monkeypatch, capsys):
    sent = posts(monkeypatch, {'id': 'R7', 'status': 'approved', 'rejection': None, 'next': 'Approved: the take for VS1 is the next step.'})
    monkeypatch.setattr(vw, 'call', lambda *a, **k: pytest.fail('the sha was given: nothing is read first'))
    code, out, err = run(args(what='approve', ref='R7', sha='a' * 64, again=True, quote='It is fine after all.'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/references/R7/reapprove', {'sha256': 'a' * 64, 'quote': 'It is fine after all.'})]
    assert err.strip() == 'Approved: the take for VS1 is the next step.'


def test_approve_again_reads_the_pictures_hash_when_none_is_given(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'references': [{'id': 'R6', 'sha256': 'c' * 64}, {'id': 'R7', 'sha256': 'b' * 64, 'status': 'rejected'}]})
    sent = posts(monkeypatch, {'id': 'R7', 'status': 'approved', 'rejection': None})
    code, out, err = run(args(what='approve', ref='R7', again=True), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/references/R7/reapprove', {'sha256': 'b' * 64, 'quote': ''})] and err.strip() == 'Approved R7 again.'
    monkeypatch.setattr(vw, 'write', lambda *a, **k: pytest.fail('an unknown picture is not sent'))
    code, out, err = run(args(what='approve', ref='R9', again=True), capsys)
    assert code == 2 and out['message'] == 'R9 is not a picture of this film; `vw visuals status` lists them.'


def test_approve_again_relays_the_line_why_it_can_no_longer_be_changed(harness, monkeypatch, capsys):
    sent = refuses(monkeypatch, 'This picture was answered with its set on step 2 of the reference round: a set is judged as a whole.')
    code, out, err = run(args(what='approve', ref='R7', sha='a' * 64, again=True), capsys)
    assert code == 2 and sent[0][0].endswith('/references/R7/reapprove') and 'a set is judged as a whole' in err
    nothing_sent(monkeypatch)
    code, out, err = run(args(what='approve', file='out/approvals.json', again=True), capsys)   # one picture at a time
    assert code == 2 and '--again takes one picture: --ref R' in out['message']
    code, out, err = run(args(what='reject', ref='R7', again=True), capsys)
    assert code == 2 and '--again' in out['message'] and 'reject' in out['message']


def test_approve_without_again_is_as_before(harness, monkeypatch, capsys):
    sent = posts(monkeypatch, {'id': 'R7', 'status': 'approved', 'next': 'Approved.'})
    code, out, err = run(args(what='approve', ref='R7', sha='a' * 64), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/references/R7/approve', {'sha256': 'a' * 64, 'quote': ''})]


# ---------- own: the operator's own picture ----------

def test_own_sends_the_file_and_says_it_is_approved(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'in').mkdir()
    (ws / 'in' / 'plinth.jpg').write_bytes(b'\xff\xd8 a picture')
    sent = posts(monkeypatch, {'id': 'own1', 'kind': 'supplied', 'status': 'approved', 'element_id': 'E1', 'next': 'Your picture is saved and approved for E1.'})
    code, out, err = run(args(what='own', element='E1', file='in/plinth.jpg', name='plinth-own'), capsys)
    assert code == 0 and sent[0][0] == '/api/runs/run-1/visuals/own'
    assert sent[0][1] == {'element_id': 'E1', 'content_base64': base64.b64encode(b'\xff\xd8 a picture').decode(), 'url': '', 'name': 'plinth-own'}
    assert err.strip() == ('Your picture is saved and approved for E1. It is picture own1: to start every shot of E1 from it, '
                           '`vw visuals round --answer E1 --verdict yes --golden own1` at step 2.')
    sent = posts(monkeypatch, {'id': 'own2', 'kind': 'supplied', 'status': 'approved', 'element_id': 'E1', 'next': 'Your picture is saved and approved for E1.'})
    code, out, err = run(args(what='own', element='E1', url='https://example.org/plinth.jpg'), capsys)
    assert code == 0 and sent[0][1] == {'element_id': 'E1', 'content_base64': '', 'url': 'https://example.org/plinth.jpg', 'name': ''}


@pytest.mark.parametrize('message', [
    "A person's reference is made from the description; an uploaded photo is not used for people.",   # a person on a kept film
    'The picture is larger than 15 MB: choose a smaller file.',
    'That file is not a picture this page can read: use a PNG, JPEG or WebP image.'])
def test_own_relays_each_refusal_in_the_servers_plain_words(harness, monkeypatch, capsys, message):
    ws, _ = harness
    (ws / 'notes.txt').write_bytes(b'not a picture')
    sent = refuses(monkeypatch, message)
    code, out, err = run(args(what='own', element='P1', file='notes.txt'), capsys)
    assert code == 2 and sent[0][0].endswith('/visuals/own') and out['message'] == message and err.strip() == message


def test_own_needs_an_element_and_a_file_in_the_run_folder_or_an_https_link(harness, monkeypatch, capsys):
    ws, _ = harness
    nothing_sent(monkeypatch)
    code, out, err = run(args(what='own', file='in/plinth.jpg'), capsys)
    assert code == 2 and '--element' in out['message']
    code, out, err = run(args(what='own', element='E1'), capsys)
    assert code == 2 and '--file' in out['message'] and '--url https://' in out['message']
    code, out, err = run(args(what='own', element='E1', url='http://example.org/a.jpg'), capsys)
    assert code == 2 and '--url https://' in out['message']
    code, out, err = run(args(what='own', element='E1', file='../outside.jpg'), capsys)
    assert code == 2 and out['message'] == 'The picture must be a file inside the run folder.'
    (ws / 'big.jpg').write_bytes(b'x' * 16)
    monkeypatch.setattr(vw, 'OWN_PICTURE_MAX', 15)   # the 15 MB limit, said before 20 MB is sent
    code, out, err = run(args(what='own', element='E1', file='big.jpg'), capsys)
    assert code == 2 and out['message'] == 'The picture is larger than 15 MB: choose a smaller file.'


def test_supply_is_the_older_way_and_still_sends_a_candidate(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'p.png').write_bytes(b'png')
    sent = posts(monkeypatch, {'id': 'r1', 'kind': 'supplied'})
    code, out, err = run(args(what='supply', element='E1', file='p.png'), capsys)
    assert code == 0 and sent[0][0].endswith('/visuals/references') and sent[0][1]['kind'] == 'supplied' and 'is a candidate' in err


# ---------- an unexpected server error; the parser; the instruction text ----------

def test_an_unexpected_server_error_reaches_the_operator_as_the_plain_sentence(harness, monkeypatch, capsys):
    refuses(monkeypatch, 'That could not be done; nothing was changed. The builder has been told what failed.', status=500)
    code, out, err = run(args(what='round', make='E1'), capsys)
    assert code == 2 and out['action'] == 'tell_builder' and err.strip() == 'That could not be done; nothing was changed. The builder has been told what failed.'


def test_the_parser_reads_the_new_flags_and_golden_both_ways():
    p = vw.build_parser()
    a = p.parse_args(['visuals', 'round', '--answer', 'E2', '--verdict', 'yes', '--golden', 'R5', '--words', 'as it is'])
    assert (a.answer, a.verdict, a.golden, a.words) == ('E2', 'yes', 'R5', 'as it is') and not vw.visuals_flags_refused(a)
    a = p.parse_args(['visuals', 'image', '--element', 'E1', '--kind', 'isolated', '--golden'])   # design/111 F11, as before
    assert a.golden is True and not vw.visuals_flags_refused(a)
    for argv in (['round', '--make', 'E1'], ['round', '--aside', 'E1', '--words', 'no need'], ['round', '--back', 'E1'], ['approve', '--ref', 'R7', '--again'],
                 ['own', '--element', 'E1', '--file', 'in/a.jpg'], ['own', '--element', 'E1', '--url', 'https://example.org/a.jpg']):
        assert not vw.visuals_flags_refused(p.parse_args(['visuals'] + argv)), argv


def test_the_instruction_text_names_each_new_command_once():
    text = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    visuals = next(line for line in text.splitlines() if line.startswith('**Visuals**'))
    for command in ('round --answer <element> --verdict yes|no|correct', 'round --make <element>', 'round --aside <element>', 'round --back <element>',
                    'approve --ref R --again', 'vw visuals own --element E'):
        assert visuals.count(command) == 1, command
    assert 'held' in visuals
