"""design/89 batch 1: B2 movement at render, B3 clip stretches, H2-H6 no repeated pictures. The store and the database are faked; ffmpeg renders for real."""
import json
import shutil
import subprocess
from io import BytesIO

import pytest

from app import lookalike, visuals_stage as VS
from app.errors import Problem
from app.stage3 import assembly as AS
from test_visuals_stage_pure import FakeConn, FakeStore, RUN, USER, accepted, g, gap_digest, plan_doc, ref, saved, session, shot, store_with

PIL = pytest.importorskip('PIL.Image')
needs_ffmpeg = pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg not installed')


def png(colour=(200, 80, 40), size=(320, 180), box=None):
    img = PIL.new('RGB', size, colour)
    if box:
        from PIL import ImageDraw
        ImageDraw.Draw(img).rectangle(box[0], fill=box[1])
    out = BytesIO()
    img.save(out, format='PNG')
    return out.getvalue()


def frames_of(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', str(path)],
                         capture_output=True, check=True, text=True).stdout
    return int(out.strip())


# ---------- B2: movement at render ----------

@needs_ffmpeg
def test_a_still_renders_its_exact_frames_and_moves_5_percent_unless_none(tmp_path):
    from app.stage2.render import Renderer
    r = Renderer(tmp_path, {'width': 320, 'height': 180, 'fps': '25'})
    p = tmp_path / 's.png'
    from PIL import ImageDraw
    img = PIL.new('RGB', (320, 180), (240, 240, 240))
    for x in range(0, 320, 16):
        ImageDraw.Draw(img).line([(x, 0), (x, 180)], fill=(30, 90, 160), width=3)
    buf = BytesIO()
    img.save(buf, format='PNG')
    p.write_bytes(buf.getvalue())
    moving = r.still(p, 'sha-s', 50, 'push_in')
    frozen = r.still(p, 'sha-s', 50)
    assert frames_of(moving) == 50 and frames_of(frozen) == 50 and moving != frozen
    def change(path):   # mean pixel change between the first and the last frame
        from PIL import ImageChops, ImageStat
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(path), '-vf', r"select='eq(n\,0)+eq(n\,49)'", '-fps_mode', 'passthrough', str(tmp_path / f'{path.stem}-%d.png')], check=True)
        a, b = (PIL.open(tmp_path / f'{path.stem}-{k}.png').convert('L') for k in (1, 2))
        return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]
    assert change(moving) > 5 and change(frozen) < 1   # the stripes slide as the picture moves in; the frozen one does not move
    seq = r.sequence([(p, 'sha-s', 40), (p, 'sha-s', 35)], 10, 75, 'push_in')
    assert frames_of(seq) == 75


# ---------- B3: a clip stretch fills a shot ----------

def clip_session(**extra):
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   **{'repeat_rules': 'refuse', **extra})
    return doc, sess


MEDIA = {'stage': 'media', 'unit': None, 'files': [], 'summary': {'clips': [{'id': 'c1', 'name': 'C0012.MP4', 'sha256': 'sha-c1', 'bytes': 9, 'fps': '25/1', 'duration_s': 30.0},
                                                                   {'id': 'c2', 'name': 'C0013.MP4', 'sha256': 'sha-c2', 'bytes': 9, 'fps': '25/1', 'duration_s': 30.0}]}}


def master(events):
    return {'stage': 'master', 'unit': None, 'files': [{'name': 'master-v1.json', 'key': 'run-1/master-v1.json'}], 'summary': {}}, json.dumps({'events': events}).encode()


def test_a_clip_stretch_fills_a_shot_from_its_in_point_and_records_and_assembles_with_its_frames(monkeypatch):
    doc, sess = clip_session()
    store = store_with(sess, doc)
    with pytest.raises(Problem, match='never a graphic|outside clip'):
        g(lambda: VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'c1', 25.0, 'yes'))   # 10 s from 25 s runs past the 30 s clip
    out = VS.fill_clip(store, USER, RUN, [MEDIA], 'VS1', 'c1', 4.0, 'This stretch, yes.')
    assert out == {'shot_id': 'VS1', 'kind': 'clip', 'clip_id': 'c1', 'in_s': 4.0, 'out_s': 14.0}
    rec = []
    monkeypatch.setattr(VS.core, 'output', lambda conn, user, run, body: (rec.append(body) or {'id': 'o1'}))
    s2 = saved(store)
    s2['accepted'] = accepted(doc)
    store2 = store_with(s2, doc)
    VS.record_gap(FakeConn(), store2, USER, RUN, [MEDIA], 'G2', 'record')
    sh = rec[0]['summary']['shots'][0]
    assert sh['source'] == 'clip' and sh['media']['clip']['id'] == 'c1' and sh['media']['in_s'] == 4.0 and rec[0]['files'][0]['key'] == 'run-1/media/C0012.MP4'
    item = AS.clip_item({'shot_id': 'VS1', 'timeline_frames': 250}, sh['media'], '25', 'k')
    assert (item['source_in_frame'], item['source_out_frame']) == (100, 350) and item['clip']['name'] == 'C0012.MP4' and item['kind'] == 'event'


