"""Visuals stage: direction (chat model), reference library (frame / supplied / web / generated via OpenAI GPT Image 2.5),
bindings, video takes (Google Omni / Higgsfield) and local assets, one stage output per gap.

Session state is one JSON object in storage ({run}/visuals/session.json); images, takes and plans are files.
Unit of the ledger = gap (from the planning certificate, or the approved first cut when the Mac slice exists);
a gap's output is recorded when every shot in it has a selected take or a local asset."""
import base64
import hashlib
import json
import re
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from io import BytesIO
from pathlib import Path

from psycopg.types.json import Jsonb

from . import apify, core, jobs, library, video_generators
from .config import settings
from .errors import Problem
from .planning.digest import digest
from .storage import storage
from .video_providers import motion_text, transfer
from .visual_contract import STILL_TYPES, chosen_scenes, gap_digest, need, route_of, routes, validate_plan

STAGE = 'visuals'
IMAGE_MODELS = {'generate': 'gpt-image-2.5-flare', 'edit': 'gpt-image-2.5-sunburst'}
REF_KINDS = ('frame', 'supplied', 'web', 'isolated', 'sheet', 'keyframe', 'state')   # design/65: a state of a graphic sequence, generated from the previous state
TREATMENT_ROUTES = ('footage', 'still', 'graphic_sequence', 'video')
DISSOLVE_S = 0.5   # between the states of a graphic sequence
MAX_INPUTS = 16    # design/71 P2: GPT Image's limit on input pictures (the library's fact sheet A5)


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
    session.setdefault('library_version', library.latest())   # design/68 L2: the library a run reads, kept like the procedure version
    procedure = core._stage(core.stage_table(run['procedure_version']), STAGE)
    brief = next((o for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None)
    script = next((o for o in outputs if o['stage'] == 'script' and o['unit'] is None), None)
    intake = next((o for o in outputs if o['stage'] == 'intake' and o['unit'] is None), None)
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
               'footage_character': footage_character(outputs),   # design/77 L42: the theme's texture comes from this, never from an assumption
               'script_digest': script['summary'].get('content_digest') if script else None,
               'intended_visuals': (intake['summary'].get('intended_visuals') if intake else None) or [],   # design/65 S3: the team's pictures per scene
               'world_evidence': world, 'plan_schema': __import__('app.visual_contract', fromlist=['Plan']).Plan.model_json_schema(),
               'generator_catalog': video_generators.catalog()}
    pk = save_json(store, key(run, 'package.json'), package)
    return {'package': pk, 'gaps': list(session['source']['gaps']), 'library_version': session['library_version'], 'next': 'write out/visual-plan.json then `vw visuals check`'}


def footage_character(outputs):
    """design/77 L42: the operator's confirmed footage character from the media record (camera, support, look, their words), or None for a run recorded before it."""
    media = next((o for o in outputs if o['stage'] == 'media' and o['unit'] is None), None)
    return ((media or {}).get('summary') or {}).get('footage_character') if media else None


def library_version_of(session):
    """design/68 L2: the library a run reads; a session from before the release reads the latest."""
    return session.get('library_version') or library.latest()


def library_pack(store, run, outputs):
    """design/68 L3: every step's library files with their text, for the plugin to write once per step."""
    return library.steps(library_version_of(session_of(store, run, outputs)))


def check(store, run, outputs, document):
    session = session_of(store, run, outputs)
    try:
        plan, warnings = validate_plan(document, session['source']['gaps'], _fps(session))
    except (ValueError, KeyError, TypeError) as exc:
        return {'status': 'rejected', 'error': str(exc)}
    r = routes(plan, _fps(session) or 25)
    pr = prices()
    planned = round(r['images_estimated'] * pr['image_inr'] + r['seconds']['video'] * pr['video_inr_per_s'], 2)   # design/65 B7: the cost against the cap, before anything is paid
    return {'status': 'valid', 'warnings': warnings, 'routes': r, 'plan_digest': digest(plan), 'budget': {'planned_inr': planned, 'cap_inr': cap_of(session)}}   # design/45 10.2


def propose(conn, store, user, run, outputs, document):
    session = session_of(store, run, outputs)
    plan, warnings = guarded(lambda: validate_plan(document, session['source']['gaps'], _fps(session)))
    need(session.get('treatment'), 'Record the treatment first (`vw visuals treatment`).')   # design/65 B6
    for gap in plan['gaps']:   # a route that departs from the recorded treatment needs a new treatment, with the reason
        said = set()
        for e in session['treatment']['gaps']:
            if e['gap_id'] == gap['gap_id']:
                said = set(e['routes']) | ({'still'} if 'footage' in e['routes'] else set())   # a frame shown in the film is a still in the plan
        scenes = gap.get('scenes') or []
        if gap.get('choices'):   # as routes() counts: the recommended choice, else the first
            scenes = next((c for c in gap['choices'] if c['id'] == gap.get('recommended_choice')), gap['choices'][0])['scenes']
        used = {route_of(sh) for sc in scenes for sh in sc['shots']}
        need(used <= said, f"gap {gap['gap_id']}: the plan uses {sorted(used)} but the treatment says {sorted(said)}; record a new treatment with the reason, or change the plan.")
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
    for gid, rv in list((session.get('revisions') or {}).items()):   # design/76: a revision is answered once the gap is proposed changed
        gap = next((g for g in plan['gaps'] if g['gap_id'] == gid), None)
        if not gap or rv.get('digest') != gap_digest(plan, gap):
            session['revisions'].pop(gid)
    save_session(store, run, session)
    return {'version': version, 'plan_digest': identity, 'warnings': warnings, 'routes': routes(plan, _fps(session) or 25), 'gaps': [g['gap_id'] for g in plan['gaps']]}


# ---------- design/65 B7: the cap ----------

def prices():
    s = settings()
    return {'image_inr': float(s.VISUALS_PRICE_IMAGE_INR), 'video_inr_per_s': float(s.VISUALS_PRICE_VIDEO_INR_PER_S)}


def visuals_spend(conn, run):
    """What this film's visuals have cost so far, at the configured prices: every image job and every take job that ran or is running."""
    rows = conn.execute("select provider, status, request from vw2_jobs where run_id=%s and stage='visuals' and provider in ('openai', 'video')", (run['id'],)).fetchall()
    live = [r for r in rows if r['status'] not in ('failed', 'rejected', 'cancelled')]
    pr = prices()
    images = sum(1 for r in live if r['provider'] == 'openai')
    seconds = float(sum(float((r.get('request') or {}).get('duration_seconds') or 0) for r in live if r['provider'] == 'video'))
    return {'images': images, 'take_seconds': seconds, 'spent_inr': round(images * pr['image_inr'] + seconds * pr['video_inr_per_s'], 2), 'prices': pr}


