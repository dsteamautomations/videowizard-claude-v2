"""design/204: `vw visuals page`, with the server faked. It writes each round as one file for the page, keeps the page's link for the run, and
sends the answers the page's list saved in the run folder, once."""
import json

from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

LINE = {'line': 'l01', 'key': 'direction', 'item': 'treatment:direction:abc', 'title': 'The direction of the film', 'state': 'open', 'rows': [['The idea', 'Fewer bricks.']], 'text': '',
        'buttons': [{'label': 'Accept', 'choice': 'accept', 'needs_words': False}]}


def page(rnd, lines=(LINE,), open_=True):
    return {'step': 'Treatment', 'round': rnd, 'how': 'HOW', 'capabilities': {'db': {}}, 'title': 'VideoWizard decisions VW-9', 'open': open_, 'lines': list(lines),
            'summary': '2 gaps', 'note': 'The 2 gap lines appear after the Direction is accepted.'}


def test_page_writes_the_round_as_one_file_and_says_to_publish_first(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: calls.append((path, body)) or page('r1'))
    code, out, err = run(args(what='page', record=False), capsys)
    doc = json.loads((ws / 'work' / 'page' / 'r1.json').read_text(encoding='utf-8'))
    assert code == 0 and calls[0][0].endswith('/visuals/page') and doc['round'] == 'r1' and doc['lines'] == [LINE] and doc['run'] == 'VW-9' and doc['at']
    assert out['url'] == '' and out['round_file'].endswith('r1.json') and out['answers_collection'] == 'rounds/r1/answers' and out['page_file'].endswith('decisions.html')
    assert out['waiting'] == 1 and 'Publish the page first' in err and (ws / 'work' / 'page' / 'current.txt').read_text(encoding='utf-8').strip() == 'r1'


def test_the_pages_link_is_kept_for_the_run_and_given_back(harness, monkeypatch, capsys):
    ws, _ = harness
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: page('r1'))
    code, out, err = run(args(what='page', url='https://claude.ai/artifact/abc', record=False), capsys)
    assert code == 0 and out == {'url': 'https://claude.ai/artifact/abc'}
    code, out, err = run(args(what='page', record=False), capsys)
    assert out['url'] == 'https://claude.ai/artifact/abc' and 'Page: https://claude.ai/artifact/abc' in err


def test_record_sends_what_the_answer_files_hold_once_and_writes_the_next_round(harness, monkeypatch, capsys):
    ws, _ = harness
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: page('r1'))
    run(args(what='page', record=False), capsys)
    answers = ws / 'work' / 'page' / 'answers' / 'rounds' / 'r1' / 'answers'
    answers.mkdir(parents=True)
    (answers / 'l01.json').write_text(json.dumps({'key': 'direction', 'item': 'treatment:direction:abc', 'choice': 'change', 'notes': 'tell it from the family', 'at': 'x'}), encoding='utf-8')
    (answers / 'l02.json').write_text(json.dumps({'data': {'key': 'G1', 'item': 'treatment:G1:def', 'choice': 'accept'}}), encoding='utf-8')   # either shape of a saved document
    (answers / 'l03.json').write_text('not json', encoding='utf-8')
    sent = []

    def write(path, body, wait=None):
        sent.append((path, body))
        return {'recorded': ['direction'], 'stale': [], 'refused': [], 'dropped': ['G1'], 'then': 'Revise the lines that are back with you.', 'page': page('r2', (), True)}
    monkeypatch.setattr(vw, 'write', write)
    code, out, err = run(args(what='page', record=True), capsys)
    assert code == 0 and sent[0][0].endswith('/visuals/page/record')
    assert sent[0][1]['answers'] == [{'line': 'l01', 'key': 'direction', 'item': 'treatment:direction:abc', 'choice': 'change', 'notes': 'tell it from the family'},
                                     {'line': 'l02', 'key': 'G1', 'item': 'treatment:G1:def', 'choice': 'accept', 'notes': ''}]
    assert out['round'] == 'r2' and out['recorded'] == ['direction'] and 'dropped with the Direction: G1' in err and (ws / 'work' / 'page' / 'r2.json').is_file()
    assert not answers.exists() and (answers.parent / 'answers.sent' / 'l01.json').is_file()   # set aside: never sent again from an old file


def test_record_before_any_round_is_refused(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (_ for _ in ()).throw(AssertionError('nothing is sent')))
    code, out, err = run(args(what='page', record=True), capsys)
    assert code == 2 and 'vw visuals page' in out['message']


def test_a_direction_sent_alone_prints_what_the_server_says_comes_next(harness, monkeypatch, capsys):
    """design/205: the Direction alone first; the tool never sends the assistant to the card after it."""
    ws, _ = harness
    (ws / 'out').mkdir(exist_ok=True)
    (ws / 'out' / 'visual-treatment.json').write_text(json.dumps({'direction_parts': {'idea': 'Fewer bricks.'}}), encoding='utf-8')
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append(body) or {'draft': True, 'direction_only': True, 'next': 'The Direction alone is with the operator: `vw visuals page`.'})
    code, out, err = run(args(what='treatment', file='out/visual-treatment.json'), capsys)
    assert code == 0 and 'gaps' not in sent[0]['document'] and '`vw visuals page`' in err and 'vw visuals next' not in err
