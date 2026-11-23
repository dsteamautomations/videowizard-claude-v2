"""SK, 23 Nov 2026 (VW-25 options, plan of action Phase 1.1 and 1.2). VW-25's script held its title line as a sentence: the clip study counted 43
sentences, the narration 42, and the whole film lost its line fits (0 direct fits, every clip B-roll). Now the script's sentences are paired with
the narration's by their words; a sentence without a pair loses only its own fits; a clip studied against another count loses only its own; and
prepare says so. Older way retired: the whole film packaged by paragraph because the two counts differ."""
from pathlib import Path

from app.stage2 import package as P

SERVER = Path(__file__).resolve().parents[1]
SCRIPT = ['Filler Slab Technology', 'As the demand for housing grows, costs rise.', 'A filler slab saves concrete.', 'Tiles replace it.']
SPOKEN = ['Filler Slab Technology As the demand for housing grows, costs rise.', 'A filler slab saves concrete.', 'Tiles replace it.']


def test_a_title_line_read_into_the_first_sentence_shifts_no_fit():
    assert P.pair_sentences(SCRIPT, SPOKEN) == {1: 1, 2: 1, 3: 2, 4: 3}
    assert P.pair_sentences(SPOKEN, SPOKEN) == {1: 1, 2: 2, 3: 3}                     # the same sentences: each to itself


def test_a_sentence_without_a_pair_loses_only_its_own_place():
    got = P.pair_sentences(SCRIPT[:3] + ['This line was cut before the recording.'] + SCRIPT[3:], SPOKEN)
    assert got == {1: 1, 2: 1, 3: 2, 5: 3}                                              # sentence 4 has no pair; the one after it is still found
    assert P.pair_sentences(SCRIPT, []) == {} and P.pair_sentences([], SPOKEN) == {}    # nothing to pair: nothing paired, no error
    assert P.pair_sentences(['', '   '], SPOKEN) == {}                                  # a sentence with no words has no pair


def test_a_sentence_said_twice_and_a_word_spelt_for_the_voice_are_still_paired():
    twice = ['Mix it well.', 'Pour the slab.', 'Mix it well.']
    assert P.pair_sentences(twice, twice) == {1: 1, 2: 2, 3: 3}                         # in order, not both to the first
    assert P.pair_sentences(['The Mangalore tile is light.', 'It costs less.'], ['The Mangaluru tile is light.', 'It costs less.']) == {1: 1, 2: 2}
    assert P.pair_sentences(['One long sentence said here, cut in two by voice.'], ['One long sentence said here.', 'Cut in two by voice.']) == {1: 1}   # ties go to the earlier


def window(bid, a, z, chapter='Casting'):
    return {'beat_id': bid, 'timeline_start_frame': a, 'timeline_end_frame': z, 'process_stages': [chapter]}


def row(fits, chapter=''):
    return {'primary_fits': [], 'secondary_fits': [], 'process_stage': chapter,
            'sentence_fits': [{'sentence': i, 'from_s': 0.0, 'to_s': 1.0, 'match': m, 'why': '', 'missing': ''} for i, m in fits]}


def test_a_fit_follows_its_sentence_to_the_narration_and_an_unpaired_one_is_left_out():
    windows = [window('B1', 0, 100), window('B2', 100, 200, 'Placing the tiles')]
    spoken = [{'start_frame': 0}, {'start_frame': 100}, {'start_frame': 150}]           # narration sentence 1 in B1, 2 and 3 in B2
    pair = {1: 1, 2: 1, 3: 2, 5: 3}                                                      # study sentence 4 has no pair
    a, b = P.scene_fits_by_sentence([row([(3, 'EXACT'), (4, 'EXACT'), (5, 'RELATED')]), row([(4, 'EXACT')], 'Casting')], windows, spoken, pair)
    assert [(f['sentence'], f['scene'], f['step_id']) for f in a['sentence_fits']] == [(2, 'B2', 'B2.S1'), (3, 'B2', 'B2.S2')]   # numbered as the narration numbers them
    assert a['fit_kinds'] == {'B2': 'direct'} and a['fit_unit'] == 'sentence'
    assert b['sentence_fits'] == [] and b['fit_kinds'] == {'B1': 'chapter'}             # its only line fit is lost; the chapter fit stays
    same = P.scene_fits_by_sentence([row([(2, 'EXACT')])], windows, spoken)[0]          # no pairing given: as before, number for number
    assert same['fit_kinds'] == {'B2': 'direct'}


def test_a_count_difference_no_longer_packages_the_whole_film_by_paragraph():
    by = lambda n: {'fit_unit': 'sentence', 'sentences': n}
    assert P.fit_unit([by(43), by(43)]) == ('sentence', '')
    assert P.fit_unit([by(43), {}])[0] == 'paragraph' and 'before' in P.fit_unit([by(43), {}])[1]    # kept: a film with both kinds of study
    assert P.fit_unit([{}, {}]) == ('paragraph', '')
    assert P.study_sentences(by(43), 43) == 43 and P.study_sentences(by(40), 43) == 0 and P.study_sentences({}, 43) == 0   # another count: that clip's lines are not read


def test_prepare_says_what_the_pairing_did():
    assert P.pairing_note(SPOKEN, 3, {1: 1, 2: 2, 3: 3}, [], []) == ''                   # nothing to say
    note = P.pairing_note(SCRIPT, 3, {1: 1, 2: 1, 3: 2, 4: 3}, [], [])
    assert note == 'The script has 4 sentences and the narration has 3: they were paired by their words, and every script sentence was found.'
    lost = P.pairing_note(SCRIPT + ['This line was cut.'], 3, {1: 1, 2: 1, 3: 2, 4: 3}, [{'sentence': 5}, {'sentence': 5}, {'sentence': 2}], ['C0050.MP4', 'C0058.MP4'])
    assert "No narration sentence was found for script sentence 5 ('This line was cut.'): 2 line fits are not used." in lost
    assert '2 clips were studied against another count of sentences (C0050.MP4, C0058.MP4): their line fits are not used, they fit by chapter only.' in lost
    stage = (SERVER / 'app' / 'stage2' / 'stage.py').read_text(encoding='utf-8')
    assert "'fit_note': fit_note" in stage                                              # in the answer of prepare, for the assistant
    vw = (SERVER.parent / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "out.get('fit_note')" in vw                                                  # and in the tool's first line, not only inside the JSON


def test_intake_proposes_the_documents_own_title_for_removal():
    """Phase 1.3, the source of VW-25's extra sentence: intake kept 'Filler Slab Technology' as speech. The operator still decides."""
    import json
    intake = json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'][0]
    assert intake['name'] == 'intake'
    rule = ' '.join(intake['prompt'].split('WHAT IS THE SCRIPT')[0].split())
    assert "The document's own title is not the script." in rule and 'is listed as scene_heading' in rule
    assert 'Keep it only when the document marks it as spoken' in rule
