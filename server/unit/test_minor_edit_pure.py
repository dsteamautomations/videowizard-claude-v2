"""Minor corrections as an edit, reference step 2 (SK, 25 Nov 2026; requirements "Approve as written", 26 Nov): "Minor corrections" on a set
sends the set's own pictures back to the image model with the operator's words and Claude's where line; it no longer makes a new set from words.

The eleven tests of the requirements' section 8 and one per edge case of its section 6, on the server's own functions and the image worker's.
The operator's marks reach the server from the page; the chat gives words alone. Without a database, a paid call or a call to any model: the
image model's answers are stood in for (`VW.httpx.post`)."""
import base64
import copy
import io
import json

import pytest
from PIL import Image

from app import chat_flow as CF, image_check, main, page_flow, ref_sets as RS, visual_workers as VW, visuals_stage as VS
import d211_fixture as F
from test_design151_refs_pure import Resp, png_bytes
from test_design151b_set_turns_pure import _settings, turn
from test_design211b_round_pure import at_two, back, film, finder, judge, look, post, put, refused, req, saved, state   # noqa: F401 (finder stands in for part A, on every test)
from test_design211b_sets_pure import RUN, Lock, el
from test_visuals_stage_pure import USER



@pytest.fixture(autouse=True)
def v2_round(_older_round_tests, monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', 2)   # conftest posts the older round for every module not named test_design211*; this one tests the round of design/211


WORDS, WHERE = 'Take the paint stains off the handle.', 'the wooden handle, at the lower right of the frame'
RECT = {'r': [0.5, 0.5, 0.25, 0.2]}


def pics(store, eid='T_LAY'):
    """The ids of the pictures of the thing's set now, in the set's order."""
    s = saved(store)
    return [p['id'] for p in RS._pictures(s, eid, s['round']['elements'][eid], ('candidate',))]


def asked(store, conn, eid='T_LAY', words=WORDS, **more):
    """The operator's "Minor corrections" on a set, recorded: what `round_sets` answers."""
    return judge(store, conn, {eid: {'verdict': 'correct', 'words': words, **more}})


def where(store, conn, eid='T_LAY', line=WHERE):
    return VS.guarded(lambda: RS.round_rewrite(conn, store, USER, RUN, [], [{'element_id': eid, 'where': line}]))


def ordered(marks=None, every=None):
    """A set of three, "Minor corrections" recorded and Claude's where line sent: (store, conn, the set before, the job's request)."""
    store, conn = at_two()
    before = pics(store)
    more = {**({'marks': {before[n - 1]: [RECT] for n in marks}} if marks else {}), **({'every': every} if every is not None else {})}
    asked(store, conn, **more)
    where(store, conn)
    return store, conn, before, req(conn.inserted[-1])


def worker(monkeypatch, tmp_path, request, answers):
    """The image worker on the edit's job: the set's pictures are in the store; `answers` are the image model's, one per call. Returns
    (what process_image gives, every body sent, the store)."""
    store = _settings(monkeypatch, tmp_path)
    for n, p in enumerate(request['parents'], 1):
        store.files[p['key']] = png_bytes(64, 36, (10, 10, 40 * n))
    sent = []
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append(copy.deepcopy(kw['json'])) or (answers[len(sent) - 1] if isinstance(answers[len(sent) - 1], Resp) else Resp(200, answers[len(sent) - 1])))
    return VW.process_image({'id': 'j-edit', 'run_id': RUN['id'], 'request': request}), sent, store


def came_back(monkeypatch, store, conn, status='retained', error=None, failure=None):
    """The edit's job is finished: finalize_image on the film's session, as the worker calls it."""
    request = req(conn.inserted[-1])
    rid, n = request['reference']['id'], len(request['parents'])
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW.jobs, 'finish', lambda *a, **k: None)
    monkeypatch.setattr(VW.jobs, 'record_file', lambda *a, **k: None)
    key = f"{RUN['id']}/visuals/references/{rid}"
    result = {'key': key + '.png', 'sha256': 'e1', 'bytes': 9, 'width': 2752, 'height': 1536, 'notes': '', 'sources': [],
              'extra': [{'key': f'{key}-{k}.png', 'sha256': f'e{k}', 'bytes': 9, 'width': 2752, 'height': 1536} for k in range(2, n + 1)]} if status == 'retained' else {'failure': failure or 'no_image', 'http_status': 400}
    VW.finalize_image(Lock(), {'id': 'j-edit', 'run_id': RUN['id'], 'request': request}, status, result, error, {'provider': 'gemini', 'pictures': n} if status == 'retained' else None, None)
    return rid