def test_stills_and_sequences_carry_the_plans_motion_at_record(monkeypatch):
    doc, sess = clip_session(references={'R1': ref('R1', 'approved')})
    doc['gaps'][0]['scenes'][0]['shots'][0]['motion'] = 'pan_left'
    sess['accepted'] = accepted(doc)
    store = store_with(sess, doc)
    VS.still_from_reference(store, USER, RUN, [], 'IM1', 'R1', 'yes')
    rec = []
    monkeypatch.setattr(VS.core, 'output', lambda conn, user, run, body: (rec.append(body) or {'id': 'o1'}))
    VS.record_gap(FakeConn(), store, USER, RUN, [], 'G1', 'record')
    assert rec[0]['summary']['shots'][0]['media'] == {'kind': 'still', 'motion': 'pan_left', 'graphic': False}


# ---------- H2-H5: no repeated pictures ----------

def frame_ref(rid, clip, at):
    return {**ref(rid, 'approved'), 'kind': 'frame', 'source': {'media_id': clip, 'requested_s': at}}


def test_a_frozen_frame_of_a_clip_that_plays_elsewhere_is_refused_even_with_approval():
    """H3: c1 plays in the first cut."""
    doc, sess = clip_session(references={'F1': frame_ref('F1', 'c1', 3.0)})
    store = store_with(sess, doc)
    m, data = master([{'kind': 'event', 'sub_clip_id': 'c1:SUB_01', 'source_in_frame': 0, 'source_out_frame': 100, 'timeline_in_frame': 0, 'timeline_out_frame': 100}])
    store.files['run-1/master-v1.json'] = data
    with pytest.raises(Problem, match='H3: clip c1 plays elsewhere'):
        g(lambda: VS.still_from_reference(store, USER, RUN, [MEDIA, m], 'IM1', 'F1', 'yes', {'reason': 'r', 'considered': 'c'}, [0, 0, 0.7, 0.7]))


def test_a_reuse_needs_the_reason_the_reimagined_shot_and_words_60_s_apart_a_different_stretch_and_a_safe_crop():
    """H2, H4 (SK): first cut c1 0-4 s at film 0-4 s; visuals VS1 at film 36-46 s."""
    near = master([{'kind': 'event', 'sub_clip_id': 'c1:SUB_01', 'source_in_frame': 0, 'source_out_frame': 100, 'timeline_in_frame': 0, 'timeline_out_frame': 100}])
    far = master([{'kind': 'event', 'sub_clip_id': 'c1:SUB_01', 'source_in_frame': 0, 'source_out_frame': 100, 'timeline_in_frame': 3000, 'timeline_out_frame': 3100}])
    for safe, (m, data), expect in ((1.35, far, 'can be enlarged only 1.35'), (2.0, near, 'is 32 s from c1:SUB_01')):
        doc, sess = clip_session(clip_safe_zoom={'c1': safe})
        store = store_with(sess, doc)
        store.files['run-1/master-v1.json'] = data
        with pytest.raises(Problem) as exc:
            g(lambda: VS.fill_clip(store, USER, RUN, [MEDIA, m], 'VS1', 'c1', 10.0, 'yes'))
        assert 'H2: clip c1 is already on screen' in exc.value.message and 'reimagined shot' in exc.value.message
        with pytest.raises(Problem, match=expect):
            g(lambda: VS.fill_clip(store, USER, RUN, [MEDIA, m], 'VS1', 'c1', 10.0, 'yes', {'reason': 'the only shot of the kiln', 'considered': 'a drone view: none exists'}, [0.1, 0.1, 0.7, 0.7]))
    # 60 s apart, a different stretch, a crop of 30 % within a safe 2×: passes, approved on the page through the same function
    m2, data2 = master([{'kind': 'event', 'sub_clip_id': 'c1:SUB_01', 'source_in_frame': 0, 'source_out_frame': 100, 'timeline_in_frame': 3000, 'timeline_out_frame': 3100}])
    doc, sess = clip_session(clip_safe_zoom={'c1': 2.0})
    store = store_with(sess, doc)
    store.files['run-1/master-v1.json'] = data2
    why = {'reason': 'the only shot of the kiln', 'considered': 'a drone view: none exists'}
    with pytest.raises(Problem, match='different stretch'):
        g(lambda: VS.fill_clip(store, USER, RUN, [MEDIA, m2], 'VS1', 'c1', 2.0, 'yes', why, [0.1, 0.1, 0.7, 0.7]))   # 2-12 s overlaps 0-4 s
    with pytest.raises(Problem) as exc:
        g(lambda: VS.fill_clip(store, USER, RUN, [MEDIA, m2], 'VS1', 'c1', 10.0, 'Use the kiln clip.', why, [0.1, 0.1, 0.7, 0.7]))
    assert exc.value.code == 'REUSE_WAITING' and 'vw visuals reuse --shot VS1' in exc.value.message   # the checks pass; the assistant's quote is not the approval
    assert saved(store)['reuse_pending']['VS1']['reason'] == 'the only shot of the kiln' and 'VS1' not in saved(store)['assets']
    with pytest.raises(Problem, match='words approving the reuse'):
        g(lambda: VS.approve_reuse(store, USER, RUN, [MEDIA, m2], 'VS1', ''))
    out = VS.approve_reuse(store, USER, RUN, [MEDIA, m2], 'VS1', 'Yes, reuse it: no other shot shows the kiln.')
    assert out['reuse']['crop'] == [0.1, 0.1, 0.7, 0.7] and out['reuse']['approval'].startswith('Yes, reuse it') and 'VS1' not in saved(store).get('reuse_pending', {})
    assert saved(store)['assets']['VS1']['quote'] == 'Use the kiln clip.'


