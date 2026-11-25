"""SK, 25 Nov 2026 (VW-25 issues 3a, 4 and 5; set A of design/_work/vw25-fixes-requirements-25-nov.md).
- R3a: a footage shot that shows only part of what its sentence says carries `fit` (the clip study's mark for the sentence it sits under, and
  what the piece does not show). Older way retired: no label for a part match.
- R4: the master build's refusal names each missing shot as the page does, then the review page. Older way retired: the bare "#2.1".
- R5: the master build says what it did with every note on an answer. Older way retired: a note that was not used was dropped in silence."""
import json
from pathlib import Path

import pytest

from app.errors import Problem
from app.stage2 import slides as SL, stage as S
from test_design127_review_pure import USER, answer_all, by_no, plan, saved, session_store
from test_review_page import FakeConn, FakeStore, RUN

SERVER = Path(__file__).resolve().parents[1]
PART = {'match': 'partly', 'missing': 'the finished slab'}


# ---------- a film logged by sentence: one scene, three sentences of 100 frames, a shot under each; shot 2 has an alternative ----------

def piece(i, *fits, **more):
    return {'sub_clip_id': f'c{i}:S', 'clip_id': f'c{i}', 'clip_name': f'C{i}.MP4', 'in_frame': 0, 'out_frame': 200, 'source_fps': '25', 'min_hold_s': 1.0, 'action_peak': None,
            'sfx_cues': [], 'eligibility': 'ELIGIBLE_AS_IS', 'grade': 'A', 'fit_kinds': {'BEAT_01': 'direct'}, 'fit_unit': 'sentence',
            'sentence_fits': [{'step_id': f'BEAT_01.S{n}', 'scene': 'BEAT_01', 'match': m, 'missing': x} for n, m, x in fits], **more}


def shot(sid, n=100, **kw):
    return {'sub_clip_id': sid, 'source_in_frame': 0, 'source_out_frame': n, 'timeline_frames': n, 'match': 'direct', 'evidence': 'x', **kw}


def fit_film():
    steps = [{'step_id': f'BEAT_01.S{n}', 'text': f'Sentence {n}.', 'start_frame': (n - 1) * 100, 'end_frame': n * 100} for n in (1, 2, 3)]
    pk = {'beats': [{'beat_id': 'BEAT_01', 'title': 'Need', 'timeline_start_frame': 0, 'timeline_end_frame': 300, 'target_beat_frames': 300, 'steps': steps}],
          'sub_clips': [piece(1, (1, 'PARTLY', 'the finished slab')), piece(2, (2, 'EXACT', '')), piece(3, (3, 'RELATED', 'the mixing')), piece(4, (2, 'PARTLY', '')),
                        piece(5, (1, 'EXACT', ''), (2, 'PARTLY', 'the second filler')), piece(6, fit_kinds={'BEAT_01': 'chapter'})],
          'cards': [], 'project': {}, 'timeline': {'fps': 25}, 'narration': {'words': []}}
    doc = {'options': [{'option_number': 1, 'beat_id': 'BEAT_01', 'events': [shot('c1:S'), shot('c2:S', alternatives=[shot('c4:S')]), shot('c3:S')],
                        'steps': [{'step_id': f'BEAT_01.S{n}', 'event': n, 'why': 'x'} for n in (1, 2, 3)]}]}
    return doc, pk


def fits(doc, pk):
    return {no: s.get('fit') for no, s in by_no(SL.slides(doc, pk, 25)).items() if s['type'] != 'scene'}