def cap_of(session):
    return float(session.get('cap_inr') or settings().VISUALS_CAP_INR)


def check_cap(conn, run, session, estimate_inr, what):
    """Before any paid call: refuse when the spend so far plus this call would pass the film's cap."""
    spent, cap = visuals_spend(conn, run)['spent_inr'], cap_of(session)
    if spent + float(estimate_inr) > cap + 1e-9:
        raise Problem(409, 'VISUALS_CAP', f"₹{spent:,.0f} spent of ₹{cap:,.0f} on this film's visuals; {what} needs about ₹{float(estimate_inr):,.0f}. "
                                          "Stop and tell the operator the spend; the cap is a setting the builder changes on SK's word (design/74 L26).",
                      spent_inr=spent, cap_inr=cap, estimate_inr=float(estimate_inr))


def budget(conn, store, run, outputs):
    """Spend, cap and what the current plan still needs, in INR."""
    session = session_of(store, run, outputs)
    sp = visuals_spend(conn, run)
    planned = {'images': 0, 'video_seconds': 0.0, 'inr': 0.0}
    if session.get('current'):
        r = routes(current_plan(store, session), _fps(session) or 25)
        planned = {'images': r['images_estimated'], 'video_seconds': r['seconds']['video'],
                   'inr': round(r['images_estimated'] * sp['prices']['image_inr'] + r['seconds']['video'] * sp['prices']['video_inr_per_s'], 2)}
    cap = cap_of(session)
    return {**sp, 'cap_inr': cap, 'left_inr': round(cap - sp['spent_inr'], 2), 'planned': planned}


# ---------- design/65 B6: the treatment as a record ----------

def treatment(store, user, run, outputs, document, quote):
    """One entry per gap: the team's intended visuals cited or departed from, the picture in a line, the routes, the seconds, the images.
    Without the operator's words the document is kept as the draft the visuals page shows; with them it is recorded (the page records the
    draft with the words given there). `propose` is refused without a record and when a route departs from it."""
    session = session_of(store, run, outputs)
    if document is None:
        document = session.get('treatment_draft')
        need(document, 'No treatment draft on this run: send one first (`vw visuals treatment --file out/visual-treatment.json`).')
    entries = (document or {}).get('gaps')
    need(isinstance(entries, list) and entries, 'The treatment is a list of gaps.')
    gaps = session['source']['gaps']
    seen, totals = set(), {'gaps': 0, 'images': 0, 'routes': {}, 'seconds': {}}
    video_seconds = 0.0
    for e in entries:
        need(isinstance(e, dict) and e.get('gap_id') in gaps, f"The treatment names an unknown gap: {(e or {}).get('gap_id')!r}.")
        need(e['gap_id'] not in seen, f"gap {e['gap_id']} appears twice in the treatment.")
        seen.add(e['gap_id'])
        routes_ = list(e.get('routes') or ([e['route']] if e.get('route') else []))
        need(routes_ and all(r in TREATMENT_ROUTES for r in routes_), f"gap {e['gap_id']}: each route is one of {', '.join(TREATMENT_ROUTES)}.")
        for sh in e.get('shots') or []:   # design/74 L25: one named route takes the shots' routes; several named routes must cover every shot
            r = (sh or {}).get('route')
            if r and r in TREATMENT_ROUTES and r not in routes_:
                need(len(routes_) == 1, f"gap {e['gap_id']}: shot {sh.get('id')} uses the route {r!r}, which the entry does not name; name it in routes or change the shot.")
                routes_.append(r)
        e['routes'] = routes_
        need(str(e.get('picture') or '').strip(), f"gap {e['gap_id']}: say the picture in one line.")
        need(isinstance(e.get('seconds'), (int, float)) and e['seconds'] > 0, f"gap {e['gap_id']}: seconds must be a number above zero.")
        need(isinstance(e.get('images'), int) and e['images'] >= 0, f"gap {e['gap_id']}: images must be a whole number.")
        totals['gaps'] += 1
        totals['images'] += e['images']
        first = routes_[0]
        totals['routes'][first] = totals['routes'].get(first, 0) + 1
        totals['seconds'][first] = round(totals['seconds'].get(first, 0.0) + float(e['seconds']), 2)
        if 'video' in routes_:
            video_seconds += float(e['seconds'])
    missing = sorted(set(gaps) - seen)
    need(not missing, 'The treatment covers every gap; missing: ' + ', '.join(missing) + '.')
    pr = prices()
    estimate = round(totals['images'] * pr['image_inr'] + video_seconds * pr['video_inr_per_s'], 2)
    record = {'gaps': entries, 'totals': totals, 'estimate_inr': estimate, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'digest': digest(entries)}
    if not str(quote or '').strip():   # the draft the page shows for approval
        session['treatment_draft'] = record
        save_session(store, run, session)
        return {'draft': True, 'totals': totals, 'estimate_inr': estimate, 'cap_inr': cap_of(session), 'digest': record['digest']}
    session['treatment'] = {**record, 'quote': quote}
    session.pop('treatment_draft', None)
    save_session(store, run, session)
    return {'recorded': True, 'totals': totals, 'estimate_inr': estimate, 'cap_inr': cap_of(session), 'digest': record['digest']}


# ---------- design/65 §8: what the visuals page shows ----------

