"""Stage 3 (assembly → delivery → Resolve once → final → close with retention), design/16 + 17. Resolve is the fake adapter; FFmpeg is real."""
import json
import os
import subprocess
from pathlib import Path

import psycopg
import pytest

from app.stage3 import delivery as D
from conftest import vw
from test_analysis import FakeTransport, gemini  # noqa: F401
from test_stage2 import approve_default_scenes, approve_scenes, author, run_until_options, silences_in
from test_visuals import png_bytes, scene, shot, vplan
from test_voice_media import drain, fake  # noqa: F401


def ffprobe_video(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)], capture_output=True, check=True).stdout
    return next(s for s in json.loads(out)['streams'] if s['codec_type'] == 'video')


def run_until_assembly(home, database, fake, gemini, scenes=False):
    """Through options, master, first cut, and the visuals gap BEAT_02 filled with a still asset. scenes: two scenes with a pause (design/19)."""
    code, ws, pk = run_until_options(home, database, fake, gemini)
    _, pk = approve_scenes(home, ws) if scenes else approve_default_scenes(home, ws)   # design/43 7.3: scenes are always approved first
    (ws / 'out' / 'options.json').write_text(json.dumps(author(pk)), encoding='utf-8')
    assert vw(home, 'options', 'propose', '--file', 'out/options.json')[0] == 0
    assert vw(home, 'options', 'render')[0] == 0
    drain()
    assert vw(home, 'options', 'record', '--quote', 'yes')[0] == 0
    assert vw(home, 'master', 'decide', '--option', '1', '--action', 'KEEP')[0] == 0
    assert vw(home, 'master', 'decide', '--option', '2', '--action', 'REJECT', '--note', 'prefer the wide')[0] == 0
    assert vw(home, 'master', 'build')[0] == 0
    assert vw(home, 'master', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'master', 'record', '--quote', 'yes master, watched and listened')   # design/44 8.4: records the first cut too
    assert rc == 0 and out['first_cut_output'], (out, err)
    gap = out['gaps'][0]
    fc = vw(home, 'view', '--stage', 'first_cut')[1]['outputs'][0]['summary']['gaps'][0]
    # visuals: one still for the gap
    assert vw(home, 'visuals', 'prepare')[0] == 0
    plan = {'foundation': {'treatment': 'documentary', 'appearance': 'warm'}, 'elements': [{'id': 'E1', 'name': 'wall', 'kind': 'object', 'identity': 'representative', 'requirements': 'a wall'}],
            'gaps': [{'gap_id': gap, 'intent': 'the wall', 'treatment_fit': 'fits', 'scenes': [scene('SC1', [shot('VS2', fc['start_frame'], fc['end_frame'], 'image', subjects=False)])]}]}
    rc, out, err = vw(home, 'visuals', 'propose', '--file', vplan(ws, plan))
    assert rc == 0, (out, err)
    assert vw(home, 'visuals', 'accept', '--gaps', gap, '--quote', 'yes')[0] == 0
    (ws / 'out' / 'wall.png').write_bytes(png_bytes((90, 90, 90), (1920, 1080)))
    assert vw(home, 'upload', '--stage', 'visuals', '--file', 'out/wall.png')[0] == 0
    assert vw(home, 'visuals', 'asset', '--shot', 'VS2', '--file', 'out/wall.png', '--kind', 'still', '--quote', 'use it')[0] == 0
    rc, out, err = vw(home, 'visuals', 'record', '--gap', gap, '--quote', 'done')
    assert rc == 0, (out, err)
    assert vw(home, 'next')[1]['stage'] == 'assembly'
    return code, ws, pk