def store_of(doc, pk):
    """The session of test_design127_review_pure.session_store, for any small film."""
    sess = {'contract': 'vw2-stage2-session-v1', 'package': {'key': 'p', 'digest': 'pk1'}, 'current': 'd1', 'accepted': {'version': 1, 'digest': 'd1'},
            'versions': [{'version': 1, 'digest': 'd1', 'file': {'key': 'run-1/stage2/options-v1.json'}, 'slides': SL.slides(doc, pk, 25)}],
            'frames': {}, 'inspections': {}, 'renders': {}, 'decisions': {}, 'extra_rules': [], 'master': None, 'recorded': {}}
    return FakeStore({'run-1/stage2/session.json': sess, 'run-1/stage2/options-v1.json': {'document': doc, 'package_digest': 'pk1'}, 'p': pk})


def fit_store():
    return store_of(*fit_film())


def say(store, slide, action, note='', edit=None, sub=None):
    return S.decide(FakeConn({}), store, USER, RUN, slide, action, note, edit, sub)


def build(store):
    return S.build_master(FakeConn({}), store, USER, RUN)


# ---------- R3a: the mark of the sentence the shot sits under ----------

def test_a_part_match_carries_what_it_does_not_show_and_an_exact_match_is_exact():
    got = fits(*fit_film())
    assert got['1.1'] == PART                                                             # PARTLY for its own sentence, with the study's `missing`
    assert got['1.2'] == {'match': 'exact', 'missing': ''}                                # exact: the page gives it no label
    assert got['1.2A1'] == {'match': 'partly', 'missing': ''}                             # an alternative is judged with its own piece; `missing` empty
    assert got['1.3'] is None                                                             # only RELATED: the options check already refuses it as direct; no second label


def test_no_mark_for_a_film_logged_by_paragraph_or_an_option_with_no_step_map():
    doc, pk = fit_film()
    for r in pk['sub_clips']:                                                             # by paragraph: stage.prepare drops the marks per sentence
        r.pop('sentence_fits')
        r['fit_unit'] = 'paragraph'
    assert set(fits(doc, pk).values()) == {None}
    doc, pk = fit_film()
    doc['options'][0].pop('steps')
    assert set(fits(doc, pk).values()) == {None}


def test_a_shot_that_shows_two_sentences_one_exact_and_one_partly_is_a_part_match():
    doc, pk = fit_film()
    doc['options'][0]['events'][0] = shot('c5:S')                                         # c5: EXACT for sentence 1, PARTLY for sentence 2
    doc['options'][0]['steps'] = [{'step_id': 'BEAT_01.S1', 'event': 1}, {'step_id': 'BEAT_01.S2', 'event': 1}, {'step_id': 'BEAT_01.S3', 'event': 3}]
    assert fits(doc, pk)['1.1'] == {'match': 'partly', 'missing': 'the second filler'}


def test_a_shot_the_step_map_does_not_name_is_judged_against_the_sentence_it_lies_under_in_time():
    doc, pk = fit_film()
    doc['options'][0]['steps'] = [{'step_id': f'BEAT_01.S{n}', 'event': 1} for n in (1, 2, 3)]   # the map names one shot per sentence: shots 2 and 3 are named by none
    doc['options'][0]['events'][1] = shot('c4:S')                                         # frames 100-200: under sentence 2, where c4 is PARTLY
    assert fits(doc, pk)['1.2'] == {'match': 'partly', 'missing': ''}
    doc['options'][0]['events'] = [shot('c1:S', 60), shot('c5:S', 140), shot('c3:S')]     # c5 lies 60-200: 40 frames under sentence 1, 100 under sentence 2
    assert fits(doc, pk)['1.2'] == {'match': 'partly', 'missing': 'the second filler'}    # the sentence that holds most of the shot
    doc['options'][0]['events'] = [shot('c1:S', 10), shot('c5:S', 120), shot('c3:S', 170)]   # c5 lies 10-130: 90 frames under sentence 1 (EXACT), 30 under sentence 2
    assert fits(doc, pk)['1.2'] == {'match': 'exact', 'missing': ''}


