"""design/147 L1 (SK, 3 Nov 2026): the brand-generic library: candidates from the studied clips, the mark recorded with the operator's words (every studied
clip stored, the named ones generic), the gate before the first cut, unmark by any team member, and the older way (films from before skip it)."""
import json

import pytest

from app import brandlib as B
from app.errors import Problem

CLIENT = 'NARDEP'
RUN = {'id': 'r1', 'code': 'VW-20', 'status': 'open', 'client_id': CLIENT, 'film': {}}
OLD = {'id': 'r0', 'code': 'VW-13', 'status': 'open', 'client_id': CLIENT, 'film': None}
USER = {'id': 'u1', 'name': 'Revathi'}


def outputs(excluded=()):
    media = {'stage': 'media', 'unit': None, 'summary': {'clips': [{'id': 'a1', 'name': 'C1.mp4', 'sha256': 'a' * 64, 'duration_s': 4.0, 'fps': '25', 'width': 1920, 'height': 1080},
                                                                   {'id': 'b2', 'name': 'C2.mp4', 'sha256': 'b' * 64, 'duration_s': 6.0, 'fps': '25', 'width': 1920, 'height': 1080},
                                                                   {'id': 'c3', 'name': 'C3.mp4', 'sha256': 'c' * 64, 'duration_s': 2.0, 'fps': '25'}]}}
    an = [{'stage': 'analysis', 'unit': 'a1', 'files': [{'name': 'a1.evidence.json', 'key': 'r1/analysis/a1.evidence.json'}],
           'summary': {'descriptive_name': 'yard wide shot', 'summary_card': ['1 OVERVIEW: the yard'], 'contract_version': 'clip-log-v1', 'excluded': 'a1' in excluded}},
          {'stage': 'analysis', 'unit': 'b2', 'files': [], 'summary': {'descriptive_name': 'the MD speaking', 'summary_card': ['1 OVERVIEW: speech'], 'contract_version': 'clip-log-v1'}},
          {'stage': 'analysis', 'unit': 'c3', 'files': [], 'summary': {'excluded': True, 'note': 'bad file'}}]   # excluded before a study: no description
    return [media] + an


class Conn:
    def __init__(self):
        self.sql = []

    def execute(self, sql, args=()):
        self.sql.append((sql, args))
        return type('R', (), {'fetchone': lambda s: None, 'fetchall': lambda s: []})()


class Store:
    def get(self, k):
        return json.dumps({'log': {'clip_overview': 'The yard from the gate.', 'entities': [{'name': 'mortar pan'}, {'name': 'plinth'}]}}).encode()


def test_candidates_are_the_studied_clips_with_their_short_description():
    rows = B.candidates(None, RUN, outputs(excluded=('a1',)))
    assert [r['name'] for r in rows] == ['C1.mp4', 'C2.mp4'] and rows[0]['excluded'] is True and rows[0]['descriptive_name'] == 'yard wide shot'
    assert rows[0]['evidence_key'] == 'r1/analysis/a1.evidence.json' and rows[1]['card'] == ['1 OVERVIEW: speech']


def test_the_gate_waits_for_the_answer_on_a_new_film_and_skips_an_older_one():
    with pytest.raises(Problem) as e:
        B.need_marked(RUN)
    assert 'vw library mark' in e.value.message
    B.need_marked(OLD)
    B.need_marked({**RUN, 'film': {'library': {'asked': True, 'generic': []}}})
    assert B.asked(OLD) == {'skipped': 'a film started before the library'} and B.asked(RUN) is None


def test_mark_stores_every_studied_clip_and_records_the_answer_with_the_words(monkeypatch):
    monkeypatch.setattr(B, 'fingerprint', lambda store, run, clip, ffmpeg='ffmpeg': [1, 2, 3])
    conn = Conn()
    out = B.mark(conn, Store(), USER, RUN, outputs(), ['C1.mp4'], 'yes, the yard shot is generic')
    assert out == {'stored': 2, 'generic': ['C1.mp4'], 'skipped': None}
    inserts = [a for s, a in conn.sql if 'insert into vw2_library' in s]
    assert len(inserts) == 2 and inserts[0][3] is True and inserts[1][3] is False   # C1 generic, C2 stored but not generic
    assert inserts[0][6] == 'r1/media/C1.mp4' and inserts[0][5].obj['overview'] == 'The yard from the gate.' and inserts[0][5].obj['entities'] == ['mortar pan', 'plinth']
    rec = next(a for s, a in conn.sql if 'update vw2_runs set film' in s)
    assert rec[0].obj['generic'] == ['C1.mp4'] and rec[0].obj['quote'] == 'yes, the yard shot is generic' and rec[0].obj['by'] == 'Revathi'


