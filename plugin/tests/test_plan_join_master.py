"""`vw visuals plan-join` after VW-24 (16 Nov 2026): a hand edit is the plan file differing from what the tool last wrote (never a file time);
a change of the base joins like a change of a gap file; after a proposal the join carries the changes of the files onto the server's current plan,
so nothing folded in there is dropped; every refusal says what to do next."""
import json
import os
import time

import vw
from test_design124_c6_c9 import gap, joined, write_parts
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)

DIRECTION = 'DIRECTION'
STATE = '.plan-join.json'


def join(capsys, **kw):
    return run(args(what='plan-join', base='out/plan-base.json', gaps=['out/plan-gaps/'], **kw), capsys)


def parts(ws):
    write_parts(ws, {'a.json': {'gaps': [gap('G1', 'E1'), gap('G2')]}, 'b.json': gap('G3')})


def edit(path, change):
    doc = json.loads(path.read_text(encoding='utf-8'))
    change(doc)
    path.write_text(json.dumps(doc), encoding='utf-8')


def server(monkeypatch, plan=None):
    """The server faked: no plan until one is proposed; a proposal gets the Direction at the head of foundation.treatment (design/207)."""
    box = {'plan': plan, 'version': 0, 'down': False}

    def request(method, path, wait=None, **kw):
        if box['down']:
            return {'action': 'unreachable', 'message': 'VideoWizard server not reachable'}, 2
        if method == 'GET' and path.endswith('/visuals/plan'):
            if box['plan'] is None:
                return {'action': 'refused', 'status': 409, 'message': 'Propose a visual plan first.'}, 2
            return {'version': box['version'], 'plan_digest': 'd', 'plan': box['plan']}, 0
        if path.endswith('/visuals/propose'):
            doc = json.loads(json.dumps(kw['json']['plan']))
            text = doc['foundation'].get('treatment') or ''
            if not text.startswith(DIRECTION):
                doc['foundation']['treatment'] = (DIRECTION + '\n\n' + text).strip()
            box['plan'], box['version'] = doc, box['version'] + 1
            return {'status': 'proposed'}, 0
        if path.endswith('/visuals/check'):
            return {'status': 'valid'}, 0
        raise AssertionError(path)
    monkeypatch.setattr(vw, 'request', request)
    return box


def propose(capsys):
    code, out, err = run(args(what='propose', file='out/visual-plan.json'), capsys)
    assert code == 0
    return err


def shot(plan, gid):
    return next(g for g in plan['gaps'] if g['gap_id'] == gid)['scenes'][0]['shots'][0]


# ---------- before a proposal ----------

def test_first_join_writes_the_plan_and_the_record_of_it(harness, monkeypatch, capsys):
    ws, _ = harness
    server(monkeypatch)
    parts(ws)
    code, out, err = join(capsys)
    assert code == 0 and [g['gap_id'] for g in joined(ws)['gaps']] == ['G1', 'G2', 'G3']
    assert (ws / 'out' / STATE).is_file()


def test_a_changed_gap_file_or_a_changed_base_joins_again_with_no_file_time_involved(harness, monkeypatch, capsys):
    ws, _ = harness
    server(monkeypatch)
    parts(ws)
    assert join(capsys)[0] == 0
    later = time.time() + 50
    os.utime(ws / 'out' / 'visual-plan.json', (later, later))   # the plan file is the newest file: the old time test refused here
    edit(ws / 'out' / 'plan-gaps' / 'b.json', lambda d: d.update(intent='revised by the helper'))
    edit(ws / 'out' / 'plan-base.json', lambda d: d['elements'][0].update(clip='C0042.MP4'))
    os.utime(ws / 'out' / 'plan-base.json', (later - 100, later - 100))
    os.utime(ws / 'out' / 'plan-gaps' / 'b.json', (later - 100, later - 100))
    code, out, err = join(capsys)
    assert code == 0 and joined(ws)['gaps'][2]['intent'] == 'revised by the helper' and joined(ws)['elements'][0]['clip'] == 'C0042.MP4'


