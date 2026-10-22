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
    for needle in ('data-a="search"', 'data-a="pick"', 'data-a="nothing-fits"', 'lightbox', 'from your footage', 'avoid brand text', 'posture only', 'Use the ticked pictures', 'element_matches', 'Image '):
        assert needle in HTML, needle
    assert 'Generate' not in HTML   # nothing paid from a click


def test_an_empty_words_box_is_marked_and_a_rejected_picture_has_its_badge_and_button():
    assert 'need-words' in HTML and "data-a=\"reject\"" in HTML and 'rejected' in HTML