def test_mark_refuses_an_unknown_name_no_words_and_an_older_film():
    with pytest.raises(Problem) as e:
        B.mark(Conn(), Store(), USER, RUN, outputs(), ['C9.mp4'], 'yes')
    assert 'C9.mp4' in e.value.message and 'C1.mp4' in e.value.message
    with pytest.raises(Problem):
        B.mark(Conn(), Store(), USER, RUN, outputs(), [], ' ')
    with pytest.raises(Problem) as e:
        B.mark(Conn(), Store(), USER, OLD, outputs(), [], 'none')
    assert 'started before' in e.value.message


def test_none_is_an_answer_and_a_run_without_a_client_stores_nothing(monkeypatch):
    monkeypatch.setattr(B, 'fingerprint', lambda *a, **k: None)
    conn = Conn()
    assert B.mark(conn, Store(), USER, RUN, outputs(), [], 'none of these')['generic'] == []
    out = B.mark(Conn(), Store(), USER, {**RUN, 'client_id': None}, outputs(), [], 'none')
    assert out['stored'] == 0 and 'no client' in out['skipped']


def test_unmark_needs_the_name_and_the_words():
    with pytest.raises(Problem):
        B.unmark(Conn(), USER, RUN, 'C1.mp4', '')
    with pytest.raises(Problem):
        B.unmark(Conn(), USER, {**RUN, 'client_id': None}, 'C1.mp4', 'wrong, it shows the MD')
    with pytest.raises(Problem) as e:
        B.unmark(Conn(), USER, RUN, 'C1.mp4', 'wrong, it shows the MD')   # the fake conn finds no row
    assert e.value.status == 404


# ---------- L2: repeats caught before the paid study ----------

class RowsConn(Conn):
    def __init__(self, rows):
        super().__init__()
        self.rows = rows

    def execute(self, sql, args=()):
        self.sql.append((sql, args))
        rows = self.rows if 'from vw2_library' in sql else []
        return type('R', (), {'fetchone': lambda s: rows[0] if rows else None, 'fetchall': lambda s: rows})()


def test_repeats_are_found_by_file_and_by_look_and_never_for_an_older_film(monkeypatch):
    lib = [{'sha256': 'a' * 64, 'name': 'yard.mp4', 'films': ['VW-12'], 'generic': True, 'fingerprint': [0b1111]}]
    monkeypatch.setattr(B, 'fingerprint', lambda store, run, clip, ffmpeg='ffmpeg': [0b1110] if clip['name'] == 'C2.mp4' else [0xFFFF0000FFFF0000])   # C3 is far from every library frame
    clips = [{'id': 'a1', 'name': 'C1.mp4', 'sha256': 'a' * 64}, {'id': 'b2', 'name': 'C2.mp4', 'sha256': 'b' * 64}, {'id': 'c3', 'name': 'C3.mp4', 'sha256': 'c' * 64}]
    found = B.repeats(RowsConn(lib), None, RUN, clips)
    assert [(f['name'], f['kind']) for f in found] == [('C1.mp4', 'the same file'), ('C2.mp4', 'looks the same')]
    assert B.repeats(RowsConn(lib), None, OLD, clips) == [] and B.repeats(RowsConn(lib), None, {**RUN, 'client_id': None}, clips) == []


def test_the_operator_decides_once_keep_or_skip():
    found = [{'clip_id': 'a1', 'name': 'C1.mp4', 'library_name': 'yard.mp4', 'films': ['VW-12'], 'kind': 'the same file'}]
    with pytest.raises(Problem) as e:
        B.duplicates_decision(found, None)
    assert 'already holds 1' in e.value.message and '--duplicates keep|skip' in e.value.message and e.value.extra['repeats'] == found
    assert B.duplicates_decision(found, 'keep') == [] and B.duplicates_decision(found, 'skip') == ['a1'] and B.duplicates_decision([], None) == []


# ---------- L3: library clips readable from their source film ----------