def test_two_shots_never_share_a_start_image_or_a_still():
    """H5; a shared boundary (an end image starting the next segment) is not compared."""
    doc, sess = clip_session(references={'R1': ref('R1', 'approved'), 'R2': ref('R2', 'approved')}, assets={'IM1': {'kind': 'still', 'reference_id': 'R1', 'key': 'k', 'placement': {'start_frame': 0, 'end_frame': 500}}})
    store = store_with(sess, doc)
    assert VS._start_images(store, saved(store)) == {}
    s = saved(store)
    s['preparations'] = {'VS0': {'preparation_id': 'p', 'key': 'x', 'start_image': 'R2', 'end_image': 'R9'}}
    store = store_with(s, doc)
    with pytest.raises(Problem, match='H5: picture R2 is already on screen in VS0'):
        g(lambda: VS.still_from_reference(store, USER, RUN, [], 'IM1', 'R2', 'yes'))


# ---------- H6: look-alike ----------

def test_identical_pictures_are_listed_and_two_different_diagrams_in_one_style_are_not():
    photo = png((90, 120, 60), box=((40, 30, 200, 150), (200, 30, 30)))
    def diagram(boxes):
        from PIL import ImageDraw
        img = PIL.new('RGB', (320, 180), (255, 255, 255))
        for b in boxes:
            ImageDraw.Draw(img).rectangle(b, fill=(20, 20, 20))
        buf = BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    d1 = diagram([(20, 20, 140, 60), (180, 120, 300, 160), (20, 120, 60, 160)])   # two walls and a label block
    d2 = diagram([(20, 20, 60, 160), (120, 60, 300, 100), (260, 120, 300, 160)])   # a section: a post, a beam, a footing
    rows = [{'label': 'A', 'at_s': 0, 'graphic': False, 'hashes': lookalike.image_hashes(photo)},
            {'label': 'B', 'at_s': 70, 'graphic': False, 'hashes': lookalike.image_hashes(photo)},
            {'label': 'D1', 'at_s': 90, 'graphic': True, 'hashes': lookalike.image_hashes(d1, True)},
            {'label': 'D2', 'at_s': 120, 'graphic': True, 'hashes': lookalike.image_hashes(d2, True)}]
    found = lookalike.pairs(rows)
    assert [(p['a'], p['b']) for p in found] == [('A', 'B')] and found[0]['a_at_s'] == 0 and found[0]['b_at_s'] == 70
    # a piece's last frame against the very next piece's first frame is a shared boundary, not a repeat
    seq = [{'label': 'S1', 'at_s': 0, 'hashes': [0, 2 ** 64 - 1]}, {'label': 'S2', 'at_s': 6, 'hashes': [2 ** 64 - 1, 2 ** 32 - 1]}]   # only S1's end matches S2's start
    assert lookalike.pairs(seq) == []
    flat = png((240, 240, 240))
    assert lookalike.image_hashes(flat) == [None] and lookalike.pairs([{'label': 'F1', 'at_s': 0, 'hashes': [None]}, {'label': 'F2', 'at_s': 9, 'hashes': [None]}]) == []


