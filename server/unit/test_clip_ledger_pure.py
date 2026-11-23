"""SK, 23 Nov 2026 (VW-25 options): the operator saw many clips unused and nobody could say why. The clip ledger says, for every piece of every clip
of a film, whether the proposal used it and, if not, why. Builder only: no route and no `vw` answer reads it."""
from pathlib import Path

from app.stage2 import ledger as L

SERVER = Path(__file__).resolve().parents[1]


def piece(n, clip='c1', **more):
    return {'sub_clip_id': f'{clip}:S{n}', 'clip_id': clip, 'clip_name': f'{clip}.mp4', 'eligibility': 'ELIGIBLE_AS_IS', 'fit_kinds': {}, 'process_stage': '', **more}


def package(*pieces):
    return {'sub_clips': list(pieces), 'cards': [{'clip_id': 'c1', 'descriptive_name': 'Mason ties the bars'}],
            'ruled_out': [{'sub_clip_id': p['sub_clip_id'], 'reason': p['ruled_out_reason']} for p in pieces if p.get('ruled_out_reason')],
            'project': {'process_stages': ['Cement, sand, aggregates and steel', 'Placing the tiles']}}


def by_piece(rows):
    out = {}
    for r in rows:
        out.setdefault(r['sub_clip_id'], []).append(r)
    return out


def test_every_piece_gets_a_row_with_its_result_and_reason():
    pk = package(piece(1, fit_kinds={'B1': 'chapter'}), piece(2), piece(3, eligibility='REJECT_ALL', ruled_out_reason='reject all'),
                 piece(4, process_stage='Cement, steel, sand and aggregates'), piece(5, fit_kinds={'B2': 'related'}), piece(6, fit_kinds={'B1': 'chapter'}),
                 piece(7, fit_kinds={'B1': 'chapter'}), piece(8))
    doc = {'options': [
        {'option_number': 1, 'beat_id': 'B1', 'best_unchosen': {'sub_clip_id': 'c1:S6', 'rule': 'G8: hard sun'},
         'events': [{'sub_clip_id': 'c1:S1', 'alternatives': [{'sub_clip_id': 'c1:S7'}]},
                    {'blank': True, 'considered': [{'sub_clip_id': 'c1:S2', 'why': 'too short'}, {'sub_clip_id': 'c1:S8', 'why': 'other', 'words': 'dog in frame'}]}]},
        {'option_number': 2, 'beat_id': 'B2', 'best_unchosen': {'sub_clip_id': '', 'rule': 'coverage zero'}, 'events': [{'blank': True, 'none_fit': 'nothing'}]}]}
    got = by_piece(L.rows(pk, doc))
    assert set(got) == {p['sub_clip_id'] for p in pk['sub_clips']}                      # all eight, none left out
    one = lambda n: got[f'c1:S{n}'][0]
    assert (one(1)['result'], one(1)['scene'], one(1)['clip']) == ('used', 'B1', 'Mason ties the bars')
    assert (one(7)['result'], one(7)['scene']) == ('alternative', 'B1')
    assert (one(2)['result'], one(2)['reason'], one(2)['decided_by']) == ('turned down', 'too short', 'assistant')
    assert one(8)['reason'] == 'other: dog in frame'
    assert (one(6)['result'], one(6)['reason']) == ('turned down', 'best not chosen: G8: hard sun')
    assert (one(3)['result'], one(3)['reason'], one(3)['decided_by']) == ('refused by analysis', 'reject all', 'analysis')
    assert one(4)['result'] == 'no fit' and one(4)['decided_by'] == 'server'
    assert one(4)['reason'] == ("its chapter 'Cement, steel, sand and aggregates' is not a chapter of this film; nearest: 'Cement, sand, aggregates and steel'")
    assert (one(5)['result'], one(5)['reason']) == ('never considered', 'fits B2 (related); the proposal did not name it')
    assert L.rows(package(piece(1)), doc={'options': []})[0]['reason'] == 'no chapter and no line fit'   # a piece with no chapter at all


def test_a_piece_used_twice_has_a_row_per_use_and_a_film_without_footage_has_none():
    pk = package(piece(1))
    doc = {'options': [{'option_number': n, 'beat_id': b, 'events': [{'sub_clip_id': 'c1:S1'}]} for n, b in ((1, 'B1'), (2, 'B2'))]}
    assert [(r['result'], r['scene']) for r in L.rows(pk, doc)] == [('used', 'B1'), ('used', 'B2')]
    assert L.rows({'sub_clips': []}, {'options': [{'option_number': 1, 'beat_id': 'B1', 'events': [{'blank': True}]}]}) == []


def test_the_operators_reject_and_the_servers_refusal_are_rows_too():
    pk = package(piece(1), piece(2))
    doc = {'options': [{'option_number': 1, 'beat_id': 'B1', 'events': [{'sub_clip_id': 'c1:S1'}]}]}
    got = L.rows(pk, doc, rejected={(1, 0): 'shaky'})
    assert [(r['result'], r['reason'], r['decided_by']) for r in got if r['sub_clip_id'] == 'c1:S1'] == [('used', '', 'assistant'), ('rejected by the operator', 'shaky', 'operator')]
    refused = L.refusal_rows(pk, ['OPTION #1 shot 1 (c1:S2): G8 hard sun', 'OPTION #2: R15 best_unchosen is required'])
    assert [(r['sub_clip_id'], r['result'], r['reason'], r['decided_by']) for r in refused] == [('c1:S2', 'named in a server refusal', 'OPTION #1 shot 1 (c1:S2): G8 hard sun', 'server')]


class Conn:
    def __init__(self, fail=False):
        self.fail, self.sent, self.logged = fail, [], []

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def executemany(self, sql, params):
        if self.fail:
            raise RuntimeError('relation "vw2_clip_ledger" does not exist')
        self.sent.append((sql, list(params)))


def test_writing_never_fails_the_proposal_and_a_repeat_writes_once():
    run, pk = {'id': 'r1'}, package(piece(1))
    rows = L.rows(pk, {'options': []})
    good = Conn()
    assert L.write(good, run, 3, rows) == 1
    sql, params = good.sent[0]
    assert 'on conflict (run_id, version, sub_clip_id, scene, result) do update' in sql and params[0][:3] == ('r1', 3, 'c1:S1')
    assert L.write(Conn(fail=True), run, 3, rows) == 0          # logged, not raised
    assert L.write(good, run, 3, []) == 0 and len(good.sent) == 1   # nothing to write: no statement


def test_the_table_goes_with_the_run_and_only_the_builder_reads_it():
    sql = (SERVER / 'migrations' / '015_clip_ledger.sql').read_text(encoding='utf-8')
    assert 'references vw2_runs(id) on delete cascade' in sql and 'unique (run_id, version, sub_clip_id, scene, result)' in sql
    readers = [p.name for p in (SERVER / 'app').rglob('*.py') if 'vw2_clip_ledger' in p.read_text(encoding='utf-8')]
    assert readers == ['ledger.py']                                             # no route, no page, no answer to the `vw` tool
    assert 'select ' not in (SERVER / 'app' / 'stage2' / 'ledger.py').read_text(encoding='utf-8').lower()   # the application only writes it
    stage = (SERVER / 'app' / 'stage2' / 'stage.py').read_text(encoding='utf-8')
    assert stage.count('LG.write(') == 3                                        # a refused proposal, a recorded proposal, the master with the operator's answers