def test_a_library_clip_reads_from_its_source_film_and_the_package_lists_it():
    from app.stage2 import stage as S
    from app.stage3 import delivery as D
    assert S.clip_key({'id': 'r1'}, {'name': 'C1.mp4'}) == 'r1/media/C1.mp4'
    assert S.clip_key({'id': 'r1'}, {'name': 'yard.mp4', 'key': 'r0/media/yard.mp4'}) == 'r0/media/yard.mp4'
    media_o = {'summary': {'clips': [{'id': 'a1', 'name': 'C1.mp4'}]}}
    pk = {'clips': {'a1': {'id': 'a1', 'name': 'C1.mp4'}, 'L9': {'id': 'L9', 'name': 'yard.mp4', 'key': 'r0/media/yard.mp4', 'library_from': 'VW-12'}}}
    assert set(D.all_clips(media_o, pk)) == {'a1', 'L9'} and D.all_clips(media_o, {})['a1']['name'] == 'C1.mp4'


def test_the_page_serves_a_same_client_library_clip_and_refuses_another_clients():
    from app import web
    class C:
        def __init__(self, client): self.client = client
        def execute(self, sql, args): return type('R', (), {'fetchone': lambda s: {'client_id': self.client} if args[0] == 'r0' else None})()
    run = {'id': 'r1', 'client_id': 'NARDEP'}
    assert web.client_key(C('NARDEP'), run, 'r0/media/yard.mp4') is True
    assert web.client_key(C('OTHER'), run, 'r0/media/yard.mp4') is False
    assert web.client_key(C('NARDEP'), run, 'r0/stage2/session.json') is False   # media only
    assert web.client_key(C('NARDEP'), run, 'r0/media/../x.mp4') is False and web.client_key(C('NARDEP'), {**run, 'client_id': None}, 'r0/media/yard.mp4') is False


# ---------- L4: the library round ----------

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'tests'))
from clip_log_fixture import synthetic_log   # noqa: E402

TL = {'width': 1920, 'height': 1080, 'fps': 25}
POLICY = {'allow_speaker_audio': False, 'show_speaker_video': False}


class LibStore:
    def __init__(self):
        self.files = {'pk': json.dumps({'sub_clips': [{'sub_clip_id': 'a1:S', 'clip_id': 'a1'}], 'cards': []}).encode(),
                      'r0/media/yard.mp4': b'x', 'r0/analysis/b.evidence.json': json.dumps({'log': synthetic_log('YARD', 'yard.mp4', 25.0, 50)}).encode(),
                      'r0/analysis/g.evidence.json': json.dumps({'log': synthetic_log('GONE', 'gone.mp4', 25.0, 50)}).encode()}

    def exists(self, k):
        return k in self.files

    def get(self, k):
        return self.files[k]


def lib_rows():
    base = {'films': ['VW-12'], 'generic': True, 'contract': 'clip-log-v1', 'clip': {'duration_s': 2.0, 'width': 1920, 'height': 1080, 'fps': '25/1'},
            'description': {'descriptive_name': 'the yard', 'overview': 'The yard from the gate.', 'entities': ['plinth'], 'card': ['1 OVERVIEW: yard']}, 'missing': False}
    return [{**base, 'id': 1, 'sha256': 'b' * 64, 'name': 'yard.mp4', 'media_key': 'r0/media/yard.mp4', 'evidence_key': 'r0/analysis/b.evidence.json'},
            {**base, 'id': 2, 'sha256': 'a' * 64, 'name': 'C1.mp4', 'media_key': 'r0/media/C1.mp4', 'evidence_key': 'r0/analysis/a.evidence.json'},   # this batch's own file
            {**base, 'id': 3, 'sha256': 'g' * 64, 'name': 'gone.mp4', 'media_key': 'r0/media/gone.mp4', 'evidence_key': 'r0/analysis/g.evidence.json'}]   # media deleted


def session_for():
    return {'package': {'key': 'pk', 'clips': {'a1': {'id': 'a1', 'name': 'C1.mp4', 'sha256': 'a' * 64}}, 'policy': POLICY, 'timeline': TL}}


