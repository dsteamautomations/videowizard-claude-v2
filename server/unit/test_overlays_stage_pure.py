"""Text overlays, build step 3 (requirements version 3 of 28 Nov 2026, parts A and B): the step's record, the one start card, the client's kept look,
and the gate the editor's package waits behind. The operator decides everything; the application only refuses what it cannot make."""
import json

import pytest

from app import overlay_stage as S
from app import overlays as O
from app.errors import Problem

RUN = {'id': 'r1', 'code': 'VW-30', 'client_id': 'c1'}
FILM = {'fps': 25, 'frames': 400, 'cuts': [], 'words': [], 'font': 'Inter', 'scripts': ['latin']}


class Store(dict):
    def put(self, key, data, mime=None):
        self[key] = data

    def get(self, key):
        if key not in self:
            raise Problem(404, 'NOT_FOUND', key)
        return self[key]

    def exists(self, key):
        return key in self


def fresh():
    store = Store()
    return store, S.session_of(store, RUN)


# ---------- the record ----------

def test_a_film_with_no_record_yet_has_an_empty_one_and_a_saved_one_reads_back():
    store, session = fresh()
    assert session['start'] is None and session['rows'] == []
    session['start'] = {'answer': 'none'}
    S.save_session(store, RUN, session)
    assert S.session_of(store, RUN)['start'] == {'answer': 'none'} and 'r1/visuals/overlays/session.json' in store


# ---------- the start card ----------

def test_the_start_card_offers_the_kinds_the_cards_as_pictures_the_motions_in_words_and_the_fonts_of_the_application():
    card = S.start_card(FILM)
    assert [k['id'] for k in card['kinds']] == list(O.KINDS) and all(k['what'] for k in card['kinds'])
    assert [c['id'] for c in card['cards']] == list(O.CARDS) and all(c['sample'].endswith('.jpg') and c['what'] for c in card['cards'])
    assert [m['id'] for m in card['motions']] == list(O.MOTIONS) and all(m['what'] for m in card['motions'])
    assert 'Inter' in card['fonts'] and 'only' in card['font_note'].lower()
    assert card['sizes'] == list(O.SIZES) and card['weights'] == list(O.WEIGHTS)
    assert [a['label'] for a in card['answers']] == ['Accept the defaults', 'Change', 'No overlays in this film']
    assert card['defaults'] == {'kinds': list(O.KINDS), 'look': {'card': 'dark', 'motion': 'wipe', 'size': 'medium', 'weight': 'bold', 'font': 'Inter'}}
    assert card['kept_from'] is None and 'your own' in card['own_card'].lower()


def test_a_film_in_another_script_is_offered_only_the_fonts_that_hold_it():
    fonts = S.start_card({**FILM, 'scripts': ['latin', 'tamil']})['fonts']
    assert fonts and 'Inter' not in fonts


def test_the_clients_look_from_their_last_film_is_the_default_of_the_next():
    store, session = fresh()
    assert S.answer(store, RUN, session, {'answer': 'change', 'kinds': ['callout', 'number'], 'look': {'card': 'cream', 'motion': 'fade'}}, FILM) == []
    card = S.start_card(FILM, S.kept_look(store, 'c1'))
    assert card['kept_from'] == 'VW-30' and card['defaults']['kinds'] == ['callout', 'number']
    assert card['defaults']['look'] == {'card': 'cream', 'motion': 'fade', 'size': 'medium', 'weight': 'bold', 'font': 'Inter'}


def test_a_kept_font_the_new_film_cannot_use_gives_way_to_the_films_own():
    kept = {'run': 'VW-29', 'kinds': ['callout'], 'look': {'font': 'Inter'}}
    assert S.start_card({**FILM, 'font': 'Noto Sans', 'scripts': ['latin', 'tamil']}, kept)['defaults']['look']['font'] == 'Noto Sans'


def test_no_client_no_kept_look():
    store, session = fresh()
    S.answer(store, {**RUN, 'client_id': None}, session, {'answer': 'defaults'}, FILM)
    assert S.kept_look(store, None) is None and not any(k.startswith('clients/') for k in store)


# ---------- the answer ----------

def test_accepting_the_defaults_records_them():
    store, session = fresh()
    assert S.answer(store, RUN, session, {'answer': 'defaults'}, FILM) == []
    assert session['start']['answer'] == 'defaults' and session['start']['kinds'] == list(O.KINDS) and session['start']['look'] == {}
    assert S.session_of(store, RUN)['start']['answer'] == 'defaults'


