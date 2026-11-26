"""Visuals stage: direction (chat model), reference library (frame / supplied / web / generated via OpenAI GPT Image 2.5),
bindings, video takes (Google Omni) and local assets, one stage output per gap.

Session state is one JSON object in storage ({run}/visuals/session.json); images, takes and plans are files.
Unit of the ledger = gap (from the planning certificate, or the approved first cut when the Mac slice exists);
a gap's output is recorded when every shot in it has a selected take or a local asset."""
import base64
import hashlib
import json
import logging
import math
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

from . import apify, core, film, generations, image_check, jobs, keys, library, video_generators
from . import footage as FM   # design/88
from .config import settings
from .errors import Problem, UNEXPECTED
from .planning.digest import digest
from .storage import storage
from .video_providers import motion_text, transfer
from .visual_contract import script_people_warnings   # design/151 Q4 (re-exported for the tool)
from .visual_contract import palette_warnings   # design/218 B
from .visual_contract import GAZE_CAMERA, take_seconds, STILL_MOVING_MAX_S, FROZEN_SHARE, _graphics_run, GRAPHIC_TYPES, STILL_TYPES, WARNING_PLAIN, all_scenes, answer_warnings, chosen_scenes, gap_digest, gap_own_digest, shared_digest, note_free_gap, need, route_of, routes, validate_plan, note_free_elements, note_free_scene

STAGE = 'visuals'
IMAGE_MODELS = {'generate': 'gpt-image-2.5-flare-2026-09-08', 'edit': 'gpt-image-2.5-sunburst-2026-09-08'}   # design/82 U4: pinned snapshots (API reference, 22 Oct 2026)
REF_KINDS = ('frame', 'supplied', 'web', 'isolated', 'sheet', 'keyframe', 'state', 'style', 'component', 'drawing')   # design/117 P1: a thing alone on a transparent background, placed by SVG scenes   # design/65: a state of a graphic sequence, generated from the previous state
TREATMENT_ROUTES = ('footage', 'still', 'graphic_sequence', 'video', 'drawn')   # design/113
DISSOLVE_S = 0.5   # between the states of a graphic sequence
MAX_INPUTS = 16    # design/71 P2: GPT Image's limit on input pictures (the library's fact sheet A5)


def said(quote, what, user):
    """design/99 C2: a click is the operator's verdict; their words are kept when given, else the record says who did what."""
    return str(quote or '').strip() or f"{what} by {user.get('name') or user.get('id')}"


def fail(message):
    raise Problem(422, 'VISUALS_CONTRACT', str(message))


def guarded(fn):
    """A refusal written for the operator (need: a ValueError) arrives as written. design/177: anything unexpected (a missing key, a wrong type) goes to
    the server log with its trace and reaches the chat tool as the page's one plain sentence (web._page_call), never as a bare key name."""
    try:
        return fn()
    except ValueError as exc:
        fail(exc)
    except KeyError as exc:   # a missing field in what the chat tool sent, or a record the run does not hold: the assistant can act on the name; the page has its own plain sentence (web._page_call)
        logging.getLogger('vw2.visuals').exception('a visuals call failed')
        raise Problem(422, 'VISUALS_CONTRACT', f'The request is missing {exc.args[0]!r}, or names something this run does not hold. Nothing was changed.')
    except (TypeError, ZeroDivisionError):
        logging.getLogger('vw2.visuals').exception('a visuals call failed')
        raise Problem(500, 'VISUALS_FAILED', UNEXPECTED)


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
        return _with_shot_prints(store, load_json(store, key(run, 'session.json')))
    except Problem:
        if not create:
            raise Problem(409, 'NOT_ALLOWED', 'Run `vw visuals prepare` first.')
    return {'contract': 'vw2-visuals-session-v1', 'source': gaps_source(store, outputs), 'versions': [], 'current': None,
            'accepted': {}, 'choice_selections': {}, 'references': {}, 'bindings': {}, 'generator_choices': {}, 'preparations': {},
            'reviews': {}, 'selections': {}, 'assets': {}, 'recorded_gaps': {}, 'repeat_rules': 'refuse'}   # design/89: a session begun before batch 1 is warned instead


def shot_prints(plan):
    """Issue 17 (R2, SK 25 Nov 2026): {shot id: the fingerprint of what a video or a render of the shot is made from}: the shot, its scene and its gap
    without their shots, the things it shows with the facts about them, and the part every gap shares (the foundation, the sequence rules)."""
    made, shared = {}, {'foundation': plan.get('foundation'), 'sequence_rules': plan.get('sequence_rules') or []}
    for gap in plan.get('gaps') or []:
        own = {k: v for k, v in gap.items() if k not in ('scenes', 'choices')}
        for sc in all_scenes(gap):
            for s in sc['shots']:
                used = set(s.get('element_ids') or [])
                made.setdefault(s['id'], []).append({'shot': s, 'scene': {k: v for k, v in sc.items() if k != 'shots'}, 'gap': own,
                                                     'elements': [e for e in plan.get('elements') or [] if e['id'] in used],
                                                     'facts': [f for f in plan.get('visual_facts') or [] if f.get('id') in (s.get('fact_ids') or []) or (f.get('about') and f['about'] in used)]})
    return {sid: digest({'made_from': m, 'shared': shared}) for sid, m in made.items()}


def _with_shot_prints(store, session):
    """Issue 17 (R2): a plan version recorded before 0.128.4 gets its shots' fingerprints from its file, once (they are kept with the next save).
    A file that cannot be read adds nothing: work made on that version counts as old, as before."""
    for v in session.get('versions') or []:
        if 'shots' not in v:
            try:
                v['shots'] = shot_prints(load_json(store, v['file']['key'])['document'])
            except (Problem, KeyError, TypeError, ValueError):
                pass
    return session


def other_plan(session, plan, job):
    """Issue 17 (R2): this video or render was made on another plan AND what it was made from is not the same there as in the plan now: its own
    shot's fingerprint (`shot_prints`) differs, or the version it was made on is unknown or has none. Work that names no plan is read as before.
    Retired: any new plan version made every unaccepted video and every render of the film old (the whole plan's fingerprint was compared)."""
    made_on = (job.get('request') or {}).get('plan_digest')
    if not made_on or made_on == digest(plan):
        return False
    was = next((v.get('shots') or {} for v in session.get('versions') or [] if v.get('plan_digest') == made_on), {}).get(job.get('unit'))
    return not was or was != shot_prints(plan).get(job.get('unit'))


def save_session(store, run, session):
    session['updated_at'] = datetime.now(timezone.utc).isoformat()
    save_json(store, key(run, 'session.json'), session)
    return session


# ---------- gaps ----------

def _fps(session):
    from fractions import Fraction
    return Fraction(str(session['source'].get('fps'))) if session['source'].get('fps') else None


def gaps_source(store, outputs):
    """Gaps come from the approved first cut when present, else from the master (design/125: the planning stage of version 1 is retired)."""
    first_cut = next((o for o in outputs if o['stage'] == 'first_cut' and o['unit'] is None), None)
    planning = next((o for o in outputs if o['stage'] == 'master' and o['unit'] is None), None)
    if not planning:
        raise Problem(409, 'NOT_ALLOWED', 'Visuals needs an approved master first.')
    base = first_cut['summary'] if first_cut and first_cut['summary'].get('gaps') is not None else planning['summary']
    gaps = {g['shot_id']: {'start_frame': g['start_frame'], 'end_frame': g['end_frame'], 'passage_ids': g.get('passage_ids', []), 'requirement': g.get('reason', '')} for g in base['gaps']}
    return {'from': 'first_cut' if base is not planning['summary'] else 'planning', 'fps': str(base.get('fps') or planning['summary']['fps']),
            'resolution': base.get('resolution') or planning['summary']['resolution'], 'plan_digest': planning['summary']['plan_digest'], 'gaps': gaps}


# ---------- direction ----------

def prepare(conn, store, user, run, outputs):
    session = session_of(store, run, outputs, create=True)
    new = not session.get('updated_at') and not session.get('cap_inr') and not session.get('cap_from')   # never saved (save_session stamps it) and no limit yet: read from the session itself, never from a second storage call that may fail
    if new or session.get('cap_from') == 'length':   # design/207: a new film's limit follows its length and only ever rises with it; a film in progress and the owner's figure are left alone
        session.update(cap_inr=max(float(session.get('cap_inr') or 0), cap_for(film_seconds(session, outputs))), cap_from='length')
    mark_kept(session, run)   # design/151 hotfix: the kept decision from the first step
    session.setdefault('library_version', library.latest())   # design/68 L2: the library a run reads, kept like the procedure version
    procedure = core.procedure_for(run, STAGE)
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
                else:   # design/125: the version-1 evidence contract is retired
                    raise Problem(409, 'RETIRED', f"Clip {o['unit']}: the version-1 evidence contract is retired; analysis uses the clip log (clip-log-v1).")
    media = next((o for o in outputs if o['stage'] == 'media' and o['unit'] is None), None)   # design/88: measured, not asked
    session['footage_measured'] = FM.measure(((media or {}).get('summary') or {}).get('clips') or [], logs, ((media or {}).get('summary') or {}).get('shot_on'))   # design/146
    session['clip_safe_zoom'] = {cid: float(log.get('max_safe_zoom_limit') or 1.0) for cid, log in logs.items()}   # design/89 H4: how far a reuse may be cropped
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
               'intended_visuals': [],   # design/202 (SK, 15 Nov 2026): the script's visual notes are not considered; the picture is chosen from the narration alone (design/65 S3 retired)
               'script_claims': script_claims(script),   # design/125 S3: the figures the narration rests on, checked or not
               'world_evidence': world, 'plan_schema': __import__('app.visual_contract', fromlist=['Plan']).Plan.model_json_schema(),
               'generator_catalog': video_generators.catalog(),
               **({'parts': procedure['parts']} if procedure.get('parts') else {})}   # design/124 C1: the instructions per step (version 3 on); version 2 has none
    session['intended_visuals'] = package['intended_visuals']   # design/86 K7: the packet reads them from the session
    save_session(store, run, session)
    pk = save_json(store, key(run, 'package.json'), package)
    return {'package': pk, 'gaps': list(session['source']['gaps']), 'library_version': session['library_version'], 'footage': (footage_view(session, outputs) or {}).get('line'),
            'cap_inr': cap_of(session), 'cap_from': session.get('cap_from') or 'older',   # design/207: the film's cost limit, told here so no instruction types a figure
            'next': 'settle the treatment with the operator and record it (`vw visuals treatment`), then write the plan (out/visual-plan.json, `vw visuals check`)'}   # design/124 A4 item 1


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


def script_claims(script):
    """design/125 S3: the figures or claims the narration rests on, as the script stage recorded them ({text, checked, source}); [] when none."""
    return list(((script or {}).get('summary') or {}).get('claims') or [])


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
    """design/88 F4: the line the operator is told, the summary and the per-clip map (design/125: the answer recorded at media is retired)."""
    f = session.get('footage')
    if not f or (not f.get('per_clip') and not session.get('footage_correction')):   # SK, 23 Nov 2026 (F10): no clip was measured, so there is no line to tell
        return None
    return {'line': FM.line(f['summary']), 'summary': f['summary'], 'per_clip': f['per_clip'], 'measured': (session.get('footage_measured') or {}).get('summary')}


def correct_footage(store, user, run, outputs, values, quote):
    """design/88 F4: the operator corrects the measured footage with their words; it wins for the rest of the run, on both front ends."""
    session = session_of(store, run, outputs)
    need(not no_real_clip(session), 'This film has no camera footage, so there is no footage line to correct. Its look is the one of the Direction the operator chose.')   # SK, 23 Nov 2026 (V9)
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


def library_version_of(session):
    """design/68 L2: the library a run reads; a session from before the release reads the latest."""
    return session.get('library_version') or library.latest()


def category_of(run):
    """design/137: the film's video category as the operator confirmed it; a film started before design/139 reads documentary-explainer
    (the older way, kept until it closes); a new film without one is refused, naming `vw category`."""
    return film.need_category(run)


def library_pack(store, run, outputs):
    """design/68 L3: every step's library files with their text, for the plugin to write once per step; design/136: by the film's category."""
    session = session_of(store, run, outputs)
    return library.steps(library_version_of(session), category_of(run), film.footage(run))


def _with_direction(session, document):
    """design/207 (SK, 16 Nov 2026): the server puts the recorded treatment's Direction at the head of the plan's foundation.treatment (the
    Direction, a blank line, then the text as sent) unless the text already starts from it (spacing is not a difference). The check and the
    proposal both call this before they read the plan, so both store the same document. No recorded Direction: nothing is placed."""
    direction = str((session.get('treatment') or {}).get('direction') or '').strip()
    if not direction or not isinstance(document, dict) or not isinstance(document.get('foundation'), dict):
        return document
    text = document['foundation'].get('treatment')
    text = text if isinstance(text, str) else ''
    if ' '.join(text.split()).startswith(' '.join(direction.split())):
        return document
    placed = (direction + '\n\n' + text).strip()
    need(len(placed) <= 16000, f"foundation.treatment is {len(placed):,} characters once the server places the treatment's Direction at its head; at most 16,000. "
                               'Shorten your own text there: you do not copy the Direction, the server places it.')
    return {**document, 'foundation': {**document['foundation'], 'treatment': placed}}


def _counted_shots(gap):
    """The shots of a gap the film counts: its scenes, or those of the recommended way (else the first), as routes() counts them."""
    scenes = gap.get('scenes') or []
    if gap.get('choices'):
        scenes = next((c for c in gap['choices'] if c['id'] == gap.get('recommended_choice')), gap['choices'][0]).get('scenes') or []
    return [sh for sc in scenes for sh in sc['shots']]


def _ways_departed(session, plan):
    """A gap made a way the recorded treatment did not name, one sentence per gap: a fault of the check (design/207) and a refusal of the proposal."""
    out = []
    for gap in plan['gaps']:
        said = set()
        for e in session['treatment']['gaps']:
            if e['gap_id'] == gap['gap_id']:
                said = set(e['routes']) | ({'still'} if 'footage' in e['routes'] else set())   # a frame shown in the film is a still in the plan
        used = {route_of(sh) for sh in _counted_shots(gap)}
        if not used <= said:
            out.append(f"gap {gap['gap_id']}: the plan uses {sorted(used)} but the treatment says {sorted(said)}; record a new treatment with the reason, or change the plan.")
    return out


def stand_in_shots(session, plan):
    """design/207 (D1): {shot id: [names]}: the first counted shot that shows each real, named person (`speaker`) as a stand-in: no permission is
    recorded for them and the shot is not their own footage. Read from the session as it stands now, so the line goes once the permission is recorded."""
    real = {e['id']: e.get('name') or e['id'] for e in plan.get('elements') or [] if e.get('kind') == 'person' and e.get('speaker') and not likeness_of(session, e['id'])}
    out, told = {}, set()
    for gap in plan.get('gaps') or []:
        for sh in _counted_shots(gap):
            for eid in sh.get('element_ids') or []:
                if eid in real and eid not in told and sh['visual_type'] != 'footage':   # their own footage is them, not a stand-in
                    told.add(eid)
                    out.setdefault(sh['id'], []).append(real[eid])
    return out


def supplied_missing(session, plan):
    """Release 3, C3 (SK, 20 Nov 2026): {shot id: [(element id, name)]}: the first counted shot that shows each thing named as a logo or a brand
    mark for which the run holds no picture given by the operator (supplied, from the web or a footage frame; a rejected one is none). Read
    from the session as it stands now, so the line goes once the file is given. What the server cannot see, the run folder, the tool adds."""
    given = {r.get('element_id') for r in (session.get('references') or {}).values() if r.get('kind') in ('supplied', 'web', 'frame') and r.get('status') != 'rejected'}
    logos = {e['id']: e.get('name') or e['id'] for e in plan.get('elements') or [] if LOGO.search(str(e.get('name') or '')) and e['id'] not in given}
    out, told = {}, set()
    for gap in plan.get('gaps') or []:
        for sh in _counted_shots(gap):
            for eid in sh.get('element_ids') or []:
                if eid in logos and eid not in told:
                    told.add(eid)
                    out.setdefault(sh['id'], []).append((eid, logos[eid]))
    return out


def text_no_labels(shot):
    """design/221 (the critic's A1, point 4): a drawn shot that carries text (`carries_text`, or a spec label that is not the corner note) and
    lists no labels. Release 3, C4: one rule for the warning at the plan and the gate before the first brief."""
    return (shot.get('visual_type') == 'drawn' and not (shot.get('scene_motion') or {}).get('labels')
            and bool(shot.get('carries_text') or _flat((shot.get('drawing_spec') or {}).get('label')) not in ('', _flat(corner_note(shot.get('drawing_spec'))))))


def palette_due(session, plan):
    """design/218 B: the palette warning only while no gap was ever accepted; after that the approved palette is never edited (an edit sends the
    accepted gaps back to the operator) and a drawing that needs a colour gets a recorded neutral (`vw motion colour`)."""
    if session.get('accepted') or session.get('shared_pending'):
        return []
    return answer_warnings(plan, palette_warnings(plan, session.get('added_colours')))


# The critic's point 9 (19 Nov 2026): a move is the camera's only in a sentence whose subject is the camera or the view (CAMERA_SUBJECT), or when the
# words are a camera term whatever the subject (the *_BARE lists): "the lid tilts up" and "a pan on the stove" are the things, not the camera.
# ponytail: word lists, a warning only; a thing named "frame" or "shot" that moves in its own sentence is flagged too.
CAMERA_SUBJECT = re.compile(r'\b(?:camera|view|frame|shot|we)\b', re.I)
CLOSER_BARE = r'push(?:es|ed|ing)?[- ]in(?:to)?|zoom(?:s|ed|ing)?[- ](?:in|out)(?:to)?|doll(?:y|ies|ying)'
SIDEWAYS_BARE = r'orbit(?:s|ed|ing)?|tracking\s+shot'
CAMERA_CLOSER = (re.compile(rf'\b(?:{CLOSER_BARE})\b', re.I),
                 re.compile(rf'\b(?:{CLOSER_BARE}|zoom(?:s|ed|ing)?|pull(?:s|ed|ing)?[- ]back|punch(?:es|ing)?[- ]in|mov(?:es?|ed|ing)\s+(?:closer|in|back|away))\b', re.I))
CAMERA_SIDEWAYS = (re.compile(rf'\b(?:{SIDEWAYS_BARE})\b', re.I),
                   re.compile(rf'\b(?:{SIDEWAYS_BARE}|pan(?:s|ned)?\s+(?:slowly\s+)?(?:along|across|left|right|up|down|over|to|from|with)|pans|panned|panning|'
                              r'track(?:s|ed|ing)?\s+(?:along|across|with|past)|tilt(?:s|ed|ing)?\s+(?:up|down)|whip(?:s|ping)?\s+(?:to|pan))\b', re.I))
LARGE_CHANGE = re.compile(r'\b(?:whole|entire|all\s+of\s+the|most\s+of\s+the|more\s+than\s+half(?:\s+of)?\s+the|(?:half|two[- ]thirds|three[- ]quarters)\s+of\s+the)\s+'
                          r'(?:frame|picture|image|scene|room)\b', re.I)   # fix set M4: a change an edit region (a third at most) cannot hold; the critic's point 9: of the frame as a whole, not of one part


def camera_words(shot):
    """Fix set M1 (19 Nov 2026): the words of a drawn shot that ask for a camera move its camera_flow does not allow, else '': a fixed flow (none
    named is fixed) allows none; a flow that scales the picture allows no sideways move; Pan along allows no move closer or back."""
    flow = shot.get('camera_flow') or 'fixed'
    text = '. '.join(str(shot.get(k) or '') for k in ('depicts', 'purpose', 'message', 'framing', 'information_progression', 'camera', 'camera_move'))
    for sentence in re.split(r'[.;!?\n]+', text):
        for no, (bare, moved) in (('pan_along', CAMERA_SIDEWAYS), ('step_closer pull_back follow slow_push_in', CAMERA_CLOSER)):
            m = None if flow in no.split() else (moved if CAMERA_SUBJECT.search(sentence) else bare).search(sentence)
            if m:
                return m.group(0)
    return ''


def carried_warnings(session, run, plan, outputs):
    """design/207: what the treatment settled, carried to the plan. Warnings, never refusals, the same from the check and the proposal:
    a gap with more still seconds than the operator accepted for it (half a second of tolerance; seconds whose way the treatment never told
    are not guessed as moving); still pictures over their share of the film, on the first gap that has one; a card of words in a documentary
    or an explaining film (never on a film with no category recorded); a real speaker made by the AI from words while no permission for their
    own likeness is recorded; on a film whose reference round compares people, every pair of people whose descriptions read alike, in one
    technical warning (`people_alike`), before the round refuses them pair by pair. A gap the treatment gave as footage may show a frame as a still."""
    fps = float(Fraction(str(session['source'].get('fps') or 25)))
    agreed = {e.get('gap_id'): e for e in (session.get('treatment') or {}).get('gaps') or [] if isinstance(e, dict)}
    words_spoken = not film.older(run) and film.category(run) == 'documentary-explainer'   # a film with no category recorded (an older film too) gets no warning
    stand_ins, to_give, labelled = stand_in_shots(session, plan), supplied_missing(session, plan), drawn_route(run) == 'motion'
    out, pictures, first = [], 0.0, None
    for gap in plan['gaps']:
        shots = _counted_shots(gap)
        secs = lambda sh: (sh['end_frame'] - sh['start_frame']) / fps
        planned = sum(secs(sh) for sh in shots if route_of(sh) == 'still')
        try:
            still, _moving, unsplit = still_and_moving(agreed[gap['gap_id']], list(agreed[gap['gap_id']].get('routes') or []))
        except (KeyError, IndexError, TypeError, ValueError):
            still = unsplit = None   # no treatment entry for this gap, or one that cannot be read: nothing to compare
        if still is not None and 'footage' not in (agreed[gap['gap_id']].get('routes') or []) and planned > still + unsplit + 0.5:   # a frame of the footage shown in the film is a still in the plan (_ways_departed allows it)
            out.append({'kind': 'still_more_than_agreed', 'gap_id': gap['gap_id'],
                        'message': f"gap {gap['gap_id']}: the plan has {round(planned, 1):g} s of still pictures; {round(still, 1):g} s were accepted in the treatment. "
                                   'Make some of them moving shots, or record the treatment again.'})
        for sh in shots:
            if sh['visual_type'] == 'image':
                pictures, first = pictures + secs(sh), first or gap['gap_id']
            if words_spoken and sh.get('graphic_kind') in ('title', 'text'):
                out.append({'kind': 'text_card', 'shot_id': sh['id'],
                            'message': f"shot {sh['id']} is a card of words. In a documentary or an explaining film the words are said by the voice and the picture shows the thing: "
                                       'plan a picture here, or say why the card is needed.'})
            for name in stand_ins.get(sh['id']) or []:
                out.append({'kind': 'stand_in_real', 'shot_id': sh['id'],
                            'message': f"shot {sh['id']} shows {name}, a real person, as a stand-in: the picture is made from the description, not from their own photo. "
                                       'To show them as they are, the operator gives a photo and records their permission.'})
            for eid, name in to_give.get(sh['id']) or []:   # release 3, C3: found at the plan, not hours later at the build; a warning, never a refusal
                out.append({'kind': 'supplied_missing', 'shot_id': sh['id'],
                            'message': f"shot {sh['id']} shows {name} ({eid}) and no file of it has been given. Ask the operator for it now, with the plan: the file goes in the run "
                                       'folder under in/brand/ (`vw brand fetch` saves the logo files the client directory holds there), then '
                                       f"`vw visuals supply --element {eid} --file in/brand/<name>`. If the film goes on without it, say so in the shot's warning_answers."})
            if labelled and text_no_labels(sh):   # release 3, C4: named with the plan; the gate before the first brief stays (motion_brief)
                out.append({'kind': 'labels_missing', 'shot_id': sh['id'],
                            'message': f"shot {sh['id']} is a drawn graphic that carries text and lists no labels. Add scene_motion: {{labels: [every text the viewer reads, word for word, "
                                       'never the corner note], cues: [{selector: "#id", word or at_s}]} to it now, in the plan; if its only text is the corner note or a logo '
                                       'picture, set carries_text to false on it. `vw motion brief` is refused for every drawn shot until then.'})
            if sh['visual_type'] == 'drawn' and not film.camera_allowed(run, sh.get('camera_flow')):   # design/221 section 10 point 4: a warning, never a refusal
                out.append({'kind': 'camera_flow', 'shot_id': sh['id'],
                            'message': f"shot {sh['id']}: the camera flow {film.CAMERA[sh.get('camera_flow') or 'fixed'][0]} is not one the film's motion style allows "
                                       f"({', '.join(film.styles()[film.motion(run)]['camera'])}). Choose one of those, or fixed when in doubt."})
            move = camera_words(sh) if sh['visual_type'] == 'drawn' else ''   # fix set M1: settled with the plan, not asked in the middle of the builds
            if move:
                out.append({'kind': 'camera_words', 'shot_id': sh['id'],
                            'message': f"shot {sh['id']}: its words ask for a camera move (\"{move}\") and its camera flow is {film.CAMERA[sh.get('camera_flow') or 'fixed'][0]}. "
                                       'Settle it now, in the plan, not at the build: name the flow the shot needs (camera_flow), or take the move out of its words; '
                                       "when the choice is the operator's, ask it with the plan."})
            big = next((c['what'] for c in sh.get('changes') or [] if LARGE_CHANGE.search(c.get('what') or '')), '') if sh.get('end_state_exact') else ''   # fix set M4
            if big:
                out.append({'kind': 'end_change_large', 'shot_id': sh['id'],
                            'message': f"shot {sh['id']} ends on an exact end picture, which is an edit inside one region of its start, a third of the frame at most; its change "
                                       f'reads as larger ("{big}"). Plan it start-only (end_state_exact false), so the motion carries the change, or as a new picture of its own.'})
        for sh, before, between in apart(shots):   # fix set M2: a drawing continues another only when they are next to each other in the film
            out.append({'kind': 'continues_apart', 'shot_id': sh['id'],
                        'message': f"shot {sh['id']} does not continue the drawing {before['id']}: {', '.join(b['id'] for b in between)} {'is' if len(between) == 1 else 'are'} between "
                                   f"them in the film. A drawing opens where another ends only when the two are next to each other, so {sh['id']} is built as its own drawing. "
                                   'Put them next to each other to continue, or name the return (return_of) when the same diagram comes back.'})
    alike = alike_people(plan) if is_kept(session, run) else []   # the reference round of such a film refuses them, one pair at a time: here they are named together, before it
    if alike:
        out.append({'kind': 'people_alike',
                    'message': 'These people read alike in their descriptions (age, build, hair, face): ' + '; '.join(f'{a} and {b}' for a, b in alike) + '. The reference round refuses people who cannot be told apart. '
                               "Write each person's age, build, hair and face in their `description`, so that every pair differs in at least one."})
    length, limit = film_seconds(session, outputs), float(settings().VISUALS_STILL_SHARE)
    if length and first and pictures / length > limit + 1e-9:   # the treatment's own warning and sentence, worked out again from the plan
        out.append({'kind': 'stills_many', 'gap_id': first,
                    'message': f"Still pictures are {math.ceil(pictures / length * 1000 - 1e-6) / 10:g} % of the film: above {limit * 100:g} %. Make some of them moving shots."})
    return answer_warnings(plan, out)


VERTICAL_VIDEO = ('{shots}: AI video is not built for a vertical film yet: the video AI makes its takes in the horizontal shape only. '
                  'Make {these} a still, a drawn graphic or footage in the plan, then check the plan again.')


NO_CLIP_SHOT = ('{shot}: this film has no clip (no camera footage of its own and no library clip in its first cut), so a footage shot can be filled by nothing. '
                'Make it AI video, a still or a drawn graphic.')
NO_CLIP_SCENE = 'scene {scene}: `continues_footage` is set, but this film has no clip beside any gap. Take it out and give the scene its own first wide shot.'
NO_CLIP_ROUTE = 'gap {gap}: the route "footage" cannot be used: this film has no clip (no camera footage of its own and no library clip in its first cut). Use video, still, graphic_sequence or drawn.'
OVER_LIMIT = ("The estimate for this film's pictures and AI video, with the takes likely to be made again, is about \u20b9{estimate}; the film's cost limit is \u20b9{cap}. "
              'Tell the operator now: the owner lifts the limit (`vw visuals cap`), or the treatment uses fewer seconds of AI video. A paid step is refused once the limit is reached.')


def no_real_clip(session):
    """SK, 23 Nov 2026: True for a film with no clip at all: none of its own (nothing was measured at prepare) and no library clip in its first
    cut. False for every other film, and for a session not prepared yet (not known, so nothing changes)."""
    return 'footage_measured' in (session or {}) and not (session['footage_measured'] or {}).get('per_clip') and not session.get('first_cut_events')


def no_clip_routes(session, gap_id, routes_):
    """V3: the treatment's refusal of the route "footage" on a film with no clip; '' when it may stand."""
    return NO_CLIP_ROUTE.format(gap=gap_id) if no_real_clip(session) and 'footage' in (routes_ or []) else ''


def no_clip_plan(session, plan):
    """V3, V9: on a film with no clip, the plan's footage shots and the scenes that say they continue the footage, each refused in one sentence."""
    if not no_real_clip(session):
        return []
    scenes = [sc for gap in plan['gaps'] for sc in all_scenes(gap)]
    return ([NO_CLIP_SHOT.format(shot=sh['id']) for sc in scenes for sh in sc['shots'] if sh.get('visual_type') == 'footage']
            + [NO_CLIP_SCENE.format(scene=sc['id']) for sc in scenes if sc.get('continues_footage')])


def footage_frame_needed(session, cited, frames_ok):
    """F13: a thing whose fact or size cites the footage waits for an approved footage frame; never on a film with no clip, where none can exist."""
    return bool(cited) and not frames_ok and not no_real_clip(session)


def over_limit(estimate_inr, allowance_inr, cap_inr):
    """V1 (SK, 23 Nov 2026): said at the treatment, for every film, when the estimate with the takes likely to be made again is above the film's
    cost limit: a warning, never a refusal (the refusal stays before a paid call)."""
    total = float(estimate_inr) + float(allowance_inr)
    return [{'kind': 'over_limit', 'message': OVER_LIMIT.format(estimate=f'{total:,.0f}', cap=f'{float(cap_inr):,.0f}')}] if total > float(cap_inr) + 1e-9 else []


def vertical_video(run, plan):
    """Release 1, C5 (SK, 20 Nov 2026): vertical AI video is not built. The AI video shots of a film whose shape, or whose AI video shape, is
    vertical, refused in one plain sentence (a refusal of the plan, not a warning); [] for a film with no AI video shot, a horizontal film,
    a film from before the shape was recorded, or a shape not recorded yet."""
    if film.older(run) or '9:16' not in (film.frame(run), film.frame(run, video=True)):
        return []
    ids = [sh['id'] for gap in plan['gaps'] for sc in all_scenes(gap) for sh in sc['shots'] if route_of(sh) == 'video']
    return [VERTICAL_VIDEO.format(shots=', '.join(ids), these='this shot' if len(ids) == 1 else 'each of these shots')] if ids else []


def supplied_plan(run, plan, pictures):
    """SK, 23 Nov 2026 (no footage, release 3, F15): on a film with no camera footage every picture the operator gave (`pictures`, the tool's list
    of the run folder's in/) has its place in the plan (`supplied` on a still shot) or its reason in `images_not_used`, and a shot names only a
    picture that is there. The refusals, one sentence each; [] for a film with footage, and where no list was sent."""
    if pictures is None or core.footage_of(run) != 'none':
        return []
    have = {str(p).lower() for p in pictures}
    placed = {str(sh['supplied']).lower(): sh for gap in plan['gaps'] for scene in all_scenes(gap) for sh in scene['shots'] if sh.get('supplied')}
    listed = {str(x['file']).lower() for x in plan.get('images_not_used') or []}
    out = [f"shot {sh['id']}: `supplied` names {sh['supplied']}, which is not among the operator's pictures in in/ ({', '.join(pictures) or 'none'})." for name, sh in placed.items() if name not in have]
    left = [p for p in pictures if str(p).lower() not in placed and str(p).lower() not in listed]
    if left:
        out.append(f"The operator gave pictures this plan neither places nor lists: {', '.join(left)}. Give each its place (`supplied` on a still shot) or list it in `images_not_used` with the "
                   'reason: the operator sees both when they approve the plan.')
    return out


def repeat_allowed(row):
    """Release 3 (F18): the operator's own picture may be shown in more than one shot; the plan warns where the two showings are close or alike."""
    return row.get('kind') == 'supplied'


MAX_PIXELS = 24_000_000


def check(store, run, outputs, document, pictures=None):
    session = session_of(store, run, outputs)
    ensure_timing(store, run, session)   # design/89 A1, finding 3
    try:
        document = _with_direction(session, document)   # design/207: placed by the server, as the proposal places it
        plan, warnings = validate_plan(document, session['source']['gaps'], _fps(session), film_frames(outputs), session.get('frozen_limit') or FROZEN_SHARE, bool(media_clips(outputs)), drawn_in_run(run),
                                       drawn_route(run) == 'motion', not film.older(run))   # design/89 B4; design/124-b item 13; design/130 §12; design/139 R3
    except (ValueError, KeyError, TypeError) as exc:
        return {'status': 'rejected', 'error': str(exc), 'errors': list(getattr(exc, 'errors', None) or [str(exc)])}   # design/148 A1: every item's first failure, as a list too
    upright = vertical_video(run, plan) + no_clip_plan(session, plan) + supplied_plan(run, plan, pictures)   # release 1, C5: an AI video shot on a vertical film is refused here, at the plan, in one plain sentence; 23 Nov 2026: a footage shot on a film with no clip
    if upright:
        return {'status': 'rejected', 'error': '\n'.join(upright), 'errors': upright}
    departed = _ways_departed(session, plan) if session.get('treatment') else []   # design/207: what only the proposal refused before, so a clean check means the proposal is taken
    if departed:
        return {'status': 'rejected', 'error': '\n'.join(departed), 'errors': departed}
    r = routes(plan, _fps(session) or 25)
    planned = plan_estimate(run, r)   # design/134 12: r['video_take_seconds']   # design/65 B7: the cost against the cap, before anything is paid
    alike = look_alike_placed(store, session)   # design/89 H6: the pictures already placed that look alike
    warnings += answer_warnings(plan, [{'kind': 'look_alike', 'shot_id': p['b'], 'message': f"{p['a']} ({p['a_at_s']} s) and {p['b']} ({p['b_at_s']} s) look alike: reimagine one (another angle, distance or moment)"} for p in alike])   # design/124 Change 7
    warnings += carried_warnings(session, run, plan, outputs)   # design/207
    warnings += palette_due(session, plan)   # design/218 B
    split = {}
    for gap in plan['gaps']:   # design/97 G3: a gap with choices is split by its recommended choice
        try:
            split[gap['gap_id']] = split_of([sh for sc in chosen_scenes(gap, {'choice_id': gap.get('recommended_choice')} if gap.get('choices') else None) for sh in sc['shots']],
                                            float(Fraction(str(_fps(session) or 25))))
        except ValueError:
            continue
    sets = set_estimate(run, session, plan)   # design/209: the reference sets, beside the shots
    return {'status': 'valid', 'warnings': warnings, 'routes': r, 'split': split, 'plan_digest': digest(plan),
            'budget': {'planned_inr': planned, 'cap_inr': cap_of(session), 'sets': sets['sets'], 'sets_inr': sets['inr']}, 'look_alike': alike}   # design/45 10.2


def propose(conn, store, user, run, outputs, document, answers='', pictures=None):
    session = session_of(store, run, outputs)
    ensure_timing(store, run, session)   # saved with the proposal
    plan, warnings = guarded(lambda: validate_plan(_with_direction(session, document), session['source']['gaps'], _fps(session), film_frames(outputs), session.get('frozen_limit') or FROZEN_SHARE, bool(media_clips(outputs)), drawn_in_run(run),
                                                   drawn_route(run) == 'motion', not film.older(run)))   # design/130 §12; design/139 R3; design/207: the Direction is placed by the server (the older refusal "starts from the treatment's Direction, word for word" is retired)
    need(not vertical_video(run, plan), '\n'.join(vertical_video(run, plan)))   # release 1, C5: as the check refuses it
    need(not supplied_plan(run, plan, pictures), '\n'.join(supplied_plan(run, plan, pictures)))   # release 3 (F15)
    need(not no_clip_plan(session, plan), '\n'.join(no_clip_plan(session, plan)))   # SK, 23 Nov 2026 (V3, V9): as the check refuses it
    need(session.get('treatment'), 'Record the treatment first (`vw visuals treatment`).')   # design/65 B6
    departed = _ways_departed(session, plan)   # a route that departs from the recorded treatment needs a new treatment, with the reason
    need(not departed, '\n'.join(departed))
    warnings = warnings + carried_warnings(session, run, plan, outputs)   # design/207: the same as the check returns
    warnings = warnings + palette_due(session, plan)   # design/218 B
    new = guarded(lambda: new_version(store, run, session, plan, user, warnings, answers))
    version, identity = new['version'], new['plan_digest']
    save_session(store, run, session)
    from . import runlog
    for e in plan_log(run, plan, version):   # design/145 L3
        runlog.write(conn, e)
    said = []
    for q in new['quiet']:   # release 3, C1 and C2: a change that asked nothing is a line of the log: the operator's decision when their answer carried it, else the assistant's change
        mine = q['why'] == 'answer'
        entry = (_short_text(f"the plan change that follows the operator's answer on {q['item']} (\"{q['question']}\"): " + '; '.join(q['changes']), 3800) + ': accepted with that answer, no second question'
                 if mine else f"{', '.join(q['shots'])}: {QUIET[q['why']]}")
        runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f"gap {q['gap']}", 'rule': f'visual plan v{version}', 'entry': entry,
                            'by_kind': 'operator' if mine else 'assistant', 'by_name': (user.get('name') or '') if mine else '', 'quote': q['answer'] if mine else '', 'request_id': None})
        said.append(f"gap {q['gap']}: " + (f"accepted with the operator's answer on {q['item']}" if mine else entry))
    if new['kept_recorded']:   # design/191 A5
        runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': 'gap ' + ', '.join(new['kept_recorded']), 'rule': f'visual plan v{version}',
                            'entry': 'already recorded into the film and its own shots unchanged: the acceptance is kept through a change of the shared part, without asking again',
                            'by_kind': 'server', 'by_name': '', 'quote': '', 'request_id': None})
    shared = sorted(session.get('shared_pending') or {})
    return {'version': version, 'plan_digest': identity, 'warnings': warnings, 'routes': routes(plan, _fps(session) or 25), 'gaps': [g['gap_id'] for g in plan['gaps']],
            **({'kept_without_asking': said} if said else {}),
            **({'asked_again': [f"gap {g}: a label in words the plan does not hold ({'; '.join(w)}): new wording on screen is the operator's to accept (`vw visuals next`)" for g, w in new['asked'].items()]
                                + [f"gap {g}: its change is larger than what the question on {answers} names: the operator is asked for it (`vw visuals next`)" for g in new['asked_beyond']]}
               if new['asked'] or new['asked_beyond'] else {}),
            **({'shared_change': f"The part every gap shares changed. {len(shared)} gap(s) the operator had accepted keep their own shots ({', '.join(shared)}): the operator is asked ONE question for all of them "
                                 '(`vw visuals next`). Do not ask them gap by gap.'} if shared else {})}


QUIET = {'labels': "labels added in the plan's own words: no decision; the acceptance is kept",   # release 3, C1 and C2: a change that asks the operator nothing, as the log says it
         'no_text': 'carries_text set to false (its only text is the corner note or a logo): no decision; the acceptance is kept'}
LOGO = re.compile(r'\b(?:logo|wordmark|brand\s*mark)\b', re.I)   # an element named as a logo: a picture the operator supplies


def _answered_for(session, item):
    """Release 3, C2: the operator's answer to the question on this item that no plan change has used yet; refused when there is none."""
    record = next((r for r in reversed(session.get('answered') or []) if r.get('item') == item and r.get('answer') and not r.get('plan_version')), None)
    need(record, f"No answered question on {item} waits for its plan change: `--answers` names the item of a question the operator answered (`vw visuals ask`, answered in the chat) "
                 'and is used once. Propose the plan without it; the operator is then asked for the gaps that changed.')
    return record


def _named(session, plan, old, gap, item):
    """Release 3, C2: what the answered question names in this gap: (its shots, its thing). A question on a shot names that shot; on a thing, the
    thing and the shots that show it in the plan in force (the critic's point 3: never a shot the change gives it); on a picture, the shot or the
    thing the picture is of."""
    ref = (session.get('references') or {}).get(item) or {}
    item = ref.get('shot_id') or ref.get('element_id') or item
    shots = [s for sc in all_scenes(old) for s in sc['shots']]
    if any(e['id'] == item for e in plan.get('elements') or []):
        return {s['id'] for s in shots if item in (s.get('element_ids') or [])}, item
    return {s['id'] for s in shots if s['id'] == item}, None


def _own_without(plan, gap, shots, element):
    """The gap's own content (as `gap_own_digest`) without these shots and this thing. With a thing (the critic's point 3 on release 3), its
    shots stay but for the thing in their `element_ids`: a change to their type, timing, route or words is still a change."""
    g = note_free_gap(gap)
    strip = lambda scenes: [{**sc, 'shots': [{**s, 'element_ids': [e for e in s.get('element_ids') or [] if e != element]} if element and s['id'] in shots else s
                                             for s in sc['shots'] if element or s['id'] not in shots]} for sc in scenes]
    g = {**g, **({'scenes': strip(g['scenes'])} if g.get('scenes') else {}), **({'choices': [{**c, 'scenes': strip(c['scenes'])} for c in g['choices']]} if g.get('choices') else {})}
    used = {eid for sc in all_scenes(g) for s in sc['shots'] for eid in s['element_ids']} - {element}
    return digest({'gap': g, 'elements': note_free_elements([e for e in plan['elements'] if e['id'] in used])})


def _shot_labels(shot):
    return [l for l in (shot.get('scene_motion') or {}).get('labels') or [] if _flat(l) != _flat(corner_note(shot.get('drawing_spec')))]


def _leaf_words(x):
    """Every word of every text inside a value of the plan, lower case."""
    if isinstance(x, dict):
        return {w for k, v in x.items() if k != 'scene_motion' for w in _leaf_words(v)}
    if isinstance(x, list):
        return {w for v in x for w in _leaf_words(v)}
    return set(re.findall(r'\w+', x.casefold())) if isinstance(x, str) else set()


def new_labels(prev, old, gap):
    """Release 3, C1: (the drawn shots of this gap that got a label in this version, the labels among them with a word that is neither in the
    shot's text in the plan in force nor in the name of a thing it shows, as 'shot: "label"'). Case and spacing do not count."""
    before = {s['id']: s for sc in all_scenes(old) for s in sc['shots']}
    names = {e['id']: e.get('name') or '' for e in prev.get('elements') or []}
    added, strange = [], []
    for s in (s for sc in all_scenes(gap) for s in sc['shots'] if s.get('visual_type') == 'drawn' and s['id'] in before):
        had = {_flat(l) for l in _shot_labels(before[s['id']])}
        fresh = [l for l in _shot_labels(s) if _flat(l) not in had]
        known = _leaf_words(before[s['id']]) | _leaf_words([names.get(e, '') for e in before[s['id']].get('element_ids') or []])
        added += [s['id']] if fresh else []
        strange += [f'{s["id"]}: "{l}"' for l in fresh if not set(re.findall(r'\w+', l.casefold())) <= known]
    return list(dict.fromkeys(added)), strange


def no_text_now(plan, old, gap):
    """Release 3, C1: the drawn shots of this gap whose `carries_text` went from true to false in this version and whose only text is the server's
    corner note or a logo picture: they list no label of their own and have a corner note or a thing named as a logo. The server cannot see the
    drawing: this is what the plan says."""
    before = {s['id']: s for sc in all_scenes(old) for s in sc['shots']}
    names = {e['id']: str(e.get('name') or '') for e in plan.get('elements') or []}
    return [s['id'] for sc in all_scenes(gap) for s in sc['shots']
            if s.get('visual_type') == 'drawn' and not s.get('carries_text') and (before.get(s['id']) or {}).get('carries_text') and not _shot_labels(s)
            and (corner_note(s.get('drawing_spec')) or any(LOGO.search(names.get(e, '')) for e in s.get('element_ids') or []))]


def _with_text(gap, shots):
    """The gap with `carries_text` true again on these shots: what it was before they were marked as carrying no text."""
    mark = lambda scenes: [{**sc, 'shots': [{**s, 'carries_text': True} if s['id'] in shots else s for s in sc['shots']]} for sc in scenes]
    return {**gap, **({'scenes': mark(gap['scenes'])} if gap.get('scenes') else {}), **({'choices': [{**c, 'scenes': mark(c['scenes'])} for c in gap['choices']]} if gap.get('choices') else {})}


def new_version(store, run, session, plan, user, warnings, answers=''):
    """A validated plan stored as the next version, and every approval carried into it (design/191). The session is changed, not saved.
    answers (release 3, C2): the item of a question the operator answered; a change inside what it names is accepted with that answer."""
    answer = _answered_for(session, answers) if answers else None
    try:
        prev = current_plan(store, session) if session.get('current') else None   # the plan in force, for what this version changes
    except (Problem, StopIteration, KeyError, TypeError, ValueError):
        prev = None   # it cannot be read: carried and asked as before this release
    version = len(session['versions']) + 1
    record = {'run_id': str(run['id']), 'version': version, 'source_plan_digest': session['source']['plan_digest'], 'document': plan,
              'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    pk = save_json(store, key(run, f'plan-v{version}.json'), record)
    identity = digest(plan)
    session['versions'].append({'version': version, 'file': pk, 'plan_digest': identity, 'warnings': warnings, 'shots': shot_prints(plan)})   # issue 17 (R2)
    session['current'] = identity
    was = set(session.get('was_accepted') or {})
    kept, quiet, asked = _carry_acceptances(session, plan, version, prev, answer)
    if answer:
        answer['plan_version'] = version   # used once
    return {'version': version, 'plan_digest': identity, 'kept_recorded': kept, 'quiet': quiet, 'asked': asked,
            'asked_beyond': sorted(g for g in set(session.get('was_accepted') or {}) - was if g not in asked) if answer else []}


def _carry_acceptances(session, plan, version, prev=None, record=None):
    """design/191: what a new plan version does to the operator's approvals. A gap's acceptance stands when nothing it covers changed. When only the
    part every gap shares changed (the foundation, the sequence rules) and the gap's own shots are as accepted, the acceptance waits behind ONE
    question for all such gaps (`shared_pending`): until it is answered the gap counts as not accepted. When the gap's own content changed it is
    asked again by itself, and the version it was accepted in is kept (`was_accepted`) so the question can say what changed. An acceptance from
    before this release (no `own` fingerprint) is asked again on any change, as before.
    Returns the gaps kept without asking: already recorded into the film, own content unchanged (section 11, A5); and (release 3, C1 and C2,
    against `prev`, the plan in force) the changes that ask nothing (`quiet`) and the gaps asked again for a label in new words (`asked`)."""
    gaps = {g['gap_id']: g for g in plan['gaps']}
    shared = shared_digest(plan)
    for gid, cs in list(session['choice_selections'].items()):   # section 11, B1: a chosen way the gap no longer offers is not a choice any more; it is asked again
        if gid not in gaps or not any(c['id'] == (cs or {}).get('choice_id') for c in gaps[gid].get('choices') or []):
            session['choice_selections'].pop(gid)
    pending, was, kept = session.setdefault('shared_pending', {}), session.setdefault('was_accepted', {}), []
    before = {**pending, **session['accepted']}
    session['accepted'].clear()
    pending.clear()
    quiet, asked, olds = [], {}, {g['gap_id']: g for g in (prev or {}).get('gaps') or []}
    for gid, acc in before.items():
        gap = gaps.get(gid)
        if not gap:
            continue
        full, own, old, why = gap_digest(plan, gap), gap_own_digest(plan, gap), olds.get(gid), None
        added, strange = new_labels(prev, old, gap) if old else ([], [])
        if strange:   # release 3, C1: a label in words the plan does not hold is new wording on screen: the gap is asked again, and its card names the words
            asked[gid] = strange
            if acc.get('version'):
                was[gid] = acc['version']
            continue
        if old and acc['digest'] != full and acc.get('own') and acc['own'] != own:   # release 3: its own content changed; is it a change that asks nothing?
            shots, thing = _named(session, plan, old, gap, record['item']) if record else (set(), None)
            bare = no_text_now(plan, old, gap)
            if shots and _own_without(prev, old, shots, thing) == _own_without(plan, gap, shots, thing):   # C2: inside what the answered question names
                why = {'gap': gid, 'why': 'answer', 'shots': sorted(shots), 'item': record['item'], 'question': record.get('question') or '', 'answer': record['answer'],
                       'changes': _diff(note_free_gap(old), note_free_gap(gap), '') + _diff(note_free_elements([e for e in prev['elements'] if e['id'] == thing]),
                                                                                                 note_free_elements([e for e in plan['elements'] if e['id'] == thing]), 'Elements')}
                acc = {**acc, 'own': own, 'quote': record['answer'], 'by': record.get('answered_by') or acc.get('by'), 'answer_to': record['item']}
            elif bare and gap_own_digest(plan, _with_text(gap, bare)) == acc['own']:   # C1: only `carries_text`, on shots whose only text is the corner note or a logo
                why, acc = {'gap': gid, 'why': 'no_text', 'shots': bare}, {**acc, 'own': own}
            if why and acc.get('shared') == shared:   # the part every gap shares is as accepted: the acceptance stands under this version (else the one shared question, below)
                _restamp_bindings(session, gap, acc['digest'], full)
                acc = {**acc, 'digest': full, 'version': version, 'kept': why['why']}
                quiet.append(why)
        if acc['digest'] == full:
            session['accepted'][gid] = acc
            if added and not why:
                quiet.append({'gap': gid, 'why': 'labels', 'shots': added})
        elif acc.get('own') and acc['own'] == own:
            if gid in session['recorded_gaps']:
                session['accepted'][gid] = {**acc, 'digest': full, 'shared': shared, 'version': version, 'kept': 'recorded before; only the shared part changed'}
                _restamp_bindings(session, gap, acc['digest'], full)
                kept.append(gid)
            else:
                pending[gid] = acc
        elif acc.get('version'):
            was[gid] = acc['version']
    for gid in [g for g in was if g not in gaps or g in session['accepted'] or g in pending]:
        was.pop(gid)
    for gid, rv in list((session.get('revisions') or {}).items()):   # design/76: a revision is answered once the gap is proposed changed; A2: its own content, not the shared part
        gap = gaps.get(gid)
        if not gap or (rv['own'] != gap_own_digest(plan, gap) if rv.get('own') else rv.get('digest') != gap_digest(plan, gap)):
            session['revisions'].pop(gid)
    if not pending or (session.get('shared_revision') or {}).get('shared') != shared:   # the shared part was proposed changed: the operator's words on it are answered
        session.pop('shared_revision', None)
    return kept, quiet, asked


def _restamp_bindings(session, gap, old, new):
    """A shot's references stay bound when its gap is accepted again with its own shots unchanged (design/191, section 6)."""
    for scene in all_scenes(gap):
        for sh in scene['shots']:
            b = session['bindings'].get(sh['id'])
            if b and b.get('gap_digest') == old:
                b['gap_digest'] = new


def _version_now(session):
    return next((v['version'] for v in session['versions'] if v['plan_digest'] == session['current']), None)


def _plan_version(store, session, version, cache=None):
    cache = cache if cache is not None else {}
    if version not in cache:
        entry = next(v for v in session['versions'] if v['version'] == version)
        cache[version] = load_json(store, entry['file']['key'])['document']
    return cache[version]


def _diff(a, b, path):
    """What differs between two values of a plan, one line per changed leaf: where it is, what it was, what it is now. Rows that carry an id are
    matched by it (a rule, a shot, an element); other lists by their place."""
    if a == b:
        return []
    at = lambda k: f'{path} › {k}' if path else str(k)
    if isinstance(a, dict) and isinstance(b, dict):
        return [x for k in list(a) + [k for k in b if k not in a] for x in _diff(a.get(k), b.get(k), at(k))]
    if isinstance(a, list) and isinstance(b, list) and (a or b) and all(isinstance(x, dict) and x.get('id') for x in a + b):
        A, B = {x['id']: x for x in a}, {x['id']: x for x in b}
        return ([f'{at(i)}: removed' for i in A if i not in B] + [f'{at(i)}: added' for i in B if i not in A]
                + [x for i in A if i in B for x in _diff(A[i], B[i], at(i))])
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [x for i, (p, q) in enumerate(zip(a, b), 1) for x in _diff(p, q, at(i))]
    text = lambda v: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    if isinstance(a, list) and isinstance(b, list) and all(not isinstance(x, (dict, list)) for x in a + b):   # a list that grew or shrank: the items taken out and put in
        out = [f'{path}: removed "{_short_text(text(x), 90)}"' for x in a if x not in b] + [f'{path}: added "{_short_text(text(x), 90)}"' for x in b if x not in a]
        return out or [f'{path}: the order changed']
    A, B = ('' if a in (None, '', [], {}) else ' '.join(text(a).split())), ('' if b in (None, '', [], {}) else ' '.join(text(b).split()))
    first = next((i for i, (x, y) in enumerate(zip(A, B)) if x != y), min(len(A), len(B)))
    start = max(0, first - 30) if max(len(A), len(B)) > 90 else 0   # a long value: shown from just before where it differs, so the two sides are never the same words
    show = lambda v: 'nothing' if not v else '"' + ('…' if start else '') + _short_text(v[start:], 90) + '"'
    return [f'{path}: {show(A)} → {show(B)}']


def shared_change(store, session, plan, cache=None):
    """design/191: the one question's content: the gaps whose own shots are as accepted while the shared part changed, and every change of that part
    between the version they were accepted in and this one. None when no gap waits so. Raises when the earlier version cannot be read."""
    pending = session.get('shared_pending') or {}
    gids = [g['gap_id'] for g in plan['gaps'] if g['gap_id'] in pending]
    if not gids:
        return None
    versions, changes = sorted({pending[g]['version'] for g in gids}), []
    for v in versions:   # gaps accepted in different versions: every change since each of them, once
        old = _plan_version(store, session, v, cache)
        changes += (_diff(old.get('foundation') or {}, plan.get('foundation') or {}, 'The foundation')
                    + _diff(old.get('sequence_rules') or [], plan.get('sequence_rules') or [], 'The sequence rules'))
    return {'gaps': gids, 'changes': list(dict.fromkeys(changes)) or ['The shared rules changed.'], 'from_version': versions[0]}


def gap_changes(store, session, plan, gap, cache=None):
    """design/191: for a gap asked again because its own content changed, what changed since the version the operator accepted. [] when the gap was
    never accepted (or not since this release); one plain line when the earlier version cannot be read."""
    version = (session.get('was_accepted') or {}).get(gap['gap_id'])
    if not version:
        return []
    try:
        old = _plan_version(store, session, version, cache)
        before = next(g for g in old['gaps'] if g['gap_id'] == gap['gap_id'])
        used = {eid for scene in all_scenes(gap) + all_scenes(before) for sh in scene['shots'] for eid in sh['element_ids']}
        texts = lambda g_: [{'id': sh['id'], 'text on screen': _shot_labels(sh)} for scene in all_scenes(g_) for sh in scene['shots'] if sh.get('visual_type') == 'drawn']   # release 3, C1: a label is a note of the shot, so it is listed here
        return (_diff(note_free_gap(before), note_free_gap(gap), '') + _diff(texts(before), texts(gap), 'Shots')
                + _diff(note_free_elements([e for e in old['elements'] if e['id'] in used]), note_free_elements([e for e in plan['elements'] if e['id'] in used]), 'Elements')
                + (['The film\'s shared rules changed as well.'] if shared_digest(old) != shared_digest(plan) else [])) or ['It differs from the version you accepted.']
    except (Problem, StopIteration, KeyError, TypeError, ValueError):
        return ['It changed since you accepted it; what changed could not be read.']


def status_shared(store, session, plan=None):
    """design/191: the shared change that waits for the operator's one answer, for the status and the visuals page: its gaps, the full list of
    changes, and the operator's words when they asked for a change. None when nothing waits."""
    if not session.get('shared_pending'):
        return None
    try:
        info = shared_change(store, session, plan or current_plan(store, session))
    except (Problem, StopIteration, KeyError, TypeError, ValueError):
        info = {'gaps': sorted(session['shared_pending']), 'changes': ['What changed could not be read: each gap is asked by itself.'], 'unread': True}
    rv = session.get('shared_revision')
    return info and {**info, **({'revise': {k: rv.get(k) for k in ('notes', 'quote', 'by', 'at')}} if rv else {})}


def _shared_note(store, session):
    """For the status and the page: the shared change that waits for the operator's one answer, when there is one."""
    info = status_shared(store, session)
    return {'shared_change': info} if info else {}


def accept_shared(conn, store, user, run, outputs, quote):
    """design/191: the operator's one yes to a change of the shared part: every gap whose own shots are as accepted is accepted under the current
    version, with the operator's words on each; their shots' references stay bound; one line in the run's log."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    try:
        info = shared_change(store, session, plan)
    except (Problem, StopIteration, KeyError, TypeError, ValueError):
        fail('The earlier plan version could not be read, so the change cannot be shown as one question: accept the gaps one by one.')
    need(info, 'No change of the shared rules waits for an answer.')
    words, version, shared = said(quote, 'accepted', user), _version_now(session), shared_digest(plan)
    for gid in info['gaps']:
        gap = next(g for g in plan['gaps'] if g['gap_id'] == gid)
        acc = session['shared_pending'].pop(gid)
        full = gap_digest(plan, gap)
        session['accepted'][gid] = {'digest': full, 'own': acc['own'], 'shared': shared, 'version': version, 'choice_id': (session['choice_selections'].get(gid) or {}).get('choice_id'),
                                    'quote': words, 'by': user['id'], 'with_shared_change': info['from_version']}
        _restamp_bindings(session, gap, acc['digest'], full)
        _feedback(session, run, user, kind='gap', ident=gid, owner=gid, step=None, verdict='pass', quote=words, notes='the change of the shared rules accepted; its own shots unchanged', prompt='', checklist=None, suggestion='', model='', inputs=())
    session.pop('shared_revision', None)
    save_session(store, run, session)
    from . import runlog
    runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': 'gap ' + ', '.join(info['gaps']), 'rule': f'visual plan v{version}',
                        'entry': _short_text(f"the change of the shared rules accepted once for {len(info['gaps'])} gaps whose own shots are unchanged ({', '.join(info['gaps'])}): " + '; '.join(info['changes']), 3900),
                        'by_kind': 'operator', 'by_name': user.get('name') or '', 'quote': words, 'request_id': None})
    return {'accepted': sorted(session['accepted']), 'with_shared_change': info['gaps'], 'changes': info['changes']}


def revise_shared(store, user, run, outputs, notes, quote):
    """design/191: the operator's words on a change of the shared part. They wait for the assistant; the gaps stay unaccepted; the question is asked
    again when the shared part is proposed changed."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    need(session.get('shared_pending'), 'No change of the shared rules waits for an answer.')
    words = str(notes or '').strip() or str(quote or '').strip()
    need(words, 'Say what to change in the shared rules.')
    session['shared_revision'] = {'notes': words, 'quote': str(quote or '').strip() or words, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'shared': shared_digest(plan)}
    save_session(store, run, session)
    return {'revise': True, 'notes': words, 'for_the_assistant': "The operator asks for this change in the plan's shared part (the foundation, the sequence rules): " + words
                                                                 + ' Change only that and propose the plan again; the gaps keep their shots.'}


# ---------- design/65 B7: the cap ----------

ROUTE_WORDS = {'footage': 'footage', 'still': 'still', 'video': 'AI video', 'graphic_sequence': 'graphic sequence', 'drawn': 'drawn'}


def plan_log(run, plan, version):
    """design/145 L3: the plan's own reasons in the run's log, one entry per gap: the choice taken, each shot's route and purpose."""
    out = []
    for gap in plan.get('gaps') or []:
        chosen = {'choice_id': gap.get('recommended_choice')} if gap.get('choices') else None
        shots = [sh for sc in chosen_scenes(gap, chosen) for sh in sc.get('shots') or []]
        said = '; '.join(f"{sh['id']} {ROUTE_WORDS.get(route_of(sh), route_of(sh))}: {_short_text(sh.get('purpose'))}" for sh in shots)
        head = f"choice {gap.get('recommended_choice')} of {len(gap['choices'])}" + (f" ({gap['choice_reason']})" if gap.get('choice_reason') else '') + '; ' if gap.get('choices') else ''
        out.append({'run_id': run['id'], 'stage': 'visuals', 'kind': 'choice', 'about': f"gap {gap.get('gap_id')}", 'rule': f'visual plan v{version}',
                    'entry': head + said, 'by_kind': 'assistant', 'by_name': '', 'quote': '', 'request_id': None})
    return out


def _short_text(text, n=160):
    t = ' '.join(str(text or '').split())
    return t if len(t) <= n else t[:n - 1] + '…'


GUIDE_KINDS = ('guide', 'edit', 'remake')   # design/223: a take made from a guide, and its versions (an edit, a remake): one family for the film
RERUN_SHARE = 0.3   # integration step E: about 1.3 takes for every AI video shot made (the consultant's two films: 1.25 to 1.4); replaced by this film's own figure in step F


def shot_second_price():
    """design/223: what one second of an AI video shot costs when it is accepted as it is: its first take (small) and its full-size video."""
    from . import corrections, video_generators
    return video_price(video_generators.GUIDE['resolution']) + video_price(corrections.VERSION_SIZE)


def rerun_allowance(video_seconds, pr):
    """What the takes that will have to be made again are likely to cost, shown beside the estimate, never hidden inside it."""
    return round(float(video_seconds) * RERUN_SHARE * pr['video_inr_per_s'], 2)


def prices():
    s = settings()
    return {'image_inr': float(s.VISUALS_PRICE_IMAGE_INR), 'video_inr_per_s': float(s.VISUALS_PRICE_VIDEO_INR_PER_S), 'video_360p_inr_per_s': float(s.VISUALS_PRICE_VIDEO_360P_INR_PER_S),
            'usd_inr': float(s.VISUALS_USD_INR)}


def video_price(resolution=None):
    """design/223 (SK, 22 Nov 2026: "the price by size"): what one second of AI video is counted at, by the size it is made at: a 360p second at its own
    figure, every other size (720p, and a take made before this, which names no size) at the 720p figure. (Until then: one price a second; design/35 row 329.)"""
    pr = prices()
    return pr.get('video_360p_inr_per_s', pr['video_inr_per_s']) if str(resolution or '') == '360p' else pr['video_inr_per_s']


IMAGE_JOB_PROVIDERS = ('openai', 'gemini-image')   # design/120: the two image job families
IMAGE_USD_PER_M = {'input': 8.0, 'output': 30.0}   # design/82 U2: OpenAI's GPT Image 2.5 rates, every input token at the image rate (the text share is a fraction of a rupee)


def provider_of(run):
    """design/120: the run's image model family, chosen once at creation. design/126 ST1: a run without one is refused, never given GPT Image."""
    p = (run or {}).get('image_provider')
    if not p:
        raise Problem(409, 'NO_PICTURE_AI', 'this film has no picture AI; it is chosen at `vw start --images`')
    return p


def image_price_inr(run, tier=None, provider=None):
    """design/126 TR2: one picture's price on this film, for every estimate: Nano Banana at its dollar price (4K when the tier is 4K; the
    configured size when no tier is given) times the rupee rate; GPT Image at the configured rupee figure. provider: a set's price is Gemini's on every film (design/151 hotfix)."""
    pr = prices()
    if (provider or provider_of(run)) == 'gemini':
        s = settings()
        usd = s.GEMINI_IMAGE_USD_4K if str(tier or s.GEMINI_IMAGE_SIZE).upper() == '4K' else s.GEMINI_IMAGE_USD
        return usd * pr.get('usd_inr', s.VISUALS_USD_INR)
    return pr['image_inr']


def image_cost_inr(cost, pr):
    """A finished image job's cost: Gemini flat per picture plus its inputs (design/120); OpenAI from its tokens; the flat image price when the job has none."""
    c = cost or {}
    if c.get('provider') == 'gemini':
        s = settings()
        usd = (s.GEMINI_IMAGE_USD_4K if str(c.get('tier') or '').upper() == '4K' else s.GEMINI_IMAGE_USD) * int(c.get('pictures') or 1) + int(c.get('inputs') or 0) * s.GEMINI_IMAGE_INPUT_USD   # design/151: a set's pictures
        return usd * pr.get('usd_inr', 88.0)
    if not c.get('output_tokens'):
        return pr['image_inr']
    return ((c.get('input_tokens') or 0) * IMAGE_USD_PER_M['input'] + c['output_tokens'] * IMAGE_USD_PER_M['output']) / 1e6 * pr.get('usd_inr', 88.0)


def visuals_spend(conn, run):
    """What this film's visuals have cost so far, at the configured prices: every image job and every take job that ran or is running."""
    rows = conn.execute("select provider, status, request, cost from vw2_jobs where run_id=%s and stage='visuals' and provider in ('openai', 'gemini-image', 'video', 'guide-still')", (run['id'],)).fetchall()   # design/120; integration step C: a guide's still is a paid picture too
    live = [r for r in rows if r['status'] not in ('failed', 'rejected', 'cancelled')]
    pr = prices()
    pics = [r for r in live if r['provider'] in IMAGE_JOB_PROVIDERS or r['provider'] == 'guide-still']
    images = len(pics)
    ref = lambda r: (r.get('request') or {}).get('reference') or {}
    fixes = sum(1 for r in pics if ref(r).get('fix_of') or str(ref(r).get('name') or '').endswith('-fix'))   # design/96 X3; an old fix by its name
    image_inr = sum(image_cost_inr(r.get('cost'), pr) for r in pics)
    takes = [(float((r.get('request') or {}).get('duration_seconds') or 0), (r.get('request') or {}).get('resolution')) for r in live if r['provider'] == 'video']
    seconds = float(sum(s for s, _ in takes))
    return {'images': images, 'fixes': fixes, 'take_seconds': seconds, 'spent_inr': round(image_inr + sum(s * video_price(size) for s, size in takes), 2), 'prices': pr}   # design/223: each take at the price of its size


def cap_of(session):
    return float(session.get('cap_inr') or settings().VISUALS_CAP_INR)   # no figure in the session: a film begun before design/207 keeps the older one


def cap_for(seconds):
    """design/207 (SK, 16 Nov 2026): a film's cost limit from its length: so much a minute of film, never under the lowest figure, to the rupee."""
    s = settings()
    return float(round(max(float(s.VISUALS_CAP_FLOOR_INR), float(s.VISUALS_CAP_INR_PER_MIN) * float(seconds or 0) / 60)))


def film_seconds(session, outputs):
    """The film's length in seconds, from the first cut's frames (as the still-share warning reads it); None when it is not known."""
    frames = film_frames(outputs)
    return frames / float(Fraction(str(session['source'].get('fps') or 25))) if frames else None


def set_cap(conn, store, user, run, outputs, inr, quote):
    """design/207: the owner sets another cost limit for this one film, with their words. A later `prepare` never changes it."""
    if (user or {}).get('role') != 'Admin':
        raise Problem(403, 'NOT_ALLOWED', "Only the owner can set the cost limit of a film, from their own sign-in. This sign-in is not the owner's: tell the operator to ask the owner.")
    quote = ' '.join(str(quote or '').split())
    need(quote, "The owner's words are needed to set the cost limit: `vw visuals cap --inr N --quote \"<the owner's words>\"`.")
    need(isinstance(inr, (int, float)) and not isinstance(inr, bool) and inr > 0, 'The cost limit is a number of rupees above zero.')
    session = session_of(store, run, outputs)
    was = cap_of(session)
    session.update(cap_inr=float(inr), cap_from='owner', cap_by=user['id'], cap_at=datetime.now(timezone.utc).isoformat(), cap_quote=quote)
    save_session(store, run, session)
    from . import corrections
    if corrections.go_waiting(conn, store, run, session):   # design/223 (E12): the videos that waited for the limit are sent, with nothing answered again
        save_session(store, run, session)
    from . import runlog
    runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': 'the cost limit', 'rule': 'visuals/cap',
                        'entry': f"the cost limit of this film's visuals set by the owner: ₹{was:,.0f} → ₹{float(inr):,.0f}", 'by_kind': 'operator', 'by_name': str(user.get('name') or ''),
                        'quote': quote, 'request_id': None})
    return {'cap_inr': float(inr), 'was_inr': was, 'cap_from': 'owner', 'log': f'cost limit ₹{was:,.0f} → ₹{float(inr):,.0f}'}


def plan_estimate(run, r):
    """What a plan's pictures and takes are likely to cost, from its counted routes: the one sum the check, the budget and the plan page show."""
    return round(r['images_estimated'] * image_price_inr(run) + r.get('video_take_seconds', 0) * shot_second_price(), 2)


def set_estimate(run, session, plan):
    """design/209 (SK, 16 Nov 2026): the reference sets a plan may need and what they cost at most, said beside the plan's estimate: one set for
    each thing the round makes one for (not a graphic, an animal or the style), less the things the round has left out or kept from a footage
    picture. None on a film whose references are not made as sets."""
    if not is_kept(session, run):
        return {'sets': 0, 'inr': 0.0}
    rows = (session.get('round') or {}).get('elements') or {}
    # ponytail: "up to": before the round nobody knows which things have a footage picture of their own; a set already made is still counted
    n = len([e for e in plan.get('elements') or [] if e['id'] != STYLE and e.get('kind') not in ('graphic', 'animal', 'style')
             and not (rows.get(e['id']) or {}).get('ignored') and not (rows.get(e['id']) or {}).get('from_footage')])
    return {'sets': n, 'inr': round(n * image_price_inr(run, provider='gemini') * SET_MAX, 2)}


def check_cap(conn, run, session, estimate_inr, what):
    """Before any paid call: refuse when the spend so far plus this call would pass the film's cap."""
    spent, cap = visuals_spend(conn, run)['spent_inr'], cap_of(session)
    if spent + float(estimate_inr) > cap + 1e-9:
        how = {'length': "The limit follows the film's length. ", 'owner': 'The owner set this limit. '}.get(session.get('cap_from'), 'This film keeps the older limit. ')
        raise Problem(409, 'VISUALS_CAP', f"₹{spent:,.0f} spent of ₹{cap:,.0f} on this film's visuals; {what} needs about ₹{float(estimate_inr):,.0f}. "
                                          "Stop and tell the operator the spend. " + how + "Only the owner can set another figure for this film, from their own sign-in (`vw visuals cap`): tell the operator to ask the owner.",
                      spent_inr=spent, cap_inr=cap, estimate_inr=float(estimate_inr))


def budget(conn, store, run, outputs):
    """Spend, cap and what the current plan still needs, in INR."""
    session = session_of(store, run, outputs)
    sp = visuals_spend(conn, run)
    planned = {'images': 0, 'video_seconds': 0.0, 'inr': 0.0}
    if session.get('current'):
        r = routes(current_plan(store, session), _fps(session) or 25)
        planned = {'images': r['images_estimated'], 'video_seconds': r['seconds']['video'], 'inr': plan_estimate(run, r)}
    cap = cap_of(session)
    return {**sp, 'cap_inr': cap, 'left_inr': round(cap - sp['spent_inr'], 2), 'planned': planned}


# ---------- design/65 B6: the treatment as a record ----------

TREATMENT_GRAPHIC_ROUTES = ('drawn', 'graphic_sequence')   # design/126 TR1: a still's kind (photo or diagram) is not in the treatment, so a still breaks a run


OLD_PLAN_RULE_RUNS = {'VW-12'}   # design/126 TR1b: these runs keep the graphics run without drawn shots (design/35 old ways: until VW-12 closes)


def drawn_in_run(run):
    return (run or {}).get('code') not in OLD_PLAN_RULE_RUNS


def treatment_length_warnings(entry):
    """design/126 TR3: the plan's still_long (design/89 B1) warning on the treatment, from each shot's route and seconds (design/139 R9: the AI-run warning is gone)."""
    out = []
    for i, sh in enumerate([s for s in entry.get('shots') or [] if isinstance(s, dict)], 1):
        secs = sh.get('seconds')
        if sh.get('route') == 'still' and isinstance(secs, (int, float)) and secs > STILL_MOVING_MAX_S + 0.04:
            out.append({'gap_id': entry['gap_id'], 'shot_id': str(sh.get('id') or f'shot {i}'), 'kind': 'still_long',
                        'message': f"shot {sh.get('id') or i} is a still of {float(secs):.1f} s: at most {STILL_MOVING_MAX_S} s; fill the stretch with several different stills or a moving shot"})
    return out


REASONS = (('fits_why', 'why the picture fits the words'), ('way_why', 'why it is made this way'))
REASON_CHARS = 300


def reason_text(row, key):
    """A reason as the operator reads it: text, trimmed. Anything else (a list, a number, only spaces) is no reason."""
    v = row.get(key) if isinstance(row, dict) else None
    return v.strip() if isinstance(v, str) else ''


def still_and_moving(entry, routes):
    """design/202: a gap's seconds that stand still (the route `still`), that move (every other way) and that cannot be told apart. Counted shot
    by shot from each shot's own route and seconds; a shot without numeric seconds, and a gap of several ways with no shots, is `unsplit`:
    never guessed as still or as moving."""
    shots = [s for s in entry.get('shots') or [] if isinstance(s, dict)]
    if not shots:
        whole = float(entry['seconds'])
        return (whole, 0.0, 0.0) if routes == ['still'] else (0.0, whole, 0.0) if len(routes) == 1 else (0.0, 0.0, whole)
    still = moving = known = 0.0
    for s in shots:
        secs = s.get('seconds')
        if isinstance(secs, (int, float)) and not isinstance(secs, bool) and secs > 0:
            known += float(secs)
            if (s.get('route') or routes[0]) == 'still':
                still += float(secs)
            else:
                moving += float(secs)
    return still, moving, max(0.0, float(entry['seconds']) - known)


def reasons_missing(entry):
    """design/202 (SK, 15 Nov 2026): every shot of the treatment says why its picture fits the words and why it is made this way, one or two
    sentences each; a gap of one way with no shots says them on its line. A missing reason is named, shown to the operator as not given, and
    does not stop the draft (design/195: flags warn); a reason over the length is refused."""
    shots = [s for s in entry.get('shots') or [] if isinstance(s, dict)]
    rows = [(f"gap {entry['gap_id']}, shot {s.get('id') or n}", s) for n, s in enumerate(shots, 1)] or [(f"gap {entry['gap_id']}", entry)]
    out = []
    for where, row in rows:
        for k, _ in REASONS:
            need(len(reason_text(row, k)) <= REASON_CHARS, f'{where}: {k} is one or two sentences (at most {REASON_CHARS} characters).')
        lack = [f'{k} ({what})' for k, what in REASONS if not reason_text(row, k)]
        if lack:
            out.append(f"{where}: say {' and '.join(lack)}.")
    return out


def graphics_runs(entry):
    """design/126 TR1: the plan's G1 warning (design/93) on the treatment: a run of graphic shots over 8 s within the gap, from each shot's route and seconds."""
    out, run_s, ids = [], 0.0, []
    for i, sh in enumerate([s for s in entry.get('shots') or [] if isinstance(s, dict)] + [None], 1):
        if sh and sh.get('route') in TREATMENT_GRAPHIC_ROUTES and isinstance(sh.get('seconds'), (int, float)):
            run_s, ids = run_s + float(sh['seconds']), ids + [str(sh.get('id') or f'shot {i}')]
            continue
        if run_s > 8:
            out.append(_graphics_run(entry['gap_id'], ids, run_s))
        run_s, ids = 0.0, []
    return out


# design/203 (SK, 15 Nov 2026): the Direction in six labelled parts, each short; the idea in one sentence
DIRECTION_PARTS = (('idea', 'The idea', 160), ('purpose', 'Who it is for and what it must do', 300), ('viewpoint', 'Whose story', 200),
                   ('feel', 'How it should feel', 300), ('shape', 'How the film moves', 400), ('pictures', 'What each kind of picture does', 500))
SECOND_LINES = (('answers_brief', 'how it answers the brief'), ('risk', 'what it risks'))
DIFFERENT_DIRECTION = 'Show me a different direction'
NOT_IN_PARTS = 'The Direction is not in its six parts.'
NO_DIRECTION = 'Write the Direction first (direction_parts, six short parts): the idea in one sentence, who it is for and what it must do, whose story, how it should feel, how the film moves, what each kind of picture does.'
REDO_NOTE = 'Written again from the direction you chose.'


def _one_line(v):
    return ' '.join(v.split()) if isinstance(v, str) else ''


def direction_from(parts, who='The Direction'):
    """design/203: (the Direction as text, the parts given, the headings not given). The text is each given part as "Heading: text", one to a
    line, in the fixed order, so everything that reads `direction` (the plan's word-for-word check, the line's digest) works as before.
    A part over its length, and an idea of more than one sentence, is refused; a part not given is named and does not stop the draft."""
    parts = parts if isinstance(parts, dict) else {}
    given, missing = {}, []
    for key, heading, limit in DIRECTION_PARTS:
        text = _one_line(parts.get(key))
        need(len(text) <= limit, f'{who}: "{heading}" is at most {limit} characters.')
        if text:
            given[key] = text
        else:
            missing.append(heading)
    need(len(re.findall(r'[.!?]', given.get('idea', ''))) <= 1, f'{who}: The idea is one sentence.')
    return '\n'.join(f'{h}: {given[k]}' for k, h, _ in DIRECTION_PARTS if k in given), given, missing


LOOK_CHARS, LOOK_MAX = 400, 4
NO_LOOK = ('{who}: give its look in `{field}`: a list with one entry for each period the script speaks of, each {{period, look}}; the look is a few lines on colours, contrast, '
           'light and texture. One period: one entry, its period left empty.')
TWO_DIRECTIONS = ('This film has no camera footage, so the operator is always shown two Directions, each with its look: put the second in `direction_alternative` '
                  '(its six parts, `answers_brief`, `risk` and `look`) and send the Direction again.')


def look_of(value, who, field):
    """SK, 23 Nov 2026 (no footage, release 2): the look of a Direction, [{period, look}], one entry for each period of the film."""
    need(isinstance(value, list) and 1 <= len(value) <= LOOK_MAX and all(isinstance(x, dict) for x in value), NO_LOOK.format(who=who, field=field))
    out = [{'period': _one_line(x.get('period')), 'look': _one_line(x.get('look'))} for x in value]
    need(all(x['look'] for x in out), f'{who}: every entry of `{field}` has its look in words.')
    need(all(len(x['look']) <= LOOK_CHARS for x in out), f'{who}: a look is at most {LOOK_CHARS} characters.')
    need(len(out) == 1 or all(x['period'] for x in out), f'{who}: with more than one look, each names its period.')
    need(len({x['period'].lower() for x in out}) == len(out), f'{who}: a period is named twice in `{field}`.')
    return out


def second_due(session, direction):
    """A film with no camera footage is shown two Directions until one is taken: True when this Direction comes without a second and is not the
    one already taken (the accepted line of the draft, else the recorded treatment)."""
    if direction.get('direction_alternative'):
        return False
    draft = session.get('treatment_draft')
    taken = (draft if ((draft.get('lines') or {}).get('direction') or {}).get('state') == 'accepted' else None) if draft else session.get('treatment')
    return not (taken and taken.get('direction') and _line_digests(taken)['direction'] == _line_digests(direction)['direction'])


def look_for(session, scene=None):
    """The film's look in words, for a film whose Direction carries one (no camera footage): the look of the scene's period, else the first. '' otherwise."""
    looks = ((session or {}).get('treatment') or {}).get('direction_look') or []
    period = _one_line((scene or {}).get('period')).lower()
    return next((x for x in looks if x['period'].lower() == period), looks[0])['look'].rstrip('.') if looks else ''


BOARD_REMAKES = 1   # the assistant has a board that does not match its words made again once
NO_BOARDS = 'Look boards are made for a film with no camera footage; this film takes its look from its footage.'
BOARD_FIRST = 'Send the Direction with its looks first (`vw visuals treatment`): the boards are made from them.'


def board_sides(session):
    """SK, 23 Nov 2026 (no footage, release 2b): the Directions whose looks are shown as boards, [(name, text, looks)]: both while the operator
    chooses, then the one taken. [] for a film whose Direction holds no look (a film with footage)."""
    rec = session.get('treatment_draft') or session.get('treatment') or {}
    alt = rec.get('direction_alternative') or {}
    return [(n, t, l) for n, t, l in (('First' if alt else '', rec.get('direction'), rec.get('direction_look')), ('Second', alt.get('text'), alt.get('look'))) if t and l]


def _board_of(text, entry):
    return digest([_one_line(text), entry['period'], entry['look']])   # a board belongs to these words: other words, another board


def board_view(session):
    """Each look of those Directions with its latest board (None when none was asked for), in the order shown."""
    out = []
    for name, text, looks in board_sides(session):
        for e in looks:
            made = [b for b in (session.get('boards') or {}).values() if b['of'] == _board_of(text, e)]
            out.append({'name': name, 'label': ' · '.join(x for x in (name, e['period']) if x), 'text': text, 'of': _board_of(text, e), **e, 'board': max(made, key=lambda b: b['n']) if made else None})
    return out


def look_board(session, scene=None):
    """The picture of the film's look: the made board of the Direction the operator took, of the scene's period, else of the first. None when
    that Direction has none (taken from its words, or a film with footage)."""
    rec = session.get('treatment') or {}
    looks = rec.get('direction_look') or []
    if not looks:
        return None
    period = _one_line((scene or {}).get('period')).lower()
    of = _board_of(rec.get('direction'), next((x for x in looks if x['period'].lower() == period), looks[0]))
    made = [b for b in (session.get('boards') or {}).values() if b['of'] == of and b.get('status') == 'candidate']
    return max(made, key=lambda b: b['n']) if made else None


def made_pictures(session):
    """Every record a finished image job is written on: the references, then the look boards."""
    return list(session['references'].values()) + list((session.get('boards') or {}).values())


def board_lettering(store, outputs):
    """A board shows a sample of lettering only when the script is written in letters the picture AI draws well (Latin)."""
    from . import voices
    try:
        return film.scripts_of(voices.script_text(store, outputs)) <= {'latin'}
    except Problem:
        return False


def board_prompt(text, entry, lettering):
    return ('One picture laid out as a look board for a film, filling the frame.\n'
            f'The film: {_one_line(text)}\n'
            f"Its look: {entry['look'].rstrip('.')}." + (f" The period: {entry['period']}." if entry['period'] else '') + '\n'
            "On the board: two or three frames of this film's own world as the film would show them in this look (a place, people in it, one close detail), "
            "and under them a row of five plain colour swatches of the look's colours"
            + ("; in one corner a short sample of the film's lettering or graphic style, two or three words.\n" if lettering else '.\n')
            + 'Never: a real, named person or their likeness (show the kind of person the film speaks of); the logo or brand mark of any company; '
            + ('any other writing.' if lettering else 'any writing.'))


LOOK_PARENT = "\nImage {n} is the film's look board: take its light, colour and texture only; show nothing of what is on it, no swatches and no lettering."


def look_parent(session, provider, body, element, n):
    """SK, 23 Nov 2026 (release 2c): a run whose picture AI is Nano Banana is handed the look board as one more reference of a picture in the
    film (not a set, a sheet, a graphic or a fix), after its `n` own pictures: (the request's entry, the line that names it), or (None, '').
    A film of more than one period: the board of the period whose look the prompt carries; neither named, no board."""
    if provider != 'gemini' or body.get('set') or body.get('fix_of') or body.get('region') or body['kind'] not in ('keyframe', 'isolated') or element.get('kind') in ('graphic', 'style') or n >= GEMINI_MAX_INPUTS:
        return None, ''
    looks = (session.get('treatment') or {}).get('direction_look') or []
    entry = looks[0] if len(looks) == 1 else next((x for x in looks if x['look'].rstrip('.') in body['prompt']), None)
    board = look_board(session, entry) if entry else None
    return ({**{k: board[k] for k in ('id', 'key', 'sha256')}, 'look': True}, LOOK_PARENT.format(n=n + 1)) if board else (None, '')   # `look`: not a reference of the run; the parent check leaves it out


def look_boards(conn, store, user, run, outputs, make=None):
    """The look boards of a film with no camera footage. With no `make`: what there is and what making the missing ones costs, nothing made (the
    cost is said first). `make='all'`: the missing boards are asked for. `make=<board id>`: that board again (once when it was made; a failed one
    freely). Always GPT Image, whatever the run's picture AI; the cost counts in the film's limit and is checked before anything is asked for."""
    need(core.footage_of(run) == 'none', NO_BOARDS)
    session = session_of(store, run, outputs)
    changed = bool(reconcile(conn, run, session))
    rows = board_view(session)
    need(rows, BOARD_FIRST)
    if make in (None, '', 'all'):
        todo = [(r, 0, 0) for r in rows if r['board'] is None]
    else:
        r = next((r for r in rows if r['board'] and r['board']['id'] == make), None)
        need(r, f'No look board {make!r} among the Directions shown now; `vw visuals boards` lists them.')
        b = r['board']
        need(b['status'] != 'generating', 'This board is still being made.')
        need(b['status'] == 'failed' or b['remakes'] < BOARD_REMAKES, 'This board was made again once already: show it to the operator as it is and say what does not match its words.')
        todo = [(r, b['n'] + 1, b['remakes'] + int(b['status'] != 'failed'))]
    cost = len(todo) * image_price_inr(run, provider='openai')
    if make and todo:
        check_cap(conn, run, session, cost, f"{len(todo)} look board{'' if len(todo) == 1 else 's'}")   # before anything is asked for: nothing half-made
        size, lettering = library.default_size(aspect_of(run, outputs, 'board')), board_lettering(store, outputs)
        for r, n, remakes in todo:
            bid = digest({'run': str(run['id']), 'board': r['of'], 'n': n})[:32]
            request = {'kind': 'image', 'op': 'generate', 'provider': 'openai', 'model': IMAGE_MODELS['generate'], 'prompt': board_prompt(r['text'], r, lettering), 'size': size, 'quality': 'high', 'parents': [],
                       'reference': {'id': bid, 'element_id': 'look', 'element_kind': 'look', 'name': 'look board' + (' ' + r['label'] if r['label'] else ''), 'kind': 'board', 'subject': r['look']}}
            row = conn.execute("insert into vw2_jobs(run_id, stage, unit, request, request_id, provider) values (%s,'visuals',%s,%s,%s,%s) returning id",
                               (run['id'], bid, Jsonb(request), str(uuid.uuid5(uuid.NAMESPACE_OID, 'board:' + bid)), 'openai')).fetchone()   # defect 27: a job's request_id is a uuid
            session.setdefault('boards', {})[bid] = {'id': bid, 'of': r['of'], 'n': n, 'remakes': remakes, 'period': r['period'], 'status': 'generating', 'job_id': str(row['id']),
                                                    'generation': {k: request[k] for k in ('op', 'provider', 'model', 'prompt', 'size', 'quality')}}
        rows, todo, changed = board_view(session), [], True
    if changed:
        save_session(store, run, session)
    out = [{'label': r['label'], 'period': r['period'], 'look': r['look'], **({k: r['board'][k] for k in ('id', 'status', 'error', 'key', 'sha256') if r['board'].get(k)} if r['board'] else {'status': 'not made'})} for r in rows]
    made = [b for b in out if b['status'] == 'candidate']
    if todo:
        nxt = (f"{len(todo)} look board{'' if len(todo) == 1 else 's'} to make with GPT Image, about ₹{cost:,.0f} in all, counted in this film's cost limit: say this cost to the operator, "
               'then `vw visuals boards --make all`.')
    elif any(b['status'] == 'generating' for b in out):
        nxt = 'The boards are being made, about a minute each: run `vw visuals boards` again to see them.'
    else:
        nxt = ('Look at each board against its own words before the operator does (the tool saved them in work/chat/). One that does not match is made again once: `vw visuals boards --make <its id>`. '
               'Then `vw visuals page`: the operator sees each Direction with its board and takes one.'
               + (' A board that was not made is said with its reason: the operator may pick from the words, and it can be asked for again later.' if len(made) < len(out) else ''))
    return {'boards': out, 'to_make': len(todo), 'cost_inr': cost, 'next': nxt,
            'show': [{'key': b['key'], 'name': 'look-board-' + (re.sub(r'[^A-Za-z0-9]+', '-', b['label']).strip('-').lower() or 'film') + '.png'} for b in made]}


def direction_fields(document, none=False):
    """design/203: the Direction of a sent draft as the record keeps it: `direction` (text), `direction_parts`, the two lines on how it answers
    the brief and what it risks (`direction_notes`), a second Direction beside it (`direction_alternative`), and `direction_missing`, what was
    not given. A draft that sends only the older paragraph is taken, flagged as not in its six parts."""
    out, missing = {}, [NOT_IN_PARTS]
    text = str(document.get('direction') or '').strip()
    if isinstance(document.get('direction_parts'), dict):   # when both are sent, the parts win
        text, given, missing = direction_from(document['direction_parts'])
        need(given, NO_DIRECTION)
        out['direction_parts'] = given
    need(text, NO_DIRECTION)   # design/124 Change 3
    need(len(text) <= 2000, 'The Direction is a few lines (at most 2000 characters).')
    out['direction'] = text
    if none:   # SK, 23 Nov 2026: `none`, a film with no camera footage: the Direction holds the film's look; a film with footage keeps none
        out['direction_look'] = look_of(document.get('direction_look'), 'The Direction', 'direction_look')
    notes = {k: _one_line(document.get('direction_' + k)) for k, _ in SECOND_LINES}
    alt = document.get('direction_alternative')
    if isinstance(alt, dict) and 'direction_parts' in out:
        atext, agiven, amissing = direction_from(alt, 'The second direction')
        need(agiven, 'The second direction has none of its six parts.')
        need(_one_line(atext) != _one_line(text), 'The second direction is the same as the first: write one that differs in viewpoint or approach.')
        second = {'parts': agiven, 'text': atext, **{k: _one_line(alt.get(k)) for k, _ in SECOND_LINES if _one_line(alt.get(k))}}
        if none:
            second['look'] = look_of(alt.get('look'), 'The second direction', 'look')
            need(sorted(x['period'].lower() for x in second['look']) == sorted(x['period'].lower() for x in out['direction_look']),
                 'The second direction: its looks are for the same periods as the first.')
        out['direction_alternative'] = second
        missing = (missing + [f'The first direction: {what}' for k, what in SECOND_LINES if not notes[k]] + [f'The second direction: {h}' for h in amissing]
                   + [f'The second direction: {what}' for k, what in SECOND_LINES if k not in second])
    if any(notes.values()):
        out['direction_notes'] = {k: v for k, v in notes.items() if v}
    out['direction_missing'] = missing
    return out


def direction_changes(before_text, before_parts, record):
    """design/203: what changed in the Direction, named by part when both sides are in parts; else what it was before."""
    now_parts = record.get('direction_parts')
    if before_parts and now_parts:
        heads = {k: h for k, h, _ in DIRECTION_PARTS}
        changes = _diff({heads[k]: before_parts.get(k, '') for k in heads}, {heads[k]: now_parts.get(k, '') for k in heads}, '')
        return changes or (['A second direction is shown beside the first.'] if record.get('direction_alternative') else [])
    return [f'Before: "{_short_text(before_text, 2000)}"'] if before_text else []   # design/205: whole (a Direction is at most 2000 characters)


def treatment(store, user, run, outputs, document, quote, accept=(), send_back=(), notes='', use_second=False, different=False):
    """One entry per gap: the team's intended visuals cited or departed from, the picture in a line, the routes, the seconds, the images.
    Without the operator's words the document is kept as the draft the visuals page shows; with them it is recorded (the page records the
    draft with the words given there). `propose` is refused without a record and when a route departs from it.
    design/124 Change 3: a sent document starts with its Direction (a few lines). Change 6: accept or send_back names lines of the draft
    (direction, G1, ...); the draft is recorded when every line is accepted."""
    session = session_of(store, run, outputs)
    alone = isinstance(document, dict) and not document.get('gaps') and not str(quote or '').strip() and not (accept or send_back)
    if not (accept or send_back or alone):
        need_motion_style(run)   # design/179 S3; design/205: asked on the page beside the Direction, so only the whole treatment waits for it
    if alone:
        return _direction_alone(store, user, run, session, document)
    if accept or send_back:
        return _treatment_lines(store, user, run, session, list(accept or []), list(send_back or []), notes, quote, use_second=use_second, different=different)
    if document is None:
        document = session.get('treatment_draft')
        need(document, 'No treatment draft on this run: send one first (`vw visuals treatment --file out/visual-treatment.json`).')
        direction = {k: document[k] for k in ('direction', 'direction_parts', 'direction_notes', 'direction_alternative', 'direction_missing', 'direction_look') if k in document}   # the stored draft, as it is
    else:
        direction = direction_fields(document if isinstance(document, dict) else {}, none=core.footage_of(run) == 'none')   # design/203: six parts, or the older paragraph
        need(core.footage_of(run) != 'none' or not second_due(session, direction), TWO_DIRECTIONS)
    entries = (document or {}).get('gaps')
    need(isinstance(entries, list) and entries, 'The treatment is a list of gaps.')
    gaps = session['source']['gaps']
    seen, totals = set(), {'gaps': 0, 'images': 0, 'routes': {}, 'seconds': {}, 'frozen_seconds': 0.0}
    video_seconds, warnings, unreasoned, still_s, moving_s, unsplit_s = 0.0, [], [], 0.0, 0.0, 0.0
    for e in entries:
        need(isinstance(e, dict) and e.get('gap_id') in gaps, f"The treatment names an unknown gap: {(e or {}).get('gap_id')!r}.")
        need(e['gap_id'] not in seen, f"gap {e['gap_id']} appears twice in the treatment.")
        seen.add(e['gap_id'])
        routes_ = list(e.get('routes') or ([e['route']] if e.get('route') else []))
        need(routes_ and all(r in TREATMENT_ROUTES for r in routes_), f"gap {e['gap_id']}: each route is one of {', '.join(TREATMENT_ROUTES)}.")
        for sh in e.get('shots') or []:   # design/74 L25: one named route takes the shots' routes; several named routes must cover every shot
            r = sh.get('route') if isinstance(sh, dict) else None
            need(r is None or (isinstance(r, str) and r in TREATMENT_ROUTES),   # design/202: a shot's way is one of the five, or it is counted and shown wrongly
                 f"gap {e['gap_id']}: shot {sh.get('id') if isinstance(sh, dict) else ''}: its route is one of {', '.join(TREATMENT_ROUTES)}.")
            if r and r in TREATMENT_ROUTES and r not in routes_:
                need(len(routes_) == 1, f"gap {e['gap_id']}: shot {sh.get('id')} uses the route {r!r}, which the entry does not name; name it in routes or change the shot.")
                routes_.append(r)
        e['routes'] = routes_
        need(not no_clip_routes(session, e['gap_id'], routes_), no_clip_routes(session, e['gap_id'], routes_))   # SK, 23 Nov 2026 (V3)
        need(str(e.get('picture') or '').strip(), f"gap {e['gap_id']}: say the picture in one line.")
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
        parts = [(sh.get('route') or first, sh.get('seconds')) for sh in e.get('shots') or [] if isinstance(sh, dict)]   # design/124-b item 14: a mixed gap's seconds per route
        if parts and all(isinstance(x, (int, float)) and x > 0 for _, x in parts):
            video_seconds += sum(take_seconds(float(x)) for r, x in parts if r == 'video')   # design/134 12: each take at its generated seconds
        else:   # no seconds per shot: today's sum, the first route, all of it as video when video is named
            parts = [(first, e['seconds'])]
            video_seconds += float(e['seconds']) if 'video' in routes_ else 0.0
        for r, x in parts:
            totals['seconds'][r] = round(totals['seconds'].get(r, 0.0) + float(x), 2)
        warnings += graphics_runs(e) + treatment_length_warnings(e)   # design/126 TR1, TR3
        unreasoned += reasons_missing(e)   # design/202
        a, b, c = still_and_moving(e, routes_)
        still_s, moving_s, unsplit_s = still_s + a, moving_s + b, unsplit_s + c
    missing = sorted(set(gaps) - seen)
    need(not missing, 'The treatment covers every gap; missing: ' + ', '.join(missing) + '.')
    totals['still_seconds'], totals['moving_seconds'] = round(still_s, 2), round(moving_s, 2)   # design/202: how much of the film stands still
    if round(unsplit_s, 2) > 0:
        totals['unsplit_seconds'] = round(unsplit_s, 2)   # seconds whose way is not told shot by shot: counted as neither
    film = film_frames(outputs)   # design/89 B4: the expected frozen share, shown before approval
    if film:
        limit = float(settings().VISUALS_STILL_SHARE)
        share = still_s / (film / float(Fraction(str(session['source'].get('fps') or 25))))
        totals['still_share'] = round(share, 3)
        if share > limit + 1e-9:   # compared before rounding; shown rounded up to a tenth, so the figure is never the limit itself
            warnings.append({'kind': 'stills_many', 'message': f"Still pictures are {math.ceil(share * 1000 - 1e-6) / 10:g} % of the film: above {limit * 100:g} %. Make some of them moving shots."})
        totals['frozen_share'] = round(totals['frozen_seconds'] / (film / float(Fraction(str(session['source'].get('fps') or 25)))), 3)
        totals['frozen_limit'] = float(session.get('frozen_limit') or FROZEN_SHARE)
    pr = prices()
    estimate = round(totals['images'] * image_price_inr(run) + video_seconds * shot_second_price(), 2)   # design/223: the first take and its full-size video
    warnings += over_limit(estimate, rerun_allowance(video_seconds, pr), cap_of(session))   # SK, 23 Nov 2026 (V1): a film of AI video alone passes its limit; said here, before anything is paid
    record = {'gaps': entries, 'totals': totals, 'reasons_missing': unreasoned, 'estimate_inr': estimate, 'rerun_allowance_inr': rerun_allowance(video_seconds, pr), 'warnings': warnings, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'digest': digest(entries),
              **direction}   # design/124 Change 3; design/203
    if not str(quote or '').strip():   # the draft the page shows for approval
        record['lines'] = _carry_lines(session, record)   # design/124 Change 6
        session['treatment_draft'] = record
        if all(v['state'] == 'accepted' for v in record['lines'].values()):   # every line accepted already, word for word
            return _record_lines(store, run, session)
        save_session(store, run, session)
        kinds = ', '.join(sorted({str(w.get('kind')) for w in warnings})) or 'none'
        return {'draft': True, 'totals': totals, 'estimate_inr': estimate, 'warnings': warnings, 'reasons_missing': unreasoned, 'direction_missing': record.get('direction_missing', []),
                'cap_inr': cap_of(session), 'digest': record['digest'], 'lines': _line_states(record['lines']),
                'log': f"draft, {len(entries)} gaps, {len([v for v in record['lines'].values() if v['state'] == 'to_accept'])} lines to accept, {len(warnings)} warnings: {kinds}, "
                       f"reasons missing: {len(unreasoned)}, direction parts not given: {len(record.get('direction_missing', []))}"}   # design/205: the run log says what a draft returned
    session['treatment'] = {**record, 'quote': quote}
    session.pop('treatment_draft', None)
    save_session(store, run, session)
    return {'recorded': True, 'totals': totals, 'estimate_inr': estimate, 'warnings': warnings, 'cap_inr': cap_of(session), 'digest': record['digest']}


DIRECTION_ACCEPTED = ('The Direction is accepted. Now write every gap line from it and send the whole treatment (`vw visuals treatment --file out/visual-treatment.json`, '
                      'the Direction unchanged, word for word), then `vw visuals page` for the gap lines.')


def _direction_alone(store, user, run, session, document):
    """design/205 (SK, 15 Nov 2026): the Direction is written, shown and answered before any gap line is written. A draft that holds only the
    Direction is kept as the draft with one line; accepting that line never records the treatment."""
    direction = direction_fields(document, none=core.footage_of(run) == 'none')
    need(core.footage_of(run) != 'none' or not second_due(session, direction), TWO_DIRECTIONS)   # SK, 23 Nov 2026
    record = {'gaps': [], 'direction_only': True, 'totals': {}, 'estimate_inr': 0, 'warnings': [], 'reasons_missing': [], 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(),
              'digest': digest([]), **direction}
    old = session.get('treatment_draft') or {}
    same = (old.get('lines') or {}).get('direction', {}).get('digest') == _line_digests(record)['direction']
    need(not (same and old.get('gaps')), 'Nothing changed in the Direction, and this draft would drop the gap lines already written: send the whole treatment (the Direction and its gaps).')
    record['lines'] = _carry_lines(session, record)
    session['treatment_draft'] = record
    save_session(store, run, session)
    state = record['lines']['direction']['state']
    return {'draft': True, 'direction_only': True, 'direction_missing': record.get('direction_missing', []), 'lines': _line_states(record['lines']),
            'next': DIRECTION_ACCEPTED if state == 'accepted' else 'The Direction alone is with the operator: `vw visuals page`. Write no gap line until it is accepted.',
            'log': f"draft, the Direction alone ({state}), direction parts not given: {len(record.get('direction_missing', []))}"}


# ---------- design/124 Change 6: a state per line of the treatment ----------

def _line_digests(record):
    """The Direction and each gap entry, each a line the operator accepts or sends back on its own."""
    second = _one_line((record.get('direction_alternative') or {}).get('text'))   # design/203: a second Direction beside the first is part of the line the operator answers
    look = [[x['period'], x['look']] for x in (record.get('direction_look') or []) + ((record.get('direction_alternative') or {}).get('look') or [])]   # a film with no camera footage: the look is part of the line
    out = ({'direction': digest([_one_line(record['direction']), second, look]) if look else
            digest([_one_line(record['direction']), second]) if second else digest(' '.join(record['direction'].split()))}) if record.get('direction') else {}
    out.update({e['gap_id']: digest(e) for e in record.get('gaps') or []})
    return out


def _line_states(lines):
    return {k: v['state'] for k, v in lines.items()}


def _carry_lines(session, record):
    """A revised draft keeps the verdict on every line whose text did not change; a changed line goes back to 'to_accept', marked changed.
    The line before is the last draft's, else the recorded treatment's (every line of it accepted with its words)."""
    old = (session.get('treatment_draft') or {}).get('lines')
    if old is None and session.get('treatment'):
        old = {k: {'digest': d, 'state': 'accepted', 'quote': session['treatment'].get('quote')} for k, d in _line_digests(session['treatment']).items()}
    old, lines = old or {}, {}
    was = session.get('treatment_draft') or session.get('treatment') or {}
    was_gaps = {e.get('gap_id'): e for e in was.get('gaps') or []}
    now_gaps = {e.get('gap_id'): e for e in record.get('gaps') or []}
    for k, d in _line_digests(record).items():
        o = old.get(k)
        # design/202: the operator sent it back and it was rewritten. It stays "asked" through any further send until they answer it, and what
        # changed is told against what they were looking at (`was`), not against a draft in between that they never saw.
        asked = bool(o) and o['digest'] != d and (o.get('state') == 'sent_back' or (o.get('state') == 'to_accept' and o.get('asked')))
        seen = o.get('was') if asked and o.get('was') is not None else None
        lines[k] = dict(o) if o and o['digest'] == d else {'digest': d, 'state': 'to_accept', **({'changed': True} if o else {}),
                                                           **({'asked': True} if asked else {}), **({'was': seen} if seen is not None else {})}
        if o and o['digest'] == d and o.get('redo'):   # design/203: sent back because the operator chose the other Direction, and the assistant lets it stand
            lines[k] = {'digest': d, 'state': 'to_accept'}
        if o and o['digest'] != d:   # design/191 section 11, B2: what changed in the line, for the question
            if k == 'direction':   # design/203: named by part; `was` is {'direction', 'parts'} (a text alone on a line sent back before design/203)
                held = seen if isinstance(seen, dict) else {'direction': seen} if isinstance(seen, str) else {'direction': was.get('direction'), 'parts': was.get('direction_parts')}
                changes = direction_changes(held.get('direction'), held.get('parts'), record)
            else:
                before_gap = seen if isinstance(seen, dict) else was_gaps.get(k)
                changes = _diff(before_gap, now_gaps[k], '') if before_gap is not None else []
            if changes:
                lines[k]['changes'] = changes
    return lines


def _record_lines(store, run, session):
    draft = session.pop('treatment_draft')
    quotes = list(dict.fromkeys(v['quote'] for v in draft['lines'].values() if v.get('quote')))
    session['treatment'] = {**draft, 'quote': ' / '.join(quotes)}
    save_session(store, run, session)
    return {'recorded': True, 'totals': draft['totals'], 'estimate_inr': draft['estimate_inr'], 'warnings': draft.get('warnings', []), 'cap_inr': cap_of(session), 'digest': draft['digest'], 'lines': _line_states(draft['lines']),
            'next': 'Treatment recorded: every line accepted. The assistant writes the plan to it.'}


def _treatment_lines(store, user, run, session, accept, send_back, notes, quote, use_second=False, different=False):
    """design/203: `different` sends the Direction back with fixed words, asking for a second one; `use_second` accepts the second Direction
    shown beside the first: it becomes the Direction and every gap line goes back to be written again from it."""
    notes = notes if str(notes or '').strip() or not different else DIFFERENT_DIRECTION
    draft = session.get('treatment_draft')
    need(draft, 'No treatment draft on this run: send one first (`vw visuals treatment --file out/visual-treatment.json`).')
    lines = draft.get('lines') or {k: {'digest': d, 'state': 'to_accept'} for k, d in _line_digests(draft).items()}   # a draft from before Change 6
    accept, send_back = [str(x).strip() for x in accept], [str(x).strip() for x in send_back]
    unknown = [x for x in accept + send_back if x not in lines]
    need(not unknown, f"Not a line of the treatment draft: {', '.join(unknown)}; its lines are {', '.join(lines)}.")
    need(not set(accept) & set(send_back), 'A line is accepted or sent back, not both.')
    need(not send_back or str(notes or '').strip(), 'Say what to change in the line sent back (notes).')
    at = datetime.now(timezone.utc).isoformat()
    seen_gaps = {e.get('gap_id'): e for e in draft.get('gaps') or []}
    for k in accept:
        lines[k] = {'digest': lines[k]['digest'], 'state': 'accepted', 'quote': said(quote, 'accepted', user), 'by': user['id'], 'at': at}
    if 'direction' in accept and draft.get('direction_alternative'):   # design/203: one of the two is taken; the other is dropped
        second = draft.pop('direction_alternative')
        if use_second:
            draft['direction'], draft['direction_parts'] = second['text'], second['parts']
            if second.get('look'):
                draft['direction_look'] = second['look']
            draft.pop('direction_notes', None)
            if any(second.get(k) for k, _ in SECOND_LINES):
                draft['direction_notes'] = {k: second[k] for k, _ in SECOND_LINES if second.get(k)}
            for k in lines:   # every gap line was written from the other Direction: back to the assistant
                if k != 'direction':
                    lines[k] = {'digest': lines[k]['digest'], 'state': 'sent_back', 'note': REDO_NOTE, 'redo': True, 'by': user['id'], 'at': at,
                                **({'was': seen_gaps[k]} if k in seen_gaps else {})}
        draft['direction_missing'] = [m for m in draft.get('direction_missing') or [] if not m.startswith(('The first direction', 'The second direction'))]
        lines['direction']['digest'] = _line_digests(draft)['direction']
    for k in send_back:
        was = {'direction': draft.get('direction'), 'parts': draft.get('direction_parts')} if k == 'direction' else seen_gaps.get(k)   # design/202: what the operator was looking at
        lines[k] = {'digest': lines[k]['digest'], 'state': 'sent_back', 'note': str(notes).strip(), 'quote': said(quote, 'sent back', user), 'by': user['id'], 'at': at,
                    **({'was': was} if was is not None else {}), **({'different': True} if different and k == 'direction' else {})}
    draft['lines'] = lines
    if all(v['state'] == 'accepted' for v in lines.values()):
        if not draft.get('direction_only'):
            return _record_lines(store, run, session)
        save_session(store, run, session)   # design/205: the Direction alone is never the treatment
        return {'draft': True, 'direction_only': True, 'lines': _line_states(lines), 'next': DIRECTION_ACCEPTED}
    save_session(store, run, session)
    waiting = [k for k, v in lines.items() if v['state'] != 'accepted']
    back = [k for k, v in lines.items() if v['state'] == 'sent_back']
    return {'draft': True, 'lines': _line_states(lines),
            'next': f"Still to accept: {', '.join(waiting)}." + (f" Sent back: {', '.join(back)}: the assistant revises only those lines and sends the draft again." if back else '')}


# ---------- design/65 §8: what the visuals page shows ----------

def _guide_view(session, shot_id, url):
    """Integration steps B to D: the guide of a shot for the page (None when it has none). Imported here because guide.py builds on this module."""
    from . import guide
    return guide.view(session, shot_id, url)


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
        refs[r['id']] = {k: r.get(k) for k in ('id', 'name', 'kind', 'element_id', 'status', 'sha256', 'job_id', 'width', 'height', 'check_pending', 'set', 'set_n', 'notes', 'sources')}   # design/92: being checked; design/151: the set
        refs[r['id']]['note'] = (r.get('source') or {}).get('note') or ''   # design/73
        refs[r['id']]['from_thumbnail'] = bool((r.get('source') or {}).get('from_thumbnail'))   # design/100 S2
        refs[r['id']]['sources_changed'] = bool(r.get('sources_changed'))   # design/110
        gold_ = golden_of(session, r.get('element_id'))   # design/111 F11
        refs[r['id']]['golden'] = bool(gold_) and gold_ == r['id']
        first = ((r.get('generation') or {}).get('parents') or [{}])[0].get('id')
        refs[r['id']]['from_golden'] = (first == gold_) if gold_ and r.get('kind') in ('keyframe', 'isolated') and r.get('role') != 'end' and not r.get('golden_candidate') and r['id'] != gold_ else None
        refs[r['id']]['edit'] = r.get('edit')
        refs[r['id']]['locked'] = verdict_lock(session, r)   # U17
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
                                                 'check': (session.get('take_checks') or {}).get(str(j['id'])), 'sheet_url': url(res.get('sheet_key') or ((session.get('take_checks') or {}).get(str(j['id'])) or {}).get('sheet_key')) if (res.get('sheet_key') or ((session.get('take_checks') or {}).get(str(j['id'])) or {}).get('sheet_key')) else None,
 'pair_url': url(((session.get('take_checks') or {}).get(str(j['id'])) or {}).get('pair_key')) if ((session.get('take_checks') or {}).get(str(j['id'])) or {}).get('pair_key') else None,   # design/91 N3; design/117 P4
                                                 **({'fact_check': ((session.get('motion_checks') or {}).get(j['unit']) or [None])[-1]} if (j.get('request') or {}).get('kind') == 'motion' else {}),
                                                 **(_finish_view(session, j, res) if (j.get('request') or {}).get('kind') == 'motion' else {})})   # design/130: the latest verdict on the shot
    gaps = []
    for gid, g in sorted(session['source']['gaps'].items(), key=lambda kv: kv[1].get('start_frame', 0)):
        entry = {'gap_id': gid, **g, 'accepted': gid in session['accepted'], 'recorded': gid in session['recorded_gaps'], 'shots': [], 'choices': None, 'warnings': [], **_accepted_words(session, gid)}
        if plan:
            gap = next((x for x in plan['gaps'] if x['gap_id'] == gid), None)
            if gap:
                entry['warnings'] = plain_warnings(session, gap, plan)   # design/124 Change 8
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
                                           'facts_line': facts_line(plan, sh), 'warning_answers': sh.get('warning_answers') or [],   # design/124 Change 7
                                           **({'ambient': ambient.get(sh['id'])} if sh['visual_type'] == 'video' and ambient.get(sh['id']) else {}),   # design/101 M6
                                           **{k: sh[k] for k in ('size', 'camera_reason') if sh.get(k)}, **lit.get(sh['id'], {}),   # design/103
                                           'start_frame': sh['start_frame'], 'end_frame': sh['end_frame'], 'states': sh.get('states') or [], 'element_ids': sh.get('element_ids') or [],
                                           'bound': [b['id'] for rows in binding.get('references', {}).values() for b in rows],
                                           'asset': ({'kind': asset['kind'], 'url': url(None if asset['kind'] == 'clip' else asset.get('key')), 'reference_id': asset.get('reference_id'), 'states': [{'reference_id': st['reference_id'], 'url': url(st['key']), 'hold_frames': st['hold_frames']} for st in asset.get('states') or []],
                                                      **({k: asset.get(k) for k in ('clip_id', 'name', 'in_s', 'out_s')} if asset['kind'] == 'clip' else {}),   # design/89 B3
                                                      **({'by': asset.get('by_name') or '', 'quote': asset.get('quote') or '', 'duration_s': asset.get('duration_s'), 'made_outside': True, 'made': asset.get('made') or ''} if asset['kind'] in ('movie', 'still') else {})} if asset else None),   # R21, E17: a supplied file
                                           'takes': takes.get(sh['id'], []), 'prepared': sh['id'] in session['preparations'], 'guide': _guide_view(session, sh['id'], url), **_state_order(session, sh),   # design/94 A2
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
    return {'state': 'prepared', 'busy': not repair, **_shared_note(store, session), 'fps': session['source'].get('fps'), 'plan_digest': session.get('current'), 'versions': len(session['versions']),
            'footage': footage_view(session, outputs),   # design/88 F4: told, not asked
            'reuse_pending': session.get('reuse_pending') or {},   # design/89 H7; design/207 (D2): no longer shown or asked; cleared when the reuse gate next runs
            'likeness': dict(session.get('likeness') or {}),   # design/207 (D1): per person, the operator's recorded yes that they have the person's permission
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
            'element_matches': element_matches(plan, package.get('world_evidence')) if plan else {}, 'searches': _searches(session), 'round': _round_view(session, plan, _set_budget(run, session, sp)), 'stock_source': STOCK_SOURCE,
            'kept': is_kept(session, run),   # design/151 hotfix: the page shows the kept way before the round
            'questions': dict(session.get('questions') or {}),   # design/110 rule 0
            'golden': dict(session.get('golden') or {}),   # design/111 F11
            'illustrative': illustrative_share(plan) if plan else {'illustrative': [], 'specs': 0, 'warning': None},   # design/111 F19
            'waiting': waiting(session, plan, code, take_rows, _set_budget(run, session, sp)),   # design/97 W1, W3
            'gaps': gaps, 'references': list(refs.values()), 'budget': {**sp, 'set_inr': round(image_price_inr(run, provider='gemini') * SET_MAX, 2), 'cap_inr': cap_of(session), 'left_inr': round(cap_of(session) - sp['spent_inr'], 2)}}


SIZE_NAMES = {'EWS': 'Extreme wide', 'WS': 'Wide', 'MWS': 'Medium wide', 'MS': 'Medium', 'MCU': 'Medium close-up', 'CU': 'Close-up', 'ECU': 'Extreme close-up'}


def facts_line(plan, shot):
    """design/124 Change 7: one line per shot from the plan's checked facts: its size, the words it sits under, what each subject does last and
    how it ends, and the counts that change. Written by the server, never by the assistant."""
    names = {e['id']: e['name'] for e in plan.get('elements') or []}
    words = str(shot.get('narration') or '').split()
    parts = ([SIZE_NAMES[shot['size']]] if shot.get('size') in SIZE_NAMES else []) + (["under '" + ' '.join(words[:12]) + ('…' if len(words) > 12 else '') + "'"] if words else [])
    for s in shot.get('subjects') or []:
        name = names.get(s['element_id'], s['element_id'])
        if s.get('beats'):
            last = s['beats'][-1]
            parts += [f"{name}: {last.get('done') or last['action']}", f"ends {last['result']}"]
        a, z = ({o['element_id']: o['count'] for o in (s.get(k) or {}).get('objects') or []} for k in ('start', 'end'))
        parts += [f'{names.get(e, e)} {a.get(e, 0)} → {z.get(e, 0)}' for e in dict.fromkeys([*a, *z]) if a.get(e, 0) != z.get(e, 0)]
    return ' · '.join(parts)


def _every_scene(gap):
    """all_scenes, for a line shown to the operator: a way with no scenes written yet gives none, never an error."""
    return [sc for c in gap.get('choices') or [] for sc in c.get('scenes') or []] or gap.get('scenes') or []


def plain_warnings(session, gap, plan=None):
    """design/124 Change 8: the current plan's warnings on this gap that the operator sees, in plain words, with the assistant's answer.
    design/207: with the plan, the stand-in line is worked out now, not read from the stored proposal: it goes once the permission is recorded."""
    version = next((v for v in reversed(session.get('versions') or []) if v.get('plan_digest') == session.get('current')), None)
    scenes = _every_scene(gap)
    shots, scene_ids = {sh['id'] for sc in scenes for sh in sc['shots']}, {sc['id'] for sc in scenes if sc.get('id')}
    stored =[w for w in (version or {}).get('warnings') or [] if w.get('kind') in WARNING_PLAIN
              and (w.get('shot_id') in shots or w.get('scene_id') in scene_ids or (w.get('gap_id') == gap['gap_id'] and not w.get('shot_id')))]
    if plan:
        answers = {w['shot_id']: w.get('answer') for w in stored if w['kind'] == 'stand_in_real'}
        stored = [w for w in stored if w['kind'] != 'stand_in_real'] + [
            {'kind': 'stand_in_real', 'shot_id': sid, **({'answer': answers[sid]} if answers.get(sid) else {})} for sid in stand_in_shots(session, plan) if sid in shots]
        missing = supplied_missing(session, plan)   # release 3, C3: the same for a logo or brand file: the line goes once the file is given
        stored = [w for w in stored if w['kind'] != 'supplied_missing' or w.get('shot_id') in missing]
    return [{'kind': w['kind'], **({'shot_id': w['shot_id']} if w.get('shot_id') else {}), 'plain': WARNING_PLAIN[w['kind']], **({'answer': w['answer']} if w.get('answer') else {})} for w in stored]


def warning_lines(session, gap, plan):
    """design/207: the plain sentences of a gap as the operator reads them on the plan page and in the chat, each once; a shot's sentence is led by
    the shot's title. From the same function the server's page uses (one flow, two front ends)."""
    ways = [c['scenes'] for c in gap.get('choices') or [] if c.get('scenes')] or [gap.get('scenes') or []]
    titles = {sid: coded(names, sid) for names in (way_names(gap, w) for w in ways) for sid in names}   # VW-25 issue 7: in words, the code last
    return list(dict.fromkeys((f"{titles[w['shot_id']]}: " if w.get('shot_id') in titles else '') + w['plain'] for w in plain_warnings(session, gap, plan)))


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
        warnings.append(f'these states have no shot recorded: the order given is used; make states with --shot {shot_id} so the order comes from its own pictures')
        for i, row in enumerate(rows[1:], 2):
            parents = [p.get('id') for p in (row.get('generation') or {}).get('parents') or []]
            if rows[i - 2]['id'] not in parents:
                warnings.append(f"state {i} ({row['id']}) was not generated from state {i - 1} ({rows[i - 2]['id']}); check the drawing is the same")
    from . import lookalike   # design/91 N12: every state adds something visible
    prints = [(_fingerprints(store, r['key']) or {}).get('graphic') for r in rows]
    for i in range(1, len(rows)):   # design/217 (R3): two steps alike is the operator's to judge (shown as advice, asked once on the page), no longer a refusal
        if not (prints[i - 1] is None or prints[i] is None or lookalike.distance(prints[i - 1], prints[i]) > lookalike.BITS_GRAPHIC):
            warnings.append(f'steps {i} and {i + 1} look almost the same: approved on the operator\'s word')
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
        k = 'footage' if sh['visual_type'] == 'footage' else 'graphics' if sh['visual_type'] in GRAPHIC_TYPES else 'AI video' if sh['visual_type'] == 'video' else 'drawn' if sh['visual_type'] == 'drawn' else ('still (frozen)' if (sh.get('motion') or 'push_in') == 'none' else 'still (moving)')   # design/112 K3; design/113
        row = out.setdefault(k, {'route': k, 'seconds': 0.0, 'shots': 0})
        row['seconds'] = round(row['seconds'] + (sh['end_frame'] - sh['start_frame']) / float(fps), 1)
        row['shots'] += 1
    return [out[k] for k in ('footage', 'graphics', 'drawn', 'AI video', 'still (moving)', 'still (frozen)') if k in out]


def _still_text(shot, ref):
    """design/112 K4: a still with words: the plan says so, every graphic, or the picture's answer carries exact text."""
    return bool(shot.get('carries_text')) or shot.get('visual_type') in ('diagram', 'animation') or bool(library.exact_entries((ref or {}).get('answer') or {}))


def _accepted_shots(plan, session):
    """The shots of the accepted gaps, as (gap, shot), in film order."""
    out = []
    for gap in plan['gaps']:
        acc = session['accepted'].get(gap['gap_id'])
        if not acc or acc['digest'] != gap_digest(plan, gap) or (gap.get('choices') and not session['choice_selections'].get(gap['gap_id'])):
            continue
        out += [(gap, sh) for sc in chosen_scenes(gap, session['choice_selections'].get(gap['gap_id'])) for sh in sc['shots']]
    return sorted(out, key=lambda gs: gs[1]['start_frame'])


def name_of(gap, sh, n, of):
    """A shot's name is never its id: its title, else its gap's title and its number in the gap."""
    return str(sh.get('title') or (str(gap.get('title') or f"Gap {gap.get('gap_id')}") + (f', shot {n}' if of > 1 else '')))


def way_names(gap, scenes):
    """VW-25 issue 7 (SK, 25 Nov 2026): {shot id: its name} for one way of a gap; the number counts inside that way."""
    shots = [sh for sc in scenes or [] for sh in sc.get('shots') or []]
    return {sh['id']: name_of(gap, sh, n, len(shots)) for n, sh in enumerate(shots, 1)}


def shot_names(plan, session):
    """VW-25 issue 7: {shot id: its name} for every accepted shot, numbered in the film's order inside its gap (as `takes.video_shots` does)."""
    by_gap = {}
    for gap, sh in _accepted_shots(plan, session):
        by_gap.setdefault(gap['gap_id'], []).append((gap, sh))
    return {sh['id']: name_of(gap, sh, n, len(rows)) for rows in by_gap.values() for n, (gap, sh) in enumerate(rows, 1)}


def coded(names, sid):
    """The name with the code last, in brackets: the assistant and the builders find the shot by it. (Until 25 Nov 2026 a card showed the title,
    else the bare code; retired.) An id with no name stays as it is."""
    return f'{names[sid]} ({sid})' if sid in names else str(sid)


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


def _not_yet_gate(store, run, session, row, at_approval=False, shot=None):
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
        _open(session, row['id'], f"{why}. Make a new start, or approve this one anyway?", [f"make a new start ({round(image_price_inr(run), 2):g} INR)", 'approve anyway'], 'server', fork='not_yet')
    need(False, f"{why}; the operator decides: make a new start, or approve anyway (the question is on its card; `vw visuals answer --item {row['id']} …`).")


# ---------- design/111 F19 (plan-check and count parts): illustrative earned, the share counted, the view named ----------

def spec_view(shot):
    """The drawing's view and its reason; a section with no view given is a cutaway."""
    spec = shot.get('drawing_spec') or {}
    if spec.get('view'):
        return spec['view'], (spec.get('view_reason') or '').strip()
    words = ' '.join(str(shot.get(k) or '') for k in ('depicts', 'purpose', 'title')).lower()
    return ('cutaway', 'a section is shown cut through') if 'section' in words else ('', '')


def view_line(shot):
    if not shot.get('drawing_spec'):
        return None
    v, why = spec_view(shot)
    return {'check': 'view: ' + v, 'pass_when': f'the drawing is a {v} view' + (f' ({why})' if why else ''), 'weight': 'must'} if v else None


def illustrative_share(plan):
    """The run's illustrative specs against all its specs (drawing specs on shots, material specs on elements); a warning above one in four."""
    ids, n = [], 0
    for g in plan.get('gaps') or []:
        for sc in (g.get('scenes') or []) + [sc for ch in g.get('choices') or [] for sc in ch.get('scenes') or []]:
            for sh in sc.get('shots') or []:
                if sh.get('drawing_spec'):
                    n += 1
                    if sh['drawing_spec'].get('illustrative'):
                        ids.append('shot ' + sh['id'])
    for e in plan.get('elements') or []:
        if e.get('material_spec'):
            n += 1
            if e['material_spec'].get('illustrative'):
                ids.append('element ' + e['id'])
    warn = (f"{len(ids)} of {n} specs are illustrative (above one in four): {', '.join(ids)}: measure them (the client material, the footage frames, a standard or maker figure, an approved picture)"
            if ids and len(ids) * 4 > n else None)
    return {'illustrative': ids, 'specs': n, 'warning': warn}


# ---------- design/111 F18: the place in use, the real light of the footage ----------

OCCUPIED = {'check': 'occupied', 'weight': 'must', 'pass_when': 'the place looks occupied or in use: traces of work or living at its landmarks, nothing showroom-clean or empty'}


def _place_in(plan, element_id, shot):
    kinds = {e['id']: e['kind'] for e in plan.get('elements') or []}
    return any(kinds.get(i) == 'place' for i in [element_id] + list(shot.get('element_ids') or []))


def place_line(plan, element_id, shot):
    # design/124-b item 4: the place's must line: occupied or in use, or clean and unused where every place in frame is staged clean with its reason
    places = [e for e in plan.get('elements') or [] if e['kind'] == 'place' and e['id'] in [element_id] + list(shot.get('element_ids') or [])]
    if not places:
        return None
    if all(str(e.get('staged_clean') or '').strip() for e in places):
        return {'check': 'clean', 'weight': 'must', 'pass_when': 'clean and unused, as planned (' + '; '.join(e['staged_clean'].strip().rstrip('.') for e in places) + '): no traces of work or living'}
    return OCCUPIED


def signs_lines(session, plan, scene, shot, element_id):
    """Two signs of use per shot, from the places in frame, taken in turn (the next shot gets the next pair); a shot keeps the pair it was given."""
    elements = {e['id']: e for e in plan.get('elements') or []}
    places = [elements[i] for i in dict.fromkeys([element_id] + list(shot.get('element_ids') or [])) if i in elements and elements[i]['kind'] == 'place' and elements[i].get('signs_of_use')]
    if not places:
        return []
    chosen = session.setdefault('signs', {})
    if shot['id'] not in chosen:
        pick = []
        for p in places:
            pool, cur = p['signs_of_use'], session.setdefault('signs_cursor', {}).get(p['id'], 0)
            pick += [pool[(cur + i) % len(pool)] for i in range(min(2, len(pool)))]
            session['signs_cursor'][p['id']] = (cur + 2) % len(pool)   # ponytail: round robin; a place with two signs repeats its pair, add more signs to vary
            if len(pick) >= 2:
                break
        chosen[shot['id']] = pick[:2]
    marks = {lm['id']: lm['description'] for lm in scene.get('landmarks') or []}
    return ['Signs of use: ' + '; '.join(f"{s['what']} at {marks.get(s['landmark_id'], s['landmark_id'])}" for s in chosen[shot['id']]) + '.'] if chosen[shot['id']] else []


def real_light_line(store, session, scene=None):
    """Composed once per run from the footage character and the measured light of the approved footage frames, then kept on the session.
    design/134 3: a scene with its own light keeps the footage's look and the no-glow clause, never the film's measured brightness and colour."""
    look = look_for(session, scene)   # SK, 23 Nov 2026: a film with no camera footage reads the look of the Direction the operator took
    if look or no_real_clip(session):
        return (f"The film's look: {look}. " if look else '') + 'No studio light, no glow, no added saturation.'
    parts = session.get('real_light_parts')
    if parts is None:
        parts = session['real_light_parts'] = _real_light_parts(store, session)
    own = bool(scene) and bool(str(scene.get('light') or '').strip())
    words = [w for w in (parts['look'], '' if own else parts['measured']) if w]
    if not (parts['look'] or parts['measured']):
        return ''
    return ('Real light, as the footage has it: ' + '; '.join(words) + '. ' if words else '') + 'No studio light, no glow, no added saturation' + (
        '; the same light and colour as the footage beside it.' if not own else '.')


def _real_light_parts(store, session):
    f = (session.get('footage') or {}).get('summary') or {}
    stats = []
    for r in [r for r in session.get('references', {}).values() if r.get('kind') == 'frame' and r.get('status') == 'approved' and r.get('key')][:6]:
        try:
            stats.append(image_check._light(store.get(r['key'])))
        except Exception:
            continue
    look = measured = ''
    if f.get('look') and f['look'] not in ('unknown', 'mixed'):
        look = f"{f['look']} look" + (f", {FM.CAMERA_WORDS.get(f['camera'], f['camera'])}" if f.get('camera') and f['camera'] not in ('unknown', 'mixed') else '')
    if stats:
        m = {k: sum(s[k] for s in stats) / len(stats) for k in ('brightness', 'saturation', 'warmth')}
        measured = (('dim' if m['brightness'] < 0.35 else 'bright' if m['brightness'] > 0.65 else 'mid') + ' light, '   # ponytail: first-guess bands on 0..1 means, tune on real films
                    + ('muted' if m['saturation'] < 0.3 else 'rich' if m['saturation'] > 0.55 else 'ordinary') + ' colour, '
                    + ('cool' if m['warmth'] < -0.03 else 'warm' if m['warmth'] > 0.05 else 'neutral') + ' cast')
    return {'look': look, 'measured': measured}


# ---------- design/111 F17: groups of a kind, said; background figures compared within the scene ----------

def group_lines(plan, shot):
    """One line per group: all alike with the reason, or no two alike with the traits."""
    names = _names(plan)
    out = []
    for g in shot.get('groups') or []:
        head = f"Every {names[g['kind']]}" if g['kind'] in names else f"{g['count']} {g['kind']}"
        traits = '; '.join(i.strip().rstrip('.') for i in g.get('items') or [])
        out.append(head + (f": all alike ({g.get('reason', '').strip().rstrip('.')})." if g['mode'] == 'same' else f', varied, the traits in turn: {traits}.' if g['mode'] == 'varied'   # design/124-b decision (a)
                           else f': no two alike: {traits}.'))
    return out


def group_rule_lines(plan, shot):
    """The two must lines: the count (for a group that is no element; the inventory counts elements) and the sameness."""
    names = _names(plan)
    out = []
    for g, line in zip(shot.get('groups') or [], group_lines(plan, shot)):
        name = names.get(g['kind'], g['kind'])
        if g['kind'] not in names:
            out.append({'check': f'group count: {name}', 'weight': 'must', 'pass_when': f"about {g['count']} {name} are in frame" if g['mode'] == 'varied'
                        else f"exactly {g['count']} {name} are in frame, no more, no fewer"})   # design/124-b decision (a): a varied group is counted roughly; design/207: the line no longer says "a crowd"
        out.append({'check': f'group alike: {name}', 'weight': 'must', 'pass_when': (f'the {name} are all alike in shape, size, colour and wear' if g['mode'] == 'same'
                                                                                     else f'the {name} differ; these traits appear among them: ' + '; '.join(g.get('items') or []) if g['mode'] == 'varied'
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
        if not keys.pool('gemini', settings()):
            return {**rec, 'error': 'no Gemini key on the server'}
        parts = []
        for i, r in enumerate(others, 1):
            parts += [{'text': f"Picture {i} ({r['id']})."}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(r['key'])).decode()}}]
        parts += [{'text': 'The new picture.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(row['key'])).decode()}}]
        parts.append({'text': 'Look only at the background and secondary figures (people and animals), not the main subject. Does any figure in the new picture look like the same '
                              'individual as a figure in an earlier picture (same face, build, hair, clothes, markings)? Answer repeated true or false, and in detail name the pair '
                              'and what matches. Be literal; two figures of one kind that differ in face, clothes or markings are not repeated.'})
        received, rec['key_index'] = keys.gemini(_gemini_transport(), image_check.CHECK_MODEL, lambda t: t.generate(
            {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': FIGURE_SCHEMA, 'thinkingConfig': {'thinkingLevel': 'LOW'}, 'maxOutputTokens': 8192}}),
            settings(), terminal_deadline_seconds=120, initial_soft_wait_seconds=20, on_update=lambda e: None, capture_answer_deltas=False)   # design/114
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
    other = elements.get(shot['compare_to'], {})
    comp = other.get('name', shot['compare_to'])
    beside = f'beside the person ({comp})' if other.get('kind') == 'person' else f'against the {comp} beside it'   # design/207: a person is the first choice of comparison
    return f"Size is the point: {el.get('name', subj)}, {sizes}, {beside}; the sizes read true against each other and the place."


def animal_lines(plan, element_ids):
    """design/207 (D4): a living extra has no reference sheet; its words (the exact kind, its look) go into every prompt that shows it. Its size is in
    the prompt's Sizes line already (size_sentence, any kind)."""
    return [f"{e.get('name') or e['id']}: {e['description'].strip().rstrip('.')}." for e in plan.get('elements') or []
            if e.get('kind') == 'animal' and e['id'] in (element_ids or []) and (e.get('description') or '').strip()]


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
        tail = (['no one looks at the lens'] if not looks_at_camera(shot, when) else []) + (['no one looks where they looked in Image 1 unless named here'] if when in ('end', 'motion') else [])
        if tail:
            said_ = '; '.join(tail)
            out[-1] += ' ' + said_[0].upper() + said_[1:] + '.'
    return out


def looks_at_camera(shot, when):
    """design/134 7: a person the plan has look at the camera (design/124-b item 17); then nothing forbids the lens."""
    return any(((s.get('end' if when in ('end', 'motion') else 'start') or {}).get('gaze') or {}).get('target') == GAZE_CAMERA for s in shot.get('subjects') or [])


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
            "(the bond, the shape, the surface, the colour, the size, the fittings), twelve lines at most, no explanations." +
            ('\nThe operator rejected these web results or wrote why nothing fit; turn each difference into a line too: ' + '; '.join(near[:20]) if near else ''))
    need(keys.pool('gemini', settings()), 'No Gemini key on the server.')
    try:
        received, _ = keys.gemini(_gemini_transport(), NOT_THIS_MODEL, lambda t: t.generate(
            {'contents': [{'role': 'user', 'parts': [{'text': text}]}], 'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': NOT_THIS_SCHEMA, 'thinkingConfig': {'thinkingLevel': 'LOW'}, 'maxOutputTokens': 8192}}),
            settings(), terminal_deadline_seconds=120, initial_soft_wait_seconds=20, on_update=lambda e: None, capture_answer_deltas=False)   # design/114
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


KEPT_PREAMBLE = ("I need a photograph-like image that will be used as a reference picture for an AI image model. Because it is a reference, technical correctness matters more than anything else: "
                 "the AI will copy exactly what it sees, including any mistake. So I am not going to describe how the work is done. You will take that entirely from real photographs: search Google Images "
                 "for real photographs of the subject below, study how it is really done, and build the picture from them. If anything I ask for below contradicts what the real photographs show, the photographs win.\n"
                 "One rule above all: show one way of doing it, as one real photograph would. Real photographs will show you more than one method of doing the same thing. Do not combine them into a single picture, "
                 "and do not add elements from one method to another. Choose the one method that appears most often in the photographs, or the one most typical of the place I describe, and show only that, exactly "
                 "as it appears in those photographs, with nothing added. Everything in the picture must be justified by a single, consistent way of working; if two details could not both be true at the same time "
                 "on one real site, one of them does not belong. Mention the other methods you saw only in your notes, not in the picture.")   # design/151: the kept prompt, version 6 (SK, 4 Nov 2026), verbatim
KEPT_SET_LINE = ("This is a set of three pictures of the same one subject on the same site, made one per turn: I name each picture's view in its turn; keep every detail the same across the set, each "
                 "picture adding the view the others lack. Deliver each picture as one separate output image at full size, never as a collage, grid or split frame, with no borders, numbers or captions "
                 "inside any picture. Say what each picture adds.")   # design/151 section 13: gemini-nano-banana-2.1 draws one picture per turn
KEPT_NOTES = ("With the pictures, tell me: (1) the one method you chose and why, and the other methods you saw in the photographs but left out; (2) what you found in the real photographs and which findings "
              "you implemented; (3) anything in my request that the photographs contradicted and what you did instead; (4) the web pages and images you consulted, with URLs.")
KEPT_COSMETICS = ("Cosmetic requirements, which do not touch the technical content:\n- The place reads as {place}; the film's look: {look}.\n- Natural daylight as in that place, natural colours, no filters, no stylisation, no illustration.\n"
                  "- Camera close enough that the subject is readable, the surroundings soft.\n- No person, no text, logos, watermarks, stock-site lettering or maker's stamps; nothing in the picture that the real photographs do not justify.")
KEPT_DRAWN_LINE = ("The drawings were made from this thing's real sizes and approved by the film's operator. For how the thing is built, its pattern, its proportions and its counts, the drawings "
                   "and the facts below are the truth: where a real photograph differs from them, the drawings win. Take from the real photographs only what a drawing cannot show: the material, "
                   "its surface, colour and wear, and the place. The picture is a photograph of the real thing, never a picture of a drawing.")   # design/200: the one case where the photographs do not win
DRAWN_LOOK_LINE = {'check': 'a photograph, not a drawing', 'weight': 'must', 'pass_when': 'the picture reads as an ordinary photograph of a real thing: no flat colour fills, no outlines, no white drawing background'}
KEPT_FRAME_LINE = "Image 1 is the approved footage frame of {name}: take the thing itself from it (its exact form, material and wear); what the frame does not show, take from the real photographs."
HOW_WORDS = re.compile(r'\b(step by step|how to|how it is done|procedure)\b', re.I)
PERSON_SET = ("Make a set of three separate pictures of this one person, one per turn: 1, a full-length front view standing at ease; 2, a full-length three-quarter view in a working pose of their trade; 3, a close-up of the face. "
              "Deliver each as one separate output image at full size, never a collage, grid or split frame; the same person in every picture in every detail; alone on plain neutral ground, nothing else in the frame; "
              "no text, numbers or captions inside any picture.")   # design/151 part 2; design/124 decision 5: from words, never from a picture of a real person
THING_VIEWS = ['the whole of {name}, filling the frame', 'a three-quarter view of the same {name}', 'a close-up of the key detail of the same {name}, the part that shows how it is made or used']   # design/151 section 13
PERSON_VIEWS = ['a full-length front view standing at ease', 'a full-length three-quarter view in a working pose of their trade', 'a close-up of the face']


def set_views(element):
    """design/151 section 13: the views of a set, one per turn, named by the server (a person's three poses; a thing's whole, three-quarter and close-up)."""
    if element.get('kind') == 'person':
        return list(PERSON_VIEWS)
    return [v.format(name=element.get('name') or element.get('id')) for v in THING_VIEWS]
KEPT_THING_LINES = [{'check': 'one way only', 'weight': 'must', 'pass_when': 'every detail belongs to one consistent way of working; nothing from a second method is mixed in'},
                    {'check': 'the subject fills the frame', 'weight': 'must', 'pass_when': 'the subject is the picture; the setting is only a soft hint at the edges'},
                    {'check': 'nothing floats', 'weight': 'must', 'pass_when': 'nothing floats or stands where it could not stand on a real site'},
                    {'check': 'no person', 'weight': 'must', 'pass_when': 'no person, no hands, no face anywhere in the frame'},
                    {'check': 'no text', 'weight': 'must', 'pass_when': 'no caption, number, label, logo or watermark anywhere in the picture'}]
PERSON_SET_LINES = [{'check': 'one person', 'weight': 'must', 'pass_when': 'one person alone, no second person and nothing else in the frame'},
                    {'check': 'plain ground', 'weight': 'must', 'pass_when': 'plain neutral ground, no setting'},
                    {'check': 'no text', 'weight': 'must', 'pass_when': 'no caption, number or label anywhere in the picture'}]
SET_MAX = 3   # design/151 section 13: a set is three pictures, one per turn (len(THING_VIEWS) == len(PERSON_VIEWS))
TRAIT_WORDS = (('40s', r'\b(forty|fort(y|ies)|4\d)\b'), ('20s', r'\b(twenty|twenties|2\d)\b'), ('30s', r'\b(thirty|thirties|3\d)\b'), ('50s', r'\b(fifty|fifties|5\d)\b'), ('60s', r'\b(sixty|sixties|6\d)\b'),
               ('teens', r'\b(teen\w*|1\d)\b'), ('lean', r'\b(lean|slim|wiry|thin(?! (moustache|beard)))\b'), ('stocky', r'\b(stocky|heavy|broad|plump|stout)\b'), ('tall', r'\btall\b'), ('short', r'\bshort(?!\w| hair| grey| black| white| cropped)\b'),
               ('short hair', r'\bshort( \w+)? hair\b'), ('long hair', r'\blong( \w+)? hair\b'), ('cropped', r'\bcropped\b'), ('bald', r'\bbald\w*\b'), ('grey', r'\b(grey|gray|white)( hair|-haired)?\b'),
               ('beard', r'\bbeard\w*\b'), ('moustache', r'\bmo?ustache\b'), ('clean-shaven', r'\bclean-shaven\b'), ('glasses', r'\b(glasses|spectacles)\b'))


def traits(text):
    """design/151: the compared traits of a person's description, as words: age band, build, hair, face; two people alike on all of them are refused."""
    text = str(text or '')
    return frozenset(name for name, rx in TRAIT_WORDS if re.search(rx, text, re.I))


def alike_people(plan):
    """Every pair of people whose descriptions carry the same compared traits (age band, build, hair, face), as (id, id), in the plan's order."""
    people = [e for e in plan.get('elements') or [] if e.get('kind') == 'person']
    return [(a['id'], b['id']) for i, a in enumerate(people) for b in people[i + 1:] if traits(a.get('description')) == traits(b.get('description'))]


PEOPLE_ALIKE = 'These two people read alike, {a} and {b}: add what tells them apart.'


def distinct_people(plan):
    """design/151 part 2: every pair of people differs on at least one compared trait, whoever they are in the film; an alike pair is refused by name
    before any payment. design/207: the plan check names every such pair together first (carried_warnings, `people_alike`)."""
    names = {e['id']: e.get('name') or e['id'] for e in plan.get('elements') or []}
    for a, b in alike_people(plan)[:1]:   # design/216 (B5): plain words, as the page shows them (was: "alike on every compared trait (age, build, hair, face) ...")
        need(False, PEOPLE_ALIKE.format(a=names[a], b=names[b]))


def _place_look(plan, session=None):
    scenes = [sc for gap in plan.get('gaps') or [] for sc in (gap.get('scenes') or [])]
    place = next((str(sc.get('location_time') or '').strip() for sc in scenes if str(sc.get('location_time') or '').strip()), 'the place the plan describes')
    return place, str((plan.get('foundation') or {}).get('appearance') or '').strip() or look_for(session) or 'as the footage'


def thing_prompt(plan, run, session, element, subject, frame=False, drawn=None):
    """design/151 part 3: the kept method's prompt for a thing: the preamble and the set line verbatim, the writer's subject block (what, never how), the
    cosmetics from the plan (Q7), the frame's job line when the thing has one (Q1), the four notes."""
    subject = ' '.join(str(subject or '').split())
    need(subject, 'Give the subject block: what the picture must represent, the subject and its frame, nobody in the picture.')
    m = HOW_WORDS.search(subject)
    if m:
        need(False, f'The subject block describes how the work is done ({m.group(0)!r} …): the kept method takes that from real photographs; say only what the picture must represent.')
    place, look = _place_look(plan, session)
    parts = [KEPT_PREAMBLE, KEPT_SET_LINE, 'What the picture must represent: ' + subject.rstrip('.') + '.']
    if frame:
        parts.append(KEPT_FRAME_LINE.format(name=element.get('name') or element['id']))
    if drawn:   # design/200: (how to read the drawings sent, the facts) of the thing's approved drawing set
        how, facts = drawn
        parts += [how, KEPT_DRAWN_LINE] + (['What must be true:\n' + '\n'.join(f'- {f}' for f in facts)] if facts else [])
    parts += [KEPT_COSMETICS.format(place=place, look=look), KEPT_NOTES]
    return '\n\n'.join(parts)


def material_words(writer_prompt, subject, is_set):
    """Hotfix, 11 Nov 2026 (VW-19): the material-words check (design/111 F10) reads the writer's words. For a kept set those are the subject block:
    the server's own kept preamble says "most typical of the place", which the check refused, so no set of a material element could be made."""
    return subject if is_set else writer_prompt


LIKENESS_PHOTO_LINE = ('Image 1 is a photograph of this person, used with their permission: take the face, the build, the skin and the hair from it, nothing else; '
                       'the garments, the poses and the plain ground are as written here.')   # design/207 (D1)


def person_prompt(plan, run, element, why='', photo=False, session=None):
    """design/151 part 2: a person's character sheet from the plan's words: who they are, their fixed look, their garments, the place, the writer's why line,
    one line against every other person so they stay apart, then the three poses as separate pictures. design/207 (D1): photo: the person's own photo is
    Image 1 (own likeness, with the recorded permission); without it the person is a stand-in, made from the words alone."""
    others = [e for e in plan.get('elements') or [] if e.get('kind') == 'person' and e['id'] != element['id']]
    outfits = list(dict.fromkeys(str((sc.get('outfit') or {}).get(element['id']) or '').strip() for gap in plan.get('gaps') or [] for sc in (gap.get('scenes') or [])))
    outfits = [o for o in outfits if o]
    place, look = _place_look(plan, session)
    lines = [f"Character sheet of {element.get('name') or element['id']} ({element['id']}), a person in this film.",
             f"Who they are: {str(element.get('requirements') or '').strip().rstrip('.')}.",
             f"Fixed look: {str(element.get('description') or '').strip().rstrip('.')}.",
             *(["Garments: " + '; '.join(outfits) + '.'] if outfits else []),
             f"Place: {place}; the film's look: {look}."]
    why = ' '.join(str(why or '').split())
    if why:
        lines.append(f"Why: {why.rstrip('.')}.")
    lines += [f"Not {o['id']} ({o.get('name') or o['id']}): {str(o.get('description') or '').strip().rstrip('.')}." for o in others]
    if photo:
        lines.append(LIKENESS_PHOTO_LINE)
    lines.append(PERSON_SET)
    return '\n'.join(lines)


def with_faces(session, parents, people, room=None, faces=None):
    """design/151 Q3: a person's full-length front (picture 1 of the set, the golden) brings the face close-up (picture 3) into a shot's prompt by default;
    the other poses go in by name. Returns the parents and the job lines of the pictures added. room, faces: how many more pictures the picture
    service takes in all, and of people (None: no limit). A face beyond either is left out: the person's full-length picture and written description
    carry them, and no line says a picture is attached when it is not."""
    parents, lines = list(parents), []
    limit = min((n for n in (room, faces) if n is not None), default=None)
    for p in list(parents):
        if limit is not None and len(lines) >= limit:
            break
        if p and p.get('kind') == 'sheet' and p.get('set') and int(p.get('set_n') or 1) == 1 and p.get('element_id') in people:
            face = session['references'].get(f"{p['set']}-3")
            if face and face.get('status') == 'approved' and all(q['id'] != face['id'] for q in parents if q):
                parents.append(face)
                lines.append(f"Image {len(parents)} is the face of {p['element_id']} ({people[p['element_id']]}): take the face from it, nothing else.")
    return parents, lines


def kept(session):
    """design/151: this film's references are made the kept way (set at its first round on a new film); an older film keeps the search, the picks and the sheet from words."""
    return (session or {}).get('refs') == 'kept'


def round_v2(session):
    """design/211: this film's reference round was created after the references step was rebuilt (`round['v'] == 2`). Every new behaviour of
    design/211 is behind it; a round without it runs as before, to its end."""
    return ((session or {}).get('round') or {}).get('v') == 2


ROUND_V = 2   # design/211: the version a round gets when it is posted for a film with no round. The tests of the older round, written before design/211, set it to None


def is_kept(session, run):
    """design/151 (hotfix, 4 Nov 2026, VW-18): a new film (from design/139 on) with no older references (no sheet, no web pick) is kept from the start, not only once its round is
    posted: the page, the next-step lines and the refusals agree before the round. An older film, or one that already made a sheet or picked a web picture, is not."""
    return kept(session) or (not film.older(run) and not any(r.get('kind') in ('sheet', 'web') for r in (session or {}).get('references', {}).values()))


def round_due(session, plan):
    """design/151 hotfix (VW-18, 4 Nov 2026): on a kept film with an accepted gap and no round posted, the status says in words that the reference round is next,
    before any picture; the chat tool prints it in its one line (the specs can be approved meanwhile)."""
    if round_v2(session):   # design/211: while the round waits for Claude (the looks at the made sets, a request to rewrite), every status repeats what to do
        from . import ref_sets
        return ref_sets.then_of(session) if _round_pass(session, session['round']) in ('looking', 'rewrite') else None
    if not plan or not kept(session) or session.get('round') or not session.get('accepted'):
        return None
    if not any(e.get('kind') != 'graphic' and e['id'] != STYLE for e in plan.get('elements') or []):
        return None
    if ROUND_V == 2:   # design/211: a film with no round starts the rebuilt references step: the footage is searched first; once every thing is searched, the round file is next
        from . import ref_find
        return ref_find.LOOK_ALL if ref_find.all_searched(session, plan) else ref_find.FIND_START
    return ('the reference round is next, before any picture: `vw visuals elements`, then `vw visuals frame --file out/frames.json` for every element the footage shows, '
            "then `vw visuals round --file out/reference-round.json` (one row per element, every person included and none for an animal: element_id, frames, prompt); the sets are made on Gemini's image model with Google Search, "
            "whatever the film's picture AI for the shots; the specs can be approved meanwhile")


def round_status(session, plan):
    """What `vw visuals status` says of the reference round (`round_due` in its answer). design/211 review, N1: a v2 round has one sentence
    for each of its states, the server's; the tool prints it and adds no line of its own."""
    if round_v2(session):
        from . import ref_sets
        return ref_sets.status_of(session)
    return round_due(session, plan)


SHEET_BY_ROUND = ("{eid}: on this film a reference set is made through the reference round, on the operator's word, never by `vw visuals image --kind sheet`. Its line is on the page "
                  '(`vw visuals page`); a thing the round does not hold yet comes in by sending the round file again (`vw visuals round --file out/reference-round.json`).')


def round_word(store, run, outputs, quote):
    """design/211 review: the chat tool's doors to a paid step of a v2 round (`round --verdicts`, `round --sets`) need the operator's words,
    as `--rest` and `--make` do. The page's click and the chat's answer carry their own word. An older round: as before."""
    if round_v2(session_of(store, run, outputs)):
        from . import ref_sets
        need(str(quote or '').strip(), ref_sets.WORD_NEEDED)


def mark_kept(session, run):
    """Sets the flag when is_kept says so; True when the film is kept (already or now)."""
    if kept(session):
        return True
    if not is_kept(session, run):
        return False
    session['refs'] = 'kept'
    return True


def golden_of(session, element_id):
    return (session.get('golden') or {}).get(element_id)


def golden_due(session, plan):
    """The elements whose golden picture the assistant writes now: a non-person, non-graphic element with an approved sheet (and an approved material spec when it has one),
    no golden picture yet and none being made."""
    out = []
    if kept(session):   # design/151: the golden picture is the ticked picture of the set; no separate call
        return out
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


def sheet_due(session, plan):
    """design/119 rule 2: the elements whose reference sheet the assistant writes now: an element (not the style) with an approved source (a frame, a
    supplied or a web picture) and no sheet approved, candidate or being made."""
    out = []
    if kept(session):   # design/151: the round makes every set; nothing is written per element
        return out
    for e in plan.get('elements') or []:
        if e['id'] == STYLE or e.get('kind') == 'animal':   # design/207 (D4): a living extra has no sheet
            continue
        refs = [r for r in session['references'].values() if r.get('element_id') == e['id']]
        sources = [r['id'] for r in refs if r.get('kind') in ('frame', 'supplied', 'web') and r.get('status') == 'approved']
        person = e.get('kind') == 'person'   # design/207 (D3): every person gets a sheet, with or without a source picture
        if (not sources and not person) or any(r.get('kind') == 'sheet' and r.get('status') in ('approved', 'candidate', 'generating') for r in refs):
            continue
        views = ', '.join(e.get('required_views') or []) or 'the views the plan needs'
        if person and likeness_photo(session, e['id']):   # design/207 (D1): own likeness: the sheet is made from the person's photo
            sources = [likeness_photo(session, e['id'])]
        elif person:   # a stand-in: the sheet is made from words; no picture of a person goes to the picture AI without their permission
            out.append({'element_id': e['id'], 'next': f"write the reference sheet of {e['id']} now from the person's description (build, age, posture, garments and how they are worn, hair"
                                                        + (f"; look at {','.join(sources)} and describe them" if sources else '')
                                                        + f"), with no picture parents: `vw visuals image --element {e['id']} --kind sheet …` ({views}; the person alone on plain ground)"})
            continue
        out.append({'element_id': e['id'], 'next': f"write the reference sheet of {e['id']} now: `vw visuals image --element {e['id']} --kind sheet --parents {','.join(sources)} …` ({views}; the thing alone on plain ground)"})
    return out


def sheet_block(element):
    views = ', '.join(element.get('required_views') or []) or 'the views the plan needs'
    who = 'the person' if element.get('kind') == 'person' else 'the thing'
    return f"Reference sheet of {element.get('name') or element['id']}: the views {views}, each labelled; {who} alone on plain ground, nothing else in the frame."


def sheet_lines(element):
    name = element.get('name') or element['id']
    who = 'the person' if element.get('kind') == 'person' else 'the thing'
    return ([{'check': f'view: {v}', 'weight': 'must', 'pass_when': f'the sheet shows {name} in a {v} view, labelled as such'} for v in element.get('required_views') or []]
            + [{'check': 'nothing but the thing', 'weight': 'must', 'pass_when': f'nothing in the frame but {who} on plain ground: no setting, no other people, no other objects'}])


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
    need(w * h <= REGION_MAX + 1e-9, f'The region covers {w * h * 100:.0f} % of the frame: an edit changes one region of a third at most; for an end image, make the shot start-only (end_state_exact false) and let the motion carry the change; '
                                       'for another picture, make a new one with the golden picture as Image 1.')   # design/124 A4 item 13
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
    places = [place_words(scene_marks, o.get('place')) for s in shot.get('subjects') or [] for w in ('start', 'end') for o in (s.get(w) or {}).get('objects') or []]
    stacks = [p for p in places if 'stack' in p.lower()]   # design/124 A4 item 15: only where a stack is named and nothing is put on it
    stack = '; nothing rests on top of the stack' if stacks and not any(re.match(r'(on|onto|on top of)\b', p, re.I) for p in stacks) else ''
    return 'Inventory, exactly: ' + '; '.join(items + holders) + '. Nothing else of these kinds in frame' + stack + '.'


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
        out_of_frame = when != 'start' and (p.get('end') or {}).get('where') == 'carried_out'   # design/134 1: a tool the action carries out is not also fully inside
        same = (f"The same {name}: it keeps its shape, size, colour and handle (where it has one) in every picture it appears in; no second one appears"
                + ('' if out_of_frame else '; it is fully inside the frame') + '. ')
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
                        + ('' if looks_at_camera(shot, 'end') else '; no one looks at the lens') + '; no one looks where they looked in Image 1 unless named'})
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
        need(not q, f"{item} waits for the operator's answer: {q['question'] if q else ''} It is asked in the chat: `vw visuals next`; "
                    f"nothing is made from {item} until then.")


def ask(store, user, run, outputs, item, question, choices, cost_inr=None):
    """The assistant's question at a fork: one sentence, the concrete choices, the paid cost; recorded on the item, shown on its card, in status and in waiting."""
    session = session_of(store, run, outputs)
    need(_item_kind(store, session, item), f'{item} is not a picture, a shot or an element of this run.')
    q = _open(session, item, question, choices, user['id'], cost_inr)
    save_session(store, run, session)
    return {**q, 'next': f"Question recorded on {item}: the server hands it to the operator in the chat, in its turn: `vw visuals next`; "
                         f"nothing is made from {item} until then."}


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
                r.update(status='rejected', rejection={'notes': f'the operator kept {words} for {item}', 'quote': words, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()})
    if q.get('fork') == 'parent' and words == q['choices'][0]:
        session['references'][item]['parent_ok'] = True
    if q.get('fork') == 'not_yet' and words == q['choices'][1]:   # F3: approved anyway, on the operator's word; the flaw is theirs to carry as a parent too
        session['references'][item].update(not_yet_ok=True, parent_ok=True)
    record = {**q, 'answer': words, 'answered_by': user['id'], 'answered_at': datetime.now(timezone.utc).isoformat()}
    del session['questions'][item]
    session.setdefault('answered', []).append(record)
    save_session(store, run, session)
    return {**record, 'next': f'Answered: {words}. Work on {item} goes on from this answer.'}


NO_UNDO = ('Done on step 1 cannot be undone on this film: its reference sets are ordered, and paid for, as soon as it is said, and they stay. '
           'The operator answers the sets on the page (`vw visuals page`): a set that is not right is made again there with their words, and a thing whose set was not made can be left out.')


def round_undo(store, user, run, outputs, quote):
    """Done on a pass is undone until the next step used its result: pass 1 until a pick is saved, pass 2 until a sheet was made from the pictures.
    design/210 review: an older film's round only. A round that makes sets (the kept method) is never undone after Done: the sets are ordered and
    paid at Done, the footage pictures approved and the starting pictures set, and nothing here takes those back."""
    session = session_of(store, run, outputs)
    rd = session.get('round')
    need(not (rd and rd.get('kept') and rd.get('pass') != 1), NO_UNDO)
    need(rd and rd.get('pass') in (2, 'complete'), 'Nothing to undo: the round is at pass 1 or has not started.')
    searches = session.get('searches') or {}
    own = [sid for r in rd['elements'].values() for sid in _sids(r)]
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


OWN_PICTURE_MAX = 15 * 1024 * 1024
# VW-25 issues 10 and 11 (SK, 25 Nov 2026: "three and one"): up to three own pictures of one thing (the set's request takes three, ref_sets.inputs_of),
# one photo of a real person; the comment written with them is at most 300 characters. The sentences are the page's and the chat's alike.
OWN_MAX, OWN_WORDS_MAX = 3, 300
OWN_MOST = 'Three pictures at most. Remove one first.'
OWN_ONE = 'One photo of a person at most. Remove one first.'
OWN_WORDS_REFUSED = 'Your words with the picture cannot be kept: {why} Write them again without it.'
OWN_WORDS_LONG = 'Your words with the picture are {n} characters long: {max} characters at most. Write them shorter.'
LIKENESS_REFUSED = 'Give another photo of this person, or make them a stand-in, made from the description.'   # design/207 (D1): when the picture service refuses the photo


def likeness_of(session, element_id):
    """design/207 (D1): the operator's recorded yes that they have this person's permission ({quote, by, at}), or None: the person is a stand-in."""
    return ((session or {}).get('likeness') or {}).get(element_id)


def likeness_photo(session, element_id):
    """design/207 (D1): the picture a person's sheet is made from when the permission is recorded: the operator's newest own photo (a later photo replaces
    an earlier one), else the approved footage frame that shows the person's face best (design/213: `ref_find.faces_of`; a look that passes before a
    weak one, then the view order), else the person's first approved footage frame. None for a stand-in: the sheet is made from the description."""
    if not likeness_of(session, element_id):
        return None
    mine = _own_pictures(session, element_id)
    frames = [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('status') == 'approved' and r.get('element_id') == element_id]
    when = lambda rid: str(session['references'][rid].get('created_at') or '')   # the session is stored with its keys sorted: the order of the rows says nothing
    if mine:
        return max(mine, key=when)
    from . import ref_find
    return next((f for f in ref_find.faces_of(session, element_id) if f in frames), None) or (min(frames, key=when) if frames else None)


def own_picture_refused(kind, session=None, element_id=None):
    """U19, design/207 (D1): the one condition. Why an uploaded picture is not taken for this element, or None: a person's photo needs the recorded permission."""
    if kind != 'person' or likeness_of(session, element_id):
        return None
    return ("A person's own photo is used only with their permission. Ask the operator; when they say they have it, record their words: "
            f'`vw visuals likeness --element {element_id} --quote "<their words>"`. Then give the photo again. '
            'Without it the person is a stand-in, made from the description.')


def person_picture_refused(session, people, row):
    """design/124 decision 5, design/207 (D1): the one test, for every door to the picture AI (a picture's parents, the pictures an end image
    inherits from its start, a guide's still and its look). Why this picture is not sent, or None: a web picture of a person never; a footage
    frame or the operator's own photo of a person only with the recorded permission. people: {person element id: name}."""
    if not (row and row.get('kind') in ('frame', 'web', 'supplied') and row.get('element_id') in people and (row['kind'] == 'web' or not likeness_of(session, row['element_id']))):
        return None
    what = {'frame': 'a footage frame', 'web': 'a web picture', 'supplied': "the operator's own picture"}[row['kind']]
    return (f"{row['id']} is {what} of {people[row['element_id']]} ({row['element_id']}), a person: " + (
        'a picture of a person from the web is never sent to the picture AI.' if row['kind'] == 'web' else
        f"a picture of a real person goes to the picture AI only with their permission, recorded in the operator's words (`vw visuals likeness --element {row['element_id']} --quote \"<their words>\"`).")
        + " Leave it out; without the permission the person's sheet is written from the description (build, age, posture, garments, hair).")


def people_of(plan):
    return {e['id']: e.get('name') or e['id'] for e in plan.get('elements') or [] if e.get('kind') == 'person'}


def likeness(store, user, run, outputs, element_id, quote, conn=None, stand_in=False):
    """design/207 (D1): the operator's yes, once per person, in their own words: they have this person's permission to make AI pictures of them. With it the
    person's own photo (or footage frame) is the source of their sheet. stand_in: the record is removed; the person is made from the description again and a
    set made from the photo is rejected (its golden picture with it; a complete round is open again for this person). One run-log line either way, with
    the words; a stand-in asked for a person who has no record changes nothing and logs nothing.
    design/213: a person the footage shows (a kept frame whose look says it shows their face): the permission needs no photo, the set is then made from
    the film's own pictures of them; "make a stand-in" is recorded too (`session['stand_in'][id]`: {quote, by, at}), so the question is not asked again
    (`ref_sets.footage_person`); the permission removes that record."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    element = next((e for e in plan['elements'] if e['id'] == element_id), None)
    need(element, f'{element_id} is not an element of the plan.')
    need(element.get('kind') == 'person', f"{element_id} is a {element.get('kind')}: the permission is recorded for a person only.")
    quote = ' '.join(str(quote or '').split())
    need(quote, "Give the operator's own words (--quote): " + ('why this person is a stand-in now.' if stand_in else "their yes that they have this person's permission to make AI pictures of them."))
    from . import ref_find
    faces = ref_find.faces_of(session, element_id)   # design/213: the footage shows this person's face
    stamp = {'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    if stand_in and not likeness_of(session, element_id) and (not faces or (session.get('stand_in') or {}).get(element_id)):   # nothing to remove: no record, no log line
        return {'element_id': element_id, 'likeness': False, 'next': f'{element_id} is already a stand-in: no permission is recorded for this person. Nothing was changed.'}
    name, had = element.get('name') or element_id, bool(likeness_of(session, element_id))
    if stand_in:
        if faces:
            session.setdefault('stand_in', {})[element_id] = stamp
        (session.get('likeness') or {}).pop(element_id, None)
        if (session['references'].get(golden_of(session, element_id) or '') or {}).get('kind') in ('supplied', 'frame'):   # the photo is no longer the starting picture
            session['golden'].pop(element_id)
        rd = session.get('round') or {}
        row = (rd.get('elements') or {}).get(element_id) or {}
        if rd.get('kept') and (row.get('made') or {}).get('photo'):   # the set made from the photo is no longer in use: rejected, its golden picture gone, the round open again for this person
            stamp = {'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'notes': 'the permission was removed after this set was made from the photo; the set is made again from the description'}
            for r in _set_rows(session, element_id, row.get('set'), ('candidate', 'approved')):
                r.update(status='rejected', rejection=stamp)
                if golden_of(session, element_id) == r['id']:
                    session['golden'].pop(element_id)
            row.pop('answer', None)
            if rd.get('pass') == 'complete':
                rd['pass'] = 2
        if not kept(session):   # an older film: its sheet made from a picture is marked as design/110 marks it
            for r in session['references'].values():
                if r.get('kind') == 'sheet' and r.get('element_id') == element_id and r.get('status') != 'rejected' and (r.get('generation') or {}).get('parents'):
                    r['sources_changed'] = True
    else:
        session.setdefault('likeness', {})[element_id] = stamp
        (session.get('stand_in') or {}).pop(element_id, None)
    save_session(store, run, session)
    if conn is not None:
        from . import runlog
        runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f'person {element_id}', 'rule': 'design/207 (own likeness with permission, or a stand-in)',
                            'entry': f'{name} is a stand-in, made from the description' + ('; the permission record is removed' if had else '') if stand_in else f"the operator has {name}'s permission to make AI pictures of them",
                            'by_kind': 'operator', 'by_name': user.get('name') or '', 'quote': quote, 'request_id': None})
    return {'element_id': element_id, 'likeness': not stand_in,
            'next': (f'{element_id} is a stand-in: the sheet is made from the description, with no picture of the person in the footage.' if stand_in and not had else
                     f'{element_id} is a stand-in again: the sheet is made from the description. A sheet made from the photo is no longer used: make it again (`vw visuals round --make {element_id}`).' if stand_in else
                     f"The permission is recorded for {element_id}. Their sheet is made from the film's own pictures of them; a photo of their own, when one is given (`vw visuals own --element {element_id} --file <photo>`), is used instead." if faces else
                     f"The permission is recorded for {element_id}. Give the person's photo (`vw visuals own --element {element_id} --file <photo>`); their sheet is made from it.")}


def _own_pictures(session, element_id):
    """The operator's own approved pictures of an element, oldest first."""
    return [r['id'] for r in session['references'].values() if r.get('kind') == 'supplied' and r.get('status') == 'approved' and r.get('element_id') == element_id]


def _own_golden(session, element_id, ref_id):
    """U19: an approved picture of the operator's own for this element: it may be chosen as the starting picture like a picture of the set."""
    r = session['references'].get(ref_id) or {}
    return r.get('kind') == 'supplied' and r.get('status') == 'approved' and r.get('element_id') == element_id


def _golden_ok(session, kind, element_id, golden, rows):
    """U19: the starting picture chosen at step 2 is a picture of the set, or the operator's own picture of the same element; refused in plain words for
    another element's picture and for a person's uploaded photo. False: neither (a set made again since)."""
    r = session['references'].get(golden) or {}
    if r.get('kind') == 'supplied':
        need(r.get('element_id') == element_id, f"{element_id}: the starting picture chosen is a picture of another element; choose one of its own.")
        need(not own_picture_refused(kind, session, element_id), own_picture_refused(kind, session, element_id))
    return any(x['id'] == golden for x in rows) or _own_golden(session, element_id, golden)


def own_words_checked(words):
    """VW-25 issue 11: the comment the operator wrote with their own picture, as one line; refused in plain words when it says what no picture's
    request may say (the check of a correction kept for every picture, design/215), before anything is stored."""
    words = ' '.join(str(words or '').split())
    need(len(words) <= OWN_WORDS_MAX, OWN_WORDS_LONG.format(n=len(words), max=OWN_WORDS_MAX))   # the page stops there and the tool refuses before; an answer sent another way is refused here
    if words:
        from . import library
        try:
            library.check_prompt(words, placed=False)
        except ValueError as exc:
            need(False, OWN_WORDS_REFUSED.format(why=exc))
    return words


def own_words(session, user, plan, element_id, words, to_set):
    """VW-25 issue 11: the operator's comment with their own picture is kept with the thing, in one place for the page and the chat. `to_set`: a set
    is made from the picture (a person, a thing with approved drawings): the words are the operator's words of its request (`operator_words`), said
    by every make from now on, also after a make that failed. Otherwise the picture is the reference itself: the words are the thing's correction
    (`thing_corrections`, design/215), which every later picture of the thing carries; the later one is the one in force. The same words given again
    are kept once. True when they were kept now. The caller checked them (`own_words_checked`) and saves the session."""
    words = ' '.join(str(words or '').split())
    row = ((session.get('round') or {}).get('elements') or {}).get(element_id)
    if not words:
        return False
    if to_set and row is not None:
        if (row.get('operator_words') or [''])[-1] == words:
            return False
        row.setdefault('operator_words', []).append(words)
        return True
    from . import ref_sets
    if (ref_sets.corrections_of(session, plan, element_id) or [''])[-1] == words:
        return False
    ref_sets.correction_kept(session, user, element_id, words, (row or {}).get('set'))
    return True


def supply_own(conn, store, user, run, outputs, element_id, content=None, url='', name='', words=''):
    """design/110 rule 0 (Revathi's addition): the operator's own picture from the page, a file or an https link, stored as an approved reference of the element.
    VW-25 issues 10 and 11 (25 Nov 2026), for the page and the chat alike: a thing takes up to three own pictures (OWN_MAX); another one is refused
    (OWN_MOST) until one is removed; the same picture given again is taken once, by its content. A person keeps one photo: a later one takes the
    place of the earlier, as before. `words`: the operator's comment with the picture (`own_words`), with a line in the run's log.
    The older way is retired: any number of own pictures of a thing, the same file stored again each time it was given, and no words."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    element = next((e for e in plan['elements'] if e['id'] == element_id), None)
    need(element, f'{element_id} is not an element of the plan.')
    url = str(url or '').strip()
    need(content or url.startswith('https://'), 'Give a file or an https link to the picture.')
    refused = own_picture_refused(element.get('kind'), session, element_id)   # design/207 (D1): a person's photo needs the recorded permission, on every film
    need(not refused, refused)
    if not content:
        content = fetch_image(url)
    need(len(content) <= OWN_PICTURE_MAX, 'The picture is larger than 15 MB: choose a smaller file.')
    try:
        png = image_bytes(content)[0]   # ponytail: decoded once here to refuse in plain words and again in add_reference; one decode if uploads ever get slow
    except ValueError:
        raise
    except Exception:   # not an image at all (Pillow's own errors)
        need(False, 'That file is not a picture this page can read: use a PNG, JPEG or WebP image.')
    words, person = own_words_checked(words), element.get('kind') == 'person'
    to_set = person or (session.get('drawings') or {}).get(element_id, {}).get('status') == 'approved'   # as `_from_footage` decides: a set is made from the picture
    mark, mine = hashlib.sha256(png).hexdigest(), [session['references'][x] for x in _own_pictures(session, element_id)]
    same = next((x for x in mine if x.get('sha256') == mark and (not person or x['id'] == likeness_photo(session, element_id))), None)   # a person: only the photo in use; an earlier one given again is the newest again
    need(same or person or len(mine) < OWN_MAX,
         OWN_MOST[:-1] + f" (`vw visuals reject --ref <one of: {', '.join(x['id'] for x in mine)}> --quote \"<the operator's words>\"`).")

    def keep(session):
        """The words kept with the thing, in the session about to be saved; their line in the run's log."""
        own = (((session.get('round') or {}).get('elements') or {}).get(element_id) or {}).get('from_footage')   # the picture is the reference itself: no set is made
        if own_words(session, user, plan, element_id, words, to_set and not own) and conn is not None:
            from . import runlog
            runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f'thing {element_id}', 'rule': "VW-25 issue 11 (the operator's words with their own picture)",
                                'entry': f"the operator's words with their own picture of {element.get('name') or element_id}", 'by_kind': 'operator', 'by_name': user.get('name') or '',
                                'quote': words, 'request_id': None})
    how = '' if words else f' When the operator said something about the picture, give their words with it: `vw visuals own --element {element_id} --file <file> --words "<their words>"` (the same picture is taken once).'
    if same:   # nothing is stored again; words given with it are kept
        keep(session)
        save_session(store, run, session)
        return {**same, 'duplicate': True, 'next': f'This picture was given already for {element_id}: it is taken once.' + how}
    body = {'request_id': str(uuid.uuid4()), 'element_id': element_id, 'name': str(name or '').strip() or f'own-{element_id}', 'kind': 'supplied', 'subject': element['name']}
    row = add_reference(conn, store, user, run, outputs, body, content)
    session = session_of(store, run, outputs)
    r = session['references'][row['id']]
    r.update(status='approved', approval={'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'sha256': r['sha256'], 'quote': 'Added by the operator on the page'})
    if url:
        r.setdefault('source', {})['url'] = url
    rd = session.get('round') or {}
    slot = (rd.get('elements') or {}).get(element_id)
    if (rd.get('kept') and rd.get('pass') in (2, 'making') and slot and element.get('kind') != 'person' and not slot.get('ignored') and not slot.get('from_footage')
            and not _set_rows(session, element_id, slot.get('set'), ('generating', 'candidate', 'approved'))):   # F2, E3: its set was not made; the own picture is its reference and nothing waits on it
        slot.update(from_footage=True, own=True, verdict='approve', error=None)
        slot.pop('answer', None)
        session.setdefault('golden', {})[element_id] = row['id']
    keep(session)
    save_session(store, run, session)
    if element.get('kind') == 'person' and slot and _set_rows(session, element_id, slot.get('set'), ('generating', 'candidate', 'approved')):   # design/207 (D1): the sheet is made from the newest photo
        return {**r, 'next': f"Your photo is saved for {element_id}. The sheet made before it is out of date: make its sheet again from this photo (`vw visuals round --make {element_id}`)." + how}
    return {**r, 'next': f"Your picture is saved and approved for {element_id}" + ('; its sheet is marked "sources changed": the assistant makes a new one.' if any(
        x.get('kind') == 'sheet' and x.get('sources_changed') and x.get('element_id') == element_id for x in session['references'].values()) else '.')
        + ('' if person else f' It is picture {len(mine) + 1} of {OWN_MAX} of this thing.') + how}


def waiting(session, plan, code, take_rows, budget=None, gate=True):
    """design/97 W1, W3, W4: what waits for the operator's verdict, in film order, each with its label and link: a checked candidate (a reference,
    the style sheet, a still, a start or end image, a sequence once every state is made), a ready take, a drawing spec, a reuse.
    UI change, 11 Nov 2026 (R6 to R9): every item names its kind and carries the card it waits on (its group: an element on References, a shot on
    Pictures and Takes), one item per thing (a set, a spec), and nothing is listed that the operator cannot act on."""
    if not plan:
        return []
    shots = {sh['id']: sh for _, sh in _accepted_shots(plan, session)}
    kinds = {e['id']: e.get('kind') for e in plan.get('elements') or []}
    rd = session.get('round') or {}
    rd_pass = _round_pass(session, rd) if rd.get('kept') else None
    items = []

    def add(at, label, step, group, item, kind):
        if not any(i['label'] == label for _, i in items):
            items.append((at, {'label': label, 'kind': kind, 'step': step, 'group': group, 'item': item, 'link': item_link(code, step, group, item)}))
    title = lambda sh: f" · {sh['title']}" if sh.get('title') else ''
    from . import pictures
    now = datetime.now(timezone.utc)
    # design/217 (C3): a picture Claude checks is offered with its look, or after pictures.PICTURE_LOOK_MINUTES as not checked; the model's `check_pending` no longer holds it
    ready = lambda r: r.get('status') == 'candidate' and r.get('sha256') and (pictures.offered(session, r, plan, now) if pictures.claude_checks(session, r, plan) else not r.get('check_pending'))
    on_takes = lambda sh: route_of(sh) in ('video', 'drawn')   # the tab that shows the shot's card
    for r in session['references'].values():
        sh = shots.get(made_for(session, r) or '')
        if not ready(r):
            continue
        if r.get('kind') == 'style':
            add(-1, 'Graphic style · style sheet', 'pictures', STYLE, r['id'], 'style sheet to approve')
        elif r.get('kind') == 'sheet' and r.get('set') and kept(session):   # design/151 hotfix (VW-18): a set's pictures are judged together on step 2, never one by one (listed per set below)
            continue
        elif r.get('kind') in ('frame', 'supplied', 'web', 'isolated', 'sheet'):
            eid, row = r.get('element_id'), (rd.get('elements') or {}).get(r.get('element_id'))
            # hotfix (VW-24, 18 Nov 2026): in a round of today the operator answered every footage picture at step 1 (a picture not kept is not used), so a candidate
            # left over is never asked again: not while the sets are looked at or rewritten, and not after the round is complete (it came up as a step-6 question in the chat)
            if eid not in kinds or (row and (rd_pass in (2, 'making') or (round_v2(session) and rd_pass in ('looking', 'rewrite', 'complete')))):   # no card answers it: a thing the plan lacks, or a kept round past step 1 (its cards judge the sets)
                continue
            add(-1, f"Reference sheet · {eid}" if r['kind'] == 'sheet' else f"Picture to answer · {eid} · {r['kind']}", 'references', eid, r['id'], 'sheet to approve' if r['kind'] == 'sheet' else 'picture to answer')
        elif sh and route_of(sh) == 'still':
            add(sh['start_frame'], f"Still · {sh['id']}{title(sh)}", 'pictures', sh['id'], r['id'], 'picture to answer')
    if rd_pass in (2, 'making'):   # F3: a ready set is answered while another is being made. One item per set, on its element's card; a set with a whole stored answer waits for Done only
        for eid, row in rd['elements'].items():
            if row.get('ignored') or row.get('from_footage') or eid not in kinds:
                continue
            if _set_rows(session, eid, row.get('set')):
                if not _answered(session, kinds, eid, row):
                    add(-1, f'Set to judge · {eid}', 'references', eid, 'set', 'set to judge')
            elif not _set_rows(session, eid, row.get('set'), ('generating', 'approved')) and not set_cause(session, plan, eid, budget):
                add(-1, f'Set to make · {eid}', 'references', eid, 'make', 'set to make')   # it was not made and nothing stands in its way now
    for sid, sh in shots.items():
        if route_of(sh) == 'graphic_sequence':
            try:
                chain = state_chain(session, sid) or []
            except ValueError:   # two pictures for one step: the page shows the problem
                chain = []
            if chain and len(chain) == len(sh.get('states') or []) and any(r['status'] == 'candidate' for r in chain) and all(ready(r) for r in chain if r['status'] == 'candidate'):   # design/217: each step offered with its look
                add(sh['start_frame'], f"Graphics · {sid}{title(sh)} · {len(chain)} states", 'pictures', sid, chain[-1]['id'], 'graphics to approve')
        spec = sh.get('drawing_spec')
        if spec and (session.get('spec_approvals') or {}).get(sid, {}).get('digest') != spec_digest(spec) and not correction_pending(session, sid, spec):
            add(sh['start_frame'], f'Drawing spec to approve · {sid}{title(sh)}', 'takes' if on_takes(sh) else 'pictures', sid, 'spec', 'drawing spec to approve')   # on its own shot's card, on the tab that shows it
    up = session.get('motion_parts') or {}
    if up.get('picture_key') and not up.get('rejected') and not parts_ready(session):   # design/221 row 1: one card in the chat, before any drawn shot's items
        add(-1, f"Shared parts · {len(up.get('parts') or [])} parts", 'pictures', 'parts', up['sha256'], 'shared parts to approve')
    stills = session.get('motion_stills') or {}   # design/221 row 3: a still end-frame with no failed must; the stills of one diagram in one card when ready together
    gap_of = {sh['id']: g_ for g_, sh in _accepted_shots(plan, session)}
    pend = {sid for sid, st in stills.items() if sid in shots and st.get('frame_key') and not st.get('rejected') and not still_approved(st)
            and not opens_changed(session, continues_from(plan, session, gap_of[sid], shots[sid]), st)}   # the critic's point 7: a still built on an earlier still that was replaced is made again, not asked
    carded = set()   # fix set A1.3: each still on one card, the cards in the order of the film
    for sid in sorted(pend, key=lambda s: shots[s]['start_frame']):
        if sid in carded:
            continue
        mine, linked = diagram_shots(plan, session, gap_of[sid], shots[sid])
        group = sorted({s['id'] for s in mine + linked} | {sid}, key=lambda s: (shots.get(s) or {}).get('start_frame', 0))
        ids = [s for s in group if s not in carded] if len(group) > 1 and set(group) <= pend else [sid]
        carded |= set(ids)
        add(shots[ids[0]]['start_frame'], 'Still end-frames · ' + ', '.join(ids) if len(ids) > 1 else f'Still end-frame · {sid}{title(shots[sid])}', 'takes', ids[0], ','.join(ids),
            'still end-frame to approve')
    for e in plan.get('elements') or []:   # design/111 F10: approved once, on the References step, on the material's own card
        if e.get('material_spec') and not material_approved(session, e) and not correction_pending(session, material_key(e['id']), e['material_spec']):
            add(-1, f"Material spec to approve · {e['id']}", 'references', e['id'], 'specs', 'material spec to approve')
    for item, q in (session.get('questions') or {}).items():   # design/110 rule 0: an open question comes first
        r = session['references'].get(item)
        sh = shots.get(made_for(session, r) if r else item)
        step = 'references' if (r and r.get('kind') in ('frame', 'supplied', 'web', 'isolated', 'sheet')) or (not r and not sh) else 'takes' if sh and on_takes(sh) else 'pictures'
        add(-2, f"Question · {item} · {q['question'][:80]}", step, ((r or {}).get('element_id') or item) if step == 'references' else (sh or {}).get('id') or item, item, 'question to answer')
    for r in session['references'].values():
        if r.get('kind') == 'sheet' and r.get('sources_changed') and r.get('status') != 'rejected':
            add(-1, f"Reference sheet · {r['element_id']} · sources changed", 'references', r['element_id'], r['id'], 'sheet to approve')
    counted = {}   # fix set (SK, 20 Nov 2026): a drawn shot offers only the render pictures._drawn_state counts or holds (its newest, of the bound project and this plan); one made before it is never offered

    def superseded(j, sh):
        if j.get('provider') != 'drawn':
            return False   # design/222: an AI video shot's takes are all read, on purpose
        if j['unit'] not in counted:
            counted[j['unit']] = pictures._drawn_state(session, sh, take_rows, plan)[1]
        return not counted[j['unit']] or str(counted[j['unit']]['id']) != str(j['id'])
    newest = {j['unit']: str(j['id']) for j in take_rows if j.get('provider') == 'video' and j['status'] == 'ready'}   # design/223: of an AI video shot the newest video is the one to answer, whatever was said of the ones before it (they are tabs of its line)
    for j in take_rows:   # design/207 (D2): a reuse no longer waits for the operator (the older way, retired: "Reuse · <shot>", reuse to approve)
        sh, reviews = shots.get(j['unit']), session['reviews'].get(str(j['id'])) or []
        if sh and j['status'] == 'ready' and not superseded(j, sh) and (session['selections'].get(j['unit']) or {}).get('job_id') != str(j['id']) and (newest.get(j['unit']) == str(j['id']) if j.get('provider') == 'video' else not (reviews and reviews[-1]['decision'] == 'rejected')) \
                and not (j.get('provider') == 'video' and j['unit'] in session['selections']):   # design/222: an AI video shot with a take selected is not asked about again
            if held_drawing(session, j['unit']):   # design/221 row 18: a drawing held after its rounds is an early decision, a card in the chat
                add(sh['start_frame'], f"Held drawing · {j['unit']}{title(sh)}", 'takes', j['unit'], str(j['id']), 'held drawing')
            else:
                add(sh['start_frame'], f"Take · {j['unit']}{title(sh)}", 'takes', j['unit'], str(j['id']), 'take to select')
    if gate and round_v2(session) and not pictures.complete(pictures.expected(session, plan, take_rows, now)):   # design/221 row 18: step 6 is shown at the end, on the page (gate False: an answer given on the page that opened)
        early = lambda i: (session['references'].get(i['item']) or {}).get('parent_wanted')   # fix set A2.2: a picture another picture is made from is an early decision: its card, by rule
        items = [(a, i) for a, i in items if not (i['kind'] == 'graphics to approve' or (i['kind'] == 'picture to answer' and i['step'] == 'pictures' and not early(i))
                                                   or (i['kind'] == 'take to select' and route_of(shots.get(i['group']) or {'visual_type': ''}) == 'drawn'))]
    if gate and round_v2(session) and any(i['kind'] == 'take to select' and route_of(shots.get(i['group']) or {'visual_type': ''}) == 'video' for _, i in items):
        from . import takes   # design/222: step 7 is shown at the end, on the page: a ready AI video take is not asked one by one (gate False: an answer given on the page that opened)
        video = lambda i: i['kind'] == 'take to select' and route_of(shots.get(i['group']) or {'visual_type': ''}) == 'video'
        by_id = {str(j['id']): j for j in take_rows}
        if not takes.complete(takes.expected(session, plan, take_rows, now)) or not pictures.complete(pictures.expected(session, plan, take_rows, now)):   # the critic's S1: nor while step 6 is still being made
            items = [(a, i) for a, i in items if not video(i)]
        else:   # the second critic's points 1, 9: the page is open: each take only with its check (a remake too), and none of a shot with an open question
            items = [(a, i) for a, i in items if not video(i) or takes.answerable(session, plan, take_rows, i['group'], by_id[i['item']], now)]   # design/223: the newest video of a shot that waits for an answer (a video the operator spoke of earlier stays on its line)
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


def plan_of(store, run, outputs):
    """Defect 37: the current visual plan, for `vw visuals plan` (a machine without out/visual-plan.json folds a spec correction into it and proposes again)."""
    session = session_of(store, run, outputs)
    need(session.get('current'), 'Propose a visual plan first.')
    entry = next(v for v in session['versions'] if v['plan_digest'] == session['current'])
    return {'version': entry['version'], 'plan_digest': session['current'], 'plan': load_json(store, entry['file']['key'])['document']}


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
        session['accepted'][gid] = {'digest': gap_digest(plan, gap), 'own': gap_own_digest(plan, gap), 'shared': shared_digest(plan), 'version': _version_now(session),   # design/191: the two fingerprints
                                    'choice_id': (session['choice_selections'].get(gid) or {}).get('choice_id'), 'quote': quote, 'by': user['id']}
        (session.get('revisions') or {}).pop(gid, None)   # design/76: accepted after all
        waited = (session.get('shared_pending') or {}).get(gid)
        if waited and waited.get('own') == gap_own_digest(plan, gap):   # design/191: its own shots are as accepted: their references stay bound
            _restamp_bindings(session, gap, waited['digest'], gap_digest(plan, gap))
        for k in ('shared_pending', 'was_accepted'):   # design/191: accepted by itself, whatever waited
            (session.get(k) or {}).pop(gid, None)
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
    (session.get('shared_pending') or {}).pop(gap_id, None)   # design/191: sent back by itself
    session.setdefault('revisions', {})[gap_id] = {'notes': words, 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'digest': gap_digest(plan, gap),
                                                   'own': gap_own_digest(plan, gap)}   # design/191 A2: answered when the gap's own content is proposed changed
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
    if gid in (session.get('shared_pending') or {}):   # design/191: its own shots are as accepted; only the shared rules changed
        out['shared_only'] = True
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
        need(image.format in ('PNG', 'JPEG', 'WEBP'), 'Use a PNG, JPEG or WebP image: an SVG, PDF or design file is not read; export it as a PNG.')
        need(image.width * image.height <= 100_000_000, 'This picture is over 100 megapixels: give a smaller one.')   # before it is decoded
        image.load()
        if image.width * image.height > MAX_PIXELS:   # release 3 (V7): a large camera photo is made smaller on the way in, not refused
            k = (MAX_PIXELS / (image.width * image.height)) ** 0.5
            image = image.resize((max(1, int(image.width * k)), max(1, int(image.height * k))))
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
    if meta.get('kind') in ('frame', 'supplied', 'web', 'isolated') and not kept(session):   # design/110: a sheet made before this picture is stale; the old one stays approved until the new one is (design/151: a set is judged on the page, never re-made from a later picture)
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
    refused = own_picture_refused(element.get('kind'), session, body['element_id']) if body['kind'] == 'supplied' else None   # design/207 (D1): a person's photo, by this door too
    need(not refused, refused)
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


def elements_answer(plan, world):
    """design/73 R1; design/207 (D4): what `vw visuals elements` answers: the elements the reference round takes and where the footage shows each. A graphic is
    drawn and a living extra (kind animal) is carried by its words, so neither is listed; the animals are named in `no_reference`."""
    listed = [e for e in plan['elements'] if e['kind'] not in ('graphic', 'animal')]
    matches = element_matches(plan, world)
    return {'elements': listed, 'graphics': [e['id'] for e in plan['elements'] if e['kind'] == 'graphic'],   # L43: graphics are drawn, never searched
            'no_reference': [e['id'] for e in plan['elements'] if e['kind'] == 'animal'], 'matches': {e['id']: matches[e['id']] for e in listed}}


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


def _search_into(session, user, run, plan, element_id, keywords, quote, results=None, source=''):
    """The search on a loaded session (design/73 R3); `source` names the stock search's added word (design/121 change 5)."""
    need(any(e['id'] == element_id for e in plan['elements']), f'Unknown element {element_id}.')
    quote = said(quote, 'Searched', user)   # design/99 C4: the click is the operator's yes to the web search
    words = str(keywords or '').split()
    need(2 <= len(words) <= 12, 'Keywords are two to twelve words: the thing and its place or trade, nothing else (Google Images is not Google search).')   # R6
    rows = results if results is not None else apify.search_images(' '.join(words), 10)
    sid = digest({'run': str(run['id']), 'element': element_id, 'keywords': ' '.join(words), 'source': source, 'at': datetime.now(timezone.utc).isoformat()})[:12]
    session.setdefault('searches', {})[sid] = {'search_id': sid, 'element_id': element_id, 'keywords': ' '.join(words), 'quote': quote, 'by': user['id'],
                                               'at': datetime.now(timezone.utc).isoformat(), 'results': rows, 'picked': [], **({'source': source} if source else {})}
    return {'search_id': sid, 'element_id': element_id, 'keywords': ' '.join(words), 'results': rows}


STOCK_SOURCE = 'pexels'   # design/121 change 5: the source box's default word; SK chose it after the real test (29 Oct): no watermarks, full size, local scenes


def prefetch_key(run, url):
    return key(run, f"prefetch/{digest({'url': url})[:24]}.png")


def search_rows(store, run, keywords, source=''):
    """design/121 changes 5, 6: before the run's lock, the plain search and, with a source word, the stock search, at once; then every picture of both
    downloaded (eight at a time) and stored, so Save is instant and a picture that will not download is marked on its row before it is ticked.
    {'plain': rows or {'error'}, 'stock': ...}; nothing when the keywords are not two to twelve words (search() refuses them under the lock)."""
    from concurrent.futures import ThreadPoolExecutor
    words, src = ' '.join(str(keywords or '').split()), ' '.join(str(source or '').split())
    if not 2 <= len(words.split()) <= 12:
        return {}
    queries = {'plain': words, **({'stock': f'{words} {src}'} if src else {})}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {k: pool.submit(apify.search_images, q, 10) for k, q in queries.items()}
    out = {}
    for k, f in futures.items():
        try:
            out[k] = f.result()
        except Exception as exc:   # this search's failure; the other may still have come back
            out[k] = {'error': exc.message if isinstance(exc, Problem) else str(exc)}
    found = [r for v in out.values() if isinstance(v, list) for r in v]
    fetched = _download_picks({r['image_url']: r for r in found})
    good = {u: f for u, f in fetched.items() if f[0] is not None}
    with ThreadPoolExecutor(max_workers=8) as pool:   # ponytail: the stored copies are never deleted (about 20 pictures a search); a cleanup at the stage's record if storage grows
        list(pool.map(lambda u: store.put(prefetch_key(run, u), good[u][0], 'image/png'), good))
    for r in found:
        data, _size, used = fetched[r['image_url']]
        r['download'] = used if data is not None else 'failed: ' + '; '.join(used)
    return out


def search(store, user, run, outputs, element_id, keywords, quote, source='', found=None):
    """design/73 R3: a Google Images search for an element, on the operator's yes; design/121: with a source word a stock search beside it, every picture
    downloaded at once; in an open round the thing's row takes the new searches (pass 1 and pass 2 alike), so Done counts them."""
    need(2 <= len(str(keywords or '').split()) <= 12, 'Keywords are two to twelve words: the thing and its place or trade, nothing else (Google Images is not Google search).')
    session = session_of(store, run, outputs)
    need(not is_kept(session, run), 'retired on this film (the kept method): references are made by the kept method (the round makes every set from real photographs); no Google Images search on this film.')
    if found is None:
        found = search_rows(store, run, keywords, source)
    plan = guarded(lambda: current_plan(store, session))
    src = ' '.join(str(source or '').split())
    rd = session.get('round') or {}
    row = rd['elements'].get(element_id) if rd.get('pass') in (1, 2) else None
    errors = {k: v['error'] for k, v in found.items() if isinstance(v, dict)}
    if found and len(errors) == len(found):   # nothing came back: the row says so and still waits
        if row is not None:
            row['error'] = '; '.join(errors.values())
            save_session(store, run, session)
        need(False, 'The search failed: ' + '; '.join(errors.values()) + '. Search again, or choose the footage picture or Ignore this.')
    plain = _search_into(session, user, run, plan, element_id, keywords, quote, results=found['plain']) if isinstance(found.get('plain'), list) else None
    stock = _search_into(session, user, run, plan, element_id, keywords, quote, results=found['stock'], source=src) if isinstance(found.get('stock'), list) else None
    sids = [x['search_id'] for x in (plain, stock) if x]
    for sid in sids:   # the page shows the plain and the stock search side by side
        session['searches'][sid]['pair'] = sids
    if row is not None:
        row.update(search_ids=sids, search_id=sids[0], keywords=' '.join(str(keywords).split()), source=src, verdict='search', error='; '.join(errors.values()) or None, ignored=False)
    save_session(store, run, session)
    first = plain or stock
    return {**first, 'search_ids': sids, 'source': src, 'stock_results': (stock or {}).get('results') or [], **({'errors': errors} if errors else {})}


def pick(store, user, run, outputs, search_id, picks, quote):
    """design/73 R4: the ticked pictures, in the order ticked, each with its note, become web references of the element with their source."""
    session = session_of(store, run, outputs)
    need(not is_kept(session, run), 'retired on this film (the kept method): references are made by the kept method; there are no web picks on this film.')
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


def _fetch_picks(store, run, rows):
    """design/121 change 6: a picture downloaded at its search is read from the store; the rest are downloaded now, as before."""
    out, rest = {}, {}
    for k, row in rows.items():
        pk = prefetch_key(run, row['image_url'])
        if row.get('download') in ('picture', 'thumbnail') and store.exists(pk):
            data = store.get(pk)
            out[k] = (data, image_bytes(data)[1], row['download'])
        else:
            rest[k] = row
    return {**out, **_download_picks(rest)}


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
        fetched = _fetch_picks(store, run, {(search_id, row['n']): row for row, _ in chosen})   # design/121 change 6
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
    s['picked'] = list(dict.fromkeys((s.get('picked') or []) + [r['source']['n'] for r in made]))   # design/126 U3: a picture saved on its own adds to the earlier saves of the search
    s['failed'] = failed
    return {'search_id': search_id, 'references': made, 'failed': failed}


# ---------- design/79: the reference round, every element at once, two passes on one page ----------

ANIMAL_NO_SHEET = ('{eid} is an animal: a living extra has no reference sheet. It is carried by its words: write its exact kind and size in the plan '
                   '(description and size); the server puts them in every prompt that shows it. Leave it out of the round.')   # design/207 (D4)

def round_start(store, user, run, outputs, elements, conn=None):
    """The assistant's one-shot preparation: for each element its grabbed footage frames and the keywords it would search; the page shows them all.
    design/151: on a new film (from design/139 on) with no older references the round is the kept one: each row carries its prompt (a thing's subject
    block, a person's why line); pass 1 shows the frames; Done makes every set silently; the sets are judged in one shot."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    kinds = {e['id']: e['kind'] for e in plan['elements']}
    need(isinstance(elements, list) and elements, 'The round lists the elements: [{element_id, frames, keywords}].')
    kept_ = mark_kept(session, run)
    if kept_:
        distinct_people(plan)
    old = session.get('round') or {}
    if kept_ and old.get('kept') and old.get('pass') != 1:   # hotfix 4 Nov 2026 (VW-18): a re-post after Done never wipes the round and its sets
        return _round_merge(conn, store, user, run, outputs, session, plan, kinds, elements)
    if kept_ and (old.get('v') == 2 or (not old and ROUND_V == 2)):   # design/211: a film with no round gets a v2 round (each row a proposal, every frame with its look); an older round still at step 1 stays an older round
        from . import ref_sets
        return ref_sets.start(conn, store, user, run, session, plan, kinds, elements)
    rows = {}
    for row in elements:
        eid = (row or {}).get('element_id')
        need(eid in kinds, f'Unknown element {eid}.')
        need(kinds[eid] != 'graphic', f'{eid} is a graphic: drawn from the plan, never referenced.')
        need(kinds[eid] != 'animal', ANIMAL_NO_SHEET.format(eid=eid))
        frames = list((row or {}).get('frames') or [])
        for fid in frames:
            r = session['references'].get(fid)
            need(r and r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved'), f'{fid} is not a footage frame of {eid}.')
        if not frames:   # the element's footage frames already grabbed count, whether or not the row names them
            frames = [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved')]
        rows[eid] = {'frames': frames, 'keywords': str((row or {}).get('keywords') or '').strip(), 'verdict': None, 'search_id': None, 'error': None}
        if kept_:
            prompt = ' '.join(str((row or {}).get('prompt') or '').split())
            need(prompt, f'{eid}: give its prompt (the subject block of a thing: what the picture must represent; the why line of a person).')
            rows[eid].update(prompt=prompt, corrections=[], set=None, round=0)
    made = {eid for gap in plan['gaps'] for sc in all_scenes(gap) for sh in sc['shots'] if sh.get('visual_type') != 'footage' for eid in sh.get('element_ids') or []}
    missing = [eid for eid, k in kinds.items() if k == 'person' and eid not in rows and eid in made] if kept_ else []   # design/207 (D3): every person a picture is made of; one seen only in their own footage needs none
    need(not missing, f"Every person gets a character sheet: add a row for {', '.join(missing)} (element_id and the why line; no picture is needed, the sheet is made from the description).")
    session['round'] = {'pass': 1, 'at': datetime.now(timezone.utc).isoformat(), 'by': user['id'], 'elements': rows, 'quote': None, **({'kept': True} if kept_ else {})}
    save_session(store, run, session)
    return {'pass': 1, 'elements': len(rows), **({'kept': True} if kept_ else {})}


def _from_footage(session, plan, rd):
    """SK, 5 Nov 2026 (VW-18): a thing the operator approved from the footage keeps that picture as its reference; no AI set is made, no money spent. Its golden
    picture is the first approved frame of its row. A person's footage picture serves the description only (design/124 decision 5), so a person still gets the sheet."""
    kinds = {e['id']: e.get('kind') for e in plan.get('elements') or []}
    out = []
    for eid, row in rd['elements'].items():
        if row.get('ignored') or kinds.get(eid) == 'person' or row.get('set'):
            continue
        if rd.get('v') == 2 and row.get('clean'):
            continue   # design/211: "Make a clean set from it": a set is made from the footage pictures
        if (session.get('drawings') or {}).get(eid, {}).get('status') == 'approved':
            continue   # design/200: a thing with an approved drawing set gets its set, made from its footage picture and the drawings; without one, the footage picture is the reference as before
        approved = [fid for fid in row.get('frames') or [] if (session['references'].get(fid) or {}).get('status') == 'approved']
        if rd.get('v') == 2:   # design/211: the frames that have a look, in view order (one marked "not this" is rejected): the first is the golden picture
            from . import ref_find
            approved = [f['ref'] for f in ref_find.frames_of(session, eid) if (session['references'].get(f['ref']) or {}).get('status') == 'approved']
        mine = [] if approved else _own_pictures(session, eid)   # F2 (11 Nov 2026): an approved own picture is the reference, as a footage picture is
        if not approved and not mine:
            continue
        row.update(from_footage=True, verdict='approve', error=None, **({'own': True} if mine else {}))
        approved = approved or mine
        session.setdefault('golden', {})[eid] = approved[0]
        out.append(eid)
    return out


def _round_merge(conn, store, user, run, outputs, session, plan, kinds, elements):
    """design/151 hotfix (VW-18, 4 Nov 2026): a kept round past step 1 keeps its sets when the assistant posts rows again; the rows name the elements whose set
    was not made (refused before the call, or failed): their prompt and frames are replaced, the error cleared, and the set is made at once. An element that has
    its set is refused by name: the operator judges it on step 2 (No or Correct it makes it again). Returns what round_done returns, plus the elements merged."""
    if round_v2(session):   # design/211: a second send of the round file never orders a set
        from . import ref_sets
        return ref_sets.merge(conn, store, user, run, session, plan, kinds, elements)
    rd = session['round']
    merged = []
    for row in elements:
        eid = (row or {}).get('element_id')
        need(eid in kinds, f'Unknown element {eid}.')
        need(kinds[eid] != 'graphic', f'{eid} is a graphic: drawn from the plan, never referenced.')
        need(kinds[eid] != 'animal', ANIMAL_NO_SHEET.format(eid=eid))
        cur = rd['elements'].get(eid) or {}
        has = cur.get('set') and _set_rows(session, eid, cur['set'], ('generating', 'candidate', 'approved'))
        need(not has, f"{eid} has its set already: the round is past step 1, so judge it on step 2 (No or Correct it makes it again); a new round file never replaces a set.")
        need(not cur.get('from_footage'), f"{eid} is referenced by its approved footage picture: no AI set is made for it.")
        prompt = ' '.join(str((row or {}).get('prompt') or '').split())
        need(prompt, f'{eid}: give its prompt (the subject block of a thing: what the picture must represent; the why line of a person).')
        frames = list((row or {}).get('frames') or [])
        for fid in frames:
            r = session['references'].get(fid)
            need(r and r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved'), f'{fid} is not a footage frame of {eid}.')
        if not frames:
            frames = [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved')]
        rd['elements'][eid] = {**cur, 'frames': frames, 'keywords': '', 'prompt': prompt, 'corrections': list(cur.get('corrections') or []), 'set': None, 'round': int(cur.get('round') or 0),
                              'verdict': 'approve', 'ignored': False, 'search_id': None, 'error': None}
        merged.append(eid)
    for eid in merged:
        for fid in rd['elements'][eid]['frames']:
            r = session['references'][fid]
            if r.get('status') == 'candidate':
                r['status'] = 'approved'
    save_session(store, run, session)
    queued, errors = _queue_sets(conn, store, user, run, outputs, merged)
    session = session_of(store, run, outputs)
    rd = session['round']
    rd['pass'] = 'making' if queued else rd['pass']
    save_session(store, run, session)
    return {'pass': _round_pass(session, rd), 'kept': True, 'merged': merged, 'queued': queued, 'errors': errors, 'elements': len(rd['elements']),
            'cost_inr': round(len(queued) * image_price_inr(run, provider='gemini') * SET_MAX, 2)}


def _set_rows(session, eid, set_id, statuses=('candidate',)):
    return [r for r in session['references'].values() if r.get('kind') == 'sheet' and r.get('element_id') == eid and r.get('set') == set_id and r.get('status') in statuses]


def _round_pass(session, rd):
    """design/151: a kept round at 'making' is at pass 2 once no set of it is still being made."""
    if (rd or {}).get('v') == 2:   # design/211: 1, 'making', 'looking', 'rewrite', 2, 'complete'
        from . import ref_sets
        return ref_sets.state(session, rd)
    if not rd or rd.get('pass') != 'making':
        return (rd or {}).get('pass')
    making = any(_set_rows(session, eid, r.get('set'), ('generating',)) for eid, r in rd['elements'].items() if r.get('set') and not r.get('ignored'))
    return 'making' if making else 2


def _queue_sets(conn, store, user, run, outputs, eids):
    """design/151: one set per element, silently, through generate_image (its gates, the cap, the log); an element refused is recorded on its row and the
    rest go on; the cap stops the lot. Returns (queued, errors)."""
    queued, errors = [], {}
    for eid in eids:
        session = session_of(store, run, outputs)
        row = session['round']['elements'][eid]
        plan = guarded(lambda: current_plan(store, session))
        element = next(e for e in plan['elements'] if e['id'] == eid)
        n = int(row.get('round') or 0) + 1
        prompt = row['prompt'] + ''.join(f"\nThe operator's correction: {c.rstrip('.')}." for c in row.get('corrections') or [])
        if round_v2(session):   # design/211: the server writes the whole request (ref_sets.set_request); the operator's words are placed there, nothing is appended here
            prompt = row['prompt']
            from . import ref_sets
            if element.get('kind') == 'place' and 'things' not in row:   # design/216b: a place waits for Claude's list of its things; never ordered on a guess
                row.pop('held', None)
                row['things_due'] = True
                save_session(store, run, session)
                continue
            if row.pop('things_due', None):   # it has its list: it is never asked for again, so it cannot be ordered a second time
                save_session(store, run, session)
            waits = ref_sets.pending_things(plan, session, eid)
            if waits:   # design/216 (the critic's points 1 and 2): a place is held until its things' sets are approved; ref_sets.release orders it then
                row['held'] = [t['id'] for t in waits]
                save_session(store, run, session)
                continue
            if ref_sets.makes(session, eid, row) >= ref_sets.MAKES_MAX:   # design/211 review, M1: every order of a set passes here, so the limit holds whatever way it comes
                errors[eid] = ref_sets.MAKES_LIMIT.format(eid=eid, max=ref_sets.MAKES_MAX)
                continue
        body = {'element_id': eid, 'kind': 'sheet', 'name': f'set-{eid}-r{n}', 'subject': element.get('name') or eid, 'prompt': prompt, 'parents': [],
                # defect 55 (VW-24): a round posted from 0.109.2 (`own_ids`) adds its own `at`, so a round started again never stores its pictures under an earlier round's keys;
                # the same on a retry inside the round. A round posted before keeps its ids.
                'request_id': str(uuid.uuid5(uuid.NAMESPACE_OID, f"{run['id']}-set-{eid}-{n}" + (f"-{session['round']['at']}" if session['round'].get('own_ids') else '')))}
        try:
            out = generate_image(conn, store, user, run, outputs, body, **({'round_set': True} if round_v2(session) else {}))
        except (Problem, ValueError) as exc:
            errors[eid] = getattr(exc, 'message', None) or str(exc)
            if getattr(exc, 'code', '') == 'VISUALS_CAP':
                if round_v2(session):   # design/213: the limit of a v2 round is said with no amount
                    errors[eid] = ref_sets.LIMIT_PLAIN
                for rest in eids[eids.index(eid) + 1:]:
                    errors[rest] = errors[eid]
                break
            continue
        session = session_of(store, run, outputs)
        session['round']['elements'][eid].update(set=out['reference_id'], round=n, error=None,
                                                 made={'at': datetime.now(timezone.utc).isoformat(), 'specs': {m['id']: spec_digest(m['material_spec']) for m in materials_of(plan, eid)},
                                                       'photo': likeness_photo(session, eid) if element.get('kind') == 'person' else None})   # E14: the specs it was made with; design/207: a person's photo it was made from
        if round_v2(session):   # design/211: the plan's words and the place it was made with
            from . import ref_sets
            session['round']['elements'][eid]['made']['fp'] = ref_sets.fp(plan, session, element)
        save_session(store, run, session)
        queued.append(eid)
    if errors:
        session = session_of(store, run, outputs)
        for eid, msg in errors.items():
            session['round']['elements'][eid]['error'] = msg
        save_session(store, run, session)
    return queued, errors


# VW-25 issue 13 (25 Nov 2026): each set is judged by its own state. The round's state (`ref_sets.state`) only says whose turn it is and closes the round.
NOT_AT_SETS = 'The reference round is not at step 2: there is no set to answer now.'
SET_WAITS = {'making': '{name}: its set is being made. An answer is taken when it is back.',
             'looking': '{name}: the assistant is looking at its set. An answer is taken after that.',
             'rewrite': '{name}: its answer is recorded. Its set is made again from those words; the new set is answered when it is back.'}
SET_REMADE = '{name}: its set was made again after this answer was given. The answer was for the earlier pictures, so it is not recorded. Look at the new set and answer it.'
SET_RECORDED = '{name}: its answer is recorded already.'


def _set_wait(session, eid, row):
    """What one set waits for before the operator's answer on it is recorded: 'making' (it is being made), 'rewrite' (its answer is recorded and its
    request is written again), 'looking' (it is made and the assistant's look is not recorded). None: it is ready, or it was never made."""
    if _set_rows(session, eid, row.get('set'), ('generating',)):
        return 'making'
    if not round_v2(session):
        return None
    from . import ref_sets
    return 'rewrite' if row.get('rewrite_due') else 'looking' if _set_rows(session, eid, row.get('set')) and not ref_sets.looked(session, eid, row) else None


def set_gone(session, plan, item_id):
    """An answer to a set's card that is not open any more (`set:<thing>:<set>`), for the page and the chat alike: (True, SET_RECORDED) when the answer
    of that set is recorded already (the same answer sent twice); (False, SET_REMADE) when the thing's set was made again since, so the answer is of
    the pictures before; None for any other card."""
    kind, _, rest = str(item_id or '').partition(':')
    eid, _, sid = rest.rpartition(':')
    row = ((session.get('round') or {}).get('elements') or {}).get(eid) or {}
    if kind != 'set' or not row.get('set'):
        return None
    name = next((e.get('name') for e in (plan or {}).get('elements') or [] if e['id'] == eid), None) or eid
    if sid in [h.get('set') for h in row.get('history') or []] + [(row.get('rewrite_due') or {}).get('set')] or (sid == row['set'] and _set_rows(session, eid, sid, ('approved',))):
        return True, SET_RECORDED.format(name=name)
    return (False, SET_REMADE.format(name=name)) if sid != row['set'] else None


def round_sets(store, user, run, outputs, verdicts, quote, conn=None, partial=False, each=False):
    """design/151: the one-shot verdicts on the sets: Yes (the set approved; a thing's golden picture is the ticked one, Q2; a person's is picture 1),
    No or Correct it (the set rejected with the words; made again, the correction in the prompt, never from a rejected picture). Complete when every
    element is approved or ignored; 'making' while any set is made again.
    UI change, 11 Nov 2026 (R13, R15): without partial (the chat tool) every set needs its verdict, as before, and a whole answer stored with
    set_answer stands where the call sends none. partial (the page): the page sends the stored answers the operator saw in its confirmation; exactly
    those are recorded, every other set is left as it is (a stored answer too) and the round stays on step 2 for them.
    Follow-up, 11 Nov 2026: at the spend cap a Yes is still recorded (it costs nothing); a No or Correct it whose remake the cap does not allow is
    held: its set and its whole answer stay as they are, stored, and wait (returned in `held` with the reason). A round where nothing is left to
    judge (every other set approved, the rest set aside) completes.
    VW-25 issue 13 (25 Nov 2026): a set that is ready is answered at any time. One that is not (`_set_wait`) is left as it is, a stored answer too, and
    an answer sent for it comes back in `waiting` with what it waits for; the round stays open for it. `already`: the sets whose answer was recorded
    before. `each` (the page and the chat, `chat_flow.flush_sets`): an answer with a fault of its own comes back in `refused` and the other answers are
    still recorded; without it one fault refuses the send, as before. An answer stored on the pictures before (the set was made again since) is never
    recorded (`_answer_of`); the set's own line says so until it is answered (SET_REMADE). Retired: the refusal of the whole send while one set is
    being made, has no look, or the round is with the assistant."""
    session = session_of(store, run, outputs)
    rd = session.get('round')
    v2 = round_v2(session)
    if v2:
        from . import ref_sets
    need(rd and rd.get('kept') and _round_pass(session, rd) in ((2, 'making', 'looking', 'rewrite') if v2 else (2, 'making')), NOT_AT_SETS)
    quote = said(quote, 'Sets done', user)
    verdicts = dict(verdicts or {})
    plan = guarded(lambda: current_plan(store, session))
    kinds = {e['id']: e['kind'] for e in plan['elements']}
    name = lambda eid: next((e.get('name') for e in plan['elements'] if e['id'] == eid), None) or eid
    # hotfix 2, 11 Nov 2026 (VW-19): a set approved in an earlier pass is settled; it needs no verdict again (its pictures are approved, no longer candidates)
    settled = {eid for eid, r in rd['elements'].items() if r.get('verdict') == 'yes' and _set_rows(session, eid, r.get('set'), ('approved',))}
    active = [eid for eid, r in rd['elements'].items() if not r.get('ignored') and not r.get('from_footage') and eid not in settled]   # a footage element was done at step 1
    if v2:   # design/211: a thing whose set waits for the second go, or that is back with the operator after a second send, is no set to judge
        open_ = ref_sets.rest_of(rd) + [eid for eid, r in rd['elements'].items() if r.get('reopened')]
        active = [eid for eid in active if eid not in open_]
    refused = {}
    waits = {eid: w for eid in active for w in [_set_wait(session, eid, rd['elements'][eid])] if w}
    waiting = {eid: SET_WAITS[w].format(name=name(eid)) for eid, w in waits.items() if (verdicts.get(eid) or {}).get('verdict')}
    already = [eid for eid in verdicts if eid in settled]
    active = [eid for eid in active if eid not in waits]
    need(partial or not waiting, next(iter(waiting.values()), ''))   # the chat tool, which sends its sets as one whole: a set that is not ready is refused by name, with what it waits for
    for eid in active if not partial else []:
        if not (verdicts.get(eid) or {}).get('verdict') and _answered(session, kinds, eid, rd['elements'][eid]):
            verdicts[eid] = _answered(session, kinds, eid, rd['elements'][eid])
    unanswered = [eid for eid in active if not (verdicts.get(eid) or {}).get('verdict')] if partial else []
    active = [eid for eid in active if eid not in unanswered]
    need(active or not unanswered or waiting or already, 'No set has an answer yet: there is nothing to record.')
    budget = _set_budget(run, session, visuals_spend(conn, run)) if conn is not None else None
    room = int((budget[1] - budget[0] + 1e-9) // budget[2]) if budget and budget[2] > 0 else None   # how many sets the cap still allows
    for eid in list(active):
        r, v = rd['elements'][eid], verdicts.get(eid) or {}
        try:
            need(v.get('verdict') in ('yes', 'no', 'correct'), f'{eid}: a verdict is required: yes, no, or correct it.')
            rows = _set_rows(session, eid, r.get('set'))
            if v['verdict'] == 'yes':
                need(rows, f"{eid}: its set did not come back ({r.get('error') or 'no picture'}); say no or correct it to make it again.")
                need(not (kinds.get(eid) == 'person' and (r.get('made') or {}).get('photo') and not likeness_of(session, eid)),   # design/207 (D1): for the page and the chat alike
                     f"{eid}: this set was made from the person's photo and the permission is no longer recorded: it cannot be approved. Make it again (`vw visuals round --make {eid}`); it is then made from the description.")
                if kinds.get(eid) != 'person':
                    need(v.get('golden'), f'{eid}: tick the golden picture of its set, the one every shot of {eid} starts from.')
                if v.get('golden') and (kinds.get(eid) != 'person' or (session['references'].get(v['golden']) or {}).get('kind') == 'supplied'):   # U19: or the operator's own picture of this element
                    need(_golden_ok(session, kinds.get(eid), eid, v['golden'], rows), f"{eid}: the starting picture chosen is not a picture of its set now (the set was made again since): choose it again.")   # R19: no picture id in a message
            if v['verdict'] == 'correct':
                need(str(v.get('words') or '').strip(), f'{eid}: say what to correct.')
            if v2 and v['verdict'] != 'yes' and v.get('all') and str(v.get('words') or '').strip():   # design/215 (change 5): checked once, here, before anything is recorded: later requests carry these words without reading them again
                try:
                    library.check_prompt(' '.join(str(v['words']).split()), placed=False)
                except ValueError as exc:
                    need(False, f'{eid}: these words cannot be kept for every picture: {exc}')
        except (ValueError, Problem) as exc:   # VW-25 issue 13: on the page and in the chat one faulty answer never stops the others; it is refused by its own name
            if not each:
                raise
            refused[eid] = str(getattr(exc, 'message', '') or exc)
            active.remove(eid)
    stamp = {'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'quote': quote}
    again, held, against = [], {}, []
    for eid in active:
        r, v = rd['elements'][eid], verdicts[eid]
        rows = _set_rows(session, eid, r.get('set'))
        if v2 and v['verdict'] != 'yes' and ref_sets.makes(session, eid, r) >= ref_sets.MAKES_MAX:   # design/211: three makes: the answer is held, not recorded
            r.pop('answer', None)
            held[eid] = ref_sets.MAKES_LIMIT.format(eid=eid, max=ref_sets.MAKES_MAX)
            continue
        if v['verdict'] != 'yes' and room is not None and len(again) >= room:   # the cap: nothing is rejected and nothing queued; the answer waits, stored
            r['answer'] = {'verdict': v['verdict'], 'golden': None, 'words': ' '.join(str(v.get('words') or '').split()), 'set': r.get('set'), 'by': user['id'], 'at': stamp['at'],
                           **({'all': True} if v.get('all') else {})}
            held[eid] = ref_sets.LIMIT_PLAIN if v2 else f'the spend cap of ₹{budget[1]:,.0f} is reached (₹{budget[0]:,.0f} spent): the set is not made again; its answer is kept and waits'   # design/213: no amount in a v2 round
            continue
        r['verdict'] = v['verdict']
        r.pop('answer', None)   # recorded: nothing stored is left behind
        if v['verdict'] == 'yes':
            if v2 and ref_sets.approved_against(eid, r):   # SK, 19 Nov 2026: an approval beside a check that did not say "use" is said in the decision log
                against.append((eid, ref_sets.approved_against(eid, r)))
            for x in rows:
                x.update(status='approved', approval={**stamp, 'sha256': x.get('sha256')})
                _feedback_image(session, run, user, x, 'pass', quote, '')
            session.setdefault('golden', {})[eid] = v['golden'] if kinds.get(eid) != 'person' or _own_golden(session, eid, v.get('golden')) else min(rows, key=lambda x: int(x.get('set_n') or 1))['id']
            continue
        words = ' '.join(str(v.get('words') or '').split())
        for x in rows:
            x.update(status='rejected', rejection={**stamp, 'notes': words})
            _feedback_image(session, run, user, x, 'reject', quote, words)
        if v2:   # design/211: nothing is ordered here: Claude rewrites the request from these words first (ref_sets.round_rewrite); the earlier request is kept
            r.setdefault('operator_words', []).extend([words] if words else [])
            if words and v.get('all'):   # design/215 (change 5): kept for the thing, in the same save as the answer: every later request of it carries them (checked above)
                ref_sets.correction_kept(session, user, eid, words, r.get('set'))
            r['rewrite_due'] = {'words': words, 'set': r.get('set'), 'at': stamp['at']}
        elif words:
            r.setdefault('corrections', []).append(words)
        again.append(eid)
    rd['quote'] = quote
    save_session(store, run, session)
    if against and conn is not None:   # the log is a record: it never stops the approval, and a failed insert stays inside its own savepoint
        try:
            from contextlib import nullcontext
            from . import runlog
            with (conn.transaction() if hasattr(conn, 'transaction') else nullcontext()):
                for eid, line in against:
                    runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f'set {eid}', 'rule': "References step 2: an approval beside Claude's check",
                                        'entry': line, 'by_kind': 'operator', 'by_name': user.get('name') or '', 'quote': quote, 'request_id': None})
        except Exception as exc:   # noqa: BLE001
            logging.getLogger('vw2.visuals').warning('decision log not written for run %s: %s', run.get('id'), exc)
    queued, errors = _queue_sets(conn, store, user, run, outputs, again) if again and not v2 else ([], {})
    if v2:   # design/216: a place held for these things is ordered in the same call as their approval
        queued = queued + ref_sets.release(conn, store, user, run, outputs)
    session = session_of(store, run, outputs)
    rd = session['round']
    left = unanswered + [eid for eid in again if eid not in queued] + list(held)   # still on step 2: the sets with no answer yet, a set that could not be made again (the page offers Make it now), a remake the cap holds
    if v2:
        left += ref_sets.rest_of(rd) + [eid for eid, r in rd['elements'].items() if r.get('reopened') or r.get('held') or r.get('things_due')]   # design/216: a held place is not judged yet; design/211: the round stays open while sets wait for the second go, or a thing is back with the operator
    left += list(waits) + list(refused)   # VW-25 issue 13: the round closes only when no set is being made, unlooked or waiting for its rewrite, and every set has its answer
    rd['pass'] = 'making' if queued or 'making' in waits.values() else (2 if left else 'complete')
    save_session(store, run, session)
    return {'pass': _round_pass(session, rd) if v2 else rd['pass'], 'queued': queued, 'errors': errors, 'approved': [eid for eid in active if verdicts[eid]['verdict'] == 'yes'], 'held': held, **({'unanswered': unanswered} if partial else {}),
            **{k: x for k, x in (('waiting', waiting), ('refused', refused), ('already', already)) if x},
            **({'rewrite': [eid for eid in again], 'then': ref_sets.then_of(session) or (_round_complete_words() if _round_pass(session, rd) == 'complete' else None)} if v2 else {})}


def _round_complete_words():
    """design/211 (the merger): the one sentence for a round that this answer completed, the page's own (page_flow.ROUND_NEXT), so the chat tool says it too."""
    from . import page_flow
    return page_flow.ROUND_NEXT


# ---------- UI change, 11 Nov 2026: one answer of step 2 stored as it is made (R13); one set that was not made, made now (R17, R18) ----------

def _answer_of(row):
    """The stored answer of step 2, when it still fits: it was made on the set the row holds now. Returns (answer or None, discarded)."""
    a = row.get('answer')
    if not a:
        return None, False
    if a.get('set') != row.get('set'):
        return None, True
    return {**{k: a.get(k) for k in ('verdict', 'golden', 'words')}, **({'all': True} if a.get('all') else {})}, False


def _answered(session, kinds, eid, row):
    """The stored answer when it is a whole one: No; Yes (with the starting picture on a thing); Correct it with its words. Else None."""
    a = _answer_of(row)[0] or {}
    v = a.get('verdict')
    whole = v == 'no' or (v == 'correct' and a.get('words')) or (v == 'yes' and (kinds.get(eid) == 'person' or any(x['id'] == a.get('golden') for x in _set_rows(session, eid, row.get('set'))) or _own_golden(session, eid, a.get('golden'))))
    return a if whole else None


def _round_row(session, element_id, where, answering=False):
    """The row of one element in a kept round that is at `where`; refused in plain words otherwise."""
    rd = session.get('round')
    step = _round_pass(session, rd) if rd and rd.get('kept') else None
    need(step in where, NOT_AT_SETS if answering or where == (2,) else 'The reference round is not at the step where its sets are made: there is nothing to make now.')
    row = rd['elements'].get(element_id)
    need(row, f'{element_id} is not in the reference round.')
    need(not row.get('ignored'), f'{element_id} was set to Ignore at step 1: it has no set.')
    need(not row.get('from_footage'), f'{element_id} is referenced by its footage picture: it has no set.')
    return row


def set_answer(store, user, run, outputs, element_id, verdict=None, golden=None, words='', all=False):
    """R13: one answer of step 2, stored as it is made and not recorded until Done: the starting picture, Yes / No / Correct it, the words. It is sent whole
    at every change, so the later writer wins. An answer whose starting picture belongs to a set made again since is discarded, not stored."""
    session = session_of(store, run, outputs)
    v2 = round_v2(session)
    row = _round_row(session, element_id, (2, 'making', 'looking', 'rewrite') if v2 else (2, 'making'), answering=True)
    need(verdict in (None, 'yes', 'no', 'correct'), f'{element_id}: the answer is Yes, No or Correct it.')
    rows = _set_rows(session, element_id, row.get('set'))
    need(rows or not _set_rows(session, element_id, row.get('set'), ('generating',)), f'{element_id}: its set is being made: there is nothing to answer yet.')
    need(rows or not row.get('rewrite_due'), SET_WAITS['rewrite'].format(name=element_id))   # VW-25 issue 13: what it waits for, by name
    need(rows, f'{element_id}: its set is approved already; it needs no answer.' if _set_rows(session, element_id, row.get('set'), ('approved',)) else f'{element_id}: its set was not made: there is nothing to answer yet.')
    if v2:   # design/211: no answer before the look; after three makes "No" and "Correct it" are held
        from . import ref_sets
        need(ref_sets.looked(session, element_id, row), ref_sets.SET_NO_LOOK.format(eid=element_id))
        need(verdict not in ('no', 'correct') or ref_sets.makes(session, element_id, row) < ref_sets.MAKES_MAX, ref_sets.MAKES_LIMIT.format(eid=element_id, max=ref_sets.MAKES_MAX))
    plan = guarded(lambda: current_plan(store, session))
    kind = next((e.get('kind') for e in plan['elements'] if e['id'] == element_id), None)
    supplied = (session['references'].get(golden or '') or {}).get('kind') == 'supplied'   # U19: the operator's own picture
    golden = (golden or None) if kind != 'person' or supplied else None   # a person's full-length front picture is taken by the server
    if golden and not _golden_ok(session, kind, element_id, golden, rows):
        row.pop('answer', None)
        save_session(store, run, session)
        return {'element_id': element_id, 'stored': False, 'discarded': True, 'next': f'{element_id}: made again since; judge the new set.'}
    row['answer'] = {'verdict': verdict, 'golden': golden, 'words': str(words or '').strip(), 'set': row.get('set'), 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(),
                     **({'all': True} if all and v2 and verdict == 'correct' else {})}   # design/215: the correction applies to every picture of the thing
    save_session(store, run, session)
    return {'element_id': element_id, 'stored': True, 'answer': _answer_of(row)[0]}


def _fail_cause(ref):
    from . import ref_sets
    return ref_sets.fail_of(ref)['cause']


def _fail_words(error, ref=None):
    """F4, E13: why a picture's call failed, in one plain sentence for the card; the full text stays in the log.
    design/211: `ref`, the failed picture of a v2 round's set: the sentence names the provider and the model the job called, and the real cause."""
    if ref is not None:
        from . import ref_sets
        return ref_sets.fail_of(ref)['text']
    e = str(error or '').lower()
    if 'returned no picture' in e:
        return 'The model returned no picture.'
    if 'rejected the request' in e or 'refused' in e:
        return 'The picture service refused the request.'
    if 'timeout' in e or 'timed out' in e:
        return 'The picture service did not answer in time.'
    return 'The picture could not be made.'


def _plain(text):
    """R19: a refusal written for the assistant, as the operator reads it: no tool command."""
    text = re.sub(r'\s*\((?:or\s+)?`[^`]*`\)', '', str(text or ''))
    return re.sub(r'\s{2,}', ' ', re.sub(r',?\s*(?:\b(?:or|with)\s+)?`[^`]*`', '', text)).strip()


def _set_budget(run, session, spend):
    """(spent, cap, the price of one set) for set_cause."""
    return spend['spent_inr'], cap_of(session), image_price_inr(run, provider='gemini') * SET_MAX


RULE_RETIRED = 'The rule that held this set back no longer applies to a set: it can be made now.'   # design/215: a refusal stored by "measure it first" or "the plan cites the footage"


RETIRED_FOR_SETS = ('size still unknown', 'cites the footage',   # design/215 (R3, R4)
                    'with no landmark and measured distance', 'says nothing a picture can show')   # defect 54: a set's request is the plan's own words; design/216 (B3): its stored refusal no longer holds the set


def rule_retired(session, error):
    return round_v2(session) and any(x in str(error or '') for x in RETIRED_FOR_SETS)


def with_corrections(session, plan, prompt, element_ids):
    """design/215 (change 5): a picture's prompt with the operator's corrections of the things it shows, each said once."""
    from . import ref_sets
    for eid in dict.fromkeys(element_ids):
        line = ref_sets.corrections_line(session, plan, eid)
        if line:
            prompt = with_composed(prompt, line)
    return prompt


def set_cause(session, plan, element_id, budget=None):
    """R12, R18: why the set of one element would not be made now, in the operator's words: its material spec is not approved (or its correction
    waits), a size is not measured, the spend cap. None when nothing stands in its way. The same three gates generate_image holds."""
    element = next((e for e in plan.get('elements') or [] if e['id'] == element_id), None)
    if not element:
        return None
    for m in materials_of(plan, element_id):
        if correction_pending(session, material_key(m['id']), m['material_spec']):
            return {'kind': 'spec', 'element_id': m['id'], 'pending': True, 'text': f"the material spec of {m.get('name') or m['id']} was corrected: the assistant revises it, then you approve it"}
        if not material_approved(session, m):
            return {'kind': 'spec', 'element_id': m['id'], 'text': f"the material spec of {m.get('name') or m['id']} is not approved"}
    unknown = [d for d in element.get('size') or [] if d.get('value') is None]
    if unknown and not round_v2(session) and element.get('kind') not in ('person', 'graphic', 'style') and any(   # design/215 (R4): not for a set of a v2 round
           
            r.get('kind') == 'frame' and r.get('element_id') == element_id and r.get('status') == 'approved' for r in session['references'].values()):   # design/119 rule 8, design/151 Q6
        return {'kind': 'size', 'element_id': element_id, 'text': f"a size of {element.get('name') or element_id} is not measured yet ({unknown[0].get('part')} {unknown[0].get('measure')}): the assistant measures it from the approved footage picture"}
    if budget and budget[0] + budget[2] > budget[1] + 1e-9:
        return {'kind': 'cap', 'element_id': element_id, 'text': f'the spend cap is reached: ₹{budget[0]:,.0f} spent of ₹{budget[1]:,.0f}'}
    return None


def _photo_changed(session, plan, element_id, row):
    """design/207 (D1): a person's set was made from another source than the one that stands now: a photo given or replaced since, or the permission
    recorded or removed since (a set made before this was recorded: not known, so no)."""
    made = row.get('made')
    person = any(e['id'] == element_id and e.get('kind') == 'person' for e in plan.get('elements') or [])
    return bool(made) and person and made.get('photo') != likeness_photo(session, element_id)


def _spec_changed(session, plan, element_id, row):
    """E14: a material spec of the element was corrected or revised after its set was made (a set made before this was recorded: not known, so no)."""
    made = row.get('made')
    if not made:
        return False
    if _photo_changed(session, plan, element_id, row):
        return True
    for m in materials_of(plan, element_id):
        c = (session.get('spec_corrections') or {}).get(material_key(m['id']))
        if spec_digest(m['material_spec']) != (made.get('specs') or {}).get(m['id']) or (c and str(c.get('at') or '') > str(made.get('at') or '')):
            return True
    return False


def set_make(conn, store, user, run, outputs, element_id, quote=None, words=''):
    """R17: one set that was not made (refused before the call, or it did not come back) is made now; also a set whose spec changed after it was made
    (E14). Refused in plain words while its cause stands; a set already being made is left alone.
    design/211, a v2 round: `quote` is the operator's words; the chat tool gives them (an empty one is refused: making a set is paid), the page and
    the chat question give None: there the operator's click or answer is the word. A set whose plan changed since is made again too; three makes at most.
    VW-25 issue 11: `words`, the operator's comment with their own picture: stored with the thing before anything is checked or ordered, so a make
    that is refused or fails keeps them and the next make says them (`own_words`). The older way, the words dropped here, is retired."""
    session = session_of(store, run, outputs)
    v2 = round_v2(session)
    if v2:
        from . import ref_sets
        need(quote is None or str(quote).strip(), ref_sets.MAKE_NO_QUOTE.format(eid=element_id))
    row = _round_row(session, element_id, (2, 'making', 'complete', 'looking', 'rewrite') if v2 else (2, 'making', 'complete'))
    if v2 and own_words(session, user, None, element_id, words, True):
        save_session(store, run, session)
    if _set_rows(session, element_id, row.get('set'), ('generating',)):
        return {'element_id': element_id, 'queued': False, 'next': f'{element_id}: its set is already being made.'}
    plan = guarded(lambda: current_plan(store, session))
    need(session['round']['pass'] != 'complete' or _photo_changed(session, plan, element_id, row),   # design/207 (D1): a complete round opens again only for a person whose photo or permission changed
         'The reference round is not at the step where its sets are made: there is nothing to make now.')
    old = [x['id'] for x in _set_rows(session, element_id, row.get('set'), ('candidate', 'approved'))]
    plan_changed = v2 and bool(old) and not _spec_changed(session, plan, element_id, row) and ref_sets.set_facts(session, plan, element_id, row)['changed']   # design/211: the plan's words of this thing changed since
    need(not old or _spec_changed(session, plan, element_id, row) or plan_changed, f'{element_id} has its set: judge it (Yes, No or Correct it).')
    need(not v2 or ref_sets.makes(session, element_id, row) < ref_sets.MAKES_MAX, ref_sets.MAKES_LIMIT.format(eid=element_id, max=ref_sets.MAKES_MAX) if v2 else '')
    cause = set_cause(session, plan, element_id, _set_budget(run, session, visuals_spend(conn, run)))
    need(not cause, ref_sets.LIMIT_PLAIN if v2 and (cause or {}).get('kind') == 'cap' else f"{element_id}: its set cannot be made yet: {(cause or {}).get('text')}.")   # design/213: the limit of a v2 round, with no amount
    what ='the photo or the permission changed' if _photo_changed(session, plan, element_id, row) else 'the plan changed' if plan_changed else 'the spec changed'   # design/207 (D1)
    queued, errors = _queue_sets(conn, store, user, run, outputs, [element_id])
    held = ((session_of(store, run, outputs).get('round') or {}).get('elements') or {}).get(element_id, {}).get('held') if v2 else None
    due = ((session_of(store, run, outputs).get('round') or {}).get('elements') or {}).get(element_id, {}).get('things_due') if v2 else None
    if due:   # design/216b: Claude names the place's things first; ref_sets.round_things orders it then
        return {'element_id': element_id, 'queued': False, 'things_due': True, 'then': ref_sets.things_due_words(session_of(store, run, outputs))}
    if held:   # design/216: a place waits for its things' sets; it is made by itself when they are approved
        return {'element_id': element_id, 'queued': False, 'held': held, 'then': ref_sets.place_waiting(guarded(lambda: current_plan(store, session)), session_of(store, run, outputs), element_id, again=False)}
    need(queued, f'{element_id}: its set was not made: {_plain(errors.get(element_id))}')
    session = session_of(store, run, outputs)
    stamp = {'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'notes': what + ' after this set was made; the set is made again'}
    for rid in old:
        session['references'][rid].update(status='rejected', rejection=stamp)
        if (session.get('golden') or {}).get(element_id) == rid:
            session['golden'].pop(element_id)
    # VW-25 issue 13: an answer stored for the set before stays stored: it is never recorded (`_answer_of`), and the new set's line says so until the operator answers it (SET_REMADE)
    session['round']['pass'] = 'making'
    save_session(store, run, session)
    return {'element_id': element_id, 'queued': True, 'pass': 'making', 'next': f'{element_id}: its set is being made; it comes back on step 2.',
            **({'then': ref_sets.ALL_MAKING.format(k=1)} if v2 else {'cost_inr': round(image_price_inr(run, provider='gemini') * SET_MAX, 2)})}   # design/215: no amount in a v2 round


def set_aside(store, user, run, outputs, element_id, words='', back=False):
    """Follow-up, 11 Nov 2026: a set that was never made (its cause cannot be settled, or the operator does not want it) is set aside at step 2: the
    element is ignored for this round exactly as Ignore at step 1 does (ignored: true), with who, when and the words. back: it returns to the round,
    while the round is open. A set that was made is answered with No or Correct it, never set aside."""
    session = session_of(store, run, outputs)
    rd = session.get('round')
    v2 = round_v2(session)   # design/211: also while the round waits for Claude (the looks, a rewrite); and a set made three times can be left out
    need(rd and rd.get('kept') and _round_pass(session, rd) in ((2, 'making', 'looking', 'rewrite') + (('complete',) if back else ()) if v2 else (2, 'making')),
         'The reference round is not open at its sets: nothing can be set aside or brought back now.')
    row = rd['elements'].get(element_id)
    need(row, f'{element_id} is not in the reference round.')
    if back and v2 and row.get('ignored') and not row.get('aside'):   # design/211 review, M5: left out at step 1, asked for again by name: an open line, answered by the operator (ref_sets.round_reopen); nothing is made here
        need(not row.get('reopened'), f'{element_id} is back with the operator already.')
        from . import ref_sets
        row['reopened'] = 'asked'
        rd['pass'] = 2 if rd.get('pass') == 'complete' else rd['pass']
        save_session(store, run, session)
        return {'element_id': element_id, 'aside': False, 'next': f'{element_id} is back in the round.', 'then': ref_sets.BACK_ASKED.format(eid=element_id)}
    need(not (back and v2) or _round_pass(session, rd) != 'complete', 'The reference round is not open at its sets: nothing can be set aside or brought back now.')
    if back:
        need(row.get('aside'), f'{element_id} was not set aside at step 2: there is nothing to bring back.')
        row['ignored'] = False
        row.pop('aside')
        save_session(store, run, session)
        return {'element_id': element_id, 'aside': False, 'next': f'{element_id} is back in the round.'}
    need(not row.get('aside'), f'{element_id} is set aside already.')
    need(not row.get('ignored'), f'{element_id} was set to Ignore at step 1: it has no set.')
    need(not row.get('from_footage'), f'{element_id} is referenced by its footage picture: it has no set.')
    limit = False
    if v2:
        from . import ref_sets
        limit = ref_sets.makes(session, element_id, row) >= ref_sets.MAKES_MAX and not _set_rows(session, element_id, row.get('set'), ('generating', 'approved'))   # "use one of these, add your own picture, or leave it out"
    need(limit or not _set_rows(session, element_id, row.get('set'), ('generating', 'candidate', 'approved')),
         f'{element_id} has its set: answer it with No or Correct it; only a set that was never made can be set aside.')
    for x in _set_rows(session, element_id, row.get('set')) if limit else []:   # its pictures are not used: rejected with the operator's words
        x.update(status='rejected', rejection={'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'notes': ' '.join(str(words or '').split()) or 'left out after three makes'})
    row['ignored'] = True
    row['aside'] = {'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'words': ' '.join(str(words or '').split())}
    row.pop('answer', None)
    save_session(store, run, session)
    return {'element_id': element_id, 'aside': True, 'next': f'{element_id} is set aside for this round: nothing is made for it. Bring back returns it while the round is open.'}


def _sids(row):
    """design/121 change 5: a thing's searches in the round, the plain one and the stock one (an older row: its one search)."""
    return list(row.get('search_ids') or ([row['search_id']] if row.get('search_id') else []))


def round_done(store, user, run, outputs, verdicts, quote, conn=None):
    """Pass 1 answered: the chosen frames approved with the words; design/121 change 6: every thing set to Google was searched with its own button
    (Done runs no search and waits, naming them); Ignore this needs nothing. Pass 2 for the searched things.
    design/151, a kept round: approve or ignore only (the search is retired by name); then every set is made silently and the round is 'making'."""
    session = session_of(store, run, outputs)
    rd = session.get('round')
    need(rd and rd.get('pass') == 1, 'No reference round is waiting for its first pass.')
    open_ = sorted(eid for eid, d in (session.get('drawings') or {}).items() if d.get('status') in ('proposed', 'rejected') and eid in rd['elements'] and not (verdicts or {}).get(eid, {}).get('verdict') == 'ignore')
    need(not open_, 'The reference drawings of ' + ', '.join(open_) + ' are not approved yet: the operator answers them first, on the page (`vw visuals page`); in the chat (`vw visuals next`) only where the page cannot be shown; and a corrected set is sent again (`vw drawing set`). '
                    'The sets are made with the approved drawings, so Done waits for them.')   # design/200
    quote = said(quote, 'Pass 1 done', user)   # design/99 C6: the click approves the frames
    verdicts = verdicts or {}
    waiting = []
    for eid, row in rd['elements'].items():
        if not row['frames']:   # a round posted without naming the frames: the element's grabbed frames count (as round_start does now)
            row['frames'] = [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved')]
        v = verdicts.get(eid) or {}
        if rd.get('kept'):
            need(v.get('verdict') != 'search', f'{eid}: the Google Images search is retired on this film (the kept method); the set is made from real photographs by the kept method: approve the footage picture or ignore.')
            if rd.get('v') == 2:   # design/211: "Make a clean set from it" is an answer too; it needs a footage picture with its look
                from . import ref_sets
                need(v.get('verdict') in ref_sets.STEP1_VERDICTS, f'{eid}: a verdict is required: approve, clean (a clean set made from its footage picture), or ignore.')
                need(ref_sets.step1_frames(session, eid, row) or v['verdict'] != 'clean', ref_sets.CLEAN_NO_FRAME.format(eid=eid))
                continue
            need(v.get('verdict') in ('approve', 'ignore'), f'{eid}: a verdict is required: approve the footage picture (or the element, when it has none), or ignore.')
            continue
        need(v.get('verdict') in ('approve', 'search', 'ignore'), f'{eid}: a verdict is required: approve the footage picture, search, or ignore.')
        if v['verdict'] == 'approve' and not rd.get('kept'):
            need(row['frames'], f'{eid} has no frame to approve: search instead, or ignore it.')
        if v['verdict'] == 'search' and not _sids(row):
            waiting.append(eid)
    need(not waiting, f"{len(waiting)} thing{'s' if len(waiting) > 1 else ''} not searched yet: {', '.join(waiting)}. Press Search on each, or choose the footage picture or Ignore this.")
    stamp = {'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(), 'quote': quote}
    for eid, row in rd['elements'].items():
        v = verdicts[eid]['verdict']
        row['verdict'], row['ignored'] = v, v == 'ignore'
        if rd.get('v') == 2:   # design/211: the answer "clean", and the operator's comment of step 1, which goes into the request
            row['clean'] = v == 'clean'
            row.setdefault('operator_words', []).extend([w for w in [' '.join(str(verdicts[eid].get('words') or '').split())] if w])
        if v in ('approve', 'clean'):
            for fid in row['frames']:
                r = session['references'][fid]
                if r['status'] == 'candidate':
                    r.update(status='approved', approval={**stamp, 'sha256': r['sha256']})
                    _feedback_image(session, run, user, r, 'pass', quote, '')
    rd['quote'] = quote
    if rd.get('kept'):   # design/151: every set made now, silently; the operator judges them in one shot
        from_footage = _from_footage(session, guarded(lambda: current_plan(store, session)), rd)   # SK, 5 Nov 2026: an approved footage picture is the reference; no AI set is made for it
        save_session(store, run, session)
        todo = [eid for eid, r in rd['elements'].items() if not r.get('ignored') and eid not in from_footage]
        v2 = rd.get('v') == 2
        if v2:   # design/211: the first three sets now; the others wait for the operator's word (ref_sets.round_rest)
            todo, rd['rest'] = ref_sets.first_go(guarded(lambda: current_plan(store, session)), rd, todo)
            rd['go'] = 1
            save_session(store, run, session)
        queued, errors = _queue_sets(conn, store, user, run, outputs, todo)
        session = session_of(store, run, outputs)
        rd = session['round']
        # design/213: a set of the first go that was refused before any call is replaced by the next waiting one, so the first go is three made sets where three
        # are possible; the refused one stays "not made" with its reason. The limit stops every order, so nothing replaces a set it refused; and where no
        # set at all could be ordered the cause is not the thing's own (the picture service is down): the waiting sets stay waiting.
        while v2 and queued and rd.get('rest') and len(queued) < ref_sets.FIRST_MAX and not any(ref_sets.is_limit(m) for m in errors.values()):
            nxt = rd['rest'].pop(0)
            save_session(store, run, session)
            more, bad = _queue_sets(conn, store, user, run, outputs, [nxt])
            queued, errors = queued + more, {**errors, **bad}
            session = session_of(store, run, outputs)
            rd = session['round']
        rd['pass'] = 'making' if queued else ('complete' if not todo else 2)   # every set refused before the call: step 2 shows them (No or Correct it makes them again)
        save_session(store, run, session)
        return {'pass': rd['pass'], 'queued': queued, 'errors': errors, 'from_footage': from_footage,
                **({} if v2 else {'cost_inr': round(len(queued) * image_price_inr(run, provider='gemini') * SET_MAX, 2)}),   # design/215: no amount in an answer of a v2 round
                **({'rest': list(rd.get('rest') or []), 'then': ' '.join(x for x in (ref_sets.done_then(run, queued, rd.get('rest') or [], errors, complete=rd['pass'] == 'complete'), ref_sets.things_due_words(session)) if x)} if v2 else {})}
    searched = [eid for eid, r in rd['elements'].items() if r['verdict'] == 'search']
    rd['pass'] = 2 if searched else 'complete'
    save_session(store, run, session)
    return {'pass': rd['pass'], 'searched': searched, 'errors': {eid: r['error'] for eid, r in rd['elements'].items() if r.get('error')}}


def round_picks(store, user, run, outputs, picks, quote, ignore=()):
    """Pass 2 answered: the ticked pictures per search become web references; design/121 change 1: every searched thing has an answer first
    (a tick, a pick saved before, or Ignore this), else nothing is saved and the waiting things are named."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    rd = session.get('round')
    need(not (rd or {}).get('kept'), 'retired on this film (the kept method): this round has no picks; answer its sets (`vw visuals round --sets`, or the page).')
    need(rd and rd.get('pass') == 2, 'No reference round is waiting for its second pass.')
    quote = said(quote, 'Pass 2 done', user)   # design/99 C6
    picks, ignore = picks or {}, set(ignore or ())
    searches = session.get('searches') or {}
    own = {sid for r in rd['elements'].values() for sid in _sids(r)}
    for sid in picks:
        need(sid in own, f'Search {sid} is not in this round.')
    waiting = [eid for eid, r in rd['elements'].items() if r.get('verdict') == 'search' and eid not in ignore
               and not any(picks.get(sid) or (searches.get(sid) or {}).get('picked') for sid in _sids(r))]
    need(not waiting, f"{len(waiting)} thing{'s' if len(waiting) > 1 else ''} still need an answer: {', '.join(waiting)}. Tick a picture, search again with new words, or press Ignore this.")
    made, failed = [], {}
    wanted = {}   # design/83 P1: every pick of every search downloaded at once, then recorded search by search in the ticked order
    for sid, rows in picks.items():
        results = {r['n']: r for r in (searches.get(sid) or {}).get('results') or []}
        for p in rows or []:
            if (p or {}).get('n') in results:
                wanted[(sid, p['n'])] = results[p['n']]
    fetched = _fetch_picks(store, run, wanted)   # design/121 change 6
    for sid, rows in picks.items():
        if not rows:
            continue
        try:
            out = _pick_into(store, session, user, run, plan, sid, list(rows), quote, fetched)
            made += out['references']
            if out['failed']:
                failed[sid] = out['failed']
        except (Problem, ValueError) as exc:
            failed[sid] = exc.message if isinstance(exc, Problem) else str(exc)
    for eid, r in rd['elements'].items():
        if r.get('verdict') == 'search':
            r['ignored'] = eid in ignore
    rd['pass'] = 'complete'
    save_session(store, run, session)
    return {'complete': True, 'references': [r['id'] for r in made], 'failed': failed, 'ignored': sorted(ignore)}


def _round_view(session, plan=None, budget=None):
    rd = session.get('round')
    if not rd:
        return None
    searches = session.get('searches') or {}
    sets = lambda eid, r: sorted((x['id'] for x in _set_rows(session, eid, r.get('set'), ('generating', 'candidate', 'approved', 'rejected', 'failed'))), key=lambda i: int(session['references'][i].get('set_n') or 1)) if r.get('set') else []
    step = _round_pass(session, rd)
    return {**rd, 'pass': step, 'kept': bool(rd.get('kept')),
            'elements': {eid: {**r, 'search_ids': _sids(r), 'picked': [n for sid in _sids(r) for n in (searches.get(sid) or {}).get('picked') or []] if _sids(r) else None,
                               **({'set': sets(eid, r), **_set_state(session, plan, step, eid, r, budget)} if rd.get('kept') else {})}
                         for eid, r in rd['elements'].items()}}


def _set_state(session, plan, step, eid, row, budget):
    """What the page adds to a kept round's row: the stored answer of step 2 (R13); for a set that is not made, or whose spec changed since, the
    cause that stands now (R12, R18) or the word that it is settled."""
    answer, discarded = _answer_of(row)
    out = {'answer': answer, **({'answer_discarded': True} if discarded else {})}
    if not plan or row.get('ignored') or row.get('from_footage') or (step not in ((1, 2, 'making', 'looking', 'rewrite') if round_v2(session) else (1, 2, 'making')) and not (step == 'complete' and _photo_changed(session, plan, eid, row))):   # design/207 (D1): a complete round still says that a person's photo or permission changed
        return out
    kind = next((e.get('kind') for e in plan.get('elements') or [] if e['id'] == eid), None)
    frames = row.get('frames') or [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved')]
    if step == 1 and kind != 'person' and frames:   # Done takes its footage picture as the reference: no set is made for it
        return out
    live = _set_rows(session, eid, row.get('set'), ('generating', 'candidate', 'approved'))
    changed = bool(live) and _spec_changed(session, plan, eid, row)
    if live and not changed:
        return out
    cause = set_cause(session, plan, eid, budget)
    error = str(row.get('error') or '')
    failed = _set_rows(session, eid, row.get('set'), ('failed',))
    mark = {**({'spec_changed': True} if changed else {}), **({'photo_changed': True} if changed and _photo_changed(session, plan, eid, row) else {})}   # design/207 (D1): the page says which
    if not error and failed and not cause:   # F4: the call itself failed; its reason is on the set's picture, said in one plain sentence
        problem = _fail_words(failed[-1].get('error'))
        if round_v2(session):   # design/211: the cause, the provider and the model from the job itself
            problem = _fail_words(failed[-1].get('error'), failed[-1])
        if (problem in ('The picture service refused the request.', 'The model returned no picture.') or (round_v2(session) and _fail_cause(failed[-1]) in ('refused', 'no_picture'))) and (row.get('made') or {}).get('photo') and row['made']['photo'] == likeness_photo(session, eid):   # design/207 (D1): the person's photo, the one that still stands, was refused
            return {**out, 'cause': None, 'settled': None, 'problem': problem + ' ' + LIKENESS_REFUSED, **mark,
                    'next': f"The picture service refused the photo of {eid}. Ask the operator: give another photo (`vw visuals own --element {eid} --file <photo>`), or make the person a stand-in "
                            f'(`vw visuals likeness --element {eid} --stand-in --quote "<their words>"`); then make the sheet again (`vw visuals round --make {eid}`).'}
        return {**out, 'cause': None, 'settled': None, 'problem': problem, **mark}
    from . import ref_sets
    was = 'spec' if 'material spec of' in error else 'cap' if ref_sets.is_limit(error) else 'size' if 'size still unknown' in error else 'other' if error else None
    if rule_retired(session, error) and not cause:
        return {**out, 'cause': None, 'settled': RULE_RETIRED, 'problem': None, **mark}
    return {**out, 'cause': cause, 'settled': None if cause else {'spec': 'spec approved', 'size': 'size measured', 'cap': 'spend cap raised'}.get(was),
            'problem': _plain(error) if was == 'other' and not cause else None, **mark}


def nothing_fits(store, user, run, outputs, search_id, reason):
    """design/73 R4b (6): none of the ten fits; the reason joins the element's "not this" list (design/111 F12). design/121 change 1: the next search is
    the operator's own (new words and Search again), or Ignore this."""
    session = session_of(store, run, outputs)
    s = (session.get('searches') or {}).get(search_id)
    need(s, f'Unknown search {search_id}.')
    need(str(reason or '').strip(), 'Say in one line why nothing fits; it goes on the "not this" list.')
    s['nothing_fits'] = {'reason': str(reason).strip(), 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    return {'search_id': search_id, 'nothing_fits': s['nothing_fits']}


def _searches(session):
    return [{k: v for k, v in s.items() if k != 'results'} | {'results': s.get('results') or []} for s in (session.get('searches') or {}).values()]


def parent_failed(session, p):
    """Rule 0, fork 4: the failed must lines of a would-be parent. The critic's review of design/217 (3): on a v2 film they are Claude's failed
    lines (`ref.look`, through `pictures.check_view`), not the model's `must_failed`, which such a picture no longer has."""
    from . import pictures
    if p and pictures.claude_checks(session, p) and not pictures.older(p):
        return pictures.check_view(session, p)['faults']
    return [l.get('check') for l in ((p or {}).get('check') or {}).get('must_failed') or []]


def generate_image(conn, store, user, run, outputs, body, round_set=False):
    """Queue an OpenAI image job (paid, informed). The worker stores the PNG and creates the candidate reference.
    `round_set`: the order comes from the reference round (`_queue_sets`); a set of a v2 round is made no other way (design/211 review, M6)."""
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    need((body['kind'] == 'style') == (body['element_id'] == STYLE), f'The style sheet is kind style with element {STYLE}, and only it.')   # design/89 C2
    need(not (body['kind'] == 'style' and round_v2(session) and not _has_steps(plan)), STYLE_NOT_NEEDED)   # design/217 (D5)
    element ={'id': STYLE, 'kind': 'style'} if body['element_id'] == STYLE else next((e for e in plan['elements'] if e['id'] == body['element_id']), None)
    need(element, 'Reference must identify an element in the current plan.')
    need(body['kind'] in ('isolated', 'sheet', 'keyframe', 'state', 'style', 'component'), 'Generated references are isolated, sheet, keyframe, state, style or component.')
    need(not (body['kind'] == 'sheet' and element['kind'] == 'animal'), ANIMAL_NO_SHEET.format(eid=element['id']))   # design/207 (D4); design/207 point 4: a real speaker may have an AI picture (the older refusal, retired)
    is_set = body['kind'] == 'sheet' and body['element_id'] != STYLE and mark_kept(session, run)   # design/151: a reference set by the kept method
    need(not (is_set and round_v2(session)) or round_set or body.get('fix_of'), SHEET_BY_ROUND.format(eid=element['id']))
    subject_words = body['prompt']   # hotfix 11 Nov 2026 (VW-19): the writer's own words for a kept set, before the server wraps them in its preamble
    v2row = ((session.get('round') or {}).get('elements') or {}).get(element['id']) if is_set and round_v2(session) else None
    if v2row is not None:   # design/211: the request of a v2 round's set is written by the server, by kind of thing, from the plan's own words and the film's own pictures
        from . import drawings, ref_sets
        if element['kind'] == 'person':
            distinct_people(plan)
        given, _ = ref_sets.inputs_of(session, element)
        sheets = [i for i in given if i['role'] == 'drawing']
        how = drawings.words(store, session, element['id'], first=len(given) - len(sheets) + 1) if sheets and (session['drawings'][element['id']].get('key')) else None
        v2req = ref_sets.set_request(plan, run, session, element, {**v2row, 'drawn_how': how})
        body = {**body, 'prompt': v2req['prompt'], 'parents': [i['ref'] for i in v2req['inputs']], 'set': True, **({'search': True} if v2req['search'] else {}),
                'views': [v['ask'] for v in v2req['views']], 'view_names': [v['name'] for v in v2req['views']]}
        v2row['parts'] = v2req['parts']
    elif is_set:
        if element['kind'] == 'person':
            distinct_people(plan)
            photo = likeness_photo(session, element['id'])   # design/207 (D1): own likeness: the person's photo is Image 1; a stand-in is made from the words alone
            body = {**body, 'prompt': person_prompt(plan, run, element, body['prompt'], photo=bool(photo), session=session), 'parents': [photo] if photo else [], 'set': True, 'views': set_views(element)}
        else:
            own = [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == element['id'] and r.get('status') == 'approved']
            parents_ = list(body.get('parents') or []) or own[:1]   # Q1: a thing the footage shows is made from its approved frame
            from . import drawings   # design/200: an approved drawing set of the thing goes with the request, after the frame, with the words that explain it and its facts
            sheets = [s['id'] for s in drawings.approved_sheets(session, element['id']) if s['id'] not in parents_]
            drawn = (drawings.words(store, session, element['id'], first=len(parents_) + 1), drawings.must_be_true(session, element['id'])) if sheets else None
            body = {**body, 'prompt': thing_prompt(plan, run, session, element, body['prompt'], frame=bool(parents_), drawn=drawn), 'parents': parents_ + sheets, 'set': True, 'search': True,
                    'views': set_views(element), **({'drawn_facts': drawn[1]} if drawn else {})}
    if element['kind'] not in ('person', 'graphic', 'style') and body['element_id'] != STYLE and v2row is None:   # design/215 (R3, R4): not for a set of a v2 round: the operator decided at step 1, and an unknown size is left out of its request
        from .visual_contract import footage_cited
        frames_ok = [r for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == element['id'] and r.get('status') == 'approved']
        cited = footage_cited(element, plan.get('visual_facts'))
        need(not footage_frame_needed(session, cited, frames_ok), f"{element['id']}'s fact or size cites the footage ({cited[:80]}): approve a footage frame of {element['id']} (`vw visuals frame --element {element['id']} ...`) "
                                     f"before any picture of it, and mark it identity exact in the plan.")
        unknown = [d for d in element.get('size') or [] if d.get('value') is None]   # design/119 rule 8: measure before the first picture
        if frames_ok and unknown and (body['kind'] != 'sheet' or is_set):   # design/151 Q6: a set is the golden picture too, so it waits for the measure
            d = unknown[0]
            need(False, f"{element['id']} has a size still unknown ({d.get('part')} {d.get('measure')}) and an approved footage frame {frames_ok[0]['id']}: measure it first "
                        f"(`vw visuals measure --refs {frames_ok[0]['id']} --question ...`), then put the value in the plan with status measured, before its first picture.")
    writer_prompt = body['prompt']   # the writer's words, before the server adds any line of its own (defect 38: kept before the component and sheet lines, which the answer form never holds)
    if body['kind'] == 'component':   # design/117 P1: a thing alone, in the approved style, on a transparent background; the style picture is Image 1
        need(element['kind'] in ('object', 'material', 'process', 'technique'), 'A component is a picture of a thing (an object, a material, a process or a technique), never a person, a graphic or the style.')
        style_ref = next((r for r in session['references'].values() if r.get('kind') == 'style' and r.get('status') == 'approved'), None)
        no_style = round_v2(session) and not _has_steps(plan)   # design/217 (D5): a film with no graphic in steps has no style sheet; its components take the plan's palette from the words
        need(style_ref or no_style, 'A component is made in the approved style: approve the style picture first (the Pictures step).')
        if style_ref and style_ref['id'] not in (body.get('parents') or []) and not body.get('fix_of'):   # W4: a fix keeps the picture to fix as Image 1
            body = {**body, 'parents': [style_ref['id']] + list(body.get('parents') or [])}
        block = COMPONENT_BLOCK if provider_of(run) == 'openai' else COMPONENT_BLOCK_GREEN   # design/120: Gemini has no transparent output; the server keys the green out
        if not style_ref:
            block = block.replace(STYLE_IMAGE_ONE, '')
        body = {**body, 'prompt': with_composed(body['prompt'], block.format(name=element.get('name') or body['element_id']))}
    if body['kind'] == 'sheet' and body['element_id'] != STYLE and not is_set:   # design/119 rule 2: the server's lines on a reference sheet (not on a kept set: no labels in a picture)
        body = {**body, 'prompt': with_composed(body['prompt'], sheet_block(element))}
    parents = [session['references'].get(p) for p in body.get('parents') or []]
    crops = body.get('crops') or {}   # design/119 rule 1: {parent id: region}; the server crops before the upload
    for pid, region in crops.items():
        need(pid in (body.get('parents') or []), f'crops names {pid}, which is not among the parents.')
        check_crop(region)
    for p in parents:   # design/71 P6 (the server check, design/74 L7): a retry starts from an approved picture, never from a rejected one
        if p and p.get('status') == 'rejected':
            need(False, f"{p['id']} was rejected: it is never a parent; " + ('make the next state from the last approved state.' if body['kind'] == 'state' else
                                                                              'start from an approved picture (an end image from its approved start).'))   # design/124 A4 item 12
    people = people_of(plan)
    for p in parents:   # design/124 decision 5, design/207 (D1): a web picture of a person is never sent to the picture AI; a footage frame or the operator's own photo only with the recorded permission
        need(not person_picture_refused(session, people, p), person_picture_refused(session, people, p))
    gold = golden_of(session, body['element_id'])
    if body.get('golden'):   # design/111 F11: the golden picture, written on the server's cue after the sheet (and the spec) are approved
        need(not kept(session), 'retired on this film (the kept method): the golden picture is the picture of the set the operator ticks (Yes on the References step); no separate golden call on this film.')
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
    else:   # design/124 decision 9: an end is made only from an approved start (the server makes it from end_prompt once the start is approved); a fix starts from its candidate
        for p in parents:
            if p and body['kind'] == 'keyframe' and p.get('kind') == 'keyframe' and p.get('status') == 'candidate' and p['id'] != body.get('fix_of'):
                from . import pictures
                early = pictures.claude_checks(session, p, plan)   # fix set A2.2: a picture of step 6 that another picture is made from is an early decision: its card comes now, in the chat
                if early and not p.get('parent_wanted'):
                    p['parent_wanted'] = True
                    save_session(store, run, session)
                need(False, f"{p['id']} is a start image still waiting for approval: an end image is made only from an approved start. Write the end with the start "
                            "(`end_prompt`, `end_answer`, `end_region` on `vw visuals image`); the server makes the end once the operator approves the start."
                            + (f" {p['id']} is asked of the operator now, in the chat (`vw visuals next`): once it is approved, order this picture again." if early else ''))
        need(all(p and (p['status'] == 'approved' or (p['status'] == 'candidate' and p['id'] == body.get('fix_of')))   # W4: a fix starts from its candidate, whatever its kind
                 for p in parents), 'Parents must be approved references of this run.')
    # design/215 (R1): of a v2 set's request the wording rules read only the words Claude or the operator added, never the plan's own words
    library.check_prompt(' '.join(x for x in (v2req['parts']['added'], v2req['parts']['operator']) if x) if v2row is not None else body['prompt'],
                         fix=bool(body.get('fix_of')), placed=not (body.get('set') and round_v2(session)), picture=True)   # fix set A2.3: a picture's prompt: a depth word places nothing; defect 54: a v2 set's request is the plan's own words, placed by the server; design/124: a fix's one change is the server's failed line; design/71 F2: no logo, no model name, no size, no resolution in a prompt (a ValueError; the API wraps this call in guarded())
    if body['kind'] == 'keyframe':   # design/67 D: an end keyframe is edited from the start keyframe and the start's own references, so identity is held by its sources
        starts = [p for p in parents if p['kind'] == 'keyframe']
        need(not starts or re.search(r'\bimage 1\b', body['prompt'], re.I),
             'An end image names its pictures: the prompt names "Image 1" as the start image (images 2 onward are its identity sheets, sent by the server).')   # design/71 P1
        for start in starts:
            for inherited in (start.get('generation') or {}).get('parents') or []:
                row = session['references'].get(inherited.get('id'))
                if row and row['status'] == 'approved' and all(p['id'] != row['id'] for p in parents):
                    need(not person_picture_refused(session, people, row), person_picture_refused(session, people, row))   # design/207 (D1): the same test on what the start brings with it
                    parents.append(row)
    need(len(parents) <= MAX_INPUTS, f'{len(parents)} input pictures after the start\'s own references are added; GPT Image takes at most {MAX_INPUTS}. Name fewer.')   # design/71 P2
    if provider_of(run) == 'gemini':   # design/120: fourteen at most, counted by kind (Google's limits for the Pro image model)
        ekind = {e['id']: e['kind'] for e in plan['elements']}
        kinds = {'style': [p for p in parents if p and p.get('kind') == 'style'], 'character': [p for p in parents if p and p.get('kind') != 'style' and ekind.get(p.get('element_id')) == 'person']}
        kinds['object'] = [p for p in parents if p and p not in kinds['style'] and p not in kinds['character']]
        need(len(parents) <= GEMINI_MAX_INPUTS, f'{len(parents)} input pictures: Gemini takes at most {GEMINI_MAX_INPUTS}. Name fewer.')
        for kind_, cap_ in GEMINI_KIND_CAPS.items():
            need(len(kinds[kind_]) <= cap_, f"{len(kinds[kind_])} {kind_} pictures ({', '.join(p['id'][:8] for p in kinds[kind_])}): Gemini takes at most {cap_} {kind_} pictures in one prompt. Name fewer.")
    # design/111 F21's cap of four removed (SK, 28 Oct 2026): every applicable reference may go in, each with its job line; the model's MAX_INPUTS is the ceiling
    named_n = len(body.get('parents') or [])
    for k, p in enumerate(parents[named_n:], named_n + 1):   # F21: the server names the pictures it added itself (the start's own sheets)
        if p:
            body = {**body, 'prompt': with_composed(body['prompt'], f"Image {k} is the approved {p.get('kind') or 'reference'} of {p.get('element_id')}: take identity from it, nothing else.")}
    if body['kind'] == 'keyframe' and kept(session):   # design/151 Q3; design/207: only while the picture service has room (its limits were checked above, before the faces)
        gem = provider_of(run) == 'gemini'
        parents, lines_ = with_faces(session, parents, people, (GEMINI_MAX_INPUTS if gem else MAX_INPUTS) - len(parents),
                                     GEMINI_KIND_CAPS['character'] - len([p for p in parents if p and p.get('kind') != 'style' and p.get('element_id') in people]) if gem else None)
        for line in lines_:
            body = {**body, 'prompt': with_composed(body['prompt'], line)}
    if parents and not body.get('fix_of'):   # F21: one job line per picture
        missing_ = library.image_names_missing(body['prompt'], len(parents))
        need(not missing_, f"the prompt does not say what Image {', '.join(map(str, missing_))} is for: one job line per picture ('Image k is …: take …').")
    if not body.get('shot_id') and body['kind'] in ('keyframe', 'state'):   # design/94 R1.1: a state, an end image or a fix takes its parent's shot
        body['shot_id'] = next((p['shot_id'] for p in parents if p and p.get('kind') in ('keyframe', 'state') and p.get('shot_id')), None)
        need(body['shot_id'] or body.get('fix_of'), f"Name the shot this {body['kind']} is for (--shot): a picture is listed, checked and placed only in its own shot.")
    _no_question(session, body['element_id'], body.get('shot_id'), *[p['id'] for p in parents if p])   # design/110 rule 0
    if not body.get('fix_of'):   # rule 0, fork 4: a parent approved with a failed must line is asked about once; a fix is that line's remedy
        for p in parents:
            failed = parent_failed(session, p)
            if p and p.get('status') == 'approved' and p.get('kind') in ('keyframe', 'state') and failed and not p.get('parent_ok'):
                _open(session, p['id'], f"{p['id']} was approved with a failed must line ({', '.join(failed)}): use it as the parent of new pictures anyway, or make a new one?",
                      ['use it as the parent', 'make a new one'], 'server', fork='parent')
                save_session(store, run, session)
                need(False, f"{p['id']} was approved with a failed must line ({', '.join(failed)}): the operator decides first; the question is on its card (`vw visuals answer --item {p['id']} …`).")
    found = guarded(lambda: locate(store, session, body['shot_id'])) if body.get('shot_id') else None   # design/91 N8: the shot this picture is for
    named = found[3] if found else None
    if named is not None:   # design/119 rule 5: a reference goes in only when its thing is in the shot (the style, the start chain and a person in frame excepted)
        allowed = set(named.get('element_ids') or []) | {body['element_id'], STYLE}
        for p in parents:
            if p and p.get('element_id') not in allowed and p.get('kind') not in ('keyframe', 'state'):
                nm = next((e.get('name') for e in plan['elements'] if e['id'] == p.get('element_id')), p.get('element_id'))
                need(False, f"{p['id']} is a picture of {p.get('element_id')} ({nm}), which is not in shot {named['id']}: add the element to the shot's element_ids or leave the picture out.")
    if body['kind'] == 'keyframe':
        _keyframe_gates(session, plan, body, parents, named)   # design/77 L35, L38, L41
    answer = body.get('answer')
    if answer is not None:   # design/68 L5: the library's answer form travels with the prompt
        try:
            library.check_answer({**answer, 'exact_text': []} if body.get('fix_of') else answer, writer_prompt)   # W5: a fix's prompt is its one change; the exact texts are added after this check
            library.check_exact_places(answer, {lm['id'] for lm in (found[2].get('landmarks') if found else []) or []})   # design/111 F13
            library.check_quoted(writer_prompt, library.exact_entries(answer))
        except ValueError as exc:
            need(False, str(exc))
    elif not body.get('fix_of') and v2row is None:   # design/215 (R2): not on a v2 set: an inch mark or a printed name in the plan's words is no lettering to place
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
    # picture was rule 2's new picture (several things change, or the framing), made whole; since design/112 S2 an end always has its region: the alternative is a start-only take
    if body['kind'] == 'keyframe':
        body = {**body, 'role': 'end' if is_end else 'start'}   # a copy: the caller's request is never changed
    if region and provider_of(run) == 'gemini' and not body.get('fix_of'):   # design/120: no mask on Gemini; the region in words, the composite-back restores the outside as before
        body = {**body, 'prompt': with_composed(body['prompt'], f"Change only what is inside the region left {region['left'] * 100:g} %, top {region['top'] * 100:g} %, width {region['width'] * 100:g} %, height {region['height'] * 100:g} % of Image 1; everything outside it exactly as Image 1.")}
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
    if body['kind'] == 'keyframe' and is_end and not region and not body.get('fix_of'):   # design/112 S2
        whats = '; '.join(c.get('what', '') for c in (named or {}).get('changes') or []) or 'the change'
        need(False, f'An end image is an edit inside one region of its start: give --region left,top,width,height (fractions of the frame, a third at most) covering where {whats} happens; '
                    'the server masks it and copies the start back outside it, so nothing else moves. Several places, or the framing itself: make the shot start-only (end_state_exact false) and let the motion carry the change.')
    lines, warns = _graphic_lines(session, plan, body, parents, answer, named)   # design/89 C, D; design/91 N6, N8, N10, N14
    if round_v2(session) and named is not None and named.get('visual_type') == 'image' and body['kind'] in ('keyframe', 'isolated') and not body.get('fix_of'):   # design/211, gap 23 in part: a still that leaves out an approved reference of a thing its shot names
        from . import ref_sets
        warns += ref_sets.unused_refs(session, plan, named, parents)
    if body['kind'] == 'component':
        lines = list(lines or []) + COMPONENT_LINES
    if v2row is not None:   # design/211: the lines of a v2 set, by kind (ref_sets.set_request)
        lines = list(lines or []) + v2req['lines']
    elif is_set:   # design/151: the kept method's checks on a thing's set; a person's set alone on plain ground
        lines = list(lines or []) + (PERSON_SET_LINES if element['kind'] == 'person' else KEPT_THING_LINES)
        if body.get('drawn_facts') is not None:   # design/200: the facts of the drawing set are checked on the picture, and it must be a photograph
            lines += [{'check': 'drawn fact: ' + f, 'weight': 'must', 'pass_when': f'the picture shows it as the approved drawings do: {f}'} for f in body['drawn_facts']] + [DRAWN_LOOK_LINE]
    elif body['kind'] == 'sheet' and body['element_id'] != STYLE:
        lines = list(lines or []) + sheet_lines(element)   # design/119 rule 2
        if not body.get('fix_of'):   # design/121 change 4: the operator's note on each source, in the prompt and as a must line
            for k, p in enumerate(parents, 1):
                note = ((p or {}).get('source') or {}).get('note') or ''
                if note.strip():
                    body = {**body, 'prompt': with_composed(body['prompt'], f"The operator's note on Image {k}: {note.strip().rstrip('.')}.")}
                    lines.append({'check': f'operator note on Image {k}', 'weight': 'must', 'pass_when': f"the picture follows the operator's note on Image {k}: {note.strip()}"})
    if not body.get('fix_of'):   # design/121 change 5: a web picture may carry a stock site's watermark; never copied
        webs = [k for k, p in enumerate(parents, 1) if p and p.get('kind') == 'web']
        for k in webs:
            body = {**body, 'prompt': with_composed(body['prompt'], f"Image {k} may carry a watermark or a stock site's lettering: ignore it, never copy it.")}
        if webs:
            lines = list(lines or []) + [WATERMARK]
    if body.get('end_prompt') and not body.get('end_region') and not body.get('fix_of'):   # design/112 S2: the end the server queues needs its region too
        warns.append('the end written with this start has no region: the server will refuse to make it; give --end-region left,top,width,height with the start')
    if body['kind'] == 'keyframe' and not is_end and named is not None:
        lines = lines + not_yet_lines(named)   # design/110 F3: a start shows the action not yet done (a fix of a start too)
    if answer is not None and library.exact_entries(answer):   # design/111 F13: every picture with exact text, not only a graphic
        lines = lines + [l for l in exact_text_lines(answer, {lm['id']: lm['description'] for lm in (found[2].get('landmarks') if found else []) or []}) if l['check'] not in {x['check'] for x in lines}]
        body = {**body, 'prompt': with_composed(body['prompt'], exact_text_block(answer))}
    for eid in [body['element_id']] + [x for x in (named or {}).get('element_ids') or [] if x != body['element_id']]:   # design/111 F12: 'none of these', in every prompt that shows the element
        nl = not_this_line(session, plan, eid, named, found[2] if found else None)
        if nl and v2row is None:   # design/215 (R5): never on a v2 set: its request carries the operator's words in their own place
            body = {**body, 'prompt': with_composed(body['prompt'], nl)}
    if v2row is None and not body.get('fix_of') and body['element_id'] != STYLE:   # design/215 (change 5): a still or a start picture carries the operator's corrections of its things (a set's request places them itself)
        body = {**body, 'prompt': with_corrections(session, plan, body['prompt'], [body['element_id']] + list((named or {}).get('element_ids') or []))}
    for m in materials_of(plan, body['element_id'], named):   # design/111 F10: the spec approved first, the words in numbers, the sentence and the line
        need(material_approved(session, m), f"the material spec of {m['id']} is not approved, or changed since: the operator approves it first, on the page (`vw visuals page`), before a picture shows it.")
        try:
            library.check_material_prompt(material_words(writer_prompt, subject_words, is_set))
        except ValueError as exc:
            need(False, str(exc))
        lines = lines + material_lines(m)
        body = {**body, 'prompt': with_composed(body['prompt'], material_sentence(m))}
    if not body.get('fix_of'):   # design/119 rule 6: every known size as a number beside the thing (the material spec carries its own)
        shown = [e for e in plan['elements'] if e['id'] in set((named or {}).get('element_ids') or []) | {body['element_id']} and not e.get('material_spec')]
        sizes = '; '.join(s for s in (size_sentence(e) for e in shown) if s)
        if sizes and v2row is None:   # design/211: a v2 set's request carries the plan's sizes with their status already
            body = {**body, 'prompt': with_composed(body['prompt'], 'Sizes: ' + sizes + '.')}
        for al in animal_lines(plan, [e['id'] for e in shown]) if body['kind'] != 'sheet' else []:   # design/207 (D4): a living extra is carried by its words
            body = {**body, 'prompt': with_composed(body['prompt'], al)}
        own_words =[e.get('name', '') for e in plan['elements'] if e['id'] in set((named or {}).get('element_ids') or []) | {body['element_id']}]   # design/119 rule 3
        for k, p in enumerate(parents, 1):
            if p and p.get('element_id') not in (body['element_id'], None) and p.get('kind') not in ('keyframe', 'state', 'frame'):
                extra = also_shows(p, own=own_words)
                if extra:
                    body = {**body, 'prompt': with_composed(body['prompt'], f"Image {k} also shows {', '.join(extra)}: show none of them.")}
                    lines = list(lines or []) + [{'check': f'not shown: {x}', 'weight': 'must', 'pass_when': f'no {x} anywhere in the frame: it belongs to Image {k}, not to this shot'} for x in extra]   # design/119 rule 4
    if body['kind'] in ('keyframe', 'isolated') and found and named.get('visual_type') == 'image' and size_line(plan, named):   # design/207: the size sentence and its must line on a still's picture too (never on a reference set)
        lines = list(lines or []) + [{'check': 'size is the point', 'weight': 'must', 'pass_when': size_line(plan, named)[len('Size is the point: '):].rstrip('.')}]
        if not body.get('fix_of'):
            body = {**body, 'prompt': with_composed(body['prompt'], size_line(plan, named))}
    if body['kind'] == 'keyframe' and found and named.get('visual_type') == 'video':   # design/110 F4, F5, F6: the lines, and the block under the writer's prompt
        lines = lines + picture_rule_lines(plan, found[2], named, 'end' if is_end else 'start')
        if not body.get('fix_of'):
            body = {**body, 'prompt': with_composed(body['prompt'], composed_block(plan, found[2], named, 'end' if is_end else 'start'))}
    lw = light_warning(found[2], body['kind'], body['prompt']) if found else None   # design/103 A1
    if found and element['kind'] not in ('graphic', 'style') and body['kind'] in ('keyframe', 'isolated'):   # design/104 C5: the scene's light and air, the shot's size, real sizes
        lines = list(lines or []) + picture_lines(found[2], found[3], plan['elements']) + height_lines(found[2])   # design/119 rule 8
        if height_sentence(found[2]) and not body.get('fix_of'):
            body = {**body, 'prompt': with_composed(body['prompt'], height_sentence(found[2]))}
        sg = signs_lines(session, plan, found[2], found[3], body['element_id'])   # design/111 F18: two signs of use, the place in use
        if sg:
            lines.append({'check': 'signs of use', 'weight': 'must', 'pass_when': sg[0][len('Signs of use: '):].rstrip('.') + ': both visible at their places'})
            if not body.get('fix_of'):
                body = {**body, 'prompt': with_composed(body['prompt'], sg[0])}
        pl = place_line(plan, body['element_id'], found[3])   # design/124-b item 4
        if pl:
            lines.append(pl)
    if element['kind'] not in ('graphic', 'style') and body['kind'] in ('keyframe', 'isolated') and not body.get('fix_of'):   # design/111 F18: the real light, once per run, in every prompt
        rl = real_light_line(store, session, found[2] if found else None)
        if rl:
            body = {**body, 'prompt': with_composed(body['prompt'], rl)}
    if lw:
        warns.append(lw)
    warns += [f"made from {p['id']}, which was made for {p['shot_id']}; this picture is listed and checked under {body['shot_id']}"   # design/95 F7: on purpose, or a slip
              for p in parents if body.get('shot_id') and p and p.get('kind') in ('keyframe', 'state') and p.get('shot_id') not in (None, body['shot_id'])]
    if (element['kind'] not in ('graphic', 'style') and not body.get('fix_of') and (body['kind'] in ('keyframe', 'isolated') or named) and body['kind'] not in ('sheet', 'component', 'style')   # design/124 A4 item 14
            and not str(plan['foundation'].get('studio_background') or '').strip()):   # design/91 N9: a picture in the film is in the film's world
        lines.append(WORLD_LINE)
    check_cap(conn, run, session, image_price_inr(run, provider='gemini' if is_set else None) * variants * ((len(body.get('views') or ()) or SET_MAX) if is_set else 1),   # design/213: a set is counted by its pictures (a place of a round posted from now on: one)
              'one image' if variants == 1 else 'a set of three' if is_set else 'two candidates')   # design/65 B7; design/151
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
COMPONENT_BLOCK = ('Image 1 is the approved style of this film: take its palette, line and finish from it. One {name} alone, nothing else in the frame, '
                   'on a transparent background: no ground, no setting, no shadow outside its own edge, the whole thing inside the frame.')   # design/117 P1
COMPONENT_BLOCK_GREEN = ('Image 1 is the approved style of this film: take its palette, line and finish from it. One {name} alone, nothing else in the frame, '
                         'on a flat, even chroma green background (#00FF00) that touches every edge: no ground, no setting, no shadow outside its own edge, no green on the thing itself, the whole thing inside the frame.')   # design/120
STYLE_IMAGE_ONE = 'Image 1 is the approved style of this film: take its palette, line and finish from it. '
STYLE_NOT_NEEDED = ("This film has no graphic in steps, so it has no style sheet (design/217 D5): a drawn graphic takes the plan's palette and lettering from its brief. "
                    'Make the style sheet only when the plan has a graphic in steps.')


def _has_steps(plan):
    """design/217 (D5): the plan has a graphic in steps (an animation shot), the only kind made from the style sheet."""
    return any(sh.get('visual_type') == 'animation' for g in (plan or {}).get('gaps') or [] for sc in all_scenes(g) for sh in sc.get('shots') or [])


GEMINI_MAX_INPUTS, GEMINI_KIND_CAPS = 14, {'object': 6, 'character': 5, 'style': 3}   # design/120: Google's limits for the Pro image model, 28 Oct 2026
WATERMARK = {'check': 'no watermark', 'weight': 'must', 'pass_when': "no watermark, stock site's name or lettering across the picture"}   # design/121 change 5
COMPONENT_LINES = [{'check': 'one thing only', 'pass_when': 'one thing alone: no background, no ground, no setting, no second object, no shadow outside its edge', 'weight': 'must'},
                   {'check': 'clean edge', 'pass_when': 'the edge of the thing is clean and nothing of it is cut off by the frame', 'weight': 'must'}]


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
    warns = [] if answer is not None else ['no answer form with this picture: write it with the library\'s form (--answer), so its checklist is checked']
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
        warns += [f"the label '{s}' uses a sign in place of words: write it as a phrase ('25 % less material', not '↓ 25 %')" for s in labels if LABEL_SIGN.search(s)]
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
        if view_line(sh):   # design/111 F19
            lines.append(view_line(sh))
    if body['kind'] != 'state' and not any(p.get('kind') == 'style' and p.get('status') == 'approved' for p in parents):   # a state is made from the previous state
        warns.append(f'no approved style sheet among the parents: make it once (`vw visuals image --element {STYLE} --kind style`), approve it, and name it in --parents')
    for sh in shots:
        spec = sh.get('drawing_spec')
        if spec and (session.get('spec_approvals') or {}).get(sh['id'], {}).get('digest') != spec_digest(spec):
            warns.append(f"the drawing spec of {sh['id']} is not approved, or changed since: the operator approves the sizes, materials and graphic specs on the page (`vw visuals page`)")   # design/124 A4 item 19
    return _dedupe(lines + label_lines), warns


def _dedupe(lines):
    seen = set()
    return [l for l in lines if not (l['check'] in seen or seen.add(l['check']))]


def researched(label, spec, material=False, real_thing=False):
    """design/124 C2: a spec is approved only when its research is done: every unknown size tried in all four sources, illustrative earned (warned in the plan)."""
    from .visual_contract import DrawingSpec, MaterialSpec, spec_research_needs
    guarded(lambda: spec_research_needs(label, (MaterialSpec if material else DrawingSpec).model_validate(spec), real_thing))


def draws_real_thing(plan, shot):
    """design/221 row 4 (as the plan's `spec_proportions_missing`): a diagram shot that names an object or a material element of the plan."""
    kinds = {e['id']: e.get('kind') for e in plan.get('elements') or []}
    return shot.get('graphic_kind') == 'diagram' and any(kinds.get(e) in ('object', 'material') for e in shot.get('element_ids') or [])


def known_on_things(plan, shot):
    """design/221 (the critic's A4): an object or material element of the shot carries a proportion, or a size that is not unknown, on its own spec."""
    els = {e['id']: e for e in plan.get('elements') or []}
    specs = [(els.get(e) or {}).get('material_spec') or {} for e in shot.get('element_ids') or [] if (els.get(e) or {}).get('kind') in ('object', 'material')]
    return any(s.get('proportions') or any(d.get('status') != 'unknown' and d.get('value') is not None for d in s.get('dimensions') or []) for s in specs)


def _research_fault(label, spec, **kw):
    """The refusal `researched` would give, or '' (so every spec of one approval is named at once)."""
    try:
        researched(label, spec, **kw)
    except Problem as exc:
        return exc.message
    return ''


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
        researched(f'material spec of {element["id"]}', spec, material=True)
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
    plan, _, _, shot = guarded(lambda: locate(store, session, shot_id))
    spec = shot.get('drawing_spec')
    need(spec, f'Shot {shot_id} has no drawing spec.')
    need(not correction_pending(session, shot_id, spec), f'The correction of {shot_id} waits for the assistant to revise the spec; approve the revised one.')   # review 27 Oct
    researched(f'shot {shot_id}', spec, real_thing=draws_real_thing(plan, shot) and not known_on_things(plan, shot))
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
    """design/106 N4: a saved picture's note stays editable; the sheet prompt reads the latest note. design/121 change 4: a note after the sheet marks
    the sheet "sources changed", like a picture added after it, so a new sheet is made with the note."""
    session = session_of(store, run, outputs)
    row = session['references'].get(ref_id)
    need(row and row.get('kind') in ('web', 'frame', 'supplied', 'isolated') and row.get('status') != 'rejected', f'{ref_id} is not a saved picture of an element.')
    row.setdefault('source', {})['note'] = str(note or '').strip()[:500]
    sheets = [r for r in session['references'].values() if r.get('kind') == 'sheet' and r.get('element_id') == row.get('element_id') and r.get('status') != 'rejected']
    for r in sheets:
        r['sources_changed'] = True
    save_session(store, run, session)
    return {'reference_id': ref_id, 'note': row['source']['note'],
            'next': f"Note saved: {row.get('element_id')}'s " + ('sheet is marked "sources changed": the assistant makes a new one with it.' if sheets else 'sheet is made with it.')}


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
    built, faults = False, {}   # design/221 (the critic's A4): every spec that fails is named in one refusal, before anything is saved
    for e in plan.get('elements') or []:   # design/134 6: each material's not-this list, built as the single approval builds it, before anything is approved
        spec = e.get('material_spec')
        if spec and not material_approved(session, e) and not correction_pending(session, material_key(e['id']), spec) and not (session.get('not_this') or {}).get(e['id']):
            fault = _research_fault(f"material spec of {e['id']}", spec, material=True)
            if fault:
                faults[fault] = True
                continue
            try:
                not_this(store, user, run, outputs, e['id'])
                built = True
            except (Problem, ValueError):   # the model call failed: the approval stands; `vw visuals not-this --element` builds the list later
                pass
    if built:
        session = session_of(store, run, outputs)
    approved, waiting_ = [], []
    for _, sh in _accepted_shots(plan, session):
        spec = sh.get('drawing_spec')
        if spec and correction_pending(session, sh['id'], spec):   # review 27 Oct: the assistant's turn, not approved over
            waiting_.append(sh['id'])
        elif spec and (session.get('spec_approvals') or {}).get(sh['id'], {}).get('digest') != spec_digest(spec):
            fault = _research_fault(f"shot {sh['id']}", spec, real_thing=draws_real_thing(plan, sh) and not known_on_things(plan, sh))   # design/124 C2: refused before anything is saved
            if fault:
                faults[fault] = True
                continue
            session.setdefault('spec_approvals', {})[sh['id']] = {'digest': spec_digest(spec), 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
            (session.get('spec_corrections') or {}).pop(sh['id'], None)
            approved.append({'shot_id': sh['id'], 'table': spec_table(spec)})
    for e in plan.get('elements') or []:   # design/111 F10: the material specs too
        spec = e.get('material_spec')
        k = material_key(e['id']) if spec else None
        if spec and correction_pending(session, k, spec):
            waiting_.append(k)
        elif spec and not material_approved(session, e):
            fault = _research_fault(f"material spec of {e['id']}", spec, material=True)
            if fault:
                faults[fault] = True
                continue
            session.setdefault('spec_approvals', {})[k] = {'digest': spec_digest(spec), 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
            (session.get('spec_corrections') or {}).pop(k, None)
            approved.append({'shot_id': k, 'element_id': e['id'], 'table': spec_table(spec)})
    need(not faults, ' '.join(faults))
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
    need(frames and all(frames), 'Measure reads approved footage frames only: name frames taken from the clips (`vw visuals status` lists them).')
    for rid, f in zip(ref_ids, frames):   # defect 40: say which frame and why, and the approved ones to use
        if f.get('kind') == 'supplied' and f['status'] == 'approved':   # release 3 (F17): the operator's own picture is read as a footage frame is
            continue
        if f.get('kind') != 'frame' or f['status'] != 'approved':
            ok = [r['id'] for r in session['references'].values() if r.get('kind') == 'frame' and r.get('status') == 'approved' and r.get('element_id') == f.get('element_id')]
            why_ = 'was rejected in the picture round' if f.get('status') == 'rejected' else f"is a {f.get('kind')} picture, not an approved footage frame" if f.get('kind') != 'frame' else f"is {f.get('status')}"
            need(False, f"{rid} {why_}: measure reads approved footage frames only" + (f"; {f.get('element_id')}'s: {', '.join(ok)}." if ok else f"; {f.get('element_id')} has none: approve one first."))
    where = [f"the operator's own picture {f.get('name') or f['id']}" if f.get('kind') == 'supplied' else
             f"clip {(f.get('source') or {}).get('media_id')} at {(f.get('source') or {}).get('requested_s')} s" for f in frames]
    parts = []
    for n, (f, w) in enumerate(zip(frames, where), 1):
        parts += [{'text': f'Frame {n}, {w}.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(f['key'])).decode()}}]
    parts.append({'text': 'Measure from these frames: ' + question.strip()[:1000] + '\nScale each size against something of known size in the same frame (a door, a chair, a hand tool, a person) '
                          'and say which in how. Give the frame number each size is read from. Measure only what is visible; say in limits what cannot be read.'})
    need(keys.pool('gemini', settings()), 'No Gemini key on the server.')
    try:
        received, _ = keys.gemini(_gemini_transport(), MEASURE_MODEL, lambda t: t.generate(
            {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': MEASURE_SCHEMA, 'maxOutputTokens': 32768}}),
            settings(), terminal_deadline_seconds=180, initial_soft_wait_seconds=30, on_update=lambda e: None, capture_answer_deltas=False)   # design/114
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
    frame = aspect_of(run, outputs, body['kind'])   # design/71 P3, design/139 R1: the size follows the shape the picture is for
    first = parents[0] if parents and parents[0].get('kind') in ('keyframe', 'frame') else None   # an edit of a keyframe or a frame keeps that picture's size when GPT Image accepts it
    provider = 'gemini' if body.get('set') else provider_of(run)   # design/120: the run's image model; design/151 hotfix: a set is the kept (Gemini) method on every film
    if provider == 'gemini':
        size = {'aspect': frame if frame in ('16:9', '9:16') else '16:9', 'tier': settings().GEMINI_IMAGE_SIZE}
        model = settings().GEMINI_IMAGE_MODEL
    else:
        size = body.get('size') or (library.edit_size(first.get('width'), first.get('height'), frame) if first else library.default_size(frame))
        model = body.get('model') or IMAGE_MODELS[op]
    board, board_line = look_parent(session, provider, body, element, len(parents))   # SK, 23 Nov 2026: no camera footage, Nano Banana: the look picture goes with the words
    request = {'kind': 'image', 'op': op, 'provider': provider, 'model': model, 'prompt': body['prompt'] + board_line, 'size': size,
               **({'background': 'transparent'} if body['kind'] == 'component' and provider == 'openai' else {}), **({'chroma_key': True} if body['kind'] == 'component' and provider == 'gemini' else {}),
               'quality': body.get('quality') or 'high', 'parents': [cropped_parent(store, run, p, (body.get('crops') or {}).get(p['id'])) for p in parents] + ([board] if board else []),
               **({'set': True, 'views': list(body.get('views') or [])} if body.get('set') else {}), **({'search': True} if body.get('search') else {}),   # design/151; section 13: the views, one per turn
               **({'view_names': list(body['view_names'])} if body.get('set') and body.get('view_names') else {}),   # design/211: the short name of each view, written on its picture
               'reference': {'id': ref_id, 'element_id': body['element_id'], 'element_kind': element['kind'], 'name': name, 'kind': body['kind'], 'subject': body['subject'],
                             **({'fix_of': body['fix_of']} if body.get('fix_of') else {}), **({'role': body['role']} if body.get('role') else {}),
                             **({'golden_candidate': True} if body.get('golden') else {})},   # design/96 X3; design/106 T1; design/111 F11
               **({'region': body['region']} if body.get('region') else {})}
    row = conn.execute("insert into vw2_jobs(run_id, stage, unit, request, request_id, provider) values (%s,'visuals',%s,%s,%s,%s) returning id",
                       (run['id'], ref_id, Jsonb(request), request_id, 'openai' if provider == 'openai' else 'gemini-image')).fetchone()   # design/120: the job family by provider, last so the older readers of the params keep their places
    session['references'][ref_id] = {**request['reference'], 'id': ref_id, 'status': 'generating', 'job_id': str(row['id']), **({'set': ref_id, 'set_n': 1} if body.get('set') else {}), 'generation': {k: request[k] for k in ('op', 'provider', 'model', 'prompt', 'size', 'quality', 'parents') + (('background',) if request.get('background') else ()) + (('chroma_key',) if request.get('chroma_key') else ()) + (('region',) if request.get('region') else ())},
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
                   "the packet carries the start instructions and the library's job form.")
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
            _not_yet_gate(store, run, session, row, at_approval=True)   # design/110 F3, rule 0 fork 5
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
    if row.get('parent_wanted'):   # fix set A2.2: approved as a picture another picture is made from: the same answer allows it as the parent (the fork-4 question is not asked after it)
        row['parent_ok'] = True
    if row.get('golden_candidate'):
        session.setdefault('golden', {})[row['element_id']] = ref_id
    if row.get('kind') == 'sheet' and row.get('set_n') in (None, 1):   # a person's identity sheet is its golden picture (design/151: picture 1 of the set)
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
    if sid and row.get('kind') in ('keyframe', 'isolated') and not round_v2(session):   # design/111 F17: background figures against the approved pictures of the scene; design/217 (C5): on a v2 film a line of Claude's list, before the answer (this call kept until the older films close)
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


FIX_RETIRED = ('The fix round is retired (design/217): a picture is changed only by "Correct it", the operator\'s words with Claude\'s failed lines written in the box. '
               'Reject the picture with the operator\'s words (`vw visuals reject --ref R --notes "…"`) and write the new request from them.')
BARE_NO = ('no', 'no, make another', 'rejected', 'reject')   # design/217 (F4, D7): a button pressed, not a reason


def request_fix(conn, store, user, run, outputs, ref_id):
    """design/96 X1, X4: one fix round of a candidate, only when the operator or the assistant asks: an edit with the one change its first failed must
    line asks for, at the image price, inside the cap. Never for a fix, never twice, never for a line the check could not decide.
    design/217 (D3, SK 18 Nov 2026): retired. "Correct it" is the one way to change a picture; its box opens with Claude's failed lines."""
    need(False, FIX_RETIRED)
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
    return {'reference_id': out['reference_id'], 'of': ref_id, 'for': failed[0]['check'], 'cost_inr': image_price_inr(run), 'next': 'Fix requested: it appears here in about a minute.'}


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
    sid = made_for(session, row)
    if word == 'start image':   # design/124 A4 item 4: an end comes next only where the shot's end must be exact
        try:
            exact = bool(locate(store, session, sid)[3].get('end_state_exact'))
        except Exception:
            exact = False
        return (f"Approved: this shot's end must be exact: its end image is made from this start next (`vw visuals image --element {row.get('element_id')} --kind keyframe --role end --parents {row['id']} --region …`)."
                if exact else f"Approved: the take for {sid} is the next step.")
    if word == 'reference sheet':   # design/124 A4 item 11: a thing's golden picture comes next; a person's sheet is its golden picture
        try:
            person = {e['id']: e.get('kind') for e in current_plan(store, session)['elements']}.get(row.get('element_id')) == 'person'
        except (ValueError, Problem, KeyError, StopIteration):
            person = False
        return f"Approved: the shots of {row.get('element_id')} are made from it." if person else f"Approved: the golden picture of {row.get('element_id')} is made from it next."
    return {'end image': f"Approved: the take for {sid} is the next step.",
            'state': 'Approved: the sequence is approved as a whole once every state is in.', 'style sheet': "Approved: every graphic's first picture is made from it."}.get(word, 'Approved.')


def reject_reference(store, user, run, outputs, ref_id, notes, quote):
    """design/74 L7: a picture rejected with the operator's words; it is never approved, bound, held or named as a parent afterwards."""
    session = session_of(store, run, outputs)
    row = session['references'].get(ref_id)
    words = str(quote or '').strip()
    reason = str(notes or '').strip() or ('' if words.lower().rstrip('.') in BARE_NO else words)   # design/217 (F4): a bare "No" stores no reason; nothing joins the not-this list or the library
    if row and row.get('status') == 'rejected' and reason and row.get('rejection'):   # design/99 C3: the reason given after the click joins the same rejection
        row['rejection']['notes'] = reason
        _feedback_image(session, run, user, row, 'reject', row['rejection']['quote'], reason)
        try:
            _not_this_add(store, session, current_plan(store, session) if session.get('current') else None, row.get('element_id'), reason)   # design/111 F12
        except (ValueError, Problem):
            pass
        save_session(store, run, session)
        return {**row, 'next': _rejected_next(store, session, row)}
    need(row and row['status'] in ('candidate', 'approved'), f"Reference {ref_id} is not a candidate or approved picture (it is {(row or {}).get('status') or 'unknown'}); only those can be rejected.")
    need(not verdict_lock(session, row), verdict_lock(session, row))   # U17: not once a later step used it
    quote = said(words, 'Rejected', user)   # design/99 C3: the reason is optional
    if row.get('kind') == 'supplied':   # U19: a stored answer of step 2 that chose it asks for its starting picture again
        for r in ((session.get('round') or {}).get('elements') or {}).values():
            if (r.get('answer') or {}).get('golden') == ref_id:
                r['answer']['golden'] = None
    row.update(status='rejected', rejection={'notes': reason, 'quote': quote, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()})
    _feedback_image(session, run, user, row, 'reject', quote, row['rejection']['notes'])
    try:   # design/111 F12: the rejection's words join the element's not-this list at once
        _not_this_add(store, session, current_plan(store, session) if session.get('current') else None, row.get('element_id'), reason)
    except (ValueError, Problem):
        pass
    save_session(store, run, session)
    return {**row, 'next': _rejected_next(store, session, row)}   # design/97 A4


def _slot(session, row):
    """The place a made picture stands in: its kind, its shot (or its element), and for a start or an end image which of the two; for a state the picture it follows."""
    parents = [p.get('id') for p in (row.get('generation') or {}).get('parents') or []]
    part = None
    if row.get('kind') == 'keyframe':
        part = 'end' if row.get('role') == 'end' or (not row.get('role') and any((session['references'].get(p) or {}).get('kind') == 'keyframe' for p in parents)) else 'start'
    elif row.get('kind') == 'state':
        part = parents[0] if parents else None
    return row.get('kind'), made_for(session, row) or row.get('element_id'), part


def verdict_lock(session, row):
    """U17 (SK, 11 Nov 2026): a verdict on one picture is changed both ways (approved to rejected, rejected to approved) until a later step has used it.
    Returns why it can no longer be changed, in the operator's words, or None. Used: a footage picture answered at step 1 of a kept round, once that step is done; an approved
    picture placed in a shot, or one a sheet was made from, or the operator's own picture recorded as a starting picture; a rejected picture of a set
    (a set is judged as a whole), a rejected source once the element has a sheet, a rejected made picture while another one stands in its place.
    Not locked, as before: a start image an end image or a take was made from."""
    rid, eid, kind, status, refs = row['id'], row.get('element_id'), row.get('kind'), row.get('status'), session['references']
    if status not in ('approved', 'rejected'):
        return None
    here = 'it can no longer be changed here'
    live = lambda x: x.get('status') not in ('rejected', 'failed')
    rd = session.get('round') or {}
    if kind == 'frame' and rd.get('kept') and rd.get('pass') != 1 and rid in (((rd.get('elements') or {}).get(eid) or {}).get('frames') or []):   # answered at step 1; a frame grabbed later is not
        return f"Step 1 of the reference round is done with this picture {'used' if status == 'approved' else 'ignored'}; {here}."
    if status == 'approved':
        shot = next((sid for sid, a in (session.get('assets') or {}).items() if a.get('reference_id') == rid or any(st.get('reference_id') == rid for st in a.get('states') or [])), None)
        if shot:
            return f'This picture is placed in shot {shot}; take it out of the shot first.'
        if any(x.get('kind') == 'sheet' and live(x) and any(p.get('id') == rid for p in (x.get('generation') or {}).get('parents') or []) for x in refs.values()):
            return f'A sheet was made from this picture; {here}.'
        if kind == 'supplied' and golden_of(session, eid) == rid:
            return f'This picture is recorded as the starting picture; {here}.'
        return None
    if kind == 'sheet' and row.get('set') and kept(session):
        return 'This picture was answered with its set on step 2 of the reference round: a set is judged as a whole.'
    if kind in ('frame', 'web', 'supplied'):
        if not kept(session) and any(x.get('kind') == 'sheet' and x.get('element_id') == eid and live(x) for x in refs.values()):
            return f'A sheet was made after this picture was rejected; {here}.'
        return None
    if any(x['id'] != rid and live(x) and _slot(session, x) == _slot(session, row) for x in refs.values()):   # ponytail: any live picture of the same place, older or newer (a made picture carries no time); reject that one first
        return f'Another picture stands in its place now; {here} while that one stands.'
    return None


def reapprove_reference(store, user, run, outputs, ref_id, sha256, quote, conn=None):
    """U17: a rejected picture approved after all, until a later step used it (verdict_lock). It goes through approve_reference, with every gate of an
    approval; refused there, it stays rejected as it was. Its earlier rejection is kept as history (`rejections`). The older way, kept: approve_reference
    itself still refuses a rejected picture (design/74 L7); this function is the only way back."""
    session = session_of(store, run, outputs)
    row = session['references'].get(ref_id)
    need(row and row.get('status') == 'rejected', 'Only a rejected picture is approved again this way.')
    need(not verdict_lock(session, row), verdict_lock(session, row))
    row['status'] = 'candidate'
    save_session(store, run, session)
    try:
        out = approve_reference(store, user, run, outputs, ref_id, sha256, quote, conn)
    except Exception:
        session = session_of(store, run, outputs)
        session['references'][ref_id]['status'] = 'rejected'
        save_session(store, run, session)
        raise
    session = session_of(store, run, outputs)
    r = session['references'][ref_id]
    if r.get('rejection'):
        r.setdefault('rejections', []).append(r.pop('rejection'))
    save_session(store, run, session)
    return {**out, 'rejection': None}


def _rejected_next(store, session, row):
    """design/124 A4 item 12: what follows a rejection, by kind: a web pick or a frame waits for the operator's words; a generated picture is made again."""
    if row.get('kind') == 'frame' and kept(session):   # follow-up, 11 Nov 2026: a kept film has no search
        return "The picture is ignored. The element's set will be made from its description."
    if row.get('kind') in ('web', 'frame', 'supplied'):
        return "Rejected: the next search or frame comes from the operator's words, or Ignore this; nothing is searched or made without them."
    word = _picture_word(store, session, row)
    return f'Rejected: the assistant makes a new {word} with your note' + {'end image': ', from the approved start, never from this one.',
                                                                          'state': ', from the last approved state, never from this one.'}.get(word, '.')


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
              prompt=(prep or {}).get('effective_prompt' if (prep or {}).get('kind') in GUIDE_KINDS else 'motion_prompt') or '', checklist=answer.get('checklist'), suggestion=answer.get('suggestion'), model=(prep or {}).get('model'), inputs=inputs)


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
    elements = {e['id']: e for e in plan['elements']}
    required = {eid for eid in shot['element_ids'] if (elements.get(eid) or {}).get('kind') != 'animal'}   # design/207 (D4): a living extra has no reference; its words carry it
    need(required <= set(references) <= set(shot['element_ids']), 'Cover every required shot element with approved references: ' + ', '.join(sorted(required - set(references))))
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


def across(plan, session, shot):
    """SK, 23 Nov 2026 (no footage, release 4, V4): the accepted shot that ends where this one starts and the one that starts where it ends, in
    film order, whatever their gap: (before, after); None where a camera clip, or nothing, stands there."""
    rows = [s for _, s in _accepted_shots(plan, session) if s['id'] != shot['id']]
    return next((s for s in rows if s['end_frame'] == shot['start_frame']), None), next((s for s in rows if s['start_frame'] == shot['end_frame']), None)


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
    if i is not None:   # release 4 (V4): at the gap's edge, the shot of the touching gap, in film order
        prev_shot, next_shot = prev_shot or across(plan, session, shot)[0], next_shot or across(plan, session, shot)[1]
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
                        'rule': 'name the geometry in nouns; the pattern is demanded on the checklist at medium and close shots only' + ('' if carriers else '; no close reference is bound yet: bind its golden picture (before one exists, a footage frame)')})
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
    start_instruction = ('Write the start prompt; only where the shot has end_state_exact, write the end\'s request with it (end_prompt, end_answer, end_region: one region, a third of the frame at most). '
                         'Compose the start for the whole segment: every visible subject, '
                         'including secondary/background subjects, in its start state in the named scene layout, what the motion heads for already in frame, room in the frame '
                         'for the move, nothing the end state needs cut off or hidden, nothing placed where the end would have to remove it. Keep landmark-relative locations; '
                         'the camera only changes their screen projection. Where a segment has an end image, it is the start image of the next only within one continuous shot, '
                         'same place and framing; a cut starts afresh with its own start image. Name one human-scale anchor against a named landmark '
                         '(a person beside a doorway, a hand on a course) so the scale is fixed; the landmarks are listed under scene.landmarks.')   # design/67 B; design/74 L24; design/77 L39
    end_instruction = ('Only for a shot with end_state_exact: the server makes the end image from the approved start (from the request written with the start); '
                       'the start\'s own references go with it. The request shows every subject in its end state '
                       'as the plan gives it: its position against its landmark and its side of the frame, its facing, its pose, what it holds, how far the work has gone; for an '
                       'acting subject the result of its last beat. Name the positions in words. Change only what lies inside the region: the same framing, camera, light, people and props. Keep in '
                       'frame whatever the motion heads for. Image 1 is the start image; images 2 onward are its own references, sent by the server: take identity from them, '
                       'nothing else. The camera does not move between the two images: the same framing, lens and position. The end shows the action\'s visible result, a '
                       'different pose or state from the start, never the same frozen pose. Carry each line of end_targets word for word: it is where every subject ends.')   # design/67 C; design/71 P1; design/77 L38; design/86 K6
    prompt = {'foundation': plan['foundation'], 'scene': {k: v for k, v in scene.items() if k != 'shots'}, 'shot': {k: v for k, v in shot.items() if k != 'warning_answers'}, 'references': refs,   # design/124 Change 7
              'end_targets': end_targets(scene, shot),   # design/86 K6: the end state of each subject as one sentence the end prompt carries word for word
              'context': packet_context(session, plan, gap, shot),   # design/86 K7: the gap's words, the treatment's picture, the intended visuals, the neighbours, earlier rejections
              'exact_patterns': exact_patterns(plan, shot, refs),   # design/86 K8: client patterns and the reference that carries each
              'sequence_rules': plan.get('sequence_rules', []), 'elements': [e for e in plan['elements'] if e['id'] in shot['element_ids']],
              'start_image_instruction': start_instruction,   # design/124 C3: the old alias image_instruction is gone
              'end_image_instruction': end_instruction,
              'video_instruction': 'Read the actual accepted starting image before writing movement. For EACH subject, follow the ordered beats, targets, paths, contacts, object responses and final progress. Keep non-acting subjects where they are. '
                                   'The take is one unbroken shot: write the motion so nothing enters the frame that the start (or the end, where the shot has one) does not show. Write the continuity line (`--continuity`): what stays unchanged through the shot (and between the start and the end image where there is one), and for a person five traits from the sheet.',   # design/84 V3
              'checks': ['Treatment and narrated meaning', 'All visible subjects accounted for', 'World-relative layout and scale', 'Secondary action progression', 'Reference identity', 'Boundary continuity', 'Exact placement duration'],
              'footage_character': {k: (footage_view(session, outputs) or {}).get(k) for k in ('line', 'summary')},   # design/77 L42; design/88: measured, the correction winning
              'provider': {k: generator[k] for k in ('provider', 'model')}}
    prompt['context'] = {**prompt['context'], 'ambient': {'line': scene.get('ambient') or '', 'instruction': AMBIENT_START},
                         'guidance': shot_guidance(shot, prompt['context'].get('footage_neighbours') or {}, category_of(run)),   # design/102: in the context, so no take goes stale
                         'bind_advice': bind_advice(plan, session, shot),   # design/104 D1, D2   # design/101 M5: in the context, so no take goes stale
                         'start_targets': {'lines': start_targets(scene, shot), 'instruction': NOT_YET_START}}   # design/110 F3: in the context, so no take goes stale
    identity = digest({**{k: v for k, v in prompt.items() if k not in ('context', 'footage_character')}, 'scene': note_free_scene(prompt['scene']),   # design/101, 103
                       'shot': note_free_scene({'shots': [prompt['shot']]})['shots'][0], 'elements': note_free_elements(prompt['elements'])})   # the composition only: the context, the footage and the library inform the writer and never make a prepared take stale (design/88)
    brief = next((o['summary'] for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None)
    steps_ = library.steps_of(shot)   # design/68 L3: the library beside the three instructions; the texts are in work/visuals/library/, written at prepare
    prompt['library'] = {'version': library_version_of(session),
                         'steps': [{'step': st, 'task': library.STEPS[st]['task'], 'playbook': library.STEPS[st]['playbook'], 'files': library.step_files(st, generator, film.footage(run))} for st in steps_],
                         'job_forms': {st: library.job_form(st, run=run, plan=plan, gap=gap, scene=scene, shot=shot, refs=refs, generator=generator, brief=brief, card=card, rules=list(rules or []),
                                                            fps=float(Fraction(session['source']['fps']))) for st in steps_}}
    return {'plan_digest': session['current'], 'gap_id': gap['gap_id'], 'shot_id': shot_id, 'preparation_digest': identity, 'preparation': prompt,
            'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame'], 'fps': session['source']['fps']}}


# ---------- takes ----------

def select_generator(store, user, run, outputs, shot_id, provider, model):
    """design/124 A4 decision 5: Omni only; choosing it sets a shot back from a retired choice."""
    session = session_of(store, run, outputs)
    guarded(lambda: video_generators.GeneratorChoice(shot_id=shot_id, provider=provider, model=model))
    session['generator_choices'][shot_id] = {'provider': provider, 'model': model, 'plan_digest': session['current']}
    save_session(store, run, session)
    return session['generator_choices'][shot_id]


def aspect_of(run, outputs, kind, body=None):
    """design/139 R1: a take and its start and end pictures (keyframes) are the AI video shape, every other picture the film's; a request that says one wins.
    A film from before keeps the old reading: pictures by the brief's frame, takes 16:9 (the tool never sent one)."""
    if (body or {}).get('aspect_ratio'):
        return body['aspect_ratio']
    if film.older(run):
        brief = next((o['summary'] for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None)
        return '16:9' if kind == 'take' else (((brief or {}).get('production') or {}).get('format') or {}).get('frame') or '16:9'
    film.timeline(run)
    return film.frame(run, video=kind in ('take', 'keyframe'))


def _route_gate(shot, wanted):
    """design/65 B2', B3: a video shot takes a take, a still shot a still, an animation shot a graphic sequence."""
    vt = shot['visual_type']
    if vt == wanted or (wanted == 'still' and vt in STILL_TYPES + ('footage',)):   # design/124-b item 1: a footage shot takes a footage frame (or a clip stretch)
        return
    takes = {'video': 'a take (`vw visuals prepare-take`)', 'animation': 'a graphic sequence (`vw visuals sequence`)',
             'footage': 'a clip stretch (`vw visuals clip`) or a footage frame (`vw visuals still`)', 'drawn': 'a drawing (`vw visuals draw --shot S`)'}.get(vt, 'a still (`vw visuals still`)')
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
        if (e['kind'] == 'material' or (e['kind'] == 'object' and e.get('identity') == 'exact')) and shot.get('size', '') in ('', 'MS', 'MCU', 'CU', 'ECU') and not golden_of(session, e['id']):   # D1; design/124 A4 item 17: the golden picture carries it
            out.append({'element_id': e['id'], 'use': 'texture', 'reference_ids': frames(e['id']), 'line': 'the texture reference: take only its surface: its colour, wear and joints'})
        if e['kind'] == 'place':   # D2
            out.append({'element_id': e['id'], 'use': 'look', 'reference_ids': frames(e['id']), 'line': 'the look reference: take only its light and colour'})
    return out


def light_warning(scene, kind, prompt):
    """design/103 A1: a keyframe in a lit scene names the scene's light word for word; a warning in this release."""
    light = (scene or {}).get('light', '').strip().rstrip('.')
    if kind == 'keyframe' and light and light not in prompt:
        return f"the prompt does not carry the scene's light sentence word for word ('{light}'): one light per scene, so the shots match"
    return None


def shot_guidance(shot, neighbours, category=library.DEFAULT_CATEGORY):
    """design/102 (course batch B): the lines for this shot's pictures and take; a graphic gets none, a close-up no layers, a still no camera line."""
    if shot.get('visual_type') in GRAPHIC_TYPES:
        return []
    lines = []
    if 'close' not in str(shot.get('framing') or '').lower():   # B1
        lines.append('Name a foreground, a midground and a background. When the camera travels, write the parallax: what is near slides past faster than what is far.')
    lines += ['Where a face is hidden or small, carry the action in the hands, shoulders and posture, beat by beat.',   # B2
              'Two or three imperfections at their places in this shot, not copied from the scene. Work leaves traces: tools left out, offcuts, spills, '
              'footprints where people work; signs of use in a place that is lived in.',   # B8
              ('The product may sit centred as the hero; elsewhere thirds, with leading lines and room ahead of a moving subject. '   # design/139 R12: by category
               if category == 'advertisement-product' else 'Thirds by default, the centre only on purpose; use leading lines and give a moving subject room ahead. ') +
              'To show a task, a first-person frame with the hands in front is an option.']   # B10, B13
    support = {(s or {}).get('support') for s in neighbours.values()} - {None, 'unknown'}
    if shot.get('visual_type') == 'video' and support:   # B4; design/124 A4 decision 2: steady takes, never handheld movement asked for
        lines.append(('The clips beside this gap are handheld, but the take stays steady: ' if 'handheld' in support else 'The clips beside this gap are steady: ')
                     + "the take is locked off on a tripod unless the shot's camera_move names its one move.")
    return lines


AMBIENT_START = ("Put in the frame what the scene's ambient line says moves (the trees, the people in the background, the dust in the light), "
                 'so the take can move it.')   # design/101 M5


OLD_PROMPT_RUNS = {'VW-12'}   # design/128 T4: these runs keep the take prompt without a timeline (design/35 old ways: until VW-12 closes)
TIMES_IN_PROMPT = re.compile(r'\b\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*s\b|\bat\s+\d+(?:\.\d+)?\s*s(?:econds?)?\b', re.I)


def take_prompt_fields(run, plan, shot, fps, duration):
    """design/128 T1, T2: the beats of every acting subject in seconds from the shot's start, in time order, and the end state from the change list.
    Empty for a run in OLD_PROMPT_RUNS (today's prompt). A beat that cannot be timed is refused by name, never sent half built."""
    if (run or {}).get('code') in OLD_PROMPT_RUNS:
        return {}
    names = {e['id']: e.get('name') or e['id'] for e in plan.get('elements') or []}
    timeline = []
    for s in shot.get('subjects') or []:
        for b in s.get('beats') or []:
            try:
                timeline.append({'start_s': round((b['start_frame'] - shot['start_frame']) / float(fps), 1), 'end_s': round((b['end_frame'] - shot['start_frame']) / float(fps), 1),
                                 'name': names.get(s['element_id'], s['element_id']), 'action': str(b.get('action') or '').strip().rstrip('.'), 'result': str(b.get('result') or '').strip().rstrip('.')})
            except (KeyError, TypeError, ValueError) as exc:
                need(False, f"shot {shot.get('id')}: beat {b.get('id')} cannot be timed ({exc.__class__.__name__}); fix the plan's beat.")
    timeline.sort(key=lambda t: t['start_s'])   # stable: subjects keep their order when beats start together
    end = [str(c.get('what') or '').strip().rstrip('.') for c in shot.get('changes') or [] if str(c.get('what') or '').strip()]
    end += end_places(plan, shot)   # design/149 B9 (SK, 3 Nov 2026): where every subject and prop is when the take ends; nothing in the frame vanishes
    return {'prompt_version': 2, **({'timeline': timeline} if timeline else {}), **({'end_state': end} if end else {})}


def end_places(plan, shot):
    """design/149 B9: one line per subject (its end position against its landmark, its pose) and per prop (in hand, set down where, carried out by whom)."""
    names = {e['id']: e.get('name') or e['id'] for e in plan.get('elements') or []}
    marks = {}
    for g in plan.get('gaps') or []:
        for sc in list(g.get('scenes') or []) + [x for c in g.get('choices') or [] for x in c.get('scenes') or []]:
            if any(sh.get('id') == shot.get('id') for sh in sc.get('shots') or []):
                marks = {l['id']: l.get('description') or l['id'] for l in sc.get('landmarks') or []}
    def place(pos):
        if not pos:
            return ''
        where = f"{str(pos.get('relation') or '').strip()} {marks.get(pos.get('landmark_id'), pos.get('landmark_id') or '')}".strip()
        amount = pos.get('amount')
        return where + (f", {amount:g} {pos.get('unit') or ''}".rstrip() if isinstance(amount, (int, float)) and amount else '')
    out = []
    for s in shot.get('subjects') or []:
        end = s.get('end') or {}
        bits = [b for b in (place(end.get('position')), str(end.get('pose') or '').strip()) if b]
        if bits:   # a plan that gives no end (an older fixture, a held-only sketch) adds no line
            out.append(f"{names.get(s['element_id'], s['element_id'])}: " + ', '.join(bits))
    for p in shot.get('props') or []:
        e = p.get('end') or {}
        how = {'in_hand': f"still in the hand of {names.get(p.get('holder'), p.get('holder'))}", 'set_down': 'set down ' + place(e.get('position')),
               'carried_out': 'carried out: ' + str(e.get('cause') or '').strip()}.get(e.get('where'), '')
        if how:
            out.append(f"{names.get(p['element_id'], p['element_id'])}: {how}")
    return out


def take_prompt_warnings(plan, shot, motion_prompt, timeline_sent=True):
    """design/128 T3: one person in the shot described as a man or a woman, and the motion prompt uses the other's pronoun: a warning, never a refusal.
    And a motion prompt that names its own times, beside the plan's timeline."""
    out, text = [], str(motion_prompt or '')
    people = [e for e in plan.get('elements') or [] if e.get('kind') == 'person' and e['id'] in (shot.get('element_ids') or [])]
    if len(people) == 1:
        d = str(people[0].get('description') or '').lower()
        woman, man = bool(re.search(r'\bwom[ae]n\b', d)), bool(re.search(r'\bm[ae]n\b', d))
        if woman and not man and re.search(r'\b(he|his|him)\b', text, re.I):
            out.append(f"{people[0].get('name')} is described as a woman, and the motion prompt says he, his or him: make them agree.")
        if man and not woman and re.search(r'\b(she|her|hers)\b', text, re.I):
            out.append(f"{people[0].get('name')} is described as a man, and the motion prompt says she, her or hers: make them agree.")
    if timeline_sent and TIMES_IN_PROMPT.search(text):
        out.append("the motion prompt names its own times; the plan's timeline is sent too: make them agree.")
    return out


def prepare_take(store, user, run, outputs, body):
    session = session_of(store, run, outputs)
    plan_full, _, _, planned = guarded(lambda: locate(store, session, body['shot_id']))
    _route_gate(planned, 'video')
    _no_question(session, body['shot_id'], body.get('start_image'), body.get('end_image'))   # design/110 rule 0
    need(body.get('start_image'), 'A start image is required.')
    if session['references'].get(body['start_image']):
        try:
            _not_yet_gate(store, run, session, session['references'][body['start_image']], shot=planned)   # design/110 F3: never a take from a start that shows the result
        except ValueError:
            save_session(store, run, session)
            raise
    need(body.get('end_image') or not planned.get('end_state_exact'), "This shot's final state must be exact (end_state_exact): write its end with the start (`end_prompt`, `end_region`); "
                                                                      'the server makes the end once the start is approved; then `--start R --end R2`.')   # design/124 decision 9   # design/66 C2, narrowed by design/112 S1: start alone by default
    need(body['start_image'] != body.get('end_image'), 'The start and end images are distinct pictures: the end is the start one small action further on.')
    library.check_prompt(body['motion_prompt'])   # design/71 F2 (a ValueError: the API wraps this call in guarded())
    answer = body.get('answer')
    if answer is not None:   # design/68 L5
        try:
            library.check_answer(answer, body['motion_prompt'])
        except ValueError as exc:
            need(False, str(exc))
    need(str(body.get('continuity_notes') or '').strip(), 'Continuity notes are required: what stays unchanged through the shot (and between the start and the end image when the shot has one), and for a person five traits from the sheet (`--continuity`).')   # design/84 V2
    base = packet(store, run, outputs, body['shot_id'], session)
    shot = base['preparation']['shot']
    need(set(body['subject_reconciliation']) == {s['element_id'] for s in shot['subjects']}, 'Reconcile every subject of the shot, exactly those: ' + ', '.join(s['element_id'] for s in shot['subjects']))
    selected = base['preparation']['provider']
    cap = next((c for c in video_generators.CATALOG if c['provider'] == selected['provider'] and c['model'] == selected['model']), None)
    if cap is None:   # design/124 A4 decision 5: a shot that chose Kling or Seedance keeps its takes, but no new take is prepared on them
        was = (video_generators.known(selected['provider'], selected['model']) or {}).get('label', selected['model']).split(' ·')[0]
        need(False, f"shot {body['shot_id']} chose {was}, which is no longer offered. {video_generators.OMNI_ONLY} Set the shot back to Omni "
                    f"(`vw visuals generator --shot {body['shot_id']} --provider google --model {video_generators.OMNI}`), then prepare the take again.")
    fps = Fraction(session['source']['fps'])
    exact = Fraction(shot['end_frame'] - shot['start_frame']) / fps
    need(exact <= cap['max_seconds'], f"shot {shot['id']} is {float(exact):.1f} s, longer than {cap['label'].split(' ·')[0]}'s maximum {cap['max_seconds']} s: "
                                      "split the shot where an action begins or ends")   # design/45 10.7: refuse, never clamp; design/124 A4 decision 5
    duration = body.get('duration_seconds') or max(cap['min_seconds'], -(-exact.numerator // exact.denominator))  # ceil, at least the generator's minimum
    need(cap['min_seconds'] <= duration <= cap['max_seconds'], f"Duration {duration}s is outside {cap['label']} ({cap['min_seconds']}–{cap['max_seconds']}s).")
    images, form = {}, []
    for role in ['start_image'] + (['end_image'] if body.get('end_image') else []):   # design/112 S1
        rid = body[role]
        row = session['references'].get(rid)
        need(row and row['status'] == 'approved', f'{role} must be an approved reference.')
        images[role] = {'reference_id': rid, 'sha256': row['sha256'], 'key': row['key'], 'mime_type': 'image/png', 'width': row.get('width'), 'height': row.get('height')}
    used = [sid for sid, rid in _start_images(store, session).items() if rid == body['start_image'] and sid != body['shot_id']] + \
           [sid for sid, a in session['assets'].items() if sid != body['shot_id'] and a.get('reference_id') == body['start_image']]
    warns, form = [], form + ([] if answer is not None else ['no answer form with this take: write the motion prompt with the library\'s form (--answer), so its checklist is checked'])   # design/89 C4
    beats = {b['id']: b for s in planned.get('subjects') or [] for b in s.get('beats') or []}   # design/91 N1: when each change happens is its beat's frames
    changes = [{'what': c['what'], 'beat_id': c['beat_id'], 'at_s': [round((beats[c['beat_id']]['start_frame'] - planned['start_frame']) / float(fps), 2),
                                                                     round((beats[c['beat_id']]['end_frame'] - planned['start_frame']) / float(fps), 2)]}
               for c in planned.get('changes') or [] if c.get('beat_id') in beats]
    if not changes:
        form.append('no change list on this shot: list what the action changes and the beat that causes each (changes), so the take (and the pair, where there is one) is checked')
    _rule(session, not used, f"{body['start_image']} is already the start of {used[0] if used else ''}; two shots never share a start image (an end image may start the next segment of one shot).", warns)
    s, e = images['start_image'], images.get('end_image')
    align = None
    if e:   # design/112 S3: the pair's alignment, measured in code before anything else reads it
        try:
            align = image_check.pair_alignment(store.get(s['key']), store.get(e['key']))
        except Exception as exc:
            form.append(f'the pair alignment was not measured ({exc.__class__.__name__}): compare the framing of the two pictures yourself')
        if align:
            need(align['pass'], f"The end image is not aligned with the start: {align['seen']}: make the end again as an edit of the start inside a region (`--region`), "
                                'or set the shot start-only (end_state_exact false).')
    if e and all((s['width'], s['height'], e['width'], e['height'])):   # design/71 P3: the pair shares its aspect ratio (a 1920x1080 frame and a 1536x864 edit both pass)
        a, b = s['width'] / s['height'], e['width'] / e['height']
        need(abs(a - b) <= 0.01 * a, f"The start ({s['width']}x{s['height']}) and the end ({e['width']}x{e['height']}) differ in aspect ratio; "
                                     "generate the end from the start at the start's own size, or pick a start of the film's frame.")
    record = {'contract': 'videowizard-video-request-v1', 'run_id': str(run['id']), 'shot_id': body['shot_id'], 'plan_digest': base['plan_digest'],
              'base_preparation_digest': base['preparation_digest'], 'motion_prompt': body['motion_prompt'], 'subject_reconciliation': body['subject_reconciliation'],
              'continuity_notes': body.get('continuity_notes') or '', 'duration_seconds': int(duration), 'camera_move': shot.get('camera_move') or '',   # design/112 S4
              'aspect_ratio': aspect_of(run, outputs, 'take', body),   # design/139 R1: the AI video shape
              'resolution': body.get('resolution') or '720p',   # design/124 A4 decision 5: Omni only
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
    record.update(take_prompt_fields(run, plan_full, planned, fps, record['duration_seconds']))   # design/128 T1, T2, T4
    form += take_prompt_warnings(plan_full, planned, body['motion_prompt'], timeline_sent=bool(record.get('timeline')))   # design/128 T3
    record['effective_prompt'] = motion_text(record)
    identity = digest(record)
    save_json(store, key(run, f'takes/{identity}.request.json'), record)
    pair = None
    if changes and e:   # design/91 N1: Gemini lists what differs; a difference no change explains is marked, never refused
        pk = digest({'start': s['sha256'], 'end': e['sha256'], 'changes': changes})
        pair = (session.get('pair_checks') or {}).get(pk)
        if pair is None or pair.get('error'):
            pair = _pair_check(store, s, e, changes)
            session.setdefault('pair_checks', {})[pk] = pair
        form += [f"marked: '{d['what']}' differs between the start and the end picture and has no cause in the change list: show the operator; they approve the pair "
                 'or the end image is changed' for d in pair.get('uncaused') or []]
        if pair.get('error'):
            form.append(f"the pair check could not run ({pair['error']}): compare the two pictures with the change list yourself")
    session['preparations'][body['shot_id']] = {'preparation_id': identity, 'key': key(run, f'takes/{identity}.request.json'), 'start_image': body['start_image'], 'end_image': body.get('end_image'),
                                                'motion_prompt': body['motion_prompt'], **({'pair_check': pair} if pair else {}), **({'alignment': align} if align else {}),   # design/112 S3
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
        if not keys.pool('gemini', settings()):
            return {**rec, 'error': 'no Gemini key on the server'}
        listed = '\n'.join(f"{n}. {c['what']}" for n, c in enumerate(changes, 1))
        parts = [{'text': 'Image 1: the start of a video shot.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(start['key'])).decode()}},
                 {'text': 'Image 2: the end of the same shot.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(end['key'])).decode()}},
                 {'text': 'List every visible difference between Image 1 and Image 2: anything that appears, disappears, moves, opens, grows, shrinks, changes shape, count, colour '
                          'or state; a person\'s place, pose or what they hold; the light. Ignore the camera\'s framing. For each difference give the number of the planned change '
                          'below that causes it, or 0 when none does. Be literal.\nPlanned changes:\n' + listed}]
        received, rec['key_index'] = keys.gemini(_gemini_transport(), MEASURE_MODEL, lambda t: t.generate(
            {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': PAIR_SCHEMA, 'thinkingConfig': {'thinkingLevel': 'LOW'}, 'maxOutputTokens': 8192}}),
            settings(), terminal_deadline_seconds=120, initial_soft_wait_seconds=30, on_update=lambda e: None, capture_answer_deltas=False)   # design/114
        body = received.get('body') if isinstance(received.get('body'), dict) else json.loads(received.get('raw') or '{}')
        diffs = [{'what': str(d.get('what') or '')[:300], 'change': d.get('change') if isinstance(d.get('change'), int) else 0} for d in body.get('differences') or [] if isinstance(d, dict)]
        return {**rec, 'differences': diffs, 'uncaused': [d for d in diffs if not 1 <= d['change'] <= len(changes)]}
    except Exception as exc:   # the check never blocks a take
        return {**rec, 'error': f'{exc.__class__.__name__}: {str(exc)[:200]}'}


def submit_take(conn, store, user, run, outputs, shot_id):
    session = session_of(store, run, outputs)
    prep = session['preparations'].get(shot_id)
    need(prep, 'Prepare the take first.')
    need(not prep.get('drawn'), f'{shot_id} is a drawn shot: it is rendered with `vw visuals draw --shot {shot_id}`, not a take.')   # W3
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


def take_in_point(prep, job, in_s):
    """Integration step E: where a take starts in its slot, kept on the selection so the editor's package (made before the assembly) and the film both start there.
    A take made from a guide is a little longer than its slot: with no point given, the slot sits in the middle of the take. Any other take starts at its first frame, as before."""
    dur = float(((job.get('result') or {}).get('evidence') or {}).get('duration_seconds') or 0)
    slot = float(((prep or {}).get('placement') or {}).get('exact_seconds') or 0)
    if in_s is None or str(in_s).strip() == '':
        return {'in_s': round(max(0.0, (dur - slot) / 2), 2)} if (prep or {}).get('kind') in GUIDE_KINDS and dur > slot > 0 else {}
    try:
        at = float(in_s)
    except (TypeError, ValueError):
        raise ValueError('The in point is a number of seconds into the take (for example 0.4).')
    need(at >= 0, 'The in point is a number of seconds into the take, from 0.')
    need(not dur or at < dur, f'The in point {at:g} s is past the end of the take ({dur:.1f} s).')
    need(not (dur and slot) or at + slot <= dur + 0.05, f'The take has {max(dur - at, 0):.1f} s after {at:g} s but its slot needs {slot:.1f} s: choose an earlier point (at most {max(dur - slot, 0):.2f} s), or the last frame is held.'
         if dur - at >= 0 else '')
    return {'in_s': round(at, 2)}


def take_checklist(session, job):
    """design/74 L6: the checklist of the preparation this take was made from, when it is still the shot's current preparation."""
    prep = session['preparations'].get(job.get('unit')) or {}
    return prep.get('checklist') if prep.get('preparation_id') == (job.get('request') or {}).get('preparation_id') else None


def take_jobs(conn, run, shot_id=None):
    sql = "select id, unit, provider, status, request, result, error, cost, attempt, created_at, updated_at from vw2_jobs where run_id=%s and stage='visuals' and provider not in ('motion', 'guide', 'guide-still')"   # design/130: a helper's check or snapshot is never a take; design/187 (VW-21, 12 Nov 2026): nor are a guide's check frames, its render or its still, which the Takes step showed as ten takes to select
    rows = conn.execute(sql + (' and unit=%s' if shot_id else '') + ' order by created_at', (run['id'], shot_id) if shot_id else (run['id'],)).fetchall()
    return rows


def review_take(conn, store, user, run, outputs, job_id, decision, notes, timing_notes, quote):
    session = session_of(store, run, outputs)
    quote = said(quote, 'Rejected' if decision == 'rejected' else 'Accepted', user)   # design/99 C3: a take's reason is optional
    job = conn.execute("select * from vw2_jobs where id=%s and run_id=%s and provider in ('video', 'drawn')", (job_id, run['id'])).fetchone()   # design/113 E3: a drawing is reviewed like a take
    need(job and job['status'] == 'ready', 'Review a ready take.')
    need_free(conn, store, run, [job['unit']])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    ev = job['result']['evidence']
    need(decision != 'accepted' or ev.get('timing_matches_placement') or (timing_notes or '').strip(), 'The take duration differs from the placement; explain in timing_notes before accepting.')
    review = {'id': digest({'job': str(job_id), 'decision': decision, 'notes': notes, 'at': datetime.now(timezone.utc).isoformat()}), 'decision': decision, 'notes': notes,
              'timing_notes': timing_notes or '', 'quote': quote, 'by': user['id'], 'sha256': job['result']['sha256']}
    session['reviews'].setdefault(str(job_id), []).append(review)
    if session['selections'].get(job['unit'], {}).get('job_id') == str(job_id):
        session['selections'].pop(job['unit'])
    if decision == 'rejected':   # design/74 L7
        prep = _prep_of(store, job)
        _feedback_take(session, run, user, job, prep, 'reject', quote, notes)
        if prep.get('kind') in GUIDE_KINDS:   # integration step D: the attempt of the record ends with its verdict and the operator's words; the next step opens a new attempt
            generations.closed(conn, run['id'], job['unit'], 'guide', 'rejected', {'kind': 'take rejected', 'job_id': str(job_id), 'notes': notes or '', 'quote': quote, 'by': user['id'], 'by_name': user.get('name') or ''})
    save_session(store, run, session)
    return review


def take_held(store, run, outputs, session, job):
    """What `select_take` asks notes for: a drawing whose musts or fact check failed, that has no fact check, or whose brief changed; a take made from
    a guide whose scorecard fails or that was not read."""
    prep, check = load_json(store, job['request']['request_key']), (session.get('take_checks') or {}).get(str(job['id'])) or {}
    if prep.get('kind') in ('drawn', 'motion'):
        if check.get('must_failed'):
            return True
        if prep.get('kind') != 'motion':
            return False
        checks = motion_rounds(session, job['unit'], prep.get('sha256'))
        return not checks or bool(open_rules(checks[-1])) or bool(stale_brief(store, run, outputs, session, prep.get('sha256'), job['unit']))
    return False   # design/223 (SK, 22 Nov 2026): a take made from a guide has no check and no scorecard; nothing holds it (until then: a failed scorecard line, or "not read"; design/35 row 320)


def select_by_tool(conn, store, user, run, outputs, job_id, quote, notes='', timing_notes='', in_s=None):
    """The critic's point 10a (release 1, B1): `vw visuals select --job J`. The page and the chat ask no reason for a held take or drawing, so the tool
    asks none either: with no `--notes` such a selection carries the fixed note (`pictures.W['against_note']`), and the record keeps what it departs
    on, as `select_take` writes it. (`select_take` itself still refuses a held item with no note: every front end gives it one.)"""
    if not str(notes or '').strip():
        session = session_of(store, run, outputs)
        job = conn.execute("select * from vw2_jobs where id=%s and run_id=%s and provider in ('video', 'drawn')", (job_id, run['id'])).fetchone()
        if job and job['status'] == 'ready' and take_held(store, run, outputs, session, job):
            from . import pictures
            notes = pictures.W['against_note']
            timing_notes = timing_notes or ('' if job['result']['evidence'].get('timing_matches_placement') else notes)
    return select_take(conn, store, user, run, outputs, job_id, quote, notes, timing_notes, in_s)


def select_take(conn, store, user, run, outputs, job_id, quote, notes='', timing_notes='', in_s=None):
    """design/45 10.4: with notes, the accepted review and the selection are one call; without, the latest review must be accepted."""
    need(not re.search(r'\breject', f'{quote or ""} {notes or ""}', re.I),   # design/106 T3: select places a take; words that reject it never do
         'Your words say reject: select places the take in the film. To reject a take, run `vw visuals review --job J --decision rejected --notes "…"`.')
    session = session_of(store, run, outputs)
    quote = said(quote, 'Selected', user)   # design/99 C2
    job = conn.execute("select * from vw2_jobs where id=%s and run_id=%s and provider in ('video', 'drawn')", (job_id, run['id'])).fetchone()   # design/113 E3: a drawing is reviewed like a take
    need(job and job['status'] == 'ready', 'Select a ready take.')
    need_free(conn, store, run, [job['unit']])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    _no_question(session, job['unit'])   # design/110 rule 0
    if str(notes or '').strip():
        ev = job['result']['evidence']
        need(ev.get('timing_matches_placement') or str(timing_notes or '').strip(), 'The take is shorter than its placement; explain in timing_notes before accepting.')
        session['reviews'].setdefault(str(job_id), []).append({'id': digest({'job': str(job_id), 'decision': 'accepted', 'notes': notes, 'at': datetime.now(timezone.utc).isoformat()}),
                                                                 'decision': 'accepted', 'notes': notes, 'timing_notes': timing_notes or '', 'quote': quote, 'by': user['id'], 'sha256': job['result']['sha256']})
    reviews = session['reviews'].get(str(job_id), [])
    need(reviews and reviews[-1]['decision'] == 'accepted', 'Select only a take whose latest review is accepted.')
    prep = load_json(store, job['request']['request_key'])
    if prep.get('kind') in ('drawn', 'motion'):   # design/113 E3: a drawing stands on the plan it was rendered from; design/130: so does a motion drawing
        again = '`vw motion render --shot S`' if prep.get('kind') == 'motion' else '`vw visuals draw --shot S`'
        need(prep.get('plan_digest') == digest(current_plan(store, session)), f'The plan changed since this drawing was rendered; render it again ({again}).')
        made = (session.get('motion_projects') or {}).get(prep.get('sha256') or '') if prep.get('kind') == 'motion' else None
        if made:   # design/221 row 1: a drawing rendered with parts that are not the approved ones now is rendered again, not rebuilt
            from . import motion
            need((prep.get('parts') or {}).get('used') == parts_in_force(session, motion.unpack(store.get(made['key']))).get('used'), MOTION_PARTS_CHANGED.format(shot=job['unit']))
        failed = [l.get('check') for l in ((session.get('take_checks') or {}).get(str(job_id)) or {}).get('must_failed') or []]   # design/117 answer 1: held after the loop
        need(not failed or str(notes or '').strip(), f"This drawing is held: {', '.join(failed)} still failed after the server's passes. Select it with --notes saying why it is taken anyway, or reject it with what to change.")
        if prep.get('kind') == 'motion':   # design/130 §4 step 6: a motion drawing is selected after a clean fact check of the project it was rendered from
            checks = motion_rounds(session, job['unit'], prep.get('sha256'))   # design/221 (the critic's A1): a verdict on other rules is no verdict
            bad = open_rules(checks[-1] if checks else {})   # design/221 rows 11, 12, 17; a failed should is a note
            need(checks or str(notes or '').strip(), 'This drawing has no fact check of its project yet: run a vw-motion-check helper and `vw motion verdict`, or select it with --notes saying why not.')
            need(not bad or str(notes or '').strip(), f"This drawing is held: the fact check failed: {'; '.join(bad)}. Select it with --notes saying why it is taken anyway, or redo the shot.")
            changed = stale_brief(store, run, outputs, session, prep.get('sha256'), job['unit'])   # design/221 (the critic's A2): a pass on an older brief is no pass
            need(not changed or str(notes or '').strip(), MOTION_BRIEF_CHANGED.format(shot=job['unit'], names=', '.join(f'"{k}"' for k in changed))
                 + ' Or select it with --notes saying why it is taken anyway.')
        context = prep['plan_digest']
    elif prep.get('kind') in GUIDE_KINDS:   # integration step D: a take made from a guide stands on the plan it was shot for. design/223: nobody checks it, so nothing of a check is asked;
        # and only a video at the version size goes into the film (a 360p take gets its full-size copy first)
        need(prep.get('plan_digest') == digest(current_plan(store, session)), f"The plan changed since this take was shot; make the shot again from its guide (`vw guide status --shot {job['unit']}`).")
        from . import corrections
        need(corrections.final(job), f"This take is {corrections.size_of(job)}: the film takes its {corrections.VERSION_SIZE} video. Accept it on the page (or `vw visuals decide`): its full-size video is made and shown first.")
        context = prep['plan_digest']
    else:
        live = packet(store, run, outputs, job['unit'], session)
        need(live['preparation_digest'] == prep['base_preparation_digest'], 'The plan, references or generator changed since this take was prepared; prepare a current take.')
        context = live['preparation_digest']
    session['selections'][job['unit']] = {'job_id': str(job_id), 'review_id': reviews[-1]['id'], 'preparation_id': job['request']['preparation_id'], 'context_digest': context,
                                          'take': {k: job['result'][k] for k in ('key', 'sha256', 'bytes')}, 'quote': quote, 'by': user['id'],
                                          **take_in_point(prep, job, in_s)}
    _feedback_take(session, run, user, job, prep, 'pass', quote, '')   # design/74 L7
    if prep.get('kind') in GUIDE_KINDS:
        generations.closed(conn, run['id'], job['unit'], 'guide', 'accepted', {'kind': 'take accepted', 'job_id': str(job_id), 'notes': notes or '', 'quote': quote, 'by': user['id'], 'by_name': user.get('name') or ''})
    save_session(store, run, session)
    shot = guarded(lambda: locate(store, session, job['unit']))[3]
    return {**session['selections'][job['unit']], 'next': f"Take selected: in the film at {film_time(session, shot)} ({job['unit']})."}   # design/97 A4


# ---------- design/113 E2, E4: the drawn graphic rendered by the server, free, reviewed like a take ----------

def render_drawn(conn, store, user, run, outputs, body):
    """design/117 P3: the plan's SVG scene of a drawn shot, rendered at the film's size and frame rate in the worker: the scene uploaded and named by the
    plan, its pictures approved, the spec approved when the shot has one (E5), the cues from the timed narration, the run's brand font, the style and the
    palette for the read; cached by the request's digest; never counted against the cap."""
    from . import drawn, svg_scene
    need(drawn_route(run) == 'svg', 'This film draws its drawn shots with HyperFrames: `vw motion render --shot S`.')
    session = session_of(store, run, outputs)
    need_font(run, session)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, body['shot_id']))
    need(shot['visual_type'] == 'drawn', f"shot {shot['id']} is {shot['visual_type']}: `draw` is for a drawn shot (visual_type drawn, with scene_svg).")
    _no_question(session, shot['id'])   # design/110 rule 0
    sv = shot.get('scene_svg') or {}
    need(sv, f"{shot['id']} has no scene yet (scene_svg): after the picture search, draw it with the approved pictures, upload it (`vw visuals scene --shot {shot['id']} --file scene.svg`), "
             "put its sha256 and actions in the plan, then draw.")   # design/124 C2: named at plan time, finished here
    row = (session.get('scenes') or {}).get(sv.get('sha256') or '')
    need(row, f"the plan's scene_svg of {shot['id']} names no uploaded scene: upload it (`vw visuals scene --shot {shot['id']} --file scene.svg`) and put its sha256 in the plan.")
    spec = shot.get('drawing_spec')
    if spec:
        need((session.get('spec_approvals') or {}).get(shot['id'], {}).get('digest') == spec_digest(spec),
             f"the drawing spec of {shot['id']} is not approved, or changed since: the operator approves the sizes, materials and graphic specs on the page (`vw visuals page`), before the drawing is rendered.")
    fps = session['source']['fps']
    res = session['source'].get('resolution') or [1920, 1080]   # defect 33: a run stores [1920, 1080] (the master's summary), the fixtures '1920x1080'; both read, as defect 26 did
    W, H = (int(x) for x in (res if isinstance(res, (list, tuple)) else str(res).lower().split('x')))
    words = ((session['source']['gaps'].get(gap['gap_id']) or {}).get('timing') or {}).get('words')
    cues = guarded(lambda: drawn.cue_seconds(sv, shot, words, fps))
    svg_text = store.get(row['key']).decode('utf-8')
    images = {}
    for rid in svg_scene.image_refs(guarded(lambda: svg_scene.parse(svg_text))):
        ref = session['references'].get(rid)
        need(ref and ref.get('status') == 'approved' and ref.get('key'), f"the scene places ref:{rid}, which is not an approved picture of this run.")
        images[rid] = ref['key']
    style = next((r for r in session['references'].values() if r.get('kind') == 'style' and r.get('status') == 'approved' and r.get('key')), None)
    frames = shot['end_frame'] - shot['start_frame']
    exact = Fraction(frames) / Fraction(str(fps))
    request = {'kind': 'drawn', 'shot_id': shot['id'], 'scene': {'sha256': sv['sha256'], 'actions': sv.get('actions') or []}, 'svg_key': row['key'], 'width': W, 'height': H, 'fps': str(fps),
               'frames': frames, 'cues': cues, 'images': images, 'plan_digest': digest(plan), 'style_key': style['key'] if style else None,
               'palette': str(((plan.get('foundation') or {}).get('graphic_style') or {}).get('palette') or ''),
               **({'font_key': session['font']['key'], 'font_name': Path(session['font']['name']).stem} if session.get('font') else {}),
               **({'film_font': next(iter(film_font_files(run))), 'font_name': film.font(run)} if film_font_files(run) else {}),   # design/139 R13
               'claims': shot.get('claims') or [], 'relationships': (spec or {}).get('relationships') or [], 'view': spec_view(shot)[0] if spec else None,
               'spec': {'dimensions': (spec or {}).get('dimensions') or []},   # design/117 P2: the sizes checked against the scene's text at render
               'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame'], 'film_fps': str(fps), 'duration_seconds': str(exact), 'exact_seconds': float(exact)}}
    identity = digest(request)
    key_ = key(run, f'takes/{identity}.drawn.json')
    save_json(store, key_, request)
    same = [j for j in take_jobs(conn, run, shot['id']) if j.get('provider') == 'drawn' and (j.get('request') or {}).get('preparation_id') == identity and j['status'] not in ('failed', 'rejected', 'cancelled')]
    session['preparations'][shot['id']] = {'preparation_id': identity, 'key': key_, 'drawn': True}
    if same:
        save_session(store, run, session)
        return {'job_id': str(same[0]['id']), 'preparation_id': identity, 'frames': frames, 'cached': True, 'next': 'Already rendered from this scene (nothing changed): see it on the Takes step.'}
    row_ = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,'drawn',%s, gen_random_uuid()) returning id",
                        (run['id'], shot['id'], Jsonb({'kind': 'drawn', 'request_key': key_, 'preparation_id': identity, 'shot_id': shot['id'], 'frames': frames, 'duration_seconds': float(exact)}))).fetchone()
    save_session(store, run, session)
    return {'job_id': str(row_['id']), 'preparation_id': identity, 'frames': frames,
            'next': f'Rendering {frames} frames, free: the server reads a sheet of every frame, fixes the scene up to twice, then shows the drawing and its sheet on the Takes step; '
                    'select it there or reject it with what to change.'}


def set_scene(store, user, run, outputs, shot_id, name, content):
    """design/117 P2: a drawn shot's SVG scene, one file kept with the run and named by the plan through its sha256; refused with the reasons when it
    breaks a rule (never rendered). The plan's scene_svg points at it."""
    from . import svg_scene
    need(drawn_route(run) == 'svg', 'This film draws its drawn shots with HyperFrames: upload the project with `vw motion upload`.')
    session = session_of(store, run, outputs)
    need(re.search(r'\.svg$', name or '', re.I), 'The scene is one .svg file.')
    need(content and len(content) <= svg_scene.MAX_BYTES, f'The scene file is empty or over {svg_scene.MAX_BYTES // 1_000_000} MB: use <use> for repeats and components for things.')
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        need(False, 'The scene is not UTF-8 text.')
    fonts = ('Noto Sans',) + ((Path(session['font']['name']).stem,) if session.get('font') else ())
    problems = svg_scene.check(text, fonts=fonts, refs=session['references'])
    need(not problems, 'The scene breaks the rules: ' + '; '.join(problems[:6]) + ('' if len(problems) <= 6 else f' (+{len(problems) - 6} more)'))
    sha = hashlib.sha256(content).hexdigest()
    k = f"{run['id']}/visuals/scenes/{sha}.svg"
    store.put(k, content, 'image/svg+xml')
    session.setdefault('scenes', {})[sha] = {'key': k, 'shot_id': shot_id, 'name': name, 'bytes': len(content), 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    root = svg_scene.parse(text)
    return {'sha256': sha, 'bytes': len(content), 'ids': list(svg_scene.ids_of(root)), 'pictures': svg_scene.image_refs(root), 'texts': [x for _, x in svg_scene.texts_of(root)],
            'next': f"Scene stored. Put scene_svg: {{sha256: {sha}, actions: [...]}} on {shot_id} in the plan, then `vw visuals draw --shot {shot_id}`."}


def scene_of(conn, store, run, outputs, shot_id):
    """design/117 P4: the shot's latest rendered scene as the loop left it (the fixed SVG when a pass changed it, else the plan's), for the planner to take back."""
    session = session_of(store, run, outputs)
    jobs_ = [j for j in take_jobs(conn, run, shot_id) if j.get('provider') == 'drawn' and j['status'] == 'ready']
    need(jobs_, f'{shot_id} has no rendered drawing yet.')
    res = jobs_[-1].get('result') or {}
    if res.get('fixed_svg_key'):
        return {'shot_id': shot_id, 'job_id': str(jobs_[-1]['id']), 'fixed': True, 'svg': store.get(res['fixed_svg_key']).decode('utf-8'),
                'passes': ((session.get('take_checks') or {}).get(str(jobs_[-1]['id'])) or {}).get('passes')}
    prep = load_json(store, jobs_[-1]['request']['request_key'])
    return {'shot_id': shot_id, 'job_id': str(jobs_[-1]['id']), 'fixed': False, 'svg': store.get(prep['svg_key']).decode('utf-8')}


def set_font(store, user, run, outputs, name, content):
    """design/113 E4: the film's brand font, one TTF or OTF kept with the run; the drawn route and the slates use it; nothing is substituted when it cannot be read."""
    from io import BytesIO
    from PIL import ImageFont
    session = session_of(store, run, outputs)
    need(re.search(r'\.(ttf|otf)$', name or '', re.I), 'The font is one .ttf or .otf file.')
    need(content and len(content) <= 5_000_000, 'The font file is empty or over 5 MB.')
    try:
        ImageFont.truetype(BytesIO(content), 12)
    except Exception as exc:
        need(False, f'Pillow cannot read {name} ({exc.__class__.__name__}): the film keeps the repo font until a readable file is given.')
    k = f"{run['id']}/fonts/{re.sub(r'[^A-Za-z0-9._-]', '_', name)}"
    store.put(k, content, 'font/ttf' if name.lower().endswith('.ttf') else 'font/otf')
    session['font'] = {'key': k, 'name': name, 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    return {'font': session['font'], 'next': f'{name} is the font of this film: every drawn graphic uses it from the next render.'}


# ---------- design/130: the HyperFrames motion route for drawn shots ----------

def drawn_route(run):
    """design/130 §9: the film's drawn route, chosen once at `vw start --drawn`; motion by default since 1 Nov 2026 (§12); a run row without one draws SVG scenes."""
    return (run or {}).get('drawn_route') or 'svg'


def _motion_run(run):
    need(drawn_route(run) == 'motion', 'This film draws its drawn shots as SVG scenes (`vw visuals scene`, `vw visuals draw`); the motion route is chosen at `vw start --drawn motion`.')


def _film_frame(session):
    fps = session['source']['fps']
    res = session['source'].get('resolution') or [1920, 1080]
    W, H = (int(x) for x in (res if isinstance(res, (list, tuple)) else str(res).lower().split('x')))
    return fps, W, H


def need_motion_style(run):
    film.need_motion(run)   # a function of its own: `treatment` has a local of the module's name


def film_font_files(run):
    """design/139 R13: the film's chosen font as {file name: 'server'} (a file under server/fonts), none for Noto Sans or a film from before."""
    name = film.font(run)
    faces = film.font_faces(name, film.font_scripts(run)) if name else []   # design/179: one file per script the film is written in
    return {f['file']: 'server' for f in faces if f['family'] != 'Noto Sans'}   # Noto Sans itself is always there (NotoSans-Variable.ttf)


def need_font(run, session=None):
    """design/139 R13: the drawing font is asked once, before the first drawing, with Noto Sans as the reference; a brand font given with
    `vw visuals font --file` answers it too."""
    need(film.font(run) or (session or {}).get('font'), "Ask the operator the film's font once, in the chat: `vw font` lists the fonts that fit this film's motion style and hold its language, the first is the "
                                                         'one to recommend. First run `vw font --sample` and show its picture (each offered font drawn on this film\'s labels; "Other" is not in it), '
                                                         'then ask the question with the fonts and "Other" as before; if it says "The font sample is not available.", say that line and ask as before. '
                                                         'Record it: `vw font <name> --quote "<their words>"`.')   # design/218


def _motion_fonts(store, session, run=None):
    """{file name: bytes} placed in assets/fonts, and the family names a project may use (Noto Sans always, for the scripts the chosen font lacks)."""
    from . import drawn
    files, names = {'NotoSans-Variable.ttf': drawn.font_file().read_bytes()}, ['Noto Sans']
    faces = {f['file']: f['family'] for f in film.font_faces(film.font(run), film.font_scripts(run))} if film.font(run) else {}
    for file in film_font_files(run):
        files[file] = (drawn.FONTS / file).read_bytes()
        names += [faces.get(file) or film.font(run)] if (faces.get(file) or film.font(run)) not in names else []
    if session.get('font'):
        files[Path(session['font']['name']).name] = store.get(session['font']['key'])
        names.append(Path(session['font']['name']).stem)
    return files, names


def _finish_view(session, job, result):
    """design/186: what the page shows of a drawing's finish: the effects this take carries with the plain sentence, why one was left off, and
    whether the operator has taken it away (so the button offers the other way)."""
    from . import motion
    carried, off = result.get('finish') or [], bool((session.get('motion_finish_off') or {}).get(job['unit']))
    if not (carried or off or result.get('finish_left_off')):
        return {}
    return {'finish': {'effects': carried, 'words': motion.finish_words(carried), 'left_off': result.get('finish_left_off') or '', 'taken_away': off}}


STILL_FIRST = ('{shot}: the still end-frame comes first: build the picture as it stands at the end of the shot, with no motion, upload it with '
               '`vw motion upload --shot {shot} --still`, snapshot its last frame, check it and send the checker\'s verdict; the operator approves it in the chat. '
               'Then the animated project.')
STILL_WAIT = "{shot}: the still end-frame waits for the operator's approval in the chat (`vw visuals next`); the animated project comes after it."
STILL_REJECTED = ('{shot}: the operator rejected the still end-frame: "{words}". Give these words to a `vw-motion-shot` helper to redo the still, then upload it '
                  'again with --still.')
STILL_STALE = ("{shot}: its parts changed since the still end-frame was approved: upload the still again (`vw motion upload --shot {shot} --still`), snapshot "
               "its last frame and send the checker's verdict; the approval stays when the picture is the same.")
STILL_FRAME = "{shot}: the still's last frame is not taken yet: run `vw motion snapshot --shot {shot} --sha {sha} --at {last:g}`, give it to the checker, then send the verdict."


def last_second(shot, fps):
    """design/221 rows 2 and 3: the second of a shot's last frame."""
    return round((shot['end_frame'] - shot['start_frame'] - 1) / float(Fraction(str(fps))), 3)


def last_frame_key(conn, run, shot_id, sha, last):
    """design/221 rows 2 and 3: the key of a ready snapshot of this project at its last frame, else ''."""
    rows = conn.execute("select id, unit, request, result, status from vw2_jobs where run_id=%s and provider='motion' and unit=%s order by created_at", (run['id'], shot_id)).fetchall()
    snaps = [s_ for j in rows if j.get('unit') == shot_id and j.get('status') == 'ready' and (j.get('request') or {}).get('kind') == 'motion-snapshot'
             and (j.get('request') or {}).get('sha256') == sha for s_ in (j.get('result') or {}).get('snapshots') or [] if float(s_['at']) >= last - 0.05]
    return snaps[-1]['key'] if snaps else ''


def still_approved(st):
    """design/221 row 3: the operator approved this picture of the still (an approval stays for the same picture made again)."""
    return bool(st.get('png')) and (st.get('approved') or {}).get('png') == st['png']


def still_stale(store, session, st):
    """design/221 row 3: the still was checked with parts that are not the approved ones now (its project gets the new parts pasted)."""
    from . import motion
    row = (session.get('motion_projects') or {}).get(st.get('sha256') or '')
    return bool(row) and (st.get('parts') or {}) != (parts_in_force(session, motion.unpack(store.get(row['key']))).get('used') or {})


def still_answer(store, user, run, outputs, shot_ids, ok, quote, words='', conn=None):
    """design/221 row 3: the operator's Approve of the still end-frame(s) of one card, or Reject with their words (the still is redone and asked again)."""
    need_free(conn, store, run, shot_ids)   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = session_of(store, run, outputs)
    stills = session.get('motion_stills') or {}
    for sid in shot_ids:
        need((stills.get(sid) or {}).get('frame_key'), f'{sid} has no still end-frame waiting.')
    need(ok or str(words or '').strip(), "Say what to change in the still, in the operator's words.")
    at = datetime.now(timezone.utc).isoformat()
    for sid in shot_ids:
        st = stills[sid]
        st.pop('rejected', None)
        st['approved' if ok else 'rejected'] = {'png': st['png'], 'quote': quote, 'by': user['id'], 'at': at, **({} if ok else {'words': str(words).strip()})}
    save_session(store, run, session)
    names = ', '.join(shot_ids)
    waits = ''   # the critic's point 7: a drawing that continues another builds its motion on that drawing's passed project
    for sid in shot_ids if ok else []:
        plan, gap, _, shot = guarded(lambda sid=sid: locate(store, session, sid))
        prev = continues_from(plan, session, gap, shot)
        if prev and not passed_project(session, guarded(lambda: locate(store, session, prev))[3]):
            waits += CHAIN_WAIT.format(shot=sid, prev=prev)
    return {'recorded': True, 'for_the_assistant': f'The still end-frame of {names} is approved: build its motion now without changing what the still shows, and upload it without --still.' + waits
            if ok else ' '.join(STILL_REJECTED.format(shot=sid, words=str(words).strip()) for sid in shot_ids)}


def set_motion(store, user, run, outputs, shot_id, name, content, rules_text='', brief_lines=None, still=False):
    """design/130 §4: a drawn shot's HyperFrames project, one zip kept with the run and named by the plan through its sha256; refused with the reasons
    when it breaks a rule (never checked or rendered). design/221 (the critic's A1): brief_lines are the lines `vw motion brief` returned when the
    rules were written (work/motion/<shot>/brief-lines.json); kept as sent, worked out here only when nothing is sent. design/221 row 3: `still`, the
    picture at the end of the shot with no motion, comes first; the animated project only after the operator approved it."""
    from . import motion
    _motion_run(run)
    session = session_of(store, run, outputs)
    _, gap, _, shot = guarded(lambda: locate(store, session, shot_id))
    need(re.search(r'\.zip$', name or '', re.I), 'The project is one .zip file of the shot\'s folder (index.html at its root).')
    need(content and len(content) <= motion.MAX_ZIP, f'The project zip is empty or over {motion.MAX_ZIP // 1_000_000} MB: pictures come from assets/ref, not inside the zip.')
    try:
        files = motion.unpack(content)
    except ValueError as exc:
        need(False, f'The project cannot be read: {exc}.')
    fps, W, H = _film_frame(session)
    need_font(run, session)
    names = _motion_fonts(store, session, run)[1]
    problems = motion.problems(files, refs=session['references'], fonts=names, frames=shot['end_frame'] - shot['start_frame'], fps=fps, width=W, height=H)
    need(not problems, 'The project breaks the rules: ' + '; '.join(problems[:6]) + ('' if len(problems) <= 6 else f' (+{len(problems) - 6} more)'))
    st = (session.get('motion_stills') or {}).get(shot_id) or {}
    if not still:   # design/221 row 3: the still end-frame first, approved by the operator in the chat, checked with the parts in force
        need(st, STILL_FIRST.format(shot=shot_id))
        need(not st.get('rejected'), STILL_REJECTED.format(shot=shot_id, words=(st.get('rejected') or {}).get('words')))
        need(still_approved(st), STILL_WAIT.format(shot=shot_id))
        need(not still_stale(store, session, st), STILL_STALE.format(shot=shot_id))
    shared = (session.get('motion_parts_approved') or {}).get('parts') or []   # design/221 row 1: a project uses the shared parts of its things, never its own copy
    text = ' '.join(motion._texts(files).values())
    own = [p['id'] for p in shared if re.search(r'\bid\s*=\s*["\']' + re.escape(p['id']) + r'["\']', text)]
    need(not own, PARTS_OWN_ID.format(shot=shot_id, ids=', '.join(own)))
    plan = guarded(lambda: current_plan(store, session))
    prev = continues_from(plan, session, gap, shot)   # the critic's point 7: the still opens on the earlier drawing's approved still; the motion is built on its passed project
    on = opens_on(session, prev) if prev and still else {}
    if prev and still:   # release 2, F1: no still of a continuing drawing while the earlier one has no still in force (nor a passed project, the older order)
        need(on or passed_project(session, guarded(lambda: locate(store, session, prev))[3]), CHAIN_STILL.format(shot=shot_id, prev=prev))
    if prev and not still:
        need(not opens_changed(session, prev, st), STILL_OPENS.format(shot=shot_id, prev=prev))
        need(passed_project(session, guarded(lambda: locate(store, session, prev))[3]), CHAIN_FIRST.format(shot=shot_id, prev=prev))
    if not still and session.get('motion_parts'):   # release 2, F11: no animated project while a new parts file waits for the operator, or was rejected (its brief is refused too)
        need_parts(plan, session)
    els = {e['id']: e for e in plan.get('elements') or []}
    placed = lambda ids: any(re.search(r'href\s*=\s*["\']#' + re.escape(i) + r'["\']', text) for i in ids)
    for p in shared:   # fix set A1.1: a shape that is no thing of the plan, drawn once: the drawings its part names place it
        need(p.get('element') or shot_id not in (p.get('shots') or []) or placed([p['id']]), PARTS_USE.format(shot=shot_id, thing=p['title'] or p['id'], id=p['id']))
    mine, fits = view_parts(session, shot), fit_parts(session, shot)
    for e in shot.get('element_ids') or []:   # defect 56 (VW-24, 19 Nov 2026): a thing may have several views among the parts (cut across, from above); a drawing places the view it shows
        views = fits.get(e) or []   # release 2, F5: with a stated view, its parts of that view or of no view; drawn in other views only: nothing of it is demanded
        thing = (els.get(e) or {}).get('name') or e
        if len([p for p in shared if p.get('element') == e]) > 1 and mine.get(e) and not placed(mine[e]):   # fix set B2: the view the shot's spec states, when the thing has a part drawn in it
            need(False, PARTS_USE_VIEW.format(shot=shot_id, thing=thing, view=shot['drawing_spec']['view'], ids=', '.join(mine[e])))
        if views and not placed(views):   # no stated view: one of the thing's views is enough (defect 56's fix, kept)
            need(False, PARTS_USE.format(shot=shot_id, thing=thing, id=views[0]) if len(views) == 1 else PARTS_USE_ONE.format(shot=shot_id, thing=thing, ids=', '.join(views)))
    from . import pictures   # design/217 (C6): the rules of the brief, held by the server per project, so a fact check answers every one of them
    notes = pictures.notes_in(rules_text)
    need(not notes, NOT_A_RULE.format(lines='; '.join(f'"{n}"' for n in notes[:12])))   # design/221 row 15
    need(not brief_lines or (isinstance(brief_lines, dict) and len(brief_lines) <= 80 and all(isinstance(k, str) and isinstance(v, str) and len(k) <= 120 and len(v) <= 64
                                                                                            for k, v in brief_lines.items())),
         'brief-lines.json is not the brief\'s lines as `vw motion brief` wrote them: run `vw motion brief --shot ' + shot_id + '` again, read the rules again, then upload.')
    lines = brief_lines or motion_brief(store, run, outputs, shot_id)['lines']   # design/221 S3: the brief the rules were written from, line by line
    held = pictures.rules_of(rules_text)
    odd = next((h['rule'] for h in held if pictures.RULE_MARKED.match(h['rule'])), None)   # release 2, F13: a mark the server cannot read is never kept as the rule's words
    need(not odd, RULE_MARK.format(shot=shot_id, rule=odd))
    cmp = comparing(session, plan, held)
    lost = next((c for c in cmp.values() if c['state'] == 'closed' and c['with'] not in ever_drawn(store, session)), None)   # the critic's point 3: a mistyped id never drops a must
    need(not lost, WITH_UNKNOWN.format(shot=shot_id, rule=(lost or {}).get('rule'), other=(lost or {}).get('with'), ids=', '.join(drawn_ids(plan, session))))
    idle = {i for i, c in cmp.items() if c['state'] != 'ready'}
    sha = hashlib.sha256(content).hexdigest()
    k = f"{run['id']}/visuals/motion/projects/{sha}.zip"
    store.put(k, content, 'application/zip')
    session.setdefault('motion_projects', {})[sha] = {'key': k, 'shot_id': shot_id, 'name': name, 'bytes': len(content), 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat(),
                                                      **({'rules': held, 'brief': lines} if held else {}), **({'still': True} if still else {}),
                                                      **({'left_out': sorted(idle)} if idle else {}),   # the critic's point 1: the comparisons this upload's checker was not given
                                                      **({'opens_on': on['png'], 'opens_from': prev} if on else {})}   # the critic's point 7: the picture of the earlier drawing this still opens on
    if sha != (st.get('sha256') if still else (session.get('motion_bound') or {}).get(shot_id)):   # fix set A3.5: a new still of a bound shot is a redraw: its old project is no longer
        (session.get('motion_bound') or {}).pop(shot_id, None)   # the drawing (the count says "being redone"; a drawing that continues it waits). design/221 (the critic's A1): a later upload is bound only by its own clean verdict. Release 2, F3: the bound project uploaded again (for a frame to compare with) stays bound
    save_session(store, run, session)
    held = [h for h in held if h['id'] not in idle]   # fix set A1.2: a comparison with nothing to compare with yet waits as a note: no checker is asked for it
    frames = compare_frames(cmp)
    with_ = {'compare': frames} if frames else {}
    told = ''.join(f" {len([c for c in cmp.values() if c['with'] == f['shot_id'] and c['state'] == 'ready'])} rule(s) compare with {f['shot_id']}: {f['shot_id']}'s approved still "
                   f"end-frame is saved in work/motion/{shot_id}/with-{f['shot_id']}/last-frame.png for the checker." for f in frames)
    again = round_rules(session, shot_id, sha, cmp)   # fix set A1.6: from round 2 of the animated project, the rules the round before left open
    passed = round_rules(session, shot_id, sha, cmp, passed=True) if again is not None else []   # the critic's point 6: and the musts that passed, answered only when this upload broke one
    if still:
        last = last_second(shot, fps)
        mine = still_rules(held)   # fix set B3: the still's checker is given the musts a still can show and no other rule
        return {'sha256': sha, 'bytes': len(content), 'files': sorted(files), 'refs': motion.ref_ids(files), 'text': motion.visible_text(files)[:2000], 'still': True,
                **({'still_rules': mine} if mine is not None else {}), **with_,
                'next': (f"Still stored. Check it (`vw motion check --shot {shot_id} --sha {sha}`), snapshot its last frame (`vw motion snapshot --shot {shot_id} --sha {sha} --at {last:g}`). "
                         f"No rule of this drawing is one a still can show, so no checker is needed: write work/motion/{shot_id}/check-1.json as "
                         f'{{"shot_id": "{shot_id}", "sha256": "{sha}", "round": 1, "rules": []}} and send it (`vw motion verdict`); it brings the still to the operator in the chat.'
                         if mine == [] else   # the carry-over c2: the still passes on the server's own checks
                         f"Still stored. Check it (`vw motion check --shot {shot_id} --sha {sha}`), snapshot its last frame (`vw motion snapshot --shot {shot_id} --sha {sha} --at {last:g}`) "
                         "and give it to a fresh vw-motion-check helper for the must rules a still can show; a verdict with no failed must brings the still to the operator in the chat."
                         + (f" Those rules ({len(mine)}) are in work/motion/{shot_id}/rules-still.md: the checker answers each of them and no other." if mine is not None else '')) + told}
    effects = motion.finish_of(files)[0]   # design/186
    return {'sha256': sha, 'bytes': len(content), 'files': sorted(files), 'refs': motion.ref_ids(files), 'text': motion.visible_text(files)[:2000],
            **({'finish': effects, 'finish_note': motion.finish_note(files, effects) or 'The server adds this finish at snapshot and render; the drawing must be complete without it.'} if effects else {}),
            **({'round_rules': again, 'round_passed': passed} if again is not None else {}), **with_,
            'next': f"Project stored. Check it with `vw motion check --shot {shot_id} --sha {sha}`, then snapshot it for the fact check; a clean verdict binds it to {shot_id} "
                    f"(nothing goes in the plan), then `vw motion render --shot {shot_id}`."
                    + (f" The {len(again)} rules the round before left open are in work/motion/{shot_id}/rules-round.md: the checker answers those, and looks at the whole frame "
                       "for a must-kind fault" + (f"; below them are the {len(passed)} musts that passed before: the checker answers one of those only when this upload broke it "
                                                  '("pass": false, with where).' if passed else '.') if again is not None else '') + told}


def comparing(session, plan, held):
    """Fix set A1.2 (19 Nov 2026): the rules marked as comparing with another drawing (`must (still, with D1):`), {rule id: {with, rule, state}}:
    `ready` with that drawing's approved still end-frame (png, key: what the checker compares with; the rule is a must), `waits` while it has none
    (the rule is a note: it holds nothing), `closed` when it is no drawn shot of the plan now. A rule marked with a shared part's id is a plain
    must: the parts are always there."""
    if not any(h.get('with') for h in held or []):
        return {}
    drawn, parts = set(drawn_ids(plan, session)), {p['id'] for p in (session.get('motion_parts_approved') or {}).get('parts') or []}
    out = {}
    for h in held or []:
        other = h.get('with')
        if other and other not in parts:
            st = (session.get('motion_stills') or {}).get(other) or {}
            out[h['id']] = {'with': other, 'rule': h['rule'], **({'state': 'closed'} if other not in drawn or other in (session.get('assets') or {}) else   # release 2 (c): nor one the operator's own file replaced: it gets no still
                                                                {'state': 'ready', 'png': st['png'], 'key': st['frame_key']} if still_approved(st) and st.get('frame_key') else {'state': 'waits'})}
    return out


WITH_UNKNOWN = ('{shot}: the rule "{rule}" compares with {other}, which is not a drawn shot of this plan and was in no earlier version of it. The drawn shots are {ids}: '
                "correct the id in the rule's mark (`with <shot id>`) in rules.md, then upload again.")
RULE_MARK = ('{shot}: the mark of the rule "{rule}" cannot be read, so the rule would lose it. A rule starts with `must:` or `should:`, and its mark is one of `(still)`, '
             '`(motion)`, `(still, with <shot id>)`, `(motion, with <shot id>)`: correct it in rules.md, then upload again.')   # release 2, F13


def ever_drawn(store, session):
    """The critic's point 3 (19 Nov 2026): the ids of the drawn shots of every stored version of the plan. A comparison is `closed` only for a
    shot that was one of them and was cut; an id that never was (a mistyped one) is refused at the upload, so its must is not dropped."""
    out = set()
    for v in session.get('versions') or []:
        try:
            doc = load_json(store, v['file']['key'])['document']
        except (Problem, KeyError, TypeError, ValueError):
            continue
        out |= {s['id'] for g_ in doc.get('gaps') or [] for sc in g_.get('scenes') or [] for s in sc.get('shots') or [] if s.get('visual_type') == 'drawn'}
    return out


def left_out(session, shot_id, sha):
    """The critic's point 1 (19 Nov 2026): the comparing rules the checker of this upload was not given (the other drawing had no approved still
    end-frame at the upload). They stay a note until a verdict of this upload is clean, whatever was approved meanwhile; after that they come due."""
    done = any(c.get('sha256') == sha and not open_rules(c) for c in (session.get('motion_checks') or {}).get(shot_id) or [])
    return set() if done else set(((session.get('motion_projects') or {}).get(sha) or {}).get('left_out') or [])


STILL_OPENS = ("{shot}: {prev}'s still end-frame, which {shot}'s still opens on, was replaced since {shot}'s still was built. Once {prev}'s new still is approved, run "
               "`vw motion brief --shot {shot}` again and build {shot}'s still again from it (`vw motion upload --shot {shot} --still`).")
CHAIN_STILL = ("{shot} continues from {prev}: its still end-frame opens on {prev}'s approved still end-frame, and {prev} has none now: have {prev}'s still built, "
               'checked and approved first, then brief {shot}.')
CHAIN_FIRST = "{shot} continues from {prev}: build and pass {prev} first (a clean fact check), then brief {shot}: this drawing is built on {prev}'s project."
CHAIN_WAIT = (" {shot} continues from {prev}: its motion waits until {prev}'s project has passed its fact check; then run `vw motion brief --shot {shot}` again (it brings "
              "{prev}'s project) and build {shot}'s motion on it.")


def opens_on(session, shot_id):
    """The critic's point 7 (19 Nov 2026): the approved still end-frame of a drawing, the picture the drawing that continues it opens on:
    {png, key, project_key}; {} while it has none in force (not approved, or a newer still of it is uploaded and not yet checked and approved)."""
    st = (session.get('motion_stills') or {}).get(shot_id) or {}
    rows = session.get('motion_projects') or {}
    if not (still_approved(st) and st.get('frame_key')) or any(p.get('shot_id') == shot_id and p.get('still') and sha != st.get('sha256') and (p.get('at') or '') > (st.get('at') or '')
                                                              for sha, p in rows.items()) or opens_changed(session, st.get('opens_from'), st):   # or it is itself to be made again (a chain)
        return {}
    return {'png': st['png'], 'key': st['frame_key'], 'project_key': (rows.get(st.get('sha256')) or {}).get('key') or ''}


def opens_changed(session, prev, st):
    """The critic's point 7: the still `st` of a drawing that continues `prev` was built on a still of `prev` that is not the one in force now:
    it is made again. A still recorded before this (no `opens_on`) is not marked."""
    return bool(prev) and 'opens_on' in (st or {}) and st['opens_on'] != opens_on(session, prev).get('png')


def base_changed(session, plan, gap, shot):
    """Release 2, F1 and F6 (20 Nov 2026): the drawing this one continues by the plan now, when this one's still was built on a still of it that is
    not the one in force (replaced, or another drawing since a plan version cut the one between); else ''. Such a drawing is made again from its
    still, whatever was finished on it: its project is bound by no verdict and is no passed project for the drawing after it."""
    st = (session.get('motion_stills') or {}).get(shot['id']) or {}
    prev = continues_from(plan, session, gap, shot) if 'opens_on' in st else ''   # a still recorded before it said what it opens on is not marked
    return prev if opens_changed(session, prev, st) else ''


def compare_frames(cmp):
    """Fix set A1.2: the other drawings' approved still end-frames the checker of a drawing is given, [{shot_id, key}], one per drawing."""
    return list({c['with']: {'shot_id': c['with'], 'key': c['key']} for c in cmp.values() if c['state'] == 'ready'}.values())


def compared(session, plan, shot_id):
    """Fix set A1.2: what stands with the comparisons of a drawing whose last verdict is clean (one with an open rule is checked again anyway):
    {due, waits, closed: [{with, rule}], round}. `due`: the other drawing's still end-frame is approved and this verdict did not answer the
    rule against that picture; the drawing counts as being checked until it does."""
    rec = next((c for c in reversed((session.get('motion_checks') or {}).get(shot_id) or []) if not c.get('still')), None)
    row = (session.get('motion_projects') or {}).get((rec or {}).get('sha256') or '') or {}
    out = {'due': [], 'waits': [], 'closed': [], 'round': int((rec or {}).get('round') or 1)}
    if not rec or open_rules(rec) or not row.get('rules'):
        return out
    from . import pictures
    cmp = comparing(session, plan, row['rules'])
    said = {pictures.rule_id(r.get('rule')): r for r in rec.get('rules') or []}
    redone = (session.get('motion_bound') or {}).get(shot_id) != rec.get('sha256')   # the critic's point 5: unbound by a newer upload (A3.5): the comparison is the new upload's
    for i, c in cmp.items():
        if c['state'] != 'ready':
            out[c['state']].append(c)
        elif said.get(i, {}).get('with_png') != c['png'] and not redone:
            out['due'].append(c)
    return out


REDONE = ('{shot} is being redone: a newer upload of it came after this project, so this project is not the drawing any more and no verdict is taken on it. A comparison '
          'with another drawing is judged on the new upload.')


def round_rules(session, shot_id, sha, cmp=None, passed=False):
    """Fix set A1.6 (19 Nov 2026): the rules the checker of an animated project's later round is given, as lines: the rules of this upload that
    the drawing's last verdict left failed or not seen or did not answer (a rule written anew; a comparison not answered against the other
    drawing's picture as it is now: `cmp`, comparing()), and the faults that verdict's checker added and left failed. Only when that verdict
    answered the same brief lines: None in a first round, after a clean verdict, after a verdict of the still, and when the brief changed since;
    then every rule is answered again. (The still's own list is short: still_rules.)
    The critic's point 6: `passed`, the second part of the list: the musts that verdict passed, which the checker answers only when this
    upload broke one (a false on one of them is a failed must, as on any rule)."""
    from . import pictures
    row, cmp = (session.get('motion_projects') or {}).get(sha) or {}, cmp or {}
    prev = ((session.get('motion_checks') or {}).get(shot_id) or [None])[-1]
    if row.get('still') or not prev or prev.get('still') or not row.get('rules') or prev.get('brief_at') != digest(row.get('brief') or {}):
        return None
    said = {pictures.rule_id(r.get('rule')): r for r in prev.get('rules') or []}
    if all(settled(r) for r in said.values()):   # release 1, A3: a rule that did not apply is recorded once, never asked again
        return None
    mine = [h for h in row['rules'] if cmp.get(h['id'], {'state': 'ready'})['state'] == 'ready'
            and (not settled(said.get(h['id'], {})) or (h['id'] in cmp and said[h['id']].get('with_png') != cmp[h['id']]['png']))]
    if passed:
        return [f"must: {h['rule']}" for h in row['rules'] if h not in mine and h.get('class') != 'should' and said.get(h['id'], {}).get('pass') is True
                and cmp.get(h['id'], {'state': 'ready'})['state'] == 'ready']
    return [f"{h.get('class') or 'must'}: {h['rule']}" for h in mine] + [f"{r.get('class') or 'must'}: {r['rule']}" for i, r in said.items()
                                                                        if i not in {h['id'] for h in row['rules']} and not settled(r)]


def still_rules(held):
    """Fix set B3 (19 Nov 2026): the rules a still end-frame is checked on, as lines for the checker: the musts of a marked list that a still can
    show (every must not marked `motion`). None for a list with no mark (written before the marks): the checker reads rules.md as before."""
    if not any(h.get('shows') for h in held or []):
        return None
    return [f"must: {h['rule']}" for h in held if h.get('class') != 'should' and h.get('shows') != 'motion']


NOTE_DARK, NOTE_LIGHT = '#2B2B2B', '#F2EFE8'   # design/221 row 9: charcoal on a light ground, off-white on a dark one
GROUND_WORDS = re.compile(r'\b(back)?ground\b|\bpaper\b|\bcanvas\b|\bpage\b|\bbackdrop\b', re.I)


def corner_note(spec):
    """design/221 row 9: the words the server draws in the corner: the label of a spec that carries "not to scale" (illustrative), else ''."""
    return str((spec or {}).get('label') or '').strip() if (spec or {}).get('illustrative') else ''


def ground_colour(plan, run):
    """design/221 rows 1 and 9: the film's ground: the colour the plan's palette, then the film record's colours, names for the ground (background,
    paper, canvas, page); '' when none is named."""
    for text in (str(((plan.get('foundation') or {}).get('graphic_style') or {}).get('palette') or ''), str(film.colours(run) or '')):
        for m in re.finditer(r'([^,;#]*?)\s*(#[0-9A-Fa-f]{6})\b', text):
            if GROUND_WORDS.search(m.group(1)):
                return m.group(2)
    return ''


def note_colour(plan, run):
    """design/221 row 9: the corner note's colour on the film's ground: charcoal on a light ground, off-white on a dark one; no ground named: a light
    ground is taken."""
    ground = ground_colour(plan, run)
    if not ground:
        return NOTE_DARK
    r, g_, b = (int(ground[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return NOTE_DARK if 0.2126 * r + 0.7152 * g_ + 0.0722 * b >= 0.5 else NOTE_LIGHT


def drawn_ids(plan, session):
    """design/221 row 1: the drawn shots of the plan's chosen scenes, in plan order."""
    return [s['id'] for g_ in plan['gaps'] for sc in chosen_scenes(g_, session['choice_selections'].get(g_['gap_id'])) for s in sc['shots'] if s.get('visual_type') == 'drawn']


PARTS_FIRST = ('This film has {n} drawn graphics: their shared parts are drawn once, before any brief. Run `vw motion parts`, start one `vw-motion-parts` helper, '
               'and upload its file with `vw motion parts --file work/motion/parts/parts.svg`; the operator approves its picture in the chat (`vw visuals next`). '
               'Then brief each drawing.')
PARTS_WAIT = "The shared parts wait for the operator's approval in the chat (`vw visuals next`): no brief before they are approved."
PARTS_REJECTED = ('The operator rejected the shared parts: "{words}". Give these words to a `vw-motion-parts` helper to redraw them, then upload again '
                  '(`vw motion parts --file work/motion/parts/parts.svg`).')
PARTS_ONE = 'This film has one drawn graphic: it has no shared parts. Brief it directly (`vw motion brief --shot S`).'
PARTS_AGAIN = ' Change the drawing, then upload it again: the same file is refused again.'   # fix set M6: each of these refusals ends with the next step
PARTS_USE_ONE = ('{shot} shows {thing} but uses none of its shared parts: place the view this drawing shows, one of {ids}, with <use href="#part-…"> '
                 '(drawn once for the whole film; do not redraw it).' + PARTS_AGAIN)
PARTS_USE = '{shot} shows {thing} but does not use its shared part: place {id} with <use href="#{id}"> (drawn once for the whole film; do not redraw it).' + PARTS_AGAIN
PARTS_USE_VIEW = ('{shot} shows {thing} in the view {view} but does not place its part of that view: place {ids} with <use href="#part-…"> '
                  '(drawn once for the whole film; do not redraw it).' + PARTS_AGAIN)   # fix set B2
PARTS_OWN_ID = ('{shot} defines {ids}, the id of a shared part: the server puts the shared parts in the page; place them with <use href="#…"> and give your '
                'own elements other ids.')
PARTS_LINE = ('Use these parts (drawn once for the whole film; do not redraw them): {parts}. Place the view this drawing shows{view} with '
              '<use href="#part-<name>"> (one view of a thing is enough): the server puts them in the page, and parts.svg beside this brief shows them.')   # fix set A3.2: was "Place each"
PARTS_EVERY = ('Shapes that are no thing of the plan repeat too: read every spec below and list first each shape that two or more drawings show, with the '
               'drawings that show it and its count where a spec gives one; then draw each once, and name on its symbol the drawings that show it '
               '(data-shots, from: {ids}). Where two specs give another count or proportion for the same shape, that is an open choice: answer with it '
               'and the count you recommend.')   # fix set A1.1, A1.5
PARTS_NONE = 'No shape repeats across the drawings: there are no shared parts. Brief the drawings now (`vw motion brief --shot S`).'   # fix set A1.1: nothing to show, so no card
MOTION_PARTS_CHANGED = 'Its parts changed since this drawing was rendered: render it again (`vw motion render --shot {shot}`); nothing is rebuilt.'


def parts_ready(session):
    """design/221 row 1: the latest parts upload is the approved one."""
    ok = session.get('motion_parts_approved') or {}
    return bool(ok) and ok.get('sha256') == (session.get('motion_parts') or {}).get('sha256')


def need_parts(plan, session):
    """design/221 row 1: with two or more drawn graphics, no brief before the shared parts are approved."""
    n = len(drawn_ids(plan, session))
    if n < 2:
        return
    up = session.get('motion_parts') or {}
    need(up, PARTS_FIRST.format(n=n))
    need(not up.get('rejected'), PARTS_REJECTED.format(words=(up.get('rejected') or {}).get('words')))
    need(parts_ready(session), PARTS_WAIT)


def _part_names(p, shot):
    """Issue 15 (VW-25, hotfix 25 Nov 2026): a part that names its drawings (data-shots) is theirs alone, also when it draws a thing of the plan; one
    that names none is not narrowed. Before: a thing's part was asked from every drawing that names the thing, whatever the part's own list (retired:
    VW-25's plan named the filler slab on two drawings of a solid slab, the part did not, and no upload of theirs could pass)."""
    return not p.get('shots') or shot['id'] in p['shots']


def shot_parts(session, shot):
    """design/221 row 1: the approved parts a shot uses: those drawing one of its things, and those that draw no thing of the plan. Fix set A1.1:
    a part that names its drawings (data-shots) is used by those; one of no thing that names none is every drawing's, as before."""
    els = set(shot.get('element_ids') or [])
    return [p for p in (session.get('motion_parts_approved') or {}).get('parts') or []
            if _part_names(p, shot) and (p.get('element') in els or shot['id'] in (p.get('shots') or []) or not (p.get('element') or p.get('shots')))]


def view_parts(session, shot):
    """Fix set B2 (19 Nov 2026): {thing: its approved parts drawn in the view this shot's spec states}, for the brief and the upload. {} when the
    spec states no view; a thing with no part drawn in that view is left out (then one of its views is enough, as defect 56's fix)."""
    view = (shot.get('drawing_spec') or {}).get('view') or ''
    out = {}
    for p in (session.get('motion_parts_approved') or {}).get('parts') or []:
        if view and p.get('view') == view and p.get('element') in (shot.get('element_ids') or []) and _part_names(p, shot):
            out.setdefault(p['element'], []).append(p['id'])
    return out


PARTS_NO_VIEW = ' No part of {things} is drawn in the view {view}: draw it in this drawing yourself, and place no part of another view for it.'


def fit_parts(session, shot):
    """Release 2, F5 (20 Nov 2026): {thing: its approved parts a drawing of this shot may place for it}, for the upload and the brief: every part of
    the thing when the spec states no view; with a stated view, its parts drawn in that view or naming no view. A thing drawn in other views only
    has an empty list: nothing of it is demanded (the wrong view is the wrong picture), and the brief says to draw it."""
    view = (shot.get('drawing_spec') or {}).get('view') or ''
    out = {}
    for p in (session.get('motion_parts_approved') or {}).get('parts') or []:
        if p.get('element') in (shot.get('element_ids') or []) and _part_names(p, shot):   # issue 15: a thing whose parts all name other drawings is left out: nothing of it is asked, and the brief says nothing
            out.setdefault(p['element'], []).extend([p['id']] if not view or (p.get('view') or view) == view else [])
    return out


def parts_differ(session, used):
    """Release 2, F7: these parts as a still was checked with them ({part id: its digest}) are not the approved ones now."""
    now = {p['id']: p.get('digest') for p in (session.get('motion_parts_approved') or {}).get('parts') or []}
    return any(now.get(i) != d for i, d in (used or {}).items())


def parts_wait(plan, session):
    """Release 2, F11: what the builders of the drawn graphics wait for while the shared parts are not the approved ones (none yet, rejected, or a
    new file on its card), in `need_parts`'s own sentence; '' when nothing is waited for."""
    try:
        need_parts(plan, session)
    except ValueError as exc:
        return str(exc)
    return ''


def parts_in_force(session, files):
    """design/221 rows 1 and 3: the approved parts a project places, {key, used: {part id: its digest}}, for the render request (a changed part it uses
    changes the request, so its take is rendered again); {} when it places none. ponytail: a part placed only inside another part is not followed."""
    ok = session.get('motion_parts_approved') or {}
    text = ' '.join(motion_texts(files).values())
    used = {p['id']: p['digest'] for p in ok.get('parts') or [] if re.search(r'href\s*=\s*["\']#' + re.escape(p['id']) + r'["\']', text)}
    return {'key': ok['key'], 'used': used} if used else {}


def motion_texts(files):
    from . import motion
    return motion._texts(files)


def shown_twice(plan, shots):
    """design/221 row 1: the things of the plan that two or more of these drawn shots show, as one line: "E1 Block (D1, D2); …"; '' for none."""
    twice = [(e, [s['id'] for s in shots if e['id'] in (s.get('element_ids') or [])]) for e in plan.get('elements') or []]
    return '; '.join(f"{e['id']} {e.get('name') or e['id']} ({', '.join(ids)})" for e, ids in twice if len(ids) >= 2)


PARTS_EMPTY = ('The parts file is empty, and these things are shown by two or more drawings: {things}. Draw each once as a shared part (one <symbol id="part-…"> each) '
               'and upload the file again; an empty file is only for a film where nothing repeats.')   # the critic's point 2


def parts_brief(store, run, outputs):
    """design/221 row 1: what the `vw-motion-parts` helper reads: the things two or more drawings show, then every drawn shot's brief (its spec, the
    sizes confirmed on its things, the palette, the fonts, the shared look, the pictures to look at); and the operator's words on a rejected file."""
    _motion_run(run)
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    ids = drawn_ids(plan, session)
    need(len(ids) >= 2, PARTS_ONE)
    briefs = [motion_brief(store, run, outputs, sid, session=session) for sid in ids]
    shots = {sid: guarded(lambda sid=sid: locate(store, session, sid))[3] for sid in ids}
    bare = [sid for sid in ids if shots[sid].get('drawing_spec') and (session.get('spec_approvals') or {}).get(sid, {}).get('digest') != spec_digest(shots[sid]['drawing_spec'])]
    need(not bare, f"The shared parts are drawn from the approved specs: approve the drawing spec of {', '.join(bare)} first (on the page, `vw visuals page`).")
    els = {e['id']: e for e in plan.get('elements') or []}
    twice = shown_twice(plan, shots.values())
    head = ['# Shared parts of the drawn graphics', '', f"Things shown by two or more drawings (each is a part to draw once): {twice or 'none'}.",
            'Things of the plan (data-element names the id): ' + '; '.join(f"{e} {x.get('name') or e}" for e, x in els.items()) + '.',
            PARTS_EVERY.format(ids=', '.join(ids))]   # fix set A1.1: every shape that repeats, not only the plan's things
    return {'brief': '\n'.join(head + [f"\n## {b['shot_id']}\n\n{b['brief']}" for b in briefs]), 'refs': need_pictures(store, run, session, list(dict.fromkeys(r for b in briefs for r in b['refs'])), 'The shared parts'),
            **({'rejected': (session.get('motion_parts') or {})['rejected']['words']} if (session.get('motion_parts') or {}).get('rejected') else {})}


def set_parts(store, user, run, outputs, name, content):
    """design/221 row 1: the film's shared parts file (one SVG of symbols, from the `vw-motion-parts` helper), checked like a project and kept with
    the run, with one picture of the parts (Chromium, as the font sample; the file itself when Chromium cannot draw it); asked in the chat."""
    from . import font_sample, motion
    _motion_run(run)
    session = session_of(store, run, outputs)
    plan = guarded(lambda: current_plan(store, session))
    need(len(drawn_ids(plan, session)) >= 2, PARTS_ONE)
    need(re.search(r'\.svg$', name or '', re.I) and content and len(content) <= motion.MAX_PARTS, 'The shared parts are one .svg file under 1 MB (work/motion/parts/parts.svg).')
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = ''
    parts, problems = motion.read_parts(text, {e['id'] for e in plan.get('elements') or []}, drawn_ids(plan, session)) if text else ([], ['the parts file is not UTF-8 text'])
    need(not problems, 'The parts file breaks the rules: ' + '; '.join(problems[:6]))
    ok = session.get('motion_parts_approved') or {}   # issue 16 (R1): a part whose drawing is the same as in the approved file keeps the approved part's fingerprint,
    try:   # so a change of its labels alone makes no still, render or brief stale. Retired: any change inside a part's <symbol>, also of its labels or spacing, made them all stale
        was = motion.part_drawings(store.get(ok['key']).decode('utf-8')) if ok.get('parts') and parts else {}
    except Exception:   # noqa: BLE001: the approved file cannot be read: nothing is carried, the upload goes on as before
        was = {}
    now, kept = motion.part_drawings(text) if was else {}, {p['id']: p['digest'] for p in ok.get('parts') or []}
    parts = [{**p, 'digest': kept[p['id']]} if p['id'] in kept and was.get(p['id']) and was[p['id']] == now.get(p['id']) else p for p in parts]
    twice = '' if parts else shown_twice(plan, [guarded(lambda sid=sid: locate(store, session, sid))[3] for sid in drawn_ids(plan, session)])
    need(not twice, PARTS_EMPTY.format(things=twice))   # the critic's point 2: an empty file stands only when the server's own list of what repeats is empty
    sha = hashlib.sha256(content).hexdigest()
    base = f"{run['id']}/visuals/motion/parts/{sha}"
    store.put(base + '.svg', content, 'image/svg+xml')
    if not parts:   # fix set A1.1: a film where no shape repeats: nothing to draw and nothing to show, so it stands at once
        at = datetime.now(timezone.utc).isoformat()
        session['motion_parts'] = {'sha256': sha, 'key': base + '.svg', 'name': name, 'parts': [], 'by': user['id'], 'at': at}
        session['motion_parts_approved'] = {'sha256': sha, 'key': base + '.svg', 'parts': [], 'quote': 'no shape repeats: nothing to approve', 'by': user['id'], 'at': at}
        save_session(store, run, session)
        return {'sha256': sha, 'parts': [], 'next': PARTS_NONE}
    ground = ground_colour(plan, run) or '#FFFFFF'
    from . import drawn   # fix set A3.1: the names in the film's font (its files under server/fonts, as the font sample reads them); ponytail: a brand font given as a file is kept with the run, not on disk, so its film gets the default here
    preview = motion.parts_preview(text, parts, ground, note_colour(plan, run), fonts=[(drawn.FONTS / f).as_uri() for f in film_font_files(run)])
    try:
        store.put(base + '.png', font_sample.render(f'<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:{ground}">{preview}</body></html>'), 'image/png')
        picture, why = base + '.png', ''
    except Exception as exc:   # noqa: BLE001: no Chromium: the card shows the drawing itself
        store.put(base + '-preview.svg', preview.encode('utf-8'), 'image/svg+xml')
        picture, why = base + '-preview.svg', f'{exc.__class__.__name__}: {exc}'[:200]
    session['motion_parts'] = {'sha256': sha, 'key': base + '.svg', 'name': name, 'parts': parts, 'picture_key': picture, **({'picture_error': why} if why else {}),
                               'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    return {'sha256': sha, 'parts': [p['id'] for p in parts],
            'next': f"Shared parts stored ({len(parts)}): their picture is in the chat for the operator to approve (`vw visuals next`); no brief before."
                    + (' The picture could not be drawn by the server: the card shows the parts drawing itself.' if why else '')}


def parts_changed(store, session):
    """design/221 row 1: the drawn shots whose last render placed parts that are not the approved ones now (rendered again, not rebuilt)."""
    from . import motion
    out = []
    for sid, prep in (session.get('preparations') or {}).items():
        try:
            req = load_json(store, prep['key']) if prep.get('drawn') and prep.get('key') else {}
            row = (session.get('motion_projects') or {}).get(req.get('sha256') or '') if req.get('kind') == 'motion' else None
            if row and (req.get('parts') or {}).get('used') != (parts_in_force(session, motion.unpack(store.get(row['key']))).get('used')):
                out.append(sid)
        except (Problem, ValueError, KeyError):
            continue
    return out


def parts_answer(store, user, run, outputs, sha, ok, quote, words=''):
    """design/221 row 1: the operator's Approve (the file's digest recorded; it is the one pasted into every drawing) or Reject with their words
    (sent back for the helper to redraw; the next upload replaces the file and is asked again)."""
    session = session_of(store, run, outputs)
    up = session.get('motion_parts') or {}
    need(up.get('sha256') == sha, 'These shared parts are not the latest upload: run `vw visuals next` again.')
    at = datetime.now(timezone.utc).isoformat()
    if ok:
        session['motion_parts_approved'] = {**{k: up[k] for k in ('sha256', 'key', 'parts')}, 'quote': quote, 'by': user['id'], 'at': at}
        up.pop('rejected', None)
        save_session(store, run, session)
        stale = parts_changed(store, session)
        return {'recorded': True, 'for_the_assistant': 'The shared parts are approved: brief the drawings now (`vw motion brief --shot S`).'
                + (f" Its parts changed for {', '.join(stale)}: render each again (`vw motion render --shot S`) after its brief, rules and verdict are read again." if stale else '')}
    need(str(words or '').strip(), 'Say what to change in the parts, in the operator\'s words.')
    up['rejected'] = {'words': str(words).strip(), 'quote': quote, 'by': user['id'], 'at': at}
    save_session(store, run, session)
    return {'recorded': True, 'for_the_assistant': PARTS_REJECTED.format(words=str(words).strip())}


def _motion_request(store, session, run, shot_id, sha=None):
    """The request a check, snapshot or render reads: the project, the server's files, the film's frame, the plan's labels and cues as a timing sidecar."""
    from . import drawn, motion
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    need(shot['visual_type'] == 'drawn', f"shot {shot['id']} is {shot['visual_type']}: the motion route is for a drawn shot.")
    sm = shot.get('scene_motion') or {}
    own = sm.get('sha256') or (session.get('motion_bound') or {}).get(shot['id']) or ''   # design/221 (the critic's A1): the plan's sha (the older way), else the project bound at its clean verdict
    sha = sha or own
    row = (session.get('motion_projects') or {}).get(sha)
    need(row, f"{shot['id']}: the plan's scene_motion names no uploaded project ({sha[:12]}…): take sha256 out of it; the server binds the project that passes its fact check."
         if sha and sha == sm.get('sha256') else f"{shot['id']}: {sha[:12]}… is no uploaded project of this film." if sha else
         f"no project of {shot['id']} has passed its fact check yet: upload it (`vw motion upload --shot {shot['id']}`), check it, and send the checker's verdict "
         f"(`vw motion verdict --shot {shot['id']}`); the render takes the project that passed.")
    fps, W, H = _film_frame(session)
    words = ((session['source']['gaps'].get(gap['gap_id']) or {}).get('timing') or {}).get('words')
    plans = sha == own or not sm.get('sha256')   # the plan's labels and cues count for the plan's project, the bound one, or any project while the plan names none (the critic's point 2)
    cues = sm.get('cues') if plans else []
    seconds = guarded(lambda: drawn.cue_seconds({'actions': cues or []}, shot, words, fps))
    images = {}
    files = motion.unpack(store.get(row['key']))
    for rid in motion.ref_ids(files):
        ref = session['references'].get(rid)
        need(ref and ref.get('status') == 'approved' and ref.get('key'), f"the project places assets/ref/{rid}.png, which is not an approved picture of this run.")
        images[rid] = ref['key']
    fonts = {n: k for n, k in [('NotoSans-Variable.ttf', None)] + ([(Path(session['font']['name']).name, session['font']['key'])] if session.get('font') else []) + list(film_font_files(run).items())}   # design/139 R13
    spec = shot.get('drawing_spec')
    frames = shot['end_frame'] - shot['start_frame']
    exact = Fraction(frames) / Fraction(str(fps))
    labels = sm.get('labels') or [] if plans else []
    finish = motion.finish_in_force(motion.finish_of(files)[0], off=bool((session.get('motion_finish_off') or {}).get(shot['id'])))   # design/186: only when there is one, so an older shot's request is unchanged
    note = corner_note(spec)   # design/221 row 9: from the spec, so a project not yet named in the plan gets it too
    note_fonts = list(dict.fromkeys(list(film_font_files(run)) + ([Path(session['font']['name']).name] if session.get('font') else []) + ['NotoSans-Variable.ttf']))
    parts = parts_in_force(session, files)   # design/221 row 1: the approved parts it places, pasted by the server; a changed one changes this request
    return shot, spec, files, {
        **({'finish': finish} if finish else {}),
        **({'parts': parts} if parts else {}),
        **({'note': {'text': note, 'fonts': note_fonts, 'colour': note_colour(plan, run)}} if note else {}),
        'kind': 'motion', 'shot_id': shot['id'], 'sha256': sha, 'project_key': row['key'], 'width': W, 'height': H, 'fps': str(fps), 'frames': frames,
        'images': images, 'fonts': fonts, 'labels': labels, 'sidecar': motion.sidecar(seconds, [c['selector'] for c in cues or []]),
        'plan_digest': digest(plan), 'palette': str(((plan.get('foundation') or {}).get('graphic_style') or {}).get('palette') or ''),
        'claims': shot.get('claims') or [], 'relationships': (spec or {}).get('relationships') or [], 'view': spec_view(shot)[0] if spec else None,
        'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame'], 'film_fps': str(fps), 'duration_seconds': str(exact), 'exact_seconds': float(exact)}}


SNAPSHOT_FRAMES = 12   # the frames one snapshot call takes (one HyperFrames run in the worker); kept at 12: the worker's time for more was not measured (fix set A3.6)


def motion_tool(conn, store, user, run, outputs, body):
    """design/130 §4 step 3: `hyperframes check` or `snapshot` of an uploaded project of the shot, run in the worker on the VM (no laptop needs Node);
    the helper reads the findings or the PNGs back. Free; never a take."""
    _motion_run(run)
    op = body.get('op')
    need(op in ('check', 'snapshot'), 'op is check or snapshot (a render is `vw motion render`).')
    asked = len(body.get('at') or [])   # fix set A3.6, M5: the limit is the server's own sentence, with what to do (it was the route's "at: List should have at most 12 items")
    need(asked <= SNAPSHOT_FRAMES, f'A snapshot call takes at most {SNAPSHOT_FRAMES} frames (--at); {asked} were asked: nothing was taken. Ask in two calls of {SNAPSHOT_FRAMES} or fewer.')
    session = session_of(store, run, outputs)
    _shot, _spec, files, request = _motion_request(store, session, run, body['shot_id'], body.get('sha256'))
    at = [round(float(t), 3) for t in (body.get('at') or [])]
    if op == 'snapshot':
        need(at and all(0 <= t <= request['frames'] / float(Fraction(str(request['fps']))) for t in at), 'Give the seconds to snapshot (--at 0.5,2.0), inside the shot.')
    crops = [[round(float(x), 4) for x in c] for c in (body.get('crops') or [])][:6]   # design/130 §4 step 5: close-ups for the checker, fractions of the frame
    need(all(len(c) == 4 and 0 <= c[0] < 1 and 0 <= c[1] < 1 and 0 < c[2] <= 1 - c[0] + 1e-9 and 0 < c[3] <= 1 - c[1] + 1e-9 for c in crops),
         'A crop is left,top,width,height as fractions of the frame, inside it (0.5,0.4,0.3,0.3).')
    request.update(kind=f'motion-{op}', at=at, zoom=str(body.get('zoom') or '')[:80], crops=crops)
    key_ = key(run, f"motion/tools/{digest({**request, 'n': uuid.uuid4().hex})}.json")
    save_json(store, key_, request)
    row = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,'motion',%s, gen_random_uuid()) returning id",
                       (run['id'], body['shot_id'], Jsonb({'kind': request['kind'], 'request_key': key_, 'shot_id': body['shot_id'], 'sha256': request['sha256']}))).fetchone()   # design/221 row 17: the project it checked
    return {'job_id': str(row['id']), 'request_key': key_, 'next': f'{op} queued: `vw motion status --job {row["id"]}` shows the findings' + (' and saves the PNGs.' if op == 'snapshot' else '.')}


def render_motion(conn, store, user, run, outputs, body):
    """design/130 §4 step 4: the plan's HyperFrames project rendered by the pinned CLI at the film's size and frame rate, every label found word for word
    first, the spec approved when the shot has one; cached by the request's digest; free; reviewed and selected like a take."""
    from . import motion
    _motion_run(run)
    need_free(conn, store, run, [body.get('shot_id')])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = session_of(store, run, outputs)
    shot, spec, files, request = _motion_request(store, session, run, body['shot_id'])
    _no_question(session, shot['id'])   # design/110 rule 0
    if spec:
        need((session.get('spec_approvals') or {}).get(shot['id'], {}).get('digest') == spec_digest(spec),
             f"the drawing spec of {shot['id']} is not approved, or changed since: the operator approves the sizes, materials and graphic specs on the page (`vw visuals page`), before the drawing is rendered.")
    missing = motion.missing_labels(files, [l for l in request['labels'] if _flat(l) != _flat(corner_note(spec))])   # design/221 row 9: the server draws the note
    need(not missing, '; '.join(f'the project does not show the label "{l}" word for word' for l in missing) + ': fix the text in the project or the label in the plan.')
    lost = motion.missing_selectors(files, [c['selector'] for c in (shot.get('scene_motion') or {}).get('cues') or []])
    need(not lost, f"the plan's cues name {', '.join(lost)}, which the project does not have (an element id).")
    identity = digest(request)
    key_ = key(run, f'takes/{identity}.motion.json')
    save_json(store, key_, request)
    frames, exact = request['frames'], request['placement']['exact_seconds']
    same = [j for j in take_jobs(conn, run, shot['id']) if j.get('provider') == 'drawn' and (j.get('request') or {}).get('preparation_id') == identity and j['status'] not in ('failed', 'rejected', 'cancelled')]
    session['preparations'][shot['id']] = {'preparation_id': identity, 'key': key_, 'drawn': True}
    if same:
        save_session(store, run, session)
        return {'job_id': str(same[0]['id']), 'preparation_id': identity, 'frames': frames, 'cached': True, 'next': 'Already rendered from this project (nothing changed): it is on the Pictures and drawn graphics step (`vw visuals page`).'}
    row_ = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,'drawn',%s, gen_random_uuid()) returning id",
                        (run['id'], shot['id'], Jsonb({'kind': 'motion', 'request_key': key_, 'preparation_id': identity, 'shot_id': shot['id'], 'frames': frames, 'duration_seconds': exact,
                                                       'sha256': request['sha256'], 'plan_digest': request['plan_digest'],   # design/221 (the critic's points 3, 4): the step-6 count reads
                                                       'parts': (request.get('parts') or {}).get('used') or {}}))).fetchone()   # which project it rendered and whether it went stale
    save_session(store, run, session)
    return {'job_id': str(row_['id']), 'preparation_id': identity, 'frames': frames, **({'finish': request['finish'], 'tell_the_operator': motion.finish_words(request['finish'])} if request.get('finish') else {}),
            'next': f'Rendering {frames} frames on the server: HyperFrames checks the project and the timing, renders, and the drawing and its sheet come to the Pictures and drawn graphics step '
                    '(`vw visuals page`): the operator selects it there or rejects it with what to change.'}


def motion_finish(conn, store, user, run, outputs, shot_id, on):
    """design/186 (SK, 12 Nov 2026): the finish of a drawn shot taken away, or put back, by the operator: the same drawing rendered once more
    without (or with) the layer. One function for the page's button and `vw motion finish`. Free. A new take: the selection is not moved."""
    from . import motion
    _motion_run(run)
    need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = session_of(store, run, outputs)
    shot, _spec, files, _request = _motion_request(store, session, run, shot_id)
    asked = motion.finish_of(files)[0]
    need(asked, f"The drawing of {shot['id']} has no finish: there is nothing to take away or put back.")
    off_now = bool((session.get('motion_finish_off') or {}).get(shot['id']))
    if off_now == (not on):
        return {'changed': False, 'finish': [] if off_now else asked, 'next': 'The drawing is already without its finish.' if off_now else 'The drawing already has its finish.'}
    flags = session.setdefault('motion_finish_off', {})
    if on:
        flags.pop(shot['id'], None)
    else:
        flags[shot['id']] = {'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    save_session(store, run, session)
    from . import runlog
    runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f"shot {shot['id']}", 'rule': 'design/186 (a finish is a layer the operator can have taken away)',
                        'entry': ('the finish put back: ' if on else 'the finish taken away: ') + ', '.join(asked), 'by_kind': 'operator', 'by_name': user.get('name') or '', 'quote': '', 'request_id': None})
    out = render_motion(conn, store, user, run, outputs, {'shot_id': shot['id']})
    return {**out, 'changed': True, 'finish': asked if on else [],
            'next': ('The drawing is being rendered again with its finish' if on else 'The drawing is being rendered again without the finish') + ': it comes back to the Pictures and drawn graphics step in under a minute, for the operator to answer there.'}


SUBJECT_RULES = Path(__file__).resolve().parents[1] / 'subject_rules'   # design/130 §4 step 8: one file per subject, seeded in the repo


def subject_rule_files():
    return sorted(p.stem for p in SUBJECT_RULES.glob('*.md'))


def _subject_rules(store, stem):
    """The subject's rules: the repo's seed lines, then the operators' additions kept in storage (every film reads both). design/221 row 14: as
    [(where they come from, rules)]: the subject file, then each film a rule was added on, in the order they were added."""
    seed = [l[2:].strip() for l in (SUBJECT_RULES / f'{stem}.md').read_text(encoding='utf-8').splitlines() if l.startswith('- ')]
    try:
        added = json.loads(store.get(f'subject-rules/{stem}.json').decode('utf-8'))
    except Problem:
        added = []
    films = {}
    for r in added:
        films.setdefault(f"added on film {r['run']}" if r.get('run') else 'added by an operator', []).append(r['rule'])
    return [(f'from the subject file {stem}.md', seed)] * bool(seed) + list(films.items())


NEUTRAL_MAX_CHROMA = 0.10   # design/218: a colour whose brightest and darkest channel differ by at most this share is a neutral (a grey, an off-white, a near-black)


def chroma(colour):
    """(max - min) of the channels of #RRGGBB, from 0 (a grey) to 1."""
    c = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return round(max(c) - min(c), 3)


def added_colour(session, plan, user, thing, colour, words, reason, shots, quote=''):
    """design/218 A: a colour for a thing the palette names none for, kept in the session beside the plan (never in the accepted plan): Claude's
    when it is a neutral; a hue, or a second colour for the same thing, only with the operator's words. The same colour again adds its shots."""
    from .font_sample import drawn_shots
    key = ' '.join(str(thing or '').lower().split())
    need(key and len(key) <= 80, 'Name the thing the colour is for (--thing, at most 80 characters).')
    colour = str(colour or '').strip().upper()
    need(re.fullmatch(r'#[0-9A-F]{6}', colour), 'Give the colour as #RRGGBB (--colour).')
    need(str(words or '').strip() and str(reason or '').strip(), 'Give the colour in plain words (--words "dark warm grey") and one plain reason (--reason "the palette named none").')
    drawn = {s['id'] for s in drawn_shots(plan)}
    need(shots and all(s in drawn for s in shots), f"Name the drawn shots that show it (--shot): {', '.join(s for s in shots if s not in drawn) or 'none given'} "
                                                   f"is not a drawn shot of the plan ({', '.join(sorted(drawn)) or 'none'}).")
    quote = str(quote or '').strip()
    need(quote or chroma(colour) <= NEUTRAL_MAX_CHROMA, f'{colour} is not a neutral (its chroma {chroma(colour):.2f} is above {NEUTRAL_MAX_CHROMA:.2f}): a real hue is the '
                                                       "operator's choice: ask the operator, then give their words with --quote.")
    rows = session.setdefault('added_colours', {})
    have = rows.get(key)
    need(not have or have['colour'] == colour or quote, f"The {have and have['thing']} already have {have and have['colour']} ({have and have['words']}), added for every drawing: "
                                                        "it stands; a change needs the operator's words (--quote)." if have else '')
    if have and have['colour'] == colour:
        have['shots'] += [s for s in shots if s not in have['shots']]
        return have
    rows[key] = {'thing': ' '.join(str(thing).split()), 'colour': colour, 'words': str(words).strip(), 'reason': str(reason).strip().rstrip('.'), 'shots': list(dict.fromkeys(shots)),
                 'by': 'operator' if quote else 'claude', 'quote': quote, 'user': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    return rows[key]


def add_colour(store, user, run, outputs, body):
    session = session_of(store, run, outputs)
    plan = current_plan(store, session)
    row = added_colour(session, plan, user, body['thing'], body['colour'], body['words'], body['reason'], body['shots'], body.get('quote'))
    save_session(store, run, session)
    return {'colour': row, 'next': f"Added for every drawing of this film: {row['thing']} {row['colour']} ({row['words']}). The next briefs carry it (`vw motion brief`); "
                                   'the operator sees it under Details on the drawing, nothing is asked.'}


VIEW_UNSTATED = 'not stated (the spec does not state the view: state it in the drawing note when another drawing shows the same part from another direction)'


def view_words(spec):
    """design/218b: the spec's direction of view as the brief says it; a spec without one says so plainly (no new required field)."""
    return spec.get('view') or VIEW_UNSTATED


def drawing_note(session, plan, user, shots, text):
    """design/218b: one plain line Claude records for the drawings it names (a part seen from another direction is the same part), kept beside
    the plan, carried in their briefs and shown under Details on their lines. The same line for the same drawings is kept once. Never refuses
    an upload or a verdict: it is only a record."""
    from .font_sample import drawn_shots
    text = ' '.join(str(text or '').split())
    need(text, 'Give the note as one plain line (--text).')
    need(len(text) <= 300, 'The note is one plain line of at most 300 characters.')
    drawn = {s['id'] for s in drawn_shots(plan)}
    shared = list(shots or []) == ['all']   # design/221 row 7: the shared look, a line for every drawing of the film
    shots = sorted(drawn) if shared else shots
    need(shots and all(s in drawn for s in shots), f"Name the drawn shots the note is for (--shot): {', '.join(s for s in shots if s not in drawn) or 'none given'} "
                                                   f"is not a drawn shot of the plan ({', '.join(sorted(drawn)) or 'none'}).")
    rows = session.setdefault('drawing_notes', [])
    same = next((r for r in rows if r['text'] == text and (set(r['shots']) == set(shots) or shared and r.get('shared'))), None)
    if same:
        return same
    rows.append({'text': text, 'shots': list(dict.fromkeys(shots)), **({'shared': True} if shared else {}), 'by': 'claude', 'user': user['id'], 'at': datetime.now(timezone.utc).isoformat()})
    return rows[-1]


def withdraw_note(session, shots, text):
    """design/218b: the named drawings leave the note that reads `text`; a note with no drawing left is deleted."""
    text = ' '.join(str(text or '').split())
    rows = session.get('drawing_notes') or []
    if list(shots or []) == ['all']:   # design/221 row 7: a shared-look line leaves every drawing
        need(any(r['text'] == text and r.get('shared') for r in rows), f'No shared-look line reads "{text}": nothing to withdraw.')
        session['drawing_notes'] = [r for r in rows if not (r['text'] == text and r.get('shared'))]
        return
    for shot in shots:
        row = next((r for r in rows if r['text'] == text and shot in r['shots'] and not r.get('shared')), None)   # a shared-look line leaves only with --shot all
        need(row, f'No note on {shot} reads "{text}": nothing to withdraw (the notes are in its brief, `vw motion brief --shot {shot}`).')
        row['shots'].remove(shot)
    session['drawing_notes'] = [r for r in rows if r['shots']]


def add_note(store, user, run, outputs, body):
    session = session_of(store, run, outputs)
    if (body.get('remove') or '').strip():
        withdraw_note(session, body['shots'], body['remove'])
        save_session(store, run, session)
        return {'notes': session['drawing_notes'], 'next': f"Withdrawn from {', '.join(body['shots'])}: the next briefs of those drawings no longer carry it."}
    row = drawing_note(session, current_plan(store, session), user, body['shots'], body['text'])
    save_session(store, run, session)
    return {'note': row, 'next': f"Recorded for {'every drawing of this film (the shared look)' if row.get('shared') else ', '.join(row['shots'])}: the next briefs of those drawings carry it (`vw motion brief`); the operator sees it under Details, nothing is asked."}


def palette_line(plan, session):
    """design/218: the brief's palette: the plan's, then the colours added since (design/218 A), so every drawing agrees."""
    base = ((plan.get('foundation') or {}).get('graphic_style') or {}).get('palette') or 'the approved style picture'
    from .font_sample import drawn_shots
    drawn = {s['id'] for s in drawn_shots(plan)}   # a colour whose drawings all left the plan is not given (existence only)
    added = '; '.join(f"{r['thing']} {r['colour']} ({r['words']})" for r in (session.get('added_colours') or {}).values() if drawn & set(r['shots']))
    approved = bool(session.get('accepted') or session.get('shared_pending'))   # design/221 row 14: as palette_due counts it: approved once a gap was accepted
    return f"Palette ({'approved' if approved else 'not yet approved'}): {base.rstrip('.')}." + (f' Added for every drawing of this film (the spec wins where they differ): {added}.' if added else '')


def add_subject_rule(store, user, run, subject, rule, quote):
    """design/130 §4 step 8: a correction kept as a rule of its subject for every later film, only with the operator's words."""
    stem = re.sub(r'[^a-z0-9-]', '', str(subject or '').lower())
    need(stem in subject_rule_files(), f"There is no subject rules file named {subject!r} ({', '.join(subject_rule_files())}); a new subject is added by the builder.")
    need(str(rule or '').strip() and len(rule) <= 400, 'Give the rule in one line (at most 400 characters).')
    quote = said(quote, 'Added', user)
    k = f'subject-rules/{stem}.json'
    try:
        rows = json.loads(store.get(k).decode('utf-8'))
    except Problem:
        rows = []
    rows.append({'rule': rule.strip(), 'quote': quote, 'by': user['id'], 'run': run.get('code'), 'at': datetime.now(timezone.utc).isoformat()})
    store.put(k, json.dumps(rows, ensure_ascii=False).encode('utf-8'), 'application/json')
    return {'subject': stem, 'rules': rows, 'next': f'Kept: every later film on {stem} starts its rules with it.'}


def _subjects_of(plan, shot=None):
    """The subjects whose every name word is in the film's plan text, or in the shot's own words when a shot is named (design/134 16)
    (ponytail: a word match; a subject field on the brief if two subjects ever collide)."""
    text = (' '.join(str(shot.get(k) or '') for k in ('narration', 'depicts', 'purpose', 'message')) if shot else
            ' '.join([json.dumps(plan.get('foundation') or {}), *(g.get('intent') or '' for g in plan.get('gaps') or []),
                      *(s.get('narration') or '' for g in plan.get('gaps') or [] for sc in all_scenes(g) for s in sc.get('shots') or [])])).lower()
    words = set(re.findall(r'[a-z0-9]+', text))
    return [stem for stem in subject_rule_files() if set(stem.split('-')) <= words]


MOTION_RULE_OPEN = ('{shot}: the verdict leaves {n} rule(s) of the project without an answer, first: "{rule}". Every rule of rules.md gets pass true or false: '
                    'add the missing ones and send the verdict again (`vw motion verdict`).')
MOTION_RULE_UNKNOWN = ('{shot}: "{rule}" is not a rule of this project (rules.md as it was uploaded): copy each rule\'s words as they are, or upload the project again '
                       'with its rules (`vw motion upload`).')
MOTION_RULE_WORDS = '{shot}: the failed rule "{rule}" says nothing of what was seen: give `where` (or `fix`) in one plain sentence and send the verdict again.'
NOT_A_RULE = ('A note or a question is not a rule: move these lines to questions.md: {lines}. A builder helper does not edit rules.md or questions.md: '
              'give these lines back to the main assistant, who moves them and uploads again.')   # design/221 row 15; the critic's A3: the lines named, and who acts
MOTION_BRIEF_CHANGED = ('{shot}: the brief changed after these rules were written, in the line(s): {names}. Read the rules of this drawing again against the new brief '
                        '(`vw motion brief --shot {shot}`), then upload again with the rules (`vw motion upload --shot {shot}`).')   # design/221 S3


def brief_changed(was, now):
    """design/221 S3: the labels of the brief's lines that differ between the brief the rules were written from and the brief now, in the brief's order."""
    return [k for k in list(now) + [k for k in was if k not in now] if was.get(k) != now.get(k)]


def stale_brief(store, run, outputs, session, sha, shot_id, now=None):
    """design/221 (the critic's A2): the brief lines changed since the rules of this project were written ([] when it kept no brief, or no brief can
    be made now). `now`: a function giving a shot's current lines, so a caller works each shot's brief out once."""
    was = ((session.get('motion_projects') or {}).get(sha or '') or {}).get('brief')
    if not was:
        return []
    try:
        lines = now(shot_id) if now else motion_brief(store, run, outputs, shot_id, session=session)['lines']
    except (Problem, ValueError):
        return []
    return brief_changed(was, lines)


def _flat(text):
    return ' '.join(str(text or '').split()).lower()


def diagram_shots(plan, session, gap, shot):
    """design/221 rows 12 and 17: the drawn shots of the same diagram, from the plan: (the gap's drawn shots in order, this one included; the drawn
    shots linked to this one by return_of, either way)."""
    pick = lambda g_: [s for sc in chosen_scenes(g_, session['choice_selections'].get(g_['gap_id'])) for s in sc['shots']]
    mine = [s for s in pick(gap) if s.get('visual_type') == 'drawn']
    linked = [s for g_ in plan['gaps'] for s in pick(g_) if s.get('visual_type') == 'drawn' and s['id'] != shot['id']
              and (s['id'] == shot.get('return_of') or s.get('return_of') == shot['id'])]
    return mine, linked


def continues_from(plan, session, gap, shot):
    """design/221 row 12: the drawn shot this one continues: the drawn shot right before it in its gap, else the drawn shot it returns to; '' for
    none. Fix set M2 (19 Nov 2026): only a drawn shot next to it in the film (no other shot between them) is continued; the plan check says so
    (`apart`)."""
    before = [s for sc in chosen_scenes(gap, session['choice_selections'].get(gap['gap_id'])) for s in sc['shots'] if s['start_frame'] < shot['start_frame']]
    if before and max(before, key=lambda s: s['start_frame']).get('visual_type') == 'drawn':
        return max(before, key=lambda s: s['start_frame'])['id']
    return next((s['id'] for s in diagram_shots(plan, session, gap, shot)[1] if s['id'] == shot.get('return_of')), '')


def is_shot(store, run, outputs, shot_id):
    """Release 3, C6: whether this is a shot of the run's current plan (a defect names its shot by the plan's id)."""
    try:
        return _item_kind(store, session_of(store, run, outputs), shot_id) == 'shot'
    except (ValueError, KeyError, Problem):
        return False


def held_chain(plan, session, shot):
    """Release 3, C6: the held shot, then each drawing that continues from it (a chain): they wait for the same defect (held_line, need_free)."""
    wait, grown = [shot], True
    while grown:   # a chain: each drawing that continues one that waits
        grown = False
        for gap in plan['gaps']:
            for sc in chosen_scenes(gap, session['choice_selections'].get(gap['gap_id'])) if not gap.get('choices') or session['choice_selections'].get(gap['gap_id']) else []:
                for s in sc['shots']:
                    if s.get('visual_type') == 'drawn' and s['id'] not in wait and continues_from(plan, session, gap, s) in wait:
                        wait.append(s['id'])
                        grown = True
    return wait


def need_free(conn, store, run, shots):
    """The critic's point 1 on release 3: the one guard of a write that acts on a shot, in the server functions every front end calls (the tool,
    the chat's items and cards, the page): refused while an open defect holds the shot, or the drawing it continues from (point 2), or the step."""
    from . import core
    shots = [s for s in shots if isinstance(s, str) and s]
    if conn is None or not shots:
        return
    rows = core.open_defect_rows(conn, run['id'])
    if any(d.get('shot') for d in rows):
        try:
            session = session_of(store, run, [])
            plan = current_plan(store, session)
            rows = [{**d, 'chain': held_chain(plan, session, d['shot'])} if d.get('shot') else d for d in rows]
        except (Problem, ValueError, KeyError, StopIteration, TypeError):
            pass   # no plan to read: the named shot alone is held
    core.need_free(rows, 'visuals', shots)


def held_line(plan, session, defects):
    """Release 3, C6: the next-step sentence for each open defect that names a shot: the shot is held, the drawings that continue from it wait
    for it too, everything else goes on. '' when no open defect names a shot (a defect about a step refuses the call itself)."""
    out = []
    for d in defects:
        if not d.get('shot'):
            continue
        wait = held_chain(plan, session, d['shot'])
        out.append(f"Defect {d['defect']} is open on {d['shot']}: nothing more is sent for {d['shot']} until the builder says it is fixed. "
                   + (f"{', '.join(wait[1:])} continue{'s' if len(wait) == 2 else ''} from it and wait{'s' if len(wait) == 2 else ''} for it too. " if wait[1:] else '')
                   + 'Everything else goes on.')
    return ' '.join(out)


def apart(shots):
    """Fix set M2: the drawn shots of one gap (its shots in film order) that follow an earlier drawing with another shot between them and name no
    return: [(the shot, the earlier drawing, the shots between)]. Such a drawing does not continue the earlier one."""
    out, order = [], sorted(shots, key=lambda s: s['start_frame'])
    for n, s in enumerate(order):
        back = next((k for k in range(n - 1, -1, -1) if order[k].get('visual_type') == 'drawn'), None)
        if s.get('visual_type') == 'drawn' and back is not None and back < n - 1 and not s.get('return_of'):
            out.append((s, order[back], order[back + 1:n]))
    return out


LABEL_MUST = '{message}. It is a label of this shot only, so this is a must: keep it on screen at least its floor, then upload and check again.'   # design/221 row 17


def short_labels(report, own, shared):
    """design/221 row 17 (SK's revised ruling): the HyperFrames check's `line_unread` warnings (each starts with the label's own words in quotes) for a
    label among this shot's labels and not among a neighbouring shot's of the same diagram, as plain sentences; a label shared with a neighbour is not counted."""
    out, whole = [], lambda text: _flat(text).rstrip('.').strip()   # design/221 (the critic's A2): whole labels, case and a trailing full stop aside
    mine, theirs = {whole(l) for l in own}, {whole(l) for l in shared}
    for w in (report or {}).get('warnings') or []:
        m = re.match(r'\s*"([^"]+)"', str(w.get('message') or '')) if w.get('code') == 'line_unread' else None
        said = whole(m.group(1)) if m else ''
        if said and said in mine and said not in theirs:
            out.append(LABEL_MUST.format(message=str(w['message']).strip().rstrip('.')))
    return out


def own_short_labels(plan, session, gap, shot, report):
    """design/221 row 17: short_labels with this shot's plan labels against the labels of the other drawn shots of the same diagram."""
    mine, linked = diagram_shots(plan, session, gap, shot)
    labels = lambda s: (s.get('scene_motion') or {}).get('labels') or []
    return short_labels(report, labels(shot), [l for s in mine + linked if s['id'] != shot['id'] for l in labels(s)])


def label_musts(conn, store, session, run, plan, gap, shot, sha):
    """design/221 row 17: the musts of the latest HyperFrames check of this project (a check job names its project since design/221)."""
    rows = conn.execute("select id, unit, request, result, status from vw2_jobs where run_id=%s and provider='motion' and unit=%s order by created_at", (run['id'], shot['id'])).fetchall()
    checks = [j for j in rows if j.get('unit') == shot['id'] and j.get('status') == 'ready' and (j.get('request') or {}).get('kind') == 'motion-check'
              and (j.get('request') or {}).get('sha256') == sha]
    need(checks, MOTION_NOT_CHECKED.format(shot=shot['id'], sha=sha))   # design/221 (the critic's A6): without a check the short-label must is not known
    return own_short_labels(plan, session, gap, shot, checks[-1].get('result'))


MOTION_NOT_CHECKED = ('{shot}: there is no finished check of this project: run `vw motion check --shot {shot} --sha {sha}` first, then send the verdict again.')


NOT_SEEN = 'not seen'   # design/221 row 12: the third answer to a rule: the checker could not judge it from its frames
NA = 'na'   # release 1, A3 (SK, 20 Nov 2026): "does not apply here", an answer to a check line everywhere Claude checks (a set, a picture, a take, a drawing's rule), with one sentence why
# A4: the guard. The server cannot see the picture, so it is said where the checker reads how to judge (the `how` served with the looks)
NA_HOW = ('A line may also be answered "does not apply here": `"pass": "na"`, with one sentence in `seen` saying why. Give it only when this view cannot show '
          'the thing the line asks about, or the line is about another thing than this picture shows: for example a line about how a hand holds a tool, where '
          'no hand is in the frame; a line about the whole room, on a close view of one object. Never for something that is in view: that passes or fails.')


def answered(row):
    """design/221 (the critic's A1): the digest of the rules and the brief lines a verdict answers, from the project's row in motion_projects."""
    return digest({'rules': (row or {}).get('rules') or [], 'brief': (row or {}).get('brief') or {}})


def motion_rounds(session, shot_id, sha):
    """The verdicts of one project of a shot that answered its current rules and brief; a record from before the digest counts (the older way, kept)."""
    now = answered((session.get('motion_projects') or {}).get(sha))
    return [c for c in (session.get('motion_checks') or {}).get(shot_id) or [] if c.get('sha256') == sha and c.get('answered', now) == now]


def open_rules(rec):
    """design/221 rows 11, 12, 17: what keeps a verdict from being clean: a failed must, a rule not seen yet, a short label of this shot only."""
    return ([r['rule'] for r in (rec or {}).get('rules') or [] if (r.get('pass') is False and r.get('class') != 'should') or r.get('pass') == NOT_SEEN]
            + list((rec or {}).get('label_musts') or []))


HELD_ROUNDS = 3   # design/221 row 18: after round 3 a drawing with an open must is held; "One more round" on its card allows round 4, once
HELD_LIMIT = ('{shot}: round {rnd} is past the last round ({top}): the drawing is held and the operator decides on its card in the chat (`vw visuals next`); '
              '"One more round" there allows round 4, once.')
HELD_MORE_USED = '{shot}: the one more round is used: select it anyway with a reason, or reject it.'


def held_rules(rec):
    """The failed musts of a verdict (a not-seen rule is still being judged, not failed)."""
    return [r['rule'] for r in (rec or {}).get('rules') or [] if r.get('pass') is False and r.get('class') != 'should'] + list((rec or {}).get('label_musts') or [])


def held_drawing(session, shot_id):
    """design/221 row 18: the latest verdict of the shot's animated project when a must still fails after its last round (3, or 4 after "One more
    round") and the operator has not answered its card; else None."""
    rec = next((c for c in reversed((session.get('motion_checks') or {}).get(shot_id) or []) if not c.get('still')), None)
    if not rec or not held_rules(rec) or int(rec.get('round') or 1) < HELD_ROUNDS + bool((session.get('motion_more') or {}).get(shot_id)):
        return None
    ans = (session.get('motion_held') or {}).get(shot_id) or {}
    return None if (ans.get('sha256'), ans.get('round')) == (rec.get('sha256'), rec.get('round')) else rec


def held_answer(conn, store, user, run, outputs, shot_id, job_id, choice, quote, words=''):
    """design/221 row 18: the operator's answer on a held drawing's card: select it anyway (with their reason, as select_take asks of a held
    drawing), reject it (rebuilt from round 1), or one more round (once: the server then takes round 4)."""
    need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = session_of(store, run, outputs)
    rec = held_drawing(session, shot_id)
    need(rec, f'{shot_id}: no drawing of it is held now: run `vw visuals next`.')
    need(choice in ('select', 'reject', 'more'), f'Not an answer to a held drawing: {choice!r} (select, reject or more).')
    need(choice != 'more' or not (session.get('motion_more') or {}).get(shot_id), HELD_MORE_USED.format(shot=shot_id))
    words = str(words or '').strip()
    if choice == 'select' and not words:   # the critic's point 10a (release 1, B1): one click, as on the page: no reason is asked; the fixed note says so
        from . import pictures
        words = pictures.W['against_note']
    out = select_take(conn, store, user, run, outputs, job_id, quote, words) if choice == 'select' else {}   # refused there, nothing is recorded here
    session = session_of(store, run, outputs)
    session.setdefault('motion_held', {})[shot_id] = {'sha256': rec.get('sha256'), 'round': rec.get('round'), 'answer': choice, 'words': words, 'quote': quote,
                                                      'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    if choice == 'more':
        session.setdefault('motion_more', {})[shot_id] = True
    save_session(store, run, session)
    if choice == 'select':
        return {**out, 'recorded': True}
    review_take(conn, store, user, run, outputs, job_id, 'rejected', words or ("one more round, at the operator's word" if choice == 'more' else ''), '', quote)
    if choice == 'more':
        return {'recorded': True, 'for_the_assistant': (f"{shot_id}: one more round, at the operator's word: give the open musts to a `vw-motion-shot` helper to redo it and "
                                                        'send its verdict as round 4. After it the operator decides again: select it anyway or reject it.')}
    return {'recorded': True, 'for_the_assistant': f'{shot_id}: the operator rejected the held drawing' + (f': "{words}".' if words else '.')
            + ' Give a new `vw-motion-shot` helper the open musts' + (' and these words' if words else '') + ' to rebuild it, and check it again from round 1.'}


def passed_project(session, shot):
    """design/221 row 2: the sha of the shot's project that passed its fact check (the bound one, else the plan's with a clean verdict), else ''."""
    sha = (session.get('motion_bound') or {}).get(shot['id']) or ((shot.get('scene_motion') or {}).get('sha256') or '')
    took = (session.get('motion_held') or {}).get(shot['id']) or {}
    if sha and ((took.get('answer') == 'select' and took.get('sha256') == sha) or shot['id'] in (session.get('selections') or {})):
        return sha   # design/221 (the critic's point 1, phases 3-4): a held drawing the operator selected anyway, or a selected shot, is passed for the drawing after it
    st = (session.get('motion_stills') or {}).get(shot['id']) or {}
    if opens_changed(session, st.get('opens_from'), st):   # release 2, F1: built on a still that was replaced: not a project the next drawing is built on
        return ''
    rounds = motion_rounds(session, shot['id'], sha) if sha else []
    return sha if rounds and not open_rules(rounds[-1]) else ''


def drawn_turn(session, plan, gap, shot, shots):
    """Fix set A1.4 (19 Nov 2026): whose turn a drawn shot is, from what the server holds: ('still' | 'motion': its builder can start now;
    'check-still' | 'check': its checker can start now; '': the operator's turn, the render's, or nothing yet, the drawing it waits on or '').
    `shots`: the plan's shots by id. Nothing can start before the shared parts are approved: `pictures.expected` holds a builder's turn for them."""
    sid = shot['id']
    mine = sorted(((p.get('at') or '', sha, p) for sha, p in (session.get('motion_projects') or {}).items() if p.get('shot_id') == sid), key=lambda x: x[0])
    prev = continues_from(plan, session, gap, shot)
    if not mine:   # the critic's point 7: its still opens on the earlier drawing's approved still (or its passed project, the older order)
        return ('', prev) if prev and not (opens_on(session, prev) or (prev in shots and passed_project(session, shots[prev]))) else ('still', '')
    _, sha, row = mine[-1]
    st = (session.get('motion_stills') or {}).get(sid) or {}
    if opens_changed(session, prev, row if row.get('still') else st):   # the critic's point 7: the earlier still was replaced: this still is made again, once the new one is
        return ('still', '') if opens_on(session, prev) else ('', prev)   # approved. Release 2, F1: whatever came after this still (its motion, a verdict, a render)
    rec = next((c for c in reversed((session.get('motion_checks') or {}).get(sid) or []) if c.get('sha256') == sha), None)
    kind = 'still' if row.get('still') else 'motion'
    if not rec or any(r.get('pass') == NOT_SEEN for r in rec.get('rules') or []):
        return ('check-still' if row.get('still') else 'check'), ''
    if held_rules(rec):   # a failed must: its redo, unless the drawing is held after its last round
        if row.get('still') or int(rec.get('round') or 1) < HELD_ROUNDS + bool((session.get('motion_more') or {}).get(sid)):
            return kind, ''
        ans = (session.get('motion_held') or {}).get(sid) or {}   # release 2, F4: held, and the operator answered its card with Reject: rebuilt
        return ('motion' if (ans.get('sha256'), ans.get('round'), ans.get('answer')) == (rec.get('sha256'), rec.get('round'), 'reject') else ''), ''
    if row.get('still') and st.get('sha256') == sha:
        if st.get('rejected') or (still_approved(st) and parts_differ(session, st.get('parts'))):
            return 'still', ''   # the operator's Reject: the still again. Release 2, F7: and a still checked with parts that were drawn anew since (its motion would be refused as stale)
        if still_approved(st):   # their Approve: its motion, which a continuing drawing builds on the earlier drawing's passed project
            return ('', prev) if prev and not (prev in shots and passed_project(session, shots[prev])) else ('motion', '')
    return '', ''   # the operator's card, or the render


MOTION_RULE_NEED = ('{shot}: the rule "{rule}" is not seen: say in `need` the frame or crop that would show it (a snapshot at 2.4 s, a crop of the joint) '
                    'and send the verdict again.')
MOTION_RULE_FAILED_BEFORE = ('{shot}: in round 2 or 3 a verdict may leave out a rule that passed before, but every rule that failed before is answered: '
                             '{n} left out, first: "{rule}". Add it and send the verdict again.')   # design/221 row 13
# release 1, A3, A4: "does not apply" always says why; a rule already judged is in view, so it is never cleared this way
MOTION_RULE_NA = ('{shot}: the rule "{rule}" is answered "na" (does not apply here) with no reason: say in `why`, in one sentence, why this drawing cannot show it or what '
                  'other thing the rule is about; or answer it pass or fail. Then send the verdict again.')
MOTION_RULE_NA_JUDGED = ('{shot}: the rule "{rule}" {was} in an earlier round, so this drawing shows it: answer it pass or fail, not "na", and send the verdict again.')


def settled(rule):
    """Release 1, A3: an answer that is not asked again: a pass, or "does not apply" (recorded once)."""
    return rule.get('pass') is True or rule.get('pass') == NA


def _rule_class(r):
    """design/221 rows 11 and 13: a held rule's class (none: a must); a rule the checker adds itself (group "seen") is a should unless it says must
    and names its kind in one line (a wrong count, a wrong fact, a part that reads as something else, a label that cannot be read)."""
    if r.get('group') == 'seen' and not r.get('held'):   # design/221 (the critic's A3): the kind is one of the four, not any text
        kind = re.sub(r'^(a|an)\s+', '', _flat(r.get('kind')).strip(' .'))
        return 'must' if str(r.get('class') or '').lower() == 'must' and kind in MUST_KINDS else 'should'
    return 'must'   # design/221 (the critic's A5): a rule of a project uploaded without rules is never downgraded by the checker


MUST_KINDS = ('wrong count', 'wrong fact', 'part that reads as something else', 'label that cannot be read')   # design/221 ruling M4


def motion_verdict(store, user, run, outputs, body, conn=None):
    """design/130 §4 step 5: a fresh checker's verdict on one uploaded project of a shot, kept per shot by round; the failed rules go back to a builder
    helper, at most two redo rounds; select holds a drawing whose project has no clean verdict. design/221 phase 2: only a failed must sends it back
    (failed shoulds are notes); a rule "not seen" waits for its frames, answered by the same checker in the same round; in a later round a rule that
    passed before may be left out (it keeps its pass); with `conn`, a label of this shot only that the latest check finds too short is a must."""
    from . import pictures
    _motion_run(run)
    need_free(conn, store, run, [body.get('shot_id')])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = session_of(store, run, outputs)
    plan, gap, _scene, shot = guarded(lambda: locate(store, session, body.get('shot_id') or ''))
    sha = body.get('sha256') or ''
    need(sha in (session.get('motion_projects') or {}), f"{shot['id']}: {sha[:12]}… is no uploaded project of this film.")
    rules = body.get('rules') or []
    held = ((session.get('motion_projects') or {}).get(sha) or {}).get('rules') or []
    was = ((session.get('motion_projects') or {}).get(sha) or {}).get('brief')
    still = bool(((session.get('motion_projects') or {}).get(sha) or {}).get('still'))   # design/221 row 3: a verdict is the still's by its project's mark
    at = session['motion_projects'][sha].get('at') or ''   # the critic's point 5: an animated project that a newer upload replaced (a redraw) and that is not the bound one takes no verdict: nothing is bound on it again
    st_ = (session.get('motion_stills') or {}).get(shot['id']) or {}
    kept = st_.get('sha256') if (st_.get('at') or '') <= at else None   # the still this project was built from, uploaded again unchanged, is no redraw
    need(still or (session.get('motion_bound') or {}).get(shot['id']) == sha
         or not any(p.get('shot_id') == shot['id'] and s_ not in (sha, kept) and (p.get('at') or '') > at for s_, p in session['motion_projects'].items()), REDONE.format(shot=shot['id']))
    base = '' if still else base_changed(session, plan, gap, shot)   # release 2, F1, F2, F6: no verdict (so no binding, no comparison answered) on a project built on a still that was replaced
    need(not base, STILL_OPENS.format(shot=shot['id'], prev=base))
    cmp = comparing(session, plan, held)   # fix set A1.2: the rules that compare with another drawing
    idle = {i for i, c in cmp.items() if c['state'] != 'ready'}   # nothing to compare with yet (or the other drawing left the plan): a note, not this verdict's
    idle |= left_out(session, shot['id'], sha)   # the critic's point 1: nor a comparison that turned ready after the upload: its checker was not given the frame
    bare = still and still_rules([h for h in held if h['id'] not in idle]) == []   # the carry-over c2: no rule of the list is one a still can show: an empty verdict passes the still
    need((rules or bare) and all(isinstance(r, dict) and (r.get('pass') is True or r.get('pass') is False or r.get('pass') in (NOT_SEEN, NA)) and str(r.get('rule') or '').strip() for r in rules),
         'The verdict lists the rules checked; every rule has pass true or false (or "not seen", with the frame it needs in `need`; or "na", it does not apply here, with why in `why`) '
         'and its words (`rule`).')
    rules = [{**r, 'rule': str(r['rule'])[m.end():] if (m := pictures.RULE_CLASS.match(str(r['rule']))) else r['rule']} for r in rules]   # row 11: a class copied into the words is not part of them
    rules = [{**r, **({'with_png': cmp[i]['png']} if i in cmp else {})} for r in rules for i in [pictures.rule_id(r['rule'])] if i not in idle]   # compared with this picture of the other drawing
    frame = ''
    if still and conn is not None:   # the checker judged the still's last frame: the card shows that frame
        frame = last_frame_key(conn, run, shot['id'], sha, last_second(shot, session['source']['fps']))
        need(frame, STILL_FRAME.format(shot=shot['id'], sha=sha, last=last_second(shot, session['source']['fps'])))
    if was:   # design/221 S3: no verdict on rules written from an older brief
        changed = brief_changed(was, motion_brief(store, run, outputs, shot['id'], session=session)['lines'])
        need(not changed, MOTION_BRIEF_CHANGED.format(shot=shot['id'], names=', '.join(f'"{k}"' for k in changed)))
    mute = [r['rule'] for r in rules if r['pass'] is False and not str(r.get('where') or r.get('fix') or r.get('seen') or '').strip()]
    need(not mute, MOTION_RULE_WORDS.format(shot=shot['id'], rule=str(mute[0])[:160] if mute else ''))
    blind = [r['rule'] for r in rules if r['pass'] == NOT_SEEN and not str(r.get('need') or '').strip()]
    need(not blind, MOTION_RULE_NEED.format(shot=shot['id'], rule=str(blind[0])[:160] if blind else ''))
    bare_na = [r['rule'] for r in rules if r['pass'] == NA and not str(r.get('why') or '').strip()]
    need(not bare_na, MOTION_RULE_NA.format(shot=shot['id'], rule=str(bare_na[0])[:160] if bare_na else ''))
    marked = any(h.get('shows') for h in held)   # release 2, F9: in a list with marks, a rule with none is one a still can show, as `still_rules` gives it to the checker
    marks = {h['id']: h.get('shows') or ('still' if marked else None) for h in held}   # fix set B3: each rule is marked when it is written: a still can show it, or only motion shows it
    if still:   # a still shows no motion: an answer to a rule only motion shows is not the still's, whatever it says. A rule with no mark (a list written
        # before the marks) keeps the hotfix of 19 Nov (VW-24): answered "not seen" on a still it is a rule left out, never a frame to fetch or "not seen twice"
        rules = [r for r in rules if marks.get(pictures.rule_id(r['rule'])) != 'motion' and (r['pass'] != NOT_SEEN or marks.get(pictures.rule_id(r['rule'])) == 'still')]
    rnd = int(body.get('round') or 1)
    top = HELD_ROUNDS + bool((session.get('motion_more') or {}).get(shot['id']))   # design/221 row 18: round 4 only after "One more round"
    need(still or rnd <= top, HELD_LIMIT.format(shot=shot['id'], rnd=rnd, top=top))
    prev = ((session.get('motion_checks') or {}).get(shot['id']) or [None])[-1]
    said = {pictures.rule_id(r.get('rule')): r for r in (prev or {}).get('rules') or []}
    fresh = {i for i, c in cmp.items() if c['state'] == 'ready' and said.get(i, {}).get('with_png') != c['png']} - idle   # fix set A1.2: a comparison not yet answered against the other drawing's picture as it is now
    same = (bool(prev) and prev.get('sha256') == sha and int(prev.get('round') or 1) == rnd
            and (any(r.get('pass') == NOT_SEEN for r in prev.get('rules') or []) or bool(fresh)))   # row 12: the frames a "not seen" asked for, answered in the same round; A1.2: a comparison that came due
    later = bool(prev) and not same and rnd >= 2 and rnd > int(prev.get('round') or 1)   # row 13: round 2 or 3 answers what failed and what the fix touched
    brief_at = digest(was or {})   # fix set A1.6: a pass stands only for the same brief lines (a record from before names none: it counts, the older way)
    earlier = {i: e for i, e in said.items() if i not in idle and i not in fresh} if (same or later) and prev.get('brief_at', brief_at) == brief_at else {}
    if still:   # the same for what an earlier verdict of the still recorded: a motion rule's answer, or an unmarked rule's not seen or "not seen twice"
        earlier = {i: e for i, e in earlier.items() if marks.get(i) != 'motion'
                   and (marks.get(i) == 'still' or (e.get('pass') != NOT_SEEN and not str(e.get('where') or '').startswith('not seen twice')))}
    got = {i: ({**r, 'pass': False, 'twice': True, 'where': f"not seen twice in round {rnd} ({r.get('need')})"} if same and r['pass'] == NOT_SEEN and earlier.get(i, {}).get('pass') == NOT_SEEN else r)
           for i, r in ((pictures.rule_id(r.get('rule')), r) for r in rules)}   # design/221 (the critic's A4): not seen twice in a round is a failed must
    out_ = idle | ({i for i, r in got.items() if r.get('twice')} if still else set())   # the carry-over c1: on a still a rule not seen twice is left out (the animated drawing answers it): a still never loops on "not seen"
    got, earlier = {i: r for i, r in got.items() if i not in out_}, {i: e for i, e in earlier.items() if i not in out_}
    judged = [(r['rule'], earlier[i]['pass']) for i, r in got.items() if r['pass'] == NA and i in earlier and isinstance(earlier[i].get('pass'), bool)]   # release 1, A4: a rule that passed or failed before keeps the existing rules
    need(not judged, MOTION_RULE_NA_JUDGED.format(shot=shot['id'], rule=str(judged[0][0])[:160], was='passed' if judged[0][1] else 'failed') if judged else '')
    if held:   # design/217 (C6): the verdict answers the project's whole rule list, by the rules' own words; a project uploaded before keeps the older way (any list)
        known = {h['id']: h for h in held}
        unknown = [r['rule'] for i, r in got.items() if i not in known and i not in earlier and r.get('group') != 'seen']   # a fault the checker adds of its own is a new rule, group "seen"
        need(not unknown, MOTION_RULE_UNKNOWN.format(shot=shot['id'], rule=str(unknown[0])[:160] if unknown else ''))
        open_before = [e['rule'] for i, e in earlier.items() if later and not settled(e) and i not in got]   # release 1, A3: a rule that did not apply is not asked again
        need(not open_before, MOTION_RULE_FAILED_BEFORE.format(shot=shot['id'], n=len(open_before), rule=str(open_before[0])[:160] if open_before else ''))
        skipped = [h['rule'] for h in held if (not still or (marks[h['id']] == 'still' and h.get('class') != 'should'))   # row 3, fix set B3: a still answers the musts marked as ones a still can show; an unmarked list, any of them
                   and h['id'] not in out_ and h['id'] not in got and not (h['id'] in earlier and (same or settled(earlier[h['id']])))]
        need(not skipped, MOTION_RULE_OPEN.format(shot=shot['id'], n=len(skipped), rule=str(skipped[0])[:160] if skipped else ''))
        rules = [{**(got.get(h['id']) or {**earlier[h['id']], 'carried': True}), 'class': h.get('class') or 'must', 'held': True} for h in held
                 if (not still or h['id'] in got or h['id'] in earlier) and h['id'] not in out_]
        rules += [{**e, 'class': e.get('class') or _rule_class(e), 'carried': True} for i, e in earlier.items() if i not in known and i not in got]
    else:
        rules = [{**e, 'class': e.get('class') or _rule_class(e), 'carried': True} for i, e in earlier.items() if i not in got] if same else []
    rules += [{**r, 'class': earlier[i]['class']} if i in earlier and earlier[i].get('class') else {**r, 'class': _rule_class(r)}
              for i, r in got.items() if not held or i not in {h['id'] for h in held}]
    musts = {pictures.rule_id(r.get('rule')) for c in (session.get('motion_checks') or {}).get(shot['id']) or [] for r in c.get('rules') or [] if r.get('class') == 'must'}
    rules = [{**r, 'class': 'must'} if r.get('twice') or pictures.rule_id(r['rule']) in musts else r for r in rules]   # design/221 (the critic's A5): once a must, always a must
    labels = label_musts(conn, store, session, run, plan, gap, shot, sha) if conn is not None else []   # row 17
    failed = [r for r in rules if r['pass'] is False and r['class'] == 'must']
    notes = [r['rule'] for r in rules if r['pass'] is False and r['class'] == 'should']
    blind = [{'rule': r['rule'], 'need': str(r.get('need') or '')} for r in rules if r['pass'] == NOT_SEEN]
    na = [{'rule': r['rule'], 'why': ' '.join(str(r.get('why') or '').split())[:500]} for r in rules if r['pass'] == NA]   # release 1, A4: a note for the operator, never a failed must: it holds nothing, no frame is fetched, no round is counted
    rec = {'sha256': sha, 'round': rnd, 'stranger': [str(x)[:500] for x in body.get('stranger') or []][:20] or list((prev or {}).get('stranger') or []) * same,
           'rules': [{k: (str(r.get(k))[:500] if k not in ('pass', 'carried') else r[k]) for k in ('n', 'group', 'rule', 'pass', 'class', 'kind', 'where', 'fix', 'need', 'why', 'carried', 'with_png') if k in r}
                     for r in rules][:80],
           **({'label_musts': labels} if labels else {}), 'answered': answered((session.get('motion_projects') or {}).get(sha)), 'brief_at': brief_at,   # the critic's A1: the rules and brief it answered
           **({'still': True} if still else {}), 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    session.setdefault('motion_checks', {}).setdefault(shot['id'], []).append(rec)
    names = [r['rule'] for r in failed] + labels
    bound = session.setdefault('motion_bound', {})   # the critic's A1: the server notes the passed project for its shot; the render follows with no plan change
    if still:   # design/221 row 3: a still is never the shot's drawing; with no failed must it waits for the operator in the chat
        if not names and not blind:
            from . import motion
            try:
                png = hashlib.sha256(store.get(frame)).hexdigest() if frame else ''
            except Problem:
                png = frame
            was_st = (session.get('motion_stills') or {}).get(shot['id']) or {}
            st = {'sha256': sha, 'frame_key': frame, 'png': png, 'parts': parts_in_force(session, motion.unpack(store.get(session['motion_projects'][sha]['key']))).get('used') or {},
                  'at': rec['at'], **{k: v for k, v in session['motion_projects'][sha].items() if k in ('opens_on', 'opens_from')}}   # the critic's point 7
            if png and (was_st.get('approved') or {}).get('png') == png:   # the same picture made again (the parts changed elsewhere): its approval stays
                st['approved'] = was_st['approved']
            session.setdefault('motion_stills', {})[shot['id']] = st
    elif (not names and not blind) or (names and rnd >= top):   # design/221 row 18: a drawing held after its last round is bound too, rendered for its card
        bound[shot['id']] = sha
    elif bound.get(shot['id']) == sha:
        bound.pop(shot['id'])
    save_session(store, run, session)
    n_notes = f"{len(notes)} note{'' if len(notes) == 1 else 's'}"
    if names and not still and rnd >= top:
        nxt = (f"Held after round {rnd}: {len(names)} must rule{' still fails' if len(names) == 1 else 's still fail'}. Render it (`vw motion render --shot {shot['id']}`): "
               "the operator decides on its card in the chat (`vw visuals next`): select it anyway with a reason, reject it, or one more round"
               + ('.' if top > HELD_ROUNDS else ' (once).'))
    elif still and names:
        nxt = (f"{len(names)} rules failed on the still: give them to a vw-motion-shot helper for {shot['id']} to redo the still (the still's rounds do not count "
               "against the animation's three).")
    elif still and not blind:
        nxt = (f"The still end-frame passed ({n_notes}): the operator approves it in the chat (`vw visuals next`); build the motion only after the approval, "
               "without changing what the still shows." + (' Its approval stays: the picture is the same as the one approved.' if still_approved(session['motion_stills'][shot['id']]) else ''))
    elif names:
        nxt = (f"{len(names)} rules failed: give them to a vw-motion-shot helper for {shot['id']} to redo (round {rnd + 1}; after round 3 the drawing is held)"
               + (f", with the {n_notes} to fix in the same redo." if notes else '.') + (f" {len(blind)} rules not seen are answered in the next round." if blind else ''))
    elif blind:
        nxt = (f"{len(blind)} rules not seen: take these frames (`vw motion snapshot --shot {shot['id']} --at … --crop …`) and give them to the same checker for these rules "
               f"only, then send its verdict with the same round ({rnd}); nothing is rebuilt: " + '; '.join(f"\"{b['rule']}\": {b['need']}" for b in blind))
    else:
        other = (shot.get('scene_motion') or {}).get('sha256')
        nxt = (f"Passed, {n_notes}: `vw motion render --shot {shot['id']}`."
               + (f" The plan names another project for {shot['id']} ({other[:12]}…): take sha256 out of its scene_motion first, so the render takes this one." if other and other != sha else '')
               + (' The notes are shown with the drawing: ' + '; '.join(f'"{n}"' for n in notes) + '.' if notes else ''))
    return {'shot_id': shot['id'], 'round': rnd, 'failed': names, 'notes': notes, 'not_seen': blind, **({'na': na} if na else {}),
            'log': f"round {rnd}: {len(names)} of {len(rules)} rules failed" + (': ' + '; '.join(f'"{n}"' for n in names) if names else '')   # design/221 row 22: the log line says what failed
                   + (f'; {n_notes}' if notes else '') + (f'; {len(blind)} not seen' if blind else '')
                   + (f'; {len(na)} did not apply: ' + '; '.join(f"\"{x['rule']}\" ({x['why']})" for x in na) if na else ''),   # release 1, A5: kept in the run's log
            'next': nxt}


def motion_brief(store, run, outputs, shot_id, session=None, build=False, conn=None):
    """design/130 §4 step 1: the designer's brief for one drawn shot, built from the plan (the test bench's prompt.txt shape): the length to the frame,
    the narration with each word's second, what it shows, the palette, the spec, the claims, the labels, the pictures and the rules. Deterministic.
    session: the one the caller already read (design/221, the critic's A2), else read here. build (`vw motion brief`): the gates before a build
    (every drawn shot with text has its labels in the plan; a drawing that continues another waits for its passed project) and `continues`."""
    _motion_run(run)
    session = session or session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    need(shot['visual_type'] == 'drawn', f"shot {shot['id']} is {shot['visual_type']}: a brief is for a drawn shot.")
    need_motion_style(run)   # design/221 S1: no brief before its facts: the motion style (asked at the treatment), then the font; a film from before passes as it did
    need_font(run, session)
    fps, W, H = _film_frame(session)
    frames = shot['end_frame'] - shot['start_frame']
    exact = Fraction(frames) / Fraction(str(fps))
    f = float(Fraction(str(fps)))
    words = [w for w in ((session['source']['gaps'].get(gap['gap_id']) or {}).get('timing') or {}).get('words') or [] if shot['start_frame'] <= w['start_frame'] < shot['end_frame']]
    timed = ', '.join(f"{w['text']} {(w['start_frame'] - shot['start_frame']) / f:.2f}" for w in words) or 'none recorded: key cues with at_s'
    spec = shot.get('drawing_spec') or {}
    fonts = _motion_fonts(store, session, run)
    pictures = sorted(brief_pictures(session, shot), key=lambda p: p[0].lower())   # design/221 S3: one order whatever order the session was saved in
    look = look_pictures(session, shot)
    sm = shot.get('scene_motion') or {}
    shared = [f"- {n['text']}" for n in session.get('drawing_notes') or [] if n.get('shared')]
    for miss in film.missing_letters(film.font(run), sm.get('labels') or []):   # design/179 E7: named before the render, not after
        need(False, f"The label \"{miss['label']}\" has letters the film's font ({film.font(run)}) does not hold: {' '.join(miss['letters'][:8])}. Ask the operator: another font for this film "
                    '(`vw font` lists those that hold its language), or other words for the label.')
    said_ = lambda *pieces: ' '.join(p for p in pieces if p)   # design/221 row 14: an empty value is left out, never printed as "None" or "-"
    piece = lambda name, value: f'{name}: {str(value).rstrip(".")}.' if value not in (None, '', '-') else ''
    els = {e['id']: e for e in plan.get('elements') or []}
    known = [said_(f"{els[e].get('name') or e}:", spec_words(els[e]['material_spec'], known_only=True)) for e in shot.get('element_ids') or []
             if (els.get(e) or {}).get('material_spec') and spec_words(els[e]['material_spec'], known_only=True)]   # design/221 row 4: a size confirmed on the thing reaches every shot that shows it
    lines = [('', f"# Brief: drawn shot {shot['id']} (HyperFrames)"), ('', ''),   # design/221 row 6: what it shows first, then its facts, the text, the timings, then the look
             ('Shows', said_(piece('Shows', shot.get('depicts') or shot.get('purpose')), piece('Message', shot.get('message')))),
             ('Claims', f"Claims (each must be plainly true in the picture): {'; '.join(shot.get('claims') or []) or 'none'}."),
             ('Framing', said_(piece('Framing', shot.get('framing')), piece('Appearance', shot.get('appearance') or (plan.get('foundation') or {}).get('appearance')))),
             ('Camera', 'Camera: ' + ': '.join(film.CAMERA[shot.get('camera_flow') or 'fixed'])),   # design/221 section 10: one flow per shot; none named is Fixed
             ('Confirmed for the things in this shot', f"Confirmed for the things in this shot: {'; '.join(known)}" if known else '')]
    note = corner_note(spec)   # design/221 row 9: drawn by the server, so it is neither the spec's label nor a text on screen here
    prev = continues_from(plan, session, gap, shot)   # design/221 row 12
    continues = {}
    if build:   # design/221 (the critic's A1): the labels and cues of every drawn shot are in the plan before the first brief, so no render is made stale by them later
        bare = [s['id'] for g_ in plan['gaps'] for sc in chosen_scenes(g_, session['choice_selections'].get(g_['gap_id'])) for s in sc['shots']
                if text_no_labels(s)]   # design/221 phase 3c: a shot's message is its point, not text on screen. The critic's point 4: the server cannot know a shot's own words, so every such shot is asked. Release 3, C4: the plan check names them first (`labels_missing`)
        one = len(bare) == 1
        need(not bare, f"Before the first brief, the texts of every drawn shot go in the plan: {', '.join(bare)} {'carries' if one else 'carry'} text and {'has' if one else 'have'} "
                       'no scene_motion.labels: add scene_motion: {labels: [every text the viewer reads, word for word, never the corner note], cues: [{selector: "#id", word or at_s}]} '
                       f"to {'it' if one else 'each'} in the plan, then propose the plan. If the only text of a shot is the corner note or a logo picture, set carries_text to "
                       'false on that shot in the plan.')
        need_parts(plan, session)   # design/221 row 1: two or more drawn graphics: their shared parts, drawn once and approved, before any brief
        if prev:   # design/221 row 2: built on the earlier drawing's passed project and its last frame
            before = guarded(lambda: locate(store, session, prev))[3]
            sha, on = passed_project(session, before), opens_on(session, prev)
            own = (session.get('motion_stills') or {}).get(shot['id']) or {}
            moves = still_approved(own) and not opens_changed(session, prev, own)   # the critic's point 7: its own still stands, so this brief is for its motion; else for
            need(sha if moves else (on or sha), (CHAIN_FIRST if moves else CHAIN_STILL).format(shot=shot['id'], prev=prev))   # its still, which opens on the earlier approved still
            last = last_second(before, fps)
            continues = {'shot_id': prev, **({'sha256': sha, 'project_key': session['motion_projects'][sha]['key'],
                                              'last_frame_key': last_frame_key(conn, run, prev, sha, last) if conn is not None else '', 'last_second': last} if sha
                                             else {'project_key': on['project_key']} if on['project_key'] else {}), **({'opens_on_key': on['key']} if on and not moves else {})}
    if spec:
        lines += [('Drawing spec', f"Drawing spec, view {view_words(spec)}: {spec_words({**spec, 'label': ''} if note else spec) or 'nothing stated'}"
                   + (' (illustrative: no figure for an unknown size).' if spec.get('illustrative') else '.'))]
    shown = [l for l in sm.get('labels') or [] if _flat(l) != _flat(note)]
    used = shot_parts(session, shot)   # design/221 row 1: the approved shared parts of this shot's things, and those of no thing
    mine = {i for ids in view_parts(session, shot).values() for i in ids}   # fix set B2, A3.2: the view this drawing shows, named with its parts
    bare = [els.get(e, {}).get('name') or e for e, ids in fit_parts(session, shot).items() if not ids]   # release 2, F5: drawn in other views only; the line changes for such a shot alone
    lines += [('Use these parts', PARTS_LINE.format(parts='; '.join(f"{p['id']}: {p['title']}" + (f" (view {p['view']})" if p.get('view') else '') for p in used),
                                                    view=f", {spec['view']} ({', '.join(p['id'] for p in used if p['id'] in mine)})," if mine else '')
               + (PARTS_NO_VIEW.format(things=', '.join(bare), view=spec.get('view')) if bare else '') if used else '')]
    lines += [('Text on screen', f"Text on screen, word for word, and only these: {'; '.join(chr(34) + l + chr(34) for l in shown) or 'none'}."),   # design/221 (the critic's A1): the labels are in the plan before the first brief
              ('Corner note', f'Corner note: "{note}" is drawn by the server in the lower right corner of every frame, in the box from 80 % of the width and 90 % of the height to the edges. '
                                             'Do not draw it, and keep that corner free.' if note else ''),
              ('Length', f"Length: exactly {frames} frames at {fps} fps = {float(exact):.3f} s. Size {W}x{H}. Root: data-duration=\"{float(exact):g}\" data-fps=\"{fps}\" data-width=\"{W}\" data-height=\"{H}\"."),
              ('Narration', f"Narration (spoken over it; silent picture): \"{shot.get('narration', '')}\""),
              ('Each word\'s start', f"Each word's start, seconds from the shot's start: {timed}."),
              ('Cues', 'Cues from the plan (each part has this id and starts to move at its word or second): '   # design/221 (the critic's point 2): the builder sees the cues the render checks
               + '; '.join(f"{c.get('selector')} at " + (f"{float(c['at_s']):g} s" if c.get('at_s') is not None else f"the word \"{c.get('word')}\"") for c in sm.get('cues') or []) + '.'
               if sm.get('cues') else ''),
              ('Progression', piece('Progression', shot.get('information_progression'))),
              ('Look at', 'Look at these before you draw (in refs/): ' + '; '.join(f"{els.get(e, {}).get('name') or e}: " + ', '.join(f'refs/{rid}.png ({_shows(r)})' for rid, r in rs)
                                                                         for e, rs in look.items()) + '.' if look else ''),   # design/221 row 5: each thing's footage picture and approved pictures, opened first
              ('Pictures', 'Pictures you may place (approved): ' + ('; '.join(f"assets/ref/{rid}.png = {r.get('name') or r.get('subject') or r.get('kind')}" for rid, r in pictures) or 'none') + '.'),
              ('Continues from', f"Continues from {prev}: this drawing is built on {prev}'s project: start from a copy of {prev}'s files and from {prev}'s last frame, and open "
                                 f"exactly as {prev} ends (same framing, same size, same parts). Its still end-frame comes first, built from {prev}'s approved still end-frame "
                                 f"(from-{prev}/opens-on.png, with that still's files); the motion is started only after {prev}'s project has passed its fact check." if prev else ''),   # design/221 row 2; the critic's point 7
              ('Palette', palette_line(plan, session)),   # design/218: the plan's palette and the colours added since, the same for every drawing
              ('Fonts', f"Fonts: {', '.join(chr(34) + n + chr(34) for n in fonts[1])}, from assets/fonts/{' or assets/fonts/'.join(fonts[0])} with @font-face; no other family."
               + (f" The film's font is {film.font(run)}: every text is set in it (its family for each script, as named here; two files of one family are its regular and its bold); "
                  '"Noto Sans" only for a sign it lacks.' if film.font(run) and film.font(run) != 'Noto Sans' else '')),
              ('Rules', f"Rules: GSAP from {'assets/vendor/gsap.min.js'}; nothing loads from the network; no Math.random, Date, timers; no sound; every label at least 2.6 % of the frame height, inside the inner 90 %; "
               'every label sentence case as written above.'),
              *(('Note on the view', f'Note on the view (the spec above wins where they differ): {n["text"]}') for n in session.get('drawing_notes') or [] if shot['id'] in n['shots'] and not n.get('shared')),
              ('Shared look', '\n'.join(['Shared look (every drawing of this film):', *shared]) if shared else ''),   # design/221 row 7: recorded once before the first brief (`vw motion note --shot all`)   # design/218b: below the spec; this shot is a drawn shot of the plan (located above)
              ('', ''), ('Motion style', film.style_part(run))]   # design/179 S4: the film's motion style; the fixed 'flat, clean, technical' is gone
    for stem in _subjects_of(plan, shot):   # design/130 §4 step 8: what earlier films taught about this shot's subject (design/134 16); design/221 row 14: each with where it comes from
        for source, rules in _subject_rules(store, stem):
            lines += [('', ''), ('Subject rules', '\n'.join([f'Subject rules ({stem}), {source}: every one holds in this drawing.', *(f'- {r}' for r in rules)]))]
    lines = [(k, t) for k, t in lines if t or not k]
    prints = {}
    for k, t in lines:   # design/221 S3: one fingerprint per labelled line, so a later change of the brief can be named
        if k:   # design/221 row 1: the parts line also carries the drawings of its parts, so a part drawn again makes the rules be read again
            prints[k] = hashlib.sha256((prints.get(k, '') + t + (''.join(p['digest'] for p in used) if k == 'Use these parts' else '')).encode('utf-8')).hexdigest()[:16]
    refs = list(dict.fromkeys([rid for rid, _ in pictures] + [rid for rs in look.values() for rid, _ in rs]))
    mine = [p for p in (session.get('motion_projects') or {}).values() if p.get('shot_id') == shot['id'] and p.get('rules')] if build else []
    compare = compare_frames(comparing(session, plan, max(mine, key=lambda p: p.get('at') or '')['rules'])) if mine else []   # fix set A1.2: the stills its latest rules compare with
    return {'shot_id': shot['id'], 'brief': '\n'.join(t for _, t in lines) + '\n', 'refs': need_pictures(store, run, session, refs, shot['id']) if build else refs, 'frames': frames, 'fps': str(fps), 'lines': prints,
            **({'continues': continues} if continues else {}), **({'parts_key': session['motion_parts_approved']['key']} if used else {}), **({'compare': compare} if compare else {})}


def spec_words(spec, known_only=False):
    """design/221 rows 4 and 14: a spec's parts, sizes, relationships, proportions and label in the brief's words; an empty piece is left out, an
    unknown size says so with no number, a size with no status gets no word. known_only: the confirmed and measured sizes and the proportions only."""
    def size(d):
        if d.get('status') == 'unknown' or d.get('value') is None:
            return f"{d.get('part')} {d.get('measure')} unknown (no figure)"
        return ' '.join(str(x) for x in (d.get('part'), d.get('measure'), f"{d['value']:g}" if isinstance(d['value'], (int, float)) else d['value'], d.get('unit')) if x not in (None, '')) \
            + (f" ({d['status']})" if d.get('status') else '')
    dims = [d for d in spec.get('dimensions') or [] if not known_only or (d.get('status') in ('confirmed', 'measured') and d.get('value') is not None)]
    pieces = ([] if known_only else [('parts', ', '.join(spec.get('parts') or []))]) + [('sizes', '; '.join(size(d) for d in dims))] \
        + ([] if known_only else [('relationships', '; '.join(spec.get('relationships') or []))]) + [('proportions', '; '.join(spec.get('proportions') or []))] \
        + ([] if known_only else [('label', f'"{spec["label"]}"' if spec.get('label') else '')])
    return '; '.join(f'{k} {v}' for k, v in pieces if v)


def brief_pictures(session, shot):
    """design/134 2, 16: the approved pictures a drawn shot may place: its own elements' sheets and components, their golden pictures, and the style picture."""
    els = set(shot.get('element_ids') or [])
    gold = {golden_of(session, e) for e in els} - {None}
    return [(rid, r) for rid, r in session['references'].items() if r.get('status') == 'approved' and r.get('key')
            and (r.get('kind') == 'style' or rid in gold or (r.get('kind') in ('component', 'sheet') and r.get('element_id') in els))]


def picture_file(store, run, session, rid):
    """Fix set B1 (defect 55, 19 Nov 2026): where this picture's file is: the key its record names (an approved drawing is kept under
    visuals/drawings/), else <run>/visuals/references/<id>.png; '' when no file is there. The brief and the fetch both ask this."""
    for k in (((session.get('references') or {}).get(rid) or {}).get('key'), key(run, f'references/{rid}.png')):
        if k and k.startswith(f"{run['id']}/") and store.exists(k):   # release 2, F14: a record naming a file of another run is treated as missing
            return k
    return ''


def fetch_key(store, run, k):
    """Fix set B1: the key the download route serves for `k`: `k` itself when a file is there; for <run>/visuals/references/<id>.png (the name the
    plugin asks a brief's picture by) with no file there, where that picture's file is; '' when there is none."""
    if store.exists(k):
        return k
    m = re.fullmatch(re.escape(key(run, 'references/')) + r'([^/]+)\.png', k)
    try:
        return picture_file(store, run, session_of(store, run, None), m.group(1)) if m else ''
    except Problem:   # a run with no visuals session holds no such picture
        return ''


PICTURE_MISSING = ('{what}: the file of an approved picture of this brief is not with the run: {ids}. It cannot be fetched: file a defect (`vw defect`) '
                   'that names it; do not build from the brief without it.')


def need_pictures(store, run, session, ids, what):
    """Fix set B1: a brief lists only pictures whose file can be fetched; a missing one is named here, not as a 404 at the fetch. The ids, unchanged."""
    gone = [rid for rid in ids if not picture_file(store, run, session, rid)]
    need(not gone, PICTURE_MISSING.format(what=what, ids=', '.join(gone)))
    return ids


def look_pictures(session, shot):
    """design/221 row 5: for each thing of a drawn shot, its approved pictures (its footage frames first), to look at before drawing."""
    out = {}
    for e in shot.get('element_ids') or []:
        rs = sorted(((rid, r) for rid, r in session['references'].items() if r.get('status') == 'approved' and r.get('key') and (r.get('element_id') == e or rid == golden_of(session, e))),
                    key=lambda p: (p[1].get('kind') != 'frame', p[0].lower()))
        if rs:
            out[e] = rs
    return out


def _shows(r):
    """What a picture shows, in the brief's words."""
    what = r.get('name') or r.get('subject') or r.get('kind')
    return f'{what}, from the footage' if r.get('kind') == 'frame' else what


def motion_job(conn, store, run, job_id):
    """design/130: a motion check, snapshot or render as the helper reads it: its status, findings, and the snapshots as base64 PNGs."""
    job = conn.execute("select * from vw2_jobs where id=%s and run_id=%s and provider in ('motion', 'drawn')", (job_id, run['id'])).fetchone()
    need(job, f'{job_id} is no motion job of this film.')
    res = dict(job.get('result') or {})
    if (job.get('request') or {}).get('kind') == 'motion-check' and job['status'] == 'ready':   # design/221 row 17: the check's answer says which short label is a must
        try:
            session = session_of(store, run, None)
            plan, gap, _scene, shot = locate(store, session, job['unit'])
            musts = own_short_labels(plan, session, gap, shot, res)
        except (Problem, ValueError):
            musts = []
        res.update({'label_musts': musts} if musts else {})
    if res.get('snapshots'):
        res['snapshots'] = [{'at': s['at'], 'png_base64': base64.b64encode(store.get(s['key'])).decode(),
                             'crops': [{'box': c['box'], 'png_base64': base64.b64encode(store.get(c['key'])).decode()} for c in s.get('crops') or []]} for s in res['snapshots']]
    return {'job_id': str(job['id']), 'status': job['status'], 'kind': (job.get('request') or {}).get('kind'), 'error': job.get('error'), 'result': res}


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
    need(shot['visual_type'] != 'footage' or row.get('kind') == 'frame', f'shot {shot_id} is a footage shot: it shows a footage frame or a clip stretch, never a made picture.')   # design/124-b item 1
    quote = said(quote, 'Placed', user)   # design/99 C2
    need(row.get('kind') != 'web', 'a web picture is a guide only; it cannot appear in the film.')   # design/94 R1.5 (U2)
    warns = []
    made = made_for(session, row)
    if made and made != shot_id:   # R1.7 (L2): only into its own shot, or moved with the operator's words
        need(str(move or '').strip(), f"{reference_id} was made for {made}; make one for {shot_id} (`vw visuals image --shot {shot_id} …`), or move it with the operator's words (--move).")
    elif not made and row.get('kind') in ('keyframe', 'state'):
        warns.append(f'{reference_id} has no shot recorded: make pictures with --shot so each is placed only in the shot it was made for')
    used = [sid for sid, a in session['assets'].items() if sid != shot_id and a.get('reference_id') == reference_id] + [sid for sid, rid in _start_images(store, session).items() if rid == reference_id and sid != shot_id]
    _rule(session, not used or repeat_allowed(row), f'this picture is already in {used[0] if used else ""}. Two shots never show the same picture: compose another (a reimagined shot, return_of, for a return), '
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


REUSE_APART_S = 60          # design/89 H4 (SK): a reuse is at least this far from the other showing; design/207 (D2): or a quarter of the film, when that is shorter
REUSE_RETIRED = ("A reuse no longer needs the operator's approval: a reuse with its reason that passes the checks is kept when the shot is placed. "
                 'Place the shot again with the reason and the reimagined shot considered (`vw visuals clip` or `vw visuals still`, with --reuse, --considered and --crop).')   # design/207 (D2): the older way, retired by name
REUSE_MIN_ZOOM = 1 / 0.7    # a clearly different framing: a crop of 30 % (1.43×), only within the clip's safe enlargement


def media_clips(outputs):
    media = next((o for o in outputs if o['stage'] == 'media' and o['unit'] is None), None)
    return {c['id']: c for c in ((media or {}).get('summary') or {}).get('clips') or []}


def library_clips(store, run):
    """Defect 59: the clips of the client's library this film was offered at the first cut (design/147 L4), by id. Each carries `key`, where its file is
    in its source film, and `library_from`. None when the film has no first-cut record."""
    from .stage2 import stage as S2
    if not store.exists(S2.key(run, 'session.json')):   # no first cut on this film; a record that is there but cannot be read is an error, never "no such clip"
        return {}
    clips = (S2.session_of(store, run).get('package') or {}).get('clips') or {}
    return {cid: c for cid, c in clips.items() if c.get('library_from')}


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
        return None, 'give the crop that makes the framing clearly different (--crop x,y,w,h, fractions of the frame).'
    x, y, w, h = (float(v) for v in crop)
    if not (0 <= x and 0 <= y and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1.0001 and y + h <= 1.0001 and abs(w - h) <= 0.01):
        return None, 'the crop lies inside the frame and keeps its shape (w equal to h).'
    zoom = 1 / max(w, h)
    if not REUSE_MIN_ZOOM - 1e-6 <= zoom <= safe + 1e-6:
        return None, f"the crop enlarges {zoom:.2f}×; it must be between {REUSE_MIN_ZOOM:.2f}× and the clip's safe {safe:.2f}×."
    return [x, y, w, h], ''


def _reuse_gate(store, run, session, outputs, shot, clip_id, src_in, src_out, moving, reuse, quote, crop, pending):
    """design/89 H2-H4 with SK's H4: a clip already on screen is a reuse: never a frozen frame of a clip that plays elsewhere; otherwise only with the
    reason and the reimagined shot considered, 60 s apart (or a quarter of the film, when that is shorter), a different stretch, and a crop within the
    clip's safe enlargement. design/207 (D2): a reuse that passes is kept, with the assistant's reason on the asset; nothing waits for the operator
    (the older way, retired: REUSE_WAITING and the operator's approval; an entry left in reuse_pending from before is cleared here).
    Returns (the reuse kept with the asset or None, the warnings): in a session begun before batch 1 every broken rule is a warning instead."""
    session.pop('reuse_pending', None)   # saved with the placement; its shot was never filled, so the assistant places it again and this gate decides
    fps = session['source'].get('fps') or 25
    film = film_frames(outputs)
    apart_min = min(REUSE_APART_S, _sec(film, fps) / 4) if film else REUSE_APART_S
    film_in, film_out = _sec(shot['start_frame'], fps), _sec(shot['end_frame'], fps)
    others = [e for e in ledger(store, session, outputs) if e.get('clip_id') == clip_id and e['shot_id'] != shot['id']]
    warns = []
    if not others:
        return None, warns
    names = ', '.join(f"{e['shot_id']} ({e['where']})" for e in others)
    if not moving:
        _rule(session, not any(e['moving'] for e in others), f'clip {clip_id} plays elsewhere ({names}); a frozen frame of it is never shown: use another clip, or a moving stretch as a reuse.', warns)
    else:
        _rule(session, all(e['moving'] for e in others), f'clip {clip_id} is shown as a frozen frame in {names}; a clip is either moving or a frame in the film, never both.', warns)
    r = reuse or {}
    why = bool(str(r.get('reason') or '').strip() and str(r.get('considered') or '').strip())
    _rule(session, why, f'clip {clip_id} is already on screen in {names}: showing it again is a reuse. Prefer a reimagined shot (the same subject from another angle, distance or moment, '
                        "return_of). A plain reuse needs the reason, the reimagined shot you considered and why it adds nothing (--reuse, --considered, or the page's reuse fields).", warns)
    for e in others:
        apart = max(film_in - e['film_out_s'], e['film_in_s'] - film_out)
        _rule(session, apart >= apart_min - 1e-6, f"{shot['id']} is {apart:.0f} s from {e['shot_id']}; a reuse is at least {apart_min:.0f} s apart.", warns)
        _rule(session, src_out <= e['src_in_s'] or src_in >= e['src_out_s'] if (moving or e['moving']) else abs(src_in - e['src_in_s']) >= 1.0,
              f"a different stretch of clip {clip_id} from the one in {e['shot_id']}, with no overlap in the clip's own time.", warns)
    safe = float((session.get('clip_safe_zoom') or {}).get(clip_id) or 1.0)
    _rule(session, safe >= REUSE_MIN_ZOOM - 1e-6, f'clip {clip_id} can be enlarged only {safe:.2f}× before it goes soft; a clearly different framing needs {REUSE_MIN_ZOOM:.2f}×. '
                                                 'Use a reimagined shot instead (return_of): a soft picture is never the fix for a repeat.', warns)
    box, problem = _crop_check(crop, safe)
    _rule(session, box is not None, problem, warns)
    # a session begun before batch 1 is placed with its warnings; in every other one each broken rule above was refused, so the reuse is kept here
    return ({'reason': r.get('reason'), 'considered': r.get('considered'), 'crop': box, 'on_screen': names} if why and box else None), warns


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
    need(shot['visual_type'] in ('image', 'video', 'footage'), f"shot {shot_id} is a {shot['visual_type']}: a clip stretch fills a footage, still or video shot, never a graphic.")   # design/124-b item 1
    clip = media_clips(outputs).get(clip_id) or library_clips(store, run).get(clip_id)   # defect 59: this film's own clip first, else a clip of the client's library
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
                                  **({'key': clip['key'], 'library_from': clip['library_from']} if clip.get('library_from') else {}),   # defect 59: a library clip's file is in its source film
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
    """design/207 (D2): retired. A reuse no longer waits for the operator (the older way: design/89 H2, H7, the operator's own words on the page or in
    chat). Kept so that an older tool or page that still calls it is answered in plain words."""
    need(False, REUSE_RETIRED)


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


def _movie_seconds(store, file_key):
    """E17: the length of a supplied movie, read once from its stored file when it is placed; None when it cannot be read (the page then says nothing about its length)."""
    try:
        from .visual_workers import probe
        return round(float(probe(store.signed_download(file_key))['duration_seconds']), 3)
    except Exception:   # no ffprobe, no such file, not a movie: never a reason to refuse the asset
        return None


NEED_MADE = 'Say how the file was made: `vw visuals asset --shot S --file out/<name> --kind … --made "<how the file was made>" --quote "…"`. A file handed in without it is no longer taken (integration step A).'
CHECKS_SKIPPED = 'made outside; checks skipped'   # what the page and the status say of a handed-in file


def add_asset(conn, store, user, run, outputs, shot_id, file_key, sha256, size, kind, quote, made=''):
    """A hand-made movie or still already uploaded with a receipt becomes the shot's output. Integration step A (SK, 12 Nov 2026): it says how it was
    made, and every hand-in is one row of the shot's record, written before the file is placed (no file without its record)."""
    session = session_of(store, run, outputs)
    plan, gap, scene, shot = guarded(lambda: locate(store, session, shot_id))
    need(kind in ('movie', 'still'), 'Local assets are movie or still.')
    made, limit = (made or '').strip(), settings().MAX_QUOTE_CHARS
    need(made, NEED_MADE)
    need(len(made) <= limit, f'How the file was made is {len(made):,} characters; the limit is {limit:,}. Shorten it; nothing was stored.')
    row = conn.execute('select key, sha256, bytes from vw2_files where run_id=%s and key=%s', (run['id'], file_key)).fetchone()
    need(row and row['sha256'] == sha256, 'Upload the asset with a receipt first (vw upload).')
    generations.opened(conn, run['id'], shot_id, 'handed in', {'kind': 'handed in', 'checks': 'not run', 'note': "handed in; the application's checks were not run",
                                                               'made': made, 'file_kind': kind, 'key': file_key, 'sha256': sha256, 'quote': quote, 'by': user['id'], 'by_name': user.get('name') or ''})
    session['assets'][shot_id] = {'kind': kind, 'key': file_key, 'sha256': sha256, 'bytes': size, 'quote': quote, 'made': made, 'by': user['id'], 'by_name': user.get('name') or '',   # R21: the page says who supplied it
                                  'duration_s': _movie_seconds(store, file_key) if kind == 'movie' else None,   # E17
                                  'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame']}}
    session['selections'].pop(shot_id, None)
    save_session(store, run, session)
    return {**session['assets'][shot_id], 'record': CHECKS_SKIPPED}


def generations_of(conn, store, run, outputs, shot_id):
    """Integration step A: every attempt of a shot, oldest first. Rows of a shot the plan no longer holds are still read; a shot with neither rows nor a place in the plan is refused."""
    rows = generations.of_shot(conn, run['id'], shot_id)
    if rows:
        return {'shot_id': shot_id, 'generations': rows}
    guarded(lambda: locate(store, session_of(store, run, outputs), shot_id))
    return {'shot_id': shot_id, 'generations': [], 'message': f'No generations yet for {shot_id}.'}


# ---------- status / gap outputs ----------

def reconcile(conn, run, session):
    """Ticket 9: repair references left 'generating' after their image job finished (a lost write). Returns how many changed."""
    from .visual_workers import apply_image_result
    fixed = 0
    for ref in made_pictures(session):   # SK, 23 Nov 2026: the look boards too
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
    fixed = reconcile(conn, run, session)
    marked = not kept(session) and mark_kept(session, run)   # design/151 hotfix: a new film is kept before its round
    plan = current_plan(store, session) if session.get('current') else None
    from . import pictures
    stamped = bool(plan) and round_v2(session) and (pictures.stamp(session, plan) | pictures.asked(session, plan))   # design/217: a picture that waited for the model's check is given to Claude's check
    if (fixed or marked or stamped) and repair:
        save_session(store, run, session)
    looks = pictures.waits_words(session, plan) if plan and round_v2(session) else ''
    gaps = []
    for gid, g in session['source']['gaps'].items():
        entry = {'gap_id': gid, **g, 'accepted': gid in session['accepted'], 'recorded': gid in session['recorded_gaps'], 'shots': [], **_accepted_words(session, gid)}
        if plan and gid in session['accepted']:
            for s in shots_of(plan, session, gid):
                entry['shots'].append({'shot_id': s['id'], 'visual_type': s['visual_type'], 'bound': s['id'] in session['bindings'], 'prepared': s['id'] in session['preparations'],
                                       'selected': s['id'] in session['selections'], 'asset': s['id'] in session['assets'],
                                       'made_outside': (session['assets'].get(s['id']) or {}).get('kind') in ('movie', 'still')})   # integration step A: a handed-in file, checks skipped
        gaps.append(entry)
    refs = [{**{k: r.get(k) for k in ('id', 'name', 'kind', 'element_id', 'status', 'sha256', 'job_id', 'set', 'set_n', 'notes', 'sources')}, 'note': (r.get('source') or {}).get('note') or '', 'sources_changed': bool(r.get('sources_changed'))}   # design/106 N4; design/110; design/151
            for r in session['references'].values()]
    take_rows = take_jobs(conn, run)
    six = pictures.expected(session, plan, take_rows) if plan and round_v2(session) else []   # design/221 row 18: the line of counts of step 6
    from . import takes
    seven = takes.expected(session, plan, take_rows) if plan and round_v2(session) else []   # design/222: step 7's line of counts, beside step 6's
    step6 = ' '.join(x for x in (pictures.status_line(six), takes.status_line(seven), pictures.drawn_due(six), pictures.starts(six), pictures.stills_due(six, pictures.ask_shots(session, plan) if six else ()), pictures.supplied_due(six),
                                 takes.starts(session, plan, take_rows) if seven else '') if x)   # release 1, D1: what of step 7 can start now, together
    jobs_ = [{**{k: j[k] for k in ('id', 'unit', 'provider', 'status', 'error', 'cost')}, 'checklist': take_checklist(session, j),   # design/74 L6
              'verdict': ((session['reviews'].get(str(j['id'])) or [{}])[-1]).get('decision'),   # defect 30: a rejected take stays 'ready' as a job
              'check_marks': [{k: m.get(k) for k in ('check', 'at_s', 'seen')} for m in ((session.get('take_checks') or {}).get(str(j['id'])) or {}).get('must_failed') or []]}   # design/91 N3
             for j in take_rows]
    t = session.get('treatment')
    sp = visuals_spend(conn, run)
    return {'state': 'prepared', 'busy': not repair, **({'pictures_waiting': looks} if looks else {}), **({'step6': step6} if step6 else {}), **_shared_note(store, session), 'plan_digest': session.get('current'), 'versions': len(session['versions']), 'gaps': gaps, 'references': refs, 'jobs': jobs_,
            'searches': _searches(session),   # design/73: the searches, their picks and any "nothing fits" reason, for the assistant
            'round': _round_view(session),    # design/79: pass 1, pass 2 or complete, with each element's verdict
            'treatment': ({k: t[k] for k in ('totals', 'estimate_inr', 'quote', 'by', 'at', 'digest')} if t else None),   # design/65 B6
            'footage': {k: (footage_view(session, outputs) or {}).get(k) for k in ('line', 'summary')},   # design/88
            'waiting': waiting(session, plan, run.get('code'), take_rows, _set_budget(run, session, sp)),   # design/97 W4: each with its label and link
            'spec_corrections': {sid: c.get('words') for sid, c in (session.get('spec_corrections') or {}).items()},   # review 27 Oct: the assistant revises these specs
            'questions': dict(session.get('questions') or {}),   # design/110 rule 0: the open questions, by item
            'material_specs': {e['id']: {'approved': material_approved(session, e), 'correction': ((session.get('spec_corrections') or {}).get(material_key(e['id'])) or {}).get('words')}
                               for e in (plan or {}).get('elements') or [] if e.get('material_spec')},   # design/111 F10
            'golden': dict(session.get('golden') or {}), 'golden_due': golden_due(session, plan) if plan else [],   # design/111 F11
            'sheet_due': sheet_due(session, plan) if plan else [],   # design/119 rule 2
            'kept': kept(session),   # design/151 hotfix: the references are made the kept way (no search, no picks, no sheet per element: the round makes every set)
            'round_due': round_status(session, plan),   # design/151 hotfix: the round is next, said in words; design/211 review: a v2 round's own sentence by its state
            'image_provider': provider_of(run),   # design/120
            'set_provider': 'gemini',   # design/151 hotfix: a reference set is the kept (Gemini) method on every film, whatever image_provider says
            'not_this': {eid: list(rec.get('lines') or []) for eid, rec in (session.get('not_this') or {}).items()},   # design/111 F12
            'needed_elements': needed_elements(plan) if plan else [],   # design/111 F14
            'illustrative': illustrative_share(plan) if plan else {'illustrative': [], 'specs': 0, 'warning': None},   # design/111 F19
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
    return {'recorded': recorded, 'skipped': skipped, 'next': record_next(plan, session_of(store, run, outputs)['recorded_gaps'], skipped)}


def record_next(plan, recorded_gaps, skipped):
    """design/132 E4: once every gap is recorded, the editor's package comes next, before the assembly."""
    if skipped:
        return 'finish the skipped gaps, then record again'
    if all(g['gap_id'] in recorded_gaps for g in plan['gaps']):
        return "`vw delivery bundle` (the editor's package, before the assembly)"
    return '`vw next`'


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
                          'duration_s': ev.get('duration_seconds'), 'timing_matches_placement': ev.get('timing_matches_placement'),
                          **({'media': {**media, **({'in_s': sel['in_s']} if sel.get('in_s') else {})}} if media else {}), **boundary})   # integration step E: the take's in point travels with the recorded shot
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
            lib = {k: asset[k] for k in ('key', 'library_from') if asset.get(k)}   # defect 59: a library clip is read from its source film, by the render and by the editor's package
            files.append({'name': name, 'key': asset.get('key') or f"{run['id']}/media/{asset['name']}", 'sha256': asset['sha256'], 'bytes': asset.get('bytes'),
                          'location': 'library' if lib else 'storage', 'receipt': True})   # a library clip's receipt is its source film's: the record does not ask this film for one (core.output)
            shots.append({'shot_id': s['id'], 'source': 'clip', 'kind': 'clip', 'placement': asset['placement'],
                          'media': {'kind': 'clip', 'clip': {**{k: asset.get(k2) for k, k2 in (('id', 'clip_id'), ('name', 'name'), ('sha256', 'sha256'), ('fps', 'fps'), ('rotation_deg', 'rotation_deg'), ('hdr', 'hdr'))}, **lib},
                                    'in_s': asset['in_s'], 'out_s': asset['out_s'], 'crop_rect': asset.get('crop') or (asset.get('reuse') or {}).get('crop')}})
        else:
            name = f"{s['id']}-asset{'.mp4' if asset['kind'] == 'movie' else '.png'}"
            files.append({'name': name, 'key': asset['key'], 'sha256': asset['sha256'], 'bytes': asset['bytes'], 'location': 'storage', 'receipt': True})
            jobs.record_file(conn, run['id'], STAGE, asset['key'], name, asset['sha256'], asset.get('bytes') or 0, 'video/mp4' if asset['kind'] == 'movie' else 'image/png')   # design/82 U1: a still from a reference was never an upload
            shots.append({'shot_id': s['id'], 'source': 'asset', 'kind': asset['kind'], 'placement': asset['placement'],
                          **({'media': {'kind': 'still', 'motion': s.get('motion') or 'push_in', 'graphic': s['visual_type'] in ('diagram', 'animation'),
                                        'text': _still_text(s, session['references'].get(asset.get('reference_id')))}} if asset['kind'] == 'still' else {})})   # design/89 B2; design/112 K4
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


def size_sentence(element):
    """design/119 rule 6: the element's known sizes as one sentence beside its name; nothing for an unknown (design/106 D6)."""
    parts = [f"{d.get('part', '')} {d.get('measure', '')} {d['value']:g} {d.get('unit') or ''}".strip() for d in element.get('size') or [] if d.get('value') is not None]
    return f"{element.get('name') or element.get('id')}: {', '.join(parts)}" if parts else ''


CAMERA_NOTE = re.compile(r'\b(focus|sharp|\d+\s?mm feel|natural colour|micro-contrast|sharpening|grain|bokeh|lens|hdr)\b', re.I)


def also_shows(parent, own=()):
    """design/119 rule 3: the things a reference's own stored prompt put in its Details sentence, less the shot's own things, less camera notes.
    [] for a picture with no stored prompt (a frame, a supplied or web picture)."""
    prompt = (parent.get('generation') or {}).get('prompt') or ''
    m = re.search(r'Details:\s*(.+?)(?:\.\s+[A-Z][a-z]+:|\n|$)', prompt, re.S)
    if not m:
        return []
    own_l = [w.lower() for w in own if w]
    out = []
    for phrase in re.split(r';|,|\band\b', m.group(1)):
        ph = phrase.strip(' .')
        if not ph or CAMERA_NOTE.search(ph) or len(ph.split()) > 10:
            continue
        if any(o and (o in ph.lower() or ph.lower() in o) for o in own_l):
            continue
        out.append(ph)
    return out


CROP_MIN_PX = 64   # design/119 rule 1: a crop smaller than this either way is too small to tell the model anything


def check_crop(region):
    """design/119 rule 1: a crop is a rectangle in fractions of the frame, inside it; unlike an edit's region it has no upper bound."""
    need(isinstance(region, dict) and all(k in region for k in ('left', 'top', 'width', 'height')), 'A crop is {left, top, width, height}, fractions of the frame.')
    try:
        l, t, w, h = (float(region[k]) for k in ('left', 'top', 'width', 'height'))
    except (TypeError, ValueError):
        need(False, 'A crop is four numbers between 0 and 1.')
    need(0 <= l < 1 and 0 <= t < 1 and 0 < w <= 1 and 0 < h <= 1 and l + w <= 1 + 1e-9 and t + h <= 1 + 1e-9, 'The crop lies inside the frame: left + width and top + height are at most 1.')


def cropped_parent(store, run, p, region):
    """The parent entry of a request: the full picture, or, with a region, the crop stored beside the reference (`<id>-crop-<hash>.png`) sent as that picture."""
    entry = {'id': p['id'], 'key': p['key'], 'sha256': p['sha256']}
    if not region:
        return entry
    from io import BytesIO
    from PIL import Image
    from .visual_workers import region_box
    with Image.open(BytesIO(store.get(p['key']))) as im:
        box = region_box(region, *im.size)
        need(box[2] - box[0] >= CROP_MIN_PX and box[3] - box[1] >= CROP_MIN_PX, f"the crop of {p['id']} is {box[2] - box[0]} x {box[3] - box[1]} px: too small to send (at least {CROP_MIN_PX} px each way).")
        buf = BytesIO()
        im.crop(box).save(buf, format='PNG')
    data = buf.getvalue()
    sha = hashlib.sha256(data).hexdigest()
    k = f"{run['id']}/visuals/references/{p['id']}-crop-{sha[:8]}.png"
    store.put(k, data, 'image/png')
    return {**entry, 'key': k, 'sha256': sha, 'crop': {x: float(region[x]) for x in ('left', 'top', 'width', 'height')}, 'full_key': p['key']}


HEIGHT_WORD = re.compile(r"([a-z][a-z\- ]{2,40}?)\s+(?:at|to|up to)\s+(knee|waist|chest|shoulder|head)[- ]height|(knee|waist|chest|shoulder|head)[- ]high\s+((?:[a-z\-]+\s+){0,2}[a-z\-]+)", re.I)   # design/119 rule 8
VERBS = re.compile(r"\b(runs|stands|sits|lies|rises|crosses|reaches)\b", re.I)


def _heights(scene):
    out = []
    for m in HEIGHT_WORD.finditer((scene or {}).get('layout') or ''):
        thing = (m.group(1) or m.group(4) or '').strip(' ,;.')
        word = (m.group(2) or m.group(3) or '').lower()
        v = VERBS.search(thing)
        if v:   # 'A plinth top runs across the frame at knee height' -> 'plinth top'
            thing = thing[:v.start()].strip(' ,;.')
        thing = re.sub(r"^(?:a|an|the)\s+", '', thing, flags=re.I).strip()
        if thing and (thing, word) not in out:
            out.append((thing, word))
    return out


def height_lines(scene):
    """design/119 rule 8: a height word in the layout is a must line: the thing reaches a standing person's knee, waist, chest, shoulder or head, no higher."""
    return [{'check': f'{thing} at {word} height', 'weight': 'must',
             'pass_when': f"the {thing} reaches a standing person's {word} and no higher; the rest of the person is above it, feet on the same ground"} for thing, word in _heights(scene)]


def height_sentence(scene):
    hs = _heights(scene)
    return ('Heights: ' + '; '.join(f"the {thing} reaches a standing person's {word} and no higher; the rest of the person is above it, feet on the same ground" for thing, word in hs) + '.') if hs else ''
