"""design/127: the review page and film by scene and shot. A scene is a header; every shot is numbered (1.2) and answered KEEP, REJECT or TRIM;
an AI shot inside a scene needs nothing; an all-AI scene's one shot takes Keep AI / Find footage; an alternative belongs to a shot (1.2A1) and opens
only when its shot is rejected; B-roll is a shot (match b_roll), no question, never a clip that is a direct match elsewhere; the words are on screen;
cards only before a scene and an alternative; one colour per scene; the older ways refused by name."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.errors import Problem
from app.stage2 import slides as SL, stage as S, validator as V
from test_design91_b2_pure import POLICY, doc as b2_doc, ev, option, package as b2_package
from test_review_page import FakeConn, FakeStore, RUN

HERE = Path(__file__).resolve().parent
APP = HERE.parent / 'app'
ROOT = HERE.parent.parent
USER = {'id': 'u1'}


# ---------- a small film: scene 1 = AI 100 + shot c1 75 + B-roll c2 75 (c2 has an alternative c4); scene 2 all AI; scene 3 = c3 100 (a reuse note) ----------

def words(*spans):
    return [{'id': f'w{i}', 'text': t, 'start_frame': a, 'end_frame': a + 5} for i, (t, a) in enumerate(spans)]


def film():
    pk = {'beats': [{'beat_id': 'BEAT_01', 'title': 'Need', 'timeline_start_frame': 0, 'timeline_end_frame': 250, 'target_beat_frames': 250},
                    {'beat_id': 'BEAT_02', 'title': 'Why', 'timeline_start_frame': 250, 'timeline_end_frame': 350, 'target_beat_frames': 100},
                    {'beat_id': 'BEAT_03', 'title': 'Laying', 'timeline_start_frame': 350, 'timeline_end_frame': 450, 'target_beat_frames': 100}],
          'sub_clips': [{'sub_clip_id': f'c{i}:S', 'clip_id': f'c{i}', 'clip_name': f'C{i}.MP4', 'in_frame': 0, 'out_frame': 200, 'source_fps': '25', 'min_hold_s': 1.0,
                         'action_peak': None, 'sfx_cues': []} for i in range(1, 6)],
          'cards': [{'clip_id': 'c2', 'descriptive_name': 'workers on site'}], 'project': {}, 'timeline': {'fps': 25},
          'narration': {'words': words(('Houses', 10), ('cost', 120), ('less.', 180), ('Bricks', 210), ('save', 260), ('Lay', 360))}}
    shot = lambda sid, n, **kw: {'sub_clip_id': sid, 'source_in_frame': 0, 'source_out_frame': n, 'timeline_frames': n, 'match': 'direct', 'evidence': 'x', **kw}
    doc = {'options': [{'option_number': 1, 'beat_id': 'BEAT_01', 'events': [{'blank': True, 'timeline_frames': 100, 'intent': 'a diagram'}, shot('c1:S', 75),
                                                                              shot('c2:S', 75, match='b_roll', alternatives=[shot('c4:S', 75)])]},
                       {'option_number': 2, 'beat_id': 'BEAT_02', 'events': [{'blank': True, 'timeline_frames': 100, 'intent': 'savings'}]},
                       {'option_number': 3, 'beat_id': 'BEAT_03', 'events': [shot('c3:S', 100, note={'kind': 'reuse', 'question': 'C3 again?'})]}]}
    return doc, pk


def by_no(sl):
    return {s['no']: s for s in sl}


# ---------- slides ----------

def test_a_scene_is_a_header_and_every_shot_is_numbered_in_play_order():
    doc, pk = film()
    sl = SL.slides(doc, pk, 25)
    assert [(s['no'], s['type']) for s in sl] == [('1', 'scene'), ('1.1', 'ai'), ('1.2', 'shot'), ('1.3', 'shot'), ('1.3A1', 'alternative'),
                                                 ('2', 'scene'), ('2.1', 'ai'), ('3', 'scene'), ('3.1', 'shot')]
    assert all(s['scheme'] == 3 for s in sl)
    b = by_no(sl)
    assert b['1']['lines'] == ['Scene 1', 'Need', 'Total time: 10.0 s', 'Shots: 3 (1 made with AI, 2 footage)']
    assert b['2']['lines'] == ['Scene 2', 'Why', 'Total time: 4.0 s', 'Shots: 1 (made with AI)']
    assert b['1.2']['title'] == 'Scene 1 · Shot 2' and b['1.3A1']['title'] == 'Scene 1 · Shot 3 · Alternative 1' and b['1.3A1']['of'] == '1.3'
    assert b['1.3']['b_roll'] and not b['1.2']['b_roll'] and b['3.1']['note'] == {'kind': 'reuse', 'question': 'C3 again?'}
    assert b['2.1']['ai_only'] and not b['1.1'].get('ai_only')
    assert not any('|' in line for s in sl for line in s['lines'])


def test_the_words_of_each_shot_are_the_narration_words_inside_its_time():
    doc, pk = film()
    b = by_no(SL.slides(doc, pk, 25))
    assert b['1.1']['words'] == 'Houses' and b['1.2']['words'] == 'cost' and b['1.3']['words'] == 'less. Bricks' and b['1.3A1']['words'] == 'less. Bricks'
    assert b['2.1']['words'] == 'save' and b['3.1']['words'] == 'Lay'


def test_a_long_ai_scene_shows_at_most_six_lines_of_words():
    lines = SL.said_lines(' '.join(['word'] * 200))
    assert len(lines) == 6 and lines[-1].endswith('...') and SL.said_lines('') == []


def test_one_colour_per_scene_neighbours_never_share_one_and_eight_repeat():
    doc, pk = film()
    sl = SL.slides(doc, pk, 25)
    colours = {s['number']: s['colour'] for s in sl}
    assert len(set(colours.values())) == 3 and all(s['colour'] == colours[s['number']] for s in sl)
    assert [SL.scene_colour(n) for n in range(1, 10)][8] == SL.scene_colour(1) and len({SL.scene_colour(n) for n in range(1, 9)}) == 8


# ---------- answers ----------

def test_what_needs_an_answer():
    doc, pk = film()
    sl = SL.slides(doc, pk, 25)
    b = by_no(sl)
    assert S.missing_answers(sl, {}) == ['1.2', '1.3', '2.1', '3.1']
    assert S.needs_answer(b['1'], sl, {})[0] is False and S.needs_answer(b['1.1'], sl, {})[0] is False
    assert S.needs_answer(b['1.3A1'], sl, {}) == (False, 'answer Scene 1 · Shot 3 first')
    assert S.needs_answer(b['1.3A1'], sl, {'1.3': {'action': 'KEEP'}}) == (False, 'Shot 3 is kept: its alternatives are off')
    assert S.needs_answer(b['1.3A1'], sl, {'1.3': {'action': 'REJECT'}}) == (True, None)
    assert S.missing_answers(sl, {'1.2': {'action': 'KEEP'}, '1.3': {'action': 'REJECT'}, '2.1': {'action': 'KEEP'}, '3.1': {'action': 'KEEP'}}) == ['1.3A1']


def session_store():
    doc, pk = film()
    sl = SL.slides(doc, pk, 25)
    sess = {'contract': 'vw2-stage2-session-v1', 'package': {'key': 'p', 'digest': 'pk1'}, 'current': 'd1', 'accepted': {'version': 1, 'digest': 'd1'},
            'versions': [{'version': 1, 'digest': 'd1', 'file': {'key': 'run-1/stage2/options-v1.json'}, 'slides': sl}],
            'frames': {}, 'inspections': {}, 'renders': {}, 'decisions': {}, 'extra_rules': [], 'master': None, 'recorded': {}}
    return FakeStore({'run-1/stage2/session.json': sess, 'run-1/stage2/options-v1.json': {'document': doc, 'package_digest': 'pk1'}, 'p': pk})


def saved(store):
    return json.loads(store.files['run-1/stage2/session.json'])


def decide(store, slide, action, edit=None):
    return S.decide(FakeConn({}), store, USER, RUN, slide, action, '', edit)


@pytest.mark.parametrize('slide, action, message', [
    ('1', 'KEEP', r'Scene 1 is a header: decide its shots: 1\.2, 1\.3'),
    ('1.1', 'KEEP', r'Scene 1 · Shot 1 is made with AI inside the scene: it needs no answer'),
    ('1.2', 'KEEP_WITH_EDIT', r'KEEP_WITH_EDIT is retired: use TRIM on the shot'),
    ('1.2', 'DROP', r'DROP is retired: answer the shot KEEP, REJECT or TRIM'),
    ('1.2', 'TRIM', r'TRIM needs --edit "in:±frames,out:±frames"'),
    ('2.1', 'TRIM', r'Scene 2 · Shot 1 is made with AI: Keep AI \(KEEP\) or Find footage \(REJECT\)'),
    ('1.3A1', 'KEEP', r'answer Scene 1 · Shot 3 first: its alternatives open when it is rejected'),
    ('1A', 'KEEP', r'No slide #1A: the labels are now 1\.2 \(Scene 1 · Shot 2\)'),
])
def test_wrong_answers_are_refused_by_name(slide, action, message):
    with pytest.raises(Problem, match=message):
        decide(session_store(), slide, action)


def test_an_alternative_opens_when_its_shot_is_rejected_and_closes_when_it_is_kept():
    store = session_store()
    decide(store, '1.3', 'REJECT')
    assert decide(store, '1.3A1', 'KEEP')['action'] == 'KEEP'
    with pytest.raises(Problem, match='TRIM is for a footage shot'):
        decide(store, '1.3A1', 'TRIM', 'in:0,out:-5')
    decide(store, '1.3', 'KEEP')
    view = S.slides_view(store, RUN)
    alt = next(r for r in view['slides'] if r['slide'] == '1.3A1')
    assert alt['needs_answer'] is False and alt['why'] == 'Shot 3 is kept: its alternatives are off' and alt['answer']['action'] == 'KEEP'


def test_a_version_proposed_in_the_old_form_is_refused():
    store = session_store()
    sess = saved(store)
    for s in sess['versions'][0]['slides']:
        s['scheme'] = 2
    store.files['run-1/stage2/session.json'] = json.dumps(sess).encode('utf-8')
    with pytest.raises(Problem, match=r'proposed in the old form: the assistant proposes it again \(`vw options propose`\)'):
        S.slides_view(store, RUN)
    assert S.review_view(FakeConn({}), store, RUN)['state'] == 'old_form'


# ---------- the master build ----------

def answer_all(store, **over):
    base = {'1.2': 'KEEP', '1.3': 'KEEP', '2.1': 'KEEP', '3.1': 'KEEP', **over}
    for k, v in base.items():
        if v:
            decide(store, k.replace('_', '.'), *(v if isinstance(v, tuple) else (v,)))


def plan(store):
    return saved(store)['master']['plan']


def test_build_keeps_shots_and_a_kept_reuse_note_approves_the_reuse():
    store = session_store()
    answer_all(store)
    S.build_master(FakeConn({}), store, USER, RUN)
    m = plan(store)
    assert [(e['kind'], e.get('sub_clip_id')) for e in m['events']] == [('gap', None), ('event', 'c1:S'), ('event', 'c2:S'), ('gap', None), ('event', 'c3:S')]
    assert m['events'][-1]['reuse_approved'] is True


def test_build_a_rejected_shot_takes_its_kept_alternative_else_becomes_ai_with_its_words():
    store = session_store()
    answer_all(store, **{'1.3': 'REJECT'})
    decide(store, '1.3A1', 'KEEP')
    S.build_master(FakeConn({}), store, USER, RUN)
    assert [e.get('sub_clip_id') for e in plan(store)['events']][:3] == [None, 'c1:S', 'c4:S']
    decide(store, '1.3A1', 'REJECT')
    S.build_master(FakeConn({}), store, USER, RUN)
    m = plan(store)
    assert [e['kind'] for e in m['events']][:3] == ['gap', 'event', 'gap'] and m['events'][2]['timeline_frames'] == 75
    assert 'in place of rejected Scene 1 · Shot 3: less. Bricks' in m['gaps'][1]['reason']


def test_build_refuses_a_rejection_that_leaves_ai_under_3_s_between_two_shots():
    doc, pk = film()
    doc['options'][2]['events'] = [{'sub_clip_id': f'c{i}:S', 'source_in_frame': 0, 'source_out_frame': n, 'timeline_frames': n, 'match': 'direct', 'evidence': 'x'}
                                   for i, n in ((3, 40), (5, 30), (4, 30))]
    store = session_store()
    store.files['run-1/stage2/options-v1.json'] = json.dumps({'document': doc, 'package_digest': 'pk1'}).encode('utf-8')
    sess = saved(store)
    sess['versions'][0]['slides'] = SL.slides(doc, pk, 25)
    store.files['run-1/stage2/session.json'] = json.dumps(sess).encode('utf-8')
    answer_all(store, **{'3.1': 'KEEP', '3.2': 'REJECT', '3.3': 'KEEP'})
    with pytest.raises(Problem, match=r'Rejecting Scene 3 · Shot 2 leaves 1\.2 s of AI between two shots: keep it, trim a neighbour, or reject a neighbour too'):
        S.build_master(FakeConn({}), store, USER, RUN)


def test_build_find_footage_on_an_all_ai_scene_sends_it_back():
    store = session_store()
    answer_all(store, **{'2.1': 'REJECT'})
    with pytest.raises(Problem, match=r'Scene 2: the operator asked to find footage'):
        S.build_master(FakeConn({}), store, USER, RUN)


def test_build_applies_a_trim_and_refuses_one_that_changes_the_scene_length():
    store = session_store()
    answer_all(store, **{'1.2': ('TRIM', 'in:+5,out:+5')})
    S.build_master(FakeConn({}), store, USER, RUN)
    e = next(e for e in plan(store)['events'] if e.get('sub_clip_id') == 'c1:S')
    assert (e['source_in_frame'], e['source_out_frame']) == (5, 80)
    decide(store, '1.2', 'TRIM', 'in:0,out:-10')
    with pytest.raises(Problem, match='240 frames'):
        S.build_master(FakeConn({}), store, USER, RUN)


# ---------- the review film ----------

def items_of():
    doc, pk = film()
    sl = SL.slides(doc, pk, 25)
    return SL.review_items(doc, pk, sl, lambda evs: [{'kind': 'event', 'timeline_frames': e['timeline_frames'], 'sub_clip_id': e['sub_clip_id']} for e in evs], 25), sl


def test_cards_only_before_a_scene_and_an_alternative_and_the_alternative_replays_its_words():
    items, _ = items_of()
    slates = [it['slide'] for it in items if it['kind'] == 'slate']
    assert slates == ['1', '1.3A1', '2', '3']
    i = next(k for k, it in enumerate(items) if it['kind'] == 'slate' and it['slide'] == '1.3A1')
    assert items[i]['lines'][0] == 'Scene 1 · Shot 3 · Alternative 1'
    assert items[i + 1] == {'kind': 'narration', 'start_s': 175 / 25, 'end_s': 250 / 25} and items[i + 2]['sub_clip_id'] == 'c4:S'
    narr = [(it['start_s'], it['end_s']) for it in items if it['kind'] == 'narration']
    assert narr == [(0.0, 10.0), (7.0, 10.0), (10.0, 14.0), (14.0, 18.0)]


def test_every_footage_piece_carries_its_strip_and_an_ai_card_shows_its_words():
    items, _ = items_of()
    shots = [it for it in items if it['kind'] == 'event']
    assert [it['strip']['label'] for it in shots] == ['Scene 1 · Shot 2', 'Scene 1 · Shot 3', 'Scene 1 · Shot 3 · Alternative 1', 'Scene 3 · Shot 1']
    assert [it['strip']['b_roll'] for it in shots] == [False, True, False, False] and shots[1]['strip']['words'] == 'less. Bricks'
    card = next(it for it in items if it['kind'] == 'card')
    assert card['slide'] == '1.1' and card['lines'][:3] == ['Scene 1 · Shot 1 · made with AI', 'Time: 4.0 s', '"Houses"']
    assert all(it.get('colour') for it in items if it['kind'] in ('slate', 'card')) and all(it['strip'].get('colour') for it in shots)


def test_cues_give_each_row_its_start_and_end():
    items, _ = items_of()
    cues = S.slide_cues({'items': items}, 25)
    assert cues['1'] == [0.0, 19.0] and cues['1.1'] == [3.0, 7.0] and cues['1.3'] == [10.0, 13.0] and cues['1.3A1'] == [13.0, 19.0]
    assert cues['2.1'] == [22.0, 26.0] and set(cues) == {'1', '1.1', '1.2', '1.3', '1.3A1', '2', '2.1', '3', '3.1'}


def test_the_strip_and_the_card_are_drawn(tmp_path):
    pytest.importorskip('PIL')
    from PIL import Image
    from app.stage2 import render as R
    R.strip_png({'label': 'Scene 1 · Shot 3', 'words': 'less. Bricks ' * 12, 'b_roll': True, 'colour': '#1D9E75'}, 640, 360, tmp_path / 's.png')
    im = Image.open(tmp_path / 's.png').convert('RGB')
    assert im.size[0] == 640 and any(im.getpixel((x, y)) == R.DARK_RED for x in range(0, 640, 2) for y in range(0, im.size[1], 2))
    R.slate_png(['Scene 1', 'Need', 'Total time: 10.0 s'], 640, 360, tmp_path / 'c.png', '#1D9E75')
    assert Image.open(tmp_path / 'c.png').convert('RGB').getpixel((2, 180)) == (0x1D, 0x9E, 0x75)


# ---------- the options check ----------

def pk4():
    pk = b2_package()
    for r in [r for r in pk['sub_clips'] if r['clip_id'] == 'clip2']:
        pk['sub_clips'].append({**deepcopy(r), 'sub_clip_id': r['sub_clip_id'].replace('clip2', 'clip3'), 'clip_id': 'clip3'})
    return pk


def refusals(d, pk=None):
    return V.validate_options(deepcopy(d), pk or pk4(), POLICY)['refusals']


def test_an_alternative_of_the_same_length_on_an_unused_clip_passes():
    d = b2_doc()
    d['options'][1]['events'][0]['alternatives'] = [ev('clip3:SUB_01', 0, 13)]
    assert refusals(d) == []


@pytest.mark.parametrize('alt, message', [
    (ev('clip3:SUB_01', 0, 12), 'an alternative fills its shot\'s time exactly: 13 frames'),
    (ev('clip0:SUB_02', 25, 38), 'alternative 1 uses clip clip0, which is already in the cut'),
    (ev('clip3:SUB_01', 30, 43), 'G1 source frames'),
])
def test_a_wrong_alternative_is_refused_by_name(alt, message):
    d = b2_doc()
    d['options'][1]['events'][0]['alternatives'] = [alt]
    assert any(message in r for r in refusals(d))


def test_an_alternative_on_an_ai_shot_is_refused():
    d = b2_doc()
    d['options'][1]['events'] = [{'blank': True, 'timeline_frames': 13, 'intent': 'bricks', 'short_reason': 'short', 'alternatives': [ev('clip3:SUB_01', 0, 13)]}]
    d['options'][1]['steps'] = [{'step_id': 'BEAT_02.S1', 'event': 1}]
    assert any('an AI shot has no clip to replace' in r for r in refusals(d))


def test_the_second_cut_of_a_scene_and_the_decision_field_are_retired():
    d = b2_doc()
    d['options'].append(option(3, 'BEAT_02', 'SECONDARY', [ev('clip3:SUB_01', 0, 13)]))
    assert any('a second cut of a scene is retired; give an alternative for a shot' in r for r in refusals(d))
    d = b2_doc()
    d['options'][1]['events'][0]['decision'] = {'kind': 'check_by_eye', 'question': 'right step?'}
    assert any('decision is retired: a doubtful shot carries a note {kind, question}' in r for r in refusals(d))
    d = b2_doc()
    d['options'][1]['events'][0]['note'] = {'kind': 'b_roll', 'question': 'b-roll?'}
    assert any('B-roll is a shot with match b_roll; it needs no question' in r for r in refusals(d))


def test_b_roll_needs_no_question_and_never_takes_a_clip_used_as_a_direct_match():
    d = b2_doc()
    d['options'][1]['events'][0]['match'] = 'b_roll'
    assert refusals(d) == []
    d['options'][1]['events'][0] = ev('clip0:SUB_02', 25, 38, match='b_roll', note={'kind': 'reuse', 'question': 'again?'})
    assert any('B-roll comes after the exact matches: clip clip0 is a direct match in option #1' in r for r in refusals(d))


def test_a_reuse_and_a_poor_quality_clip_need_their_note():
    d = b2_doc()
    d['options'][1]['events'][0] = ev('clip0:SUB_02', 25, 38)
    assert any('needs a note of kind reuse' in r for r in refusals(d))
    d['options'][1]['events'][0]['note'] = {'kind': 'reuse', 'question': 'again?'}
    assert not any('Q4' in r for r in refusals(d))
    pk = pk4()
    pk['sub_clips'][4]['grade'] = 'C'
    d = b2_doc()
    assert any('note (kind poor_quality)' in r for r in refusals(d, pk))


# ---------- the page, the words, the chat path ----------

def test_the_page_pauses_for_answers_marks_b_roll_and_alternatives_and_drops_the_old_rows():
    html = (APP / 'templates' / 'review.html').read_text(encoding='utf-8')
    for s in ('Pause for answers', 'Answer to continue', 'Continue', 'class="broll"', 'alternative (dashed)', 'Keep AI', 'Find footage', 'localStorage', "'TRIM'"):
        assert s in html, s
    for s in ('second choice', 'KEEP_WITH_EDIT', "'DROP'", 'parts_decide', 'backup'):
        assert s not in html, s


def test_the_instructions_and_the_chat_path_speak_of_shots():
    proc = json.loads((APP.parent / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    text = json.dumps([s for s in proc['stages'] if s['name'] in ('options', 'master')], ensure_ascii=False)
    for s in ('SECONDARY', 'second choice', 'KEEP_WITH_EDIT', 'DROP', 'Decision slides', 'A large share of blanks is fine'):
        assert s not in text, s
    for s in ('ROUND 2', 'alternatives', 'the shot before and the shot after', 'TRIM', '1.2'):
        assert s in text, s
    for path in ('plugin/commands/vw.md', 'plugin/agents/vw-scene-review.md'):
        t = (ROOT / path).read_text(encoding='utf-8')
        assert 'KEEP_WITH_EDIT' not in t and 'SECONDARY' not in t and 'alternatives' in t, path
    main = (APP / 'main.py').read_text(encoding='utf-8')
    assert "Literal['KEEP', 'REJECT', 'KEEP_WITH_EDIT', 'DROP']" not in main