def test_a_hand_edit_is_refused_with_what_to_do_and_rebuild_says_what_it_drops(harness, monkeypatch, capsys):
    ws, _ = harness
    server(monkeypatch)
    parts(ws)
    assert join(capsys)[0] == 0
    edit(ws / 'out' / 'visual-plan.json', lambda d: d['gaps'][0].update(intent='by hand'))
    edit(ws / 'out' / 'plan-gaps' / 'b.json', lambda d: d.update(intent='revised'))   # a newer gap file does not hide the hand edit
    later = time.time() + 50
    os.utime(ws / 'out' / 'plan-gaps' / 'b.json', (later, later))
    code, out, err = join(capsys)
    assert code == 2 and joined(ws)['gaps'][0]['intent'] == 'by hand'
    for phrase in ('edited after the last join', 'by hand', 'out/plan-base.json', 'out/plan-gaps/', '--rebuild'):
        assert phrase in out['message'], phrase
    code, out, err = join(capsys, rebuild=True)
    assert code == 0 and joined(ws)['gaps'][0]['intent'] == 'i' and joined(ws)['gaps'][2]['intent'] == 'revised'
    assert 'hand edits' in err and 'dropped' in err
    assert join(capsys)[0] == 0   # the rebuilt file is the tool's own again


def test_a_plan_file_that_is_not_json_is_a_hand_edit(harness, monkeypatch, capsys):
    ws, _ = harness
    server(monkeypatch)
    parts(ws)
    assert join(capsys)[0] == 0
    (ws / 'out' / 'visual-plan.json').write_text('{"gaps": [', encoding='utf-8')
    code, out, err = join(capsys)
    assert code == 2 and '--rebuild' in out['message']
    assert join(capsys, rebuild=True)[0] == 0 and len(joined(ws)['gaps']) == 3


def test_a_run_folder_with_no_record_falls_back_to_the_file_times_the_base_among_them(harness, monkeypatch, capsys):
    ws, _ = harness
    server(monkeypatch)
    parts(ws)
    assert join(capsys)[0] == 0
    for record in (None, 'not json {'):   # joined by an older tool; or the record unreadable
        if record is None:
            (ws / 'out' / STATE).unlink()
        else:
            (ws / 'out' / STATE).write_text(record, encoding='utf-8')
        now = time.time() + (200 if record else 0)
        os.utime(ws / 'out' / 'visual-plan.json', (now + 50, now + 50))   # newer than the base and every gap file: perhaps a hand edit
        code, out, err = join(capsys)
        assert code == 2 and 'edited after the last join' in out['message'] and '--rebuild' in out['message']
        edit(ws / 'out' / 'plan-base.json', lambda d: d['elements'][0].update(clip='C7'))
        os.utime(ws / 'out' / 'plan-base.json', (now + 100, now + 100))   # the base changed after the plan was written: join
        code, out, err = join(capsys)
        assert code == 0 and joined(ws)['elements'][0]['clip'] == 'C7'


# ---------- after a proposal ----------

def proposed(ws, monkeypatch, capsys):
    """Joined and proposed; then, on the server only: a drawing spec corrected in G1's shot, a material spec on E1, the Direction placed."""
    box = server(monkeypatch)
    parts(ws)
    assert join(capsys)[0] == 0
    propose(capsys)
    shot(box['plan'], 'G1')['drawing_spec'] = {'sizes': 'corrected'}
    box['plan']['elements'][0]['material_spec'] = {'unit': '190 x 90 x 90 mm'}
    return box


def test_the_plan_file_written_by_vw_visuals_plan_is_not_a_hand_edit(harness, monkeypatch, capsys):
    ws, _ = harness
    proposed(ws, monkeypatch, capsys)
    code, out, err = run(args(what='plan'), capsys)
    assert code == 0 and joined(ws)['foundation']['treatment'].startswith(DIRECTION)
    code, out, err = join(capsys)
    assert code == 0