def test_b_roll_a_library_clip_and_a_piece_no_longer_in_the_package_get_no_mark():
    doc, pk = fit_film()
    doc['options'][0]['events'][0]['match'] = 'b_roll'
    doc['options'][0]['events'][1]['alternatives'][0]['match'] = 'library'
    doc['options'][0]['events'][2] = shot('gone:S')
    got = fits(doc, pk)
    assert got['1.1'] is None and got['1.2A1'] is None and got['1.3'] is None
    assert by_no(SL.slides(doc, pk, 25))['1.3']['clip'] == 'gone:S'                       # the card still shows


def test_the_mark_reaches_the_page_and_the_chat_path_and_changes_no_card_of_the_film():
    doc, pk = fit_film()
    sl = SL.slides(doc, pk, 25)
    rows = {r['slide']: r for r in S._slide_rows(sl, {}, 25)}
    assert rows['1.1']['fit'] == PART and rows['1.3']['fit'] is None and rows['1']['fit'] is None
    store = fit_store()
    assert next(r for r in S.slides_view(store, RUN)['slides'] if r['slide'] == '1.1')['fit'] == PART              # `vw master slides`
    assert next(r for r in S.review_view(FakeConn({}), store, RUN)['slides'] if r['slide'] == '1.1')['fit'] == PART   # the review page
    assert not any('part' in line.lower() for s in sl for line in s['lines'])             # the review film's own cards are not changed


def test_the_mark_follows_the_piece_the_operator_put_on_the_shot():
    store = fit_store()
    row = lambda no: next(r for r in S.slides_view(store, RUN)['slides'] if r['slide'] == no)
    say(store, '1.2', 'SWAP', sub='c5:S')                                                 # shot 2 was exact; c5 is PARTLY for its sentence
    assert row('1.2')['fit'] == {'match': 'partly', 'missing': 'the second filler'} and row('1.2')['answer']['swap']['sub_clip_id'] == 'c5:S'
    say(store, '1.2', 'KEEP')                                                             # its own piece is back
    assert row('1.2')['fit'] == {'match': 'exact', 'missing': ''}
    say(store, '1.1', 'SWAP', sub='c5:S')                                                 # shot 1 was a part match; c5 is EXACT for its sentence
    assert row('1.1')['fit'] == {'match': 'exact', 'missing': ''}
    say(store, '1.1', 'SWAP', sub='c6:S')                                                 # a piece of the same chapter goes in as B-roll: no mark
    assert row('1.1')['fit'] is None and row('1.1')['answer']['swap']['match'] == 'b_roll'


def test_the_mark_never_changes_what_can_be_answered():
    doc, pk = fit_film()
    sl = SL.slides(doc, pk, 25)
    bare = [{k: v for k, v in s.items() if k != 'fit'} for s in sl]
    assert S.missing_answers(sl, {}) == S.missing_answers(bare, {}) == ['1.1', '1.2', '1.3']
    assert [(r['answerable'], r['needs_answer']) for r in S._slide_rows(sl, {}, 25)] == [(r['answerable'], r['needs_answer']) for r in S._slide_rows(bare, {}, 25)]


# ---------- R4: the refusal names the missing shots ----------

def many(n):
    """One scene of n footage shots of one second each."""
    pk = {'beats': [{'beat_id': 'BEAT_01', 'title': 'Need', 'timeline_start_frame': 0, 'timeline_end_frame': 25 * n, 'target_beat_frames': 25 * n}],
          'sub_clips': [piece(i) for i in range(1, n + 1)], 'cards': [], 'project': {}, 'timeline': {'fps': 25}, 'narration': {'words': []}}
    return {'options': [{'option_number': 1, 'beat_id': 'BEAT_01', 'events': [shot(f'c{i}:S', 25) for i in range(1, n + 1)]}]}, pk


def refusal(store):
    with pytest.raises(Problem) as e:
        build(store)
    return e.value.message


