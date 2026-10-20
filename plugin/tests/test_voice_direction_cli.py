"""design/52 C and D in the plugin: the direction step (prepare, record), per-voice tweaks, history, the record from a job,
the compact catalog line, the fetch message (design/49 V3), the next line with the page state, and the procedure text."""
import argparse
import json

import pytest

from conftest import STAGES
import vw
from stages_av import voice_prepare

SCRIPT = {'spoken_text': 'Earth blocks are pressed. Not fired.\n\nThey save fuel!\n', 'passages': {'P001': 'Earth blocks are pressed. Not fired.', 'P002': 'They save fuel!'},
          'beats': [{'beat_id': 'BEAT_01', 'passage_id': 'P001', 'text': 'Earth blocks are pressed. Not fired.'}, {'beat_id': 'BEAT_02', 'passage_id': 'P002', 'text': 'They save fuel!'}],
          'content_digest': 'd1'}
BRIEF = {'summary': {'purpose': 'teach', 'audience': 'builders', 'message': 'more with less', 'tone': 'calm', 'ending': 'principle', 'constraints': '',
                     'production': {'narration_language': 'en', 'field_speech_languages': ['ta']}}}
DIRECTION = {'kind_of_film': 'a documentary explainer', 'register': {'best_fit': '[measured]', 'experimental': '[warm, unhurried]'},
             'options': {'best_fit': [{'passage_id': 'P002', 'sentence': 1, 'first_words': 'They save fuel!', 'tag': '[with weight on the figures]', 'reason': 'the claim'}],
                         'experimental': [{'passage_id': 'P001', 'sentence': 2, 'first_words': 'Not fired.', 'tag': '[softly]', 'reason': 'the turn'}]},
             'experimental_idea': 'quieter, more intimate; risks sounding small'}


def args(**kw):
    base = {'what': 'direct', 'step': None, 'wait': 0, 'voice': [], 'excerpt': None, 'model': 'eleven_v4', 'settings': None, 'job': None, 'note': None, 'scope': 'account',
            'search': '', 'cursor': '', 'language': '', 'accent': '', 'gender': '', 'age': '', 'use_case': None, 'high_quality': False, 'owner': None,
            'choice': None, 'quote': None, 'file': None, 'passage': None}
    return argparse.Namespace(**{**base, **kw})


@pytest.fixture
def harness(ws, monkeypatch):
    monkeypatch.setattr(vw, 'RUNS', ws.parent)
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    (ws / 'out' / 'script.json').write_text(json.dumps(SCRIPT), encoding='utf-8')
    return ws


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_voice(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


# ---------- direct prepare ----------

def test_direct_prepare_prints_the_sentences_the_brief_and_the_direction_prompt(harness, monkeypatch, capsys):
    full = {'procedure_version': '2', 'next': {'stage': 'voice', 'voice_page': {'pick': {'voice_id': 'v1', 'name': 'A'}}},
            'outputs': [{'stage': 'brief', 'unit': None, **BRIEF}, {'stage': 'script', 'unit': None, 'summary': {'content_digest': 'd1'}}]}
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: full if '/api/runs/' in path else STAGES['voice'])
    code, out, err = run(args(step='prepare'), capsys)
    assert code == 0 and out['prompt'].startswith('VW-PROCEDURE') and 'VW-DIRECTION' in out['prompt']
    rows = out['inputs']['sentences']
    assert [(r['passage_id'], r['sentence'], r['text']) for r in rows] == [('P001', 1, 'Earth blocks are pressed.'), ('P001', 2, 'Not fired.'), ('P002', 1, 'They save fuel!')]
    assert out['inputs']['brief']['tone'] == 'calm' and out['inputs']['voice'] == {'voice_id': 'v1', 'name': 'A'} and out['output_file'] == 'out/direction.json'
    assert out['not_shareable']


# ---------- direct record ----------

PASSAGES = [{'passage_id': 'P001', 'first_word': 1, 'last_word': 6, 'why': 'the turn'}]


def test_direct_record_sends_the_chosen_list_and_the_words(harness, monkeypatch, capsys):
    ws = harness
    (ws / 'out' / 'direction.json').write_text(json.dumps({**DIRECTION, 'test_passages': PASSAGES}), encoding='utf-8')
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'chosen': 'experimental', 'digest': 'dd', 'items': 1, 'next': {'stage': 'voice'}})
    code, out, err = run(args(step='record', choice='experimental', passage=1, quote='the quieter one'), capsys)
    assert code == 0 and posted[0][0] == '/api/runs/run-1/voice/direction'
    body = posted[0][1]
    assert body['chosen'] == 'experimental' and body['register'] == '[warm, unhurried]' and body['items'] == DIRECTION['options']['experimental'] and body['quote'] == 'the quieter one'
    assert body['options'] == DIRECTION['options'] and body['kind_of_film'] == 'a documentary explainer'
    assert 'experimental' in err and 'recorded' in err