def test_vw24_a_base_corrected_after_the_proposal_reaches_the_plan_and_the_servers_corrections_stay(harness, monkeypatch, capsys):
    ws, _ = harness
    proposed(ws, monkeypatch, capsys)
    run(args(what='plan'), capsys)   # as on VW-24: the tool itself rewrote the plan file
    edit(ws / 'out' / 'plan-base.json', lambda d: (d['elements'][0].update(clip='C0042.MP4'), d.update(sequence_overview='clip C0042 first')))
    edit(ws / 'out' / 'plan-gaps' / 'a.json', lambda d: d['gaps'][1].update(intent='revised by the helper'))
    code, out, err = join(capsys)
    plan = joined(ws)
    assert code == 0 and "server's plan" in err
    assert plan['elements'][0]['clip'] == 'C0042.MP4' and plan['sequence_overview'] == 'clip C0042 first' and plan['gaps'][1]['intent'] == 'revised by the helper'
    assert shot(plan, 'G1')['drawing_spec'] == {'sizes': 'corrected'} and plan['elements'][0]['material_spec'] == {'unit': '190 x 90 x 90 mm'}
    assert plan['foundation']['treatment'] == DIRECTION + '\n\nt'
    edit(ws / 'out' / 'plan-base.json', lambda d: d.update(graphic_style='flat'))   # joined again before proposing: the first change is still there
    assert join(capsys)[0] == 0
    plan = joined(ws)
    assert plan['graphic_style'] == 'flat' and plan['elements'][0]['clip'] == 'C0042.MP4' and shot(plan, 'G1')['drawing_spec'] == {'sizes': 'corrected'}
    propose(capsys)
    edit(ws / 'out' / 'plan-gaps' / 'b.json', lambda d: d.update(intent='third round'))   # and after proposing: only the new change is new
    assert join(capsys)[0] == 0
    plan = joined(ws)
    assert plan['gaps'][2]['intent'] == 'third round' and plan['graphic_style'] == 'flat' and shot(plan, 'G1')['drawing_spec'] == {'sizes': 'corrected'}


def test_the_treatment_text_changed_in_the_base_keeps_the_placed_direction_at_its_head(harness, monkeypatch, capsys):
    ws, _ = harness
    proposed(ws, monkeypatch, capsys)
    edit(ws / 'out' / 'plan-base.json', lambda d: d['foundation'].update(treatment='my new text'))
    assert join(capsys)[0] == 0
    assert joined(ws)['foundation']['treatment'] == DIRECTION + '\n\nmy new text'


def test_a_part_changed_in_the_files_and_on_the_server_is_refused_by_name_with_the_way_on(harness, monkeypatch, capsys):
    ws, _ = harness
    proposed(ws, monkeypatch, capsys)
    before = (ws / 'out' / 'visual-plan.json').read_bytes()
    edit(ws / 'out' / 'plan-gaps' / 'a.json', lambda d: d['gaps'][0]['scenes'][0]['shots'][0].update(drawing_spec={'sizes': 'the helper wrote another'}))
    code, out, err = join(capsys)
    assert code == 2 and (ws / 'out' / 'visual-plan.json').read_bytes() == before
    for phrase in ('gaps/G1/scenes/SCG1/shots/SG1/drawing_spec', '`vw visuals plan`', 'out/visual-plan.json', '`vw visuals check', '`vw visuals propose'):
        assert phrase in out['message'], phrase


def test_a_hand_edit_not_proposed_is_refused_and_once_proposed_it_is_kept_by_the_next_join(harness, monkeypatch, capsys):
    ws, _ = harness
    proposed(ws, monkeypatch, capsys)
    run(args(what='plan'), capsys)
    edit(ws / 'out' / 'visual-plan.json', lambda d: shot(d, 'G2').update(drawing_spec={'sizes': 'folded by hand'}))   # the stated way for a spec correction
    code, out, err = join(capsys)
    assert code == 2 and 'by hand' in out['message'] and '`vw visuals propose' in out['message']
    propose(capsys)
    edit(ws / 'out' / 'plan-base.json', lambda d: d.update(graphic_style='flat'))
    assert join(capsys)[0] == 0
    plan = joined(ws)
    assert plan['graphic_style'] == 'flat' and shot(plan, 'G2')['drawing_spec'] == {'sizes': 'folded by hand'}


def test_rebuild_after_a_proposal_drops_the_hand_edit_and_keeps_what_the_server_holds(harness, monkeypatch, capsys):
    ws, _ = harness
    proposed(ws, monkeypatch, capsys)
    edit(ws / 'out' / 'visual-plan.json', lambda d: d.update(graphic_style='by hand'))
    code, out, err = join(capsys, rebuild=True)
    plan = joined(ws)
    assert code == 0 and 'graphic_style' not in plan and shot(plan, 'G1')['drawing_spec'] == {'sizes': 'corrected'}
    assert 'hand edits' in err and 'dropped' in err


