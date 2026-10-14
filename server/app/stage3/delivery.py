"""Delivery: bundle with manifest (approved film, narration, originals, normalised fills, plans), SRT, finishing checklist, media-pool CSV;
the Resolve ledger (reserve → dispatched → reported → closed, never replayed); final approval on five points; retention on close."""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from fractions import Fraction

from .. import core, jobs
from ..errors import Problem
from ..stage2 import stage as S2
from . import CONTRACT_BUNDLE
from .assembly import key, session_of, save_session, fail

FINAL_WORDS = {'watched': ('watch',), 'listened': ('listen',), 'subtitles read': ('srt', 'subtitle'), 'timeline verified': ('drt', 'timeline'), 'package complete': ('package', 'bundle')}


def srt_time(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def srt_of(beats):
    """One cue per beat from the narration's measured first and last word (design/17 A15)."""
    lines = []
    for i, b in enumerate(beats, 1):
        lines += [str(i), f"{srt_time(b['narration_first_word_s'])} --> {srt_time(b['narration_last_word_s'])}", b['text'].strip(), '']
    return '\n'.join(lines) + '\n'


def checklist_of(assembly_summary, pk, master_summary):
    items = [{'where': f"frame {i.get('timeline_in_frame', 0)}", 'item': i['item']} for i in assembly_summary.get('finishing') or []]
    for c in pk.get('sfx_cues_flat') or []:
        items.append({'where': c.get('start_tc', ''), 'item': f"A3 SFX to source: {c.get('sfx_type')} — {c.get('description')}"})
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    groups = sorted({r['color_group'] for r in rows.values() if r.get('color_group')})
    items += [{'where': 'Fairlight', 'item': 'A2 nat-sound pieces are placed at unity in the timeline; the film used 4-frame fades and −27 dBFS peaks (API cannot set fades); match if re-rendering'},
              {'where': 'Fairlight bus', 'item': 'Master limiter: −14 LUFS integrated, −1 dBTP true-peak ceiling'},
              {'where': 'Deliver page', 'item': 'Subtitles: burn in or deliver the SRT alongside (SRT is in the package)'},
              {'where': 'Color page', 'item': 'Colour groups from the logs: ' + (', '.join(groups) if groups else 'none')},
              {'where': 'A4', 'item': 'Add background music on A4, ducked −28 to −32 dBFS under narration, swells to −18 dBFS in pauses (none in v2)'}]
    return items


def media_pool_csv(pk):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['File Name', 'Scene', 'Shot', 'Take', 'Good Take', 'Description', 'Comments', 'Keywords'])
    by_clip = {}
    for r in pk['sub_clips']:
        by_clip.setdefault(r['clip_name'], []).append(r)
    for card in pk['cards']:
        subs = by_clip.get(card['clip_name'], [])
        stage = next((s['process_stage'] for s in subs if s.get('process_stage')), '')
        comments = '; '.join(f"{s['log_sub_clip_id']} (f{s['in_frame']}-{s['out_frame']}) {s['grade']} {s['eligibility']}" for s in subs)
        keywords = sorted({k for s in subs for k in ([stage, s['effective_shot_size'], 'Grade_' + s['grade'], s.get('color_group') or ''] + s['primary_fits']) if k})
        w.writerow([card['clip_name'], stage, card['clip_id'], 1, 1 if any(s['grade'] in ('A', 'B') for s in subs) else 0, (card['lines'] or [''])[0][:200], comments, ','.join(keywords)])
    return buf.getvalue()


