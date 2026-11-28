"""Text overlays, build step 1 (requirements version 3 of 28 Nov 2026, part C): the overlay list, the film's look, and the refusals.
SK: the assistant and the server are the enabler, not the checker. Only what cannot be made is refused; everything else is made as the operator says."""
import pytest

from app import overlays as O

FPS = 25
# three cuts: S01-1 0-100 (4 s), S02-1 100-250 (6 s), D03-1 250-400 (a drawn shot); the film is 400 frames (16 s)
CUTS = [{'name': 'S01-1', 'start_frame': 0, 'end_frame': 100}, {'name': 'S02-1', 'start_frame': 100, 'end_frame': 250},
        {'name': 'D03-1', 'start_frame': 250, 'end_frame': 400, 'drawn': True}]
WORDS = [{'start_frame': i * 10, 'end_frame': i * 10 + 8, 'text': f'w{i + 1}'} for i in range(40)]   # word n starts at frame (n - 1) * 10
FILM = {'fps': FPS, 'frames': 400, 'cuts': CUTS, 'words': WORDS, 'font': 'Inter', 'scripts': ['latin']}


def row(**k):
    return {'kind': 'callout', 'lines': ['Two weeks'], 'word': 3, **k}


def check(rows, look=None, film=FILM):
    return O.check({'look': look or {}, 'overlays': rows}, film)


def one(**k):
    out = check([row(**k)])
    assert out['problems'] == [], out['problems']
    return out['rows'][0]


def problems(rows, look=None, film=FILM):
    return check(rows, look, film)['problems']


# ---------- a good list, and the defaults ----------

def test_a_good_list_is_accepted_and_takes_the_default_look():
    r = one()
    assert r['card'] == O.CARDS['dark'] and r['motion'] == 'wipe' and r['size'] == 'medium' and r['font'] == 'Inter' and r['place'] == 'bottom left'
    assert r['lines'] == ['Two weeks'] and r['kind'] == 'callout'


def test_an_empty_list_is_accepted():
    assert check([]) == {'look': O.look_of({}, FILM), 'rows': [], 'problems': []}


def test_a_rows_own_setting_wins_over_the_films_look():
    out = check([row(), row(word=12, motion='fade', card='bare', size='large', place='top right')], look={'card': 'cream', 'motion': 'slide', 'size': 'small'})
    a, b = out['rows']
    assert (a['card'], a['motion'], a['size']) == (O.CARDS['cream'], 'slide', 'small')
    assert (b['card'], b['motion'], b['size'], b['place']) == (O.CARDS['bare'], 'fade', 'large', 'top right')


def test_a_card_of_the_operators_own_is_the_default_card_with_their_settings():
    r = one(card={'ground': '#102030', 'opacity': 80, 'corner': 'pill'})
    assert r['card'] == {**O.CARDS['dark'], 'ground': '#102030', 'opacity': 80, 'corner': 'pill'}


def test_each_kind_has_its_usual_place_and_every_named_place_and_a_shift_and_a_spot_are_taken():
    assert one(kind='title')['place'] == 'top left' and one(kind='list')['place'] == 'left'
    for p in O.PLACES:
        assert one(place=p)['place'] == p
    assert one(place='centre', shift={'x': -5, 'y': 12.5})['shift'] == {'x': -5, 'y': 12.5}
    assert one(place={'x': 62, 'y': 30})['place'] == {'x': 62, 'y': 30}


# ---------- nothing of judgment is refused ----------

def test_long_words_two_at_once_a_drawn_shot_and_the_caption_area_are_all_made_as_asked():
    rows = [row(lines=['A very long line of many many words that no guide would ever advise for one overlay on a screen']),
            row(word=3, lines=['A second one at the same moment']),
            row(word=30, lines=['On a drawn shot']),                       # word 30 starts at frame 290, inside D03-1
            row(word=12, place='bottom', lines=['Over the captions']),
            row(kind='list', lines=[f'item {i}' for i in range(12)], word=11)]
    assert problems(rows) == []


# ---------- the moment ----------

def test_from_a_spoken_word_it_comes_in_on_the_word_and_stays_long_enough_to_read():
    r = one(word=3, lines=['Two weeks'])   # frame 20; 1 s + 0.4 s a word = 1.8 s = 45 frames; ends at 65, inside S01-1
    assert (r['start_frame'], r['end_frame'], r['facts']) == (20, 65, [])
    assert one(word=3, lines=['Now'])['end_frame'] == 20 + 38   # never under 1.5 s (37.5 frames, rounded up)


