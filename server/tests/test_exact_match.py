"""design/21: exact-match editing. Blanks inside a scene, match evidence, decision slides, the reuse rule, short real shots,
numbered slides, the review film sequence, master decisions by slide number, gaps for the visuals stage."""
import json
import os
import shutil
import subprocess
from pathlib import Path
from copy import deepcopy

import pytest

from app.stage2 import render as R, slides as SL, validator as V
from conftest import vw
from test_analysis import FakeTransport, gemini  # noqa: F401
from test_stage2 import POLICY, approve_scenes, blank, ev, good_doc, make_package, option, run_until_options, silences_in
from test_voice_media import drain, fake  # noqa: F401

FPS = 25


def pk_with(beat_frames=(112, 13)):
    a, b = beat_frames
    return make_package(beats=[{'beat_id': 'BEAT_01', 'passage_id': 'P001', 'title': 'Pressing the blocks', 'text': 'One.', 'timeline_start_frame': 0, 'timeline_end_frame': a, 'target_beat_frames': a},
                               {'beat_id': 'BEAT_02', 'passage_id': 'P002', 'title': 'Not fired', 'text': 'Two.', 'timeline_start_frame': a, 'timeline_end_frame': a + b, 'target_beat_frames': b}])


def doc_with(events, extra=()):
    return {'contract': 'vw2-options-v1', 'options': [option(1, 'BEAT_01', 'PRIMARY', events), *extra], 'gaps': [{'beat_id': 'BEAT_02', 'reason': 'abstract'}],
            'qc_self': {f'Q{i}': {'pass': True, 'evidence': 'synthetic'} for i in range(1, 9)}}


def check(doc, pk=None):
    return V.validate_options(deepcopy(doc), pk or pk_with(), POLICY)


# ---------- validator ----------

def test_blank_inside_a_scene_counts_toward_its_length():
    r = check(doc_with([ev('clip0:SUB_01', 0, 25), blank(75), ev('clip1:SUB_01', 0, 12)]))
    assert r['refusals'] == [], r
    r = check(doc_with([ev('clip0:SUB_01', 0, 25), blank(74), ev('clip1:SUB_01', 0, 12)]))
    assert any('G11' in x for x in r['refusals'])


def test_blank_needs_intent_and_at_least_3_s_or_the_operators_call():
    r = check(doc_with([ev('clip0:SUB_01', 0, 25), blank(75, intent=''), ev('clip1:SUB_01', 0, 12)]))
    assert any('intent is required' in x for x in r['refusals'])
    short = doc_with([ev('clip0:SUB_01', 0, 25), blank(50), ev('clip1:SUB_01', 0, 12)])   # 2 s blank
    assert any('E1' in x for x in check(short, pk_with((87, 13)))['refusals'])
    short['options'][0]['events'][1]['short_reason'] = 'the neighbouring shots have no more usable frames'
    r = check(short, pk_with((87, 13)))
    assert r['refusals'] == [] and any('E1' in f for f in r['flags']), r


def test_every_real_shot_states_its_match_and_b_roll_goes_behind_a_decision():
    d = doc_with([ev('clip0:SUB_01', 0, 25, match=None), blank(75), ev('clip1:SUB_01', 0, 12, evidence='')])
    assert sum('match (direct or b_roll) and evidence' in x for x in check(d)['refusals']) == 2
    d = doc_with([ev('clip0:SUB_01', 0, 25), blank(75), ev('clip1:SUB_01', 0, 12, match='b_roll')])
    assert any('B-roll goes behind a decision slide' in x for x in check(d)['refusals'])
    d['options'][0]['events'][2]['decision'] = {'kind': 'b_roll', 'question': 'Site footage for "less material": keep it, or leave it for AI?'}
    assert check(d)['refusals'] == []
    d['options'][0]['events'][2]['decision'] = {'kind': 'maybe', 'question': 'x'}
    assert any('decision needs kind' in x for x in check(d)['refusals'])


def test_poor_quality_match_goes_behind_a_decision():
    pk = pk_with()
    next(r for r in pk['sub_clips'] if r['sub_clip_id'] == 'clip1:SUB_01')['grade'] = 'C'
    d = doc_with([ev('clip0:SUB_01', 0, 25), blank(75), ev('clip1:SUB_01', 0, 12)])
    assert any('E3' in x for x in check(d, pk)['refusals'])
    d['options'][0]['events'][2]['decision'] = {'kind': 'poor_quality', 'question': 'The log says this is shaky. Judge it by eye.'}
    assert check(d, pk)['refusals'] == []