# ---------- section 8, tests 1 to 3: the request ----------

def test_1_the_request_of_the_first_picture_is_the_frame_of_section_3_1_with_the_sets_own_settings(monkeypatch, tmp_path):
    store, conn, before, request = ordered()
    assert request['prompt'] == ('Using the provided image, change only this: Take the paint stains off the handle.\n'
                                 'Where: the wooden handle, at the lower right of the frame.\n'
                                 'Keep everything else in the image exactly the same: the same camera, framing, people, things, light and colours. Add no marks, outlines, numbers or text.')
    assert request['prompt'] == RS.EDIT_FIRST.format(words=WORDS, where=WHERE)
    assert [p['id'] for p in request['parents']] == before and request['provider'] == 'gemini' and request['size'] == {'aspect': '16:9', 'tier': '2K'} and 'search' not in request
    assert not any(k in request['prompt'] for k in ('rectangle', 'area 1', 'px'))   # the mark is never sent, in words or as a picture
    (status, result, error, cost, retry), sent, _ = worker(monkeypatch, tmp_path, request, [turn(1), turn(2), turn(3)])
    first = sent[0]['contents'][0]['parts']
    assert status == 'retained' and [p.get('text') for p in first] == ['Image 1.', None, request['prompt']] and first[1]['inlineData']['mimeType'] == 'image/png'
    assert all('tools' not in body and body['generationConfig']['imageConfig'] == {'aspectRatio': '16:9', 'imageSize': '2K'} for body in sent)


def test_2_a_set_of_three_is_one_conversation_each_later_turn_its_picture_the_words_of_3_2_and_the_models_own_corrected_pictures(monkeypatch, tmp_path):
    store, conn, before, request = ordered()
    name = el('T_LAY')['name']
    assert [t['n'] for t in request['edit']['turns']] == [1, 2, 3]
    assert request['edit']['turns'][1]['text'] == (f'Picture 2 of 3 of the same set. Make the same correction here, so that {name} looks the same as in the picture you corrected before. '
                                                   'Keep everything else in this picture exactly the same: the same camera, framing, people, things, light and colours.')
    assert request['edit']['turns'][2]['text'] == RS.EDIT_NEXT.format(n=3, N=3, name=name, s='s') and 'the pictures you corrected before' in request['edit']['turns'][2]['text']
    (status, result, error, cost, retry), sent, store2 = worker(monkeypatch, tmp_path, request, [turn(1), turn(2), turn(3)])
    assert status == 'retained' and len(sent) == 3 and len(result['extra']) == 2 and cost['pictures'] == 3 and cost['inputs'] == 3
    third = sent[2]['contents']
    assert [c['role'] for c in third] == ['user', 'model', 'user', 'model', 'user']
    assert all(any(p.get('inlineData') for p in c['parts']) for c in third)          # each of its turns carries that turn's picture; the model's own corrected pictures go back to it
    assert third[4]['parts'][-1] == {'text': request['edit']['turns'][2]['text']}
    assert third[4]['parts'][-2]['inlineData']['data'] == base64.b64encode(store2.files[request['parents'][2]['key']]).decode()


def test_3_without_the_tick_only_the_marked_picture_is_ordered_and_the_others_come_back_as_they_are(monkeypatch, tmp_path):
    store, conn, before, request = ordered(marks=[2], every=False)
    assert [t['n'] for t in request['edit']['turns']] == [2] and request['edit']['turns'][0]['text'] == RS.EDIT_FIRST.format(words=WORDS, where=WHERE)
    (status, result, error, cost, retry), sent, store2 = worker(monkeypatch, tmp_path, request, [turn(1)])
    assert status == 'retained' and len(sent) == 1 and (cost['pictures'], cost['inputs']) == (1, 1)
    out = [store2.files[result['key']]] + [store2.files[x['key']] for x in result['extra']]
    same = lambda a, b: Image.open(io.BytesIO(a)).tobytes() == Image.open(io.BytesIO(b)).tobytes()
    assert same(out[0], store2.files[request['parents'][0]['key']]) and same(out[2], store2.files[request['parents'][2]['key']]) and not same(out[1], store2.files[request['parents'][1]['key']])


