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
    assert 'one click' in rows['334'] and 'design/223' in rows['334'] and '335' not in rows   # SK, 22 Nov: "Use take n after all" asks no second question
