"""design/74 L26, L28, L29, L31: the visuals page template, read as text (the route rule in test_review_page covers its paths)."""
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def test_the_page_is_six_steps_on_the_voices_frame():
    """design/78 (L45)."""
    for step in ('treatment', 'plan', 'references', 'pictures', 'takes', 'record'):
        assert f'id="s-{step}"' in HTML, step
    assert "['treatment','Treatment']" in HTML and "['record','Record']" in HTML and 'id="steps"' in HTML and 'class="v2"' in HTML and 'class="foot"' in HTML
    assert 'id="pl"' in HTML and '<video id="pl"' in HTML   # the docked player, as the voices page has for audio
    assert 'localStorage' in HTML   # the step chosen survives a refresh


def test_the_reference_round_has_its_two_passes_and_one_done_button():
    """design/79 Q2."""
    for needle in ('pass 1 of 2', 'pass 2 of 2', 'data-a="round-done"', 'data-a="round-picks"', 'Approve the frame', 'Search with these keywords', 'input.kw', 'roundOpen()'):
        assert needle in HTML, needle
    assert "'" + 'candidate' + "'" in HTML and 'style="margin:4px 6px 0"' in HTML   # the picture's own state badge


def test_the_page_has_no_cap_button_and_no_cap_action():
    assert 'Raise the cap' not in HTML and "action:'cap'" not in HTML and 'do-cap' not in HTML


def test_a_draft_after_a_record_is_shown_with_its_badge_and_the_approve_box():
    assert 'replaces the approved treatment of' in HTML and 'd.treatment_draft' in HTML


def test_the_page_polls_at_all_times_at_visuals_and_reloads_on_return():
    assert 'visibilitychange' in HTML and '60000' in HTML and '15000' in HTML


def test_an_accepted_gap_shows_the_operators_words():
    assert 'g.quote' in HTML   # design/75 (defect 20)


def test_each_gap_has_accept_and_revise_and_a_gap_under_revision_shows_its_badge():
    assert 'data-a="revise-selected"' in HTML and 'data-a="accept-selected"' in HTML and 'under revision' in HTML and 'g.revise' in HTML   # design/76 (L32); design/78: the foot's action on the ticked gaps


def test_the_element_sections_carry_the_picks_page():
    """design/73 R4b: the ten points."""
    for needle in ('data-a="search"', 'data-a="pick"', 'data-a="nothing-fits"', 'from your footage', 'avoid brand text', 'posture only', 'Use the ticked pictures', 'element_matches', 'Image '):
        assert needle in HTML, needle
    assert 'Generate' not in HTML   # nothing paid from a click


def test_the_references_step_is_a_split_view_with_the_controls_in_the_panel():
    """design/80: the grid left, the chosen picture and its controls on the right, the ticks as chips in the footer; no note under a card, no overlay."""
    for needle in ('class="split"', 'id="panel"', 'Tick as Image', 'Untick (Image', 'Previous', 'Next ›', 'id="pwords"', 'data-untick', 'tickChips', 'ArrowLeft', "ev.key==='Escape'", 'max-width:900px'):
        assert needle in HTML, needle
    assert 'lightbox' not in HTML and 'textarea class="note"' not in HTML and 'bigPicture' not in HTML
    card = HTML[HTML.index('function resultCard'):HTML.index('function elState')]
    assert 'textarea' not in card and 'data-chip' not in card and 'data-a=' not in card   # S1: the card is the thumbnail, the order number and the caption
    assert "$('pwords')" in HTML and 'Approve' in HTML[HTML.index('function panel'):HTML.index('function selectPic')]   # S6: the words sit with the button


def test_the_takes_step_says_whose_turn_it_is_and_marks_the_checked_lines():
    """design/86 K2, K3."""
    for needle in ('function shotState', 'Your turn: approve the start image', 'Your turn: approve the pair', 'Checking the picture against its list, under 30 seconds', 'about 3 minutes. You may leave the page',
                   'prompt is not written yet', 'want your decision', 'wait for the assistant', 'class="turn ', 'c.pass===false', 'a fix of the picture before it'):
        assert needle in HTML, needle


def test_the_treatment_step_tells_the_measured_footage_and_offers_the_correction():
    """design/88 F4."""
    for needle in ('function footageBlock', 'Correct this', 'data-a="footage"', 'id="ftwords"', "action:'footage'", 'wireFootage'):
        assert needle in HTML, needle


def test_the_treatment_and_plan_rows_show_when_each_sentence_is_spoken():
    """design/89 A1."""
    assert 'function timed(g)' in HTML and HTML.count('+timed(g)+') == 2


def test_a_proposed_reuse_waits_on_the_page_for_the_operators_words_and_the_treatment_shows_the_frozen_share():
    """design/89 H7, B4."""
    for needle in ('function reuseBox', 'data-a="approve-reuse"', "action:'approve-reuse'", 'Approve the reuse', 'frozen_share', 'of the film (limit'):
        assert needle in HTML, needle
    assert HTML.count('+reuseBox(s)+') == 2   # the Pictures and the Takes steps


def test_an_empty_words_box_is_marked_and_a_rejected_picture_has_its_badge_and_button():
    assert 'need-words' in HTML and "data-a=\"reject\"" in HTML and 'rejected' in HTML
