"""Stage 3 (assembly → delivery → Resolve once → final → close with retention), design/16 + 17. Resolve is the fake adapter; FFmpeg is real."""
import json
import os
import subprocess

import psycopg
import pytest

from app.stage3 import delivery as D
from conftest import vw
from test_analysis import FakeTransport, gemini  # noqa: F401
from test_stage2 import author, run_until_options
from test_visuals import png_bytes, scene, shot, vplan
from test_voice_media import drain, fake  # noqa: F401


def run_until_assembly(home, database, fake, gemini):
    """Through options, master, first cut, and the visuals gap BEAT_02 filled with a still asset."""
    code, ws, pk = run_until_options(home, database, fake, gemini)
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
    assert vw(home, 'master', 'record', '--quote', 'yes master')[0] == 0
    rc, out, err = vw(home, 'first-cut', 'record', '--quote', 'yes, watched and listened')
    assert rc == 0, (out, err)
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
    # D10: acceptance without watched + listened
    rc, out, _ = vw(home, 'assembly', 'review', '--decision', 'accepted', '--notes', 'good', '--quote', 'yes')
    assert rc == 2 and 'listened' in out['message']
    rc, out, _ = vw(home, 'assembly', 'review', '--decision', 'changes', '--notes', 'hold the wall longer', '--frame-note', '40:too short', '--quote', 'change it')
    assert rc == 0 and out['frame_notes'][0]['frame'] == 40
    assert vw(home, 'assembly', 'build')[0] == 0   # a new version after changes
    assert vw(home, 'assembly', 'render')[0] == 0
    drain()
    assert vw(home, 'assembly', 'review', '--decision', 'accepted', '--notes', 'good', '--quote', 'yes, watched it and listened to it')[0] == 0
    rc, out, err = vw(home, 'assembly', 'record', '--quote', 'yes assembly')
    assert rc == 0, (out, err)
    assert vw(home, 'next')[1]['stage'] == 'delivery'
    # D12: bundle manifest lists every file with hashes; D15/D16 SRT and checklist
    rc, out, err = vw(home, 'delivery', 'bundle')
    assert rc == 0 and out['files'] >= 8, (out, err)
    manifest = json.loads((ws / 'work' / 'manifest.json').read_text(encoding='utf-8'))
    roles = {f['role'] for f in manifest['files']}
    assert {'approved_film', 'narration', 'original', 'normalised', 'plan', 'generated'} <= roles and all(len(f['sha256']) == 64 for f in manifest['files'])
    names = {f['name'] for f in manifest['files']}
    assert {'Subtitles.srt', 'Finishing-checklist.md', 'Media-pool.csv', 'OPEN-EDIT.md', 'Approved-film.mp4'} <= names
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