def page_view(conn, store, run, outputs, code):
    """The page's data in one read of the session (plus the package for the intended visuals): the treatment (draft or record), the plan's gaps and
    shots with their pictures, the references with their image links, the takes, the budget. Links go through the run's file route."""
    def url(k):
        return f'/runs/{code}/file/{k}' if k else None
    try:
        session = session_of(store, run, outputs)
    except Problem:
        return {'state': 'not_prepared'}
    if reconcile(conn, run, session):
        save_session(store, run, session)
    try:
        package = load_json(store, key(run, 'package.json'))
    except Problem:
        package = {}
    plan = current_plan(store, session) if session.get('current') else None
    refs = {}
    for r in session['references'].values():
        refs[r['id']] = {k: r.get(k) for k in ('id', 'name', 'kind', 'element_id', 'status', 'sha256', 'job_id', 'width', 'height')}
        refs[r['id']]['note'] = (r.get('source') or {}).get('note') or ''   # design/73
        refs[r['id']].update(url=url(r.get('key')), prompt=(r.get('generation') or {}).get('prompt'), parents=[p.get('id') for p in (r.get('generation') or {}).get('parents') or []],
                             approval={k: (r.get('approval') or {}).get(k) for k in ('by', 'at', 'quote')} if r.get('approval') else None,
                             rejection={k: (r.get('rejection') or {}).get(k) for k in ('notes', 'quote', 'by', 'at')} if r.get('rejection') else None,   # design/74 L7
                             checklist=(r.get('answer') or {}).get('checklist') if r.get('answer') else None)   # design/74 L6
    takes = {}
    for j in take_jobs(conn, run):
        res = j.get('result') or {}
        takes.setdefault(j['unit'], []).append({'job_id': str(j['id']), 'status': j['status'], 'error': j.get('error'), 'url': url(res.get('key')), 'sha256': res.get('sha256'),
                                                 'duration_s': (res.get('evidence') or {}).get('duration_seconds'), 'timing_matches': (res.get('evidence') or {}).get('timing_matches_placement'),
                                                 'reviews': [{k: rv.get(k) for k in ('decision', 'notes', 'quote', 'by')} for rv in session['reviews'].get(str(j['id']), [])],
                                                 'selected': (session['selections'].get(j['unit']) or {}).get('job_id') == str(j['id']), 'checklist': take_checklist(session, j)})
    gaps = []
    for gid, g in sorted(session['source']['gaps'].items(), key=lambda kv: kv[1].get('start_frame', 0)):
        entry = {'gap_id': gid, **g, 'accepted': gid in session['accepted'], 'recorded': gid in session['recorded_gaps'], 'shots': [], 'choices': None, **_accepted_words(session, gid)}
        if plan:
            gap = next((x for x in plan['gaps'] if x['gap_id'] == gid), None)
            if gap:
                if gap.get('choices'):
                    entry['choices'] = {'options': [{'id': c['id'], 'title': c['title'], 'why': c['why']} for c in gap['choices']], 'recommended': gap.get('recommended_choice'),
                                        'selected': (session['choice_selections'].get(gid) or {}).get('choice_id')}
                try:
                    shots = [sh for sc in chosen_scenes(gap, session['choice_selections'].get(gid)) for sh in sc['shots']]
                except ValueError:
                    shots = []
                for sh in shots:
                    asset = session['assets'].get(sh['id'])
                    binding = session['bindings'].get(sh['id']) or {}
                    entry['shots'].append({'shot_id': sh['id'], 'title': sh.get('title') or '', 'visual_type': sh['visual_type'], 'route': route_of(sh), 'purpose': sh.get('purpose', ''),
                                           'start_frame': sh['start_frame'], 'end_frame': sh['end_frame'], 'states': sh.get('states') or [], 'element_ids': sh.get('element_ids') or [],
                                           'bound': [b['id'] for rows in binding.get('references', {}).values() for b in rows],
                                           'asset': ({'kind': asset['kind'], 'url': url(asset.get('key')), 'states': [{'reference_id': st['reference_id'], 'url': url(st['key']), 'hold_frames': st['hold_frames']} for st in asset.get('states') or []]} if asset else None),
                                           'takes': takes.get(sh['id'], []), 'prepared': sh['id'] in session['preparations']})
        gaps.append(entry)
    sp = visuals_spend(conn, run)
    return {'state': 'prepared', 'fps': session['source'].get('fps'), 'plan_digest': session.get('current'), 'versions': len(session['versions']),
            'treatment': session.get('treatment'), 'treatment_draft': session.get('treatment_draft'), 'intended_visuals': package.get('intended_visuals') or [],
            'elements': [{k: e.get(k) for k in ('id', 'name', 'kind', 'identity', 'requirements', 'required_views')} for e in (plan or {}).get('elements') or []],   # design/73: the page's element sections
            'element_matches': element_matches(plan, package.get('world_evidence')) if plan else {}, 'searches': _searches(session),
            'gaps': gaps, 'references': list(refs.values()), 'budget': {**sp, 'cap_inr': cap_of(session), 'left_inr': round(cap_of(session) - sp['spent_inr'], 2)}}


# ---------- design/65 B2': the graphic sequence ----------

def sequence(store, user, run, outputs, shot_id, reference_ids, quote):
    """An animation shot's states, approved in one call with the operator's words; each state's hash is recorded; the asset holds them for the shot."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    _route_gate(shot, 'animation')
    states = shot.get('states') or []
    need(len(reference_ids) == len(states), f'shot {shot_id} plans {len(states)} states; {len(reference_ids)} references given.')
    need(str(quote or '').strip(), 'The operator reply is required.')
    rows = []
    for rid in reference_ids:
        row = session['references'].get(rid)
        need(row and row.get('status') in ('candidate', 'approved') and row.get('sha256'), f'{rid} is not a candidate or approved reference of this run.')
        rows.append(row)
    warnings = []
    for i, row in enumerate(rows[1:], 2):
        parents = [p.get('id') for p in (row.get('generation') or {}).get('parents') or []]
        if rows[i - 2]['id'] not in parents:
            warnings.append(f"state {i} ({row['id']}) was not generated from state {i - 1} ({rows[i - 2]['id']}); check the drawing is the same")
    stamp = {'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'quote': quote}
    for row in rows:
        row.update(status='approved', approval={**stamp, 'sha256': row['sha256']})
    fps = _fps(session) or Fraction(25)
    total = shot['end_frame'] - shot['start_frame']
    holds = [int(round(float(st['hold_s']) * float(fps))) for st in states]
    holds[-1] += total - sum(holds)   # the rounding lands on the last state so the states fill the shot exactly
    session['assets'][shot_id] = {'kind': 'sequence', 'quote': quote, 'by': user['id'],
                                  'states': [{'reference_id': r['id'], 'key': r['key'], 'sha256': r['sha256'], 'bytes': r.get('bytes'), 'hold_frames': h, 'what_appears': st.get('what_appears', '')}
                                             for r, h, st in zip(rows, holds, states)],
                                  'dissolve_frames': int(round(DISSOLVE_S * float(fps))), 'motion': 'none',
                                  'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame']}}
    session['selections'].pop(shot_id, None)
    save_session(store, run, session)
    return {'shot_id': shot_id, 'kind': 'sequence', 'states': len(rows), 'warnings': warnings}


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
        (session.get('revisions') or {}).pop(gid, None)   # design/76: accepted after all
        _feedback(session, run, user, kind='gap', ident=gid, owner=gid, step=None, verdict='pass', quote=quote, notes='', prompt='', checklist=None, suggestion='', model='', inputs=())   # design/75
    save_session(store, run, session)
    return {'accepted': sorted(session['accepted'])}


def revise_gap(store, user, run, outputs, gap_id, notes, quote):
    """design/76 (L32): the operator sends a gap back with their words; it is not accepted, the words wait for the assistant in status and on the page,
    a feedback record says fix, and the entry clears when the gap is proposed changed or accepted after all."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    gap = next((g for g in plan['gaps'] if g['gap_id'] == gap_id), None)
    need(gap, f'Unknown gap {gap_id}.')
    need((quote or '').strip(), 'The operator reply is required.')
    words = str(notes or '').strip() or str(quote)
    session['accepted'].pop(gap_id, None)
    session.setdefault('revisions', {})[gap_id] = {'notes': words, 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'digest': gap_digest(plan, gap)}
    _feedback(session, run, user, kind='gap', ident=gap_id, owner=gap_id, step=None, verdict='fix', quote=quote, notes=words, prompt='', checklist=None, suggestion='', model='', inputs=())
    save_session(store, run, session)
    return {'gap_id': gap_id, 'revise': True, 'notes': words}