def test_a_proposed_plan_with_no_record_of_the_join_is_refused_with_the_working_way(harness, monkeypatch, capsys):
    ws, _ = harness
    proposed(ws, monkeypatch, capsys)
    (ws / 'out' / STATE).unlink()   # VW-24 itself: joined and proposed by the older tool
    edit(ws / 'out' / 'plan-base.json', lambda d: d['elements'][0].update(clip='C0042.MP4'))
    before = (ws / 'out' / 'visual-plan.json').read_bytes()
    code, out, err = join(capsys)
    assert code == 2 and (ws / 'out' / 'visual-plan.json').read_bytes() == before
    for phrase in ('`vw visuals plan`', 'out/visual-plan.json', '`vw visuals check --file out/visual-plan.json`', '`vw visuals propose --file out/visual-plan.json`', '--rebuild'):
        assert phrase in out['message'], phrase
    code, out, err = join(capsys, rebuild=True)   # the files alone, said plainly
    plan = joined(ws)
    assert code == 0 and plan['elements'][0]['clip'] == 'C0042.MP4' and 'drawing_spec' not in shot(plan, 'G1')
    assert "only in the server's plan" in err and 'dropped' in err
    propose(capsys)
    edit(ws / 'out' / 'plan-base.json', lambda d: d.update(graphic_style='flat'))   # from here the record exists
    assert join(capsys)[0] == 0 and joined(ws)['graphic_style'] == 'flat'


def test_the_server_not_reached_stops_the_join_and_writes_nothing(harness, monkeypatch, capsys):
    ws, _ = harness
    box = server(monkeypatch)
    parts(ws)
    box['down'] = True
    code, out, err = join(capsys)
    assert code == 2 and out['action'] == 'unreachable' and not (ws / 'out' / 'visual-plan.json').exists()


def test_a_field_the_files_add_after_a_proposal_is_not_a_clash_with_the_servers_default():
    """The critic's check: the server stores a plan with its defaults for fields the files never carried (a material spec of null, an empty
    list). A field the files add after the proposal is theirs to add: it goes in, and nothing is named as changed on both sides."""
    old = {'elements': [{'id': 'E1', 'name': 'Panel'}], 'gaps': [{'gap_id': 'G1', 'scenes': [{'id': 'S1', 'shots': [{'id': 'SH1', 'title': 'a'}]}]}]}
    mine = {'elements': [{'id': 'E1', 'name': 'Panel', 'material_spec': {'laid': 'flat'}, 'signs_of_use': ['scuffed']}],
            'gaps': [{'gap_id': 'G1', 'scenes': [{'id': 'S1', 'outfit': {'P1': 'blue'}, 'shots': [{'id': 'SH1', 'title': 'a', 'camera_move': 'fixed'}]}]}]}
    theirs = {'elements': [{'id': 'E1', 'name': 'Panel', 'material_spec': None, 'signs_of_use': [], 'description': ''}],
              'gaps': [{'gap_id': 'G1', 'scenes': [{'id': 'S1', 'outfit': {}, 'shots': [{'id': 'SH1', 'title': 'a', 'camera_move': ''}]}]}]}
    clashes = []
    out = vw._merge3(old, mine, theirs, [], clashes)
    assert clashes == []
    e, scene = out['elements'][0], out['gaps'][0]['scenes'][0]
    assert e['material_spec'] == {'laid': 'flat'} and e['signs_of_use'] == ['scuffed'] and e['description'] == ''   # the server's own default for a field the files do not name stays
    assert scene['outfit'] == {'P1': 'blue'} and scene['shots'][0]['camera_move'] == 'fixed'
    clashes = []   # a part both sides really changed is still named, and so is a field the files add where the server holds a real value (a correction folded in)
    vw._merge3({'a': 1}, {'a': 2}, {'a': 3}, [], clashes)
    vw._merge3({}, {'spec': {'x': 1}}, {'spec': {'x': 2}}, [], clashes)
    assert clashes == ['a', 'spec']