def test_a_clip_is_used_once_unless_the_operator_chooses_a_reuse():
    pk = pk_with((112, 24))
    second = [option(2, 'BEAT_02', 'PRIMARY', [ev('clip0:SUB_02', 25, 49)])]   # another part of clip0, already used in scene 1
    d = doc_with([ev('clip0:SUB_01', 0, 25), blank(75), ev('clip1:SUB_01', 0, 12)], second)
    d['gaps'] = []
    assert any('Q4 clip clip0' in x for x in check(d, pk)['refusals'])
    d['options'][1]['events'][0]['decision'] = {'kind': 'reuse', 'question': 'The same clip again, a later moment: keep it, or blank?'}
    assert check(d, pk)['refusals'] == []
    d = doc_with([ev('clip0:SUB_01', 0, 25), blank(75), ev('clip0:SUB_02', 25, 37)])   # twice inside one option
    assert any('Q4 clip clip0' in x for x in check(d)['refusals'])


def test_a_long_real_shot_must_earn_its_length():
    pk = pk_with((125, 13))
    row = next(r for r in pk['sub_clips'] if r['sub_clip_id'] == 'clip0:SUB_01')
    row['out_frame'] = 125
    d = doc_with([ev('clip0:SUB_01', 0, 125)])
    assert any('rule 11' in f for f in check(d, pk)['flags'])
    d['options'][0]['events'][0]['hold_reason'] = 'the whole course is laid in one continuous action'
    assert not any('rule 11' in f for f in check(d, pk)['flags'])


# ---------- slides and the review film sequence ----------

def proposed(doc, pk):
    work = deepcopy(doc)
    assert V.validate_options(work, pk, POLICY)['refusals'] == []
    for o in work['options']:
        for e in o['events']:
            e['timeline_frames'] = e.pop('_timeline_frames')
    return work


def test_slides_are_numbered_in_film_order_with_readable_ascii_text():
    pk = pk_with()
    d = doc_with([ev('clip0:SUB_01', 0, 25), blank(75, intent='Bricks saved compared with a solid wall — an animation'),
                  ev('clip1:SUB_01', 0, 12, match='b_roll', decision={'kind': 'b_roll', 'question': 'Site footage for "less material": keep it, or leave it for AI?'})],
                 [option(2, 'BEAT_01', 'SECONDARY', [ev('clip2:SUB_01', 0, 25), blank(87)])])
    sl = SL.slides(proposed(d, pk), pk, FPS)
    # design/44 8.1: running numbers for the scene's option and its backup, letters inside an option
    assert [(s['no'], s['type']) for s in sl] == [('1', 'option'), ('1A', 'blank'), ('1B', 'decision'), ('2', 'backup'), ('2A', 'blank')]
    assert sl[0]['lines'][0] == '#1 | Scene 1: Pressing the blocks | 4.5 s | 2 shots'
    assert sl[3]['lines'][0].startswith('#2 | Scene 1: Pressing the blocks | BACKUP for #1 | 4.5 s | 1 shot')
    assert sl[1]['lines'][:2] == ['#1A | BLANK | Scene 1: Pressing the blocks | 3.0 s', 'For AI video or animation']
    assert sl[2]['lines'][0] == '#1B | DECISION | Scene 1: Pressing the blocks' and sl[2]['lines'][-1].startswith('Keep or drop: synthetic test clip')
    assert all(len(l) <= 80 and all(ord(c) < 127 for c in l) for s in sl for l in s['lines'])
    assert 'SUB_' not in json.dumps([s['lines'] for s in sl])   # readable names, not internal codes