def _accepted_words(session, gid):
    """design/75 (defect 20): the operator's words on a gap's acceptance; design/76: a revision's words while the gap waits for its next version."""
    acc = session['accepted'].get(gid)
    out = {'quote': acc.get('quote') or '', 'by': acc.get('by')} if acc else {}
    rv = (session.get('revisions') or {}).get(gid)
    if rv:
        out['revise'] = {k: rv.get(k) for k in ('notes', 'quote', 'by', 'at')}
    return out


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


# ---------- design/73: reference assets from the footage first, then Google Images ----------

STOP = {'the', 'and', 'with', 'from', 'that', 'this', 'their', 'then', 'into', 'onto', 'over', 'under', 'same', 'exact', 'representative', 'view', 'views', 'front', 'side', 'close'}
KIND_MATCH = {'person': {'person'}, 'animal': {'person', 'other'}, 'object': {'tool', 'material', 'machine', 'vehicle', 'other', 'text'}, 'place': {'structure', 'other'}}


def _words(text):
    return {w for w in re.findall(r'[a-z]{4,}', str(text or '').lower()) if w not in STOP}


def element_matches(plan, world):
    """design/73 R1: where each person, object or place element is seen in the footage, from the clip logs' entities, by word overlap and kind; best first."""
    out = {}
    for e in plan.get('elements') or []:
        if e['kind'] == 'graphic':
            continue
        want = _words(e['name']) | _words(e.get('requirements'))
        hits = {}   # the best entity per clip
        for clip in world or []:
            for ent in clip.get('entities') or []:
                shared = want & (_words(ent.get('name')) | _words(ent.get('description')))
                if not shared:
                    continue
                score = len(shared) + (1 if ent.get('kind') in KIND_MATCH.get(e['kind'], set()) else 0)
                if score > (hits.get(clip['clip']) or {}).get('score', 0):
                    hits[clip['clip']] = {'clip': clip['clip'], 'seconds': ent.get('first_seen_s'), 'entity': ent.get('name'), 'description': ent.get('description'), 'score': score}
        out[e['id']] = sorted(hits.values(), key=lambda h: (-h['score'], str(h['clip'])))
    return out


def fetch_image(url):
    return transfer(url, limit=16 * 1024 * 1024)