def test_d1_d10_d12_d13_d15_d16_d17_d18_end_to_end(home, database, fake, gemini):
    code, ws, pk = run_until_assembly(home, database, fake, gemini)
    rc, out, err = vw(home, 'assembly', 'prepare')
    assert rc == 0 and 'VS2' in out['fills'] and out['fills']['VS2']['default']['end_policy'] == 'hold_last', (out, err)
    # D38/D39: a movie fill shorter than its slot cannot be trimmed; a still is held
    rc, out, _ = vw(home, 'assembly', 'choose', '--shot', 'VS2', '--offset', '0', '--end', 'hold_last')
    assert rc == 0
    rc, out, err = vw(home, 'assembly', 'build')
    assert rc == 0 and out['events'] == 3, (out, err)   # 2 footage events + 1 fill
    assert vw(home, 'assembly', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'assembly', 'fetch')
    assert rc == 0 and abs(out['duration_s'] - 2.0) < 0.15, (out, err)   # D1: duration = sum of beats
    rec = out['record']
    assert rec['a1_measured']['integrated_lufs'] is not None and rec['mix']['integrated_lufs'] is not None   # D9 measured
    assert rec['loudness_check']['peak_ceiling_dbtp'] == -3 and rec['loudness_check']['peak_inside'] is True   # design/46 11.6
    assert ffprobe_video(ws / 'out' / 'assembly.mp4')['width'] == 1920   # design/46 11.1: the delivered film is the full one
    # D10 (design/46 11.5): the record itself needs the watched-and-listened words; without them, refused
    rc, out, _ = vw(home, 'assembly', 'record', '--quote', 'yes')
    assert rc == 2 and 'listened' in out['message']
    rc, out, _ = vw(home, 'assembly', 'review', '--decision', 'changes', '--notes', 'hold the wall longer', '--frame-note', '0:01.6:too short', '--quote', 'change it')
    assert rc == 0 and out['frame_notes'][0]['frame'] == 40
    assert vw(home, 'assembly', 'build')[0] == 0   # a new version after changes
    rc, out, _ = vw(home, 'assembly', 'render')
    assert rc == 0 and out['frames'] == 50   # design/46 11.4
    drain()
    rc, st, err = vw(home, 'assembly', 'status')
    assert rc == 0 and st['renders']['assembly']['status'] == 'ready' and st['renders']['assembly']['frames'] == 50 and st['render_rate_fps'] > 0 and 'assembly film ready' in err
    rc, out, err = vw(home, 'assembly', 'record', '--quote', 'yes assembly, watched it and listened to it')   # one call: the accepted review and the output
    assert rc == 0, (out, err)
    assert vw(home, 'view', '--stage', 'assembly')[1]['outputs'][0]['summary']['review']['decision'] == 'accepted'
    assert vw(home, 'next')[1]['stage'] == 'delivery'
    # D12: bundle manifest lists every file with hashes; D15/D16 SRT and checklist
    rc, out, err = vw(home, 'delivery', 'bundle')
    assert rc == 0 and out['files'] >= 8, (out, err)
    manifest = json.loads((ws / 'work' / 'manifest.json').read_text(encoding='utf-8'))
    roles = {f['role'] for f in manifest['files']}
    assert {'approved_film', 'narration', 'original', 'normalised', 'plan', 'generated'} <= roles and all(len(f['sha256']) == 64 for f in manifest['files'])
    names = {f['name'] for f in manifest['files']}
    assert {'Subtitles.srt', 'Finishing-checklist.md', 'Media-pool.csv', 'OPEN-EDIT.md', 'Approved-film.mp4'} <= names
    from app.storage import storage as _storage
    gen = {f['name']: f['key'] for f in manifest['files'] if f['role'] == 'generated'}
    checklist = _storage().get(gen['Finishing-checklist.md']).decode('utf-8')
    assert 'measured ' in checklist and '-3 dBTP' in checklist and '-14 LUFS' not in checklist   # design/47 12.3
    assert 'one cue per narrated sentence' in _storage().get(gen['OPEN-EDIT.md']).decode('utf-8')
    # D17: final before the Resolve step is refused, naming what is missing
    rc, out, _ = vw(home, 'delivery', 'final', '--quote', 'yes')
    assert rc == 2 and any('Resolve report' in m for m in out['missing'])
    # D13/D20 (fake Resolve): run once, twice refused, report verified
    home['env']['VW2_RESOLVE_FAKE'] = '1'
    rc, out, err = vw(home, 'delivery', 'resolve', '--check')
    assert rc == 0 and out['preflight']['resolve'] == 'fake', (out, err)
    rc, out, _ = vw(home, 'delivery', 'resolve', '--run')
    assert rc == 2 and 'authorization' in out['message']
    rc, out, err = vw(home, 'delivery', 'resolve', '--run', '--authorization', 'yes build the Resolve timeline')
    assert rc == 0 and out['ledger']['state'] == 'reported' and out['ledger']['report']['drt_verified'] is True and out['differences'] == [], (out, err)
    assert (ws / 'out' / 'delivery' / 'Approved-timeline.drt').exists()
    rc, out, _ = vw(home, 'delivery', 'resolve', '--run', '--authorization', 'again')
    assert rc == 2 and 'already reported' in out['message']
    # D17: final needs the five words
    rc, out, _ = vw(home, 'delivery', 'final', '--quote', 'yes I watched and listened')
    assert rc == 2 and any('subtitles' in m for m in out['missing'])
    rc, out, err = vw(home, 'delivery', 'final', '--quote', 'yes: watched, listened, read the subtitles, the timeline DRT is verified, the package is complete')
    assert rc == 0 and out['files'] >= 7, (out, err)
    assert vw(home, 'next')[1]['stage'] is None
    # D18: close with retention: final package, narration, visuals kept; originals and films gone
    run_id = json.loads((ws / 'manifest.json').read_text())['run_id']
    from app.storage import storage
    st = storage()
    before = st.list(run_id)
    assert any('/media/' in k for k in before) and any('review-v' in k for k in before)
    keep = os.environ.get('VW2_TEST_KEEP')
    if keep:   # snapshot every stage's files before close deletes the intermediates (for a human to browse)
        import shutil
        dest = Path(keep)
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(ws, dest / 'run-folder')
        shutil.copytree(Path(os.environ['VW2_STORAGE_LOCAL_DIR']) / run_id, dest / 'server-storage')
        with psycopg.connect(database) as c:
            from psycopg.rows import dict_row
            c.row_factory = dict_row
            rows = c.execute("select stage, unit, summary, files, accepted_quote, created_at from vw2_stage_outputs where run_id=%s and not stale order by created_at", (run_id,)).fetchall()
            (dest / 'stage-outputs.json').write_text(json.dumps(rows, indent=1, default=str), encoding='utf-8')
            jobs_ = c.execute("select stage, unit, provider, status, cost, created_at from vw2_jobs where run_id=%s order by created_at", (run_id,)).fetchall()
            (dest / 'jobs.json').write_text(json.dumps(jobs_, indent=1, default=str), encoding='utf-8')
    rc, out, err = vw(home, 'close')
    assert rc == 0 and out['retention']['deleted'] > 0, (out, err)
    after = st.list(run_id)
    used = {f['name'].split('/')[-1] for f in manifest['files'] if f['role'] == 'original'}
    assert used and all(f'/media/{n}' in '|'.join(after) for n in used)            # originals the package references stay (the editor opens them in Resolve)
    unused = {'c0.mp4', 'c1.mp4', 'c2.mp4'} - used
    assert unused and not any(f'/media/{n}' in k for n in unused for k in after)   # originals the film does not use are deleted
    assert not any('review-v' in k or 'first-cut' in k or '/frames/' in k or 'session.json' in k for k in after)   # review film, frames, sessions gone
    assert any('assembly-v' in k and k.endswith('.mp4') for k in after) and any('/voice/' in k for k in after) and any('/visuals/' in k for k in after)
    with psycopg.connect(database) as c:
        assert c.execute("select status from vw2_runs where id=%s", (run_id,)).fetchone()[0] == 'closed'


