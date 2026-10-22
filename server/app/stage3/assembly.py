"""Assembly: the master plan plus one fill per gap shot (take or asset), per-shot choices (offset, end policy, stabilise, accept-as-is),
normalisation at render, A1 untouched, A2 band, A3 as a list, no A4. Session at {run}/stage3/session.json."""
import hashlib
import json
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from psycopg.types.json import Jsonb

from .. import core, jobs
from ..errors import Problem
from ..stage2 import stage as S2
from . import CONTRACT_ASSEMBLY, STABILIZE_ZOOM

MAX_ZOOM_1080 = 1.35
DISSOLVE_FRAMES = 6   # design/71 P4: the cross-fade where two takes of one gap share their boundary picture


def dissolves(fills, choices):
    """design/71 P4: per fill, the frames it dissolves into the next fill of its gap: six when the first take's end image is the second's
    start image and the first has that much spare tail after its offset and slot; else nought (a cut, as today)."""
    out = {sid: 0 for sid in fills}
    by_gap = {}
    for sid, f in fills.items():
        by_gap.setdefault(f['gap_id'], []).append((sid, f))
    for shots in by_gap.values():
        shots.sort(key=lambda x: x[1]['placement']['start_frame'])
        for (sid, a), (_, b) in zip(shots, shots[1:]):
            ba, bb = a.get('boundary') or {}, b.get('boundary') or {}
            if not ba.get('end_image') or ba['end_image'] != bb.get('start_image'):
                continue
            if a['meta']['kind'] != 'movie' or b['meta']['kind'] != 'movie' or a.get('available_frames') is None:
                continue
            c = choices.get(sid) or {}
            if c.get('end_policy') == 'hold_last':
                continue
            if a['available_frames'] - int(c.get('offset_frames') or 0) - a['slot_frames'] >= DISSOLVE_FRAMES:
                out[sid] = DISSOLVE_FRAMES
    return out


def fail(message):
    raise Problem(422, 'ASSEMBLY_CONTRACT', str(message))


def key(run, name):
    return f"{run['id']}/stage3/{name}"


def session_of(store, run, create=False):
    try:
        return S2.load_json(store, key(run, 'session.json'))
    except Problem:
        if not create:
            raise Problem(409, 'NOT_ALLOWED', 'Run `vw assembly prepare` first.')
    return {'contract': 'vw2-stage3-session-v1', 'fills': {}, 'choices': {}, 'stabilize': {}, 'versions': [], 'current': None, 'renders': {}, 'reviews': [], 'recorded': {},
            'bundle': None, 'resolve': None, 'final': None}


def save_session(store, run, session):
    session['updated_at'] = datetime.now(timezone.utc).isoformat()
    S2.save_json(store, key(run, 'session.json'), session)
    return session


def fill_file(files, shot, name, visuals_assets):
    """A gap's file for one shot, by name. Ticket 12: gaps recorded before 16 Oct dropped a second shot's entry when two shots shared one
    file; the shot's asset in the visuals record names that file, and it is used only if the gap's recorded output holds the same
    stored file with the same fingerprint."""
    ref = next((f for f in files if f['name'] == name), None)
    if ref or shot['source'] != 'asset':
        return ref
    asset = visuals_assets.get(shot['shot_id']) or {}
    same = next((f for f in files if f['key'] == asset.get('key') and f['sha256'] == asset.get('sha256')), None)
    return {**same, 'name': name} if same else None


def probe_file(store, k, name):
    with tempfile.TemporaryDirectory(prefix='vw2-probe-') as folder:
        p = Path(folder) / (name or 'x.mp4')
        p.write_bytes(store.get(k))
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(p)], capture_output=True, check=True, timeout=120).stdout
    data = json.loads(out)
    v = next((s for s in data['streams'] if s.get('codec_type') == 'video'), None)
    if not v:
        fail(f'{name} has no video stream.')
    rotation = next((int(sd['rotation']) for sd in v.get('side_data_list') or [] if 'rotation' in sd), 0) % 360
    return {'duration_s': float(data['format'].get('duration') or 0), 'fps': v.get('avg_frame_rate'), 'width': v.get('width'), 'height': v.get('height'),
            'color_transfer': v.get('color_transfer'), 'color_primaries': v.get('color_primaries'), 'rotation_deg': rotation,
            'issues': ([] if v.get('color_transfer') and v.get('color_primaries') else ['colour untagged']) + (['rotation metadata'] if rotation else [])}