def search(store, user, run, outputs, element_id, keywords, quote):
    """design/73 R3: one Google Images search for an element, on the operator's yes; the ten rows kept on the session for the page and the tool."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    need(any(e['id'] == element_id for e in plan['elements']), f'Unknown element {element_id}.')
    need((quote or '').strip(), "The operator's yes to the search is required (the web rule).")
    words = str(keywords or '').split()
    need(2 <= len(words) <= 6, 'Keywords are two to six words: the thing and its place or trade, nothing else (Google Images is not Google search).')   # R6
    rows = apify.search_images(' '.join(words), 10)
    sid = digest({'run': str(run['id']), 'element': element_id, 'keywords': ' '.join(words), 'at': datetime.now(timezone.utc).isoformat()})[:12]
    session.setdefault('searches', {})[sid] = {'search_id': sid, 'element_id': element_id, 'keywords': ' '.join(words), 'quote': quote, 'by': user['id'],
                                               'at': datetime.now(timezone.utc).isoformat(), 'results': rows, 'picked': []}
    save_session(store, run, session)
    return {'search_id': sid, 'element_id': element_id, 'keywords': ' '.join(words), 'results': rows}


def pick(store, user, run, outputs, search_id, picks, quote):
    """design/73 R4: the ticked pictures, in the order ticked, each with its note, become web references of the element with their source."""
    session = session_of(store, run, outputs)
    s = (session.get('searches') or {}).get(search_id)
    need(s, f'Unknown search {search_id}.')
    need((quote or '').strip(), "The operator's words are required.")
    need(isinstance(picks, list) and picks, 'Tick at least one picture.')
    rows = {r['n']: r for r in s['results']}
    chosen = []
    for p in picks:
        n = (p or {}).get('n')
        need(n in rows, f'Picture {n} is not in the search ({len(rows)} pictures).')
        chosen.append((rows[n], str((p or {}).get('note') or '').strip()))
    made = []
    for row, note in chosen:
        png, size = image_bytes(guarded(lambda: fetch_image(row['image_url'])))
        rid = digest({'run': str(run['id']), 'search': search_id, 'n': row['n']})[:32]
        meta = {'element_id': s['element_id'], 'element_kind': next(e['kind'] for e in current_plan(store, session)['elements'] if e['id'] == s['element_id']),
                'name': f"web-{s['element_id']}-{row['n']}", 'kind': 'web', 'subject': row.get('title') or s['keywords'], 'width': size[0], 'height': size[1],
                'source': {'url': row['image_url'], 'page_url': row.get('page_url'), 'selection_reply': quote, 'note': note, 'search_id': search_id, 'n': row['n']}}
        made.append(_store_reference(store, run, session, rid, png, meta))
    s['picked'] = [row['n'] for row, _ in chosen]
    save_session(store, run, session)
    return {'search_id': search_id, 'references': made}


def nothing_fits(store, user, run, outputs, search_id, reason):
    """design/73 R4b (6): none of the ten fits; the reason reaches the assistant as the next search's hint."""
    session = session_of(store, run, outputs)
    s = (session.get('searches') or {}).get(search_id)
    need(s, f'Unknown search {search_id}.')
    need(str(reason or '').strip(), 'Say in one line why nothing fits; it becomes the next search.')
    s['nothing_fits'] = {'reason': str(reason).strip(), 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    return {'search_id': search_id, 'nothing_fits': s['nothing_fits']}


def _searches(session):
    return [{k: v for k, v in s.items() if k != 'results'} | {'results': s.get('results') or []} for s in (session.get('searches') or {}).values()]


def generate_image(conn, store, user, run, outputs, body):
    """Queue an OpenAI image job (paid, informed). The worker stores the PNG and creates the candidate reference."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    element = next((e for e in plan['elements'] if e['id'] == body['element_id']), None)
    need(element, 'Reference must identify an element in the current plan.')
    need(body['kind'] in ('isolated', 'sheet', 'keyframe', 'state'), 'Generated references are isolated, sheet, keyframe or state.')
    parents = [session['references'].get(p) for p in body.get('parents') or []]
    for p in parents:   # design/71 P6 (the server check, design/74 L7): a retry starts from an approved picture, never from a rejected one
        if p and p.get('status') == 'rejected':
            need(False, f"{p['id']} was rejected: make the next {'state from the last approved state' if body['kind'] == 'state' else 'end image from the approved start, not from the candidate chain'}.")
    if body['kind'] == 'state':   # design/65: a state is made from the previous state, which is approved only when the whole sequence is
        need(len(parents) == 1, 'A state is generated from the previous state: give one parent.')
        need(parents[0] and parents[0]['status'] in ('approved', 'candidate'), 'The parent must be a candidate or approved reference of this run.')
    else:   # design/66 C3: an end keyframe is made from the start keyframe before either is approved, so the pair is approved together
        need(all(p and (p['status'] == 'approved' or (body['kind'] == 'keyframe' and p['kind'] == 'keyframe' and p['status'] == 'candidate')) for p in parents),
             'Parents must be approved references of this run (an end keyframe may be made from a candidate start keyframe).')
    library.check_prompt(body['prompt'])   # design/71 F2: no logo, no model name, no size, no resolution in a prompt (a ValueError; the API wraps this call in guarded())
    if body['kind'] == 'keyframe':   # design/67 D: an end keyframe is edited from the start keyframe and the start's own references, so identity is held by its sources
        starts = [p for p in parents if p['kind'] == 'keyframe']
        need(not starts or re.search(r'\bimage 1\b', body['prompt'], re.I),
             'An end image names its pictures: the prompt names "Image 1" as the start image (images 2 onward are its identity sheets, sent by the server).')   # design/71 P1
        for start in starts:
            for inherited in (start.get('generation') or {}).get('parents') or []:
                row = session['references'].get(inherited.get('id'))
                if row and row['status'] == 'approved' and all(p['id'] != row['id'] for p in parents):
                    parents.append(row)
    need(len(parents) <= MAX_INPUTS, f'{len(parents)} input pictures after the start\'s own references are added; GPT Image takes at most {MAX_INPUTS}. Name fewer.')   # design/71 P2
    if body['kind'] == 'keyframe':
        _keyframe_gates(session, plan, body, parents)   # design/77 L35, L38, L41
    answer = body.get('answer')
    if answer is not None:   # design/68 L5: the library's answer form travels with the prompt
        try:
            library.check_answer(answer, body['prompt'])
        except ValueError as exc:
            need(False, str(exc))
    check_cap(conn, run, session, prices()['image_inr'], 'one image')   # design/65 B7
    op = 'edit' if parents else 'generate'
    ref_id = digest({'run': str(run['id']), 'request': body['request_id']})[:32]
    frame = default_aspect(next((o['summary'] for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None), {})   # design/71 P3: the size follows the brief's frame
    first = parents[0] if parents and parents[0].get('kind') in ('keyframe', 'frame') else None   # an edit of a keyframe or a frame keeps that picture's size when GPT Image accepts it
    size = body.get('size') or (library.edit_size(first.get('width'), first.get('height'), frame) if first else library.default_size(frame))
    request = {'kind': 'image', 'op': op, 'model': body.get('model') or IMAGE_MODELS[op], 'prompt': body['prompt'], 'size': size,
               'quality': body.get('quality') or 'high', 'parents': [{'id': p['id'], 'key': p['key'], 'sha256': p['sha256']} for p in parents],
               'reference': {'id': ref_id, 'element_id': body['element_id'], 'element_kind': element['kind'], 'name': body['name'], 'kind': body['kind'], 'subject': body['subject']}}
    row = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,'openai',%s,%s) returning id",
                       (run['id'], ref_id, Jsonb(request), body['request_id'])).fetchone()
    session['references'][ref_id] = {**request['reference'], 'id': ref_id, 'status': 'generating', 'job_id': str(row['id']), 'generation': {k: request[k] for k in ('op', 'model', 'prompt', 'size', 'quality', 'parents')},
                                     **({'answer': answer} if answer is not None else {})}
    save_session(store, run, session)
    return {'reference_id': ref_id, 'job_id': str(row['id']), 'model': request['model'], 'op': op}


CAMERA_MOVE = re.compile(r"(camera(?![^.;]{0,40}?\b(does not|doesn't|never|no|without|unmoved|stays|static|fixed|locked)\b)[^.;]{0,40}?\b(push|drift|dolly|zoom|pan|tilt|track|mov)\w*)"
                         r"|\b(push[- ]in|pull[- ]out|dolly|zoom\w*|tracking shot|pan(ning)? (left|right)|tilt(ing)? (up|down))\b", re.I)


def _shots_with(plan, session, element_id):
    """The accepted shots of the current plan that name an element, as (gap, shot) pairs."""
    out = []
    for gap in plan['gaps']:
        if gap.get('choices') and not session['choice_selections'].get(gap['gap_id']):
            continue
        acc = session['accepted'].get(gap['gap_id'])
        if not acc or acc['digest'] != gap_digest(plan, gap):
            continue
        for scene in chosen_scenes(gap, session['choice_selections'].get(gap['gap_id'])):
            for sh in scene['shots']:
                if element_id in (sh.get('element_ids') or []):
                    out.append((gap, sh))
    return out


def _keyframe_gates(session, plan, body, parents):
    """design/77: L35 a start keyframe for a video shot's element waits until a shot's packet was read (bind, then packet); L38 an end keyframe
    never moves the camera; L41 a shot that shows a client's own material (an exact object element with approved footage frames) sends one of
    those frames as a parent."""
    pairs = _shots_with(plan, session, body['element_id'])
    end = any(p['kind'] == 'keyframe' for p in parents)
    video = [(gap, sh) for gap, sh in pairs if sh['visual_type'] == 'video']
    if video and not end:   # L35
        read = [sh['id'] for gap, sh in video if (session['bindings'].get(sh['id']) or {}).get('packet_read_at') and session['bindings'][sh['id']].get('gap_digest') == gap_digest(plan, gap)]
        first = video[0][1]['id']
        need(read, f"Bind the shot and read its packet before composing its start image (`vw visuals bind --shot {first} …`, then `vw visuals packet --shot {first}`): "
                   "the packet carries the pair instructions and the library's job form.")
    if end:   # L38
        m = CAMERA_MOVE.search(body['prompt'])
        if m:
            need(False, f"The end image moves the camera ({m.group(0).strip()!r}): the camera does not move between the start and the end; show the action's visible result instead.")
    elements = {e['id']: e for e in plan['elements']}
    parent_frames = {p['element_id'] for p in parents if p.get('kind') == 'frame'}
    for gap, sh in pairs:   # L41
        for eid in sh.get('element_ids') or []:
            e = elements.get(eid)
            if not e or eid == body['element_id'] or e['kind'] != 'object' or e['identity'] != 'exact':
                continue
            frames = [r for r in session['references'].values() if r.get('element_id') == eid and r.get('kind') == 'frame' and r.get('status') == 'approved']
            need(not frames or eid in parent_frames, f"{eid} is the client's own: send one of its approved footage frames as a parent, named by number as the material reference "
                                                     f"({', '.join(r['id'][:8] for r in frames)}).")


def approve_reference(store, user, run, outputs, ref_id, sha256, quote):
    session = session_of(store, run, outputs)
    row = session['references'].get(ref_id)
    need(row and row['status'] in ('candidate', 'approved'), 'Reference is not a candidate.')
    if row['sha256'] != sha256:
        raise Problem(409, 'REFERENCE_MISMATCH', 'Approve the exact stored image hash after viewing it.')
    need((quote or '').strip(), 'The operator reply is required.')
    row.update(status='approved', approval={'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'sha256': sha256, 'quote': quote})
    _feedback_image(session, run, user, row, 'pass', quote, '')
    save_session(store, run, session)
    return row


def reject_reference(store, user, run, outputs, ref_id, notes, quote):
    """design/74 L7: a picture rejected with the operator's words; it is never approved, bound, held or named as a parent afterwards."""
    session = session_of(store, run, outputs)
    row = session['references'].get(ref_id)
    need(row and row['status'] in ('candidate', 'approved'), f"Reference {ref_id} is not a candidate or approved picture (it is {(row or {}).get('status') or 'unknown'}); only those can be rejected.")
    need((quote or '').strip(), 'The operator reply is required.')
    row.update(status='rejected', rejection={'notes': str(notes or '').strip() or str(quote), 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()})
    _feedback_image(session, run, user, row, 'reject', quote, row['rejection']['notes'])
    save_session(store, run, session)
    return row


# ---------- design/74 L7: the feedback record, in the library's shape (record-template.videowizard.yaml) ----------

def _step_of_reference(session, row):
    kind = row.get('kind')
    if kind in ('isolated', 'sheet'):
        return 'reference'
    if kind == 'state':
        return 'state'
    if kind == 'keyframe':
        parents = [(session['references'].get(p.get('id')) or {}) for p in (row.get('generation') or {}).get('parents') or []]
        return 'end' if any(p.get('kind') == 'keyframe' for p in parents) else 'start'
    return 'frame'


def _feedback(session, run, user, *, kind, ident, owner, step, verdict, quote, notes, prompt, checklist, suggestion, model, inputs):
    spec = library.STEPS.get(step) or {}
    session.setdefault('feedback', []).append({
        'app': 'videowizard', 'library_version': library_version_of(session), 'run_code': run.get('code'), 'job_id': f"{run.get('code')}-{owner}-{str(ident)[:8]}",
        'kind': kind, 'id': str(ident), 'playbook': spec.get('playbook'), 'task': spec.get('task'), 'model': model or '', 'inputs': list(inputs),
        'prompt': prompt or '', 'checklist': list(checklist or []), 'verdict': verdict, 'verdict_by': 'person', 'quote': quote,
        'what_went_wrong': notes if verdict in ('reject', 'fix') else '', 'suggestion': suggestion or '', 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()})


def _feedback_image(session, run, user, row, verdict, quote, notes):
    gen, answer = row.get('generation') or {}, row.get('answer') or {}
    inputs = [{'picture_id': p.get('id'), 'tag': 'scene' if (session['references'].get(p.get('id')) or {}).get('kind') == 'frame' else 'approved'} for p in gen.get('parents') or []]
    _feedback(session, run, user, kind='image', ident=row['id'], owner=row.get('element_id') or '', step=_step_of_reference(session, row), verdict=verdict, quote=quote, notes=notes,
              prompt=gen.get('prompt') or '', checklist=answer.get('checklist'), suggestion=answer.get('suggestion'), model=gen.get('model'), inputs=inputs)


def _feedback_take(session, run, user, job, prep, verdict, quote, notes):
    answer = (prep or {}).get('answer') or {}
    inputs = [{'picture_id': (prep or {}).get(role, {}).get('reference_id'), 'tag': tag} for role, tag in (('start_image', 'first-frame'), ('end_image', 'last-frame')) if (prep or {}).get(role)]
    _feedback(session, run, user, kind='take', ident=job['id'], owner=job['unit'], step='take', verdict=verdict, quote=quote, notes=notes,
              prompt=(prep or {}).get('motion_prompt') or '', checklist=answer.get('checklist'), suggestion=answer.get('suggestion'), model=(prep or {}).get('model'), inputs=inputs)


def _prep_of(store, job):
    try:
        return load_json(store, (job.get('request') or {})['request_key'])
    except (KeyError, Problem):
        return {}


def feedback_yaml(records):
    """The records as YAML text, by hand (no yaml dependency): a list of mappings; a checklist line is 'check: pass_when (weight)'."""
    def scalar(v):
        if v is None:
            return 'null'
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if isinstance(v, (int, float)):
            return str(v)
        s = str(v)
        return s if s and re.fullmatch(r'[A-Za-z0-9_./-]+', s) else json.dumps(s, ensure_ascii=False)

    def emit(v, pad):
        out = []
        if isinstance(v, dict):
            for k, val in v.items():
                if isinstance(val, (dict, list)):
                    out += [f'{pad}{k}:'] + emit(val, pad + '  ') if val else [f'{pad}{k}: ' + ('[]' if isinstance(val, list) else '{}')]
                else:
                    out.append(f'{pad}{k}: {scalar(val)}')
        else:
            for item in v:
                if isinstance(item, dict):
                    sub = emit(item, pad + '  ')
                    out += [f'{pad}- ' + sub[0].lstrip()] + sub[1:]
                else:
                    out.append(f'{pad}- {scalar(item)}')
        return out
    rows = [{**r, 'checklist': [{'line': f"{c.get('check')}: {c.get('pass_when')} ({c.get('weight')})"} for c in r.get('checklist') or []]} for r in records]
    return '\n'.join(emit(rows, '')) + '\n'


def feedback(store, run, outputs):
    session = session_of(store, run, outputs)
    records = session.get('feedback') or []
    return {'records': len(records), 'yaml': feedback_yaml(records)}


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


def packet(store, run, outputs, shot_id, session=None, card=None, rules=()):
    session = session or session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    binding = session['bindings'].get(shot_id)
    need(binding and binding['gap_digest'] == gap_digest(plan, gap), 'Bind references for this shot under the current accepted plan.')
    if not binding.get('packet_read_at'):   # design/77 L35: the start image waits for this
        binding['packet_read_at'] = datetime.now(timezone.utc).isoformat()
        save_session(store, run, session)
    refs = []
    for eid, rows in binding['references'].items():
        for b in rows:
            row = session['references'][b['id']]
            need(row['status'] == 'approved' and row['sha256'] == b['sha256'], 'A bound reference changed or lost approval.')
            refs.append({'element_id': eid, 'reference_id': b['id'], 'sha256': b['sha256'], 'key': row['key'], 'subject': row['subject'], 'kind': row.get('kind'),
                         'note': (row.get('source') or {}).get('note') or '',   # design/73 R4a: the operator's note on a picked picture becomes a keep or avoid line
                         **({'subject_selector': b['subject_selector']} if 'subject_selector' in b else {})})
    generator = session['generator_choices'].get(shot_id) or video_generators.DEFAULT
    start_instruction = ('Write the start prompt and the end prompt together before generating either. Compose the start for the whole segment: every visible subject, '
                         'including secondary/background subjects, in its start state in the named scene layout, what the motion heads for already in frame, room in the frame '
                         'for the move, nothing the end state needs cut off or hidden, nothing placed where the end would have to remove it. Keep landmark-relative locations; '
                         'the camera only changes their screen projection. A boundary picture is shared only within one continuous shot, same place and framing: the end image '
                         'of one segment is the start of the next there; a cut starts a new pair with its own two images. Name one human-scale anchor against a named landmark '
                         '(a person beside a doorway, a hand on a course) so the scale is fixed; the landmarks are listed under scene.landmarks.')   # design/67 B; design/74 L24; design/77 L39
    end_instruction = ('Make the end image from the approved start image as its parent; the server sends the start\'s own references with it. Show every subject in its end state '
                       'as the plan gives it: its position against its landmark and its side of the frame, its facing, its pose, what it holds, how far the work has gone; for an '
                       'acting subject the result of its last beat. Name the positions in words. Change nothing else: the same framing, camera, light, people and props. Keep in '
                       'frame whatever the motion heads for. Image 1 is the start image; images 2 onward are its identity sheets, sent by the server: take identity from them, '
                       'nothing else. The camera does not move between the two images: the same framing, lens and position. The end shows the action\'s visible result, a '
                       'different pose or state from the start, never the same frozen pose.')   # design/67 C; design/71 P1; design/77 L38
    prompt = {'foundation': plan['foundation'], 'scene': {k: v for k, v in scene.items() if k != 'shots'}, 'shot': shot, 'references': refs,
              'sequence_rules': plan.get('sequence_rules', []), 'elements': [e for e in plan['elements'] if e['id'] in shot['element_ids']],
              'start_image_instruction': start_instruction, 'image_instruction': start_instruction,   # the old name answers for one release (design/67 A)
              'end_image_instruction': end_instruction,
              'video_instruction': 'Read the actual accepted starting image before writing movement. For EACH subject, follow the ordered beats, targets, paths, contacts, object responses and final progress. Keep non-acting subjects where they are.',
              'checks': ['Treatment and narrated meaning', 'All visible subjects accounted for', 'World-relative layout and scale', 'Secondary action progression', 'Reference identity', 'Boundary continuity', 'Exact placement duration'],
              'footage_character': footage_character(outputs),   # design/77 L42
              'provider': {k: generator[k] for k in ('provider', 'model')}}
    identity = digest(prompt)   # the composition only: the library block below carries the card and the rules, which must not make a prepared take stale
    brief = next((o['summary'] for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None)
    steps_ = library.steps_of(shot)   # design/68 L3: the library beside the three instructions; the texts are in work/visuals/library/, written at prepare
    prompt['library'] = {'version': library_version_of(session),
                         'steps': [{'step': st, 'task': library.STEPS[st]['task'], 'playbook': library.STEPS[st]['playbook'], 'files': library.step_files(st, generator)} for st in steps_],
                         'job_forms': {st: library.job_form(st, run=run, plan=plan, gap=gap, scene=scene, shot=shot, refs=refs, generator=generator, brief=brief, card=card, rules=list(rules or []),
                                                            fps=float(Fraction(session['source']['fps']))) for st in steps_}}
    return {'plan_digest': session['current'], 'gap_id': gap['gap_id'], 'shot_id': shot_id, 'preparation_digest': identity, 'preparation': prompt,
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


def _route_gate(shot, wanted):
    """design/65 B2', B3: a video shot takes a take, a still shot a still, an animation shot a graphic sequence."""
    vt = shot['visual_type']
    if vt == wanted or (wanted == 'still' and vt in STILL_TYPES):
        return
    takes = {'video': 'a take (`vw visuals prepare-take`)', 'animation': 'a graphic sequence (`vw visuals sequence`)'}.get(vt, 'a still (`vw visuals still`)')
    article = 'an' if vt in ('animation', 'image') else 'a'
    need(False, f"shot {shot['id']} is {article} {vt} shot: it takes {takes}, not " + {'video': 'a take', 'still': 'a still', 'animation': 'a sequence'}[wanted] + '.')


def prepare_take(store, user, run, outputs, body):
    session = session_of(store, run, outputs)
    _, _, _, planned = guarded(lambda: locate(store, session, body['shot_id']))
    _route_gate(planned, 'video')
    need(body.get('start_image'), 'A start image is required.')
    need(body.get('end_image'), 'Every take has a start and an end image: generate the end from the start (`vw visuals image --kind keyframe --parents <start>`), '
                                'approve both, then `--start R --end R2`.')   # design/66 C2
    need(body['start_image'] != body['end_image'], 'The start and end images are distinct pictures: the end is the start one small action further on.')
    library.check_prompt(body['motion_prompt'])   # design/71 F2 (a ValueError: the API wraps this call in guarded())
    answer = body.get('answer')
    if answer is not None:   # design/68 L5
        try:
            library.check_answer(answer, body['motion_prompt'])
        except ValueError as exc:
            need(False, str(exc))
    base = packet(store, run, outputs, body['shot_id'], session)
    shot = base['preparation']['shot']
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
        rid = body[role]
        row = session['references'].get(rid)
        need(row and row['status'] == 'approved', f'{role} must be an approved reference.')
        images[role] = {'reference_id': rid, 'sha256': row['sha256'], 'key': row['key'], 'mime_type': 'image/png', 'width': row.get('width'), 'height': row.get('height')}
    s, e = images['start_image'], images['end_image']
    if all((s['width'], s['height'], e['width'], e['height'])):   # design/71 P3: the pair shares its aspect ratio (a 1920x1080 frame and a 1536x864 edit both pass)
        a, b = s['width'] / s['height'], e['width'] / e['height']
        need(abs(a - b) <= 0.01 * a, f"The start ({s['width']}x{s['height']}) and the end ({e['width']}x{e['height']}) differ in aspect ratio; "
                                     "generate the end from the start at the start's own size, or pick a start of the film's frame.")
    record = {'contract': 'videowizard-video-request-v1', 'run_id': str(run['id']), 'shot_id': body['shot_id'], 'plan_digest': base['plan_digest'],
              'base_preparation_digest': base['preparation_digest'], 'motion_prompt': body['motion_prompt'], 'subject_reconciliation': body['subject_reconciliation'],
              'continuity_notes': body.get('continuity_notes') or '', 'duration_seconds': int(duration),
              'aspect_ratio': default_aspect(next((o['summary'] for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None), body),   # design/53 L7
              'resolution': body.get('resolution') or ('720p' if selected['model'] != video_generators.CATALOG[1]['model'] else None),
              **images, 'provider': selected['provider'], 'model': selected['model'],
              'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame'], 'film_fps': str(fps), 'duration_seconds': str(exact), 'exact_seconds': float(exact)},
              'generated_audio_policy': 'retain original output; never replace narration automatically', **({'answer': answer} if answer is not None else {})}
    record['effective_prompt'] = motion_text(record)
    identity = digest(record)
    save_json(store, key(run, f'takes/{identity}.request.json'), record)
    session['preparations'][body['shot_id']] = {'preparation_id': identity, 'key': key(run, f'takes/{identity}.request.json'),
                                                **({'checklist': answer.get('checklist') or []} if answer is not None else {})}   # design/74 L6
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
    seconds = int(request.get('duration_seconds') or 0)
    check_cap(conn, run, session, seconds * prices()['video_inr_per_s'], f'a {seconds} s take')   # design/65 B7
    row = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,'video',%s, gen_random_uuid()) returning id",
                       (run['id'], shot_id, Jsonb({'kind': 'take', 'preparation_id': prep['preparation_id'], 'request_key': prep['key'], 'provider': request['provider'], 'model': request['model'],
                                                   'duration_seconds': seconds}))).fetchone()
    return {'job_id': str(row['id']), 'shot_id': shot_id, 'provider': request['provider'], 'model': request['model']}