def test_the_plan_check_lists_the_placed_pictures_that_look_alike():
    photo = png((90, 120, 60), box=((40, 30, 200, 150), (200, 30, 30)))
    doc, sess = clip_session(assets={'IM1': {'kind': 'still', 'reference_id': 'R1', 'key': 'run-1/a.png', 'placement': {'start_frame': 0, 'end_frame': 100}},
                                     'IM2': {'kind': 'still', 'reference_id': 'R2', 'key': 'run-1/b.png', 'placement': {'start_frame': 2000, 'end_frame': 2100}}})
    store = store_with(sess, doc)
    store.files['run-1/a.png'] = photo
    store.files['run-1/b.png'] = photo
    assert [(p['a'], p['b']) for p in VS.look_alike_placed(store, saved(store))] == [('IM1', 'IM2')]


# ---------- the review of batch 1: the fixes ----------

def test_a_visuals_session_begun_before_the_release_is_warned_not_refused():
    """Finding 1: SK's rule, a run in progress is warned for one release; a session begun on this release refuses."""
    doc, sess = clip_session(references={'F1': frame_ref('F1', 'c1', 3.0)})
    sess.pop('repeat_rules')   # begun before batch 1
    store = store_with(sess, doc)
    m, data = master([{'kind': 'event', 'sub_clip_id': 'c1:SUB_01', 'source_in_frame': 0, 'source_out_frame': 100, 'timeline_in_frame': 0, 'timeline_out_frame': 100}])
    store.files['run-1/master-v1.json'] = data
    out = VS.still_from_reference(store, USER, RUN, [MEDIA, m], 'IM1', 'F1', 'yes')
    assert out['warnings'] and out['warnings'][0].startswith('H3: clip c1 plays elsewhere') and saved(store)['assets']['IM1']['repeat_warnings'] == out['warnings']


def test_a_new_visuals_session_refuses_the_repeat_rules(monkeypatch):
    monkeypatch.setattr(VS, 'gaps_source', lambda store, outputs: {'from': 'first_cut', 'fps': '25', 'gaps': {}})
    assert VS.session_of(FakeStore({}), RUN, [], create=True)['repeat_rules'] == 'refuse'


def test_a_shot_may_take_its_own_former_still_as_its_start_image():
    """Finding 2."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc), repeat_rules='refuse',
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', 'approved')}, assets={'VS1': {'kind': 'still', 'reference_id': 'R1', 'key': 'k', 'placement': {'start_frame': 900, 'end_frame': 1150}}},
                   bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}})
    out = VS.prepare_take(store_with(sess, doc), USER, RUN, [], {'shot_id': 'VS1', 'motion_prompt': 'water poured', 'subject_reconciliation': {}, 'start_image': 'R1', 'end_image': 'R2',
                                                                 'continuity_notes': 'the wall stays'})
    assert out['duration_seconds'] == 10


def test_a_session_prepared_before_batch_1_gets_its_timing_when_first_needed():
    """Finding 3: the check and the packet build the timing; no prepare needed."""
    doc, sess = clip_session(references={'R1': ref('R1', 'approved')}, bindings={})
    sess['bindings'] = {'VS1': {'gap_digest': gap_digest(doc, doc['gaps'][1]), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}}
    store = store_with(sess, doc)
    w = lambda i, text, a, b: {'id': f'w{i}', 'text': text, 'start_frame': a, 'end_frame': b}
    store.files['run-1/stage2/session.json'] = json.dumps({'package': {'key': 'run-1/stage2/package.json'}}).encode()
    store.files['run-1/stage2/package.json'] = json.dumps({'narration': {'words': [w(0, 'Bricks', 900, 950), w(1, 'stand.', 952, 1000)],
                                                                         'sentences': [{'text': 'Bricks stand.', 'start_frame': 900, 'end_frame': 1000}]}}).encode()
    assert 'timing' not in saved(store)['source']['gaps']['G2']
    ctx = VS.packet(store, RUN, [], 'VS1')['preparation']['context']
    assert ctx['timing']['sentences'][0]['text'] == 'Bricks stand.' and saved(store)['source']['gaps']['G2']['timing']['words'][0]['text'] == 'Bricks'