def test_review_sequence_keeps_words_with_their_pictures():
    pk = pk_with()
    d = proposed(doc_with([ev('clip0:SUB_01', 0, 25), blank(75), ev('clip1:SUB_01', 0, 12, match='b_roll', decision={'kind': 'b_roll', 'question': 'keep?'})]), pk)
    items = SL.review_items(d, pk, SL.slides(d, pk, FPS), lambda evs: [{'kind': 'event', 'frames': e['timeline_frames']} for e in evs], FPS)
    assert [i['kind'] for i in items] == ['slate', 'narration', 'event', 'card', 'slate', 'narration', 'event']
    assert items[2]['label'] == '#1' and items[6]['label'] == '#1B DECISION'   # every real shot shows which slide it belongs to
    n1, n2 = items[1], items[5]
    assert (n1['start_s'], n1['end_s']) == (0.0, 100 / FPS) and (n2['start_s'], n2['end_s']) == (100 / FPS, 112 / FPS)   # split at the decision; the blank keeps its words
    assert items[3]['frames'] == 75 and items[3]['lines'][0].startswith('#1A | BLANK')


def test_render_a_blank_card_carries_the_narration_and_a_decision_slide_is_silent(tmp_path):
    tone = tmp_path / 'narration.wav'   # 1 s of silence, then 1 s of tone
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo:d=1', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1:sample_rate=48000',
                    '-filter_complex', '[1]aformat=channel_layouts=stereo[t];[0][t]concat=n=2:v=0:a=1', str(tone)], check=True)
    items = [{'kind': 'slate', 'lines': ['#01'], 'frames': 25}, {'kind': 'narration', 'start_s': 0.0, 'end_s': 1.0}, {'kind': 'card', 'frames': 25, 'lines': ['#02 | BLANK']},
             {'kind': 'slate', 'lines': ['#03 | DECISION'], 'frames': 25}, {'kind': 'narration', 'start_s': 1.0, 'end_s': 2.0}, {'kind': 'card', 'frames': 25, 'lines': ['#04 | BLANK']}]
    film, record = R.render_film('review', {'items': items}, {}, tone, tmp_path / 'work', {'width': 320, 'height': 180, 'fps': 25})
    assert abs(record['duration_s'] - 4.0) < 0.1
    sil = silences_in(film, 0.5)
    assert len(sil) == 1 and sil[0][0] < 0.05 and abs(sil[0][1] - 3.0) < 0.15, sil   # silent until 3 s, then the tone under the last card


# ---------- end to end: decisions by slide number, blanks become visuals gaps ----------

def author_exact(pk):
    """Scene 1: one direct shot, a blank, then a B-roll offered as a decision. Scene 2 is a declared blank."""
    rows = [r for r in pk['sub_clips'] if r['eligibility'] == 'ELIGIBLE_AS_IS']
    first = rows[0]
    other = next(r for r in rows if r['clip_id'] != first['clip_id'])
    b1 = pk['beats'][0]
    n1, n3 = first['out_frame'] - first['in_frame'], other['out_frame'] - other['in_frame']
    gap = b1['target_beat_frames'] - n1 - n3
    assert gap >= 75, (b1, n1, n3)
    events = [ev(first['sub_clip_id'], first['in_frame'], first['out_frame']), blank(gap, intent='blocks curing, as an animation'),
              ev(other['sub_clip_id'], other['in_frame'], other['out_frame'], match='b_roll', decision={'kind': 'b_roll', 'question': 'Related site footage: keep it, or leave it blank?'})]
    return {'contract': 'vw2-options-v1', 'options': [option(1, b1['beat_id'], 'PRIMARY', events)],
            'gaps': [{'beat_id': b['beat_id'], 'reason': 'abstract claim'} for b in pk['beats'][1:]], 'qc_self': {f'Q{i}': {'pass': True, 'evidence': 'synthetic'} for i in range(1, 9)}}, gap, n1, n3


