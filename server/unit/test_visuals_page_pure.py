"""design/74 L26, L28, L29, L31: the visuals page template, read as text (the route rule in test_review_page covers its paths)."""
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def test_the_page_has_no_cap_button_and_no_cap_action():
    assert 'Raise the cap' not in HTML and "action:'cap'" not in HTML and 'do-cap' not in HTML


def test_a_draft_after_a_record_is_shown_with_its_badge_and_the_approve_box():
    assert 'replaces the approved treatment of' in HTML and 'd.treatment_draft' in HTML


def test_the_page_polls_at_all_times_at_visuals_and_reloads_on_return():
    assert 'visibilitychange' in HTML and '60000' in HTML and '15000' in HTML


def test_an_accepted_gap_shows_the_operators_words():
    assert 'g.quote' in HTML   # design/75 (defect 20)


def test_an_empty_words_box_is_marked_and_a_rejected_picture_has_its_badge_and_button():
    assert 'need-words' in HTML and "data-a=\"reject\"" in HTML and 'rejected' in HTML
