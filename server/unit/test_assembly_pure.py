"""design/71 P4: two consecutive take fills of one gap that share their boundary picture are joined by a six-frame dissolve, taken from
the first take's spare tail; otherwise a cut as today. No database, no files."""
from app.stage3 import assembly as A


def fill(gap, start, slot=100, avail=110, boundary=None, kind='movie'):
    return {'gap_id': gap, 'placement': {'start_frame': start, 'end_frame': start + slot}, 'slot_frames': slot, 'available_frames': avail,
            'meta': {'kind': kind, 'issues': []}, **({'boundary': boundary} if boundary else {})}


def choice(offset=0, end_policy='trim'):
    return {'offset_frames': offset, 'end_policy': end_policy, 'accept_as_is': False}


def test_a_shared_boundary_with_a_spare_tail_dissolves_and_the_rest_cut():
    fills = {'VS1': fill('G1', 0, boundary={'start_image': 'R1', 'end_image': 'R2'}),
             'VS2': fill('G1', 100, boundary={'start_image': 'R2', 'end_image': 'R3'}),
             'VS3': fill('G1', 200, boundary={'start_image': 'R9', 'end_image': 'R10'}),   # a cut: its start is not VS2's end
             'VS4': fill('G2', 0, boundary={'start_image': 'R10', 'end_image': 'R11'})}     # another gap: never joined across gaps
    choices = {sid: choice() for sid in fills}
    assert A.dissolves(fills, choices) == {'VS1': A.DISSOLVE_FRAMES, 'VS2': 0, 'VS3': 0, 'VS4': 0} and A.DISSOLVE_FRAMES == 6


def test_no_spare_tail_or_an_offset_that_eats_it_means_a_cut():
    shared = ({'start_image': 'R1', 'end_image': 'R2'}, {'start_image': 'R2', 'end_image': 'R3'})
    fills = {'VS1': fill('G1', 0, avail=100, boundary=shared[0]), 'VS2': fill('G1', 100, boundary=shared[1])}
    assert A.dissolves(fills, {sid: choice() for sid in fills}) == {'VS1': 0, 'VS2': 0}
    fills = {'VS1': fill('G1', 0, avail=110, boundary=shared[0]), 'VS2': fill('G1', 100, boundary=shared[1])}
    assert A.dissolves(fills, {'VS1': choice(offset=5), 'VS2': choice()}) == {'VS1': 0, 'VS2': 0}   # 110 - 5 - 100 = 5 frames, under six
    assert A.dissolves(fills, {'VS1': choice(offset=4), 'VS2': choice()}) == {'VS1': 6, 'VS2': 0}
    assert A.dissolves(fills, {'VS1': choice(end_policy='hold_last'), 'VS2': choice()}) == {'VS1': 0, 'VS2': 0}   # a held last frame has no tail to spend


def test_a_still_or_a_take_without_boundary_ids_never_dissolves():
    fills = {'VS1': fill('G1', 0, boundary={'start_image': 'R1', 'end_image': 'R2'}), 'ST1': fill('G1', 100, kind='still', avail=None), 'VS2': fill('G1', 200)}
    assert A.dissolves(fills, {sid: choice() for sid in fills}) == {'VS1': 0, 'ST1': 0, 'VS2': 0}