def test_exact_match_end_to_end(home, database, fake, gemini):
    code, ws, _ = run_until_options(home, database, fake, gemini)
    _, pk = approve_scenes(home, ws, pause_s=4.0)   # a long first scene: room for a 3 s blank
    doc, gap, n1, n3 = author_exact(pk)
    (ws / 'out' / 'options.json').write_text(json.dumps(doc), encoding='utf-8')
    rc, out, err = vw(home, 'options', 'check', '--file', 'out/options.json')
    assert rc == 0 and out['status'] == 'valid', (out, err)
    s1 = out['scenes'][0]
    assert (s1['real_s'], s1['blank_s'], s1['decisions']) == (round(n1 / FPS, 2), round(gap / FPS, 2), 1) and out['scenes'][1]['note'] == 'declared blank'
    rc, out, err = vw(home, 'options', 'propose', '--file', 'out/options.json')
    assert rc == 0, (out, err)
    assert [(s['no'], s['type']) for s in out['slides']] == [('1', 'option'), ('1A', 'blank'), ('1B', 'decision')]
    assert vw(home, 'options', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'options', 'fetch')
    b1 = pk['beats'][0]['target_beat_frames']
    assert rc == 0 and abs(out['duration_s'] - (75 + b1 + 75) / FPS) < 0.15, (out, err)   # #01 slide + the scene + #03 decision slide
    keep = os.environ.get('VW2_TEST_KEEP_FILMS')   # optional: copy the films for a human to watch
    if keep:
        Path(keep).mkdir(parents=True, exist_ok=True)
        shutil.copy(ws / 'out' / 'review.mp4', Path(keep) / 'synthetic-review-film.mp4')
    assert vw(home, 'options', 'record', '--quote', 'yes, these options')[0] == 0
    # answers by slide label (design/44 8.1)
    rc, out, err = vw(home, 'master', 'slides')
    assert rc == 0 and out['waiting'] == ['1', '1B'] and out['of'] == 2 and 'waiting: 1, 1B' in err, (out, err)
    rc, out, _ = vw(home, 'master', 'decide', '--slide', '1A', '--action', 'KEEP')
    assert rc == 2 and 'needs no decision' in out['message']
    rc, out, _ = vw(home, 'master', 'decide', '--slide', '1b', '--action', 'REJECT')
    assert rc == 2 and 'KEEP or DROP' in out['message']
    (ws / 'out' / 'decisions.json').write_text(json.dumps([{'slide': '1', 'action': 'KEEP'}, {'slide': '7', 'action': 'KEEP'}, {'slide': '#1b', 'action': 'DROP'}]), encoding='utf-8')
    rc, out, _ = vw(home, 'master', 'decide', '--file', 'out/decisions.json')
    assert rc == 2 and out['recorded'] == ['1'] and out['refused']['slide'] == '7' and 'No slide #7' in out['refused']['message'] and out['remaining'] == ['1B'], out
    rc, out, _ = vw(home, 'master', 'build')
    assert rc == 2 and '#1B' in out['message']
    (ws / 'out' / 'decisions.json').write_text(json.dumps([{'slide': '#1b', 'action': 'DROP'}]), encoding='utf-8')
    rc, out, _ = vw(home, 'master', 'decide', '--file', 'out/decisions.json')
    assert rc == 0 and out['recorded'] == ['1B'] and out['decided'] == 2 and out['of'] == 2, out
    assert vw(home, 'master', 'slides')[1]['waiting'] == []
    rc, out, err = vw(home, 'master', 'build')
    assert rc == 0 and out['gaps'] == ['BEAT_01-B1', 'BEAT_02'] and out['events'] == 1, (out, err)   # the dropped B-roll joined the blank
    assert vw(home, 'master', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'master', 'fetch')
    assert rc == 0 and abs(out['duration_s'] - pk['narration']['total_frames'] / FPS) < 0.15, (out, err)
    if keep:
        shutil.copy(ws / 'out' / 'master.mp4', Path(keep) / 'synthetic-master-film.mp4')
    rc, out, _ = vw(home, 'master', 'record', '--quote', 'yes the master')
    assert rc == 2 and 'listened' in out['message']   # design/44 8.4: one approval, with the first cut's words
    rc, out, err = vw(home, 'master', 'record', '--quote', 'yes the master, watched and listened')
    assert rc == 0 and out['gaps'] == ['BEAT_01-B1', 'BEAT_02'] and out['first_cut_output'], (out, err)
    nxt = vw(home, 'next')[1]
    assert nxt['stage'] == 'visuals' and nxt['units_open'] == ['BEAT_01-B1', 'BEAT_02'], nxt
    assert vw(home, 'view', '--stage', 'first_cut')[1]['outputs'][0]['summary']['master_output'] == out['output']
    rc, out, err = vw(home, 'visuals', 'prepare')
    assert rc == 0, (out, err)


