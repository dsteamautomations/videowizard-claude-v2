"""design/210, the wording review (16 Nov 2026), the tool's side, with the server faked: the lines the tool prints send the assistant to
the page for the steps that are answered there. F4: after the round file is sent. F5: the wait ends when the sets are back, and what
waits on the page is not sent to the chat. F8: `vw next` at the visuals stage. F9: a frame grabbed alone. And the instruction texts
(the command file, the drawing skill, the visuals parts of version 3) say the same."""
import argparse
import json

import pytest

from conftest import PLUGIN, REPO
from test_visuals_cli import args, harness, jobs_answer, run   # noqa: F401 (harness is a fixture)
import vw

ON_PAGE = 'on the page (`vw visuals page`)'
CMD = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
VISUALS = next(s for s in json.loads((REPO / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
PART = {p['name']: p['text'] for p in VISUALS['parts']}


# ---------- F4: after `vw visuals round --file` ----------

def test_after_the_round_file_is_sent_the_assistant_is_sent_to_the_page(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'out' / 'reference-round.json').write_text(json.dumps([{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}]), encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'pass': 1, 'elements': 1, 'kept': True})
    code, out, err = run(args(what='round', file='out/reference-round.json'), capsys)
    assert code == 0 and ('Now `vw visuals page`: the operator answers step 1 there, in one visit; in the chat (`vw visuals next`) only where the page '
                          'cannot be shown.') in err
    assert 'no page' not in err and 'one element at a time in the chat' not in err and 'again after every answer' not in err


# ---------- F5: the wait between the two steps ----------

def status(monkeypatch, capsys, answers, wait=900):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answers.pop(0) if len(answers) > 1 else answers[0])
    return run(args(what='status', wait=wait), capsys)


def test_the_wait_ends_at_once_when_the_sets_are_back_and_sends_the_assistant_to_the_page(harness, monkeypatch, capsys):
    _, slept = harness
    code, out, err = status(monkeypatch, capsys, [{**jobs_answer(), 'round': {'pass': 2, 'kept': True}}])
    assert code == 0 and slept == [] and 'reference round at pass 2: the operator answers it on the page, `vw visuals page`' in err
    assert 'in the chat' not in err


def test_the_wait_does_not_wait_for_the_operators_step_one(harness, monkeypatch, capsys):
    _, slept = harness
    code, out, err = status(monkeypatch, capsys, [{**jobs_answer(), 'round': {'pass': 1, 'kept': True}}])
    assert slept == [] and 'reference round at pass 1: the operator answers it on the page, `vw visuals page`' in err


def test_the_wait_goes_on_while_a_set_is_being_made_and_ends_when_it_is_back(harness, monkeypatch, capsys):
    _, slept = harness
    making = {**jobs_answer(), 'round': {'pass': 'making', 'kept': True}}   # the set's job is done and its pictures are not stored yet: the round still says making
    code, out, err = status(monkeypatch, capsys, [jobs_answer(('j1', 'E2', 'gemini-image', 'running')) | {'round': {'pass': 'making', 'kept': True}}, making,
                                                  {**jobs_answer(), 'round': {'pass': 2, 'kept': True}}])
    assert slept == [15, 15] and 'pass 2: the operator answers it on the page' in err


def test_an_older_films_round_is_waited_for_as_before(harness, monkeypatch, capsys):
    _, slept = harness
    code, out, err = status(monkeypatch, capsys, [{'jobs': [], 'round': {'pass': 1}}, {'jobs': [], 'round': {'pass': 'complete'}}], wait=60)
    assert slept == [15] and 'reference round at pass complete' in err and 'read the verdicts' in err


def test_what_waits_on_the_page_is_not_sent_to_the_chat(harness, monkeypatch, capsys):
    wt = [{'label': 'Set to judge · E2', 'kind': 'set to judge'}, {'label': 'Set to make · P1', 'kind': 'set to make'}, {'label': 'Drawing spec to approve · DG1', 'kind': 'drawing spec to approve'}]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {**jobs_answer(), 'waiting': wt})
    code, out, err = run(args(), capsys)
    assert '3 waiting for the operator: all answered on the page in one visit (`vw visuals page`): the sizes, materials and graphic specs, and the reference sets' in err
    assert '`vw visuals next`' not in err
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {**jobs_answer(), 'waiting': wt + [{'label': 'Still · DG1', 'kind': 'picture to answer'}]})
    code, out, err = run(args(), capsys)
    assert ('4 waiting for the operator: 3 of them are answered on the page in one visit (`vw visuals page`): the sizes, materials and graphic specs, and the reference sets; '
            'ask the others one at a time with `vw visuals next` (design/188), never from this list') in err


# ---------- F8: `vw next` at the visuals stage ----------