def test_accepting_the_defaults_of_a_kept_look_records_the_kept_look():
    store, session = fresh()
    S.answer(store, RUN, session, {'answer': 'change', 'look': {'card': 'bar'}}, FILM)
    run2 = {'id': 'r2', 'code': 'VW-31', 'client_id': 'c1'}
    s2 = S.session_of(store, run2)
    S.answer(store, run2, s2, {'answer': 'defaults'}, FILM)
    assert s2['start']['look'] == {'card': 'bar'}


def test_a_change_keeps_what_the_operator_set_and_an_own_card_too():
    store, session = fresh()
    own = {'ground': '#102a43', 'opacity': 90, 'corner': 'pill'}
    assert S.answer(store, RUN, session, {'answer': 'change', 'look': {'card': own, 'size': 'large'}}, FILM) == []
    assert session['start']['look'] == {'card': own, 'size': 'large'} and session['start']['kinds'] == list(O.KINDS)
    assert O.look_of(session['start']['look'], FILM)['card']['corner'] == 'pill'


def test_no_overlays_in_this_film_is_an_answer():
    store, session = fresh()
    assert S.answer(store, RUN, session, {'answer': 'none'}, FILM) == [] and session['start'] == {'answer': 'none', 'kinds': [], 'look': {}, 'at': session['start']['at']}
    assert S.kept_look(store, 'c1') is None   # a film without overlays does not change the client's look


@pytest.mark.parametrize('body, said', [
    ({'answer': 'maybe'}, 'defaults, change, none'),
    ({'answer': 'change', 'look': {'motion': 'spin'}}, "motion 'spin'"),
    ({'answer': 'change', 'look': {'font': 'Comic Sans'}}, 'not in the application'),
    ({'answer': 'change', 'look': {'colour': 'red'}}, 'colour'),
    ({'answer': 'change', 'kinds': ['banner']}, "'banner'"),
    ({'answer': 'change', 'kinds': []}, 'No overlays in this film'),
    ({'answer': 'change', 'look': 'dark'}, 'look'),
])
def test_only_what_cannot_be_made_is_refused_and_nothing_is_recorded(body, said):
    store, session = fresh()
    problems = S.answer(store, RUN, session, body, FILM)
    assert len(problems) == 1 and said in problems[0] and session['start'] is None and store == {}


def test_a_changed_look_asks_every_overlay_again_and_the_same_look_does_not():
    store, session = fresh()
    S.answer(store, RUN, session, {'answer': 'defaults'}, FILM)
    session['rows'] = [{'id': 'O01', 'state': 'approved', 'clip': {'key': 'k'}}, {'id': 'O02', 'state': 'removed', 'clip': None}]
    S.answer(store, RUN, session, {'answer': 'defaults'}, FILM)
    assert session['rows'][0]['state'] == 'approved'
    S.answer(store, RUN, session, {'answer': 'change', 'look': {'card': 'cream'}}, FILM)
    assert session['rows'][0] == {'id': 'O01', 'state': 'proposed', 'clip': None} and session['rows'][1]['state'] == 'removed'


# ---------- the gate ----------

def test_the_package_waits_for_the_start_card():
    _, session = fresh()
    assert S.open_points(session) == ['the start card of the overlays is not answered (`vw overlays start`)']
    with pytest.raises(Problem) as e:
        S.gate(session)
    assert e.value.status == 409 and 'start card' in e.value.message


def test_no_overlays_in_this_film_settles_the_step():
    store, session = fresh()
    S.answer(store, RUN, session, {'answer': 'none'}, FILM)
    assert S.open_points(session) == [] and S.gate(session) is None


def test_the_package_waits_for_the_list_then_every_approval_then_every_clip():
    store, session = fresh()
    S.answer(store, RUN, session, {'answer': 'defaults'}, FILM)
    assert S.open_points(session) == ['no overlay list is proposed yet (`vw overlays propose`)']
    session['proposed'] = True
    session['rows'] = [{'id': 'O01', 'state': 'proposed', 'clip': None}, {'id': 'O02', 'state': 'approved', 'clip': None}, {'id': 'O03', 'state': 'removed', 'clip': None}]
    assert S.open_points(session) == ['O01 is not approved or removed', 'O02 has no clip yet']
    session['rows'][0]['state'], session['rows'][1]['clip'] = 'removed', {'key': 'k'}
    assert S.open_points(session) == []


def test_a_list_the_operator_emptied_settles_the_step():
    store, session = fresh()
    S.answer(store, RUN, session, {'answer': 'defaults'}, FILM)
    session['proposed'], session['rows'] = True, []
    assert S.open_points(session) == []


