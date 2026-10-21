"""Visuals stage: direction (chat model), reference library (frame / supplied / web / generated via OpenAI GPT Image 2.5),
bindings, video takes (Google Omni / Higgsfield) and local assets, one stage output per gap.

Session state is one JSON object in storage ({run}/visuals/session.json); images, takes and plans are files.
Unit of the ledger = gap (from the planning certificate, or the approved first cut when the Mac slice exists);
a gap's output is recorded when every shot in it has a selected take or a local asset."""
import base64
import hashlib
import json
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from io import BytesIO
from pathlib import Path

from psycopg.types.json import Jsonb

from . import core, jobs, video_generators
from .errors import Problem
from .planning.digest import digest
from .storage import storage
from .video_providers import motion_text
from .visual_contract import STILL_TYPES, chosen_scenes, gap_digest, need, routes, validate_plan

STAGE = 'visuals'
IMAGE_MODELS = {'generate': 'gpt-image-2.5-flare', 'edit': 'gpt-image-2.5-sunburst'}
REF_KINDS = ('frame', 'supplied', 'web', 'isolated', 'sheet', 'keyframe')


def fail(message):
    raise Problem(422, 'VISUALS_CONTRACT', str(message))


def guarded(fn):
    try:
        return fn()
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        fail(exc)


def key(run, name):
    return f"{run['id']}/visuals/{name}"


def load_json(store, k):
    return json.loads(store.get(k).decode('utf-8'))


