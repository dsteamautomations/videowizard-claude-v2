"""design/52 D and E: delivery direction on the accepted script, pure. Sentences by passage, the validator, tags applied before
sentences, and the alignment stripped back to the accepted script whether or not the provider timed the tag characters."""
import pytest

from app import voice_direction as VD

TEXT = 'Earth blocks are pressed. Not fired.\n\nThey save fuel! Really.\n'


def test_sentences_are_numbered_inside_their_passage_with_offsets():
    rows = VD.sentences_of(TEXT)
    assert [(r['passage_id'], r['sentence'], r['first_words']) for r in rows] == \
        [('P001', 1, 'Earth blocks are pressed.'), ('P001', 2, 'Not fired.'), ('P002', 1, 'They save fuel!'), ('P002', 2, 'Really.')]
    assert TEXT[rows[2]['start']:rows[2]['end']] == 'They save fuel!'


def good(items=None, register='[measured]'):
    return {'register': register, 'items': items if items is not None else [{'passage_id': 'P002', 'sentence': 1, 'tag': '[with weight on the figures]', 'reason': 'the claim'}]}


def test_validator_accepts_a_sparse_list_and_names_what_it_refuses():
    assert VD.validate(good(), TEXT) == []
    assert VD.validate(good([]), TEXT) == []
    assert 'register' in VD.validate(good(register=''), TEXT)[0]
    assert 'P009' in VD.validate(good([{'passage_id': 'P009', 'sentence': 1, 'tag': '[warm]', 'reason': ''}]), TEXT)[0]
    assert 'sentence 3' in VD.validate(good([{'passage_id': 'P001', 'sentence': 3, 'tag': '[warm]', 'reason': ''}]), TEXT)[0]
    two = [{'passage_id': 'P001', 'sentence': 1, 'tag': '[warm]', 'reason': ''}, {'passage_id': 'P001', 'sentence': 1, 'tag': '[softly]', 'reason': ''}]
    assert 'one tag' in VD.validate(good(two), TEXT)[0]
    assert 'square brackets' in VD.validate(good([{'passage_id': 'P001', 'sentence': 1, 'tag': 'warm', 'reason': ''}]), TEXT)[0]


@pytest.mark.parametrize('tag, word', [('[laughs]', 'laugh'), ('[long pause]', 'pause'), ('[softly, then a sigh]', 'sigh'), ('[a beat, then on]', 'beat'),
                                       ('[British accent]', 'accent'), ('[clears throat]', 'clears throat'), ('[silence]', 'silence')])
def test_validator_refuses_reactions_pauses_and_accents(tag, word):
    problems = VD.validate(good([{'passage_id': 'P001', 'sentence': 1, 'tag': tag, 'reason': ''}]), TEXT)
    assert problems and word in problems[0]
    assert 'register' in VD.validate(good(register=tag), TEXT)[0]


def test_validator_caps_tag_length():
    assert 'characters' in VD.validate(good([{'passage_id': 'P001', 'sentence': 1, 'tag': '[' + 'x' * 70 + ']', 'reason': ''}]), TEXT)[0]


def test_apply_puts_the_register_first_and_each_tag_before_its_sentence():
    tagged, spans = VD.apply(TEXT, good()['items'], '[measured]')
    assert tagged == '[measured] Earth blocks are pressed. Not fired.\n\n[with weight on the figures] They save fuel! Really.\n'
    assert [tagged[a:b] for a, b in spans] == ['[measured] ', '[with weight on the figures] ']
    assert VD.untag(tagged, spans) == TEXT


def test_apply_with_tweaks_replaces_a_tag_for_one_voice_without_touching_the_base():
    base = good()['items']
    tagged, _ = VD.apply(TEXT, base, '[measured]', tweaks=[{'passage_id': 'P002', 'sentence': 1, 'tag': '[brisk]'}, {'passage_id': 'P001', 'sentence': 2, 'tag': '[softly]'}])
    assert tagged == '[measured] Earth blocks are pressed. [softly] Not fired.\n\n[brisk] They save fuel! Really.\n'
    assert base[0]['tag'] == '[with weight on the figures]'


def alignment(text, per=0.1):
    return {'characters': list(text), 'character_start_times_seconds': [round(i * per, 3) for i in range(len(text))],
            'character_end_times_seconds': [round((i + 1) * per, 3) for i in range(len(text))]}


def test_strip_removes_timed_tag_characters_and_keeps_true_times():
    tagged, spans = VD.apply(TEXT, good()['items'], '[measured]')
    stripped = VD.strip(alignment(tagged), tagged, spans, TEXT)
    assert ''.join(stripped['characters']) == TEXT
    i = TEXT.index('They')
    assert stripped['character_start_times_seconds'][i] == round(tagged.index('They') * 0.1, 3)   # the real time of that character, not shifted


def test_strip_is_a_no_op_when_the_provider_dropped_the_tags():
    tagged, spans = VD.apply(TEXT, good()['items'], '[measured]')
    stripped = VD.strip(alignment(TEXT), tagged, spans, TEXT)
    assert ''.join(stripped['characters']) == TEXT and stripped['character_end_times_seconds'][-1] == alignment(TEXT)['character_end_times_seconds'][-1]


def test_strip_refuses_anything_else():
    tagged, spans = VD.apply(TEXT, good()['items'], '[measured]')
    with pytest.raises(ValueError):
        VD.strip(alignment(tagged.replace('Really', 'Truly')), tagged, spans, TEXT)


def test_digest_depends_on_the_tags_only():
    a = VD.digest(good()['items'], '[measured]')
    assert a == VD.digest([{**good()['items'][0], 'reason': 'other words'}], '[measured]') and a != VD.digest(good()['items'], '[warm]')


def test_pieces_are_cut_from_the_directed_text_and_the_record_keeps_the_accepted_one():
    from app import narration_pieces as NP
    tagged, spans = VD.apply(TEXT, good()['items'], '[measured]')
    snap = {'text': TEXT, 'text_tagged': tagged, 'tag_spans': spans, 'voice_id': 'v', 'model_id': 'eleven_v4', 'settings': {}, 'format': 'mp3',
            'pieces': NP.split_for_narration(tagged, 10000)}
    pieces = NP.pieces_of(snap)
    assert ''.join(p['text'] for p in pieces).replace('\n', '') == tagged.replace('\n\n', '').rstrip('\n') and NP.provider_text(snap) == tagged
    assert NP.provider_text({'text': TEXT}) == TEXT