def bundle(conn, store, user, run, outputs):
    session = session_of(store, run)
    asm_o = S2._output(outputs, 'assembly')
    master_o = S2._output(outputs, 'master')
    voice_o = S2._output(outputs, 'voice')
    media_o = S2._output(outputs, 'media')
    s2 = S2.session_of(store, run)
    pk = S2._package(store, s2)
    assembly, _ = S2._file(store, asm_o, f"assembly-v{asm_o['summary']['version']}.json")
    master, _ = S2._file(store, master_o, f"master-v{master_o['summary']['version']}.json")
    film = next(f for f in asm_o['files'] if f['name'] == 'assembly.mp4')
    files = [{'role': 'approved_film', 'name': 'Approved-film.mp4', **{k: film[k] for k in ('key', 'sha256', 'bytes')}}]
    for f in voice_o['files']:
        if f['name'] in ('narration.mp3', 'timing.json'):
            files.append({'role': 'narration', 'name': 'Audio/' + f['name'], **{k: f[k] for k in ('key', 'sha256', 'bytes')}})
    used_clips = {}
    for ev in assembly['events']:
        if ev['kind'] == 'event':
            row = next(r for r in pk['sub_clips'] if r['sub_clip_id'] == ev['sub_clip_id'])
            used_clips[row['clip_id']] = row['clip_name']
    clips = {c['id']: c for c in media_o['summary']['clips']}
    for cid, name in used_clips.items():
        c = clips[cid]
        files.append({'role': 'original', 'name': 'Media/Originals/' + name, 'key': f"{run['id']}/media/{name}", 'sha256': c['sha256'], 'bytes': c['bytes']})
    for f in asm_o['files']:
        if f['name'].startswith('normalised/'):
            files.append({'role': 'normalised', 'name': 'Media/Normalised/' + f['name'].split('/', 1)[1], **{k: f[k] for k in ('key', 'sha256', 'bytes')}})
    for o, name in ((master_o, f"master-v{master_o['summary']['version']}.json"), (asm_o, f"assembly-v{asm_o['summary']['version']}.json")):
        f = next(x for x in o['files'] if x['name'] == name)
        files.append({'role': 'plan', 'name': 'Plans/' + name, **{k: f[k] for k in ('key', 'sha256', 'bytes')}})
    files.append({'role': 'plan', 'name': 'Plans/options-package.json', **{k: s2['package'][k] for k in ('key', 'sha256', 'bytes')}})
    srt = srt_of(pk['beats']).encode('utf-8')
    pk_flat = {**pk, 'sfx_cues_flat': assembly.get('sfx_cues') or []}
    checklist = checklist_of(asm_o['summary'], pk_flat, master_o['summary'])
    md = '# Human finishing checklist\n\n' + '\n'.join(f"- [{i['where']}] {i['item']}" for i in checklist) + '\n'
    csv_text = media_pool_csv(pk).encode('utf-8')
    open_edit = (f"# OPEN-EDIT\n\nRun {run['code']} — client {run.get('client')}.\n\n1. Open Approved-timeline.drt in DaVinci Resolve 21.1.1 (File > Import > Timeline) with Media/ next to it.\n"
                 "2. Approved-film.mp4 is the film the operator approved; the timeline reproduces its cuts, crops and zooms. A2 fades are listed in the checklist.\n"
                 "3. Subtitles.srt matches the narration beats. Finishing-checklist.md lists everything the API could not do.\n").encode('utf-8')
    generated = {'Subtitles.srt': (srt, 'text/plain'), 'Finishing-checklist.md': (md.encode('utf-8'), 'text/markdown'), 'Finishing-checklist.json': (json.dumps(checklist, ensure_ascii=False, indent=1).encode('utf-8'), 'application/json'),
                 'Media-pool.csv': (csv_text, 'text/csv'), 'OPEN-EDIT.md': (open_edit, 'text/markdown')}
    for name, (data, mime) in generated.items():
        k = key(run, 'delivery/' + name)
        store.put(k, data, mime)
        files.append({'role': 'generated', 'name': name, 'key': k, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    manifest = {'contract': CONTRACT_BUNDLE, 'run': run['code'], 'client': run.get('client'), 'created_at': datetime.now(timezone.utc).isoformat(), 'film_sha256': film['sha256'],
                'assembly_digest': asm_o['summary']['assembly_digest'], 'timeline': pk['timeline'], 'files': files, 'resolve_events': resolve_events(assembly, pk, master)}
    mk = S2.save_json(store, key(run, 'delivery/manifest.json'), manifest)
    for f in files + [{'name': 'manifest.json', **mk}]:
        jobs.record_file(conn, run['id'], 'delivery', f['key'], f['name'], f['sha256'], f['bytes'], 'application/octet-stream')
    session['bundle'] = {'manifest': mk, 'film_sha256': film['sha256'], 'files': len(files), 'bytes': sum(f['bytes'] for f in files)}
    session['resolve'] = None if (session.get('resolve') or {}).get('film_sha256') != film['sha256'] else session['resolve']
    save_session(store, run, session)
    return {'manifest': mk, 'files': len(files), 'bytes': session['bundle']['bytes'], 'next': 'on the Mac: `vw pull <code>` then `vw delivery resolve --check`, then `--run --authorization "<operator words>"`'}


def resolve_events(assembly, pk, master):
    """What the Resolve timeline must contain: per event the file, source in/out, record in/out, zoom/pan/tilt/rotation, marker, colour group."""
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    out = []
    for ev in assembly['events']:
        if ev['kind'] == 'event':
            r = rows[ev['sub_clip_id']]
            crop = ev.get('crop') in ('solver', 'hands_only') and r.get('zoom')
            if ev.get('stabilize'):   # the stabilised render is the source; crop and zoom are already applied in it
                out.append({'file': f"Media/Normalised/{ev['sub_clip_id'].replace(':', '-')}-{ev['timeline_in_frame']}.mp4", 'source_in_frame': 0, 'source_out_frame': ev['timeline_frames'],
                            'record_in_frame': ev['timeline_in_frame'], 'record_out_frame': ev['timeline_out_frame'], 'source_fps': str(pk['timeline']['fps']), 'zoom': 1.0, 'pan': 0.0, 'tilt': 0.0,
                            'rotation': 0.0, 'color_group': r.get('color_group'), 'marker': {'name': ev['sub_clip_id'], 'note': f"option #{ev.get('approved_from_option')}, stabilised copy", 'colour': 'Blue'},
                            'a2': ev.get('a2_intervals') or [], 'stabilized': True})
                continue
            out.append({'file': 'Media/Originals/' + r['clip_name'], 'source_in_frame': ev['source_in_frame'], 'source_out_frame': ev['source_out_frame'],
                        'record_in_frame': ev['timeline_in_frame'], 'record_out_frame': ev['timeline_out_frame'], 'source_fps': r['source_fps'],
                        'zoom': r['zoom'] if crop else 1.0, 'pan': (r['position'] or [0, 0])[0] if crop else 0.0, 'tilt': (r['position'] or [0, 0])[1] if crop else 0.0,
                        'rotation': r.get('horizon_rotation_deg') or 0.0, 'color_group': r.get('color_group'), 'marker': {'name': ev['sub_clip_id'], 'note': f"option #{ev.get('approved_from_option')}", 'colour': 'Blue'},
                        'a2': ev.get('a2_intervals') or [], 'stabilized': False})
        else:
            out.append({'file': 'Media/Normalised/' + ev['shot_id'] + '.mp4', 'source_in_frame': 0, 'source_out_frame': ev['timeline_frames'], 'record_in_frame': ev['timeline_in_frame'],
                        'record_out_frame': ev['timeline_out_frame'], 'source_fps': str(pk['timeline']['fps']), 'zoom': 1.0, 'pan': 0.0, 'tilt': 0.0, 'rotation': 0.0, 'color_group': None,
                        'marker': {'name': ev['shot_id'], 'note': 'visuals fill', 'colour': 'Green'}, 'a2': [], 'stabilized': False})
    return out


# ---------- Resolve ledger (reserve → dispatched → reported → closed) ----------

def resolve_reserve(store, user, run, machine, authorization):
    session = session_of(store, run)
    if not session.get('bundle'):
        raise Problem(409, 'NOT_ALLOWED', 'Build the bundle first (`vw delivery bundle`).')
    led = session.get('resolve')
    if led and led.get('state') in ('reserved', 'dispatched', 'reported') and led.get('film_sha256') == session['bundle']['film_sha256']:
        raise Problem(409, 'NOT_ALLOWED', f"The Resolve step is already {led['state']} on {led.get('machine')}; inspect or close it, never replay.", state=led['state'])
    if not str(authorization or '').strip():
        fail('The operator\'s words permitting the Resolve timeline are required (--authorization).')
    session['resolve'] = {'state': 'reserved', 'machine': machine, 'authorization': authorization, 'film_sha256': session['bundle']['film_sha256'], 'reserved_at': datetime.now(timezone.utc).isoformat(), 'by': user['id']}
    save_session(store, run, session)
    return session['resolve']


def resolve_mark(store, user, run, state, machine, report=None, note=None):
    session = session_of(store, run)
    led = session.get('resolve')
    if not led:
        raise Problem(409, 'NOT_ALLOWED', 'Nothing reserved.')
    allowed = {'dispatched': ('reserved',), 'reported': ('dispatched',), 'closed': ('dispatched', 'reported', 'reserved')}
    if led['state'] not in allowed.get(state, ()):
        raise Problem(409, 'NOT_ALLOWED', f"Cannot move {led['state']} → {state}.")
    if led.get('machine') != machine and state != 'closed':
        raise Problem(409, 'NOT_ALLOWED', f"Reserved by {led.get('machine')}, not this machine.")
    led['state'] = state
    led[f'{state}_at'] = datetime.now(timezone.utc).isoformat()
    if report is not None:
        led['report'] = report
    if note:
        led['note'] = note
    save_session(store, run, session)
    return led


def final(conn, store, user, run, outputs, quote):
    session = session_of(store, run)
    asm_o = S2._output(outputs, 'assembly')
    film = next(f for f in asm_o['files'] if f['name'] == 'assembly.mp4')
    b = session.get('bundle')
    led = session.get('resolve') or {}
    missing = []
    if not b or b['film_sha256'] != film['sha256']:
        missing.append('bundle for the current assembly film')
    if led.get('state') != 'reported' or led.get('film_sha256') != film['sha256']:
        missing.append('Resolve report for this film')
    elif not (led.get('report') or {}).get('drt_verified'):
        missing.append('DRT reopened and verified (the report says it was not)')
    if any(o.get('stale') for o in outputs):
        missing.append('no stale stage outputs')
    q = (quote or '').lower()
    for label, words in FINAL_WORDS.items():
        if not any(w in q for w in words):
            missing.append(f"operator's words for: {label}")
    if missing:
        raise Problem(409, 'NOT_ALLOWED', 'Final approval is not possible yet: ' + '; '.join(missing), missing=missing)
    manifest = S2.load_json(store, b['manifest']['key'])
    rep = led['report']
    files = [{'name': 'Approved-film.mp4', 'key': film['key'], 'sha256': film['sha256'], 'bytes': film['bytes'], 'location': 'storage', 'receipt': True},
             {'name': 'manifest.json', **{k: b['manifest'][k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True}]
    for f in manifest['files']:   # the whole package is the delivery record, so retention keeps it (originals the timeline references included)
        if f['key'] not in {x['key'] for x in files}:
            files.append({'name': f['name'], **{k: f[k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True})
    for name in ('drt', 'report'):
        ref = rep.get(name)
        if ref:
            files.append({'name': 'Approved-timeline.drt' if name == 'drt' else 'resolve-report.json', **{k: ref[k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True})
    for f in files:
        jobs.record_file(conn, run['id'], 'delivery', f['key'], f['name'], f['sha256'], f['bytes'], 'application/octet-stream')
    summary = {'film_sha256': film['sha256'], 'manifest_sha256': b['manifest']['sha256'], 'resolve': {k: led.get(k) for k in ('machine', 'authorization', 'reported_at')},
               'readback': rep.get('readback'), 'drt_verified': rep.get('drt_verified'), 'differences': rep.get('differences') or [], 'checks': list(FINAL_WORDS)}
    out = core.output(conn, user, run, {'stage': 'delivery', 'files': files, 'accepted_quote': quote, 'summary': summary})
    led['state'] = 'closed'
    session['final'] = {'output': str(out['id']), 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    return {'output': str(out['id']), 'files': len(files), 'next': '`vw close`'}


KEEP_STAGES = ('delivery', 'voice', 'visuals')


def retention(conn, store, run, outputs):
    """Plan §1 decision 4: keep the final film and package, approved narration, approved images and takes, and every stage-output record (JSON);
    delete everything else under the run (originals, review/master/assembly films, sessions, frames, normalised copies, inspections)."""
    keep = set()
    for o in outputs:
        for f in o['files']:
            if o['stage'] in KEEP_STAGES or str(f.get('name', '')).endswith('.json'):
                keep.add(f['key'])
    everything = store.list(str(run['id']))
    doomed = [k for k in everything if k not in keep]
    store.delete(doomed)
    conn.execute("delete from vw2_files where run_id=%s and key = any(%s)", (run['id'], doomed))
    return {'kept': len(keep), 'deleted': len(doomed)}