def test_with_the_tick_the_marked_picture_is_corrected_first_and_the_others_follow(monkeypatch, tmp_path):
    store, conn, before, request = ordered(marks=[3])
    assert [t['n'] for t in request['edit']['turns']] == [3, 1, 2] and request['edit']['turns'][1]['text'].startswith('Picture 2 of 3')


# ---------- section 8, test 4, and the failures of section 6 ----------

@pytest.mark.parametrize('answers, said', [([turn(1, 'I cannot change this picture.', image=False)], 'I cannot change this picture.'),
                                           ([{'candidates': [], 'promptFeedback': {'blockReason': 'SAFETY'}}], 'SAFETY'),
                                           ([turn(1), turn(2, 'Not this one.', image=False), turn(3)], 'picture 2')])
def test_4_no_picture_a_block_or_a_later_picture_missing_drops_the_whole_edit(monkeypatch, tmp_path, answers, said):
    store, conn, before, request = ordered()
    (status, result, error, cost, retry), sent, store2 = worker(monkeypatch, tmp_path, request, answers)
    assert status == 'failed' and result['failure'] == 'no_image' and said in error and cost is None
    assert not [k for k in store2.files if request['reference']['id'] in k]          # a set is never left half corrected: nothing is stored


def test_4_the_set_stays_to_be_judged_with_the_reason_and_it_is_not_a_make(monkeypatch):
    store, conn, before, request = ordered()
    assert state(store) == 'making' and saved(store)['round']['elements']['T_LAY']['round'] == 2
    rid = came_back(monkeypatch, store, conn, 'failed', "Google's image model returned no picture: SAFETY")
    s = saved(store)
    who = f"Google's image model {s['references'][rid]['generation']['model']}"
    row = s['round']['elements']['T_LAY']
    assert pics(store) == before and row['set'] == before[0] and state(store) == 2 and 'rewrite_due' not in row and row['history'] == []
    assert RS.makes(s, 'T_LAY', row) == 1                                             # not counted as a make
    f = RS.set_facts(s, F.plan(), 'T_LAY', row)
    assert row['edit_note'] == RS.EDIT_FAILED.format(why=RS.FAIL_TEXT['no_picture'].format(who=who)) and f['edit_note'] == row['edit_note']
    item = next(i for i in CF._round_items(CF._ctx(conn, store, USER, RUN, []), every=True) if i['id'] == f'set:T_LAY:{before[0]}')
    assert row['edit_note'] in item['_line']['text'] and item['_line']['edit_note'] == row['edit_note']   # the reason is shown, on the page and in the chat
    asked(store, conn)                                                                # and the operator may ask again
    assert saved(store)['round']['elements']['T_LAY']['rewrite_due']['edit']


def test_the_corrected_set_takes_the_place_of_the_set_and_the_earlier_one_goes_to_the_versions(monkeypatch):
    store, conn, before, request = ordered(marks=[1])
    rid = came_back(monkeypatch, store, conn)
    s = saved(store)
    row = s['round']['elements']['T_LAY']
    assert pics(store) == [rid, rid + '-2', rid + '-3'] and row['set'] == rid and 'edit_note' not in row
    assert all(s['references'][p]['status'] == 'rejected' and s['references'][p]['rejection']['notes'] == WORDS for p in before)
    assert row['history'][-1]['set'] == before[0] and row['history'][-1]['operator'] == WORDS and row['history'][-1]['edit'] is True and row['prompt'] == 'The brick is wet from soaking.'
    assert row['operator_words'][-1] == WORDS                                         # kept as today: a later "Make again" carries them
    assert s['golden'].get('T_LAY') is None and state(store) == 'looking'              # the starting picture is chosen again, after the look
    new = s['references'][rid + '-2']
    assert new['view'] == s['references'][before[1]]['view'] and new['edit_of'] == before[0]
    assert all(c['pass'] is not False for c in new['check']['code'])                  # made from the pictures it corrects: no fault of the parents
    lines = [l for l in image_check.lines_of(new) if l['check'] == RS.EDIT_LINE[0]]
    assert lines == [{'check': "the operator's correction is made", 'pass_when': f"the operator's correction is made: {WORDS}", 'weight': 'should'}]   # the look's one more line; it only warns
    look(store)
    s = saved(store)
    f = RS.set_facts(s, F.plan(), 'T_LAY', s['round']['elements']['T_LAY'])
    assert f['edited'] is True and f['asked'] == WORDS and f['makes'] == 2 and f['makes_left'] == 1
    item = next(i for i in CF._round_items(CF._ctx(conn, store, USER, RUN, []), every=True) if i['id'] == f'set:T_LAY:{rid}')
    assert item['_line']['asked'] == CF.WORDS['edited'].format(words=WORDS) and [p['label'] for p in item['_line']['earlier']] == ['Before: A', 'Before: B', 'Before: C']