def save_json(store, k, value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')
    store.put(k, data, 'application/json')
    return {'key': k, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def session_of(store, run, outputs, create=False):
    try:
        return load_json(store, key(run, 'session.json'))
    except Problem:
        if not create:
            raise Problem(409, 'NOT_ALLOWED', 'Run `vw visuals prepare` first.')
    return {'contract': 'vw2-visuals-session-v1', 'source': gaps_source(store, outputs), 'versions': [], 'current': None,
            'accepted': {}, 'choice_selections': {}, 'references': {}, 'bindings': {}, 'generator_choices': {}, 'preparations': {},
            'reviews': {}, 'selections': {}, 'assets': {}, 'recorded_gaps': {}}


def save_session(store, run, session):
    session['updated_at'] = datetime.now(timezone.utc).isoformat()
    save_json(store, key(run, 'session.json'), session)
    return session


# ---------- gaps ----------

def _fps(session):
    from fractions import Fraction
    return Fraction(str(session['source'].get('fps'))) if session['source'].get('fps') else None


def gaps_source(store, outputs):
    """Gaps come from the approved first cut when present (Mac slice), else from the planning certificate."""
    first_cut = next((o for o in outputs if o['stage'] == 'first_cut' and o['unit'] is None), None)
    planning = next((o for o in outputs if o['stage'] in ('planning', 'master') and o['unit'] is None), None)
    if not planning:
        raise Problem(409, 'NOT_ALLOWED', 'Visuals needs a finalized plan (planning or master) first.')
    base = first_cut['summary'] if first_cut and first_cut['summary'].get('gaps') is not None else planning['summary']
    gaps = {g['shot_id']: {'start_frame': g['start_frame'], 'end_frame': g['end_frame'], 'passage_ids': g.get('passage_ids', []), 'requirement': g.get('reason', '')} for g in base['gaps']}
    return {'from': 'first_cut' if base is not planning['summary'] else 'planning', 'fps': str(base.get('fps') or planning['summary']['fps']),
            'resolution': base.get('resolution') or planning['summary']['resolution'], 'plan_digest': planning['summary']['plan_digest'], 'gaps': gaps}


# ---------- direction ----------

def prepare(conn, store, user, run, outputs):
    session = session_of(store, run, outputs, create=True)
    procedure = core._stage(core.stage_table(run['procedure_version']), STAGE)
    brief = next((o for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None)
    script = next((o for o in outputs if o['stage'] == 'script' and o['unit'] is None), None)
    world = []
    for o in outputs:
        if o['stage'] == 'analysis' and not o['summary'].get('excluded'):
            ref = next((f for f in o['files'] if f['name'].endswith('.evidence.json')), None)
            if ref:
                doc = load_json(store, ref['key'])
                if doc.get('contract_version') == 'clip-log-v1':
                    log = doc['log']
                    world.append({'clip': o['unit'], 'entities': log.get('entities'), 'unavailable_or_uncertain': log.get('unavailable_or_uncertain'),
                                  'landmarks': sorted({l for s in log.get('sub_clips') or [] for l in (s.get('continuity_and_story') or {}).get('world_landmarks_and_props', [])})})
                else:
                    ev = doc['evidence']
                    world.append({'clip': o['unit'], 'world_markers': ev.get('world_markers'), 'evidence_limits': ev.get('evidence_limits')})
    save_session(store, run, session)
    package = {'source': session['source'], 'prompt': procedure.get('prompt') or '', 'steps': procedure.get('steps') or [],
               'brief': ({**brief['summary'], 'effective_rules': core.effective_rules(conn, run, outputs)} if brief else None),   # design/37 2.7
               'script_digest': script['summary'].get('content_digest') if script else None,
               'world_evidence': world, 'plan_schema': __import__('app.visual_contract', fromlist=['Plan']).Plan.model_json_schema(),
               'generator_catalog': video_generators.catalog()}
    pk = save_json(store, key(run, 'package.json'), package)
    return {'package': pk, 'gaps': list(session['source']['gaps']), 'next': 'write out/visual-plan.json then `vw visuals check`'}


def check(store, run, outputs, document):
    session = session_of(store, run, outputs)
    try:
        plan, warnings = validate_plan(document, session['source']['gaps'], _fps(session))
    except (ValueError, KeyError, TypeError) as exc:
        return {'status': 'rejected', 'error': str(exc)}
    return {'status': 'valid', 'warnings': warnings, 'routes': routes(plan, _fps(session) or 25), 'plan_digest': digest(plan)}   # design/45 10.2


def propose(conn, store, user, run, outputs, document):
    session = session_of(store, run, outputs)
    plan, warnings = guarded(lambda: validate_plan(document, session['source']['gaps'], _fps(session)))
    version = len(session['versions']) + 1
    record = {'run_id': str(run['id']), 'version': version, 'source_plan_digest': session['source']['plan_digest'], 'document': plan,
              'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    pk = save_json(store, key(run, f'plan-v{version}.json'), record)
    identity = digest(plan)
    session['versions'].append({'version': version, 'file': pk, 'plan_digest': identity, 'warnings': warnings})
    session['current'] = identity
    # accepted gaps survive only if their scoped digest is unchanged
    for gid, acc in list(session['accepted'].items()):
        gap = next((g for g in plan['gaps'] if g['gap_id'] == gid), None)
        if not gap or acc['digest'] != gap_digest(plan, gap):
            session['accepted'].pop(gid)
    save_session(store, run, session)
    return {'version': version, 'plan_digest': identity, 'warnings': warnings, 'routes': routes(plan, _fps(session) or 25), 'gaps': [g['gap_id'] for g in plan['gaps']]}


def current_plan(store, session):
    need(session.get('current'), 'Propose a visual plan first.')
    entry = next(v for v in session['versions'] if v['plan_digest'] == session['current'])
    return load_json(store, entry['file']['key'])['document']


def select_choice(store, user, run, outputs, choices):
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    for gid, cid in choices.items():
        gap = next((g for g in plan['gaps'] if g['gap_id'] == gid), None)
        need(gap and gap.get('choices') and any(c['id'] == cid for c in gap['choices']), f'Gap {gid} has no choice {cid}.')
        session['choice_selections'][gid] = {'choice_id': cid, 'by': user['id']}
    save_session(store, run, session)
    return {'choices': session['choice_selections']}


def accept(store, user, run, outputs, gap_ids, quote):
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    if list(gap_ids) == ['all']:   # design/45 10.4: every gap of the current version
        gap_ids = [g['gap_id'] for g in plan['gaps']]
        unresolved = [g['gap_id'] for g in plan['gaps'] if g.get('choices') and not session['choice_selections'].get(g['gap_id'])]
        need(not unresolved, 'Select a choice for these gaps before accepting all: ' + ', '.join(unresolved))
    for gid in gap_ids:
        gap = next((g for g in plan['gaps'] if g['gap_id'] == gid), None)
        need(gap, f'Unknown gap {gid}.')
        if gap.get('choices'):
            need(session['choice_selections'].get(gid), f'Select a choice for gap {gid} before accepting it.')
        session['accepted'][gid] = {'digest': gap_digest(plan, gap), 'choice_id': (session['choice_selections'].get(gid) or {}).get('choice_id'), 'quote': quote, 'by': user['id']}
    save_session(store, run, session)
    return {'accepted': sorted(session['accepted'])}


def shots_of(plan, session, gid):
    gap = next(g for g in plan['gaps'] if g['gap_id'] == gid)
    return [s for sc in chosen_scenes(gap, session['choice_selections'].get(gid)) for s in sc['shots']]


def locate(store, session, shot_id):
    plan = current_plan(store, session)
    for gap in plan['gaps']:
        if gap.get('choices') and not session['choice_selections'].get(gap['gap_id']):
            continue
        for scene in chosen_scenes(gap, session['choice_selections'].get(gap['gap_id'])):
            for shot in scene['shots']:
                if shot['id'] == shot_id:
                    acc = session['accepted'].get(gap['gap_id'])
                    need(acc and acc['digest'] == gap_digest(plan, gap), f"Accept gap {gap['gap_id']} (current version) before working on its shots.")
                    return plan, gap, scene, shot
    raise ValueError(f'Shot {shot_id} is not in an accepted gap of the current plan.')


# ---------- references ----------

def image_bytes(raw):
    from PIL import Image
    need(0 < len(raw) <= 16 * 1024 * 1024, 'Reference image must be at most 16 MiB.')
    with Image.open(BytesIO(raw)) as image:
        need(image.format in ('PNG', 'JPEG', 'WEBP') and image.width * image.height <= 24_000_000, 'Use a PNG, JPEG or WebP image up to 24 megapixels.')
        image.load()
        out = BytesIO()
        image.convert('RGBA' if image.mode == 'RGBA' else 'RGB').save(out, format='PNG')
        size = image.size
    return out.getvalue(), size


def _store_reference(store, run, session, ref_id, png, meta):
    k = key(run, f'references/{ref_id}.png')
    store.put(k, png, 'image/png')
    row = {**meta, 'id': ref_id, 'key': k, 'sha256': hashlib.sha256(png).hexdigest(), 'bytes': len(png), 'status': 'candidate', 'approval': None,
           'created_at': datetime.now(timezone.utc).isoformat()}
    session['references'][ref_id] = row
    return row


def add_reference(conn, store, user, run, outputs, body, content):
    """kind frame (extract from a clip) · supplied (operator bytes) · web (bytes + HTTPS url + selection reply)."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    element = next((e for e in plan['elements'] if e['id'] == body['element_id']), None)
    need(element, 'Reference must identify an element in the current plan.')
    ref_id = digest({'run': str(run['id']), 'request': body['request_id']})[:32]
    if ref_id in session['references']:
        return session['references'][ref_id]
    meta = {'element_id': body['element_id'], 'element_kind': element['kind'], 'name': body['name'], 'kind': body['kind'], 'subject': body['subject'], 'source': {}}
    if body['kind'] == 'frame':
        media = next((o for o in outputs if o['stage'] == 'media' and o['unit'] is None), None)
        clipr = next((c for c in media['summary']['clips'] if c['id'] == body.get('source_media_id')), None) if media else None
        need(clipr and body.get('requested_s') is not None and 0 <= body['requested_s'] < clipr['duration_s'], 'Frame needs a known clip and a time inside it.')
        with tempfile.TemporaryDirectory(prefix='vw2-ref-') as folder:
            src = Path(folder) / 'src.mp4'
            src.write_bytes(store.get(f"{run['id']}/media/{clipr['name']}"))
            out = Path(folder) / 'frame.png'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f"{body['requested_s']:.6f}", '-i', str(src), '-frames:v', '1', str(out)], check=True, capture_output=True, timeout=120)
            png, size = image_bytes(out.read_bytes())
        meta['source'] = {'media_id': clipr['id'], 'source_sha256': clipr['sha256'], 'requested_s': body['requested_s']}
    else:
        need(content, 'Image bytes are required.')
        if body['kind'] == 'web':
            from urllib.parse import urlsplit
            url = urlsplit(body.get('source_url') or '')
            need(url.scheme == 'https' and url.hostname and not url.username and not url.password and (body.get('selection_reply') or '').strip(),
                 'A web reference needs its public HTTPS source URL and the operator selection reply.')
            meta['source'] = {'url': body['source_url'], 'selection_reply': body['selection_reply']}
        need(body['kind'] in ('supplied', 'web'), 'Generated kinds come from `vw visuals image`, not from supplied bytes.')
        png, size = image_bytes(content)
    meta['width'], meta['height'] = size
    row = _store_reference(store, run, session, ref_id, png, meta)
    save_session(store, run, session)
    return row


def generate_image(conn, store, user, run, outputs, body):
    """Queue an OpenAI image job (paid, informed). The worker stores the PNG and creates the candidate reference."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    element = next((e for e in plan['elements'] if e['id'] == body['element_id']), None)
    need(element, 'Reference must identify an element in the current plan.')
    need(body['kind'] in ('isolated', 'sheet', 'keyframe'), 'Generated references are isolated, sheet or keyframe.')
    parents = [session['references'].get(p) for p in body.get('parents') or []]
    need(all(p and p['status'] == 'approved' for p in parents), 'Parents must be approved references of this run.')
    op = 'edit' if parents else 'generate'
    ref_id = digest({'run': str(run['id']), 'request': body['request_id']})[:32]
    request = {'kind': 'image', 'op': op, 'model': body.get('model') or IMAGE_MODELS[op], 'prompt': body['prompt'], 'size': body.get('size') or '1536x864',
               'quality': body.get('quality') or 'high', 'parents': [{'id': p['id'], 'key': p['key'], 'sha256': p['sha256']} for p in parents],
               'reference': {'id': ref_id, 'element_id': body['element_id'], 'element_kind': element['kind'], 'name': body['name'], 'kind': body['kind'], 'subject': body['subject']}}
    row = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,'openai',%s,%s) returning id",
                       (run['id'], ref_id, Jsonb(request), body['request_id'])).fetchone()
    session['references'][ref_id] = {**request['reference'], 'id': ref_id, 'status': 'generating', 'job_id': str(row['id']), 'generation': {k: request[k] for k in ('op', 'model', 'prompt', 'size', 'quality', 'parents')}}
    save_session(store, run, session)
    return {'reference_id': ref_id, 'job_id': str(row['id']), 'model': request['model'], 'op': op}


def approve_reference(store, user, run, outputs, ref_id, sha256, quote):
    session = session_of(store, run, outputs)
    row = session['references'].get(ref_id)
    need(row and row['status'] in ('candidate', 'approved'), 'Reference is not a candidate.')
    if row['sha256'] != sha256:
        raise Problem(409, 'REFERENCE_MISMATCH', 'Approve the exact stored image hash after viewing it.')
    need((quote or '').strip(), 'The operator reply is required.')
    row.update(status='approved', approval={'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'sha256': sha256, 'quote': quote})
    save_session(store, run, session)
    return row


def bind(store, user, run, outputs, shot_id, references, selectors, quote=''):
    """design/45 10.4: the approved references are the operator's yes; a quote is kept when given."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    need(set(references) == set(shot['element_ids']), 'Cover every required shot element with approved references: ' + ', '.join(sorted(set(shot['element_ids']) - set(references))))
    elements = {e['id']: e for e in plan['elements']}
    bindings = {}
    for eid, ids in references.items():
        need(0 < len(ids) <= 20 and len(ids) == len(set(ids)), 'Choose 1–20 distinct references per element.')
        rows = []
        for rid in ids:
            row = session['references'].get(rid)
            need(row and row['status'] == 'approved', f'Reference {rid} is not approved.')
            sel = (selectors.get(eid) or {}).get(rid)
            depicted = elements[eid]['kind'] == 'object' and row['element_kind'] == 'place'
            need(row['element_kind'] == elements[eid]['kind'] or (depicted and sel), 'Reference subject type must match the element (or give a subject selector for an object inside a place reference).')
            rows.append({'id': rid, 'sha256': row['sha256'], **({'subject_selector': sel} if sel else {})})
        bindings[eid] = rows
    session['bindings'][shot_id] = {'gap_digest': gap_digest(plan, gap), 'references': bindings, 'quote': quote or '', 'by': user['id']}
    save_session(store, run, session)
    return {'shot_id': shot_id, 'elements': sorted(bindings)}


def packet(store, run, outputs, shot_id, session=None):
    session = session or session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    binding = session['bindings'].get(shot_id)
    need(binding and binding['gap_digest'] == gap_digest(plan, gap), 'Bind references for this shot under the current accepted plan.')
    refs = []
    for eid, rows in binding['references'].items():
        for b in rows:
            row = session['references'][b['id']]
            need(row['status'] == 'approved' and row['sha256'] == b['sha256'], 'A bound reference changed or lost approval.')
            refs.append({'element_id': eid, 'reference_id': b['id'], 'sha256': b['sha256'], 'key': row['key'], 'subject': row['subject'], **({'subject_selector': b['subject_selector']} if 'subject_selector' in b else {})})
    generator = session['generator_choices'].get(shot_id) or video_generators.DEFAULT
    prompt = {'foundation': plan['foundation'], 'scene': {k: v for k, v in scene.items() if k != 'shots'}, 'shot': shot, 'references': refs,
              'sequence_rules': plan.get('sequence_rules', []), 'elements': [e for e in plan['elements'] if e['id'] in shot['element_ids']],
              'image_instruction': 'Compose the starting state of every visible subject, including secondary/background subjects, in the named scene layout. Keep landmark-relative locations; the camera only changes their screen projection.',
              'video_instruction': 'Read the actual accepted starting image before writing movement. For EACH subject, follow the ordered beats, targets, paths, contacts, object responses and final progress. Keep non-acting subjects where they are.',
              'checks': ['Treatment and narrated meaning', 'All visible subjects accounted for', 'World-relative layout and scale', 'Secondary action progression', 'Reference identity', 'Boundary continuity', 'Exact placement duration'],
              'provider': {k: generator[k] for k in ('provider', 'model')}}
    return {'plan_digest': session['current'], 'gap_id': gap['gap_id'], 'shot_id': shot_id, 'preparation_digest': digest(prompt), 'preparation': prompt,
            'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame'], 'fps': session['source']['fps']}}


# ---------- takes ----------

def select_generator(store, user, run, outputs, shot_id, provider, model):
    session = session_of(store, run, outputs)
    guarded(lambda: video_generators.GeneratorChoice(shot_id=shot_id, provider=provider, model=model))
    session['generator_choices'][shot_id] = {'provider': provider, 'model': model, 'plan_digest': session['current']}
    save_session(store, run, session)
    return session['generator_choices'][shot_id]


def default_aspect(brief_summary, body):
    """design/53 L7: a take's aspect ratio is the body's, else the brief's frame, else 16:9."""
    if body.get('aspect_ratio'):
        return body['aspect_ratio']
    return (((brief_summary or {}).get('production') or {}).get('format') or {}).get('frame') or '16:9'


def prepare_take(store, user, run, outputs, body):
    session = session_of(store, run, outputs)
    base = packet(store, run, outputs, body['shot_id'], session)
    shot = base['preparation']['shot']
    need(shot['visual_type'] == 'video', f"shot {shot['id']} is a {shot['visual_type']} shot: " + ('an animation shot takes a graphic sequence (`vw visuals sequence`)' if shot['visual_type'] == 'animation' else 'it takes a still (`vw visuals still`)') + ', not a take.')
    need(set(body['subject_reconciliation']) == {s['element_id'] for s in shot['subjects']}, 'Reconcile every subject of the shot, exactly those: ' + ', '.join(s['element_id'] for s in shot['subjects']))
    selected = base['preparation']['provider']
    cap = next(c for c in video_generators.CATALOG if c['provider'] == selected['provider'] and c['model'] == selected['model'])
    fps = Fraction(session['source']['fps'])
    exact = Fraction(shot['end_frame'] - shot['start_frame']) / fps
    need(exact <= cap['max_seconds'], f"shot {shot['id']} is {float(exact):.1f} s, longer than {cap['label'].split(' ·')[0]}'s maximum {cap['max_seconds']} s: "
                                      "split the shot or choose another generator (`vw visuals generator`)")   # design/45 10.7: refuse, never clamp
    duration = body.get('duration_seconds') or max(cap['min_seconds'], -(-exact.numerator // exact.denominator))  # ceil, at least the generator's minimum
    need(cap['min_seconds'] <= duration <= cap['max_seconds'], f"Duration {duration}s is outside {cap['label']} ({cap['min_seconds']}–{cap['max_seconds']}s).")
    images = {}
    for role in ('start_image', 'end_image'):
        rid = body.get(role)
        if not rid:
            need(role == 'end_image', 'A start image is required.')
            continue
        row = session['references'].get(rid)
        need(row and row['status'] == 'approved', f'{role} must be an approved reference.')
        images[role] = {'reference_id': rid, 'sha256': row['sha256'], 'key': row['key'], 'mime_type': 'image/png', 'width': row.get('width'), 'height': row.get('height')}
    record = {'contract': 'videowizard-video-request-v1', 'run_id': str(run['id']), 'shot_id': body['shot_id'], 'plan_digest': base['plan_digest'],
              'base_preparation_digest': base['preparation_digest'], 'motion_prompt': body['motion_prompt'], 'subject_reconciliation': body['subject_reconciliation'],
              'continuity_notes': body.get('continuity_notes') or '', 'duration_seconds': int(duration),
              'aspect_ratio': default_aspect(next((o['summary'] for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None), body),   # design/53 L7
              'resolution': body.get('resolution') or ('720p' if selected['model'] != video_generators.CATALOG[1]['model'] else None),
              **images, 'provider': selected['provider'], 'model': selected['model'],
              'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame'], 'film_fps': str(fps), 'duration_seconds': str(exact), 'exact_seconds': float(exact)},
              'generated_audio_policy': 'retain original output; never replace narration automatically'}
    record['effective_prompt'] = motion_text(record)
    identity = digest(record)
    save_json(store, key(run, f'takes/{identity}.request.json'), record)
    session['preparations'][body['shot_id']] = {'preparation_id': identity, 'key': key(run, f'takes/{identity}.request.json')}
    save_session(store, run, session)
    return {'preparation_id': identity, 'duration_seconds': record['duration_seconds'], 'exact_seconds': record['placement']['exact_seconds'], 'provider': selected}


def submit_take(conn, store, user, run, outputs, shot_id):
    session = session_of(store, run, outputs)
    prep = session['preparations'].get(shot_id)
    need(prep, 'Prepare the take first.')
    open_job = conn.execute("select id from vw2_jobs where run_id=%s and stage='visuals' and unit=%s and provider='video' and status in ('queued','running','submitted','submission_unknown','storage_pending')",
                            (run['id'], shot_id)).fetchone()
    if open_job:
        raise Problem(409, 'JOB_OPEN', 'A take for this shot is still open; wait, recover or resolve it first.', job_id=str(open_job['id']))
    request = load_json(store, prep['key'])
    row = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,'video',%s, gen_random_uuid()) returning id",
                       (run['id'], shot_id, Jsonb({'kind': 'take', 'preparation_id': prep['preparation_id'], 'request_key': prep['key'], 'provider': request['provider'], 'model': request['model']}))).fetchone()
    return {'job_id': str(row['id']), 'shot_id': shot_id, 'provider': request['provider'], 'model': request['model']}


def take_jobs(conn, run, shot_id=None):
    sql = "select id, unit, provider, status, request, result, error, cost, attempt, created_at, updated_at from vw2_jobs where run_id=%s and stage='visuals'"
    rows = conn.execute(sql + (' and unit=%s' if shot_id else '') + ' order by created_at', (run['id'], shot_id) if shot_id else (run['id'],)).fetchall()
    return rows


def review_take(conn, store, user, run, outputs, job_id, decision, notes, timing_notes, quote):
    session = session_of(store, run, outputs)
    job = conn.execute("select * from vw2_jobs where id=%s and run_id=%s and provider='video'", (job_id, run['id'])).fetchone()
    need(job and job['status'] == 'ready', 'Review a ready take.')
    ev = job['result']['evidence']
    need(decision != 'accepted' or ev.get('timing_matches_placement') or (timing_notes or '').strip(), 'The take duration differs from the placement; explain in timing_notes before accepting.')
    review = {'id': digest({'job': str(job_id), 'decision': decision, 'notes': notes, 'at': datetime.now(timezone.utc).isoformat()}), 'decision': decision, 'notes': notes,
              'timing_notes': timing_notes or '', 'quote': quote, 'by': user['id'], 'sha256': job['result']['sha256']}
    session['reviews'].setdefault(str(job_id), []).append(review)
    if session['selections'].get(job['unit'], {}).get('job_id') == str(job_id):
        session['selections'].pop(job['unit'])
    save_session(store, run, session)
    return review


def select_take(conn, store, user, run, outputs, job_id, quote, notes='', timing_notes=''):
    """design/45 10.4: with notes, the accepted review and the selection are one call; without, the latest review must be accepted."""
    session = session_of(store, run, outputs)
    job = conn.execute("select * from vw2_jobs where id=%s and run_id=%s and provider='video'", (job_id, run['id'])).fetchone()
    need(job and job['status'] == 'ready', 'Select a ready take.')
    if str(notes or '').strip():
        ev = job['result']['evidence']
        need(ev.get('timing_matches_placement') or str(timing_notes or '').strip(), 'The take is shorter than its placement; explain in timing_notes before accepting.')
        session['reviews'].setdefault(str(job_id), []).append({'id': digest({'job': str(job_id), 'decision': 'accepted', 'notes': notes, 'at': datetime.now(timezone.utc).isoformat()}),
                                                                 'decision': 'accepted', 'notes': notes, 'timing_notes': timing_notes or '', 'quote': quote, 'by': user['id'], 'sha256': job['result']['sha256']})
    reviews = session['reviews'].get(str(job_id), [])
    need(reviews and reviews[-1]['decision'] == 'accepted', 'Select only a take whose latest review is accepted.')
    live = packet(store, run, outputs, job['unit'], session)
    prep = load_json(store, job['request']['request_key'])
    need(live['preparation_digest'] == prep['base_preparation_digest'], 'The plan, references or generator changed since this take was prepared; prepare a current take.')
    session['selections'][job['unit']] = {'job_id': str(job_id), 'review_id': reviews[-1]['id'], 'preparation_id': job['request']['preparation_id'], 'context_digest': live['preparation_digest'],
                                          'take': {k: job['result'][k] for k in ('key', 'sha256', 'bytes')}, 'quote': quote, 'by': user['id']}
    save_session(store, run, session)
    return session['selections'][job['unit']]


def still_from_reference(store, user, run, outputs, shot_id, reference_id, quote):
    """design/45 10.3: an approved reference becomes a still shot's asset; no download and upload."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    need(shot['visual_type'] != 'animation', f'shot {shot_id} is an animation shot: it takes a graphic sequence (`vw visuals sequence`), not a still.')
    need(shot['visual_type'] in STILL_TYPES, f"shot {shot_id} is a video shot: it takes a take (`vw visuals prepare-take`), not a still.")
    row = session['references'].get(reference_id)
    need(row and row['status'] == 'approved', f'Reference {reference_id} is not an approved reference of this run.')
    need((quote or '').strip(), 'The operator reply is required.')
    session['assets'][shot_id] = {'kind': 'still', 'key': row['key'], 'sha256': row['sha256'], 'bytes': row['bytes'], 'reference_id': reference_id, 'quote': quote, 'by': user['id'],
                                  'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame']}}
    session['selections'].pop(shot_id, None)
    save_session(store, run, session)
    return {'shot_id': shot_id, 'kind': 'still', 'reference_id': reference_id, 'sha256': row['sha256']}


def add_asset(conn, store, user, run, outputs, shot_id, file_key, sha256, size, kind, quote):
    """A hand-made movie or still already uploaded with a receipt becomes the shot's output."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    need(kind in ('movie', 'still'), 'Local assets are movie or still.')
    row = conn.execute('select key, sha256, bytes from vw2_files where run_id=%s and key=%s', (run['id'], file_key)).fetchone()
    need(row and row['sha256'] == sha256, 'Upload the asset with a receipt first (vw upload).')
    session['assets'][shot_id] = {'kind': kind, 'key': file_key, 'sha256': sha256, 'bytes': size, 'quote': quote, 'by': user['id'],
                                  'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame']}}
    session['selections'].pop(shot_id, None)
    save_session(store, run, session)
    return session['assets'][shot_id]


# ---------- status / gap outputs ----------

def reconcile(conn, run, session):
    """Ticket 9: repair references left 'generating' after their image job finished (a lost write). Returns how many changed."""
    from .visual_workers import apply_image_result
    fixed = 0
    for ref in session['references'].values():
        if ref.get('status') != 'generating' or not ref.get('job_id'):
            continue
        job = conn.execute('select status, result, error, cost from vw2_jobs where id=%s', (ref['job_id'],)).fetchone()
        if job and apply_image_result(conn, run['id'], ref, job['status'], job['result'] or {}, job['error'], job['cost']):
            fixed += 1
    return fixed


def status(conn, store, run, outputs):
    try:
        session = session_of(store, run, outputs)
    except Problem:
        return {'state': 'not_prepared', 'next': 'prepare'}
    if reconcile(conn, run, session):
        save_session(store, run, session)
    plan = current_plan(store, session) if session.get('current') else None
    gaps = []
    for gid, g in session['source']['gaps'].items():
        entry = {'gap_id': gid, **g, 'accepted': gid in session['accepted'], 'recorded': gid in session['recorded_gaps'], 'shots': []}
        if plan and gid in session['accepted']:
            for s in shots_of(plan, session, gid):
                entry['shots'].append({'shot_id': s['id'], 'visual_type': s['visual_type'], 'bound': s['id'] in session['bindings'], 'prepared': s['id'] in session['preparations'],
                                       'selected': s['id'] in session['selections'], 'asset': s['id'] in session['assets']})
        gaps.append(entry)
    refs = [{k: r.get(k) for k in ('id', 'name', 'kind', 'element_id', 'status', 'sha256', 'job_id')} for r in session['references'].values()]
    jobs_ = [{k: j[k] for k in ('id', 'unit', 'provider', 'status', 'error', 'cost')} for j in take_jobs(conn, run)]
    return {'state': 'prepared', 'plan_digest': session.get('current'), 'versions': len(session['versions']), 'gaps': gaps, 'references': refs, 'jobs': jobs_}


def unique_by_name(files):
    """Ticket 12: one entry per file name, not per stored key, so two shots may share one placeholder or image."""
    seen, out = set(), []
    for f in files:
        if f['name'] not in seen:
            seen.add(f['name'])
            out.append(f)
    return out


def record_gaps(conn, store, user, run, outputs, gap_ids, quote):
    """design/45 10.4: `all` records every accepted gap whose shots are done; named gaps are recorded as before (a gap not ready is refused)."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    recorded, skipped = [], {}
    if list(gap_ids) == ['all']:
        for gid in [g['gap_id'] for g in plan['gaps']]:
            if gid in session['recorded_gaps']:
                continue
            if gid not in session['accepted']:
                skipped[gid] = 'not accepted'
                continue
            missing = [s['id'] for s in shots_of(plan, session, gid) if not (session['selections'].get(s['id']) or session['assets'].get(s['id']))]
            if missing:
                skipped[gid] = 'shot ' + ', '.join(missing) + ' has no selection or asset'
                continue
            record_gap(conn, store, user, run, outputs, gid, quote)
            recorded.append(gid)
    else:
        for gid in gap_ids:
            record_gap(conn, store, user, run, outputs, gid, quote)
            recorded.append(gid)
    return {'recorded': recorded, 'skipped': skipped, 'next': 'vw next' if not skipped else 'finish the skipped gaps, then record again'}


def record_gap(conn, store, user, run, outputs, gap_id, quote):
    """Stage output for one gap: every shot has a selected take or an asset."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    need(gap_id in session['accepted'], f'Gap {gap_id} is not accepted.')
    files, shots = [], []
    cost = []
    for s in shots_of(plan, session, gap_id):
        sel, asset = session['selections'].get(s['id']), session['assets'].get(s['id'])
        need(sel or asset, f"Shot {s['id']} has neither a selected take nor a local asset.")
        if sel:
            job = conn.execute("select result, cost from vw2_jobs where id=%s", (sel['job_id'],)).fetchone()
            files.append({'name': f"{s['id']}.mp4", 'key': sel['take']['key'], 'sha256': sel['take']['sha256'], 'bytes': sel['take']['bytes'], 'location': 'storage', 'receipt': True})
            jobs.record_file(conn, run['id'], STAGE, sel['take']['key'], f"{s['id']}.mp4", sel['take']['sha256'], sel['take']['bytes'], 'video/mp4')
            if job and job['cost']:
                cost.append(job['cost'])
            ev = (job['result'] or {}).get('evidence', {}) if job else {}
            media = ({'kind': 'movie', 'duration_s': ev.get('duration_seconds'), 'fps': ev.get('fps'), 'width': ev.get('width'), 'height': ev.get('height'),
                      'color_transfer': ev.get('color_transfer'), 'color_primaries': ev.get('color_primaries'), 'rotation_deg': ev.get('rotation_deg') or 0, 'issues': ev['issues']}
                     if 'issues' in ev else None)   # design/46 11.2: assembly reads this instead of downloading the take
            shots.append({'shot_id': s['id'], 'source': 'take', 'job_id': sel['job_id'], 'placement': {'start_frame': s['start_frame'], 'end_frame': s['end_frame']},
                          'duration_s': ev.get('duration_seconds'), 'timing_matches_placement': ev.get('timing_matches_placement'), **({'media': media} if media else {})})
        else:
            name = f"{s['id']}-asset{'.mp4' if asset['kind'] == 'movie' else '.png'}"
            files.append({'name': name, 'key': asset['key'], 'sha256': asset['sha256'], 'bytes': asset['bytes'], 'location': 'storage', 'receipt': True})
            shots.append({'shot_id': s['id'], 'source': 'asset', 'kind': asset['kind'], 'placement': asset['placement'], **({'media': {'kind': 'still'}} if asset['kind'] == 'still' else {})})
        binding = session['bindings'].get(s['id']) or {}
        for eid, rows in binding.get('references', {}).items():
            for b in rows:
                r = session['references'][b['id']]
                files.append({'name': f"ref-{b['id'][:8]}.png", 'key': r['key'], 'sha256': r['sha256'], 'bytes': r['bytes'], 'location': 'storage', 'receipt': True})
                jobs.record_file(conn, run['id'], STAGE, r['key'], f"ref-{b['id'][:8]}.png", r['sha256'], r['bytes'], 'image/png')
    unique_files = unique_by_name(files)
    image_cost = [r.get('generation', {}).get('cost') for r in session['references'].values() if r.get('generation', {}).get('cost')]
    out = core.output(conn, user, run, {'stage': STAGE, 'unit': gap_id, 'files': unique_files, 'accepted_quote': quote,
                                        'summary': {'gap_id': gap_id, 'plan_digest': session['current'], 'shots': shots, 'take_cost': cost, 'image_cost': image_cost}})
    session['recorded_gaps'][gap_id] = str(out['id'])
    save_session(store, run, session)
    return {'gap_id': gap_id, 'output': str(out['id']), 'shots': len(shots)}
