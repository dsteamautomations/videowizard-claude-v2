"""Defect 59 (VW-24, SK, 22 Nov 2026): a plan may give a footage shot a clip of the client's library (design/147: a clip of another film of the same
client, offered to this film at the first cut). `vw visuals clip` knew only this film's own footage and answered "Unknown clip". Now the placer also
reads the library clips kept in this film's first-cut record; the placed shot carries where the clip's file is, so the recording, the assembly's
render and the editor's package read it from its source film. The store and the database are faked."""
import pytest

from app import core, files as F, visuals_stage as VS
from app.errors import Problem
from app.stage3 import assembly as AS, delivery as D
from test_batch89_pure import MEDIA, clip_session
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, saved, store_with
import test_design132_pure as T132

RECORD_RULE = __import__('inspect').getsource(core.output)   # read before any test replaces it

LIB = {'id': 'L9', 'name': 'yard.mp4', 'sha256': 'sha-L9', 'bytes': 7, 'fps': '50/1', 'duration_s': 16.8, 'width': 1920, 'height': 1080, 'rotation_deg': 0,
       'color_transfer': 'bt709', 'key': 'r0/media/yard.mp4', 'library_from': 'VW-12'}
OWN_IN_PACKAGE = {'id': 'c7', 'name': 'C0099.MP4', 'sha256': 'sha-c7', 'fps': '25/1', 'duration_s': 30.0}   # an own clip the media record no longer lists


def first_cut(store, clips=(LIB, OWN_IN_PACKAGE)):
    store.put('run-1/stage2/session.json', __import__('json').dumps({'package': {'key': 'run-1/stage2/package.json', 'clips': {c['id']: c for c in clips}}}).encode())
    return store


def refused(fn):
    with pytest.raises(Problem) as exc:
        VS.guarded(fn)
    return exc.value.message


def test_a_library_clip_of_the_first_cut_fills_a_shot_and_keeps_where_its_file_is():
    doc, sess = clip_session()
    store = first_cut(store_with(sess, doc))
    out = VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'L9', 4.0, 'Yes, place it')
    assert out == {'shot_id': 'VS1', 'kind': 'clip', 'clip_id': 'L9', 'in_s': 4.0, 'out_s': 14.0}
    a = saved(store)['assets']['VS1']
    assert a['key'] == 'r0/media/yard.mp4' and a['library_from'] == 'VW-12' and a['name'] == 'yard.mp4' and a['fps'] == '50/1' and a['quote'] == 'Yes, place it'
    assert 'outside clip L9 (16.8 s)' in refused(lambda: VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'L9', 9.0, 'yes'))   # its own length is checked: 10 s from 9 s runs past 16.8 s


def test_an_own_clip_is_placed_as_before_and_carries_no_key():
    doc, sess = clip_session()
    store = first_cut(store_with(sess, doc), clips=(LIB, {**LIB, 'id': 'c1', 'name': 'other.mp4'}))   # a library row under an own clip's id: the film's own clip wins
    VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'c1', 4.0, 'This stretch, yes.')
    a = saved(store)['assets']['VS1']
    assert a['name'] == 'C0012.MP4' and 'key' not in a and 'library_from' not in a


@pytest.mark.parametrize('clip', ['nope', 'yard.mp4', 'c7'])   # no such clip; a name is not an id; a clip of the first cut that is not a library clip
def test_a_clip_neither_this_film_nor_its_library_has_is_refused_as_before(clip):
    doc, sess = clip_session()
    assert refused(lambda: VS.fill_clip(first_cut(store_with(sess, doc)), USER, RUN, [MEDIA], 'VS1', clip, 4.0, 'yes')) == f'Unknown clip {clip}.'


def test_a_film_with_no_first_cut_record_refuses_in_plain_words():
    doc, sess = clip_session()
    assert refused(lambda: VS.fill_clip(store_with(sess, doc), USER, RUN, [MEDIA], 'VS1', 'L9', 4.0, 'yes')) == 'Unknown clip L9.'
    assert VS.library_clips(store_with(sess, doc), RUN) == {}