def test_the_asked_thing_unchanged_fails_the_looks_new_line_beside_the_picture_and_nothing_is_tried_again(monkeypatch):
    store, conn, before, request = ordered()
    rid = came_back(monkeypatch, store, conn)
    sets = RS.looks_due(store, RUN, [])['sets']
    line = next(l for l in sets[0]['pictures'][0]['lines'] if l['check'] == RS.EDIT_LINE[0])
    sent = [{'element_id': 'T_LAY', 'set': rid, 'recommend': 'doubt', 'golden': None, 'reason': 'The stains are still there.', 'chose': 'x', 'aside': 'y',
             'pictures': [{'ref': p['ref'], 'view': p['view'], 'verdict': 'weak', 'seen': 'As before.',
                           'lines': [{'id': l['id'], 'pass': l['id'] != line['id'], 'seen': 'The stains are still on the handle.' if l['id'] == line['id'] else ('ok' if l.get('say') else '')} for l in p['lines']]} for p in sets[0]['pictures']]}]
    VS.guarded(lambda: RS.round_looks(store, USER, RUN, [], sent, 'helper'))
    s = saved(store)
    f = RS.set_facts(s, F.plan(), 'T_LAY', s['round']['elements']['T_LAY'])
    assert f['pictures'][0]['check']['failed'] == [{'check': RS.EDIT_LINE[0], 'seen': 'The stains are still on the handle.'}]
    assert state(store) == 2 and len(conn.inserted) == 4                              # with the operator: no automatic second try


@pytest.mark.parametrize('code', [429, 503])
def test_a_limit_or_an_outage_on_any_turn_queues_the_edit_again(monkeypatch, tmp_path, code):
    store, conn, before, request = ordered()
    (status, result, error, cost, retry), sent, store2 = worker(monkeypatch, tmp_path, request, [turn(1), Resp(code, {'error': {'message': 'later'}})])
    assert status == 'queued' and retry == 1 and result['http_status'] == code


# ---------- section 8, tests 5 to 9: what is asked, the three makes, the limit, a stale answer ----------

def test_5_words_and_no_mark_is_an_edit_from_the_words_and_a_mark_with_no_words_is_refused():
    store, conn = at_two()
    before = pics(store)
    assert refused(lambda: asked(store, conn, words='  ', marks={before[0]: [RECT]})) == 'T_LAY: say what to correct.'
    assert pics(store) == before and 'rewrite_due' not in saved(store)['round']['elements']['T_LAY']
    out = asked(store, conn)
    row = saved(store)['round']['elements']['T_LAY']
    assert out['rewrite'] == ['T_LAY'] and row['rewrite_due'] == {'words': WORDS, 'set': before[0], 'at': row['rewrite_due']['at'], 'edit': {'marks': {}, 'every': True, 'by': USER['id'], 'quote': 'Sets done'}}
    assert pics(store) == before and state(store) == 'rewrite' and len(conn.inserted) == 3   # nothing is rejected and nothing is ordered before the where line
    assert RS.EDIT_DUE.format(n=1, things=RS.REWRITE_WORDS.format(eid='T_LAY', words=WORDS)) == out['then'] == RS.then_of(saved(store))
    due = RS.rewrites_due(store, RUN, [])
    assert due['how'] == RS.WHERE_HOW and due['sets'] == [{'element_id': 'T_LAY', 'name': due['sets'][0]['name'], 'edit': True, 'words': WORDS, 'every': True,
                                                           'pictures': [{'ref': r, 'n': n, 'view': due['sets'][0]['pictures'][n - 1]['view'], 'key': due['sets'][0]['pictures'][n - 1]['key'], 'marks': 0} for n, r in enumerate(before, 1)]}]
    assert where(store, conn) == {'pass': 'making', 'queued': ['T_LAY'], 'errors': {}, 'then': RS.EDIT_MAKING.format(n=1)}


