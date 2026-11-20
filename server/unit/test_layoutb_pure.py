"""Layout B (SK, 20 Nov 2026): the layout video of step 7 is rendered in Blender's Workbench engine, flat colours with thin black outlines
(version B, measured on the VM: about 1 s a frame against EEVEE's 6.4 s); the first frame, from which the still is made, stays EEVEE at 16
samples. SK's addition: the boxes that stand for a person keep the colours that tell front, back and side apart, and the prompt names them:
a flat render has no shading, so the back of a box person is given its own purple mark (the purple the shot's drawing already uses).
Each test failed first. Blender and ffmpeg are faked (test_guide_worker_pure.py); guide_scene.py is read as text (it needs Blender to run)."""
import json
import re
import sys
from pathlib import Path

from app import config, guide as GD, guide_spec as G, guide_worker as W, draw3d
from test_guide_route_pure import TAKE_WORDS
from test_guide_spec_pure import counter_pour, home_walk
from test_guide_worker_pure import blender, job   # noqa: F401 (blender: the fixture)
from test_rel4_first_frame_pure import ffmpeg_into

ROOT = Path(__file__).resolve().parents[2]
SCENE = (ROOT / 'server' / 'blender' / 'guide_scene.py').read_text(encoding='utf-8')


# ---------- the switch ----------

def test_the_layout_video_look_is_one_setting_flat_by_default():
    assert config.Settings.model_fields['GUIDE_VIDEO_LOOK'].default == 'flat'
    assert config.Settings.model_fields['GUIDE_FRAME1_SAMPLES'].default == 16


def test_the_blender_call_carries_the_look(monkeypatch, tmp_path):
    seen = []

    def run(cmd, **kw):
        seen.append(cmd)
        (tmp_path / 'o').mkdir(exist_ok=True)
        (tmp_path / 'o' / 'g0001.png').write_bytes(b'x')
        return type('R', (), {'returncode': 0, 'stdout': 'GUIDE DONE 1\n', 'stderr': ''})()
    monkeypatch.setattr(W.subprocess, 'run', run)
    W.run_blender(tmp_path / 's.json', tmp_path / 'o', [1], 1, 'flat')
    W.run_blender(tmp_path / 's.json', tmp_path / 'o', [1], 16)
    assert seen[0][-3:] == ['frames=1', 'samples=1', 'look=flat'] and seen[1][-3:] == ['frames=1', 'samples=16', 'look=eevee']


def test_the_first_frame_stays_eevee_and_every_frame_of_the_video_is_flat(blender, monkeypatch):
    calls, store, tmp = blender
    W.process(job('guide-frame1', seconds=5))
    assert calls == [{'frames': [1], 'samples': 16, 'outdir': 'first', 'look': 'eevee'}]
    calls.clear()
    encoded = []
    ffmpeg_into(monkeypatch, encoded)
    status, result, error, cost, retry = W.process(job('guide-render', seconds=5, split=True))
    assert status == 'ready', error
    assert [c['frames'][0] for c in calls] == [1, 31, 61, 91, 121] and all(c['look'] == 'flat' and c['outdir'] == 'all' and c['samples'] == 1 for c in calls)   # frame 1 of the video too
    assert result['look'] == 'flat' and len(encoded) == 1


def test_a_video_job_that_makes_the_missing_first_frame_makes_it_eevee_and_the_video_flat(blender, monkeypatch):
    calls, store, tmp = blender
    ffmpeg_into(monkeypatch, [])
    W.process(job('guide-render', seconds=5))
    assert calls[0] == {'frames': [1], 'samples': 16, 'outdir': 'first', 'look': 'eevee'} and {c['look'] for c in calls[1:]} == {'flat'}


def test_the_check_frames_show_what_the_video_shows(blender):
    calls, store, tmp = blender
    W.process(job('guide-frames', frames=[1, 75, 150]))
    assert calls == [{'frames': [1, 75, 150], 'samples': 1, 'outdir': 'check', 'look': 'flat'}]


def test_the_setting_switches_the_video_back_to_eevee_without_code(blender, monkeypatch):
    calls, store, tmp = blender
    monkeypatch.setattr(W, 'settings', lambda: config.Settings(GUIDE_VIDEO_LOOK='eevee'))   # as VW2_GUIDE_VIDEO_LOOK=eevee in server/.env
    ffmpeg_into(monkeypatch, [])
    status, result, error, cost, retry = W.process(job('guide-render', seconds=5))
    assert status == 'ready' and {c['look'] for c in calls} == {'eevee'} and result['look'] == 'eevee'