def prepare(conn, store, user, run, outputs):
    """Collect the master plan and every gap's selected take or asset; probe each fill; default choices."""
    master_o = S2._output(outputs, 'master')
    plan, _ = S2._file(store, master_o, f"master-v{master_o['summary']['version']}.json")
    s2 = S2.session_of(store, run)
    pk = S2._package(store, s2)
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    session = session_of(store, run, create=True)
    fills = {}
    found = []   # ticket 12: find every fill's file before probing any, so a missing file fails in seconds, not after the downloads
    visuals_assets = None
    for g in plan['gaps']:
        vo = next((o for o in outputs if o['stage'] == 'visuals' and o['unit'] == g['shot_id']), None)
        if not vo:
            raise Problem(409, 'NOT_ALLOWED', f"Gap {g['shot_id']} has no recorded visuals output.")
        for shot in vo['summary']['shots']:
            if shot.get('kind') == 'sequence':   # design/65 B8: one file per state; the fill carries them all
                names = [st['name'] for st in shot['media']['states']]
                refs = [next((f for f in vo['files'] if f['name'] == n), None) for n in names]
                if not all(refs):
                    fail(f"Visuals output for {g['shot_id']} lacks a state file of {shot['shot_id']}: " + ', '.join(n for n, r in zip(names, refs) if not r))
                found.append((g, shot, names[0], {**refs[0], 'states': [{'file': {k: r[k] for k in ('name', 'key', 'sha256', 'bytes')}, 'hold_frames': st['hold_frames']} for r, st in zip(refs, shot['media']['states'])]}))
                continue
            name = f"{shot['shot_id']}.mp4" if shot['source'] == 'take' else f"{shot['shot_id']}-asset{'.mp4' if shot.get('kind') == 'movie' else '.png'}"
            if shot['source'] == 'asset' and visuals_assets is None and not any(f['name'] == name for f in vo['files']):
                try:
                    visuals_assets = S2.load_json(store, f"{run['id']}/visuals/session.json").get('assets') or {}
                except Problem:
                    visuals_assets = {}
            ref = fill_file(vo['files'], shot, name, visuals_assets or {})
            if not ref:
                fail(f"Visuals output for {g['shot_id']} lacks the file {name}.")
            found.append((g, shot, name, ref))
    for g, shot, name, ref in found:
        placement = shot['placement']
        slot = placement['end_frame'] - placement['start_frame']
        if ref.get('states'):   # design/65 B8: a graphic sequence
            meta = {'kind': 'sequence', 'duration_s': None, 'fps': None, 'issues': [], 'states': ref['states'],
                    'dissolve_frames': shot['media'].get('dissolve_frames') or 0, 'motion': shot['media'].get('motion') or 'none'}
        elif ref['name'].endswith('.png'):
            meta = {'kind': 'still', 'duration_s': None, 'fps': None, 'issues': []}
        elif shot.get('media') and shot['media'].get('kind') == 'movie' and shot['media'].get('duration_s'):   # design/46 11.2: measured when the take was retained
            meta = {**shot['media'], 'issues': shot['media'].get('issues') or []}
        else:
            meta = {'kind': 'movie', **probe_file(store, ref['key'], ref['name'])}
        avail = int(Fraction(str(meta['duration_s'] or 0)) * Fraction(str(pk['timeline']['fps']))) if meta.get('duration_s') else None
        fills[shot['shot_id']] = {'gap_id': g['shot_id'], 'file': {k: ref[k] for k in ('name', 'key', 'sha256', 'bytes')}, 'placement': placement, 'slot_frames': slot, 'meta': meta,
                                  'available_frames': avail, 'default': {'offset_frames': 0, 'end_policy': 'trim' if (avail or 0) >= slot else 'hold_last'},
                                  **({'boundary': shot['boundary']} if shot.get('boundary') else {})}   # design/71 P4
        session['choices'].setdefault(shot['shot_id'], {**fills[shot['shot_id']]['default'], 'accept_as_is': False})
    session['fills'] = fills
    joins = dissolves(fills, session['choices'])
    session['stabilize'] = {ev['sub_clip_id']: session['stabilize'].get(ev['sub_clip_id'], {'flagged': bool(rows[ev['sub_clip_id']].get('stabilization_needed')), 'choice': 'leave'})
                            for ev in plan['events'] if ev['kind'] == 'event'}
    session['master'] = {'output': str(master_o['id']), 'version': master_o['summary']['version'], 'digest': master_o['summary']['plan_digest']}
    save_session(store, run, session)
    flagged = [k for k, v in session['stabilize'].items() if v['flagged']]
    issues = {k: f['meta']['issues'] for k, f in fills.items() if f['meta']['issues']}
    return {'gaps': len(plan['gaps']), 'fills': {k: {'slot_frames': f['slot_frames'], 'available_frames': f['available_frames'], 'default': f['default'], 'issues': f['meta']['issues'],
                                                  'dissolve_into_next': joins[k]} for k, f in fills.items()},
            'stabilization_flagged': flagged, 'issues': issues, 'next': 'ask the operator per fill (offset, end policy) and per flagged shot (leave / stabilise / swap), then `vw assembly build`'}


