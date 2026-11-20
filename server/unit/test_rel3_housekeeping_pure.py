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
    assert '302' not in rows
