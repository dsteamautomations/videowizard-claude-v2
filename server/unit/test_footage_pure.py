"""design/88: the footage character is measured, not asked."""
from app import footage as F


def sub(move, stab=False):
    return {'camera_and_optics': {'movement_type': move}, 'technical_qc_and_remediation': {'stabilization_needed': stab}}


def test_a_prores_ten_bit_log_clip_mostly_handheld_is_cinema_handheld_log():
    clip = {'id': 'c1', 'name': 'A001C003.mov', 'codec': 'prores', 'pix_fmt': 'yuv422p10le', 'bit_rate': 180_000_000, 'color_transfer': 'log3g10', 'make': 'Blackmagic Design', 'model': 'Pocket 6K'}
    row = F.per_clip(clip, {'sub_clips': [sub('Handheld'), sub('Handheld'), sub('Static')], 'contrast_profile': 'Standard_Normal'})
    assert (row['camera'], row['support'], row['look']) == ('cinema', 'handheld', 'log')
    assert row['evidence']['camera'] == 'Blackmagic Design Pocket 6K' and row['evidence']['look'] == 'colour transfer log3g10' and row['evidence']['support'] == 'handheld 2, tripod 1'


def test_an_iphone_hevc_clip_on_a_tripod_with_normal_contrast_is_phone_tripod_natural():
    clip = {'id': 'c2', 'name': 'IMG_0412.MOV', 'codec': 'hevc', 'pix_fmt': 'yuv420p10le', 'bit_rate': 24_000_000, 'color_transfer': 'bt709', 'make': 'Apple', 'model': 'iPhone 15 Pro'}
    row = F.per_clip(clip, {'sub_clips': [sub('Static'), sub('Pan')], 'contrast_profile': 'Standard_Normal'})
    assert (row['camera'], row['support'], row['look']) == ('phone', 'tripod', 'natural')   # the maker tag wins over the 10-bit pixel format


def test_vw7_names_without_tags_are_read_from_the_file_name_and_a_drone_flies_on_a_gimbal():
    """SK's VW-7 media list: C0… names from a Sony, a DJI clip, 1080p h264 at 22 Mbit/s that the old rule called phone footage."""
    sony = {'id': 'a', 'name': 'C0012.MP4', 'codec': 'h264', 'pix_fmt': 'yuv420p', 'bit_rate': 22_000_000}
    dji = {'id': 'b', 'name': 'DJI_20241217163840_0071_D.MP4', 'codec': 'h264', 'pix_fmt': 'yuv420p', 'bit_rate': 22_000_000}
    assert F.camera_of(sony) == ('unknown', 'file name C0012.MP4 (Sony, mirrorless or cinema: not classified)')   # L57, SK 23 Oct: left unclassified, never the codec rule
    assert F.camera_of(dji)[0] == 'drone' and F.support_of([], 'drone') == ('gimbal', 'a drone, no analysis yet')
    assert F.camera_of({'id': 'c', 'name': 'clip.mp4', 'codec': 'h264', 'pix_fmt': 'yuv420p', 'bit_rate': 22_000_000})[0] == 'phone'   # the codec rule, last
    assert F.camera_of({'id': 'd', 'name': 'clip.mp4'}) == ('unknown', 'no maker tag, name pattern or codec on record')   # a run recorded before design/88


def test_three_clips_of_two_kinds_are_mixed_with_counts_and_two_of_three_is_mostly():
    clips = [{'id': 'a', 'name': 'C0001.MP4'}, {'id': 'b', 'name': 'C0002.MP4'}, {'id': 'c', 'name': 'DJI_0001.MP4'}]
    logs = {'a': {'sub_clips': [sub('Handheld')]}, 'b': {'sub_clips': [sub('Static')]}, 'c': {'sub_clips': [sub('Gimbal')]}}
    m = F.measure(clips, logs)
    assert m['summary']['camera'] == 'unknown' and m['summary']['camera_counts'] == {'unknown': 2, 'drone': 1}   # L57: two unread Sony clips are not a drone film
    assert m['summary']['support'] == 'mixed' and m['summary']['support_counts'] == {'handheld': 1, 'tripod': 1, 'gimbal': 1}
    assert F.line(m['summary']) == 'Your footage: camera not known, mixed support (1 handheld, 1 tripod, 1 gimbal), natural look (measured from the clips)'


def test_a_clip_with_no_analysis_yet_has_camera_and_look_from_the_probe_and_support_unknown():
    row = F.per_clip({'id': 'a', 'name': 'C0001.MP4', 'color_transfer': 'bt709'}, None)
    assert (row['camera'], row['support'], row['look']) == ('unknown', 'unknown', 'natural')
    assert F.measure([{'id': 'a', 'name': 'x.mp4'}], {})['summary']['support'] == 'unknown'


def test_flat_contrast_or_an_hlg_transfer_reads_as_log_and_graded_is_never_measured():
    assert F.look_of({'color_transfer': 'arib-std-b67'}, None)[0] == 'log'
    assert F.look_of({'color_transfer': 'bt709'}, {'contrast_profile': 'Flat_Low_Contrast'}) == ('log', 'flat, low contrast in the analysis')
    assert all(F.look_of({'color_transfer': t}, {'contrast_profile': c})[0] != 'graded' for t in ('bt709', '') for c in ('High_Contrast', 'Standard_Normal'))


def test_the_operators_correction_wins_field_by_field_and_the_measurement_is_kept():
    m = F.measure([{'id': 'a', 'name': 'C0001.MP4'}, {'id': 'b', 'name': 'DJI_0001.MP4'}], {})
    c = F.apply_correction(m, {'camera': 'cinema', 'support': 'handheld', 'quote': 'professional camera, handheld, natural', 'by': 'u1'})
    assert c['summary']['camera'] == 'cinema' and c['summary']['support'] == 'handheld' and c['summary']['look'] == m['summary']['look']
    assert all(r['camera'] == 'cinema' for r in c['per_clip'].values()) and m['per_clip']['b']['camera'] == 'drone'   # the measurement untouched
    assert c['summary']['corrected']['quote'] == 'professional camera, handheld, natural' and F.line(c['summary']).endswith('(your correction)')
    assert F.apply_correction(m, None)['summary'] == m['summary']