def test_dropping_a_short_placement_between_two_shots_is_refused_at_build():
    """A dropped placement under 3 s with real shots on both sides cannot become a blank (E1)."""
    from app.stage2 import stage as S

    class Store(dict):
        def get(self, k):
            from app.errors import Problem
            if k not in self:
                raise Problem(404, 'FILE_MISSING', 'Stored file not found.')
            return self[k]

        def put(self, k, data, mime=None):
            self[k] = data

        def exists(self, k):
            return k in self
    pk = pk_with((49, 13))
    d = proposed(doc_with([ev('clip0:SUB_01', 0, 25), ev('clip1:SUB_01', 0, 12, match='b_roll', decision={'kind': 'b_roll', 'question': 'keep?'}), ev('clip2:SUB_02', 25, 37, crop='solver')]), pk)
    st, run = Store(), {'id': 'r', 'code': 'VW-T'}
    entry = {'version': 1, 'digest': 'd', 'slides': SL.slides(d, pk, FPS), 'file': S.save_json(st, S.key(run, 'options-v1.json'), {'document': d})}
    pk_ref = S.save_json(st, S.key(run, 'package.json'), pk)
    session = {**S.session_of(st, run, create=True), 'package': {**pk_ref, 'policy': POLICY}, 'versions': [entry], 'current': 'd', 'accepted': {'version': 1},
               'decisions': {'1': {'action': 'KEEP', 'type': 'option'}, '2': {'action': 'DROP', 'type': 'decision'}}}
    S.save_session(st, run, session)
    with pytest.raises(Exception) as e:
        S.build_master(None, st, {'id': 'u'}, run)
    assert 'under 3 s' in str(e.value)


def test_one_generated_shot_is_at_most_30_s_and_a_long_blank_is_several_shots():
    from app.visual_contract import validate_plan
    from test_visuals import scene, shot, visual_plan
    plan = visual_plan(1000)
    plan['gaps'] = plan['gaps'][:1]
    gaps = {'G1': {'start_frame': 0, 'end_frame': 1000, 'passage_ids': [], 'requirement': 'kiln'}}
    plan['gaps'][0]['scenes'] = [scene('SC1', [shot('VS1', 0, 1000, 'video')])]   # 40 s in one shot
    with pytest.raises(ValueError, match='at most 30 s'):
        validate_plan(plan, gaps, 25)
    plan['gaps'][0]['scenes'] = [scene('SC1', [shot('VS1', 0, 750, 'video'), shot('VS2', 750, 1000, 'video')])]   # 30 s + 10 s
    validate_plan(plan, gaps, 25)


def test_slides_show_the_number_large_and_footage_carries_a_corner_label(tmp_path):
    from PIL import Image
    amber = lambda im, box: any(r > 200 and 150 < g < 230 and b < 120 for r, g, b in im.crop(box).convert('RGB').getdata())
    R.slate_png(['#3B | DECISION | Scene 3: Why Rat-Trap Bond is different', 'Keep or drop?'], 640, 360, tmp_path / 's.png')
    assert amber(Image.open(tmp_path / 's.png'), (0, 0, 640, 360))          # the number, drawn large in amber
    R.slate_png(['no number here'], 640, 360, tmp_path / 'p.png')
    assert not amber(Image.open(tmp_path / 'p.png'), (0, 0, 640, 360))
    src = tmp_path / 'src.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=0x204060:s=320x180:r=25:d=2', '-pix_fmt', 'yuv420p', str(src)], check=True)
    r = R.Renderer(tmp_path / 'work', {'width': 320, 'height': 180, 'fps': 25})
    seg = r.segment(src, 'x' * 64, '25', {'source_in_frame': 0, 'source_out_frame': 25}, 25, label='#08')
    plain = r.segment(src, 'x' * 64, '25', {'source_in_frame': 0, 'source_out_frame': 25}, 25)
    assert seg != plain
    frames = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_entries', 'stream=nb_read_frames', '-of', 'json', str(seg)], capture_output=True, check=True).stdout)
    assert int(frames['streams'][0]['nb_read_frames']) == 25
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(seg), '-frames:v', '1', str(tmp_path / 'f.png')], check=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(plain), '-frames:v', '1', str(tmp_path / 'g.png')], check=True)
    assert amber(Image.open(tmp_path / 'f.png'), (0, 0, 120, 50)) and not amber(Image.open(tmp_path / 'g.png'), (0, 0, 120, 50))