def test_vw_next_at_the_visuals_stage_says_what_is_on_the_page_and_what_is_in_the_chat(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'ensure_mine', lambda nxt, take_over, run_id: None)
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'stage': 'visuals', 'paid': 'openai'})
    with pytest.raises(SystemExit):
        vw.cmd_next(argparse.Namespace(take_over=False))
    out, err = capsys.readouterr()
    said = ('The treatment, the plan, the sizes, materials and graphic specs, the reference drawings, the two steps of the references and the pictures and drawn graphics are answered '
            'on the page (`vw visuals page`); the AI video and the recording are asked in the chat, one at a time (`vw visuals next`).')   # design/217
    assert json.loads(out)['visuals_in_chat'] == said and said in err and "decisions of this stage are taken in the chat" not in err


# ---------- F9: a frame grabbed alone ----------

def test_a_frame_grabbed_alone_is_a_candidate_for_the_round_not_approved_by_its_sha(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'id': 'F7', 'kind': 'frame', 'sha256': 'abc'})
    code, out, err = run(args(what='frame', element='E1', clip='m1', at='12.5'), capsys)
    assert code == 0 and 'F7' in err and 'a candidate for the round (`vw visuals round --file`)' in err
    assert 'sha256' not in err and 'fetch --ref' not in err


# ---------- the instruction texts ----------

def test_the_command_file_says_where_each_decision_is_taken():
    assert ('The treatment, the plan, the sizes, materials and graphic specs, the reference drawings, the two steps of the references, the pictures and drawn graphics and the finished AI video takes are answered '
            "on the page (`vw visuals page`), and in the chat only a question the server says is asked there (the film's font: show the picture of `vw font --sample` first, "
            "then ask as before) or where the page cannot be shown; an AI video shot's layout drawing, its still and the word to make its first take, and the recording, are asked in the chat, one at a time;") in CMD   # design/218; design/217; design/222: the finished takes on the page
    assert 'the AI video and the recording are asked in the chat, one at a time' not in CMD   # design/222: retired
    assert 'every other decision of this stage is asked in the chat' not in CMD
    assert "the card's buttons" not in CMD and '`vw visuals next` hands' in CMD                       # C2: a question is handed out by `vw visuals next`
    assert '`select` a choice where offered' not in CMD and 'with the operator\'s answer' in CMD     # F3: the choice is the operator's
    assert '`status --wait 900`: step 1 the operator approves' not in CMD and '`status --wait 900` while sets are made' in CMD and 'then do what each answer says (`then`)' in CMD   # F5; design/211: every answer of the round says what comes next


def test_the_drawing_skill_sends_the_approval_to_the_page():
    skill = (PLUGIN / 'skills' / 'drawing' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'Then `vw visuals next` shows the operator' not in skill
    assert ON_PAGE + '; in the chat (`vw visuals next`) only where the page cannot be shown' in skill


def test_the_plan_part_leaves_an_offered_choice_to_the_operator():
    assert '`vw visuals select --gap G --choice C` for an offered choice' not in PART['plan']
    assert PART['plan'].count('vw visuals select --gap') == 1 and "with the operator's answer" in PART['plan']   # named once, as the chat way


def test_the_picture_search_part_reads_in_the_order_it_is_done_and_names_no_command_that_refuses():
    text = PART['picture-search']
    frames, drawn, the_round = text.index('take small trial frames'), text.index('is drawn before the round'), text.index('write out/reference-round.json')   # design/211: was 'grab a frame of each'
    assert frames < drawn < the_round < text.index('`vw visuals status --wait 900`')
    assert 'round --undo' not in text and 'until the round is complete; ask nothing per element' not in text
    assert 'Every answer of the round says what comes next (`then`): do that and add nothing of your own.' in text   # design/211: was 'it ends when the sets are back; then `vw visuals page`'
    assert len(text.strip().split('\n')) == 5   # the heading and four paragraphs: the frames, the drawings, the round, the two steps


def test_the_common_part_and_the_treatment_part_say_what_the_server_does():
    common = VISUALS['prompt']
    assert 'E. WHERE THE OPERATOR DECIDES: THE PAGE, THEN THE CHAT\n' in common and 'ONE AT A TIME, IN THE CHAT' not in common
    assert "shows on the item's card" not in common and "the card's buttons" not in common and 'in its turn (`vw visuals next`)' in common
    assert 'every line on one card, the Direction first' not in PART['treatment'] and 'the Direction alone' in PART['treatment']


def test_every_command_the_new_sentences_name_is_one_the_tool_takes():
    parser = vw.build_parser()
    for line in ('visuals page', 'visuals next', 'visuals round --file out/reference-round.json', 'visuals status --wait 900', 'visuals select --gap G --choice C',
                 'visuals decide --item I --choice C --quote Q', 'visuals card --file F', 'visuals answer --item X --answer A', 'drawing set --element E --file work/drawing/E/set.json'):
        assert parser.parse_args(line.split()), line
