"""SK, 15 Nov 2026 (VW-23 review): scrolling the review page cut the top of the film, because the film stuck 64px from the top while the page's own
top block is taller. The film and the rows now keep clear of the top block and the footer at their measured heights."""
from pathlib import Path

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'review.html').read_text(encoding='utf-8')


def test_the_film_sticks_below_the_top_block_at_its_measured_height():
    assert '.rv .left{position:sticky;top:calc(var(--top-h) + 10px)}' in PAGE and 'top:64px' not in PAGE
    assert "setProperty('--top-h',a.querySelector('.top').offsetHeight+'px')" in PAGE and "setProperty('--foot-h',a.querySelector('.foot').offsetHeight+'px')" in PAGE
    assert 'calc(100vh - var(--top-h) - var(--foot-h) - 140px)' in PAGE   # the film never grows past the space between the two


def test_the_height_is_measured_again_whenever_it_can_change():
    for needle in ("$('line').innerHTML=line;fit();", 'draw();fit();', "addEventListener('toggle',fit,true)", "window.addEventListener('resize',fit)", 'new ResizeObserver(fit)'):
        assert needle in PAGE, needle


def test_a_row_brought_into_view_stays_clear_of_the_top_block_and_the_footer():
    assert '.rv .row,.rv .head{scroll-margin-top:calc(var(--top-h) + 10px);scroll-margin-bottom:calc(var(--foot-h) + 10px)}' in PAGE


# ---------- SK, 25 Nov 2026 (VW-25 issue 1, requirement R1): the shot card uses its full width ----------
# The saved answer and its note sat in the button column, whose width is its content's: a long note squeezed the text to two or three words a
# line. Older way retired: the answer beside the buttons.

def test_the_saved_answer_and_its_note_are_a_line_of_their_own_under_the_text_outside_the_button_column():
    assert ".rv .ans,.rv .why{grid-column:1/-1;" in PAGE and 'overflow-wrap:anywhere' in PAGE          # full width, wrapping; a link in one piece wraps too
    assert "+info+btns+under+" in PAGE and "'<div>'+ans+'</div>'" not in PAGE                             # the row: text, buttons, the line under them
    assert "btns='<div class=\"btns\">'+(CHOICES[s.type]||[]).map(" in PAGE and 'text-align:right' not in PAGE
    assert "under='<div class=\"ans\"><b>'+esc(said(s,a))+'</b>'+(a.note?' · '+esc(a.note):'')" in PAGE   # the note is escaped, as before
    assert '.rv .info{min-width:0;overflow-wrap:anywhere}' in PAGE


def test_the_button_column_holds_the_buttons_only_and_they_go_under_the_text_in_a_narrow_window():
    assert '.rv .btns{display:flex;flex-direction:column;' in PAGE
    narrow = '@media (max-width:980px){.rv .row{grid-template-columns:minmax(0,1fr)}.rv .btns{flex-direction:row;flex-wrap:wrap}}'
    assert PAGE.index('.rv .btns{display:flex;') < PAGE.index(narrow) and PAGE.index('.rv .row{background:') < PAGE.index(narrow)   # after the rules it changes, or it would not hold


def test_every_part_of_the_card_has_a_bold_label_and_the_parts_are_separated_by_a_thin_line():
    assert "const lb=t=>'<b class=\"lb\">'+t+'</b>';" in PAGE and '.rv .lb{font-weight:700;' in PAGE
    for label in ('Clip', 'Words', 'For AI', 'Has', 'Question', 'Timing'):
        assert f"lb('{label}')" in PAGE, label
    assert '.rv .part+.part{border-top:1px solid var(--line);' in PAGE and ".filter(Boolean).map(p=>'<div class=\"part\">'+p+'</div>')" in PAGE   # a part with no text: no label, no line
    for old in ("esc('Has: '+s.flags.join('; '))", "'Question: '+esc(", "'Timing: '+esc(", "'For AI: '+esc("):    # the plain labels are gone from the shot card
        assert old not in PAGE, old
    assert 'text-overflow' not in PAGE and 'line-clamp' not in PAGE                                          # nothing is cut short


# ---------- SK, 25 Nov 2026 (VW-25 issue 5, requirement R5): the page says what a Reject note does ----------

def test_the_page_says_what_a_reject_note_does_and_the_older_words_are_gone():
    assert ('Reject: not this one; an AI stretch takes its place. A note says what the picture should show there. '
            'It does not bring another clip: for that use Other clips, and Trim for a shorter cut. Trim: use it with its start or end moved. ') in PAGE
    assert 'placeholder="What should the picture show instead? (optional)"' in PAGE
    assert '(a reason is optional)' not in PAGE and 'placeholder="Why? (optional)"' not in PAGE


# ---------- SK, 25 Nov 2026 (VW-25 issue 3a, requirement R3a): a part match is labelled, plainly ----------

def test_a_part_match_is_labelled_before_the_clip_line_in_plain_words():
    assert "const fit=s.fit&&s.fit.match==='partly'?'Shows part of what the words say.'+(s.fit.missing?' Not shown: '+s.fit.missing:''):'';" in PAGE
    assert "(fit&&!swapped?'<div class=\"fit\">'+esc(fit)+'</div>':'')+(s.clip?" in PAGE                # before the clip line; a swapped shot says it with the clip now in use
    assert '.rv .fit{' in PAGE and 'class="broll">Shows part' not in PAGE                                   # not the large red badge
