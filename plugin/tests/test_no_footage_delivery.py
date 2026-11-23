"""SK, 23 Nov 2026 (no-footage release 1e): after the download of a package with no camera file, the tool names no originals, no camera copies
and no relink. A package with a camera file reads as before."""
import vw

CAMERA = {'files': [{'role': 'original', 'name': 'Media/Camera/c1.mp4'}, {'role': 'ai', 'name': 'Media/AI/a.mp4'}]}
NONE = {'files': [{'role': 'ai', 'name': 'Media/AI/a.mp4'}, {'role': 'narration', 'name': 'Media/Voiceover/narration.mp3'}]}


def test_a_package_with_camera_files_reads_as_before():
    how, copies = vw.download_words(CAMERA, ('original',), True, 'VW-T')
    assert '--originals "<folder>"' in how and 'The camera copies were left out' in copies
    assert vw.download_words(CAMERA, (), True, 'VW-T')[1] == ''
    assert 'relink-check' in vw.download_words({**CAMERA, 'camera_copies': 'copies'}, (), True, 'VW-T')[1]
    assert vw.download_words(CAMERA, ('original',), False, 'VW-T')[0] == vw.handoff.free_route_text('VW-T')


def test_a_package_with_no_camera_file_names_no_originals_and_no_copies():
    how, copies = vw.download_words(NONE, ('original',), True, 'VW-T')
    assert copies == '' and '`vw delivery open`' in how and 'Resolve must be running' in how
    assert not [w for w in ('camera', 'original', 'relink') if w in how.lower()]
    assert vw.download_words(NONE, ('original',), False, 'VW-T') == (vw.handoff.free_route_text('VW-T'), '')