def test_after_three_review_rounds_the_assistant_suggests_blanks():
    from app.stage2 import stage as S
    assert S.round_advice(1) is None and S.round_advice(3) is None
    assert 'blanks' in S.round_advice(4) and 'round 4' in S.round_advice(4)


def test_blanks_inside_a_scene_go_through_visuals_and_assembly(home, database, fake, gemini):
    """Tickets 12 and 13: a gap named BEAT_01-B1 (a blank inside scene 1) is filled, recorded and assembled; two of its shots share one still."""
    from test_visuals import png_bytes, scene, shot, vplan
    code, ws, _ = run_until_options(home, database, fake, gemini)
    _, pk = approve_scenes(home, ws, pause_s=4.0)
    doc, gap, n1, n3 = author_exact(pk)
    (ws / 'out' / 'options.json').write_text(json.dumps(doc), encoding='utf-8')
    assert vw(home, 'options', 'propose', '--file', 'out/options.json')[0] == 0
    assert vw(home, 'options', 'render')[0] == 0
    drain()
    assert vw(home, 'options', 'record', '--quote', 'yes, these options')[0] == 0
    assert vw(home, 'master', 'decide', '--slide', '1', '--action', 'KEEP')[0] == 0
    assert vw(home, 'master', 'decide', '--slide', '1B', '--action', 'DROP')[0] == 0
    assert vw(home, 'master', 'build')[0] == 0
    assert vw(home, 'master', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'master', 'record', '--quote', 'yes the master, watched and listened')
    assert rc == 0 and out['gaps'] == ['BEAT_01-B1', 'BEAT_02'], (out, err)
    gaps = {g['shot_id']: g for g in vw(home, 'view', '--stage', 'first_cut')[1]['outputs'][0]['summary']['gaps']}
    assert vw(home, 'visuals', 'prepare')[0] == 0
    b1, b2 = gaps['BEAT_01-B1'], gaps['BEAT_02']
    mid = (b1['start_frame'] + b1['end_frame']) // 2
    plan = {'foundation': {'treatment': 'documentary', 'appearance': 'warm'}, 'elements': [{'id': 'E1', 'name': 'wall', 'kind': 'object', 'identity': 'representative', 'requirements': 'a wall'}],
            'gaps': [{'gap_id': 'BEAT_01-B1', 'intent': 'curing', 'treatment_fit': 'fits', 'scenes': [scene('SC1', [shot('VA', b1['start_frame'], mid, 'image', subjects=False),
                                                                                                                  shot('VB', mid, b1['end_frame'], 'image', subjects=False)])]},
                     {'gap_id': 'BEAT_02', 'intent': 'not fired', 'treatment_fit': 'fits', 'scenes': [scene('SC2', [shot('VC', b2['start_frame'], b2['end_frame'], 'image', subjects=False)])]}]}
    rc, out, err = vw(home, 'visuals', 'propose', '--file', vplan(ws, plan))
    assert rc == 0, (out, err)
    assert vw(home, 'visuals', 'accept', '--gaps', 'BEAT_01-B1', 'BEAT_02', '--quote', 'yes')[0] == 0
    (ws / 'out' / 'placeholder.png').write_bytes(png_bytes((40, 40, 40), (1920, 1080)))
    assert vw(home, 'upload', '--stage', 'visuals', '--file', 'out/placeholder.png')[0] == 0
    for s in ('VA', 'VB', 'VC'):   # one file shared by three shots, two of them in the same gap (ticket 12)
        assert vw(home, 'visuals', 'asset', '--shot', s, '--file', 'out/placeholder.png', '--kind', 'still', '--quote', 'placeholder')[0] == 0
    for g in ('BEAT_01-B1', 'BEAT_02'):
        rc, out, err = vw(home, 'visuals', 'record', '--gap', g, '--quote', 'done')
        assert rc == 0, (out, err)
    assert vw(home, 'next')[1]['stage'] == 'assembly'
    rc, out, err = vw(home, 'assembly', 'prepare')
    assert rc == 0 and set(out['fills']) == {'VA', 'VB', 'VC'}, (out, err)
    rc, out, err = vw(home, 'assembly', 'build')
    assert rc == 0, (out, err)
    assert vw(home, 'assembly', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'assembly', 'fetch')
    assert rc == 0 and abs(out['duration_s'] - pk['narration']['total_frames'] / FPS) < 0.15, (out, err)
