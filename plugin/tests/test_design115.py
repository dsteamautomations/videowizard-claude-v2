"""design/115 on the plugin: the cross-check passes a folder whose camera copies were left out on purpose, and the Studio import takes the relinked timeline."""
from pathlib import Path

import handoff as H
import resolve_bridge as RB
from test_handoff import edit


def test_the_cross_check_skips_the_camera_copies_left_out_and_still_checks_the_rest(tmp_path):
    d, manifest = edit(tmp_path)
    cam = [f for f in manifest['files'] if f['name'].startswith('Media/Camera/')]
    assert cam, 'the fixture has a camera file'
    for f in cam:
        (d / f['name']).unlink()
    rep = H.cross_check(d, manifest)
    assert not rep['ok'] and any('missing' in p for p in rep['problems'])   # as before: a full download misses them
    rep = H.cross_check(d, manifest, skip_roles=('original',))
    assert rep['ok'] and 'camera copies left out' in rep['present'] and rep['cuts'] == manifest['cuts']
    ai = next(f for f in manifest['files'] if f['name'].startswith('Media/AI/'))
    (d / ai['name']).unlink()
    rep = H.cross_check(d, manifest, skip_roles=('original',))
    assert not rep['ok'] and any(ai['name'] in p for p in rep['problems'])   # an AI file is never optional


def test_the_studio_import_takes_the_relinked_timeline_when_one_is_given(tmp_path):
    d, manifest = edit(tmp_path)
    manifest['resolve_events'] = [{'file': 'Media/Camera/C1.MP4', 'source_in_frame': 250, 'source_out_frame': 350, 'record_in_frame': 0, 'record_out_frame': 100, 'source_fps': '25'},
                                  {'file': 'Media/AI/VS1.mp4', 'source_in_frame': 0, 'source_out_frame': 300, 'record_in_frame': 100, 'record_out_frame': 400, 'source_fps': '25'}]
    manifest['narration_pieces'] = [{'file': 'Media/Voiceover/narration.mp3', 'source_in_frame': 0, 'source_out_frame': 400, 'record_in_frame': 0}]
    H.write_timeline_for(d, manifest, base=str(d))
    relinked = d / 'Timeline' / 'VW-9-relinked.fcpxml'
    relinked.write_bytes((d / 'Timeline' / 'VW-9.fcpxml').read_bytes())

    class Adapter(RB.FakeAdapter):
        def import_timeline(self, path, name):
            self.took = Path(path)
            return super().import_timeline(path, name)
    ad = Adapter()
    rep = RB.studio_import(ad, d, manifest, 'VW-9', timeline=str(relinked))
    assert ad.took == relinked and rep['drt_verified']
    ad = Adapter()
    RB.studio_import(ad, d, manifest, 'VW-9')
    assert ad.took == d / 'Timeline' / 'VW-9.fcpxml'


def test_relink_bad_names_every_outcome_that_must_stop_the_import():
    rc = {'lines': [{'outcome': 'match', 'line': 'a'}, {'outcome': 'renamed', 'line': 'b'}, {'outcome': 'timecode', 'line': 'c: the copy has timecode 01:00:00:00, the original 00:00:00:00'},
                    {'outcome': 'missing', 'line': 'd'}, {'outcome': 'ask', 'line': 'e'}, {'outcome': 'by_hand', 'line': 'f'}]}
    assert [l['line'][:1] for l in H.relink_bad(rc)] == ['c', 'd', 'e', 'f']   # review 28 Oct: a timecode disagreement stops the import too
    assert H.relink_bad({'lines': []}) == []