def test_the_record_is_plain_json():
    store, session = fresh()
    S.answer(store, RUN, session, {'answer': 'change', 'look': {'card': {'ground': '#000000'}}}, FILM)
    assert json.loads(store['r1/visuals/overlays/session.json'])['start']['look']['card'] == {'ground': '#000000'}


# ---------- build step 4 (parts C and D): the list, proposed and decided ----------

CUTS = {'fps': 25, 'frames': 400, 'font': 'Inter', 'scripts': ['latin'],
        'cuts': [{'name': 'S01-1', 'start_frame': 0, 'end_frame': 200}, {'name': 'S02-1', 'start_frame': 200, 'end_frame': 400}],
        'words': [{'start_frame': i * 10, 'end_frame': i * 10 + 8, 'text': 'w'} for i in range(40)]}
A_ROW = {'kind': 'callout', 'lines': ['Two weeks'], 'word': 3, 'why': 'the figure the viewer should keep'}
B_ROW = {'kind': 'title', 'lines': ['Curing'], 'word': 22}


def started(answer='defaults', **k):
    store, session = fresh()
    S.answer(store, RUN, session, {'answer': answer, **k}, CUTS)
    return store, session


def test_the_films_cuts_and_words_are_read_from_the_package():
    events = [{'record_in_frame': 0, 'record_out_frame': 50, 'marker': {'name': 'S01-1'}}, {'record_in_frame': 50, 'record_out_frame': 90, 'marker': {'name': 'S01-1'}},
              {'record_in_frame': 90, 'record_out_frame': 120, 'marker': {'name': 'S02-1'}}, {'record_in_frame': 120, 'record_out_frame': 150}]
    film = S.film_of(events, [{'start_frame': 3, 'end_frame': 9, 'text': 'A'}], 25, 150, 'Inter', {'latin'})
    assert film['cuts'] == [{'name': 'S01-1', 'start_frame': 0, 'end_frame': 90}, {'name': 'S02-1', 'start_frame': 90, 'end_frame': 120}, {'name': 'cut 4', 'start_frame': 120, 'end_frame': 150}]
    assert film['words'] == [{'start_frame': 3, 'text': 'A'}] and (film['fps'], film['frames'], film['font'], film['scripts']) == (25, 150, 'Inter', ['latin'])


def test_a_proposed_list_is_recorded_with_a_number_for_each_overlay_and_each_waits_for_the_operator():
    store, session = started()
    out = S.propose(store, RUN, session, {'overlays': [A_ROW, B_ROW]}, CUTS)
    assert out['problems'] == [] and out['to_draw'] == ['O01', 'O02'] and session['proposed'] is True
    assert [(r['id'], r['state'], r['still'], r['clip']) for r in session['rows']] == [('O01', 'proposed', None, None), ('O02', 'proposed', None, None)]
    assert S.session_of(store, RUN)['rows'][0]['given'] == A_ROW
    view = S.listing(session, CUTS)
    assert view[0] == {'id': 'O01', 'state': 'proposed', 'kind': 'callout', 'lines': ['Two weeks'], 'shot': 'S01-1', 'start_s': 0.8, 'end_s': 2.6, 'place': 'bottom left',
                       'motion': 'wipe', 'facts': [], 'why': 'the figure the viewer should keep', 'still': None, 'clip': False}
    assert view[1]['shot'] == 'S02-1'


def test_the_list_uses_the_look_of_the_start_card():
    store, session = started('change', look={'card': 'cream', 'motion': 'fade'})
    S.propose(store, RUN, session, {'overlays': [A_ROW]}, CUTS)
    assert session['rows'][0]['row']['motion'] == 'fade' and session['rows'][0]['row']['card']['ground'] == O.CARDS['cream']['ground']


def test_a_list_with_a_fault_is_not_recorded_and_the_fault_is_named():
    store, session = started()
    out = S.propose(store, RUN, session, {'overlays': [A_ROW, {**B_ROW, 'word': 99}]}, CUTS)
    assert len(out['problems']) == 1 and out['problems'][0].startswith('row 2') and session['rows'] == [] and session['proposed'] is False


def test_a_list_before_the_start_card_or_after_no_overlays_is_refused_with_what_to_do():
    store, session = fresh()
    assert 'start card' in S.propose(store, RUN, session, {'overlays': [A_ROW]}, CUTS)['problems'][0]
    store, session = started('none')
    assert 'No overlays in this film' in S.propose(store, RUN, session, {'overlays': [A_ROW]}, CUTS)['problems'][0]


