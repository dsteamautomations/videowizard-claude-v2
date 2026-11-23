"""Fix set, part 2 (SK, 20 Nov 2026), the server's side: the page is never empty, and its link is given only when it is filled.

(a) a round with pictures comes with `loading`: what the page says while its pictures are sent, the minutes the server states, and the sentence
for a load that takes longer; (b), (d) `how` puts the loading note first, the link last, and names the one path for a publish that fails or goes
to another link; (f) the round of step 6 and of step 7 says how many of the step's things are on the page, lists the ones answered earlier, and
the answer names a thing that is made and has no line. Without a database."""
import io
from app import core as _core   # SK, 23 Nov 2026: v3.json is read as a film with footage is served it
import json
import sys
from pathlib import Path

from PIL import Image

from app import chat_flow as CF, page_flow as PF, pictures as P, takes as T

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_shared_change as H   # noqa: E402


def png():
    out = io.BytesIO()
    Image.new('RGB', (800, 600), 'navy').save(out, 'PNG')
    return out.getvalue()


# ---------- (a) what the page says while its pictures are sent ----------

def test_a_round_with_pictures_comes_with_the_loading_note_the_minutes_and_the_late_sentence():
    store = H.Store()
    lines = []
    for n in range(19):
        store.put(f'r1/{n}.png', png())
        lines.append({'title': f'Thing {n}', 'state': 'open', 'pics': [PF.pic(f'r1/{n}.png', 'Front')]})
    got = PF._with_pictures(store, {'step': 'Pictures and drawn graphics', 'lines': lines})
    assert got['preparing'] == 'Preparing 19 pictures for the page, about 2 minutes.'
    assert got['loading'] == {'note': 'The pictures of this step are being loaded: 19 lines, about 2 minutes. This page fills itself: there is no need to reload it.',
                              'late': LATE, 'minutes': 2, 'expected': 19, 'late_after': 10}
    one = PF._with_pictures(store, {'lines': lines[:1]})['loading']
    assert one['minutes'] == 1 and one['expected'] == 1 and '1 line, about 1 minute.' in one['note']


LATE = 'This is taking longer than expected. Nothing is lost and the page still fills itself: wait a little longer, or ask the assistant once its turn in the chat has ended.'


def test_a_load_is_late_only_after_ten_minutes_or_three_times_the_minutes_stated():
    """The critic's point 1: the minutes stated cover the server's copies only; the laptop's fetch, the uploads and the round come after them."""
    assert [PF.late_after(m) for m in (1, 2, 3, 4, 7)] == [10, 10, 10, 12, 21]
    assert 'interrupt' not in LATE and CF.WORDS['loading_late'] == LATE and 'ask the assistant in the chat.' not in LATE


def test_a_round_with_no_picture_has_no_loading_note():
    assert 'loading' not in PF._with_pictures(H.Store(), {'lines': [{'title': 'A gap', 'state': 'open'}]})


# ---------- (b), (d) the order the assistant is told ----------

def test_how_puts_the_loading_note_first_the_link_last_and_names_one_path_for_a_failed_publish():
    how = PF.HOW
    assert how.index('loading_write') < how.index('picture_batches') < how.index('collection "rounds"') < how.index('after_round') < how.index('Say to the operator `say`, exactly as it is, then the link')
    assert 'only once `vw visuals page --shown` has printed it' in how and 'one progress line, without the link' in how
    assert ('If a publish fails, or its answer names another link than `url`, stop: never go on with a new page. Tell the operator that the page is not available, '
            'run `vw visuals next` and ask this step in the chat.') in how
    assert 'If `republish` is true' in how and 'as soon as an answer of the tool says so' in how   # (c): done early, checked again when the page is wanted
    assert how.count('`loading_write`') == 1 and how.count('`after_round`') == 2


# ---------- (f) every finished item is offered and counted ----------

def item(kind, sid, state, **more):
    return {'kind': kind, 'id': sid, 'name': f'The {sid}', 'state': P.STATE[state], **more}


def line(ident, name):
    return {'key': 'pic:' + ident, 'item': ident, 'state': 'open', 'kind': 'x', 'name': name, 'pics': [], 'details': []}


SESSION = {'references': {'K1': {'id': 'K1', 'shot_id': 'IM1'}}}
SIX = [item('drawn', 'MO1', 'done', job={'id': 'job-8'}), item('still', 'IM1', 'done'), item('steps', 'GS1', 'done'), item('still', 'IM2', 'answered'), item('still', 'IM3', 'failed'),
       item('component', 'E1', 'done')]
LINES = [line('question:K9', 'A question'), line('take:job-8', 'The MO1'), line('picture:K1:aaaaaaaaaa', 'The IM1'), line('graphics:GS1:3', 'The GS1')]


def test_the_round_of_step_6_says_how_many_are_on_the_page_and_lists_the_ones_answered_earlier():
    page = PF._pictures_page({'session': SESSION}, {}, [dict(l) for l in LINES], SIX)
    lay = page['layout']
    assert lay['count'] == '5 of 5 pictures and drawn graphics are on this page.'   # three to answer, one answered earlier, one that could not be made; a component is never a line
    assert lay['recorded'] == [{'name': 'The IM2', 'kind_words': 'A still', 'state': 'answered', 'note': 'Answered earlier, in the chat.'}]
    assert lay['words']['pictures']['recorded'] == 'Answered earlier' and 'not_on_page' not in page
    assert len(page['lines']) == 4   # a question is a line and is not one of the step's things