def test_the_refusal_names_one_missing_shot_as_the_page_does_and_gives_the_review_page():
    store = session_store()
    answer_all(store, **{'2.1': None})
    assert refusal(store) == 'Every shot needs an answer; missing: Scene 2 · Shot 1 (#2.1). Review page: /runs/VW-9/review'


def test_the_refusal_names_five_and_says_how_many_more():
    five = ', '.join(f'Scene 1 · Shot {i} (#1.{i})' for i in range(1, 6))
    assert refusal(store_of(*many(5))) == f'Every shot needs an answer; missing: {five}. Review page: /runs/VW-9/review'
    assert refusal(store_of(*many(7))) == f'Every shot needs an answer; missing: {five} and 2 more. Review page: /runs/VW-9/review'


def test_an_alternative_is_named_once_its_shot_is_rejected():
    store = session_store()
    answer_all(store)
    assert S.slides_view(store, RUN)['waiting'] == []
    say(store, '1.3', 'REJECT')
    assert S.slides_view(store, RUN)['waiting'] == ['1.3A1']                              # the page's list comes from the server on every read
    assert refusal(store) == 'Every shot needs an answer; missing: Scene 1 · Shot 3 · Alternative 1 (#1.3A1). Review page: /runs/VW-9/review'


# ---------- R5: what the build did with every note ----------

PASSED = 'passed to the visuals stage as the request for this stretch'


def spare(store):
    """c5 becomes a piece that can go on a shot of scene 1 (as test_review_page_browser.with_spare_piece)."""
    pk = json.loads(store.files['p'])
    pk['sub_clips'][4].update(fit_kinds={'BEAT_01': 'chapter'}, eligibility='ELIGIBLE_AS_IS', grade='A')
    store.files['p'] = json.dumps(pk).encode('utf-8')
    return store


def test_no_note_gives_an_empty_list_and_a_note_of_spaces_is_not_a_note():
    store = session_store()
    answer_all(store)
    assert build(store)['notes'] == []
    say(store, '3.1', 'KEEP', '   ')
    say(store, '2.1', 'KEEP')                                                             # Keep AI on an all-AI scene: no note there
    assert build(store)['notes'] == []


def test_a_reject_that_becomes_an_ai_stretch_passes_its_note_on():
    store = session_store()
    answer_all(store, **{'1.3': None})
    say(store, '1.3', 'REJECT', 'show the finished slab')
    say(store, '1.3A1', 'REJECT')
    out = build(store)
    assert out['notes'] == [{'slide': '1.3', 'title': 'Scene 1 · Shot 3', 'answer': 'REJECT', 'note': 'show the finished slab', 'outcome': PASSED}]
    assert 'the operator: show the finished slab' in plan(store)['gaps'][1]['reason']     # what the visuals stage receives is unchanged
    assert set(out) >= {'version', 'events', 'gaps', 'flags', 'duration_frames', 'next'}  # no gate: the build goes through as before


def test_a_note_is_not_used_when_the_kept_alternative_takes_the_place():
    store = session_store()
    answer_all(store, **{'1.3': None})
    say(store, '1.3', 'REJECT', 'use the wide shot')
    say(store, '1.3A1', 'KEEP', 'this one is fine')
    assert build(store)['notes'] == [
        {'slide': '1.3', 'title': 'Scene 1 · Shot 3', 'answer': 'REJECT', 'note': 'use the wide shot', 'outcome': "not used: the kept alternative took the shot's place"},
        {'slide': '1.3A1', 'title': 'Scene 1 · Shot 3 · Alternative 1', 'answer': 'KEEP', 'note': 'this one is fine', 'outcome': 'not used: a note on an alternative is not passed on'}]
    assert 'use the wide shot' not in json.dumps(plan(store)['gaps'])