def test_the_reading_time_is_not_a_frame_too_long_by_rounding():
    assert one(word=3, lines=['one two three'])['end_frame'] == 20 + 55   # 2.2 s at 25 frames a second is 55 frames


def test_it_starts_up_to_2_seconds_before_its_word_to_stay_inside_its_shot():
    r = one(word=8, lines=['Two weeks'])   # frame 70; 45 frames would end at 115, past the cut at 100: it starts at 55, 0.6 s early
    assert (r['start_frame'], r['end_frame']) == (55, 100) and r['facts'] == ['starts 0.6 s before its word']


def test_when_2_seconds_are_not_enough_it_runs_over_the_cut_and_says_so():
    r = one(word=10, lines=['one two three four five six seven eight'])   # frame 90; 4.2 s = 105 frames; S01-1 is 100 frames long
    assert (r['start_frame'], r['end_frame']) == (90, 195) and r['facts'] == ['runs over the cut into S02-1']


def test_it_never_runs_past_the_end_of_the_film():
    r = one(word=40, lines=['one two three four five'])   # frame 390 of 400, in the last shot
    assert r['end_frame'] == 400 and r['start_frame'] == 400 - 75


def test_times_given_in_seconds_are_kept_exactly_and_win_over_a_word():
    r = one(word=3, start_s=3.2, end_s=11)
    assert (r['start_frame'], r['end_frame']) == (80, 275) and r['facts'] == ['runs over the cut into S02-1', 'runs over the cut into D03-1']
    assert one(word=None, start_s=0, end_s=0.2)['end_frame'] == 5   # shorter than any reading time: made as asked


def test_a_list_shows_each_item_on_its_own_word_or_all_at_once():
    r = one(kind='list', heading='Materials', lines=['Cement', 'Steel', 'Sand'], item_words=[3, 9, 14])
    assert r['start_frame'] == 20 and r['item_frames'] == [20, 80, 130] and r['end_frame'] >= 130 + 38
    r = one(kind='list', lines=['Cement', 'Steel'], word=3, all_at_once=True)
    assert r['item_frames'] == [20, 20]


# ---------- the refusals: only what cannot be made ----------

@pytest.mark.parametrize('doc, said', [
    (None, 'the overlay list must be an object'),
    ({'overlays': {}}, '"overlays" must be a list of rows'),
    ({'overlays': [], 'look': []}, '"look" must be an object'),
    ({'overlays': ['x']}, 'row 1: a row is an object'),
    ({'overlays': [], 'looks': {}}, 'the list has a field it does not know: looks'),
])
def test_a_file_in_another_shape_is_refused(doc, said):
    assert said in O.check(doc, FILM)['problems'][0]


