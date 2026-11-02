"""design/142 R1: `vw log` adds the assistant's entry to the run's decision log, or shows the whole log in work/decision-log.md."""

import vw
from test_visuals_cli import harness  # noqa: F401


def run(argv, capsys):
    a = vw.build_parser().parse_args(argv)
    try:
        a.fn(a)
        code = 0
    except SystemExit as exc:
        code = exc.code
    out = capsys.readouterr().out
    import json
    return code, json.loads(out) if out.strip() else {}


def test_an_entry_is_sent_with_its_rule_and_about(harness, monkeypatch, capsys):
    sent = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (sent.update(path=path, **body) or {'logged': True}))
    code, out = run(['log', '--about', 'C0073', '--rule', 'no rule', 'dropped', 'for', 'the', 'eye-trace'], capsys)
    assert code == 0 and sent['path'].endswith('/log') and sent['text'] == 'dropped for the eye-trace' and sent['about'] == 'C0073' and sent['rule'] == 'no rule'


def test_an_empty_entry_is_refused(harness, capsys):
    assert run(['log'], capsys)[0] == 2


def test_show_writes_the_whole_log(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'markdown': '# Decision log: VW-9\n'})
    code, out = run(['log', '--show'], capsys)
    assert code == 0 and (vw.RUNS / 'VW-9' / 'work' / 'decision-log.md').read_text(encoding='utf-8').startswith('# Decision log')


def test_the_second_look_plans_stills_from_the_cut_and_closer_on_a_claim_or_state():
    options = [{'option_number': 1, 'beat_id': 'BEAT_01', 'steps': [{'step_id': 'S1', 'event': 2, 'claim': True}],
                'events': [{'sub_clip_id': 'c1:S1', 'source_in_frame': 100, 'source_out_frame': 250, 'alternatives': [{'sub_clip_id': 'c2:S1', 'source_in_frame': 0, 'source_out_frame': 150}]},
                           {'sub_clip_id': 'c3:S1', 'source_in_frame': 10, 'source_out_frame': 160},
                           {'sub_clip_id': 'c4:S1', 'source_in_frame': 0, 'source_out_frame': 90, 'state': True},
                           {'blank': True, 'timeline_frames': 50}]}]
    plan = vw.still_plan(options)
    assert plan == [('c1:S1', 100, 250, 1.0), ('c2:S1', 0, 150, 1.0), ('c3:S1', 10, 160, 0.5), ('c4:S1', 0, 90, 0.5)]


def test_the_join_names_the_scenes_whose_cuts_changed():
    before = [{'beat_id': 'BEAT_01', 'events': [{'sub_clip_id': 'a', 'source_in_frame': 1, 'source_out_frame': 9}]},
              {'beat_id': 'BEAT_02', 'events': [{'sub_clip_id': 'b', 'source_in_frame': 1, 'source_out_frame': 9}]}]
    after = [{'beat_id': 'BEAT_01', 'events': [{'sub_clip_id': 'a', 'source_in_frame': 3, 'source_out_frame': 9}]}, before[1]]
    assert vw.cuts_changed(before, after) == ['BEAT_01']


def test_the_scene_reviewer_knows_the_servers_rules():
    text = (vw.ROOT / 'agents' / 'vw-scene-review.md').read_text(encoding='utf-8') if hasattr(vw, 'ROOT') else open(__file__.replace('tests\test_design142.py', 'agents\vw-scene-review.md').replace('tests/test_design142.py', 'agents/vw-scene-review.md'), encoding='utf-8').read()
    for words in ('reuse, check_by_eye, poor_quality, join, other', 'whole action peak', 'camera move', '6 to 12 frames before the word', 'marker_reasons', 'considered', 'preferred_because', 'as cut'):
        assert words in text, words