def test_several_marks_on_one_picture_are_one_where_line_and_claude_sees_them_drawn_on_a_copy():
    store, conn = at_two()
    before = pics(store)
    for p in before:
        store.files[saved(store)['references'][p]['key']] = png_bytes(320, 180, (200, 200, 200))
    marks = {before[0]: [RECT, {'p': [0.1, 0.1, 0.2, 0.15, 0.3, 0.1], 's': 0.04}, {'r': [0, 0, 0.1, 0.1]}]}
    asked(store, conn, marks=marks, every=False)
    assert saved(store)['round']['elements']['T_LAY']['rewrite_due']['edit']['marks'] == marks   # the marks are kept with the answer
    shown = RS.rewrites_due(store, RUN, [])['sets'][0]['pictures']
    assert [p['marks'] for p in shown] == [3, 0, 0] and '-marked-' in shown[0]['key'] and '-marked-' not in shown[1]['key']
    with Image.open(io.BytesIO(store.files[shown[0]['key']])) as im:
        w, h = im.size
        r, g, b = im.convert('RGB').getpixel((int(0.5 * w) + 1, int(0.6 * h)))
        assert r > 180 and g < 90 and b < 90                                          # the red outline of the rectangle, on the copy only
    assert Image.open(io.BytesIO(store.files[saved(store)['references'][before[0]]['key']])).getpixel((161, 108)) == (200, 200, 200)
    where(store, conn)
    request = req(conn.inserted[-1])
    assert request['prompt'].count(WORDS) == 1 and [t['n'] for t in request['edit']['turns']] == [1] and saved(store)['round']['elements']['T_LAY']['edit']['marks'] == marks


@pytest.mark.parametrize('marks', [{'nobody': [RECT]}, {0: [RECT, RECT, RECT, RECT]}, {0: [{'r': [0.1, 0.1]}]}, {0: [{'circle': 1}]}, {0: 'here'}, {0: [{'p': [], 's': 0.1}]}, {0: [{'p': [0.1, 0.2, 0.3], 's': 0.1}]}])
def test_a_mark_that_is_no_mark_of_this_set_is_refused(marks):
    store, conn = at_two()
    before = pics(store)
    marks = {before[k] if isinstance(k, int) else k: v for k, v in marks.items()}
    assert refused(lambda: asked(store, conn, marks=marks)) == RS.MARKS_BAD.format(eid='T_LAY', max=3)
    assert refused(lambda: asked(store, conn, every=False)) == RS.EDIT_ONE.format(eid='T_LAY')   # no tick and no mark: which picture is not said


def test_a_mark_over_most_of_the_picture_and_words_the_text_says_are_done_poorly_are_sent_as_they_are():
    store, conn = at_two()
    before = pics(store)
    words = 'Give the frame four legs instead of three.'
    asked(store, conn, words=words, marks={before[0]: [{'r': [0, 0, 1, 1]}]})
    where(store, conn, line='the whole frame')
    assert req(conn.inserted[-1])['prompt'] == RS.EDIT_FIRST.format(words=words, where='the whole frame')


def test_6_an_edit_counts_as_a_make_and_after_three_the_next_is_held(monkeypatch):
    store, conn, before, request = ordered()
    came_back(monkeypatch, store, conn)
    look(store)
    asked(store, conn, words='Now clean the blade too.')
    where(store, conn, line='the steel blade, left of the handle')
    came_back(monkeypatch, store, conn)
    look(store)
    s = saved(store)
    assert RS.makes(s, 'T_LAY', s['round']['elements']['T_LAY']) == 3 and len(conn.inserted) == 5
    out = asked(store, conn, words='Once more.')
    assert out['held'] == {'T_LAY': RS.MAKES_LIMIT.format(eid='T_LAY', max=3)} and 'rewrite_due' not in saved(store)['round']['elements']['T_LAY'] and len(conn.inserted) == 5
    assert refused(lambda: VS.set_answer(store, USER, RUN, [], 'T_LAY', 'correct', None, 'Once more.')) == RS.MAKES_LIMIT.format(eid='T_LAY', max=3)


