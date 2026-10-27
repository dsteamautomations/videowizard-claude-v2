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
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from io import BytesIO
from pathlib import Path

from psycopg.types.json import Jsonb

from . import apify, core, image_check, jobs, library, video_generators
from . import footage as FM   # design/88
from .config import settings
from .errors import Problem
from .planning.digest import digest
from .storage import storage
from .video_providers import motion_text, transfer
from .visual_contract import FROZEN_SHARE, GRAPHIC_TYPES, NEXT_RELEASE, STILL_TYPES, chosen_scenes, gap_digest, need, route_of, routes, validate_plan, note_free_elements, note_free_scene

STAGE = 'visuals'
IMAGE_MODELS = {'generate': 'gpt-image-2.5-flare-2026-09-08', 'edit': 'gpt-image-2.5-sunburst-2026-09-08'}   # design/82 U4: pinned snapshots (API reference, 22 Oct 2026)
REF_KINDS = ('frame', 'supplied', 'web', 'isolated', 'sheet', 'keyframe', 'state', 'style')   # design/65: a state of a graphic sequence, generated from the previous state
TREATMENT_ROUTES = ('footage', 'still', 'graphic_sequence', 'video')
DISSOLVE_S = 0.5   # between the states of a graphic sequence
MAX_INPUTS = 16    # design/71 P2: GPT Image's limit on input pictures (the library's fact sheet A5)


def said(quote, what, user):
    """design/99 C2: a click is the operator's verdict; their words are kept when given, else the record says who did what."""
    return str(quote or '').strip() or f"{what} by {user.get('name') or user.get('id')}"


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
            'reviews': {}, 'selections': {}, 'assets': {}, 'recorded_gaps': {}, 'repeat_rules': 'refuse'}   # design/89: a session begun before batch 1 is warned instead


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
    world, logs = [], {}
    for o in outputs:
        if o['stage'] == 'analysis' and not o['summary'].get('excluded'):
            ref = next((f for f in o['files'] if f['name'].endswith('.evidence.json')), None)
            if ref:
                doc = load_json(store, ref['key'])
                if doc.get('contract_version') == 'clip-log-v1':
                    log = doc['log']
                    logs[o['unit']] = log   # design/88: movement and contrast per clip
                    world.append({'clip': o['unit'], 'entities': log.get('entities'), 'unavailable_or_uncertain': log.get('unavailable_or_uncertain'),
                                  'landmarks': sorted({l for s in log.get('sub_clips') or [] for l in (s.get('continuity_and_story') or {}).get('world_landmarks_and_props', [])})})
                else:
                    ev = doc['evidence']
                    world.append({'clip': o['unit'], 'world_markers': ev.get('world_markers'), 'evidence_limits': ev.get('evidence_limits')})
    media = next((o for o in outputs if o['stage'] == 'media' and o['unit'] is None), None)   # design/88: measured, not asked
    session['footage_measured'] = FM.measure(((media or {}).get('summary') or {}).get('clips') or [], logs)
    session['clip_safe_zoom'] = {cid: float(log.get('max_safe_zoom_limit') or 1.0) for cid, log in logs.items()}   # design/89 H4: how far a reuse may be cropped
    if 'footage_correction' not in session:   # F6: the answer recorded at the media step before design/88 stands as the correction
        old = footage_character(outputs)
        if old:
            session['footage_correction'] = {**{k: old.get(k) for k in ('camera', 'support', 'look', 'quote')}, 'from': 'the media step'}
    session['footage'] = FM.apply_correction(session['footage_measured'], session.get('footage_correction'))
    session['gap_neighbours'] = gap_neighbours(store, outputs)   # F3: the clip before and after each gap
    session['first_cut_events'] = first_cut_events(store, outputs)   # design/89 H1, finding 9: read once here, not on every placement
    for gid, timing in gap_timing(store, run, session['source']['gaps'], session['source'].get('fps') or 25).items():   # design/89 A1
        session['source']['gaps'][gid]['timing'] = timing
    save_session(store, run, session)
    package = {'source': session['source'], 'prompt': procedure.get('prompt') or '', 'steps': procedure.get('steps') or [],
               'brief': ({**brief['summary'], 'effective_rules': core.effective_rules(conn, run, outputs)} if brief else None),   # design/37 2.7
               'footage_character': footage_view(session, outputs),   # design/88: measured per clip; the operator's correction wins; the texture comes from this
               'script_digest': script['summary'].get('content_digest') if script else None,
               'intended_visuals': (intake['summary'].get('intended_visuals') if intake else None) or [],   # design/65 S3: the team's pictures per scene
               'world_evidence': world, 'plan_schema': __import__('app.visual_contract', fromlist=['Plan']).Plan.model_json_schema(),
               'generator_catalog': video_generators.catalog()}
    session['intended_visuals'] = package['intended_visuals']   # design/86 K7: the packet reads them from the session
    save_session(store, run, session)
    pk = save_json(store, key(run, 'package.json'), package)
    return {'package': pk, 'gaps': list(session['source']['gaps']), 'library_version': session['library_version'], 'footage': (footage_view(session, outputs) or {}).get('line'),
            'next': 'write out/visual-plan.json then `vw visuals check`'}


def gap_timing(store, run, gaps, fps):
    """design/89 A1: each gap's narration as timed sentences (seconds from the gap's start and in the film) and its words (film frames), with the
    sentence before and after. Read from the options package, in film time with the approved pauses already in; a run without one gets none."""
    try:
        from .stage2 import stage as S2
        nar = (S2._package(store, S2.session_of(store, run)).get('narration') or {})
    except (Problem, KeyError, TypeError, ValueError):
        return {}
    words, sents = nar.get('words') or [], nar.get('sentences') or []
    if not words:
        return {}
    f = float(Fraction(str(fps)))
    out = {}
    for gid, g in gaps.items():
        a, b = g['start_frame'], g['end_frame']
        before = next((s for s in reversed(sents) if s['end_frame'] <= a), None)
        after = next((s for s in sents if s['start_frame'] >= b), None)
        out[gid] = {'sentences': [{'text': s['text'], 'start_s': round((s['start_frame'] - a) / f, 2), 'end_s': round((s['end_frame'] - a) / f, 2),
                                   'film_start_s': round(s['start_frame'] / f, 2), 'film_end_s': round(s['end_frame'] / f, 2), 'whole': a <= s['start_frame'] and s['end_frame'] <= b}
                                  for s in sents if s['end_frame'] > a and s['start_frame'] < b],
                    'words': [{'text': w['text'], 'start_frame': w['start_frame'], 'end_frame': w['end_frame']} for w in words if a <= w['start_frame'] < b],
                    'before': before['text'] if before else None, 'after': after['text'] if after else None}
    return out


def ensure_timing(store, run, session):
    """design/89 A1: a session prepared before batch 1 gets its gaps' timing when the check, the packet or the page first needs it. True when it changed."""
    gaps = session['source']['gaps']
    if all('timing' in g for g in gaps.values()):
        return False
    found = gap_timing(store, run, gaps, session['source'].get('fps') or 25)
    for gid, timing in found.items():
        gaps[gid]['timing'] = timing
    return bool(found)


def _rule(session, ok, message, warns):
    """design/89 H2-H5: refused in a visuals session begun on batch 1 or later; in one begun before, warned and kept with the picture (SK: a run in progress is warned for one release first)."""
    if ok:
        return
    if session.get('repeat_rules') == 'refuse':
        need(False, message)
    warns.append(message)


def film_frames(outputs):
    """design/89 B4: the film's length, from the first cut (or the master)."""
    o = next((o for o in outputs if o['stage'] in ('first_cut', 'master') and o['unit'] is None and (o.get('summary') or {}).get('duration_frames')), None)
    return o['summary']['duration_frames'] if o else None


def first_cut_events(store, outputs):
    """The master's picture events, the fields the ledger needs."""
    master = next((o for o in outputs if o['stage'] == 'master' and o['unit'] is None), None)
    ref = next((f for f in (master or {}).get('files') or [] if f['name'].endswith('.json')), None)
    try:
        events = load_json(store, ref['key']).get('events') or [] if ref else []
    except Problem:
        return []
    keys = ('sub_clip_id', 'source_in_frame', 'source_out_frame', 'timeline_in_frame', 'timeline_out_frame')
    return [{k: ev[k] for k in keys} for ev in events if ev.get('kind') == 'event' and all(k in ev for k in keys)]


def gap_neighbours(store, outputs):
    """design/88 F3: for each gap of the master, the clip just before it and just after it on the timeline (a sub-clip id is clip:sub)."""
    master = next((o for o in outputs if o['stage'] == 'master' and o['unit'] is None), None)
    ref = next((f for f in (master or {}).get('files') or [] if f['name'].endswith('.json')), None)
    if not ref:
        return {}
    try:
        events = load_json(store, ref['key']).get('events') or []
    except Problem:
        return {}
    def clip(e):
        return str(e['sub_clip_id']).rsplit(':', 1)[0] if e and e.get('sub_clip_id') else None
    out = {}
    for i, ev in enumerate(events):
        if ev.get('kind') == 'gap':
            out[ev.get('gap_id')] = {'before': clip(next((e for e in reversed(events[:i]) if e.get('kind') == 'event'), None)),
                                     'after': clip(next((e for e in events[i + 1:] if e.get('kind') == 'event'), None))}
    return out


def footage_view(session, outputs=()):
    """design/88 F4: the line the operator is told, the summary and the per-clip map; a session prepared before design/88 shows the recorded answer."""
    f = session.get('footage')
    if not f:
        old = footage_character(outputs) if outputs else None
        return {'line': None, 'summary': old, 'per_clip': {}} if old else None
    return {'line': FM.line(f['summary']), 'summary': f['summary'], 'per_clip': f['per_clip'], 'measured': (session.get('footage_measured') or {}).get('summary')}


