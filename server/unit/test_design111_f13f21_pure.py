"""design/111 F13 and F21. F13: words to be read go only through the exact-text field, each entry with its text, its place (a landmark or a frame region)
and its size; an entry with no place is refused; quoted words outside the field are refused; "reads exactly", "where the entry says" and "no other
lettering" are checked on every picture with exact text. F21: at most four pictures go in with a prompt and each has one job line."""
import json
from pathlib import Path

import pytest

from app import library as L, visuals_stage as VS
from app.errors import Problem
from test_design106_pure import revise_start, start_store
from test_visuals_stage_pure import RUN, USER, FakeConn, g, ref, saved

ROOT = Path(__file__).resolve().parents[1]
ENTRY = {'text': 'Brick strength', 'place': {'region': 'lower third, inside the safe area, left-aligned'}, 'size_pct': 6}
ON = {'text': 'ACC', 'place': {'landmark_id': 'L2'}, 'size_pct': 4}


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def put(store, s):
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')


# ---------- F13: the entries ----------

def test_an_exact_text_entry_carries_its_place_and_size_and_the_old_bare_string_is_refused_on_a_new_picture():
    assert L.exact_entries({'exact_text': [ENTRY, 'air']}) == [ENTRY, {'text': 'air', 'place': None, 'size_pct': None}]
    assert L.exact_entries({}) == [] and L.exact_entries({'exact_text': ['']}) == []
    with pytest.raises(ValueError, match="'Brick strength' is not in the prompt"):
        L.check_answer({'status': 'ready', 'prompt': 'A title card.', 'checklist': [{'check': 'w', 'pass_when': 'reads', 'weight': 'must'}], 'exact_text': [ENTRY]}, 'A title card.')
    L.check_answer({'status': 'ready', 'prompt': 'A title card: Brick strength.', 'checklist': [{'check': 'w', 'pass_when': 'reads', 'weight': 'must'}], 'exact_text': [ENTRY]}, 'A title card: Brick strength.')
    with pytest.raises(ValueError, match='has no place'):
        L.check_exact_places({'exact_text': ['air']}, {'L2'})
    with pytest.raises(ValueError, match='L9 is not a landmark'):
        L.check_exact_places({'exact_text': [{**ON, 'place': {'landmark_id': 'L9'}}]}, {'L2'})
    with pytest.raises(ValueError, match='size'):
        L.check_exact_places({'exact_text': [{**ENTRY, 'size_pct': None}]}, set())
    L.check_exact_places({'exact_text': [ENTRY, ON]}, {'L2'})


def test_quoted_words_outside_the_exact_text_field_are_refused():
    with pytest.raises(ValueError, match="quoted words 'Brick strength' are not an exact-text entry"):
        L.check_quoted('A title card reading "Brick strength" in white.', [])
    L.check_quoted('A title card reading "Brick strength" in white.', [ENTRY])
    L.check_quoted("The mason's trowel, the 'pointing' done.", [])   # a one-word quote is a word, not lettering to render
    L.check_quoted('No quotes here.', [])


def test_every_picture_with_exact_text_is_checked_for_the_words_their_place_and_no_other_lettering():
    lines = VS.exact_text_lines({'exact_text': [ENTRY, ON]}, {'L2': 'the cement bag at right'})
    assert [l['check'] for l in lines] == ['reads: Brick strength', 'placed: Brick strength', 'reads: ACC', 'placed: ACC', 'no other lettering']
    assert lines[0]['pass_when'] == 'the words read exactly "Brick strength", spelled as written' and 'lower third, inside the safe area, left-aligned' in lines[1]['pass_when'] and '6 %' in lines[1]['pass_when']
    assert 'on the cement bag at right' in lines[3]['pass_when'] and lines[4]['weight'] == 'must'
    assert VS.exact_text_lines({'exact_text': []}, {}) == []


def test_a_keyframe_with_exact_text_carries_the_render_line_and_the_checks_and_a_bare_string_is_refused():
    store = start_store()
    answer = {'status': 'ready', 'prompt': 'Image 1 is the old start; the labourer at the stack, a sack reading ACC. Image 2 is the sheet.', 'checklist': [{'check': 'w', 'pass_when': 'reads', 'weight': 'must'}],
              'exact_text': [ON]}
    out = revise_start(store, role='start', prompt=answer['prompt'], answer=answer, end_prompt=None, end_answer=None, request_id='r-text')
    row = saved(store)['references'][out['reference_id']]
    assert 'Render exactly this text, letter for letter, nothing else: "ACC"' in row['generation']['prompt'] and 'no other letters, numbers or logos anywhere' in row['generation']['prompt']
    assert [l['check'] for l in row['server_checklist'] if l['check'].startswith(('reads', 'placed', 'no other'))] == ['reads: ACC', 'placed: ACC', 'no other lettering']
    with pytest.raises(Problem, match='has no place'):
        g(lambda: revise_start(store, role='start', prompt=answer['prompt'], answer={**answer, 'exact_text': ['ACC']}, end_prompt=None, end_answer=None, request_id='r-bare'))
    with pytest.raises(Problem, match='quoted words'):
        g(lambda: revise_start(store, role='start', prompt=answer['prompt'] + ' A board says "Site office".', answer={**answer, 'prompt': answer['prompt'] + ' A board says "Site office".'},
                               end_prompt=None, end_answer=None, request_id='r-quoted'))


# ---------- F21: one job line per picture; SK, 28 Oct 2026: the cap of four removed, the model's sixteen is the only ceiling ----------

def test_pictures_up_to_the_models_ceiling_pass_with_a_job_line_each():
    store = start_store()
    s = saved(store)
    for i in range(2, 20):
        s['references'][f'X{i}'] = {**ref(f'X{i}', 'approved'), 'kind': 'web', 'element_id': 'E1'}
    put(store, s)
    base = {'request_id': 'r-many', 'element_id': 'E1', 'name': 'keyframe-start-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer', 'role': 'start',
            'prompt': 'Image 1 is the old start. Image 2 is the sheet. Image 3 is a texture. Image 4 is a look. Image 5 is another.'}
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**base, 'parents': ['K1', 'X2', 'X3', 'X4', 'X5']})   # five, each with its line: allowed since 28 Oct
    assert out['reference_id']
    many = ['K1'] + [f'X{i}' for i in range(2, 18)]   # seventeen: past the model's own limit
    with pytest.raises(Problem, match='17 input pictures.*GPT Image takes at most 16'):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], {**base, 'request_id': 'r-17', 'parents': many, 'prompt': ' '.join(f'Image {k} is picture {k}: take its look.' for k in range(1, 18))}))
    with pytest.raises(Problem, match='does not say what Image 2 is for'):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], {**base, 'request_id': 'r-nojob', 'parents': ['K1', 'X2'], 'prompt': 'Image 1 is the old start; the labourer.'}))
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**base, 'request_id': 'r-four', 'parents': ['K1', 'X2', 'X3', 'X4'],
                                                                 'prompt': 'Image 1 is the old start: repeat it. Image 2 is the sheet: take identity. Image 3 is the brick texture: take only its surface. Image 4 is the look: take its light.'})
    assert out['reference_id']


def test_the_procedure_names_the_exact_text_entry_and_the_picture_rule():
    proc = (ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8')
    assert 'size_pct' in proc and 'at most four pictures' not in proc.lower() and 'Up to sixteen pictures' in proc and 'Render exactly this text' in proc
