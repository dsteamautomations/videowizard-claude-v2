"""Release 1 of 27 Nov 2026, phase 4, part E (SK): a footage shot with no clip is named in the status and next-step lines from the moment
its gap is accepted, and asked by a card of its own: the gap's clip candidates of the plan, or the assistant's proposals, one button each
and "None of these" with words. `fill_clip` takes the clip's file name too and refuses in plain words. Without a database."""
import pytest

from app import chat_flow as CF, visuals_stage as VS
from test_batch89_pure import MEDIA
from test_visuals_stage_pure import RUN, USER, accepted, g, plan_doc, saved, session, shot, store_with

CANDIDATE = {'media_id': 'c1', 'source_name': 'C0012.MP4', 'start_s': 4.0, 'end_s': 16.0, 'use': 'clip', 'evidence': 'The mason lays the first course.'}
SAID = 'The second one, where he lays the brick.'


def film(kind='footage', candidates=()):
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, kind, subjects=[])])   # VS1 is 10 s long
    doc['gaps'][1]['candidates'] = list(candidates)
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc))
    return store_with(sess, doc)


def state(store):
    s = saved(store)
    return s, VS.current_plan(store, s)


def cards(store):
    s, p = state(store)
    return CF._footage_items({'session': s, 'plan': p, 'run': RUN, 'store': store, 'user': USER, 'outputs': [MEDIA], 'conn': None})


def due(store):
    s, p = state(store)
    return VS.footage_due(store, RUN, s, p, [MEDIA])


def test_a_footage_shot_with_no_clip_is_named_as_soon_as_its_gap_is_accepted():
    store = film()
    assert due(store).endswith('is a footage shot and has no clip yet. Propose one to three stretches for it: `vw visuals clip --shot VS1 --propose "<clip>@<seconds>, …"`.')
    assert cards(store) == []                                                                         # nothing to show yet: the line asks the assistant


def test_the_gaps_clip_candidates_make_one_card_with_the_voiceover_and_a_button_each():
    short = {**CANDIDATE, 'media_id': 'c2', 'start_s': 2.0, 'end_s': 6.0}                             # 4 s: too short for the 10 s shot
    still = {**CANDIDATE, 'use': 'still_in_film'}
    store = film(candidates=[short, still, CANDIDATE])
    card, = cards(store)
    s, p = state(store)
    assert card['kind'] == 'footage' and card['question'].endswith(': which of your clips goes here?') and card['_head'] == CF.P.heading_text(s, p, ['VS1'])
    assert [(b['label'], b['choice'], bool(b.get('needs_words'))) for b in card['buttons']] == [('C0012.MP4, from 4 s', 'c1', False), ('None of these clips', 'none', True)]
    assert card['text'] == '1. C0012.MP4, 4 to 14 s: The mason lays the first course.' and card['show'] == []
    assert 'its clip is asked of the operator on a card' in due(store)


def test_the_operators_answer_fills_the_shot_with_their_words():
    store = film(candidates=[CANDIDATE])
    cards(store)[0]['_run']('c1', SAID, '')
    a = saved(store)['assets']['VS1']
    assert (a['kind'], a['clip_id'], a['in_s'], a['out_s'], a['quote']) == ('clip', 'c1', 4.0, 14.0, SAID)
    assert cards(store) == [] and due(store) == ''


def test_none_of_these_keeps_the_shot_open_with_the_words_sent_on_and_new_proposals_make_a_new_card():
    store = film(candidates=[CANDIDATE])
    first = cards(store)[0]
    assert first['_run']('none', 'None of these clips', 'Use the wide view of the kiln.') == {'for_the_assistant': 'Use the wide view of the kiln.'}
    assert cards(store) == [] and 'VS1' not in saved(store)['assets']
    assert 'The operator said none of the stretches shown: "Use the wide view of the kiln.". Propose one to three other stretches' in due(store)
    out = VS.propose_clips(store, USER, RUN, [MEDIA], 'VS1', [{'clip': 'C0013.MP4', 'at_s': 12.5, 'why': 'the wide view'}, {'clip': 'c1', 'at_s': 0}])
    assert [r['clip_id'] for r in out['proposed']] == ['c2', 'c1']
    card, = cards(store)
    assert card['id'] != first['id'] and [b['label'] for b in card['buttons']] == ['C0013.MP4, from 12.5 s', 'C0012.MP4, from 0 s', 'None of these clips']
    assert card['text'].startswith('1. C0013.MP4, 12.5 to 22.5 s: the wide view\n2. C0012.MP4, 0 to 10 s')
    card['_run']('c1', SAID, '')
    assert saved(store)['assets']['VS1']['clip_id'] == 'c2' and 'VS1' not in saved(store).get('clip_proposals', {})


def test_a_proposal_outside_its_clip_or_more_than_three_is_refused_when_it_is_made():
    store = film()
    with pytest.raises(Exception, match=r'lies outside clip C0012.MP4 \(30.0 s\); the shot is 10 s long'):
        g(lambda: VS.propose_clips(store, USER, RUN, [MEDIA], 'VS1', [{'clip': 'c1', 'at_s': 25}]))
    with pytest.raises(Exception, match='Propose one to three stretches'):
        g(lambda: VS.propose_clips(store, USER, RUN, [MEDIA], 'VS1', [{'clip': 'c1', 'at_s': n} for n in range(4)]))
    assert cards(store) == []


def test_fill_clip_takes_the_file_name_lists_the_clips_for_an_unknown_one_and_asks_for_the_quote_in_plain_words():
    store = film()
    with pytest.raises(Exception, match=r"No clip of this film is called 'C0051_1.mp4'. Its clips: C0012.MP4 \(id c1\); C0013.MP4 \(id c2\)\."):
        g(lambda: VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'C0051_1.mp4', 0, 'yes'))
    for quote in ('', None, '  '):
        with pytest.raises(Exception, match=r"Give the operator's own words \(--quote\)\."):
            g(lambda: VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'c1', 0, quote))
    assert VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'c0013.mp4', 3.0, SAID)['clip_id'] == 'c2'   # the file name, in any case
    twice = {**MEDIA, 'summary': {'clips': MEDIA['summary']['clips'] + [{**MEDIA['summary']['clips'][0], 'id': 'c9'}]}}
    with pytest.raises(Exception, match=r"2 clips are called 'C0012.MP4': give the id\. C0012.MP4 \(id c1\); C0012.MP4 \(id c9\)\."):
        g(lambda: VS.fill_clip(store, USER, RUN, [twice], 'VS1', 'C0012.MP4', 0, 'yes'))


def test_the_route_takes_a_missing_quote_and_a_proposal():
    from app.main import ClipBody
    rid = '00000000-0000-0000-0000-000000000001'
    assert ClipBody(request_id=rid, shot_id='VS1', clip_id='c1', in_s=1, quote=None).quote is None      # refused by `fill_clip`, in plain words
    assert ClipBody(request_id=rid, shot_id='VS1', propose=[{'clip': 'c1', 'at_s': 2}]).propose == [{'clip': 'c1', 'at_s': 2}]


def test_a_film_with_no_footage_shot_sees_nothing_of_this():
    store = film(kind='video', candidates=[CANDIDATE])
    assert cards(store) == [] and due(store) == ''