def choose(store, user, run, shot_id, offset, end_policy, accept_as_is):
    session = session_of(store, run)
    f = session['fills'].get(shot_id)
    if not f:
        fail(f'No gap fill {shot_id}.')
    if end_policy not in ('trim', 'hold_last'):
        fail('end_policy is trim or hold_last')
    if f['meta']['kind'] == 'movie':
        if offset < 0 or (f['available_frames'] is not None and offset >= f['available_frames']):
            fail(f"offset must be inside the take (0–{f['available_frames'] - 1} frames)")
        if end_policy == 'trim' and f['available_frames'] is not None and f['available_frames'] - offset < f['slot_frames']:
            fail(f"the take has {f['available_frames'] - offset} frames after the offset but the slot needs {f['slot_frames']}: use hold_last or a smaller offset")
    if f['meta']['issues'] and not accept_as_is:
        fail(f"{shot_id} has issues {f['meta']['issues']}; pass --accept-as-is to use it anyway, or swap it in visuals")
    session['choices'][shot_id] = {'offset_frames': int(offset), 'end_policy': end_policy, 'accept_as_is': bool(accept_as_is), 'by': user['id']}
    session['current'] = None
    save_session(store, run, session)
    return session['choices'][shot_id]


def stabilize(store, user, run, sub_clip_id, choice):
    session = session_of(store, run)
    st = session['stabilize'].get(sub_clip_id)
    if st is None:
        fail(f'{sub_clip_id} is not in the master.')
    if choice not in ('leave', 'ffmpeg'):
        fail('choice is leave or ffmpeg (swap a shot in the master stage)')
    st['choice'] = choice
    session['current'] = None
    save_session(store, run, session)
    return st