def test_7_the_spend_limit_holds_the_edit_and_the_answer_waits_stored_with_its_marks(monkeypatch):
    store, conn = at_two()
    before = pics(store)
    monkeypatch.setattr(VS, '_set_budget', lambda run, s, spend: (100.0, 100.0, 35.0))
    out = asked(store, conn, marks={before[1]: [RECT]}, every=False)
    row = saved(store)['round']['elements']['T_LAY']
    assert out['held'] == {'T_LAY': RS.LIMIT_PLAIN} and 'rewrite_due' not in row and pics(store) == before and len(conn.inserted) == 3
    assert {k: row['answer'][k] for k in ('verdict', 'words', 'set', 'marks', 'every')} == {'verdict': 'correct', 'words': WORDS, 'set': before[0], 'marks': {before[1]: [RECT]}, 'every': False}
    assert VS._answer_of(row)[0] == {'verdict': 'correct', 'golden': None, 'words': WORDS, 'marks': {before[1]: [RECT]}, 'every': False}


def test_7_the_limit_reached_between_the_answer_and_the_where_line_orders_nothing_and_the_set_stays(monkeypatch):
    store, conn = at_two()
    before = pics(store)
    asked(store, conn)
    monkeypatch.setattr(VS, 'check_cap', lambda *a, **k: (_ for _ in ()).throw(VS.Problem(409, 'VISUALS_CAP', 'no room')))
    out = where(store, conn)
    row = saved(store)['round']['elements']['T_LAY']
    assert out['queued'] == [] and out['errors'] == {'T_LAY': RS.LIMIT_PLAIN} and row['rewrite_due']['edit'] and pics(store) == before and len(conn.inserted) == 3


def test_8_an_answer_stored_on_the_set_before_is_refused_as_stale_also_for_a_second_member(monkeypatch):
    store, conn = at_two()
    before = pics(store)
    VS.set_answer(store, USER, RUN, [], 'T_LAY', 'correct', None, WORDS, marks={before[0]: [RECT]})   # one member's answer, stored
    other = {**USER, 'id': 'user-2', 'name': 'Second member'}
    VS.guarded(lambda: VS.round_sets(store, other, RUN, [], {'T_LAY': {'verdict': 'correct', 'words': 'Another thing.'}}, 'Sets done', conn=conn, partial=True))
    assert refused(lambda: VS.set_answer(store, USER, RUN, [], 'T_LAY', 'correct', None, WORDS)) == VS.SET_WAITS['edit'].format(name='T_LAY')
    name = el('T_LAY')['name']
    assert asked(store, conn)['waiting'] == {'T_LAY': VS.SET_WAITS['edit'].format(name=name)}
    where(store, conn)
    rid = came_back(monkeypatch, store, conn)
    look(store)
    s = saved(store)
    s['round']['elements']['T_LAY']['answer'] = {'verdict': 'correct', 'golden': None, 'words': WORDS, 'set': before[0], 'marks': {before[0]: [RECT]}, 'by': USER['id'], 'at': 'x'}
    put(store, s)
    assert VS._answer_of(saved(store)['round']['elements']['T_LAY']) == (None, True)   # made again since: never recorded
    assert VS.set_gone(saved(store), F.plan(), f'set:T_LAY:{before[0]}') == (True, VS.SET_RECORDED.format(name=name))
    assert refused(lambda: asked(store, conn, marks={before[0]: [RECT]})) == RS.MARKS_BAD.format(eid='T_LAY', max=3)   # a mark on a picture of the set before


# ---------- section 8, tests 9 to 11: one function, the older way, the text ----------