def test_the_shot_keeps_the_look_its_video_was_rendered_in():
    session = {'guides': {'VS1': {'sha256': 'abc'}}}
    j = {'id': 'j9', 'request': {'kind': 'guide-render', 'shot_id': 'VS1', 'sha256': 'abc'}}
    GD.apply_result(session, j, 'ready', {'guide_key': 'g.mp4', 'sha256': 's', 'bytes': 1, 'frame1_key': 'f.png', 'frame1_sha256': 'f', 'render_seconds': 9, 'look': 'flat'}, None)
    assert session['guides']['VS1']['render']['look'] == 'flat'
    GD.apply_result(session, j, 'ready', {'guide_key': 'g.mp4', 'sha256': 's', 'bytes': 1, 'frame1_key': 'f.png', 'frame1_sha256': 'f', 'render_seconds': 9}, None)   # a record of the older code
    assert 'look' not in session['guides']['VS1']['render']


# ---------- the script ----------

def test_the_script_reads_the_look_and_refuses_an_unknown_one():
    assert "look = opt.get('look', 'eevee')" in SCENE and "if look not in ('eevee', 'flat'):" in SCENE


def test_the_flat_look_sets_exactly_version_b_with_thin_black_outlines():
    flat = SCENE[SCENE.index("if look == 'flat':"):SCENE.index('for f in frames:')]
    for line in ("sc.render.engine = 'BLENDER_WORKBENCH'", "sh.light = 'FLAT'", "sh.color_type = 'MATERIAL'", 'sh.show_shadows = False', "sc.display.render_aa = '5'",
                 'sh.show_object_outline = True', 'sh.object_outline_color = (0, 0, 0)', 'sc.world.color = tuple(c * strength for c in sky)'):
        assert line in flat, line
    assert "sc.render.engine = 'BLENDER_EEVEE'" in SCENE.split("if look == 'flat':")[1]   # the else: today's EEVEE, untouched


def test_every_material_has_its_viewport_colour_equal_to_its_node_colour():
    assert SCENE.count('bpy.data.materials.new(') == 1 and SCENE.count('.data.materials.append(mat(') == 2   # every box and every cylinder through mat()
    m = SCENE[SCENE.index('def mat(rgb):'):SCENE.index('def box(')]
    assert 'm.diffuse_color = (*key, 1)' in m and "b.inputs['Base Color'].default_value = (*key, 1)" in m


# ---------- the marks: front, back and side by colour alone ----------

def test_a_box_person_has_a_black_face_and_chest_a_purple_back_and_yellow_side_stripes():
    assert G.MARK_COLOURS == {'black': (0.03, 0.03, 0.03), 'purple': (0.47, 0.235, 0.667), 'yellow': (0.95, 0.85, 0.05)}
    assert max(abs(round(c * 255) - d) for c, d in zip(G.MARK_COLOURS['purple'], draw3d.BACK)) <= 1   # the purple of the shot's drawing
    people = SCENE[SCENE.index('# ---- the people'):SCENE.index('props = []')]
    assert "box('FACE_' + p['id']" in people and "box('CHEST_' + p['id']" in people
    assert "box('BACK_' + p['id'], (-0.12, 0.13, max(top - 0.45, 0.05)), (0.12, 0.145, top - 0.1), BACK, root)" in people          # the chest mark, mirrored
    assert "box('NAPE_' + p['id'], (-0.07, 0.11, top + 0.1), (0.07, 0.135, top + 0.2), BACK, root)" in people                      # the face mark, mirrored
    assert "BLACK, BACK, STRIPE = G.MARK_COLOURS['black'], G.MARK_COLOURS['purple'], G.MARK_COLOURS['yellow']" in SCENE