def test_direct_record_none_sends_an_empty_list(harness, monkeypatch, capsys):
    ws = harness
    (ws / 'out' / 'direction.json').write_text(json.dumps({**DIRECTION, 'test_passages': PASSAGES}), encoding='utf-8')
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append(body) or {'chosen': 'none', 'digest': 'dd', 'items': 0})
    code, out, err = run(args(step='record', choice='none', passage=1, quote='read it plain'), capsys)
    assert code == 0 and posted[0]['chosen'] == 'none' and posted[0]['items'] == [] and posted[0]['register'] == ''


def test_direct_record_refuses_without_the_file_the_choice_or_the_words(harness, monkeypatch, capsys):
    ws = harness
    code, out, _ = run(args(step='record', choice='best_fit', quote='yes'), capsys)
    assert code == 2 and 'direction.json' in out['message']
    (ws / 'out' / 'direction.json').write_text(json.dumps(DIRECTION), encoding='utf-8')
    code, out, _ = run(args(step='record', choice='weird', quote='yes'), capsys)
    assert code == 2 and 'best_fit, experimental or none' in out['message']
    code, out, _ = run(args(step='record', choice='best_fit', quote=''), capsys)
    assert code == 2 and 'quote' in out['message']
    (ws / 'out' / 'direction.json').write_text(json.dumps({'register': {}, 'options': {'best_fit': 'no'}}), encoding='utf-8')
    code, out, _ = run(args(step='record', choice='best_fit', quote='yes'), capsys)
    assert code == 2 and 'options.best_fit' in out['message']


# ---------- tweak and history ----------

def test_tweak_posts_the_voice_and_the_tags(harness, monkeypatch, capsys):
    ws = harness
    (ws / 'out' / 'tweaks.json').write_text(json.dumps([{'passage_id': 'P001', 'sentence': 1, 'tag': '[brisk]'}]), encoding='utf-8')
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'voice_id': 'v1', 'tweaks': 1})
    code, out, err = run(args(what='tweak', voice=['v1'], file='out/tweaks.json'), capsys)
    assert code == 0 and posted[0] == ('/api/runs/run-1/voice/tweaks', {'voice_id': 'v1', 'tweaks': [{'passage_id': 'P001', 'sentence': 1, 'tag': '[brisk]'}]})


def test_history_prints_where_a_voice_was_used(harness, monkeypatch, capsys):
    hist = {'voices': {'v1': {'name': 'A', 'narrations': 2, 'auditions': 3, 'last_used': '2026-10-18', 'final_in': [{'code': 'VW-5', 'title': 'T', 'client': 'C', 'date': '2026-10-18'}], 'narrated_in': [], 'auditioned_in': []}}}
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: hist if (kw.get('params') or {}).get('voice_id') == 'v1' else {'voices': {}})
    code, out, err = run(args(what='history', voice=['v1']), capsys)
    assert code == 0 and 'A' in err and '2 narration' in err and '3 audition' in err and 'VW-5' in err
    code, out, err = run(args(what='history', voice=['v9']), capsys)
    assert code == 0 and 'never used' in err


# ---------- fetch names the file it wrote (design/49 V3); catalog prints one line per voice ----------

def test_fetch_message_names_the_audition_file(harness, monkeypatch, capsys):
    ws = harness
    job = {'id': 'j1', 'status': 'ready', 'request': {'kind': 'audition', 'voice_id': 'v1', 'name': 'Adamya Sharma'}, 'result': {'audio_key': 'k', 'duration_s': 22.5}}
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: job)

    class R:
        status_code = 200
        content = b'ID3audio'

    class C:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **k):
            return R()
    monkeypatch.setattr(vw, 'api', lambda: C())
    code, out, err = run(args(what='fetch', job='j1'), capsys)
    assert code == 0 and out['files'] == [str(ws / 'out' / 'audition-Adamya-Sharma.mp3')] and 'audition-Adamya-Sharma.mp3' in err and (ws / 'out' / 'audition-Adamya-Sharma.mp3').is_file()
    assert not (ws / 'out' / 'narration.mp3').exists()