def test_srt_and_checklist_shapes():
    beats = [{'beat_id': 'BEAT_01', 'text': 'One.', 'narration_first_word_s': 0.12, 'narration_last_word_s': 1.5}, {'beat_id': 'BEAT_02', 'text': 'Two.', 'narration_first_word_s': 1.8, 'narration_last_word_s': 2.4}]
    srt = D.srt_of(beats)
    assert srt.startswith('1\n00:00:00,120 --> 00:00:01,500\nOne.\n\n2\n00:00:01,800 --> 00:00:02,400\nTwo.')
    pk = {'sub_clips': [{'sub_clip_id': 'a', 'color_group': 'GRP_X', 'clip_name': 'c.mp4', 'log_sub_clip_id': 'SUB_01', 'in_frame': 0, 'out_frame': 10, 'grade': 'A', 'eligibility': 'ELIGIBLE_AS_IS', 'process_stage': 'S1', 'effective_shot_size': 'WS', 'primary_fits': ['BEAT_01']}],
          'cards': [{'clip_id': 'c', 'clip_name': 'c.mp4', 'lines': ['OVERVIEW: x']}], 'sfx_cues_flat': [{'sfx_type': 'birds', 'description': 'distant', 'start_tc': '00:00:01:00'}]}
    items = D.checklist_of({'finishing': [{'item': 'Stabilise a', 'timeline_in_frame': 3}]}, pk, {})
    text = json.dumps(items, ensure_ascii=False)
    assert 'Stabilise a' in text and 'birds' in text and 'GRP_X' in text and 'A4' in text and '14 LUFS' in text
    csv_text = D.media_pool_csv(pk)
    assert csv_text.splitlines()[0].startswith('File Name,Scene,Shot') and 'c.mp4,S1,c,1,1' in csv_text and 'GRP_X' in csv_text