def take_checklist(session, job):
    """design/74 L6: the checklist of the preparation this take was made from, when it is still the shot's current preparation."""
    prep = session['preparations'].get(job.get('unit')) or {}
    return prep.get('checklist') if prep.get('preparation_id') == (job.get('request') or {}).get('preparation_id') else None


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
    if decision == 'rejected':   # design/74 L7
        _feedback_take(session, run, user, job, _prep_of(store, job), 'reject', quote, notes)
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
    _feedback_take(session, run, user, job, prep, 'pass', quote, '')   # design/74 L7
    save_session(store, run, session)
    return session['selections'][job['unit']]


def still_from_reference(store, user, run, outputs, shot_id, reference_id, quote):
    """design/45 10.3: an approved reference becomes a still shot's asset; no download and upload."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    _route_gate(shot, 'still')
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
        entry = {'gap_id': gid, **g, 'accepted': gid in session['accepted'], 'recorded': gid in session['recorded_gaps'], 'shots': [], **_accepted_words(session, gid)}
        if plan and gid in session['accepted']:
            for s in shots_of(plan, session, gid):
                entry['shots'].append({'shot_id': s['id'], 'visual_type': s['visual_type'], 'bound': s['id'] in session['bindings'], 'prepared': s['id'] in session['preparations'],
                                       'selected': s['id'] in session['selections'], 'asset': s['id'] in session['assets']})
        gaps.append(entry)
    refs = [{k: r.get(k) for k in ('id', 'name', 'kind', 'element_id', 'status', 'sha256', 'job_id')} for r in session['references'].values()]
    jobs_ = [{**{k: j[k] for k in ('id', 'unit', 'provider', 'status', 'error', 'cost')}, 'checklist': take_checklist(session, j)} for j in take_jobs(conn, run)]   # design/74 L6
    t = session.get('treatment')
    sp = visuals_spend(conn, run)
    return {'state': 'prepared', 'plan_digest': session.get('current'), 'versions': len(session['versions']), 'gaps': gaps, 'references': refs, 'jobs': jobs_,
            'searches': _searches(session),   # design/73: the searches, their picks and any "nothing fits" reason, for the assistant
            'treatment': ({k: t[k] for k in ('totals', 'estimate_inr', 'quote', 'by', 'at', 'digest')} if t else None),   # design/65 B6
            'budget': {**sp, 'cap_inr': cap_of(session), 'left_inr': round(cap_of(session) - sp['spent_inr'], 2)}}      # design/65 B7


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


def boundary_of(request):
    """design/71 P4: the take's start and end picture ids, kept on the gap record so assembly sees where two takes share one."""
    return {'start_image': (request.get('start_image') or {}).get('reference_id'), 'end_image': (request.get('end_image') or {}).get('reference_id')}


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
            job = conn.execute("select result, cost, request from vw2_jobs where id=%s", (sel['job_id'],)).fetchone()
            boundary = {}
            if job and (job.get('request') or {}).get('request_key'):
                try:
                    boundary = {'boundary': boundary_of(load_json(store, job['request']['request_key']))}
                except Problem:
                    boundary = {}
            files.append({'name': f"{s['id']}.mp4", 'key': sel['take']['key'], 'sha256': sel['take']['sha256'], 'bytes': sel['take']['bytes'], 'location': 'storage', 'receipt': True})
            jobs.record_file(conn, run['id'], STAGE, sel['take']['key'], f"{s['id']}.mp4", sel['take']['sha256'], sel['take']['bytes'], 'video/mp4')
            if job and job['cost']:
                cost.append(job['cost'])
            ev = (job['result'] or {}).get('evidence', {}) if job else {}
            media = ({'kind': 'movie', 'duration_s': ev.get('duration_seconds'), 'fps': ev.get('fps'), 'width': ev.get('width'), 'height': ev.get('height'),
                      'color_transfer': ev.get('color_transfer'), 'color_primaries': ev.get('color_primaries'), 'rotation_deg': ev.get('rotation_deg') or 0, 'issues': ev['issues']}
                     if 'issues' in ev else None)   # design/46 11.2: assembly reads this instead of downloading the take
            shots.append({'shot_id': s['id'], 'source': 'take', 'job_id': sel['job_id'], 'placement': {'start_frame': s['start_frame'], 'end_frame': s['end_frame']},
                          'duration_s': ev.get('duration_seconds'), 'timing_matches_placement': ev.get('timing_matches_placement'), **({'media': media} if media else {}), **boundary})
        elif asset['kind'] == 'sequence':   # design/65: one file per state; assembly plays them as a build
            media_states = []
            for i, st in enumerate(asset['states'], 1):
                name = f"{s['id']}-state{i}.png"
                files.append({'name': name, 'key': st['key'], 'sha256': st['sha256'], 'bytes': st.get('bytes'), 'location': 'storage', 'receipt': True})
                jobs.record_file(conn, run['id'], STAGE, st['key'], name, st['sha256'], st.get('bytes') or 0, 'image/png')
                media_states.append({'name': name, 'key': st['key'], 'sha256': st['sha256'], 'hold_frames': st['hold_frames']})
            shots.append({'shot_id': s['id'], 'source': 'asset', 'kind': 'sequence', 'placement': asset['placement'],
                          'media': {'kind': 'sequence', 'states': media_states, 'dissolve_frames': asset['dissolve_frames'], 'motion': asset.get('motion') or 'none'}})
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