def test_9_the_page_and_the_chat_store_the_answer_through_the_same_server_function(monkeypatch):
    store, conn = at_two()
    before = pics(store)
    calls = []
    real = VS.set_answer
    monkeypatch.setattr(VS, 'set_answer', lambda *a, **k: calls.append((a[4:], k)) or real(*a, **k))
    item = next(i for i in CF._round_items(CF._ctx(conn, store, USER, RUN, []), every=True) if i['id'] == f'set:T_LAY:{before[0]}')
    assert [p['ref'] for p in item['_line']['pics'] if not p.get('ref_only')] == before     # the page names a mark by its picture
    button = next(b for b in item['_line']['buttons'] if b['choice'] == 'correct')
    assert button['label'] == 'Minor corrections' and button['mark'] is True and CF.SETS_PAGE['mark'] is CF.MARK_WORDS and button['every']['on'] is True
    got = page_flow._round_answer(CF._ctx(conn, store, USER, RUN, []), {'key': 'set:T_LAY', 'item': item['id'], 'choice': 'correct', 'marks': {before[1]: [RECT]}, 'every': False}, 'correct', WORDS)
    assert got[0] == 'Minor corrections: ' + WORDS and calls == [(('T_LAY', 'correct', None, WORDS), {'all': False, 'marks': {before[1]: [RECT]}, 'every': False, 'own': None})]
    assert saved(store)['round']['elements']['T_LAY']['rewrite_due']['edit'] == {'marks': {before[1]: [RECT]}, 'every': False, 'by': USER['id'], 'quote': 'Minor corrections'}
    store, conn = at_two()                                                             # the chat: the same answer, with words alone
    del calls[:]
    item = next(i for i in CF._round_items(CF._ctx(conn, store, USER, RUN, []), every=True) if i['id'].startswith('set:T_LAY:'))
    assert any(b['label'] == 'Minor corrections' and b['choice'] == 'correct' for b in item['buttons'] + list(item.get('other_choices') or []))
    item['_run']('correct', 'Minor corrections', WORDS)
    assert calls == [(('T_LAY', 'correct', None, WORDS), {'all': False, 'marks': None, 'every': None, 'own': None})]
    assert saved(store)['round']['elements']['T_LAY']['rewrite_due']['edit']['every'] is True
    assert set(main.RoundAnswer.model_fields) >= {'marks', 'every'} and set(main.PageAnswer.model_fields) >= {'marks', 'every'}


def test_9_make_again_with_a_comment_stays_a_fresh_set_from_the_request_written_again():
    store, conn = at_two()
    before = pics(store)
    item = next(i for i in CF._round_items(CF._ctx(conn, store, USER, RUN, []), every=True) if i['id'] == f'set:T_LAY:{before[0]}')
    again = next(b for b in item['_line']['buttons'] if b['choice'] == 'no')
    assert again['comment'] == CF.WORDS['again_hint'] and again['say'] == CF.WORDS['say_again']
    got = page_flow._round_answer(CF._ctx(conn, store, USER, RUN, []), {'key': 'set:T_LAY', 'item': item['id'], 'choice': 'no'}, 'no', 'Seen from further away.')
    s = saved(store)
    row = s['round']['elements']['T_LAY']
    assert got[0].endswith(': Seen from further away.') and row['verdict'] == 'no' and row['rewrite_due'] == {'words': 'Seen from further away.', 'set': before[0], 'at': row['rewrite_due']['at']}
    assert all(s['references'][p]['status'] == 'rejected' for p in before) and row['operator_words'] == ['Seen from further away.']
    out = VS.guarded(lambda: RS.round_rewrite(conn, store, USER, RUN, [], [{'element_id': 'T_LAY', 'prompt': 'The whole wall, seen from four metres.'}]))
    assert out['queued'] == ['T_LAY'] and 'edit' not in req(conn.inserted[-1]) and "The operator's words: Seen from further away." in req(conn.inserted[-1])['prompt']


def test_9_in_the_chat_the_operators_word_for_the_click_is_no_comment_and_their_notes_are():
    for notes, kept in (('', ''), ('Make it narrower.', 'Make it narrower.')):
        store, conn = at_two()
        item = next(i for i in CF._round_items(CF._ctx(conn, store, USER, RUN, []), every=True) if i['id'].startswith('set:T_LAY:'))
        again = next(b for b in item['buttons'] + list(item.get('other_choices') or []) if b['choice'] == 'no')
        assert again['tell'] == CF.WORDS['again_tell'] and '--notes' in again['tell']
        item['_run']('no', 'no, once more', notes or 'no, once more')   # as `chat_flow.answer` calls it: the notes, else the operator's word for the click
        CF.flush_sets(conn, store, USER, RUN, [], 'no, once more')
        assert saved(store)['round']['elements']['T_LAY']['rewrite_due']['words'] == kept


def test_10_the_older_remake_from_words_is_refused_by_name_where_the_tool_still_offers_it():
    store, conn = at_two()
    asked(store, conn)
    send = lambda rows: refused(lambda: RS.round_rewrite(conn, store, USER, RUN, [], rows))
    assert send([{'element_id': 'T_LAY', 'prompt': 'A new request from the words.'}]) == RS.EDIT_NOT_REMAKE.format(eid='T_LAY')
    assert 'no longer makes a new set from words' in RS.EDIT_NOT_REMAKE
    assert send([{'element_id': 'T_LAY', 'where': ' '}]) == RS.WHERE_EMPTY.format(eid='T_LAY')
    for bad in ('the red rectangle at the right', 'area 1', 'the handle at 1200 px from the left', 'the handle.\nAlso the blade', 'x' * 301):
        assert send([{'element_id': 'T_LAY', 'where': bad}]) == RS.WHERE_SHAPE.format(eid='T_LAY', max=300), bad
    assert len(conn.inserted) == 3 and saved(store)['round']['elements']['T_LAY']['rewrite_due']['edit']
    judge(store, conn, {'MASON': {'verdict': 'no'}})                                   # and a where line is no rewrite of a set that waits for "Make again"
    assert send([{'element_id': 'MASON', 'where': WHERE}]) == RS.REWRITE_EMPTY.format(eid='MASON')