def build(conn, store, user, run, outputs):
    """The assembly plan: master events (with stabilisation decisions within the zoom cap) and gap fills with their choices."""
    session = session_of(store, run)
    master_o = S2._output(outputs, 'master')
    plan, _ = S2._file(store, master_o, f"master-v{master_o['summary']['version']}.json")
    s2 = S2.session_of(store, run)
    pk = S2._package(store, s2)
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    tl = pk['timeline']
    events, checklist = [], []
    fills_by_gap = {}
    joins = dissolves(session['fills'], session['choices'])   # design/71 P4
    for sid, f in session['fills'].items():
        fills_by_gap.setdefault(f['gap_id'], []).append((sid, f))
    for ev in plan['events']:
        if ev['kind'] == 'event':
            row = rows[ev['sub_clip_id']]
            stab = session['stabilize'].get(ev['sub_clip_id']) or {}
            zoom = (row.get('zoom') or 1.0) if ev.get('crop') in ('solver', 'hands_only') else 1.0
            apply_stab = stab.get('choice') == 'ffmpeg'
            if apply_stab and zoom * STABILIZE_ZOOM > MAX_ZOOM_1080:
                apply_stab = False
                checklist.append({'item': f"Stabilise {ev['sub_clip_id']} in Resolve (FFmpeg stabilisation would exceed the zoom cap: {zoom:.2f} × {STABILIZE_ZOOM})", 'timeline_in_frame': ev['timeline_in_frame']})
            elif stab.get('flagged') and not apply_stab:
                checklist.append({'item': f"Stabilise {ev['sub_clip_id']} in Resolve (flagged, left as is)", 'timeline_in_frame': ev['timeline_in_frame']})
            events.append({**ev, 'source': 'footage', 'stabilize': apply_stab, 'cumulative_zoom': round(zoom * (STABILIZE_ZOOM if apply_stab else 1.0), 3)})
        else:
            gid = ev.get('gap_id') or ev['beat_id']   # ticket 13: since design/21 a scene can hold several blanks (BEAT_01-B1, -B2)
            shots = sorted(fills_by_gap.get(gid, []), key=lambda x: x[1]['placement']['start_frame'])
            if not shots:
                fail(f"Gap {gid} has no fills; record its visuals first.")
            cursor = ev['timeline_in_frame']
            for sid, f in shots:
                c = session['choices'][sid]
                n = f['slot_frames']
                if f['meta']['kind'] == 'movie' and c['end_policy'] == 'trim' and f['available_frames'] is not None and f['available_frames'] - c['offset_frames'] < n:
                    fail(f"{sid}: the take is shorter than its slot with end_policy trim; choose hold_last")
                if f['meta']['issues'] and not c.get('accept_as_is'):
                    fail(f"{sid} has issues {f['meta']['issues']} and was not accepted as is")
                events.append({'kind': 'fill', 'beat_id': ev['beat_id'], 'gap_id': gid, 'shot_id': sid, 'source': 'take' if f['file']['name'].endswith('.mp4') and 'asset' not in f['file']['name'] else 'asset',
                               'file': f['file'], 'media': f['meta'], 'offset_frames': c['offset_frames'], 'end_policy': c['end_policy'], 'timeline_in_frame': cursor, 'timeline_out_frame': cursor + n, 'timeline_frames': n,
                               'fit': 'contain', 'stabilize': False, 'cumulative_zoom': 1.0, 'a2_intervals': [], 'dissolve_into_next': joins.get(sid, 0)})
                cursor += n
            if cursor != ev['timeline_out_frame']:
                fail(f"Gap {gid} fills cover {cursor - ev['timeline_in_frame']} frames; the gap is {ev['timeline_frames']}")
    assembly = {'contract': CONTRACT_ASSEMBLY, 'run_id': str(run['id']), 'master_output': str(master_o['id']), 'master_digest': master_o['summary']['plan_digest'], 'timeline': tl,
                'events': events, 'duration_frames': plan['duration_frames'], 'sfx_cues': plan.get('sfx_cues') or [], 'finishing': (plan.get('finishing_preview') or []) + checklist,
                'choices': session['choices'], 'stabilize': session['stabilize']}
    version = len(session['versions']) + 1
    saved = S2.save_json(store, key(run, f'assembly-v{version}.json'), assembly)
    d = S2.digest(assembly)
    session['versions'].append({'version': version, 'file': saved, 'digest': d, 'events': len(events)})
    session['current'] = d
    session['renders'].pop('assembly', None)
    save_session(store, run, session)
    return {'version': version, 'digest': d, 'events': len(events), 'stabilized': [e['sub_clip_id'] for e in events if e.get('stabilize')], 'finishing_items': len(assembly['finishing']),
            'next': '`vw assembly render`, poll, `vw assembly fetch`, let the operator watch and listen, then `vw assembly review`'}


def current(store, session):
    if not session.get('current'):
        raise Problem(409, 'NOT_ALLOWED', 'Build the assembly first.')
    entry = next(v for v in session['versions'] if v['digest'] == session['current'])
    return S2.load_json(store, entry['file']['key']), entry


