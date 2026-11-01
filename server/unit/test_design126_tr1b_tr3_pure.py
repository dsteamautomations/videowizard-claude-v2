"""design/126 TR1b (SK, 1 Nov 2026: "Yes, count drawn"): the plan's graphics run counts drawn shots; VW-12 keeps today's rule.
TR3 (SK, 31 Oct): the treatment gives the plan's two other length warnings, AI video back to back over 12 s and a still over 4 s."""
from fractions import Fraction

from app import visual_contract as VC, visuals_stage as VS
from drawn_fixture import as_drawn
from test_design103_pure import doc_
from test_design126_a_pure import entry, treat, vw12
from test_visuals_pure import GAPS, shot as pshot


def runs(d, drawn_in_run=True):
    return [w for w in VC.validate_plan(d, GAPS, Fraction(25), drawn_in_run=drawn_in_run)[1] if w['kind'] == 'graphics_run']


def tail(a):   # camera shots to the gap's end, each within a take's 10 s
    cuts = list(range(a, 1000, 200)) + [1000]
    return [pshot(f'VS{n}', x, y, 'video') for n, (x, y) in enumerate(zip(cuts, cuts[1:]), 1)]


def drawn(sid, a, b):
    return as_drawn(pshot(sid, a, b, 'diagram'))


def test_tr1b_three_drawn_shots_of_4_s_give_a_graphics_run():
    w = runs(doc_(drawn('DR1', 0, 100), drawn('DR2', 100, 200), drawn('DR3', 200, 300), *tail(300)))
    assert len(w) == 1 and '12.0 s' in w[0]['message'] and 'DR1, DR2, DR3' in w[0]['message']


def test_tr1b_a_drawn_shot_beside_a_diagram_counts_with_it():
    w = runs(doc_(pshot('DG1', 0, 125, 'diagram'), drawn('DR1', 125, 250), *tail(250)))
    assert len(w) == 1 and '10.0 s' in w[0]['message']


def test_tr1b_a_drawn_shot_between_camera_shots_gives_none():
    assert runs(doc_(pshot('VS0', 0, 100, 'video'), drawn('DR1', 100, 250), *tail(250))) == []


def test_tr1b_a_drawn_shot_asks_no_camera_reason():
    k = VC.validate_plan(doc_(drawn('DR1', 0, 100), *tail(100)), GAPS, Fraction(25))[1]
    assert not any(w['kind'] == 'camera_reason_missing' and w.get('shot_id') == 'DR1' for w in k)


def test_tr1b_vw12_keeps_todays_rule():
    d = doc_(drawn('DR1', 0, 100), drawn('DR2', 100, 200), drawn('DR3', 200, 300), *tail(300))
    assert runs(d, drawn_in_run=False) == []
    assert VS.drawn_in_run({'code': 'VW-12'}) is False and VS.drawn_in_run({'code': 'VW-13'}) is True and VS.drawn_in_run(None) is True


def test_tr3_ai_video_back_to_back_over_12_s_warns():
    w = VS.treatment_length_warnings(entry('BEAT_08-B1', [('video', 6.6), ('video', 5.04), ('video', 7.2)]))
    assert [x['kind'] for x in w] == ['ai_run'] and '18.8 s' in w[0]['message'] and 'BEAT_08-B1-1, BEAT_08-B1-2, BEAT_08-B1-3' in w[0]['message']


def test_tr3_a_graphic_or_a_still_breaks_the_ai_run():
    assert VS.treatment_length_warnings(entry('G', [('video', 7.0), ('drawn', 4.0), ('video', 7.0)])) == []
    assert VS.treatment_length_warnings(entry('G', [('video', 6.0), ('video', 6.0)])) == []   # 12 s is not over 12 s


def test_tr3_a_still_over_4_s_warns_and_4_s_does_not():
    w = VS.treatment_length_warnings(entry('BEAT_03-B2', [('still', 5.56)]))
    assert [x['kind'] for x in w] == ['still_long'] and '5.6 s' in w[0]['message']
    assert VS.treatment_length_warnings(entry('G', [('still', 4.0)])) == []


def test_tr3_vw12s_treatment_gives_the_length_warnings_with_the_four_graphics_runs():
    out = treat(vw12())[0]
    kinds = [w['kind'] for w in out['warnings']]
    assert kinds.count('graphics_run') == 4 and kinds.count('still_long') == 1 and kinds.count('ai_run') == 1   # the fixture's 88.14 s video line and its 5.56 s still