@pytest.mark.parametrize('change, said', [
    ({'colour': 'red'}, "row 1: a field the application does not know: colour. A row may hold: "),
    ({'kind': 'banner'}, "row 1: kind 'banner' is not one the application has. Write one of: callout, number, list, title, name"),
    ({'lines': []}, 'row 1: the words are empty. Write "lines": one or more lines of text'),
    ({'lines': ['  ']}, 'row 1: the words are empty'),
    ({'lines': 'Two weeks'}, 'row 1: "lines" is a list of lines of text'),
    ({'word': 41}, 'row 1: word 41 is not in the voiceover (it has 40 words)'),
    ({'word': 0}, 'row 1: word 0 is not in the voiceover'),
    ({'word': None}, 'row 1: no moment. Write "word": the number of the spoken word, or "start_s" and "end_s" in seconds of the film'),
    ({'shot': 'S09-1'}, "row 1: shot 'S09-1' is not a cut of the film. The cuts are: S01-1, S02-1, D03-1"),
    ({'shot': 'S02-1'}, "row 1: word 3 is spoken in S01-1, not in S02-1. Name S01-1, or leave the shot out"),
    ({'word': None, 'start_s': 15, 'end_s': 17}, 'row 1: the time 17 s is outside the film (16 s long)'),
    ({'word': None, 'start_s': 5, 'end_s': 5}, 'row 1: the end (5 s) is not after the start (5 s)'),
    ({'word': None, 'start_s': 5}, 'row 1: "start_s" and "end_s" come together'),
    ({'word': None, 'start_s': 'soon', 'end_s': 9}, 'row 1: "start_s" and "end_s" are numbers, in seconds of the film'),
    ({'font': 'Comic Sans'}, "row 1: the font 'Comic Sans' is not in the application. The fonts are: "),
    ({'card': 'glass'}, "row 1: card 'glass' is not one the application has. Write one of: dark, cream, bare, bar, or the settings of your own card"),
    ({'card': {'ground': 'navy'}}, "row 1: the card's ground 'navy' is not a colour the application can read. Write it as #rrggbb"),
    ({'card': {'opacity': 140}}, "row 1: the card's opacity is a number from 0 to 100"),
    ({'card': {'corner': 'cut'}}, "row 1: the card's corner 'cut' is not one the application has. Write one of: square, rounded, pill"),
    ({'card': {'shape': 'star'}}, "row 1: the card has a setting the application does not have: shape. A card may set: "),
    ({'motion': 'bounce'}, "row 1: motion 'bounce' is not one the application has. Write one of: wipe, fade, rise, slide, cut"),
    ({'size': 'huge'}, "row 1: size 'huge' is not one the application has. Write one of: small, medium, large"),
    ({'weight': 'thin'}, "row 1: weight 'thin' is not one the application has. Write one of: regular, bold"),
    ({'place': 'middle'}, "row 1: place 'middle' is not one the application has. Write one of: top left, top, top right, left, centre, right, bottom left, bottom, bottom right"),
    ({'place': {'x': 120, 'y': 40}}, 'row 1: the spot is outside the frame. "x" and "y" are shares of the width and the height, from 0 to 100'),
    ({'shift': {'x': 'left'}}, 'row 1: the shift is "x" and "y" in shares of the frame, from -100 to 100'),
    ({'kind': 'list', 'item_words': [3, 9]}, 'row 1: "item_words" names one spoken word for each line (1 lines, 2 words)'),
    ({'kind': 'list', 'lines': ['a', 'b'], 'item_words': [3, 99]}, 'row 1: word 99 is not in the voiceover'),
])
def test_what_cannot_be_made_is_refused_with_its_row_and_what_to_write(change, said):
    got = problems([row(**change)])
    assert len(got) == 1 and said in got[0], got


def test_every_fault_of_a_list_is_named_by_its_row():
    got = problems([row(), row(motion='bounce'), row(word=99)])
    assert [p[:6] for p in got] == ['row 2:', 'row 3:']


def test_a_fault_in_the_films_look_is_named_as_the_look():
    assert "the film's look: motion 'spin' is not one the application has" in problems([], look={'motion': 'spin'})[0]
    assert "the film's look: a field the application does not know: lines" in problems([], look={'lines': ['x']})[0]


def test_a_letter_the_font_does_not_have_is_refused_with_the_fonts_that_have_it():
    tamil = 'சுவர்'
    got = problems([row(lines=[tamil], font='Montserrat')])   # a Latin-only font
    assert len(got) == 1 and got[0].startswith("row 1: the font 'Montserrat' has no letter for ") and 'Fonts that have them: ' in got[0] and 'Noto Sans' in got[0]
    assert problems([row(lines=[tamil], font='Noto Sans')], film={**FILM, 'scripts': ['latin', 'tamil']}) == []


def test_a_sign_the_font_lacks_is_not_refused():
    assert problems([row(lines=['₹ 4 lakh', '25 %', '40 °C'])]) == []


# ---------- film shapes, languages, sending again ----------

def test_a_hindi_row_and_a_vertical_film_are_taken():
    hindi = 'दो हफ्ते'
    out = check([row(lines=[hindi])], look={'font': 'Noto Sans'}, film={**FILM, 'scripts': ['latin', 'devanagari'], 'width': 1080, 'height': 1920})
    assert out['problems'] == [] and out['rows'][0]['lines'] == [hindi]


def test_the_same_list_checked_twice_gives_the_same_rows():
    doc = {'look': {'card': 'cream'}, 'overlays': [row(), row(word=12, motion='fade')]}
    assert O.check(doc, FILM) == O.check(doc, FILM)