def test_proposing_again_keeps_what_did_not_change_and_asks_only_the_new_ones():
    store, session = started()
    S.propose(store, RUN, session, {'overlays': [A_ROW, B_ROW]}, CUTS)
    session['rows'][0].update(state='approved', still={'key': 's'}, clip={'key': 'c'})
    out = S.propose(store, RUN, session, {'overlays': [{**B_ROW, 'lines': ['Curing the slab']}, A_ROW]}, CUTS)
    assert out['to_draw'] == ['O03']
    assert [(r['id'], r['state']) for r in session['rows']] == [('O03', 'proposed'), ('O01', 'approved')] and session['rows'][1]['clip'] == {'key': 'c'}


def test_the_operator_approves_removes_and_changes_one_overlay():
    store, session = started()
    S.propose(store, RUN, session, {'overlays': [A_ROW, B_ROW]}, CUTS)
    session['rows'][0]['still'] = {'key': 's'}
    assert S.decide(store, RUN, session, 'O01', 'approve', CUTS) == {'problems': [], 'to_draw': []} and session['rows'][0]['state'] == 'approved'
    assert S.decide(store, RUN, session, 'O02', 'remove', CUTS)['problems'] == [] and session['rows'][1]['state'] == 'removed'
    out = S.decide(store, RUN, session, 'O01', 'change', CUTS, {**A_ROW, 'place': {'x': 70, 'y': 30}, 'motion': 'cut'})
    assert out == {'problems': [], 'to_draw': ['O01']}
    assert session['rows'][0]['state'] == 'proposed' and session['rows'][0]['still'] is None and session['rows'][0]['row']['motion'] == 'cut'
    assert S.session_of(store, RUN)['rows'][0]['given']['motion'] == 'cut'


def test_a_change_with_a_fault_changes_nothing_and_names_the_overlay():
    store, session = started()
    S.propose(store, RUN, session, {'overlays': [A_ROW]}, CUTS)
    out = S.decide(store, RUN, session, 'O01', 'change', CUTS, {**A_ROW, 'motion': 'spin'})
    assert out['problems'][0].startswith('O01: ') and "'spin'" in out['problems'][0] and session['rows'][0]['given'] == A_ROW


@pytest.mark.parametrize('rid, what, given, said', [('O09', 'approve', None, 'O09 is not an overlay of this film'), ('O01', 'like', None, 'approve, remove, change'),
                                                    ('O01', 'change', None, 'the changed overlay')])
def test_a_decision_that_cannot_be_recorded_says_why(rid, what, given, said):
    store, session = started()
    S.propose(store, RUN, session, {'overlays': [A_ROW]}, CUTS)
    assert said in S.decide(store, RUN, session, rid, what, CUTS, given)['problems'][0]


def test_approve_all_as_shown_approves_every_overlay_still_waiting():
    store, session = started()
    S.propose(store, RUN, session, {'overlays': [A_ROW, B_ROW, {**A_ROW, 'word': 30}]}, CUTS)
    S.decide(store, RUN, session, 'O02', 'remove', CUTS)
    assert S.approve_all(store, RUN, session) == ['O01', 'O03'] and [r['state'] for r in session['rows']] == ['approved', 'removed', 'approved']
    assert S.open_points(session) == ['O01 has no clip yet', 'O03 has no clip yet']


# ---------- build step 5: the stills and the clips, made by the worker ----------

PAGE = {'fps': 25, 'width': 1920, 'height': 1080, 'accent': '#F0A46E', 'scripts': ['latin']}
EVENTS = [{'file': 'Media/AI/S01-1-asset.png', 'kind': 'still', 'source_in_frame': 0, 'source_out_frame': 200, 'record_in_frame': 0, 'record_out_frame': 200, 'source_fps': '25'},
          {'file': 'Media/AI/S02-1.mp4', 'kind': 'movie', 'source_in_frame': 10, 'source_out_frame': 210, 'record_in_frame': 200, 'record_out_frame': 400, 'source_fps': '25'}]
KEYS = {'Media/AI/S01-1-asset.png': 'r1/a.png', 'Media/AI/S02-1.mp4': 'r1/b.mp4'}


def test_the_accent_is_the_first_colour_the_operator_named_else_the_applications_own():
    assert S.accent_of('navy #F0A46E and white') == '#000080' and S.accent_of('#f0a46e') == '#F0A46E'
    assert S.accent_of('no preference') == S.ACCENT and S.accent_of(None) == S.ACCENT


