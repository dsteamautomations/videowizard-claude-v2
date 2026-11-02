"""design/132: the editor's package first, then the assembly, enforced. The gate before `prepare` and `build` (no package, an out-of-date one, one
made before this release), the inputs the early package saves, the early package made with no assembly session yet, the full bundle after the
assembly record unchanged, the next step after the last gap is recorded, and the procedure's new order."""
import json
from pathlib import Path

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from app.stage3 import assembly as A, delivery as D

ROOT = Path(__file__).resolve().parents[2]
PLAN = {'duration_frames': 100, 'events': [{'kind': 'gap', 'beat_id': 'B1', 'gap_id': 'G1', 'timeline_in_frame': 0, 'timeline_out_frame': 100, 'timeline_frames': 100}],
        'gaps': [{'shot_id': 'G1', 'start_frame': 0, 'end_frame': 100}]}
MASTER = {'stage': 'master', 'unit': None, 'summary': {'version': 2, 'plan_digest': 'm2'}, 'files': [{'name': 'master-v2.json', 'key': 'k/m', 'sha256': 'm' * 64, 'bytes': 9}]}
VOICE = {'stage': 'voice', 'unit': None, 'summary': {}, 'files': [{'name': 'narration.mp3', 'key': 'k/n', 'sha256': 'n' * 64, 'bytes': 5}]}
MEDIA = {'stage': 'media', 'unit': None, 'summary': {'clips': []}, 'files': []}


def vis(gap, oid):
    return {'id': oid, 'stage': 'visuals', 'unit': gap, 'files': [], 'summary': {'shots': []}}


OUTPUTS = [MASTER, VOICE, MEDIA, vis('G1', 'o-1'), vis('G2', 'o-2')]


def refused(fn):
    with pytest.raises(Problem) as exc:
        fn()
    assert exc.value.status == 409
    return exc.value.message


def test_the_inputs_name_the_master_and_each_gaps_recorded_output():
    assert A.early_inputs(OUTPUTS) == {'master_digest': 'm2', 'gaps': {'G1': 'o-1', 'G2': 'o-2'}}


def test_no_package_refuses_the_assembly_and_names_the_bundle():
    msg = refused(lambda: A.package_first({'bundle': None}, OUTPUTS))
    assert "editor's package comes first" in msg and '`vw delivery bundle`' in msg


def test_a_matching_early_package_lets_the_assembly_through():
    A.package_first({'bundle': {'early': True, 'inputs': A.early_inputs(OUTPUTS)}}, OUTPUTS)


def test_a_gap_recorded_again_after_the_package_is_named():
    was = A.early_inputs(OUTPUTS)
    now = [MASTER, VOICE, MEDIA, vis('G1', 'o-1'), vis('G2', 'o-9')]
    msg = refused(lambda: A.package_first({'bundle': {'early': True, 'inputs': was}}, now))
    assert 'G2' in msg and 'G1' not in msg and '`vw delivery bundle`' in msg


def test_a_new_master_plan_makes_the_package_out_of_date():
    was = A.early_inputs(OUTPUTS)
    now = [{**MASTER, 'summary': {'version': 3, 'plan_digest': 'm3'}}] + OUTPUTS[1:]
    assert 'master plan' in refused(lambda: A.package_first({'bundle': {'early': True, 'inputs': was}}, now))


def test_a_package_made_before_this_release_is_out_of_date():
    assert '`vw delivery bundle`' in refused(lambda: A.package_first({'bundle': {'early': True, 'files': 3}}, OUTPUTS))


def test_the_full_bundle_after_the_assembly_is_not_an_early_package():
    msg = refused(lambda: A.package_first({'bundle': {'early': False, 'film_sha256': 'f'}}, OUTPUTS))   # an assembly sent back: the package again first
    assert '`vw delivery bundle`' in msg


def test_prepare_and_build_call_the_gate():
    import inspect
    for fn in (A.prepare, A.build):
        assert 'package_first(' in inspect.getsource(fn), fn.__name__


@pytest.fixture
def fake(monkeypatch):
    """The early package with storage replaced: no stage3 session exists yet (no assembly prepared)."""
    saved = {}

    def load_json(store, k):
        raise Problem(404, 'NOT_FOUND', 'no file')
    by_stage = {o['stage']: o for o in OUTPUTS if o['unit'] is None}
    monkeypatch.setattr(D.S2, 'load_json', load_json)
    monkeypatch.setattr(D.S2, '_output', lambda outputs, stage: by_stage.get(stage))
    monkeypatch.setattr(D.S2, '_file', lambda store, o, name: (PLAN, None))
    monkeypatch.setattr(D.S2, 'session_of', lambda store, run: {})
    monkeypatch.setattr(D.S2, '_package', lambda store, s2: {'timeline': {'fps': 25, 'width': 1920, 'height': 1080}, 'sub_clips': [], 'narration': {}})
    monkeypatch.setattr(D.S2, 'save_json', lambda store, k, data: {'key': k, 'sha256': 's' * 64, 'bytes': 1})
    monkeypatch.setattr(D.jobs, 'record_file', lambda *a, **kw: None)
    monkeypatch.setattr(D, 'save_session', lambda store, run, session: saved.update(session))

    class Store:
        def put(self, k, data, mime):
            pass
    return Store(), saved


def test_the_early_package_is_made_with_no_assembly_session_and_saves_its_inputs(fake):
    store, saved = fake
    outputs = [o for o in OUTPUTS if o['unit'] != 'G2']
    out = D.bundle(None, store, {}, {'id': 'r1', 'code': 'VW-13', 'client': 'c'}, outputs)
    assert out['early'] is True
    assert saved['bundle']['early'] is True and saved['bundle']['inputs'] == A.early_inputs(outputs)
    A.package_first(saved, outputs)   # the assembly may start now


def test_the_last_recorded_gap_points_to_the_package():
    plan = {'gaps': [{'gap_id': 'G1'}, {'gap_id': 'G2'}]}
    assert '`vw delivery bundle`' in VS.record_next(plan, {'G1': 'o', 'G2': 'o'}, {})
    assert VS.record_next(plan, {'G1': 'o'}, {}) == '`vw next`'
    assert VS.record_next(plan, {'G1': 'o'}, {'G2': 'not accepted'}).startswith('finish the skipped gaps')


def test_the_procedure_puts_the_package_before_the_assembly():
    d = json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    st = {s['name']: s for s in d['stages']}
    asm, dl = st['assembly']['steps'], st['delivery']['steps']
    assert '`vw delivery bundle`' in asm[0] and "editor's package" in asm[0] and '`vw assembly prepare`' in asm[1]
    assert 'again' in dl[0] and 'approved film' in dl[0]