def test_the_recorded_shot_and_the_render_read_the_clip_from_its_source_film(monkeypatch):
    doc, sess = clip_session()
    store = first_cut(store_with(sess, doc))
    VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'L9', 4.0, 'Yes, place it')
    rec = []
    monkeypatch.setattr(VS.core, 'output', lambda conn, user, run, body: (rec.append(body) or {'id': 'o1'}))
    s2 = saved(store)
    s2['accepted'] = accepted(doc)
    VS.record_gap(FakeConn(), first_cut(store_with(s2, doc)), USER, RUN, [MEDIA], 'G2', 'record')
    f, sh = rec[0]['files'][0], rec[0]['summary']['shots'][0]
    assert f['key'] == 'r0/media/yard.mp4' and f['name'] == 'VS1-clip-yard.mp4' and f['sha256'] == 'sha-L9'
    # the review of the fix: the record asks this film for a receipt of every file held in 'storage'; a library clip's receipt is its source film's
    assert f['location'] == 'library' and f['receipt'] is True and "f.get('location') == 'storage'" in RECORD_RULE
    assert sh['source'] == 'clip' and sh['media']['clip'] == {'id': 'L9', 'name': 'yard.mp4', 'sha256': 'sha-L9', 'fps': '50/1', 'rotation_deg': 0, 'hdr': False,
                                                             'key': 'r0/media/yard.mp4', 'library_from': 'VW-12'}
    item = AS.clip_item({'shot_id': 'VS1', 'timeline_frames': 250}, sh['media'], '25', 'k')
    assert item['clip']['key'] == 'r0/media/yard.mp4' and (item['source_in_frame'], item['source_out_frame']) == (200, 700)   # the render downloads by this key; 50 frames a second
    own = AS.clip_item({'shot_id': 'VS1', 'timeline_frames': 250}, {'clip': {'id': 'c1', 'name': 'C0012.MP4', 'sha256': 's', 'fps': '25/1'}, 'in_s': 4.0, 'out_s': 14.0}, '25', 'k')
    assert 'key' not in own['clip']   # an own clip is read from this film's media folder, as before


def test_an_own_clip_is_recorded_with_this_films_receipt_as_before(monkeypatch):
    doc, sess = clip_session()
    store = first_cut(store_with(sess, doc))
    VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'c1', 4.0, 'This stretch, yes.')
    rec = []
    monkeypatch.setattr(VS.core, 'output', lambda conn, user, run, body: (rec.append(body) or {'id': 'o1'}))
    s2 = saved(store)
    s2['accepted'] = accepted(doc)
    VS.record_gap(FakeConn(), first_cut(store_with(s2, doc)), USER, RUN, [MEDIA], 'G2', 'record')
    f = rec[0]['files'][0]
    assert f['key'] == 'run-1/media/C0012.MP4' and f['location'] == 'storage' and 'key' not in rec[0]['summary']['shots'][0]['media']['clip']


def test_a_clip_this_film_holds_itself_keeps_its_own_row_in_the_package():
    own = {'id': 'L9', 'name': 'mine.mp4', 'start_timecode': '01:00:00:00'}
    clips = D.all_clips({'summary': {'clips': [{'id': 'a1', 'name': 'C1.mp4'}, own]}}, {'clips': {'L9': LIB, 'L8': {**LIB, 'id': 'L8'}}})
    assert list(clips) == ['a1', 'L9', 'L8'] and clips['L9'] == own and clips['L8']['library_from'] == 'VW-12'   # own first, in their order; the timecode stays