def test_the_frame_under_a_still_is_the_shots_own_picture_at_that_moment():
    assert S.base_of(EVENTS, KEYS, 50) == {'key': 'r1/a.png', 'picture': True, 'at_s': 0}
    assert S.base_of(EVENTS, KEYS, 250) == {'key': 'r1/b.mp4', 'picture': False, 'at_s': 2.4}   # 10 frames in, plus 50 of the cut
    assert S.base_of(EVENTS, {}, 250) is None and S.base_of(EVENTS, KEYS, 900) is None


def test_a_request_for_the_worker_names_the_overlay_its_page_and_where_the_result_goes():
    store, session = started()
    S.propose(store, RUN, session, {'overlays': [A_ROW, B_ROW]}, CUTS)
    reqs = S.requests(RUN, session, ['O01', 'O02'], 'still', PAGE, EVENTS, KEYS)
    assert [(q['kind'], q['overlay']) for q in reqs] == [('overlay-still', 'O01'), ('overlay-still', 'O02')]
    assert reqs[0]['row'] == session['rows'][0]['row'] and reqs[0]['page'] == PAGE and reqs[0]['base']['key'] == 'r1/a.png' and reqs[1]['base']['key'] == 'r1/b.mp4'
    assert reqs[0]['out_key'] == f"r1/visuals/overlays/O01-{reqs[0]['digest'][:12]}.jpg" and len(reqs[0]['digest']) == 64
    clip = S.requests(RUN, session, ['O01'], 'clip', PAGE, EVENTS, KEYS)[0]
    assert clip['kind'] == 'overlay-clip' and clip['out_key'].endswith('.mov') and 'base' not in clip and clip['digest'] == reqs[0]['digest']


def test_the_clips_are_asked_for_every_approved_overlay_that_has_none():
    store, session = started()
    S.propose(store, RUN, session, {'overlays': [A_ROW, B_ROW, {**A_ROW, 'word': 30}]}, CUTS)
    session['rows'][0]['state'], session['rows'][1].update(state='approved', clip={'key': 'c'}), session['rows'][2]['state']
    assert S.clips_due(session) == []
    session['rows'][0]['state'] = 'approved'
    assert S.clips_due(session) == ['O01']
    assert S.stills_due(session) == ['O03']   # a proposed overlay with no picture yet


def job(overlay, kind, digest, status='ready', result=None, error=None, n=1):
    return {'id': n, 'status': status, 'request': {'kind': kind, 'overlay': overlay, 'digest': digest}, 'result': result or {}, 'error': error}


def test_the_workers_results_are_taken_into_the_record_by_the_overlays_own_fingerprint():
    store, session = started()
    S.propose(store, RUN, session, {'overlays': [A_ROW, B_ROW]}, CUTS)
    d1, d2 = (q['digest'] for q in S.requests(RUN, session, ['O01', 'O02'], 'still', PAGE, EVENTS, KEYS))
    changed = S.collect(session, PAGE, [job('O01', 'overlay-still', d1, result={'key': 'k1.jpg', 'bytes': 9}), job('O02', 'overlay-still', 'an older digest', result={'key': 'old.jpg'}),
                                        job('O02', 'overlay-still', d2, 'failed', error='The overlay picture could not be made: no chrome', n=2)])
    assert changed is True and session['rows'][0]['still'] == {'key': 'k1.jpg'} and session['rows'][1]['still'] is None
    assert session['rows'][1]['failed'] == 'The overlay picture could not be made: no chrome'
    session['rows'][0]['state'] = 'approved'
    S.collect(session, PAGE, [job('O01', 'overlay-clip', d1, result={'key': 'k1.mov', 'bytes': 5, 'sha256': 'x' * 64, 'frames': 45})])
    assert session['rows'][0]['clip'] == {'key': 'k1.mov', 'bytes': 5, 'sha256': 'x' * 64, 'frames': 45}
    assert S.collect(session, PAGE, []) is False


def test_a_later_good_result_clears_an_earlier_failure_and_a_running_job_is_counted():
    store, session = started()
    S.propose(store, RUN, session, {'overlays': [A_ROW]}, CUTS)
    d = S.requests(RUN, session, ['O01'], 'still', PAGE, EVENTS, KEYS)[0]['digest']
    S.collect(session, PAGE, [job('O01', 'overlay-still', d, 'failed', error='x'), job('O01', 'overlay-still', d, result={'key': 'k.jpg'}, n=2)])
    assert session['rows'][0]['still'] == {'key': 'k.jpg'} and 'failed' not in session['rows'][0]
    assert S.waiting(session, PAGE, [job('O01', 'overlay-clip', d, 'queued')]) == ['O01']