def render(conn, store, user, run):
    session = session_of(store, run)
    assembly, entry = current(store, session)
    s2 = S2.session_of(store, run)
    pk = S2._package(store, s2)
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    items = []
    for ev in assembly['events']:
        if ev['kind'] == 'event':
            it = S2._event_items(s2, pk, [ev], rows)[0]
            it['stabilize'] = ev.get('stabilize', False)
            it['normalised_key'] = key(run, f"normalised/{ev['sub_clip_id'].replace(':', '-')}-{ev['timeline_in_frame']}.mp4") if ev.get('stabilize') else None
            items.append(it)
        else:
            m = ev['media']
            fps = m.get('fps') or str(pk['timeline']['fps'])
            if m['kind'] == 'still':
                items.append({'kind': 'still', 'file': ev['file'], 'timeline_frames': ev['timeline_frames'], 'normalised_key': key(run, f"normalised/{ev['shot_id']}.mp4")})
            elif m['kind'] == 'sequence':   # design/65 B8
                items.append({'kind': 'sequence', 'states': m['states'], 'dissolve_frames': m.get('dissolve_frames') or 0, 'motion': m.get('motion') or 'none',
                              'timeline_frames': ev['timeline_frames'], 'normalised_key': key(run, f"normalised/{ev['shot_id']}.mp4")})
            else:
                n_src = int(Fraction(ev['timeline_frames']) * Fraction(str(fps)) / Fraction(str(pk['timeline']['fps'])))
                avail = ev.get('offset_frames', 0) + n_src
                items.append({'kind': 'event', 'sub_clip_id': ev['shot_id'], 'clip': {'id': ev['shot_id'], 'name': ev['file']['name'], 'sha256': ev['file']['sha256'], 'key': ev['file']['key'], 'fps': fps,
                                                                                       'rotation_deg': 0.0, 'hdr': str(m.get('color_transfer') or '').lower() in ('arib-std-b67', 'smpte2084')},
                              'source_in_frame': ev['offset_frames'], 'source_out_frame': avail, 'timeline_frames': ev['timeline_frames'], 'crop_rect': None,
                              'hold_last_frame': ev['end_policy'] == 'hold_last', 'a2': [], 'normalised_key': key(run, f"normalised/{ev['shot_id']}.mp4"),
                              'dissolve_into_next': ev.get('dissolve_into_next') or 0})   # design/71 P4
    open_job = session['renders'].get('assembly')
    if open_job and open_job.get('status') in ('queued', 'running') and open_job.get('digest') == entry['digest']:
        raise Problem(409, 'JOB_OPEN', 'The assembly film is already rendering.', job_id=open_job['job_id'])
    plan = {'kind': 'assembly', 'items': items, 'timeline': pk['timeline'], 'narration_key': s2['package']['narration_key'], 'narration': s2['package'].get('narration'), 'version': entry['version'], 'digest': entry['digest'],
            'out_key': key(run, f"assembly-v{entry['version']}-{entry['digest'][:8]}.mp4"), 'upload_normalised': True}   # design/46 11.1: its own kind, the full size
    frames = sum(int(it.get('timeline_frames') or 0) for it in items)   # design/46 11.4
    rk = S2.save_json(store, key(run, f"render-assembly-v{entry['version']}.json"), plan)
    job = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'assembly','assembly','render',%s, gen_random_uuid()) returning id",
                       (run['id'], Jsonb({'kind': 'render', 'film': 'assembly', 'plan_key': rk['key'], 'out_key': plan['out_key']}))).fetchone()
    session['renders']['assembly'] = {'job_id': str(job['id']), 'status': 'queued', 'digest': entry['digest'], 'version': entry['version'], 'out_key': plan['out_key'], 'frames': frames}
    save_session(store, run, session)
    return {'job_id': str(job['id']), 'version': entry['version'], 'frames': frames, 'paid': False, 'next': 'wait with `vw assembly status --wait 900`, then fetch; the operator watches and listens'}


def _refresh(conn, session):
    for kind, r in session['renders'].items():
        row = conn.execute('select status, result, error from vw2_jobs where id=%s', (r['job_id'],)).fetchone()
        if row:
            r.update(status=row['status'], error=row['error'], result=row['result'])


def status(conn, store, run):
    try:
        session = session_of(store, run)
    except Problem:
        return {'state': 'not_prepared'}
    _refresh(conn, session)
    save_session(store, run, session)
    last = conn.execute("select result->'record'->>'frames_per_s' as rate from vw2_jobs where provider='render' and status='ready' and result->'record'->>'frames_per_s' is not null "
                        "order by updated_at desc limit 1").fetchone()   # design/46 11.4
    return {**{k: session.get(k) for k in ('fills', 'choices', 'stabilize', 'versions', 'current', 'renders', 'reviews', 'recorded', 'bundle', 'resolve', 'final')},
            'render_rate_fps': float(last['rate']) if last and last['rate'] else None}


