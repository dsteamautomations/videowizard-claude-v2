"""Release 3, E5 and E6 (SK, 20 Nov 2026). E5: the step 7 notes live in design/ beside design/222, and nothing names their old place.
E6: the owner's rulings on rows 237, 243, 260 and 262, and the decisions not to build (rows 298 to 301), are in the decision log."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTES = ('222-step7-build-requirements-19-nov.md', '222-step7-take-check-test-result-19-nov.md', '222-step7-what-to-show-19-nov.md')


def test_the_step7_notes_are_beside_design_222_and_nothing_names_the_old_place():
    for name in NOTES:
        assert (ROOT / 'design' / name).is_file(), name
        assert not (ROOT / 'design' / '_work' / name.replace('222-', '')).exists(), name
    tracked = subprocess.run(['git', 'ls-files', 'design/_work'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert 'step7-' not in tracked
    note = (ROOT / 'design' / '222-step7-ai-video-page.md').read_text(encoding='utf-8')
    assert '_work/step7' not in note and all(f'design/{n}' in note for n in NOTES)


def test_the_owner_rulings_and_the_decisions_not_to_build_are_logged():
    rows = {line.split('|')[1].strip(): line for line in (ROOT / 'design' / '35-decision-log.md').read_text(encoding='utf-8').splitlines() if line.startswith('| ')}
    for n in ('237', '243', '260', '262'):
        assert 'Keep all three' in rows[n], n
    assert 'no shared-parts approval card' in rows['237'] and 'not a refusal' in rows['243'] and 'not refusals' in rows['262']
    assert 'once the earlier drawing\'s still is approved' in rows['260']
    for n, words in (('298', 'left as it is today'), ('299', 'no reminder'), ('300', 'Keep fixed for now'), ('301', 'player box')):
        assert words in rows[n] and 'Not to be built' in rows[n], n
    # the merge of release 4: its row is 302; release 3's older ways (C6, C1, C2, E2) are 303 to 306
    assert 'guide-frame1' in rows['302'] and 'release 4' in rows['302']
    for n, words in (('303', 'C6'), ('304', 'C1'), ('305', 'C2'), ('306', 'E2')):
        assert words in rows[n] and 'release 3' in rows[n], n
    # the critic's points on releases 3 and 4 (commit 74f4d7a) are rows 307 to 309
    for n in ('307', '308', '309'):
        assert n in rows, n
    assert 'GUIDE_VIDEO_LOOK' in rows['310'] and 'layout B' in rows['310']   # layout B (20 Nov) is row 310
    assert "stripes on for every person in flat mode" in rows['311'] and 'Marks only where facing matters' in rows['312']   # layout B, second part (20 Nov)
    assert 'max_prompt' not in rows['313'] and 'B1 shorten' in rows['313'] and 'HTTP 400' in rows['313']   # the still's length hotfix (21 Nov)
    assert '30 %' in rows['314'] and 'released only by the script' in rows['314']   # the first-frame limits hotfix (21 Nov)
    assert 'sending key' in rows['315'] and '404' in rows['315']   # the same key for the same take (21 Nov)
    # design/223, the new take process (22 Nov): rows 316 to 333
    assert all('design/223' in rows[str(n)] for n in range(316, 334)) and '360p' in rows['316'] and 'price by size' in rows['329'] and 'Kept' in rows['332'] and 'Kept' in rows['333']
    assert 'one click' in rows['334'] and 'design/223' in rows['334']   # SK, 22 Nov: "Use take n after all" asks no second question
    assert 'defect 62' in rows['335'] and 'portable' in rows['335'] and 'already here' in rows['336']   # defect 62 (23 Nov): the download's check and its lines
    assert 'drt' in rows['337'] and 'current one' in rows['338'] and 'camera copies' in rows['339'] and 'every member' in rows['340']   # the hand-over stoppers and films for the team (23 Nov)
    assert 'Indian script' in rows['341'] and 'Hindi and Tamil script' in rows['342'] and 'Shift + click' in rows['343'] and 'Confirm: send' in rows['344']   # the voices screen set (23 Nov)
    assert all(str(n) in rows for n in range(345, 359)) and 'paragraph' in rows['345'] and 'pixels' in rows['356']   # the VW-25 set (23 Nov)
    assert all(str(n) in rows for n in range(359, 368)) and 'issue 9' in rows['359'] and 'issue 14' in rows['362'] and 'Withdrawn' in rows['367']   # the release of 25 Nov (server 0.129.0)
    assert 'A1' in rows['368'] and 'Retired' in rows['368'] and 'Kept' in rows['368']   # the layout drawing card retired (26 Nov)
    assert 'issue 13' in rows['369'] and 'issue 12' in rows['370'] and 'guess' in rows['370']   # the reference sets (26 Nov)
    assert 'issue 3b' in rows['371'] and 'short' in rows['372'] and 'N18' in rows['373']   # short shots and lists (26 Nov)
    assert '4e part 1' in rows['374'] and '4e part 2' in rows['375']   # the specs on one card (26 Nov)
    assert 'each cut short' in rows['376'] and 'Kept' in rows['376']   # three short shots of one size (26 Nov)
    assert all('issue 10' in rows[n] for n in ('377', '378', '379')) and 'issue 11' in rows['380']   # own pictures and their words (26 Nov)
    assert 'Minor corrections' in rows['381'] and 'Make again' in rows['382'] and 'Reversed' in rows['383'] and 'Kept' in rows['384']   # minor corrections as an edit (26 Nov)
    assert 'hint_again' in rows['385'] and 'cannot change the camera' in rows['385'] and '_next_after' in rows['386'] and '--keeps' in rows['387'] and 'select_gate' in rows['388'] and '_Visit' in rows['389'] and 'heading_text' in rows['390'] and '391' not in rows   # what a correction can change (27 Nov)
