"""Release 1 of 27 Nov 2026, phase 3, part C (SK approved: the timing is approved once, on this card, and is not asked again).

Four of eleven renders on VW-25 passed every check and were rejected for timing: the end-picture card showed the picture only. Now it lists
the parts in the order they appear, with the second and the word of each, and one approval covers the picture and that timing. A rejection
says both ways out. Each test failed first. Without a database."""
from app import visuals_stage as VS
from step6_shape import chat
from test_design130_p1_pure import motion_store
from test_design221_p1_pure import NEW, edit_plan, edit_session
from test_design221_p3c_pure import drawn_picture, two   # noqa: F401 (`drawn_picture` is autouse)
from test_visuals_stage_pure import USER, saved

entry = lambda n: {'sha256': str(n) * 64, 'frame_key': f'k{n}', 'png': f'p{n}', 'parts': {}}
ORDER = 'The parts appear in this order:'


def card(store, cues, shot=0, stills=None):
    edit_plan(store, lambda d: d['gaps'][0]['scenes'][0]['shots'][shot].setdefault('scene_motion', {}).update(cues=cues))
    edit_session(store, lambda s: s.update(motion_stills=stills or {'MO1': entry(1)}))
    return chat(store, 'still end-frame')[0]


def rows(item, after=ORDER):
    text = item['text']
    return [l[2:] for l in text[text.index(after) + len(after):].strip().split('\n') if l.startswith('- ')]


def test_the_card_lists_every_cue_in_order_with_its_second_and_its_word():
    item = card(motion_store(), [{'selector': '#arrow-down', 'at_s': 2.4}, {'selector': '#label', 'word': 'solid'}])   # "solid" is said at 0.84 s
    assert rows(item) == ['0.84 s, on the word "solid": label', '2.4 s: arrow down', 'The other parts have no set moment.']
    assert item['question'] == 'Gap G1, shot 1 (MO1): this is the drawing as it stands at the end of the shot, before any motion is added. Is the drawing right, and do the parts appear at the right moments?'


def test_a_drawing_with_no_cues_says_so_and_keeps_the_question_on_the_picture():
    item = card(motion_store(), [])
    assert rows(item) == ['The plan sets no moment for any part of this drawing.'] and item['question'].endswith('Is it right?')


def test_a_cue_with_no_second_is_shown_with_its_reason():
    store = motion_store()
    item = card(store, [{'selector': '#label', 'word': 'granite'}])   # not a word of the shot's narration
    assert rows(item)[0] == 'no second (the word "granite" is not spoken in this shot): label'
    edit_session(store, lambda s: [g.pop('timing', None) for g in s['source']['gaps'].values()])
    assert rows(chat(store, 'still end-frame')[0])[0] == 'no second (this film has no timed narration), on the word "granite": label'


def test_a_changed_second_after_the_approval_does_not_hand_the_card_out_again():
    store = motion_store()
    item = card(store, [{'selector': '#label', 'word': 'solid'}])
    item['_run']('approve', 'Approve', '')
    assert chat(store, 'still end-frame') == []
    edit_plan(store, lambda d: d['gaps'][0]['scenes'][0]['shots'][0]['scene_motion'].update(cues=[{'selector': '#label', 'at_s': 1.5}]))
    assert chat(store, 'still end-frame') == []
    again = card(motion_store(), [{'selector': '#label', 'at_s': 1.5}])
    assert again['id'] == item['id']   # the card's identity is the picture: an answer on it stands whatever the seconds


def test_a_rejection_names_both_ways_out():
    item = card(motion_store(), [{'selector': '#label', 'word': 'solid'}])
    said = item['_run']('reject', 'Reject', 'the label comes too early')['for_the_assistant']
    assert 'MO1: the operator rejected the still end-frame: "the label comes too early".' in said
    assert 'redo the still' in said and 'change the cues of MO1 in the plan' in said and 'upload it again with --still' in said


def test_several_drawings_on_one_card_each_keep_their_rows():
    store = two()
    edit_plan(store, lambda d: d['gaps'][0]['scenes'][0]['shots'][1].setdefault('scene_motion', {}).update(cues=[{'selector': '#beam', 'at_s': 1}]))
    item = card(store, [{'selector': '#wall', 'at_s': 0.5}], stills={'MO1': entry(1), 'MO2': entry(2)})
    text = item['text']
    assert text.count(ORDER) == 2 and text.index('0.5 s: wall') < text.index('(MO2)') < text.index('1 s: beam')
    assert item['question'].endswith('Are the drawings right, and do the parts appear at the right moments?')