def test_a_person_the_colour_of_a_mark_is_warned_and_ordinary_colours_are_not():
    def colour_rows(spec):
        return [r['message'] for r in G.checks(spec) if r['check'] == 'colours' and 'mark' in r['message']]
    assert colour_rows(home_walk()) == []
    s = home_walk()
    s['people'][2]['colour'] = [0.45, 0.25, 0.65]
    assert colour_rows(s) == ['Colours: the mother is nearly the purple of the back mark on a box person; the mark would not show. Give the person another colour.']
    s = counter_pour()   # a yellow man: the yellow of the side stripes only matters when the scene has stripes
    assert colour_rows(s) == []
    s['marks'] = {'band': None, 'stripes': True}
    assert colour_rows(s) == ['Colours: the man is nearly the yellow of the side stripes on a box person; the mark would not show. Give the person another colour.']
    s['people'][0]['colour'] = [0.04, 0.04, 0.05]
    assert colour_rows(s) == ['Colours: the man is nearly the black of the face and chest marks on a box person; the mark would not show. Give the person another colour.']
    assert all(r['level'] == 'warn' for r in G.checks(s) if r['check'] == 'colours')


def test_two_touching_things_of_the_same_colour_are_already_warned():
    s = home_walk()
    s['set'][2]['colour'] = list(s['set'][1]['colour'])   # the verandah floor the colour of the house wall it touches
    assert 'Colours: the house wall and the verandah floor are nearly the same colour. Use dark, strongly contrasting colours, one per thing.' in [r['message'] for r in G.checks(s)]


# ---------- the words ----------

def test_the_take_and_the_still_name_the_mark_colours():
    assert 'The small black squares on box people mark their face and chest, and the purple squares their back, so they show which way each person faces.' in GD.TAKE_OPEN
    assert 'The small black squares on box people mark the face and chest, and the purple squares the back, so they show which way each person faces.' in GD.STILL_OPEN
    sent = GD.effective_prompt({'marks': {'band': 'LANE', 'stripes': True}}, TAKE_WORDS)
    assert "the thin yellow stripe down the side of each box person marks that person's side." in sent


def test_a_flat_video_is_explained_once_and_an_eevee_one_is_not():
    flat = GD.effective_prompt({'render': {'look': 'flat'}}, TAKE_WORDS)
    assert flat.count(GD.FLAT_LINE) == 1 and flat.index(GD.TAKE_OPEN) < flat.index(GD.FLAT_LINE) < flat.index(TAKE_WORDS)
    assert GD.FLAT_LINE == ('The video is drawn in flat colours with thin black outlines only to mark the layout; the footage shows neither: '
                            'its light, shadows and surfaces are those of the image.')
    assert GD.FLAT_LINE not in GD.effective_prompt({'render': {'look': 'eevee'}}, TAKE_WORDS) and GD.FLAT_LINE not in GD.effective_prompt({}, TAKE_WORDS)
    assert GD.prompt_problems(GD.FLAT_LINE) == []
    assert GD.prompt_problems(flat.replace(GD.TAKE_OPEN, '')) == [] and 'ONE action only' in flat


def test_the_still_explains_the_band_and_the_stripes_as_the_take_does():
    assert GD.marks_line({}, 'image') == ''
    assert GD.marks_line({'band': 'LANE', 'stripes': True}, 'image') == ("How to read the image: the coloured band on the ground only marks where the walking line runs; it is not a thing in the place and is never shown. "
                                                                         "the thin yellow stripe down the side of each box person marks that person's side.")


# ---------- the checker's helper text ----------

def test_the_checker_is_told_what_the_check_frames_show():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import layoutb_wording as L
    check = (ROOT / 'plugin' / 'agents' / 'vw-guide-check.md').read_text(encoding='utf-8')
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert check.count(L.CHECK_NEW) == 1 and L.CHECK_OLD not in check and L.CHECK_OLD in retired
    assert 'flat colours with thin black outlines' in L.CHECK_NEW and 'purple back mark' in L.CHECK_NEW and 'yellow stripe' in L.CHECK_NEW
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('from rel4_wording import apply as rel4') < split.index('from layoutb_wording import apply as layoutb') < split.index('from d132_wording_v3 import')


def test_nothing_but_the_worker_and_the_take_words_reads_the_look():
    readers = sorted(f.name for f in (ROOT / 'server' / 'app').rglob('*') if f.suffix in ('.py', '.html', '.js')
                     and re.search(r"GUIDE_VIDEO_LOOK|render[^\n]{0,30}\.get\('look'\)", f.read_text(encoding='utf-8', errors='replace')))
    assert readers == ['config.py', 'guide.py', 'guide_worker.py']