def test_catalog_prints_one_line_per_voice(harness, monkeypatch, capsys):
    rows = {'voices': [{'voice_id': 'v1', 'name': 'Adamya Sharma', 'accent': 'indian', 'gender': 'male', 'age': 'middle_aged', 'use_case': 'informative_educational', 'descriptive': 'confident',
                        'description': 'Authoritative.', 'favourite': True, 'on_account': True, 'narrations': 2, 'auditions': 1}], 'has_more': True, 'next_page_token': 'p2'}
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: rows)
    code, out, err = run(args(what='catalog', scope='library', gender='male'), capsys)
    assert code == 0 and '★ v1 · Adamya Sharma · indian · male · middle_aged · informative_educational · confident · on the account · 2 narrations, 1 audition' in err
    assert 'more: --cursor p2' in err


# ---------- the record from a job; prepare shows favourites and the page ----------

def test_stage_voice_record_takes_the_job_from_the_server(harness, monkeypatch):
    from stages_av import voice_record
    ws = harness
    job = {'id': 'j1', 'request': {'kind': 'narration', 'voice_id': 'v1', 'name': 'A', 'model_id': 'eleven_v4', 'settings': {}, 'source_script': 'd1', 'direction_digest': 'dd', 'tweaks': []},
           'result': {'audio_key': 'k.mp3', 'sha256': 'a', 'bytes': 1, 'timing_key': 'k.timing.json', 'timing_sha256': 'b', 'timing_bytes': 2, 'duration_s': 5.0}, 'cost': {'characters': 40}}
    (ws / 'out' / 'timing.json').write_text(json.dumps({'words': [{'passage_id': 'P001', 'start_s': 0, 'end_s': 2}, {'passage_id': 'P002', 'start_s': 2.5, 'end_s': 4}]}), encoding='utf-8')
    out = voice_record(ws, STAGES['voice'], lambda s: None, job)
    assert out['summary']['job_id'] == 'j1' and out['summary']['direction_digest'] == 'dd' and out['summary']['recorded_from'] == 'chat' and len(out['summary']['beats']) == 2
    assert [f['name'] for f in out['stored']] == ['narration.mp3', 'timing.json']


def test_voice_prepare_lists_favourites_and_the_page_state(harness):
    ws = harness
    prior = lambda stage: {'brief': BRIEF}[stage]
    out = voice_prepare(ws, STAGES['voice'], prior, last_voice=None, favourites=[{'voice_id': 'v1', 'name': 'A', 'narrations': 2, 'last_used': '2026-10-18'}],
                        voice_page={'pick': {'voice_id': 'v2', 'name': 'B', 'at': '2026-10-20T10:00:00+00:00'}, 'narrations': 1, 'direction': 'best_fit', 'final': False})
    assert out['inputs']['favourites'][0]['name'] == 'A' and out['inputs']['voice_page']['pick']['name'] == 'B'
    assert 'favourite' in out['message'].lower() and 'B' in out['message'] and 'page' in out['message'].lower()
    assert out['direction_prompt'].startswith('VW-PROCEDURE') and 'VW-DIRECTION' in out['direction_prompt']


def test_next_line_says_what_the_page_holds():
    nxt = {'stage': 'voice', 'paid': 'elevenlabs', 'voice_page': {'pick': {'name': 'B'}, 'narrations': 2, 'final': False, 'direction': 'none'}}
    line = vw.next_line(nxt)
    assert 'picked B on the voices page' in line and '2 narrations' in line and 'no direction' in line


# ---------- the procedure text ----------