def test_the_library_round_offers_the_clients_generic_clips_this_film_can_use():
    conn, store, session = RowsConn(lib_rows()), LibStore(), session_for()
    saved = {}
    out = B.library_round(conn, store, RUN, [], session, lambda pk: saved.update(pk))
    names = {c['clip_name'] for c in out['candidates']}
    assert names == {'yard.mp4'} and out['candidates'][0]['library_from'] == 'VW-12' and out['candidates'][0]['overview'] == 'The yard from the gate.'
    assert out['candidates'][0]['eligibility'].startswith('ELIGIBLE') and out['note'] == ''
    lib_rows_in_pk = [r for r in saved['sub_clips'] if r.get('library')]
    assert lib_rows_in_pk and all(r['library_from'] == 'VW-12' and r['primary_fits'] == [] for r in lib_rows_in_pk) and saved['sub_clips'][0]['sub_clip_id'] == 'a1:S'
    clip = session['package']['clips']['b' * 16]
    assert clip['key'] == 'r0/media/yard.mp4' and clip['library_from'] == 'VW-12'
    assert any('missing=true' in s for s, a in conn.sql)   # gone.mp4's media is gone: marked, never proposed


def test_a_rejected_proposal_is_not_offered_again_and_older_films_have_no_round():
    conn, store, session = RowsConn(lib_rows()), LibStore(), session_for()
    first = B.library_round(conn, store, RUN, [], session, lambda pk: None)['candidates']
    session['library_rejected'] = [first[0]['sub_clip_id']]
    again = B.library_round(RowsConn(lib_rows()), LibStore(), RUN, [], session, lambda pk: None)
    assert first[0]['sub_clip_id'] not in {c['sub_clip_id'] for c in again['candidates']} and again['rejected_before'] == [first[0]['sub_clip_id']]
    assert B.library_round(conn, store, OLD, [], session_for(), lambda pk: None) == {'candidates': [], 'note': 'a film started before the library: no library round'}
    assert 'no client' in B.library_round(conn, store, {**RUN, 'client_id': None}, [], session_for(), lambda pk: None)['note']


def test_the_check_takes_match_library_only_on_a_library_row_and_the_note_kind_exists():
    from app.stage2 import slides as SL, validator as V
    assert 'library' in SL.NOTE_KINDS
    row = {'eligibility': 'ELIGIBLE', 'client_safe': True, 'risk_flags': [], 'in_frame': 0, 'out_frame': 500, 'source_fps': '25', 'min_hold_s': 1.0, 'action_peak': None, 'library': True}
    ev = {'source_in_frame': 0, 'source_out_frame': 100, 'match': 'library', 'evidence': 'the yard, as the words say', 'crop': 'full'}
    refusals = []
    V._piece('T', ev, row, {}, refusals)
    assert refusals == []
    V._piece('T', ev, {**row, 'library': False}, {}, refusals)
    assert refusals and 'not this batch' in refusals[0]


def test_slides_name_the_source_film_and_a_rejected_library_shot_is_remembered():
    from app.stage2 import slides as SL, stage as S
    from test_design127_review_pure import FakeConn, RUN as R127, USER as U127, film, saved, session_store
    doc, pk = film()
    pk['sub_clips'].append({'sub_clip_id': 'L1:S', 'clip_id': 'L1', 'clip_name': 'yard.mp4', 'in_frame': 0, 'out_frame': 200, 'source_fps': '25', 'min_hold_s': 1.0,
                            'action_peak': None, 'sfx_cues': [], 'library': True, 'library_from': 'VW-12'})
    doc['options'][2]['events'] = [{'sub_clip_id': 'L1:S', 'source_in_frame': 0, 'source_out_frame': 100, 'timeline_frames': 100, 'match': 'library', 'evidence': 'x',
                                    'note': {'kind': 'library', 'question': 'the yard fits the words'}}]
    sl = SL.slides(doc, pk, 25)
    shot = next(s for s in sl if s['type'] == 'shot' and s.get('library'))
    assert shot['library'] == 'VW-12' and shot['sub_clip_id'] == 'L1:S'
    store = session_store()
    sess = saved(store)
    sess['versions'][0]['slides'] = sl
    store.files['run-1/stage2/session.json'] = json.dumps(sess).encode('utf-8')
    store.files['run-1/stage2/options-v1.json'] = json.dumps({'document': doc, 'package_digest': 'pk1'}).encode('utf-8')
    store.files['p'] = json.dumps(pk).encode('utf-8')
    S.decide(FakeConn({}), store, U127, R127, shot['no'], 'REJECT', '', None)
    assert saved(store)['library_rejected'] == ['L1:S']