def test_claude_cannot_tell_which_thing_is_meant_the_operator_is_asked_once_and_nothing_is_sent():
    store, conn = at_two()
    before = pics(store)
    asked(store, conn, words='Take it off.')
    out = VS.guarded(lambda: RS.round_rewrite(conn, store, USER, RUN, [], [{'element_id': 'T_LAY', 'unclear': 'Which thing should come off: the cloth or the string?'}]))
    row = saved(store)['round']['elements']['T_LAY']
    assert out['queued'] == [] and out['asked'] == ['T_LAY'] and len(conn.inserted) == 3 and 'rewrite_due' not in row and pics(store) == before and state(store) == 2
    assert row['edit_note'] == RS.EDIT_UNCLEAR.format(question='Which thing should come off: the cloth or the string?') and row['round'] == 1 and row['operator_words'] == []


def test_11_the_text_of_section_3_4_is_one_constant_the_page_shows_and_the_chat_says():
    assert CF.EDIT_TOLD == ('Minor corrections changes this picture and keeps the rest.\n'
                            'It does well: taking a thing out of the picture; changing the condition of a thing (newer, cleaner, less worn).\n'
                            'It does poorly: changing how a thing is built or shaped (its parts, how many there are, how they join). For that, ask another way, for example take the thing out, '
                            'or use Make again and describe it as it should be.\n'
                            'Small things around the place may shift.')
    store, conn = at_two()
    item = next(i for i in CF._round_items(CF._ctx(conn, store, USER, RUN, []), every=True) if i['id'].startswith('set:T_LAY:'))
    page = next(b for b in item['_line']['buttons'] if b['choice'] == 'correct')
    chat = next(b for b in item['buttons'] + list(item.get('other_choices') or []) if b['choice'] == 'correct')
    assert page['mark'] is True and CF.SETS_PAGE['mark']['told'] == CF.EDIT_TOLD and CF.EDIT_TOLD in chat['tell']
    assert json.dumps(page_flow.page_words()).count('Minor corrections changes this picture') == 1 and 'told' not in page   # sent once, with the screen's words, not on every set's button


# ---------- the operator's own picture ----------

def test_the_operators_own_picture_is_marked_and_corrected_like_a_picture_of_the_set(monkeypatch):
    store, conn = at_two()
    eid = 'T_LAY'
    before = pics(store, eid)
    s = saved(store)
    s['references']['own-1'] = {'id': 'own-1', 'kind': 'supplied', 'status': 'approved', 'element_id': eid, 'name': 'own', 'key': f"{RUN['id']}/visuals/references/own-1.png", 'sha256': 'o' * 64, 'width': 1600, 'height': 900}
    put(store, s)
    VS.set_answer(store, USER, RUN, [], eid, 'correct', None, 'Take the maker\'s sticker off.', marks={'own-1': [RECT]}, own=['own-1'])
    CF.flush_sets(conn, store, USER, RUN, [], 'Minor corrections')   # recorded as the page and the chat record a kept answer
    where(store, conn, eid, 'the white sticker, at the top left')
    request = req(conn.inserted[-1])
    assert [p['id'] for p in request['parents']] == ['own-1'] and request['provider'] == 'gemini' and request['view_names'] == [CF.WORDS['own_view']] and len(request['edit']['turns']) == 1
    rid = came_back(monkeypatch, store, conn)
    s = saved(store)
    assert pics(store, eid) == [rid] and all(s['references'][p]['status'] == 'rejected' for p in before) and s['references']['own-1']['status'] == 'approved'
    assert refused(lambda: VS.set_answer(store, USER, RUN, [], 'MASON', 'correct', None, 'x', own=['own-1'])) == RS.EDIT_OWN.format(eid='MASON')   # another thing's picture, and a person's photo is never corrected