def test_the_tool_downloads_a_library_original_of_the_same_client_and_no_other_file_of_another_film(monkeypatch):
    """`vw delivery download --camera`: the package lists the library original by its key in its source film."""
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, sql, args):
            row = None if 'vw2_files' in sql else {'client_id': 'NARDEP' if args[0] == 'r0' else 'OTHER'} if args[0] in ('r0', 'r9') else None
            return type('R', (), {'fetchone': lambda s: row})()

    class Store:
        def exists(self, k): return k == 'r0/media/yard.mp4' or k == 'r9/media/x.mp4'
        def signed_download(self, k): return 'https://files.test/' + k
    monkeypatch.setattr(F, 'connect', lambda: Conn())
    monkeypatch.setattr(F, 'storage', lambda: Store())
    monkeypatch.setattr(F.core, 'load_run', lambda conn, user, run_id: {'id': 'r1', 'client_id': 'NARDEP'})
    monkeypatch.setattr(VS, 'fetch_key', lambda store, run, key: '')
    assert F.download('r1', 'r0/media/yard.mp4', USER).headers['location'] == 'https://files.test/r0/media/yard.mp4'
    for key in ('r9/media/x.mp4', 'r0/stage2/session.json', 'r0/media/missing.mp4', 'r1/media/none.mp4'):   # another client's; not media; no such file; this film's, not kept
        with pytest.raises(Problem) as exc:
            F.download('r1', key, USER)
        assert exc.value.status == 404, key


def test_the_editors_package_lists_the_library_original_with_its_film_and_in_the_relink_list(monkeypatch):
    """The package read the library clips from the package file, which holds none: they are in the first-cut record (its `package.clips`)."""
    saved_, puts = {}, {}
    plan = T132.PLAN
    vis = {'id': 'o-1', 'stage': 'visuals', 'unit': 'G1', 'files': [], 'summary': {'shots': [
        {'shot_id': 'G1_S1', 'source': 'clip', 'kind': 'clip', 'placement': {'start_frame': 0, 'end_frame': 100},
         'media': {'kind': 'clip', 'clip': {k: LIB[k] for k in ('id', 'name', 'sha256', 'fps', 'key', 'library_from')}, 'in_s': 7.0, 'out_s': 11.0}}]}}
    outputs = [T132.MASTER, T132.VOICE, T132.MEDIA, vis]
    by_stage = {o['stage']: o for o in outputs if o['unit'] is None}

    def missing(store, k):
        raise Problem(404, 'NOT_FOUND', 'no file')
    monkeypatch.setattr(D.S2, 'load_json', missing)
    monkeypatch.setattr(D.S2, '_output', lambda outs, stage: by_stage.get(stage))
    monkeypatch.setattr(D.S2, '_file', lambda store, o, name: (plan, None))
    monkeypatch.setattr(D.S2, 'session_of', lambda store, run: {'package': {'clips': {'L9': LIB}}})
    monkeypatch.setattr(D.S2, '_package', lambda store, s2: {'timeline': {'fps': 25, 'width': 1920, 'height': 1080}, 'sub_clips': [], 'narration': {}})
    monkeypatch.setattr(D.S2, 'save_json', lambda store, k, data: (saved_.update({k: data}) or {'key': k, 'sha256': 's' * 64, 'bytes': 1}))
    monkeypatch.setattr(D.jobs, 'record_file', lambda *a, **kw: None)
    monkeypatch.setattr(D, 'save_session', lambda store, run, session: None)

    class Store:
        def put(self, k, data, mime):
            puts[k] = data
    D.bundle(None, Store(), {}, {'id': 'r1', 'code': 'VW-13', 'client': 'c'}, outputs)
    manifest = next(v for k, v in saved_.items() if k.endswith('delivery/manifest.json'))
    original = [f for f in manifest['files'] if f['role'] == 'original']
    assert original == [{'role': 'original', 'name': 'Media/Camera/yard.mp4', 'key': 'r0/media/yard.mp4', 'sha256': 'sha-L9', 'bytes': 7, 'source_film': 'VW-12'}]
    relink = next(v for k, v in puts.items() if k.endswith('Relink-list.csv')).decode()
    assert 'yard.mp4' in relink and relink.count('\n') == 2   # the heading and the one camera file the film uses