def test_a_thing_that_is_made_and_has_no_line_is_named_never_left_out_silently():
    page = PF._pictures_page({'session': SESSION}, {}, [dict(l) for l in LINES if 'job-8' not in l['item']], SIX)
    assert page['layout']['count'] == '4 of 5 pictures and drawn graphics are on this page.'
    assert page['not_on_page'] == ('Not on the page: The MO1 (made and checked). Tell the operator which, and ask about them in the chat (`vw visuals next`): '
                                   'never leave them out silently.')
    old = PF._pictures_page({'session': SESSION}, {}, [dict(l) for l in LINES[:1]] + [line('take:job-7', 'The MO1')], SIX)   # a line of a render that is not the one counted
    assert 'The MO1 (made and checked)' in old['not_on_page']


def test_a_thing_whose_only_line_is_an_open_question_is_on_the_page():
    """The critic's point 6a: a question about a made picture is asked in the picture's place; the picture is not missing."""
    lines = [line('question:K1', 'A question about the IM1'), line('question:GS1', 'A question about the GS1'), line('take:job-8', 'The MO1')]   # by its picture, and by its shot
    page = PF._pictures_page({'session': SESSION}, {}, lines, SIX)
    assert page['layout']['count'] == '5 of 5 pictures and drawn graphics are on this page.' and 'not_on_page' not in page


def test_a_thing_with_a_line_is_not_also_listed_as_answered_earlier():
    """The critic's point 6b: a render selected before a re-render is asked again on the new render: one place on the page, its line."""
    six = [item('steps', 'GS1', 'answered'), item('drawn', 'MO1', 'answered'), item('still', 'IM2', 'answered')]
    page = PF._pictures_page({'session': SESSION}, {}, [line('graphics:GS1:3', 'The GS1'), line('take:job-9', 'The MO1')], six)   # MO1's new render: its job is not in the list, its name is
    assert [r['name'] for r in page['layout']['recorded']] == ['The IM2'] and page['layout']['count'] == '3 of 3 pictures and drawn graphics are on this page.'


def test_a_round_with_no_list_of_the_step_is_as_before():
    page = PF._pictures_page({'session': {}}, {}, [line('picture:K1:aaaaaaaaaa', 'One')], [])
    assert 'count' not in page['layout'] and 'recorded' not in page['layout'] and 'not_on_page' not in page


def test_the_round_of_step_7_counts_its_takes_and_the_ones_answered_earlier_are_lines():
    seven = [{'kind': 'take', 'id': 'S1', 'name': 'Shot one', 'state': T.STATE['done'], 'job': {'id': 'j1'}}, {'kind': 'take', 'id': 'S2', 'name': 'Shot two', 'state': T.STATE['answered']},
             {'kind': 'take', 'id': 'S3', 'name': 'Shot three', 'state': T.STATE['done'], 'job': {'id': 'j3'}}]
    lines = [{**line('take:j1:abcdef12', 'Shot one'), 'takes': []}, {'key': 'pic:take-done:S2', 'item': 'take-done:S2', 'state': 'recorded', 'name': 'Shot two', 'takes': [], 'pics': []}]
    page = PF._takes_page({'session': {}}, {}, lines, seven)
    assert page['layout']['count'] == '2 of 3 AI video shots are on this page.' and 'Not on the page: Shot three (made).' in page['not_on_page']
    full = PF._takes_page({'session': {}}, {}, lines + [{**line('take:j3:abcdef12', 'Shot three'), 'takes': []}], seven)
    assert full['layout']['count'] == '3 of 3 AI video shots are on this page.' and 'not_on_page' not in full


def test_the_served_text_and_the_command_text_say_it_and_the_replaced_sentences_are_retired():
    import fixset5_wording as W
    stage = next(s for s in _core.for_footage(json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8')), 'own')['stages'] if s['name'] == 'visuals')
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    assert stage['prompt'].count(W.SAY_NEW) == 1 and W.SAY_NEW not in W.before(stage)['prompt'] and W.before(stage)['prompt'].count(W.SAY) == 1
    for said in ('only when `vw visuals page --shown` prints it', 'When the tool says `republish_now`', 'is never a new page'):
        assert said in stage['prompt'], said
    md = (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8').replace('\r\n', '\n')
    for file, old, new in W.HELPERS:
        assert md.count(new) == 1 and old not in md.replace(new, ''), old[:50]
    everything = stage['prompt'] + ''.join(p['text'] for p in stage['parts'])
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired and s not in everything and s not in md for s in W.RETIRED)
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('fixset4(prompt, parts)') < split.index('fixset5(prompt, parts)')


def test_the_words_and_the_older_ways_are_in_the_decision_log():
    assert CF.WORDS['loading'].startswith('The pictures of this step are being loaded') and CF.WORDS['loading_late'].startswith('This is taking longer than expected')
    log = (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8')
    assert all(f'| {n} |' in log for n in range(265, 271))
    for name in ('loading_write', '--shown', '--new-page', 'republish_now', 'not_on_page', 'layout.count'):
        assert name in log.split('| 265 |', 1)[1], name
    assert json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