def test_scenes_and_pause_through_assembly_delivery_and_resolve(home, database, fake, gemini):
    code, ws, pk = run_until_assembly(home, database, fake, gemini, scenes=True)
    nar = pk['narration']
    cut, total = nar['cuts'][0], nar['total_frames']
    assert vw(home, 'assembly', 'prepare')[0] == 0
    assert vw(home, 'assembly', 'choose', '--shot', 'VS2', '--offset', '0', '--end', 'hold_last')[0] == 0
    assert vw(home, 'assembly', 'build')[0] == 0
    assert vw(home, 'assembly', 'render')[0] == 0
    drain()
    rc, out, err = vw(home, 'assembly', 'fetch')
    assert rc == 0 and abs(out['duration_s'] - total / 25) < 0.15, (out, err)   # the pause is in the approved film
    film = ws / 'out' / 'assembly.mp4'
    assert any(abs(s - cut['source_cut_frame'] / 25) < 0.1 and abs(d - cut['inserted_frames'] / 25) < 0.1 for s, d in silences_in(film)), silences_in(film)
    assert vw(home, 'assembly', 'review', '--decision', 'accepted', '--notes', 'good', '--quote', 'yes, watched it and listened to it')[0] == 0
    assert vw(home, 'assembly', 'record', '--quote', 'yes assembly')[0] == 0
    rc, out, err = vw(home, 'delivery', 'bundle')
    assert rc == 0, (out, err)
    manifest = json.loads((ws / 'work' / 'manifest.json').read_text(encoding='utf-8'))
    pieces = manifest['narration_pieces']
    assert [(p['source_in_frame'], p['source_out_frame'], p['record_in_frame']) for p in pieces] == \
        [(q['source_start_frame'], q['source_end_frame'], q['timeline_start_frame']) for q in nar['pieces']] and len(pieces) == 2
    home['env']['VW2_RESOLVE_FAKE'] = '1'
    rc, out, err = vw(home, 'delivery', 'resolve', '--run', '--authorization', 'yes build the Resolve timeline')
    assert rc == 0 and out['differences'] == [] and out['ledger']['report']['drt_verified'] is True, (out, err)
    from app.storage import storage
    srt = storage().get(next(f['key'] for f in manifest['files'] if f['name'] == 'Subtitles.srt')).decode('utf-8')
    second = nar['sentences'][1]
    assert srt.count(' --> ') == 2 and D.srt_time(second['start_frame'] / 25) + ' --> ' in srt   # one cue per sentence, shifted by the pause
    drt = (ws / 'out' / 'delivery' / 'Approved-timeline.drt').read_text(encoding='utf-8')
    assert drt.count('<audio><track>') == 1 and drt.split('<audio><track>')[1].count('<clipitem>') == 2   # narration as two whole-frame pieces


def test_srt_per_sentence_shifted():
    sentences = [{'text': 'One.', 'start_frame': 3, 'end_frame': 30}, {'text': 'Two.', 'start_frame': 55, 'end_frame': 70}]
    srt = D.srt_of([], sentences, 25)
    assert srt.startswith('1\n00:00:00,120 --> 00:00:01,200\nOne.\n\n2\n00:00:02,200 --> 00:00:02,800\nTwo.')