def correct_footage(store, user, run, outputs, values, quote):
    """design/88 F4: the operator corrects the measured footage with their words; it wins for the rest of the run, on both front ends."""
    session = session_of(store, run, outputs)
    need((quote or '').strip(), "The operator's words are required: say what the footage really is.")
    vals = {k: ((values or {}).get(k) or None) for k in ('camera', 'support', 'look')}
    need(any(vals.values()), 'Give the camera, the support or the look to correct.')
    for k, allowed in (('camera', FM.CAMERAS), ('support', FM.SUPPORTS), ('look', FM.LOOKS)):
        need(vals[k] is None or vals[k] in allowed, f"{k} is one of {', '.join(allowed)}.")
    prev = session.get('footage_correction') or {}
    session['footage_correction'] = {**{k: prev.get(k) for k in ('camera', 'support', 'look') if prev.get(k)}, **{k: v for k, v in vals.items() if v},
                                     'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    session['footage'] = FM.apply_correction(session.get('footage_measured') or {'per_clip': {}, 'summary': {}}, session['footage_correction'])
    save_session(store, run, session)
    return footage_view(session)


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
    ensure_timing(store, run, session)   # design/89 A1, finding 3
    try:
        plan, warnings = validate_plan(document, session['source']['gaps'], _fps(session), film_frames(outputs), session.get('frozen_limit') or FROZEN_SHARE)   # design/89 B4
    except (ValueError, KeyError, TypeError) as exc:
        return {'status': 'rejected', 'error': str(exc)}
    r = routes(plan, _fps(session) or 25)
    pr = prices()
    planned = round(r['images_estimated'] * pr['image_inr'] + r['seconds']['video'] * pr['video_inr_per_s'], 2)   # design/65 B7: the cost against the cap, before anything is paid
    alike = look_alike_placed(store, session)   # design/89 H6: the pictures already placed that look alike
    warnings += [{'kind': 'look_alike', 'shot_id': p['b'], 'message': f"{p['a']} ({p['a_at_s']} s) and {p['b']} ({p['b_at_s']} s) look alike: reimagine one (another angle, distance or moment)"} for p in alike]
    split = {}
    for gap in plan['gaps']:   # design/97 G3: a gap with choices is split by its recommended choice
        try:
            split[gap['gap_id']] = split_of([sh for sc in chosen_scenes(gap, {'choice_id': gap.get('recommended_choice')} if gap.get('choices') else None) for sh in sc['shots']],
                                            float(Fraction(str(_fps(session) or 25))))
        except ValueError:
            continue
    return {'status': 'valid', 'warnings': warnings, 'routes': r, 'split': split, 'plan_digest': digest(plan), 'budget': {'planned_inr': planned, 'cap_inr': cap_of(session)}, 'look_alike': alike}   # design/45 10.2


def propose(conn, store, user, run, outputs, document):
    session = session_of(store, run, outputs)
    ensure_timing(store, run, session)   # saved with the proposal
    plan, warnings = guarded(lambda: validate_plan(document, session['source']['gaps'], _fps(session), film_frames(outputs), session.get('frozen_limit') or FROZEN_SHARE))
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
    return {'image_inr': float(s.VISUALS_PRICE_IMAGE_INR), 'video_inr_per_s': float(s.VISUALS_PRICE_VIDEO_INR_PER_S), 'usd_inr': float(s.VISUALS_USD_INR)}


IMAGE_USD_PER_M = {'input': 8.0, 'output': 30.0}   # design/82 U2: OpenAI's GPT Image 2.5 rates, every input token at the image rate (the text share is a fraction of a rupee)


def image_cost_inr(cost, pr):
    """A finished image job's cost from its tokens; the flat image price when the job has none."""
    c = cost or {}
    if not c.get('output_tokens'):
        return pr['image_inr']
    return ((c.get('input_tokens') or 0) * IMAGE_USD_PER_M['input'] + c['output_tokens'] * IMAGE_USD_PER_M['output']) / 1e6 * pr.get('usd_inr', 88.0)


def visuals_spend(conn, run):
    """What this film's visuals have cost so far, at the configured prices: every image job and every take job that ran or is running."""
    rows = conn.execute("select provider, status, request, cost from vw2_jobs where run_id=%s and stage='visuals' and provider in ('openai', 'video')", (run['id'],)).fetchall()
    live = [r for r in rows if r['status'] not in ('failed', 'rejected', 'cancelled')]
    pr = prices()
    images = sum(1 for r in live if r['provider'] == 'openai')
    ref = lambda r: (r.get('request') or {}).get('reference') or {}
    fixes = sum(1 for r in live if r['provider'] == 'openai' and (ref(r).get('fix_of') or str(ref(r).get('name') or '').endswith('-fix')))   # design/96 X3; an old fix by its name
    image_inr = sum(image_cost_inr(r.get('cost'), pr) for r in live if r['provider'] == 'openai')
    seconds = float(sum(float((r.get('request') or {}).get('duration_seconds') or 0) for r in live if r['provider'] == 'video'))
    return {'images': images, 'fixes': fixes, 'take_seconds': seconds, 'spent_inr': round(image_inr + seconds * pr['video_inr_per_s'], 2), 'prices': pr}


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
    seen, totals = set(), {'gaps': 0, 'images': 0, 'routes': {}, 'seconds': {}, 'frozen_seconds': 0.0}
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
        need(e.get('activity_level', '') in ('', 'quiet', 'normal', 'busy'), f"gap {e['gap_id']}: activity_level is quiet, normal or busy.")   # design/91 N4
        need(isinstance(e.get('depicts', []), list) and all(isinstance(x, str) and x.strip() for x in e.get('depicts', [])),
             f"gap {e['gap_id']}: depicts is a list of lines, one per graphic, each saying what it shows.")   # design/91 N10
        need(isinstance(e.get('seconds'), (int, float)) and e['seconds'] > 0, f"gap {e['gap_id']}: seconds must be a number above zero.")
        need(isinstance(e.get('images'), int) and e['images'] >= 0, f"gap {e['gap_id']}: images must be a whole number.")
        need(isinstance(e.get('frozen_seconds', 0), (int, float)) and 0 <= e.get('frozen_seconds', 0) <= e['seconds'],
             f"gap {e['gap_id']}: frozen_seconds, the seconds held without movement, is between 0 and the gap's seconds.")   # design/89 B4
        totals['frozen_seconds'] = round(totals['frozen_seconds'] + float(e.get('frozen_seconds', 0)), 2)
        totals['gaps'] += 1
        totals['images'] += e['images']
        first = routes_[0]
        totals['routes'][first] = totals['routes'].get(first, 0) + 1
        totals['seconds'][first] = round(totals['seconds'].get(first, 0.0) + float(e['seconds']), 2)
        if 'video' in routes_:
            video_seconds += float(e['seconds'])
    missing = sorted(set(gaps) - seen)
    need(not missing, 'The treatment covers every gap; missing: ' + ', '.join(missing) + '.')
    film = film_frames(outputs)   # design/89 B4: the expected frozen share, shown before approval
    if film:
        totals['frozen_share'] = round(totals['frozen_seconds'] / (film / float(Fraction(str(session['source'].get('fps') or 25)))), 3)
        totals['frozen_limit'] = float(session.get('frozen_limit') or FROZEN_SHARE)
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

def page_view(conn, store, run, outputs, code, repair=True):
    """The page's data in one read of the session (plus the package for the intended visuals): the treatment (draft or record), the plan's gaps and
    shots with their pictures, the references with their image links, the takes, the budget. Links go through the run's file route."""
    def url(k):
        return f'/runs/{code}/file/{k}' if k else None
    try:
        session = session_of(store, run, outputs)
    except Problem:
        return {'state': 'not_prepared'}
    if (reconcile(conn, run, session) | ensure_timing(store, run, session)) and repair:   # design/89 A1: the page shows the timing too; design/92: saved only under the lock
        save_session(store, run, session)
    try:
        package = load_json(store, key(run, 'package.json'))
    except Problem:
        package = {}
    plan = current_plan(store, session) if session.get('current') else None
    refs = {}
    for r in session['references'].values():
        refs[r['id']] = {k: r.get(k) for k in ('id', 'name', 'kind', 'element_id', 'status', 'sha256', 'job_id', 'width', 'height', 'check_pending')}   # design/92: being checked
        refs[r['id']]['note'] = (r.get('source') or {}).get('note') or ''   # design/73
        refs[r['id']]['from_thumbnail'] = bool((r.get('source') or {}).get('from_thumbnail'))   # design/100 S2
        refs[r['id']]['sources_changed'] = bool(r.get('sources_changed'))   # design/110
        gold_ = golden_of(session, r.get('element_id'))   # design/111 F11
        refs[r['id']]['golden'] = bool(gold_) and gold_ == r['id']
        first = ((r.get('generation') or {}).get('parents') or [{}])[0].get('id')
        refs[r['id']]['from_golden'] = (first == gold_) if gold_ and r.get('kind') in ('keyframe', 'isolated') and r.get('role') != 'end' and not r.get('golden_candidate') and r['id'] != gold_ else None
        refs[r['id']]['edit'] = r.get('edit')
        refs[r['id']]['shot_id'] = made_for(session, r)   # design/94 R1.3: listed only under its own shot
        refs[r['id']].update(url=url(r.get('key')), prompt=(r.get('generation') or {}).get('prompt'), parents=[p.get('id') for p in (r.get('generation') or {}).get('parents') or []],
                             approval={k: (r.get('approval') or {}).get(k) for k in ('by', 'at', 'quote')} if r.get('approval') else None,
                             rejection={k: (r.get('rejection') or {}).get(k) for k in ('notes', 'quote', 'by', 'at')} if r.get('rejection') else None,   # design/74 L7
                             checklist=(r.get('answer') or {}).get('checklist') if r.get('answer') else None,   # design/74 L6
                             check=({k: image_check.expand(r['check'], r).get(k) for k in ('lines', 'must_failed', 'error', 'fix_error', 'model')} if r.get('check') else None),   # design/86 K2; design/92
                             pending_end=bool(r.get('pending_end')), end_queued=r.get('end_queued'), role=r.get('role'), fix_of=r.get('fix_of'), fix_queued=r.get('fix_queued'), fix_for=r.get('fix_for'))   # design/86 K1, K2
    takes, take_rows = {}, take_jobs(conn, run)
    for j in take_rows:
        res = j.get('result') or {}
        takes.setdefault(j['unit'], []).append({'job_id': str(j['id']), 'status': j['status'], 'error': j.get('error'), 'url': url(res.get('key')), 'sha256': res.get('sha256'),
                                                 'duration_s': (res.get('evidence') or {}).get('duration_seconds'), 'timing_matches': (res.get('evidence') or {}).get('timing_matches_placement'),
                                                 'reviews': [{k: rv.get(k) for k in ('decision', 'notes', 'quote', 'by')} for rv in session['reviews'].get(str(j['id']), [])],
                                                 'selected': (session['selections'].get(j['unit']) or {}).get('job_id') == str(j['id']), 'checklist': take_checklist(session, j),
                                                 'check': (session.get('take_checks') or {}).get(str(j['id']))})   # design/91 N3
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
                    ambient = {sh['id']: sc.get('ambient') or '' for sc in chosen_scenes(gap, session['choice_selections'].get(gid)) for sh in sc['shots']}   # design/101 M6
                    lit = {sh['id']: {k: sc.get(k) for k in ('light', 'air') if sc.get(k)} for sc in chosen_scenes(gap, session['choice_selections'].get(gid)) for sh in sc['shots']}   # design/103
                except ValueError:
                    shots, ambient, lit = [], {}, {}
                entry['split'] = split_of(shots, float(Fraction(str(_fps(session) or 25))))   # design/97 G3
                for sh in shots:
                    asset = session['assets'].get(sh['id'])
                    binding = session['bindings'].get(sh['id']) or {}
                    entry['shots'].append({'shot_id': sh['id'], 'title': sh.get('title') or '', 'visual_type': sh['visual_type'], 'route': route_of(sh), 'purpose': sh.get('purpose', ''),
                                           **({'ambient': ambient.get(sh['id'])} if sh['visual_type'] == 'video' and ambient.get(sh['id']) else {}),   # design/101 M6
                                           **{k: sh[k] for k in ('size', 'camera_reason') if sh.get(k)}, **lit.get(sh['id'], {}),   # design/103
                                           'start_frame': sh['start_frame'], 'end_frame': sh['end_frame'], 'states': sh.get('states') or [], 'element_ids': sh.get('element_ids') or [],
                                           'bound': [b['id'] for rows in binding.get('references', {}).values() for b in rows],
                                           'asset': ({'kind': asset['kind'], 'url': url(asset.get('key')), 'reference_id': asset.get('reference_id'), 'states': [{'reference_id': st['reference_id'], 'url': url(st['key']), 'hold_frames': st['hold_frames']} for st in asset.get('states') or []],
                                                      **({k: asset.get(k) for k in ('clip_id', 'name', 'in_s', 'out_s')} if asset['kind'] == 'clip' else {})} if asset else None),   # design/89 B3
                                           'takes': takes.get(sh['id'], []), 'prepared': sh['id'] in session['preparations'], **_state_order(session, sh),   # design/94 A2
                                           'changes': sh.get('changes') or [], 'motion': (session['preparations'].get(sh['id']) or {}).get('motion_prompt'),   # design/91 N1
                                           'pair_check': (session['preparations'].get(sh['id']) or {}).get('pair_check'),
                                           'message': sh.get('message') or '', 'adds': sh.get('adds') or '',   # design/91 N11
                                           **{k: sh.get(k) or '' for k in ('transition_in', 'transition_out', 'transition_reason')},   # design/91 N16
                                           'depicts': sh.get('depicts') or '', 'descriptors': sh.get('descriptors') or [], 'carries_over': sh.get('carries_over') or [],   # design/91
                                           'facts': [f"{f['looks']} ({f['status']}{', ' + f['source'] if f.get('source') else ''})" for f in (plan or {}).get('visual_facts') or []
                                                     if f['id'] in (sh.get('fact_ids') or []) or f.get('about') in (sh.get('element_ids') or [])],
                                           'claims': sh.get('claims') or [], 'spec': ({'table': spec_table(sh['drawing_spec']), 'relationships': sh['drawing_spec'].get('relationships') or [],   # design/89 C1, D4
                                                                                      'label': sh['drawing_spec'].get('label') or '',
                                                                                      'correction': ((session.get('spec_corrections') or {}).get(sh['id']) or {}).get('words'), 'approved': (session.get('spec_approvals') or {}).get(sh['id'], {}).get('digest') == spec_digest(sh['drawing_spec'])}
                                                                                     if sh.get('drawing_spec') else None)})
        gaps.append(entry)
    sp = visuals_spend(conn, run)
    return {'state': 'prepared', 'busy': not repair, 'fps': session['source'].get('fps'), 'plan_digest': session.get('current'), 'versions': len(session['versions']),
            'footage': footage_view(session, outputs),   # design/88 F4: told, not asked
            'reuse_pending': session.get('reuse_pending') or {},   # design/89 H7: a reuse the operator may approve here
            'clips': [{k: c.get(k) for k in ('id', 'name', 'duration_s')} for c in media_clips(outputs).values()],   # finding 7: a clip stretch placed from the page
            'graphic_style': ((plan or {}).get('foundation') or {}).get('graphic_style'),   # design/89 C2
            'measurements': [{'id': k, **{f: m.get(f) for f in ('question', 'measurements', 'limits', 'at')}} for k, m in (session.get('measurements') or {}).items()],   # design/89 D2
            'treatment': session.get('treatment'), 'treatment_draft': session.get('treatment_draft'), 'intended_visuals': package.get('intended_visuals') or [],
            'elements': [{**{k: e.get(k) for k in ('id', 'name', 'kind', 'identity', 'requirements', 'required_views', 'size')},
                          'material_spec': ({'table': spec_table(e['material_spec']) + [{'part': 'laid', 'measure': '', 'size': e['material_spec']['laid'], 'source': '', 'status': 'rule'},
                                                                                       {'part': 'pattern', 'measure': '', 'size': e['material_spec']['pattern'], 'source': '', 'status': 'rule'}],
                                            'sentence': material_sentence(e), 'approved': material_approved(session, e),
                                            'correction': ((session.get('spec_corrections') or {}).get(material_key(e['id'])) or {}).get('words')} if e.get('material_spec') else None),
                          'not_this': list(((session.get('not_this') or {}).get(e['id']) or {}).get('lines') or [])}   # design/111 F10, F12
                         for e in (plan or {}).get('elements') or []],   # design/73: the page's element sections
            'element_matches': element_matches(plan, package.get('world_evidence')) if plan else {}, 'searches': _searches(session), 'round': _round_view(session),
            'questions': dict(session.get('questions') or {}),   # design/110 rule 0
            'golden': dict(session.get('golden') or {}),   # design/111 F11
            'waiting': waiting(session, plan, code, take_rows),   # design/97 W1, W3
            'gaps': gaps, 'references': list(refs.values()), 'budget': {**sp, 'cap_inr': cap_of(session), 'left_inr': round(cap_of(session) - sp['spent_inr'], 2)}}


# ---------- design/65 B2': the graphic sequence ----------

def sequence(store, user, run, outputs, shot_id, reference_ids, quote):
    """An animation shot's states, approved in one call with the operator's words; each state's hash is recorded; the asset holds them for the shot."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    _route_gate(shot, 'animation')
    _no_question(session, shot_id, *(reference_ids or []))   # design/110 rule 0
    states = shot.get('states') or []
    quote = said(quote, 'Approved', user)   # design/99 C2
    rows, warnings = state_chain(session, shot_id), []
    if rows is not None:   # design/94 A2: the order comes from the shot's own pictures, each state made from the one before
        need(len(rows) == len(states), f"{shot_id} plans {len(states)} states; its pictures make {len(rows)}: {', '.join(r['name'] for r in rows)}.")
        need(not reference_ids or list(reference_ids) == [r['id'] for r in rows], f"in the plan's order the states are {', '.join(r['id'] for r in rows)}; give them in that order, or leave --refs out.")
    else:   # pictures made before shots were recorded: the order given, warned
        need(reference_ids, f'no pictures made for {shot_id}: make its states with `vw visuals image --shot {shot_id} --kind state …`.')
        need(len(reference_ids) == len(states), f'shot {shot_id} plans {len(states)} states; {len(reference_ids)} references given.')
        rows = []
        for rid in reference_ids:
            row = session['references'].get(rid)
            need(row and row.get('status') in ('candidate', 'approved') and row.get('sha256'), f'{rid} is not a candidate or approved reference of this run.')
            rows.append(row)
        warnings.append(f'these states have no shot recorded; from the next release the order comes from the pictures made for {shot_id}')
        for i, row in enumerate(rows[1:], 2):
            parents = [p.get('id') for p in (row.get('generation') or {}).get('parents') or []]
            if rows[i - 2]['id'] not in parents:
                warnings.append(f"state {i} ({row['id']}) was not generated from state {i - 1} ({rows[i - 2]['id']}); check the drawing is the same")
    from . import lookalike   # design/91 N12: every state adds something visible
    prints = [(_fingerprints(store, r['key']) or {}).get('graphic') for r in rows]
    for i in range(1, len(rows)):
        need(prints[i - 1] is None or prints[i] is None or lookalike.distance(prints[i - 1], prints[i]) > lookalike.BITS_GRAPHIC,
             f"state {i + 1} ({rows[i]['name']}) looks the same as state {i} ({rows[i - 1]['name']}): a state adds something visible; make it again from state {i} with what it adds.")
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
    return {'shot_id': shot_id, 'kind': 'sequence', 'states': len(rows), 'warnings': warnings, 'next': f'Sequence approved: in the film at {film_time(session, shot)} ({shot_id}).'}


def _state_order(session, sh):
    """The page's numbered states: the server's order, or why there is none."""
    if route_of(sh) != 'graphic_sequence':
        return {}
    try:
        return {'state_order': [r['id'] for r in state_chain(session, sh['id']) or []], 'state_problem': None}
    except ValueError as exc:
        return {'state_order': [], 'state_problem': str(exc)}


def film_time(session, shot):
    """design/97 A4: where a shot sits in the film, as 0:14–0:17."""
    fps = float(Fraction(str(_fps(session) or 25)))
    m = lambda f: f"{int(f / fps) // 60}:{int(f / fps) % 60:02d}"
    return f"{m(shot['start_frame'])}–{m(shot['end_frame'])}"


def item_link(code, step, group, item):
    """design/97 W1: the page's link to one item, the same from both front ends."""
    return f'/runs/{code}/visuals#{step}/{group}/{item}'


def split_of(shots, fps):
    """design/97 G3: a gap's seconds and shots per route."""
    out = {}
    for sh in shots:
        k = 'graphics' if sh['visual_type'] in GRAPHIC_TYPES else 'AI video' if sh['visual_type'] == 'video' else 'still'
        row = out.setdefault(k, {'route': k, 'seconds': 0.0, 'shots': 0})
        row['seconds'] = round(row['seconds'] + (sh['end_frame'] - sh['start_frame']) / float(fps), 1)
        row['shots'] += 1
    return [out[k] for k in ('graphics', 'AI video', 'still') if k in out]


def _accepted_shots(plan, session):
    """The shots of the accepted gaps, as (gap, shot), in film order."""
    out = []
    for gap in plan['gaps']:
        acc = session['accepted'].get(gap['gap_id'])
        if not acc or acc['digest'] != gap_digest(plan, gap) or (gap.get('choices') and not session['choice_selections'].get(gap['gap_id'])):
            continue
        out += [(gap, sh) for sc in chosen_scenes(gap, session['choice_selections'].get(gap['gap_id'])) for sh in sc['shots']]
    return sorted(out, key=lambda gs: gs[1]['start_frame'])


# ---------- design/110 F3: the start shows the action not yet done ----------

NOT_YET_START = ('Carry each line of start_targets word for word in the start prompt: the start is the moment before the action; the result of the shot\'s action is not visible '
                 'in it (the count, the position, the surface the action changes is still as the start state says). The server checks the picture against it, when it is made and '
                 'again at approval.')


def _acting_beats(shot):
    return [(s, s['beats'][0]) for s in shot.get('subjects') or [] if s.get('behaviour') == 'acts' and s.get('beats')]


def start_targets(scene, shot):
    """One line per acting subject: about to <action>; has not yet <done>: <what the start state still shows>."""
    return [f"{s['element_id']}: about to {b['action']}; not yet done: {b['result']}; still as at the start: {(s.get('start') or {}).get('progress', '')}."
            for s, b in _acting_beats(shot) if shot.get('visual_type') == 'video']   # live check 27 Oct: the plan's action is third person, so "about to:" not "about to <verb>"


def not_yet_lines(shot):
    """The must line on a start keyframe of a video shot with an action: the picture shows the moment before it (design/110 F3)."""
    if shot.get('visual_type') != 'video':
        return []
    return [{'check': 'not yet done', 'weight': 'must',
             'pass_when': f"the picture still shows the start state ({s['element_id']}: {(s.get('start') or {}).get('progress', '')}) and {b['result']} has NOT happened yet; "
                          f"this line FAILS when {b['result']} is already in the picture, even with a hand still on it"}   # live check 27 Oct (f3-live): steady on VW-7's B07B_S2, two reads each
            for s, b in _acting_beats(shot)]


def _not_yet_gate(store, session, row, at_approval=False, shot=None):
    """F3 at approval and before a take: the stored "not yet done" line decides; failed or undecided refuses and asks the operator (rule 0, fork 5);
    at approval a start checked before this release is asked the line once; the operator's "approve anyway" lets it through."""
    if row.get('not_yet_ok') or (shot is None and (row.get('kind') != 'keyframe' or _picture_word(store, session, row) != 'start image')):
        return
    sid = shot['id'] if shot else made_for(session, row)
    if shot is None:
        try:
            shot = locate(store, session, sid)[3] if sid else None
        except (ValueError, Problem):
            shot = None
    wanted = not_yet_lines(shot) if shot else []
    if not wanted:
        return
    check = row.get('check')
    if not check:
        return   # never checked (no checklist, or the check still running): nothing stored to read
    line = next((l for l in check.get('lines') or [] if l.get('check') == 'not yet done'), None)
    if line is None and not at_approval:
        return   # a take from an older start: nothing stored to read; the approval gate covers new pictures
    if line is None:
        from . import image_check
        from .analysis_jobs import transport_factory
        rec = image_check.check_lines(store, session, row, wanted, transport_factory)
        line = next((l for l in rec.get('lines') or [] if l.get('check') == 'not yet done'), None) or {'check': 'not yet done', 'pass': None, 'seen': rec.get('error') or 'no answer'}
        row['check'] = {**check, 'lines': list(check.get('lines') or []) + [line], 'must_failed': list(check.get('must_failed') or []) + ([line] if line.get('pass') is False else [])}
    if line.get('pass') is True:
        return
    why = (f"{row['id']} already shows the result of {sid}'s action ({line.get('seen') or 'no detail'})" if line.get('pass') is False
           else f"whether {row['id']} already shows the result of {sid}'s action could not be decided ({line.get('seen') or 'no answer'})")
    if row['id'] not in (session.get('questions') or {}):
        _open(session, row['id'], f"{why}. Make a new start, or approve this one anyway?", [f"make a new start ({prices()['image_inr']:g} INR)", 'approve anyway'], 'server', fork='not_yet')
    need(False, f"{why}; the operator decides: make a new start, or approve anyway (the question is on its card; `vw visuals answer --item {row['id']} …`).")


# ---------- design/111 F17: groups of a kind, said; background figures compared within the scene ----------

def group_lines(plan, shot):
    """One line per group: all alike with the reason, or no two alike with the traits."""
    names = _names(plan)
    out = []
    for g in shot.get('groups') or []:
        head = f"Every {names[g['kind']]}" if g['kind'] in names else f"{g['count']} {g['kind']}"
        out.append(head + (f": all alike ({g.get('reason', '').strip().rstrip('.')})." if g['mode'] == 'same' else ': no two alike: ' + '; '.join(i.strip().rstrip('.') for i in g.get('items') or []) + '.'))
    return out


def group_rule_lines(plan, shot):
    """The two must lines: the count (for a group that is no element; the inventory counts elements) and the sameness."""
    names = _names(plan)
    out = []
    for g, line in zip(shot.get('groups') or [], group_lines(plan, shot)):
        name = names.get(g['kind'], g['kind'])
        if g['kind'] not in names:
            out.append({'check': f'group count: {name}', 'weight': 'must', 'pass_when': f"exactly {g['count']} {name} are in frame, no more, no fewer"})
        out.append({'check': f'group alike: {name}', 'weight': 'must', 'pass_when': (f'the {name} are all alike in shape, size, colour and wear' if g['mode'] == 'same'
                                                                                     else f'no two alike among the {name}; each shows its own trait: ' + '; '.join(g.get('items') or []))})
    return out


def _has_figures(plan, shot):
    kinds = {e['id']: e['kind'] for e in plan.get('elements') or []}
    return any(s.get('role') in ('secondary', 'background') and kinds.get(s['element_id']) in ('person', 'animal') for s in shot.get('subjects') or [])


FIGURE_SCHEMA = {'type': 'object', 'properties': {'repeated': {'type': 'boolean'}, 'detail': {'type': 'string'}}, 'required': ['repeated', 'detail']}


def figure_repeat(store, session, row, scene):
    """SK's answer 7: one Gemini question when a picture with background figures is approved, against the approved pictures of the same scene.
    None when there is nothing to compare with; never raises."""
    import base64
    sids = {s['id'] for s in scene.get('shots') or []}
    others = [r for r in session['references'].values() if r['id'] != row['id'] and r.get('status') == 'approved' and r.get('kind') in ('keyframe', 'isolated')
              and made_for(session, r) in sids and r.get('key')]
    if not others:
        return None
    rec = {'against': [r['id'] for r in others], 'repeated': None, 'detail': '', 'model': image_check.CHECK_MODEL}
    try:
        key_ = settings().GEMINI_API_KEY.get_secret_value().strip()
        if not key_:
            return {**rec, 'error': 'no Gemini key on the server'}
        parts = []
        for i, r in enumerate(others, 1):
            parts += [{'text': f"Picture {i} ({r['id']})."}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(r['key'])).decode()}}]
        parts += [{'text': 'The new picture.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(row['key'])).decode()}}]
        parts.append({'text': 'Look only at the background and secondary figures (people and animals), not the main subject. Does any figure in the new picture look like the same '
                              'individual as a figure in an earlier picture (same face, build, hair, clothes, markings)? Answer repeated true or false, and in detail name the pair '
                              'and what matches. Be literal; two figures of one kind that differ in face, clothes or markings are not repeated.'})
        received = _gemini_transport()(key_, image_check.CHECK_MODEL, terminal_deadline_seconds=120, initial_soft_wait_seconds=20, on_update=lambda e: None, capture_answer_deltas=False).generate(
            {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': FIGURE_SCHEMA, 'maxOutputTokens': 512}})
        body = received.get('body') if isinstance(received.get('body'), dict) else json.loads(received.get('raw') or '{}')
        rec.update(repeated=bool(body.get('repeated')), detail=str(body.get('detail') or '')[:500])
    except Exception as exc:   # the comparison never blocks an approval
        rec['error'] = f'{exc.__class__.__name__}: {str(exc)[:200]}'
    return rec


# ---------- design/111 F16: the person's two layers, the fixed description and the scene's colours ----------

def person_lines(plan, scene, shot):
    """One line per person in the shot: the fixed description, then this scene's garment colours."""
    out = []
    for e in plan.get('elements') or []:
        if e['kind'] == 'person' and e['id'] in (shot.get('element_ids') or []) and (e.get('description') or '').strip():
            colours = ((scene.get('outfit') or {}).get(e['id']) or '').strip().rstrip('.')
            out.append(f"{e['name']}: {e['description'].strip().rstrip('.')}" + (f'; wearing in this scene: {colours}' if colours else '') + '.')
    return out


# ---------- design/111 F14, F15: techniques are elements; size as the message carries a number and a comparison ----------

def technique_words(text):
    from .visual_contract import technique_words as tw
    return tw(text)


def needed_elements(plan):
    """F14: the technique elements the plan's beats need and do not have yet, for the planner to add before the round."""
    have = {e['id'].lower() for e in plan.get('elements') or []} | {e['name'].lower() for e in plan.get('elements') or []}
    out, seen = [], set()
    for g in plan.get('gaps') or []:
        for sc in (g.get('scenes') or []) + [sc for ch in g.get('choices') or [] for sc in ch.get('scenes') or []]:
            for sh in sc.get('shots') or []:
                for s in sh.get('subjects') or []:
                    for b in s.get('beats') or []:
                        for tech in technique_words((b.get('action') or '') + ' ' + (b.get('done') or '')):
                            if tech not in have and tech not in seen:
                                seen.add(tech)
                                out.append({'id': tech.upper(), 'kind': 'technique', 'from': f"{sh['id']} {b.get('id')}: {b.get('action')}"})
    return out


def size_line(plan, shot):
    """F15: one number and one comparison when the shot's claim or descriptor is about size."""
    from .visual_contract import SIZE_WORDS
    if not SIZE_WORDS.search(' '.join((shot.get('claims') or []) + (shot.get('descriptors') or []))) or not shot.get('compare_to'):
        return ''
    elements = {e['id']: e for e in plan.get('elements') or []}
    subj = shot['subjects'][0]['element_id'] if shot.get('subjects') else (shot.get('element_ids') or [''])[0]
    el = elements.get(subj) or {}
    dims = [d for d in (el.get('size') or []) + ((el.get('material_spec') or {}).get('dimensions') or []) if d.get('value') is not None]
    if not dims:
        return ''
    sizes = ', '.join(f"{d['part']} {d['measure']} {d['value']:g} {d.get('unit') or ''}".strip() for d in dims[:2])
    comp = elements.get(shot['compare_to'], {}).get('name', shot['compare_to'])
    return f"Size is the point: {el.get('name', subj)}, {sizes}, against the {comp} beside it; the sizes read true against each other and the place."


# ---------- design/111 F13: words to be read, letter for letter, in their place ----------

def exact_text_lines(answer, marks):
    """The must lines on every picture with exact text: reads exactly, placed as the entry says at that size, no other lettering."""
    entries = library.exact_entries(answer)
    out = []
    for e in entries:
        place = e.get('place') or {}
        where = f"on {marks.get(place['landmark_id'], place['landmark_id'])}" if place.get('landmark_id') else (f"in the {place.get('region')}" if place.get('region') else 'where the prompt says')
        out.append({'check': f"reads: {e['text']}", 'weight': 'must', 'pass_when': f'the words read exactly "{e["text"]}", spelled as written'})
        out.append({'check': f"placed: {e['text']}", 'weight': 'must', 'pass_when': f'"{e["text"]}" sits {where}' + (f", about {float(e['size_pct']):g} % of the frame height" if e.get('size_pct') else '')})
    if entries:
        out.append({'check': 'no other lettering', 'weight': 'must', 'pass_when': 'no letters, numbers or logos anywhere but the exact text named'})
    return out


def exact_text_block(answer):
    entries = library.exact_entries(answer)
    if not entries:
        return ''
    return '\n'.join(f'Render exactly this text, letter for letter, nothing else: "{e["text"]}".' for e in entries) + '\nConstraints: no other letters, numbers or logos anywhere.'


# ---------- design/111 F7, F8, F9: the eye lines, the fixed background, how a placed thing sits ----------

PLACING = re.compile(r'\b(lay|lays|laid|laying|set|sets|setting|put|puts|putting|fit|fits|fitted|fitting|stacks|stacked|stacking|join|joins|joined|joining|fixes|fixed|fixing|place|places|placed|placing)\b', re.I)   # verbs only: 'the stack' and 'a fix' are not placings


def _target_words(plan, marks, target):
    return marks.get(target) or next((e['name'] for e in plan.get('elements') or [] if e['id'] == target), target)


def gaze_lines(plan, scene, shot, when):
    """F7: per person, where the eyes are, the head turn and the mouth; the two constraints."""
    marks = {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
    kinds = {e['id']: e.get('kind') for e in plan.get('elements') or []}
    out = []
    for s in shot.get('subjects') or []:
        state = s.get('end' if when in ('end', 'motion') else 'start') or {}
        gz = state.get('gaze')
        if not gz or kinds.get(s['element_id']) != 'person':
            continue
        out.append(f"{s['element_id']}'s eyes are on {_target_words(plan, marks, gz.get('target'))}; head turned {gz.get('head_turn')}; mouth {gz.get('mouth')}.")
    if out:
        out[-1] += ' No one looks at the lens' + ('; no one looks where they looked in Image 1 unless named here.' if when in ('end', 'motion') else '.')
    return out


def fixed_line(scene, shot):
    """F8: the background is Image 1's, three fixed things named from the landmarks."""
    marks = {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
    names = [marks.get(lid, lid) for lid in shot.get('fixed') or []]
    return f"The background is Image 1's background: {', '.join(names)} are in the same place, same size, same light." if names else ''


def sits_lines(plan, scene, shot):
    """F9: for each thing the action sets down (a beat with a placing verb and a thing whose count grew, or a prop set down), how it sits: on what, full contact,
    in line, the joint from the spec, the facts' words; never a guessed number."""
    marks = {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
    elements = {e['id']: e for e in plan.get('elements') or []}
    facts = {f.get('about'): f for f in plan.get('visual_facts') or [] if f.get('status') != 'unknown' and f.get('how')}
    placed = []
    for s in shot.get('subjects') or []:
        if not any(PLACING.search(b.get('action', '') + ' ' + b.get('done', '')) for b in s.get('beats') or []):
            continue
        before = {o['element_id']: o['count'] for o in (s.get('start') or {}).get('objects') or []}
        for o in (s.get('end') or {}).get('objects') or []:
            if o['count'] > before.get(o['element_id'], 0):
                placed.append((o['element_id'], o.get('place')))
    for p in shot.get('props') or []:
        if (p.get('end') or {}).get('where') == 'set_down':
            placed.append((p['element_id'], (p['end'] or {}).get('position')))
    out, seen = [], set()
    for eid, pos in placed:
        if eid in seen:
            continue
        seen.add(eid)
        e = elements.get(eid) or {'name': eid}
        bits = [f"{e['name']} rests on {marks.get((pos or {}).get('landmark_id'), (pos or {}).get('landmark_id', 'its support'))} with full contact", 'lined up with its neighbours']
        spec = e.get('material_spec') or {}
        if spec.get('joint'):
            bits.append(spec['joint'])
        if facts.get(eid):
            bits.append(facts[eid]['how'])
        bits.append('not tilted, not floating')
        out.append('; '.join(bits) + '.')
    return out


# ---------- design/111 F12: every element carries a "not this" list, made by one method, pasted into every prompt ----------

NOT_THIS_MODEL = 'gemini-3.8-flash'   # SK's answer 5: the check model, once per element
NOT_THIS_SCHEMA = {'type': 'object', 'properties': {'lines': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['lines']}


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', str(text or '').lower()).strip('-')[:60] or 'thing'


def not_this_key(name):
    return f'library/not-this/{_slug(name)}.json'


def _dedupe_lines(lines):
    out = []
    for l in lines:
        l = str(l or '').strip().rstrip('.')
        if l and l.lower() not in {x.lower() for x in out}:
            out.append(l)
    return out


def _library_lines(store, name):
    try:
        return list(json.loads(store.get(not_this_key(name)).decode('utf-8')).get('lines') or []) if store.exists(not_this_key(name)) else []
    except (ValueError, Problem, AttributeError):
        return []


def _keep_library(store, name, lines):
    try:
        store.put(not_this_key(name), json.dumps({'element': name, 'lines': lines}, ensure_ascii=False).encode('utf-8'), 'application/json')
    except Exception:   # the run's own list stands even when the shared store is unreachable
        pass


def _rejection_lines(session, element_id):
    return [r['rejection']['notes'] for r in session['references'].values() if r.get('element_id') == element_id and r.get('status') == 'rejected' and (r.get('rejection') or {}).get('notes', '').strip()]


def not_this(store, user, run, outputs, element_id):
    """The list, by the one method: the library's lines for this thing (earlier films), one model call on the spec and the round's near misses
    (the unticked web results and the nothing-fits reasons), then this film's rejections; kept on the session and in the library's store."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    element = next((e for e in plan['elements'] if e['id'] == element_id), None)
    need(element, f'{element_id} is not an element of the plan.')
    lib = _library_lines(store, element['name'])
    near = []
    for s_ in (session.get('searches') or {}).values():
        if s_.get('element_id') != element_id:
            continue
        picked = set(s_.get('picked') or [])
        near += [str(r.get('title') or '').strip() for r in s_.get('results') or [] if r.get('n') not in picked and str(r.get('title') or '').strip()]
        if (s_.get('nothing_fits') or {}).get('reason'):
            near.append(s_['nothing_fits']['reason'])
    spec = material_sentence(element) if element.get('material_spec') else f"{element['name']}: {element.get('requirements') or ''}"
    text = (f"The thing: {spec}\nList the common variants of this thing that a picture model draws instead of it, each as one short 'no …' line naming the difference "
            "(the bond, the shape, the surface, the colour, the size, the fittings), eight lines at most, no explanations." +
            ('\nThe operator rejected these web results or wrote why nothing fit; turn each difference into a line too: ' + '; '.join(near[:20]) if near else ''))
    key_ = settings().GEMINI_API_KEY.get_secret_value().strip()
    need(key_, 'No Gemini key on the server.')
    try:
        received = _gemini_transport()(key_, NOT_THIS_MODEL, terminal_deadline_seconds=120, initial_soft_wait_seconds=20, on_update=lambda e: None, capture_answer_deltas=False).generate(
            {'contents': [{'role': 'user', 'parts': [{'text': text}]}], 'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': NOT_THIS_SCHEMA, 'maxOutputTokens': 1024}})
        body = received.get('body') if isinstance(received.get('body'), dict) else json.loads(received.get('raw') or '{}')
    except Exception as exc:
        raise Problem(502, 'NOT_THIS_FAILED', f'The not-this call failed: {exc.__class__.__name__}: {str(exc)[:200]}')
    model = _dedupe_lines(body.get('lines') or [])[:12]
    rejections = _rejection_lines(session, element_id)
    lines = _dedupe_lines(lib + model + rejections)
    record = {'lines': lines, 'from': {'library': len(_dedupe_lines(lib)), 'model': len([l for l in model if l.lower() not in {x.lower() for x in lib}]),
                                       'rejections': len([l for l in _dedupe_lines(rejections) if l.lower() not in {x.lower() for x in lib + model}])},
              'model': NOT_THIS_MODEL, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    session.setdefault('not_this', {})[element_id] = record
    _keep_library(store, element['name'], lines)
    save_session(store, run, session)
    return {'element_id': element_id, **record, 'next': f"Not-this list of {element_id} ({len(lines)} lines): shown with the spec on the References step; the server pastes it into every prompt that shows {element_id}."}


def _not_this_add(store, session, plan, element_id, line):
    """A rejection's words join the list at once (source 3), on the session and in the library's store."""
    line = str(line or '').strip().rstrip('.')
    if not line or not element_id:
        return
    rec = (session.get('not_this') or {}).get(element_id)
    if rec is None:
        return   # no list yet: the rejection is read when the list is built
    if line.lower() in {x.lower() for x in rec['lines']}:
        return
    rec['lines'].append(line)
    rec['from']['rejections'] = rec['from'].get('rejections', 0) + 1
    name = next((e['name'] for e in (plan or {}).get('elements') or [] if e['id'] == element_id), element_id)
    _keep_library(store, name, rec['lines'])


def not_this_line(session, plan, element_id, shot=None, scene=None):
    """The constraint line for a prompt: the list minus the shot's named exceptions, which are said instead; a person's garment negatives (design/111 F16)."""
    rec = (session.get('not_this') or {}).get(element_id) or {}
    colours = ((scene or {}).get('outfit') or {}).get(element_id, '').strip().rstrip('.')
    allows = [a.strip().lower() for a in (shot or {}).get('allows') or []]
    kept = [l for l in rec.get('lines') or [] if not any(a and a in l.lower() for a in allows)] + ([f'garment colours other than {colours}'] if colours else [])
    if not kept:
        return ''
    name = next((e['name'] for e in (plan or {}).get('elements') or [] if e['id'] == element_id), element_id)
    return f"Not this ({name}): " + '; '.join(kept) + '.' + (f" Except in this shot: {'; '.join((shot or {}).get('allows') or [])}." if allows else '')


# ---------- design/111 F11 (+F41): one golden picture per element; every later picture is an edit of it ----------

REGION_MAX = 1 / 3   # an edit changes one region, about a third of the frame at most


def golden_of(session, element_id):
    return (session.get('golden') or {}).get(element_id)


def golden_due(session, plan):
    """The elements whose golden picture the assistant writes now: a non-person, non-graphic element with an approved sheet (and an approved material spec when it has one),
    no golden picture yet and none being made."""
    out = []
    for e in plan.get('elements') or []:
        if e.get('kind') in ('person', 'graphic') or e['id'] == STYLE or golden_of(session, e['id']):
            continue
        sheet = [r for r in session['references'].values() if r.get('kind') == 'sheet' and r.get('element_id') == e['id'] and r.get('status') == 'approved']
        if not sheet or (e.get('material_spec') and not material_approved(session, e)):
            continue
        if any(r.get('golden_candidate') and r.get('element_id') == e['id'] and r.get('status') in ('generating', 'candidate') for r in session['references'].values()):
            continue
        frames = [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == e['id'] and r.get('status') == 'approved']
        parents = ','.join([sheet[0]['id']] + frames[:1])
        out.append({'element_id': e['id'], 'next': f"write the golden picture of {e['id']} now: `vw visuals image --element {e['id']} --kind isolated --golden --parents {parents} …`"})
    return out


def _derived(session, p):
    """A picture made from another generated picture (a keyframe or a state among its parents)."""
    return any((session['references'].get(q.get('id')) or {}).get('kind') in ('keyframe', 'state') for q in (p.get('generation') or {}).get('parents') or [])


def check_region(region):
    """A rectangle in fractions of the frame, inside it, a third of the frame at most."""
    need(isinstance(region, dict) and all(k in region for k in ('left', 'top', 'width', 'height')), 'A region is {left, top, width, height}, fractions of the frame.')
    try:
        l, t, w, h = (float(region[k]) for k in ('left', 'top', 'width', 'height'))
    except (TypeError, ValueError):
        need(False, 'A region is four numbers between 0 and 1.')
    need(0 <= l < 1 and 0 <= t < 1 and 0 < w <= 1 and 0 < h <= 1 and l + w <= 1 + 1e-9 and t + h <= 1 + 1e-9, 'The region lies inside the frame: left + width and top + height are at most 1.')
    need(w * h <= REGION_MAX + 1e-9, f'The region covers {w * h * 100:.0f} % of the frame: an edit changes one region of a third at most; a bigger change is a new picture made with the golden picture as a reference (design/111 F11).')
    return {'left': l, 'top': t, 'width': w, 'height': h}


# ---------- design/111 F10: a repeating material has one measured spec, used in numbers by every picture ----------

def materials_of(plan, element_id=None, shot=None):
    """The repeating materials a picture shows: the element itself, or the materials among its shot's elements."""
    ids = {element_id} | set((shot or {}).get('element_ids') or [])
    return [e for e in plan.get('elements') or [] if e['id'] in ids and e.get('material_spec')]


def material_sentence(element):
    spec = element['material_spec']
    sizes = ', '.join(f"{d['part']} {d['measure']} {d['value']:g} {d.get('unit') or ''}".strip() for d in spec.get('dimensions') or [] if d.get('value') is not None)
    parts = [f"Material spec, {element['name']}: {sizes}" if sizes else f"Material spec, {element['name']}", f"laid {spec['laid']}"]
    if spec.get('joint'):
        parts.append(f"joints {spec['joint']}")
    parts.append(f"pattern: {spec['pattern']}")
    if spec.get('proportions'):
        parts.append('proportions: ' + '; '.join(spec['proportions']))
    return '; '.join(parts) + '.'


def material_ratio(spec):
    """The long face against the height, from the spec's unit sizes: '2.1 : 1'; '' when a side is missing."""
    by = {}
    for d in spec.get('dimensions') or []:
        if d.get('value'):
            by.setdefault(d['measure'].lower(), float(d['value']))
    long_, high = by.get('length') or by.get('long'), by.get('height') or by.get('thickness') if 'length' in by and 'height' not in by and len(by) == 2 else by.get('height')
    if not long_ or not high:
        return ''
    return f'{long_ / high:.1f} : 1'


def material_lines(element):
    """F10's must line: the unit ratio measured on three units and the pattern across three courses."""
    spec = element['material_spec']
    ratio = material_ratio(spec)
    return [{'check': f"material: {element['name']}", 'weight': 'must',
             'pass_when': 'measured on three units, ' + (f"the long face is {ratio} (length to height) and " if ratio else '') + f"the units are laid {spec['laid']}; across three courses the pattern is: {spec['pattern']}"
                          + (f"; joints {spec['joint']}" if spec.get('joint') else '')}]


def material_key(element_id):
    return 'element:' + element_id


def material_approved(session, element):
    return (session.get('spec_approvals') or {}).get(material_key(element['id']), {}).get('digest') == spec_digest(element['material_spec'])


# ---------- design/110 F4, F5, F6: what the server composes into every start and end prompt, and the take ----------

def _names(plan):
    return {e['id']: e['name'] for e in plan.get('elements') or []}


def inventory_line(plan, scene, shot, when):
    """F4: every movable thing of the shot, counted and placed; the end is the start after the action."""
    names = _names(plan)
    scene_marks = {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
    items, holders = [], []
    for s in shot.get('subjects') or []:
        state = s.get(when) or {}
        for o in state.get('objects') or []:
            items.append(f"{names.get(o['element_id'], o['element_id'])} \u00d7 {o['count']} {place_words(scene_marks, o.get('place'))}".strip())
        held = state.get('holding') or []
        if held:
            items += [f"{names.get(h, h)} \u00d7 {held.count(h)} in {s['element_id']}'s hands" for h in dict.fromkeys(held)]   # ['BRICK', 'BRICK'] counts two
        elif any((x.get('holding') for x in (s.get('start'), s.get('end')) if x)):
            holders.append(f"{s['element_id']} holds nothing")
    if not items and not holders:
        return ''
    return 'Inventory, exactly: ' + '; '.join(items + holders) + '. Nothing else of these kinds in frame; nothing rests on top of the stack.'


def _prop_end_words(marks, p):
    e = p.get('end') or {}
    if e.get('where') == 'set_down':
        return f"set down {place_words(marks, e.get('position'))}"
    if e.get('where') == 'carried_out':
        return f"out of frame, carried out by {e.get('cause') or 'the action'}"
    return f"still in {p['holder']}'s hand"


def tool_lines(plan, scene, shot, when):
    """F5: the same sentence for every held tool in the start prompt, the end prompt and the motion text; where it is at the end comes from the action."""
    names, marks = _names(plan), {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
    out = []
    for p in shot.get('props') or []:
        name = names.get(p['element_id'], p['element_id'])
        same = (f"The same {name}: it keeps its shape, size, colour and handle (where it has one) in every picture it appears in; {p['holder']} holds nothing else; no second one appears; "
                "it is fully inside the frame. ")
        if when == 'start':
            out.append(same + f"At the start it is {place_words(marks, p.get('start'))}.")
        elif when == 'end':
            out.append(same + f"At the end it is {_prop_end_words(marks, p)}.")
        else:
            out.append(same + f"By the end it is {_prop_end_words(marks, p)}; it never changes into another thing and never simply disappears.")
    return out


def _side(h):
    """'the left side', 'his back': the camera side with its own article."""
    side = str(h.get('camera_side') or '').strip()
    return side if re.match(r'(the|his|her|its|their)\b', side, re.I) else 'the ' + side


def _turns(shot, subject_id=None, name=''):
    """A change of this shot that is a turn; of this subject when one is named (its id or name in the change's words)."""
    for ch in shot.get('changes') or []:
        what = (ch.get('what') or '').lower()
        if re.search(r'\bturn', what) and (subject_id is None or subject_id.lower() in what or (name and name.lower() in what)):
            return True
    return False


def heading_lines(scene, shot, when, names=None):
    """F6: each subject's heading against a landmark and a frame edge, the side toward the camera, kept unless the action is a turn; a living thing that
    is not the actor gets its own small change at the end."""
    marks = {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
    out = []
    for s in shot.get('subjects') or []:
        state = s.get(when if when != 'motion' else 'end') or {}
        h = state.get('facing')
        if not isinstance(h, dict):
            continue
        lm = marks.get(h.get('landmark_id'), h.get('landmark_id', ''))
        if s.get('behaviour') == 'holds':
            if when in ('end', 'motion') and s.get('start', {}).get('position') != state.get('position'):
                out.append(f"{s['element_id']} has moved at least one body-length toward {marks.get((state.get('position') or {}).get('landmark_id'), '')} and turned a little; it does not stand where it stood in the start.")
            else:
                out.append(f"Heading of {s['element_id']}: front toward {lm} at the {h.get('edge')} edge; {_side(h)} faces the camera.")
            continue
        if when in ('end', 'motion') and _turns(shot, s['element_id'], (names or {}).get(s['element_id'], '')):
            out.append(f"Heading of {s['element_id']}: it turns, as the change says; at the end its front is toward {lm} at the {h.get('edge')} edge; {_side(h)} faces the camera.")
        else:
            out.append(f"Heading of {s['element_id']}: front toward {lm} at the {h.get('edge')} edge; {_side(h)} faces the camera; it must not turn, reverse or show its other side.")
    return out


def composed_block(plan, scene, shot, when):
    """What the server writes under the writer's prompt of a start or an end picture: the targets (F1, F3), the headings (F6), the tools (F5), the inventory (F4)."""
    lines = ((start_targets(scene, shot) if when == 'start' else end_targets(scene, shot)) + gaze_lines(plan, scene, shot, when) + heading_lines(scene, shot, when, _names(plan))
             + ([size_line(plan, shot)] if size_line(plan, shot) else []) + person_lines(plan, scene, shot) + group_lines(plan, shot)   # design/111 F15, F16, F17
             + tool_lines(plan, scene, shot, when) + (([fixed_line(scene, shot)] if fixed_line(scene, shot) else []) + sits_lines(plan, scene, shot) if when == 'end' else []))   # design/111 F7, F8, F9
    inv = inventory_line(plan, scene, shot, when)
    return '\n'.join(lines + ([inv] if inv else []))


def with_composed(prompt, block):
    """The block's lines that the prompt does not carry yet, appended; nothing twice."""
    missing = [l for l in block.split('\n') if l.strip() and l.strip()[:40] not in prompt]
    return prompt.rstrip() + '\n' + '\n'.join(missing) if missing else prompt


def picture_rule_lines(plan, scene, shot, when):
    """The must lines of F4 (start and end), F5 and F6 (the end) on a keyframe's check."""
    names = _names(plan)
    marks = {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
    out = []
    out += group_rule_lines(plan, shot)   # design/111 F17
    for pl_ in person_lines(plan, scene, shot):   # design/111 F16: both layers are checked
        out.append({'check': 'person kept: ' + pl_.split(':')[0], 'weight': 'must', 'pass_when': pl_.rstrip('.') + '; no other garment colours, no other build, hair or skin'})
    if size_line(plan, shot):   # design/111 F15: the true-sizes question is a must when size is the message
        out.append({'check': 'size is the point', 'weight': 'must', 'pass_when': size_line(plan, shot)[len('Size is the point: '):].rstrip('.')})
    inv = inventory_line(plan, scene, shot, when)
    if inv:
        out.append({'check': 'inventory', 'weight': 'must', 'pass_when': 'the picture holds exactly these things, in these counts and places, and nothing else of these kinds: ' + inv[len('Inventory, exactly: '):]})
    if when == 'end':
        if gaze_lines(plan, scene, shot, 'end'):   # design/111 F7
            out.append({'check': 'eye lines', 'weight': 'must', 'pass_when': 'each person\'s eyes are on the named target, head turned and mouth as written: ' + ' '.join(gaze_lines(plan, scene, shot, 'end'))
                        + '; no one looks at the lens; no one looks where they looked in Image 1 unless named'})
        if fixed_line(scene, shot):   # design/111 F8
            marks_ = {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
            out.append({'check': 'background kept', 'weight': 'must', 'pass_when': ', '.join(marks_.get(l, l) for l in shot.get('fixed') or []) + ' are in the same place, size and light as in Image 1; none has moved or gone'})
        for sl in sits_lines(plan, scene, shot):   # design/111 F9
            out.append({'check': 'sits: ' + sl.split(' rests')[0], 'weight': 'must', 'pass_when': sl.rstrip('.') + '; the placed thing sits on its support with full contact and in line with its neighbours'})
        for p in shot.get('props') or []:
            out.append({'check': 'same tool', 'weight': 'must', 'pass_when': f"the {names.get(p['element_id'], p['element_id'])} {p['holder']} held is the same one as in Image 1 (shape, size, colour, handle where it has one), "
                                                                             f"and it is {_prop_end_words(marks, p)}; it has not changed into another thing or vanished"})
        if any(isinstance((s.get('end') or {}).get('facing'), dict) for s in shot.get('subjects') or []):
            out.append({'check': 'heading kept', 'weight': 'must', 'pass_when': 'each travelling subject faces the same landmark and shows the same side as in Image 1' +
                        (' (except the subject whose change is a turn, which faces its new heading)' if _turns(shot) else '') + '; no subject is flipped or reversed'})
    return out


# ---------- design/110 rule 0: an open question is a server state ----------

def _item_kind(store, session, item):
    """picture, element or shot of this run; None for anything else."""
    if item in session['references']:
        return 'picture'
    plan = current_plan(store, session) if session.get('current') else None
    if plan and any(e['id'] == item for e in plan['elements']):
        return 'element'
    try:
        locate(store, session, item)
        return 'shot'
    except (ValueError, Problem):
        return None


def _open(session, item, question, choices, by, cost_inr=None, fork=None):
    qs = session.setdefault('questions', {})
    need(item not in qs, f"{item} already waits for an answer: {qs.get(item, {}).get('question', '')}")
    need(str(question or '').strip(), 'Say the question in one sentence.')
    choices = [str(c).strip() for c in (choices or []) if str(c).strip()]
    need(len(choices) >= 2, 'Give at least two choices, the concrete ones (and the paid cost of each where there is one).')
    qs[item] = {'item': item, 'question': str(question).strip(), 'choices': choices, 'by': by, 'at': datetime.now(timezone.utc).isoformat(),
                **({'cost_inr': float(cost_inr)} if cost_inr is not None else {}), **({'fork': fork} if fork else {})}
    return qs[item]


def _no_question(session, *items):
    """Derived work from an item with an open question waits (rule 0): the end, a fix, a take, a binding, a placement, a picture made from it."""
    qs = session.get('questions') or {}
    for item in items:
        q = qs.get(item) if item else None
        need(not q, f"{item} waits for the operator's answer: {q['question'] if q else ''} Answer it on the page or with `vw visuals answer --item {item} --answer \"…\"`; "
                    f"nothing is made from {item} until then.")


def ask(store, user, run, outputs, item, question, choices, cost_inr=None):
    """The assistant's question at a fork: one sentence, the concrete choices, the paid cost; recorded on the item, shown on its card, in status and in waiting."""
    session = session_of(store, run, outputs)
    need(_item_kind(store, session, item), f'{item} is not a picture, a shot or an element of this run.')
    q = _open(session, item, question, choices, user['id'], cost_inr)
    save_session(store, run, session)
    return {**q, 'next': f"Question recorded on {item}: the operator answers on the page (the buttons on its card) or you record their words with `vw visuals answer --item {item} --answer \"…\"`; "
                         f"nothing is made from {item} until then. Wait with `vw visuals status --wait`."}


def answer(store, user, run, outputs, item, words):
    """The operator's answer closes the question; a server-raised one acts on it (fork 3 keeps one picture for the slot; fork 4 clears the parent)."""
    session = session_of(store, run, outputs)
    q = (session.get('questions') or {}).get(item)
    need(q, f'No open question on {item}.')
    words = str(words or '').strip()
    need(words, 'Say the answer: one of the choices, or your own words.')
    if q.get('fork') == 'slot':
        need(words in q['choices'], f"Answer with one of {', '.join(q['choices'])}: the picture to keep.")
        for rid in q['choices']:
            r = session['references'].get(rid)
            if rid != words and r and r.get('status') != 'rejected':
                r.update(status='rejected', rejection={'notes': f'rule 0: the operator kept {words} for {item}', 'quote': words, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()})
    if q.get('fork') == 'parent' and words == q['choices'][0]:
        session['references'][item]['parent_ok'] = True
    if q.get('fork') == 'not_yet' and words == q['choices'][1]:   # F3: approved anyway, on the operator's word; the flaw is theirs to carry as a parent too
        session['references'][item].update(not_yet_ok=True, parent_ok=True)
    record = {**q, 'answer': words, 'answered_by': user['id'], 'answered_at': datetime.now(timezone.utc).isoformat()}
    del session['questions'][item]
    session.setdefault('answered', []).append(record)
    save_session(store, run, session)
    return {**record, 'next': f'Answered: {words}. Work on {item} goes on from this answer.'}


def round_undo(store, user, run, outputs, quote):
    """Done on a pass is undone until the next step used its result: pass 1 until a pick is saved, pass 2 until a sheet was made from the pictures."""
    session = session_of(store, run, outputs)
    rd = session.get('round')
    need(rd and rd.get('pass') in (2, 'complete'), 'Nothing to undo: the round is at pass 1 or has not started.')
    searches = session.get('searches') or {}
    own = [r['search_id'] for r in rd['elements'].values() if r.get('search_id')]
    if rd['pass'] == 2:
        picked = [sid for sid in own if (searches.get(sid) or {}).get('picked')]
        need(not picked, f"Pass 1 cannot be undone: a pick is saved from {', '.join(picked)}; reject the pictures you do not want instead.")
        to = 1
    else:
        sources = {r['id'] for r in session['references'].values() if r.get('element_id') in rd['elements'] and r.get('kind') in ('frame', 'web', 'supplied', 'isolated')}
        used = [r['id'] for r in session['references'].values() if r.get('kind') == 'sheet' and r.get('status') != 'rejected' and r.get('element_id') in rd['elements']
                and any(p.get('id') in sources for p in (r.get('generation') or {}).get('parents') or [])]
        need(not used, f"Pass 2 cannot be undone: sheet {used[0] if used else ''} was made from this round's pictures; reject that sheet first.")
        to = 2 if own else 1
    rd.setdefault('undone', []).append({'from': rd['pass'], 'to': to, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'quote': said(quote, 'Undone', user)})
    rd['pass'] = to
    save_session(store, run, session)
    return {'pass': to, 'next': f'Done undone: the round is at pass {to} again; nothing already saved was removed.'}


def supply_own(conn, store, user, run, outputs, element_id, content=None, url='', name=''):
    """design/110 rule 0 (Revathi's addition): the operator's own picture from the page, a file or an https link, stored as an approved reference of the element."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    element = next((e for e in plan['elements'] if e['id'] == element_id), None)
    need(element, f'{element_id} is not an element of the plan.')
    url = str(url or '').strip()
    need(content or url.startswith('https://'), 'Give a file or an https link to the picture.')
    if not content:
        content = fetch_image(url)
    body = {'request_id': str(uuid.uuid4()), 'element_id': element_id, 'name': str(name or '').strip() or f'own-{element_id}', 'kind': 'supplied', 'subject': element['name']}
    row = add_reference(conn, store, user, run, outputs, body, content)
    session = session_of(store, run, outputs)
    r = session['references'][row['id']]
    r.update(status='approved', approval={'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'sha256': r['sha256'], 'quote': 'Added by the operator on the page'})
    if url:
        r.setdefault('source', {})['url'] = url
    save_session(store, run, session)
    return {**r, 'next': f"Your picture is saved and approved for {element_id}" + ('; its sheet is marked "sources changed": the assistant makes a new one.' if any(
        x.get('kind') == 'sheet' and x.get('sources_changed') and x.get('element_id') == element_id for x in session['references'].values()) else '.')}


def waiting(session, plan, code, take_rows):
    """design/97 W1, W3, W4: what waits for the operator's verdict, in film order, each with its label and link: a checked candidate (a reference,
    the style sheet, a still, a start or end image, a sequence once every state is made), a ready take, a drawing spec, a reuse."""
    if not plan:
        return []
    shots = {sh['id']: sh for _, sh in _accepted_shots(plan, session)}
    items = []

    def add(at, label, step, group, item):
        if not any(i['label'] == label for _, i in items):
            items.append((at, {'label': label, 'step': step, 'group': group, 'item': item, 'link': item_link(code, step, group, item)}))
    title = lambda sh: f" · {sh['title']}" if sh.get('title') else ''
    ready = lambda r: r.get('status') == 'candidate' and r.get('sha256') and not r.get('check_pending')
    pending_specs = []
    for r in session['references'].values():
        sh = shots.get(made_for(session, r) or '')
        if not ready(r):
            continue
        if r.get('kind') == 'style':
            add(-1, 'Graphic style · style sheet', 'pictures', STYLE, r['id'])
        elif r.get('kind') in ('frame', 'supplied', 'web', 'isolated', 'sheet'):
            add(-1, f"Reference sheet · {r['element_id']}" if r['kind'] == 'sheet' else f"Reference · {r['element_id']} · {r['kind']}", 'references', r['element_id'], r['id'])
        elif sh and route_of(sh) == 'still':
            add(sh['start_frame'], f"Still · {sh['id']}{title(sh)}", 'pictures', sh['id'], r['id'])
        elif sh and route_of(sh) == 'video':
            add(sh['start_frame'], f"Start and end · {sh['id']}{title(sh)}", 'takes', sh['id'], r['id'])
    for sid, sh in shots.items():
        if route_of(sh) == 'graphic_sequence':
            try:
                chain = state_chain(session, sid) or []
            except ValueError:   # two pictures for one step: the page shows the problem
                chain = []
            if chain and len(chain) == len(sh.get('states') or []) and any(r['status'] == 'candidate' for r in chain) and not any(r.get('check_pending') for r in chain):
                add(sh['start_frame'], f"Graphics · {sid}{title(sh)} · {len(chain)} states", 'pictures', sid, chain[-1]['id'])
        spec = sh.get('drawing_spec')
        if spec and (session.get('spec_approvals') or {}).get(sid, {}).get('digest') != spec_digest(spec) and not correction_pending(session, sid, spec):
            pending_specs.append(sh['start_frame'])
    if pending_specs:   # design/106 D5: one item, one table, one approval
        add(min(pending_specs), f"Drawing specs · {len(pending_specs)} to approve", 'pictures', 'specs', 'specs')
    mats = [e for e in plan.get('elements') or [] if e.get('material_spec') and not material_approved(session, e) and not correction_pending(session, material_key(e['id']), e['material_spec'])]
    if mats:   # design/111 F10: approved once, on the References step
        add(-1, f"Material specs · {len(mats)} to approve", 'references', mats[0]['id'], 'specs')
    for item, q in (session.get('questions') or {}).items():   # design/110 rule 0: an open question comes first
        r = session['references'].get(item)
        sh = shots.get(made_for(session, r) if r else item)
        step = 'references' if (r and r.get('kind') in ('frame', 'supplied', 'web', 'isolated', 'sheet')) or (not r and not sh) else 'takes' if sh and route_of(sh) == 'video' else 'pictures'
        add(-2, f"Question · {item} · {q['question'][:80]}", step, (r or {}).get('element_id') if step == 'references' else (sh or {}).get('id') or item, item)
    for r in session['references'].values():
        if r.get('kind') == 'sheet' and r.get('sources_changed') and r.get('status') != 'rejected':
            add(-1, f"Reference sheet · {r['element_id']} · sources changed", 'references', r['element_id'], r['id'])
    for sid in session.get('reuse_pending') or {}:
        sh = shots.get(sid) or {'start_frame': 0}
        add(sh['start_frame'], f'Reuse · {sid}', 'takes' if sh.get('visual_type') == 'video' else 'pictures', sid, 'reuse')
    for j in take_rows:
        sh, reviews = shots.get(j['unit']), session['reviews'].get(str(j['id'])) or []
        if sh and j['status'] == 'ready' and (session['selections'].get(j['unit']) or {}).get('job_id') != str(j['id']) and not (reviews and reviews[-1]['decision'] == 'rejected'):
            add(sh['start_frame'], f"Take · {j['unit']}{title(sh)}", 'takes', j['unit'], str(j['id']))
    return [i for _, i in sorted(items, key=lambda x: x[0])]


def state_chain(session, shot_id):
    """design/94 A2: the not-rejected pictures made for a shot, in order: the first has no parent among them, each next is made from the one before.
    None when no picture records the shot; a fork names both cards. design/95: a fix not rejected stands in for its original (F1); a picture made
    from a rejected one leaves the order (F2)."""
    shot_pics = {r['id']: r for r in session['references'].values() if r.get('kind') in ('keyframe', 'state') and made_for(session, r) == shot_id}
    if not shot_pics:
        return None
    stand = {r['fix_of']: r['id'] for r in shot_pics.values() if r.get('fix_of') in shot_pics and r.get('status') != 'rejected'}

    def parents_of(r):
        if r.get('fix_of') in shot_pics:   # a fix sits where its original sat
            return parents_of(shot_pics[r['fix_of']])
        return [stand.get(p.get('id'), p.get('id')) for p in (r.get('generation') or {}).get('parents') or [] if p.get('id') in shot_pics]

    alive = {}

    def live(rid):
        if rid not in alive:
            r = shot_pics[rid]
            alive[rid] = False   # a loop never counts
            alive[rid] = (r.get('status') in ('candidate', 'approved') and bool(r.get('sha256')) and rid not in stand and all(live(p) for p in parents_of(r)))
        return alive[rid]
    mine = [r for r in shot_pics.values() if live(r['id'])]
    parent = {r['id']: parents_of(r) for r in mine}
    chain, level = [], [r for r in mine if not parent[r['id']]]
    while level:
        need(len(level) == 1, f"two pictures for state {len(chain) + 1}: {', '.join(sorted(r['name'] for r in level))}; reject one.")
        chain.append(level[0])
        level = [r for r in mine if chain[-1]['id'] in parent[r['id']]]
    return chain


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
    if meta.get('kind') in ('frame', 'supplied', 'web', 'isolated'):   # design/110: a sheet made before this picture is stale; the old one stays approved until the new one is
        for r in session['references'].values():
            if r.get('kind') == 'sheet' and r.get('element_id') == meta.get('element_id') and r.get('status') != 'rejected':
                r['sources_changed'] = True
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
KIND_MATCH = {'person': {'person'}, 'animal': {'person', 'other'}, 'object': {'tool', 'material', 'machine', 'vehicle', 'other', 'text'}, 'place': {'structure', 'other'},
              'material': {'material', 'other'}, 'process': {'tool', 'machine', 'material', 'other'}}   # design/91 N6


def _words(text):
    return {(w[:-1] if w.endswith('s') and len(w) > 4 else w) for w in re.findall(r'[a-z]{4,}', str(text or '').lower()) if w not in STOP}   # bricks and brick are one word


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
                if len(shared) < 2:   # L44: one shared word is noise ("brick" matched a kiln to every wall); two name the thing
                    continue
                score = len(shared) + (1 if ent.get('kind') in KIND_MATCH.get(e['kind'], set()) else 0)
                if score > (hits.get(clip['clip']) or {}).get('score', 0):
                    hits[clip['clip']] = {'clip': clip['clip'], 'seconds': ent.get('first_seen_s'), 'entity': ent.get('name'), 'description': ent.get('description'), 'score': score}
        out[e['id']] = sorted(hits.values(), key=lambda h: (-h['score'], str(h['clip'])))
    return out


IMAGE_LIMIT = 16 * 1024 * 1024
BROWSER = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', 'Accept': 'image/avif,image/webp,image/*,*/*;q=0.8'}


def _public_https(url):
    """The same guard as the provider transfer: HTTPS, a hostname, and a public address, so a picked picture never points the server at itself."""
    import ipaddress
    import socket
    from urllib.parse import urlsplit
    t = urlsplit(url)
    if t.scheme != 'https' or not t.hostname or t.username or t.password:
        raise ValueError(f'not an HTTPS picture address: {url[:80]}')
    addresses = socket.getaddrinfo(t.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError(f'{t.hostname} does not resolve to a public address')


def fetch_image(url):
    """design/73 R4: download a picked picture as a browser would: redirects followed (each hop checked), a browser identity, 20 s, 16 MiB."""
    import httpx
    target = url
    for _ in range(5):
        _public_https(target)
        r = httpx.get(target, headers=BROWSER, timeout=20, follow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get('location'):
            target = httpx.URL(target).join(r.headers['location']).__str__()
            continue
        if r.status_code != 200:
            raise ValueError(f'HTTP {r.status_code} from {httpx.URL(target).host}')
        if len(r.content) > IMAGE_LIMIT:
            raise ValueError('the picture is over 16 MiB')
        return r.content
    raise ValueError('too many redirects')


def _search_into(session, user, run, plan, element_id, keywords, quote, results=None):
    """The search on a loaded session (design/73 R3; the round of design/79 calls it for several elements before one save)."""
    need(any(e['id'] == element_id for e in plan['elements']), f'Unknown element {element_id}.')
    quote = said(quote, 'Searched', user)   # design/99 C4: the click is the operator's yes to the web search
    words = str(keywords or '').split()
    need(2 <= len(words) <= 6, 'Keywords are two to six words: the thing and its place or trade, nothing else (Google Images is not Google search).')   # R6
    rows = results if results is not None else apify.search_images(' '.join(words), 10)
    sid = digest({'run': str(run['id']), 'element': element_id, 'keywords': ' '.join(words), 'at': datetime.now(timezone.utc).isoformat()})[:12]
    session.setdefault('searches', {})[sid] = {'search_id': sid, 'element_id': element_id, 'keywords': ' '.join(words), 'quote': quote, 'by': user['id'],
                                               'at': datetime.now(timezone.utc).isoformat(), 'results': rows, 'picked': []}
    return {'search_id': sid, 'element_id': element_id, 'keywords': ' '.join(words), 'results': rows}


def search(store, user, run, outputs, element_id, keywords, quote):
    """design/73 R3: one Google Images search for an element, on the operator's yes; the ten rows kept on the session for the page and the tool."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    out = _search_into(session, user, run, plan, element_id, keywords, quote)
    save_session(store, run, session)
    return out


def pick(store, user, run, outputs, search_id, picks, quote):
    """design/73 R4: the ticked pictures, in the order ticked, each with its note, become web references of the element with their source."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    out = _pick_into(store, session, user, run, plan, search_id, picks, quote)
    save_session(store, run, session)
    return out


def _download_pick(row):
    """The full picture, else Google's thumbnail (smaller, always served): (png, size, which) or (None, None, the errors)."""
    errors = []
    for candidate, label in ((row['image_url'], 'picture'), (row.get('thumbnail'), 'thumbnail')):
        if not candidate:
            continue
        try:
            png, size = image_bytes(fetch_image(candidate))
            return png, size, label
        except (ValueError, OSError) as exc:
            errors.append(f'{label}: {exc}')
    return None, None, errors


def _download_picks(rows):
    """design/83 P1: every picked picture at once (eight downloads in flight), keyed by (search_id, n)."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {key: pool.submit(_download_pick, row) for key, row in rows.items()}
    return {key: f.result() for key, f in futures.items()}


def _pick_into(store, session, user, run, plan, search_id, picks, quote, fetched=None):
    s = (session.get('searches') or {}).get(search_id)
    need(s, f'Unknown search {search_id}.')
    words = str(quote or '').strip()
    quote = said(quote, 'Saved', user)   # design/99 C5
    need(isinstance(picks, list) and picks, 'Tick at least one picture.')
    rows = {r['n']: r for r in s['results']}
    chosen = []
    for p in picks:
        n = (p or {}).get('n')
        need(n in rows, f'Picture {n} is not in the search ({len(rows)} pictures).')
        chosen.append((rows[n], str((p or {}).get('note') or '').strip()))
    made, failed = [], []
    element_kind = next(e['kind'] for e in plan['elements'] if e['id'] == s['element_id'])
    if fetched is None:
        fetched = _download_picks({(search_id, row['n']): row for row, _ in chosen})
    for row, note in chosen:
        png, size, used = fetched[(search_id, row['n'])]
        if png is None:
            failed.append({'n': row['n'], 'site': row.get('site'), 'why': '; '.join(used)})
            continue
        rid = digest({'run': str(run['id']), 'search': search_id, 'n': row['n']})[:32]
        meta = {'element_id': s['element_id'], 'element_kind': element_kind, 'name': f"web-{s['element_id']}-{row['n']}", 'kind': 'web', 'subject': row.get('title') or s['keywords'],
                'width': size[0], 'height': size[1],
                'source': {'url': row['image_url'], 'page_url': row.get('page_url'), 'selection_reply': quote, 'note': note, 'search_id': search_id, 'n': row['n'], 'from_thumbnail': used == 'thumbnail'}}
        row = _store_reference(store, run, session, rid, png, meta)
        row.update(status='approved', approval={'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'sha256': row['sha256'],   # design/100 S1: ticking and saving is the approval
                                                'quote': words or f"Approved when saved by {user.get('name') or user.get('id')}"})
        made.append(row)
    need(made, 'None of the ticked pictures could be downloaded: ' + '; '.join(f"{f['n']} ({f['site']}): {f['why']}" for f in failed) + '. Pick others, or save one yourself and `vw visuals supply` it.')
    s['picked'] = [r['source']['n'] for r in made]
    s['failed'] = failed
    return {'search_id': search_id, 'references': made, 'failed': failed}


# ---------- design/79: the reference round, every element at once, two passes on one page ----------

def round_start(store, user, run, outputs, elements):
    """The assistant's one-shot preparation: for each element its grabbed footage frames and the keywords it would search; the page shows them all."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    kinds = {e['id']: e['kind'] for e in plan['elements']}
    need(isinstance(elements, list) and elements, 'The round lists the elements: [{element_id, frames, keywords}].')
    rows = {}
    for row in elements:
        eid = (row or {}).get('element_id')
        need(eid in kinds, f'Unknown element {eid}.')
        need(kinds[eid] != 'graphic', f'{eid} is a graphic: drawn from the plan, never referenced.')
        frames = list((row or {}).get('frames') or [])
        for fid in frames:
            r = session['references'].get(fid)
            need(r and r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved'), f'{fid} is not a footage frame of {eid}.')
        if not frames:   # the element's footage frames already grabbed count, whether or not the row names them
            frames = [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved')]
        rows[eid] = {'frames': frames, 'keywords': str((row or {}).get('keywords') or '').strip(), 'verdict': None, 'search_id': None, 'error': None}
    session['round'] = {'pass': 1, 'at': datetime.now(timezone.utc).isoformat(), 'by': user['id'], 'elements': rows, 'quote': None}
    save_session(store, run, session)
    return {'pass': 1, 'elements': len(rows)}


def round_searches(store, run, outputs, verdicts):
    """design/92 (L59): the round's searches, run before the run's lock (each may take two minutes); round_done saves them under the lock.
    {element: rows, or {'error': message}}; nothing when no first pass is waiting (round_done then refuses as before)."""
    session = session_of(store, run, outputs)
    rd = session.get('round') or {}
    if rd.get('pass') != 1:
        return {}
    wanted = {eid: ' '.join(str((verdicts.get(eid) or {}).get('keywords') or row['keywords']).split()) for eid, row in rd['elements'].items()
              if (verdicts.get(eid) or {}).get('verdict') == 'search'}
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {eid: pool.submit(apify.search_images, kw, 10) for eid, kw in wanted.items() if 2 <= len(kw.split()) <= 6}
    out = {}
    for eid, f in futures.items():
        try:
            out[eid] = f.result()
        except Exception as exc:   # this row's failure, recorded at the save
            out[eid] = {'error': exc.message if isinstance(exc, Problem) else str(exc)}
    return out


def round_done(store, user, run, outputs, verdicts, quote, found=None):
    """Pass 1 answered: the chosen frames approved with the words, the searches run with the words as the yes; pass 2 for the searched elements."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    rd = session.get('round')
    need(rd and rd.get('pass') == 1, 'No reference round is waiting for its first pass.')
    quote = said(quote, 'Pass 1 done', user)   # design/99 C6: the click approves the frames and says yes to the searches
    verdicts = verdicts or {}
    for eid, row in rd['elements'].items():
        if not row['frames']:   # a round posted without naming the frames: the element's grabbed frames count (as round_start does now)
            row['frames'] = [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved')]
        v = verdicts.get(eid) or {}
        need(v.get('verdict') in ('approve', 'search'), f'{eid}: a verdict is required, approve or search.')
        if v['verdict'] == 'approve':
            need(row['frames'], f'{eid} has no frame to approve: search instead.')
    stamp = {'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'quote': quote}
    for eid, row in rd['elements'].items():
        if verdicts[eid]['verdict'] == 'search':
            row['keywords'] = str(verdicts[eid].get('keywords') or row['keywords']).strip()
    if found is None:   # design/80 S5: the searches do not depend on each other; they run at once (the routes run them before the lock, design/92)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {eid: pool.submit(apify.search_images, ' '.join(row['keywords'].split()), 10) for eid, row in rd['elements'].items() if verdicts[eid]['verdict'] == 'search' and 2 <= len(row['keywords'].split()) <= 6}
    else:
        futures = found
    for eid, row in rd['elements'].items():
        v = verdicts[eid]
        row['verdict'] = v['verdict']
        if v['verdict'] == 'approve':
            for fid in row['frames']:
                r = session['references'][fid]
                if r['status'] == 'candidate':
                    r.update(status='approved', approval={**stamp, 'sha256': r['sha256']})
                    _feedback_image(session, run, user, r, 'pass', quote, '')
            continue
        try:
            got = futures.get(eid)
            got = got.result() if hasattr(got, 'result') else got
            if isinstance(got, dict) and got.get('error'):
                raise ValueError(got['error'])
            row['search_id'] = _search_into(session, user, run, plan, eid, row['keywords'], quote, got)['search_id']
            row['error'] = None
        except (Problem, ValueError) as exc:   # a failed search is this row's, the rest go on
            row['error'] = exc.message if isinstance(exc, Problem) else str(exc)
    rd['quote'] = quote
    rd['pass'] = 2 if any(r['search_id'] for r in rd['elements'].values()) else 'complete'
    save_session(store, run, session)
    return {'pass': rd['pass'], 'searched': [eid for eid, r in rd['elements'].items() if r['search_id']], 'errors': {eid: r['error'] for eid, r in rd['elements'].items() if r['error']}}


def round_picks(store, user, run, outputs, picks, quote):
    """Pass 2 answered: the ticked pictures per search become web references; the round is complete."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    rd = session.get('round')
    need(rd and rd.get('pass') == 2, 'No reference round is waiting for its second pass.')
    quote = said(quote, 'Pass 2 done', user)   # design/99 C6
    own = {r['search_id'] for r in rd['elements'].values() if r['search_id']}
    made, failed = [], {}
    for sid in (picks or {}):
        need(sid in own, f'Search {sid} is not in this round.')
    wanted = {}   # design/83 P1: every pick of every search downloaded at once, then recorded search by search in the ticked order
    for sid, rows in (picks or {}).items():
        results = {r['n']: r for r in (session.get('searches') or {}).get(sid, {}).get('results') or []}
        for p in rows or []:
            if (p or {}).get('n') in results:
                wanted[(sid, p['n'])] = results[p['n']]
    fetched = _download_picks(wanted)
    for sid, rows in (picks or {}).items():
        if not rows:
            continue
        try:
            out = _pick_into(store, session, user, run, plan, sid, list(rows), quote, fetched)
            made += out['references']
            if out['failed']:
                failed[sid] = out['failed']
        except (Problem, ValueError) as exc:
            failed[sid] = exc.message if isinstance(exc, Problem) else str(exc)
    rd['pass'] = 'complete'
    save_session(store, run, session)
    return {'complete': True, 'references': [r['id'] for r in made], 'failed': failed}


def _round_view(session):
    rd = session.get('round')
    if not rd:
        return None
    searches = session.get('searches') or {}
    return {**rd, 'elements': {eid: {**r, 'picked': (searches.get(r['search_id']) or {}).get('picked') if r.get('search_id') else None} for eid, r in rd['elements'].items()}}


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
    need((body['kind'] == 'style') == (body['element_id'] == STYLE), f'The style sheet is kind style with element {STYLE}, and only it.')   # design/89 C2
    element = {'id': STYLE, 'kind': 'style'} if body['element_id'] == STYLE else next((e for e in plan['elements'] if e['id'] == body['element_id']), None)
    need(element, 'Reference must identify an element in the current plan.')
    need(body['kind'] in ('isolated', 'sheet', 'keyframe', 'state', 'style'), 'Generated references are isolated, sheet, keyframe, state or style.')
    parents = [session['references'].get(p) for p in body.get('parents') or []]
    writer_prompt = body['prompt']   # the writer's words, before the server adds any line of its own
    for p in parents:   # design/71 P6 (the server check, design/74 L7): a retry starts from an approved picture, never from a rejected one
        if p and p.get('status') == 'rejected':
            need(False, f"{p['id']} was rejected: make the next {'state from the last approved state' if body['kind'] == 'state' else 'end image from the approved start, not from the candidate chain'}.")
    gold = golden_of(session, body['element_id'])
    if body.get('golden'):   # design/111 F11: the golden picture, written on the server's cue after the sheet (and the spec) are approved
        need(body['kind'] == 'isolated' and element['kind'] not in ('person', 'graphic', 'style'), 'A golden picture is a picture of an object, a place, an animal, a material or a process (kind isolated); a person\'s golden picture is its identity sheet.')
        need(not gold, f"{body['element_id']} already has its golden picture ({gold[:8] if gold else ''}); replacing it is the operator's decision (reject it first).")
        need(any(p and p.get('kind') == 'sheet' and p.get('status') == 'approved' and p.get('element_id') == body['element_id'] for p in parents), 'The golden picture is made from the element\'s approved sheet: name it among the parents.')
        if element.get('identity') == 'exact' and element['kind'] == 'object':   # L41 lives here now: the golden picture carries the footage; every edit inherits it
            frames = [r for r in session['references'].values() if r.get('element_id') == body['element_id'] and r.get('kind') == 'frame' and r.get('status') == 'approved']
            need(not frames or any(p and p.get('kind') == 'frame' and p.get('element_id') == body['element_id'] for p in parents),
                 f"{body['element_id']} is the client's own: send one of its approved footage frames as a parent of the golden picture ({', '.join(r['id'][:8] for r in frames)}).")
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
    need(len(parents) <= 4, f"{len(parents)} pictures: at most four go in with a prompt (the picture edited or the scene parent, one identity sheet per person in frame, one material or look frame); "
         f"say the rest in words. Extra: {', '.join(p['id'][:8] for p in parents[4:] if p)} (design/111 F21).")
    named_n = len(body.get('parents') or [])
    for k, p in enumerate(parents[named_n:], named_n + 1):   # F21: the server names the pictures it added itself (the start's own sheets)
        if p:
            body = {**body, 'prompt': with_composed(body['prompt'], f"Image {k} is the approved {p.get('kind') or 'reference'} of {p.get('element_id')}: take identity from it, nothing else.")}
    if parents and not body.get('fix_of'):   # F21: one job line per picture
        missing_ = library.image_names_missing(body['prompt'], len(parents))
        need(not missing_, f"the prompt does not say what Image {', '.join(map(str, missing_))} is for: one job line per picture ('Image k is …: take …') (design/111 F21).")
    if not body.get('shot_id') and body['kind'] in ('keyframe', 'state'):   # design/94 R1.1: a state, an end image or a fix takes its parent's shot
        body['shot_id'] = next((p['shot_id'] for p in parents if p and p.get('kind') in ('keyframe', 'state') and p.get('shot_id')), None)
        need(body['shot_id'] or body.get('fix_of'), f"Name the shot this {body['kind']} is for (--shot): a picture is listed, checked and placed only in its own shot.")
    _no_question(session, body['element_id'], body.get('shot_id'), *[p['id'] for p in parents if p])   # design/110 rule 0
    if not body.get('fix_of'):   # rule 0, fork 4: a parent approved with a failed must line is asked about once; a fix is that line's remedy
        for p in parents:
            failed = [l.get('check') for l in ((p or {}).get('check') or {}).get('must_failed') or []]
            if p and p.get('status') == 'approved' and p.get('kind') in ('keyframe', 'state') and failed and not p.get('parent_ok'):
                _open(session, p['id'], f"{p['id']} was approved with a failed must line ({', '.join(failed)}): use it as the parent of new pictures anyway, or make a new one?",
                      ['use it as the parent', 'make a new one'], 'server', fork='parent')
                save_session(store, run, session)
                need(False, f"{p['id']} was approved with a failed must line ({', '.join(failed)}): the operator decides first; the question is on its card (`vw visuals answer --item {p['id']} …`).")
    found = guarded(lambda: locate(store, session, body['shot_id'])) if body.get('shot_id') else None   # design/91 N8: the shot this picture is for
    named = found[3] if found else None
    if body['kind'] == 'keyframe':
        _keyframe_gates(session, plan, body, parents, named)   # design/77 L35, L38, L41
    answer = body.get('answer')
    if answer is not None:   # design/68 L5: the library's answer form travels with the prompt
        try:
            library.check_answer(answer, writer_prompt)
            library.check_exact_places(answer, {lm['id'] for lm in (found[2].get('landmarks') if found else []) or []})   # design/111 F13
            library.check_quoted(writer_prompt, library.exact_entries(answer))
        except ValueError as exc:
            need(False, str(exc))
    elif not body.get('fix_of'):
        try:
            library.check_quoted(writer_prompt, [])   # design/111 F13: quoted words with no exact-text field at all
        except ValueError as exc:
            need(False, str(exc))
    role = body.get('role') or ''   # design/106 T1, T2: a start made from an old start says so; without a role, a keyframe parent means an end
    need(role in ('', 'start', 'end'), 'role is start or end.')
    need(not role or body['kind'] == 'keyframe', 'A role (start or end) is for a keyframe.')
    is_end = role == 'end' if role else any(p['kind'] == 'keyframe' for p in parents)
    need(not is_end or any(p['kind'] == 'keyframe' for p in parents), 'An end image is made from its start: name the start keyframe among its parents.')   # review 27 Oct
    if gold and body['kind'] in ('keyframe', 'isolated') and not is_end and not body.get('golden') and not body.get('fix_of'):   # design/111 F11: Image 1 is the golden picture
        need(parents and parents[0] and parents[0]['id'] == gold, f"{body['element_id']} has its golden picture ({gold[:8]}): it is Image 1 of every picture of {body['element_id']}; name it first in --parents and change one thing.")
    for p in parents:   # F11: the chain always goes back to the golden picture
        if not p or body.get('fix_of') or body['kind'] == 'state':
            continue
        need(not p.get('fix_of'), f"{p['id']} is a fix round's output: a fix round is never a parent; use the golden picture" + (f' ({gold[:8]})' if gold else '') + ' or the approved start.')
        if p.get('kind') in ('keyframe', 'state') and _derived(session, p) and not (is_end and _picture_word(store, session, p) == 'start image'):
            need(False, f"{p['id']} is a derived picture (made from {', '.join(q.get('id', '')[:8] for q in (p.get('generation') or {}).get('parents') or [])}): a derived picture is never the parent of another; "
                        + (f'use the golden picture {gold[:8]}' if gold else 'use an approved sheet or the golden picture') + ' (an end is made from its approved start).')
    region = check_region(body['region']) if body.get('region') else None   # F11's edit rule: one change inside one region, masked, the start copied back outside it; without a region the
    # picture is rule 2's new picture (several things change, or the framing), made whole as before
    if body['kind'] == 'keyframe':
        body = {**body, 'role': 'end' if is_end else 'start'}   # a copy: the caller's request is never changed
    variants = int(body.get('variants') or 1)   # design/86 K4: two candidates for a start keyframe, the operator picks
    need(variants in (1, 2), 'variants is 1 or 2.')
    need(variants == 1 or (body['kind'] == 'keyframe' and not is_end), 'Two candidates are for a start keyframe only.')
    pending_end = None
    if body.get('end_prompt'):   # design/86 K1: the end prompt written with the start; the server makes the end from the approved start
        need(body['kind'] == 'keyframe' and not is_end, 'An end prompt goes with a start keyframe.')
        library.check_prompt(body['end_prompt'])
        need(re.search(r'\bimage 1\b', body['end_prompt'], re.I), 'The end prompt names Image 1 as the start image.')
        if body.get('end_answer') is not None:
            try:
                library.check_answer(body['end_answer'], body['end_prompt'])
            except ValueError as exc:
                need(False, 'end answer: ' + str(exc))
        pending_end = {'prompt': body['end_prompt'], 'answer': body.get('end_answer'), **({'region': check_region(body['end_region'])} if body.get('end_region') else {})}   # design/111 F11
    lines, warns = _graphic_lines(session, plan, body, parents, answer, named)   # design/89 C, D; design/91 N6, N8, N10, N14
    if body['kind'] == 'keyframe' and not is_end and named is not None:
        lines = lines + not_yet_lines(named)   # design/110 F3: a start shows the action not yet done (a fix of a start too)
    if answer is not None and library.exact_entries(answer):   # design/111 F13: every picture with exact text, not only a graphic
        lines = lines + [l for l in exact_text_lines(answer, {lm['id']: lm['description'] for lm in (found[2].get('landmarks') if found else []) or []}) if l['check'] not in {x['check'] for x in lines}]
        body = {**body, 'prompt': with_composed(body['prompt'], exact_text_block(answer))}
    for eid in [body['element_id']] + [x for x in (named or {}).get('element_ids') or [] if x != body['element_id']]:   # design/111 F12: 'none of these', in every prompt that shows the element
        nl = not_this_line(session, plan, eid, named, found[2] if found else None)
        if nl:
            body = {**body, 'prompt': with_composed(body['prompt'], nl)}
    for m in materials_of(plan, body['element_id'], named):   # design/111 F10: the spec approved first, the words in numbers, the sentence and the line
        need(material_approved(session, m), f"the material spec of {m['id']} is not approved, or changed since: approve it on the References step (or `vw visuals spec --element {m['id']}`) before a picture shows it.")
        try:
            library.check_material_prompt(writer_prompt)
        except ValueError as exc:
            need(False, str(exc))
        lines = lines + material_lines(m)
        body = {**body, 'prompt': with_composed(body['prompt'], material_sentence(m))}
    if body['kind'] == 'keyframe' and found and named.get('visual_type') == 'video':   # design/110 F4, F5, F6: the lines, and the block under the writer's prompt
        lines = lines + picture_rule_lines(plan, found[2], named, 'end' if is_end else 'start')
        if not body.get('fix_of'):
            body = {**body, 'prompt': with_composed(body['prompt'], composed_block(plan, found[2], named, 'end' if is_end else 'start'))}
    lw = light_warning(found[2], body['kind'], body['prompt']) if found else None   # design/103 A1
    if found and element['kind'] not in ('graphic', 'style') and body['kind'] in ('keyframe', 'isolated'):   # design/104 C5: the scene's light and air, the shot's size, real sizes
        lines = list(lines or []) + picture_lines(found[2], found[3], plan['elements'])
    if lw:
        warns.append(lw)
    missing = [] if body.get('fix_of') else library.image_names_missing(body['prompt'], len(body.get('parents') or []))   # design/96 C1: the pictures it names, not those the server adds
    if missing:
        warns.append(f"the edit sends {len(body['parents'])} pictures but the prompt does not name Image {', '.join(map(str, missing))}: name each as Image 1 to Image N "
                     'with what to take from it' + NEXT_RELEASE)
    warns += [f"made from {p['id']}, which was made for {p['shot_id']}; this picture is listed and checked under {body['shot_id']}"   # design/95 F7: on purpose, or a slip
              for p in parents if body.get('shot_id') and p and p.get('kind') in ('keyframe', 'state') and p.get('shot_id') not in (None, body['shot_id'])]
    if (element['kind'] not in ('graphic', 'style') and not body.get('fix_of') and (body['kind'] in ('keyframe', 'isolated') or named)
            and not str(plan['foundation'].get('studio_background') or '').strip()):   # design/91 N9: a picture in the film is in the film's world
        lines.append(WORLD_LINE)
    check_cap(conn, run, session, prices()['image_inr'] * variants, 'one image' if variants == 1 else 'two candidates')   # design/65 B7
    op = 'edit' if parents else 'generate'
    made = []
    for n in range(variants):
        suffix = '' if variants == 1 else '-ab'[n + 1]
        request_id = str(uuid.uuid5(uuid.NAMESPACE_OID, f"{body['request_id']}-{suffix}")) if suffix else body['request_id']   # defect 27: the jobs' request_id is a uuid; one per candidate, the same on a retry
        made.append(_queue_image(conn, store, session, run, outputs, element, {**body, 'region': region}, parents, answer, op, body['name'] + ('-' + suffix if suffix else ''), request_id, pending_end))
        if lines:
            session['references'][made[-1]['reference_id']]['server_checklist'] = lines
        if found:   # design/91 N9: the check measures its light against the footage beside the shot's gap
            session['references'][made[-1]['reference_id']].update(shot_id=named['id'], gap_id=found[1]['gap_id'])
    save_session(store, run, session)
    return {**made[0], **({'reference_ids': [m['reference_id'] for m in made], 'job_ids': [m['job_id'] for m in made]} if variants == 2 else {}), **({'warnings': warns} if warns else {})}


LABEL_MIN_PCT, TITLE_MIN_PCT = 4, 6   # design/91 N13, SK 23 Oct: of the frame height (43 and 65 px at 1080p)
LABEL_SIZE = {'check': 'label size', 'pass_when': f'every label is at least {LABEL_MIN_PCT} % of the frame height and a title at least {TITLE_MIN_PCT} %, readable on a phone',
              'weight': 'should'}
LABEL_SIGN = re.compile(r'[↑↓←→⇧⇩▲▼⬆⬇]|^\s*[+\-−]\s*\d')
LABEL_BARE = re.compile(r'^\s*[\d.,]+\s*$')
WORLD_LINE = {'check': "the film's world", 'pass_when': 'the subject is in a real place of the film (its ground, light and surroundings), not on a plain studio or neutral '
                                                       'background, and not an object alone out of its place of use', 'weight': 'should'}   # design/91 N9, N11
STYLE = '_STYLE'   # design/89 C2: the film's style sheet, one picture every graphic is made from


def spec_digest(spec):
    return digest(spec)


def _fact_line(f):
    return {'check': 'fact: ' + f['id'], 'pass_when': f"it looks as the fact says: {f['looks']}" + (f"; done as: {f['how']}" if f.get('how') else ''), 'weight': 'must'}


def _step_filter(session, parents, named):
    """design/96 J1: for a state of a graphic sequence, (keep(text), final): a claim, word or depiction belongs to the first state whose `what_appears`
    or `words` names it, else to the last; a state keeps the ones before it. The step is 1 plus the parents made for the shot. A still diagram is
    one state, with everything."""
    states = named.get('states') or [] if route_of(named) == 'graphic_sequence' else []
    if not states:
        return (lambda text: True), True
    step, row = 1, next((p for p in parents if p and p.get('kind') in ('keyframe', 'state') and made_for(session, p) == named['id']), None)
    while row and step < len(states):
        step += 1
        ups = [session['references'].get(p.get('id')) or {} for p in (row.get('generation') or {}).get('parents') or []]
        row = next((p for p in ups if p.get('kind') in ('keyframe', 'state') and made_for(session, p) == named['id']), None)
    shown = [f"{st.get('what_appears') or ''} {st.get('words') or ''}".lower() for st in states]
    first = lambda text: next((i for i, t in enumerate(shown, 1) if str(text).lower() in t), len(states))
    return (lambda text: first(text) <= step), step >= len(states)


def _graphic_lines(session, plan, body, parents, answer, named=None):
    """design/89 C1, C4, D3-D5: every picture is warned without its answer form; a picture of a graphic carries its claims, the spec's relationships,
    its sizes and its label as lines, and is warned without its style sheet or an approved spec (refused from the next release).
    design/91: every picture of an element carries the element's facts (N6); a picture made for a named shot carries that shot's claims (never shown as
    their opposite), its descriptive words (N8), what the step before left (N14) and its facts; a graphic carries what it depicts (N10)."""
    if body.get('fix_of'):   # a fix round carries its picture's form when it had one
        return [], []
    warns = [] if answer is not None else ['no answer form with this picture: write it with the library\'s form (--answer), so its checklist is checked' + NEXT_RELEASE]
    facts = {f['id']: f for f in plan.get('visual_facts') or [] if f.get('status') != 'unknown'}   # an unknown fact is never a line: it is never drawn
    lines = [_fact_line(f) for f in facts.values() if f.get('about') == body['element_id']]
    graphic = named is not None and named['visual_type'] in GRAPHIC_TYPES
    kind = (named or {}).get('graphic_kind') or 'diagram'
    wordy = graphic and kind in ('title', 'text')   # design/96 J2: a card of words is checked for its words, their size and readability only
    keep, final = _step_filter(session, parents, named) if graphic else ((lambda text: True), True)   # design/96 J1: each step for what it shows
    if named is not None:
        if not wordy:
            lines += [{'check': 'claim: ' + c, 'pass_when': (f'the picture shows that {c}, plainly, without the narration' if graphic else
                                                             f'the picture never shows the opposite of: {c}'), 'weight': 'must'} for c in named.get('claims') or [] if keep(c)]
            lines += [{'check': 'word: ' + d, 'pass_when': f'what the narration calls {d} looks {d}, never the opposite', 'weight': 'must'} for d in named.get('descriptors') or [] if keep(d)]
        lines += [{'check': 'carried over: ' + c, 'pass_when': f'{c} is visible, as the step before left it', 'weight': 'must'} for c in named.get('carries_over') or []]
        lines += [_fact_line(facts[f]) for f in named.get('fact_ids') or [] if f in facts]
    shots = [named] if graphic else []   # design/94 R1.2: its own shot's lines only, never every shot of the element
    if shots or any(sh['visual_type'] in GRAPHIC_TYPES for _, sh in _shots_with(plan, session, body['element_id'])):   # design/91 N13: labels say what they mean, readable on a phone
        labels = [e['text'] for e in library.exact_entries(answer)]   # design/111 F13: entries with their place and size
        said = ((lambda s: f'the words read exactly "{s}", spelled as written, at least {TITLE_MIN_PCT} % of the frame height, readable on a phone') if wordy else
                (lambda s: f'the label reads exactly "{s}", is at least {LABEL_MIN_PCT} % of the frame height, and its leader line ends on the part it names') if kind == 'diagram' else
                (lambda s: f'the label reads exactly "{s}", spelled as written, at least {LABEL_MIN_PCT} % of the frame height'))   # J2: leader lines only on a diagram
        label_lines = [{'check': 'label: ' + s, 'pass_when': said(s), 'weight': 'must'} for s in labels] + [LABEL_SIZE]   # after the claims and the drawing's own lines
        warns += [f"the label '{s}' uses a sign in place of words: write it as a phrase ('25 % fewer bricks', not '↓ 25 %')" for s in labels if LABEL_SIGN.search(s)]
        warns += [f"the label '{s}' is a number without its unit: give the unit, and its source in the drawing spec" for s in labels if LABEL_BARE.match(s)]
    else:
        label_lines = []
    if not shots:
        return _dedupe(lines + label_lines), warns
    if wordy:
        if named.get('drawing_spec'):
            warns.append(f"{named['id']} is a {kind} card: its drawing spec is not checked")
        shots = []   # its words, their size and readability only
    lines += [{'check': 'claim: ' + c, 'pass_when': f'the picture shows that {c}, plainly, without the narration', 'weight': 'must'} for sh in shots for c in sh.get('claims') or [] if keep(c)]
    lines += [{'check': 'depicts: ' + sh['depicts'], 'pass_when': f"the drawing shows {sh['depicts']}, in the subject's own form (an alternative only as a labelled contrast)",
               'weight': 'must'} for sh in shots if str(sh.get('depicts') or '').strip() and keep(sh['depicts'])]   # design/91 N10
    shots = shots if final else []   # J1: the spec's relationships, sizes and label are the finished drawing's
    lines += [{'check': 'relationship: ' + r, 'pass_when': f'in the drawing, {r}', 'weight': 'must'} for sh in shots for r in (sh.get('drawing_spec') or {}).get('relationships') or []]
    for sh in shots:   # D3, D5: an unknown size shows no figure; the label is on the drawing; a known size reads as the spec says
        spec = sh.get('drawing_spec') or {}
        for r in spec_table(spec):
            name = f"{r['part']} {r['measure']}"
            lines.append({'check': 'unknown: ' + name, 'pass_when': f'no figure is shown for the {name}', 'weight': 'must'} if r['status'] == 'unknown' else
                         {'check': f"size: {name} {r['size']}", 'pass_when': f"any figure shown for the {name} reads {r['size']}, and its proportion to the other parts looks right", 'weight': 'should'})
        if spec.get('label'):
            lines.append({'check': 'label: ' + spec['label'], 'pass_when': f"the drawing carries the words \"{spec['label']}\"", 'weight': 'must'})
    if body['kind'] != 'state' and not any(p.get('kind') == 'style' and p.get('status') == 'approved' for p in parents):   # a state is made from the previous state
        warns.append(f'no approved style sheet among the parents: make it once (`vw visuals image --element {STYLE} --kind style`), approve it, and name it in --parents' + NEXT_RELEASE)
    for sh in shots:
        spec = sh.get('drawing_spec')
        if spec and (session.get('spec_approvals') or {}).get(sh['id'], {}).get('digest') != spec_digest(spec):
            warns.append(f"the drawing spec of {sh['id']} is not approved, or changed since: approve it as a table (`vw visuals spec --shot {sh['id']} --quote`, or on the page)" + NEXT_RELEASE)
    return _dedupe(lines + label_lines), warns


def _dedupe(lines):
    seen = set()
    return [l for l in lines if not (l['check'] in seen or seen.add(l['check']))]


def approve_spec(store, user, run, outputs, shot_id, quote):
    """design/89 D4: the operator approves a drawing spec once, as a table of parts, sizes and sources; a change to the spec needs a new approval.
    design/106 D4: no words needed; the operator never types sizes, and a correction goes to the assistant instead."""
    session = session_of(store, run, outputs)
    if shot_id.startswith('element:'):   # design/111 F10: a material spec, approved once on the References step
        plan = guarded(lambda: current_plan(store, session))
        element = next((e for e in plan['elements'] if e['id'] == shot_id[len('element:'):]), None)
        need(element and element.get('material_spec'), f'{shot_id[len("element:"):]} has no material spec.')
        spec = element['material_spec']
        need(not correction_pending(session, shot_id, spec), f'The correction of {element["id"]}\'s material spec waits for the assistant to revise it; approve the revised one.')
        if not (session.get('not_this') or {}).get(element['id']):   # design/111 F12: the list is the spec's second half, built with it
            try:
                not_this(store, user, run, outputs, element['id'])
                session = session_of(store, run, outputs)
            except (Problem, ValueError):   # the model call failed: the approval stands; `vw visuals not-this --element` builds the list when the model answers
                pass
        session.setdefault('spec_approvals', {})[shot_id] = {'digest': spec_digest(spec), 'quote': said(quote, 'Approved', user), 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
        (session.get('spec_corrections') or {}).pop(shot_id, None)
        save_session(store, run, session)
        return {'element_id': element['id'], 'table': spec_table(spec), 'sentence': material_sentence(element), 'next': f"Material spec of {element['id']} approved: every picture that shows it carries it word for word."}
    _, _, _, shot = guarded(lambda: locate(store, session, shot_id))
    spec = shot.get('drawing_spec')
    need(spec, f'Shot {shot_id} has no drawing spec.')
    need(not correction_pending(session, shot_id, spec), f'The correction of {shot_id} waits for the assistant to revise the spec; approve the revised one.')   # review 27 Oct
    session.setdefault('spec_approvals', {})[shot_id] = {'digest': spec_digest(spec), 'quote': said(quote, 'Approved', user), 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    (session.get('spec_corrections') or {}).pop(shot_id, None)
    save_session(store, run, session)
    return {'shot_id': shot_id, 'table': spec_table(spec), 'relationships': spec.get('relationships') or [], 'label': spec.get('label') or '',
            'depicts': shot.get('depicts') or ''}   # design/91 N10: the spec repeats what the drawing depicts


def spec_table(spec):
    """design/106 D3, D5: every size with its source and status, an unknown one with its risk in one line, then the proportions."""
    rows = []
    for d in spec.get('dimensions') or []:
        row = {'part': d['part'], 'measure': d['measure'], 'size': 'unknown' if d.get('value') is None else f"{d['value']:g} {d.get('unit') or ''}".strip(),
               'source': d.get('source') or '', 'status': d['status']}
        if d['status'] == 'unknown':
            row['risk'] = f"{d['part']} {d['measure']} not found" + (f" ({d['tried']})" if d.get('tried') else '') + '; drawn by eye'
        rows.append(row)
    return rows + [{'part': 'proportion', 'measure': '', 'size': p, 'source': '', 'status': 'ratio'} for p in spec.get('proportions') or []]


def note_reference(store, user, run, outputs, ref_id, note):
    """design/106 N4: a saved picture's note stays editable until its element's sheet is made; the sheet prompt reads the latest note."""
    session = session_of(store, run, outputs)
    row = session['references'].get(ref_id)
    need(row and row.get('kind') in ('web', 'frame', 'supplied', 'isolated') and row.get('status') != 'rejected', f'{ref_id} is not a saved picture of an element.')
    sheet = next((r for r in session['references'].values() if r.get('kind') == 'sheet' and r.get('element_id') == row.get('element_id') and r.get('status') != 'rejected'), None)
    need(not sheet, f"{row.get('element_id')}'s sheet is already made ({(sheet or {}).get('id', '')[:8]}): reject the sheet to change the notes it was made from.")
    row.setdefault('source', {})['note'] = str(note or '').strip()[:500]
    save_session(store, run, session)
    return {'reference_id': ref_id, 'note': row['source']['note'], 'next': f"Note saved: {row.get('element_id')}'s sheet is made with it."}


def correct_spec(store, user, run, outputs, shot_id, words):
    """design/106 D4: the operator corrects a value; the assistant revises the spec, and the next approval clears the correction."""
    words = str(words or '').strip()
    need(words, 'Say what to correct in the spec (a value, a part, a proportion).')
    session = session_of(store, run, outputs)
    if shot_id.startswith('element:'):   # design/111 F10
        plan = guarded(lambda: current_plan(store, session))
        element = next((e for e in plan['elements'] if e['id'] == shot_id[len('element:'):]), None)
        need(element and element.get('material_spec'), f'{shot_id[len("element:"):]} has no material spec.')
        spec = element['material_spec']
    else:
        _, _, _, shot = guarded(lambda: locate(store, session, shot_id))
        need(shot.get('drawing_spec'), f'Shot {shot_id} has no drawing spec.')
        spec = shot['drawing_spec']
    session.setdefault('spec_corrections', {})[shot_id] = {'words': words, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'digest': spec_digest(spec)}
    save_session(store, run, session)
    return {'shot_id': shot_id, 'correction': words, 'next': f'Correction sent: the assistant revises the spec of {shot_id}, then you approve it.'}


def approve_specs(store, user, run, outputs, quote=''):
    """design/106 D5: one approval for every drawing spec of the run still to approve, the same function for the page and chat."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    quote = said(quote, 'Approved', user)
    approved, waiting_ = [], []
    for _, sh in _accepted_shots(plan, session):
        spec = sh.get('drawing_spec')
        if spec and correction_pending(session, sh['id'], spec):   # review 27 Oct: the assistant's turn, not approved over
            waiting_.append(sh['id'])
        elif spec and (session.get('spec_approvals') or {}).get(sh['id'], {}).get('digest') != spec_digest(spec):
            session.setdefault('spec_approvals', {})[sh['id']] = {'digest': spec_digest(spec), 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
            (session.get('spec_corrections') or {}).pop(sh['id'], None)
            approved.append({'shot_id': sh['id'], 'table': spec_table(spec)})
    for e in plan.get('elements') or []:   # design/111 F10: the material specs too
        spec = e.get('material_spec')
        k = material_key(e['id']) if spec else None
        if spec and correction_pending(session, k, spec):
            waiting_.append(k)
        elif spec and not material_approved(session, e):
            session.setdefault('spec_approvals', {})[k] = {'digest': spec_digest(spec), 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
            (session.get('spec_corrections') or {}).pop(k, None)
            approved.append({'shot_id': k, 'element_id': e['id'], 'table': spec_table(spec)})
    save_session(store, run, session)
    return {'approved': approved, 'waiting': waiting_, 'next': (f"{len(approved)} drawing spec{'s' if len(approved) != 1 else ''} approved." if approved else 'No drawing spec was waiting.')
            + (f" {', '.join(waiting_)}: a correction waits for the assistant; approve the revised spec." if waiting_ else '')}


def correction_pending(session, shot_id, spec):
    """design/106 D4: a correction stays until the spec it was made on changes (an old record without a digest counts as pending)."""
    c = (session.get('spec_corrections') or {}).get(shot_id)
    return bool(c) and c.get('digest', spec_digest(spec)) == spec_digest(spec)


def _gemini_transport():
    from .analysis_jobs import transport_factory
    return transport_factory


MEASURE_SCHEMA = {'type': 'object', 'properties': {'measurements': {'type': 'array', 'items': {'type': 'object', 'properties': {
    'part': {'type': 'string'}, 'measure': {'type': 'string'}, 'value': {'type': 'number'}, 'unit': {'type': 'string'}, 'frame': {'type': 'integer'}, 'how': {'type': 'string'}},
    'required': ['part', 'measure', 'value', 'unit', 'how']}}, 'limits': {'type': 'string'}}, 'required': ['measurements', 'limits']}


def measure(store, user, run, outputs, ref_ids, question):
    """design/89 D2: Gemini reads sizes off approved footage frames against something of known size; each number keeps its clip and time."""
    need((question or '').strip(), 'Say what to measure.')
    session = session_of(store, run, outputs)
    frames = [session['references'].get(r) for r in ref_ids or []]
    need(frames and all(f and f.get('kind') == 'frame' and f['status'] == 'approved' for f in frames), 'Measure reads approved footage frames only: name frames taken from the clips.')
    where = [f"clip {(f.get('source') or {}).get('media_id')} at {(f.get('source') or {}).get('requested_s')} s" for f in frames]
    parts = []
    for n, (f, w) in enumerate(zip(frames, where), 1):
        parts += [{'text': f'Frame {n}, {w}.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(f['key'])).decode()}}]
    parts.append({'text': 'Measure from these frames: ' + question.strip()[:1000] + '\nScale each size against something of known size in the same frame (a brick, a door, a level, a person) '
                          'and say which in how. Give the frame number each size is read from. Measure only what is visible; say in limits what cannot be read.'})
    key_ = settings().GEMINI_API_KEY.get_secret_value().strip()
    need(key_, 'No Gemini key on the server.')
    try:
        received = _gemini_transport()(key_, MEASURE_MODEL, terminal_deadline_seconds=180, initial_soft_wait_seconds=30, on_update=lambda e: None, capture_answer_deltas=False).generate(
            {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': MEASURE_SCHEMA, 'maxOutputTokens': 4096}})
        body = received.get('body') if isinstance(received.get('body'), dict) else json.loads(received.get('raw') or '{}')
    except Exception as exc:
        raise Problem(502, 'MEASURE_FAILED', f'The measure call failed: {exc.__class__.__name__}: {str(exc)[:200]}')
    out = []
    for m in body.get('measurements') or []:
        n = m.get('frame') if isinstance(m.get('frame'), int) and 1 <= m['frame'] <= len(frames) else 1
        out.append({'part': str(m.get('part') or ''), 'measure': str(m.get('measure') or ''), 'value': m.get('value'), 'unit': str(m.get('unit') or ''), 'status': 'measured',
                    'source': where[n - 1], 'how': str(m.get('how') or '')[:300]})
    mid = uuid.uuid4().hex[:12]
    session.setdefault('measurements', {})[mid] = {'question': question, 'frames': list(ref_ids), 'measurements': out, 'limits': str(body.get('limits') or '')[:500],
                                                   'model': MEASURE_MODEL, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    return {'measure_id': mid, 'measurements': out, 'limits': session['measurements'][mid]['limits']}


MEASURE_MODEL = 'gemini-3.8-flash'


def _queue_image(conn, store, session, run, outputs, element, body, parents, answer, op, name, request_id, pending_end):
    ref_id = digest({'run': str(run['id']), 'request': request_id})[:32]
    frame = default_aspect(next((o['summary'] for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None), {})   # design/71 P3: the size follows the brief's frame
    first = parents[0] if parents and parents[0].get('kind') in ('keyframe', 'frame') else None   # an edit of a keyframe or a frame keeps that picture's size when GPT Image accepts it
    size = body.get('size') or (library.edit_size(first.get('width'), first.get('height'), frame) if first else library.default_size(frame))
    request = {'kind': 'image', 'op': op, 'model': body.get('model') or IMAGE_MODELS[op], 'prompt': body['prompt'], 'size': size,
               'quality': body.get('quality') or 'high', 'parents': [{'id': p['id'], 'key': p['key'], 'sha256': p['sha256']} for p in parents],
               'reference': {'id': ref_id, 'element_id': body['element_id'], 'element_kind': element['kind'], 'name': name, 'kind': body['kind'], 'subject': body['subject'],
                             **({'fix_of': body['fix_of']} if body.get('fix_of') else {}), **({'role': body['role']} if body.get('role') else {}),
                             **({'golden_candidate': True} if body.get('golden') else {})},   # design/96 X3; design/106 T1; design/111 F11
               **({'region': body['region']} if body.get('region') else {})}
    row = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,'openai',%s,%s) returning id",
                       (run['id'], ref_id, Jsonb(request), request_id)).fetchone()
    session['references'][ref_id] = {**request['reference'], 'id': ref_id, 'status': 'generating', 'job_id': str(row['id']), 'generation': {k: request[k] for k in ('op', 'model', 'prompt', 'size', 'quality', 'parents') + (('region',) if request.get('region') else ())},
                                     **({'answer': answer} if answer is not None else {}), **({'pending_end': pending_end} if pending_end else {}),
                                     **({'fix_of': body['fix_of']} if body.get('fix_of') else {})}
    return {'reference_id': ref_id, 'job_id': str(row['id']), 'model': request['model'], 'op': op}


CAMERA_MOVE = re.compile(r"(\bcamera\s+(?:(?:\w+ly|has|had|is|was|then|now|also|begins? to|starts? to)\s+)*(push|drift|dolly|zoom|pan|tilt|track|mov)\w*)"   # review 27 Oct: the camera is the one moving, not something near the word
                         r"|\b(push[- ]in|pull[- ]out|dolly|zoom\w*|tracking shot|pan(ning)? (left|right)|tilt(ing)? (up|down))\b", re.I)


def camera_move(text):
    """design/106 T6: the first camera move the text asks for; a negated one ('no camera move', 'did not move', 'stays still', 'locked off') is not a move."""
    text = text or ''
    for m in CAMERA_MOVE.finditer(text):
        before = text[max(0, m.start() - 20):m.start()]
        if re.search(r"(\b(no|not|never|without)\b|n't)[^.;,]{0,12}$", before, re.I):
            continue
        return m.group(0).strip()
    return None


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


def _keyframe_gates(session, plan, body, parents, named=None):
    """design/77: L35 a start keyframe for a video shot's element waits until a shot's packet was read (bind, then packet); L38 an end keyframe
    never moves the camera; L41 a shot that shows a client's own material (an exact object element with approved footage frames) sends one of
    those frames as a parent."""
    pairs = _shots_with(plan, session, body['element_id'])
    end = body['role'] == 'end' if body.get('role') else any(p['kind'] == 'keyframe' for p in parents)   # design/106 T1
    video = [(gap, sh) for gap, sh in pairs if sh['visual_type'] == 'video' and (named is None or sh['id'] == named['id'])]   # defect 24: a named image shot is a still, no bind or packet
    if video and not end:   # L35
        read = [sh['id'] for gap, sh in video if (session['bindings'].get(sh['id']) or {}).get('packet_read_at') and session['bindings'][sh['id']].get('gap_digest') == gap_digest(plan, gap)]
        first = video[0][1]['id']
        need(read, f"Bind the shot and read its packet before composing its start image (`vw visuals bind --shot {first} …`, then `vw visuals packet --shot {first}`): "
                   "the packet carries the pair instructions and the library's job form.")
    if end:   # L38
        m = camera_move(body['prompt'])
        if m:
            need(False, f"The end image moves the camera ({m!r}): the camera does not move between the start and the end; show the action's visible result instead.")
    elements = {e['id']: e for e in plan['elements']}
    parent_frames = {p['element_id'] for p in parents if p.get('kind') == 'frame'}
    for gap, sh in pairs:   # L41
        if named is not None and sh['id'] != named['id']:   # defect 28: the picture's own shot, not every shot its element appears in
            continue
        for eid in sh.get('element_ids') or []:
            e = elements.get(eid)
            if not e or eid == body['element_id'] or e['kind'] != 'object' or e['identity'] != 'exact' or golden_of(session, eid):   # design/111 F11: the golden picture carries the frame
                continue
            frames = [r for r in session['references'].values() if r.get('element_id') == eid and r.get('kind') == 'frame' and r.get('status') == 'approved']
            need(not frames or eid in parent_frames, f"{eid} is the client's own: send one of its approved footage frames as a parent, named by number as the material reference "
                                                     f"({', '.join(r['id'][:8] for r in frames)}).")


def approve_reference(store, user, run, outputs, ref_id, sha256, quote, conn=None):
    session = session_of(store, run, outputs)
    row = session['references'].get(ref_id)
    need(row and row['status'] in ('candidate', 'approved'), 'Reference is not a candidate.')
    _no_question(session, ref_id, made_for(session, row))   # design/110 rule 0
    if row['sha256'] != sha256:
        raise Problem(409, 'REFERENCE_MISMATCH', 'Approve the exact stored image hash after viewing it.')
    if row['status'] == 'candidate':
        try:
            _not_yet_gate(store, session, row, at_approval=True)   # design/110 F3, rule 0 fork 5
        except ValueError:
            save_session(store, run, session)   # the question, and the line asked once, are kept
            raise
    if row.get('kind') == 'keyframe' and row['status'] == 'candidate' and made_for(session, row) and _shot_is_video(store, session, made_for(session, row)):   # rule 0, fork 3: two pictures approved for one slot (a start or an end) : the operator keeps one; a still's second picture replaces (design/94)
        sid, word = made_for(session, row), _picture_word(store, session, row)
        others = [r['id'] for r in session['references'].values() if r['id'] != ref_id and r.get('kind') == 'keyframe' and r.get('status') == 'approved' and made_for(session, r) == sid
                  and _picture_word(store, session, r) == word]
        if others:
            _open(session, sid, f"Two {word}s for {sid} would be approved: {', '.join(others)} (approved) and {ref_id}. Keep which?", others + [ref_id], 'server', fork='slot')
            save_session(store, run, session)
            need(False, f"Two {word}s for {sid}: {', '.join(others)} is approved already. Answer which to keep on the shot's card (or `vw visuals answer --item {sid} --answer <id>`); the other is rejected, then approve again.")
    if row.get('golden_candidate'):   # design/111 F11: a flawed picture cannot be golden
        flaw = 'approved anyway after the not-yet-done check failed' if row.get('not_yet_ok') else ('rejected before, with words' if row.get('rejection') else '')
        need(not flaw, f"{ref_id} cannot be the golden picture: it was approved with a stated flaw ({flaw}); make a new golden picture of {row.get('element_id')}.")
    quote = said(quote, 'Approved', user)   # design/99 C2
    row.update(status='approved', approval={'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'sha256': sha256, 'quote': quote})
    if row.get('golden_candidate'):
        session.setdefault('golden', {})[row['element_id']] = ref_id
    if row.get('kind') == 'sheet':   # a person's identity sheet is its golden picture
        try:
            kinds_ = {e['id']: e['kind'] for e in current_plan(store, session)['elements']} if session.get('current') else {}
        except (ValueError, Problem):
            kinds_ = {}
        if kinds_.get(row.get('element_id')) == 'person':
            session.setdefault('golden', {})[row['element_id']] = ref_id
    placed = None
    sid = made_for(session, row)
    if sid and row.get('kind') in ('keyframe', 'state'):   # design/94 A1: approving a still shot's picture places it, in the same save; a refusal approves nothing
        try:
            shot = locate(store, session, sid)[3]
        except ValueError:   # its shot left the plan or its gap waits for acceptance: approved only
            shot = None
        if shot and route_of(shot) == 'still':
            placed = _place_still(store, user, run, outputs, session, sid, ref_id, quote)
    row['dhash'] = _fingerprints(store, row['key'])   # design/89 H6, finding 9: kept once, never read again for the look-alike check
    if sid and row.get('kind') in ('keyframe', 'isolated'):   # design/111 F17: background figures against the approved pictures of the scene
        try:
            pl_, _, sc_, sh_ = locate(store, session, sid)
        except ValueError:
            sh_ = None
        if sh_ and _has_figures(pl_, sh_):
            fc = figure_repeat(store, session, row, sc_)
            if fc:
                row['figure_check'] = fc
    if row.get('kind') == 'sheet':   # design/110: the new sheet answers the changed sources
        for r in session['references'].values():
            if r.get('kind') == 'sheet' and r.get('element_id') == row.get('element_id'):
                r.pop('sources_changed', None)
    _feedback_image(session, run, user, row, 'pass', quote, '')
    save_session(store, run, session)
    if placed:   # design/97 A4: what happens next, with the film time
        nxt = f"Approved: in the film at {film_time(session, shot)} ({sid})" + (f"; it replaces {placed['replaced']}, which stays approved" if placed.get('replaced') else '') + '.'
        return {**row, 'placed': sid, 'next': nxt, **({k: placed[k] for k in ('replaced', 'warnings') if k in placed})}
    pe = row.get('pending_end')
    if pe and conn is not None and not row.get('end_queued'):   # design/86 K1: the end image follows the approved start without a chat turn
        try:
            out = generate_image(conn, store, user, run, outputs, {'request_id': str(uuid.uuid4()), 'element_id': row['element_id'], 'name': re.sub(r'\bstart\b', 'end', row['name']) if 'start' in row['name'] else 'end-' + row['name'],
                                                                   'kind': 'keyframe', 'subject': row['subject'], 'prompt': pe['prompt'], 'parents': [ref_id], 'answer': pe.get('answer'), 'role': 'end',
                                                                   **({'region': pe['region']} if pe.get('region') else {})})   # design/111 F11: the end's region, written with the start
        except (ValueError, Problem) as exc:   # defect 28: the start stays approved; the reason goes back, and approving it again tries the end again
            why = exc.message if isinstance(exc, Problem) else str(exc)
            return {**row, 'next': f"Approved; the end image was not made: {why} Make the end from this start (it is Image 1), or approve this start again to retry."}
        session = session_of(store, run, outputs)
        session['references'][ref_id]['end_queued'] = out['reference_id']
        save_session(store, run, session)
        return {**session['references'][ref_id], 'end_reference_id': out['reference_id'], 'end_job_id': out['job_id'],   # design/106 T2
                'next': f"Approved: end image queued (job {out['job_id']}); it appears here in about a minute."}
    return {**row, 'next': _approved_next(store, session, row)}


def request_fix(conn, store, user, run, outputs, ref_id):
    """design/96 X1, X4: one fix round of a candidate, only when the operator or the assistant asks: an edit with the one change its first failed must
    line asks for, at the image price, inside the cap. Never for a fix, never twice, never for a line the check could not decide."""
    session = session_of(store, run, outputs)
    ref = session['references'].get(ref_id)
    need(ref, f'{ref_id} is not a picture of this run.')
    _no_question(session, ref_id, made_for(session, ref))   # design/110 rule 0
    need(not ref.get('fix_of'), 'a fix is not fixed again: reject it and make a new picture.')
    need(not ref.get('fix_queued'), f"a fix of this picture is already made: {ref.get('fix_queued')}.")
    need(ref.get('status') == 'candidate', f"only a candidate is fixed; {ref_id} is {ref.get('status')}.")
    need(ref.get('check'), 'the check is still running; try again once its lines show.')
    failed = [l for l in image_check.expand(ref['check'], ref)['must_failed'] if l.get('pass') is False]
    need(failed, 'nothing to fix: no must line failed.')
    out = generate_image(conn, store, user, run, outputs, image_check.fix_body(ref, failed[0]))
    session = session_of(store, run, outputs)
    session['references'][ref_id]['fix_queued'] = out['reference_id']
    session['references'][out['reference_id']]['fix_for'] = failed[0]['check']
    save_session(store, run, session)
    return {'reference_id': out['reference_id'], 'of': ref_id, 'for': failed[0]['check'], 'cost_inr': prices()['image_inr'], 'next': 'Fix requested: it appears here in about a minute.'}


def _picture_word(store, session, row):
    """What the picture is, in the operator's words."""
    kind = row.get('kind')
    if kind == 'keyframe':
        if row.get('role') == 'end' or (not row.get('role') and any((session['references'].get(p.get('id')) or {}).get('kind') == 'keyframe' for p in (row.get('generation') or {}).get('parents') or [])):
            return 'end image'
        return 'start image' if made_for(session, row) and _shot_is_video(store, session, made_for(session, row)) else 'picture'
    return {'state': 'state', 'sheet': 'reference sheet', 'style': 'style sheet'}.get(kind, 'reference picture')


def _shot_is_video(store, session, shot_id):
    try:
        return locate(store, session, shot_id)[3]['visual_type'] == 'video'
    except Exception:   # a shot no longer in the plan
        return False


def _approved_next(store, session, row):
    """design/97 A4: what follows an approval that places nothing."""
    word = _picture_word(store, session, row)
    return {'end image': f"Approved: the take for {made_for(session, row)} is the next step.", 'start image': 'Approved: the end image is made from it next.',
            'state': 'Approved: the sequence is approved as a whole once every state is in.', 'style sheet': 'Approved: every graphic is made from it.',
            'reference sheet': f"Approved: the shots of {row.get('element_id')} are made from it."}.get(word, 'Approved.')


def reject_reference(store, user, run, outputs, ref_id, notes, quote):
    """design/74 L7: a picture rejected with the operator's words; it is never approved, bound, held or named as a parent afterwards."""
    session = session_of(store, run, outputs)
    row = session['references'].get(ref_id)
    words = str(quote or '').strip()
    reason = str(notes or '').strip() or words
    if row and row.get('status') == 'rejected' and reason and row.get('rejection'):   # design/99 C3: the reason given after the click joins the same rejection
        row['rejection']['notes'] = reason
        _feedback_image(session, run, user, row, 'reject', row['rejection']['quote'], reason)
        try:
            _not_this_add(store, session, current_plan(store, session) if session.get('current') else None, row.get('element_id'), reason)   # design/111 F12
        except (ValueError, Problem):
            pass
        save_session(store, run, session)
        return {**row, 'next': f'Rejected: the assistant makes a new {_picture_word(store, session, row)} with your note.'}
    need(row and row['status'] in ('candidate', 'approved'), f"Reference {ref_id} is not a candidate or approved picture (it is {(row or {}).get('status') or 'unknown'}); only those can be rejected.")
    quote = said(words, 'Rejected', user)   # design/99 C3: the reason is optional
    row.update(status='rejected', rejection={'notes': reason, 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()})
    _feedback_image(session, run, user, row, 'reject', quote, row['rejection']['notes'])
    try:   # design/111 F12: the rejection's words join the element's not-this list at once
        _not_this_add(store, session, current_plan(store, session) if session.get('current') else None, row.get('element_id'), reason)
    except (ValueError, Problem):
        pass
    save_session(store, run, session)
    return {**row, 'next': f'Rejected: the assistant makes a new {_picture_word(store, session, row)} with your note.'}   # design/97 A4


# ---------- design/74 L7: the feedback record, in the library's shape (record-template.videowizard.yaml) ----------

def _step_of_reference(session, row):
    kind = row.get('kind')
    if kind in ('isolated', 'sheet', 'style'):   # design/89 C2: the style sheet is a reference
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


def rounds_summary(records):
    """design/86 K9: per kind, how many were approved, how many rejected, and the rounds per approved picture; the next film shows whether the corrections work."""
    out = {}
    for r in records:
        k = out.setdefault(r.get('kind') or '?', {'approved': 0, 'rejected': 0})
        if r.get('verdict') == 'pass':
            k['approved'] += 1
        elif r.get('verdict') in ('reject', 'fix'):
            k['rejected'] += 1
    for k in out.values():
        k['rounds_per_approved'] = round((k['approved'] + k['rejected']) / k['approved'], 2) if k['approved'] else None
    return out


def feedback(store, run, outputs):
    session = session_of(store, run, outputs)
    records = session.get('feedback') or []
    summary = rounds_summary(records)
    head = ''.join(f"# {kind}: approved {v['approved']}, rejected {v['rejected']}, rounds per approved {v['rounds_per_approved']}\n" for kind, v in sorted(summary.items()))
    return {'records': len(records), 'summary': summary, 'yaml': head + feedback_yaml(records)}


def bind(store, user, run, outputs, shot_id, references, selectors, quote=''):
    """design/45 10.4: the approved references are the operator's yes; a quote is kept when given."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    _no_question(session, shot_id)   # design/110 rule 0
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


def place_words(marks, pos):
    """design/110 F2: '<amount> <unit> <relation> <landmark>' (the amount and unit when the plan has them)."""
    pos = pos or {}
    words = f"{pos.get('relation', '')} {marks.get(pos.get('landmark_id'), pos.get('landmark_id', ''))}".strip()
    if pos.get('amount') and pos.get('unit'):   # live check 27 Oct: '<relation> <landmark>, <amount> <unit> from it'; nothing for 0
        words += f", {pos['amount']:g} {pos['unit']} from it"
    return words


def moved_words(start, end):
    """design/110 F2: how far the subject moved from its place in Image 1, when both places are measured against the same landmark in the same unit."""
    a, b = start or {}, end or {}
    if a.get('amount') is None or b.get('amount') is None or a.get('landmark_id') != b.get('landmark_id') or a.get('unit') != b.get('unit') or a['amount'] == b['amount']:
        return ''
    return f"{abs(b['amount'] - a['amount']):g} {b['unit']} from where it stood in Image 1"


def end_targets(scene, shot):
    """design/86 K6: each subject's end state, from the plan's data, as one sentence; the writer cannot send a person the wrong way.
    design/110 F1: for an acting subject the cause, the path and the result come first; F2: the place is measured, and how far it moved."""
    marks = {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
    out = []
    for s in shot.get('subjects') or []:
        e = s.get('end') or {}
        pos = e.get('position') or {}
        held = ', '.join(e.get('holding') or []) or 'nothing'
        cause = ''
        if s.get('behaviour') == 'acts' and s.get('beats'):   # F1
            b = s['beats'][-1]
            here, there = place_words(marks, (s.get('start') or {}).get('position')), place_words(marks, pos)
            where = f'at {there}' if here == there else f'from {here} to {there}'   # live check 27 Oct: no "from X to X"
            cause = f"Because {s['element_id']} has {b.get('done') or b['action']}, {b['path']}, {where}, {b['result']} is now in frame. "
        moved = moved_words((s.get('start') or {}).get('position'), pos)
        out.append(cause + f"{s['element_id']} ends {place_words(marks, pos)}{', ' + moved if moved else ''}, facing {heading_words(marks, e.get('facing'))}, {e.get('pose', '')}, holding {held}; {e.get('progress', '')}.")
    return out


def heading_words(marks, facing):
    """A facing as words: the old free text, or (design/110 F6, later in this batch) a heading."""
    if isinstance(facing, dict):
        return f"front toward {marks.get(facing.get('landmark_id'), facing.get('landmark_id', ''))} at the {facing.get('edge', '')} edge, {_side(facing)} toward the camera"
    return str(facing or '')


def packet_context(session, plan, gap, shot):
    """design/86 K7: what the writer should know beyond the shot. None of it goes into the prompt sent to the model."""
    scenes = chosen_scenes(gap, session['choice_selections'].get(gap['gap_id']))
    shots = [sh for sc in scenes for sh in sc['shots']]
    words = ' '.join(str(sh.get('narration') or '').strip() for sh in shots if sh.get('narration')).strip()
    entry = next((e for e in ((session.get('treatment') or {}).get('gaps') or []) if e.get('gap_id') == gap['gap_id']), None)
    treatment = {k: entry.get(k) for k in ('picture', 'routes', 'intended', 'departure') if entry and entry.get(k)} if entry else None
    intended = [iv for iv in (session.get('intended_visuals') or []) if words and str(iv.get('narration_starts') or '')[:40] and str(iv.get('narration_starts'))[:40] in words]
    i = next((n for n, sh in enumerate(shots) if sh['id'] == shot['id']), None)
    prev_shot = shots[i - 1] if i else None
    next_shot = shots[i + 1] if i is not None and i + 1 < len(shots) else None
    neighbours = {'previous': {'shot_id': prev_shot['id'], 'ends': [{'element_id': s['element_id'], **(s.get('end') or {})} for s in prev_shot.get('subjects') or []]} if prev_shot else None,
                  'next': {'shot_id': next_shot['id'], 'starts': [{'element_id': s['element_id'], **(s.get('start') or {})} for s in next_shot.get('subjects') or []]} if next_shot else None}
    rejected = [{'reference_id': r['id'], 'element_id': r.get('element_id'), 'name': r.get('name'), 'kind': r.get('kind'), 'notes': (r.get('rejection') or {}).get('notes') or ''}
                for r in session['references'].values() if r.get('status') == 'rejected' and r.get('element_id') in (shot.get('element_ids') or [])]
    nb = (session.get('gap_neighbours') or {}).get(gap['gap_id']) or {}   # design/88 F3: the character of the clips on either side of the gap
    rows = (session.get('footage') or {}).get('per_clip') or {}
    footage_nb = {side: ({'clip_id': cid, **rows[cid]} if cid in rows else {'clip_id': cid}) if cid else None for side, cid in (('before', nb.get('before')), ('after', nb.get('after')))}
    timing = (session['source']['gaps'].get(gap['gap_id']) or {}).get('timing')   # design/89 A1: when each sentence is spoken, and the sentences on either side
    return {'gap_id': gap['gap_id'], 'gap_words': words, 'treatment_picture': treatment, 'intended_visuals': intended, 'neighbours': neighbours, 'earlier_rejections': rejected,
            'timing': ({k: timing.get(k) for k in ('sentences', 'before', 'after')} if timing else None),
            'footage_neighbours': footage_nb,
            'visual_facts': [f for f in plan.get('visual_facts') or [] if f['id'] in (shot.get('fact_ids') or []) or f.get('about') in (shot.get('element_ids') or [])]}   # design/91 N6


def exact_patterns(plan, shot, refs):
    """design/86 K8: an object of exact identity in the shot (a bond, a product, a uniform) and the bound picture that carries its pattern."""
    out = []
    for e in plan['elements']:
        if e['id'] in (shot.get('element_ids') or []) and e.get('kind') == 'object' and e.get('identity') == 'exact':
            carriers = [r['reference_id'] for r in refs if r['element_id'] == e['id'] and r.get('kind') in ('frame', 'isolated', 'supplied', 'web')]
            out.append({'element_id': e['id'], 'name': e.get('name'), 'requirements': e.get('requirements'), 'pattern_references': carriers,
                        'rule': 'name the geometry in nouns; the pattern is demanded on the checklist at medium and close shots only' + ('' if carriers else '; no close reference is bound yet: bind a footage frame or an isolated picture of it first')})
    return out


def packet(store, run, outputs, shot_id, session=None, card=None, rules=()):
    session = session or session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    if ensure_timing(store, run, session):   # design/89 A1, finding 3
        save_session(store, run, session)
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
                       'different pose or state from the start, never the same frozen pose. Carry each line of end_targets word for word: it is where every subject ends.')   # design/67 C; design/71 P1; design/77 L38; design/86 K6
    prompt = {'foundation': plan['foundation'], 'scene': {k: v for k, v in scene.items() if k != 'shots'}, 'shot': shot, 'references': refs,
              'end_targets': end_targets(scene, shot),   # design/86 K6: the end state of each subject as one sentence the end prompt carries word for word
              'context': packet_context(session, plan, gap, shot),   # design/86 K7: the gap's words, the treatment's picture, the intended visuals, the neighbours, earlier rejections
              'exact_patterns': exact_patterns(plan, shot, refs),   # design/86 K8: client patterns and the reference that carries each
              'sequence_rules': plan.get('sequence_rules', []), 'elements': [e for e in plan['elements'] if e['id'] in shot['element_ids']],
              'start_image_instruction': start_instruction, 'image_instruction': start_instruction,   # the old name answers for one release (design/67 A)
              'end_image_instruction': end_instruction,
              'video_instruction': 'Read the actual accepted starting image before writing movement. For EACH subject, follow the ordered beats, targets, paths, contacts, object responses and final progress. Keep non-acting subjects where they are. '
                                   'The take is one unbroken shot: write the motion so nothing enters the frame that the start or the end does not show. Write the continuity line (`--continuity`): what stays unchanged between the two frames, and for a person five traits from the sheet.',   # design/84 V3
              'checks': ['Treatment and narrated meaning', 'All visible subjects accounted for', 'World-relative layout and scale', 'Secondary action progression', 'Reference identity', 'Boundary continuity', 'Exact placement duration'],
              'footage_character': {k: (footage_view(session, outputs) or {}).get(k) for k in ('line', 'summary')},   # design/77 L42; design/88: measured, the correction winning
              'provider': {k: generator[k] for k in ('provider', 'model')}}
    prompt['context'] = {**prompt['context'], 'ambient': {'line': scene.get('ambient') or '', 'instruction': AMBIENT_START},
                         'guidance': shot_guidance(shot, prompt['context'].get('footage_neighbours') or {}),   # design/102: in the context, so no take goes stale
                         'bind_advice': bind_advice(plan, session, shot),   # design/104 D1, D2   # design/101 M5: in the context, so no take goes stale
                         'start_targets': {'lines': start_targets(scene, shot), 'instruction': NOT_YET_START}}   # design/110 F3: in the context, so no take goes stale
    identity = digest({**{k: v for k, v in prompt.items() if k not in ('context', 'footage_character')}, 'scene': note_free_scene(prompt['scene']),   # design/101, 103
                       'shot': note_free_scene({'shots': [prompt['shot']]})['shots'][0], 'elements': note_free_elements(prompt['elements'])})   # the composition only: the context, the footage and the library inform the writer and never make a prepared take stale (design/88)
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


def picture_lines(scene, shot, elements):
    """design/104 C5: should lines from the plan's fields, only where the plan gives them."""
    out = []
    light, air = (scene.get('light') or '').strip(), (scene.get('air') or '').strip()
    if light:
        out.append({'check': 'light', 'pass_when': f'the main light comes from where the scene\'s light says ({light}); shadows fall opposite', 'weight': 'should'})
    if air and air.lower() != 'clean':
        out.append({'check': 'air', 'pass_when': f'{air}: visible, lit by the light', 'weight': 'should'})
    if shot.get('size'):
        out.append({'check': 'shot size', 'pass_when': f"the picture is a {shot['size']}", 'weight': 'should'})
    sized = [e for e in elements if e['id'] in (shot.get('element_ids') or []) and e.get('size')]
    if sized:
        words = '; '.join(e['name'] + ': ' + ', '.join(f"{d['part']} {d['measure']} {d.get('value')} {d.get('unit') or ''}".strip() for d in e['size'] if d.get('value') is not None) for e in sized)
        out.append({'check': 'real size', 'pass_when': f'true sizes against the person and the place ({words})', 'weight': 'should'})
    return out


def bind_advice(plan, session, shot):
    """design/104 D1, D2: the footage frames the shot should bind, and why; advice for the assistant, never bound automatically."""
    out = []
    frames = lambda eid: sorted(r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('status') == 'approved' and r.get('element_id') == eid)
    for e in plan['elements']:
        if e['id'] not in (shot.get('element_ids') or []) or not frames(e['id']):
            continue
        if (e['kind'] == 'material' or (e['kind'] == 'object' and e.get('identity') == 'exact')) and shot.get('size', '') in ('', 'MS', 'MCU', 'CU', 'ECU'):   # D1
            out.append({'element_id': e['id'], 'use': 'texture', 'reference_ids': frames(e['id']), 'line': 'the texture reference: take only its surface: its colour, wear and joints'})
        if e['kind'] == 'place':   # D2
            out.append({'element_id': e['id'], 'use': 'look', 'reference_ids': frames(e['id']), 'line': 'the look reference: take only its light and colour'})
    return out


def light_warning(scene, kind, prompt):
    """design/103 A1: a keyframe in a lit scene names the scene's light word for word; a warning in this release."""
    light = (scene or {}).get('light', '').strip().rstrip('.')
    if kind == 'keyframe' and light and light not in prompt:
        return f"the prompt does not carry the scene's light sentence word for word ('{light}'): one light per scene, so the shots match" + NEXT_RELEASE
    return None


def shot_guidance(shot, neighbours):
    """design/102 (course batch B): the lines for this shot's pictures and take; a graphic gets none, a close-up no layers, a still no camera line."""
    if shot.get('visual_type') in GRAPHIC_TYPES:
        return []
    lines = []
    if 'close' not in str(shot.get('framing') or '').lower():   # B1
        lines.append('Name a foreground, a midground and a background. When the camera travels, write the parallax: what is near slides past faster than what is far.')
    lines += ['Where a face is hidden or small, carry the action in the hands, shoulders and posture, beat by beat.',   # B2
              'Two or three imperfections at their places in this shot, not copied from the scene. Work leaves traces: tools, offcuts, mortar droppings, '
              'footprints on an active site; signs of use in a finished house.',   # B8
              'Thirds by default, the centre only on purpose; use leading lines and give a moving subject room ahead. To show a task, a first-person frame '
              'with the hands in front is an option.']   # B10, B13
    support = {(s or {}).get('support') for s in neighbours.values()} - {None, 'unknown'}
    if shot.get('visual_type') == 'video' and support:   # B4: the camera matches the clips beside the gap
        lines.append('The clips beside this gap are handheld: ask for slight handheld micro-movement in the take.' if 'handheld' in support
                     else 'The clips beside this gap are steady: keep the camera steady in the take.')
    return lines


AMBIENT_START = ("Put in the frame what the scene's ambient line says moves (the trees, the people in the background, the dust in the light), "
                 'so the take can move it.')   # design/101 M5


def prepare_take(store, user, run, outputs, body):
    session = session_of(store, run, outputs)
    plan_full, _, _, planned = guarded(lambda: locate(store, session, body['shot_id']))
    _route_gate(planned, 'video')
    _no_question(session, body['shot_id'], body.get('start_image'), body.get('end_image'))   # design/110 rule 0
    need(body.get('start_image'), 'A start image is required.')
    if session['references'].get(body['start_image']):
        try:
            _not_yet_gate(store, session, session['references'][body['start_image']], shot=planned)   # design/110 F3: never a take from a start that shows the result
        except ValueError:
            save_session(store, run, session)
            raise
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
    need(str(body.get('continuity_notes') or '').strip(), 'Continuity notes are required: what stays unchanged between the two frames, and for a person five traits from the sheet (`--continuity`).')   # design/84 V2
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
    used = [sid for sid, rid in _start_images(store, session).items() if rid == body['start_image'] and sid != body['shot_id']] + \
           [sid for sid, a in session['assets'].items() if sid != body['shot_id'] and a.get('reference_id') == body['start_image']]
    warns, form = [], [] if answer is not None else ['no answer form with this take: write the motion prompt with the library\'s form (--answer), so its checklist is checked' + NEXT_RELEASE]   # design/89 C4
    beats = {b['id']: b for s in planned.get('subjects') or [] for b in s.get('beats') or []}   # design/91 N1: when each change happens is its beat's frames
    changes = [{'what': c['what'], 'beat_id': c['beat_id'], 'at_s': [round((beats[c['beat_id']]['start_frame'] - planned['start_frame']) / float(fps), 2),
                                                                     round((beats[c['beat_id']]['end_frame'] - planned['start_frame']) / float(fps), 2)]}
               for c in planned.get('changes') or [] if c.get('beat_id') in beats]
    if not changes:
        form.append('no change list on this shot: list what differs between the start and the end picture and the beat that causes each (changes), so the pair is checked' + NEXT_RELEASE)
    _rule(session, not used, f"H5: {body['start_image']} is already the start of {used[0] if used else ''}; two shots never share a start image (an end image may start the next segment of one shot).", warns)
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
              'generated_audio_policy': 'retain original output; never replace narration automatically', **({'answer': answer} if answer is not None else {}),
              **({'changes': changes} if changes else {}),   # design/91 N1: the take check reads them too (N3)
              **({'ambient': base['preparation']['scene']['ambient']} if base['preparation']['scene'].get('ambient') else {}),
              **({'tool_lines': tool_lines(plan_full, base['preparation']['scene'], shot, 'motion')} if shot.get('props') else {}),   # design/110 F5: the whole plan, for the tool's name
              **({'heading_lines': heading_lines(base['preparation']['scene'], shot, 'motion')} if heading_lines(base['preparation']['scene'], shot, 'motion') else {}),   # design/110 F6
              **({'person_lines': person_lines(plan_full, base['preparation']['scene'], shot)} if person_lines(plan_full, base['preparation']['scene'], shot) else {}),   # design/111 F16
              **({'gaze_lines': gaze_lines(plan_full, base['preparation']['scene'], shot, 'motion')} if gaze_lines(plan_full, base['preparation']['scene'], shot, 'motion') else {}),   # design/111 F7
              **({'fixed_line': fixed_line(base['preparation']['scene'], shot)} if fixed_line(base['preparation']['scene'], shot) else {}),   # design/111 F8
              **({'light': base['preparation']['scene']['light']} if base['preparation']['scene'].get('light') else {})}   # design/103 A1   # design/101 M3, M4: the take text and the take check read it
    record['effective_prompt'] = motion_text(record)
    identity = digest(record)
    save_json(store, key(run, f'takes/{identity}.request.json'), record)
    pair = None
    if changes:   # design/91 N1: Gemini lists what differs; a difference no change explains is marked, never refused
        pk = digest({'start': s['sha256'], 'end': e['sha256'], 'changes': changes})
        pair = (session.get('pair_checks') or {}).get(pk)
        if pair is None or pair.get('error'):
            pair = _pair_check(store, s, e, changes)
            session.setdefault('pair_checks', {})[pk] = pair
        form += [f"marked: '{d['what']}' differs between the start and the end picture and has no cause in the change list: show the operator; they approve the pair "
                 'or the end image is changed' for d in pair.get('uncaused') or []]
        if pair.get('error'):
            form.append(f"the pair check could not run ({pair['error']}): compare the two pictures with the change list yourself")
    session['preparations'][body['shot_id']] = {'preparation_id': identity, 'key': key(run, f'takes/{identity}.request.json'), 'start_image': body['start_image'], 'end_image': body['end_image'],
                                                'motion_prompt': body['motion_prompt'], **({'pair_check': pair} if pair else {}),
                                                **({'repeat_warnings': warns} if warns else {}),
                                                **({'checklist': answer.get('checklist') or []} if answer is not None else {})}   # design/74 L6
    save_session(store, run, session)
    return {'preparation_id': identity, 'duration_seconds': record['duration_seconds'], 'exact_seconds': record['placement']['exact_seconds'], 'provider': selected, **({'warnings': warns + form} if warns + form else {})}


PAIR_SCHEMA = {'type': 'object', 'properties': {'differences': {'type': 'array', 'items': {'type': 'object', 'properties': {'what': {'type': 'string'}, 'change': {'type': 'integer'}},
                                                                                          'required': ['what', 'change']}}}, 'required': ['differences']}


def _pair_check(store, start, end, changes):
    """design/91 N1: one Gemini Flash call on the two pictures; every visible difference, matched to the change that causes it (0: none). Never raises."""
    rec = {'model': MEASURE_MODEL, 'differences': [], 'uncaused': []}
    try:
        key_ = settings().GEMINI_API_KEY.get_secret_value().strip()
        if not key_:
            return {**rec, 'error': 'no Gemini key on the server'}
        listed = '\n'.join(f"{n}. {c['what']}" for n, c in enumerate(changes, 1))
        parts = [{'text': 'Image 1: the start of a video shot.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(start['key'])).decode()}},
                 {'text': 'Image 2: the end of the same shot.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(end['key'])).decode()}},
                 {'text': 'List every visible difference between Image 1 and Image 2: anything that appears, disappears, moves, opens, grows, shrinks, changes shape, count, colour '
                          'or state; a person\'s place, pose or what they hold; the light. Ignore the camera\'s framing. For each difference give the number of the planned change '
                          'below that causes it, or 0 when none does. Be literal.\nPlanned changes:\n' + listed}]
        received = _gemini_transport()(key_, MEASURE_MODEL, terminal_deadline_seconds=120, initial_soft_wait_seconds=30, on_update=lambda e: None, capture_answer_deltas=False).generate(
            {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': PAIR_SCHEMA, 'maxOutputTokens': 4096}})
        body = received.get('body') if isinstance(received.get('body'), dict) else json.loads(received.get('raw') or '{}')
        diffs = [{'what': str(d.get('what') or '')[:300], 'change': d.get('change') if isinstance(d.get('change'), int) else 0} for d in body.get('differences') or [] if isinstance(d, dict)]
        return {**rec, 'differences': diffs, 'uncaused': [d for d in diffs if not 1 <= d['change'] <= len(changes)]}
    except Exception as exc:   # the check never blocks a take
        return {**rec, 'error': f'{exc.__class__.__name__}: {str(exc)[:200]}'}


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
    quote = said(quote, 'Rejected' if decision == 'rejected' else 'Accepted', user)   # design/99 C3: a take's reason is optional
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
    need(not re.search(r'\breject', f'{quote or ""} {notes or ""}', re.I),   # design/106 T3: select places a take; words that reject it never do
         'Your words say reject: select places the take in the film. To reject a take, run `vw visuals review --job J --decision rejected --notes "…"`.')
    session = session_of(store, run, outputs)
    quote = said(quote, 'Selected', user)   # design/99 C2
    job = conn.execute("select * from vw2_jobs where id=%s and run_id=%s and provider='video'", (job_id, run['id'])).fetchone()
    need(job and job['status'] == 'ready', 'Select a ready take.')
    _no_question(session, job['unit'])   # design/110 rule 0
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
    shot = guarded(lambda: locate(store, session, job['unit']))[3]
    return {**session['selections'][job['unit']], 'next': f"Take selected: in the film at {film_time(session, shot)} ({job['unit']})."}   # design/97 A4


def made_for(session, row):
    """design/94 R1.1: the shot a picture was made for; a fix made before shots were recorded takes its original's."""
    return row.get('shot_id') or (session['references'].get(row.get('fix_of')) or {}).get('shot_id')


def still_from_reference(store, user, run, outputs, shot_id, reference_id, quote, reuse=None, crop=None, move=None):
    """design/45 10.3: an approved reference becomes a still shot's asset; no download and upload. design/89 H2-H5: never a picture already on screen."""
    session = session_of(store, run, outputs)
    out = _place_still(store, user, run, outputs, session, shot_id, reference_id, quote, reuse, crop, move)
    save_session(store, run, session)
    return out


def _place_still(store, user, run, outputs, session, shot_id, reference_id, quote, reuse=None, crop=None, move=None):
    """The placement on a loaded session, saved by the caller (design/94 A1: approving places in the same save)."""
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    _route_gate(shot, 'still')
    _no_question(session, shot_id, reference_id)   # design/110 rule 0
    row = session['references'].get(reference_id)
    need(row and row['status'] == 'approved', f'Reference {reference_id} is not an approved reference of this run.')
    quote = said(quote, 'Placed', user)   # design/99 C2
    need(row.get('kind') != 'web', 'a web picture is a guide only; it cannot appear in the film.')   # design/94 R1.5 (U2)
    warns = []
    made = made_for(session, row)
    if made and made != shot_id:   # R1.7 (L2): only into its own shot, or moved with the operator's words
        need(str(move or '').strip(), f"{reference_id} was made for {made}; make one for {shot_id} (`vw visuals image --shot {shot_id} …`), or move it with the operator's words (--move).")
    elif not made and row.get('kind') in ('keyframe', 'state'):
        warns.append(f'{reference_id} has no shot recorded; from the next release a picture is placed only in the shot it was made for')
    used = [sid for sid, a in session['assets'].items() if sid != shot_id and a.get('reference_id') == reference_id] + [sid for sid, rid in _start_images(store, session).items() if rid == reference_id and sid != shot_id]
    _rule(session, not used, f'H5: this picture is already in {used[0] if used else ""}. Two shots never show the same picture: compose another (a reimagined shot, return_of, for a return), '
                             f'or take it out there first: `vw visuals unplace --shot {used[0] if used else ""}`, or Remove on the page.', warns)   # design/94 R1.8
    if made and made != shot_id:
        row.update(shot_id=shot_id, moved={'from': made, 'to': shot_id, 'quote': move, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()})
    held = session['assets'].get(shot_id) or {}
    replaced = held.get('reference_id') or held.get('clip_id')   # a picture or a clip stretch taken out by this placement
    kept = None
    src = row.get('source') or {}
    if row.get('kind') == 'frame' and src.get('media_id') is not None:
        at = float(src.get('requested_s') or 0)
        kept, more = _reuse_gate(store, run, session, outputs, shot, src['media_id'], at, at, False, reuse, quote, crop, {'action': 'still', 'reference_id': reference_id})
        warns += more
    session['assets'][shot_id] = {'kind': 'still', 'key': row['key'], 'sha256': row['sha256'], 'bytes': row['bytes'], 'reference_id': reference_id, 'quote': quote, 'by': user['id'],
                                  'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame']}, **({'reuse': kept} if kept else {}), **({'repeat_warnings': warns} if warns else {})}
    session['selections'].pop(shot_id, None)
    (session.get('reuse_pending') or {}).pop(shot_id, None)
    return {'shot_id': shot_id, 'kind': 'still', 'reference_id': reference_id, 'sha256': row['sha256'], **({'replaced': replaced} if replaced and replaced != reference_id else {}),
            **({'warnings': warns} if warns else {})}


def unplace(store, user, run, outputs, shot_id, quote):
    """design/94 R1.8 (L3): a shot's still, sequence or clip taken out with the operator's words; the picture stays approved."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    quote = said(quote, 'Removed', user)   # design/99 C2
    asset = session['assets'].get(shot_id)
    need(asset, f'{shot_id} holds no picture.')
    need(gap['gap_id'] not in session['recorded_gaps'], f"{shot_id}'s gap {gap['gap_id']} is recorded; a recorded gap keeps its pictures.")
    removed = asset.get('reference_id') or [st.get('reference_id') for st in asset.get('states') or []] or asset.get('clip_id')
    session.setdefault('unplaced', []).append({'shot_id': shot_id, 'kind': asset['kind'], 'removed': removed, 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()})
    del session['assets'][shot_id]
    save_session(store, run, session)
    return {'shot_id': shot_id, 'kind': asset['kind'], 'removed': removed, 'next': f'Taken out of {shot_id}: it stays approved.'}


REUSE_APART_S = 60          # design/89 H4 (SK): an approved reuse is at least this far from the other showing
REUSE_MIN_ZOOM = 1 / 0.7    # a clearly different framing: a crop of 30 % (1.43×), only within the clip's safe enlargement


def media_clips(outputs):
    media = next((o for o in outputs if o['stage'] == 'media' and o['unit'] is None), None)
    return {c['id']: c for c in ((media or {}).get('summary') or {}).get('clips') or []}


def _sec(frames, fps):
    return float(Fraction(int(frames)) / Fraction(str(fps)))


def ledger(store, session, outputs):
    """design/89 H1: what the film shows, first cut and visuals alike: clip stretches (moving), footage frames (frozen), other pictures."""
    fps = session['source'].get('fps') or 25
    clips = media_clips(outputs)
    events = session.get('first_cut_events')
    if events is None:   # a session prepared before batch 1
        events = first_cut_events(store, outputs)
    out = []
    for ev in events:
        if ev.get('kind', 'event') == 'event':
            cid = str(ev['sub_clip_id']).rsplit(':', 1)[0]
            cf = (clips.get(cid) or {}).get('fps') or fps
            out.append({'where': 'first cut', 'shot_id': ev['sub_clip_id'], 'clip_id': cid, 'moving': True, 'src_in_s': _sec(ev['source_in_frame'], cf), 'src_out_s': _sec(ev['source_out_frame'], cf),
                        'film_in_s': _sec(ev['timeline_in_frame'], fps), 'film_out_s': _sec(ev['timeline_out_frame'], fps)})
    for sid, a in (session.get('assets') or {}).items():
        p = a.get('placement') or {}
        base = {'where': 'visuals', 'shot_id': sid, 'film_in_s': _sec(p.get('start_frame', 0), fps), 'film_out_s': _sec(p.get('end_frame', 0), fps)}
        if a.get('kind') == 'clip':
            out.append({**base, 'clip_id': a['clip_id'], 'moving': True, 'src_in_s': a['in_s'], 'src_out_s': a['out_s']})
        elif a.get('kind') == 'still':
            src = (session['references'].get(a.get('reference_id')) or {}).get('source') or {}
            at = float(src.get('requested_s') or 0)
            out.append({**base, 'clip_id': src.get('media_id'), 'reference_id': a.get('reference_id'), 'moving': False, 'src_in_s': at, 'src_out_s': at})
    return out


def _crop_check(crop, safe):
    """H4: a crop inside the frame, of the frame's shape, enlarging at least REUSE_MIN_ZOOM and no more than the clip's safe enlargement."""
    if not (isinstance(crop, (list, tuple)) and len(crop) == 4):
        return None, 'H4: give the crop that makes the framing clearly different (--crop x,y,w,h, fractions of the frame).'
    x, y, w, h = (float(v) for v in crop)
    if not (0 <= x and 0 <= y and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1.0001 and y + h <= 1.0001 and abs(w - h) <= 0.01):
        return None, 'H4: the crop lies inside the frame and keeps its shape (w equal to h).'
    zoom = 1 / max(w, h)
    if not REUSE_MIN_ZOOM - 1e-6 <= zoom <= safe + 1e-6:
        return None, f"H4: the crop enlarges {zoom:.2f}×; it must be between {REUSE_MIN_ZOOM:.2f}× and the clip's safe {safe:.2f}×."
    return [x, y, w, h], ''


def _reuse_gate(store, run, session, outputs, shot, clip_id, src_in, src_out, moving, reuse, quote, crop, pending):
    """design/89 H2-H4 with SK's H4: a clip already on screen is a reuse: never a frozen frame of a clip that plays elsewhere; otherwise only with the
    reason, the reimagined shot considered and the operator's words, 60 s apart, a different stretch, and a crop within the clip's safe enlargement.
    Returns (the reuse kept with the asset or None, the warnings): in a session begun before batch 1 every broken rule is a warning instead."""
    fps = session['source'].get('fps') or 25
    film_in, film_out = _sec(shot['start_frame'], fps), _sec(shot['end_frame'], fps)
    others = [e for e in ledger(store, session, outputs) if e.get('clip_id') == clip_id and e['shot_id'] != shot['id']]
    warns = []
    if not others:
        return None, warns
    names = ', '.join(f"{e['shot_id']} ({e['where']})" for e in others)
    if not moving:
        _rule(session, not any(e['moving'] for e in others), f'H3: clip {clip_id} plays elsewhere ({names}); a frozen frame of it is never shown: use another clip, or a moving stretch with an approved reuse.', warns)
    else:
        _rule(session, all(e['moving'] for e in others), f'H3: clip {clip_id} is shown as a frozen frame in {names}; a clip is either moving or a frame in the film, never both.', warns)
    r = reuse or {}
    why = bool(str(r.get('reason') or '').strip() and str(r.get('considered') or '').strip())
    _rule(session, why, f'H2: clip {clip_id} is already on screen in {names}: showing it again is a reuse. Prefer a reimagined shot (the same subject from another angle, distance or moment, '
                        "return_of). A plain reuse needs the reason, the reimagined shot you considered and why it adds nothing (--reuse, --considered, or the page's reuse fields), then the operator's approval.", warns)
    for e in others:
        apart = max(film_in - e['film_out_s'], e['film_in_s'] - film_out)
        _rule(session, apart >= REUSE_APART_S, f"H4: {shot['id']} is {apart:.0f} s from {e['shot_id']}; an approved reuse is at least {REUSE_APART_S} s apart.", warns)
        _rule(session, src_out <= e['src_in_s'] or src_in >= e['src_out_s'] if (moving or e['moving']) else abs(src_in - e['src_in_s']) >= 1.0,
              f"H4: a different stretch of clip {clip_id} from the one in {e['shot_id']}, with no overlap in the clip's own time.", warns)
    safe = float((session.get('clip_safe_zoom') or {}).get(clip_id) or 1.0)
    _rule(session, safe >= REUSE_MIN_ZOOM - 1e-6, f'H4: clip {clip_id} can be enlarged only {safe:.2f}× before it goes soft; a clearly different framing needs {REUSE_MIN_ZOOM:.2f}×. '
                                                 'Use a reimagined shot instead (return_of): a soft picture is never the fix for a repeat.', warns)
    box, problem = _crop_check(crop, safe)
    _rule(session, box is not None, problem, warns)
    if session.get('repeat_rules') != 'refuse':   # a session begun before batch 1: placed as before, with its warnings
        return ({'reason': r.get('reason'), 'considered': r.get('considered'), 'crop': box, 'on_screen': names} if why and box else None), warns
    if not str(r.get('approval') or '').strip():   # H2, H7: the reuse itself waits for the operator's own words, on the page or in chat
        session.setdefault('reuse_pending', {})[shot['id']] = {**pending, 'clip_id': clip_id, 'on_screen': names, 'reason': r['reason'], 'considered': r['considered'],
                                                               'crop': box, 'quote': quote, 'at': datetime.now(timezone.utc).isoformat()}
        save_session(store, run, session)
        raise Problem(409, 'REUSE_WAITING', f"The reuse of clip {clip_id} in {shot['id']} passes the checks and waits for the operator's approval in their own words: on the visuals "
                                           f"page, or `vw visuals reuse --shot {shot['id']} --quote \"<their words>\"`.")
    return {'reason': r['reason'], 'considered': r['considered'], 'approval': r['approval'], 'crop': box, 'on_screen': names}, warns


def _start_images(store, session):
    """design/89 H5: each prepared take's start image (kept on the preparation since batch 1; read from its request before)."""
    out = {}
    for sid, p in (session.get('preparations') or {}).items():
        rid = p.get('start_image')
        if rid is None and p.get('key'):
            try:
                rid = (load_json(store, p['key']).get('start_image') or {}).get('reference_id')
            except Problem:
                rid = None
            p['start_image'] = rid   # kept in the session once read; saved with the session's next save
        if rid:
            out[sid] = rid
    return out


def fill_clip(store, user, run, outputs, shot_id, clip_id, in_s, quote, reuse=None, crop=None):
    """design/89 B3: a moving stretch of an original clip fills a still or a video shot, from its in point for exactly the shot's length."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    need(shot['visual_type'] in ('image', 'video'), f"shot {shot_id} is a {shot['visual_type']}: a clip stretch fills a still or a video shot, never a graphic.")
    clip = media_clips(outputs).get(clip_id)
    need(clip, f'Unknown clip {clip_id}.')
    need((quote or '').strip(), 'The operator reply is required.')
    seconds = _sec(shot['end_frame'] - shot['start_frame'], session['source'].get('fps') or 25)
    in_s = float(in_s)
    out_s = round(in_s + seconds, 3)
    need(in_s >= 0 and out_s <= float(clip.get('duration_s') or 0) + 1e-3, f"The stretch {in_s:.2f}–{out_s:.2f} s lies outside clip {clip_id} ({clip.get('duration_s')} s).")
    kept, warns = _reuse_gate(store, run, session, outputs, shot, clip_id, in_s, out_s, True, reuse, quote, crop, {'action': 'clip', 'clip_id': clip_id, 'in_s': in_s})
    if crop is not None:   # design/91 N15: the part of the clip the planner keeps
        need(len(crop) == 4 and all(0 <= float(v) <= 1 for v in crop) and crop[2] > 0 and crop[3] > 0 and crop[0] + crop[2] <= 1 + 1e-6 and crop[1] + crop[3] <= 1 + 1e-6,
             'A crop is x,y,w,h as fractions of the picture, inside it.')
    bars = _bars(clip, crop, session)
    if bars:
        warns.append(bars)
    session['assets'][shot_id] = {'kind': 'clip', 'clip_id': clip_id, 'name': clip['name'], 'sha256': clip['sha256'], 'bytes': clip.get('bytes'), 'fps': clip.get('fps'),
                                  'rotation_deg': clip.get('rotation_deg') or 0, 'hdr': str(clip.get('color_transfer') or '').lower() in ('arib-std-b67', 'smpte2084'),
                                  'in_s': in_s, 'out_s': out_s, 'quote': quote, 'by': user['id'], 'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame']},
                                  **({'crop': list(crop)} if crop is not None else {}),
                                  **({'reuse': kept} if kept else {}), **({'repeat_warnings': warns} if warns else {})}
    session['selections'].pop(shot_id, None)
    (session.get('reuse_pending') or {}).pop(shot_id, None)
    save_session(store, run, session)
    return {'shot_id': shot_id, 'kind': 'clip', 'clip_id': clip_id, 'in_s': in_s, 'out_s': out_s, **({'reuse': kept} if kept else {}), **({'warnings': warns} if warns else {})}


def _bars(clip, crop, session):
    """design/91 N15: a clip whose shape needs more than the fill cap keeps bars; say so, with the crop that would fill."""
    from .stage2.render import FILL_MAX_ZOOM, fit
    w, h = clip.get('width'), clip.get('height')
    if not w or not h:
        return None
    if int(clip.get('rotation_deg') or 0) % 180 == 90:
        w, h = h, w
    if crop is not None:
        w, h = w * crop[2], h * crop[3]
    res = session['source'].get('resolution') or [1920, 1080]   # defect 26: a run stores [1920, 1080] (the master's summary); '1920x1080' read too
    W, H = (int(x) for x in (res if isinstance(res, (list, tuple)) else str(res).split('x')))
    fill, zoom = fit(w, h, W, H)
    return None if fill else (f"clip {clip.get('name')} is {int(w)}x{int(h)}: filling the {W}x{H} frame needs {zoom:.2f}x, over the {FILL_MAX_ZOOM}x cap, so it keeps bars; "
                              'give a crop with the frame\'s shape (--crop x,y,w,h), or choose another clip')


def approve_reuse(store, user, run, outputs, shot_id, quote):
    """design/89 H2, H7: the operator approves a proposed reuse with their own words, on the page or in chat; the same placement function runs again."""
    session = session_of(store, run, outputs)
    p = (session.get('reuse_pending') or {}).get(shot_id)
    need(p, f'No reuse is waiting for shot {shot_id}.')
    need((quote or '').strip(), "The operator's words approving the reuse are required.")
    reuse = {'reason': p['reason'], 'considered': p['considered'], 'approval': quote}
    if p['action'] == 'clip':
        return fill_clip(store, user, run, outputs, shot_id, p['clip_id'], p['in_s'], p.get('quote') or quote, reuse, p['crop'])
    return still_from_reference(store, user, run, outputs, shot_id, p['reference_id'], p.get('quote') or quote, reuse, p['crop'])


def _fingerprints(store, key_):
    from . import lookalike
    try:
        data = store.get(key_)
        return {'picture': lookalike.image_hashes(data)[0], 'graphic': lookalike.image_hashes(data, True)[0]}
    except Exception:   # a picture that cannot be read has no fingerprint
        return None


def look_alike_placed(store, session):
    """design/89 H6 at the plan stage: the pictures already placed (stills, the first state of a sequence, prepared starts) that look alike."""
    from . import lookalike
    fps = session['source'].get('fps') or 25
    items = []   # (shot, start frame, reference id, file key, graphic)
    starts = _start_images(store, session)
    for sid, a in (session.get('assets') or {}).items():
        first = (a.get('states') or [{}])[0] if a.get('kind') == 'sequence' else {}
        rid, key_ = (a.get('reference_id'), a.get('key')) if a.get('kind') == 'still' else (first.get('id') or first.get('reference_id'), first.get('key')) if a.get('kind') == 'sequence' else (None, None)
        if key_:
            items.append((sid, a.get('placement', {}).get('start_frame', 0), rid, key_, a.get('kind') == 'sequence'))
    for sid, rid in starts.items():
        r = session['references'].get(rid) or {}
        if r.get('key') and sid not in session.get('assets', {}):
            items.append((sid, 0, rid, r['key'], False))
    rows = []
    for sid, start, rid, key_, graphic in sorted(items, key=lambda x: x[1]):
        kept = (session['references'].get(rid) or {}).get('dhash')   # finding 9: the fingerprint kept at approval; the file is read only for a picture approved before it
        if kept is None:
            kept = _fingerprints(store, key_)
        if kept is not None:
            rows.append({'label': sid, 'at_s': _sec(start, fps), 'graphic': graphic, 'hashes': [kept['graphic' if graphic else 'picture']]})
    return lookalike.pairs(rows)


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


def status(conn, store, run, outputs, repair=True):
    """repair: the run's lock is held, so a repaired session may be saved; without it the answer is read as stored (design/92: busy)."""
    try:
        session = session_of(store, run, outputs)
    except Problem:
        return {'state': 'not_prepared', 'next': 'prepare'}
    if reconcile(conn, run, session) and repair:
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
    refs = [{**{k: r.get(k) for k in ('id', 'name', 'kind', 'element_id', 'status', 'sha256', 'job_id')}, 'note': (r.get('source') or {}).get('note') or '', 'sources_changed': bool(r.get('sources_changed'))}   # design/106 N4; design/110
            for r in session['references'].values()]
    take_rows = take_jobs(conn, run)
    jobs_ = [{**{k: j[k] for k in ('id', 'unit', 'provider', 'status', 'error', 'cost')}, 'checklist': take_checklist(session, j),   # design/74 L6
              'verdict': ((session['reviews'].get(str(j['id'])) or [{}])[-1]).get('decision'),   # defect 30: a rejected take stays 'ready' as a job
              'check_marks': [{k: m.get(k) for k in ('check', 'at_s', 'seen')} for m in ((session.get('take_checks') or {}).get(str(j['id'])) or {}).get('must_failed') or []]}   # design/91 N3
             for j in take_rows]
    t = session.get('treatment')
    sp = visuals_spend(conn, run)
    return {'state': 'prepared', 'busy': not repair, 'plan_digest': session.get('current'), 'versions': len(session['versions']), 'gaps': gaps, 'references': refs, 'jobs': jobs_,
            'searches': _searches(session),   # design/73: the searches, their picks and any "nothing fits" reason, for the assistant
            'round': _round_view(session),    # design/79: pass 1, pass 2 or complete, with each element's verdict
            'treatment': ({k: t[k] for k in ('totals', 'estimate_inr', 'quote', 'by', 'at', 'digest')} if t else None),   # design/65 B6
            'footage': {k: (footage_view(session, outputs) or {}).get(k) for k in ('line', 'summary')},   # design/88
            'waiting': waiting(session, plan, run.get('code'), take_rows),   # design/97 W4: each with its label and link
            'spec_corrections': {sid: c.get('words') for sid, c in (session.get('spec_corrections') or {}).items()},   # review 27 Oct: the assistant revises these specs
            'questions': dict(session.get('questions') or {}),   # design/110 rule 0: the open questions, by item
            'material_specs': {e['id']: {'approved': material_approved(session, e), 'correction': ((session.get('spec_corrections') or {}).get(material_key(e['id'])) or {}).get('words')}
                               for e in (plan or {}).get('elements') or [] if e.get('material_spec')},   # design/111 F10
            'golden': dict(session.get('golden') or {}), 'golden_due': golden_due(session, plan) if plan else [],   # design/111 F11
            'not_this': {eid: list(rec.get('lines') or []) for eid, rec in (session.get('not_this') or {}).items()},   # design/111 F12
            'needed_elements': needed_elements(plan) if plan else [],   # design/111 F14
            'figure_repeats': [{'reference_id': r['id'], 'shot_id': made_for(session, r), 'detail': r['figure_check'].get('detail', '')} for r in session['references'].values()
                               if (r.get('figure_check') or {}).get('repeated') and r.get('status') == 'approved'],   # design/111 F17
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
                          'media': {'kind': 'sequence', 'states': media_states, 'dissolve_frames': asset['dissolve_frames'], 'motion': s.get('motion') or 'push_in', 'graphic': True}})   # design/89 B2
        elif asset['kind'] == 'clip':   # design/89 B3: a moving stretch of an original clip
            name = f"{s['id']}-clip-{asset['name']}"
            files.append({'name': name, 'key': f"{run['id']}/media/{asset['name']}", 'sha256': asset['sha256'], 'bytes': asset.get('bytes'), 'location': 'storage', 'receipt': True})
            shots.append({'shot_id': s['id'], 'source': 'clip', 'kind': 'clip', 'placement': asset['placement'],
                          'media': {'kind': 'clip', 'clip': {k: asset.get(k2) for k, k2 in (('id', 'clip_id'), ('name', 'name'), ('sha256', 'sha256'), ('fps', 'fps'), ('rotation_deg', 'rotation_deg'), ('hdr', 'hdr'))},
                                    'in_s': asset['in_s'], 'out_s': asset['out_s'], 'crop_rect': asset.get('crop') or (asset.get('reuse') or {}).get('crop')}})
        else:
            name = f"{s['id']}-asset{'.mp4' if asset['kind'] == 'movie' else '.png'}"
            files.append({'name': name, 'key': asset['key'], 'sha256': asset['sha256'], 'bytes': asset['bytes'], 'location': 'storage', 'receipt': True})
            jobs.record_file(conn, run['id'], STAGE, asset['key'], name, asset['sha256'], asset.get('bytes') or 0, 'video/mp4' if asset['kind'] == 'movie' else 'image/png')   # design/82 U1: a still from a reference was never an upload
            shots.append({'shot_id': s['id'], 'source': 'asset', 'kind': asset['kind'], 'placement': asset['placement'],
                          **({'media': {'kind': 'still', 'motion': s.get('motion') or 'push_in', 'graphic': s['visual_type'] in ('diagram', 'animation')}} if asset['kind'] == 'still' else {})})   # design/89 B2
        binding = session['bindings'].get(s['id']) or {}
        for eid, rows in binding.get('references', {}).items():
            for b in rows:
                r = session['references'][b['id']]
                files.append({'name': f"ref-{b['id'][:8]}.png", 'key': r['key'], 'sha256': r['sha256'], 'bytes': r['bytes'], 'location': 'storage', 'receipt': True})
                jobs.record_file(conn, run['id'], STAGE, r['key'], f"ref-{b['id'][:8]}.png", r['sha256'], r['bytes'], 'image/png')
    chosen = {s['id']: s for s in shots_of(plan, session, gap_id) if s.get('transition_in') or s.get('transition_out')}   # design/91 N16
    for sh in shots:
        s = chosen.get(sh['shot_id'])
        if s:
            sh['transition'] = {'in': s.get('transition_in') or '', 'out': s.get('transition_out') or '', 'reason': s.get('transition_reason') or ''}
    unique_files = unique_by_name(files)
    image_cost = [r.get('generation', {}).get('cost') for r in session['references'].values() if r.get('generation', {}).get('cost')]
    out = core.output(conn, user, run, {'stage': STAGE, 'unit': gap_id, 'files': unique_files, 'accepted_quote': quote,
                                        'summary': {'gap_id': gap_id, 'plan_digest': session['current'], 'shots': shots, 'take_cost': cost, 'image_cost': image_cost}})
    session['recorded_gaps'][gap_id] = str(out['id'])
    save_session(store, run, session)
    return {'gap_id': gap_id, 'output': str(out['id']), 'shots': len(shots)}
