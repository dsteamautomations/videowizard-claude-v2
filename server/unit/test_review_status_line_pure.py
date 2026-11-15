"""SK, 15 Nov 2026 (VW-23 review): under the title the reviewer reads one line, large: where the review stands and what to do. The version, the
approval and the second-look record are kept, closed, behind Details; "2 fixes" read like something to approve and is now worded as what it is."""
from pathlib import Path

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'review.html').read_text(encoding='utf-8')


def test_one_status_line_for_each_state_of_the_review():
    for needle in ('Answer each shot. Your first answer approves these options.', 'The review film is not ready yet.', 'Answers closed. The master film is built.',
                   "'All '+d.of+' answered. The assistant builds the master film next.'", "d.answered+' of '+d.of+' answered. '+(d.of-d.answered)+' left.'"):
        assert needle in PAGE, needle
    assert '.rv .st{font-size:16px;font-weight:600' in PAGE and '<div class="st">' in PAGE


def test_an_open_defect_is_said_on_its_own_line_in_red():
    assert '<div class="st err">A defect is open on this run. Nothing can be recorded until it is fixed.</div>' in PAGE


def test_the_record_is_kept_behind_details_and_closed_by_default():
    assert 'let detOpen=false' in PAGE and "(detOpen?'':' hidden')" in PAGE and "(detOpen?'Hide details':'Details')" in PAGE
    for needle in ("'<div>Version '+esc(d.version)", 'Options approved by your first answer', 'Second look (the assistant checked its own cut before showing it): ran', "' · waiting: '"):
        assert needle in PAGE, needle
    assert "Version <strong>" not in PAGE and '<details>' not in PAGE


def test_a_fix_of_the_second_look_is_not_worded_as_something_to_approve():
    assert 'Changed by the second look, nothing to approve: ' in PAGE and "' fix'+" not in PAGE