def test_voice_steps_ask_one_question_at_a_time_and_carry_the_direction_prompt():
    v = STAGES['voice']
    steps = ' '.join(v['steps'])
    assert 'one question per message' in steps and 'gender' in steps and 'register' in steps and 'favourites' in steps and 'voices page' in steps.lower()
    assert 'vw voice direct prepare' in steps and 'best fit, experimental' in steps and 'vw voice direct record' in steps
    assert v['direction_prompt'].startswith('VW-PROCEDURE — for the assistant only, never for the operator.') and 'Never a pause tag' in v['direction_prompt'] and 'experimental' in v['direction_prompt']
    md = (vw.Path(__file__).resolve().parents[1] / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'direction' in md and 'voices page' in md.lower()


# ---------- VW-6: the voices page link travels with prepare and next; library voices are saved on audition ----------

def test_voice_prepare_hands_over_the_page_link(harness):
    ws = harness
    out = voice_prepare(ws, STAGES['voice'], lambda stage: {'brief': BRIEF}[stage], page_url='https://x.example/runs/VW-9/voices')
    assert out['voice_page_url'] == 'https://x.example/runs/VW-9/voices' and 'https://x.example/runs/VW-9/voices' in out['message']


def test_next_carries_the_page_link_at_the_voice_stage(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'server_url', lambda: 'https://x.example')
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'stage': 'voice', 'paid': 'elevenlabs', 'voice_page': {'pick': None, 'narrations': 0, 'final': False, 'direction': None}})
    monkeypatch.setattr(vw, 'ensure_mine', lambda nxt, take_over, run_id: None)
    with pytest.raises(SystemExit) as exc:
        vw.cmd_next(argparse.Namespace(take_over=False))
    out, err = capsys.readouterr()
    assert exc.value.code == 0 and json.loads(out)['voice_page_url'] == 'https://x.example/runs/VW-9/voices2' and 'https://x.example/runs/VW-9/voices2' in err
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'stage': 'media'})
    with pytest.raises(SystemExit):
        vw.cmd_next(argparse.Namespace(take_over=False))
    assert 'voice_page_url' not in json.loads(capsys.readouterr()[0])


def test_voice_steps_say_the_link_and_the_automatic_save():
    steps = ' '.join(STAGES['voice']['steps'])
    assert 'voice_page_url' in steps and 'saved to the account automatically' in steps


def test_catalog_offers_the_page_link_with_the_same_filters(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'server_url', lambda: 'https://x.example')
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'voices': [], 'has_more': False})
    code, out, err = run(args(what='catalog', scope='library', gender='male', age='middle_aged', accent='indian', language='en', search='measured'), capsys)
    assert code == 0 and out['voice_page_url'] == 'https://x.example/runs/VW-9/voices2?browse=1&scope=library&language=en&accent=indian&gender=male&age=middle_aged&search=measured'
    assert 'voices page with these filters' in err


def test_voice_steps_make_the_page_the_default():
    steps = ' '.join(STAGES['voice']['steps'])
    assert 'the voices page is the default' in steps.lower()


# ---------- design/54: test passages with the direction; the page link goes to /voices2; direction comes first ----------

def test_direct_prepare_numbers_the_words_for_passages(harness, monkeypatch, capsys):
    full = {'procedure_version': '2', 'next': {'stage': 'voice', 'voice_page': {}}, 'outputs': [{'stage': 'brief', 'unit': None, **BRIEF}]}
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: full if '/api/runs/' in path else STAGES['voice'])
    code, out, err = run(args(step='prepare'), capsys)
    rows = out['inputs']['sentences']
    assert [(r['first_word'], r['last_word']) for r in rows] == [(1, 4), (5, 6), (7, 9)] and out['inputs']['words'] == 9
    assert 'test passages' in out['prompt'].lower() or 'TEST PASSAGES' in out['prompt']


def test_direct_record_sends_the_passages_and_the_choice(harness, monkeypatch, capsys):
    ws = harness
    doc = {**DIRECTION, 'test_passages': [{'passage_id': 'P001', 'first_word': 1, 'last_word': 6, 'why': 'the turn'}, {'passage_id': 'P002', 'first_word': 7, 'last_word': 9, 'why': 'the close'}]}
    (ws / 'out' / 'direction.json').write_text(json.dumps(doc), encoding='utf-8')
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append(body) or {'chosen': 'best_fit', 'digest': 'dd', 'items': 1, 'passage': 2})
    code, out, err = run(args(step='record', choice='best_fit', passage=2, quote='the careful one, passage two'), capsys)
    assert code == 0 and posted[0]['passage'] == 2 and posted[0]['test_passages'] == doc['test_passages']
    code, out, _ = run(args(step='record', choice='best_fit', passage=5, quote='x'), capsys)
    assert code == 2 and 'passage' in out['message']
    code, out, _ = run(args(step='record', choice='best_fit', passage=None, quote='x'), capsys)
    assert code == 2 and '--passage' in out['message']


def test_page_link_points_at_the_new_page_and_the_steps_put_the_direction_first():
    assert vw.voice_page_url('VW-9').endswith('/runs/VW-9/voices2')
    steps = STAGES['voice']['steps']
    assert 'direct prepare' in steps[1] and 'test passage' in steps[1].lower() and '--passage' in steps[1]
    assert 'voices page' in steps[2].lower() and 'default' in steps[2].lower()
    assert 'TEST PASSAGES' in STAGES['voice']['direction_prompt'] and '"test_passages"' in STAGES['voice']['direction_prompt']
