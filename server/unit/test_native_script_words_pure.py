"""SK, 23 Nov 2026 (voices screen set). A word the voice says wrongly is written in an Indian script, Hindi first and Tamil second; the English
respelling suggestions and the Google link are retired. A name of several words is picked with a click and a Shift + click. A paid two-click button
keeps its place under the pointer, turns red and says what it waits for."""
from pathlib import Path

import pytest

from app import spelling_hints as H
from app import voices
from app.errors import Problem

T = Path(__file__).resolve().parents[1] / 'app' / 'templates'
WORDS = (T / 'voice_words.html').read_text(encoding='utf-8')
VOICES = (T / 'voices2.html').read_text(encoding='utf-8')


def test_the_request_asks_for_hindi_then_tamil_by_sound():
    ask = H.build('Vivekananda', 'He met Vivekananda there.')['contents'][0]['parts'][0]['text']
    assert ask.index('Hindi') < ask.index('Tamil')
    for needle in ('"Vivekananda"', 'He met Vivekananda there.', 'Devanagari', 'sound', 'not its meaning', 'spoken today', 'letter by letter'):
        assert needle in ask, needle
    assert 'hyphens' not in ask and 'stressed' not in ask   # the English respelling is retired


def test_only_the_named_script_is_kept_and_labelled_hindi_first():
    out = H.clean('RBI', {'tamil': ['ஆர் பி ஐ', 'RBI', 'आर'], 'hindi': ['आर बी आई', 'आरबीआई', 'आर बी आई', 'ar-bee-EYE', 'ஆர்', '', None, 'तीसरा']})
    assert out == [{'label': 'Hindi script', 'text': 'आर बी आई'}, {'label': 'Hindi script', 'text': 'आरबीआई'}, {'label': 'Tamil script', 'text': 'ஆர் பி ஐ'}]


def test_spaces_are_tidied_and_a_long_or_empty_answer_is_dropped():
    assert H.clean('x', {'hindi': ['  विवेकानंद   केंद्र '], 'tamil': ['வி' * 61]}) == [{'label': 'Hindi script', 'text': 'विवेकानंद केंद्र'}]
    assert H.clean('x', {}) == [] and H.clean('x', None) == [] and H.clean('x', {'hindi': 'विवेक'}) == []


def test_no_key_is_one_plain_line(monkeypatch):
    monkeypatch.setattr(H.keys, 'pool', lambda *a, **k: [])
    with pytest.raises(Problem) as e:
        H.suggest('Vivekananda', 'He met Vivekananda there.')
    assert 'Type or paste your own spelling' in str(e.value.message) and 'look the word up' not in str(e.value.message)


def test_a_provider_answer_becomes_labelled_spellings(monkeypatch):
    monkeypatch.setattr(H.keys, 'pool', lambda *a, **k: ['k'])
    monkeypatch.setattr(H.keys, 'gemini', lambda *a, **k: ({'body': {'hindi': ['विवेकानंद'], 'tamil': ['விவேகானந்தா']}}, None))
    assert H.suggest('Vivekananda', 's', transport_factory=object()) == [{'label': 'Hindi script', 'text': 'विवेकानंद'}, {'label': 'Tamil script', 'text': 'விவேகானந்தா'}]


def test_a_phrase_and_a_native_spelling_pass_the_word_check():
    text = 'They walked to the Vivekananda Kendra, then home.'
    assert voices.check_word(text, 'Vivekananda  Kendra', ' विवेकानंद केंद्र ') == ('Vivekananda Kendra', 'विवेकानंद केंद्र')
    rules = voices.pronunciation_rules([{'word': 'Kendra', 'say_as': 'केंद्र', 'kind': 'name'}, {'word': 'Vivekananda Kendra', 'say_as': 'विवेकानंद केंद्र', 'kind': 'name'}])
    assert rules[0]['string_to_replace'] == 'Vivekananda Kendra' and rules[0]['alias'] == 'विवेकानंद केंद्र'   # the longer one first
    with pytest.raises(Problem) as e:
        voices.check_word(text, 'Kendra', '')
    assert 'Hindi or Tamil letters' in str(e.value.message) and 'Man-ga-loor' not in str(e.value.message)


def test_the_word_page_offers_the_scripts_and_not_the_older_ways():
    for needle in ('Suggest in Hindi and Tamil script (free)', 'Write the word in Hindi or Tamil letters, as it is spoken.', 'The script and the captions keep the English spelling.',
                   'For a name of several words, click the first word, then Shift + click the last.', 'One name, one spelling, one try, one approval.'):
        assert needle in WORDS, needle
    for old in ('Look it up on Google', 'google.com', 'Suggest spellings (free)', 'syllables with hyphens', 'SHUT-er-ing', 'select them with the mouse', 'select several words', 'window.getSelection()).trim()'):
        assert old not in WORDS, old


def test_shift_click_picks_a_phrase_and_refuses_what_the_server_would_refuse():
    for needle in ('e.shiftKey', 'Pick words inside one sentence.', 'Pick words with nothing between them but spaces.', 'A name can be up to 80 characters. Pick fewer words.'):
        assert needle in WORDS, needle


def test_a_paid_two_click_button_keeps_its_place_turns_red_and_says_so():
    assert "btn.style.minWidth=btn.offsetWidth+'px'" in VOICES and "btn.textContent='Confirm: send'" in VOICES   # the armed button keeps its size and place
    assert "if(btn.closest('.foot')){c.className='lk';c.style.marginLeft='10px';$('fmsg').append(c);}else{c.className='cancel';btn.after(c);}" in VOICES   # in the bar Cancel is a link in the message line: nothing moves
    assert '.v2 button.armed,.v2 .foot .go.armed{background:var(--err)' in VOICES   # every armed button, also the bar's Narrate
    assert 'Click Confirm within 8 seconds to send. Nothing is sent yet.' in VOICES and "msg('Not sent.')" in VOICES
