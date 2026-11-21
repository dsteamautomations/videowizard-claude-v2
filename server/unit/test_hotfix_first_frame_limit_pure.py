"""Hotfix (SK, 21 Nov 2026): "the upper limit as 30% shift and 30% zoom so that this doesn't initiate any retakes".

On VW-24's first real step 7, 8 of 18 measured takes (6 of 19 shots) were set aside by "first frame matches the still" at 3 % of the width and
3 % of zoom ("starting values at 720p", never checked against real takes): they measured 0.8 to 6.7 % shift and 0 to 4.8 % zoom; the takes that
passed measured 0 to 2.4 %. Now a take is set aside only above 30 % of either. A take set aside under the old limits is released by
`guide_worker.released` (used by scripts/vw24_release_first_frame.py, on SK's words): its line passes, its block is gone, its scorecard is
rebuilt; it then waits for Claude's check like any other take. Each test failed first. Without a database."""
import copy

from PIL import Image

from app import guide_worker as W, image_check as IC

TAIL = ': the fault is before the video, in the still or the guide; look at the overlay'


def measured(monkeypatch, shift, scale):
    monkeypatch.setattr(IC, '_match', lambda *a, **k: {'shift': shift, 'scale': scale})
    im = Image.effect_noise((256, 144), 60).convert('RGB')
    return W.first_frame_line(im, im.copy())


def test_the_limits_are_thirty_per_cent():
    assert (W.FIRST_FRAME_SHIFT, W.FIRST_FRAME_ZOOM) == (0.30, 0.30)


def test_a_take_as_far_off_as_vw24s_set_aside_takes_passes_and_keeps_its_numbers(monkeypatch):
    for shift, scale in ((0.0625, 1.038), (0.0369, 1.034), (0.0315, 1.0), (0.0247, 1.048), (0.0669, 1.015), (0.0078, 1.031)):
        line = measured(monkeypatch, shift, scale)
        assert line['pass'] is True and 'before the video' not in line['seen'], (shift, scale)
        assert line['shift_pct'] == round(shift * 100, 2) and line['seen'].startswith(f'shifted {shift * 100:.1f} % of the width')
        assert W.blocked_by([line]) is None


def test_above_thirty_per_cent_of_either_the_take_is_still_set_aside(monkeypatch):
    for shift, scale in ((0.31, 1.0), (0.0, 1.31), (0.0, 0.69)):
        line = measured(monkeypatch, shift, scale)
        assert line['pass'] is False and line['seen'].endswith(TAIL), (shift, scale)
        assert W.blocked_by([line]).startswith('the first frame does not match the still (shifted ')
    assert measured(monkeypatch, 0.30, 1.30)['pass'] is True                                    # at the limit: not set aside


# ---------- a take set aside under the old limits ----------

def record(shift=6.25, zoom=3.8, extra=()):
    """A take's check record as the worker wrote it under the 3 % limits (the shape of VW-24's, 21 Nov)."""
    seen = f'shifted {shift:.1f} % of the width, zoom {zoom:.1f} %'
    lines = [{'check': 'as long as the guide', 'weight': 'must', 'pass': True, 'seen': 'the clip is 5.0 s, the guide 5.0 s'},
             {'check': 'real footage', 'weight': 'must', 'pass': True, 'seen': 'the clip differs from its guide by 31.0 % on 5 frames', 'difference': 0.31},
             {'check': 'first frame matches the still', 'weight': 'must', 'pass': False, 'seen': seen + TAIL, 'shift_pct': shift, 'zoom_pct': zoom,
              'pass_when': "the take's first frame is the still: nothing moved, nothing pushed in"},
             {'check': 'one continuous shot', 'weight': 'must', 'pass': True, 'seen': 'no jump to another view'}] + list(extra)
    rows, watch = W.scorecard(lines, None)
    return {'guide': True, 'blocked': f'the first frame does not match the still ({seen})', 'code_lines': lines, 'scorecard': rows, 'watch': watch,
            'frames': [{'at_s': 0.0, 'key': 'f0'}], 'sheet_key': 'sheet', 'pair_key': 'pair', 'lines': [], 'must_failed': [], 'model': None, 'not_read': True}


def test_a_take_set_aside_under_the_old_limits_is_released():
    rec = record()
    assert W.released(rec) is True
    line = next(l for l in rec['code_lines'] if l['check'] == 'first frame matches the still')
    assert rec['blocked'] is None and line['pass'] is True and line['seen'] == 'shifted 6.2 % of the width, zoom 3.8 %' and line['shift_pct'] == 6.25
    assert next(r for r in rec['scorecard'] if r['line'] == 'first frame')['state'] == 'Pass'
    assert rec['frames'] and rec['sheet_key'] == 'sheet'                                         # what Claude judges it from is kept
    assert W.released(rec) is False                                                              # a second time: nothing to do


def test_what_is_not_released():
    far = record(shift=31.0, zoom=0.0)
    before = copy.deepcopy(far)
    assert W.released(far) is False and far == before                                            # above the new limit: stays set aside
    unedited = record()
    unedited['code_lines'][1].update({'pass': False})
    unedited['blocked'] = 'the guide came back unedited'
    before = copy.deepcopy(unedited)
    assert W.released(unedited) is False and unedited == before                                  # set aside for another reason
    fine = record(shift=1.0, zoom=0.0)
    fine['code_lines'][2].update({'pass': True, 'seen': 'shifted 1.0 % of the width, zoom 0.0 %'})
    fine['blocked'] = None
    assert W.released(fine) is False                                                             # never set aside
    assert W.released({}) is False and W.released({'blocked': 'the first frame does not match the still (x)', 'code_lines': []}) is False


# ---------- the release script's choice of takes ----------

def test_the_script_releases_only_takes_of_a_shot_whose_one_still_is_approved():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
    import vw24_release_first_frame as R
    s = {'guides': {'A': {'stills': [{'status': 'approved'}], 'takes': [{'job_id': 'a1'}]},
                    'B': {'stills': [{'status': 'superseded'}, {'status': 'approved'}], 'takes': [{'job_id': 'b1'}, {'job_id': 'b2'}]},
                    'C': {'stills': [{'status': 'approved'}, {'status': 'failed'}], 'takes': [{'job_id': 'c1'}, {'job_id': 'c2'}]},
                    'D': {'stills': [{'status': 'approved'}], 'takes': [{'job_id': 'd1'}]}},
         'take_checks': {'a1': record(), 'b1': record(), 'b2': record(3.69, 3.4), 'c1': record(31.0, 0.0), 'c2': record(0.78, 3.1), 'd1': {'blocked': None}}}
    rows = R.plan(s)
    assert [(r[0], r[1], r[3]) for r in rows] == [('A', 'a1', True), ('B', 'b1', False), ('B', 'b2', False), ('C', 'c1', False), ('C', 'c2', True)]
    assert s['take_checks']['a1']['blocked'] is None and s['take_checks']['b1']['blocked'] and s['take_checks']['c1']['blocked']
    assert 'its still was made again since' in rows[1][2] and 'not within the limits' in rows[3][2]
    again = R.plan(s, all_shots=True)                                                          # on SK's word: the shots with a newer still too
    assert [(r[0], r[1], r[3]) for r in again] == [('B', 'b1', True), ('B', 'b2', True), ('C', 'c1', False)]
