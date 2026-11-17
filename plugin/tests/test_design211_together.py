"""design/211, the plugin side of the three parts together (the merger): every `vw visuals …` command the two helper files and the
instructions of the references step name is one the tool's parser takes, with flags its subcommand reads; the guard allows the two helpers
and exactly the calls their files tell them to make; and each new call of the tool reaches a route the server has, with a body the
server's own model accepts (skipped where the server's packages are not installed)."""
import json
import os
import re
import shlex
import sys
import typing

import pytest

from conftest import PLUGIN, REPO, run_hook
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

VW = PLUGIN / 'scripts' / 'vw.py'
FINDER = (PLUGIN / 'agents' / 'vw-reference-finder.md').read_text(encoding='utf-8')
LOOKER = (PLUGIN / 'agents' / 'vw-set-look.md').read_text(encoding='utf-8')
CMD = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
V3 = next(s for s in json.loads((REPO / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
SEARCH = next(p['text'] for p in V3['parts'] if p['name'] == 'picture-search')
PARSER = vw.build_parser()


def named(text):
    """The `vw visuals …` commands a text names in backticks, placeholders filled in."""
    out = []
    for c in re.findall(r'`(vw visuals [^`]+)`', text):
        c = re.sub(r'\[[^\]]*\]', '', c)                       # an optional part, as `[--golden <picture>]`
        c = re.sub(r'"<[^>]*>"|<[^>]*>|…', '1', c)             # a placeholder
        out.append(shlex.split(c)[1:])
    return out


def takes(words):
    for given in (words, words + ['1'] if words[-1].startswith('--') else words):   # a flag may be named without its value, as `vw visuals trial --file`
        try:
            return not vw.visuals_flags_refused(PARSER.parse_args(given))
        except SystemExit:
            pass
    return False


# ---------- the commands the texts name ----------

TEXTS = {'vw-reference-finder.md': FINDER, 'vw-set-look.md': LOOKER, 'the picture search of version 3': SEARCH, 'commands/vw.md': CMD}


@pytest.mark.parametrize('name', sorted(TEXTS))
def test_every_command_a_text_names_is_one_the_tool_takes(name):
    for words in named(TEXTS[name]):
        assert takes(words), (name, ' '.join(words))
    assert not takes(['visuals', 'round', '--lookz']) and not takes(['visuals', 'digest', '--file', 'x.json'])   # the test can fail


def test_the_helper_files_name_their_own_commands_and_no_other():
    assert sorted({' '.join(w[:3]) for w in named(FINDER)}) == ['visuals look --file', 'visuals trial --file']
    assert sorted({' '.join(w[:3]) for w in named(LOOKER)}) == ['visuals round --looks']
    for text in (FINDER, LOOKER):   # a helper approves nothing, orders nothing and writes no round file
        assert not re.search(r'`vw visuals (approve|image|round --(file|rest|rewrite|make|verdicts|sets)|page|next|decide)', text)
    for said in ('`vw visuals digest`', '`vw visuals trial --file`', '`vw visuals look --file`', '`vw visuals round --looks`', '`vw visuals round --looks <file>`',
                 '`vw visuals round --rewrite out/round-rewrites.json`', '`vw visuals round --rest --quote`', '`vw visuals round --make E --quote`', '`vw-reference-finder` helpers', '`vw-set-look` helpers'):
        assert said in SEARCH, said
    assert '`vw-reference-finder` and `vw-set-look`' in CMD   # The web: the two helpers the steps name


# ---------- the guard ----------

def guard(tool, tool_input, cwd):
    return run_hook('guard.py', {'tool_name': tool, 'tool_input': tool_input}, cwd)[0]


def test_the_guard_allows_the_two_helpers_and_the_calls_their_files_name(ws, tmp_path):
    for helper in ('vw:vw-reference-finder', 'vw-reference-finder', 'vw:vw-set-look', 'vw-set-look'):
        assert guard('Agent', {'subagent_type': helper, 'prompt': 'g1: TROWEL, TILE'}, tmp_path) == 0, helper
    assert guard('Agent', {'subagent_type': 'vw-look', 'prompt': 'g1'}, tmp_path) == 2
    # the finder: reads the things and the digest, writes its two files, sends them, reads each trial frame
    # the looker: reads the list and the pictures, writes its looks, sends them
    for rel in ('work/visuals/refs/things.json', 'work/visuals/digest/index.json', 'work/visuals/digest/clips-1.json', 'work/visuals/trials/TROWEL/t0000000000a1.jpg',
                'work/visuals/sets/looks.json', 'work/visuals/sets/TROWEL/picture-1.jpg', 'work/visuals/sets/TROWEL/input-1.jpg'):
        assert guard('Read', {'file_path': str(ws / rel)}, tmp_path) == 0, rel
    for rel in ('work/visuals/refs/g1.trials.json', 'work/visuals/refs/g1.looks.json', 'work/visuals/sets/g1.looks.json', 'out/reference-round.json', 'out/round-rewrites.json'):
        assert guard('Write', {'file_path': str(ws / rel), 'content': '{}'}, tmp_path) == 0, rel
    for text in (FINDER, LOOKER, SEARCH):
        for words in named(text):
            line = ' '.join(shlex.quote(w) for w in words).replace("'1'", '1')
            assert guard('Bash', {'command': f'python "{VW}" {line}'}, tmp_path) == 0, line
    for line in ('visuals trial --file work/visuals/refs/g1.trials.json', 'visuals look --file work/visuals/refs/g1.looks.json', 'visuals round --looks work/visuals/sets/g1.looks.json',
                 'visuals digest', 'visuals round --looks', 'visuals round --rest --quote "yes, make the others"', 'visuals round --rewrite out/round-rewrites.json', 'visuals page'):
        assert guard('Bash', {'command': f'python "{VW}" {line}'}, tmp_path) == 0, line
    # and nothing more: a file outside the run folder, another program, two commands in one call
    assert guard('Write', {'file_path': str(tmp_path / 'g1.looks.json'), 'content': '{}'}, tmp_path) == 2
    assert guard('Bash', {'command': 'ffmpeg -i clip.mp4 frame.jpg'}, tmp_path) == 2
    assert guard('Bash', {'command': f'python "{VW}" visuals look --file work/visuals/refs/g1.looks.json && python "{VW}" visuals round --file out/reference-round.json'}, tmp_path) == 2


# ---------- each new call against the server's routes and models ----------

def put(ws, rel, value):
    (ws / rel).parent.mkdir(parents=True, exist_ok=True)
    (ws / rel).write_text(json.dumps(value), encoding='utf-8')


def test_each_new_call_reaches_a_route_the_server_has_with_a_body_it_accepts(harness, monkeypatch, capsys):
    pytest.importorskip('fastapi')
    sys.path.insert(0, str(REPO / 'server'))
    os.environ.setdefault('VW2_DATABASE_URL', '')
    try:
        from app import main
    except Exception as exc:   # the server's packages are not all on this machine
        pytest.skip(f'the server cannot be imported here: {exc}')
    ws, _ = harness
    routes = {(m, r.path): r for r in main.app.routes for m in getattr(r, 'methods', None) or ()}
    sent = []

    def call(method, path, wait=None, **kw):
        sent.append((method, path.replace('/api/runs/run-1/', '/api/runs/{run_id}/'), kw.get('json')))
        return {'then': 'next', 'sets': [], 'digest': {'clips': []}, 'things': [], 'trials': [], 'page': {'lines': []}}
    monkeypatch.setattr(vw, 'call', call)
    monkeypatch.setattr(vw, '_download', lambda *a, **k: None)
    put(ws, 'work/visuals/refs/g1.trials.json', [{'element': 'TROWEL', 'clip': 'C001', 'at': 30.2}])
    put(ws, 'work/visuals/refs/g1.looks.json', {'by': 'helper', 'things': [{'element': 'TROWEL', 'clips': ['C001'], 'note': 'seen', 'looks': [{'trial': 't1', 'view': 'side', 'verdict': 'pass', 'seen': 'whole', 'keep': True}]}]})
    put(ws, 'work/visuals/sets/g1.looks.json', {'by': 'helper', 'sets': [{'element_id': 'STREET', 'set': 's1', 'recommend': 'use', 'golden': 's1', 'reason': 'fine', 'pictures': [{'ref': 's1', 'view': 'whole', 'verdict': 'pass', 'seen': 'ok'}]}]})
    put(ws, 'out/round-rewrites.json', [{'element_id': 'T_LAY', 'prompt': 'The hand presses the brick.'}])
    put(ws, 'out/reference-round.json', [{'element_id': 'TROWEL', 'rec': 'footage', 'reason': 'Seen whole.', 'first': True, 'prompt': ''}])
    put(ws, 'out/round-verdicts.json', {'TROWEL': {'verdict': 'clean', 'words': 'Show the blade clean.'}})
    want = [({'what': 'digest'}, 'GET', '/visuals/digest'),
            ({'what': 'trial', 'file': 'work/visuals/refs/g1.trials.json'}, 'POST', '/visuals/trials'),
            ({'what': 'trial', 'element': 'TROWEL', 'clip': 'C001', 'at': '6.4'}, 'POST', '/visuals/trials'),
            ({'what': 'look', 'file': 'work/visuals/refs/g1.looks.json'}, 'POST', '/visuals/looks'),
            ({'what': 'round', 'file': 'out/reference-round.json'}, 'POST', '/visuals/round'),
            ({'what': 'round', 'verdicts': 'out/round-verdicts.json', 'quote': 'done'}, 'POST', '/visuals/round/done'),
            ({'what': 'round', 'looks': True}, 'GET', '/visuals/round/looks'),
            ({'what': 'round', 'looks': 'work/visuals/sets/g1.looks.json'}, 'POST', '/visuals/round/looks'),
            ({'what': 'round', 'rest': True, 'quote': 'yes, make the others'}, 'POST', '/visuals/round/rest'),
            ({'what': 'round', 'rewrite': 'out/round-rewrites.json'}, 'POST', '/visuals/round/rewrite'),
            ({'what': 'round', 'make': 'FAN', 'quote': 'make it'}, 'POST', '/visuals/round/make')]
    for kw, method, tail in want:
        del sent[:]
        code, _out, err = run(args(**kw), capsys)
        assert code == 0 and err.strip().endswith('next'), (kw, err)             # the server's `then` is the tool's one sentence
        (m, path, body), = [s for s in sent if s[1].endswith(tail)]
        assert m == method and (m, path) in routes, (kw, m, path)
        if method == 'POST':
            model = typing.get_type_hints(routes[(m, path)].endpoint)['body']
            model.model_validate(body)                                           # the server's own model takes it; an unknown field is refused there
    looks = [s for s in want if s[2] == '/visuals/looks']
    assert looks and main.Looks.model_fields['by'].is_required()
    # an answer of the page with a picture answered on its own
    main.PageAnswers.model_validate({'request_id': '00000000-0000-0000-0000-000000000001',
                                     'answers': [{'line': 'l01', 'key': 'ref:TROWEL', 'item': 'round1:TROWEL', 'choice': 'pics', 'notes': '', 'pics': {'f-trowel-use': 'not'}}]})


def test_vw_next_prints_the_servers_sentence_while_a_v2_round_waits_for_the_assistant(harness, monkeypatch, capsys):
    answer = {'item': None, 'needed': False, 'working': [], 'say_last': 'Nothing is needed from you now.', 'how': 'h'}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: dict(answer, then='The sets are back. Look at them before the operator does.'))
    code, out, err = run(args(what='next', one=False), capsys)
    assert code == 0 and err.strip() == 'Nothing is needed from you now. The sets are back. Look at them before the operator does.'
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: dict(answer))   # an older round, or nothing for the assistant to do: as before
    assert run(args(what='next', one=False), capsys)[2].strip() == 'Nothing is needed from you now.'
