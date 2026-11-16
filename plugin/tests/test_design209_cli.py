"""design/209: the tool's lines for the drawings and the materials approved on the page, with the server faked: the page command names the
step the server gives, the chat item of a drawing or a material points to the page first, and the check says what the reference sets may cost."""
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

LINE = {'line': 'l01', 'key': 'G1-S1', 'item': 'spec:G1-S1:abc', 'title': 'The box, cut open', 'state': 'open', 'ask': 'Are the parts and the known sizes right?',
        'spec': {'parts': ['box', 'lid'], 'sizes': [['box', 'length', '600 mm', "the maker's sheet"]], 'known': 1},
        'buttons': [{'label': 'Yes', 'choice': 'yes', 'needs_words': False}, {'label': 'Correct it', 'choice': 'correct', 'needs_words': True}]}


def test_the_page_command_names_the_step_of_the_drawings_and_materials(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'step': 'Drawings and materials', 'round': 'r1', 'how': 'HOW', 'capabilities': {'db': {}}, 'title': 'VideoWizard decisions VW-9',
                                                                     'open': True, 'lines': [LINE], 'summary': '1 drawing: 1 to answer, 0 recorded, 0 with the assistant.',
                                                                     'note': 'Answer each line, then say done in the chat.'})
    code, out, err = run(args(what='page', record=False), capsys)
    assert code == 0 and err.startswith('Drawings and materials page: 1 line(s) to answer. Answer each line, then say done in the chat.') and out['waiting'] == 1


def test_a_drawing_asked_in_the_chat_points_to_the_page_first(harness, monkeypatch, capsys):
    item = {'id': 'spec:G1-S1:abc', 'kind': 'spec', 'position': '1 of 1 waiting', 'question': 'The box, cut open: are the parts right?', 'ask': 'Are the parts right?',
            'buttons': [{'label': 'Yes', 'choice': 'yes'}], 'how': 'HOW', 'show': []}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'item': dict(item)})
    code, out, err = run(args(what='next', one=False), capsys)
    assert code == 0 and err.startswith('The drawings and the materials are approved on the page, in one visit: run `vw visuals page` instead; ask here only where the page cannot be shown. 1 of 1 waiting.')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'item': {**item, 'kind': 'picture'}})
    assert 'on the page' not in run(args(what='next', one=False), capsys)[2]


def test_the_check_line_says_what_the_reference_sets_may_cost(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'out' / 'visual-plan.json').write_text('{}', encoding='utf-8')
    answer = {'status': 'valid', 'warnings': [], 'routes': {'video': 1, 'still': 1, 'graphic_sequence': 0, 'seconds': {}, 'images_estimated': 5}}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {**answer, 'budget': {'cap_inr': 5000.0, 'planned_inr': 1144.0, 'sets': 49, 'sets_inr': 1733.42}})
    assert ', about ₹1,144 for the shots, and up to ₹1,733 for 49 reference sets, against cap ₹5,000' in run(args(what='check', file='out/visual-plan.json'), capsys)[2]
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {**answer, 'budget': {'cap_inr': 5000.0, 'planned_inr': 1144.0, 'sets': 0, 'sets_inr': 0.0}})
    assert ', about ₹1,144 against cap ₹5,000' in run(args(what='check', file='out/visual-plan.json'), capsys)[2]