def review(conn, store, user, run, decision, notes, frame_notes, quote):
    session = session_of(store, run)
    assembly, entry = current(store, session)
    _refresh(conn, session)
    film = session['renders'].get('assembly') or {}
    if film.get('status') != 'ready' or film.get('digest') != entry['digest']:
        raise Problem(409, 'NOT_ALLOWED', 'Render the current assembly and let the operator watch it before reviewing.')
    if decision not in ('accepted', 'changes', 'rejected'):
        fail('decision is accepted, changes or rejected')
    q = (quote or '').lower()
    if decision == 'accepted' and ('watch' not in q or 'listen' not in q):
        fail("Acceptance must say the operator watched the film and listened to it (both words).")
    row = {'decision': decision, 'notes': notes or '', 'frame_notes': frame_notes or [], 'quote': quote, 'version': entry['version'], 'film_sha256': film['result']['sha256'], 'by': user['id'],
           'at': datetime.now(timezone.utc).isoformat()}
    session['reviews'].append(row)
    if decision == 'changes':
        session['current'] = None   # choices stay; the operator changes some and builds again; frame notes are carried in the next version's record
    save_session(store, run, session)
    return {**row, 'next': {'accepted': '`vw assembly record --quote`', 'changes': 'change the choices the notes name, `vw assembly build`, render again', 'rejected': '`vw revise --stage visuals` or `--stage master` as the notes say'}[decision]}


def record(conn, store, user, run, quote):
    session = session_of(store, run)
    assembly, entry = current(store, session)
    _refresh(conn, session)
    film = session['renders'].get('assembly') or {}
    if film.get('status') != 'ready' or film.get('digest') != entry['digest']:
        raise Problem(409, 'NOT_ALLOWED', 'The current assembly is not rendered.')
    last = session['reviews'][-1] if session['reviews'] else None
    if not last or last['decision'] != 'accepted' or last['film_sha256'] != film['result']['sha256']:
        q = (quote or '').lower()
        if 'watch' not in q or 'listen' not in q:   # design/46 11.5: one call records the review and the output when the words are there
            raise Problem(409, 'NOT_ALLOWED', "The operator's yes must say they watched the film and listened to it (both words); or review it first (`vw assembly review --decision accepted`).")
        last = {'decision': 'accepted', 'notes': '', 'frame_notes': [], 'quote': quote, 'version': entry['version'], 'film_sha256': film['result']['sha256'], 'by': user['id'],
                'at': datetime.now(timezone.utc).isoformat()}
        session['reviews'].append(last)
    files = [{'name': f"assembly-v{entry['version']}.json", **{k: entry['file'][k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True},
             {'name': 'assembly.mp4', 'key': film['result']['key'], 'sha256': film['result']['sha256'], 'bytes': film['result']['bytes'], 'location': 'storage', 'receipt': True}]
    for n in (film['result'].get('record') or {}).get('normalised') or []:
        files.append({'name': 'normalised/' + Path(n['key']).name, 'key': n['key'], 'sha256': n['sha256'], 'bytes': n['bytes'], 'location': 'storage', 'receipt': True})
    for f in files:
        jobs.record_file(conn, run['id'], 'assembly', f['key'], f['name'], f['sha256'], f['bytes'], 'application/json' if f['name'].endswith('.json') else 'video/mp4')
    rec = film['result'].get('record') or {}
    summary = {'version': entry['version'], 'assembly_digest': entry['digest'], 'master_digest': assembly['master_digest'], 'duration_frames': assembly['duration_frames'],
               'film': {'sha256': film['result']['sha256'], 'duration_s': film['result'].get('duration_s'), 'bytes': film['result']['bytes']},
               'loudness': {'a1': rec.get('a1_measured'), 'a1_gain_db': rec.get('a1_gain_db'), 'mix': rec.get('mix'), 'check': rec.get('loudness_check')}, 'a2_pieces': rec.get('a2_pieces'),
               'stabilized': [e['sub_clip_id'] for e in assembly['events'] if e.get('stabilize')], 'fills': len([e for e in assembly['events'] if e['kind'] == 'fill']),
               'finishing': assembly['finishing'], 'sfx_cues': len(assembly['sfx_cues']), 'review': {k: last[k] for k in ('decision', 'notes', 'frame_notes', 'quote')}}
    out = core.output(conn, user, run, {'stage': 'assembly', 'files': files, 'accepted_quote': quote, 'summary': summary})
    session['recorded']['assembly'] = str(out['id'])
    save_session(store, run, session)
    return {'output': str(out['id']), 'version': entry['version'], 'next': '`vw delivery bundle`'}