def test_a_note_on_a_keep_a_trim_or_another_clip_is_not_used():
    store = spare(session_store())
    answer_all(store, **{'1.2': None, '1.3': None, '3.1': None})
    say(store, '1.2', 'TRIM', 'without its first frames', 'in:+5,out:+5')
    say(store, '1.3', 'SWAP', 'first half of C5', sub='c5:S')
    say(store, '3.1', 'KEEP', 'then the next clip too')
    assert [(n['slide'], n['answer'], n['outcome']) for n in build(store)['notes']] == [
        ('1.2', 'TRIM', 'not used: the shot is trimmed'), ('1.3', 'SWAP', "not used: the shot is replaced by the operator's clip"), ('3.1', 'KEEP', 'not used: the shot is kept')]


def test_a_long_note_is_whole_in_the_record_and_cut_at_400_characters_in_the_list():
    store = session_store()
    answer_all(store, **{'3.1': None})
    say(store, '3.1', 'KEEP', 'n' * 500)
    out = build(store)
    assert out['notes'][0]['note'] == 'n' * 400 and saved(store)['decisions']['3.1']['note'] == 'n' * 500 and plan(store)['decisions']['3.1']['note'] == 'n' * 500


def test_a_note_in_another_script_is_passed_as_written():
    store = session_store()
    answer_all(store, **{'1.3': None})
    say(store, '1.3', 'REJECT', 'முடிந்த தளத்தைக் காட்டுங்கள் · तैयार स्लैब दिखाएँ')
    say(store, '1.3A1', 'REJECT')
    out = build(store)
    assert out['notes'][0]['note'] == 'முடிந்த தளத்தைக் காட்டுங்கள் · तैयार स्लैब दिखाएँ' and out['notes'][0]['outcome'] == PASSED
    assert 'the operator: முடிந்த தளத்தைக் காட்டுங்கள் · तैयार स्लैब दिखाएँ' in plan(store)['gaps'][1]['reason']


def test_two_rejects_side_by_side_merge_into_one_stretch_and_each_note_is_listed_under_its_own_shot():
    store = session_store()
    answer_all(store, **{'1.2': None, '1.3': None})
    say(store, '1.2', 'REJECT', 'the finished slab')
    say(store, '1.3', 'REJECT', 'a slab beside a normal slab')
    say(store, '1.3A1', 'REJECT')
    out = build(store)
    assert [(n['slide'], n['title'], n['note'], n['outcome']) for n in out['notes']] == [
        ('1.2', 'Scene 1 · Shot 2', 'the finished slab', PASSED), ('1.3', 'Scene 1 · Shot 3', 'a slab beside a normal slab', PASSED)]
    reasons = [g['reason'] for g in plan(store)['gaps']]
    assert len(reasons) == 2 and 'the operator: the finished slab' in reasons[0] and 'the operator: a slab beside a normal slab' in reasons[0]   # scene 1 is one stretch
    assert build(store)['notes'] == out['notes'] and saved(store)['master']['version'] == 2   # built a second time (a new master version): the list comes again


def test_a_note_on_the_ai_shot_of_an_all_ai_scene_can_only_come_from_the_chat_and_is_listed_as_not_used():
    store = session_store()
    answer_all(store, **{'2.1': None})
    say(store, '2.1', 'KEEP', 'make it a diagram')                                        # the page has no note box on Keep AI; `vw master decide --note` can send one
    assert build(store)['notes'] == [{'slide': '2.1', 'title': 'Scene 2 · Shot 1', 'answer': 'KEEP', 'note': 'make it a diagram', 'outcome': 'not used: a note on an AI shot is not passed on'}]


def test_the_instruction_tells_the_assistant_to_report_every_note_and_ask_about_each_one_not_used():
    master = next(s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'master')
    sentence = 'After the build, tell the operator in one message what it did with each note (its `notes`), and ask about each note not used before going on.'
    builds = [t for t in master['steps'] if '`vw master build`' in t]
    assert len(builds) == 2 and all(sentence in t for t in builds)                         # the film with footage and the film with library pieces only
    assert 'Rejection notes stay with this run.' in builds[0]                             # still true, still said
